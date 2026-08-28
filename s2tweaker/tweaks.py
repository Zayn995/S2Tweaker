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

MOVEMENT_SPEED_KEYS = [
    "WalkSpeed", "RunSpeed", "CrouchSpeed", "LowCrouchSpeed",
    "JoggingSpeed", "SprintSpeed",
]


@dataclass
class Settings:
    mod_name: str = "S2Tweaker"

    # --- Player ---
    max_hp: float = 100.0                    # Vanilla 100
    hp_regen: float = 0.0                    # HP/s, Vanilla 0
    max_stamina: float = 100.0               # Vanilla 100
    stamina_regen: float = 5.0               # SP/s, Vanilla 5
    fall_damage_pct: float = 100.0           # 100 = Vanilla, 0 = kein Fallschaden
    movement_speed_factor: float = 1.0       # alle Gangarten
    jump_height_factor: float = 1.0          # JumpSpeedCoef

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
    npc_damage_factor: float = 1.0
    npc_hp_factor: float = 1.0
    mutant_hp_factor: float = 1.0
    mutant_damage_factor: float = 1.0
    explosion_damage_factor: float = 1.0
    durability_factor: float = 1.0
    jamming_factor: float = 1.0              # 0 = Waffen klemmen nie

    # --- Waffenhandling ---
    scope_sway_pct: float = 100.0            # 100 = Vanilla, 0 = kein Sway (ZF)
    breath_drain_factor: float = 1.0         # 0 = unbegrenzt Luft anhalten
    breath_regen_factor: float = 1.0
    spread_factor: float = 1.0               # Streuung; 0 = laserpraezise
    recoil_factor: float = 1.0               # Rueckstoss

    # --- Welt & Survival ---
    anomaly_damage_factor: float = 1.0
    radiation_factor: float = 1.0
    bleeding_factor: float = 1.0
    hunger_rate_factor: float = 1.0          # 0 = kein Hunger
    sleepiness_rate_factor: float = 1.0      # 0 = keine Muedigkeit

    # --- Wirtschaft ---
    trader_min_durability_pct: float = 40.0  # Vanilla 40
    trader_buy_price_factor: float = 1.0     # was Haendler DIR zahlen
    trader_sell_price_factor: float = 1.0    # was DU bezahlst
    repair_cost_factor: float = 1.0
    upgrade_cost_factor: float = 1.0
    quest_reward_factor: float = 1.0


def _num(x: float) -> str:
    return fmt_float(round(x, 4))


def _neq(a: float, b: float) -> bool:
    return abs(a - b) > 1e-9


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
    if _neq(s.movement_speed_factor, 1.0):
        for key in MOVEMENT_SPEED_KEYS:
            vanilla = parse_number(gd.resolve(gd.obj, "Player", f"MovementParams.{key}"))
            if vanilla > 0:
                movement[key] = _num(vanilla * s.movement_speed_factor)
    if _neq(s.jump_height_factor, 1.0):
        vanilla = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.JumpSpeedCoef"), 1.0)
        movement["JumpSpeedCoef"] = _num(vanilla * s.jump_height_factor)
    if movement:
        player["MovementParams"] = movement

    if _neq(s.fall_damage_pct, 100):
        # Protection.Fall ist prozentualer Schutz: 100 = kein Fallschaden
        player["Protection"] = {"Fall": _num(100.0 - s.fall_damage_pct)}

    return {"Player": player} if player else {}


def _mutants_patch(gd: GameData, s: Settings) -> dict:
    if not _neq(s.mutant_hp_factor, 1.0):
        return {}
    patches: dict = {}
    for sid, hp in sorted(gd.mutants().items()):
        patches[sid] = {"VitalParams": {"MaxHP": _num(max(1.0, hp * s.mutant_hp_factor))}}
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
    apply("EnvironmentDifficulty", "Armor_Durability", s.durability_factor)
    apply("NPCCombatDifficulty", "Weapon_JammingMultiplier", s.jamming_factor)
    apply("EnvironmentDifficulty", "Anomaly_Damage", s.anomaly_damage_factor)
    apply("EnvironmentDifficulty", "Radiation_AccumulationSpeed", s.radiation_factor)
    apply("EnvironmentDifficulty", "Effect_Bleeding", s.bleeding_factor)
    apply("EconomyDifficulty", "Upgrade_Cost", s.upgrade_cost_factor)
    apply("EconomyDifficulty", "Reward_MainLine_Money", s.quest_reward_factor)
    apply("EconomyDifficulty", "Reward_SideLine_Money", s.quest_reward_factor)
    return patches


def _weapon_settings_patch(gd: GameData, s: Settings) -> dict:
    """*_Player-Waffen-Settings: Abnutzung pro Schuss + Streuung."""
    patches: dict = {}
    if _neq(s.durability_factor, 1.0):
        for sid, wear in sorted(gd.player_weapon_wear().items()):
            patches.setdefault(sid, {})["DurabilityDamagePerShot"] = _num(
                wear / s.durability_factor)
    if _neq(s.spread_factor, 1.0):
        for sid, radius in sorted(gd.player_weapon_dispersion().items()):
            patches.setdefault(sid, {})["DispersionRadius"] = _num(
                radius * s.spread_factor)
    return patches


def _weapon_general_patch(gd: GameData, s: Settings) -> dict:
    """WeaponGeneralSetup: Erstschuss-Streuung + Rueckstoss (verschachtelt)."""
    patches: dict = {}
    if _neq(s.spread_factor, 1.0):
        values = gd.weapon_general_values("DispersionParams.FirstShotDispersionRadius")
        for sid, value in sorted(values.items()):
            patches.setdefault(sid, {}).setdefault("DispersionParams", {})[
                "FirstShotDispersionRadius"] = _num(value * s.spread_factor)
    if _neq(s.recoil_factor, 1.0):
        values = gd.weapon_general_values("RecoilParams.RecoilRadius")
        for sid, value in sorted(values.items()):
            patches.setdefault(sid, {}).setdefault("RecoilParams", {})[
                "RecoilRadius"] = _num(value * s.recoil_factor)
    return patches


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
    if _neq(s.scope_sway_pct, 100):
        # Sway-Reduktion (Zielfernrohr-Effekte): -1.0 = -100 % Sway.
        # ValueProviderSID=Empty macht den Wert konstant (statt x Aim-Alpha).
        value = _num(-(1.0 - s.scope_sway_pct / 100.0))
        for sid in ("ScopeIdleSwayXModifierEffect", "ScopeIdleSwayYModifierEffect"):
            if sid in gd.effects.children:
                patches[sid] = {
                    "ValueMin": value,
                    "ValueMax": value,
                    "ValueProviderSID": "Empty",
                }
    return patches


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


def _items_patch(gd: GameData, s: Settings) -> dict:
    patches: dict = {}
    if _neq(s.item_weight_factor, 1.0) and s.item_weight_categories:
        for sid, (cat, weight) in sorted(gd.item_weights().items()):
            if cat not in s.item_weight_categories:
                continue
            patches[sid] = {"Weight": _num(weight * s.item_weight_factor)}
    if s.ignore_equipped_weight:
        patches["[0]"] = {"IgnoreEquippedWeight": "true"}
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

def build_patches(gd: GameData, s: Settings) -> dict[str, str]:
    """{Pfad relativ zu GameData/: cfg-Text} fuer alle aktiven Tweaks."""
    n = s.mod_name
    out: dict[str, str] = {}

    def add(path: str, patches: dict):
        if patches:
            out[path] = emit_patch(patches)

    obj_patches = _player_patch(gd, s)
    obj_patches.update(_mutants_patch(gd, s))
    add(f"ObjPrototypes/ObjPrototypes_patch_{n}.cfg", obj_patches)

    add(f"DifficultyPrototypes/DifficultyPrototypes_patch_{n}.cfg",
        _difficulty_patch(gd, s))
    add(
        "WeaponData/CharacterWeaponSettingsPrototypes/"
        f"CharacterWeaponSettingsPrototypes_patch_{n}.cfg",
        _weapon_settings_patch(gd, s),
    )
    add(
        "WeaponData/WeaponGeneralSetupPrototypes/"
        f"WeaponGeneralSetupPrototypes_patch_{n}.cfg",
        _weapon_general_patch(gd, s),
    )
    add(f"ObjWeightParamsPrototypes/ObjWeightParamsPrototypes_patch_{n}.cfg",
        _weight_params_patch(gd, s))
    add(f"ObjEffectMaxParamsPrototypes/ObjEffectMaxParamsPrototypes_patch_{n}.cfg",
        _effect_max_patch(gd, s))
    add(f"EffectPrototypes/EffectPrototypes_patch_{n}.cfg", _effects_patch(gd, s))
    add(f"ObjHoldBreathParamsPrototypes/ObjHoldBreathParamsPrototypes_patch_{n}.cfg",
        _holdbreath_patch(gd, s))
    add(f"CoreVariables.cfg_patch_{n}.cfg", _corevars_patch(gd, s))
    add(f"ItemPrototypes/ItemPrototypes_patch_{n}.cfg", _items_patch(gd, s))
    add(f"TradePrototypes/TradePrototypes_patch_{n}.cfg", _trade_patch(gd, s))

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
    f("Movement speed", s.movement_speed_factor)
    f("Jump height", s.jump_height_factor)

    if _neq(s.max_carry_weight, VANILLA_MAX_CARRY):
        lines.append(f"Max carry weight {s.max_carry_weight:g} kg (vanilla 80)")
    if _neq(s.penalty_start_weight, VANILLA_PENALTY_START):
        lines.append(f"Overweight penalty starts at {s.penalty_start_weight:g} kg (vanilla 50)")
    if s.no_overweight_penalty:
        lines.append("No overweight penalty (speed/stamina)")
    if _neq(s.item_weight_factor, 1.0):
        cats = ", ".join(sorted(CATEGORY_LABELS[c] for c in s.item_weight_categories))
        lines.append(f"Item weight × {s.item_weight_factor:g} ({cats})")
    if s.ignore_equipped_weight:
        lines.append("Equipped items are weightless")

    f("Player damage", s.player_damage_factor)
    f("Headshot damage", s.headshot_factor)
    f("Human NPC damage", s.npc_damage_factor)
    f("Human NPC health", s.npc_hp_factor)
    f("Mutant health", s.mutant_hp_factor)
    f("Mutant damage", s.mutant_damage_factor)
    f("Explosion damage", s.explosion_damage_factor)
    f("Weapon & armor durability", s.durability_factor)
    f("Weapon jamming", s.jamming_factor)

    if _neq(s.scope_sway_pct, 100):
        lines.append(f"Scoped aim sway {s.scope_sway_pct:g} %")
    f("Breath-hold drain", s.breath_drain_factor)
    f("Breath recovery", s.breath_regen_factor)
    f("Weapon spread", s.spread_factor)
    f("Weapon recoil", s.recoil_factor)

    f("Anomaly damage", s.anomaly_damage_factor)
    f("Radiation accumulation", s.radiation_factor)
    f("Bleeding intensity", s.bleeding_factor)
    f("Hunger rate", s.hunger_rate_factor)
    f("Sleepiness rate", s.sleepiness_rate_factor)

    if _neq(s.trader_min_durability_pct, 40):
        lines.append(f"Traders buy gear from {s.trader_min_durability_pct:g} % durability (vanilla 40)")
    f("Trader buy prices (what you get)", s.trader_buy_price_factor)
    f("Trader sell prices (what you pay)", s.trader_sell_price_factor)
    f("Repair cost", s.repair_cost_factor)
    f("Upgrade cost", s.upgrade_cost_factor)
    f("Quest money rewards", s.quest_reward_factor)
    return lines
