"""Exercise exhausted-pool routing with synthetic native conditions, without a game."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import itertools
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker.cfgparse import parse
from s2tweaker.emit import emit_patch
from s2tweaker.quest_pool import build_pool_guard
from s2tweaker.tweaks import _merge_nested, _struct_dict


def launcher(sid, pin=""):
    return {"Excluding": "false", "Connections": {"[2]": {"SID": sid, "Name": pin}}}


def bridge(sid):
    return {"ConditionType": "EQuestConditionType::Bridge", "ConditionComparance": "EConditionComparance::NotEqual",
            "LinkedNodePrototypeSID": sid, "CompletedNodeLauncherNames": {"[0]": ""}}


class PoolTests(unittest.TestCase):
    def setUp(self):
        def node(sid, kind, **fields):
            return {"__new__": True, "SID": sid, "QuestSID": "RSQ_TEST", "NodeType": "EQuestNodeType::" + kind, **fields}
        self.source = {
            "Cap": node("Cap", "If", Conditions={"[3]": {"[1]": {
                "ConditionType": "EQuestConditionType::GlobalVariable", "ConditionComparance": "EConditionComparance::Less",
                "GlobalVariablePrototypeSID": "Count", "VariableValue": "3"}}}),
            "Draw": node("Draw", "Random", Launchers={"[4]": launcher("Cap", "True"), "[8]": launcher("Other")}),
            "Offer": node("Offer", "SetDialog", Launchers={"[2]": launcher("Cap", "False"), "[7]": launcher("Cancel")}),
        }
        self.slots = []
        for name in "ABC":
            conditions = {"[0]": {"[0]": bridge("Add" + name)}}
            if name in "BC":
                conditions["[1]"] = {"[0]": bridge("AddC" if name == "B" else "AddB")}
            if name in "BC":
                conditions["[2]"] = {"[0]": {"ConditionType": "EQuestConditionType::GlobalVariable",
                    "ConditionComparance": "EConditionComparance::Equal", "GlobalVariablePrototypeSID": "StoryB", "VariableValue": "true"}}
            self.source["Gate" + name] = node("Gate" + name, "If", Conditions=conditions,
                                              Launchers={"[0]": launcher("Draw", name)})
            self.source["Add" + name] = node("Add" + name, "Technical", Launchers={"[0]": launcher("Gate" + name, "True")})
            self.slots.append({"add": "Add" + name})
        self.gd = SimpleNamespace(questnodes=parse(emit_patch(self.source)), repeatable_job_slots=lambda quest: self.slots)
        self.giver = {"quest_sid": "RSQ_TEST", "cap_key": "Cap", "pool": 3,
                      "cap_node": self.gd.questnodes.children["Cap"], "cond_path": ("[3]", "[1]"),
                      "dialog_sid": "Offer", "dialog_node": self.gd.questnodes.children["Offer"]}

    def test_routes_partial_pools_without_removing_native_restrictions(self):
        before = deepcopy(self.gd.questnodes)
        changed, added = build_pool_guard(self.gd, self.giver)
        graph = deepcopy(self.source)
        _merge_nested(graph, changed)
        graph.update(added)
        graph = {sid: _struct_dict(node) for sid,node in parse(emit_patch(graph)).children.items()}
        self.assertEqual(self.gd.questnodes, before)
        self.assertEqual(graph['Draw']['Launchers']['[8]'], self.source['Draw']['Launchers']['[8]'])
        self.assertEqual(graph['Offer']['Launchers']['[2]'], self.source['Offer']['Launchers']['[2]'])
        for name in 'ABC':
            self.assertEqual(graph['Gate'+name]['Conditions'], self.source['Gate'+name]['Conditions'])
        self.assertTrue(all(n['NodeType'] == 'EQuestNodeType::If' for n in added.values()))

        for flags in itertools.product((False, True), repeat=3):
            selected = {"Add" + name for name, on in zip("ABC", flags) if on}
            for story in (False, True):
                for count in (0, 3, 5):
                    def evaluate(conditions):
                        results = []
                        for group in conditions.values():
                            for atom in group.values():
                                kind = atom['ConditionType']
                                if kind.endswith('Bridge'):
                                    equal = atom['LinkedNodePrototypeSID'] in selected
                                elif atom['GlobalVariablePrototypeSID'] == 'StoryB':
                                    equal = story
                                else:
                                    self.assertEqual(atom['ConditionComparance'], 'EConditionComparance::Greater')
                                    results.append(count > int(atom['VariableValue']))
                                    continue
                                results.append(equal if atom['ConditionComparance'].endswith('::Equal') else not equal)
                        return all(results)

                    events = [('Cap', 'True')]
                    terminals = []
                    while events:
                        source, pin = events.pop(0)
                        for sid, node in graph.items():
                            for entry in node.get('Launchers', {}).values():
                                if any(c['SID'] == source and c.get('Name', '') == pin for c in entry['Connections'].values()):
                                    if sid in ('Draw', 'Offer'):
                                        terminals.append(sid)
                                    elif sid in added:
                                        events.append((sid, 'True' if evaluate(node['Conditions']) else 'False'))
                    eligible = ('AddA' not in selected or
                                (story and 'AddB' not in selected and 'AddC' not in selected))
                    expected = ['Draw'] if eligible else ['Offer'] if count > 0 else []
                    self.assertEqual(terminals, expected, (selected, story, count))

    def test_unknown_layout_and_namespace_collisions_fail_export(self):
        self.gd.questnodes.children['S2T_RSQ_TEST_PoolCandidate_0'] = parse('Conflict : struct.begin\nstruct.end').children['Conflict']
        with self.assertRaisesRegex(ValueError, 'namespace collision'):
            build_pool_guard(self.gd, self.giver)
        del self.gd.questnodes.children['S2T_RSQ_TEST_PoolCandidate_0']
        del self.gd.questnodes.children['GateA'].children['Conditions']
        with self.assertRaisesRegex(ValueError, 'eligibility'):
            build_pool_guard(self.gd, self.giver)


if __name__ == '__main__':
    unittest.main()
