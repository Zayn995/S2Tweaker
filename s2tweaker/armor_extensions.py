"""Optional per-outfit settings, resolved from the installed game data.

Absent values (-1 in the editor) inherit existing controls. Explicit values
replace only the corresponding item field; difficulty and upgrades still apply.
"""
from dataclasses import dataclass
import math
import hashlib

from .cfgparse import parse_number


@dataclass(frozen=True)
class Control:
    label: str
    path: str
    maximum: float
    step: float = 1
    body_only: bool = False
    experimental: bool = False
    help: str = ""


CONTROLS = {
    "weight": Control("Weight (kg)", "Weight", 100, 0.1),
    "cost": Control("Base price (coupons)", "Cost", 500000, 100,
                    help="Trader and difficulty price multipliers still apply."),
    "durability": Control("Maximum durability", "BaseDurability", 20000, 10,
                          help="Existing items store condition in the save. Intended for newly spawned gear."),
    "grid_width": Control("Inventory width (cells)", "ItemGridWidth", 12),
    "grid_height": Control("Inventory height (cells)", "ItemGridHeight", 12),
    "artifact_slots": Control("Base artifact slots", "ArtifactSlots", 5, body_only=True,
                              help="Sets the base count, before technician upgrades; at most five slots."),
    "strike": Control("Physical protection (absolute)", "Protection.Strike", 10, 0.05),
    "burn": Control("Fire protection (absolute)", "Protection.Burn", 100, 0.5),
    "shock": Control("Electric protection (absolute)", "Protection.Shock", 100, 0.5),
    "chemical": Control("Chemical protection (absolute)", "Protection.ChemicalBurn", 100, 0.5),
    "radiation": Control("Radiation protection (absolute)", "Protection.Radiation", 100, 0.5),
    "psy": Control("PSY protection (absolute)", "Protection.PSY", 100, 0.5),
    "fall": Control("Fall protection (absolute)", "Protection.Fall", 100, 1,
                    experimental=True, help="Adds armor-specific fall protection. Gameplay effect is not verified."),
    "noise": Control("Armor noise coefficient", "NoiseCoef", 3, 0.1,
                     experimental=True, help="Armor-specific noise field; its audible/AI effect is unverified."),
    "limp_protection": Control("Prevent limping", "bPreventFromLimping", 1,
                               experimental=True, help="0 = off, 1 = on. This is separate from knockdown immunity."),
    "allow_helmet": Control("Allow a separate helmet", "bBlockHead", 1, body_only=True,
                            experimental=True, help="0 = block head slot, 1 = allow helmet. Model and protection stacking are not verified."),
    "free_sprint": Control("Remove armor sprint restriction", "", 1, body_only=True,
                           experimental=True, help="0 = keep the original armor restriction, 1 = remove it. Sprint speed stays unchanged."),
    "lead_slots": Control("Shield first artifact slots", "", 5, body_only=True,
                          experimental=True, help="Adds native radiation-blocking effects to the first N base slots. Does not remove technician protection. N must fit the base slot count."),
}
TOGGLES = {"limp_protection", "allow_helmet", "free_sprint"}
POSITIVE = {"durability", "grid_width", "grid_height"}


def clean(values):
    """Validate public Settings and imported profiles, including disabled sentinels."""
    if not isinstance(values, dict):
        raise ValueError("Per-armor settings must be an object.")
    result = {}
    for key, value in values.items():
        if key not in CONTROLS:
            continue
        spec = CONTROLS[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"Invalid armor value: {key}")
        if value == -1:
            continue
        minimum = 1 if key in POSITIVE else 0
        if not minimum <= value <= spec.maximum or (spec.step == 1 and value != int(value)):
            raise ValueError(f"Armor {spec.label}: enter -1 (inherit) or {minimum}–{spec.maximum:g}.")
        result[key] = value
    return result


def format_value(key, value):
    if value == -1:
        return "Inherit"
    if key in TOGGLES:
        return "On" if value else "Off"
    return f"{value:g}"


def chain_for(gd, sid, edition):
    return (gd.dlc_item_chain(edition, sid) if edition is not None
            else gd._resolve_chain(gd.items, sid))


def inventory(gd):
    """Visible player equipment, including edition-specific item branches."""
    editions = gd.dlc_armor_editions()
    return {sid: (slot, editions.get(sid))
            for sid, (slot, _) in gd.player_armors().items()}


def available(gd, sid, slot, edition):
    chain = chain_for(gd, sid, edition)
    return {key: spec for key, spec in CONTROLS.items()
            if (not spec.body_only or slot == "Body")
            and (not spec.path or gd._chain_get(chain, spec.path) is not None)}


def _number(value):
    return f"{value:.9g}"


def _put(cfg, path, value, original):
    parts = path.split(".")
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    # Clear an earlier global/item-factor patch when the explicit override
    # chooses the original value. Other fields on the same item are preserved.
    if original is not None and value == original:
        node.pop(parts[-1], None)
    else:
        node[parts[-1]] = value


def _effect_list(chain):
    values = {}
    for item in reversed(chain):
        node = item.children.get("EffectPrototypeSIDs")
        if node is None:
            continue
        if "bskipref" in node.attr_dict():
            values.clear()
        if node.children or any(not (key.startswith("[") and key.endswith("]") and key[1:-1].isdigit())
                                for key in node.values):
            raise ValueError("Unsupported armor effect list; no replacement was generated.")
        values.update(node.values)
    return values


def _sprint_blocker(gd, sid):
    node = gd.effects.children.get(sid)
    if node is None or node.get("ConditionSID") != "TargetHasAddSprintEffect":
        return False
    blocked = gd.effects.children.get(node.get("FalseEffectSID"))
    return (blocked is not None and blocked.get("Type") == "EEffectType::BlockAnimationActionType"
            and "EActionType::Sprint" in getattr(blocked.children.get("BlockAnimationTypes"), "values", {}).values())


def _lead_effect(gd, number):
    sid = f"ArtifactSlotBlockEffect3_Slot{number}"
    node = gd.effects.children.get(sid)
    if node is None or node.get("Type") != "EEffectType::ArtifactSlotBlock":
        raise ValueError(f"Native shielded-slot effect {number} is unavailable in this game data.")
    slots = getattr(node.children.get("ArtifactEquipmentSlots"), "values", {})
    blocked = getattr(node.children.get("EffectsToBlockIDs"), "values", {})
    if (set(slots.values()) != {f"EInventoryEquipmentSlot::Artifact{number}"}
            or not set(f"ArtifactAddRadiation{i}" for i in range(1, 5)).issubset(blocked.values())):
        raise ValueError(f"Native shielded-slot effect {number} has changed; refusing to guess.")
    return sid


def _composite_sid(mod_name, sid):
    digest = hashlib.sha256((mod_name + "\0" + sid).encode("utf-8")).hexdigest()[:20]
    return "S2Tweaker_ArmorLead_" + digest


def lead_composites(gd, settings):
    result = {}
    if not settings.armor_custom:
        return result
    known = inventory(gd)
    for sid, values in sorted(settings.armor_custom.items()):
        if sid not in known or known[sid][0] != "Body":
            continue
        count = int(clean(values).get("lead_slots", 0))
        if count <= 0:
            continue
        name = _composite_sid(settings.mod_name, sid)
        if name in gd.effects.children:
            raise ValueError("Generated armor effect name already exists in the source data.")
        result[name] = {"__new__": True, "__attrs__": "refkey=[0]", "SID": name,
                        "Type": "EEffectType::Composite",
                        "ApplyExtraEffectPrototypeSIDs": {
                            f"[{n-1}]": _lead_effect(gd, n) for n in range(1, count + 1)}}
    return result


def apply(gd, settings, patches, dlc_patches):
    if not (settings.armor_custom or settings.armor_free_sprint or settings.armor_limp_protection):
        return
    known = inventory(gd)
    selected = set(settings.armor_custom)
    if settings.armor_free_sprint or settings.armor_limp_protection:
        selected.update(known)
    for sid in sorted(selected):
        if sid not in known:
            continue
        slot, edition = known[sid]
        params = clean(settings.armor_custom.get(sid, {}))
        supported = available(gd, sid, slot, edition)
        params = {key: value for key, value in params.items() if key in supported}
        if settings.armor_limp_protection and slot == "Body" and "limp_protection" in supported:
            params.setdefault("limp_protection", 1)
        if settings.armor_free_sprint and slot == "Body":
            params.setdefault("free_sprint", 1)
        chain = chain_for(gd, sid, edition)
        bucket = patches if edition is None else dlc_patches.setdefault(edition, {})
        cfg = bucket.setdefault(sid, {})
        for key, value in params.items():
            path = CONTROLS[key].path
            if not path:
                continue
            original = gd._chain_get(chain, path)
            if key in ("limp_protection", "allow_helmet"):
                target = bool(value) if key == "limp_protection" else not bool(value)
                literal = "true" if target else "false"
                baseline = original.strip().rstrip(";").lower() if original is not None else None
            else:
                literal = _number(value)
                baseline = _number(parse_number(original)) if original is not None else None
            _put(cfg, path, literal, baseline)
        if params.get("free_sprint") == 1 or params.get("lead_slots", 0) > 0:
            effects = _effect_list(chain)
            changed = {}
            if params.get("free_sprint") == 1:
                for index, effect in effects.items():
                    if _sprint_blocker(gd, effect):
                        changed[index] = "empty"
            count = int(params.get("lead_slots", 0))
            slots = int(parse_number(cfg.get("ArtifactSlots", gd._chain_get(chain, "ArtifactSlots"))))
            if count > slots:
                raise ValueError(f"{sid}: {count} shielded slots require at least {count} base artifact slots (currently {slots}).")
            if count:
                for number in range(1, count + 1):
                    _lead_effect(gd, number)
                # Native wildcard append preserves other mods' existing indices.
                changed["[*]"] = _composite_sid(settings.mod_name, sid)
            if changed:
                cfg.setdefault("EffectPrototypeSIDs", {}).update(changed)
        for key in list(cfg):
            if cfg[key] == {}:
                del cfg[key]
        if not cfg:
            bucket.pop(sid, None)
    for edition in list(dlc_patches):
        if not dlc_patches[edition]:
            del dlc_patches[edition]


def summaries(custom, label):
    for sid, values in sorted(custom.items()):
        for key, value in sorted(clean(values).items()):
            yield f"Armor {label(sid)}: {CONTROLS[key].label} = {format_value(key, value)}"


def footprint(gd):
    from .modscan import EFFECT_LIST_LEAF
    pairs = set()
    for sid, (slot, edition) in inventory(gd).items():
        for spec in available(gd, sid, slot, edition).values():
            pairs.add((sid, spec.path.rsplit(".", 1)[-1] if spec.path else EFFECT_LIST_LEAF))
    return pairs
