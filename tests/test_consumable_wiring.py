"""Check consumable desktop/profile wiring without opening a window or game."""
from collections import defaultdict
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import animation_sync, consumable_sync, editor_state, gui
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize


class Value:
    def __init__(self, value):
        self.value = self.default = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def reset(self):
        self.value = self.default


class ConsumableWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def assets(self, support):
        directory = self.root / "assets"
        directory.mkdir(exist_ok=True)
        for name in ("runtime.zip", "profile.sav"):
            shutil.copy2(animation_sync.ASSETS / name, directory / name)
        manifest = json.loads((animation_sync.ASSETS / "runtime.json").read_text(encoding="utf-8"))
        features = set(manifest.get("features", ())) - {"consumable-actions"}
        if support:
            features.add("consumable-actions")
        manifest["features"] = sorted(features)
        (directory / "runtime.json").write_text(json.dumps(manifest), encoding="utf-8")
        return directory

    def test_settings_defaults_and_independent_profile_merge(self):
        self.assertFalse(animation_sync.enabled(Settings()))
        settings = Settings(consumable_food_speed=1.1375, weapon_sway_sync=True, weapon_sway_pct=50)
        self.assertTrue(animation_sync.enabled(settings))
        self.assertEqual(animation_sync.profile_values(settings),
                         {"action.consumable.food": 1.1375, "visual.sway": 1.5})
        self.assertEqual(animation_sync.parse(animation_sync.profile_bytes(settings)).payload,
                         "S2T1\naction.consumable.food=1.1375\nvisual.sway=1.5")
        self.assertIn("Eating speed (native companion, experimental) × 1.1375", summarize(settings))
        self.assertFalse(any("Medicine use" in line for line in summarize(settings)))

    def test_old_bundle_rejects_consumables_before_export_or_install(self):
        settings = Settings(consumable_medicine_speed=1.5)
        with patch.object(animation_sync, "ASSETS", self.assets(False)):
            with self.assertRaisesRegex(ValueError, "consumable-actions"):
                animation_sync.export_files(settings, self.root / "test.pak")
            with self.assertRaisesRegex(ValueError, "consumable-actions"):
                animation_sync.installation_changes(settings, self.root / "game", self.root / "saves")
            self.assertTrue(animation_sync.export_files(
                Settings(weapon_shot_sync=True, weapon_shot_pct=50), self.root / "other.pak"))
        self.assertFalse((self.root / "game").exists())
        self.assertFalse((self.root / "saves").exists())

    def test_capable_manifest_routes_same_profile_to_all_exports(self):
        # A synthetic capability declaration exercises Python routing only.
        # It does not validate the native contents of the copied test bundle.
        settings = Settings(consumable_medicine_speed=0.25, consumable_drink_speed=4)
        expected = {"action.consumable.drink": 4, "action.consumable.medicine": 0.25}
        with patch.object(animation_sync, "ASSETS", self.assets(True)):
            files = animation_sync.export_files(settings, self.root / "test.pak")
            profile = files["Profile/" + animation_sync.PROFILE_SLOT + ".sav"]
            self.assertEqual(json.loads(files["S2Tweaker_AnimationSync.json"])["factors"], expected)
            changes = animation_sync.installation_changes(settings, self.root / "game", self.root / "saves")
            self.assertEqual(changes[self.root / "saves" / (animation_sync.PROFILE_SLOT + ".sav")], profile)
            debug = animation_sync.debug_changes(settings, self.root / "test.pak", self.root / "debug")
            self.assertIn(profile, debug.values())
            self.assertIn("action.consumable.drink=4", animation_sync.parse(profile).payload)

    def app_without_widgets(self):
        app = Mock()
        app.sliders = defaultdict(lambda: Value(100))
        app.checks = defaultdict(lambda: Value(False))
        app.name_entry = Value("ConsumableTest")
        for name in ("cat_checks", "weapon_overrides", "weapon_calibers", "weapon_fire_modes",
                     "weapon_ammo_types", "ammo_overrides", "scope_overrides", "armor_overrides",
                     "armor_custom", "mutant_overrides", "faction_relations"):
            setattr(app, name, {})
        app._collect_weapon_cats.return_value = {}
        def slider(parent, key, label, low, high, step, default, formatter, hint):
            app.sliders[key] = Value(default)
        app._slider.side_effect = slider
        gui.App._build_consumable_controls(app, None)
        return app

    def test_desktop_collection_persistence_and_companion_removal(self):
        app = self.app_without_widgets()
        keys = ("cons_medicine_speed", "cons_food_speed", "cons_drink_speed")
        self.assertEqual(consumable_sync.profile_values(gui.App._collect(app)), {})
        for key, percent in zip(keys, (25, 137.5, 400)):
            app.sliders[key].set(percent)
        settings = gui.App._collect(app)
        expected = {"action.consumable.medicine": 0.25,
                    "action.consumable.food": 1.375,
                    "action.consumable.drink": 4.0}
        self.assertEqual(consumable_sync.profile_values(settings), expected)
        state = editor_state.state_only(gui.App._ui_state(app))
        self.assertEqual({key: state["sliders"][key] for key in keys},
                         dict(zip(keys, (25, 137.5, 400))))
        for call in app._slider.call_args_list:
            self.assertEqual(call.args[3:7], (25, 400, 5, 100))
        app.game_dir = self.root / "game"
        with patch.object(gui.messagebox, "showinfo"):
            gui.App._remove_animation_sync(app)
        self.assertEqual(consumable_sync.profile_values(gui.App._collect(app)), {})
        app._save_ui_settings.assert_called_once()

    @unittest.skipUnless((ROOT / "vanilla/Stalker2/Content/GameLite/GameData").exists(),
                         "requires local game snapshot")
    def test_consumables_do_not_change_cfg_or_inventory_action_factor(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        fields = dict(consumable_medicine_speed=2, consumable_food_speed=0.5, consumable_drink_speed=4)
        self.assertEqual(build_patches(gd, Settings(**fields)), {})
        self.assertEqual(build_patches(gd, Settings(inventory_action_factor=1.5, **fields)),
                         build_patches(gd, Settings(inventory_action_factor=1.5)))


if __name__ == "__main__":
    unittest.main()
