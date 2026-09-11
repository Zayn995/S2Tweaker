"""Regional scope, weather history, factor composition and portable settings."""
from pathlib import Path
import ast
import copy
import math
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, editor_state, extension_controls, regional_weather as weather
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, _weather_patch, build_patches, summarize

REGION = "LesserZoneWeather"
RED = "RedForestWeatherSelectionMain"
VANILLA = ROOT / "vanilla/Stalker2/Content/GameLite/GameData"


def profile(name, clear=12, rain=7):
    rows = []
    for key, weight, increase in (("Clearly", clear, 0), ("Cloudy", 9, 0),
                                  ("Fogy", 3, 0), ("Rainy", rain, 0),
                                  ("LightRainy", 11, 15), ("Stormy", 0, 0),
                                  ("Thundery", 0, 0), ("Emission", 0, 100),
                                  ("CalmBeforeEmission", 0, 0), ("Underground", 0, 0)):
        rows.append(f"""{key} : struct.begin
BlendWeight = {weight}.f
BlendWeightIncrease = {increase}.f
WeatherDurationMin = 13.f
WeatherDurationMax = 19.f
MaximumRepeatAmount = 2
MaximumCooldownWeatherAmount = 1
bAllowInDialogueTransition = true
struct.end""")
    return f"{name} : struct.begin\nSID = {name}\nPriority = 14\n" + "\n".join(rows) + "\nstruct.end\n"


class RegionalWeather(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        names = (REGION, "GarbageWeather", RED, "RedForestWeatherSelectionSide",
                 "SQ10_NoEmission_Weather", "Region_ChemicalPlant", "SIIRCAWeatherSelection", "[1]")
        (folder / "WeatherSelectionPrototypes.cfg").write_text(
            "".join(profile(n, clear=24 if n == RED else 12) for n in names), encoding="utf-8")
        self.gd = GameData(folder)

    def settings(self, rows, **kwargs):
        return Settings(regional_weather_overrides={REGION: rows}, **kwargs)

    def test_neutral_is_lazy_and_ignores_unknown_scope(self):
        self.assertEqual(_weather_patch(object(), Settings()), {})
        self.assertEqual(weather.apply(object(), Settings(), {}), {})
        self.assertEqual(summarize(Settings()), [])
        for key in ("[1]", "SQ10_NoEmission_Weather", "Region_ChemicalPlant", "SIIRCAWeatherSelection"):
            s = Settings(regional_weather_overrides={key: {"Rainy": {"weight": 2}}})
            self.assertEqual(_weather_patch(self.gd, s), {})
        self.assertEqual(_weather_patch(self.gd, self.settings({"Emission": {"weight": 2}})), {})

    def test_live_values_only_selected_region_and_leaves(self):
        before = copy.deepcopy(self.gd.weatherselection)
        patch = _weather_patch(self.gd, self.settings({"Fogy": {"weight": 2.5, "duration": 1.5}}))
        self.assertEqual(patch, {REGION: {"Fogy": {
            "BlendWeight": "7.5", "WeatherDurationMin": "19.5", "WeatherDurationMax": "28.5"}}})
        self.assertEqual(self.gd.weatherselection, before)

    def test_zero_removes_starting_weight_and_history_increase(self):
        patch = _weather_patch(self.gd, self.settings({"LightRainy": {"weight": 0}}))
        self.assertEqual(patch, {REGION: {"LightRainy": {"BlendWeight": "0.0", "BlendWeightIncrease": "0.0"}}})
        for kind in ("Stormy", "Thundery"):
            self.assertEqual(_weather_patch(self.gd, self.settings({kind: {"weight": 4, "duration": 2}})), {})
            self.assertNotIn(kind, self.gd.regional_weather[REGION])

    def test_global_factors_multiply_without_scaling_history_twice(self):
        patch = _weather_patch(self.gd, self.settings({"LightRainy": {"weight": .5, "duration": 1.5}},
                                                     rain_factor=2, weather_duration_factor=2))
        row = patch[REGION]["LightRainy"]
        self.assertNotIn("BlendWeight", row)  # 11 * 2 * .5 is vanilla, not a rewrite
        self.assertEqual(row["BlendWeightIncrease"], "7.5")  # 15 * .5, not *2
        self.assertEqual(float(row["WeatherDurationMin"]), 39)
        self.assertEqual(float(row["WeatherDurationMax"]), 57)
        other = patch["GarbageWeather"]["LightRainy"]
        self.assertEqual(float(other["BlendWeight"]), 22)
        self.assertNotIn("BlendWeightIncrease", other)

    def test_cancellation_removes_only_affected_leaves(self):
        patch = _weather_patch(self.gd, self.settings({"Rainy": {"weight": .5, "duration": .5}},
                                                     rain_factor=2, weather_duration_factor=2))
        self.assertNotIn("Rainy", patch[REGION])
        self.assertIn("Fogy", patch[REGION])
        self.assertIn("Emission", patch[REGION])  # the explicitly enabled global duration still applies
        self.assertEqual(set(patch["[1]"]), set(weather.WEATHERS) | {"Emission", "CalmBeforeEmission", "Underground", "SID", "Priority"})

    def test_red_forest_group_uses_each_baseline(self):
        patch = _weather_patch(self.gd, Settings(regional_weather_overrides={RED: {"Clearly": {"weight": 2}}}))
        self.assertEqual(patch, {RED: {"Clearly": {"BlendWeight": "48.0"}},
                                "RedForestWeatherSelectionSide": {"Clearly": {"BlendWeight": "24.0"}}})

    def test_missing_or_partly_inherited_rows_stay_inactive(self):
        root = self.gd.weatherselection
        row = root.children[REGION]
        row.attrs = "refkey=[1]"
        del row.children["Fogy"].values["WeatherDurationMax"]
        self.assertEqual(self.gd.resolve(root, REGION, "Fogy.WeatherDurationMax"), "19.f")
        self.assertNotIn("Fogy", self.gd.regional_weather[REGION])
        self.assertEqual(_weather_patch(self.gd, self.settings({"Fogy": {"duration": .5}})), {})
        root.children.pop("RedForestWeatherSelectionSide")
        self.gd.__dict__.pop("regional_weather")
        self.assertNotIn(RED, self.gd.regional_weather)

    def test_rejects_empty_selection_including_global_rain(self):
        all_zero = {key: {"weight": 0} for key in weather.WEATHERS}
        with self.assertRaisesRegex(ValueError, "Lesser Zone: keep at least one"):
            _weather_patch(self.gd, self.settings(all_zero))
        dry_zero = {key: {"weight": 0} for key in ("Clearly", "Cloudy", "Fogy")}
        with self.assertRaisesRegex(ValueError, "global Rain"):
            _weather_patch(self.gd, self.settings(dry_zero, rain_factor=0))

    def test_invalid_factors_fail_before_emission(self):
        for param, values in (("weight", (-1, 5, math.nan, math.inf, "2", True)),
                              ("duration", (0, .1, 5, math.nan))):
            for value in values:
                with self.subTest(param=param, value=value), self.assertRaises(ValueError):
                    _weather_patch(self.gd, self.settings({"Rainy": {param: value}}))
        for factor in (0, -1, math.inf, math.nan):
            with self.subTest(global_duration=factor), self.assertRaisesRegex(ValueError, "positive durations"):
                _weather_patch(self.gd, self.settings({"Fogy": {"duration": 2}}, weather_duration_factor=factor))

    def test_settings_roundtrip_reset_and_actual_collection_wiring(self):
        specs = list(weather.control_specs())
        sliders = {key: extension_controls.StoredControl(title, lo, hi, default)
                   for key, title, lo, hi, default, _help in specs}
        key = weather.control_key(REGION, "Fogy", "weight")
        sliders[key].set(250)
        state = {"sliders": {k: r.get() for k, r in sliders.items()}}
        path = Path(self.temp.name) / "weather.json"
        editor_state.save_profile(path, state, "Regional weather")
        loaded = editor_state.read_profile(path).state
        for k, value in loaded["sliders"].items():
            sliders[k].set(value)
        # Evaluate the real _collect keyword, so wiring cannot silently disappear.
        tree = ast.parse((ROOT / "s2tweaker/gui.py").read_text(encoding="utf-8"))
        collect = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_collect")
        keyword = next(n for n in ast.walk(collect) if isinstance(n, ast.keyword) and n.arg == "regional_weather_overrides")
        result = eval(compile(ast.Expression(keyword.value), "_collect", "eval"),
                      {"regional_weather": weather, "s": sliders})
        self.assertEqual(result, {REGION: {"Fogy": {"weight": 2.5}}})
        self.assertTrue(summarize(Settings(regional_weather_overrides=result)))
        self.assertEqual(extension_controls.dict_probe(key), {"regional_weather_overrides": {REGION: {"Fogy": {"weight": .5}}}})
        for row in sliders.values():
            row.reset()
        self.assertEqual(weather.collect(sliders), {})


@unittest.skipUnless((VANILLA / "WeatherSelectionPrototypes.cfg").is_file(), "local game data only")
class LiveRegionalWeather(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(VANILLA)

    def test_every_available_choice_only_patches_selected_profiles(self):
        data = self.gd.regional_weather
        self.assertEqual(len(data), 18)
        self.assertEqual(sum(len(rows) for rows in data.values()), 94)
        for region, rows in data.items():
            for kind in rows:
                for param in weather.PARAMS:
                    with self.subTest(region=region, weather=kind, param=param):
                        patch = _weather_patch(self.gd, Settings(**weather.probe(weather.control_key(region, kind, param))))
                        self.assertEqual(set(patch), set(weather.REGIONS[region][1]))
                        for profile_key, entries in patch.items():
                            self.assertEqual(set(entries), {kind})
                            expected_keys = {"BlendWeight", "BlendWeightIncrease"} if param == "weight" else {"WeatherDurationMin", "WeatherDurationMax"}
                            self.assertLessEqual(set(entries[kind]), expected_keys)
                            for leaf, value in entries[kind].items():
                                base = cfgparse.parse_number(self.gd.resolve(self.gd.weatherselection, profile_key, f"{kind}.{leaf}"))
                                self.assertAlmostEqual(float(value), base * .5)

    def test_full_builder_emits_single_weather_file(self):
        s = Settings(regional_weather_overrides={REGION: {"Fogy": {"weight": 2, "duration": 1.5}}})
        patch = build_patches(self.gd, s)
        self.assertEqual(set(patch), {"WeatherSelectionPrototypes/WeatherSelectionPrototypes_patch_S2Tweaker.cfg"})
        parsed = cfgparse.parse(next(iter(patch.values())))
        self.assertEqual(set(parsed.children), {REGION})
        self.assertTrue(all(n.attrs == "bpatch" for n in parsed.children[REGION].walk()))


if __name__ == "__main__":
    unittest.main()
