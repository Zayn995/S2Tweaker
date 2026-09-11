"""Regression for external story cancellation of isolated job journals.

Checks the emitted event/condition/action links against real game data.
The state table is a config regression, not an emulation of the game engine.
"""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, _struct_dict

gd = GameData(ROOT / 'vanilla/Stalker2/Content/GameLite/GameData')
assert build_patches(gd, Settings()) == {}
assert 'questnodes' not in gd.__dict__
patches = build_patches(gd, Settings(repeatable_jobs_multi=True))
new = cfgparse.parse(patches['QuestNodePrototypes/S2Tweaker_Jobs.cfg']).children
changed = cfgparse.parse(patches['QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg']).children
journals = cfgparse.parse(patches['JournalQuestPrototypes/S2Tweaker_Jobs.cfg']).children

source = gd.questnodes.children['Zalesie_Hub_SetJournal_RSQ01']
owner = source.values['QuestSID']
assert source.values['JournalAction'] == 'EJournalAction::Cancel'
assert source.values['JournalQuestSID'] == 'RSQ01'
assert source.name not in changed  # preserve the original story action too
warlock = next(g for g in gd.repeatable_quest_givers() if g['quest_sid'] == 'RSQ01')
expected = {'S2T_Job_' + gd.questnodes.children[s['container']].values['ContaineredQuestPrototypeSID']
            for s in gd.repeatable_job_slots(warlock['quest_sid'])}
assert len(expected) == 6
cancels = [n for n in new.values() if n.values.get('QuestSID') == owner
           and n.values.get('NodeType') == 'EQuestNodeType::SetJournal']
assert len(cancels) == 6, 'Story cancellation does not reach the six isolated Warlock journals'
assert {n.values['JournalQuestSID'] for n in cancels} == expected

guards = []
for cancel in cancels:
    assert cancel.values['JournalEntity'] == 'EJournalEntity::Quest'
    assert cancel.values['JournalAction'] == 'EJournalAction::Cancel'
    assert 'LaunchOnQuestStart' not in cancel.values and 'StartDelay' not in cancel.values
    inputs = _struct_dict(cancel.children['Launchers'])
    assert len(inputs) == 1
    launcher = next(iter(inputs.values()))
    assert launcher['Excluding'] == 'false' and len(launcher['Connections']) == 1
    connection = next(iter(launcher['Connections'].values()))
    assert connection['Name'] == 'True'
    guard = new[connection['SID']]
    assert guard.values['QuestSID'] == owner  # survives the RSQ container shutdown
    assert guard.values['NodeType'] == 'EQuestNodeType::If'
    assert _struct_dict(guard.children['Launchers']) == _struct_dict(source.children['Launchers'])
    assert _struct_dict(guard.children['Conditions']) == {
        'ConditionCheckType': 'EConditionCheckType::And', '[0]': {'[0]': {
            'ConditionType': 'EQuestConditionType::JournalState',
            'ConditionComparance': 'EConditionComparance::Equal',
            'JournalEntity': 'EJournalEntity::Quest',
            'JournalState': 'EJournalState::Active',
            'JournalQuestSID': cancel.values['JournalQuestSID']}}}
    for node in (guard, cancel):
        assert node.name not in gd.questnodes.children and 'bpatch' not in node.attrs
    guards.append(guard)

# Read the actual story gate; neither an ordinary tick before this stage
# nor a completed stage without the tick may trigger the new cancellation.
source_inputs = _struct_dict(source.children['Launchers'])
assert len(source_inputs) == 1
connections = next(iter(source_inputs.values()))['Connections']
condition_sid = next(c['SID'] for c in connections.values()
                     if gd.questnodes.children[c['SID']].values['NodeType'] == 'EQuestNodeType::Condition')
condition = gd.questnodes.children[condition_sid].children['Conditions']
rule = next(iter(next(iter(condition.children.values())).children.values())).values
assert rule['ConditionType'] == 'EQuestConditionType::NodeState'
assert rule['ConditionComparance'] == 'EConditionComparance::Equal'
assert rule['NodeState'] == 'EQuestNodeState::Finished'
assert rule['TargetNode'] in gd.questnodes.children
tick_sid = next(c['SID'] for c in connections.values() if c['SID'] != condition_sid)
assert gd.questnodes.children[tick_sid].values['NodeType'] == 'EQuestNodeType::OnTickEvent'


def apply_story(state, tick, stage_finished):
    events = set()
    if tick:
        events.add(tick_sid)
        if stage_finished:
            events.add(condition_sid)
    result = dict(state)
    for guard, cancel in zip(guards, cancels):
        launchers = _struct_dict(guard.children['Launchers'])
        triggered = any(l['Excluding'] == 'false' and
                        all(c['SID'] in events for c in l['Connections'].values())
                        for l in launchers.values())
        condition = guard.children['Conditions'].children['[0]'].children['[0]'].values
        if triggered and state[condition['JournalQuestSID']] == condition['JournalState']:
            result[cancel.values['JournalQuestSID']] = 'EJournalState::Cancelled'
    return result


ids = sorted(expected)
states = ['EJournalState::' + n for n in ('Active', 'Finished', 'Cancelled', 'Unset')]
scenarios = 0
for combination in itertools.product(states, repeat=len(ids)):
    state = dict(zip(ids, combination))
    state['UnrelatedStoryJournal'] = states[0]
    for tick, stage in ((False, False), (False, True), (True, False)):
        assert apply_story(state, tick, stage) == state
    result = apply_story(state, True, True)
    for journal, previous in state.items():
        expected_state = states[2] if journal in expected and previous == states[0] else previous
        assert result[journal] == expected_state
    assert apply_story(result, True, True) == result
    scenarios += 1

assert len([n for n in new.values() if n.values.get('QuestSID') == owner]) == 12
assert len(journals) == 69  # no extra journal entries for this repair
print(f'PASS: external story gate, 6 active-only cancellations, {scenarios} state combinations; no engine test')
