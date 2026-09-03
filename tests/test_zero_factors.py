"""Regler auf 0 %: Recoil/Spread muessen wirklich patchen.

Nexus-Bug (Koningkoen, 02.09.2026): "Weapon recoil 0 %" hatte keine
Wirkung. Ursache: die Waffen-Builder uebersprangen JEDEN Faktor <= 0
(Schutz vor Division durch null bei invertierten Werten wie Feuerrate)
- 0 % erzeugte darum gar keinen Patch; "Weapon spread 0 %" ebenso,
obwohl der Tooltip "laser accuracy" verspricht. Jetzt gilt: 0 ist fuer
multiplikative Werte erlaubt, invertierte (Feuerrate, Haltbarkeit,
ADS-Zeit) und negative Faktoren bleiben tabu. Sollmengen werden live
aus den Vanilla-Daten abgeleitet, nichts ist hardcodiert.
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
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)
WGS = ("WeaponData/WeaponGeneralSetupPrototypes/"
       "WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg")
CWS = ("WeaponData/CharacterWeaponSettingsPrototypes/"
       "CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg")


def values_by_struct(text: str, key: str) -> dict[str, str]:
    """{Top-Level-SID: Wert} fuer jede Zeile `key = wert` im Patch."""
    out, cur = {}, None
    for line in text.splitlines():
        if line and not line.startswith((" ", "struct")):
            cur = line.split(" :")[0]
            continue
        m = re.match(r"\s+" + re.escape(key) + r" = (\S+)", line)
        if m and cur:
            out[cur] = m.group(1)
    return out


# --- 1) Recoil 0 %: jeder selbst definierende Struct auf 0 ------------
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
    assert hits, f"DLC {ed}/{sid} ohne RecoilRadius-0-Patch"
assert any("Weapon recoil" in line
           for line in summarize(Settings(recoil_factor=0.0)))
print(f"Recoil 0 %: {len(got)} Basis-Structs + DLC auf RecoilRadius 0  OK")

# --- 2) Spread 0 %: Erstschuss (WGS) + Streuung (CWS) auf 0 -----------
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
print(f"Spread 0 %: {len(got)} Erstschuss- + {len(got_cws)} "
      "Streuungs-Structs auf 0  OK")

# --- 3) Guards bleiben: invertierte Werte und negative Faktoren --------
assert not build_patches(gd, Settings(
    weapon_category_factors={"rifle": {"firerate": 0.0}})), \
    "Feuerrate 0 darf nicht teilen"
assert not build_patches(gd, Settings(durability_factor=0.0))
assert not build_patches(gd, Settings(aim_time_factor=0.0))
assert not build_patches(gd, Settings(recoil_factor=-1.0))
assert not build_patches(gd, Settings(spread_factor=-0.5))
# 100 % bleibt neutral
assert not build_patches(gd, Settings(recoil_factor=1.0, spread_factor=1.0))
print("Guards: Feuerrate/Haltbarkeit/ADS-Zeit 0 und negative Faktoren "
      "-> kein Patch  OK")

print("\nZERO-FACTORS-TEST OK")
