# External job references: acquisition and comparison

Historical review of Nexus mods 2638 and 2482, dated 11 September 2026.
This compares source/data evidence and does not establish in-game behavior.

## Material available

| Reference | Evidence obtained | Practical use |
| --- | --- | --- |
| [Multiple Radiant Quests, 2638](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2638) | Existing local version-1 archive from 7 September; all ten Pak entries extracted privately and inspected. The live page still lists version 1. The supplied Google share link resolves to this same mod. | Giver-marker and dispatch lifecycle patterns; comparison with original game data. |
| [Double Quest Rewards, 2482](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2482?tab=files) | Live file list, archive preview and changelog. The current 2.0.5 hotfix was uploaded on 11 September. Preview lists a README and a 2.3 KB Pak. Its payload was **not downloaded or inspected**; Nexus requires login for that download. | Confirm the author's change from a root database replacement to an additive patch; compare our own output against the game data. |
| Installed game data | Native quest nodes, dispatcher inputs and difficulty values. | Establish actual supported fields and distinguish references from engine guarantees. |

The existing downloaded 2638 source remains in private local research storage.
No foreign mod files were installed in the game or copied into S2Tweaker's
production/source distribution. No account or credentials were needed for the
useful local archive and public metadata review.

## Findings

See [native giver-marker research](JOB_GIVER_MARKER_RESEARCH.md) and
[the complete 2638 graph comparison](JOB_REFERENCE_2638_REVIEW.md).

- Availability markers and journal return markers use different node mechanisms.
  A giver icon is not evidence that a completed sibling's objective marker has
  been repaired. The reference contains no journal/localization resource files.
- A future available-work indicator needs the actual live menu/slot conditions.
  The reference's held-job cap alone does not establish that an offer exists.
- The local cross-hub dispatch data disagrees with the advertised probability;
  the detailed graph review records the actual weights and their limits. It is
  not a verified cross-region feature to transplant into the tool.
- The [2638 author's warning and player reports](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2638?tab=posts)
  still describe hand-in restrictions and lost future offers. These are reports,
  not tests of S2Tweaker or proof of their precise cause.

## Reward output comparison

The [2482 hotfix changelog](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2482?tab=description)
describes rebuilding as an additive prototype patch to address startup crashes.
S2Tweaker already emits `DifficultyPrototypes/DifficultyPrototypes_patch_<name>.cfg`
under the GameData directory, not the root `DifficultyPrototypes.cfg` database.

A focused local export checked both money multipliers against all eleven loaded
difficulty definitions (22 values), using 2x their current resolved values.
Every emitted node and nested economy struct has `bpatch`; only the two reward
keys change. Neutral settings emit nothing. The Pak contains exactly that one
expected patch file, and its payload was read back byte-for-byte. This validates
our output, without claiming that the external 2.0.5 payload was inspected or
that new rewards were measured in the game.

Private evidence: `out/issue9_reference_deepening/reward_check.json` and the
two research subdirectories referenced by the detailed reports. The previously
prepared all-language and guarded-return-marker repair is unchanged by this review.
