# NPC equipment: complete GeneralNPC generator baselines

Research snapshot: **2026-09-11, local S.T.A.L.K.E.R. 2 2.0.5 data**. This is a read-only CFG inventory, not an in-game validation or a released feature. All paths are relative to the repository. Numeric values below are documentation baselines; an implementation must obtain its values from the user's loaded installation.

Source: `vanilla/Stalker2/Content/GameLite/GameData/ItemGeneratorPrototypes.cfg`.
The current file has **277,353 lines, 3,086 top-level structs, and 9,719,947 bytes**; SHA-256 `b72648f0c8d400b2ddf69b60fedcb3805f028f69826b1975212ab19b3c6541d6`. Earlier counts in [GENERATOR_RESEARCH.md](GENERATOR_RESEARCH.md) describe an older snapshot and must not be reused for current controls.

## What “rank” actually means

These generator tables use **`PlayerRank`**, not NPC rank. Across the 114 `GeneralNPC_*` roots there are **444 slots with `PlayerRank`, zero slots with `Rank`, and 300 slots with no rank filter**. The four explicit enum ranks are `ERank::Newbie`, `ERank::Experienced`, `ERank::Veteran`, and `ERank::Master`. The appropriate UI wording is **Player progression / player rank**. A promise to equip individual NPC ranks differently cannot be justified from these tables alone; NPC prototype rank and the links selecting the generator are a separate investigation.

Many native slots cover several ranks together. Editing such a slot affects its entire native mask. Splitting a combined mask into independent rank controls would require adding/replacing slots and validating native selection behavior; a scalar patch cannot separate a single shared slot. A missing mask is not evidence that the slot belongs to one rank.

## Complete scope and exclusions

The prefix inventory contains **114 roots, 744 direct slots, 1,483 direct candidate rows, 126 distinct direct item SIDs and 44 distinct referenced generator SIDs**. There is also **one additional item-shaped child nested inside a candidate**, documented below. Direct candidate counts intentionally exclude that malformed nested child.

| Root family | Roots | Direct candidates | Interpretation |
|---|---:|---:|---|
| Ordinary faction / role | 50 | 896 | Narrow initial role scope; reference consumers still need auditing |
| Shared equipment helpers | 37 | 203 | Armor, helmets, pistols and night vision; shared across role consumers |
| Shared consumables | 8 | 142 | Not inherently isolated to a faction or role |
| Trade | 9 | 68 | Merchant stocks; exclude from NPC equipment editor |
| Prologue | 4 | 28 | Scripted opening variants; exclude |
| Site-specific scientists | 2 | 8 | SIRCAA / MALACHITE; exclude from ordinary faction controls |
| Special variants | 4 | 138 | Three No_Armor roots and a custom sniper; exclude |

The 50 ordinary role generators cover 12 naming families: Neutral, Bandit, Mercenaries, Scientists, Militaries, Monolith, Duty, Freedom, Varta, Noon, Spark, and Corpus. These names are the generator namespace, not a claim that the UI faction enum has identical spelling. For example, use the actual object-to-generator links before mapping `Mercenaries` to a game faction label.

The ordinary role subset has **480 slots**: 209 primary weapon, 148 sub-generator, 50 detector, 49 `Artifact`, 16 body armor and 8 head slots. Its 896 direct candidates comprise **653 weighted and 243 chance candidates**. There are 44 distinct direct item SIDs in this subset; shared helper items expand that coverage.

## Paths and full baseline CSV

[NPC_EQUIPMENT_BASELINES.csv](NPC_EQUIPMENT_BASELINES.csv) contains **every one of the 1,483 direct candidate rows**, including excluded families. Each row records the actual struct key and SID, source, family, role/helper, `refkey`, root values, real slot/candidate indices, category, raw player-rank and difficulty masks, extra slot fields, item or sub-generator SID, selection mechanism, weight/chance, count, ammo, durability, and all candidate leaves as JSON. Empty cells mean **the field is absent locally**, not zero. `candidate_all_values` retains the exceptional nested child with its full relative path.

The patch path is exactly:

`<struct_key>.ItemGenerator.<slot>.PossibleItems.<candidate>.<field>`

For example: `GeneralNPC_Neutral_CloseCombat_ItemGenerator.ItemGenerator.[0].PossibleItems.[0].Weight = 1000`.

The CSV is a baseline artifact, not a patch list: it deliberately includes entries that must not be exposed or modified. Its `root_values` and `candidate_all_values` fields allow lossless auditing of all relevant local leaves without embedding raw game structs in production code.

## Weights, chance, durability and ammo

All 744 direct lists are internally consistent: **411 lists use only `Weight` (921 candidates); 333 lists use only `Chance` (562 candidates)**. There are no direct candidates with both fields and none with neither. Weighted values range from **0.1 to 1000**. Chance values range from **0 to 1**, with eight explicit zeroes, all in the two Bandit prologue variants.

The data distinguishes a relative selection weight from a chance value. Within a weighted pool, an isolated multiplier changes relative selection frequency; multiplying every candidate equally leaves the ratios unchanged. For a chance list, entries should retain their independent chance semantics; do not normalize them to sum to one. These are CFG-based interpretations consistent with the existing loot research, not a new runtime test of the engine.

Concrete check: Neutral CloseCombat / Newbie / Easy+Medium+Hard has Obrez 1000 and TOZ 100. The relative shares are `1000 / 1100 = 90.909%` and `100 / 1100 = 9.091%`. Doubling only TOZ produces weights 1000 and 200, hence `83.333%` and `16.667%`. If preserving the native pool sum is desired, renormalized weights are approximately 916.666667 and 183.333333. Either method must leave unrelated pools untouched and reject an all-zero weighted pool.

Known owned candidate scalar fields: `MinDurability` and `MaxDurability` each occur **712 times**; `AmmoMinCount` and `AmmoMaxCount` each **710 times**; `MinCount` **321 times**, `MaxCount` **265 times**. These counts exclude the nested malformed child. Missing maximum fields must not be silently fabricated. Durability on generated weapons is already handled by other tool controls and is not evidence of separate NPC combat health. Ammo fields are the generator's weapon-ammo payload, not a proof of NPC AI ammunition reserves.

**Category names are not reliable item descriptions.** The ordinary role `Artifact` slots contain grenade candidates. Classify the actual `ItemPrototypeSID` through the item data before showing a grenade or artifact label.

## Difficulty and rank masks

There are **164 difficulty-filtered slots**: 82 use `EGameDifficulty::Easy, EGameDifficulty::Medium, EGameDifficulty::Hard`, and 82 use `EGameDifficulty::Stalker`. Another 580 slots have no local difficulty filter. Preserve the two native branches and their distinct ammo ranges; do not flatten them into an assumed three-difficulty model.

Raw rank-mask counts, including the malformed value:

| Raw PlayerRank value | Slots |
|---|---:|
| `ERank::Newbie, ERank::Experienced` | 67 |
| `ERank::Veteran, ERank::Master` | 34 |
| `ERank::Newbie` | 53 |
| `ERank::Experienced` | 53 |
| `<absent>` | 300 |
| `ERank::Veteran` | 94 |
| `ERank::Master` | 107 |
| `ERank::Experienced, ERank::Veteran, ERank::Master` | 12 |
| `ERank::Newbie, ERank::Experienced, ERank::Veteran, ERank::Master` | 9 |
| `ERank::Experienced, ERank::Veteran` | 5 |
| `ERank::Newbie, ERank::Experienced, ERank::Veteran` | 5 |
| `ERank::Veteran, Master` | 1 |
| `ERank::Newbie, ERank::Experienced, ERank::Veteran,  ERank::Master` | 4 |

## Inheritance, schema fallback and exceptional shapes

Of the 114 roots, **103 reference `[0]`**, eight shared consumable roots have no `refkey`, and three No_Armor variants reference the corresponding ordinary Neutral role. There are **zero nested `refkey` / `refurl` attributes** anywhere inside this prefix scope. All 114 roots define their own `ItemGenerator`; no root has a `MoneyGenerator` or another child branch. Fifty-nine roots own `RefreshTime = 1d`; the other 55 lack this field. Do not turn that timer into a promise that existing NPCs will refresh their equipment every day.

`[0]` is the empty generator schema. Its first candidate contains both `Weight = 4.f` and `Chance = 0.f`, counts zero and item/sub-generator `empty`. **Do not discover a candidate's mode by calling `gd.resolve` for missing fields**: it will fall back by path to those schema fields. For example, resolving `GeneralNPC_Neutral_CloseCombat_ItemGenerator.ItemGenerator.[0].PossibleItems.[0].Chance` returns `0.f` despite the actual local candidate being a weight-only Obrez candidate. Determine existence and mode from audited local fields, then resolve the actual target leaves live. Never patch `[0]` to implement this editor.

The three No_Armor variants define local copies plus named `BodyArmor` and `Head` slots carrying `empty`, while referencing ordinary Neutral generators. Their inherited behavior cannot be isolated merely by ignoring their names in a patch loop; they need explicit consumer/inheritance analysis. The prefix inventory contains exactly six `empty` direct candidates, these two slots in each of the three variants. All other 1,263 direct item candidates resolve to item structs; none of the direct items are quest-flagged or match the existing unique-weapon convention. This does **not** prove their generator consumers are free of story involvement.

One root key differs from its SID:

- Struct key: `GeneralNPC_Consumables_Armored`
- SID: `GeneralNPC_Consumables_Recon_Armored`

Patch using the actual struct key. Preserve sub-generator links by SID when resolving consumers.

Two problematic data shapes require conservative exclusions:

1. `GeneralNPC_Mercenaries_Recon_ItemGenerator.ItemGenerator.[2]` (Master; Easy+Medium+Hard) has `GunIntegral_PP` at `PossibleItems.[1]` and an extra **nested** `[6]` child beneath it. That child contains `GunFora230_PP`, Weight 400, durability 0.25–0.5 and ammo 0–7. It is not a direct sibling candidate. Do not move it, treat it as a normal candidate, or normalize the containing pool while claiming validated probabilities. Exclude this pool until engine behavior is known.
2. `GeneralNPC_Bandit_WeaponPistol.ItemGenerator.[2].PlayerRank = ERank::Veteran, Master` contains one unqualified `Master` token. Do not silently convert it to a valid enum or promise that both ranks match. Exclude this slot from rank-specific controls until tested.

The custom sniper links out of this namespace to `GamePass_Stash_ItemGenerator_Rare` at `GeneralNPC_Neutral_Sniper_ItemGeneratorCustom.ItemGenerator.[4].PossibleItems.[0]`, Chance 1.0. A recursive blanket patch would unexpectedly reach world-stash logic.

## Complete root / slot inventory

All 114 roots are listed below. Each root name is its exact patch key except for the explicitly documented Armored SID mismatch. Abbreviations are **WP** primary weapon, **P** pistol, **B** body armor, **H** head, **G** sub-generator, **C** consumable, **D** detector, **A** native Artifact category, **N** night vision and **M** ammo. Numbers and named slots are copied from the parsed file; they are not calculated positions. The CSV supplies every corresponding candidate and filter.

| Struct key | Family | Slots | Candidates | Category: actual slots |
|---|---|---:|---:|---|
| `GeneralNPC_Consumables` | consumable | 4 | 22 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_Recon` | consumable | 4 | 18 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_Noon` | consumable | 4 | 20 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_CloseCombat` | consumable | 4 | 16 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_Sniper` | consumable | 4 | 16 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_Stormtrooper` | consumable | 4 | 18 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_Armored` | consumable | 4 | 16 | C: [0], [1], [2], [3] |
| `GeneralNPC_Consumables_Heavy` | consumable | 4 | 16 | C: [0], [1], [2], [3] |
| `GeneralNPC_Neutral_CloseCombat_ItemGenerator` | ordinary role | 19 | 31 | WP: [0], [1], [2], [3], [5], [6], [7], [8]; G: [4], [15], [18]; B: [9], [10], [11], [12]; H: [13], [14]; D: [16]; A: [17] |
| `GeneralNPC_Neutral_Recon_ItemGenerator` | ordinary role | 18 | 45 | WP: [0], [2], [3], [4], [5], [6], [7]; G: [1], [14], [17]; B: [8], [9], [10], [11]; H: [12], [13]; A: [15]; D: [16] |
| `GeneralNPC_Neutral_Sniper_ItemGenerator` | ordinary role | 19 | 42 | WP: [0], [1], [2], [3], [4], [5], [6], [7]; G: [8], [15], [18]; B: [9], [10], [11], [12]; H: [13], [14]; A: [16]; D: [17] |
| `GeneralNPC_Neutral_Stormtrooper_ItemGenerator` | ordinary role | 14 | 35 | G: [0], [13]; WP: [1], [2], [3], [4]; B: [5], [6], [7], [8]; H: [9], [10]; A: [11]; D: [12] |
| `GeneralNPC_Bandit_Armor` | shared helper | 3 | 5 | B: [0], [1]; H: [2] |
| `GeneralNPC_Bandit_CloseCombat_ItemGenerator` | ordinary role | 10 | 14 | G: [0], [5], [6], [9]; WP: [1], [2], [3], [4]; D: [7]; A: [8] |
| `GeneralNPC_Bandit_Recon_ItemGenerator` | ordinary role | 13 | 34 | G: [0], [8], [9], [12]; WP: [1], [2], [3], [4], [5], [6], [7]; A: [10]; D: [11] |
| `GeneralNPC_Bandit_Stormtrooper_ItemGenerator` | ordinary role | 11 | 14 | G: [0], [6], [7], [10]; WP: [1], [2], [3], [4], [5]; A: [8]; D: [9] |
| `GeneralNPC_Bandit_Heavy_ItemGenerator` | ordinary role | 11 | 16 | G: [0], [6], [8], [10]; WP: [1], [2], [3], [4], [5]; A: [7]; D: [9] |
| `GeneralNPC_Mercenaries_Armor` | shared helper | 5 | 7 | B: [0], [1], [2], [3]; H: [4] |
| `GeneralNPC_Mercenaries_CloseCombat_ItemGenerator` | ordinary role | 11 | 15 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [7], [10]; D: [8]; A: [9] |
| `GeneralNPC_Mercenaries_Recon_ItemGenerator` | ordinary role | 11 | 19 | WP: [0], [1], [2], [3], [4], [5]; G: [6], [7], [10]; A: [8]; D: [9] |
| `GeneralNPC_Mercenaries_Stormtrooper_ItemGenerator` | ordinary role | 8 | 17 | WP: [0], [1], [2]; G: [3], [4], [7]; A: [5]; D: [6] |
| `GeneralNPC_Mercenaries_Sniper_ItemGenerator` | ordinary role | 10 | 16 | WP: [0], [1], [2], [3], [4]; G: [5], [7], [9]; A: [6]; D: [8] |
| `GeneralNPC_Scientists_Armor` | shared helper | 2 | 3 | B: [0], [1] |
| `GeneralNPC_Scientists_Recon_ItemGenerator` | ordinary role | 4 | 5 | WP: [0]; G: [1], [2]; D: [3] |
| `GeneralNPC_Scientists_Stormtrooper_ItemGenerator` | ordinary role | 5 | 7 | WP: [0]; G: [1], [2]; A: [3]; D: [4] |
| `GeneralNPC_Militaries_Armor` | shared helper | 5 | 6 | B: [0], [2]; G: [1]; H: [3], [4] |
| `GeneralNPC_Militaries_CloseCombat_ItemGenerator` | ordinary role | 8 | 10 | WP: [0], [1], [2]; G: [3], [4], [7]; A: [5]; D: [6] |
| `GeneralNPC_Militaries_Recon_ItemGenerator` | ordinary role | 10 | 20 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; A: [7]; D: [8] |
| `GeneralNPC_Militaries_Stormtrooper_ItemGenerator` | ordinary role | 11 | 23 | WP: [0], [1], [2], [3], [4], [5]; G: [6], [7], [10]; A: [8]; D: [9] |
| `GeneralNPC_Militaries_Sniper_ItemGenerator` | ordinary role | 9 | 13 | WP: [0], [1], [2], [3]; G: [4], [5], [8]; A: [6]; D: [7] |
| `GeneralNPC_Militaries_Heavy_ItemGenerator` | ordinary role | 12 | 22 | WP: [0], [1], [2], [3], [4], [5], [6]; G: [7], [8], [11]; D: [9]; A: [10] |
| `GeneralNPC_Monolith_Armor` | shared helper | 4 | 7 | B: [0], [1], [2]; H: [3] |
| `GeneralNPC_Monolith_CloseCombat_ItemGenerator` | ordinary role | 10 | 19 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Monolith_Recon_ItemGenerator` | ordinary role | 8 | 19 | WP: [0], [1], [2]; G: [3], [4], [7]; A: [5]; D: [6] |
| `GeneralNPC_Monolith_Stormtrooper_ItemGenerator` | ordinary role | 8 | 19 | WP: [0], [1], [2]; G: [3], [4], [7]; A: [5]; D: [6] |
| `GeneralNPC_Monolith_Sniper_ItemGenerator` | ordinary role | 10 | 26 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Duty_Armor_Experienced_var1` | shared helper | 2 | 2 | B: [0]; H: [1] |
| `GeneralNPC_Duty_Armor_Experienced_var2` | shared helper | 1 | 1 | B: [0] |
| `GeneralNPC_Duty_Armor` | shared helper | 5 | 8 | B: [0], [2], [3]; G: [1]; H: [4] |
| `GeneralNPC_Duty_CloseCombat_ItemGenerator` | ordinary role | 10 | 14 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; A: [7]; D: [8] |
| `GeneralNPC_Duty_Recon_ItemGenerator` | ordinary role | 8 | 12 | WP: [0], [1], [2]; G: [3], [4], [7]; A: [5]; D: [6] |
| `GeneralNPC_Duty_Stormtrooper_ItemGenerator` | ordinary role | 10 | 22 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; A: [7]; D: [8] |
| `GeneralNPC_Duty_Sniper_ItemGenerator` | ordinary role | 10 | 19 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; A: [7]; D: [8] |
| `GeneralNPC_Duty_Heavy_ItemGenerator` | ordinary role | 10 | 18 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Freedom_Armor` | shared helper | 5 | 9 | B: [0], [1], [2], [3]; H: [4] |
| `GeneralNPC_Freedom_CloseCombat_ItemGenerator` | ordinary role | 10 | 17 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Freedom_Recon_ItemGenerator` | ordinary role | 11 | 18 | WP: [0], [1], [2], [3], [4], [5]; G: [6], [7], [10]; A: [8]; D: [9] |
| `GeneralNPC_Freedom_Stormtrooper_ItemGenerator` | ordinary role | 10 | 20 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; A: [7]; D: [8] |
| `GeneralNPC_Freedom_Sniper_ItemGenerator` | ordinary role | 10 | 17 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Varta_Armor` | shared helper | 4 | 6 | B: [0], [1], [2]; H: [3] |
| `GeneralNPC_Varta_CloseCombat_ItemGenerator` | ordinary role | 10 | 18 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Varta_Recon_ItemGenerator` | ordinary role | 10 | 24 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; A: [7]; D: [8] |
| `GeneralNPC_Varta_Stormtrooper_ItemGenerator` | ordinary role | 11 | 28 | WP: [0], [1], [2], [3], [4], [5]; G: [6], [7], [10]; A: [8]; D: [9] |
| `GeneralNPC_Varta_Sniper_ItemGenerator` | ordinary role | 9 | 15 | WP: [0], [1], [2], [3]; G: [4], [5], [8]; D: [6]; A: [7] |
| `GeneralNPC_Varta_Heavy_ItemGenerator` | ordinary role | 9 | 15 | WP: [0], [1], [2], [3]; G: [4], [5], [8]; D: [6]; A: [7] |
| `GeneralNPC_Noon_Armor` | shared helper | 5 | 7 | B: [0], [1], [2]; H: [3], [4] |
| `GeneralNPC_Noon_CloseCombat_ItemGenerator` | ordinary role | 6 | 9 | WP: [0], [1]; G: [2], [3]; D: [4]; A: [5] |
| `GeneralNPC_Noon_Recon_ItemGenerator` | ordinary role | 6 | 11 | WP: [0], [1]; G: [2], [3]; D: [4]; A: [5] |
| `GeneralNPC_Noon_Stormtrooper_ItemGenerator` | ordinary role | 6 | 8 | WP: [0], [1]; G: [2], [3]; D: [4]; A: [5] |
| `GeneralNPC_Noon_Sniper_ItemGenerator` | ordinary role | 6 | 13 | WP: [0], [1]; G: [2], [4]; A: [3]; D: [5] |
| `GeneralNPC_Spark_Armor` | shared helper | 4 | 9 | B: [0], [1], [2]; H: [3] |
| `GeneralNPC_Spark_CloseCombat_ItemGenerator` | ordinary role | 8 | 12 | WP: [0], [1], [2]; G: [3], [4], [7]; D: [5]; A: [6] |
| `GeneralNPC_Spark_Recon_ItemGenerator` | ordinary role | 7 | 12 | WP: [0], [1]; G: [2], [3], [6]; A: [4]; D: [5] |
| `GeneralNPC_Spark_Stormtrooper_ItemGenerator` | ordinary role | 8 | 19 | WP: [0], [1], [2]; G: [3], [4], [7]; A: [5]; D: [6] |
| `GeneralNPC_Spark_Sniper_ItemGenerator` | ordinary role | 10 | 22 | WP: [0], [1], [2], [3], [4]; G: [5], [6], [9]; D: [7]; A: [8] |
| `GeneralNPC_Corpus_Armor` | shared helper | 5 | 11 | B: [0], [1], [2]; H: [3], [4] |
| `GeneralNPC_Corpus_CloseCombat_ItemGenerator` | ordinary role | 7 | 11 | WP: [0], [1]; G: [2], [3], [6]; D: [4]; A: [5] |
| `GeneralNPC_Corpus_Recon_ItemGenerator` | ordinary role | 7 | 12 | WP: [0], [1]; G: [2], [3], [6]; A: [4]; D: [5] |
| `GeneralNPC_Corpus_Stormtrooper_ItemGenerator` | ordinary role | 7 | 11 | WP: [0], [1]; G: [2], [3], [6]; A: [4]; D: [5] |
| `GeneralNPC_Corpus_Sniper_ItemGenerator` | ordinary role | 7 | 9 | WP: [0], [1]; G: [2], [3], [6]; D: [4]; A: [5] |
| `GeneralNPC_Corpus_Heavy_ItemGenerator` | ordinary role | 7 | 9 | WP: [0], [1]; G: [2], [3], [6]; D: [4]; A: [5] |
| `GeneralNPC_Neutral_WeaponPistol` | shared helper | 4 | 14 | P: [0], [1], [2], [3] |
| `GeneralNPC_Bandit_WeaponPistol` | shared helper | 3 | 3 | P: [0], [1], [2] |
| `GeneralNPC_Mercenaries_WeaponPistol` | shared helper | 3 | 6 | P: [0], [1], [2] |
| `GeneralNPC_Scientists_WeaponPistol` | shared helper | 2 | 3 | P: [0], [1] |
| `GeneralNPC_Militaries_WeaponPistol` | shared helper | 3 | 5 | P: [0], [1], [2] |
| `GeneralNPC_Monolith_WeaponPistol` | shared helper | 3 | 5 | P: [0], [1], [2] |
| `GeneralNPC_Duty_WeaponPistol` | shared helper | 3 | 5 | P: [0], [1], [2] |
| `GeneralNPC_Freedom_WeaponPistol` | shared helper | 3 | 7 | P: [0], [1], [2] |
| `GeneralNPC_Varta_WeaponPistol` | shared helper | 4 | 8 | P: [0], [1], [2], [3] |
| `GeneralNPC_Noon_WeaponPistol` | shared helper | 2 | 4 | P: [0], [1] |
| `GeneralNPC_Spark_WeaponPistol` | shared helper | 2 | 7 | P: [0], [1] |
| `GeneralNPC_Corpus_WeaponPistol` | shared helper | 2 | 4 | P: [0], [1] |
| `GeneralNPC_Neutral_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Bandit_NVG` | shared helper | 1 | 2 | N: [0] |
| `GeneralNPC_Mercenaries_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Militaries_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Monolith_NVG` | shared helper | 2 | 4 | N: [0], [1] |
| `GeneralNPC_Duty_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Freedom_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Varta_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Spark_NVG` | shared helper | 3 | 6 | N: [0], [1], [2] |
| `GeneralNPC_Corpus_NVG` | shared helper | 3 | 5 | N: [0], [1], [2] |
| `GeneralNPC_Bandit_Recon_ItemGenerator_Prolog_Obrez` | prologue | 7 | 8 | G: [0], [3], [4]; WP: [1], [2]; A: [5], [6] |
| `GeneralNPC_Bandit_Recon_ItemGenerator_Prolog_AKU` | prologue | 7 | 8 | G: [0], [3], [4]; WP: [1], [2]; A: [5], [6] |
| `GeneralNPC_TradeItemGenerator` | trade | 2 | 7 | C: [0]; M: [1] |
| `GeneralNPC_TradeItemGenerator_Duty` | trade | 2 | 6 | C: [0]; M: [1] |
| `GeneralNPC_TradeItemGenerator_Freedom` | trade | 2 | 9 | C: [0]; M: [1] |
| `GeneralNPC_TradeItemGenerator_Mercenary` | trade | 2 | 7 | C: [0]; A: [1] |
| `GeneralNPC_TradeItemGenerator_Militaries` | trade | 2 | 8 | C: [0]; A: [1] |
| `GeneralNPC_TradeItemGenerator_Bandit` | trade | 2 | 9 | C: [0]; M: [1] |
| `GeneralNPC_TradeItemGenerator_Scientists` | trade | 1 | 8 | C: [0] |
| `GeneralNPC_TradeItemGenerator_Spark` | trade | 1 | 7 | C: [0] |
| `GeneralNPC_TradeItemGenerator_Corpus` | trade | 2 | 7 | C: [0]; M: [1] |
| `GeneralNPC_SIRCAA_Scientist_Recon_ItemGenerator` | site-specific | 4 | 4 | P: [0]; B: [1]; G: [2]; D: [3] |
| `GeneralNPC_MALACHITE_Scientist_Recon_ItemGenerator` | site-specific | 4 | 4 | P: [0]; B: [1]; G: [2]; D: [3] |
| `GeneralNPC_Militaries_Armor_var2` | shared helper | 2 | 3 | B: [0]; H: [1] |
| `GeneralNPC_Militaries_Armor_var1` | shared helper | 1 | 1 | B: [0] |
| `GeneralNPC_Neutral_Recon_No_Armor_ItemGenerator` | special variant | 20 | 47 | B: BodyArmor, [8], [9], [10], [11]; H: Head, [12], [13]; WP: [0], [2], [3], [4], [5], [6], [7]; G: [1], [14], [17]; A: [15]; D: [16] |
| `GeneralNPC_Neutral_Stormtrooper_No_Armor_ItemGenerator` | special variant | 16 | 37 | B: BodyArmor, [5], [6], [7], [8]; H: Head, [9], [10]; G: [0], [13]; WP: [1], [2], [3], [4]; A: [11]; D: [12] |
| `GeneralNPC_Neutral_CloseCombat_No_Armor_ItemGenerator` | special variant | 21 | 33 | B: BodyArmor, [9], [10], [11], [12]; H: Head, [13], [14]; WP: [0], [1], [2], [3], [5], [6], [7], [8]; G: [4], [15], [18]; D: [16]; A: [17] |
| `GeneralNPC_Neutral_Sniper_ItemGeneratorCustom` | special variant | 15 | 21 | WP: [0], [1], [2], [3]; G: [4], [11], [14]; B: [5], [6], [7], [8]; H: [9], [10]; A: [12]; D: [13] |
| `GeneralNPC_Neutral_CloseCombat_ItemGenerator_Prolog` | prologue | 4 | 6 | M: [0]; B: [1]; H: [2]; C: [3] |
| `GeneralNPC_Neutral_CloseCombat_ItemGenerator_Prolog_Medkit` | prologue | 4 | 6 | B: [0]; H: [1]; C: [2]; WP: [3] |

## Ordinary faction-role helper mappings

Every direct sub-generator reference from the 50 ordinary role roots is listed below. `slot/candidate → SID (W=value or C=value)` preserves the exact branch and selection mechanism. Shared helper modification changes every consumer unless the implementation clones and rewires a specific branch.

| Ordinary role root | Direct helper links |
|---|---|
| `GeneralNPC_Neutral_CloseCombat_ItemGenerator` | `[4]/[0]` → `GeneralNPC_Neutral_WeaponPistol` (C=0.3); `[15]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[18]/[0]` → `GeneralNPC_Neutral_NVG` (C=1) |
| `GeneralNPC_Neutral_Recon_ItemGenerator` | `[1]/[0]` → `GeneralNPC_Neutral_WeaponPistol` (C=0.25); `[14]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[17]/[0]` → `GeneralNPC_Neutral_NVG` (C=1) |
| `GeneralNPC_Neutral_Sniper_ItemGenerator` | `[8]/[0]` → `GeneralNPC_Neutral_WeaponPistol` (C=1.0); `[15]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[18]/[0]` → `GeneralNPC_Neutral_NVG` (C=1) |
| `GeneralNPC_Neutral_Stormtrooper_ItemGenerator` | `[0]/[0]` → `GeneralNPC_Neutral_WeaponPistol` (C=0.4); `[0]/[1]` → `GeneralNPC_Consumables_Stormtrooper` (C=1); `[13]/[0]` → `GeneralNPC_Neutral_NVG` (C=1) |
| `GeneralNPC_Bandit_CloseCombat_ItemGenerator` | `[0]/[0]` → `GeneralNPC_Bandit_WeaponPistol` (C=0.3); `[5]/[0]` → `GeneralNPC_Bandit_Armor` (W=1); `[6]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[9]/[0]` → `GeneralNPC_Bandit_NVG` (C=1) |
| `GeneralNPC_Bandit_Recon_ItemGenerator` | `[0]/[0]` → `GeneralNPC_Bandit_WeaponPistol` (C=0.25); `[8]/[0]` → `GeneralNPC_Bandit_Armor` (W=1); `[9]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[12]/[0]` → `GeneralNPC_Bandit_NVG` (C=1) |
| `GeneralNPC_Bandit_Stormtrooper_ItemGenerator` | `[0]/[0]` → `GeneralNPC_Bandit_WeaponPistol` (C=1.0); `[6]/[0]` → `GeneralNPC_Bandit_Armor` (W=1); `[7]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[10]/[0]` → `GeneralNPC_Bandit_NVG` (C=1) |
| `GeneralNPC_Bandit_Heavy_ItemGenerator` | `[0]/[0]` → `GeneralNPC_Bandit_WeaponPistol` (C=1.0); `[6]/[0]` → `GeneralNPC_Bandit_Armor` (W=1); `[8]/[0]` → `GeneralNPC_Consumables_Heavy` (W=1); `[10]/[0]` → `GeneralNPC_Bandit_NVG` (C=1) |
| `GeneralNPC_Mercenaries_CloseCombat_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Mercenaries_Armor` (W=1); `[6]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[7]/[0]` → `GeneralNPC_Mercenaries_WeaponPistol` (C=0.35); `[10]/[0]` → `GeneralNPC_Mercenaries_NVG` (C=1) |
| `GeneralNPC_Mercenaries_Recon_ItemGenerator` | `[6]/[0]` → `GeneralNPC_Mercenaries_Armor` (C=1); `[6]/[1]` → `GeneralNPC_Mercenaries_WeaponPistol` (C=0.25); `[7]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[10]/[0]` → `GeneralNPC_Mercenaries_NVG` (C=1) |
| `GeneralNPC_Mercenaries_Stormtrooper_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Mercenaries_Armor` (C=1); `[3]/[1]` → `GeneralNPC_Mercenaries_WeaponPistol` (C=0.4); `[4]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[7]/[0]` → `GeneralNPC_Mercenaries_NVG` (C=1) |
| `GeneralNPC_Mercenaries_Sniper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Mercenaries_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Mercenaries_WeaponPistol` (C=0.5); `[7]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[9]/[0]` → `GeneralNPC_Mercenaries_NVG` (C=1) |
| `GeneralNPC_Scientists_Recon_ItemGenerator` | `[1]/[0]` → `GeneralNPC_Scientists_Armor` (C=1); `[1]/[1]` → `GeneralNPC_Scientists_WeaponPistol` (C=0.25); `[2]/[0]` → `GeneralNPC_Consumables_Recon` (W=1) |
| `GeneralNPC_Scientists_Stormtrooper_ItemGenerator` | `[1]/[0]` → `GeneralNPC_Scientists_Armor` (C=1); `[1]/[1]` → `GeneralNPC_Scientists_WeaponPistol` (C=0.45); `[2]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1) |
| `GeneralNPC_Militaries_CloseCombat_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Consumables_CloseCombat` (C=1); `[3]/[1]` → `GeneralNPC_Militaries_WeaponPistol` (C=0.35); `[4]/[0]` → `GeneralNPC_Militaries_Armor` (W=1); `[7]/[0]` → `GeneralNPC_Militaries_NVG` (C=1) |
| `GeneralNPC_Militaries_Recon_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Militaries_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Militaries_WeaponPistol` (C=0.25); `[6]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[9]/[0]` → `GeneralNPC_Militaries_NVG` (C=1) |
| `GeneralNPC_Militaries_Stormtrooper_ItemGenerator` | `[6]/[0]` → `GeneralNPC_Militaries_Armor` (C=1); `[6]/[1]` → `GeneralNPC_Militaries_WeaponPistol` (C=0.4); `[7]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[10]/[0]` → `GeneralNPC_Militaries_NVG` (C=1) |
| `GeneralNPC_Militaries_Sniper_ItemGenerator` | `[4]/[0]` → `GeneralNPC_Militaries_Armor` (C=1); `[4]/[1]` → `GeneralNPC_Militaries_WeaponPistol` (C=0.5); `[5]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[8]/[0]` → `GeneralNPC_Militaries_NVG` (C=1) |
| `GeneralNPC_Militaries_Heavy_ItemGenerator` | `[7]/[0]` → `GeneralNPC_Militaries_Armor` (C=1); `[7]/[1]` → `GeneralNPC_Militaries_WeaponPistol` (C=0.1); `[8]/[0]` → `GeneralNPC_Consumables_Heavy` (W=1); `[11]/[0]` → `GeneralNPC_Militaries_NVG` (C=1) |
| `GeneralNPC_Monolith_CloseCombat_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Monolith_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Monolith_WeaponPistol` (C=0.3); `[6]/[0]` → `GeneralNPC_Consumables_Noon` (W=1); `[9]/[0]` → `GeneralNPC_Monolith_NVG` (C=1) |
| `GeneralNPC_Monolith_Recon_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Monolith_Armor` (C=1); `[3]/[1]` → `GeneralNPC_Monolith_WeaponPistol` (C=0.25); `[4]/[0]` → `GeneralNPC_Consumables_Noon` (W=1); `[7]/[0]` → `GeneralNPC_Monolith_NVG` (C=1) |
| `GeneralNPC_Monolith_Stormtrooper_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Monolith_Armor` (C=1); `[3]/[1]` → `GeneralNPC_Monolith_WeaponPistol` (C=0.4); `[4]/[0]` → `GeneralNPC_Consumables_Noon` (W=1); `[7]/[0]` → `GeneralNPC_Monolith_NVG` (C=1) |
| `GeneralNPC_Monolith_Sniper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Monolith_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Monolith_WeaponPistol` (C=0.5); `[6]/[0]` → `GeneralNPC_Consumables_Noon` (W=1); `[9]/[0]` → `GeneralNPC_Monolith_NVG` (C=1) |
| `GeneralNPC_Duty_CloseCombat_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Duty_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Duty_WeaponPistol` (C=0.4); `[6]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[9]/[0]` → `GeneralNPC_Duty_NVG` (C=1) |
| `GeneralNPC_Duty_Recon_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Duty_Armor` (C=1); `[3]/[1]` → `GeneralNPC_Duty_WeaponPistol` (C=0.25); `[4]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[7]/[0]` → `GeneralNPC_Duty_NVG` (C=1) |
| `GeneralNPC_Duty_Stormtrooper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Duty_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Duty_WeaponPistol` (C=0.45); `[6]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[9]/[0]` → `GeneralNPC_Duty_NVG` (C=1) |
| `GeneralNPC_Duty_Sniper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Duty_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Duty_WeaponPistol` (C=0.5); `[6]/[0]` → `GeneralNPC_Consumables_Sniper` (W=0.5); `[9]/[0]` → `GeneralNPC_Duty_NVG` (C=1) |
| `GeneralNPC_Duty_Heavy_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Duty_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Duty_WeaponPistol` (C=0.1); `[6]/[0]` → `GeneralNPC_Consumables_Heavy` (W=1); `[9]/[0]` → `GeneralNPC_Duty_NVG` (C=1) |
| `GeneralNPC_Freedom_CloseCombat_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Freedom_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Freedom_WeaponPistol` (C=0.3); `[6]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[9]/[0]` → `GeneralNPC_Freedom_NVG` (C=1) |
| `GeneralNPC_Freedom_Recon_ItemGenerator` | `[6]/[0]` → `GeneralNPC_Freedom_Armor` (C=1); `[6]/[1]` → `GeneralNPC_Freedom_WeaponPistol` (C=0.25); `[7]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[10]/[0]` → `GeneralNPC_Freedom_NVG` (C=1) |
| `GeneralNPC_Freedom_Stormtrooper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Freedom_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Freedom_WeaponPistol` (C=0.4); `[6]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[9]/[0]` → `GeneralNPC_Freedom_NVG` (C=1) |
| `GeneralNPC_Freedom_Sniper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Freedom_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Freedom_WeaponPistol` (C=0.5); `[6]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[9]/[0]` → `GeneralNPC_Freedom_NVG` (C=1) |
| `GeneralNPC_Varta_CloseCombat_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Varta_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Varta_WeaponPistol` (C=0.35); `[6]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[9]/[0]` → `GeneralNPC_Varta_NVG` (C=1) |
| `GeneralNPC_Varta_Recon_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Varta_Armor` (C=1); `[5]/[1]` → `GeneralNPC_Varta_WeaponPistol` (C=0.25); `[6]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[9]/[0]` → `GeneralNPC_Varta_NVG` (C=1) |
| `GeneralNPC_Varta_Stormtrooper_ItemGenerator` | `[6]/[0]` → `GeneralNPC_Varta_Armor` (C=1); `[6]/[1]` → `GeneralNPC_Varta_WeaponPistol` (C=0.4); `[7]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[10]/[0]` → `GeneralNPC_Varta_NVG` (C=1) |
| `GeneralNPC_Varta_Sniper_ItemGenerator` | `[4]/[0]` → `GeneralNPC_Varta_Armor` (C=1); `[4]/[1]` → `GeneralNPC_Varta_WeaponPistol` (C=0.5); `[5]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[8]/[0]` → `GeneralNPC_Varta_NVG` (C=1) |
| `GeneralNPC_Varta_Heavy_ItemGenerator` | `[4]/[0]` → `GeneralNPC_Varta_Armor` (C=1); `[4]/[1]` → `GeneralNPC_Varta_WeaponPistol` (C=0.1); `[5]/[0]` → `GeneralNPC_Consumables_Heavy` (W=1); `[8]/[0]` → `GeneralNPC_Varta_NVG` (C=1) |
| `GeneralNPC_Noon_CloseCombat_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Noon_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Noon_WeaponPistol` (C=0.3); `[3]/[0]` → `GeneralNPC_Consumables_Noon` (W=1) |
| `GeneralNPC_Noon_Recon_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Noon_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Noon_WeaponPistol` (C=0.25); `[3]/[0]` → `GeneralNPC_Consumables_Noon` (W=1) |
| `GeneralNPC_Noon_Stormtrooper_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Noon_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Noon_WeaponPistol` (C=0.45); `[3]/[0]` → `GeneralNPC_Consumables_Noon` (W=1) |
| `GeneralNPC_Noon_Sniper_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Noon_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Noon_WeaponPistol` (C=0.5); `[4]/[0]` → `GeneralNPC_Consumables_Noon` (W=1) |
| `GeneralNPC_Spark_CloseCombat_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Spark_WeaponPistol` (C=0.3); `[3]/[1]` → `GeneralNPC_Spark_Armor` (C=1); `[4]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[7]/[0]` → `GeneralNPC_Spark_NVG` (C=1) |
| `GeneralNPC_Spark_Recon_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Spark_WeaponPistol` (C=0.25); `[2]/[1]` → `GeneralNPC_Spark_Armor` (C=1); `[3]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[6]/[0]` → `GeneralNPC_Spark_NVG` (C=1) |
| `GeneralNPC_Spark_Stormtrooper_ItemGenerator` | `[3]/[0]` → `GeneralNPC_Spark_WeaponPistol` (C=0.4); `[3]/[1]` → `GeneralNPC_Spark_Armor` (C=1); `[4]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[7]/[0]` → `GeneralNPC_Spark_NVG` (C=1) |
| `GeneralNPC_Spark_Sniper_ItemGenerator` | `[5]/[0]` → `GeneralNPC_Spark_WeaponPistol` (C=0.5); `[5]/[1]` → `GeneralNPC_Spark_Armor` (C=1); `[6]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[9]/[0]` → `GeneralNPC_Spark_NVG` (C=1) |
| `GeneralNPC_Corpus_CloseCombat_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Corpus_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Corpus_WeaponPistol` (C=0.3); `[3]/[0]` → `GeneralNPC_Consumables_CloseCombat` (W=1); `[6]/[0]` → `GeneralNPC_Corpus_NVG` (C=1) |
| `GeneralNPC_Corpus_Recon_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Corpus_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Corpus_WeaponPistol` (C=0.25); `[3]/[0]` → `GeneralNPC_Consumables_Recon` (W=1); `[6]/[0]` → `GeneralNPC_Corpus_NVG` (C=1) |
| `GeneralNPC_Corpus_Stormtrooper_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Corpus_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Corpus_WeaponPistol` (C=0.4); `[3]/[0]` → `GeneralNPC_Consumables_Stormtrooper` (W=1); `[6]/[0]` → `GeneralNPC_Corpus_NVG` (C=1) |
| `GeneralNPC_Corpus_Sniper_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Corpus_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Corpus_WeaponPistol` (C=0.5); `[3]/[0]` → `GeneralNPC_Consumables_Sniper` (W=1); `[6]/[0]` → `GeneralNPC_Corpus_NVG` (C=1) |
| `GeneralNPC_Corpus_Heavy_ItemGenerator` | `[2]/[0]` → `GeneralNPC_Corpus_Armor` (C=1); `[2]/[1]` → `GeneralNPC_Corpus_WeaponPistol` (C=0.15); `[3]/[0]` → `GeneralNPC_Consumables_Heavy` (W=1); `[6]/[0]` → `GeneralNPC_Corpus_NVG` (C=1) |

## Shape-validated weighted subset for implementation

The private identity inventory `out/npc_equipment_research/inventory/weighted_pool_identities.json` contains no numeric game baselines. It records exact struct/SID/refkey identities, native rank and difficulty token strings, slot/category identities, and direct candidate key/item pairs. Its generator `identity.py` excludes entire malformed pools, unknown rank/difficulty tokens, attributed or nested candidate shapes, missing/empty/quest/unique items, sub-generator candidates, chance candidates and non-positive weights. This is a structural filter, not a claim that all consumers are free of quests or inheritance effects.

| Scope | Structurally valid pools | Candidate rows | Pools with at least 2 candidates | Rows in those pools |
|---|---:|---:|---:|---:|
| 50 ordinary role roots | 224 | 597 | 190 | 563 |
| 24 shared helper roots | 66 | 133 | 42 | 109 |

The direct role pools comprise **208 WeaponPrimary and 16 BodyArmor**. The shared helper pools comprise **33 BodyArmor and 33 WeaponPistol**. The complete helper family has 37 roots: **15 armor roots (11 bases and 4 variants), 12 pistol roots, 10 night-vision roots**. Three of the armor roots have no direct weighted body-armor pool; night vision uses chance lists and is not included in the weighted subset. A single-candidate pool cannot change relative frequency and should not show a misleading selection-bias control.

Mask strings are preserved exactly, including native spaces. Updating any live identity, slot structure or selector should fail closed for that target until it is re-audited. Selection weights must be read live after that check, rather than copied from this research.

## Implementation boundary

An initial editor can safely *represent* the audited native faction-role / player-rank-mask / difficulty / slot hierarchy and adjust existing local weapon selection weights, chance-based accessory entries, and known helper pools. Every selected target still needs a full consumer audit because “GeneralNPC” is not a quest-safety marker. Broadly changing faction armor helpers is broader than changing one role; show that scope honestly. Exclude traders, prologue roots, special variants, site-specific scientist roots, empty/template candidates, malformed masks and malformed pools unless a later focused investigation justifies them.

Do not promise arbitrary NPC rank loadouts, replacement of the equipment already stored on spawned NPCs, harmless quest coverage, or armor being recoverable as corpse loot. Those behaviors require object/spawn linkage research and an actual game test. Do not add arbitrary item SIDs, edit `MoneyGenerator`, rewrite enum masks, repair unrelated vanilla typos, or modify global item definitions to implement a local equipment preference.

`ItemGeneratorPrototypes.cfg` and `ItemPrototypes.cfg` are already extracted by `GameData.NEEDED_FILES`; this inventory itself requires no new extraction input or cache-schema change. Production values must remain live and default settings must emit no patch.

## Reproduction and validation

The read-only private scripts are `out/npc_equipment_research/inventory/analyze.py` and `out/npc_equipment_research/inventory/document.py`. The first rebuilds the CSV and inventory from the current local CFG through `cfgparse` / `GameData`; the second verifies each recorded candidate leaf against both its own parsed node and `gd.resolve`, verifies filter and root values, and rebuilds this document. The scripts and extracted data remain private and must not enter the release source ZIP.


Validation completed: **19,643 exact value comparisons passed across all 1,483 CSV rows**. This verifies data transcription and target paths, not engine behavior. No production code, installed game files, saves, or published assets were changed by this research.
