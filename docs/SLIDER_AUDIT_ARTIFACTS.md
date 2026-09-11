# Artifact, detector and consumable slider audit

Static audit of the local 2.0.5 text baseline against the 1.40.1 code, 2026-09-11. Research only: no production settings, generated game mod, installation or gameplay behavior changed. Values below describe this inspected installation; future implementation must resolve its own live values. All game paths are relative to `vanilla/Stalker2/Content/GameLite/GameData/`.

## Sources and existing coverage

| Source | Lines | Top-level structs |
| --- | ---: | ---: |
| `ItemPrototypes.cfg` | 92,232 | 1,375 |
| `EffectPrototypes.cfg` | 85,869 | 2,426 |
| `ArtifactSpawnerPrototypes.cfg` | 6,848 | 98 |
| `AnomalyPrototypes.cfg` | 1,225 | 28 |
| `PassiveDetectorPrototypes.cfg` | 51 | 4 |

Counts and file hashes were recorded with the private scripts/results under `out/slider_audit_1401/artifacts/`. This audit does not scan the multi-million-line quest/spawn files. Reference counts below cover the item and effect inventories, not arbitrary Blueprint references.

The current code in [artifact_extensions.py](../s2tweaker/artifact_extensions.py) defines 984 detail-control identities, of which **871 are supported by this baseline**. These are possible editor settings, not 871 simultaneously rendered slider widgets.

| Detail group | Defined | Available | Current coverage |
| --- | ---: | ---: | --- |
| Ordinary artifacts | 917 | 814 | 69 items: 69 weights, 69 prices, 114 existing bonus values, 44 native radiation selectors, 518 additions of absent bonus families |
| Detectors | 20 | 14 | Echo/Bear/Gilka: reveal, work and near radius; Veles adds sonar and anomaly radius |
| Weird Ball | 7 | 7 | Damage-to-stamina, damage-to-weight, dynamic minimum/maximum weight, recovery delay/rate/amount |
| Moving anomalies | 8 | 8 | Base plus artifact-influenced speed, and pursuit distance, for four ordinary variants |
| Rarity profiles | 32 | 28 | Four ranks of two live spawners; zero-baseline tiers remain unavailable |

The main Artifacts section in [gui.py](../s2tweaker/gui.py) additionally has **13 sliders and three checkboxes**: global strength/radiation/spawn chance/rarity/count/respawn, Weird charge-duration, raw artifact radius, four hop/keep-away settings, detector/scanner range, and the three no-hop/no-detector/cache switches. The label-follow checkbox, permanent Weird Flower option, artifact slots and caps, prices/weights, and stash additions exist elsewhere. Do not present any of these as new proposals.

The consumable baseline classifies 25 item roots as consumables; that includes two templates and the guitar. Nineteen ordinary food/medicine items have effect lists, plus `DvupalovVodka`, `EQ08_FreshBread` and `EQ82_konserva`. Current helpers expose **40 distinct strength effects, four medical healing effects and 12 duration effects**, using three broad strength/healing/duration sliders. The 12 duration effects include `MagicVodkaDrunkness=15` and the two Poppy Field sleepiness effects; this is a measured inventory of existing behavior, not a claim that all are ordinary buffs or should enter a new editor.

The old [adjacent-artifact research](ARTIFACT_ADJACENT_RESEARCH.md) predates the completed detail editor. Its per-detector, Weird Ball, moving-anomaly speed/pursuit and rarity proposals are already implemented.

## 1. Weird Nut: separate bleeding benefit and healing drawback

**Priority: high for the next artifact addition. Effort: medium. Gameplay confidence: needs a focused equipment/healing test.** Let the player reduce the Nut's healing drawback independently of its bleeding protection. This is absent from the ordinary-artifact editor and the global Weird duration/charge control.

Full proposed scalar source inventory:

| Exact source path | Live value | Meaning supported by the data |
| --- | --- | --- |
| `ItemPrototypes.cfg: AArtifactWeirdNut.EffectPrototypeSIDs.[0]` | `DegenBleeding10` | Equipped bleeding-decay effect |
| `EffectPrototypes.cfg: DegenBleeding10.ValueMin` / `.ValueMax` | `2000.0%` / `2000.0%` | `EEffectType::DegenBleeding`, permanent positive effect |
| `ItemPrototypes.cfg: AArtifactWeirdNut.EffectPrototypeSIDs.[1]` | `RegenHealthModifier` | Equipped health-regeneration modifier |
| `EffectPrototypes.cfg: RegenHealthModifier.ValueMin` / `.ValueMax` | `-0.75` / `-0.75` | `EEffectType::RegenHealthModifier`, permanent negative effect |

The item directly declares both slots and inherits `TemplateArtifact`. Both effect roots inherit `[0]`, explicitly declare all these values, use `KeepAll`, and have no value provider or curve. Each effect has exactly one reference within the item/effect inventory, on Weird Nut; neither special item has a direct descendant in the item inventory. Preserve types, permanence, save/dialog behavior and localization identity. Do not patch `[0]` or `TemplateArtifact`.

An item-specific clone attached to the existing slot gives a bounded implementation and avoids claiming the generic `RegenHealthModifier` identity has no engine/quest users elsewhere. At 50% of the current drawback, both `-0.75` values become `-0.375`; the bleeding effect remains `2000.0%`. This is arithmetic on the configured modifier, not a proven percentage reduction in final healing. Do not label it “medkits heal X% faster” until measured. Preserve the percent suffix on the bleeding effect.

## 2. Weird Water: paired carry bonus and independent minimum intoxication

**Priority: high. Effort: medium because the equipped effect is composite. Gameplay confidence: conditional; minimum-intoxication semantics require measurement.** Expose the paired capacity bonus and a separate raw minimum-drunkness setting. This gives the player useful control over a special artifact beyond ordinary radiation/strength controls.

Complete proposed field set:

| Exact source path | Live value |
| --- | --- |
| `ItemPrototypes.cfg: AArtifactWeirdWater.MinimalDrunkenness` | `15.0` |
| `AArtifactWeirdWater.EffectPrototypeSIDs.[0]` | `WeirdWaterWeightChangeCompositeEffect` |
| `EffectPrototypes.cfg: WeirdWaterWeightChangeCompositeEffect.ApplyExtraEffectPrototypeSIDs.[0]` | `WeirdWaterCarryWeightEffect` |
| `WeirdWaterWeightChangeCompositeEffect.ApplyExtraEffectPrototypeSIDs.[1]` | `WeirdWaterPenaltyLessWeightEffect` |
| `WeirdWaterCarryWeightEffect.ValueMin` / `.ValueMax` | `50.0%` / `50.0%` |
| `WeirdWaterPenaltyLessWeightEffect.ValueMin` / `.ValueMax` | `50.0%` / `50.0%` |

The item inherits `TemplateArtifact`, the three effect roots inherit `[0]`, and all selected leaves are directly declared. The composite is nonpermanent `KeepAll`; its two child effects are permanent `KeepNew`, with types `AdditionalInventoryWeight` and `PenaltyLessWeight`. Keep those identities and the composite lifecycle intact. Item/effect reference discovery finds precisely the chain above for these three effects. There is no direct item descendant of Weird Water.

The current broad armor-carry multiplier already scales the `AdditionalInventoryWeight` leaf through `_effects_patch`; it does not scale the paired `PenaltyLessWeight` leaf. A new explicit Weird Water override therefore needs a documented precedence/composition policy, using the original live sources once. It must not accidentally multiply the already modified carry result again. A 150% artifact-specific factor would make both 50% leaves 75%; do not present either value as kilograms. Preserve the separate existing `ArtifactProtectionRadiation1` at item slot `[1]`.

Do not promise “no intoxication at all” from setting `MinimalDrunkenness` to zero: the item Blueprint can still have additional drunkness behavior. The feasible first label is a raw minimum setting with a gameplay check. Test equip/unequip, save/load, carried weight changes and simultaneous Hercules use.

## 3. Individual medicine, food and buff settings

**Priority: high for general usefulness. Effort: medium to large. Gameplay confidence: clear native numeric sources, but per-item isolation and alternative effect lists need careful implementation.** Let players strengthen bandages without stronger food, change a specific medkit's bleeding removal independently of healing, or lengthen Hercules without lengthening all drinks.

There is currently no consumable override mapping or per-item effect editor. The proposed first phase is four medical items plus AntiRad, Hercules, Cinnamon and PSYBlocker; food/drinks can follow the same verified model. These are existing effects, not newly invented healing systems.

Complete medical first-phase baseline. Each listed effect has equal `.ValueMin` and `.ValueMax`; the table lists both through that equality. Paths are `EffectPrototypes.cfg: <effect>.ValueMin`, `.ValueMax`, `.Duration`. Item slot prefixes are `ItemPrototypes.cfg: <item>.EffectPrototypeSIDs`.

| Item / slot | Effect | ValueMin = ValueMax | Duration |
| --- | --- | --- | --- |
| Bandage `[0]` | BandageHealing2 | 20 | 1.0 |
| Bandage `[1]` | BandageBleeding4 | -100 | 2.0 |
| Medkit `[0]` | MedkitHealing3 | 70 | 1.0 |
| Medkit `[1]` | MedkitBleeding2 | -15 | 2.0 |
| ArmyMedkit `[0]` | ArmyMedkitHealing4 | 85 | 1.0 |
| ArmyMedkit `[1]` | ArmyMedkitBleeding3 | -35 | 2.0 |
| EcoMedkit `[0]` | EcoMedkitHealing4 | 100 | 1.0 |
| EcoMedkit `[1]` | EcoMedkitBleeding2 | -25 | 2.0 |
| EcoMedkit `[2]` | EcoMedkitAntirad3 | -60 | 2.0 |
| AntiRad `[0]` | Antirad4 | -100 | 2.0 |
| Hercules `[0]` | HerculesWeight | 20 | 300.f |
| Hercules `[1]` | HerculesWeight_Penalty | 20 | 300.f |
| Cinnamon `[0]` | CinnamonDegenBleeding | 10.0 | 180.f |
| PSYBlocker `[0]` | PSYBlockerIncreaseRegen | 10 | 60.0 |

All eight item roots inherit `TemplateConsumable`; all 14 effect roots above inherit `[0]` and explicitly declare the numeric fields. The medical damage-removal values are negative by design. Strength and time are separate controls: extending a 1-second medical effect can slow delivery and is not equivalent to adding a longer beneficial buff. First phase should expose duration only on the ongoing Hercules/Cinnamon/PSYBlocker effects. Couple Hercules's capacity and penalty-free threshold strength/duration; the `_Penalty` name denotes an additional positive threshold benefit, not a harmful aftereffect.

Example: Bandage healing at 150%, broad consumable strength at 120%, medical healing at 100% yields `20 × 1.5 × 1.2 = 36` on that item's healing clone. Bandage bleeding remains unchanged unless separately selected. Hercules duration at 200% changes both 300-second leaves to 600 seconds; its quantity does not automatically double.

Important existing behavior: Hercules magnitude is not in the 40-effect consumable-strength helper. Its capacity effect can be changed by the broad armor-carry control, while duration covers both Hercules effects. Explicit per-item controls must compose with these existing behaviors, rather than treating all benefits as identical.

For later food/drink expansion, do not simply edit shared effect roots or select all category matches. `FreshBread` descends from `Bread`; `EQ08_FreshBread` descends from `FreshBread`. `SpoiledCannedFood` descends from `CannedFood`, with quest descendant `EQ82_konserva`. `DvupalovVodka` inherits `Vodka`. `Energetic_Limited` inherits `Energetic`. Preserve existing child slots and exclude the two templates, guitar and three quest-specific named items from the first ordinary editor. The current category alone includes these special cases.

`AlternativeEffectPrototypeSIDs` exists on drinks; a future editor must inspect and preserve the alternative branch instead of only the main effect list. Reuse the existing artifact editor's lessons about deterministic clones, native localization and transitive inheritance protection, but do not assume its append-guard scheme automatically applies to consumables. No source or quest variants should acquire an unrequested bonus.

## 4. Optional consumable drawbacks, separate from benefits

**Priority: medium. Effort: medium. Gameplay confidence: field semantics vary; alcohol stamina percentage needs a neutral-baseline test.** A dedicated section could reduce hunger or alcohol penalties while preserving radiation removal, food healing and normal global buff settings. These magnitudes are intentionally outside the current beneficial-strength control.

Complete candidate/deferred penalty inventory for the scoped ordinary drinks/food. Paths are `EffectPrototypes.cfg: <SID>.ValueMin`, `.ValueMax`, `.Duration`; both magnitude endpoints are equal in every row.

| Effect | ValueMin = ValueMax | Duration | Scope / disposition |
| --- | --- | --- | --- |
| VodkaDrunkness | 30 | 5.0 | Ordinary vodka intoxication |
| BeerDrunkness | 15 | 5.0 | Beer intoxication |
| VodkaStaminaPenalty | 200% | 20 | Vodka main and alternative lists; neutral percentage semantics need measurement |
| BeerStaminaPenalty | 200% | 20 | Beer stamina penalty; same semantic caution |
| VodkaSatiety1 | 10 | 0.f | Shared with DvupalovVodka; clone/repoint the ordinary item only |
| BeerSatiety1 | 10 | 0.f | Beer hunger increase |
| EnegeticSatiety1 | 10 | 0.f | Ordinary energy-drink hunger increase |
| EnegeticSatiety2 | 5 | 0.f | Limited energy-drink hunger increase |
| EnergeticOverusePoints | 200 | 0.f | Defer: duplicate references and alternative lists |
| EnergeticTolerancePoints | 300 | 0.f | Defer: duplicate references and alternative lists |
| SpoiledCannedDamage1 | 15 | 0.f | Shared with EQ82_konserva; defer until quest-child isolation is implemented |

All 11 effects inherit `[0]` and declare the selected values. All use `KeepAll`. Do not infer benefits from `Positive` alone: both ordinary alcohol drunkness effects say `EBeneficial::Positive`, while `EnergeticOverusePoints` spells `EBeneficial::negative` with a lowercase value. Use an explicit effect type/sign and item-slot policy.

The limited energy drink's main list contains Overuse at `[5]` and `[7]`, and Tolerance at `[6]` and `[8]`; its alternative list has further references. Do not flatten/deduplicate these arrays or silently assume one application per drink. An overuse/tolerance control is not ready for the first phase.

For the additive hunger amount, 50% of `VodkaSatiety1=10` gives 5 on an ordinary-item clone. For `SPDrain=200%`, blindly multiplying to 100% may have a different neutral meaning from multiplying to zero; verify the runtime contract before describing a “no hangover” endpoint. Altering a penalty's duration is also separate from its strength. Keep scripted magic-vodka behavior and quest-food injury unchanged.

## 5. Independent passive anomaly warning and search scanner ranges

**Priority: medium; a small useful extension. Effort: low. Gameplay confidence: same native radius mechanism already used by the global control.** The existing four-detector editor covers held artifacts detectors. It does not let players tune the passive anomaly beeper independently from the PDA search scanner.

Complete file baseline, including exclusions:

| Exact patch path | SID / type | Live radius | Proposed scope |
| --- | --- | --- | --- |
| `PassiveDetectorPrototypes.cfg: [0].DetectorRadius` | Empty / None | 0.f | Never patch template |
| `[1].DetectorRadius` | PlayerDetector / Anomaly | 1000.0 | Separate passive anomaly-warning range |
| `[2].DetectorRadius` | PlayerSearchpointDetector / Searchpoint | 1000.0 | Separate search-point range |
| `[3].DetectorRadius` | CollarSearchpointDetector / Searchpoint | 1000.0 | Exclude quest collar scanner from new ordinary controls |

The three real roots inherit `[0]`, but each directly declares its radius. Patch the live root key matched by SID and type; the SID is not the root key. Leave sound curves and all nine anomaly exclusions on PlayerDetector intact. Do not claim range changes add detection of anomalies excluded by the native list.

Current `_passive_detector_patch` scales all three nonzero radii together, including the collar scanner. New specific settings should override only `[1]`/`[2]` after that existing result, with inherit as default. Example: global range 150% produces 1500 for each current scanner; an explicit ordinary anomaly radius of 800 should produce 800 only on PlayerDetector. The other global results remain as chosen by the user. No need to change the four existing detector editors or introduce a new extraction dependency.

## Moving anomalies: remaining lower-priority opportunities

The useful speed and pursuit-distance controls are already implemented. The following are real unexposed fields, but rank below the five proposals above because their exact gameplay meaning has not been measured. Full selected baseline from `AnomalyPrototypes.cfg`; paths are `<SID>.<column>`.

| SID | TargetLostDelay | MaxArtifactsToUpSpeed | OnlyDetectSlotsArtifacts |
| --- | --- | --- | --- |
| LightningBallMediumAnomaly | 3.0 | 5 | true |
| LightningBallSmallAnomaly | 3.0 | 5 | true |
| LightningBallBigAnomaly | 3.0 | 5 | true |
| FireBallAnomaly | 3.0 | 5 | true |
| LightningBallPrologueAnomaly | 3.0 | 5 | false |

Medium and FireBall inherit Empty; Small, Big and Prologue inherit Medium but declare all selected leaves themselves. `TargetLostDelay` suggests a useful pursuit-memory control; 50% gives 1.5 from the current 3.0. `MaxArtifactsToUpSpeed` suggests a sensitivity threshold, but does not establish how intermediate artifact counts affect speed. Exclude Prologue. Do not turn `OnlyDetectSlotsArtifacts` into a blanket “artifacts attract anomalies” toggle without establishing the carried-versus-equipped runtime behavior. Do not advertise `ArtifactEatingTime` as an artifact-theft switch.

## Boundaries and implementation order

1. Artifact-focused choice: Weird Nut, then Weird Water. The source relationships are small and understandable, while respecting their special behavior outside the ordinary editor.
2. Broad-use choice: individual medical/buff editor, then ordinary food/drinks with effect-list inheritance and alternatives handled.
3. Small addition: separate passive warning/search ranges. Optional penalties come after exact endpoint and quest-isolation checks.

The existing raw artifact `Radius` slider remains unproven; detector `ShowArtifactRadius` is already available and is the researched reveal mechanism. A higher UI maximum for the raw radius does not add proven functionality. Weird Bolt still has `bUseCharge=false` despite charge fields; do not promise charge-speed controls as effective from those fields alone. Weird Kettle's equipped `WeirdKettleEffect` is a flag effect with zero magnitude, so a generic strength slider is not justified. Special-artifact detectability and element-specific spawn-list weighting also remain unproven, as documented in the earlier research.

All candidate source files are already extracted. No `NEEDED_FILES` addition or `CACHE_SCHEMA` bump is needed for these scoped designs; that changes if a future runtime/Blueprint investigation introduces a new extraction dependency. Implementation must remain sparse, use `gd.resolve(...)`, preserve percent literals and native localized identities, verify global-factor composition, and test only the chosen changes. Static references and arithmetic are not in-game confirmation.
