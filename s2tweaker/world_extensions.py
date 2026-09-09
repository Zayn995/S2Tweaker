"""Selective world/AI additions researched against the installed game.

Lists are located by their current discriminators, never foreign mod indices.
Only existing leaves are scaled. Runtime gameplay remains unverified.
"""
from __future__ import annotations

import math
from .cfgparse import parse_number
from .emit import fmt_float

# UI choices are identifiers, not baked-in game values. Missing types are skipped.
SURFACES = (
    "Default", "Dirt", "Grass", "Brick", "Glass", "Sand", "Rock", "Asphalt",
    "Cloth", "Leather", "Rubber", "Paper", "Plastic", "Flesh", "FleshCloth",
    "FleshMetal", "MetalGrid", "Slate", "Water", "Chemical", "Bread",
    "Meat", "Vegetable", "Tree", "ForestGrass", "Puddle", "Gravel",
    "BrokenGlass", "Ground",
)
WEATHERS = ("Clearly", "Cloudy", "Fogy", "Stormy", "LightRainy", "Rainy",
            "Thundery", "Emission", "CalmBeforeEmission")


def _walk(node, path=()):
    yield path, node
    next_index = 0
    for key, child in node.children.items():
        if child.name == "[*]":
            key = f"[{next_index}]"
            next_index += 1
        elif key.startswith("[") and key.endswith("]") and key[1:-1].isdigit():
            next_index = int(key[1:-1]) + 1
        elif "#" in key:
            continue
        yield from _walk(child, path + (key,))


def _put(out, path, key, value):
    for part in path:
        out = out.setdefault(part, {})
    out[key] = value


def _scaled(raw, factor, *, cap=None, integer=False):
    if raw is None or not isinstance(factor, (int, float)) or not math.isfinite(factor):
        return None
    if factor < 0 or abs(factor - 1) < 1e-8:
        return None
    base = parse_number(raw, math.nan)
    if not math.isfinite(base) or base <= 0:
        return None
    value = base * factor
    if cap is not None:
        value = min(cap, value)
    if integer:
        value = max(1, int(value + .5))
    if abs(value - base) < 1e-8:
        return None
    return str(value) if integer else fmt_float(value)


def build(gd, s):
    """Return patches grouped by vanilla .cfg path, ready for nested merging."""
    out = {}
    ai = {}
    if (s.vegetation_translucency_factor != 1 or s.surface_noise_overrides
            or s.weather_luminance_overrides):
        root = gd.aiglobals.children.get("AISettings")
        if root:
            vegetation = {"PM_ForestGrass", "PM_Grass", "PM_Leaves"}
            for path, node in _walk(root):
                if path and path[0] == "MaterialTranslucencyList":
                    mats = node.children.get("Materials")
                    ids = {n.values.get("SID") for _, n in _walk(mats)} if mats else set()
                    ids.discard(None)
                    # Do not accidentally scale glass if a future game mixes it in.
                    if ids and ids <= vegetation:
                        value = _scaled(node.values.get("Translucency"),
                                        s.vegetation_translucency_factor, cap=1)
                        if value is not None:
                            _put(ai, path, "Translucency", value)
                if path and path[0] == "PhysMatSettings":
                    material = node.values.get("MaterialType", "").split("::")[-1]
                    value = _scaled(node.values.get("CharacterNoiseCoef"),
                                    s.surface_noise_overrides.get(material, 1))
                    if value is not None:
                        _put(ai, path, "CharacterNoiseCoef", value)
                        _put(ai, path, "MaterialType", node.values["MaterialType"])
                if "WeatherLuminanceCoefficients" in path:
                    weather = node.values.get("WeatherType", "").split("::")[-1]
                    value = _scaled(node.values.get("Coefficient"),
                                    s.weather_luminance_overrides.get(weather, 1))
                    if value is not None:
                        _put(ai, path, "Coefficient", value)
                        _put(ai, path, "WeatherType", node.values["WeatherType"])
    if ai:
        out["AIGlobals.cfg"] = {"AISettings": ai}

    core = {}
    fields = {
        "MutantLootContainerInteractRange": s.mutant_loot_range_factor,
        "MutantLootInteractHeightMax": s.mutant_loot_height_factor,
        "BoltLifetime": s.bolt_lifetime_factor,
        "ProjectileDecalLifeSpan": s.decal_lifetime_factor,
        "ProjectileDecalLifeSpanOnCorpse": s.decal_lifetime_factor,
        "AgentsDecalsPoolSize": s.decal_count_factor,
        "MeshesDecalsPoolSize": s.decal_count_factor,
        "CorpsesDecalsPoolSize": s.decal_count_factor,
        "ProjectileDecalMaxSaveCountOnCorpse": s.decal_count_factor,
    }
    if any(v != 1 for v in fields.values()) or s.mutant_loot_ground_access or s.mutant_cut_radius_factor != 1:
        for key, factor in fields.items():
            # Compose with the existing general interaction slider, not overwrite it.
            if factor != 1 and key in ("MutantLootContainerInteractRange", "MutantLootInteractHeightMax"):
                factor *= s.interaction_range_factor
            value = _scaled(gd.resolve(gd.corevars, "DefaultConfig", key), factor,
                            integer="PoolSize" in key or "SaveCount" in key)
            if value is not None:
                core[key] = value
            elif fields[key] != 1 and factor == 1 and key.startswith("MutantLoot"):
                # Two factors can cancel, so restore vanilla over the earlier patch.
                raw = gd.resolve(gd.corevars, "DefaultConfig", key)
                if raw is not None:
                    core[key] = raw
        raw = gd.resolve(gd.corevars, "DefaultConfig", "MutantLootInteractHeightMin")
        if s.mutant_loot_ground_access and raw is not None and parse_number(raw) != 0:
            core["MutantLootInteractHeightMin"] = "0.0"
        root = gd.corevars.children.get("DefaultConfig")
        params = root.children.get("MutantLootParams") if root else None
        if params:
            for path, node in _walk(params):
                value = _scaled(node.values.get("CutRadiusModifier"), s.mutant_cut_radius_factor)
                if value is not None:
                    _put(core, ("MutantLootParams",) + path, "CutRadiusModifier", value)
    if core:
        out["CoreVariables.cfg"] = {"DefaultConfig": core}

    if s.npc_dispersion_distance_factor != 1:
        cws = {}
        for sid in gd.weaponsettings.children:
            if "_NPC" not in sid or "#" in sid:
                continue
            value = _scaled(gd.resolve(gd.weaponsettings, sid, "FireDistanceDispersion"),
                            s.npc_dispersion_distance_factor)
            if value is not None:
                cws[sid] = {"FireDistanceDispersion": value}
        if cws:
            out["WeaponData/CharacterWeaponSettingsPrototypes.cfg"] = cws

    items = {}
    if s.mutant_trophy_weight_factor != 1 or s.mutant_trophy_value_factor != 1:
        for sid in gd.items.children:
            if sid == "MutantLootTemplate" or "#" in sid or sid in gd._quest_item_sids:
                continue
            chain = gd._resolve_chain(gd.items, sid)
            if not any(n.name == "MutantLootTemplate" for n in chain):
                continue
            for key, factor in (("Weight", s.mutant_trophy_weight_factor),
                                ("Cost", s.mutant_trophy_value_factor)):
                value = _scaled(gd.resolve(gd.items, sid, key), factor)
                if value is not None:
                    items.setdefault(sid, {})[key] = value
    if s.weird_flower_permanent and "AArtifactWeirdFlower" in gd.items.children:
        sid = "FlairDistanceModifierEffect"
        if gd.resolve(gd.effects, sid, "bIsPermanent") == "true":
            chain = gd._resolve_chain(gd.items, "AArtifactWeirdFlower")
            effects = next((n.children["EffectPrototypeSIDs"] for n in chain
                            if "EffectPrototypeSIDs" in n.children), None)
            if effects is not None and sid not in effects.values.values():
                # [*] is the native append syntax; retain every existing effect.
                items.setdefault("AArtifactWeirdFlower", {})["EffectPrototypeSIDs"] = {"[*]": sid}
    if items:
        out["ItemPrototypes.cfg"] = items
    return out
