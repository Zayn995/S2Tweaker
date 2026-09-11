"""Independent maximum talk distance, old profiles and live per-NPC baselines."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, _dialog_distance_values, _npc_dialog_patch, build_patches


class DialogRange(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name)
        (folder / "ObjPrototypes.cfg").write_text('''Player : struct.begin
MinDialogInteractDistance = 43
MaxDialogInteractDistance = 137
struct.end
TestHuman : struct.begin
Faction = TestFaction
MinDialogInteractDistance = 71.f
MaxDialogInteractDistance = 263.f
struct.end
MissingMax : struct.begin
Faction = TestFaction
MinDialogInteractDistance = 50
struct.end
''', encoding="utf-8")
        self.gd = GameData(folder)

    def test_neutral_never_resolves_game_data(self):
        self.assertEqual(_dialog_distance_values(object(), Settings(), "Player"), {})
        self.assertEqual(_npc_dialog_patch(object(), Settings()), {})

    def test_maximum_only_keeps_minimum_absent(self):
        settings = Settings(dialog_max_range_factor=2)
        self.assertEqual(_dialog_distance_values(self.gd, settings, "Player"),
                         {"MaxDialogInteractDistance": "274.0"})
        self.assertEqual(_npc_dialog_patch(self.gd, settings),
                         {"TestHuman": {"MaxDialogInteractDistance": "526.0f"}})

    def test_old_settings_keep_both_distances(self):
        settings = Settings(**json.loads('{"dialog_range_factor": 1.5}'))
        self.assertEqual(settings.dialog_max_range_factor, 1)
        self.assertEqual(_dialog_distance_values(self.gd, settings, "Player"),
                         {"MinDialogInteractDistance": "64.5", "MaxDialogInteractDistance": "205.5"})
        self.assertEqual(_npc_dialog_patch(self.gd, settings)["TestHuman"],
                         {"MinDialogInteractDistance": "106.5f", "MaxDialogInteractDistance": "394.5f"})

    def test_combined_factors_apply_once(self):
        settings = Settings(dialog_range_factor=1.5, dialog_max_range_factor=2)
        self.assertEqual(_dialog_distance_values(self.gd, settings, "TestHuman"),
                         {"MinDialogInteractDistance": "106.5f", "MaxDialogInteractDistance": "789.0f"})

    def test_cancelled_maximum_is_omitted(self):
        settings = Settings(dialog_range_factor=.5, dialog_max_range_factor=2)
        self.assertEqual(_dialog_distance_values(self.gd, settings, "Player"),
                         {"MinDialogInteractDistance": "21.5"})

    def test_missing_or_zero_values_are_not_invented(self):
        settings = Settings(dialog_max_range_factor=2)
        self.assertEqual(_dialog_distance_values(self.gd, settings, "MissingMax"), {})
        self.gd.obj.children["MissingMax"].values["MaxDialogInteractDistance"] = "0"
        self.assertEqual(_dialog_distance_values(self.gd, settings, "MissingMax"), {})

    def test_invalid_extension_rejected(self):
        for value in (-1, 0, .99, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _dialog_distance_values(self.gd, Settings(dialog_max_range_factor=value), "Player")

    def test_conflict_scan_only_uses_supported_factors(self):
        from s2tweaker.gui import footprint_settings
        probes = footprint_settings("dialog_max_range")
        self.assertTrue(probes)
        for settings in probes:
            self.assertGreater(settings.dialog_max_range_factor, 1)
            self.assertEqual(set(_dialog_distance_values(self.gd, settings, "Player")),
                             {"MaxDialogInteractDistance"})

    @unittest.skipUnless((ROOT / "vanilla/Stalker2/Content/GameLite/GameData").is_dir(), "Local game data only")
    def test_live_full_patch_only_changes_maximum_on_humans_and_player(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        self.assertEqual(build_patches(gd, Settings()), {})
        patches = build_patches(gd, Settings(dialog_max_range_factor=1.8))
        self.assertEqual(set(patches), {"ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"})
        tree = cfgparse.parse(next(iter(patches.values())))
        expected = {"Player", *gd.human_npc_sids()}
        self.assertEqual(set(tree.children), expected)
        for sid, node in tree.children.items():
            self.assertEqual(set(node.values), {"MaxDialogInteractDistance"}, sid)
            baseline = cfgparse.parse_number(gd.resolve(gd.obj, sid, "MaxDialogInteractDistance"))
            self.assertAlmostEqual(cfgparse.parse_number(node.values["MaxDialogInteractDistance"]), baseline * 1.8)


if __name__ == "__main__":
    unittest.main()
