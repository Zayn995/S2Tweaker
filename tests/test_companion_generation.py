"""Exercise standalone native builds and their debug output without GUI windows."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import animation_sync as sync, gui, pakio
from s2tweaker.animation_profile import parse
from s2tweaker.tweaks import Settings


class CompanionGenerationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.saves = self.root / "saves"
        self.app = SimpleNamespace(
            _wb_busy=False, _scan_running=False, gd=object(),
            game_dir=self.root / "game", debug_check=SimpleNamespace(get=lambda: True),
            _collect=Mock(), _save_ui_settings=Mock(),
            _build_manifest=lambda settings, active: json.dumps({"active_tweaks": active}),
        )
        for context in (
            patch.object(gui, "app_dir", return_value=self.root),
            patch.object(gui, "build_patches", return_value={}),
            patch.object(gui, "build_root_files", return_value={}),
            patch.object(gui.messagebox, "showinfo"),
            patch.object(sync, "default_save_dir", return_value=self.saves),
        ):
            context.start()
            self.addCleanup(context.stop)

    def generate(self, settings, *, install=False):
        self.app._collect.return_value = settings
        target = self.root / f"{settings.mod_name}.pak"
        return gui.App._generate(self.app, target, install_animation=install), target

    def debug_root(self, settings):
        return self.root / f"{settings.mod_name}_cfg" / "AnimationSync"

    def test_each_visual_control_builds_and_installs_without_cfg_changes(self):
        for control, value, profile_key, encoded in (
            ("weapon_sway", 0, "visual.sway", 1),
            ("weapon_shot", 37, "visual.shot", 1.37),
        ):
            for install in (False, True):
                with self.subTest(control=control, install=install):
                    settings = Settings(mod_name=f"{control}_{install}", **{
                        control + "_sync": True, control + "_pct": value,
                    })
                    ok, target = self.generate(settings, install=install)
                    self.assertTrue(ok)
                    self.assertEqual(pakio.list_pak(target), [gui.MANIFEST_NAME])
                    debug = self.debug_root(settings)
                    if install:
                        runtime = sync.runtime_files()
                        for name, data in runtime.items():
                            self.assertEqual((self.app.game_dir / name).read_bytes(), data)
                        profile = (self.saves / (sync.PROFILE_SLOT + ".sav")).read_bytes()
                    else:
                        archive_path = target.with_name(target.stem + "_AnimationSync.zip")
                        with zipfile.ZipFile(archive_path) as archive:
                            for name in archive.namelist():
                                self.assertEqual((debug / name).read_bytes(), archive.read(name))
                            profile = archive.read("Profile/" + sync.PROFILE_SLOT + ".sav")
                    self.assertEqual((debug / "Profile" / (sync.PROFILE_SLOT + ".sav")).read_bytes(), profile)
                    decoded = (debug / "Profile" / (sync.PROFILE_SLOT + ".txt")).read_text()
                    self.assertEqual(decoded, parse(profile).payload + "\n")
                    metadata = json.loads((debug / "S2Tweaker_AnimationSync.json").read_text())
                    self.assertEqual(metadata["factors"], {profile_key: encoded})

    def test_debug_also_contains_movement_and_sound_profile(self):
        settings = Settings(mod_name="Movement", animation_sync=True,
                            movement_sound_sync=True, walk_speed_factor=.8, run_speed_factor=1.4)
        with patch.object(gui, "build_patches", return_value={"example.cfg": "Example : struct.begin\nstruct.end\n"}):
            ok, target = self.generate(settings)
        self.assertTrue(ok)
        debug = self.debug_root(settings)
        self.assertTrue((debug.parent / "example.cfg").is_file())
        metadata = json.loads((debug / "S2Tweaker_AnimationSync.json").read_text())
        self.assertEqual(metadata["factors"]["movement.crouch"], .8)
        self.assertEqual(metadata["factors"], sync.profile_values(settings, self.app.gd))
        with zipfile.ZipFile(target.with_name(target.stem + "_AnimationSync.zip")) as archive:
            self.assertEqual((debug / "Profile" / (sync.PROFILE_SLOT + ".sav")).read_bytes(),
                             archive.read("Profile/" + sync.PROFILE_SLOT + ".sav"))

    def test_disabled_companion_clears_stale_debug_but_keeps_notes(self):
        settings = Settings(mod_name="Same", weapon_shot_sync=True, weapon_shot_pct=40)
        self.assertTrue(self.generate(settings)[0])
        debug = self.debug_root(settings)
        notes = debug / "my_notes.txt"
        notes.write_text("keep")
        settings = Settings(mod_name="Same", walk_speed_factor=.8)
        with patch.object(gui, "build_patches", return_value={"example.cfg": "Example : struct.begin\nstruct.end\n"}):
            self.assertTrue(self.generate(settings)[0])
        self.assertEqual([p for p in debug.rglob("*") if p.is_file()], [notes])
        self.assertEqual(notes.read_text(), "keep")

    def test_inactive_visual_settings_and_ineffective_cfg_still_emit_nothing(self):
        for settings in (Settings(), Settings(weapon_shot_sync=True),
                         Settings(weapon_sway_sync=True), Settings(weapon_shot_pct=0),
                         Settings(ammo_piercing_factor=3)):
            with self.subTest(settings=settings):
                ok, target = self.generate(settings)
                self.assertFalse(ok)
                self.assertFalse(target.exists())
                self.assertFalse(self.debug_root(settings).exists())

    def test_standalone_install_rolls_back_if_pak_build_fails(self):
        settings = Settings(weapon_shot_sync=True, weapon_shot_pct=40)
        with patch.object(gui.mod_library, "build_safely", side_effect=OSError("build failed")):
            with self.assertRaisesRegex(OSError, "build failed"):
                self.generate(settings, install=True)
        self.assertFalse(any(p.is_file() for p in self.app.game_dir.rglob("*")))
        self.assertFalse(any(p.is_file() for p in self.saves.rglob("*")))

    def test_debug_failure_does_not_report_a_successful_build_as_failed(self):
        settings = Settings(weapon_shot_sync=True, weapon_shot_pct=40)
        with patch.object(sync, "debug_changes", side_effect=ValueError("invalid debug folder")):
            ok, target = self.generate(settings)
        self.assertTrue(ok)
        self.assertTrue(target.is_file())
        message = gui.messagebox.showinfo.call_args.args[1]
        self.assertIn("Debug export failed", message)
        self.assertIn("invalid debug folder", message)


if __name__ == "__main__":
    unittest.main()
