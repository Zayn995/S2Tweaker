# Editor workspace

The desktop editor now has an Overview page and left navigation. Game-data
generation still uses the existing Settings and selective config patch engine.
No native in-game menu or targeted third-party mod support is included.

| Feature | Behavior |
| --- | --- |
| My changes | A combined, editable list across categories. Values are editor inputs; use Preview for actual generated values. |
| Favorites | Right-click a control label, or use the star in Overview. Favorites persist separately from game settings. |
| Undo / redo | Whole-state history, including overrides and mod name. A mouse drag commits once on release. Reset and profile loads can be undone; file installation/removal is not part of settings history. |
| Profiles | Name and describe the current settings, duplicate a saved profile, compare it with the current selection, or load it. Existing plain JSON presets remain readable; new metadata preserves the old top-level groups. |
| My mods | Read own manifests in output, pak_history and the selected game's ~mods folder. Inspect settings, compare two own Paks, load settings, or restore a selected copy to a chosen destination. |
| Pak history | Build into a temporary location, read back every output entry, retain the previous destination, then replace it. Failed build/readback/backup preserves the old destination. Removing the current named Pak also retains a backup. |
| Preview | Summarize the current selection and inspect generated config values, resolving original values where practical. No-effect output is explicitly identified. Large/unresolved bases are labelled rather than guessed; the displayed assignment list is bounded. |
| Relationships | Control details describe existing override priority and retain the control's original coupling explanations. Individual weapon factors take priority over category factors, then global factors. |
| Navigation | A scrollable left category list with counts of changed editor inputs. |
| Density and scale | Compact or detailed explanations and 85/100/115/130 percent widget scale under More options. |
| Mousewheel | Visible in the toolbar. Red OFF scrolls the page; green ON permits slider changes. Starts OFF every time. |
| Design | One shared desktop layout with 24 color palettes: teal/ice-blue Standard, olive/amber Zone PDA, violet Obsidian, ten more general palettes and the existing faction palettes. Previews and the active palette remain available in the toolbar. Hint text, highlighted text, tab captions and selection controls remain readable when switching. |
| Game data and Oodle | The header keeps the game folder, Browse, Confirm & load game data, and Oodle status visible. Successful loading changes the action to Reload game data. The Oodle indicator still opens the setup guide. |
| Command layout | Preview, build and install remain visible. Profiles, own Paks and display/occasional actions have their own entry points. |
| Evidence status | Distinguish experimental controls, explicitly recorded in-game reports and controls with no recorded play-test. Export checks never imply verified gameplay. |

Editor preferences are stored in `editor.json`. Game settings remain in
`settings.json`, profiles in `presets/`, retained Paks in `pak_history/`.
Nothing is written into the executable. The preferences stay local and are
not embedded into generated game patches.

The desktop uses Segoe UI, coordinated control borders, quieter inactive
navigation, and a persistent footer for preview/build/install. Overview cards
put the setting name first and its full category context underneath; hovering
the title also shows the complete label. Status colors for loading, Oodle and
mousewheel mode are independent of the selected palette. Mousewheel adjustment
still resets to OFF at each start. No game-data loading or DLL download is
triggered by selecting a palette.

## Scope and limits

The own-Pak comparison reports shared exact config targets and input INI
replacement. It does not establish effective load order, inheritance or list
compatibility. No-overlap is not a guarantee that two mods can coexist.
Retaining or restoring a Pak does not roll back savegame state.

The Overview limits visible rows to 20 per page; paging and filtering reach all
remaining entries. Leaving Overview destroys its cards. Individual controls
remain available through their original category trees.

The current runtime and all existing EXE/DLL/PYD files are retained byte for
byte. `tools/refresh_portable.py` assembles fresh application sources around
that runtime into a new destination and verifies the complete binary inventory.
It never starts the GUI. This preserves the existing starter signature;
the separate application source files are not covered by that signature.
The GitHub build downloads the 1.36.1 player archive, checks its fixed SHA-256,
then uses this same assembly step and runs the portable headless self-test.
The player README is taken from the current source when packaging the release.

Functional verification uses headless history/profile/controller tests and
real Pak readback/backup/restore fixtures, plus the existing regression suites.
Visual layout and interactive GUI behavior are not verified by those tests.

## Design polish, 2026-09-10

The current portable preview is `out/design_polish_final/S2Tweaker/S2Tweaker.exe`.
It includes the startup repair documented in `STARTUP_REPAIR.md`. Mousewheel
and Design have been moved out of More options into the visible toolbar.
Warning captions retain their amber system colour and wrap to the available
width. Palette previews retain their own colours while the main window changes.
Native slider values follow the chosen text colour; selected and unselected
tabs keep readable captions. At that stage, Standard used a blue-on-black palette.

`test_theme_palette.py` covers all palettes, normal/hover text contrast, role
round-trips, system colours, fixed previews and defaults for newly built widgets.
The separate opt-in `--design-review` checks all available palettes, toolbar
visibility at the 1000-pixel minimum width, Mousewheel state, native value text
and tab/segmented captions in one real Windows process. It records handle counts
and leaves a short interval for manual inspection. It never runs in CI.

## Local preview and verification, 2026-09-09

The preview is at `out/preview_editor/S2Tweaker/S2Tweaker.exe`. It includes
the preceding 18 loot/world additions and retains the inherited 1.36.1 version
label; this is an unreleased development preview.

All 41 headless suites passed. Following the final preview and overlap fixes,
the three new suites passed again: 8 state/profile tests, 13 Pak/preview tests
and 3 controller transaction tests. A preview against current game data also
resolved Player health from 100 to 250 and identified neutral output correctly.
Syntax, GUI imports without Tk initialization, and required bundled standard
library modules were checked. The runner now excludes window suites even
with `--only`, and accepts both `-jN` and `-j N` without mixing worker counts
into the name filter.

All 19 EXE/DLL/PYD files have the same hashes as `preview_1_18` and valid
Authenticode signatures. The starter SHA-256 remains
`58B39B6D8DC9F51A94F1A3143E49B7498FB804A101F2B33BAA14BD72D45298F8`.
The 23 shipped Python application files match the workspace. Reports are
stored beside the preview in `runtime_integrity.json` and `signatures.json`.
No GUI/game session or interactive layout review was performed for this preview.
