# Weapon item detail controls and non-timing upgrade controls

Research for additional controls after 1.40.1, limited to options that do not
edit animations: individual weapon weight, base
price, inventory dimensions, and non-timing upgrade effects. Movement,
reload, aim-in, draw/holster and recovery timing are deferred. No new animation,
UE4SS or Dev Kit work is part of this proposal.

This document defines an implementation scope, not a claim of in-game testing.
Research used the existing local CFG snapshot. It did not change production
code, game files, installed mods or public releases.

## 1. Result and audited scope

The reviewed item list contains **84 IDs**: **72 base items and 12 edition
items**. Of the 131 slot-bearing weapon items returned by the current helper,
47 are excluded: 32 guard variants, two melee stubs, three underbarrel weapon
data items, one quest pistol, and nine named story/special variants.

Each included item explicitly owns all four editable fields:
`Weight`, `Cost`, `ItemGridWidth`, `ItemGridHeight`. The 336 values are listed
below. All 72 base items have an exact item consumer in the extracted
generator, spawn or quest CFGs. Named collectible weapons remain included;
receiving a normal weapon as a quest reward does not make its prototype a
quest-locked item. Special actor replicas and explicitly quest-marked items
are excluded separately.

The 12 edition items have valid item/setup chains in the extracted edition
files. Their acquisition consumers are not present in this local CFG set;
their inclusion is based on their edition inventory definitions. It does not
claim an acquisition route, ownership entitlement or gameplay test. Only show
an edition item when its real local definition is available.

Use this finite identity list with live shape checks for the first release.
Do not automatically enable unknown future items merely because their names
start with `Gun`. A fixed identity list is not a fixed numeric baseline:
values must still be read from `GameData` for every installed game version.

### Exact property paths

For a row with item ID `I`, the only allowed leaves are:

- `ItemPrototypes.cfg: I.Weight`
- `ItemPrototypes.cfg: I.Cost`
- `ItemPrototypes.cfg: I.ItemGridWidth`
- `ItemPrototypes.cfg: I.ItemGridHeight`

For editions, use the same leaves in the item's
`DLCGameData/<edition>/ItemPrototypes.cfg` tree. No weapon setup, character
weapon settings, animation, durability, effect list or quest key is edited.
Weight is item mass, price is the base coupon value, and grid width/height are
positive integer inventory cells.

## 2. Complete included IDs and values

The base table comes from
`vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg`; edition tables
come from `vanilla/Stalker2/Content/GameLite/DLCGameData/<edition>/ItemPrototypes.cfg`.
Setup IDs are shown for classification and scope checking, not as patch targets.

### Base game

| Item SID | Setup SID / category | Weight | Base price | Grid |
|---|---|---:|---:|---|
| `GunAK74_ST` | `GunAK74_ST` / rifle | 3.3 | 10000.0 | 5 x 2 |
| `GunAKU_PP` | `GunAKU_PP` / smg | 2.7 | 6000.0 | 4 x 2 |
| `GunAPB_HG` | `GunAPB_HG` / pistol | 1.1 | 14000.0 | 2 x 1 |
| `GunArevPrecise_AR` | `GunArevPrecise_AR_GS` / rifle | 3.9 | 47900.0 | 5 x 2 |
| `GunArev_ST` | `GunArev_ST_GS` / rifle | 3.25 | 27000.0 | 5 x 2 |
| `GunBucket_PP` | `GunBucket_PP` / smg | 1.6 | 12000.0 | 4 x 2 |
| `GunD12_SG` | `GunD12_SG` / shotgun | 3.6 | 24000.0 | 5 x 2 |
| `GunDnipro_ST` | `GunDnipro_ST` / rifle | 2.9 | 34000.0 | 5 x 2 |
| `GunFora230_PP` | `GunFora230_PP_GS` / smg | 1.7 | 13500.0 | 4 x 2 |
| `GunFora_ST` | `GunFora_ST` / rifle | 3.3 | 15000.0 | 5 x 2 |
| `GunG37V2_ST` | `GunG37V2_ST` / rifle | 3.8 | 16700.0 | 5 x 2 |
| `GunG37_ST` | `GunG37_ST` / rifle | 3.6 | 17000.0 | 5 x 2 |
| `GunGP3A_DMR` | `GunGP3A_DMR_GS` / dmr | 4.4 | 41000.0 | 6 x 2 |
| `GunGauss_SP` | `GunGauss_SP` / sniper | 7.0 | 120000.0 | 7 x 2 |
| `GunGonta_SP` | `GunGonta_SP_GS` / sniper | 4.0 | 17600.0 | 6 x 2 |
| `GunGrim_ST` | `GunGrim_ST` / rifle | 3.2 | 25000.0 | 5 x 2 |
| `GunGvintar_ST` | `GunGvintar_ST` / rifle | 3.2 | 21000.0 | 5 x 2 |
| `GunIntegral_PP` | `GunIntegral_PP` / smg | 2.7 | 17000.0 | 4 x 2 |
| `GunKharod_ST` | `GunKharod_ST` / rifle | 3.3 | 28000.0 | 5 x 2 |
| `GunKora_HG` | `GunKora_HG` / pistol | 1.1 | 6000.0 | 2 x 1 |
| `GunLavina_ST` | `GunLavina_ST` / rifle | 2.5 | 26000.0 | 5 x 2 |
| `GunM10_HG` | `GunM10_HG` / smg | 1.4 | 5700.0 | 3 x 2 |
| `GunM16_ST` | `GunM16_ST` / rifle | 3.7 | 14000.0 | 5 x 2 |
| `GunM701_SP` | `GunM701_SP` / sniper | 4.5 | 35000.0 | 6 x 2 |
| `GunM860_SG` | `GunM860_SG` / shotgun | 3.2 | 8000.0 | 5 x 2 |
| `GunMark_SP` | `GunMark_SP` / dmr | 4.1 | 28000.0 | 6 x 2 |
| `GunNightStalker_HG` | `GunNightStalker_HG` / pistol | 1.1 | 11000.0 | 2 x 1 |
| `GunObrez_SG` | `GunObrez_SG` / shotgun | 1.9 | 1700.0 | 4 x 1 |
| `GunPKP_MG` | `GunPKP_MG` / mg | 6.8 | 30000.0 | 6 x 2 |
| `GunPM_HG` | `GunPM_HG` / pistol | 0.5 | 950.0 | 2 x 1 |
| `GunRam2_SG` | `GunRam2_SG` / shotgun | 3.0 | 29000.0 | 5 x 2 |
| `GunRhino_HG` | `GunRhino_HG` / pistol | 1.5 | 10000.0 | 3 x 2 |
| `GunRpg7_GL` | `GunRpg7_GL` / launcher | 6.3 | 50000.0 | 6 x 2 |
| `GunSKP_DMR` | `GunSKP_DMR_GS` / dmr | 3.9 | 33500.0 | 6 x 2 |
| `GunSPSA_SG` | `GunSPSA_SG` / shotgun | 4.4 | 17000.0 | 5 x 2 |
| `GunSVDM_SP` | `GunSVDM_SP` / sniper | 4.9 | 24000.0 | 6 x 2 |
| `GunSVU_SP` | `GunSVU_SP` / sniper | 4.4 | 39000.0 | 5 x 2 |
| `GunTOZ_SG` | `GunTOZ_SG` / shotgun | 3.1 | 3000.0 | 5 x 2 |
| `GunThreeLine_SP` | `GunThreeLine_SP_GS` / sniper | 4.0 | 3500.0 | 6 x 2 |
| `GunUDP_HG` | `GunUDP_HG` / pistol | 0.72 | 1425.0 | 2 x 1 |
| `GunViper_PP` | `GunViper_PP` / smg | 2.5 | 3000.0 | 4 x 2 |
| `GunZubr_PP` | `GunZubr_PP` / smg | 2.1 | 20000.0 | 4 x 2 |
| `Gun_Cavalier_SR` | `Gun_Cavalier_SR_GS` / sniper | 4.5 | 40000.0 | 6 x 2 |
| `Gun_Combatant_AR` | `Gun_Combatant_AR_GS` / rifle | 3.3 | 12500.0 | 5 x 2 |
| `Gun_Deadeye_HG` | `GunUDP_Deadeye_HG` / pistol | 0.72 | 2925.0 | 2 x 1 |
| `Gun_Decider_AR` | `Gun_Decider_AR_GS` / rifle | 3.3 | 16000.0 | 5 x 2 |
| `Gun_Drowned_AR` | `Gun_Drowned_AR_GS` / rifle | 3.3 | 11500.0 | 5 x 2 |
| `Gun_Encourage_HG` | `Gun_Encourage_HG_GS` / pistol | 1.1 | 8200.0 | 2 x 1 |
| `Gun_GStreet_HG` | `Gun_GStreet_HG_GS` / smg | 1.4 | 8900.0 | 3 x 2 |
| `Gun_Krivenko_HG` | `Gun_Krivenko_HG_GS` / pistol | 0.72 | 3425.0 | 2 x 1 |
| `Gun_Lummox_AR` | `Gun_Lummox_AR_GS` / rifle | 3.3 | 12000.0 | 5 x 2 |
| `Gun_Lynx_SR` | `Gun_Lynx_SR_GS` / sniper | 4.9 | 25500.0 | 6 x 2 |
| `Gun_Merc_AR` | `Gun_Merc_AR_GS` / rifle | 3.2 | 38000.0 | 5 x 2 |
| `Gun_Partner_SR` | `Gun_Partner_SR_GS` / dmr | 4.1 | 33400.0 | 6 x 2 |
| `Gun_Predator_SG` | `Gun_Predator_SG_GS` / shotgun | 3.2 | 11800.0 | 5 x 2 |
| `Gun_ProjectY_HG` | `Gun_Kaimanov_HG_GS` / pistol | 0.5 | 1750.0 | 2 x 1 |
| `Gun_RatKiller_SMG` | `Gun_RatKiller_SMG_GS` / smg | 2.1 | 27000.0 | 4 x 2 |
| `Gun_S15_AR` | `Gun_S15_AR` / rifle | 3.2 | 32500.0 | 5 x 2 |
| `Gun_SOFMOD_AR` | `Gun_SOFMOD_AR_GS` / rifle | 3.7 | 25700.0 | 5 x 2 |
| `Gun_Shakh_SMG` | `Gun_Shakh_SMG_GS` / smg | 2.5 | 5700.0 | 4 x 2 |
| `Gun_Sharpshooter_AR` | `Gun_Sharpshooter_AR_GS` / rifle | 3.7 | 41200.0 | 5 x 2 |
| `Gun_Silence_SMG` | `Gun_Silence_SMG_GS` / smg | 2.5 | 18500.0 | 4 x 2 |
| `Gun_Sledgehammer_SG` | `Gun_Sledgehammer_SG_GS` / shotgun | 4.4 | 22000.0 | 5 x 2 |
| `Gun_Sotnyk_AR` | `Gun_Sotnyk_AR_GS` / rifle | 2.9 | 53000.0 | 5 x 2 |
| `Gun_Spitfire_SMG` | `Gun_Spitfire_SMG_GS` / smg | 2.7 | 12000.0 | 4 x 2 |
| `Gun_Spitter_SMG` | `Gun_Spitter_SMG_GS` / smg | 1.6 | 10800.0 | 4 x 2 |
| `Gun_Star_HG` | `Gun_Star_HG_GS` / pistol | 0.5 | 4950.0 | 2 x 1 |
| `Gun_Tank_MG` | `Gun_Tank_MG_GS` / mg | 6.8 | 60000.0 | 6 x 2 |
| `Gun_Texas_SG` | `Gun_Texas_SG_GS` / shotgun | 4.5 | 33500.0 | 5 x 2 |
| `Gun_Trophy_AR` | `Gun_Trophy_AR_GS` / rifle | 2.5 | 29500.0 | 5 x 2 |
| `Gun_Unknown_AR` | `Gun_Unknown_AR_GS` / rifle | 3.7 | 18800.0 | 5 x 2 |
| `Gun_Whip_SR` | `Gun_Whip_SR_GS` / sniper | 4.4 | 40000.0 | 5 x 2 |

### Deluxe

| Item SID | Setup SID / category | Weight | Base price | Grid |
|---|---|---:|---:|---|
| `Gun_Gabion_AR` | `Gun_Gabion_AR_GS` / rifle | 2.5 | 15700.0 | 5 x 2 |
| `Gun_Logarithm_SMG` | `Gun_Logarithm_SMG_GS` / smg | 2.7 | 8700.0 | 4 x 2 |
| `Gun_PistolMonolith_HG` | `Gun_Monolit_HG_GS` / pistol | 0.5 | 300.0 | 2 x 1 |
| `Gun_RifleMonolith_AR` | `Gun_Monolit_AR_GS` / rifle | 3.7 | 5200.0 | 5 x 2 |
| `Gun_ShotgunMonolith_SG` | `Gun_Monolit_SG_GS` / shotgun | 3.2 | 7800.0 | 5 x 2 |
| `Gun_Zvirolov_SR` | `Gun_Zvirolov_SR_GS` / sniper | 4.5 | 26000.0 | 6 x 2 |

### PreOrder

| Item SID | Setup SID / category | Weight | Base price | Grid |
|---|---|---:|---:|---|
| `Gun_Veteran_AR` | `Gun_Veteran_AR_GS` / rifle | 3.2 | 22700.0 | 5 x 2 |

### Ultimate

| Item SID | Setup SID / category | Weight | Base price | Grid |
|---|---|---:|---:|---|
| `Deluxe_GunAK74_ST` | `GunAK74_ST` / rifle | 3.3 | 10000.0 | 5 x 2 |
| `Gun_Margach_SG` | `Gun_Margach_SG_GS` / shotgun | 3.6 | 15500.0 | 5 x 2 |
| `Gun_ModelSpecial_HG` | `Gun_ModelSpecial_HG_GS` / pistol | 1.5 | 16200.0 | 3 x 2 |
| `Gun_Novator_AR` | `Gun_Novator_AR_GS` / rifle | 3.3 | 5800.0 | 5 x 2 |
| `Gun_SMGMonolith_SMG` | `Gun_SMGMonolith_SMG_GS` / smg | 2.5 | 700.0 | 4 x 2 |

## 3. Complete exclusions and evidence

All 32 `GuardGun` items use guard-specific `NPCWeaponAttributes` and ordinary
player setup parents. `Invisible=false` is not a useful exclusion by itself:
all 131 slot-bearing items are visible according to that one field. Exclude
these identities and reject newly discovered guard attribute/parent branches.

- `GuardGunPM_HG`
- `GuardGunUDP_HG`
- `GuardGunAPB_HG`
- `GuardGunM10_HG`
- `GuardGunRhino_HG`
- `GuardGunViper_PP`
- `GuardGunAKU_PP`
- `GuardGunBucket_PP`
- `GuardGunIntegral_PP`
- `GuardGunZubr_PP`
- `GuardGunAK74_ST`
- `GuardGunM16_ST`
- `GuardGunG37_ST`
- `GuardGunFora_ST`
- `GuardGunGrim_ST`
- `GuardGunGvintar_ST`
- `GuardGunKharod_ST`
- `GuardGunLavina_ST`
- `GuardGunDnipro_ST`
- `GuardGunPKP_MG`
- `GuardGunObrez_SG`
- `GuardGunTOZ_SG`
- `GuardGunM860_SG`
- `GuardGunSPSA_SG`
- `GuardGunD12_SG`
- `GuardGunRam2_SG`
- `GuardGunSKP_DMR`
- `GuardGunGP3A_DMR`
- `GuardGunSVDM_SP`
- `GuardGunMark_SP`
- `GuardGunM701_SP`
- `GuardGunSVU_SP`

Other exclusions:

| Item ID | Reason and observed evidence |
|---|---|
| `MeleeStub` | The general setup has no firearm category. This is a melee placeholder. |
| `MeleeShovel` | Uses `MeleeStub` as its general setup and a shovel NPC attribute. |
| `UA_GLaunch_Weapon_Data_En` | `EN_GLaunch_1.ShootingAttach.WeaponPrototypeSID` references it; internal underbarrel weapon data. |
| `UA_GLaunch_Weapon_Data_Ru` | Referenced by `RU_GLaunch_1`, `GunGrim_GLaunch` and `GunDrowned_GLaunch` shooting attachments. |
| `EN_BuckLaunch_Data` | Referenced by `EN_BuckLaunch_1.ShootingAttach.WeaponPrototypeSID`; internal underbarrel data. |
| `Gun_SkifGun_HG` | Live `IsQuestItem=true`; initial-player generators and `E01_MQ01_EquipItemInHands_Gun_SkifGun_HG.EquipmentItemSID` use it. |
| `GunAK74_Phantom_ST` | Explicit phantom setup identity. Its role is not established by a normal item consumer in this CFG snapshot; conservatively excluded. |
| `GunAK74_Korshunov_ST` | Own `NPCWeaponAttributes=GunAK74_Korshunov_ST_NPC`; named special NPC branch. No direct item consumer was found in this snapshot. |
| `GunAK74_Strelok_ST` | `Strelok_ItemGenerator.ItemGenerator.[0].PossibleItems.[0].ItemPrototypeSID`. |
| `GunPKP_Korshunov_MG` | `VartaColonelKorshunovBoss_ItemGenerator.ItemGenerator.[2].PossibleItems.[0].ItemPrototypeSID`. |
| `GunSVU_Sniper_Duga_SP` | `Duga_Sniper_ItemGenerator.ItemGenerator.[0].PossibleItems.[0].ItemPrototypeSID`. |
| `GunGauss_Scar_SP` | `Scar_ItemGenerator.ItemGenerator.[1].PossibleItems.[0].ItemPrototypeSID`. |
| `Gun_Rail_SG` | Named rail variant without an identified normal consumer in this snapshot; conservatively excluded, not asserted unreachable. |
| `GunPM_PDA_Tutorial_HG` | `PDATutorialPrototypes.cfg: [82].ItemSIDs.[2]`; explicitly `IsQuestItem=false`, so the quest flag alone would miss it. |
| `GunTOZ_Gonta` | `SQ94_P_If_GontaIsNear_Pin_0.Conditions.[0].[0].ItemPrototypeSID.VariableValue`; story condition binds this exact identity. |

`GunGonta_SP` is a different item from `GunTOZ_Gonta` and stays in the included
list. Similarly, ordinary collectible named weapons such as `Gun_Deadeye_HG`
stay included: `E05_MQ03_ItemAdd_FaustGun.ItemSID` adds that normal item.
`Gun_ProjectY_HG` is a placed item referenced by
`SpawnActorPrototypes.cfg: 48D94129415BD18A2C087B8F502C6EAE.ItemSID`.
Do not reuse the loot-generation unique-weapon exclusion regex: that filter
prevents duplicating uniques in random loot, a different operation from
editing the metadata of an existing collectible.

## 4. Live validation and inheritance rules

Use `gd.slot_weapon_items()` only as the initial identity/edition inventory.
For a base item, use `gd._resolve_chain(gd.items, item_sid)`; for an edition
item use `gd.dlc_item_chain(edition, item_sid)`. Resolve fields with
`gd._chain_get(chain, path)` or the corresponding public resolver.

The helper's returned category is not a sufficient filter: it calls weapon
classification with item IDs in some paths. Normal examples such as
`GunFora230_PP -> GunFora230_PP_GS`, the named variants and the edition items
can consequently have a missing helper category. Resolve
`GeneralWeaponSetup`, then classify that setup using `gd.weapon_category` or
`gd.dlc_weapon_category`. Require the approved expected item-to-setup mapping.

Required checks before offering or applying an override:

1. The identity is in this list, the expected source/edition exists, and
   `Type` resolves to `EItemType::Weapon` with its normal weapon slot.
2. Check both `IsQuestItem` and `IsQuestItemPrototype` through inheritance.
   Also reject true `Invisible`, `InvisibleInPlayerInventory` and
   `DestroyOnPickup`. Handle boolean strings deliberately, not by Python
   truthiness of the string `"false"`.
3. Reject unknown, ambiguous or changed setup/parent branches; templates,
   duplicate parser keys, guards and special identities are never targets.
4. All edited values are present, numeric and finite. Weight/price must be
   nonnegative; grid dimensions must be positive integers. Invalid values
   must fail validation rather than being silently truncated.
5. Inspect descendants before patching a shared item parent. Every current
   included item owns its four leaves, and no excluded descendant of an
   included parent inherits any of those four leaves. If a later game update
   makes a protected descendant inherit a changed leaf, refuse that edit or
   require a new explicit scope review. Do not write compensating patches to
   protected quest/guard/story items outside the selected scope.

Each ordinary item may be used by player inventories, NPCs, vendors and world
spawns. This is an item-prototype edit affecting copies of that item, not a
save edit restricted to the currently carried gun. Base price can also
influence systems selecting equipment by price. No claim of such behavior
being isolated should appear in the UI.

### Parent and edition example

`Deluxe_GunAK74_ST` is in the **Ultimate** item tree in this snapshot despite
its name. Its item override must target that tree. It uses the base
`GunAK74_ST` setup; editing the skin's weight must not patch the base setup or
the normal AK74 item. Conversely, a normal AK74 item override must not be
silently copied to this distinct skin item. Other edition items have their
own setup IDs; always trust the discovered source tree, not a name prefix.

## 5. Composition with current global controls

Implement item details as absolute optional values, analogous to
`armor_custom`, keyed by **item SID**. Absence means inherit the existing
global settings. An explicit value equal to vanilla is meaningful: it can
override a non-neutral global weight or grid factor.

Apply the detail layer at the end of `_items_patch`, after both base and
edition global item passes, alongside the existing armor custom pass.
Modify only the selected leaf on the selected item. Preserve other item
changes from ammo, weights, grid, flags or other independent settings.

Example: global item weight ×0.5 would write `GunPM_HG.Weight=0.25` from
vanilla `0.5`. An explicit PM value of `0.5` should remove that PM weight
override, leaving its current own vanilla value in force. An explicit value
of `0.4` should replace it with `0.4`. The global factor still applies to
other items. Because every current approved item owns these leaves, removing
the selected leaf is sufficient here; changed inheritance must be checked.

Grid example: AK74 vanilla is `5 × 2`. A global grid factor can change both
dimensions; an explicit width of `5` restores just its width. Height remains
under the global setting unless the user also sets an explicit height.

`Cost` is the base price only. Category difficulty prices, trader buy/sell
coefficients, reputation and condition still apply. Do not promise a final
shop price. Do not add an `InventoryActionTime` or other timing field to this
detail dictionary. Existing global maximum durability is also outside this
limited four-field addition.

## 6. Non-timing upgrade detail controls

Keep the existing family controls for compatibility. Add optional overrides
for the following **effect types**, replacing the family factor for that
type rather than multiplying a second time. This is a global upgrade-effect
control, not an individual weapon's technician tree. A true per-weapon
upgrade editor would require separate effect/reference isolation and is not
part of this minimal integration.

| Effect type | Existing inherited family | Bonus direction | Directly referenced IDs |
|---|---|---|---:|
| `BaseDamage` | `upg_damage_factor` | positive | 4 |
| `ArmorPiercing` | `upg_damage_factor` | positive | 8 |
| `CoverPiercing` | `upg_damage_factor` | positive | 8 |
| `AmmoCapacity` | `upg_handling_factor` | positive | 2 |
| `Dispersion` | `upg_accuracy_factor` | negative | 8 |
| `DispersionMaxRadiusExtension` | `upg_accuracy_factor` | negative | 7 |
| `DispersionPerIterationRadiusExtension` | `upg_accuracy_factor` | negative | 4 |
| `Accuracy` | `upg_accuracy_factor` | positive | 1 |
| `DispersionAimModifier` | `upg_accuracy_factor` | negative | 1 |
| `DispersionOffsetAimModifier` | `upg_accuracy_factor` | negative | 1 |
| `ProtectionStrike` | `upg_armor_protection_factor` | positive | 83 |
| `ProtectionBurn` | `upg_armor_protection_factor` | positive | 91 |
| `ProtectionShock` | `upg_armor_protection_factor` | positive | 87 |
| `ProtectionChemical` | `upg_armor_protection_factor` | positive | 83 |
| `ProtectionPSY` | `upg_armor_protection_factor` | positive | 38 |
| `ProtectionRadiation` | `upg_armor_protection_factor` | positive | 81 |

There are 507 referenced effect IDs across these 16 types. Counts include
penalties and zero placeholders, which retain the current bonus-only
filtering; they are not 507 unconditional patch targets.

The consumer scan inspected 484 CFG files and 11,978,418 lines. Exact value
references to these 507 effects were found only in `UpgradePrototypes.cfg`
and `EffectPrototypes.cfg`. Following reverse effect links and inheritance
adds two composite effects, making 509. No direct item-effect-list consumers
were found in that closure. This excludes neither asset-side consumers nor
future game changes. Upgrades themselves can be installed on different
equipment, and the effect is still shared by every such upgrade.

### Minimal builder rules

- Resolve the effective factor once per allowed type: explicit detail factor
  if the key is present, otherwise its existing family factor. An explicit
  `1.0` must be retained to override a non-neutral family setting; missing is
  the inherit sentinel. Factor `0` keeps the existing meaning of removing
  that bonus, not deleting its effect or upgrade reference.
- Extend the early neutral check in `_upgrade_strength_patch` to consider
  detail overrides. Otherwise a detail-only setting is skipped before the
  effect loop. With no new detail values, the old builder output must remain
  byte-identical.
- Keep the current direct-upgrade-reference scope. Match allowed live
  `EEffectType` values and apply the existing bonus-direction checks to
  `ValueMin` and `ValueMax`. Never scale effects just because their SID starts
  with a matching word. Unknown imported type keys must not become arbitrary
  effect-path edits.
- Preserve units and existing caps. `AmmoCapacityIncrease.ValueMin=50.0`
  and `AmmoCapacityIncrease1.ValueMin=50%` are different operations; their
  corresponding `ValueMax` values match. At ×2 the existing output is
  `100.0` and `100.0%`, respectively. Negative percent bonuses stop at -100%;
  protection percentage bonuses stop at 100%. Do not apply that percentage
  cap to an absolute physical-protection value.
- `DispersionPos15Effect.ValueMin/ValueMax=-15%` becomes `-30%` at ×2;
  `DamageNeg10Effect=-10%` is a penalty in the positive BaseDamage family and
  stays unchanged. `ArmorPiercingPos20Effect=20%` becomes `40%`; its separate
  cover-piercing effect can retain `20%` if the user only overrides armor
  piercing. These examples describe CFG arithmetic, not measured damage.
- For composite display values, compute the **actual effective child
  factors**, including inherited existing family values, after overrides.
  Update a composite summary only when every contributing child changed
  coherently with the same factor and without differing caps/zero/penalty
  filtering. Otherwise leave the existing summary and disclose the mixed
  component values. Do not fabricate one percentage from different bonuses.

Two concrete mixed composites need coverage:

| Composite SID | Existing summary | Children |
|---|---|---|
| `BattleExoskeleton_Varta_Armor_accuracy` | `20%` | `IdleSwayXPos20Effect`, `IdleSwayYPos20Effect`, `DispersionPos15Effect` |
| `HeavyExoskeleton_Monolith_Armor_accuracy` | `20%` | `IdleSwayXPos15Effect`, `IdleSwayYPos15Effect`, `DispersionPos15Effect` |

A new dispersion override can change the last child while the two sway
children stay at their existing factors. The shared 20% display must then
remain unscaled; no new sway control or animation change is introduced.

No new `AimingTime`, `ShowEquipmentTime`, `HideEquipmentTime`,
`RecoilRadiusNormalizationInterval`, movement or reload settings belong to
this change. Existing controls and imported profiles must continue to work
as before unless the user explicitly sets one of the permitted new values.

## 7. Verification required during implementation

The parent implementation should cover neutral output, explicit vanilla
overrides over non-neutral globals, per-leaf composition, distinct base/skin
targets, missing editions, every protected identity, changed inheritance and
invalid imported values. Upgrade tests should cover a detail-only setting,
explicit factor 1 overriding a family, unrelated timing values unchanged,
percent versus absolute capacity, penalty direction and both mixed composites.
No gameplay or animation validation is claimed by this research.

Private evidence and reproducibility scripts are in
`out/slider_audit_1401/combat/`: `weapon_item_scope.py`,
`weapon_item_scope.json`, `consumer_scan.py`, `consumer_scan.json`,
`upgrade_consumer_closure.py`, `upgrade_consumer_closure.json`, and
`write_detail_doc.py`. Raw game files and the private audits must not be
committed or included in a public source archive.

### Core source sizes

| Source | Lines | Top-level structs |
|---|---:|---:|
| `vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg` | 92,232 | 1,375 |
| `vanilla/Stalker2/Content/GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg` | 32,332 | 92 |
| `vanilla/Stalker2/Content/GameLite/GameData/ItemGeneratorPrototypes.cfg` | 277,353 | 3,086 |
| `vanilla/Stalker2/Content/GameLite/DLCGameData/Deluxe/ItemPrototypes.cfg` | 1,092 | 11 |
| `vanilla/Stalker2/Content/GameLite/DLCGameData/PreOrder/ItemPrototypes.cfg` | 435 | 4 |
| `vanilla/Stalker2/Content/GameLite/DLCGameData/Ultimate/ItemPrototypes.cfg` | 732 | 7 |
