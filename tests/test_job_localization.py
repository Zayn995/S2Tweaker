"""Binary localization, lazy extraction, cache invalidation and atomic Pak output."""
from pathlib import Path
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
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
    table = (struct.pack('<IIIi', 1, 1, 2301254463, len(namespace)) + namespace
             + struct.pack('<IIi', 1, 827375239, len(key)) + key + struct.pack('<Ii', 0, 0))
    payload = 'Pilz 🍄\0'.encode('utf-16-le')
    pool = struct.pack('<Ii', 1, -len(payload)//2) + payload + struct.pack('<i', 1)
    return loc.MAGIC + b'\x03' + struct.pack('<q', 25 + len(table)) + table + pool


def preservation_fixture(version, added=()):
    # Independent native layout: multiple namespaces, shared/unused pool slots,
    # nonzero source hashes and intentionally UTF-16-encoded ASCII originals.
    hashes = {'NS':2301254463, 'Other':1912752590, 'Key':827375239,
              'Repeat':1858927902, 'New':1460575270, '火焰保护':3405809369}
    def string(value, wide=False):
        if not value:
            return struct.pack('<i', 0)
        raw = (value+'\0').encode('utf-16-le' if wide else 'utf-8')
        return struct.pack('<i', -len(raw)//2 if wide else len(raw)) + raw
    def key(value, wide=False):
        prefix = struct.pack('<I', hashes[value]) if version == 3 else b''
        return prefix + string(value, wide)
    table = bytearray(struct.pack('<I', 2))
    table += key('NS') + struct.pack('<I', 2+len(added))
    table += key('Key', True) + struct.pack('<Ii', 0xdeadbeef, 0)
    table += key('Repeat') + struct.pack('<Ii', 123, 0)
    for alias, source_hash in added:
        table += key(alias, not alias.isascii()) + struct.pack('<Ii', source_hash, 0)
    table += key('Other', True) + struct.pack('<I', 1)
    table += key('Key') + struct.pack('<Ii', 456, 1)
    pool = bytearray(struct.pack('<I', 3))
    for value, wide, refs in [('Pilz 🍄', True, 2+len(added)), ('', False, 1), ('unused', True, 0)]:
        pool += string(value, wide)
        if version == 3:
            pool += struct.pack('<i', refs)
    header_size = 29 if version == 3 else 25
    header = loc.MAGIC + bytes([version]) + struct.pack('<q', header_size+len(table))
    if version == 3:
        header += struct.pack('<I', 3+len(added))
    return header + table + pool


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

    def test_native_hash_vectors_from_independent_unreallocres_reference(self):
        # Fixed outputs from the upstream C# CityHash implementation, separately
        # compiled during research; no expected value uses our Python algorithm.
        # https://github.com/akintos/UnrealLocres/blob/master/LocresLib/CityHash.cs
        vectors = [('',0), ('A',4090798841), ('NS',2301254463), ('Other',1912752590),
                   ('Key',827375239), ('Quest',4141712023), ('Stage',3126211316),
                   ('Empty',3971747829), ('New',1460575270), ('Repeat',1858927902),
                   ('Alias',664255720), ('Pilz 🍄',1562515376), ('Найти 🍄',2827013474),
                   ('火焰保护',3405809369), ('Übersetzung',3046945790),
                   ('ST_S2BaseGameLocalization',3136070845),
                   ('sid_journal_stage_S2T_Job_RSQ04_C02_RSQ04_C02_Start',2650586000),
                   ('A'*33,186059502), ('火'*65,2694752993)]
        for text, expected in vectors:
            with self.subTest(text=text):
                self.assertEqual(loc.key_hash(text),expected)

    def test_alias_append_matches_independent_bytes_and_preserves_both_formats(self):
        aliases = {'火焰保护':'Repeat', 'New':'Key'}
        for version in (1,3):
            with self.subTest(version=version):
                raw = preservation_fixture(version)
                expected = preservation_fixture(version, [('New',0xdeadbeef),('火焰保护',123)])
                self.assertIs(loc.append_aliases(raw,'NS',{}),raw)
                output = loc.append_aliases(raw,'NS',aliases)
                self.assertEqual(output,expected)
                self.assertEqual(output,loc.append_aliases(raw,'NS',dict(reversed(list(aliases.items())))))
                before, after = loc.read_resource(raw), loc.read_resource(output)
                self.assertEqual({k:after[k] for k in before},before)
                self.assertEqual(after['NS','New'],before['NS','Key'])
                self.assertEqual(after['NS','火焰保护'],before['NS','Repeat'])
                self.assertEqual(after['Other','Key'],(456,''))
                self.assertEqual(len(after),len(before)+2)

    def test_alias_append_rejects_missing_existing_invalid_and_bad_native_hashes(self):
        for version in (1,3):
            raw = preservation_fixture(version)
            for namespace, aliases in [('missing',{'New':'Key'}), ('NS',{'New':'Missing'}),
                                       ('NS',{'Key':'Repeat'}), ('NS',{'':'Key'}),
                                       ('NS',{'New':12}), ('NS',{'bad\0alias':'Key'}),
                                       ('NS',{'New':'Key', 'Alias':'New'})]:
                with self.subTest(version=version,aliases=aliases), self.assertRaises(loc.ResourceError):
                    loc.append_aliases(raw,namespace,aliases)
            for damaged in (raw[:-1], raw+b'junk'):
                with self.assertRaises(loc.ResourceError):
                    loc.append_aliases(damaged,'NS',{'New':'Key'})
        raw = optimized_fixture()
        # Namespace hash at 33; key hash at 48 in this independent tiny fixture.
        for offset in (33,48):
            damaged = bytearray(raw)
            struct.pack_into('<I',damaged,offset,0)
            with self.subTest(hash_offset=offset), self.assertRaisesRegex(loc.ResourceError,'hash'):
                loc.append_aliases(bytes(damaged),'NS',{'New':'Key'})
        with self.assertRaises(loc.ResourceError):
            loc.append_aliases(raw[:-4]+struct.pack('<i',2),'NS',{'New':'Key'})

    def test_alias_append_rejects_invalid_pool_indices_and_duplicate_identities(self):
        raw = optimized_fixture()
        for index in (-1,1,0x7fffffff):
            damaged = bytearray(raw)
            struct.pack_into('<i',damaged,64,index)
            with self.subTest(index=index), self.assertRaises(loc.ResourceError):
                loc.append_aliases(bytes(damaged),'NS',{'New':'Key'})
        # Duplicate the sole serialized key record and update otherwise valid
        # entry counts, pool offset and reference count independently.
        duplicate = bytearray(raw[:68]+raw[48:68]+raw[68:])
        struct.pack_into('<q',duplicate,17,88)
        struct.pack_into('<I',duplicate,25,2)
        struct.pack_into('<I',duplicate,44,2)
        struct.pack_into('<i',duplicate,len(duplicate)-4,2)
        with self.assertRaisesRegex(loc.ResourceError,'Duplicate localization identity'):
            loc.append_aliases(bytes(duplicate),'NS',{'New':'Key'})


class GameResources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pak = self.root/'game.pak'
        self.cultures = ('ar','cs','de','en','es-419','es','fr','it','ja','ko','pl','pt-BR','ru','sr','tr','uk','zh-Hans','zh-Hant')
        self.originals = {'sid_journal_Test_Name':(0,'A job'), 'sid_journal_stage_Test_Start':(0,'Find a mushroom 🍄'),
                          'Unrelated': (123, 'Unchanged 日本語 العربية Україна')}
        self.write_source()
        self.gd = GameData(self.root/'data', source_pak=self.pak)

    def write_source(self):
        files = [(jobs.PREFIX+culture+'/Game.locres', loc.write_resource(jobs.NAMESPACE, {
            key:(h,text+' / '+culture) for key,(h,text) in self.originals.items()}))
            for culture in self.cultures]
        pakfile.write_pak(self.pak, files)

    def test_lazy_default_and_all_installed_languages_preserved(self):
        with patch.object(self.gd,'job_localization_files',side_effect=AssertionError('not lazy')):
            self.assertEqual(build_root_files(self.gd,Settings()),{})
            self.assertEqual(set(build_root_files(self.gd,Settings(no_mouse_smoothing=True))),{'Stalker2/Config/UserInput.ini'})
        files = self.gd.job_localization_files(ALIASES)
        self.assertEqual(set(files), {jobs.PREFIX+c+'/Game.locres' for c in self.cultures})
        for path, raw in files.items():
            self.assertTrue(path.endswith('/Game.locres'))
            culture = path[len(jobs.PREFIX):-len('/Game.locres')]
            entries=loc.read_resource(raw)
            self.assertEqual({k for ns,k in entries},set(ALIASES) | set(self.originals))
            for key, (h, text) in self.originals.items():
                self.assertEqual(entries[jobs.NAMESPACE,key], (h,text+' / '+culture))
            for key,original in ALIASES.items():
                expected=self.originals[original][1]+' / '+culture
                self.assertEqual(entries[jobs.NAMESPACE,key],(0,expected))

    def test_cache_reuse_corruption_and_updated_source(self):
        first=self.gd.job_localization_files(ALIASES)
        with patch.object(loc,'append_aliases',side_effect=AssertionError('cache should avoid rebuilding resources')):
            self.assertEqual(self.gd.job_localization_files(ALIASES),first)
        cache=next((self.gd.dir/'.optional').glob('*.zip'))
        cache.write_bytes(b'broken ZIP')
        self.assertEqual(self.gd.job_localization_files(ALIASES),first)
        self.originals['sid_journal_Test_Name']=(0,'Updated job')
        self.write_source()
        with self.assertRaisesRegex(RuntimeError,'changed'):
            self.gd.job_localization_files(ALIASES)
        reloaded=GameData(self.gd.dir,source_pak=self.pak)
        self.assertNotEqual(reloaded.job_localization_files(ALIASES),first)

    def test_missing_original_or_changed_file_leaves_no_complete_cache(self):
        with self.assertRaises(ValueError):
            self.gd.job_localization_files({**ALIASES,'new':'missing'})
        self.assertFalse(list(self.gd.dir.glob('.optional/*.zip')))
        append=loc.append_aliases
        def changed(raw, namespace, aliases):
            # touch() can keep the same timestamp on fast Windows runners.
            # Advance it explicitly so the test always simulates a changed Pak.
            stamp=self.pak.stat()
            os.utime(self.pak, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000_000))
            self.assertNotEqual(self.gd._pak_stamp(), self.gd._source_stamp)
            return append(raw, namespace, aliases)
        with patch.object(loc,'append_aliases',side_effect=changed), self.assertRaisesRegex(RuntimeError,'changed'):
            self.gd.job_localization_files(ALIASES)
        self.assertFalse(list(self.gd.dir.glob('.optional/*.zip')))

    def test_language_discovery_is_not_a_fixed_list(self):
        self.cultures = ('en', 'de', 'test-Latn')
        self.write_source()
        gd = GameData(self.gd.dir, source_pak=self.pak)
        self.assertEqual(set(gd.job_localization_files(ALIASES)),
                         {jobs.PREFIX+c+'/Game.locres' for c in self.cultures})

    def test_cache_rejects_missing_or_changed_language_and_old_cache(self):
        first = self.gd.job_localization_files(ALIASES)
        cache = next(self.gd.dir.glob('.optional/*.zip'))
        with zipfile.ZipFile(cache) as archive:
            saved = {n: archive.read(n) for n in archive.namelist()}
        for mode in ('missing', 'changed', 'old-format'):
            with self.subTest(mode=mode):
                damaged = dict(saved)
                name = jobs.PREFIX+'zh-Hant/Game.locres'
                if mode == 'missing':
                    del damaged[name]
                elif mode == 'changed':
                    damaged[name] = damaged[name][:-1] + b'x'
                else:
                    manifest = json.loads(damaged['manifest.json'])
                    manifest['identity']['version'] = 1
                    damaged['manifest.json'] = json.dumps(manifest)
                with zipfile.ZipFile(cache, 'w') as archive:
                    for n, raw in damaged.items():
                        archive.writestr(n, raw)
                self.assertEqual(self.gd.job_localization_files(ALIASES), first)

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
