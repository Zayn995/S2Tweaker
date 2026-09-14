"""Check sparse profiles and resolved equipment/limping semantics."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import animation_sync, sound_sync, cfgparse
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches


class RemainingControls(unittest.TestCase):
    def test_shot_profile_is_opt_in_sparse_and_independent(self):
        self.assertEqual(animation_sync.profile_values(Settings(weapon_shot_pct=0)), {})
        self.assertFalse(animation_sync.enabled(Settings(weapon_shot_sync=True)))
        self.assertEqual(animation_sync.profile_values(Settings(weapon_shot_sync=True, weapon_shot_pct=0)),
                         {'visual.shot': 1})
        settings = Settings(weapon_shot_sync=True, weapon_shot_pct=40,
                            weapon_sway_sync=True, weapon_sway_pct=150)
        self.assertEqual(animation_sync.profile_values(settings),
                         {'visual.shot': 1.4, 'visual.sway': 2.5})
        payload = animation_sync.parse(animation_sync.profile_bytes(settings)).payload
        self.assertIn('visual.shot=1.4', payload)
        for invalid in (-1, 101, float('nan'), float('inf'), True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                animation_sync.profile_values(Settings(weapon_shot_sync=True, weapon_shot_pct=invalid))

    def test_sway_zero_is_explicit_and_neutral_is_sparse(self):
        self.assertFalse(animation_sync.enabled(Settings(weapon_sway_sync=True)))
        self.assertEqual(animation_sync.profile_values(Settings(weapon_sway_sync=True,weapon_sway_pct=0)),
                         {'visual.sway':1})
        self.assertEqual(animation_sync.profile_values(Settings(weapon_sway_pct=0)),{})
        with self.assertRaises(ValueError):
            animation_sync.profile_bytes(Settings(weapon_sway_sync=True,weapon_sway_pct=float('nan')))

    def test_limp_limit_is_read_live_and_composes_with_gaits(self):
        gd=GameData(Path('unused'))
        gd.__dict__['obj']=cfgparse.parse('Player : struct.begin\n MovementParams : struct.begin\n LimpSpeedCoef = 0.8\n struct.end\nstruct.end')
        s=Settings(animation_sync=True,movement_sound_sync=True,limp_speed_factor=2,walk_speed_factor=.8,run_speed_factor=1.4)
        values=animation_sync.profile_values(s,gd)
        self.assertAlmostEqual(values['movement.limp.walk'],1)
        self.assertAlmostEqual(values['movement.limp.run'],1.75)
        self.assertAlmostEqual(values['audio.limp.run'],1.75)

    def test_equipment_override_alone_requests_companion(self):
        self.assertTrue(animation_sync.enabled(Settings(sound_sync=True,weapon_overrides={'GunA':{'equiptime':1.3}})))
        self.assertFalse(animation_sync.enabled(Settings(weapon_overrides={'GunA':{'equiptime':1.3}})))

    @unittest.skipUnless(Path('vanilla/Stalker2/Content/GameLite/GameData').exists(),'requires local game snapshot')
    def test_live_equipment_cfg_rates_and_audio_agree(self):
        gd=GameData(Path('vanilla/Stalker2/Content/GameLite/GameData'))
        s=Settings(sound_sync=True,equip_speed_factor=1.5)
        self.assertFalse(build_patches(gd,Settings()))
        patches=build_patches(gd,s)
        targets=sound_sync.profile_values(s,gd)
        self.assertIn('audio.equip.SK_AK74',targets)
        self.assertEqual(targets['audio.equip.SK_AK74'],1.5)
        rows=cfgparse.parse(patches['WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg'])
        for sid,row in rows.children.items():
            for key in ('ShowEquipmentTime','HideEquipmentTime'):
                baseline=cfgparse.parse_number(gd.resolve(gd.weapongeneral,sid,key))
                self.assertAlmostEqual(cfgparse.parse_number(row.values[key]),baseline*1.5,places=3)


if __name__=='__main__':unittest.main()
