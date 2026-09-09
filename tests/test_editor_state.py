"""History/profile regressions; no windows or game installation required."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import editor_state as state


class HistoryTests(unittest.TestCase):
    def test_snapshot_does_not_alias_live_overrides(self):
        original = {"weapon_overrides": {"Gun": {"damage": 2}}}
        history = state.History(original)
        original["weapon_overrides"]["Gun"]["damage"] = 3
        history.commit(original)
        original["weapon_overrides"]["Gun"].clear()
        self.assertEqual(history.undo()["weapon_overrides"]["Gun"]["damage"], 2)
        self.assertEqual(history.redo()["weapon_overrides"]["Gun"]["damage"], 3)

    def test_branching_discards_redo(self):
        history = state.History({"n": 0})
        history.commit({"n": 1})
        history.commit({"n": 2})
        history.undo()
        history.commit({"n": 3})
        self.assertIsNone(history.redo())
        self.assertEqual(history.undo(), {"n": 1})

    def test_noop_and_bounded_history(self):
        history = state.History({"n": 0}, limit=2)
        self.assertFalse(history.commit({"n": 0}))
        for n in range(1, 5):
            history.commit({"n": n})
        self.assertEqual(len(history.past), 2)
        self.assertEqual(history.undo(), {"n": 3})
        self.assertEqual(history.undo(), {"n": 2})
        self.assertIsNone(history.undo())


class ProfileTests(unittest.TestCase):
    def test_old_profile_and_new_metadata_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            raw = {"sliders": {"hp": 250}, "checks": {"a": True}}
            path.write_text(json.dumps(raw), encoding="utf-8")
            old = state.read_profile(path)
            state.save_profile(path, old.state, "Survival", "Low loot", "MyMod")
            new = state.read_profile(path)
            self.assertEqual(new.state, old.state)
            self.assertEqual((new.name, new.description, new.mod_name), ("Survival", "Low loot", "MyMod"))
            self.assertEqual(json.loads(path.read_text())["sliders"], {"hp": 250})

    def test_missing_neutral_and_zero_override(self):
        defaults = {"sliders": {"hp": 100}, "checks": {"a": False}, "cats": {"food": True}}
        self.assertEqual(state.differences({}, defaults, defaults), [])
        changed = {**defaults, "mutant_overrides": {"Boar": {"regen": 0}}}
        self.assertEqual(state.differences(defaults, changed, defaults),
                         [(("mutant_overrides", "Boar", "regen"), 1.0, 0)])

    def test_reject_bad_values_and_shapes(self):
        for bad in ([], {"sliders": []}, {"sliders": {"hp": float("nan")}},
                    {"sliders": {"hp": float("inf")}}, {"checks": {"a": "false"}},
                    {"weapon_overrides": {"Gun": 5}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                state.state_only(bad)

    def test_unique_names_cannot_escape_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            first = state.unique_profile_path(directory, "../../Profile")
            first.touch()
            second = state.unique_profile_path(directory, "../../Profile")
            self.assertEqual(first.parent, Path(directory))
            self.assertNotEqual(first, second)

    def test_failed_serialization_preserves_existing_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            state.write_json(path, {"good": 1})
            with self.assertRaises(ValueError):
                state.write_json(path, {"bad": float("nan")})
            self.assertEqual(json.loads(path.read_text()), {"good": 1})


if __name__ == "__main__":
    unittest.main()
