# S2Tweaker 1.46.2 — Repeatable Job Pool Repair

**Experimental quest repair; not play-tested yet.** Addresses
[Molkerr's Hera report in #9](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5718007870):
requesting five repeatable jobs could leave the offer unavailable when native
story and mutual-exclusion rules allowed fewer choices.

## What changes

- Enlarged job menus check their remaining eligible pool. If no candidate remains,
  they offer the choices already collected instead of waiting for an impossible
  target. An empty pool does not create an empty offer.
- The repair covers all eight discovered job givers. The requested number is a
  maximum, not a promise that every round contains that many eligible jobs.
- Original story gates, previous-job rules, mutual exclusions, random weights,
  rewards and journals are preserved. Default and lower menu limits do not add
  this repair. Unsupported quest layouts fail export rather than dropping rules.

**Rebuild and replace your existing generated Pak to apply the repair.** Keep
the same multi-job setting and journal definitions while those jobs are active.
This update does not reset quests or migrate saved quest states; recovery of
every already-saved node state is not guaranteed. Until player confirmation,
restoring the affected jobs-per-round setting to vanilla 3 remains the reported
workaround. Please report Hera's menu, acceptance, hand-in and save/load results.

**OXA inventory-size compatibility remains unresolved.** Disabling conflicting
settings avoids those patches; it is not an automatic compatibility merge.
Issue #9 remains open. The animation/sound companion and all 19 signed desktop
runtime binaries are unchanged.

## Validation and download

All 69 local headless suites passed across the full run and a focused rerun of
the corrected sparse-patch baseline assertions. Checks preserve all 69 native
eligibility trees and the player's existing 296 generated job nodes and journal
definitions. They verify generated configuration and routing, not the full game
quest engine. No game or Zone Kit session was started for this repair.
[Technical cause and validation limits](../docs/JOB_POOL_EXHAUSTION.md).

Download **S2Tweaker_v1.46.2.zip** and extract the complete folder. Keep `_internal`
beside `S2Tweaker.exe`, and preserve your settings and profiles when moving to a
new folder. The source ZIP is for development.

Source build: install `requirements.txt` and run `build.bat`. The published
portable package uses the unchanged signed Python runtime assembled by
`tools/refresh_portable.py`, as defined in the GitHub build workflow.
