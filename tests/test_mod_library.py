"""Real generated Pak readback, backups, restore and own-mod comparisons."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import mod_library as library, pakio
from s2tweaker.editor_preview import base_file, describe_output
from s2tweaker import cfgparse
from s2tweaker.tweaks import Settings


def manifest(name="Sample"):
    return {library.MANIFEST: json.dumps({"tool": "S2Tweaker test", "manifest_version": 1,
        "mod_name": name, "ui_state": {"sliders": {"hp": 200}}})}


def cfg(value):
    return f"Player : struct.begin {{bpatch}}\n VitalParams : struct.begin {{bpatch}}\n MaxHP = {value}\n struct.end\nstruct.end\n"


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.history = self.root / "history"
        self.target = self.root / "sample.pak"

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, value=200, path=None):
        return library.build_safely({"ObjPrototypes/Own.cfg": cfg(value)}, path or self.target,
                                     manifest(), self.history)

    def test_build_and_overwrite_retains_previous_bytes(self):
        self.assertIsNone(self.build())
        old = self.target.read_bytes()
        backup = self.build(300)
        self.assertEqual(backup.read_bytes(), old)
        self.assertNotEqual(self.target.read_bytes(), old)
        self.assertEqual(library.read_own_mod(self.target).name, "Sample")

    def test_bad_build_does_not_replace_original(self):
        self.build()
        old = self.target.read_bytes()
        with patch.object(pakio, "pack_mod", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.build(300)
        self.assertEqual(self.target.read_bytes(), old)

    def test_backup_failure_prevents_replacement(self):
        self.build()
        old = self.target.read_bytes()
        with patch.object(library, "backup_pak", side_effect=OSError("no space")):
            with self.assertRaises(OSError):
                self.build(300)
        self.assertEqual(self.target.read_bytes(), old)

    def test_restore_retains_overwritten_destination(self):
        self.build()
        first = self.target.read_bytes()
        backup = self.build(300)
        second = self.target.read_bytes()
        retained = library.restore_pak(backup, self.target, self.history)
        self.assertEqual(self.target.read_bytes(), first)
        self.assertEqual(retained.read_bytes(), second)

    def test_refuses_executable_output_and_foreign_restore(self):
        with self.assertRaises(ValueError):
            self.build(path=self.root / "S2Tweaker.exe")
        foreign = self.root / "foreign.pak"
        pakio.pack_mod({"Other.cfg": cfg(1)}, foreign)
        with self.assertRaises(ValueError):
            library.restore_pak(foreign, self.target, self.history)

    def test_inventory_ignores_foreign_and_deduplicates_roots(self):
        self.build()
        pakio.pack_mod({"Other.cfg": cfg(1)}, self.root / "foreign.pak")
        mods, errors = library.list_own_mods([self.root, self.root])
        self.assertEqual([mod.path for mod in mods], [self.target])
        self.assertEqual(errors, [])

    def test_exact_overlap_and_disjoint_targets(self):
        self.build()
        other = self.root / "other.pak"
        pakio.pack_mod({"ObjPrototypes/Another.cfg": cfg(300)}, other, root_files=manifest("Other"))
        overlap = library.compare_own_mods(self.target, other)
        self.assertEqual(len(overlap), 1)
        self.assertEqual(overlap[0][1:], ("200", "300"))
        pakio.pack_mod({"ObjPrototypes/Another.cfg": cfg(300).replace("MaxHP", "MaxSP")}, other, root_files=manifest())
        self.assertEqual(library.compare_own_mods(self.target, other), [])

    def test_dlc_and_ini_roundtrip(self):
        files = {"//DLCGameData/Test/Own.cfg": cfg(2)}
        roots = {**manifest(), "Stalker2/Config/UserInput.ini": "[/Script/Engine.InputSettings]\nbEnableMouseSmoothing=False\n"}
        library.build_safely(files, self.target, roots, self.history)
        targets = library.own_patch_targets(self.target)
        self.assertEqual(len(targets), 2)

    def test_unbinarized_patch_families_remain_distinct(self):
        other = self.root / "other.pak"
        pakio.pack_mod({"CoreVariables.cfg_patch_First.cfg": "Value = 1\n"}, self.target, root_files=manifest())
        pakio.pack_mod({"OtherVariables.cfg_patch_Second.cfg": "Value = 2\n"}, other, root_files=manifest())
        self.assertEqual(library.compare_own_mods(self.target, other), [])
        pakio.pack_mod({"CoreVariables.cfg_patch_Second.cfg": "Value = 2\n"}, other, root_files=manifest())
        self.assertEqual(len(library.compare_own_mods(self.target, other)), 1)

    def test_preview_resolves_top_level_original_values(self):
        source = self.root / "CoreVariables.cfg"
        root = cfgparse.parse("Value = 100\n", root_name=str(source))
        gd = SimpleNamespace(dir=self.root, core=root)
        with patch("s2tweaker.editor_preview.build_patches", return_value={"CoreVariables.cfg_patch_Own.cfg": "Value = 250\n"}):
            self.assertIn("Value: 100 → 250", describe_output(gd, Settings()))

    def test_preview_baseline_paths(self):
        self.assertEqual(base_file("ObjPrototypes/Own.cfg"), "ObjPrototypes.cfg")
        self.assertEqual(base_file("WeaponData/CharacterWeaponSettingsPrototypes/Own.cfg"), "WeaponData/CharacterWeaponSettingsPrototypes.cfg")
        self.assertEqual(base_file("CoreVariables.cfg_patch_Own.cfg"), "CoreVariables.cfg")
        self.assertIsNone(base_file("//DLCGameData/Test/Own.cfg"))

    def test_preview_uses_already_cached_large_original(self):
        source = self.root / "ObjPrototypes.cfg"
        source.write_bytes(b" " * (6 * 1024 * 1024))
        root = cfgparse.parse(cfg(100), root_name=str(source))
        gd = SimpleNamespace(dir=self.root, obj=root,
            resolve=lambda tree, sid, key: tree.children[sid].get(key))
        with patch("s2tweaker.editor_preview.build_patches", return_value={"ObjPrototypes/Own.cfg": cfg(250)}):
            text = describe_output(gd, Settings(max_hp=250))
        self.assertIn("MaxHP: 100 → 250", text)

    def test_preview_does_not_invent_missing_original(self):
        gd = SimpleNamespace(dir=self.root)
        with patch("s2tweaker.editor_preview.build_patches", return_value={"ObjPrototypes/Own.cfg": cfg(250)}):
            text = describe_output(gd, Settings(max_hp=250))
        self.assertIn("[new or unresolved base] → 250", text)
        with patch("s2tweaker.editor_preview.build_patches", return_value={}):
            self.assertIn("No effective patch", describe_output(gd, Settings()))


if __name__ == "__main__":
    unittest.main()
