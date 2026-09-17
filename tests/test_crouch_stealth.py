"""Independent stealth controls, legacy profiles and sparse installed-data patches."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, editor_state, modscan, tweaks
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize

VANILLA = ROOT / "vanilla/Stalker2/Content/GameLite/GameData"


class ProfileMigration(unittest.TestCase):
    def test_old_state_is_copied_and_explicit_new_choices_win(self):
        old = {"sliders": {"stealth_crouch": 235, "stealth_noise": 50}}
        saved = copy.deepcopy(old)
        migrated = editor_state.state_only(old)
        self.assertEqual(migrated["sliders"], {
            "stealth_crouch_sight": 235, "stealth_crouch_sound": 235, "stealth_noise": 50})
        self.assertEqual(old, saved)
        self.assertEqual(editor_state.state_only(migrated), migrated)
        self.assertEqual(editor_state.differences(old, migrated), [])
        explicit = editor_state.migrate_stealth_sliders({
            "stealth_crouch": 200, "stealth_crouch_sight": 100,
            "stealth_crouch_sound": 150})
        self.assertEqual(explicit, {"stealth_crouch_sight": 100, "stealth_crouch_sound": 150})

    def test_profile_file_roundtrip_and_independent_history(self):
        old = {"sliders": {"stealth_crouch": 175}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stealth.json"
            editor_state.save_profile(path, old, "Stealth")
            state = editor_state.read_profile(path).state
            history = editor_state.History(state)
            changed = copy.deepcopy(state)
            changed["sliders"]["stealth_crouch_sound"] = 100
            history.commit(changed)
            self.assertEqual(history.undo(), state)
            self.assertEqual(history.redo(), changed)
            editor_state.save_profile(path, changed, "Stealth")
            self.assertEqual(editor_state.read_profile(path).state, changed)

    def test_partial_pose_fields_are_independent(self):
        gd = GameData(Path("unused"))
        gd.aiglobals = cfgparse.parse("""
AISettings : struct.begin
 CharacterPoseSettings : struct.begin
  [7] : struct.begin
   Pose = EStateTag::Crouch
   VisibilityCoef = 0.6
  struct.end
  [12] : struct.begin
   Pose = EStateTag::LowCrouchInPlace
   NoiseCoef = 0.08
  struct.end
 struct.end
struct.end
""")
        result = tweaks._aiglobals_patch(gd, Settings(crouch_visibility_factor=2, crouch_noise_factor=4))
        self.assertEqual(result, {"AISettings": {"CharacterPoseSettings": {
            "[7]": {"VisibilityCoef": "0.3"}, "[12]": {"NoiseCoef": "0.02"}}}})


@unittest.skipUnless((VANILLA / "ObjPrototypes.cfg").is_file(), "installed game data only")
class InstalledStealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(VANILLA)

    def leaves(self, patches):
        def walk(node, path=()):
            for key, value in node.values.items():
                yield path + (key,), value
            for key, child in node.children.items():
                yield from walk(child, path + (key,))
        return {(name, path): value for name, text in patches.items()
                for path, value in walk(cfgparse.parse(text))}

    def test_separate_exports_have_disjoint_fields_and_compose(self):
        sight = build_patches(self.gd, Settings(crouch_visibility_factor=2))
        sound = build_patches(self.gd, Settings(crouch_noise_factor=4))
        sight_fields, sound_fields = self.leaves(sight), self.leaves(sound)
        self.assertEqual(len(sight_fields), 3)
        self.assertEqual(len(sound_fields), 3)
        self.assertTrue(all(path[-1].startswith("Visibility") for _, path in sight_fields))
        self.assertTrue(all(path[-1].startswith("Noise") for _, path in sound_fields))
        self.assertFalse(sight_fields.keys() & sound_fields.keys())
        self.assertFalse(modscan.pairs_from_patches(sight) & modscan.pairs_from_patches(sound))
        combined = build_patches(self.gd, Settings(crouch_visibility_factor=2, crouch_noise_factor=4))
        self.assertEqual(self.leaves(combined), sight_fields | sound_fields)
        self.assertEqual(self.leaves(combined), sound_fields | sight_fields)
        for field, expected in (("crouch_visibility_factor", "Crouch visual stealth"),
                                ("crouch_noise_factor", "Crouch sound stealth")):
            self.assertTrue(any(expected in text for text in summarize(Settings(**{field: 2}))))

    def test_legacy_output_is_preserved_at_all_original_slider_steps(self):
        self.assertEqual(build_patches(self.gd, Settings()), {})
        for percentage in range(25, 401, 5):
            factor = percentage / 100
            old = Settings(crouch_stealth_factor=factor)
            new = Settings(crouch_visibility_factor=factor, crouch_noise_factor=factor)
            self.assertEqual(tweaks._player_patch(self.gd, old), tweaks._player_patch(self.gd, new))
            self.assertEqual(tweaks._aiglobals_patch(self.gd, old), tweaks._aiglobals_patch(self.gd, new))

    def test_other_stealth_controls_do_not_restore_crouch_fields(self):
        options = dict(movement_noise_factor=.5, darkness_factor=.5,
                       vegetation_translucency_factor=.5, surface_noise_overrides={"Grass": .5})
        other = self.leaves(build_patches(self.gd, Settings(**options)))
        crouch = self.leaves(build_patches(self.gd, Settings(crouch_visibility_factor=2, crouch_noise_factor=3)))
        self.assertFalse(other.keys() & crouch.keys())
        combined = self.leaves(build_patches(self.gd, Settings(
            crouch_visibility_factor=2, crouch_noise_factor=3, **options)))
        self.assertEqual(combined, other | crouch)


if __name__ == "__main__":
    unittest.main()
