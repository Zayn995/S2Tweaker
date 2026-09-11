"""Isolated ordinary NPC equipment choices; see NPC_EQUIPMENT_RESEARCH.md."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import math

from .cfgparse import parse_number
from .npc_equipment_scope import OBJECTS, SOURCES, LINKS, POOLS
from .names import WEAPON_ALIASES, ARMOR_ALIASES
from .detail_scope import HELMET_POOLS

PREFIX = "npc_equipment:"
RANKS = ("Newbie", "Experienced", "Veteran", "Master")
DIFFICULTIES = ("Easy", "Medium", "Hard", "Stalker")
CATEGORIES = {"WeaponPrimary": "Primary weapon", "WeaponPistol": "Pistol", "BodyArmor": "Body armor"}
CONTROL_POOLS = {**POOLS, **{key: ("EItemGenerationCategory::Head", rank, diff, ((row, item),))
                           for key, (rank, diff, row, item) in HELMET_POOLS.items()}}
NOTE = ("Ordinary faction/role profiles, including their use as generic enemies in missions. "
        "Rank means player progression; shared rank groups stay together. Existing NPC inventories may not refresh. "
        "New generator loading and gameplay effects are not play-tested yet.")


def _mask(raw, prefix, allowed):
    return frozenset(allowed) if not raw else frozenset(x.strip().removeprefix(prefix) for x in raw.split(","))


def _routes(source, seen=(), ranks=frozenset(RANKS), diffs=frozenset(DIFFICULTIES)):
    if source in seen:
        return
    yield source, ranks, diffs
    for _slot, _row, target, rank, diff in LINKS.get(source, ()):
        rs = ranks & _mask(rank, "ERank::", RANKS)
        ds = diffs & _mask(diff, "EGameDifficulty::", DIFFICULTIES)
        if rs and ds:
            yield from _routes(target, (*seen, source), rs, ds)


@dataclass(frozen=True)
class Control:
    obj: str
    source: str
    slot: str
    row: str
    item: str
    context: str

    default = 100
    lo = minimum = 0
    maximum = 400
    decimals = 0

    @property
    def key(self):
        prefix = "npc_helmet:" if self.kind == "Chance" else PREFIX
        return f"{prefix}{self.obj}:{self.source}:{self.slot}:{self.row}"

    @property
    def kind(self):
        return "Chance" if (self.source, self.slot) in HELMET_POOLS else "Weight"

    @property
    def faction(self):
        return OBJECTS[self.obj][0]

    @property
    def role(self):
        return self.obj.rsplit("_", 1)[-1].replace("CloseCombat", "Close combat")

    @property
    def pool(self):
        category = "Optional helmet" if self.kind == "Chance" else CATEGORIES[POOLS[self.source, self.slot][0].split("::")[-1]]
        # Helper variants can have identical masks; keep their identity visible.
        variant = "" if self.source == OBJECTS[self.obj][2] else " / " + self.source.removeprefix("GeneralNPC_")
        return f"{category} / {self.context}{variant} / {self.slot}"

    @property
    def selection(self):
        return f"NPC equipment / {self.faction} / {self.role} / {self.pool} /"

    @property
    def title(self):
        name = ARMOR_ALIASES.get(self.item) or WEAPON_ALIASES.get(self.item) or WEAPON_ALIASES.get(self.item + "_GS") or self.item
        return name + (" generation chance (%)" if self.kind == "Chance" else " relative weight (%)")

    @property
    def label(self):
        return self.selection + " " + self.title

    @property
    def help(self):
        if self.kind == "Chance":
            return (f"Item identifier: {self.item}. 100% inherits the globally adjusted helmet chance; "
                    "this extra factor multiplies the resulting chance, capped at 100%. 0% disables this optional roll. "
                    "Shared native rank groups stay together. This is generated head equipment, not armor drop chance or night vision. " + NOTE)
        return (f"Item identifier: {self.item}. "
                "100% inherits global gear quality; 0% disables this choice if another final choice remains. "
                "Weights are relative, not drop chances. Scaling every choice equally keeps the same ratios. "
                "Only existing candidates are editable; lower-rank variety additions keep their global settings. " + NOTE)

    def validate(self, value):
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not self.lo <= value <= self.maximum or value != int(value)):
            raise ValueError("NPC equipment: enter a whole percentage from 0 to 400 (100 = inherit).")
        return float(value)


def _controls():
    for obj, (_faction, _npc, root) in OBJECTS.items():
        contexts = {}
        for source, ranks, diffs in _routes(root):
            for (pool_source, slot), (_cat, rank, diff, rows) in CONTROL_POOLS.items():
                if source != pool_source:
                    continue
                rs = ranks & _mask(rank, "ERank::", RANKS)
                ds = diffs & _mask(diff, "EGameDifficulty::", DIFFICULTIES)
                if rs and ds:
                    rlabel = " + ".join(r for r in RANKS if r in rs)
                    dlabel = " + ".join(d for d in DIFFICULTIES if d in ds)
                    contexts.setdefault((source, slot), set()).add(rlabel + " / " + dlabel)
        for (source, slot), labels in contexts.items():
            for row, item in CONTROL_POOLS[source, slot][3]:
                yield Control(obj, source, slot, row, item, " or ".join(sorted(labels)))


CONTROLS = {c.key: c for c in _controls()}


def control_specs():
    return ((c.key, c.label, c.lo, c.maximum, c.default, c.help) for c in CONTROLS.values())


def changes(values):
    if not isinstance(values, dict):
        raise ValueError("NPC equipment settings must be a mapping.")
    for key, value in values.items():
        c = CONTROLS.get(key)
        if c is not None:
            value = c.validate(value)
            if value != c.default:
                yield c, value


def collect(sliders):
    return {key: c.validate(sliders[key].get()) for key, c in CONTROLS.items()
            if key in sliders and sliders[key].get() != c.default}


def _source_ok(gd, source):
    node = gd.itemgenerators.children.get(source)
    return (node is not None and node.values.get("SID") == source
            and node.attr_dict() == SOURCES[source]
            and "ItemGenerator" in node.children)


def _object_ok(gd, obj, children):
    faction, npc, source = OBJECTS[obj]
    node = gd.obj.children.get(obj)
    if (node is None or node.attr_dict() != {"refkey": "NPCBase"}
            or any(node.values.get(k) != v for k, v in {
                "SID": obj, "Faction": faction, "NPCPrototypeSID": npc,
                "ItemGeneratorPrototypeSID": source, "Type": "EObjType::NPC"}.items())
            or gd.resolve(gd.obj, obj, "IsZombie") != "false"
            or gd.resolve(gd.obj, obj, "NPCType") != "ENPCType::None"
            or gd.resolve(gd.npcprototypes, npc, "QuestNPC") != "false"
            or gd.resolve(gd.npcprototypes, npc, "UseGeneratedName") != "true"):
        return False
    # A child with no own link would unexpectedly inherit the new generator.
    if any("ItemGeneratorPrototypeSID" not in gd.obj.children[ch].values for ch in children.get(obj, ())):
        return False
    for sid, _rs, _ds in _routes(source):
        if not _source_ok(gd, sid):
            return False
        gen = gd.itemgenerators.children[sid].children["ItemGenerator"]
        for slot, row, target, rank, diff in LINKS.get(sid, ()):
            path = f"{slot}.PossibleItems.{row}.ItemGeneratorPrototypeSID"
            group = gen.children.get(slot)
            if (group is None or gen.get(path) != target
                    or group.values.get("PlayerRank", "") != rank
                    or group.values.get("Diff", "") != diff):
                return False
    return True


def _pool(gd, source, slot):
    from .loot_extensions import _item_ok
    if not _source_ok(gd, source):
        return None
    category, ranks, diff, rows = POOLS[source, slot]
    group = gd.itemgenerators.children[source].children["ItemGenerator"].children.get(slot)
    if (group is None or group.attrs or group.values.get("Category") != category
            or group.values.get("PlayerRank", "") != ranks or group.values.get("Diff", "") != diff):
        return None
    possible = group.children.get("PossibleItems")
    if possible is None or possible.attrs or possible.values or set(possible.children) != {r for r, _ in rows}:
        return None
    result = {}
    for row, item in rows:
        node = possible.children[row]
        path = f"ItemGenerator.{slot}.PossibleItems.{row}.Weight"
        weight = parse_number(gd.resolve(gd.itemgenerators, source, path), math.nan)
        if (node.attrs or node.children or "Weight" not in node.values or "Chance" in node.values
                or "ItemGeneratorPrototypeSID" in node.values or node.values.get("ItemPrototypeSID") != item
                or not math.isfinite(weight) or weight <= 0 or not _item_ok(gd, item)
                or gd.item_category(item) != ("armor" if category.endswith("BodyArmor") else "weapon")):
            return None
        result[row] = weight
    return result


def _helmet_pool(gd, source, slot):
    from .loot_extensions import _item_ok
    if not _source_ok(gd, source):
        return None
    rank, diff, row, item = HELMET_POOLS[source, slot]
    group = gd.itemgenerators.children[source].children["ItemGenerator"].children.get(slot)
    if (group is None or group.attrs or group.values.get("Category") != "EItemGenerationCategory::Head"
            or group.values.get("PlayerRank", "") != rank or group.values.get("Diff", "") != diff):
        return None
    possible = group.children.get("PossibleItems")
    if possible is None or possible.attrs or possible.values or set(possible.children) != {row}:
        return None
    node = possible.children[row]
    chance = parse_number(node.values.get("Chance"), math.nan)
    if (node.attrs or node.children or "Weight" in node.values or "ItemGeneratorPrototypeSID" in node.values
            or node.values.get("ItemPrototypeSID") != item or not math.isfinite(chance) or not 0 <= chance <= 1
            or not _item_ok(gd, item) or gd.item_category(item) != "armor"):
        return None
    return {row: chance}


def catalog(gd):
    children = {}
    for sid, node in gd.obj.children.items():
        children.setdefault(node.attr_dict().get("refkey"), []).append(sid)
    objects = {obj for obj in OBJECTS if _object_ok(gd, obj, children)}
    pools = {key: _pool(gd, *key) for key in POOLS}
    pools.update({key: _helmet_pool(gd, *key) for key in HELMET_POOLS})
    return {k: pools[c.source, c.slot][c.row] for k, c in CONTROLS.items()
            if c.obj in objects and pools[c.source, c.slot] is not None}


def available(gd):
    return getattr(gd, "npc_equipment_editor", {}) if gd is not None else {}


def quality_weight(base, factor, rank):
    """Preserve fractional baselines without changing established integer tiers."""
    if factor == 1 or rank == 0:
        return base
    value = base * factor ** rank
    return max(1, round(value)) if float(base).is_integer() else value


def _fmt(value):
    return f"{value:.12g}"


def clone_sid(mod_name, obj, source):
    return "S2Tweaker_Equipment_" + hashlib.sha256((mod_name + "\0" + obj + "\0" + source).encode()).hexdigest()[:24]


def _clone(node):
    return {**node.values, **({"__attrs__": node.attrs} if node.attrs else {}),
            **{key: _clone(child) for key, child in node.children.items()}}


def _merge(target, patch):
    for key, value in patch.items():
        if isinstance(value, dict):
            _merge(target.setdefault(key, {}), value)
        else:
            target[key] = value


def apply(gd, settings, generators):
    """After all global loot patches: append private branches and return Obj links."""
    selected = list(changes(settings.npc_equipment_overrides))
    if not selected:
        return {}
    data = available(gd)
    by_object = {}
    for c, value in selected:
        if c.key in data:
            by_object.setdefault(c.obj, {}).setdefault(c.source, []).append((c, value))
    original_patches = deepcopy(generators)
    objects = {}
    for obj, edits in by_object.items():
        built = {}

        def branch(source):
            if source in built:
                return built[source]
            built[source] = None
            cfg = _clone(gd.itemgenerators.children[source])
            _merge(cfg, original_patches.get(source, {}))
            changed = False
            touched = set()
            for c, value in edits.get(source, ()):
                row = cfg["ItemGenerator"][c.slot]["PossibleItems"][c.row]
                old = parse_number(row[c.kind], math.nan)
                new = old * value / 100
                if not math.isfinite(new) or new < 0:
                    raise ValueError("NPC equipment has an invalid effective weight.")
                if c.kind == "Chance":
                    new = min(1, new)
                if not math.isclose(new, old, rel_tol=1e-12, abs_tol=0):
                    row[c.kind] = _fmt(new)
                    changed = True
                if c.kind == "Weight":
                    touched.add(c.slot)
            for slot in touched:
                weights = [parse_number(row.get("Weight"), math.nan)
                           for row in cfg["ItemGenerator"][slot]["PossibleItems"].values() if isinstance(row, dict)]
                if not weights or any(not math.isfinite(w) or w < 0 for w in weights) or sum(weights) <= 0:
                    raise ValueError(f"{obj} / {slot}: keep at least one equipment choice above 0%.")
            for slot, row, target, _rank, _diff in LINKS.get(source, ()):
                name = branch(target)
                if name:
                    cfg["ItemGenerator"][slot]["PossibleItems"][row]["ItemGeneratorPrototypeSID"] = name
                    changed = True
            if not changed:
                return None
            name = clone_sid(settings.mod_name, obj, source)
            if name in gd.itemgenerators.children or name in generators:
                raise ValueError("Generated NPC equipment name already exists.")
            cfg.update(__new__=True, SID=name)
            generators[name] = cfg
            built[source] = name
            return name

        name = branch(OBJECTS[obj][2])
        if name:
            objects[obj] = {"ItemGeneratorPrototypeSID": name}
    return objects


def footprint(gd, key):
    if key not in available(gd):
        return set()
    c = CONTROLS[key]
    # Cloning copies the entire source branch, so all its leaves can conflict.
    sources = {src for src, _rs, _ds in _routes(OBJECTS[c.obj][2])}
    return {(c.obj, "ItemGeneratorPrototypeSID")} | {
        (source, field) for source in sources for node in gd.itemgenerators.children[source].walk()
        for field in node.values}


def probe(key):
    return {"npc_equipment_overrides": {key: 200}} if key in CONTROLS else None


def summarize(values):
    return [f"{c.label}: {value:g}% (experimental)" for c, value in changes(values)]
