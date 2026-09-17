# S2Tweaker 1.46.0 — Separate Crouch Stealth & Clearer Compatibility Reports

Crouched visibility and AI hearing now have independent controls. Compatibility
reports show more useful evidence when another mod overrides a setting.

- **Crouch visual stealth / Crouch sound stealth:** separate 25–400% controls
  replace the combined slider. Higher values reduce the respective perception
  coefficients; 200% halves those coefficients, not necessarily detection range.
  Sound stealth changes AI hearing, not audible footstep volume. Shared pose
  coefficients can also affect NPCs. The new split controls are **not play-tested**.
- **Existing profiles migrate automatically:** the old combined percentage is
  copied to both controls. Explicit separate choices take precedence. Profiles,
  history, reset, summaries, CFG exports and conflict detection support the split.
  Each control writes only its own changed fields. Rebuild your Pak to separate
  them; an older combined Pak still affects both channels.
- **More useful compatibility reports:** current editor selections and every
  overlapping property are included. Reports distinguish editor choices from
  the installed Pak. Filename ordering is an estimate, not a guaranteed winner;
  distinct CFG patches and uninspected packed assets can affect the result.
- **Updated community findings:** Molkerr reports several existing fire-mode and
  ammunition combinations, caliber adaptation, and restricted OXA Standard
  sidearm selections working. AKM-74U belongs to the game's SMG setup category.
  These are limited player confirmations, not universal compatibility claims.

## Still open

**This release does not fix the OXA inventory-size conflict.** Inspection of
Standard and Prototype 3.0.6 confirms competing size assignments for Arev and
Fora230. It does not reproduce the original Standard 3.0.5 installation or prove
runtime patch order. Mod-only weapon IDs, especially Prototype variants, are not
automatically imported into S2Tweaker's installed-game catalog. No automatic
overhaul merge or complete Prototype support is included.

The Hera repeatable-job dialogue report also remains open. No speculative quest
reset or save-state repair is included. A night-only detection-distance cap or
player-glow removal has not been implemented through unverified CFG keys.

## Validation and download

The 68 local headless suites and an isolated GUI check cover generation, migration,
independent controls, state restoration and conflict footprints. No new game or
Zone Kit session was started for this release. The animation/sound companion and
all 19 signed desktop runtime binaries remain unchanged.

Download **S2Tweaker_v1.46.0.zip** and extract the complete folder. Keep the
`_internal` folder beside `S2Tweaker.exe`. Preserve your settings and profiles
when moving to a new folder. The source ZIP is for development.

[Stealth controls and limits](../docs/STEALTH_CONTROLS.md) ·
[OXA archive findings](../docs/WEAPON_MODES_AND_AMMO_TYPES.md)

Source build: install `requirements.txt` and run `build.bat`. The published
portable package uses the unchanged signed Python runtime assembled by
`tools/refresh_portable.py`, as defined in the GitHub build workflow.
