"""Tweak-Engine: erzeugt aus den Einstellungen die Patch-cfg-Dateien.

Jede Funktion baut fuer ein Feature die {bpatch}-Structs auf Basis der
Vanilla-Werte (GameData der installierten Spielversion). build_patches()
liefert {Pfad relativ zu .../GameData/: cfg-Text}.

Konventionen (siehe docs/SPEC.md):
- Patch-Dateien heissen <BasisCfg>/<BasisCfg>_patch_<Mod>.cfg
- CoreVariables.cfg ist unbinarisiert -> offizielle Benennung
  CoreVariables.cfg_patch_<Mod>.cfg direkt in GameData/ (feld-erprobt).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import re

from . import loot_extensions, repair_extensions, world_extensions, extension_controls, armor_extensions
from .cfgparse import parse_number
from .emit import emit_patch, fmt_float
from .gamedata import CATEGORY_TEMPLATES, GameData

ALL_CATEGORIES = {
    "weapon", "armor", "ammo", "artifact", "attach",
    "consumable", "grenade", "misc",
}

CATEGORY_LABELS = {  # GUI (englisch)
    "weapon": "Weapons",
    "armor": "Armor & helmets",
    "ammo": "Ammo",
    "artifact": "Artifacts",
    "attach": "Attachments",
    "consumable": "Consumables",
    "grenade": "Grenades",
    "misc": "Misc (detectors etc.)",
}

VANILLA_MAX_CARRY = 80.0
VANILLA_PENALTY_START = 50.0

# Einzeln regelbare Ausdauer-Aktionen: (Settings-Feld, cfg-Schluessel)
STAMINA_ACTIONS = [
    ("stamina_sprint", "Sprint"),
    ("stamina_jump", "Jump"),
    ("stamina_melee_light", "MeleeNormal"),
    ("stamina_melee_strong", "MeleeStrong"),
    ("stamina_buttstock", "MeleeButstock"),
    ("stamina_vault", "Vault"),
]

# Kontinuierlicher Drain (CoreVariables StaminaRegenStateCoefs), der vom
# Sprint-Regler mitskaliert wird
SPRINT_DRAIN_TAGS = {
    "EStateTag::Sprint",
    "EStateTag::SprintUnderRunSpeed",
    "EStateTag::Run",
}

# --- 1.28.0 Kern-Sweep P1 (docs/CORE_SWEEP_RESEARCH.md par. 1.1 / 3b) -------
# Schadens-Bildschirmeffekte in PostEffectProcessorPrototypes: der rote
# Richtungs-Blitz (8 Richtungen) plus Verbrennung, Dampf, Strom, Chemie,
# Dunkelheit (Staerke + Radius) und Quecksilber. Jedes Kind deklariert
# Intensity selbst -> jeden Prozessor einzeln patchen, nie nur die Basis.
# Die SIDs kommen live aus der Datei, das Muster prueft nur den Namen;
# GameplayGas/NVG*/LowHealth/Bleeding bleiben bewusst draussen.
DAMAGE_SCREEN_RE = re.compile(
    r"^(?:(?:Top|Right|Bottom|Left|TopRight|TopLeft|BottomRight|BottomLeft"
    r"|Burn|Steam|Chemical)Damage|ElectroIntensity"
    r"|DarknessDamage(?:Intensity|Radius)|QuicksilverDamageIntensity)"
    r"EffectProcessor$")
# Erwartete Vanilla-Liste (2.0.3) - Anker fuer die Tests, nicht fuer den Bau
DAMAGE_SCREEN_PROCESSORS = (
    "TopDamageEffectProcessor", "RightDamageEffectProcessor",
    "BottomDamageEffectProcessor", "LeftDamageEffectProcessor",
    "TopRightDamageEffectProcessor", "TopLeftDamageEffectProcessor",
    "BottomRightDamageEffectProcessor", "BottomLeftDamageEffectProcessor",
    "BurnDamageEffectProcessor", "SteamDamageEffectProcessor",
    "ElectroIntensityEffectProcessor", "ChemicalDamageEffectProcessor",
    "DarknessDamageIntensityEffectProcessor", "DarknessDamageRadiusEffectProcessor",
    "QuicksilverDamageIntensityEffectProcessor",
)
# CoreVariablesCustom.cfg (CustomConfigOverride) wiederholt diese vier
# DefaultConfig-Schluessel (dazu bStartWithMenu und Debug-Kram - tabu).
# Ob der Override NACH DefaultConfig greift, ist aus den Daten nicht zu
# entscheiden -> jeder Patch dieser Schluessel wird dorthin gespiegelt.
COREVARS_CUSTOM_KEYS = ("InventoryPenaltyLessWeight", "InventorySPOverweightDrainCoef",
                        "InventorySPDrainCoef", "StaminaFallingDamageCoef")
# 1.28.0 P4: Witterung (FlairSensorPrototypes, par. 2.4). Tabu-Liste: Boss
# (ohnehin inaktiv), PsyNPC (kein Objekt nutzt ihn) und die Quest-Variante
# Yaniv - die werden nie angefasst, auch nicht vom Schalter.
FLAIR_SENSOR_SKIP = {"BossFlairSensor", "PsyNPCFlairSensor",
                     "PoltergeistFlairSensorYanivToxicRozliv"}
FLAIR_SENSOR_KEYS = ("SensingRadius", "FrontSensingRadius",
                     "DetectionSpeed", "FrontDetectionSpeed")
# 1.28.0 P6: Strahlungsfelder (CoreVariables RadiationPresetValues, par. 1.2).
# NUR diese vier Presets - Deadly und RadBlock sind die Karten-Todeszonen
# (9000 Schaden, Tabu-Liste), Custom hat genau ein Weltvorkommen.
RADIATION_PRESETS_OK = ("ERadiationPreset::Light", "ERadiationPreset::Medium",
                        "ERadiationPreset::Strong", "ERadiationPreset::Topaz")
# 1.28.0 P6: Lagerleben (NPCNeedsPresetPrototypes Needs, par. 2.6). Emission
# (auf 100 festgenagelt), Patrolling, Work, Guard, Monolog, RunOnTalking,
# Idle, PDA, Detector und WeaponCleaning bleiben vanilla.
CAMP_LIFE_NEEDS = ("EContextualActionNeeds::Guitar", "EContextualActionNeeds::Anecdote",
                   "EContextualActionNeeds::Dialog", "EContextualActionNeeds::Smoke",
                   "EContextualActionNeeds::Sleep", "EContextualActionNeeds::Eat",
                   "EContextualActionNeeds::Rest", "EContextualActionNeeds::Drink")
# 1.28.0 P6: Himmel (SingletonConstants TimeManager, par. 2.8) - (Feld, Schluessel,
# Deckel). Latitude/Longitude/TimeZone/NorthOffsetAngle/Start* sind tabu.
SKY_KEYS = (("moon_brightness_factor", "MoonLightMaxBrightness", None),
            ("sun_brightness_factor", "SunLightMaxBrightness", None),
            ("stars_brightness_factor", "StarsBrightness", None),
            ("cloud_opacity_factor", "CloudOpacity", 1.0),
            ("cloud_speed_factor", "CloudSpeed", None),
            ("dusk_length_factor", "LightSourceFadingDurationHoursOnDayNightChange", None))

# --- Waffen-Drei-Ebenen-System: Einzelwaffe > Kategorie > global ---------
WEAPON_PARAMS = ["damage", "spread", "recoil", "durability", "firerate",
                 "range", "bleeding", "adsspeed", "aimtime", "magazine"]

# --- Kaliberwechsel (GitHub Issue #6) -----------------------------------
# KEIN Kaskaden-Parameter: ein Kaliber ist ein Name, kein Faktor — es
# stapelt nicht und gilt nur pro Waffe. Die Beschriftungen kommen aus
# AMMO_CALIBER_LABELS weiter unten (die Tabelle gab es schon fuer den
# Munitions-Baum) — keine zweite Liste danebenstellen.
#
# Es wird NICHTS gesperrt (ausdruecklicher Wunsch des Besitzers): jedes
# Kaliber, das im Spiel wirklich an einer Waffe haengt, steht im Dropdown.
# Stattdessen wird ehrlich drangeschrieben, was kaputtgeht. Nicht dabei ist
# nur, was gar nicht in den Waffendaten steht — 7,62x39 zum Beispiel: die
# Munition existiert, aber keine Waffe benutzt sie und sie liegt in null
# Loot-Generatoren. Das faellt von selbst raus, weil die Tabelle aus den
# Waffendaten kommt statt aus einer Liste im Code.
CALIBERS_ODD = {"AGA", "APG7V", "AVOG", "AHEDP"}   # Gauss, Werfer


def swappable_calibers(gd: GameData) -> dict[str, dict[str, str]]:
    """{Kaliber: {Sorte: Projektil}} — alles, was eine Waffe benutzt."""
    return gd.ammo_caliber_projectiles()


def caliber_label(caliber: str) -> str:
    return AMMO_CALIBER_LABELS.get(caliber, caliber)


def caliber_warning(gd: GameData, current: str | None,
                    wanted: str | None) -> str:
    """Ehrlicher Hinweis zu genau diesem Wechsel — oder "".

    Rechnet den Schadenseffekt aus den echten Munitionswerten vor, statt
    ihn zu behaupten: der Schaden steht an der Waffe (BaseDamage), die
    Munition liefert nur einen Multiplikator. Ueber alle Gewehr- und
    Pistolenkaliber ist der 1.0, also aendert ein Wechsel dort NICHTS.
    Schrot steht bei 0.084 — und die Flinte gleicht das mit BaseDamage
    50.0 statt 9.5 aus. Wer eine Flinte auf 5.45 stellt, bekommt also
    50 Schaden pro Schuss; wer ein Gewehr auf Schrot stellt, 0,8."""
    if not wanted or not current or wanted == current:
        return ""
    mods = gd.caliber_damage_mods()
    old, new = mods.get(current), mods.get(wanted)
    if old and new and abs(new - old) > 1e-9:
        # new/old, nicht old/new: der Multiplikator der NEUEN Patrone
        # ersetzt den der alten, die BaseDamage der Waffe bleibt stehen.
        factor = new / old
        if factor >= 2:
            return (f"Warning: this weapon will do roughly {factor:.0f}x its "
                    "current damage per shot. Its damage value is balanced "
                    f"against {caliber_label(current)}, whose rounds are "
                    "scored per pellet; a single bullet is not. Broken, "
                    "not a bug - and yours to keep if you want it.")
        if factor <= 0.5:
            return (f"Warning: this weapon will do roughly "
                    f"{factor * 100:.0f} % of its current damage per shot. "
                    f"{caliber_label(wanted)} is scored per pellet, and only "
                    "shotguns carry the high damage value that makes up for "
                    "it. Broken, not a bug - and yours to keep if you want "
                    "it.")
    if wanted in CALIBERS_ODD or current in CALIBERS_ODD:
        return ("Warning: gauss and launcher ammunition is not normal "
                "weapon ammunition. Nobody has tested what a rifle does "
                "with it - expect it to simply not work.")
    return ""

WEAPON_PARAM_LABELS = {  # GUI (englisch)
    "damage": "Damage",
    "spread": "Spread",
    "recoil": "Recoil",
    "durability": "Durability",
    "firerate": "Fire rate",
    "range": "Effective range",
    "bleeding": "Bleeding",
    "adsspeed": "ADS move speed",
    "aimtime": "ADS aim-in speed",
    "magazine": "Magazine size",
}

# Die vier Ziel-Zeiten skalieren ZUSAMMEN (rein, seitlich, gelehnt, wieder
# raus) — ein Snappiness-Gefuehl, wie bei den vier Range-Schluesseln.
WEAPON_AIMTIME_KEYS = ("AimingTime", "OffsetAimingTime", "LeanAimingTime",
                       "LeanAimingRestoreTime")

# CWS-Schluessel, die der Range-Faktor gemeinsam skaliert
WEAPON_RANGE_KEYS = ("EffectiveFireDistanceMin", "EffectiveFireDistanceMax",
                     "FireDistanceDropOff", "DistanceDropOffLength")

# Welche CWS-Schluessel ein Kaskaden-Parameter braucht. _weapon_settings_patch
# patcht nur Werte > 0 — fehlt der Wert, kann dieser Parameter fuer diese
# Waffe NIE einen Patch erzeugen, und ein Regler dafuer waere ein
# Blindgaenger (der Ammo- und der Ruestungsbaum blenden solche Regler
# laengst aus). Nicht aufgefuehrte Parameter (recoil, firerate, magazine,
# adsspeed, aimtime) stehen in WeaponGeneralSetup und existieren dort fuer
# jede Waffe.
WEAPON_PARAM_CWS_KEYS: dict[str, tuple[str, ...]] = {
    "damage": ("BaseDamage",),
    "spread": ("DispersionRadius",),
    "durability": ("DurabilityDamagePerShot",),
    "bleeding": ("BaseBleeding", "ChanceBleedingPerShot"),
    "range": WEAPON_RANGE_KEYS,
}


def weapon_available_params(gd: GameData, cws: str | None) -> list[str]:
    """WEAPON_PARAMS ohne die, die dieses CWS-Struct nachweislich nicht hat.

    Nachweislich heisst: der Struct existiert und ALLE Schluessel des
    Parameters loesen sich zu <= 0 auf. Ohne Struct (oder ohne bekanntes
    CWS-Struct) wird nichts gefiltert — dann laesst sich nichts beweisen.
    Beispiel aus den echten Spieldaten: die beiden Unterlauf-Granatwerfer
    und der Buckshot-Launcher haben keinen DurabilityDamagePerShot, ihre
    Waffen nutzen sich also gar nicht ab."""
    if cws is None or cws not in gd.weaponsettings.children:
        return list(WEAPON_PARAMS)
    return [
        param for param in WEAPON_PARAMS
        if param not in WEAPON_PARAM_CWS_KEYS
        or any(parse_number(gd.resolve(gd.weaponsettings, cws, key)) > 0
               for key in WEAPON_PARAM_CWS_KEYS[param])
    ]

WEAPON_CATEGORY_LABELS = {  # Reihenfolge = GUI-Reihenfolge
    "pistol": "Pistols",
    "smg": "SMGs",
    "rifle": "Assault rifles",
    "shotgun": "Shotguns",
    "dmr": "Marksman rifles (DMR)",
    "sniper": "Sniper rifles",
    "mg": "Machine guns",
    "launcher": "Grenade launchers",
}

# --- Munitions-Zwei-Ebenen-System: Einzelsorte > globaler Regler ---------
# ⚠ Reihenfolge NICHT aendern und Neues nur ANHAENGEN: sie bestimmt die
# Zeilenfolge im Patch und damit die Byte-Gleichheit zu aelteren Paks.
AMMO_PARAMS = ["damage", "piercing", "armordamage", "cover", "stack",
               "bleeding", "recoil", "flatness", "wear",
               # 1.33.0 ans ENDE angehaengt (Byte-Gleichheit alter Paks)
               "dispersion", "aimdispersion"]

AMMO_PARAM_LABELS = {  # GUI (englisch)
    "damage": "Damage",
    "piercing": "Armor piercing",
    "armordamage": "Armor damage",
    "cover": "Cover penetration",
    "stack": "Stack size",
    "bleeding": "Bleeding",
    "recoil": "Recoil",
    "flatness": "Trajectory flatness",
    "wear": "Weapon wear",
    "dispersion": "Spread",
    "aimdispersion": "Spread while aiming",
}

# Regler-Schluessel -> cfg-Schluessel in ItemPrototypes (= AMMO_MOD_KEYS).
# Reihenfolge NICHT aendern: sie bestimmt die Reihenfolge der Zeilen im
# erzeugten Patch und damit die Byte-Gleichheit zu bisherigen Paks.
AMMO_PARAM_KEYS = {
    "damage": "DamageMod",
    "piercing": "ArmorPiercingMod",
    "armordamage": "ArmorDamageMod",
    "cover": "CoverPiercingMod",
    "stack": "MaxStackCount",
    "bleeding": "BleedingMod",
    "recoil": "RecoilMod",
    "flatness": "FlatnessMod",
    "wear": "WeaponExhaustionMod",
    "dispersion": "DispersionMod",
    "aimdispersion": "AimDispersionMod",
}

# Reihenfolge = Sortierung der Sorten INNERHALB eines Kalibers
AMMO_TYPE_LABELS = {
    "Default": "Standard",
    "ArmorPiercing": "Armor-piercing",
    "Expanding": "Expanding",
    "Supersonic": "Supersonic",
}

# Schluessel = Enum-Schwanz von Caliber, Reihenfolge = GUI-Reihenfolge.
# NACHSCHLAGEWERK, KEIN FILTER: unbekannte Kaliber (kuenftige Spiel-Patches)
# erscheinen im Baum mit dem rohen Schwanz als Beschriftung.
AMMO_CALIBER_LABELS = {
    "A918": "9×18 mm Makarov",
    "A919": "9×19 mm Parabellum",
    "A045": ".45 ACP",
    "A939": "9×39 mm",
    "A545": "5.45×39 mm",
    "A556": "5.56×45 mm NATO",
    "A762": "7.62×39 mm",
    "A762NATO": "7.62×51 mm NATO",
    "A762Sniper": "7.62×54 mmR",
    "A012": "12 gauge",
    "AGA": "Gauss rounds",
    "AVOG": "VOG-25 grenades",
    "AHEDP": "40 mm HEDP grenades",
    "APG7V": "PG-7V rockets",
}

# Endbuchstabe einer Munitions-SID -> Sorte. A545A = 5.45 armor-piercing.
AMMO_SID_TYPE_SUFFIX = {
    "A": "ArmorPiercing",
    "D": "Default",
    "E": "Expanding",
    "S": "Supersonic",
}


def ammo_label(sid: str) -> str:
    """'A545A' -> '5.45×39 mm armor-piercing'.

    Nur aus der SID abgeleitet, weil summarize() keine GameData hat. Reihen-
    folge wichtig: AGA/AHEDP/APG7V/AVOG sind KOMPLETTE Kaliber-Schluessel und
    muessen VOR dem Abtrennen des Endbuchstabens erkannt werden (sonst wuerde
    'AGA' als 'AG' + 'A' gelesen). Unbekanntes bleibt die rohe SID.
    """
    if sid in AMMO_CALIBER_LABELS:
        return AMMO_CALIBER_LABELS[sid]
    stem, suffix = sid[:-1], sid[-1:]
    if stem in AMMO_CALIBER_LABELS and suffix in AMMO_SID_TYPE_SUFFIX:
        kind = AMMO_TYPE_LABELS[AMMO_SID_TYPE_SUFFIX[suffix]]
        return f"{AMMO_CALIBER_LABELS[stem]} {kind.lower()}"
    return sid


# Ruestungs-Overrides: Reihenfolge = Regler-Reihenfolge im Baum.
ARMOR_PARAMS = ["strike", "burn", "shock", "chemical", "radiation", "psy"]
ARMOR_PARAM_KEYS = {
    "strike": "Strike", "burn": "Burn", "shock": "Shock",
    "chemical": "ChemicalBurn", "radiation": "Radiation", "psy": "PSY",
}
ARMOR_PARAM_LABELS = {
    "strike": "Physical (bullets & melee)", "burn": "Burn (fire)",
    "shock": "Shock (electric)", "chemical": "Chemical",
    "radiation": "Radiation", "psy": "PSY",
}

# Fraktions-Namen fuer lesbare Ruestungs-Labels (SID-Token -> Anzeige).
ARMOR_FACTION_LABELS = {
    "Dolg": "Duty", "Svoboda": "Freedom", "Neutral": "Loners",
    "Bandit": "Bandits", "Military": "Military", "Monolith": "Monolith",
    "Mercenaries": "Mercenaries", "Scientific": "Scientists",
    "Spark": "Spark", "Varta": "Varta", "Duty": "Duty",
}

_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z0-9])")


def armor_label(sid: str) -> str:
    """'SEVA_Neutral_Armor' -> 'SEVA Suit' (verifizierter Anzeigename aus
    names.py); ohne Alias -> 'Exoskeleton_Dolg_Armor' -> 'Exoskeleton
    (Duty)' aus der SID abgeleitet (summarize() hat keine GameData).
    Muster der Spieldaten: <Modell>_<Fraktion>_Armor|Helmet[_Zusatz...].
    Was nicht passt (z.B. supack_vozmercform), bleibt die rohe SID --
    lieber ehrlich technisch als falsch geraten."""
    from .names import ARMOR_ALIASES
    alias = ARMOR_ALIASES.get(sid)
    if alias:
        return alias
    parts = sid.split("_")
    for kind_token, kind_text in (("Armor", ""), ("Helmet", " helmet")):
        if kind_token not in parts:
            continue
        idx = parts.index(kind_token)
        if idx < 2:
            break
        # Fraktion = das RECHTESTE bekannte Fraktions-Token vor Armor/Helmet
        # (nicht stur Position idx-1: Battle_Dolg_End_Armor traegt seine
        # Variante HINTER der Fraktion).
        fac_idx = idx - 1
        for j in range(idx - 1, 0, -1):
            if parts[j] in ARMOR_FACTION_LABELS:
                fac_idx = j
                break
        model = _CAMEL_SPLIT.sub(" ", "_".join(parts[:fac_idx]))
        faction = ARMOR_FACTION_LABELS.get(parts[fac_idx], parts[fac_idx])
        label = f"{model}{kind_text} ({faction})"
        trailing = parts[fac_idx + 1:idx] + parts[idx + 1:]
        if trailing:
            label += " – " + " ".join(trailing)
        return label
    return sid


# "Improved vaulting": die 14 Werte, die die (seit Patch 2.0 kaputte)
# Vault-Mod gegenueber Vanilla aenderte — rekonstruiert aus GitHub Issue #2
# (BigTinz hat den kompletten Block der alten Mod gepostet; der Diff gegen
# die echten Vanilla-Daten ergab genau diese 14 Schluessel). Bewusst
# ABSOLUTE Zielwerte statt Faktoren: die Trace-Parameter haengen zusammen
# und die Mod war ein abgestimmtes Set. Gepatcht wird NUR der Player —
# NPCs und Mutanten haben eigene VaultingParams-Bloecke und bleiben vanilla.
# Emittiert wird je Schluessel nur, was vom LIVE gelesenen Vanilla abweicht.
VAULT_PRESET = {
    "MaxAngle": "115",              # Vanilla 75: steilere Anlaufwinkel
    "MaxTestDistance": "115",       # Vanilla 15: aus groesserem Abstand
    "StartDistance": "20",          # Vanilla 10
    "VaultOverMaxDepth": "25",      # Vanilla 50
    "VaultOverLandOffset": "100",   # Vanilla 20
    "MinObstacleHeight": "85",      # Vanilla 70
    "MaxObstacleHeight": "200",     # Vanilla 130: hoehere Hindernisse
    "FrontSearchRadiusModifier": "1",       # Vanilla 0.5
    "DepthTraceRadiusModifier": "0.8",      # Vanilla 0.5
    "LandingMinHeight": "10",       # Vanilla 30
    "MaxWindowDetectionIterations": "20",   # Vanilla 10
    "MaxLandingDetectionIterations": "15",  # Vanilla 5
    "MaxLandingOffset": "300",      # Vanilla 50
    "LandingMaxSlope": "90",        # Vanilla 45
}

# Gangarten getrennt regelbar: Animation/Schrittsound skalieren NICHT mit
# (Engine-Assets, per cfg unerreichbar) -- getrennte Regler halten den
# sichtbaren Versatz klein (Referenz: Nexus-Mod 2314 laesst Walk unangetastet).
WALK_SPEED_KEYS = ["WalkSpeed", "CrouchSpeed", "LowCrouchSpeed"]
RUN_SPEED_KEYS = ["RunSpeed", "JoggingSpeed", "SprintSpeed"]


@dataclass
class Settings:
    mod_name: str = "S2Tweaker"

    # --- Player ---
    max_hp: float = 100.0                    # Vanilla 100
    hp_regen: float = 0.0                    # HP/s, Vanilla 0
    max_stamina: float = 100.0               # Vanilla 100
    stamina_regen: float = 5.0               # SP/s, Vanilla 5
    fall_damage_pct: float = 100.0           # 100 = Vanilla, 0 = kein Fallschaden
    walk_speed_factor: float = 1.0           # Gehen + Schleichen
    run_speed_factor: float = 1.0            # Laufen + Sprinten
    jump_height_factor: float = 1.0
    vault_height_factor: float = 1.0         # MaxObstacleHeight x Faktor
    vault_distance_factor: float = 1.0       # MaxTestDistance+StartDistance
    vault_angle_factor: float = 1.0          # MaxAngle (Deckel 180 Grad)
    vault_min_height_factor: float = 1.0     # MinObstacleHeight
    vault_landing_factor: float = 1.0        # Lande-Toleranz (3 Schluessel)
    vault_over_depth_factor: float = 1.0     # VaultOverMaxDepth
    vault_over_offset_factor: float = 1.0    # VaultOverLandOffset
    vault_sprint: bool = False               # StartWithSprintPressed
    improved_vaulting: bool = False          # Preset der alten Vault-Mod          # JumpSpeedCoef

    # --- Ausdauer-Kosten einzeln (Faktor, 1.0 = Vanilla) ---
    stamina_sprint: float = 1.0
    stamina_jump: float = 1.0
    stamina_melee_light: float = 1.0
    stamina_melee_strong: float = 1.0
    stamina_buttstock: float = 1.0
    stamina_vault: float = 1.0

    # --- Gewicht & Inventar ---
    max_carry_weight: float = VANILLA_MAX_CARRY
    penalty_start_weight: float = VANILLA_PENALTY_START
    no_overweight_penalty: bool = False
    item_weight_factor: float = 1.0
    item_weight_categories: set[str] = field(default_factory=lambda: set(ALL_CATEGORIES))
    ignore_equipped_weight: bool = False

    # --- Kampf ---
    player_damage_factor: float = 1.0
    headshot_factor: float = 1.0
    aim_punch_factor: float = 1.0        # Kamera-Wackeln bei Treffern (0-3)
    npc_damage_factor: float = 1.0
    npc_hp_factor: float = 1.0
    # --- NPCs & KI ---
    npc_accuracy_factor: float = 1.0     # >1 = praeziser (Dispersion kleiner)
    # --- NPC-Kampfverhalten (WeaponAttributes *_NPC.AIParameters; Vorbild
    # Nexus 2396 'Grounded Combat' + 129 'Better Gunfights') ---
    npc_free_shots_factor: float = 1.0    # IgnoreDispersionMin/MaxShots ('Aimbot'-Schuesse)
    npc_burst_factor: float = 1.0         # MinShots/MaxShots je Feuerstoss
    npc_fire_pause_factor: float = 1.0    # Pausen zwischen Feuerstoessen/Einzelschuessen
    npc_engage_range_factor: float = 1.0  # CombatEffectiveFireDistanceMin/Max
    npc_weapon_range_factor: float = 1.0  # CWS *_NPC Distanz-Schluessel
    npc_regen_factor: float = 1.0         # RegenHP der menschlichen NPCs
    # --- Stealth (AIGlobals Pose/Wetter/Taschenlampe + Player.StealthParams) ---
    crouch_stealth_factor: float = 1.0    # >1 = geduckt schwerer zu sehen/hoeren
    movement_noise_factor: float = 1.0    # Laerm von Gehen/Rennen/Sprinten
    weather_stealth_factor: float = 1.0   # Wetter-Abschlaege auf Sicht/Gehoer
    flashlight_stealth_factor: float = 1.0  # wie stark deine Lampe dich verraet
    # --- NPC-Wachsamkeit/Mut (ThreatPrototypes, AIGlobals CombatTactics) ---
    npc_alertness_factor: float = 1.0     # Reaktionsschwellen / Faktor
    npc_search_time_factor: float = 1.0   # Verdachts-Gedaechtnis x Faktor
    npc_courage_factor: float = 1.0       # Angriffs-/Rueckzugsschwellen / Faktor
    npc_stagger_factor: float = 1.0       # CriticalDamageThreshold x Faktor
    npc_attack_cooldown_factor: float = 1.0   # Difficulty NPC_AttackCooldown
    mutant_attack_cooldown_factor: float = 1.0  # Difficulty Mutant_AttackCooldown
    npc_weapon_rank_add: float = 0.0      # Difficulty NPC_Weapon_Rank_Add (+0..3)
    npc_vision_factor: float = 1.0       # Sichtweite (Story-Bosse ausgenommen)
    npc_hearing_factor: float = 1.0      # Hoerweite (Mutanten ausgenommen)
    npc_reaction_factor: float = 1.0     # >1 = NPCs melden Bedrohungen spaeter
    npc_grenade_factor: float = 1.0      # 0 = nie werfen (-1-Bosse bleiben)
    npc_no_heal: bool = False            # RegenHP=0 fuer alle Human-NPCs
    npc_gear_quality_factor: float = 1.0  # Weight-Kipp zur teureren Ware
    # --- Mutanten (global; Overrides pro Art via mutant_overrides) ---
    mutant_speed_factor: float = 1.0     # Walk/Run/SprintSpeed aller Arten
    mutant_hearing_factor: float = 1.0   # der eine geteilte MutantsHearingSensor
    mutant_regen_factor: float = 1.0     # VitalParams.RegenHP; 0 = keine Regen
    mutant_overrides: dict = field(default_factory=dict)  # {Art: {param: f}}
    bloodsucker_cloak_factor: float = 1.0    # >1 = tarnt sich schneller
    bloodsucker_uncloak_factor: float = 1.0  # >1 = Treffer enttarnen staerker
    # --- A-Life (experimentell) ---
    max_agents_factor: float = 1.0       # gleichzeitige NPCs/Mutanten um den Spieler
    spawn_distance_factor: float = 1.0   # A-Life-Spawn-Distanz
    # --- A-Life-Spawns: Lager + Director (docs/ALIFE_SPAWN_RESEARCH.md) ---
    lair_mutant_factor: float = 1.0       # MaxSpawnQuantity Mutanten-Lager
    lair_human_factor: float = 1.0        # MaxSpawnQuantity Menschen-Lager (ohne Guard*)
    lair_respawn_factor: float = 1.0      # >1 = Lager fuellen schneller nach
    encounter_frequency_factor: float = 1.0  # >1 = Director wuerfelt oefter
    encounter_mutant_factor: float = 1.0     # Gewicht rein-Mutanten-Szenarien
    encounter_pack_factor: float = 1.0       # Rang-Deckel spawnbarer Typen
    enc_blinddog_factor: float = 1.0         # je Art: Gewicht der Pack-Szenarien
    enc_boar_factor: float = 1.0
    enc_flesh_factor: float = 1.0
    enc_tushkan_factor: float = 1.0
    enc_chimera_factor: float = 1.0
    enc_generic_mutant_factor: float = 1.0   # 'Mutants'-Szenarien (Archetyp Mutant)
    mutant_hp_factor: float = 1.0
    mutant_damage_factor: float = 1.0
    explosion_damage_factor: float = 1.0
    durability_factor: float = 1.0           # Waffen-Verschleiss (Kaskade)
    armor_durability_factor: float = 1.0     # Ruestungs-"Gesundheit" (Difficulty)
    jamming_factor: float = 1.0              # 0 = Waffen klemmen nie
    # --- Ruestungsschutz (Spieler-Protection je Schadensart) ---
    armor_strike_factor: float = 1.0         # Beschuss/Physisch
    armor_burn_factor: float = 1.0
    armor_shock_factor: float = 1.0
    armor_chemical_factor: float = 1.0
    armor_radiation_factor: float = 1.0
    armor_psy_factor: float = 1.0
    armor_carry_bonus_factor: float = 1.0    # Exo-/Ruestungs-Tragegewicht-Boni

    # --- Waffenhandling ---
    scope_sway_pct: float = 100.0            # 100 = Vanilla, 0 = kein Sway (ZF)
    breath_drain_factor: float = 1.0         # 0 = unbegrenzt Luft anhalten
    breath_regen_factor: float = 1.0
    spread_factor: float = 1.0               # Streuung; 0 = laserpraezise
    recoil_factor: float = 1.0               # Rueckstoss
    recoil_upgrade_factor: float = 1.0       # Rueckstoss-Upgrades verstaerken (Deckel -100 %)
    weapon_range_factor: float = 1.0         # effektive Reichweite (Kaskade)
    weapon_bleeding_factor: float = 1.0      # Blutungs-Chance/-Staerke (Kaskade)
    ads_speed_factor: float = 1.0            # Bewegungstempo beim Zielen (Kaskade)
    aim_time_factor: float = 1.0             # Ziel-Geschwindigkeit (Kaskade)
    magazine_factor: float = 1.0             # Magazingroesse (Waffe + Magazine)
    melee_damage_factor: float = 1.0         # Messer + Kolbenschlag
    melee_range_factor: float = 1.0          # deren Reichweite (HitDetectionDistance)
    # --- Reichweiten (Nexus-Recherche 05.09.2026) ---
    interaction_range_factor: float = 1.0    # Aufheben/Behaelter (CoreVariables) + Leichen (Player)
    dialog_range_factor: float = 1.0         # Gespraechsabstand zu NPCs (Player)
    # --- NPC-Taschenlampen (FlashlightPrototypes/CoreVariables/AIGlobals) ---
    npc_flashlight_factor: float = 1.0       # Intencity + AttenuationRadius der NPC-Lampe
    npc_flashlight_cone_factor: float = 1.0  # OuterConeAngle (Deckel 170 Grad)
    npc_flashlight_combat_factor: float = 1.0  # FlashlightCombatUseChance je Rang (Deckel 1.0)
    npc_flashlight_on_hour: int = 22         # AIGlobals FlashlightTimeOfDayOn
    npc_flashlight_off_hour: int = 5         # AIGlobals FlashlightTimeOfDayOff
    # --- Speichern (SaveLoadVariables / AutoSaveVariables, beide unbinarisiert) ---
    manual_save_slots: int = 31              # SavesLimit.Manual (0 = unbegrenzt)
    quick_save_slots: int = 3                # SavesLimit.Quick
    auto_save_slots: int = 10                # SavesLimit.Auto
    autosave_interval_min: float = 10.0      # AutoSaveIntervalTime (Vanilla 600 s)
    # --- 1.24.0 (06.09.2026) ---
    artifact_slots_bonus: int = 0            # +N ArtifactSlots je Koerperruestung, Deckel 5
    shooting_shake_factor: float = 1.0       # CameraShakePrototypes *ShootCameraShake.Scale
    ads_zoom_factor: float = 1.0             # AimingFOVModifier: 0 = kein Zoom, 2 = doppelt
    climb_speed_factor: float = 1.0          # Player MovementParams.ClimbSpeedCoef (0.6)
    starting_money: int = 0                  # CoreVariables PlayerStartingMoney (neues Spiel)
    no_aim_assist_mouse: bool = False        # AimAssist-Presets *Mouse*: Kegel auf Empty
    no_aim_assist_gamepad: bool = False      # AimAssist-Presets *Gamepad*: Kegel auf Empty
    # --- 1.25.0 (06.09.2026) ---
    # ZURUECKGEZOGEN 1.36.0 (GitHub #10, craigduk76): DialogFOVDefault hat im
    # Spiel keine Wirkung, und es gibt keinen zweiten cfg-Hebel dafuer
    # (EffectPrototypes, DialogPrototypes, AIGlobals durchsucht). Feld
    # bleibt, damit alte Presets/settings.json weiter laden; kein Regler,
    # kein Patch mehr.
    dialog_fov: float = 70.0
    cutscene_fov: float = 90.0               # CoreVariables CutsceneFOVDefault
    default_fov: float = 90.0                # CoreVariables FOVDefault
    hud_compass: int = 0                     # 0 vanilla, 1 immer an, 2 immer aus
    hud_crosshair: int = 0
    hud_body_markers: int = 0
    hud_stash_markers: int = 0
    corpse_time_factor: float = 1.0          # CoreVariables Corpse*Time (1800/900/300/1800/6000)
    corpse_max_count: int = 10               # CoreVariables CorpseConditionOnlineCount
    weather_duration_factor: float = 1.0     # WeatherSelection WeatherDurationMin/Max
    regional_weather_overrides: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    bullet_drop_factor: float = 1.0          # CharacterWeaponSettings BulletDropHeight (170)
    bullet_speed_factor: float = 1.0         # ProjectilePrototypes Speed (Kugeln)
    pistol_slot_level: int = 0               # 0 vanilla, 1 +SMG, 2 +SMG+Shotgun, 3 alle
    mutant_protection_factor: float = 1.0    # Protection.* der Mutanten (fast nur Strike)
    sleep_anytime: bool = False              # AllowSleepThreshold 50 -> 0
    min_sleep_hours: int = 7                 # MinSleepHours
    sleep_in_emission: bool = False          # bAllowEmissionSleep
    # --- 1.26.0 (06.09.2026, Recherche auf Steam Workshop / mod.io / ap-pro /
    # stalker-world / sdwvit-S2Mods; docs/ROADMAP.md "Vierte Datenrecherche") ---
    no_knockdown: bool = False               # Player.CanBeKnockedDown -> false
    no_water_slowdown: bool = False          # Player.WaterContactInfo Kurven-Effekte -> empty
    # ZURUECKGEZOGEN 1.36.0 (GitHub #11, craigduk76): ClimbViewYaw/PitchLimit
    # 30/40 -> 90 taten im Spiel nichts, waehrend ViewPitchDownLimit aus
    # demselben Struct derselben Pak wirkte - die Schluessel sind tot.
    # Feld bleibt fuer alte Presets; kein Schalter, kein Patch mehr.
    ladder_free_look: bool = False
    look_straight_down: bool = False         # CoreVariables ViewPitchDownLimit -80 -> -90
    handless_zoom_factor: float = 1.0        # HandlessFOVAimModifier (0.8; kleiner = mehr Zoom)
    crouch_vignette_factor: float = 1.0      # PostEffectProcessor CrouchEffectProcessor.Intensity (0.6)
    butt_wear_factor: float = 1.0            # EffectPrototypes ButtStroke_Corrosion (5 je Schlag)
    mutants_trigger_anomalies: bool = False  # ShouldTriggerAnomalies der immunen Arten -> true
    guards_no_instakill: bool = False        # KillVolumeEffect leeren + GuardGun* BaseDamage normal
    explosion_radius_factor: float = 1.0     # ExplosionPrototypes Radius/ImpulseRadius/ConcussionRadius
    explosion_npc_damage_factor: float = 1.0 # ExplosionPrototypes DamageNPC
    phantom_dog_damage_factor: float = 1.0   # AbilityPrototypes PseudoDogSummon_* Damage/Bleeding
    psy_phantoms_only: bool = False          # ConditionalSpawnPSYNPC.FalseEffectSID -> SpawnPSYPhantoms
    reload_speed_factor: float = 1.0         # WeaponGeneralSetup *ReloadTimeMultiplier (Zeit / Faktor)
    jam_clear_factor: float = 1.0            # WeaponGeneralSetup WeaponJamParams.FullJamTime (Zeit / Faktor)
    mutant_loot_chance_factor: float = 1.0   # ItemGenerator <Art>LootGenerator Chance (Deckel 1)
    stash_clue_factor: float = 1.0           # CorpseClueStash Base/AddSpawnChance je Region (Deckel 1)
    npcs_no_corpse_loot: bool = False        # CanProcessCorpses der menschlichen NPCs -> false
    alife_vision_factor: float = 1.0         # CoreVariables ALifeGridVisionRadius/GenericModelGridVisionRadius
    map_reveal_factor: float = 1.0           # MarkerPrototypes MarkerRevealDistance/MarkerExploreDistance
    map_all_regions: bool = False            # MarkerPrototypes RegionMarker Hidden -> Explored
    fast_travel_lock: int = 2                # FastTravel OverweightLock: 0 NoLock, 1 Partial, 2 Full (Vanilla)
    guide_delay_factor: float = 1.0          # FastTravel GuideDelay (120)
    instant_teleports: bool = False          # EffectPrototypes *Teleport* TeleportType -> Instant
    protection_cap_factor: float = 1.0       # ObjEffectMaxParams Protection*-Deckel (%-Werte max 100)
    weird_artifact_factor: float = 1.0       # ItemPrototypes AArtifactWeird* EffectsDuration/MaxCharge
    skip_intro: bool = False                 # QuestNode E01_MQ01_PlayVideo Launcher-Verbindung leeren
    traders_no_gear_buy: bool = False        # TradePrototypes BuyLimitations + Weapon/Armor
    clicker_factor: float = 1.0              # AnomalyPrototypes ClickerAnomaly.ParticleMaxCount + Hit-Schaden
    # --- 1.27.0 (06.09.2026, Schluessel-Sweep; docs/ROADMAP.md 'Fuenfte Datenrecherche') ---
    back_speed_factor: float = 1.0           # Player.MovementParams *Back*Coef (Deckel 1.0)
    air_control_factor: float = 1.0          # Player.MovementParams.AirControlCoef (0.1, Deckel 1.0)
    limp_speed_factor: float = 1.0           # Player.MovementParams.LimpSpeedCoef (0.5, Deckel 1.0)
    slow_run_threshold_pct: float = 50.0     # CoreVariables SlowRunThreshold (0.5)
    hp_regen_delay: float = 5.0              # Player.VitalParams.RegenHPDelayTimeSeconds
    radiation_decay_factor: float = 1.0      # Player.VitalParams.DegenRadiation (0.05)
    bleeding_stop_factor: float = 1.0        # Player.VitalParams.DegenBleeding (0.3)
    psy_recovery_factor: float = 1.0         # Player.VitalParams.DegenPsyPoints (1.0)
    sober_up_factor: float = 1.0             # Player.VitalParams.DegenDrunknessPoints (1)
    stealth_kill_range_factor: float = 1.0   # Player.StealthKillParams.StealthKillDistance (180)
    wheel_time_pct: float = 30.0             # CoreVariables ItemSelectorTimeDilationCoefficient (0.3)
    sleep_fade_factor: float = 1.0           # CoreVariables PlayerBedFadeToBlackTime/BlackScreenTime (1.5/3.5)
    corpse_drag_factor: float = 1.0          # CoreVariables DraggingCorpseSpeedCoef (0.6, Deckel 1.0)
    item_despawn_factor: float = 1.0         # CoreVariables Untouched/DespawnItemTime (3600/10800 s)
    day_start_hour: int = 6                  # CoreVariables DayStartTime (Dawn rutscht mit)
    evening_start_hour: int = 20             # CoreVariables EveningStartTime
    calm_damage_factor: float = 1.0          # CoreVariables CalmDamageFromPlayerCoef (2.5)
    last_bullet_multiplier: float = 2.0      # CoreVariables LastBulletBaseDamageMultiplier
    armor_difference_factor: float = 1.0     # CoreVariables ArmorDifferenceCoef (2) + Player *ArmorDifferenceCoef*
    armor_deflect_chance_pct: float = 93.0   # CoreVariables ArmorDeflectMin/MaxChance (0.93)
    armor_deflect_damage_factor: float = 1.0 # CoreVariables ArmorDeflectDamageCoefHuman/Mutant (1.5)
    scope_zoom_factor: float = 1.0           # EffectPrototypes AimingFOVX2/X3/X4/X8Effect (-43..-70 %, Deckel -90)
    scope_penalty_factor: float = 1.0        # EffectPrototypes ScopeAimingTimeNeg*/ScopeAimingMovementNeg*
    upg_accuracy_factor: float = 1.0         # Upgrade-Effekte: Streuung
    upg_handling_factor: float = 1.0         # Upgrade-Effekte: Zielzeit, ADS-Tempo, Sway, Ziehen, Schusserholung, Kapazitaet
    upg_durability_factor: float = 1.0       # Upgrade-Effekte: Haltbarkeit (Waffe + Ruestung)
    upg_range_factor: float = 1.0            # Upgrade-Effekte: Reichweite, Abfall, Geschosstempo
    upg_damage_factor: float = 1.0           # Upgrade-Effekte: Schaden, Durchschlag, Deckungsdurchschlag
    upg_weight_factor: float = 1.0           # Upgrade-Effekte: Gewicht (Waffe + Ruestung)
    upg_breath_factor: float = 1.0           # Upgrade-Effekte: Atem anhalten
    upg_armor_protection_factor: float = 1.0 # Upgrade-Effekte: Ruestungsschutz je Art (Deckel 100 %)
    upg_armor_misc_factor: float = 1.0       # Upgrade-Effekte: Ausdauer-Regeneration der Ruestungen
    weapon_warning_count: int = 3            # Player.HideWeaponWarning.WarningAttemptsBeforeAlert
    weapon_warning_delay_factor: float = 1.0 # Player.HideWeaponWarning.BarkDelay (10)
    camper_time_factor: float = 1.0          # Player.CamperFeatureData.TimeToAssumeAsCamper (10)
    sync_melee_factor: float = 1.0           # CombatSynchronization: Nahkampf-Token (MaxScore)
    sync_ability_factor: float = 1.0         # CombatSynchronization: Faehigkeiten/Knockdown-Token
    sync_grenade_factor: float = 1.0         # CombatSynchronization: Granatenwuerfe-Token
    sync_suppress_factor: float = 1.0        # CombatSynchronization: Sperrfeuer-Token
    npcs_no_weapon_pickup: bool = False      # AIGlobals AllowWeaponPickupWhenLooting/BasedOnPrice -> false
    darkness_factor: float = 1.0             # AIGlobals TimeOfDayBaseLuminance (Nacht 0.2 ...), Deckel 1.0
    corpse_threat_factor: float = 1.0        # AIGlobals DeadBodyToConsiderAsThreatDuration (120)
    damage_mercy_factor: float = 1.0         # Difficulty AccumulatedDamageReductionCurveWeightMin/Max (Deckel 1)
    psy_phantom_factor: float = 1.0          # Difficulty PsyPhantomNPCOverrides[*].PsyPhantomNPCCountMultiplier
    min_resale_pct: float = 10.0             # CoreVariables ItemCostMinPercent (0.1)
    container_respawn_hours: float = 0.0     # ItemContainerPrototypes RespawnTimeSeconds (0 = nie)
    energy_tolerance_factor: float = 1.0     # CoreVariables VitalMaxEnergeticOveruse/Tolerance (1000/2500)
    npc_hip_accuracy_factor: float = 1.0     # Difficulty NPCCombatDifficulty.HipAccuracyMultiplier
    device_price_factor: float = 1.0         # Difficulty EconomyDifficulty Binoculars_Cost/NightVisionGoggles_Cost
    # --- 1.28.0 P1 (06.09.2026, Kern-Sweep; docs/CORE_SWEEP_RESEARCH.md par. 1.1 / 2.3 / 3b) ---
    limp_threshold_factor: float = 1.0       # CoreVariables LimpEffectSIDToThresholdMap Threshold 25/65 x Faktor
    no_landing_limp: bool = False            # dito, Schwellen x1000 = praktisch nie humpeln (schlaegt den Faktor)
    bleeding_hit_factor: float = 1.0         # CoreVariables VitalBaseBleedingValue (10.0)
    bleeding_nonpen_factor: float = 1.0      # CoreVariables BleedingChance/PointsNonPenetrationMod (1.0)
    damage_screen_factor: float = 1.0        # PostEffectProcessor 15 Schadens-Prozessoren Intensity (1.0), Deckel 1
    flashlight_dialog_bright: bool = False   # CoreVariables FlashlightDialogIntensityPercent 0.525 -> 1.0
    quicksave_overwrite_min: float = 5.0     # QuickSaveVariables QuickSaveOverwriteTime (300 s), in Minuten
    # --- 1.28.0 P2 (Ruestung und Trefferrechnung; par. 1.1) ---
    grenade_resist_factor: float = 1.0       # CoreVariables StrikeGrenadeResistCoefs.[0..4].GrenadeDamageResist x Faktor, Deckel 1
    armor_wear_coef: float = 0.7             # CoreVariables Armor/HelmetDurabilityParamsCoef (0.7f), absolut, experimentell
    anomaly_armor_difference_factor: float = 1.0  # CoreVariables StrikeAnomalyArmorDifferenceCoef (1.0), experimentell
    # --- 1.28.0 P3 (NPC-Verhalten im Kampf; par. 1.3 / 2.5) ---
    wounded_heal_chance: int = 70            # CoreVariables ChanceToGetHealOverTimeWhenWounded (0-100, absolut)
    wounded_cooldown_s: int = 300            # CoreVariables CooldownOnFallingWounded (Sekunden, absolut)
    wounded_regen_factor: float = 1.0        # CoreVariables WoundedStateHealthRegen (5.f) x Faktor
    wounded_heal_threshold: int = 35         # CoreVariables HpThresholdToHealWound (absolut, Richtung unbewiesen)
    npc_player_focus_factor: float = 1.0     # EnemyEvaluator [0].NotPlayerCoeff (0.15) x Faktor, Vorzeichen unbewiesen
    npc_retarget_cooldown_factor: float = 1.0   # EnemyEvaluator [0].ChangeEnemyCooldown (3.0) x Faktor
    npc_damage_memory_factor: float = 1.0    # EnemyEvaluator [0].DamageAccumulationDurationSeconds (7.0) x Faktor
    cover_distance_factor: float = 1.0       # CoverEvaluator DefaultCoverEvaluator.DefaultCoverSettings Min/MaxDistanceToEnemy (800/7000)
    cover_path_factor: float = 1.0           # CoverEvaluator DefaultCoverEvaluator.MaxPathLength (2000)
    # --- 1.28.0 P4 (Mutanten; par. 2.4 / 1.3 / 1.1) ---
    mutant_smell_factor: float = 1.0         # FlairSensor Sensing/FrontSensingRadius + Detection/FrontDetectionSpeed (aktive Sensoren)
    mutants_no_smell: bool = False           # FlairSensor IsActive -> false auf denselben Sensoren
    burer_fire_interval_factor: float = 1.0  # CoreVariables PossessedWeaponFireIntervals.<Ammo>.FireInterval (0.5-4 s) x Faktor
    mutant_loot_widget: bool = False         # CoreVariables UseMutantLootWithoutWidget true -> false (Loot-Fenster statt Animation)
    # --- 1.28.0 P5 (A-Life und Leichen; par. 2.6 / 2.7 / 1.4) ---
    squad_expansion_factor: float = 1.0      # NPCNeedsPreset GoalNeeds[Expansion] Min/MaxIncreasePerMinute (16 Presets)
    refill_cooldown_factor: float = 1.0      # ALifePolicy Full/PartialWipeRefillCooldown (360.f/120.f)
    refill_distance_factor: float = 1.0      # ALifePolicy Min/MaxRefillDistance (20000/25000), ganzzahlig
    corpse_budget: int = 30                  # ALifePolicy MaxCorpsePerRadius (absolut)
    faction_battle_chance: int = 50          # ALifePopulationManager Factions.<F>.ALifeLairExpansionBattleChance (29x, absolut)
    faction_expansion_pace_factor: float = 1.0  # ALifePopulationManager ALifeLairExpansionTime (50.f), INVERS
    corpse_distance_factor: float = 1.0      # CoreVariables CorpseOffline*SquaredDistance (x f^2) + DistanceToDestroyCorpsesIfOverpopulated (x f)
    alife_corpse_hardcap: int = 1500         # CoreVariables AlifeCorpsesHardcap (absolut)
    # --- 1.28.0 P6 (Welt und Atmosphaere; par. 1.2 / 1.3 / 2.2 / 2.6 / 2.8 / 2.10 / 2.11) ---
    radiation_dose_factor: float = 1.0       # CoreVariables RadiationPresetValues RadiationPerSecondValue (1/3/6/1)
    radiation_filter_factor: float = 1.0     # dito PostProcessRadiationIntensity (Deckel 1.0)
    geiger_volume_factor: float = 1.0        # dito GeigerRadiationIntensity (Deckel 1.0)
    barbed_wire_factor: float = 1.0          # BarbedWire Damage/BleedingValue/ArmorDamage + BleedingChance (Deckel 1)
    explosive_container_factor: float = 1.0  # Destructible Exp_* DamageDestroyThreshold (20-50)
    push_force_factor: float = 1.0           # PhysicsInteraction PlayerPushImpulse (88 Prototypen)
    weather_transition_factor: float = 1.0   # WeatherChain WeatherTransitionTimeMultiplier (22x 1), INVERS
    moon_brightness_factor: float = 1.0      # SingletonConstants MoonLightMaxBrightness (1.046f)
    sun_brightness_factor: float = 1.0       # dito SunLightMaxBrightness (3.14f)
    stars_brightness_factor: float = 1.0     # dito StarsBrightness (0.1f)
    cloud_opacity_factor: float = 1.0        # dito CloudOpacity (0.7f, Deckel 1.0)
    cloud_speed_factor: float = 1.0          # dito CloudSpeed (1.f)
    dusk_length_factor: float = 1.0          # dito LightSourceFadingDurationHoursOnDayNightChange (2.f)
    music_combat_threshold: float = 20.0     # CoreVariables MusicManagerCombatScoreThreshold (absolut)
    music_combat_lifetime: float = 25.0      # CoreVariables MusicManagerCombatEnemyAttackActionLifetimeSeconds (absolut)
    camp_life_factor: float = 1.0            # NPCNeedsPreset Needs IncreaseRateMin/Max der Lagerleben-Beduerfnisse
    # --- 1.28.0 P7 (Artefakte und Loot; par. 3b / 2.12 / 1.3) ---
    artifact_radius_factor: float = 1.0      # ItemPrototypes je Artefakt Radius (40 cm / 10), Sichtbarkeit
    artifacts_no_hop: bool = False           # dito Strafe true -> false (146 von 154)
    artifact_keepaway_factor: float = 1.0    # dito PlayerDistance (1000) + CoreVariables ArtifactStrafeMinDistance (600)
    artifact_hop_pause_factor: float = 1.0   # dito JumpSeriesDelay (45/35/25/15)
    artifact_caches_drop: bool = False       # PackOfItems ArtifactUncommon: 20 Weight 0 -> 1
    loot_reroll_radius_factor: float = 1.0   # CoreVariables RegenerateItemsOnRankUpdateRadius (40000.f)
    loot_reroll_timer_factor: float = 1.0    # CoreVariables RegenerateItemsOnRankUpdateTimer (10.f)
    # --- 1.28.0 P8 (Haendler und Wirtschaft; par. 1.3 / 2.9) ---
    repair_cost_reputation: bool = False     # CoreVariables ReputationRepairCostModifiers.[0..3] alle auf 1.0
    infotopic_refresh_hours: int = 24        # CoreVariables InfotopicRefreshHours (absolut, Spielstunden)
    # --- 1.29.0 ---
    equip_speed_factor: float = 1.0          # WeaponGeneralSetup Show/HideEquipmentTime (je 1.0), Zeit / Faktor
    shooting_anim_skip: int = 0              # WeaponGeneralSetup ShootingAnimationNumberToSkip (Vanilla 0), absolut
    # --- Munition (global ueber alle Munitionstypen) ---
    ammo_damage_factor: float = 1.0
    ammo_piercing_factor: float = 1.0        # verstaerkt die AP-Charakteristik
    ammo_armor_damage_factor: float = 1.0
    ammo_cover_factor: float = 1.0
    # Einzelsorten-Overrides {Ammo-SID: {param: faktor}}; ein Eintrag
    # ERSETZT den globalen Regler fuer diesen Parameter an dieser Sorte
    # (wie bei den Waffen), er multipliziert sich nicht dazu.
    # UpgradePrototypes RepairCostModifier: ABSOLUTWERT, Vanilla 0.2f bei
    # allen 1288 Upgrades (live gegengelesen). Der gleichnamige Schluessel
    # in ObjPrototypes (1659x, Wert 1) gehoert zu den NPCs und bleibt tabu.
    upgrade_repair_surcharge: float = 0.2
    mutant_attack_series_factor: float = 1.0  # AbilityPrototypes MaxAttacksInSeries (0/1/2/3)
    mutant_attack_bleed_factor: float = 1.0   # dito BleedingChanceIncrement (.1f / 0.f / .5f)
    jam_chance_factor: float = 1.0           # WGS Min/MaxJamChance (0.0 / 4.0-15.0)
    # --- 1.32.0: Schussverhalten (Siebte Datenrecherche, Nr. 3/4/5) ---
    recoil_recovery_factor: float = 1.0      # WGS RadiusNormalizationInterval/-Delay, Rueckstoss UND Streuung, INVERS
    spread_bloom_factor: float = 1.0         # WGS DispersionParams Max/PerIterationRadiusExtensionModifier
    aim_steady_factor: float = 1.0           # WGS Aim/AimCrouch/AimFullCrouchModifier, Betrag gedeckelt auf 1.0
    zombie_spread_factor: float = 1.0        # CWS DispersionRadiusZombieAddend (75x 30.0)
    explosion_armor_damage_factor: float = 1.0   # ExplosionPrototypes DamageArmorPlayer/-NPC
    explosion_armor_pierce_factor: float = 1.0   # dito ArmorPenetrationPlayer/-NPC (4-6)
    explosion_destructible_factor: float = 1.0   # dito DamageDestructible (1000-4000)
    bullet_penetration_factor: float = 1.0   # ProjectilePrototypes PenetrationSpawnChance, Deckel 1.0
    bullet_range_factor: float = 1.0         # ProjectilePrototypes MaxFlyDistance (16x 100000)
    # --- 1.32.0, zweite Runde (Maklane's Better Zone, Nexus 241) ---
    hip_steady_factor: float = 1.0           # WGS HipModifiers (4 Schluessel x 2 Zweige), Betrag <= 1
    move_steady_factor: float = 1.0          # WGS MovementSpeedModifiers (2 Zweige), Betrag <= 1
    recoil_pattern_factor: float = 1.0       # WGS RecoilParams.RecoilPatternInterval (0.3/1.0/5.0)
    chamber_round: bool = False              # WGS AdditionalBulletsAfterReloadingCount 0 -> 1
    dropped_ammo_factor: float = 1.0         # WGS Min/MaxDeadNPCLoadedAmmoCount (-1 = tabu)
    weapon_noise_factor: float = 1.0         # CWS FireLoudness (150x, 0.6-0.8)
    item_grid_factor: float = 1.0            # ItemPrototypes ItemGridWidth/-Height (1375x)
    inventory_action_factor: float = 1.0     # ItemPrototypes InventoryActionTime (243x), INVERS
    npc_anomaly_ignore_factor: float = 1.0   # ObjPrototypes AnomalyRestrictionsIgnoreChance, Deckel 1
    ragdoll_force_factor: float = 1.0        # ObjPrototypes DeathHit-/DeathVelocityImpulseMultiplier
    npc_retreat_radius_factor: float = 1.0   # ObjPrototypes RetreatRadius (3 top + 29 verschachtelt)
    npc_retreat_damage_factor: float = 1.0   # dito DamageAccumulatedToRetreat
    npc_vs_npc_damage_factor: float = 1.0    # CWS NPCToNPCDamageScaler (150x 0.7)
    stat_bars_follow: bool = False           # CWS DamageUI/RangeUI/RateOfFireUI mitziehen
    ammo_pack_factor: float = 1.0            # ItemPrototypes AmmoPackCount (30/10/20/50)
    ammo_bleeding_factor: float = 1.0        # ItemPrototypes BleedingMod (35x 1.0)
    ammo_recoil_factor: float = 1.0          # dito RecoilMod (35x 1.0)
    ammo_flatness_factor: float = 1.0        # dito FlatnessMod (1.0-1.9; hoeher = flachere Flugbahn)
    ammo_wear_factor: float = 1.0            # dito WeaponExhaustionMod (0.8-1.3; Abnutzung je Schuss)
    ammo_stack_factor: float = 1.0           # ItemPrototypes MaxStackCount, Munition (900)
    consumable_stack_factor: float = 1.0     # dito Nahrung/Medizin (999)

    # --- 1.33.0: Ausbeute der neunten Datenrecherche (27 fremde Mods
    # gegengelesen, docs/ROADMAP.md "Neunte Datenrecherche") -------------
    anomaly_wear_factor: float = 1.0         # EffectPrototypes: alle Corrosion-Effekte
                                             # (Burning/Carousel/Chemical/Clicker/Electro je
                                             # Body/Head/Pistol/Weapon/SecWeapon, 0.2-25) +
                                             # VelocityCorrosion; ButtStroke bleibt eigener Regler
    gear_durability_factor: float = 1.0      # ItemPrototypes BaseDurability (Waffen 1125-3000,
                                             # Ruestung 520-1040) - nur neu erzeugte Gegenstaende
    far_damage_factor: float = 1.0           # CWS MinBulletDistanceDamageModifier (150x 0.1-0.6,
                                             # Deckel 1.0) + ...ArmorPiercingModifier (150x 1.0)
    effect_cap_other_factor: float = 1.0     # ObjEffectMaxParams RegenStamina 30 / DegenBleeding 5
    lair_initial_fill_factor: float = 1.0    # LairPrototypes InitialSpawnQuantityPercent
                                             # (688x 0.5, 100x 1.0), Deckel 1.0
    lair_rare_archetype_factor: float = 1.0  # dito SpawnWeight, NUR die seltenen (0 < w < 1.0:
                                             # 147x 0.2, 23x 0.5), Deckel 1.0; Nullen bleiben 0
    lair_expansion_player_factor: float = 1.0  # ALifeDirectorScenario
                                             # DefaultALifeLairExpansionToPlayerTimeMin (120), INVERS
    fallback_spawn_count: int = 3            # dito FallbackMaxSpawnCount (3), absolut
    ammo_dispersion_factor: float = 1.0      # ItemPrototypes DispersionMod (35x, 33x 1.0)
    ammo_aim_dispersion_factor: float = 1.0  # dito AimDispersionMod (35x, 33x 1.0)
    ammo_overrides: dict = field(default_factory=dict)

    # --- Waffen-Kaskade (nur Abweichungen von 1.0 speichern; fehlt ein
    # Wert, faellt er eine Ebene runter: Einzelwaffe > Kategorie > global) ---
    weapon_category_factors: dict = field(default_factory=dict)  # {kat: {param: f}}
    weapon_overrides: dict = field(default_factory=dict)         # {WGS-SID: {param: f}}
    # Kaliberwechsel je Waffe: {WGS-SID: "A556"}. Bewusst NEBEN
    # weapon_overrides, nicht darin: dort stehen ueberall Faktoren, und
    # ein String an dieser Stelle wuerde die Kaskaden-Rechnung
    # (_weapon_factor) und den Preset-Loader zum Absturz bringen.
    weapon_calibers: dict = field(default_factory=dict)
    # Einzelruestungs-Overrides: {Item-SID: {strike/burn/...: faktor}}
    armor_overrides: dict = field(default_factory=dict)
    armor_custom: dict = field(default_factory=dict)  # explicit per-piece fields, absent = inherit
    armor_free_sprint: bool = False
    armor_limp_protection: bool = False
    # Einzel-Zielfernrohr-Overrides (1.27.0): {Item-SID: {zoom/penalty: faktor}};
    # ein Eintrag ERSETZT die globalen Scope-Regler fuer dieses Fernrohr.
    scope_overrides: dict = field(default_factory=dict)

    # --- Welt & Survival ---
    anomaly_damage_factor: float = 1.0
    anomaly_electro_factor: float = 1.0      # je Element-Typ (stapelt mit global)
    anomaly_chemical_factor: float = 1.0
    anomaly_fire_factor: float = 1.0
    anomaly_gravity_factor: float = 1.0
    radiation_factor: float = 1.0
    bleeding_factor: float = 1.0
    hunger_rate_factor: float = 1.0          # 0 = kein Hunger
    sleepiness_rate_factor: float = 1.0      # 0 = keine Muedigkeit
    consumable_duration_factor: float = 1.0  # Wirkdauer laufender Consumable-Effekte
    day_length_factor: float = 1.0           # RealToGameTimeCoef = 24 / Faktor
    quest_items_weightless: bool = False     # Quest-Items Weight = 0
    consumable_factor: float = 1.0           # Medkits/Verband/Essen usw.
    healing_factor: float = 1.0              # NUR Medizin-Heilung (Nexus-Wunsch)
    rain_factor: float = 1.0                 # Regen-/Sturm-Wettergewichte
    emission_factor: float = 1.0             # Emissions-Haeufigkeit
    emission_duration_factor: float = 1.0    # Emissions-Dauer (Zeitstreckung)
    # --- Loot in Verstecken und auf Leichen (StashPrototypes) ---
    stash_loot_factor: float = 1.0           # Stueckzahlen je Fund
    stash_chance_factor: float = 1.0         # Fundwahrscheinlichkeit
    stash_ammo_factor: float = 1.0
    stash_sets_factor: float = 1.0           # StashPrototypes ItemSetCount (0-15)           # Munition an gefundenen Waffen
    # --- Loot-Mengen im grossen Generator (ItemGeneratorPrototypes) ---
    loot_amount_factor: float = 1.0          # Stueckzahlen je Fundstelle
    # --- Zustand gedroppter Waffen (docs/GENERATOR_RESEARCH.md 3.3) ---
    # Absoluter Mittelwert in % (Vanilla-Hauptcluster 0.25/0.5 -> 37.5);
    # die Vanilla-SPANNE je Eintrag bleibt erhalten (das Spiel wuerfelt
    # darin), ausser exact=True klemmt sie auf exakt den Mittelwert.
    dropped_condition_pct: float = 37.5
    dropped_condition_exact: bool = False
    # --- Artefakte ---
    artifact_effect_factor: float = 1.0      # Effektstaerke (inkl. Nebenwirkungen)
    artifact_radiation_factor: float = 1.0   # 0 = Artefakte strahlen nicht
    artifact_count_factor: float = 1.0       # Count je Spawner/Rang
    artifact_respawn_factor: float = 1.0     # >1 = Cooldown kuerzer
    artifact_spawn_factor: float = 1.0       # Spawn-Chance der Artefakt-Spawner
    artifact_rarity_factor: float = 1.0      # >1 = seltene Stufen wahrscheinlicher

    # --- Ausruestung / Welt-Extras ---
    detector_range_factor: float = 1.0       # Detektoren + Anomalie-Piepser
    fast_travel_cost_factor: float = 1.0     # 0 = Schnellreise gratis
    trader_restock_factor: float = 1.0       # Restock-Zeit der Haendler

    # --- Fraktionsbeziehungen (docs/FACTION_RELATIONS_RESEARCH.md) ---
    # {Paar-Schluessel exakt wie in den Spieldaten ("Bandits<->Player"):
    # Zielwert als int}. Nur Abweichungen von Vanilla speichern; der
    # Builder prueft ohnehin gegen die live gelesenen Vanilla-Werte.
    faction_relations: dict = field(default_factory=dict)
    # Beziehungen auch im LAUFENDEN Spielstand setzen (1.36.0, RSO-Weg):
    # eine eigene Mini-Quest aus ChangeRelationships-Knoten, die ein
    # Skript in Scripts/OnGameLaunch/ bei jedem Spielstart anwirft.
    relations_runtime: bool = False
    relation_rollback_factor: float = 1.0    # Reputations-Rollback-Zeit
    relation_reaction_factor: float = 1.0    # Staerke der Reputations-Deltas
    trade_min_level: float = 1.0             # 0=Enemy 1=Disaffection(Van.) 2=Neutral 3=Friend

    # --- Wirtschaft ---
    trader_min_durability_pct: float = 40.0  # Vanilla 40
    # --- Haendler-Bestand & Geldbeutel (Tab "Traders") ---
    trader_stock_factor: float = 1.0         # Stueckzahlen der Ware
    trader_variety_factor: float = 1.0       # Chance je Posten (Deckel 1.0)
    trader_money_factor: float = 1.0         # Geldbeutel (nur endliche)
    trader_infinite_money: bool = False      # bInfiniteMoney ueberall an
    # --- Techniker-Upgrades (UpgradePrototypes.cfg; Nexus-Mods 2545/2549) ---
    upgrades_take_both: bool = False         # sich ausschliessende Zweige beide
    upgrades_no_blueprint: bool = False      # keine Blaupause noetig
    upgrades_no_tiers: bool = False          # keine Vorstufe noetig
    trader_buy_price_factor: float = 1.0     # was Haendler DIR zahlen
    trader_sell_price_factor: float = 1.0    # was DU bezahlst
    repair_cost_factor: float = 1.0
    upgrade_cost_factor: float = 1.0
    quest_reward_factor: float = 1.0
    repeatable_quest_factor: float = 1.0     # Cooldown wiederholbarer Jobs
    # --- 1.31.0: Jobs je Runde (GitHub Issue #8, Molkerr) ---
    # Vanilla-Cap ist bei allen acht Gebern 3 (live gegengelesen); der
    # Regler ist ein ABSOLUTWERT, je Geber auf seinen Aufgaben-Topf
    # gedeckelt (6 bis 10). 0/negativ = aus.
    repeatable_jobs_per_round: int = 3
    # Haengt den Job-Dialog vom False- auf den True-Ausgang des
    # Limit-Knotens: der Geber bietet sofort den naechsten Job an,
    # statt erst wenn er leer ist.
    repeatable_jobs_instant: bool = False
    # 1.33.0, dritter Entwurf 1.36.0 (GitHub #9): nur noch {bpatch} an den
    # vorhandenen Abschalt-Launchern des Dialogs, kein neuer Knoten - siehe
    # _quest_multi_patch. `repeatable_jobs_instant` (Pin-Schalter) ist
    # dagegen zurueckgezogen: er kann laut Graph nichts bewirken.
    repeatable_jobs_multi: bool = False

    # --- 1.35.0: die kleinen Kandidaten der neunten Datenrecherche und des
    # Familien-Waechters, alle am 08.09.2026 live nachgemessen ------------
    npc_vs_player_damage_factor: float = 1.0   # CWS NPCToPlayerDamageScaler (150x 1.0)
    npc_vs_friendly_damage_factor: float = 1.0 # CWS NPCToFriendlyDamageScaler (150x 0.3)
    traders_on_map: bool = False               # NPCPrototypes UpdateMarkerOnMap: die 80
                                               # NPCs, die schon einen Marker-TYP tragen
    look_speed_h_factor: float = 1.0           # BaseTurnRate (Player 40, CoreVariables 50)
    look_speed_v_factor: float = 1.0           # BaseLookUpRate (beide 30)
    camera_slowdown_factor: float = 1.0        # EffectPrototypes TurnRateChangeYaw/Pitch
                                               # (6 Effekte: Chemie -0.6, Draht -0.8,
                                               # Fliegenfaenger -0.7; Wasser 0% bleibt)
    bullet_penetration_depth_factor: float = 1.0  # ProjectilePrototypes
                                                  # PenetrationTraceLenght (16x 150-300)
    artifacts_no_detector: bool = False        # ItemPrototypes DetectorRequired (147x true)
    artifact_hop_distance_factor: float = 1.0  # dito JumpDistance/JumpHeight/JumpForce
    artifact_hop_count_factor: float = 1.0     # dito JumpAmount (3/5/7/9), ganzzahlig
    encounter_wounded_factor: float = 1.0      # Director ScenarioSquads WoundedMultiplier
                                               # (8 Eintraege 0.1/0.2, Rest 0), Deckel 1.0
    encounter_dead_factor: float = 1.0         # dito DeadMultiplier (36 Eintraege > 0)
    no_mouse_smoothing: bool = False           # Stalker2/Config/UserInput.ini
    no_view_acceleration: bool = False         # dito - KEINE GameData-Datei

    # Optional loot/world extensions: neutral settings emit nothing.
    stash_extra_chance_pct: float = 10.0
    npc_armor_drop_chance_pct: float = 0.0
    npc_armor_drop_min_pct: float = 20.0
    npc_armor_drop_max_pct: float = 80.0
    npc_loaded_ammo_factor: float = 1.0
    npc_helmet_chance_factor: float = 1.0
    vegetation_translucency_factor: float = 1.0
    npc_dispersion_distance_factor: float = 1.0
    mutant_loot_range_factor: float = 1.0
    mutant_loot_height_factor: float = 1.0
    mutant_cut_radius_factor: float = 1.0
    mutant_trophy_weight_factor: float = 1.0
    mutant_trophy_value_factor: float = 1.0
    decal_lifetime_factor: float = 1.0
    decal_count_factor: float = 1.0
    field_repair_body_pct: float = 0.0
    field_repair_head_pct: float = 0.0
    field_repair_weapons_pct: float = 0.0
    bolt_lifetime_factor: float = 1.0
    stash_extra_artifacts: bool = False
    stash_extra_weapons: bool = False
    stash_extra_armor: bool = False
    stash_extra_attachments: bool = False
    npc_equipment_variety: bool = False
    mutant_loot_ground_access: bool = False
    weird_flower_permanent: bool = False
    surface_noise_overrides: dict[str, float] = field(default_factory=dict)
    weather_luminance_overrides: dict[str, float] = field(default_factory=dict)
    mutant_loot_overrides: dict[str, dict[str, float]] = field(default_factory=dict)

    # Kategorie-Preise (EconomyDifficulty *_Cost, Vanilla ueberall 1.0)
    weapon_price_factor: float = 1.0
    armor_price_factor: float = 1.0
    ammo_price_factor: float = 1.0
    artifact_price_factor: float = 1.0
    consumable_price_factor: float = 1.0


def _num(x: float) -> str:
    x = round(x, 4)
    if x == 0:
        x = 0.0          # nie '-0.0' (Faktor 0 auf negative Werte)
    return fmt_float(x)


def _neq(a: float, b: float) -> bool:
    return abs(a - b) > 1e-9


def _scale_literal(raw: str, factor: float, cap: float | None = None) -> str | None:
    """GSC-Zahlenliteral vorzeichen- und suffixerhaltend skalieren.

    '20' -> '40', '-0.15' -> '-0.3', '35%' -> '70%', '2.5f' -> '5.0f'.
    None bei nicht-numerischen Werten (die bleiben unangetastet).
    cap (seit 1.28.0): Deckel auf den Zahlenwert nach dem Skalieren,
    Suffix bleibt (0.6f x 2, cap 1.0 -> 1.0f)."""
    raw = raw.strip()
    suffix = ""
    core = raw
    if core.endswith("%"):
        suffix = "%"
        core = core[:-1]
    elif core.endswith(("f", "F")):
        suffix = "f"
        core = core[:-1].rstrip(".")
    try:
        value = float(core)
    except ValueError:
        return None
    value *= factor
    if cap is not None:
        value = min(cap, value)
    return _num(value) + suffix


def _scale_count(raw: str | None, factor: float) -> str | None:
    """Ganzzahlige Stueckzahl skalieren. 0 bleibt 0 (0 x Faktor = 0), sonst
    mindestens 1. None = nichts zu patchen."""
    if raw is None:
        return None
    try:
        value = int(float(raw.strip().rstrip("fF").rstrip(".") or "0"))
    except ValueError:
        return None
    if value <= 0:
        return None
    scaled = max(1, int(round(value * factor)))
    return str(scaled) if scaled != value else None


def _scale_chance(raw: str | None, factor: float) -> str | None:
    """Wahrscheinlichkeit 0..1 skalieren, bei 1.0 deckeln, Suffix erhalten.

    Vanilla schreibt hier '0.7f', '0.5', '0' und sogar '0.' (nackter Punkt);
    0-Werte bleiben 0, damit bewusst abgeschaltete Generatoren
    (die beiden *_MainLoot) nicht versehentlich aktiviert werden."""
    if raw is None:
        return None
    core = raw.strip()
    suffix = "f" if core.endswith(("f", "F")) else ""
    if suffix:
        core = core[:-1]
    try:
        value = float(core or "0")
    except ValueError:
        return None
    if value <= 0:
        return None
    scaled = min(1.0, value * factor)
    if not _neq(scaled, value):
        return None
    return _num(scaled) + suffix


def _bool_literal(raw: str | None) -> bool | None:
    """'true'/'false' (auch mit ';') -> bool, sonst None."""
    if raw is None:
        return None
    core = raw.strip().rstrip(";").strip().lower()
    if core == "true":
        return True
    if core == "false":
        return False
    return None


def _is_empty_sid(raw: str | None) -> bool:
    return (raw or "").strip().rstrip(";").strip().lower() in ("", "empty")


# 1.26.0: alle *ReloadTimeMultiplier einer Waffe (direkt am Struct und je
# Magazin-Aufsatz in WeaponReloadTimePerAttachment)
RELOAD_KEYS = ("TacticalReloadTimeMultiplier", "FullReloadTimeMultiplier",
               "SingleBulletReloadTimeMultiplier", "TwinReloadTimeMultiplier",
               "TwinTacticalReloadTimeMultiplier")
EXPLOSION_RADIUS_KEYS = ("Radius", "ImpulseRadius", "ConcussionRadius")
# Schutz-Deckel in ObjEffectMaxParams: True = Prozentwert (Deckel 100),
# Strike ist eine Punkteskala (Vanilla 4.5) ohne Deckel
PROTECTION_CAP_TYPES = {"ProtectionStrike": False, "ProtectionBurn": True,
                        "ProtectionShock": True, "ProtectionChemical": True,
                        "ProtectionPSY": True, "ProtectionRadiation": True}
FAST_TRAVEL_LOCKS = {0: "EOverweightLock::NoLock", 1: "EOverweightLock::Partial",
                     2: "EOverweightLock::Full"}
# 1.27.0: Upgrade-Effektfamilien (Effekt-Typ -> Regler, Richtung). "neg" = der
# Bonus steht als negative Zahl (-20 % Streuung), "pos" = als positive
# (+15 % Haltbarkeit). Gegenteilige Vorzeichen sind Malus-Effekte
# (RecoilNeg20, DurabilityPerShotNeg20) und bleiben unangetastet.
UPGRADE_FAMILIES = {
    # 1.33.0: `Accuracy` fehlte hier ganz (AccuracyUpgrade -> AccuracyEffect
    # +50 %, gemessen 07.09.2026) - der Regler hat den Effekt bisher
    # uebersprungen. Die zwei Aim-Modifikatoren stehen dazu, weil sie
    # sachlich zur Streuung gehoeren; ihre Vorzeichen sind in Vanilla
    # uneinheitlich (AimDispersionPos100 -100 %, DispersionAimModifierNeg70
    # +70 %), darum "neg": es wird nur skaliert, was wirklich ein Bonus ist.
    "upg_accuracy_factor": {"Dispersion": "neg", "DispersionMaxRadiusExtension": "neg",
                            "DispersionPerIterationRadiusExtension": "neg",
                            "Accuracy": "pos", "DispersionAimModifier": "neg",
                            "DispersionOffsetAimModifier": "neg"},
    "upg_handling_factor": {"AimingTime": "neg", "AimingMovementSpeed": "pos",
                            "IdleSwayXModifier": "neg", "IdleSwayYModifier": "neg",
                            "ShowEquipmentTime": "pos", "HideEquipmentTime": "pos",
                            "RecoilRadiusNormalizationInterval": "neg", "AmmoCapacity": "pos"},
    "upg_durability_factor": {"MaxDurability": "pos", "DurabilityDamagePerShot": "neg"},
    "upg_range_factor": {"EffectiveFireDistance": "pos", "BulletDropLength": "pos",
                         "MinBulletDistanceDamage": "pos", "BulletSpeedSlowdown": "neg"},
    "upg_damage_factor": {"BaseDamage": "pos", "ArmorPiercing": "pos", "CoverPiercing": "pos"},
    "upg_weight_factor": {"WeaponItemWeight": "neg", "ArmorItemWeight": "neg"},
    "upg_breath_factor": {"HoldBreathDrain": "neg"},
    "upg_armor_protection_factor": {"ProtectionStrike": "pos", "ProtectionBurn": "pos",
                                    "ProtectionShock": "pos", "ProtectionChemical": "pos",
                                    "ProtectionPSY": "pos", "ProtectionRadiation": "pos"},
    # 1.33.0: MovementSpeedUpgrade -> MovementSpeedEffect (+50 %) hing an
    # keinem Regler; die zwei Exo-Varianten stehen auf 0.f und bleiben es.
    "upg_armor_misc_factor": {"RegenStamina": "pos", "MovementSpeed": "pos"},
}
BACK_SPEED_KEYS = ("WalkBackCoef", "RunBackCoef", "MoveBackCrouchCoef",
                   "MoveBackLowCrouchCoef", "RunDiagonalBackCoef", "WalkDiagonalBackCoef")
SYNC_GROUPS = {"sync_melee_factor": ("TokenTag.Melee",),
               "sync_ability_factor": ("TokenTag.Ability", "TokenTag.Ability.Knockdown"),
               "sync_grenade_factor": ("TokenTag.CombatAction.ThrowGrenade",
                                       "TokenTag.CombatAction.Special.ThrowGrenade"),
               "sync_suppress_factor": ("TokenTag.CombatAction.SuppressiveFire",)}


# ------------------------------------------------------------------ features

def _player_patch(gd: GameData, s: Settings) -> dict:
    player_node = gd.obj.children.get("Player")

    vital: dict = {}
    if _neq(s.max_hp, 100):
        vital["MaxHP"] = _num(s.max_hp)
    if _neq(s.hp_regen, 0):
        vital["RegenHP"] = _num(s.hp_regen)
    if _neq(s.max_stamina, 100):
        vital["MaxSP"] = _num(s.max_stamina)
    if _neq(s.stamina_regen, 5.0):
        vital["RegenSP"] = _num(s.stamina_regen)
    if _neq(s.hunger_rate_factor, 1.0):
        vanilla = parse_number(gd.resolve(gd.obj, "Player", "VitalParams.RegenHungerPoints"), 0.015)
        vital["RegenHungerPoints"] = _num(vanilla * s.hunger_rate_factor)
    if _neq(s.sleepiness_rate_factor, 1.0):
        vanilla = parse_number(gd.resolve(gd.obj, "Player", "VitalParams.RegenSleepinessPoints"), 0.01)
        vital["RegenSleepinessPoints"] = _num(vanilla * s.sleepiness_rate_factor)

    # 1.27.0: Regen-Verzoegerung (absolut) und die vier Erholungs-Raten
    live_delay = parse_number(gd.resolve(gd.obj, "Player", "VitalParams.RegenHPDelayTimeSeconds"), -1.0)
    if live_delay >= 0 and _neq(float(s.hp_regen_delay), live_delay):
        vital["RegenHPDelayTimeSeconds"] = _num(max(0.0, float(s.hp_regen_delay)))
    for key, factor in (("DegenRadiation", s.radiation_decay_factor),
                        ("DegenBleeding", s.bleeding_stop_factor),
                        ("DegenPsyPoints", s.psy_recovery_factor),
                        ("DegenDrunknessPoints", s.sober_up_factor)):
        if _neq(factor, 1.0) and factor >= 0:
            raw = gd.resolve(gd.obj, "Player", f"VitalParams.{key}")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, factor)
                if scaled is not None:
                    vital[key] = scaled

    player: dict = {}
    if vital:
        player["VitalParams"] = vital

    actions: dict = {}
    per_action = player_node.children.get("StaminaPerAction") if player_node else None
    if per_action:
        for field_name, key in STAMINA_ACTIONS:
            factor = getattr(s, field_name)
            if _neq(factor, 1.0):
                vanilla = parse_number(per_action.values.get(key))
                actions[key] = _num(vanilla * factor)
    if actions:
        player["StaminaPerAction"] = actions

    movement: dict = {}
    for factor, keys in ((s.walk_speed_factor, WALK_SPEED_KEYS),
                         (s.run_speed_factor, RUN_SPEED_KEYS)):
        if _neq(factor, 1.0):
            for key in keys:
                vanilla = parse_number(gd.resolve(gd.obj, "Player", f"MovementParams.{key}"))
                if vanilla > 0:
                    movement[key] = _num(vanilla * factor)
    if _neq(s.jump_height_factor, 1.0):
        vanilla = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.JumpSpeedCoef"), 1.0)
        movement["JumpSpeedCoef"] = _num(vanilla * s.jump_height_factor)
    # Leitern (06.09.2026): ClimbSpeedCoef, Vanilla 0.6.
    if _neq(s.climb_speed_factor, 1.0) and s.climb_speed_factor > 0:
        vanilla = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.ClimbSpeedCoef"), 0.0)
        if vanilla > 0:
            movement["ClimbSpeedCoef"] = _num(vanilla * s.climb_speed_factor)

    # Vaulting: Preset (nur vom Vanilla abweichende Werte) + Hoehen-Faktor.
    # Der Faktor skaliert auf der jeweils aktiven Basis (Preset an: 200).
    vault: dict = {}
    if s.improved_vaulting:
        for key, value in VAULT_PRESET.items():
            current = gd.resolve(gd.obj, "Player", f"VaultingParams.{key}")
            if current is None or _neq(parse_number(value),
                                       parse_number(current)):
                vault[key] = value

    def vault_base(key: str, fallback: float) -> float:
        """Basis fuer die Vault-Regler: Preset-Wert, wenn das Preset an ist
        und diesen Schluessel setzt, sonst der live gelesene Vanilla-Wert.
        Dieselbe Stapel-Regel wie beim Hoehen-Regler seit v1.10.0."""
        if s.improved_vaulting and key in VAULT_PRESET:
            return parse_number(VAULT_PRESET[key])
        return parse_number(
            gd.resolve(gd.obj, "Player", f"VaultingParams.{key}"), fallback)

    if _neq(s.vault_height_factor, 1.0) and s.vault_height_factor > 0:
        vault["MaxObstacleHeight"] = _num(
            vault_base("MaxObstacleHeight", 130.0) * s.vault_height_factor)
    if _neq(s.vault_distance_factor, 1.0) and s.vault_distance_factor > 0:
        # Beide Distanzen zusammen: die Erkennung (MaxTestDistance) und der
        # fruehestmoegliche Start (StartDistance) gehoeren zusammen — die
        # alte Mod hat auch beide angehoben.
        vault["MaxTestDistance"] = _num(
            vault_base("MaxTestDistance", 15.0) * s.vault_distance_factor)
        vault["StartDistance"] = _num(
            vault_base("StartDistance", 10.0) * s.vault_distance_factor)
    if _neq(s.vault_angle_factor, 1.0) and s.vault_angle_factor > 0:
        # 180 Grad = frontal bis seitlich; mehr ergibt geometrisch keinen Sinn
        vault["MaxAngle"] = _num(min(
            180.0, vault_base("MaxAngle", 75.0) * s.vault_angle_factor))
    if _neq(s.vault_min_height_factor, 1.0) and s.vault_min_height_factor > 0:
        vault["MinObstacleHeight"] = _num(
            vault_base("MinObstacleHeight", 70.0) * s.vault_min_height_factor)
    if _neq(s.vault_landing_factor, 1.0) and s.vault_landing_factor > 0:
        # Ein Knopf, drei zusammengehoerige Schluessel: weiter entfernt
        # landen duerfen (Offset x f), auf steilerem Untergrund (Slope x f,
        # Deckel 90 Grad) und auf niedrigeren Kanten (MinHeight / f, nie
        # unter 5 — 0 waere "in der Luft landen").
        vault["MaxLandingOffset"] = _num(
            vault_base("MaxLandingOffset", 50.0) * s.vault_landing_factor)
        vault["LandingMaxSlope"] = _num(min(
            90.0, vault_base("LandingMaxSlope", 45.0) * s.vault_landing_factor))
        vault["LandingMinHeight"] = _num(max(
            5.0, vault_base("LandingMinHeight", 30.0) / s.vault_landing_factor))
    if _neq(s.vault_over_depth_factor, 1.0) and s.vault_over_depth_factor > 0:
        vault["VaultOverMaxDepth"] = _num(
            vault_base("VaultOverMaxDepth", 50.0) * s.vault_over_depth_factor)
    if _neq(s.vault_over_offset_factor, 1.0) and s.vault_over_offset_factor > 0:
        vault["VaultOverLandOffset"] = _num(
            vault_base("VaultOverLandOffset", 20.0)
            * s.vault_over_offset_factor)
    if s.vault_sprint:
        current = (gd.resolve(gd.obj, "Player",
                              "VaultingParams.StartWithSprintPressed") or "")
        if current.strip().rstrip(";").strip().lower() != "true":
            vault["StartWithSprintPressed"] = "true"
    # 1.27.0: rueckwaerts/seitwaerts, Luftkontrolle, Humpeln (Deckel 1.0 =
    # nie schneller als vorwaerts)
    for keys, factor in ((BACK_SPEED_KEYS, s.back_speed_factor),
                         (("AirControlCoef",), s.air_control_factor),
                         (("LimpSpeedCoef",), s.limp_speed_factor)):
        if not (_neq(factor, 1.0) and factor > 0):
            continue
        for key in keys:
            vanilla = parse_number(gd.resolve(gd.obj, "Player", f"MovementParams.{key}"))
            if vanilla > 0:
                new = min(1.0, vanilla * factor)
                if _neq(new, vanilla):
                    movement[key] = _num(new)
    # 1.35.0: Blicktempo waagerecht/senkrecht getrennt. Gemessen 08.09.2026:
    # Player.MovementParams BaseTurnRate 40 / BaseLookUpRate 30 - waagerecht
    # dreht man also ein Drittel schneller als senkrecht, und das Spielmenue
    # hat dafuer nur EINEN Regler. Dieselben zwei Schluessel stehen auch in
    # CoreVariables (50.0 / 30.0); welcher gewinnt, ist unbewiesen, darum
    # werden beide gleich skaliert (siehe _corevars_patch). KEIN Deckel 1.0 -
    # das sind Grad je Sekunde, keine Koeffizienten.
    for key, factor in (("BaseTurnRate", s.look_speed_h_factor),
                        ("BaseLookUpRate", s.look_speed_v_factor)):
        if not (_neq(factor, 1.0) and factor > 0):
            continue
        raw = gd.resolve(gd.obj, "Player", f"MovementParams.{key}")
        if raw is None:
            continue
        scaled = _scale_literal(raw, factor)
        if scaled is not None and scaled != raw.strip():
            movement[key] = scaled
    if movement:
        player["MovementParams"] = movement

    if vault:
        player["VaultingParams"] = vault
    if _neq(s.fall_damage_pct, 100):
        # Protection.Fall ist prozentualer Schutz: 100 = kein Fallschaden
        player["Protection"] = {"Fall": _num(100.0 - s.fall_damage_pct)}

    # Stealth-Koeffizienten des Spielers (Player.StealthParams): geduckte
    # Sichtbarkeit/Laerm (Vanilla 0.3/0.3) sinken mit dem Crouch-Faktor,
    # der Lampen-Faktor (Vanilla 2.0) skaliert mit dem Flashlight-Regler.
    stealth: dict = {}
    if _neq(s.crouch_stealth_factor, 1.0) and s.crouch_stealth_factor > 0:
        for key in ("VisibilityCrouchCoef", "NoiseCrouchCoef"):
            raw = gd.resolve(gd.obj, "Player", f"StealthParams.{key}")
            if raw is not None and parse_number(raw) > 0:
                stealth[key] = _scale_literal(raw, 1.0 / s.crouch_stealth_factor)
    if _neq(s.flashlight_stealth_factor, 1.0) and s.flashlight_stealth_factor >= 0:
        raw = gd.resolve(gd.obj, "Player", "StealthParams.FlashLightCoef")
        if raw is not None and parse_number(raw) > 0:
            stealth["FlashLightCoef"] = _scale_literal(raw, s.flashlight_stealth_factor)
    if stealth:
        player["StealthParams"] = stealth

    # Reichweiten (Nexus "Exi's Social Distancing", Recherche 05.09.2026):
    # Gespraechsabstand (Player.Min/MaxDialogInteractDistance, Vanilla
    # 75/130, beide gemeinsam skaliert, damit ihr Verhaeltnis bleibt) und
    # Leichen pluendern (ProcessCorpseObjectFeatureData.
    # CorpseInteractionDistance, Vanilla 65). Werte in cm.
    if _neq(s.dialog_range_factor, 1.0) and s.dialog_range_factor > 0:
        for key in ("MinDialogInteractDistance", "MaxDialogInteractDistance"):
            raw = gd.resolve(gd.obj, "Player", key)
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.dialog_range_factor)
                if scaled is not None:
                    player[key] = scaled
    if _neq(s.interaction_range_factor, 1.0) and s.interaction_range_factor > 0:
        raw = gd.resolve(gd.obj, "Player",
                         "ProcessCorpseObjectFeatureData.CorpseInteractionDistance")
        if raw is not None and parse_number(raw) > 0:
            scaled = _scale_literal(raw, s.interaction_range_factor)
            if scaled is not None:
                player["ProcessCorpseObjectFeatureData"] = {
                    "CorpseInteractionDistance": scaled}

    # 1.27.0: Stealth-Kill-Reichweite, Waffe-weg-Warnungen, Camper-Erkennung,
    # Ruestung-gegen-Kugel-Gewichtung des Spielers
    if _neq(s.stealth_kill_range_factor, 1.0) and s.stealth_kill_range_factor > 0:
        raw = gd.resolve(gd.obj, "Player", "StealthKillParams.StealthKillDistance")
        if raw is not None and parse_number(raw) > 0:
            scaled = _scale_literal(raw, s.stealth_kill_range_factor)
            if scaled is not None:
                player["StealthKillParams"] = {"StealthKillDistance": scaled}
    warning: dict = {}
    live_count = parse_number(gd.resolve(gd.obj, "Player", "HideWeaponWarning.WarningAttemptsBeforeAlert"), -1.0)
    if live_count >= 0 and int(s.weapon_warning_count) != int(live_count):
        warning["WarningAttemptsBeforeAlert"] = str(max(1, int(s.weapon_warning_count)))
    if _neq(s.weapon_warning_delay_factor, 1.0) and s.weapon_warning_delay_factor > 0:
        raw = gd.resolve(gd.obj, "Player", "HideWeaponWarning.BarkDelay")
        if raw is not None and parse_number(raw) > 0:
            warning["BarkDelay"] = _num(parse_number(raw) * s.weapon_warning_delay_factor)
    if warning:
        player["HideWeaponWarning"] = warning
    if _neq(s.camper_time_factor, 1.0) and s.camper_time_factor > 0:
        raw = gd.resolve(gd.obj, "Player", "CamperFeatureData.TimeToAssumeAsCamper")
        if raw is not None and parse_number(raw) > 0:
            player["CamperFeatureData"] = {
                "TimeToAssumeAsCamper": _num(parse_number(raw) * s.camper_time_factor)}
    if _neq(s.armor_difference_factor, 1.0) and s.armor_difference_factor > 0:
        for key in ("ArmorDifferenceCoefProjectiles", "ArmorDifferenceCoefMeleeAttacks"):
            raw = gd.resolve(gd.obj, "Player", key)
            if raw is not None and parse_number(raw) > 0:
                player[key] = _num(parse_number(raw) * s.armor_difference_factor)

    # 1.26.0: nicht umwerfbar (sdwvit CantBeKnockedDown) und kein
    # Schleichgang im Wasser (sdwvit NoSluggishWater: die Kurven-Effekte der
    # Wasserberuehrung - Drehrate und Bewegungstempo - auf 'empty').
    if s.no_knockdown and _bool_literal(
            gd.resolve(gd.obj, "Player", "CanBeKnockedDown")) is not False:
        player["CanBeKnockedDown"] = "false"
    if s.no_water_slowdown and player_node is not None:
        water_node = player_node.children.get("WaterContactInfo")
        water: dict = {}
        if water_node is not None:
            for group in ("SingleCurveEffects", "DualCurveEffects"):
                arr = water_node.children.get(group)
                if arr is None:
                    continue
                entries = {idx: {"EffectSID": "empty"}
                           for idx, entry in arr.children.items()
                           if not _is_empty_sid(entry.values.get("EffectSID"))}
                if entries:
                    water[group] = entries
        if water:
            player["WaterContactInfo"] = water

    return {"Player": player} if player else {}


# Vision: Player/NoVision nie anfassen; Boss/ScarBoss-Scanner (Korshunov,
# Scar, StrelokMutant) bewusst ausgenommen. ACHTUNG Vanilla-Ausreisser:
# der Faust-Bosskampf nutzt DefaultNPC-Vision (wird also mitskaliert) und
# der Supersoldier als einziger Mutant DefaultNPC-Hearing — beides ist in
# den GUI-Tooltips dokumentiert; sauberer Fix (eigener Sensor-Klon per
# Patch) steht in docs/ROADMAP.md fuer nach den In-Game-Tests.
NPC_VISION_SKIP = {"Player", "NoVision", "ScarBoss", "Boss"}
NPC_HEARING_SKIP = {"MutantsHearingSensor"}


def _stash_patch(gd: GameData, s: Settings) -> dict:
    """Loot in Verstecken und auf Leichen (StashPrototypes.cfg).

    Aufbau je Eintrag: <SID>.ItemGenerators[i].SmartLootParams.<Gruppe>[j]
    mit MinSpawnChance/MaxSpawnChance/MainWeaponAmmoCount und darunter
    Items[k].MinCount/MaxCount. Raenge und Gruppen sind je Struct
    unterschiedlich belegt und werden deshalb live gelesen; das Null-Schema
    'empty' bleibt unangetastet (docs/GENERATOR_RESEARCH.md)."""
    loot = _neq(s.stash_loot_factor, 1.0)
    chance = _neq(s.stash_chance_factor, 1.0)
    ammo = _neq(s.stash_ammo_factor, 1.0)
    sets = _neq(s.stash_sets_factor, 1.0)
    if not (loot or chance or ammo or sets):
        return {}

    patches: dict = {}
    for sid, gen_key, group, entry_key, entry in gd.stash_entries():
        cfg: dict = {}
        if chance:
            for key in ("MinSpawnChance", "MaxSpawnChance"):
                scaled = _scale_chance(entry.values.get(key), s.stash_chance_factor)
                if scaled is not None:
                    cfg[key] = scaled
        if ammo:
            scaled = _scale_count(entry.values.get("MainWeaponAmmoCount"),
                                  s.stash_ammo_factor)
            if scaled is not None:
                cfg["MainWeaponAmmoCount"] = scaled
        if sets:
            # ItemSetCount = wieviele Fundgruppen ein Versteck auswuerfelt
            # (Vanilla 0 bis 15, meist 2-5). Andere Achse als der
            # Mengen-Regler darueber: mehr SORTEN statt mehr Stueck.
            # _scale_count laesst 0 bei 0 und geht nie unter 1.
            scaled = _scale_count(entry.values.get("ItemSetCount"),
                                  s.stash_sets_factor)
            if scaled is not None:
                cfg["ItemSetCount"] = scaled
        if loot:
            items: dict = {}
            items_node = entry.children.get("Items")
            for item_key, item in (items_node.children.items() if items_node else ()):
                new_min = _scale_count(item.values.get("MinCount"), s.stash_loot_factor)
                new_max = _scale_count(item.values.get("MaxCount"), s.stash_loot_factor)
                # Ein Vanilla-Eintrag hat Min 25 > Max 15. Den Widerspruch
                # nicht verschaerfen — aber auch keinen neuen erzeugen.
                if new_min is not None and new_max is not None:
                    old_min = parse_number(item.values.get("MinCount"))
                    old_max = parse_number(item.values.get("MaxCount"))
                    if old_min <= old_max and int(new_min) > int(new_max):
                        new_min = new_max
                item_cfg: dict = {}
                if new_min is not None:
                    item_cfg["MinCount"] = new_min
                if new_max is not None:
                    item_cfg["MaxCount"] = new_max
                if item_cfg:
                    items[item_key] = item_cfg
            if items:
                cfg["Items"] = items
        if not cfg:
            continue
        node = (patches.setdefault(sid, {})
                       .setdefault("ItemGenerators", {})
                       .setdefault(gen_key, {})
                       .setdefault("SmartLootParams", {})
                       .setdefault(group, {}))
        node[entry_key] = cfg
    return patches


def _loot_patch(gd: GameData, s: Settings) -> dict:
    """Stueckzahlen im grossen Loot-Generator (ItemGeneratorPrototypes.cfg).

    Pfad je Eintrag: <Prototyp>.ItemGenerator.<Slot>.PossibleItems[j] mit
    MinCount/MaxCount. Welche Prototypen sicher sind, entscheidet der
    zweistufige Filter in gamedata.loot_generators(); MoneyGenerator (Kupons)
    und das Basis-Template [0] werden dort gar nicht erst geliefert.

    Es werden nur vorhandene Schluessel skaliert - 814 Eintraege haben
    MinCount ohne MaxCount, und ein Patch darf dort nichts anlegen."""
    if not _neq(s.loot_amount_factor, 1.0):
        return {}

    patches: dict = {}
    for sid, gen_key, slot_key, item_key, item in gd.loot_count_entries():
        new_min = _scale_count(item.values.get("MinCount"), s.loot_amount_factor)
        new_max = _scale_count(item.values.get("MaxCount"), s.loot_amount_factor)
        # Rundung darf keinen Widerspruch Min > Max erzeugen (Vanilla hat in
        # dieser Datei keinen einzigen solchen Fall).
        if new_min is not None and new_max is not None and int(new_min) > int(new_max):
            new_min = new_max
        cfg: dict = {}
        if new_min is not None:
            cfg["MinCount"] = new_min
        if new_max is not None:
            cfg["MaxCount"] = new_max
        if not cfg:
            continue
        (patches.setdefault(sid, {})
                .setdefault(gen_key, {})
                .setdefault(slot_key, {})
                .setdefault("PossibleItems", {}))[item_key] = cfg
    return patches


def _merge_nested(dst: dict, src: dict) -> dict:
    """Zwei Patch-Baeume (verschachtelte dicts, Blaetter = Strings)
    zusammenfuehren — mehrere Builder schreiben in DIESELBE Zieldatei
    und teilweise in denselben Knoten (z.B. MinCount + MinDurability am
    selben PossibleItems-Eintrag)."""
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _merge_nested(dst[key], value)
        else:
            dst[key] = value
    return dst


def _struct_dict(node) -> dict:
    """CfgStruct -> verschachteltes dict (Werte als gestrippte Roh-Strings,
    also exakt die Vanilla-Literale wie `40.f`)."""
    out: dict = {k: v.strip() for k, v in node.values.items()}
    for key, child in node.children.items():
        out[key] = _struct_dict(child)
    return out


def _resolved_struct(root, node, depth: int = 0) -> dict:
    """Wie _struct_dict, aber mit aufgeloester refkey-Vererbung innerhalb
    derselben Datei (Vorlage zuerst, eigene Werte darueber).

    Zweck: index-adressierte TOP-LEVEL-Eintraege ([0], [1] ...) KOMPLETT
    ausgeben. Ob das Spiel solche Eintraege beim {bpatch} wie benannte
    Structs zusammenfuehrt oder — wie Array-Elemente — ersetzt, ist nicht
    belegt (docs/SPEC.md §0 nennt Arrays als offene Frage; Anlass war der
    Nexus-Wetterbericht vom 04.09.). Komplett ausgegeben ist der Patch
    unter beiden Lesarten richtig; Kosten sind ein paar Zeilen mehr."""
    base: dict = {}
    ref = node.attr_dict().get("refkey")
    if ref and depth < 8 and ref in root.children:
        base = _resolved_struct(root, root.children[ref], depth + 1)
    return _merge_nested(base, _struct_dict(node))


def _loot_condition_patch(gd: GameData, s: Settings) -> dict:
    """Zustand gedroppter Waffen (MinDurability/MaxDurability).

    Der Regler setzt den MITTELWERT absolut (Vanilla-Hauptcluster
    0.25/0.5 = 37.5 %); die Vanilla-Spanne jedes Eintrags wandert mit —
    das Spiel wuerfelt darin, genau wie vanilla (80 % ergibt also z.B.
    67.5–92.5 % beim Hauptcluster). exact=True klemmt die Spanne auf 0.
    Nur Waffen-Slots (Primary/Secondary/Pistol) der sicheren Loot-
    Prototypen; Ruestung/Helme/Artefakte und Haendler-Ware bleiben
    vanilla. Klammer 0..1, nie Min > Max (Recherche, Warnung 16)."""
    move = _neq(s.dropped_condition_pct, 37.5)
    if not (move or s.dropped_condition_exact):
        return {}
    patches: dict = {}
    for sid, gen_key, slot_key, item_key, item in gd.loot_durability_entries():
        vmin = parse_number(item.values.get("MinDurability"))
        vmax = parse_number(item.values.get("MaxDurability"))
        center = (vmin + vmax) / 2.0
        width = 0.0 if s.dropped_condition_exact else (vmax - vmin) / 2.0
        target = (s.dropped_condition_pct / 100.0) if move else center
        new_min = min(1.0, max(0.0, target - width))
        new_max = min(1.0, max(0.0, target + width))
        if new_min > new_max:
            new_min = new_max
        cfg: dict = {}
        if _neq(new_min, vmin):
            cfg["MinDurability"] = _num(new_min)
        if _neq(new_max, vmax):
            cfg["MaxDurability"] = _num(new_max)
        if cfg:
            (patches.setdefault(sid, {})
                    .setdefault(gen_key, {})
                    .setdefault(slot_key, {})
                    .setdefault("PossibleItems", {}))[item_key] = cfg
    return patches


def _gear_quality_patch(gd: GameData, s: Settings) -> dict:
    """NPC-Ausruestungsqualitaet: kippt die Weight-Lotterien der
    Loadout-Pools zur teureren Ware (Preis als Tier-Massstab, live aus
    ItemPrototypes.Cost gelesen). Innerhalb eines Pools bekommt das
    billigste Item Faktor 1, das teuerste den vollen Faktor, dazwischen
    geometrisch nach Preisrang — bei Faktor 4 ist die beste Waffe des
    Pools also 4x so wahrscheinlich, bei 0.25 dominiert der Schrott.
    EHRLICHE GRENZE: es werden nie Items ergaenzt oder entfernt (Gewicht
    faellt nie unter 1), NPCs tragen weiter nur, was ihr Pool vanilla
    hergibt. Items ohne aufloesbaren Preis bleiben unangetastet."""
    f = s.npc_gear_quality_factor
    if not _neq(f, 1.0) or f <= 0:
        return {}
    patches: dict = {}
    for sid, gen_key, slot_key, pool in gd.gear_weight_pools():
        costs = sorted({cost for *_x, cost in pool if cost is not None})
        if len(costs) < 2:
            continue
        rank = {cost: i / (len(costs) - 1) for i, cost in enumerate(costs)}
        for item_key, item, weight, cost in pool:
            if cost is None:
                continue
            new = max(1, int(round(weight * (f ** rank[cost]))))
            if new == int(round(weight)):
                continue
            (patches.setdefault(sid, {})
                    .setdefault(gen_key, {})
                    .setdefault(slot_key, {})
                    .setdefault("PossibleItems", {})
                    .setdefault(item_key, {}))["Weight"] = str(new)
    return patches


def _trader_stock_patch(gd: GameData, s: Settings) -> dict:
    """Haendler-Bestand: Stueckzahlen (MinCount/MaxCount) und Sortiments-
    Chance je Posten (Deckel 1.0) in der Handelsketten-Huelle — strikt
    getrennt vom Loot-Regler (docs/GENERATOR_RESEARCH.md, Kap. 7)."""
    stock_on = _neq(s.trader_stock_factor, 1.0) and s.trader_stock_factor > 0
    variety_on = (_neq(s.trader_variety_factor, 1.0)
                  and s.trader_variety_factor > 0)
    if not (stock_on or variety_on):
        return {}
    patches: dict = {}
    for sid, gen_key, slot_key, item_key, item in gd.trader_stock_entries():
        cfg: dict = {}
        if stock_on:
            new_min = _scale_count(item.values.get("MinCount"),
                                   s.trader_stock_factor)
            new_max = _scale_count(item.values.get("MaxCount"),
                                   s.trader_stock_factor)
            if (new_min is not None and new_max is not None
                    and int(new_min) > int(new_max)):
                new_min = new_max
            if new_min is not None:
                cfg["MinCount"] = new_min
            if new_max is not None:
                cfg["MaxCount"] = new_max
        if variety_on:
            raw = item.values.get("Chance")
            if raw is not None:
                value = parse_number(raw)
                if value > 0:
                    new = min(1.0, value * s.trader_variety_factor)
                    if _neq(new, value):
                        cfg["Chance"] = _num(new)
        if cfg:
            (patches.setdefault(sid, {})
                    .setdefault(gen_key, {})
                    .setdefault(slot_key, {})
                    .setdefault("PossibleItems", {}))[item_key] = cfg
    return patches


def _trader_wallet_patch(gd: GameData, s: Settings) -> dict:
    """Haendler-Geldbeutel in TradePrototypes.cfg: Money-Faktor (wirkt
    nur auf die vanilla-endlichen Boersen) und bInfiniteMoney-Schalter
    (patcht nur Haendler, die vanilla auf false stehen)."""
    money_on = _neq(s.trader_money_factor, 1.0) and s.trader_money_factor > 0
    if not (money_on or s.trader_infinite_money):
        return {}
    patches: dict = {}
    for sid, (money, infinite) in sorted(gd.trader_wallets().items()):
        cfg: dict = {}
        if s.trader_infinite_money and not infinite:
            cfg["bInfiniteMoney"] = "true"
        if money_on and not infinite and money > 0:
            cfg["Money"] = str(int(round(money * s.trader_money_factor)))
        if cfg:
            patches[sid] = cfg
    return patches


def _npc_heal_patch(gd: GameData, s: Settings) -> dict:
    """NPCs heilen sich nicht mehr: RegenHP=0 pro NPC-Prototyp (die Structs
    sind voll expandiert, ein Patch am Basis-Struct reicht daher nicht)."""
    if s.npc_no_heal:
        return {sid: {"VitalParams": {"RegenHP": "0.0"}}
                for sid in sorted(gd.npcs_with_regen())}
    # Regen als Faktor (Nexus 2396 senkt Wachen von 20 auf 5 HP/s): live je
    # Prototyp, weil die Structs voll expandiert sind
    if _neq(s.npc_regen_factor, 1.0) and s.npc_regen_factor >= 0:
        return {sid: {"VitalParams": {"RegenHP": _num(regen * s.npc_regen_factor)}}
                for sid, regen in sorted(gd.npcs_with_regen().items())
                if regen > 0}
    return {}


def _vision_patch(gd: GameData, s: Settings) -> dict:
    if not _neq(s.npc_vision_factor, 1.0):
        return {}
    patches: dict = {}
    for sid, node in gd.visionscanners.children.items():
        if sid in NPC_VISION_SKIP or "#" in sid:
            continue
        cfg = {}
        for key in ("CentralVisionDistance", "PeripheralVisionDistance"):
            value = parse_number(node.values.get(key))
            if value > 0:
                cfg[key] = _num(value * s.npc_vision_factor)
        if cfg:
            patches[sid] = cfg
    return patches


def _hearing_patch(gd: GameData, s: Settings) -> dict:
    """SoundEvents-Array: komplette Eintraege ({Type, HearingDistance})
    emittieren, nur Distanzen > 0 skalieren."""
    if not _neq(s.npc_hearing_factor, 1.0):
        return {}
    patches: dict = {}
    for sid, node in gd.hearingsensors.children.items():
        if sid in NPC_HEARING_SKIP or "#" in sid:
            continue
        events = node.children.get("SoundEvents")
        if events is None:
            continue
        entries: dict = {}
        for idx, entry in events.children.items():
            distance = parse_number(entry.values.get("HearingDistance"))
            if distance <= 0:
                continue
            entries[idx] = {
                "Type": entry.values.get("Type", "ESoundEventType::None"),
                "HearingDistance": _num(distance * s.npc_hearing_factor),
            }
        if entries:
            patches[sid] = {"SoundEvents": entries}
    return patches


def _npc_weapon_patch(gd: GameData, s: Settings) -> dict:
    """CWS *_NPC-Structs: DispersionRadius / Genauigkeits-Faktor
    (Faktor > 1 = NPCs treffen besser) und die vier Distanz-Schluessel
    (WEAPON_RANGE_KEYS) x Reichweiten-Faktor - Gegenstueck zum Spieler-
    Range-Regler, nur fuer NPC-Waffenprofile (Nexus 2396 'NPC Ballistics')."""
    acc_on = _neq(s.npc_accuracy_factor, 1.0) and s.npc_accuracy_factor > 0
    range_on = (_neq(s.npc_weapon_range_factor, 1.0)
                and s.npc_weapon_range_factor > 0)
    if not (acc_on or range_on):
        return {}
    patches: dict = {}
    for sid in sorted(gd.weaponsettings.children):
        if "_NPC" not in sid or "#" in sid:
            continue
        cfg: dict = {}
        if acc_on:
            value = parse_number(gd.resolve(gd.weaponsettings, sid, "DispersionRadius"))
            if value > 0:
                cfg["DispersionRadius"] = _num(value / s.npc_accuracy_factor)
        if range_on:
            for key in WEAPON_RANGE_KEYS:
                value = parse_number(gd.resolve(gd.weaponsettings, sid, key))
                if value > 0:
                    cfg[key] = _num(value * s.npc_weapon_range_factor)
        if cfg:
            patches[sid] = cfg
    return patches


NPC_AI_DISTANCES = ("Long", "Medium", "Short")


def _npc_ai_patch(gd: GameData, s: Settings) -> dict:
    """WeaponAttributesPrototypes *_NPC.AIParameters.BehaviorTypes.<Rang>
    (Newbie/Experienced/Veteran/Master/Zombie), je Distanz Long/Medium/Short:
    IgnoreDispersionMin/MaxShots = Schuesse je Feuerstoss OHNE Streuung (das
    'Aimbot'-Eroeffnungsfeuer, Vorbild Nexus 2396/129), MinShots/MaxShots =
    Feuerstoss-Laenge, Min/MaxSecondsDelay + NonAutomaticWeaponShotDelay =
    Pausen, CombatEffectiveFireDistanceMin/Max = Gefechtsreichweite je Rang.
    Alle 77 *_NPC-Structs definieren ihre Bloecke selbst (kein Template-
    Patch). Ganzzahlen bleiben ganzzahlig, Min <= Max, Vanilla 0 bleibt 0,
    Garantietreffer nie ueber der Feuerstoss-Laenge."""
    free = s.npc_free_shots_factor
    free_on = _neq(free, 1.0) and free >= 0
    burst = s.npc_burst_factor
    burst_on = _neq(burst, 1.0) and burst > 0
    pause = s.npc_fire_pause_factor
    pause_on = _neq(pause, 1.0) and pause > 0
    engage = s.npc_engage_range_factor
    engage_on = _neq(engage, 1.0) and engage > 0
    if not (free_on or burst_on or pause_on or engage_on):
        return {}

    def scaled_int(raw, factor, floor=0):
        value = parse_number(raw)
        if value <= 0:
            return None
        return max(floor, int(round(value * factor)))

    patches: dict = {}
    for sid, node in sorted(gd.weaponattributes.children.items()):
        if not sid.endswith("_NPC") or "#" in sid:
            continue
        ai = node.children.get("AIParameters")
        bt = ai.children.get("BehaviorTypes") if ai else None
        if bt is None:
            continue
        ranks: dict = {}
        for rank, rn in bt.children.items():
            rcfg: dict = {}
            if engage_on:
                for key in ("CombatEffectiveFireDistanceMin",
                            "CombatEffectiveFireDistanceMax"):
                    raw = rn.values.get(key)
                    if raw is not None and parse_number(raw) > 0:
                        rcfg[key] = _scale_literal(raw, engage)
            if pause_on:
                raw = rn.values.get("NonAutomaticWeaponShotDelay")
                if raw is not None and parse_number(raw) > 0:
                    rcfg["NonAutomaticWeaponShotDelay"] = _scale_literal(raw, pause)
            for dist in NPC_AI_DISTANCES:
                dn = rn.children.get(dist)
                if dn is None:
                    continue
                v = dn.values
                dcfg: dict = {}
                min_shots = parse_number(v.get("MinShots"))
                max_shots = parse_number(v.get("MaxShots"))
                if burst_on:
                    new_min = scaled_int(v.get("MinShots"), burst, 1)
                    new_max = scaled_int(v.get("MaxShots"), burst, 1)
                    if new_min is not None and new_max is not None:
                        new_min = min(new_min, new_max)
                        if new_min != int(min_shots):
                            dcfg["MinShots"] = str(new_min)
                        if new_max != int(max_shots):
                            dcfg["MaxShots"] = str(new_max)
                        max_shots = new_max
                if free_on:
                    ig_min = parse_number(v.get("IgnoreDispersionMinShots"))
                    ig_max = parse_number(v.get("IgnoreDispersionMaxShots"))
                    if ig_max > 0 or ig_min > 0:
                        new_max = int(round(ig_max * free))
                        new_min = int(round(ig_min * free))
                        if max_shots > 0:
                            new_max = min(new_max, int(max_shots))
                        new_min = min(new_min, new_max)
                        if new_min != int(ig_min):
                            dcfg["IgnoreDispersionMinShots"] = str(new_min)
                        if new_max != int(ig_max):
                            dcfg["IgnoreDispersionMaxShots"] = str(new_max)
                if pause_on:
                    for key in ("MinSecondsDelay", "MaxSecondsDelay"):
                        raw = v.get(key)
                        if raw is not None and parse_number(raw) > 0:
                            scaled = _scale_literal(raw, pause)
                            if scaled is not None and scaled != raw.strip():
                                dcfg[key] = scaled
                if dcfg:
                    rcfg[dist] = dcfg
            if rcfg:
                ranks[rank] = rcfg
        if ranks:
            patches[sid] = {"AIParameters": {"BehaviorTypes": ranks}}
    return patches


def _aiglobals_patch(gd: GameData, s: Settings) -> dict:
    """AIGlobals: Granaten pro Fraktion/Rang, Reaktionszeiten, A-Life."""
    root = gd.aiglobals.children.get("AISettings")
    if root is None:
        return {}
    settings: dict = {}

    if _neq(s.npc_grenade_factor, 1.0):
        throw = root.children.get("ThrowGrenadeSettings")
        per_faction = throw.children.get("AvailableGrenadesPerFaction") if throw else None
        factions: dict = {}
        if per_faction is not None:
            for faction, node in per_faction.children.items():
                if "#" in faction:
                    continue
                ranks: dict = {}
                for rank, raw in node.values.items():
                    count = parse_number(raw, -1.0)
                    if count < 0:  # -1 = unbegrenzt (Boss-Fraktionen) nie anfassen
                        continue
                    scaled = int(round(count * s.npc_grenade_factor))
                    if scaled != int(count):
                        ranks[rank] = str(scaled)
                if ranks:
                    factions[faction] = ranks
        if factions:
            settings["ThrowGrenadeSettings"] = {
                "AvailableGrenadesPerFaction": factions}

    if _neq(s.npc_reaction_factor, 1.0):
        threats: dict = {}
        for key in ("ThreatReportDelaySeconds", "EnemyReportDelaySeconds"):
            vanilla = parse_number(root.get(f"ThreatsSettings.{key}"))
            if vanilla > 0:
                threats[key] = _num(vanilla * s.npc_reaction_factor)
        if threats:
            settings["ThreatsSettings"] = threats

    # 1.27.0: Waffen aufheben, Leichen als Bedrohung, Dunkelheit fuer NPC-Augen
    if s.npcs_no_weapon_pickup:
        for key in ("AllowWeaponPickupWhenLooting", "AllowWeaponPickupBasedOnPrice"):
            if _bool_literal(root.values.get(key)) is not False:
                settings[key] = "false"
    if _neq(s.corpse_threat_factor, 1.0) and s.corpse_threat_factor >= 0:
        raw = root.values.get("DeadBodyToConsiderAsThreatDuration")
        if raw is not None and parse_number(raw) > 0:
            settings["DeadBodyToConsiderAsThreatDuration"] = _num(parse_number(raw) * s.corpse_threat_factor)
    if _neq(s.darkness_factor, 1.0) and s.darkness_factor >= 0:
        lum = root.children.get("LuminanceSettings")
        env = lum.children.get("EnvironmentLuminanceCoefficients") if lum is not None else None
        table = env.children.get("TimeOfDayBaseLuminance") if env is not None else None
        if table is not None:
            # die Eintraege stehen in Vanilla als [*] (Auto-Index): in
            # Reihenfolge als [0], [1], ... ansprechen; nur Werte < 1 skalieren
            rows: dict = {}
            for idx, entry in enumerate(table.children.values()):
                raw = entry.values.get("Luminance")
                value = parse_number(raw)
                if raw is None or value <= 0 or value >= 1.0:
                    continue
                new = min(1.0, value * s.darkness_factor)
                if _neq(new, value):
                    rows[f"[{idx}]"] = {"Luminance": _num(new) + "f"}
            if rows:
                settings["LuminanceSettings"] = {"EnvironmentLuminanceCoefficients": {
                    "TimeOfDayBaseLuminance": rows}}

    if _neq(s.max_agents_factor, 1.0):
        vanilla = parse_number(root.values.get("MaxAgentsCount"), 52.0)
        settings["MaxAgentsCount"] = str(max(1, int(round(vanilla * s.max_agents_factor))))

    if _neq(s.spawn_distance_factor, 1.0):
        spawn = parse_number(root.values.get("MinALifeSpawnDistance"), 2500.0)
        despawn = parse_number(root.values.get("MinALifeDespawnDistance"), 3000.0)
        new_spawn = spawn * s.spawn_distance_factor
        # Despawn-Distanz muss immer ueber der Spawn-Distanz bleiben, sonst
        # verschwinden frisch gespawnte Agenten sofort wieder
        new_despawn = max(despawn * s.spawn_distance_factor, new_spawn + 500.0)
        settings["MinALifeSpawnDistance"] = _num(new_spawn)
        settings["MinALifeDespawnDistance"] = _num(new_despawn)

    # Stealth: Haltungs-Koeffizienten (komplette [i]-Eintraege ausgeben, wie
    # bei StaminaRegenStateCoefs - Array-Eintraege nie halb patchen)
    crouch_on = _neq(s.crouch_stealth_factor, 1.0) and s.crouch_stealth_factor > 0
    noise_on = _neq(s.movement_noise_factor, 1.0) and s.movement_noise_factor >= 0
    if crouch_on or noise_on:
        poses = root.children.get("CharacterPoseSettings")
        entries: dict = {}
        for idx, entry in (poses.children.items() if poses else ()):
            pose = (entry.values.get("Pose") or "").strip()
            short = pose.split("::")[-1]
            vis = entry.values.get("VisibilityCoef")
            noise = entry.values.get("NoiseCoef")
            if vis is None or noise is None:
                continue
            new_vis, new_noise = vis.strip(), noise.strip()
            if crouch_on and short in ("LowCrouchInPlace", "Crouch"):
                new_vis = _scale_literal(vis, 1.0 / s.crouch_stealth_factor) or new_vis
                new_noise = _scale_literal(noise, 1.0 / s.crouch_stealth_factor) or new_noise
            elif noise_on and short in ("Walk", "Run", "Sprint", "None"):
                new_noise = _scale_literal(noise, s.movement_noise_factor) or new_noise
            if new_vis != vis.strip() or new_noise != noise.strip():
                entries[idx] = {"Pose": pose, "VisibilityCoef": new_vis,
                                "NoiseCoef": new_noise}
        if entries:
            settings["CharacterPoseSettings"] = entries

    # Stealth: Wetter-Abschlaege (1 - Koeffizient) x Faktor, Deckel 0.05..1
    if _neq(s.weather_stealth_factor, 1.0) and s.weather_stealth_factor >= 0:
        weather = root.children.get("WeatherSettings")
        entries = {}
        for idx, entry in (weather.children.items() if weather else ()):
            sid = (entry.values.get("WeatherSID") or "").strip()
            cfg = {"WeatherSID": sid}
            changed = False
            for key in ("VisibilityCoef", "HearingDistanceCoef", "FlairCoef"):
                raw = entry.values.get(key)
                if raw is None:
                    continue
                coef = parse_number(raw)
                new = coef
                if coef < 1.0:
                    new = max(0.05, min(1.0, 1.0 - (1.0 - coef) * s.weather_stealth_factor))
                cfg[key] = _num(new)
                if _neq(new, coef):
                    changed = True
            if changed:
                entries[idx] = cfg
        if entries:
            settings["WeatherSettings"] = entries

    # Stealth: wie stark die Spieler-Taschenlampe NPC-Sicht fuellt
    if _neq(s.flashlight_stealth_factor, 1.0) and s.flashlight_stealth_factor >= 0:
        fl = root.children.get("PlayerFlashlightVisionSettings")
        cfg = {}
        for key in ("FlashlightMinVisionScorePerSecond",
                    "FlashlightMaxVisionScorePerSecond"):
            raw = fl.values.get(key) if fl else None
            if raw is not None and parse_number(raw) > 0:
                cfg[key] = _scale_literal(raw, s.flashlight_stealth_factor)
        if cfg:
            settings["PlayerFlashlightVisionSettings"] = cfg

    # NPC-Mut: Angriffs-/Rueckzugs-Schwellen der menschlichen Taktik-Typen
    # (Bandits/Monolith/Humanoid) / Faktor; der Mutant-Eintrag bleibt.
    if _neq(s.npc_courage_factor, 1.0) and s.npc_courage_factor > 0:
        tactics = root.children.get("CombatTacticsSettings")
        per = tactics.children.get("CombatTacticsParamsPerFactions") if tactics else None
        factions = {}
        for name, node in (per.children.items() if per else ()):
            if name == "Mutant" or "#" in name:
                continue
            cfg = {}
            for key in ("ConfidenceToAttack", "ConfidenceToRetreat"):
                raw = node.values.get(key)
                if raw is not None and parse_number(raw) > 0:
                    cfg[key] = _scale_literal(raw, 1.0 / s.npc_courage_factor)
            if cfg:
                factions[name] = cfg
        if factions:
            settings["CombatTacticsSettings"] = {
                "CombatTacticsParamsPerFactions": factions}

    # NPC-Taschenlampen: Ein-/Ausschaltstunde (Vanilla 22 / 5), live
    # gelesen und nur bei Abweichung geschrieben.
    for key, wanted in (("FlashlightTimeOfDayOn", s.npc_flashlight_on_hour),
                        ("FlashlightTimeOfDayOff", s.npc_flashlight_off_hour)):
        raw = root.values.get(key)
        if raw is not None and _neq(float(wanted), parse_number(raw)):
            settings[key] = str(int(round(wanted)))

    return {"AISettings": settings} if settings else {}


def _threats_patch(gd: GameData, s: Settings) -> dict:
    """ThreatPrototypes.cfg, Profil DefaultNPC (Top-Level-Key [1]): Wachsamkeit
    = Aktions-Schwellen (TurnHead 200, SearchEnemy 350, MoveToLocation 500,
    CallAllies 700) / Faktor, ganzzahlig, 1..MaxThreatLevelValue;
    Gedaechtnis = Freeze-Zeiten x Faktor und Verlust/s / Faktor, im Profil-
    Default und je Aktion. Aktions-Eintraege ([i]) komplett ausgeben.
    Mutanten-Profile und BossNPC bleiben vanilla."""
    alert = s.npc_alertness_factor
    alert_on = _neq(alert, 1.0) and alert > 0
    mem = s.npc_search_time_factor
    mem_on = _neq(mem, 1.0) and mem > 0
    if not (alert_on or mem_on):
        return {}
    patches: dict = {}
    for key, prof in gd.threats.children.items():
        if (prof.values.get("SID") or "").strip() != "DefaultNPC":
            continue
        cfg: dict = {}
        max_level = parse_number(prof.values.get("MaxThreatLevelValue"), 1000.0)
        if mem_on:
            raw = prof.values.get("DefaultThreatValueFreezeTimeSeconds")
            if raw is not None and parse_number(raw) > 0:
                cfg["DefaultThreatValueFreezeTimeSeconds"] = _scale_literal(raw, mem)
            raw = prof.values.get("DefaultThreatValueLossPerSecond")
            if raw is not None and parse_number(raw) > 0:
                cfg["DefaultThreatValueLossPerSecond"] = _scale_literal(raw, 1.0 / mem)
        actions = prof.children.get("Actions")
        entries: dict = {}
        for idx, act in (actions.children.items() if actions else ()):
            v = act.values
            entry = {k: val.strip() for k, val in v.items()}
            changed = False
            if alert_on and parse_number(v.get("ThreatLevelValueMin")) > 0:
                new = int(round(parse_number(v["ThreatLevelValueMin"]) / alert))
                new = max(1, min(int(max_level), new))
                if new != int(parse_number(v["ThreatLevelValueMin"])):
                    entry["ThreatLevelValueMin"] = str(new)
                    changed = True
            if mem_on:
                raw = v.get("ThreatValueFreezeTimeSeconds")
                if raw is not None and parse_number(raw) > 0:
                    entry["ThreatValueFreezeTimeSeconds"] = _scale_literal(raw, mem)
                    changed = True
                raw = v.get("ThreatValueLossPerSecond")
                if raw is not None and parse_number(raw) > 0:
                    entry["ThreatValueLossPerSecond"] = _scale_literal(raw, 1.0 / mem)
                    changed = True
            if changed:
                entries[idx] = entry
        if entries:
            cfg["Actions"] = entries
        if cfg:
            if key.startswith("["):
                # Das Profil haengt am Index-Schluessel [1]: komplett
                # ausgeben (siehe _resolved_struct), Aktions-Eintraege
                # waren es schon.
                cfg = _merge_nested(_resolved_struct(gd.threats, prof), cfg)
            patches[key] = cfg
    return patches


def _npc_stagger_patch(gd: GameData, s: Settings) -> dict:
    """CriticalDamageThreshold (Schaden in 2 s, ab dem ein NPC taumelt;
    Vanilla 40, Bosse 200..100000) x Faktor - je menschlichem Prototyp,
    weil die Structs voll expandiert sind."""
    f = s.npc_stagger_factor
    if not _neq(f, 1.0) or f <= 0:
        return {}
    patches: dict = {}
    for sid in gd.human_npc_sids():
        raw = gd.obj.children[sid].values.get("CriticalDamageThreshold")
        if raw is None or parse_number(raw) <= 0:
            continue
        patches[sid] = {"CriticalDamageThreshold": _scale_literal(raw, f)}
    return patches


def _npc_dialog_patch(gd: GameData, s: Settings) -> dict:
    """Gespraechsabstand auch an den NPCs (1.36.0, GitHub #10).

    craigduk76 hat auf 1.35.0 gemessen: Min/MaxDialogInteractDistance am
    SPIELER (75/130 -> 112.5/195) aendert nichts, er musste genauso nah an
    die NPCs heran. Nachgezaehlt: die zwei Schluessel stehen an **1659**
    Prototypen - jeder der 1608 menschlichen NPCs deklariert sie selbst
    (1530x 75/130, 62x 85.f/250.f bei Haendlern und Wichtigen, ein paar
    Sonderwerte). Das Spiel liest den Abstand also offenbar am
    Gespraechspartner, nicht am Spieler. Darum jetzt beide Seiten: der
    Spieler-Teil bleibt in `_player_patch`, hier kommen die Menschen dazu;
    Mutanten reden nicht und bleiben draussen. Literalform bleibt
    (`85.f` -> `127.5f`). Nicht im Spiel getestet."""
    f = s.dialog_range_factor
    if not _neq(f, 1.0) or f <= 0:
        return {}
    patches: dict = {}
    for sid in gd.human_npc_sids():
        values = gd.obj.children[sid].values
        cfg: dict = {}
        for key in ("MinDialogInteractDistance", "MaxDialogInteractDistance"):
            raw = values.get(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, f)
            if scaled is not None:
                cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _camerashake_patch(gd: GameData, s: Settings) -> dict:
    """Aim Punch (Wackeln beim Getroffenwerden, Nexus-Wunsch) und seit
    1.24.0 das Wackeln beim SCHIESSEN: ShootingCameraShake plus die 39
    *ShootCameraShake-Eintraege je Waffe, alle mit eigenem Scale = 1.0
    (Nexus 'No Screenshake'). Explosionen/Mutanten bleiben unberuehrt."""
    patches: dict = {}
    if _neq(s.aim_punch_factor, 1.0):
        vanilla = parse_number(
            gd.resolve(gd.camerashake, "ProjectileHitCameraShake", "Scale"), 1.0)
        patches["ProjectileHitCameraShake"] = {"Scale": _num(vanilla * s.aim_punch_factor)}
    if _neq(s.shooting_shake_factor, 1.0) and s.shooting_shake_factor >= 0:
        for name, node in gd.camerashake.children.items():
            if "#" in name:
                continue
            if name != "ShootingCameraShake" and not name.endswith("ShootCameraShake"):
                continue
            raw = node.get("Scale")
            if raw is None:
                continue
            patches.setdefault(name, {})["Scale"] = _num(
                parse_number(raw, 1.0) * s.shooting_shake_factor)
    return patches


def _aimassist_patch(gd: GameData, s: Settings) -> dict:
    """Aim Assist aus (06.09.2026): die Staerke steckt in CurveFloat-Assets,
    per cfg laesst sich nur der Kegel abhaengen. Jedes Preset traegt vier
    Kegel-SIDs plus die Magnetismus-Liste; alles wird auf den Empty-Kegel
    gesetzt, dessen Name live aus dem Empty-Preset gelesen wird. Maus- und
    Gamepad-Presets getrennt (Wunsch des Besitzers). Die Waffen verweisen
    per AimAssistPresetSID auf die Gamepad-Presets je Klasse; die Maus-
    Presets haengen nicht in den Waffendaten, sondern werden vom Spiel
    direkt angesprochen (nicht play-getestet)."""
    if not (s.no_aim_assist_mouse or s.no_aim_assist_gamepad):
        return {}
    root = gd.aimassist
    empty_node = root.children.get("Empty")
    if empty_node is None:
        return {}
    empty = (empty_node.values.get("StickinessAimAssistConeSID") or "Empty").strip()
    cone_keys = ("StickinessAimAssistConeSID", "SnappingAimAssistConeSID",
                 "MovingTrackingAimAssistConeSID", "StationaryTrackingAimAssistConeSID")
    patches: dict = {}
    for name, node in root.children.items():
        if "#" in name or name == "Empty":
            continue
        is_mouse, is_pad = "Mouse" in name, "Gamepad" in name
        if not ((is_mouse and s.no_aim_assist_mouse) or (is_pad and s.no_aim_assist_gamepad)):
            continue
        cfg: dict = {}
        for key in cone_keys:
            current = (gd.resolve(root, name, key) or "").strip()
            if current and current != empty:
                cfg[key] = empty
        magnet = node.children.get("MagnetismAimAssistConeSIDs")
        if magnet is not None:
            entries = {idx: empty for idx, value in magnet.values.items()
                       if (value or "").strip() != empty}
            if entries:
                cfg["MagnetismAimAssistConeSIDs"] = entries
        if cfg:
            patches[name] = cfg
    return patches


def _artifact_spawner_patch(gd: GameData, s: Settings) -> dict:
    """SpawnChanceBase (Cap 100 %), Rarity-Verteilung, Count (Artefakte je
    Feld, Vanilla 1) und Min/MaxCooldown (Respawn, Vanilla meist 3/15,
    Nullen bleiben) je Spawner/Rang."""
    spawn_on = _neq(s.artifact_spawn_factor, 1.0)
    rarity_on = _neq(s.artifact_rarity_factor, 1.0)
    count_on = _neq(s.artifact_count_factor, 1.0) and s.artifact_count_factor > 0
    respawn_on = (_neq(s.artifact_respawn_factor, 1.0)
                  and s.artifact_respawn_factor > 0)
    if not (spawn_on or rarity_on or count_on or respawn_on):
        return {}
    patches: dict = {}
    for sid, node in gd.artifactspawners.children.items():
        if sid == "Empty" or "#" in sid:
            continue
        ranks: dict = {}
        for rank, rank_node in node.children.items():
            cfg: dict = {}
            if count_on:
                count = parse_number(rank_node.values.get("Count"))
                if count > 0:
                    new = max(1, int(round(count * s.artifact_count_factor)))
                    if new != int(count):
                        cfg["Count"] = str(new)
            if respawn_on:
                for key in ("MinCooldown", "MaxCooldown"):
                    raw = rank_node.values.get(key)
                    if raw is None or parse_number(raw) <= 0:
                        continue
                    scaled = _scale_literal(raw, 1.0 / s.artifact_respawn_factor)
                    if scaled is not None and scaled != raw.strip():
                        cfg[key] = scaled
            if spawn_on:
                chance = parse_number(rank_node.values.get("SpawnChanceBase"))
                if chance > 0:
                    cfg["SpawnChanceBase"] = _num(
                        min(100.0, chance * s.artifact_spawn_factor)) + "f"
            if rarity_on:
                rarity = rank_node.children.get("RarityChance")
                if rarity is not None:
                    weights = {key: parse_number(rarity.values.get(key))
                               for key in ("Common", "Uncommon", "Rare", "Epic")}
                    total = sum(weights.values())
                    higher = sum(weights[k] for k in ("Uncommon", "Rare", "Epic"))
                    if total > 0 and higher > 0:
                        # Seltene Stufen x Faktor, Common uebernimmt den Rest,
                        # damit die Gesamtsumme (= Ziehungsgewicht) gleich bleibt
                        scale = min(s.artifact_rarity_factor,
                                    total / higher if higher else 1.0)
                        new = {k: weights[k] * scale
                               for k in ("Uncommon", "Rare", "Epic")}
                        new["Common"] = max(0.0, total - sum(new.values()))
                        if any(_neq(new[k], weights[k]) for k in new):
                            cfg["RarityChance"] = {
                                k: _num(v) + "f" for k, v in new.items()}
            if cfg:
                ranks[rank] = cfg
        if ranks:
            patches[sid] = ranks
    return patches


def _mutant_factor(s: Settings, species: str | None, param: str,
                   global_factor: float) -> float:
    """Kaskade Art-Override > globaler Mutanten-Regler."""
    if species is not None:
        value = s.mutant_overrides.get(species, {}).get(param)
        if value is not None:
            return value
    return global_factor


def _mutants_patch(gd: GameData, s: Settings) -> dict:
    hp_on = _neq(s.mutant_hp_factor, 1.0) or any(
        "hp" in p for p in s.mutant_overrides.values())
    speed_on = _neq(s.mutant_speed_factor, 1.0) or any(
        "speed" in p for p in s.mutant_overrides.values())
    regen_on = _neq(s.mutant_regen_factor, 1.0) or any(
        "regen" in p for p in s.mutant_overrides.values())
    protection_on = _neq(s.mutant_protection_factor, 1.0) or any(
        "protection" in p for p in s.mutant_overrides.values())
    patches: dict = {}
    if hp_on:
        for sid, hp in sorted(gd.mutants().items()):
            factor = _mutant_factor(s, gd.mutant_faction(sid), "hp",
                                    s.mutant_hp_factor)
            if _neq(factor, 1.0) and factor > 0:
                # setdefault-Merge: der Regen-Block unten schreibt in
                # DENSELBEN VitalParams-Knoten
                patches.setdefault(sid, {}).setdefault("VitalParams", {})[
                    "MaxHP"] = _num(max(1.0, hp * factor))
    if regen_on:
        # Faktor 0 ist hier ausdruecklich erlaubt (Mutanten heilen nie) —
        # das Gegenstueck zu "NPCs don't self-heal" auf der Menschen-Seite
        for sid, regen in sorted(gd.mutant_regens().items()):
            factor = _mutant_factor(s, gd.mutant_faction(sid), "regen",
                                    s.mutant_regen_factor)
            if _neq(factor, 1.0) and factor >= 0:
                patches.setdefault(sid, {}).setdefault("VitalParams", {})[
                    "RegenHP"] = _num(regen * factor)
    if speed_on:
        for sid, speeds in sorted(gd.mutant_speeds().items()):
            factor = _mutant_factor(s, gd.mutant_faction(sid), "speed",
                                    s.mutant_speed_factor)
            if _neq(factor, 1.0) and factor > 0:
                patches.setdefault(sid, {})["MovementParams"] = {
                    key: _num(value * factor) for key, value in speeds.items()}
    if protection_on:
        # Schutz je Art (06.09.2026, Nexus 'No More Tanky Mutants'): fast nur
        # Strike (Nahkampf), Shot ist ueberall 0 - Faktor auf 0 bleibt 0.
        for sid, values in sorted(gd.mutant_protections().items()):
            factor = _mutant_factor(s, gd.mutant_faction(sid), "protection",
                                    s.mutant_protection_factor)
            if _neq(factor, 1.0) and factor >= 0:
                patches.setdefault(sid, {})["Protection"] = {
                    key: _num(value * factor) for key, value in values.items()}
    return patches


def _mutant_abilities_patch(gd: GameData, s: Settings) -> dict:
    """Attacken-Schaden pro Mutanten-Art (nur via Art-Overrides)."""
    patches: dict = {}
    for species, params in sorted(s.mutant_overrides.items()):
        factor = params.get("damage")
        if factor is None or not _neq(factor, 1.0) or factor <= 0:
            continue
        for sid, (path, value) in sorted(gd.mutant_attack_damages(species).items()):
            node = patches.setdefault(sid, {})
            parts = path.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = _num(value * factor)
    return patches


def _mutant_attack_patch(gd: GameData, s: Settings) -> dict:
    """Angriffe je Serie und Blutungsaufbau der Mutanten.

    `MaxAttacksInSeries` (wie viele Schlaege ein Mutant am Stueck macht,
    Vanilla 0/1/2/3) und `BleedingChanceIncrement` (wie schnell ein
    Treffer die Blutung aufbaut, Vanilla meist .1f). Beides gemessen
    07.09.2026 an 143 Mutanten-Attacken; menschliche und Boss-Attacken
    tragen dieselben Schluessel und bleiben draussen (siehe
    gd.mutant_attack_params). Gefunden in "Stalker Unlimited" (Nexus 1453).

    Vanilla 0 bleibt 0 (eine Attacke ohne Serie bekommt keine), sonst
    mindestens 1 — eine halbe Attacke gibt es nicht. Die Blutung behaelt
    ihre Schreibweise (`.1f` bleibt `.1f`)."""
    want_series = _neq(s.mutant_attack_series_factor, 1.0) and s.mutant_attack_series_factor >= 0
    want_bleed = _neq(s.mutant_attack_bleed_factor, 1.0) and s.mutant_attack_bleed_factor >= 0
    if not (want_series or want_bleed):
        return {}
    keys = ()
    if want_series:
        keys += ("MaxAttacksInSeries",)
    if want_bleed:
        keys += ("BleedingChanceIncrement",)
    patches: dict = {}
    for sid, found in sorted(gd.mutant_attack_params(keys).items()):
        for path, raw in sorted(found.items()):
            parts = path.split(".")
            if parts[-1] == "MaxAttacksInSeries":
                vanilla = parse_number(raw)
                if vanilla <= 0:
                    continue
                new = max(1, int(round(vanilla * s.mutant_attack_series_factor)))
                if new == int(vanilla):
                    continue
                value = str(new)
            else:
                value = _scale_literal(raw, s.mutant_attack_bleed_factor)
                if value is None or value == raw:
                    continue
            node = patches.setdefault(sid, {})
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
    return patches


def _invisibility_patch(gd: GameData, s: Settings) -> dict:
    """Bloodsucker-Tarnung: Tarn-Tempo und Enttarnung durch Treffer."""
    cloak_on = _neq(s.bloodsucker_cloak_factor, 1.0) and s.bloodsucker_cloak_factor > 0
    uncloak_on = _neq(s.bloodsucker_uncloak_factor, 1.0)
    if not (cloak_on or uncloak_on):
        return {}
    patches: dict = {}
    for sid, values in sorted(gd.invisibility_prototypes().items()):
        cfg: dict = {}
        if cloak_on and "ToInvisibleSeconds" in values:
            cfg["ToInvisibleSeconds"] = _num(
                values["ToInvisibleSeconds"] / s.bloodsucker_cloak_factor)
        if uncloak_on and "InvisibilityLossFromDamage" in values:
            cfg["InvisibilityLossFromDamage"] = _num(
                values["InvisibilityLossFromDamage"] * s.bloodsucker_uncloak_factor)
        if cfg:
            patches[sid] = {"InvisibilityFeatureData": cfg}
    return patches


def _melee_patch(gd: GameData, s: Settings) -> dict:
    """Messer + Kolbenschlag (MeleeWeaponPrototypes): Schaden und Reichweite.

    Beide Structs definieren Damage UND HitDetectionDistance selbst
    (Vanilla 160 = 1,6 m fuer Knife wie WeaponButt), also je Struct
    patchen. Reichweite: Nexus "Increased Melee Range" / "Melee and Bash
    Range", Recherche 05.09.2026."""
    want_damage = _neq(s.melee_damage_factor, 1.0) and s.melee_damage_factor > 0
    want_range = _neq(s.melee_range_factor, 1.0) and s.melee_range_factor > 0
    if not (want_damage or want_range):
        return {}
    patches: dict = {}
    for sid in ("Knife", "WeaponButt"):
        entry: dict = {}
        if want_damage:
            value = parse_number(gd.resolve(gd.melee, sid, "Damage"))
            if value > 0:
                entry["Damage"] = _num(value * s.melee_damage_factor)
        if want_range:
            raw = gd.resolve(gd.melee, sid, "HitDetectionDistance")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.melee_range_factor)
                if scaled is not None:
                    entry["HitDetectionDistance"] = scaled
        if entry:
            patches[sid] = entry
    return patches


NPC_FLASHLIGHT_SID = "NPCFlashlight"
NPC_FLASHLIGHT_CONE_CAP = 170.0      # Grad; darueber wird aus dem Kegel eine Kugel


def _sid_of(node) -> str:
    return (node.values.get("SID") or "").strip().rstrip(";").strip()


def _npc_flashlight_node(gd: GameData):
    """(Top-Level-Key, Struct) der NPC-Lampe. Die Structs heissen in der
    Datei nur [0]..[3]; gefunden wird ueber die SID, nicht ueber die
    Position."""
    for key, node in gd.flashlights.children.items():
        if "#" in key:
            continue
        if _sid_of(node) == NPC_FLASHLIGHT_SID:
            return key, node
    return None, None


def _flashlight_patch(gd: GameData, s: Settings) -> dict:
    """NPC-Taschenlampen (FlashlightPrototypes, Recherche 05.09.2026).

    Lichtwerte stehen nur in ExtraLightDistanceBasedParameters: drei
    Eintraege nach Entfernung (Vanilla Intencity 7/9/18, Radius
    175/325/500, Kegel 45/55/80). 1.600 NPC-Prototypen verweisen auf
    diese eine Lampe. Die Spieler-Lampe hat hier keine Werte (leere
    Tabelle; Blueprint-Kurven) - siehe ROADMAP. Array-Regel: komplette
    Eintraege ausgeben. Der Schluessel "Intencity" ist GSCs Schreibweise."""
    want_light = _neq(s.npc_flashlight_factor, 1.0) and s.npc_flashlight_factor > 0
    want_cone = (_neq(s.npc_flashlight_cone_factor, 1.0)
                 and s.npc_flashlight_cone_factor > 0)
    if not (want_light or want_cone):
        return {}
    key, node = _npc_flashlight_node(gd)
    table = node.children.get("ExtraLightDistanceBasedParameters") if node else None
    if key is None or table is None:
        return {}
    entries: dict = {}
    for idx, entry in table.children.items():
        if "#" in idx:
            continue
        distance = parse_number(entry.values.get("Distance"))
        intensity = parse_number(entry.values.get("Intencity"))
        radius = parse_number(entry.values.get("AttenuationRadius"))
        cone = parse_number(entry.values.get("OuterConeAngle"))
        if want_light:
            intensity *= s.npc_flashlight_factor
            radius *= s.npc_flashlight_factor
        if want_cone:
            cone = min(NPC_FLASHLIGHT_CONE_CAP, cone * s.npc_flashlight_cone_factor)
        entries[idx] = {"Distance": _num(distance), "Intencity": _num(intensity),
                        "AttenuationRadius": _num(radius),
                        "OuterConeAngle": _num(cone)}
    if not entries:
        return {}
    return {key: {"ExtraLightDistanceBasedParameters": entries}}


def _weather_patch(gd: GameData, s: Settings) -> dict:
    """Regen-/Sturm-Gewichte, Emissions-Haeufigkeit und (seit 1.25.0) die
    Wetterdauer je Auswahl-Prototyp: WeatherDurationMin/Max jeder Wetterlage
    (500-1200 s) werden skaliert, Literalform bleibt (500.f -> 1000.f)."""
    rain_on = _neq(s.rain_factor, 1.0)
    emission_on = _neq(s.emission_factor, 1.0)
    duration_on = _neq(s.weather_duration_factor, 1.0) and s.weather_duration_factor > 0
    if not (rain_on or emission_on or duration_on or s.regional_weather_overrides):
        return {}
    patches: dict = {}
    root = gd.weatherselection
    for sid, node in root.children.items():
        if "#" in sid:
            continue
        cfg: dict = {}
        if rain_on:
            for wtype in gd.RAIN_WEATHER_TYPES:
                sub = node.children.get(wtype)
                if sub is None:
                    continue
                weight = parse_number(sub.values.get("BlendWeight"))
                if weight > 0:
                    cfg[wtype] = {"BlendWeight": _num(weight * s.rain_factor)}
        if emission_on:
            sub = node.children.get("Emission")
            if sub is not None:
                increase = parse_number(sub.values.get("BlendWeightIncrease"))
                if increase > 0:
                    cfg.setdefault("Emission", {})["BlendWeightIncrease"] = _num(
                        increase * s.emission_factor)
        if duration_on:
            for wtype, sub in node.children.items():
                for key in ("WeatherDurationMin", "WeatherDurationMax"):
                    raw = sub.values.get(key)
                    if raw is None or parse_number(raw) <= 0:
                        continue
                    scaled = _scale_literal(raw, s.weather_duration_factor)
                    if scaled is not None:
                        cfg.setdefault(wtype, {})[key] = scaled
        if cfg:
            if sid.startswith("["):
                # Index-Vorlagen [0]/[1]/[2]/[3]/[35] (Regionen erben per
                # refkey=[1]): komplett ausgeben, siehe _resolved_struct.
                cfg = _merge_nested(_resolved_struct(root, node), cfg)
            patches[sid] = cfg
    return extension_controls.regional_weather.apply(gd, s, patches)


def _bullet_drop_patch(gd: GameData, s: Settings) -> dict:
    """Geschossabfall (06.09.2026, Nexus 'Better Ballistics' & Co.):
    BulletDropHeight steht an den Waffen-Templates (170) und wird von den
    *_Player-Settings geerbt; NPC-Settings setzen 0 und bleiben 0.
    Faktor 0 = flache Flugbahn."""
    if not _neq(s.bullet_drop_factor, 1.0) or s.bullet_drop_factor < 0:
        return {}
    patches: dict = {}
    for sid, node in gd.weaponsettings.children.items():
        if "#" in sid:
            continue
        raw = node.values.get("BulletDropHeight")
        if raw is None:
            continue
        value = parse_number(raw)
        if value > 0:
            patches[sid] = {"BulletDropHeight": _num(value * s.bullet_drop_factor)}
    return patches


def _projectile_patch(gd: GameData, s: Settings) -> dict:
    """Geschoss-Geschwindigkeit (06.09.2026): Speed der Kugel-Projektile
    (20000-42000). Gauss (1e7), RPG (6000) und Granaten (3500) bleiben."""
    speed_on = _neq(s.bullet_speed_factor, 1.0) and s.bullet_speed_factor > 0
    # 1.32.0 (Nr. 15/16): Wanddurchschlag und Maximalreichweite
    pen_on = _neq(s.bullet_penetration_factor, 1.0) and s.bullet_penetration_factor >= 0
    range_on = _neq(s.bullet_range_factor, 1.0) and s.bullet_range_factor > 0
    # 1.35.0: die zweite Haelfte der Durchschlags-Gruppe. `PenetrationSpawnChance`
    # (Chance) hat `PenetrationTraceLenght` (sic, Tippfehler von GSC) im selben
    # Struct - 16x, gemessen 150/200/300. Der Familien-Waechter hat es gemeldet,
    # "Better Ballistics Core" (Nexus 2536) skaliert es.
    depth_on = (_neq(s.bullet_penetration_depth_factor, 1.0)
                and s.bullet_penetration_depth_factor > 0)
    if not (speed_on or pen_on or range_on or depth_on):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.projectiles.children.items()):
        if "#" in sid:
            continue
        cfg: dict = {}
        raw = node.values.get("Speed")
        if speed_on and raw is not None:
            value = parse_number(raw)
            if 10000 <= value < 1_000_000:
                cfg["Speed"] = _num(value * s.bullet_speed_factor)
        if pen_on:
            # Wahrscheinlichkeit 0..1: gedeckelt; Vanilla-0 bleibt 0
            raw = node.values.get("PenetrationSpawnChance")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.bullet_penetration_factor, cap=1.0)
                if scaled is not None and scaled != raw.strip():
                    cfg["PenetrationSpawnChance"] = scaled
        if depth_on:
            raw = node.values.get("PenetrationTraceLenght")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.bullet_penetration_depth_factor)
                if scaled is not None and scaled != raw.strip():
                    cfg["PenetrationTraceLenght"] = scaled
        if range_on:
            raw = node.values.get("MaxFlyDistance")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.bullet_range_factor)
                if scaled is not None and scaled != raw.strip():
                    cfg["MaxFlyDistance"] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _sleep_patch(gd: GameData, s: Settings) -> dict:
    """Schlaf (06.09.2026): DefaultSleepParams - AllowSleepThreshold 50 (die
    Muedigkeit, ab der man schlafen darf; 0 = jederzeit), MinSleepHours 7,
    bAllowEmissionSleep."""
    root = gd.sleepparams
    if root.children.get("DefaultSleepParams") is None:
        return {}
    cfg: dict = {}
    if s.sleep_anytime:
        if parse_number(gd.resolve(root, "DefaultSleepParams", "AllowSleepThreshold")) > 0:
            cfg["AllowSleepThreshold"] = "0"
    live_min = parse_number(gd.resolve(root, "DefaultSleepParams", "MinSleepHours"), 0.0)
    if live_min > 0 and int(s.min_sleep_hours) != int(live_min):
        cfg["MinSleepHours"] = str(max(1, int(s.min_sleep_hours)))
    if s.sleep_in_emission:
        raw = (gd.resolve(root, "DefaultSleepParams", "bAllowEmissionSleep") or "")
        if raw.strip().rstrip(";").strip().lower() != "true":
            cfg["bAllowEmissionSleep"] = "true"
    return {"DefaultSleepParams": cfg} if cfg else {}


def _mutant_hearing_patch(gd: GameData, s: Settings) -> dict:
    """Der eine geteilte MutantsHearingSensor (alle Arten)."""
    if not _neq(s.mutant_hearing_factor, 1.0):
        return {}
    node = gd.hearingsensors.children.get("MutantsHearingSensor")
    events = node.children.get("SoundEvents") if node else None
    if events is None:
        return {}
    entries: dict = {}
    for idx, entry in events.children.items():
        distance = parse_number(entry.values.get("HearingDistance"))
        if distance <= 0:
            continue
        entries[idx] = {
            "Type": entry.values.get("Type", "ESoundEventType::None"),
            "HearingDistance": _num(distance * s.mutant_hearing_factor),
        }
    if not entries:
        return {}
    return {"MutantsHearingSensor": {"SoundEvents": entries}}


def _flair_patch(gd: GameData, s: Settings) -> dict:
    """FlairSensorPrototypes (1.28.0 P4, docs/CORE_SWEEP_RESEARCH.md par. 2.4):
    Witterung der Mutanten. Alle Sensoren mit IsActive = true ausser der
    Tabu-Liste FLAIR_SENSOR_SKIP (live: BlindDog fuer 38 Arten, Chimera,
    Flesh, Poltergeist). Jedes Kind deklariert seine Schluessel selbst; die
    Front*-Schluessel gibt es nur bei BlindDog/Chimera/Flesh -> nur
    vorhandene Schluessel patchen. Der Schalter setzt IsActive = false auf
    dieselben Sensoren. AIGlobals.FlairCoef (Wetter-Regler) gilt weiter."""
    smell_on = _neq(s.mutant_smell_factor, 1.0) and s.mutant_smell_factor > 0
    if not (smell_on or s.mutants_no_smell):
        return {}
    patches: dict = {}
    for sid, node in gd.flairsensors.children.items():
        if sid == "[0]" or "#" in sid or sid in FLAIR_SENSOR_SKIP:
            continue
        if _bool_literal(node.values.get("IsActive")) is not True:
            continue
        cfg: dict = {}
        if s.mutants_no_smell:
            cfg["IsActive"] = "false"
        if smell_on:
            for key in FLAIR_SENSOR_KEYS:
                raw = node.values.get(key)
                if raw is None or parse_number(raw) <= 0:
                    continue
                scaled = _scale_literal(raw, s.mutant_smell_factor)
                if scaled is not None:
                    cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _needs_patch(gd: GameData, s: Settings) -> dict:
    """NPCNeedsPresetPrototypes (1.28.0 P5, docs/CORE_SWEEP_RESEARCH.md par. 2.6):
    A-Life-Trupp-Ausbreitung. GoalNeeds-Eintraege mit NeedTag AI.Need.Expansion
    (16 Presets, jeder deklariert seinen Eintrag selbst; Auswahl ueber den
    NeedTag, NICHT den Index - MutantGeneric hat ihn unter [1]):
    Min/MaxIncreasePerMinute x Faktor, Array-Eintrag KOMPLETT ausgegeben.
    AI.Need.ReuniteWithLair (inert) bleibt unangetastet."""
    expansion_on = _neq(s.squad_expansion_factor, 1.0) and s.squad_expansion_factor > 0
    camp_on = _neq(s.camp_life_factor, 1.0) and s.camp_life_factor > 0
    if not (expansion_on or camp_on):
        return {}
    patches: dict = {}
    for sid, node in gd.needspresets.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        cfg: dict = {}
        goals = node.children.get("GoalNeeds")
        if expansion_on and goals is not None:
            entries: dict = {}
            for idx, entry in goals.children.items():
                if entry.values.get("NeedTag", "").strip() != "AI.Need.Expansion":
                    continue
                full = {k: v.strip() for k, v in entry.values.items()}
                changed = False
                for key in ("MinIncreasePerMinute", "MaxIncreasePerMinute"):
                    raw = entry.values.get(key)
                    if raw is None or parse_number(raw) <= 0:
                        continue
                    scaled = _scale_literal(raw, s.squad_expansion_factor)
                    if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                        full[key] = scaled
                        changed = True
                if changed:
                    entries[idx] = full
            if entries:
                cfg["GoalNeeds"] = entries
        # 1.28.0 P6 (Lagerleben, par. 2.6, 25 echte Presets - das Dokument
    # zaehlt 26 inklusive der Basis [0], die hier uebersprungen wird):
    # Gitarre, Witze, Gespraeche,
        # Rauchen, Schlafen, Essen, Rasten, Trinken - Auswahl ueber den
        # NeedType, Eintrag komplett (NeedType, Min, Max, Radius, MaxCount).
        needs = node.children.get("Needs")
        if camp_on and needs is not None:
            entries = {}
            for idx, entry in needs.children.items():
                if (entry.values.get("NeedType") or "").strip() not in CAMP_LIFE_NEEDS:
                    continue
                full = {k: v.strip() for k, v in entry.values.items()}
                changed = False
                for key in ("IncreaseRateMin", "IncreaseRateMax"):
                    raw = entry.values.get(key)
                    if raw is None or parse_number(raw) <= 0:
                        continue
                    scaled = _scale_literal(raw, s.camp_life_factor)
                    if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                        full[key] = scaled
                        changed = True
                if changed:
                    entries[idx] = full
            if entries:
                cfg["Needs"] = entries
        if cfg:
            patches[sid] = cfg
    return patches


def _alife_policy_patch(gd: GameData, s: Settings) -> dict:
    """ALifePolicyPrototypes (1.28.0 P5, par. 2.7): das eine Struct Default.
    Refill-Cooldowns (360.f/120.f) x Faktor, Refill-Distanzband (20000/25000,
    ganzzahlig, Min <= Max) x Faktor, MaxCorpsePerRadius (30) absolut.
    TriggerExtinction/StopExtinction (globaler Agenten-Deckel) sind tabu."""
    node = gd.alifepolicy.children.get("Default")
    if node is None:
        return {}
    cfg: dict = {}
    if _neq(s.refill_cooldown_factor, 1.0) and s.refill_cooldown_factor > 0:
        for key in ("FullWipeRefillCooldown", "PartialWipeRefillCooldown"):
            raw = node.values.get(key)
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.refill_cooldown_factor)
                if scaled is not None:
                    cfg[key] = scaled
    if _neq(s.refill_distance_factor, 1.0) and s.refill_distance_factor > 0:
        raw_min = node.values.get("MinRefillDistance")
        raw_max = node.values.get("MaxRefillDistance")
        if (raw_min is not None and raw_max is not None
                and parse_number(raw_min) > 0 and parse_number(raw_max) > 0):
            new_max = max(1, int(round(parse_number(raw_max) * s.refill_distance_factor)))
            new_min = min(max(1, int(round(parse_number(raw_min) * s.refill_distance_factor))), new_max)
            for key, raw, new in (("MinRefillDistance", raw_min, new_min),
                                  ("MaxRefillDistance", raw_max, new_max)):
                if new != int(round(parse_number(raw))):
                    cfg[key] = str(new)
    raw = node.values.get("MaxCorpsePerRadius")
    if raw is not None and parse_number(raw, -1.0) >= 0:
        wanted = max(1, int(s.corpse_budget))
        if wanted != int(round(parse_number(raw))):
            cfg["MaxCorpsePerRadius"] = str(wanted)
    return {"Default": cfg} if cfg else {}


def _alife_faction_patch(gd: GameData, s: Settings) -> dict:
    """ALifePopulationManagerFactionPrototypes (1.28.0 P5, par. 2.7): das eine
    Struct ALifePopulationManagerPreset. ALifeLairExpansionBattleChance (50)
    absolut auf alle 29 benannten Fraktions-Kinder (bpatch je Fraktion, nur bei
    Abweichung), ALifeLairExpansionTime (50.f) INVERS x Faktor - Einheit
    unbewiesen, darum experimentell. Die Lagerbaender MinLairs/MaxLairs sind
    tabu."""
    node = gd.alifefactions.children.get("ALifePopulationManagerPreset")
    if node is None:
        return {}
    cfg: dict = {}
    factions = node.children.get("Factions")
    wanted = max(0, min(100, int(s.faction_battle_chance)))
    if factions is not None:
        sub: dict = {}
        for name, fac in factions.children.items():
            if "#" in name:
                continue
            raw = fac.values.get("ALifeLairExpansionBattleChance")
            if raw is None:
                continue
            if wanted != int(round(parse_number(raw))):
                sub[name] = {"ALifeLairExpansionBattleChance": str(wanted)}
        if sub:
            cfg["Factions"] = sub
    if _neq(s.faction_expansion_pace_factor, 1.0) and s.faction_expansion_pace_factor > 0:
        raw = node.values.get("ALifeLairExpansionTime")
        if raw is not None and parse_number(raw) > 0:
            scaled = _scale_literal(raw, 1.0 / s.faction_expansion_pace_factor)
            if scaled is not None:
                cfg["ALifeLairExpansionTime"] = scaled
    return {"ALifePopulationManagerPreset": cfg} if cfg else {}


def _barbedwire_patch(gd: GameData, s: Settings) -> dict:
    """BarbedWirePrototypes (1.28.0 P6, par. 2.2): beide echten Prototypen
    (Limiting/Overlappable) deklarieren alle Werte selbst; welcher Zaun
    welchen nutzt, steht in den Levels -> beide patchen. [0] Empty bleibt
    die unbenutzte Basis. BleedingChance ist eine Wahrscheinlichkeit
    (Deckel 1.0), die drei anderen sind Schadenswerte."""
    if not (_neq(s.barbed_wire_factor, 1.0) and s.barbed_wire_factor >= 0):
        return {}
    patches: dict = {}
    for sid, node in gd.barbedwire.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        cfg: dict = {}
        for key, cap in (("Damage", None), ("BleedingValue", None),
                         ("ArmorDamage", None), ("BleedingChance", 1.0)):
            raw = node.values.get(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, s.barbed_wire_factor, cap=cap)
            if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _destructible_patch(gd: GameData, s: Settings) -> dict:
    """DestructibleObjectPrototypes (1.28.0 P6, par. 2.10): explodierende
    Behaelter. Die Struct-Schluessel sind Indizes [N], erkannt wird ueber die
    SID (Exp_* / *_Exp_*: Gasflaschen, Kanister, Fass, dazu die Quest- und
    Static-Varianten - live 22 Stueck). Gepatcht wird nur
    ObjectPhaseSettings.[0].DamageDestroyThreshold; der Phasen-Eintrag wird
    mit allen seinen Skalaren ausgegeben (die Unter-Arrays IgnoredDamageTypes
    und DestructibleActions bleiben ausdruecklich draussen - sie tragen
    Mesh-, VFX- und Sound-Pfade, die zu duplizieren mehr Risiko als Nutzen
    braechte). Die 536-KB-Datei wird nur bei aktivem Regler geparst."""
    if not (_neq(s.explosive_container_factor, 1.0) and s.explosive_container_factor > 0):
        return {}
    patches: dict = {}
    for key, node in gd.destructibles.children.items():
        if "#" in key:
            continue
        sid = (node.values.get("SID") or "").strip()
        if not (sid.startswith("Exp_") or "_Exp_" in sid):
            continue
        phases = node.children.get("ObjectPhaseSettings")
        if phases is None:
            continue
        entries: dict = {}
        for idx, phase in phases.children.items():
            raw = phase.values.get("DamageDestroyThreshold")
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, s.explosive_container_factor)
            if scaled is None or not _neq(parse_number(scaled), parse_number(raw)):
                continue
            full = {k: v.strip() for k, v in phase.values.items()}
            full["DamageDestroyThreshold"] = scaled
            entries[idx] = full
        if entries:
            patches[key] = {"ObjectPhaseSettings": entries}
    return patches


def _physics_patch(gd: GameData, s: Settings) -> dict:
    """PhysicsInteractionPrototypes (1.28.0 P6, par. 2.11): wie hart der
    Spieler Gegenstaende und Leichen anschiebt. Alle 88 Prototypen tragen
    ihren eigenen PlayerPushImpulse (20.0 Laborglas bis 27000.0 Munitionskiste,
    Leiche 3500.0)."""
    if not (_neq(s.push_force_factor, 1.0) and s.push_force_factor >= 0):
        return {}
    patches: dict = {}
    for sid, node in gd.physicsinteractions.children.items():
        if "#" in sid:
            continue
        raw = node.values.get("PlayerPushImpulse")
        if raw is None or parse_number(raw) <= 0:
            continue
        scaled = _scale_literal(raw, s.push_force_factor)
        if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
            patches[sid] = {"PlayerPushImpulse": scaled}
    return patches


def _weatherchain_patch(gd: GameData, s: Settings) -> dict:
    """WeatherChainPrototypes (1.28.0 P6, par. 2.11): wie lange ein
    Wetterwechsel dauert. Zwei Array-Ebenen (TransitionSteps.[i] ->
    WeatherChains.[j]), beide werden komplett ausgegeben; der Regler wirkt
    INVERS (200 % = halber Multiplikator = schnellerer Wechsel).
    WeatherChainWeight wird nur mitgeschrieben, nie veraendert."""
    if not (_neq(s.weather_transition_factor, 1.0) and s.weather_transition_factor > 0):
        return {}
    factor = 1.0 / s.weather_transition_factor
    patches: dict = {}
    for sid, node in gd.weatherchains.children.items():
        if "#" in sid:
            continue
        steps = node.children.get("TransitionSteps")
        if steps is None:
            continue
        step_entries: dict = {}
        for si, step in steps.children.items():
            chains = step.children.get("WeatherChains")
            if chains is None:
                continue
            chain_entries: dict = {}
            for ci, chain in chains.children.items():
                raw = chain.values.get("WeatherTransitionTimeMultiplier")
                if raw is None or parse_number(raw) <= 0:
                    continue
                scaled = _scale_literal(raw, factor)
                if scaled is None or not _neq(parse_number(scaled), parse_number(raw)):
                    continue
                full = {k: v.strip() for k, v in chain.values.items()}
                full["WeatherTransitionTimeMultiplier"] = scaled
                chain_entries[ci] = full
            if chain_entries:
                full_step = {k: v.strip() for k, v in step.values.items()}
                full_step["WeatherChains"] = chain_entries
                step_entries[si] = full_step
        if step_entries:
            patches[sid] = {"TransitionSteps": step_entries}
    return patches


def _singleton_patch(gd: GameData, s: Settings) -> dict:
    """SingletonConstants (1.28.0 P6, par. 2.8, unbinarisiert wie CoreVariables):
    Mond, Sonne, Sterne, Wolken und die Daemmerungsdauer im TimeManager.
    Latitude/Longitude/TimeZone/NorthOffsetAngle (Sonnenbahn) und die
    Start*-Schluessel (neues Spiel) sind tabu. Die Datei wurde nie zuvor
    gepatcht und die Schluessel stehen nicht in der Namenstabelle der EXE -
    Wirkung voellig ungetestet, der Tooltip sagt es."""
    node = gd.singletonconstants.children.get("TimeManager")
    if node is None:
        return {}
    cfg: dict = {}
    for field_name, key, cap in SKY_KEYS:
        factor = getattr(s, field_name)
        if not (_neq(factor, 1.0) and factor >= 0):
            continue
        raw = node.values.get(key)
        if raw is None or parse_number(raw) <= 0:
            continue
        scaled = _scale_literal(raw, factor, cap=cap)
        if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
            cfg[key] = scaled
    return {"TimeManager": cfg} if cfg else {}


def _artifact_behaviour_patch(gd: GameData, s: Settings) -> dict:
    """Artefakt-Verhalten in ItemPrototypes (1.28.0 P7, docs/CORE_SWEEP_RESEARCH.md
    par. 3b). Live gemessen: 154 Artefakt-Structs, und JEDES deklariert Radius,
    Strafe, PlayerDistance und JumpSeriesDelay selbst (auch TemplateArtifact) -
    also wird jedes einzeln gepatcht, nie nur die Vorlage.

    - Radius (147x 40.0, 7x 10): wie nah man ran muss, damit ein Artefakt
      sichtbar wird. Deutung aus dem Recherche-Dokument ("sehr wahrscheinlich",
      Vorbild Nexus "Less Shy Artifacts") - der Tooltip sagt es.
    - Strafe (146 true / 8 false): der Schalter setzt NUR die true-Artefakte auf
      false, die acht Weird-/Quest-Artefakte bleiben, wie sie sind.
    - PlayerDistance (153x 1000.0, 1x 100000.0 bei QuestArtifactCrystalThorn) und
      JumpSeriesDelay (45/35/25/15, dazu 2x 0.0 und 1x 0.5): Faktoren; 0 bleibt 0.

    Der Editions-Zweig (DLCGameData) enthaelt KEINE Artefakte - gemessen: null
    Radius- und null Strafe-Schluessel in allen drei Editions-Dateien -, darum
    gibt es hier anders als beim Artefakt-Slot-Regler keinen DLC-Pfad.

    ⚠ **1.35.0: die Huepf-Familie ist jetzt vollstaendig.** Der Familien-
    Waechter hatte gemeldet, dass wir nur die Haelfte anfassen. Nachgemessen
    am 08.09.2026, alle 154 Artefakte deklarieren auch diese selbst:
    `JumpAmount` (3/5/7/9, dazu 2x 0), `JumpDelay` (6.0/3.0 - die Pause
    ZWISCHEN den Spruengen einer Serie, waehrend `JumpSeriesDelay` zwischen
    den Serien liegt), `JumpForce` 15.0, `JumpDistance` 1500, `JumpHeight`
    100 und `ReturnDistanceValue` 10000 (1x 100000). Eingefaltet statt neue
    Regler zu erfinden: JumpDelay laeuft im Pausen-Regler mit, die
    Rueckkehr-Distanz im Abstands-Regler; neu sind nur zwei Regler
    (Sprungweite = Distanz/Hoehe/Kraft, Spruenge je Serie) und der Schalter
    "ohne Detektor sichtbar" (`DetectorRequired`, 147x true / 7x false)."""
    radius_on = _neq(s.artifact_radius_factor, 1.0) and s.artifact_radius_factor > 0
    keep_on = _neq(s.artifact_keepaway_factor, 1.0) and s.artifact_keepaway_factor > 0
    pause_on = _neq(s.artifact_hop_pause_factor, 1.0) and s.artifact_hop_pause_factor > 0
    dist_on = (_neq(s.artifact_hop_distance_factor, 1.0)
               and s.artifact_hop_distance_factor > 0)
    count_on = (_neq(s.artifact_hop_count_factor, 1.0)
                and s.artifact_hop_count_factor >= 0)
    if not (radius_on or keep_on or pause_on or dist_on or count_on
            or s.artifacts_no_hop or s.artifacts_no_detector):
        return {}
    patches: dict = {}
    for sid, node in gd.items.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        # Artefakt = eigener Strafe-Schluessel; das ist zugleich der Beleg,
        # dass der Struct die Huepf-Familie selbst deklariert.
        if "Strafe" not in node.values:
            continue
        cfg: dict = {}
        if s.artifacts_no_hop and _bool_literal(node.values.get("Strafe")) is True:
            cfg["Strafe"] = "false"
        if (s.artifacts_no_detector
                and _bool_literal(node.values.get("DetectorRequired")) is True):
            cfg["DetectorRequired"] = "false"
        for on, key, factor in (
                (radius_on, "Radius", s.artifact_radius_factor),
                (keep_on, "PlayerDistance", s.artifact_keepaway_factor),
                (keep_on, "ReturnDistanceValue", s.artifact_keepaway_factor),
                (pause_on, "JumpSeriesDelay", s.artifact_hop_pause_factor),
                (pause_on, "JumpDelay", s.artifact_hop_pause_factor),
                (dist_on, "JumpDistance", s.artifact_hop_distance_factor),
                (dist_on, "JumpHeight", s.artifact_hop_distance_factor),
                (dist_on, "JumpForce", s.artifact_hop_distance_factor)):
            if not on:
                continue
            raw = node.values.get(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                cfg[key] = scaled
        if count_on:
            # Spruenge je Serie: ganzzahlig, 0 bleibt 0 (zwei Artefakte
            # huepfen vanilla gar nicht), sonst mindestens einer.
            raw = node.values.get("JumpAmount")
            value = parse_number(raw) if raw is not None else 0.0
            if raw is not None and value > 0:
                new = max(1, int(round(value * s.artifact_hop_count_factor)))
                if new != int(round(value)):
                    cfg["JumpAmount"] = str(new)
        if cfg:
            patches[sid] = cfg
    return patches


def _packofitems_patch(gd: GameData, s: Settings) -> dict:
    """PackOfItemsGroupPrototypes (1.28.0 P7, par. 2.12): die handplatzierten
    Welt-Loot-Haufen. Die Gruppe ArtifactUncommon hat neun Weltvorkommen, aber
    alle 20 Eintraege stehen auf Weight 0 - im Spiel also leere Verstecke.
    Der Schalter hebt genau diese 20 auf 1 und laesst alles andere in der Datei
    unangetastet (die Rang-Sperren der uebrigen 46 Gruppen sind tabu).
    Array-Eintraege werden komplett ausgegeben (ItemPrototypeSID + Weight).
    Ob eine Gruppe mit Gewicht 0 ueberhaupt je gezogen wird, ist unbewiesen -
    darum experimentell."""
    if not s.artifact_caches_drop:
        return {}
    group = gd.packofitems.children.get("ArtifactUncommon")
    if group is None:
        return {}
    settings: dict = {}
    for si, setting in (group.children.get("PackOfItemsSettings").children.items()
                        if group.children.get("PackOfItemsSettings") else ()):
        items = setting.children.get("Items")
        if items is None:
            continue
        entries: dict = {}
        for ii, entry in items.children.items():
            raw = entry.values.get("Weight")
            if raw is None or parse_number(raw) != 0:
                continue                      # nur die abgeschalteten Eintraege
            full = {k: v.strip() for k, v in entry.values.items()}
            full["Weight"] = "1"
            entries[ii] = full
        if entries:
            settings[si] = {"Items": entries}
    return {"ArtifactUncommon": {"PackOfItemsSettings": settings}} if settings else {}


def _npc_trader_patch(gd: GameData, s: Settings) -> dict:
    """NPCPrototypes (1.28.0 P8, docs/CORE_SWEEP_RESEARCH.md par. 2.9): die
    Haendler tragen NEBEN ihren TradePrototypes-Werten eigene Zahlen am
    NPC-Struct, die die Preisregler bisher nie angefasst haben. Gemessen:
    genau neun NPCs mit `BuyCoefficient` 0.8 UND `SellCoefficient` 2.0
    (dieselbe Neunermenge), und 22 Structs mit `Money` > 0 (16x 20000,
    4x 10, 1x 10000, 1x 5). Welche Zahl das Spiel am Ende nimmt - die des
    Handelsprototyps oder die des NPC - ist unbewiesen; darum bekommen beide
    denselben Faktor, was im schlechtesten Fall wirkungslos ist und im besten
    eine Luecke schliesst. Die 1.8-MB-Datei wird nur bei aktivem Regler
    geparst; alle Struct-Schluessel sind Namen, keine Indizes."""
    buy_on = _neq(s.trader_buy_price_factor, 1.0) and s.trader_buy_price_factor > 0
    sell_on = _neq(s.trader_sell_price_factor, 1.0) and s.trader_sell_price_factor > 0
    money_on = _neq(s.trader_money_factor, 1.0) and s.trader_money_factor > 0
    if not (buy_on or sell_on or money_on):
        return {}
    patches: dict = {}
    for sid, node in gd.npcprototypes.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        cfg: dict = {}
        for on, key, factor in ((buy_on, "BuyCoefficient", s.trader_buy_price_factor),
                                (sell_on, "SellCoefficient", s.trader_sell_price_factor)):
            if not on:
                continue
            raw = node.values.get(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                cfg[key] = scaled
        if money_on:
            raw = node.values.get("Money")
            value = parse_number(raw, 0.0) if raw is not None else 0.0
            if value > 0:
                new = max(0, int(round(value * s.trader_money_factor)))
                if new != int(round(value)):
                    cfg["Money"] = str(new)
        if cfg:
            patches[sid] = cfg
    return patches


def _npc_marker_patch(gd: GameData, s: Settings) -> dict:
    """Haendler, Techniker, Medics und Fuehrer auf der Karte anzeigen (1.35.0).

    Kein neuer Inhalt, nur eine Fahne: **80 NPCs tragen in Vanilla bereits
    einen Marker-TYP** (`NPCMarker` = Trader 34, Technician 18, Guider 14,
    Medic 14), aber ihre Anzeige-Fahne `UpdateMarkerOnMap` steht auf false —
    nur acht Ausnahmen stehen auf true (gemessen 08.09.2026). Der Schalter
    legt genau diese 80 um; NPCs mit `NPCMarker = Empty` (1265 Stueck)
    bleiben unangetastet, es taucht also niemand neu auf, der nicht schon
    ein Symbol haette.

    ⚠ Der Vanilla-Wert steht als `false;` mit Semikolon in der Datei —
    darum wird vor dem Vergleich abgeschnitten, sonst wuerde jeder Eintrag
    als "abweichend" gelten.

    Idee aus "Shay's Living Zone" (Nexus 1301, Trackermap-Teil); die Zahlen
    stammen aus unserer eigenen Messung, nicht aus deren Dateien. Die
    1,8-MB-Datei wird nur bei aktivem Schalter geparst."""
    if not s.traders_on_map:
        return {}
    patches: dict = {}
    for sid, node in gd.npcprototypes.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        marker = (node.values.get("NPCMarker") or "").strip().rstrip(";").strip()
        if not marker or marker.split("::")[-1] in ("", "Empty"):
            continue
        flag = (node.values.get("UpdateMarkerOnMap") or "").strip().rstrip(";").strip()
        if flag.lower() == "true":
            continue                      # steht schon an
        patches[sid] = {"UpdateMarkerOnMap": "true"}
    return patches


def _difficulty_patch(gd: GameData, s: Settings) -> dict:
    patches: dict = {}

    def apply(group: str, key: str, factor: float):
        if not _neq(factor, 1.0):
            return
        for sid, vanilla in gd.difficulty_values(f"{group}.{key}").items():
            patches.setdefault(sid, {}).setdefault(group, {})[key] = _num(vanilla * factor)

    apply("EnvironmentDifficulty", "Weapon_BaseDamage", s.player_damage_factor)
    apply("NPCCombatDifficulty", "PlayerWeapon_HeadshotMultiplier", s.headshot_factor)
    apply("NPCCombatDifficulty", "NPC_Weapon_BaseDamage", s.npc_damage_factor)
    apply("NPCCombatDifficulty", "NPC_HP", s.npc_hp_factor)
    apply("MutantCombatDifficulty", "Mutant_BaseDamage", s.mutant_damage_factor)
    apply("EnvironmentDifficulty", "Explosion_BaseDamage", s.explosion_damage_factor)
    apply("EnvironmentDifficulty", "Armor_Durability", s.armor_durability_factor)
    apply("NPCCombatDifficulty", "NPC_AttackCooldown", s.npc_attack_cooldown_factor)
    apply("MutantCombatDifficulty", "Mutant_AttackCooldown",
          s.mutant_attack_cooldown_factor)
    # Additiv: NPC-Waffenprofile um n Raenge anheben (Vanilla 0 ueberall)
    rank_add = int(round(s.npc_weapon_rank_add))
    if rank_add > 0:
        for sid, vanilla in gd.difficulty_values(
                "NPCCombatDifficulty.NPC_Weapon_Rank_Add").items():
            patches.setdefault(sid, {}).setdefault("NPCCombatDifficulty", {})[
                "NPC_Weapon_Rank_Add"] = str(int(vanilla) + rank_add)
    apply("NPCCombatDifficulty", "Weapon_JammingMultiplier", s.jamming_factor)
    apply("EnvironmentDifficulty", "Anomaly_Damage", s.anomaly_damage_factor)
    apply("EnvironmentDifficulty", "Radiation_AccumulationSpeed", s.radiation_factor)
    apply("EnvironmentDifficulty", "Effect_Bleeding", s.bleeding_factor)
    apply("EconomyDifficulty", "Upgrade_Cost", s.upgrade_cost_factor)
    apply("EconomyDifficulty", "Reward_MainLine_Money", s.quest_reward_factor)
    apply("EconomyDifficulty", "Reward_SideLine_Money", s.quest_reward_factor)
    apply("EconomyDifficulty", "Weapon_Cost", s.weapon_price_factor)
    apply("EconomyDifficulty", "Armor_Cost", s.armor_price_factor)
    # HUD-Elemente (06.09.2026): die vier bShouldDisable*-Schalter je
    # Schwierigkeitsgrad (Master: alle true). 1 = immer an (false), 2 = immer
    # aus (true), 0 = wie der Grad es vorgibt. Nur Abweichungen.
    for level, key in ((s.hud_compass, "bShouldDisableCompass"),
                       (s.hud_crosshair, "bShouldDisableCrosshair"),
                       (s.hud_body_markers, "bShouldDisableDeadBodyMarkers"),
                       (s.hud_stash_markers, "bShouldDisableStashMarkers")):
        if int(level) not in (1, 2):
            continue
        wanted = "false" if int(level) == 1 else "true"
        for sid in gd.difficulty.children:
            if sid == "[0]" or "#" in sid:
                continue
            raw = gd.resolve(gd.difficulty, sid, f"EnvironmentDifficulty.{key}")
            if raw is None:
                continue
            if raw.strip().rstrip(";").strip().lower() != wanted:
                patches.setdefault(sid, {}).setdefault("EnvironmentDifficulty", {})[key] = wanted
    apply("EconomyDifficulty", "Ammo_Cost", s.ammo_price_factor)
    apply("EconomyDifficulty", "Artifact_Cost", s.artifact_price_factor)
    apply("EconomyDifficulty", "Consumable_Cost", s.consumable_price_factor)
    # 1.27.0
    apply("NPCCombatDifficulty", "HipAccuracyMultiplier", s.npc_hip_accuracy_factor)
    apply("EconomyDifficulty", "Binoculars_Cost", s.device_price_factor)
    apply("EconomyDifficulty", "NightVisionGoggles_Cost", s.device_price_factor)
    if _neq(s.damage_mercy_factor, 1.0) and s.damage_mercy_factor >= 0:
        # nur selbst definierte Werte, Deckel 1.0 (Easy/Custom stehen schon auf 1)
        for sid, node in gd.difficulty.children.items():
            if sid == "[0]" or "#" in sid:
                continue
            combat = node.children.get("NPCCombatDifficulty")
            if combat is None:
                continue
            for key in ("AccumulatedDamageReductionCurveWeightMin",
                        "AccumulatedDamageReductionCurveWeightMax"):
                raw = combat.values.get(key)
                value = parse_number(raw)
                if raw is None or value <= 0:
                    continue
                new = min(1.0, value * s.damage_mercy_factor)
                if _neq(new, value):
                    patches.setdefault(sid, {}).setdefault("NPCCombatDifficulty", {})[key] = _num(new)
    if _neq(s.psy_phantom_factor, 1.0) and s.psy_phantom_factor >= 0:
        for sid, node in gd.difficulty.children.items():
            if sid == "[0]" or "#" in sid:
                continue
            combat = node.children.get("NPCCombatDifficulty")
            overrides = combat.children.get("PsyPhantomNPCOverrides") if combat is not None else None
            if overrides is None:
                continue
            rows: dict = {}
            for idx, entry in overrides.children.items():
                raw = entry.values.get("PsyPhantomNPCCountMultiplier")
                if raw is not None and parse_number(raw) > 0:
                    rows[idx] = {"PsyPhantomNPCCountMultiplier": _num(parse_number(raw) * s.psy_phantom_factor)}
            if rows:
                patches.setdefault(sid, {}).setdefault("NPCCombatDifficulty", {})[
                    "PsyPhantomNPCOverrides"] = rows
    return patches


def _weapon_factor(s: Settings, category: str | None, wgs_sid: str,
                   param: str, global_factor: float = 1.0) -> float:
    """Kaskade Einzelwaffe > Kategorie > globaler Regler."""
    value = s.weapon_overrides.get(wgs_sid, {}).get(param)
    if value is None and category is not None:
        value = s.weapon_category_factors.get(category, {}).get(param)
    if value is None:
        value = global_factor
    return value


def _weapon_settings_patch(gd: GameData, s: Settings) -> dict:
    """CharacterWeaponSettings: Schaden, Streuung, Abnutzung (Kaskade).

    Mehrere Waffen koennen sich EIN CWS-Struct teilen (AK74-Familie ->
    GunAK74_ST_Player) und Unikate heissen *_Player_WS — daher wird pro
    CWS-Struct ueber ALLE darauf zeigenden Waffen kaskadiert: irgendein
    Einzelwaffen-Override gewinnt, sonst irgendein Kategorie-Faktor,
    sonst der globale Regler (letzterer wie bisher nur fuer klassische
    *_Player-Structs). Schaden hat keinen globalen per-Waffe-Regler
    (global wirkt der Difficulty-Multiplikator Weapon_BaseDamage und
    multipliziert sich im Spiel mit Kategorie/Einzelwaffe)."""
    by_cws: dict[str, list[tuple[str, str | None]]] = {}
    for wgs, (cat, cws) in sorted(gd.player_weapons().items()):
        if cws:
            by_cws.setdefault(cws, []).append((wgs, cat))

    sids = set(by_cws)
    sids.update(sid for sid in gd.weaponsettings.children
                if "_Player" in sid and "#" not in sid)

    def factor_for(sid: str, param: str, global_factor: float) -> float:
        refs = by_cws.get(sid)
        if not refs:
            wgs = sid.replace("_Player", "")
            refs = [(wgs, gd.weapon_category(wgs))]
        for wgs, _cat in refs:
            value = s.weapon_overrides.get(wgs, {}).get(param)
            if value is not None:
                return value
        for _wgs, cat in refs:
            if cat is not None:
                value = s.weapon_category_factors.get(cat, {}).get(param)
                if value is not None:
                    return value
        return global_factor if "_Player" in sid else 1.0

    patches: dict = {}
    for sid in sorted(sids):
        if "#" in sid or sid not in gd.weaponsettings.children:
            continue

        def scaled(key: str, factor: float, invert: bool = False):
            # 0 ist fuer spread/recoil erlaubt (Regler bis 0 %); nur
            # invertierte Werte (Teilung) und negative Faktoren bleiben tabu
            if (not _neq(factor, 1.0) or factor < 0
                    or (invert and factor <= 0)):
                return
            value = parse_number(gd.resolve(gd.weaponsettings, sid, key))
            if value > 0:
                patches.setdefault(sid, {})[key] = _num(
                    value / factor if invert else value * factor)

        scaled("DurabilityDamagePerShot",
               factor_for(sid, "durability", s.durability_factor), invert=True)
        scaled("DispersionRadius", factor_for(sid, "spread", s.spread_factor))
        scaled("BaseDamage", factor_for(sid, "damage", 1.0))

        range_factor = factor_for(sid, "range", s.weapon_range_factor)
        for key in WEAPON_RANGE_KEYS:
            scaled(key, range_factor)

        # Bleeding darf auch auf 0 (nie bluten) — daher ohne scaled()-Guard
        bleed_factor = factor_for(sid, "bleeding", s.weapon_bleeding_factor)
        if _neq(bleed_factor, 1.0) and bleed_factor >= 0:
            value = parse_number(gd.resolve(gd.weaponsettings, sid, "BaseBleeding"))
            if value > 0:
                patches.setdefault(sid, {})["BaseBleeding"] = _num(value * bleed_factor)
            # ChanceBleedingPerShot ist ein %-Literal ("10%")
            raw = gd.resolve(gd.weaponsettings, sid, "ChanceBleedingPerShot")
            if raw is not None:
                scaled_raw = _scale_literal(raw, bleed_factor)
                if scaled_raw is not None and scaled_raw != raw.strip():
                    patches.setdefault(sid, {})["ChanceBleedingPerShot"] = scaled_raw

        # Anzeigebalken im Inventar (1.31.0). Sie sind reine Deko: das
        # Spiel rechnet sie NIE aus den echten Werten aus, sie stehen als
        # feste Zahlen 0..1 an jedem CWS-Struct (gemessen: 150 Structs,
        # Maximum genau 1.0). Darum ziehen sie hier mit demselben Faktor
        # mit wie der echte Wert, gedeckelt bei 1.0. Angeboten werden nur
        # die drei sauber zuordenbaren Balken — Accuracy und Handling sind
        # Mischwerte aus Streuung, Rueckstoss und Gewicht, fuer die es
        # keine ehrliche Formel gibt. Ausloeser: der Nexus-Bericht von
        # Ygracael (03.09.), bis 1.30.0 nur ein FAQ-Eintrag.
        # 1.33.0: Schaden und Durchschlag auf Extremdistanz. Gefunden beim
        # Gegenlesen von Maklane (241) und Stalker Unlimited (1453), die
        # beide daran drehen. Gemessen: `MinBulletDistanceDamageModifier`
        # steht 150x zwischen 0.1 und 0.6 (= so viel Schaden bleibt jenseits
        # der Abfalldistanz uebrig), `MinBulletDistanceArmorPiercingModifier`
        # 150x auf 1.0. Bewusst NICHT im Reichweiten-Regler: der verschiebt
        # die Distanzen, das hier ist der Boden dahinter (steht so seit der
        # Recherche vom 04.09. in der ROADMAP).
        if _neq(s.far_damage_factor, 1.0) and s.far_damage_factor >= 0:
            # Beide Deckel 1.0: der Wert ist ein ANTEIL des Nahwerts, und 1.0
            # heisst bereits "kein Verlust auf Distanz". Darueber hinaus
            # waere ein Schuss auf 300 m durchschlagskraeftiger als aus
            # 5 m - nicht erklaerbar, also gedeckelt. Vanilla steht beim
            # Durchschlag ueberall auf 1.0, dort wirkt der Regler also nur
            # nach unten (steht so im Tooltip).
            for key, cap in (("MinBulletDistanceDamageModifier", 1.0),
                             ("MinBulletDistanceArmorPiercingModifier", 1.0)):
                raw = gd.resolve(gd.weaponsettings, sid, key)
                if raw is None:
                    continue
                value = parse_number(raw)
                if value <= 0:
                    continue
                new = value * s.far_damage_factor
                if cap is not None:
                    new = min(cap, new)
                if _neq(new, value):
                    patches.setdefault(sid, {})[key] = _num(new)

        if s.stat_bars_follow:
            for key, param, global_factor in (
                    ("DamageUI", "damage", 1.0),
                    ("RangeUI", "range", s.weapon_range_factor),
                    ("RateOfFireUI", "firerate", 1.0)):
                bar_factor = factor_for(sid, param, global_factor)
                if not _neq(bar_factor, 1.0) or bar_factor < 0:
                    continue
                value = parse_number(gd.resolve(gd.weaponsettings, sid, key))
                if value <= 0:
                    continue
                new = min(1.0, value * bar_factor)
                if _neq(new, value):
                    patches.setdefault(sid, {})[key] = _num(new)

            # 1.33.0: die zwei restlichen Balken. Bis 1.32.0 blieben sie
            # bewusst draussen, weil Accuracy und Handling im Spiel
            # Mischwerte sind. Zwei fremde Mods (Maklane 241, Stalker
            # Unlimited 1453) setzen sie trotzdem, und ein halb mitziehender
            # Balkensatz ist verwirrender als ein ganzer. Also als ehrliche
            # NAEHERUNG: Genauigkeit folgt der Streuung (weniger Streuung =
            # besserer Balken, darum invers), Handling folgt der Zielzeit
            # (die ist schon invers definiert: x2 = doppelt so schnell).
            # Der Tooltip sagt, dass das eine Naeherung ist.
            for key, param, global_factor, invert in (
                    ("AccuracyUI", "spread", s.spread_factor, True),
                    ("HandlingUI", "aimtime", s.aim_time_factor, False)):
                bar_factor = factor_for(sid, param, global_factor)
                if not _neq(bar_factor, 1.0) or bar_factor <= 0:
                    continue
                if invert:
                    bar_factor = 1.0 / bar_factor
                value = parse_number(gd.resolve(gd.weaponsettings, sid, key))
                if value <= 0:
                    continue
                new = min(1.0, value * bar_factor)
                if _neq(new, value):
                    patches.setdefault(sid, {})[key] = _num(new)
    return patches


def _npc_vs_npc_patch(gd: GameData, s: Settings) -> dict:
    """Wie hart NPCs EINANDER treffen (CharacterWeaponSettings).

    `NPCToNPCDamageScaler` steht in Vanilla bei allen 150 CWS-Structs auf
    0.7 (gemessen 07.09.2026) — Stalker gegen Stalker macht also 70 % des
    Schadens. Ein Wert, ein Regler; er beruehrt den Spieler nicht.
    Gefunden beim Durchsehen der Mod "Stalker Unlimited" (Nexus 1453).

    Bewusst OHNE Kaskade: das ist kein Waffengefuehl, sondern eine
    Weltregel — und sie an einer einzelnen Waffe zu verstellen waere im
    Tooltip nicht zu erklaeren.

    **1.35.0: der Dreiersatz ist vollstaendig.** Der Schluessel hat zwei
    Geschwister im selben Struct, und 1.31.0 hatte nur den ersten genommen —
    aufgefallen ueber den Familien-Waechter und beim Lesen von "Better
    Ballistics Core" (Nexus 2536). Live gemessen (08.09.2026, je 150x):
    `NPCToNPCDamageScaler` 0.7, `NPCToPlayerDamageScaler` 1.0,
    `NPCToFriendlyDamageScaler` 0.3. Der mittlere ist der interessanteste:
    er entscheidet, wie hart NPC-Kugeln DICH treffen, und zwar unabhaengig
    vom Schwierigkeitsgrad-Multiplikator, der daneben steht."""
    keys = (("NPCToNPCDamageScaler", s.npc_vs_npc_damage_factor),
            ("NPCToPlayerDamageScaler", s.npc_vs_player_damage_factor),
            ("NPCToFriendlyDamageScaler", s.npc_vs_friendly_damage_factor))
    active = [(k, f) for k, f in keys if _neq(f, 1.0) and f >= 0]
    if not active:
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.weaponsettings.children.items()):
        if "#" in sid:
            continue
        cfg: dict = {}
        for key, factor in active:
            raw = node.values.get(key)
            if raw is None:
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None and scaled != raw.strip():
                cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _zombie_spread_patch(gd: GameData, s: Settings) -> dict:
    """Streuungs-Aufschlag fuer zombifizierte Stalker (CharacterWeaponSettings).

    `DispersionRadiusZombieAddend` steht bei allen 75 NPC-Structs auf 30.0
    (gemessen 07.09.2026) - ein AUFSCHLAG auf die Streuung, der nur greift,
    wenn der Schuetze zombifiziert ist. 0 % = Zombies zielen so gut wie
    normale Stalker. Gefunden in "Stalker Unlimited" (Nexus 1453)."""
    if not _neq(s.zombie_spread_factor, 1.0) or s.zombie_spread_factor < 0:
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.weaponsettings.children.items()):
        if "#" in sid:
            continue
        raw = node.values.get("DispersionRadiusZombieAddend")
        if raw is None:
            continue
        scaled = _scale_literal(raw, s.zombie_spread_factor)
        if scaled is not None and scaled != raw.strip():
            patches[sid] = {"DispersionRadiusZombieAddend": scaled}
    return patches


def _weapon_noise_patch(gd: GameData, s: Settings) -> dict:
    """Wie laut eine Waffe ist (CharacterWeaponSettings `FireLoudness`).

    150 Structs, Vanilla 0.6 bis 0.8 (neun stehen auf 0.0 - lautlose
    Sonderfaelle, die 0 bleiben). Das ist der fehlende Baustein neben den
    Stealth-Reglern: bisher konnte man einstellen, wie gut NPCs hoeren,
    aber nicht, wie laut die eigene Waffe ist. 0 % = kein Schuss wird
    gehoert. Gefunden in "Maklane's Better Zone" (Nexus 241)."""
    if not _neq(s.weapon_noise_factor, 1.0) or s.weapon_noise_factor < 0:
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.weaponsettings.children.items()):
        if "#" in sid:
            continue
        raw = node.values.get("FireLoudness")
        if raw is None or parse_number(raw) <= 0:
            continue
        scaled = _scale_literal(raw, s.weapon_noise_factor)
        if scaled is not None and scaled != raw.strip():
            patches[sid] = {"FireLoudness": scaled}
    return patches


def _npc_body_patch(gd: GameData, s: Settings) -> dict:
    """Drei NPC-weite Stellschrauben aus ObjPrototypes (1.32.0).

    - `AnomalyRestrictionsIgnoreChance` (1657 Prototypen, Vanilla 0.1):
      wie oft ein NPC die Anomalie-Sperre ignoriert und hineinlaeuft.
      Gedeckelt bei 1.0.
    - `DeathHitImpulseMultiplier` 2.0 / `DeathVelocityImpulseMultiplier`
      3.0: mit welcher Wucht ein Koerper beim Sterben wegfliegt.
    - Rueckzug: `RetreatRadius` (wie weit) und `DamageAccumulatedToRetreat`
      (wieviel Schaden vorher) - beide stehen teils direkt am Prototyp,
      teils unter RetreatActionData, darum beide Orte.

    Player und die Basis `[0]` bleiben aussen vor."""
    anomaly = _neq(s.npc_anomaly_ignore_factor, 1.0) and s.npc_anomaly_ignore_factor >= 0
    ragdoll = _neq(s.ragdoll_force_factor, 1.0) and s.ragdoll_force_factor >= 0
    radius = _neq(s.npc_retreat_radius_factor, 1.0) and s.npc_retreat_radius_factor >= 0
    damage = _neq(s.npc_retreat_damage_factor, 1.0) and s.npc_retreat_damage_factor >= 0
    if not (anomaly or ragdoll or radius or damage):
        return {}

    simple = []
    if anomaly:
        simple.append(("AnomalyRestrictionsIgnoreChance", s.npc_anomaly_ignore_factor, 1.0))
    if ragdoll:
        simple.append(("DeathHitImpulseMultiplier", s.ragdoll_force_factor, None))
        simple.append(("DeathVelocityImpulseMultiplier", s.ragdoll_force_factor, None))
    if radius:
        simple.append(("RetreatRadius", s.npc_retreat_radius_factor, None))
    if damage:
        simple.append(("DamageAccumulatedToRetreat", s.npc_retreat_damage_factor, None))
    nested = [(key, factor) for key, factor, _cap in simple
              if key in ("RetreatRadius", "DamageAccumulatedToRetreat")]

    patches: dict = {}
    for sid, node in sorted(gd.obj.children.items()):
        if sid in ("[0]", "Player") or "#" in sid:
            continue
        cfg: dict = {}
        for key, factor, cap in simple:
            raw = node.values.get(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, factor, cap=cap)
            if scaled is not None and scaled != raw.strip():
                cfg[key] = scaled
        action = node.children.get("RetreatActionData")
        if action is not None:
            inner: dict = {}
            for key, factor in nested:
                raw = action.values.get(key)
                if raw is None or parse_number(raw) <= 0:
                    continue
                scaled = _scale_literal(raw, factor)
                if scaled is not None and scaled != raw.strip():
                    inner[key] = scaled
            if inner:
                cfg["RetreatActionData"] = inner
        if cfg:
            patches[sid] = cfg
    return patches


def _weapon_general_patch(gd: GameData, s: Settings) -> tuple[dict, dict]:
    """WeaponGeneralSetup: Streuung, Rueckstoss, Feuerrate (Kaskade).

    Gepatcht werden Structs, die den Wert SELBST definieren — Erben
    skalieren ueber den Eltern-Patch automatisch mit. Einzelwaffen-
    Overrides werden zusaetzlich am eigenen Struct emittiert (Wert via
    gd.resolve aufgeloest), falls die Waffe den Wert nur erbt.

    Liefert (Basis-Patches, {Edition: Patches}): die Editions-Waffen
    (Gabion & Co.) haben ihre Setup-Structs in EIGENEN DLC-Dateien —
    was sie von der Basis erben, deckt der Basis-Patch ab; was sie
    selbst definieren (und ihre Einzel-Overrides), landet im Patch des
    jeweiligen DLCGameData-Zweigs."""
    patches: dict = {}
    dlc_patches: dict[str, dict] = {}
    dlc_eds = gd.dlc_weapon_editions()

    def emit(bucket: dict, sid: str, path: str, value: float):
        node = bucket.setdefault(sid, {})
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = _num(value)

    def scale(path: str, param: str, global_factor: float = 1.0,
              invert: bool = False, skip_unchanged: bool = False):
        """skip_unchanged: Blaetter auslassen, deren Ergebnis gleich
        Vanilla ist. Gebraucht seit 1.31.0 fuer die Ladehemmung — dort
        steht MinJamChance bei 91 von 92 Waffen auf 0.0, und 0 x Faktor
        bleibt 0; ohne den Filter stuenden 91 wirkungslose Zeilen im
        Patch. Fuer die aelteren Aufrufe bleibt das Verhalten
        unveraendert (Vorgabe False), damit deren Paks bytegleich
        bleiben."""
        values = gd.weapon_general_values(path)
        for sid, value in sorted(values.items()):
            f = _weapon_factor(s, gd.weapon_category(sid), sid, param,
                               global_factor)
            if not _neq(f, 1.0) or f < 0 or (invert and f <= 0):
                continue
            new = value / f if invert else value * f
            if skip_unchanged and not _neq(new, value):
                continue
            emit(patches, sid, path, new)
        dlc_values = gd.dlc_weapon_general_values(path)
        for (ed, sid), value in sorted(dlc_values.items()):
            f = _weapon_factor(s, gd.dlc_weapon_category(ed, sid), sid,
                               param, global_factor)
            if not _neq(f, 1.0) or f < 0 or (invert and f <= 0):
                continue
            new = value / f if invert else value * f
            if skip_unchanged and not _neq(new, value):
                continue
            emit(dlc_patches.setdefault(ed, {}), sid, path, new)
        dlc_defined = {sid for _ed, sid in dlc_values}
        for sid, params in sorted(s.weapon_overrides.items()):
            f = params.get(param)
            if (f is None or sid in values or sid in dlc_defined
                    or not _neq(f, 1.0) or f < 0
                    or (invert and f <= 0)):
                continue
            ed = dlc_eds.get(sid)
            if ed is not None:
                value = parse_number(gd.dlc_resolve_weapon(ed, sid, path))
                if value > 0:
                    emit(dlc_patches.setdefault(ed, {}), sid, path,
                         value / f if invert else value * f)
                continue
            value = parse_number(gd.resolve(gd.weapongeneral, sid, path))
            if value > 0:
                emit(patches, sid, path, value / f if invert else value * f)

    # Patrone in der Kammer (1.32.0): 65 der 92 Waffen geben nach dem
    # Nachladen eine Zusatzpatrone, 27 nicht. Der Schalter zieht die 27 nach.
    if s.chamber_round:
        for _sid, _node in sorted(gd.weapongeneral.children.items()):
            if "#" in _sid:
                continue
            _raw = _node.values.get("AdditionalBulletsAfterReloadingCount")
            if _raw is not None and parse_number(_raw) < 1:
                # Stueckzahl: als Ganzzahl schreiben wie Vanilla ("1", nicht "1.0")
                patches.setdefault(_sid, {})["AdditionalBulletsAfterReloadingCount"] = "1"

    # Munition in der Waffe eines toten NPCs (1.32.0). ⚠ -1 heisst "nicht
    # gesetzt" und wird uebersprungen (16 bzw. 19 Waffen) - ein Faktor
    # darauf ergaebe -2 und damit Unsinn.
    if _neq(s.dropped_ammo_factor, 1.0) and s.dropped_ammo_factor >= 0:
        for _sid, _node in sorted(gd.weapongeneral.children.items()):
            if "#" in _sid:
                continue
            for _key in ("MinDeadNPCLoadedAmmoCount", "MaxDeadNPCLoadedAmmoCount"):
                _raw = _node.values.get(_key)
                if _raw is None:
                    continue
                _value = parse_number(_raw)
                if _value < 0:
                    continue
                _new = max(0, int(round(_value * s.dropped_ammo_factor)))
                if _new != int(_value):
                    patches.setdefault(_sid, {})[_key] = str(_new)

    # Ladehemmung (1.31.0): die Wahrscheinlichkeit selbst, NICHT die
    # Haltbarkeits-Schwellen, ab denen sie greift (MinJamDurabilityThreshold
    # 0.75 / MaxJamDurabilityThreshold 0.1 bleiben vanilla — sie sagen, AB
    # WANN geklemmt wird, und das laesst sich nicht in einen Satz fassen).
    # "jamchance" steht bewusst NICHT in WEAPON_PARAMS: damit faellt
    # _weapon_factor immer auf den globalen Regler zurueck (Muster wie
    # "equiptime" seit 1.29.0).
    scale("MinJamChance", "jamchance", s.jam_chance_factor, skip_unchanged=True)
    scale("MaxJamChance", "jamchance", s.jam_chance_factor, skip_unchanged=True)

    # Erholung nach dem Schuss (1.32.0). Rueckstoss UND Streuung haben je
    # ein eigenes RadiusNormalizationModifiers-Struct; beide Zeiten werden
    # INVERS skaliert (200 % = halb so lang, also schnelleres Beruhigen).
    # Delay steht bei vielen Waffen auf 0.0 und bleibt es (skip_unchanged).
    for _branch in ("RecoilParams", "DispersionParams"):
        for _key in ("RadiusNormalizationInterval", "RadiusNormalizationDelay"):
            scale(f"{_branch}.ShootingStateParams.RadiusNormalizationModifiers.{_key}",
                  "recoilrecovery", s.recoil_recovery_factor, invert=True,
                  skip_unchanged=True)

    # Streuungs-Aufbau bei Dauerfeuer (1.32.0). ⚠ Nur der DispersionParams-
    # Zweig: auf der Rueckstoss-Seite stehen ALLE 92 Waffen auf 0.0/0.0/0,
    # dort gibt es in Vanilla gar keinen Aufbau (gemessen 07.09.2026).
    # RadiusExtensionBulletCount (ab dem wievielten Schuss) bleibt
    # unangetastet — das ist eine andere Achse als "wie stark".
    for _key in ("MaxRadiusExtensionModifier", "PerIterationRadiusExtensionModifier"):
        scale(f"DispersionParams.ShootingStateParams.RadiusExtensionModifiers.{_key}",
              "spreadbloom", s.spread_bloom_factor, skip_unchanged=True)
    # Wie stark Zielen und Ducken die Waffe beruhigen (1.32.0,
    # experimentell). Vanilla: auf der Rueckstoss-Seite senkt Ducken um
    # 15 %, auf der Streuungs-Seite nimmt Zielen sie bei 71 Waffen KOMPLETT
    # weg (-1.0). Der Betrag wird deshalb bei 1.0 gedeckelt — mehr als
    # "faellt ganz weg" gibt es in den Spieldaten nirgends, und was das
    # Spiel mit -2.0 taete, weiss niemand.
    if _neq(s.aim_steady_factor, 1.0) and s.aim_steady_factor >= 0:
        for _branch in ("RecoilParams", "DispersionParams"):
            for _key in ("AimModifier", "AimCrouchModifier",
                         "AimFullCrouchModifier"):
                _path = f"{_branch}.ShootingStateParams.AimModifiers.{_key}"
                values = gd.weapon_general_values(_path, signed=True)
                for _sid, _value in sorted(values.items()):
                    _new = max(-1.0, min(1.0, _value * s.aim_steady_factor))
                    if _neq(_new, _value):
                        emit(patches, _sid, _path, _new)

    # Hueftfeuer und Bewegung (1.32.0) - dieselbe Familie wie die
    # Aim-Modifikatoren darueber: unter ShootingStateParams liegen DREI
    # gleichartige Bloecke (AimModifiers, HipModifiers,
    # MovementSpeedModifiers), je einmal fuer Rueckstoss und Streuung.
    # Vanilla: Ducken senkt die Hueft-Streuung um 0.2, Springen hebt sie um
    # 0.3, und Laufen hebt sie um 0.1 bis 1.0. Betrag wieder auf 1.0
    # gedeckelt - mehr kommt in den Spieldaten nirgends vor.
    for _factor, _keys, _group in (
            (s.hip_steady_factor,
             ("HipModifier", "HipCrouchModifier", "HipFullCrouchModifier",
              "HipJumpModifier"), "HipModifiers"),
            (s.move_steady_factor, ("MovementSpeedModifier",),
             "MovementSpeedModifiers")):
        if not _neq(_factor, 1.0) or _factor < 0:
            continue
        for _branch in ("RecoilParams", "DispersionParams"):
            for _key in _keys:
                _path = f"{_branch}.ShootingStateParams.{_group}.{_key}"
                for _sid, _value in sorted(
                        gd.weapon_general_values(_path, signed=True).items()):
                    _new = max(-1.0, min(1.0, _value * _factor))
                    if _neq(_new, _value):
                        emit(patches, _sid, _path, _new)

    # Pause, nach der das Rueckstossmuster von vorn beginnt (Vanilla 0.3 s,
    # 18 Waffen 1.0, zwei 5.0). Die RICHTUNG des Musters steckt in einem
    # IoStore-Asset und bleibt unerreichbar - nur diese Pause ist cfg-seitig.
    scale("RecoilParams.RecoilPatternInterval", "recoilpattern",
          s.recoil_pattern_factor, skip_unchanged=True)

    scale("DispersionParams.FirstShotDispersionRadius", "spread",
          s.spread_factor)
    scale("RecoilParams.RecoilRadius", "recoil", s.recoil_factor)
    # Feuerrate: Faktor 2 = doppelt so schnell -> Intervalle halbieren;
    # RecoilInterval synchron, sonst laufen Rueckstoss und Schuss auseinander
    scale("FireInterval", "firerate", invert=True)
    scale("RecoilInterval", "firerate", invert=True)
    scale("AimingMovementSpeedModifier", "adsspeed", s.ads_speed_factor)
    # Ziel-Geschwindigkeit: Faktor 2 = doppelt so schnell im Ziel ->
    # Zeiten halbieren (Nexus-Wunsch "change ADS speed"; der aeltere
    # adsspeed-Regler ist nur das BEWEGUNGSTEMPO waehrend des Zielens)
    for key in WEAPON_AIMTIME_KEYS:
        scale(key, "aimtime", s.aim_time_factor, invert=True)
    # 1.29.0: Waffe ziehen und wegstecken (ShowEquipmentTime /
    # HideEquipmentTime, Vanilla je 1.0 an allen 92 Basis- und 11
    # Editions-Waffen). Zeit / Faktor wie beim Nachladen; anders als der
    # Nachlade-Regler nimmt dieser die Editions-Waffen mit, weil sie den
    # Schluessel selbst tragen und sonst spuerbar anders waeren.
    # "equiptime" ist KEIN Kaskaden-Parameter (nicht in WEAPON_PARAMS) -
    # _weapon_factor faellt damit immer auf den globalen Regler zurueck.
    for key in ("ShowEquipmentTime", "HideEquipmentTime"):
        scale(key, "equiptime", s.equip_speed_factor, invert=True)

    # 1.29.0: uebersprungene Schuss-Animationen. Der Schluessel steht an
    # allen 92 Basis- und 11 Editions-Waffen auf 0 und ist der einzige
    # cfg-Hebel, der ueberhaupt etwas mit dem Anim-Timing beim Schiessen zu
    # tun hat (eine Suche ueber ALLE cfg nach PlayRate/RateScale/Anim*Speed
    # ergab fuer Waffen nichts - Tempo und Ton liegen in gekochten Assets).
    # Absolutwert und ganzzahlig; weil Vanilla 0 ist, liefert
    # weapon_general_values() hier nichts und die Structs werden direkt
    # durchlaufen. Wirkung im Spiel voellig offen - Deutung nur aus dem
    # Schluesselnamen.
    if int(s.shooting_anim_skip) != 0:
        wanted = str(max(0, int(s.shooting_anim_skip)))
        key = "ShootingAnimationNumberToSkip"
        for sid, node in sorted(gd.weapongeneral.children.items()):
            if sid.startswith("[") or "#" in sid:
                continue
            raw = node.values.get(key)
            if raw is None or raw.strip() == wanted:
                continue
            patches.setdefault(sid, {})[key] = wanted
        for ed, trees in sorted(gd.dlc_editions.items()):
            tree = trees.get("weapongeneral")
            for sid, node in sorted(tree.children.items() if tree else ()):
                if sid.startswith("[") or "#" in sid:
                    continue
                raw = node.values.get(key)
                if raw is None or raw.strip() == wanted:
                    continue
                dlc_patches.setdefault(ed, {}).setdefault(sid, {})[key] = wanted

    # ADS-Zoom (06.09.2026, Nexus 'No zoom while aiming' / 'Zoom in when
    # aiming'): AimingFOVModifier < 1 = Zoom beim Zielen (0.92/0.88/0.83).
    # Faktor auf den ABSTAND zu 1.0: 0 = kein Zoom, 2 = doppelter Zoom;
    # Deckel 0.2, damit das Bild nie kippt. OffsetAiming genauso.
    if _neq(s.ads_zoom_factor, 1.0) and s.ads_zoom_factor >= 0:
        for key in ("AimingFOVModifier", "OffsetAimingFOVModifier"):
            for sid, value in sorted(gd.weapon_general_values(key).items()):
                new = max(0.2, min(1.0, 1.0 - (1.0 - value) * s.ads_zoom_factor))
                if _neq(new, value):
                    patches.setdefault(sid, {})[key] = _num(new)
            for (ed, sid), value in sorted(gd.dlc_weapon_general_values(key).items()):
                new = max(0.2, min(1.0, 1.0 - (1.0 - value) * s.ads_zoom_factor))
                if _neq(new, value):
                    dlc_patches.setdefault(ed, {}).setdefault(sid, {})[key] = _num(new)

    # Magazingroesse an der WAFFE (Basiswert ohne Magazin-Aufsatz): ganzzahlig,
    # seit 03.09. der 10. Kaskaden-Parameter (Nexus-Wunsch Qfander): Einzel-
    # waffe > Kategorie > globaler Regler, wie scale() - nur mit Ganzzahl-
    # Rundung und ohne Division, darum eigene Schleife.
    mag_values = gd.weapon_general_values("MaxAmmo")
    mag_dlc = gd.dlc_weapon_general_values("MaxAmmo")
    for sid, value in sorted(mag_values.items()):
        f = _weapon_factor(s, gd.weapon_category(sid), sid, "magazine",
                           s.magazine_factor)
        if not _neq(f, 1.0) or f <= 0:
            continue
        scaled_int = max(1, int(round(value * f)))
        if scaled_int != int(value):
            patches.setdefault(sid, {})["MaxAmmo"] = str(scaled_int)
    for (ed, sid), value in sorted(mag_dlc.items()):
        f = _weapon_factor(s, gd.dlc_weapon_category(ed, sid), sid,
                           "magazine", s.magazine_factor)
        if not _neq(f, 1.0) or f <= 0:
            continue
        scaled_int = max(1, int(round(value * f)))
        if scaled_int != int(value):
            dlc_patches.setdefault(ed, {}).setdefault(sid, {})[
                "MaxAmmo"] = str(scaled_int)
    # Einzelwaffen-Override auf einer Waffe, die MaxAmmo nur ERBT: am
    # eigenen Struct emittieren (Wert aufgeloest), sonst traefe der
    # Template-Patch die ganze Kategorie.
    mag_dlc_defined = {sid for _ed, sid in mag_dlc}
    for sid, params in sorted(s.weapon_overrides.items()):
        f = params.get("magazine")
        if (f is None or sid in mag_values or sid in mag_dlc_defined
                or not _neq(f, 1.0) or f <= 0):
            continue
        ed = dlc_eds.get(sid)
        raw = (gd.dlc_resolve_weapon(ed, sid, "MaxAmmo") if ed is not None
               else gd.resolve(gd.weapongeneral, sid, "MaxAmmo"))
        value = parse_number(raw)
        if value <= 0:
            continue
        scaled_int = max(1, int(round(value * f)))
        if scaled_int == int(value):
            continue
        bucket = dlc_patches.setdefault(ed, {}) if ed is not None else patches
        bucket.setdefault(sid, {})["MaxAmmo"] = str(scaled_int)

    # Kaliberwechsel (GitHub Issue #6, Molkerr): AmmoCaliber umsetzen und
    # die Projektile der bestehenden Sorten-Slots auf das neue Kaliber
    # umbiegen.
    #
    # Bewusst werden NUR vorhandene Slots umgeschrieben, nie welche
    # angelegt oder entfernt. Ob {bpatch} ein Array verlaengern kann, ist
    # im Projekt nie im Spiel geprueft worden (docs/SPEC.md fuehrt es als
    # offene Frage) — und es waere auch nicht noetig: eine Waffe behaelt
    # einfach so viele Munitionssorten, wie sie vorher hatte.
    #
    # Die Sorte wird pro Index AUS DEN DATEN gelesen, nie aus der
    # Position geschlossen: sechs Scharfschuetzengewehre haben auf [0]
    # Supersonic statt Default. Kennt das Zielkaliber die Sorte nicht,
    # bekommt der Slot dessen Default-Projektil — so entsteht nie ein
    # Slot, der ins Leere zeigt.
    caliber_tables = swappable_calibers(gd) if s.weapon_calibers else {}
    for sid, wanted in sorted(s.weapon_calibers.items()):
        table = caliber_tables.get(wanted)
        if table is None:
            continue                      # unbekanntes/gesperrtes Kaliber
        ed = dlc_eds.get(sid)
        if gd.weapon_caliber(sid, ed) == wanted:
            continue                      # Vanilla — kein Patch (_neq-Regel)
        slots = gd.weapon_ammo_slots(sid, ed)
        if not slots:
            continue
        fallback = table.get("Default") or next(iter(table.values()))
        node: dict = {"AmmoCaliber": f"EAmmoCaliber::{wanted}"}
        block: dict = {}
        for index, kind in slots.items():
            block[index] = {
                "AmmoType": f"EAmmoType::{kind}",
                "ProjectilePrototypeSID": table.get(kind, fallback),
            }
        node["AmmoTypeProjectiles"] = block
        bucket = dlc_patches.setdefault(ed, {}) if ed is not None else patches
        for key, value in node.items():
            existing = bucket.setdefault(sid, {})
            existing[key] = value
    # 1.26.0: Nachladegeschwindigkeit (stalker-world 'schnelleres Nachladen',
    # die Felder aus dem offiziellen Weapon-Animation-Guide) - alle
    # *ReloadTimeMultiplier direkt am Struct und je Magazin-Aufsatz, Zeit /
    # Faktor - und Klemmer-Beseitigung (WeaponJamParams.FullJamTime, Zeit /
    # Faktor). Nur selbst definierte Werte der Basisdatei; die Editions-
    # Waffen im DLC-Zweig behalten Vanilla. Wirkung im Spiel offen.
    reload_on = _neq(s.reload_speed_factor, 1.0) and s.reload_speed_factor > 0
    jam_on = _neq(s.jam_clear_factor, 1.0) and s.jam_clear_factor > 0
    jam_chance_on = _neq(s.jam_chance_factor, 1.0) and s.jam_chance_factor >= 0
    if reload_on or jam_on or jam_chance_on:
        for sid, node in sorted(gd.weapongeneral.children.items()):
            if sid.startswith("[") or "#" in sid:
                continue
            cfg: dict = {}
            if reload_on:
                for key in RELOAD_KEYS:
                    raw = node.values.get(key)
                    if raw is not None and parse_number(raw) > 0:
                        cfg[key] = _num(parse_number(raw) / s.reload_speed_factor)
                table = node.children.get("WeaponReloadTimePerAttachment")
                if table is not None:
                    rows: dict = {}
                    for idx, entry in table.children.items():
                        row = {key: _num(parse_number(entry.values[key]) / s.reload_speed_factor)
                               for key in RELOAD_KEYS
                               if key in entry.values and parse_number(entry.values[key]) > 0}
                        if row:
                            rows[idx] = row
                    if rows:
                        cfg["WeaponReloadTimePerAttachment"] = rows
            # WeaponJamParams.[i] traegt GENAU zwei Schluessel: JamChanceCoef
            # (wie wahrscheinlich es klemmt) und FullJamTime (wie lange das
            # Beseitigen dauert). Bis 1.31.0 schrieb der Klemmer-Regler nur
            # FullJamTime hinein - ein HALBER Array-Eintrag. Sollte {bpatch}
            # Array-Eintraege ersetzen statt zusammenzufuehren (docs/SPEC.md
            # par. 0, offene Frage), haette das den Klemm-Koeffizienten still
            # geloescht. Beide Regler geben den Eintrag jetzt KOMPLETT aus.
            if jam_on or jam_chance_on:
                table = node.children.get("WeaponJamParams")
                if table is not None:
                    rows = {}
                    for idx, entry in table.children.items():
                        time_raw = entry.values.get("FullJamTime")
                        coef_raw = entry.values.get("JamChanceCoef")
                        row = {}
                        if time_raw is not None:
                            value = parse_number(time_raw)
                            row["FullJamTime"] = (
                                _num(value / s.jam_clear_factor)
                                if jam_on and value > 0 else time_raw.strip())
                        if coef_raw is not None:
                            value = parse_number(coef_raw)
                            row["JamChanceCoef"] = (
                                _num(value * s.jam_chance_factor)
                                if jam_chance_on and value > 0 else coef_raw.strip())
                        # Nur schreiben, wenn sich wirklich etwas aendert
                        if row and any(
                                row.get(k) != (entry.values.get(k) or "").strip()
                                for k in row):
                            rows[idx] = row
                    if rows:
                        cfg["WeaponJamParams"] = rows
            if cfg:
                _merge_nested(patches.setdefault(sid, {}), cfg)
    return patches, dlc_patches


def _weight_params_patch(gd: GameData, s: Settings) -> dict:
    m = s.max_carry_weight
    ps = min(s.penalty_start_weight, m - 1.0)
    if not _neq(m, VANILLA_MAX_CARRY) and not _neq(ps, VANILLA_PENALTY_START):
        return {}
    # Stufen zwischen Malus-Start und Maximum verteilen (Vanilla: 50/60/70/80)
    t1 = ps + (m - ps) / 3.0
    t2 = ps + 2.0 * (m - ps) / 3.0
    thresholds = {
        "[0]": {
            "Threshold": f"{_num(m)}f",
            "EffectPrototypeSIDs": {
                "[0]": "OverweightStaminaPointsRegen",
                "[1]": "OverweightBlockJoggingActionTypeEffect",
                "[2]": "OverweightMovementVelocityChange_3",
            },
        },
        "[1]": {
            "Threshold": f"{_num(t2)}f",
            "EffectPrototypeSIDs": {
                "[0]": "OverweightMovementVelocityChange_3",
                "[1]": "OverweightStaminaPointsRegen70kg",
                "[2]": "OverweightBlockJoggingActionTypeEffect",
            },
        },
        "[2]": {
            "Threshold": f"{_num(t1)}f",
            "EffectPrototypeSIDs": {
                "[0]": "OverweightMovementVelocityChange_2",
                "[1]": "OverweightStaminaPointsRegen60kg",
            },
        },
        "[3]": {
            "Threshold": f"{_num(ps)}f",
            "EffectPrototypeSIDs": {
                "[0]": "OverweightMovementVelocityChange_1",
                "[1]": "OverweightStaminaPointsRegen50kg",
            },
        },
    }
    return {
        "DefaultWeightParams": {
            "MaxInventoryMass": _num(m),
            "InventoryPenaltyLessWeight": _num(ps - 0.01),
            "WeightEffectParams": thresholds,
        }
    }


def _effect_max_patch(gd: GameData, s: Settings) -> dict:
    """ObjEffectMaxParams: Tragegewicht-Deckel (seit je) und seit 1.26.0 die
    Schutz-Deckel (ap-pro 'Max Stats Patch'): alles, was Ruestung und
    Artefakte ueber 90 % (Strike 4.5) geben, verpufft in Vanilla."""
    entries: dict = {}
    if _neq(s.max_carry_weight, VANILLA_MAX_CARRY):
        scale = s.max_carry_weight / VANILLA_MAX_CARRY
        entries["[1]"] = {"EffectSID": "EEffectType::PenaltyLessWeight",
                          "MaxValue": _num(90 * scale)}
        entries["[9]"] = {"EffectSID": "EEffectType::AdditionalInventoryWeight",
                          "MaxValue": _num(140 * scale)}
    if _neq(s.protection_cap_factor, 1.0) and s.protection_cap_factor > 0:
        root = gd.effectmax.children.get("DefaultEffectMaxParamsSID")
        values = root.children.get("MaxEffectValues") if root is not None else None
        for idx, entry in (values.children.items() if values is not None else ()):
            sid = (entry.values.get("EffectSID") or "").strip()
            kind = sid.replace("EEffectType::", "")
            raw = entry.values.get("MaxValue")
            value = parse_number(raw)
            if kind not in PROTECTION_CAP_TYPES or raw is None or value <= 0:
                continue
            new = value * s.protection_cap_factor
            if PROTECTION_CAP_TYPES[kind]:
                new = min(100.0, new)
            if not _neq(new, value):
                continue
            suffix = "f" if raw.strip().endswith(("f", "F")) else ""
            entries[idx] = {"EffectSID": sid, "MaxValue": _num(new) + suffix}
    # 1.33.0: die zwei restlichen Deckel. Die Liste hat genau zehn Eintraege
    # (gemessen): sechs Schutzwerte (oben), PenaltyLessWeight 90 und
    # AdditionalInventoryWeight 140 (haengen am Traglast-Regler) - und diese
    # beiden hier, die bisher an keinem Regler hingen. "More Uncapped"
    # (Nexus 858) nimmt alle zehn mal zehn.
    if _neq(s.effect_cap_other_factor, 1.0) and s.effect_cap_other_factor > 0:
        root = gd.effectmax.children.get("DefaultEffectMaxParamsSID")
        values = root.children.get("MaxEffectValues") if root is not None else None
        for idx, entry in (values.children.items() if values is not None else ()):
            sid = (entry.values.get("EffectSID") or "").strip()
            if sid.replace("EEffectType::", "") not in ("RegenStamina", "DegenBleeding"):
                continue
            raw = entry.values.get("MaxValue")
            value = parse_number(raw)
            if raw is None or value <= 0 or idx in entries:
                continue
            new = value * s.effect_cap_other_factor
            if not _neq(new, value):
                continue
            suffix = "f" if raw.strip().endswith(("f", "F")) else ""
            entries[idx] = {"EffectSID": sid, "MaxValue": _num(new) + suffix}
    if not entries:
        return {}
    return {"DefaultEffectMaxParamsSID": {"MaxEffectValues": entries}}


def _effects_patch(gd: GameData, s: Settings) -> dict:
    patches: dict = {}
    # 1.26.0: Kolbenschlag-Abnutzung (ButtStroke_Corrosion, 5 Haltbarkeit je
    # Schlag x Faktor), Wachen-Insta-Kill (KillVolumeEffect: die drei Zusatz-
    # Effekte leeren, sdwvit NoInstaGibByGuards), Psy-Phantome statt echter
    # Stalker (sdwvit NoPsyStalkerSpawns), Teleports ohne Blende (sdwvit
    # InstaTeleports), Klicker-Blendschaden (sdwvit FlashbangAnomalyNerf).
    if _neq(s.butt_wear_factor, 1.0) and s.butt_wear_factor >= 0:
        node = gd.effects.children.get("ButtStroke_Corrosion")
        if node is not None:
            cfg: dict = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is not None and parse_number(raw) > 0:
                    scaled = _scale_literal(raw, s.butt_wear_factor)
                    if scaled is not None:
                        cfg[key] = scaled
            if cfg:
                patches["ButtStroke_Corrosion"] = cfg
    # 1.33.0: Ausruestungs-Verschleiss in Anomalien. Gefunden beim
    # Gegenlesen von "Better Durability 3.0" (Nexus 1695), die genau diese
    # Familie durch 4 teilt. Gemessen 07.09.2026: die Effekt-Typen
    # `Corrosion` und `VelocityCorrosion` bilden fuenf Anomalie-Saetze
    # (Burning/Carousel/Chemical/Clicker/Electro, dazu die Prolog-Variante)
    # mit je einem Eintrag fuer Body/Head/Pistol/Weapon/SecWeapon, Werte
    # 0.2 bis 25 Haltbarkeit je Treffer. Die gleichnamigen Composite-Eltern
    # stehen auf 0.f und bleiben unberuehrt (Wert 0). ButtStroke_Corrosion
    # gehoert dem eigenen Kolbenschlag-Regler und wird hier ausgelassen.
    if _neq(s.anomaly_wear_factor, 1.0) and s.anomaly_wear_factor >= 0:
        for sid, node in gd.effects.children.items():
            if sid == "ButtStroke_Corrosion" or "#" in sid:
                continue
            typ = (node.values.get("Type") or "").replace("EEffectType::", "").strip()
            if typ not in ("Corrosion", "VelocityCorrosion"):
                continue
            cfg = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is None or parse_number(raw) <= 0:
                    continue
                scaled = _scale_literal(raw, s.anomaly_wear_factor)
                if scaled is not None and scaled != raw.strip():
                    cfg[key] = scaled
            if cfg:
                patches.setdefault(sid, {}).update(cfg)
    # 1.35.0: Kamera-Bremsen. Gemessen 08.09.2026 - die Typen
    # `TurnRateChangeYaw`/`TurnRateChangePitch` gibt es GENAU sechsmal mit
    # Wirkung: Chemie-Anomalie -0.6, Stacheldraht -0.8, Fliegenfaenger -0.7,
    # je Yaw und Pitch. Die zwei Wasser-Effekte stehen auf 0% und bleiben es.
    # Bewusst NICHT dabei: die zwei `Concussion`-Effekte (1.0 und 25.0) -
    # das sind keine Prozentwerte, ihre Einheit ist unbekannt, und der
    # Blutsauger-Schrei ueber einen "Kamera"-Regler zu verstellen waere
    # geraten. Der Betrag ist bei 1.0 gedeckelt: mehr als "Blick steht
    # still" gibt es in den Spieldaten nirgends.
    if _neq(s.camera_slowdown_factor, 1.0) and s.camera_slowdown_factor >= 0:
        for sid, node in gd.effects.children.items():
            if "#" in sid:
                continue
            typ = (node.values.get("Type") or "").replace("EEffectType::", "").strip()
            if typ not in ("TurnRateChangeYaw", "TurnRateChangePitch"):
                continue
            cfg = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                value = parse_number(raw) if raw is not None else 0.0
                if raw is None or value == 0:
                    continue
                # Betrags-Deckel: die Werte sind NEGATIV (-0.6 bis -0.8), und
                # `cap` in _scale_literal deckelt nur nach oben. Mehr als
                # "Blick steht still" (-1.0) kommt in den Daten nicht vor.
                factor = s.camera_slowdown_factor
                if abs(value * factor) > 1.0:
                    factor = 1.0 / abs(value)
                scaled = _scale_literal(raw, factor)
                if scaled is not None and scaled != raw.strip():
                    cfg[key] = scaled
            if cfg:
                patches.setdefault(sid, {}).update(cfg)
    if s.guards_no_instakill:
        node = gd.effects.children.get("KillVolumeEffect")
        extra = (node.children.get("ApplyExtraEffectPrototypeSIDs")
                 if node is not None else None)
        if extra is not None:
            entries = {idx: "empty" for idx, raw in extra.values.items()
                       if not _is_empty_sid(raw)}
            if entries:
                patches["KillVolumeEffect"] = {"ApplyExtraEffectPrototypeSIDs": entries}
    if s.psy_phantoms_only:
        node = gd.effects.children.get("ConditionalSpawnPSYNPC")
        if node is not None and "SpawnPSYPhantoms" in gd.effects.children:
            if (node.values.get("FalseEffectSID") or "").strip() != "SpawnPSYPhantoms":
                patches["ConditionalSpawnPSYNPC"] = {"FalseEffectSID": "SpawnPSYPhantoms"}
    if s.instant_teleports:
        for sid, node in gd.effects.children.items():
            if "#" in sid:
                continue
            raw = node.values.get("TeleportType")
            if raw is not None and raw.strip() != "EGSCTeleportType::Instant":
                patches.setdefault(sid, {})["TeleportType"] = "EGSCTeleportType::Instant"
    if _neq(s.clicker_factor, 1.0) and s.clicker_factor >= 0:
        node = gd.effects.children.get("ClickerAnomalyHit")
        if node is not None:
            cfg = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is not None and parse_number(raw) > 0:
                    scaled = _scale_literal(raw, s.clicker_factor)
                    if scaled is not None:
                        cfg[key] = scaled
            if cfg:
                patches["ClickerAnomalyHit"] = cfg
    if s.no_overweight_penalty:
        for sid in (
            "OverweightMovementVelocityChange_1",
            "OverweightMovementVelocityChange_2",
            "OverweightMovementVelocityChange_3",
            "OverweightStaminaPointsRegen",
            "OverweightStaminaPointsRegen50kg",
            "OverweightStaminaPointsRegen60kg",
            "OverweightStaminaPointsRegen70kg",
        ):
            if sid in gd.effects.children:
                patches[sid] = {"ValueMin": "0%", "ValueMax": "0%"}

    # Artefakt-Effekte: alle Artifact*-Structs sind ein sauberer Namensraum.
    # Strahlung (ArtifactAddRadiation*) hat einen eigenen Regler.
    effect_on = _neq(s.artifact_effect_factor, 1.0)
    radiation_on = _neq(s.artifact_radiation_factor, 1.0)
    carry_on = _neq(s.armor_carry_bonus_factor, 1.0)
    for sid, node in gd.effects.children.items():
        if "#" in sid:
            continue
        if sid.startswith("Artifact"):
            is_radiation = sid.startswith("ArtifactAddRadiation")
            factor = (s.artifact_radiation_factor if is_radiation
                      else s.artifact_effect_factor)
            if not (radiation_on if is_radiation else effect_on):
                continue
        elif (carry_on and node.values.get("Type")
                == "EEffectType::AdditionalInventoryWeight"):
            # Exo-/Ruestungs-/Upgrade-Tragegewicht-Boni (Artefakte oben)
            factor = s.armor_carry_bonus_factor
        else:
            continue
        if not _neq(factor, 1.0):
            continue
        cfg: dict = {}
        for key in ("ValueMin", "ValueMax"):
            raw = node.values.get(key)
            if raw is None:
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None and scaled != raw.strip():
                cfg[key] = scaled
        if cfg:
            patches[sid] = cfg

    # Anomalie-Schaden je Element-Typ (SID-Sets verifiziert, Werte live)
    anomaly_factors = {
        "electro": s.anomaly_electro_factor,
        "chemical": s.anomaly_chemical_factor,
        "fire": s.anomaly_fire_factor,
        "gravity": s.anomaly_gravity_factor,
    }
    for element, factor in anomaly_factors.items():
        if not _neq(factor, 1.0):
            continue
        for sid in gd.ANOMALY_EFFECT_SETS[element]:
            node = gd.effects.children.get(sid)
            if node is None:
                continue
            cfg = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is None:
                    continue
                scaled = _scale_literal(raw, factor)
                if scaled is not None and scaled != raw.strip():
                    cfg[key] = scaled
            if cfg:
                patches.setdefault(sid, {}).update(cfg)

    # Consumable-Staerke (dynamische Whitelist ueber Item-Referenzen + Typ).
    # Der Heil-Regler stapelt MULTIPLIKATIV auf den Health-Effekten
    # medizinischer Items (Medkits/Verbaende, live erkannt) — beide auf
    # 200 % ergibt also x4 Heilung; Essen/Getraenke sieht nur den
    # Consumable-Faktor. Ein Effekt wird genau EINMAL mit dem kombinierten
    # Faktor emittiert, es entstehen keine doppelten Patch-Zeilen.
    if _neq(s.consumable_factor, 1.0) or _neq(s.healing_factor, 1.0):
        healing_sids = gd.medical_healing_effects()
        for sid, node in sorted(gd.consumable_effects().items()):
            factor = s.consumable_factor
            if sid in healing_sids:
                factor *= s.healing_factor
            if not _neq(factor, 1.0):
                continue
            cfg = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is None:
                    continue
                scaled = _scale_literal(raw, factor)
                if scaled is not None and scaled != raw.strip():
                    cfg[key] = scaled
            if cfg:
                patches.setdefault(sid, {}).update(cfg)
    # Wirkdauer von Verbrauchsguetern (Nexus-Trend seit 2.0, "Increased
    # Consumable Duration"): nur LAUFENDE Effekte (Duration >= 10 s -
    # Energydrink 45 s, Hercules 300 s, Zimt 180 s, PSY-Blocker 60 s ...).
    # Sofort-Effekte (Heilung/Blutstopp/Antirad ueber 1-2 s) bleiben, sonst
    # wuerde ein Medkit langsamer heilen statt laenger zu wirken.
    if (_neq(s.consumable_duration_factor, 1.0)
            and s.consumable_duration_factor > 0):
        for sid, raw in sorted(gd.consumable_duration_effects().items()):
            scaled = _scale_literal(raw, s.consumable_duration_factor)
            if scaled is not None and scaled != raw.strip():
                patches.setdefault(sid, {})["Duration"] = scaled

    # Rueckstoss-Reduktion aus Upgrades/Aufsaetzen (Community-Weg der
    # Nexus-Mod "Dead Steady" 2478, auf Patch 2.0 bestaetigt): alle Effekte
    # vom Typ Recoil mit NEGATIVEM Wert (= senken den Rueckstoss, Vanilla
    # -5 % .. -30 %, inkl. Scope-Varianten) werden skaliert, Deckel bei
    # -100 %. Positive Recoil-Effekte (Munitionsumbauten, Muedigkeit)
    # bleiben unangetastet. Greift nur bei Waffen, in denen ein solches
    # Upgrade/Attachment steckt - Tooltip und FAQ sagen das ehrlich.
    if _neq(s.recoil_upgrade_factor, 1.0) and s.recoil_upgrade_factor > 0:
        for sid, node in gd.effects.children.items():
            if "#" in sid or node.values.get("Type") != "EEffectType::Recoil":
                continue
            cfg = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is None or not raw.strip().endswith("%"):
                    continue
                try:
                    value = float(raw.strip()[:-1])
                except ValueError:
                    continue
                if value >= 0:
                    continue
                scaled = _num(max(-100.0, value * s.recoil_upgrade_factor)) + "%"
                if scaled != raw.strip():
                    cfg[key] = scaled
            if cfg:
                patches.setdefault(sid, {}).update(cfg)

    return patches


def _floatprovider_patch(gd: GameData, s: Settings) -> dict:
    """Scope-Sway ueber den Konstant-Provider regeln (Bugfix).

    Vanilla speist ScopeIdleSwayValue = ScopeIdleSwayConstValue x
    (1 - OffsetAimAlpha) die Sway-Effekte pro Tick und blendet den Daempfer
    beim Offset-Aiming (seitliches Zielen am ZF vorbei) auf 0 aus. Ein Patch
    direkt an den Effekten (ValueProviderSID=Empty) legte diese Ausblendung
    still -- die Offset-Aim-Animation blieb aus (Nexus-Bugreport).
    Hier wird nur die Konstante skaliert; die Provider-Kette bleibt intakt.
    """
    if not _neq(s.scope_sway_pct, 100):
        return {}
    # Vanilla-Konstante -0.2 = -20 % Sway im ZF; 100 % = Vanilla, 0 % = -1.0
    # (kein Sway). Dazwischen linear auf dem Rest-Sway (1 + Konstante).
    vanilla = parse_number(
        gd.resolve(gd.floatproviders, "ScopeIdleSwayConstValue", "Value"), -0.2)
    value = -(1.0 - (1.0 + vanilla) * s.scope_sway_pct / 100.0)
    return {"ScopeIdleSwayConstValue": {"Value": _num(value)}}


def _holdbreath_patch(gd: GameData, s: Settings) -> dict:
    if not _neq(s.breath_drain_factor, 1.0) and not _neq(s.breath_regen_factor, 1.0):
        return {}
    cfg: dict = {}
    if _neq(s.breath_drain_factor, 1.0):
        vanilla = parse_number(
            gd.resolve(gd.holdbreath, "DefaultHoldBreathParams", "HoldBreathDrainPerSecond"), 25.0)
        cfg["HoldBreathDrainPerSecond"] = _num(vanilla * s.breath_drain_factor)
    if _neq(s.breath_regen_factor, 1.0):
        vanilla = parse_number(
            gd.resolve(gd.holdbreath, "DefaultHoldBreathParams", "HoldBreathRegenPerSecond"), 12.5)
        cfg["HoldBreathRegenPerSecond"] = _num(vanilla * s.breath_regen_factor)
    return {"DefaultHoldBreathParams": cfg}


def _saveload_patch(gd: GameData, s: Settings) -> dict:
    """SaveLoadVariables (unbinarisiert wie CoreVariables): SavesLimit je
    Speichertyp (Vanilla Manual 31 / Quick 3 / Auto 10; 0 = unbegrenzt).
    Nexus "Bode's Unlimited Saves", Recherche 05.09.2026. Live gelesen,
    nur Abweichungen geschrieben."""
    node = gd.saveload.children.get("DefaultConfig")
    limits = node.children.get("SavesLimit") if node else None
    if limits is None:
        return {}
    cfg: dict = {}
    for key, wanted in (("Manual", s.manual_save_slots),
                        ("Quick", s.quick_save_slots),
                        ("Auto", s.auto_save_slots)):
        raw = limits.values.get(key)
        if raw is not None and wanted >= 0 and _neq(float(wanted), parse_number(raw)):
            cfg[key] = str(int(round(wanted)))
    return {"DefaultConfig": {"SavesLimit": cfg}} if cfg else {}


def _autosave_patch(gd: GameData, s: Settings) -> dict:
    """AutoSaveVariables (unbinarisiert): AutoSaveIntervalTime in Sekunden
    (Vanilla 600 = 10 min). Der Regler arbeitet in Minuten."""
    node = gd.autosave.children.get("DefaultConfig")
    raw = node.values.get("AutoSaveIntervalTime") if node else None
    if raw is None or s.autosave_interval_min <= 0:
        return {}
    wanted = s.autosave_interval_min * 60.0
    if not _neq(wanted, parse_number(raw)):
        return {}
    return {"DefaultConfig": {"AutoSaveIntervalTime": str(int(round(wanted)))}}


def _quicksave_patch(gd: GameData, s: Settings) -> dict:
    """QuickSaveVariables (unbinarisiert, 1.28.0): QuickSaveOverwriteTime in
    Sekunden (Vanilla 300 = 5 min) - so lange ueberschreibt ein neuer
    Schnellspeicher denselben Slot. Regler in Minuten, 0 = jeder
    Schnellspeicher bekommt einen eigenen Slot; ganzzahlig, live verglichen."""
    node = gd.quicksave.children.get("DefaultConfig")
    raw = node.values.get("QuickSaveOverwriteTime") if node else None
    if raw is None or s.quicksave_overwrite_min < 0:
        return {}
    wanted = int(round(s.quicksave_overwrite_min * 60.0))
    if not _neq(float(wanted), parse_number(raw)):
        return {}
    return {"DefaultConfig": {"QuickSaveOverwriteTime": str(wanted)}}


def _corevars_custom_patch(gd: GameData, core: dict) -> dict:
    """Versicherung fuer die zweite Kern-Datei (1.28.0, docs/CORE_SWEEP_RESEARCH.md
    par. 0): CoreVariablesCustom.cfg / CustomConfigOverride wiederholt vier
    DefaultConfig-Schluessel mit identischen Werten. Ob der Override nach
    DefaultConfig greift, ist unbekannt - darum bekommt er dieselben Werte,
    sobald der CoreVariables-Patch einen dieser Schluessel enthaelt (nur
    Schluessel, die dort live stehen). Harmlos, falls er nie greift."""
    wanted = {k: v for k, v in (core.get("DefaultConfig") or {}).items()
              if k in COREVARS_CUSTOM_KEYS}
    if not wanted:
        return {}
    node = gd.corevarscustom.children.get("CustomConfigOverride")
    if node is None:
        return {}
    cfg = {k: v for k, v in wanted.items() if k in node.values}
    return {"CustomConfigOverride": cfg} if cfg else {}


def _enemy_evaluator_patch(gd: GameData, s: Settings) -> dict:
    """EnemyEvaluatorPrototypes (1.28.0 P3, docs/CORE_SWEEP_RESEARCH.md par. 2.5):
    das einzige Struct [0] (SID empty) wird als '[0] : struct.begin {bpatch}'
    gepatcht (Muster IgnoreEquippedWeight in _items_patch). NotPlayerCoeff:
    Vorzeichen unbewiesen - experimentell, der Tooltip sagt es."""
    node = gd.enemyevaluators.children.get("[0]")
    if node is None:
        return {}
    cfg: dict = {}
    for key, factor in (("NotPlayerCoeff", s.npc_player_focus_factor),
                        ("ChangeEnemyCooldown", s.npc_retarget_cooldown_factor),
                        ("DamageAccumulationDurationSeconds", s.npc_damage_memory_factor)):
        if not (_neq(factor, 1.0) and factor >= 0):
            continue
        raw = node.values.get(key)
        if raw is None or parse_number(raw) <= 0:
            continue
        scaled = _scale_literal(raw, factor)
        if scaled is not None:
            cfg[key] = scaled
    return {"[0]": cfg} if cfg else {}


def _cover_evaluator_patch(gd: GameData, s: Settings) -> dict:
    """CoverEvaluatorPrototypes (1.28.0 P3, par. 2.5): NUR DefaultCoverEvaluator
    (CoverEvaluatorSID an 1605 NPC-Objekten). Boss/Strelok/Scar/Korshunov
    stehen auf der Tabu-Liste; Attack/Zombie/DLC01_ZulusMate/Default/
    LeaveCrossfire deklarieren alles selbst, haengen an keinem Objekt und
    bleiben ebenfalls unangetastet. Min <= Max bleibt gewahrt, MaxPathLength
    bleibt ganzzahlig."""
    node = gd.coverevaluators.children.get("DefaultCoverEvaluator")
    if node is None:
        return {}
    cfg: dict = {}
    if _neq(s.cover_distance_factor, 1.0) and s.cover_distance_factor > 0:
        settings = node.children.get("DefaultCoverSettings")
        raw_min = settings.values.get("MinDistanceToEnemy") if settings is not None else None
        raw_max = settings.values.get("MaxDistanceToEnemy") if settings is not None else None
        if (raw_min is not None and raw_max is not None
                and parse_number(raw_min) > 0 and parse_number(raw_max) > 0):
            new_max = parse_number(raw_max) * s.cover_distance_factor
            new_min = min(parse_number(raw_min) * s.cover_distance_factor, new_max)
            sub: dict = {}
            for key, raw, new in (("MinDistanceToEnemy", raw_min, new_min),
                                  ("MaxDistanceToEnemy", raw_max, new_max)):
                if _neq(new, parse_number(raw)):
                    sub[key] = _num(new) + ("f" if raw.strip().endswith(("f", "F")) else "")
            if sub:
                cfg["DefaultCoverSettings"] = sub
    if _neq(s.cover_path_factor, 1.0) and s.cover_path_factor > 0:
        raw = node.values.get("MaxPathLength")
        if raw is not None and parse_number(raw) > 0:
            core = raw.strip()
            if core.lstrip("-").isdigit():           # 2000 bleibt ganzzahlig
                cfg["MaxPathLength"] = str(max(1, int(round(int(core) * s.cover_path_factor))))
            else:
                scaled = _scale_literal(raw, s.cover_path_factor)
                if scaled is not None:
                    cfg["MaxPathLength"] = scaled
    return {"DefaultCoverEvaluator": cfg} if cfg else {}


def _corevars_patch(gd: GameData, s: Settings) -> dict:
    cfg: dict = {}
    if _neq(s.repair_cost_factor, 1.0):
        vanilla = gd.corevar("BaseRepairCostModifier", 0.7)
        cfg["BaseRepairCostModifier"] = _num(vanilla * s.repair_cost_factor)

    m = s.max_carry_weight
    ps = min(s.penalty_start_weight, m - 1.0)
    if _neq(m, VANILLA_MAX_CARRY) or _neq(ps, VANILLA_PENALTY_START):
        t1 = ps + (m - ps) / 3.0
        cfg["InventoryPenaltyLessWeight"] = _num(ps)
        cfg["MediumEffectStartUI"] = _num(ps)
        cfg["CriticalEffectStartUI"] = _num(t1)

    if s.no_overweight_penalty:
        cfg["InventorySPOverweightDrainCoef"] = "0.0"

    # 1.35.0: Blicktempo. Dieselben zwei Schluessel stehen am Player-Struct
    # (40/30) und hier (50.0/30.0) - welchen das Spiel benutzt, ist unbewiesen,
    # also werden beide mit demselben Faktor skaliert. Die fuenfte Recherche
    # hatte sie mit "dafuer gibt es einen Menuepunkt" verworfen; das Menue hat
    # aber nur EINE Empfindlichkeit und kann das Verhaeltnis nicht aendern.
    for key, factor, fallback in (("BaseTurnRate", s.look_speed_h_factor, 50.0),
                                  ("BaseLookUpRate", s.look_speed_v_factor, 30.0)):
        if _neq(factor, 1.0) and factor > 0:
            vanilla = gd.corevar(key, fallback)
            if vanilla > 0:
                cfg[key] = _num(vanilla * factor)

    # Tageslaenge (Nexus-Dauerbrenner "Longer Days"): RealToGameTimeCoef =
    # Spielsekunden je Echtsekunde (Vanilla 24 = ein Spieltag pro Echtstunde).
    # Faktor 2 = halber Koeffizient = doppelt so langer Tag.
    if _neq(s.day_length_factor, 1.0) and s.day_length_factor > 0:
        vanilla = gd.corevar("RealToGameTimeCoef", 24.0)
        value = vanilla / s.day_length_factor
        cfg["RealToGameTimeCoef"] = (str(int(round(value)))
                                     if abs(value - round(value)) < 1e-9
                                     else _num(value))

    # Interaktions-Reichweite (Recherche 05.09.2026): allgemeine
    # Interaktionsdistanz (Aufheben, Tueren) und Behaelter/Verstecke,
    # Vanilla je 200 cm. Leichen haengen am Player (ObjPrototypes).
    if _neq(s.interaction_range_factor, 1.0) and s.interaction_range_factor > 0:
        for key in ("MaxInteractionDistance", "ItemContainerInteractRange"):
            vanilla = gd.corevar(key, 200.0)
            if vanilla > 0:
                cfg[key] = _num(vanilla * s.interaction_range_factor)

    # Sichtfeld (06.09.2026): CutsceneFOVDefault 90, FOVDefault 90 -
    # Absolutwerte, live verglichen. DialogFOVDefault stand hier bis 1.35.0
    # mit dabei und ist zurueckgezogen: im Spiel ohne Wirkung (GitHub #10).
    # Die zwei uebrigen sind unverifiziert und sitzen im selben Struct.
    for key, wanted in (("CutsceneFOVDefault", s.cutscene_fov),
                        ("FOVDefault", s.default_fov)):
        live = gd.corevar(key, 0.0)
        if live > 0 and _neq(wanted, live):
            cfg[key] = _num(wanted)

    # Leichen (06.09.2026, Nexus 'Corpse Despawn Time Increased'): die fuenf
    # Zeiten skalieren (Literalform bleibt: 6000 -> 12000, 1800.0 -> 3600.0),
    # Hoechstzahl Leichen um den Spieler als Absolutwert.
    if _neq(s.corpse_time_factor, 1.0) and s.corpse_time_factor > 0:
        node = gd.corevars.children.get("DefaultConfig")
        # 1.28.0 P5 (par. 1.4): CorpseOffscreenLifetime (3.0 s nach dem Blick
        # weg) und CorpseDespawnToOfflineTimeCoef (0.5) skalieren mit
        for key in ("CorpseOnlineTime", "CorpseSeenOnlineTime", "CorpseLootedOnlineTime",
                    "CorpseALifeOnlineTime", "CorpseTimeout",
                    "CorpseOffscreenLifetime", "CorpseDespawnToOfflineTimeCoef"):
            raw = node.values.get(key) if node is not None else None
            if raw is None or parse_number(raw) <= 0:
                continue
            core = raw.strip().rstrip(";").strip()
            if core.lstrip("-").isdigit():          # 6000 bleibt ganzzahlig
                cfg[key] = str(int(round(int(core) * s.corpse_time_factor)))
            else:
                scaled = _scale_literal(raw, s.corpse_time_factor)
                if scaled is not None:
                    cfg[key] = scaled
    live_max = gd.corevar("CorpseConditionOnlineCount", 0.0)
    if live_max > 0 and int(s.corpse_max_count) != int(live_max):
        cfg["CorpseConditionOnlineCount"] = str(max(1, int(s.corpse_max_count)))

    # Startgeld (06.09.2026): PlayerStartingMoney, Vanilla 0, nur neues Spiel.
    if int(s.starting_money) != int(gd.corevar("PlayerStartingMoney", 0.0)):
        cfg["PlayerStartingMoney"] = str(max(0, int(s.starting_money)))

    # NPC-Taschenlampen im Kampf (Recherche 05.09.2026): Nutzungschance je
    # Rang, Vanilla Newbie 1 / Experienced 0.75 / Veteran 0.5 / Master 0.25,
    # Deckel 1.0; Faktor 0 = nie.
    if _neq(s.npc_flashlight_combat_factor, 1.0) and s.npc_flashlight_combat_factor >= 0:
        node = gd.corevars.children.get("DefaultConfig")
        chance = node.children.get("FlashlightCombatUseChance") if node else None
        if chance is not None:
            ranks: dict = {}
            for rank, raw in chance.values.items():
                value = parse_number(raw, -1.0)
                if value >= 0:
                    ranks[rank] = _num(min(1.0, value * s.npc_flashlight_combat_factor))
            if ranks:
                cfg["FlashlightCombatUseChance"] = ranks

    # 1.26.0 (Ace's CoreVariables-Liste, Shay's Distant Horizons): gerade
    # nach unten (ViewPitchDownLimit -80 -> -90, im Spiel bestaetigt durch
    # craigduk76 auf 1.35.0), Zoom mit leeren Haenden (HandlessFOVAimModifier
    # 0.8, kleiner = mehr Zoom, Deckel 0.2..1.0) und die Sichtweite des
    # A-Life-Rasters (8500 / 7500 cm). "Auf Leitern umschauen"
    # (ClimbViewYaw/PitchLimit) stand bis 1.35.0 hier und ist
    # zurueckgezogen: dieselbe Pak, dasselbe Struct, keine Wirkung (GitHub #11).
    if s.look_straight_down:
        live = gd.corevar("ViewPitchDownLimit", 0.0)
        if live != 0 and _neq(live, -90.0):
            cfg["ViewPitchDownLimit"] = "-90.0"
    if _neq(s.handless_zoom_factor, 1.0) and s.handless_zoom_factor > 0:
        live = gd.corevar("HandlessFOVAimModifier", 0.0)
        if live > 0:
            new = max(0.2, min(1.0, live * s.handless_zoom_factor))
            if _neq(new, live):
                cfg["HandlessFOVAimModifier"] = _num(new)
    if _neq(s.alife_vision_factor, 1.0) and s.alife_vision_factor > 0:
        for key in ("ALifeGridVisionRadius", "GenericModelGridVisionRadius"):
            live = gd.corevar(key, 0.0)
            if live > 0:
                cfg[key] = _num(live * s.alife_vision_factor)

    # 1.27.0 (Schluessel-Sweep): Absolutwerte werden live verglichen,
    # Faktoren ueber _scale_literal (Suffix f bleibt).
    node = gd.corevars.children.get("DefaultConfig")
    raw_of = (lambda key: node.values.get(key) if node is not None else None)
    live = gd.corevar("SlowRunThreshold", -1.0)
    if live >= 0 and _neq(s.slow_run_threshold_pct / 100.0, live):
        cfg["SlowRunThreshold"] = _num(max(0.0, min(1.0, s.slow_run_threshold_pct / 100.0))) + "f"
    live = gd.corevar("ItemSelectorTimeDilationCoefficient", -1.0)
    if live >= 0 and _neq(s.wheel_time_pct / 100.0, live):
        cfg["ItemSelectorTimeDilationCoefficient"] = _num(max(0.05, min(1.0, s.wheel_time_pct / 100.0)))
    for keys, factor, cap in ((("PlayerBedFadeToBlackTime", "PlayerBedBlackScreenTime"), s.sleep_fade_factor, None),
                              (("UntouchedDespawnItemTime", "DespawnItemTime"), s.item_despawn_factor, None),
                              (("VitalMaxEnergeticOveruse", "VitalMaxEnergeticTolerance"), s.energy_tolerance_factor, None),
                              (("ArmorDifferenceCoef",), s.armor_difference_factor, None),
                              (("ArmorDeflectDamageCoefHuman", "ArmorDeflectDamageCoefMutant"), s.armor_deflect_damage_factor, None),
                              (("CalmDamageFromPlayerCoef",), s.calm_damage_factor, None),
                              (("DraggingCorpseSpeedCoef",), s.corpse_drag_factor, 1.0)):
        if not (_neq(factor, 1.0) and factor >= 0):
            continue
        for key in keys:
            raw = raw_of(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            if cap is not None:
                new = min(cap, parse_number(raw) * factor)
                if _neq(new, parse_number(raw)):
                    cfg[key] = _num(new)
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None:
                cfg[key] = scaled
    live = gd.corevar("LastBulletBaseDamageMultiplier", -1.0)
    if live >= 0 and _neq(float(s.last_bullet_multiplier), live):
        cfg["LastBulletBaseDamageMultiplier"] = _num(max(0.0, float(s.last_bullet_multiplier)))
    live = gd.corevar("ArmorDeflectMinChance", -1.0)
    if live >= 0 and _neq(s.armor_deflect_chance_pct / 100.0, live):
        chance = _num(max(0.0, min(1.0, s.armor_deflect_chance_pct / 100.0)))
        cfg["ArmorDeflectMinChance"] = chance
        cfg["ArmorDeflectMaxChance"] = chance
    live = gd.corevar("ItemCostMinPercent", -1.0)
    if live >= 0 and _neq(s.min_resale_pct / 100.0, live):
        cfg["ItemCostMinPercent"] = _num(max(0.0, min(1.0, s.min_resale_pct / 100.0)))
    live_day = gd.corevar("DayStartTime", -1.0)
    if live_day >= 0 and int(s.day_start_hour) != int(live_day):
        cfg["DayStartTime"] = _num(int(s.day_start_hour))
        dawn = gd.corevar("DawnStartTime", -1.0)
        if dawn >= 0 and int(s.day_start_hour) <= int(dawn):
            cfg["DawnStartTime"] = _num(max(0, int(s.day_start_hour) - 1))
    live_eve = gd.corevar("EveningStartTime", -1.0)
    if live_eve >= 0 and int(s.evening_start_hour) != int(live_eve):
        cfg["EveningStartTime"] = _num(int(s.evening_start_hour))
    if s.instant_teleports:
        for key in ("GenericTeleportScreenShowDelay", "GenericTeleportScreenHideDelay"):
            raw = raw_of(key)
            if raw is not None and parse_number(raw) > 0:
                cfg[key] = "0.f"

    # 1.28.0 P1 (Kern-Sweep, docs/CORE_SWEEP_RESEARCH.md par. 1.1): Humpeln
    # nach harter Landung - Array-Eintraege KOMPLETT ausgeben (EffectSID +
    # Threshold, Muster StaminaRegenStateCoefs); der Schalter setzt beide
    # Schwellen auf Vanilla x 1000 und schlaegt den Faktor.
    limp_factor = 1000.0 if s.no_landing_limp else s.limp_threshold_factor
    if _neq(limp_factor, 1.0) and limp_factor > 0:
        arr = node.children.get("LimpEffectSIDToThresholdMap") if node is not None else None
        entries: dict = {}
        changed = False
        for idx, entry in (arr.children.items() if arr is not None else ()):
            sid = entry.values.get("EffectSID")
            raw = entry.values.get("Threshold")
            if sid is None or raw is None:
                continue
            scaled = _scale_literal(raw, limp_factor) if parse_number(raw) > 0 else None
            if scaled is not None and scaled != raw.strip():
                changed = True
            entries[idx] = {"EffectSID": sid.strip(),
                            "Threshold": scaled if scaled is not None else raw.strip()}
        if changed:
            cfg["LimpEffectSIDToThresholdMap"] = entries
    # Blutung je Treffer (VitalBaseBleedingValue 10 gegen MaxBleeding 100)
    # und bei nicht durchschlagenden Treffern (Chance + Punkte, je 1.0)
    for keys, factor in ((("VitalBaseBleedingValue",), s.bleeding_hit_factor),
                         (("BleedingChanceNonPenetrationMod", "BleedingPointsNonPenetrationMod"),
                          s.bleeding_nonpen_factor)):
        if not (_neq(factor, 1.0) and factor >= 0):
            continue
        for key in keys:
            raw = raw_of(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None:
                cfg[key] = scaled
    # Taschenlampe im Dialog: Vanilla dimmt auf 52.5 %
    if s.flashlight_dialog_bright:
        live = gd.corevar("FlashlightDialogIntensityPercent", -1.0)
        if live >= 0 and _neq(live, 1.0):
            cfg["FlashlightDialogIntensityPercent"] = "1.0"
    # Eingefaltet in vorhandene Regler (par. 3b - kein neuer Regler):
    # - Traglast-Ausdauer unterhalb der Ueberlast (InventorySPDrainCoef
    #   0.024) in den Schalter, der InventorySPOverweightDrainCoef auf 0 setzt
    # - Lande-Ausdauer (StaminaFallingDamageCoef 0.5) in den Sprung-Kosten-Regler
    # - fuenf Leiter-Abspielraten (je 1.0f) in climb_speed_factor
    # - vier Reichweiten + Loot-Hoehenfenster (max) in interaction_range_factor
    # - Leichen-Greifzeit (DeadBodyPickUpTime 2.0) INVERS in corpse_drag_factor
    # - drei globale Marker-Distanzen (300/30/20 m) in map_reveal_factor
    if s.no_overweight_penalty:
        raw = raw_of("InventorySPDrainCoef")
        if raw is not None and parse_number(raw) > 0:
            cfg["InventorySPDrainCoef"] = "0.0"
    folded = [
        (("StaminaFallingDamageCoef",), s.stamina_jump, True),
        (("ClimbUpSpeed", "ClimbDownSpeed", "ClimbEnterUpSpeed", "ClimbEnterDownSpeed",
          "ClimbExitUpSpeed"), s.climb_speed_factor, False),
        (("WideTraceInteractionDistance", "AutoInteractionDistance",
          "MutantLootContainerInteractRange", "DragDeadBodyInteractRange",
          "MutantLootInteractHeightMax"), s.interaction_range_factor, False),
        (("MarkerShowingDistance", "MarkerRevealingDistance", "MarkerExploringDistance"),
         s.map_reveal_factor, False),
    ]
    if _neq(s.corpse_drag_factor, 1.0) and s.corpse_drag_factor > 0:
        folded.append((("DeadBodyPickUpTime",), 1.0 / s.corpse_drag_factor, False))
    for keys, factor, allow_zero in folded:
        if not _neq(factor, 1.0) or factor < 0 or (factor == 0 and not allow_zero):
            continue
        for key in keys:
            raw = raw_of(key)
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, factor)
            if scaled is not None:
                cfg[key] = scaled

    # 1.28.0 P2 (Ruestung und Trefferrechnung, par. 1.1): Granatenschutz je
    # Strike-Stufe - Array KOMPLETT ausgeben (ProtectionStrike +
    # GrenadeDamageResist, Literalform mit f bleibt), Deckel 1.0;
    # Faktor 0 = Granaten ignorieren die Ruestung.
    if _neq(s.grenade_resist_factor, 1.0) and s.grenade_resist_factor >= 0:
        arr = node.children.get("StrikeGrenadeResistCoefs") if node is not None else None
        entries = {}
        changed = False
        for idx, entry in (arr.children.items() if arr is not None else ()):
            strike = entry.values.get("ProtectionStrike")
            raw = entry.values.get("GrenadeDamageResist")
            if strike is None or raw is None:
                continue
            scaled = (_scale_literal(raw, s.grenade_resist_factor, cap=1.0)
                      if parse_number(raw) > 0 else None)
            if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                changed = True
            entries[idx] = {"ProtectionStrike": strike.strip(),
                            "GrenadeDamageResist": scaled if scaled is not None else raw.strip()}
        if changed:
            cfg["StrikeGrenadeResistCoefs"] = entries
    # Schutzverlust durch Abnutzung (experimentell, Richtung unbekannt -
    # docs/SPEC.md par. 1.11): EIN Absolutregler fuer beide Koeffizienten,
    # 0..1, live verglichen, Suffix f bleibt.
    wanted_wear = max(0.0, min(1.0, float(s.armor_wear_coef)))
    for key in ("ArmorDurabilityParamsCoef", "HelmetDurabilityParamsCoef"):
        raw = raw_of(key)
        if raw is None:
            continue
        live = parse_number(raw, -1.0)
        if live >= 0 and _neq(wanted_wear, live):
            cfg[key] = _num(wanted_wear) + ("f" if raw.strip().endswith(("f", "F")) else "")
    # Ruestung gegen Anomalie-Schlag (experimentell; Geschwister von
    # ArmorDifferenceCoef 2 / Explosion 0.5 / PlayerMelee 0.6)
    if _neq(s.anomaly_armor_difference_factor, 1.0) and s.anomaly_armor_difference_factor >= 0:
        raw = raw_of("StrikeAnomalyArmorDifferenceCoef")
        if raw is not None and parse_number(raw) > 0:
            scaled = _scale_literal(raw, s.anomaly_armor_difference_factor)
            if scaled is not None:
                cfg["StrikeAnomalyArmorDifferenceCoef"] = scaled

    # 1.28.0 P3 (NPC-Verhalten, par. 1.3): verwundete NPCs. Absolutwerte
    # ganzzahlig, live verglichen (Kommentare hinter den Werten strippt der
    # Parser); UnkillableNPCWoundedStateResurrectionTime (Questrisiko) und
    # WoundHitAreasThresholds (ungeklaert) bleiben bewusst tabu.
    for key, wanted, lo, hi in (("ChanceToGetHealOverTimeWhenWounded", s.wounded_heal_chance, 0, 100),
                                ("CooldownOnFallingWounded", s.wounded_cooldown_s, 0, None),
                                ("HpThresholdToHealWound", s.wounded_heal_threshold, 0, 100)):
        live = gd.corevar(key, -1.0)
        if live < 0:
            continue
        value = max(lo, int(round(float(wanted))))
        if hi is not None:
            value = min(hi, value)
        if value != int(round(live)):
            cfg[key] = str(value)
    if _neq(s.wounded_regen_factor, 1.0) and s.wounded_regen_factor >= 0:
        raw = raw_of("WoundedStateHealthRegen")
        if raw is not None and parse_number(raw) > 0:
            scaled = _scale_literal(raw, s.wounded_regen_factor)
            if scaled is not None:
                cfg["WoundedStateHealthRegen"] = scaled

    # 1.28.0 P4 (Mutanten, par. 1.3 / 1.1): Burer-Waffenfeuer - zehn benannte
    # Unter-Structs (A012 ... A045), also normaler bpatch je Struct; und das
    # Ausweiden: Vanilla true = Animation OHNE Loot-Fenster (beide
    # Animationssaetze liegen in der Datei), false = Fenster-Ablauf.
    if _neq(s.burer_fire_interval_factor, 1.0) and s.burer_fire_interval_factor > 0:
        arr = node.children.get("PossessedWeaponFireIntervals") if node is not None else None
        entries = {}
        for ammo, entry in (arr.children.items() if arr is not None else ()):
            raw = entry.values.get("FireInterval")
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, s.burer_fire_interval_factor)
            if scaled is not None:
                entries[ammo] = {"FireInterval": scaled}
        if entries:
            cfg["PossessedWeaponFireIntervals"] = entries
    if s.mutant_loot_widget and _bool_literal(raw_of("UseMutantLootWithoutWidget")) is True:
        cfg["UseMutantLootWithoutWidget"] = "false"

    # 1.28.0 P5 (Leichen, par. 1.4): die drei Offline-Distanzen sind QUADRIERTE
    # Zentimeter (100 m -> 1e8), ein Distanz-Faktor f wirkt dort als f^2;
    # DistanceToDestroyCorpsesIfOverpopulated (30000 = 300 m) linear und
    # ganzzahlig. Nur DefaultConfig (LowMemoryProfileXSS ist Konsolen-Kram).
    # CorpseRagdollQuestProtection* bleiben tabu.
    if _neq(s.corpse_distance_factor, 1.0) and s.corpse_distance_factor > 0:
        sq = s.corpse_distance_factor * s.corpse_distance_factor
        for key in ("CorpseOfflineSquaredDistance", "CorpseOfflineTimeConditionSquaredDistance",
                    "CorpseOfflineCountConditionSquaredDistance"):
            raw = raw_of(key)
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, sq)
                if scaled is not None:
                    cfg[key] = scaled
        raw = raw_of("DistanceToDestroyCorpsesIfOverpopulated")
        if raw is not None and parse_number(raw) > 0:
            cfg["DistanceToDestroyCorpsesIfOverpopulated"] = str(
                max(1, int(round(parse_number(raw) * s.corpse_distance_factor))))
    live = gd.corevar("AlifeCorpsesHardcap", -1.0)
    if live >= 0 and int(s.alife_corpse_hardcap) != int(round(live)):
        cfg["AlifeCorpsesHardcap"] = str(max(1, int(s.alife_corpse_hardcap)))

    # 1.28.0 P6 (Strahlungsfelder, par. 1.2): die vier harmlosen Presets
    # (Light/Medium/Strong/Topaz) - ueber den PRESET-NAMEN gefiltert, nicht
    # ueber den Index, damit Deadly und RadBlock (Karten-Todeszonen mit 9000
    # Schaden) und Custom garantiert draussen bleiben. Array-Eintraege
    # komplett; RadioactivityValue bleibt unangetastet.
    rad_on = [(f, key, cap) for f, key, cap in
              ((s.radiation_dose_factor, "RadiationPerSecondValue", None),
               (s.radiation_filter_factor, "PostProcessRadiationIntensity", 1.0),
               (s.geiger_volume_factor, "GeigerRadiationIntensity", 1.0))
              if _neq(f, 1.0) and f >= 0]
    if rad_on:
        arr = node.children.get("RadiationPresetValues") if node is not None else None
        entries: dict = {}
        for idx, entry in (arr.children.items() if arr is not None else ()):
            preset = (entry.values.get("Preset") or "").strip()
            if preset not in RADIATION_PRESETS_OK:
                continue
            full = {k: v.strip() for k, v in entry.values.items()}
            changed = False
            for factor, key, cap in rad_on:
                raw = entry.values.get(key)
                if raw is None or parse_number(raw) <= 0:
                    continue
                scaled = _scale_literal(raw, factor, cap=cap)
                if scaled is not None and _neq(parse_number(scaled), parse_number(raw)):
                    full[key] = scaled
                    changed = True
            if changed:
                entries[idx] = full
        if entries:
            cfg["RadiationPresetValues"] = entries
    # Kampfmusik (par. 1.3): Schwelle (ein normaler NPC zaehlt 10) und
    # Nachlauf, beide absolut und live verglichen (Suffix f bleibt).
    for key, wanted in (("MusicManagerCombatScoreThreshold", s.music_combat_threshold),
                        ("MusicManagerCombatEnemyAttackActionLifetimeSeconds", s.music_combat_lifetime)):
        raw = raw_of(key)
        if raw is None:
            continue
        live = parse_number(raw, -1.0)
        if live >= 0 and _neq(float(wanted), live):
            cfg[key] = _num(max(0.0, float(wanted))) + ("f" if raw.strip().endswith(("f", "F")) else "")

    # 1.28.0 P7 (Artefakte und Loot, par. 3b / 1.3): der Mindestabstand, ab dem
    # ein Artefakt ueberhaupt wegzuhuepfen beginnt, gehoert zum Keep-away-Regler
    # (die eigentliche Distanz steht je Artefakt in ItemPrototypes); dazu die
    # Loot-Neuauslosung beim Rangaufstieg (Radius 400 m, Verzoegerung 10 s).
    for key, factor in (("ArtifactStrafeMinDistance", s.artifact_keepaway_factor),
                        ("RegenerateItemsOnRankUpdateRadius", s.loot_reroll_radius_factor),
                        ("RegenerateItemsOnRankUpdateTimer", s.loot_reroll_timer_factor)):
        if not (_neq(factor, 1.0) and factor > 0):
            continue
        raw = raw_of(key)
        if raw is None or parse_number(raw) <= 0:
            continue
        scaled = _scale_literal(raw, factor)
        if scaled is not None:
            cfg[key] = scaled

    # 1.28.0 P8 (Haendler und Wirtschaft, par. 1.3): Reparaturpreis je Ruf -
    # der Schalter zieht alle vier Stufen (Enemy 2.0 / Disaffection 1.5 /
    # Neutral 1.0 / Friend 0.75) auf den Neutral-Wert 1.0, Array-Eintraege
    # komplett (RelationLevel + Modifier). Dazu die Geruechte-Auffrischung.
    if s.repair_cost_reputation:
        arr = node.children.get("ReputationRepairCostModifiers") if node is not None else None
        entries: dict = {}
        changed = False
        for idx, entry in (arr.children.items() if arr is not None else ()):
            level = entry.values.get("RelationLevel")
            raw = entry.values.get("Modifier")
            if level is None or raw is None:
                continue
            if _neq(parse_number(raw), 1.0):
                changed = True
            entries[idx] = {"RelationLevel": level.strip(), "Modifier": "1.0"}
        if changed:
            cfg["ReputationRepairCostModifiers"] = entries
    live = gd.corevar("InfotopicRefreshHours", -1.0)
    if live >= 0 and int(s.infotopic_refresh_hours) != int(round(live)):
        cfg["InfotopicRefreshHours"] = str(max(1, int(s.infotopic_refresh_hours)))

    if _neq(s.stamina_sprint, 1.0):
        # Dauer-Drain (Sprint/Run): komplette Eintraege ausgeben
        node = gd.corevars.children.get("DefaultConfig")
        coefs = node.children.get("StaminaRegenStateCoefs") if node else None
        if coefs:
            entries: dict = {}
            for idx, entry in coefs.children.items():
                tag = entry.values.get("StateTag", "EStateTag::None")
                value = parse_number(entry.values.get("Value"))
                if value < 0 and tag in SPRINT_DRAIN_TAGS:
                    value *= s.stamina_sprint
                entries[idx] = {"StateTag": tag, "Value": _num(value)}
            cfg["StaminaRegenStateCoefs"] = entries

    return {"DefaultConfig": cfg} if cfg else {}


def _items_patch(gd: GameData, s: Settings) -> tuple[dict, dict]:
    """ItemPrototypes: Gewichte, Munitions-Mods, Detektoren, Magazine,
    Ruestungsschutz. Liefert (Basis-Patches, {Edition: Patches}) — die
    Editions-Ruestungen (SEVA Monolith & Co.) werden in den jeweiligen
    DLCGameData-Zweig gepatcht."""
    patches: dict = {}
    if _neq(s.item_weight_factor, 1.0) and s.item_weight_categories:
        for sid, (cat, weight) in sorted(gd.item_weights().items()):
            if cat not in s.item_weight_categories:
                continue
            patches[sid] = {"Weight": _num(weight * s.item_weight_factor)}
    if s.ignore_equipped_weight:
        patches["[0]"] = {"IgnoreEquippedWeight": "true"}
    # 1.33.0: maximale Haltbarkeit von Waffen und Ruestung (BaseDurability).
    # Bis dahin haben wir den Wert nur GELESEN (Haendler-Mindestzustand),
    # nie gepatcht - "Better Durability 3.0" (Nexus 1695) nimmt ihn mal
    # fuenf. gear_durability() liefert nur echte Ausruestung (die 1.0 des
    # Basis-Structs faellt raus). Ganzzahlig macht das Spiel selbst nicht,
    # also bleibt der skalierte Wert eine Kommazahl wie in Vanilla.
    if _neq(s.gear_durability_factor, 1.0) and s.gear_durability_factor > 0:
        for sid, (_cat, vanilla) in sorted(gd.gear_durability().items()):
            new = vanilla * s.gear_durability_factor
            if _neq(new, vanilla):
                patches.setdefault(sid, {})["BaseDurability"] = _num(new)
    # Quest-Items wiegen nichts (Nexus "quest item weight to 0"): die
    # Kategorie-Regler lassen Quest-Items aus, hier explizit Weight = 0.
    if s.quest_items_weightless:
        for sid in sorted(gd.quest_items_with_weight()):
            patches.setdefault(sid, {})["Weight"] = "0.0"
    # Artefakt-Slots (06.09.2026, Nexus 'Armor Artifact Slots'): +N je
    # Koerperruestung, Deckel 5 = Vanilla-Maximum (3 Ruestungen haben 5).
    # Helme bleiben draussen. Editions-Ruestungen in den DLC-Zweig.
    dlc_slot_patches: dict = {}
    if int(s.artifact_slots_bonus) > 0:
        for sid, (vanilla, edition) in sorted(gd.armor_artifact_slots().items()):
            target = min(5, vanilla + int(s.artifact_slots_bonus))
            if target == vanilla:
                continue
            bucket = patches if edition is None else dlc_slot_patches.setdefault(edition, {})
            bucket.setdefault(sid, {})["ArtifactSlots"] = str(target)
    # Pistolenslot (06.09.2026, Nexus 1735 dukeen / 1533 overjoony): Waffen
    # der gewaehlten Klassen bekommen ItemSlotType = Pistol (Text live aus
    # einem Pistolen-Item). Die Hauptslots nehmen weiterhin jede Waffe.
    level = int(s.pistol_slot_level)
    if level > 0:
        literal = gd.pistol_slot_literal()
        allowed = {1: {"smg"}, 2: {"smg", "shotgun"}}.get(level)
        for sid, (cat, slot, edition) in sorted(gd.slot_weapon_items().items()):
            if literal is None or slot != "PrimaryWeapon":
                continue
            if allowed is not None and cat not in allowed:
                continue
            bucket = patches if edition is None else dlc_slot_patches.setdefault(edition, {})
            bucket.setdefault(sid, {})["ItemSlotType"] = literal

    # Munitions-Modifikatoren (pro Munitions-Item, aufgeloeste Vanilla-Werte).
    # Kaskade: Einzelsorte > globaler Regler -- der Override ERSETZT den
    # globalen Faktor, er stapelt sich nicht (vgl. _weapon_factor).
    ammo_globals = {
        "damage": s.ammo_damage_factor,
        "piercing": s.ammo_piercing_factor,
        "armordamage": s.ammo_armor_damage_factor,
        "cover": s.ammo_cover_factor,
        "stack": s.ammo_stack_factor,
        "bleeding": s.ammo_bleeding_factor,
        "recoil": s.ammo_recoil_factor,
        "flatness": s.ammo_flatness_factor,
        "wear": s.ammo_wear_factor,
        "dispersion": s.ammo_dispersion_factor,
        "aimdispersion": s.ammo_aim_dispersion_factor,
    }
    # Ohne "or s.ammo_overrides" faende ein Pak mit AUSSCHLIESSLICH
    # Einzelsorten-Overrides gar nicht statt.
    if any(_neq(f, 1.0) for f in ammo_globals.values()) or s.ammo_overrides:
        for sid, mods in sorted(gd.ammo_mods().items()):
            over = s.ammo_overrides.get(sid) or {}
            cfg = {}
            for param in AMMO_PARAMS:          # Reihenfolge = Patch-Reihenfolge
                key = AMMO_PARAM_KEYS[param]
                if key not in mods:
                    continue
                factor = over.get(param, ammo_globals[param])
                if not _neq(factor, 1.0):
                    continue
                vanilla = mods[key]
                scaled = vanilla * factor
                if param == "stack":
                    # Stapelgroesse ist eine STUECKZAHL: ganzzahlig, nie unter
                    # 1, und gedeckelt auf 300000 — den Wert, den das Spiel
                    # selbst fuer "praktisch unbegrenzt" benutzt (PDAs,
                    # Notizen, Schluessel). Darueber hinaus zu gehen waere
                    # geraten, nicht gemessen.
                    new_stack = max(1, min(300000, int(round(scaled))))
                    if new_stack != int(vanilla):
                        cfg[key] = str(new_stack)
                    continue
                # Vanilla 0 bleibt 0 -> _neq faengt es ab: kein Scheinpatch,
                # kein Absturz (A545D ArmorPiercingMod ist 0.0).
                if _neq(scaled, vanilla):
                    cfg[key] = _num(scaled)
            if cfg:
                patches.setdefault(sid, {}).update(cfg)

    # Stapelgroesse Nahrung & Medizin (GitHub Issue #7, Molkerr). Vanilla 999
    # bei 24 Gegenstaenden — eine Grenze, die man im Spiel kaum erreicht; der
    # Tooltip sagt das auch. Die Gitarre (MaxStackCount 1) faellt durch die
    # >1-Regel in stack_counts() heraus.
    if _neq(s.consumable_stack_factor, 1.0):
        for sid, vanilla in sorted(gd.stack_counts("consumable").items()):
            target = max(1, min(300000, int(round(vanilla * s.consumable_stack_factor))))
            if target != vanilla:
                patches.setdefault(sid, {})["MaxStackCount"] = str(target)

    # Platz im Inventar je Gegenstand (1.32.0): ItemGridWidth/-Height
    # stehen an allen 1375 Items (1x1 bis 6x3). Ganzzahlig, nie unter 1 -
    # ein Gegenstand ohne Flaeche waere im Raster nicht darstellbar.
    if _neq(s.item_grid_factor, 1.0) and s.item_grid_factor > 0:
        for sid, node in sorted(gd.items.children.items()):
            if sid == "[0]" or "#" in sid:
                continue
            cfg = {}
            for key in ("ItemGridWidth", "ItemGridHeight"):
                raw = node.values.get(key)
                if raw is None:
                    continue
                value = parse_number(raw)
                if value <= 0:
                    continue
                new = max(1, int(round(value * s.item_grid_factor)))
                if new != int(value):
                    cfg[key] = str(new)
            if cfg:
                patches.setdefault(sid, {}).update(cfg)

    # Dauer von Inventar-Aktionen (1.32.0), INVERS: 200 % = halb so lang.
    # Vanilla 2.5 bis 5.0 s an 243 Gegenstaenden.
    if _neq(s.inventory_action_factor, 1.0) and s.inventory_action_factor > 0:
        for sid, node in sorted(gd.items.children.items()):
            if sid == "[0]" or "#" in sid:
                continue
            raw = node.values.get("InventoryActionTime")
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, 1.0 / s.inventory_action_factor)
            if scaled is not None and scaled != raw.strip():
                patches.setdefault(sid, {})["InventoryActionTime"] = scaled

    # Packungsgroesse der Munition (1.31.0, aus "Stalker Unlimited"):
    # wieviele Schuss eine aufgesammelte Packung hergibt. Bewusst NUR ein
    # globaler Regler und KEIN Baum-Parameter — das ist eine Fundmenge,
    # kein Ballistik-Wert, und der Sorten-Baum haette sonst zehn Regler.
    if _neq(s.ammo_pack_factor, 1.0):
        for sid, vanilla in sorted(gd.ammo_pack_counts().items()):
            target = max(1, int(round(vanilla * s.ammo_pack_factor)))
            if target != int(vanilla):
                patches.setdefault(sid, {})["AmmoPackCount"] = str(target)

    # Artefakt-Detektor-Items (Echo/Bear/Veles/Gilka): Reichweiten skalieren
    if _neq(s.detector_range_factor, 1.0):
        for sid, radii in sorted(gd.detector_items().items()):
            cfg = {key: _num(value * s.detector_range_factor) + "f"
                   for key, value in radii.items()}
            patches.setdefault(sid, {}).update(cfg)

    # Magazin-Aufsaetze: Magazine.MaxAmmo (80 konkrete Magazine, ganzzahlig).
    # Seit 03.09. kaskadiert (Nexus-Wunsch Qfander): ein Magazin folgt den
    # Waffen, die es laut WeaponReloadTimePerAttachment benutzen - irgendein
    # Einzelwaffen-Override gewinnt, sonst irgendein Kategorie-Faktor, sonst
    # der globale Regler. Geteilte Magazine (GunAK_MagPaired: AK-Familie)
    # folgen damit der ersten Waffe mit Override - Tooltip/FAQ sagen es.
    # Magazine ohne bekannte Waffe (Waisen) sehen nur den globalen Regler.
    magazine_on = ((_neq(s.magazine_factor, 1.0) and s.magazine_factor > 0)
                   or any("magazine" in p for p in s.weapon_overrides.values())
                   or any("magazine" in p
                          for p in s.weapon_category_factors.values()))
    if magazine_on:
        users: dict[str, list[str]] = {}
        for wgs, mags in gd.weapon_magazines().items():
            for m in mags:
                users.setdefault(m, []).append(wgs)
        dlc_eds = gd.dlc_weapon_editions()

        def magazine_factor(mag_sid: str) -> float:
            wgs_list = sorted(users.get(mag_sid, []))
            for wgs in wgs_list:
                value = s.weapon_overrides.get(wgs, {}).get("magazine")
                if value is not None:
                    return value
            for wgs in wgs_list:
                ed = dlc_eds.get(wgs)
                cat = (gd.dlc_weapon_category(ed, wgs) if ed is not None
                       else gd.weapon_category(wgs))
                if cat is None:
                    continue
                value = s.weapon_category_factors.get(cat, {}).get("magazine")
                if value is not None:
                    return value
            return s.magazine_factor

        for sid, value in sorted(gd.magazine_items().items()):
            f = magazine_factor(sid)
            if not _neq(f, 1.0) or f <= 0:
                continue
            scaled_int = max(1, int(round(value * f)))
            if scaled_int != int(value):
                patches.setdefault(sid, {})["Magazine"] = {
                    "MaxAmmo": str(scaled_int)}

    # Ruestungsschutz je Schadensart (nur die Spieler-Protection;
    # ProtectionNPC bleibt unangetastet). Kaskade wie bei der Munition:
    # der Einzelruestungs-Override ERSETZT den globalen Faktor fuer diesen
    # Wert an dieser Ruestung, er stapelt sich nicht.
    protection_globals = {
        "strike": s.armor_strike_factor,
        "burn": s.armor_burn_factor,
        "shock": s.armor_shock_factor,
        "chemical": s.armor_chemical_factor,
        "radiation": s.armor_radiation_factor,
        "psy": s.armor_psy_factor,
    }
    # Ohne "or s.armor_overrides" faende ein Pak mit AUSSCHLIESSLICH
    # Einzelruestungs-Overrides gar nicht statt (vgl. Ammo oben).
    dlc_patches: dict[str, dict] = {}
    if any(_neq(f, 1.0) for f in protection_globals.values()) or s.armor_overrides:
        for sid, values in sorted(gd.armor_protection().items()):
            over = s.armor_overrides.get(sid) or {}
            cfg = {}
            for param in ARMOR_PARAMS:         # Reihenfolge = Patch-Reihenfolge
                key = ARMOR_PARAM_KEYS[param]
                if key not in values:          # 0 in Vanilla: kein Patch
                    continue
                factor = over.get(param, protection_globals[param])
                if _neq(factor, 1.0):
                    cfg[key] = _num(values[key] * factor)
            if cfg:
                patches.setdefault(sid, {}).setdefault("Protection", {}).update(cfg)
        # Editions-Ruestungen: dieselbe Kaskade, aber der Patch gehoert in
        # den DLCGameData-Zweig der jeweiligen Edition (analog Waffen)
        for sid, (slot, values, ed) in sorted(gd.dlc_player_armors().items()):
            over = s.armor_overrides.get(sid) or {}
            cfg = {}
            for param in ARMOR_PARAMS:
                key = ARMOR_PARAM_KEYS[param]
                if key not in values:
                    continue
                factor = over.get(param, protection_globals[param])
                if _neq(factor, 1.0):
                    cfg[key] = _num(values[key] * factor)
            if cfg:
                dlc_patches.setdefault(ed, {}).setdefault(sid, {}).setdefault(
                    "Protection", {}).update(cfg)
    for edition, extra in dlc_slot_patches.items():
        for sid, cfg in extra.items():
            dlc_patches.setdefault(edition, {}).setdefault(sid, {}).update(cfg)

    # --- 1.33.0: dieselben Regler auch fuer die Editions-Gegenstaende ------
    # Gemeldet von Molkerr (GitHub #9, 07.09.2026): "Resizing icons in the
    # inventory doesn't work with DLC armor and weapons". Stimmt - die 22
    # Editions-Stuecke (Deluxe 11, PreOrder 4, Ultimate 7) deklarieren
    # Weight, ItemGridWidth/-Height, InventoryActionTime und BaseDurability
    # SELBST, aber bis hierher lief nur der Basiszweig. Eine frueher Sitzung
    # hatte "DLC-Gewichte, nur 22 Items, lohnt nicht" notiert - genau das ist
    # jemandem aufgefallen. Kategorie kommt aus der Vererbungskette
    # (dlc_item_chain springt in die Basis-Templates).
    grid_on = _neq(s.item_grid_factor, 1.0) and s.item_grid_factor > 0
    act_on = _neq(s.inventory_action_factor, 1.0) and s.inventory_action_factor > 0
    dur_on = _neq(s.gear_durability_factor, 1.0) and s.gear_durability_factor > 0
    weight_on = _neq(s.item_weight_factor, 1.0) and bool(s.item_weight_categories)
    if grid_on or act_on or dur_on or weight_on:
        for edition, trees in gd.dlc_editions.items():
            tree = trees.get("items")
            for sid, node in sorted((tree.children if tree else {}).items()):
                if sid.startswith("[") or "#" in sid or sid.startswith("Template"):
                    continue
                cfg: dict = {}
                if grid_on:
                    for key in ("ItemGridWidth", "ItemGridHeight"):
                        value = parse_number(node.values.get(key))
                        if value > 0:
                            new = max(1, int(round(value * s.item_grid_factor)))
                            if new != int(value):
                                cfg[key] = str(new)
                if act_on:
                    value = parse_number(node.values.get("InventoryActionTime"))
                    if value > 0:
                        new = value / s.inventory_action_factor
                        if _neq(new, value):
                            cfg["InventoryActionTime"] = _num(new)
                if dur_on:
                    value = parse_number(node.values.get("BaseDurability"))
                    if value > 1.0:
                        new = value * s.gear_durability_factor
                        if _neq(new, value):
                            cfg["BaseDurability"] = _num(new)
                if weight_on:
                    value = parse_number(node.values.get("Weight"))
                    cat = None
                    for step in gd.dlc_item_chain(edition, sid):
                        if step.name in CATEGORY_TEMPLATES:
                            cat = CATEGORY_TEMPLATES[step.name]
                            break
                    if value > 0 and cat in s.item_weight_categories:
                        new = value * s.item_weight_factor
                        if _neq(new, value):
                            cfg["Weight"] = _num(new)
                if cfg:
                    dlc_patches.setdefault(edition, {}).setdefault(sid, {}).update(cfg)
    armor_extensions.apply(gd, s, patches, dlc_patches)
    return patches, dlc_patches


def _passive_detector_patch(gd: GameData, s: Settings) -> dict:
    """Anomalie-Piepser & Searchpoint-Scanner: DetectorRadius skalieren."""
    if not _neq(s.detector_range_factor, 1.0):
        return {}
    patches: dict = {}
    for name, node in gd.passivedetectors.children.items():
        if "#" in name:
            continue
        radius = parse_number(node.values.get("DetectorRadius"))
        if radius > 0:
            patches[name] = {
                "DetectorRadius": _num(radius * s.detector_range_factor)}
    return patches


def _fasttravel_patch(gd: GameData, s: Settings) -> dict:
    """RequiredMoney je Reiseziel skalieren (0 = Schnellreise gratis); seit
    1.26.0 dazu die Uebergewichts-Sperre (OverweightLock Full/Partial/NoLock,
    die drei Werte stehen so in der Spiel-EXE) und GuideDelay (Vanilla 120,
    Bedeutung im Spiel offen) je Guide."""
    cost_on = _neq(s.fast_travel_cost_factor, 1.0)
    wanted_lock = FAST_TRAVEL_LOCKS.get(int(s.fast_travel_lock), FAST_TRAVEL_LOCKS[2])
    lock_on = wanted_lock != FAST_TRAVEL_LOCKS[2]
    delay_on = _neq(s.guide_delay_factor, 1.0) and s.guide_delay_factor >= 0
    if not (cost_on or lock_on or delay_on):
        return {}
    patches: dict = {}
    for sid, node in gd.fasttravel.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        cfg: dict = {}
        locations = node.children.get("Locations")
        if cost_on and locations is not None:
            entries: dict = {}
            for idx, entry in locations.children.items():
                money = parse_number(entry.values.get("RequiredMoney"))
                if money > 0:
                    entries[idx] = {"RequiredMoney": _num(
                        money * s.fast_travel_cost_factor)}
            if entries:
                cfg["Locations"] = entries
        if lock_on:
            live = (gd.resolve(gd.fasttravel, sid, "OverweightLock") or "").strip()
            if live and live != wanted_lock:
                cfg["OverweightLock"] = wanted_lock
        if delay_on:
            raw = gd.resolve(gd.fasttravel, sid, "GuideDelay")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.guide_delay_factor)
                if scaled is not None:
                    cfg["GuideDelay"] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _restock_patch(gd: GameData, s: Settings) -> dict:
    """TradeRegen-Bedingungen: Days/Hours skalieren (Minimum 1)."""
    if not _neq(s.trader_restock_factor, 1.0):
        return {}
    patches: dict = {}
    for sid, node in gd.boolproviders.children.items():
        if not sid.startswith("TradeRegen") or "#" in sid:
            continue
        for key in ("Days", "Hours"):
            raw = node.values.get(key)
            if raw is None:
                continue
            vanilla = parse_number(raw)
            scaled = max(1, int(round(vanilla * s.trader_restock_factor)))
            if scaled != int(vanilla):
                patches[sid] = {key: str(scaled)}
    return patches


def _trade_patch(gd: GameData, s: Settings) -> dict:
    durability_on = _neq(s.trader_min_durability_pct, 40.0)
    buy_on = _neq(s.trader_buy_price_factor, 1.0)
    sell_on = _neq(s.trader_sell_price_factor, 1.0)
    if not (durability_on or buy_on or sell_on):
        return {}
    min_dur = f"{_num(s.trader_min_durability_pct / 100.0)}f"
    patches: dict = {}
    for trader, entries in sorted(gd.traders().items()):
        gens: dict = {}
        for idx, values in entries.items():
            patch: dict = {}
            if durability_on and (
                "WeaponSellMinDurability" in values or "ArmorSellMinDurability" in values
            ):
                patch["WeaponSellMinDurability"] = min_dur
                patch["ArmorSellMinDurability"] = min_dur
            if buy_on and "BuyModifier" in values:
                patch["BuyModifier"] = f"{_num(values['BuyModifier'] * s.trader_buy_price_factor)}f"
            if sell_on and "SellModifier" in values:
                patch["SellModifier"] = f"{_num(values['SellModifier'] * s.trader_sell_price_factor)}f"
            if patch:
                gens[idx] = patch
        if gens:
            patches[trader] = {"TradeGenerators": gens}
    return patches


# ------------------------------------------------------------------ assembly

def _emission_patch(gd: GameData, s: Settings) -> dict:
    """Emissions-Dauer: reine ZEITSTRECKUNG des Default-Prototyps.

    Alle Zeitwerte der Ablauf-Struktur (PhaseStartTime, PhaseDuration,
    AIEventStartTime) werden mit demselben Faktor multipliziert — damit
    bleiben auch die Vanilla-Ueberlappungen (ShockWave laeuft in die
    Active-Phase hinein) exakt erhalten. Zwei bewusste Ausnahmen:
    die ActivateQuest-Stufe behaelt ihre Dauer (Quest-Triggerfenster),
    und die 5 Story-Emissionen (E06/E15) werden gar nicht angefasst
    (der Accessor liefert nur den Default-Prototyp)."""
    f = s.emission_duration_factor
    if not _neq(f, 1.0) or f <= 0:
        return {}
    key, stages, aievents = gd.emission_default_timeline()
    if key is None or stages is None:
        return {}
    patches: dict = {}

    def scale_into(dst: dict, node, field: str, skip: bool = False):
        raw = node.values.get(field)
        if raw is None:
            return
        value = parse_number(raw)
        new = value if skip else value * f
        if _neq(new, value):
            dst[field] = _num(new)

    stage_cfg: dict = {}
    for idx, stage in stages.children.items():
        quest_trigger = ("ActivateQuest"
                         in (stage.values.get("StageID") or ""))
        cfg: dict = {}
        scale_into(cfg, stage, "PhaseStartTime")
        scale_into(cfg, stage, "PhaseDuration", skip=quest_trigger)
        if cfg:
            stage_cfg[idx] = cfg
    if stage_cfg:
        patches.setdefault(key, {})["Stages"] = stage_cfg
    event_cfg: dict = {}
    for idx, event in (aievents.children.items() if aievents else ()):
        cfg: dict = {}
        scale_into(cfg, event, "AIEventStartTime")
        if cfg:
            event_cfg[idx] = cfg
    if event_cfg:
        patches.setdefault(key, {})["AIEvents"] = event_cfg
    return patches


def _quest_timer_patch(gd: GameData, s: Settings) -> dict:
    """Cooldown wiederholbarer Quests (Nexus-Wunsch).

    Fundort: SetTimer-Knoten der RSQ-Quests in QuestNodePrototypes.cfg
    (Vanilla: 8 Knoten, alle InGameHours = 24 — die Wartezeit, bis ein
    Auftraggeber neue Jobs hat). NUR QuestSID "RSQ*" wird angefasst; die
    78 uebrigen SetTimer gehoeren zu Story-/Nebenquests und bleiben tabu.
    Die 75-MB-Datei wird wie beim Loot-Regler NUR geparst, wenn der
    Faktor nicht auf 100 % steht. Faktor 0 = sofort neue Jobs (bewaehrtes
    Muster der "No Quest Delay"-Mods). Bereits laufende Timer im Save
    ticken mit ihrer alten Endzeit fertig."""
    if not _neq(s.repeatable_quest_factor, 1.0) or s.repeatable_quest_factor < 0:
        return {}
    patches: dict = {}
    for sid, hours in sorted(gd.repeatable_quest_timers().items()):
        new = max(0, int(round(hours * s.repeatable_quest_factor)))
        if new != int(hours):
            patches[sid] = {"InGameHours": str(new)}
    return patches


def _quest_limit_patch(gd: GameData, s: Settings) -> dict:
    """Jobs, die ein Auftraggeber pro Runde ausgibt (GitHub Issue #8).

    Fundort: je RSQ-Geber EIN If-Knoten mit `Less <Zaehler> 3` in
    QuestNodePrototypes.cfg. Das ist die einzige Zahl, die das Limit setzt —
    der Zaehler wird beim Abgeben eines Jobs nie heruntergezaehlt, nur der
    24-h-Timer setzt ihn auf 0 zurueck (das ist der Cooldown-Regler
    nebenan). Beide Schrauben zusammen ergeben "wie viele Jobs, wie oft".

    Gedeckelt wird je Geber auf seinen eigenen Aufgaben-Topf (6 bis 10):
    mehr Jobs als er verschiedene Aufgaben hat, zieht nur Wiederholungen.

    Der Bedingungs-Eintrag wird KOMPLETT ausgegeben (alle Schluessel, nicht
    nur VariableValue): ob {bpatch} verschachtelte Array-Eintraege
    zusammenfuehrt oder ersetzt, ist nicht belegt (docs/SPEC.md par. 0) —
    komplett ist der Patch unter beiden Lesarten richtig.

    Die 75-MB-Datei wird nur geparst, wenn der Regler nicht auf Vanilla
    steht (dasselbe Lazy-Muster wie beim Cooldown-Regler)."""
    target = int(s.repeatable_jobs_per_round)
    if target == Settings.repeatable_jobs_per_round or target < 1:
        return {}
    patches: dict = {}
    for giver in gd.repeatable_quest_givers():
        want = min(target, giver["pool"])
        if not _neq(want, giver["cap"]):
            continue
        outer, inner = giver["cond_path"]
        conditions = giver["cap_node"].children["Conditions"]
        entry = _struct_dict(conditions.children[outer].children[inner])
        entry["VariableValue"] = str(want)
        patches[giver["cap_key"]] = {"Conditions": {outer: {inner: entry}}}
    return patches


def _quest_multi_patch(gd: GameData, s: Settings) -> dict:
    """Re-arm the existing offer dialog after accepting a job.

    Acceptance is confirmed by Molkerr (GitHub #9, 10 September 2026),
    but he must interact again; this does not force the conversation open.
    The earlier End=false workaround did not protect sibling jobs because
    they shared a journal. quest_jobs.build_job_isolation now separates
    journals and guards round cleanup, leaving the End behavior vanilla.
    """
    if not s.repeatable_jobs_multi:
        return {}
    patches: dict = {}
    for giver in gd.repeatable_quest_givers():
        accept = giver.get("accept")
        dialog_sid = giver.get("dialog_sid")
        dialog = giver.get("dialog_node")
        if not (accept and dialog_sid and dialog is not None):
            continue          # Geber ohne erkennbare Zusage bleibt vanilla
        launchers = dialog.children.get("Launchers")
        if launchers is None:
            continue
        flipped: dict = {}
        for idx, entry in launchers.children.items():
            if (entry.values.get("Excluding") or "").strip() != "true":
                continue
            conns = entry.children.get("Connections")
            if conns is None:
                continue
            sources = [(c.values.get("SID") or "").strip()
                       for c in conns.children.values()]
            if not sources:
                continue
            # Zusage-Wache oder Job-Start-Wache: umdrehen. Finish-Wache und
            # alles andere: unangetastet, wie bei der Vorlage.
            is_accept = accept in sources
            is_start = all("OnJournalQuestEvent" in src and src.endswith("_Start")
                           for src in sources)
            if not (is_accept or is_start):
                continue
            complete: dict = {}
            for cidx, c in conns.children.items():
                one = {"SID": (c.values.get("SID") or "").strip()}
                if "Name" in c.values:
                    one["Name"] = (c.values.get("Name") or "").strip()
                complete[cidx] = one
            flipped[idx] = {"Excluding": "false", "Connections": complete}
        if flipped:
            patches.setdefault(dialog_sid, {})["Launchers"] = flipped
        # End behavior stays vanilla. build_job_isolation guards cleanup
        # until every independent journal has finished/cancelled.
    return patches

def _quest_menu_patch(gd: GameData, s: Settings) -> dict:
    """Job-Menue statt Abbruch-Zweig, wenn schon ein Job gehalten wird
    (DialogPrototypes; Teil 2 des Mehrfach-Job-Schalters, 1.36.0).

    Gemessen 09.09.2026: jede der acht Job-Dialogketten beginnt mit einem
    If-Knoten, dessen True-Zweig eine Bridge-Bedingung `NotEqual` auf die
    Zusage (`Technical_GetQuest`) traegt - Zusage noch nicht erfolgt: Job-
    Menue; erfolgt: Abbruch-Zweig. Solange das Ergebnis der Zusage steht,
    fuehrt der wieder geoeffnete Dialog also in den Abbruch-Zweig. Genau das
    hat Molkerr auf 1.35.0 gesehen ("nur noch die Abbruch-Zeile").

    Zone Contracts loest das mit einem Zusatzknoten, der das Ergebnis der
    Zusage drei Sekunden nach der Annahme loescht (`_quest_taken_patch` tut
    dasselbe). Dieser Builder ist der BODEN darunter, der auch dann haelt,
    wenn neue Knoten nicht geladen werden: der False-Zweig des If-Knotens
    zeigt per {bpatch} auf dasselbe Ziel wie der True-Zweig, das Menue.
    Abbrechen geht weiter ueber den eigenen "Auftrag abbrechen"-Dialog, den
    die Zusage scharf macht. Nur der eine Schluessel wird geschrieben,
    `Terminate` und alles andere bleibt. Erkennung datengetrieben (siehe
    GameData.job_menu_switch).

    ⚠ Erste Patchdatei des Werkzeugs in DialogPrototypes: neue Datei in
    NEEDED_FILES (31.6 MB, lazy), CACHE_SCHEMA 23. Dieselbe Regel wie bei
    QuestNodePrototypes - eine Datei je Familie, Patch als
    `DialogPrototypes/DialogPrototypes_patch_<Mod>.cfg`; RSO legt dort
    eigene Dateien ab, die Familie nimmt also Patches an."""
    if not s.repeatable_jobs_multi:
        return {}
    patches: dict = {}
    for giver in gd.repeatable_quest_givers():
        accept = giver.get("accept")
        dialog = giver.get("dialog_node")
        if not (accept and dialog is not None):
            continue
        chain = (dialog.values.get("DialogChainPrototypeSID") or "").strip()
        if not chain:
            continue
        found = gd.job_menu_switch(chain, accept)
        if found is None:
            continue
        if_sid, menu_target, cancel_target = found
        if not menu_target or cancel_target == menu_target:
            continue
        patches[if_sid] = {"NextDialogOptions": {"False": {"NextDialogSID": menu_target}}}
    return patches


def _quest_taken_patch(gd: GameData, s: Settings) -> dict:
    """Genommene Jobs verschwinden aus dem Menue (Teil 3 des Mehrfach-Job-
    Schalters, 1.36.0) - NEUE Knoten, eigene Datei.

    Das Menue zeigt je Job eine Option, die per Bridge-Bedingung am
    Ergebnis von `<Q>_Add_C0x` haengt (gemessen 09.09.2026 in
    DialogPrototypes, `VisibleOnFailedCondition = false`). Solange das
    Ergebnis steht, steht der Job im Menue - auch nach der Annahme. Zone
    Contracts loescht es darum je Job drei Sekunden nach der Zusage, und
    dazu das Ergebnis der Zusage selbst: ein Technical-Knoten mit StartDelay
    3.0, gestartet vom Pin des Behaelters (der auf die Zusage-Phrase
    wartet), und dahinter ein BridgeCleanUp mit `Add_C0x` +
    `Technical_GetQuest`. Genau so, Knoten fuer Knoten, auch hier - je
    Behaelter zwei, 69 Behaelter an acht Gebern (GameData.repeatable_job_slots).

    Warum eine EIGENE Datei (`QuestNodePrototypes/<Mod>_Jobs.cfg`, kein
    `{bpatch}`): die zwei Mods, deren neue Quest-Knoten nachweislich laufen
    (RSO, Living Zone), legen sie genau so ab; unsere ersten zwei Entwuerfe
    hatten neue Knoten in die `{bpatch}`-Datei gemischt und taten nichts.

    Fehlerfall, bewusst harmlos: laden diese Knoten nicht, bleibt ein
    genommener Job im Menue stehen - sonst passiert nichts. Und weil
    `_quest_menu_patch` das Menue unabhaengig davon offen haelt, ist genau
    das die Frage, die Molkerrs naechster Test nebenbei beantwortet: werden
    unsere neuen Knoten ueberhaupt geladen?"""
    if not s.repeatable_jobs_multi:
        return {}
    patches: dict = {}
    for giver in gd.repeatable_quest_givers():
        quest_sid = giver.get("quest_sid")
        accept = giver.get("accept")
        if not (quest_sid and accept):
            continue
        for slot in gd.repeatable_job_slots(quest_sid):
            tag = slot["container"].rsplit("_", 1)[-1]        # RSQ01_C01 -> C01
            taken = f"S2T_{quest_sid}_Taken_{tag}"
            clear = f"S2T_{quest_sid}_Clear_{tag}"
            patches[taken] = {
                "__new__": True,
                "SID": taken,
                "NodePrototypeVersion": "1",
                "Repeatable": "true",
                "QuestSID": quest_sid,
                "NodeType": "EQuestNodeType::Technical",
                "Launchers": {"[0]": {"Excluding": "false",
                                      "Connections": {"[0]": {"SID": slot["pin"], "Name": ""}}}},
                "StartDelay": "3.0",
            }
            patches[clear] = {
                "__new__": True,
                "SID": clear,
                "NodePrototypeVersion": "1",
                "Repeatable": "true",
                "QuestSID": quest_sid,
                "NodeType": "EQuestNodeType::BridgeCleanUp",
                "Launchers": {"[0]": {"Excluding": "false",
                                      "Connections": {"[0]": {"SID": taken, "Name": ""}}}},
                "NodesToCleanUpResults": {"[0]": slot["add"], "[1]": accept},
            }
    return patches


def _quest_dialog_patch(gd: GameData, s: Settings) -> dict:
    """Der Auftraggeber bietet den naechsten Job sofort an (Issue #8).

    In Vanilla haengt sein SetDialog-Knoten am FALSE-Ausgang des
    Limit-Knotens: der Job-Dialog wird erst wieder scharf, wenn der Geber
    LEER ist. Auf True umgehaengt fragt er sofort wieder — das ist die
    Haelfte der Anfrage, die "mehrmals ansprechen" heisst.

    Geaendert wird nur der Pin-Name; der Verbindungs-Eintrag geht mit
    seiner SID KOMPLETT raus, und mit ihm der ganze Launcher-Eintrag samt
    seiner uebrigen Verbindungen (Array-Regel wie oben). Der Verbindungs-
    Index ist NICHT bei allen Gebern gleich — er wird live gesucht.

    Ohne diesen Schalter bringt ein hoeheres Limit wenig; dieselbe
    Kombination faehrt die Nexus-Mod "New Game Start" (1211)."""
    if not s.repeatable_jobs_instant:
        return {}
    patches: dict = {}
    for giver in gd.repeatable_quest_givers():
        if giver["pin"] == "True":
            continue
        launcher_key, conn_key = giver["link_path"]
        launcher = giver["dialog_node"].children["Launchers"].children[launcher_key]
        entry = _struct_dict(launcher)
        entry["Connections"][conn_key]["Name"] = "True"
        patches[giver["dialog_key"]] = {"Launchers": {launcher_key: entry}}
    return patches


def _relations_patch(gd: GameData, s: Settings) -> dict:
    """Fraktionsbeziehungen + Reputations-Rollback (RelationPrototypes.cfg).

    Beziehungspaare: nur Schluessel patchen, die es in Vanilla gibt (die
    Schreibrichtung "A<->B" ist je Paar fest; neue Paare anzulegen ist
    ungetestet und bleibt tabu). Diese Baseline gilt fuer NEUE Spielstaende;
    wer bestehende erreichen will, schaltet `relations_runtime` ein
    (`_relations_runtime_patch`) - der Weg, den auch die einzige grosse
    Beziehungs-Mod geht.

    ⚠ **`RelationVersion` wird NICHT mehr angefasst.** Von 1.12.0 bis 1.36.0
    schrieb der Patch bei mindestens einem geaenderten Paar Vanilla+1
    hinein - in der Hoffnung, bestehende Saves bemerkten so die neue
    Baseline. Am 08.09.2026 widerlegt (siehe `GameData.relation_version`),
    am 09.09.2026 auf Entscheidung des Besitzers gestrichen: der Zaehler
    gehoert GSC, ein Bump ohne passenden Delta-Eintrag wirkt nicht und
    koennte den Spielstand ein kuenftiges echtes Update ueberspringen lassen.

    Rollback: skaliert die Basis-Cooldown-Sekunden UND die 19
    fraktionsspezifischen Cooldowns; die Hub-/Lair-Modifier bleiben
    unangetastet (sie multiplizieren die Basis und skalieren so mit)."""
    out: dict = {}

    if s.faction_relations:
        vanilla_pairs = gd.relation_pairs()
        changed: dict[str, str] = {}
        for key, target in sorted(s.faction_relations.items()):
            vanilla = vanilla_pairs.get(key)
            if vanilla is None:
                continue                     # anderes Spiel / alter Preset
            try:
                value = int(round(float(target)))
            except (TypeError, ValueError):
                continue
            # weit weg vom Sonderwert 100000 bleiben; unter -800 ist ohnehin
            # Enemy, ueber 201 Friend (docs: RelationLevelRanges)
            value = max(-2000, min(2000, value))
            if value != vanilla:
                changed[key] = str(value)
        if changed:
            out["Relations"] = changed

    f = s.relation_rollback_factor
    if _neq(f, 1.0) and f > 0:
        base = parse_number(
            gd.resolve(gd.relations, "Default", "ReputationRollbackCooldown"))
        if base > 0:
            out["ReputationRollbackCooldown"] = str(
                max(1, int(round(base * f))))
        cooldowns = {
            fac: str(max(1, int(round(seconds * f))))
            for fac, seconds in sorted(gd.faction_rollback_cooldowns().items())
            if seconds > 0
        }
        if cooldowns:
            out["FactionRollbackCooldowns"] = cooldowns

    # Reaktionsstaerke: alle Reputations-Deltas der 2x8 Tabellen skalieren
    # (vorzeichen-erhaltend, ganzzahlig; Nullen bleiben Null).
    rf = s.relation_reaction_factor
    if _neq(rf, 1.0) and rf > 0:
        for table, idx, entry in gd.relation_reaction_tables():
            cfg: dict = {}
            for key, raw in entry.values.items():
                if key == "Type" or "->" not in key:
                    continue
                value = parse_number(raw)
                new = int(round(value * rf))
                if value and new != int(value):
                    cfg[key] = str(new)
            if cfg:
                out.setdefault(table, {})[idx] = cfg

    # Handels-Schwelle: Vanilla = Disaffection (Index 1)
    level = max(0, min(3, int(round(s.trade_min_level))))
    if level != 1:
        name = ("Enemy", "Disaffection", "Neutral", "Friend")[level]
        vanilla_raw = (gd.resolve(gd.relations, "Default",
                                  "MinRelationLevelToTrade") or "")
        target = f"ERelationLevel::{name}"
        if target != vanilla_raw.strip():
            out["MinRelationLevelToTrade"] = target

    return {"Default": out} if out else {}


# Der Spieler als Ziel eines ChangeRelationships-Knotens. Gemessen am
# 08.09.2026: in QuestNodePrototypes steht diese GUID 1436x als
# `FirstTargetSID` und KEIN einziges Mal als `SecondTargetSID`; die Knoten,
# die sie benutzen, heissen `..._SkifEnemy`, `..._KosoyEnemy` usw. Auch
# RSO (Nexus 2009) adressiert den Spieler ausschliesslich so.
PLAYER_TARGET_GUID = "A" * 32

# Namen unserer Mini-Quest. Bewusst mit S2T-Praefix, damit nichts mit einer
# Vanilla- oder Fremd-Quest kollidiert (test_orphan_sids prueft es).
RELATIONS_QUEST_SID = "S2T_Relations"
RELATIONS_START_SID = "S2T_Relations_Start"


def _relations_runtime_patch(gd: GameData, s: Settings) -> tuple[dict, dict, dict]:
    """Fraktionsbeziehungen auch im LAUFENDEN Spielstand setzen.

    (quest_nodes, quest_prototypes, launch_script)

    **Warum es das gibt.** Die Baseline in RelationPrototypes.cfg liest das
    Spiel nur beim Anlegen eines Spielstands; danach lebt der Wert im Save.
    Seit 1.12.0 schrieb der Fraktions-Tab darum zusaetzlich
    `RelationVersion = Vanilla+1` — in der Hoffnung, dass GSCs eigener
    Versionszaehler bestehende Saves nachziehen laesst. **Am 08.09.2026
    widerlegt** (RSO, Nexus 2009, alle acht Varianten gelesen): niemand
    zaehlt den Wert hoch, RSO liefert sogar `0` aus, waehrend das Spiel auf
    `7` steht. Der Zaehler gehoert GSC, und daneben steht
    `RelationUpdateDeltas` — eine Liste von DELTAS je Version. Ein Bump ohne
    passenden Delta-Eintrag wirkt darum nicht — seit 09.09.2026 wird er
    nicht mehr geschrieben (Besitzer-Entscheidung, nach dem 1.36.0-Release).

    **Was stattdessen wirkt** (RSOs Weg, jede Behauptung gegen vanilla/
    nachgemessen):

    1. `EQuestNodeType::ChangeRelationships` — ein Vanilla-Knotentyp, **1875x**
       im Spiel. Er setzt zur Laufzeit die Beziehung zwischen zwei Zielen.
    2. `GameData/Scripts/OnGameLaunch/` — ein Vanilla-Ordner mit 333 Dateien,
       der bei jedem Spielstart Skriptzeilen ausfuehrt; `XStartQuestNodeBySID`
       benutzt das Spiel dort selbst. Eine zusaetzliche Datei mit eigenem
       SID haengt sich an (207 der vorhandenen Dateien benutzen `[0]` als
       Top-Level-Schluessel, mehrere `[*]` — wir nehmen `[*]`, den
       Anhaenge-Index, damit gar nichts kollidieren kann).

    Daraus wird: eine eigene Mini-Quest, ein Startknoten, je geaendertem
    Paar ein ChangeRelationships-Knoten, und ein Startskript.

    **Absolut statt Delta.** RSO verschiebt Werte (`UseDeltaValue = true`),
    weil es Belohnungen umbaut. Unser Regler nennt einen ZIELwert, also
    `UseDeltaValue = false` + `UsePreset = false`. Das ist keine Erfindung:
    91 Vanilla-Knoten stehen genau so, und ihre Werte sind unsere Skala
    (10x `-800`, dazu `-599`, `801`, `-199`).

    ⚠ **Was gemessen ist und was nicht.** Spieler ↔ Fraktion macht RSO
    genauso (44 Knoten) — das ist im Feld erprobt. Fraktion ↔ Fraktion
    macht RSO NICHT; dass beide Ziele ein Fraktionsname sein duerfen, ist
    aus Vanilla belegt (35 Knoten tragen einen Namen als `FirstTargetSID`,
    darunter Varta, Spark, Monolith, Noon, Neutrals), aber nicht von einer
    laufenden Mod. Steht so im Tooltip und im FAQ.

    ⚠ Nichts davon liegt im Spielstand: Pak raus = das Skript laeuft nicht
    mehr, die Beziehungen bleiben auf dem zuletzt gesetzten Stand."""
    if not (s.relations_runtime and s.faction_relations):
        return {}, {}, {}

    vanilla_pairs = gd.relation_pairs()
    nodes: dict = {}
    n = 0
    for key, target in sorted(s.faction_relations.items()):
        vanilla = vanilla_pairs.get(key)
        if vanilla is None or "<->" not in key:
            continue
        try:
            value = int(round(float(target)))
        except (TypeError, ValueError):
            continue
        value = max(-2000, min(2000, value))
        if value == vanilla:
            continue
        first, second = key.split("<->", 1)
        # Der Spieler wird ueber seine GUID adressiert, nicht ueber den
        # Fraktionsnamen "Player" - so macht es RSO, und so stehen 1436
        # Vanilla-Knoten da. Steht "Player" auf der zweiten Seite, drehen
        # wir das Paar um, damit der Spieler immer das erste Ziel ist.
        if second == "Player":
            first, second = second, first
        if first == "Player":
            first = PLAYER_TARGET_GUID
        n += 1
        sid = f"S2T_Rel_{n:02d}"
        nodes[sid] = {
            "__new__": True,
            "SID": sid,
            "NodePrototypeVersion": "1",
            "QuestSID": RELATIONS_QUEST_SID,
            "NodeType": "EQuestNodeType::ChangeRelationships",
            "Launchers": {"[0]": {
                "Excluding": "false",
                "Connections": {"[0]": {"SID": RELATIONS_START_SID, "Name": ""}}}},
            "FirstTargetSID": first,
            "SecondTargetSID": second,
            "UseDeltaValue": "false",
            "UsePreset": "false",
            "RelationshipValue": str(value),
            "SetFactionRelationshipAsPersonal": "false",
            "ShouldLockPersonalRelationship": "false",
        }

    if not nodes:
        return {}, {}, {}

    # Startknoten. `LaunchOnQuestStart` UND das Startskript - beides wie bei
    # RSO; die Verzoegerung gibt dem Spiel Zeit, den Spielstand zu laden.
    nodes[RELATIONS_START_SID] = {
        "__new__": True,
        "SID": RELATIONS_START_SID,
        "NodePrototypeVersion": "1",
        "QuestSID": RELATIONS_QUEST_SID,
        "NodeType": "EQuestNodeType::Technical",
        "StartDelay": "3.0",
        "LaunchOnQuestStart": "true",
    }

    # Die Quest selbst. Vanilla-Eintraege in QuestPrototypes tragen nur
    # ihren SID (nachgesehen: 1304 Quests, die meisten sind zwei Zeilen).
    quest = {RELATIONS_QUEST_SID: {"__new__": True, "SID": RELATIONS_QUEST_SID}}

    # Das Startskript. `[*]` = anhaengen, damit kein Index kollidiert.
    script = {"[*]": {
        "__new__": True,
        "SID": "S2T_OnGameLaunch_Relations",
        "ScriptsArray": {"[*]": f"XStartQuestNodeBySID {RELATIONS_START_SID}"},
    }}
    return nodes, quest, script


# Begegnungs-Arten (Director): Settings-Feld -> Squad-Token (siehe
# GameData.director_scenario_tokens). Ein Szenario gehoert zur Art, wenn ALLE
# seine Squads dieses Token tragen (BlinddogPack, Blinddog3_5 ...); gemischte
# Paare (Blinddog3_5VsBoar1_2) sieht nur der Mutanten-Anteil-Regler.
# Bloodsucker fehlt bewusst: in den Karten-Gruppen steht das Gewicht auf 0,
# und 0 bleibt 0 (Verhalten, das Vanilla nie nutzt, wird nicht erfunden).
ENCOUNTER_KINDS = {
    "enc_blinddog_factor": "Blinddog",
    "enc_boar_factor": "Boar",
    "enc_flesh_factor": "Flesh",
    "enc_tushkan_factor": "Tushkan",
    "enc_chimera_factor": "Chimera",
    "enc_generic_mutant_factor": "Mutant",
}

DIRECTOR_DELAY_KEYS = ("SpawnDelayMin", "SpawnDelayMax",
                       "PostSpawnDirectorTimeoutMin", "PostSpawnDirectorTimeoutMax")


def _lairs_patch(gd: GameData, s: Settings) -> dict:
    """Lager-Bestand und -Respawn (LairPrototypes.cfg, docs/ALIFE_SPAWN_RESEARCH.md).

    MaxSpawnQuantity je (Lager, Fraktion, Rang) x Faktor - Mutanten- und
    Menschen-Fraktionen getrennt, Guard*-Lager (Basis-Wachen) bleiben
    vanilla. Ganzzahlig, nie unter 1; beim Verkleinern nicht unter
    min(Vanilla, Summe MinQuantityPerArchetype) - Vanilla verletzt diese
    Summe bei Freedom/Newbie selbst, die Luecke wird nur nicht vergroessert.
    Respawn: die drei Timer / Faktor, NUR fuer Bloecke mit dem Standard-
    Tripel (180/480/480); die Story-Lager mit 6/30/30 bleiben unangetastet."""
    mut_on = _neq(s.lair_mutant_factor, 1.0) and s.lair_mutant_factor > 0
    hum_on = _neq(s.lair_human_factor, 1.0) and s.lair_human_factor > 0
    rsp_on = _neq(s.lair_respawn_factor, 1.0) and s.lair_respawn_factor > 0
    # 1.33.0 (neunte Datenrecherche): Startbefuellung und die Gewichte der
    # selteneren Archetypen. Beides drehen "A-Life Extended" (273) und
    # "More Enemies" (438); gemessen: InitialSpawnQuantityPercent 688x 0.5
    # und 100x 1.0, SpawnWeight 2244x 1.0 / 237x 0 / 147x 0.2 / 23x 0.5.
    ini_on = (_neq(s.lair_initial_fill_factor, 1.0)
              and s.lair_initial_fill_factor > 0)
    arch_on = (_neq(s.lair_rare_archetype_factor, 1.0)
               and s.lair_rare_archetype_factor > 0)
    if not (mut_on or hum_on or rsp_on or ini_on or arch_on):
        return {}
    standard = gd.lair_standard_timers()
    patches: dict = {}
    for blk in gd.lair_blocks():
        cfg: dict = {}
        if not blk["guard"]:
            f = (s.lair_mutant_factor if blk["mutant"] else s.lair_human_factor)
            on = mut_on if blk["mutant"] else hum_on
            if on and blk["quantity"] > 0:
                q = blk["quantity"]
                new = max(1, int(round(q * f)))
                if f < 1.0:
                    new = max(new, int(min(q, blk["min_sum"])))
                if new != int(q):
                    cfg["MaxSpawnQuantity"] = str(new)
        if rsp_on and blk["timers"] == standard:
            for key, raw in zip(gd.LAIR_TIMER_KEYS, blk["timers"]):
                value = parse_number(raw)
                if value > 0:
                    cfg[key] = _num(value / s.lair_respawn_factor)
        if ini_on and not blk["guard"]:
            value = parse_number(blk["initial"])
            if value > 0:
                new = min(1.0, value * s.lair_initial_fill_factor)
                if _neq(new, value):
                    cfg["InitialSpawnQuantityPercent"] = _num(new)
        # Archetyp-Gewichte: NUR die selteneren (0 < w < 1.0) werden
        # angehoben - alle gleichmaessig zu skalieren wuerde am Verhaeltnis
        # nichts aendern, und die Nullen sind eine Design-Entscheidung des
        # Spiels (der Archetyp kommt in diesem Lager gar nicht vor).
        arch_cfg: dict = {}
        if arch_on and not blk["guard"]:
            for name, raw in sorted(blk["archetypes"].items()):
                value = parse_number(raw)
                if not (0 < value < 1.0):
                    continue
                new = min(1.0, value * s.lair_rare_archetype_factor)
                if _neq(new, value):
                    arch_cfg[name] = {"SpawnWeight": _num(new)}
        if arch_cfg:
            cfg["SpawnSettingsPerArchetypes"] = arch_cfg
        if cfg:
            (patches.setdefault(blk["lair"], {})
                    .setdefault("Preset", {})
                    .setdefault("PossibleInhabitantFactions", {})
                    .setdefault(blk["faction_key"], {})
                    .setdefault("SpawnSettingsPerPlayerRanks", {})
                    .setdefault(blk["rank"], {})).update(cfg)
    return patches


def _director_patch(gd: GameData, s: Settings) -> dict:
    """Zufallsbegegnungen (ALifeDirectorScenarioPrototypes.cfg).

    Frequenz: SpawnDelay*/PostSpawnDirectorTimeout* aller Gruppen und die
    Default-Werte / Faktor (ganzzahlig, >= 1). Mutanten-Anteil: ScenarioWeight
    der rein-Mutanten-Szenarien (kein Human-Squad) x Faktor, Art-Regler
    obendrauf (ENCOUNTER_KINDS); ganzzahlig, Vanilla 0 bleibt 0, sonst >= 1.
    Rudel-Groesse: MaxCount der Rang-Deckel fuer Typen, die NICHT in
    ProhibitedAgentTypes stehen (live gelesen); Vanilla 0 bleibt 0."""
    d = gd.director_preset()
    if d is None:
        return {}
    freq = s.encounter_frequency_factor
    freq_on = _neq(freq, 1.0) and freq > 0
    share = s.encounter_mutant_factor
    kinds = {token: getattr(s, flag) for flag, token in ENCOUNTER_KINDS.items()}
    weight_on = (_neq(share, 1.0) and share >= 0) or any(
        _neq(v, 1.0) and v >= 0 for v in kinds.values())
    pack = s.encounter_pack_factor
    pack_on = _neq(pack, 1.0) and pack > 0
    # 1.33.0: zwei Einzelwerte desselben Presets, die an keinem Regler
    # hingen. "A-Life Extended" (273) halbiert die Ausbreitungszeit
    # (120 -> 60); FallbackMaxSpawnCount (3) ist der Notnagel, wenn der
    # Director keine passende Gruppe findet.
    exp_on = (_neq(s.lair_expansion_player_factor, 1.0)
              and s.lair_expansion_player_factor > 0)
    fb_on = int(s.fallback_spawn_count) != int(
        parse_number(d.values.get("FallbackMaxSpawnCount")) or 3)
    # 1.35.0: Zustand der Begegnung (lebend/verwundet/tot)
    wounded_on = (_neq(s.encounter_wounded_factor, 1.0)
                  and s.encounter_wounded_factor >= 0)
    dead_on = (_neq(s.encounter_dead_factor, 1.0)
               and s.encounter_dead_factor >= 0)
    if not (freq_on or weight_on or pack_on or exp_on or fb_on
            or wounded_on or dead_on):
        return {}
    preset: dict = {}

    if exp_on:
        value = parse_number(d.values.get("DefaultALifeLairExpansionToPlayerTimeMin"))
        if value > 0:
            new = max(1, int(round(value / s.lair_expansion_player_factor)))
            if new != int(value):
                preset["DefaultALifeLairExpansionToPlayerTimeMin"] = str(new)
    if fb_on:
        value = parse_number(d.values.get("FallbackMaxSpawnCount"))
        target = max(1, int(s.fallback_spawn_count))
        if value > 0 and target != int(value):
            preset["FallbackMaxSpawnCount"] = str(target)

    if freq_on:
        for key in ("DefaultSpawnDelayMin", "DefaultSpawnDelayMax",
                    "DefaultPostSpawnDirectorTimeoutMin",
                    "DefaultPostSpawnDirectorTimeoutMax"):
            value = parse_number(d.values.get(key))
            if value > 0:
                preset[key] = str(max(1, int(round(value / freq))))
    groups = d.children.get("ScenarioGroups")
    tokens = gd.director_scenario_tokens() if weight_on else {}
    for gkey, grp in (groups.children.items() if groups else ()):
        gcfg: dict = {}
        if freq_on:
            for key in DIRECTOR_DELAY_KEYS:
                value = parse_number(grp.values.get(key))
                if value > 0:
                    gcfg[key] = str(max(1, int(round(value / freq))))
        if weight_on:
            sids = grp.children.get("ScenarioSIDs")
            for skey, sc in (sids.children.items() if sids else ()):
                toks = tokens.get(skey)
                if not toks or "Human" in toks:
                    continue                      # Menschen/gemischt: tabu
                w = parse_number(sc.values.get("ScenarioWeight"))
                if w <= 0:
                    continue                      # 0 bleibt 0
                f = share if _neq(share, 1.0) and share >= 0 else 1.0
                for token, kf in kinds.items():
                    if toks == {token} and _neq(kf, 1.0) and kf >= 0:
                        f *= kf
                if not _neq(f, 1.0):
                    continue
                new = int(round(w * f))
                if f > 0:
                    new = max(1, new)
                if new != int(w):
                    gcfg.setdefault("ScenarioSIDs", {}).setdefault(skey, {})[
                        "ScenarioWeight"] = str(new)
        if gcfg:
            preset.setdefault("ScenarioGroups", {})[gkey] = gcfg

    if pack_on:
        banned = gd.director_prohibited()
        for ri, ti, atype, count in gd.director_limits():
            if atype in banned or count <= 0:
                continue
            new = max(1, int(round(count * pack)))
            if new != int(count):
                # kompletter [i]-Eintrag (Array-Eintraege nie halb patchen)
                (preset.setdefault("ALifeScenarioNPCArchetypesLimitsPerPlayerRank", {})
                       .setdefault(ri, {}).setdefault("Restrictions", {})
                       )[ti] = {"AgentType": f"EAgentType::{atype}",
                                "MaxCount": str(new)}

    # 1.35.0: in welchem Zustand eine Begegnung ankommt. Jeder der 95
    # Squad-Eintraege traegt vier Zahlen: AliveMultiplierMin/Max (wie gross
    # der lebende Anteil ist, 72x 0.4/0.8), WoundedMultiplier und
    # DeadMultiplier. Gemessen 08.09.2026 - und die Notiz aus der neunten
    # Recherche war zu duester: **Vanilla HAT Verwundeten-Begegnungen**, es
    # gibt acht eigene Szenarien dafuer (Humans_Wounded_Friendly/_Enemy und
    # ihre Gruppen-Varianten, 0.1 bis 0.2). Sie sind nur selten. Darum
    # skalieren wir, was da ist, statt Verwundete zu erfinden: Nullen
    # bleiben Nullen, der Anteil ist bei 1.0 gedeckelt.
    # Der Eintrag geht KOMPLETT raus (Array-Regel), also mit Archetyp,
    # Feind-Flag, Gruppe und beiden Alive-Werten unveraendert.
    if wounded_on or dead_on:
        scenarios = d.children.get("Scenarios")
        for scen_key, scen in (scenarios.children.items() if scenarios else ()):
            squads = scen.children.get("ScenarioSquads")
            for skey, entry in (squads.children.items() if squads else ()):
                cfg: dict = {}
                for on, key, factor in (
                        (wounded_on, "WoundedMultiplier", s.encounter_wounded_factor),
                        (dead_on, "DeadMultiplier", s.encounter_dead_factor)):
                    if not on:
                        continue
                    raw = entry.values.get(key)
                    if raw is None or parse_number(raw) <= 0:
                        continue          # 0 bleibt 0 - nichts erfinden
                    scaled = _scale_literal(raw, factor, cap=1.0)
                    if scaled is not None and _neq(parse_number(scaled),
                                                   parse_number(raw)):
                        cfg[key] = scaled
                if not cfg:
                    continue
                full = {k: v.strip() for k, v in entry.values.items()}
                full.update(cfg)
                (preset.setdefault("Scenarios", {})
                       .setdefault(scen_key, {})
                       .setdefault("ScenarioSquads", {}))[skey] = full
    return {"ALifeDirectorPreset": preset} if preset else {}


UPGRADE_LOCK_KEYS = {
    # Settings-Flag -> Sperrliste im Upgrade-Prototyp
    "upgrades_take_both": "BlockingUpgradePrototypeSIDs",
    "upgrades_no_blueprint": "RequiredItemPrototypeSIDs",
    "upgrades_no_tiers": "RequiredUpgradePrototypeSIDs",
}


def _upgrades_patch(gd: GameData, s: Settings) -> dict:
    """Techniker-Upgrade-Sperren loesen (UpgradePrototypes.cfg, 1288
    Upgrades). Vorbild: die Nexus-Mods "Take Both Upgrades" (2549) und
    "Unrestricted Upgrades" (+NoTiers, 2545) - beide leeren die jeweilige
    Liste per bpatch mit einem leeren Skalar (`Key =`); `[0] = empty`
    funktioniert laut Autor NICHT (das Spiel sucht dann ein Item namens
    empty). Hier live aus den Spieldaten: jedes Upgrade, dessen Liste in
    Vanilla nicht leer ist (die Mods lassen 4/1/1 davon aus). Was die
    Techniker warten, steht nicht in dieser Datei und bleibt vanilla."""
    patches: dict = {}
    for flag, key in UPGRADE_LOCK_KEYS.items():
        if not getattr(s, flag):
            continue
        for sid in gd.upgrade_sids_with(key):
            patches.setdefault(sid, {})[key] = ""

    # Upgrade-Preis je Upgrade (1.32.0, Nr. 14): `BaseCost` steht an allen
    # 1288 Upgrades (5400-21700). Bewusst KEIN eigener Regler - der
    # vorhandene "Upgrade cost" skalierte bisher nur den Difficulty-
    # Multiplikator; jetzt zieht er die Einzelpreise mit, genau wie in
    # 1.28.0 die NPC-Haendlerwerte in die Preisregler gewandert sind.
    if _neq(s.upgrade_cost_factor, 1.0) and s.upgrade_cost_factor >= 0:
        for sid, node in sorted(gd.upgrades.children.items()):
            if "#" in sid:
                continue
            raw = node.values.get("BaseCost")
            if raw is None or parse_number(raw) <= 0:
                continue
            scaled = _scale_literal(raw, s.upgrade_cost_factor)
            if scaled is not None and scaled != raw.strip():
                patches.setdefault(sid, {})["BaseCost"] = scaled

    # Reparatur-Aufschlag je verbautem Upgrade (1.31.0). `RepairCostModifier`
    # steht in Vanilla bei ALLEN 1288 Upgrades auf 0.2f — der Posten, den
    # die Formel in docs/SPEC.md par. 1.10 als "0.1-Koeffizient ohne cfg-
    # Schluessel" fuehrte. Absolutregler, weil der Wert einheitlich ist;
    # verglichen wird trotzdem je Upgrade gegen den live gelesenen Wert.
    # Gefunden in "Stalker Unlimited" (Nexus 1453).
    for sid, node in sorted(gd.upgrades.children.items()):
        if "#" in sid:
            continue
        raw = node.values.get("RepairCostModifier")
        if raw is None:
            continue
        if not _neq(s.upgrade_repair_surcharge, parse_number(raw)):
            continue
        # Literalform erhalten (Vanilla schreibt "0.2f")
        suffix = "f" if raw.strip().endswith(("f", "F")) else ""
        patches.setdefault(sid, {})["RepairCostModifier"] = (
            _num(s.upgrade_repair_surcharge) + suffix)
    return patches


# ------------------------------------------------------------ 1.26.0

def _obj_flags_patch(gd: GameData, s: Settings) -> dict:
    """ObjPrototypes-Schalter je Prototyp: Mutanten loesen Anomalien aus
    (sdwvit AnomaliesHitAllMutants - Vanilla sind Bloodsucker, Chimaere,
    Controller, Poltergeist, Pseudohund, Riese, Hirsch und Ratten immun)
    und menschliche NPCs pluendern keine Leichen (sdwvit NPCsDontLootCorpses).
    Jeder Struct, der den Wert aufgeloest 'falsch herum' hat, bekommt eine
    eigene Zeile - Erben eingeschlossen, das ist harmlos und deckt Structs
    ab, die den Wert selbst ueberschreiben."""
    patches: dict = {}
    if s.mutants_trigger_anomalies:
        for sid in sorted(gd.mutants()):
            if _bool_literal(gd.resolve(gd.obj, sid, "ShouldTriggerAnomalies")) is False:
                patches.setdefault(sid, {})["ShouldTriggerAnomalies"] = "true"
    if s.npcs_no_corpse_loot:
        for sid in sorted(gd.human_npcs()):
            if _bool_literal(gd.resolve(gd.obj, sid, "CanProcessCorpses")) is True:
                patches.setdefault(sid, {})["CanProcessCorpses"] = "false"
    return patches


def _guard_patch(gd: GameData, s: Settings) -> dict:
    """Basis-Wachen: GuardGun*_NPC (BaseDamage 500) auf den Schaden ihrer
    normalen NPC-Waffe (refkey-Elternteil, z.B. AK 9.5) setzen - zusammen
    mit dem geleerten KillVolumeEffect ist das sdwvit NoInstaGibByGuards."""
    if not s.guards_no_instakill:
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.weaponsettings.children.items()):
        if not sid.startswith("GuardGun") or "#" in sid:
            continue
        own = node.values.get("BaseDamage")
        parent = node.attr_dict().get("refkey")
        if own is None or not parent:
            continue
        normal = parse_number(gd.resolve(gd.weaponsettings, parent, "BaseDamage"))
        if normal > 0 and _neq(normal, parse_number(own)):
            patches[sid] = {"BaseDamage": _num(normal)}
    return patches


def _explosion_patch(gd: GameData, s: Settings) -> dict:
    """ExplosionPrototypes (Granaten, Werfer, Faesser, Gasflaschen):
    Radius/ImpulseRadius/ConcussionRadius x Faktor (sdwvit
    IncreaseGrenadeRadius) und DamageNPC x Faktor - der Spieler-Schaden
    laeuft weiter ueber den Schwierigkeits-Multiplikator."""
    radius_on = _neq(s.explosion_radius_factor, 1.0) and s.explosion_radius_factor > 0
    npc_on = _neq(s.explosion_npc_damage_factor, 1.0) and s.explosion_npc_damage_factor >= 0
    # 1.32.0 (Siebte Datenrecherche Nr. 11/12): Ruestungsschaden,
    # Ruestungsdurchschlag und Schaden an zerstoerbaren Objekten
    armor_on = _neq(s.explosion_armor_damage_factor, 1.0) and s.explosion_armor_damage_factor >= 0
    pierce_on = _neq(s.explosion_armor_pierce_factor, 1.0) and s.explosion_armor_pierce_factor >= 0
    destr_on = _neq(s.explosion_destructible_factor, 1.0) and s.explosion_destructible_factor >= 0
    if not (radius_on or npc_on or armor_on or pierce_on or destr_on):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.explosions.children.items()):
        if sid in ("[0]", "Empty") or "#" in sid:
            continue
        cfg: dict = {}
        if radius_on:
            for key in EXPLOSION_RADIUS_KEYS:
                raw = node.values.get(key)
                if raw is not None and parse_number(raw) > 0:
                    scaled = _scale_literal(raw, s.explosion_radius_factor)
                    if scaled is not None:
                        cfg[key] = scaled
        if npc_on:
            raw = node.values.get("DamageNPC")
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.explosion_npc_damage_factor)
                if scaled is not None:
                    cfg["DamageNPC"] = scaled
        for flag, factor, keys in (
                (armor_on, s.explosion_armor_damage_factor,
                 ("DamageArmorPlayer", "DamageArmorNPC")),
                (pierce_on, s.explosion_armor_pierce_factor,
                 ("ArmorPenetrationPlayer", "ArmorPenetrationNPC")),
                (destr_on, s.explosion_destructible_factor,
                 ("DamageDestructible",))):
            if not flag:
                continue
            for key in keys:
                raw = node.values.get(key)
                # Vanilla-0 bleibt 0 - DamageArmorNPC steht bei sechs der
                # zwoelf Explosionen auf 0., sonst gaebe es Scheinpatches
                if raw is None or parse_number(raw) <= 0:
                    continue
                scaled = _scale_literal(raw, factor)
                if scaled is not None and scaled != raw.strip():
                    cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _phantom_dog_patch(gd: GameData, s: Settings) -> dict:
    """Pseudohund-Trugbilder (AbilityPrototypes PseudoDogSummon_*): Damage
    und Bleeding x Faktor, 0 = harmlos (sdwvit NoPseudoDogCloneDamage)."""
    if not (_neq(s.phantom_dog_damage_factor, 1.0) and s.phantom_dog_damage_factor >= 0):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.abilities.children.items()):
        if not sid.startswith("PseudoDogSummon_") or "#" in sid:
            continue
        cfg: dict = {}
        for key in ("Damage", "Bleeding"):
            raw = node.values.get(key)
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.phantom_dog_damage_factor)
                if scaled is not None:
                    cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _mutant_loot_patch(gd: GameData, s: Settings) -> dict:
    """Trophaeen-Chance je Mutantenart (<Art>LootGenerator, Vanilla 0.1 bis
    1.0) x Faktor, Deckel 1 ('100% Chance Mutant Loot', sdwvit
    AlternativeMutantsAlwaysDropLoot). Die grosse Generator-Datei wird nur
    bei aktivem Regler geparst."""
    if not (_neq(s.mutant_loot_chance_factor, 1.0) and s.mutant_loot_chance_factor >= 0):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.itemgenerators.children.items()):
        if not sid.endswith("LootGenerator") or "#" in sid:
            continue
        gen = node.children.get("ItemGenerator")
        if gen is None:
            continue
        slots: dict = {}
        for slot_key, slot in gen.children.items():
            items = slot.children.get("PossibleItems")
            if items is None:
                continue
            rows: dict = {}
            for item_key, item in items.children.items():
                new = _scale_chance(item.values.get("Chance"), s.mutant_loot_chance_factor)
                if new is not None:
                    rows[item_key] = {"Chance": new}
            if rows:
                slots[slot_key] = {"PossibleItems": rows}
        if slots:
            patches[sid] = {"ItemGenerator": slots}
    return patches


def _corpse_clue_patch(gd: GameData, s: Settings) -> dict:
    """Versteck-Hinweise auf Leichen (CorpseClueStashPrototypes, je Region
    BaseSpawnChance 0.02 / AddSpawnChance 0.01) x Faktor, Deckel 1
    ('More Stash Clues', sdwvit StashClueRework)."""
    if not (_neq(s.stash_clue_factor, 1.0) and s.stash_clue_factor >= 0):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.corpseclues.children.items()):
        if "#" in sid:
            continue
        cfg: dict = {}
        for key in ("BaseSpawnChance", "AddSpawnChance"):
            new = _scale_chance(node.values.get(key), s.stash_clue_factor)
            if new is not None:
                cfg[key] = new
        if cfg:
            patches[sid] = cfg
    return patches


def _marker_patch(gd: GameData, s: Settings) -> dict:
    """PDA-Karte (MarkerPrototypes): Aufdeck-/Erkundungsdistanz der Orte
    (Vanilla meist 100 m / 20 m) x Faktor und Regionsnamen von Anfang an
    (RegionMarker Hidden -> Explored, stalker-world 'alle Ortsnamen')."""
    reveal_on = _neq(s.map_reveal_factor, 1.0) and s.map_reveal_factor > 0
    if not (reveal_on or s.map_all_regions):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.markers.children.items()):
        if sid == "[0]" or "#" in sid:
            continue
        # ~320 der 359 Marker sind index-adressierte Top-Level-Eintraege
        # ([1] ...): die werden wie beim Wetter KOMPLETT (aufgeloest)
        # ausgegeben, weil unklar ist, ob {bpatch} solche Eintraege
        # zusammenfuehrt oder ersetzt (docs/SPEC.md); benannte Marker nur
        # mit den geaenderten Schluesseln.
        indexed = sid.startswith("[")
        values = _resolved_struct(gd.markers, node) if indexed else node.values
        cfg: dict = {}
        if reveal_on:
            for key in ("MarkerRevealDistance", "MarkerExploreDistance"):
                raw = values.get(key)
                if isinstance(raw, str) and parse_number(raw) > 0:
                    scaled = _scale_literal(raw, s.map_reveal_factor)
                    if scaled is not None:
                        cfg[key] = scaled
        if s.map_all_regions:
            kind = str(values.get("MarkType") or "").strip()
            state = str(values.get("InitDiscoverState") or "").strip()
            if kind == "EMarkerType::RegionMarker" and state.endswith("Hidden"):
                cfg["InitDiscoverState"] = "EMarkerState::Explored"
        if not cfg:
            continue
        if indexed:
            full = _resolved_struct(gd.markers, node)
            full.update(cfg)
            patches[sid] = full
        else:
            patches[sid] = cfg
    return patches


def _weird_artifact_patch(gd: GameData, s: Settings) -> dict:
    """Weird-Artefakte (Cost of Hope): EffectsDuration / MaxCharge x Faktor
    (sdwvit NoWeirdArtifactRecharge)."""
    if not (_neq(s.weird_artifact_factor, 1.0) and s.weird_artifact_factor > 0):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.items.children.items()):
        if not sid.startswith("AArtifactWeird") or "#" in sid:
            continue
        cfg: dict = {}
        for key in ("EffectsDuration", "MaxCharge"):
            raw = node.values.get(key)
            if raw is not None and parse_number(raw) > 0:
                scaled = _scale_literal(raw, s.weird_artifact_factor)
                if scaled is not None:
                    cfg[key] = scaled
        if cfg:
            patches[sid] = cfg
    return patches


def _skip_intro_patch(gd: GameData, s: Settings) -> dict:
    """Intro-Video (QuestNode E01_MQ01_PlayVideo): die Startverbindung des
    Knotens leeren, das Spiel laeuft direkt weiter (sdwvit SkipIntroCutscene).
    Parst die 75-MB-Datei nur bei aktivem Schalter."""
    if not s.skip_intro:
        return {}
    node = gd.questnodes.children.get("E01_MQ01_PlayVideo")
    launchers = node.children.get("Launchers") if node is not None else None
    if launchers is None:
        return {}
    out: dict = {}
    for lidx, launcher in launchers.children.items():
        conns = launcher.children.get("Connections")
        if conns is None:
            continue
        rows = {cidx: {"SID": "empty"} for cidx, conn in conns.children.items()
                if not _is_empty_sid(conn.values.get("SID"))}
        if rows:
            out[lidx] = {"Connections": rows}
    return {"E01_MQ01_PlayVideo": {"Launchers": out}} if out else {}


def _buy_limits_patch(gd: GameData, s: Settings) -> dict:
    """Haendler kaufen keine Waffen/Ruestungen: BuyLimitations jedes
    Handelsgenerators um Weapon und Armor ergaenzen (vorhandene Sperren
    bleiben; sdwvit TradersDontBuyWeaponsArmor)."""
    if not s.traders_no_gear_buy:
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.trade.children.items()):
        if sid == "[0]" or "#" in sid:
            continue
        gens = node.children.get("TradeGenerators")
        if gens is None:
            continue
        rows: dict = {}
        for idx, gen in gens.children.items():
            limits = gen.children.get("BuyLimitations")
            existing = ([v.strip() for v in limits.values.values()]
                        if limits is not None else [])
            wanted = list(existing)
            for kind in ("EItemType::Weapon", "EItemType::Armor"):
                if kind not in wanted:
                    wanted.append(kind)
            if wanted == existing:
                continue
            rows[idx] = {"BuyLimitations": {f"[{i}]": kind for i, kind in enumerate(wanted)}}
        if rows:
            patches[sid] = {"TradeGenerators": rows}
    return patches


def _posteffect_patch(gd: GameData, s: Settings) -> dict:
    """Duck-Vignette (PostEffectProcessorPrototypes CrouchEffectProcessor.
    Intensity 0.6) x Faktor, Deckel 1 ('Remove Crouch Vignette'); seit
    1.28.0 auch die 15 Schadens-Bildschirmeffekte (DAMAGE_SCREEN_RE, je
    Intensity 1.0) x Faktor 0..1 - jeder Prozessor einzeln, weil jedes
    Kind Intensity selbst deklariert (docs/CORE_SWEEP_RESEARCH.md par. 3b)."""
    patches: dict = {}
    if _neq(s.crouch_vignette_factor, 1.0) and s.crouch_vignette_factor >= 0:
        node = gd.posteffects.children.get("CrouchEffectProcessor")
        raw = node.values.get("Intensity") if node is not None else None
        value = parse_number(raw)
        if raw is not None and value > 0:
            new = min(1.0, value * s.crouch_vignette_factor)
            if _neq(new, value):
                patches["CrouchEffectProcessor"] = {"Intensity": _num(new)}
    if _neq(s.damage_screen_factor, 1.0) and s.damage_screen_factor >= 0:
        for sid, node in gd.posteffects.children.items():
            if sid == "[0]" or "#" in sid or not DAMAGE_SCREEN_RE.match(sid):
                continue
            raw = node.values.get("Intensity")
            if raw is None:                  # heute deklariert jedes Kind selbst
                raw = gd.resolve(gd.posteffects, sid, "Intensity")
            value = parse_number(raw)
            if raw is None or value <= 0:
                continue
            new = min(1.0, value * s.damage_screen_factor)
            if _neq(new, value):
                patches.setdefault(sid, {})["Intensity"] = _num(new)
    return patches


def _anomaly_patch(gd: GameData, s: Settings) -> dict:
    """Klicker-Anomalie (AnomalyPrototypes ClickerAnomaly.ParticleMaxCount,
    Vanilla 20) x Faktor, mindestens 1; der Blendschaden sitzt in
    _effects_patch (ClickerAnomalyHit)."""
    if not (_neq(s.clicker_factor, 1.0) and s.clicker_factor >= 0):
        return {}
    node = gd.anomalies.children.get("ClickerAnomaly")
    raw = node.values.get("ParticleMaxCount") if node is not None else None
    value = parse_number(raw)
    if raw is None or value <= 0:
        return {}
    new = max(1, int(round(value * s.clicker_factor)))
    if new == int(value):
        return {}
    return {"ClickerAnomaly": {"ParticleMaxCount": str(new)}}


# ------------------------------------------------------------ 1.27.0

def _upgrade_strength_patch(gd: GameData, s: Settings) -> dict:
    """Staerke der Techniker-Upgrades: alle Effekte, die UpgradePrototypes
    referenzieren, nach Effekt-Typ in Familien (UPGRADE_FAMILIES) - je Familie
    ein Regler. Nur die Bonus-Richtung wird skaliert (Malus-Effekte wie
    RecoilNeg20 bleiben), Prozent-Boni deckeln bei -100 bzw. Schutz bei 100."""
    factors = {fam: getattr(s, fam) for fam in UPGRADE_FAMILIES}
    if not any(_neq(f, 1.0) and f >= 0 for f in factors.values()):
        return {}
    by_type: dict[str, tuple[str, str]] = {}
    for fam, types in UPGRADE_FAMILIES.items():
        for typ, direction in types.items():
            by_type[typ] = (fam, direction)
    refs: set[str] = set()
    for node in gd.upgrades.children.values():
        sids = node.children.get("EffectPrototypeSIDs")
        if sids is not None:
            refs.update(v.strip() for v in sids.values.values())
    patches: dict = {}
    for sid in sorted(refs):
        node = gd.effects.children.get(sid)
        if node is None:
            continue
        typ = (node.values.get("Type") or "").replace("EEffectType::", "").strip()
        if typ not in by_type:
            continue
        fam, direction = by_type[typ]
        factor = factors[fam]
        if not (_neq(factor, 1.0) and factor >= 0):      # 0 = Upgrades wirken nicht
            continue
        cfg: dict = {}
        for key in ("ValueMin", "ValueMax"):
            raw = node.values.get(key)
            if raw is None:
                continue
            core = raw.strip()
            suffix = "%" if core.endswith("%") else ("f" if core.endswith(("f", "F")) else "")
            number = core[:-1] if suffix else core
            try:
                value = float(number.rstrip(".") or "0")
            except ValueError:
                continue
            if (direction == "neg" and value >= 0) or (direction == "pos" and value <= 0):
                continue
            new = value * factor
            if suffix == "%":
                if direction == "neg":
                    new = max(-100.0, new)
                elif typ.startswith("Protection"):
                    new = min(100.0, new)
            if not _neq(new, value):
                continue
            cfg[key] = _num(new) + suffix
        if cfg:
            patches[sid] = cfg

    # 1.33.0: Composite-Effekte nachziehen. Ein Composite (31 Stueck, z.B.
    # BattleExoskeleton_Varta_Armor_accuracy "20 %") traegt selbst KEINE
    # Wirkung, sondern nur die Zahl fuers Techniker-Menue und verweist per
    # ApplyExtraEffectPrototypeSIDs auf die echten Effekte
    # (IdleSwayXPos20 + IdleSwayYPos20 + DispersionPos15). Bisher haben wir
    # die Kinder skaliert und die angezeigte Zahl stehen lassen - die
    # Anzeige log dann. Nur wenn ALLE Kinder mit DEMSELBEN Faktor skaliert
    # wurden, ist die Anzeige eindeutig; sonst bleibt sie bewusst vanilla.
    for sid in sorted(refs):
        node = gd.effects.children.get(sid)
        if node is None or sid in patches:
            continue
        if (node.values.get("Type") or "").strip() != "EEffectType::Composite":
            continue
        extra = node.children.get("ApplyExtraEffectPrototypeSIDs")
        if extra is None:
            continue
        kids = [v.strip() for v in extra.values.values() if not _is_empty_sid(v)]
        if not kids:
            continue
        kid_factors = set()
        for kid in kids:
            knode = gd.effects.children.get(kid)
            ktyp = ((knode.values.get("Type") or "").replace("EEffectType::", "").strip()
                    if knode is not None else "")
            fam_dir = by_type.get(ktyp)
            kid_factors.add(factors[fam_dir[0]] if fam_dir else 1.0)
        if len(kid_factors) != 1:
            continue
        factor = kid_factors.pop()
        if not (_neq(factor, 1.0) and factor >= 0):
            continue
        cfg = {}
        for key in ("ValueMin", "ValueMax"):
            raw = node.values.get(key)
            if raw is None:
                continue
            core = raw.strip()
            suffix = "%" if core.endswith("%") else ("f" if core.endswith(("f", "F")) else "")
            number = core[:-1] if suffix else core
            try:
                value = float(number.rstrip(".") or "0")
            except ValueError:
                continue
            if value == 0:                     # 0.f-Platzhalter bleiben
                continue
            new = value * factor
            if not _neq(new, value):
                continue
            cfg[key] = _num(new) + suffix
        if cfg:
            patches[sid] = cfg
    return patches


def _scope_patch(gd: GameData, s: Settings) -> dict:
    """Zielfernrohre (EffectPrototypes): Vergroesserung AimingFOVX2..X8
    (-43..-70 %, Deckel -90) und die Nachteile ScopeAimingTimeNeg* /
    ScopeAimingMovementNeg* (0 = keine)."""
    zoom_on = _neq(s.scope_zoom_factor, 1.0) and s.scope_zoom_factor > 0
    pen_on = _neq(s.scope_penalty_factor, 1.0) and s.scope_penalty_factor >= 0
    if not (zoom_on or pen_on):
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.effects.children.items()):
        if "#" in sid:
            continue
        is_zoom = sid.startswith("AimingFOVX") and sid.endswith("Effect")
        is_pen = sid.startswith(("ScopeAimingTimeNeg", "ScopeAimingMovementNeg"))
        if not ((zoom_on and is_zoom) or (pen_on and is_pen)):
            continue
        factor = s.scope_zoom_factor if is_zoom else s.scope_penalty_factor
        cfg: dict = {}
        for key in ("ValueMin", "ValueMax"):
            raw = node.values.get(key)
            if raw is None or not raw.strip().endswith("%"):
                continue
            try:
                value = float(raw.strip()[:-1])
            except ValueError:
                continue
            new = value * factor
            if is_zoom:
                new = max(-90.0, new)
            if _neq(new, value):
                cfg[key] = _num(new) + "%"
        if cfg:
            patches[sid] = cfg
    return patches


def _scope_override_patch(gd: GameData, s: Settings) -> tuple[dict, dict]:
    """Pro-Fernrohr (1.27.0): fuer jedes Fernrohr mit Override einen abgeleiteten
    Effekt S2T_<Scope>_<Effekt> {refkey=<Effekt>;bpatch} mit Vanilla x Faktor
    anlegen (Zoom-Deckel -90 %) und die komplette EffectPrototypeSIDs-Liste des
    Items mit den ersetzten Eintraegen ausgeben (jedes Scope-Item definiert
    die Liste in Vanilla selbst). Liefert (Effekt-Patches, Item-Patches)."""
    if not s.scope_overrides:
        return {}, {}
    table = gd.scope_effects()
    effects: dict = {}
    items: dict = {}
    for sid, params in sorted(s.scope_overrides.items()):
        if sid not in table or not isinstance(params, dict):
            continue
        zoom_sid, pen_sids = table[sid]
        replacements: dict[str, str] = {}

        def derive(orig: str, factor: float, floor: float | None) -> str | None:
            node = gd.effects.children.get(orig)
            if node is None:
                return None
            cfg: dict = {}
            for key in ("ValueMin", "ValueMax"):
                raw = node.values.get(key)
                if raw is None or not raw.strip().endswith("%"):
                    continue
                try:
                    value = float(raw.strip()[:-1])
                except ValueError:
                    continue
                new = value * factor
                if floor is not None:
                    new = max(floor, new)
                cfg[key] = _num(new) + "%"
            if not cfg:
                return None
            new_sid = f"S2T_{sid}_{orig}"
            effects[new_sid] = {"__attrs__": f"refkey={orig}", **cfg}
            return new_sid

        zoom_f = params.get("zoom")
        if zoom_sid and zoom_f is not None and _neq(zoom_f, 1.0) and zoom_f > 0:
            new = derive(zoom_sid, float(zoom_f), -90.0)
            if new:
                replacements[zoom_sid] = new
        pen_f = params.get("penalty")
        if pen_sids and pen_f is not None and _neq(pen_f, 1.0) and pen_f >= 0:
            for orig in pen_sids:
                new = derive(orig, float(pen_f), None)
                if new:
                    replacements[orig] = new
        if not replacements:
            continue
        entries = gd.scope_effect_list(sid)
        if not entries:
            continue
        items[sid] = {"EffectPrototypeSIDs": {idx: replacements.get(v, v) for idx, v in entries.items()}}
    return effects, items


def _combat_sync_patch(gd: GameData, s: Settings) -> dict:
    """CombatSynchronizationPrototypes: Token-Budgets (MaxScore) je Grad und
    Spielerrang - wie viele Gegner gleichzeitig im Nahkampf angreifen,
    Faehigkeiten einsetzen, Granaten werfen oder Sperrfeuer geben."""
    factors = {fam: getattr(s, fam) for fam in SYNC_GROUPS}
    if not any(_neq(f, 1.0) and f > 0 for f in factors.values()):
        return {}
    by_tag = {tag: fam for fam, tags in SYNC_GROUPS.items() for tag in tags}
    patches: dict = {}
    for sid, node in sorted(gd.combatsync.children.items()):
        if "#" in sid:
            continue
        for rank, rank_node in node.children.items():
            groups = rank_node.children.get("FilterGroups")
            if groups is None:
                continue
            rows: dict = {}
            for idx, group in groups.children.items():
                tags = group.children.get("AllowedTags")
                tag = (tags.values.get("[0]") or "").strip() if tags is not None else ""
                fam = by_tag.get(tag)
                if fam is None:
                    continue
                factor = factors[fam]
                if not (_neq(factor, 1.0) and factor > 0):
                    continue
                raw = group.values.get("MaxScore")
                value = parse_number(raw)
                if raw is None or value <= 0 or value >= 1000:
                    continue
                new = max(1, int(round(value * factor)))
                if new != int(value):
                    rows[idx] = {"MaxScore": f"{new}.f"}
            if rows:
                patches.setdefault(sid, {})[rank] = {"FilterGroups": rows}
    return patches


def _container_patch(gd: GameData, s: Settings) -> dict:
    """ItemContainerPrototypes: RespawnTimeSeconds (Vanilla 0 = nie) auf
    Stunden x 3600 - Behaelter fuellen sich wieder (experimentell)."""
    hours = float(s.container_respawn_hours)
    if hours <= 0:
        return {}
    patches: dict = {}
    for sid, node in sorted(gd.containers.children.items()):
        if sid == "[0]" or "#" in sid:
            continue
        raw = node.values.get("RespawnTimeSeconds")
        if raw is None:
            continue
        seconds = int(round(hours * 3600))
        if seconds != int(parse_number(raw)):
            patches[sid] = {"RespawnTimeSeconds": str(seconds)}
    return patches


def input_ini(s: Settings) -> str | None:
    """Der Inhalt von `Stalker2/Config/UserInput.ini` — oder None (1.35.0).

    **Ein zweiter Auslieferungsweg.** Bisher schreibt das Werkzeug
    ausschliesslich cfg-Dateien unterhalb von GameData; diese INI liegt
    daneben im Spielordner und wird ueber `root_files` an die Pak-Wurzel
    gelegt (der Mount-Punkt der Pak IST der Spielordner). Genau so macht es
    "Fluid Movement and Aiming Overhaul" (Nexus 562) — deren Datei habe ich
    geoeffnet, um das FORMAT zu kennen; die zwei Schluessel sind
    Unreal-Standard (`/Script/Engine.InputSettings`), keine Spielwerte.

    Warum ueberhaupt: Maus-Glaettung und Sicht-Beschleunigung lassen sich im
    Spielmenue nicht abschalten. Beides sind Ein/Aus-Fahnen, darum zwei
    Schalter statt Regler.

    ⚠ Anders als alle anderen Ausgaben ist das eine ganze Datei, kein
    `{bpatch}`: liefert eine andere Mod dieselbe INI, entscheidet die
    Ladereihenfolge, und unser Mod-Scan sieht das nicht (er vergleicht nur
    cfg-Blaetter). Steht so im Tooltip."""
    lines = []
    if s.no_view_acceleration:
        lines.append("bViewAccelerationEnabled=False")
    if s.no_mouse_smoothing:
        lines.append("bEnableMouseSmoothing=False")
    if not lines:
        return None
    return "[/Script/Engine.InputSettings]\n" + "\n".join(lines) + "\n"


def build_patches(gd: GameData, s: Settings) -> dict[str, str]:
    """{Pfad relativ zu GameData/: cfg-Text} fuer alle aktiven Tweaks."""
    n = s.mod_name
    out: dict[str, str] = {}

    extensions: dict[str, dict] = {}
    for module in (world_extensions, loot_extensions, repair_extensions):
        for source, patch in module.build(gd, s).items():
            stem = source.removesuffix(".cfg")
            if source in ("AIGlobals.cfg", "CoreVariables.cfg"):
                target = f"{source}_patch_{n}.cfg"
            else:
                target = f"{stem}/{stem.rsplit('/', 1)[-1]}_patch_{n}.cfg"
            _merge_nested(extensions.setdefault(target, {}), patch)

    def add(path: str, patches: dict):
        _merge_nested(patches, extensions.pop(path, {}))
        # A combined factor of one must leave other mods' values alone.
        # Remove the earlier global patch instead of writing vanilla back.
        def drop(parts):
            parents = []
            node = patches
            for part in parts[:-1]:
                if not isinstance(node.get(part), dict):
                    return
                parents.append((node, part))
                node = node[part]
            node.pop(parts[-1], None)
            for parent, part in reversed(parents):
                if not parent[part]:
                    del parent[part]

        if path == f"CoreVariables.cfg_patch_{n}.cfg":
            for key, factor in (("MutantLootContainerInteractRange", s.mutant_loot_range_factor),
                                ("MutantLootInteractHeightMax", s.mutant_loot_height_factor)):
                if factor != 1 and not _neq(factor * s.interaction_range_factor, 1):
                    drop(("DefaultConfig", key))
        if (path == f"ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_{n}.cfg"
                and s.mutant_loot_overrides and s.loot_amount_factor != 1):
            for species, key, slot, row, _item in loot_extensions._trophy_entries(gd):
                factor = s.mutant_loot_overrides.get(species, {}).get("amount_factor", 1)
                if factor != 1 and not _neq(factor * s.loot_amount_factor, 1):
                    for leaf in ("MinCount", "MaxCount"):
                        drop((key, "ItemGenerator", slot, "PossibleItems", row, leaf))
        if patches:
            out[path] = emit_patch(patches)

    obj_patches = _player_patch(gd, s)
    obj_patches.update(_mutants_patch(gd, s))
    obj_patches.update(_npc_heal_patch(gd, s))
    for sid, cfg in _invisibility_patch(gd, s).items():
        obj_patches.setdefault(sid, {}).update(cfg)
    for sid, cfg in _npc_stagger_patch(gd, s).items():
        obj_patches.setdefault(sid, {}).update(cfg)
    for sid, cfg in _obj_flags_patch(gd, s).items():
        obj_patches.setdefault(sid, {}).update(cfg)
    for sid, cfg in _npc_body_patch(gd, s).items():
        _merge_nested(obj_patches.setdefault(sid, {}), cfg)
    for sid, cfg in _npc_dialog_patch(gd, s).items():          # 1.36.0
        _merge_nested(obj_patches.setdefault(sid, {}), cfg)
    add(f"ObjPrototypes/ObjPrototypes_patch_{n}.cfg", obj_patches)

    ability_patches = _mutant_abilities_patch(gd, s)
    _merge_nested(ability_patches, _phantom_dog_patch(gd, s))
    _merge_nested(ability_patches, _mutant_attack_patch(gd, s))
    add(f"AbilityPrototypes/AbilityPrototypes_patch_{n}.cfg", ability_patches)
    add(f"MeleeWeaponPrototypes/MeleeWeaponPrototypes_patch_{n}.cfg",
        _melee_patch(gd, s))
    add(f"FlashlightPrototypes/FlashlightPrototypes_patch_{n}.cfg",
        _flashlight_patch(gd, s))
    add(f"WeatherSelectionPrototypes/WeatherSelectionPrototypes_patch_{n}.cfg",
        _weather_patch(gd, s))

    add(f"DifficultyPrototypes/DifficultyPrototypes_patch_{n}.cfg",
        _difficulty_patch(gd, s))
    cws_patches = _weapon_settings_patch(gd, s)
    for sid, cfg in _bullet_drop_patch(gd, s).items():
        cws_patches.setdefault(sid, {}).update(cfg)
    cws_patches.update(_npc_weapon_patch(gd, s))
    for sid, cfg in _guard_patch(gd, s).items():
        cws_patches.setdefault(sid, {}).update(cfg)
    # NACH _npc_weapon_patch/_guard_patch mergen: die beiden benutzen
    # dict.update auf Struct-Ebene und wuerden einen fertigen Eintrag
    # sonst ueberschreiben.
    for sid, cfg in _npc_vs_npc_patch(gd, s).items():
        cws_patches.setdefault(sid, {}).update(cfg)
    for sid, cfg in _zombie_spread_patch(gd, s).items():
        cws_patches.setdefault(sid, {}).update(cfg)
    for sid, cfg in _weapon_noise_patch(gd, s).items():
        cws_patches.setdefault(sid, {}).update(cfg)
    add("WeaponData/WeaponAttributesPrototypes/"
        f"WeaponAttributesPrototypes_patch_{n}.cfg", _npc_ai_patch(gd, s))
    add(
        "WeaponData/CharacterWeaponSettingsPrototypes/"
        f"CharacterWeaponSettingsPrototypes_patch_{n}.cfg",
        cws_patches,
    )
    wgs_patches, wgs_dlc = _weapon_general_patch(gd, s)
    add(
        "WeaponData/WeaponGeneralSetupPrototypes/"
        f"WeaponGeneralSetupPrototypes_patch_{n}.cfg",
        wgs_patches,
    )
    # Editions-Waffen: eigene Patch-Dateien im DLCGameData-Zweig
    # ("//" = relativ zu Stalker2/Content/, siehe pakio.pack_mod)
    for edition, ed_patches in sorted(wgs_dlc.items()):
        add(
            f"//GameLite/DLCGameData/{edition}/WeaponData/"
            "WeaponGeneralSetupPrototypes/"
            f"WeaponGeneralSetupPrototypes_patch_{n}.cfg",
            ed_patches,
        )
    add(f"ObjWeightParamsPrototypes/ObjWeightParamsPrototypes_patch_{n}.cfg",
        _weight_params_patch(gd, s))
    add(f"ObjEffectMaxParamsPrototypes/ObjEffectMaxParamsPrototypes_patch_{n}.cfg",
        _effect_max_patch(gd, s))
    effect_patches = _effects_patch(gd, s)
    effect_patches.update(armor_extensions.lead_composites(gd, s))
    _merge_nested(effect_patches, _upgrade_strength_patch(gd, s))
    _merge_nested(effect_patches, _scope_patch(gd, s))
    scope_effects, scope_items = _scope_override_patch(gd, s)
    _merge_nested(effect_patches, scope_effects)
    add(f"EffectPrototypes/EffectPrototypes_patch_{n}.cfg", effect_patches)
    add(f"CombatSynchronizationPrototypes/CombatSynchronizationPrototypes_patch_{n}.cfg",
        _combat_sync_patch(gd, s))
    add(f"EnemyEvaluatorPrototypes/EnemyEvaluatorPrototypes_patch_{n}.cfg",
        _enemy_evaluator_patch(gd, s))
    add(f"CoverEvaluatorPrototypes/CoverEvaluatorPrototypes_patch_{n}.cfg",
        _cover_evaluator_patch(gd, s))
    add(f"ItemContainerPrototypes/ItemContainerPrototypes_patch_{n}.cfg",
        _container_patch(gd, s))
    add(f"ExplosionPrototypes/ExplosionPrototypes_patch_{n}.cfg",
        _explosion_patch(gd, s))
    add(f"PostEffectProcessorPrototypes/PostEffectProcessorPrototypes_patch_{n}.cfg",
        _posteffect_patch(gd, s))
    add(f"CorpseClueStashPrototypes/CorpseClueStashPrototypes_patch_{n}.cfg",
        _corpse_clue_patch(gd, s))
    add(f"MarkerPrototypes/MarkerPrototypes_patch_{n}.cfg", _marker_patch(gd, s))
    add(f"AnomalyPrototypes/AnomalyPrototypes_patch_{n}.cfg", _anomaly_patch(gd, s))
    add(f"FloatProviderPrototypes/FloatProviderPrototypes_patch_{n}.cfg",
        _floatprovider_patch(gd, s))
    add(f"ObjHoldBreathParamsPrototypes/ObjHoldBreathParamsPrototypes_patch_{n}.cfg",
        _holdbreath_patch(gd, s))
    core_patch = _corevars_patch(gd, s)
    add(f"CoreVariables.cfg_patch_{n}.cfg", core_patch)
    # 1.28.0: dieselben Gewichts-/Ausdauer-Werte auch in CoreVariablesCustom
    add(f"CoreVariablesCustom.cfg_patch_{n}.cfg", _corevars_custom_patch(gd, core_patch))
    add(f"SaveLoadVariables.cfg_patch_{n}.cfg", _saveload_patch(gd, s))
    add(f"AutoSaveVariables.cfg_patch_{n}.cfg", _autosave_patch(gd, s))
    add(f"QuickSaveVariables.cfg_patch_{n}.cfg", _quicksave_patch(gd, s))
    add(f"StashPrototypes/StashPrototypes_patch_{n}.cfg", _stash_patch(gd, s))
    # Drei Builder teilen sich die Generator-Datei (Mengen, Waffen-Zustand,
    # Haendler-Bestand) und teils denselben PossibleItems-Eintrag -> mergen
    gen_patches = _loot_patch(gd, s)
    _merge_nested(gen_patches, _loot_condition_patch(gd, s))
    _merge_nested(gen_patches, _gear_quality_patch(gd, s))
    _merge_nested(gen_patches, _trader_stock_patch(gd, s))
    # loot_extensions composes global and species trophy settings.
    add(f"ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_{n}.cfg",
        gen_patches)
    add(f"AIGlobals.cfg_patch_{n}.cfg", _aiglobals_patch(gd, s))
    add(f"AIPrototypes/ThreatPrototypes/ThreatPrototypes_patch_{n}.cfg",
        _threats_patch(gd, s))
    add(f"AimAssistPresetPrototypes/AimAssistPresetPrototypes_patch_{n}.cfg",
        _aimassist_patch(gd, s))
    add(f"ProjectilePrototypes/ProjectilePrototypes_patch_{n}.cfg",
        _projectile_patch(gd, s))
    add(f"ObjSleepParamsPrototypes/ObjSleepParamsPrototypes_patch_{n}.cfg",
        _sleep_patch(gd, s))
    add(f"CameraShakePrototypes/CameraShakePrototypes_patch_{n}.cfg",
        _camerashake_patch(gd, s))
    add(f"ArtifactSpawnerPrototypes/ArtifactSpawnerPrototypes_patch_{n}.cfg",
        _artifact_spawner_patch(gd, s))
    add(f"PassiveDetectorPrototypes/PassiveDetectorPrototypes_patch_{n}.cfg",
        _passive_detector_patch(gd, s))
    add(f"FastTravelPrototypes/FastTravelPrototypes_patch_{n}.cfg",
        _fasttravel_patch(gd, s))
    add(f"BoolProviderPrototypes/BoolProviderPrototypes_patch_{n}.cfg",
        _restock_patch(gd, s))
    add("AIPrototypes/VisionScannerPrototypes/"
        f"VisionScannerPrototypes_patch_{n}.cfg", _vision_patch(gd, s))
    hearing = _hearing_patch(gd, s)
    hearing.update(_mutant_hearing_patch(gd, s))
    add("AIPrototypes/HearingSensorPrototypes/"
        f"HearingSensorPrototypes_patch_{n}.cfg", hearing)
    add("AIPrototypes/FlairSensorPrototypes/"
        f"FlairSensorPrototypes_patch_{n}.cfg", _flair_patch(gd, s))
    items_patches, items_dlc = _items_patch(gd, s)
    _merge_nested(items_patches, _weird_artifact_patch(gd, s))
    _merge_nested(items_patches, _artifact_behaviour_patch(gd, s))
    _merge_nested(items_patches, scope_items)
    add(f"ItemPrototypes/ItemPrototypes_patch_{n}.cfg", items_patches)
    for edition, ed_patches in sorted(items_dlc.items()):
        add(f"//GameLite/DLCGameData/{edition}/ItemPrototypes/"
            f"ItemPrototypes_patch_{n}.cfg", ed_patches)
    trade_patches = _trade_patch(gd, s)
    _merge_nested(trade_patches, _trader_wallet_patch(gd, s))
    _merge_nested(trade_patches, _buy_limits_patch(gd, s))
    add(f"TradePrototypes/TradePrototypes_patch_{n}.cfg", trade_patches)
    npc_proto = _npc_trader_patch(gd, s)
    _merge_nested(npc_proto, _npc_marker_patch(gd, s))   # 1.35.0
    add(f"NPCPrototypes/NPCPrototypes_patch_{n}.cfg", npc_proto)
    add(f"RelationPrototypes/RelationPrototypes_patch_{n}.cfg",
        _relations_patch(gd, s))
    quest_patches = _quest_timer_patch(gd, s)
    quest_patches.update(_skip_intro_patch(gd, s))
    _merge_nested(quest_patches, _quest_limit_patch(gd, s))
    _merge_nested(quest_patches, _quest_dialog_patch(gd, s))
    _merge_nested(quest_patches, _quest_multi_patch(gd, s))
    job_guards, job_journals = {}, {}
    if s.repeatable_jobs_multi:
        from .quest_jobs import build_job_isolation
        isolated, job_guards, job_journals = build_job_isolation(gd)
        _merge_nested(quest_patches, isolated)
    add(f"QuestNodePrototypes/QuestNodePrototypes_patch_{n}.cfg", quest_patches)
    # Mehrfach-Jobs, Teil 2 + 3 (1.36.0): der Menue-Boden in DialogPrototypes
    # ({bpatch}, erste Patchdatei dort) und die Taken/Clear-Knoten in einer
    # EIGENEN Datei ohne {bpatch} - Begruendung in den zwei Buildern.
    add(f"DialogPrototypes/DialogPrototypes_patch_{n}.cfg", _quest_menu_patch(gd, s))
    job_nodes = _quest_taken_patch(gd, s)
    job_nodes.update(job_guards)
    add(f"QuestNodePrototypes/{n}_Jobs.cfg", job_nodes)
    add(f"JournalQuestPrototypes/{n}_Jobs.cfg", job_journals)
    # Beziehungen im laufenden Spielstand (1.36.0): drei Dateien. Die neuen
    # Knoten bekommen bewusst eine EIGENE Datei statt in die {bpatch}-Datei
    # oben zu wandern: die zwei Mods, deren neue Quest-Knoten nachweislich
    # laufen (RSO, Living Zone), legen sie genau so ab - und unser einziger
    # Versuch, neue Knoten in eine gemischte {bpatch}-Datei zu schreiben
    # (der Mehrfach-Job-Schalter), hat im Spiel zweimal nicht gewirkt.
    # Ob die Ablage der Grund war, ist unbewiesen; sie kostet nichts.
    rel_nodes, rel_quest, rel_script = _relations_runtime_patch(gd, s)
    add(f"QuestNodePrototypes/{n}_Relations.cfg", rel_nodes)
    add(f"QuestPrototypes/QuestPrototypes_patch_{n}.cfg", rel_quest)
    add(f"Scripts/OnGameLaunch/OnGameLaunchScripts_patch_{n}.cfg", rel_script)
    add(f"EmissionPrototypes/EmissionPrototypes_patch_{n}.cfg",
        _emission_patch(gd, s))
    add(f"UpgradePrototypes/UpgradePrototypes_patch_{n}.cfg",
        _upgrades_patch(gd, s))
    add(f"LairPrototypes/LairPrototypes_patch_{n}.cfg", _lairs_patch(gd, s))
    add(f"PackOfItemsGroupPrototypes/PackOfItemsGroupPrototypes_patch_{n}.cfg",
        _packofitems_patch(gd, s))
    add(f"NPCNeedsPresetPrototypes/NPCNeedsPresetPrototypes_patch_{n}.cfg", _needs_patch(gd, s))
    add(f"BarbedWirePrototypes/BarbedWirePrototypes_patch_{n}.cfg", _barbedwire_patch(gd, s))
    add(f"DestructibleObjectPrototypes/DestructibleObjectPrototypes_patch_{n}.cfg",
        _destructible_patch(gd, s))
    add(f"PhysicsInteractionPrototypes/PhysicsInteractionPrototypes_patch_{n}.cfg",
        _physics_patch(gd, s))
    add(f"WeatherChainPrototypes/WeatherChainPrototypes_patch_{n}.cfg", _weatherchain_patch(gd, s))
    # SingletonConstants ist unbinarisiert -> Patchdatei direkt in GameData/
    # (gleiche Konvention wie CoreVariables/AIGlobals, docs/SPEC.md par. 0)
    add(f"SingletonConstants.cfg_patch_{n}.cfg", _singleton_patch(gd, s))
    add(f"ALifePrototypes/ALifePolicyPrototypes/ALifePolicyPrototypes_patch_{n}.cfg",
        _alife_policy_patch(gd, s))
    add(f"ALifePrototypes/ALifePopulationManagerFactionPrototypes/"
        f"ALifePopulationManagerFactionPrototypes_patch_{n}.cfg", _alife_faction_patch(gd, s))
    add(f"ALifePrototypes/ALifeDirectorScenarioPrototypes/"
        f"ALifeDirectorScenarioPrototypes_patch_{n}.cfg", _director_patch(gd, s))

    for path in list(extensions):
        add(path, {})

    return out


def summarize(s: Settings) -> list[str]:
    """Kurze englische Zusammenfassung der aktiven Tweaks (fuer GUI/Log)."""
    lines = extension_controls.regional_weather.summarize(s.regional_weather_overrides)
    defaults = Settings()
    for field_name, (_, title, _lo, _hi, _step, _default, divisor, _tip) in extension_controls.SLIDERS.items():
        value = getattr(s, field_name)
        if value != getattr(defaults, field_name):
            if field_name == "stash_extra_chance_pct" and not any((s.stash_extra_artifacts, s.stash_extra_weapons, s.stash_extra_armor, s.stash_extra_attachments)):
                continue
            if field_name in ("npc_armor_drop_min_pct", "npc_armor_drop_max_pct") and s.npc_armor_drop_chance_pct <= 0:
                continue
            lines.append(f"{title}: {value * divisor:g}%")
    for field_name, (_, title, _tip) in extension_controls.CHECKS.items():
        if getattr(s, field_name):
            lines.append(title)
    for field_name, title in (("surface_noise_overrides", "Surface noise"), ("weather_luminance_overrides", "Weather luminance")):
        for key, value in sorted(getattr(s, field_name).items()):
            if value != 1:
                lines.append(f"{title} / {extension_controls.label(key)}: {value * 100:g}%")
    for species, params in sorted(s.mutant_loot_overrides.items()):
        for key, value in sorted(params.items()):
            if value != 1:
                lines.append(f"{species} trophy {key.removesuffix('_factor')}: {value * 100:g}%")

    def f(name, factor, vanilla=1.0):
        if _neq(factor, vanilla):
            lines.append(f"{name} × {factor:g}")

    if _neq(s.max_hp, 100):
        lines.append(f"Max health {s.max_hp:g} (vanilla 100)")
    if _neq(s.hp_regen, 0):
        lines.append(f"Passive health regen {s.hp_regen:g} HP/s")
    if s.improved_vaulting:
        lines.append("Improved vaulting (community preset)")
    f("Max vault height", s.vault_height_factor)
    f("Vault trigger distance", s.vault_distance_factor)
    f("Vault approach angle", s.vault_angle_factor)
    f("Vault min obstacle height", s.vault_min_height_factor)
    f("Vault landing tolerance", s.vault_landing_factor)
    f("Vault-over max thickness", s.vault_over_depth_factor)
    f("Vault-over landing distance", s.vault_over_offset_factor)
    if s.vault_sprint:
        lines.append("Vault while sprinting (experimental)")
    if _neq(s.max_stamina, 100):
        lines.append(f"Max stamina {s.max_stamina:g} (vanilla 100)")
    if _neq(s.stamina_regen, 5):
        lines.append(f"Stamina regen {s.stamina_regen:g}/s (vanilla 5)")
    for field_name, key in STAMINA_ACTIONS:
        factor = getattr(s, field_name)
        if _neq(factor, 1.0):
            lines.append(f"Stamina cost {key} × {factor:g}")
    if _neq(s.fall_damage_pct, 100):
        lines.append(f"Fall damage {s.fall_damage_pct:g} %")
    f("Walk & crouch speed", s.walk_speed_factor)
    f("Run & sprint speed", s.run_speed_factor)
    f("Jump height", s.jump_height_factor)

    if _neq(s.max_carry_weight, VANILLA_MAX_CARRY):
        lines.append(f"Max carry weight {s.max_carry_weight:g} kg (vanilla 80)")
    if _neq(s.penalty_start_weight, VANILLA_PENALTY_START):
        lines.append(f"Overweight penalty starts at {s.penalty_start_weight:g} kg (vanilla 50)")
    if s.no_overweight_penalty:
        lines.append("No overweight penalty (speed/stamina)")
    if _neq(s.item_weight_factor, 1.0):
        # Ohne angehakte Kategorie baut _item_weight_patch nichts -> das auch sagen
        if s.item_weight_categories:
            cats = ", ".join(sorted(CATEGORY_LABELS[c] for c in s.item_weight_categories))
            lines.append(f"Item weight × {s.item_weight_factor:g} ({cats})")
        else:
            lines.append(f"Item weight × {s.item_weight_factor:g} "
                         "(no category ticked - no effect)")
    if s.ignore_equipped_weight:
        lines.append("Equipped items are weightless")

    f("Player damage", s.player_damage_factor)
    f("Headshot damage", s.headshot_factor)
    f("Hit camera shake (aim punch)", s.aim_punch_factor)
    f("Human NPC damage", s.npc_damage_factor)
    f("Human NPC health", s.npc_hp_factor)
    f("NPC accuracy", s.npc_accuracy_factor)
    f("NPC vision range", s.npc_vision_factor)
    f("NPC hearing range", s.npc_hearing_factor)
    f("NPC reaction delay", s.npc_reaction_factor)
    f("NPC grenade usage", s.npc_grenade_factor)
    if s.npc_no_heal:
        lines.append("NPCs don't self-heal")
    f("Max simultaneous A-Life agents", s.max_agents_factor)
    f("A-Life spawn distance", s.spawn_distance_factor)
    f("Lair population: mutants", s.lair_mutant_factor)
    f("Lair population: humans", s.lair_human_factor)
    f("Lair respawn speed", s.lair_respawn_factor)
    f("Random encounters: frequency", s.encounter_frequency_factor)
    f("Random encounters: mutant share", s.encounter_mutant_factor)
    f("Random encounters: pack size", s.encounter_pack_factor)
    f("Encounters: blind dogs", s.enc_blinddog_factor)
    f("Encounters: boars", s.enc_boar_factor)
    f("Encounters: fleshes", s.enc_flesh_factor)
    f("Encounters: tushkans", s.enc_tushkan_factor)
    f("Encounters: chimeras", s.enc_chimera_factor)
    f("Encounters: mixed mutant packs", s.enc_generic_mutant_factor)
    f("Mutant health", s.mutant_hp_factor)
    f("Mutant damage", s.mutant_damage_factor)
    f("Mutant speed", s.mutant_speed_factor)
    f("Mutant hearing range", s.mutant_hearing_factor)
    f("Mutant health regen", s.mutant_regen_factor)
    f("Mutant attack cooldown", s.mutant_attack_cooldown_factor)
    f("Bloodsucker cloaking speed", s.bloodsucker_cloak_factor)
    f("Bloodsucker uncloak from damage", s.bloodsucker_uncloak_factor)
    for species, params in sorted(s.mutant_overrides.items()):
        parts = [f"{p} × {v:g}" for p, v in sorted(params.items()) if _neq(v, 1.0)]
        if parts:
            lines.append(f"Mutant {species}: " + ", ".join(parts))
    f("Explosion damage", s.explosion_damage_factor)
    f("Weapon durability", s.durability_factor)
    f("Armor durability", s.armor_durability_factor)
    f("Weapon jamming", s.jamming_factor)
    for sid, params in sorted(s.armor_overrides.items()):
        for param, factor in sorted(params.items()):
            if _neq(factor, 1.0):
                lines.append(
                    f"Armor {armor_label(sid)}: "
                    f"{ARMOR_PARAM_LABELS.get(param, param).lower()} × {factor:g}")
    lines.extend(armor_extensions.summaries(s.armor_custom, armor_label))
    if s.armor_free_sprint:
        lines.append("Remove armor sprint restrictions (experimental)")
    if s.armor_limp_protection:
        lines.append("Body armor prevents limping (experimental)")
    f("Armor protection: physical (strike)", s.armor_strike_factor)
    f("Armor protection: burn", s.armor_burn_factor)
    f("Armor protection: shock", s.armor_shock_factor)
    f("Armor protection: chemical", s.armor_chemical_factor)
    f("Armor protection: radiation", s.armor_radiation_factor)
    f("Armor protection: PSY", s.armor_psy_factor)
    f("Armor carry-weight bonuses", s.armor_carry_bonus_factor)

    if _neq(s.scope_sway_pct, 100):
        lines.append(f"Scoped aim sway {s.scope_sway_pct:g} %")
    f("Breath-hold drain", s.breath_drain_factor)
    f("Breath recovery", s.breath_regen_factor)
    f("Weapon spread", s.spread_factor)
    f("Weapon recoil", s.recoil_factor)
    f("Recoil reduction from upgrades", s.recoil_upgrade_factor)
    f("Weapon effective range", s.weapon_range_factor)
    f("Weapon bleeding", s.weapon_bleeding_factor)
    f("ADS movement speed", s.ads_speed_factor)
    f("Magazine size", s.magazine_factor)
    f("Melee damage (knife & butt strike)", s.melee_damage_factor)
    f("Melee range (knife & butt strike)", s.melee_range_factor)
    f("Interaction reach (pick up, loot, containers)", s.interaction_range_factor)
    f("Talk distance (NPC dialog)", s.dialog_range_factor)
    f("NPC flashlight brightness & reach", s.npc_flashlight_factor)
    f("NPC flashlight beam width", s.npc_flashlight_cone_factor)
    f("NPC flashlight use in combat", s.npc_flashlight_combat_factor)
    if _neq(s.npc_flashlight_on_hour, 22):
        lines.append(f"NPC flashlights on from {int(s.npc_flashlight_on_hour)}:00")
    if _neq(s.npc_flashlight_off_hour, 5):
        lines.append(f"NPC flashlights off at {int(s.npc_flashlight_off_hour)}:00")
    if _neq(s.manual_save_slots, 31):
        lines.append(f"Manual save slots {int(s.manual_save_slots)}")
    if _neq(s.quick_save_slots, 3):
        lines.append(f"Quick save slots {int(s.quick_save_slots)}")
    if _neq(s.auto_save_slots, 10):
        lines.append(f"Autosave slots {int(s.auto_save_slots)}")
    if _neq(s.autosave_interval_min, 10.0):
        lines.append(f"Autosave every {s.autosave_interval_min:g} min")
    if int(s.artifact_slots_bonus) > 0:
        lines.append(f"Artifact slots +{int(s.artifact_slots_bonus)} on every armor (max 5)")
    f("Shooting camera shake", s.shooting_shake_factor)
    f("ADS zoom", s.ads_zoom_factor)
    f("Ladder climb speed", s.climb_speed_factor)
    if int(s.starting_money) > 0:
        lines.append(f"Starting money {int(s.starting_money)} (new game only)")
    if s.no_aim_assist_mouse:
        lines.append("Aim assist off (mouse)")
    if s.no_aim_assist_gamepad:
        lines.append("Aim assist off (gamepad)")
    for label, value, vanilla in (("Cutscene FOV", s.cutscene_fov, 90.0),
                                  ("Default FOV", s.default_fov, 90.0)):
        if _neq(value, vanilla):
            lines.append(f"{label} {value:g}")
    for label, level in (("Compass", s.hud_compass), ("Crosshair", s.hud_crosshair),
                         ("Dead body markers", s.hud_body_markers),
                         ("Stash markers", s.hud_stash_markers)):
        if int(level) == 1:
            lines.append(f"{label} always shown")
        elif int(level) == 2:
            lines.append(f"{label} always hidden")
    f("Bodies stay", s.corpse_time_factor)
    if _neq(s.corpse_max_count, 10):
        lines.append(f"Max bodies near you {int(s.corpse_max_count)}")
    f("Weather duration", s.weather_duration_factor)
    f("Bullet drop", s.bullet_drop_factor)
    f("Bullet speed", s.bullet_speed_factor)
    if int(s.pistol_slot_level) > 0:
        lines.append("Pistol slot accepts " + {1: "SMGs", 2: "SMGs and shotguns"}.get(
            int(s.pistol_slot_level), "any weapon"))
    f("Mutant physical protection", s.mutant_protection_factor)
    if s.sleep_anytime:
        lines.append("Sleep whenever you like")
    if _neq(s.min_sleep_hours, 7):
        lines.append(f"Minimum sleep {int(s.min_sleep_hours)} h")
    if s.sleep_in_emission:
        lines.append("Sleeping during emissions allowed")
    # 1.26.0
    if s.no_knockdown:
        lines.append("Skif can't be knocked down")
    if s.no_water_slowdown:
        lines.append("No slowdown in water")
    if s.look_straight_down:
        lines.append("Look straight down")
    f("Hands-free zoom", s.handless_zoom_factor)
    f("Crouch vignette", s.crouch_vignette_factor)
    f("Butt-strike weapon wear", s.butt_wear_factor)
    if s.mutants_trigger_anomalies:
        lines.append("All mutants trigger anomalies")
    if s.guards_no_instakill:
        lines.append("Base guards use normal weapon damage (no instant death)")
    f("Explosion radius", s.explosion_radius_factor)
    f("Explosion damage to NPCs", s.explosion_npc_damage_factor)
    f("Pseudodog phantom damage", s.phantom_dog_damage_factor)
    if s.psy_phantoms_only:
        lines.append("Psy fields spawn phantoms instead of real stalkers")
    f("Reload speed", s.reload_speed_factor)
    f("Weapon draw & holster speed", s.equip_speed_factor)
    if int(s.shooting_anim_skip) != 0:
        lines.append(f"Skip {int(s.shooting_anim_skip)} shooting animation(s) per shot (vanilla 0, experimental)")
    f("Jam clearing speed", s.jam_clear_factor)
    f("Mutant trophy drop chance", s.mutant_loot_chance_factor)
    f("Stash clues on bodies", s.stash_clue_factor)
    if s.npcs_no_corpse_loot:
        lines.append("NPCs don't loot bodies")
    f("NPC visibility distance (A-Life grid)", s.alife_vision_factor)
    f("Map location reveal distance", s.map_reveal_factor)
    if s.map_all_regions:
        lines.append("All region names shown on the map")
    if int(s.fast_travel_lock) != 2:
        lines.append("Fast travel when overweight: "
                     + ("allowed" if int(s.fast_travel_lock) == 0 else "partial lock"))
    f("Guide delay", s.guide_delay_factor)
    if s.instant_teleports:
        lines.append("Instant teleports (no fade)")
    f("Protection caps", s.protection_cap_factor)
    f("Weird artifact charge/duration", s.weird_artifact_factor)
    if s.skip_intro:
        lines.append("Intro video skipped")
    if s.traders_no_gear_buy:
        lines.append("Traders don't buy weapons or armor")
    f("Clicker anomaly strength", s.clicker_factor)
    # 1.27.0
    f("Backward/sideways speed", s.back_speed_factor)
    f("Air control", s.air_control_factor)
    f("Limping speed", s.limp_speed_factor)
    if _neq(s.slow_run_threshold_pct, 50.0):
        lines.append(f"Jog below {s.slow_run_threshold_pct:g} % stamina (vanilla 50)")
    if _neq(s.hp_regen_delay, 5.0):
        lines.append(f"Health regen delay {s.hp_regen_delay:g} s (vanilla 5)")
    f("Radiation decay", s.radiation_decay_factor)
    f("Bleeding stops by itself", s.bleeding_stop_factor)
    f("Psy recovery", s.psy_recovery_factor)
    f("Sober-up speed", s.sober_up_factor)
    f("Stealth kill reach", s.stealth_kill_range_factor)
    if _neq(s.wheel_time_pct, 30.0):
        lines.append(f"Quick wheel time speed {s.wheel_time_pct:g} % (vanilla 30)")
    f("Sleep fade time", s.sleep_fade_factor)
    f("Corpse dragging speed", s.corpse_drag_factor)
    f("Dropped items stay", s.item_despawn_factor)
    if int(s.day_start_hour) != 6:
        lines.append(f"Day starts at {int(s.day_start_hour)}:00 (vanilla 6)")
    if int(s.evening_start_hour) != 20:
        lines.append(f"Evening starts at {int(s.evening_start_hour)}:00 (vanilla 20)")
    f("Damage to unaware NPCs", s.calm_damage_factor)
    if _neq(s.last_bullet_multiplier, 2.0):
        lines.append(f"Last-bullet damage multiplier {s.last_bullet_multiplier:g} (vanilla 2)")
    f("Armor vs. bullet difference weight", s.armor_difference_factor)
    if _neq(s.armor_deflect_chance_pct, 93.0):
        lines.append(f"Armor deflection chance {s.armor_deflect_chance_pct:g} % (vanilla 93)")
    f("Deflected-hit damage", s.armor_deflect_damage_factor)
    f("Scope magnification", s.scope_zoom_factor)
    f("Scope handling penalties", s.scope_penalty_factor)
    f("Upgrades: accuracy", s.upg_accuracy_factor)
    f("Upgrades: handling", s.upg_handling_factor)
    f("Upgrades: durability", s.upg_durability_factor)
    f("Upgrades: range & ballistics", s.upg_range_factor)
    f("Upgrades: damage & penetration", s.upg_damage_factor)
    f("Upgrades: weight", s.upg_weight_factor)
    f("Upgrades: breath hold", s.upg_breath_factor)
    f("Upgrades: armor protection", s.upg_armor_protection_factor)
    f("Upgrades: armor stamina regen", s.upg_armor_misc_factor)
    if int(s.weapon_warning_count) != 3:
        lines.append(f"Weapon-out warnings before alert {int(s.weapon_warning_count)} (vanilla 3)")
    f("Time between weapon-out warnings", s.weapon_warning_delay_factor)
    f("Camper detection time", s.camper_time_factor)
    f("Simultaneous melee attackers", s.sync_melee_factor)
    f("Simultaneous special attacks", s.sync_ability_factor)
    f("Simultaneous grenade throwers", s.sync_grenade_factor)
    f("Simultaneous suppressive fire", s.sync_suppress_factor)
    if s.npcs_no_weapon_pickup:
        lines.append("NPCs don't pick up weapons")
    f("Night darkness for NPC eyes", s.darkness_factor)
    f("Bodies alarm NPCs", s.corpse_threat_factor)
    f("Hidden damage mercy", s.damage_mercy_factor)
    f("Psy phantom count", s.psy_phantom_factor)
    if _neq(s.min_resale_pct, 10.0):
        lines.append(f"Minimum resale value {s.min_resale_pct:g} % (vanilla 10)")
    if float(s.container_respawn_hours) > 0:
        lines.append(f"Containers refill after {s.container_respawn_hours:g} h")
    f("Energy drink tolerance", s.energy_tolerance_factor)
    f("NPC hip-fire accuracy", s.npc_hip_accuracy_factor)
    f("Device prices (binoculars, NVG)", s.device_price_factor)
    # 1.28.0 P1
    if s.no_landing_limp:
        lines.append("Never limp after landings")
    else:
        f("Limp threshold after hard landings", s.limp_threshold_factor)
    f("Bleeding per hit", s.bleeding_hit_factor)
    f("Bleeding from non-penetrating hits", s.bleeding_nonpen_factor)
    f("Damage screen effects", s.damage_screen_factor)
    if s.flashlight_dialog_bright:
        lines.append("Flashlight stays bright in dialogue")
    if _neq(s.quicksave_overwrite_min, 5.0):
        lines.append(f"Quicksave overwrite window {s.quicksave_overwrite_min:g} min (vanilla 5)")
    # 1.28.0 P2
    f("Armor grenade resistance", s.grenade_resist_factor)
    if _neq(s.armor_wear_coef, 0.7):
        lines.append(f"Armor wear coefficient {s.armor_wear_coef:g} (vanilla 0.7, experimental)")
    f("Armor vs. anomaly strike weight (experimental)", s.anomaly_armor_difference_factor)
    # 1.28.0 P3
    if int(s.wounded_heal_chance) != 70:
        lines.append(f"Wounded NPCs recover {int(s.wounded_heal_chance)} % of the time (vanilla 70)")
    if int(s.wounded_cooldown_s) != 300:
        lines.append(f"Wounded-state cooldown {int(s.wounded_cooldown_s)} s (vanilla 300)")
    f("Wounded NPC health regen", s.wounded_regen_factor)
    if int(s.wounded_heal_threshold) != 35:
        lines.append(f"Wounded heal threshold {int(s.wounded_heal_threshold)} HP (vanilla 35, experimental)")
    f("NPC focus on the player (experimental)", s.npc_player_focus_factor)
    f("NPC target-switch cooldown", s.npc_retarget_cooldown_factor)
    f("NPC damage memory", s.npc_damage_memory_factor)
    f("NPC cover distance (experimental)", s.cover_distance_factor)
    f("NPC cover search path", s.cover_path_factor)
    # 1.28.0 P4
    f("Mutant sense of smell", s.mutant_smell_factor)
    if s.mutants_no_smell:
        lines.append("Mutants cannot smell you")
    f("Burer weapon fire interval", s.burer_fire_interval_factor)
    if s.mutant_loot_widget:
        lines.append("Mutant harvest opens the loot window (experimental)")
    # 1.28.0 P5
    f("A-Life squad expansion (experimental)", s.squad_expansion_factor)
    f("Lair refill cooldown", s.refill_cooldown_factor)
    f("Lair refill distance", s.refill_distance_factor)
    if int(s.corpse_budget) != 30:
        lines.append(f"Offline corpse budget {int(s.corpse_budget)} per lair radius (vanilla 30)")
    if int(s.faction_battle_chance) != 50:
        lines.append(f"Faction expansion battle chance {int(s.faction_battle_chance)} % (vanilla 50, experimental)")
    f("Faction expansion pace (experimental)", s.faction_expansion_pace_factor)
    f("Corpse distance", s.corpse_distance_factor)
    if int(s.alife_corpse_hardcap) != 1500:
        lines.append(f"A-Life corpse hard cap {int(s.alife_corpse_hardcap)} (vanilla 1500)")
    # 1.28.0 P6
    f("Radiation dose per second", s.radiation_dose_factor)
    f("Radiation screen filter", s.radiation_filter_factor)
    f("Geiger counter volume", s.geiger_volume_factor)
    f("Barbed wire damage", s.barbed_wire_factor)
    f("Explosive containers durability (experimental)", s.explosive_container_factor)
    f("Push and kick force (experimental)", s.push_force_factor)
    f("Weather transition speed (experimental)", s.weather_transition_factor)
    f("Moon brightness (experimental)", s.moon_brightness_factor)
    f("Sun brightness (experimental)", s.sun_brightness_factor)
    f("Stars (experimental)", s.stars_brightness_factor)
    f("Cloud opacity (experimental)", s.cloud_opacity_factor)
    f("Cloud speed (experimental)", s.cloud_speed_factor)
    f("Dusk & dawn length (experimental)", s.dusk_length_factor)
    if _neq(s.music_combat_threshold, 20.0):
        lines.append(f"Combat music threshold {s.music_combat_threshold:g} (vanilla 20)")
    if _neq(s.music_combat_lifetime, 25.0):
        lines.append(f"Combat music lingers {s.music_combat_lifetime:g} s (vanilla 25)")
    f("Camp life", s.camp_life_factor)
    # 1.28.0 P7
    f("Artifact visibility radius", s.artifact_radius_factor)
    if s.artifacts_no_hop:
        lines.append("Artifacts don't hop away")
    f("Artifact keep-away distance (experimental)", s.artifact_keepaway_factor)
    f("Artifact hop pause (experimental)", s.artifact_hop_pause_factor)
    if s.artifact_caches_drop:
        lines.append("Uncommon artifact caches actually drop (experimental)")
    f("Loot re-roll radius on rank-up", s.loot_reroll_radius_factor)
    f("Loot re-roll delay on rank-up", s.loot_reroll_timer_factor)
    # 1.28.0 P8
    if s.repair_cost_reputation:
        lines.append("Reputation does not affect repair prices")
    if int(s.infotopic_refresh_hours) != 24:
        lines.append(f"NPC rumours refresh every {int(s.infotopic_refresh_hours)} h (vanilla 24)")
    if s.scope_overrides:
        n_sc = len(s.scope_overrides)
        lines.append(f"Scope overrides: {n_sc} scope{'s' if n_sc != 1 else ''} tuned")
    f("Ammo damage", s.ammo_damage_factor)
    f("Ammo armor piercing", s.ammo_piercing_factor)
    f("Ammo armor damage", s.ammo_armor_damage_factor)
    f("Ammo cover penetration", s.ammo_cover_factor)
    f("Ammo stack size", s.ammo_stack_factor)
    if _neq(s.upgrade_repair_surcharge, Settings.upgrade_repair_surcharge):
        lines.append(f"Repair surcharge per upgrade {s.upgrade_repair_surcharge:g} "
                     f"(vanilla {Settings.upgrade_repair_surcharge:g})")
    f("Mutant attacks per series", s.mutant_attack_series_factor)
    f("Mutant bleeding buildup", s.mutant_attack_bleed_factor)
    f("Weapon jam chance", s.jam_chance_factor)
    f("Hip-fire stance effect", s.hip_steady_factor)
    f("Movement effect on aim", s.move_steady_factor)
    f("Recoil pattern reset", s.recoil_pattern_factor)
    if s.chamber_round:
        lines.append("Every weapon keeps a round in the chamber")
    f("Ammo in dropped weapons", s.dropped_ammo_factor)
    f("Weapon noise", s.weapon_noise_factor)
    f("Inventory space per item", s.item_grid_factor)
    f("Inventory action speed", s.inventory_action_factor)
    f("NPCs walk into anomalies", s.npc_anomaly_ignore_factor)
    f("Ragdoll force on death", s.ragdoll_force_factor)
    f("NPC retreat distance", s.npc_retreat_radius_factor)
    f("NPC damage before retreating", s.npc_retreat_damage_factor)
    f("Recoil & spread recovery", s.recoil_recovery_factor)
    f("Spread build-up", s.spread_bloom_factor)
    f("Aim & crouch steadiness", s.aim_steady_factor)
    f("Zombie spread penalty", s.zombie_spread_factor)
    f("Explosion armor damage", s.explosion_armor_damage_factor)
    f("Explosion armor penetration", s.explosion_armor_pierce_factor)
    f("Explosion damage to objects", s.explosion_destructible_factor)
    f("Bullet wall penetration", s.bullet_penetration_factor)
    f("Bullet max range", s.bullet_range_factor)
    f("NPC vs NPC damage", s.npc_vs_npc_damage_factor)
    # 1.35.0: kleine Kandidaten
    f("NPC vs player damage", s.npc_vs_player_damage_factor)
    f("NPC vs allies damage", s.npc_vs_friendly_damage_factor)
    f("Bullet penetration depth", s.bullet_penetration_depth_factor)
    f("Look speed, horizontal", s.look_speed_h_factor)
    f("Look speed, vertical", s.look_speed_v_factor)
    f("Camera slowdown from hazards", s.camera_slowdown_factor)
    f("Artifact hop distance (experimental)", s.artifact_hop_distance_factor)
    f("Artifact hops per series (experimental)", s.artifact_hop_count_factor)
    if s.artifacts_no_detector:
        lines.append("Artifacts are visible without a detector")
    if s.traders_on_map:
        lines.append("Traders, technicians, medics and guides on the map")
    f("Random encounters: wounded stalkers", s.encounter_wounded_factor)
    f("Random encounters: dead bodies", s.encounter_dead_factor)
    if s.no_mouse_smoothing:
        lines.append("Mouse smoothing off (UserInput.ini)")
    if s.no_view_acceleration:
        lines.append("View acceleration off (UserInput.ini)")
    if s.stat_bars_follow:
        lines.append("Inventory stat bars follow your changes")
    f("Ammo pack size", s.ammo_pack_factor)
    # 1.33.0 (neunte Datenrecherche)
    f("Anomaly wear on gear", s.anomaly_wear_factor)
    f("Weapon & armor max condition", s.gear_durability_factor)
    f("Damage at extreme range", s.far_damage_factor)
    f("Stamina & bleeding caps", s.effect_cap_other_factor)
    f("Lair starting occupancy", s.lair_initial_fill_factor)
    f("Rare lair archetypes", s.lair_rare_archetype_factor)
    f("Lair expansion toward you", s.lair_expansion_player_factor)
    if int(s.fallback_spawn_count) != 3:
        lines.append(f"Fallback spawn count: {int(s.fallback_spawn_count)}")
    f("Ammo spread", s.ammo_dispersion_factor)
    f("Ammo spread while aiming", s.ammo_aim_dispersion_factor)
    f("Stash item sets", s.stash_sets_factor)
    f("Ammo bleeding", s.ammo_bleeding_factor)
    f("Ammo recoil", s.ammo_recoil_factor)
    f("Ammo trajectory flatness", s.ammo_flatness_factor)
    f("Ammo weapon wear", s.ammo_wear_factor)
    f("Food & medicine stack size", s.consumable_stack_factor)
    # Strenger als die Waffen-Schleife weiter unten: ein Muellschluessel aus
    # einem von Hand bearbeiteten Preset darf hier kein KeyError werfen.
    # Das Praefix "Ammo " haelt A545A davon ab, wie eine Waffen-SID zu wirken.
    for sid, params in sorted(s.ammo_overrides.items()):
        parts = [f"{AMMO_PARAM_LABELS[p].lower()} × {v:g}"
                 for p, v in sorted(params.items())
                 if p in AMMO_PARAM_LABELS and _neq(v, 1.0)]
        if parts:
            lines.append(f"Ammo {ammo_label(sid)}: " + ", ".join(parts))

    for cat, params in sorted(s.weapon_category_factors.items()):
        label = WEAPON_CATEGORY_LABELS.get(cat, cat)
        for param in WEAPON_PARAMS:
            value = params.get(param)
            if value is not None and _neq(value, 1.0):
                lines.append(
                    f"{label}: {WEAPON_PARAM_LABELS[param].lower()} × {value:g}")
    for sid, params in sorted(s.weapon_overrides.items()):
        parts = [f"{WEAPON_PARAM_LABELS[p].lower()} × {v:g}"
                 for p, v in sorted(params.items()) if _neq(v, 1.0)]
        if parts:
            from .names import WEAPON_ALIASES
            lines.append(f"{WEAPON_ALIASES.get(sid, sid)}: "
                         + ", ".join(parts))
    # Kaliberwechsel eigene Zeile: er ist kein Faktor und gehoert nicht in
    # die Aufzaehlung darueber — aber unbedingt in die Zusammenfassung,
    # weil er die Waffe staerker veraendert als jeder Regler.
    for sid, caliber in sorted(s.weapon_calibers.items()):
        from .names import WEAPON_ALIASES
        lines.append(f"{WEAPON_ALIASES.get(sid, sid)}: ammunition "
                     f"-> {caliber_label(caliber)}")

    f("Anomaly damage", s.anomaly_damage_factor)
    f("Anomaly damage: electro", s.anomaly_electro_factor)
    f("Anomaly damage: chemical", s.anomaly_chemical_factor)
    f("Anomaly damage: fire", s.anomaly_fire_factor)
    f("Anomaly damage: gravity", s.anomaly_gravity_factor)
    f("Consumable strength", s.consumable_factor)
    f("Consumable effect duration", s.consumable_duration_factor)
    f("Medkit & bandage healing", s.healing_factor)
    f("Rain & storm frequency", s.rain_factor)
    f("Emission frequency", s.emission_factor)
    f("Emission duration", s.emission_duration_factor)
    f("Day length", s.day_length_factor)
    f("Stash & body loot amount", s.stash_loot_factor)
    f("Stash & body find chance", s.stash_chance_factor)
    f("Stash & body ammo bonus", s.stash_ammo_factor)
    f("Loot amount (NPCs, containers, world)", s.loot_amount_factor)
    if _neq(s.dropped_condition_pct, 37.5):
        lines.append(f"Dropped weapon condition ~{s.dropped_condition_pct:g} % "
                     "(vanilla ~37.5)")
    if s.dropped_condition_exact:
        lines.append("Dropped weapon condition: exact (no random spread)")
    f("NPC gear quality", s.npc_gear_quality_factor)
    f("NPC guaranteed-hit shots", s.npc_free_shots_factor)
    f("NPC burst length", s.npc_burst_factor)
    f("NPC fire pauses", s.npc_fire_pause_factor)
    f("NPC engagement range", s.npc_engage_range_factor)
    f("NPC weapon range", s.npc_weapon_range_factor)
    if not s.npc_no_heal:
        f("NPC health regen", s.npc_regen_factor)
    f("Crouch stealth", s.crouch_stealth_factor)
    f("Movement noise", s.movement_noise_factor)
    f("Bad-weather stealth", s.weather_stealth_factor)
    f("Flashlight gives you away", s.flashlight_stealth_factor)
    f("NPC alertness", s.npc_alertness_factor)
    f("NPC search time", s.npc_search_time_factor)
    f("NPC courage", s.npc_courage_factor)
    f("NPC stagger threshold", s.npc_stagger_factor)
    f("NPC attack cooldown", s.npc_attack_cooldown_factor)
    if int(round(s.npc_weapon_rank_add)) > 0:
        lines.append(f"NPC weapon rank +{int(round(s.npc_weapon_rank_add))}")
    f("Trader stock amount", s.trader_stock_factor)
    f("Trader stock variety (chance per item)", s.trader_variety_factor)
    f("Trader money (finite wallets)", s.trader_money_factor)
    if s.trader_infinite_money:
        lines.append("All traders have unlimited money")
    if s.quest_items_weightless:
        lines.append("Quest items weigh nothing")
    f("Radiation accumulation", s.radiation_factor)
    f("Bleeding intensity", s.bleeding_factor)
    f("Hunger rate", s.hunger_rate_factor)
    f("Sleepiness rate", s.sleepiness_rate_factor)
    f("Artifact effect strength", s.artifact_effect_factor)
    f("Artifact radiation side-effect", s.artifact_radiation_factor)
    f("Artifact spawn chance", s.artifact_spawn_factor)
    f("Artifacts per anomaly field", s.artifact_count_factor)
    f("Artifact respawn speed", s.artifact_respawn_factor)
    f("Rare artifact bias", s.artifact_rarity_factor)
    f("Detector & scanner range", s.detector_range_factor)
    f("Fast travel cost", s.fast_travel_cost_factor)
    f("Trader restock time", s.trader_restock_factor)

    if _neq(s.trader_min_durability_pct, 40):
        lines.append(f"Traders buy gear from {s.trader_min_durability_pct:g} % durability (vanilla 40)")
    f("Trader buy prices (what you get)", s.trader_buy_price_factor)
    f("Trader sell prices (what you pay)", s.trader_sell_price_factor)
    f("Repair cost", s.repair_cost_factor)
    f("Upgrade cost", s.upgrade_cost_factor)
    if s.upgrades_take_both:
        lines.append("Upgrades: mutually exclusive branches can all be installed")
    if s.upgrades_no_blueprint:
        lines.append("Upgrades: no blueprint required")
    if s.upgrades_no_tiers:
        lines.append("Upgrades: no earlier tier required")
    f("Quest money rewards", s.quest_reward_factor)
    f("Repeatable quest cooldown", s.repeatable_quest_factor)
    if s.repeatable_jobs_multi:
        lines.append("Accept several repeatable jobs in one conversation")
    if _neq(s.repeatable_jobs_per_round, Settings.repeatable_jobs_per_round):
        lines.append(f"Repeatable jobs per round {s.repeatable_jobs_per_round:g} "
                     f"(vanilla {Settings.repeatable_jobs_per_round})")
    if s.repeatable_jobs_instant:
        lines.append("Task givers offer the next job right away")
    f("ADS aim-in speed", s.aim_time_factor)
    f("Weapon prices", s.weapon_price_factor)
    f("Armor prices", s.armor_price_factor)
    f("Ammo prices", s.ammo_price_factor)
    f("Artifact prices", s.artifact_price_factor)
    f("Consumable prices", s.consumable_price_factor)

    if s.faction_relations:
        n_rel = len(s.faction_relations)
        lines.append(f"Faction relations: {n_rel} pair"
                     f"{'s' if n_rel != 1 else ''} changed")
    if s.relations_runtime:
        lines.append("Faction relations are also applied to a running save")
    f("Reputation rollback time", s.relation_rollback_factor)
    f("Reputation reaction strength", s.relation_reaction_factor)
    if int(round(s.trade_min_level)) != 1:
        level = max(0, min(3, int(round(s.trade_min_level))))
        lines.append("Trading requires standing: "
                     + ("Enemy", "Disaffection", "Neutral", "Friend")[level]
                     + " (vanilla Disaffection)")
    return lines
