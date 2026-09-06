"""1.28.0 Kern-Sweep (06.09.2026, docs/CORE_SWEEP_RESEARCH.md): ein Block je
Paket P1..P8. Sollwerte live aus vanilla/; Anker sind nur die bekannten
Vanilla-Groessen (Limp-Schwellen 25/65, Blutung 10, QuickSave 300 s ...).

P1 (Spieler: Koerper, Sicht, Speichern): Humpel-Schwellen (Array komplett),
Blutung je Treffer, Schadens-Bildschirmeffekte (15 Prozessoren), Taschenlampe
im Dialog, Schnellspeicher-Fenster (neue Textdatei), eingefaltete Schluessel
in sechs vorhandene Regler und die CoreVariablesCustom-Versicherung.
"""
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
# P1 - Spieler: Koerper, Sicht, Speichern
# =========================================================================

# --- P1.0) Dateien, Schema, Mod-Scan, Live-Werte == Defaults ---------------
assert "QuickSaveVariables.cfg" in NEEDED_FILES and "CoreVariablesCustom.cfg" in NEEDED_FILES
assert CACHE_SCHEMA >= 22, "zwei neue Dateien ohne Schema-Bump"
assert "corevarscustom" in _GD_TREES and "quicksave" in _GD_TREES, _GD_TREES
qs_live = parse_number(gd.quicksave.children["DefaultConfig"].values["QuickSaveOverwriteTime"])
assert abs(qs_live - Settings().quicksave_overwrite_min * 60.0) < 1e-9, qs_live
custom_live = gd.corevarscustom.children["CustomConfigOverride"].values
core_live = gd.corevars.children["DefaultConfig"].values
for key in COREVARS_CUSTOM_KEYS:
    assert parse_number(custom_live[key]) == parse_number(core_live[key]), key
limp_live = gd.corevars.children["DefaultConfig"].children["LimpEffectSIDToThresholdMap"].children
assert [e.values["EffectSID"] for e in limp_live.values()] == ["WeakLimp", "MediumLimp"]
print(f"P1.0 Dateien: Schema {CACHE_SCHEMA}, QuickSave live {qs_live:g} s = Default, "
      f"CustomConfigOverride wiederholt {len(COREVARS_CUSTOM_KEYS)} Schluessel identisch  OK")

# --- P1.1) Neutral erzeugt nichts ------------------------------------------
neutral = build_patches(gd, S())
assert not neutral, sorted(neutral)
print("P1.1 Neutral: keine Patch-Datei  OK")

# --- P1.2) Humpeln nach harter Landung (Array KOMPLETT) ---------------------
core = parsed(build_patches(gd, S(limp_threshold_factor=2.0)), CORE).children["DefaultConfig"]
arr = core.children["LimpEffectSIDToThresholdMap"].children
assert set(arr) == {"[0]", "[1]"}, set(arr)
assert arr["[0]"].values == {"EffectSID": "WeakLimp", "Threshold": "50.0"}, arr["[0]"].values
assert arr["[1]"].values == {"EffectSID": "MediumLimp", "Threshold": "130.0"}, arr["[1]"].values
assert not core.values, core.values                                        # sonst nichts
arr = parsed(build_patches(gd, S(no_landing_limp=True)), CORE).children["DefaultConfig"] \
    .children["LimpEffectSIDToThresholdMap"].children
assert arr["[0]"].values == {"EffectSID": "WeakLimp", "Threshold": "25000.0"}, arr["[0]"].values
assert arr["[1]"].values["Threshold"] == "65000.0"
arr = parsed(build_patches(gd, S(no_landing_limp=True, limp_threshold_factor=3.0)), CORE) \
    .children["DefaultConfig"].children["LimpEffectSIDToThresholdMap"].children
assert arr["[1]"].values["Threshold"] == "65000.0"                          # Schalter schlaegt Regler
assert CORE not in build_patches(gd, S(limp_threshold_factor=1.0))
text = build_patches(gd, S(limp_threshold_factor=2.0))[CORE]
assert "LimpEffectSIDToThresholdMap : struct.begin {bpatch}" in text and "[0] : struct.begin {bpatch}" in text
print("P1.2 Humpeln: x2 -> 50/130, Schalter -> 25000/65000, beide Eintraege komplett  OK")

# --- P1.3) Blutung je Treffer + nicht durchschlagende Treffer -------------
core = core_values(bleeding_hit_factor=0.0, bleeding_nonpen_factor=2.0)
assert core["VitalBaseBleedingValue"] == "0.0", core
assert core["BleedingChanceNonPenetrationMod"] == "2.0" == core["BleedingPointsNonPenetrationMod"], core
assert len(core) == 3, core
assert core_values(bleeding_hit_factor=2.5) == {"VitalBaseBleedingValue": "25.0"}
print("P1.3 Blutung: je Treffer x0 / x2.5, nicht durchschlagend x2 (beide Schluessel)  OK")

# --- P1.4) Schadens-Bildschirmeffekte: 15 Prozessoren, jeder einzeln --------
assert len(DAMAGE_SCREEN_PROCESSORS) == 15, DAMAGE_SCREEN_PROCESSORS
for sid in DAMAGE_SCREEN_PROCESSORS:
    node = gd.posteffects.children[sid]                                     # existiert live
    assert parse_number(node.values["Intensity"]) == 1.0, (sid, node.values)   # deklariert selbst
pfx = parsed(build_patches(gd, S(damage_screen_factor=0.5)), PFX)
assert set(pfx.children) == set(DAMAGE_SCREEN_PROCESSORS), set(pfx.children) ^ set(DAMAGE_SCREEN_PROCESSORS)
assert all(n.values == {"Intensity": "0.5"} for n in pfx.children.values())
for sid in ("GameplayGasEffectProcessor", "NVGElectroIntensityEffectProcessor",
            "LowHealthEffectProcessor", "BleedingEffectProcessor", "CrouchEffectProcessor"):
    assert sid not in pfx.children, sid
assert parsed(build_patches(gd, S(damage_screen_factor=0.0)), PFX) \
    .children["BottomLeftDamageEffectProcessor"].values["Intensity"] == "0.0"
assert PFX not in build_patches(gd, S(damage_screen_factor=1.5))            # Deckel 1.0 = Vanilla
both = parsed(build_patches(gd, S(damage_screen_factor=0.3, crouch_vignette_factor=0.0)), PFX)
assert both.children["CrouchEffectProcessor"].values["Intensity"] == "0.0" and len(both.children) == 16
print("P1.4 Bildschirmeffekte: 15 Prozessoren x0.5, 0 %, Deckel, neben der Duck-Vignette  OK")

# --- P1.5) Taschenlampe im Dialog ------------------------------------------
assert core_values(flashlight_dialog_bright=True) == {"FlashlightDialogIntensityPercent": "1.0"}
print("P1.5 Taschenlampe: 0.525 -> 1.0  OK")

# --- P1.6) Schnellspeicher-Fenster (neue Textdatei) ------------------------
p = build_patches(gd, S(quicksave_overwrite_min=0))
text = p[QS]
assert "DefaultConfig : struct.begin {bpatch}" in text and "QuickSaveOverwriteTime = 0" in text, text
assert text.count("struct.end") == 1, text
assert parsed(build_patches(gd, S(quicksave_overwrite_min=30)), QS) \
    .children["DefaultConfig"].values == {"QuickSaveOverwriteTime": "1800"}
assert QS not in build_patches(gd, S(quicksave_overwrite_min=5))            # = Vanilla 300 s
assert QS not in build_patches(gd, S(quicksave_overwrite_min=-1))
print("P1.6 Schnellspeicher: 0 min -> 0, 30 min -> 1800, 5 min = Vanilla  OK")

# --- P1.7) Einfalten in vorhandene Regler ----------------------------------
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
assert core == {"DraggingCorpseSpeedCoef": "1.0", "DeadBodyPickUpTime": "1.0"}, core   # Deckel / invers
core = core_values(corpse_drag_factor=0.5)
assert core == {"DraggingCorpseSpeedCoef": "0.3", "DeadBodyPickUpTime": "4.0"}, core
core = core_values(map_reveal_factor=2.0)
assert core == {"MarkerShowingDistance": "60000.0", "MarkerRevealingDistance": "6000.0",
                "MarkerExploringDistance": "4000.0"}, core
print("P1.7 Eingefaltet: Traglast-Drain, Lande-Ausdauer, 5 Leiter-Raten, 5 Reichweiten, "
      "Leichen-Greifzeit (invers), 3 Marker-Distanzen  OK")

# --- P1.8) Versicherung CoreVariablesCustom: genau dann, wenn einer der vier --
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
    assert all(cus[k] == core[k] for k in keys), (kw, cus, core)           # identisch mit DefaultConfig
    assert "CustomConfigOverride : struct.begin {bpatch}" in p[CUSTOM] and p[CUSTOM].count("struct.end") == 1
    assert "MediumEffectStartUI" not in cus and "bGSCEnsure" not in cus
for kw in (dict(repair_cost_factor=0.5), dict(limp_threshold_factor=2.0), dict(flashlight_dialog_bright=True),
           dict(interaction_range_factor=2.0), dict(day_length_factor=2.0)):
    p = build_patches(gd, S(**kw))
    assert CORE in p and CUSTOM not in p, kw
print("P1.8 Versicherung: erscheint genau bei den vier Schluesseln, Werte identisch  OK")

# --- P1.9) Zusammenfassung --------------------------------------------------
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
print("P1.9 Zusammenfassung: 6 Zeilen vorhanden, Schalter ersetzt den Regler, neutral leer  OK")

# =========================================================================
# P2 - Ruestung und Trefferrechnung
# =========================================================================

# --- P2.0) Live-Werte == Defaults, Neutral leer ------------------------------
arr_live = gd.corevars.children["DefaultConfig"].children["StrikeGrenadeResistCoefs"].children
assert [e.values["ProtectionStrike"] for e in arr_live.values()] == ["0.f", "1.f", "2.f", "3.f", "4.f"]
for key in ("ArmorDurabilityParamsCoef", "HelmetDurabilityParamsCoef"):
    assert abs(gd.corevar(key) - Settings().armor_wear_coef) < 1e-9, (key, gd.corevar(key))
assert abs(gd.corevar("StrikeAnomalyArmorDifferenceCoef") - 1.0) < 1e-9
assert not build_patches(gd, S(grenade_resist_factor=1.0, armor_wear_coef=0.7, anomaly_armor_difference_factor=1.0))
print("P2.0 Live: 5 Strike-Stufen, Abnutzungs-Koeffizienten = Default 0.7, Neutral leer  OK")

# --- P2.1) Granatenschutz: Array KOMPLETT, Literal f, Deckel 1.0 -------------
def resist(factor):
    core = parsed(build_patches(gd, S(grenade_resist_factor=factor)), CORE).children["DefaultConfig"]
    assert not core.values, core.values                                      # sonst nichts
    return core.children["StrikeGrenadeResistCoefs"].children

arr = resist(2.0)
assert set(arr) == {"[0]", "[1]", "[2]", "[3]", "[4]"}, set(arr)
assert arr["[0]"].values == {"ProtectionStrike": "0.f", "GrenadeDamageResist": "0.0f"}, arr["[0]"].values
assert arr["[1]"].values == {"ProtectionStrike": "1.f", "GrenadeDamageResist": "0.2f"}, arr["[1]"].values
assert arr["[2]"].values["GrenadeDamageResist"] == "0.4f" and arr["[3]"].values["GrenadeDamageResist"] == "0.8f"
assert arr["[4]"].values == {"ProtectionStrike": "4.f", "GrenadeDamageResist": "1.0f"}, arr["[4]"].values  # Deckel
arr = resist(0.0)
assert [e.values["GrenadeDamageResist"] for e in arr.values()] == ["0.0f"] * 5
arr = resist(3.0)
assert [e.values["GrenadeDamageResist"] for e in arr.values()] == ["0.0f", "0.3f", "0.6f", "1.0f", "1.0f"]
text = build_patches(gd, S(grenade_resist_factor=0.5))[CORE]
assert "StrikeGrenadeResistCoefs : struct.begin {bpatch}" in text and text.count("[") == 5, text
assert CORE not in build_patches(gd, S(grenade_resist_factor=1.0))
print("P2.1 Granatenschutz: x2 -> 0/0.2/0.4/0.8/1.0f (Deckel), x0 -> alles 0, x3 gedeckelt, Eintraege komplett  OK")

# --- P2.2) Absolutregler Abnutzung (beide Koeffizienten, Suffix f) ------------
assert core_values(armor_wear_coef=0.3) == {"ArmorDurabilityParamsCoef": "0.3f", "HelmetDurabilityParamsCoef": "0.3f"}
assert core_values(armor_wear_coef=1.0) == {"ArmorDurabilityParamsCoef": "1.0f", "HelmetDurabilityParamsCoef": "1.0f"}
assert core_values(armor_wear_coef=0.0)["HelmetDurabilityParamsCoef"] == "0.0f"
assert core_values(armor_wear_coef=1.4)["ArmorDurabilityParamsCoef"] == "1.0f"        # geklemmt
assert CORE not in build_patches(gd, S(armor_wear_coef=0.7))                           # = Vanilla live
print("P2.2 Abnutzung: 0.3 / 1.0 / 0.0 fuer Ruestung + Helm, 0.7 = Vanilla, >1 geklemmt  OK")

# --- P2.3) Ruestung gegen Anomalie-Schlag --------------------------------------
assert core_values(anomaly_armor_difference_factor=2.0) == {"StrikeAnomalyArmorDifferenceCoef": "2.0"}
assert core_values(anomaly_armor_difference_factor=0.0) == {"StrikeAnomalyArmorDifferenceCoef": "0.0"}
assert core_values(anomaly_armor_difference_factor=0.5) == {"StrikeAnomalyArmorDifferenceCoef": "0.5"}
print("P2.3 Anomalie-Schlag: x2 / x0 / x0.5, Geschwister unangetastet  OK")

# --- P2.4) Zusammenfassung ----------------------------------------------------
joined = "\n".join(summarize(S(grenade_resist_factor=0.0, armor_wear_coef=0.3, anomaly_armor_difference_factor=2.0)))
for needle in ("grenade resistance", "wear coefficient 0.3", "anomaly strike"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("grenade", "wear coefficient", "anomaly strike"))
print("P2.4 Zusammenfassung: 3 Zeilen vorhanden, neutral leer  OK")

# =========================================================================
# P3 - NPC-Verhalten im Kampf
# =========================================================================
EE = "EnemyEvaluatorPrototypes/EnemyEvaluatorPrototypes_patch_S2Tweaker.cfg"
CE = "CoverEvaluatorPrototypes/CoverEvaluatorPrototypes_patch_S2Tweaker.cfg"
BOSSES = ("BossCoverEvaluator", "StrelokCoverEvaluator", "ScarCoverEvaluator", "KorshunovCoverEvaluator")

# --- P3.0) Dateien, Schema bleibt 22, Mod-Scan, Live == Default -----------------
assert "EnemyEvaluatorPrototypes.cfg.bin" in NEEDED_FILES and "CoverEvaluatorPrototypes.cfg.bin" in NEEDED_FILES
assert CACHE_SCHEMA == 22, "Schema 22 gilt fuer das ganze 1.28.0-Release"
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
print("P3.0 Dateien: Schema 22, [0]-Evaluator + DefaultCoverEvaluator live, Absolutwerte = Default, Neutral leer  OK")

# --- P3.1) Verwundete NPCs: Absolutwerte ganzzahlig, Faktor mit f, Tabus -------
core = core_values(wounded_heal_chance=0, wounded_cooldown_s=60, wounded_regen_factor=2.0, wounded_heal_threshold=50)
assert core == {"ChanceToGetHealOverTimeWhenWounded": "0", "CooldownOnFallingWounded": "60",
                "WoundedStateHealthRegen": "10.0f", "HpThresholdToHealWound": "50"}, core
assert core_values(wounded_heal_chance=150) == {"ChanceToGetHealOverTimeWhenWounded": "100"}   # geklemmt
assert core_values(wounded_regen_factor=0.0) == {"WoundedStateHealthRegen": "0.0f"}
text = build_patches(gd, S(wounded_heal_chance=0, wounded_cooldown_s=30, wounded_heal_threshold=95))[CORE]
assert "UnkillableNPCWoundedStateResurrectionTime" not in text and "WoundHitAreasThresholds" not in text
assert CORE not in build_patches(gd, S(wounded_cooldown_s=300))
print("P3.1 Verwundete: Chance 0 / 100 (Klemme), Cooldown 60, Regen x2 = 10.0f, Schwelle 50, Tabus unberuehrt  OK")

# --- P3.2) Zielwahl: das einzige Struct [0] in {bpatch}-Form ----------------------
p = build_patches(gd, S(npc_player_focus_factor=2.0, npc_retarget_cooldown_factor=0.5, npc_damage_memory_factor=2.0))
text = p[EE]
assert text.startswith("[0] : struct.begin {bpatch}") and text.count("struct.begin") == 1, text
assert parsed(p, EE).children["[0]"].values == {"NotPlayerCoeff": "0.3", "ChangeEnemyCooldown": "1.5",
                                                "DamageAccumulationDurationSeconds": "14.0"}, text
assert parsed(build_patches(gd, S(npc_player_focus_factor=0.0)), EE).children["[0]"].values == {"NotPlayerCoeff": "0.0"}
assert EE not in build_patches(gd, S(npc_player_focus_factor=1.0))
assert "DistanceCoeff" not in text and "RangeSearchPathToEnemies" not in text          # nur die drei
print("P3.2 Zielwahl: [0] {bpatch}, NotPlayerCoeff x2 / x0, Zielwechsel x0.5, Gedaechtnis x2  OK")

# --- P3.3) Deckung: nur DefaultCoverEvaluator, Bosse fehlen, Min <= Max ------------
p = build_patches(gd, S(cover_distance_factor=0.5, cover_path_factor=2.0))
ce = parsed(p, CE)
assert list(ce.children) == ["DefaultCoverEvaluator"], list(ce.children)
for other in BOSSES + ("AttackCoverEvaluator", "ZombieCoverEvaluator", "DLC01_ZulusMateCoverEvaluator",
                       "LeaveCrossfireCoverEvaluator", "ExplosivesCoverSettings"):
    assert other not in p[CE], other
d = ce.children["DefaultCoverEvaluator"]
assert d.values == {"MaxPathLength": "4000"}, d.values                                   # ganzzahlig
assert d.children["DefaultCoverSettings"].values == {"MinDistanceToEnemy": "400.0f", "MaxDistanceToEnemy": "3500.0f"}
assert "DefaultCoverEvaluator : struct.begin {bpatch}" in p[CE] and "DefaultCoverSettings : struct.begin {bpatch}" in p[CE]
d = parsed(build_patches(gd, S(cover_distance_factor=2.0)), CE).children["DefaultCoverEvaluator"]
v = d.children["DefaultCoverSettings"].values
assert parse_number(v["MinDistanceToEnemy"]) <= parse_number(v["MaxDistanceToEnemy"]) and v["MaxDistanceToEnemy"] == "14000.0f"
assert "MaxPathLength" not in d.values
assert CE not in build_patches(gd, S(cover_distance_factor=1.0, cover_path_factor=1.0))
print("P3.3 Deckung: nur DefaultCoverEvaluator, Bosse/Sonderkinder fehlen, 400/3500f + Pfad 4000, Min <= Max  OK")

# --- P3.4) Zusammenfassung -----------------------------------------------------
joined = "\n".join(summarize(S(wounded_heal_chance=0, wounded_cooldown_s=60, wounded_regen_factor=2.0,
                               wounded_heal_threshold=50, npc_player_focus_factor=2.0,
                               npc_retarget_cooldown_factor=0.5, npc_damage_memory_factor=2.0,
                               cover_distance_factor=0.5, cover_path_factor=2.0)))
for needle in ("Wounded NPCs recover 0 %", "cooldown 60 s", "Wounded NPC health regen", "heal threshold 50",
               "focus on the player", "target-switch", "damage memory", "cover distance", "cover search path"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("Wounded", "focus on the player", "cover"))
print("P3.4 Zusammenfassung: 9 Zeilen vorhanden, neutral leer  OK")

# =========================================================================
# P4 - Mutanten
# =========================================================================
from s2tweaker.tweaks import FLAIR_SENSOR_SKIP, FLAIR_SENSOR_KEYS   # noqa: E402
FL = "AIPrototypes/FlairSensorPrototypes/FlairSensorPrototypes_patch_S2Tweaker.cfg"
TARGET = ["BlindDogFlairSensor", "ChimeraFlairSensor", "FleshFlairSensor", "PoltergeistFlairSensor"]

# --- P4.0) Datei, Schema 22, Mod-Scan, Sensorliste live: 6 aktive, 2 Tabu ---------
assert "AIPrototypes/FlairSensorPrototypes.cfg.bin" in NEEDED_FILES and CACHE_SCHEMA == 22
assert "flairsensors" in _GD_TREES
active = sorted(sid for sid, n in gd.flairsensors.children.items()
                if n.values.get("IsActive", "").strip() == "true")
assert active == sorted(TARGET + ["PsyNPCFlairSensor", "PoltergeistFlairSensorYanivToxicRozliv"]), active
assert len(active) == 6 and len(FLAIR_SENSOR_SKIP & set(active)) == 2
assert all("FrontSensingRadius" in gd.flairsensors.children[s].values for s in ("BlindDogFlairSensor", "ChimeraFlairSensor", "FleshFlairSensor"))
assert "FrontSensingRadius" not in gd.flairsensors.children["PoltergeistFlairSensor"].values
assert gd.corevars.children["DefaultConfig"].values["UseMutantLootWithoutWidget"].strip() == "true"
assert not build_patches(gd, S(mutant_smell_factor=1.0, burer_fire_interval_factor=1.0))
print("P4.0 Witterung: 6 aktive Sensoren live, 2 davon Tabu, Front* nur bei 3, Widget-Flag true, Neutral leer  OK")

# --- P4.1) Geruch x0.5: vier Sensoren, nur vorhandene Schluessel, Suffix f ---------
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
print("P4.1 Geruch x0.5: BlindDog 2000/55/2000/200f, Poltergeist ohne Front*, Tabu-Sensoren fehlen  OK")

# --- P4.2) Schalter: IsActive = false auf genau den vier erlaubten -------------------
fl = parsed(build_patches(gd, S(mutants_no_smell=True)), FL)
assert sorted(fl.children) == TARGET and all(n.values == {"IsActive": "false"} for n in fl.children.values())
both = parsed(build_patches(gd, S(mutants_no_smell=True, mutant_smell_factor=2.0)), FL)
assert both.children["FleshFlairSensor"].values["IsActive"] == "false" and both.children["FleshFlairSensor"].values["SensingRadius"] == "4000.0f"
print("P4.2 Schalter: genau die vier erlaubten Sensoren auf IsActive = false  OK")

# --- P4.3) Burer-Waffenfeuer: zehn benannte Unter-Structs ----------------------------
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
print("P4.3 Burer: 10 Munitionsarten x2 (1 -> 2.0, 4 -> 8.0), x0.5 (0.5 -> 0.25)  OK")

# --- P4.4) Ausweiden mit Loot-Fenster ----------------------------------------------------
assert core_values(mutant_loot_widget=True) == {"UseMutantLootWithoutWidget": "false"}
print("P4.4 Ausweiden: UseMutantLootWithoutWidget true -> false  OK")

# --- P4.5) Zusammenfassung ----------------------------------------------------------------
joined = "\n".join(summarize(S(mutant_smell_factor=0.5, mutants_no_smell=True, burer_fire_interval_factor=2.0,
                               mutant_loot_widget=True)))
for needle in ("sense of smell", "cannot smell", "Burer weapon fire", "loot window"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("smell", "Burer", "loot window"))
print("P4.5 Zusammenfassung: 4 Zeilen vorhanden, neutral leer  OK")

# =========================================================================
# P5 - A-Life und Leichen
# =========================================================================
NEEDS = "NPCNeedsPresetPrototypes/NPCNeedsPresetPrototypes_patch_S2Tweaker.cfg"
POL = "ALifePrototypes/ALifePolicyPrototypes/ALifePolicyPrototypes_patch_S2Tweaker.cfg"
FAC = ("ALifePrototypes/ALifePopulationManagerFactionPrototypes/"
       "ALifePopulationManagerFactionPrototypes_patch_S2Tweaker.cfg")

# --- P5.0) Dateien, Schema 22, Mod-Scan, Live == Default, Neutral leer -------------
for name in ("NPCNeedsPresetPrototypes.cfg.bin", "ALifePrototypes/ALifePolicyPrototypes.cfg.bin",
             "ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg.bin"):
    assert name in NEEDED_FILES, name
assert CACHE_SCHEMA == 22 and all(t in _GD_TREES for t in ("needspresets", "alifepolicy", "alifefactions"))
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
print("P5.0 Dateien: drei neue, Schema 22, 16 Expansion-Eintraege live (MutantGeneric unter [1]), 29 Fraktionen, Neutral leer  OK")

# --- P5.1) Trupp-Ausbreitung: 16 Presets, Eintrag komplett, Sonderwerte ------------
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
print("P5.1 Ausbreitung: 16 Presets x2 (6/10 -> 12/20, Zombie 2/6, MutantGeneric [1] 14/22), Eintraege komplett  OK")

# --- P5.2) A-Life-Policy: Cooldowns, Distanzband (Min <= Max, ganzzahlig), Budget --
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
print("P5.2 Policy: Cooldowns x0.5 = 180/60f, Distanz x2 = 40000/50000, x0.5 = 10000/12500, Budget 60/5, Extinction tabu  OK")

# --- P5.3) Fraktions-Ausbreitung: 29 Kinder, Lagerbaender tabu, Tempo invers ------
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
print("P5.3 Fraktionen: 29 x Kampfchance 80 / 0, Tempo x2 -> 25.0f (invers), Lagerbaender fehlen  OK")

# --- P5.4) Leichen-Distanzen (Quadrat-Regel), eingefaltete Zeiten, Hardcap --------
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
assert text.count("struct.begin") == 1                                            # nur DefaultConfig
print("P5.4 Leichen: Distanz x2 -> x4 auf die Quadrate + 60000, x0.5 -> x0.25, Zeiten falten 6.0/1.0, Hardcap 3000  OK")

# --- P5.5) Zusammenfassung ---------------------------------------------------------
joined = "\n".join(summarize(S(squad_expansion_factor=2.0, refill_cooldown_factor=0.5, refill_distance_factor=2.0,
                               corpse_budget=60, faction_battle_chance=80, faction_expansion_pace_factor=2.0,
                               corpse_distance_factor=2.0, alife_corpse_hardcap=3000)))
for needle in ("squad expansion", "refill cooldown", "refill distance", "corpse budget 60", "battle chance 80",
               "expansion pace", "Corpse distance", "hard cap 3000"):
    assert needle in joined, (needle, joined)
assert not any(k in "\n".join(summarize(S())) for k in ("squad expansion", "refill", "corpse budget", "hard cap"))
print("P5.5 Zusammenfassung: 8 Zeilen vorhanden, neutral leer  OK")

print("\n1.28.0-TEST OK")
