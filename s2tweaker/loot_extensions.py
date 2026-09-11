"""Optional loot additions, derived from the installed game's current tables.

Existing arrays are patched sparsely. New inventory groups have namespaced keys;
stash additions are attached to selected world containers, never shared pools.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from .cfgparse import CfgStruct, parse, parse_number

RANKS = ("Newbie", "Experienced", "Veteran", "Master")
STASH_BASES = frozenset("GamePass_Stash_ItemGenerator_" + suffix for suffix in
                       ("Cheap", "Common_Var1", "Common_Var2", "Rare"))
WEAPON_CATEGORIES = frozenset(("WeaponPrimary", "WeaponSecondary", "WeaponPistol"))
ARMOR_CATEGORIES = frozenset(("BodyArmor", "Head"))
GEN_PREFIX = "EItemGenerationCategory::"


def _setting(s, name, default):
    return getattr(s, name, default)


def _number(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _fmt(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _different(a, b):
    return not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def loot_namespace(mod_name="S2Tweaker"):
    """Stable config-safe names, distinct even when cleaned profile names match."""
    name = str(mod_name)
    readable = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_")[:24] or "Mod"
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
    return f"S2Tweaker_Loot_{readable}_{digest}"


def _name(kind, *parts, mod_name="S2Tweaker"):
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{loot_namespace(mod_name)}_{kind}_{digest}"


def _cached_data(gd, key, collect):
    """Settings-independent analyses live exactly as long as this GameData."""
    cache = gd.__dict__.setdefault("_loot_extensions_cache", {})
    if key not in cache:
        cache[key] = collect()
    return cache[key]


def _clone(node):
    result = {k: v.strip() for k, v in node.values.items()}
    result.update((k, _clone(v)) for k, v in node.children.items())
    return result


def _rows(slot):
    items = slot.children.get("PossibleItems")
    return ((k, v) for k, v in (items.children.items() if items else ())
            if "#" not in k and k != "[*]")


def _rank_set(raw):
    return {r for r in RANKS if f"ERank::{r}" in (raw or "")}


def _item_ok(gd, sid, *, visible=False):
    if (not sid or sid not in gd.items.children or sid.startswith("Template")
            or sid in gd._quest_item_sids or gd.LOOT_UNIQUE_ITEM.match(sid)
            or gd._loot_item_is_skippable(sid) or "Collar" in sid):
        return False
    if visible:
        for key in ("Invisible", "InvisibleInPlayerInventory", "DestroyOnPickup"):
            if (gd.resolve(gd.items, sid, key) or "").strip().lower() in ("true", "1"):
                return False
    return True


def _ordinary_npc_groups(gd):
    for key in gd.loot_generators():
        if not key.startswith("GeneralNPC_"):
            continue
        node = gd.itemgenerators.children[key]
        gen = node.children.get("ItemGenerator")
        for slot_key, slot in (gen.children.items() if gen else ()):
            if "#" not in slot_key and slot_key != "[*]":
                yield key, slot_key, slot


def _patch_row(patches, key, slot_key, row_key, changes):
    if changes:
        (patches.setdefault(key, {}).setdefault("ItemGenerator", {})
         .setdefault(slot_key, {}).setdefault("PossibleItems", {})
         .setdefault(row_key, {})).update(changes)


def _scaled_bounds(values, low, high, factor):
    if not math.isfinite(factor) or not _different(factor, 1.0) or factor < 0:
        return {}
    originals = {key: parse_number(values[key], math.nan) for key in (low, high) if key in values}
    if any(not math.isfinite(value) or value < 0 for value in originals.values()):
        return {}
    if low in originals and high in originals and originals[low] > originals[high]:
        return {}
    result = {}
    scaled = {key: value * factor for key, value in originals.items()}
    if any(not math.isfinite(value) for value in scaled.values()):
        return {}
    numbers = {key: max(0, int(round(value))) for key, value in scaled.items()}
    if low in numbers and high in numbers:
        numbers[low] = min(numbers[low], numbers[high])
    for key, value in numbers.items():
        if _different(value, parse_number(values[key])):
            result[key] = str(value)
    return result


def _restrictions(slot):
    return {key: slot.values[key] for key in ("PlayerRank", "Diff")
            if key in slot.values}


def _lottery(candidates, mod_name):
    """New inventory lottery: no numeric positions from another mod."""
    return {"__new__": True,
            "Category": GEN_PREFIX + "Consumable",
            "bAllowSameCategoryGeneration": "true",
            "PossibleItems": {_name("Item", sid, mod_name=mod_name): values
                              for sid, values in sorted(candidates.items())}}


def _subgenerator(helper, chance, mod_name, restrictions=None):
    return {"__new__": True, **(restrictions or {}),
            "Category": GEN_PREFIX + "SubItemGenerator",
            "PossibleItems": {_name("Selection", mod_name=mod_name): {
                "ItemGeneratorPrototypeSID": helper, "Chance": _fmt(chance)}}}


def _npc_patches(gd, s):
    ammo = max(0.0, _number(_setting(s, "npc_loaded_ammo_factor", 1), 1))
    helmet = max(0.0, _number(_setting(s, "npc_helmet_chance_factor", 1), 1))
    armor_chance = min(100., max(0., _number(_setting(s, "npc_armor_drop_chance_pct", 0)))) / 100
    variety = bool(_setting(s, "npc_equipment_variety", False))
    if ammo == helmet == 1 and armor_chance == 0 and not variety:
        return {}
    mod_name = _setting(s, "mod_name", "S2Tweaker")
    patches = {}
    groups = list(_ordinary_npc_groups(gd))
    by_generator = {}
    for key, slot_key, slot in groups:
        by_generator.setdefault(key, []).append((slot_key, slot))
    for key, slot_key, slot in groups:
        category = slot.values.get("Category", "").removeprefix(GEN_PREFIX)
        for row_key, row in _rows(slot):
            sid = row.values.get("ItemPrototypeSID", "").strip()
            if not _item_ok(gd, sid):
                continue
            changes = {}
            if category in WEAPON_CATEGORIES and gd.item_category(sid) == "weapon":
                changes.update(_scaled_bounds(row.values, "AmmoMinCount", "AmmoMaxCount", ammo))
            if (category == "Head" and helmet != 1 and "Chance" in row.values
                    and gd.item_category(sid) == "armor"):
                original = parse_number(row.values["Chance"])
                changed = min(1., max(0., original * helmet))
                if _different(changed, original):
                    changes["Chance"] = _fmt(changed)
            _patch_row(patches, key, slot_key, row_key, changes)

        if armor_chance > 0 and category == "BodyArmor":
            low = min(1., max(0., _number(_setting(s, "npc_armor_drop_min_pct", 20), 20) / 100))
            high = min(1., max(0., _number(_setting(s, "npc_armor_drop_max_pct", 80), 80) / 100))
            low, high = sorted((low, high))
            candidates = {}
            for _, row in _rows(slot):
                sid = row.values.get("ItemPrototypeSID", "").strip()
                weight = parse_number(row.values.get("Weight", row.values.get("Chance")))
                if (weight > 0 and _item_ok(gd, sid, visible=True)
                        and gd.item_category(sid) == "armor"):
                    candidates[sid] = {"ItemPrototypeSID": sid, "Weight": _fmt(weight),
                                       "MinCount": "1", "MaxCount": "1",
                                       "MinDurability": _fmt(low), "MaxDurability": _fmt(high)}
            if candidates:
                helper = _name("ArmorLoot", key, slot_key, mod_name=mod_name)
                patches[helper] = {"__new__": True, "SID": helper,
                                   "ItemGenerator": {_name("Armor", mod_name=mod_name): _lottery(candidates, mod_name)}}
                (patches.setdefault(key, {}).setdefault("ItemGenerator", {}))[
                    _name("ArmorDrop", slot_key, mod_name=mod_name)] = _subgenerator(
                        helper, armor_chance, mod_name, _restrictions(slot))

        if variety and category in WEAPON_CATEGORIES | ARMOR_CATEGORIES:
            _add_earlier_equipment(gd, s, patches, key, slot_key, slot,
                                   by_generator[key], ammo)
    return patches


def _add_earlier_equipment(gd, s, patches, key, slot_key, slot, siblings, ammo):
    ranks = _rank_set(slot.values.get("PlayerRank"))
    if not ranks:
        return
    earliest = min(RANKS.index(r) for r in ranks)
    if earliest == 0:
        return
    category = slot.values.get("Category")
    own_rows = list(_rows(slot))
    # A Chance list is not an equipment Weight lottery; never mix mechanisms.
    if not own_rows or any("Weight" not in row.values for _, row in own_rows):
        return
    existing = {row.values.get("ItemPrototypeSID") for _, row in own_rows}
    target_diff = {x.strip() for x in slot.values.get("Diff", "").split(",") if x.strip()}
    additions = {}
    for source_key, source in siblings:
        source_ranks = _rank_set(source.values.get("PlayerRank"))
        if (source_key == slot_key or source.values.get("Category") != category
                or not source_ranks
                or min(RANKS.index(r) for r in source_ranks) >= earliest):
            continue
        source_diff = {x.strip() for x in source.values.get("Diff", "").split(",") if x.strip()}
        if source_diff and (not target_diff or not target_diff <= source_diff):
            continue
        for _, row in _rows(source):
            sid = row.values.get("ItemPrototypeSID", "").strip()
            expected = "weapon" if category.removeprefix(GEN_PREFIX) in WEAPON_CATEGORIES else "armor"
            if (sid in existing or sid in additions or "Weight" not in row.values
                    or parse_number(row.values["Weight"]) <= 0 or not _item_ok(gd, sid, visible=True)
                    or gd.item_category(sid) != expected):
                continue
            values = _clone(row)
            values["__new__"] = True
            values.update(_scaled_bounds(row.values, "AmmoMinCount", "AmmoMaxCount", ammo))
            # A copied candidate participates in the current dropped-condition option.
            if (gd.item_category(sid) == "weapon"
                    and "MinDurability" in values and "MaxDurability" in values):
                target = _number(_setting(s, "dropped_condition_pct", 37.5), 37.5)
                exact = bool(_setting(s, "dropped_condition_exact", False))
                if target != 37.5 or exact:
                    low, high = parse_number(values["MinDurability"]), parse_number(values["MaxDurability"])
                    center = target / 100 if target != 37.5 else (low + high) / 2
                    width = 0 if exact else (high - low) / 2
                    values.update(MinDurability=_fmt(max(0., min(1., center - width))),
                                  MaxDurability=_fmt(max(0., min(1., center + width))))
            additions[sid] = values
    _expanded_gear_quality(gd, s, patches, key, slot_key, own_rows, additions)
    for sid, values in additions.items():
        _patch_row(patches, key, slot_key, _name("EarlierGear", sid,
                   mod_name=_setting(s, "mod_name", "S2Tweaker")), values)


def _expanded_gear_quality(gd, s, patches, key, slot_key, own_rows, additions):
    """Apply the existing quality weighting to the final expanded lottery."""
    from .npc_equipment import quality_weight, _fmt as weight_literal
    factor = _number(_setting(s, "npc_gear_quality_factor", 1), 1)
    if not additions or factor <= 0 or factor == 1:
        return
    entries = [(row_key, row.values, False) for row_key, row in own_rows]
    entries.extend((sid, values, True) for sid, values in additions.items())
    costs = {}
    for row_key, values, added in entries:
        sid = values.get("ItemPrototypeSID", "")
        cost = parse_number(gd.resolve(gd.items, sid, "Cost"))
        if _item_ok(gd, sid) and cost > 0:
            costs[(row_key, added)] = cost
    levels = sorted(set(costs.values()))
    if len(levels) < 2:
        return
    ranks = {cost: index / (len(levels) - 1) for index, cost in enumerate(levels)}
    original_levels = sorted({cost for (_, added), cost in costs.items() if not added})
    original_ranks = ({cost: index / (len(original_levels) - 1)
                       for index, cost in enumerate(original_levels)} if len(original_levels) > 1 else {})
    for row_key, values, added in entries:
        cost = costs.get((row_key, added))
        weight = parse_number(values.get("Weight"))
        if cost is None or weight <= 0:
            continue
        changed = quality_weight(weight, factor, ranks[cost])
        if added:
            values["Weight"] = weight_literal(changed)
        else:
            earlier = (quality_weight(weight, factor, original_ranks[cost])
                       if cost in original_ranks else weight)
            if _different(changed, weight) or _different(earlier, weight):
                _patch_row(patches, key, slot_key, row_key, {"Weight": weight_literal(changed)})


def mutant_species(gd):
    """Available species keys derived from verified ordinary trophy entries."""
    return sorted({species for species, *_ in _trophy_entries(gd)})


def _trophy_entries(gd):
    safe = set(gd.loot_generators())
    for key, node in gd.itemgenerators.children.items():
        sid = node.values.get("SID", key)
        if key not in safe or not sid.endswith("LootGenerator"):
            continue
        gen = node.children.get("ItemGenerator")
        for slot_key, slot in (gen.children.items() if gen else ()):
            if slot.values.get("Category") != GEN_PREFIX + "MutantLoot" or "#" in slot_key:
                continue
            for row_key, row in _rows(slot):
                item = row.values.get("ItemPrototypeSID", "").strip()
                if (not _item_ok(gd, item, visible=True)
                        or gd.resolve(gd.items, item, "Type") != "EItemType::MutantLoot"):
                    continue
                # The base trophy generator's species identity must match its item.
                if sid != item + "Generator" or not item.endswith("Loot"):
                    continue
                yield item[:-4], key, slot_key, row_key, row


def mutant_loot_patch(gd, s):
    global_chance = max(0., _number(_setting(s, "mutant_loot_chance_factor", 1), 1))
    overrides = _setting(s, "mutant_loot_overrides", {}) or {}
    if not isinstance(overrides, dict):
        overrides = {}
    if global_chance == 1 and not overrides:
        return {}
    patches = {}
    for species, key, slot_key, row_key, row in _trophy_entries(gd):
        override = overrides.get(species, {})
        if not isinstance(override, dict):
            continue
        chance = global_chance * max(0., _number(override.get("chance_factor", 1), 1))
        amount = max(0., _number(override.get("amount_factor", 1), 1))
        changes = {}
        if "Chance" in row.values and chance != 1:
            original = parse_number(row.values["Chance"])
            new = min(1., max(0., original * chance))
            if _different(new, original):
                changes["Chance"] = _fmt(new)
        if amount != 1:
            # Existing global amount runs before this extension. Compose explicitly.
            global_amount = max(0., _number(_setting(s, "loot_amount_factor", 1), 1))
            amount *= global_amount
            changes.update(_scaled_bounds(row.values, "MinCount", "MaxCount", amount))
            if global_amount != 1:
                # Explicitly replace earlier globally-scaled leaves even when the
                # combined factors cancel back to the original integer count.
                for field in ("MinCount", "MaxCount"):
                    if field in row.values:
                        changes[field] = str(max(0, round(parse_number(row.values[field]) * amount)))
        _patch_row(patches, key, slot_key, row_key, changes)
    return patches


def _effective_generator(gd, key):
    for node in gd._resolve_chain(gd.itemgenerators, key):
        if "ItemGenerator" in node.children:
            return node.children["ItemGenerator"]
    return None


def _safe_stash_tree(gd, key, seen=None):
    """Fail closed on unsafe branches; return whether a verified stash base occurs."""
    seen = set() if seen is None else seen
    if key in seen or key not in gd.itemgenerators.children:
        return False, False
    node = gd.itemgenerators.children[key]
    sid = node.values.get("SID", key)
    if (key == "[0]" or "#" in key or key in gd._trade_generator_keys
            or key in gd.LOOT_DENY_SIDS or gd.LOOT_UNSAFE_NAME.search(sid)):
        return False, False
    gen = _effective_generator(gd, key)
    if gen is None:
        return False, False
    found = sid in STASH_BASES
    for slot in gen.children.values():
        for _, row in _rows(slot):
            item = row.values.get("ItemPrototypeSID", "").strip()
            if item and item not in gd.LOOT_EMPTY_ITEMS:
                # Preserve existing money, but never manufacture it as extra finds.
                if item not in gd._money_item_sids and not _item_ok(gd, item, visible=True):
                    return False, False
            ref = row.values.get("ItemGeneratorPrototypeSID", "").strip()
            if ref:
                child = gd._generator_key_by_sid.get(ref)
                safe, reaches = _safe_stash_tree(gd, child, seen | {key}) if child else (False, False)
                if not safe:
                    return False, False
                found |= reaches
    return True, found


def _stream_spawn_containers(path: Path):
    """Keep only one top-level struct in memory from the very large spawn file."""
    lines, depth = [], 0
    with path.open(encoding="utf-8-sig") as source:
        for line in source:
            lines.append(line)
            if re.search(r":\s*struct\.begin", line):
                depth += 1
            elif line.strip() == "struct.end":
                depth -= 1
            if depth == 0:
                text = "".join(lines)
                lines.clear()
                if ("ESpawnType::ItemContainer" in text and "ItemGeneratorSettings" in text
                        and "Stash" in text and "WorldMap_WP" in text):
                    yield from parse(text).children.items()


def _stash_candidates(gd):
    return _cached_data(gd, "stash_candidates", lambda: _collect_stash_candidates(gd))


def _collect_stash_candidates(gd):
    """Category -> rank -> item IDs. Only live, ordinary availability is used."""
    candidates = {cat: {rank: set() for rank in RANKS}
                  for cat in ("weapon", "armor", "attach", "artifact")}
    for _, _, slot in _ordinary_npc_groups(gd):
        rank_set = _rank_set(slot.values.get("PlayerRank")) or set(RANKS)
        for _, row in _rows(slot):
            sid = row.values.get("ItemPrototypeSID", "").strip()
            if not _item_ok(gd, sid, visible=True):
                continue
            cat = gd.item_category(sid)
            if cat not in ("weapon", "armor"):
                continue
            for rank in rank_set:
                candidates[cat][rank].add(sid)
    # Attachments must already occur in safe ordinary loot, not only templates.
    for key in gd.loot_generators():
        gen = _effective_generator(gd, key)
        for slot in (gen.children.values() if gen else ()):
            rank_set = _rank_set(slot.values.get("PlayerRank")) or set(RANKS)
            for _, row in _rows(slot):
                sid = row.values.get("ItemPrototypeSID", "").strip()
                if _item_ok(gd, sid, visible=True) and gd.item_category(sid) == "attach":
                    for rank in rank_set:
                        candidates["attach"][rank].add(sid)
    for key, spawner in gd.artifactspawners.children.items():
        if gd.LOOT_UNSAFE_NAME.search(key) or "#" in key:
            continue
        if (gd.resolve(gd.artifactspawners, key, "UseListOfArtifacts") or "").lower() != "true":
            continue
        items = spawner.children.get("ListOfArtifacts")
        for sid in (items.values.values() if items else ()):
            sid = sid.strip()
            if (not _item_ok(gd, sid, visible=True) or gd.item_category(sid) != "artifact"
                    or gd.resolve(gd.items, sid, "ArchiartifactType") not in
                    (None, "EArchiartifactType::None")):
                continue
            for rank in RANKS:
                count = gd.resolve(gd.artifactspawners, key, rank + ".Count")
                if count is not None and parse_number(count) > 0:
                    candidates["artifact"][rank].add(sid)
    return candidates


def _stash_conditions(gd):
    return _cached_data(gd, "stash_conditions", lambda: _collect_stash_conditions(gd))


def _collect_stash_conditions(gd):
    """Current ordinary NPC weapon conditions, keyed by rank and item identity."""
    result = {}
    for _, _, slot in _ordinary_npc_groups(gd):
        rank_set = _rank_set(slot.values.get("PlayerRank")) or set(RANKS)
        for _, row in _rows(slot):
            sid = row.values.get("ItemPrototypeSID", "").strip()
            if not _item_ok(gd, sid, visible=True) or gd.item_category(sid) != "weapon":
                continue
            if not {"MinDurability", "MaxDurability"} <= row.values.keys():
                continue
            low, high = (parse_number(row.values[key]) for key in ("MinDurability", "MaxDurability"))
            if not 0 <= low <= high <= 1:
                continue
            for rank in rank_set:
                result.setdefault((rank, sid), {"MinDurability": row.values["MinDurability"],
                                                "MaxDurability": row.values["MaxDurability"]})
    return result


def _stash_targets(gd):
    return _cached_data(gd, "stash_targets", lambda: _collect_stash_targets(gd))


def _collect_stash_targets(gd):
    """Retain only vetted (spawn SID, rank key, rank) tuples, never a full parse."""
    source = gd.stash_spawn_source()
    targets = []
    suitability = {}
    for key, spawn in _stream_spawn_containers(source):
        if (spawn.attrs or spawn.values.get("LevelName") != "WorldMap_WP"
                or spawn.values.get("SpawnOnStart", "").lower() != "true"
                or spawn.values.get("DLC") not in ("None", "BaseGame")
                or spawn.values.get("SpawnType") != "ESpawnType::ItemContainer"):
            continue
        settings = spawn.children.get("ItemGeneratorSettings")
        if settings is None:
            continue
        for rank_key, rank_node in settings.children.items():
            if "#" in rank_key or rank_key == "[*]":
                continue
            rank_set = _rank_set(rank_node.values.get("PlayerRank"))
            if len(rank_set) != 1:
                continue
            rank = next(iter(rank_set))
            refs = rank_node.children.get("ItemGenerators")
            if refs is None:
                continue
            suitable, reached = True, False
            for ref_node in refs.children.values():
                ref = ref_node.values.get("PrototypeSID", "").strip()
                gen_key = gd._generator_key_by_sid.get(ref)
                if gen_key not in suitability:
                    suitability[gen_key] = _safe_stash_tree(gd, gen_key) if gen_key else (False, False)
                safe, has_stash = suitability[gen_key]
                suitable &= safe
                reached |= has_stash
            if not suitable or not reached:
                continue
            targets.append((key, rank_key, rank))
    return tuple(targets)


def _stash_patches(gd, s):
    enabled = {cat for cat, field in (("artifact", "artifacts"), ("weapon", "weapons"),
                                     ("armor", "armor"), ("attach", "attachments"))
               if _setting(s, "stash_extra_" + field, False)}
    chance = min(1., max(0., _number(_setting(s, "stash_extra_chance_pct", 10), 10) / 100))
    if not enabled or not chance:
        return {}, {}
    mod_name = _setting(s, "mod_name", "S2Tweaker")
    candidates = _stash_candidates(gd)
    conditions = _stash_conditions(gd) if "weapon" in enabled else {}
    generators, spawns, used_ranks = {}, {}, set()
    for key, rank_key, rank in _stash_targets(gd):
        if not any(candidates[cat][rank] for cat in enabled):
            continue
        helper = _name("ExtraStash", rank, mod_name=mod_name)
        (spawns.setdefault(key, {}).setdefault("ItemGeneratorSettings", {})
         .setdefault(rank_key, {}).setdefault("ItemGenerators", {}))[
             _name("ExtraFinds", mod_name=mod_name)] = {"__new__": True, "PrototypeSID": helper}
        used_ranks.add(rank)
    for rank in sorted(used_ranks):
        helper = _name("ExtraStash", rank, mod_name=mod_name)
        slots = {}
        for cat in sorted(enabled):
            items = candidates[cat][rank]
            if not items:
                continue
            pool = _name("StashPool", rank, cat, mod_name=mod_name)
            values = {sid: {"ItemPrototypeSID": sid, "Weight": "1", "MinCount": "1", "MaxCount": "1"}
                      for sid in items}
            if cat in ("weapon", "armor"):
                for sid, item in values.items():
                    # Newly added armor is intact. Weapons use the corresponding
                    # live NPC candidate's condition where the game specifies it.
                    item.update(conditions.get((rank, sid), {"MinDurability": "1", "MaxDurability": "1"}))
            generators[pool] = {"__new__": True, "SID": pool,
                                "ItemGenerator": {_name("Inventory", mod_name=mod_name): _lottery(values, mod_name)}}
            slots[_name(cat, mod_name=mod_name)] = _subgenerator(pool, chance, mod_name)
        generators[helper] = {"__new__": True, "SID": helper, "ItemGenerator": slots}
    return generators, spawns


def build(gd, settings):
    """Return raw patch trees keyed by base file name, including `.cfg`."""
    generators = _npc_patches(gd, settings)
    trophies = mutant_loot_patch(gd, settings)
    for key, value in trophies.items():
        # These dedicated trophy roots cannot overlap ordinary NPC pools.
        generators[key] = value
    stash_generators, spawns = _stash_patches(gd, settings)
    generators.update(stash_generators)
    result = {}
    if generators:
        result["ItemGeneratorPrototypes.cfg"] = generators
    if spawns:
        result["SpawnActorPrototypes.cfg"] = spawns
    return result
