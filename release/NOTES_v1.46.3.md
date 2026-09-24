# S2Tweaker 1.46.3 — Smaller Generated Paks

Fixes [#22](https://github.com/Zayn995/S2Tweaker/issues/22), reported by
craigduk76: Paks built with 1.46.2 were far larger than the same Paks built with
1.37.3 and earlier, while their debug configuration output was identical.

## Why they grew

Every generated Pak embeds a manifest so that "Load preset …" can read your
settings back out of it. That manifest stored the state of *every* control,
including the thousands sitting at vanilla. The optional editors register 2,837
of the editor's 3,264 sliders — artifact editor, NPC equipment, regional weather
and detail options — so the manifest grew along with them, and Paks are written
uncompressed:

| Version | Sliders | Manifest |
| --- | --- | --- |
| 1.37.3 | 508 | 17.5 KB |
| 1.38.0 — regional weather | 760 | 34.8 KB |
| 1.39.0 — artifact editor | 1124 | 58.8 KB |
| 1.40.0 — artifact bonuses, NPC equipment | 2773 | 206.6 KB |
| 1.41.0 — detail settings | 3261 | 238.5 KB |
| 1.46.2 | 3264 | 238.9 KB |

That matches the report: a Bullet Drop Pak with 7 KB of configuration was 25 KB
on 1.37.3 and 249 KB on 1.46.2. The debug export never contained the manifest,
which is why the configuration output looked unchanged between versions.

## What changes

- **Paks and the settings file keep only what you changed.** An aim-punch-only
  Pak drops from 245,363 to 1,012 bytes. A `settings.json` with two changed
  values drops from 237,931 to 308 bytes.
- **Reading settings back is unaffected.** Importing a Pak resets every control
  to vanilla before applying the manifest, and the editor builds its controls at
  vanilla on startup, so a stored default restored nothing that its absence does
  not restore.
- **Your existing Paks still work.** They keep their complete manifest and
  import exactly as before, including older Paks kept for settings recovery.
  The format stays `manifest_version 1`, so S2Tweaker 1.10.0 and newer read the
  smaller manifests as well.
- **Profiles and presets are unchanged.** They continue to store the complete
  state, where size is no concern and the editor's comparison view expects it.
- **No change to the generated game data.** The configuration patches inside the
  Pak are what 1.46.2 produced. Rebuilding is optional and only makes the file
  smaller.

## Artifact 'Radius' renamed

[#23](https://github.com/Zayn995/S2Tweaker/issues/23), reported by matalayupog:
the 40 cm `Radius` each artifact carries had no established meaning, and its
slider said as much. The report shows the same Slug artifact floating visibly
higher at 5x than at 2x, so the slider is now **Artifact hover height** and the
build report follows. This is one screenshot from one player and has not been
reproduced here, so it stays marked experimental — a pickup radius that happens
to displace the mesh would look the same. The generator is unchanged: it scales
the same values as before and writes no patch at 1x.
[Game check and open questions](../docs/REMAINING_ISSUE_CHECKS.md).

## Validation and download

New headless checks cover the reduction from both ends: the reducer's semantics —
defaults dropped, changed values kept, override groups copied rather than
aliased, numeric tolerance, unknown keys retained — and real generated Paks built
from the actual control inventory, so controls added in later versions cannot
quietly reintroduce the defaults. The window check builds a Pak, reimports it,
writes the settings file and restarts the editor from it. The sizes above are
that suite's measurements.

All 28 headless CI suites passed on Windows, along with the portable self-test
and the signature check on all 19 unchanged runtime binaries. The game-data and
window suites run locally, as always.

No game or Zone Kit session was started. The artifact hover height is not
play-tested, and neither is the rest of the tool.

Download **S2Tweaker_v1.46.3.zip** and extract the complete folder. Keep
`_internal` beside `S2Tweaker.exe`. Preserve your settings and profiles when
moving to a new folder. The source ZIP is for development.

Source build: install `requirements.txt` and run `build.bat`. The published
portable package uses the unchanged signed Python runtime assembled by
`tools/refresh_portable.py`, as defined in the GitHub build workflow.
