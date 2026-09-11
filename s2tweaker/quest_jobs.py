"""Independent repeatable-job journals and a guarded round cleanup.

The 1.36 design let several containers run against ONE journal. Completing
one closed that journal for its siblings. This extension gives each live
container its own journal/stages and only lets the original round cleanup
run after every journal is inactive. See docs/REPEATABLE_JOBS_REPAIR.md.
"""
from collections import defaultdict
from copy import deepcopy


def _walk(node):
    yield node
    for child in node.children.values():
        yield from _walk(child)


def _remap(node, journal, replacement, stages):
    """Only changed references; preserve unrelated node settings/links."""
    patch = {}
    for key, value in node.values.items():
        value = value.strip()
        if key == "JournalQuestSID" and value == journal:
            patch[key] = replacement
        elif (key == "JournalQuestStageSID" and value in stages
              and node.values.get("JournalQuestSID", "").strip() == journal):
            patch[key] = stages[value]
    for key, child in node.children.items():
        child_patch = _remap(child, journal, replacement, stages)
        if child_patch:
            if key.startswith("["):
                from .tweaks import _struct_dict, _merge_nested
                child_patch = _merge_nested(_struct_dict(child), child_patch)
            patch[key] = child_patch
    return patch


def build_job_isolation(gd):
    """Return (existing-node patches, new guard nodes, new journals).

    No held-job counter: the engine's native JournalState condition also
    sees accepted jobs after saving/loading. Do not install this over jobs
    accepted with an older pak: their journal state cannot be migrated here.
    Unknown/incomplete game layouts fail the export instead of half-patching.
    """
    from .tweaks import _struct_dict, _resolved_struct

    by_quest = defaultdict(list)
    for key, node in gd.questnodes.children.items():
        by_quest[node.values.get("QuestSID", "").strip()].append((key, node))
    existing, guards, journals = {}, {}, {}
    givers = gd.repeatable_quest_givers()
    if not givers:
        raise ValueError("Cannot identify repeatable job givers for journal isolation.")
    for giver in givers:
        quest = giver["quest_sid"]
        slots = gd.repeatable_job_slots(quest)
        cleanup_sid = giver.get("cleanup_sid")
        if len(slots) != giver["pool"] or not cleanup_sid or not giver.get("end_sid"):
            raise ValueError(f"Incomplete repeatable-job cleanup layout: {quest}")
        cleanup = gd.questnodes.children[cleanup_sid]
        launchers = cleanup.children.get("Launchers")
        if not launchers or not launchers.children:
            raise ValueError(f"Missing repeatable-job cleanup launchers: {quest}")
        expected = {s["container"] for s in slots}
        actual = set()
        for entry in launchers.children.values():
            conns = entry.children.get("Connections")
            if entry.values.get("Excluding", "").strip() != "false" or not conns or len(conns.children) != 1:
                raise ValueError(f"Unsupported repeatable-job cleanup launcher: {quest}")
            conn = next(iter(conns.children.values()))
            source = conn.values.get("SID", "").strip()
            pin = conn.values.get("Name", "").strip()
            container = gd.questnodes.children.get(source)
            outputs = container.children.get("OutputPinNames") if container else None
            if source in expected:
                if not outputs or pin not in {v.strip() for v in outputs.values.values()}:
                    raise ValueError(f"Unknown job completion pin: {quest}/{source}")
                actual.add(source)
            elif not (container and container.values.get("QuestSID", "").strip() == quest
                      and container.values.get("NodeType", "").strip() == "EQuestNodeType::Technical"):
                raise ValueError(f"Unknown cleanup connection: {quest}/{source}")
        if actual != expected:
            raise ValueError(f"Not all job completions reach cleanup: {quest}")

        guard_sid = f"S2T_{quest}_NoActiveJobs"
        if guard_sid in gd.questnodes.children:
            raise ValueError(f"Quest node namespace collision: {guard_sid}")
        conditions = {}
        for index, slot in enumerate(slots):
            container = gd.questnodes.children[slot["container"]]
            subquest = container.values["ContaineredQuestPrototypeSID"].strip()
            job_nodes = by_quest[subquest]
            refs = {node.values["JournalQuestSID"].strip()
                    for _, node in job_nodes
                    if node.values.get("NodeType", "").strip() == "EQuestNodeType::SetJournal"
                    and node.values.get("JournalEntity", "").strip() == "EJournalEntity::Quest"
                    and node.values.get("JournalAction", "").strip() == "EJournalAction::Start"}
            if len(refs) != 1:
                raise ValueError(f"Unsupported job journal references: {subquest}")
            original = refs.pop()
            source = gd.journals.children.get(original)
            if source is None:
                raise ValueError(f"Missing journal prototype: {original}")
            used_stages = {part.values["JournalQuestStageSID"].strip()
                           for _, node in job_nodes for part in _walk(node)
                           if "JournalQuestStageSID" in part.values
                           and part.values.get("JournalQuestSID", "").strip() == original}
            resolved = _resolved_struct(gd.journals, source)
            source_stages = resolved.get("Stages", {})
            stage_by_sid = {v.get("SID", k): v for k, v in source_stages.items()
                            if isinstance(v, dict)}
            if not used_stages or not used_stages <= stage_by_sid.keys():
                raise ValueError(f"Missing journal stages: {subquest}")
            journal_sid = f"S2T_Job_{subquest}"
            if journal_sid in gd.journals.children or journal_sid in journals:
                raise ValueError(f"Journal namespace collision: {journal_sid}")
            stages = {sid: f"{journal_sid}_{sid}" for sid in sorted(used_stages)}
            journal = deepcopy(resolved)
            journal.update(__new__=True, SID=journal_sid)
            journal["Stages"] = {}
            for sid, new_sid in stages.items():
                stage = deepcopy(stage_by_sid[sid])
                stage["SID"] = new_sid
                journal["Stages"][new_sid] = stage
            # Use an existing localized objective as the title, never an
            # invented localization key derived from our generated SID.
            titles = [v.get("Description", "") for k, v in stage_by_sid.items()
                      if k in used_stages and k.endswith("_Start")]
            if not journal.get("Name") and titles:
                journal["Name"] = titles[0]
            journals[journal_sid] = journal
            for key, node in job_nodes:
                patch = _remap(node, original, journal_sid, stages)
                if patch:
                    existing[key] = patch
            conditions[f"[{index}]"] = {"[0]": {
                "ConditionType": "EQuestConditionType::JournalState",
                "ConditionComparance": "EConditionComparance::NotEqual",
                "JournalEntity": "EJournalEntity::Quest",
                "JournalState": "EJournalState::Active",
                "JournalQuestSID": journal_sid,
            }}
        guards[guard_sid] = {
            "__new__": True, "SID": guard_sid, "NodePrototypeVersion": "1",
            "Repeatable": "true", "QuestSID": quest,
            "NodeType": "EQuestNodeType::If",
            "Launchers": _struct_dict(launchers),
            "Conditions": {"ConditionCheckType": "EConditionCheckType::And",
                           **conditions},
        }
        # Replace EVERY original incoming edge, retaining its array index.
        # Thus no individual completion bypasses the all-jobs guard.
        existing[cleanup_sid] = {"Launchers": {
            idx: {"Excluding": "false", "Connections": {
                next(iter(entry.children["Connections"].children)):
                    {"SID": guard_sid, "Name": "True"}}}
            for idx, entry in launchers.children.items()}}
    return existing, guards, journals
