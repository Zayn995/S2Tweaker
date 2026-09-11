# NPC equipment: faction, role and scope audit

Verified on the local 2.0.5 decoded snapshot on 2026-09-11. This is a static CFG audit, not a gameplay test. Counts describe stored definitions and references, not the number of NPCs currently alive, obtainable items, or effective quest-stage inventories.

## Result and implementation boundary

There are **50 ordinary main-faction / role Obj prototypes** suitable for an initial allowlist. A faction label alone does not identify an exclusive generator. **Do not edit the shared vanilla GeneralNPC equipment generators directly for an isolated faction editor.** Instead, create a namespaced generator branch for each selected ordinary Obj prototype and replace only that prototype's own `ItemGeneratorPrototypeSID`. Clone any helper whose values change, and redirect only references inside that clone. Keep original generator roots, named NPC object roots, zombies, quest scripts and trade tables unchanged.

The boundary is the **ordinary Obj prototype**, not the placement's quest status. These prototypes are also placed as ordinary enemies or corpses in quest levels, and such uses can change. A separate quest script can later replace an NPC's inventory with a vanilla generator, bypassing the new profile. Do not promise “all members of the faction”, “all named NPCs unchanged at runtime” or “A-Life only / no quest NPCs affected”. Runtime loading of new generator IDs, equipment regeneration in existing saves and quest-stage overrides need in-game validation.

## Source files

All paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`. The parser treats a stored top-level struct as a root and keeps array indices exactly. Spawn and quest files were streamed root by root; no partial text search was used to derive their counts.

| CFG file | Lines | Top-level structs | Bytes |
| --- | --- | --- | --- |
| NPCPrototypes.cfg | 99339 | 1354 | 3387469 |
| ObjPrototypes.cfg | 1318780 | 1660 | 46786799 |
| LairPrototypes.cfg | 19795 | 75 | 918610 |
| SpawnActorPrototypes.cfg | 5068665 | 130058 | 183955505 |
| QuestPrototypes.cfg | 4990 | 1309 | 102673 |
| QuestNodePrototypes.cfg | 2366619 | 84244 | 77542782 |
| TradePrototypes.cfg | 3267 | 74 | 98974 |
| ItemGeneratorPrototypes.cfg | 277353 | 3086 | 9719947 |

`ItemGeneratorPrototypes.cfg`, `ObjPrototypes.cfg`, `NPCPrototypes.cfg`, `LairPrototypes.cfg`, `QuestNodePrototypes.cfg` and `TradePrototypes.cfg` are already standard extraction inputs. `SpawnActorPrototypes.cfg` is an existing optional input; a prototype-level implementation does not need to make this 184 MB decoded file mandatory. This audit by itself adds no extraction input or cache-schema change.

## The actual link chain

For Duty Close Combat, these are the exact stored values:

| File | Path | Vanilla value |
| --- | --- | --- |
| ObjPrototypes.cfg | `GeneralNPC_Duty_CloseCombat.Faction` | `Duty` |
| ObjPrototypes.cfg | `GeneralNPC_Duty_CloseCombat.ItemGeneratorPrototypeSID` | `GeneralNPC_Duty_CloseCombat_ItemGenerator` |
| ObjPrototypes.cfg | `GeneralNPC_Duty_CloseCombat.NPCPrototypeSID` | `GeneralNPC_Duty` |
| ObjPrototypes.cfg | `GeneralNPC_Duty_CloseCombat.TradePrototypeSID` | `GeneralNPC_TradePrototype_Duty` |
| NPCPrototypes.cfg | `GeneralNPC_Duty.QuestNPC` | `false` |
| NPCPrototypes.cfg | `GeneralNPC_Duty.UseGeneratedName` | `true` |
| NPCPrototypes.cfg | `GeneralNPC_Duty.NPCType` | `ENPCType::Trader` |
| TradePrototypes.cfg | `GeneralNPC_TradePrototype_Duty.TradeGenerators.[0].ItemGeneratorPrototypeSID` | `GeneralNPC_TradeItemGenerator_Duty` |

`NPCPrototypes.cfg` primarily supplies the dialog/name/quest metadata here; the equipment link and actual Faction are on the Obj. The generic Duty and Neutral metadata use `NPCType=Trader` to permit ordinary trading. Excluding every metadata `Trader` would wrongly remove nine ordinary profiles. All 50 selected Obj definitions themselves have `NPCType=ENPCType::None`.

The role tokens are `CloseCombat`, `Recon`, `Stormtrooper`, `Sniper`, and `Heavy`, with different availability per faction. They are roles, not progression ranks. Singular/plural identifiers differ between data families (`Mercenaries` Obj/generator, `GeneralNPC_Mercenary` metadata; `Militaries` vs `GeneralNPC_Military`). Use audited identifiers and the live `Faction` value, not string inference alone.

## Rank means PlayerRank in these equipment tables

Generator slots use the explicit field `PlayerRank`, with `ERank::Newbie`, `ERank::Experienced`, `ERank::Veteran`, `ERank::Master` or comma-separated combinations. Lair quantity/archetype tables independently use `SpawnSettingsPerPlayerRanks`. A UI for these slots should call its selection **Player rank** or **Progression rank**, not claim to set a particular NPC's rank. The 50 ordinary Obj roots have no own `Rank` assignment. Individual spawn definitions can carry `Rank` / `OverrideRank`; that is a separate field and is outside this feature.

One exact lair example is:

`[0].Preset.PossibleInhabitantFactions.[0].SpawnSettingsPerPlayerRanks.Newbie.SpawnSettingsPerArchetypes.GeneralNPC_Duty_CloseCombat`

It has `MinQuantityPerArchetype=1`, `SpawnWeight=1.0`. The corresponding Newbie `MaxSpawnQuantity=5`; Experienced/Veteran/Master each use 8. These fields choose or size a spawn population, not the contents of the equipment lottery. Do not change them as part of equipment editing.

Across LairPrototypes there are **1,465 GeneralNPC archetype-key occurrences**, covering **78 distinct GeneralNPC object keys in 27 top-level lair roots**. Of those occurrences, **1,355** target the initial 50 main profiles. This includes definitions/test or template content, not active population counts.

## Full initial Obj allowlist and vanilla links

Every row has its own `ItemGeneratorPrototypeSID`, `refkey=NPCBase`, `Type=EObjType::NPC`, `NPCType=ENPCType::None`, `IsZombie=false`, and `CanProcessCorpses=true`. Its referenced metadata has `QuestNPC=false`, `UseGeneratedName=true`. These checks are baseline eligibility checks; they do not prove that all placements are outside quests.

| Obj SID | Faction | NPC metadata SID | Item generator SID | Obj root line |
| --- | --- | --- | --- | --- |
| GeneralNPC_Duty_CloseCombat | Duty | GeneralNPC_Duty | GeneralNPC_Duty_CloseCombat_ItemGenerator | 30752 |
| GeneralNPC_Duty_Recon | Duty | GeneralNPC_Duty | GeneralNPC_Duty_Recon_ItemGenerator | 31543 |
| GeneralNPC_Duty_Stormtrooper | Duty | GeneralNPC_Duty | GeneralNPC_Duty_Stormtrooper_ItemGenerator | 32334 |
| GeneralNPC_Duty_Sniper | Duty | GeneralNPC_Duty | GeneralNPC_Duty_Sniper_ItemGenerator | 33125 |
| GeneralNPC_Duty_Heavy | Duty | GeneralNPC_Duty | GeneralNPC_Duty_Heavy_ItemGenerator | 33916 |
| GeneralNPC_Freedom_CloseCombat | Freedom | GeneralNPC_Freedom | GeneralNPC_Freedom_CloseCombat_ItemGenerator | 34707 |
| GeneralNPC_Freedom_Recon | Freedom | GeneralNPC_Freedom | GeneralNPC_Freedom_Recon_ItemGenerator | 35498 |
| GeneralNPC_Freedom_Stormtrooper | Freedom | GeneralNPC_Freedom | GeneralNPC_Freedom_Stormtrooper_ItemGenerator | 36289 |
| GeneralNPC_Freedom_Sniper | Freedom | GeneralNPC_Freedom | GeneralNPC_Freedom_Sniper_ItemGenerator | 37080 |
| GeneralNPC_Monolith_CloseCombat | Monolith | GeneralNPC_Monolith | GeneralNPC_Monolith_CloseCombat_ItemGenerator | 37871 |
| GeneralNPC_Monolith_Recon | Monolith | GeneralNPC_Monolith | GeneralNPC_Monolith_Recon_ItemGenerator | 38662 |
| GeneralNPC_Monolith_Stormtrooper | Monolith | GeneralNPC_Monolith | GeneralNPC_Monolith_Stormtrooper_ItemGenerator | 39453 |
| GeneralNPC_Monolith_Sniper | Monolith | GeneralNPC_Monolith | GeneralNPC_Monolith_Sniper_ItemGenerator | 40244 |
| GeneralNPC_Mercenaries_CloseCombat | Mercenaries | GeneralNPC_Mercenary | GeneralNPC_Mercenaries_CloseCombat_ItemGenerator | 41035 |
| GeneralNPC_Mercenaries_Recon | Mercenaries | GeneralNPC_Mercenary | GeneralNPC_Mercenaries_Recon_ItemGenerator | 41826 |
| GeneralNPC_Mercenaries_Stormtrooper | Mercenaries | GeneralNPC_Mercenary | GeneralNPC_Mercenaries_Stormtrooper_ItemGenerator | 42617 |
| GeneralNPC_Mercenaries_Sniper | Mercenaries | GeneralNPC_Mercenary | GeneralNPC_Mercenaries_Sniper_ItemGenerator | 43408 |
| GeneralNPC_Militaries_CloseCombat | Militaries | GeneralNPC_Military | GeneralNPC_Militaries_CloseCombat_ItemGenerator | 44199 |
| GeneralNPC_Militaries_Recon | Militaries | GeneralNPC_Military | GeneralNPC_Militaries_Recon_ItemGenerator | 44990 |
| GeneralNPC_Militaries_Stormtrooper | Militaries | GeneralNPC_Military | GeneralNPC_Militaries_Stormtrooper_ItemGenerator | 45781 |
| GeneralNPC_Militaries_Sniper | Militaries | GeneralNPC_Military | GeneralNPC_Militaries_Sniper_ItemGenerator | 46572 |
| GeneralNPC_Militaries_Heavy | Militaries | GeneralNPC_Military | GeneralNPC_Militaries_Heavy_ItemGenerator | 47363 |
| GeneralNPC_Bandit_CloseCombat | Bandits | GeneralNPC_Bandit | GeneralNPC_Bandit_CloseCombat_ItemGenerator | 52109 |
| GeneralNPC_Bandit_Recon | Bandits | GeneralNPC_Bandit | GeneralNPC_Bandit_Recon_ItemGenerator | 52900 |
| GeneralNPC_Bandit_Stormtrooper | Bandits | GeneralNPC_Bandit | GeneralNPC_Bandit_Stormtrooper_ItemGenerator | 53691 |
| GeneralNPC_Bandit_Heavy | Bandits | GeneralNPC_Bandit | GeneralNPC_Bandit_Heavy_ItemGenerator | 54482 |
| GeneralNPC_Scientists_Recon | Scientists | GeneralNPC_Scientist | GeneralNPC_Scientists_Recon_ItemGenerator | 61601 |
| GeneralNPC_Scientists_Stormtrooper | Scientists | GeneralNPC_Scientist | GeneralNPC_Scientists_Stormtrooper_ItemGenerator | 62392 |
| GeneralNPC_Neutral_CloseCombat | Neutrals | GeneralNPC_Neutral | GeneralNPC_Neutral_CloseCombat_ItemGenerator | 63183 |
| GeneralNPC_Neutral_Recon | Neutrals | GeneralNPC_Neutral | GeneralNPC_Neutral_Recon_ItemGenerator | 63974 |
| GeneralNPC_Neutral_Sniper | Neutrals | GeneralNPC_Neutral | GeneralNPC_Neutral_Sniper_ItemGenerator | 64765 |
| GeneralNPC_Neutral_Stormtrooper | Neutrals | GeneralNPC_Neutral | GeneralNPC_Neutral_Stormtrooper_ItemGenerator | 65556 |
| GeneralNPC_Noon_CloseCombat | Noon | GeneralNPC_Noon | GeneralNPC_Noon_CloseCombat_ItemGenerator | 69511 |
| GeneralNPC_Noon_Recon | Noon | GeneralNPC_Noon | GeneralNPC_Noon_Recon_ItemGenerator | 70302 |
| GeneralNPC_Noon_Stormtrooper | Noon | GeneralNPC_Noon | GeneralNPC_Noon_Stormtrooper_ItemGenerator | 71093 |
| GeneralNPC_Noon_Sniper | Noon | GeneralNPC_Noon | GeneralNPC_Noon_Sniper_ItemGenerator | 71884 |
| GeneralNPC_Varta_CloseCombat | Varta | GeneralNPC_Varta | GeneralNPC_Varta_CloseCombat_ItemGenerator | 72675 |
| GeneralNPC_Varta_Recon | Varta | GeneralNPC_Varta | GeneralNPC_Varta_Recon_ItemGenerator | 73466 |
| GeneralNPC_Varta_Stormtrooper | Varta | GeneralNPC_Varta | GeneralNPC_Varta_Stormtrooper_ItemGenerator | 74257 |
| GeneralNPC_Varta_Sniper | Varta | GeneralNPC_Varta | GeneralNPC_Varta_Sniper_ItemGenerator | 75048 |
| GeneralNPC_Varta_Heavy | Varta | GeneralNPC_Varta | GeneralNPC_Varta_Heavy_ItemGenerator | 75839 |
| GeneralNPC_Spark_CloseCombat | Spark | GeneralNPC_Spark | GeneralNPC_Spark_CloseCombat_ItemGenerator | 84540 |
| GeneralNPC_Spark_Recon | Spark | GeneralNPC_Spark | GeneralNPC_Spark_Recon_ItemGenerator | 85331 |
| GeneralNPC_Spark_Stormtrooper | Spark | GeneralNPC_Spark | GeneralNPC_Spark_Stormtrooper_ItemGenerator | 86122 |
| GeneralNPC_Spark_Sniper | Spark | GeneralNPC_Spark | GeneralNPC_Spark_Sniper_ItemGenerator | 86913 |
| GeneralNPC_Corpus_CloseCombat | Corpus | GeneralNPC_Corpus | GeneralNPC_Corpus_CloseCombat_ItemGenerator | 87704 |
| GeneralNPC_Corpus_Recon | Corpus | GeneralNPC_Corpus | GeneralNPC_Corpus_Recon_ItemGenerator | 88495 |
| GeneralNPC_Corpus_Stormtrooper | Corpus | GeneralNPC_Corpus | GeneralNPC_Corpus_Stormtrooper_ItemGenerator | 89286 |
| GeneralNPC_Corpus_Sniper | Corpus | GeneralNPC_Corpus | GeneralNPC_Corpus_Sniper_ItemGenerator | 90077 |
| GeneralNPC_Corpus_Heavy | Corpus | GeneralNPC_Corpus | GeneralNPC_Corpus_Heavy_ItemGenerator | 90868 |

The explicit allowlist contains 12 main factions: Duty (5 roles), Freedom (4), Monolith (4), Mercenaries (4), Militaries (5), Bandits (4), Scientists (2), Neutrals (4), Noon (4), Varta (5), Spark (4), Corpus (5). This totals 50; no missing Heavy/Sniper role should be invented.

Additional GeneralNPC objects exist for NeutralMSOP, IkarVarta, EnemyVarta, SultanBandits, NeutralBandits and Diggers, plus SIRCAA/MALACHITE and prologue/custom variants. They are outside the first allowlist and are not implied by selecting a main faction. In total, 83 `GeneralNPC_` Obj roots directly name a `GeneralNPC_` generator, across 20 live Faction values. Do not silently merge their equipment links under the main factions.

## Inheritance isolation audit

The 50 main Obj roots have **82 direct descendants** through `refkey`, including zombies, psy NPCs, phantoms, Faust variants and cutscene objects. All 82 have an explicit own `ItemGeneratorPrototypeSID` in this decoded snapshot; **27** explicitly repeat the parent's vanilla SID, while 55 specify a different SID. None therefore needs to inherit a relinked parent's generator leaf in the audited CFG tree. Across the complete Obj file, no `Type=EObjType::NPC` root lacks an own generator leaf.

This is a data-level argument, not proof of engine runtime evaluation. A live availability check should scan descendants of any selected Obj, follow `refkey` safely, and fail closed if a descendant lacks an explicit generator assignment before crossing the selected ancestor. Do not rely only on current counts or names. Never patch a common `NPCBase` / `QuestNPCBase` parent. Do not write redundant vanilla patches into descendants to “protect” them: the own values already provide the static boundary.

All direct descendants are listed below. The last column identifies those with the same original generator SID as the ordinary parent.

| Ordinary parent | Descendant Obj SID | Own vanilla generator SID | Same as parent |
| --- | --- | --- | --- |
| GeneralNPC_Duty_CloseCombat | GeneralZombie_Duty_CloseCombat | GeneralZombie_Duty_CloseCombat_ItemGenerator | no |
| GeneralNPC_Duty_Recon | GeneralZombie_Duty_Recon | GeneralZombie_Duty_Recon_ItemGenerator | no |
| GeneralNPC_Duty_Recon | VortexDude | VortexDudeItemGenerator | no |
| GeneralNPC_Duty_Recon | GDEQ_Duty_DeadBody_ConcreteForest | GDEQ_Duty_DeadBody_ConcreteForest_ItemGenerator | no |
| GeneralNPC_Duty_Recon | GDEQ_Duty_DeadBody_Razliv | ConcretePlandNoteCorpseItemGenerator | no |
| GeneralNPC_Duty_Stormtrooper | GeneralZombie_Duty_Stormtrooper | GeneralZombie_Duty_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Duty_Sniper | GeneralZombie_Duty_Sniper | GeneralZombie_Duty_Sniper_ItemGenerator | no |
| GeneralNPC_Duty_Heavy | GeneralZombie_Duty_Heavy | GeneralZombie_Duty_Heavy_ItemGenerator | no |
| GeneralNPC_Freedom_CloseCombat | GeneralZombie_Freedom_CloseCombat | GeneralZombie_Freedom_CloseCombat_ItemGenerator | no |
| GeneralNPC_Freedom_Recon | GeneralZombie_Freedom_Recon | GeneralZombie_Freedom_Recon_ItemGenerator | no |
| GeneralNPC_Freedom_Stormtrooper | GeneralZombie_Freedom_Stormtrooper | GeneralZombie_Freedom_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Freedom_Sniper | GeneralZombie_Freedom_Sniper | GeneralZombie_Freedom_Sniper_ItemGenerator | no |
| GeneralNPC_Monolith_CloseCombat | GeneralZombie_Monolith_CloseCombat | GeneralZombie_Monolith_CloseCombat_ItemGenerator | no |
| GeneralNPC_Monolith_CloseCombat | FaustMonolith_CloseCombat | GeneralNPC_Monolith_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Monolith_CloseCombat | PsyNPC_Monolith_CloseCombat | GeneralNPC_Monolith_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Monolith_CloseCombat | PhantomNPC_Monolith_CloseCombat | GeneralNPC_Monolith_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Monolith_CloseCombat | C_E06_MQ04_ZoneIsAlive_Monolith_01 | GeneralNPC_Monolith_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Monolith_CloseCombat | C_E06_MQ04_ZoneIsAlive_Monolith_02 | GeneralNPC_Monolith_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Monolith_Recon | GeneralZombie_Monolith_Recon | GeneralZombie_Monolith_Recon_ItemGenerator | no |
| GeneralNPC_Monolith_Recon | PsyNPC_Monolith_Recon | GeneralNPC_Monolith_Recon_ItemGenerator | yes |
| GeneralNPC_Monolith_Stormtrooper | GeneralZombie_Monolith_Stormtrooper | GeneralZombie_Monolith_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Monolith_Stormtrooper | FaustMonolith_Stormtrooper | GeneralNPC_Monolith_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Monolith_Stormtrooper | PsyNPC_Monolith_Stormtrooper | GeneralNPC_Monolith_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Monolith_Sniper | GeneralZombie_Monolith_Sniper | GeneralZombie_Monolith_Sniper_ItemGenerator | no |
| GeneralNPC_Mercenaries_CloseCombat | GeneralZombie_Mercenary_CloseCombat | GeneralZombie_Mercenaries_CloseCombat_ItemGenerator | no |
| GeneralNPC_Mercenaries_CloseCombat | PsyNPC_Mercenaries_CloseCombat | GeneralNPC_Mercenaries_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Mercenaries_Recon | GeneralZombie_Mercenary_Recon | GeneralZombie_Mercenaries_Recon_ItemGenerator | no |
| GeneralNPC_Mercenaries_Recon | PsyNPC_Mercenaries_Recon | GeneralNPC_Mercenaries_Recon_ItemGenerator | yes |
| GeneralNPC_Mercenaries_Stormtrooper | GeneralZombie_Mercenary_Stormtrooper | GeneralZombie_Mercenaries_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Mercenaries_Stormtrooper | PsyNPC_Mercenaries_Stormtrooper | GeneralNPC_Mercenaries_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Mercenaries_Sniper | GeneralZombie_Mercenary_Sniper | GeneralZombie_Mercenaries_Sniper_ItemGenerator | no |
| GeneralNPC_Militaries_CloseCombat | GeneralZombie_Military_CloseCombat | GeneralZombie_Militaries_CloseCombat_ItemGenerator | no |
| GeneralNPC_Militaries_CloseCombat | PhantomNPC_Militaries_CloseCombat | GeneralNPC_Militaries_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Militaries_Recon | GeneralZombie_Military_Recon | GeneralZombie_Militaries_Recon_ItemGenerator | no |
| GeneralNPC_Militaries_Stormtrooper | GeneralZombie_Military_Stormtrooper | GeneralZombie_Militaries_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Militaries_Stormtrooper | GeneralZombieMilitaryReconRedForest | RC_Military_Zombie_RedForest_ItemGenerator | no |
| GeneralNPC_Militaries_Sniper | GeneralZombie_Military_Sniper | GeneralZombie_Militaries_Sniper_ItemGenerator | no |
| GeneralNPC_Militaries_Heavy | GeneralZombie_Military_Heavy | GeneralZombie_Militaries_Heavy_ItemGenerator | no |
| GeneralNPC_Bandit_CloseCombat | GeneralZombie_Bandit_CloseCombat | GeneralZombie_Bandit_CloseCombat_ItemGenerator | no |
| GeneralNPC_Bandit_CloseCombat | PsyNPC_Bandit_CloseCombat | GeneralNPC_Bandit_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Bandit_Recon | GeneralZombie_Bandit_Recon | GeneralZombie_Bandit_Recon_ItemGenerator | no |
| GeneralNPC_Bandit_Recon | PsyNPC_Bandit_Recon | GeneralNPC_Bandit_Recon_ItemGenerator | yes |
| GeneralNPC_Bandit_Stormtrooper | GeneralZombie_Bandit_Stormtrooper | GeneralZombie_Bandit_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Bandit_Stormtrooper | PsyNPC_Bandit_Stormtrooper | GeneralNPC_Bandit_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Bandit_Heavy | GeneralZombie_Bandit_Heavy | GeneralZombie_Bandit_Heavy_ItemGenerator | no |
| GeneralNPC_Scientists_Recon | GeneralZombie_Scientist_Recon | GeneralZombie_Scientists_Recon_ItemGenerator | no |
| GeneralNPC_Scientists_Recon | PhantomNPC_Scientists_Recon | GeneralNPC_Scientists_Recon_ItemGenerator | yes |
| GeneralNPC_Scientists_Stormtrooper | GeneralZombie_Scientist_Stormtrooper | GeneralZombie_Scientists_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Neutral_CloseCombat | GeneralZombie_Neutral_CloseCombat | GeneralZombie_Neutral_CloseCombat_ItemGenerator | no |
| GeneralNPC_Neutral_CloseCombat | PsyNPC_Neutral_CloseCombat | GeneralNPC_Neutral_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Neutral_CloseCombat | PsyNPC_Neutral_CloseCombat_Alt | GeneralNPC_Neutral_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Neutral_CloseCombat | PhantomNPC_Neutral_CloseCombat | GeneralNPC_Neutral_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Neutral_CloseCombat | PhantomNPC_Neutral_CloseCombat_Alt | GeneralNPC_Neutral_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Neutral_Recon | GeneralZombie_Neutral_Recon | GeneralZombie_Neutral_Recon_ItemGenerator | no |
| GeneralNPC_Neutral_Recon | PsyNPC_Neutral_Recon | GeneralNPC_Neutral_Recon_ItemGenerator | yes |
| GeneralNPC_Neutral_Recon | PsyNPC_Neutral_Recon_Alt | GeneralNPC_Neutral_Recon_ItemGenerator | yes |
| GeneralNPC_Neutral_Recon | SwampNoteCorpse | SwampNoteCorpseItemGenerator | no |
| GeneralNPC_Neutral_Sniper | GeneralZombie_Neutral_Sniper | GeneralZombie_Neutral_Sniper_ItemGenerator | no |
| GeneralNPC_Neutral_Stormtrooper | GeneralZombie_Neutral_Stormtrooper | GeneralZombie_Neutral_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Neutral_Stormtrooper | PsyNPC_Neutral_StormTrooper | GeneralNPC_Neutral_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Neutral_Stormtrooper | PsyNPC_Neutral_StormTrooper_Alt | GeneralNPC_Neutral_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Noon_CloseCombat | GeneralZombie_Noon_CloseCombat | GeneralZombie_Noon_CloseCombat_ItemGenerator | no |
| GeneralNPC_Noon_Recon | GeneralZombie_Noon_Recon | GeneralZombie_Noon_Recon_ItemGenerator | no |
| GeneralNPC_Noon_Stormtrooper | GeneralZombie_Noon_Stormtrooper | GeneralZombie_Noon_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Noon_Sniper | GeneralZombie_Noon_Sniper | GeneralZombie_Noon_Sniper_ItemGenerator | no |
| GeneralNPC_Varta_CloseCombat | GeneralZombie_Varta_CloseCombat | GeneralZombie_Varta_CloseCombat_ItemGenerator | no |
| GeneralNPC_Varta_CloseCombat | PsyNPC_Varta_CloseCombat | GeneralNPC_Varta_CloseCombat_ItemGenerator | yes |
| GeneralNPC_Varta_Recon | GeneralZombie_Varta_Recon | GeneralZombie_Varta_Recon_ItemGenerator | no |
| GeneralNPC_Varta_Recon | PsyNPC_Varta_Recon | GeneralNPC_Varta_Recon_ItemGenerator | yes |
| GeneralNPC_Varta_Stormtrooper | GeneralZombie_Varta_Stormtrooper | GeneralZombie_Varta_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Varta_Stormtrooper | PsyNPC_Varta_Stormtrooper | GeneralNPC_Varta_Stormtrooper_ItemGenerator | yes |
| GeneralNPC_Varta_Sniper | GeneralZombie_Varta_Sniper | GeneralZombie_Varta_Sniper_ItemGenerator | no |
| GeneralNPC_Varta_Heavy | GeneralZombie_Varta_Heavy | GeneralZombie_Varta_Heavy_ItemGenerator | no |
| GeneralNPC_Spark_CloseCombat | GeneralZombie_Spark_CloseCombat | GeneralZombie_Spark_CloseCombat_ItemGenerator | no |
| GeneralNPC_Spark_Recon | GeneralZombie_Spark_Recon | GeneralZombie_Spark_Recon_ItemGenerator | no |
| GeneralNPC_Spark_Stormtrooper | GeneralZombie_Spark_Stormtrooper | GeneralZombie_Spark_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Spark_Sniper | GeneralZombie_Spark_Sniper | GeneralZombie_Spark_Sniper_ItemGenerator | no |
| GeneralNPC_Corpus_CloseCombat | GeneralZombie_Corpus_CloseCombat | GeneralZombie_Corpus_CloseCombat_ItemGenerator | no |
| GeneralNPC_Corpus_Recon | GeneralZombie_Corpus_Recon | GeneralZombie_Corpus_Recon_ItemGenerator | no |
| GeneralNPC_Corpus_Stormtrooper | GeneralZombie_Corpus_Stormtrooper | GeneralZombie_Corpus_Stormtrooper_ItemGenerator | no |
| GeneralNPC_Corpus_Sniper | GeneralZombie_Corpus_Sniper | GeneralZombie_Corpus_Sniper_ItemGenerator | no |
| GeneralNPC_Corpus_Heavy | GeneralZombie_Corpus_Heavy | GeneralZombie_Corpus_Heavy_ItemGenerator | no |

## Why a direct shared-generator patch is too broad

There are **114** generator roots beginning `GeneralNPC_`. The current `gd.loot_generators()` accepts **105**, excluding the nine trade roots. This is not an ordinary-actor allowlist. It also admits prologue, No_Armor, special scientist and custom variants. There are **695 Obj roots** that directly name one of the 114 GeneralNPC generators, including 612 whose own name does not start `GeneralNPC_`.

The largest trap is `GeneralNPC_Neutral_Recon_ItemGenerator`: **586 Obj roots**, with **34 distinct Faction values**, name it directly. **472** reference metadata with `QuestNPC=true` and `UseGeneratedName=false`. Example: `Batya.ItemGeneratorPrototypeSID=GeneralNPC_Neutral_Recon_ItemGenerator`, `Batya.NPCPrototypeSID=Bata`; its Obj has `refkey=QuestNPCBase`. These are stored default links; quest scripts can install different inventories later. They establish potential shared scope, not proof that every one of those NPCs always uses Neutral Recon at runtime.

`GeneralNPC_Bandit_CloseCombat_ItemGenerator` is directly used by the named quest objects `BanditGosan` and `BanditVentil`; `GeneralNPC_Bandit_Recon_ItemGenerator` by `BanditKesaOtbitok`. That sharing is reinforced by explicit quest SetItemGenerator nodes below.

The following complete table lists direct Obj consumers for every GeneralNPC generator. Quest/name columns count metadata flags on those consumers. “Caller generators” counts direct `ItemGeneratorPrototypeSID` links inside ItemGeneratorPrototypes only; it does not count inheritance or resolve runtime quest state.

| Generator SID | Current loot-safe | Direct Obj consumers | Quest=true | Generated name=false | Caller generators |
| --- | --- | --- | --- | --- | --- |
| GeneralNPC_Consumables | yes | 0 | 0 | 0 | 0 |
| GeneralNPC_Consumables_Recon | yes | 0 | 0 | 0 | 239 |
| GeneralNPC_Consumables_Noon | yes | 0 | 0 | 0 | 60 |
| GeneralNPC_Consumables_CloseCombat | yes | 0 | 0 | 0 | 159 |
| GeneralNPC_Consumables_Sniper | yes | 0 | 0 | 0 | 40 |
| GeneralNPC_Consumables_Stormtrooper | yes | 0 | 0 | 0 | 281 |
| GeneralNPC_Consumables_Armored | yes | 0 | 0 | 0 | 0 |
| GeneralNPC_Consumables_Heavy | yes | 0 | 0 | 0 | 29 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator | yes | 6 | 0 | 0 | 0 |
| GeneralNPC_Neutral_Recon_ItemGenerator | yes | 586 | 472 | 472 | 0 |
| GeneralNPC_Neutral_Sniper_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Neutral_Stormtrooper_ItemGenerator | yes | 4 | 0 | 0 | 0 |
| GeneralNPC_Bandit_Armor | yes | 0 | 0 | 0 | 143 |
| GeneralNPC_Bandit_CloseCombat_ItemGenerator | yes | 6 | 2 | 2 | 0 |
| GeneralNPC_Bandit_Recon_ItemGenerator | yes | 5 | 1 | 1 | 0 |
| GeneralNPC_Bandit_Stormtrooper_ItemGenerator | yes | 4 | 0 | 0 | 0 |
| GeneralNPC_Bandit_Heavy_ItemGenerator | yes | 3 | 0 | 0 | 0 |
| GeneralNPC_Mercenaries_Armor | yes | 0 | 0 | 0 | 29 |
| GeneralNPC_Mercenaries_CloseCombat_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Mercenaries_Recon_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Mercenaries_Stormtrooper_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Mercenaries_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Scientists_Armor | yes | 0 | 0 | 0 | 37 |
| GeneralNPC_Scientists_Recon_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Scientists_Stormtrooper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Militaries_Armor | yes | 0 | 0 | 0 | 29 |
| GeneralNPC_Militaries_CloseCombat_ItemGenerator | yes | 3 | 0 | 0 | 0 |
| GeneralNPC_Militaries_Recon_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Militaries_Stormtrooper_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Militaries_Sniper_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Militaries_Heavy_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Monolith_Armor | yes | 0 | 0 | 0 | 22 |
| GeneralNPC_Monolith_CloseCombat_ItemGenerator | yes | 6 | 0 | 1 | 0 |
| GeneralNPC_Monolith_Recon_ItemGenerator | yes | 2 | 0 | 0 | 0 |
| GeneralNPC_Monolith_Stormtrooper_ItemGenerator | yes | 3 | 0 | 1 | 0 |
| GeneralNPC_Monolith_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Duty_Armor_Experienced_var1 | yes | 0 | 0 | 0 | 1 |
| GeneralNPC_Duty_Armor_Experienced_var2 | yes | 0 | 0 | 0 | 1 |
| GeneralNPC_Duty_Armor | yes | 0 | 0 | 0 | 40 |
| GeneralNPC_Duty_CloseCombat_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Duty_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Duty_Stormtrooper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Duty_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Duty_Heavy_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Freedom_Armor | yes | 0 | 0 | 0 | 35 |
| GeneralNPC_Freedom_CloseCombat_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Freedom_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Freedom_Stormtrooper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Freedom_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Varta_Armor | yes | 0 | 0 | 0 | 142 |
| GeneralNPC_Varta_CloseCombat_ItemGenerator | yes | 4 | 0 | 0 | 0 |
| GeneralNPC_Varta_Recon_ItemGenerator | yes | 4 | 0 | 0 | 0 |
| GeneralNPC_Varta_Stormtrooper_ItemGenerator | yes | 4 | 0 | 0 | 0 |
| GeneralNPC_Varta_Sniper_ItemGenerator | yes | 3 | 0 | 0 | 0 |
| GeneralNPC_Varta_Heavy_ItemGenerator | yes | 3 | 0 | 0 | 0 |
| GeneralNPC_Noon_Armor | yes | 0 | 0 | 0 | 40 |
| GeneralNPC_Noon_CloseCombat_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Noon_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Noon_Stormtrooper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Noon_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Spark_Armor | yes | 0 | 0 | 0 | 46 |
| GeneralNPC_Spark_CloseCombat_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Spark_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Spark_Stormtrooper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Spark_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Corpus_Armor | yes | 0 | 0 | 0 | 25 |
| GeneralNPC_Corpus_CloseCombat_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Corpus_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Corpus_Stormtrooper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Corpus_Sniper_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Corpus_Heavy_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Neutral_WeaponPistol | yes | 0 | 0 | 0 | 201 |
| GeneralNPC_Bandit_WeaponPistol | yes | 0 | 0 | 0 | 139 |
| GeneralNPC_Mercenaries_WeaponPistol | yes | 0 | 0 | 0 | 29 |
| GeneralNPC_Scientists_WeaponPistol | yes | 0 | 0 | 0 | 37 |
| GeneralNPC_Militaries_WeaponPistol | yes | 0 | 0 | 0 | 29 |
| GeneralNPC_Monolith_WeaponPistol | yes | 0 | 0 | 0 | 21 |
| GeneralNPC_Duty_WeaponPistol | yes | 0 | 0 | 0 | 35 |
| GeneralNPC_Freedom_WeaponPistol | yes | 0 | 0 | 0 | 31 |
| GeneralNPC_Varta_WeaponPistol | yes | 0 | 0 | 0 | 137 |
| GeneralNPC_Noon_WeaponPistol | yes | 0 | 0 | 0 | 36 |
| GeneralNPC_Spark_WeaponPistol | yes | 0 | 0 | 0 | 46 |
| GeneralNPC_Corpus_WeaponPistol | yes | 0 | 0 | 0 | 20 |
| GeneralNPC_Neutral_NVG | yes | 0 | 0 | 0 | 196 |
| GeneralNPC_Bandit_NVG | yes | 0 | 0 | 0 | 137 |
| GeneralNPC_Mercenaries_NVG | yes | 0 | 0 | 0 | 29 |
| GeneralNPC_Militaries_NVG | yes | 0 | 0 | 0 | 28 |
| GeneralNPC_Monolith_NVG | yes | 0 | 0 | 0 | 18 |
| GeneralNPC_Duty_NVG | yes | 0 | 0 | 0 | 34 |
| GeneralNPC_Freedom_NVG | yes | 0 | 0 | 0 | 31 |
| GeneralNPC_Varta_NVG | yes | 0 | 0 | 0 | 137 |
| GeneralNPC_Spark_NVG | yes | 0 | 0 | 0 | 46 |
| GeneralNPC_Corpus_NVG | yes | 0 | 0 | 0 | 20 |
| GeneralNPC_Bandit_Recon_ItemGenerator_Prolog_Obrez | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Bandit_Recon_ItemGenerator_Prolog_AKU | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Duty | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Freedom | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Mercenary | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Militaries | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Bandit | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Scientists | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Spark | no | 0 | 0 | 0 | 0 |
| GeneralNPC_TradeItemGenerator_Corpus | no | 0 | 0 | 0 | 0 |
| GeneralNPC_SIRCAA_Scientist_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_MALACHITE_Scientist_Recon_ItemGenerator | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Militaries_Armor_var2 | yes | 0 | 0 | 0 | 1 |
| GeneralNPC_Militaries_Armor_var1 | yes | 0 | 0 | 0 | 1 |
| GeneralNPC_Neutral_Recon_No_Armor_ItemGenerator | yes | 0 | 0 | 0 | 0 |
| GeneralNPC_Neutral_Stormtrooper_No_Armor_ItemGenerator | yes | 0 | 0 | 0 | 0 |
| GeneralNPC_Neutral_CloseCombat_No_Armor_ItemGenerator | yes | 0 | 0 | 0 | 0 |
| GeneralNPC_Neutral_Sniper_ItemGeneratorCustom | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator_Prolog | yes | 1 | 0 | 0 | 0 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator_Prolog_Medkit | yes | 0 | 0 | 0 | 0 |

Helper tables are shared even when the top-level role generator is distinct. For example, the exact path `GeneralNPC_Duty_Recon_ItemGenerator.ItemGenerator.[3].PossibleItems.[1].ItemGeneratorPrototypeSID` has the value `GeneralNPC_Duty_WeaponPistol` (Chance 0.25 on the same row) and must be re-read from live data before use; helper references should be discovered structurally, never copied from an assumed array index. A cloned role root must continue reading untouched helpers from the original table unless the selected edit requires a private helper clone. Armor and pistol helper edits otherwise affect other roles, zombies and named-NPC generator branches too. Consumable helpers are role-wide rather than faction-specific; Recon and Stormtrooper consumables also have trader-named generator callers. Trade inventory and on-person inventory are distinct branches and must not be conflated.

## Explicit quest generator assignments

QuestNodePrototypes contains **26** `ItemGeneratorSID` references to **12** actual GeneralNPC generator roots. Every entry below is a `SetItemGenerator` node. Keep these unchanged; they will continue to refer to vanilla generators after ordinary Obj relinking. Their presence alone refutes an assertion that direct vanilla generator edits never affect quests.

| Exact quest path | Vanilla generator SID | Root line |
| --- | --- | --- |
| E02_SQ01_SetItemGenerator_BP_NPCPlaceholder_KesaOtbitok.ItemGeneratorSID | GeneralNPC_Bandit_Recon_ItemGenerator | 182152 |
| E02_SQ01_SetItemGenerator_BP_NPCPlaceholder_Goshan.ItemGeneratorSID | GeneralNPC_Bandit_CloseCombat_ItemGenerator | 182163 |
| E02_SQ01_SetItemGenerator_BP_NPCPlaceholder_ForDeath.ItemGeneratorSID | GeneralNPC_Bandit_Recon_ItemGenerator | 182174 |
| E02_SQ01_SetItemGenerator_BP_NPCPlaceholder_Bandit2.ItemGeneratorSID | GeneralNPC_Bandit_Recon_ItemGenerator | 182196 |
| E02_SQ01_SetItemGenerator_BP_NPCPlaceholder_Bandit.ItemGeneratorSID | GeneralNPC_Bandit_Recon_ItemGenerator | 182207 |
| E02_SQ01_SetItemGenerator_BP_NPC_VentelBandit.ItemGeneratorSID | GeneralNPC_Bandit_CloseCombat_ItemGenerator | 182218 |
| E02_SQ01_SetItemGenerator_BP_NPCPlaceholder_Bandit3.ItemGeneratorSID | GeneralNPC_Bandit_CloseCombat_ItemGenerator | 182229 |
| E03_SQ01_SetItemGenerator_BP_NPC_E03_SQ01_GosaMogila.ItemGeneratorSID | GeneralNPC_Bandit_Stormtrooper_ItemGenerator | 271490 |
| E08_EQ01_P_SetItemGenerator_DutyCernyh.ItemGeneratorSID | GeneralNPC_Duty_Recon_ItemGenerator | 580316 |
| E08_EQ01_P_SetItemGenerator_DutyLapin.ItemGeneratorSID | GeneralNPC_Duty_WeaponPistol | 580337 |
| E11_MQ01_SetItemGenerator_BP_NPC_FimaSemafor.ItemGeneratorSID | GeneralNPC_Bandit_Stormtrooper_ItemGenerator | 774661 |
| E11_MQ01_SetItemGenerator_BP_NPC_Mona.ItemGeneratorSID | GeneralNPC_Bandit_Stormtrooper_ItemGenerator | 774691 |
| E11_MQ01_SetItemGenerator_BP_NPC_Bora.ItemGeneratorSID | GeneralNPC_Bandit_CloseCombat_ItemGenerator | 774721 |
| E11_MQ02_SetItemGenerator_BP_NPC_SparkVeles.ItemGeneratorSID | GeneralNPC_Spark_Recon_ItemGenerator | 784991 |
| E11_MQ02_SetItemGenerator_BP_NPC_SparkLovcij.ItemGeneratorSID | GeneralNPC_Spark_Stormtrooper_ItemGenerator | 785012 |
| E11_MQ02_SetItemGenerator_BP_NPC_SparkKruk.ItemGeneratorSID | GeneralNPC_Spark_Sniper_ItemGenerator | 785033 |
| EQ101_SetItemGenerator_Cekan_SecondBody_FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_Stormtrooper_No_Armor_ItemGenerator | 1008035 |
| EQ101_SetItemGenerator_Cekan_ThirdBody_FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_CloseCombat_No_Armor_ItemGenerator | 1008123 |
| EQ101_SetItemGenerator_Cekan_FirstBody__FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_Recon_No_Armor_ItemGenerator | 1008184 |
| EQ101_SetItemGenerator_Cekan_SecondBody_FixLooting.ItemGeneratorSID | GeneralNPC_Neutral_Stormtrooper_No_Armor_ItemGenerator | 1008214 |
| EQ101_C01_SetItemGenerator_Cekan_FirstBody__FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_Recon_No_Armor_ItemGenerator | 1009332 |
| EQ101_C01_SetItemGenerator_Cekan_SecondBody_FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_Stormtrooper_No_Armor_ItemGenerator | 1009402 |
| EQ101_C02_SetItemGenerator_Cekan_FirstBody__FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_Recon_No_Armor_ItemGenerator | 1010345 |
| EQ101_C02_SetItemGenerator_Cekan_SecondBody_FixLoot.ItemGeneratorSID | GeneralNPC_Neutral_Stormtrooper_No_Armor_ItemGenerator | 1010406 |
| EQ32_SetItemGenerator_BP_NPC_EQ32_Gerc_Fix.ItemGeneratorSID | GeneralNPC_Bandit_WeaponPistol | 1115765 |
| EQ32_SetItemGenerator_BP_NPC_EQ32_BanditDimaVertuha_Fix.ItemGeneratorSID | GeneralNPC_Bandit_WeaponPistol | 1115845 |

One additional source value, `EQ101_C01_SetItemGenerator_Cekan_SecondBody.ItemGeneratorSID=GeneralNPC_Neutral_Stormtrooper`, is **not** a generator SID in ItemGeneratorPrototypes; it matches an Obj SID instead. Exclude this unresolved reference from the 26 valid generator assignments and do not “repair” it in this feature.

## Spawn placement scope

For the initial 50 Obj SIDs, SpawnActorPrototypes stores **3,023 `SpawnedPrototypeSID` occurrences** (including squad members). Four additional occurrences are `AllowedUserRestriction` strings in contextual-action preconditions and are not spawn references. The generic prototypes appear in both world and test content. Specific quest-level examples:

| Exact SpawnActor path | Obj SID | LevelName |
| --- | --- | --- |
| `F51804814344086386240B88683503C3.SpawnedPrototypeSID` | `GeneralNPC_Bandit_Recon` | `WorldMap_WP/SQ95_LogicLevel_WP` |
| `8DD5A10547B08B8B97ED779C1CD399E2.SpawnedPrototypeSID` | `GeneralNPC_Neutral_Recon` | `WorldMap_WP/SQ97_LogicLevel_WP` |
| `46CEBE1B46E7095CBDFB1D9A54AEA196.SpawnedPrototypeSID` | `GeneralNPC_Mercenaries_CloseCombat` | `WorldMap_WP/SQ98_LogicLevel_WP` |

The same ordinary Obj root may therefore serve A-Life, placed enemies, squads, dead bodies and quest-level opponents. Per-Obj generator cloning can avoid editing separate named/special Obj IDs and direct quest generator definitions, but cannot separate uses of the same Obj prototype by map/quest placement. Do not add a placement filter that merely checks `SpawnOnStart`; scripted spawns are real gameplay too.

## Current filter review and prohibited candidates

The shipped method corresponding to “npc_gear_pools” is `gd.gear_weight_pools()`; there is no method literally named `npc_gear_pools` in the audited tree. It currently returns **4,153** weighted gear pools in **840** accepted generator roots. Only **77** of those generator roots begin `GeneralNPC_`; 763 do not. It is designed for the existing broad loot-quality control, not a faction editor.

`loot_generators()` excludes the template `[0]`, duplicate keys, explicit denylist, transitively linked trade stock, known story/reward/container/trade names, dev All* generators, and roots directly containing unknown, quest-flagged or unique `Gun_<Name>` items. Its content check is not a recursive ordinary-actor ownership proof. `_ordinary_npc_groups()` adds only the `GeneralNPC_` prefix; the prologue and No_Armor/custom roots therefore still pass that helper. Reuse row validation where useful, but introduce a stricter explicit Obj/profile allowlist for this feature.

Do not offer these as automatic candidates:

- Common templates/base roots; named NPCs, bosses, psy/phantom/zombie/cutscene roots; prologue variants and special quest No_Armor generators.
- Trader stock (`GeneralNPC_TradeItemGenerator*`, TradePrototypes links or the stock graph); keep a generic NPC's ordinary on-person equipment distinct from its trade stock.
- Quest items marked by either `IsQuestItem` or `IsQuestItemPrototype`; unknown SIDs; unique `Gun_<Name>` weapons; invisible/template/DestroyOnPickup items; collar items, money cards and quest-name matches. A specific weapon picker must independently validate the selected item, not assume that a safe-looking generator name makes every row safe.
- Edition/preorder/unlock variants added from a global weapon catalog. Current item `DLC` fields are not a reliable edition gate: only 25 item roots carry that field, all `BaseGame`, and they are consumables. ItemGeneratorPrototypes has no DLC/Edition field. Use only verified existing ordinary-pool candidates initially, and do not infer unrestricted availability from a missing DLC field.

`GamePass_Stash_*` is not automatically paid content: the repository's earlier audit established ordinary base-game stash uses. Nevertheless `GeneralNPC_Neutral_Sniper_ItemGeneratorCustom` calls `GamePass_Stash_ItemGenerator_Rare` and is outside the 50 ordinary profiles for its custom scope; exclude it by exact profile boundary rather than mislabelling its stash helper.

## Practical initial scope

Build the editor around the 50 explicit main-faction roles and their existing `PlayerRank` slots. Provide per-role or faction-group edits only by creating new generator branches and relinking those selected Obj roots. Start with weights/choices among existing validated equipment candidates; any changed shared helper needs a private clone. Preserve native array keys, slot categories, difficulty/rank constraints and unrelated counts/condition/ammo metadata. Show that ordinary enemies in quests can share these profiles, and that already-generated inventory may require new spawns.

The data supports this implementation route without UE4SS. It does not establish engine acceptance or live-game behavior; those remain test obligations. No production files, game installation, saves or release state were changed by this audit.
