"""Binary localization, lazy extraction, cache invalidation and atomic Pak output."""
from pathlib import Path
import json
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import localization as loc, job_localization as jobs, pakfile, pakio, mod_library
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_root_files

ALIASES = {'sid_journal_S2T_Job_Test_Name':'sid_journal_Test_Name',
           'sid_journal_stage_S2T_Job_Test_Start':'sid_journal_stage_Test_Start'}


def optimized_fixture():
    # Independently assembled tiny version-3 resource, including a non-BMP string.
    namespace = b'NS\0'
    key = b'Key\0'
    table = (struct.pack('<IIIi', 1, 1, 123, len(namespace)) + namespace
             + struct.pack('<IIi', 1, 456, len(key)) + key + struct.pack('<Ii', 0, 0))
    payload = 'Pilz 🍄\0'.encode('utf-16-le')
    pool = struct.pack('<Ii', 1, -len(payload)//2) + payload + struct.pack('<i', 1)
    return loc.MAGIC + b'\x03' + struct.pack('<q', 25 + len(table)) + table + pool


class ResourceFormat(unittest.TestCase):
    def test_independent_optimized_fixture_and_compact_unicode(self):
        self.assertEqual(loc.read_resource(optimized_fixture()), {('NS','Key'):(0,'Pilz 🍄')})
        entries = {'Quest':(0,'Auftrag'), 'Stage':(0,'Найти 🍄'), 'Empty':(0,'')}
        raw = loc.write_resource('NS', entries)
        self.assertEqual(raw[:17], loc.MAGIC + b'\x01')
        self.assertEqual(loc.read_resource(raw), {('NS',k):v for k,v in entries.items()})
        self.assertEqual(raw, loc.write_resource('NS', dict(reversed(list(entries.items())))))

    def test_rejects_truncated_corrupt_and_unknown_resources(self):
        raw = optimized_fixture()
        for candidate in (b'', raw[:-1], raw+b'junk', raw[:16]+b'\x04'+raw[17:],
                          raw[:17]+struct.pack('<q',-1)+raw[25:], raw[:-4]+struct.pack('<i',99)):
            with self.subTest(size=len(candidate)), self.assertRaises(loc.ResourceError):
                loc.read_resource(candidate)
        with self.assertRaises(loc.ResourceError):
            loc.write_resource('NS', {'bad':(0,'bad\0text')})


class GameResources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pak = self.root/'game.pak'
        self.originals = {'sid_journal_Test_Name':(0,'A job'), 'sid_journal_stage_Test_Start':(0,'Find a mushroom 🍄')}
        self.write_source()
        self.gd = GameData(self.root/'data', source_pak=self.pak)

    def write_source(self):
        files = [(jobs.PREFIX+culture+'/Game.locres', loc.write_resource(jobs.NAMESPACE, {
            key:(h,text+(' / RU' if culture=='ru' else '')) for key,(h,text) in self.originals.items()}))
            for culture in ('en','ru')]
        pakfile.write_pak(self.pak, files)

    def test_lazy_default_and_alias_only_output(self):
        with patch.object(self.gd,'job_localization_files',side_effect=AssertionError('not lazy')):
            self.assertEqual(build_root_files(self.gd,Settings()),{})
            self.assertEqual(set(build_root_files(self.gd,Settings(no_mouse_smoothing=True))),{'Stalker2/Config/UserInput.ini'})
        files = self.gd.job_localization_files(ALIASES)
        self.assertEqual(len(files),2)
        for path, raw in files.items():
            self.assertTrue(path.endswith('/S2Tweaker_JobLocalization.locres'))
            entries=loc.read_resource(raw)
            self.assertEqual({k for ns,k in entries},set(ALIASES))
            self.assertFalse(set(ALIASES.values()) & {k for ns,k in entries})
            for key,original in ALIASES.items():
                expected=self.originals[original][1]+(' / RU' if '/ru/' in path else '')
                self.assertEqual(entries[jobs.NAMESPACE,key],(0,expected))

    def test_cache_reuse_corruption_and_updated_source(self):
        first=self.gd.job_localization_files(ALIASES)
        with patch.object(loc,'read_resource',side_effect=AssertionError('cache should avoid decompression')):
            self.assertEqual(self.gd.job_localization_files(ALIASES),first)
        cache=next((self.gd.dir/'.optional').glob('*.json'))
        cache.write_text('{}',encoding='utf-8')
        self.assertEqual(self.gd.job_localization_files(ALIASES),first)
        self.originals['sid_journal_Test_Name']=(0,'Updated job')
        self.write_source()
        with self.assertRaisesRegex(RuntimeError,'changed'):
            self.gd.job_localization_files(ALIASES)
        reloaded=GameData(self.gd.dir,source_pak=self.pak)
        self.assertNotEqual(reloaded.job_localization_files(ALIASES),first)

    def test_missing_original_or_changed_file_leaves_no_complete_cache(self):
        with self.assertRaisesRegex(ValueError,'identity'):
            self.gd.job_localization_files({**ALIASES,'new':'missing'})
        self.assertFalse(list(self.gd.dir.glob('.optional/*.json')))
        reader=loc.read_resource
        def changed(raw):
            self.pak.touch()
            return reader(raw)
        with patch.object(loc,'read_resource',side_effect=changed), self.assertRaisesRegex(RuntimeError,'changed'):
            self.gd.job_localization_files(ALIASES)
        self.assertFalse(list(self.gd.dir.glob('.optional/*.json')))

    def test_binary_output_is_verified_and_old_pak_retained(self):
        target=self.root/'own.pak'
        manifest={mod_library.MANIFEST:json.dumps({'manifest_version':1,'tool':'S2Tweaker test','mod_name':'Own'})}
        mod_library.build_safely({'Obj/Own.cfg':'Value = 1\n'},target,manifest,self.root/'history')
        old=target.read_bytes()
        files={**manifest,**self.gd.job_localization_files(ALIASES)}
        backup=mod_library.build_safely({'Obj/Own.cfg':'Value = 2\n'},target,files,self.root/'history')
        self.assertEqual(backup.read_bytes(),old)
        with pakfile.PakFile(target) as pak:
            for path,value in files.items():
                if isinstance(value,bytes):
                    self.assertEqual(pak.read(path),value)
        written=pakio.export_root_files(files,self.root/'debug')
        self.assertEqual(len(written),len(files))
        for path,value in files.items():
            if isinstance(value,bytes):
                self.assertEqual((self.root/'debug'/path).read_bytes(),value)


if __name__=='__main__':
    unittest.main()
