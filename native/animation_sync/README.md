# Native animation and sound companion

These editable Blueprint assets implement S2Tweaker's optional native
animation and sound companion. They contain original control logic, not copies of
game animations. `S2TRuntimeLab` is a stable internal Unreal package name; changing
it also requires updating the numeric profile class and cooked references.

Copy this mod folder into the compatible Zone Kit's `Stalker2/Mods/S2TRuntimeLab`
and select it as the active mod. The four files under `Wwise/Banks` are the
companion's own effect banks and metadata. Copy only these four files into the
active Wwise workspace at `Stalker2/S2_WwiseProject/GeneratedSoundBanks/Windows`.
Let the editor finish detecting the changes and caching them for the active mod.
Use **Package Mod** in the editor so its audio preparation and package
classification steps run before cooking. For the NewContent cook, disable Wwise
bulk-data packaging in the SDK's temporary custom-cook configuration. This
build uses the following section in both `DefaultGame.ini` and
`DefaultEngine.ini` under `Stalker2/Config/Custom/ModCookNewContent`:

```ini
[/Script/WwisePackaging.WwisePackagingSettings]
bPackageAsBulkData=False
```

Back up existing configuration before adding this section and restore it after
cooking. These are SDK build settings; do not distribute them with the mod.
This packages the two own banks as files inside the companion's Pak, instead of
leaving references to unavailable bulk data. Verify both bank payloads in the
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
actual crouch/sprint/limping state. The normal walk/run state retains native animation
behavior. Cinematics and absent players release previously applied rates.

Body and shadow animation component rates use the initial native rate as their
basis. For the currently active action montage, the controller cancels only its
own movement factor. Native reload rates already include the CFG reload factor;
applying that factor a second time would double the requested acceleration.
The controller tracks its last montage write to detect native replays and rate
changes, and restores owned rates when the correction is released.

Validation: isolated Zone Kit gameplay with actual generated CFG patches and
native input, including 80% crouch, 140% sprint, 130% AK fire/reload, and stance
transitions during reload. The finished bundle has been cooked and inspected.
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

`BP_S2TMovementSoundController` independently controls Step, Backpack Rattle and
Player Clothes groups with `S2T_MovementTime` / `S2T_MovementDuration`. Native
player gait selects the walk/crouch, run/sprint or limping factor. The live native
locomotion PlayRate also contributes to audio duration so overweight slowdown
is preserved. Its animation correction already belongs to the native engine.
Existing animation
events retain responsibility for triggering footsteps. The effect uses a fixed
zero pitch shift and a 25–1600% duration range. Other mods using these effect slots
can conflict; NPC emitters keep the unchanged global parameter default.

`BP_S2TVisualController` scales all six standing/crouching/moving idle-sway
amplitude modifiers. Profile `visual.sway` encodes the requested factor plus one
so a positive value of one explicitly requests zero sway. Original values and
last writes are tracked per animation instance and per field; repeated updates
do not compound, external changes become new baselines, and release restores
only owned values. Runtime rotation, alpha and curves remain native. This does
not reduce firing montage kick, pushback or weapon inertia.

`BP_S2TShotController` handles firing-pose amplitude separately. `visual.shot`
encodes the requested 0–1 factor plus one; omission leaves the layer unchanged.
It links the original `ABP_S2TShotMix` control graph into the native player's
weapon-slot layer. Two `ABP_S2TShotBridge` instances evaluate the existing native
layer with and without main-instance montage data; cached inputs and a pose
blend provide fractional amplitude without duplicating animation sequences.
The two linked-graph nodes use static bridge classes with the `InstanceClass`
input pin hidden. Preserve these fixed bindings and the five cached pose inputs
when editing or cooking the control graph.
Only the normal branch receives main-instance montage data. The controller
selects the requested blend during `_shoot` montages, or firing when no montage
is active, and returns to full weight for other actions. It refuses a foreign
slot-layer replacement and unlinks only its own verified instance on release.
Player/cinematic changes release ownership. Camera shake and weapon inertia
remain native; zero weight need not remove every visible movement.

A brief automatic AK test verified 40% shooting weight, full reload/idle weight,
and release. A same-session comparison of native playback and 100%, 50%, 0%
blend weights preserved firing cadence. This shared-layer approach has not been
individually validated on every weapon family or in packaged campaign play.

The `Content/Audio` assets and included Wwise effect banks contain no original
game media. `Wwise/Authoring` contains only the companion's three work units,
authored with Wwise 2024.1.10.8979. Add them to the corresponding Effects, Game
Parameters and SoundBanks folders of a compatible Wwise project; preserve their
GUIDs. An isolated authoring project avoids generating unrelated automatic
SoundBanks from the full game project. Generate only `S2T_ActionTime` and
`S2T_MovementTime`, then stage their `.bnk` / `.json` pairs as described above.
Never substitute the game's
Init bank with one generated by a separate authoring project.

The native subsystem mechanism is documented in
[GSC's ModWorldSubsystem guide](https://zonekit-support.stalker2.com/hc/en-us/articles/39356792645521-How-to-work-with-ModWorldSubsystem).
