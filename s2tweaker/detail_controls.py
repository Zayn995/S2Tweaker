"""Optional data-only detail settings; no animation or runtime injection changes.

Scope identities and UI bounds are fixed; numeric baselines come from GameData.
See SLIDER_AUDIT_1_40_1.md and the linked bounded source inventories.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import math

from .cfgparse import parse_number
from .artifact_extensions import _literal, _put
from .npc_equipment import _clone, _merge
from . import detail_effects
from .detail_scope import WEAPON_ITEMS

PREFIX = "detail_edit:"
GROUPS = {"special": "Special artifacts", "medicine": "Medicine & buffs",
          "weapon_item": "Weapon item properties", "weather": "Weather senses",
          "camp": "Camp activities", "grenade": "NPC grenade budgets",
          "upgrade": "Upgrade bonuses", "scanner": "Passive scanners"}
WEATHERS = ("Clearly", "Cloudy", "Fogy", "Rainy", "LightRainy", "Thundery")
SENSES = {"VisibilityCoef": "Sight penalty", "HearingDistanceCoef": "Hearing penalty",
          "FlairCoef": "Scent penalty"}
CAMPS = ("Bandits", "Corpus", "Duty", "Freedoms", "Mercenaries", "Militaries",
         "Monolit", "Neutrals", "Noon", "Scientists", "Spark", "Varta")
ACTIVITIES = {"Guitar": "Guitar", "Anecdote": "Jokes", "Dialog": "Conversations",
              "Smoke": "Smoking", "Sleep": "Sleeping", "Eat": "Eating",
              "Rest": "Resting", "Drink": "Drinking"}
RANKS = ("Newbie", "Experienced", "Veteran", "Master")
# No aim, movement, reload, draw/holster or animation recovery parameters.
UPGRADES = {"BaseDamage": "Damage", "ArmorPiercing": "Armor penetration",
            "CoverPiercing": "Cover penetration", "AmmoCapacity": "Magazine capacity",
            "Dispersion": "Dispersion reduction", "DispersionMaxRadiusExtension": "Maximum dispersion reduction",
            "DispersionPerIterationRadiusExtension": "Dispersion growth reduction", "Accuracy": "Accuracy",
            "DispersionAimModifier": "Aimed dispersion reduction", "DispersionOffsetAimModifier": "Aim offset reduction",
            "ProtectionStrike": "Physical protection", "ProtectionBurn": "Fire protection",
            "ProtectionShock": "Electric protection", "ProtectionChemical": "Chemical protection",
            "ProtectionPSY": "Psy protection", "ProtectionRadiation": "Radiation protection"}
ITEM_FIELDS = {"Weight": ("Weight (kg)", 0, 100, 3), "Cost": ("Base price", 0, 1000000, 0),
               "ItemGridWidth": ("Inventory width", 1, 20, 0), "ItemGridHeight": ("Inventory height", 1, 20, 0)}
NOTE = " Not play-tested yet. No animation assets or runtime injector are changed."


@dataclass(frozen=True)
class Control:
    group: str
    target: str
    param: str
    title: str
    minimum: float
    maximum: float
    default: float
    decimals: int
    help: str
    tab: str = "World"

    @property
    def key(self):
        return f"{PREFIX}{self.group}:{self.target}:{self.param}"

    @property
    def label(self):
        return f"{GROUPS[self.group]} / {self.target} / {self.title}"

    @property
    def lo(self):
        return min(self.minimum, self.default)

    def validate(self, value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{self.title}: enter a finite number.")
        if value != self.default and not self.minimum <= value <= self.maximum:
            raise ValueError(f"{self.title}: enter {self.minimum:g}–{self.maximum:g}, or {self.default:g} to inherit.")
        if self.decimals == 0 and value != int(value):
            raise ValueError(f"{self.title}: enter a whole number.")
        return round(float(value), self.decimals)


def _controls():
    yield from detail_effects.controls(Control, NOTE)
    for sid in WEAPON_ITEMS:
        for leaf, (label, lo, hi, decimals) in ITEM_FIELDS.items():
            yield Control("weapon_item", sid, leaf, label + " (-1 inherit)", lo, hi, -1, decimals,
                          "An explicit item value replaces this weapon's global weight/grid result. It affects copies in inventories, "
                          "NPC equipment, vendors and world spawns. Base price still combines with trader, difficulty and reputation factors. "
                          "Only available ordinary and collectible weapon definitions are supported; protected quest/guard/story variants are excluded." + NOTE, "Weapons")
    for weather in WEATHERS:
        for field, label in SENSES.items():
            yield Control("weather", weather, field, label + " (%)", 0, 400, 100, 0,
                          "100% inherits bad-weather stealth; this detail factor multiplies that global factor once. "
                          "0 removes this weather penalty. Native clear-weather coefficients stay unchanged. "
                          "Shared AI coefficients can also affect mutants and story NPCs; this does not change screen brightness." + NOTE, "NPCs & AI")
    for activity, label in ACTIVITIES.items():
        yield Control("camp", "Ordinary faction camps", activity, label + " need (%)", 0, 400, 100, 0,
                      "100% inherits camp life; multiplies its need accumulation rate for this activity in supported ordinary faction presets. "
                      "0 stops this source of need accumulation, not a running action. Existing action spots and threats still matter. "
                      "No activity is added and no animation is altered. Explicit quest/guard/mutant/zombie presets are excluded; "
                      "ordinary presets may also be used in missions." + NOTE, "NPCs & AI")
    for group in ("Bandits", "Army", "Humanoid"):
        for rank in RANKS:
            yield Control("grenade", group, rank, rank + " budget (%)", 0, 400, 100, 0,
                          "100% inherits the global NPC grenade factor; detail multiplies it before integer rounding. "
                          "Humanoid is a native fallback group, not an individual faction. Zero budgets and boss sentinels stay unchanged. "
                          "This changes an allowed budget, not throw frequency or animation." + NOTE, "NPCs & AI")
    for sid, label in (("PlayerDetector", "Anomaly warning range"), ("PlayerSearchpointDetector", "Search-point range")):
        yield Control("scanner", sid, "DetectorRadius", label + " (cm; -1 inherit)", 1, 100000, -1, 0,
                      "An explicit radius replaces this scanner's global detector range result. The quest collar scanner is excluded. "
                      "Native anomaly exclusions remain; this does not add detection of excluded anomaly types." + NOTE)
    for typ, label in UPGRADES.items():
        yield Control("upgrade", "Technician bonuses", typ, label + " (%; -1 inherit)", 0, 400, -1, 0,
                      "-1 inherits the existing upgrade family. An explicit percentage replaces that family for this positive bonus type only. "
                      "Penalties remain. Effects shared by other upgrades or attachments are also affected. "
                      "Mixed composite descriptions may retain their original number; use the export preview for exact values." + NOTE, "Upgrades")


CONTROLS = {c.key: c for c in _controls()}


def control_specs():
    return ((c.key, c.label, c.lo, c.maximum, c.default, c.help) for c in CONTROLS.values())


def changes(values):
    if not isinstance(values, dict):
        raise ValueError("Detail settings must be a mapping.")
    for key, value in values.items():
        c = CONTROLS.get(key)
        if c is not None:
            value = c.validate(value)
            if value != c.default:
                yield c, value


def collect(sliders):
    return {key: c.validate(sliders[key].get()) for key, c in CONTROLS.items()
            if key in sliders and sliders[key].get() != c.default}


def _finite(raw, minimum=0):
    value = parse_number(raw, math.nan)
    return math.isfinite(value) and value >= minimum


def _rows(root, path):
    node = root
    for part in path.split("."):
        node = node.children.get(part) if node is not None else None
    return node.children.items() if node is not None else ()


def catalog(gd):
    """Identity-checked live leaves; no speculative indices or game numbers."""
    data = {}
    children = {}
    for sid, node in gd.needspresets.children.items():
        children.setdefault(node.attr_dict().get("refkey"), []).append(node)
    for c in CONTROLS.values():
        targets = []
        if c.group == "weather":
            for index, node in _rows(gd.aiglobals, "AISettings.WeatherSettings"):
                raw = node.values.get(c.param)
                if (node.values.get("WeatherSID") == c.target and not node.attrs
                        and not node.children and _finite(raw) and parse_number(raw) <= 1):
                    targets.append(("AIGlobals", "AISettings", f"WeatherSettings.{index}.{c.param}", raw, _clone(node)))
        elif c.group == "grenade":
            path = f"ThrowGrenadeSettings.AvailableGrenadesPerFaction.{c.target}.{c.param}"
            raw = gd.resolve(gd.aiglobals, "AISettings", path)
            if _finite(raw) and parse_number(raw).is_integer():
                targets.append(("AIGlobals", "AISettings", path, raw, None))
        elif c.group == "scanner":
            for sid, node in gd.passivedetectors.children.items():
                expected = "EPassiveDetectorType::Anomaly" if c.target == "PlayerDetector" else "EPassiveDetectorType::Searchpoint"
                raw = gd.resolve(gd.passivedetectors, sid, c.param)
                if (node.values.get("SID") == c.target and _finite(raw, .000001)
                        and node.values.get("Type") == expected):
                    targets.append(("PassiveDetectorPrototypes", sid, c.param, raw, None))
        elif c.group == "camp":
            for prefix in CAMPS:
                sid = prefix + "NeedsPreset"
                for index, node in _rows(gd.needspresets, sid + ".Needs"):
                    if (node.values.get("NeedType") != "EContextualActionNeeds::" + c.param
                            or node.attrs or node.children):
                        continue
                    leaves = ("IncreaseRateMin", "IncreaseRateMax")
                    if not all(_finite(node.values.get(k)) for k in leaves):
                        continue
                    # A direct child's explicit row shields all of its descendants.
                    if any(child.get(f"Needs.{index}.NeedType") != node.values["NeedType"]
                           or any(child.get(f"Needs.{index}.{leaf}") is None for leaf in leaves)
                           for child in children.get(sid, ())):
                        continue
                    for leaf in leaves:
                        targets.append(("NPCNeedsPresetPrototypes", sid, f"Needs.{index}.{leaf}", node.values[leaf], _clone(node)))
        elif c.group == "upgrade":
            refs = {value.strip() for node in gd.upgrades.children.values()
                    for value in (node.children.get("EffectPrototypeSIDs").values.values()
                                  if node.children.get("EffectPrototypeSIDs") else ())}
            for sid in sorted(refs):
                if gd.resolve(gd.effects, sid, "Type") != "EEffectType::" + c.param:
                    continue
                for leaf in ("ValueMin", "ValueMax"):
                    raw = gd.resolve(gd.effects, sid, leaf)
                    number = parse_number(raw, math.nan)
                    if math.isfinite(number) and (number < 0 if c.param.startswith("Dispersion") else number > 0):
                        targets.append(("EffectPrototypes", sid, leaf, raw, None))
        if targets:
            data[c.key] = targets
    data.update(detail_effects.catalog(gd, CONTROLS))
    data.update(_weapon_catalog(gd))
    return data


def _weapon_catalog(gd):
    data = {}
    trees = [gd.items] + [entry["items"] for entry in gd.dlc_editions.values() if "items" in entry]
    children = {}
    for tree in trees:
        for node in tree.children.values():
            children.setdefault(node.attr_dict().get("refkey"), []).append(node)
    for sid, (edition, setup, category, expected_chain) in WEAPON_ITEMS.items():
        tree = gd.dlc_editions.get(edition, {}).get("items") if edition else gd.items
        if tree is None or sid not in tree.children:
            continue
        chain = gd.dlc_item_chain(edition, sid) if edition else gd._resolve_chain(tree, sid)
        if tuple(node.name for node in chain) != expected_chain:
            continue
        get = lambda path: gd._chain_get(chain, path)
        if get("Type") != "EItemType::Weapon" or get("GeneralWeaponSetup") != setup:
            continue
        actual_cat = gd.dlc_weapon_category(edition, setup) if edition else gd.weapon_category(setup)
        if actual_cat != category:
            continue
        if any((get(flag) or "false").lower() != "false" for flag in
               ("IsQuestItem", "IsQuestItemPrototype", "Invisible", "InvisibleInPlayerInventory", "DestroyOnPickup")):
            continue
        for leaf in ITEM_FIELDS:
            raw = tree.children[sid].values.get(leaf)
            if not _finite(raw, 1 if leaf.startswith("ItemGrid") else 0):
                continue
            if leaf.startswith("ItemGrid") and not parse_number(raw).is_integer():
                continue
            # Explicit child values shield their descendants, including protected variants.
            if any(leaf not in child.values for child in children.get(sid, ())):
                continue
            key = f"{PREFIX}weapon_item:{sid}:{leaf}"
            data[key] = [("ItemPrototypes", sid, leaf, raw, None)]
    return data


def apply_weapon_items(gd, settings, patches, editions):
    selected = [(c, value) for c, value in changes(settings.detail_overrides) if c.group == "weapon_item"]
    if not selected:
        return
    data = available(gd)
    for c, value in selected:
        targets = data.get(c.key)
        if not targets:
            continue
        edition = WEAPON_ITEMS[c.target][0]
        target = editions.setdefault(edition, {}) if edition else patches
        raw = targets[0][3]
        _put(target, c.target, c.param, _literal(value, raw), raw)
        if edition and not target:
            editions.pop(edition, None)


def available(gd):
    return getattr(gd, "detail_editor", {}) if gd is not None else {}


def _get(tree, parts):
    for part in parts:
        tree = tree.get(part, {})
    return tree


def _drop(tree, parts):
    parents = []
    for part in parts[:-1]:
        if part not in tree:
            return
        parents.append((tree, part))
        tree = tree[part]
    tree.pop(parts[-1], None)
    for parent, part in reversed(parents):
        if not parent[part]:
            del parent[part]


def _same(a, b):
    if isinstance(a, dict) or isinstance(b, dict):
        return isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    return a == b or (_finite_number(a) and _finite_number(b)
                     and math.isclose(parse_number(a), parse_number(b), rel_tol=1e-9, abs_tol=1e-9))


def _finite_number(value):
    return isinstance(value, str) and math.isfinite(parse_number(value, math.nan))


def _write(patches, sid, path, value, raw, row):
    if row is None:
        _put(patches, sid, path, value, raw)
        return
    parts = (sid, *path.split("."))
    full = deepcopy(row)
    _merge(full, _get(patches, parts[:-1]))
    full[parts[-1]] = value
    if _same(full, row):
        _drop(patches, parts[:-1])
    else:
        parent = patches
        for part in parts[:-2]:
            parent = parent.setdefault(part, {})
        parent[parts[-2]] = full


def apply(gd, settings, source, patches):
    selected = list(changes(settings.detail_overrides))
    if not selected:
        return
    data = available(gd)
    detail_effects.apply(gd, settings, source, patches, selected, data)
    for c, value in selected:
        for file, sid, path, raw, row in data.get(c.key, ()):
            if file != source or c.group == "upgrade":
                continue  # Upgrades compose inside the original builder.
            base = parse_number(raw)
            if c.group == "weather":
                result = max(.05, min(1, 1 - (1 - base) * settings.weather_stealth_factor * value / 100))
            elif c.group == "camp":
                global_factor = settings.camp_life_factor if settings.camp_life_factor > 0 else 1
                result = base * global_factor * value / 100
            elif c.group == "grenade":
                result = max(0, round(base * settings.npc_grenade_factor * value / 100))
            elif c.group == "scanner":
                result = value
            else:
                continue
            _write(patches, sid, path, _literal(result, raw), raw, row)


def upgrade_factor(settings, typ, inherited):
    key = f"{PREFIX}upgrade:Technician bonuses:{typ}"
    c = CONTROLS.get(key)
    if c is None:
        return inherited
    value = c.validate(settings.detail_overrides.get(key, c.default))
    return inherited if value == c.default else value / 100


def probe(key):
    c = CONTROLS.get(key)
    return {"detail_overrides": {key: 50 if c.default == 100 else c.minimum}} if c else None


def footprint(gd, key):
    c = CONTROLS.get(key)
    if c and c.group in ("special", "medicine") and key in available(gd):
        return detail_effects.footprint(gd, c, available(gd)[key])
    result = set()
    for _file, sid, path, _raw, row in available(gd).get(key, ()):
        result.add((sid, path.rsplit(".", 1)[-1]))
        if row:
            result.update((sid, leaf) for leaf in row if not leaf.startswith("__"))
    if c and c.group == "upgrade":
        affected = {sid for sid, _leaf in result}
        for sid, node in gd.effects.children.items():
            kids = node.children.get("ApplyExtraEffectPrototypeSIDs")
            if kids and affected.intersection(kids.values.values()):
                result.update((sid, leaf) for leaf in ("ValueMin", "ValueMax"))
    return result


def baseline(gd, key):
    values = sorted({str(row[3]) for row in available(gd).get(key, ())})
    return ", ".join(values[:8]) + (" …" if len(values) > 8 else "")


def summarize(values):
    return [f"{c.label}: {value:g} (experimental)" for c, value in changes(values)]
