"""Regression coverage for controls introduced in 1.27.0, using live baselines."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker import cfgparse                       # noqa: E402
from s2tweaker.cfgparse import parse_number          # noqa: E402
from s2tweaker.gamedata import GameData              # noqa: E402
from s2tweaker.tweaks import Settings, build_patches, summarize  # noqa: E402

gd = GameData(VANILLA)
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
EFF = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"
AI = "AIGlobals.cfg_patch_S2Tweaker.cfg"
DIFF = "DifficultyPrototypes/DifficultyPrototypes_patch_S2Tweaker.cfg"
SYNC = "CombatSynchronizationPrototypes/CombatSynchronizationPrototypes_patch_S2Tweaker.cfg"
CONT = "ItemContainerPrototypes/ItemContainerPrototypes_patch_S2Tweaker.cfg"


def parsed(patches, name):
    return cfgparse.parse(patches[name]) if name in patches else None


def S(**kw):
    return Settings(mod_name="S2Tweaker", **kw)


# --- 0) Neutral -----------------------------------------------------------
neutral = build_patches(gd, S())
for name in (SYNC, CONT, DIFF, AI):
    assert name not in neutral, name
for name, keys in ((OBJ, ("BackCoef", "AirControl", "Limp", "RegenHPDelay", "Degen", "StealthKill", "HideWeaponWarning", "Camper")),
                   (CORE, ("SlowRun", "ItemSelector", "PlayerBed", "DespawnItem", "StartTime", "CalmDamage", "LastBullet",
                           "ArmorDeflect", "ArmorDifference", "ItemCostMin", "Energetic", "TeleportScreen")),
                   (EFF, ("AimingFOVX", "ScopeAiming", "DispersionPos", "DurabilityPos", "protection"))):
    text = neutral.get(name, "")
    assert not any(k in text for k in keys), (name, keys)
print("Neutral: no 1.27.0 keys  OK")

# --- 1) Player: movement ---
mv = parsed(build_patches(gd, S(back_speed_factor=1.5, air_control_factor=20.0, limp_speed_factor=3.0)), OBJ)
mv = mv.children["Player"].children["MovementParams"].values
assert mv["WalkBackCoef"] == "0.75" and mv["RunBackCoef"] == "0.6486", mv
assert mv["AirControlCoef"] == "1.0" and mv["LimpSpeedCoef"] == "1.0", mv       # cap
assert len([k for k in mv if "Back" in k]) == 6
print("Movement: backward x1.5, air control/limping capped at 1.0  OK")

# --- 2) Player: recovery, stealth kill, warnings, camping, armor difference ---
pl = parsed(build_patches(gd, S(hp_regen_delay=0, radiation_decay_factor=2.0, bleeding_stop_factor=0.0,
                                psy_recovery_factor=3.0, sober_up_factor=2.0, stealth_kill_range_factor=2.0,
                                weapon_warning_count=1, weapon_warning_delay_factor=0.5, camper_time_factor=3.0,
                                armor_difference_factor=0.5)), OBJ).children["Player"]
vit = pl.children["VitalParams"].values
assert vit["RegenHPDelayTimeSeconds"] == "0.0" and vit["DegenRadiation"] == "0.1" and vit["DegenBleeding"] == "0.0"
assert vit["DegenPsyPoints"] == "3.0" and vit["DegenDrunknessPoints"] == "2.0", vit
assert pl.children["StealthKillParams"].values["StealthKillDistance"] == "360.0"
warn = pl.children["HideWeaponWarning"].values
assert warn == {"WarningAttemptsBeforeAlert": "1", "BarkDelay": "5.0"}, warn
assert pl.children["CamperFeatureData"].values["TimeToAssumeAsCamper"] == "30.0"
assert pl.values["ArmorDifferenceCoefProjectiles"] == "0.8" and pl.values["ArmorDifferenceCoefMeleeAttacks"] == "0.65"
assert OBJ not in build_patches(gd, S(hp_regen_delay=5))                    # Vanilla value emits no patch.
print("Player: regeneration delay 0, recovery x2/x0/x3/x2, stealth kill 360, warnings 1, camping 30 s  OK")

# --- 3) CoreVariables ---------------------------------------------------------
core = parsed(build_patches(gd, S(slow_run_threshold_pct=0, wheel_time_pct=100, sleep_fade_factor=0.0,
                                  corpse_drag_factor=2.0, item_despawn_factor=2.0, day_start_hour=4,
                                  evening_start_hour=18, calm_damage_factor=0.4, last_bullet_multiplier=1.0,
                                  armor_difference_factor=0.5, armor_deflect_chance_pct=50,
                                  armor_deflect_damage_factor=2.0, min_resale_pct=50, energy_tolerance_factor=2.0,
                                  instant_teleports=True)), CORE).children["DefaultConfig"].values
assert core["SlowRunThreshold"] == "0.0f" and core["ItemSelectorTimeDilationCoefficient"] == "1.0", core
assert core["PlayerBedFadeToBlackTime"] == "0.0f" and core["PlayerBedBlackScreenTime"] == "0.0f"
assert core["DraggingCorpseSpeedCoef"] == "1.0"                                 # cap
assert core["UntouchedDespawnItemTime"] == "7200.0f" and core["DespawnItemTime"] == "21600.0f"
assert core["DayStartTime"] == "4.0" and core["DawnStartTime"] == "3.0" and core["EveningStartTime"] == "18.0"
assert core["CalmDamageFromPlayerCoef"] == "1.0" and core["LastBulletBaseDamageMultiplier"] == "1.0"
assert core["ArmorDifferenceCoef"] == "1.0f" and core["ArmorDeflectMinChance"] == "0.5" == core["ArmorDeflectMaxChance"]
assert core["ArmorDeflectDamageCoefHuman"] == "3.0" and core["ItemCostMinPercent"] == "0.5"
assert core["VitalMaxEnergeticOveruse"] == "2000.0f" and core["VitalMaxEnergeticTolerance"] == "5000.0f"
assert core["GenericTeleportScreenShowDelay"] == "0.f" and core["GenericTeleportScreenHideDelay"] == "0.f"
core = parsed(build_patches(gd, S(day_start_hour=7)), CORE).children["DefaultConfig"].values
assert core["DayStartTime"] == "7.0" and "DawnStartTime" not in core
print("CoreVariables: 19 keys set, dawn adjusted only when necessary  OK")

# --- 4) Scopes and upgrade strength ---
eff = parsed(build_patches(gd, S(scope_zoom_factor=2.0, scope_penalty_factor=0.0)), EFF)
assert eff.children["AimingFOVX2Effect"].values["ValueMin"] == "-86.0%"
assert eff.children["AimingFOVX8Effect"].values["ValueMin"] == "-90.0%"          # cap
assert eff.children["ScopeAimingTimeNeg15Effect"].values["ValueMin"] == "0.0%"
assert eff.children["ScopeAimingMovementNeg10Effect"].values["ValueMax"] == "0.0%"
assert "ScopeRecoilPos10Effect" not in eff.children and "ScopeAimingTimePos10Effect" not in eff.children
eff = parsed(build_patches(gd, S(upg_accuracy_factor=2.0, upg_durability_factor=3.0, upg_armor_protection_factor=5.0,
                                 upg_weight_factor=4.0, upg_damage_factor=2.0)), EFF)
assert eff.children["DispersionPos20Effect"].values["ValueMin"] == "-40.0%"
assert eff.children["MaxDispersionPos50Effect"].values["ValueMin"] == "-100.0%"   # cap -100
assert eff.children["DurabilityPos20Effect"].values["ValueMin"] == "60.0%"
assert eff.children["DurabilityPerShotPos20Effect"].values["ValueMin"] == "-60.0%"
assert "DurabilityPerShotNeg20Effect" not in eff.children                        # Preserve the penalty.
assert eff.children["Seva_Armor_protectionThermal"].values["ValueMin"] == "75.0%"
assert eff.children["HeavyAnomaly_Scientific_Armor_protectionPhysical"].values["ValueMin"] == "100.0%"  # cap
assert eff.children["WeightPos30Effect"].values["ValueMin"] == "-100.0%" and eff.children["Nasos_Neutral_Armor_reductionWeight"].values["ValueMin"] == "-4.0"
assert eff.children["ArmorPiercingPos10Effect"].values["ValueMin"] == "20.0%" and eff.children["DamagePos20Effect"].values["ValueMin"] == "40.0%"
assert "DamageNeg10Effect" not in eff.children and "RecoilPos10Effect" not in eff.children
assert "ArtifactSlotBlockEffect3_Slot1" not in eff.children
print("Effects: zoom x2 (cap -90), drawbacks 0, upgrade families respect signs and caps  OK")

# --- 5) AIGlobals ---------------------------------------------------------------
ai = parsed(build_patches(gd, S(npcs_no_weapon_pickup=True, corpse_threat_factor=0.0, darkness_factor=0.5)), AI).children["AISettings"]
assert ai.values["AllowWeaponPickupWhenLooting"] == "false" and ai.values["AllowWeaponPickupBasedOnPrice"] == "false"
assert ai.values["DeadBodyToConsiderAsThreatDuration"] == "0.0"
rows = ai.children["LuminanceSettings"].children["EnvironmentLuminanceCoefficients"].children["TimeOfDayBaseLuminance"].children
assert rows["[0]"].values["Luminance"] == "0.1f" and rows["[1]"].values["Luminance"] == "0.15f", {k: v.values for k, v in rows.items()}
assert "[3]" not in rows                                                           # Preserve entries at 1.0.
print(f"AIGlobals: no weapon pickup, corpses 0 s, {len(rows)} night brightness values halved  OK")

# --- 6) Difficulty ---
diff = parsed(build_patches(gd, S(npc_hip_accuracy_factor=2.0, device_price_factor=0.5, damage_mercy_factor=2.0,
                                  psy_phantom_factor=0.5)), DIFF)
med = diff.children["Medium"]
assert med.children["NPCCombatDifficulty"].values["HipAccuracyMultiplier"] == "2.0"
assert med.children["EconomyDifficulty"].values["Binoculars_Cost"] == "0.5" == med.children["EconomyDifficulty"].values["NightVisionGoggles_Cost"]
assert med.children["NPCCombatDifficulty"].values["AccumulatedDamageReductionCurveWeightMin"] == "0.66"
assert med.children["NPCCombatDifficulty"].values["AccumulatedDamageReductionCurveWeightMax"] == "1.0"   # cap
assert "AccumulatedDamageReductionCurveWeightMin" not in diff.children["Easy"].children["NPCCombatDifficulty"].values
assert diff.children["Stalker"].children["NPCCombatDifficulty"].children["PsyPhantomNPCOverrides"].children["[0]"].values["PsyPhantomNPCCountMultiplier"] == "1.0"
assert "PsyPhantomNPCOverrides" not in med.children["NPCCombatDifficulty"].children
print("Difficulty: hip fire x2, equipment prices x0.5, damping x2 (capped), phantoms x0.5 only Stalker  OK")

# --- 7) Concurrent attackers ---
sync = parsed(build_patches(gd, S(sync_melee_factor=0.2, sync_ability_factor=3.0, sync_grenade_factor=2.0,
                                  sync_suppress_factor=2.0)), SYNC)
med = sync.children["CombatSynchronizerMedium"].children["Newbie"].children["FilterGroups"].children
assert med["[2]"].values["MaxScore"] == "1.f" and med["[3]"].values["MaxScore"] == "3.f" and med["[4]"].values["MaxScore"] == "3.f"
assert med["[9]"].values["MaxScore"] == "2.f" and med["[16]"].values["MaxScore"] == "2.f" and med["[10]"].values["MaxScore"] == "4.f"
assert "[1]" not in med and "[5]" not in med                                    # Range 1000 / Flank unchanged.
assert len(sync.children) == 5 and all(len(n.children) == 4 for n in sync.children.values())
print("Attackers: melee 5 -> 1, abilities 1 -> 3, grenades 1 -> 2, suppressive fire 2 -> 4; 5 structs x 4 ranks  OK")

# --- 8) Containers -----------------------------------------------------------------
cont = parsed(build_patches(gd, S(container_respawn_hours=12)), CONT)
assert len(cont.children) == 25 and all(n.values["RespawnTimeSeconds"] == "43200" for n in cont.children.values()), len(cont.children)
print("Containers: 25 Typen, 12 h = 43200 s  OK")

# --- 8b) Per-scope controls ---
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
table = gd.scope_effects()
assert len(table) == 17 and table["RU_X4Scope_1"][0] == "AimingFOVX4Effect" and table["Gauss_Scope"][1] == [], len(table)
p = build_patches(gd, S(scope_overrides={"RU_X4Scope_1": {"zoom": 1.5, "penalty": 0.0},
                                         "Gauss_Scope": {"zoom": 0.5}, "RU_ColimScope_2": {"penalty": 2.0}}))
eff = parsed(p, EFF)
z = eff.children["S2T_RU_X4Scope_1_AimingFOVX4Effect"]
assert z.attr_dict().get("refkey") == "AimingFOVX4Effect" and z.values["ValueMin"] == "-90.0%", (z.attrs, z.values)
assert eff.children["S2T_RU_X4Scope_1_ScopeAimingTimeNeg15Effect"].values["ValueMin"] == "0.0%"
assert eff.children["S2T_RU_X4Scope_1_ScopeAimingMovementNeg10Effect"].values["ValueMax"] == "0.0%"
assert eff.children["S2T_Gauss_Scope_AimingFOVX4Effect"].values["ValueMin"] == "-30.0%"
assert eff.children["S2T_RU_ColimScope_2_ScopeAimingTimeNeg7Effect"].values["ValueMin"] == "14.0%"
assert "AimingFOVX4Effect" not in eff.children                                     # Global unchanged.
lst = parsed(p, ITEMS).children["RU_X4Scope_1"].children["EffectPrototypeSIDs"].values
assert len(lst) == len(gd.scope_effect_list("RU_X4Scope_1")) >= 5
assert "S2T_RU_X4Scope_1_AimingFOVX4Effect" in lst.values() and "AimingFOVX4Effect" not in lst.values()
assert "ScopeRecoilPos20Effect" in lst.values()                                   # Preserve the rest of the list.
assert "{refkey=AimingFOVX4Effect;bpatch}" in p[EFF]
assert "S2T_" not in build_patches(gd, S()).get(EFF, "")
print("Per scope: 17 scopes, derived effects with refkey, complete lists  OK")

# --- 9) Summary ---
joined = "\n".join(summarize(S(back_speed_factor=2.0, air_control_factor=2.0, limp_speed_factor=2.0, slow_run_threshold_pct=0,
                               hp_regen_delay=0, radiation_decay_factor=2.0, bleeding_stop_factor=2.0, psy_recovery_factor=2.0,
                               sober_up_factor=2.0, stealth_kill_range_factor=2.0, wheel_time_pct=100, sleep_fade_factor=0.0,
                               corpse_drag_factor=2.0, item_despawn_factor=2.0, day_start_hour=5, evening_start_hour=21,
                               calm_damage_factor=2.0, last_bullet_multiplier=1.0, armor_difference_factor=2.0,
                               armor_deflect_chance_pct=0, armor_deflect_damage_factor=2.0, scope_zoom_factor=2.0,
                               scope_penalty_factor=0.0, upg_accuracy_factor=2.0, upg_handling_factor=2.0,
                               upg_durability_factor=2.0, upg_range_factor=2.0, upg_damage_factor=2.0, upg_weight_factor=2.0,
                               upg_breath_factor=2.0, upg_armor_protection_factor=2.0, upg_armor_misc_factor=2.0,
                               weapon_warning_count=1, weapon_warning_delay_factor=2.0, camper_time_factor=2.0,
                               sync_melee_factor=2.0, sync_ability_factor=2.0, sync_grenade_factor=2.0, sync_suppress_factor=2.0,
                               npcs_no_weapon_pickup=True, darkness_factor=0.5, corpse_threat_factor=0.0, damage_mercy_factor=2.0,
                               psy_phantom_factor=2.0, min_resale_pct=50, container_respawn_hours=12, energy_tolerance_factor=2.0,
                               npc_hip_accuracy_factor=2.0, device_price_factor=2.0)))
for needle in ("Backward", "Air control", "Limping", "Jog below", "regen delay", "Radiation decay", "Bleeding stops",
               "Psy recovery", "Sober-up", "Stealth kill", "Quick wheel", "Sleep fade", "dragging", "Dropped items",
               "Day starts", "Evening starts", "unaware", "Last-bullet", "difference weight", "deflection chance",
               "Deflected-hit", "Scope magnification", "Scope handling", "Upgrades: accuracy", "Upgrades: handling",
               "Upgrades: durability", "Upgrades: range", "Upgrades: damage", "Upgrades: weight", "Upgrades: breath",
               "Upgrades: armor protection", "Upgrades: armor stamina", "Weapon-out warnings", "between weapon-out",
               "Camper", "melee attackers", "special attacks", "grenade throwers", "suppressive", "pick up weapons",
               "darkness", "Bodies alarm", "mercy", "Psy phantom", "resale", "Containers refill", "Energy drink",
               "hip-fire", "Device prices"):
    assert needle in joined, needle
assert not any(k in "\n".join(summarize(S())) for k in ("Backward", "Upgrades:", "Containers"))
print("Summary: 49 lines present, neutral empty  OK")

print("\n1.27.0-TEST OK")
