# Repeatable jobs: experimental hand-in repair

Included in version 1.37.2, 11 September 2026. Not play-tested.

## Report and diagnosis

[Molkerr's latest report](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5622646388)
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
has no explicit title, the existing localized start-objective description is
used. The source journals remain unchanged. Nested conditions are remapped too;
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

Final local validation: all 47 headless suites passed in 1.2 minutes, all
9 CI suites passed, and the portable self-test passed. The preview's 26 Python
source files match the workspace; all 19 runtime binaries match the published
1.37.1 runtime byte-for-byte and have valid signatures. No GUI or game test
was performed in this session.
