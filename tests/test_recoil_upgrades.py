"""Regler "Recoil reduction from upgrades" (03.09.2026, Wunsch des Besitzers
nach der Recoil-Recherche).

Community-Weg der Nexus-Mod "Dead Steady" (2478, auf Patch 2.0
bestaetigt): die rueckstosssenkenden Upgrade-/Attachment-Effekte
(EEffectType::Recoil mit negativem Prozentwert) werden verstaerkt, Deckel
bei -100 %. Positive Recoil-Effekte (Munitionsumbauten, Muedigkeit)
bleiben unangetastet. Sollmengen live aus vanilla/, nichts hardcodiert
ausser den bekannten Vanilla-Groessen als Plausibilitaets-Anker.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)
KEY = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"


def pct(raw: str) -> float:
    return float(raw.strip()[:-1])


# --- 1) Inventar: negative und positive Recoil-Effekte ------------------
recoil = {sid: node for sid, node in gd.effects.children.items()
          if "#" not in sid
          and node.values.get("Type") == "EEffectType::Recoil"}
neg = {sid: pct(n.values["ValueMin"]) for sid, n in recoil.items()
       if pct(n.values["ValueMin"]) < 0}
pos = {sid: pct(n.values["ValueMin"]) for sid, n in recoil.items()
       if pct(n.values["ValueMin"]) >= 0}
assert len(neg) >= 10, neg
assert len(pos) >= 3, pos
assert "RecoilPos10Effect" in neg and "RecoilNeg20Effect" in pos
assert all(n.values["ValueMin"] == n.values["ValueMax"] for n in recoil.values())
print(f"Inventar: {len(neg)} senkende ({min(neg.values()):g} .. "
      f"{max(neg.values()):g} %), {len(pos)} erhoehende Recoil-Effekte  OK")


def patched_values(text: str) -> dict[str, tuple[float, float]]:
    out = {}
    for m in re.finditer(r"^(\S+) : struct.begin \{bpatch\}\n(.*?)^struct.end",
                         text, re.S | re.M):
        body = m.group(2)
        vmin = re.search(r"ValueMin = (\S+)", body)
        vmax = re.search(r"ValueMax = (\S+)", body)
        assert vmin and vmax, m.group(1)
        out[m.group(1)] = (pct(vmin.group(1)), pct(vmax.group(1)))
    return out


# --- 2) x2: jeder senkende Effekt verdoppelt, sonst nichts --------------
p = build_patches(gd, Settings(recoil_upgrade_factor=2.0))
assert list(p) == [KEY], list(p)
got = patched_values(p[KEY])
assert set(got) == set(neg), set(got) ^ set(neg)
for sid, vanilla in neg.items():
    assert got[sid] == (vanilla * 2, vanilla * 2), (sid, vanilla, got[sid])
assert not (set(got) & set(pos)), "erhoehende Effekte duerfen nicht angefasst werden"
print(f"x2: {len(got)} Effekte verdoppelt (z. B. RecoilPos10Effect -> "
      f"{got['RecoilPos10Effect'][0]:g} %), positive unangetastet  OK")

# --- 3) x20 und x100: alles auf -100 % gedeckelt ------------------------
for factor in (20.0, 100.0):
    got = patched_values(build_patches(
        gd, Settings(recoil_upgrade_factor=factor))[KEY])
    assert set(got) == set(neg)
    assert all(v == (-100.0, -100.0) for v in got.values()), got
print("x20 / x100: alle senkenden Effekte auf -100 % gedeckelt  OK")

# --- 4) x4: -5 -> -20, -30 -> -100 (Deckel greift nur wo noetig) --------
got = patched_values(build_patches(gd, Settings(recoil_upgrade_factor=4.0))[KEY])
for sid, vanilla in neg.items():
    assert got[sid][0] == max(-100.0, vanilla * 4), (sid, vanilla, got[sid])
print("x4: gemischt skaliert/gedeckelt  OK")

# --- 5) Neutral, negativ, summarize ------------------------------------
assert not build_patches(gd, Settings(recoil_upgrade_factor=1.0))
assert not build_patches(gd, Settings(recoil_upgrade_factor=-2.0))
assert any("Recoil reduction from upgrades" in line
           for line in summarize(Settings(recoil_upgrade_factor=20.0)))
assert not [line for line in summarize(Settings())
            if "Recoil reduction" in line]
# Stapelt sauber mit dem Artefakt-Regler in derselben Patch-Datei
p = build_patches(gd, Settings(recoil_upgrade_factor=2.0,
                               artifact_effect_factor=2.0))
assert "RecoilPos10Effect" in p[KEY] and "Artifact" in p[KEY]
print("Neutral/negativ = kein Patch, summarize, Koexistenz mit Artefakt-Regler  OK")

print("\nRECOIL-UPGRADES-TEST OK")
