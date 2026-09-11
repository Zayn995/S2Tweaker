# Artifact effects: current data research

[Research overview and implementation priorities](ARTIFACT_EDITOR_RESEARCH.md)

Inspected 2026-09-11 against the locally extracted game 2.0.5 data. Research only: no application changes, generated game patches, runtime observations, or release are implied.

Paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`. These factual tables record selected values and references; proprietary source cfg files are not included.

## Outcome

Individual ordinary artifact effect tuning is supported by the native data shape. It needs item-specific effect references because effects are shared between artifacts and fake counterparts. It is not equivalent to multiplying one global `Artifact*` value.

A deliberately limited first version can clone individual numeric benefit effects into a mod/item namespace and replace the chosen artifact's list entry. Radiation needs a separate compatibility design: the native lead-container effects and the radiation tutorial refer to exact harmful-radiation SIDs. Replacing those with arbitrary new SIDs may bypass shielding and tutorial detection. Config inspection cannot establish whether effect inheritance preserves these identity matches.

## File inventory

| File | Lines | Top-level structs |
| --- | --- | --- |
| ItemPrototypes.cfg | 92232 | 1375 |
| EffectPrototypes.cfg | 85869 | 2426 |
| ObjEffectMaxParamsPrototypes.cfg | 48 | 2 |

All three parsed files have no duplicate root keys. Additional reverse-reference source inventories:

| File | Lines | Top-level structs | References to audited 118-effect union |
| --- | --- | --- | --- |
| QuestNodePrototypes.cfg | 2366619 | 84244 | 4 |
| UpgradePrototypes.cfg | 46006 | 1288 | 71 |

The reverse-reference pass scanned 485 currently extracted text cfg files. This is a bounded audit of available files, not all compiled Blueprint/C++ references in the game. Its 576 exact effect-like references point into the union of 108 `Artifact*` effects and the 60 artifact-reachable effects (118 unique in the union).

## Graph counts and inheritance

- 154 item roots resolve to the artifact category, including templates, fakes, quest/prologue variants, and arch-artifacts. This is not the number of ordinary user-facing artifacts.
- Their explicit effect-bearing fields contain 419 references to 58 distinct effect roots. Following explicit effect edges yields 60 roots.
- Every reachable effect has `refkey=[0]`, no `refurl`, and directly declares Type, ValueMin, ValueMax, Duration and bIsPermanent. Runtime code must still resolve live data rather than assume this remains true after updates.
- 50 of the 60 effects are reachable from more than one artifact-classified item. User counts in the baseline table include fakes and quest variants.
- No reachable effect is directly referenced by a non-artifact item's effect fields, and none is referenced by UpgradePrototypes. This is narrower than the whole `Artifact*` name prefix: that prefix includes effects used by consumables and lead-container upgrades.
- There is one reachable Composite, `WeirdWaterWeightChangeCompositeEffect`, with two outgoing effect edges. There are no reachable Conditional effects. The actual special-artifact behavior also lives outside the effect graph.
- Text and LocalizationSID fields that happen to equal another effect name are metadata, not graph edges. In particular `ArtifactProtectionShock1.Text = ArtifactProtectionShock2` must not make an editor clone Shock2.

## Exact patch paths and semantics

For ordinary equipped effects, the reference path is `<ArtifactSID>.EffectPrototypeSIDs.[index]`. Effect magnitude lives in `<EffectSID>.ValueMin` and `.ValueMax`; both must be updated together for deterministic effects. The full reference table below preserves exact indices.

The graph's only nonconstant interval is `FakeArtifactsPSYPoints`: ValueMin 10, ValueMax 20. It is a pickup penalty and should not be exposed as an ordinary equipped artifact effect.

Preserve literal units. For example, `ArtifactProtectionStrike1.ValueMin = 0.1` is a raw value, `ArtifactDurabilityIncrease1.ValueMin = 5.0%` is a percent literal, and `DegenBleeding10.ValueMin = 2000.0%` is a separate unit/scale. A percentage literal must not silently become a bare number or a normalized fraction.

Hand checks: Shock1 raw 10 × 1.5 = 15 for both magnitude fields; Strike1 raw 0.1 × 2 = 0.2; durability 5.0% × 2 = 10%; harmful radiation -0.15 × 0 = 0. These arithmetic checks demonstrate intended values, not game behavior or a generated patch test.

Both `ArtifactProtectionRadiation1..4` and `ArtifactAddRadiation1..4` have Type `DegenRadiation`: positive 0.1/0.15/0.25/0.5 reduces radiation, negative -0.1/-0.15/-0.25/-0.5 adds it. They are not armor's `ProtectionRadiation` effect type. The armor radiation-protection cap of 85 is therefore not their cap.

`ArtifactDurabilityIncrease1..4` have Type `MaxDurability`, not an equipment wear-rate type. The cfg identifies the value but does not prove which equipped targets receive it. Labeling these as reduced weapon wear would overclaim.

## Special-artifact cases

| Item | Exact path / graph | What the editor must respect |
| --- | --- | --- |
| AArtifactWeirdBall | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1 | The equipped protection shares a standard effect. Ball-specific damage/stamina/weight fields and Blueprint behavior are separate. |
| AArtifactWeirdWater | EffectPrototypeSIDs.[0] = WeirdWaterWeightChangeCompositeEffect | Clone the two child effects and a parent pointing to those clones if tuning the paired capacity/penalty bonus. Child values are 50.0%, not flat kg. EffectPrototypeSIDs.[1] is ArtifactProtectionRadiation1. |
| AArtifactWeirdNut | EffectPrototypeSIDs.[0] = DegenBleeding10; [1] = RegenHealthModifier | Bleeding reduction 2000.0% and health-regeneration modifier -0.75 use different numeric semantics. |
| AArtifactWeirdFlower | WakeUpEffectSIDs.[0] = FlairDistanceModifierEffect | This is a wake-up-triggered effect, not the empty equipped EffectPrototypeSIDs.[0]. Item EffectsDuration is 7200.f. Existing permanent-flower extension is separate. |
| AArtifactWeirdBolt | PositiveEffectPrototypeSIDs.[0..4]; NegativeEffectPrototypeSIDs.[0] | Distinct normal, charged-benefit and drawback arrays. The drawback SPDrain is 200%; charge/deflection behavior is in item fields/Blueprint. |
| AArtifactWeirdKettle | EffectPrototypeSIDs.[0] = WeirdKettleEffect | This is a permanent FlagEffect with zero magnitude, not the food/drink bonuses. Alternative and negative consumable effects live on the consumable items. |
| QuestArtifactHeartofChornobyl | EffectPrototypeSIDs contains Artifact_HeartOfChornobyl_RegenHP | Quest-only health regeneration should not be offered as an ordinary artifact tweak. |
| PQuestArtifactScraper and its fake | AddRadiation1 and ProtectionShock1 | Generic effect SIDs, unlike normal artifact namespaces; exclude quest variants. |
| 70 ordinary fake variants | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints | Distinct pickup PSY penalty, Duration 1, Charges 1, nonpermanent. Exclude from ordinary artifact editor. |

## Native caps (complete)

These caps are already controlled by existing general settings. Individual artifact editing must not silently modify them. A displayed sum of raw artifact values cannot claim to be final player stats: armor, upgrades, percentage effects, conditions and caps also participate.

| Exact MaxValue path | EffectSID | Vanilla |
| --- | --- | --- |
| DefaultEffectMaxParamsSID.MaxEffectValues.[0].MaxValue | EEffectType::ProtectionShock | 90.f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[1].MaxValue | EEffectType::PenaltyLessWeight | 90 |
| DefaultEffectMaxParamsSID.MaxEffectValues.[2].MaxValue | EEffectType::RegenStamina | 30.f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[3].MaxValue | EEffectType::ProtectionStrike | 4.5f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[4].MaxValue | EEffectType::DegenBleeding | 5 |
| DefaultEffectMaxParamsSID.MaxEffectValues.[5].MaxValue | EEffectType::ProtectionBurn | 90.f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[6].MaxValue | EEffectType::ProtectionChemical | 90.f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[7].MaxValue | EEffectType::ProtectionPSY | 90.f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[8].MaxValue | EEffectType::ProtectionRadiation | 85.f |
| DefaultEffectMaxParamsSID.MaxEffectValues.[9].MaxValue | EEffectType::AdditionalInventoryWeight | 140 |

## Identity-based radiation references (complete)

Eight native slot blocker effects name original harmful-radiation SIDs. The tutorial also uses four exact SIDs. New radiation clones need both systems audited; simply deriving from a blocked effect does not establish that the game treats the new SID as blocked.

| File | Exact reference path | Effect |
| --- | --- | --- |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect1.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect2.EffectsToBlockIDs.[0] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3.EffectsToBlockIDs.[1] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3.EffectsToBlockIDs.[2] | ArtifactAddRadiation3 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3.EffectsToBlockIDs.[3] | ArtifactAddRadiation4 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot1.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot1.EffectsToBlockIDs.[1] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot1.EffectsToBlockIDs.[2] | ArtifactAddRadiation3 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot1.EffectsToBlockIDs.[3] | ArtifactAddRadiation4 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot2.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot2.EffectsToBlockIDs.[1] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot2.EffectsToBlockIDs.[2] | ArtifactAddRadiation3 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot2.EffectsToBlockIDs.[3] | ArtifactAddRadiation4 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot3.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot3.EffectsToBlockIDs.[1] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot3.EffectsToBlockIDs.[2] | ArtifactAddRadiation3 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot3.EffectsToBlockIDs.[3] | ArtifactAddRadiation4 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot4.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot4.EffectsToBlockIDs.[1] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot4.EffectsToBlockIDs.[2] | ArtifactAddRadiation3 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot4.EffectsToBlockIDs.[3] | ArtifactAddRadiation4 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot5.EffectsToBlockIDs.[0] | ArtifactAddRadiation1 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot5.EffectsToBlockIDs.[1] | ArtifactAddRadiation2 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot5.EffectsToBlockIDs.[2] | ArtifactAddRadiation3 |
| EffectPrototypes.cfg | ArtifactSlotBlockEffect3_Slot5.EffectsToBlockIDs.[3] | ArtifactAddRadiation4 |
| QuestNodePrototypes.cfg | GDTQ00_BP_ShowTutorialWidget_ArtifactRadiation_Pin_0.Conditions.[0].[0].EffectPrototypeSID | ArtifactAddRadiation1 |
| QuestNodePrototypes.cfg | GDTQ00_BP_ShowTutorialWidget_ArtifactRadiation_Pin_0.Conditions.[0].[1].EffectPrototypeSID | ArtifactAddRadiation2 |
| QuestNodePrototypes.cfg | GDTQ00_BP_ShowTutorialWidget_ArtifactRadiation_Pin_0.Conditions.[0].[2].EffectPrototypeSID | ArtifactAddRadiation3 |
| QuestNodePrototypes.cfg | GDTQ00_BP_ShowTutorialWidget_ArtifactRadiation_Pin_0.Conditions.[0].[3].EffectPrototypeSID | ArtifactAddRadiation4 |

For a first editor, retaining native references or offering an explicit radiation-off replacement avoids introducing a new radiation identity. Selecting an existing radiation tier is also possible, using the live inventory. Changing tier intentionally changes which partial native container matches it. Fully arbitrary per-item radiation requires appending each cloned SID to precisely the blocker lists that contain its source SID, preserving existing entries; quest identity conditions and gameplay behavior still need validation. Do not rewrite unrelated quest conditions as a routine artifact setting.

## Scope and implementation hazards

1. Never patch the shared original effect for a single-artifact override. For example, ArtifactProtectionRadiation1 has 25 artifact-classified users including Weird Water, fakes and quest/prologue variants.
2. A derived effect should use an explicit new SID, mod-name/item/effect namespace, preserve live prototype metadata, and be emitted as a new structure rather than a patch against a nonexistent original. `armor_extensions.lead_composites` provides the current `__new__` precedent. The older `_scope_override_patch` demonstrates per-item reference routing, but its historical emit semantics should not be copied without checking.
3. Preserve `DuplicationType`, lifetime, pause/save flags and triggering lists. There are 57 KeepAll, one KeepOld (Flower), and two KeepNew (Water children) effects in the graph. New identities could change how multiple instances stack or replace one another; a per-item override affects all instances of that prototype, not a single inventory instance.
4. All 60 effects have DelayMin = DelayMax = 0.f, TimePerChargeMin = TimePerChargeMax = 1.f, IsSaveable = true and InstantFirstCharge = false. Fifty-nine have Duration 0.f and Charges 0; FakeArtifactsPSYPoints is Duration 1 and Charges 1. Fifty-eight are permanent; the Fake pickup penalty and Water composite parent are not. Do not interpret Duration 0 as an effect that lasts zero seconds.
5. Every graph effect has empty ValueProviderSID and EffectCurvePath in this baseline. A future version introducing a provider/curve needs explicit handling instead of guessed scalar scaling.
6. Existing `_effects_patch` scales every `Artifact*` ValueMin/Max, except ArtifactAddRadiation* uses the separate radiation factor. This also reaches Kettle food/drink benefits/drawbacks and ArtifactWeirdVodkaEffect. Conversely, Weird Water's child capacity effects, Nut's two effects and Flower's flair effect lack the Artifact prefix and are not covered by that artifact factor. Individual overrides must define whether they replace or multiply the existing global result and avoid double scaling inherited cloned values.
7. The existing armor carrying-bonus branch also matches non-Artifact `AdditionalInventoryWeight` effects. WeirdWaterCarryWeightEffect matches it. A future Water-specific override must compose with that path deliberately.
8. Item effect lists are indexed arrays. Preserve unrelated entries and account for other mods changing list order. `bpatch` and config-only delivery do not imply automatic mod compatibility. A general artifact override should not rewrite fake or quest lists.
9. Avoid exposing numeric ValueMin/Max for FlagEffect or zero-valued Composite parents as if they were actual magnitude controls. Do not add a timer slider to ordinary permanent effects merely because Duration exists.
10. No new extraction files are required for this audited ordinary-effect scope: ItemPrototypes, EffectPrototypes, ObjEffectMaxParams and UpgradePrototypes are already available. A later implementation must increment CACHE_SCHEMA if it adds an extraction dependency.
11. Two excluded fakes have unusual nested data inside a pickup-effect list: EArtifactSoul_Fake.EffectOnPickPrototypeSIDs.ViewOffset is X 0.0 / Y 3.0 / Z 0.0; EArtifactSnowflake_Fake has X 0.0 / Y 3.0 / Z 2.0 there. These are present in the text source, not missing effect SIDs. Do not flatten all descendants of an effect-list structure into effect references or rewrite these fake lists.

## Complete reachable effect baseline table

Type values below omit `EEffectType::`. The columns map to `<EffectSID>.ValueMin`, `.ValueMax`, `.Duration`, `.bIsPermanent`, `.DuplicationType`, and `.ShouldPauseByDialog`. All values are raw literals from live extracted data. Artifact user counts include every classified root, including fakes and quests.

| EffectSID | Type | ValueMin | ValueMax | Duration | Permanent | Duplication | Pause in dialog | Artifact users |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AddRadiation1 | DegenRadiation | -5 | -5 | 0.f | true | KeepAll | true | 2 |
| ArtifactAddRadiation1 | DegenRadiation | -0.1 | -0.1 | 0.f | true | KeepAll | true | 34 |
| ArtifactAddRadiation2 | DegenRadiation | -0.15 | -0.15 | 0.f | true | KeepAll | true | 27 |
| ArtifactAddRadiation3 | DegenRadiation | -0.25 | -0.25 | 0.f | true | KeepAll | true | 22 |
| ArtifactAddRadiation4 | DegenRadiation | -0.5 | -0.5 | 0.f | true | KeepAll | true | 8 |
| ArtifactAdditionalInventoryWeight05 | AdditionalInventoryWeight | 2 | 2 | 0.f | true | KeepAll | false | 6 |
| ArtifactAdditionalInventoryWeight1 | AdditionalInventoryWeight | 3 | 3 | 0.f | true | KeepAll | false | 12 |
| ArtifactAdditionalInventoryWeight2 | AdditionalInventoryWeight | 6 | 6 | 0.f | true | KeepAll | false | 6 |
| ArtifactAdditionalInventoryWeight3 | AdditionalInventoryWeight | 9 | 9 | 0.f | true | KeepAll | false | 4 |
| ArtifactDegenBleeding05 | DegenBleeding | 0.3 | 0.3 | 0.f | true | KeepAll | true | 8 |
| ArtifactDegenBleeding1 | DegenBleeding | 0.5 | 0.5 | 0.f | true | KeepAll | true | 11 |
| ArtifactDegenBleeding2 | DegenBleeding | 1 | 1 | 0.f | true | KeepAll | true | 6 |
| ArtifactDegenBleeding3 | DegenBleeding | 2 | 2 | 0.f | true | KeepAll | true | 2 |
| ArtifactDegenBleeding4 | DegenBleeding | 4 | 4 | 0.f | true | KeepAll | true | 3 |
| ArtifactDurabilityIncrease1 | MaxDurability | 5.0% | 5.0% | 0.f | true | KeepAll | true | 6 |
| ArtifactDurabilityIncrease2 | MaxDurability | 10.0% | 10.0% | 0.f | true | KeepAll | true | 4 |
| ArtifactDurabilityIncrease3 | MaxDurability | 15.0% | 15.0% | 0.f | true | KeepAll | true | 2 |
| ArtifactDurabilityIncrease4 | MaxDurability | 20.0% | 20.0% | 0.f | true | KeepAll | true | 2 |
| ArtifactIncreaseRegenStamina05 | RegenStamina | 1.5 | 1.5 | 0.f | true | KeepAll | true | 6 |
| ArtifactIncreaseRegenStamina1 | RegenStamina | 2.5f | 2.5f | 0.f | true | KeepAll | true | 12 |
| ArtifactIncreaseRegenStamina2 | RegenStamina | 5 | 5 | 0.f | true | KeepAll | true | 7 |
| ArtifactIncreaseRegenStamina3 | RegenStamina | 7.5f | 7.5f | 0.f | true | KeepAll | true | 2 |
| ArtifactIncreaseRegenStamina4 | RegenStamina | 12.5f | 12.5f | 0.f | true | KeepAll | true | 2 |
| ArtifactPenaltyLessWeightEffect05 | PenaltyLessWeight | 2 | 2 | 0.f | true | KeepAll | false | 2 |
| ArtifactPenaltyLessWeightEffect1 | PenaltyLessWeight | 3 | 3 | 0.f | true | KeepAll | false | 12 |
| ArtifactPenaltyLessWeightEffect2 | PenaltyLessWeight | 6 | 6 | 0.f | true | KeepAll | false | 6 |
| ArtifactPenaltyLessWeightEffect3 | PenaltyLessWeight | 9 | 9 | 0.f | true | KeepAll | false | 4 |
| ArtifactProtectionBurn1 | ProtectionBurn | 10 | 10 | 0.f | true | KeepAll | true | 11 |
| ArtifactProtectionBurn2 | ProtectionBurn | 15 | 15 | 0.f | true | KeepAll | true | 4 |
| ArtifactProtectionBurn3 | ProtectionBurn | 20 | 20 | 0.f | true | KeepAll | true | 2 |
| ArtifactProtectionBurn4 | ProtectionBurn | 35 | 35 | 0.f | true | KeepAll | true | 3 |
| ArtifactProtectionChemicalBurn1 | ProtectionChemical | 10 | 10 | 0.f | true | KeepAll | true | 9 |
| ArtifactProtectionChemicalBurn2 | ProtectionChemical | 15 | 15 | 0.f | true | KeepAll | true | 6 |
| ArtifactProtectionChemicalBurn3 | ProtectionChemical | 20 | 20 | 0.f | true | KeepAll | true | 4 |
| ArtifactProtectionChemicalBurn4 | ProtectionChemical | 35 | 35 | 0.f | true | KeepAll | true | 3 |
| ArtifactProtectionRadiation1 | DegenRadiation | 0.1 | 0.1 | 0.f | true | KeepAll | true | 25 |
| ArtifactProtectionRadiation2 | DegenRadiation | 0.15 | 0.15 | 0.f | true | KeepAll | true | 10 |
| ArtifactProtectionRadiation3 | DegenRadiation | 0.25 | 0.25 | 0.f | true | KeepAll | true | 4 |
| ArtifactProtectionRadiation4 | DegenRadiation | 0.5 | 0.5 | 0.f | true | KeepAll | true | 2 |
| ArtifactProtectionShock05 | ProtectionShock | 7 | 7 | 0.f | true | KeepAll | true | 2 |
| ArtifactProtectionShock1 | ProtectionShock | 10 | 10 | 0.f | true | KeepAll | true | 9 |
| ArtifactProtectionShock2 | ProtectionShock | 15 | 15 | 0.f | true | KeepAll | true | 4 |
| ArtifactProtectionShock3 | ProtectionShock | 20 | 20 | 0.f | true | KeepAll | true | 2 |
| ArtifactProtectionShock4 | ProtectionShock | 35 | 35 | 0.f | true | KeepAll | true | 1 |
| ArtifactProtectionStrike05 | ProtectionStrike | 0.07 | 0.07 | 0.f | true | KeepAll | true | 4 |
| ArtifactProtectionStrike1 | ProtectionStrike | 0.1 | 0.1 | 0.f | true | KeepAll | true | 8 |
| ArtifactProtectionStrike2 | ProtectionStrike | 0.25 | 0.25 | 0.f | true | KeepAll | true | 4 |
| ArtifactProtectionStrike3 | ProtectionStrike | 0.5 | 0.5 | 0.f | true | KeepAll | true | 2 |
| ArtifactProtectionStrike4 | ProtectionStrike | 1 | 1 | 0.f | true | KeepAll | true | 3 |
| Artifact_HeartOfChornobyl_RegenHP | RegenHealth | 10 | 10 | 0.f | true | KeepAll | false | 1 |
| Artifact_WeirdBolt_NegativeEffect_SPDrain | SPDrain | 200% | 200% | 0.f | true | KeepAll | true | 1 |
| DegenBleeding10 | DegenBleeding | 2000.0% | 2000.0% | 0.f | true | KeepAll | true | 1 |
| FakeArtifactsPSYPoints | PsyPoints | 10 | 20 | 1 | false | KeepAll | true | 70 |
| FlairDistanceModifierEffect | FlairDistanceModifier | 60.0% | 60.0% | 0.f | true | KeepOld | true | 1 |
| ProtectionShock1 | ProtectionShock | 5.0% | 5.0% | 0.f | true | KeepAll | true | 2 |
| RegenHealthModifier | RegenHealthModifier | -0.75 | -0.75 | 0.f | true | KeepAll | true | 1 |
| WeirdKettleEffect | FlagEffect | 0.f | 0.f | 0.f | true | KeepAll | true | 1 |
| WeirdWaterCarryWeightEffect | AdditionalInventoryWeight | 50.0% | 50.0% | 0.f | true | KeepNew | false | 1 |
| WeirdWaterPenaltyLessWeightEffect | PenaltyLessWeight | 50.0% | 50.0% | 0.f | true | KeepNew | false | 1 |
| WeirdWaterWeightChangeCompositeEffect | Composite | 0.f | 0.f | 0.f | false | KeepAll | false | 1 |

## Complete item reference table (154 rows)

Each semicolon-separated entry is `<relative item path> = <EffectSID>`; prepend the ItemSID column for the full path. `none` means no explicit nonempty reference resolving to EffectPrototypes. This inventory does not make excluded templates/fakes/quests editor candidates.

| ItemSID | Exact references |
| --- | --- |
| TemplateArtifact | none |
| EArtifactFlash | EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| EArtifactFlash_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| EArtifactSoul | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| EArtifactSoul_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| EArtifactSnowflake | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| EArtifactSnowflake_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| GArtifactNightStar | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect3 |
| GArtifactNightStar_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect3 |
| EArtifactDummy | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1 |
| EArtifactDummy_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1 |
| CArtifactCrystalThorn | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| CArtifactCrystalThorn_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| EArtifactBattery | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| EArtifactBattery_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| FArtifactCrystal | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| FArtifactCrystal_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| EArtifactMoonlight | EffectPrototypeSIDs.[0] = ArtifactProtectionShock2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| EArtifactMoonlight_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| FArtifactMomsBeads | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| FArtifactMomsBeads_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| EArtifactJellyFish | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina05; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding05 |
| EArtifactJellyFish_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina05; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding05 |
| EArtifactTow | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2 |
| EArtifactTow_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2 |
| EArtifactThunderHedgehog | EffectPrototypeSIDs.[0] = ArtifactProtectionShock2; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation2 |
| EArtifactThunderHedgehog_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock2; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation2 |
| EArtifactWorm | EffectPrototypeSIDs.[0] = ArtifactProtectionShock05; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding05; EffectPrototypeSIDs.[2] = ArtifactProtectionRadiation1 |
| EArtifactWorm_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock05; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding05; EffectPrototypeSIDs.[2] = ArtifactProtectionRadiation1 |
| EArtifactCloud | EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2 |
| EArtifactCloud_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2 |
| EArtifactAtom | EffectPrototypeSIDs.[0] = ArtifactProtectionShock3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| EArtifactAtom_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| EArtifactRazor | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding2; EffectPrototypeSIDs.[2] = ArtifactAddRadiation3 |
| EArtifactRazor_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[1] = ArtifactDegenBleeding2; EffectPrototypeSIDs.[2] = ArtifactAddRadiation3 |
| EArtifactSparkler | EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| EArtifactSparkler_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| FArtifactFireBall | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| FArtifactFireBall_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| GArtifactGoldFish | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| GArtifactGoldFish_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactSteak | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| FArtifactSteak_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| GArtifactStoneDrop | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| GArtifactStoneDrop_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactBakedBolts | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactBakedBolts_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactGlass | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding05; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight05; EffectPrototypeSIDs.[2] = ArtifactAddRadiation1; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect05 |
| FArtifactGlass_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding05; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight05; EffectPrototypeSIDs.[2] = ArtifactAddRadiation1; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect05 |
| FArtifactDeadSponge | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| FArtifactDeadSponge_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| FArtifactHellishHedgehog | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactHellishHedgehog_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactPlasma | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn2; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation2 |
| FArtifactPlasma_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn2; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation2 |
| FArtifactCandle | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| FArtifactCandle_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| FArtifactRingOmnipotence | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding4; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4; EffectPrototypeSIDs.[2] = ArtifactProtectionBurn4 |
| FArtifactRingOmnipotence_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding4; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4; EffectPrototypeSIDs.[2] = ArtifactProtectionBurn4 |
| FArtifactFireworks | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| FArtifactFireworks_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| FArtifactCore | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn2; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight2; EffectPrototypeSIDs.[2] = ArtifactAddRadiation3; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect2 |
| FArtifactCore_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn2; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight2; EffectPrototypeSIDs.[2] = ArtifactAddRadiation3; EffectPrototypeSIDs.[3] = ArtifactPenaltyLessWeightEffect2 |
| FArtifactBurntHunk | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| FArtifactBurntHunk_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| FArtifactResin | EffectPrototypeSIDs.[0] = ArtifactDegenBleeding05; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight05 |
| FArtifactResin_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactDegenBleeding05; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight05 |
| GArtifactSpring | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect2 |
| GArtifactSpring_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect2 |
| CArtifactPellicle | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn3; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation3 |
| CArtifactPellicle_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn3; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation3 |
| CArtifactChunkMeat | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| CArtifactChunkMeat_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| GArtifactGravy | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| GArtifactGravy_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| FArtifactDrops | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| FArtifactDrops_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| FArtifactEye | EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1 |
| FArtifactEye_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionBurn1 |
| CArtifactBun | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| CArtifactBun_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| CArtifactThorn | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| CArtifactThorn_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| GArtifactWrenched | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1 |
| GArtifactWrenched_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1 |
| GArtifactBloodStone | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| GArtifactBloodStone_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect1 |
| GArtifactGraphiteBlock | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2 |
| GArtifactGraphiteBlock_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[2] = ArtifactAddRadiation2 |
| GArtifactSplitStone | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| GArtifactSplitStone_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| GArtifactTrunk | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina05; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight05 |
| GArtifactTrunk_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina05; EffectPrototypeSIDs.[1] = ArtifactAdditionalInventoryWeight05 |
| GArtifactRubiksCube | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4 |
| GArtifactRubiksCube_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4 |
| GArtifactSponge | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike05; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[2] = ArtifactProtectionRadiation1 |
| GArtifactSponge_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike05; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina1; EffectPrototypeSIDs.[2] = ArtifactProtectionRadiation1 |
| GArtifactHedgehog | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight2; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation2; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect2 |
| GArtifactHedgehog_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight2; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation2; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect2 |
| GArtifactBud | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike2; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[2] = ArtifactAddRadiation3 |
| GArtifactBud_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike2; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[2] = ArtifactAddRadiation3 |
| GArtifactPlane | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike05; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina05; EffectPrototypeSIDs.[2] = ArtifactAddRadiation1 |
| GArtifactPlane_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike05; EffectPrototypeSIDs.[1] = ArtifactIncreaseRegenStamina05; EffectPrototypeSIDs.[2] = ArtifactAddRadiation1 |
| CArtifactMica | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| CArtifactMica_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| CArtifactBubble | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation2 |
| CArtifactBubble_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation2 |
| CArtifactSlime | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1; EffectPrototypeSIDs.[1] = ArtifactDurabilityIncrease1 |
| CArtifactSlime_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1; EffectPrototypeSIDs.[1] = ArtifactDurabilityIncrease1 |
| CArtifactSlug | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| CArtifactSlug_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| CArtifactEchinus | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation2 |
| CArtifactEchinus_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation2 |
| GArtifactCompass | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike4; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4 |
| GArtifactCompass_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike4; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4 |
| CArtifactKryptonite | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| CArtifactKryptonite_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| CArtifactBung | EffectPrototypeSIDs.[0] = ArtifactAddRadiation1; EffectPrototypeSIDs.[1] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease1 |
| CArtifactBung_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAddRadiation1; EffectPrototypeSIDs.[1] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease1 |
| EArtifactCrystalGlass | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| EArtifactCrystalGlass_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3 |
| CArtifactCottonWool | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease1 |
| CArtifactCottonWool_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease1 |
| GArtifactLandSlug | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| GArtifactLandSlug_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| CArtifactRosin | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease2 |
| CArtifactRosin_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease2 |
| CArtifactPlasticine | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease2 |
| CArtifactPlasticine_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease2 |
| EArtifactDope | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina4; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4 |
| EArtifactDope_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina4; EffectPrototypeSIDs.[1] = ArtifactAddRadiation4 |
| CArtifactBouncyBall | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation3 |
| CArtifactBouncyBall_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation3 |
| CArtifactDevilsMushroom | EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease3 |
| CArtifactDevilsMushroom_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionChemicalBurn3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease3 |
| EArtifactChocolate | EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| EArtifactChocolate_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactAddRadiation1 |
| CArtifactLiquidStone | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation4; EffectPrototypeSIDs.[1] = ArtifactProtectionChemicalBurn4; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease4 |
| CArtifactLiquidStone_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation4; EffectPrototypeSIDs.[1] = ArtifactProtectionChemicalBurn4; EffectPrototypeSIDs.[2] = ArtifactDurabilityIncrease4 |
| PArtifactBrain | EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect3 |
| PArtifactBrain_Fake | EffectOnPickPrototypeSIDs.[0] = FakeArtifactsPSYPoints; EffectPrototypeSIDs.[0] = ArtifactAdditionalInventoryWeight3; EffectPrototypeSIDs.[1] = ArtifactAddRadiation3; EffectPrototypeSIDs.[2] = ArtifactPenaltyLessWeightEffect3 |
| PQuestArtifactScraper | EffectPrototypeSIDs.[0] = ProtectionShock1; EffectPrototypeSIDs.[1] = AddRadiation1 |
| PQuestArtifactScraper_Fake | EffectPrototypeSIDs.[0] = ProtectionShock1; EffectPrototypeSIDs.[1] = AddRadiation1 |
| AArtifactWeirdBall | EffectPrototypeSIDs.[0] = ArtifactProtectionStrike1 |
| AArtifactWeirdWater | EffectPrototypeSIDs.[0] = WeirdWaterWeightChangeCompositeEffect; EffectPrototypeSIDs.[1] = ArtifactProtectionRadiation1 |
| AArtifactWeirdNut | EffectPrototypeSIDs.[0] = DegenBleeding10; EffectPrototypeSIDs.[1] = RegenHealthModifier |
| AArtifactWeirdFlower | WakeUpEffectSIDs.[0] = FlairDistanceModifierEffect |
| AArtifactWeirdBolt | EffectPrototypeSIDs.[0] = ArtifactProtectionShock1; EffectPrototypeSIDs.[1] = ArtifactProtectionBurn1; EffectPrototypeSIDs.[2] = ArtifactDegenBleeding1; EffectPrototypeSIDs.[3] = ArtifactProtectionStrike1; EffectPrototypeSIDs.[4] = ArtifactProtectionChemicalBurn1; PositiveEffectPrototypeSIDs.[0] = ArtifactProtectionShock4; PositiveEffectPrototypeSIDs.[1] = ArtifactProtectionBurn4; PositiveEffectPrototypeSIDs.[2] = ArtifactDegenBleeding4; PositiveEffectPrototypeSIDs.[3] = ArtifactProtectionStrike4; PositiveEffectPrototypeSIDs.[4] = ArtifactProtectionChemicalBurn4; NegativeEffectPrototypeSIDs.[0] = Artifact_WeirdBolt_NegativeEffect_SPDrain |
| AArtifactWeirdKettle | EffectPrototypeSIDs.[0] = WeirdKettleEffect |
| CPrologArtifactSlug | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| TemplateQuestArtifact | none |
| SQ13_Soul | EffectPrototypeSIDs.[0] = ArtifactIncreaseRegenStamina2; EffectPrototypeSIDs.[1] = ArtifactAddRadiation2 |
| QuestArtifactCrystalThorn | EffectPrototypeSIDs.[0] = ArtifactProtectionRadiation1 |
| QuestArtifactHeartofChornobyl | EffectPrototypeSIDs.[0] = Artifact_HeartOfChornobyl_RegenHP |

## Complete nested reachable edges

| Exact path | Target effect |
| --- | --- |
| WeirdWaterWeightChangeCompositeEffect.ApplyExtraEffectPrototypeSIDs.[0] | WeirdWaterCarryWeightEffect |
| WeirdWaterWeightChangeCompositeEffect.ApplyExtraEffectPrototypeSIDs.[1] | WeirdWaterPenaltyLessWeightEffect |

## Additional Artifact-prefixed effects outside the direct artifact graph

These 58 effects are the remainder of the broad prefix audit. They demonstrate why prefix-only classification cannot define a per-artifact editor. Zero-valued slot-blocker structures are not strength controls. Some PSY/weight effect prototypes have no direct artifact item reference in the extracted baseline; their existence alone does not prove a normal artifact currently uses them.

| EffectSID | Type | ValueMin | ValueMax | Duration | Permanent |
| --- | --- | --- | --- | --- | --- |
| ArtifactAdditionalInventoryWeight4 | AdditionalInventoryWeight | 12 | 12 | 0.f | true |
| ArtifactProtectionPSY1 | ProtectionPSY | 10.0 | 10.0 | 0.f | true |
| ArtifactProtectionPSY2 | ProtectionPSY | 15.0 | 15.0 | 0.f | true |
| ArtifactProtectionPSY3 | ProtectionPSY | 30.0 | 30.0 | 0.f | true |
| ArtifactProtectionPSY5 | ProtectionPSY | 50.0 | 50.0 | 0.f | true |
| ArtifactSlotBlockEffect1 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect2 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect3 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect3_Slot1 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect3_Slot2 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect3_Slot3 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect3_Slot4 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactSlotBlockEffect3_Slot5 | ArtifactSlotBlock | 0.f | 0.f | 0.f | true |
| ArtifactWeirdVodkaEffect | Drunkness | 50.0 | 50.0 | 0.f | true |
| Artifact_WeirdKettle_BeerAntirad | Radiation | -20 | -20 | 2.0 | false |
| Artifact_WeirdKettle_BeerDrunkness | Drunkness | 5 | 5 | 5.0 | false |
| Artifact_WeirdKettle_BeerPSYInstaDecrease | PsyPoints | -5 | -5 | 0.f | false |
| Artifact_WeirdKettle_BeerSatiety | HungerPoints | 5 | 5 | 0.f | false |
| Artifact_WeirdKettle_BeerStaminaPenalty | SPDrain | 150% | 150% | 20 | false |
| Artifact_WeirdKettle_BreadHealing | Health | 25 | 25 | 2.0 | false |
| Artifact_WeirdKettle_BreadSatiety | HungerPoints | -40 | -40 | 0.f | false |
| Artifact_WeirdKettle_CannedHealing | Health | 60 | 60 | 2.0 | false |
| Artifact_WeirdKettle_CannedSatiety | HungerPoints | -75 | -75 | 0.f | false |
| Artifact_WeirdKettle_EnegeticSatiety | HungerPoints | 10 | 10 | 0.f | false |
| Artifact_WeirdKettle_EnergeticStamina | RegenStamina | 400% | 400% | 45.0 | false |
| Artifact_WeirdKettle_EnergeticStaminaInstant | Stamina | 75% | 75% | 0.f | false |
| Artifact_WeirdKettle_LimitedEnegeticSatiety | HungerPoints | -100 | -100 | 0.f | false |
| Artifact_WeirdKettle_LimitedEnergeticAntirad | Radiation | -100 | -100 | 2.0 | false |
| Artifact_WeirdKettle_LimitedEnergeticBleeding | Bleeding | -100 | -100 | 2.0 | false |
| Artifact_WeirdKettle_LimitedEnergeticHealing | Health | 100 | 100 | 1.0 | false |
| Artifact_WeirdKettle_LimitedEnergeticPSYInstaDecrease | PsyPoints | -100 | -100 | 0.f | false |
| Artifact_WeirdKettle_LimitedEnergeticSleepiness | SleepinessPoints | -100 | -100 | 3.0 | false |
| Artifact_WeirdKettle_LimitedEnergeticStamina | RegenStamina | 500% | 500% | 60.0 | false |
| Artifact_WeirdKettle_LimitedEnergeticStaminaInstant | Stamina | 100% | 100% | 0.f | false |
| Artifact_WeirdKettle_LimitedEnergeticWeightInstaBonus | AdditionalInventoryWeight | 0.5 | 0.5 | 0.f | true |
| Artifact_WeirdKettle_LimitedEnergeticWeightInstaBonus_PenaltyLessWeight | PenaltyLessWeight | 0.5 | 0.5 | 0.f | true |
| Artifact_WeirdKettle_MilkHealing | Health | 50 | 50 | 2.0 | false |
| Artifact_WeirdKettle_MilkSatiety | HungerPoints | -100 | -100 | 0.f | false |
| Artifact_WeirdKettle_MilkStaminaInstant | Stamina | 50% | 50% | 0.f | false |
| Artifact_WeirdKettle_NegativeEffect_Bleeding_CannedFood | Bleeding | 25 | 25 | 5.0 | false |
| Artifact_WeirdKettle_NegativeEffect_Drunkness_Bread | Drunkness | 20 | 20 | 5.0 | false |
| Artifact_WeirdKettle_NegativeEffect_PSY_Energetic | PsyPoints | 20.0f | 20.0f | 1 | false |
| Artifact_WeirdKettle_NegativeEffect_PSY_Milk | PsyPoints | 20.0f | 20.0f | 1 | false |
| Artifact_WeirdKettle_NegativeEffect_Radiation_Sausage | Radiation | 10 | 10 | 2.0 | false |
| Artifact_WeirdKettle_NegativeEffect_Radiation_Water | Radiation | 10 | 10 | 2.0 | false |
| Artifact_WeirdKettle_NegativeEffect_Satiety | HungerPoints | 33 | 33 | 0.f | false |
| Artifact_WeirdKettle_NegativeEffect_Sleepiness_Beer | SleepinessPoints | 5 | 5 | 0.f | false |
| Artifact_WeirdKettle_NegativeEffect_Sleepiness_Vodka | SleepinessPoints | 10 | 10 | 0.f | false |
| Artifact_WeirdKettle_SausageHealing | Health | 40 | 40 | 2.0 | false |
| Artifact_WeirdKettle_SausageSatiety | HungerPoints | -60 | -60 | 0.f | false |
| Artifact_WeirdKettle_VodkaAntirad | Radiation | -80 | -80 | 2.0 | false |
| Artifact_WeirdKettle_VodkaDrunkness | Drunkness | 40 | 40 | 5.0 | false |
| Artifact_WeirdKettle_VodkaPSYInstaDecrease | PsyPoints | -15 | -15 | 0.f | false |
| Artifact_WeirdKettle_VodkaSatiety | HungerPoints | 10 | 10 | 0.f | false |
| Artifact_WeirdKettle_WaterSatiety | HungerPoints | -10 | -10 | 0.f | false |
| Artifact_WeirdKettle_WaterStamina | RegenStamina | 25% | 25% | 15.0 | false |
| Artifact_WeirdKettle_WaterStaminaInstant | Stamina | 50% | 50% | 0.f | false |
| Artifact_WeirdKettle_WaterStaminaPerAction | SPDrain | -20% | -20% | 30.0 | false |

## Complete related non-artifact item references

41 exact references across 14 consumable item roots, including quest variants. These are outside the direct equipped-artifact graph. Kettle behavior therefore cannot be discovered by following only AArtifactWeirdKettle.EffectPrototypeSIDs.

| Exact item path | Effect |
| --- | --- |
| Bread.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_BreadSatiety |
| Bread.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_BreadHealing |
| FreshBread.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_BreadSatiety |
| FreshBread.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_BreadHealing |
| CannedFood.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_CannedSatiety |
| CannedFood.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_CannedHealing |
| SpoiledCannedFood.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_CannedSatiety |
| SpoiledCannedFood.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_CannedHealing |
| Vodka.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_VodkaAntirad |
| Vodka.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_VodkaSatiety |
| Vodka.AlternativeEffectPrototypeSIDs.[3] | Artifact_WeirdKettle_VodkaDrunkness |
| Sausage.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_SausageSatiety |
| Sausage.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_SausageHealing |
| Energetic.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_EnegeticSatiety |
| Energetic.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_EnergeticStamina |
| Energetic.AlternativeEffectPrototypeSIDs.[2] | Artifact_WeirdKettle_EnergeticStaminaInstant |
| Energetic_Limited.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_LimitedEnegeticSatiety |
| Energetic_Limited.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_LimitedEnergeticStamina |
| Energetic_Limited.AlternativeEffectPrototypeSIDs.[2] | Artifact_WeirdKettle_LimitedEnergeticStaminaInstant |
| Energetic_Limited.AlternativeEffectPrototypeSIDs.[4] | Artifact_WeirdKettle_LimitedEnergeticSleepiness |
| Energetic_Limited.AlternativeEffectPrototypeSIDs.[7] | Artifact_WeirdKettle_LimitedEnergeticWeightInstaBonus |
| Energetic_Limited.AlternativeEffectPrototypeSIDs.[8] | Artifact_WeirdKettle_LimitedEnergeticWeightInstaBonus_PenaltyLessWeight |
| Beer.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_BeerSatiety |
| Beer.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_BeerAntirad |
| Beer.AlternativeEffectPrototypeSIDs.[2] | Artifact_WeirdKettle_BeerStaminaPenalty |
| Beer.AlternativeEffectPrototypeSIDs.[3] | Artifact_WeirdKettle_BeerDrunkness |
| Beer.AlternativeEffectPrototypeSIDs.[4] | Artifact_WeirdKettle_BeerPSYInstaDecrease |
| Water.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_WaterSatiety |
| Water.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_WaterStamina |
| Water.AlternativeEffectPrototypeSIDs.[3] | Artifact_WeirdKettle_WaterStaminaInstant |
| Water.AlternativeEffectPrototypeSIDs.[4] | Artifact_WeirdKettle_WaterStaminaPerAction |
| Milk.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_MilkSatiety |
| Milk.AlternativeEffectPrototypeSIDs.[2] | Artifact_WeirdKettle_MilkHealing |
| Milk.AlternativeEffectPrototypeSIDs.[3] | Artifact_WeirdKettle_MilkStaminaInstant |
| Milk.NegativeEffectPrototypeSIDs.[0].Effect | Artifact_WeirdKettle_NegativeEffect_PSY_Milk |
| DvupalovVodka.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_VodkaDrunkness |
| DvupalovVodka.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_VodkaSatiety |
| EQ08_FreshBread.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_BreadSatiety |
| EQ08_FreshBread.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_BreadHealing |
| EQ82_konserva.AlternativeEffectPrototypeSIDs.[0] | Artifact_WeirdKettle_CannedSatiety |
| EQ82_konserva.AlternativeEffectPrototypeSIDs.[1] | Artifact_WeirdKettle_CannedHealing |

## Handoff

Recommended scope: ordinary artifacts first, per-effect magnitude and item-specific weight/price handled separately, explicit exclusions for templates/fakes/quests, and a narrowly designed radiation option. Benefits should be derived per item; arbitrary radiation and Weird artifacts need extra identity/trigger checks. A raw comparison or equipment planner can reuse these baselines, but must distinguish raw bonuses from final gameplay stats.

Required gameplay cases after implementation: equip/unequip; two instances of the same edited artifact; edited plus unedited artifacts sharing a source effect; each supported radiation tier with/without native and tool-added lead slots; save/load; global-factor composition; fake/quest objects unchanged; Weird-specific triggers if later included. Config parsing and Pak readback alone cannot verify these cases.

The tables record configuration evidence, not an installed mod or implemented feature.
