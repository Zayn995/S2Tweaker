"""Resolve native action-sound targets from the installed weapon configuration."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

from . import cfgparse

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "animation_sync"


def action_factors(settings):
    if not settings.sound_sync:
        return {}
    result = {}
    for key, field in (("audio.reload", "reload_speed_factor"),
                       ("audio.jam", "jam_clear_factor"),
                       ("audio.equip", "equip_speed_factor")):
        value = getattr(settings, field)
        if type(value) not in (int, float) or not math.isfinite(value) or not .0625 <= value <= 4:
            raise ValueError(f"Sound synchronization supports 6.25% to 400%: {field}")
        if not math.isclose(value, 1, rel_tol=0, abs_tol=1e-9):
            result[key] = value
    return result


def equipment_requested(settings):
    return settings.sound_sync and (
        not math.isclose(settings.equip_speed_factor, 1)
        or any(not math.isclose(row.get("equiptime", 1), 1)
               for group in (settings.weapon_overrides, settings.weapon_category_factors)
               for row in group.values()))


def mesh_targets(gd, equipment_settings=None):
    """Map loaded mesh names to the companion's stable, one-based family indices.

    Item and weapon inheritance include DLC cross-file references. Ambiguous
    mesh identities are omitted instead of attaching an unrelated effect.
    """
    catalog = json.loads((ASSETS / "audio_targets.json").read_text(encoding="utf-8"))
    families = {r["family"].casefold(): i for i, r in enumerate(catalog, 1)}
    meshes = cfgparse.parse_file(gd.dir / "MeshPrototypes.cfg")
    mesh_rows = {n.values.get("SID", n.name): n.name for n in meshes.children.values()}
    result, ambiguous = {}, set()
    equipment, equipment_ambiguous = {}, set()
    for item, (_, _, edition) in gd.slot_weapon_items().items():
        chain = gd.dlc_item_chain(edition, item) if edition else gd._resolve_chain(gd.items, item)
        sid = gd._chain_get(chain, "GeneralWeaponSetup")
        if not sid:
            continue
        switch = (gd.dlc_resolve_weapon(edition, sid, "WeaponTypeSoundSwitch") if edition
                  else gd.resolve(gd.weapongeneral, sid, "WeaponTypeSoundSwitch")) or ""
        family = switch.split("WeaponType-")[-1].rstrip("'")
        family = {"TOZ": "TOZ34", "SVDM": "SVD"}.get(family, family)
        index = families.get(family.casefold())
        mesh_sid = gd._chain_get(chain, "MeshPrototypeSID")
        row = mesh_rows.get(mesh_sid)
        if not index or not row:
            continue
        raw = gd.resolve(meshes, row, "MeshPath") or ""
        name = raw.rstrip("'\"").rsplit("/", 1)[-1].rsplit(".", 1)[-1]
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            continue
        if name in result and result[name] != index:
            ambiguous.add(name)
        result[name] = index
        if equipment_settings is not None:
            from .tweaks import _weapon_factor
            category = gd.dlc_weapon_category(edition, sid) if edition else gd.weapon_category(sid)
            factor = _weapon_factor(equipment_settings, category, sid, "equiptime",
                                    equipment_settings.equip_speed_factor)
            if type(factor) not in (int, float) or not math.isfinite(factor) or not .0625 <= factor <= 4:
                raise ValueError(f"Equipment sound synchronization supports 6.25% to 400%: {sid}")
            if name in equipment and not math.isclose(equipment[name], factor):
                equipment_ambiguous.add(name)
            equipment[name] = factor
    targets = {"audio.mesh." + name: index for name, index in result.items() if name not in ambiguous}
    # A shared mesh cannot identify different item variants at runtime. Refuse
    # conflicting equipment timing instead of silently using one variant's rate.
    if equipment_ambiguous:
        raise ValueError("Equipment sounds cannot distinguish variants sharing these meshes: "
                         + ", ".join(sorted(equipment_ambiguous))
                         + ". Use matching equipment speeds or disable weapon sound synchronization.")
    targets.update({"audio.equip." + name: factor for name, factor in equipment.items()
                    if name not in ambiguous and not math.isclose(factor, 1)})
    return targets


def movement_factors(settings):
    if not settings.movement_sound_sync:
        return {}
    result = {}
    for key, field in (("audio.walk", "walk_speed_factor"), ("audio.run", "run_speed_factor")):
        value = getattr(settings, field)
        if type(value) not in (int, float) or not math.isfinite(value) or not .0625 <= value <= 4:
            raise ValueError(f"Sound synchronization supports 6.25% to 400%: {field}")
        if not math.isclose(value, 1, rel_tol=0, abs_tol=1e-9):
            result[key] = value
    return {"audio.movement": 1, **result} if result or not math.isclose(settings.limp_speed_factor, 1) else {}


def profile_values(settings, gd):
    values = action_factors(settings)
    movement = movement_factors(settings)
    if movement:
        from .animation_sync import limp_values
        limping = {key.replace("movement.", "audio.", 1): value
                   for key, value in limp_values(settings, gd).items()}
        if any(not .0625 <= value <= 4 for value in limping.values()):
            raise ValueError("Combined movement and limping sound speed must stay between 6.25% and 400%.")
        movement.update(limping)
    equip = equipment_requested(settings)
    if not values and not equip:
        return movement
    if gd is None:
        raise ValueError("Load installed game data before enabling sound synchronization.")
    targets = mesh_targets(gd, settings if equip else None)
    if not targets:
        raise ValueError("No supported weapon sound families were found in the installed game data.")
    values.pop("audio.equip", None)  # Equipment factors are resolved per mesh.
    return {"audio.enabled": 1, **values, **targets, **movement}
