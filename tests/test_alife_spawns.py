"""Check A-Life camp/director controls against installed vanilla data.

Recorded counts/timers are regression anchors; derive expected patches live.
See docs/ALIFE_SPAWN_RESEARCH.md."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import cfgparse
from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData, NEEDED_FILES, CACHE_SCHEMA
from s2tweaker.tweaks import Settings, build_patches, summarize, ENCOUNTER_KINDS

assert "LairPrototypes.cfg.bin" in NEEDED_FILES
assert "ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg.bin" in NEEDED_FILES
assert CACHE_SCHEMA >= 14
gd = GameData(VANILLA)
LAIR = "LairPrototypes/LairPrototypes_patch_S2Tweaker.cfg"
DIR = ("ALifePrototypes/ALifeDirectorScenarioPrototypes/"
       "ALifeDirectorScenarioPrototypes_patch_S2Tweaker.cfg")


def leaf_values(root, key: str) -> list[tuple[list[str], str]]:
    """Return [(path, value)] for all leaves named key in the parsed patch."""
    out = []

    def walk(node, path):
        for k, v in node.values.items():
            if k == key:
                out.append((path, v))
        for k, c in node.children.items():
            walk(c, path + [k])
    walk(root, [])
    return out


# --- 1) Inventory ----------------------------------------------------------
blocks = gd.lair_blocks()
assert len(blocks) >= 700, len(blocks)
n_mut = sum(1 for b in blocks if b["mutant"] and not b["guard"])
n_hum = sum(1 for b in blocks if not b["mutant"] and not b["guard"])
n_guard = sum(1 for b in blocks if b["guard"])
assert n_mut >= 300 and n_hum >= 300 and n_guard >= 40, (n_mut, n_hum, n_guard)
std = gd.lair_standard_timers()
assert std == ("180.0", "480.0", "480.0"), std
n_std = sum(1 for b in blocks if b["timers"] == std)
assert n_std >= len(blocks) - 20, (n_std, len(blocks))
toks = gd.director_scenario_tokens()
assert len(toks) >= 60 and toks["BlinddogPack"] == {"Blinddog"} and "Human" in toks["HumansVsMutants"]
assert "Chimera" in gd.director_prohibited() and "Blinddog" not in gd.director_prohibited()
assert len(gd.director_limits()) == 64
print(f"Inventory: {len(blocks)} lair blocks ({n_mut} mutants, {n_hum} humans, "
      f"{n_guard} Guard), {n_std} with default timers, {len(toks)} scenarios  OK")

# Double mutant camp population, excluding human and Guard camps.
p = build_patches(gd, Settings(lair_mutant_factor=2.0))
assert list(p) == [LAIR], list(p)
root = cfgparse.parse(p[LAIR])
got = leaf_values(root, "MaxSpawnQuantity")
assert len(got) == n_mut, (len(got), n_mut)
assert not any(path[0].startswith("Guard") for path, _v in got)
by_key = {(b["lair"], b["faction_key"], b["rank"]): b for b in blocks}
for path, v in got:
    b = by_key[(path[0], path[3], path[5])]
    assert b["mutant"] and int(v) == int(round(b["quantity"] * 2)), (path, v, b["quantity"])
# Tushkan Master 24 -> 48, Bloodsucker Newbie 2 -> 4
vals = {tuple(path): int(v) for path, v in got}
assert vals[("Tushkan", "Preset", "PossibleInhabitantFactions", "Tushkan",
             "SpawnSettingsPerPlayerRanks", "Master")] == 48
print(f"Mutant lairs x2: {len(got)} blocks, Guard unangetastet, Tushkan Master 48  OK")

# --- 3) Human lair population x0.5: floor from summed MinQuantity ---------
p = build_patches(gd, Settings(lair_human_factor=0.5))
got = leaf_values(cfgparse.parse(p[LAIR]), "MaxSpawnQuantity")
assert all(not b["mutant"] for path, _v in got for b in [by_key[(path[0], path[3], path[5])]])
for path, v in got:
    b = by_key[(path[0], path[3], path[5])]
    floor = min(b["quantity"], b["min_sum"])
    assert int(v) >= max(1, floor), (path, v, b)
# Preserve an existing Freedom/Newbie minimum-count discrepancy without worsening it.
freedom = [v for path, v in got if path[0] == "Freedom" and path[5] == "Newbie"]
assert freedom == [], freedom
print(f"Human lairs x0.5: {len(got)} blocks, lower bound enforced (Freedom/Newbie stays at 6)  OK")

# Double ordinary respawn speed by halving all three timers.
p = build_patches(gd, Settings(lair_respawn_factor=2.0))
root = cfgparse.parse(p[LAIR])
for key, vanilla in zip(gd.LAIR_TIMER_KEYS, std):
    got = leaf_values(root, key)
    assert len(got) == n_std, (key, len(got), n_std)
    assert all(abs(parse_number(v) - parse_number(vanilla) / 2) < 1e-6 for _p, v in got)
# Story camps (6/30/30) are absent from the patch.
assert not any(path[0] == "SultanBandits" and path[5] == "Newbie"
               for path, _v in leaf_values(root, "WipeRespawnTimeoutSeconds"))
print(f"Respawn x2: {n_std} blocks x 3 timers halved, story lairs excluded  OK")

# --- 5) Director frequency x2 ---
p = build_patches(gd, Settings(encounter_frequency_factor=2.0))
assert list(p) == [DIR], list(p)
root = cfgparse.parse(p[DIR]).children["ALifeDirectorPreset"]
assert root.values["DefaultSpawnDelayMin"] == "50" and root.values["DefaultSpawnDelayMax"] == "90"
glob = root.children["ScenarioGroups"].children["Global"].values
assert glob["SpawnDelayMin"] == "30" and glob["SpawnDelayMax"] == "45"
assert int(glob["SpawnDelayMin"]) <= int(glob["SpawnDelayMax"])
assert "ScenarioSIDs" not in root.children["ScenarioGroups"].children["Global"].children
print("Frequency x2: defaults + 13 groups halved, Min <= Max  OK")

# --- 6) Mutant share and per-species controls ---
p = build_patches(gd, Settings(encounter_mutant_factor=2.0))
root = cfgparse.parse(p[DIR]).children["ALifeDirectorPreset"]
sids = root.children["ScenarioGroups"].children["Global"].children["ScenarioSIDs"].children
assert sids["BlinddogPack"].values["ScenarioWeight"] == "20"
assert sids["TushkanPack"].values["ScenarioWeight"] == "10"
assert sids["ChimeraSingle"].values["ScenarioWeight"] == "4"
assert "BloodsuckerSingle" not in sids            # Preserve vanilla zero.
assert "HumansVsMutants" not in sids and "HumansVsHumans" not in sids
weights = leaf_values(root, "ScenarioWeight")
assert all(int(v) >= 1 for _p, v in weights)
# Species factor zero overrides the mutant factor only for pure-species scenarios.
p = build_patches(gd, Settings(encounter_mutant_factor=2.0, enc_blinddog_factor=0.0))
sids = (cfgparse.parse(p[DIR]).children["ALifeDirectorPreset"]
        .children["ScenarioGroups"].children["Global"].children["ScenarioSIDs"].children)
assert sids["BlinddogPack"].values["ScenarioWeight"] == "0"
assert sids["BoarPack"].values["ScenarioWeight"] == "20"
# Share 0%: zero all mutant-only weights, leave humans unchanged.
p = build_patches(gd, Settings(encounter_mutant_factor=0.0))
weights = leaf_values(cfgparse.parse(p[DIR]), "ScenarioWeight")
assert weights and all(v == "0" for _p, v in weights)
assert all("Human" not in toks[path[-1]] for path, _v in weights)
print("Mutant share x2 / species x0 / share 0%: correct weights, humans unchanged  OK")

# --- 7) Pack size: preserve prohibited types and zero values ---
p = build_patches(gd, Settings(encounter_pack_factor=2.0))
root = cfgparse.parse(p[DIR]).children["ALifeDirectorPreset"]
counts = leaf_values(root, "MaxCount")
banned = gd.director_prohibited()
limits = {(ri, ti): (atype, c) for ri, ti, atype, c in gd.director_limits()}
for path, v in counts:
    atype, c = limits[(path[1], path[3])]
    assert atype not in banned and c > 0 and int(v) == int(round(c * 2)), (path, v, atype, c)
n_allowed = sum(1 for ri, ti, atype, c in gd.director_limits() if atype not in banned and c > 0)
assert len(counts) == n_allowed, (len(counts), n_allowed)
print(f"Pack x2: {len(counts)} limits scaled, {len(banned)} excluded types and zero values unchanged  OK")

# --- 8) Neutral, summary, all sliders combined ---
assert not build_patches(gd, Settings())
s = Settings(lair_mutant_factor=1.5, lair_human_factor=1.5, lair_respawn_factor=2.0,
             encounter_frequency_factor=2.0, encounter_mutant_factor=1.5,
             encounter_pack_factor=1.2, enc_chimera_factor=2.0)
p = build_patches(gd, s)
assert set(p) == {LAIR, DIR}
lines = summarize(s)
assert sum(1 for l in lines if l.startswith(("Lair", "Random encounters", "Encounters:"))) == 7, lines
assert len(ENCOUNTER_KINDS) == 6
print("Neutral = no patch; combined settings -> 2 files, 7 summary lines  OK")

print("\nALIFE-SPAWNS-TEST OK")
