# Core sweep (sixth data research, 2026-09-06): unused CoreVariables keys and never-read core files

Research only — no code. Prepared for the next feature round after 1.27.1.
Everything below was read from the extracted vanilla text configs under
`vanilla/Stalker2/Content/GameLite/GameData/` (`GameData/` from here on), never
from the `.cfg.bin` files. Every number is quoted verbatim (suffix `f` kept
where the file has it). Line numbers refer to the extracted 2026-08-27 files.
Four parallel research passes (CoreVariables first half, CoreVariables second
half, small core files, mid-size mechanics files) were consolidated here; every
value in the candidate tables was re-read from the raw files afterwards, and
the occurrence counts were re-counted.

## 0. Ground truth that changes earlier assumptions

- **Which CoreVariables struct is live on PC.** `GameData/CoreVariables.cfg`
  lines 1–3: `CurrentConfig : struct.begin / LaunchConfig = DefaultConfig /
  struct.end`. `DefaultConfig` runs lines 4–1407; `LowMemoryProfile` (1408–1411)
  and `LowMemoryProfileXSS` (1412–1427, Xbox Series S) are console profiles and
  dead weight on PC. Patch `DefaultConfig` only (the tool already does).
- **The tool writes exactly 48 CoreVariables keys** (`_corevars_patch` in
  `s2tweaker/tweaks.py`). Structs such as `LimpEffectSIDToThresholdMap`,
  `WoundHitAreasThresholds`, `StrikeGrenadeResistCoefs`,
  `PossessedWeaponFireIntervals`, `ReputationRepairCostModifiers`,
  `RadiationPresetValues` and `MutantLootParams` are untouched (the mutant-loot
  slider patches `ItemGeneratorPrototypes`, not CoreVariables).
- **`GameData/CoreVariablesCustom.cfg` exists and the tool does not know it.**
  One struct `CustomConfigOverride` (13 lines) re-declares five DefaultConfig
  keys with identical values: `bStartWithMenu = true`, `InventorySPDrainCoef =
  0.024`, `InventorySPOverweightDrainCoef = 0.05`, `InventoryPenaltyLessWeight =
  50.0`, `StaminaFallingDamageCoef = 0.5`, plus developer leftovers (`bGSCEnsure`,
  `bAllowDropOnClick = false`, `bShowBrokenGameDataWindows = true`, a build-machine
  `PathToBrokenGameData`, `TriggerDebugDrawDistance`). Both `CustomConfigOverride`
  and `CoreVariablesCustom` are present in the name table of
  `Stalker2-Win64-Shipping.exe`, so the engine knows the file. Whether it is
  applied *after* `DefaultConfig` cannot be decided from the data (identical
  values). Consequence: the two keys the tool already patches there
  (`InventoryPenaltyLessWeight`, `InventorySPOverweightDrainCoef`) may be
  silently reset if the override wins. **Cheap insurance for the build:** when
  those keys are patched, also emit `CoreVariablesCustom.cfg_patch_<Mod>.cfg`
  with `CustomConfigOverride : struct.begin {bpatch}` carrying the same values.
  Harmless if the override is never applied.
- **EXE name-table check (soft signal only).** Property names the C++ side reads
  appear as strings in `Stalker2-Win64-Shipping.exe`. 109 of the 120 candidate
  key names below are present. The 11 absent ones are: `InventorySPDrainCoef`,
  `EmissionNeutralityTimer`, `MoonLightMaxBrightness`, `SunLightMaxBrightness`,
  `StarsBrightness`, `CloudOpacity`, `LightSourceFadingDurationHoursOnDayNightChange`,
  `NorthOffsetAngle`, `QuickSaveOverwriteTime`, `SpeechEventCooldown`,
  `bAllowDropOnClick`. Absence proves nothing: `InventorySPOverweightDrainCoef`
  and `ALifeGridVisionRadius`, both patched by the tool today, and
  `AutoSaveSlotsCount` are absent as well (blueprint-side or differently encoded).
  Presence is a plus, absence is a "test in game" flag, nothing more.
- **Earlier claim corrected:** `DestructibleObjectPrototypes.cfg` *does* have an
  HP key (`DamageDestroyThreshold`, 441 occurrences) — but 348 of them are `0.0`.

## 1. CoreVariables.cfg — new candidates (file already cached, no schema bump)

All paths are relative to `DefaultConfig`. "Array" means the entry must be
re-emitted completely (discriminator + value), as the tool already does for
`StaminaRegenStateCoefs`.

### 1.1 Player and survival

| key | line | vanilla | meaning / evidence | tweak | risk |
|---|---|---|---|---|---|
| `LimpEffectSIDToThresholdMap.[0].Threshold` / `.[1].Threshold` (array; `EffectSID = WeakLimp` / `MediumLimp`) | 207 / 211 | `25.0` / `65.0` | Landing severity at which the player starts limping. `EffectPrototypes.cfg:30619/30653`: both effects say `Text = Applies limp effect when player lands`, `Type = EEffectType::Limp`, `Duration = 2.5` / `4.5` | factor 1×–8× plus a "never limp" switch (very high thresholds) | none known |
| `InventorySPDrainCoef` | 181 | `0.024` | Stamina drain scaled by carried weight below the overweight line; sibling of the used `InventorySPOverweightDrainCoef` (`docs/SPEC.md` §1.3) | factor 0×–2× | duplicated in `CoreVariablesCustom.cfg` → patch both files |
| `StaminaFallingDamageCoef` | 202 | `0.5` | Stamina cost of a landing (not HP; fall HP damage is `Protection.Fall`, SPEC §1.8) | factor 0×–2× | duplicated in `CoreVariablesCustom.cfg` → patch both |
| `VitalBaseBleedingValue` | 197 | `10.0` | Bleeding points per bleeding event against `MaxBleeding = 100` (`ObjPrototypes.cfg:662`); `BleedingMechanics` phases at 0.1 / 50 / 75 | factor 0.25×–3× | overlaps the existing bleeding-stop slider only in feel |
| `BleedingChanceNonPenetrationMod` / `BleedingPointsNonPenetrationMod` | 476 / 477 | `1.0` / `1.0` | Bleeding chance / amount from hits that do not penetrate armour (1 occurrence each) | factor 0×–3× | arithmetic unproven, but vanilla 1.0 makes a factor safe |
| `StrikeGrenadeResistCoefs.[0..4].GrenadeDamageResist` (array; `ProtectionStrike = 0.f … 4.f`) | 284, 288, 292, 296, 300 | `0.0f`, `0.1f`, `0.2f`, `0.4f`, `0.6f` | Fraction of grenade/explosion damage absorbed per armour Strike level 0–4 | factor, cap 1.0 (0 = grenades ignore armour) | none known |
| `StrikeAnomalyArmorDifferenceCoef` | 585 | `1.0` | Armour-vs-attacker weighting for anomaly Strike damage; sibling of `ArmorDifferenceCoef` 2 / `ExplosionArmorDifferenceCoef` 0.5 / `PlayerMeleeArmorDifferenceCoef` 0.6 | factor 0×–3×, experimental like its siblings | formula unknown |
| `ArmorDurabilityParamsCoef` / `HelmetDurabilityParamsCoef` | 1179 / 1180 | `0.7f` / `0.7f` | Only armour-durability scalars in GameData (weapons use `WeaponDurabilityCurve`). Direction unknown: "30 % protection left at 0 durability" or the opposite (`docs/SPEC.md` line 190 says the same) | absolute 0.0–1.0, experimental | needs one in-game A/B |
| `ClimbUpSpeed`, `ClimbDownSpeed`, `ClimbEnterUpSpeed`, `ClimbEnterDownSpeed`, `ClimbExitUpSpeed` | 239–243 | all `1.0f` | Ladder animation play-rates; `ClimbFastAscendingSpeedScale = 1.2f`, `ClimbMediumAscendingSpeedScale = 1.1f` show the game scales them. `Player.MovementParams.ClimbSpeedCoef = 0.6` (`ObjPrototypes.cfg:708`) is a second lever | factor 0.5×–3× on the five | animation feel only |
| `IdleSwayInterpolationSpeed` | 38 | `2.f` | How fast the weapon's idle sway follows the aim | factor 0.25×–3× | cosmetic |
| `FlashlightDialogIntensityPercent` (+ `…LerpTime`) | 1104 / 1105 | `0.525` / `1.5` | Flashlight dims to 52.5 % during dialogue | absolute 0–1 (1 = no dimming) | cosmetic |
| `UseMutantLootWithoutWidget` | 384 | `true` | `true` = harvest animation without the loot window (`AnimCollection_Player_MutantLoot_alt`), `false` = widget flow; both collections ship (lines 382–383) | switch | none known |
| `MarkerShowingDistance` / `MarkerRevealingDistance` / `MarkerExploringDistance` | 499 / 501 / 500 | `30000.0` / `3000.0` / `2000.0` | HUD marker show / reveal / explored distances (300 m / 30 m / 20 m). Names only — no cross-reference. Distinct from the per-marker `MarkerPrototypes` distances the 1.26.0 map slider scales | factor 0.25×–4× | meaning by name only |
| Interaction ranges: `WideTraceInteractionDistance`, `AutoInteractionDistance`, `MutantLootContainerInteractRange`, `DragDeadBodyInteractRange`; `MutantLootInteractHeightMin/Max`; `DeadBodyPickUpTime` | 343, 349, 351, 352; 462, 463; 354 | `500.0`, `70.0`, `120.0`, `130.0`; `25.f`, `90.f`; `2.0` | Same `// / Player consts` block as the used `MaxInteractionDistance` / `ItemContainerInteractRange` | fold into `interaction_range_factor` and the corpse-drag slider | none known |

### 1.2 Radiation presets (`RadiationPresetValues`, lines 617–672, array of 7)

| idx | `Preset` | `RadioactivityValue` | `RadiationPerSecondValue` | `GeigerRadiationIntensity` | `PostProcessRadiationIntensity` | world volumes |
|---|---|---|---|---|---|---|
| 0 | Light | `15.f` | `1.0f` | `0.4f` | `0.5f` | 639 |
| 1 | Medium | `45.f` | `3.f` | `0.6f` | `0.55f` | 1486 |
| 2 | Strong | `75.f` | `6.f` | `0.8f` | `0.75f` | 623 |
| 3 | Deadly | `99.f` | `33.f` | `0.9f` | `0.9f` | 91 — **never touch** |
| 4 | RadBlock | `100.f` | `50.f` | `1.0f` | `1.0f` | 239 — **never touch** |
| 5 | Custom | `1.f` | `1.f` | `0.1f` | `0.1f` | 1 |
| 6 | Topaz | `15.f` | `1.f` | `0.2f` | `0.45f` | 2 |

Volumes counted from `Radioactivity = ERadiationPreset::<X>` in
`GameData/SpawnActorPrototypes.cfg` (3081 total). Deadly and RadBlock carry
`EffectPrototypeSIDs.[0] = RadBlockFieldDamage` = `EffectPrototypes.cfg:78481`:
`Type = EEffectType::Damage`, `ValueMin/Max = 9000.0`, `TimePerChargeMin/Max =
2.7` — the map-boundary kill zone. Player `MaxRadiation = 100`
(`ObjPrototypes.cfg:59`), so Strong fills the bar in ~17 s.
Knobs: dose per second (0/1/2/6 only; overlaps the difficulty radiation slider),
screen filter intensity (visual), Geiger loudness (audio). `RadioactivityValue`
stays untouched (unknown whether it feeds damage). Array → emit whole entries.

### 1.3 NPCs, wounded state, music

| key | line | vanilla | meaning / evidence | tweak | risk |
|---|---|---|---|---|---|
| `ChanceToGetHealOverTimeWhenWounded` | 71 | `70` | Dev comment on the line: 0–100 chance a downed NPC heals over time instead of bleeding out (`HealOverTime_Wounded` +10 vs `DamageOverTime_Wounded` −1, `EffectPrototypes.cfg:14823/14858`) | absolute 0–100 | none known |
| `CooldownOnFallingWounded` | 73 | `300` (`// 5 mins`) | Seconds before the same NPC can go down again | absolute 30–1800 | very low = NPCs drop repeatedly |
| `WoundedStateHealthRegen` | 69 | `5.f` | HP/s regenerated while wounded | factor 0×–4× | none |
| `HpThresholdToHealWound` | 72 | `35` | Either "healable below 35 HP" or "wakes up with 35 HP" — direction unproven | absolute 5–95, experimental | — |
| `UnkillableNPCWoundedStateResurrectionTime` | 74 | `60` | Seconds until a plot-protected NPC gets up again | absolute 10–300 | **quest risk** at high values — leave out or cap |
| `WoundHitAreasThresholds.Head/Torso/Legs/Default` | 148–151 | `0` / `7` / `7` / `5` | Damage a hit must reach per body area to count as a wound (`BoneToHitAreaMap` lines 75–93); whether it gates the down-state or the bleeding wound is unproven | skip until tested | — |
| `PossessedWeaponFireIntervals.<Ammo>.FireInterval` (10 sub-structs `A012`, `AVOG`, `AGA`, `APG7V`, `AHEDP`, `A762Sniper`, `A762NATO`, `A918`, `A919`, `A045`) | 112–143 | `1`, `4`, `2`, `4`, `4`, `1`, `1`, `0.5`, `0.5`, `0.5` | Seconds between shots of a weapon a Burer levitates and fires (`AbilityPrototypes.cfg:2917` `Burer_WeaponRiseAndShoot` → `PossessedWeaponParams`) | factor 0.5×–4× | none |
| `MusicManagerCombatScoreThreshold` | 849 | `20.f` | Combat music starts when nearby enemies' `MusicManagerCombatScore` sum reaches this. `ObjPrototypes.cfg`: `10` ×1628, `20.f` ×24, `7.f` ×5, `3.f` ×1, `0.f` ×1 → one standard NPC does not trigger it, two do | absolute 5–100 | music only |
| `MusicManagerCombatEnemyAttackActionLifetimeSeconds` | 850 | `25.f` | How long an attack keeps counting → how long combat music lingers | absolute 5–60 | music only |
| `RegenerateItemsOnRankUpdateRadius` / `…Timer` | 1395 / 1396 | `40000.f` / `10.f` | On a player rank-up, item generators within 400 m are re-rolled after 10 s (`ItemGeneratorPrototypes.cfg` gates loot on `PlayerRank`) | factor 0.25×–5× | none known |
| `InfotopicRefreshHours` | 497 | `24` | Game hours before NPC rumours refresh | absolute 1–72 | low |
| `ReputationRepairCostModifiers.[0..3].Modifier` (array; `RelationLevel = Enemy / Disaffection / Neutral / Friend`) | 262, 266, 270, 274 | `2.0`, `1.5`, `1.0`, `0.75` | Repair price by faction relation, next to the used `BaseRepairCostModifier` | switch "reputation does not affect repair prices" (all 1.0) or factor on the spread | none |
| `ArtifactStrafeMinDistance` | 464 | `600.0` | Belongs to the `Strafe = true` artifacts (146 in `ItemPrototypes.cfg`, 8 false) that hop away; whether 600 is the keep-away or the trigger distance is unproven | absolute 0–1200, experimental | — |

### 1.4 Corpse system, second half (lines 361–380)

The tool scales five corpse *times* and one count; these decide whether the
times are ever reached (`docs`: "corpses still vanish" reports):

| key | line | vanilla | note |
|---|---|---|---|
| `CorpseOfflineSquaredDistance` | 361 | `100000000.0` | 100 m, **squared cm** (2× range = 4× value) |
| `CorpseOfflineTimeConditionSquaredDistance` | 363 | `25000000.0` | 50 m squared |
| `CorpseOfflineCountConditionSquaredDistance` | 365 | `9000000.0` | 30 m squared |
| `CorpseDespawnToOfflineTimeCoef` | 374 | `0.5` | (LowMemoryProfile copy 0.1 is dead on PC) |
| `CorpseOffscreenLifetime` | 376 | `3.0` | seconds a corpse stays online after leaving view (dev comment) |
| `DistanceToDestroyCorpsesIfOverpopulated` | 379 | `30000` | 300 m |
| `AlifeCorpsesHardcap` | 380 | `1500` | global cap |

Never touch `CorpseRagdollQuestProtectionCheckTime/EnableTime` (377/378).

### 1.5 Not recommended (traps and unknowns) — recorded so nobody researches them again

`VitalMaxPsyPoints` 100 / `VitalMaxPoppyFieldSleepiness` 1000 (phase thresholds
are absolute 30/60/85 and 400, raising the max does not delay effects);
`StartHour` etc. (duplicated in `SingletonConstants.cfg`, new game only);
`EmissionNeutralityTimer` 120, `bStartWithLoadedWeapon`, `HPThresholdToKill`
0.1, `MaxRecoilPitchDifference` 3.5, `BleedingTimer` 0.05 /
`BleedingChanceStackMaxSize` 99, `ObjRadiationSphereMin/MaxRadius`,
`SignalStrength.[0..2]`, `PhysicalMaterialFrictionCoefficients` (meanings
unknown); `ActorCrouchHeight` 115 / `BaseActorHeight` 180 (collision);
`SimulatePhysicsDistance` 6200, `ALifeGridUpdateDelay` 1.0,
`OnlineDirectorModelsPerTick` 20 (performance); `LairSearchingRadius` 130000
(quest knock-on); `FaustCloneCountCap` 20 (boss); `bALifeTick`,
`WorldMapActualWidth/Height`, `bEnableWaterElement` (never); `Unfocusable*`
(quest protection); `Item Info` block (tooltip bars only);
`DegenSuppressionDelayTimeSeconds` (overridden 1659× per prototype);
`bResetArtifactLuckOnPickup` (only a nerf); `WeightAzimuthArrayPsyPhantom`
(distribution, not a scalar); `bEnableDisassembleUI` / `bEnableHideInformationUI`
(dead flags).

## 2. Never-read core files

Each one is a new `NEEDED_FILES` entry → bump `CACHE_SCHEMA` once per release.
Patch-file names follow the confirmed convention (prototype files:
`<Base>/<Base>_patch_<Mod>.cfg`; unbinarized non-prototype files:
`<Base>.cfg_patch_<Mod>.cfg`).

### 2.1 `GameData/ObjOnHitParamsPrototypes.cfg` (181 lines, bin 3.5 KB) — damage screen effects

Only `PlayerOnHitParams` matters (`OnHitParamsSID = PlayerOnHitParams` once in
`ObjPrototypes.cfg`, `Empty` 1658×). It defines everything itself (`{refkey=[0]}`,
base empty). `DirectionalDamageEffects[0..7][0]`: eight identical entries
(`MinDamage 0`, `MaxDamage 75`, `MinEffectValueModifier 0.2`,
`MaxEffectValueModifier 1`) — the red directional hit flash.
`DamageTypeEffects`:

| idx | DamageType | EffectSID | Min/MaxDamage | Min/MaxEffectValueModifier | note |
|---|---|---|---|---|---|
| [0] | Shock | ElectroIntensityPostProcess | 10 / 50 | 0.4 / 1 | only non-zero MinDamage |
| [1] | ChemicalBurn | ChemicalDamagePostProcess | 0.001 / 50 | 0.5 / 1 | `bIgnoreLowDamage = true` |
| [2] | Burn | BurnDamagePostProcess | 0 / 50 | 0.1 / 1.0 | |
| [3] | SteamBurn | SteamDamagePostProcess | 0 / 50 | 0.1 / 1.0 | |
| [4] | Darkness | DarknessDamageIntensity/RadiusPostProcess | 0 / 50 | 0.4 / 1.0 and 0.25 / 0.75 | damage type occurs nowhere else |
| [5] | GameplayGas | GameplayGasPostProcess | 0 / 50 | 0.1 / 1.0 | occurs nowhere else |
| [6] | Quicksilver | QuicksilverDamageIntensityPostProcess | 0 / 10 | 0.25 / 1 | occurs nowhere else |

All effects are `EEffectType::PostProcessing` overlays. Tweak: one slider
"damage screen effects" 0–100 % on the modifiers (entries re-emitted whole);
optionally a second one for the directional flash. Risk: at 0 % a chemical
field gives no visual warning. No psy/radiation/bleeding entries here.

### 2.2 `GameData/BarbedWirePrototypes.cfg` (47 lines, bin 1.3 KB)

`LimitingBarbedWire` (line 16) and `OverlappableBarbedWire` (32) both
`{refkey=[0]}` and both redeclare every value: `Damage = 10.0`, `DamageDelay =
1.0`, `BleedingChance = 0.1`, `BleedingValue = 25.0`, `ArmorDamage = 5.0`,
`ArmorPiercing = 2.5`, `MovementSpeedDegradeDelay = 0.5`; only `bOverlappable`
differs. Which fences use which prototype is placed in levels, not in cfgs →
patch both. Tweak: one factor 0×–3× on Damage, BleedingValue, ArmorDamage and
BleedingChance (cap 1.0). Zero risk, low value.

### 2.3 `GameData/QuickSaveVariables.cfg` (3 lines, unbinarized)

`DefaultConfig.QuickSaveOverwriteTime = 300` with the dev comment "seconds during
which we continue to rewrite the same quick save slot instead of creating a new
one". Same struct/patch convention as the already-patched `AutoSaveVariables.cfg`.
Tweak: absolute 0–3600 s (0 = every quicksave gets its own slot; save-count limit
lives in `SaveLoadVariables`).

### 2.4 `GameData/AIPrototypes/FlairSensorPrototypes.cfg` (173 lines, bin 4 KB) — mutant sense of smell

Ten structs; children `{refkey=DefaultFlairSensor}` but redeclare every key →
patch each child. Reference counts from `FlairSensorPrototypeSID` in
`ObjPrototypes.cfg` (1659 total):

| SID | line | IsActive | SensingRadius | DetectionSpeed | Front radius / angle / speed | MaxFlairPoints | LosePointsPerSecond | objects |
|---|---|---|---|---|---|---|---|---|
| DefaultFlairSensor | 1 | false | 0.f | 0.f | — | 0.f | 0.f | 1566 |
| BlindDogFlairSensor | 16 | true | 4000.f | 110.f | 4000.f / 70.f / 400.f | 1000.f | 200.f | 38 (all common mutants) |
| BossFlairSensor | 34 | false | 8200.f | 1000.f | — | 1000.f | 5.f | 6 |
| PsyNPCFlairSensor | 49 | true | 7500.f | 999999.f | — | 1000.f | 5.f | 0 (dead data) |
| PoltergeistFlairSensor | 64 | true | 1000.f | 110.f | — | 1000.f | 200.f | 5 |
| DugaSniperFlairSensor | 79 | false | 7500.f | 2000.f | — | 1000.f | 5.f | 1 |
| GuardNPCFlairSensor | 94 | false | 7500.f | 2000.f | — | 1000.f | 5.f | 40 |
| PoltergeistFlairSensorYanivToxicRozliv | 109 | true | 200.f | 110.f | — | 1000.f | 200.f | 1 (quest, skip) |
| ChimeraFlairSensor | 124 | true | 7000.f | 110.f | 3500.f / 70.f / 400.f | 1000.f | 200.f | 1 |
| FleshFlairSensor | 157 | true | 2000.f | 110.f | 2000.f / 70.f / 400.f | 1000.f | 200.f | 1 |

Player-facing proof: the Weird Flower artifact (`ItemPrototypes.cfg:28141`)
grants `FlairDistanceModifierEffect` = `60.0%` "Modifies flair emission"
(`EffectPrototypes.cfg:40258`); the weather-stealth slider already scales
`AIGlobals.FlairCoef` (1.0/1.0/0.7/0.65/0.9/0.45). Tweak: "Mutant sense of
smell" ×0.25–2 on `SensingRadius`, `FrontSensingRadius`, `DetectionSpeed`,
`FrontDetectionSpeed` of the active sensors (skip PsyNPC and the Yaniv quest
variant), plus a switch that sets `IsActive = false` on the six active ones.
Risk: scripted mutant ambushes at very low values.
`MovementSensorPrototypes.cfg` (Poltergeists only, 6 objects) and
`VisionTickPrototypes.cfg` / `ConstraintPrototypes.cfg` (per-tick budgets) are
not worth a slider.

### 2.5 `GameData/EnemyEvaluatorPrototypes.cfg` (16 lines) and `GameData/CoverEvaluatorPrototypes.cfg` (569 lines)

EnemyEvaluator: one struct `[0]` (`SID = empty`): `DistanceCoeff 0.7`,
`NoAddedDamageCoeff 0.3`, `NotPlayerCoeff 0.15`, `NPCSelectedAsTargetByOtherCoeff
0.4`, `PlayerSelectedAsTargetByOtherCoeff 0.4`, `CloseCombatMaxPenaltyDistance
2000.0`, `RangedCombatMaxPenaltyDistance 15000.0`,
`DamageAccumulationDurationSeconds 7.0`, `DamageAccumulationMinValue 10.0`,
`DamageAccumulationMaxValue 50.0`, `ChangeEnemyCooldown 3.0`,
`NPCSelectedAsEnemyValue 0.01`, `PlayerSelectedAsEnemyValue 0.01`,
`RangeSearchPathToEnemies 6000.f`. Patch shape `[0] : struct.begin {bpatch}` at
file top level (same as the `ItemPrototypes` weightless-equipment patch).
Candidates: `NotPlayerCoeff` ("how strongly NPCs focus the player"; the sign of
the term is inferred from the neighbouring `…MaxPenaltyDistance` keys →
experimental), `ChangeEnemyCooldown`, `DamageAccumulationDurationSeconds`.

CoverEvaluator: `DefaultCoverEvaluator` is used by 1605 NPC objects
(`BossCoverEvaluator` 3, `Strelok/Scar/KorshunovCoverEvaluator` 1 each — skip
all four). Every child redeclares all 47 keys. Legible knobs:
`DefaultCoverSettings.MinDistanceToEnemy = 800.f`, `MaxDistanceToEnemy = 7000.f`
(lines 41–42), `MaxPathLength = 2000` (line 4). Formula unknown → experimental,
single conservative slider at most.

### 2.6 `GameData/NPCNeedsPresetPrototypes.cfg` (3861 lines, bin 78 KB) — camp life and A-Life expansion

26 presets, wired by `NeedsPresetSID` in `ObjPrototypes.cfg` (1659 refs; the
referenced `CorpusNeedsPreset_Guard` is never defined — vanilla bug). Every
preset writes its own `Needs` numbers despite refkeys → patch all.
`HumanGenericNeedsPreset` (line 132) reference rates (`IncreaseRateMin/Max`,
`Radius`, `MaxCount`): Idle 3/4, Rest 2/4, Sleep 4/6, Smoke 6/8, Drink 2/4,
Eat 3/4, Guitar 4/6 (radius 5500, MaxCount 1), Work 2/4, PDA 2/4, Detector 2/4,
WeaponCleaning 5/8, Patrolling 6/8 (MaxCount 12), Monolog 3/6, Dialog 5/8,
Emission 100/100 (pinned), Anecdote 3/6, RunOnTalking 3/6. Presets deviate
(Duty flattens to 1/2, Neutrals Guitar 5/15, Bandits Work 0.5/2).
`GoalNeeds` `AI.Need.Expansion` (`ExpansionResolverFactory`, squads 2–4):
`InitialNeedValue 65.0`, `MinIncreasePerMinute 6.0`, `MaxIncreasePerMinute 10.0`,
threshold 100 on 14 human presets; Zombie `1.0 / 3.0`; MutantGeneric `7.0 /
11.0` (Militaries, Noon, Spark, Corpus, MutantNoExpansion never expand).
`AI.Need.ReuniteWithLair` is inert (0/0). Tweaks: "A-Life squad expansion"
factor 0.25×–3× on the 16 Expansion pairs (density knob; CPU); "camp life"
factor on Guitar/Anecdote/Dialog/Smoke/Sleep/Eat across 26 presets (atmosphere,
high patch volume).

### 2.7 `GameData/ALifePrototypes/ALifePolicyPrototypes.cfg` (14 lines) and `ALifePopulationManagerFactionPrototypes.cfg` (616 lines)

Policy `Default`: `TriggerExtinction 2000` / `StopExtinction 1950` (global agent
cap — **never touch**), `TriggerOfflineALifeCorpseDecomposition 100` /
`Stop… 80`, `MaxCorpsePerRadius 30`, `CorpseRadius 10000.f`, `FarLairDistance
100000.f`, `SeenLongAgoByPlayerSec 900.f`, `FullWipeRefillCooldown 360.f`,
`PartialWipeRefillCooldown 120.f`, `MinRefillDistance 20000`, `MaxRefillDistance
25000`. None of the keys occurs elsewhere (readings by name; the A-Life mods in
`docs/ALIFE_SPAWN_RESEARCH.md` §6 change the refill pair). Tweaks: refill
cooldowns and refill distance band next to the lair respawn slider; corpse
budget.
Faction preset: `ALifeLairExpansionTime 50.f`, `ALifeLairExpansionRadius
500000.f`, `ALifeStartSimulation 48.0f`; 29 factions with
`ALifeLairExpansionBattleChance = 50` each and contiguous
Aggressive/Normal/Defensive lair bands (Diggers and Spark overlap at 3 — vanilla
inconsistency). Offline simulation, low visibility; the bands must not be
scaled.

### 2.8 `GameData/SingletonConstants.cfg` (146 lines, unbinarized) — sky, night, clock

`TimeManager`: `Latitude 51.23f`, `Longitude 30.3f`, `TimeZone 2.f`,
`NorthOffsetAngle 90.f` (**never touch** — sun path),
`LightSourceFadingDurationHoursOnDayNightChange 2.f`, `SunLightMaxBrightness
3.14f`, `MoonLightMaxBrightness 1.046f`, `StarsBrightness 0.1f`, `CloudSpeed
1.f`, `CloudOpacity 0.7f`, `StartYear 2021`, `StartMonth 8`, `StartDay 1`,
`StartHour 9`, `StartMinute 0`, `StartSecond 0` (the Start* keys are duplicated
in `CoreVariables.cfg` lines 18–23). The six light/cloud keys are the only
definition in GameData but absent from the EXE name table → probably read by a
blueprint; the file has never been patched by the tool (would be
`SingletonConstants.cfg_patch_<Mod>.cfg` next to it; a directory of the same
name exists, no collision). Experimental "darker nights / brighter moon" knobs,
in-game test mandatory. `SpeechManager` cooldowns (5 × `CooldownSec = 25.f`) and
`SingletonConstants/BarkManager.cfg` are audio; half of BarkManager's keys sit
outside any struct and cannot be addressed by `emit.py`.

### 2.9 `GameData/NPCPrototypes.cfg` (94 067 lines, bin 1.8 MB) — trader-side numbers

24 keys; besides dialog chains and technician `Upgrades` lists the only numeric
families are `Money` (`0` ×1331, `20000` ×16, `10000` ×1, `10` ×4, `5` ×1),
`BuyCoefficient = 0.8` / `SellCoefficient = 2.0` on exactly 9 NPCs (`Koldun`
10755, `Eger` 15166, `Guron` 15274, `Sinak` 19937, `sulc` 33713, `drabadan`
33741, `KoldunM` 91129, `supack_trader_selma_0` 93531,
`trader_assistent_medulin_0` 93891) and `ThreshHoldItemCondition` (`0.5` ×1332,
`0.8` ×21, meaning unknown). The existing price sliders scale
`BuyModifier`/`SellModifier` in `TradePrototypes.cfg` (73 each) and never touch
these nine; the wallet slider scales `TradePrototypes` `Money`. Precedence
unknown → fold the nine coefficients and the NPC-level `Money` into the existing
sliders (harmless if the engine ignores them, closes a gap if it does not).

### 2.10 `GameData/DestructibleObjectPrototypes.cfg` (20 565 lines, bin 536 KB)

`DamageDestroyThreshold` (441 phases): `0.0` ×348, `40.0` ×18, `10.0` ×17, `1.0`
×12, `25.0` ×10, `30.0` ×9, `60.0` ×6, `3.0` ×6, `100.0` ×6, `50.0` ×3, `5.0` ×3,
`20.0` ×3. Every prototype defines its own phase block (no inheritance). A global
factor moves only 93 values; the honest tweak is "explosive containers pop
sooner/later" on the 22 `Exp_*` prototypes (gas cylinders 20–40, canister 30,
barrel 50; `[37] Exp_MetallGasBalon_01` line 1965 = `40.0` with
`ExplosionPrototypeSID = ExplosionGasCylinder`). `MassMultiplier` (0.3–60,
median 5) is physics feel only.

### 2.11 `GameData/PhysicsInteractionPrototypes.cfg` (2850 lines) and `WeatherChainPrototypes.cfg` (318 lines)

PhysicsInteraction is audio mapping except `PlayerPushImpulse` (88 entries, 47
distinct, `LabJar 20.0` … `Ammo_Plastic 27000.0`, `DeadBodyHuman 3500.0`) —
"how hard you shove props and bodies"; fun, physics-stability risk.
WeatherChain: 18 chains, all 20 real `WeatherChainWeight = 100` (a factor
changes no probability) and all 22 `WeatherTransitionTimeMultiplier = 1` —
usable as "weather changes faster/slower" but overlaps the duration slider and
the exact quantity is unverified.

### 2.12 `GameData/PackOfItemsGroupPrototypes.cfg` (5178 lines)

Hand-placed world loot piles only (`PackOfItemsPrototypeSID` 4781× in
`SpawnActorPrototypes.cfg`, 0× in item generators, stashes, NPCs, trade). 47
groups × 4 ranks, 979 `Weight` entries (`1` ×390, `0` ×218 rank locks, `2` ×113,
`20` ×50, `30` ×44 …). `ArtifactUncommon` (line 5089): all 20 weights `0` yet 9
world references — either an engine fallback or nine empty caches. A switch that
gives those 20 a weight is a genuine but experimental tweak; scaling the rank
locks is not recommended.

### 2.13 Dead ends (do not research again)

`GlobalVariablePrototypes.cfg` (469 entries: 391 Bool / 64 Int / 14 String;
468 are quest/boss/debug state written by `QuestNodePrototypes.cfg`; the one
feature gate `MutantLootFeatureEnabled` is set by quest `SmallZone_L`);
`ImpactPhysicalMaterialPrototypes.cfg` `MaterialCoefficient` (256 values,
contradictory readings: invulnerable materials are 0.0 but SmallCaliber beats
BigCaliber through MetalSolid 0.78 vs 0.46 — unknown, do not ship);
`Achievements.cfg` (integrity); `MovementFXPrototypes.cfg` (footstep VFX);
`RestrictorsPrototypes.cfg` (1260 nav boxes); `HappyHoursPrototypes.cfg` (18
clock times, no consumer anywhere); `DailySchedulePrototypes.cfg` (HH:MM
strings + need enums); `TeleportPrototypes.cfg`, `TeleportGroupPrototypes.cfg`,
`DoorPrototypes.cfg`, `CorpsePrototypes.cfg` (set-dressing corpses),
`SingletonConstants/BarkManager.cfg`, `DialogLight.cfg`, `InputManager`,
`ReflectionManager`, `CameraManagerConstants.cfg`, `WaterVariables.cfg`,
`GameLoadingVariables.cfg` (assets, budgets, materials).

## 3. WARNINGS (must never be patched)

- `RadiationPresetValues.[3]` Deadly and `.[4]` RadBlock and their
  `EffectPrototypeSIDs` (map-boundary kill zones).
- `CoreVariables` `bALifeTick`, `WorldMapActualWidth/Height`, `bEnableWaterElement`,
  `BaseActorHeight`, `ActorCrouchHeight`, `CorpseRagdollQuestProtection*`,
  `Unfocusable*`, `FaustCloneCountCap`, `MaxTimeSpentOnLoading`.
- `ALifePolicyPrototypes` `TriggerExtinction` / `StopExtinction`.
- `SingletonConstants` `Latitude`, `Longitude`, `TimeZone`, `NorthOffsetAngle`,
  `StartYear/Month/Day`; `InputManager`, `ReflectionManager`.
- `CoreVariablesCustom` debug keys (`bGSCEnsure`, `bShowBrokenGameDataWindows`,
  `PathToBrokenGameData`, `TriggerDebugDrawDistance`).
- Boss evaluators (`BossCoverEvaluator`, `Strelok/Scar/KorshunovCoverEvaluator`),
  `BossFlairSensor`, `PsyNPCFlairSensor`, `PoltergeistFlairSensorYanivToxicRozliv`.
- All of `GlobalVariablePrototypes.cfg` (quest state), `Achievements.cfg`,
  `DoorPrototypes.cfg` locks, quest teleports, `DailySchedule` need lists,
  PackOfItems rank locks.

## 4. Build notes for the implementation round

- Arrays (`LimpEffectSIDToThresholdMap`, `StrikeGrenadeResistCoefs`,
  `ReputationRepairCostModifiers`, `RadiationPresetValues`, OnHit entries) →
  emit complete entries; `[N]`-named top-level structs (EnemyEvaluator `[0]`,
  Destructibles `[37]`…) → `[N] : struct.begin {bpatch}`.
- Children that redeclare everything (flair sensors, cover evaluators, barbed
  wire, needs presets) → patch each child, never only the base.
- New `NEEDED_FILES` (one `CACHE_SCHEMA` bump): ObjOnHitParams, BarbedWire,
  QuickSaveVariables (text), FlairSensor, EnemyEvaluator, CoverEvaluator,
  NPCNeedsPreset, ALifePolicy, ALifePopulationManagerFaction, SingletonConstants
  (text), CoreVariablesCustom (text), NPCPrototypes (1.8 MB — parse lazily like
  ItemGenerator), DestructibleObject, PhysicsInteraction, WeatherChain,
  PackOfItemsGroup.
- Two verification tasks, not tweaks: (a) CoreVariablesCustom precedence —
  ship the belt-and-braces patch; (b) NPC-level trader coefficients — fold into
  the existing price/wallet sliders.
- Everything remains un-play-tested; tooltips must say so, and the
  "experimental" ones (armour durability coefs, NotPlayerCoeff, cover
  distances, sky brightness, ArtifactStrafe, HpThresholdToHealWound) need the
  explicit label.
