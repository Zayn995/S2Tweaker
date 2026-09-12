"""Check clearing technician prerequisite/blocking lists.

Verify live inventory, empty-scalar syntax, parser roundtrip, scan coverage
and neutral output; exclude placeholders and the base template."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import cfgparse, modscan
from s2tweaker.gamedata import GameData, NEEDED_FILES, CACHE_SCHEMA
from s2tweaker.tweaks import (Settings, build_patches, summarize,
                              UPGRADE_LOCK_KEYS)

assert "UpgradePrototypes.cfg.bin" in NEEDED_FILES and CACHE_SCHEMA >= 13
gd = GameData(VANILLA)
KEY = "UpgradePrototypes/UpgradePrototypes_patch_S2Tweaker.cfg"

# --- 1) Inventory ---------------------------------------------------------
n_up = sum(1 for k in gd.upgrades.children if "#" not in k and k != "[0]")
assert n_up >= 1000, n_up
sets = {key: set(gd.upgrade_sids_with(key)) for key in UPGRADE_LOCK_KEYS.values()}
assert len(sets["BlockingUpgradePrototypeSIDs"]) >= 400
assert len(sets["RequiredUpgradePrototypeSIDs"]) >= 600
assert len(sets["RequiredItemPrototypeSIDs"]) >= 90
assert "[0]" not in {s for v in sets.values() for s in v}
# Check a known upgrade's mutually exclusive and prerequisite branches.
ex = "DutyArmor_4_E1_BulletProof2Upgrade"
assert ex in sets["BlockingUpgradePrototypeSIDs"] and ex in sets["RequiredUpgradePrototypeSIDs"]
# Placeholder lists ("" / "empty") do not count as restrictions.
ph = "Seva_Neutral_PSY_Right_3_2"
assert ph in gd.upgrades.children and ph not in sets["BlockingUpgradePrototypeSIDs"]
print(f"Inventory: {n_up} Upgrades, locks "
      + ", ".join(f"{k.replace('PrototypeSIDs', '')}={len(v)}" for k, v in sets.items())
      + "  OK")

# --- 2) One checkbox: exactly that list, `Key =` format ---
s = Settings(upgrades_take_both=True)
p = build_patches(gd, s)
assert list(p) == [KEY], list(p)
txt = p[KEY]
assert txt.count("{bpatch}") == len(sets["BlockingUpgradePrototypeSIDs"])
lines = [l for l in txt.splitlines() if "=" in l]
assert all(l == "   BlockingUpgradePrototypeSIDs =" for l in lines), lines[:3]
assert "RequiredUpgradePrototypeSIDs" not in txt and "empty" not in txt
root = cfgparse.parse(txt)
assert set(root.children) == sets["BlockingUpgradePrototypeSIDs"]
assert all(n.values == {"BlockingUpgradePrototypeSIDs": ""} for n in root.children.values())
pairs = modscan.pairs_from_patches(p)
assert pairs == {(sid, "BlockingUpgradePrototypeSIDs")
                 for sid in sets["BlockingUpgradePrototypeSIDs"]}
assert any("mutually exclusive" in line for line in summarize(s))
print(f"Take both: {len(root.children)} structs, `Key =` without trailing whitespace, "
      "Roundtrip + Fussabdruck  OK")

# Combine all three options with the appropriate fields per upgrade.
s3 = Settings(upgrades_take_both=True, upgrades_no_blueprint=True,
              upgrades_no_tiers=True)
root = cfgparse.parse(build_patches(gd, s3)[KEY])
union = set().union(*sets.values())
assert set(root.children) == union, len(union)
for sid, node in root.children.items():
    expected = {key for key, v in sets.items() if sid in v}
    assert set(node.values) == expected, (sid, node.values, expected)
assert len([l for l in summarize(s3) if l.startswith("Upgrades:")]) == 3
print(f"All three: {len(union)} structs, correct keys per upgrade  OK")

# --- 4) Neutral and independent checkboxes ---
assert not build_patches(gd, Settings())
only_tiers = cfgparse.parse(build_patches(gd, Settings(upgrades_no_tiers=True))[KEY])
assert set(only_tiers.children) == sets["RequiredUpgradePrototypeSIDs"]
only_bp = cfgparse.parse(build_patches(gd, Settings(upgrades_no_blueprint=True))[KEY])
assert set(only_bp.children) == sets["RequiredItemPrototypeSIDs"]
print("Neutral = no patch, checkboxes independent  OK")

print("\nUPGRADES-TEST OK")
