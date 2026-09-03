"""Techniker-Upgrade-Sperren (UpgradePrototypes.cfg) - drei Checkboxen
(Wunsch des Besitzers 03.09.2026, Vorbilder: Nexus-Mods 2549 "Take Both
Upgrades" und 2545 "Unrestricted Upgrades" + NoTiers).

Prueft: Inventar der Sperrlisten (live, Platzhalter "" / "empty" zaehlen als
leer, [0]-Template bleibt draussen), Patch-Format (`Key =` ohne Leerzeichen
dahinter - `[0] = empty` funktioniert laut Mod-Autor nicht), Parser-Roundtrip
und Mod-Scan-Fussabdruck, Neutralzustand.
"""
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

# --- 1) Inventar ---------------------------------------------------------
n_up = sum(1 for k in gd.upgrades.children if "#" not in k and k != "[0]")
assert n_up >= 1000, n_up
sets = {key: set(gd.upgrade_sids_with(key)) for key in UPGRADE_LOCK_KEYS.values()}
assert len(sets["BlockingUpgradePrototypeSIDs"]) >= 400
assert len(sets["RequiredUpgradePrototypeSIDs"]) >= 600
assert len(sets["RequiredItemPrototypeSIDs"]) >= 90
assert "[0]" not in {s for v in sets.values() for s in v}
# Bekannter Anker: BulletProof 2 der Duty-Ruestung sperrt DecreaseArmorWeight
# und braucht BulletProof 1
ex = "DutyArmor_4_E1_BulletProof2Upgrade"
assert ex in sets["BlockingUpgradePrototypeSIDs"] and ex in sets["RequiredUpgradePrototypeSIDs"]
# Platzhalter-Listen ("" / "empty") zaehlen NICHT als Sperre
ph = "Seva_Neutral_PSY_Right_3_2"
assert ph in gd.upgrades.children and ph not in sets["BlockingUpgradePrototypeSIDs"]
print(f"Inventar: {n_up} Upgrades, Sperren "
      + ", ".join(f"{k.replace('PrototypeSIDs', '')}={len(v)}" for k, v in sets.items())
      + "  OK")

# --- 2) Eine Box: genau diese Liste, Format `Key =` -----------------------
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
print(f"Take both: {len(root.children)} Structs, `Key =` ohne Leerzeichen, "
      "Roundtrip + Fussabdruck  OK")

# --- 3) Alle drei Boxen: Vereinigung, je Struct die passenden Schluessel --
s3 = Settings(upgrades_take_both=True, upgrades_no_blueprint=True,
              upgrades_no_tiers=True)
root = cfgparse.parse(build_patches(gd, s3)[KEY])
union = set().union(*sets.values())
assert set(root.children) == union, len(union)
for sid, node in root.children.items():
    expected = {key for key, v in sets.items() if sid in v}
    assert set(node.values) == expected, (sid, node.values, expected)
assert len([l for l in summarize(s3) if l.startswith("Upgrades:")]) == 3
print(f"Alle drei: {len(union)} Structs, Schluessel je Upgrade korrekt  OK")

# --- 4) Neutral + Einzelboxen unabhaengig --------------------------------
assert not build_patches(gd, Settings())
only_tiers = cfgparse.parse(build_patches(gd, Settings(upgrades_no_tiers=True))[KEY])
assert set(only_tiers.children) == sets["RequiredUpgradePrototypeSIDs"]
only_bp = cfgparse.parse(build_patches(gd, Settings(upgrades_no_blueprint=True))[KEY])
assert set(only_bp.children) == sets["RequiredItemPrototypeSIDs"]
print("Neutral = kein Patch, Boxen unabhaengig  OK")

print("\nUPGRADES-TEST OK")
