# Repeatable jobs: experimental hand-in repair

Introduced in version 1.37.2; story cancellation corrected in 1.37.3,
11 September 2026. Partially player-tested on 1.39; further repairs after the
1.40 report are available in test release 1.40.1-rc.1 and require game tests.

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
[Molkerr's 1.40 follow-up](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5639882302)
reports that the missing texts and the disappearing completed-sibling marker both
persist. The supplementary resource attempt in 1.40 is therefore not a confirmed
fix. Both new videos were sampled in the browser: internal job keys remain
visible, including the return-stage key in the second video. The report remains
open. The current development revision below preserves every existing journal
and stage identifier.

## Native translations (1.40.1-rc.1 test release)

`build_root_files` pairs the actual isolated journal/stage keys with their original
keys and reads the translations from the currently loaded installation. On 2.0.5
this discovers 18 installed cultures and produces 208 aliases in each language.
Discovery is dynamic, including additional cultures if the installation provides
them; there is no English/Russian or fixed 18-language limit.

Each native `Stalker2/Content/Localization/Game/<culture>/Game.locres` is extended
in its original format. Existing key records and translated string bytes remain
exact; new aliases reuse original string slots. Native version-3 hashes and
reference counts are handled explicitly. See the [all-language audit and format
evidence](JOB_LOCALIZATION_LOADING_FOLLOWUP.md).

This overrides complete resources. On the audited installation the translations
alone add about 147 MiB to an uncompressed Pak; compression for sharing reduces
the private ZIP to about 37 MiB. **Other mods replacing the same Game.locres files
conflict.** A cfg-only mod scan does not detect this conflict. No game translations
ship with the app or its source archive; they are generated locally.

An optional version-2 ZIP cache stores the generated files with exact culture
membership and per-file size/hash checks. Its identity includes the source Pak
stamp and alias map. Damaged caches rebuild; changed game files require reloading.
Old version-1 alias caches are not used. Neutral settings do not extract or emit
localization files; no global cache-schema change is required.

Preview lists the language files; normal Pak export, verified replacement and debug
export handle their binary content without newline conversion. The generated texts
match the independently constructed native candidate in all 18 languages.
Actual loading/rendering still requires a game test in multiple languages,
including native English, Russian and the owner's language. Also check ordinary
quests and menus. Binary equality does not prove visible text is fixed.

## Remaining marker case

The [original marker audit](JOB_MARKERS_RESEARCH.md) found that all 318 original
marker-bearing nodes retained their marker settings. Ready-to-return jobs use
their giver's shared actor GUID. The [follow-up audit](JOB_COMPLETED_MARKER_FOLLOWUP.md)
found native quests reapplying a marker to an already active stage.

The 1.40.1-rc.1 candidate adds 69 checks and 69 separate reapplication nodes. After a
job container ends, each remaining journal AND its return stage must be Active
before its existing marker payload is reapplied. Original reward/dialog outputs
are not reused, completed/failed/cancelled jobs are excluded, and tracking is not
forced. Native patterns justify this experiment but do not prove the shared-marker
problem is fixed or that repeat notifications are absent.

Test two ready-to-return jobs: hand in either first, check the other's journal,
map/compass and reward, then save/load. Repeat the reverse order and compare an
unfinished sibling. Start before hand-in; the patch does not promise retroactive
recovery for an already lost marker. Test translations separately first if
diagnosing loading, so marker behavior cannot be attributed to changed text.

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
