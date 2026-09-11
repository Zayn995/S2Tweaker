# Repeatable jobs: experimental hand-in repair

Introduced in version 1.37.2; story cancellation corrected in 1.37.3,
11 September 2026. Partially player-tested on 1.39; localization remains open.

## Player follow-up, 11 September 2026

[Molkerr reports](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5635943100)
separate hand-ins and the remaining journal surviving save/load. His later
clean-save test retains the unfinished sibling's marker; an earlier report loses
the marker of a completed sibling. The shared cancel line cancels all current
jobs as documented. This is limited player evidence, not verification of every
giver, hand-in order, reward or save scenario.

The later video was inspected at 0:42: the long description is localized, while
the title displays `S2T_Job_RSQ04_C02` and the objective displays
`sid_journal_stage_S2T_Job_RSQ04_C02_RSQ04_C02_Start`. Preserving the old explicit
description keys does not localize the new implicit title/stage keys. See
[CFG research](JOB_LOCALIZATION_CFG_RESEARCH.md) and
[localization resource research](JOB_LOCALIZATION_ASSETS_RESEARCH.md).
Version 1.40.0 generates supplementary localization files automatically
when exporting this option. It preserves the existing journal and stage identifiers;
game-side discovery of these resources still needs testing.

## Automatic translations (1.40.0)

`build_root_files` pairs the actual isolated journal/stage keys with their original
keys and reads the translations from the currently loaded installation. On 2.0.5
this produces 18 Compact resources with 208 aliases each. Only missing title/stage
identities are added; already working general descriptions stay unchanged.

The resources are placed beside each language's `Game.locres`, under the separate
filename `S2Tweaker_JobLocalization.locres`. Whole original files are not replaced,
and no game text ships with the tool. A compact optional cache stores only these
entries, keyed by the game Pak stamp and alias map; corrupt caches rebuild and a
changed game Pak stops export until game data is reloaded. No default/startup
localization extraction or global cache-schema change is required.

Preview lists the language files; normal Pak export, verified replacement and debug
export handle their binary content without newline conversion. The generated texts
match the independently constructed research candidate in all 18 languages.
File discovery, native English and actual journal rendering still require a game
test. Do not claim the missing text is fixed in-game on binary checks alone.

## Remaining marker case

The [marker audit](JOB_MARKERS_RESEARCH.md) finds no proven CFG defect: all 318
marker-bearing nodes retain their original marker settings. Every ready-to-return
job targets its giver's shared actor GUID. No speculative marker patch was added.
For a discriminating game test, complete two jobs, hand in one, explicitly track
the surviving journal, compare map and compass, then reload. This checks whether
tracking selection or shared target-marker behavior explains the report.

## Report and diagnosis

[Molkerr's earlier report](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5622646388)
confirms that several jobs can be accepted by interacting with the giver again.
Handing in one can remove another, including a completed job, without its reward.
Earlier comments describe inconsistent availability of the next round.
The linked videos have not been independently reviewed in this repair session.

The installed config data exposes two independent problems with the old design:

- Each job container starts, finishes and cancels the same giver-wide journal
  quest. Different jobs also share the return-to-giver journal stage. Ending one
  therefore targets journal state used by its siblings.
- The round's BridgeCleanUp receives individual container completion outputs.
  Changing only the End node's ExcludeAllNodesInContainer to false did not delay
  that cleanup or isolate the journal, and left round nodes active.

These are concrete config-level defects consistent with the report. An engine
test is still required to establish whether they explain every observed symptom.

## Implementation

`quest_jobs.build_job_isolation` derives all jobs from the existing container
connections, including irregular names and the extended RSQ06–RSQ10 quest SIDs.
For the current data it generates 69 journal prototypes, 8 guard nodes and
patches the existing journal references and round-cleanup inputs.

Each job receives its own `S2T_Job_<containered quest SID>` journal and uniquely
named stages. Metadata and localization references come from the live journal
prototype. Only stages actually used by that job are included. Where the source
has no explicit title, its start-objective description key is copied into `Name`.
The later video establishes that this does not provide a localized title.
The source journals remain unchanged. Nested conditions are remapped too;
unrelated story-journal conditions (including Harpy's special job) stay intact.

Every original cleanup input is rerouted through a new If node. It uses the
game's JournalState condition to require that **all** the giver's job journals
are not Active. A completed objective awaiting hand-in still has an Active
quest journal and therefore blocks cleanup. Container completion and the
existing cancellation-cleanup input trigger reevaluation. The original End
behavior is retained, so the exhausted round can shut down normally.

No new held-job global variable is needed. Acceptance/menu patches and the
existing Taken/Clear nodes remain. Dialog windows are not forced open. The
giver's shared cancel command still cancels all his running jobs; this is now
stated in the UI. Rewards, task objectives, dialog phrases, cooldown settings,
and their connections are not rewritten by journal isolation.

New nodes and journals use separate plain config files in their respective
prototype directories; existing nodes use selective bpatch files. Missing
metadata or unsupported cleanup connections fail export rather than producing
a partial repair. JournalQuestPrototypes.cfg.bin is now a required extraction
input, and CACHE_SCHEMA is 26. Parsing remains lazy and default settings emit
no patches.

## External story cancellation: corrected in 1.37.3

The post-release review found a missed writer outside the job containers:
`Zalesie_Hub_SetJournal_RSQ01` cancels the original Warlock journal when the
story's Stage3 condition is met. Version 1.37.2 remapped only nodes inside
the job subquests, so this action did not target any of their six new journals.

The builder now discovers external quest-journal cancellation actions for
the original job journals. For each new journal it adds an If/SetJournal pair
in the **story owner's quest**, which survives shutdown of the job container.
The If copies the original story launchers, including their conditions,
and additionally requires the new journal to be Active. The cancellation
action runs only on that If's True output. Completed, cancelled and never
accepted journals are not changed; the original story action remains intact.
The current data adds six guards and six cancellations for Warlock.

The regression failed on 1.37.2 and passes after the correction. It checks
the actual emitted story inputs and all 4096 combinations of six journal
states, including inactive jobs, missing story triggers and repeated events.
It checks config wiring and state decisions, not the engine or a save file.
No new extraction input or cache-schema change is needed.
All 48 local headless suites and the 9 CI suites passed for 1.37.3 before
release preparation. No new GUI or game test was performed.

The review also found seven old parent JournalIsCleared conditions. Those
alone do not prove a normal-cancellation hang: all 69 jobs have alternative
non-excluding launcher paths from their cancellation to their own End.

Rebuild the generated pak to obtain this correction. For testing, use a save
from before accepting jobs. Recovery of saves already past the story event
is not promised.

## Limits and verification

- This cannot migrate jobs accepted with an older pak. Start from a save before
  accepting jobs, and keep the generated pak while its jobs are active. Journal
  and quest state is saved by the game; removing a pak is not a save rollback.
- Custom journal registration, localized titles, markers, save/reload behavior,
  independent rewards and subsequent rounds still need engine verification.
- Other mods changing the same quests/journals may conflict. Separate generated
  paks using this feature share its namespace and must not be combined.
- Automated tests check emitted references, preserve reward/launcher data, and
  model 536 ordered pairs of job hand-ins, cancellation and subsequent rounds.
  That model is a regression check, not an emulation of the game's quest engine.

The decisive eventual game check is two jobs from one giver: complete both,
hand in either one first, receive both rewards, then get the next round. Also
check one unfinished sibling, cancellation, and save/reload between hand-ins.

Historical 1.37.2 validation: all 47 headless suites passed in 1.2 minutes, all
9 CI suites passed, and the portable self-test passed. The preview's 26 Python
source files match the workspace; all 19 runtime binaries match the published
1.37.1 runtime byte-for-byte and have valid signatures. No GUI or game test
was performed in this session.
