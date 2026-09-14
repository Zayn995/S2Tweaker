"""Verify timing coverage, edition ownership and independent jam controls."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, _weapon_general_patch

DATA = ROOT / 'vanilla/Stalker2/Content/GameLite/GameData'


@unittest.skipUnless(DATA.is_dir(), 'Local game data required')
class ReloadScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(DATA)

    def sources(self):
        yield None, self.gd.weapongeneral
        for edition, trees in self.gd.dlc_editions.items():
            if 'weapongeneral' in trees:
                yield edition, trees['weapongeneral']

    def test_neutral_is_empty(self):
        self.assertEqual(_weapon_general_patch(self.gd, Settings()), ({}, {}))

    def test_all_live_reload_leaves_are_scaled_in_their_own_file(self):
        # Discover keys independently of the implementation's allowlist.
        for factor in (0.625, 1.75):
            base, editions = _weapon_general_patch(self.gd, Settings(reload_speed_factor=factor))
            count, auxiliary, edition_count = 0, 0, 0
            for edition, tree in self.sources():
                bucket = base if edition is None else editions.get(edition, {})
                for sid, node in tree.children.items():
                    if sid.startswith('[') or '#' in sid:
                        continue
                    patch = bucket.get(sid, {})
                    pairs = [(node, patch)]
                    table = node.children.get('WeaponReloadTimePerAttachment')
                    if table:
                        patched_rows = patch.get('WeaponReloadTimePerAttachment', {})
                        self.assertLessEqual(set(patched_rows), set(table.children))
                        pairs.extend((row, patched_rows.get(index, {}))
                                     for index, row in table.children.items())
                    for original, changed in pairs:
                        for key, raw in original.values.items():
                            if key.endswith('ReloadTimeMultiplier') and parse_number(raw) > 0:
                                with self.subTest(factor=factor, edition=edition, sid=sid, key=key):
                                    self.assertIn(key, changed)
                                    self.assertAlmostEqual(parse_number(changed[key]), parse_number(raw) / factor, delta=0.000051)
                                count += 1
                                auxiliary += 'Aux' in key
                                edition_count += edition is not None
                        self.assertNotIn('AttachmentSID', changed)
                        self.assertNotIn('UnloadTime', changed)
                    self.assertNotIn('WeaponJamParams', patch)
            self.assertGreater(count, 100)
            self.assertGreater(auxiliary, 0)
            if self.gd.dlc_editions:
                self.assertGreater(edition_count, 0)

    def test_inherited_values_are_not_materialized_or_scaled_twice(self):
        base, editions = _weapon_general_patch(self.gd, Settings(reload_speed_factor=2))
        for edition, tree in self.sources():
            bucket = base if edition is None else editions.get(edition, {})
            for sid, patch in bucket.items():
                node = tree.children[sid]
                for key in patch:
                    if key.endswith('ReloadTimeMultiplier'):
                        self.assertIn(key, node.values)
                for index, row in patch.get('WeaponReloadTimePerAttachment', {}).items():
                    self.assertLessEqual(set(row), set(node.children['WeaponReloadTimePerAttachment'].children[index].values))

    def test_jam_time_and_probability_are_independent_including_editions(self):
        for settings, key, factor in ((Settings(jam_clear_factor=2), 'FullJamTime', .5),
                                      (Settings(jam_chance_factor=.25), 'JamChanceCoef', .25),
                                      (Settings(jam_chance_factor=0), 'JamChanceCoef', 0)):
            base, editions = _weapon_general_patch(self.gd, settings)
            count = 0
            for edition, tree in self.sources():
                bucket = base if edition is None else editions.get(edition, {})
                for sid, node in tree.children.items():
                    if sid.startswith('[') or '#' in sid:
                        continue
                    table = node.children.get('WeaponJamParams')
                    if not table:
                        continue
                    patch = bucket.get(sid, {})
                    self.assertNotIn('WeaponReloadTimePerAttachment', patch)
                    rows = patch.get('WeaponJamParams', {})
                    for index, original in table.children.items():
                        value = parse_number(original.values.get(key))
                        row = rows.get(index, {})
                        self.assertLessEqual(set(row), {key})
                        if value > 0:
                            self.assertAlmostEqual(parse_number(row[key]), value * factor, delta=0.000051)
                            count += 1
                        else:
                            self.assertNotIn(key, row)
            self.assertGreater(count, 0)


if __name__ == '__main__':
    unittest.main()
