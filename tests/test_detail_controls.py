"""Data-only extensions: sparse composition, scope protection and editor state."""
from copy import deepcopy
from pathlib import Path
import ast
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, detail_controls as d, detail_effects as effects, npc_equipment as equipment
from s2tweaker import extension_controls, editor_state
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize, _upgrade_strength_patch

VANILLA = ROOT / 'vanilla/Stalker2/Content/GameLite/GameData'


def key(group, target, param):
    return f'{d.PREFIX}{group}:{target}:{param}'


def setting(values, **globals):
    return Settings(detail_overrides={key(*identity): value for identity, value in values.items()}, **globals)


def parsed(files, source):
    matches = [text for path, text in files.items() if path.startswith(source)]
    return cfgparse.parse(matches[0] if matches else '')


class Contracts(unittest.TestCase):
    def test_validation_and_default_history(self):
        controls = {k: extension_controls.ArtifactControl(c) for k, c in d.CONTROLS.items()}
        self.assertEqual(d.collect(controls), {})
        snapshot = {'sliders': {k: c.get() for k, c in controls.items()}}
        history = editor_state.History(snapshot)
        selected = key('special', 'AArtifactWeirdWater', 'minimum')
        controls[selected].set(3.75)
        changed = {'sliders': {k: c.get() for k, c in controls.items()}}
        history.commit(changed)
        self.assertEqual(history.undo(), snapshot)
        self.assertEqual(history.redo(), changed)
        self.assertEqual(editor_state.state_only(changed)['sliders'][selected], 3.75)
        for bad in (math.nan, math.inf, '20', True, -2, 1001):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                controls[selected].set(bad)

    def test_no_animation_control_or_gameplay_state_group(self):
        forbidden = ('Reload', 'MovementSpeed', 'WalkSpeed', 'SprintSpeed', 'AimingTime',
                     'ShowEquipmentTime', 'HideEquipmentTime', 'RecoilRadiusNormalizationInterval')
        for c in d.CONTROLS.values():
            self.assertFalse(any(word in c.param for word in forbidden), c)
        self.assertFalse(summarize(Settings()))
        self.assertIn('sliders', editor_state.GROUPS)
        self.assertNotIn('detail_overrides', editor_state.GROUPS)  # normal slider persistence, not a competing state store

    def test_synthetic_weather_full_rows_and_cancellation(self):
        gd = GameData(Path('unused'))
        gd.__dict__['detail_editor'] = {key('weather', 'Rainy', 'HearingDistanceCoef'): [
            ('AIGlobals', 'AISettings', 'WeatherSettings.[7].HearingDistanceCoef', '.62f',
             {'WeatherSID': 'Rainy', 'VisibilityCoef': '.91f', 'HearingDistanceCoef': '.62f', 'FlairCoef': '.81f'})]}
        s = setting({('weather', 'Rainy', 'HearingDistanceCoef'): 200})
        patch = {}
        d.apply(gd, s, 'AIGlobals', patch)
        self.assertAlmostEqual(cfgparse.parse_number(patch['AISettings']['WeatherSettings']['[7]']['HearingDistanceCoef']), .24)
        self.assertEqual(patch['AISettings']['WeatherSettings']['[7]']['VisibilityCoef'], '.91f')
        s.weather_stealth_factor = .5
        d.apply(gd, s, 'AIGlobals', patch)
        self.assertEqual(patch, {})


@unittest.skipUnless(VANILLA.exists(), 'requires private game-data snapshot')
class InstalledData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(VANILLA)
        cls.data = d.available(cls.gd)

    def test_default_and_registry(self):
        self.assertEqual(build_patches(self.gd, Settings()), {})
        self.assertEqual(sum(d.CONTROLS[k].group == 'medicine' for k in self.data), 16)
        self.assertEqual(sum(d.CONTROLS[k].group == 'weapon_item' for k in self.data), 336)
        self.assertEqual(sum(equipment.CONTROLS[k].kind == 'Chance' for k in equipment.available(self.gd)), 76)
        self.assertEqual(len({c.key for c in d.CONTROLS.values()}), len(d.CONTROLS))

    def test_medicine_composition_keeps_master_sid_and_delivery_time(self):
        s = setting({('medicine', 'Medkit', 'healing'): 125}, consumable_factor=1.2, healing_factor=1.5)
        files = build_patches(self.gd, s)
        tree = parsed(files, 'EffectPrototypes/')
        base = cfgparse.parse_number(self.gd.resolve(self.gd.effects, 'MedkitHealing3', 'ValueMin'))
        self.assertAlmostEqual(cfgparse.parse_number(tree.get('MedkitHealing3.ValueMin')), base * 1.2 * 1.5 * 1.25)
        self.assertIsNone(tree.get('MedkitHealing3.Duration'))
        self.assertNotIn('MasterEffectModifier', tree.children)
        self.assertFalse(any(sid.startswith('S2Tweaker_Detail_') for sid in tree.children))
        self.assertFalse(any('ItemPrototypes/' in path for path in files))

    def test_medical_cancel_only_selected_leaf(self):
        s = setting({('medicine', 'Hercules', 'strength'): 50, ('medicine', 'Hercules', 'duration'): 150},
                    armor_carry_bonus_factor=2, consumable_duration_factor=2)
        tree = parsed(build_patches(self.gd, s), 'EffectPrototypes/')
        self.assertIsNone(tree.get('HerculesWeight.ValueMin'))
        base = cfgparse.parse_number(self.gd.resolve(self.gd.effects, 'HerculesWeight', 'Duration'))
        self.assertEqual(cfgparse.parse_number(tree.get('HerculesWeight.Duration')), base * 3)
        self.assertIsNotNone(tree.get('HerculesWeight_Penalty.ValueMin'))

    def test_hercules_repair_remains_instant_and_unscaled(self):
        s = setting({('medicine', 'Hercules', 'strength'): 200, ('medicine', 'Hercules', 'duration'): 200}, field_repair_body_pct=10)
        files = build_patches(self.gd, s)
        items, tree = parsed(files, 'ItemPrototypes/'), parsed(files, 'EffectPrototypes/')
        self.assertIsNotNone(items.get('Hercules.EffectPrototypeSIDs.[*]'))
        self.assertEqual(items.get('Hercules.ShouldShowEffects.[*]'), 'false')
        repair = [node for sid, node in tree.children.items() if sid.startswith('S2Tweaker_FieldRepair_') and node.values.get('Type') == 'EEffectType::Corrosion']
        self.assertEqual(len(repair), 1)
        self.assertEqual(cfgparse.parse_number(repair[0].values['ValueMin']), -10)
        self.assertNotIn('Duration', repair[0].values)

    def test_nut_and_water_clone_shape_and_native_radiation(self):
        s = setting({('special', 'AArtifactWeirdNut', 'healing_drawback'): 50,
                     ('special', 'AArtifactWeirdWater', 'strength'): 150}, armor_carry_bonus_factor=2)
        files = build_patches(self.gd, s)
        tree, items = parsed(files, 'EffectPrototypes/'), parsed(files, 'ItemPrototypes/')
        nut = effects.clone_sid(s.mod_name, 'AArtifactWeirdNut', 'RegenHealthModifier')
        self.assertEqual(tree.children[nut].attr_dict(), {'refkey': 'RegenHealthModifier'})
        self.assertEqual(tree.get(nut + '.LocalizationSID'), 'Empty')
        self.assertAlmostEqual(cfgparse.parse_number(tree.get(nut + '.ValueMin')), -.375)
        self.assertIsNone(items.get('AArtifactWeirdNut.EffectPrototypeSIDs.[0]'))
        self.assertEqual(items.get('AArtifactWeirdNut.EffectPrototypeSIDs.[1]'), nut)
        comp = effects.clone_sid(s.mod_name, 'AArtifactWeirdWater', effects.COMPOSITE)
        self.assertEqual(items.get('AArtifactWeirdWater.EffectPrototypeSIDs.[0]'), comp)
        self.assertIsNone(items.get('AArtifactWeirdWater.EffectPrototypeSIDs.[1]'))
        self.assertNotIn('ShouldShowEffects', items.children['AArtifactWeirdWater'].children)
        children = tree.children[comp].children['ApplyExtraEffectPrototypeSIDs'].values
        self.assertEqual(len(children), 2)
        carry = tree.children[children['[0]']]
        threshold = tree.children[children['[1]']]
        self.assertEqual(carry.values['ValueMin'], '150%')
        self.assertEqual(threshold.values['ValueMin'], '75%')

    def test_future_effect_sharing_or_item_children_disable_medicine(self):
        gd = GameData(VANILLA)
        gd.__dict__['items'] = deepcopy(self.gd.items)
        gd.items.children['FutureQuest'] = cfgparse.parse('FutureQuest : struct.begin {refkey=Medkit}\n SID = FutureQuest\nstruct.end').children['FutureQuest']
        data = effects.catalog(gd, d.CONTROLS)
        self.assertNotIn(key('medicine', 'Medkit', 'healing'), data)
        del gd.items.children['FutureQuest']
        gd.items.children['FutureShared'] = cfgparse.parse('FutureShared : struct.begin\n EffectPrototypeSIDs : struct.begin\n [0] = MedkitHealing3\n struct.end\nstruct.end').children['FutureShared']
        self.assertNotIn(key('medicine', 'Medkit', 'healing'), effects.catalog(gd, d.CONTROLS))

    def test_weapon_absolute_and_dlc_output(self):
        s = setting({('weapon_item', 'GunPM_HG', 'Weight'): .5, ('weapon_item', 'GunPM_HG', 'Cost'): 123,
                     ('weapon_item', 'Deluxe_GunAK74_ST', 'Weight'): 1.75}, item_weight_factor=.5)
        files = build_patches(self.gd, s)
        items = parsed(files, 'ItemPrototypes/')
        self.assertIsNone(items.get('GunPM_HG.Weight'))
        self.assertEqual(cfgparse.parse_number(items.get('GunPM_HG.Cost')), 123)
        dlc = parsed(files, '//GameLite/DLCGameData/Ultimate/ItemPrototypes/')
        self.assertEqual(cfgparse.parse_number(dlc.get('Deluxe_GunAK74_ST.Weight')), 1.75)
        self.assertIsNone(items.get('Deluxe_GunAK74_ST.Weight'))

    def test_weather_grenades_camp_and_scanner_isolation(self):
        s = setting({('weather', 'Rainy', 'HearingDistanceCoef'): 200,
                     ('grenade', 'Army', 'Veteran'): 50,
                     ('camp', 'Ordinary faction camps', 'Guitar'): 150,
                     ('scanner', 'PlayerDetector', 'DetectorRadius'): 800})
        files = build_patches(self.gd, s)
        ai = parsed(files, 'AIGlobals')
        self.assertEqual(cfgparse.parse_number(ai.get('AISettings.ThrowGrenadeSettings.AvailableGrenadesPerFaction.Army.Veteran')), 4)
        self.assertIsNone(ai.get('AISettings.ThrowGrenadeSettings.AvailableGrenadesPerFaction.KorshunovBoss_Faction'))
        camps = parsed(files, 'NPCNeedsPresetPrototypes/')
        self.assertTrue(camps.children)
        self.assertTrue(all(sid.removesuffix('NeedsPreset') in d.CAMPS for sid in camps.children))
        self.assertTrue(all(node.values.get('NeedType') == 'EContextualActionNeeds::Guitar' for root in camps.children.values() for node in root.children['Needs'].children.values()))
        scanner = parsed(files, 'PassiveDetectorPrototypes/')
        self.assertEqual(set(scanner.children), {'[1]'})
        self.assertEqual(cfgparse.parse_number(scanner.get('[1].DetectorRadius')), 800)

    def test_upgrade_bonus_does_not_change_animation_effects(self):
        s = setting({('upgrade', 'Technician bonuses', 'ArmorPiercing'): 150,
                     ('upgrade', 'Technician bonuses', 'AmmoCapacity'): 200,
                     ('upgrade', 'Technician bonuses', 'Dispersion'): 200})
        patch = _upgrade_strength_patch(self.gd, s)
        self.assertTrue(patch)
        allowed = {'EEffectType::ArmorPiercing', 'EEffectType::AmmoCapacity', 'EEffectType::Dispersion'}
        self.assertTrue(all(self.gd.resolve(self.gd.effects, sid, 'Type') in allowed for sid in patch))
        self.assertNotIn('BattleExoskeleton_Varta_Armor_accuracy', patch)

    def test_helmet_and_weight_share_one_clone_branch(self):
        c = next(c for c in equipment.CONTROLS.values() if c.kind == 'Chance' and c.source == 'GeneralNPC_Militaries_Armor_var2')
        s = Settings(npc_equipment_overrides={c.key: 50}, npc_helmet_chance_factor=2)
        files = build_patches(self.gd, s)
        generators = parsed(files, 'ItemGeneratorPrototypes/')
        name = equipment.clone_sid(s.mod_name, c.obj, c.source)
        self.assertEqual(cfgparse.parse_number(generators.get(name + f'.ItemGenerator.{c.slot}.PossibleItems.{c.row}.Chance')), .5)
        weighted = next(x for x in equipment.CONTROLS.values() if x.obj == c.obj and x.kind == 'Weight' and x.key in equipment.available(self.gd))
        s.npc_equipment_overrides[weighted.key] = 200
        combined = build_patches(self.gd, s)
        gen = parsed(combined, 'ItemGeneratorPrototypes/')
        self.assertIn(name, gen.children)
        objects = parsed(combined, 'ObjPrototypes/')
        self.assertEqual(set(objects.children), {c.obj})
        self.assertEqual(objects.get(c.obj + '.ItemGeneratorPrototypeSID'), equipment.clone_sid(s.mod_name, c.obj, equipment.OBJECTS[c.obj][2]))


if __name__ == '__main__':
    unittest.main()
