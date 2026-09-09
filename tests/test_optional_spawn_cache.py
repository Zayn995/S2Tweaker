"""Optional spawn data must not inflate a normal user's startup/cache."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import gamedata as data, vendor_bin2cfg as binary, cfgparse
from s2tweaker.loot_extensions import _stash_patches


class OptionalSpawnCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pak = self.root / "game/Stalker2/Content/Paks/pakchunk0-Windows.pak"
        self.pak.parent.mkdir(parents=True)
        self.pak.write_bytes(b"synthetic game pak")
        self.gd = data.GameData(self.root / "cache/data", source_pak=self.pak)

    def unpack(self, pak, folder, *, include, progress=None):
        self.assertEqual(include, data.GAMEDATA_REL + "/" + data.OPTIONAL_SPAWN)
        output = Path(folder) / include
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"synthetic spawn")

    def roots(self):
        other = binary.Node("NPC")
        other["SpawnType"] = "ESpawnType::NPC"
        container = binary.Node("Stash")
        container["SpawnType"] = "ESpawnType::ItemContainer"
        container["LevelName"] = "WorldMap_WP"
        container["ItemGeneratorSettings"] = binary.Node("ItemGeneratorSettings")
        inherited = binary.Node("InheritedContainer")
        inherited["SpawnType"] = "ESpawnType::ItemContainer"
        inherited.__internal__.refkey = "Stash"
        for root in (other, container, inherited):
            root.__internal__.isRoot = True
        return [other, container, inherited]

    def test_normal_cache_never_extracts_or_converts_spawn(self):
        self.assertNotIn(data.OPTIONAL_SPAWN, data.NEEDED_FILES)
        self.assertGreater(data.CACHE_SCHEMA, 24)
        requested = []
        def unpack(pak, folder, *, include, progress=None):
            requested.append(include)
            file = Path(folder) / include
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"synthetic cfg")
        with patch.object(data.pakio, "unpack", side_effect=unpack), patch.object(
                binary, "read_binary_cfg", return_value=[]):
            gd = data.GameData.from_game(self.root / "game", self.root / "normal-cache")
        self.assertEqual(len(requested), len(data.NEEDED_FILES))
        self.assertFalse(any("SpawnActor" in name for name in requested))
        self.assertFalse((gd.dir / ".optional").exists())

    def test_default_stashes_do_not_request_optional_data(self):
        with patch.object(self.gd, "stash_spawn_source", side_effect=AssertionError("must remain lazy")):
            self.assertEqual(_stash_patches(self.gd, {}), ({}, {}))

    def test_optional_cache_is_compact_reused_and_not_a_full_vanilla_file(self):
        roots = self.roots()
        with patch.object(data.pakio, "unpack", side_effect=self.unpack) as unpack, patch.object(
                binary, "iter_binary_cfg", side_effect=lambda _: iter(roots)):
            source = self.gd.stash_spawn_source()
            self.assertEqual(self.gd.stash_spawn_source(), source)
            unpack.assert_called_once()
        parsed = cfgparse.parse_file(source)
        self.assertEqual(set(parsed.children), {"Stash", "InheritedContainer"})
        self.assertIn("refkey=Stash", parsed.children["InheritedContainer"].attrs)
        self.assertFalse((self.gd.dir / "SpawnActorPrototypes.cfg").exists())
        self.assertEqual(list((self.gd.dir / ".optional").iterdir()), [source])

    def test_failed_conversion_leaves_no_cache_or_large_binary_and_can_retry(self):
        def broken(_):
            yield self.roots()[1]
            raise ValueError("truncated source")
        with patch.object(data.pakio, "unpack", side_effect=self.unpack), patch.object(
                binary, "iter_binary_cfg", side_effect=broken):
            with self.assertRaisesRegex(ValueError, "truncated"):
                self.gd.stash_spawn_source()
        self.assertEqual(list((self.gd.dir / ".optional").iterdir()), [])
        with patch.object(data.pakio, "unpack", side_effect=self.unpack), patch.object(
                binary, "iter_binary_cfg", side_effect=lambda _: iter(self.roots())):
            self.assertTrue(self.gd.stash_spawn_source().is_file())

    def test_game_update_during_extraction_refuses_stale_optional_index(self):
        def changed(_):
            self.pak.write_bytes(b"updated game")
            yield from self.roots()
        with patch.object(data.pakio, "unpack", side_effect=self.unpack), patch.object(
                binary, "iter_binary_cfg", side_effect=changed):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                self.gd.stash_spawn_source()
        self.assertFalse(list((self.gd.dir / ".optional").iterdir()))
        with self.assertRaisesRegex(RuntimeError, "changed"):
            self.gd.stash_spawn_source()

    def test_existing_developer_data_is_used_without_extraction(self):
        self.gd.dir.mkdir(parents=True)
        full = self.gd.dir / "SpawnActorPrototypes.cfg"
        full.write_text("developer fixture", encoding="utf-8")
        with patch.object(data.pakio, "unpack", side_effect=AssertionError("must use existing data")):
            self.assertEqual(data.GameData(self.gd.dir).stash_spawn_source(), full)


if __name__ == "__main__":
    unittest.main()
