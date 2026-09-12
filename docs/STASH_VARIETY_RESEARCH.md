# Extra stash finds — research and requested feature

Research snapshot: 2026-09-09; not verified in the running game. For the subsequent implementation, see [OPTIONAL_EXTENSIONS.md](OPTIONAL_EXTENSIONS.md).

## Result and reference

Additional artifacts, ordinary weapons, armor/helmets and attachments in world stashes would add a capability that S2Tweaker's current loot sliders do not provide. Keep these four categories independently optional, off by default. Use the installed game's current items and generator structure for an original implementation.

Inspiration: [Ultimate Stashes Upgrade by Stalker_Boss / StalkerBoss](https://www.nexusmods.com/stalker2heartofchornobyl/mods/832?tab=description). The [four downloaded v1.3 files](https://www.nexusmods.com/stalker2heartofchornobyl/mods/832?tab=files) were uploaded on 2025-06-27; the file changelog targets patch 1.5 although the page title says updated for 1.8. Treat the archives as historical references. The description's claim about leaving scripted stashes unchanged is not a verified guarantee for today's game.

All four archives contain one Pak with the complete `Stalker2/Content/GameLite/GameData/ItemGeneratorPrototypes/Gamepass_ItemGenerators.cfg`: 856 top-level generators, no selective bpatch headers. All 856 names still exist in the installed merged original. Differences between the four variants concern exactly four generators. Their other 852 generators are identical **between variants**, which does not mean they match current vanilla.

## Sources read from the installed game

The following binary originals were read from the installed `pakchunk0-Windows.pak` and decoded for analysis. Paths below are relative to `Stalker2/Content/GameLite/GameData/`. Counts describe this snapshot, not every game version.

| File (decoded `.cfg`) | Lines | Top-level structs |
| --- | ---: | ---: |
| `ItemGeneratorPrototypes.cfg` | 277,318 | 3,085 |
| `ItemPrototypes.cfg` | 92,224 | 1,375 |
| `EffectPrototypes.cfg` | 85,869 | 2,426 |
| `TradePrototypes.cfg` | 3,267 | 74 |
| `StashPrototypes.cfg` | 10,681 | 19 |
| `SpawnActorPrototypes.cfg` | 5,068,168 | 130,055 |
| `ArtifactSpawnerPrototypes.cfg` | 6,848 | 98 |

## Historical variants, checked against current item definitions

| Variant | Extra unique items in EACH of the four pools | Composition |
| --- | ---: | --- |
| Full | 163 | 65 artifacts, 18 outfits, 10 helmets, 45 attachments/magazines, 25 weapons |
| No Artefacts | 98 | 28 armor/helmets, 45 attachments/magazines, 25 weapons |
| No Weapons | 138 | 65 artifacts, 28 armor/helmets, 45 attachments/magazines |
| No Artefacts And Weapons | 73 | 28 armor/helmets, 45 attachments/magazines |

These are unique item counts per pool, not expected items per stash. All 163 added item SIDs exist in current `ItemPrototypes`; resolved categories confirm 65 artifact, 28 armor, 45 attach and 25 weapon items. None match the existing quest flags, money-effect filter or named-unique weapon filter. All 65 artifacts also occur as item references in the current `ArtifactSpawnerPrototypes`. Existence and references do not prove every item is appropriate at every rank or actively available from every spawner.

For all additions, the historical mod sets `MinCount = MaxCount = 1`. Added weapons and armor/helmets have `MinDurability = 0.7`, `MaxDurability = 1.0`. The four expanded groups and their new items have no explicit rank/difficulty restriction in the historical files.

Full-version raw Chance fields:

| Added category | Cheap / Common_Var2 / Rare | Common_Var1 |
| --- | --- | --- |
| Attachments: 45; weapons: 25 | 0.0035 each | 0.0035 each |
| Armor/helmets: 28 | 0.002 each | 0.002 each |
| Artifacts: 37 | 0.004 each | 0.002 each |
| Artifacts: 17 | 0.0035 each | 0.0035 each |
| Artifacts: 11 | 0.003 each | 0.003 each |

No Artefacts and No Both additionally double all 28 armor/helmet Chance values to 0.004. No Weapons only removes the 25 added weapon entries. It does not remove existing weapons in other stashes. These raw fields are **not** established overall percentages per stash or category; do not sum them into a UI promise.

## Exact current target structures and values

The four historical targets share prefix `GamePass_Stash_ItemGenerator_`. They inherit `{refurl=../ItemGeneratorPrototypes.cfg;refkey=[0]}` but each defines its own `ItemGenerator` block in the decoded original. In the table below, the suffix expands to that complete generator name.

| Suffix | Current ItemGenerator groups | Current direct item entries across all groups | Historical expanded group | Current explicit group difficulty | Current bAllowSameCategoryGeneration |
| --- | ---: | ---: | --- | --- | --- |
| `Cheap` | 12 | 52 | `ItemGenerator.[1]` | `EGameDifficulty::Hard` | `true` |
| `Common_Var1` | 10 | 39 | `ItemGenerator.[0]` | `EGameDifficulty::Easy, EGameDifficulty::Medium, EGameDifficulty::Hard` | `true` |
| `Common_Var2` | 2 | 9 | `ItemGenerator.[0]` | `absent` | `absent` |
| `Rare` | 19 | 42 | `ItemGenerator.[0]` | `absent` | `absent` |

All four groups currently use `Category = EItemGenerationCategory::Consumable`. These are complete current item/value tables for the specific groups expanded by the mod. Full key: `GamePass_Stash_ItemGenerator_<suffix>.ItemGenerator.<group>.PossibleItems.<entry>.<field>`. Absent fields below are absent locally, not a claim about the engine default.

| Suffix / group | Entry | ItemPrototypeSID | Chance | Weight | MinCount | MaxCount |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `Cheap.[1]` | `[0]` | `Milk` | — | 1 | 1 | 1 |
| `Cheap.[1]` | `[1]` | `Bread` | — | 5 | 1 | 1 |
| `Cheap.[1]` | `[2]` | `Sausage` | — | 5 | 1 | 1 |
| `Cheap.[1]` | `[3]` | `CannedFood` | — | 3 | 1 | 1 |
| `Cheap.[1]` | `[4]` | `Bandage` | — | 2 | 1 | 1 |
| `Common_Var1.[0]` | `[0]` | `Bandage` | 1 | — | 1 | 3 |
| `Common_Var1.[0]` | `[1]` | `Medkit` | 1 | — | 1 | 2 |
| `Common_Var1.[0]` | `[2]` | `Vodka` | 1 | — | 1 | 1 |
| `Common_Var1.[0]` | `[3]` | `Energetic` | 0.5 | — | 1 | 2 |
| `Common_Var2.[0]` | `[0]` | `Sausage` | 1 | — | 2 | 4 |
| `Common_Var2.[0]` | `[1]` | `Bread` | 1 | — | 1 | 2 |
| `Common_Var2.[0]` | `[2]` | `Vodka` | 1 | — | 1 | 2 |
| `Common_Var2.[0]` | `[3]` | `Energetic` | 1 | — | 1 | 3 |
| `Common_Var2.[0]` | `[4]` | `CannedFood` | 1 | — | 1 | 2 |
| `Rare.[0]` | `[0]` | `Bandage` | 1 | — | 2 | 4 |
| `Rare.[0]` | `[1]` | `Medkit` | 1 | — | 2 | 3 |
| `Rare.[0]` | `[2]` | `CannedFood` | 1 | — | 1 | 3 |
| `Rare.[0]` | `[3]` | `AntiRad` | 1 | — | 1 | 1 |
| `Rare.[0]` | `[4]` | `Energetic` | 1 | — | 1 | 2 |

## Concrete incompatibilities in copying the historical file

- Full and No Weapons repeat `Common_Var1.ItemGenerator.[0].PossibleItems.[91]` for Heavy_Military_Helmet and Light_Mercenaries_Helmet. All four variants repeat `Common_Var1.ItemGenerator.[4]` for Veteran and Master. Neither duplicate occurs in the current original: its ten groups are `[0]` through `[9]`, with Veteran at `[4]` and Master at `[5]`. Parser-preserved `#2` keys do not establish the game's interpretation.
- The current Cheap group `[1]` is restricted to Hard, with Bandage Weight 2. The historical expanded group omits that difficulty and uses Bandage Weight 3. It mixes existing Weight entries with new Chance entries. Current Common_Var1 group `[0]` explicitly includes Easy/Medium/Hard and `bAllowSameCategoryGeneration = true`; the corresponding historical group omits both fields.
- The current Cheap, Common_Var1 and Rare generators contain money item references absent from their historical replacements. A new extra-find option must preserve current money groups and existing loot.
- Among the other 852 generators, **54 have value/path differences beyond the absent `SpecificRewardSound` field**, comparing parsed paths and numerically equivalent literals. This counts data differences, not proven runtime regressions; some original fields may come from compiled inheritance. The remaining 798 differ only by that sound field in this comparison.
- Concrete changes outside the four pools: `LesserZone_NorthernCheckpoint_StashGenerator1_CE3C517D422A62D2F61ECA9A396D06C9` uses an `empty` placeholder where today's file references `RU_X4Scope_1`; `LesserZone_SphereTunnel_StashGenerator2_ECE56C564E112CFA3818EEB28A23BC50` likewise replaces `A545D` with `empty`. `Garbage_Plant_StashGenerator7_4AB2B2CF48D0FC16B2E853BF27922273` references `RU_Silen_1` instead of today's `GunBucket_PP`.
- Some world stashes also select different parent pools. For example, `BurntForest_HelicopterBase_StashGenerator3_DBC6D2A14D832E328ECE9FA2FF974EED` selects Rare currently and Common_Var1 in the mod. Several current fixed attachment groups are absent from the old file.

## Usage, inheritance and scope

The actual spawn assignment path is `SpawnActorPrototypes.<spawn>.ItemGeneratorSettings.[rank].ItemGenerators.[entry].PrototypeSID`. It is **not** named ItemGeneratorPrototypeSID at this level. Nested generator-to-generator references use `ItemGenerator.[group].PossibleItems.[entry].ItemGeneratorPrototypeSID`. Also account for `refkey` / `refurl` inheritance and explicit array replacement.

A conservative graph of current generator references plus resolvable inheritance finds 762 generators potentially reaching one of the four pools, including the pools. There are 1,975 matching PrototypeSID occurrences in SpawnActor data: 1,918 on `WorldMap_WP`, with additional test-map and quest-sublevel assignments. These are reference occurrences, not distinct stashes or confirmed runtime reachability. 1,973 belong to ItemContainer spawns and two to DestructibleObject spawns. The graph includes potential inheritance even when descendants repeat full arrays; do not treat that as proof that a base-only patch propagates to every descendant.

This confirms that the mechanism is still connected to current world containers. It also rules out assuming these shared pools are exclusive to ordinary unscripted stashes: quest sublevels reference the same graph. `GamePass` in a generator name is not by itself a paid-content exclusion rule. Current rank-specific `Stash_Cheap_*`, `Stash_Medium_*`, and `Stash_Expensive_*` definitions point to these bases while defining their own item blocks.

## Existing S2Tweaker features and implementation direction

`_stash_patch()` changes `StashPrototypes` Smart-Loot quantities, chances and ItemSetCount. `_loot_patch()` changes existing generator MinCount/MaxCount. NPC equipment quality reweights existing candidates; dropped weapon condition changes existing durability ranges. These do not implement additional categories of stash finds. Keep the new option distinct from the existing "variety" control, which changes ItemSetCount.

Recommended user-facing options: **Extra stash finds**, default off, with independent Artifacts, Weapons, Armor and helmets, and Attachments selections. Separate category enablement from intensity. Derive ordinary, available candidates and any progression limits from live sources rather than the old 163-name list. Preserve current consumables, money, ammunition and fixed rewards. Do not silently increase armor chance when artifacts are disabled.

Before implementation, finish an effective consumer graph with array-override handling and quest/trade/NPC exclusions. Select only appropriate world-stash instances or isolated generator targets. Copying the full historical cfg or globally changing every shared base cannot provide those guarantees. Define category probability using a verified generator structure before presenting a percentage or a maximum-one-item promise. Resolve new array positions against current data; do not reuse old numeric indices.

The implementation fits the existing generated-Pak architecture without additional runtime injection, hooks or executable dependencies. Antivirus classifications still depend on the scanner and build.

`ItemGeneratorPrototypes`, `ItemPrototypes`, `EffectPrototypes`, `TradePrototypes`, `StashPrototypes`, `ArtifactSpawnerPrototypes` and `ObjPrototypes` are already in NEEDED_FILES. `SpawnActorPrototypes` is not. If the implementation uses it for scope verification, add it with a CACHE_SCHEMA increment (currently 23). No cache schema or product code was changed for this research.

## Warnings and verification boundary

- Do not modify templates, quest rewards, money-effect items, named unique weapons, trader inventories, NPC equipment or test-map spawns as a side effect of this option. Do not rely on item existence alone to establish ordinary availability.
- Existing `loot_generators()` safety checks inspect direct items and were designed for scaling existing quantities; they are not a complete transitive safety proof for adding content. Keep both inherited quest flags, money-effect detection and the generator SID-to-struct-key mapping, while strengthening usage checks.
- Preserve rank/difficulty restrictions and preexisting original values. Default settings must generate no patch. A future patch should validate all item references, preserve old slots, and compose deliberately with other loot controls.
- This analysis used static archive/data comparisons only, with no game/GUI launch or mod activation. Actual engine selection probabilities, already-generated stash behavior and runtime compatibility remain unverified.

## Local evidence and handoff

Ignored analysis directory: `out/workshop_review_2026-09-09/ultimate_stashes/`. `inventory.json` identifies the four archives; `live_comparison.json` records generator/item comparisons and original source hashes; `audit.json` records current usage references and path differences; `vanilla_pool_values.json` records the values above; `agent_variants/concise.json` contains the complete additional item lists and variant counts. Extraction and audit scripts are in the parent analysis directory. Decoded originals and foreign Pak contents remain local and must not enter the repository or source release.

Conclusion: a useful requested feature with a current data basis. Implement as independent optional extra finds after resolving target isolation and probability semantics. The historical mod's broad replacement, duplicate indices and coupled chances should not be carried into S2Tweaker.
