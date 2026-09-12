"""Check repeatable-job pool limits, cooldowns and dialogue rearming against live data.

Counters count jobs issued per round, not currently held jobs. Resolve varying
launcher indices, cap limits by pool size, and emit complete array entries.
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

# --- 3) Limit patch: complete condition entry ---
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6)))
assert len(p) == 8, sorted(p)
for sid, node in p.items():
    entry = node.children["Conditions"].children["[0]"].children["[0]"]
    # Emit complete condition/launcher entries for either array-merge interpretation.
    assert set(entry.values) == {
        "ConditionType", "ConditionComparance", "GlobalVariablePrototypeSID",
        "ChangeValueMode", "VariableValue"}, (sid, sorted(entry.values))
    assert entry.values["ConditionComparance"] == "EConditionComparance::Less"
    assert entry.values["VariableValue"] == "6", (sid, entry.values["VariableValue"])
print("Limit 6: 8 nodes, complete condition with all five keys  OK")

# --- 4) Cap each giver to its job pool ---
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=10)))
got = {sid: n.children["Conditions"].children["[0]"].children["[0]"].values["VariableValue"]
       for sid, n in p.items()}
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

# --- 5) Dialog changes: complete launcher entry ---
p = nodes(build_patches(gd, Settings(repeatable_jobs_instant=True)))
assert len(p) == 8, sorted(p)
for giver in givers:
    node = p[giver["dialog_key"]]
    launcher_key, conn_key = giver["link_path"]
    launcher = node.children["Launchers"].children[launcher_key]
    # Emit the complete launcher entry: Excluding and ALL connections.
    assert "Excluding" in launcher.values, giver["quest"]
    conns = launcher.children["Connections"].children
    vanilla_conns = (giver["dialog_node"].children["Launchers"]
                     .children[launcher_key].children["Connections"].children)
    assert set(conns) == set(vanilla_conns), (giver["quest"], sorted(conns))
    for key, conn in conns.items():
        # Preserve SID on each connection.
        assert conn.values["SID"] == vanilla_conns[key].values["SID"], (giver["quest"], key)
        want = "True" if key == conn_key else vanilla_conns[key].values.get("Name", "")
        assert conn.values.get("Name", "") == want, (giver["quest"], key, conn.values)
print("Dialog changes: only one pin set to True, SIDs and adjacent entries unchanged  OK")

# Patch RSQ nodes only.
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6,
                                     repeatable_jobs_instant=True)))
assert len(p) == 16, sorted(p)
assert all(sid.startswith("RSQ") for sid in p), sorted(p)
print("16 nodes, all RSQ - story and side quests remain vanilla  OK")

# Compose limit and dialogue changes with cooldowns.
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6,
                                     repeatable_jobs_instant=True,
                                     repeatable_quest_factor=0.0)))
timers = [sid for sid, n in p.items() if "InGameHours" in n.values]
assert len(timers) == 8, timers
assert {n.values["InGameHours"] for sid, n in p.items() if sid in timers} == {"0"}
assert len(p) == 24, len(p)   # Each limit/dialogue/timer node must appear once.
print("Limit, dialog and cooldown share one patch file (24 nodes)  OK")

# --- 8) Tweak list ------------------------------------------------------
lines = summarize(Settings(repeatable_jobs_per_round=6, repeatable_jobs_instant=True))
assert any("Repeatable jobs per round 6" in l for l in lines), lines
assert any("next job right away" in l for l in lines), lines
assert not any("Repeatable jobs per round" in l for l in summarize(Settings()))
print("Lines in the tweak list  OK")

print("\nJOBS PER ROUND TEST PASSED")
