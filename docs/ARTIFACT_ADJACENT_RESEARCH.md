# Adjacent artifact opportunities — static research, 2026-09-11

[Research overview and implementation priorities](ARTIFACT_EDITOR_RESEARCH.md)

The following is research of the installed 2.0.5 text baseline, not an implemented feature or gameplay validation. No product files, saves, game installation, Git history or releases were changed. The [complete spawner baseline CSV](ARTIFACT_SPAWNER_BASELINES.csv) contains all 98 roots and four rank sections per root for the selected scalar fields; the tables below focus on candidate and excluded example profiles.

All config paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`. Top-level counts were independently checked against unindented struct declarations; the huge SpawnActor file was streamed rather than fully parsed.

| Source | Lines | Top-level structs |
| --- | --- | --- |
| ItemPrototypes.cfg | 92232 | 1375 |
| ArtifactSpawnerPrototypes.cfg | 6848 | 98 |
| PassiveDetectorPrototypes.cfg | 51 | 4 |
| AnomalyPrototypes.cfg | 1225 | 28 |
| SpawnActorPrototypes.cfg | 5068665 | 130058 |

## 1. Per-detector settings, separating signal range from artifact reveal range

**Strongest next adjacent feature.** Current `Settings.detector_range_factor`, `GameData.DETECTOR_RANGE_KEYS`, `_items_patch` and `_passive_detector_patch` scale all five supported radius keys on detectors and the passive scanner radius together. There is no per-detector override or independent reveal-range setting.

A new editor could select Echo, Bear, Gilka or Veles and adjust `ItemPrototypes.<SID>.ShowArtifactRadius` separately from `<SID>.DetectorWorkRadius`, retaining a separate control for `MinDetectRadius`. Only Veles has `SonarRadius` and `AnomalyDetectionRadius`; do not invent those capabilities for the other detectors. Existing global scaling must compose predictably, and neutral values must emit no patch. Units and the exact relationship of MinDetectRadius to rendering should remain as raw baseline values until measured in game.

The full detector inventory contains seven roots: four ordinary models, two templates and one quest Echo. All radius and update-interval values below are explicitly present in each included root except the em dashes, which denote absent keys, not zero.

| SID (start line) | ShowArtifactRadius | MinDetectRadius | DetectorWorkRadius | SonarRadius | AnomalyDetectionRadius | DisplayUpdateInterval |
| --- | --- | --- | --- | --- | --- | --- |
| TemplateDetector (55380) | 0.f | 0.f | 0.f | — | — | 1 |
| Veles (55432) | 400.f | 400.0 | 6000.0 | 1500.f | 1500.f | 1 |
| Bear (55517) | 300.0 | 300.0 | 5000.0 | — | — | 1 |
| Echo (55570) | 230.0 | 230.0 | 5000.0 | — | — | 1 |
| Gilka (55623) | 250.0 | 100.0 | 10000.0 | — | — | 1.5 |
| TemplateQuestDetector (58529) | 0.f | 0.f | 0.f | — | — | 1 |
| EchoE01 (76705) | 230.0 | 230.0 | 5000.0 | — | — | 1 |

`Veles`, `Bear`, `Echo` and `Gilka` declare `refkey=TemplateDetector`. `TemplateDetector` has `refurl=../ItemPrototypes.cfg;refkey=[0]`; `TemplateQuestDetector` refers to `DetectorPrototypes.cfg/TemplateDetector`; `EchoE01` refers to `DetectorPrototypes.cfg/Echo`, but the merged file repeats the inspected values locally. Patch ordinary named roots, not the template. Explicitly exclude `TemplateDetector`, `TemplateQuestDetector` and `EchoE01`; the latter two declare both `IsQuestItem=true` and `IsQuestItemPrototype=true`.

Passive detectors must be separate from a per-item range override. Complete baseline in `PassiveDetectorPrototypes.cfg`:

| Patch root | SID | DetectorRadius | Disposition |
| --- | --- | --- | --- |
| [0] | Empty | 0.f | Never patch template |
| [1] | PlayerDetector | 1000.0 | Optional independent anomaly-warning setting |
| [2] | PlayerSearchpointDetector | 1000.0 | Separate search-point setting |
| [3] | CollarSearchpointDetector | 1000.0 | Keep quest scanner out of ordinary detector editor |

All seven detector roots explicitly exclude the same six special artifacts using `ExclusionArtifactList.[0..5]`: AArtifactWeirdBall, AArtifactWeirdWater, AArtifactWeirdNut, AArtifactWeirdFlower, AArtifactWeirdBolt and AArtifactWeirdKettle. Preserve this list initially. Removing it does not prove the game will detect or display those objects. Veles also excludes DiamondAnomaly, PillowAnomaly, ClickerAnomaly and PsyAnomaly; adding anomaly types would need a separate rendering/engine audit.

`DisplayUpdateInterval` is another new numeric key, but defer it until the engine's update semantics and performance effects are measured. It is not needed for the first useful per-detector release.

## 2. Weird Ball weight and stamina tuning

Current special-artifact control `_weird_artifact_patch` scales only `EffectsDuration` and `MaxCharge`; the permanent Weird Flower addition is also already implemented. The Weird Ball's seven fields below are untouched by those controls and by the current artifact behavior patch. They provide a stronger new special-artifact candidate than adding another global multiplier.

Exact patch prefix: `ItemPrototypes.cfg: AArtifactWeirdBall` (root starts at line 27887), `refkey=TemplateArtifact`. Every selected value is explicitly declared on that root:

| Complete patch key | Vanilla raw value |
| --- | --- |
| AArtifactWeirdBall.DamageToStaminaCoefficient | 2.0 |
| AArtifactWeirdBall.DamageToWeightCoefficient | 0.01 |
| AArtifactWeirdBall.MinWeight | 0.5 |
| AArtifactWeirdBall.MaxWeight | 7.5 |
| AArtifactWeirdBall.WeightDecreaseDelay | 0.0 |
| AArtifactWeirdBall.WeightDecreaseRate | 10.0 |
| AArtifactWeirdBall.WeightDecreaseAmount | 0.2 |

Likely useful user-facing options are the dynamic weight ceiling and weight recovery, then the stamina cost. This interpretation follows key names; it is not a measured engine contract. The base inventory `AArtifactWeirdBall.Weight` is 0.3, while `MinWeight` is 0.5 and `MaxWeight` is 7.5: do not treat the static weight and dynamic bounds as one parameter. Preserve `MinWeight <= MaxWeight`; avoid treating zero-delay baselines as multiplier-controlled values. Do not promise a specific recovery time until WeightDecreaseRate versus WeightDecreaseAmount has been measured.

Arithmetic check for a future neutral-relative control: a 50% MaxWeight factor gives 7.5 × 0.5 = 3.75, while the minimum remains 0.5. A 50% WeightDecreaseAmount factor gives 0.2 × 0.5 = 0.1; this would likely slow recovery, so an eventual label should describe measured behavior, not assume a larger factor is always beneficial.

Do not sweep all `AArtifactWeird*` roots with these keys. Weird Bolt has a separate `AnomalyDamageDeflections.[0..11]` array, and importantly `AArtifactWeirdBolt.bUseCharge=false` despite `MaxCharge=300.0`, `ChargeThreshold=1.0` and `ChargingSpeed=20.0`. That contradiction is a reason to defer additional Bolt charge promises pending Blueprint/gameplay verification.

## 3. More detailed rarity profiles, with a quest-sharing caveat

Current `_artifact_spawner_patch` already offers global count, cooldown, base chance and a single rare-bias multiplier. The existing rare-bias logic changes Uncommon/Rare/Epic together and cannot create a nonzero Epic probability from a zero baseline. A new profile could separately tune already-enabled rarity tiers for each of the four rank sections. Do not present general artifact spawn chance/count as new features.

The inspected file has 98 roots and 392 rank sections. Exactly five roots have `UseListOfArtifacts=false`: Empty, UniversalArtifactSpawner, MSDemoArtifactSpawner, LesserZoneMagneticShortDistance and ArtifactSpawnerBase. The supported research target is UniversalArtifactSpawner plus LesserZoneMagneticShortDistance; the other three are templates/demo data.

Complete selected-field baselines for the two candidate roots (all values are explicitly repeated on each root, including the derived LesserZone root):

| Spawner / rank | Count | Radius | MinCooldown | MaxCooldown | SpawnChanceBase | SpawnChanceBonus | Common | Uncommon | Rare | Epic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UniversalArtifactSpawner.Newbie | 1 | 2000.f | 5400.f | 5400.f | 25.f | 15.f | 80.f | 20.f | 0.f | 0.f |
| UniversalArtifactSpawner.Experienced | 1 | 2000.f | 5400.f | 5400.f | 25.f | 15.f | 50.f | 48.f | 1.9f | 0.1f |
| UniversalArtifactSpawner.Veteran | 1 | 2000.f | 5400.f | 5400.f | 25.f | 15.f | 30.f | 59.f | 10.f | 1.f |
| UniversalArtifactSpawner.Master | 1 | 2000.f | 5400.f | 5400.f | 25.f | 15.f | 10.f | 65.f | 20.f | 5.f |
| LesserZoneMagneticShortDistance.Newbie | 1 | 800.f | 5400.f | 5400.f | 25.f | 15.f | 80.f | 20.f | 0.f | 0.f |
| LesserZoneMagneticShortDistance.Experienced | 1 | 800.f | 5400.f | 5400.f | 25.f | 15.f | 50.f | 48.f | 1.9f | 0.1f |
| LesserZoneMagneticShortDistance.Veteran | 1 | 800.f | 5400.f | 5400.f | 25.f | 15.f | 30.f | 59.f | 10.f | 1.f |
| LesserZoneMagneticShortDistance.Master | 1 | 800.f | 5400.f | 5400.f | 25.f | 15.f | 10.f | 65.f | 20.f | 5.f |

Paths are `<Spawner>.<Rank>.RarityChance.<Tier>`; e.g. `UniversalArtifactSpawner.Experienced.RarityChance.Rare=1.9f`. Every displayed distribution sums to 100. A possible future normalization example that preserves disabled ranks is Experienced: keep Common 50 and Uncommon 48, double Rare's relative weight from 1.9 to 3.8, retain Epic 0.1, then normalize all four weights against the new sum 101.9. There are different valid UX policies; none is selected or implemented here. Newbie Rare/Epic must remain disabled in an initial multiplier-based editor.

**Do not claim quest isolation:** the SpawnActor text contains 77 direct `SpawnedPrototypeSID=UniversalArtifactSpawner` references, all with `SpawnType=ESpawnType::ArtifactSpawner`: 73 in `WorldMap_WP`, one in `WorldMap_WP/E06_MQ01_LogicLevel_WP`, and three in test/demo maps. LesserZoneMagneticShortDistance has one WorldMap_WP reference. These are placements, not proof that all are active concurrently. Altering a shared prototype affects the quest-logic placement too. A release needs focused quest/gameplay validation, or a researched way to isolate ordinary placements.

Important rejected assumption: the four element-specific list spawners do **not** expose a proven usable rarity matrix. Complete baselines below; each row applies identically to Newbie, Experienced, Veteran and Master, so it covers all 16 rank sections without hiding outliers:

| Spawner | UseListOfArtifacts | List entries | Count | Radius | Min / MaxCooldown | Base / Bonus chance | Common / Uncommon / Rare / Epic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ElectroArtifactSpawner | true | 17 | 1 | 0.f | 3.0 / 15.0 | 40.0 / 5.0 | 0.f / 0.f / 0.f / 0.f |
| FireArtifactSpawner | true | 16 | 1 | 0.f | 3.0 / 15.0 | 40.0 / 5.0 | 0.f / 0.f / 0.f / 0.f |
| GravityArtifactSpawner | true | 17 | 1 | 0.f | 3.0 / 15.0 | 40.0 / 5.0 | 0.f / 0.f / 0.f / 0.f |
| ChemicalArtifactSpawner | true | 18 | 1 | 0.f | 3.0 / 15.0 | 40.0 / 5.0 | 0.f / 0.f / 0.f / 0.f |

The four list spawners have no direct SpawnedPrototypeSID references in this SpawnActor file; indirect engine use remains possible. Their explicit lists contain 17/16/17/18 artifact SIDs, but no per-entry weight field. Do not promise favored-artifact weighting or spawn-by-element rarity settings from this evidence. All four preserve `ExcludeQuestArtifacts` and `ExcludeArchiArtifacts`; leave exclusions and list membership untouched. `UseListOfArtifacts` runtime behavior needs further audit before an element editor is considered feasible.

Explicitly keep templates, Demo variants, `Quest*`, `SQ13_SoulArtifactSpawner` and `Weird*` spawners out of a new ordinary-spawn control. That alone cannot isolate the shared Universal quest placement described above.

## 4. Moving anomaly pursuit: Lightning Balls and Fire Ball

Anomaly damage and the Clicker special case are already configurable. Movement/pursuit properties below are new opportunities, not current settings: no production references to `HuntDistance`, `AnomalySpeedToMaxArtifacts`, `MaxArtifactsToUpSpeed` or `OnlyDetectSlotsArtifacts` were found.

Exactly five roots in AnomalyPrototypes.cfg declare `MaxArtifactsToUpSpeed`. Four ordinary variants are candidates; LightningBallPrologueAnomaly is an explicit story exception and must remain excluded. All selected fields are locally declared, even on the roots whose refkey points to LightningBallMediumAnomaly.

Full selected movement/pursuit baselines; paths are `<SID>.<column>`:

| SID (start line) | MovementSpeed | MovementLocationPriorityRadius | AnomalySpeedToMaxArtifacts | HuntDistance | OnlyDetectSlotsArtifacts | TargetLostDelay |
| --- | --- | --- | --- | --- | --- | --- |
| LightningBallMediumAnomaly (381) | 500.0 | 800.0 | 600.f | 300.0 | true | 3.0 |
| LightningBallSmallAnomaly (431) | 500.0 | 400.0 | 600.f | 300.0 | true | 3.0 |
| LightningBallBigAnomaly (481) | 500.0 | 400.0 | 600.f | 300.0 | true | 3.0 |
| LightningBallPrologueAnomaly (1019) | 800.0 | 800.0 | 800.f | 275.0 | false | 3.0 |
| FireBallAnomaly (1069) | 500.0 | 800.0 | 600.f | 300.0 | true | 3.0 |

Complete additional artifact-interaction baselines (same root-prefix rule):

| SID | MaxArtifactsToUpSpeed | CloseArtifactRadius | ArtifactEatingTime | ArtifactEatingRadius | EMIRadius | EMIDuration |
| --- | --- | --- | --- | --- | --- | --- |
| LightningBallMediumAnomaly | 5 | 100.0 | 4.0 | 100.0 | 1000.0 | 0.3 |
| LightningBallSmallAnomaly | 5 | 100.0 | 4.0 | 100.0 | 1000.0 | 0.3 |
| LightningBallBigAnomaly | 5 | 100.0 | 4.0 | 100.0 | 1000.0 | 0.3 |
| LightningBallPrologueAnomaly | 5 | 100.0 | 4.0 | 100.0 | 1000.0 | 0.3 |
| FireBallAnomaly | 5 | 100.0 | 4.0 | 100.0 | 0 | 0 |

`LightningBallSmallAnomaly`, `LightningBallBigAnomaly` and `LightningBallPrologueAnomaly` declare `refkey=LightningBallMediumAnomaly`; Medium and FireBall use Empty. Explicitly patch the four allowed ordinary roots rather than assuming one template patch covers them. All five use EAnomalyType::LightningBallAnomaly, but FireBall has AnomalyElementType::Fire, so selecting only by Type cannot distinguish it from electric variants.

Likely options are slower pursuit or a smaller attraction distance. Key names support that direction, but how carried/equipped artifacts determine a target remains gameplay-unverified. `OnlyDetectSlotsArtifacts=false` on the prologue variant must not be copied into ordinary ones without a separate requirement and test. Do not advertise an artifact-theft toggle from the name ArtifactEatingTime alone. Initial tuning should avoid zero values and leave artifact-eating mechanics untouched.

## Feasibility and scope

1. Start with a per-detector editor separating signal/reveal ranges; four ordinary models and a small explicit field list make this the clearest adjacent feature.
2. Add Weird Ball dynamic weight controls as an experimental special-artifact section after one focused in-game measurement.
3. Treat moving anomaly pursuit as a separate experiment with the prologue excluded.
4. Defer detailed rarity profiles until shared quest usage is accepted/tested; element-specific list/weight selection remains unproven.

All four proposed families can be represented by existing cfg patch files without adding a runtime UE4SS dependency. This establishes static data/patch feasibility, not that every named key changes the expected gameplay behavior. Every file needed for the core proposed controls is already in NEEDED_FILES; a future implementation limited to those files does not itself require a cache schema change. If it needs new data for placement isolation, re-evaluate extraction and schema rules then.

Not new and deliberately omitted from the proposal list: global artifact strength/radiation/price, no-detector visibility, no hopping/hop controls, global detector range, artifact spawn count/chance/respawn, extra armor slots/shielding, permanent Weird Flower, global consumable strength/duration, and thrown-bolt lifetime.
