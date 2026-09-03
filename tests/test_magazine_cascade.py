"""Magazingroesse als 10. Kaskaden-Parameter (Nexus-Wunsch Qfander, 03.09.2026).

Einzelwaffe > Kategorie > globaler Regler fuer (a) den Basiswert MaxAmmo im
WeaponGeneralSetup und (b) die Magazin-Aufsaetze (Magazine.MaxAmmo), die
ueber WeaponReloadTimePerAttachment der Waffe zugeordnet werden. Sollwerte
werden live aus vanilla/ gelesen; als Plausibilitaets-Anker dienen nur die
bekannten AK74-Magazine (30 / 45 / 30).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize,
                              WEAPON_PARAMS, WEAPON_PARAM_LABELS)

gd = GameData(VANILLA)
WGS = ("WeaponData/WeaponGeneralSetupPrototypes/"
       "WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg")
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"


def mag_values(text: str) -> dict[str, int]:
    """{Item-SID: Magazine.MaxAmmo} aus einem ItemPrototypes-Patch."""
    out = {}
    for m in re.finditer(r"^(\S+) : struct.begin \{bpatch\}\n   Magazine : "
                         r"struct.begin \{bpatch\}\n      MaxAmmo = (\d+)",
                         text, re.M):
        out[m.group(1)] = int(m.group(2))
    return out


def wgs_values(text: str) -> dict[str, int]:
    out = {}
    for m in re.finditer(r"^(\S+) : struct.begin \{bpatch\}\n(.*?)^struct.end",
                         text, re.S | re.M):
        mm = re.search(r"MaxAmmo = (\d+)", m.group(2))
        if mm:
            out[m.group(1)] = int(mm.group(1))
    return out


# --- 1) Parameter + Zuordnung Waffe -> Magazine -------------------------
assert WEAPON_PARAMS[-1] == "magazine" and len(WEAPON_PARAMS) == 10
assert WEAPON_PARAM_LABELS["magazine"] == "Magazine size"
mags = gd.magazine_items()
wm = gd.weapon_magazines()
assert len(mags) >= 70, len(mags)
assert set(wm["GunAK74_ST"]) == {"GunAK74_MagDefault", "GunAK74_MagIncreased",
                                 "GunAK_MagPaired"}, wm["GunAK74_ST"]
assert mags["GunAK74_MagDefault"] == 30 and mags["GunAK74_MagIncreased"] == 45
used = {m for lst in wm.values() for m in lst}
orphans = sorted(set(mags) - used)
assert len(orphans) <= 10, orphans          # Unikate ohne Listeneintrag
assert all(sid in wm for sid in ("GunM16_ST", "GunPKP_MG", "GunAPB_HG")), \
    [s for s in ("GunM16_ST", "GunPKP_MG", "GunAPB_HG") if s not in wm]
shared = [m for m, ws in
          {m: [w for w, l in wm.items() if m in l] for m in used}.items()
          if len(ws) > 1]
assert "GunAK_MagPaired" in shared
print(f"Zuordnung: {len(wm)} Waffen, {len(used)}/{len(mags)} Magazine, "
      f"{len(orphans)} Waisen, {len(shared)} geteilte  OK")

# --- 2) Global x2 (unveraendertes Verhalten): alle Magazine -------------
p = build_patches(gd, Settings(magazine_factor=2.0))
got = mag_values(p[ITEMS])
assert set(got) == set(mags), set(mags) ^ set(got)
for sid, v in mags.items():
    assert got[sid] == max(1, int(round(v * 2))), (sid, v, got[sid])
base_defined = gd.weapon_general_values("MaxAmmo")
assert set(wgs_values(p[WGS])) == set(base_defined), set(base_defined) ^ set(wgs_values(p[WGS]))
print(f"Global x2: {len(got)} Magazine + {len(base_defined)} WGS-Basiswerte  OK")

# --- 3) Einzelwaffe: nur AK74 (+ ihr geteiltes Paar-Magazin) -------------
s = Settings(weapon_overrides={"GunAK74_ST": {"magazine": 2.0}})
p = build_patches(gd, s)
got = mag_values(p[ITEMS])
assert got == {"GunAK74_MagDefault": 60, "GunAK74_MagIncreased": 90,
               "GunAK_MagPaired": 60}, got
ak_base = parse_number(gd.resolve(gd.weapongeneral, "GunAK74_ST", "MaxAmmo"))
assert wgs_values(p[WGS]) == {"GunAK74_ST": int(round(ak_base * 2))}, wgs_values(p[WGS])
assert any("magazine size" in line and "AK" in line for line in summarize(s)), summarize(s)
print("Einzelwaffe AK74 x2: 3 Magazine + eigener MaxAmmo, sonst nichts  OK")

# --- 4) Kategorie: alle Sturmgewehr-Magazine, keine Pistole --------------
p = build_patches(gd, Settings(weapon_category_factors={"rifle": {"magazine": 2.0}}))
got = mag_values(p[ITEMS])
rifle_mags = {m for w, l in wm.items() if gd.weapon_category(w) == "rifle" for m in l}
pistol_only = {m for w, l in wm.items() if gd.weapon_category(w) == "pistol"
               for m in l} - rifle_mags
assert rifle_mags <= set(got), rifle_mags - set(got)
assert not (pistol_only & set(got)), pistol_only & set(got)
assert "GunAK74_MagDefault" in got and "GunAPB_MagDefault" not in got
print(f"Kategorie rifle x2: {len(got)} Magazine, Pistolen unangetastet  OK")

# --- 5) Kaskade: Override schlaegt Kategorie, Kategorie schlaegt global ---
p = build_patches(gd, Settings(
    magazine_factor=3.0,
    weapon_category_factors={"rifle": {"magazine": 2.0}},
    weapon_overrides={"GunAK74_ST": {"magazine": 0.5}}))
got = mag_values(p[ITEMS])
assert got["GunAK74_MagDefault"] == 15 and got["GunAK74_MagIncreased"] == 22, got
assert got["GunM16_MagDefault"] == mags["GunM16_MagDefault"] * 2
assert got["GunAPB_MagDefault"] == mags["GunAPB_MagDefault"] * 3
print("Kaskade: AK74 x0.5 < rifle x2 < global x3  OK")

# --- 6) Neutral + Untergrenze ---------------------------------------------
assert not build_patches(gd, Settings())
assert not build_patches(gd, Settings(weapon_overrides={"GunAK74_ST": {"magazine": 1.0}}))
p = build_patches(gd, Settings(weapon_overrides={"GunAK74_ST": {"magazine": 0.01}}))
assert mag_values(p[ITEMS])["GunAK74_MagDefault"] == 1
print("Neutral = kein Patch, Untergrenze 1 Schuss  OK")

print("\nMAGAZINE-CASCADE-TEST OK")
