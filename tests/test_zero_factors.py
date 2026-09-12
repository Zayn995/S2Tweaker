"""Check zero recoil/spread factors produce real changes.

Permit zero for multiplicative values while rejecting negative factors and
zero divisors. Derive expected coverage from live data."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)
WGS = ("WeaponData/WeaponGeneralSetupPrototypes/"
       "WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg")
CWS = ("WeaponData/CharacterWeaponSettingsPrototypes/"
       "CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg")


def values_by_struct(text: str, key: str) -> dict[str, str]:
    """Extract {top_level_SID: value} for a named leaf from patch text."""
    out, cur = {}, None
    for line in text.splitlines():
        if line and not line.startswith((" ", "struct")):
            cur = line.split(" :")[0]
            continue
        m = re.match(r"\s+" + re.escape(key) + r" = (\S+)", line)
        if m and cur:
            out[cur] = m.group(1)
    return out


# Set every explicit recoil baseline to zero.
vals = gd.weapon_general_values("RecoilParams.RecoilRadius")
assert len(vals) >= 70, len(vals)
p = build_patches(gd, Settings(recoil_factor=0.0))
assert WGS in p, list(p)
got = values_by_struct(p[WGS], "RecoilRadius")
assert set(got) == set(vals), (set(vals) - set(got), set(got) - set(vals))
assert all(parse_number(v) == 0 for v in got.values()), got
for (ed, sid) in gd.dlc_weapon_general_values("RecoilParams.RecoilRadius"):
    hits = [k for k in p if f"DLCGameData/{ed}/" in k
            and parse_number(values_by_struct(p[k], "RecoilRadius")
                             .get(sid, "1")) == 0]
    assert hits, f"DLC {ed}/{sid} without a RecoilRadius-zero patch"
assert any("Weapon recoil" in line
           for line in summarize(Settings(recoil_factor=0.0)))
print(f"Recoil 0 %: {len(got)} base structs + DLC set to RecoilRadius 0  OK")

# Set WGS first-shot and CWS dispersion to zero.
p = build_patches(gd, Settings(spread_factor=0.0))
first = gd.weapon_general_values("DispersionParams.FirstShotDispersionRadius")
got = values_by_struct(p[WGS], "FirstShotDispersionRadius")
assert set(got) == set(first), set(first) ^ set(got)
assert all(parse_number(v) == 0 for v in got.values())
expected_cws = {
    sid for sid in gd.weaponsettings.children
    if "_Player" in sid and "#" not in sid
    and parse_number(gd.resolve(gd.weaponsettings, sid,
                                "DispersionRadius")) > 0}
got_cws = values_by_struct(p[CWS], "DispersionRadius")
assert set(got_cws) == expected_cws, (expected_cws ^ set(got_cws))
assert all(parse_number(v) == 0 for v in got_cws.values())
print(f"Spread 0 %: {len(got)} first-shot + {len(got_cws)} "
      "Dispersion structs set to zero  OK")

# Retain guards on inverse values and negative factors.
assert not build_patches(gd, Settings(
    weapon_category_factors={"rifle": {"firerate": 0.0}})), \
    "Fire rate 0 must not cause division"
assert not build_patches(gd, Settings(durability_factor=0.0))
assert not build_patches(gd, Settings(aim_time_factor=0.0))
assert not build_patches(gd, Settings(recoil_factor=-1.0))
assert not build_patches(gd, Settings(spread_factor=-0.5))
# 100% remains neutral.
assert not build_patches(gd, Settings(recoil_factor=1.0, spread_factor=1.0))
print("Guards: fire rate/durability/ADS duration 0 and negative factors "
      "-> no patch  OK")

print("\nZERO-FACTORS-TEST OK")
