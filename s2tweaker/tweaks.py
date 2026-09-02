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

from .cfgparse import parse_number
from .emit import emit_patch, fmt_float
from .gamedata import GameData

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

# --- Waffen-Drei-Ebenen-System: Einzelwaffe > Kategorie > global ---------
WEAPON_PARAMS = ["damage", "spread", "recoil", "durability", "firerate",
                 "range", "bleeding", "adsspeed", "aimtime"]

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
}

# Die vier Ziel-Zeiten skalieren ZUSAMMEN (rein, seitlich, gelehnt, wieder
# raus) — ein Snappiness-Gefuehl, wie bei den vier Range-Schluesseln.
WEAPON_AIMTIME_KEYS = ("AimingTime", "OffsetAimingTime", "LeanAimingTime",
                       "LeanAimingRestoreTime")

# CWS-Schluessel, die der Range-Faktor gemeinsam skaliert
WEAPON_RANGE_KEYS = ("EffectiveFireDistanceMin", "EffectiveFireDistanceMax",
                     "FireDistanceDropOff", "DistanceDropOffLength")

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
AMMO_PARAMS = ["damage", "piercing", "armordamage", "cover"]

AMMO_PARAM_LABELS = {  # GUI (englisch)
    "damage": "Damage",
    "piercing": "Armor piercing",
    "armordamage": "Armor damage",
    "cover": "Cover penetration",
}

# Regler-Schluessel -> cfg-Schluessel in ItemPrototypes (= AMMO_MOD_KEYS).
# Reihenfolge NICHT aendern: sie bestimmt die Reihenfolge der Zeilen im
# erzeugten Patch und damit die Byte-Gleichheit zu bisherigen Paks.
AMMO_PARAM_KEYS = {
    "damage": "DamageMod",
    "piercing": "ArmorPiercingMod",
    "armordamage": "ArmorDamageMod",
    "cover": "CoverPiercingMod",
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
    weapon_range_factor: float = 1.0         # effektive Reichweite (Kaskade)
    weapon_bleeding_factor: float = 1.0      # Blutungs-Chance/-Staerke (Kaskade)
    ads_speed_factor: float = 1.0            # Bewegungstempo beim Zielen (Kaskade)
    aim_time_factor: float = 1.0             # Ziel-Geschwindigkeit (Kaskade)
    magazine_factor: float = 1.0             # Magazingroesse (Waffe + Magazine)
    melee_damage_factor: float = 1.0         # Messer + Kolbenschlag
    # --- Munition (global ueber alle Munitionstypen) ---
    ammo_damage_factor: float = 1.0
    ammo_piercing_factor: float = 1.0        # verstaerkt die AP-Charakteristik
    ammo_armor_damage_factor: float = 1.0
    ammo_cover_factor: float = 1.0
    # Einzelsorten-Overrides {Ammo-SID: {param: faktor}}; ein Eintrag
    # ERSETZT den globalen Regler fuer diesen Parameter an dieser Sorte
    # (wie bei den Waffen), er multipliziert sich nicht dazu.
    ammo_overrides: dict = field(default_factory=dict)

    # --- Waffen-Kaskade (nur Abweichungen von 1.0 speichern; fehlt ein
    # Wert, faellt er eine Ebene runter: Einzelwaffe > Kategorie > global) ---
    weapon_category_factors: dict = field(default_factory=dict)  # {kat: {param: f}}
    weapon_overrides: dict = field(default_factory=dict)         # {WGS-SID: {param: f}}
    # Einzelruestungs-Overrides: {Item-SID: {strike/burn/...: faktor}}
    armor_overrides: dict = field(default_factory=dict)

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
    consumable_factor: float = 1.0           # Medkits/Verband/Essen usw.
    healing_factor: float = 1.0              # NUR Medizin-Heilung (Nexus-Wunsch)
    rain_factor: float = 1.0                 # Regen-/Sturm-Wettergewichte
    emission_factor: float = 1.0             # Emissions-Haeufigkeit
    emission_duration_factor: float = 1.0    # Emissions-Dauer (Zeitstreckung)
    # --- Loot in Verstecken und auf Leichen (StashPrototypes) ---
    stash_loot_factor: float = 1.0           # Stueckzahlen je Fund
    stash_chance_factor: float = 1.0         # Fundwahrscheinlichkeit
    stash_ammo_factor: float = 1.0           # Munition an gefundenen Waffen
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
    trader_buy_price_factor: float = 1.0     # was Haendler DIR zahlen
    trader_sell_price_factor: float = 1.0    # was DU bezahlst
    repair_cost_factor: float = 1.0
    upgrade_cost_factor: float = 1.0
    quest_reward_factor: float = 1.0
    repeatable_quest_factor: float = 1.0     # Cooldown wiederholbarer Jobs
    # Kategorie-Preise (EconomyDifficulty *_Cost, Vanilla ueberall 1.0)
    weapon_price_factor: float = 1.0
    armor_price_factor: float = 1.0
    ammo_price_factor: float = 1.0
    artifact_price_factor: float = 1.0
    consumable_price_factor: float = 1.0


def _num(x: float) -> str:
    return fmt_float(round(x, 4))


def _neq(a: float, b: float) -> bool:
    return abs(a - b) > 1e-9


def _scale_literal(raw: str, factor: float) -> str | None:
    """GSC-Zahlenliteral vorzeichen- und suffixerhaltend skalieren.

    '20' -> '40', '-0.15' -> '-0.3', '35%' -> '70%', '2.5f' -> '5.0f'.
    None bei nicht-numerischen Werten (die bleiben unangetastet)."""
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
    return _num(value * factor) + suffix


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
    if movement:
        player["MovementParams"] = movement

    if vault:
        player["VaultingParams"] = vault
    if _neq(s.fall_damage_pct, 100):
        # Protection.Fall ist prozentualer Schutz: 100 = kein Fallschaden
        player["Protection"] = {"Fall": _num(100.0 - s.fall_damage_pct)}

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
    if not (loot or chance or ammo):
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
    if not s.npc_no_heal:
        return {}
    return {sid: {"VitalParams": {"RegenHP": "0.0"}}
            for sid in sorted(gd.npcs_with_regen())}


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
    (Faktor > 1 = NPCs treffen besser)."""
    if not _neq(s.npc_accuracy_factor, 1.0) or s.npc_accuracy_factor <= 0:
        return {}
    patches: dict = {}
    for sid in sorted(gd.weaponsettings.children):
        if "_NPC" not in sid or "#" in sid:
            continue
        value = parse_number(gd.resolve(gd.weaponsettings, sid, "DispersionRadius"))
        if value > 0:
            patches[sid] = {
                "DispersionRadius": _num(value / s.npc_accuracy_factor)}
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

    return {"AISettings": settings} if settings else {}


def _camerashake_patch(gd: GameData, s: Settings) -> dict:
    """Aim Punch: Kamera-Wackeln beim Getroffenwerden (Nexus-Wunsch)."""
    if not _neq(s.aim_punch_factor, 1.0):
        return {}
    vanilla = parse_number(
        gd.resolve(gd.camerashake, "ProjectileHitCameraShake", "Scale"), 1.0)
    return {"ProjectileHitCameraShake": {"Scale": _num(vanilla * s.aim_punch_factor)}}


def _artifact_spawner_patch(gd: GameData, s: Settings) -> dict:
    """SpawnChanceBase (Cap 100 %) und Rarity-Verteilung je Spawner/Rang."""
    spawn_on = _neq(s.artifact_spawn_factor, 1.0)
    rarity_on = _neq(s.artifact_rarity_factor, 1.0)
    if not (spawn_on or rarity_on):
        return {}
    patches: dict = {}
    for sid, node in gd.artifactspawners.children.items():
        if sid == "Empty" or "#" in sid:
            continue
        ranks: dict = {}
        for rank, rank_node in node.children.items():
            cfg: dict = {}
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
    """Messer + Kolbenschlag (MeleeWeaponPrototypes)."""
    if not _neq(s.melee_damage_factor, 1.0) or s.melee_damage_factor <= 0:
        return {}
    patches: dict = {}
    for sid in ("Knife", "WeaponButt"):
        value = parse_number(gd.resolve(gd.melee, sid, "Damage"))
        if value > 0:
            patches[sid] = {"Damage": _num(value * s.melee_damage_factor)}
    return patches


def _weather_patch(gd: GameData, s: Settings) -> dict:
    """Regen-/Sturm-Gewichte und Emissions-Haeufigkeit je Auswahl-Prototyp."""
    rain_on = _neq(s.rain_factor, 1.0)
    emission_on = _neq(s.emission_factor, 1.0)
    if not (rain_on or emission_on):
        return {}
    patches: dict = {}
    for sid, node in gd.weatherselection.children.items():
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
        if cfg:
            patches[sid] = cfg
    return patches


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
    apply("NPCCombatDifficulty", "Weapon_JammingMultiplier", s.jamming_factor)
    apply("EnvironmentDifficulty", "Anomaly_Damage", s.anomaly_damage_factor)
    apply("EnvironmentDifficulty", "Radiation_AccumulationSpeed", s.radiation_factor)
    apply("EnvironmentDifficulty", "Effect_Bleeding", s.bleeding_factor)
    apply("EconomyDifficulty", "Upgrade_Cost", s.upgrade_cost_factor)
    apply("EconomyDifficulty", "Reward_MainLine_Money", s.quest_reward_factor)
    apply("EconomyDifficulty", "Reward_SideLine_Money", s.quest_reward_factor)
    apply("EconomyDifficulty", "Weapon_Cost", s.weapon_price_factor)
    apply("EconomyDifficulty", "Armor_Cost", s.armor_price_factor)
    apply("EconomyDifficulty", "Ammo_Cost", s.ammo_price_factor)
    apply("EconomyDifficulty", "Artifact_Cost", s.artifact_price_factor)
    apply("EconomyDifficulty", "Consumable_Cost", s.consumable_price_factor)
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
            if not _neq(factor, 1.0) or factor <= 0:
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
              invert: bool = False):
        values = gd.weapon_general_values(path)
        for sid, value in sorted(values.items()):
            f = _weapon_factor(s, gd.weapon_category(sid), sid, param,
                               global_factor)
            if not _neq(f, 1.0) or f <= 0:
                continue
            emit(patches, sid, path, value / f if invert else value * f)
        dlc_values = gd.dlc_weapon_general_values(path)
        for (ed, sid), value in sorted(dlc_values.items()):
            f = _weapon_factor(s, gd.dlc_weapon_category(ed, sid), sid,
                               param, global_factor)
            if not _neq(f, 1.0) or f <= 0:
                continue
            emit(dlc_patches.setdefault(ed, {}), sid, path,
                 value / f if invert else value * f)
        dlc_defined = {sid for _ed, sid in dlc_values}
        for sid, params in sorted(s.weapon_overrides.items()):
            f = params.get(param)
            if (f is None or sid in values or sid in dlc_defined
                    or not _neq(f, 1.0) or f <= 0):
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

    # Magazingroesse an der WAFFE (Basiswert ohne Magazin-Aufsatz): ganzzahlig
    if _neq(s.magazine_factor, 1.0) and s.magazine_factor > 0:
        for sid, value in sorted(gd.weapon_general_values("MaxAmmo").items()):
            scaled_int = max(1, int(round(value * s.magazine_factor)))
            if scaled_int != int(value):
                patches.setdefault(sid, {})["MaxAmmo"] = str(scaled_int)
        for (ed, sid), value in sorted(
                gd.dlc_weapon_general_values("MaxAmmo").items()):
            scaled_int = max(1, int(round(value * s.magazine_factor)))
            if scaled_int != int(value):
                dlc_patches.setdefault(ed, {}).setdefault(sid, {})[
                    "MaxAmmo"] = str(scaled_int)
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
    if not _neq(s.max_carry_weight, VANILLA_MAX_CARRY):
        return {}
    scale = s.max_carry_weight / VANILLA_MAX_CARRY
    return {
        "DefaultEffectMaxParamsSID": {
            "MaxEffectValues": {
                "[1]": {
                    "EffectSID": "EEffectType::PenaltyLessWeight",
                    "MaxValue": _num(90 * scale),
                },
                "[9]": {
                    "EffectSID": "EEffectType::AdditionalInventoryWeight",
                    "MaxValue": _num(140 * scale),
                },
            }
        }
    }


def _effects_patch(gd: GameData, s: Settings) -> dict:
    patches: dict = {}
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

    # Munitions-Modifikatoren (pro Munitions-Item, aufgeloeste Vanilla-Werte).
    # Kaskade: Einzelsorte > globaler Regler -- der Override ERSETZT den
    # globalen Faktor, er stapelt sich nicht (vgl. _weapon_factor).
    ammo_globals = {
        "damage": s.ammo_damage_factor,
        "piercing": s.ammo_piercing_factor,
        "armordamage": s.ammo_armor_damage_factor,
        "cover": s.ammo_cover_factor,
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
                # Vanilla 0 bleibt 0 -> _neq faengt es ab: kein Scheinpatch,
                # kein Absturz (A545D ArmorPiercingMod ist 0.0).
                if _neq(scaled, vanilla):
                    cfg[key] = _num(scaled)
            if cfg:
                patches.setdefault(sid, {}).update(cfg)

    # Artefakt-Detektor-Items (Echo/Bear/Veles/Gilka): Reichweiten skalieren
    if _neq(s.detector_range_factor, 1.0):
        for sid, radii in sorted(gd.detector_items().items()):
            cfg = {key: _num(value * s.detector_range_factor) + "f"
                   for key, value in radii.items()}
            patches.setdefault(sid, {}).update(cfg)

    # Magazin-Aufsaetze: Magazine.MaxAmmo (81 konkrete Magazine, ganzzahlig)
    if _neq(s.magazine_factor, 1.0) and s.magazine_factor > 0:
        for sid, node in sorted(gd.items.children.items()):
            if "#" in sid or sid.startswith("Template") or sid == "[0]":
                continue
            mag = node.children.get("Magazine")
            if mag is None:
                continue
            value = parse_number(mag.values.get("MaxAmmo"))
            if value <= 0:
                continue
            scaled_int = max(1, int(round(value * s.magazine_factor)))
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
    """RequiredMoney je Reiseziel skalieren (0 = Schnellreise gratis)."""
    if not _neq(s.fast_travel_cost_factor, 1.0):
        return {}
    patches: dict = {}
    for sid, node in gd.fasttravel.children.items():
        if sid == "[0]" or "#" in sid:
            continue
        locations = node.children.get("Locations")
        if locations is None:
            continue
        entries: dict = {}
        for idx, entry in locations.children.items():
            money = parse_number(entry.values.get("RequiredMoney"))
            if money > 0:
                entries[idx] = {"RequiredMoney": _num(
                    money * s.fast_travel_cost_factor)}
        if entries:
            patches[sid] = {"Locations": entries}
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


def _relations_patch(gd: GameData, s: Settings) -> dict:
    """Fraktionsbeziehungen + Reputations-Rollback (RelationPrototypes.cfg).

    Beziehungspaare: nur Schluessel patchen, die es in Vanilla gibt (die
    Schreibrichtung "A<->B" ist je Paar fest; neue Paare anzulegen ist
    ungetestet und bleibt tabu). Sobald mindestens ein Paar abweicht, wird
    zusaetzlich RelationVersion = Vanilla+1 geschrieben — GSCs eigener
    Versionszaehler, ueber den bestehende Saves Beziehungs-Updates
    bemerken (Details/Hypothese: docs/FACTION_RELATIONS_RESEARCH.md).

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
            out["RelationVersion"] = str(gd.relation_version() + 1)

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
    # (vorzeichen-erhaltend, ganzzahlig; Nullen bleiben Null). Wie der
    # Rollback ein Mechanik-Wert -> bewusst KEIN RelationVersion-Bump.
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


def build_patches(gd: GameData, s: Settings) -> dict[str, str]:
    """{Pfad relativ zu GameData/: cfg-Text} fuer alle aktiven Tweaks."""
    n = s.mod_name
    out: dict[str, str] = {}

    def add(path: str, patches: dict):
        if patches:
            out[path] = emit_patch(patches)

    obj_patches = _player_patch(gd, s)
    obj_patches.update(_mutants_patch(gd, s))
    obj_patches.update(_npc_heal_patch(gd, s))
    for sid, cfg in _invisibility_patch(gd, s).items():
        obj_patches.setdefault(sid, {}).update(cfg)
    add(f"ObjPrototypes/ObjPrototypes_patch_{n}.cfg", obj_patches)

    add(f"AbilityPrototypes/AbilityPrototypes_patch_{n}.cfg",
        _mutant_abilities_patch(gd, s))
    add(f"MeleeWeaponPrototypes/MeleeWeaponPrototypes_patch_{n}.cfg",
        _melee_patch(gd, s))
    add(f"WeatherSelectionPrototypes/WeatherSelectionPrototypes_patch_{n}.cfg",
        _weather_patch(gd, s))

    add(f"DifficultyPrototypes/DifficultyPrototypes_patch_{n}.cfg",
        _difficulty_patch(gd, s))
    cws_patches = _weapon_settings_patch(gd, s)
    cws_patches.update(_npc_weapon_patch(gd, s))
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
    add(f"EffectPrototypes/EffectPrototypes_patch_{n}.cfg", _effects_patch(gd, s))
    add(f"FloatProviderPrototypes/FloatProviderPrototypes_patch_{n}.cfg",
        _floatprovider_patch(gd, s))
    add(f"ObjHoldBreathParamsPrototypes/ObjHoldBreathParamsPrototypes_patch_{n}.cfg",
        _holdbreath_patch(gd, s))
    add(f"CoreVariables.cfg_patch_{n}.cfg", _corevars_patch(gd, s))
    add(f"StashPrototypes/StashPrototypes_patch_{n}.cfg", _stash_patch(gd, s))
    # Drei Builder teilen sich die Generator-Datei (Mengen, Waffen-Zustand,
    # Haendler-Bestand) und teils denselben PossibleItems-Eintrag -> mergen
    gen_patches = _loot_patch(gd, s)
    _merge_nested(gen_patches, _loot_condition_patch(gd, s))
    _merge_nested(gen_patches, _gear_quality_patch(gd, s))
    _merge_nested(gen_patches, _trader_stock_patch(gd, s))
    add(f"ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_{n}.cfg",
        gen_patches)
    add(f"AIGlobals.cfg_patch_{n}.cfg", _aiglobals_patch(gd, s))
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
    items_patches, items_dlc = _items_patch(gd, s)
    add(f"ItemPrototypes/ItemPrototypes_patch_{n}.cfg", items_patches)
    for edition, ed_patches in sorted(items_dlc.items()):
        add(f"//GameLite/DLCGameData/{edition}/ItemPrototypes/"
            f"ItemPrototypes_patch_{n}.cfg", ed_patches)
    trade_patches = _trade_patch(gd, s)
    _merge_nested(trade_patches, _trader_wallet_patch(gd, s))
    add(f"TradePrototypes/TradePrototypes_patch_{n}.cfg", trade_patches)
    add(f"RelationPrototypes/RelationPrototypes_patch_{n}.cfg",
        _relations_patch(gd, s))
    add(f"QuestNodePrototypes/QuestNodePrototypes_patch_{n}.cfg",
        _quest_timer_patch(gd, s))
    add(f"EmissionPrototypes/EmissionPrototypes_patch_{n}.cfg",
        _emission_patch(gd, s))

    return out


def summarize(s: Settings) -> list[str]:
    """Kurze englische Zusammenfassung der aktiven Tweaks (fuer GUI/Log)."""
    lines = []

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
    f("Mutant health", s.mutant_hp_factor)
    f("Mutant damage", s.mutant_damage_factor)
    f("Mutant speed", s.mutant_speed_factor)
    f("Mutant hearing range", s.mutant_hearing_factor)
    f("Mutant health regen", s.mutant_regen_factor)
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
    f("Weapon effective range", s.weapon_range_factor)
    f("Weapon bleeding", s.weapon_bleeding_factor)
    f("ADS movement speed", s.ads_speed_factor)
    f("Magazine size", s.magazine_factor)
    f("Melee damage (knife & butt strike)", s.melee_damage_factor)
    f("Ammo damage", s.ammo_damage_factor)
    f("Ammo armor piercing", s.ammo_piercing_factor)
    f("Ammo armor damage", s.ammo_armor_damage_factor)
    f("Ammo cover penetration", s.ammo_cover_factor)
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

    f("Anomaly damage", s.anomaly_damage_factor)
    f("Anomaly damage: electro", s.anomaly_electro_factor)
    f("Anomaly damage: chemical", s.anomaly_chemical_factor)
    f("Anomaly damage: fire", s.anomaly_fire_factor)
    f("Anomaly damage: gravity", s.anomaly_gravity_factor)
    f("Consumable strength", s.consumable_factor)
    f("Medkit & bandage healing", s.healing_factor)
    f("Rain & storm frequency", s.rain_factor)
    f("Emission frequency", s.emission_factor)
    f("Emission duration", s.emission_duration_factor)
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
    f("Trader stock amount", s.trader_stock_factor)
    f("Trader stock variety (chance per item)", s.trader_variety_factor)
    f("Trader money (finite wallets)", s.trader_money_factor)
    if s.trader_infinite_money:
        lines.append("All traders have unlimited money")
    f("Radiation accumulation", s.radiation_factor)
    f("Bleeding intensity", s.bleeding_factor)
    f("Hunger rate", s.hunger_rate_factor)
    f("Sleepiness rate", s.sleepiness_rate_factor)
    f("Artifact effect strength", s.artifact_effect_factor)
    f("Artifact radiation side-effect", s.artifact_radiation_factor)
    f("Artifact spawn chance", s.artifact_spawn_factor)
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
    f("Quest money rewards", s.quest_reward_factor)
    f("Repeatable quest cooldown", s.repeatable_quest_factor)
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
    f("Reputation rollback time", s.relation_rollback_factor)
    f("Reputation reaction strength", s.relation_reaction_factor)
    if int(round(s.trade_min_level)) != 1:
        level = max(0, min(3, int(round(s.trade_min_level))))
        lines.append("Trading requires standing: "
                     + ("Enemy", "Disaffection", "Neutral", "Friend")[level]
                     + " (vanilla Disaffection)")
    return lines
