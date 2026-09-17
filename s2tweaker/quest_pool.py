"""Stop enlarged repeatable-job pools when no further native job is eligible."""
from copy import deepcopy


def _links(node):
    launchers = node.children.get("Launchers")
    if launchers is None:
        return []
    return [(index, key, entry, connection)
            for index, entry in launchers.children.items()
            if "Connections" in entry.children
            for key, connection in entry.children["Connections"].children.items()]


def _launcher(sid, pin):
    return {"Excluding": "false", "Connections": {"[0]": {"SID": sid, "Name": pin}}}


def _next_index(node):
    keys = node.children["Launchers"].children
    if any(not key.startswith("[") or not key.endswith("]") or not key[1:-1].isdigit() for key in keys):
        raise ValueError(f"Unsupported job launcher indices: {node.name}")
    return max((int(key[1:-1]) for key in keys), default=-1) + 1


def build_pool_guard(gd, giver):
    """Return existing-node patches and new checks using live eligibility rules.

    Each candidate is evaluated before the native random selection. One eligible
    candidate permits another draw; otherwise a nonempty partial pool enables the
    original offer dialog. No job, story flag, counter or journal is reset.
    """
    from .tweaks import _struct_dict

    nodes = gd.questnodes.children
    quest, cap_sid = giver["quest_sid"], giver["cap_key"]
    slots = gd.repeatable_job_slots(quest)
    if not slots or len(slots) != giver["pool"]:
        raise ValueError(f"Incomplete repeatable-job pool: {quest}")
    randoms = [(sid, node, link) for sid, node in nodes.items()
               if node.values.get("QuestSID", "").strip() == quest
               and node.values.get("NodeType", "").strip() == "EQuestNodeType::Random"
               for link in _links(node)
               if link[3].values.get("SID", "").strip() == cap_sid
               and link[3].values.get("Name", "").strip() == "True"]
    if len(randoms) != 1:
        raise ValueError(f"Unsupported repeatable-job random selection: {quest}")
    random_sid, random_node, (outer, inner, entry, _) = randoms[0]
    if entry.values.get("Excluding", "").strip() != "false" or len(entry.children["Connections"].children) != 1:
        raise ValueError(f"Unsupported job random launcher: {quest}")
    conditions = []
    for slot in slots:
        add = nodes[slot["add"]]
        links = _links(add)
        if len(links) != 1 or links[0][3].values.get("Name", "").strip() != "True":
            raise ValueError(f"Unsupported job pool-add launcher: {add.name}")
        gate = nodes.get(links[0][3].values.get("SID", "").strip())
        if (gate is None or gate.attrs
                or gate.values.get("NodeType", "").strip() != "EQuestNodeType::If"
                or gate.values.get("QuestSID", "").strip() != quest
                or "Conditions" not in gate.children
                or any(child.attrs for child in gate.children["Conditions"].walk())
                or not any(link[3].values.get("SID", "").strip() == random_sid for link in _links(gate))):
            raise ValueError(f"Unsupported job eligibility check: {add.name}")
        # Preserve the entire condition tree, including story gates, previous-job
        # restrictions, mutual exclusions and journal-state conditions.
        conditions.append(_struct_dict(gate.children["Conditions"]))

    def make(sid, source, pin, condition):
        if sid in nodes:
            raise ValueError(f"Quest node namespace collision: {sid}")
        return {"__new__": True, "SID": sid, "NodePrototypeVersion": "1",
                "Repeatable": "true", "QuestSID": quest, "NodeType": "EQuestNodeType::If",
                "Launchers": {"[0]": _launcher(source, pin)}, "Conditions": condition}

    checks = [f"S2T_{quest}_PoolCandidate_{index}" for index in range(len(conditions))]
    new_nodes = {}
    for index, (sid, condition) in enumerate(zip(checks, conditions)):
        new_nodes[sid] = make(sid, cap_sid if index == 0 else checks[index - 1],
                              "True" if index == 0 else "False", condition)
    # The count refers to menu entries already added, not to accepted jobs.
    outer_cond, inner_cond = giver["cond_path"]
    counter = giver["cap_node"].children["Conditions"].children[outer_cond].children[inner_cond]
    if (counter.values.get("ConditionType", "").strip() != "EQuestConditionType::GlobalVariable"
            or counter.values.get("ConditionComparance", "").strip() != "EConditionComparance::Less"):
        raise ValueError(f"Unsupported job pool counter: {quest}")
    nonempty = deepcopy(_struct_dict(counter))
    nonempty.update(ConditionComparance="EConditionComparance::Greater", VariableValue="0")
    ready = f"S2T_{quest}_PoolExhausted"
    new_nodes[ready] = make(ready, checks[-1], "False", {"[0]": {"[0]": nonempty}})

    # Reuse the original random input index; preserve every other launcher.
    random_launchers = {outer: {"Connections": {inner: {"SID": checks[0]}}}}
    index = _next_index(random_node)
    for sid in checks[1:]:
        random_launchers[f"[{index}]"] = _launcher(sid, "True")
        index += 1
    dialog_index = _next_index(giver["dialog_node"])
    existing = {random_sid: {"Launchers": random_launchers}, giver["dialog_sid"]: {
        "Launchers": {f"[{dialog_index}]": _launcher(ready, "True")}}}
    return existing, new_nodes
