# Additional artifact bonuses: implementation research

Audit: 2026-09-11, locally extracted game 2.0.5. Read-only research; no production or test files were changed by this audit. This document extends [the artifact effect audit](ARTIFACT_EFFECT_RESEARCH.md) and [the editor scope](ARTIFACT_EDITOR_RESEARCH.md). Config evidence does not establish gameplay or UI behavior.

## Requested behavior and concrete scope

The owner requested adding a benefit an ordinary artifact does not already have, specifically fire protection on Liquid Stone. The planned editor offers nine visible numeric benefit families on the existing 69 ordinary artifact identifiers. A family is available only if the live item does not already contain that family. Existing-family magnitude controls retain their current role.

Each additional family has `0 = off` and `1–1000%` of that installation's native tier-1 effect. All nine tier-1 sources currently have `EffectLevel = EEffectLevel::Low`. The percentage is an authoring choice; the source magnitudes are read live, never copied from this document into code. The global artifact-strength multiplier also applies once. Default settings produce no extra effect, item row, display row or descendant guard.

There are 518 absent-family choices across the current 69 items. Present-family totals are 103. Nine controls per item could be stored as metadata, but eagerly constructing all native GUI widgets would be inappropriate; retain the existing deferred editor.

## Source inventory


| Source relative to `vanilla/Stalker2/Content/GameLite/GameData/` | Lines | Top-level structs |
| --- | --- | --- |
| ItemPrototypes.cfg | 92232 | 1375 |
| EffectPrototypes.cfg | 85869 | 2426 |
| ObjEffectMaxParamsPrototypes.cfg | 48 | 2 |


The local scripts and numeric/key inventories are in ignored `out/job_repair_integration/artifact_research/`. An already-extracted English localization resource was inspected for effect-name key existence only. No translated text is included here and no localization asset needs to be added as a production dependency for these effects: their original `LocalizationSID` can be retained.

## Nine visible families and live tier-1 baselines

Every source below is permanent, `KeepAll`, positive, has equal ValueMin/ValueMax, no nested effects, and no value provider or effect curve. These traits must be checked against the loaded data. Both magnitude fields must be written together and original raw units retained.


| Family | Source SID | Type | ValueMin = ValueMax | LocalizationSID | Absent on items |
| --- | --- | --- | --- | --- | --- |
| ProtectionShock | ArtifactProtectionShock1 | EEffectType::ProtectionShock | 10 | ArtifactProtectionShock2 | 61 |
| ProtectionBurn | ArtifactProtectionBurn1 | EEffectType::ProtectionBurn | 10 | general_protectionThermal | 60 |
| ProtectionChemicalBurn | ArtifactProtectionChemicalBurn1 | EEffectType::ProtectionChemical | 10 | general_protectionChemical | 59 |
| ProtectionStrike | ArtifactProtectionStrike1 | EEffectType::ProtectionStrike | 0.1 | general_protectionBullet | 60 |
| ProtectionRadiation | ArtifactProtectionRadiation1 | EEffectType::DegenRadiation | 0.1 | general_protectionRadiation | 50 |
| IncreaseRegenStamina | ArtifactIncreaseRegenStamina1 | EEffectType::RegenStamina | 2.5f | general_regenerationStamina | 55 |
| AdditionalInventoryWeight | ArtifactAdditionalInventoryWeight1 | EEffectType::AdditionalInventoryWeight | 3 | general_weight | 56 |
| DegenBleeding | ArtifactDegenBleeding1 | EEffectType::DegenBleeding | 0.5 | general_protectionBleed | 55 |
| DurabilityIncrease | ArtifactDurabilityIncrease1 | EEffectType::MaxDurability | 5.0% | ArtifactMoreDurability | 62 |


Maximum durability remains experimental: native Type is `MaxDurability`. It must not be described as reducing weapon wear. Radiation removal is positive `DegenRadiation`; it is different from harmful `ArtifactAddRadiation*` and from armor's `ProtectionRadiation` type.

All 41 structurally safe effect candidates in these nine visible families have a nonempty English localization entry at `sid_effects_<effective LocalizationSID>_name`. The four PenaltyLessWeight candidates do not. The existing unusual Shock1 localization identity (`ArtifactProtectionShock2`) must be preserved, not guessed or renamed.

Across all ten numeric families there are 45 candidates passing the current `_safe_effect` checks; 43 occur on ordinary artifacts. `ArtifactProtectionShock4` and `ArtifactAdditionalInventoryWeight4` pass the structural checks but have no ordinary-artifact user. The initial addition sources use the observed tier-1 effects, so they do not depend on those unused tiers.

## Liquid Stone hand check

`CArtifactLiquidStone` currently defines:

| Index | EffectPrototypeSIDs | ShouldShowEffects | EffectsDisplayTypes |
| --- | --- | --- | --- |
| [0] | ArtifactProtectionRadiation4 | true | EEffectDisplayType::EffectLevel |
| [1] | ArtifactProtectionChemicalBurn4 | true | EEffectDisplayType::EffectLevel |
| [2] | ArtifactDurabilityIncrease4 | true | EEffectDisplayType::EffectLevel |

Its next free index is `[3]`. A fire addition derives a new item-specific effect from live `ArtifactProtectionBurn1`. At global strength 100% and added fire 200%, the current native 10 becomes 20 for both ValueMin and ValueMax. At global 150%, added fire 200%, it becomes 30. If fire's existing donor is already globally patched to 15, the clone must still explicitly write 30 from the original live baseline; multiplying the patched donor again would produce an incorrect 45.

The item appends the clone at EffectPrototypeSIDs.[3], `true` at ShouldShowEffects.[3], and the native EffectLevel display type at EffectsDisplayTypes.[3]. The first three rows remain unchanged, including any already selected individual overrides. The fake descendant gets a neutral guard for the new index as discussed below. Selecting fire 0 produces none of these additions.

## Three arrays, existing hidden effects and index allocation

The relevant parallel paths are `<Item>.EffectPrototypeSIDs.[i]`, `<Item>.ShouldShowEffects.[i]`, and `<Item>.EffectsDisplayTypes.[i]`. All 69 ordinary items explicitly contain all three containers, but 15 have different index sets across them. None of those differences may be silently normalized.

There are 10 ordinary items with one effect, 33 with two, 22 with three and four with four. Existing visibility/display metadata can be longer or shorter than the effect list. Allocate additions after the maximum existing index across all three arrays, rather than after the count of effects. Preserve all original entries, their literal values, holes and ordering. Compose the final arrays from live source plus previously generated overrides before appending additions; otherwise the new feature could erase an individual bonus or radiation-off choice.

The complete mismatched cases are:


| Item | Effect indices | Visibility indices | Display indices |
| --- | --- | --- | --- |
| CArtifactCrystalThorn | [0] | [0], [1] | [0], [1] |
| GArtifactGoldFish | [0], [1], [2] | [0], [1] | [0], [1] |
| GArtifactStoneDrop | [0], [1], [2] | [0], [1], [2] | [0], [1] |
| FArtifactBakedBolts | [0], [1], [2], [3] | [0], [1], [2] | [0], [1], [2] |
| FArtifactGlass | [0], [1], [2], [3] | [0], [1], [2] | [0], [1], [2] |
| FArtifactHellishHedgehog | [0], [1], [2], [3] | [0], [1], [2] | [0], [1], [2] |
| FArtifactCore | [0], [1], [2], [3] | [0], [1], [2] | [0], [1], [2] |
| FArtifactResin | [0], [1] | [0], [1], [2] | [0], [1], [2] |
| GArtifactSpring | [0], [1], [2] | [0], [1] | [0], [1] |
| GArtifactGravy | [0], [1], [2] | [0], [1] | [0], [1] |
| FArtifactEye | [0] | [0], [1] | [0], [1] |
| GArtifactWrenched | [0] | [0], [1] | [0], [1] |
| GArtifactBloodStone | [0], [1], [2] | [0], [1] | [0], [1] |
| GArtifactTrunk | [0], [1] | [0], [1], [2] | [0], [1], [2] |
| GArtifactHedgehog | [0], [1], [2] | [0], [1] | [0], [1] |


Explicitly hidden ordinary rows are NightStar.[2] and StoneDrop.[2], both penalty-free carry thresholds. Several others lack visibility/display metadata for that hidden supporting effect rather than explicitly setting false. Missing metadata must not be treated as a request to expose that effect.

The 153 native EffectsDisplayTypes entries on ordinary items all use `EEffectDisplayType::EffectLevel`. Use the loaded native display identity. An item-specific effect clone must preserve its original localization reference. A clone's new SID must not become its label key.

## Carry capacity includes a hidden threshold benefit

The chosen new Carry capacity option is a two-effect package: visible `ArtifactAdditionalInventoryWeight1` plus hidden `ArtifactPenaltyLessWeightEffect1`, both scaled by the same additional percentage and the same global artifact factor. Their live tier-1 values are currently 3 and 3. This keeps capacity and the threshold for carrying penalties moving together.

This is a common native pattern, not a universal invariant. Thirteen ordinary artifacts carry a capacity effect; eleven pair it with the same tier and equal raw magnitude. Resin and Trunk are genuine exceptions with Carry05 but no penalty effect. Existing exceptions must stay untouched. The full baseline is:


| Item | Capacity source / value | Threshold source / value |
| --- | --- | --- |
| GArtifactNightStar | ArtifactAdditionalInventoryWeight3 = 9 | ArtifactPenaltyLessWeightEffect3 = 9 |
| GArtifactGoldFish | ArtifactAdditionalInventoryWeight1 = 3 | ArtifactPenaltyLessWeightEffect1 = 3 |
| GArtifactStoneDrop | ArtifactAdditionalInventoryWeight1 = 3 | ArtifactPenaltyLessWeightEffect1 = 3 |
| FArtifactBakedBolts | ArtifactAdditionalInventoryWeight1 = 3 | ArtifactPenaltyLessWeightEffect1 = 3 |
| FArtifactGlass | ArtifactAdditionalInventoryWeight05 = 2 | ArtifactPenaltyLessWeightEffect05 = 2 |
| FArtifactHellishHedgehog | ArtifactAdditionalInventoryWeight1 = 3 | ArtifactPenaltyLessWeightEffect1 = 3 |
| FArtifactCore | ArtifactAdditionalInventoryWeight2 = 6 | ArtifactPenaltyLessWeightEffect2 = 6 |
| FArtifactResin | ArtifactAdditionalInventoryWeight05 = 2 | none |
| GArtifactSpring | ArtifactAdditionalInventoryWeight2 = 6 | ArtifactPenaltyLessWeightEffect2 = 6 |
| GArtifactGravy | ArtifactAdditionalInventoryWeight1 = 3 | ArtifactPenaltyLessWeightEffect1 = 3 |
| GArtifactBloodStone | ArtifactAdditionalInventoryWeight1 = 3 | ArtifactPenaltyLessWeightEffect1 = 3 |
| GArtifactTrunk | ArtifactAdditionalInventoryWeight05 = 2 | none |
| GArtifactHedgehog | ArtifactAdditionalInventoryWeight2 = 6 | ArtifactPenaltyLessWeightEffect2 = 6 |


No normal item currently has a penalty effect without a capacity effect. If a future layout does, do not append a duplicate penalty family silently. Either disable the coupled addition for that shape or implement an explicitly validated composition rule. The penalty row should stay hidden: there is no corresponding native localized name in the inspected English resource. Do not invent a label or misuse the visible capacity label for a different statistic.

## Inheritance leak and descendant protection

The selected 69 ordinary items have 73 direct and 74 total transitive descendants. These include 69 ordinary fakes, four direct special/quest/prologue variants (`SQ13_Soul`, `PArtifactBrain`, `QuestArtifactCrystalThorn`, `CPrologArtifactSlug`), and the additional transitive `PArtifactBrain_Fake`.

All 73 direct descendants define their own effect/display arrays. That alone is not proof against appended-index inheritance. Both `GameData.resolve` and `_resolved_struct` can inherit a missing leaf/index from the item's ancestors; the latter merges nested structures. In the current source, the first index selected for each parent's addition is absent from all three effective lists on all 74 descendants. An unguarded parent addition could therefore introduce a bonus on an excluded descendant.

The planned protection is a shadow at each added index for every transitive descendant:

1. Read the descendant's original effective value through the complete unmodified inheritance chain before adding parent rows.
2. Preserve an existing original effect and existing metadata exactly. Never overwrite a descendant's own original slot with a new benefit or an empty marker.
3. For a genuinely absent original effect, explicitly write `empty`, with `ShouldShowEffects = false`. Preserve original display metadata if present; otherwise use the observed native EffectLevel display identity.
4. Cover descendants of descendants. Retain already selected independent changes outside the new indices. Unknown cycles, unresolved parents or unsupported cross-file references must not silently omit protection.

These patches protect excluded variants; they are not new bonuses on those variants. The source for every preserved value must be the original live data, not a partially modified parent result.

Measured support and limits:

- Seven native item EffectPrototypeSIDs entries are explicitly `empty`. Artifact examples include TemplateArtifact.[0], WeirdFlower.[0], and TemplateQuestArtifact.[0].
- Forty-four explicit item effect rows resolve to `ShouldShowEffects = false`. NightStar.[2] and its Brain/Fake descendants demonstrate false combined with EffectLevel metadata for a hidden artifact effect.
- There is **no native row with the exact combined triple `empty` + `false` + `EffectLevel`** in this inventory. The components are observed separately. Their combination as an inheritance guard remains an experiment requiring an in-game check.
- The neutral guard adds an inert row where the source had no row; it cannot be described as a byte-identical preservation of descendant arrays. The intended gameplay preservation is unverified until tested.
- If a future descendant has an original nonempty effect at a new parent index but lacks some display metadata, retain that original behavior rather than blindly hiding it. The current measured layout has no such collision; tests should cover this future-shape case explicitly.

## No verified engine maximum for benefit rows

The largest ordinary EffectPrototypeSIDs array has four entries. The largest explicit artifact equipped-effect array in the full item inventory is WeirdBolt's five entries. WeirdBolt also has separate special positive/negative behavior and is excluded from this editor; it does not prove an ordinary-item limit or unlimited support.

No per-artifact effect-row maximum was established by the inspected cfg fields. Artifact equipment slots and player stat caps are different concepts. Do not present four, five, nine or another editor bound as an engine limit. With all nine families completed and the hidden carry counterpart, the planned construction yields ten final indices on 22 items and eleven on 47 items in this dataset. Rendering and applying that many rows needs gameplay validation; parser success alone is insufficient.

## Duplication, caps, radiation and global composition

- Add only a family absent from the original effective item. Existing numeric edits remain in the existing editor. An existing zero-strength bonus still belongs to its family; do not silently add a second instance.
- Keep original Type, DuplicationType=KeepAll, permanence, save/pause flags, provider/curve status and localization metadata. A new per-item effect identity affects every copy of that item prototype. Stacking multiple equipped copies still needs a game test.
- Use a separate deterministic clone identity for additional effects so it cannot collide with a clone for an existing effect, a different item, family or mod name. Emit the clone as a new prototype with a valid native parent; do not patch an absent SID.
- Calculate `live source magnitude × global artifact strength × extra percentage / 100` once. Do not scale the already globally patched effect again. Percent literals such as MaxDurability must remain percent literals.
- With global artifact strength zero, omit all positive additions and their guards (unless another nonzero addition needs those rows). Do not expose zero-value benefit labels. Changing source-effect labels through the existing follow-strength option must compose with new clone labels, not overwrite them afterward.
- The general armor carry multiplier does not additionally apply to these `Artifact*` donors: the existing `_effects_patch` chooses the artifact branch first. The coupled threshold uses the artifact factor too.
- New positive radiation removal does not create a harmful radiation identity. Do not clone `ArtifactAddRadiation1..4`, change native lead-container blocker lists, or alter tutorial conditions as part of this feature. Existing per-item radiation-off/tier choices and global harmful-radiation scaling remain separate.
- Native caps remain in force. Fire/electric/chemical protection currently cap at 90, physical at 4.5, stamina regeneration at 30, bleeding reduction at 5, capacity at 140 and penalty-free carry threshold at 90. The armor radiation-protection cap of 85 is not a cap for positive DegenRadiation. No MaxDurability cap was found in that cap table.
- Do not silently adjust caps, add harmful radiation, change rarity/cost/weight, edit fake pickup penalties, or include special, quest, prologue, template or arch-artifact source items. Descendant guard rows are the narrowly scoped exception needed to prevent inheritance leakage.

## Implementation and test checklist

No new cfg extraction file is required: the item, effect and cap roots are already available. A CACHE_SCHEMA bump is needed only if implementation adds a new extraction dependency.

Useful regression checks are behavioral and compositional:

1. Neutral extras generate no new patches; reset removes extra state and rows.
2. Liquid Stone fire 200% emits live 20/20 at global 100%, 30/30 at global 150%, and retains all original bonuses and their prior individual overrides.
3. Compare another artifact using the same native fire effect: it must retain its existing behavior unless a separately chosen global control changes it.
4. A source baseline changed in the fixture changes the output proportionally; literal units and metadata are preserved.
5. Reject/disable a donor that becomes nonpermanent, non-KeepAll, negative, ranged, provider-driven, composite, missing or differently typed.
6. Existing family cannot be duplicated, including a hidden family or existing override set to zero. Unknown settings and invalid percentages follow existing state validation.
7. Three-array append preserves all fifteen native mismatches and all prior overrides. Multiple additions never collide; carry reserves two separate indices and hides only its supporting threshold.
8. Cover all 74 current descendants plus synthetic transitive and colliding-index cases: original effect values stay intact, missing new slots receive the documented neutral guard, and unrelated fields do not change.
9. Test global strength zero, label-follow on/off, radiation-off/tier selection, global harmful-radiation factor and carry-cap settings together. No factor is applied twice.
10. Conflict footprints include the three affected arrays, donor magnitude/type/lifetime/localization fields, coupled carry donor, and guarded descendants. Presets, export/import, undo/reset and summaries must retain extra settings.
11. Reparse emitted cfg and Pak contents to verify all new SIDs resolve and guards cover every added index. Inspect the deferred GUI without exceeding native resource budgets.
12. In game, re-equip a freshly tested ordinary artifact, confirm its new localized row and measured effect, then check multiple copies, hidden threshold behavior, fake pickup, affected quest/prologue variants and long effect lists. Until then label the feature experimental and not play-tested.

## Complete numeric family source inventory

These values are documentation, not constants for production. The implementation's tier-1 choice is identified above. All rows pass the current structural checks; Reachable refers only to use by one of the 69 ordinary artifacts.


| Effect SID | Family | ValueMin = ValueMax | Native level | Ordinary reachable |
| --- | --- | --- | --- | --- |
| ArtifactProtectionShock1 | ProtectionShock | 10 | EEffectLevel::Low | True |
| ArtifactProtectionShock2 | ProtectionShock | 15 | EEffectLevel::Medium | True |
| ArtifactProtectionShock3 | ProtectionShock | 20 | EEffectLevel::Strong | True |
| ArtifactProtectionShock4 | ProtectionShock | 35 | EEffectLevel::Max | False |
| ArtifactIncreaseRegenStamina1 | IncreaseRegenStamina | 2.5f | EEffectLevel::Low | True |
| ArtifactIncreaseRegenStamina2 | IncreaseRegenStamina | 5 | EEffectLevel::Medium | True |
| ArtifactIncreaseRegenStamina3 | IncreaseRegenStamina | 7.5f | EEffectLevel::Strong | True |
| ArtifactIncreaseRegenStamina4 | IncreaseRegenStamina | 12.5f | EEffectLevel::Max | True |
| ArtifactProtectionBurn1 | ProtectionBurn | 10 | EEffectLevel::Low | True |
| ArtifactProtectionBurn2 | ProtectionBurn | 15 | EEffectLevel::Medium | True |
| ArtifactProtectionBurn3 | ProtectionBurn | 20 | EEffectLevel::Strong | True |
| ArtifactProtectionBurn4 | ProtectionBurn | 35 | EEffectLevel::Max | True |
| ArtifactDegenBleeding1 | DegenBleeding | 0.5 | EEffectLevel::Low | True |
| ArtifactDegenBleeding2 | DegenBleeding | 1 | EEffectLevel::Medium | True |
| ArtifactDegenBleeding3 | DegenBleeding | 2 | EEffectLevel::Strong | True |
| ArtifactDegenBleeding4 | DegenBleeding | 4 | EEffectLevel::Max | True |
| ArtifactProtectionStrike1 | ProtectionStrike | 0.1 | EEffectLevel::Low | True |
| ArtifactProtectionStrike2 | ProtectionStrike | 0.25 | EEffectLevel::Medium | True |
| ArtifactProtectionStrike3 | ProtectionStrike | 0.5 | EEffectLevel::Strong | True |
| ArtifactProtectionStrike4 | ProtectionStrike | 1 | EEffectLevel::Max | True |
| ArtifactAdditionalInventoryWeight1 | AdditionalInventoryWeight | 3 | EEffectLevel::Low | True |
| ArtifactAdditionalInventoryWeight2 | AdditionalInventoryWeight | 6 | EEffectLevel::Medium | True |
| ArtifactAdditionalInventoryWeight3 | AdditionalInventoryWeight | 9 | EEffectLevel::Strong | True |
| ArtifactAdditionalInventoryWeight4 | AdditionalInventoryWeight | 12 | EEffectLevel::Max | False |
| ArtifactProtectionChemicalBurn1 | ProtectionChemicalBurn | 10 | EEffectLevel::Low | True |
| ArtifactProtectionChemicalBurn2 | ProtectionChemicalBurn | 15 | EEffectLevel::Medium | True |
| ArtifactProtectionChemicalBurn3 | ProtectionChemicalBurn | 20 | EEffectLevel::Strong | True |
| ArtifactProtectionChemicalBurn4 | ProtectionChemicalBurn | 35 | EEffectLevel::Max | True |
| ArtifactProtectionRadiation1 | ProtectionRadiation | 0.1 | EEffectLevel::Low | True |
| ArtifactProtectionRadiation2 | ProtectionRadiation | 0.15 | EEffectLevel::Medium | True |
| ArtifactProtectionRadiation3 | ProtectionRadiation | 0.25 | EEffectLevel::Strong | True |
| ArtifactProtectionRadiation4 | ProtectionRadiation | 0.5 | EEffectLevel::Max | True |
| ArtifactIncreaseRegenStamina05 | IncreaseRegenStamina | 1.5 | EEffectLevel::VeryLow | True |
| ArtifactDegenBleeding05 | DegenBleeding | 0.3 | EEffectLevel::VeryLow | True |
| ArtifactAdditionalInventoryWeight05 | AdditionalInventoryWeight | 2 | EEffectLevel::VeryLow | True |
| ArtifactProtectionShock05 | ProtectionShock | 7 | EEffectLevel::VeryLow | True |
| ArtifactProtectionStrike05 | ProtectionStrike | 0.07 | EEffectLevel::VeryLow | True |
| ArtifactPenaltyLessWeightEffect1 | PenaltyLessWeightEffect | 3 | EEffectLevel::Low | True |
| ArtifactPenaltyLessWeightEffect2 | PenaltyLessWeightEffect | 6 | EEffectLevel::Medium | True |
| ArtifactPenaltyLessWeightEffect3 | PenaltyLessWeightEffect | 9 | EEffectLevel::Strong | True |
| ArtifactPenaltyLessWeightEffect05 | PenaltyLessWeightEffect | 2 | EEffectLevel::VeryLow | True |
| ArtifactDurabilityIncrease1 | DurabilityIncrease | 5.0% | EEffectLevel::Low | True |
| ArtifactDurabilityIncrease2 | DurabilityIncrease | 10.0% | EEffectLevel::Medium | True |
| ArtifactDurabilityIncrease3 | DurabilityIncrease | 15.0% | EEffectLevel::Strong | True |
| ArtifactDurabilityIncrease4 | DurabilityIncrease | 20.0% | EEffectLevel::Max | True |
