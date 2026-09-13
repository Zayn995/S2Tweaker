# Control patch compatibility — 1.43.0

## Independent settings

NPC alertness changes only the minimum threat thresholds for reaction actions.
NPC search time changes only the default and action-specific threat freeze times
and decay rates. They do not need to write the same values.

The previous generator copied the complete indexed DefaultNPC profile for either
control. A separate search-time Pak therefore repeated vanilla alertness values,
and a separate alertness Pak repeated vanilla search timing. The current generator
addresses the existing profile and action indices with recursive `{bpatch}` structs,
omitting identifiers, event definitions and unchanged action fields.

Rain frequency, emission frequency and weather duration had the same problem in
indexed weather templates. They now also write only their affected leaves.
Regional/global factors that intentionally affect the same weather value still
compose during a single build. Different Paks assigning different values to the
same leaf remain a conflict; this change cannot reconcile incompatible choices.

## Wider control audit

The same unnecessary row copies also occurred outside NPC threat settings.
Existing indexed nodes now receive only their changed values in these families:

- NPC flashlight brightness/reach and cone width; human/mutant hearing and movement noise.
- Radiation dose, screen filter and Geiger intensity.
- Weapon jam probability and jam-clearing time.
- Per-scope zoom and handling-effect references.
- Wounded/dead encounter fractions, squad limits, expansion and camp activity rates.
- Weather sense details, transition speeds, surface noise and marker reveal settings.
- Landing thresholds, grenade resistance, sprint stamina drain and reputation repair modifiers.
- Effect caps, carry thresholds, artifact cache weights and repeatable-job conditions/connections.

Additional artifact bonuses now append only the new effect/display slots. Existing
bonus selections are preserved, and fake/quest descendants still receive the
necessary explicit shields against inherited new bonuses. Newly created effect,
equipment and quest nodes retain their required definitions.

Caps and zero baselines are compared numerically, so formatting differences such
as `0` versus `0.0` do not cause an assignment. Carry-cap values and indices now
come from the installation instead of fixed example values. These corrections
change config output only; they do not change animations or add a runtime dependency.

### Intentional overlaps remain

Carry capacity and the start of overweight penalties jointly determine the
intermediate thresholds. Global and individual multipliers may also intentionally
affect the same value. Configure these together in one export; separate Paks
cannot combine two competing numeric assignments automatically.

Two mods adding bonuses to the same artifact may use the same new slot. Build
those additions together. Sparse output avoids restoring existing bonuses but
does not make competing list additions compatible. New-node definitions and
replacement localization files likewise require conflict checks.

### Updating existing Paks

1. Rebuild every affected Pak with the corrected generator. Paks from 1.42.0 and
   earlier still contain the full profiles and can overwrite the new settings.
2. Give separately generated mods different names so their internal patch filenames
   are distinct. Renaming only a Pak does not rename the files inside it.
3. Remove the superseded Paks, then scan the installed mods again. Old complete
   profiles should still be reported as conflicts.

One combined Pak remains supported. No UE4SS or Zone Kit is needed to generate it.

## Extended damage-mercy weights

The normal **Hidden damage mercy** mode scales both curve weights from each
installed difficulty and caps the result at 1.0. This preserves existing presets.
Profiles already at 1.0 have no room to increase in that mode, so they are omitted
when the requested result would still be 1.0.

**Allow damage-mercy weights above 1.0 (experimental)** removes the tool's cap.
For example, at 300%, a live weight of 1.0 becomes 3.0. The builder now resolves
inherited as well as explicit values, including custom and platform profiles.
Zero stays zero, missing values are not invented, and unchanged results are omitted.
At 100%, enabling the option alone creates no patch.

The setting controls curve weights, not a direct percentage of protection. The
engine's behavior above 1.0 has not been established; it may clamp the values or
interpret them unexpectedly. Extended mode defaults to off. Non-finite or negative
multipliers are rejected instead of writing invalid values.

## Evidence and remaining checks

GSC documents `{bpatch}` as preserving unlisted child values and replacing listed
ones, without a separate exception for explicit numeric node names. This is the
format used here. The earlier whole-profile copy was a precaution for unverified
index behavior, rather than a demonstrated engine requirement.
[Official Config patches documentation](https://zonekit-support.stalker2.com/hc/en-us/articles/39357395461265-Config-patches).

Regression tests check disjoint leaf paths, both NPC patch orders, all six weather
patch orders, preservation of unrelated values, Pak write/read roundtrips, legacy
conflict detection, inherited difficulty values, and capped/extended modes. The
merge-order checks implement the documented contract locally; they do not run
Unreal and are not in-game proof. Synthetic fixtures run in CI, and installed-data
checks exercise the actual local game baselines.

The wider regression suite also checks independent flashlight, radiation, jam,
encounter, camp, map and weather-detail writes against combined exports in every
order, detail/global cancellation without deleting sibling changes, live carry
caps at nonstandard indices, and preservation of artifact inheritance shields.

Before claiming in-game compatibility, compare one combined Pak against both
orders of the two separately named NPC Paks. Check that NPC reactions/searches
still work and unrelated threat events are intact. Weather needs an equivalent
test across several transitions. Compare extended damage mercy at 100% and 300%
on Easy/Custom and inspect damage behavior before treating it as confirmed.

Reports: [search-time/alertness overlap](https://github.com/Zayn995/S2Tweaker/issues/13#issuecomment-5647985198),
[damage-mercy output](https://github.com/Zayn995/S2Tweaker/issues/20).
