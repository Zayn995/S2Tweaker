"""Headless field-repair patch contract; does not claim engine validation."""

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker.cfgparse import parse
from s2tweaker.emit import emit_patch
from s2tweaker.gamedata import GameData
from s2tweaker.repair_extensions import (
    REPAIR_COMPOSITE_SID, REPAIR_FIELDS, build, effect_namespace,
)

PREFIX = effect_namespace()


def fixture():
    """Small synthetic tree, with a third-party extra effect at index 2."""
    gd = GameData.__new__(GameData)
    gd.items = parse("""
TemplateConsumable : struct.begin
 Type = EItemType::Consumable
 Usable = true
 ConsumeOnUse = true
struct.end
Hercules : struct.begin {refkey=TemplateConsumable}
 SID = Hercules
 Cost = 987
 EffectPrototypeSIDs : struct.begin
  [0] = HerculesWeight
  [1] = HerculesWeight_Penalty
  [2] = ThirdPartyHerculesEffect
 struct.end
 ShouldShowEffects : struct.begin
  [0] = true
  [1] = false
  [2] = false
 struct.end
struct.end
""")
    effect_text = """
[0] : struct.begin
 SID = Empty
 Duration = 0.f
 Charges = 0
 DelayMin = 0.f
 DelayMax = 0.f
 bIsPermanent = false
struct.end
HerculesWeight : struct.begin {refkey=[0]}
 SID = HerculesWeight
 Type = EEffectType::AdditionalInventoryWeight
 Positive = EBeneficial::Positive
 Duration = 321.f
 ValueMin = 17
 ValueMax = 17
struct.end
NativeComposite : struct.begin {refkey=[0]}
 SID = NativeComposite
 Type = EEffectType::Composite
struct.end
"""
    for slot in ("Body", "Head", "PrimaryWeapon", "SecondaryWeapon", "Pistol"):
        effect_text += f"""
NativeCorrosion{slot} : struct.begin {{refkey=[0]}}
 SID = NativeCorrosion{slot}
 Type = EEffectType::Corrosion
 InventoryEquipmentSlot = EInventoryEquipmentSlot::{slot}
 ValueMin = 7
 ValueMax = 7
struct.end
"""
    gd.effects = parse(effect_text)
    return gd


class RepairExtensionsTest(unittest.TestCase):
    def test_neutral_does_not_read_game_data(self):
        self.assertEqual({}, build(object(), SimpleNamespace()))

    def test_addition_preserves_existing_and_third_party_effects(self):
        gd = fixture()
        snapshot = copy.deepcopy((gd.items, gd.effects))
        patches = build(gd, SimpleNamespace(field_repair_body_pct=12.5))
        self.assertEqual(snapshot, (gd.items, gd.effects))
        self.assertEqual(set(patches), {"ItemPrototypes.cfg", "EffectPrototypes.cfg"})
        item = patches["ItemPrototypes.cfg"]["Hercules"]
        self.assertEqual(set(item), {"EffectPrototypeSIDs", "ShouldShowEffects"})
        self.assertEqual(item["EffectPrototypeSIDs"], {"[*]": REPAIR_COMPOSITE_SID})
        self.assertEqual(item["ShouldShowEffects"], {"[*]": "false"})
        effects = patches["EffectPrototypes.cfg"]
        self.assertEqual(len(effects), 2)
        repair = effects[PREFIX + "_Body"]
        self.assertEqual(repair["ValueMin"], "-12.5%")
        self.assertEqual(repair["ValueMax"], "-12.5%")
        self.assertEqual(repair["InventoryEquipmentSlot"], "EInventoryEquipmentSlot::Body")
        self.assertNotIn("HerculesWeight", effects)

    def test_weapon_slider_targets_exactly_the_three_equipped_weapon_slots(self):
        patches = build(fixture(), SimpleNamespace(field_repair_weapons_pct=4.0))
        effects = patches["EffectPrototypes.cfg"]
        slots = {node["InventoryEquipmentSlot"] for node in effects.values()
                 if "InventoryEquipmentSlot" in node}
        self.assertEqual(slots, {"EInventoryEquipmentSlot::PrimaryWeapon",
                                 "EInventoryEquipmentSlot::SecondaryWeapon",
                                 "EInventoryEquipmentSlot::Pistol"})
        targets = effects[REPAIR_COMPOSITE_SID]["ApplyExtraEffectPrototypeSIDs"]
        self.assertEqual(set(targets.values()), set(effects) - {REPAIR_COMPOSITE_SID})

    def test_selected_strengths_stay_independent(self):
        p = build(fixture(), SimpleNamespace(field_repair_body_pct=9.0,
                    field_repair_head_pct=13.0, field_repair_weapons_pct=25.0))
        effects = p["EffectPrototypes.cfg"]
        self.assertEqual(len(effects), 6)
        self.assertEqual(effects[PREFIX + "_Body"]["ValueMin"], "-9.0%")
        self.assertEqual(effects[PREFIX + "_Head"]["ValueMin"], "-13.0%")
        for slot in ("PrimaryWeapon", "SecondaryWeapon", "Pistol"):
            self.assertEqual(effects[f"{PREFIX}_{slot}"]["ValueMin"], "-25.0%")

    def test_emitted_merge_attributes_only_target_existing_structs(self):
        p = build(fixture(), SimpleNamespace(field_repair_body_pct=5.0))
        item_text = emit_patch(p["ItemPrototypes.cfg"])
        effect_text = emit_patch(p["EffectPrototypes.cfg"])
        self.assertEqual(item_text.count("{bpatch}"), 3)
        self.assertNotIn("bpatch", effect_text)
        self.assertNotIn("__new__", effect_text)
        self.assertIn("{refkey=[0]}", effect_text)
        self.assertIn("[*] = " + REPAIR_COMPOSITE_SID, item_text)
        self.assertNotIn("[0] =", item_text)
        self.assertNotIn("Duration =", effect_text)  # instant template inheritance

    def test_invalid_percentages_never_generate_damage_or_nonfinite_cfg(self):
        for field, _slots in REPAIR_FIELDS:
            for invalid in (-0.01, 25.01, float("nan"), float("inf"), "invalid", None):
                with self.subTest(field=field, value=invalid):
                    with self.assertRaises(ValueError):
                        build(fixture(), SimpleNamespace(**{field: invalid}))

    def test_missing_or_unusable_item_fails_clearly(self):
        for mutation in ("missing", "Usable", "ConsumeOnUse", "Type", "effects"):
            with self.subTest(mutation=mutation):
                gd = fixture()
                if mutation == "missing":
                    del gd.items.children["Hercules"]
                elif mutation == "effects":
                    del gd.items.children["Hercules"].children["EffectPrototypeSIDs"]
                else:
                    gd.items.children["Hercules"].values[mutation] = "false"
                with self.assertRaisesRegex(ValueError, "Hercules"):
                    build(gd, SimpleNamespace(field_repair_body_pct=10.0))

    def test_repeating_template_or_missing_slot_is_rejected(self):
        for field in ("Duration", "Charges", "DelayMin", "DelayMax", "bIsPermanent", "slot"):
            with self.subTest(field=field):
                gd = fixture()
                if field == "slot":
                    del gd.effects.children["NativeCorrosionBody"]
                else:
                    gd.effects.children["[0]"].values[field] = "true" if field == "bIsPermanent" else "1"
                with self.assertRaises(ValueError):
                    build(gd, SimpleNamespace(field_repair_body_pct=10.0))

    def test_existing_effect_name_or_sid_is_not_overwritten(self):
        for sid in (PREFIX + "_Body", REPAIR_COMPOSITE_SID):
            with self.subTest(sid=sid):
                gd = fixture()
                gd.effects.children["ForeignNode"] = parse(f"""
ForeignNode : struct.begin
 SID = {sid}
struct.end
""").children["ForeignNode"]
                with self.assertRaisesRegex(ValueError, "SID already exists"):
                    build(gd, SimpleNamespace(field_repair_body_pct=10.0))

    def test_mod_names_produce_safe_distinct_stable_effect_names(self):
        names = ("My Profile", "My/Profile", "\n;struct.end = x", "\u00e4" * 90)
        namespaces = [effect_namespace(name) for name in names]
        self.assertEqual(len(set(namespaces)), len(names))
        for name, namespace in zip(names, namespaces):
            self.assertEqual(namespace, effect_namespace(name))
            self.assertRegex(namespace, r"^S2Tweaker_FieldRepair_[A-Za-z0-9_]+$")
            p = build(fixture(), SimpleNamespace(mod_name=name, field_repair_body_pct=5))
            self.assertEqual(set(p["EffectPrototypes.cfg"]),
                             {namespace + "_Body", namespace + "_OnHercules"})
            self.assertEqual(p["ItemPrototypes.cfg"]["Hercules"]["EffectPrototypeSIDs"],
                             {"[*]": namespace + "_OnHercules"})

    @unittest.skipUnless((ROOT / "vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg").exists(),
                         "local original game data unavailable")
    def test_live_game_has_supported_schema_and_preserves_hercules(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        original = copy.deepcopy(gd.items.children["Hercules"])
        p = build(gd, SimpleNamespace(field_repair_body_pct=8.0,
                   field_repair_head_pct=11.0, field_repair_weapons_pct=14.0))
        self.assertEqual(gd.items.children["Hercules"], original)
        self.assertEqual(len(p["EffectPrototypes.cfg"]), 6)
        self.assertEqual(set(p["ItemPrototypes.cfg"]), {"Hercules"})


if __name__ == "__main__":
    unittest.main()
