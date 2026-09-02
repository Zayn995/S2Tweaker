"""Editions-Waffen (PreOrder/Deluxe/Ultimate) im Waffen-Baum + DLC-Patches.

Ueberspringt sich selbst sauber, wenn vanilla/ (noch) keinen
DLCGameData-Zweig hat — auf so einem Rechner einmal die GUI laden lassen
(extrahiert die Editions-Paks mit) oder den Zweig aus dem Cache kopieren."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches
from s2tweaker.cfgparse import parse_number
from s2tweaker import pakio

gd = GameData(VANILLA)
if not gd.dlc_editions:
    print("SKIP: kein DLCGameData neben vanilla/GameData - Suite "
          "uebersprungen (kein Fehler).")
    sys.exit(0)

# --- 1) Inventar --------------------------------------------------------
dlc = gd.dlc_player_weapons()
eds = {ed for _c, _w, ed in dlc.values()}
assert eds == {"PreOrder", "Deluxe", "Ultimate"}, eds
assert "Gun_Gabion_AR_GS" in dlc, sorted(dlc)
cat, cws, ed = dlc["Gun_Gabion_AR_GS"]
assert ed == "Deluxe" and cat == "rifle", (cat, ed)
assert cws and cws in gd.weaponsettings.children, cws
# Skins mit Basis-Setup (Deluxe_GunAK74_ST -> GunAK74_ST) nicht doppelt
assert "GunAK74_ST" not in {s for s in dlc}, "Basis-Setup als DLC gelistet"
pw = gd.player_weapons()
assert "Gun_Gabion_AR_GS" in pw and pw["Gun_Gabion_AR_GS"][0] == "rifle"
print(f"Inventar: {len(dlc)} Editions-Waffen in {len(eds)} Editionen, "
      "Gabion=rifle, CWS in der Basis  OK")

# --- 2) Einzel-Override auf einer DLC-Waffe -> DLC-Patchdatei -----------
p = build_patches(gd, Settings(
    weapon_overrides={"Gun_Gabion_AR_GS": {"firerate": 2.0}}))
dlc_keys = [k for k in p if k.startswith("//GameLite/DLCGameData/Deluxe/")]
assert dlc_keys, list(p)
text = p[dlc_keys[0]]
vanilla_fi = parse_number(
    gd.dlc_resolve_weapon("Deluxe", "Gun_Gabion_AR_GS", "FireInterval"))
assert vanilla_fi > 0
import re
m = re.search(r"FireInterval = ([^\s;]+)", text)
assert m and abs(float(m.group(1)) - vanilla_fi / 2) < 1e-9, (
    m and m.group(1), vanilla_fi)
print(f"Gabion-Override x2: DLC-Patch {dlc_keys[0].split('/')[-1]}, "
      f"FireInterval {vanilla_fi} -> {m.group(1)}  OK")

# --- 3) Globaler Regler trifft selbst-definierte DLC-Werte --------------
p = build_patches(gd, Settings(aim_time_factor=2.0))
n_dlc = sum(1 for k in p if k.startswith("//GameLite/DLCGameData/"))
n_self = len(gd.dlc_weapon_general_values("AimingTime"))
if n_self:
    assert n_dlc >= 1, list(p)
print(f"Global aimtime x2: {n_self} selbst-definierte DLC-Zeiten, "
      f"{n_dlc} DLC-Patchdateien  OK")

# --- 4) Pak-Rundlauf: DLC-Pfad landet korrekt in der Pak ----------------
out = ROOT / "tests" / "_tmp" / "dlc_test.pak"
p = build_patches(gd, Settings(
    weapon_overrides={"Gun_Gabion_AR_GS": {"firerate": 2.0}}))
pakio.pack_mod(p, out)
names = pakio.list_pak(out)
assert any(n.startswith("Stalker2/Content/GameLite/DLCGameData/Deluxe/")
           for n in names), names
out.unlink(missing_ok=True)
print("Pak-Rundlauf: DLCGameData-Pfad korrekt gemountet  OK")

# --- 5) Neutral bleibt neutral ------------------------------------------
assert not build_patches(gd, Settings())
print("Neutral = kein Patch  OK")

print("\nDLC-WAFFEN-TEST OK")
