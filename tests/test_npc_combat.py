"""NPC-Kampfverhalten (Vorbild Nexus 2396 'Grounded Combat', 03.09.2026):
Garantietreffer, Feuerstoss-Laenge, Pausen, Gefechtsreichweite
(WeaponAttributesPrototypes *_NPC.AIParameters), NPC-Waffenreichweite
(CWS *_NPC) und NPC-Regen als Faktor (ObjPrototypes). Sollwerte live aus
vanilla/, Anker: AK74-NPC Newbie Long 2/3 Garantietreffer, 3-6 Schuss.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import cfgparse
from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize,
                              WEAPON_RANGE_KEYS)

gd = GameData(VANILLA)
WA = ("WeaponData/WeaponAttributesPrototypes/"
      "WeaponAttributesPrototypes_patch_S2Tweaker.cfg")
CWS = ("WeaponData/CharacterWeaponSettingsPrototypes/"
       "CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg")
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
npc_wa = [s for s in gd.weaponattributes.children if s.endswith("_NPC") and "#" not in s]
assert len(npc_wa) >= 70, len(npc_wa)


def vanilla_block(sid, rank, dist):
    return (gd.weaponattributes.children[sid].children["AIParameters"]
            .children["BehaviorTypes"].children[rank].children[dist].values)


def leaves(root, key):
    out = []

    def walk(node, path):
        for k, v in node.values.items():
            if k == key:
                out.append((path, v))
        for k, c in node.children.items():
            walk(c, path + [k])
    walk(root, [])
    return out


ak = vanilla_block("GunAK74_ST_NPC", "Newbie", "Long")
assert ak["IgnoreDispersionMinShots"] == "2" and ak["IgnoreDispersionMaxShots"] == "3"
assert ak["MinShots"] == "3" and ak["MaxShots"] == "6"

# --- 1) Garantietreffer 0 %: alle nicht-0-Bloecke auf 0, nur die ---------
p = build_patches(gd, Settings(npc_free_shots_factor=0.0))
assert list(p) == [WA], list(p)
root = cfgparse.parse(p[WA])
vals = leaves(root, "IgnoreDispersionMaxShots") + leaves(root, "IgnoreDispersionMinShots")
assert vals and all(v == "0" for _p, v in vals)
n_nonzero = sum(1 for s in npc_wa for rn in gd.weaponattributes.children[s].children["AIParameters"].children["BehaviorTypes"].children.values()
                for dn in rn.children.values()
                if parse_number(dn.values.get("IgnoreDispersionMaxShots")) > 0 or parse_number(dn.values.get("IgnoreDispersionMinShots")) > 0)
assert len(leaves(root, "IgnoreDispersionMaxShots")) == n_nonzero, (len(leaves(root, "IgnoreDispersionMaxShots")), n_nonzero)
assert set(root.children) <= set(npc_wa)
# Schrotflinten-Bloecke mit Vanilla 0 fehlen im Patch (0 bleibt 0)
print(f"Garantietreffer 0 %: {n_nonzero} Distanz-Bloecke auf 0, Vanilla-Nullen tabu  OK")

# --- 2) Garantietreffer x1.5: Deckel = Feuerstoss-Laenge, Min <= Max ------
p = build_patches(gd, Settings(npc_free_shots_factor=1.5))
root = cfgparse.parse(p[WA])
blk = root.children["GunAK74_ST_NPC"].children["AIParameters"].children["BehaviorTypes"]
long_ = blk.children["Newbie"].children["Long"].values
exp_min, exp_max = int(round(2 * 1.5)), int(round(3 * 1.5))     # Python-Rundung wie im Builder
assert long_ == {"IgnoreDispersionMinShots": str(exp_min), "IgnoreDispersionMaxShots": str(exp_max)}, long_
for path, vmax in leaves(root, "IgnoreDispersionMaxShots"):
    sid, rank, dist = path[0], path[3], path[4]
    van = vanilla_block(sid, rank, dist)
    assert int(vmax) <= int(parse_number(van["MaxShots"])), (path, vmax, van["MaxShots"])
print("Garantietreffer x1.5: gedeckelt durch Feuerstoss-Laenge  OK")

# --- 3) Feuerstoss x0.5, Pausen x2, Gefechtsreichweite x0.5 ---------------
p = build_patches(gd, Settings(npc_burst_factor=0.5))
blk = cfgparse.parse(p[WA]).children["GunAK74_ST_NPC"].children["AIParameters"].children["BehaviorTypes"]
assert blk.children["Newbie"].children["Long"].values == {"MinShots": "2", "MaxShots": "3"}
assert blk.children["Newbie"].children["Short"].values == {"MinShots": "4", "MaxShots": "8"}
p = build_patches(gd, Settings(npc_fire_pause_factor=2.0))
blk = cfgparse.parse(p[WA]).children["GunAK74_ST_NPC"].children["AIParameters"].children["BehaviorTypes"]
nb = blk.children["Newbie"]
assert nb.values["NonAutomaticWeaponShotDelay"] == "0.4"
assert nb.children["Long"].values == {"MinSecondsDelay": "2.4", "MaxSecondsDelay": "3.0"}, nb.children["Long"].values
p = build_patches(gd, Settings(npc_engage_range_factor=0.5))
root = cfgparse.parse(p[WA])
nb = root.children["GunAK74_ST_NPC"].children["AIParameters"].children["BehaviorTypes"].children["Newbie"]
assert nb.values == {"CombatEffectiveFireDistanceMin": "750.0", "CombatEffectiveFireDistanceMax": "3000.0"}, nb.values
assert not nb.children                                    # nur Rang-Ebene
assert "Zombie" in root.children["GunAK74_ST_NPC"].children["AIParameters"].children["BehaviorTypes"].children
print("Feuerstoss x0.5 / Pausen x2 / Gefechtsreichweite x0.5: AK74 korrekt, Zombie-Rang dabei  OK")

# --- 4) NPC-Waffenreichweite x0.5: vier Schluessel, nur *_NPC ------------
p = build_patches(gd, Settings(npc_weapon_range_factor=0.5))
assert list(p) == [CWS]
root = cfgparse.parse(p[CWS])
assert all("_NPC" in s for s in root.children)
ak_cws = root.children["GunAK74_ST_NPC"].values
for key in WEAPON_RANGE_KEYS:
    van = parse_number(gd.resolve(gd.weaponsettings, "GunAK74_ST_NPC", key))
    assert abs(parse_number(ak_cws[key]) - van / 2) < 1e-6, (key, ak_cws[key], van)
assert "DispersionRadius" not in ak_cws
print(f"NPC-Waffenreichweite x0.5: {len(root.children)} NPC-Profile, 4 Schluessel  OK")

# --- 5) NPC-Regen x0.25, Checkbox gewinnt --------------------------------
regen = gd.npcs_with_regen()
p = build_patches(gd, Settings(npc_regen_factor=0.25))
root = cfgparse.parse(p[OBJ])
assert set(root.children) == set(regen)
for sid, van in list(regen.items())[:50]:
    got = parse_number(root.children[sid].children["VitalParams"].values["RegenHP"])
    assert abs(got - van * 0.25) < 1e-6, (sid, van, got)
p = build_patches(gd, Settings(npc_regen_factor=0.25, npc_no_heal=True))
root = cfgparse.parse(p[OBJ])
assert all(n.children["VitalParams"].values["RegenHP"] == "0.0" for n in root.children.values())
assert not [l for l in summarize(Settings(npc_regen_factor=0.25, npc_no_heal=True)) if "health regen" in l]
print(f"NPC-Regen x0.25: {len(regen)} Prototypen, Checkbox gewinnt  OK")

# --- 6) Neutral + Kombination --------------------------------------------
assert not build_patches(gd, Settings())
s = Settings(npc_free_shots_factor=0.5, npc_burst_factor=1.5, npc_fire_pause_factor=1.5,
             npc_engage_range_factor=0.75, npc_weapon_range_factor=0.75, npc_regen_factor=0.5)
p = build_patches(gd, s)
assert set(p) == {WA, CWS, OBJ}
assert sum(1 for l in summarize(s) if l.startswith("NPC ")) == 6, summarize(s)
print("Neutral = kein Patch, Kombination -> 3 Dateien, 6 Summary-Zeilen  OK")

print("\nNPC-COMBAT-TEST OK")
