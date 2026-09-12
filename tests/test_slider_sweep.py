"""Check offered controls for neutral output, effective endpoints and monotonic scaling.

Include supported per-item parameters. Compare linear, inverse and bounded
behavior across probes. Requires vanilla data and temporary GUI settings."""
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.gui import CHECK_FIELDS, SLIDER_FIELDS
from s2tweaker.tweaks import (ALL_CATEGORIES, AMMO_PARAMS, AMMO_PARAM_KEYS,
                              ARMOR_PARAMS, Settings, build_patches, input_ini,
                              summarize, weapon_available_params)

gd = GameData(str(VANILLA))
NUM = re.compile(r"^-?\d+(?:\.\d+)?(?:e-?\d+)?[fF]?\.?[;%]?$")
MUT_PARAMS = ("hp", "speed", "damage", "regen")


def leaves(patches: dict[str, str]) -> dict[tuple, str]:
    """Parse generated patches into {(file, path_tuple): raw_value}."""
    out: dict[tuple, str] = {}
    for fname, text in patches.items():
        stack: list[str] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            depth = (len(line) - len(line.lstrip(" "))) // 3
            body = line.strip()
            if body.endswith("struct.end"):
                stack = stack[:depth]
                continue
            m = re.match(r"(.+?) : struct\.begin", body)
            if m:
                stack = stack[:depth] + [m.group(1)]
                continue
            if " = " in body or body.endswith(" ="):
                key, _, value = body.partition(" = ")
                out[(fname, tuple(stack + [key.strip()]))] = value.strip()
    return out


def explained(xs: list[float], es: list[float]) -> bool:
    """Check linear/inverse relationships or at least monotonic progression."""
    if not all(math.isfinite(e) for e in es):
        return False
    if max(es) - min(es) <= 1e-9:
        return True                                    # Constant value at cap.
    for transform in (lambda x: x, lambda x: 1.0 / x if x else None):
        ts = [transform(x) for x in xs]
        if any(t is None for t in ts) or ts[1] == ts[0]:
            continue
        b = (es[1] - es[0]) / (ts[1] - ts[0])
        a = es[0] - b * ts[0]
        if all(abs(a + b * t - e) <= 1e-4 * max(1.0, abs(e))
               for t, e in zip(ts, es)):
            return True
    up = all(y >= x - 1e-9 for x, y in zip(es, es[1:]))
    down = all(y <= x + 1e-9 for x, y in zip(es, es[1:]))
    return up or down                                  # Rounding / saturation.


def law_violations(probes: list[dict], xs: list[float]) -> list[str]:
    common = set(probes[0]) & set(probes[1]) & set(probes[2])
    bad = []
    for leaf in common:
        raws = [p[leaf] for p in probes]
        if not all(NUM.match(r) for r in raws):
            continue
        es = [parse_number(r) for r in raws]
        if not explained(xs, es):
            bad.append(f"{leaf[0]} :: {'.'.join(leaf[1])} "
                       f"x={xs} -> {es}")
    return bad


# --- 1) Vanilla settings produce nothing ---
assert not build_patches(gd, Settings()), \
    "Settings() at vanilla produces patches"
print("Vanilla settings: 0 patch files  OK")


# --- 2) Fixed sliders: GUI -> Settings -> patch ---
app = gui.App()
app.update()

dead, no_line = [], []
for key, field in SLIDER_FIELDS.items():
    row = app.sliders[key]
    for value in (row.lo, row.hi, (row.default + row.hi) / 2.0):
        if abs(value - row.default) < 1e-9:
            continue
        row.set(value)
        s = app._collect()
        if not build_patches(gd, s):
            dead.append(f"{key}={value:g}")
        if not summarize(s):
            no_line.append(f"{key}={value:g}")
    row.set(row.default)
for key, field in CHECK_FIELDS.items():
    app.checks[key].select()
    s = app._collect()
    # Handle dependent-only stat bars/runtime relations and separate INI output
    # outside ordinary standalone cfg-control checks.
    if (not build_patches(gd, s) and key not in
            ("stat_bars", "art_stat_labels", "no_mouse_smooth", "no_view_accel",
             "relations_runtime")):
        dead.append(f"check:{key}")
    if key in ("no_mouse_smooth", "no_view_accel"):
        assert input_ini(s), key
    if not summarize(s):
        no_line.append(f"check:{key}")
    app.checks[key].deselect()
try:
    app.destroy()
except Exception:
    pass
assert not dead, f"Sliders producing no patch: {dead}"
assert not no_line, f"Sliders missing from the tweak list: {no_line}"
print(f"{len(SLIDER_FIELDS)} sliders + {len(CHECK_FIELDS)} Checkboxen: "
      "Each setting produces a patch and summary line  OK")


# Every offered override parameter must generate an applicable patch.
def probe(**kw) -> dict:
    return build_patches(gd, Settings(**kw))


offered = 0
blind = []
for wgs, (cat, cws) in sorted(gd.player_weapons().items()):
    if not cat:                       # Item is not offered in the tree.
        continue
    for param in weapon_available_params(gd, cws):
        offered += 1
        if not probe(weapon_overrides={wgs: {param: 2.0}}):
            blind.append(f"weapon {wgs}.{param}")

for sid, mods in sorted(gd.ammo_mods().items()):
    usable = [p for p in AMMO_PARAMS
              if abs(mods.get(AMMO_PARAM_KEYS[p], 0.0)) > 1e-9]
    for param in (usable or AMMO_PARAMS):
        offered += 1
        if not probe(ammo_overrides={sid: {param: 2.0}}):
            blind.append(f"ammo {sid}.{param}")

armor_values = dict(gd.armor_protection())
armor_values.update({sid: values
                     for sid, (_slot, values, _ed) in gd.dlc_player_armors().items()})
for sid, values in sorted(armor_values.items()):
    for param in ARMOR_PARAMS:
        if param not in values:       # Zero baseline: no control offered.
            continue
        offered += 1
        if not probe(armor_overrides={sid: {param: 2.0}}):
            blind.append(f"armor {sid}.{param}")

species = sorted({gd.mutant_faction(sid) for sid in gd.mutants()} - {None})
damaging = {sp for sp in species if gd.mutant_attack_damages(sp)}
for sp in species:
    for param in MUT_PARAMS:
        if param == "damage" and sp not in damaging:
            continue              # These species lack direct damage attacks.
        offered += 1
        if not probe(mutant_overrides={sp: {param: 2.0}}):
            blind.append(f"mutant {sp}.{param}")

assert not blind, f"Available overrides without a patch: {blind}"
print(f"{offered} available override sliders: all produce a patch  OK")


# --- 4) Faction pairs reach their exact target values ---------------------
pairs = gd.relation_pairs()
assert pairs, "No faction pairs found"
wrong = []
for key, vanilla in sorted(pairs.items()):
    target = int(vanilla) + 500
    hits = [v for leaf, v in leaves(probe(faction_relations={key: target})).items()
            if leaf[1][-1] == key]
    if not hits or int(parse_number(hits[0])) != target:
        wrong.append(f"{key}: {hits or "no patch"} instead of {target}")
assert not wrong, f"Faction pairs with incorrect values: {wrong[:5]}"
print(f"{len(pairs)} Faction pairs reach their exact target values  OK")


# Check three-point behavior for each fixed control.
violations = []
for key, field in SLIDER_FIELDS.items():
    default = float(getattr(Settings(), field))
    xs = [default * 0.5, default * 2.0, default * 3.0] if default else [0.5, 1.0, 2.0]
    extra = ({"item_weight_categories": set(ALL_CATEGORIES)}
             if field == "item_weight_factor" else {})
    probes = [leaves(build_patches(gd, Settings(**{field: x}, **extra)))
              for x in xs]
    for bad in law_violations(probes, xs):
        violations.append(f"{key}: {bad}")
assert not violations, ("Generated values do not follow any expected rule:\n  "
                        + "\n  ".join(violations[:10]))
print(f"{len(SLIDER_FIELDS)} sliders: all generated values follow their "
      "Gesetz (linear / invers / monoton)  OK")


# --- 6) Cascade: individual weapon overrides category ---
rifle = next(s for s, (c, _) in sorted(gd.player_weapons().items()) if c == "rifle")
only_cat = leaves(probe(weapon_category_factors={"rifle": {"damage": 2.0}}))
with_one = leaves(probe(weapon_category_factors={"rifle": {"damage": 2.0}},
                        weapon_overrides={rifle: {"damage": 3.0}}))
differing = [leaf for leaf in set(only_cat) | set(with_one)
             if only_cat.get(leaf) != with_one.get(leaf)]
assert len(differing) == 1, \
    f"Individual weapon override changes {len(differing)} leaves instead of 1: {differing[:5]}"
base = parse_number(gd.resolve(gd.weaponsettings,
                               gd.player_weapons()[rifle][1], "BaseDamage"))
assert abs(parse_number(with_one[differing[0]]) - base * 3.0) < 1e-6, \
    f"Cascade: {differing[0]} = {with_one[differing[0]]}, erwartet {base * 3.0}"
assert abs(parse_number(only_cat[differing[0]]) - base * 2.0) < 1e-6
print(f"Cascade {rifle}: individual weapon x3 overrides category x2, "
      "Rest of category unchanged  OK")


# Weapons without wear values must not offer durability controls.
without = [wgs for wgs, (cat, cws) in gd.player_weapons().items()
           if cat and "durability" not in weapon_available_params(gd, cws)]
assert without, ("No weapon CWS without DurabilityDamagePerShot found - "
                 "Game data changed? Update this test accordingly.")
for wgs in without:
    assert not probe(weapon_overrides={wgs: {"durability": 2.0}}), \
        f"{wgs} does have a wear value"
print(f"{len(without)} weapons without wear values: no durability slider  OK")

print("\nSLIDER SWEEP PASSED")
