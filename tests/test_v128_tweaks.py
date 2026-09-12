"""Check core control families against installed game data.

Cover complete indexed entries, related field composition, neutral output
and mirrored CoreVariablesCustom values; see CORE_SWEEP_RESEARCH.md."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker import cfgparse                       # noqa: E402
from s2tweaker.cfgparse import parse_number          # noqa: E402
from s2tweaker.gamedata import GameData, NEEDED_FILES, CACHE_SCHEMA   # noqa: E402
from s2tweaker.modscan import _GD_TREES              # noqa: E402
from s2tweaker.tweaks import (Settings, build_patches, summarize,     # noqa: E402
                              DAMAGE_SCREEN_PROCESSORS, COREVARS_CUSTOM_KEYS)

gd = GameData(VANILLA)
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
CUSTOM = "CoreVariablesCustom.cfg_patch_S2Tweaker.cfg"
QS = "QuickSaveVariables.cfg_patch_S2Tweaker.cfg"
PFX = "PostEffectProcessorPrototypes/PostEffectProcessorPrototypes_patch_S2Tweaker.cfg"


def parsed(patches, name):
    return cfgparse.parse(patches[name]) if name in patches else None


def S(**kw):
    return Settings(mod_name="S2Tweaker", **kw)


def core_values(**kw) -> dict:
    return parsed(build_patches(gd, S(**kw)), CORE).children["DefaultConfig"].values


# =========================================================================
# P1 - Player: body, vision, saving.
# =========================================================================

# --- P1.0) Files, schema, mod scan, live values match defaults ---
assert "QuickSaveVariables.cfg" in NEEDED_FILES and "CoreVariablesCustom.cfg" in NEEDED_FILES
assert CACHE_SCHEMA >= 22, "Two new files without schema bump"
assert "corevarscustom" in _GD_TREES and "quicksave" in _GD_TREES, _GD_TREES
qs_live = parse_number(gd.quicksave.children["DefaultConfig"].values["QuickSaveOverwriteTime"])
assert abs(qs_live - Settings().quicksave_overwrite_min * 60.0) < 1e-9, qs_live
custom_live = gd.corevarscustom.children["CustomConfigOverride"].values
core_live = gd.corevars.children["DefaultConfig"].values
for key in COREVARS_CUSTOM_KEYS:
    assert parse_number(custom_live[key]) == parse_number(core_live[key]), key
limp_live = gd.corevars.children["DefaultConfig"].children["LimpEffectSIDToThresholdMap"].children
assert [e.values["EffectSID"] for e in limp_live.values()] == ["WeakLimp", "MediumLimp"]
print(f"P1.0 Files: schema {CACHE_SCHEMA}, QuickSave live {qs_live:g} s = Default, "
      f"CustomConfigOverride repeated {len(COREVARS_CUSTOM_KEYS)} identical keys  OK")

# --- P1.1) Neutral produces nothing ---
neutral = build_patches(gd, S())
assert not neutral, sorted(neutral)
print("P1.1 Neutral: no patch file  OK")

# --- P1.2) Limping after a hard landing: complete array ---
core = parsed(build_patches(gd, S(limp_threshold_factor=2.0)), CORE).children["DefaultConfig"]
arr = core.children["LimpEffectSIDToThresholdMap"].children
assert set(arr) == {"[0]", "[1]"}, set(arr)
assert arr["[0]"].values == {"EffectSID": "WeakLimp", "Threshold": "50.0"}, arr["[0]"].values
assert arr["[1]"].values == {"EffectSID": "MediumLimp", "Threshold": "130.0"}, arr["[1]"].values
assert not core.values, core.values                                        # Nothing else.
arr = parsed(build_patches(gd, S(no_landing_limp=True)), CORE).children["DefaultConfig"] \
    .children["LimpEffectSIDToThresholdMap"].children
assert arr["[0]"].values == {"EffectSID": "WeakLimp", "Threshold": "25000.0"}, arr["[0]"].values
assert arr["[1]"].values["Threshold"] == "65000.0"
arr = parsed(build_patches(gd, S(no_landing_limp=True, limp_threshold_factor=3.0)), CORE) \
    .children["DefaultConfig"].children["LimpEffectSIDToThresholdMap"].children
assert arr["[1]"].values["Threshold"] == "65000.0"                          # Toggle takes precedence over slider.
assert CORE not in build_patches(gd, S(limp_threshold_factor=1.0))
text = build_patches(gd, S(limp_threshold_factor=2.0))[CORE]
assert "LimpEffectSIDToThresholdMap : struct.begin {bpatch}" in text and "[0] : struct.begin {bpatch}" in text
print("P1.2 Limping: x2 -> 50/130, toggle -> 25000/65000, both entries complete  OK")

# Bleeding from penetrating and nonpenetrating hits.
core = core_values(bleeding_hit_factor=0.0, bleeding_nonpen_factor=2.0)
assert core["VitalBaseBleedingValue"] == "0.0", core
assert core["BleedingChanceNonPenetrationMod"] == "2.0" == core["BleedingPointsNonPenetrationMod"], core
assert len(core) == 3, core
assert core_values(bleeding_hit_factor=2.5) == {"VitalBaseBleedingValue": "25.0"}
print("P1.3 Bleeding: per hit x0 / x2.5, nonpenetrating x2 (both keys)  OK")

# --- P1.4) Damage screen effects: 15 processors, individually ---
assert len(DAMAGE_SCREEN_PROCESSORS) == 15, DAMAGE_SCREEN_PROCESSORS
for sid in DAMAGE_SCREEN_PROCESSORS:
    node = gd.posteffects.children[sid]                                     # Present in live data.
    assert parse_number(node.values["Intensity"]) == 1.0, (sid, node.values)   # Self-defined.
pfx = parsed(build_patches(gd, S(damage_screen_factor=0.5)), PFX)
assert set(pfx.children) == set(DAMAGE_SCREEN_PROCESSORS), set(pfx.children) ^ set(DAMAGE_SCREEN_PROCESSORS)
assert all(n.values == {"Intensity": "0.5"} for n in pfx.children.values())
for sid in ("GameplayGasEffectProcessor", "NVGElectroIntensityEffectProcessor",
            "LowHealthEffectProcessor", "BleedingEffectProcessor", "CrouchEffectProcessor"):
    assert sid not in pfx.children, sid
assert parsed(build_patches(gd, S(damage_screen_factor=0.0)), PFX) \
    .children["BottomLeftDamageEffectProcessor"].values["Intensity"] == "0.0"
assert PFX not in build_patches(gd, S(damage_screen_factor=1.5))            # cap 1.0 = Vanilla
both = parsed(build_patches(gd, S(damage_screen_factor=0.3, crouch_vignette_factor=0.0)), PFX)
assert both.children["CrouchEffectProcessor"].values["Intensity"] == "0.0" and len(both.children) == 16
print("P1.4 Screen effects: 15 processors x0.5, 0%, caps, alongside crouch vignette  OK")

# --- P1.5) Flashlight during dialog ---
assert core_values(flashlight_dialog_bright=True) == {"FlashlightDialogIntensityPercent": "1.0"}
print("P1.5 Taschenlampe: 0.525 -> 1.0  OK")

# --- P1.6) Quicksave window: new text file ---
p = build_patches(gd, S(quicksave_overwrite_min=0))
text = p[QS]
assert "DefaultConfig : struct.begin {bpatch}" in text and "QuickSaveOverwriteTime = 0" in text, text
assert text.count("struct.end") == 1, text
assert parsed(build_patches(gd, S(quicksave_overwrite_min=30)), QS) \
    .children["DefaultConfig"].values == {"QuickSaveOverwriteTime": "1800"}
assert QS not in build_patches(gd, S(quicksave_overwrite_min=5))            # = Vanilla 300 s
assert QS not in build_patches(gd, S(quicksave_overwrite_min=-1))
print("P1.6 Schnellspeicher: 0 min -> 0, 30 min -> 1800, 5 min = Vanilla  OK")

# --- P1.7) Integrate with existing sliders ---
core = core_values(no_overweight_penalty=True)
assert core == {"InventorySPOverweightDrainCoef": "0.0", "InventorySPDrainCoef": "0.0"}, core
p = build_patches(gd, S(stamina_jump=0.5))
assert parsed(p, CORE).children["DefaultConfig"].values == {"StaminaFallingDamageCoef": "0.25"}
jump_v = parse_number(gd.resolve(gd.obj, "Player", "StaminaPerAction.Jump"))
assert parse_number(parsed(p, OBJ).children["Player"].children["StaminaPerAction"].values["Jump"]) == jump_v * 0.5
p = build_patches(gd, S(climb_speed_factor=2.0))
assert parsed(p, CORE).children["DefaultConfig"].values == {
    k: "2.0f" for k in ("ClimbUpSpeed", "ClimbDownSpeed", "ClimbEnterUpSpeed",
                        "ClimbEnterDownSpeed", "ClimbExitUpSpeed")}
assert parsed(p, OBJ).children["Player"].children["MovementParams"].values["ClimbSpeedCoef"] == "1.2"
core = core_values(interaction_range_factor=2.0)
assert core["MaxInteractionDistance"] == "400.0" and core["ItemContainerInteractRange"] == "400.0"
assert core["WideTraceInteractionDistance"] == "1000.0" and core["AutoInteractionDistance"] == "140.0", core
assert core["MutantLootContainerInteractRange"] == "240.0" and core["DragDeadBodyInteractRange"] == "260.0", core
assert core["MutantLootInteractHeightMax"] == "180.0f" and "MutantLootInteractHeightMin" not in core, core
assert len(core) == 7, core
core = core_values(corpse_drag_factor=2.0)
assert core == {"DraggingCorpseSpeedCoef": "1.0", "DeadBodyPickUpTime": "1.0"}, core   # cap / inverse
core = core_values(corpse_drag_factor=0.5)
assert core == {"DraggingCorpseSpeedCoef": "0.3", "DeadBodyPickUpTime": "4.0"}, core
core = core_values(map_reveal_factor=2.0)
assert core == {"MarkerShowingDistance": "60000.0", "MarkerRevealingDistance": "6000.0",
                "MarkerExploringDistance": "4000.0"}, core
print("P1.7 Collapsed: encumbrance drain, landing stamina, 5 ladder rates, 5 ranges, "
      "Corpse interaction duration (inverse), 3 marker distances  OK")

# Mirror core overrides only when their corresponding fields change.
for kw, keys in ((dict(max_carry_weight=200), {"InventoryPenaltyLessWeight"}),
                 (dict(penalty_start_weight=60), {"InventoryPenaltyLessWeight"}),
                 (dict(no_overweight_penalty=True), {"InventorySPOverweightDrainCoef", "InventorySPDrainCoef"}),
                 (dict(stamina_jump=2.0), {"StaminaFallingDamageCoef"}),
                 (dict(max_carry_weight=120, no_overweight_penalty=True, stamina_jump=0.0),
                  set(COREVARS_CUSTOM_KEYS))):
    p = build_patches(gd, S(**kw))
    core = parsed(p, CORE).children["DefaultConfig"].values
    cus = parsed(p, CUSTOM).children["CustomConfigOverride"].values
    assert set(cus) == keys, (kw, cus)
    assert all(cus[k] == core[k] for k in keys), (kw, cus, core)           # Match the patched DefaultConfig value.
    assert "CustomConfigOverride : struct.begin {bpatch}" in p[CUSTOM] and p[CUSTOM].count("struct.end") == 1
    assert "MediumEffectStartUI" not in cus and "bGSCEnsure" not in cus
for kw in (dict(repair_cost_factor=0.5), dict(limp_threshold_factor=2.0), dict(flashlight_dialog_bright=True),
           dict(interaction_range_factor=2.0), dict(day_length_factor=2.0)):
    p = build_patches(gd, S(**kw))
    assert CORE in p and CUSTOM not in p, kw
print("P1.8 Confirmation: appears for exactly four keys, identical values  OK")

# --- P1.9) Summary ---
joined = "\n".join(summarize(S(limp_threshold_factor=2.0, bleeding_hit_factor=0.5, bleeding_nonpen_factor=0.0,
                               damage_screen_factor=0.0, flashlight_dialog_bright=True,
                               quicksave_overwrite_min=0)))
for needle in ("Limp threshold", "Bleeding per hit", "non-penetrating", "Damage screen",
               "Flashlight stays bright", "Quicksave overwrite"):
    assert needle in joined, (needle, joined)
switch = "\n".join(summarize(S(no_landing_limp=True, limp_threshold_factor=2.0)))
assert "Never limp" in switch and "Limp threshold" not in switch, switch
assert not any(k in "\n".join(summarize(S())) for k in ("Limp", "Bleeding per", "Damage screen",
                                                        "Flashlight stays", "Quicksave"))
print("P1.9 Summary: 6 lines present, toggle replaces slider, neutral empty  OK")

# Armor and hit calculations.

# --- P2.0) Live values match defaults, neutral output empty ---
arr_live = gd.corevars.children["DefaultConfig"].children["StrikeGrenadeResistCoefs"].children
assert [e.values["ProtectionStrike"] for e in arr_live.values()] == ["0.f", "1.f", "2.f", "3.f", "4.f"]
for key in ("ArmorDurabilityParamsCoef", "HelmetDurabilityParamsCoef"):
    assert abs(gd.corevar(key) - Settings().armor_wear_coef) < 1e-9, (key, gd.corevar(key))
assert abs(gd.corevar("StrikeAnomalyArmorDifferenceCoef") - 1.0) < 1e-9
assert not build_patches(gd, S(grenade_resist_factor=1.0, armor_wear_coef=0.7, anomaly_armor_difference_factor=1.0))
print("P2.0 Live: 5 Strike levels, wear coefficients match default 0.7, neutral empty  OK")

# --- P2.1) Grenade protection: complete array, f suffix, cap 1.0 ---
def resist(factor):
    core = parsed(build_patches(gd, S(grenade_resist_factor=factor)), CORE).children["DefaultConfig"]
    assert not core.values, core.values                                      # Nothing else.
    return core.children["StrikeGrenadeResistCoefs"].children

arr = resist(2.0)
assert set(arr) == {"[0]", "[1]", "[2]", "[3]", "[4]"}, set(arr)
assert arr["[0]"].values == {"ProtectionStrike": "0.f", "GrenadeDamageResist": "0.0f"}, arr["[0]"].values
assert arr["[1]"].values == {"ProtectionStrike": "1.f", "GrenadeDamageResist": "0.2f"}, arr["[1]"].values
assert arr["[2]"].values["GrenadeDamageResist"] == "0.4f" and arr["[3]"].values["GrenadeDamageResist"] == "0.8f"
assert arr["[4]"].values == {"ProtectionStrike": "4.f", "GrenadeDamageResist": "1.0f"}, arr["[4]"].values  # cap
arr = resist(0.0)
assert [e.values["GrenadeDamageResist"] for e in arr.values()] == ["0.0f"] * 5
arr = resist(3.0)
assert [e.values["GrenadeDamageResist"] for e in arr.values()] == ["0.0f", "0.3f", "0.6f", "1.0f", "1.0f"]
text = build_patches(gd, S(grenade_resist_factor=0.5))[CORE]
assert "StrikeGrenadeResistCoefs : struct.begin {bpatch}" in text and text.count("[") == 5, text
assert CORE not in build_patches(gd, S(grenade_resist_factor=1.0))
print("P2.1 Grenade protection: x2 -> 0/0.2/0.4/0.8/1.0f (capped), x0 -> all zero, x3 capped, complete entries  OK")

# --- P2.2) Absolute wear control: both coefficients, f suffix ---
assert core_values(armor_wear_coef=0.3) == {"ArmorDurabilityParamsCoef": "0.3f", "HelmetDurabilityParamsCoef": "0.3f"}
assert core_values(armor_wear_coef=1.0) == {"ArmorDurabilityParamsCoef": "1.0f", "HelmetDurabilityParamsCoef": "1.0f"}
assert core_values(armor_wear_coef=0.0)["HelmetDurabilityParamsCoef"] == "0.0f"
assert core_values(armor_wear_coef=1.4)["ArmorDurabilityParamsCoef"] == "1.0f"        # Clamped
assert CORE not in build_patches(gd, S(armor_wear_coef=0.7))                           # = Vanilla live
print("P2.2 Wear: 0.3 / 1.0 / 0.0 for armor + helmet, 0.7 = vanilla, >1 clamped  OK")

# --- P2.3) Armor against anomaly strikes ---
assert core_values(anomaly_armor_difference_factor=2.0) == {"StrikeAnomalyArmorDifferenceCoef": "2.0"}
assert core_values(anomaly_armor_difference_factor=0.0) == {"StrikeAnomalyArmorDifferenceCoef": "0.0"}
assert core_values(anomaly_armor_difference_factor=0.5) == {"StrikeAnomalyArmorDifferenceCoef": "0.5"}
print("P2.3 Anomaly strike: x2 / x0 / x0.5, sibling keys unchanged  OK")

# --- P2.4) Summary ---
joined = "\n".join(summarize(S(grenade_resist_factor=0.0, armor_wear_coef=0.3, anomaly_armor_difference_factor=2.0)))
for needle in ("grenade resistance", "wear coefficient 0.3", "anomaly strike"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("grenade", "wear coefficient", "anomaly strike"))
print("P2.4 Summary: 3 lines present, neutral empty  OK")

# =========================================================================
# P3 - NPC combat behavior.
# =========================================================================
EE = "EnemyEvaluatorPrototypes/EnemyEvaluatorPrototypes_patch_S2Tweaker.cfg"
CE = "CoverEvaluatorPrototypes/CoverEvaluatorPrototypes_patch_S2Tweaker.cfg"
BOSSES = ("BossCoverEvaluator", "StrelokCoverEvaluator", "ScarCoverEvaluator", "KorshunovCoverEvaluator")

# --- P3.0) Files, schema stays 22, mod scan, live values match defaults ---
assert "EnemyEvaluatorPrototypes.cfg.bin" in NEEDED_FILES and "CoverEvaluatorPrototypes.cfg.bin" in NEEDED_FILES
assert CACHE_SCHEMA >= 22, "Schema 22 covered all of 1.28.0 (1.36.0: 23, DialogPrototypes)"
assert "enemyevaluators" in _GD_TREES and "coverevaluators" in _GD_TREES
for key, field in (("ChanceToGetHealOverTimeWhenWounded", "wounded_heal_chance"),
                   ("CooldownOnFallingWounded", "wounded_cooldown_s"),
                   ("HpThresholdToHealWound", "wounded_heal_threshold")):
    assert abs(gd.corevar(key) - getattr(Settings(), field)) < 1e-9, (key, gd.corevar(key))
assert abs(gd.corevar("WoundedStateHealthRegen") - 5.0) < 1e-9
ee_live = gd.enemyevaluators.children
assert list(ee_live) == ["[0]"] and ee_live["[0]"].values["NotPlayerCoeff"] == "0.15", list(ee_live)
ce_live = gd.coverevaluators.children
assert "DefaultCoverEvaluator" in ce_live and all(b in ce_live for b in BOSSES), list(ce_live)
assert ce_live["DefaultCoverEvaluator"].children["DefaultCoverSettings"].values["MinDistanceToEnemy"] == "800.f"
assert not build_patches(gd, S(wounded_heal_chance=70, wounded_cooldown_s=300, wounded_regen_factor=1.0,
                               wounded_heal_threshold=35, npc_player_focus_factor=1.0,
                               npc_retarget_cooldown_factor=1.0, npc_damage_memory_factor=1.0,
                               cover_distance_factor=1.0, cover_path_factor=1.0))
print("P3.0 Files: schema 22, live [0] evaluator + DefaultCoverEvaluator, absolute values match defaults, neutral empty  OK")

# Wounded NPC values, numeric formatting and exclusions.
core = core_values(wounded_heal_chance=0, wounded_cooldown_s=60, wounded_regen_factor=2.0, wounded_heal_threshold=50)
assert core == {"ChanceToGetHealOverTimeWhenWounded": "0", "CooldownOnFallingWounded": "60",
                "WoundedStateHealthRegen": "10.0f", "HpThresholdToHealWound": "50"}, core
assert core_values(wounded_heal_chance=150) == {"ChanceToGetHealOverTimeWhenWounded": "100"}   # Clamped
assert core_values(wounded_regen_factor=0.0) == {"WoundedStateHealthRegen": "0.0f"}
text = build_patches(gd, S(wounded_heal_chance=0, wounded_cooldown_s=30, wounded_heal_threshold=95))[CORE]
assert "UnkillableNPCWoundedStateResurrectionTime" not in text and "WoundHitAreasThresholds" not in text
assert CORE not in build_patches(gd, S(wounded_cooldown_s=300))
print("P3.1 Wounded: chance 0 / 100 (clamped), cooldown 60, regeneration x2 = 10.0f, threshold 50, excluded values unchanged  OK")

# Patch the indexed target evaluator.
p = build_patches(gd, S(npc_player_focus_factor=2.0, npc_retarget_cooldown_factor=0.5, npc_damage_memory_factor=2.0))
text = p[EE]
assert text.startswith("[0] : struct.begin {bpatch}") and text.count("struct.begin") == 1, text
assert parsed(p, EE).children["[0]"].values == {"NotPlayerCoeff": "0.3", "ChangeEnemyCooldown": "1.5",
                                                "DamageAccumulationDurationSeconds": "14.0"}, text
assert parsed(build_patches(gd, S(npc_player_focus_factor=0.0)), EE).children["[0]"].values == {"NotPlayerCoeff": "0.0"}
assert EE not in build_patches(gd, S(npc_player_focus_factor=1.0))
assert "DistanceCoeff" not in text and "RangeSearchPathToEnemies" not in text          # Only these three keys.
print("P3.2 Target selection: [0] {bpatch}, NotPlayerCoeff x2 / x0, target switching x0.5, memory x2  OK")

# Default cover evaluation only; preserve bosses and ordered bounds.
p = build_patches(gd, S(cover_distance_factor=0.5, cover_path_factor=2.0))
ce = parsed(p, CE)
assert list(ce.children) == ["DefaultCoverEvaluator"], list(ce.children)
for other in BOSSES + ("AttackCoverEvaluator", "ZombieCoverEvaluator", "DLC01_ZulusMateCoverEvaluator",
                       "LeaveCrossfireCoverEvaluator", "ExplosivesCoverSettings"):
    assert other not in p[CE], other
d = ce.children["DefaultCoverEvaluator"]
assert d.values == {"MaxPathLength": "4000"}, d.values                                   # integer
assert d.children["DefaultCoverSettings"].values == {"MinDistanceToEnemy": "400.0f", "MaxDistanceToEnemy": "3500.0f"}
assert "DefaultCoverEvaluator : struct.begin {bpatch}" in p[CE] and "DefaultCoverSettings : struct.begin {bpatch}" in p[CE]
d = parsed(build_patches(gd, S(cover_distance_factor=2.0)), CE).children["DefaultCoverEvaluator"]
v = d.children["DefaultCoverSettings"].values
assert parse_number(v["MinDistanceToEnemy"]) <= parse_number(v["MaxDistanceToEnemy"]) and v["MaxDistanceToEnemy"] == "14000.0f"
assert "MaxPathLength" not in d.values
assert CE not in build_patches(gd, S(cover_distance_factor=1.0, cover_path_factor=1.0))
print("P3.3 Cover: DefaultCoverEvaluator only, bosses/special children excluded, 400/3500f + path 4000, Min <= Max  OK")

# --- P3.4) Summary ---
joined = "\n".join(summarize(S(wounded_heal_chance=0, wounded_cooldown_s=60, wounded_regen_factor=2.0,
                               wounded_heal_threshold=50, npc_player_focus_factor=2.0,
                               npc_retarget_cooldown_factor=0.5, npc_damage_memory_factor=2.0,
                               cover_distance_factor=0.5, cover_path_factor=2.0)))
for needle in ("Wounded NPCs recover 0 %", "cooldown 60 s", "Wounded NPC health regen", "heal threshold 50",
               "focus on the player", "target-switch", "damage memory", "cover distance", "cover search path"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("Wounded", "focus on the player", "cover"))
print("P3.4 Summary: 9 lines present, neutral empty  OK")

# =========================================================================
# P4 - Mutants
# =========================================================================
from s2tweaker.tweaks import FLAIR_SENSOR_SKIP, FLAIR_SENSOR_KEYS   # noqa: E402
FL = "AIPrototypes/FlairSensorPrototypes/FlairSensorPrototypes_patch_S2Tweaker.cfg"
TARGET = ["BlindDogFlairSensor", "ChimeraFlairSensor", "FleshFlairSensor", "PoltergeistFlairSensor"]

# --- P4.0) File, schema 22, mod scan, live sensors: 6 active, 2 excluded ---
assert "AIPrototypes/FlairSensorPrototypes.cfg.bin" in NEEDED_FILES and CACHE_SCHEMA >= 22
assert "flairsensors" in _GD_TREES
active = sorted(sid for sid, n in gd.flairsensors.children.items()
                if n.values.get("IsActive", "").strip() == "true")
assert active == sorted(TARGET + ["PsyNPCFlairSensor", "PoltergeistFlairSensorYanivToxicRozliv"]), active
assert len(active) == 6 and len(FLAIR_SENSOR_SKIP & set(active)) == 2
assert all("FrontSensingRadius" in gd.flairsensors.children[s].values for s in ("BlindDogFlairSensor", "ChimeraFlairSensor", "FleshFlairSensor"))
assert "FrontSensingRadius" not in gd.flairsensors.children["PoltergeistFlairSensor"].values
assert gd.corevars.children["DefaultConfig"].values["UseMutantLootWithoutWidget"].strip() == "true"
assert not build_patches(gd, S(mutant_smell_factor=1.0, burer_fire_interval_factor=1.0))
print("P4.0 Scent: 6 live active sensors, 2 excluded, Front* only on 3, widget flag true, neutral empty  OK")

# Scale only existing scent-sensor fields with their suffixes.
p = build_patches(gd, S(mutant_smell_factor=0.5))
fl = parsed(p, FL)
assert sorted(fl.children) == TARGET, sorted(fl.children)
assert fl.children["BlindDogFlairSensor"].values == {"SensingRadius": "2000.0f", "DetectionSpeed": "55.0f",
                                                    "FrontSensingRadius": "2000.0f", "FrontDetectionSpeed": "200.0f"}
assert fl.children["PoltergeistFlairSensor"].values == {"SensingRadius": "500.0f", "DetectionSpeed": "55.0f"}
assert fl.children["ChimeraFlairSensor"].values["FrontSensingRadius"] == "1750.0f"
assert fl.children["FleshFlairSensor"].values["SensingRadius"] == "1000.0f"
for other in sorted(FLAIR_SENSOR_SKIP) + ["DugaSniperFlairSensor", "GuardNPCFlairSensor", "DefaultFlairSensor"]:
    assert other not in p[FL], other
assert "FrontSensingAngle" not in p[FL] and "IsActive" not in p[FL] and "MaxFlairPoints" not in p[FL]
assert FL not in build_patches(gd, S(mutant_smell_factor=1.0))
print("P4.1 Scent x0.5: BlindDog 2000/55/2000/200f, Poltergeist without Front*, excluded sensors absent  OK")

# Disable only the supported active scent sensors.
fl = parsed(build_patches(gd, S(mutants_no_smell=True)), FL)
assert sorted(fl.children) == TARGET and all(n.values == {"IsActive": "false"} for n in fl.children.values())
both = parsed(build_patches(gd, S(mutants_no_smell=True, mutant_smell_factor=2.0)), FL)
assert both.children["FleshFlairSensor"].values["IsActive"] == "false" and both.children["FleshFlairSensor"].values["SensingRadius"] == "4000.0f"
print("P4.2 Toggle: exactly four allowed sensors set to IsActive = false  OK")

# --- P4.3) Burer weapon fire: ten named substructs ---
AMMO = ["A012", "AVOG", "AGA", "APG7V", "AHEDP", "A762Sniper", "A762NATO", "A918", "A919", "A045"]
p = build_patches(gd, S(burer_fire_interval_factor=2.0))
iv = parsed(p, CORE).children["DefaultConfig"].children["PossessedWeaponFireIntervals"].children
assert sorted(iv) == sorted(AMMO) and len(iv) == 10, sorted(iv)
assert iv["A012"].values == {"FireInterval": "2.0"} and iv["AVOG"].values == {"FireInterval": "8.0"}
assert iv["AGA"].values == {"FireInterval": "4.0"} and iv["A918"].values == {"FireInterval": "1.0"}
assert "PossessedWeaponFireIntervals : struct.begin {bpatch}" in p[CORE] and "A045 : struct.begin {bpatch}" in p[CORE]
assert parsed(p, CORE).children["DefaultConfig"].values == {}
iv = parsed(build_patches(gd, S(burer_fire_interval_factor=0.5)), CORE).children["DefaultConfig"] \
    .children["PossessedWeaponFireIntervals"].children
assert iv["A919"].values == {"FireInterval": "0.25"} and iv["APG7V"].values == {"FireInterval": "2.0"}
print("P4.3 Burer: 10 ammo types x2 (1 -> 2.0, 4 -> 8.0), x0.5 (0.5 -> 0.25)  OK")

# Mutant looting with an inventory window.
assert core_values(mutant_loot_widget=True) == {"UseMutantLootWithoutWidget": "false"}
print("P4.4 Skinning: UseMutantLootWithoutWidget true -> false  OK")

# --- P4.5) Summary ---
joined = "\n".join(summarize(S(mutant_smell_factor=0.5, mutants_no_smell=True, burer_fire_interval_factor=2.0,
                               mutant_loot_widget=True)))
for needle in ("sense of smell", "cannot smell", "Burer weapon fire", "loot window"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("smell", "Burer", "loot window"))
print("P4.5 Summary: 4 lines present, neutral empty  OK")

# A-Life and corpses.
NEEDS = "NPCNeedsPresetPrototypes/NPCNeedsPresetPrototypes_patch_S2Tweaker.cfg"
POL = "ALifePrototypes/ALifePolicyPrototypes/ALifePolicyPrototypes_patch_S2Tweaker.cfg"
FAC = ("ALifePrototypes/ALifePopulationManagerFactionPrototypes/"
       "ALifePopulationManagerFactionPrototypes_patch_S2Tweaker.cfg")

# --- P5.0) Files, schema 22, mod scan, live values match defaults, neutral empty ---
for name in ("NPCNeedsPresetPrototypes.cfg.bin", "ALifePrototypes/ALifePolicyPrototypes.cfg.bin",
             "ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg.bin"):
    assert name in NEEDED_FILES, name
assert CACHE_SCHEMA >= 22 and all(t in _GD_TREES for t in ("needspresets", "alifepolicy", "alifefactions"))
pol_live = gd.alifepolicy.children["Default"].values
assert pol_live["FullWipeRefillCooldown"] == "360.f" and pol_live["MinRefillDistance"] == "20000"
assert int(pol_live["MaxCorpsePerRadius"]) == Settings().corpse_budget
fac_live = gd.alifefactions.children["ALifePopulationManagerPreset"].children["Factions"].children
assert len(fac_live) == 29 and {int(n.values["ALifeLairExpansionBattleChance"]) for n in fac_live.values()} == {Settings().faction_battle_chance}
assert int(gd.corevar("AlifeCorpsesHardcap")) == Settings().alife_corpse_hardcap
exp_live = [(sid, idx) for sid, n in gd.needspresets.children.items()
            for idx, e in (n.children["GoalNeeds"].children.items() if "GoalNeeds" in n.children else [])
            if e.values.get("NeedTag", "").strip() == "AI.Need.Expansion"]
assert len(exp_live) == 16 and ("MutantGenericNeedsPreset", "[1]") in exp_live, exp_live
assert not build_patches(gd, S(squad_expansion_factor=1.0, refill_cooldown_factor=1.0, refill_distance_factor=1.0,
                               corpse_budget=30, faction_battle_chance=50, faction_expansion_pace_factor=1.0,
                               corpse_distance_factor=1.0, alife_corpse_hardcap=1500))
print("P5.0 Files: three new, schema 22, 16 live expansion entries (MutantGeneric at [1]), 29 factions, neutral empty  OK")

# --- P5.1) Squad expansion: 16 presets, complete entries, special values ---
p = build_patches(gd, S(squad_expansion_factor=2.0))
nd = parsed(p, NEEDS)
assert len(nd.children) == 16, sorted(nd.children)
human = nd.children["HumanGenericNeedsPreset"].children["GoalNeeds"].children
assert list(human) == ["[0]"] and human["[0]"].values == {
    "NeedTag": "AI.Need.Expansion", "InitialNeedValue": "65.0", "MinIncreasePerMinute": "12.0",
    "MaxIncreasePerMinute": "20.0", "NeedSatisfactionThreshold": "100.0"}, human["[0]"].values
zombie = nd.children["ZombieNeedsPreset"].children["GoalNeeds"].children["[0]"].values
assert zombie["MinIncreasePerMinute"] == "2.0" and zombie["MaxIncreasePerMinute"] == "6.0" and zombie["InitialNeedValue"] == "0.0"
mut = nd.children["MutantGenericNeedsPreset"].children["GoalNeeds"].children
assert list(mut) == ["[1]"] and mut["[1]"].values["MinIncreasePerMinute"] == "14.0" and mut["[1]"].values["MaxIncreasePerMinute"] == "22.0"
assert mut["[1]"].values["InitialNeedValue"] == "80.0" and len(mut["[1]"].values) == 5
for absent in ("ReuniteWithLair", "MilitariesNeedsPreset", "NoonNeedsPreset", "SparkNeedsPreset", "CorpusNeedsPreset",
               "MutantGenericNeedsNoExpansionPreset", "ScientistsNeedsPreset", "QuestNPCNeedsPreset",
               "   Needs : struct.begin"):
    assert absent not in p[NEEDS], absent
assert "GoalNeeds : struct.begin {bpatch}" in p[NEEDS] and "[1] : struct.begin {bpatch}" in p[NEEDS]
assert NEEDS not in build_patches(gd, S(squad_expansion_factor=1.0))
quarter = parsed(build_patches(gd, S(squad_expansion_factor=0.25)), NEEDS).children["DutyNeedsPreset_Guard"] \
    .children["GoalNeeds"].children["[0]"].values
assert quarter["MinIncreasePerMinute"] == "1.5" and quarter["MaxIncreasePerMinute"] == "2.5"
print("P5.1 Expansion: 16 presets x2 (6/10 -> 12/20, Zombie 2/6, MutantGeneric [1] 14/22), complete entries  OK")

# --- P5.2) A-Life policy: cooldowns, integer distance range, budget ---
p = build_patches(gd, S(refill_cooldown_factor=0.5, refill_distance_factor=2.0, corpse_budget=60))
pol = parsed(p, POL)
assert list(pol.children) == ["Default"] and pol.children["Default"].values == {
    "FullWipeRefillCooldown": "180.0f", "PartialWipeRefillCooldown": "60.0f",
    "MinRefillDistance": "40000", "MaxRefillDistance": "50000", "MaxCorpsePerRadius": "60"}, pol.children["Default"].values
assert "Default : struct.begin {bpatch}" in p[POL] and "Extinction" not in p[POL] and "CorpseRadius" not in p[POL]
d = parsed(build_patches(gd, S(refill_distance_factor=0.5)), POL).children["Default"].values
assert d == {"MinRefillDistance": "10000", "MaxRefillDistance": "12500"} and int(d["MinRefillDistance"]) <= int(d["MaxRefillDistance"])
assert POL not in build_patches(gd, S(corpse_budget=30, refill_cooldown_factor=1.0))
assert parsed(build_patches(gd, S(corpse_budget=5)), POL).children["Default"].values == {"MaxCorpsePerRadius": "5"}
print("P5.2 Policy: Cooldowns x0.5 = 180/60f, Distance x2 = 40000/50000, x0.5 = 10000/12500, Budget 60/5, extinction settings unchanged  OK")

# --- P5.3) Faction expansion: 29 children, camp bands excluded, inverse speed ---
p = build_patches(gd, S(faction_battle_chance=80, faction_expansion_pace_factor=2.0))
fac = parsed(p, FAC)
assert p[FAC].startswith("ALifePopulationManagerPreset : struct.begin {bpatch}")
pre = fac.children["ALifePopulationManagerPreset"]
assert pre.values == {"ALifeLairExpansionTime": "25.0f"}, pre.values
fs = pre.children["Factions"].children
assert len(fs) == 29 and all(n.values == {"ALifeLairExpansionBattleChance": "80"} for n in fs.values())
assert "MinLairs" not in p[FAC] and "MaxLairs" not in p[FAC] and "ALifeLairExpansionRadius" not in p[FAC]
assert parsed(build_patches(gd, S(faction_expansion_pace_factor=0.5)), FAC).children["ALifePopulationManagerPreset"] \
    .values["ALifeLairExpansionTime"] == "100.0f"
assert FAC not in build_patches(gd, S(faction_battle_chance=50, faction_expansion_pace_factor=1.0))
assert parsed(build_patches(gd, S(faction_battle_chance=0)), FAC).children["ALifePopulationManagerPreset"] \
    .children["Factions"].children["Bandits"].values == {"ALifeLairExpansionBattleChance": "0"}
print("P5.3 Factions: 29 x combat chance 80 / 0, speed x2 -> 25.0f (inverse), camp ranges absent  OK")

# --- P5.4) Corpse distances: squared scaling, integrated timers, hard cap ---
core = core_values(corpse_distance_factor=2.0)
assert core == {"CorpseOfflineSquaredDistance": "400000000.0",
                "CorpseOfflineTimeConditionSquaredDistance": "100000000.0",
                "CorpseOfflineCountConditionSquaredDistance": "36000000.0",
                "DistanceToDestroyCorpsesIfOverpopulated": "60000"}, core
core = core_values(corpse_distance_factor=0.5)
assert core["CorpseOfflineSquaredDistance"] == "25000000.0" and core["DistanceToDestroyCorpsesIfOverpopulated"] == "15000"
core = core_values(corpse_time_factor=2.0)
assert core["CorpseOffscreenLifetime"] == "6.0" and core["CorpseDespawnToOfflineTimeCoef"] == "1.0" and core["CorpseOnlineTime"] == "3600.0"
assert core_values(alife_corpse_hardcap=3000) == {"AlifeCorpsesHardcap": "3000"}
text = build_patches(gd, S(corpse_distance_factor=2.0, corpse_time_factor=2.0, alife_corpse_hardcap=500))[CORE]
assert "LowMemoryProfile" not in text and "CorpseRagdollQuestProtection" not in text
assert text.count("struct.begin") == 1                                            # DefaultConfig only.
print("P5.4 Corpses: distance x2 -> x4 for squares + 60000, x0.5 -> x0.25, time ordering 6.0/1.0, hard cap 3000  OK")

# --- P5.5) Summary ---
joined = "\n".join(summarize(S(squad_expansion_factor=2.0, refill_cooldown_factor=0.5, refill_distance_factor=2.0,
                               corpse_budget=60, faction_battle_chance=80, faction_expansion_pace_factor=2.0,
                               corpse_distance_factor=2.0, alife_corpse_hardcap=3000)))
for needle in ("squad expansion", "refill cooldown", "refill distance", "corpse budget 60", "battle chance 80",
               "expansion pace", "Corpse distance", "hard cap 3000"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("squad expansion", "refill", "corpse budget", "hard cap"))
print("P5.5 Summary: 8 lines present, neutral empty  OK")

# World and atmosphere.
from s2tweaker.tweaks import RADIATION_PRESETS_OK, CAMP_LIFE_NEEDS, SKY_KEYS   # noqa: E402
BW = "BarbedWirePrototypes/BarbedWirePrototypes_patch_S2Tweaker.cfg"
DES = "DestructibleObjectPrototypes/DestructibleObjectPrototypes_patch_S2Tweaker.cfg"
PHY = "PhysicsInteractionPrototypes/PhysicsInteractionPrototypes_patch_S2Tweaker.cfg"
WCH = "WeatherChainPrototypes/WeatherChainPrototypes_patch_S2Tweaker.cfg"
SKY = "SingletonConstants.cfg_patch_S2Tweaker.cfg"
NEEDS = "NPCNeedsPresetPrototypes/NPCNeedsPresetPrototypes_patch_S2Tweaker.cfg"

# --- P6.0) Files, schema 22, mod scan, neutral empty ---
for name in ("BarbedWirePrototypes.cfg.bin", "DestructibleObjectPrototypes.cfg.bin",
             "PhysicsInteractionPrototypes.cfg.bin", "WeatherChainPrototypes.cfg.bin",
             "SingletonConstants.cfg"):
    assert name in NEEDED_FILES, name
assert CACHE_SCHEMA >= 22
for tree in ("barbedwire", "destructibles", "physicsinteractions", "weatherchains", "singletonconstants"):
    assert tree in _GD_TREES, tree
assert not build_patches(gd, S(radiation_dose_factor=1.0, barbed_wire_factor=1.0, explosive_container_factor=1.0,
                               push_force_factor=1.0, weather_transition_factor=1.0, moon_brightness_factor=1.0,
                               music_combat_threshold=20, music_combat_lifetime=25, camp_life_factor=1.0))
print("P6.0 Files: five new, schema 22, all known to mod scan, neutral empty  OK")

# Scale ordinary radiation presets; exclude Deadly, RadBlock and Custom.
p = build_patches(gd, S(radiation_dose_factor=2.0, radiation_filter_factor=2.0, geiger_volume_factor=0.5))
rad = parsed(p, CORE).children["DefaultConfig"].children["RadiationPresetValues"].children
assert sorted(rad) == ["[0]", "[1]", "[2]", "[6]"], sorted(rad)
assert len(RADIATION_PRESETS_OK) == 4
assert rad["[0]"].values == {"Preset": "ERadiationPreset::Light", "RadioactivityValue": "15.f",
                             "RadiationPerSecondValue": "2.0f", "GeigerRadiationIntensity": "0.2f",
                             "PostProcessRadiationIntensity": "1.0f"}, rad["[0]"].values
assert rad["[2]"].values["RadiationPerSecondValue"] == "12.0f" and rad["[2]"].values["PostProcessRadiationIntensity"] == "1.0f"
assert rad["[6]"].values["GeigerRadiationIntensity"] == "0.1f" and rad["[6]"].values["RadioactivityValue"] == "15.f"
for tabu in ("Deadly", "RadBlock", "Custom", "RadBlockFieldDamage", "EffectPrototypeSIDs"):
    assert tabu not in p[CORE], tabu
assert CORE not in build_patches(gd, S(radiation_dose_factor=1.0))
print("P6.1 Radiation: complete [0]/[1]/[2]/[6], dose x2, filter capped at 1.0f, Geiger x0.5, death zones absent  OK")

# --- P6.2) Combat music: absolute values compared with live data, f suffix ---
assert core_values(music_combat_threshold=50, music_combat_lifetime=10) == {
    "MusicManagerCombatScoreThreshold": "50.0f", "MusicManagerCombatEnemyAttackActionLifetimeSeconds": "10.0f"}
assert CORE not in build_patches(gd, S(music_combat_threshold=20, music_combat_lifetime=25))
print("P6.2 Combat music: threshold 50.0f, delay 10.0f, vanilla produces nothing  OK")

# --- P6.3) Barbed wire: both prototypes, base [0] unchanged ---
bw = parsed(build_patches(gd, S(barbed_wire_factor=2.0)), BW)
assert sorted(bw.children) == ["LimitingBarbedWire", "OverlappableBarbedWire"], sorted(bw.children)
assert bw.children["LimitingBarbedWire"].values == {"Damage": "20.0", "BleedingValue": "50.0",
                                                    "ArmorDamage": "10.0", "BleedingChance": "0.2"}
assert bw.children["OverlappableBarbedWire"].values["Damage"] == "20.0"
bw = parsed(build_patches(gd, S(barbed_wire_factor=0.0)), BW)
assert bw.children["LimitingBarbedWire"].values == {"Damage": "0.0", "BleedingValue": "0.0",
                                                    "ArmorDamage": "0.0", "BleedingChance": "0.0"}
assert parsed(build_patches(gd, S(barbed_wire_factor=20.0)), BW).children["LimitingBarbedWire"] \
    .values["BleedingChance"] == "1.0"                                      # cap
assert "ArmorPiercing" not in build_patches(gd, S(barbed_wire_factor=2.0))[BW]
print("P6.3 Barbed wire: both prototypes x2 / x0, chance capped at 1.0, base [0] unchanged  OK")

# --- P6.4) Explosive containers: 22 explosion structs, complete phase ---
live_exp = [k for k, n in gd.destructibles.children.items()
            if (n.values.get("SID") or "").startswith("Exp_") or "_Exp_" in (n.values.get("SID") or "")]
assert len(live_exp) == 22, len(live_exp)
p = build_patches(gd, S(explosive_container_factor=0.5))
des = parsed(p, DES)
assert len(des.children) == 22 and all(k.startswith("[") for k in des.children), sorted(des.children)[:3]
first = des.children[live_exp[0]].children["ObjectPhaseSettings"].children["[0]"].values
assert first == {"DamageIgnoranceThreshold": "3.0", "DamageDestroyThreshold": "20.0"}, first
assert "DestructibleActions" not in p[DES] and "AssetPath" not in p[DES] and "OriginalMesh" not in p[DES]
assert "ObjectPhaseSettings : struct.begin {bpatch}" in p[DES]
assert DES not in build_patches(gd, S(explosive_container_factor=1.0))
print(f"P6.4 Containers: {len(des.children)} explosion prototypes, threshold 40 -> 20, phase with both scalars, assets excluded  OK")

# --- P6.5) Impulse: all 88 prototypes ---
phy = parsed(build_patches(gd, S(push_force_factor=2.0)), PHY)
assert len(phy.children) == 88 and len(gd.physicsinteractions.children) == 88, len(phy.children)
assert phy.children["Empty"].values == {"PlayerPushImpulse": "2000.0"}
assert all(list(n.values) == ["PlayerPushImpulse"] for n in phy.children.values())
assert PHY not in build_patches(gd, S(push_force_factor=1.0))
print("P6.5 Impulse: all 88 prototypes x2, only the single key  OK")

# --- P6.6) Weather transitions: 22 multipliers, both levels complete, inverse ---
p = build_patches(gd, S(weather_transition_factor=2.0))
wch = parsed(p, WCH)
total = 0
for n in wch.children.values():
    for st in n.children["TransitionSteps"].children.values():
        assert "WeatherChainWeight" in st.values, st.values          # Complete first level.
        for ch in st.children["WeatherChains"].children.values():
            assert "WeatherType" in ch.values, ch.values             # Complete second level.
            assert ch.values["WeatherTransitionTimeMultiplier"] == "0.5"
            total += 1
assert total == 22, total
assert wch.children["ClearlyToRainy"].children["TransitionSteps"].children["[0]"].values["WeatherChainWeight"] == "100"
assert parsed(build_patches(gd, S(weather_transition_factor=0.5)), WCH).children["ClearlyToRainy"] \
    .children["TransitionSteps"].children["[0]"].children["WeatherChains"].children["[0]"] \
    .values["WeatherTransitionTimeMultiplier"] == "2.0"
assert WCH not in build_patches(gd, S(weather_transition_factor=1.0))
print(f"P6.6 Weather: {total} inverse multipliers (x2 -> 0.5), weights emitted unchanged  OK")

# Use a separate sky patch with protected keys absent.
assert len(SKY_KEYS) == 6
p = build_patches(gd, S(moon_brightness_factor=2.0, sun_brightness_factor=0.5, stars_brightness_factor=5.0,
                        cloud_opacity_factor=2.0, cloud_speed_factor=3.0, dusk_length_factor=0.5))
assert SKY in p and "/" not in SKY                                    # Directly in GameData/.
sky = parsed(p, SKY).children["TimeManager"].values
assert sky == {"MoonLightMaxBrightness": "2.092f", "SunLightMaxBrightness": "1.57f",
               "StarsBrightness": "0.5f", "CloudOpacity": "1.0f", "CloudSpeed": "3.0f",
               "LightSourceFadingDurationHoursOnDayNightChange": "1.0f"}, sky
assert "TimeManager : struct.begin {bpatch}" in p[SKY]
for tabu in ("Latitude", "Longitude", "TimeZone", "NorthOffsetAngle", "StartYear", "StartHour", "InputManager"):
    assert tabu not in p[SKY], tabu
assert SKY not in build_patches(gd, S(moon_brightness_factor=1.0))
print("P6.7 Sky: SingletonConstants.cfg_patch_* in GameData/, 6 keys with f suffix, clouds capped, excluded keys absent  OK")

# Patch only supported camp needs with complete entries.
assert len(CAMP_LIFE_NEEDS) == 8
p = build_patches(gd, S(camp_life_factor=2.0))
nd = parsed(p, NEEDS)
# Exclude the [0] template from concrete preset counts.
assert len(nd.children) == 25 == len(gd.needspresets.children) - 1, len(nd.children)
assert "[0]" not in nd.children
seen = set()
for node in nd.children.values():
    assert "GoalNeeds" not in node.children                       # Without the expansion slider.
    for e in node.children["Needs"].children.values():
        t = e.values["NeedType"]
        seen.add(t)
        assert t in CAMP_LIFE_NEEDS, t
        assert {"NeedType", "IncreaseRateMin", "IncreaseRateMax", "Radius", "MaxCount"} <= set(e.values), e.values
assert seen == set(CAMP_LIFE_NEEDS), sorted(seen)
guitar = next(e.values for e in nd.children["NeutralsNeedsPreset"].children["Needs"].children.values()
              if e.values["NeedType"] == "EContextualActionNeeds::Guitar")
# Scale the nonstandard Neutrals guitar values while retaining suffixes.
assert guitar["IncreaseRateMin"] == "10.0f" and guitar["IncreaseRateMax"] == "30.0f", guitar
assert guitar["Radius"] == "5500.f" and guitar["MaxCount"] == "1", guitar
# Match excluded needs by full enum name, avoiding unrelated preset-name substrings.
for tabu in ("Patrolling", "Emission", "Work", "Guard", "Monolog", "RunOnTalking",
             "WeaponCleaning", "PDA", "Idle", "Detector"):
    assert "EContextualActionNeeds::" + tabu not in p[NEEDS], tabu
both = parsed(build_patches(gd, S(camp_life_factor=2.0, squad_expansion_factor=2.0)), NEEDS)
assert "GoalNeeds" in both.children["HumanGenericNeedsPreset"].children
assert "Needs" in both.children["HumanGenericNeedsPreset"].children
print("P6.8 Camp life: 25 presets, only 8 needs, complete entries, combined with expansion  OK")

# --- P6.9) Summary ---
joined = "\n".join(summarize(S(radiation_dose_factor=2.0, radiation_filter_factor=0.0, geiger_volume_factor=2.0,
                               barbed_wire_factor=0.0, explosive_container_factor=0.5, push_force_factor=2.0,
                               weather_transition_factor=2.0, moon_brightness_factor=2.0, sun_brightness_factor=2.0,
                               stars_brightness_factor=2.0, cloud_opacity_factor=0.5, cloud_speed_factor=2.0,
                               dusk_length_factor=2.0, music_combat_threshold=50, music_combat_lifetime=10,
                               camp_life_factor=2.0)))
for needle in ("Radiation dose", "Radiation screen filter", "Geiger", "Barbed wire", "Explosive containers",
               "Push and kick", "Weather transition", "Moon brightness", "Sun brightness", "Stars",
               "Cloud opacity", "Cloud speed", "Dusk & dawn", "music threshold 50", "music lingers 10",
               "Camp life"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("Radiation dose", "Barbed", "Moon", "Camp life", "music"))
print("P6.9 Summary: 16 lines present, neutral empty  OK")

# Artifacts and loot.
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
POI = "PackOfItemsGroupPrototypes/PackOfItemsGroupPrototypes_patch_S2Tweaker.cfg"

# Verify artifact field inventory.
assert "PackOfItemsGroupPrototypes.cfg.bin" in NEEDED_FILES and CACHE_SCHEMA >= 22
assert "packofitems" in _GD_TREES
arts = {sid: n for sid, n in gd.items.children.items() if "#" not in sid and "Strafe" in n.values}
assert len(arts) == 154, len(arts)
for key in ("Radius", "PlayerDistance", "JumpSeriesDelay"):
    assert all(key in n.values for n in arts.values()), key      # Each defines its own values.
strafe_true = [s for s, n in arts.items() if n.values["Strafe"].strip() == "true"]
assert len(strafe_true) == 146 and len(arts) - len(strafe_true) == 8
radii = sorted({n.values["Radius"].strip() for n in arts.values()})
assert radii == ["10", "10.0", "40.0"], radii
far = [s for s, n in arts.items() if n.values["PlayerDistance"].strip() == "100000.0"]
assert far == ["QuestArtifactCrystalThorn"], far
assert gd.corevars.children["DefaultConfig"].values["ArtifactStrafeMinDistance"] == "600.0"
assert not build_patches(gd, S(artifact_radius_factor=1.0, artifact_keepaway_factor=1.0,
                               artifact_hop_pause_factor=1.0, loot_reroll_radius_factor=1.0,
                               loot_reroll_timer_factor=1.0))
print(f"P7.0 Artifacts: {len(arts)} structs, all self-defined, 146 jump, radii {radii}, neutral empty  OK")

# --- P7.1) Visibility radius ---
it = parsed(build_patches(gd, S(artifact_radius_factor=19.0)), ITEMS)
assert len(it.children) == 154, len(it.children)
assert it.children["TemplateArtifact"].values == {"Radius": "760.0"}
assert it.children["AArtifactWeirdBall"].values == {"Radius": "190.0"}      # Vanilla 10
assert all(list(n.values) == ["Radius"] for n in it.children.values())
assert ITEMS not in build_patches(gd, S(artifact_radius_factor=1.0))
print("P7.1 Radius: 154 artifacts x19 (40 -> 760, 10 -> 190), only the single key  OK")

# Disable jumping only where enabled in vanilla.
it = parsed(build_patches(gd, S(artifacts_no_hop=True)), ITEMS)
assert len(it.children) == 146, len(it.children)
assert all(n.values == {"Strafe": "false"} for n in it.children.values())
for keeper in ("AArtifactWeirdBall", "AArtifactWeirdFlower", "CPrologArtifactSlug",
               "QuestArtifactHeartofChornobyl"):
    assert keeper not in it.children, keeper
assert "TemplateArtifact" in it.children
print("P7.2 Jumping: toggle reaches exactly 146 true artifacts, 8 false entries remain  OK")

# Check keep-away/jump delays, including unusual values and zero.
p = build_patches(gd, S(artifact_keepaway_factor=0.5, artifact_hop_pause_factor=2.0))
it = parsed(p, ITEMS)
# Compose ReturnDistanceValue with spacing and JumpDelay with pause controls;
# see test_v135_tweaks.py for the complete jump family.
assert it.children["TemplateArtifact"].values == {
    "PlayerDistance": "500.0", "ReturnDistanceValue": "5000.0",
    "JumpSeriesDelay": "90.0", "JumpDelay": "12.0"}, \
    it.children["TemplateArtifact"].values
assert it.children["QuestArtifactCrystalThorn"].values["PlayerDistance"] == "50000.0"   # Outlier is scaled too.
zero = [s for s, n in arts.items() if parse_number(n.values["JumpSeriesDelay"]) == 0]
assert zero and all("JumpSeriesDelay" not in it.children[s].values for s in zero if s in it.children)
core = parsed(p, CORE).children["DefaultConfig"].values
assert core == {"ArtifactStrafeMinDistance": "300.0"}, core
print(f"P7.3 Jump values: distance x0.5 (including the 100000 outlier), pause x2, {len(zero)} zero values skipped  OK")

# --- P7.4) Rare artifact stashes ---
live = gd.packofitems.children["ArtifactUncommon"].children["PackOfItemsSettings"]
live_items = live.children["[0]"].children["Items"].children
assert len(live_items) == 20 and {e.values["Weight"] for e in live_items.values()} == {"0"}
p = build_patches(gd, S(artifact_caches_drop=True))
poi = parsed(p, POI)
assert list(poi.children) == ["ArtifactUncommon"], list(poi.children)
entries = poi.children["ArtifactUncommon"].children["PackOfItemsSettings"].children["[0]"] \
    .children["Items"].children
assert len(entries) == 20, len(entries)
assert all(e.values["Weight"] == "1" and e.values.get("ItemPrototypeSID") for e in entries.values())
assert entries["[0]"].values["ItemPrototypeSID"] == "EArtifactMoonlight", entries["[0]"].values
assert "ArtifactUncommon : struct.begin {bpatch}" in p[POI]
for other in ("Medkits", "Stimulator", "Drink", "Food", "empty"):
    assert other not in p[POI], other
assert POI not in build_patches(gd, S())
print("P7.4 Stashes: ArtifactUncommon only, 20 complete entries set to Weight 1, other groups unchanged  OK")

# --- P7.5) Reroll loot on rank increase ---
assert core_values(loot_reroll_radius_factor=2.0, loot_reroll_timer_factor=0.5) == {
    "RegenerateItemsOnRankUpdateRadius": "80000.0f", "RegenerateItemsOnRankUpdateTimer": "5.0f"}
print("P7.5 Reroll: radius 80000.0f, delay 5.0f  OK")

# --- P7.6) Summary ---
joined = "\n".join(summarize(S(artifact_radius_factor=19.0, artifacts_no_hop=True,
                               artifact_keepaway_factor=0.5, artifact_hop_pause_factor=2.0,
                               artifact_caches_drop=True, loot_reroll_radius_factor=2.0,
                               loot_reroll_timer_factor=0.5)))
for needle in ("visibility radius", "don't hop away", "keep-away", "hop pause",
               "caches actually drop", "re-roll radius", "re-roll delay"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("visibility radius", "hop", "caches", "re-roll"))
print("P7.6 Summary: 7 lines present, neutral empty  OK")

# Traders and economy.
NPCP = "NPCPrototypes/NPCPrototypes_patch_S2Tweaker.cfg"
TRADE = "TradePrototypes/TradePrototypes_patch_S2Tweaker.cfg"
TRADERS9 = ["Eger", "Guron", "Koldun", "KoldunM", "Sinak", "drabadan", "sulc",
            "supack_trader_selma_0", "trader_assistent_medulin_0"]

# --- P8.0) File, schema 22, mod scan intentionally excludes NPCPrototypes ---
assert "NPCPrototypes.cfg.bin" in NEEDED_FILES and CACHE_SCHEMA >= 22
# Keep large lazily parsed files outside the eager vanilla scan index.
assert "npcprototypes" not in _GD_TREES
assert int(gd.corevar("InfotopicRefreshHours")) == Settings().infotopic_refresh_hours
rep = gd.corevars.children["DefaultConfig"].children["ReputationRepairCostModifiers"].children
assert [e.values["Modifier"] for e in rep.values()] == ["2.0", "1.5", "1.0", "0.75"]
assert not build_patches(gd, S(repair_cost_reputation=False, infotopic_refresh_hours=24))
print("P8.0 File: NPCPrototypes in NEEDED_FILES, intentionally excluded from mod scan, live values match defaults  OK")

# Emit complete reputation repair entries at the neutral modifier.
p = build_patches(gd, S(repair_cost_reputation=True))
arr = parsed(p, CORE).children["DefaultConfig"].children["ReputationRepairCostModifiers"].children
assert sorted(arr) == ["[0]", "[1]", "[2]", "[3]"], sorted(arr)
assert arr["[0]"].values == {"RelationLevel": "ERelationLevel::Enemy", "Modifier": "1.0"}
assert arr["[3]"].values == {"RelationLevel": "ERelationLevel::Friend", "Modifier": "1.0"}
assert all(e.values["Modifier"] == "1.0" for e in arr.values())
assert "BaseRepairCostModifier" not in p[CORE]                    # The general price control remains separate.
print("P8.1 Repair reputation: all four levels set to 1.0, RelationLevel included  OK")

# --- P8.2) Rumor refresh: absolute integer ---
assert core_values(infotopic_refresh_hours=6) == {"InfotopicRefreshHours": "6"}
assert core_values(infotopic_refresh_hours=72) == {"InfotopicRefreshHours": "72"}
assert CORE not in build_patches(gd, S(infotopic_refresh_hours=24))
print("P8.2 Rumors: 6 h / 72 h, vanilla 24 produces nothing  OK")

# Check NPC trader coefficients and wallets against live data.
live_buy = {s for s, n in gd.npcprototypes.children.items() if "BuyCoefficient" in n.values}
live_sell = {s for s, n in gd.npcprototypes.children.items() if "SellCoefficient" in n.values}
assert sorted(live_buy) == TRADERS9 and live_buy == live_sell, sorted(live_buy)
live_money = {s for s, n in gd.npcprototypes.children.items()
              if parse_number(n.values.get("Money"), 0.0) > 0}
assert live_money, "No NPC money entries found in the installed game data"
np_ = parsed(build_patches(gd, S(trader_buy_price_factor=2.0, trader_sell_price_factor=0.5)), NPCP)
assert sorted(np_.children) == TRADERS9, sorted(np_.children)
assert np_.children["Koldun"].values == {"BuyCoefficient": "1.6", "SellCoefficient": "1.0"}
np_ = parsed(build_patches(gd, S(trader_money_factor=2.0)), NPCP)
assert set(np_.children) == live_money
assert all(list(n.values) == ["Money"] for n in np_.children.values())
for sid in live_money:
    before = parse_number(gd.npcprototypes.children[sid].values["Money"])
    assert parse_number(np_.children[sid].values["Money"]) == round(before * 2), sid
assert np_.children["Eger"].values == {"Money": "40000"}
assert all("." not in n.values["Money"] for n in np_.children.values())      # integer
p = build_patches(gd, S(trader_buy_price_factor=2.0))
assert TRADE in p and NPCP in p                     # Both levels receive the same factor.
assert NPCP not in build_patches(gd, S(trader_min_durability_pct=0))   # Unrelated controls must not emit NPC patches.
print(f"P8.3 Traders: 9 coefficients (0.8 -> 1.6 / 2.0 -> 1.0), {len(live_money)} wallets x2, both levels  OK")

# Parse the large NPC file only when needed.
fresh = GameData(VANILLA)
assert not build_patches(fresh, S())
assert "npcprototypes" not in fresh.__dict__, "Neutral setting parsed the 1.8-MB file"
build_patches(fresh, S(trader_money_factor=2.0))
assert "npcprototypes" in fresh.__dict__
print("P8.4 Lazy loading: NPCPrototypes remains unparsed at neutral, loads when slider is active  OK")

# --- P8.5) Summary ---
joined = "\n".join(summarize(S(repair_cost_reputation=True, infotopic_refresh_hours=6)))
assert "Reputation does not affect repair prices" in joined and "rumours refresh every 6 h" in joined
assert not any(k in "\n".join(summarize(S())) for k in ("Reputation does not", "rumours refresh"))
print("P8.5 Summary: 2 lines present, neutral empty  OK")

# Weapon draw and holster controls.
WGS = "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg"
EQUIP_KEYS = ("ShowEquipmentTime", "HideEquipmentTime")

# Check the installed base-weapon timing inventory.
live = {sid: n.values for sid, n in gd.weapongeneral.children.items()
        if "#" not in sid and "ShowEquipmentTime" in n.values}
assert len(live) == 92, len(live)
assert {v["ShowEquipmentTime"] for v in live.values()} == {"1.0"}
assert {v["HideEquipmentTime"] for v in live.values()} == {"1.0"}
assert not build_patches(gd, S(equip_speed_factor=1.0))
print(f"1.29.0 Live: {len(live)} weapons with draw/holster duration, all 1.0, neutral empty  OK")

# Scale base and edition timings inversely.
p = build_patches(gd, S(equip_speed_factor=2.0))
wgs = parsed(p, WGS)
assert len(wgs.children) == 92, len(wgs.children)
assert all(n.values == {"ShowEquipmentTime": "0.5", "HideEquipmentTime": "0.5"}
           for n in wgs.children.values())
dlc = [k for k in p if k.startswith("//GameLite/DLCGameData/") and "WeaponGeneralSetup" in k]
assert len(dlc) == 3, dlc                       # Deluxe, PreOrder, Ultimate
n_dlc = sum(len(parsed(p, k).children) for k in dlc)
assert n_dlc == 11, n_dlc
assert all(v == "0.5" for k in dlc for n in parsed(p, k).children.values()
           for key, v in n.values.items() if key in EQUIP_KEYS)
half = parsed(build_patches(gd, S(equip_speed_factor=0.5)), WGS)
assert next(iter(half.children.values())).values["ShowEquipmentTime"] == "2.0"
assert "FireInterval" not in p[WGS] and "ReloadTimeMultiplier" not in p[WGS]
print(f"1.29.0 Sliders: 92 base + {n_dlc} edition weapons, x2 -> 0.5 s, x0.5 -> 2.0 s  OK")

# --- 3) Skipped firing animations ---
live_skip = {sid: n.values["ShootingAnimationNumberToSkip"]
             for sid, n in gd.weapongeneral.children.items()
             if "#" not in sid and "ShootingAnimationNumberToSkip" in n.values}
assert len(live_skip) == 92 and set(live_skip.values()) == {"0"}, len(live_skip)
p = build_patches(gd, S(shooting_anim_skip=1))
wgs = parsed(p, WGS)
assert len(wgs.children) == 92, len(wgs.children)
assert all(n.values == {"ShootingAnimationNumberToSkip": "1"} for n in wgs.children.values())
dlc = [k for k in p if k.startswith("//GameLite/DLCGameData/") and "WeaponGeneralSetup" in k]
assert sum(len(parsed(p, k).children) for k in dlc) == 11, dlc
assert parsed(build_patches(gd, S(shooting_anim_skip=3)), WGS).children["Default"] \
    .values["ShootingAnimationNumberToSkip"] == "3"
assert WGS not in build_patches(gd, S(shooting_anim_skip=0))          # Vanilla emits no patch.
print("1.29.0 Animation skip: 92 base + 11 edition weapons set to 1 or 3, integers, vanilla empty  OK")

# --- 4) Summary ---
assert "Weapon draw & holster speed × 2" in "\n".join(summarize(S(equip_speed_factor=2.0)))
assert "Skip 1 shooting animation" in "\n".join(summarize(S(shooting_anim_skip=1)))
assert "draw & holster" not in "\n".join(summarize(S()))
assert "Skip" not in "\n".join(summarize(S()))
print("1.29.0 Summary: two lines present, neutral empty  OK")

print("\n1.28.0-TEST OK")
