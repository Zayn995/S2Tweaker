"""Check independent profile controls and live base/DLC mesh resolution."""
from pathlib import Path
import io,sys,unittest,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from s2tweaker import sound_sync,animation_sync,cfgparse
from s2tweaker.tweaks import Settings
from s2tweaker.gamedata import GameData
from s2tweaker.animation_profile import parse
from unittest.mock import patch

class SoundSyncTests(unittest.TestCase):
    def test_independent_and_neutral_controls(self):
        self.assertFalse(animation_sync.enabled(Settings(sound_sync=True,movement_sound_sync=True)))
        s=Settings(movement_sound_sync=True,walk_speed_factor=.8,run_speed_factor=1.4,reload_speed_factor=1.3)
        values=animation_sync.profile_values(s)
        self.assertEqual(values,{'audio.movement':1,'audio.walk':.8,'audio.run':1.4,
                                 'audio.limp.walk':.8,'audio.limp.run':1.4})
        self.assertNotIn('audio.reload',values)
        self.assertIn('audio.walk=0.8',parse(animation_sync.profile_bytes(s)).payload)
        with self.assertRaises(ValueError):
            animation_sync.profile_bytes(Settings(sound_sync=True,reload_speed_factor=1.3))
        with self.assertRaises(ValueError):
            sound_sync.movement_factors(Settings(movement_sound_sync=True,run_speed_factor=4.01))

    def test_base_and_cross_file_dlc_mesh_inheritance(self):
        gd=GameData(Path('unused'))
        gd.__dict__['items']=cfgparse.parse('Base : struct.begin\n GeneralWeaponSetup = GunBase\n MeshPrototypeSID = MeshBase\nstruct.end')
        gd.__dict__['weapongeneral']=cfgparse.parse("GunBase : struct.begin\n WeaponTypeSoundSwitch = Switch.WeaponType-AK74'\nstruct.end")
        gd.__dict__['dlc_editions']={'Test':{'items':cfgparse.parse('DLC : struct.begin {refurl=../ItemPrototypes.cfg; refkey=Base}\nstruct.end')}}
        meshes=cfgparse.parse("[77] : struct.begin\n SID = MeshBase\n MeshPath = SkeletalMesh'/Game/Weapons/Custom.Custom'\nstruct.end")
        with patch.object(gd,'slot_weapon_items',return_value={'DLC':('AR','Primary','Test')}),patch('s2tweaker.sound_sync.cfgparse.parse_file',return_value=meshes):
            self.assertEqual(sound_sync.mesh_targets(gd),{'audio.mesh.Custom':1})
            settings=Settings(sound_sync=True,movement_sound_sync=True,
                              reload_speed_factor=1.3,walk_speed_factor=.8)
            exported=animation_sync.export_changes(settings,Path('unused/test.pak'),gd=gd)
            with zipfile.ZipFile(io.BytesIO(next(iter(exported.values())))) as archive:
                payload=parse(archive.read('Profile/'+animation_sync.PROFILE_SLOT+'.sav')).payload
            self.assertIn('audio.mesh.Custom=1',payload)
            self.assertIn('audio.reload=1.3',payload)
            self.assertIn('audio.walk=0.8',payload)
            self.assertNotIn('movement.crouch',payload)

if __name__=='__main__':unittest.main()
