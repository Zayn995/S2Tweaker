# Per-weapon fire modes, ammunition types and overhaul compatibility

Introduced in 1.45.0. New fire-mode and ammunition-type behavior is not play-tested yet.

## Weapon editor

Each supported weapon has two additional experimental selections:

- **Fire modes:** Single, Burst, Auto, or a combination. The native default mode
  remains selected if it belongs to the requested combination. Otherwise the
  first selected mode becomes the default.
- **Allowed ammunition types:** Standard, Armor-piercing, Expanding, Supersonic,
  or a combination, limited to ammunition items and projectile mappings found
  for the selected caliber in the installed data. No new ammunition is created.

The existing ammunition dropdown is labelled **Ammunition caliber** to distinguish
caliber conversion from permitted ammunition types. Changing caliber resets an
incompatible type selection. **Vanilla** removes the corresponding override.
The settings participate in profiles, undo/redo, My changes, reset, summaries,
generated-Pak manifests and CFG/debug output.

Burst keeps the selected weapon's positive native burst count. For a weapon
without one, the generator uses the most common burst count among installed
player weapon setups that already support Burst. If none exists, Burst is not
offered. There is no hardcoded game burst length.

The changes affect every item using the same weapon setup, potentially including
NPCs and bosses. They do not remove mechanical bolt or pump cycles, alter weapon
animations, rewrite sound assets, or prove that a newly enabled mode works on a
particular weapon. Re-equip an unloaded weapon after changing these settings.
Existing savegame state and technician upgrades may affect the result.

## Generated configuration

All fields are in the already loaded `WeaponGeneralSetupPrototypes` data:

| Selection | Fields |
| --- | --- |
| Fire modes | `FireTypes`, and `DefaultFireType` when the old default is no longer allowed |
| Burst without a positive native count | `FireQueueCount`, resolved from installed burst-capable weapons |
| Ammunition types | `AmmoTypeProjectiles`, including `AmmoType` and `ProjectilePrototypeSID` |
| Existing caliber selection | `AmmoCaliber` and the associated projectile mapping |

The generator patches only the selected setup. Base-game and edition setups use
their respective output branches. Complete selected arrays are emitted as nested
struct replacements rather than index-by-index merges so removed entries are not
intentionally retained. The containing weapon uses `{bpatch}` and unrelated
magazine, rate, reload and caliber changes are preserved. Sparse unchanged
selections emit no additional patch. Array replacement and newly enabled firing
behavior still need a game test; a parser readback is not an engine test.

## Sidearm and inventory compatibility

[Molkerr's 15 September report](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5679630409)
confirms **All weapons** with OXA Standard. The same report describes partial
failure with **SMG** and **SMG + shotgun**, an inventory comparison limited to the
pistol-slot weapon, and Arev/Fora230 inventory sizes reverting after an OXA update.
This is a player report, not our own OXA test. OXA Prototype remains unverified.

The restricted sidearm selector now classifies each item through its actual
`GeneralWeaponSetup` reference. Previously it incorrectly passed the item SID to
the weapon-setup tree. These identities differ for numerous newer and unique
weapons. This correction covers such items as Fora230 and unique shotguns; it
does not establish compatibility with redefined or newly introduced OXA items.

Arev and Fora230 already receive the global inventory-dimension patches. The
scanner previously discarded vanilla-valued fields from full copied item
definitions. It now retains explicit `ItemGridWidth`, `ItemGridHeight`, and
`ItemSlotType` assignments because an overhaul can reassert those values over a
tweak. Unrelated unchanged fields keep their existing filtering behavior.

Fire-mode and ammunition-array overlaps are also included in compatibility
reports. Active selections display a warning in their weapon row. **Avoid
conflicts does not lock these dropdowns**; reset the selection to Vanilla to
remove its override. Scan warnings identify potential overlap, not an automatic
mod merge or verified load precedence. Full copies, mod-specific item names,
unreadable assets and game-side loading can still require a targeted patch.

The current OXA Standard package was not available locally for this check. No
OXA-specific binary or configuration merge is included or claimed as verified.

## Validation

The focused generator tests cover native/no-op choices, list reduction, added
existing ammunition types, shotgun projectile selection, invalid values, combined
caliber/rate/magazine changes, edition routing, profiles/history, corrected
sidearm classes, and inventory/slot reassertion detection. A separate GUI check
covers lazy row construction, state collection, profile reload, caliber changes,
disabled controls and reset. No game or Zone Kit session was started for these
changes.
