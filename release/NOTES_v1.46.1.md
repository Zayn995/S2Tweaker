# S2Tweaker 1.46.1 — Scrollable Build Reports

Fixes [#21](https://github.com/Zayn995/S2Tweaker/issues/21), reported by NooB9496:
the message shown after building a Pak could extend beyond the screen when many
settings were changed, leaving its OK button inaccessible.

- The completion report now opens in a wider, resizable window with scrolling
  and word wrapping. Its initial size fits the current monitor's available area.
- **OK stays below the scrolling report.** Enter and Escape also close the window.
- The full change list, output paths, previous-Pak backup information,
  animation/sound companion instructions and debug-export messages are retained.

This is a desktop interface fix. Existing generated Paks do not need rebuilding
just for this update. Gameplay settings and the animation/sound companion are
unchanged.

## Validation and download

All 68 local headless suites passed. The GUI regression check covers 350 changes,
a long file path, an 800 × 600 work area, increased UI scaling, scrolling,
resizing and keyboard confirmation. No game or Zone Kit session was needed.
All 19 signed desktop runtime binaries remain unchanged.

Download **S2Tweaker_v1.46.1.zip** and extract the complete folder. Keep
`_internal` beside `S2Tweaker.exe`. Preserve your settings and profiles when
moving to a new folder. The source ZIP is for development.

Source build: install `requirements.txt` and run `build.bat`. The published
portable package uses the unchanged signed Python runtime assembled by
`tools/refresh_portable.py`, as defined in the GitHub build workflow.
