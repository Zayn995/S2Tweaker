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


def _external_cancellations(gd, journal_jobs, job_quests, reserved):
    """Mirror story-owned cancellation gates for the isolated journals.

    These nodes belong to the story quest, not the job container it shuts
    down. Share the original inputs rather than relying on cancellation of
    the now-unused old journal to emit a completion event.
    """
    from .tweaks import _struct_dict

    nodes = {}
    for source in gd.questnodes.children.values():
        values = source.values
        original = values.get("JournalQuestSID", "").strip()
        owner = values.get("QuestSID", "").strip()
        if (original not in journal_jobs or owner in job_quests
                or values.get("NodeType", "").strip() != "EQuestNodeType::SetJournal"
                or values.get("JournalEntity", "").strip() != "EJournalEntity::Quest"
                or values.get("JournalAction", "").strip() != "EJournalAction::Cancel"):
            continue
        if not owner or (not source.children.get("Launchers")
                         and values.get("LaunchOnQuestStart", "").strip() != "true"):
            raise ValueError(f"Unsupported external job cancellation: {source.name}")
        template = _struct_dict(source)
        for journal in journal_jobs[original]:
            guard_sid = f"S2T_StoryCancel_{source.name}_{journal}_Active"
            cancel_sid = f"S2T_StoryCancel_{source.name}_{journal}_Cancel"
            for sid in (guard_sid, cancel_sid):
                if sid in gd.questnodes.children or sid in reserved or sid in nodes:
                    raise ValueError(f"Quest node namespace collision: {sid}")
            guard = {key: deepcopy(value) for key, value in template.items()
                     if not key.startswith("Journal")}
            guard.update(__new__=True, SID=guard_sid, NodePrototypeVersion="1",
                         NodeType="EQuestNodeType::If", Conditions={
                             "ConditionCheckType": "EConditionCheckType::And", "[0]": {"[0]": {
                                 "ConditionType": "EQuestConditionType::JournalState",
                                 "ConditionComparance": "EConditionComparance::Equal",
                                 "JournalEntity": "EJournalEntity::Quest",
                                 "JournalState": "EJournalState::Active",
                                 "JournalQuestSID": journal}}})
            cancel = deepcopy(template)
            # Activation and delay are already handled by the guard. The
            # action must run only on True, never automatically at quest start.
            cancel.pop("LaunchOnQuestStart", None)
            cancel.pop("StartDelay", None)
            cancel.update(__new__=True, SID=cancel_sid, JournalQuestSID=journal,
                          Launchers={"[0]": {"Excluding": "false", "Connections": {
                              "[0]": {"SID": guard_sid, "Name": "True"}}}})
            nodes[guard_sid] = guard
            nodes[cancel_sid] = cancel
    return nodes


def _return_marker_reapplication(gd, parent, job, job_nodes, original,
                                journal, stages, parent_guard, reserved):
    """Experimental post-hand-in recovery for an already active return stage.

    Native quests reapply Start/Markers to active stages. Use separate nodes
    so none of the original return-start node's dialog/reward consumers run.
    See docs/JOB_COMPLETED_MARKER_FOLLOWUP.md for the native evidence and
    remaining in-game checks; this does not force journal tracking.
    """
    from .tweaks import _struct_dict

    returns = [node for _, node in job_nodes
               if node.values.get("NodeType", "").strip() == "EQuestNodeType::SetJournal"
               and node.values.get("JournalEntity", "").strip() == "EJournalEntity::QuestStage"
               and node.values.get("JournalAction", "").strip() == "EJournalAction::Start"
               and node.values.get("JournalQuestSID", "").strip() == original
               and node.values.get("JournalQuestStageSID", "").strip().endswith("_Finish")]
    if len(returns) != 1:
        raise ValueError(f"Unsupported job return-stage layout: {job}")
    source = returns[0]
    old_stage = source.values["JournalQuestStageSID"].strip()
    markers = source.children.get("Markers")
    marker = markers.children.get("[0]") if markers else None
    allowed = {"SID", "NodePrototypeVersion", "Repeatable", "QuestSID", "NodeType",
               "JournalEntity", "JournalAction", "JournalQuestSID", "JournalQuestStageSID"}
    if (old_stage not in stages or source.attrs or set(source.values) - allowed
            or set(source.children) != {"Launchers", "Markers"}
            or not markers or markers.attrs or markers.values or set(markers.children) != {"[0]"}
            or not marker or marker.attrs or marker.children
            or set(marker.values) != {"MarkerTargetQuestGuid", "AddOnCondition", "RemoveOnCondition"}
            or marker.values["AddOnCondition"].strip() != "false"
            or marker.values["RemoveOnCondition"].strip() != "false"
            or not marker.values["MarkerTargetQuestGuid"].strip()):
        raise ValueError(f"Unsupported job return-marker layout: {job}")
    # Reapplication can emit a stage event. Do not silently activate newly
    # introduced native listeners when a future game version changes a job.
    if any(node.values.get("NodeType", "").strip() == "EQuestNodeType::OnJournalQuestEvent"
           and node.values.get("JournalQuestSID", "").strip() == original
           and node.values.get("JournalQuestStageSID", "").strip() == old_stage
           for _, node in job_nodes):
        raise ValueError(f"Unsupported job return-stage listener: {job}")

    ready_sid = f"S2T_ReturnMarker_{job}_Ready"
    reapply_sid = f"S2T_ReturnMarker_{job}_Reapply"
    for sid in (ready_sid, reapply_sid):
        if sid in gd.questnodes.children or sid in reserved:
            raise ValueError(f"Quest node namespace collision: {sid}")

    def launcher(sid, pin):
        return {"[0]": {"Excluding": "false", "Connections": {
            "[0]": {"SID": sid, "Name": pin}}}}

    active = {"ConditionType": "EQuestConditionType::JournalState",
              "ConditionComparance": "EConditionComparance::Equal",
              "JournalEntity": "EJournalEntity::Quest",
              "JournalState": "EJournalState::Active", "JournalQuestSID": journal}
    ready = {"__new__": True, "SID": ready_sid, "NodePrototypeVersion": "1",
             "Repeatable": "true", "QuestSID": parent, "NodeType": "EQuestNodeType::If",
             "Launchers": launcher(parent_guard, "False"), "Conditions": {
                 "ConditionCheckType": "EConditionCheckType::And",
                 "[0]": {"[0]": active}, "[1]": {"[0]": {
                     **active, "JournalEntity": "EJournalEntity::QuestStage",
                     "JournalQuestStageSID": stages[old_stage]}}}}
    reapply = _struct_dict(source)
    reapply.update(__new__=True, SID=reapply_sid, Repeatable="true", QuestSID=parent,
                   JournalQuestSID=journal, JournalQuestStageSID=stages[old_stage],
                   Launchers=launcher(ready_sid, "True"))
    return {ready_sid: ready, reapply_sid: reapply}


def build_job_isolation(gd, *, localization_aliases=None):
    """Return (existing-node patches, new nodes, new journals).

    No held-job counter: the engine's native JournalState condition also
    sees accepted jobs after saving/loading. Do not install this over jobs
    accepted with an older pak: their journal state cannot be migrated here.
    Unknown/incomplete game layouts fail the export instead of half-patching.
    """
    from .tweaks import _struct_dict, _resolved_struct

    by_quest = defaultdict(list)
    for key, node in gd.questnodes.children.items():
        by_quest[node.values.get("QuestSID", "").strip()].append((key, node))
    existing, new_nodes, journals = {}, {}, {}
    journal_jobs, job_quests = defaultdict(list), set()
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
            job_quests.add(subquest)
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
            if localization_aliases is not None:
                localization_aliases[f"sid_journal_{journal_sid}_Name"] = f"sid_journal_{original}_Name"
                for sid, new_sid in stages.items():
                    localization_aliases[f"sid_journal_stage_{new_sid}"] = f"sid_journal_stage_{sid}"
            journal = deepcopy(resolved)
            journal.update(__new__=True, SID=journal_sid)
            journal["Stages"] = {}
            for sid, new_sid in stages.items():
                stage = deepcopy(stage_by_sid[sid])
                stage["SID"] = new_sid
                journal["Stages"][new_sid] = stage
            # Retain metadata for existing saves. The renderer still needs
            # the supplemental implicit journal/stage localization aliases.
            titles = [v.get("Description", "") for k, v in stage_by_sid.items()
                      if k in used_stages and k.endswith("_Start")]
            if not journal.get("Name") and titles:
                journal["Name"] = titles[0]
            journals[journal_sid] = journal
            journal_jobs[original].append(journal_sid)
            for key, node in job_nodes:
                patch = _remap(node, original, journal_sid, stages)
                if patch:
                    existing[key] = patch
            new_nodes.update(_return_marker_reapplication(
                gd, quest, subquest, job_nodes, original, journal_sid, stages,
                guard_sid, new_nodes))
            conditions[f"[{index}]"] = {"[0]": {
                "ConditionType": "EQuestConditionType::JournalState",
                "ConditionComparance": "EConditionComparance::NotEqual",
                "JournalEntity": "EJournalEntity::Quest",
                "JournalState": "EJournalState::Active",
                "JournalQuestSID": journal_sid,
            }}
        new_nodes[guard_sid] = {
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
    new_nodes.update(_external_cancellations(gd, journal_jobs, job_quests, new_nodes))
    return existing, new_nodes, journals
