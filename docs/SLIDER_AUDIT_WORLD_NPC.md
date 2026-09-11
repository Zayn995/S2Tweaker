# World and NPC slider expansion audit

Research only, 2026-09-11; current application 1.40.1, installed-data snapshot
2.0.5. No application changes, game installation or gameplay tests were made.
This is a bounded review of world/NPC controls, not the inventory of every
S2Tweaker control. The strongest opportunities are more selective controls over
already supported mechanisms, rather than larger global slider limits.

## What already exists

| Area | Current controls; these are not new proposals |
| --- | --- |
| Human combat | Damage/health, accuracy and dispersion, vision/hearing/reaction, grenade usage, regeneration, retreat, wounded state, target selection, cover, alertness/search/courage/stagger; global weapon AI burst, guaranteed-hit shots, pauses and engagement distance |
| Stealth | Darkness, crouching and movement noise, combined weather penalties, flashlight detection, vegetation transparency, surface noise and separate weather luminance factors |
| Equipment | Global quality/condition/ammo/helmet chance, lower-rank variety, extra armor loot; individual weighted weapons/pistols/body armor for 50 ordinary roles across 12 factions and player-progression groups |
| A-Life | Agent cap, spawn/grid distances, human/mutant lair populations, refill and occupancy, encounters and six mutant encounter families, squad expansion, global faction battle chance/pace, one combined camp-life control |
| World | Global rain/emission/day/weather durations and transitions; regional weather weights/durations, corpse/item persistence, travel; experimental sky/night controls |
| Loot/traders | Smart loot amount/chance/ammo/variety/clues; filtered ordinary generator amounts, extra stash categories, trader stock/variety/restock/money/prices and purchase restrictions |

Code reviewed: `s2tweaker/gui.py`, `s2tweaker/tweaks.py`,
`s2tweaker/extension_controls.py`, `s2tweaker/world_extensions.py`,
`s2tweaker/loot_extensions.py`, `s2tweaker/npc_equipment.py`,
`s2tweaker/npc_equipment_scope.py` and `s2tweaker/gamedata.py`.
See also [NPC equipment scope](NPC_EQUIPMENT_SCOPE.md) and
[composition](NPC_EQUIPMENT_COMPOSITION.md).

## Priorities

| Priority | Extension | Player benefit | Effort and evidence |
| --- | --- | --- | --- |
| 1 | Separate camp activities | More guitar/jokes/conversation without also making every NPC sleep/eat more often | Small-to-medium; existing generator, 88 relevant entries in a narrower 12-profile pilot |
| 2 | Separate weather effects on sight, hearing and scent | Tune rain noise independently from fog visibility or mutant scent | Small-to-medium; six native weather entries, 18 explicit values |
| 3 | Grenade budgets by native group and rank | Reduce army grenade spam without changing every other ordinary group equally | Small; 12 ordinary integer values; global/fallback scope must be disclosed |
| 4 | Optional helmets in the faction equipment editor | Give one role/progression group a different helmet chance, independent of the global chance | Medium; 23 existing chance entries across audited equipment sources; retain clone/relink boundary |
| 5 | Advanced NPC firing profiles by rank and distance | Longer pauses at long range or weaker novice opening bursts without equally weakening experts at close range | Medium-to-large; 77 global profiles exist, three-profile pilot fully enumerated below; expand only after consumer audit |

Night-vision equipment generation is an additional research lead under priority
4, not a promise of improved NPC night vision. Regional weather selection and
faction equipment weights are already implemented and should not be marketed
as new features.

## Source inventory

All paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`.
Line counts refer to decoded local CFG text; top-level counts use the existing
CFG parser. Source hashes and complete private audit output are kept in
`out/slider_audit_1401/world_npc/audit.json`.

| CFG | Lines | Top-level structs |
| --- | --- | --- |
| NPCNeedsPresetPrototypes.cfg | 3862 | 26 |
| AIGlobals.cfg | 779 | 2 |
| ItemGeneratorPrototypes.cfg | 277353 | 3086 |
| WeaponData/WeaponAttributesPrototypes.cfg | 26603 | 148 |
| ObjPrototypes.cfg | 1318780 | 1660 |
| ItemPrototypes.cfg | 92232 | 1375 |
| ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg | 617 | 1 |
| WeatherSelectionPrototypes.cfg | 4230 | 45 |
| WeatherChainPrototypes.cfg | 319 | 18 |

All files required by the five bounded candidates are already in
`NEEDED_FILES`; these candidates alone need no extraction or cache-schema
change. A future consumer audit may discover additional inputs; adding any
required extraction input must also increment `CACHE_SCHEMA`.

## 1. Camp activities separately

Current `_needs_patch` scales both rate leaves for all eight `CAMP_LIFE_NEEDS`
using one factor. There are 168 matching entries in 25 non-empty presets. That
includes guard, quest, mutant and zombie presets; their presence must not be
mistaken for ordinary stalker camp activity. This is a scope observation, not
evidence of a gameplay defect in the released control.

Proposed first scope: the 12 presets marked **pilot** below, 88 existing
entries, using eight independent activity factors. Continue to offer the
existing global control, but multiply its result by the selected detail factor
only for these pilot entries. Each activity occurs only where the native preset
already has it. No zero-rate activity is invented and no absent activity is
added. This can be presented as a small activity editor, without 96 permanent
sliders on the main page.

The patch paths are `<Preset>.Needs.<index>.IncreaseRateMin` and
`<Preset>.Needs.<index>.IncreaseRateMax`; each table cell below gives
`index: minimum/maximum`. A dash means absent, not zero. Select entries by
`NeedType = EContextualActionNeeds::<activity>`, and find the current index at
load time. Root inheritance is listed in the table; all selected rows have
empty attributes and both rates explicitly present. Preserve the complete
native row, including `NeedType`, `Radius` and `MaxCount`. The shared
`HumanGenericNeedsPreset` parent stays outside the pilot. Validate shielding
of each inherited guard child before accepting its parent's numeric edit.
In this snapshot, all 59 relevant rows across the eight direct guard children
explicitly repeat the matching activity and both rate leaves; the private
validation checks each pair. Repeat this check against loaded game data rather
than relying on these counts after an update.

These are need accumulation rates, not a direct number of performances per
minute. Availability of an action spot, ongoing behavior and threats still
matter. Native ordinary values differ: Neutrals' guitar 5/15 is not the generic
4/6, while several restricted profiles use 1/2. For example, generic guitar
4/6 multiplied by 1.5 gives 6/9; its sleep rates remain unchanged when only
guitar is edited.

Do not include `QuestNPCNeedsPreset`, guard suffixes, the two mutant presets,
`ZombieNeedsPreset`, shared `HumanGenericNeedsPreset` or empty `[0]` in the new detail mode. Keep emission,
patrol, work, guard duty, radius and occupancy limits unchanged. Shared ordinary
presets can still be used by mission NPCs, so this is not absolute quest
isolation. Confirm activity changes in game without claiming timing guarantees.

| Preset | Root inheritance | New detail scope | Guitar | Anecdote | Dialog | Smoke | Sleep | Eat | Rest | Drink |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BanditsNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | [6]: 1.5f/3.f | [14]: 1.f/2.f | [12]: 1.f/2.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| BanditsNeedsPreset_Guard | refkey=BanditsNeedsPreset | exclude | [6]: 1.5f/3.f | [14]: 1.f/2.f | [12]: 1.f/2.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| CorpusNeedsPreset | — | pilot | [6]: 1.f/2.f | [15]: 1.f/2.f | [13]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 1.f/2.f |
| DutyNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | [6]: 1.f/2.f | [15]: 3.f/6.f | [13]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 1.f/2.f |
| DutyNeedsPreset_Guard | refkey=DutyNeedsPreset | exclude | [6]: 1.f/2.f | [15]: 3.f/6.f | [13]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 1.f/2.f |
| FreedomsNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | [6]: 2.f/4.f | [15]: 2.f/4.f | [13]: 2.f/4.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| FreedomsNeedsPreset_Guard | refkey=FreedomsNeedsPreset | exclude | [6]: 2.f/4.f | [15]: 2.f/4.f | [13]: 2.f/4.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| HumanGenericNeedsPreset | — | exclude | [6]: 4.f/6.f | [15]: 3.f/6.f | [13]: 5.f/8.f | [3]: 6.f/8.f | [2]: 4.f/6.f | [5]: 3.f/4.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| MercenariesNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | — | [15]: 3.f/6.f | [10]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 1.f/2.f |
| MilitariesNeedsPreset | — | pilot | — | [13]: 1.f/2.f | [11]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 1.f/2.f |
| MilitariesNeedsPreset_Guard | refkey=MilitariesNeedsPreset | exclude | — | [13]: 1.f/2.f | [11]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 1.f/2.f |
| MonolitNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | — | [15]: 3.f/6.f | [13]: 5.f/8.f | — | [2]: 1.f/3.f | [3]: 1.f/2.f | [1]: 1.f/2.f | — |
| MonolitNeedsPreset_Guard | refkey=MonolitNeedsPreset | exclude | — | [15]: 3.f/6.f | [13]: 5.f/8.f | — | [2]: 1.f/3.f | [3]: 1.f/2.f | [1]: 1.f/2.f | — |
| MutantGenericNeedsNoExpansionPreset | — | exclude | — | — | — | — | [1]: 1.f/2.f | [2]: 1.f/2.f | — | — |
| MutantGenericNeedsPreset | — | exclude | — | — | — | — | [1]: 1.f/2.f | [2]: 1.f/2.f | — | — |
| NeutralsNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | [6]: 5.f/15.f | [15]: 3.f/6.f | [13]: 3.f/6.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| NeutralsNeedsPreset_Guard | refkey=NeutralsNeedsPreset | exclude | [6]: 5.f/15.f | [15]: 3.f/6.f | [13]: 3.f/6.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 2.f/4.f | [4]: 2.f/4.f |
| NoonNeedsPreset | — | pilot | — | [13]: 2.f/4.f | [11]: 2.f/4.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [4]: 1.f/2.f | [1]: 1.f/2.f | — |
| NoonNeedsPreset_Guard | refkey=NoonNeedsPreset | exclude | — | [13]: 2.f/4.f | [11]: 2.f/4.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [4]: 1.f/2.f | [1]: 1.f/2.f | — |
| QuestNPCNeedsPreset | — | exclude | — | — | — | [2]: 6.f/8.f | [8]: 4.f/6.f | [4]: 3.f/4.f | [1]: 2.f/4.f | [3]: 2.f/4.f |
| ScientistsNeedsPreset | — | pilot | — | [10]: 1.f/2.f | [8]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | — | [1]: 1.f/2.f | — |
| SparkNeedsPreset | — | pilot | [6]: 1.f/2.f | [15]: 1.f/2.f | [13]: 1.f/2.f | [3]: 2.f/4.f | [2]: 1.f/2.f | [5]: 1.f/2.f | [1]: 1.f/2.f | [4]: 2.f/4.f |
| VartaNeedsPreset | refkey=HumanGenericNeedsPreset | pilot | — | [15]: 3.f/6.f | [11]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [4]: 1.f/2.f | [1]: 1.f/2.f | — |
| VartaNeedsPreset_Guard | refkey=VartaNeedsPreset | exclude | — | [15]: 3.f/6.f | [11]: 1.f/2.f | [3]: 1.f/2.f | [2]: 1.f/2.f | [4]: 1.f/2.f | [1]: 1.f/2.f | — |
| ZombieNeedsPreset | refkey=HumanGenericNeedsPreset | exclude | — | [15]: 3.f/6.f | [13]: 5.f/8.f | — | [2]: 1.f/2.f | — | [1]: 1.f/2.f | — |

## 2. Weather-specific sight, hearing and scent

The existing `weather_stealth_factor` changes all three penalty types together
in `_aiglobals_patch`. The independent weather luminance editor is a different
mechanism and does not replace these coefficients. The six native rows below
contain all 18 values in this bounded set; all are explicit and have no
inheritance attributes.

Paths: `AISettings.WeatherSettings.<index>.VisibilityCoef`,
`.HearingDistanceCoef`, `.FlairCoef`. Match `WeatherSID`, not a remembered index.
The spellings `Clearly` and `Fogy` are native identifiers. Do not add Stormy,
Emission or other weather rows simply because those exist in another table.

| Index | WeatherSID | VisibilityCoef | HearingDistanceCoef | FlairCoef |
| --- | --- | --- | --- | --- |
| [0] | Clearly | 1.0 | 1.0 | 1.0 |
| [1] | Cloudy | 0.95 | 1.0 | 1.0 |
| [2] | Fogy | 0.7 | 0.7 | 0.7 |
| [3] | Rainy | 0.9 | 0.7 | 0.65 |
| [4] | LightRainy | 0.95 | 0.7 | 0.9 |
| [5] | Thundery | 0.8 | 0.6 | 0.45 |

A compatible editor can expose the strength of each existing penalty, with
100% inheriting the global weather slider. Use its existing formula once:
`max(0.05, min(1, 1 - (1 - native coefficient) * global * detail))`.
For Rainy hearing 0.7, global 1 and detail 2 produces 0.4; the visibility stays
0.9 when its detail factor remains 1. Detail zero removes that particular
weather penalty (coefficient 1), not all hearing. A native coefficient of 1
remains 1; do not silently create a clear-weather penalty.

Use precise labels: sight, hearing and scent. Scent may also affect mutants;
the shared AI table cannot isolate ordinary humans from bosses or story NPCs.
Existing general sensor/range controls also apply. This does not change the
rendered weather or visual brightness. It needs a controlled in-game stealth
comparison, including unchanged clear weather and unedited senses.

## 3. Grenade budgets by native group and rank

Current `npc_grenade_factor` multiplies every non-negative integer in one
table. A small matrix can expose its ordinary groups independently. These are
the **complete** rows, including the excluded boss sentinel:

| Group | Newbie | Experienced | Veteran | Master | Scope |
| --- | --- | --- | --- | --- | --- |
| KorshunovBoss_Faction | -1 | -1 | -1 | -1 | exclude: unlimited sentinel |
| Bandits | 0 | 2 | 3 | 4 | candidate |
| Army | 3 | 5 | 8 | 13 | candidate |
| Humanoid | 0 | 3 | 5 | 8 | candidate |

Exact path:
`AISettings.ThrowGrenadeSettings.AvailableGrenadesPerFaction.<group>.<rank>`.
All 16 leaves are explicit, with no `refkey`/`refurl`. There are three ordinary
native groups, not twelve equipment factions. `Humanoid` is a parent/fallback
group, so do not advertise isolated controls for every faction without
establishing the engine's group selection. These are native rank buckets; the
equipment editor's `PlayerRank` masks are a separate system.

An inherited percentage control can keep the existing global result and apply
one local multiplier before integer rounding. With global 1, Army Veteran 8
at 50% gives 4 while Bandits Veteran remains 3. Preserve native zero budgets
and every negative sentinel. Fractional changes may round to no change; show
the resulting integer budget beside the slider. Never patch
`KorshunovBoss_Faction` or reinterpret -1 as a negative count. Other story NPCs
using ordinary/fallback groups can still be affected. Count allowed grenades
rather than promising an exact throwing frequency: tactical logic and inventory
may constrain actual throws. Runtime reset/refresh behavior needs a game test.

## 4. Optional head equipment in the existing faction editor

The existing individual editor includes weighted primary weapons, pistols and
body armor, and rejects `Chance` rows. A global optional helmet multiplier
already exists in `_npc_patches`. The actual gap is **selective** chance
controls on the existing cloned ordinary-role branch.

Across sources already enumerated in `npc_equipment_scope.SOURCES`, there are
23 `Head` chance rows and 47 `NightVision` chance rows, in 50 groups total.
There are no `Weight` rows in this selected head/night-vision set. Each source
has `refkey=[0]; refurl=../ItemGeneratorPrototypes.cfg`; every selected slot
and candidate is explicitly defined. Clone/relink only the modified ordinary
object's branch; never change shared armor/NVG helpers in place. Keep source
attributes and native rank/difficulty restrictions. Existing [scope and clone
rules](NPC_EQUIPMENT_RESEARCH.md) still apply.

First implementation should expose the 23 existing helmet rows in their
ordinary role contexts, with 100% inheriting global helmet chance and current
clone composition. The complete baseline is below. Path syntax is
`<source>.ItemGenerator.<slot>.PossibleItems.<row>.Chance`; the table lists
`slot/row`, `PlayerRank` mask and `GameDifficulty` restriction. A dash denotes
an absent restriction, not a new permission. Traverse enclosing routes to
compute the final restriction as the current editor does.

### Complete Head candidate baselines

| Source | Slot/row | PlayerRank | Difficulty | Item | Chance |
| --- | --- | --- | --- | --- | --- |
| GeneralNPC_Bandit_Armor | [2]/[0] | Experienced, Veteran, Master | — | Light_Bandit_Helmet | 0.3 |
| GeneralNPC_Corpus_Armor | [3]/[0] | Newbie, Experienced | — | Light_Military_Helmet | 0.3 |
| GeneralNPC_Corpus_Armor | [4]/[0] | Veteran | — | Heavy_Military_Helmet | 0.3 |
| GeneralNPC_Duty_Armor | [4]/[0] | Newbie | — | Light_Duty_Helmet | 0.3 |
| GeneralNPC_Duty_Armor_Experienced_var1 | [1]/[0] | — | — | Heavy_Duty_Helmet | 0.3 |
| GeneralNPC_Freedom_Armor | [4]/[0] | Experienced | — | Heavy_Svoboda_Helmet | 0.3 |
| GeneralNPC_Mercenaries_Armor | [4]/[0] | Newbie, Experienced | — | Light_Mercenaries_Helmet | 0.3 |
| GeneralNPC_Militaries_Armor | [3]/[0] | Newbie | — | Light_Military_Helmet | 0.3 |
| GeneralNPC_Militaries_Armor | [4]/[0] | Experienced | — | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Militaries_Armor_var2 | [1]/[0] | — | — | Heavy_Military_Helmet | 0.9 |
| GeneralNPC_Monolith_Armor | [3]/[0] | Newbie, Experienced | — | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator | [13]/[0] | Newbie, Experienced | — | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator | [14]/[0] | Veteran, Master | — | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Neutral_Recon_ItemGenerator | [12]/[0] | Newbie, Experienced | — | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_Recon_ItemGenerator | [13]/[0] | Veteran, Master | — | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Neutral_Sniper_ItemGenerator | [13]/[0] | Newbie, Experienced | — | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_Sniper_ItemGenerator | [14]/[0] | Veteran, Master | — | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Neutral_Stormtrooper_ItemGenerator | [9]/[0] | Newbie, Experienced | — | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_Stormtrooper_ItemGenerator | [10]/[0] | Veteran, Master | — | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Noon_Armor | [3]/[0] | Newbie, Experienced | — | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Noon_Armor | [4]/[0] | Veteran | — | Heavy_Military_Helmet | 0.3 |
| GeneralNPC_Spark_Armor | [3]/[0] | Newbie, Experienced | — | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Varta_Armor | [3]/[0] | Experienced, Veteran | — | Heavy_Varta_Helmet | 0.7 |

### Complete NightVision candidate baselines

| Source | Slot/row | PlayerRank | Difficulty | Item | Chance |
| --- | --- | --- | --- | --- | --- |
| GeneralNPC_Bandit_NVG | [0]/[0] | Master | — | NVG_NPC_Gen1 | 0.8 |
| GeneralNPC_Bandit_NVG | [0]/[1] | Master | — | NVG_NPC_Gen2 | 0.2 |
| GeneralNPC_Corpus_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.5 |
| GeneralNPC_Corpus_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Corpus_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Corpus_NVG | [2]/[0] | Master | — | NVG_NPC_Gen2 | 0.3 |
| GeneralNPC_Corpus_NVG | [2]/[1] | Master | — | NVG_NPC_Gen3 | 0.7 |
| GeneralNPC_Duty_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Duty_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.4 |
| GeneralNPC_Duty_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.1 |
| GeneralNPC_Duty_NVG | [2]/[0] | Master | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Duty_NVG | [2]/[1] | Master | — | NVG_NPC_Gen3 | 0.2 |
| GeneralNPC_Freedom_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Freedom_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.4 |
| GeneralNPC_Freedom_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.1 |
| GeneralNPC_Freedom_NVG | [2]/[0] | Master | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Freedom_NVG | [2]/[1] | Master | — | NVG_NPC_Gen3 | 0.2 |
| GeneralNPC_Mercenaries_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Mercenaries_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.4 |
| GeneralNPC_Mercenaries_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.1 |
| GeneralNPC_Mercenaries_NVG | [2]/[0] | Master | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Mercenaries_NVG | [2]/[1] | Master | — | NVG_NPC_Gen3 | 0.2 |
| GeneralNPC_Militaries_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Militaries_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.4 |
| GeneralNPC_Militaries_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.1 |
| GeneralNPC_Militaries_NVG | [2]/[0] | Master | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Militaries_NVG | [2]/[1] | Master | — | NVG_NPC_Gen3 | 0.2 |
| GeneralNPC_Monolith_NVG | [0]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Monolith_NVG | [0]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Monolith_NVG | [1]/[0] | Master | — | NVG_NPC_Gen2 | 0.3 |
| GeneralNPC_Monolith_NVG | [1]/[1] | Master | — | NVG_NPC_Gen3 | 0.7 |
| GeneralNPC_Neutral_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.7 |
| GeneralNPC_Neutral_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.5 |
| GeneralNPC_Neutral_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.2 |
| GeneralNPC_Neutral_NVG | [2]/[0] | Master | — | NVG_NPC_Gen1 | 0.2 |
| GeneralNPC_Neutral_NVG | [2]/[1] | Master | — | NVG_NPC_Gen2 | 0.6 |
| GeneralNPC_Spark_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 1.0 |
| GeneralNPC_Spark_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.8 |
| GeneralNPC_Spark_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.2 |
| GeneralNPC_Spark_NVG | [2]/[0] | Master | — | NVG_NPC_Gen1 | 0.1 |
| GeneralNPC_Spark_NVG | [2]/[1] | Master | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Spark_NVG | [2]/[2] | Master | — | NVG_NPC_Gen3 | 0.1 |
| GeneralNPC_Varta_NVG | [0]/[0] | Experienced | — | NVG_NPC_Gen1 | 0.5 |
| GeneralNPC_Varta_NVG | [1]/[0] | Veteran | — | NVG_NPC_Gen1 | 0.3 |
| GeneralNPC_Varta_NVG | [1]/[1] | Veteran | — | NVG_NPC_Gen2 | 0.5 |
| GeneralNPC_Varta_NVG | [2]/[0] | Master | — | NVG_NPC_Gen2 | 0.3 |
| GeneralNPC_Varta_NVG | [2]/[1] | Master | — | NVG_NPC_Gen3 | 0.7 |


For the Neutral recon Newbie/Experienced helmet, 0.3 at local 200% becomes
0.6 while its Veteran/Master 0.7 remains unchanged when unedited. Clamp valid
probabilities; do not turn these entries into relative weights or infer a drop
chance for worn armor. New NPC inventories may require new spawns. An ordinary
profile can appear inside missions, and named objects with original generator
links remain outside the clone by the established definition-level boundary.

Night-vision helper groups use `bAllowSameCategoryGeneration=false`; multiple
chance entries and their order require a separate probability/selection audit.
Their 27 group totals in this snapshot are at most 1, but that alone does not
prove normalization or independent-roll semantics. In particular, do not
multiply all chances into totals above 1 and call them weights. Preserving
all native groups and limiting edits conservatively still needs validation.

The NVG items are existing equipment identifiers (`NVG_NPC_Gen1/2/3`). Their
presence does **not** establish how NPC night vision functions, whether meshes
change or whether they become lootable. Earlier CFG investigations found NPC
night-vision appearance/behavior is not a simple sensor slider; this equipment
lead does not overturn that finding. Keep NVG controls behind additional
research rather than promise a night-vision AI feature.

## 5. Advanced NPC fire profiles

The global implementation already has four dimensions: guaranteed-hit shots,
burst length, fire pauses and engagement distance. It operates on 77
`*_NPC` definitions with direct AI profiles. The missing layer is selection
by behavior rank and Long/Medium/Short band, optionally scoped to a weapon
profile. Three ordinary profiles were fully enumerated here as a pilot:
`GunPM_HG_NPC`, `GunAK74_ST_NPC`, `GunM16_ST_NPC`. This is not a completed
consumer audit for all 77 definitions.

Every pilot has the five ranks shown below, with all edited rank and distance
leaves directly present. Each root references its matching `_Player` profile
via `refurl=PlayerWeaponAttributesPrototypes.cfg`; do not patch that parent.
For example, `GunAK74_ST_NPC` has `refkey=GunAK74_ST_Player`. Rank and distance
nodes themselves have empty attributes. Patch the NPC definition only.

Rank-level paths:
`<weapon>.AIParameters.BehaviorTypes.<rank>.CombatEffectiveFireDistanceMin`,
`.CombatEffectiveFireDistanceMax` and `.NonAutomaticWeaponShotDelay`.
Distances below retain native units (game coordinates), delays are seconds.
The last column records the native `CharacterWeaponSettingsSID` reference;
do not replace it when editing timing. These are weapon behavior ranks, not
the equipment generator's player-progression masks.

| Weapon | Rank | Engagement min/max | Non-auto delay | Weapon settings reference |
| --- | --- | --- | --- | --- |
| GunPM_HG_NPC | Newbie | 200.0/2500.0 | 0.3 | GunPM_HG_NPC |
| GunPM_HG_NPC | Experienced | 200.0/2500.0 | 0.3 | GunPM_HG_NPC |
| GunPM_HG_NPC | Veteran | 200.0/2500.0 | 0.3 | GunPM_HG_NPC |
| GunPM_HG_NPC | Master | 200.0/2500.0 | 0.3 | GunPM_HG_NPC |
| GunPM_HG_NPC | Zombie | 200.0/2500.0 | 0.3 | GunPM_HG_NPC |
| GunAK74_ST_NPC | Newbie | 1500.0/6000.0 | 0.2 | GunAK74_ST_NPC |
| GunAK74_ST_NPC | Experienced | 1500.0/6000.0 | 0.2 | GunAK74_ST_NPC |
| GunAK74_ST_NPC | Veteran | 1500.0/6000.0 | 0.2 | GunAK74_ST_NPC |
| GunAK74_ST_NPC | Master | 1500.0/6000.0 | 0.2 | GunAK74_ST_NPC |
| GunAK74_ST_NPC | Zombie | 1500.0/6000.0 | 0.2 | GunAK74_ST_NPC |
| GunM16_ST_NPC | Newbie | 1500.0/6000.0 | 0.2 | GunM16_ST_NPC |
| GunM16_ST_NPC | Experienced | 1500.0/6000.0 | 0.2 | GunM16_ST_NPC |
| GunM16_ST_NPC | Veteran | 1500.0/6000.0 | 0.2 | GunM16_ST_NPC |
| GunM16_ST_NPC | Master | 1500.0/6000.0 | 0.2 | GunM16_ST_NPC |
| GunM16_ST_NPC | Zombie | 1500.0/6000.0 | 0.2 | GunM16_ST_NPC |

Distance-level paths:
`<weapon>.AIParameters.BehaviorTypes.<rank>.<distance>.MinShots`, `.MaxShots`,
`.IgnoreDispersionMinShots`, `.IgnoreDispersionMaxShots`, `.MinSecondsDelay`
and `.MaxSecondsDelay`. The complete 45-row pilot is shown below.

| Weapon | Rank | Distance | Burst min/max | No-dispersion min/max | Delay min/max |
| --- | --- | --- | --- | --- | --- |
| GunPM_HG_NPC | Newbie | Long | 3/4 | 2/3 | 1.2/1.5 |
| GunPM_HG_NPC | Newbie | Medium | 4/5 | 2/3 | 1.0/1.2 |
| GunPM_HG_NPC | Newbie | Short | 4/5 | 4/5 | 0.8/1.0 |
| GunPM_HG_NPC | Experienced | Long | 3/4 | 2/3 | 1.2/1.5 |
| GunPM_HG_NPC | Experienced | Medium | 4/5 | 2/3 | 1.0/1.2 |
| GunPM_HG_NPC | Experienced | Short | 4/5 | 4/5 | 0.8/1.0 |
| GunPM_HG_NPC | Veteran | Long | 3/4 | 2/3 | 1.2/1.5 |
| GunPM_HG_NPC | Veteran | Medium | 4/5 | 2/3 | 1.0/1.2 |
| GunPM_HG_NPC | Veteran | Short | 4/5 | 4/5 | 0.8/1.0 |
| GunPM_HG_NPC | Master | Long | 3/4 | 2/3 | 1.2/1.5 |
| GunPM_HG_NPC | Master | Medium | 4/5 | 2/3 | 1.0/1.2 |
| GunPM_HG_NPC | Master | Short | 4/5 | 4/5 | 0.8/1.0 |
| GunPM_HG_NPC | Zombie | Long | 3/4 | 2/3 | 2.0/2.5 |
| GunPM_HG_NPC | Zombie | Medium | 4/5 | 2/3 | 1.8/2.0 |
| GunPM_HG_NPC | Zombie | Short | 4/5 | 4/5 | 1.5/1.8 |
| GunAK74_ST_NPC | Newbie | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunAK74_ST_NPC | Newbie | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunAK74_ST_NPC | Newbie | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunAK74_ST_NPC | Experienced | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunAK74_ST_NPC | Experienced | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunAK74_ST_NPC | Experienced | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunAK74_ST_NPC | Veteran | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunAK74_ST_NPC | Veteran | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunAK74_ST_NPC | Veteran | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunAK74_ST_NPC | Master | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunAK74_ST_NPC | Master | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunAK74_ST_NPC | Master | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunAK74_ST_NPC | Zombie | Long | 3/6 | 1/3 | 2.0/2.5 |
| GunAK74_ST_NPC | Zombie | Medium | 4/14 | 2/3 | 1.8/2.0 |
| GunAK74_ST_NPC | Zombie | Short | 8/16 | 4/6 | 1.5/1.8 |
| GunM16_ST_NPC | Newbie | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunM16_ST_NPC | Newbie | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunM16_ST_NPC | Newbie | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunM16_ST_NPC | Experienced | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunM16_ST_NPC | Experienced | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunM16_ST_NPC | Experienced | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunM16_ST_NPC | Veteran | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunM16_ST_NPC | Veteran | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunM16_ST_NPC | Veteran | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunM16_ST_NPC | Master | Long | 3/6 | 2/3 | 1.2/1.5 |
| GunM16_ST_NPC | Master | Medium | 4/14 | 3/5 | 1.0/1.2 |
| GunM16_ST_NPC | Master | Short | 8/16 | 4/6 | 0.8/1.0 |
| GunM16_ST_NPC | Zombie | Long | 3/6 | 1/3 | 2.0/2.5 |
| GunM16_ST_NPC | Zombie | Medium | 4/14 | 4/7 | 1.8/2.0 |
| GunM16_ST_NPC | Zombie | Short | 8/16 | 6/8 | 1.5/1.8 |

Compose effective factors with the existing global controls once. Preserve
zero guaranteed shots, integer counts, min/max ordering and the existing rule
that guaranteed shots cannot exceed burst length. Do not multiply all
distance bands when only Long was selected. A preview should show final values;
integer rounding can make small adjustments inert.

Direct children of the pilot roots are:

| Parent | Direct child | Child refkey |
| --- | --- | --- |
| GunAK74_ST_NPC | GunAK74_Korshunov_ST_NPC | refkey=GunAK74_ST_NPC |
| GunAK74_ST_NPC | GunAK74_Strelok_ST_NPC | refkey=GunAK74_ST_NPC |
| GunAK74_ST_NPC | GuardGunAK74_ST_NPC | refkey=GunAK74_ST_NPC |
| GunM16_ST_NPC | GuardGunM16_ST_NPC | refkey=GunM16_ST_NPC |
| GunPM_HG_NPC | GuardGunPM_HG_NPC | refkey=GunPM_HG_NPC |

These include explicit guard, Korshunov and Strelok definitions. Their Newbie
engagement minimum is explicitly present in the snapshot; that one check is
not enough to prove shielding of every edited nested leaf. Before implementation,
audit all targeted leaves and descendants and protect boss/guard definitions
from inherited changes. Also trace general weapon/profile consumers: a normal
weapon can be used by named or quest NPCs. A generic weapon-wide control cannot
promise complete quest isolation. Do not use the current global wildcard as
the definition of a safe ordinary-only advanced editor.

The key name `IgnoreDispersion` supports a zero-spread interpretation, not a
guarantee of a hit through cover or without line of sight. Validate bursts and
pauses by rank, save/load, and one excluded boss/guard context in game.

## Exclusions and implementation handoff

- Keep the current unresolved A-Life feedback separate. Raising the global
  agent cap or every spawn slider again is not a verified fix and is not a
  priority proposal here. Extinction controls, story lairs and fallback faction
  behavior need their existing safeguards.
- Do not add player flashlight brightness or animation playback sliders from
  these CFG findings; the prior asset-level limitations still stand.
- Do not call regional weather, NPC faction equipment, trophy chances, extra
  stash finds or loaded NPC ammunition new features; these already exist.
- No routine increase of every slider maximum. Use selective controls with
  inherited defaults, final-value previews and reset/undo/profile integration.
- Any implementation must resolve live values, emit only deviations and retain
  full native rows where array semantics require it. A neutral configuration
  must still emit no patch.
- Priorities 1–3 have small, complete numeric candidate sets. Priority 4 has
  complete head/NVG candidate baselines but needs route/context validation;
  NVG semantics remain a separate gate. Priority 5 needs the broader consumer
  audit before expanding beyond this three-profile study.

Private reproducibility scripts: `out/slider_audit_1401/world_npc/audit.py`,
`detail.py`, `write_report.py`; results `audit.json` and `detail.json`.
The source CFGs remain local and must not be committed or redistributed.
