# Repeatable-job return markers: config research

Audited 11 September 2026 against the installed 2.0.5 config data and
the current journal-isolation builder. This is config research, not an
in-game marker test.

## Result

No incorrect marker-removal command or sibling-journal completion was found
in the generated config. The complete marker data in all 318 marker-bearing
job/parent nodes is unchanged by journal isolation. Each of the 69 jobs has
one return marker, and jobs from the same giver intentionally target the
same NPC GUID. This shared actor target is consistent with a marker
de-duplication or tracked-quest display problem when two completed jobs are
ready for hand-in, but config alone does not establish that engine behavior.

There is no justified production marker patch from this audit. In particular,
changing arbitrary marker IDs, restarting a sibling stage, or adding a
second marker system would be speculative and could alter working quest
state. The relevant two-completed-jobs case should be reproduced while
checking whether selecting/tracking the surviving journal restores its
return marker.

## Report boundary

Molkerr's [initial 1.39 report](https://drive.google.com/file/d/17vQHEYOswsaVd96rwJ_USlF_0l1NF-q8)
states that handing in one quest retains its sibling in the journal but
loses the sibling's marker. The [follow-up clean-save video](https://drive.google.com/file/d/1_CKj2d3KWK0lRW1Zd4a-4DBdThPd6trB)
instead retains an unfinished sibling and its map marker. Its 0:42 journal
view identifies `S2T_Job_RSQ04_C02`. The second result does not verify two
simultaneously active return markers on the same giver.

The meaningful distinction is therefore an **unfinished job's objective
marker at another target** versus a **completed job's return marker on the
same giver**. Player reports support investigating this
distinction; they do not prove the underlying engine cause.

## Input scope and measured fields

Primary source:
`vanilla/Stalker2/Content/GameLite/GameData/QuestNodePrototypes.cfg`,
2,366,619 lines and 84,244 parsed top-level nodes. The analyzed job scope is
69 subquests plus eight parent giver quests, identified from existing
container links rather than just SID prefixes.

The previous stage audit also searched all 491 local `.cfg` files. Stage
operations are always paired with an explicit JournalQuestSID; see
[journal localization research](JOB_LOCALIZATION_CFG_RESEARCH.md).

The complete marker-named scalar key counts in QuestNodePrototypes are:

| Scalar key | All quest nodes | 69 jobs plus eight parents |
|---|---:|---:|
| `MarkerRadius` | 487 | 228 |
| `MarkerRadiusSquared` | 58 | 4 |
| `ZoneSubMarkers` | 437 | 224 |
| `Markers` | 322 | 23 |
| `MarkerSID` | 133 | 0 |
| `MarkerTargetQuestGuid` | 977 | 289 |
| `MarkerDescription` | 98 | 0 |

`Markers` in this table counts explicit empty scalar fields. The 318
marker-bearing scoped nodes contain 295 nested Markers structs and 23
empty Markers scalars.
There is no ActorMarkerSID or MarkerPrototypeSID field in these job nodes.
There is also no scoped MarkerSID field and no scoped ShowMarker node.
The 133 global MarkerSID fields belong to the separate ShowMarker mechanism,
with values such as `sid_locations_loc_01_scientists_bunker_name`. They are
not evidence for a per-job return-marker identity override.

## Complete return-marker baseline

Each of the 69 jobs has exactly one SetJournal node with:

- `JournalEntity = EJournalEntity::QuestStage`;
- `JournalAction = EJournalAction::Start`;
- an original `JournalQuestStageSID` ending in `_Finish`;
- exactly one marker row, `Markers.[0]`;
- exactly these three marker scalars: `MarkerTargetQuestGuid`,
  `AddOnCondition = false`, `RemoveOnCondition = false`.

There is no custom marker identity, explicit removal operation, radius,
location, condition struct or marker description in those 69 return rows.
Neither flag is accidentally enabled. The target GUID differs by giver,
and is the same for all that giver's jobs:

| Parent giver quest | Jobs/return markers | Shared target GUID |
|---|---:|---|
| `RSQ01` | 6 | `0D0457214D9959BD245322A0F6502D49` |
| `RSQ04` | 10 | `0A9B5BCC4CEE5A8152C8D88CA0C5254C` |
| `RSQ05` | 8 | `7FE2532443129907B6BA259BEC0306A4` |
| `RSQ06_C00___SIDOROVICH` | 9 | `50D530D64ECEC8C5C8499C95EA5BA59B` |
| `RSQ07_C00_TSEMZAVOD` | 9 | `BD493D9A437E3E606BEE5F8ABC96F60B` |
| `RSQ08_C00_ROSTOK` | 9 | `1792AC6A4539617277E8189ABA6B917E` |
| `RSQ09_C00_MALAHIT` | 9 | `D9AF01A14AA7D12C40650EAD62D5BF0E` |
| `RSQ10_C00_HARPY` | 9 | `7F2626BE4D1747472A79178CA5B0B51D` |

The full return-start-node inventory follows. The concrete marker path is
`<node>.Markers.[0].MarkerTargetQuestGuid`; its value is the corresponding
giver's target from the table above. Both condition flags at that same path
are false for every row.

| Job subquest | Return-stage start node |
|---|---|
| `RSQ01_C01` | `RSQ01_C01_Start_C01_Finish` |
| `RSQ01_C02` | `RSQ01_C02_Start_ReturnToWarlock` |
| `RSQ01_C03` | `RSQ01_C03_BackToWarlock` |
| `RSQ01_C04` | `RSQ01_C04_RSQ01_C04_Start_ReturnToWarlock` |
| `RSQ01_C05` | `RSQ01_C05_Start_ReturnToWarlock` |
| `RSQ01_C06` | `RSQ01_C06_Start_ReturnToWarlock_1` |
| `RSQ04_C01` | `RSQ04_C01_SetJournal_RSQ04_Finish` |
| `RSQ04_C02` | `RSQ04_C02_SetJournal_RSQ04_Finish` |
| `RSQ04_C03` | `RSQ04_C03_SetJournal_RSQ04_Finish` |
| `RSQ04_C04` | `RSQ04_C04_SetJournal_RSQ04_Finish` |
| `RSQ04_C05` | `RSQ04_C05_BackToDrabadan` |
| `RSQ04_C06` | `RSQ04_C06_SetJournal_RSQ04_Finish` |
| `RSQ04_C10` | `RSQ04_C10_BackToDrabadan` |
| `RSQ04_C07` | `RSQ04_C07_BackToWarlock` |
| `RSQ04_C08` | `RSQ04_C08_BackToWarlock` |
| `RSQ04_C09` | `RSQ04_C09_BackToWarlock` |
| `RSQ05_C01` | `RSQ05_C01_SetJournal_RSQ05_Finish` |
| `RSQ05_C02` | `RSQ05_C02_SetJournal_RSQ05_Finish` |
| `RSQ05_C04` | `RSQ05_C04_SetJournal_RSQ05_Finish` |
| `RSQ05_C05` | `RSQ05_C05_SetJournal_RSQ05_Finish` |
| `RSQ05_C10` | `RSQ05_C10_SetJournal_RSQ05_Finish` |
| `RSQ05_C07` | `RSQ05_C07_BackToSich` |
| `RSQ05_C08` | `RSQ05_C08_BackToSich` |
| `RSQ05_C09` | `RSQ05_C09_BackToSich` |
| `RSQ06_C01___K_Z` | `RSQ06_C01___K_Z_SetJournal_RSQ06_Finish_1` |
| `RSQ06_C02___K_M` | `RSQ06_C02___K_M_SetJournal_RSQ06_Finish` |
| `RSQ06_C03___K_B` | `RSQ06_C03___K_B_SetJournal_RSQ06_Finish` |
| `RSQ06_C04___K_S` | `RSQ06_C04___K_S_SetJournal_RSQ06_Finish` |
| `RSQ06_C05___B_B` | `RSQ06_C05___B_B_SetJournal_RSQ06_Finish` |
| `RSQ06_C06___B_A` | `RSQ06_C06___B_A_BackToSich` |
| `RSQ06_C07___B_A` | `RSQ06_C07___B_A_BackToSich` |
| `RSQ06_C08___B_A` | `RSQ06_C08___B_A_BackToSich` |
| `RSQ06_C09___S_P` | `RSQ06_C09___S_P_SetJournal_RSQ06_Finish` |
| `RSQ07_C01_K_Z` | `RSQ07_C01_K_Z_SetJournal_RSQ07_Finish` |
| `RSQ07_C02_K_M` | `RSQ07_C02_K_M_SetJournal_RSQ07_Finish` |
| `RSQ07_C03_K_M` | `RSQ07_C03_K_M_SetJournal_RSQ07_Finish` |
| `RSQ07_C04_K_B` | `RSQ07_C04_K_B_SetJournal_RSQ07_Finish` |
| `RSQ07_C05_B_B` | `RSQ07_C05_B_B_SetJournal_RSQ07_Finish` |
| `RSQ07_C06_B_A` | `RSQ07_C06_B_A_BackToSich` |
| `RSQ07_C09_S_P` | `RSQ07_C09_S_P_SetJournal_RSQ07_Finish` |
| `RSQ07_C07_B_A` | `RSQ07_C07_B_A_BackToSich` |
| `RSQ07_C08_B_A` | `RSQ07_C08_B_A_BackToSich` |
| `RSQ08_C01_K_M` | `RSQ08_C01_K_M_SetJournal_RSQ08_Finish` |
| `RSQ08_C02_K_B` | `RSQ08_C02_K_B_SetJournal_RSQ08_Finish` |
| `RSQ08_C03_K_S` | `RSQ08_C03_K_S_SetJournal_RSQ08_Finish` |
| `RSQ08_C04_B_B` | `RSQ08_C04_B_B_SetJournal_RSQ08_Finish` |
| `RSQ08_C05_B_B` | `RSQ08_C05_B_B_SetJournal_RSQ08_Finish` |
| `RSQ08_C06_B_A` | `RSQ08_C06_B_A_BackToSich` |
| `RSQ08_C09_S_P` | `RSQ08_C09_S_P_SetJournal_RSQ08_Finish` |
| `RSQ08_C07_B_A` | `RSQ08_C07_B_A_BackToSich` |
| `RSQ08_C08_B_A` | `RSQ08_C08_B_A_BackToSich` |
| `RSQ09_C01_K_M` | `RSQ09_C01_K_M_SetJournal_RSQ09_Finish` |
| `RSQ09_C02_K_M` | `RSQ09_C02_K_M_SetJournal_RSQ09_Finish` |
| `RSQ09_C03_K_M` | `RSQ09_C03_K_M_SetJournal_RSQ09_Finish` |
| `RSQ09_C04_K_S` | `RSQ09_C04_K_S_SetJournal_RSQ09_Finish` |
| `RSQ09_C05_B_B` | `RSQ09_C05_B_B_SetJournal_RSQ09_Finish` |
| `RSQ09_C06_B_A` | `RSQ09_C06_B_A_BackToSich` |
| `RSQ09_C09_S_P` | `RSQ09_C09_S_P_SetJournal_RSQ09_Finish` |
| `RSQ09_C07_B_A` | `RSQ09_C07_B_A_BackToSich` |
| `RSQ09_C08_B_A` | `RSQ09_C08_B_A_BackToSich` |
| `RSQ10_C01_K_M` | `RSQ10_C01_K_M_SetJournal_RSQ10_Finish` |
| `RSQ10_C02_K_M` | `RSQ10_C02_K_M_SetJournal_RSQ10_Finish` |
| `RSQ10_C03_K_S` | `RSQ10_C03_K_S_SetJournal_RSQ10_Finish` |
| `RSQ10_C04_K_S` | `RSQ10_C04_K_S_SetJournal_RSQ10_Finish` |
| `RSQ10_C05_B_B` | `RSQ10_C05_B_B_SetJournal_RSQ10_Finish` |
| `RSQ10_C06_B_A` | `RSQ10_C06_B_A_BackToSich` |
| `RSQ10_C09_S_P` | `RSQ10_C09_S_P_SetJournal_RSQ10_Finish_1` |
| `RSQ10_C07_B_A` | `RSQ10_C07_B_A_BackToSich` |
| `RSQ10_C08_B_A` | `RSQ10_C08_B_A_BackToSich` |

## Concrete Drabadan hand-in wiring

The original `RSQ04_C02_SetJournal_RSQ04_Finish` starts RSQ04_Finish and
places the return marker on Drabadan. Its only launcher is:

`RSQ04_C02_SetJournal_RSQ04_Finish.Launchers.[0].Connections.[0].SID = RSQ04_C02_SetJournal_RSQ04_C02_Finish_V2`

Its marker target is:

`RSQ04_C02_SetJournal_RSQ04_Finish.Markers.[0].MarkerTargetQuestGuid = 0A9B5BCC4CEE5A8152C8D88CA0C5254C`

The hand-in node `RSQ04_C02_SetJournal_RSQ04_Finish_1` finishes that stage.
It runs from:

- `Launchers.[0].Connections.[0].SID = RSQ04_C02_SetDialog_RSQ04_Dialog_Drabadan_C02_Finish`;
- `Launchers.[0].Connections.[0].Name = RSQ04_Dialog_Drabadan_C02_Finish_Done_63788`.

Journal isolation changes the start and finish references to the same pair:

- `JournalQuestSID = S2T_Job_RSQ04_C02`;
- `JournalQuestStageSID = S2T_Job_RSQ04_C02_RSQ04_Finish`.

Sibling job C01 instead uses `S2T_Job_RSQ04_C01` and
`S2T_Job_RSQ04_C01_RSQ04_Finish`. Their actor target is shared, but their
explicit journal and stage identities are not. No marker field or launcher
is changed as part of this remapping.

Across the 69 jobs, 157 nodes reference the giver-wide original `_Finish`
stage: 69 Start, 60 Finish and 28 Cancel actions. A job is not required to
carry a standalone Finish-stage Finish node; some flows terminate the
journal itself. After isolation, the only remaining non-S2T journal
reference anywhere within the job subquests is the intentional unrelated
story condition `RSQ10_C09_S_P_If` -> `E12_MQ01`. Thus this audit found no
hand-in node still ending the old shared giver journal or another cloned
job's journal.

The 318 marker-bearing scoped nodes were compared before and after applying
the emitted journal-isolation patches. All Markers values/structs match
exactly. This comparison is an executable private audit assertion; it
does not emulate the engine's marker ownership or drawing logic.

## Parent OnJournalQuestEvent listeners

All 30 original parent listeners observe OnJournalQuestStageStart on the
old journal SID. There are two for RSQ01 and four each for the other seven
givers. Each feeds exactly two direct consumers, both SetDialog nodes:
the ordinary offer dialog and the separate decline/cancel dialog. There is
no direct journal completion, marker removal, ShowMarker or actor despawn
among their consumers.

For Drabadan, the return listener is
`RSQ04_OnJournalQuestEvent_RSQ04_C01_Finish`, with:

- `EventType = EQuestEventType::OnJournalQuestStageStart`;
- `JournalQuestSID = RSQ04`;
- `JournalQuestStageSID = RSQ04_Finish`.

Its direct consumers are `RSQ04_SetDialog_DrabadanRSQ_1` and
`RSQ04_SetDialog_RSQ04_Dialog_Drabadan_DeclineJob`. In vanilla its links
appear under `Launchers.[9]` and `Launchers.[4]` respectively, both with
`Excluding = true`. Other multi-job code can change dialog launch behavior;
this does not convert these listeners into marker writers.

The cloned journals do not trigger these original-journal stage listeners.
That is a real difference from vanilla dialog-event wiring, already adjacent
to the job-menu modifications. It is **not evidence for a marker fix**:
the listeners contain no marker control, and restoring their old shutdown
behavior blindly could regress the multi-job menu.

## What is established and what remains open

Established:

1. The independent journal and stage references are maintained at hand-in.
2. Return markers from multiple completed jobs share their giver actor.
3. Marker settings survive patch generation unchanged, and both conditional
   removal/addition flags remain false.
4. Parent event listeners operate on dialogs, not marker ownership.

Not established:

- Whether the engine coalesces actor-target markers across journals and
  removes the shared visual when one journal completes.
- Whether the surviving marker exists but is hidden until its journal is
  selected/tracked after the previously tracked quest ends.
- Whether the original report reproduces on a clean save with two completed
  jobs using the current generated pak and no conflicting quest/UI mod.

No marker-specific production change is justified yet. If a shared actor
marker lifetime bug is reproduced, the next research target is the engine's
marker ownership/refresh mechanism or a verified native refresh operation.
A blanket repeated Start of the surviving stage is not a safe substitute:
it can change journal state, retrigger notifications/listeners, or affect
saved progress. Inventing a different actor GUID would target a nonexistent
actor; changing to a static world location could stop following the giver.

## Focused in-game check

From a save before accepting the jobs, use two jobs from the same giver and
complete both. Before hand-in, select/track each journal in turn and verify
the giver marker. Hand in either one, then select/track the surviving journal
and check PDA/map/compass separately. Save and reload before handing in the
second, receive its reward, then repeat with the opposite hand-in order.
Keep a control case with one unfinished sibling, matching the successful
follow-up report. A restored marker after selecting the surviving journal
distinguishes tracking behavior from missing marker state.

Record which journal was tracked, which display lost the marker, both job
SIDs and whether selection/reload restores it. Those observations make the
next correction concrete without changing the working journal isolation.
