"""Native artifact isolation, composition, exclusions and deferred UI contracts."""
import ast
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import artifact_extensions as a, cfgparse, editor_state, extension_controls
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize, _artifact_spawner_patch, _items_patch
from s2tweaker.modscan import EFFECT_LIST_LEAF

VANILLA = ROOT / "vanilla/Stalker2/Content/GameLite/GameData"


def key(suffix):
    return a.PREFIX + suffix


def setting(**kwargs):
    return Settings(artifact_overrides={key(k): v for k, v in kwargs.items()})


def fixture():
    """Small synthetic values deliberately unlike the installed baselines."""
    gd = GameData(Path("unused"))
    def item(sid):
        return f"""{sid} : struct.begin {{refkey=TemplateArtifact}}
   SID = {sid}
   Type = EItemType::Artifact
   ArtifactType = EArtifactType::Electro
   Weight = 0.73
   Cost = 12345
   EffectPrototypeSIDs : struct.begin
      [2] = ArtifactProtectionShock1
      [7] = ArtifactAddRadiation1
   struct.end
   ShouldShowEffects : struct.begin
      [2] = true
      [7] = true
   struct.end
struct.end
"""
    gd.__dict__["items"] = cfgparse.parse(item("EArtifactFlash") + item("EArtifactChocolate") + item("EArtifactFlash_Fake"))
    def effect(sid, value, typ):
        return f"""{sid} : struct.begin {{refkey=[0]}}
   SID = {sid}
   Type = EEffectType::{typ}
   ValueMin = {value}
   ValueMax = {value}
   Duration = 0.f
   bIsPermanent = true
   DuplicationType = EDuplicateResolveType::KeepAll
   ValueProviderSID = Empty
   EffectCurvePath =
   LocalizationSID = original_label
struct.end
"""
    text = effect("ArtifactProtectionShock1", "17.5f", "ProtectionShock")
    text += "".join(effect(sid, f"-{i * .13:g}", "DegenRadiation") for i, sid in enumerate(a.RADIATION, 1))
    gd.__dict__["effects"] = cfgparse.parse(text)
    for name in ("anomalies", "artifactspawners"):
        gd.__dict__[name] = cfgparse.parse("")
    return gd


class SyntheticArtifacts(unittest.TestCase):
    def setUp(self):
        self.gd = fixture()

    def test_simple_effect_isolation_and_native_metadata(self):
        s = setting(**{"item:EArtifactFlash:ArtifactProtectionShock1": 150})
        effect, items = {}, {}
        a.apply(self.gd, s, "EffectPrototypes", effect)
        a.apply(self.gd, s, "ItemPrototypes", items)
        name = a.clone_sid(s.mod_name, "EArtifactFlash", "ArtifactProtectionShock1")
        self.assertEqual(effect[name]["ValueMin"], "26.25f")
        self.assertEqual(effect[name]["ValueMax"], "26.25f")
        self.assertEqual(effect[name]["LocalizationSID"], "original_label")
        self.assertTrue(effect[name]["__new__"])
        self.assertEqual(effect[name]["__attrs__"], "refkey=ArtifactProtectionShock1")
        self.assertEqual(items, {"EArtifactFlash": {"EffectPrototypeSIDs": {"[2]": name}}})
        self.assertEqual(self.gd.resolve(self.gd.effects, "ArtifactProtectionShock1", "ValueMin"), "17.5f")
        self.assertNotIn("EArtifactChocolate", items)

    def test_global_composition_and_zero(self):
        s = setting(**{"item:EArtifactFlash:ArtifactProtectionShock1": 50})
        s.artifact_effect_factor = 2
        result = {}
        a.apply(self.gd, s, "EffectPrototypes", result)
        self.assertEqual(next(iter(result.values()))["ValueMin"], "17.5f")
        s.artifact_effect_factor = 0
        result = {}
        a.apply(self.gd, s, "ItemPrototypes", result)
        self.assertEqual(result, {})

    def test_weight_overrides_global_and_cancels_only_own_leaf(self):
        patches = {"EArtifactFlash": {"Weight": "0.365", "Cost": "25000"}}
        a.apply(self.gd, setting(**{"item:EArtifactFlash:weight": .73}), "ItemPrototypes", patches)
        self.assertEqual(patches, {"EArtifactFlash": {"Cost": "25000"}})
        a.apply(self.gd, setting(**{"item:EArtifactFlash:weight": 0}), "ItemPrototypes", patches)
        self.assertEqual(patches["EArtifactFlash"]["Weight"], "0")

    def test_radiation_uses_native_tier_or_off_at_actual_index(self):
        for value, expected in ((0, "empty"), (2, "ArtifactAddRadiation2"), (4, "ArtifactAddRadiation4")):
            s = setting(**{"item:EArtifactFlash:radiation": value})
            items, effects = {}, {}
            a.apply(self.gd, s, "ItemPrototypes", items)
            a.apply(self.gd, s, "EffectPrototypes", effects)
            self.assertEqual(items["EArtifactFlash"]["EffectPrototypeSIDs"], {"[7]": expected})
            self.assertEqual(effects, {})
            self.assertEqual(items["EArtifactFlash"].get("ShouldShowEffects"), {"[7]": "false"} if value == 0 else None)
        items = {}
        a.apply(self.gd, setting(**{"item:EArtifactFlash:radiation": 1}), "ItemPrototypes", items)
        self.assertEqual(items, {})

    def test_changed_source_definitions_stay_inactive(self):
        effect = self.gd.effects.children["ArtifactProtectionShock1"]
        for leaf, value in (("Type", "EEffectType::Composite"), ("ValueMin", "-3"),
                            ("DuplicationType", "Other"), ("ValueProviderSID", "DynamicProvider")):
            original = dict(effect.values)
            effect.values[leaf] = value
            self.assertNotIn(key("item:EArtifactFlash:ArtifactProtectionShock1"), a.catalog(self.gd))
            effect.values = original
        self.gd.items.children["EArtifactFlash"].values["IsQuestItem"] = "true"
        self.assertFalse(any(c.startswith(key("item:EArtifactFlash:")) for c in a.catalog(self.gd)))

    def test_namespaces_distinguish_items_and_mods(self):
        names = {a.clone_sid(mod, item, "ArtifactProtectionShock1") for mod in ("One", "Two")
                 for item in ("EArtifactFlash", "EArtifactChocolate")}
        self.assertEqual(len(names), 4)

    def test_invalid_values_and_unknown_scope(self):
        for value in (True, "2", math.inf, math.nan, -2, 401, 123.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                list(a.changes({key("item:EArtifactFlash:ArtifactProtectionShock1"): value}))
        for value in (-.5, 5, 1.5):
            with self.assertRaises(ValueError):
                list(a.changes({key("item:EArtifactFlash:radiation"): value}))
        self.assertEqual(list(a.changes({key("item:EArtifactFlash_Fake:weight"): 0})), [])
        self.assertEqual(list(a.changes({key("item:EArtifactFlash:weight"): -1})), [])
        self.assertEqual(list(a.changes({key("item:EArtifactFlash:ArtifactProtectionShock1"): 100})), [])

    def test_profile_history_decimal_zero_and_collection_wiring(self):
        sliders = {k: extension_controls.ArtifactControl(c) for k, c in a.CONTROLS.items()}
        before = {"sliders": {k: r.get() for k, r in sliders.items()}}
        history = editor_state.History(before)
        sliders[key("item:EArtifactFlash:weight")].set(.125)
        sliders[key("item:EArtifactFlash:radiation")].set(0)
        after = {"sliders": {k: r.get() for k, r in sliders.items()}}
        history.commit(after)
        self.assertEqual(history.undo(), before)
        self.assertEqual(history.redo(), after)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "artifacts.json"
            editor_state.save_profile(path, after, "Artifact checks")
            loaded = editor_state.read_profile(path).state
            self.assertEqual(loaded["sliders"], after["sliders"])
        tree = ast.parse((ROOT / "s2tweaker/gui.py").read_text(encoding="utf-8"))
        collect = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_collect")
        arg = next(n for n in ast.walk(collect) if isinstance(n, ast.keyword) and n.arg == "artifact_overrides")
        actual = eval(compile(ast.Expression(arg.value), "collection", "eval"), {"artifact_extensions": a, "s": sliders})
        self.assertEqual(actual, {key("item:EArtifactFlash:weight"): .125, key("item:EArtifactFlash:radiation"): 0})
        self.assertEqual(len(summarize(Settings(artifact_overrides=actual))), 2)
        for row in sliders.values(): row.reset()
        self.assertEqual(a.collect(sliders), {})


@unittest.skipUnless((VANILLA / "ItemPrototypes.cfg").exists(), "local game data only")
class LiveArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(VANILLA)

    def test_inventory_and_every_available_control(self):
        self.assertEqual(Counter(a.CONTROLS[k].group for k in self.gd.artifact_editor),
                         {"item": 296, "detector": 14, "ball": 7, "anomaly": 8, "rarity": 28})
        for k in self.gd.artifact_editor:
            c = a.CONTROLS[k]
            value = 50 if c.default == 100 else 0 if c.param == "radiation" else None
            source, paths = self.gd.artifact_editor[k]
            if value is None:
                raw = self.gd.resolve(self.gd.items, c.target, paths[0])
                value = round(max(c.minimum, cfgparse.parse_number(raw) * 1.1), c.decimals)
                if value == cfgparse.parse_number(raw): value = max(c.minimum, 1)
            patches = {}
            a.apply(self.gd, Settings(artifact_overrides={k: value}), source, patches)
            self.assertTrue(patches, (k, value))
            self.assertEqual(set(patches), {c.target}, k)
            self.assertTrue(a.footprint(self.gd, k), k)

    def test_detector_override_and_quest_exclusion(self):
        s = setting(**{"detector:Echo:reveal": 230})
        s.detector_range_factor = 2
        items, _ = _items_patch(self.gd, s)
        quest_before = deepcopy(items.get("EchoE01"))
        a.apply(self.gd, s, "ItemPrototypes", items)
        self.assertNotIn("ShowArtifactRadius", items["Echo"])
        self.assertEqual(items.get("EchoE01"), quest_before)
        with self.assertRaisesRegex(ValueError, "work radius"):
            build_patches(self.gd, setting(**{"detector:Echo:work": 10}))

    def test_weird_ball_bounds_and_anomaly_ceiling(self):
        with self.assertRaisesRegex(ValueError, "minimum dynamic"):
            build_patches(self.gd, setting(**{"ball:AArtifactWeirdBall:MinWeight": 9}))
        result = build_patches(self.gd, setting(**{"anomaly:LightningBallMediumAnomaly:speed": 50}))
        tree = cfgparse.parse(next(iter(result.values())))
        self.assertEqual(set(tree.children), {"LightningBallMediumAnomaly"})
        self.assertEqual(float(tree.children["LightningBallMediumAnomaly"].values["MovementSpeed"]), 250)
        self.assertEqual(cfgparse.parse_number(tree.children["LightningBallMediumAnomaly"].values["AnomalySpeedToMaxArtifacts"]), 300)

    def test_rarity_normalization_combines_global_preserves_zeros(self):
        s = setting(**{"rarity:UniversalArtifactSpawner:Experienced.Rare": 200})
        s.artifact_rarity_factor = 2
        patch = _artifact_spawner_patch(self.gd, s)
        original = deepcopy(patch)
        a.apply(self.gd, s, "ArtifactSpawnerPrototypes", patch)
        row = patch["UniversalArtifactSpawner"]["Experienced"]["RarityChance"]
        values = {t: cfgparse.parse_number(row.get(t, self.gd.resolve(self.gd.artifactspawners, "UniversalArtifactSpawner", "Experienced.RarityChance." + t))) for t in a.TIERS}
        self.assertAlmostEqual(sum(values.values()), 100, places=6)
        self.assertAlmostEqual(values["Rare"] / values["Epic"], 38, places=6)
        self.assertEqual(patch["UniversalArtifactSpawner"]["Newbie"], original["UniversalArtifactSpawner"]["Newbie"])
        for tier in ("Rare", "Epic"):
            self.assertNotIn(key("rarity:UniversalArtifactSpawner:Newbie." + tier), self.gd.artifact_editor)
        zero = {key("rarity:UniversalArtifactSpawner:Experienced." + tier): 0 for tier in a.TIERS}
        with self.assertRaisesRegex(ValueError, "above zero"):
            build_patches(self.gd, Settings(artifact_overrides=zero))
        uniform = {k: 50 for k in zero}
        self.assertEqual(build_patches(self.gd, Settings(artifact_overrides=uniform)), {})
        self.assertEqual(a.footprint(self.gd, key("rarity:UniversalArtifactSpawner:Experienced.Rare")),
                         {("UniversalArtifactSpawner", tier) for tier in a.TIERS})

    def test_all_five_build_paths_and_sparse_native_output(self):
        s = setting(**{"item:EArtifactFlash:weight": .15, "item:EArtifactFlash:ArtifactProtectionShock1": 150,
                       "item:EArtifactFlash:radiation": 2, "detector:Echo:reveal": 500,
                       "ball:AArtifactWeirdBall:MaxWeight": 3.75, "anomaly:FireBallAnomaly:speed": 50,
                       "rarity:UniversalArtifactSpawner:Experienced.Rare": 200})
        patches = build_patches(self.gd, s)
        self.assertEqual(len(patches), 4)
        for path, text in patches.items():
            tree = cfgparse.parse(text)
            if path.startswith("EffectPrototypes/"):
                self.assertTrue(all("bpatch" not in n.attrs for n in tree.walk()))
            else:
                for top in tree.children.values():
                    self.assertTrue(all(n.attrs == "bpatch" for n in top.walk()))
        self.assertEqual(build_patches(self.gd, Settings()), {})

    def test_native_radiation_identity_and_shielding_are_preserved(self):
        s = setting(**{"item:EArtifactFlash:radiation": 4})
        s.armor_custom = {"Exoskeleton_Neutral_Armor": {"artifact_slots": 5, "lead_slots": 3}}
        result = build_patches(self.gd, s)
        effects = cfgparse.parse(next(text for path, text in result.items() if path.startswith("EffectPrototypes/")))
        self.assertFalse(any(k.startswith("S2Tweaker_Artifact_") for k in effects.children))
        for number in range(1, 4):
            native = self.gd.effects.children[f"ArtifactSlotBlockEffect3_Slot{number}"]
            self.assertIn("ArtifactAddRadiation4", native.children["EffectsToBlockIDs"].values.values())
        self.assertIn(("EArtifactFlash", EFFECT_LIST_LEAF), a.footprint(self.gd, key("item:EArtifactFlash:radiation")))


if __name__ == "__main__":
    unittest.main()
