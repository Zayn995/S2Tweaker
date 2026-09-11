"""Emitted-graph regressions for issue #9; these are NOT engine play tests."""
import itertools
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse
from s2tweaker.gamedata import GameData, CACHE_SCHEMA, NEEDED_FILES
from s2tweaker.tweaks import Settings, build_patches, _struct_dict, _merge_nested
from s2tweaker.quest_jobs import build_job_isolation

gd = GameData(ROOT / 'vanilla/Stalker2/Content/GameLite/GameData')
assert CACHE_SCHEMA >= 26 and 'JournalQuestPrototypes.cfg.bin' in NEEDED_FILES
assert not build_patches(gd, Settings())
assert 'journals' not in gd.__dict__ and 'questnodes' not in gd.__dict__
p = build_patches(gd, Settings(repeatable_jobs_multi=True))
patched = cfgparse.parse(p['QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg']).children
new = cfgparse.parse(p['QuestNodePrototypes/S2Tweaker_Jobs.cfg']).children
journals = cfgparse.parse(p['JournalQuestPrototypes/S2Tweaker_Jobs.cfg']).children
assert len(journals) == 69
effective = {k: _struct_dict(v) for k, v in gd.questnodes.children.items()}
for key, node in patched.items():
    assert key in effective
    _merge_nested(effective[key], _struct_dict(node))


def guard_allows(guard, state):
    conditions = guard.children['Conditions']
    assert conditions.values['ConditionCheckType'] == 'EConditionCheckType::And'
    results = []
    for group in conditions.children.values():
        assert len(group.children) == 1
        rule = next(iter(group.children.values())).values
        assert rule['ConditionType'] == 'EQuestConditionType::JournalState'
        assert rule['ConditionComparance'] == 'EConditionComparance::NotEqual'
        assert rule['JournalEntity'] == 'EJournalEntity::Quest'
        results.append(state.get(rule['JournalQuestSID'], 'EJournalState::Unset') != rule['JournalState'])
    return all(results)


scenarios = 0
for giver in gd.repeatable_quest_givers():
    slots = gd.repeatable_job_slots(giver['quest_sid'])
    guard_sid = f"S2T_{giver['quest_sid']}_NoActiveJobs"
    guard = new[guard_sid]
    assert _struct_dict(guard.children['Launchers']) == _struct_dict(
        gd.questnodes.children[giver['cleanup_sid']].children['Launchers'])
    cleanup = effective[giver['cleanup_sid']]
    for launcher in cleanup['Launchers'].values():
        assert launcher['Excluding'] == 'false'
        assert list(launcher['Connections'].values()) == [{'SID': guard_sid, 'Name': 'True'}]
    # The End really shuts down the exhausted round again; no lingering
    # cancel/offer nodes from the former End=false workaround.
    assert giver['end_sid'] not in patched
    assert effective[giver['end_sid']]['ExcludeAllNodesInContainer'] == 'true'
    ids, finish_nodes = [], {}
    for slot in slots:
        subquest = effective[slot['container']]['ContaineredQuestPrototypeSID']
        job_id = f'S2T_Job_{subquest}'
        ids.append(job_id)
        journal = journals[job_id]
        assert journal.values['SID'] == job_id and 'bpatch' not in journal.attrs
        assert journal.values.get('Name'), job_id
        stages = set(journal.children['Stages'].children)
        assert stages and all(x.startswith(job_id + '_') for x in stages)
        job_nodes = [(k, n) for k, n in effective.items() if n.get('QuestSID') == subquest]
        finish_nodes[job_id] = []
        for k, n in job_nodes:
            if n.get('NodeType') == 'EQuestNodeType::SetJournal':
                assert n['JournalQuestSID'] == job_id, k
                if 'JournalQuestStageSID' in n:
                    assert n['JournalQuestStageSID'] in stages, k
                if n.get('JournalEntity') == 'EJournalEntity::Quest' and n.get('JournalAction') == 'EJournalAction::Finish':
                    finish_nodes[job_id].append(n)
            original = _struct_dict(gd.questnodes.children[k])
            # Reward amounts, destinations, dialog phrases and launchers
            # cannot change as a side effect of journal isolation.
            def strip_refs(d):
                return {a: strip_refs(b) if isinstance(b, dict) else b for a, b in d.items()
                        if a not in ('JournalQuestSID', 'JournalQuestStageSID')}
            assert strip_refs(n) == strip_refs(original), k
        assert finish_nodes[job_id], job_id
    assert set(ids) == {next(iter(group.children.values())).values['JournalQuestSID']
                        for group in guard.children['Conditions'].children.values()}
    # All ordered pairs: finish one while the other is unfinished OR ready
    # for hand-in. Both are Active at journal-quest level. Simulate a saved
    # state roundtrip, reverse hand-in orders, cancellations and next round.
    for first, second in itertools.permutations(ids, 2):
        state = {first: 'EJournalState::Active', second: 'EJournalState::Active'}
        assert not guard_allows(guard, state)
        for end in finish_nodes[first]:
            state[end['JournalQuestSID']] = 'EJournalState::Finished'
        state = deepcopy(state)
        assert state[second] == 'EJournalState::Active'
        assert not guard_allows(guard, state)
        state[second] = 'EJournalState::Finished'
        assert guard_allows(guard, state)
        state[first] = 'EJournalState::Active'  # subsequent round
        assert not guard_allows(guard, state)
        state[first] = 'EJournalState::Cancelled'
        assert guard_allows(guard, state)
        scenarios += 1

# Incomplete metadata must fail rather than ship a half-isolated journal.
original_journals = gd.journals
gd.journals = cfgparse.parse('')
try:
    build_job_isolation(gd)
except ValueError as error:
    assert 'Missing journal' in str(error)
else:
    raise AssertionError('Missing journal data was silently accepted')
finally:
    gd.journals = original_journals

print(f'PASS: 69 isolated jobs, 8 guarded round cleanups, {scenarios} ordered hand-in scenarios; no engine test')
