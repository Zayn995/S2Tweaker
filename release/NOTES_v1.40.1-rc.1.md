# S2Tweaker 1.40.1-rc.1 — job text and return-marker test release

**Pre-release for testing issue #9. NOT PLAY-TESTED.** This is a repair
candidate for missing job text and disappearing markers after another job is
handed in. Version 1.40.0 remains the latest regular release. The reported
in-game problems are not marked as solved.

Experimental multi-job exports now extend the installed native `Game.locres`
resources. This replaces the supplementary localization files used in 1.40.0.
Every installed language is discovered dynamically: all 18 languages in the
audited installation contain 208 additional title/objective aliases each.
Existing text bytes and keys are retained; isolated journal/stage IDs stay the
same. The optional language cache rebuilds automatically when required.

After a job container ends, the marker repair attempts to reapply each
remaining return marker only if that job AND its return stage are still active.
It uses the live game's marker payload and separate guarded nodes. Reward and
dialogue outputs are not replayed, and journal tracking is not forced.

**Compatibility:** enabling multiple jobs adds full native language resources
to your generated Pak (about 147 MiB for the 18-language installation checked).
Other mods replacing `Game.locres` can override these changes or be overridden;
the config conflict scan cannot detect those localization conflicts. The tool
generates translations from your installation; no game translations or Oodle
DLL are distributed in the player/source ZIPs. Initial preparation can require
your existing Oodle setup. No UE4SS is needed.

## How to test

1. Extract the entire player ZIP into a separate folder. Keep the previous tool,
   personal Pak and saves available. Load your game data and rebuild a personal
   Pak with experimental multiple jobs enabled.
2. Close the game before replacing the personal Pak. Use a separate save from
   before accepting the test jobs; do not overwrite your original saves.
3. Check job titles and objectives in your game language, then compare another
   language if possible. Ordinary quest/menu text must remain correct.
4. Accept two jobs from the same giver and complete both objectives. Hand in
   one: the other's journal, map/compass marker and hand-in dialogue should
   remain. Then hand in the other; each reward should be paid once.
5. Repeat in reverse order and after save/reload. Check three ready jobs and a
   ready job alongside an unfinished one. The unfinished job must not acquire
   a premature return marker. Report duplicate objective notifications too.

Keep the same generated Pak throughout a test until its jobs are finished or
cancelled. The shared cancel line cancels that giver's active jobs. Removing a
Pak does not undo saved quest state; restore the matching original save and Pak
together when reverting. Old active jobs are not migrated.

**Validation:** 56 local headless suites passed. The production export was read
back and compared with an independent localization candidate: all 18 native
language resources matched, with 208 aliases each. Marker state checks and
ordered hand-in simulations passed. These checks do not establish game-side
localization loading, marker lifetime, notifications or save/load behavior.
Packaged-app and GitHub build results are appended to the published release.

Molkerr reports added artifact bonuses working on 1.40.0; the screenshot shows
Liquid Stone with nine bonus rows. This is limited community evidence, not a
verification of all magnitudes or combinations. No additional artifact or
NPC-equipment feature is introduced by this candidate. Bullet Time remains
deferred. Issues #9 and #19 remain open.

[Job guide](https://github.com/Zayn995/S2Tweaker/blob/v1.40.1-rc.1/docs/REPEATABLE_JOBS_REPAIR.md)
and [language-loading research](https://github.com/Zayn995/S2Tweaker/blob/v1.40.1-rc.1/docs/JOB_LOCALIZATION_LOADING_FOLLOWUP.md).

Source: tag `v1.40.1-rc.1`; build with `.github/workflows/build.yml` and
`tools/refresh_portable.py` using the existing hash-pinned runtime.
