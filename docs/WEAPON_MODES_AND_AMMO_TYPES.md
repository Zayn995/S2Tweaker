# Per-weapon fire modes, ammunition types and overhaul compatibility

Introduced in 1.45.0. [Molkerr's 16 September report](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5700758898)
confirms several fire-mode/ammunition combinations and ammunition choices adapting
to a changed caliber. The report does not name every tested weapon or combination;
it is limited player evidence, not our own game test or universal compatibility.

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
selections emit no additional patch. The player report supports the tested
combinations; it does not independently verify every array reduction or newly
enabled firing mode. A parser readback is not an engine test.

## Sidearm and inventory compatibility

Molkerr previously confirmed **All weapons** with OXA Standard. His 16 September
follow-up on 1.45.0 now also confirms **SMG** and **SMG + shotgun**, superseding the
earlier partial-failure report. OXA Prototype remains unverified. The earlier
inventory-comparison limitation has not been reported as fixed.

The native `GunAKU_PP` setup (AKM-74U) inherits `TemplateSMG`. Consequently the
SMG category and sidearm selection include it; this is the game's category, not
a claim about the real weapon's classification.

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

The supplied compatibility report identifies **OXA Standard 3.0.5** in the
accompanying message, OXA's A/B Paks and packed assets, with Avoid conflicts off.
It confirms overlapping item-dimension fields, but does not include the selected
size factor, generated CFG values or final runtime values. Local 50% generation
produces 2x1 cells for both Arev and Fora230 from the installed baselines. That
does not prove what his save/installation loaded. The exact OXA Standard 3.0.5
package and generated output are not available locally. No OXA-specific merge or
inventory-size fix is claimed.

### OXA 3.0.6 archive inspection

Both locally supplied **3.0.6** archives were inspected separately. This is a
newer version than the **3.0.5** package in the player report, not a reproduction
of that installation. Standard contains 56 CFG files across its A/C Paks;
Prototype contains 1,842 across its Z/DLC Paks. All of those CFGs were readable
by the existing scanner. Their separate IoStore assets were not inspected.

Both variants explicitly apply `{bpatch}` assignments to these existing items:

| Item | OXA 3.0.6 width x height | S2Tweaker at 50% |
| --- | --- | --- |
| Arev (`GunArev_ST`) | 5 x 2 | 2 x 1 |
| Fora230 (`GunFora230_PP`) | 4 x 2 | 2 x 1 |
| AKM-74U (`GunAKU_PP`) | 5 x 2 | 2 x 1 |

In Standard these assignments are in
`ItemPrototypes/WeaponPrototypes_OXA.cfg`. In Prototype Arev/Fora230 are in
`ItemPrototypes/WeaponPrototypes/WeaponPrototypes_AR.cfg`, and AKM-74U is in
`ItemPrototypes/WeaponPrototypes/WeaponPrototypes_SMG.cfg`. The scanner detects
their dimension fields. This establishes an actual competing assignment; it
does **not** establish the order in which the game applies the distinct patch
files. These specific entries are sparse patches, not whole-item replacements.
Renaming the outer Pak is not a verified repair for their conflict.

Prototype also defines many additional weapon IDs. For example,
`GunAKS74U_PP` is a separate item from the installed game's `GunAKU_PP` and has
its own grid and weapon-setup reference. Patching the latter does not directly
patch the former. Standard also introduces items such as `GunGlock17_HG` and
`GunP30L_HG`. S2Tweaker currently reads the installed game's catalog; scanning
an overhaul does not import its new items into that catalog or extend the
global/per-weapon controls to them. Treat neither variant as fully supported.

The generated 50% CFGs, neutral no-output behavior and all scanned archive CFGs
were checked locally. Neither overhaul was installed for this inspection. The
later supplied output is analyzed below; no in-game size repair is claimed.

Since 1.46.0, the compatibility report includes current editor selections and
the complete property overlap list. It explicitly distinguishes the current editor
from the installed Pak and treats filename order as an estimate. The prior
"your values win" guarantee was not justified for patch order or packed assets.

### Supplied player Pak and report, 17 September 2026

Molkerr supplied a [generated Pak](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5718066361)
and a [new compatibility report](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5717746507).
These represent different editor/build states:

- The embedded manifest identifies the Pak as **1.45.0**, generated on
  16 September at 19:19:03. It selects 50% inventory size and 20% item weight.
  Direct CFG inspection confirms `GunArev_ST`, `GunFora230_PP` and `GunAKU_PP`
  each receive a **2x1** grid, plus their requested weight changes. Those changes
  are present in the supplied output; they were not omitted by the generator.
- The report identifies **1.46.0**, OXA Standard 3.0.6 and **Avoid conflicts ON**.
  The current changes list no longer includes the global size/weight adjustments.
  Avoid conflicts intentionally resets and locks an entire overlapping slider,
  including its nonoverlapping items. It does not merge competing values.
- His [follow-up](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5718158532)
  reports unchanged grids on OXA-integrated weapons and smaller grids on weapons
  outside that integration. This supports the OXA overlap diagnosis; it does not
  identify the engine's final patch ordering or establish an automatic repair.

Switching Avoid conflicts off restores access to the sliders; it is **not a
verified solution to the original OXA conflict**. No OXA files or player-generated
translations are redistributed with the tool. The supplied files were inspected
locally without installing either overhaul or altering a save.

## Validation

The focused generator tests cover native/no-op choices, list reduction, added
existing ammunition types, shotgun projectile selection, invalid values, combined
caliber/rate/magazine changes, edition routing, profiles/history, corrected
sidearm classes, and inventory/slot reassertion detection. A separate GUI check
covers lazy row construction, state collection, profile reload, caliber changes,
disabled controls and reset. No game or Zone Kit session was started for these
changes.
