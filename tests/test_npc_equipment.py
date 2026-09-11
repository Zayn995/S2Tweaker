"""Faction isolation, native masks, clone composition and update safety."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import npc_equipment as e, cfgparse, editor_state, extension_controls
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize, _gear_quality_patch
from s2tweaker.emit import emit_patch

VANILLA = ROOT / "vanilla/Stalker2/Content/GameLite/GameData"
OBJ = "GeneralNPC_Neutral_CloseCombat"
SOURCE = e.OBJECTS[OBJ][2]
FIRST = next(c for c in e.CONTROLS.values() if c.obj == OBJ and c.source == SOURCE and c.slot == "[0]" and c.row == "[0]")


def node(name, values=None, children=None, attrs=""):
    return cfgparse.CfgStruct(name, attrs, values or {}, children or {})


def fixture():
    """Audited identities with deliberately different, fractional numeric data."""
    gd = GameData(Path("unused"))
    generators, objects, npcs = {}, {}, {}
    items = {t: node(t) for t in ("TemplateWeapon", "TemplateArmor")}
    for source, attrs in e.SOURCES.items():
        generators[source] = node(source, {"SID": source, "RefreshTime": "3d"},
                                  {"ItemGenerator": node("ItemGenerator")},
                                  ";".join(k + "=" + v for k, v in attrs.items()))
    for (source, sk), (category, rank, diff, rows) in e.POOLS.items():
        values = {"Category": category}
        if rank: values["PlayerRank"] = rank
        if diff: values["Diff"] = diff
        candidates = {}
        for index, (rk, item) in enumerate(rows):
            candidates[rk] = node(rk, {"ItemPrototypeSID": item, "Weight": ".2" if index == 0 else "3.7",
                                     "AmmoMinCount": "2", "AmmoMaxCount": "11", "MinDurability": ".12", "MaxDurability": ".71"})
            items[item] = node(item, {"SID": item, "Cost": str(17 + sum(map(ord, item)) % 31)},
                               attrs="refkey=" + ("TemplateArmor" if category.endswith("BodyArmor") else "TemplateWeapon"))
        generators[source].children["ItemGenerator"].children[sk] = node(sk, values, {"PossibleItems": node("PossibleItems", children=candidates)})
    for source, links in e.LINKS.items():
        for sk, rk, target, rank, diff in links:
            values = {"Category": "EItemGenerationCategory::SubGenerator"}
            if rank: values["PlayerRank"] = rank
            if diff: values["Diff"] = diff
            gen = generators[source].children["ItemGenerator"]
            slot = gen.children.setdefault(sk, node(sk, values, {"PossibleItems": node("PossibleItems")}))
            slot.children["PossibleItems"].children[rk] = node(rk, {"ItemGeneratorPrototypeSID": target, "Chance": ".6"})
    for obj, (faction, npc, source) in e.OBJECTS.items():
        objects[obj] = node(obj, {"SID": obj, "Faction": faction, "NPCPrototypeSID": npc,
                                "ItemGeneratorPrototypeSID": source, "Type": "EObjType::NPC",
                                "IsZombie": "false", "NPCType": "ENPCType::None"}, attrs="refkey=NPCBase")
        npcs[npc] = node(npc, {"QuestNPC": "false", "UseGeneratedName": "true"})
    for key, children in (("itemgenerators", generators), ("obj", objects), ("npcprototypes", npcs), ("items", items)):
        gd.__dict__[key] = node(key, children=children)
    gd.__dict__["effects"] = node("effects")
    return gd


def settings(*pairs, **extra):
    return Settings(npc_equipment_overrides={c.key: v for c, v in pairs}, **extra)


def row(tree, c):
    return tree["ItemGenerator"][c.slot]["PossibleItems"][c.row]


class SyntheticEquipment(unittest.TestCase):
    def setUp(self):
        self.gd = fixture()

    def test_live_baseline_isolation_and_new_struct_emission(self):
        source = self.gd.itemgenerators.children[SOURCE]
        before = deepcopy(source)
        result = {}
        objects = e.apply(self.gd, settings((FIRST, 250)), result)
        name = objects[OBJ]["ItemGeneratorPrototypeSID"]
        self.assertEqual(set(objects), {OBJ})
        self.assertEqual(set(result), {name})
        self.assertEqual(row(result[name], FIRST)["Weight"], "0.5")
        self.assertEqual(row(result[name], FIRST)["AmmoMaxCount"], "11")
        self.assertEqual(result[name]["RefreshTime"], "3d")
        self.assertEqual(source, before)
        text = emit_patch(result)
        self.assertNotIn("bpatch", text)
        self.assertIn("refurl=../ItemGeneratorPrototypes.cfg", text)
        self.assertEqual(cfgparse.parse(text).children[name].get("ItemGenerator.[0].PlayerRank"), "ERank::Newbie")
        self.assertIn("{bpatch}", emit_patch(objects))

    def test_global_effective_values_and_variety_are_copied_once(self):
        existing = {SOURCE: {"ItemGenerator": {FIRST.slot: {"PossibleItems": {
            FIRST.row: {"Weight": ".6", "AmmoMaxCount": "33", "MinDurability": ".42"},
            "EarlierCandidate": {"__new__": True, "ItemPrototypeSID": "Earlier", "Weight": "7", "AmmoMaxCount": "9"}}}}}}
        before = deepcopy(existing)
        objects = e.apply(self.gd, settings((FIRST, 50)), existing)
        name = objects[OBJ]["ItemGeneratorPrototypeSID"]
        self.assertEqual(existing[SOURCE], before[SOURCE])
        self.assertEqual(row(existing[name], FIRST)["Weight"], "0.3")
        self.assertEqual(row(existing[name], FIRST)["AmmoMaxCount"], "33")
        self.assertEqual(row(existing[name], FIRST)["MinDurability"], ".42")
        self.assertEqual(existing[name]["ItemGenerator"][FIRST.slot]["PossibleItems"]["EarlierCandidate"]["Weight"], "7")

    def test_shared_helper_is_private_per_role_and_namespace(self):
        first = next(c for c in e.CONTROLS.values() if c.obj == "GeneralNPC_Duty_CloseCombat" and c.source != e.OBJECTS[c.obj][2])
        second = next(c for c in e.CONTROLS.values() if c.obj == "GeneralNPC_Duty_Recon" and (c.source, c.slot, c.row) == (first.source, first.slot, first.row))
        result = {}
        links = e.apply(self.gd, settings((first, 200), (second, 50)), result)
        self.assertEqual(set(links), {first.obj, second.obj})
        a = e.clone_sid("S2Tweaker", first.obj, first.source)
        b = e.clone_sid("S2Tweaker", second.obj, second.source)
        self.assertNotEqual(a, b)
        self.assertEqual(row(result[a], first)["Weight"], "0.4")
        self.assertEqual(row(result[b], second)["Weight"], "0.1")
        self.assertNotIn(first.source, result)
        root = result[links[first.obj]["ItemGeneratorPrototypeSID"]]
        self.assertIn(a, str(root))
        self.assertNotIn(b, str(root))
        self.assertNotEqual(a, e.clone_sid("Other mod", first.obj, first.source))

    def test_zero_pool_requires_a_final_alternative_including_variety(self):
        controls = [c for c in e.CONTROLS.values() if (c.obj, c.source, c.slot) == (OBJ, SOURCE, FIRST.slot)]
        s = settings(*[(c, 0) for c in controls])
        with self.assertRaisesRegex(ValueError, "at least one"):
            e.apply(self.gd, s, {})
        result = {SOURCE: {"ItemGenerator": {FIRST.slot: {"PossibleItems": {
            "Extra": {"__new__": True, "ItemPrototypeSID": "Earlier", "Weight": "2"}}}}}}
        objects = e.apply(self.gd, s, result)
        cfg = result[objects[OBJ]["ItemGeneratorPrototypeSID"]]
        self.assertTrue(all(row(cfg, c)["Weight"] == "0" for c in controls))
        self.assertEqual(cfg["ItemGenerator"][FIRST.slot]["PossibleItems"]["Extra"]["Weight"], "2")

    def test_update_changes_fail_closed_and_do_not_retarget_saved_keys(self):
        self.assertIn(FIRST.key, e.catalog(self.gd))
        source = self.gd.itemgenerators.children[SOURCE]
        slot = source.children["ItemGenerator"].children[FIRST.slot]
        candidate = slot.children["PossibleItems"].children[FIRST.row]
        for target, field, value in ((slot.values, "PlayerRank", "ERank::Veteran, Master"),
                                     (candidate.values, "ItemPrototypeSID", "UnrelatedWeapon"),
                                     (candidate.values, "Chance", ".5"),
                                     (candidate.values, "Weight", "nan")):
            previous = dict(target)
            target[field] = value
            self.assertNotIn(FIRST.key, e.catalog(self.gd))
            target.clear(); target.update(previous)
        candidate.children["[6]"] = node("[6]", {"ItemPrototypeSID": FIRST.item, "Weight": "5"})
        self.assertNotIn(FIRST.key, e.catalog(self.gd))

    def test_named_consumers_and_inheritance_guard(self):
        self.gd.obj.children["NamedCharacter"] = node("NamedCharacter", {"ItemGeneratorPrototypeSID": SOURCE}, attrs="refkey=" + OBJ)
        self.assertIn(FIRST.key, e.catalog(self.gd))
        objects = e.apply(self.gd, settings((FIRST, 200)), {})
        self.assertNotIn("NamedCharacter", objects)
        del self.gd.obj.children["NamedCharacter"].values["ItemGeneratorPrototypeSID"]
        self.assertNotIn(FIRST.key, e.catalog(self.gd))
        self.gd.__dict__.pop("npc_equipment_editor", None)
        self.assertEqual(e.apply(self.gd, settings((FIRST, 200)), {}), {})

    def test_invalid_values_neutral_and_generated_id_collision(self):
        for value in (True, "2", -1, 401, 1.5, math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                list(e.changes({FIRST.key: value}))
        self.assertEqual(e.apply(self.gd, settings((FIRST, 100)), {}), {})
        self.assertEqual(list(e.changes({"npc_equipment:unaudited": 200})), [])
        name = e.clone_sid("S2Tweaker", OBJ, SOURCE)
        self.gd.itemgenerators.children[name] = node(name)
        with self.assertRaisesRegex(ValueError, "already exists"):
            e.apply(self.gd, settings((FIRST, 200)), {})

    def test_fractional_quality_preserves_lowest_and_existing_integer_tiers(self):
        for weight in (.1, .5, 7, 1000):
            self.assertEqual(e.quality_weight(weight, 4, 0), weight)
            self.assertEqual(e.quality_weight(weight, 1, .5), weight)
        self.assertEqual(e.quality_weight(.1, .25, 1), .025)
        self.assertEqual(e.quality_weight(.5, 4, 1), 2)
        self.assertEqual(e.quality_weight(1, .25, 1), 1)
        self.assertEqual(e.quality_weight(100, 4, 1), 400)
        # Exercise the production global quality builder with actual fractional rows.
        pool = self.gd.itemgenerators.children[SOURCE].children["ItemGenerator"].children[FIRST.slot].children["PossibleItems"]
        keys = list(pool.children)
        data = [(keys[0], pool.children[keys[0]], .1, 10), (keys[1], pool.children[keys[1]], .5, 20)]
        with patch.object(self.gd, "gear_weight_pools", return_value=[(SOURCE, "ItemGenerator", FIRST.slot, data)]):
            patch_result = _gear_quality_patch(self.gd, Settings(npc_gear_quality_factor=.25))
        self.assertNotIn(keys[0], patch_result[SOURCE]["ItemGenerator"][FIRST.slot]["PossibleItems"])
        self.assertEqual(patch_result[SOURCE]["ItemGenerator"][FIRST.slot]["PossibleItems"][keys[1]]["Weight"], "0.125")

    def test_profiles_undo_reset_summary_and_conflict_footprint(self):
        sliders = {c.key: extension_controls.ArtifactControl(c) for c in e.CONTROLS.values()}
        before = {"sliders": {k: r.get() for k, r in sliders.items()}}
        history = editor_state.History(before)
        sliders[FIRST.key].set(0)
        after = {"sliders": {k: r.get() for k, r in sliders.items()}}
        history.commit(after)
        self.assertEqual(history.undo(), before)
        self.assertEqual(history.redo(), after)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "equipment.json"
            editor_state.save_profile(path, after, "Equipment")
            self.assertEqual(editor_state.read_profile(path).state["sliders"], after["sliders"])
        self.assertEqual(e.collect(sliders), {FIRST.key: 0})
        self.assertIn("experimental", summarize(settings((FIRST, 0)))[0])
        sliders[FIRST.key].reset()
        self.assertEqual(e.collect(sliders), {})
        footprint = e.footprint(self.gd, FIRST.key)
        self.assertIn((OBJ, "ItemGeneratorPrototypeSID"), footprint)
        self.assertIn((SOURCE, "AmmoMaxCount"), footprint)
        self.assertIn((SOURCE, "Weight"), footprint)


@unittest.skipUnless((VANILLA / "ObjPrototypes.cfg").exists(), "local game data only")
class LiveEquipment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(VANILLA)

    def test_live_scope_neutral_and_exclusions(self):
        data = e.available(self.gd)
        self.assertEqual(len(data), 1028)
        self.assertEqual(len({e.CONTROLS[k].obj for k in data}), 50)
        self.assertEqual(len({e.CONTROLS[k].faction for k in data}), 12)
        self.assertEqual(build_patches(self.gd, Settings()), {})
        self.assertFalse(any(c.source == "GeneralNPC_Mercenaries_Recon_ItemGenerator" and c.slot == "[2]" for c in e.CONTROLS.values()))
        self.assertFalse(any(c.source == "GeneralNPC_Bandit_WeaponPistol" and c.slot == "[2]" for c in e.CONTROLS.values()))

    def test_export_isolated_with_globals_and_readback(self):
        from dataclasses import replace
        s = settings((FIRST, 200), npc_gear_quality_factor=4, npc_equipment_variety=True,
                     npc_loaded_ammo_factor=2, dropped_condition_pct=65, npc_helmet_chance_factor=2,
                     npc_armor_drop_chance_pct=35)
        normal = build_patches(self.gd, replace(s, npc_equipment_overrides={}))
        changed = build_patches(self.gd, s)
        gp = "ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_S2Tweaker.cfg"
        before, after = cfgparse.parse(normal[gp]), cfgparse.parse(changed[gp])
        for key, value in before.children.items():
            self.assertEqual(after.children[key], value, key)
        name = e.clone_sid(s.mod_name, OBJ, SOURCE)
        self.assertIn(name, after.children)
        baseline = e._clone(self.gd.itemgenerators.children[SOURCE])
        if SOURCE in before.children:
            e._merge(baseline, e._clone(before.children[SOURCE]))
        actual = after.children[name]
        expected = deepcopy(baseline)
        expected.pop("__attrs__", None)
        expected["SID"] = name
        row(expected, FIRST)["Weight"] = e._fmt(cfgparse.parse_number(row(baseline, FIRST)["Weight"]) * 2)
        parsed = e._clone(actual)
        parsed.pop("__attrs__", None)
        def leaves_only(tree):
            return {k: leaves_only(v) if isinstance(v, dict) else v for k, v in tree.items() if k != "__attrs__"}
        self.assertEqual(leaves_only(parsed), leaves_only(expected))
        op = cfgparse.parse(changed["ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"])
        self.assertEqual(op.children[OBJ].values, {"ItemGeneratorPrototypeSID": name})
        self.assertEqual(set(op.children), {OBJ})


if __name__ == "__main__":
    unittest.main()
