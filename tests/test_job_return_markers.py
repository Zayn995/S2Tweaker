"""Guarded marker reapplication data checks; these do not emulate the engine."""
from copy import deepcopy
from itertools import product
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse
from s2tweaker.emit import emit_patch
from s2tweaker.quest_jobs import _return_marker_reapplication, build_job_isolation
from s2tweaker.tweaks import _struct_dict, Settings, build_patches


def fixture():
    root = cfgparse.parse('''
ReturnStart : struct.begin
   SID = ReturnStart
   NodePrototypeVersion = 7
   QuestSID = JobA
   NodeType = EQuestNodeType::SetJournal
   JournalEntity = EJournalEntity::QuestStage
   JournalAction = EJournalAction::Start
   JournalQuestSID = ParentJournal
   JournalQuestStageSID = Different_Finish
   Launchers : struct.begin
      [2] : struct.begin
         Excluding = false
         Connections : struct.begin
            [5] : struct.begin
               SID = ObjectiveDone
               Name = RewardWouldRunFromOldNode
            struct.end
         struct.end
      struct.end
   struct.end
   Markers : struct.begin
      [0] : struct.begin
         MarkerTargetQuestGuid = 1234567890ABCDEF1234567890ABCDEF
         AddOnCondition = false
         RemoveOnCondition = false
      struct.end
   struct.end
struct.end
''')
    return SimpleNamespace(questnodes=root), [('ReturnStart', root.children['ReturnStart'])]


def build(gd, job_nodes, reserved=None):
    return _return_marker_reapplication(
        gd, 'GiverParent', 'JobA', job_nodes, 'ParentJournal', 'S2T_Job_JobA',
        {'Different_Finish':'S2T_Job_JobA_Different_Finish'},
        'ExistingNoActiveJobs', reserved or {})


def guard_passes(node, quest_state, stage_state):
    conditions = node.children['Conditions']
    assert conditions.values['ConditionCheckType'] == 'EConditionCheckType::And'
    state = {'EJournalEntity::Quest':quest_state, 'EJournalEntity::QuestStage':stage_state}
    return all(state[rule.values['JournalEntity']] == rule.values['JournalState']
               for group in conditions.children.values() for rule in group.children.values())


class ReturnMarkerData(unittest.TestCase):
    def test_live_payload_is_copied_without_replaying_original_consumers(self):
        gd, job_nodes = fixture()
        original = deepcopy(_struct_dict(job_nodes[0][1]))
        parsed = cfgparse.parse(emit_patch(build(gd, job_nodes))).children
        self.assertEqual(len(parsed), 2)
        guard, action = (parsed['S2T_ReturnMarker_JobA_' + suffix] for suffix in ('Ready','Reapply'))
        self.assertEqual(_struct_dict(action.children['Markers']), original['Markers'])
        self.assertEqual(action.values['NodePrototypeVersion'], '7')
        self.assertEqual(action.values['JournalQuestStageSID'], 'S2T_Job_JobA_Different_Finish')
        self.assertEqual(action.values['JournalAction'], 'EJournalAction::Start')
        self.assertEqual(action.values['JournalEntity'], 'EJournalEntity::QuestStage')
        for node in (guard, action):
            self.assertEqual(node.values['QuestSID'], 'GiverParent')
            self.assertEqual(node.values['Repeatable'], 'true')
            self.assertTrue(all(not part.attrs for part in node.walk()))
            self.assertFalse({'LaunchOnQuestStart','SetQuestActive','StartDelay'} & node.values.keys())
        self.assertEqual(_struct_dict(guard.children['Launchers']), {
            '[0]':{'Excluding':'false','Connections':{'[0]':{'SID':'ExistingNoActiveJobs','Name':'False'}}}})
        self.assertEqual(_struct_dict(action.children['Launchers']), {
            '[0]':{'Excluding':'false','Connections':{'[0]':{'SID':guard.name,'Name':'True'}}}})
        self.assertEqual(_struct_dict(job_nodes[0][1]), original)

    def test_only_a_live_ready_sibling_passes_including_stale_terminal_stage(self):
        gd, job_nodes = fixture()
        guard = cfgparse.parse(emit_patch(build(gd,job_nodes))).children['S2T_ReturnMarker_JobA_Ready']
        states = ['EJournalState::' + x for x in ('Pending','Active','Finished','Failed','Cancelled')]
        for quest, stage in product(states,repeat=2):
            with self.subTest(quest=quest,stage=stage):
                self.assertEqual(guard_passes(guard,quest,stage), quest==stage=='EJournalState::Active')
        # A later completion must find the same remaining ready sibling;
        # emitted Repeatable=true is checked above, scheduler behavior is not.
        for stage in ('Active','Active','Finished','Active'):
            self.assertEqual(guard_passes(guard,'EJournalState::Active','EJournalState::'+stage),stage=='Active')

    def test_unknown_layouts_and_return_listeners_fail_closed(self):
        def no_marker(n): n.children.pop('Markers')
        def extra_marker(n): n.children['Markers'].children['[1]']=deepcopy(n.children['Markers'].children['[0]'])
        def conditional(n): n.children['Markers'].children['[0]'].values['AddOnCondition']='true'
        def forced_tracking(n): n.values['SetQuestActive']='true'
        for mutation in (no_marker,extra_marker,conditional,forced_tracking):
            gd, job_nodes = fixture()
            mutation(job_nodes[0][1])
            with self.subTest(mutation=mutation.__name__), self.assertRaisesRegex(ValueError,'return-marker layout'):
                build(gd,job_nodes)
        gd, job_nodes = fixture()
        with self.assertRaisesRegex(ValueError,'return-stage layout'):
            build(gd,job_nodes+job_nodes)
        listener = cfgparse.CfgStruct('NewReturnListener',values={
            'NodeType':'EQuestNodeType::OnJournalQuestEvent','JournalQuestSID':'ParentJournal',
            'JournalQuestStageSID':'Different_Finish'})
        with self.assertRaisesRegex(ValueError,'return-stage listener'):
            build(gd,job_nodes+[('NewReturnListener',listener)])

    def test_namespace_collisions_fail_before_adding_nodes(self):
        for suffix in ('Ready','Reapply'):
            sid='S2T_ReturnMarker_JobA_'+suffix
            gd,job_nodes=fixture()
            with self.assertRaisesRegex(ValueError,'namespace collision'):
                build(gd,job_nodes,{sid:{}})
            gd.questnodes.children[sid]=cfgparse.CfgStruct(sid)
            with self.assertRaisesRegex(ValueError,'namespace collision'):
                build(gd,job_nodes)

    @unittest.skipUnless((ROOT/'vanilla/Stalker2/Content/GameLite/GameData/QuestNodePrototypes.cfg').exists(),
                         'Local game data unavailable; synthetic data checks still run in CI')
    def test_all_live_jobs_have_only_guarded_standalone_reapplication(self):
        from s2tweaker.gamedata import GameData
        gd=GameData(ROOT/'vanilla/Stalker2/Content/GameLite/GameData')
        self.assertEqual(build_patches(gd,Settings()),{})
        self.assertNotIn('questnodes',gd.__dict__)
        aliases={}
        changed,new,journals=build_job_isolation(gd,localization_aliases=aliases)
        parsed=cfgparse.parse(emit_patch(new)).children
        recovery={sid:n for sid,n in parsed.items() if sid.startswith('S2T_ReturnMarker_')}
        self.assertEqual(len(recovery),138)
        self.assertEqual(len(journals),69)
        self.assertEqual(len(aliases),208)
        refs={part.values.get('SID') for node in gd.questnodes.children.values() for part in node.walk()}
        self.assertFalse(recovery.keys() & refs)
        for giver in gd.repeatable_quest_givers():
            parent=giver['quest_sid']
            cleanup=changed[giver['cleanup_sid']]['Launchers']
            self.assertTrue(all(next(iter(row['Connections'].values())) == {
                'SID':f'S2T_{parent}_NoActiveJobs','Name':'True'} for row in cleanup.values()))
            for slot in gd.repeatable_job_slots(parent):
                job=gd.questnodes.children[slot['container']].values['ContaineredQuestPrototypeSID']
                guard=recovery[f'S2T_ReturnMarker_{job}_Ready']
                action=recovery[f'S2T_ReturnMarker_{job}_Reapply']
                self.assertEqual(action.values['QuestSID'],parent)
                self.assertEqual(action.values['JournalQuestSID'],'S2T_Job_'+job)
                self.assertEqual(action.values['JournalAction'],'EJournalAction::Start')
                self.assertEqual(action.values['JournalEntity'],'EJournalEntity::QuestStage')
                sources=[n for n in gd.questnodes.children.values() if n.values.get('QuestSID')==job
                         and n.values.get('JournalAction')=='EJournalAction::Start'
                         and n.values.get('JournalQuestStageSID','').endswith('_Finish')]
                self.assertEqual(len(sources),1)
                self.assertEqual(_struct_dict(action.children['Markers']),_struct_dict(sources[0].children['Markers']))
                self.assertEqual(changed[sources[0].name],{
                    'JournalQuestSID':action.values['JournalQuestSID'],
                    'JournalQuestStageSID':action.values['JournalQuestStageSID']})
                self.assertEqual(guard.children['Launchers'].get('[0].Connections.[0].SID'),f'S2T_{parent}_NoActiveJobs')
                self.assertEqual(guard.children['Launchers'].get('[0].Connections.[0].Name'),'False')
                for quest,stage in product(('Pending','Active','Finished','Failed','Cancelled'),repeat=2):
                    self.assertEqual(guard_passes(guard,'EJournalState::'+quest,'EJournalState::'+stage),
                                     quest==stage=='Active')


if __name__=='__main__':
    unittest.main()
