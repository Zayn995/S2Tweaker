"""Verify control wiring without creating a GUI window.

Check field registration, collection, patch generation, summaries and neutral
output. --static-only omits game-data checks for CI. Appearance and input
interaction remain separate visual checks."""
import ast
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, input_ini, summarize
# Import the module without constructing App.
from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS

ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


# Read _collect wiring statically from source.
source = (ROOT / "s2tweaker" / "gui.py").read_text(encoding="utf-8")
tree = ast.parse(source)
collect = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "_collect":
        collect = node
        break
assert collect is not None, "_collect() not found"
collected = set()
for node in ast.walk(collect):
    if isinstance(node, ast.keyword) and node.arg:
        collected.add(node.arg)

fields = set(SLIDER_FIELDS.values()) | set(CHECK_FIELDS.values())
missing = sorted(fields - collected)
check(not missing,
      f"Each of the {len(fields)} controls is collected by _collect()"
      + (f" - MISSING: {missing}" if missing else ""))

known = {f.name for f in Settings.__dataclass_fields__.values()}
unknown = sorted(f for f in fields if f not in known)
check(not unknown, f"Each field table points to an existing Settings field{unknown}")

if "--static-only" in sys.argv:
    print("STATIC WIRING PASSED (without game data or windows)")
    sys.exit(0)

gd = GameData(str(VANILLA))

# --- 2) Vanilla produces nothing ---
check(build_patches(gd, Settings(mod_name="S2Tweaker")) == {},
      "Vanilla settings produce no patch files")
check(not summarize(Settings()), "Vanilla settings produce no tweak-list lines")
check(input_ini(Settings()) is None, "Vanilla settings produce no INI")

# Probe each control with upward/downward factors or changed absolute values.
SPECIAL = {                      # Special probes for zero baselines or capped defaults.
    "fall_damage_pct": 50.0, "fast_travel_lock": 0.0, "slow_run_threshold_pct": 25.0,
    "evening_start_hour": 22.0, "armor_deflect_chance_pct": 50.0,
    "npc_weapon_rank_add": 2.0, "scope_sway_pct": 50.0,
    "trader_min_durability_pct": 0.0, "hud_compass": 2.0, "hud_crosshair": 2.0,
    "hud_body_markers": 2.0, "hud_stash_markers": 2.0, "pistol_slot_level": 3.0,
}
# Handle dependent stat bars/runtime relations and separate INI output explicitly.
ALONE_EMPTY = {"stat_bars_follow", "artifact_stat_labels_follow", "no_mouse_smoothing", "no_view_acceleration",
               "relations_runtime"}

COUPLED = {
    "stash_extra_chance_pct": {"stash_extra_artifacts": True},
    "npc_armor_drop_min_pct": {"npc_armor_drop_chance_pct": 25.0},
    "npc_armor_drop_max_pct": {"npc_armor_drop_chance_pct": 25.0},
}

t0 = time.time()
dead, no_line = [], []
for field in sorted(fields):
    default = getattr(Settings(), field)
    if isinstance(default, bool):
        probe = not default
    elif field in SPECIAL:
        probe = SPECIAL[field]
    elif isinstance(default, (int, float)):
        probe = default * 2 if default else 1.0
        if isinstance(default, int):
            probe = int(probe) or 1
    else:
        continue                      # Tree dictionaries have dedicated suites.
    extra = COUPLED.get(field, {})
    s = Settings(mod_name="S2Tweaker", **{field: probe}, **extra)
    if extra:
        check(build_patches(gd, s) != build_patches(gd, Settings(**extra)),
              f"dependent control {field} changes its enabled feature")
    if not build_patches(gd, s) and field not in ALONE_EMPTY:
        # Probe the opposite direction to cover capped values.
        if isinstance(default, (int, float)) and not isinstance(default, bool):
            s2 = Settings(mod_name="S2Tweaker", **{field: type(default)(default * 0.5)})
            if build_patches(gd, s2):
                s = s2
            else:
                dead.append(field)
        else:
            dead.append(field)
    if field in ALONE_EMPTY:
        # Require an INI output or a patch line.
        if not (input_ini(s) or summarize(s)):
            dead.append(field)
    if not summarize(s):
        no_line.append(field)
check(not dead, f"Each control produces a patch{dead}")
check(not no_line, f"Each control appears in the tweak list{no_line}")
print(f"      ({len(fields)} controls in {time.time() - t0:.1f}s, without opening a window)")

print(f"\n=== {ok} checks passed ===")
