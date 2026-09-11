# Zone Borders / Contracts reference review (Nexus 2638)

Audit date: 2026-09-11. This is a static review of the owner's already downloaded version-1 archive associated with [Nexus mod 2638](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2638). It is not a game test, a compatibility endorsement, or permission to redistribute the mod. No reference implementation was copied into S2Tweaker production code.

The inspected archive filename is `ZZZ ZoneBordersContracts P 2638 1 2026-09-07T08-33Z vusaOsS2X.zip`. Its extracted Pak is 1,648,471 bytes with SHA-256 `1adab2eb56bc2dc14dbcaedf957cb24a6d0d91e184641e8d85d2cea59f1cd693`. Findings below apply to those exact bytes. They must not be generalized to another download or a future release.

## Main finding

The reference contains a mechanism for **job-giver availability**, using eight `SetQuestGiver` nodes and a held-job counter at each giver. It does not supply evidence that `SetQuestGiver` repairs the surviving journal objective marker reported in issue #9. None of those eight nodes contains a journal SID, journal stage, or `Markers` payload. The whole Pak has no `SetJournal`, `ShowMarker`, or `TrackJournal` node, no journal prototypes, and no localization resources.

The reference also contains cross-giver dispatch scaffolding, including 132 console-command nodes. However, all 66 dispatch random nodes in this particular download assign zero weight to the remote route. That is an important difference between the code inventory and demonstrated functionality. The positive local weight is `0.4`; the remote weight is `0.0`. These are relative pin weights, not a measured 40%/0% gameplay probability.

## Inspected scope

Paths in the following table are relative to `Stalker2/Content/GameLite/GameData/` inside the reference Pak.

| File | Lines | Top-level structs |
| --- | ---: | ---: |
| `GlobalVariablePrototypes/ZoneBorders.cfg` | 62 | 8 |
| `GlobalVariablePrototypes/ZoneContracts.cfg` | 65 | 8 |
| `QuestNodePrototypes/RSQ01.cfg` | 5,200 | 180 |
| `QuestNodePrototypes/RSQ04.cfg` | 8,144 | 284 |
| `QuestNodePrototypes/RSQ05.cfg` | 6,729 | 232 |
| `QuestNodePrototypes/RSQ06_C00___SIDOROVICH.cfg` | 7,496 | 260 |
| `QuestNodePrototypes/RSQ07_C00_TSEMZAVOD.cfg` | 7,630 | 265 |
| `QuestNodePrototypes/RSQ08_C00_ROSTOK.cfg` | 7,068 | 245 |
| `QuestNodePrototypes/RSQ09_C00_MALAHIT.cfg` | 7,023 | 242 |
| `QuestNodePrototypes/RSQ10_C00_HARPY.cfg` | 7,117 | 247 |
| **Total** | **56,534** | **1,971** |

The total consists of 1,955 quest nodes and 16 global variables. Relevant node counts are 69 containers, 96 journal-event listeners, 8 `SetQuestGiver` nodes, 8 tick listeners, 143 `BridgeCleanUp` nodes, and 132 console-command nodes. All 1,971 top-level SIDs are distinct. There are no `bpatch` declarations in these ten files; the eight parent-quest resources contain complete definitions rather than S2Tweaker-style sparse object patches.

## Held-job lifecycle and giver availability

All eight givers use the same basic counter scheme:

| Parent quest | Native containers retained | Cross-giver forks present | Held counter suffix |
| --- | ---: | ---: | --- |
| `RSQ01` | 6 | 6 | `RSQ01_WarlockQuest` |
| `RSQ04` | 10 | 10 | `RSQ04_DrabadansQuests` |
| `RSQ05` | 8 | 8 | `RSQ05_SichQuest` |
| `RSQ06_C00___SIDOROVICH` | 9 | 9 | `RSQ06_SidorovichQuest` |
| `RSQ07_C00_TSEMZAVOD` | 9 | 9 | `RSQ07_VoroninQuest` |
| `RSQ08_C00_ROSTOK` | 9 | 8 | `RSQ08_BarmenQuest` |
| `RSQ09_C00_MALAHIT` | 9 | 8 | `RSQ09_BarmenQuest` |
| `RSQ10_C00_HARPY` | 9 | 8 | `RSQ10_BarmenQuest` |

Each counter has the prefix `ZC_Held_`, integer type, and initial value zero. The three mutation nodes per parent add 1 after the acceptance technical node, subtract 1 when a local container ends or a remote branch completes/cancels, and reset to 0 on parent quest start. Seven parents also reset after `JournalIsCleared`; **RSQ04 is the exception and resets only from its Start node in this file**.

The decrement nodes have 69 local-container inputs in total, plus 66 remote-done and 66 remote-cancel inputs. The graph assumes those event paths keep the held counter synchronized. It does not compute the counter from the currently active journals, and its decrement has no lower-bound clamp. That is a structural distinction, not proof that counter drift actually occurs in the game.

Two repeated predicates control subsequent behavior:

- `If_HeldBelowCap_ZC` compares the counter with **5**, using `Less`. Its True output supplies a non-excluding launcher to both the giver's offer dialog and `SetQuestGiver`; its False output supplies an excluding launcher to both.
- `If_NoneHeld_ZC` compares with **1**, also using `Less`. Its True output allows the parent cleanup and resets the original offer-pool variable to zero, refilling offers.

For the concrete RSQ04 example, the relevant source locations are `RSQ04.cfg` lines 2772 (increment), 2794 (decrement), 3077 (reset), 3099 (cap test), 3156 (empty test), 1359 (parent cleanup), and 3186 (refill). These are line numbers in the inspected reference file, not S2Tweaker source.

### What SetQuestGiver actually receives

`RSQ04_SetQuestGiver_ZC` starts at line 2683. It is repeatable, belongs to `RSQ04`, targets the existing Drabadan actor GUID, uses `MainQuest=false`, and has an empty `MarkerDescription`. Its launchers mirror availability-related dialog paths: initial offer preparation, cancel/no-job/postpone dialog outputs, a journal-finish event exclusion, and the held-cap True/False outputs.

The other seven giver nodes have the same cap behavior and their own live actor GUIDs. They have seven or eight launcher groups depending on the parent dialog shape. There are no downstream graph consumers of these new giver nodes in the reference.

This wiring supports an **availability indicator** interpretation. It does not distinguish two active return stages at the same actor. It cannot establish that the player's map/compass marker for the surviving isolated journal will be recreated, nor that journal tracking is restored. The separate native `SetQuestGiver` research is needed before proposing any giver-icon feature of our own.

## Cross-giver route: present but zero-weighted in this archive

There are 66 `ZB_Random_*` nodes. Every one has `PinWeights.[0]=0.4` and `PinWeights.[1]=0.0`. Pin 0 leads to the local branch; pin 1 is the sole incoming launcher of the remote eligibility test. That test's False result also falls back to the local branch.

The entire ten-file Pak was checked for later redefinitions and weight writers:

- No duplicate top-level SID and no `bpatch` declaration replaces these random nodes.
- All `PinWeights` fields belong to the 74 Random nodes (66 added forks plus eight ordinary random selectors).
- No field value references `PinWeights` as a mutation target.
- The only console-command verbs present are the two start commands described below; there is no console command changing weights.

Thus no later override or writer in this Pak was found that enables the remote route. Under ordinary weighted-random semantics, the zero-weight branch would not be selected. That remains a static inference: this audit did not execute the game scheduler, inspect another installed mod's overrides, or establish what another version does.

### Representative remote route, if enabled separately

For the RSQ04 C01 → RSQ07 fork, the graph is:

1. The remote eligibility test requires the remote giver's acceptance bridge not to be completed and its `ZB_Remote_RSQ07` flag to equal zero.
2. Accepting the offer checks that the remote-selection bridge was chosen. It sets the remote flag to one and opens the branch's `Go` bridge.
3. A console-command node invokes `XStartQuestBySID RSQ07_C01_K_Z` directly. Across the archive, all **66 start-command nodes** have this form, each targeting an existing job SID.
4. The completion listener watches **`OnJournalQuestStageStart` for `RSQ07_Finish`**. Despite its `OnFinish` name, it observes the start of the return stage, not final quest hand-in. All 66 remote listeners use this same event kind for their respective destination journal's `_Finish` stage.
5. If the branch was opened and its remote flag is still one, a one-second delayed Done node decrements the originating giver's Held counter, clears the remote flag, and cleans the branch's Go result. The remote job itself retains its original destination journal/return flow.
6. Cancelling through the originating giver's decline dialog invokes `XStartQuestNodeBySID RSQ07_C00_TSEMZAVOD_cancelQuest`. All **66 cancellation-command nodes** start a destination parent's cancellation node; they do not identify one isolated job journal.

The decisive RSQ04 locations are lines 3737 (weighted fork), 3782 (remote eligibility), 3910 (quest-start command), 3928 (return-stage listener), 3978 (Done), and 4097 (cancellation command). The originating counter can therefore be released at objective completion for a remote branch, before final hand-in to the destination giver; it is not universally a count of jobs still awaiting reward.

Each destination parent also has a remote-finish predicate and one-second technical event that rechecks Held-based availability. For RSQ04 these are at lines 8097 and 8126. They do not reapply a journal stage or its objective marker.

## Comparison with S2Tweaker's current candidate

| Concern | Inspected reference | Current S2Tweaker design |
| --- | --- | --- |
| Active-job ownership | Additional Held integer updated by events | Isolated journal per accepted job; native JournalState predicates |
| Final round cleanup | Held < 1 | No isolated job journal remains Active |
| More job offers | Held < 5 drives offer dialog and giver availability | Existing verified offer paths retained; separate job journals |
| Surviving ready-job marker | No SetJournal/Markers repair found | After a container ends, separately require journal Active and return stage Active, then reapply only that live marker payload |
| Job localization | No localization or journal files | Live-generated alias entries in all installed native language resources |
| Cross-giver dispatch | Console-command graph with zero-weighted remote selection in this archive | Not implemented by the marker repair |
| Updating game data | Full parent quest-file replacements | Live discovery plus sparse patches and explicit unsupported-layout rejection |

Our guarded marker reapplication remains grounded in native game examples described in [JOB_COMPLETED_MARKER_FOLLOWUP.md](JOB_COMPLETED_MARKER_FOLLOWUP.md). This third-party reference neither confirms nor disproves the candidate. It provides no stronger isolated-return-marker repair to substitute for it.

## Practical takeaways and boundaries

The useful lead is to keep **new-job availability indicators** separate from **an accepted job's return marker** in diagnosis and future UI descriptions. A giver-icon enhancement could be investigated independently from native `SetQuestGiver` examples if requested. It is not a justification to alter the pending marker experiment.

Do not import the Held counter, foreign global IDs, arbitrary delays, complete parent graphs, or cross-giver console commands into the current repair. They would introduce a separate lifecycle model, additional persistent state, and cancellation/compatibility questions unrelated to the reported sibling marker loss. The reference's shared destination-journal listeners also cannot be connected unchanged to S2Tweaker's isolated journal IDs.

No claim about runtime reliability, save migration, simultaneous remote jobs, payout correctness, or map/compass behavior is established by these files. No additional production change is recommended from this comparison alone. Keep the current localization/marker experiment focused and obtain a game result before broadening it.

The private audit scripts, extracted comparison files and graph JSON are confined to ignored `out/issue9_reference_deepening/reference_graph/`. They are not included in source or release archives. The public document records findings and short identifiers, not the mod's full implementation.
