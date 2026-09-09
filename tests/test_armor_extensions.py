"""Armor semantics, inheritance, DLC routing and UI state without creating Tk."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import armor_extensions as ext, editor_state, modscan
from s2tweaker.cfgparse import parse
from s2tweaker.emit import emit_patch
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize


def fixture(directory):
    gd = GameData(directory)
    gd.items = parse('''TemplateArmor : struct.begin
 Type = EItemType::Armor
 ItemSlotType = EInventoryEquipmentSlot::Body
 Invisible = false
 Weight = 10
 Cost = 1000
 BaseDurability = 800
 ItemGridWidth = 2
 ItemGridHeight = 3
 ArtifactSlots = 2
 bPreventFromLimping = false
 bBlockHead = false
 NoiseCoef = 1
 Protection : struct.begin
  Strike = 2
  PSY = 0
  Fall = 0
 struct.end
 ProtectionNPC : struct.begin
  Strike = 7
 struct.end
 EffectPrototypeSIDs : struct.begin
  [0] = Carry
  [1] = ArmorConditionalEffect
  [2] = Gas
 struct.end
struct.end
Suit : struct.begin {refkey=TemplateArmor}
 SID = Suit
struct.end
Other : struct.begin {refkey=TemplateArmor}
 SID = Other
struct.end
Hidden : struct.begin {refkey=TemplateArmor}
 Invisible = true
struct.end
TemplateHelmet : struct.begin {refkey=TemplateArmor}
 ItemSlotType = EInventoryEquipmentSlot::Head
 ArtifactSlots = 0
struct.end
Helmet : struct.begin {refkey=TemplateHelmet}
 SID = Helmet
struct.end
''')
    gd.dlc_editions = {"Deluxe": {"items": parse('''EditionSuit : struct.begin {refurl=../GameData/ItemPrototypes/ArmorPrototypes.cfg;refkey=TemplateArmor}
 SID = EditionSuit
 Weight = 12
struct.end
''')}}
    effects = '''[0] : struct.begin
 Type = EEffectType::None
struct.end
ArmorConditionalEffect : struct.begin
 ConditionSID = TargetHasAddSprintEffect
 FalseEffectSID = BlockSprintEffect
struct.end
BlockSprintEffect : struct.begin
 Type = EEffectType::BlockAnimationActionType
 BlockAnimationTypes : struct.begin
  [0] = EActionType::Sprint
 struct.end
struct.end
'''
    for n in range(1, 6):
        effects += f'''ArtifactSlotBlockEffect3_Slot{n} : struct.begin
 Type = EEffectType::ArtifactSlotBlock
 ArtifactEquipmentSlots : struct.begin
  [0] = EInventoryEquipmentSlot::Artifact{n}
 struct.end
 EffectsToBlockIDs : struct.begin
  [0] = ArtifactAddRadiation1
  [1] = ArtifactAddRadiation2
  [2] = ArtifactAddRadiation3
  [3] = ArtifactAddRadiation4
 struct.end
struct.end
'''
    gd.effects = parse(effects)
    return gd


class ArmorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gd = fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def apply(self, custom=None, base=None, **kwargs):
        settings = Settings(armor_custom=custom or {}, **kwargs)
        base, editions = base if base is not None else {}, {}
        ext.apply(self.gd, settings, base, editions)
        return base, editions

    def test_neutral_and_explicit_original_do_not_emit(self):
        self.assertEqual(self.apply(), ({}, {}))
        self.assertEqual(self.apply({"Suit": {"weight": -1, "cost": 1000, "psy": 0}}), ({}, {}))

    def test_explicit_original_cancels_global_patch_only_on_chosen_field(self):
        base = {"Suit": {"Weight": "5", "Cost": "1200", "Protection": {"Strike": "6"}}}
        patched, _ = self.apply({"Suit": {"weight": 10, "strike": 2}}, base)
        self.assertEqual(patched, {"Suit": {"Cost": "1200"}})

    def test_absolute_zero_and_new_protection(self):
        patched, _ = self.apply({"Suit": {"weight": 0, "psy": 25, "fall": 50}})
        self.assertEqual(patched, {"Suit": {"Weight": "0", "Protection": {"PSY": "25", "Fall": "50"}}})
        self.assertNotIn("ProtectionNPC", emit_patch(patched))

    def test_routing_and_unavailable_items(self):
        patched, dlc = self.apply({"EditionSuit": {"weight": 4}, "Hidden": {"weight": 4}, "Unknown": {"weight": 4}})
        self.assertEqual(patched, {})
        self.assertEqual(dlc, {"Deluxe": {"EditionSuit": {"Weight": "4"}}})

    def test_body_only_controls_do_not_touch_helmets(self):
        patched, _ = self.apply({"Helmet": {"artifact_slots": 5, "allow_helmet": 1, "free_sprint": 1, "lead_slots": 3}})
        self.assertEqual(patched, {})

    def test_boolean_overrides_and_global_opt_out(self):
        patched, _ = self.apply({"Suit": {"limp_protection": 0, "free_sprint": 0}},
                                armor_free_sprint=True, armor_limp_protection=True)
        self.assertNotIn("Suit", patched)
        self.assertEqual(patched["Other"]["bPreventFromLimping"], "true")
        self.assertNotIn("Helmet", patched)

    def test_sprint_preserves_unrelated_effects(self):
        patched, _ = self.apply({"Suit": {"free_sprint": 1}})
        self.assertEqual(patched, {"Suit": {"EffectPrototypeSIDs": {"[1]": "empty"}}})
        original = ext._effect_list(ext.chain_for(self.gd, "Suit", None))
        original.update(patched["Suit"]["EffectPrototypeSIDs"])
        self.assertEqual(original, {"[0]": "Carry", "[1]": "empty", "[2]": "Gas"})

    def test_sprint_does_not_disable_other_sprint_blockers(self):
        self.gd.effects.children["ArmorConditionalEffect"].values["ConditionSID"] = "Concussion"
        self.assertEqual(self.apply({"Suit": {"free_sprint": 1}}), ({}, {}))

    def test_helmet_switch_inverts_block_flag(self):
        patched, _ = self.apply({"Suit": {"allow_helmet": 0}})
        self.assertEqual(patched["Suit"]["bBlockHead"], "true")
        self.assertEqual(self.apply({"Suit": {"allow_helmet": 1}}), ({}, {}))

    def test_lead_slots_append_a_namespaced_native_composite(self):
        settings = Settings(mod_name="One", armor_custom={"Suit": {"lead_slots": 2}})
        composites = ext.lead_composites(self.gd, settings)
        base, _ = self.apply(settings.armor_custom, mod_name="One")
        name = base["Suit"]["EffectPrototypeSIDs"]["[*]"]
        self.assertEqual(composites[name]["ApplyExtraEffectPrototypeSIDs"],
                         {"[0]": "ArtifactSlotBlockEffect3_Slot1", "[1]": "ArtifactSlotBlockEffect3_Slot2"})
        self.assertNotIn("bpatch", emit_patch(composites))
        self.assertIn("{bpatch}", emit_patch(base))
        other = ext.lead_composites(self.gd, Settings(mod_name="Two", armor_custom=settings.armor_custom))
        self.assertNotEqual(set(composites), set(other))

    def test_lead_count_must_fit_base_slots(self):
        with self.assertRaisesRegex(ValueError, "require at least"):
            self.apply({"Suit": {"lead_slots": 5}})
        base, _ = self.apply({"Suit": {"artifact_slots": 5, "lead_slots": 5}})
        self.assertEqual(base["Suit"]["ArtifactSlots"], "5")

    def test_changed_native_effect_fails_instead_of_guessing(self):
        self.gd.effects.children["ArtifactSlotBlockEffect3_Slot1"].children["ArtifactEquipmentSlots"].values["[0]"] = "Wrong"
        with self.assertRaisesRegex(ValueError, "has changed"):
            self.apply({"Suit": {"lead_slots": 1}})

    def test_imports_preserve_off_zero_and_old_profiles(self):
        state = {"armor_custom": {"Suit": {"weight": 0, "allow_helmet": 0, "psy": 20}}}
        target = Path(self.tmp.name) / "profile.json"
        editor_state.save_profile(target, state, "Armor")
        self.assertEqual(editor_state.read_profile(target).state["armor_custom"], state["armor_custom"])
        self.assertEqual(editor_state.differences({}, {"armor_custom": {"Suit": {"weight": -1}}}), [])
        self.assertEqual(len(editor_state.differences({}, state)), 3)
        self.assertEqual(editor_state.state_only({})["armor_custom"], {})

    def test_invalid_values_are_rejected(self):
        for key, value in (("weight", float("nan")), ("cost", float("inf")), ("artifact_slots", 6),
                           ("artifact_slots", 1.5), ("free_sprint", 2), ("weight", -0.5), ("grid_width", 0)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                ext.clean({key: value})

    def test_scan_reports_item_and_effect_list_targets(self):
        pairs = ext.footprint(self.gd)
        self.assertIn(("Suit", "Fall"), pairs)
        self.assertIn(("EditionSuit", "Cost"), pairs)
        base, _ = self.apply({"Suit": {"lead_slots": 2}})
        output = modscan.pairs_from_patches({"Own.cfg": emit_patch(base)})
        self.assertIn(("Suit", modscan.EFFECT_LIST_LEAF), output & pairs)


class InstalledDataTests(unittest.TestCase):
    def test_real_generator_precedence_dlc_and_native_effects(self):
        gd = GameData(str(ROOT / "vanilla/Stalker2/Content/GameLite/GameData"))
        sid = "Exoskeleton_Neutral_Armor"
        settings = Settings(item_weight_factor=0.5, armor_strike_factor=3,
            armor_custom={sid: {"weight": 4, "strike": 2, "artifact_slots": 5,
                               "lead_slots": 5, "free_sprint": 1, "limp_protection": 0}})
        patches = build_patches(gd, settings)
        item = parse(patches["ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"]).children[sid]
        self.assertEqual(item.get("Weight"), "4")
        self.assertEqual(item.get("Protection.Strike"), "2")
        self.assertEqual(item.get("ArtifactSlots"), "5")
        self.assertEqual(item.get("bPreventFromLimping"), "false")
        self.assertEqual(item.children["EffectPrototypeSIDs"].get("[1]"), "empty")
        effect_sid = item.children["EffectPrototypeSIDs"].get("[*]")
        effects = parse(patches["EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"])
        self.assertIn(effect_sid, effects.children)
        dlc_sid = next(iter(gd.dlc_player_armors()))
        patch = build_patches(gd, Settings(armor_custom={dlc_sid: {"weight": 0}}))
        self.assertTrue(any(path.startswith("//GameLite/DLCGameData/") and "Weight = 0" in text for path, text in patch.items()))
        self.assertTrue(any("Base artifact slots = 5" in line for line in summarize(settings)))
        self.assertFalse(build_patches(gd, Settings()))

    def test_every_new_control_changes_a_real_armor(self):
        gd = GameData(str(ROOT / "vanilla/Stalker2/Content/GameLite/GameData"))
        values = dict(weight=4, cost=100, durability=2500, grid_width=1, grid_height=1,
                      artifact_slots=5, strike=1, burn=1, shock=1, chemical=1,
                      radiation=1, psy=1, fall=50, noise=0.5, limp_protection=0,
                      allow_helmet=1, free_sprint=1, lead_slots=2)
        self.assertEqual(set(values), set(ext.CONTROLS))
        for key, value in values.items():
            with self.subTest(key=key):
                settings = Settings(armor_custom={"Exoskeleton_Neutral_Armor": {key: value}})
                patches = build_patches(gd, settings)
                self.assertTrue(patches)
                self.assertTrue(any(ext.CONTROLS[key].label in line for line in summarize(settings)))

    def test_row_load_keeps_zero_and_reset_clears_both_modes(self):
        from s2tweaker.gui import IrArmorRow
        row = object.__new__(IrArmorRow)
        row.sid, row.group = "Suit", "Body"
        row.app = SimpleNamespace(armor_overrides={"Suit": {"strike": 2}},
                                  armor_custom={"Suit": {"weight": 0, "allow_helmet": 0}},
                                  _ir_loading=False, _ir_after_change=lambda group: None)
        row.refresh = lambda: None
        class Value:
            def set(self, value):
                self.value = value
                self.loading = row.app._ir_loading
            def get(self):
                return self.value
        row.sliders = {"strike": Value()}
        row.custom_sliders = {key: Value() for key in ("weight", "allow_helmet", "psy")}
        row.load_values()
        self.assertEqual(row.custom_sliders["weight"].get(), 0)
        self.assertEqual(row.custom_sliders["psy"].get(), -1)
        self.assertTrue(all(value.loading for value in row.custom_sliders.values()))
        self.assertFalse(row.app._ir_loading)
        row.reset()
        self.assertEqual(row.app.armor_custom, {})
        self.assertEqual(row.app.armor_overrides, {})
        self.assertTrue(all(value.get() == -1 for value in row.custom_sliders.values()))

    def test_gui_collect_and_state_contain_custom_group(self):
        source = ast.parse((ROOT / "s2tweaker/gui.py").read_text(encoding="utf-8"))
        collect = next(node for node in ast.walk(source) if isinstance(node, ast.FunctionDef) and node.name == "_collect")
        args = {node.arg for node in ast.walk(collect) if isinstance(node, ast.keyword)}
        self.assertTrue({"armor_custom", "armor_free_sprint", "armor_limp_protection"}.issubset(args))


if __name__ == "__main__":
    unittest.main()
