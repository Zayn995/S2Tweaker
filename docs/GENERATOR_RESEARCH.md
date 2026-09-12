# Item generators: loot, drops, traders and stashes

Research snapshot: 2026-09-01. Counts describe the inspected game files and
initial filter analysis, not constants for the application. The implementation
reads current installation values through `gd.resolve` and related accessors.

The completed filter review corrected four early assumptions: money also exists
as items (`MoneyCommon/Rare/Epic/Legendary`, `EEffectType::AddMoney`); quest items
can use `IsQuestItemPrototype` as well as `IsQuestItem`; trader membership must
not transitively blacklist unrelated loot; and exclusion patterns apply to item
SIDs too. **291 items carry only the second quest marker.** `Electrocollar` is
not itself marked `IsQuestItem = true`. The inspected generator file has no
duplicate top-level keys; the earlier claim of four identical `LesserZone_Cabin`
keys was incorrect. See `gamedata.loot_generators()` for the resulting filter.

## Files and scope

| File | Lines | Top-level structs | Size |
|---|---|---|---|
| ItemGeneratorPrototypes.cfg | 277,318 | 3,085 | 9.3 MB |
| StashPrototypes.cfg | 10,681 | 19 | 0.4 MB |

Related files are DifficultyPrototypes (11 structs, CorpseSmartLoot),
TradePrototypes (74 structs), ObjPrototypes (1,659 NPC prototypes),
ItemPrototypes (quest markers), and SpawnActorPrototypes (stash assignments).

Loot quantity, weapon condition, trader stock and stash contents use different
paths and filters. They must remain separate controls. The initial analysis
identified 2,049 candidate loot generators after filtering, but that count
predates the additional quest/money checks above and is not a current allowlist.
Stashes are much smaller; weapon condition can require about 23,000 patch lines
because those values are locally defined rather than inherited.

## ItemGeneratorPrototypes structure

Five levels, normally indented by three spaces:

```text
Prototype key
   ItemGenerator | MoneyGenerator
      [N] or named slot, with Category and filters
         PossibleItems
            [M] candidate item and numeric values
```

For example, `SimpleFoodGenerator.ItemGenerator.[0].PossibleItems.[0]` contains
Bread, Weight 4, MinCount 1 and MaxCount 1. This is an illustrative snapshot;
patch addressing must come from the parsed file.

There are 28 distinct field names across 153,578 assignment lines:

| Field | Count | Level |
|---|---|---|
| ItemPrototypeSID | 23,469 | Item |
| Weight | 17,520 | Item |
| Category | 13,940 | Slot |
| MinDurability / MaxDurability | 12,987 / 12,984 | Item |
| AmmoMinCount / AmmoMaxCount | 12,375 / 12,371 | Item |
| Chance | 10,587 | Item |
| MinCount / MaxCount | 6,962 / 6,147 | Item and MoneyGenerator |
| PlayerRank | 6,941 | Slot |
| ItemGeneratorPrototypeSID | 4,752 | Subgenerator reference |
| SID | 3,085 | Prototype |
| SpecificRewardSound | 2,485 | Prototype |
| Diff | 2,364 | Slot |
| bAllowSameCategoryGeneration | 2,003 | Slot |
| bRequireWeapon | 1,103 | Item |
| RefreshTime | 799 | Prototype; 794 `1d`, five `1h` |
| weight | 152 | Lowercase vanilla spelling |
| ID | 66 | Prototype |
| bUnloadedWeapon / ReputationThreshold / AmmoMaxcount | 5 / 4 / 4 | Rare fields |
| bRequireAmmo / GeneratedItems / Binoculars_03 | 1 each | Includes malformed vanilla fields |

The initial filtered category counts were WeaponPrimary 3,858, SubItemGenerator
3,334, BodyArmor 1,670, Head 1,255, Detector 838, Artifact 817, Consumable 297,
WeaponPistol 210, Junk 150, Ammo 144, Attach 102, WeaponSecondary 98, Mask 75,
NightVision 30, MutantLoot 15 and None 1.

## Numeric controls

### Quantities

The same field names occur in different semantic contexts:

| Path | MinCount | MaxCount | Meaning |
|---|---|---|---|
| PossibleItems.[j] | 6,479 | 5,665 | Item quantity |
| Prototype.MoneyGenerator | 372 | 372 | Money, excluded from item-quantity scaling |
| ItemGenerator.Consumable.PossibleItems.[j] | 83 | 83 | Named slot |
| PossibleItems.[j].Upgrades | 20 | 19 | Weapon upgrades |
| PossibleItems.[j].Attaches | 8 | 8 | Attachments |

Across PossibleItems and nested forms, MinCount has 6,590 occurrences and
MaxCount 5,775. Common minimums: 1 (4,289), 2 (400), 10 (342), 5 (301), 30 (195).
Common maximums: 1 (3,070), 2 (494), 3 (333), 10 (278), 5 (231).
There are 3,895 fixed quantities and 1,853 ranges, with no Min > Max in that
generator subset. The common pair 1/1 occurs 3,029 times. **814 entries have
MinCount without MaxCount**, 807 of them equal to 1; none has only MaxCount.

### Ammunition inside a found weapon

`AmmoMinCount/AmmoMaxCount` are ammunition amounts, not numbers of weapons.
84.99% of minimums are zero. Common maximums are 7 (4,493), 6 (2,635) and
5 (2,602); 0/7 occurs 4,486 times. 92.7% belong to WeaponPrimary. The 315
Consumable entries at 0/0 remain unchanged under multiplicative scaling.

### Condition

12,981 regular entries contain condition values, about 46.5% of PossibleItems:

| Min / Max | Count | Typical use |
|---|---|---|
| 0.25 / 0.5 | 11,431 | Looted weapons |
| 1.0 / 1.0; 1 / 1; 1. / 1. | 415; 220; 13 | New condition in three numeric spellings |
| 0.0 / 0.0 | 319 | Placeholders, often quest rewards |
| 0.4 / 0.9 | 263 | Mostly secondary weapons |
| 0.8 / 0.9 | 162 | Mostly pistols |
| 0.45 / 0.45 | 64 | Mostly artifacts |

WeaponPrimary has 11,209 of 11,572 entries at 0.25/0.5. BodyArmor has 272
of 278 at new condition; Head has 83 of 84. A blanket reduction would create
damaged armor where vanilla normally provides new armor. Keep these categories
separate. None of the 12,981 regular condition entries inherits its values.

### Chance versus Weight

Weight represents weighted selection; Chance represents independent item rolls.
Do not normalize chance lists to a total of one. Only two of 621 lists with at
least three entries sum to one; `Monolit_bench_1_ItemGenerator`, for example,
contains 13 entries at Chance 1.0. Weight totals range from zero to 4,100.

Of 27,889 entries, 17,329 have Weight only, 10,222 Chance only, 337 both and one
neither. Mixed entries require care; the presence of a Weight key alone is not
proof of the behavior of every nested generator. Increasing quantity changes
the selected item's amount, not necessarily the number of independent rolls.

## Inheritance and addressing

- 2,607 of 3,085 structs have refurl/refkey metadata; 1,773 reference `[0]`,
  the empty base template. **Never patch that template for general loot.**
- `refkey=[N]` is positional. Eighty-eight structs reference `[1]`, whose
  actual second top-level key is `MoneyGenerator`.
- Many refurl source files were merged during packaging and do not exist as
  separate files. Resolve the merged structure rather than opening arbitrary
  refurl paths. 2,519 of 2,607 refkeys resolve within the inspected file;
  missing-source inheritance remains a data limitation.
- 226 structs use indexed keys; 239 have a key different from their SID.
  Addressing an indexed struct by SID can create a new ineffective node.
- Named slots coexist with indexed slots. The initial scan identified 724
  relevant direct-child groups, including Head, BodyArmor, Consumable,
  WeaponPrimary, WeaponPistol and Attach. Read actual paths from the parser.
- Numeric and Boolean spellings vary (`1`, `1.`, `1.0`, `4.f`, `True`, `false`).
  Compare parsed values numerically to avoid redundant patches.

## Exclusions

Generator names do not contain reliable quest-item flags. Resolve both
`IsQuestItem` and `IsQuestItemPrototype` in ItemPrototypes, including inheritance.
The original IsQuestItem-only scan found 327 true assignments and 326 resolved
items; that was incomplete without the second marker.

Apply exclusions to struct keys, generator SIDs and contained item SIDs. The
initial name pattern covered quest prefixes MQ/EQ/SQ/RSQ/ANCQ, Quest, QSBIG,
GDEQ, Reward, C_, BP_, UAID_, Container, Template, Player, Boss, Arena,
GamePass, Key, Safe, Icon and PDA. It removed 918 structs, but names alone
missed quest keys and unique weapons. Inspect item content and subgenerators too.

Unique item IDs follow `Gun_<Name>_<Class>`, for example `Gun_Whip_SR`, unlike
ordinary `GunAK74_ST`. `_GS` identifies a weapon setup and is not a unique-item
test. The snapshot had 39 unique items, seven appearing in nine generators.

The preliminary two-stage filter left 2,162 structs, then 2,049 after trader
and aggregate-template exclusions. Those historical counts must not replace
the corrected item, money and graph checks in the implementation.

Preserve these boundaries:

1. Exclude MoneyGenerator counts and money-effect items from general quantities.
   MoneyGenerator values reach 72,500 at `SQ94_RSQ_reward_var11`.
2. Exclude story rewards, player starting equipment and unique-item distributors.
   Examples include `E01_MQ01_PlayerItemGenerator`, `E02_MQ01_PlayerItemGenerator`,
   `Stash_SQ01_ValenokStash`, Korshunov generators, `NeutralPaivka_ItemGenerator`,
   `SQ02_reward_var1` and `SQ20_reward_var5`.
3. Protect key/document generators such as `KeyGeneratorRedForest`,
   `MutantElectrocollarGenerator`, `CementPlant_IslandNearKopachi_Safe`,
   `GarbageDetCenterCorpseItemGenerator` and
   `GDEQ_Duty_DeadBody_ConcreteForest_ItemGenerator`.
4. Preserve indexed story distributors `[159]`, `[192]`, `[206]`, `[238]`,
   `[239]` and their icon/PDA/document contents.
5. Preserve empty assignments: 261 `ItemGenerator =` and 181 `PossibleItems =`
   intentionally clear inherited arrays.
6. Exclude development collections: AllPistols `[10]`, AllPrimaryWeapons `[11]`,
   AllAmmosGenerator `[12]`, AllBodyArmors `[13]`, AllHeads `[14]`, AllArtifacts
   `[15]`, AllConsumables `[16]`, AllDetectors `[17]`, AllAttaches `[18]`,
   AllTraderItemGenerator `[19]`. Some already generate quantities of 900.
7. Preserve lowercase `weight`, `AmmoMaxcount` and malformed fields instead
   of silently inventing corrected keys. `DefaultReward` contains the unusual
   `GeneratedItems` and `Binoculars_03` assignments.
8. Determine traders through references, not names. Seventeen names containing
   Trade/Trader represent real loot, while trader references can use other names.
9. Do not add missing MaxDurability to the three MinDurability-only entries.
   Skip the six Mercenaries generators with condition values one level too deep
   under `PossibleItems[1].[6]` (12 malformed lines).
10. Clamp condition to 0..1 and maintain Min <= Max without unrelated repairs.

## StashPrototypes

Nineteen structs include `empty`, a zero-valued schema inherited by the other
18. All numeric values are defined locally. The snapshot has 1,060 items and
470 parameter entries, with stable indices and no `[*]` arrays. No quest items,
unique items or condition fields were found in that stash scan.

Path structure: `<Stash>.ItemGenerators.[rank].SmartLootParams.<Group>.[j].Items.[k]`.
Groups are HealthParams and AttachParams (template-only), PrimaryWeaponParams,
SecondaryWeaponParams, PistolWeaponParams, ConsumablesParams and GrenadesParams.
Parameters include Min/MaxSpawnChance, MainWeaponAmmoCount, ItemSetCount,
PriorityCaliber and per-item MinCount/MaxCount/Weight or Chance.
Items use Weight 1,035 times and Chance 25 times.

| Corpse generator | Newbie | Experienced | Veteran | Master |
|---|---|---|---|---|
| NPC_Ammo_Smart | 4 entries | 5 | 7 | 8 |
| NPC_Medicine_Smart | Medkit 1–2, Bandage 2–4 | Adds Antirad | Adds ArmyMedkit | Antirad weight 5 |
| NPC_Water_Smart | Water 1–1 | Same | Same | Same |

All 39 entries use MinSpawnChance 0.1f. MaxSpawnChance is 0.8f for ammunition
and 0.7f for medicine/water. Of 2,972 map assignments, Empty accounts for 2,022;
StashMedicine_Smart and Stash_Ammo_Smart_CommonRare account for 753 and 86;
the Cheap ammunition combination adds 46, StashMedicine_Cheap 16 and
Stash_AmmoAll_Cheap 13. Four generators cover 2,937 assignments, including Empty.
That count does not authorize modifying the empty template.

### CorpseSmartLoot limitations

`EconomyDifficulty.CorpseSmartLoot` assigns generators only on Easy
(NPC_Medicine_Smart and NPC_Ammo_Smart) and Medium (NPC_Water_Smart).
Empty and Hard explicitly clear it; Stalker, Custom, Default and four Xbox
variants inherit empty values. There is no existing Hard/Stalker block to scale.
Creating one is a different operation whose runtime support was not established
by this research. NPCs also need `EnableSmartLootIfPossible = true`
(1,514 entries), so the feature must not promise to affect every corpse.

### Stash invariants

Do not patch `empty`: activating inherited entries with ItemPrototypeSID empty
could be invalid. Read available ranks and groups instead of assuming four
complete ranks. Seven structs have only `[0]`; twelve have `[0..3]`, and some
ranks omit entire groups. Preserve both PrimaryWeaponParams and
SecondaryWeaponParams where present, and preserve Chance versus Weight.

StashMedicine_Corpse and StashVodka_Corpse have no references in the snapshot.
Stash_AmmoSNG_Smart_MainLoot and Stash_AmmoNATO_Smart_MainLoot have zero maximum
spawn chance throughout; multiplication must preserve those disabled values.
Forty-two entries repeat item SIDs: deduplicating them would shift indices.
Numeric parsing must accept `0.`, `0`, `0.5` and suffixed forms.

Useful regression cases include the unique 0.9f MaxSpawnChance at
`NPC_Ammo_Smart.ItemGenerators[0].…PrimaryWeaponParams[1]` and the existing
stash inconsistency MinCount 25 > MaxCount 15 at
`Stash_AmmoNATO_Smart.ItemGenerators[3].…SecondaryWeaponParams[7].Items[0]`.
This stash inconsistency is distinct from the regular generator subset above.

## Traders

Reference chain: `ObjPrototypes.<NPC>.TradePrototypeSID` ->
`TradePrototypes.<Shop>.TradeGenerators.[i].ItemGeneratorPrototypeSID` ->
`ItemGeneratorPrototypes.<Generator>.ItemGenerator.<Slot>.PossibleItems.[j]`.

The initial transitive trader graph has 95 structs (68 roots, 27 shared
components); the NPC-loot graph has 963, with six shared structs. Trader entries
usually specify quantities (77.0%, versus 13.4% for loot) and use Chance rather
than Weight (892 of 904). Median ammunition quantities are 60/120 versus 10/15.
Twenty-seven shared components contain 334 of 696 quantity lines; the initial
non-development trader subset had 62 structs and 456 entries (912 values).

TradePrototypes separately provides Money, bInfiniteMoney and RefreshConditionSID.
ObjPrototypes defines both ItemGeneratorPrototypeSID and TradePrototypeSID on
all 1,659 NPC prototypes. GeneralNPC_Neutral_Recon_ItemGenerator is referenced
by 586 NPCs; 1,304 use NoTrade and 303 have an actual trade setup in this scan.
These counts describe different reference subsets and should not be treated
as a complete partition of all NPC types.

## Implementation checks

Use parsed paths, cross-file item classification, resolved inheritance,
separate money/item semantics and numeric comparisons. Neutral settings must
emit no patch. Important test cases include zero condition, three spellings of
new condition, missing maximum keys, named slots, indexed prototypes, malformed
nested condition fields and inactive stash groups. Runtime loot generation and
save refresh behavior still require in-game observation beyond structural tests.
