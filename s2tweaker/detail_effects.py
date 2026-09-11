"""Bounded special-artifact and medical effects, with native SID ownership checks.

Medical SIDs are retained so the game's Master difficulty modifiers still match.
Only ongoing buff durations are exposed; use/reload/movement animations are not.
"""
from __future__ import annotations

import hashlib
import math
from .cfgparse import parse_number
from .artifact_extensions import _literal, _put

# (item, parameter): native effect identities and expected native type. No values.
MEDICINE = {
    ("Bandage", "healing"): (("BandageHealing2", "Health"),),
    ("Bandage", "bleeding"): (("BandageBleeding4", "Bleeding"),),
    ("Medkit", "healing"): (("MedkitHealing3", "Health"),),
    ("Medkit", "bleeding"): (("MedkitBleeding2", "Bleeding"),),
    ("ArmyMedkit", "healing"): (("ArmyMedkitHealing4", "Health"),),
    ("ArmyMedkit", "bleeding"): (("ArmyMedkitBleeding3", "Bleeding"),),
    ("EcoMedkit", "healing"): (("EcoMedkitHealing4", "Health"),),
    ("EcoMedkit", "bleeding"): (("EcoMedkitBleeding2", "Bleeding"),),
    ("EcoMedkit", "radiation"): (("EcoMedkitAntirad3", "Radiation"),),
    ("AntiRad", "radiation"): (("Antirad4", "Radiation"),),
    ("Hercules", "strength"): (("HerculesWeight", "AdditionalInventoryWeight"), ("HerculesWeight_Penalty", "PenaltyLessWeight")),
    ("Cinnamon", "strength"): (("CinnamonDegenBleeding", "DegenBleeding"),),
    ("PSYBlocker", "strength"): (("PSYBlockerIncreaseRegen", "DegenPsyPoints"),),
}
BUFFS = ("Hercules", "Cinnamon", "PSYBlocker")
NUT = {"bleeding": ("DegenBleeding10", "DegenBleeding"),
       "healing_drawback": ("RegenHealthModifier", "RegenHealthModifier")}
WATER = (("WeirdWaterCarryWeightEffect", "AdditionalInventoryWeight"),
         ("WeirdWaterPenaltyLessWeightEffect", "PenaltyLessWeight"))
COMPOSITE = "WeirdWaterWeightChangeCompositeEffect"
MASTER_HEALS = {"BandageHealing2", "MedkitHealing3", "ArmyMedkitHealing4"}


def controls(Control, note):
    labels = {"healing": "Healing amount", "bleeding": "Bleeding removal", "radiation": "Radiation removal", "strength": "Buff strength"}
    tip = ("100% inherits existing global effects; this extra factor multiplies the original effect and applicable globals once. "
           "Only this supported item's native effects change. Difficulty modifiers and native effect identities remain. "
           "Medical delivery time and use animations stay unchanged.")
    for item, param in MEDICINE:
        extra = " Carry and penalty-free capacity use one local factor; their existing global carry settings still apply separately." if item == "Hercules" else ""
        yield Control("medicine", item, param, labels[param] + " (%)", 0, 400, 100, 0, tip + extra + note)
    for item in BUFFS:
        yield Control("medicine", item, "duration", "Ongoing buff duration (%)", 10, 1000, 100, 0,
                      "100% inherits global consumable duration; this extra factor changes only the existing ongoing buff. "
                      "It does not stretch healing delivery, item-use animations or Hercules field-repair effects." + note)
    for param, label in (("bleeding", "Bleeding protection"), ("healing_drawback", "Healing drawback")):
        yield Control("special", "AArtifactWeirdNut", param, label + " (%)", 0, 400, 100, 0,
                      "Scales this equipped effect's native magnitude independently. 100% unchanged, 0 removes the magnitude. "
                      "The healing modifier is not a measured final medkit-speed percentage. Unequip before changing the mod; "
                      "re-equip afterward. Saved effect transitions need a game test." + note)
    yield Control("special", "AArtifactWeirdWater", "strength", "Paired carry bonus (%)", 0, 400, 100, 0,
                  "Scales capacity and penalty-free weight together. The existing global carry bonus still affects capacity separately. "
                  "Native units remain percentages, not kilograms. Re-equip after changing the mod; saved effects may need to expire." + note)
    yield Control("special", "AArtifactWeirdWater", "minimum", "Minimum intoxication (-1 inherit)", 0, 100, -1, 2,
                  "An explicit value sets the existing minimum-drunkness field. Zero is not a guarantee of no intoxication, "
                  "because the artifact can have additional scripted behavior. Separate from its carry effects." + note)


def _chain_ok(gd, root, sid):
    seen = set()
    while sid:
        if sid in seen or sid not in root.children:
            return False
        seen.add(sid)
        node = root.children[sid]
        attrs = node.attr_dict()
        filename = "ItemPrototypes.cfg" if root is gd.items else "EffectPrototypes.cfg"
        if attrs.get("refurl") not in (None, "", filename, "../" + filename):
            return False
        sid = attrs.get("refkey")
    return True


def _item(gd, sid, category):
    node = gd.items.children.get(sid)
    if node is None or not _chain_ok(gd, gd.items, sid):
        return None
    if any(child.attr_dict().get("refkey") == sid for child in gd.items.children.values()):
        return None
    if gd.resolve(gd.items, sid, "Type") != "EItemType::" + category:
        return None
    for flag in ("IsQuestItem", "IsQuestItemPrototype"):
        if (gd.resolve(gd.items, sid, flag) or "false").lower() != "false":
            return None
    if category == "Consumable" and any(gd.resolve(gd.items, sid, field) != "true" for field in ("Usable", "ConsumeOnUse")):
        return None
    for parent in gd._resolve_chain(gd.items, sid):
        if any("alternative" in key.lower() and "effect" in key.lower() for key in (*parent.children, *parent.values)):
            return None
    listing = node.children.get("EffectPrototypeSIDs")
    if (listing is None or listing.attrs or listing.children or not listing.values
            or any(not key.startswith("[") or not key[1:-1].isdigit() for key in listing.values)):
        return None
    return listing.values


def _effect(gd, sid, typ, permanent):
    node = gd.effects.children.get(sid)
    if node is None or not _chain_ok(gd, gd.effects, sid):
        return False
    if (gd.resolve(gd.effects, sid, "Type") != "EEffectType::" + typ
            or gd.resolve(gd.effects, sid, "bIsPermanent") != permanent
            or (gd.resolve(gd.effects, sid, "ValueProviderSID") or "").lower() != "empty"
            or (gd.resolve(gd.effects, sid, "EffectCurvePath") or "").strip()):
        return False
    return all(math.isfinite(parse_number(gd.resolve(gd.effects, sid, leaf), math.nan)) for leaf in ("ValueMin", "ValueMax"))


def catalog(gd, specs):
    result = {}
    ids = {sid for pairs in MEDICINE.values() for sid, _typ in pairs}
    owners = {sid: set() for sid in ids}
    effect_users = {sid: set() for sid in ids}
    for item, root in gd.items.children.items():
        for node in root.walk():
            for leaf, value in node.values.items():
                if value in owners and leaf not in ("SID", "LocalizationSID"):
                    owners[value].add(item)
    for source, root in gd.effects.children.items():
        parent = root.attr_dict().get("refkey")
        if parent in effect_users:
            effect_users[parent].add(source)
        for node in root.walk():
            for leaf, value in node.values.items():
                if value in effect_users and leaf not in ("SID", "LocalizationSID"):
                    effect_users[value].add(source)
    for c in specs.values():
        targets = []
        if c.group == "medicine":
            pairs = MEDICINE.get((c.target, "strength" if c.param == "duration" else c.param), ())
            listing = _item(gd, c.target, "Consumable")
            if not listing or not pairs:
                continue
            valid = all(sid in listing.values() and owners[sid] == {c.target}
                        and effect_users[sid] <= ({"MasterEffectModifier"} if sid in MASTER_HEALS else set())
                        and _effect(gd, sid, typ, "false") for sid, typ in pairs)
            leaves = ("Duration",) if c.param == "duration" else ("ValueMin", "ValueMax")
            if c.param == "duration":
                valid &= all(parse_number(gd.resolve(gd.effects, sid, "Duration"), -1) >= 10 for sid, _ in pairs)
            if valid:
                targets = [("EffectPrototypes", sid, leaf, gd.resolve(gd.effects, sid, leaf), None)
                           for sid, _typ in pairs for leaf in leaves]
        elif c.group == "special":
            listing = _item(gd, c.target, "Artifact")
            if not listing:
                continue
            if c.target == "AArtifactWeirdNut":
                sid, typ = NUT[c.param]
                if list(listing.values()).count(sid) == 1 and _effect(gd, sid, typ, "true"):
                    targets = [("EffectPrototypes", sid, leaf, gd.resolve(gd.effects, sid, leaf), None) for leaf in ("ValueMin", "ValueMax")]
            elif c.param == "minimum":
                raw = gd.resolve(gd.items, c.target, "MinimalDrunkenness")
                if math.isfinite(parse_number(raw, math.nan)):
                    targets = [("ItemPrototypes", c.target, "MinimalDrunkenness", raw, None)]
            else:
                comp = gd.effects.children.get(COMPOSITE)
                kids = comp.children.get("ApplyExtraEffectPrototypeSIDs") if comp else None
                if (list(listing.values()).count(COMPOSITE) == 1 and kids and not kids.attrs and not kids.children
                        and set(kids.values.values()) == {sid for sid, _ in WATER} and len(kids.values) == 2
                        and _effect(gd, COMPOSITE, "Composite", "false")
                        and all(_effect(gd, sid, typ, "true") for sid, typ in WATER)):
                    targets = [("EffectPrototypes", sid, leaf, gd.resolve(gd.effects, sid, leaf), None) for sid, _ in WATER for leaf in ("ValueMin", "ValueMax")]
        if targets:
            result[c.key] = targets
    return result


def _global(settings, sid, leaf):
    if leaf == "Duration":
        return settings.consumable_duration_factor
    if sid in ("HerculesWeight", "WeirdWaterCarryWeightEffect"):
        return settings.armor_carry_bonus_factor
    if sid in ("HerculesWeight_Penalty", "WeirdWaterPenaltyLessWeightEffect") or sid in {pair[0] for pair in NUT.values()}:
        return 1
    healing = {pairs[0][0] for (_item, param), pairs in MEDICINE.items() if param == "healing"}
    return settings.consumable_factor * (settings.healing_factor if sid in healing else 1)


def clone_sid(mod_name, item, effect):
    return "S2Tweaker_Detail_" + hashlib.sha256((mod_name + "\0" + item + "\0" + effect).encode()).hexdigest()[:24]


def special_changes(gd, settings, c, value, targets):
    effects, items = {}, {}
    if c.param == "minimum":
        _put(items, c.target, "MinimalDrunkenness", _literal(value, targets[0][3]), targets[0][3])
        return effects, items
    native_ids = {row[1] for row in targets}
    mapping = {sid: clone_sid(settings.mod_name, c.target, sid) for sid in native_ids}
    if c.target == "AArtifactWeirdWater":
        mapping[COMPOSITE] = clone_sid(settings.mod_name, c.target, COMPOSITE)
    existing = set(gd.effects.children) | {node.values.get("SID") for node in gd.effects.children.values()}
    if existing & set(mapping.values()):
        raise ValueError("Generated detail-effect identity already exists in loaded game data.")
    for sid, name in mapping.items():
        cfg = {"__new__": True, "__attrs__": "refkey=" + sid, "SID": name}
        localization = gd.resolve(gd.effects, sid, "LocalizationSID")
        if localization is not None:
            cfg["LocalizationSID"] = localization
        effects[name] = cfg
    for _file, sid, leaf, raw, _row in targets:
        factor = _global(settings, sid, leaf) * value / 100
        effects[mapping[sid]][leaf] = _literal(parse_number(raw) * factor, raw)
    if COMPOSITE in mapping:
        kids = gd.effects.children[COMPOSITE].children["ApplyExtraEffectPrototypeSIDs"].values
        effects[mapping[COMPOSITE]]["ApplyExtraEffectPrototypeSIDs"] = {index: mapping[sid] for index, sid in kids.items()}
    listing = gd.items.children[c.target].children["EffectPrototypeSIDs"].values
    for index, sid in listing.items():
        if sid in mapping:
            items.setdefault(c.target, {}).setdefault("EffectPrototypeSIDs", {})[index] = mapping[sid]
    return effects, items


def apply(gd, settings, source, patches, selected, data):
    for c, value in selected:
        targets = data.get(c.key, ())
        if not targets:
            continue
        if c.group == "medicine" and source == "EffectPrototypes":
            for _file, sid, leaf, raw, _row in targets:
                result = parse_number(raw) * _global(settings, sid, leaf) * value / 100
                _put(patches, sid, leaf, _literal(result, raw), raw)
        elif c.group == "special" and source in ("EffectPrototypes", "ItemPrototypes"):
            effects, items = special_changes(gd, settings, c, value, targets)
            from .npc_equipment import _merge
            _merge(patches, effects if source == "EffectPrototypes" else items)


def footprint(gd, c, targets):
    result = {(sid, path.rsplit(".", 1)[-1]) for _file, sid, path, _raw, _row in targets}
    if c.group == "special":
        from .modscan import EFFECT_LIST_LEAF
        result.update({(c.target, EFFECT_LIST_LEAF), (c.target, "EffectPrototypeSIDs")})
        if c.param == "minimum":
            return {(c.target, "MinimalDrunkenness")}
        for sid in {row[1] for row in targets} | ({COMPOSITE} if c.target == "AArtifactWeirdWater" else set()):
            node = gd.effects.children[sid]
            result.update((sid, leaf) for sub in node.walk() for leaf in sub.values)
    return result
