"""Exercise the native profile, portable export and reversible installation."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import animation_sync as sync
from s2tweaker.animation_profile import parse
from s2tweaker.tweaks import Settings


class AnimationSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.game = self.root / "game"
        self.saves = self.root / "saves"
        self.settings = Settings(animation_sync=True, walk_speed_factor=.8, run_speed_factor=1.4)

    def changes(self, settings=None):
        return sync.installation_changes(settings or self.settings, self.game, self.saves)

    def apply(self, changes):
        with sync.file_transaction(changes):
            pass

    def test_disabled_and_neutral_emit_nothing(self):
        for s in (Settings(), Settings(animation_sync=True), Settings(walk_speed_factor=.8)):
            self.assertEqual(self.changes(s), {})
            self.assertEqual(sync.export_changes(s, self.root / "test.pak"), {})
        self.assertFalse(self.game.exists())

    def test_non_quarter_values_and_strict_native_format(self):
        data = sync.profile_bytes(Settings(animation_sync=True, walk_speed_factor=1.1375, run_speed_factor=1.26))
        self.assertEqual(parse(data).payload, "S2T1\nmovement.crouch=1.1375\nmovement.limp.run=1.26\nmovement.limp.walk=1.1375\nmovement.sprint=1.26")
        for broken in (data[:-1], data + b"\0", data.replace(b"BP_S2TProfile", b"BP_OtherSave0")):
            with self.assertRaises(ValueError):
                parse(broken)
        for value in (float("nan"), float("inf"), 0, -1, 101):
            with self.assertRaises(ValueError):
                sync.profile_bytes(Settings(animation_sync=True, walk_speed_factor=value))

    def test_bundle_checksums_and_export_profile(self):
        runtime = sync.runtime_files()
        self.assertEqual(len(runtime), 7)
        self.assertLess(sum(map(len, runtime.values())), 100_000)
        result = sync.export_changes(self.settings, self.root / "my_mod.pak")
        data = next(iter(result.values()))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertTrue(set(runtime).issubset(archive.namelist()))
            profile = archive.read("Profile/" + sync.PROFILE_SLOT + ".sav")
            self.assertEqual(parse(profile).payload, "S2T1\nmovement.crouch=0.8\nmovement.limp.run=1.4\nmovement.limp.walk=0.8\nmovement.sprint=1.4")
            self.assertEqual(json.loads(archive.read("S2Tweaker_AnimationSync.json"))["cfg_pak"], "my_mod.pak")

    def test_install_update_disable_preserves_campaign_saves(self):
        self.saves.mkdir()
        campaign = self.saves / "CampaignSave.sav"
        campaign.write_bytes(b"untouched player progress")
        self.apply(self.changes())
        profile = self.saves / (sync.PROFILE_SLOT + ".sav")
        self.assertIn("movement.crouch=0.8", parse(profile.read_bytes()).payload)
        self.apply(self.changes(Settings(animation_sync=True, walk_speed_factor=1.1)))
        self.assertEqual(parse(profile.read_bytes()).payload, "S2T1\nmovement.crouch=1.1\nmovement.limp.run=1\nmovement.limp.walk=1.1")
        self.apply(self.changes(Settings()))
        self.assertFalse(profile.exists())
        self.assertFalse(any(p.is_file() for p in self.game.rglob("*")))
        self.assertEqual(campaign.read_bytes(), b"untouched player progress")

    def test_modified_companion_and_unrelated_profile_rejected(self):
        self.apply(self.changes())
        target = next(p for p in self.game.rglob("*.utoc"))
        target.write_bytes(b"external modification")
        with self.assertRaises(ValueError):
            self.changes(Settings())
        self.assertEqual(target.read_bytes(), b"external modification")

    def test_wrong_profile_class_is_not_overwritten(self):
        self.saves.mkdir()
        target = self.saves / (sync.PROFILE_SLOT + ".sav")
        target.write_bytes(b"unrelated data")
        with self.assertRaises(ValueError):
            self.changes()
        self.assertEqual(target.read_bytes(), b"unrelated data")

    def test_cfg_build_failure_rolls_back_companion(self):
        self.apply(self.changes())
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(OSError, "CFG build failed"):
            with sync.file_transaction(self.changes(Settings(animation_sync=True, run_speed_factor=1.2))):
                raise OSError("CFG build failed")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_export_can_be_removed_without_touching_other_zip(self):
        out = self.root / "example.pak"
        self.apply(sync.export_changes(self.settings, out))
        self.apply(sync.export_changes(Settings(), out))
        self.assertFalse(list(self.root.glob("*.zip")))
        foreign = self.root / "example_AnimationSync.zip"
        foreign.write_bytes(b"unrelated archive")
        with self.assertRaises(zipfile.BadZipFile):
            sync.export_changes(self.settings, out)
        self.assertEqual(foreign.read_bytes(), b"unrelated archive")

    def test_receipt_cannot_escape_game_root(self):
        path = self.game / sync.RECEIPT
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"format": sync.FORMAT, "files": {"../../outside": "hash"}}))
        with self.assertRaises(ValueError):
            self.changes()


if __name__ == "__main__":
    unittest.main()
