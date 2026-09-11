# Completed sibling job markers: 1.40 follow-up

Audited 11 September 2026 against the installed 2.0.5 config data after
[Molkerr's 1.40 report](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5639882302).
This is config research and a private candidate, not an in-game fix confirmation.

## Finding and scope

The contributor reports the previously unresolved case again: **both jobs
are ready for hand-in**; handing in the first removes the other map marker
while its journal entry survives. This is different from the earlier
successful case with one unfinished sibling at another target.

The original [marker audit](JOB_MARKERS_RESEARCH.md) still applies. All 69
return markers use the giver's actor GUID, and all markers from one giver
share that target. Independent journal IDs do not create independent actor
GUIDs. Config inspection cannot establish whether the engine removes a
coalesced actor marker or stops displaying an untracked surviving journal.

This follow-up found a stronger native candidate than was established by
the first audit: the shipped game **reapplies SetJournal Start and a marker
payload to an already active stage**. The operation has both an actor-marker
example and a repeatable example. It can therefore be reproduced as a
bounded experiment, guarded by the surviving journal and its return stage
both being active, after another job container has ended.

It remains possible that the engine ignores a redundant Start, retains
incorrect marker ownership, repeats a notification, or behaves differently
after saving. This research does not declare the operation idempotent or
the shared-actor problem fixed.

## Measured source scope

Primary file:
`vanilla/Stalker2/Content/GameLite/GameData/QuestNodePrototypes.cfg`.

| Measurement | Count |
|---|---:|
| Lines | 2,366,619 |
| Parsed top-level nodes | 84,244 |
| SetJournal nodes | 4,455 |
| Start / Finish / Fail / Cancel actions | 2,000 / 1,677 / 256 / 522 |
| ShowMarker nodes | 133 |
| TrackJournal nodes | 1 |
| Active quest equality predicates | 332 |
| Active quest-stage equality predicates | 502 |
| Repeatable QuestStage Start nodes | 96 |
| Giver parents / independent job subquests | 8 / 69 |
| Return-stage Start nodes | 69 |
| Return starts explicitly Repeatable=true | 23 |
| Return starts with Repeatable omitted | 46 |
| Same-job listeners on its return stage | 0 |
| Same-job JournalState predicates on its return stage | 0 |

The input SHA-256 is
`85508c26fc44b5e18e004c34dd8cbb599f463e97fdff18189c072193731eee01`.
The per-job return node and giver GUID inventories are in the original audit;
this follow-up retains all of them unchanged.

## Native evidence: active-stage marker reapplication

### Actor-target marker on an already active stage

At line 340583,
`E05_MQ01_SetJournal_E05_MQ01_GetInfoBravo_Start_1` uses these scalar paths:

| Path suffix | Native value |
|---|---|
| `NodeType` | `EQuestNodeType::SetJournal` |
| `JournalEntity` | `EJournalEntity::QuestStage` |
| `JournalAction` | `EJournalAction::Start` |
| `JournalQuestSID` | `E05_MQ01` |
| `JournalQuestStageSID` | `E05_MQ01_GetInfoBravo` |
| `Markers.[0].MarkerTargetQuestGuid` | `116884544D8D1A1C0B3023A7428A6315` |

Its first launcher requires the tick event and
`E05_MQ01_SetJournal_E05_MQ01_GetInfoBravo_Start_1_Pin_0` together. That
condition node, starting at line 340632, contains:

- `Conditions.[0].[0]`: QuestStage `E05_MQ01_KillBravo` is Finished;
- `Conditions.[1].[0]`: QuestStage `E05_MQ01_GetInfoBravo` is Active;
- `Conditions.ConditionCheckType = EConditionCheckType::And`.

Both predicates explicitly carry `JournalQuestSID = E05_MQ01`. Thus this
Start is not restricted to a Pending stage. It intentionally supplies an
actor marker while the same target stage is already Active. The example's
distance/alive marker conditions belong to that story objective and must
not be transplanted to repeatable jobs.

### Repeatable guarded reapplication

At line 1859944,
`SQ100_SetJournal_supack_SQ100_GetRidOfInterference` has:

- `Repeatable = true`;
- `JournalEntity = EJournalEntity::QuestStage`;
- `JournalAction = EJournalAction::Start`;
- `JournalQuestSID = supack_SQ100`;
- `JournalQuestStageSID = supack_SQ100_GetRidOfInterference`;
- `Launchers.[1].Excluding = false`;
- `Launchers.[1].Connections.[0].SID = SQ100_If_1`;
- `Launchers.[1].Connections.[0].Name = True`.

`SQ100_If_1`, at line 1862121, is itself Repeatable and includes the same
stage's Active state in `Conditions.[0].[0]`. Its other two alternatives
are Active stages `supack_SQ100_BackToBanzai` and
`supack_SQ100_SwitchOn`. The Start node includes a static-location marker.
The condition is therefore not evidence for an actor-target fix by itself;
it supplies native evidence for the repeatable guard/action wiring.

The actor example and repeatable example together justify a controlled
candidate using existing fields. They do not establish all engine side
effects of combining those patterns with the independent job journals.

## Exact ready-to-return predicate

Quest Active alone is insufficient: an unfinished job is also Active.
Checking a stage name ending in `_Finish` is a way to discover the live
return-stage prototype during export, not a runtime state test.

For each verified job, the candidate evaluates two explicit conditions in
separate groups under `ConditionCheckType = EConditionCheckType::And`:

| Field | Condition `[0].[0]` | Condition `[1].[0]` |
|---|---|---|
| `ConditionType` | `EQuestConditionType::JournalState` | Same |
| `ConditionComparance` | `EConditionComparance::Equal` | Same |
| `JournalEntity` | `EJournalEntity::Quest` | `EJournalEntity::QuestStage` |
| `JournalState` | `EJournalState::Active` | Same |
| `JournalQuestSID` | Existing isolated job SID | Same |
| `JournalQuestStageSID` | Absent | Existing isolated return-stage SID |

For Drabadan C02, the two identities are
`S2T_Job_RSQ04_C02` and `S2T_Job_RSQ04_C02_RSQ04_Finish`.

The predicate accepts only Active/Active. Pending, Finished, Failed and
Cancelled states in either position fail. Explicitly checking the quest
as well as the stage avoids assuming that cancelling a journal always
rewrites all of its persisted child-stage states.

All 69 live jobs have exactly one return-stage Start; its three marker
scalars are `MarkerTargetQuestGuid`, `AddOnCondition=false`, and
`RemoveOnCondition=false`. Unknown/multiple return layouts should fail a
future export rather than select an arbitrary candidate.

## Trigger and node ownership

The current isolation builder already observes every job-container End pin
at `S2T_<giver>_NoActiveJobs`, with `Repeatable=true`. Its True output alone
allows the original BridgeCleanUp. Its False output means a sibling job is
still Active; it currently has no marker action.

An experimental addition can use that **False output** as its only trigger.
This keeps the existing cleanup gate, job endings, reward paths, journals,
stage IDs and translations unchanged. The private candidate adds, per job:

1. A Repeatable If node owned by the giver parent, launched by
   `S2T_<giver>_NoActiveJobs` / `False`, applying the two ready predicates.
2. A separate Repeatable SetJournal node, also owned by the giver parent,
   launched only by the new If / `True` output. It copies the live return
   marker payload and the already isolated journal/stage references.

A **new SID** is essential. Reusing the original return-start node would
also replay that node's outgoing graph connections. The separate clone has
no existing consumers and must not feed the original reward, dialog, stage
completion or container End nodes. It must not carry a quest-start launcher
or a loop/tick launcher. `SetQuestActive` is absent from the live return
nodes and stays absent; there is no forced tracking in this candidate.

The parent ownership is deliberate. For example,
`RSQ04_C02_End.ExcludeAllNodesInContainer = true`; putting recovery nodes in
the job container being handed in could exclude them with that container.
The surviving giver round remains available until the existing no-active-
jobs guard permits its cleanup. No blanket change to ExcludeAllNodesInContainer
is justified.

The post-End trigger also covers a job cancellation when another completed
job survives. It is **not** proof that all cancellation events are already
settled in the engine's event queue. This requires the cancellation test
below, especially when the shared decline dialog cancels several jobs.

## Tracking is a separate possible cause

The sole native tracking node is `EmissionQuest_TrackJournal`, line 979370:

- `NodeType = EQuestNodeType::TrackJournal`;
- `JournalQuestSID = EmissionQuest`;
- its launcher follows `EmissionQuest_EmissionQuestStart`.

It changes which journal is tracked. It has no Markers payload or stage
action. It is a legitimate tracking operation, but does not establish a
marker-creation operation.

Before treating a tracking node as a fix, explicitly select/track the
surviving journal in the UI. If that restores the marker, changing tracking
may be sufficient. If it does not, automatically tracking it is unlikely to
address lost marker ownership. Forcing all surviving journals to be tracked
in sequence would also override the player's selection and leave only the
last one selected; that is not a per-job marker repair.

All 133 ShowMarker nodes instead take `MarkerSID`, primarily a discovered
location identifier, with Explored/Discovered metadata. None of the 69 job
return rows expose such an identity. There is no basis for inventing a
per-job actor MarkerSID or a new actor GUID. The complete SetJournal action
inventory contains Start, Finish, Fail and Cancel, with no explicit Refresh.

## Private candidate checks

Ignored local research artifacts live under
`out/issue9_140_followup/marker_research/`:

- `audit.py` / `audit.json`: action, state, marker and repeatability inventory;
- `inspect_patterns.py` / `patterns.json`: native predecessor predicates;
- `candidate_audit.py` / `candidate.json`: all 69 return stages, terminal
  paths, parent cleanup inputs, listeners and native exemplars;
- `build_candidate.py`: emits the separate, uninstalled candidate;
- `S2Tweaker_MarkerCandidate.cfg` / `candidate_checks.json`: candidate and
  assertion result.

The candidate has 138 new nodes: 69 If guards and 69 standalone marker
reapplication nodes. Its emitted CFG parsed successfully. All 1,725
combinations of the five native states for both predicates across 69 jobs
passed the intended ready-state truth table. The checks also verify live
marker equality, isolated identities, parent ownership, Repeatable flags,
single incoming trigger per action, and the absence of pre-existing graph
consumers for the new action IDs.

These checks evaluate emitted data. They do not run the game's scheduler,
journal notification logic, save system or map/compass renderer. The private
candidate is not installed. The private artifacts describe the initial
research checkpoint before implementation.

## Experimental implementation follow-up

After review of this research, the existing multi-job builder gained the
guarded reapplication path described above. Production IDs use
`S2T_ReturnMarker_<job>_Ready` and `S2T_ReturnMarker_<job>_Reapply`; all
existing journal/stage IDs and completion paths stay the same. The path is
enabled only with the existing multi-job option. It fails export on an
unknown return-marker shape, a conflicting new node SID, or a new native
listener on the return stage. There is no automatic TrackJournal action.

`tests/test_job_return_markers.py` checks source payload preservation,
inactive/unfinished/terminal-state rejection, standalone graph connections,
unknown-layout and namespace guards, and the 69 live job mappings. These
remain data-level regressions and do not remove the in-game limitations.

## Required game experiment and warnings

Use a save from before accepting the test jobs with the existing independent
journal IDs. Keep current working job definitions present; do not remove
their pak with jobs still active or replace them with vanilla journal IDs.

1. **Baseline tracking check:** complete two jobs from one giver. Track
   each before hand-in, hand one in, then explicitly track the survivor.
   Record map and compass separately, including whether reload restores it.
2. **Candidate, both orders:** repeat with the isolated candidate and hand
   in C01 then C02, then reverse. The survivor must retain its marker, active
   journal, reward and hand-in dialog. Record duplicate stage notifications.
3. **Unfinished control:** complete only one job; its sibling must retain
   its actual objective marker and must not gain a premature giver marker.
4. **Three ready jobs:** hand in successively. Recovery must work after both
   the first and second hand-in, proving repeated guard/action activation.
5. **Cancellation:** cancel one job with a ready sibling, then exercise the
   shared decline/cancel-all path. Completed or cancelled journals must not
   regain a live stage or leave ghost markers.
6. **Persistence and final cleanup:** save/reload with a surviving ready
   job, finish it, verify no stale marker and accept another round normally.

Do not add an artificial delay without evidence. Do not cancel/restart the
whole journal, reassign reward outputs, alter the source actor GUID, or
substitute a static world location for the moving giver. Do not claim that
a truth-table or Pak readback test proves marker behavior in the game.

The finding supports an **experimental, tightly guarded implementation**
of live marker reapplication. The new contributor report is enough to
justify testing that candidate; game confirmation is still required before
describing the marker issue as fixed or closing issue #9.
