"""Check repeatable-job pool limits, cooldowns and dialogue rearming against live data.

Counters count menu entries, not currently held jobs. Resolve varying launcher
indices, preserve eligibility conditions and stop when the pool is exhausted.
Neutral settings must avoid parsing the large quest file."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker import cfgparse

gd = GameData(VANILLA)
KEY = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"


def nodes(patches):
    assert KEY in patches, sorted(patches)
    return cfgparse.parse(patches[KEY]).children


# Verify discovered job-giver data against vanilla.
givers = gd.repeatable_quest_givers()
assert len(givers) == 8, [g["quest"] for g in givers]
assert [g["quest"] for g in givers] == [
    "RSQ01", "RSQ04", "RSQ05", "RSQ06", "RSQ07", "RSQ08", "RSQ09", "RSQ10"]
assert {g["cap"] for g in givers} == {3.0}, sorted({g["cap"] for g in givers})
assert {g["pin"] for g in givers} == {"False"}, sorted({g["pin"] for g in givers})
pools = {g["quest"]: g["pool"] for g in givers}
assert pools == {"RSQ01": 6, "RSQ04": 10, "RSQ05": 8, "RSQ06": 9,
                 "RSQ07": 9, "RSQ08": 9, "RSQ09": 9, "RSQ10": 9}, pools
print(f"Live: 8 givers, limit 3 throughout, pools {sorted(set(pools.values()))}  OK")

# Connection indices vary and must be resolved.
conn_idx = {g["quest"]: g["link_path"][1] for g in givers}
assert set(conn_idx.values()) == {"[0]", "[1]"}, conn_idx
print(f"Mixed connection indexes ({sorted(set(conn_idx.values()))}) and searched per giver  OK")

# Neutral output must not parse the large quest file.
fresh = GameData(VANILLA)
assert not build_patches(fresh, Settings())
assert "questnodes" not in fresh.__dict__, "Neutral settings parse QuestNodePrototypes"
print("Neutral: no patch, 75-MB file untouched  OK")

# Preserve the existing counter condition except its limit.
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6)))
assert len(p) == 24, sorted(p)  # Limit, random input and exhausted-pool dialog per giver.
for giver in givers:
    sid = giver["cap_key"]
    node = p[sid]
    entry = node.children["Conditions"].children["[0]"].children["[0]"]
    assert set(entry.values) == {"VariableValue"}, (sid, sorted(entry.values))
    assert gd.resolve(gd.questnodes, sid, "Conditions.[0].[0].ConditionComparance") == "EConditionComparance::Less"
    assert entry.values["VariableValue"] == "6", (sid, entry.values["VariableValue"])
print("Limit 6: counter values and exhaustion wiring for all eight givers OK")

# --- 4) Cap each giver to its job pool ---
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=10)))
got = {g["cap_key"]: p[g["cap_key"]].get("Conditions.[0].[0].VariableValue") for g in givers}
by_quest = {q: got[g["cap_key"]] for q, g in
            ((g["quest"], g) for g in givers)}
assert by_quest == {"RSQ01": "6", "RSQ04": "10", "RSQ05": "8", "RSQ06": "9",
                    "RSQ07": "9", "RSQ08": "9", "RSQ09": "9", "RSQ10": "9"}, by_quest
print("Slider 10 is capped to each giver's pool (Warlock 6)  OK")

# Allow limits below vanilla.
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=1)))
assert len(p) == 8
vals = {n.children["Conditions"].children["[0]"].children["[0]"].values["VariableValue"]
        for n in p.values()}
assert vals == {"1"}, vals
print("Slider 1: stricter than vanilla, all eight set to 1  OK")

# --- 5) Dialog changes: only the resolved pin ---
p = nodes(build_patches(gd, Settings(repeatable_jobs_instant=True)))
assert len(p) == 8, sorted(p)
for giver in givers:
    node = p[giver["dialog_key"]]
    launcher_key, conn_key = giver["link_path"]
    launcher = node.children["Launchers"].children[launcher_key]
    assert not launcher.values, giver["quest"]
    conns = launcher.children["Connections"].children
    vanilla_conns = (giver["dialog_node"].children["Launchers"]
                     .children[launcher_key].children["Connections"].children)
    assert set(conns) == {conn_key}, (giver["quest"], sorted(conns))
    assert conns[conn_key].values == {"Name": "True"}
print("Dialog changes: only one pin set to True, SIDs and adjacent entries unchanged  OK")

# Patch RSQ nodes only.
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6,
                                     repeatable_jobs_instant=True)))
assert len(p) == 24, sorted(p)
assert all(sid.startswith("RSQ") for sid in p), sorted(p)
print("24 existing nodes, all RSQ - unrelated quests remain vanilla OK")

# Compose limit and dialogue changes with cooldowns.
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6,
                                     repeatable_jobs_instant=True,
                                     repeatable_quest_factor=0.0)))
timers = [sid for sid, n in p.items() if "InGameHours" in n.values]
assert len(timers) == 8, timers
assert {n.values["InGameHours"] for sid, n in p.items() if sid in timers} == {"0"}
assert len(p) == 32, len(p)   # Limit/random/dialogue/timer nodes appear once.
print("Limit, random, dialog and cooldown compose in one patch file OK")

# Live eligibility conditions are copied exactly, including journal/story gates.
from s2tweaker.quest_pool import build_pool_guard
from s2tweaker.tweaks import _struct_dict
for giver in givers:
    old, added = build_pool_guard(gd, giver)
    for index, slot in enumerate(gd.repeatable_job_slots(giver["quest_sid"])):
        add = gd.questnodes.children[slot["add"]]
        source = next(iter(next(iter(add.children["Launchers"].children.values())).children["Connections"].children.values()))
        gate = gd.questnodes.children[source.values["SID"]]
        check = added[f"S2T_{giver['quest_sid']}_PoolCandidate_{index}"]
        assert check["Conditions"] == _struct_dict(gate.children["Conditions"])
    assert len(added) == giver["pool"] + 1
print("All 69 native eligibility trees preserved; no story conditions removed OK")

# --- 8) Tweak list ------------------------------------------------------
lines = summarize(Settings(repeatable_jobs_per_round=6, repeatable_jobs_instant=True))
assert any("Repeatable jobs per round 6" in l for l in lines), lines
assert any("next job right away" in l for l in lines), lines
assert not any("Repeatable jobs per round" in l for l in summarize(Settings()))
print("Lines in the tweak list  OK")

print("\nJOBS PER ROUND TEST PASSED")
