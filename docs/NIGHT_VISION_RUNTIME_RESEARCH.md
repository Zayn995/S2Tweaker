# NPC night vision: asset and runtime research

Research against installed 2.0.5 data. This document identifies implementation
candidates; it does not claim a working night-only distance cap or a gameplay
test. Existing light-perception controls are documented in
[STEALTH_CONTROLS.md](STEALTH_CONTROLS.md).

Current status: no night-only distance slider has been implemented. The bounded
editor investigation did not spawn an NPC or apply a vision-distance effect.
No exposed getter for the effective scanner distance, sight-only acquisition
event, or perception-memory reset was established. `fg.VisionScanner.DrawDebug`
is documented by its native description as drawing scanner traces; it is not a
verified range readout. The native `CustomConsoleManagerRK:XSpawnObjBySID`
function exists, but its argument signature is absent from the exposed Python
surface and text export. A successful effect call or a focused enemy alone
would not establish distance semantics. Implementation remains gated on a
controlled measurement of the actual native sight boundary.

## Sources and scope

Paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`.

| File | Lines | Top-level structs | Relevant data |
| --- | ---: | ---: | --- |
| `AIPrototypes/VisionScannerPrototypes.cfg` | 345 | 7 | Vision distances, angles, daytime curve, luminance penalties |
| `AIGlobals.cfg` | 779 | 2 | AI luminance and seven time-of-day intervals |
| `ObjPrototypes.cfg` | 1,318,780 | 1,660 | Object-to-scanner assignments |
| `EffectPrototypes.cfg` | 85,869 | 2,426 | Native vision-distance modifier effect |

`EffectPrototypes.cfg`, at `VisionDistanceModifierEffect` (line 40,360), supplies
an additional native effect candidate. Cached Zone Kit Python reflection data
and editor binary diagnostic names establish that a custom vision scanner exists;
neither provides a callable setter for that scanner's distance.

## Exact scanner fields and baseline values

The patchable paths are `<scanner>.CentralVisionDistance`,
`<scanner>.PeripheralVisionDistance`,
`<scanner>.HorizontalVisionHalvedAngleDegrees`,
`<scanner>.VerticalVisionHalvedAngleDegrees`, and
`<scanner>.DaytimeDistanceAndAnglesVisibilityPercentModificationCurve`.

| Scanner | `refkey` | Central distance | Peripheral distance | Horizontal half-angle | Vertical half-angle | Existing range-control scope |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `DefaultNPC` | None | 8000 | 2500 | 85 | 85 | Included |
| `NoVision` | None | 0 | 0 | 0 | 0 | Excluded |
| `ZombieHuman` | `DefaultNPC` | 5000 | 1500 | 60 | 60 | Included |
| `Player` | None | 6700 | 5200 | 85 | 85 | Excluded |
| `ScarBoss` | `DefaultNPC` | 8000 | 2500 | 85 | 85 | Excluded |
| `Boss` | `DefaultNPC` | 15000 | 15000 | 90 | 90 | Excluded |
| `Default` | `DefaultNPC` | 8000 | 2500 | 85 | 85 | Included |

All seven structs explicitly assign the same curve; none relies on inheritance
for this field in the installed flattened data:

`/Game/GameLite/Resources/AI/VisibilityDetector/DaytimeDistanceAndAnglesVisibilityPercentModificationCurve.DaytimeDistanceAndAnglesVisibilityPercentModificationCurve`

The name couples distance and angles. Without further evaluation, replacing this
curve must not be advertised as a distance-only slider or a fixed meter cap.

Read-only Zone Kit export and direct `CurveFloat.get_float_value()` evaluation
establish these keys:

| Input time | Value |
| ---: | ---: |
| 5 | 0.3 |
| 6 | 0.1 |
| 7 | 0 |
| 12 | 0 |
| 18 | 0 |
| 20 | 0.1 |
| 23 | 0.3 |

Direct integer samples at 0 through 5 return 0.3, 7 through 18 return 0,
19 returns 0.05, 21 returns approximately 0.166667, 22 returns approximately
0.233333, and 23 through 24 return 0.3. Thus this is not a direct multiplier
curve: blindly multiplying scanner distance by its value would eliminate daytime
range. A penalty interpretation is plausible, but the consuming formula still
requires confirmation. The export contains an arrival tangent of -0.025 on the
first key; transformations must preserve native interpolation rather than assume
arbitrary smooth curves. The key domain matches hours of day, but the game-clock
getter and the native consumer must agree before runtime use.

Other curve references on the scanners are
`DistancePercentToScorePenaltyCurve_Default` and
`AnglePercentToScorePenaltyCurve_Default` under the same asset directory. Those
operate on distance/angle percentages and do not establish time-of-day scoping.

### Consumer counts and inheritance hazards

The flattened object catalog contains these direct assignments:

| Field | Value | Occurrences |
| --- | --- | ---: |
| `VisionScannerPrototypeSID` | `DefaultNPC` | 1609 |
| `VisionScannerPrototypeSID` | `NoVision` | 47 |
| `VisionScannerPrototypeSID` | `Player` | 1 |
| `VisionScannerPrototypeSID` | `ScarBoss` | 1 |
| `VisionScannerPrototypeSID` | `Boss` | 2 |
| `ZombieVisionScannerPrototypeSID` | `ZombieHuman` | 1660 |

The counts are assignments, including templates, not live NPC counts.
`Korshunov` and `StrelokMutant` use `Boss`; `ScarBoss` uses its own scanner.
`Default` has no direct `VisionScannerPrototypeSID` assignment in this catalog.
`ZombieHuman` is the alternate zombie-scanner field; its presence does not mean
every object is a zombie.

A sparse override of only the three included scanners can retain the explicit
player, no-vision and boss curve references. Overwriting the original shared
curve asset would affect all its consumers and cannot preserve that separation.
Future game data must be inspected again if explicit inherited values disappear.

The raw Zone Kit configuration differs from the flattened installation data:
`ZombieHuman`, `ScarBoss`, `Boss`, and `Default` inherit this curve from
`DefaultNPC`. An editor experiment that overrides `DefaultNPC` must explicitly
retain the native curve on excluded boss scanners. Otherwise the experiment
also changes bosses through inheritance, even though the flattened release
data has explicit references. This distinction must be checked separately for
editor experiments and generated installation patches.

## Existing luminance controls are different

The exact table is
`AISettings.LuminanceSettings.EnvironmentLuminanceCoefficients.TimeOfDayBaseLuminance`.
Native entries are anonymous array rows, in this order:

| Index | `TimeFrom` | `TimeTill` | `Luminance` |
| --- | ---: | ---: | ---: |
| `[0]` | 0 | 4 | 0.2 |
| `[1]` | 4 | 6 | 0.3 |
| `[2]` | 6 | 8 | 0.6 |
| `[3]` | 8 | 17 | 1.0 |
| `[4]` | 17 | 20 | 0.8 |
| `[5]` | 20 | 22 | 0.5 |
| `[6]` | 22 | 24 | 0.3 |

The existing darkness control scales sub-daylight luminance entries and therefore
also affects dawn, morning and evening. It does not alter scanner distances.
An array-row coefficient alone cannot enforce a maximum recognition distance.

Additional asset references occur in
`AISettings.LuminanceSettings.LightLuminanceByTimeOfDayCurve`,
`ShadowLuminanceByTimeOfDayCurve`, and `ShadowOffsetByTimeOfDayCurve`; their assets
are under `/Game/GameLite/Resources/AI/Luminance/`. These are separate lighting
inputs, not a substitute for a distance setter.

## Native effect candidate

`VisionDistanceModifierEffect` has the following verified fields:

| Exact field | Installed value |
| --- | --- |
| `Type` | `EEffectType::VisionDistanceModifier` |
| `ValueMin` | `60.0%` |
| `ValueMax` | `60.0%` |
| `bIsPermanent` | `true` |
| `DuplicationType` | `EDuplicateResolveType::KeepOld` |
| `Duration` | `0.f` |
| `ValueProviderSID` | `Empty` |
| `IsSaveable` | `true` |
| `bUpdateValueEachTickPlayer` | `false` |
| `bUpdateValueEachTickNPC` | `false` |

The field name identifies a native distance modifier. It does **not** establish
whether 60% means a 0.6 multiplier or a 60% reduction, whether both distance cones
are affected, or whether the modifier is applied before close-range and retained
target adjustments.

A runtime design could apply a new, uniquely named temporary effect to supported
NPCs during night and remove it during daytime. Read-only Zone Kit reflection
confirms these native methods:

- `ApplyEffectComponent.apply_effects(target_object: Obj)`
- `ApplyEffectComponent.remove_effects(target_object: Obj)`
- Configurable `effects_to_apply: Array[InteractEffectData]`
- Configurable `can_use_stackable_effects: bool`

The struct construction path is also reflected: set `PrototypeSID.value` to a
string, assign that struct to `InteractEffectData.prototype_sid`, and place the
entry in the component's `effects_to_apply` array. `EDuplicateResolveType::KeepNew`
is a verified native duplication mode (228 definitions in the installed effect
catalog); a finite-duration, non-saveable private effect using this mode is a
candidate for bounded refresh without stacking. Application still needs a real
initialized NPC model and a loaded effect definition.

This establishes an application/removal route but not the effect's arithmetic or
successful use by the packaged mod. Game-clock access, native effect semantics,
live actor selection, and cleanup on unload still need verification. The original
permanent, saveable effect must not be reused as a global setting. It could
otherwise persist or overlap with quest-owned instances of the same effect.

## API evidence and implementation routes

The cached complete Python type inventory has no exposed type named
`VisionScanner` or `VisibilityDetector`. Targeted reflection identifies
`AIHelperLibrary` as the generic engine `AIBlueprintHelperLibrary`; `AIDynamicParam`
and `AIParamType` are also engine AI types, not scanner setters.

`WeatherController.solar_time` is an exposed read-only float. Its unit and
availability in each game world need a focused check before using it as the night
gate. `TimeSetter.hours_on_begin_play` and `minutes_on_begin_play` configure a
time-setting actor; they are not current-clock getters.

The native WeatherController default object has `solar_time=12`, sunrise bounds
4.5 to 5.5 and sunset bounds 20.5 to 21.5, supporting an hours-of-day interpretation.
The inspected editor world had only the default object, not an active weather
actor, so these values do not verify a live clock. A runtime controller must
resolve a world instance and stop applying the modifier if none is available.

`Obj` exposes `is_human()`, `is_alive()`, `is_current_player()`,
`is_player_controlled()` and zombie-state getters. No prototype SID getter was
found in the reflected `Obj`/`ObjBase` surface. `CppMediator.get_prototype_id(Obj)`
returns a numeric ID, but its mapping to a CFG SID is not established. The raw
`ID` fields in the installed CFG are not a reliable mapping: many definitions
contain zero. Human/alive checks alone cannot exclude named human bosses.

A conservative class filter is supported by the installed object definitions:

| Exact blueprint asset name | Object roots | Scanner scope |
| --- | ---: | --- |
| `BP_AI_Human` | 1,580 | All `DefaultNPC` |
| `BP_AI_Faust` | 3 | `DefaultNPC`, including `FaustBoss` |
| `BP_AI_Faust_Clone` | 2 | `DefaultNPC` |
| `BP_AI_Human_PSYNPC` | 18 | `DefaultNPC` |
| `BP_AI_PsyPhantomHuman` | 5 | `DefaultNPC` |
| `BP_AI_Korshunov` | 1 | `Boss` |
| `BP_AI_Scar` | 1 | `ScarBoss` |
| `BP_AI_Strelok` | 1 | `Boss` |
| `BP_AI_Blinddog` | 3 | Two `NoVision`, one `DefaultNPC` |

The ordinary class asset is
`/Game/GameLite/Blueprints/Characters/NPC/Final/BP_AI_Human.BP_AI_Human`.
It is the blueprint referenced by `NPCBase.Blueprint`. None of the installed
`Player`, `NoVision`, `Boss`, or `ScarBoss` definitions share this exact asset.
A first implementation could therefore restrict itself to this exact generated
class, with the ordinary alive/non-player checks, and describe its scope as
ordinary human NPCs. Class inheritance must not widen the match. Derive the class
from the installed data and validate its consumers; do not assume future game
versions or other mods retain the same assignment. Live spawned-class identity
still needs one check. This excludes named boss classes, but does not distinguish
story NPCs that use the ordinary class.

Using every `DefaultNPC` consumer would include Faust. Selecting a class from
one matching prototype without checking its other consumers is also unsafe:
the blind-dog blueprint has mixed scanner assignments. These are concrete
reasons to begin with the exact ordinary-human class rather than all humans or
all users of a scanner SID. An isolated test must still target only one
explicitly selected ordinary NPC.

Further reflection rules out several misleading measurement shortcuts:

- `NPCComponent` contains interaction/dialog settings. Its `cone_angle`,
  `cone_height`, and interaction-radius fields are not AI sight settings.
- `ThreatSensor` and `ThreatAwareness` are enums, not readable sensor instances.
- `GSCAIController.line_of_sight_to()` describes the engine's collision traces to
  the target's center/top. It does not establish the custom scanner's range,
  light penalties or effect-modified detection boundary.

Calling an effect method without an exception is not a distance measurement.
Validation needs either a native scanner diagnostic exposing the computed range
or a controlled detection-boundary experiment with the actual vision sensor.

Engine `AISenseConfig_Sight` exposes `sight_radius` and `lose_sight_radius`.
There is no evidence that S.T.A.L.K.E.R. 2's custom scanner uses these generic
Unreal properties. Changing them without verifying a connection would be a
misleading feature.

Editor diagnostic strings include `fg.VisionScanner.DrawDebug`,
`GSC.AI.VisionScannerTraceComplex`, `GSC.AI.VisionScannerTraceMulti`, and
`XToggleDrawInteractNPCStats`. These can help inspect the scanner but do not
provide distance or time-of-day setters. `CppMediator.get_focused_enemy(Obj)`
exposes a current enemy, not the sensor or measured sight boundary that acquired
it. No computed-range getter was found in the inspected model, controller,
mediator, cheat-manager, or debug-drawer reflection.

| Candidate | What is established | Remaining gate |
| --- | --- | --- |
| New curve asset plus sparse scanner CFG references | Real time-of-day asset reference; separable scanner scope | Read native keys and semantics, construct the transform, verify daylight preservation and cooked loading |
| Temporary native vision-distance effect | Real effect type, native apply/remove methods, conservative ordinary-human class scope | Verify live class/clock, effect construction, modifier semantics and lifecycle cleanup |
| Generic Unreal AI sense radius | Engine property exists | No connection to the game's custom scanner established |

## Required focused verification

1. Preserve the inspected original curve keys, evaluation range and source
   identity, including daylight keys and tangents. Do not hardcode a native
   baseline or treat the zero daytime value as a distance multiplier.
2. For a curve implementation, verify that only the intended three scanner CFG
   references change. Defaults must generate no patch or added dependency.
3. For a runtime implementation, verify effect add, replacement and removal;
   check midnight wrap, dawn, newly streamed NPCs and disabled-mod cleanup.
4. Compare one ordinary NPC's detection boundary by day and night in a bounded
   editor scene, with other vision/light controls held constant. Check central
   and peripheral directions to establish any angle coupling.
5. Keep player/boss/no-vision scanners unchanged. Describe the result as a
   modifier unless an actual hard distance boundary has been measured.

The native curve and effect both provide concrete paths for further work.
Neither is ready to be labelled a verified night-only range feature from static
CFG and reflection evidence alone.
