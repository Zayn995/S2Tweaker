# Stealth controls and verified limits

Introduced in 1.46.0. The separate controls are not play-tested yet.

`Crouch visual stealth` and `Crouch sound stealth` replace the combined
`Crouch stealth` control. Both retain the original 25–400% range and direction:
higher values reduce the corresponding coefficients. At 200%, each affected
coefficient is halved. This is not a measured reduction in detection distance
or a guarantee of concealment.

| Control | Player setting | Shared pose setting |
| --- | --- | --- |
| Crouch visual stealth | `StealthParams.VisibilityCrouchCoef` | `CharacterPoseSettings.*.VisibilityCoef` for `Crouch` and `LowCrouchInPlace` |
| Crouch sound stealth | `StealthParams.NoiseCrouchCoef` | `CharacterPoseSettings.*.NoiseCoef` for the same poses |

All values come from the installed `ObjPrototypes.cfg` and `AIGlobals.cfg`.
Only changed fields are emitted. The two controls have disjoint patch fields,
including when exported into separate newly generated Paks. Old combined Paks
still modify both channels and should be replaced when separating them.
Shared pose settings may also affect NPCs using those poses. The sound control
changes AI perception coefficients, not audible footstep volume or sound assets.

Old settings, profiles and embedded UI manifests copy their combined percentage
to both new controls. Explicit new choices take precedence. Programmatic
`Settings(crouch_stealth_factor=...)` remains supported and multiplies with any
separate factors provided by the caller; the GUI only exposes separate controls.

## Existing options and unsupported claims

The [follow-up in issue #17](https://github.com/Zayn995/S2Tweaker/issues/17#issuecomment-5693234332)
suggested several possible variable names. The installed 2.0.5 CFG data contains
none of `Player_BaseIlluminationFactor`, `PlayerLuminanceMultiplier`,
`Light_PlayerGlowFactor`, `Sight_Night_MaxDistance`,
`Crouch_Visibility_Modifier`, `LowCrouch_Visibility_Modifier` or
`Sight_VisibilityFactors`. These are not implemented as guessed patch keys.

- The native `LuminanceSettings` comment states that `BaseLuminance` applies to
  agents and the player model uses environment luminance instead. It does not
  establish that Lumen rendering gives the player a detectable glow.
- `Night darkness for NPC eyes` already scales the sub-daylight entries of
  `TimeOfDayBaseLuminance`, including dawn, morning and evening. Setting those
  entries to zero does not prove that all other visibility contributions stop.
  The report of improved stealth at 50% is a player report, not an isolated test
  of the new split controls.
- Weather-specific AI luminance is available in the World tab, independently
  of the combined bad-weather sight/hearing control.
- `AI sight through grass and leaves` adjusts AI material translucency for
  supported grass and leaf materials. It does not change rendered vegetation
  or guarantee that every bush blocks sight.
- General NPC vision range also affects daytime. Vision scanners contain
  luminance penalties and a daytime distance/angle curve reference. A true
  night-only hard distance cap requires additional asset/engine investigation;
  no such CFG-only control is claimed here.

Validation covers independent output, composition with other stealth controls,
legacy profile preservation and GUI integration. Campaign behavior remains
unverified.
