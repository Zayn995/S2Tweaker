# Faction relationships: data reference

Data inspected on 2026-09-02, with the save-version conclusion corrected on
2026-09-09. Source: `RelationPrototypes.cfg` in the game's `GameData` directory
(1,210 lines, one top-level struct named `Default`). `Relations.csv` provides
a development matrix of the same values; `RelationColors*.json` controls UI colors.
The inspected dataset contains **582 pairs**, not 644. Counts below describe
that snapshot; the tool reads current installation values.

## Structure of Default

| Patch path | Meaning | Checked vanilla value |
|---|---|---|
| `Default.RelationVersion` | Relationship dataset version | 7 |
| `Default.Relations.<A><->B>` | 582 relationship pairs | Tables below |
| `Default.Factions.<Child>` | 93-faction inheritance tree | Humanoid, Player and Mutant roots |
| `Default.RelationLevelRanges` | Numeric ranges mapped to levels | Five ranges below |
| `Default.MinRelationLevelToTrade` | Trading threshold | `ERelationLevel::Disaffection` |
| `Default.CharacterReactions` | Eight event tables with local reputation deltas | Kill: `Neutral->Friend = -2000`, for example |
| `Default.FactionReactions` | Corresponding faction-wide event tables | Kill: `Neutral->Friend = -10`; `[5]` Grenade is empty |
| `Default.ReputationRollbackCooldown` | Local reaction rollback, seconds | 3600 |
| `Default.Hub/LairReputationRollbackCooldownModifier` | Hub/lair rollback modifiers | 0.05 / 0.1 |
| `Default.FactionRollbackCooldowns.<Faction>` | 19 faction-specific cooldowns | 900 each |
| `Default.RelationUpdateDeltas` | Versioned save migration data | Empty `[0]`, `RelationVersion = 0` |
| `Default.ExpansionPolicies.AttackLairRestrictions` | A-Life lair attack permissions, `A->B = true` | 74 entries |
| `Default.PositiveReactionsExcludedFactions` / `Negative…` | Exemptions from reputation changes | 36 / 26 array entries, including `Player<->Monolith` |

The reaction events are Damage, Kill, Heal, Wounded, KillWounded, Grenade,
FractionDamage and Melee.

### RelationLevelRanges

| Range | Level | Interpretation in the inspected data and community reports |
|---|---|---|
| <= -800 | Enemy | Hostile; no trading |
| -799 through -201 | Disaffection | Conversation/trading allowed by the vanilla threshold |
| -200 through 200 | Neutral | Default behavior |
| 201 through 99999 | Friend | Lowest reputation-based repair cost |
| Exactly 100000 | Internal fifth level, probably Self | Appears as `…->Self` in reaction tables |

`CoreVariables.ReputationRepairCostModifiers` uses Enemy 2.0, Disaffection 1.5,
Neutral 1.0 and Friend 0.75. Relationships therefore affect repair prices too.
The exact boundary matters: -799 is Disaffection, -800 is Enemy, and 201 is Friend.
Both 600 and 800 lie in the game's Friend range even if UI labels distinguish them.

## Count cross-check

- 582 total pairs = 62 involving Player + 520 without Player.
- Player pairs: 51 zero values; seven -800 values (Mutant, ArenaEnemy, Bandits,
  Monolith, Militaries, Mercenaries, EnemyVarta); three -600 values (VaranBandits,
  ShahBandits, NoonFaustians); one +800 value (ArenaFriend).
- Non-player pairs: 247 nonzero and 273 zero. The full distribution is below.

## Existing saves and RelationVersion

Relationship baselines do not automatically replace reputation stored in an
existing save. Vanilla includes `RelationVersion` and `RelationUpdateDeltas`,
but the inspected data contains no populated delta example. The exact migration
syntax has not been established.

Versions 1.12.0 through 1.36.0 emitted vanilla `RelationVersion + 1` under the
unverified assumption that this refreshed relationships. That approach was
removed after the September 9 comparison of all eight
[RSO variants](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2009): they
do not increment the counter, and merely changing a version without matching
delta entries is not a demonstrated migration. It could also collide with a
future game migration. **The generator now leaves RelationVersion unchanged.**

The optional existing-save path introduced in 1.36.0 instead generates a small
quest using `ChangeRelationships` nodes, started from `Scripts/OnGameLaunch/`.
See `_relations_runtime_patch` in `s2tweaker/tweaks.py` and
`tests/test_relations_runtime.py`. Structural tests validate the generated
graph; they do not establish behavior for every story state or saved NPC.

## Runtime limits

Quests and scripts can override relationships. Related values appear in quest,
dialog, infotopic and threat prototypes. Scripted NPCs can have individual
relationships independent of their faction. `CharacterReactions` controls large,
local, temporary changes; `FactionReactions` controls smaller faction-wide changes.
Rollback can restore local values later. Community reports describe hub guards
unexpectedly returning to neutral in modified configurations.

Relevant external references are [RSO](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2009)
and [Faction Relations Live PDA Tab](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2557).
These are historical research sources, not a current compatibility endorsement.

## Scope and invariants

The normal faction controls use Neutrals (Loners), Bandits, Militaries (Military),
Varta (Ward), Duty, Freedom, Mercenaries, Monolith, Noon (Noontide), Spark, Corpus
(Corps), Scientists, and the Mutant umbrella faction. Twelve human factions form
66 distinct human pairs plus 12 pairs against Mutant; each also has a Player pair.

Story, boss, arena and special subfactions remain outside that normal selection.
Examples include `ScarBoss_Faction`, `KorshunovBoss_Faction`,
`StrelokBoss_Faction`, `FaustBoss_Faction`, `ArenaEnemy`, `ArenaFriend`,
`EnemyVarta`, `SQ72_Varta`, `SQ89_SidorMercs`, `CNPP_Archanomaly_PhantomZombie`,
`NoonFaustians`, `VartaSIRCAA`, `SIRCAA_Scientist`, `MALACHITE_Scientist`,
`DepoVictims`, `DocileLabMutants`, `YantarZombie`, `NoahLesya`, `Lessy`,
`FriendlyBlinddog`, `MoldyBlinddog`, `CrazyGuardians` and special bandit camps.

Preserve the faction tree, reaction-exclusion arrays and empty Grenade reaction
table. Do not invent migration deltas. The UI range is -800..800; runtime drift
outside it does not justify expanding the baseline controls. Neutral settings
emit no patch, and exact irregular vanilla values such as -599 remain selectable.

Rollback controls include the main cooldown, all 19 faction cooldowns and both
hub/lair modifiers. Pair selection and reputation mechanics do not authorize
unrelated story edits or a dataset version increment.

## Complete vanilla tables (generated from CFG data, 2026-09-02)

### Faction tree (93 factions, child -> parent inheritance)

- **`Humanoid`** (root)
  - `Bandits`
    - `WildBandits`
    - `NeutralBandits`
    - `VaranBandits`
      - `VaranStashBandits`
    - `RooseveltBandits`
    - `ShahBandits`
    - `LokotBandits`
    - `DepoBandits`
    - `DocentBandits`
    - `KosakBandits`
    - `SultanBandits`
    - `KabanBandits`
    - `SQ89_SidorMercs`
  - `Monolith`
    - `FaustBoss_Faction`
  - `FreeStalkers`
    - `Freedom`
    - `Neutrals`
      - `Diggers`
      - `ShevchenkoStalkers`
      - `MoleStalkers`
      - `NoahLesya`
    - `Noon`
      - `NoonFaustians`
    - `Scientists`
      - `SIRCAA_Scientist`
      - `MALACHITE_Scientist`
    - `Flame`
    - `Spark`
      - `SparkLesnichestvo`
      - `CrazyGuardians`
      - `ScarBoss_Faction`
  - `Army`
    - `Duty`
    - `Varta`
      - `AzimutVarta`
      - `VartaLesnichestvo`
      - `IkarVarta`
      - `EnemyVarta`
      - `VartaSIRCAA`
      - `KorshunovBoss_Faction`
    - `Militaries`
      - `GarmataMilitaries`
      - `SphereMilitaries`
      - `AzimuthMilitaries`
      - `DrozdMilitaries`
      - `NeutralMSOP`
    - `Mercenaries`
      - `UdavMercenaries`
      - `KlenMercenaries`
    - `Law`
    - `Corpus`
      - `YanovCorpus`
      - `CorpusStorm`
  - `DepoVictims`
  - `SafariHunters`
  - `ArenaEnemy`
  - `ArenaFriend`
    - `CNPP_Archanomaly_PhantomZombie`
  - `SQ72_Varta`
- **`Player`** (root)
- **`Mutant`** (root)
  - `Controller`
  - `Poltergeist`
  - `Bloodsucker`
  - `Zombie`
    - `YantarZombie`
  - `Chimera`
  - `Burer`
  - `Pseudogiant`
  - `Anamorph`
  - `Sinister`
  - `Pseudobear`
  - `Snork`
  - `Pseudodog`
  - `Boar`
  - `Flesh`
  - `Beaver`
  - `Ratwolf`
  - `Deer`
  - `Rat`
  - `Tushkan`
  - `Stickman`
  - `Blinddog`
    - `FriendlyBlinddog`
    - `Lessy`
    - `MoldyBlinddog`
  - `Bayun`
  - `DocileLabMutants`
  - `AlliedMutants`
  - `StrelokBoss_Faction`

### All Player pairs (62)

| Pair | Vanilla | Level |
|---|---|---|
| `Army<->Player` | 0 | Neutral |
| `FreeStalkers<->Player` | 0 | Neutral |
| `Mutant<->Player` | -800 | Enemy |
| `Humanoid<->Player` | 0 | Neutral |
| `AlliedMutants<->Player` | 0 | Neutral |
| `ArenaEnemy<->Player` | -800 | Enemy |
| `Bandits<->Player` | -800 | Enemy |
| `Monolith<->Player` | -800 | Enemy |
| `Duty<->Player` | 0 | Neutral |
| `Freedom<->Player` | 0 | Neutral |
| `Varta<->Player` | 0 | Neutral |
| `Neutrals<->Player` | 0 | Neutral |
| `Militaries<->Player` | -800 | Enemy |
| `Noon<->Player` | 0 | Neutral |
| `Scientists<->Player` | 0 | Neutral |
| `Mercenaries<->Player` | -800 | Enemy |
| `Spark<->Player` | 0 | Neutral |
| `Corpus<->Player` | 0 | Neutral |
| `NeutralBandits<->Player` | 0 | Neutral |
| `VaranBandits<->Player` | -600 | Disaffection |
| `RooseveltBandits<->Player` | 0 | Neutral |
| `ShahBandits<->Player` | -600 | Disaffection |
| `DepoBandits<->Player` | 0 | Neutral |
| `DocentBandits<->Player` | 0 | Neutral |
| `SultanBandits<->Player` | 0 | Neutral |
| `Diggers<->Player` | 0 | Neutral |
| `UdavMercenaries<->Player` | 0 | Neutral |
| `ShevchenkoStalkers<->Player` | 0 | Neutral |
| `SIRCAA_Scientist<->Player` | 0 | Neutral |
| `MALACHITE_Scientist<->Player` | 0 | Neutral |
| `NoonFaustians<->Player` | -600 | Disaffection |
| `IkarVarta<->Player` | 0 | Neutral |
| `NeutralMSOP<->Player` | 0 | Neutral |
| `EnemyVarta<->Player` | -800 | Enemy |
| `Law<->Player` | 0 | Neutral |
| `Flame<->Player` | 0 | Neutral |
| `DepoVictims<->Player` | 0 | Neutral |
| `SphereMilitaries<->Player` | 0 | Neutral |
| `VaranStashBandits<->Player` | 0 | Neutral |
| `SafariHunters<->Player` | 0 | Neutral |
| `GarmataMilitaries<->Player` | 0 | Neutral |
| `AzimutVarta<->Player` | 0 | Neutral |
| `AzimuthMilitaries<->Player` | 0 | Neutral |
| `KabanBandits<->Player` | 0 | Neutral |
| `YanovCorpus<->Player` | 0 | Neutral |
| `VartaLesnichestvo<->Player` | 0 | Neutral |
| `SparkLesnichestvo<->Player` | 0 | Neutral |
| `CrazyGuardians<->Player` | 0 | Neutral |
| `KlenMercenaries<->Player` | 0 | Neutral |
| `DrozdMilitaries<->Player` | 0 | Neutral |
| `LokotBandits<->Player` | 0 | Neutral |
| `FriendlyBlinddog<->Player` | 0 | Neutral |
| `KosakBandits<->Player` | 0 | Neutral |
| `MoleStalkers<->Player` | 0 | Neutral |
| `SQ72_Varta<->Player` | 0 | Neutral |
| `VartaSIRCAA<->Player` | 0 | Neutral |
| `NoahLesya<->Player` | 0 | Neutral |
| `YantarZombie<->Player` | 0 | Neutral |
| `DocileLabMutants<->Player` | 0 | Neutral |
| `Lessy<->Player` | 0 | Neutral |
| `ArenaFriend<->Player` | 800 | Friend |
| `Player<->Player` | 0 | Neutral |

### Nonzero non-player pairs (247; the remaining 273 are zero)

| Pair | Vanilla | Level |
|---|---|---|
| `AlliedMutants<->AlliedMutants` | 600 | Friend |
| `ArenaEnemy<->ArenaEnemy` | 600 | Friend |
| `ArenaFriend<->ArenaEnemy` | -800 | Enemy |
| `Bandits<->Bandits` | 600 | Friend |
| `Bandits<->FreeStalkers` | -800 | Enemy |
| `Bandits<->Humanoid` | -800 | Enemy |
| `Bandits<->Mutant` | -800 | Enemy |
| `Bayun<->Bayun` | 800 | Friend |
| `Bayun<->Blinddog` | -800 | Enemy |
| `Bayun<->Bloodsucker` | -800 | Enemy |
| `Bayun<->Boar` | -800 | Enemy |
| `Bayun<->Burer` | -800 | Enemy |
| `Bayun<->Chimera` | -800 | Enemy |
| `Bayun<->Controller` | -800 | Enemy |
| `Bayun<->Flesh` | -800 | Enemy |
| `Bayun<->Pseudodog` | -800 | Enemy |
| `Bayun<->Pseudogiant` | -800 | Enemy |
| `Bayun<->Snork` | -800 | Enemy |
| `Bayun<->Tushkan` | -800 | Enemy |
| `Bayun<->Zombie` | -800 | Enemy |
| `Blinddog<->Blinddog` | 800 | Friend |
| `Blinddog<->Bloodsucker` | -800 | Enemy |
| `Blinddog<->Boar` | -800 | Enemy |
| `Blinddog<->Burer` | -800 | Enemy |
| `Blinddog<->Chimera` | -800 | Enemy |
| `Blinddog<->Controller` | -800 | Enemy |
| `Blinddog<->Flesh` | -800 | Enemy |
| `Blinddog<->Snork` | -800 | Enemy |
| `Blinddog<->Tushkan` | -800 | Enemy |
| `Blinddog<->Zombie` | -800 | Enemy |
| `Bloodsucker<->Bloodsucker` | 800 | Friend |
| `Bloodsucker<->Controller` | -800 | Enemy |
| `Boar<->Bloodsucker` | -800 | Enemy |
| `Boar<->Boar` | 800 | Friend |
| `Boar<->Burer` | -800 | Enemy |
| `Boar<->Chimera` | -800 | Enemy |
| `Boar<->Controller` | -800 | Enemy |
| `Boar<->Pseudodog` | -800 | Enemy |
| `Boar<->Pseudogiant` | -800 | Enemy |
| `Boar<->Snork` | -800 | Enemy |
| `Boar<->Zombie` | -800 | Enemy |
| `Burer<->Bloodsucker` | -800 | Enemy |
| `Burer<->Burer` | 800 | Friend |
| `Burer<->Chimera` | -800 | Enemy |
| `Burer<->Controller` | -800 | Enemy |
| `Burer<->Zombie` | -800 | Enemy |
| `Chimera<->Bloodsucker` | -800 | Enemy |
| `Chimera<->Chimera` | 800 | Friend |
| `Chimera<->Zombie` | -800 | Enemy |
| `Controller<->Controller` | 800 | Friend |
| `Corpus<->Bandits` | -800 | Enemy |
| `Corpus<->Corpus` | 600 | Friend |
| `Corpus<->Duty` | 201 | Friend |
| `Corpus<->Mercenaries` | -799 | Disaffection |
| `Corpus<->Monolith` | -800 | Enemy |
| `Corpus<->Mutant` | -800 | Enemy |
| `Corpus<->Noon` | -599 | Disaffection |
| `Corpus<->Scientists` | 201 | Friend |
| `Deer<->Bloodsucker` | -800 | Enemy |
| `Deer<->Burer` | -800 | Enemy |
| `Deer<->Controller` | -800 | Enemy |
| `Deer<->Deer` | 800 | Friend |
| `Deer<->Snork` | -800 | Enemy |
| `Deer<->Zombie` | -800 | Enemy |
| `DocentBandits<->Corpus` | -800 | Enemy |
| `DocentBandits<->DocentBandits` | 600 | Friend |
| `DocentBandits<->Duty` | -800 | Enemy |
| `DocentBandits<->Mercenaries` | -799 | Disaffection |
| `DocentBandits<->Militaries` | -800 | Enemy |
| `DocentBandits<->Monolith` | -800 | Enemy |
| `DocentBandits<->Mutant` | -800 | Enemy |
| `DocentBandits<->Neutrals` | -800 | Enemy |
| `DocentBandits<->Noon` | -800 | Enemy |
| `DocentBandits<->Scientists` | -799 | Disaffection |
| `DocentBandits<->Spark` | -799 | Disaffection |
| `DocentBandits<->Varta` | -799 | Disaffection |
| `Duty<->Bandits` | -800 | Enemy |
| `Duty<->Duty` | 600 | Friend |
| `Duty<->Monolith` | -800 | Enemy |
| `Duty<->Mutant` | -800 | Enemy |
| `Flesh<->Bloodsucker` | -800 | Enemy |
| `Flesh<->Burer` | -800 | Enemy |
| `Flesh<->Chimera` | -800 | Enemy |
| `Flesh<->Controller` | -800 | Enemy |
| `Flesh<->Flesh` | 800 | Friend |
| `Flesh<->Pseudodog` | -800 | Enemy |
| `Flesh<->Pseudogiant` | -800 | Enemy |
| `Flesh<->Snork` | -800 | Enemy |
| `Flesh<->Zombie` | -800 | Enemy |
| `Freedom<->Bandits` | -800 | Enemy |
| `Freedom<->Duty` | -599 | Disaffection |
| `Freedom<->Freedom` | 600 | Friend |
| `Freedom<->Monolith` | -800 | Enemy |
| `Freedom<->Mutant` | -800 | Enemy |
| `Humanoid<->Mutant` | -800 | Enemy |
| `Mercenaries<->Bandits` | -599 | Disaffection |
| `Mercenaries<->Duty` | -799 | Disaffection |
| `Mercenaries<->Freedom` | -599 | Disaffection |
| `Mercenaries<->Mercenaries` | 600 | Friend |
| `Mercenaries<->Militaries` | -800 | Enemy |
| `Mercenaries<->Monolith` | -800 | Enemy |
| `Mercenaries<->Mutant` | -800 | Enemy |
| `Mercenaries<->Neutrals` | -799 | Disaffection |
| `Mercenaries<->Noon` | -799 | Disaffection |
| `Mercenaries<->Varta` | -599 | Disaffection |
| `Militaries<->Bandits` | -800 | Enemy |
| `Militaries<->Freedom` | -799 | Disaffection |
| `Militaries<->Militaries` | 600 | Friend |
| `Militaries<->Monolith` | -800 | Enemy |
| `Militaries<->Mutant` | -800 | Enemy |
| `Militaries<->Neutrals` | -800 | Enemy |
| `Monolith<->Bandits` | -800 | Enemy |
| `Monolith<->Humanoid` | -800 | Enemy |
| `Monolith<->Monolith` | 600 | Friend |
| `Monolith<->Mutant` | -800 | Enemy |
| `Mutant<->Army` | -800 | Enemy |
| `Mutant<->FreeStalkers` | -800 | Enemy |
| `NeutralBandits<->Corpus` | -800 | Enemy |
| `NeutralBandits<->Duty` | -800 | Enemy |
| `NeutralBandits<->Mercenaries` | -599 | Disaffection |
| `NeutralBandits<->Militaries` | -800 | Enemy |
| `NeutralBandits<->Monolith` | -800 | Enemy |
| `NeutralBandits<->Mutant` | -800 | Enemy |
| `NeutralBandits<->NeutralBandits` | 600 | Friend |
| `NeutralBandits<->Noon` | -799 | Disaffection |
| `NeutralBandits<->Scientists` | -799 | Disaffection |
| `NeutralBandits<->Spark` | -799 | Disaffection |
| `NeutralBandits<->Varta` | -799 | Disaffection |
| `Neutrals<->Bandits` | -800 | Enemy |
| `Neutrals<->Monolith` | -800 | Enemy |
| `Neutrals<->Mutant` | -800 | Enemy |
| `Neutrals<->Neutrals` | 600 | Friend |
| `Neutrals<->Varta` | -399 | Disaffection |
| `Noon<->Bandits` | -800 | Enemy |
| `Noon<->Duty` | -599 | Disaffection |
| `Noon<->Freedom` | -599 | Disaffection |
| `Noon<->Militaries` | -800 | Enemy |
| `Noon<->Monolith` | -800 | Enemy |
| `Noon<->Mutant` | -800 | Enemy |
| `Noon<->Neutrals` | -599 | Disaffection |
| `Noon<->Noon` | 600 | Friend |
| `Noon<->Varta` | -399 | Disaffection |
| `Poltergeist<->Poltergeist` | 800 | Friend |
| `Pseudodog<->Bloodsucker` | -800 | Enemy |
| `Pseudodog<->Burer` | -800 | Enemy |
| `Pseudodog<->Chimera` | -800 | Enemy |
| `Pseudodog<->Pseudodog` | 800 | Friend |
| `Pseudodog<->Pseudogiant` | -800 | Enemy |
| `Pseudodog<->Snork` | -800 | Enemy |
| `Pseudodog<->Zombie` | -800 | Enemy |
| `Pseudogiant<->Burer` | -800 | Enemy |
| `Pseudogiant<->Chimera` | -800 | Enemy |
| `Pseudogiant<->Controller` | -800 | Enemy |
| `Pseudogiant<->Pseudogiant` | 800 | Friend |
| `Pseudogiant<->Zombie` | -800 | Enemy |
| `Rat<->Rat` | 800 | Friend |
| `RooseveltBandits<->Corpus` | -800 | Enemy |
| `RooseveltBandits<->Mercenaries` | -799 | Disaffection |
| `RooseveltBandits<->Militaries` | -800 | Enemy |
| `RooseveltBandits<->Monolith` | -800 | Enemy |
| `RooseveltBandits<->Mutant` | -800 | Enemy |
| `RooseveltBandits<->Neutrals` | -800 | Enemy |
| `RooseveltBandits<->Noon` | -800 | Enemy |
| `RooseveltBandits<->RooseveltBandits` | 600 | Friend |
| `RooseveltBandits<->Scientists` | -799 | Disaffection |
| `RooseveltBandits<->Spark` | -799 | Disaffection |
| `RooseveltBandits<->Varta` | -799 | Disaffection |
| `Scientists<->Bandits` | -800 | Enemy |
| `Scientists<->Duty` | 201 | Friend |
| `Scientists<->Militaries` | 201 | Friend |
| `Scientists<->Monolith` | -800 | Enemy |
| `Scientists<->Mutant` | -800 | Enemy |
| `Scientists<->Scientists` | 600 | Friend |
| `ShahBandits<->Corpus` | -800 | Enemy |
| `ShahBandits<->Duty` | -800 | Enemy |
| `ShahBandits<->Freedom` | 201 | Friend |
| `ShahBandits<->Mercenaries` | -799 | Disaffection |
| `ShahBandits<->Militaries` | -800 | Enemy |
| `ShahBandits<->Monolith` | -800 | Enemy |
| `ShahBandits<->Mutant` | -800 | Enemy |
| `ShahBandits<->Neutrals` | -800 | Enemy |
| `ShahBandits<->Noon` | -800 | Enemy |
| `ShahBandits<->RooseveltBandits` | -800 | Enemy |
| `ShahBandits<->Scientists` | -799 | Disaffection |
| `ShahBandits<->ShahBandits` | 600 | Friend |
| `ShahBandits<->Spark` | -799 | Disaffection |
| `ShahBandits<->Varta` | -799 | Disaffection |
| `Snork<->Bloodsucker` | -800 | Enemy |
| `Snork<->Burer` | -800 | Enemy |
| `Snork<->Chimera` | -800 | Enemy |
| `Snork<->Controller` | -800 | Enemy |
| `Snork<->Pseudogiant` | -800 | Enemy |
| `Snork<->Snork` | 800 | Friend |
| `Snork<->Zombie` | -800 | Enemy |
| `Spark<->Bandits` | -800 | Enemy |
| `Spark<->Mercenaries` | -799 | Disaffection |
| `Spark<->Militaries` | -800 | Enemy |
| `Spark<->Monolith` | -800 | Enemy |
| `Spark<->Mutant` | -800 | Enemy |
| `Spark<->Noon` | -599 | Disaffection |
| `Spark<->Scientists` | 201 | Friend |
| `Spark<->Spark` | 600 | Friend |
| `Spark<->Varta` | -599 | Disaffection |
| `SultanBandits<->Corpus` | -799 | Disaffection |
| `SultanBandits<->Duty` | -800 | Enemy |
| `SultanBandits<->Mercenaries` | -799 | Disaffection |
| `SultanBandits<->Militaries` | -800 | Enemy |
| `SultanBandits<->Monolith` | -800 | Enemy |
| `SultanBandits<->Mutant` | -800 | Enemy |
| `SultanBandits<->Noon` | -799 | Disaffection |
| `SultanBandits<->Scientists` | -799 | Disaffection |
| `SultanBandits<->SultanBandits` | 600 | Friend |
| `SultanBandits<->Varta` | -799 | Disaffection |
| `Tushkan<->Bloodsucker` | -800 | Enemy |
| `Tushkan<->Boar` | -800 | Enemy |
| `Tushkan<->Burer` | -800 | Enemy |
| `Tushkan<->Chimera` | -800 | Enemy |
| `Tushkan<->Controller` | -800 | Enemy |
| `Tushkan<->Flesh` | -800 | Enemy |
| `Tushkan<->Pseudodog` | -800 | Enemy |
| `Tushkan<->Pseudogiant` | -800 | Enemy |
| `Tushkan<->Snork` | -800 | Enemy |
| `Tushkan<->Tushkan` | 800 | Friend |
| `Tushkan<->Zombie` | -800 | Enemy |
| `Varta<->Bandits` | -800 | Enemy |
| `Varta<->Duty` | 201 | Friend |
| `Varta<->Monolith` | -800 | Enemy |
| `Varta<->Mutant` | -800 | Enemy |
| `Varta<->Varta` | 600 | Friend |
| `VartaSIRCAA<->AlliedMutants` | -800 | Enemy |
| `VartaSIRCAA<->ArenaEnemy` | -800 | Enemy |
| `VartaSIRCAA<->Bandits` | -800 | Enemy |
| `VartaSIRCAA<->DepoBandits` | -800 | Enemy |
| `VartaSIRCAA<->DocentBandits` | -800 | Enemy |
| `VartaSIRCAA<->Monolith` | -800 | Enemy |
| `VartaSIRCAA<->Mutant` | -800 | Enemy |
| `VartaSIRCAA<->RooseveltBandits` | -800 | Enemy |
| `VartaSIRCAA<->SIRCAA_Scientist` | 800 | Friend |
| `VartaSIRCAA<->Scientists` | 800 | Friend |
| `VartaSIRCAA<->ShahBandits` | -800 | Enemy |
| `VartaSIRCAA<->Spark` | -299 | Disaffection |
| `VartaSIRCAA<->SultanBandits` | -800 | Enemy |
| `VartaSIRCAA<->VaranBandits` | -800 | Enemy |
| `VartaSIRCAA<->Varta` | 800 | Friend |
| `Zombie<->Bloodsucker` | -800 | Enemy |
| `Zombie<->Controller` | 800 | Friend |
| `Zombie<->Zombie` | 800 | Friend |

### Value distribution across all 582 pairs

| Value | Count | Level |
|---|---|---|
| -800 | 167 | Enemy |
| -799 | 27 | Disaffection |
| -600 | 3 | Disaffection |
| -599 | 11 | Disaffection |
| -399 | 2 | Disaffection |
| -299 | 1 | Disaffection |
| 0 | 324 | Neutral |
| 201 | 7 | Friend |
| 600 | 19 | Friend |
| 800 | 21 | Friend |
