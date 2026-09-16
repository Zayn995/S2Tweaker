"""Per-weapon fire modes and ammunition types resolved from installed data."""
from __future__ import annotations

from collections import Counter
from itertools import combinations

from .cfgparse import parse_number

FIRE_LABELS = {"SemiAutomatic": "Single", "Queue": "Burst", "Automatic": "Auto"}
AMMO_LABELS = {"Default": "Standard", "ArmorPiercing": "Armor-piercing",
               "Expanding": "Expanding", "Supersonic": "Supersonic"}
GROUPS = ("weapon_fire_modes", "weapon_ammo_types")


def decode(value, labels):
    """Validate a nonempty, duplicate-free selection; return canonical order."""
    if not isinstance(value, str):
        return ()
    parts = value.split(",")
    if not parts or len(parts) != len(set(parts)) or any(p not in labels for p in parts):
        return ()
    return tuple(p for p in labels if p in parts)


def label(value, labels):
    return " + ".join(labels[p] for p in decode(value, labels))


def chain(gd, sid, edition=None):
    return (gd.dlc_weapon_chain(edition, sid) if edition is not None
            else gd._resolve_chain(gd.weapongeneral, sid))


def block(gd, sid, name, edition=None):
    """Use the nearest complete array, respecting an explicit empty override."""
    for node in chain(gd, sid, edition):
        if name in node.children:
            return node.children[name]
        if name in node.values:
            return None
    return None


def scalar(gd, sid, name, edition=None):
    return gd._chain_get(chain(gd, sid, edition), name)


def fire_modes(gd, sid, edition=None):
    array = block(gd, sid, "FireTypes", edition)
    if array is None:
        return ()
    return tuple(v.split("::")[-1].strip() for v in array.values.values())


def burst_count(gd, sid, edition=None):
    """Retain a weapon's burst length, otherwise use the most common native length."""
    own = parse_number(scalar(gd, sid, "FireQueueCount", edition))
    if own >= 2 and own == int(own):
        return int(own)
    counts = Counter()
    editions = gd.dlc_weapon_editions()
    for other in gd.player_weapons():
        ed = editions.get(other)
        if "Queue" not in fire_modes(gd, other, ed):
            continue
        count = parse_number(scalar(gd, other, "FireQueueCount", ed))
        if count >= 2 and count == int(count):
            counts[int(count)] += 1
    return counts.most_common(1)[0][0] if counts else None


def ammo_types(gd, caliber):
    """Offer existing ammo items with a projectile mapping for this caliber."""
    table = gd.ammo_caliber_projectiles().get(caliber, {})
    found = set()
    for sid in gd.items.children:
        if "#" in sid or sid.startswith(("Template", "[")):
            continue
        if gd.resolve(gd.items, sid, "Caliber") != f"EAmmoCaliber::{caliber}":
            continue
        kind = (gd.resolve(gd.items, sid, "AmmoType") or "").split("::")[-1]
        if kind in table:
            found.add(kind)
    return tuple(kind for kind in AMMO_LABELS if kind in found)


def options(gd, sid, group, caliber=None):
    """Return selectable nonempty combinations for a known player weapon setup."""
    if gd is None or sid not in gd.player_weapons():
        return {}
    ed = gd.dlc_weapon_editions().get(sid)
    if group == "weapon_fire_modes":
        current = fire_modes(gd, sid, ed)
        if not current or any(k not in FIRE_LABELS for k in current):
            return {}
        labels = FIRE_LABELS
        kinds = tuple(k for k in labels if k != "Queue" or burst_count(gd, sid, ed))
    else:
        labels = AMMO_LABELS
        kinds = ammo_types(gd, caliber or gd.weapon_caliber(sid, ed))
        if not gd.weapon_ammo_slots(sid, ed):
            return {}
    return {",".join(combo): " + ".join(labels[k] for k in combo)
            for n in range(1, len(kinds) + 1) for combo in combinations(kinds, n)}


def baseline(gd, sid, group):
    ed = gd.dlc_weapon_editions().get(sid)
    kinds = (fire_modes(gd, sid, ed) if group == "weapon_fire_modes"
             else gd.weapon_ammo_slots(sid, ed).values())
    labels = FIRE_LABELS if group == "weapon_fire_modes" else AMMO_LABELS
    return ",".join(k for k in labels if k in kinds)


def footprint(gd, sid, group):
    ed = gd.dlc_weapon_editions().get(sid)
    leaves = ({"@FireTypes", "DefaultFireType", "FireQueueCount"} if group == GROUPS[0]
              else {"@AmmoTypeProjectiles", "AmmoType", "ProjectilePrototypeSID", "AmmoCaliber"})
    return {(node.name, leaf) for node in chain(gd, sid, ed) for leaf in leaves}


def clean(gd, values, group, calibers=None):
    """Remove unknown and neutral choices after a data or caliber change."""
    if not isinstance(values, dict):
        return {}
    labels = FIRE_LABELS if group == "weapon_fire_modes" else AMMO_LABELS
    result = {}
    for sid, value in values.items():
        kinds = decode(value, labels)
        canonical = ",".join(kinds)
        if not kinds:
            continue
        if gd is not None:
            if canonical not in options(gd, sid, group, (calibers or {}).get(sid)):
                continue
            if canonical == baseline(gd, sid, group):
                continue
        result[sid] = canonical
    return result


def _copy_entry(node):
    """Preserve installed slot metadata when replacing the surrounding array."""
    return {**node.values, **{key: _copy_entry(child) for key, child in node.children.items()}}


def apply(gd, settings, patches, dlc_patches):
    """Compose only selected arrays into existing base/edition weapon patches.

    Arrays are replaced as complete nested structs (no nested bpatch) so removing
    a mode/type cannot leave trailing native entries behind. Unrelated setup
    fields and existing reload, rate, magazine and caliber patches are retained.
    """
    editions = gd.dlc_weapon_editions()
    for sid, value in clean(gd, settings.weapon_fire_modes, GROUPS[0]).items():
        ed = editions.get(sid)
        kinds = decode(value, FIRE_LABELS)
        bucket = dlc_patches.setdefault(ed, {}) if ed else patches
        node = bucket.setdefault(sid, {})
        node["FireTypes"] = {"__new__": True, **{
            f"[{i}]": f"EFireType::{kind}" for i, kind in enumerate(kinds)}}
        default = scalar(gd, sid, "DefaultFireType", ed)
        if default not in {f"EFireType::{k}" for k in kinds}:
            node["DefaultFireType"] = f"EFireType::{kinds[0]}"
        if "Queue" in kinds:
            count = burst_count(gd, sid, ed)
            if parse_number(scalar(gd, sid, "FireQueueCount", ed)) != count:
                node["FireQueueCount"] = str(count)
    for sid, value in clean(gd, settings.weapon_ammo_types, GROUPS[1], settings.weapon_calibers).items():
        ed = editions.get(sid)
        caliber = settings.weapon_calibers.get(sid) or gd.weapon_caliber(sid, ed)
        table = gd.ammo_caliber_projectiles()[caliber]
        bucket = dlc_patches.setdefault(ed, {}) if ed else patches
        node = bucket.setdefault(sid, {})
        original = block(gd, sid, "AmmoTypeProjectiles", ed)
        entries = {entry.values.get("AmmoType", "").split("::")[-1]: entry
                   for entry in original.children.values()} if original else {}
        target = {"__new__": True}
        for i, kind in enumerate(decode(value, AMMO_LABELS)):
            # Keep any extra slot fields from the installed weapon where available.
            entry = _copy_entry(entries[kind]) if kind in entries else {}
            entry["AmmoType"] = f"EAmmoType::{kind}"
            if (caliber != gd.weapon_caliber(sid, ed)
                    or not entry.get("ProjectilePrototypeSID")):
                entry["ProjectilePrototypeSID"] = table[kind]
            target[f"[{i}]"] = entry
        node["AmmoTypeProjectiles"] = target
