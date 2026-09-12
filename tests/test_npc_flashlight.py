"""Check NPC flashlight prototypes, switching hours and combat chance.

Verify extraction coverage, actual indexed keys, complete distance-band entries,
caps, live scaling and neutral output. Player light values remain outside cfg coverage."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData, NEEDED_FILES, CACHE_SCHEMA
from s2tweaker.tweaks import Settings, build_patches, summarize

assert "FlashlightPrototypes.cfg.bin" in NEEDED_FILES, "File missing from extraction list"
assert CACHE_SCHEMA >= 16, "New file without schema bump"
gd = GameData(VANILLA)
KEY = "FlashlightPrototypes/FlashlightPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
AI = "AIGlobals.cfg_patch_S2Tweaker.cfg"


def sid(node) -> str:
    return (node.values.get("SID") or "").strip().rstrip(";").strip()


def nums(text: str, key: str) -> list[float]:
    return [float(v) for v in re.findall(rf"\b{key} = (-?[0-9.]+)", text)]


# --- 1) Inventory --------------------------------------------------------
structs = {k: n for k, n in gd.flashlights.children.items() if "#" not in k}
by_sid = {sid(n): (k, n) for k, n in structs.items()}
assert {"NPCFlashlight", "PlayerFlashlight"} <= set(by_sid), sorted(by_sid)
npc_key, npc = by_sid["NPCFlashlight"]
rows = [e for k, e in npc.children["ExtraLightDistanceBasedParameters"].children.items()
        if "#" not in k]
assert len(rows) == 3, len(rows)
v_int = [parse_number(e.values["Intencity"]) for e in rows]
v_rad = [parse_number(e.values["AttenuationRadius"]) for e in rows]
v_cone = [parse_number(e.values["OuterConeAngle"]) for e in rows]
v_dist = [parse_number(e.values["Distance"]) for e in rows]
assert v_int == sorted(v_int) and v_int[0] > 0, v_int
_, player = by_sid["PlayerFlashlight"]
prow = [e for k, e in player.children["ExtraLightDistanceBasedParameters"].children.items()
        if "#" not in k]
assert all(parse_number(e.values["Intencity"]) == 0 for e in prow), \
    "Player flashlight now has light values; reassess support for a player slider"
print(f"Inventory: {len(structs)} Structs, NPC flashlight = {npc_key}, "
      f"Intencity {v_int}, Radius {v_rad}, Kegel {v_cone}  OK")

# --- 2) Brightness x2 + cone x1.5: complete entries, values x factor ---
text = build_patches(gd, Settings(npc_flashlight_factor=2.0,
                                  npc_flashlight_cone_factor=1.5))[KEY]
assert f"{npc_key} : struct.begin {{bpatch}}" in text, text[:120]
assert "ExtraLightDistanceBasedParameters : struct.begin {bpatch}" in text
assert text.count(": struct.begin {bpatch}") == 2 + len(rows), text
for got, want in ((nums(text, "Intencity"), [v * 2 for v in v_int]),
                  (nums(text, "AttenuationRadius"), [v * 2 for v in v_rad]),
                  (nums(text, "OuterConeAngle"), [v * 1.5 for v in v_cone]),
                  (nums(text, "Distance"), v_dist)):
    assert len(got) == len(rows) and all(abs(g - w) < 1e-6 for g, w in zip(got, want)), (got, want)
# Only the actual NPC top-level key is patched; nested array indices are independent.
top_level = [ln for ln in text.splitlines() if ln and not ln.startswith(" ") and ln.endswith("{bpatch}")]
assert top_level == [f"{npc_key} : struct.begin {{bpatch}}"], top_level
print("Patch: top-level key, {bpatch} at 3 levels, 3 complete entries, x2 / x1.5  OK")

# --- 3) Cone capped at 170 degrees ---
text = build_patches(gd, Settings(npc_flashlight_cone_factor=3.0))[KEY]
cones = nums(text, "OuterConeAngle")
assert max(cones) == 170.0 and all(c <= 170.0 for c in cones), cones
assert nums(text, "Intencity") == v_int, "Cone slider must not change brightness"
print(f"Cone x3 -> {cones} (Deckel 170)  OK")

# --- 4) Combat chance per rank, capped at 1.0, factor 0 = never ---
text = build_patches(gd, Settings(npc_flashlight_combat_factor=1.5))[CORE]
block = text[text.index("FlashlightCombatUseChance"):]
chances = dict(re.findall(r"(\w+) = ([0-9.]+)", block.split("struct.end")[0]))
assert set(chances) >= {"Newbie", "Experienced", "Veteran", "Master"}, chances
assert float(chances["Newbie"]) == 1.0 and float(chances["Experienced"]) == 1.0
assert abs(float(chances["Veteran"]) - 0.75) < 1e-9 and abs(float(chances["Master"]) - 0.375) < 1e-9
text0 = build_patches(gd, Settings(npc_flashlight_combat_factor=0.0))[CORE]
assert all(float(v) == 0 for v in dict(re.findall(r"(\w+) = ([0-9.]+)",
           text0[text0.index("FlashlightCombatUseChance"):].split("struct.end")[0])).values())
print(f"Combat chance x1.5 -> {chances}; x0 -> all zero  OK")

# Read switching-hour baselines from AIGlobals.
root = gd.aiglobals.children["AISettings"]
v_on = int(parse_number(root.values["FlashlightTimeOfDayOn"]))
v_off = int(parse_number(root.values["FlashlightTimeOfDayOff"]))
assert Settings().npc_flashlight_on_hour == v_on and Settings().npc_flashlight_off_hour == v_off, \
    "Settings default differs from vanilla; neutral settings would patch"
text = build_patches(gd, Settings(npc_flashlight_on_hour=20, npc_flashlight_off_hour=6))[AI]
assert "FlashlightTimeOfDayOn = 20" in text and "FlashlightTimeOfDayOff = 6" in text, text
only_on = build_patches(gd, Settings(npc_flashlight_on_hour=20))[AI]
assert "FlashlightTimeOfDayOff" not in only_on, "Off written despite vanilla setting"
print(f"Hours: vanilla {v_on}/{v_off}, patch 20/6, individual setting writes only On  OK")

# --- 6) Neutral and summary lines ---
neutral = build_patches(gd, Settings())
assert KEY not in neutral and not any("Flashlight" in t for t in neutral.values())
lines = summarize(Settings(npc_flashlight_factor=2.0, npc_flashlight_cone_factor=1.5,
                           npc_flashlight_combat_factor=0.5,
                           npc_flashlight_on_hour=20, npc_flashlight_off_hour=6))
for needle in ("NPC flashlight brightness & reach", "NPC flashlight beam width",
               "NPC flashlight use in combat", "on from 20:00", "off at 6:00"):
    assert any(needle in ln for ln in lines), (needle, lines)
print("Neutral empty, 5 summary lines  OK")

print("\nNPC FLASHLIGHT TEST PASSED")
