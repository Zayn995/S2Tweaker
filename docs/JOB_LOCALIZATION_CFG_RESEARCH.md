# Repeatable-job journal localization: config audit

Measured on the local S.T.A.L.K.E.R. 2 version 2.0.5 data, 11 September 2026,
against the S2Tweaker 1.39.0 journal-isolation implementation.
This document audits config evidence only; it does not establish Unreal's
runtime localization lookup or prove a localization repair.

## Finding

The existing builder copies the eight source journals into 69 independent
journals. All 69 preserve the source `Descriptions` array verbatim. All 139
generated stages preserve their corresponding original `Description` token.
The source title is absent in all eight journals, so the builder supplies
the original start-objective description token as `Name`.

These operations preserve strings in the emitted config, but the vanilla
data does **not** prove that these strings bind localization independently
of the journal/stage SID. The prior nonempty-Name regression is therefore
insufficient to claim that localized text works. Molkerr's new issue #9
report supplies the missing negative engine evidence: system strings appear.
The video review and additional stage-scope audit below narrow the cause:
stage text uses a SID-derived key, while the long description still works.
Reusing original stage SIDs is a supported candidate for a controlled test;
it does not by itself repair the title or migrate existing saved stages.

## Video evidence and its boundary

At **0:42** in [Molkerr's clean-save test video](https://drive.google.com/file/d/1_CKj2d3KWK0lRW1Zd4a-4DBdThPd6trB),
the reviewed journal displays:

- Title: `S2T_Job_RSQ04_C02`.
- Stage: `sid_journal_stage_S2T_Job_RSQ04_C02_RSQ04_C02_Start`.
- Long journal description: localized Russian prose beginning with the
  giver's name, rather than a system string.

The bad title is the generated journal SID, not the explicit Name value
`RSQ04_C02_Start_Description`. The bad objective is a literal
`sid_journal_stage_` prefix plus the generated stage SID, not the copied
Description value `RSQ04_C02_Start_Description`. Therefore copying those
explicit fields did not control the two failing display elements in this
observed journal. The existing long description remains usable; changing
its copied `Descriptions.[0]` is not warranted by this evidence.

This identifies an observed SID-derived stage lookup, without proving the
entire engine implementation. The corresponding title lookup must be
checked against localization assets separately; the visible bare SID is
its fallback output, not necessarily its attempted lookup key.

## Inputs and scope

Paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`.

| Config | Lines | Parsed top-level structs |
|---|---:|---:|
| `JournalQuestPrototypes.cfg` | 10,065 | 199 |
| `QuestNodePrototypes.cfg` | 2,366,619 | 84,244 |

The journal count includes the `JournalQuestPrototypes` template-like first
entry. All 199 top-level journal structs have no `refkey` or `refurl`
attributes. Thus `_resolved_struct` contributes no explicitly inherited
metadata to these eight source journals. This does not rule out undocumented
engine defaults.

`Texts/En/SQ13_Journal.cfg`, an existing local text reference, contains only
`@SQ13_mat_Name`, `@SQ13_mat_Description_0` and similar markers, without
translated values. It does not demonstrate a usable new localization binding.
The previously unpacked ZoneBordersContracts reference contains ten pak
entries and **zero** journal, localization or `.locres` entries. That mod
therefore provides no precedent for custom journal localization.

## Exact supported config fields

The following counts cover explicit top-level fields only. Empty scalar
fields and child structs are counted separately because both forms occur.

| Key | Scalar occurrences | Child-struct occurrences |
|---|---:|---:|
| `DLC` | 1 | 0 |
| `Description` | 31 | 0 |
| `Descriptions` | 2 | 166 |
| `Image` | 1 | 0 |
| `ImagePath` | 198 | 0 |
| `LocationSID` | 164 | 0 |
| `MainQuest` | 199 | 0 |
| `Name` | 71 | 0 |
| `Region` | 126 | 0 |
| `RewardTypes` | 138 | 26 |
| `SID` | 199 | 0 |
| `SaveLoadImagePath` | 58 | 0 |
| `Stages` | 3 | 196 |

No `Localization`, `LocalizedName`, `LocalizationSID`, `Namespace`,
`StringTable`, `TextKey` or alternate title-binding field appears anywhere
in the entire journal config. Absence is a data finding, not proof that an
undocumented engine property is impossible.

The relevant concrete paths are:

- `RSQ01.SID = RSQ01` identifies the source journal.
- `RSQ01.Descriptions.[0] = RSQ01_Description_0` supplies its only explicit
  description-array value.
- `RSQ01.Stages.RSQ01_C01_Start.SID = RSQ01_C01_Start` identifies one stage.
- `RSQ01.Stages.RSQ01_C01_Start.Description = RSQ01_C01_Start_Description`
  supplies its explicit stage description token.
- `RSQ01.Stages.RSQ01_C01_Start.Optional = false` marks it required.
- `Name` and singular top-level `Description` are **absent**, not empty,
  in every RSQ journal. The template-like first struct declares both empty.

Across all journals, 70 explicit Name values are nonempty, one is empty,
and 128 journals omit Name. Of the 70 nonempty values, 69 equal
`<journal SID>_Name`; `OldCordon.Name = _Name` is the only exception. The
exception resembles a missing prefix and does not show a validated alias.
All 1,517 stage Description values equal `<stage SID>_Description`, without
any exception. Thus there is no vanilla example establishing that replacing
the stage SID while retaining a different stage's token localizes correctly.

Thirty journals carry a nonempty singular top-level `Description`, and the
template-like entry carries an empty one. Repeatable jobs use the plural
`Descriptions` struct instead; changing that structure to singular would
discard the observed source layout.

## Complete source-journal baselines

All eight have `LocationSID =` (empty), `Region = ERegion::Zone`,
`RewardTypes =` (empty) and `MainQuest = false`. All use this same ImagePath:

`/Script/Engine.Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Quest/Journal/T_Atmospheric_Journal.T_Atmospheric_Journal'`

All eight omit Name, singular Description, Image, SaveLoadImagePath and DLC.
All 78 source stages have `Optional = false` and their child key equals SID.

| Source journal SID | `Descriptions.[0]` | Source stages | Generated journals |
|---|---|---:|---:|
| `RSQ01` | `RSQ01_Description_0` | 8 | 6 |
| `RSQ04` | `RSQ04_Description_0` | 11 | 10 |
| `RSQ05` | `RSQ05_Description_0` | 9 | 8 |
| `RSQ06` | `RSQ06_Description_0` | 10 | 9 |
| `RSQ07` | `RSQ07_Description_0` | 10 | 9 |
| `RSQ08` | `RSQ08_Description_0` | 10 | 9 |
| `RSQ09` | `RSQ09_Description_0` | 10 | 9 |
| `RSQ10` | `RSQ10_Description_0` | 10 | 9 |

The complete stage table below gives the path suffix under
`<source>.Stages.<stage>.Description`; every listed stage's `SID` is its
stage key. All 78 are used by at least one of the 69 job containers.

| Source | Stage key and SID | Description value |
|---|---|---|
| `RSQ01` | `RSQ01_C01_Start` | `RSQ01_C01_Start_Description` |
| `RSQ01` | `RSQ01_Finish` | `RSQ01_Finish_Description` |
| `RSQ01` | `RSQ01_C02_Start` | `RSQ01_C02_Start_Description` |
| `RSQ01` | `RSQ01_C04_Start` | `RSQ01_C04_Start_Description` |
| `RSQ01` | `RSQ01_C05_Start` | `RSQ01_C05_Start_Description` |
| `RSQ01` | `RSQ01_C06_Start` | `RSQ01_C06_Start_Description` |
| `RSQ01` | `RSQ01_C03_Start` | `RSQ01_C03_Start_Description` |
| `RSQ01` | `RSQ01_C06_Loot` | `RSQ01_C06_Loot_Description` |
| `RSQ04` | `RSQ04_Finish` | `RSQ04_Finish_Description` |
| `RSQ04` | `RSQ04_C01_Start` | `RSQ04_C01_Start_Description` |
| `RSQ04` | `RSQ04_C02_Start` | `RSQ04_C02_Start_Description` |
| `RSQ04` | `RSQ04_C03_Start` | `RSQ04_C03_Start_Description` |
| `RSQ04` | `RSQ04_C04_Start` | `RSQ04_C04_Start_Description` |
| `RSQ04` | `RSQ04_C05_Start` | `RSQ04_C05_Start_Description` |
| `RSQ04` | `RSQ04_C06_Start` | `RSQ04_C06_Start_Description` |
| `RSQ04` | `RSQ04_C07_Start` | `RSQ04_C07_Start_Description` |
| `RSQ04` | `RSQ04_C08_Start` | `RSQ04_C08_Start_Description` |
| `RSQ04` | `RSQ04_C09_Start` | `RSQ04_C09_Start_Description` |
| `RSQ04` | `RSQ04_C10_Start` | `RSQ04_C10_Start_Description` |
| `RSQ05` | `RSQ05_Finish` | `RSQ05_Finish_Description` |
| `RSQ05` | `RSQ05_C01_Start` | `RSQ05_C01_Start_Description` |
| `RSQ05` | `RSQ05_C02_Start` | `RSQ05_C02_Start_Description` |
| `RSQ05` | `RSQ05_C10_Start` | `RSQ05_C10_Start_Description` |
| `RSQ05` | `RSQ05_C04_Start` | `RSQ05_C04_Start_Description` |
| `RSQ05` | `RSQ05_C05_Start` | `RSQ05_C05_Start_Description` |
| `RSQ05` | `RSQ05_C09_Start` | `RSQ05_C09_Start_Description` |
| `RSQ05` | `RSQ05_C07_Start` | `RSQ05_C07_Start_Description` |
| `RSQ05` | `RSQ05_C08_Start` | `RSQ05_C08_Start_Description` |
| `RSQ06` | `RSQ06_Finish` | `RSQ06_Finish_Description` |
| `RSQ06` | `RSQ06_C01_Start` | `RSQ06_C01_Start_Description` |
| `RSQ06` | `RSQ06_C02_Start` | `RSQ06_C02_Start_Description` |
| `RSQ06` | `RSQ06_C03_Start` | `RSQ06_C03_Start_Description` |
| `RSQ06` | `RSQ06_C04_Start` | `RSQ06_C04_Start_Description` |
| `RSQ06` | `RSQ06_C05_Start` | `RSQ06_C05_Start_Description` |
| `RSQ06` | `RSQ06_C06_Start` | `RSQ06_C06_Start_Description` |
| `RSQ06` | `RSQ06_C07_Start` | `RSQ06_C07_Start_Description` |
| `RSQ06` | `RSQ06_C08_Start` | `RSQ06_C08_Start_Description` |
| `RSQ06` | `RSQ06_C09_Start` | `RSQ06_C09_Start_Description` |
| `RSQ07` | `RSQ07_Finish` | `RSQ07_Finish_Description` |
| `RSQ07` | `RSQ07_C01_Start` | `RSQ07_C01_Start_Description` |
| `RSQ07` | `RSQ07_C02_Start` | `RSQ07_C02_Start_Description` |
| `RSQ07` | `RSQ07_C03_Start` | `RSQ07_C03_Start_Description` |
| `RSQ07` | `RSQ07_C04_Start` | `RSQ07_C04_Start_Description` |
| `RSQ07` | `RSQ07_C05_Start` | `RSQ07_C05_Start_Description` |
| `RSQ07` | `RSQ07_C06_Start` | `RSQ07_C06_Start_Description` |
| `RSQ07` | `RSQ07_C07_Start` | `RSQ07_C07_Start_Description` |
| `RSQ07` | `RSQ07_C08_Start` | `RSQ07_C08_Start_Description` |
| `RSQ07` | `RSQ07_C09_Start` | `RSQ07_C09_Start_Description` |
| `RSQ08` | `RSQ08_Finish` | `RSQ08_Finish_Description` |
| `RSQ08` | `RSQ08_C01_Start` | `RSQ08_C01_Start_Description` |
| `RSQ08` | `RSQ08_C02_Start` | `RSQ08_C02_Start_Description` |
| `RSQ08` | `RSQ08_C03_Start` | `RSQ08_C03_Start_Description` |
| `RSQ08` | `RSQ08_C04_Start` | `RSQ08_C04_Start_Description` |
| `RSQ08` | `RSQ08_C05_Start` | `RSQ08_C05_Start_Description` |
| `RSQ08` | `RSQ08_C06_Start` | `RSQ08_C06_Start_Description` |
| `RSQ08` | `RSQ08_C07_Start` | `RSQ08_C07_Start_Description` |
| `RSQ08` | `RSQ08_C08_Start` | `RSQ08_C08_Start_Description` |
| `RSQ08` | `RSQ08_C09_Start` | `RSQ08_C09_Start_Description` |
| `RSQ09` | `RSQ09_Finish` | `RSQ09_Finish_Description` |
| `RSQ09` | `RSQ09_C01_Start` | `RSQ09_C01_Start_Description` |
| `RSQ09` | `RSQ09_C02_Start` | `RSQ09_C02_Start_Description` |
| `RSQ09` | `RSQ09_C03_Start` | `RSQ09_C03_Start_Description` |
| `RSQ09` | `RSQ09_C04_Start` | `RSQ09_C04_Start_Description` |
| `RSQ09` | `RSQ09_C05_Start` | `RSQ09_C05_Start_Description` |
| `RSQ09` | `RSQ09_C06_Start` | `RSQ09_C06_Start_Description` |
| `RSQ09` | `RSQ09_C07_Start` | `RSQ09_C07_Start_Description` |
| `RSQ09` | `RSQ09_C08_Start` | `RSQ09_C08_Start_Description` |
| `RSQ09` | `RSQ09_C09_Start` | `RSQ09_C09_Start_Description` |
| `RSQ10` | `RSQ10_Finish` | `RSQ10_Finish_Description` |
| `RSQ10` | `RSQ10_C01_Start` | `RSQ10_C01_Start_Description` |
| `RSQ10` | `RSQ10_C02_Start` | `RSQ10_C02_Start_Description` |
| `RSQ10` | `RSQ10_C03_Start` | `RSQ10_C03_Start_Description` |
| `RSQ10` | `RSQ10_C04_Start` | `RSQ10_C04_Start_Description` |
| `RSQ10` | `RSQ10_C05_Start` | `RSQ10_C05_Start_Description` |
| `RSQ10` | `RSQ10_C06_Start` | `RSQ10_C06_Start_Description` |
| `RSQ10` | `RSQ10_C07_Start` | `RSQ10_C07_Start_Description` |
| `RSQ10` | `RSQ10_C08_Start` | `RSQ10_C08_Start_Description` |
| `RSQ10` | `RSQ10_C09_Start` | `RSQ10_C09_Start_Description` |

## Complete generated mapping

For every row below, the generated journal SID is `S2T_Job_<subquest>`.
For each original stage listed in the last column, the generated stage key
and SID are `<generated journal SID>_<original stage SID>`. The stage
Description remains the original token from the complete table above.
This formula is the implementation's emitted naming rule, not a proposed fix.

`Name` is exactly `<start stage SID>_Description`; all rows have one matching
`_Start` stage. There are 138 stages from two per job, plus the additional
`RSQ01_C06_Loot` stage, producing 139 generated stages in total.

| Source | Job subquest | Original stages retained |
|---|---|---|
| `RSQ01` | `RSQ01_C01` | `RSQ01_C01_Start`, `RSQ01_Finish` |
| `RSQ01` | `RSQ01_C02` | `RSQ01_C02_Start`, `RSQ01_Finish` |
| `RSQ01` | `RSQ01_C03` | `RSQ01_C03_Start`, `RSQ01_Finish` |
| `RSQ01` | `RSQ01_C04` | `RSQ01_C04_Start`, `RSQ01_Finish` |
| `RSQ01` | `RSQ01_C05` | `RSQ01_C05_Start`, `RSQ01_Finish` |
| `RSQ01` | `RSQ01_C06` | `RSQ01_C06_Loot`, `RSQ01_C06_Start`, `RSQ01_Finish` |
| `RSQ04` | `RSQ04_C01` | `RSQ04_C01_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C02` | `RSQ04_C02_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C03` | `RSQ04_C03_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C04` | `RSQ04_C04_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C05` | `RSQ04_C05_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C06` | `RSQ04_C06_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C10` | `RSQ04_C10_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C07` | `RSQ04_C07_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C08` | `RSQ04_C08_Start`, `RSQ04_Finish` |
| `RSQ04` | `RSQ04_C09` | `RSQ04_C09_Start`, `RSQ04_Finish` |
| `RSQ05` | `RSQ05_C01` | `RSQ05_C01_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C02` | `RSQ05_C02_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C04` | `RSQ05_C04_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C05` | `RSQ05_C05_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C10` | `RSQ05_C10_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C07` | `RSQ05_C07_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C08` | `RSQ05_C08_Start`, `RSQ05_Finish` |
| `RSQ05` | `RSQ05_C09` | `RSQ05_C09_Start`, `RSQ05_Finish` |
| `RSQ06` | `RSQ06_C01___K_Z` | `RSQ06_C01_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C02___K_M` | `RSQ06_C02_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C03___K_B` | `RSQ06_C03_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C04___K_S` | `RSQ06_C04_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C05___B_B` | `RSQ06_C05_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C06___B_A` | `RSQ06_C06_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C07___B_A` | `RSQ06_C07_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C08___B_A` | `RSQ06_C08_Start`, `RSQ06_Finish` |
| `RSQ06` | `RSQ06_C09___S_P` | `RSQ06_C09_Start`, `RSQ06_Finish` |
| `RSQ07` | `RSQ07_C01_K_Z` | `RSQ07_C01_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C02_K_M` | `RSQ07_C02_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C03_K_M` | `RSQ07_C03_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C04_K_B` | `RSQ07_C04_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C05_B_B` | `RSQ07_C05_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C06_B_A` | `RSQ07_C06_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C09_S_P` | `RSQ07_C09_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C07_B_A` | `RSQ07_C07_Start`, `RSQ07_Finish` |
| `RSQ07` | `RSQ07_C08_B_A` | `RSQ07_C08_Start`, `RSQ07_Finish` |
| `RSQ08` | `RSQ08_C01_K_M` | `RSQ08_C01_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C02_K_B` | `RSQ08_C02_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C03_K_S` | `RSQ08_C03_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C04_B_B` | `RSQ08_C04_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C05_B_B` | `RSQ08_C05_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C06_B_A` | `RSQ08_C06_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C09_S_P` | `RSQ08_C09_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C07_B_A` | `RSQ08_C07_Start`, `RSQ08_Finish` |
| `RSQ08` | `RSQ08_C08_B_A` | `RSQ08_C08_Start`, `RSQ08_Finish` |
| `RSQ09` | `RSQ09_C01_K_M` | `RSQ09_C01_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C02_K_M` | `RSQ09_C02_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C03_K_M` | `RSQ09_C03_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C04_K_S` | `RSQ09_C04_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C05_B_B` | `RSQ09_C05_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C06_B_A` | `RSQ09_C06_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C09_S_P` | `RSQ09_C09_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C07_B_A` | `RSQ09_C07_Start`, `RSQ09_Finish` |
| `RSQ09` | `RSQ09_C08_B_A` | `RSQ09_C08_Start`, `RSQ09_Finish` |
| `RSQ10` | `RSQ10_C01_K_M` | `RSQ10_C01_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C02_K_M` | `RSQ10_C02_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C03_K_S` | `RSQ10_C03_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C04_K_S` | `RSQ10_C04_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C05_B_B` | `RSQ10_C05_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C06_B_A` | `RSQ10_C06_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C09_S_P` | `RSQ10_C09_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C07_B_A` | `RSQ10_C07_Start`, `RSQ10_Finish` |
| `RSQ10` | `RSQ10_C08_B_A` | `RSQ10_C08_Start`, `RSQ10_Finish` |

## Quest-node references and existing test limits

The full QuestNode config contains 6,859 explicit `JournalQuestSID`, 4,998
`JournalQuestStageSID` and 293 `JournalQuestDescriptionIndex` fields.
No separate journal-localization override appears in those nodes. The
`TutorialHeadLocalizedSID` and `TutorialTextLocalizedSID` fields each occur
123 times but belong to tutorial text, not journal metadata.

The 69 job subquests contain 799 SetJournal nodes. Of these, 69 explicitly set JournalQuestDescriptionIndex; the complete value distribution is `{'0': 69}`. Journal isolation preserves those indexes.


`quest_jobs._remap` changes `JournalQuestSID` and the matching
`JournalQuestStageSID`, recursively including conditions. It deliberately
does not change `JournalQuestDescriptionIndex`, rewards, dialogs or other
node fields. A new journal retains `Descriptions.[0]`, so index 0 still
addresses the original description-array slot at the config level.

`tests/test_job_isolation.py` asserts 69 new journals, valid references,
nonempty Name, isolated hand-in state and unchanged non-reference node
data. It does not load language assets or evaluate the game's localization
resolver. Its pass cannot support a localized-text claim.

## Can independent journals retain original stage SIDs?

A second audit scanned all **491** locally available `.cfg` files and parsed
the complete QuestNode and Dialog trees. This is a statement about the
extracted local inputs, not every cooked asset in the installed game.

The only config field whose name contains both journal and stage is
`JournalQuestStageSID`: 4,998 occurrences in QuestNodePrototypes and 34 in
DialogPrototypes, totaling **5,032**. Every occurrence carries a nonempty
`JournalQuestSID` in the **same struct**. None has an empty stage value.
Thus every observed explicit stage operation or condition identifies a
journal together with the stage. No unscoped stage-reference config field
was found in these inputs.

For the 78 repeatable-job stage SIDs, exact value matches occur only as:

| Field | Occurrences | Interpretation |
|---|---:|---|
| `JournalQuestStageSID` | 622 | Journal-scoped stage operations or conditions |
| `SID` | 196 | Stage definitions, quest-node definitions or quest-node links |

The plain SID uses must not be blindly remapped: a quest technical node can
share the text of a journal stage SID while belonging to the quest-node
namespace. For example, `RSQ04_C02_Start` is also a quest-node SID with
ordinary launcher references. Those are not unscoped journal-stage actions.

Of the 622 actual stage-reference fields, 592 belong to the 69 job subquests.
The remaining 30 belong to parent giver quests and are OnJournalQuestEvent
listeners targeting the **original** journal: two for RSQ01 and four each
for RSQ04, RSQ05 and RSQ06–RSQ10. None occurs in DialogPrototypes. Preserving
stage SIDs under new journal SIDs would not retarget these old-journal
listeners if the observed `(JournalQuestSID, JournalQuestStageSID)` scoping
is respected. Their existing gameplay relevance is a separate graph question.

### Duplicate stage IDs already exist in vanilla

The 1,517 stage definitions use **1,502 unique stage SIDs**: 11 SID groups
span different journals, accounting for 15 additional definitions. This is
the complete duplicate table:

| Reused stage SID | Journals containing it |
|---|---|
| `TQC_01_05` | `TQC_01`, `TQC_09` |
| `TQF_04_05` | `TQC_04`, `TQF_04` |
| `TQF_08_05` | `TQC_08`, `TQF_08` |
| `TQQ_01_05` | `TQQ_01`, `TQQ_09` |
| `TQF_01_05` | `TQF_01`, `TQF_09` |
| `FollowRichter` | `MQ01`, `QuestToolCombatTest` |
| `1` | `qtc_test_1`, `qtc_test_2`, `qtc_test_3` |
| `2` | `qtc_test_1`, `qtc_test_2`, `qtc_test_3` |
| `GoToBanditCamp` | `SQ18_AppleMen`, `SQ18_1`, `STQB` |
| `PlayTir` | `SQ18_AppleMen`, `SQ18_1` |
| `GetReward` | `SQ18_AppleMen`, `SQ18_1`, `Test_MQ01` |

For the first five groups, QuestNodePrototypes contains two explicit stage
references under **each** of the two containing journals. SID `1` also has
references scoped separately to `qtc_test_1` (three) and `qtc_test_2` (two).
`GetReward` has three under `Test_MQ01`. The other duplicate definitions
have no matching stage reference in the parsed QuestNode/Dialog files.
These test/legacy names do not prove active retail quest execution, but they
do establish a concrete config precedent for the paired namespace.

### Candidate and remaining limits

A controlled candidate can keep `S2T_Job_<subquest>` as the independent
journal SID while retaining each original stage SID inside that journal.
For the observed video example, the desired objective lookup would become
`sid_journal_stage_RSQ04_C02_Start`, which can then be checked against the
installed localization assets. State conditions must continue carrying the
new journal SID, including both jobs that share a giver's Finish stage SID.

This candidate has materially better evidence than an invented localization
override property. It still requires a game test of two concurrent jobs
that share a Finish stage, reversed hand-in order, cancellation and reload.
The title would still use the independent new journal SID and needs a
separate verified binding. Changing stage SIDs also does not migrate stages
saved under the current generated SIDs; testing must start before accepting
the affected jobs. Adding locale aliases for the existing generated IDs is
an alternative that would preserve saved identifiers, provided the game's
localization loading mechanism is independently verified.

## Warnings and implementation boundary

- Do not silently restore shared journal SIDs to repair text: that would
  undo independent journal state, including the sibling-hand-in correction.
- Do not rename already generated journal/stage SIDs casually. They are
  persistent journal-state identifiers; CFG does not provide save migration.
- Do not invent `LocalizationSID`, `Title`, a namespace override, or any
  other unobserved field. No such binding is verified by this audit.
- Do not assume copying explicit Name/Description tokens proves resolution.
  The reviewed title/objective failures use generated identifiers despite
  these copied values; the long description does localize in that example.
- Do not replace plural Descriptions with singular Description or reuse
  tutorial-localization fields. Neither change follows the observed journal
  schema.
- Keep extracted proprietary configs and language assets local. A fix that
  adds localization must determine the smallest valid user-local output
  and cannot publish extracted game localization wholesale.

The expanded evidence supports a controlled original-stage-SID candidate,
while retaining independent journal IDs. A complete production correction
still needs verified title localization, an explicit decision about saved
stage identifiers, and engine verification. No production code was changed
by this audit.
