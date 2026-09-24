"""Check consumable profile bounds, sparse output, and factor independence."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import consumable_sync as sync


class ConsumableSyncTests(unittest.TestCase):
    def settings(self, **changes):
        fields = {field: 1.0 for _, field in sync.PROFILE_FIELDS}
        fields.update(changes)
        return SimpleNamespace(**fields)

    def test_neutral_and_missing_settings_emit_nothing(self):
        for settings in (self.settings(), SimpleNamespace()):
            self.assertEqual(sync.profile_values(settings), {})
            self.assertFalse(sync.enabled(settings))

    def test_each_category_is_independent_and_supports_fine_steps(self):
        for key, field in sync.PROFILE_FIELDS:
            with self.subTest(field=field):
                settings = self.settings(**{field: 1.1375})
                self.assertEqual(sync.profile_values(settings), {key: 1.1375})
                self.assertTrue(sync.enabled(settings))

    def test_inclusive_bounds(self):
        for value in (0.25, 4, 4.0):
            settings = self.settings(**{field: value for _, field in sync.PROFILE_FIELDS})
            self.assertEqual(sync.profile_values(settings),
                             {key: value for key, _ in sync.PROFILE_FIELDS})

    def test_invalid_values_are_rejected_for_each_category(self):
        invalid = (None, True, False, "1", float("nan"), float("inf"),
                   -float("inf"), -1, 0, 0.249999, 4.000001, 10**1000)
        for key, field in sync.PROFILE_FIELDS:
            for value in invalid:
                with self.subTest(field=field, value=value):
                    settings = self.settings(**{field: value})
                    with self.assertRaisesRegex(ValueError, field):
                        sync.profile_values(settings)
                    with self.assertRaisesRegex(ValueError, field):
                        sync.enabled(settings)

    def test_neutral_tolerance_matches_existing_profile_helpers(self):
        self.assertEqual(sync.profile_values(self.settings(
            consumable_medicine_speed=1.0 + 5e-10)), {})
        self.assertEqual(sync.profile_values(self.settings(
            consumable_medicine_speed=1.00001)),
            {"action.consumable.medicine": 1.00001})

    def test_unrelated_speed_and_sync_settings_do_not_change_action_rate(self):
        settings = self.settings(consumable_drink_speed=1.7,
                                 inventory_action_factor=3.0,
                                 reload_speed_factor=2.0,
                                 walk_speed_factor=0.5,
                                 animation_sync=False,
                                 sound_sync=False)
        self.assertEqual(sync.profile_values(settings), {"action.consumable.drink": 1.7})
        self.assertEqual(settings.inventory_action_factor, 3.0)
        self.assertTrue(sync.enabled(settings))


if __name__ == "__main__":
    unittest.main()
