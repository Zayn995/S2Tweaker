"""Headless regressions for loot-list identity and lottery conflicts.

Small synthetic configs exercise the EML-style index shift without
depending on a downloaded mod, game assets, Tk, or an installed game.
"""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import cfgparse, loot_conflicts, modscan
from s2tweaker.emit import emit_patch


def config(rows, *, patch=False, name="TrophyGenerator", group="[0]",
           attrs=None, category=True):
    slot = {"PossibleItems": rows}
    if category:
        slot["Category"] = "EItemGeneratorCategory::Consumable"
    body = {"ItemGenerator": {group: slot}}
    if not patch:
        body["__new__"] = True
    if attrs:
        body["__attrs__"] = attrs
    return emit_patch({name: body})


ROWS = {
    "[0]": {"ItemPrototypeSID": "Trophy", "Chance": "0.5f",
            "Weight": "2", "MinCount": "1", "MaxCount": "2"},
    "[1]": {"ItemPrototypeSID": "OtherLoot", "Chance": "1.0",
            "Weight": "5.0", "MinCount": "1", "MaxCount": "3"},
}


class LootConflictTests(unittest.TestCase):
    def setUp(self):
        self.vanilla = cfgparse.parse(config(ROWS))
        self.index = modscan.build_vanilla_index(
            SimpleNamespace(itemgenerators=self.vanilla))

    def scanned(self, text):
        return modscan.collect_pairs(cfgparse.parse(text), self.index)

    def footprint(self, rows, **kwargs):
        return modscan.pairs_from_patches(
            {"ItemGeneratorPrototypes/Test.cfg":
             config(rows, patch=True, category=False, **kwargs)})

    def test_unchanged_full_copy_is_not_a_conflict(self):
        self.assertEqual(self.scanned(config(ROWS)), set())
        normalized = deepcopy(ROWS)
        normalized["[0]"]["Chance"] = "0.500"
        normalized["[1]"]["Weight"] = "5.f"
        self.assertEqual(self.scanned(config(normalized)), set())

    def test_identical_value_sets_after_reorder_are_detected(self):
        reordered = {"[0]": ROWS["[1]"], "[1]": ROWS["[0]"]}
        pairs = self.scanned(config(reordered))
        marker = ("TrophyGenerator", loot_conflicts.LAYOUT_LEAF)
        self.assertIn(marker, pairs)
        for field in ("Chance", "MinCount", "MaxDurability", "AmmoMaxCount"):
            with self.subTest(field=field):
                footprint = self.footprint({"[0]": {field: "2"}})
                self.assertIn(marker, footprint)
                self.assertTrue(pairs & footprint)

    def test_eml_style_trophy_move_with_unchanged_chance(self):
        moved = deepcopy(ROWS)
        moved["[3]"] = moved.pop("[0]")
        moved["[0]"] = {"ItemPrototypeSID": "MutantBlood", "Chance": "0.5f"}
        self.assertTrue(self.scanned(config(moved))
                        & self.footprint({"[0]": {"Chance": "0.25"}}))

    def test_sparse_patch_does_not_delete_omitted_siblings(self):
        pairs = self.scanned(config({"[0]": {"Chance": "0.25"}},
                                    patch=True, category=False))
        self.assertIn(("TrophyGenerator", "Chance"), pairs)
        self.assertNotIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), pairs)

    def test_unchanged_identity_anchor_is_not_a_layout_change(self):
        pairs = self.scanned(config({"[0]": {
            "ItemPrototypeSID": "Trophy", "Chance": "0.25"}},
            patch=True, category=False))
        self.assertNotIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), pairs)

    def test_legacy_patch_targets_the_original_generator(self):
        pairs = self.scanned(config({"[0]": {"ItemPrototypeSID": "MutantBlood"}},
            name="LegacyLootPatch", attrs="refkey=TrophyGenerator", category=False))
        self.assertIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), pairs)
        unchanged = self.scanned(config({"[0]": {"ItemPrototypeSID": "Trophy"}},
            name="LegacyLootPatch", attrs="refkey=TrophyGenerator", category=False))
        self.assertNotIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), unchanged)

    def test_same_numeric_values_in_different_rows_are_detected(self):
        rows = deepcopy(ROWS)
        rows["[0]"]["Chance"], rows["[1]"]["Chance"] = "1", "0.5"
        pairs = self.scanned(config(rows))
        self.assertIn(("TrophyGenerator", "Chance"), pairs)
        self.assertNotIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), pairs)

    def test_lottery_weight_does_not_collide_with_item_mass(self):
        rows = deepcopy(ROWS)
        rows["[0]"]["Weight"] = "5"
        pairs = self.scanned(config(rows))
        self.assertIn(("TrophyGenerator", loot_conflicts.WEIGHT_LEAF), pairs)
        footprint = self.footprint({"[0]": {"Weight": "7"}})
        self.assertTrue(pairs & footprint)
        self.assertNotIn(("TrophyGenerator", "Weight"), footprint)
        mass = modscan.collect_pairs(cfgparse.parse(emit_patch({
            "TrophyGenerator": {"Weight": "7"}})))
        self.assertFalse(mass & footprint)
        other_lottery = modscan.collect_pairs(cfgparse.parse(emit_patch({
            "TrophyGenerator": {"Items": {"[0]": {"Weight": "7"}}}})))
        self.assertFalse(other_lottery & footprint)

    def test_new_named_sibling_does_not_depend_on_vanilla_indices(self):
        footprint = self.footprint({"[0]": {
            "ItemGeneratorPrototypeSID": "S2Tweaker_ExtraLoot", "Chance": "0.1"}},
            group="S2Tweaker_ExtraLoot")
        self.assertNotIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), footprint)

    def test_foreign_named_sibling_does_not_redirect_existing_rows(self):
        addition = config({"Extra": {"ItemGeneratorPrototypeSID": "OtherPool"}},
                          patch=True, group="OtherMod_Extra", category=False)
        pairs = self.scanned(addition)
        self.assertNotIn(("TrophyGenerator", loot_conflicts.LAYOUT_LEAF), pairs)
        self.assertFalse(pairs & self.footprint({"[0]": {"MinCount": "2"}}))

    def test_removed_rows_and_explicit_list_clear_are_detected(self):
        marker = ("TrophyGenerator", loot_conflicts.LAYOUT_LEAF)
        self.assertIn(marker, self.scanned(config({"[0]": ROWS["[0]"]})))
        cleared = emit_patch({"TrophyGenerator": {"ItemGenerator": ""}})
        self.assertIn(marker, self.scanned(cleared))
        empty = emit_patch({"TrophyGenerator": {"__new__": True,
                                                "ItemGenerator": {}}})
        self.assertIn(marker, self.scanned(empty))

    def test_structural_conflict_is_limited_to_its_generator(self):
        changed = config({"[0]": {"ItemPrototypeSID": "MutantBlood"}},
                         patch=True, category=False)
        other = self.footprint({"[0]": {"Chance": "0.25"}}, name="OtherGenerator")
        self.assertFalse(self.scanned(changed) & other)

    def test_large_spawn_file_is_only_streamed_when_needed(self):
        spawn = cfgparse.parse(emit_patch({"WorldStash": {
            "__new__": True,
            "ItemGeneratorSettings": {"[0]": {"ItemGenerators": {
                "[0]": {"PrototypeSID": "GamePass_Stash_ItemGenerator_Cheap"}}}}}}))
        with tempfile.TemporaryDirectory(prefix="s2t_spawn_scan_") as temp:
            source = Path(temp) / "SpawnActorPrototypes.cfg"
            source.write_text("stream fixture", encoding="utf-8")
            with patch("s2tweaker.loot_extensions._stream_spawn_containers",
                       return_value=list(spawn.children.items())) as reader:
                index = modscan.build_vanilla_index(SimpleNamespace(
                    itemgenerators=self.vanilla, dir=Path(temp)))
                modscan.collect_pairs(self.vanilla, index)
                reader.assert_not_called()
                self.assertFalse(modscan.collect_pairs(spawn, index))
                reader.assert_called_once_with(source)
                modscan.collect_pairs(spawn, index)
                reader.assert_called_once_with(source)


class EffectListConflictTests(unittest.TestCase):
    def setUp(self):
        self.base = {"Hercules": {
            "__new__": True,
            "EffectPrototypeSIDs": {"[0]": "CarryBonus", "[1]": "HerculesDuration"},
            "ShouldShowEffects": {"[0]": "true", "[1]": "false"},
        }}
        self.index = modscan.build_vanilla_index(SimpleNamespace(
            items=cfgparse.parse(emit_patch(self.base))))
        self.append = {"EffectPrototypeSIDs": {"[*]": "S2Tweaker_Repair"},
                       "ShouldShowEffects": {"[*]": "false"}}
        self.footprint = modscan.pairs_from_patches({"Items/Test.cfg":
            emit_patch({"Hercules": self.append})})

    def scanned(self, body):
        return modscan.collect_pairs(cfgparse.parse(emit_patch(body)), self.index)

    def test_append_detects_numeric_effect_changes(self):
        pairs = self.scanned({"Hercules": {
            "EffectPrototypeSIDs": {"[0]": "DifferentCarryBonus"}}})
        self.assertIn(("Hercules", modscan.EFFECT_LIST_LEAF), self.footprint)
        self.assertTrue(pairs & self.footprint)

    def test_append_detects_changed_full_copy_and_list_replacement(self):
        body = deepcopy(self.base)
        body["Hercules"]["EffectPrototypeSIDs"]["[0]"] = "DifferentCarryBonus"
        self.assertTrue(self.scanned(body) & self.footprint)
        replacement = {"Hercules": {"EffectPrototypeSIDs": {
            "__new__": True, "[0]": "CarryBonus"}}}
        self.assertTrue(self.scanned(replacement) & self.footprint)

    def test_append_detects_list_clear(self):
        self.assertTrue(self.scanned({"Hercules": {"EffectPrototypeSIDs": ""}})
                        & self.footprint)

    def test_two_independent_native_appends_do_not_conflict(self):
        other = {"Hercules": {
            "EffectPrototypeSIDs": {"[*]": "OtherMod_Effect"},
            "ShouldShowEffects": {"[*]": "false"}}}
        self.assertFalse(self.scanned(other) & self.footprint)
        self.assertNotIn(("Hercules", "[*]"), self.footprint)

    def test_unchanged_full_copy_and_numeric_anchor_do_not_conflict(self):
        self.assertFalse(self.scanned(self.base))
        self.assertFalse(self.scanned({"Hercules": {
            "EffectPrototypeSIDs": {"[0]": "CarryBonus"}}}))

    def test_reordered_values_do_not_disappear_in_the_vanilla_value_set(self):
        body = deepcopy(self.base)
        body["Hercules"]["EffectPrototypeSIDs"] = {
            "[0]": "HerculesDuration", "[1]": "CarryBonus"}
        self.assertTrue(self.scanned(body) & self.footprint)

    def test_conflict_is_limited_to_the_affected_item(self):
        other = {"OtherDrug": {"EffectPrototypeSIDs": {"[0]": "OtherEffect"}}}
        self.assertFalse(self.scanned(other) & self.footprint)

    def test_legacy_effect_replacement_targets_the_item(self):
        body = {"LegacyHercules": {
            "__new__": True, "__attrs__": "refkey=Hercules",
            "EffectPrototypeSIDs": {"[0]": "DifferentCarryBonus"}}}
        self.assertTrue(self.scanned(body) & self.footprint)

    def test_nested_weight_threshold_lists_keep_their_existing_footprint(self):
        text = emit_patch({"DefaultWeightParams": {"WeightEffectParams": {
            "[0]": {"EffectPrototypeSIDs": {"[0]": "OverweightEffect"}}}}})
        footprint = modscan.pairs_from_patches({"Weight/Test.cfg": text})
        self.assertIn(("DefaultWeightParams", "[0]"), footprint)
        self.assertNotIn(("DefaultWeightParams", modscan.EFFECT_LIST_LEAF), footprint)


if __name__ == "__main__":
    unittest.main()
