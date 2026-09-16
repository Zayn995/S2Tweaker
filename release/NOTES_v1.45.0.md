# S2Tweaker 1.45.0 — Weapon Fire Modes, Ammo Types & Compatibility Fixes

The per-weapon editor now includes **fire-mode combinations** and **allowed
ammunition types**, independently of its existing caliber and numeric controls.
The new options are **experimental and not play-tested yet**.

- **Single, Burst and Auto:** choose one mode or a combination. Burst retains
  the weapon's native burst length, or takes the most common existing burst
  length from installed burst-capable weapons when necessary. No game burst
  count is hardcoded.
- **Allowed ammunition types:** choose existing Standard, Armor-piercing,
  Expanding and Supersonic rounds where the selected caliber supports them.
  This does not create new ammunition. Existing weapon-specific projectile
  mappings remain unchanged unless the caliber changes.
- **Full editor integration:** profiles, undo/redo, My changes, reset, summaries,
  generated-Pak manifests and CFG/debug output include both selections.
  Changing caliber resets an incompatible ammunition-type selection.
- **Corrected restricted sidearm selection:** SMG and SMG + shotgun now classify
  each item through its actual weapon setup. The previous lookup missed newer
  and unique weapons when the item and setup had different identifiers.
- **Improved mod conflict detection:** full item definitions that explicitly
  restore vanilla inventory dimensions or equipment slots are now flagged.
  Fire-mode and ammunition-array overlaps also appear in scan reports, with
  warnings beside active per-weapon selections. Avoid conflicts does not lock
  these dropdowns; reset them to Vanilla to remove your override.

## OXA compatibility

Thanks to **Molkerr** for the detailed tests and requests. His report confirms
**All weapons** with **OXA Standard**, while the restricted sidearm selections
were only partly working. The inventory comparison may still use only the
pistol-slot weapon. **OXA Prototype remains untested.**

Arev and Fora230 already receive S2Tweaker's inventory-size patches. The scanner
now detects an additional way copied overhaul definitions can override them.
The exact current OXA Standard package was not available for a direct test:
**this release does not claim a verified OXA inventory fix or automatic merge**.
Rescan after updating other mods and inspect the compatibility report.

## Behavior and validation limits

Fire modes and allowed ammunition affect shared weapon setups, potentially
including NPCs and bosses. They do not remove bolt/pump cycles or rewrite the
animations and sounds required by a newly enabled mode. Re-equip an unloaded
weapon after changing these options. New modes, ammunition-array replacements,
savegame behavior and arbitrary overhaul combinations still require game tests.

Validation includes **66 local headless suites**, **12 focused weapon-option
checks after final review**, and an isolated GUI check covering lazy controls,
presets, collection, caliber changes and reset. No game or Zone Kit session was
started for this update. All **19 signed desktop runtime binaries are unchanged**;
the existing animation/sound companion is unchanged too.

[Detailed scope and implementation](../docs/WEAPON_MODES_AND_AMMO_TYPES.md).

Download the player ZIP, extract it completely to a new folder, and run
`S2Tweaker.exe`. Rebuild your generated Pak to use these fixes. The source ZIP is
for developers; it does not contain the ready-to-run application.
