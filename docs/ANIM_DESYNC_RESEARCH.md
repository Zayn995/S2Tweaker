# Animation desynchronization and carry-weight interactions

Historical research: 2026-08-30, game 2.0.4 (UE 5.5.4), with archive checks
on 2026-09-09. This records evidence available at those dates, not a current
compatibility guarantee. Engine and save-state explanations below include
community hypotheses that have not been reproduced in an S2Tweaker play test.

## Archive findings

The six archives checked on September 9 contained no verified locomotion
animation-rate fix or replacement locomotion animations. This finding applies
only to those archives, not to every published mod.

- [No HeadBob While Sprinting / CS Movement, v2](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2414)
  by blcksw0rdsman changes CFG movement speeds: Walk 370, Run 820, and
  Jogging/Sprint/Crouch 370, plus stamina and ADS speed. Its suggested key
  bindings are Walk on Shift and Sprint on X. It does not remove the engine's
  sprint state. The author reports mismatched footsteps; eliminating visible
  leg-animation desynchronization has not been verified.
- [Movement Modifications](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2375)
  2x, 3x and UNINSTALL contain CFG patches. All 17 reset values match the
  installed vanilla data checked on September 9. The uninstall patch has no
  refresh or state-transition mechanism, so matching values alone do not prove
  that loading it immediately resets a saved movement state.
- All eight carry-weight paks in
  [Long Days](https://www.nexusmods.com/stalker2heartofchornobyl/mods/410)
  3.0 and 3.1 are byte-identical. Only the eight upgrade-cost paks changed;
  `Upgrade_Cost` moved under `EconomyDifficulty`. The earlier theory that
  regenerated weight patches fixed animations in 3.1 is disproved.
- [Faster Animations](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2409)
  v0.5 concerns interaction montages. That is a different mechanism from
  blendspace-driven locomotion and does not establish a walking-animation fix.
- [SCAM](https://www.nexusmods.com/stalker2heartofchornobyl/mods/672?tab=posts)
  2.3 was available for inspection. Historical discussion of per-stance
  animation speed is not evidence of an implemented synchronization fix.

## Carry weight and movement

A community report described broken walking animations when changed
`ObjWeightParamsPrototypes` limits and penalty thresholds were combined with
SCAM movement changes. Restoring carry-weight defaults reportedly helped.
This is a single-user observation, not proof of a particular engine formula.

The checked vanilla data connects weight thresholds at 50/60/70/80 kg to
`OverweightMovementVelocityChange` effects, including
`VelocityChangeNoCap = -15%`. A direct coupling between those thresholds and
locomotion playback remains unverified.

S2Tweaker reads base values from the current installation through `gd.resolve`.
Regenerate the pak after a game update. Weight limits and penalty thresholds
must remain internally consistent; changing the maximum alone can produce an
inconsistent set. A published high-limit pattern uses thresholds immediately
below the maximum, such as 9997/9998/9999, but those are examples, not values
to hardcode into the generator.

Reported refresh triggers include drinking Hercules or equipping/removing a
carry-weight item for weight changes, and entering water or changing a player
effect for movement changes. Claims that movement values are cached in saves
remain hypotheses until controlled load/remove/reset tests reproduce them.
Likewise, the report that increasing `WalkTransitionCoef` above its checked
vanilla value of 1.3 accelerates transitions excessively is not independently
verified.

## Asset investigation

The research identified the player pawn reference
`Blueprint'/Game/GameLite/Blueprints/Characters/Player/BP_Stalker2Character'`
and animation content under `/Game/_STALKER2/Animations/Player/`. The inspected
player body-mesh prototypes have an empty `AnimPath`. This suggests assignment
elsewhere, but does not establish the exact locomotion AnimBlueprint path.

The [Auto-Walk mod discussion](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2485)
attributes gait selection and speed-to-play-rate mapping to native code. Treat
that as a lead to investigate rather than proof that every useful adjustment
requires a native hook.

A CFG-only packager cannot edit and cook animation assets. A future asset-based
approach needs to identify the actual animation dependencies, change a small
test asset, cook it with a compatible toolchain, and demonstrate that the game
loads it. The historical Zone Kit support limitations concerning Blueprint mods
do not by themselves establish whether a particular AnimBlueprint can be used.
See the [Zone Kit support article](https://zonekit-support.stalker2.com/hc/en-us/articles/38198531582481)
and [known-issues article](https://zonekit-support.stalker2.com/hc/en-us/articles/39349140740369)
for the referenced documentation; compatibility must be checked for the version
being tested.

Historical [UE4SS compatibility work](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2341)
does not demonstrate a Lua animation-rate fix. Neither UE4SS nor an asset addon
is required by the existing CFG generator. Any future dependency needs its own
version-specific compatibility evidence.

## Product implications and validation

- Explain that movement speed, visible animation and footsteps can diverge.
  Values closer to vanilla may reduce the visible mismatch, but no percentage
  range is established as universally safe.
- Test gait ratios as well as absolute speeds. The checked vanilla sequence is
  Walk/Run/Jog/Sprint = 160/370/625/820; an extreme report used Walk 160 and
  Run 165. Always obtain the actual baseline from the installed game.
- Test weight changes alone, movement changes alone, and their combination.
  Do not label the first combination safe merely because no failure was reported.
- Compare a fresh load, a state-changing trigger, pak removal and an explicit
  reset candidate. Distinguish generated reset values from observed restoration.
- Check animations and footsteps separately. A montage edit that helps an
  interaction does not prove that walking, running or weapon reloads synchronize.
- Whole-world time dilation changes gameplay timing as well as animations; it
  is not a demonstrated replacement for per-action synchronization.
- Do not advertise the inspected movement mods as a verified synchronization
  fix. Their CFG paths can also overlap S2Tweaker's movement and weapon patches.

These are technical limitations and test criteria, not a commitment to ship
an animation feature before a working in-game proof exists.
