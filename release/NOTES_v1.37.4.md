# S2Tweaker 1.37.4 — game patch 2.0.5 data-loading fix

Fixes game-data loading after S.T.A.L.K.E.R. 2 patch **2.0.5**. Its binary
configs use format 2; the previous reader could fail during conversion or
silently read incorrect structures.

- Reads binary cfg formats 1 and 2 and rejects unknown versions explicitly.
- Rebuilds the game-data cache once (schema 27) so incorrect data is not reused.
- Conversion errors now identify the affected file.
- Existing controls use the updated game's values, including its changed
  weather hearing coefficients and NPC entries. No new controls or UE4SS.

Extract the complete ZIP over your tool folder, then load the game data again.
Keep the executable, DLLs and `_internal` folder together. Rebuild your personal
pak if you want its selected values calculated from the updated game data.

**Validation:** 49 local headless suites and 10 CI suites, using freshly
extracted data from Steam build 25222692. All 63 required configs and six
edition files loaded; the optional spawn file decoded 130,058 roots. A test
pak with 69 entries was built and read back. Version handling is covered by
six synthetic binary-format tests that contain no game assets.

**Not play-tested.** These checks verify extraction and patch generation,
not in-game behavior or savegame compatibility. The multi-job feature remains
experimental with the existing savegame restrictions. The unfinished
slow-motion feature is not included.

The existing GitHub Actions workflow assembles the release from the tagged
source and a hash-pinned runtime. No EXE/DLL/PYD files are modified. No new
VirusTotal result is claimed for this ZIP.

[Validation details](https://github.com/Zayn995/S2Tweaker/blob/v1.37.4/docs/GAME_2_0_5_CHECK.md).
Source: tag `v1.37.4`; build: `.github/workflows/build.yml` and
`tools/refresh_portable.py`.
