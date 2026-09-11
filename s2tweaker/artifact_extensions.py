"""Individual artifacts and adjacent controls; see ARTIFACT_EDITOR_RESEARCH.md.

Only scope identifiers and UI limits are fixed. Every game baseline is resolved
from the loaded installation. No runtime injector or game process access.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

from .artifact_scope import ARTIFACTS
from .cfgparse import parse_number

PREFIX = "artifact_edit:"
GROUPS = {"item": "Artifacts", "detector": "Detectors", "ball": "Weird Ball",
          "anomaly": "Moving anomalies", "rarity": "Rarity profiles"}
DETECTORS = ("Echo", "Bear", "Gilka", "Veles")
DETECTOR_PATHS = {"reveal": "ShowArtifactRadius", "work": "DetectorWorkRadius",
                  "near": "MinDetectRadius", "sonar": "SonarRadius",
                  "anomaly": "AnomalyDetectionRadius"}
ANOMALIES = ("LightningBallMediumAnomaly", "LightningBallSmallAnomaly",
             "LightningBallBigAnomaly", "FireBallAnomaly")
SPAWNERS = ("UniversalArtifactSpawner", "LesserZoneMagneticShortDistance")
RANKS = ("Newbie", "Experienced", "Veteran", "Master")
TIERS = ("Common", "Uncommon", "Rare", "Epic")
RADIATION = tuple(f"ArtifactAddRadiation{i}" for i in range(1, 5))
EFFECT_LABELS = {
    "ProtectionShock": "Electric protection", "ProtectionBurn": "Fire protection",
    "ProtectionChemicalBurn": "Chemical protection", "ProtectionStrike": "Physical protection",
    "ProtectionRadiation": "Radiation removal", "IncreaseRegenStamina": "Stamina regeneration",
    "AdditionalInventoryWeight": "Carry capacity", "PenaltyLessWeightEffect": "Penalty-free carry weight",
    "DegenBleeding": "Bleeding reduction", "DurabilityIncrease": "Maximum durability (experimental)",
}
EFFECT_TYPES = dict(zip(EFFECT_LABELS, (
    "ProtectionShock", "ProtectionBurn", "ProtectionChemical", "ProtectionStrike",
    "DegenRadiation", "RegenStamina", "AdditionalInventoryWeight", "PenaltyLessWeight",
    "DegenBleeding", "MaxDurability")))
# path: (label, lower bound, upper bound, decimal places)
BALL = {
    "DamageToStaminaCoefficient": ("Damage-to-stamina coefficient", 0, 20, 3),
    "DamageToWeightCoefficient": ("Damage-to-weight coefficient", 0, 1, 4),
    "MinWeight": ("Dynamic minimum weight", 0, 100, 3),
    "MaxWeight": ("Dynamic maximum weight", .001, 100, 3),
    "WeightDecreaseDelay": ("Weight decrease delay", 0, 3600, 3),
    "WeightDecreaseRate": ("Weight decrease rate", .001, 1000, 3),
    "WeightDecreaseAmount": ("Weight decrease amount", 0, 100, 3),
}


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

    @property
    def key(self):
        return f"{PREFIX}{self.group}:{self.target}:{self.param}"

    @property
    def label(self):
        return f"{GROUPS[self.group]} / {self.target} / {self.title}"

    @property
    def lo(self):
        return min(self.default, self.minimum)

    def validate(self, value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{self.title}: enter a finite number.")
        if value != self.default and not self.minimum <= value <= self.maximum:
            raise ValueError(f"{self.title}: enter {self.minimum:g}–{self.maximum:g}, or {self.default:g} to reset.")
        if self.decimals == 0 and value != int(value):
            raise ValueError(f"{self.title}: enter a whole number.")
        return round(float(value), self.decimals)


def effect_family(sid):
    return next((name for name in EFFECT_LABELS if sid.startswith("Artifact" + name)
                 and sid[len("Artifact" + name):].isdigit()), None)


def _controls():
    experimental = " Not play-tested yet."
    absolute = " -1 = Inherit. An explicit value overrides global item changes; difficulty and trader factors still apply."
    for sid, effects in ARTIFACTS.items():
        yield Control("item", sid, "weight", "Weight (kg; -1 = Inherit)", 0, 100, -1, 3, absolute + experimental)
        yield Control("item", sid, "cost", "Base price (-1 = Inherit)", 0, 1000000, -1, 0, absolute + experimental)
        for effect in effects:
            if effect in RADIATION:
                yield Control("item", sid, "radiation", "Radiation (-1 inherit; 0 off; 1–4 tier)", 0, 4, -1, 0,
                              "Uses the game's existing radiation tiers so lead containers and tutorials retain recognized effects. "
                              "Higher tiers need stronger shielding. The global radiation factor still applies. -1 = unchanged." + experimental)
            elif effect_family(effect):
                yield Control("item", sid, effect, EFFECT_LABELS[effect_family(effect)] + " (%)", 0, 400, 100, 0,
                              "Additional multiplier on this item's existing bonus, combined with global artifact strength. "
                              "100% inherits; 0% removes the magnitude. Other artifacts keep their own effects. "
                              "Carry capacity and penalty-free carry weight are separate bonuses. Re-equip after changing the mod." + experimental)
    for sid in DETECTORS:
        for param, path in DETECTOR_PATHS.items():
            title = {"reveal": "Artifact reveal radius", "work": "Search / work radius", "near": "Near detection radius",
                     "sonar": "Sonar radius", "anomaly": "Anomaly detection radius"}[param]
            yield Control("detector", sid, param, title + " (cm; -1 = Inherit)", 1, 100000, -1, 0,
                          "Overrides this detector's corresponding global range result. Reveal and near radii must fit within the work radius. "
                          "Passive scanners and quest detectors are separate; unsupported capabilities remain unavailable." + experimental)
    for path, (title, lo, hi, decimals) in BALL.items():
        yield Control("ball", "AArtifactWeirdBall", path, title + " (-1 = Inherit)", lo, hi, -1, decimals,
                      "Weird Ball only. Dynamic weight bounds are separate from its static inventory weight. "
                      "Minimum must not exceed maximum. Rate/amount semantics need gameplay measurement; this is a raw setting." + experimental)
    for sid in ANOMALIES:
        for param, title in (("speed", "Movement speed including artifact speed-up (%)"), ("hunt", "Pursuit distance (%)")):
            yield Control("anomaly", sid, param, title, 25, 300, 100, 0,
                          "Scales this ordinary anomaly variant. Speed changes both base and artifact-influenced maximum speed. "
                          "Prologue variant, damage and artifact-eating behavior are unchanged." + experimental)
    for sid in SPAWNERS:
        for rank in RANKS:
            for tier in TIERS:
                yield Control("rarity", sid, rank + "." + tier, f"{rank} / {tier} relative weight (%)", 0, 400, 100, 0,
                              "Additional weight after the global rare-artifact bias; the four tiers are normalized to their original total. "
                              "Only tiers already enabled in the loaded baseline are offered. Keep at least one enabled tier above zero. "
                              "Shared profiles also affect quest placements, including E06_MQ01 for Universal; existing spawns may not refresh." + experimental)


CONTROLS = {c.key: c for c in _controls()}


def control_specs():
    return ((c.key, c.label, c.lo, c.maximum, c.default, c.help) for c in CONTROLS.values())


def changes(values):
    if not isinstance(values, dict):
        raise ValueError("Artifact editor settings must be a mapping.")
    for key, value in values.items():
        spec = CONTROLS.get(key)
        if spec is None:
            continue
        value = spec.validate(value)
        if value != spec.default:
            yield spec, value


def collect(sliders):
    return {key: spec.validate(sliders[key].get()) for key, spec in CONTROLS.items()
            if key in sliders and sliders[key].get() != spec.default}


def _numeric(raw, positive=False):
    value = parse_number(raw, math.nan)
    return math.isfinite(value) and (value > 0 if positive else value >= 0)


def _plain_item(gd, sid):
    node = gd.items.children.get(sid)
    return (node is not None and node.values.get("SID") == sid
            and node.values.get("Type") == "EItemType::Artifact"
            and node.values.get("ArtifactType") in {"EArtifactType::" + t for t in ("Electro", "Chemical", "Fire", "Gravity")}
            and not any(gd.resolve(gd.items, sid, k) == "true" for k in ("IsQuestItem", "IsQuestItemPrototype", "DestroyOnPickup")))


def _effect_indices(gd, sid):
    node = gd.items.children.get(sid)
    effects = node.children.get("EffectPrototypeSIDs") if node else None
    if effects is None or effects.attrs or effects.children:
        return {}
    if any(not (k.startswith("[") and k.endswith("]") and k[1:-1].isdigit()) for k in effects.values):
        return {}
    return {v: k for k, v in effects.values.items() if list(effects.values.values()).count(v) == 1}


def _safe_effect(gd, sid, family):
    node = gd.effects.children.get(sid)
    if node is None or node.attr_dict() != {"refkey": "[0]"} or node.children:
        return False
    if (gd.resolve(gd.effects, sid, "Type") != "EEffectType::" + EFFECT_TYPES[family]
            or gd.resolve(gd.effects, sid, "bIsPermanent") != "true"
            or gd.resolve(gd.effects, sid, "DuplicationType") != "EDuplicateResolveType::KeepAll"):
        return False
    if any((gd.resolve(gd.effects, sid, key) or "").strip().lower() not in ("", "empty", "none")
           for key in ("ValueProviderSID", "EffectCurvePath")):
        return False
    raw = [gd.resolve(gd.effects, sid, k) for k in ("ValueMin", "ValueMax")]
    return all(_numeric(v, True) for v in raw) and raw[0] == raw[1]


def _radiation_valid(gd):
    for sid in RADIATION:
        node = gd.effects.children.get(sid)
        lo = gd.resolve(gd.effects, sid, "ValueMin")
        hi = gd.resolve(gd.effects, sid, "ValueMax")
        if (node is None or node.children or gd.resolve(gd.effects, sid, "Type") != "EEffectType::DegenRadiation"
                or not math.isfinite(parse_number(lo, math.nan)) or parse_number(lo) >= 0 or lo != hi
                or gd.resolve(gd.effects, sid, "bIsPermanent") != "true"):
            return False
    return True


def catalog(gd):
    """Control -> exact source paths. Fail closed on unaudited data shapes."""
    result = {}
    radiation_valid = _radiation_valid(gd)
    indices = {sid: _effect_indices(gd, sid) for sid in ARTIFACTS if _plain_item(gd, sid)}
    for key, c in CONTROLS.items():
        if c.group == "item":
            if c.target not in indices:
                continue
            if c.param in ("weight", "cost"):
                path = {"weight": "Weight", "cost": "Cost"}[c.param]
                raw = gd.resolve(gd.items, c.target, path)
                if _numeric(raw) and gd.items.children[c.target].get(path) is not None:
                    result[key] = ("ItemPrototypes", (path,))
            elif c.param == "radiation":
                native = [e for e in ARTIFACTS[c.target] if e in RADIATION and e in indices[c.target]]
                if radiation_valid and len(native) == 1:
                    result[key] = ("ItemPrototypes", ("EffectPrototypeSIDs." + indices[c.target][native[0]], native[0]))
            elif c.param in indices[c.target] and _safe_effect(gd, c.param, effect_family(c.param)):
                result[key] = ("ItemPrototypes", ("EffectPrototypeSIDs." + indices[c.target][c.param], c.param))
        elif c.group in ("detector", "ball"):
            node = gd.items.children.get(c.target)
            path = DETECTOR_PATHS[c.param] if c.group == "detector" else c.param
            if (node is not None and node.values.get("SID") == c.target
                    and node.attr_dict().get("refkey") == ("TemplateDetector" if c.group == "detector" else "TemplateArtifact")
                    and not any(gd.resolve(gd.items, c.target, k) == "true" for k in ("IsQuestItem", "IsQuestItemPrototype"))
                    and path in node.values and _numeric(gd.resolve(gd.items, c.target, path), c.group == "detector")):
                result[key] = ("ItemPrototypes", (path,))
        elif c.group == "anomaly":
            node = gd.anomalies.children.get(c.target)
            paths = ("MovementSpeed", "AnomalySpeedToMaxArtifacts") if c.param == "speed" else ("HuntDistance",)
            if (node is not None and node.values.get("SID") == c.target
                    and all(p in node.values and _numeric(gd.resolve(gd.anomalies, c.target, p), True) for p in paths)):
                result[key] = ("AnomalyPrototypes", paths)
        elif c.group == "rarity":
            rank, tier = c.param.split(".")
            node = gd.artifactspawners.children.get(c.target)
            row = node.children.get(rank) if node else None
            weights = row.children.get("RarityChance") if row else None
            if (node is not None and node.values.get("UseListOfArtifacts") == "false"
                    and weights is not None and not weights.attrs
                    and all(t in weights.values and _numeric(gd.resolve(gd.artifactspawners, c.target, f"{rank}.RarityChance.{t}")) for t in TIERS)
                    and _numeric(gd.resolve(gd.artifactspawners, c.target, f"{rank}.RarityChance.{tier}"), True)):
                result[key] = ("ArtifactSpawnerPrototypes", (f"{rank}.RarityChance.{tier}",))
    return result


def available(gd):
    return getattr(gd, "artifact_editor", {}) if gd is not None else {}


def _literal(value, raw):
    if not math.isfinite(value):
        raise ValueError("The combined artifact setting is not finite.")
    suffix = "%" if raw.strip().endswith("%") else "f" if raw.strip().endswith(("f", "F")) else ""
    return f"{value:.9g}" + suffix


def _put(patch, sid, path, value, original):
    parts = (sid, *path.split("."))
    node = patch
    parents = []
    for part in parts[:-1]:
        parents.append((node, part))
        node = node.setdefault(part, {})
    same = (value == original or (math.isfinite(parse_number(value, math.nan))
            and math.isclose(parse_number(value), parse_number(original, math.nan), rel_tol=1e-9, abs_tol=1e-9)))
    if same:
        node.pop(parts[-1], None)
    else:
        node[parts[-1]] = value
    for parent, part in reversed(parents):
        if not parent[part]:
            del parent[part]


def clone_sid(mod_name, item, effect):
    return "S2Tweaker_Artifact_" + hashlib.sha256((mod_name + "\0" + item + "\0" + effect).encode()).hexdigest()[:24]


def _effect_change(gd, settings, c, value):
    global_factor = settings.artifact_effect_factor
    if not math.isfinite(global_factor) or global_factor < 0:
        raise ValueError("Artifact strength must be finite and nonnegative.")
    if global_factor == 0:
        return None
    name = clone_sid(settings.mod_name, c.target, c.param)
    if name in gd.effects.children:
        raise ValueError("Generated artifact effect name already exists in the game data.")
    cfg = {"__new__": True, "__attrs__": "refkey=" + c.param, "SID": name}
    for leaf in ("ValueMin", "ValueMax"):
        raw = gd.resolve(gd.effects, c.param, leaf)
        cfg[leaf] = _literal(parse_number(raw) * global_factor * value / 100, raw)
    # Keep the original localization lookup when a new SID is introduced.
    localization = gd.resolve(gd.effects, c.param, "LocalizationSID")
    cfg["LocalizationSID"] = localization if localization and localization.lower() != "empty" else c.param
    return name, cfg


def apply(gd, settings, source, patches):
    if source not in ("ItemPrototypes", "EffectPrototypes", "ArtifactSpawnerPrototypes", "AnomalyPrototypes"):
        return
    selected = list(changes(settings.artifact_overrides))
    if not selected:
        return
    data = available(gd)
    ranks = set()
    touched_detectors, touched_ball = set(), False
    for c, value in selected:
        if c.key not in data:
            continue
        file, paths = data[c.key]
        is_effect = c.group == "item" and effect_family(c.param) is not None
        if source == "EffectPrototypes":
            if is_effect:
                change = _effect_change(gd, settings, c, value)
                if change:
                    patches[change[0]] = change[1]
            continue
        if source != file:
            continue
        if c.group == "rarity":
            ranks.add((c.target, c.param.split(".")[0]))
            continue
        if c.group == "item" and (is_effect or c.param == "radiation"):
            path, original = paths
            if is_effect:
                change = _effect_change(gd, settings, c, value)
                target = change[0] if change else original
            else:
                target = "empty" if value == 0 else RADIATION[int(value) - 1]
            _put(patches, c.target, path, target, original)
            if c.param == "radiation" and value == 0:
                visible_path = path.replace("EffectPrototypeSIDs", "ShouldShowEffects")
                raw = gd.resolve(gd.items, c.target, visible_path)
                if raw is not None:
                    _put(patches, c.target, visible_path, "false", raw)
        else:
            root = gd.anomalies if c.group == "anomaly" else gd.items
            for path in paths:
                raw = gd.resolve(root, c.target, path)
                target = parse_number(raw) * value / 100 if c.group == "anomaly" else value
                _put(patches, c.target, path, _literal(target, raw), raw)
            if c.group == "detector":
                touched_detectors.add(c.target)
            touched_ball |= c.group == "ball"
    if source == "ItemPrototypes":
        def final(sid, path):
            return parse_number(patches.get(sid, {}).get(path, gd.resolve(gd.items, sid, path)), math.nan)
        for sid in touched_detectors:
            if max(final(sid, "ShowArtifactRadius"), final(sid, "MinDetectRadius")) > final(sid, "DetectorWorkRadius"):
                raise ValueError(f"{sid}: reveal and near detection radii must fit within the search / work radius.")
        if touched_ball and final("AArtifactWeirdBall", "MinWeight") > final("AArtifactWeirdBall", "MaxWeight"):
            raise ValueError("Weird Ball: minimum dynamic weight must not exceed maximum weight.")
    if source == "ArtifactSpawnerPrototypes":
        factors = {c.key: value / 100 for c, value in selected}
        for sid, rank in ranks:
            raw = {t: gd.resolve(gd.artifactspawners, sid, f"{rank}.RarityChance.{t}") for t in TIERS}
            current = patches.get(sid, {}).get(rank, {}).get("RarityChance", {})
            weights = {t: parse_number(current.get(t, raw[t])) * factors.get(f"{PREFIX}rarity:{sid}:{rank}.{t}", 1) for t in TIERS}
            total, baseline_total = sum(weights.values()), sum(parse_number(v) for v in raw.values())
            if not math.isfinite(total) or total <= 0 or any(v < 0 for v in weights.values()):
                raise ValueError(f"{sid} / {rank}: keep at least one rarity tier above zero.")
            for tier in TIERS:
                _put(patches, sid, f"{rank}.RarityChance.{tier}", _literal(weights[tier] * baseline_total / total, raw[tier]), raw[tier])


def probe(key):
    c = CONTROLS.get(key)
    if c is None:
        return None
    return {"artifact_overrides": {key: (50 if c.default == 100 else 0 if c.param == "radiation" else c.minimum)}}


def footprint(gd, key):
    """Direct footprint avoids generating a full mod for every deferred row."""
    if key not in available(gd):
        return set()
    c = CONTROLS[key]
    _source, paths = available(gd)[key]
    if c.group == "item" and (c.param == "radiation" or effect_family(c.param)):
        from .modscan import EFFECT_LIST_LEAF
        effects = RADIATION if c.param == "radiation" else (paths[1],)
        return {(c.target, EFFECT_LIST_LEAF), (c.target, "EffectPrototypeSIDs"),
                (c.target, "ShouldShowEffects")} | {
                    (effect, leaf) for effect in effects for leaf in
                    ("ValueMin", "ValueMax", "Type", "Duration", "DuplicationType", "bIsPermanent", "LocalizationSID")}
    if c.group == "rarity":
        return {(c.target, tier) for tier in TIERS}  # normalization changes every tier
    if c.group == "ball" and c.param in ("MinWeight", "MaxWeight"):
        return {(c.target, "MinWeight"), (c.target, "MaxWeight")}
    return {(c.target, p.rsplit(".", 1)[-1]) for p in paths}


def summarize(values):
    return [f"{c.label}: {value:g}" + (" (shared quest placements; experimental)" if c.group == "rarity" else "")
            for c, value in changes(values)]
