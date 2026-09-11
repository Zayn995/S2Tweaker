# S2Tweaker 1.37.3 — story cancellation for multi-job journals

Corrects a missed story cleanup in the experimental multi-job repair from
1.37.2. Zalissya's story cancellation still targeted Warlock's old shared
journal, leaving the six new job journals outside that cleanup.

- The same story event now also cancels each **active** Warlock job journal.
- Completed, already cancelled and never-accepted jobs are left untouched.
- The correction follows the original story conditions and stays in the
  story quest, so shutting down the job container does not remove it.
- The original story action, rewards and ordinary job-hand-in wiring remain.

**The multi-job feature is still experimental and NOT PLAY-TESTED.**
The new regression failed against 1.37.2 and passes with this correction.
It checks the emitted event/condition/action links and all 4096 combinations
of the six journal states. This is not an engine or savegame test.
All 48 local headless suites and the 9 CI suites passed before release
preparation. No new GUI or game test was performed.

Rebuild your generated pak to receive the correction. Use a save from before
accepting jobs for testing; recovery of saves already past the story event
is not promised. Jobs accepted with the older shared-journal design cannot
be migrated. Keep the pak while its jobs are active.

No new controls or extraction inputs. The cache schema stays at 26.
The 1000% NPC-search ceiling and community-report updates from 1.37.2 remain.

The release uses the existing GitHub Actions build with the hash-pinned
1.36.1 runtime. All existing EXE/DLL/PYD files remain byte-identical and signed.
No VirusTotal result is claimed for this release's ZIP.

[Implementation and limits](https://github.com/Zayn995/S2Tweaker/blob/v1.37.3/docs/REPEATABLE_JOBS_REPAIR.md).
The source ZIP matches tag `v1.37.3`; build assembly is defined in
`.github/workflows/build.yml` and `tools/refresh_portable.py`.
