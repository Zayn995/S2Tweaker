# A-Life spawning: Director and lairs

Research snapshot: 2026-09-03, using extracted 2.0.x data dated 2026-08-27.
Counts refer to that snapshot. Paths below are relative to the game's `GameData`
directory; current values must be read from the installed game. Runtime
interpretations that still need a play test are identified separately.

## Two spawning systems

`AIGlobals.MaxAgentsCount = 52` caps simultaneously online agents. Raising it
alone does not change how many agents the spawning systems generate.

**Lairs** are fixed map locations. Their population, initial fill, replacement
timers and archetype weights depend on lair type, inhabitant faction and player
rank. **The Director** chooses weighted encounter scenarios around the player,
using region-specific scenario groups, delays and per-rank agent limits.
Increasing population or frequency can still run into the online-agent cap.

## Files

| File | Inspected size/structure | Purpose |
|---|---|---|
| `ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg` | 2,233 lines, 82 KB, one `ALifeDirectorPreset` with SID `Default` | Defaults, rank limits, exclusions, 73 scenarios, 13 groups |
| `LairPrototypes.cfg` | 19,794 lines, 918 KB, `[0]` plus 74 lair types | 196 lair/faction pairs x 4 ranks = 784 blocks; 2,709 archetype entries |
| `ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg` | 616 lines, one `ALifePopulationManagerPreset` | Expansion between lairs, 29 factions |
| `ALifePrototypes/ALifePolicyPrototypes.cfg` | 14 lines, one `Default` | Refill cooldowns and corpse limits |
| `AIGlobals.cfg` | 779 lines | Online cap 52, spawn/despawn distance 2500/3000, 23 region-rank entries |
| `CoreVariables.cfg` | Selected scalars | Grid vision radius 8500, lair search radius 130000, corpse hard cap 1500, corpse online time 1800 |
| `SpawnActorPrototypes.cfg` | 184 MB | 446 lair placements and 63 scenario-group assignments; outside the extraction/patch scope of this feature |

No DLC overrides of the A-Life/lair files or external CFG references to these
files were found in the inspected data. Adding Director and lair files originally
required cache schema 12 -> 13; this is historical context, not the current schema.

## Director

All patch paths begin with the **struct key** `ALifeDirectorPreset`, not its SID.

### Defaults

| Keys | Vanilla | Interpretation |
|---|---|---|
| `DefaultSpawnDelayMin/Max` | 100 / 180 | Seconds between selections if a group has no own delay |
| `DefaultPostSpawnDirectorTimeoutMin/Max` | 150 / 300 | Pause after spawning |
| `DefaultALifeLairExpansionToPlayerTimeMin/Max` | 120 / 180 | Expansion toward the player; timing interpretation requires testing |
| `DefaultExpansionSquadNumMin/Max` | 4 / 7 | Expansion squad size; attack-lair scenarios override humans to 4/7 and mutants to 1/1 |
| `DefaultShouldDespawnNPCs` | true | Despawn flag |
| `DefaultEmissionScenarioGroup` | Emission | Emission group |
| `DefaultScenarioGroup` | Global | Fallback group |
| `DefaultEmptyScenarioGroup` | EmptyGroup | Empty group |
| `FallbackMaxSpawnCount` | 3 | Fallback limit |

### Rank limits

Path: `ALifeDirectorPreset.ALifeScenarioNPCArchetypesLimitsPerPlayerRank.[i].Restrictions.[j].MaxCount`.
Match entries by `AgentType`; do not assume rank/type array positions stay fixed.

| Agent type | Newbie | Experienced | Veteran | Master | Generic Director selection |
|---|---|---|---|---|---|
| Human | 3 | 4 | 5 | 6 | Allowed |
| MutantGeneric | 3 | 4 | 4 | 4 | Allowed |
| Blinddog | 4 | 6 | 8 | 12 | Allowed |
| Boar | 2 | 3 | 5 | 6 | Allowed |
| Flesh | 2 | 3 | 5 | 6 | Allowed |
| Snork | 1 | 3 | 4 | 6 | Allowed |
| Tushkan | 6 | 8 | 12 | 16 | Allowed |
| Bloodsucker | 0 | 1 | 1 | 1 | Allowed; Newbie stays zero |
| Chimera | 1 | 1 | 1 | 1 | Prohibited, although a specific scenario exists |
| Controller | 0 | 1 | 1 | 1 | Prohibited |
| Burer | 1 | 1 | 1 | 2 | Prohibited |
| Poltergeist | 1 | 1 | 2 | 2 | Prohibited |
| PseudoDog | 1 | 1 | 1 | 1 | Prohibited |
| Cat | 1 | 1 | 1 | 2 | Prohibited |
| Deer | 1 | 1 | 1 | 1 | Prohibited |
| RatSwarm | 1 | 1 | 1 | 1 | Prohibited |

**Unverified formula:** pack size may be `MaxCount * AliveMultiplier`, usually
0.4..0.8. This roughly matches scenario names such as `Blinddog3_5` and `Boar5_7`,
but names and data consistency do not prove the runtime formula.

`ProhibitedAgentTypes` contains nine types: Chimera, Pseudogiant, Controller,
Poltergeist, Burer, Cat, Deer, PseudoDog and RatSwarm. Yet `ChimeraSingle` has
weight 2 in Global and 1 in HumanVsMutants, requiring Veteran rank. Explicit
`AgentPrototypeSID` scenarios may bypass generic exclusions; this is unverified.
The 51 `RestrictedObjPrototypeSIDs` include guards and Spark/Noon/Scientist
prototypes. Fallback types are Bandits, Neutrals, Blinddog and Boar. These arrays
are preserved by the scalar controls.

### Scenarios and groups

Each scenario has `PlayerRequiredRank` and `ScenarioSquads.[k]` containing either
generic `AgentArchetype` or specific `AgentPrototypeSID`, plus `bPlayerEnemy`,
`RelationGroup`, alive/wounded/dead multipliers and a group target. Targets include
Player, TargetEachOther, AttackEnemyLair, AllyLair and ContextualAction.
`BlinddogPack` has SID `BlinddogPackSmall`; `ChimeraSingle` has SID
`Mutant_Chimera`. Patches must address the struct keys.

The 73 scenarios comprise 33 mutant-only, 3 mixed and 37 human-only cases.
Mixed cases are `HumansVsMutants`, `Humans_Wounded_Friendly_vs_Dead_Mutants`
and `Humans_Wounded_Enemy_vs_Dead_Mutants`. Mutant cases include generic
Mutants/DeadMutant/DeadMutants/Mutant_AttackEnemyLair, species packs and duels.
Human cases include friendly/enemy, dead/wounded, lair attacks, movement and
contextual actions. `BloodsuckerSingle` uses alive multipliers 0.2/0.3 and
`Bloodsucker1` 0.2/0.4; most others use 0.4/0.8. Wounded/dead scenarios use
alive 0 with wounded/dead multipliers 0.1..0.6.

Weight path: `ALifeDirectorPreset.ScenarioGroups.<Group>.ScenarioSIDs.<Scenario>.ScenarioWeight`.
Group delays and timeouts are siblings of `ScenarioSIDs`.

| Group | Delay | Timeout | Explicit map assignments | Selection weights |
|---|---|---|---|---|
| Global | 60–90 | 130–180 | 4, plus fallback | HumansVsHumans 20, HumansVsMutants 25, Friendly 15, Enemy 10, Mutants/BlinddogPack/BoarPack/FleshPack 10 each, TushkanPack 5, BloodsuckerSingle 0, ChimeraSingle 2, contextual friendly/enemy 5 each, MoveTo 0/0 |
| Local | 30–60 | 150–210 | 0 | Mutants 20, HumansVsHumans 10, HumansVsMutants 10, Friendly 15, Enemy 10 |
| Hub | 45–90 | 90–120 | 10 | Humans_Friendly_MoveTo_AllyLair 5 |
| Quiet | 120–150 | 120–160 | 5 | Five dead scenarios, all zero |
| Global_LesserZone | 120–150 | 180–300 | 0 | HvH/HvM/Friendly 10 each, Enemy/Mutants 4 each, Blinddog/Boar/FleshPack 5 each, Tushkan/Bloodsucker 0 |
| HumanVsMutants_LesserZone | 120–180 | 240–300 | 1 | Same weights as Global_LesserZone |
| HumanVsMutants | 120–210 | 300–420 | 0 | HvH 10, HvM 20, Friendly/Enemy/MoveTo 7 each, contextual 6 each, ChimeraSingle 1 |
| CaptureLairs | 60–90 | 240–360 | 0 | AttackEnemyLair enemy/friendly/mutant 5 each |
| ContextualActions | 5–30 | 120–150 | 0 | Friendly/enemy contextual actions 5 each |
| Swamp_ScenarioGroups | 60–120 | 140–210 | 1 | Mutant3_5VsMutant3_5 and Mutant5_7VsMutant5_7 5 each; 20 others zero |
| AllScenarios | 150–240 | 240–360 | 0 | 34 scenarios, weight 5 each; development group |
| Emission | 10–20 | 120–150 | 1, plus emission default | Friendly 6, Enemy 3 |
| EmptyGroup | 50–120 | 60–120 | 41 | No scenarios |

Global has total weight 127: mutant-only 47 (37%), or 72 (57%) including the
mixed encounter. These are selection weights, not guaranteed population shares.
Groups with no direct map assignment may be unused or activated by scripts;
zero map references alone do not establish that patching them has an effect.

`AIGlobals.RegionRank` has 23 entries: Zone spans Newbie–Master, MalayaZona
Newbie–Experienced, Bolota/Kordon Experienced–Veteran, Pripyat/Generatory
Veteran–Master, and the other 17 Experienced–Master. The limits depend on
regional rank, not simply accumulated player XP.

## Lairs

The 446 placements use 74 types. Common types include BigLivingSpace 37,
SmallLivingSpace 36, RestingLairDefault 35, GenericHumansAndMutants 33,
Monolith 29, WildField 23, Neutrals/Militaries 17 each, WildUnderground 16,
GenericHumansOnly/Bloodsucker 12 each, Rat 11, GuardNeutrals 10,
Poltergeist 9, Varta/Blinddog 8 each, GuardVarta/Flesh/Burer 7 each,
Mercenaries/LivingUnderground 6 each, Noon/NeutralZombies/Freedom/Controller/
Boar/Bandits 5 each, and Snork/Pseudogiant/Pseudodog/Poltergeist_Electro/
GuardNoon/GuardCorpus 4 each. NeutralMSOP/GuardFreedom/Duty/BanditZombies have
3 each; WildForest/Spark/Poltergeist_Toxic have 2 each. Remaining types occur
at most once, including Chimera, Deer, Tushkan and Bayun.

Example path:
`Blinddog.Preset.PossibleInhabitantFactions.Blinddog.SpawnSettingsPerPlayerRanks.Master.MaxSpawnQuantity`.
The preset also contains `InitialInhabitantFaction`, `IsALifePoint`, faction
priority and `SpawnSettingsPerArchetypes`. All 784 rank blocks define their own
values; none uses `refkey` inheritance.

| Faction | Population N/E/V/M | Initial fraction | Archetypes |
|---|---|---|---|
| Blinddog, MoldyBlinddog | 9/9/9/9 | 0.5 | 1 |
| Tushkan | 14/16/20/24 | 0.5 | 1 |
| Snork | 8/8/9/9 | 0.5 | 1 |
| Boar | 5/5/5/5 | 0.5 | 1 |
| Flesh | 5/5/5/6 | 0.5 | 1 |
| Bloodsucker | 2/2/3/3 | 0.5 | 1 |
| Bayun | 2/2/2/2 | 0.5 | 1 |
| Pseudodog, Deer | 1/1/2/2 | 0.5; Master 1.0 | 1 |
| Controller, four Poltergeist variants, Chimera, Burer, Pseudogiant | 1/1/1/2 | 0.5; Master 1.0 | 1 |
| Rat, five lair types | 1/1/1/1 | 1.0 | RatSwarm_75/150/225/300; one swarm counts as one |
| Zombie, Duty/Freedom/Bandit/Neutral | 6/7/8/10 | 0.5 | 4–5 GeneralZombie variants |
| Zombie, Corpus/generic lairs | 6/8/10/10 | 0.5 | 5 |
| Human factions | 6/6/6–8/7–8 | 0.5 | 2–5 GeneralNPC roles, recon-heavy minimums |
| Guard lairs | 7/7/8/10 | 0.5 | GuardNPC variants; sniper guards 1/1/1/1 |

Newbie population distribution: 1x31, 2x16, 5x12, 6x101, 7x13, 8x6, 9x8,
14x9. Master: 1x12, 2x27, 3x8, 5x6, 6x6, 7x74, 8x14, 9x14, 10x26, 24x9.

### Timers and population floors

774 of 784 blocks use `InitialSpawnQuantityRespawnTimeSeconds = 180`,
`MaxSpawnQuantityRespawnTimeSeconds = 480`, `WipeRespawnTimeoutSeconds = 480`.
Ten Newbie exceptions use 6/30/30: Diggers, IkarVarta, SultanBandits,
NeutralBandits, GuardDiggers, GuardSultanBandits, DutyZombies, FreedomZombies,
BanditZombies and NeutralZombies. Preserve these story/tutorial refill settings.

Seven Freedom Newbie blocks already have archetype minimums totaling 7 while
their maximum is 6; 96 blocks have minimum totals equal to the maximum.
When reducing population, the lower bound is
`max(1, min(vanilla maximum, sum of archetype minimums))`.
Do not make the existing inconsistency worse.

### RestingLairDefault

Used at 35 campfires, this preset has `ELairType::RestingLair`, instant and
short-delay chances 0.4/0.4, NPC limits 1/5, short delay 60/120, long delay
600/1200, search radius 65000, and `GameTimeOfflineToRerollLairData = 14400`
(four game hours). These special settings were excluded from the initial
population controls. Community reports associate short-delay spawning with
nearby pop-in; that does not prove all camp types reroll by this same timer.

## Population manager and policy

The inspected population manager uses expansion time 50, radius 500000 and
simulation start 48 hours. Each of 29 factions has battle chance 50 plus
Aggressive/Normal/Defensive lair-count bands. Examples: Bandits 1–5/6–20/21–900,
most mutants 1–7/8–31/32–900, Pseudogiant 1–7/8–10/11–900.

Policy values: TriggerExtinction 2000, MaxCorpsePerRadius 30, CorpseRadius 10000,
SeenLongAgoByPlayerSec 900, FullWipeRefillCooldown 360,
PartialWipeRefillCooldown 120, and refill distance 20000/25000.
Deeper offline-combat and need parameters were outside this initial study.

## Patch scope and test boundaries

The initial design separates mutant population (352 blocks), human population
(368 non-guard blocks), respawn speed (774 standard-timer blocks), encounter
frequency (group/default delays), mutant scenario weights and experimental
per-type limits. Sixty-four guard blocks remain unchanged by population scaling.
Per-species weights alter encounter selection, not lair ownership or map placement.

Emit only changed numeric leaves, preserve array structure and read all values
live. Do not replace prohibition/fallback lists or invent scenarios. Keep counts
integral, preserve vanilla zeros under multiplicative controls, keep positive
limits at least 1, and maintain delay minimum 5 seconds with Min <= Max.
Existing saves may need time, refill or region changes before populations differ.
Higher populations also increase CPU costs and can hit the online-agent cap.

Unresolved runtime checks include the pack-size formula, explicit scenarios
versus prohibited generic types, and whether activating a zero-weight scenario
actually produces its intended encounter. Zero mutant-only weights do not
eliminate mutants from mixed scenarios or lairs.

Historical comparison sources:
[A-Life Uh.. Found A Way](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1122),
[More Enemies](https://www.nexusmods.com/stalker2heartofchornobyl/mods/438),
[A-Life Extended](https://www.nexusmods.com/stalker2heartofchornobyl/mods/273),
and [Roadside Panic](https://www.nexusmods.com/stalker2heartofchornobyl/mods/210).
Their reported changes cover the same files and include delayed save effects,
corpse accumulation and pop-in. Overlapping patches remain subject to load order.
