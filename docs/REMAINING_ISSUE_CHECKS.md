# Remaining issue checks — 1.39.0

## Maximum talk distance (#10)

Open **Vaulting → Interaction reach**. Leave **Talk distance (minimum & maximum)**
at **100%** and set **Maximum talk distance only** to **180%** (range 100–300%).
The new control extends each participant's installed maximum without changing
the minimum. It covers the player and human NPCs, excluding mutants.

The earlier control still scales both bounds, so existing profiles retain their
behavior. If both controls change, their factors multiply for the maximum;
only the earlier control affects the minimum. A result equal to the installed
value is omitted from the patch. Reset both controls to 100% for no distance patch.

Synthetic and live-data checks cover neutral output, old settings, per-NPC
baselines, numeric suffixes, combined factors, cancellation to vanilla and
missing values. The new maximum-only behavior has **not been play-tested**.
The earlier shared-distance control has craigduk76's confirmation on 1.37.1.

For a game check, compare the same ordinary NPC and trader from the same save:
first without the test pak, then with only the maximum at 180%. Approach from
far away and check the farthest interaction point, then check the closest
interaction point. The maximum should increase while the minimum stays the same.
Restart the game between pak changes and keep other interaction mods out of
the comparison. Record game version, NPC/location and both observations.

## Multiple jobs (#9)

The repair in 1.37.2/1.37.3 is included unchanged. Config tests cannot establish
that the game's journal registration, rewards and save/reload behavior work.
See [repair details and save restrictions](REPEATABLE_JOBS_REPAIR.md).

Use a copy of a save from **before accepting the jobs** and enable only
**Accept several jobs from one giver (experimental repair)** in Economy.
Leave the round size and cooldown at
vanilla initially; use a giver whose round offers at least two jobs. Interact
again to accept the second job: the dialogue does not open automatically.

1. Complete both jobs. Record money, hand in one and check that the second
   journal and hand-in option remain. Hand in the second and check its reward.
2. Repeat from the original save with the other hand-in order.
3. Repeat with the second objective unfinished when handing in the first.
4. Save/reload between the two hand-ins and verify the remaining job survives.
5. From a separate copy, test cancellation: the shared line cancels all current
   jobs from that giver. Check the next round after the configured cooldown.

Keep the generated pak while its jobs are active. Do not use these tests to
overwrite the only copy of a playthrough. Removing the pak does not roll back
saved quest state. Report the giver, order, journal state, each reward and whether
the next round appears. Until these observations exist, #9 remains open.

## A-Life (#19)

The Quieter Zone report changes four settings together. It supports that
combination, but does not isolate any one slider. These separate comparisons
are still needed; use a backed-up save and the same route/time span for each.
Restart after switching paks and compare several runs because encounters vary.

| Test | Only changed setting | Observe |
| --- | --- | --- |
| Respawn | Lair respawn speed 25% | Time until a known cleared lair repopulates |
| Refill | Lair refill cooldown 400% | Time before a partially depleted lair refills |
| Encounters | Random encounters frequency 25% | Encounters over the same route and in-game time |
| Expansion | Lairs expand toward you 25% | Repeated expansion behavior around the same lairs |
| Agent cap | Max simultaneous NPCs & mutants 200% | Frame times, stutters, crashes and observable population |

Use one test pak at a time, with all other settings at vanilla. Keep quest and
NPC population changes from other mods out of the comparison. A 200% agent cap
doubles the installed value; it does not set an absolute population of 1000 or
guarantee that the game spawns enough agents to reach the cap. An unchanged FPS
reading below the cap does not prove that increasing the cap has no cost.

No performance or stability conclusion about another mod is established by
this report. #19 remains open for the continuing observations.
