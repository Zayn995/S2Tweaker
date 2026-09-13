"""Check disjoint Pak writes and the documented recursive bpatch contract.

Synthetic fixtures run in CI. Optional installed-data checks exercise the full
builder. The local merge model is not an Unreal parser or an in-game test.
"""
from pathlib import Path
import copy
import itertools
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, emit, modscan, pakfile, pakio
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, _difficulty_patch, _threats_patch, _weather_patch, build_patches

VANILLA = ROOT / "vanilla/Stalker2/Content/GameLite/GameData"
MIN = "AccumulatedDamageReductionCurveWeightMin"
MAX = "AccumulatedDamageReductionCurveWeightMax"


def apply_bpatch(base, patch):
    """Model documented node merge/replacement rules, independently of builders."""
    result = copy.deepcopy(base)
    result.values.update(patch.values)
    for key, child in patch.children.items():
        if key in result.children and "bpatch" in child.attr_dict():
            result.children[key] = apply_bpatch(result.children[key], child)
        else:
            result.children[key] = copy.deepcopy(child)
    return result


def leaves(node, prefix=""):
    result = {prefix + key: value.strip() for key, value in node.values.items()}
    for key, child in node.children.items():
        result.update(leaves(child, prefix + key + "/"))
    return result


class PatchCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.gd = GameData(self.folder)
        self.gd.threats = cfgparse.parse("""
[7] : struct.begin
SID = DefaultNPC
ID = 71
MaxThreatLevelValue = 900
DefaultThreatValueFreezeTimeSeconds = 16.0
DefaultThreatValueLossPerSecond = 24.0
ShowThreatIndicator = true
ThreatParams : struct.begin
[3] : struct.begin
Type = EThreatType::Sound
ThreatValue = 123
ConfidenceDropToZeroTimeSeconds = 0.0
RelationLevels =
struct.end
struct.end
Actions : struct.begin
[2] : struct.begin
Type = EThreatActionType::TurnHead
ThreatLevelValueMin = 120
ThreatLevelValueMax = 900
ThreatValueFreezeTimeSeconds = 8.0
ThreatValueLossPerSecond = 12.0
struct.end
[9] : struct.begin
Type = EThreatActionType::SearchEnemy
ThreatLevelValueMin = 240
ThreatLevelValueMax = 900
ThreatValueFreezeTimeSeconds = 40.0
ThreatValueLossPerSecond = 20.0
struct.end
struct.end
struct.end
[8] : struct.begin
SID = SpecialBoss
DefaultThreatValueFreezeTimeSeconds = 987
struct.end
""")
        self.gd.difficulty = cfgparse.parse(f"""
Easy : struct.begin
NPCCombatDifficulty : struct.begin
{MIN} = 1.0
{MAX} = 1.0
Unrelated = 19
struct.end
struct.end
Medium : struct.begin {{refkey=Easy}}
NPCCombatDifficulty : struct.begin
{MIN} = 0.2
{MAX} = 0.6
struct.end
struct.end
Custom : struct.begin {{refkey=Easy}}
struct.end
Inherited : struct.begin {{refkey=Medium}}
NPCCombatDifficulty : struct.begin
Unrelated = 27
struct.end
struct.end
Zero : struct.begin
NPCCombatDifficulty : struct.begin
{MIN} = 0.0
{MAX} = 0.0
struct.end
struct.end
Unknown : struct.begin
struct.end
""")

    def threat(self, **settings):
        return emit.emit_patch(_threats_patch(self.gd, Settings(**settings)))

    def test_search_and_alertness_are_disjoint_and_commute(self):
        baseline = leaves(self.gd.threats)
        alert = cfgparse.parse(self.threat(npc_alertness_factor=2))
        search = cfgparse.parse(self.threat(npc_search_time_factor=10))
        combined = cfgparse.parse(self.threat(npc_alertness_factor=2, npc_search_time_factor=10))
        self.assertFalse(leaves(alert).keys() & leaves(search).keys())
        self.assertEqual(len(leaves(alert)), 2)
        self.assertEqual(len(leaves(search)), 6)
        self.assertEqual(set(alert.children), {"[7]"})
        for patch in (alert, search, combined):
            self.assertTrue(all(n.attrs == "bpatch" for top in patch.children.values() for n in top.walk()))
            self.assertTrue(all(baseline[k] != v for k, v in leaves(patch).items()))
        expected = dict(baseline)
        expected.update({
            "[7]/Actions/[2]/ThreatLevelValueMin": "60",
            "[7]/Actions/[9]/ThreatLevelValueMin": "120",
            "[7]/DefaultThreatValueFreezeTimeSeconds": "160.0",
            "[7]/DefaultThreatValueLossPerSecond": "2.4",
            "[7]/Actions/[2]/ThreatValueFreezeTimeSeconds": "80.0",
            "[7]/Actions/[2]/ThreatValueLossPerSecond": "1.2",
            "[7]/Actions/[9]/ThreatValueFreezeTimeSeconds": "400.0",
            "[7]/Actions/[9]/ThreatValueLossPerSecond": "2.0",
        })
        for first, second in ((alert, search), (search, alert)):
            actual = apply_bpatch(apply_bpatch(self.gd.threats, first), second)
            self.assertEqual(leaves(actual), expected)
        self.assertEqual(leaves(apply_bpatch(self.gd.threats, combined)), expected)

    def test_pak_roundtrip_and_conflict_scan(self):
        footprints = []
        for name, settings in (("Search", {"npc_search_time_factor": 10}),
                               ("Alertness", {"npc_alertness_factor": 2})):
            path = f"AIPrototypes/ThreatPrototypes/ThreatPrototypes_patch_{name}.cfg"
            patch = {path: self.threat(**settings)}
            pak = pakio.pack_mod(patch, self.folder / f"{name}_P.pak")
            with pakfile.PakFile(pak) as archive:
                readback = archive.read("Stalker2/Content/GameLite/GameData/" + path).decode("utf-8")
            self.assertEqual(leaves(cfgparse.parse(readback)), leaves(cfgparse.parse(patch[path])))
            info = modscan.scan_pak(pak)
            self.assertTrue(info.readable)
            footprints.append(modscan.pairs_from_patches(patch))
            self.assertEqual(footprints[-1], info.pairs)
        self.assertFalse(footprints[0] & footprints[1])
        # Old full-profile Paks still conflict and must be regenerated.
        legacy = modscan.collect_pairs(self.gd.threats)
        self.assertTrue(legacy & footprints[0])
        self.assertTrue(legacy & footprints[1])

    def test_mercy_resolves_inheritance_and_preserves_legacy_cap(self):
        patch = _difficulty_patch(self.gd, Settings(damage_mercy_factor=3))
        self.assertEqual(set(patch), {"Medium", "Inherited"})
        for row in patch.values():
            self.assertEqual(row, {"NPCCombatDifficulty": {MIN: "0.6", MAX: "1.0"}})
        zero = _difficulty_patch(self.gd, Settings(damage_mercy_factor=0))
        self.assertEqual(set(zero), {"Easy", "Medium", "Custom", "Inherited"})
        self.assertTrue(all(row["NPCCombatDifficulty"] == {MIN: "0.0", MAX: "0.0"} for row in zero.values()))

    def test_mercy_extended_mode_scales_every_nonzero_profile(self):
        before = copy.deepcopy(self.gd.difficulty)
        patch = _difficulty_patch(self.gd, Settings(damage_mercy_factor=3, damage_mercy_uncapped=True))
        self.assertEqual(set(patch), {"Easy", "Medium", "Custom", "Inherited"})
        for name in ("Easy", "Custom"):
            self.assertEqual(patch[name]["NPCCombatDifficulty"], {MIN: "3.0", MAX: "3.0"})
        for name in ("Medium", "Inherited"):
            self.assertEqual(patch[name]["NPCCombatDifficulty"], {MIN: "0.6", MAX: "1.8"})
        self.assertEqual(self.gd.difficulty, before)
        self.assertEqual(_difficulty_patch(self.gd, Settings(damage_mercy_uncapped=True)), {})
        self.assertEqual(_threats_patch(self.gd, Settings()), {})

    def test_mercy_rejects_nonfinite_or_negative_values(self):
        for value in (float("nan"), float("inf"), -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _difficulty_patch(self.gd, Settings(damage_mercy_factor=value))

    def test_weather_controls_use_disjoint_leaves_in_indexed_templates(self):
        self.gd.weatherselection = cfgparse.parse("""
[5] : struct.begin
SID = TestWeather
Priority = 17
Rainy : struct.begin
BlendWeight = 8.0
WeatherDurationMin = 11.0
WeatherDurationMax = 22.0
Unrelated = 99
struct.end
Emission : struct.begin
BlendWeightIncrease = 4.0
WeatherDurationMin = 33.0
WeatherDurationMax = 44.0
struct.end
struct.end
""")
        choices = ({"rain_factor": 2}, {"emission_factor": 3}, {"weather_duration_factor": 2})
        patches = [cfgparse.parse(emit.emit_patch(_weather_patch(self.gd, Settings(**choice)))) for choice in choices]
        for a, b in itertools.combinations(patches, 2):
            self.assertFalse(leaves(a).keys() & leaves(b).keys())
        combined = cfgparse.parse(emit.emit_patch(_weather_patch(self.gd, Settings(
            rain_factor=2, emission_factor=3, weather_duration_factor=2))))
        expected = leaves(apply_bpatch(self.gd.weatherselection, combined))
        for order in itertools.permutations(patches):
            actual = self.gd.weatherselection
            for patch in order:
                actual = apply_bpatch(actual, patch)
            self.assertEqual(leaves(actual), expected)
        self.assertEqual(expected["[5]/Rainy/Unrelated"], "99")
        self.assertEqual(expected["[5]/Rainy/BlendWeight"], "16.0")
        self.assertEqual(expected["[5]/Emission/BlendWeightIncrease"], "12.0")


@unittest.skipUnless((VANILLA / "DifficultyPrototypes.cfg").is_file(), "local game data only")
class InstalledData(unittest.TestCase):
    def test_reported_settings_in_full_builder(self):
        gd = GameData(VANILLA)
        search = build_patches(gd, Settings(mod_name="Search", npc_search_time_factor=10))
        alert = build_patches(gd, Settings(mod_name="Alertness", npc_alertness_factor=2))
        self.assertFalse(search.keys() & alert.keys())
        self.assertFalse(modscan.pairs_from_patches(search) & modscan.pairs_from_patches(alert))
        combined = build_patches(gd, Settings(npc_search_time_factor=10, npc_alertness_factor=2))
        separate_values = {}
        for output in (search, alert):
            separate_values.update(leaves(cfgparse.parse(next(iter(output.values())))))
        self.assertEqual(separate_values, leaves(cfgparse.parse(next(iter(combined.values())))))
        for name in ("Easy", "Custom", "Default", "Empty"):
            patch = _difficulty_patch(gd, Settings(damage_mercy_factor=3, damage_mercy_uncapped=True))
            for key in (MIN, MAX):
                base = cfgparse.parse_number(gd.resolve(gd.difficulty, name, "NPCCombatDifficulty." + key))
                self.assertAlmostEqual(float(patch[name]["NPCCombatDifficulty"][key]), base * 3)
        self.assertEqual(build_patches(gd, Settings()), {})


if __name__ == "__main__":
    unittest.main()
