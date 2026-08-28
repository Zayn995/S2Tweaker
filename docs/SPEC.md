# S.T.A.L.K.E.R. 2 Tweak Generator — Implementation Specification

**Target game version:** 2.0.3 (released 2026-08-26; Update 2.0 "Back to the Zone" 2026-08-20 upgraded the engine UE 5.1 → UE 5.5.4 and shipped with the "Cost of Hope" DLC).
**Deliverable:** Windows GUI tool that renders sliders/checkboxes and emits a single mod `.pak` into the game's `~mods` folder.
**Core finding:** every requested feature except bullet time is implementable through GSC's text `.cfg` GameData system, packaged as a plain legacy pak. Bullet time is out of cfg scope (see §4).

**Vanilla-value provenance warning (applies to every table below):** most exact numbers were verified against the Steam **v1.1.3** dump (github.com/chrisvblemos/stalker2cfg) and/or a **~1.7/1.8-era** dump (github.com/RetrowaveRat/Stalker2, pushed 2026-01-10). Balance drift between patches is proven (see §7). Where a value was re-confirmed for 2.0 via a current mod, this is stated. The tool should not hardcode vanilla values for multiplier features — see §3.

---

## 0. The edit mechanism the tool MUST use: the official config-patch system (`{bpatch}`)

Since patch 1.6 the engine has an **official partial-patch system** (ZoneKit doc "Config patches", https://zonekit-support.stalker2.com/hc/en-us/articles/39357395461265-Config-patches). This is the recommended output format for every feature — never ship whole-file replacements.

Rules (verified from the official doc):
- For each `Base.cfg` / `Base.cfg.bin`, the engine looks for `Base.cfg_patch_*` / `Base.cfg.bin_patch_*` files during load. The config cache scans everything under `Content\GameLite\GameData`.
- **Exception:** inside binarized prototype folders, `.cfg_patch_*` is NOT searched — there the patch file must use the plain `.cfg` extension, and "all patching functionalities, along with the new keywords, will continue to operate seamlessly."
- Semantics: a top-level node with a new name is **appended**; a same-name node **replaces the entire node** by default; `RootB : struct.begin {bpatch}` **merges** (listed keys overwritten, unlisted keys keep vanilla, new keys added); inside a `{bpatch}` struct, `[2] : removenode` deletes a child (only works with `{bpatch}`). Patches can reference base-cfg nodes without `refurl`; a `refurl` to a missing `.cfg` inside a prototype folder is redirected to the `.cfg.bin`.
- Works from plain repak paks in `~mods` — no SDK required (dump maintainer hwkmod: "You don't need SDK to use the new {bpatch}. Classic pak/unpak are compatible with it!").

**Proven-in-the-wild naming convention** (sdwvit/S2Mods, whose paks were regenerated against game v2.0 — https://github.com/sdwvit/S2Mods): patches for `GameData/X.cfg` go into a folder named after the cfg, with plain `.cfg` extension:

```
<Mod>_P/Stalker2/Content/GameLite/GameData/ObjPrototypes/ObjPrototypes_patch_<Mod>.cfg
<Mod>_P/Stalker2/Content/GameLite/GameData/ObjPrototypes/GeneralNPCObjPrototypes/GeneralNPCObjPrototypes_patch_<Mod>.cfg
<Mod>_P/Stalker2/Content/GameLite/GameData/ObjWeightParamsPrototypes/ObjWeightParamsPrototypes_patch_<Mod>.cfg
```

Verbatim working example (sdwvit MaxStamina200, current for v2.0):

```
Player : struct.begin {bpatch}
   VitalParams : struct.begin {bpatch}
      MaxSP = 200
   struct.end
struct.end
```

⚠ **Contradiction flag (naming):** the official doc's examples use `Test.cfg_patch_mod` **next to** the base file; sdwvit's proven 2.0 mods use `<CfgName>/<CfgName>_patch_<Mod>.cfg` **subfolder** with plain `.cfg`. Both reportedly work; the sdwvit convention is field-proven on 2.0 and also satisfies the "plain `.cfg` inside prototype folders" exception. **Use the sdwvit convention.**

Fallback/legacy mechanism (pre-1.6, still works): `refurl`/`refkey` inheritance — `MyName : struct.begin {refurl=../CoreVariables.cfg;refkey=DefaultConfig}` listing only changed keys; `{bskipref}` to replace an inherited array wholesale; same-SID full-struct override wins by load order ("Cfg files are loaded alphabetically, and what is below can use and override what is above"). Caveats: reference operators only work on structs with an SID; `CoreVariables.cfg`/`AIGlobals.cfg` `DefaultConfig` structs historically resisted refurl overrides (Nexus article 138, https://www.nexusmods.com/stalker2heartofchornobyl/articles/138; modding.wiki/en/stalker2heartofchornobyl/developers/ConfigFiles); joric: "refkey on structure with refkey works badly and leads to errors and crashes"; `[*]` auto-index lists cannot be inherited via refkey. One modding.wiki example writes `ref=` instead of `refurl=` — treat as a typo; vanilla files use `refurl=`. **Prefer `{bpatch}` everywhere; use refurl/bskipref only where bpatch is awkward.**

Open question (both agents): merge order when multiple `.cfg_patch_*` files from different mods hit the same base cfg is undocumented (presumed alphabetical).

---

## 1. Feature-by-feature specification

All in-pak paths below are prefixed `Stalker2/Content/GameLite/GameData/`. (FModel dumps omit the `Content` segment — `Stalker2/GameLite/GameData/...` — but **working mod paks must include `Content`**.)

### 1.1 Item weights scaling (slider, e.g. 0–100% of vanilla)

| | |
|---|---|
| **Files** | `ItemPrototypes.cfg` (root; base struct `[0]`, SID = Empty) + `ItemPrototypes/` folder: `AmmoPrototypes.cfg` (20,965 B), `ArmorPrototypes.cfg` (258,090 B), `ArtifactPrototypes.cfg` (156,729 B), `AttachPrototypes.cfg` (94,416 B), `BlueprintPrototypes.cfg` (22,080 B), `ConsumablePrototypes.cfg` (33,308 B), `DetectorPrototypes.cfg` (7,235 B), `GDItemPrototypes.cfg` (859 B), `GrenadePrototypes.cfg` (2,438 B), `KeyItemPrototypes.cfg` (4,076 B), `QuestItemPrototypes.cfg` (104,783 B), `WeaponPrototypes.cfg` (99,823 B) |
| **Key** | `Weight` (float, per item struct; per-round for ammo). Base default `Weight = 0.0` in `[0]`. Companion flag in `[0]`: `IgnoreEquippedWeight = false` (`// Weight will be ignored if item is equipped and flag set to true`) |
| **Vanilla examples (1.1.3)** | GrenadeRGD5 0.2, GrenadeF1 0.5, Bread 0.3, CannedFood 0.4, Bandage 0.05; ammo A918D 0.006, A045D 0.008, A545D 0.011 |
| **Inheritance** | `TemplateGrenade : struct.begin {refurl=../ItemPrototypes.cfg;refkey=[0]}`; items via `GrenadeRGD5 : struct.begin {refkey=TemplateGrenade}`. Items may inherit Weight and not declare it (mod 172's author found `Gun_Decider_AR` "had no weight listed, and was pulling from another") |
| **Edit strategy** | Because it's a multiplier over hundreds of items, the tool must **enumerate every item SID + resolved vanilla Weight from an extracted current dump** (see §3), then emit per-file bpatch cfgs containing one `{bpatch}` struct per item with the scaled `Weight`. ⚠ Do NOT regex-replace `Weight =` blindly — `Weight` is reused as a probability key in nested effect arrays (e.g. Bread's `NegativeEffectPrototypeSIDs` entries have `Weight = 1`); a real cfg parser is required. Offer a cheap checkbox alternative: `IgnoreEquippedWeight = true` in `ItemPrototypes.cfg` `[0]` (the "Weightless Equipment" mod 253 approach, current for 2.0.3) |
| **Confidence** | High (paths/keys; mods 172 & 253 updated 20/25 Aug 2026 confirm survival into 2.0.x). Medium on individual vanilla numbers |
| **Prior art** | Nexus mods 45, 172, 253, 387 |
| **Open** | Post-2.0 value drift; whether ammo has any pack/box weight key (none observed) |

Sources: https://github.com/chrisvblemos/stalker2cfg · https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/ItemPrototypes.cfg · .../ItemPrototypes/GrenadePrototypes.cfg · https://www.nexusmods.com/stalker2heartofchornobyl/mods/45 · /mods/172 · /mods/253 · /mods/387 · https://modding.wiki/en/stalker2heartofchornobyl/developers/ConfigFiles

### 1.2 Max carry weight (slider, kg)

Three files must be patched **coherently** (this is what "Higher Max Carry Weight" mod 1034 and sdwvit's 35KgPenalty do):

| File | Struct → keys | Vanilla |
|---|---|---|
| `ObjWeightParamsPrototypes.cfg` | `DefaultWeightParams : struct.begin {refkey=[0]}` → `MaxInventoryMass`, `InventoryPenaltyLessWeight`, nested `WeightEffectParams` array `Threshold` values | `MaxInventoryMass = 80`, `InventoryPenaltyLessWeight = 49.99`; Thresholds: `[0]` 80.f (no effect), `[1]` 70.f → OverweightMovementVelocityChange_3, `[2]` 60.f → _2, `[3]` 50.f → _1. **Re-confirmed vanilla for 2.0** via sdwvit 35KgPenalty (2.0-regenerated: 45/14.99/45/35/25/15) |
| `CoreVariables.cfg` | `DefaultConfig` (selected via `CurrentConfig : struct.begin / LaunchConfig = DefaultConfig`) → `InventoryPenaltyLessWeight`, `MediumEffectStartUI`, `CriticalEffectStartUI` (UI color thresholds) | 50.0 / 50 / 70 |
| `ObjEffectMaxParamsPrototypes.cfg` | `DefaultEffectMaxParamsSID` → `MaxEffectValues` entry `[9]`: `EffectSID = EEffectType::AdditionalInventoryWeight / MaxValue = 140` (the "140 kg cap"); same struct: `PenaltyLessWeight` MaxValue = 90, `RegenStamina` MaxValue = 30 | 140 / 90 / 30 |

Player links: `WeightParamsSID = DefaultWeightParams` and `EffectMaxParamsSID = DefaultEffectMaxParamsSID` in `ObjPrototypes.cfg` base `[0]`.

**Edit strategy:** bpatch. Given target max `M`, scale `MaxInventoryMass = M`, thresholds proportionally (M, M−10·M/80… or simply M·{1, 0.875, 0.75, 0.625}), `InventoryPenaltyLessWeight` ≈ M·0.625, UI keys to match, and raise `MaxValue` (140) proportionally or to a large number. CoreVariables caveat: `DefaultConfig` resisted refurl overrides historically — use `{bpatch}` (proven: sdwvit's `coreVarsTransformer` targets struct `DefaultConfig`).
**Confidence:** High. **Open:** whether `MaxValue = 140` is kg or accumulated percent (contributing `AdditionalInventoryWeight1..7` effects in `EffectPrototypes.cfg` are %-valued: 5/10/15/20/25...; `DutyArmor_4_E1_CarryweightEffect` ValueMin/Max = 20.0%); community treats it as the 140 kg cap.

Sources: https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/ObjWeightParamsPrototypes.cfg · .../CoreVariables.cfg · .../ObjEffectMaxParamsPrototypes.cfg · https://raw.githubusercontent.com/sdwvit/S2Mods/master/Mods/35KgPenalty/raw/Stalker2/Content/GameLite/GameData/ObjWeightParamsPrototypes/ObjWeightParamsPrototypes_patch_35KgPenalty.cfg · https://www.nexusmods.com/stalker2heartofchornobyl/mods/1034 · /mods/858 · /mods/2306

### 1.3 Carry-weight movement penalty (slider: penalty strength / off)

| | |
|---|---|
| **Files/keys** | `EffectPrototypes.cfg` → structs `OverweightMovementVelocityChange_1` (`ValueMin = ValueMax = -15%`), `_2` (−25%), `_3` (−50%); all `Type = EEffectType::VelocityChangeNoCap`, `bIsPermanent = true`, `DuplicationType = EDuplicateResolveType::KeepNew` (lines ~11094–11124 of 1.1.3 dump). Thresholds mapping in `ObjWeightParamsPrototypes.cfg` `WeightEffectParams` (§1.2). Hard-block at ≥ MaxInventoryMass: `ObjPrototypes.cfg` → `Player.DisableMovementWeightThreshold` → `[0] WeightStatus = EWeightStatus::Overweight` with `BlockingMovement` `[*] = EStateTag::Run/Sprint/Jump/Vault/Walk/Climb`. Weight-scaled stamina drain: `CoreVariables.cfg` `DefaultConfig` → `InventorySPDrainCoef = 0.024`, `InventorySPOverweightDrainCoef = 0.05`, `StaminaWeightCurve = /Script/Engine.CurveFloat'/Game/GameLite/Blueprints/Curves/StaminaWeightCurve.StaminaWeightCurve'` |
| **Edit strategy** | Slider scales the three effect percentages (e.g. 0% = no penalty). bpatch the three `OverweightMovementVelocityChange_*` structs. Optional "never immobile" checkbox: bpatch `Player.DisableMovementWeightThreshold` (remove blocking tags via `removenode`, or set the threshold's `WeightStatus`) — test in-game, `[*]` arrays are the riskiest structure to patch |
| **Vanilla** | −15% at 50–60 kg, −25% at 60–70, −50% at 70–80, full block ≥80 |
| **Confidence** | High for keys/values; medium for patching `[*]` blocking arrays cleanly |

Sources: https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/EffectPrototypes.cfg · .../ObjPrototypes.cfg · .../CoreVariables.cfg

### 1.4 Player max stamina (slider)

| | |
|---|---|
| **File** | `ObjPrototypes.cfg` (root) → `Player : struct.begin {refkey=[0]}` (ID = 1, SID = Player, Blueprint BP_Stalker2Character). **There is no `ObjPrototypes/Player.cfg`** |
| **Keys** | `Player.VitalParams.MaxSP` = **100** (re-confirmed vanilla in 2.0 via sdwvit MaxStamina200 "Doubles the player's maximum stamina from 100 to 200"); `RegenSP = 5.0` (NPC base `[0]`: 10); base `[0].VitalParams.StaminaDisableThresholds`: `[0] Threshold = 15 / RegenerationDelay = 1 / StateTags [0] = EStateTag::Sprint`. If exposing a regen slider, note cap `EEffectType::RegenStamina MaxValue = 30` in `ObjEffectMaxParamsPrototypes.cfg` |
| **Edit strategy** | bpatch — exact working patch is the MaxStamina200 example quoted in §0, file `ObjPrototypes/ObjPrototypes_patch_<Mod>.cfg` |
| **Confidence** | High |

Sources: https://raw.githubusercontent.com/sdwvit/S2Mods/master/Mods/MaxStamina200/meta.mts · https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/ObjPrototypes.cfg

### 1.5 Stamina costs per action (slider, % of vanilla)

Two mechanisms; patch both proportionally for a believable global slider:

1. `ObjPrototypes.cfg` → `Player.StaminaPerAction` (vanilla 1.1.3): `LowCrouch = 0, Crouch = 0, Walk = 0, Run = 0, Sprint = 5.25, Climb = 0, Jump = 16.0, MeleeNormal = 16.0, MeleeStrong = 25.0, MeleeButstock = 12.0, Vault = 12.0`. (Sprint 5.25 independently confirmed by a mod description "vanilla value of 5.25".) NPC base `[0]`: Sprint 0.1, Jump 20, Vault 10, melee 0.
2. `CoreVariables.cfg` `DefaultConfig` → `StaminaRegenStateCoefs`: `Sprint = -1.4`, `SlowRun = 0`, `Run = -0.65`, `Aim = -0.25`; plus `SlowRunThreshold = 0.5f`. Community halves sprint drain by −1.4 → −0.7. Also base `[0]`: `SpendStaminaInSafeZone = true`.

**Edit strategy:** bpatch `Player.StaminaPerAction` values × slider; bpatch `StaminaRegenStateCoefs` negatives × slider. **Confidence:** high on keys/values (1.1.3-verified only; runtime formula combining the two with `RegenSP` is engine-side/undocumented). Prior art: Nexus 433, 512, 1039, 845, 1458 ("Unlimited stamina", a CoreVariables edit), 136.

Sources: as §1.4 plus https://www.nexusmods.com/stalker2heartofchornobyl/mods/1458

### 1.6 Player max health (slider)

| | |
|---|---|
| **Keys** | `ObjPrototypes.cfg` → `Player.VitalParams`: `MaxHP = 100`, `RegenHP = 0.0` (player has NO passive regen); inherited from base `[0]`: `RegenHP = 1.0`, `RegenHPDelayTimeSeconds = 5`, `RegenHealthModifier = 1.0`. Difficulty scaling: `DifficultyPrototypes.cfg` key `Regen_HP` (Empty 1.0, Easy 1, Hard 0.75; Master preset 0.5 in later dump) |
| **Edit strategy** | bpatch `Player.VitalParams.MaxHP`. Optional checkbox "passive regen": `RegenHP = 1.0` (Nexus mod 1439's approach) |
| **Confidence** | High (1.1.3-verified; 2.0 unconfirmed) |

Sources: https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/ObjPrototypes.cfg · .../DifficultyPrototypes.cfg · https://www.nexusmods.com/stalker2heartofchornobyl/mods/1439

### 1.7 Player damage dealt (slider, multiplier)

**Recommended route — single global multiplier:** `DifficultyPrototypes.cfg` key `Weapon_BaseDamage` ("multiplies damage the PLAYER deals with guns") inside each difficulty struct: `Empty`, `Easy : struct.begin {refkey=Empty}`, `Medium`, `Hard`, `Stalker`, plus `Easy_Xbox/Medium_Xbox/Hard_Xbox/Stalker_Xbox`.

Vanilla: 1.1.3 dump — Empty 1.0, Easy **1.2**, Medium 1.0, Hard 0.75, Stalker inherits 1.0. Jan-2026 (~1.7/1.8) dump — Easy **1.3**, Medium 1.0, Hard 0.75, Stalker **0.75**. ⚠ Contradiction = real patch drift; read current values from the user's install and multiply each difficulty struct's value by the slider (bpatch per struct, all difficulty structs including Xbox variants).

**Alternative route — per-weapon:** `WeaponData/CharacterWeaponSettingsPrototypes/PlayerWeaponSettingsPrototypes.cfg`, structs `<WeaponSID>_Player` (e.g. `GunAK74_ST_Player`), key `BaseDamage` (siblings: `ArmorDamage`, `ArmorPiercing`, `CoverPiercing`, `BaseBleeding`, `ChanceBleedingPerShot`, `EffectiveFireDistanceMin/Max`, `FireDistanceDropOff`, `MinBulletDistanceDamageModifier`, `DispersionRadius`). Vanilla ~1.7-era table: PM 30, UDP 25, APB 20, Kora 51, Rhino 100; Viper 19, AKU 19, Bucket 23, Integral 13, Zubr 20; AK74 23, M16 16, G37 16, Fora 17, Grim 25, Gvintar 35, Kharod 18, Lavina 20, Dnipro 23; PKP 25; shotguns Obrez/TOZ 150, M860 160, SPSA/D12 140, Ram2 150 (whole pellet cloud); SVDM 70, Mark 55, M701 160, SVU 80, ThreeLine 100, Gauss 500. Unique variants `<...>_Player_WS` inherit via `{refkey=<base>_Player}` (e.g. Gun_Sharpshooter_AR_Player_WS 34.0). Template default in `WeaponData/CharacterWeaponSettingsPrototypes.cfg`. Ammo modifiers stack: `ItemPrototypes/AmmoPrototypes.cfg` → `DamageMod` (default 1.0), `ArmorPiercingMod`, `CoverPiercingMod`, `ArmorDamageMod` (AP ammo: ArmorPiercingMod +0.5, DamageMod 0.98; buckshot ArmorPiercingMod −0.7).

Context: community damage formula `FinalDamage = BaseDamage * ArmorDifferenceCoefProjectiles ^ (ArmorPiercing − Strike)` with `ArmorDifferenceCoefProjectiles = 1.6`, `ArmorDifferenceCoefMeleeAttacks = 1.3` in `ObjPrototypes.cfg` base struct (coefs verified; formula reverse-engineered, medium confidence). Difficulty companions: `NPC_Weapon_BaseDamage` (Easy 0.2→0.17 drift, Medium 0.85, Hard 1.02, Stalker 1.35), `Explosion_BaseDamage`.

**Confidence:** high. **Open:** four new 2.0 weapons (Arev AR, GP3A DMR, SKP DMR, Fora-230 SMG) add new `_Player` structs; interaction with 2.0's in-game "Custom Rules" difficulty (may write the same multipliers — undetermined whether the mod or Custom Rules wins).

Sources: https://raw.githubusercontent.com/RetrowaveRat/Stalker2/main/Content/GameLite/GameData/WeaponData/CharacterWeaponSettingsPrototypes/PlayerWeaponSettingsPrototypes.cfg · .../DifficultyPrototypes.cfg · https://zonekit-support.stalker2.com/hc/en-us/articles/38198715901329-Zone-Kit-Guide-Adding-new-Weapon · https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/ObjPrototypes.cfg

### 1.8 No fall damage (checkbox)

| | |
|---|---|
| **Key** | `ObjPrototypes.cfg` base `[0]` → `Protection : struct.begin / Burn = 0.0 / Shock = 0.0 / ChemicalBurn = 0.0 / Radiation = 0.0 / PSY = 0.0 / Strike = 0.0 / Fall = 0.0 / struct.end` — Player inherits `Fall = 0.0`. Set **`Fall = 100`** (100% protection). GuardBase NPCs ship `Fall = 90.0` for reference. Armor can add Fall protection via its own `Protection` struct in `ItemPrototypes/ArmorPrototypes.cfg`; total ≥100% nullifies fall damage |
| **Exact working patch (sdwvit NoFallDamage, current for 2.0)** | File `ObjPrototypes/ObjPrototypes_patch_NoFallDamage.cfg`: `Player : struct.begin {bpatch}` / `Protection : struct.begin {bpatch}` / `Fall = 100` / `struct.end` / `struct.end` (plus same for `NPCBase` in `ObjPrototypes/GeneralNPCObjPrototypes/GeneralNPCObjPrototypes_patch_NoFallDamage.cfg` if NPCs should be included) |
| **Not the route** | The velocity→HP damage curve is engine/blueprint-side (no `FallDamage` key exists in cfg; grep confirmed). `EffectPrototypes.cfg` `FallHeightMechanics` (HighFallHeight ConditionValue = 150 → FallPostProcess/FallSoundPlay) is camera/sound only. `CoreVariables.cfg` has `StaminaFallingDamageCoef = 0.5` (falls cost stamina), `MaxFallingVelocity = -4000.0`, `MinFallingVelocity = -200.0`, `ClampedMaxFallingVelocity = 2000.0`, `ClampedMinFallingVelocity = 50.0`, `MaxFallHeight = 10000.0` |
| **Confidence** | High (field-proven on 2.0) |

Sources: https://raw.githubusercontent.com/sdwvit/S2Mods/master/Mods/NoFallDamage/raw/Stalker2/Content/GameLite/GameData/ObjPrototypes/ObjPrototypes_patch_NoFallDamage.cfg · https://www.nexusmods.com/stalker2heartofchornobyl/mods/377 · /mods/1594

### 1.9 Traders buy weapons/armor at any condition (checkbox)

| | |
|---|---|
| **File** | `TradePrototypes.cfg` — ~50 named trader structs, each `<Name> : struct.begin {refkey=[0]}` (base `[0]`: SID = Empty, Money = 0, bInfiniteMoney = false) |
| **Keys** | Inside each trader's `TradeGenerators : struct.begin > [*] : struct.begin`: **`WeaponSellMinDurability`** / **`ArmorSellMinDurability`** — vanilla **`0.4f`** (40%) for nearly all; exception `Trader_Soviet_Rostok_TradePrototype` WeaponSellMinDurability = 0.0f. Template example (BaseTraderNPC_Template): `ConditionSID = ConstTrue / ItemGeneratorPrototypeSID = GeneralNPC_TradeItemGenerator / BuyModifier = 0.3f / SellModifier = 1.f / WeaponSellMinDurability = 0.4f / ArmorSellMinDurability = 0.4f` |
| **Trader structs (v1.1.3, patch all)** | Trader_Zalesie_TradePrototype, Trader_ChemicalPlant_TradePrototype, Trader_Terikon_TradePrototype, Bartender_Zalesie_TradePrototype, Technician_ChemicalPlant_TradePrototype, Trader_Armor_Rostok_TradePrototype, Trader_NATO_Rostok_TradePrototype, Trader_Soviet_Rostok_TradePrototype, Trader_Yanov_TradePrototype, GeneralNPC_TradePrototype(_Duty/_Freedom/_Mercenary/_Militaries/_Bandit/_Scientists/_Spark/_Corpus), etc. — enumerate at build time from the extracted dump rather than hardcoding |
| **Related** | `BuyLimitations` (same `[*]` entry) lists `EItemType::` categories a trader refuses outright (GeneralNPC\_\*: Weapon+Armor; medics: Weapon/Armor/Ammo/Grenade/Attach; technicians: Consumable/Ammo/Grenade) — an optional second checkbox "wandering NPCs buy weapons" removes those entries (needs `{bpatch}` + `removenode`; `[*]` arrays are risky — validate in-game). Price scaling by durability preserved automatically via `CoreVariables.cfg` `ItemCostMinPercent = 0.1` (`// Price percentage of base price for item with durability = 0...`). Optional extras: `BuyModifier` (0.3f towns, 0.5f generic TraderNPC/AllTraderNPC/BasicTrader, 0.15f wandering), `SellModifier` (1.f), `BuyDiscounts`/`SellDiscounts` (PlayerRankExperienced 1.15f/0.97f, Veteran 1.2f/0.95f, Master 1.25f/0.9f), `Money`, `bInfiniteMoney`. Confirmed ~30% vanilla buy rate still true in 2.0.x per mod 1728 |
| **Edit strategy** | bpatch: for every trader struct, `TradeGenerators`-nested `WeaponSellMinDurability = 0.0f` / `ArmorSellMinDurability = 0.0f`. ⚠ The keys sit inside a `[*]` array entry — mirror exactly how mods 87/1728/2465 ("done with bpatch method") structure their patches; if nested `[*]` bpatch proves unreliable, fall back to same-SID full-struct override per trader |
| **Confidence** | High |

Sources: https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/TradePrototypes.cfg · https://www.nexusmods.com/stalker2heartofchornobyl/mods/87 · /mods/1728 · /mods/2465 · /mods/1698 · /mods/2488 · /mods/119 · /mods/1790 (TEO, bpatch reference)

### 1.10 Repair costs (slider, multiplier; 0 = free)

| | |
|---|---|
| **Keys** | `CoreVariables.cfg` `DefaultConfig`, `// Repair` section: **`BaseRepairCostModifier = 0.7`**; `ReputationRepairCostModifiers`: `[0] RelationLevel = ERelationLevel::Enemy, Modifier = 2.0`; `[1] Disaffection 1.5`; `[2] Neutral 1.0`; `[3] Friend 0.75`. Secondary lever: `DifficultyPrototypes.cfg` `Repair_Cost` (vanilla 1.0 at all difficulties in 1.1.3) and `Upgrade_Cost` (Hard 1.25) |
| **Edit strategy** | bpatch `DefaultConfig.BaseRepairCostModifier = 0.7 × slider` (0 = free repairs — mod 1482's "Free" option does exactly this) |
| **Formula (empirical, medium conf.)** | RepairCost = WearLevel × BasePrice / 1.9 + WearLevel × TotalUpgradesCost × 0.1 (1/1.9 ≈ 0.7 × 0.75 Friend). The 0.1 upgrade coefficient has no named cfg key found — likely hardcoded |
| **Confidence** | High. ⚠ Low-confidence contradiction: one source claimed launch value was 1.0 and 0.7 is post-patch — 1.1.3 dump definitively shows 0.7; treat 0.7 as vanilla |

Sources: https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/CoreVariables.cfg · https://www.nexusmods.com/stalker2heartofchornobyl/mods/1482 · /mods/77 · /mods/1284 · /mods/171 · https://steamcommunity.com/sharedfiles/filedetails/?id=3382254101

### 1.11 Weapon + armor durability × multiplier (slider)

**Recommended route — global difficulty multipliers** (apply immediately, save-safe): `DifficultyPrototypes.cfg` per difficulty struct:

| Key | Meaning | Vanilla (Empty/Easy/Medium/Hard/Stalker) |
|---|---|---|
| `Weapon_DurabilityDamage` | rate of weapon condition loss (firing + melee) | 1.0 / 0.5 / 1.0 / 1.25 / 1.75 (Stalker 1.75 in later dump; absent in 1.1.3) |
| `Weapon_Durability` | weapon max-health multiplier (also vs anomaly damage) | 1.0 everywhere |
| `Armor_Durability` | armor overall health multiplier | 1.0 / 1.35 / 1.0 / 0.9 / 0.6 |

For "durability ×N": set `Weapon_DurabilityDamage = vanilla / N` and `Armor_Durability = vanilla × N` (optionally `Weapon_Durability × N`) in **every** difficulty struct. "No degradation" preset: Weapon_DurabilityDamage = 0, Weapon_Durability = 9999, Armor_Durability = 9999 (existing mod recipe).

**Alternative per-item route** (finer, but ⚠ item condition is baked into saves — BaseDurability edits "may only work on items spawned after the mod was applied"):
- Weapon wear rate: `WeaponData/CharacterWeaponSettingsPrototypes/PlayerWeaponSettingsPrototypes.cfg` → `DurabilityDamagePerShot` per `<Gun>_Player` (vanilla: PM/UDP 3.3, APB 4.76, Kora 4.0, Rhino 6.67; Viper 0.69, AKU 0.92, Bucket 1.56, Integral 2.3, Zubr 1.67; AK74 1.2, M16 1.04, G37 1.35, Fora 1.39, Grim 1.76, Gvintar 1.79, Kharod 1.76, Lavina 1.79, Dnipro 1.66; PKP 1.38; Obrez/TOZ 3.75, M860 4.3, SPSA/D12 6.0, Ram2 5.71; SVDM 8.0, Mark 3.33, M701 7.4, SVU 11.0, ThreeLine 5.0, Gauss 12.5; RPG-7 66.7; template default 1.0 in `WeaponData/CharacterWeaponSettingsPrototypes.cfg`). NPC weapons: all 36 structs in `NPCWeaponSettingsPrototypes.cfg` have 0.0.
- Weapon max condition: `ItemPrototypes/WeaponPrototypes.cfg` → `BaseDurability` (TemplateWeapon 1000.0, GunPM_HG 1500.0, GunAK74_ST 1950.0, GunM16_ST 1500.0, GunDnipro_ST 3000.0, GunViper_PP 1125.0, GunObrez_SG 2250.0, GunSVDM_SP 1950.0, GunM701_SP 3000.0, GunRhino_HG 3000.0). Wiring: `GeneralWeaponSetup = GunPM_HG`, `PlayerWeaponAttributes = GunPM_HG_Player`, `NPCWeaponAttributes = GunPM_HG_NPC`.
- Armor max condition: `ItemPrototypes/ArmorPrototypes.cfg` → `BaseDurability` (Jemmy/Newbie 780.0, Nasos/Zorya/Seva 910.0, Exoskeleton_Neutral 845.0, Skin_Jacket_Bandit 520.0, Heavy_Mercenaries 1040.0). **No per-hit armor degradation-rate cfg key exists** (engine-side); `CoreVariables.cfg` `ArmorDurabilityParamsCoef = 0.7f` / `HelmetDurabilityParamsCoef = 0.7f` semantics undocumented.
- Jamming (context, don't touch by default): `WeaponData/WeaponGeneralSetupPrototypes.cfg` → `MinJamChance = 0.0`, `MaxJamChance = 4.0–8.0`, `MinJamDurabilityThreshold = 0.75–0.8`, `MaxJamDurabilityThreshold = 0.1`. Note this file contains NO BaseDamage/DurabilityDamagePerShot despite the name.

**Confidence:** high. Prior art: Nexus 497, 1484, 931, 1695 ("uses the new 1.6 Update's patching method" on DifficultyPrototypes.cfg), 2483, 558, 68.

Sources: https://raw.githubusercontent.com/RetrowaveRat/Stalker2/main/Content/GameLite/GameData/WeaponData/CharacterWeaponSettingsPrototypes/PlayerWeaponSettingsPrototypes.cfg · .../NPCWeaponSettingsPrototypes.cfg · .../ItemPrototypes/WeaponPrototypes.cfg · .../ItemPrototypes/ArmorPrototypes.cfg · .../WeaponData/WeaponGeneralSetupPrototypes.cfg · https://www.stalker2mod.com/no-weapon-and-optionally-outfits-durability-loss/ · https://www.nexusmods.com/stalker2heartofchornobyl/mods/1695

### 1.12 Mutant health × multiplier (slider)

**There is no global mutant-HP difficulty key** (no `Mutant_HP` in DifficultyPrototypes.cfg as of 1.1.3 — directly verified) → must patch **per mutant prototype**.

| | |
|---|---|
| **Files** | `ObjPrototypes/` folder: `BlindDog.cfg, Bloodsucker.cfg, Boar.cfg, Burer.cfg, Cat.cfg, Chimera.cfg, Controller.cfg, Deer.cfg, Flesh.cfg, Poltergeist.cfg, PseudoDog.cfg, Pseudogiant.cfg, Snork.cfg, Tushkan.cfg, MutantBase.cfg` (Rat lives inside MutantBase.cfg). Each begins e.g. `Bloodsucker : struct.begin {refurl=MutantBase.cfg;refkey=[0]}`; MutantBase: `MutantBase : struct.begin {refurl=../ObjPrototypes.cfg;refkey=[0]}` |
| **Key** | `VitalParams : struct.begin ... MaxHP = <n> ... struct.end` |
| **Struct names** | Bloodsucker.cfg: Bloodsucker, MistBloodsucker, Bloodsucker_Collar; BlindDog.cfg: Blinddog, Blinddog_Collar; Snork.cfg: Snork, Snork_Collar; Controller.cfg: Controller, Controller_Collar; Burer.cfg: Burer, Burer_ShootingSpecial; Pseudogiant.cfg: Pseudogiant, Pseudogiant_Collar; Poltergeist.cfg: Poltergeist, Poltergeist_Electro/_Toxic/_Fire/_YanivToxicRozliv/_Explosives; Cat.cfg: Bayun, Bayun_Collar, Bayun_Collar_Clone; PseudoDog.cfg: PseudoDogBase, PseudoDog, PseudoDogCombatSummon, PseudoDogRetreatSummon; Boar.cfg: Boar; Flesh.cfg: Flesh; Chimera.cfg: Chimera; Deer.cfg: Deer; Tushkan.cfg: Tushkan |
| **Vanilla MaxHP (v1.1.3)** | Tushkan 19, Blinddog 63, Rat 60, Snork 150, Boar 220, Flesh 280, MutantBase default 300, PseudoDogBase 300, Burer 400, Poltergeist 400, Bayun 400, Controller 500, Bloodsucker 500, Deer 600, MistBloodsucker 1000, Chimera 2500, Pseudogiant 4000; summons/clones 5. Bloodsucker also `RegenHP = 2` with `RegenHPDelayTimeSeconds = 30.f`; MutantBase default `RegenHP = 0.05` |
| **⚠ Contradiction** | Mod 1748 (Mutant HP Overhaul) lists vanilla Chimera **1400** and Pseudogiant **2500** (matching 1.1.3 elsewhere) → GSC likely nerfed both between 1.1.3 and ~1.6. Launch 1.0 values were also higher (Boar 270, Flesh 360, Controller 650, Burer 500; official 1.0.1 nerf). **Resolution: read current values from the user's install at build time; never hardcode** |
| **Edit strategy** | bpatch one file per mutant cfg (`ObjPrototypes/<Mutant>/<Mutant>_patch_<Mod>.cfg` per sdwvit convention — note base cfgs already live inside `ObjPrototypes/`, so patches go in e.g. `ObjPrototypes/Bloodsucker/Bloodsucker_patch_<Mod>.cfg`): `<Struct> : struct.begin {bpatch} / VitalParams : struct.begin {bpatch} / MaxHP = <vanilla × slider> / struct.end / struct.end`. Optionally exclude `_Collar`/summon variants. Note `Protection.Strike` (MutantBase/Flesh/Blinddog/Tushkan 1.0, Bloodsucker 2.f, Snork/Poltergeist/PseudoDogBase/Bayun/Deer 3.0, Controller/Burer/Pseudogiant/Chimera 4.0) is the other "bullet sponge" factor some mods lower instead |
| **Confidence** | High on mechanism; low on current absolute values |

Sources: https://github.com/chrisvblemos/stalker2cfg · https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/ObjPrototypes/MutantBase.cfg · .../Bloodsucker.cfg · https://github.com/joe-p/Stalker-2-Mutant-Health-Reduction · https://www.nexusmods.com/stalker2heartofchornobyl/mods/23 · /mods/41 · /mods/1748 · https://www.stalker2mod.com/mutant-hp-overhaul-v1-0/ · https://support.stalker2.com/hc/en-us/articles/32829217590929-Patch-1-0-1-here-is-the-patchnote

### 1.13 Mutant damage × multiplier (slider)

**Recommended route — single global key:** `DifficultyPrototypes.cfg` → `Mutant_BaseDamage` per difficulty struct, multiplier on mutant damage vs player. Vanilla: 1.1.3-era — Easy 0.55 (one agent read 0.5), Medium 1.0, Hard 1.35; Jan-2026 dump — Easy 0.35, Hard 1.35, Stalker 1.5. ⚠ drift again — read live values, multiply, bpatch every difficulty struct. Companion `Mutant_AttackCooldown` scales attack frequency.

**Alternative per-attack route:** `AbilityPrototypes/<Mutant>Abilities.cfg` (BlindDog, Bloodsucker, Boar, Burer, Cat, Chimera, Controller, Deer, Flesh, Poltergeist, PseudoDog, Pseudogiant, Snork, Tushkan + Faust/Korshunov/Strelok/Human), key `Damage` per attack struct (siblings: `ArmorDamage`, `ArmorPiercing`, `Bleeding`, `BleedingChanceIncrement`, `DamageSource`, `DamageType`, `NPCDamageMultiplier`, `HitDetectionDistance`, `MaxAttacksInSeries`). Vanilla examples (1.1.3): Bloodsucker_RunAttack_Base 23, Bloodsucker_JumpAttack 32, Bloodsucker_ClawAttack 18, Bloodsucker_TurnAttack 23 (ArmorDamage 1, ArmorPiercing 2.f, Bleeding 30.0f); Boar_RunAttack_Base 30, Boar_ClawAttack 20, Boar_TurnAttack 10, ChargeAbility_Boar 30.f; Chimera claw/run/turn 35, ShortJump 30, LongJump 45, FlyThrough 40 (ArmorPiercing 4.f). Base template `BaseAttackAbility` in `AbilityPrototypes.cfg` has `NPCDamageMultiplier = 2.f` (mutants hit human NPCs at 2× the player-facing value). Note: `MutantBase.cfg`'s `AttackParams.MeleeDamage = 60.0` / `MutantAttackParams.JumpAttack.Damage = 40.0` appear to be legacy/fallback defaults — real damage lives in the ability cfgs (medium confidence).

**Confidence:** high for the difficulty-key route. **Open:** Controller/Burer/Poltergeist psy/telekinesis damage numbers (in Abilities + EffectPrototypes) not extracted; 2.0 fixed a bug where mutant-vs-NPC damage ignored stalker armor.

Sources: https://raw.githubusercontent.com/chrisvblemos/stalker2cfg/main/Stalker2/GameLite/GameData/AbilityPrototypes.cfg · .../AbilityPrototypes/BloodsuckerAbilities.cfg · .../BoarAbilities.cfg · .../ChimeraAbilities.cfg · .../DifficultyPrototypes.cfg · https://pastebin.com/g8mP43m8 · https://www.nexusmods.com/stalker2heartofchornobyl/mods/1730

**Note on difficulty structs (applies to 1.7, 1.11, 1.13):** SID→menu mapping is Easy=Novice/Rookie (`sid_misc_newGame_difficultyNovice_STI`), Medium=Stalker (default), Hard=Veteran, `Stalker`=Master (`difficultyMaster`) — the odd extra `Stalker` struct was near-empty in 1.1.3 (NPC_HP 1.2) and became a full hardcore preset by the Jan-2026 dump. Patch **all** structs including `*_Xbox`. 2.0's "Custom Rules" mode may have added structs/keys — enumerate difficulty structs from the live dump, don't hardcode the five names.

---

## 2. Packaging pipeline

### 2.1 Build steps

1. Stage a folder (name = pak name without extension), e.g. `zzz_TweakGen_1000_P/`:
   ```
   zzz_TweakGen_1000_P/
     Stalker2/Content/GameLite/GameData/ObjPrototypes/ObjPrototypes_patch_TweakGen.cfg
     Stalker2/Content/GameLite/GameData/CoreVariables/CoreVariables_patch_TweakGen.cfg
     Stalker2/Content/GameLite/GameData/TradePrototypes/TradePrototypes_patch_TweakGen.cfg
     ... (one patch file per touched base cfg, per §0 convention)
   ```
   The in-pak path **must** include the `Content` segment.
2. Pack with **repak** (trumank, v0.2.3, released 2026-01-02, Apache-2.0/MIT, Windows x64 binary `repak_cli-x86_64-pc-windows-msvc.zip` — https://github.com/trumank/repak/releases; bundle it, licensing permits):
   `repak pack zzz_TweakGen_1000_P` → `zzz_TweakGen_1000_P.pak`.
   Defaults (from `repak_cli/src/main.rs`) are correct for STALKER 2: `--version V8B`, `--mount-point "../../../"` (relative to `Stalker2/Content/Paks/`, so `Stalker2/Content/...` resolves to game root), `--path-hash-seed 0`. Output is unencrypted/uncompressed — exactly what the game accepts for mods. Community bats (v3fish StalkerPakTool, BossPack Repak.bat) pass no flags.
   ⚠ **Contradiction flag:** one research agent reports the community-standard command as `repak pack --version V11 <folder>/ <name>_P.pak`; the packaging agent verified the widely-used bats use the **default V8B** and the game mounts it. Both apparently load; default to no version flag (V8B), keep `--version V11` as a config escape hatch. No post-2.0 failure reports for either (update was 8 days old at research time).
3. Install to `<GameInstall>\Stalker2\Content\Paks\~mods\` (create if missing; subfolders allowed). GSC officially acknowledges this path (2.0 FAQ: "For custom mods — delete Stalker2/Content/Paks/~mods").

### 2.2 Naming and load order

- Filename must end `_P` (case-insensitive). Community priority form: `modName_{number}_P.pak` — Stalker2PakCfgMergeTool parses `_(\d+)_P$` and assigns merged paks priority ≥100 in steps of 10. `z`/`zz`/`zzz` prefixes win alphabetical ordering.
- Load order: paks in `~mods` mount alphabetically A–Z, **last-loaded wins whole-file conflicts** (confidence high for alphabetical; the numeric `_N_P` override of alphabetical order is community convention, medium confidence, never officially documented). Because this tool emits uniquely-named *patch* files (not copies of base cfgs), it coexists with other mods unless they patch the same keys.
- Recommended default output: `zzz_<UserModName>_1000_P.pak`.

### 2.3 Do legacy paks still work on the current patch?

**Yes (high confidence).** As of Update 2.0/2.0.3, plain repak legacy paks in `~mods` still load; no IoStore (`.utoc/.ucas`) or retoc conversion is needed for cfg mods. Confirmed by GSC's Aug 18, 2026 FAQ (warns only about *content* incompatibility, not format), Nexus mods updated on/after Aug 20, 2026 (e.g. Shay's Living Zone v2.0.0, mod 1301), and dump maintainer hwkmod (25 Aug 2026): "There no change regarding pak/unpak in 2.0." IoStore triple-file mods (`.pak+.utoc+.ucas`, via retoc v0.1.5 `to-zen` or Zone Kit) exist for *asset* mods only — irrelevant here. The UE 5.1→5.5.4 upgrade broke cooked-asset and UE4SS mods, not cfg paks.

### 2.4 Platform install paths

| Platform | Path |
|---|---|
| Steam / GOG (identical) | `...\S.T.A.L.K.E.R. 2 Heart of Chornobyl\Stalker2\Content\Paks\~mods\` |
| Xbox Game Pass (PC) | extra `Content` level: `<XboxGames root>\...\Content\Stalker2\Content\Paks\~mods\` (detect Game Pass by a `Content` folder at install root — Stalker2PakCfgMergeTool's method; exact full path string unverified, medium confidence; reach via Xbox app > Manage > Files). User config in `%LOCALAPPDATA%\Stalker2\Saved\Config\WinGDK\` instead of `\Windows\` |
| mod.io in-game-browser mods (NOT ours) | `C:\Users\Public\mod.io\5761` and `%LOCALAPPDATA%\mod.io\5761` |
| Xbox console | mod.io Mod Browser only — out of scope |

**Install-dir autodetection:** Steam library via registry/`libraryfolders.vdf` (app 1643320); GOG registry; Game Pass via XboxGames scan; always offer manual browse. Verify by presence of `Stalker2\Content\Paks\pakchunk0-Windows.pak`.

Sources: https://www.stalker2.com/news/mods-cost-of-hope-update-2-0-faq · https://github.com/trumank/repak · https://raw.githubusercontent.com/trumank/repak/master/repak_cli/src/main.rs · https://github.com/trumank/retoc · https://www.nexusmods.com/stalker2heartofchornobyl/mods/219 · /mods/1301 · https://modding.wiki/en/stalker2heartofchornobyl/users · https://steamcommunity.com/app/1643320/discussions/0/4626981776940635843 · https://github.com/Zweite93/Stalker2PakCfgMergeTool · https://github.com/v3fish/StalkerPakTool · https://support.stalker2.com/hc/en-us/articles/50032918910097

---

## 3. Where the tool gets vanilla cfg data

**Recommendation: hybrid — extract from the user's install at first run (source of truth), with a bundled 2.0 dump as offline fallback for UI defaults.** Rationale: multiplier features (item weights, mutant HP, per-difficulty multipliers) need *current* vanilla baselines, and values demonstrably drift every patch. This is the approach of Ultimate Modpack Builder (Nexus 1591: "changes your current game files, rather than using fixed templates, ensuring compatibility with new patches") and S2ZonaConfigurator, vs SCAM's stale bundled templates.

**Extraction pipeline (first run / on game update detected):**
1. `repak unpack <install>\Stalker2\Content\Paks\pakchunk0-Windows.pak -o <cache>` — extract only `Stalker2/Content/GameLite/GameData/**` (skip the ~80k SpawnActorPrototypes files; pre-1.6 full extract was ~7 GB, 5–15 min per mod 1591).
   ⚠ **Contradiction flag (AES):** packaging agent says shipping paks are AES-encrypted, key `0x33A604DF49A07FFD4A4C919962161F5C35A134D37EFA98DB37A34F6450D7D386` (hardcoded in v3fish StalkerPakTool and Stalker2PakCfgMergeTool, dumped via AESDumpster); dumps agent cites securitronlinux ("I did not need it to extract the files") + hwkmod that no key is needed and nothing changed in 2.0. **Resolution: try without key first; on failure retry with `--aes-key 0x33A604DF...D386`.** Whether the key changed with 2.0 is unverified (no reports of a change).
2. Since patch 1.6 (2025-09-24) GameData ships as **binary `.cfg.bin`** (some entire folders packed into single `.cfg.bin`; "151k files → 117"). Convert with **joric's `bin2cfg.py`** (https://github.com/joric/stalker/blob/main/scripts/bin2cfg.py — updated for 2.0.3, "Now all data is 100% converted") or **sdwvit's `s2cfgtojson` npm package** (`Struct.fromBinary(buffer)` → `.toString()`; repo pushed 2026-08-27, includes binCfgParser — https://github.com/sdwvit/S2CfgToJSON). If the tool is .NET/C#, port or shell out to one of these; also reusable as the cfg *parser* for reading values.
3. Parse the resulting text cfgs (custom format: `Name : struct.begin {refurl=...;refkey=...}` / `struct.end`, SIDs, `[*]`/`[n]` array entries, `//` comments) to resolve inherited values (refkey chains like `[0] → TemplateGrenade → GrenadeRGD5`).

**Bundled fallback dumps (for defaults/offline):**
- **Best current:** Nexus mod 1653 "Stalker2 Config Files Dump" (author hwkmod, updated 21 Aug 2026 with the v2.0 dump, ".cfg.bin already extracted", sourced from ZoneKit) — https://www.nexusmods.com/stalker2heartofchornobyl/mods/1653. DLC configs: mod 2412 "2.02 DLC .cfg converted" (some DLC1 items missing — see risks). Older: mod 1900 (1.8.1). Nexus requires login for downloads — bundling requires permission or manual re-dump; safest is to ship values you re-dump yourself via the pipeline above.
- GitHub repos are **stale**: chrisvblemos/stalker2cfg = v1.1.3 (pushed 2024-12-29; GDK branch v1.0.1 missing SpawnActorPrototypes); RetrowaveRat/Stalker2 = ~1.7/1.8 era (pushed 2026-01-10); CnRJay/Stalker-2-Dump-Files = 404. Use only as documentation references.
- Official alternative: **Zone Kit "Lesser Zone Kit"** (~1.85 GB via Epic Games Launcher 3-dots > Options, vs ~700 GB full SDK) contains base-game text configs (no DLC) — https://zonekit-support.stalker2.com/hc/en-us/articles/39349140740369-Creating-mods-with-Mini-SDK. Not automatable for end users; not recommended as tool dependency.

**Reference implementations to study:** SCAM (github.com/v3fish/SCAMStalkerConfigurator — GUI → writes cfg to `{mod_folder}/Stalker2/Content/GameLite/GameData/ObjPrototypes/...`, runs `repak.exe pack`, outputs `z_SCAM_P.pak` into `~mods`; template-based); S2ZonaConfigurator (github.com/dmcooller/S2ZonaConfigurator — declarative JSON actions `Modify/Add/RemoveLine/RemoveStruct/AddStruct/Replace` with `path` like `DefaultConfig::RealToGameTimeCoef`, applied to freshly unpacked cfgs, packed via bundled C# NetPak lib to `~mods\ZonaBundle.pak`); Ultimate Modpack Builder (Nexus 1591); joe-p/unreal-pak-mod-manager (Rust, uses repak as a library).

---

## 4. Bullet time — verdict

**Verdict: correctly assessed as out of cfg scope. Do NOT implement in the generated pak.** The GameData cfg system has no runtime time-dilation key (only `CoreVariables.cfg` `DefaultConfig::RealToGameTimeCoef = 24`, which scales the in-game *clock*, not gameplay speed), and cfg mods cannot register hotkeys. Zone Kit supports blueprint *data* modification, not scripting. All existing slow-mo mods use UE4SS or console commands:

1. **UE4SS Lua** — "bulletTime for stalker2" (Nexus mod 10, Boilingmetal, Nov 2024): internal name `GameSpeedAdjust`; installs UE4SS to `Stalker2\Binaries\Win64`, mod in `ue4ss\Mods\GameSpeedAdjust\Scripts\main.lua`, enabled via `mods.txt` line `GameSpeedAdjust : 1`; hotkeys via `RegisterKeyBind(Key.XBUTTON_ONE/XBUTTON_TWO, ...)`; 20%/50% world speed, player speed uncompensated-slow exempted. ⚠ UE4SS broke on 2.0/UE5.5.4 — requires "RE-UE4SS Compatibility Fix for Update 2.0 (UE5.5)" (Nexus mod 2341); whether mod 10 itself runs on 2.0 is unverified.
2. **Console binds via UETools** (Nexus mod 64 — itself a pak+sig+ucas+utoc set installed to `~mods`): one-key toggle
   `UETools_BindToggle H "uetools_slomo 0.001|uetools_forceactorstimedilation bp_stalker2character_c 1000" "uetools_slomo 1|uetools_forceactorstimedilation bp_stalker2character_c 1"` (milder: `uetools_slomo 0.1` + player ×10). Player class: `BP_Stalker2Character_C`. 2.0 compatibility of UETools unverified.
3. **Focus Aim** (Nexus 1218 / mod.io / Workshop id 3574327503): hybrid UE4SS BPModLoader (`Stalker2\Content\Paks\LogicMods\FocusAim.pak/.ucas/.utoc`) + Lua; slow-mo on Hold Breath; config keys SlowRate, IgnorePlayer, AltSFX, SCSlow.

**Recommended tool behavior:** show "Bullet time" as an informational entry (not a slider) that explains it needs UE4SS/console scripting, and links mods 10, 64, 1218, 2341. Optionally offer to copy the UETools bind string to clipboard. Do not auto-install UE4SS (post-2.0 fragility, save-corruption reports, out of a cfg-tool's warranty).

Do-not-confuse: Steam Workshop "Bullet Time X" id 3268589630 is for Selaco; Nexus 2360 is projectile velocity.

Sources: https://www.nexusmods.com/stalker2heartofchornobyl/mods/10 · /mods/64 · /mods/1218 · /mods/2341 · https://vgtimes.com/games/s.t.a.l.k.e.r.-2-heart-of-chornobyl/files/77282-time-dilation.html · https://www.stalker2mod.com/focus-aim/ · https://github.com/scalespeeder/stalker-2-pc-console-common-useful-commands-list/blob/main/readme.txt

---

## 5. Risks

1. **Game patches change cfg content/format.** Values provably drift (Weapon_BaseDamage Easy 1.2→1.3; Mutant_BaseDamage Easy 0.5/0.55→0.35; mutant HP nerfs at 1.0.1 and later; Master preset overhaul). Format changed at 1.6 (`.cfg.bin`) and 2.0 (folder-packed bins, UE 5.5.4). Mitigations: extract-at-build-time (§3); bpatch output (unlisted keys keep new vanilla values automatically); re-run tool after each patch; GSC officially recommends disabling mods across major updates.
2. **`{bpatch}` unknowns:** deep-nested and `[*]`-array patching not covered by official examples (open question) — features 1.3 blocking-tags and 1.9 TradeGenerators need in-game verification; fall back to same-SID full-struct override where bpatch fails. Multi-mod patch ordering on the same base cfg is undocumented.
3. **Mod conflicts:** whole-file-replacement mods (most pre-1.6 mods) clobber any base cfg they ship regardless of our patches' correctness if they also carry stale copies of files we patch — actually our uniquely-named patch files always load *in addition*, but a replacement mod swaps the *base* the patch applies to. Two patch mods editing the same key: undocumented winner. Ship high load priority (`zzz_..._1000_P`) and document. Zweite93/Stalker2PakCfgMergeTool exists for whole-file conflicts but predates cfg.bin (last push 2024-12-30).
4. **Steam vs Game Pass:** extra `Content` path level, `WinGDK` config dir, unverified exact path string, possible `-WinGDK` pak suffixes (unverified). GOG = Steam. mod.io/Workshop mods live elsewhere and may conflict invisibly.
5. **2.0 "Custom Rules" difficulty** overlaps DifficultyPrototypes multipliers (mutant survivability, people, economy) — unknown precedence vs mod patches; may also have added structs/keys.
6. **DLC content:** "Cost of Hope" DLC cfgs (`Stalker2/Content/GameLite/DLCGameData/`) are partly unextractable `.cfg.bin` (new artifacts missing from all dumps and the SDK) — DLC items may escape the item-weight slider.
7. **Save-baked state:** BaseDurability-style per-item edits only affect newly spawned items; durability sliders should default to the DifficultyPrototypes route. GSC warns pre-2.0 mods "may cause game instability"; advise users to keep backup saves.
8. **AES key / pak version uncertainty post-2.0** (see contradiction list) — implement both fallbacks.

---

## 6. Explicit contradiction register

| # | Topic | Agent A | Agent B | Resolution |
|---|---|---|---|---|
| 1 | AES on pakchunk0 | Encrypted; key `0x33A604DF49A07FFD4A4C919962161F5C35A134D37EFA98DB37A34F6450D7D386` required | Unencrypted; "did not need it"; "no change in 2.0" | Try keyless, retry with key |
| 2 | repak pack version | Defaults (V8B), no flags — verified in community bats + repak source | "community-standard `--version V11`" | Default V8B; V11 config fallback |
| 3 | Chimera/Pseudogiant MaxHP | 2500/4000 (1.1.3 raw dump) | 1400/2500 (mod 1748 page) | Patch drift; read live values |
| 4 | Weapon_BaseDamage Easy | 1.2 (1.1.3) | 1.3 (Jan-2026 dump) | Drift; read live |
| 5 | Mutant_BaseDamage Easy | 0.5 (agent 2) / 0.55 (agent 6) | 0.35 (Jan-2026 dump, agent 5) | Drift + read discrepancy; read live |
| 6 | BaseRepairCostModifier launch value | 1.0 at launch (low-conf web claim) | 0.7 in 1.1.3 dump (verified) | Use 0.7 |
| 7 | Patch-file naming | Official: `Base.cfg_patch_x` beside base file | Proven mods: `Base/Base_patch_x.cfg` subfolder | Use subfolder convention (works with binarized folders) |
| 8 | `refurl` vs `ref=` | modding.wiki one example `ref=` | vanilla + article 138 `refurl=` | Use `refurl=` (typo) |
| 9 | Dump paths | FModel dumps: `Stalker2/GameLite/GameData` | mod paks: `Stalker2/Content/GameLite/GameData` | Always include `Content` in pak |

---

## 7. Suggested GUI → patch-file mapping (build matrix)

| Control | Type | Patch files emitted |
|---|---|---|
| Item weight % | slider 0–100% | `ItemPrototypes/ItemPrototypes_patch_*.cfg` + one per `ItemPrototypes/<Category>/<Category>_patch_*.cfg` |
| Max carry weight | slider kg | `ObjWeightParamsPrototypes/...`, `CoreVariables/...`, `ObjEffectMaxParamsPrototypes/...` |
| Overweight penalty % | slider | `EffectPrototypes/...` (+ optional `ObjPrototypes/...`) |
| Max stamina | slider | `ObjPrototypes/ObjPrototypes_patch_*.cfg` (Player.VitalParams.MaxSP) |
| Stamina costs % | slider | `ObjPrototypes/...` (StaminaPerAction) + `CoreVariables/...` (StaminaRegenStateCoefs) |
| Max health | slider | `ObjPrototypes/...` (Player.VitalParams.MaxHP) |
| Player damage × | slider | `DifficultyPrototypes/DifficultyPrototypes_patch_*.cfg` (Weapon_BaseDamage, all structs) |
| No fall damage | checkbox | `ObjPrototypes/...` (Player.Protection.Fall = 100) |
| Traders buy broken gear | checkbox | `TradePrototypes/TradePrototypes_patch_*.cfg` (all traders → \*SellMinDurability = 0.0f) |
| Repair cost × | slider | `CoreVariables/...` (BaseRepairCostModifier) |
| Durability × | slider | `DifficultyPrototypes/...` (Weapon_DurabilityDamage ÷N, Armor_Durability ×N, Weapon_Durability ×N) |
| Mutant HP × | slider | per-mutant `ObjPrototypes/<Mutant>/<Mutant>_patch_*.cfg` (VitalParams.MaxHP) |
| Mutant damage × | slider | `DifficultyPrototypes/...` (Mutant_BaseDamage, all structs) |
| Bullet time | info panel only | none (links to UE4SS/UETools per §4) |

All patch files for one build merge into one `zzz_<Name>_1000_P.pak` → `~mods`. Multiple base cfgs can each receive exactly one patch file per build; regenerating overwrites the previous pak (stable filename = clean upgrade path).