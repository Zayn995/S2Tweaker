"""Check live baselines, Sprint row identity and composition with existing controls."""
from collections import defaultdict
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, editor_state, gui
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize, _stamina_exhaustion_patch,
                              _corevars_patch, _player_patch)
from test_ingame_menu import Value

OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"


def fixture():
    gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
    gd.__dict__["obj"] = cfgparse.parse("""
Base : struct.begin
   VitalParams : struct.begin
      DegenSuppressionPoints = 40
      StaminaDisableThresholds : struct.begin
         [8] : struct.begin
            Threshold = 150
            RegenerationDelay = 0
            StateTags : struct.begin
               [0] = EStateTag::None
            struct.end
         struct.end
         [3] : struct.begin
            Threshold = 20
            RegenerationDelay = 2
            Extra = 77
            StateTags : struct.begin
               [0] = EStateTag::Sprint
            struct.end
         struct.end
      struct.end
   struct.end
struct.end
Player : struct.begin {refkey=Base}
struct.end
""")
    gd.__dict__["corevars"] = cfgparse.parse("""
Base : struct.begin
   WoundedHealHoldInteractTime = 1.6
struct.end
DefaultConfig : struct.begin {refkey=Base}
struct.end
""")
    return gd


class RecoveryControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")

    def test_neutral_and_installed_values_compose(self):
        self.assertEqual(build_patches(self.gd, Settings()), {})
        settings = Settings(sprint_exhaustion_factor=.5, exhausted_recovery_delay_factor=.5,
                            suppression_recovery_factor=1.5, wounded_help_hold_factor=.5,
                            max_stamina=300, stamina_regen=10, stamina_sprint=.5)
        patches = build_patches(self.gd, settings)
        obj = cfgparse.parse(patches[OBJ])
        self.assertEqual(set(obj.children), {"Player"})
        player = obj.children["Player"]
        vital = player.children["VitalParams"]
        self.assertEqual(vital.values["MaxSP"], "300.0")
        self.assertEqual(vital.values["RegenSP"], "10.0")
        for leaf, factor in (("Threshold", .5), ("RegenerationDelay", .5)):
            value = cfgparse.parse_number(vital.children["StaminaDisableThresholds"].children["[0]"].values[leaf])
            live = cfgparse.parse_number(self.gd.resolve(self.gd.obj, "Player", f"VitalParams.StaminaDisableThresholds.[0].{leaf}"))
            self.assertAlmostEqual(value, live * factor)
        self.assertAlmostEqual(cfgparse.parse_number(vital.values["DegenSuppressionPoints"]),
                               cfgparse.parse_number(self.gd.resolve(self.gd.obj, "Player", "VitalParams.DegenSuppressionPoints"))*1.5)
        self.assertIn("Sprint", player.children["StaminaPerAction"].values)
        core = cfgparse.parse(patches[CORE]).children["DefaultConfig"]
        self.assertEqual(core.values, {"WoundedHealHoldInteractTime": "0.5"})
        self.assertTrue(any("Suppression recovery" in line for line in summarize(settings)))

    def test_inherited_reindexed_rows_preserve_other_state(self):
        gd = fixture()
        before = copy.deepcopy(gd.obj)
        rows = _stamina_exhaustion_patch(gd, Settings(sprint_exhaustion_factor=.5,
                                                    exhausted_recovery_delay_factor=.5))
        self.assertEqual(rows["[3]"], {"Threshold": "10.0", "RegenerationDelay": "1.0", "Extra": "77",
                                       "StateTags": {"[0]": "EStateTag::Sprint"}})
        self.assertEqual(rows["[8]"], {"Threshold": "150", "RegenerationDelay": "0",
                                       "StateTags": {"[0]": "EStateTag::None"}})
        self.assertEqual(gd.obj, before)
        self.assertEqual(_corevars_patch(gd, Settings(wounded_help_hold_factor=.5)),
                         {"DefaultConfig": {"WoundedHealHoldInteractTime": "0.8"}})
        vital = _player_patch(gd, Settings(suppression_recovery_factor=1.5))["Player"]["VitalParams"]
        self.assertEqual(vital, {"DegenSuppressionPoints": "60.0"})

    def test_delay_only_and_zero_baseline(self):
        gd = fixture()
        rows = _stamina_exhaustion_patch(gd, Settings(exhausted_recovery_delay_factor=0))
        self.assertEqual(rows["[3]"]["Threshold"], "20")
        self.assertEqual(rows["[3]"]["RegenerationDelay"], "0.0")
        gd.obj.children["Base"].children["VitalParams"].children["StaminaDisableThresholds"].children["[3]"].values["RegenerationDelay"] = "0"
        self.assertEqual(_stamina_exhaustion_patch(gd, Settings(exhausted_recovery_delay_factor=2)), {})

    def test_ambiguous_missing_and_crossing_fail_explicitly(self):
        for case in ("ambiguous", "missing", "crossing", "invalid"):
            with self.subTest(case=case):
                gd = fixture()
                rows = gd.obj.children["Base"].children["VitalParams"].children["StaminaDisableThresholds"].children
                if case == "ambiguous":
                    rows["[8]"].children["StateTags"].values["[0]"] = "EStateTag::Sprint"
                elif case == "missing":
                    rows["[3]"].children["StateTags"].values["[0]"] = "EStateTag::None"
                elif case == "crossing":
                    rows["[8]"].values["Threshold"] = "25"
                else:
                    rows["[3]"].values["Threshold"] = "nan"
                with self.assertRaises(ValueError):
                    _stamina_exhaustion_patch(gd, Settings(sprint_exhaustion_factor=2))

    def test_invalid_factors_and_missing_baselines(self):
        for factor in (float("nan"), float("inf"), -1, 5):
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                _corevars_patch(fixture(), Settings(wounded_help_hold_factor=factor))
        gd = fixture()
        del gd.corevars.children["Base"].values["WoundedHealHoldInteractTime"]
        with self.assertRaises(ValueError):
            _corevars_patch(gd, Settings(wounded_help_hold_factor=.5))

    def test_desktop_collection_and_saved_state(self):
        app = Mock()
        app.sliders = defaultdict(lambda: Value(100))
        app.checks = defaultdict(lambda: Value(False))
        app.name_entry = Value("RecoveryTest")
        for name in ("cat_checks", "weapon_overrides", "weapon_calibers", "weapon_fire_modes",
                     "weapon_ammo_types", "ammo_overrides", "scope_overrides", "armor_overrides",
                     "armor_custom", "mutant_overrides", "faction_relations"):
            setattr(app, name, {})
        app._collect_weapon_cats.return_value = {}
        mapping = {"sprint_exhaustion": "sprint_exhaustion_factor", "exhausted_delay": "exhausted_recovery_delay_factor",
                   "suppression_recovery": "suppression_recovery_factor", "wounded_hold": "wounded_help_hold_factor"}
        for key, field in mapping.items():
            app.sliders[key].set(50)
            self.assertEqual(getattr(gui.App._collect(app), field), .5)
            state = editor_state.state_only(gui.App._ui_state(app))
            self.assertEqual(state["sliders"][key], 50)
        gui.App._reset_all(app)
        for field in mapping.values():
            self.assertEqual(getattr(gui.App._collect(app), field), 1)


if __name__ == "__main__":
    unittest.main()
