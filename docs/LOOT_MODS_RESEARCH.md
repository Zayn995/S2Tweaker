# BNPL, EML and Lootable Zone — reference research

Research snapshot: 2026-09-09. No mod activation, game launch or GUI testing was performed. For the subsequent implementation, see [OPTIONAL_EXTENSIONS.md](OPTIONAL_EXTENSIONS.md).

## Scope and result

Eight supplied archives were read: six BNPL variants, EML 0.5a and Lootable Zone 2.0. Their ten Pak indices contain 3,936 configuration files. All were extracted/read with zero reader errors. Parsing and targeted comparisons against the installed game's current original data support this feature assessment; they are not an exhaustive validation of every quest graph or compiled Blueprint.

Concrete future candidates: ordinary NPC armor drop chance; NPC-carried ammunition amounts; more varied faction/rank equipment pools; mutant-part weight and value controls; investigating field-repair items through native quest/effect configuration. Fast looting and backpack interfaces are larger optional asset-based features. Existing loot/quality sliders do not automatically cover these capabilities or third-party item definitions.

## Source packages

| Reference | Paks | Configs | Config bytes read |
| --- | ---: | ---: | ---: |
| `bnpl_base` | 1 | 1 | 622,064 |
| `bnpl_armor` | 1 | 1 | 632,901 |
| `bnpl_armor_always` | 1 | 1 | 632,797 |
| `bnpl_ammo_half` | 1 | 1 | 621,384 |
| `bnpl_ammo_double` | 1 | 1 | 622,162 |
| `bnpl_lz_test` | 1 | 1 | 617,521 |
| `eml` | 2 | 4 | 87,285 |
| `lootable_zone` | 2 | 3926 | 16,087,312 |

Primary author pages: [Better NPC Progressive Loadouts](https://www.nexusmods.com/stalker2heartofchornobyl/mods/596?tab=description), [Extended Mutant Loots](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1452?tab=description), [Lootable Zone](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1495?tab=description). BNPL describes retaining equipment diversity through progression and primarily affecting newly generated NPCs. EML 0.5 targets game 2.0+, with localization updated in 0.5a. Lootable Zone describes MCM-controlled inventory and survival systems. These are author claims; the data findings below come from the supplied local archives.

## BNPL: separate the useful ideas from the supplied table

All six variants contain 187 generator definitions: 108 SIDs match the current base game, 79 are additional. Their cfg is `ItemGeneratorPrototypes/New_NPC_Loadouts.cfg`. The 0.35 variants redefine loadout blocks; the TEST 0.36 file changes the patch structure.

| Variant | Observed difference from Base 0.35 |
| --- | --- |
| Armor Drop | 52 additional item rows with `Chance = 0.1`, `MinDurability = 0.2`, `MaxDurability = 0.8` |
| Always Armor Drop | Same additional rows with `Chance = 1`; same durability range |
| X2 Ammo | Changes 795 `AmmoMaxCount` fields; minimums unchanged |
| X0.5 Ammo | Changes 795 maximums and 550 minimums |
| TEST for Lootable Zone 0.36 | Same values as Base after SID matching and analytical normalization of two malformed headers; changes merging strategy |

Ammo values live at `<generator>.ItemGenerator.<slot>.PossibleItems.<entry>.AmmoMinCount/AmmoMaxCount`. They are distinct from the `MinCount/MaxCount` fields used by S2Tweaker's existing loot-amount control. A separate ammo control should define both bounds and preserve minimum <= maximum. Do not present the two supplied ammo variants as symmetric scaling of both ends.

All changed maximum-value groups, Base -> Half -> Double: 4 -> 2 -> 8 (27 entries), 7 -> 4 -> 14 (84), 10 -> 5 -> 20 (206), 30 -> 15 -> 60 (460), 50 -> 25 -> 100 (14), and 2 -> 1 -> 4 (4). Half changes minimums 5 -> 2 (76 entries) and 10 -> 5 (474); other minimums remain unchanged. Example `GeneralNPC_Neutral_WeaponPistol`, Newbie / `GunPM_HG`: current original 0–3, BNPL Base 5–10, Half 2–5, Double 5–20. Base also changes category/rank/weights, so it is not itself a standalone ammo tweak.

Armor drop chance and condition are separate from the equipment `Weight` lottery. The existing gear-quality control reweights already-present candidates; it neither creates new armor loot rows nor supplies BNPL's wider rank/faction distributions. A future variety option must preserve faction roles and current availability, without making every NPC use a universal pool. Raw Chance values are configuration evidence, not independently verified gameplay percentages.

The 52 added armor rows refer to 38 distinct current base-game armor IDs, sometimes mapping NPC-specific equipment to a different usable outfit. The current dropped-condition control only targets weapons; armor loot condition would be an additional capability.

The TEST file removes `_Override` from 109 top-level names and uses bpatch on those roots and their ItemGenerator blocks, allowing unrelated named sibling slots to survive. However, two headers contain literal `ItemGenerator : struct.begin {bpatch} {bpatch}` (Corpus sniper/heavy; source lines 18051/18162). The current parser does not accept this header form. All variants also contain 65 `PlayerRank` values with a duplicated `ERank::ERank::` prefix. Engine tolerance is unverified. The analytical comparison normalizes the malformed headers solely to compare intended values; it does not repair the downloaded files.

There are 209 distinct referenced item SIDs, including 77 outside base-game Items. Many explicitly belong to Project Itemization or faction-patch integrations. `SEVA_Monolith_Armor` is confirmed in the installed Deluxe DLC and must not be rejected as obsolete. `GuardGunGauss_SP` and `GuardGunRpg7_GL` were not found in the checked base/edition item definitions. Some generator references need external integrations; keep an explicit dependency/scope check instead of copying the historical table.

## EML: new content and a real gap in our weight controls

The four cfgs contain 34 generators, 66 item definitions, 53 meshes, and patches for 26 existing mutant ObjPrototypes. The item definitions consist of 14 existing trophies, one existing template and 51 new items. Fifty of the new items occur in its generator references; `KadavrHelmetLoot` does not. The new mesh references resolve against EML plus the current original mesh definitions. Models, icons and localization also require the supplied content assets; plain cfg output cannot reproduce them by itself.

The following table includes every existing trophy touched by EML. Paths are `ItemPrototypes.<SID>.Weight/Cost`; chance paths are `<SID>Generator.ItemGenerator.<group>.PossibleItems.<row>.Chance`. For loot paths below, the pair means `group.row`.

| Trophy SID | Vanilla weight | EML weight | Vanilla Cost | EML Cost | Vanilla Chance | EML Chance | EML loot path |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `TushkanLoot` | 0.01 | 0.01 | 500 | 500 | 0.1 | 0.3 | `[0].[1]` |
| `FleshLoot` | 0.05 | 0.05 | 1000 | 1000 | 0.2 | 0.3 | `[0].[3]` |
| `BoarLoot` | 0.5 | 0.5 | 2000 | 2000 | 0.2 | 0.3 | `[0].[0]` |
| `BlinddogLoot` | 0.05 | 0.1 | 1000 | 1000 | 0.15 | 0.25 | `[0].[2]` |
| `SnorkLoot` | 1 | 1 | 2500 | 2500 | 0.2 | 0.25 | `[0].[2]` |
| `CatLoot` | 0.05 | 0.1 | 8000 | 8000 | 1 | 0.9 | `[0].[0]` |
| `BloodsuckerLoot` | 0.4 | 0.4 | 4000 | 4000 | 0.5 | 0.5 | `[0].[3]` |
| `PseudodogLoot` | 1 | 0.5 | 2500 | 2500 | 1 | 0.9 | `[0].[2]` |
| `PoltergeistLoot` | 0.6 | 0.75 | 6500 | 6500 | 0.65 | 0.7 | `[0].[3]` |
| `BurerLoot` | 0.1 | 0.1 | 4000 | 4000 | 1 | 0.6 | `[0].[2]` |
| `ControllerLoot` | 0.5 | 0.5 | 4000 | 5000 | 1 | 0.9 | `[0].[1]` |
| `ChimeraLoot` | 0.2 | 0.2 | 18000 | 18000 | 1 | 0.9 | `[0].[5]` |
| `DeerLoot` | 1.6 | 2 | 14000 | 14000 | 1 | 1 | `[0].[3]` |
| `PseudogiantLoot` | 0.8 | 1 | 17000 | 17000 | 1 | 1 | `[0].[0]` |

S2Tweaker's item-category mapping does not include `MutantLootTemplate`, so the current item-weight control skips these 14 trophies. A dedicated mutant-parts weight control is therefore useful even without EML. A new price control can address the underlying trophy Cost separately from the existing trader buy/sell multipliers. The usual trophy drop-chance control already exists; do not list it as a wholly new feature.

**Compatibility finding:** EML moves 11 of the 14 existing trophies away from their original `[0]` item position. `_mutant_loot_patch()` currently derives paths from vanilla only. With EML active, the same numeric path can address a different new part: Tushkan's first item becomes MutantBlood and the original trophy moves to `[1]`. Applying our vanilla-derived patch may therefore affect a different item, depending on effective mod loading. No compatibility guarantee is justified without reading/resolving the effective modded structure.

Three EML Poltergeist entries use `ItemPrototypeSID` to reference its own `MutantLoot*ArtifactGenerator` definitions, although those are generators rather than items. The current base game does not contain those item SIDs. EML elsewhere uses the proper subgenerator shape, `Category = SubItemGenerator` plus `ItemGeneratorPrototypeSID`. Three additional item names (`FArtifactDemonsHorn`, `FleshSinTransformation`, `PArtifactBloodyCup`) are absent from the checked base and installed edition DLC definitions. These unresolved references should not become generated S2Tweaker output. They do not establish that every EML feature is broken.

## Lootable Zone: data additions, interfaces, and repair mechanics

Lootable Zone supplies 3,926 cfgs, including 1,132 QuestNodePrototypes files, 1,185 QuestPrototypes files and 1,556 SpawnActorPrototypes files. Parsed quest-node roots total 5,670. There are 416 distinct item definitions including templates/helpers, 346 effects and 532 distinct generator roots across additions and patches. Do not equate item definitions or spawn files with usable item counts or distinct active world spawns.

Its override Pak patches 129 generator roots, all present in current vanilla. NPC inventory additions use named `KpLM_Items_<rank>` slots. Nine mutant loot generators receive a named `Kp_LM_Patch` slot. Four shared stash pools receive slots `[86]` through `[89]`; those slots are absent in the current original, but another mod can still use them. Six targets overlap existing slots intentionally: four breakable-food generators and two prologue quest inventory generators. Thus the complete mod also affects fixed gameplay content outside ordinary loot.

Fast-loot, backpack and MCM work cannot be inferred from cfg tables alone. The local AssetRegistry contains `BPI_MCM_API`, `BPI_MCM_SettingsProvider`, `MWSS_LootableZone` and backpack UI names; compiled UCAS Blueprint bodies were not decoded. Global-variable cfgs expose power-system flags and equipped backpack/knife state, which are state definitions, not a ready-made generic MCM-to-cfg converter. Initial global defaults must not be assumed to overwrite existing saved state or MCM settings.

### Field-repair items: concrete native effect route worth investigating

The repair mechanism is partly visible in cfg. For example `KpAdvancedSewingKit` checks equipment/conditions in a quest, then uses `EQuestNodeType::SetCharacterEffect` with `EffectPrototypeSID = KpAdvancedSewingKit`. Its effect uses the native `EEffectType::Corrosion`, a selected `InventoryEquipmentSlot` and negative percentage values. Current vanilla contains 93 Corrosion effect definitions with the same basic schema, but none of those direct values are negative. The repair interpretation is supported by the mod's construction and author description; a new standalone implementation's behavior remains unverified.

Complete Corrosion-effect values in Lootable Zone, all with `Positive = EBeneficial::Positive`. Full path: `EffectPrototypes.<SID>.Type/InventoryEquipmentSlot/ValueMin/ValueMax`.

| Effect SID | Equipment slot | ValueMin | ValueMax |
| --- | --- | ---: | ---: |
| `KpRepairPistol` | `Pistol` | -20% | -20% |
| `KpRepairPrimary` | `PrimaryWeapon` | -20% | -20% |
| `KpRepairSecondary` | `SecondaryWeapon` | -20% | -20% |
| `KpRepairHelm` | `Head` | -20% | -20% |
| `KpRepairBody` | `Body` | -20% | -20% |
| `KpLightArmorRepairKit` | `Body` | -20% | -20% |
| `KpMediumArmorRepairKit` | `Body` | -20% | -20% |
| `KpHeavyArmorRepairKit` | `Body` | -20% | -20% |
| `KpExoskeletonRepairKit` | `Body` | -20% | -20% |
| `KpHeadgearRepairKit` | `Head` | -25% | -25% |
| `KpHandgunRepairKit` | `Pistol` | -20% | -20% |
| `KpMediumLargeRepairKit` | `PrimaryWeapon` | -20% | -20% |
| `KpShotgunRepairKit` | `PrimaryWeapon` | -20% | -20% |
| `KpSmallboreRepairKit` | `PrimaryWeapon` | -20% | -20% |
| `KpEmergencyArmorRepairSet` | `Body` | -12% | -12% |
| `KpBasicSewingKit` | `Body` | -16% | -16% |
| `KpAdvancedSewingKit` | `Body` | -16% | -16% |
| `KpHeavySewingKit` | `Body` | -16% | -16% |
| `KpM17GlueTube` | `Body` | -10% | -10% |
| `KpZviezdaGlueTube` | `Body` | -4% | -4% |
| `KpTurGlueTube` | `Body` | -8% | -8% |
| `KpProLineHandgunCleaningKit` | `Pistol` | -12% | -12% |
| `KpNorthstarCleaningKit` | `PrimaryWeapon` | -12% | -12% |
| `KpMediumLargeCleaningKit` | `PrimaryWeapon` | -12% | -12% |
| `KpValuProCleaningKit` | `PrimaryWeapon` | -12% | -12% |
| `KpHoppesCleaningSolvent` | `PrimaryWeapon` | -16% | -16% |
| `KpDvojkaGunOil` | `PrimaryWeapon` | -13% | -13% |
| `KpFalconGunOil` | `PrimaryWeapon` | -6% | -6% |
| `KpBrunoxSprayLubricant` | `PrimaryWeapon` | -10% | -10% |

A standalone field-repair feature would still need an original usable item or deliberate existing-item trigger, correct effect/quest linkage, equipment restrictions and validation of clamping/condition rules. Do not copy Lootable Zone's full quests, item assets or global state. A simple setting for repair strength in an already installed supported mod is a different possible feature from creating new repair kits ourselves.

Another directly readable field is `CoreVariables.DefaultConfig.BoltLifetime`: current vanilla 20.0, Lootable Zone 500.0. This only addresses the lifetime field; it does not implement the separate collectible-bolt inventory, UI or requirement system. S2Tweaker does not currently expose it.

## Cross-mod interactions and exclusions

EML and Lootable Zone both define four identical meat SIDs with different data:

| SID | EML weight / Cost | Lootable Zone weight / Cost |
| --- | --- | --- |
| `KpBlinddogMeat` | 0.2 / 200 | 0.3 / 40.0 |
| `KpBoarMeat` | 0.25 / 350 | 0.5 / 40.0 |
| `KpChimeraMeat` | 0.4 / 6200 | 1 / 40.0 |
| `KpDeerMeat` | 0.35 / 5000 | 0.7 / 40.0 |

Their mesh definitions also differ. EML's meat/organs inherit its mutant-loot template; names alone do not establish edible food behavior. A compatibility patch would need to reconcile these definitions and generator additions, not just choose an arbitrary file order.

Do not copy quest/collar loot, DLC-only equipment, test generators, broad NPC replacement tables or unresolved foreign item references into ordinary loot options. Preserve both item identity and context when generating patches. Existing filters were designed around current original definitions; they do not represent a general third-party mod merge engine.

No DLL, EXE or Lua payload appears in these eight archive inventories. Config-only features fit the current antivirus-friendly architecture; larger Blueprint/UI features require ordinary content assets and remain a separate engineering task. This is not a guarantee about scanner classifications.

## Implementation handoff and evidence

Priority candidates: (1) independent NPC armor loot controls, (2) NPC carried-ammo bounds, (3) mutant-part weight/value controls, (4) equipment variety that preserves rank/faction availability. Investigate native field-repair items next. Optional fast-loot/backpack/MCM interfaces are larger work. More third-party loot variety should first address the effective-data/path compatibility issue found with EML.

The necessary base files for the small numeric candidates are already in NEEDED_FILES. Reading external mod additions, adding new file families or supporting ModGameData patches would require explicit architecture work; a new required vanilla file also requires CACHE_SCHEMA increment. Research did not change the schema or product behavior.

Private, ignored evidence: `out/workshop_review_2026-09-09/new_loot_mods/inventory.json`, `lootable_zone_summary.json`, `lootable_zone_audit.json`, `interactions.json`, plus `agent_bnpl/` and `agent_eml/` reports/tables. Fresh original sources are under the earlier analysis folders and `new_loot_mods/live_vanilla`; the edition comparison uses the installed 101/102/104 Paks. Scripts are in the parent analysis directory. Keep extracted game/mod files and proprietary DLLs outside source releases.

All conclusions here are static analysis. No gameplay effects, load ordering, save compatibility or compiled Blueprint behavior were tested in a running game.
