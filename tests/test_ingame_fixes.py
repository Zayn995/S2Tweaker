"""Regression checks derived from community issues #9-#12.

Cover simultaneous-job gates, explicit edition item fields, dialogue range,
retired ineffective options and low sober-up factors. Expected values are
read from installed vanilla data; passing does not establish gameplay success."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker import cfgparse

gd = GameData(VANILLA)
QUESTS = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"

ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


def build(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


# Check existing dialogue launcher repairs for simultaneous jobs.
print("\n1) Accept several jobs in one conversation")
check(build() == {}, "Vanilla settings produce nothing")

MENU = "DialogPrototypes/DialogPrototypes_patch_S2Tweaker.cfg"
JOBS = "QuestNodePrototypes/S2Tweaker_Jobs.cfg"
p = build(repeatable_jobs_multi=True)
check(set(p) == {QUESTS, MENU, JOBS, "JournalQuestPrototypes/S2Tweaker_Jobs.cfg"},
      f"Three patch files: guards, menu graph, Taken/Clear: {sorted(p)}")
raw = p[QUESTS]
nodes = cfgparse.parse(raw).children
givers = gd.repeatable_quest_givers()
check(len(givers) == 8, f"{len(givers)} quest givers detected")

# Existing-node patches must target vanilla structs with bpatch.
new = [sid for sid in nodes if sid not in gd.questnodes.children]
check(not new, f"not a single new node{new}")
check(raw.count(" : struct.begin") == raw.count("{bpatch}"),
      "Every struct and array entry carries {bpatch}")

# Disable acceptance/job-start exclusion guards with complete launcher entries;
# preserve completion guards.
total_flipped, total_starts = 0, 0
for giver in givers:
    dlg = nodes[giver["dialog_sid"]]
    vanilla = gd.questnodes.children[giver["dialog_sid"]].children["Launchers"].children
    flipped = dlg.children["Launchers"].children
    assert list(dlg.children) == ["Launchers"] and not dlg.values, giver["quest"]
    for idx, entry in flipped.items():
        assert idx in vanilla, (giver["quest"], idx)
        assert entry.values == {"Excluding": "false"}, (giver["quest"], idx, entry.values)
        v_conns = vanilla[idx].children["Connections"].children
        p_conns = entry.children["Connections"].children
        assert list(p_conns) == list(v_conns), (giver["quest"], idx)
        for cidx in v_conns:
            assert p_conns[cidx].values["SID"] == v_conns[cidx].values["SID"].strip()
    sources = {c.values["SID"] for e in flipped.values()
               for c in e.children["Connections"].children.values()}
    assert giver["accept"] in sources, giver["quest"]

    def _sources(entry):
        return [c.values.get("SID", "").strip()
                for c in entry.children["Connections"].children.values()]

    excluding = {i: e for i, e in vanilla.items()
                 if e.values.get("Excluding", "").strip() == "true"}
    finish = [i for i, e in excluding.items() if any(s.endswith("_Finish") for s in _sources(e))]
    starts = [i for i, e in excluding.items()
              if all("OnJournalQuestEvent" in s and s.endswith("_Start") for s in _sources(e))]
    assert finish and not (set(finish) & set(flipped)), (giver["quest"], finish)
    assert set(starts) <= set(flipped), (giver["quest"], starts, list(flipped))
    assert len(flipped) == 1 + len(starts), (giver["quest"], len(flipped), len(starts))
    total_flipped += len(flipped)
    total_starts += len(starts)
check(total_flipped == 8 + total_starts and total_starts == 22,
      f"{total_flipped} guards changed: 8 acceptance nodes + {total_starts} job-start guards; "
      f"The 8 Finish guards remain")

# Verify the vanilla acceptance exclusion used by the repair.
excluded = 0
for giver in givers:
    dlg = gd.questnodes.children[giver["dialog_sid"]]
    for lnode in dlg.children["Launchers"].children.values():
        conns = lnode.children.get("Connections")
        for c in (conns.children.values() if conns else ()):
            if c.values.get("SID", "").strip() == giver["accept"]:
                assert lnode.values.get("Excluding", "").strip() == "true", giver["quest"]
                excluded += 1
check(excluded == 8, f"For all {excluded} givers, accepting a job disables the dialog through Excluding")

# Check the repeatable delayed acceptance node used to reopen dialogue.
for giver in givers:
    acc = gd.questnodes.children[giver["accept"]]
    assert acc.values.get("Repeatable", "").strip() == "true", giver["quest"]
    assert acc.values.get("StartDelay", "").strip() == "1.0", giver["quest"]
check(True, "Every acceptance is repeatable and waits 1 s; the dialog returns afterward")

# 1e) The round End now stays vanilla. The independent journal repair
# gates the original cleanup; full lifecycle checks: test_job_isolation.py.
for giver in givers:
    assert giver["end_sid"] not in nodes, giver["quest"]
    assert giver["cleanup_sid"] in nodes, giver["quest"]
    assert giver["accept"] not in nodes, giver["quest"]
check(True, "round cleanup is guarded; End and acceptance stay vanilla")

# Without the option, dialogue and end nodes remain unchanged.
only_limit = build(repeatable_jobs_per_round=6)
if only_limit:
    assert "ExcludeAllNodesInContainer" not in only_limit.get(QUESTS, "")
    assert "Excluding" not in only_limit.get(QUESTS, "")
    assert MENU not in only_limit and JOBS not in only_limit
check(True, "Without the toggle, the dialog, end node and menu remain unchanged")

# Check the initial dialogue gate routes both outcomes to the job menu.
menu = cfgparse.parse(p[MENU]).children
check(len(menu) == 8, f"{len(menu)} If nodes, one per dialog chain")
for giver in givers:
    chain = giver["dialog_node"].values["DialogChainPrototypeSID"].strip()
    if_sid, menu_target, cancel_target = gd.job_menu_switch(chain, giver["accept"])
    node = menu[if_sid]
    assert not node.values and list(node.children) == ["NextDialogOptions"], if_sid
    branches = node.children["NextDialogOptions"].children
    assert list(branches) == ["False"], (if_sid, list(branches))
    assert branches["False"].values == {"NextDialogSID": menu_target}, if_sid
    assert menu_target != cancel_target, if_sid
    # Verify the existing gate/target and distinct vanilla false branch.
    vanilla_if = gd.dialogs.children[if_sid]
    assert menu_target in gd.dialogs.children and cancel_target in gd.dialogs.children, if_sid
    v_false = vanilla_if.children["NextDialogOptions"].children["False"].values["NextDialogSID"].strip()
    assert v_false == cancel_target, (if_sid, v_false)
check(True, "Only the False branch is redirected to the True branch's vanilla target")
check(raw.count(" : struct.begin") == raw.count("{bpatch}") and
      p[MENU].count(" : struct.begin") == p[MENU].count("{bpatch}"),
      "Every struct in the menu graph also carries {bpatch}")

# Emit new taken/cleanup nodes separately without bpatch.
jobs = cfgparse.parse(p[JOBS]).children
slots = {g["quest_sid"]: gd.repeatable_job_slots(g["quest_sid"]) for g in givers}
n_slots = sum(len(v) for v in slots.values())
check(n_slots == 69 and all(len(slots[g["quest_sid"]]) == g["pool"] for g in givers),
      f"{n_slots} job containers, matching each giver's pool")
check(len(jobs) == 4 * n_slots + len(givers) + 12 and "{bpatch}" not in p[JOBS],
      f"{len(jobs)} new nodes (Taken/Clear, marker guards/reapply, round guards, story abort), no {{bpatch}}")
check(sum(sid.startswith("S2T_ReturnMarker_") for sid in jobs) == 2 * n_slots,
      "Each job has a separate marker guard and reapply node")


def _conn(node):
    return node.children["Launchers"].children["[0]"].children["Connections"].children["[0]"].values["SID"]


for g in givers:
    for slot in slots[g["quest_sid"]]:
        tag = slot["container"].rsplit("_", 1)[-1]
        taken = jobs[f"S2T_{g['quest_sid']}_Taken_{tag}"]
        clear = jobs[f"S2T_{g['quest_sid']}_Clear_{tag}"]
        assert taken.values["NodeType"] == "EQuestNodeType::Technical" and taken.values["StartDelay"] == "3.0"
        assert taken.values["Repeatable"] == "true" and clear.values["Repeatable"] == "true"
        assert _conn(taken) == slot["pin"], (taken.values["SID"], _conn(taken))
        assert _conn(clear) == taken.values["SID"]
        assert clear.values["NodeType"] == "EQuestNodeType::BridgeCleanUp"
        cleaned = list(clear.children["NodesToCleanUpResults"].values.values())
        assert cleaned == [slot["add"], g["accept"]], (clear.values["SID"], cleaned)
        for sid in (slot["pin"], slot["add"], slot["container"]):
            assert sid in gd.questnodes.children, sid
        assert taken.values["SID"] not in gd.questnodes.children
check(True, "Every Taken node depends on its container pin; each Clear removes "
            "Exactly Add_C0x + acceptance: all targets exist and names do not collide")

# Verify Warlock options depend on the job pool-add results being cleared.
warlock = next(g for g in givers if g["quest"] == "RSQ01")
adds = {s["add"] for s in slots[warlock["quest_sid"]]}
chain = warlock["dialog_node"].values["DialogChainPrototypeSID"].strip()
linked = set()
for node in gd.dialogs.children.values():
    if (node.values.get("DialogChainPrototypeSID") or "").strip() != chain:
        continue
    stack = [node]
    while stack:
        cur = stack.pop()
        v = (cur.values.get("LinkedNodePrototypeSID") or "").strip()
        if v in adds:
            linked.add(v)
        stack.extend(cur.children.values())
check(linked == adds, f"The Warlock menu depends on all {len(adds)} Add_C0x ({len(linked)} gefunden)")

# Check composition with the older job-pool controls.
both = build(repeatable_jobs_multi=True, repeatable_jobs_per_round=6,
             repeatable_quest_factor=0.04)
txt = both[QUESTS]
check("Excluding = false" in txt and "VariableValue = 6" in txt and "InGameHours = 1" in txt,
      "Toggle, round limit and cooldown share one file")
check("Accept several repeatable jobs" in "\n".join(summarize(Settings(repeatable_jobs_multi=True))),
      "The tweak list includes the toggle")


# --- 2) The 22 edition items ---
print("\n2) DLC items")
dlc_items = {ed: trees["items"].children for ed, trees in gd.dlc_editions.items()}
total = sum(len(v) for v in dlc_items.values())
check(total >= 20, f"{total} edition items in {len(dlc_items)} Editionen")
for ed, kids in dlc_items.items():
    n = sum(1 for x in kids.values() if "ItemGridWidth" in x.values)
    assert n == len(kids), (ed, n, len(kids))
check(True, "Each item defines its own inventory size")


def dlc_files(patches):
    return {k: v for k, v in patches.items() if k.startswith("//")}


grid = build(item_grid_factor=2.0)
files = dlc_files(grid)
check(files, f"Grid size now generates DLC files: {sorted(files)[:2]}")
hits = 0
for text in files.values():
    for node in cfgparse.parse(text).children.values():
        if "ItemGridWidth" in node.values:
            hits += 1
check(hits >= 20, f"{hits} edition items receive a larger inventory grid")

dur = dlc_files(build(gear_durability_factor=2.0))
hits = sum(1 for t in dur.values() for n in cfgparse.parse(t).children.values()
           if "BaseDurability" in n.values)
# Exclude edition items with placeholder BaseDurability 1.0, as for base items.
check(hits == 17, f"{hits} edition items receive the new maximum condition")

act = dlc_files(build(inventory_action_factor=2.0))
check(act, "Use duration also reaches the DLC branch")

weight = dlc_files(build(item_weight_factor=0.5,
                         item_weight_categories={"weapon", "armor"}))
hits = sum(1 for t in weight.values() for n in cfgparse.parse(t).children.values()
           if "Weight" in n.values)
check(hits > 0, f"{hits} edition items follow weight sliders")

check(not dlc_files(build(item_weight_factor=0.5, item_weight_categories={"consumable"})),
      "A category without edition items produces no DLC patch")
check(not dlc_files(build()), "Vanilla settings leave the DLC branch unchanged")

# --- craigduk76, 1.35.0 (GitHub #10, #11, #12) ---------------------------
print("\n--- craigduk76 (#10/#11/#12) ---")
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"

# Dialogue range must cover explicit human NPC fields as well as Player.
humans = gd.human_npc_sids()
carriers = [sid for sid in humans
            if gd.obj.children[sid].values.get("MaxDialogInteractDistance")]
check(len(carriers) == len(humans) and len(humans) > 1500,
      f"All {len(humans)} human NPCs define their own talk distance")
obj = cfgparse.parse(build_patches(gd, Settings(dialog_range_factor=1.5))[OBJ])
touched = {sid for sid, node in obj.children.items()
           if "MaxDialogInteractDistance" in node.values}
check("Player" in touched and len(touched & set(humans)) == len(humans),
      f"1.36.0: player AND all {len(humans)} humans receive the new distance")
check(not touched - set(humans) - {"Player"},
      "Mutants remain excluded (they do not speak)")
check(obj.children["Player"].values["MinDialogInteractDistance"] == "112.5"
      and obj.children["Player"].values["MaxDialogInteractDistance"] == "195.0",
      "Player: 75/130 -> 112.5/195.0 at a factor of 1.5")
sample = next(sid for sid in humans
              if gd.obj.children[sid].values.get("MaxDialogInteractDistance", "").strip() == "250.f")
check(obj.children[sample].values["MaxDialogInteractDistance"] == "375.0f",
      f"Literal format preserved: {sample} 250.f -> 375.0f")
check(OBJ not in build_patches(gd, Settings(dialog_range_factor=1.0)),
      "Vanilla settings do not write any NPC")

# Retain retired option fields for presets without emitting ineffective patches.
core = build_patches(gd, Settings(dialog_fov=105, ladder_free_look=True,
                                  look_straight_down=True)).get(CORE, "")
check("DialogFOVDefault" not in core and "ClimbView" not in core,
      "Withdrawn controls: dialog zoom and ladder look-around no longer write patches")
check("ViewPitchDownLimit = -90.0" in core,
      "'Look straight down' remains, supported by a player test")

# Low sober-up factors must survive numeric formatting.
for factor, want in ((0.25, "0.25"), (0.01, "0.01")):
    obj = cfgparse.parse(build_patches(gd, Settings(sober_up_factor=factor))[OBJ])
    check(obj.children["Player"].children["VitalParams"].values["DegenDrunknessPoints"] == want,
          f"Ausnuechtern {factor:.0%} -> DegenDrunknessPoints = {want}")

# Statically verify retired controls are absent from the GUI.
from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS
gone = {"dialog_fov"} & set(SLIDER_FIELDS) | {"ladder_look", "rq_jobs_instant"} & set(CHECK_FIELDS)
check(not gone, f"The three withdrawn controls are absent{sorted(gone)}")
check("sober" in SLIDER_FIELDS and "rq_jobs" in SLIDER_FIELDS and "look_down" in CHECK_FIELDS
      and "rq_jobs_multi" in CHECK_FIELDS,
      "Verified adjacent controls remain; the multiple-jobs toggle uses the third revision")

print(f"\n=== {ok} checks passed ===")
