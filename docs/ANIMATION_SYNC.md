# Optional native animation and sound synchronization

Enable **Synchronize movement animations (experimental)** beside the movement
sliders on the Player page. It uses the exact selected factors; 5% slider steps
and finer numeric-entry values are supported.

**Build pak** writes the ordinary CFG Pak and a matching `*_AnimationSync.zip`.
The archive includes installation instructions, the small native companion and
a separate numeric profile. **Install to ~mods** installs both automatically.
Close the game before installing and restart after changing settings. Use only
one active S2Tweaker companion profile.

Idle sway or firing-animation movement can also be built and installed on their
own, without changing a CFG slider. In that case, the matching Pak contains the
settings manifest; the actual effect comes from the companion and its profile.

With **Debug export** enabled, the usual `<mod_name>_cfg` folder also contains an
`AnimationSync` directory with the loose companion files, installation README,
numeric `.sav` profile and a decoded `.txt` copy of that profile. The JSON manifest
lists the profile parameters. These files come from the same generated bundle
as the regular ZIP, including when using **Install to ~mods**. A subsequent debug
export with the companion disabled clears its known previous debug files.

The companion lives in `Stalker2/Mods/S2TRuntimeLab` inside the selected game
installation. Its profile is
`%LOCALAPPDATA%/Stalker2/Saved/SaveGames/S2Tweaker_AnimationProfile_v1.sav`.
Despite the `.sav` extension, this file contains only numeric configuration;
it does not contain or replace campaign progress.

The option adjusts crouch, sprint and limping animations and preserves native timing of
active action montages. Ordinary walking/running retains the game's existing
animation behavior. In particular, native reload rates already follow the CFG
reload multipliers and must not receive the factor twice. No original animation
assets are replaced.

Limping uses the installed wounded-speed coefficient and its native cap, combined
with the selected walking/running factor. Crouching takes priority over limping.
The game's own overweight effect already changes locomotion playback speed;
the companion preserves that correction instead of applying it twice.

On the Weapons page, **Adjust weapon idle sway with native companion** enables
the **Weapon idle sway (native companion)** slider, including iron sights. It supports 0–400%, where
0% removes the native idle-sway rotation. It preserves the game's baseline and
restores only its own amplitude changes. This is independent of scoped sway,
weapon inertia, firing animation kick and the **Shooting camera shake** slider.

**Adjust firing animation with native companion** enables **Firing animation
movement (native companion)** on the Weapons page. Its 0–100% range blends the
native weapon-slot pose during shooting, with 10% slider steps and finer numeric
entry. 100% retains the original motion; lower values reduce its firing-montage
contribution. Reload, draw/holster and other action montages retain full weight.
The control uses the shared native weapon layer rather than a replacement for
each weapon. Standard `_shoot` montage names are supported; unusual weapon or
animation mods can differ. An existing foreign slot-layer replacement is left
alone. Recoil, camera shake, idle sway and inertia remain separate, so 0% does
not guarantee a completely motionless weapon. No gunshot sound adjustment is
needed because this control changes pose amplitude, not timing.

Two independent sound options on the Player page adjust duration without pitch
shifts or replacement recordings. **Synchronize weapon action sounds** follows
reload, jam-clearing and draw/holster factors for supported weapon families. Mesh identities
come from installed base/DLC configuration; unknown or ambiguous meshes are
omitted. Draw/holster audio follows individual weapon, category and global speed
precedence; conflicting values on variants sharing a mesh produce an error.
Twenty native equipment-rattle groups use existing event references. The AK automatic reload route has passed a short isolated test.
Jam-clearing classification is implemented but has not been triggered in that test.

**Synchronize movement sounds** uses separate walk/crouch and run/sprint factors
for footsteps, backpack rattle and player clothing. Native animation events
still trigger footsteps; this option adjusts their sound duration. It does not
schedule extra footsteps or alter gunshot tails, speech, music or ambient audio.
The weapon and movement parameters are independent, including during reloads.
Limping also composes with gait settings. Native overweight locomotion slowdown
is included in movement sound duration, within the effect's supported range.
An isolated check verified 80% walk/crouch and 140% sprint sound factors with a
simultaneous 130% AK reload and successful effect removal. The observer stopped
at the test floor boundary after crouching; the final idle phase was not measured.

Sound synchronization supports factors from 6.25% to 400%, including fine numeric
entry. Values outside this range produce an explanatory error instead of silently
clamping the requested profile. The options use Wwise's last effect slot in the
target audio groups; another mod using those same slots can conflict. Only local
player emitters receive changed duration parameters. Two tiny original effect
banks are included; no original game sound media or game Init bank is supplied.

Tests used actual generated CFGs in a small Zone Kit gameplay scene: movement,
AK sustained hip/ADS fire, reloads and stance transitions. The package is a
Windows PC experimental build; campaign behavior and arbitrary mod combinations
remain unverified. A brief additional check confirmed 150% native AK draw and
M860 holster playback, matching equipment sound parameters and all 20 rattle
attachments, plus limping and the native overweight animation slowdown.
A separate four-second check confirmed that 80% walking sound speed combined
with the native 50% overweight playback rate requests 250% sound duration.
The requested limp/run phase had already left the limp state, so that combination
remains unverified. Arbitrary multi-slot animations remain outside the validated
scope. A separate short AK check verified automatic 40% firing-pose weight,
full weight during reload and idle, and successful release. A same-session
comparison at 100%, 50% and 0% did not change firing cadence. Other weapon
families use the same layer but have not each been tested.

Use **Remove installed animation / sound companion** to remove a tool-managed
installation. The CFG Pak remains installed: reset its movement values and
rebuild/remove that Pak separately if you also want vanilla movement. The tool
checks ownership and restores previous companion files if the CFG build fails.
Files modified by another program are left for manual review.
