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

print("\n1.28.0-TEST OK")
