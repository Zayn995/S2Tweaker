# Local repair of the withdrawn 1.37.0 release

The owner withdrew the 1.37.0 GitHub release after a mostly black application
window and `Failed to create the menu window`. Its tag is retained as history.
Version 1.37.1 contains the repair and subsequent design polish described here.

Release preparation: all 46 local headless suites passed. The GitHub workflow
assembles current application sources with the hash-pinned 1.36.1 runtime,
checks unchanged binaries/signatures and runs the portable self-test.

Subsequent design polish is available locally in `out/design_polish_final/S2Tweaker`.
The visible Mousewheel/Design controls and all twelve palettes passed a separate
Windows check: peak 6,652 USER objects, 105 GDI objects, no Tk callback errors,
84.892 seconds including shutdown. Nine headless CI suites and the portable
self-test passed. All 19 runtime binaries remain byte-identical. This focused
design check supplements the complete startup/armor/navigation check below.

## Changes

- Removed the two CTkButtons added to every slider and checkbox. Right-clicking
  the existing label opens one shared menu for favorites and details. Overview
  retains its visible favorite/details actions.
- The 85 additional loot/world settings retain their keys, defaults, preset and
  export behavior. Values are held without Tk widgets and edited through
  **World → Edit loot & world settings** or **Overview → Loot & world**.
- Overview builds at most 20 cards per page and destroys them when leaving the
  page. Detailed help labels exist only for the selected category. Compact mode
  does not retain hidden labels. Saved non-default scaling is applied before
  building controls; 100% does not cause a redundant full redraw.
- Only one individual armor editor stays built. Closing it or selecting another
  armor releases its controls while preserving values in the existing settings
  dictionaries.
- Plain slider value displays use one native Tk label instead of the three
  widgets in a CTkLabel. They retain the surrounding background and scaled font.
- Cache schema 25 removes SpawnActorPrototypes from mandatory extraction.
  Extra stash finds request it only during export. Binary roots are decoded
  individually and only container records remain in a separate optional index.
  Temporary extraction files are removed even after a conversion failure; an
  installation changed during extraction is rejected.

## Verification completed on 10 September 2026

45 headless suites passed. Eight CI suites passed, including new regressions
for deferred settings, conflicts, edit history, scaling and optional extraction.
These checks are supplemented by the real Windows checks below; headless tests
alone do not establish that the window opens successfully.

The compact-index comparison against the existing local game data retained
exactly the same 776 eligible stash targets. Measured inputs were 108,543,592
binary bytes and 183,937,954 text bytes; the resulting index is 1,899,628 bytes.
Conversion took 14.98 seconds and is needed only for the optional stash feature.

`tools/check_gui_resources.py` provides a separate, explicit, single-window
Windows check. It records actual USER/GDI counts and peaks, Tk widget count,
elapsed time and callback failures. It exercises overview paging, categories,
density, scale, armor editors when local data is supplied, and a real menu.
Its budget is below 8,000 native USER/GDI objects, leaving headroom beneath the
standard 10,000 process quotas. A parent timeout terminates a hung child.

It is excluded from automatic test selection under the owner's existing rule.
The first approved run opened the real release runtime in 9.376 seconds at
7,095 USER objects (7,860 Tk widgets). After loading item trees it used 7,515;
opening the first armor reached 8,153. The diagnostic correctly failed its
8,000-object reserve requirement and closed after 20.826 seconds. There was no
Tk callback error in these completed stages. This prompted the additional
native value-label reduction described above.

The owner then authorized the remaining checks. The full run passed with the
unchanged release runtime (Python 3.12.10):

| Stage | USER objects | Tk widgets |
| --- | ---: | ---: |
| Startup, 8.754 seconds | 6,397 | 7,002 |
| Item trees loaded | 6,791 | 7,840 |
| Highest observed usage, overview | 7,481 | 8,445 |
| Final, after categories, scaling and real context menu | 7,159 | 8,066 |

All 15 categories including Overview, six armor/helmet editors, overview paging,
an optional setting edit/export collection, detailed/compact mode, 115%/100%
scaling and the real native context menu passed. No Tk callback errors occurred.
The USER peak stayed at 7,481 and GDI peak at 114. The run ended in 87.149 seconds;
the context menu was explicitly dismissed with Escape during that time.

A separate 60-second visual review passed: the Player page, header/footer,
native value displays and paged Loot & world controls were inspected using
Computer Use. The window was fully drawn. That run closed automatically after
74.571 seconds including startup/cleanup and reported no callback errors.
No game effects were play-tested as part of this repair.

Tcl initially could not see its bundled init.tcl inside the execution sandbox;
the actual window run succeeded outside that sandbox, using Python 3.12.10 and
the existing release binaries. Example for the revised portable runtime:

```powershell
python tools/check_gui_resources.py --open-window --portable out/repair_137_final/S2Tweaker --report out/repair_137_final/gui-resources.json --vanilla vanilla/Stalker2/Content/GameLite/GameData
```

The opt-in launcher diagnostic uses the portable build's own Python/Tk runtime;
ordinary startup and `S2TWEAKER_SELFTEST` remain separate. The latter is explicitly
headless, imports modules and checks packaging/Pak operations only.
Dismiss the test's native context menu with Escape when it appears. For visual
inspection only, add `--visual-review`; this is recorded separately and does not
claim to have performed the full resource sweep. These explicit diagnostics
remain outside the normal automatic test selection.

The current local repair preview in `out/repair_137_final/S2Tweaker` retains all 19
EXE/DLL/PYD files byte-for-byte from the withdrawn GitHub build. Only readable
Python sources changed. The portable headless selftest passed. Neither the game
nor installed mods have been changed, and no release/tag has been modified.
The application sources match the measured preview; the only later diagnostic
changes add visual review mode and remove an unused Pillow screenshot option.
Raw measurements are retained locally in `out/repair_137_startup_v2/gui-resources.json`
and `out/repair_137_verified/visual-review.json`.
