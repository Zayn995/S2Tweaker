"""v1.18-Paket (Nexus-Beliebtheits-Recherche 03.09.2026): Tageslaenge,
Wirkdauer von Verbrauchsguetern, Artefakte je Feld + Respawn, Quest-Items
ohne Gewicht. Sollwerte live aus vanilla/; Anker sind nur die bekannten
Vanilla-Groessen (RealToGameTimeCoef 24, Energydrink 45 s, Count 1, Cooldown
3/15).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import cfgparse
from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
EFF = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"
ART = "ArtifactSpawnerPrototypes/ArtifactSpawnerPrototypes_patch_S2Tweaker.cfg"
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"


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


# --- 1) Tageslaenge ------------------------------------------------------
assert gd.corevar("RealToGameTimeCoef", 0) == 24
p = build_patches(gd, Settings(day_length_factor=2.0))
assert list(p) == [CORE], list(p)
assert "RealToGameTimeCoef = 12" in p[CORE] and "12." not in p[CORE], p[CORE]
p = build_patches(gd, Settings(day_length_factor=0.5))
assert "RealToGameTimeCoef = 48" in p[CORE]
p = build_patches(gd, Settings(day_length_factor=2.5))
assert "RealToGameTimeCoef = 9.6" in p[CORE]
print("Tageslaenge: 24 -> 12 / 48 / 9.6  OK")

# --- 2) Wirkdauer: nur laufende, nicht-negative Consumable-Effekte -------
dur = gd.consumable_duration_effects()
assert 8 <= len(dur) <= 30, len(dur)
assert "EnergeticStamina" in dur and "HerculesWeight" in dur
assert "MedkitHealing3" not in dur and "Antirad4" not in dur   # 1-2 s = Sofort
assert "VodkaStaminaPenalty" not in dur                        # Negative
assert all(parse_number(v) >= 10 for v in dur.values())
p = build_patches(gd, Settings(consumable_duration_factor=3.0))
assert list(p) == [EFF], list(p)
root = cfgparse.parse(p[EFF])
assert set(root.children) == set(dur), set(root.children) ^ set(dur)
assert root.children["EnergeticStamina"].values["Duration"] == "135.0"
assert root.children["HerculesWeight"].values["Duration"] == "900.0f"
print(f"Wirkdauer x3: {len(dur)} laufende Effekte, Sofort-/Malus-Effekte tabu  OK")

# --- 3) Artefakte je Feld + Respawn --------------------------------------
spawners = [s for s in gd.artifactspawners.children if s != "Empty" and "#" not in s]
p = build_patches(gd, Settings(artifact_count_factor=2.0))
assert list(p) == [ART]
root = cfgparse.parse(p[ART])
counts = leaves(root, "Count")
n_blocks = sum(1 for s in spawners for r in gd.artifactspawners.children[s].children.values()
               if parse_number(r.values.get("Count")) > 0)
assert len(counts) == n_blocks and all(v == "2" for _p, v in counts), (len(counts), n_blocks)
assert "Empty" not in root.children
p = build_patches(gd, Settings(artifact_count_factor=5.0))
assert all(v == "5" for _p, v in leaves(cfgparse.parse(p[ART]), "Count"))
p = build_patches(gd, Settings(artifact_respawn_factor=2.0))
root = cfgparse.parse(p[ART])
cds = leaves(root, "MinCooldown") + leaves(root, "MaxCooldown")
assert cds and all(parse_number(v) > 0 for _p, v in cds)      # Nullen bleiben
chunk = root.children["ChunkMeatArtifactSpawner"].children["Newbie"].values
assert chunk["MinCooldown"] == "1.5f" and chunk["MaxCooldown"] == "7.5f", chunk
n_cd = sum(1 for s in spawners for r in gd.artifactspawners.children[s].children.values()
           if parse_number(r.values.get("MinCooldown")) > 0)
assert len(leaves(root, "MinCooldown")) == n_cd
print(f"Artefakte: {len(counts)} Rang-Bloecke Count 2, {n_cd} Cooldowns halbiert, Nullen tabu  OK")

# --- 4) Quest-Items ohne Gewicht -----------------------------------------
qw = gd.quest_items_with_weight()
assert len(qw) >= 250 and max(qw.values()) >= 10, (len(qw), max(qw.values()))
p = build_patches(gd, Settings(quest_items_weightless=True))
assert list(p) == [ITEMS]
root = cfgparse.parse(p[ITEMS])
assert set(root.children) == set(qw)
assert all(n.values == {"Weight": "0.0"} for n in root.children.values())
assert "GunAK74_ST" not in root.children and "Medkit" not in root.children
print(f"Quest-Items: {len(qw)} Items auf 0.0 kg, Rest unangetastet  OK")

# --- 5) Neutral + summarize ----------------------------------------------
assert not build_patches(gd, Settings())
s = Settings(day_length_factor=2.0, consumable_duration_factor=2.0,
             artifact_count_factor=3.0, artifact_respawn_factor=2.0,
             quest_items_weightless=True)
lines = summarize(s)
for needle in ("Day length", "Consumable effect duration", "Artifacts per anomaly field",
               "Artifact respawn speed", "Quest items weigh nothing"):
    assert any(needle in l for l in lines), (needle, lines)
assert set(build_patches(gd, s)) == {CORE, EFF, ART, ITEMS}
print("Neutral = kein Patch, 5 Summary-Zeilen, 4 Patch-Dateien  OK")

print("\nV118-TWEAKS-TEST OK")
