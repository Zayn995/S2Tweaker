# S2Tweaker 1.38.0 — regional weather controls

Adjust ordinary weather separately in 18 regions. Load your game data, open
**World → Regional weather (experimental)**, choose a region and click
**Edit this region's weather**.

- Selection weights: 0–400%; duration: 25–400% of the installed game's values.
  100% leaves that regional setting unchanged. A weight is not a probability.
- Only currently enabled, verified ordinary weather entries are offered:
  94 weather rows / 188 settings across 19 profiles in the audited 2.0.5 data.
  Red Forest's two profiles are grouped under one region.
- Regional factors combine with the existing global rain and duration controls.
  Values that cancel back to vanilla produce no patch. Invalid combinations
  leaving a changed region without any positive ordinary weight are rejected.
- Settings support profiles, favorites, undo/redo, reset and conflict avoidance.
  Unavailable saved settings remain resettable and do not generate a patch.
- Emissions, quest/forced weather, underground and unconfirmed special profiles
  are excluded from the new regional controls. No UE4SS or runtime loader.

**Validation:** 50 local headless suites and 11 CI suites; live 2.0.5 baseline
checks, neutral-output and global-control regression checks, and pak readback.
The packaged interface was checked in one Windows window across all 18 regions,
including editing, undo/redo, profile restoration, export and reset.

**Not play-tested.** These checks do not verify in-game weather transitions or
geographic boundaries. Quests and forced weather can override ordinary weather,
and changes may wait for a later transition. The multi-job feature remains
experimental with its existing savegame restrictions. An independent slow-motion
hotkey is not included.

Extract the complete ZIP over your tool folder and keep the executable, DLLs and
`_internal` folder together. Rebuild your personal pak after changing settings.
All fixes from 1.37.4 for game patch 2.0.5 are included.

The tagged GitHub Actions build uses the existing hash-pinned runtime. All 19
EXE/DLL/PYD files remain unchanged; no new VirusTotal result is claimed for this ZIP.

[Usage and validation limits](https://github.com/Zayn995/S2Tweaker/blob/v1.38.0/docs/REGIONAL_WEATHER.md).
[Research and baseline evidence](https://github.com/Zayn995/S2Tweaker/blob/v1.38.0/docs/REGIONAL_WEATHER_RESEARCH.md).
Source: tag `v1.38.0`; build: `.github/workflows/build.yml` and
`tools/refresh_portable.py`.
