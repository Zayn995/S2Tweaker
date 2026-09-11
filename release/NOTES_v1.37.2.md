# S2Tweaker 1.37.2 — community fixes & experimental job repair

**The multi-job repair is experimental and has not been play-tested. Use a
save from before accepting jobs: jobs already active with an older pak cannot
be migrated. Keep the generated pak until its jobs are finished or cancelled.**

## Multi-job hand-in repair — #9

Molkerr confirmed that several jobs could be accepted, but handing in one
could remove another without its reward. The previous design used a shared
journal and allowed the shared round cleanup to run after an individual job.

- Each of the 69 job variants now receives its own journal and stages.
- The eight giver cleanup guards wait until no accepted job remains active.
- The normal end-of-round behavior is restored. Rewards and dialog phrases
  are preserved by the repair.
- Interact with the giver again to accept another job; the conversation does
  not open automatically. The shared cancel line cancels all his current jobs.

These are config-level corrections. Independent rewards, markers, save/reload
behavior and subsequent rounds still need confirmation in the game. This
release does not claim that the entire issue is proven fixed. Quest state is
saved by the game; removing a pak is not a save rollback.

## NPC search time and community reports

- NPC search time now reaches **1000%**, as requested in #13. The player's
  observation covers 400%; higher values are not play-tested.
- Updated tooltips record reports for talk distance, 1% sober-up speed, aim
  punch, weapon noise, guaranteed-hit shots, night perception and flashlight
  use in combat (#10, #12, #14–18).
- The quieter-zone report in #19 is a combined test, not independent proof
  of each A-Life slider. No agent-cap increase or performance guarantee.
- Talk distance still scales both minimum and maximum distance. Standing too
  close can therefore prevent interaction; its behavior is unchanged.

## Updating and verification

- Cache schema 26 adds journal prototypes; the first game-data load refreshes
  the cache. Rebuild your generated pak to use the changes.
- All 47 local headless suites and 9 CI suites passed before release preparation.
  The new regression model checks 536 ordered pairs of hand-ins. It does not
  emulate the game's quest engine.
- The portable self-test and generated-pak readback passed. No new GUI or game
  test was performed for this release; the prior 1.37.1 window checks remain
  documented separately.
- GitHub Actions assembles the current sources with the hash-pinned 1.36.1
  runtime. All EXE/DLL/PYD files remain byte-identical, including the signed
  launcher. No VirusTotal result is claimed for this release's ZIP.

Full details: [multi-job repair](https://github.com/Zayn995/S2Tweaker/blob/v1.37.2/docs/REPEATABLE_JOBS_REPAIR.md)
and [community reports](https://github.com/Zayn995/S2Tweaker/blob/v1.37.2/docs/COMMUNITY_TESTS_2026_09_10.md).

## Source and build

The source ZIP matches tag `v1.37.2`. For development, install Python 3.12+
and the packages in `requirements.txt`, then run `python main.py`.
Release assembly is defined in `.github/workflows/build.yml`; it uses
`tools/refresh_portable.py` to retain the existing signed runtime.
