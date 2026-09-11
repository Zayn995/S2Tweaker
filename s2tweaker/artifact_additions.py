"""Optional extra ordinary artifact bonuses; all magnitudes come from live data."""
from collections import defaultdict
import math

from . import artifact_extensions as a
from .cfgparse import parse_number

PREFIX = "extra_"
ARRAYS = ("EffectPrototypeSIDs", "ShouldShowEffects", "EffectsDisplayTypes")
DISPLAY = "EEffectDisplayType::EffectLevel"


def family(param):
    return param[len(PREFIX):] if param.startswith(PREFIX) else None


def _arrays(node):
    result = {}
    for name in ARRAYS:
        array = node.children.get(name)
        if array is None or array.attrs or array.children:
            return None
        if any(not (k.startswith("[") and k.endswith("]") and k[1:-1].isdigit()) for k in array.values):
            return None
        result[name] = dict(array.values)
    return result


def descendants(gd, target):
    children = defaultdict(list)
    for sid, node in gd.items.children.items():
        attrs = node.attr_dict()
        if "refurl" not in attrs:
            children[attrs.get("refkey")].append(sid)
    found, pending = [], list(children[target])
    seen = {target}
    while pending:
        sid = pending.pop()
        if sid in seen:
            raise ValueError("Cyclic artifact inheritance.")
        seen.add(sid)
        found.append(sid)
        pending.extend(children[sid])
    return sorted(found)


def supported(gd, target, kind):
    if kind not in a.EFFECT_LABELS or kind == "PenaltyLessWeightEffect" or not a._plain_item(gd, target):
        return False
    layout = _arrays(gd.items.children[target])
    effects = a._effect_indices(gd, target)
    if layout is None or set(effects) != set(a.ARTIFACTS[target]):
        return False
    if any(a.effect_family(sid) == kind for sid in effects):
        return False  # Existing bonuses already have their individual control.
    sources = ["Artifact" + kind + "1"]
    if kind == "AdditionalInventoryWeight":
        sources.append("ArtifactPenaltyLessWeightEffect1")
    if any(not a._safe_effect(gd, sid, a.effect_family(sid))
           or gd.resolve(gd.effects, sid, "EffectLevel") != "EEffectLevel::Low" for sid in sources):
        return False
    for child in descendants(gd, target):
        node = gd.items.children[child]
        if node.values.get("SID") != child or _arrays(node) is None:
            return False
    return True


def apply(gd, settings, source, patches, selected):
    if source not in ("ItemPrototypes", "EffectPrototypes"):
        return
    chosen = defaultdict(list)
    for c, percent in selected:
        if family(c.param) and c.key in a.available(gd):
            chosen[c.target].append((c, percent))
    if not chosen:
        return
    if not math.isfinite(settings.artifact_effect_factor) or settings.artifact_effect_factor < 0:
        raise ValueError("Artifact strength must be finite and nonnegative.")
    if settings.artifact_effect_factor == 0:
        return
    for target, choices in sorted(chosen.items()):
        layout = _arrays(gd.items.children[target])
        next_index = 1 + max(int(k[1:-1]) for values in layout.values() for k in values)
        added = []
        for c, percent in sorted(choices, key=lambda pair: pair[0].param):
            kind = family(c.param)
            sources = [("Artifact" + kind + "1", True)]
            if kind == "AdditionalInventoryWeight":
                sources.append(("ArtifactPenaltyLessWeightEffect1", False))
            for native, visible in sources:
                name = a.clone_sid(settings.mod_name, target, PREFIX + native)
                if name in gd.effects.children:
                    raise ValueError("Generated extra artifact effect already exists in game data.")
                cfg = {"__new__": True, "__attrs__": "refkey=" + native, "SID": name}
                for leaf in ("ValueMin", "ValueMax"):
                    raw = gd.resolve(gd.effects, native, leaf)
                    cfg[leaf] = a._literal(parse_number(raw) * settings.artifact_effect_factor * percent / 100, raw)
                label = gd.resolve(gd.effects, native, "LocalizationSID")
                cfg["LocalizationSID"] = label if label and label.lower() != "empty" else native
                if settings.artifact_stat_labels_follow:
                    a._sync_level(gd, native, cfg)
                if source == "EffectPrototypes":
                    patches[name] = cfg
                added.append((f"[{next_index}]", name, visible))
                next_index += 1
        if source != "ItemPrototypes":
            continue
        item_patch = patches.setdefault(target, {})
        for array, values in layout.items():
            values.update(item_patch.get(array, {}))  # Retain existing individual changes.
            for index, name, visible in added:
                values[index] = {"EffectPrototypeSIDs": name, "ShouldShowEffects": "true" if visible else "false",
                                 "EffectsDisplayTypes": DISPLAY}[array]
            item_patch[array] = values
        # A new parent index must not give its bonus to a fake or quest child.
        # Restore each descendant's effective original slot, or an empty hidden slot.
        for child in descendants(gd, target):
            original = _arrays(gd.items.children[child])
            for array, values in original.items():
                additions = {}
                for index, _, _ in added:
                    if index in values:
                        continue
                    value = gd.resolve(gd.items, child, array + "." + index)
                    fallback = {"EffectPrototypeSIDs": "empty", "ShouldShowEffects": "false", "EffectsDisplayTypes": DISPLAY}[array]
                    additions[index] = value if value is not None else fallback
                if additions:
                    changed = patches.setdefault(child, {})
                    values.update(changed.get(array, {}))
                    values.update(additions)
                    changed[array] = values


def footprint(gd, target, kind):
    sources = ["Artifact" + kind + "1"]
    if kind == "AdditionalInventoryWeight":
        sources.append("ArtifactPenaltyLessWeightEffect1")
    from .modscan import EFFECT_LIST_LEAF
    return {(item, leaf) for item in [target, *descendants(gd, target)]
            for leaf in (*ARRAYS, EFFECT_LIST_LEAF)} | {
                (sid, leaf) for sid in sources for leaf in
                ("ValueMin", "ValueMax", "Type", "LocalizationSID", "EffectLevel", "DuplicationType")}
