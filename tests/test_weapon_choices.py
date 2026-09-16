"""Weapon choices: sparse composition, real data, edition routing and conflicts.

These checks validate generator output, not the game's array merge implementation.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse, editor_state, modscan, weapon_choices as choices
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize, _weapon_general_patch, _items_patch


class WeaponChoices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")

    def test_defaults_and_native_selection_are_empty(self):
        self.assertEqual(build_patches(self.gd, Settings()), {})
        for group in choices.GROUPS:
            values = {sid: choices.baseline(self.gd, sid, group)
                      for sid in self.gd.player_weapons()}
            base, dlc = _weapon_general_patch(self.gd, Settings(**{group: values}))
            self.assertFalse(base)
            self.assertFalse(dlc)

    def test_single_mode_replaces_whole_list_and_default(self):
        patch, _ = _weapon_general_patch(self.gd, Settings(weapon_fire_modes={"GunAK74_ST": "SemiAutomatic"}))
        node = patch["GunAK74_ST"]
        self.assertEqual(node["FireTypes"], {"__new__": True, "[0]": "EFireType::SemiAutomatic"})
        self.assertEqual(node["DefaultFireType"], "EFireType::SemiAutomatic")
        self.assertNotIn("FireQueueCount", node)
        files = build_patches(self.gd, Settings(weapon_fire_modes={"GunAK74_ST": "SemiAutomatic"}))
        tree = cfgparse.parse(next(t for p, t in files.items() if "WeaponGeneralSetup" in p))
        node = tree.children["GunAK74_ST"]
        self.assertIn("bpatch", node.attr_dict())
        self.assertNotIn("bpatch", node.children["FireTypes"].attr_dict())

    def test_burst_composes_with_rate_magazine_caliber_and_types(self):
        settings = Settings(weapon_fire_modes={"GunAK74_ST": "Queue"},
                            weapon_ammo_types={"GunAK74_ST": "ArmorPiercing"},
                            weapon_calibers={"GunAK74_ST": "A556"},
                            weapon_overrides={"GunAK74_ST": {"magazine": 2, "firerate": 1.5}})
        patch, _ = _weapon_general_patch(self.gd, settings)
        node = patch["GunAK74_ST"]
        self.assertEqual(int(node["FireQueueCount"]), choices.burst_count(self.gd, "GunAK74_ST"))
        self.assertGreater(int(node["FireQueueCount"]), 1)
        self.assertEqual(node["AmmoCaliber"], "EAmmoCaliber::A556")
        self.assertIn("MaxAmmo", node)
        self.assertIn("FireInterval", node)
        slot = node["AmmoTypeProjectiles"]["[0]"]
        self.assertEqual(slot["AmmoType"], "EAmmoType::ArmorPiercing")
        self.assertEqual(slot["ProjectilePrototypeSID"], self.gd.ammo_caliber_projectiles()["A556"]["ArmorPiercing"])
        self.assertEqual(set(node["AmmoTypeProjectiles"]), {"__new__", "[0]"})
        self.assertTrue(any("fire modes -> Burst" in line for line in summarize(settings)))

    def test_existing_burst_length_is_preserved(self):
        self.assertEqual(choices.burst_count(self.gd, "GunIntegral_PP"), 2)
        patch, _ = _weapon_general_patch(self.gd, Settings(weapon_fire_modes={"GunIntegral_PP": "Queue"}))
        self.assertNotIn("FireQueueCount", patch["GunIntegral_PP"])

    def test_new_native_ammo_kind_and_projectile_specificity(self):
        self.assertNotIn("Default", self.gd.weapon_ammo_slots("GunSVDM_SP").values())
        patch, _ = _weapon_general_patch(self.gd, Settings(weapon_ammo_types={"GunSVDM_SP": "Default,ArmorPiercing"}))
        kinds = patch["GunSVDM_SP"]["AmmoTypeProjectiles"]
        self.assertEqual([v["AmmoType"] for k, v in kinds.items() if k != "__new__"],
                         ["EAmmoType::Default", "EAmmoType::ArmorPiercing"])
        patch, _ = _weapon_general_patch(self.gd, Settings(weapon_ammo_types={"GunAK74_ST": "ArmorPiercing"},
                                                        weapon_calibers={"GunAK74_ST": "A012"}))
        self.assertEqual(patch["GunAK74_ST"]["AmmoTypeProjectiles"]["[0]"]["ProjectilePrototypeSID"], "P012F")

    def test_invalid_or_nonexistent_ammo_is_not_invented(self):
        for value in ("Expanding", "Default,Default", "Bogus", ["Default"]):
            with self.subTest(value=value):
                patch, _ = _weapon_general_patch(self.gd, Settings(weapon_ammo_types={"GunPM_HG": value}))
                self.assertFalse(patch)
        self.assertFalse(choices.clean(self.gd, {"MissingGun": "Automatic"}, choices.GROUPS[0]))
        self.assertNotIn("Expanding", choices.ammo_types(self.gd, "A918"))

    def test_existing_type_retains_weapon_specific_projectile_and_metadata(self):
        original = choices.block(self.gd, "GunAK74_ST", "AmmoTypeProjectiles")
        slot = original.children["[1]"]
        previous = dict(slot.values)
        try:
            slot.values.update(ProjectilePrototypeSID="SpecificNativeProjectile", ExtraNativeField="keep")
            patch, _ = _weapon_general_patch(self.gd, Settings(weapon_ammo_types={"GunAK74_ST": "ArmorPiercing"}))
            emitted = patch["GunAK74_ST"]["AmmoTypeProjectiles"]["[0]"]
            self.assertEqual(emitted["ProjectilePrototypeSID"], "SpecificNativeProjectile")
            self.assertEqual(emitted["ExtraNativeField"], "keep")
        finally:
            slot.values.clear()
            slot.values.update(previous)

    def test_edition_setup_is_written_only_to_its_edition(self):
        sid, ed = next(iter(self.gd.dlc_weapon_editions().items()))
        options = choices.options(self.gd, sid, choices.GROUPS[0])
        target = next(v for v in options if v != choices.baseline(self.gd, sid, choices.GROUPS[0]))
        patch, dlc = _weapon_general_patch(self.gd, Settings(weapon_fire_modes={sid: target}))
        self.assertNotIn(sid, patch)
        self.assertIn(sid, dlc[ed])
        files = build_patches(self.gd, Settings(weapon_fire_modes={sid: target}))
        self.assertTrue(any("DLCGameData" in path for path in files))

    def test_history_and_profiles_keep_choices_and_reject_malformed_values(self):
        value = {"weapon_fire_modes": {"GunAK74_ST": "Queue"},
                 "weapon_ammo_types": {"GunSVDM_SP": "Default,ArmorPiercing"}}
        state = editor_state.state_only(value)
        history = editor_state.History(editor_state.state_only({}))
        history.commit(state)
        self.assertFalse(history.undo()["weapon_fire_modes"])
        self.assertEqual(history.redo(), state)
        self.assertEqual(len(editor_state.differences({}, state)), 2)
        for bad in ("Bogus", 3, ["Automatic"], "Automatic,Automatic"):
            with self.assertRaises(ValueError):
                editor_state.state_only({"weapon_fire_modes": {"GunAK74_ST": bad}})

    def test_inventory_and_slot_reassertions_are_scanned(self):
        root = cfgparse.parse("""TestItem : struct.begin
            ItemGridWidth = 4
            ItemGridHeight = 2
            ItemSlotType = EInventoryEquipmentSlot::PrimaryWeapon
            Cost = 10
        struct.end""")
        baseline = {("TestItem", key): {modscan._norm_value(value)}
                    for key, value in root.children["TestItem"].values.items()}
        pairs = modscan.collect_pairs(root, baseline)
        self.assertEqual(pairs, {("TestItem", key) for key in
                                ("ItemGridWidth", "ItemGridHeight", "ItemSlotType")})
        fire = cfgparse.parse("""TestGun : struct.begin
            FireTypes : struct.begin
                [0] = EFireType::Automatic
            struct.end
            FireIntervalModifiers : struct.begin
                [0] = 1.0
            struct.end
        struct.end""")
        pairs = modscan.collect_pairs(fire)
        self.assertIn(("TestGun", "@FireTypes"), pairs)
        self.assertIn(("TestGun", "[0]"), pairs)  # Unrelated numeric array still retained.

    def test_item_category_uses_linked_weapon_setup(self):
        slots = self.gd.slot_weapon_items()
        self.assertEqual(slots["GunFora230_PP"][0], "smg")
        self.assertEqual(slots["GunArev_ST"][0], "rifle")
        smg, *_ = _items_patch(self.gd, Settings(pistol_slot_level=1))
        self.assertIn("ItemSlotType", smg["GunFora230_PP"])
        self.assertNotIn("GunArev_ST", smg)
        both, *_ = _items_patch(self.gd, Settings(pistol_slot_level=2))
        self.assertIn("ItemSlotType", both["Gun_Texas_SG"])

    def test_new_weapons_already_receive_inventory_dimensions(self):
        files = build_patches(self.gd, Settings(item_grid_factor=.5))
        text = "\n".join(files.values())
        root = cfgparse.parse(text)
        for sid in ("GunArev_ST", "GunFora230_PP"):
            self.assertEqual(root.children[sid].values["ItemGridHeight"], "1")
            self.assertEqual(root.children[sid].values["ItemGridWidth"], "2")


if __name__ == "__main__":
    unittest.main()
