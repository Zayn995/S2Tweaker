# Optional loot and world controls (v1.37.0)

The following additions are available through **World → Edit loot & world settings**
or **Overview → Loot & world**. Their values are edited in a paged list so the
application does not allocate 85 additional hidden sliders at startup. Search,
favorites, presets, undo/redo and conflict avoidance use the same settings.
They use the installed
game's current configuration data. All switches start off; multipliers start
at 100%. Leaving the tool at its defaults produces no patch.

| # | Addition | Scope |
|---|---|---|
| 1 | Extra stash finds | Separate artifact, weapon, armor/helmet and attachment rolls with adjustable chance in vetted ordinary world stashes. |
| 2 | NPC armor loot | An extra usable armor roll from the same ordinary faction/rank equipment pool. It does not copy the exact worn outfit. |
| 3 | Armor loot condition | Independent minimum and maximum for these extra drops. |
| 4 | Loaded ammunition | Ammo already in generated NPC weapons, separate from loose ammo and loot stack amounts. |
| 5 | NPC equipment variety | Earlier-rank equipment remains eligible within the same faction and equipment category. |
| 6 | NPC helmet chance | Scales existing optional helmet rolls; guaranteed equipment lists keep their mechanism. |
| 7 | Vegetation visibility | AI translucency of grass and leaves. |
| 8 | Surface movement noise | Separate controls for the game's 29 current physical surface types. |
| 9 | Weather luminance | Nine weather-specific contributions to AI visibility, separate from screen brightness. |
| 10 | NPC dispersion distance | Experimental `FireDistanceDispersion` control for NPC weapons. |
| 11 | Mutant looting comfort | Reach, upper interaction height, access down to ground level, and an experimental cut-radius control. |
| 12 | Mutant trophy weight | Dedicated multiplier for the 14 current native trophies. |
| 13 | Mutant trophy base value | Separate from trader buying/selling multipliers. |
| 14 | Trophy drops by species | Chance and quantity for each of the 14 current species; combines with global loot settings. |
| 15 | Blood/projectile marks | Lifetime and decal capacities for the world, agents and corpses. |
| 16 | Permanent Weird Flower effect | Adds the existing permanent stealth/flair effect; independent of duration. |
| 17 | Hercules field repair | Optional native effect bonus for body armor, helmet and equipped weapon slots; 0–25% each. |
| 18 | Thrown bolt lifetime | Persistence of thrown bolts; no new collectible-bolt system. |

## Patch behavior and compatibility

Existing structures receive selective `{bpatch}` changes. Additional stash and
NPC armor generators use namespaced new structures and named sibling entries.
Their identifiers include the chosen mod name and a stable hash. Brand-new
structures necessarily have no `{bpatch}` header, because they have no existing
target to merge into. No foreign full configuration files are bundled.

Extra stash generators attach to vetted spawn instances; shared GamePass stash
pools are not replaced. Quest/edition restrictions, unsafe nested generators,
currency and unique items are checked against current game data. The large spawn
file is extracted only when building with extra stash finds enabled. Binary roots
are decoded one at a time; only container records are retained in a separate
optional index. The temporary binary is removed on success or failure. Schema 25
removes this source from the normal startup cache. The index is never presented
to conflict scanning as a complete vanilla SpawnActorPrototypes configuration.

The mod scan now checks loot identities at their actual array positions and
distinguishes selection weights from item weight. This catches changes such as
EML moving trophy entries, which a comparison of numeric value sets can miss.
It also distinguishes independent native effect-list appends from replacing or
reordering the same item's effects, covering Hercules and Weird Flower.
The scan reports conflicts; it is not a system for merging all active mods into
an effective baseline. `{bpatch}` cannot guarantee compatibility with a mod that
replaces the same list or assigns a different meaning to the same array index.

Global/specific interaction and trophy multipliers compose. If their combined
result is neutral, the affected value is omitted instead of writing vanilla
back over another mod. UI values use the existing preset, reset, search and
conflict-avoidance mechanisms.

## Validation limits

Headless checks cover current-data targeting, ordered bounds, new references,
quest/unique-item exclusions, namespace separation, list preservation, neutral
defaults, factor composition, UI collection and generated Pak contents.
For v1.37.0, all 43 headless suites passed. The generated sample Pak was
read back successfully (69 files, including 68 cfg files). The local preview
reuses the existing PSF starter byte-for-byte; all 19 bundled binary files have
valid signatures. No game or interactive GUI test is part of this work.

Actual in-game behavior remains unverified, especially NPC dispersion distance,
cut radius, permanent Weird Flower behavior and negative-corrosion repair.
Hercules keeps its original effects; repair is an explicitly optional bonus,
not a new localized repair-kit item. Existing containers/inventories may already
have generated their contents. No animation-speed desynchronization fix is
claimed.

The additions require no new injector, runtime DLL, executable, network feature
or bundled third-party mod asset. MCM and features beyond this list are not
included.

Further targeting details: [loot implementation](LOOT_EXTENSIONS_IMPLEMENTATION.md),
[stash research](STASH_VARIETY_RESEARCH.md), [loot research](LOOT_MODS_RESEARCH.md).
