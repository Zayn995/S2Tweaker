"""Independent controls must not undo siblings through unchanged assignments.

Synthetic fixtures exercise the documented merge contract, not the game engine.
Installed-data cases cover full assembly and inheritance without shipping GSC data.
"""
import copy
import itertools
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, detail_controls, emit, tweaks
from s2tweaker.editor_preview import base_file
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches
from test_npc_patch_compatibility import apply_bpatch, leaves

VANILLA = ROOT / "vanilla/Stalker2/Content/GameLite/GameData"


def same(a, b):
    if a == b:
        return True
    x, y = (cfgparse.parse_number(v, math.nan) for v in (a, b))
    return math.isfinite(x) and math.isfinite(y) and math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-9)


class Synthetic(unittest.TestCase):
    def test_flashlight_bands_preserve_identity_zero_and_unknown_fields(self):
        gd = GameData(Path("unused"))
        gd.flashlights = cfgparse.parse("""
[9] : struct.begin
 SID = NPCFlashlight
 ExtraLightDistanceBasedParameters : struct.begin
  [4] : struct.begin
   Distance = 321
   Intencity = 10.f
   AttenuationRadius = 30.f
   OuterConeAngle = 40.f
   FutureField = 99
  struct.end
  [8] : struct.begin
   Intencity = 0.f
  struct.end
 struct.end
struct.end
""")
        a = cfgparse.parse(emit.emit_patch(tweaks._flashlight_patch(gd, Settings(npc_flashlight_factor=2))))
        b = cfgparse.parse(emit.emit_patch(tweaks._flashlight_patch(gd, Settings(npc_flashlight_cone_factor=3))))
        self.assertFalse(leaves(a).keys() & leaves(b).keys())
        self.assertEqual(len(leaves(a)), 2)
        self.assertEqual(len(leaves(b)), 1)
        expected = leaves(gd.flashlights)
        expected.update({"[9]/ExtraLightDistanceBasedParameters/[4]/Intencity": "20.0f",
                         "[9]/ExtraLightDistanceBasedParameters/[4]/AttenuationRadius": "60.0f",
                         "[9]/ExtraLightDistanceBasedParameters/[4]/OuterConeAngle": "120.0f"})
        for first, second in ((a, b), (b, a)):
            self.assertEqual(leaves(apply_bpatch(apply_bpatch(gd.flashlights, first), second)), expected)

    def test_detail_cancellation_removes_only_its_own_leaf(self):
        patch = {"AISettings": {"WeatherSettings": {"[7]": {"VisibilityCoef": ".7f", "HearingDistanceCoef": ".2f"}}}}
        row = {"WeatherSID": "Rainy", "VisibilityCoef": ".9f", "HearingDistanceCoef": ".6f"}
        detail_controls._write(patch, "AISettings", "WeatherSettings.[7].HearingDistanceCoef", ".60f", ".6f", row)
        self.assertEqual(patch, {"AISettings": {"WeatherSettings": {"[7]": {"VisibilityCoef": ".7f"}}}})
        self.assertEqual(row["HearingDistanceCoef"], ".6f")

    def test_carry_caps_use_live_values_and_observed_indices(self):
        gd = GameData(Path("unused"))
        gd.weightparams = cfgparse.parse("DefaultWeightParams : struct.begin\nMaxInventoryMass = 120\nstruct.end")
        gd.effectmax = cfgparse.parse("""
DefaultEffectMaxParamsSID : struct.begin
 MaxEffectValues : struct.begin
  [17] : struct.begin
   EffectSID = EEffectType::PenaltyLessWeight
   MaxValue = 210.f
  struct.end
  [29] : struct.begin
   EffectSID = EEffectType::AdditionalInventoryWeight
   MaxValue = 330.f
  struct.end
 struct.end
struct.end
""")
        patch = tweaks._effect_max_patch(gd, Settings(max_carry_weight=240))
        self.assertEqual(patch, {"DefaultEffectMaxParamsSID": {"MaxEffectValues": {
            "[17]": {"MaxValue": "420.0f"}, "[29]": {"MaxValue": "660.0f"}}}})


@unittest.skipUnless((VANILLA / "CoreVariables.cfg").is_file(), "installed game data only")
class InstalledData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(VANILLA)

    def assignments(self, settings):
        result = {}
        for path, text in build_patches(self.gd, settings).items():
            base = base_file(path)
            if base is None:
                continue
            root = self.gd._parse(base)
            for leaf, value in leaves(cfgparse.parse(text)).items():
                sid, nested = leaf.split("/", 1)
                raw = self.gd.resolve(root, sid, nested.replace("/", "."))
                self.assertIsNotNone(raw, (path, leaf))
                self.assertFalse(same(value, raw), (path, leaf, value))
                result[(base, leaf)] = value
        return result

    def test_independent_families_commute_and_match_combined_export(self):
        groups = [
            ({"npc_flashlight_factor": 2}, {"npc_flashlight_cone_factor": 1.5}),
            ({"radiation_dose_factor": 2}, {"radiation_filter_factor": .5}, {"geiger_volume_factor": .5}),
            ({"jam_clear_factor": 2}, {"jam_chance_factor": .5}),
            ({"encounter_wounded_factor": .5}, {"encounter_dead_factor": .5}),
            ({"squad_expansion_factor": 2}, {"camp_life_factor": 2}),
            ({"map_reveal_factor": 2}, {"map_all_regions": True}),
            ({"detail_overrides": {"detail_edit:weather:Rainy:VisibilityCoef": 200}},
             {"detail_overrides": {"detail_edit:weather:Rainy:HearingDistanceCoef": 200}}),
        ]
        for group in groups:
            with self.subTest(group=group):
                parts = [self.assignments(Settings(**choice)) for choice in group]
                self.assertTrue(all(parts))
                for a, b in itertools.combinations(parts, 2):
                    self.assertFalse(a.keys() & b.keys())
                options = {}
                for choice in group:
                    for key, value in choice.items():
                        if isinstance(value, dict):
                            options.setdefault(key, {}).update(value)
                        else:
                            options[key] = value
                expected = self.assignments(Settings(**options))
                for order in itertools.permutations(parts):
                    merged = {}
                    for part in order:
                        merged.update(part)
                    self.assertEqual(merged, expected)

    def test_additional_existing_row_controls_are_sparse(self):
        for options in (
            {"max_carry_weight": 160}, {"penalty_start_weight": 25},
            {"protection_cap_factor": .5}, {"effect_cap_other_factor": 2},
            {"npc_hearing_factor": 2}, {"mutant_hearing_factor": 2},
            {"movement_noise_factor": .5}, {"crouch_stealth_factor": 2},
            {"weather_stealth_factor": 2}, {"explosive_container_factor": .5},
            {"weather_transition_factor": 2}, {"grenade_resist_factor": 0},
            {"limp_threshold_factor": 2}, {"repair_cost_reputation": True},
            {"stamina_sprint": .5}, {"artifact_caches_drop": True},
            {"repeatable_jobs_per_round": 6}, {"surface_noise_overrides": {"Grass": .5}},
        ):
            with self.subTest(options=options):
                self.assertTrue(self.assignments(Settings(**options)))
        self.assertEqual(build_patches(self.gd, Settings()), {})

    def test_legacy_job_pin_and_rearm_do_not_restore_other_connections(self):
        gd = self.gd
        first = tweaks._quest_dialog_patch(gd, Settings(repeatable_jobs_instant=True))
        second = tweaks._quest_multi_patch(gd, Settings(repeatable_jobs_multi=True))
        a, b = [cfgparse.parse(emit.emit_patch(p)) for p in (first, second)]
        self.assertFalse(leaves(a).keys() & leaves(b).keys())
        for sid in set(first) | set(second):
            base = copy.deepcopy(gd.questnodes.children[sid])
            x, y = a.children.get(sid), b.children.get(sid)
            expected = leaves(base)
            for patch in (x, y):
                if patch:
                    expected.update(leaves(patch))
            for order in ((x, y), (y, x)):
                result = base
                for patch in order:
                    if patch:
                        result = apply_bpatch(result, patch)
                self.assertEqual(leaves(result), expected)

    def test_scope_zoom_and_penalties_preserve_other_effect_references(self):
        gd = self.gd
        for sid, (zoom, penalties) in gd.scope_effects().items():
            if not zoom or not penalties:
                continue
            with self.subTest(scope=sid):
                outputs = [tweaks._scope_override_patch(gd, Settings(scope_overrides={sid: {param: .5}}))[1]
                           for param in ("zoom", "penalty")]
                first, second = [cfgparse.parse(emit.emit_patch(p)) for p in outputs]
                self.assertFalse(leaves(first).keys() & leaves(second).keys())
                combined = tweaks._scope_override_patch(gd, Settings(scope_overrides={sid: {"zoom": .5, "penalty": .5}}))[1]
                expected = leaves(apply_bpatch(gd.items, cfgparse.parse(emit.emit_patch(combined))))
                for a, b in ((first, second), (second, first)):
                    self.assertEqual(leaves(apply_bpatch(apply_bpatch(gd.items, a), b)), expected)
                for patch in outputs:
                    for idx, value in patch[sid]["EffectPrototypeSIDs"].items():
                        self.assertNotEqual(value, gd.scope_effect_list(sid)[idx])


if __name__ == "__main__":
    unittest.main()
