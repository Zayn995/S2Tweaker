"""Quest-Cooldown- und ADS-Aim-in-Tweaks (Community-Wuensche 02.09.).

Rein auf tweaks/gamedata-Ebene (kein GUI-Fenster): Sollwerte werden aus
den Vanilla-Daten nachgerechnet, nichts hardcodiert ausser den bekannten
Vanilla-Groessen als Plausibilitaets-Anker (8 RSQ-Timer, 24 h)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize,
                              WEAPON_PARAMS, WEAPON_AIMTIME_KEYS)
from s2tweaker import cfgparse

gd = GameData(VANILLA)

# --- 1) Quest-Timer-Inventar --------------------------------------------
timers = gd.repeatable_quest_timers()
assert len(timers) == 8, f"8 RSQ-Timer erwartet, {len(timers)} gefunden"
assert all(v == 24 for v in timers.values()), timers
assert all(sid.startswith("RSQ") or "RSQ" in sid for sid in timers), timers
print(f"Inventar: {len(timers)} RSQ-SetTimer, alle 24 h  OK")

# --- 2) Cooldown 25 % -> 6 h, nur RSQ-Knoten ----------------------------
p = build_patches(gd, Settings(repeatable_quest_factor=0.25))
key = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"
assert list(p) == [key], list(p)
root = cfgparse.parse_text(p[key]) if hasattr(cfgparse, "parse_text") else None
text = p[key]
assert text.count("InGameHours = 6") == 8, text
for sid in timers:
    assert sid in text, f"{sid} fehlt im Patch"
# Kein Nicht-RSQ-Knoten im Patch (Story-Timer sind tabu)
for line in text.splitlines():
    if line and not line.startswith((" ", "struct")):
        node = line.split(" :")[0]
        assert node in timers, f"fremder Knoten im Patch: {node}"
print("Cooldown x0.25: 8 Knoten auf 6 h, keine Story-Timer  OK")

# --- 3) Faktor 0 = sofort; 100 % = kein Patch; negativ = kein Patch -----
p0 = build_patches(gd, Settings(repeatable_quest_factor=0.0))
assert p0[key].count("InGameHours = 0") == 8
assert not build_patches(gd, Settings(repeatable_quest_factor=1.0))
assert not build_patches(gd, Settings(repeatable_quest_factor=-1.0))
assert any("Repeatable quest cooldown" in line
           for line in summarize(Settings(repeatable_quest_factor=0.5)))
print("Cooldown-Randfaelle (0 / 100 % / negativ) + summarize  OK")

# --- 4) ADS aim-in: global x2 halbiert alle vier Zeiten -----------------
assert "aimtime" in WEAPON_PARAMS and len(WEAPON_PARAMS) == 9
p = build_patches(gd, Settings(aim_time_factor=2.0))
wgs_key = ("WeaponData/WeaponGeneralSetupPrototypes/"
           "WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg")
# Seit den Editions-Waffen (02.09.) duerfen zusaetzlich DLC-Patchdateien
# derselben WGS-Familie entstehen (deren Structs definieren Zeiten selbst)
assert wgs_key in p, list(p)
assert all(k == wgs_key
           or ("DLCGameData" in k and "WeaponGeneralSetup" in k)
           for k in p), list(p)
text = p[wgs_key]
# TemplateWeapon definiert alle vier Zeiten (0.5/0.6/0.3/0.6) selbst
vanilla = {k: gd.weapon_general_values(k)["TemplateWeapon"]
           for k in WEAPON_AIMTIME_KEYS}
import re
block = re.search(r"^TemplateWeapon : struct.begin \{bpatch\}\n(.*?)^struct.end",
                  text, re.S | re.M).group(1)
for k, v in vanilla.items():
    m = re.search(rf"{k} = ([^\s;]+)", block)
    assert m and abs(float(m.group(1)) - v / 2) < 1e-9, (k, v, m and m.group(1))
n_structs = sum(1 for line in text.splitlines()
                if line and not line.startswith((" ", "struct")))
assert n_structs >= 90, f"nur {n_structs} Structs gepatcht (92 definieren selbst)"
print(f"ADS global x2: TemplateWeapon-Zeiten halbiert, {n_structs} Structs  OK")

# --- 5) Kaskade: Kategorie-Faktor nur fuer die Kategorie ----------------
p = build_patches(gd, Settings(
    weapon_category_factors={"rifle": {"aimtime": 2.0}}))
text = p[wgs_key]
rifle_vals = {s for s, _v in gd.weapon_general_values("AimingTime").items()
              if gd.weapon_category(s) == "rifle"}
assert "GunAK74_ST" in text and "TemplateRifle" in text
pistols = [s for s in gd.weapon_general_values("AimingTime")
           if gd.weapon_category(s) == "pistol" and s in text]
assert not pistols, f"Pistolen betroffen: {pistols[:3]}"
# Einzelwaffen-Override schlaegt Kategorie
p = build_patches(gd, Settings(
    weapon_category_factors={"rifle": {"aimtime": 2.0}},
    weapon_overrides={"GunAK74_ST": {"aimtime": 4.0}}))
m = re.search(r"^GunAK74_ST : struct.begin \{bpatch\}\n(.*?)^struct.end",
              p[wgs_key], re.S | re.M)
ak_vanilla = gd.weapon_general_values("AimingTime")["GunAK74_ST"]
am = re.search(r"AimingTime = ([^\s;]+)", m.group(1))
assert abs(float(am.group(1)) - ak_vanilla / 4) < 1e-9, am.group(1)
print("ADS-Kaskade: Kategorie nur rifle, Override x4 schlaegt x2  OK")

print("\nQUEST/ADS-TEST OK")
