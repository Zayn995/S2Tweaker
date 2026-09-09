"""Headless regression checks for world controls and live-data composition."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, world_extensions as world, extension_controls as controls
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize


class WorldExtensions(unittest.TestCase):
    def test_neutral_reads_nothing(self):
        self.assertEqual(world.build(object(), Settings()), {})

    def test_zero_and_invalid_originals_are_not_enabled_by_scaling(self):
        for raw in ("0", "-1", "garbage", "nan", "inf", None):
            self.assertIsNone(world._scaled(raw, 2, integer=True))
        self.assertEqual(world._scaled("3", 1.5, integer=True), "5")

    def test_shipped_inline_struct_end_does_not_nest_following_material(self):
        tree = cfgparse.parse("AI : struct.begin\n[0] : struct.begin\nCharacterNoiseCoef = 1.0    struct.end\n[1] : struct.begin\nMaterialType = Grass\nstruct.end\nstruct.end")
        self.assertEqual(set(tree.children["AI"].children), {"[0]", "[1]"})
        self.assertEqual(tree.children["AI"].children["[0]"].values["CharacterNoiseCoef"], "1.0")

    def test_weather_order_uses_current_numeric_indices(self):
        ai = cfgparse.parse("""AISettings : struct.begin
LuminanceSettings : struct.begin
EnvironmentLuminanceCoefficients : struct.begin
WeatherLuminanceCoefficients : struct.begin
[*] : struct.begin
WeatherType = EWeather::Rainy
Coefficient = 0.7
struct.end
[*] : struct.begin
WeatherType = EWeather::Fogy
Coefficient = 0.6
struct.end
struct.end
struct.end
struct.end
struct.end""")
        gd = SimpleNamespace(aiglobals=ai)
        patch = world.build(gd, Settings(weather_luminance_overrides={"Fogy": .5}))
        rows = patch["AIGlobals.cfg"]["AISettings"]["LuminanceSettings"]["EnvironmentLuminanceCoefficients"]["WeatherLuminanceCoefficients"]
        self.assertEqual(rows, {"[1]": {"Coefficient": "0.3", "WeatherType": "EWeather::Fogy"}})

    def test_control_registry_collects_and_resets_nested_overrides(self):
        class Row:
            def __init__(self, value): self.value = value
            def get(self): return self.value
        sliders = {"surface_noise:Grass": Row(50), "surface_noise:Glass": Row(100),
                   "weather_luminance:Fogy": Row(25), "mutant_loot:Boar:chance_factor": Row(50),
                   "mutant_loot:Boar:amount_factor": Row(200)}
        self.assertEqual(controls.collect_factors(sliders, "surface_noise:"), {"Grass": .5})
        self.assertEqual(controls.collect_mutant_loot(sliders), {"Boar": {"chance_factor": .5, "amount_factor": 2}})
        for row in sliders.values(): row.value = 100
        self.assertEqual(controls.collect_mutant_loot(sliders), {})
        self.assertEqual(controls.collect_factors(sliders, "surface_noise:"), {})

    def test_live_surfaces_weather_species_have_working_controls(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        for prefix, choices in (("surface_noise:", world.SURFACES),
                                ("weather_luminance:", world.WEATHERS)):
            for choice in choices:
                with self.subTest(choice=choice):
                    settings = Settings(**controls.dict_probe(prefix + choice))
                    patches = build_patches(gd, settings)
                    self.assertTrue(patches)
                    self.assertTrue(summarize(settings))
                    self.assertNotIn("#", "".join(patches.values()))
        for species in controls.SPECIES:
            for param in ("chance_factor", "amount_factor"):
                with self.subTest(species=species, param=param):
                    settings = Settings(**controls.dict_probe(f"mutant_loot:{species}:{param}"))
                    self.assertTrue(build_patches(gd, settings))
                    self.assertTrue(summarize(settings))

    def test_live_interaction_factors_compose_and_flower_appends(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        settings = Settings(interaction_range_factor=2, mutant_loot_range_factor=1.5,
                            mutant_loot_ground_access=True, weird_flower_permanent=True)
        patches = build_patches(gd, settings)
        core = cfgparse.parse(patches["CoreVariables.cfg_patch_S2Tweaker.cfg"])
        original = cfgparse.parse_number(gd.resolve(gd.corevars, "DefaultConfig", "MutantLootContainerInteractRange"))
        self.assertEqual(cfgparse.parse_number(core.get("DefaultConfig.MutantLootContainerInteractRange")), original * 3)
        self.assertEqual(core.get("DefaultConfig.MutantLootInteractHeightMin"), "0.0")
        flower = patches["ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"]
        self.assertIn("[*] = FlairDistanceModifierEffect", flower)
        self.assertNotIn("[0] =", flower)

    def test_trophy_weights_do_not_touch_ordinary_items_or_templates(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        patch = world.build(gd, Settings(mutant_trophy_weight_factor=.5, mutant_trophy_value_factor=2))
        items = patch["ItemPrototypes.cfg"]
        self.assertGreaterEqual(len(items), 14)
        self.assertNotIn("MutantLootTemplate", items)
        self.assertNotIn("Bandage", items)
        for sid, values in items.items():
            self.assertNotIn(sid, gd._quest_item_sids)
            self.assertAlmostEqual(float(values["Weight"]), cfgparse.parse_number(gd.resolve(gd.items, sid, "Weight")) * .5)
            self.assertAlmostEqual(float(values["Cost"]), cfgparse.parse_number(gd.resolve(gd.items, sid, "Cost")) * 2)

    def test_cancelled_multipliers_do_not_write_vanilla_back(self):
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        settings = Settings(interaction_range_factor=2, mutant_loot_range_factor=.5,
                            mutant_loot_height_factor=.5, loot_amount_factor=2,
                            mutant_loot_overrides={"Boar": {"amount_factor": .5}})
        patches = build_patches(gd, settings)
        core = patches["CoreVariables.cfg_patch_S2Tweaker.cfg"]
        self.assertNotIn("MutantLootContainerInteractRange", core)
        self.assertNotIn("MutantLootInteractHeightMax", core)
        loot = cfgparse.parse(patches["ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_S2Tweaker.cfg"])
        boar = loot.children.get("BoarLootGenerator")
        if boar:
            self.assertTrue(all("MinCount" not in n.values and "MaxCount" not in n.values
                                for n in boar.walk()))


if __name__ == "__main__":
    unittest.main()
