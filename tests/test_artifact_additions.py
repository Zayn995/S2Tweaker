"""Extra bonus composition and protection of fake/quest inheritance; no engine test."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from s2tweaker import artifact_extensions as a, artifact_additions as extra, cfgparse
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, _struct_dict, _merge_nested

VANILLA=ROOT/'vanilla/Stalker2/Content/GameLite/GameData'


def key(item,kind):
    return f'{a.PREFIX}item:{item}:extra_{kind}'


def fixture():
    gd=GameData(Path('unused'))
    text='''EArtifactFlash : struct.begin {refkey=TemplateArtifact}
 SID = EArtifactFlash
 Type = EItemType::Artifact
 ArtifactType = EArtifactType::Electro
 EffectPrototypeSIDs : struct.begin
  [2] = ArtifactProtectionShock1
  [7] = ArtifactAddRadiation1
 struct.end
 ShouldShowEffects : struct.begin
  [2] = true
  [7] = true
 struct.end
 EffectsDisplayTypes : struct.begin
  [2] = EEffectDisplayType::EffectLevel
  [10] = EEffectDisplayType::EffectLevel
 struct.end
struct.end
'''
    for sid,parent in [('Fake','EArtifactFlash'),('Nested','Fake')]:
        text+=f'''{sid} : struct.begin {{refkey={parent}}}
 SID = {sid}
 EffectPrototypeSIDs : struct.begin
  [2] = ArtifactProtectionShock1
  [7] = ArtifactAddRadiation1
 struct.end
 ShouldShowEffects : struct.begin
  [2] = true
  [7] = true
 struct.end
 EffectsDisplayTypes : struct.begin
  [2] = EEffectDisplayType::EffectLevel
 struct.end
struct.end
'''
    gd.items=cfgparse.parse(text)
    effects=''
    for sid,value,typ in [('ArtifactProtectionBurn1','13.25f','ProtectionBurn'),
                           ('ArtifactAdditionalInventoryWeight1','4.3','AdditionalInventoryWeight'),
                           ('ArtifactPenaltyLessWeightEffect1','4.3','PenaltyLessWeight'),
                           ('ArtifactProtectionShock1','17.5f','ProtectionShock')]:
        effects+=f'''{sid} : struct.begin {{refkey=[0]}}
 SID = {sid}
 Type = EEffectType::{typ}
 ValueMin = {value}
 ValueMax = {value}
 bIsPermanent = true
 DuplicationType = EDuplicateResolveType::KeepAll
 EffectLevel = EEffectLevel::Low
 LocalizationSID = original_label
struct.end
'''
    gd.effects=cfgparse.parse(effects)
    gd.anomalies=gd.artifactspawners=cfgparse.parse('')
    return gd


class SyntheticAdditions(unittest.TestCase):
    def setUp(self):
        self.gd=fixture()

    def test_sparse_three_array_append_composes_and_shields_transitive_children(self):
        k=key('EArtifactFlash','ProtectionBurn')
        s=Settings(artifact_effect_factor=2,artifact_overrides={k:150,a.PREFIX+'item:EArtifactFlash:ArtifactProtectionShock1':50})
        items,effects={},{}
        a.apply(self.gd,s,'EffectPrototypes',effects)
        a.apply(self.gd,s,'ItemPrototypes',items)
        clone=a.clone_sid(s.mod_name,'EArtifactFlash','extra_ArtifactProtectionBurn1')
        self.assertEqual(effects[clone]['ValueMin'],'39.75f')
        self.assertEqual(effects[clone]['LocalizationSID'],'original_label')
        expected=_struct_dict(self.gd.items.children['EArtifactFlash'])
        for name in extra.ARRAYS:
            self.assertIn('[11]',items['EArtifactFlash'][name])
            self.assertNotIn('[8]',items['EArtifactFlash'][name])
            for index,value in expected[name].items():
                if name=='EffectPrototypeSIDs' and index=='[2]':
                    self.assertEqual(items['EArtifactFlash'][name][index],a.clone_sid(s.mod_name,'EArtifactFlash','ArtifactProtectionShock1'))
                else:
                    self.assertEqual(items['EArtifactFlash'][name][index],value)
        effective=deepcopy(self.gd.items)
        for sid,node in items.items():
            original=_struct_dict(effective.children[sid])
            _merge_nested(original,node)
            # Use emitted CFG with original inheritance to exercise normal resolve().
            from s2tweaker.tweaks import emit_patch
            combined=cfgparse.parse(emit_patch({sid:{'__new__':True,'__attrs__':self.gd.items.children[sid].attrs,**original}}))
            effective.children[sid]=combined.children[sid]
        for sid in ('Fake','Nested'):
            self.assertEqual(self.gd.resolve(effective,sid,'EffectPrototypeSIDs.[11]'),'empty')
            self.assertEqual(self.gd.resolve(effective,sid,'ShouldShowEffects.[11]'),'false')
            self.assertEqual(self.gd.resolve(effective,sid,'EffectPrototypeSIDs.[2]'),'ArtifactProtectionShock1')
        self.assertEqual(self.gd.items.children['EArtifactFlash'].children['EffectPrototypeSIDs'].values,expected['EffectPrototypeSIDs'])

    def test_carry_pair_and_zero_do_not_add_visible_penalty(self):
        s=Settings(artifact_overrides={key('EArtifactFlash','AdditionalInventoryWeight'):250})
        items,effects={},{}
        a.apply(self.gd,s,'EffectPrototypes',effects)
        a.apply(self.gd,s,'ItemPrototypes',items)
        self.assertEqual(len(effects),2)
        self.assertEqual({n['ValueMin'] for n in effects.values()},{'10.75'})
        self.assertEqual(items['EArtifactFlash']['ShouldShowEffects']['[11]'],'true')
        self.assertEqual(items['EArtifactFlash']['ShouldShowEffects']['[12]'],'false')
        s.artifact_effect_factor=0
        for source in ('ItemPrototypes','EffectPrototypes'):
            result={}
            a.apply(self.gd,s,source,result)
            self.assertEqual(result,{})

    def test_existing_family_and_unsafe_schema_not_offered(self):
        self.assertNotIn(key('EArtifactFlash','ProtectionShock'),a.catalog(self.gd))
        self.assertNotIn(key('Fake','ProtectionBurn'),a.catalog(self.gd))
        self.assertNotIn(key('EArtifactFlash','PenaltyLessWeightEffect'),a.CONTROLS)
        self.gd.items.children['Nested'].children.pop('EffectsDisplayTypes')
        self.assertNotIn(key('EArtifactFlash','ProtectionBurn'),a.catalog(self.gd))

    def test_childs_existing_slot_is_never_emptied(self):
        self.gd.items.children['Fake'].children['EffectPrototypeSIDs'].values['[11]']='OwnChildEffect'
        s=Settings(artifact_overrides={key('EArtifactFlash','ProtectionBurn'):100})
        items={}
        a.apply(self.gd,s,'ItemPrototypes',items)
        self.assertNotIn('[11]',items.get('Fake',{}).get('EffectPrototypeSIDs',{}))
        self.assertEqual(items['Nested']['EffectPrototypeSIDs']['[11]'],'OwnChildEffect')


@unittest.skipUnless((VANILLA/'ItemPrototypes.cfg').exists(),'local game data only')
class LiveAdditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd=GameData(VANILLA)

    def test_all_518_choices_have_valid_references_and_preserve_native_slots(self):
        controls=[a.CONTROLS[k] for k in self.gd.artifact_editor if a.CONTROLS[k].param.startswith('extra_')]
        self.assertEqual(len(controls),518)
        for c in controls:
            s=Settings(artifact_overrides={c.key:100})
            items,effects={},{}
            a.apply(self.gd,s,'ItemPrototypes',items)
            a.apply(self.gd,s,'EffectPrototypes',effects)
            original=_struct_dict(self.gd.items.children[c.target])
            for name in extra.ARRAYS:
                for index,value in original[name].items():
                    self.assertEqual(items[c.target][name][index],value,c.key)
            new_indices=set(items[c.target]['EffectPrototypeSIDs'])-set(original['EffectPrototypeSIDs'])
            for index in new_indices:
                self.assertIn(items[c.target]['EffectPrototypeSIDs'][index],effects,c.key)
                for child in extra.descendants(self.gd,c.target):
                    self.assertEqual(items[child]['EffectPrototypeSIDs'][index],'empty',c.key)
                    self.assertEqual(items[child]['ShouldShowEffects'][index],'false',c.key)
            for node in effects.values():
                source=node['__attrs__'].removeprefix('refkey=')
                self.assertEqual(cfgparse.parse_number(node['ValueMin']),cfgparse.parse_number(self.gd.resolve(self.gd.effects,source,'ValueMin')))
                self.assertNotIn('ArtifactAddRadiation',source)
            self.assertTrue(a.footprint(self.gd,c.key))

    def test_liquid_stone_fire_and_existing_chemistry_in_same_export(self):
        s=Settings(artifact_stat_labels_follow=True,artifact_overrides={key('CArtifactLiquidStone','ProtectionBurn'):200,
                   a.PREFIX+'item:CArtifactLiquidStone:ArtifactProtectionChemicalBurn4':50})
        result=build_patches(self.gd,s)
        items=cfgparse.parse(next(v for k,v in result.items() if k.startswith('ItemPrototypes/')))
        effects=cfgparse.parse(next(v for k,v in result.items() if k.startswith('EffectPrototypes/')))
        self.assertEqual(set(items.children),{'CArtifactLiquidStone','CArtifactLiquidStone_Fake'})
        own=items.children['CArtifactLiquidStone'].children['EffectPrototypeSIDs'].values
        self.assertEqual(own['[0]'],'ArtifactProtectionRadiation4')
        self.assertEqual(own['[2]'],'ArtifactDurabilityIncrease4')
        self.assertEqual(effects.children[own['[3]']].values['ValueMin'],'20')
        self.assertEqual(effects.children[own['[3]']].values['EffectLevel'],'EEffectLevel::Strong')
        self.assertEqual(effects.children[own['[1]']].values['ValueMin'],'17.5')
        self.assertEqual(build_patches(self.gd,Settings(artifact_overrides={key('CArtifactLiquidStone','ProtectionBurn'):0})),{})

    def test_all_additions_together_have_unique_slots_and_effects(self):
        selected={k:100 for k in self.gd.artifact_editor if a.CONTROLS[k].param.startswith('extra_')}
        s=Settings(artifact_overrides=selected)
        items,effects={},{}
        a.apply(self.gd,s,'ItemPrototypes',items)
        a.apply(self.gd,s,'EffectPrototypes',effects)
        referenced=[]
        for target in a.ARTIFACTS:
            native=self.gd.items.children[target].children['EffectPrototypeSIDs'].values
            own=items[target]
            added=set(own['EffectPrototypeSIDs'])-set(native)
            for index in added:
                sid=own['EffectPrototypeSIDs'][index]
                referenced.append(sid)
                self.assertIn(sid,effects)
                self.assertIn(index,own['ShouldShowEffects'])
                self.assertIn(index,own['EffectsDisplayTypes'])
            for child in extra.descendants(self.gd,target):
                for index in added:
                    self.assertEqual(items[child]['EffectPrototypeSIDs'][index],'empty')
        self.assertEqual(len(referenced),len(set(referenced)))
        self.assertEqual(set(referenced),set(effects))


if __name__=='__main__':
    unittest.main()
