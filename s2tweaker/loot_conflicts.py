"""Position-sensitive conflict metadata for ItemGenerator loot lists.

The normal mod scan compares a prototype and a leaf name. That loses the
relationship between an array position and its item: moving a trophy from
[0] to [3] can leave every value in the same value set. A vanilla-based
Chance patch still writes to [0], however. These scan-only markers connect
such structural changes to controls that address existing array positions.
They are never written to a generated game config and do not merge mods.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .cfgparse import CfgStruct


LAYOUT_LEAF = "@loot-layout"
WEIGHT_LEAF = "@loot-weight"
_POSITION = re.compile(r"^\[\d+\](?:#\d+)?$")
_IDENTITY_KEYS = frozenset({"ItemPrototypeSID", "ItemGeneratorPrototypeSID"})
_VALUE_KEYS = frozenset({
    "Chance", "Weight", "MinCount", "MaxCount", "MinDurability",
    "MaxDurability", "AmmoMinCount", "AmmoMaxCount",
})
_ROW_KEYS = _IDENTITY_KEYS | _VALUE_KEYS
Path = tuple[str, ...]


def _normal(raw: str) -> str:
    value = raw.strip().rstrip(";").strip()
    suffix = "%" if value.endswith("%") else ""
    core = value[:-1].strip() if suffix else value
    try:
        return repr(float(core.rstrip("fF").rstrip("."))) + suffix
    except ValueError:
        return value.lower()


@dataclass
class LootLayout:
    rows: dict[Path, dict[str, str]] = field(default_factory=dict)
    categories: dict[Path, str] = field(default_factory=dict)
    cleared: set[Path] = field(default_factory=set)


def _layout(top: CfgStruct) -> LootLayout:
    out = LootLayout()
    if "ItemGenerator" in top.values:
        out.cleared.add(("ItemGenerator",))
    generators = top.children.get("ItemGenerator")
    if generators is None:
        return out
    for group_name, group in generators.children.items():
        prefix = ("ItemGenerator", group_name)
        if "Category" in group.values:
            out.categories[prefix] = _normal(group.values["Category"])
        if "PossibleItems" in group.values:
            out.cleared.add(prefix + ("PossibleItems",))
        items = group.children.get("PossibleItems")
        if items is None:
            continue
        for item_name, item in items.children.items():
            path = prefix + ("PossibleItems", item_name)
            out.rows[path] = {key: _normal(value)
                              for key, value in item.values.items()
                              if key in _ROW_KEYS}
    return out


def build_loot_index(root: CfgStruct) -> dict[str, LootLayout]:
    """Record current item identities and values at their actual positions."""
    return {name.split("#", 1)[0]: _layout(top)
            for name, top in root.children.items()
            if "ItemGenerator" in top.children or "ItemGenerator" in top.values}


def _names(key: str, top: CfgStruct) -> tuple[str, set[str], str]:
    own = key.split("#", 1)[0]
    ref = top.attr_dict().get("refkey", "").strip()
    names = {own}
    if ref and not _POSITION.fullmatch(ref):
        names.add(ref)
    return own, names, ref


def layout_dependencies(root: CfgStruct) -> set[tuple[str, str]]:
    """Add dependencies only for patches addressing existing array positions.

    Named sibling groups used by new optional pools do not depend on a
    vanilla list index, so an unrelated list reorder does not mark them.
    """
    pairs: set[tuple[str, str]] = set()
    for key, top in root.children.items():
        layout = _layout(top)
        positional = any(
            _POSITION.fullmatch(path[1]) and _POSITION.fullmatch(path[3])
            for path, values in layout.rows.items() if values)
        if positional or layout.cleared:
            _, names, _ = _names(key, top)
            pairs.update((name, LAYOUT_LEAF) for name in names)
    return pairs


def changed_pairs(root: CfgStruct,
                  vanilla: dict[str, LootLayout] | None = None
                  ) -> set[tuple[str, str]]:
    """Detect reordered/replaced item rows and distinct lottery weights.

    Full copies are compared by path, including removed rows. A sparse
    bpatch or a legacy patch under a new name compares only supplied
    fields; omitting unchanged siblings is not treated as deleting them.
    """
    pairs: set[tuple[str, str]] = set()
    for key, top in root.children.items():
        current = _layout(top)
        if "ItemGenerator" not in top.children and not current.cleared:
            continue
        own, names, ref = _names(key, top)
        original = (vanilla.get(own) if vanilla is not None else None)
        full_copy = original is not None and "bpatch" not in top.attr_dict()
        if original is None and vanilla is not None and ref in names:
            original = vanilla.get(ref)
        structural = bool(current.cleared)
        changed: set[str] = set()
        original_groups = ({path[1] for path in original.rows}
                           | {path[1] for path in original.categories}
                           if original is not None else set())

        def named_addition(path: Path) -> bool:
            return (original is not None and not full_copy
                    and not _POSITION.fullmatch(path[1])
                    and path[1] not in original_groups)

        for path, row in current.rows.items():
            if named_addition(path):
                # An independently named bpatch sibling cannot redirect
                # an existing numeric row. The normal leaf comparison
                # still handles direct value overlaps conservatively.
                continue
            old = original.rows.get(path) if original is not None else None
            for leaf, value in row.items():
                if old is not None and old.get(leaf) == value:
                    continue
                if leaf in _IDENTITY_KEYS:
                    structural = True
                else:
                    changed.add(WEIGHT_LEAF if leaf == "Weight" else leaf)
            # An added empty row can still change the list structure.
            if original is not None and old is None:
                structural = True
            if full_copy and old is not None:
                removed = old.keys() - row.keys()
                structural |= bool(removed & _IDENTITY_KEYS)
                changed.update(WEIGHT_LEAF if leaf == "Weight" else leaf
                               for leaf in removed & _VALUE_KEYS)

        if original is not None:
            for path, category in current.categories.items():
                if (not named_addition(path)
                        and original.categories.get(path) != category):
                    structural = True
            if full_copy:
                structural |= bool(original.rows.keys() - current.rows.keys())
                structural |= bool(original.categories.keys()
                                   - current.categories.keys())

        if structural:
            changed.add(LAYOUT_LEAF)
        pairs.update((name, leaf) for name in names for leaf in changed)
    return pairs
