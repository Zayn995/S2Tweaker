# Editor workspace improvements (v1.37.0)

The desktop editor now has an Overview page and left navigation. Game-data
generation still uses the existing Settings and selective config patch engine.
No native in-game menu or targeted third-party mod support is included.

| Feature | Behavior |
| --- | --- |
| My changes | A combined, editable list across categories. Values are editor inputs; use Preview for actual generated values. |
| Favorites | Star controls in their category or in Overview. Favorites persist separately from game settings. |
| Undo / redo | Whole-state history, including overrides and mod name. A mouse drag commits once on release. Reset and profile loads can be undone; file installation/removal is not part of settings history. |
| Profiles | Name and describe the current settings, duplicate a saved profile, compare it with the current selection, or load it. Existing plain JSON presets remain readable; new metadata preserves the old top-level groups. |
| My mods | Read own manifests in output, pak_history and the selected game's ~mods folder. Inspect settings, compare two own Paks, load settings, or restore a selected copy to a chosen destination. |
| Pak history | Build into a temporary location, read back every output entry, retain the previous destination, then replace it. Failed build/readback/backup preserves the old destination. Removing the current named Pak also retains a backup. |
| Preview | Summarize the current selection and inspect generated config values, resolving original values where practical. No-effect output is explicitly identified. Large/unresolved bases are labelled rather than guessed; the displayed assignment list is bounded. |
| Relationships | Control details describe existing override priority and retain the control's original coupling explanations. Individual weapon factors take priority over category factors, then global factors. |
| Navigation | A scrollable left category list with counts of changed editor inputs. |
| Density and scale | Compact or detailed explanations and 85/100/115/130 percent widget scale under More options. |
| Command layout | Preview, build and install remain visible. Profiles, own Paks and display/occasional actions have their own entry points. |
| Evidence status | Distinguish experimental controls, explicitly recorded in-game reports and controls with no recorded play-test. Export checks never imply verified gameplay. |

Editor preferences are stored in `editor.json`. Game settings remain in
`settings.json`, profiles in `presets/`, retained Paks in `pak_history/`.
Nothing is written into the executable. The preferences stay local and are
not embedded into generated game patches.

## Scope and limits

The own-Pak comparison reports shared exact config targets and input INI
replacement. It does not establish effective load order, inheritance or list
compatibility. No-overlap is not a guarantee that two mods can coexist.
Retaining or restoring a Pak does not roll back savegame state.

The Overview limits visible rows to 100 at a time; its filter can reach the
remaining entries without creating thousands of widgets. Individual controls
remain available through their original category trees.

The current runtime and all existing EXE/DLL/PYD files are retained byte for
byte. `tools/refresh_portable.py` assembles fresh application sources around
that runtime into a new destination and verifies the complete binary inventory.
It never starts the GUI. This preserves the existing starter signature;
the separate application source files are not covered by that signature.

Functional verification uses headless history/profile/controller tests and
real Pak readback/backup/restore fixtures, plus the existing regression suites.
Visual layout and interactive GUI behavior are not verified by those tests.

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
