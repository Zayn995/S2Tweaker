"""Exercise menu opt-in, prepared audio, capability checks and desktop state."""
from collections import defaultdict
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import animation_sync, editor_state, gui, sound_sync
from s2tweaker.tweaks import Settings, summarize


class Value:
    def __init__(self, value):
        self.value = self.default = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def reset(self):
        self.value = self.default

    def deselect(self):
        self.value = False


class IngameMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def assets(self, support):
        directory = self.root / 'assets'
        directory.mkdir(exist_ok=True)
        for name in ('runtime.zip', 'profile.sav'):
            shutil.copy2(animation_sync.ASSETS / name, directory / name)
        manifest = json.loads((animation_sync.ASSETS / 'runtime.json').read_text(encoding='utf-8'))
        features = set(manifest.get('features', ())) - {'ingame-menu', 'ingame-menu-presets'}
        if support:
            features.update({'ingame-menu', 'ingame-menu-presets', 'consumable-actions'})
        manifest['features'] = sorted(features)
        (directory / 'runtime.json').write_text(json.dumps(manifest), encoding='utf-8')
        return directory

    def test_opt_in_includes_neutral_visuals_without_activating_disabled_values(self):
        self.assertFalse(animation_sync.enabled(Settings()))
        self.assertEqual(animation_sync.profile_values(Settings()), {})
        settings = Settings(ingame_menu=True, weapon_sway_pct=0, weapon_shot_pct=20)
        self.assertTrue(animation_sync.enabled(settings))
        with patch.object(sound_sync, 'mesh_targets', return_value={'audio.mesh.Test': 1}):
            values = animation_sync.profile_values(settings, object())
        self.assertEqual(values, {
            'menu.enabled': 1, 'menu.sound.weapon': 1, 'menu.sound.movement': 1,
            'action.consumable.medicine': 1, 'action.consumable.food': 1,
            'action.consumable.drink': 1,
            'visual.sway': 2, 'visual.shot': 2, 'audio.enabled': 1,
            'audio.mesh.Test': 1, 'audio.movement': 1, 'audio.walk': 1, 'audio.run': 1,
        })
        self.assertTrue(any('F10' in line for line in summarize(settings)))

    def test_disabled_audio_is_prepared_from_cfg_factors_without_mutating_settings(self):
        settings = Settings(ingame_menu=True, reload_speed_factor=1.5, jam_clear_factor=.75,
                            equip_speed_factor=1.2, walk_speed_factor=.8, run_speed_factor=1.4,
                            weapon_sway_sync=True, weapon_sway_pct=35,
                            weapon_shot_sync=True, weapon_shot_pct=0)
        with patch.object(sound_sync, 'mesh_targets', return_value={
            'audio.mesh.Test': 1, 'audio.equip.Test': 1.2,
        }) as targets:
            values = animation_sync.profile_values(settings, object())
        self.assertEqual(values['audio.reload'], 1.5)
        self.assertEqual(values['audio.jam'], .75)
        self.assertEqual(values['audio.equip.Test'], 1.2)
        self.assertEqual(values['audio.limp.walk'], .8)
        self.assertEqual(values['audio.limp.run'], 1.4)
        self.assertEqual(values['visual.sway'], 1.35)
        self.assertEqual(values['visual.shot'], 1)
        self.assertEqual((values['menu.sound.weapon'], values['menu.sound.movement']), (1, 1))
        prepared = targets.call_args.args[1]
        self.assertTrue(prepared.sound_sync and prepared.movement_sound_sync)
        self.assertFalse(settings.sound_sync or settings.movement_sound_sync)
        self.assertNotIn('movement.walk', values)
        self.assertNotIn('audio.equip', values)

    def test_sound_initial_flags_and_invalid_future_rates(self):
        settings = Settings(ingame_menu=True, sound_sync=True, movement_sound_sync=True)
        with patch.object(sound_sync, 'mesh_targets', return_value={'audio.mesh.Test': 1}):
            values = animation_sync.profile_values(settings, object())
        self.assertEqual((values['menu.sound.weapon'], values['menu.sound.movement']), (2, 2))
        with self.assertRaisesRegex(ValueError, 'reload_speed_factor'):
            animation_sync.profile_values(Settings(ingame_menu=True, reload_speed_factor=5), object())
        with self.assertRaisesRegex(ValueError, 'Load installed game data'):
            animation_sync.profile_values(Settings(ingame_menu=True))

    def test_old_bundle_rejects_menu_before_export_install_or_debug(self):
        settings = Settings(ingame_menu=True)
        with patch.object(animation_sync, 'ASSETS', self.assets(False)):
            for action in (
                lambda: animation_sync.export_files(settings, self.root / 'test.pak'),
                lambda: animation_sync.installation_changes(settings, self.root / 'game', self.root / 'saves'),
                lambda: animation_sync.debug_changes(settings, self.root / 'test.pak', self.root / 'debug'),
            ):
                with self.assertRaisesRegex(ValueError, 'ingame-menu'):
                    action()
        self.assertFalse((self.root / 'game').exists())
        self.assertFalse((self.root / 'debug').exists())
        self.assertEqual(animation_sync.required_runtime_features(
            Settings(ingame_menu=True, consumable_food_speed=2)), {'ingame-menu', 'ingame-menu-presets', 'consumable-actions'})

    def test_capable_bundle_exports_matching_debug_and_install_profiles(self):
        # This synthetic declaration checks routing, not native bundle behavior.
        settings = Settings(ingame_menu=True)
        with patch.object(animation_sync, 'ASSETS', self.assets(True)), \
                patch.object(sound_sync, 'mesh_targets', return_value={'audio.mesh.Test': 1}):
            files = animation_sync.export_files(settings, self.root / 'test.pak', gd=object())
            profile = files['Profile/' + animation_sync.PROFILE_SLOT + '.sav']
            installed = animation_sync.installation_changes(settings, self.root / 'game', self.root / 'saves', gd=object())
            self.assertEqual(installed[self.root / 'saves' / (animation_sync.PROFILE_SLOT + '.sav')], profile)
            debug = animation_sync.debug_changes(settings, self.root / 'test.pak', self.root / 'debug', gd=object())
            self.assertIn(profile, debug.values())
            decoded = animation_sync.parse(profile).payload
            self.assertIn('menu.enabled=1', decoded)
            self.assertIn('visual.shot=2', decoded)
            self.assertIn((decoded + '\n').encode(), debug.values())
            with animation_sync.file_transaction(installed):
                pass
            removal = animation_sync.installation_changes(Settings(), self.root / 'game', self.root / 'saves')
            self.assertTrue(removal)
            self.assertTrue(all(value is None for value in removal.values()))

    def test_desktop_checkbox_collection_state_reset_and_remove(self):
        app = Mock()
        app.sliders = defaultdict(lambda: Value(100))
        app.checks = defaultdict(lambda: Value(False))
        app.name_entry = Value('MenuTest')
        for name in ('cat_checks', 'weapon_overrides', 'weapon_calibers', 'weapon_fire_modes',
                     'weapon_ammo_types', 'ammo_overrides', 'scope_overrides', 'armor_overrides',
                     'armor_custom', 'mutant_overrides', 'faction_relations'):
            setattr(app, name, {})
        app._collect_weapon_cats.return_value = {}
        gui.App._build_ingame_menu_control(app, None)
        self.assertEqual(app._check.call_args.args[1], 'ingame_menu')
        self.assertIn('F10', app._check.call_args.args[2])
        self.assertFalse(gui.App._collect(app).ingame_menu)
        app.checks['ingame_menu'].set(True)
        self.assertTrue(gui.App._collect(app).ingame_menu)
        state = editor_state.state_only(gui.App._ui_state(app))
        self.assertTrue(state['checks']['ingame_menu'])
        gui.App._reset_all(app)
        self.assertFalse(app.checks['ingame_menu'].get())
        app.checks['ingame_menu'].set(True)
        app.game_dir = self.root / 'game'
        with patch.object(gui.messagebox, 'showinfo'):
            gui.App._remove_animation_sync(app)
        self.assertFalse(app.checks['ingame_menu'].get())


if __name__ == '__main__':
    unittest.main()
