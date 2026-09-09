"""Headless semantic tests for optional loot and sparse additions.

Fixtures deliberately contain rank, quest, visibility and reused-index traps.
No installed game, GUI, executable or foreign mod is required.
"""
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker.cfgparse import CfgStruct, parse
from s2tweaker.emit import emit_patch
from s2tweaker.gamedata import GameData
from s2tweaker import loot_extensions as ext


def node(name, values=None, children=None, ref=None):
    return CfgStruct(name, "refkey=" + ref if ref else "", values or {}, children or {})


def slot(name, category, rows, rank=None, difficulty=None):
    values = {"Category": ext.GEN_PREFIX + category}
    if rank:
        values["PlayerRank"] = "ERank::" + rank
    if difficulty:
        values["Diff"] = difficulty
    return node(name, values, {"PossibleItems": node("PossibleItems", children={
        f"[{i}]": node(f"[{i}]", row) for i, row in enumerate(rows)})})


def generator(name, slots, ref=None):
    return node(name, {"SID": name}, {"ItemGenerator": node("ItemGenerator", children={
        x.name: x for x in slots})}, ref)


def fixture(directory):
    gd = GameData(directory)
    gd.items = node("items", children={
        name: node(name) for name in ("TemplateWeapon", "TemplateArmor", "TemplateArtifact",
                                     "TemplateAttach", "TemplateConsumable")})
    specs = (("GunLow_ST", "TemplateWeapon", {}), ("GunHigh_ST", "TemplateWeapon", {}),
             ("ArmorLow", "TemplateArmor", {}), ("ArmorHigh", "TemplateArmor", {}),
             ("ArmorHidden", "TemplateArmor", {"Invisible": "true"}),
             ("Helmet", "TemplateArmor", {}), ("Artifact", "TemplateArtifact", {"ArchiartifactType": "EArchiartifactType::None"}),
             ("Scope", "TemplateAttach", {}), ("Food", "TemplateConsumable", {}),
             ("FleshLoot", None, {"Type": "EItemType::MutantLoot"}),
             ("TushkanLoot", None, {"Type": "EItemType::MutantLoot"}),
             ("QuestLoot", None, {"Type": "EItemType::MutantLoot", "IsQuestItemPrototype": "true"}),
             ("QuestNote", None, {"IsQuestItem": "true"}))
    for name, template, values in specs:
        gd.items.children[name] = node(name, {"SID": name, **values}, ref=template)
    pistol = generator("GeneralNPC_Test_WeaponPistol", [
        slot("[0]", "WeaponPistol", [{"ItemPrototypeSID": "GunLow_ST", "Weight": "1",
             "AmmoMinCount": "2", "AmmoMaxCount": "5", "MinDurability": "0.2", "MaxDurability": "0.5"}], "Newbie"),
        slot("[1]", "WeaponPistol", [{"ItemPrototypeSID": "GunHigh_ST", "Weight": "2",
             "AmmoMinCount": "3", "AmmoMaxCount": "8"}], "Master"),
        slot("[2]", "WeaponPistol", [{"ItemPrototypeSID": "GunHigh_ST", "Weight": "2"}], "Experienced", "EGameDifficulty::Hard")])
    armor = generator("GeneralNPC_Test_Armor", [
        slot("[0]", "BodyArmor", [{"ItemPrototypeSID": "ArmorLow", "Weight": "1"},
            {"ItemPrototypeSID": "ArmorHidden", "Weight": "1"}], "Newbie"),
        slot("[1]", "BodyArmor", [{"ItemPrototypeSID": "ArmorHigh", "Weight": "1"}], "Master"),
        slot("[2]", "Head", [{"ItemPrototypeSID": "Helmet", "Chance": "0.3"}], "Master"),
        slot("[3]", "Head", [{"ItemPrototypeSID": "Helmet", "Weight": "1"}], "Newbie")])
    flesh = generator("FleshLootGenerator", [slot("[0]", "MutantLoot", [
        {"ItemPrototypeSID": "FleshLoot", "Chance": "0.2", "MinCount": "1", "MaxCount": "1"}])])
    tushkan = generator("TushkanLootGenerator", [slot("[0]", "MutantLoot", [
        {"ItemPrototypeSID": "TushkanLoot", "Chance": "0.1", "MinCount": "1", "MaxCount": "1"}])])
    quest = generator("QuestLootGenerator", [slot("[0]", "MutantLoot", [
        {"ItemPrototypeSID": "QuestLoot", "Chance": "0.2", "MinCount": "1", "MaxCount": "1"}])])
    base = generator("GamePass_Stash_ItemGenerator_Cheap", [slot("[0]", "Consumable", [
        {"ItemPrototypeSID": "Food", "Chance": "1", "MinCount": "1", "MaxCount": "1"},
        {"ItemPrototypeSID": "Scope", "Chance": "0.1", "MinCount": "1", "MaxCount": "1"}])])
    wrapper = generator("Forest_StashGenerator", [slot("[0]", "SubItemGenerator", [
        {"ItemGeneratorPrototypeSID": base.name, "Weight": "1"}])])
    unsafe = generator("Forest_UnsafeStashGenerator", [slot("[0]", "Consumable", [
        {"ItemPrototypeSID": "QuestNote", "Chance": "1"}])], ref=base.name)
    gd.itemgenerators = node("generators", children={x.name: x for x in
        (pistol, armor, flesh, tushkan, quest, base, wrapper, unsafe)})
    gd.trade = node("trade")
    gd.effects = node("effects")
    gd.artifactspawners = node("artifacts", children={"CommonSpawner": node("CommonSpawner",
        {"UseListOfArtifacts": "true"}, {"ListOfArtifacts": node("ListOfArtifacts", {"[0]": "Artifact"}),
        **{rank: node(rank, {"Count": "1"}) for rank in ext.RANKS}})})
    return gd


def spawn(name, level="WorldMap_WP", on_start="true", generator_sid="Forest_StashGenerator"):
    return {name: {"__new__": True, "SID": name, "LevelName": level, "SpawnOnStart": on_start,
                  "DLC": "None", "SpawnType": "ESpawnType::ItemContainer",
                  "ItemGeneratorSettings": {"[0]": {"PlayerRank": "ERank::Newbie",
                      "ItemGenerators": {"[0]": {"PrototypeSID": generator_sid}}}}}}


class LootExtensions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.gd = fixture(self.temp.name)

    def test_defaults_are_lazy(self):
        class NoReads:
            def __getattr__(self, name):
                raise AssertionError("Default attempted to read " + name)
        self.assertEqual(ext.build(NoReads(), SimpleNamespace()), {})

    def test_ammo_and_helmet_patch_only_their_fields(self):
        patches = ext.build(self.gd, SimpleNamespace(npc_loaded_ammo_factor=2,
                                                    npc_helmet_chance_factor=3))["ItemGeneratorPrototypes.cfg"]
        ammo = patches["GeneralNPC_Test_WeaponPistol"]["ItemGenerator"]["[0]"]["PossibleItems"]["[0]"]
        self.assertEqual(ammo, {"AmmoMinCount": "4", "AmmoMaxCount": "10"})
        heads = patches["GeneralNPC_Test_Armor"]["ItemGenerator"]
        self.assertEqual(heads, {"[2]": {"PossibleItems": {"[0]": {"Chance": "0.9"}}}})

    def test_armor_helpers_preserve_equipment_and_filter_hidden_items(self):
        patches = ext.build(self.gd, SimpleNamespace(npc_armor_drop_chance_pct=30,
                         npc_armor_drop_min_pct=90, npc_armor_drop_max_pct=80))["ItemGeneratorPrototypes.cfg"]
        roots = patches["GeneralNPC_Test_Armor"]["ItemGenerator"]
        self.assertTrue(all(key.startswith("S2Tweaker_") for key in roots))
        text = emit_patch(patches)
        self.assertNotIn("ArmorHidden", text)
        self.assertIn("MinDurability = 0.8", text)
        self.assertIn("MaxDurability = 0.9", text)
        self.assertIn("PlayerRank = ERank::Newbie", text)
        parsed = parse(text)
        self.assertIn("bpatch", parsed.children["GeneralNPC_Test_Armor"].attr_dict())
        helper = next(n for k, n in parsed.children.items() if "_ArmorLoot_" in k)
        self.assertNotIn("bpatch", helper.attr_dict())

    def test_earlier_equipment_stays_in_faction_role_and_preserves_existing_rows(self):
        patches = ext.build(self.gd, SimpleNamespace(npc_equipment_variety=True,
                                                     npc_loaded_ammo_factor=2))["ItemGeneratorPrototypes.cfg"]
        slots = patches["GeneralNPC_Test_WeaponPistol"]["ItemGenerator"]
        new_rows = {k: v for k, v in slots["[1]"]["PossibleItems"].items() if k.startswith("S2Tweaker_")}
        self.assertEqual(len(new_rows), 1)
        added = next(iter(new_rows.values()))
        self.assertEqual(added["ItemPrototypeSID"], "GunLow_ST")
        self.assertEqual(added["AmmoMaxCount"], "10")
        self.assertTrue(added["__new__"])
        self.assertTrue(all(v.get("ItemPrototypeSID") != "GunHigh_ST" for k, v in
                            slots["[0]"]["PossibleItems"].items() if k.startswith("S2Tweaker_")))

    def test_species_overrides_compose_and_preserve_other_species(self):
        patches = ext.build(self.gd, SimpleNamespace(mutant_loot_chance_factor=2,
                    loot_amount_factor=2, mutant_loot_overrides={"Flesh": {"chance_factor": 3,
                                                                           "amount_factor": 0.5}}))["ItemGeneratorPrototypes.cfg"]
        flesh = patches["FleshLootGenerator"]["ItemGenerator"]["[0]"]["PossibleItems"]["[0]"]
        self.assertEqual(flesh, {"Chance": "1", "MinCount": "1", "MaxCount": "1"})
        self.assertEqual(patches["TushkanLootGenerator"]["ItemGenerator"]["[0]"]["PossibleItems"]["[0]"], {"Chance": "0.2"})
        self.assertNotIn("QuestLootGenerator", patches)
        self.assertEqual(ext.mutant_species(self.gd), ["Flesh", "Tushkan"])

    def test_stash_additions_isolate_world_container_and_preserve_existing_assignments(self):
        data = {}
        data.update(spawn("MainStash"))
        data.update(spawn("QuestSublevel", level="WorldMap_WP/MQ01_LogicLevel_WP"))
        data.update(spawn("ScriptedStash", on_start="false"))
        data.update(spawn("UnsafeStash", generator_sid="Forest_UnsafeStashGenerator"))
        Path(self.temp.name, "SpawnActorPrototypes.cfg").write_text(emit_patch(data), encoding="utf-8")
        patches = ext.build(self.gd, SimpleNamespace(stash_extra_artifacts=True,
                          stash_extra_weapons=True, stash_extra_armor=True, stash_extra_attachments=True))
        self.assertEqual(set(patches["SpawnActorPrototypes.cfg"]), {"MainStash"})
        refs = patches["SpawnActorPrototypes.cfg"]["MainStash"]["ItemGeneratorSettings"]["[0]"]["ItemGenerators"]
        self.assertEqual(len(refs), 1)
        self.assertIn("_ExtraFinds_", next(iter(refs)))
        self.assertTrue(all(k.startswith("S2Tweaker_") for k in patches["ItemGeneratorPrototypes.cfg"]))
        emitted = emit_patch(patches["ItemGeneratorPrototypes.cfg"])
        self.assertNotIn("GunHigh_ST", emitted)
        self.assertNotIn("ArmorHidden", emitted)
        for item in ("GunLow_ST", "ArmorLow", "Artifact", "Scope"):
            self.assertIn("ItemPrototypeSID = " + item, emitted)

    def test_inherited_array_override_does_not_leak_stash_base_reachability(self):
        self.assertEqual(ext._safe_stash_tree(self.gd, "Forest_UnsafeStashGenerator"), (False, False))
        safe_override = generator("NoLongerStash", [slot("[0]", "Consumable", [
            {"ItemPrototypeSID": "Food", "Chance": "1"}])], ref="GamePass_Stash_ItemGenerator_Cheap")
        self.gd.itemgenerators.children[safe_override.name] = safe_override
        self.assertEqual(ext._safe_stash_tree(self.gd, safe_override.name), (True, False))

    def test_every_custom_name_uses_the_profile_namespace(self):
        Path(self.temp.name, "SpawnActorPrototypes.cfg").write_text(emit_patch(spawn("MainStash")), encoding="utf-8")

        def custom_names(tree):
            names = set()
            for key, value in tree.items():
                if key.startswith("S2Tweaker_"):
                    names.add(key)
                if isinstance(value, dict):
                    names.update(custom_names(value))
            return names

        outputs = []
        for mod_name in ("Travel-Light", "Travel Light"):
            result = ext.build(self.gd, SimpleNamespace(mod_name=mod_name, npc_equipment_variety=True,
                                npc_armor_drop_chance_pct=30, stash_extra_weapons=True))
            names = custom_names(result)
            self.assertTrue(names)
            self.assertTrue(all(name.startswith(ext.loot_namespace(mod_name) + "_") for name in names))
            self.assertTrue(all(name.replace("_", "").isalnum() for name in names))
            outputs.append(names)
        self.assertFalse(outputs[0] & outputs[1])
        namespace = ext.loot_namespace("[]\n{bpatch};ärger/..")
        self.assertRegex(namespace, r"^[A-Za-z0-9_]+$")
        self.assertEqual(namespace, ext.loot_namespace("[]\n{bpatch};ärger/.."))

    def test_stash_analysis_is_cached_independently_of_settings_and_mod_name(self):
        Path(self.temp.name, "SpawnActorPrototypes.cfg").write_text(emit_patch(spawn("MainStash")), encoding="utf-8")
        with patch.object(ext, "_stream_spawn_containers", wraps=ext._stream_spawn_containers) as stream:
            with patch.object(ext, "_collect_stash_candidates", wraps=ext._collect_stash_candidates) as candidates:
                first = ext.build(self.gd, SimpleNamespace(mod_name="First", stash_extra_weapons=True))
                second = ext.build(self.gd, SimpleNamespace(mod_name="Second", stash_extra_artifacts=True,
                                                             stash_extra_chance_pct=30))
                self.assertEqual(stream.call_count, 1)
                self.assertEqual(candidates.call_count, 1)
                self.assertNotEqual(first, second)
                self.assertIn("Chance = 0.3", emit_patch(second["ItemGeneratorPrototypes.cfg"]))
        self.assertIs(ext._stash_targets(self.gd), ext._stash_targets(self.gd))
        self.assertIs(ext._stash_conditions(self.gd), ext._stash_conditions(self.gd))

    def test_scaled_bounds_preserve_order_zeros_and_missing_fields(self):
        values = {"AmmoMinCount": "0", "AmmoMaxCount": "7"}
        self.assertEqual(ext._scaled_bounds(values, "AmmoMinCount", "AmmoMaxCount", 0.5), {"AmmoMaxCount": "4"})
        self.assertEqual(ext._scaled_bounds(values, "AmmoMinCount", "AmmoMaxCount", 0), {"AmmoMaxCount": "0"})
        self.assertEqual(ext._scaled_bounds({"AmmoMaxCount": "7"}, "AmmoMinCount", "AmmoMaxCount", 2), {"AmmoMaxCount": "14"})
        for bad in ({"AmmoMinCount": "10", "AmmoMaxCount": "2"}, {"AmmoMaxCount": "nan"}, {"AmmoMaxCount": "-2"}):
            self.assertEqual(ext._scaled_bounds(bad, "AmmoMinCount", "AmmoMaxCount", 2), {})
        self.assertEqual(ext._scaled_bounds({"AmmoMaxCount": "1e308"}, "AmmoMinCount", "AmmoMaxCount", 1e308), {})

    def test_variety_does_not_import_a_difficulty_limited_pool_into_all_difficulties(self):
        gen = self.gd.itemgenerators.children["GeneralNPC_Test_WeaponPistol"].children["ItemGenerator"]
        gen.children["[0]"].values["Diff"] = "EGameDifficulty::Hard"
        result = ext.build(self.gd, SimpleNamespace(npc_equipment_variety=True))["ItemGeneratorPrototypes.cfg"]
        slots = result["GeneralNPC_Test_WeaponPistol"]["ItemGenerator"]
        self.assertNotIn("[1]", slots)
        self.assertIn("[2]", slots)

    def test_weapon_condition_does_not_change_added_armor_and_quality_uses_expanded_pool(self):
        armor = self.gd.itemgenerators.children["GeneralNPC_Test_Armor"].children["ItemGenerator"]
        armor.children["[0]"].children["PossibleItems"].children["[0]"].values.update(
            MinDurability="0.1", MaxDurability="0.2")
        for sid, cost in (("GunLow_ST", "10"), ("GunHigh_ST", "100")):
            self.gd.items.children[sid].values["Cost"] = cost
        result = ext.build(self.gd, SimpleNamespace(npc_equipment_variety=True,
                                npc_gear_quality_factor=4, dropped_condition_pct=90))["ItemGeneratorPrototypes.cfg"]
        armor_rows = result["GeneralNPC_Test_Armor"]["ItemGenerator"]["[1]"]["PossibleItems"]
        added_armor = next(v for k, v in armor_rows.items() if k.startswith("S2Tweaker_"))
        self.assertEqual(added_armor["MinDurability"], "0.1")
        self.assertEqual(added_armor["MaxDurability"], "0.2")
        weapon_rows = result["GeneralNPC_Test_WeaponPistol"]["ItemGenerator"]["[1]"]["PossibleItems"]
        self.assertEqual(weapon_rows["[0]"]["Weight"], "8")
        added_weapon = next(v for k, v in weapon_rows.items() if k.startswith("S2Tweaker_"))
        self.assertEqual(added_weapon["Weight"], "1")
        self.assertEqual(added_weapon["MinDurability"], "0.75")
        self.assertEqual(added_weapon["MaxDurability"], "1")


if __name__ == "__main__":
    unittest.main()
