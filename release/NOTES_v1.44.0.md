# S2Tweaker 1.44.0 — Animation & Sound Update (experimental)

Optional controls now coordinate movement animations, weapon-action sounds and
movement sounds with the selected settings. Separate controls adjust idle sway
and firing-animation movement. All new companion options start disabled.

## New options

- **Player → Synchronize movement animations (experimental):** adjusts crouch,
  sprint and limping while preserving native action timing and overweight
  slowdown. Ordinary walking/running retains native animation behavior.
- **Player → Synchronize weapon action sounds:** adjusts reload, jam-clearing
  and draw/holster sound duration without shifting pitch. Weapon families and
  equipment overrides are resolved from installed base/DLC data.
- **Player → Synchronize movement sounds:** independently adjusts footsteps,
  backpack and clothing duration, including limping and native overweight
  slowdown. Native animation events still trigger footsteps.
- **Weapons → Adjust weapon idle sway with native companion:** 0–400%, including
  iron sights, independent of the existing scoped-sway control.
- **Weapons → Adjust firing animation with native companion:** 0–100% shooting
  pose contribution with 10% slider steps and finer numeric entry. Reload,
  draw/holster and other actions retain full weight. Camera shake, recoil and
  inertia remain separate; 0% does not guarantee a motionless weapon.

Movement sliders now allow 5% steps and fine numeric entry. Sound synchronization
supports factors from 6.25% to 400%. Unsupported factors and conflicting equipment
rates for variants sharing a mesh produce an explanatory error.

The shared native weapon layer avoids shipping a separate animation replacement
for each weapon. The companion adds about **52 KiB unpacked**; it contains
original control logic and two tiny original effect banks, with references to
installed animations and audio. No game animation sequences, sound recordings,
SDK files or Oodle DLL are included.

## Timing corrections and warnings

**Draw/holster speed previously applied its factor backwards.** The native fields
named `ShowEquipmentTime` and `HideEquipmentTime` are playback-rate multipliers.
They now scale directly: 150% means faster playback. Rebuild affected Paks and
review presets that compensated for the old behavior. This CFG fix also works
without enabling the companion.

Reload and jam controls now cover explicit edition/DLC values in their owning
files, including auxiliary twin reload multipliers. Inherited values follow
their parent without applying the factor twice.

The A-Life grid warning now explains the uncertain range and saved consequences.
It is not a measured render-distance control or a Distant Horizons preset; no
safe threshold is claimed. [Details](../docs/A_LIFE_GRID_LIMITS.md).

## Installation and updating

Extract the complete `S2Tweaker_v1.44.0.zip` and keep its runtime files together.
Preserve existing settings and presets when moving folders. The first game-data
load refreshes the cache to read installed weapon mesh identities.

With a changed companion option enabled, **Build pak** also creates
`*_AnimationSync.zip` containing the companion, numeric profile and installation
instructions. **Install to ~mods** installs both automatically. Close the game
before installation and restart after changing settings. Use one active
S2Tweaker companion profile.

The companion is installed under `Stalker2/Mods/S2TRuntimeLab`; its separate
numeric profile goes to
`%LOCALAPPDATA%/Stalker2/Saved/SaveGames/S2Tweaker_AnimationProfile_v1.sav`.
This profile contains no campaign progress. Use **Remove installed animation /
sound companion** for removal; rebuild or remove the CFG Pak separately.

## Verification and limits

64 local headless suites passed, including companion export/install rollback,
fine profile values, live reload coverage and CFG/companion control wiring.

Short isolated Zone Kit checks covered actual generated CFGs, AK sustained fire
and reloads, stance transitions, draw/holster, idle sway, limping, overweight
slowdown and independent sound parameters. AK firing-pose checks verified reduced
shooting weight, full reload/idle weight, cleanup and unchanged firing cadence.
The cooked package and both effect-bank payloads were inspected.

**Packaged campaign behavior and arbitrary mod combinations remain unverified.**
Jam-clearing sound classification is implemented but was not triggered in these
checks; the limp/run combination and every weapon family have not each been
validated. Other mods occupying the same Wwise effect slots can conflict. A
foreign weapon-slot layer replacement is left alone. Extreme fire-rate settings
and unusual animation mods are outside the verified scope.

[Full behavior, installation and test limits](../docs/ANIMATION_SYNC.md).
Bullet Time is not included in this update.

The signed Python starter and all 19 native desktop runtime binaries remain
byte-identical to 1.43.0. Application sources and companion assets change, so the
ZIP has a new hash. No new VirusTotal result is claimed. The source ZIP includes
the matching application code, original editable companion assets and cooked
bundle.
