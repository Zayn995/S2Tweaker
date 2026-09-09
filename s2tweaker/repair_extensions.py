"""Optional Hercules field-repair bonus using native config effects.

No new item assets or runtime code are needed. Existing Hercules effects stay
intact; a single additional Composite routes to the selected equipment slots.
Negative percentage Corrosion is supported by the examined repair mod's cfg
construction, but this standalone feature has not been verified in game.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import TYPE_CHECKING

from .cfgparse import parse_number
from .emit import fmt_float

if TYPE_CHECKING:
    from .gamedata import GameData


REPAIR_ITEM_SID = "Hercules"
# A bound on this opt-in new feature, not a hardcoded original game value.
# Examined native-schema repair effects use percentages from -4% to -25%.
MAX_REPAIR_PERCENT = 25.0
REPAIR_FIELDS = (
    ("field_repair_body_pct", ("Body",)),
    ("field_repair_head_pct", ("Head",)),
    ("field_repair_weapons_pct", ("PrimaryWeapon", "SecondaryWeapon", "Pistol")),
)


def effect_namespace(mod_name: str = "S2Tweaker") -> str:
    """Config-safe, stable namespace, distinct even for equal cleaned names."""
    name = str(mod_name)
    readable = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_")[:24] or "Mod"
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
    return f"S2Tweaker_FieldRepair_{readable}_{digest}"


REPAIR_COMPOSITE_SID = effect_namespace() + "_OnHercules"


def _percent(settings, field: str) -> float:
    try:
        value = float(getattr(settings, field, 0.0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a percentage from 0 to 25") from exc
    if not math.isfinite(value) or not 0.0 <= value <= MAX_REPAIR_PERCENT:
        raise ValueError(f"{field} must be a percentage from 0 to 25")
    return value


def _item_effect_list(gd: GameData):
    for node in gd._resolve_chain(gd.items, REPAIR_ITEM_SID):
        effects = node.children.get("EffectPrototypeSIDs")
        if effects is not None:
            return effects
    return None


def _native_schema(gd: GameData, requested_slots: set[str]) -> tuple[str, str, dict]:
    """Check the installed game's template/slots before adding new effects."""
    effects = gd.effects
    if "[0]" not in effects.children:
        raise ValueError("Hercules field repair: native effect template is missing")
    # Inheriting a ticking/permanent template could apply repair repeatedly.
    for key in ("Duration", "Charges", "DelayMin", "DelayMax"):
        raw = gd.resolve(effects, "[0]", key)
        if raw is None or parse_number(raw, math.nan) != 0:
            raise ValueError(f"Hercules field repair: unexpected effect template {key}")
    if gd.resolve(effects, "[0]", "bIsPermanent") != "false":
        raise ValueError("Hercules field repair: effect template is not instantaneous")

    composite_type = None
    slot_literals = {}
    for sid in effects.children:
        if "#" in sid:
            continue
        typ = gd.resolve(effects, sid, "Type")
        if typ == "EEffectType::Composite":
            composite_type = typ
        if typ != "EEffectType::Corrosion":
            continue
        raw = gd.resolve(effects, sid, "InventoryEquipmentSlot") or ""
        slot = raw.removeprefix("EInventoryEquipmentSlot::")
        if slot in requested_slots and raw.startswith("EInventoryEquipmentSlot::"):
            slot_literals[slot] = raw
    if requested_slots - slot_literals.keys() or composite_type is None:
        raise ValueError("Hercules field repair: native repair slot/effect schema is missing")

    beneficial = gd.resolve(effects, "HerculesWeight", "Positive")
    if beneficial != "EBeneficial::Positive":
        raise ValueError("Hercules field repair: Hercules beneficial effect is missing")
    return composite_type, beneficial, slot_literals


def build(gd: GameData, settings) -> dict[str, dict]:
    """Return partial patches keyed by base cfg filename; default is empty.

    Strength is the requested percentage of the equipped item's durability.
    Runtime percentage interpretation and condition clamping remain untested.
    Each existing list receives a wildcard append instead of a numeric-slot
    replacement. Only the wholly new Composite uses fixed child indices.
    """
    requested = {}
    for field, slots in REPAIR_FIELDS:
        percent = _percent(settings, field)
        if percent:
            requested.update({slot: percent for slot in slots})
    if not requested:
        return {}

    item = gd.items.children.get(REPAIR_ITEM_SID)
    if item is None:
        raise ValueError("Hercules field repair: Hercules is missing from game data")
    for key, expected in (("Type", "EItemType::Consumable"),
                          ("Usable", "true"), ("ConsumeOnUse", "true")):
        if gd.resolve(gd.items, REPAIR_ITEM_SID, key) != expected:
            raise ValueError(f"Hercules field repair: unexpected Hercules {key}")
    effects_list = _item_effect_list(gd)
    if effects_list is None or not effects_list.values:
        raise ValueError("Hercules field repair: Hercules use-effect list is missing")

    composite_type, beneficial, slots = _native_schema(gd, set(requested))
    namespace = effect_namespace(getattr(settings, "mod_name", "S2Tweaker"))
    composite_sid = namespace + "_OnHercules"
    own_sids = {slot: f"{namespace}_{slot}" for slot in requested}
    existing = set(gd.effects.children)
    existing.update(node.values.get("SID", "") for node in gd.effects.children.values())
    if existing.intersection((*own_sids.values(), composite_sid)):
        raise ValueError("Hercules field repair: a generated effect SID already exists")
    if composite_sid in effects_list.values.values():
        raise ValueError("Hercules field repair: Hercules already refers to the repair effect")

    effect_patches = {}
    for slot, percent in requested.items():
        sid = own_sids[slot]
        effect_patches[sid] = {
            "__new__": True,
            "__attrs__": "refkey=[0]",
            "SID": sid,
            "Type": "EEffectType::Corrosion",
            "InventoryEquipmentSlot": slots[slot],
            "Positive": beneficial,
            "ValueMin": f"-{fmt_float(percent)}%",
            "ValueMax": f"-{fmt_float(percent)}%",
        }
    effect_patches[composite_sid] = {
        "__new__": True,
        "__attrs__": "refkey=[0]",
        "SID": composite_sid,
        "Type": composite_type,
        "ApplyExtraEffectPrototypeSIDs": {
            f"[{index}]": sid for index, sid in enumerate(own_sids.values())
        },
    }
    return {
        "EffectPrototypes.cfg": effect_patches,
        "ItemPrototypes.cfg": {
            REPAIR_ITEM_SID: {
                "EffectPrototypeSIDs": {"[*]": composite_sid},
                # A hidden extra effect needs no new localization or icon.
                "ShouldShowEffects": {"[*]": "false"},
            },
        },
    }
