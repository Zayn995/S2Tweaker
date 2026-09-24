# S2Tweaker 1.47.0 — Live In-Game Menu & Consumable Animation/Sound Update

An optional F10 menu now changes companion settings during ordinary gameplay.
Medicine, eating and drinking also get separate speed controls with paired
native animations and matching sound-duration parameters. Four additional
CFG sliders cover player recovery and helping wounded NPCs.

## Live companion menu

Enable **In-game companion menu (F10, experimental)** on the Player page,
then rebuild and install or export the updated companion and profile.

- Live idle sway, firing movement, weapon/movement sound toggles, and separate
  medicine, eating and drinking speeds.
- Select 1%, 5% or 10% adjustment steps and one of three preset slots.
- Up/Down selects a row; Left/Right adjusts; Enter saves normal preferences.
- P saves the selected preset; L loads it. Enter makes loaded values the normal
  startup preferences. Presets are tied to the exact generated source profile.
- R resets the selected row; Home restores generated companion values and the
  10% step; Backspace discards edits since opening or the last successful save.
- F10/Escape closes while retaining session values. **The menu does not pause
  the game.** Ordinary CFG sliders still require rebuilding and reinstalling.

## Consumable animation and sound speeds

World has separate **Medicine use speed**, **Eating speed** and **Drinking speed**
controls, from 25% to 400%, with finer numeric entry. Changing a category requests
its companion and matching sound timing automatically. At 100% that category
keeps its generated baseline unless changed through the opted-in live menu.

The original player and held-item animations retain their native consumption
and sound events. Healing amounts and effect duration are not changed. Twelve
ordinary animation families are covered; quest/mod items reusing those exact
animations share the family speed. Custom animation paths and cinematics are
excluded. Inventory action speed is a separate CFG control, and its interaction
with these new controls is not yet verified.

## Four additional CFG sliders

- **Sprint exhaustion threshold:** percentage of the installed threshold in
  stamina points, independent of maximum stamina.
- **Exhausted stamina recovery delay:** delay for the sprint-exhausted state.
- **Suppression recovery speed:** decay of the player's suppression points;
  separate from weapon recoil and spread.
- **Hold time to help a wounded NPC:** input hold duration, without changing
  healing amount or animation speed.

They read installed game values and emit no changes at 100%. The two exhaustion
options preserve the native threshold array and should be configured together
in the same Pak. Missing/ambiguous data or a threshold crossing another native
state is rejected. These four options are **not play-tested yet**.

## Validation and limits

All 73 local headless suites passed, including targeted reruns after updating
two legacy checks for native-profile controls and suppression coverage. The
portable application window also passed its launch/layout smoke check.

Zone Kit checks covered the expanded menu's step sizes, slot-1 save/load,
selected reset and discard. A normal drinking action after changing 100% to
150% live used paired 1.5 animation rates, matching 66.67% sound/clothing-duration
parameters, consumed exactly one item and completed normally. Earlier separate
100%/150% drinking checks also passed.

This is limited Zone Kit evidence, not a full campaign or audible-alignment test.
Other consumable families, preset slots 2/3, startup restoration of the expanded
save format, interrupted actions and arbitrary mod combinations remain unverified.
Night-only NPC vision is still research and is not exposed as a working slider.

The companion contains about 95 KiB of original runtime files, with no original
game animation or sound media. All 19 desktop runtime binaries remain unchanged;
the launcher retains its Python Software Foundation signature. Automatic install,
ZIP export and CFG debug output share the same updated companion and profile.

## Download and update

Download **S2Tweaker_v1.47.0.zip**, extract the complete folder, and keep
`_internal` beside `S2Tweaker.exe`. Preserve your existing settings and presets.
Enable the new menu or desired consumable speed, then rebuild/reinstall the
companion and profile: updating only the desktop tool does not update an old
in-game companion. Old menu-only preview preferences are ignored until saved
again in the expanded menu; campaign saves are not modified by menu preferences.

The source ZIP is for development. Details: [companion guide](../docs/ANIMATION_SYNC.md)
and [recovery controls](../docs/PLAYER_RECOVERY_CONTROLS.md).
Source build: install `requirements.txt`, then run `build.bat`. The published
portable build uses `tools/refresh_portable.py` with the unchanged signed runtime;
the GitHub workflow independently checks its sources, signatures and ZIPs.
