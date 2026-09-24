# Native animation and sound companion

These editable Blueprint assets implement S2Tweaker's optional native
animation and sound companion. They contain original control logic, not copies of
game animations. `S2TRuntimeLab` is a stable internal Unreal package name; changing
it also requires updating the numeric profile class and cooked references.

Copy this mod folder into the compatible Zone Kit's `Stalker2/Mods/S2TRuntimeLab`
and select it as the active mod. The eight files under `Wwise/Banks` are the
companion's own effect banks and metadata. Copy only these eight files into the
active mod's Wwise workspace at
`Stalker2/Mods/S2TRuntimeLab/S2_WwiseProject/GeneratedSoundBanks/Windows`.
Let the editor finish detecting the changes and caching them for the active mod.
Use **Package Mod** in the editor so its audio preparation and package
classification steps run before cooking. For both content-group cooks, disable Wwise
bulk-data packaging in the SDK's temporary custom-cook configuration. This
build uses the following section in both `DefaultGame.ini` and
`DefaultEngine.ini` under `Stalker2/Config/Custom/ModCookNewContent` and
`Stalker2/Config/Custom/ModCookOverrideContent`:

```ini
[/Script/WwisePackaging.WwisePackagingSettings]
bPackageAsBulkData=False
```

Back up existing configuration before adding this section and restore it after
cooking. These are SDK build settings; do not distribute them with the mod.
This packages the four own banks as files inside the companion's Pak, instead of
leaving references to unavailable bulk data. Verify all four bank payloads in the
finished Pak before distributing it. The
editor generates the world-subsystem registration asset. Both the NewContent and
OverrideContent Pak/IoStore triplets are needed. Do not distribute the SDK,
original game assets, editor-only files, intermediate manifests or Oodle DLLs.

The shipped runtime and its checksums are in `assets/animation_sync`. The source
assets alone are not runtime files. Rebuild the bundle whenever these assets
change; do not pair an old cooked controller with a new profile format.

The controller loads `S2Tweaker_AnimationProfile_v1` through Unreal's native
SaveGame API. This is a separate numeric configuration object with no player
progress. It accepts schema 1 and bounded positive multipliers, enables its
native tick when a movement profile is present, and follows the local player's
actual walk/run/crouch/sprint/limping state. `movement.walk` and `movement.run`
use the same component-rate correction as crouching and sprinting. Cinematics
and absent players release previously applied rates.

Body and shadow animation component rates use the initial native rate as their
basis. For the currently active action montage, the controller cancels only its
own movement factor. Native reload rates already include the CFG reload factor;
applying that factor a second time would double the requested acceleration.
The controller tracks its last montage write to detect native replays and rate
changes, and restores owned rates when the correction is released.

Validation: isolated Zone Kit gameplay with actual generated CFG patches and
native input, including 80% crouch, 140% sprint, 130% AK fire/reload, and stance
transitions during reload. The finished bundle has been cooked and inspected.
A separate brief walk/run check confirmed 80% walking and 140% running,
matching body/shadow component rates, measured foot-pose periods and movement
sound duration parameters for Step, Backpack and Clothes. Crossed extreme
walk/run combinations remain outside the measured scope.
Packaged campaign testing and arbitrary multi-slot montages remain unestablished.
Native draw/holster montages follow
the direct CFG equipment-rate multiplier; the fields named ShowEquipmentTime
and HideEquipmentTime are not inverted durations. Native Wwise duration control is implemented
separately for weapon actions and movement audio. The automatic AK reload route,
variable Time Stretch, and effect removal have passed isolated checks.

`BP_S2TSoundController` maps the held mesh to a reload group using numeric profile
indices and loads one existing anchor event as a soft reference. It attaches the
original `S2T_ActionTime` effect in slot 3. `S2T_ActionDuration` receives
100 / action factor on local-player emitters. The global default remains 100.
Jam montage names take priority over reload and equip/unequip names. Equipment
rates resolve per mesh using the same individual/category/global precedence as
the generated CFGs. The controller attaches the same effect to 20 equipment
rattle roots, loads existing anchor events and tracks successful attachments
for removal. Unmapped weapons release the
previous effect. This uses only the first active montage exposed by the engine.

`BP_S2TMovementSoundController` independently controls Step and Backpack Rattle
groups with `S2T_MovementTime` / `S2T_MovementDuration`. Native
player gait selects the walk/crouch, run/sprint or limping factor. The live native
locomotion PlayRate also contributes to audio duration so overweight slowdown
is preserved. Its animation correction already belongs to the native engine.
Existing animation
events retain responsibility for triggering footsteps. The effect uses a fixed
zero pitch shift and a 25–1600% duration range. Other mods using these effect slots
can conflict; NPC emitters keep the unchanged global parameter default.

`BP_S2TConsumableSoundController` owns the shared Player Clothes group through
`S2T_ClothesTime` / `S2T_ClothesDuration`. Consumable timing takes priority while
a recognized use montage is active; otherwise enabled movement sound timing
provides the factor, including the native locomotion rate. Keeping one owner
prevents the movement and consumable controllers from replacing each other's
clothing effect. The new movement-to-consumable clothing handoff has not had a
separate runtime comparison; earlier movement observations predate this handoff.

The animation controller also recognizes 12 exact pairs of native player and
held-item use montages. Profile keys `action.consumable.medicine`,
`action.consumable.food` and `action.consumable.drink` accept factors 0.25–4.0.
Both halves retain their native events and the existing consumption notify;
the companion does not call consumption or alter effect strength/duration.
Quest and mod variants sharing those exact montages inherit the family speed.
Cinematics and unrecognized animation paths are excluded. Consumable sound
uses a separate duration parameter and 28 native event/container anchors.

A bounded comparison using ordinary quickslot drinking at 100% and 150%
measured both montage rates at the expected ratio, exactly one consumed item
and normal action completion. Sound and clothing duration parameters followed
the factor. Audible alignment, other families played individually, campaign
play and combinations with Inventory action speed remain unverified. See
`docs/CONSUMABLE_ACTION_RESEARCH.md` for the scope and evidence.

## Optional in-game menu

Enable **In-game companion menu (F10, experimental)** when generating the mod.
The profile-bound native menu controls idle sway, firing motion, weapon/movement
sound toggles and medicine/eating/drinking playback speed. It has 1%, 5% and 10%
adjustment steps, three matching-profile preset slots, per-row reset and edit discard.
See [the companion guide](../../docs/ANIMATION_SYNC.md#in-game-companion-menu)
for controls, persistence and validation limits. CFG gameplay changes still require
rebuilding. Consumable playback uses the same validated local widget values in the
single montage writer and the consumable/clothing sound owner; the original parsed
profile map is never overwritten. The menu remains experimental and does not pause.
