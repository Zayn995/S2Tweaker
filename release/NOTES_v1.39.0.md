# S2Tweaker 1.39.0 — artifact editor and world settings

Edit individual artifacts and related world settings in **World → Artifact editor & related settings**.
Choose a family and target, then **Edit selected settings**. The installed 2.0.5
baseline exposes 353 supported settings across five families:

- **Artifacts:** individual weight, base price and existing bonuses for 69 ordinary
  artifact candidates. Each changed bonus gets an isolated effect reference.
  Harmful radiation uses the game's native tiers: inherit, off, or tier 1–4.
  The inventory includes candidates whose ordinary gameplay availability is not confirmed.
- **Detectors:** separate reveal, work and near-detection radii for Echo, Bear,
  Gilka and Veles, plus Veles sonar/anomaly radii. Final radius constraints are checked.
- **Weird Ball:** seven damage/stamina/weight parameters, including dynamic weight
  bounds and weight-decrease settings. Their gameplay timing remains experimental.
- **Moving anomalies:** speed and pursuit distance for four ordinary lightning/
  fire-ball variants. The prologue variant is excluded.
- **Rarity profiles:** rank-based relative weights for two supported profiles.
  Weights are normalized; disabled tiers remain disabled. **Universal also affects
  an E06_MQ01 quest placement**, so this control is not quest-isolated.

Profiles, favorites, undo/redo, reset, Pak manifests and conflict scans are
supported. Values come from the installed game; neutral settings produce no patch.
Absolute item values override global values, while individual bonus factors
combine with global strength. Higher radiation tiers may need stronger shielding.

Also delivers GitHub **#10**: **Maximum talk distance only**, 100–300%, in
**Vaulting → Interaction reach**. Keep the existing minimum/maximum control at
100% to preserve the installed minimum. The new setting uses each participant's
own baseline for the player and human NPCs. Existing profiles retain their behavior.

**Validation:** 52 local headless suites and 13 CI suites; targeted Windows GUI
checks cover editing, profiles, undo/redo, export and reset. Generated Paks are
read back and checked against their expected patches. The release source,
runtime binaries and packaged files are verified against the tag and CI output.

**Not play-tested:** the five new families and maximum-only conversation distance.
Re-equip changed artifacts; stacking, active-effect persistence, save/load,
removing mods and actual spawning still require gameplay checks. The earlier
multi-job repair (#9) and individual A-Life effects/performance (#19) remain
open for player observations; this release does not claim new fixes for them.
Use a save from before accepting experimental jobs and retain their Pak while
they are active. Old active jobs cannot be migrated.

[Artifact editor guide](https://github.com/Zayn995/S2Tweaker/blob/v1.39.0/docs/ARTIFACT_EDITOR.md) ·
[Remaining issue game checks](https://github.com/Zayn995/S2Tweaker/blob/v1.39.0/docs/REMAINING_ISSUE_CHECKS.md).

Extract the entire player ZIP and keep the executable, DLLs and `_internal`
together. Rebuild your personal Pak to apply changed settings. Includes all
regional-weather and game patch 2.0.5 fixes from 1.38.0. No UE4SS or independent
slow-motion hotkey is included. All 19 runtime binaries are unchanged; no new
VirusTotal result is claimed for this ZIP.

Source: tag `v1.39.0`; build with `.github/workflows/build.yml` and
`tools/refresh_portable.py` using the existing hash-pinned runtime.
