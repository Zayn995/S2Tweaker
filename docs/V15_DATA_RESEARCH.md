# Mutant attack ability Damage values (AbilityPrototypes.cfg), InvisibilityFeatureData prototypes (ObjPrototypes.cfg), mutant hearing sensor SID (HearingSensorPrototypes.cfg)

## 1. Mutant attack abilities with `Damage` — AbilityPrototypes.cfg

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/AbilityPrototypes.cfg` (11421 lines).

**Key placement:** `Damage` and `ArmorPiercing` sit at the **top level of each named ability struct** (path `<AbilityStructName>.Damage`), with ONE exception: the four `ChargeAbility_*` structs nest them under a `DamageParams` sub-struct (path `ChargeAbility_X.DamageParams.Damage`). `ArmorDamage`, `Bleeding`, `BleedingChanceIncrement`, `DamageSource` sit next to `Damage` at the same level. Struct headers look like `Bloodsucker_ClawAttack : struct.begin {refurl=../AbilityPrototypes.cfg;refkey=[0]}` (base = `BaseAttackAbility`, the file's first struct, which itself has `Damage = 0`, `ArmorPiercing = 0.f`). `_Left`/`_Right` run-attack variants inherit via `{refkey=<Base>}` but **each redefines Damage locally**, so every struct must be patched individually.

### Complete mapping (Damage / ArmorPiercing, vanilla)

**Bloodsucker** (`Bloodsucker_`):
| Struct | Damage | ArmorPiercing |
|---|---|---|
| Bloodsucker_RunAttack_Base | 23 | 2.f |
| Bloodsucker_RunAttack_Left | 23 | 2.f |
| Bloodsucker_RunAttack_Right | 23 | 2.f |
| Bloodsucker_JumpAttack | 32 | 2.f |
| Bloodsucker_ClawAttack | 18 | 2.f |
| Bloodsucker_TurnAttack | 23 | 2.f |
| Bloodsucker_PhantomAttack | 0 | 0 |
| Bloodsucker_SpawnAnomaly | 0 | 0.f |
| RoarAbility (bloodsucker roar, generic name!) | 0 | 0.f |

**AshyBloodsucker** (`AshyBloodsucker_`): RunAttack_Base 23/2.f, RunAttack_Left 23/2.f, RunAttack_Right 23/2.f, JumpAttack 32/2.f, ClawAttack 18/2.f, TurnAttack 23/2.f, RoarAbility 0/0.f.

**MistBloodsucker** (`MistBloodsucker_`): RunAttack_Base 23/2.f, RunAttack_Left 23/2.f, RunAttack_Right 23/2.f, JumpAttack 32/2.f, ClawAttack 18/2.f.

**PrologueBloodsucker** (`PrologueBloodsucker_`): RunAttack_Base 23/2.f, RunAttack_Left 23/2.f, RunAttack_Right 23/2.f, JumpAttack 32/2.f, ClawAttack 18/2.f, TurnAttack 23/2.f, RoarAbility_PrologueBloodsucker 0/0.f.

**Boar** (`Boar_`):
| Struct | Damage | ArmorPiercing |
|---|---|---|
| Boar_RunAttack_Base | 30 | 1.f |
| Boar_RunAttack_Left | 30 | 1.f |
| Boar_RunAttack_Right | 30 | 1.f |
| Boar_ClawAttack | 20 | 1.f |
| Boar_TurnAttack | 10 | 1.f |
| ChargeAbility_Boar (**nested**: `DamageParams.Damage`) | 30.f | 1.f (also `ArmorDamage = 3.f`, `bShouldIgnoreArmor = false`, `DamageType = EDamageType::Strike` inside DamageParams) |
| Boar_PhantomAttack | 10.f | 0 |

**HelmedBoar** (`HelmedBoar_`): RunAttack_Base 30/1.f, RunAttack_Left 30/1.f, RunAttack_Right 30/1.f, ClawAttack 20/1.f, TurnAttack 10/1.f, ChargeAbility_HelmedBoar `DamageParams.Damage = 30.f` / AP 1.f. (HelmedBoar_GruntAbility has no Damage.)

**PorcupineBoar** (`PorcupineBoar_`): RunAttack_Base 30/1.f, RunAttack_Left 30/1.f, RunAttack_Right 30/1.f, ClawAttack 20/1.f, TurnAttack 10/1.f, ChargeAbility_PorcupineBoar `DamageParams.Damage = 30.f` / AP 1.f.

**Flesh** (`Flesh_`): Flesh_JumpAttack 20/1.f, Flesh_ClawAttack 10/1.f, Flesh_TurnAttack 20/1.f, Flesh_PhantomAttack 10.f/0.
**BoggyFlesh** (`BoggyFlesh_`): JumpAttack 20/1.f, ClawAttack 10/1.f, TurnAttack 20/1.f.

**PseudoDog** (`PseudoDog_`): RunAttack_Base 10/3.f, RunAttack_Left 10/3.f, RunAttack_Right 10/3.f, BiteAttack 10/3.f, TurnAttack 10/3.f.
**PseudoDogSummon** (phantom pack, `PseudoDogSummon_`): RunAttack_Base 5/3, RunAttack_Left 5/3, RunAttack_Right 5/3, BiteAttack 5/3, TurnAttack 5/3.f.

**BlindDog** (`BlindDog_`): RunAttack_Base 5/1.f, RunAttack_Left 5/1.f, RunAttack_Right 5/1.f, BiteAttack 10/1.f, BiteAttackAnyAngle 10/1.f, TurnAttack 5/1.f, TurnAttackAnyAngle 5/1.f, PhantomAttack 0/0, BlindDog_Shield 0/0.f.
**MoldyBlindDog** (`MoldyBlindDog_`): RunAttack_Base 30/1.f, RunAttack_Left 30/1.f, RunAttack_Right 30/1.f, BiteAttack 20/1.f, BiteAttackAnyAngle 20/1.f, TurnAttack 15/1.f, TurnAttackAnyAngle 15/1.f.

**Snork** (`Snork_`): ClawAttack 15/3.f, KickAttack 15/3.f, JumpAttack 25/3.f, Snork_Collar_JumpAttack 25/3.f, TurnAttack 15/3.f, FlyThrough 20/3.f. (Zero-damage utility: Snork_Jump, Snork_EscapeIsolatedNavmesh, Snork_JumpToEnemy, Snork_Evasion — all Damage 0.)

**Controller** (`Controller_`): Controller_ClawAttack 30/**4** (integer, no `.f`). Zero-damage: Controller_PSYStrike 0/0.f, Controller_RoarAbility 0/0.f, Controller_RaiseDeadBody 0/0.f, Controller_ZombifyNPC 0/0.f. (Controller_Collar_PSYAttack `{refkey=Controller_PSYStrike}` and Controller_PSYAura define no local Damage.)

**Burer** (`Burer_`): Burer_ClawAttack 30/**4** (integer). Zero-damage: Burer_Shield, Burer_Throw, Burer_ThrowQueue_Grenades, Burer_WeaponDrag, Burer_WeaponRiseAndShoot, Burer_WeaponRiseAndShoot_ShootingSpecial, Burer_WeaponDrag_ShootingSpecial — all Damage 0/AP 0.f.

**Poltergeist** (`Poltergeist_`): ALL Damage = 0 (damage comes from anomalies/thrown props): Poltergeist_Shield, Poltergeist_AOEPassiveAttack, Poltergeist_Electro_AOEPassiveAttack, Poltergeist_Toxic_AOEPassiveAttack, Poltergeist_Fire_AOEPassiveAttack, Poltergeist_ActivateAnomaly (+Fire/Electro/ToxicCloud/_YanivToxicRozmiv variants), Poltergeist_ThrowBase, Poltergeist_Throw, Poltergeist_ThrowExplosivesOnly. No direct-damage slider possible here.

**Pseudogiant** (`Pseudogiant_`): ClawAttack 40/3.f, RunAttack_Base 40/3.f, RunAttack_Right 40/3.f, RunAttack_Left 40/3.f, ShockwaveAttack **45.f**/3.f, TurnAttack 35/3.f, ChargeAbility_Pseudogiant `DamageParams.Damage = 45.f` / AP 3.f, Pseudogiant_Throw 0/0.f.

**Chimera** (`Chimera_`): ClawAttack 35/4.f, RunAttack_Base 35/4.f, RunAttack_Left 35/4.f, RunAttack_Right 35/4.f, TurnAttack 35/4.f, ShortJumpAttack 30/4.f, LongJumpAttack 45/4.f, FlyThrough 40/4.f. Zero-damage: Chimera_Jump, Chimera_EscapeIsolatedNavmesh, Chimera_JumpToEnemy, Chimera_Evasion.

**Deer** (`Deer_`): JumpAttack 30/3.f, ClawAttack 30/3.f, TurnAttack 20/3.f, ChargeAbility_Deer `DamageParams.Damage = 45.f` / AP 3.f. (RoarAbility_Deer has no Damage.)

**Tushkan** (`Tushkan_`): JumpAttack 4/2.f, ClawAttack **`4f`**/**`2.0f`** (unusual literals, exactly as written), PhantomAttack 10.f/0.

**Bayun/Cat** — ability prefix is `Cat_` (lore name Bayun appears only in `TrickSound*_Bayun_E10_MQ01` quest sound structs): Cat_ClawAttack 10/3.f, Cat_JumpAttack 24/3.f, Cat_TurnAttack 10/3.f, Cat_FlyThrough 15/3.f. Zero-damage: Cat_Jump, Cat_EscapeIsolatedNavmesh, Cat_JumpToEnemy, Cat_Evasion. (Cat_BlinkTeleport, Cat_SleepinessAura: no Damage.)

**Rat**: **NO ability structs exist** in AbilityPrototypes.cfg (verified: zero `Rat*` struct headers and zero SIDs containing "Rat"). A `Rat` ObjPrototype exists (ObjPrototypes.cfg line 1307755, `{refurl=./MutantBase.cfg;refkey=[0]}`) but its damage is not defined in this file.

## 2. InvisibilityFeatureData — ObjPrototypes.cfg

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/ObjPrototypes.cfg`. Exactly **5 prototypes** define it, always as a struct at the top level of the mutant prototype (path `<Prototype>.InvisibilityFeatureData.<Key>`):

| Prototype (line) | ToVisibleSeconds | ToInvisibleSeconds | InvisibilityDeadChangeDurationSeconds | InvisibilityLossFromDamage | InvisibilityEffectsThreshold |
|---|---|---|---|---|---|
| AshyBloodsucker (L1716) | 0.4f | **0.8f** | 10.f | 0.01f | 0.75f |
| Bloodsucker (L4411) | 0.4f | 1.8f | 10.f | 0.01f | 0.75f |
| MistBloodsucker (L5294) | 0.4f | 1.8f | 10.f | 0.01f | 0.75f |
| Bloodsucker_Collar (L5813) | 0.4f | 1.8f | 10.f | 0.01f | 0.75f |
| PrologueBloodsucker (L205699) | 0.4f | 1.8f | 10.f | 0.01f | 0.75f |

All five also contain a nested `InvisibilityEffects : struct.begin` → `[0] : struct.begin` → `EffectPrototypeSID = ProtectionStrike1`, `Chance = 1.0`. `Bloodsucker_Collar` additionally has `EnterInvisibilityAbility = Abilities.SpawnAnomaly` as the last key inside InvisibilityFeatureData. Exact block shape (Bloodsucker, L4411-4423):
```
   InvisibilityFeatureData : struct.begin
      ToVisibleSeconds = 0.4f
      ToInvisibleSeconds = 1.8f
      InvisibilityDeadChangeDurationSeconds = 10.f
      InvisibilityLossFromDamage = 0.01f
      InvisibilityEffectsThreshold = 0.75f
      InvisibilityEffects : struct.begin
         [0] : struct.begin
            EffectPrototypeSID = ProtectionStrike1
            Chance = 1.0
         struct.end
      struct.end
   struct.end
```
Prototype headers: `Bloodsucker : struct.begin {refurl=MutantBase.cfg;refkey=[0]}`, `AshyBloodsucker : struct.begin {refurl=MutantBase.cfg;refkey=[0]}`, `MistBloodsucker : struct.begin {refkey=[0]}`, `Bloodsucker_Collar : struct.begin {refkey=Bloodsucker}`, `PrologueBloodsucker : struct.begin {refurl=MutantBase.cfg;refkey=[0]}`.

## 3. Mutant hearing sensor — AIPrototypes/HearingSensorPrototypes.cfg

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/AIPrototypes/HearingSensorPrototypes.cfg` (423 lines, 6 top-level structs: BaseHearingSensor, DefaultNPC, ZombieHuman, MutantsHearingSensor, Default, HumanFWHearingSensor).

Shared mutant sensor: struct name **`MutantsHearingSensor`** (line 213), header `MutantsHearingSensor : struct.begin {refkey=DefaultNPC}`, keys: `SID = MutantsHearingSensor`, `HearingVolumeThreshold = 6.0`, `ID = 1` (last key, after SoundEvents). SoundEvents is an indexed array `SoundEvents : struct.begin` → `[N] : struct.begin` with keys `Type = ESoundEventType::<X>` and `HearingDistance = <val>`; patch path form: `MutantsHearingSensor.SoundEvents.[N].HearingDistance`.

MutantsHearingSensor vanilla SoundEvents (index: Type = HearingDistance):
- [0] Shot = 10000.f
- [1] Reload = 600.f
- [2] Steps = 2400.f
- [3] Jump = 1500.f
- [4] Voice = 6000.f
- [5] AnomalyActivated = 0.f
- [6] Explosion = 10000.f
- [7] BulletFlyby = 300.f
- [8] PhysObjectImpact = 1500.f
- [9] Interactable = 0.f
- [10] DoorKnockedOut = 2000.f
- [11] Bolt = 2500.f
- [12] StealthKill = 1000.f
- [13] BulletHit = 600.f
- [14] GrenadeHit = 2000.f
- [15] Guitar = 3000.f

(For contrast, DefaultNPC/BaseHearingSensor/Default: Shot 4600.f, Steps 1200.f, Voice 3000.f, Explosion 6000.f, Bolt 2500.f, StealthKill 500.f; ZombieHuman: Shot 3500.f, Steps 600.f, HearingVolumeThreshold 4.0.)

WARNUNGEN:
- Rat has NO ability structs in AbilityPrototypes.cfg — a Rat damage slider cannot be built from this file (Rat ObjPrototype is at ObjPrototypes.cfg L1307755). Rat damage is likely handled elsewhere (e.g. swarm mechanics).
- The Bloodsucker roar struct is named plain 'RoarAbility' (no Bloodsucker_ prefix) — a naive 'Bloodsucker_' prefix filter misses it; conversely 'RoarAbility' also prefixes 'RoarAbility_PrologueBloodsucker' and 'RoarAbility_Deer'.
- AbilityPrototypes.cfg also contains human/boss abilities with Damage (Human_MeleeAttack 25.f, Human_MeleeAttack_Agent 25.f, Human_PhantomAttack 10.f, Strelok_MeleeAttack 30.f, Korshunov_MeleeAttack 25.f, Korshunov_JumpAttack 30) — mutant patches must not touch these; match struct names exactly.
- ChargeAbility_Boar/HelmedBoar/PorcupineBoar/Deer/Pseudogiant use the NESTED path DamageParams.Damage, unlike all other attacks where Damage is top-level in the ability struct — the patch generator must handle both shapes.
- Value literal styles are inconsistent (integer '23', float '45.f', and Tushkan_ClawAttack's '4f' / '2.0f'). Controller_ClawAttack and Burer_ClawAttack have integer ArmorPiercing '4' while most others use 'N.f'. Keep the game's parser tolerance in mind when writing patched values.
- _Left/_Right run-attack variants inherit via refkey from their _Base struct but redefine Damage locally — scaling only the _Base struct will NOT propagate; patch every variant.
- All Poltergeist abilities have Damage = 0 (damage comes from activated anomalies/thrown objects) — a Poltergeist melee-damage slider would be a no-op.
- MutantsHearingSensor inherits {refkey=DefaultNPC} and redefines all 16 SoundEvents locally; note it carries 'ID = 1' which duplicates DefaultNPC's ID = 1 — do not touch ID when patching.
- Controller_Collar_PSYAttack defines no local Damage (inherits from Controller_PSYStrike, which is 0 anyway); Snork_Collar_JumpAttack DOES define local Damage 25.
- InvisibilityFeatureData: AshyBloodsucker's ToInvisibleSeconds (0.8f) differs from the other four (1.8f) — do not assume one shared vanilla value; Bloodsucker_Collar has the extra key EnterInvisibilityAbility = Abilities.SpawnAnomaly.

# Vanilla verification: AimingMovementSpeedModifier + MaxAmmo (WeaponGeneralSetupPrototypes.cfg), magazine attachments (ItemPrototypes.cfg), melee weapons (MeleeWeaponPrototypes.cfg)

## 1. AimingMovementSpeedModifier — WeaponGeneralSetupPrototypes.cfg

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg`

- **Position: TOP-LEVEL key directly inside each weapon struct** (3-space indent, depth 1). NOT nested in any sub-struct. Example: `TemplateWeapon : struct.begin` → line 11 `AimingMovementSpeedModifier = 1.0`.
- The file contains exactly **92 top-level structs**, and **every single one of the 92 defines both `AimingMovementSpeedModifier` and `MaxAmmo` exactly once** (verified by count: 92 structs, 92 AMSM lines, 92 MaxAmmo lines; no duplicates, no inheritance holes). So per-weapon patches are always safe, and patching only templates would have **no effect** — every concrete weapon overrides both keys itself.
- Struct inventory: 12 templates (`TemplateWeapon`, `TemplatePistol`, `TemplateSMG`, `TemplateMAC`, `TemplateRifle`, `TemplateRifleSingleFire`, `TemplateMG`, `TemplateShotgun`, `TemplateDMR`, `TemplateSniper`, `TemplateGLaunch`, `MeleeStub`), 79 concrete weapons (`Gun*` / `UA_GLaunch_Weapon_Data_Ru/En` / `EN_BuckLaunch_Data`), plus a trailing `Default : struct.begin {refkey=TemplateWeapon}`.
- **Value range: 0.58 – 1.5.** Higher = faster movement while aiming (pistols 1.38, SMGs 1.15–1.5, rifles 0.85–1.0, shotguns 0.85–1.27, DMR 0.76–0.9, snipers 0.58–1.04, MGs 0.7). Template values: TemplateWeapon 1.0, TemplatePistol 1.38, TemplateSMG 1.27, TemplateMAC 1.38, TemplateRifle 0.92, TemplateRifleSingleFire 0.92, TemplateMG 0.7, TemplateShotgun 0.925, TemplateDMR 0.9, TemplateSniper 0.9, TemplateGLaunch 1.0, MeleeStub 1.0.
- Extremes among weapons: min 0.58 (`GunSVDM_SP`, `Gun_Lynx_SR_GS`), max 1.5 (`GunFora230_PP_GS`).

## 2a. MaxAmmo — WeaponGeneralSetupPrototypes.cfg (same file)

- **TOP-LEVEL key in each of the 92 structs** (e.g. line 144 in TemplateWeapon). All 12 templates and `Default` have `MaxAmmo = 0`; all 79 concrete weapons have real values.
- Complete weapon table (struct → MaxAmmo): GunPM_HG=8, GunUDP_HG=15, GunAPB_HG=18, GunM10_HG=30, GunRhino_HG=6, GunKora_HG=7, GunViper_PP=30, GunAKU_PP=30, GunBucket_PP=20, GunIntegral_PP=20, GunZubr_PP=50, GunFora230_PP_GS=20, GunAK74_ST=30, GunAK74_Phantom_ST=30, GunAK74_Strelok_ST=30, GunM16_ST=30, GunG37_ST=30, GunFora_ST=30, GunGrim_ST=20, GunGvintar_ST=10, GunKharod_ST=30, GunLavina_ST=20, GunDnipro_ST=30, GunArev_ST_GS=30, GunPKP_MG=150, GunPKP_Korshunov_MG_GS=300, GunObrez_SG=2, GunTOZ_SG=2, GunM860_SG=6, GunSPSA_SG=8, GunD12_SG=8, GunRam2_SG=14, GunSKP_DMR_GS=10, GunGP3A_DMR_GS=20, GunMark_SP=10, GunSVDM_SP=10, GunM701_SP=5, GunSVU_SP=10, GunThreeLine_SP_GS=5, GunGauss_SP=10, GunRpg7_GL=1, UA_GLaunch_Weapon_Data_Ru=1, UA_GLaunch_Weapon_Data_En=1, EN_BuckLaunch_Data=4, GunG37V2_ST=30, GunArevPrecise_AR_GS=30, GunGonta_SP_GS=5, GunGauss_Scar_SP=99, GunNightStalker_HG=12, GunUDP_Deadeye_HG=15, Gun_Krivenko_HG_GS=15, Gun_S15_AR=20, Gun_Sharpshooter_AR_GS=30, Gun_Cavalier_SR_GS=5, Gun_Unknown_AR_GS=30, Gun_GStreet_HG_GS=40, Gun_Encourage_HG_GS=18, Gun_Star_HG_GS=8, Gun_Shakh_SMG_GS=40, Gun_RatKiller_SMG_GS=50, Gun_Silence_SMG_GS=30, Gun_Spitter_SMG_GS=20, Gun_Spitfire_SMG_GS=40, Gun_Lynx_SR_GS=10, Gun_Whip_SR_GS=10, Gun_Partner_SR_GS=10, Gun_SOFMOD_AR_GS=30, Gun_Predator_SG_GS=8, Gun_Sledgehammer_SG_GS=8, Gun_Texas_SG_GS=14, Gun_Combatant_AR_GS=30, Gun_Drowned_AR_GS=30, Gun_Lummox_AR_GS=30, Gun_Merc_AR_GS=10, Gun_Tank_MG_GS=500, Gun_Sotnyk_AR_GS=30, Gun_Trophy_AR_GS=20, Gun_Decider_AR_GS=30, Gun_Kaimanov_HG_GS=8.

## 2b. Magazine attachments — ItemPrototypes.cfg

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg`

- **Exact path: `<MagStruct> → Magazine (sub-struct) → MaxAmmo`** (i.e. `Magazine.MaxAmmo`, key at 6-space indent inside the `Magazine : struct.begin` block, which sits at depth 1 in the attachment struct). Sibling keys inside `Magazine`: `IsTwinMagazine`, `BindBulletsToAttach`, `PhysicsInteractionPrototypeSID`, `HasMultipleMeshes`, `MeshArray`.
- The file has **218 `MaxAmmo` lines total**; **137 are `= 0`** and belong to `TemplateAttach` (line 28571) and all NON-magazine attachments (scopes, silencers, rails, etc. — every attachment inherits a `Magazine` block with `MaxAmmo = 0` from TemplateAttach) plus the 4 magazine templates. **Only 81 are non-zero — exactly the 81 concrete magazine attachment structs** (region lines 38694–46652).
- Templates (all with `Magazine.MaxAmmo = 0`): `MagTemplate` (refkey=TemplateAttach, line 38322), `PairedMagTemplate` (refkey=MagTemplate, adds effect AimingTimeNeg10Effect), `BigMagTemplate` (adds AimingTimeNeg15Effect + AimingMovementNeg10Effect), `HugeMagTemplate` (adds AimingTimeNeg20Effect + AimingMovementNeg10Effect).
- **81 concrete magazines** (struct → Magazine.MaxAmmo; * = IsTwinMagazine=true): GunPM_MagDefault=8, GunPM_MagIncreased=12, GunUDP_MagDefault=15, GunUDP_MagIncreased=20, GunM10_MagDefault=30, GunM10_MagIncreased=40, Gun_GStreet_MagIncreased=40, GunAPB_MagDefault=18, GunAPB_MagIncreased=30, GunKora_MagDefault=7, GunKora_MagIncreased=10, GunNightStalker_MagIncreased=12, GunViper_MagDefault=30, GunViper_MagIncreased=40, Gun_Shakh_MagIncreased=40, GunAKU_MagDefault=30, GunAKU_Silence_MagDefault=30, GunSpitfire_MagDefault=40, GunAK_MagPaired=30*, GunDrowned_MagPaired=30*, GunBucket_MagDefault=20, GunBucket_MagIncreased=30, GunIntegral_MagDefault=20, GunIntegral_MagIncreased=30, GunZubr_MagDefault=50, Gun_RatKiller_MagDefault=50, GunZubr_MagIncreased=64, GunAK74_MagDefault=30, GunAK74_MagIncreased=45, GunSotnyk_MagDefault=30, GunM16_MagDefault=30, GunM16_MagIncreased=50, GunGP37_MagDefault=30, GunGP37_MagPaired=30*, GunG37V2_MagPaired=30*, GunGP37_MagLarge=90, GunFora_MagDefault=30, GunDecider_MagDefault=30, GunNovator_MagDefault=30, GunFora_MagIncreased=40, GunGrim_MagDefault=20, GunS15_MagDefault=20, GunGrim_MagIncreased=30, GunGrim_MagLarge=45, GunGvintar_MagDefault=10, GunGvintar_MagIncreased=20, GunKharod_MagDefault=30, GunKharod_MagPaired=30*, GunLavina_MagDefault=20, GunLavina_MagIncreased=30, GunDnipro_MagDefault=30, GunDnipro_MagPaired=30*, GunArev_MagDefault=30, GunArevPrecise_MagDefault=30, GunPKP_MagDefault=150, GunPKP_MagIncreased=250, GunPKP_MagLarge=350, GunTank_MagLarge=500, GunPKP_Korshunov_MagLarge=350, GunM860_MagLarge=10, GunD12_MagDefault=8, GunD12_MagIncreased=12, GunD12_MagPaired=8*, GunD12_MagLarge=20, GunSVDM_MagDefault=10, GunM701_MagDefault=5, GunMark_MagDefault=10, GunMark_MagIncreased=20, GunSVU_MagDefault=10, GunSVU_MagIncreased=20, GunSKP_MagDefault=10, GunSKP_MagIncreased=20, GunGP3A_MagDefault=20, GunGP3A_MagIncreased=30, GunGP3A_MagLarge=50, GunGauss_MagDefault=10, GunGauss_MagIncreased=20, GunGauss_Scar_MagHuge=99, GunFora230_MagDefault=20, GunFora230_MagIncreased=40.
- Weapon-level MaxAmmo matches the corresponding `*_MagDefault` value in every case where a default mag exists (PM 8=8, UDP 15=15, Zubr 50=50, PKP 150=150, D12 8=8, etc.). Weapons WITHOUT any mag attachment (tube/break shotguns GunObrez_SG, GunTOZ_SG, GunSPSA_SG, GunRam2_SG plus RPG/GLaunch) are governed solely by the weapon-level MaxAmmo. GunM860_SG (weapon MaxAmmo=6) only has the optional `GunM860_MagLarge=10` extension.

## 3. MeleeWeaponPrototypes.cfg — complete listing

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/MeleeWeaponPrototypes.cfg` (66 lines, only 3 structs):

1. **`Empty`** (line 1): stub — only `SID`, empty `DamageModifiers =`, empty `ImpulseModifiers =`. Nothing to scale.
2. **`Knife`** (line 6, refkey=Empty), all keys top-level, float values written with `.f` suffix:
   - `Damage = 51.f`
   - `ArmorDamage = 0.f`, `ArmorPiercing = 0.f`, `ShouldIgnoreArmor = false`
   - `Bleeding = 50.f`, `BleedingChanceIncrement = 50.f`
   - `ImpulseStrength = 500.f`
   - `HitDetectionDistance = 160.f`, `HitDetectionAngle = 45.f`, `HitDetectionRadius = 5.f`
   - `DamageModifiers : struct.begin` → `HandOccupied = 1.0`, `StrongAttack = 1.77`
   - `ImpulseModifiers : struct.begin` → `HandOccupied = 1.0`, `StrongAttack = 1.0`
3. **`WeaponButt`** (line 31, refkey=Knife) — the gun-butt melee strike:
   - `Damage = 30.f`, `ArmorDamage = 0.f`, `ArmorPiercing = 0.f`, `Bleeding = 0.f`, `BleedingChanceIncrement = 0.f`, `ShouldIgnoreArmor = false`, `ImpulseStrength = 500.f`
   - `HitDetectionDistance = 160.f`, `HitDetectionAngle = 45.f`, `HitDetectionRadius = 10.f`
   - Same `DamageModifiers` (HandOccupied 1.0, StrongAttack 1.77) and `ImpulseModifiers` (both 1.0)
   - Extra: `TargetEffects[0].EffectPrototypeSID = ButtStroke_CameraShake` (Chance 1.f), `SourceEffects[0].EffectPrototypeSID = ButtStroke_Corrosion` (Chance 1.f)

Scalable melee keys: `Damage`, `Bleeding`, `BleedingChanceIncrement`, `ImpulseStrength`, `HitDetectionDistance/Angle/Radius`, `DamageModifiers.StrongAttack`. `ArmorDamage`/`ArmorPiercing` exist but are 0.f vanilla (multiplicative scaling is a no-op; only additive/absolute override would do anything). `ShouldIgnoreArmor` is a bool toggle candidate.

WARNUNGEN:
- Templates are dead ends for these two weapon keys: every one of the 92 structs in WeaponGeneralSetupPrototypes.cfg (templates AND weapons) defines AimingMovementSpeedModifier and MaxAmmo itself, so patching TemplateWeapon/TemplatePistol etc. changes nothing on concrete weapons — patch the concrete Gun* structs.
- Zero values: all 12 templates plus the 'Default' struct have MaxAmmo = 0, and 137 of 218 MaxAmmo lines in ItemPrototypes.cfg are 0 (TemplateAttach + every non-magazine attachment inherits a Magazine block with MaxAmmo = 0). Multiplicative scaling of these is a no-op; never emit patches for them (matches the _neq rule) and never round a scaled 0 up.
- Effective in-game magazine capacity for mag-fed weapons comes from the installed magazine attachment (ItemPrototypes.cfg Magazine.MaxAmmo); the weapon-level MaxAmmo in WeaponGeneralSetupPrototypes.cfg is the no-attachment/base value. To scale magazine size consistently you must patch BOTH: the 79 weapon structs' top-level MaxAmmo and the 81 mag attachments' Magazine.MaxAmmo (nested one level: Magazine → MaxAmmo).
- Shared/derived mag structs: several mags are refkeyed to another concrete mag (Gun_GStreet_MagIncreased→GunM10_MagIncreased, GunNightStalker_MagIncreased→GunKora_MagIncreased, Gun_Shakh_MagIncreased→GunViper_MagIncreased, GunAKU_Silence_MagDefault→GunAKU_MagDefault, Gun_RatKiller_MagDefault→GunZubr_MagDefault, GunSotnyk_MagDefault→GunAK74_MagDefault, GunS15_MagDefault→GunGrim_MagDefault, GunArevPrecise_MagDefault→GunArev_MagDefault, GunTank_MagLarge/GunPKP_Korshunov_MagLarge→GunPKP_MagLarge, GunG37V2_MagPaired→GunGP37_MagPaired, GunDrowned_MagPaired→GunAK_MagPaired, GunGauss_Scar_MagHuge→GunGauss_MagIncreased). Each still defines its own Magazine.MaxAmmo, so per-struct patches are safe, but do not assume unique values.
- 7 twin magazines (IsTwinMagazine = true): GunAK_MagPaired, GunDrowned_MagPaired, GunGP37_MagPaired, GunG37V2_MagPaired, GunKharod_MagPaired, GunDnipro_MagPaired, GunD12_MagPaired. Their MaxAmmo is PER SIDE (e.g. GunD12_MagPaired = 8, same as the 8-round default); scaling them scales both mags.
- Outlier values to consider capping in the UI: Gun_Tank_MG_GS weapon MaxAmmo = 500 and GunTank_MagLarge = 500, GunPKP_Korshunov_MG_GS = 300, GunPKP_MagLarge/Korshunov_MagLarge = 350, GunGauss_Scar 99. RPG/grenade launchers have MaxAmmo = 1 — scaling with a multiplier <1 would floor to 0 (unusable); clamp minimum to 1.
- WeaponButt (gun-butt strike) inherits from Knife in MeleeWeaponPrototypes.cfg and is a separate struct — a 'melee damage' slider that patches both Knife and WeaponButt also buffs rifle-butt hits; consider exposing them separately or documenting it.
- Melee float values use the '.f' suffix in vanilla (Damage = 51.f, ImpulseStrength = 500.f) while modifier sub-struct values use plain '1.0'/'1.77'. The bpatch writer should keep emitting plain floats as usual (the game parses both), but parsers reading vanilla values must strip the trailing 'f'.
- MeleeWeaponPrototypes.cfg contains only Knife and WeaponButt — NPC mutant melee damage is NOT in this file. ArmorDamage and ArmorPiercing exist on both melee structs but are 0.f in vanilla (multiplier no-op; would need absolute values to activate).

# Anomaly damage per element type (Electro/Chemical/Fire/Gravity/PSY): AnomalyPrototypes.cfg -> EffectPrototypes.cfg mapping with vanilla values

## Files
- Anomalies: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/AnomalyPrototypes.cfg` (1224 lines)
- Effects: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/EffectPrototypes.cfg` (85868 lines)

## How anomalies reference damage
Anomaly structs carry NO direct HP-damage numbers. Each anomaly lists effect SIDs in the arrays `InteractionEffectPrototypeSIDs`, `PostInteractionEffectPrototypeSIDs`, `PassiveEffectPrototypeSIDs` (entries `[0]`, `[1]`, ...). The actual numbers live in EffectPrototypes.cfg in structs whose name = the SID, keys `ValueMin` / `ValueMax` (damage per application; effects with `bIsPermanent = true` + `TimePerChargeMin/Max = 1.f` tick as DPS). All damage effects inherit `refkey=[0]` (base struct `[0]` at top of EffectPrototypes.cfg, `ValueMin/ValueMax = 0.f`).
Special anomaly-local (non-effect) damage keys exist only for: LavaLampAnomaly `DestructibleDamage = 10.f` (objects only) and DiamondAnomaly `EquipmentDamage = 10.0` (gear only). SoapBubble `ParticlePrototype`/`BubblePrototype` `MinHP/MaxHP = 5.f` are bubble health, NOT damage.

## All anomaly prototypes (AnomalyPrototypes.cfg) with AnomalyElementType
| Struct | Element | Damage-relevant effect SIDs referenced |
|---|---|---|
| Empty (template) | None | — |
| ElectroAnomaly | Electro | Interaction: ElectroAnomaly, ElectroCorrosion |
| ElectroAnomaly_Dynamic | Electro | same as ElectroAnomaly |
| ChemicalAnomaly | Chemical | Interaction: ChemicalAnomalyVelocityChange, ChemicalAnomalyTurnRateChange, ChemicalDamage, ChemicalCorrosion |
| CarouselAnomaly | Gravity | Interaction: CarouselAnomaly, CarouselCorrosion |
| RazorAnomaly | Gravity | Interaction: RazorAnomalyDamageDPSLow, RazorAnomalyLowBleed, RazorAnomalyDamageDPSHigh, RazorAnomalyHighBleed, RazorAnomalyCorrosionDPS |
| PsyAnomaly | PSY | Interaction: PsyAnomalyIncreaseRegen |
| ClassicFireAnomaly | Fire | Interaction: FireAnomalyDPS, FireAnomalyCorrosion; Post: FireBurning; Passive: HeatBurning, BurningCorrosion |
| PillowAnomaly | Gravity | none (physics push only: CharacterPushingImpulse=500000.0, MaxPushingImpulse=100000.0, PushingForce=3000.0) |
| SpringboardAnomaly | Gravity | none (physics only: CharacterPushingImpulse=180000.0) |
| LightningBallMediumAnomaly | Electro | Interaction: ElectroAnomaly, ElectroCorrosion |
| LightningBallSmallAnomaly | Electro | same |
| LightningBallBigAnomaly | Electro | same |
| FlycatcherAnomaly | PSY | Interaction: FlycatcherSlowRegenHP, FlycatcherSlowRegenFP, FlycatcherVelocityChange, FlycatcherTurnRateChange, FlycatcherPostProcess (no direct damage) |
| SoapBubbleAnomaly | Chemical | Interaction: SoapBubbleDamage, SoapBubbleCorrosion; nested `ParticlePrototype.InteractionEffectPrototypeSIDs`: ParticleSoapBubbleDamage, ParticleSoapBubbleCorrosion |
| LavaLampAnomaly | Fire | Interaction: LavaLampAnomalyFloor, LavaLampClotCorrosion; `LavaHitEffectPrototypeSIDs`: LavaLampAnomalyHit, LavaLampAnomalyCorrosion; `LavaItemHitEffectPrototypeSIDs`: LavaLampAnomalyItemCorrosion; local `DestructibleDamage = 10.f` |
| PSYControllerAnomaly | PSY | Interaction: PsyAnomalyIncreaseRegen |
| PSYEmitterAnomaly | PSY | Interaction: PsyAnomalyIncreaseRegen |
| ExpulsionAnomaly | Gravity | Interaction: ExpulsionDamage, ExpulsionCorrosion, ExpulsionPostProcess |
| ClickerAnomaly | Fire | Interaction: ClickerAnomalyHit, ClickerCorrosion, ClickerFlasBangComposite |
| ToxicCloudAnomaly_Box | Chemical | Interaction: ToxicCloudDamage, ToxicCloudCorrosion |
| ToxicCloudAnomaly_Cylinder | Chemical | same (identical SIDs) |
| DiamondAnomaly | Gravity | Interaction: DiamondDPS, DiamondBleeding, DiamondEquipDPS; local `EquipmentDamage = 10.0` |
| LightningBallPrologueAnomaly | Electro | Interaction: ElectroAnomalyPrologue, ElectroCorrosionPrologue |
| FireBallAnomaly | Fire | Interaction: FireBallAnomaly, FireBallCorrosion |
| SteamAnomaly | Fire | Interaction: SteamAnomalyDPS, SteamAnomalyCorrosion; Post: SteamBurning; Passive: SteamHeatBurning, SteamCorrosion |
| AnomalyBase (template) | None | — |
| [1] (SID=QuestChemicalAnomaly) | Chemical | none (all effect arrays empty) |

## Effect structs in EffectPrototypes.cfg — vanilla damage values
All patch targets are `<StructName>::ValueMin` and `<StructName>::ValueMax` in EffectPrototypes.cfg (struct name = SID, top level).

### ELECTRO
| Effect struct | Type | ValueMin | ValueMax | Notes |
|---|---|---|---|---|
| ElectroAnomaly (line 1883) | EEffectType::Damage | 65.0 | 65.0 | Shock/Electricity, per hit (Duration 0, Charges 0). Used by 5 anomalies + LightningBalls |
| ElectroAnomalyPrologue (line 81961) | EEffectType::Damage | 50.0 | 50.0 | prologue LightningBall only |

### CHEMICAL
| Effect struct | Type | ValueMin | ValueMax | Notes |
|---|---|---|---|---|
| ChemicalDamage (line 1921) | EEffectType::Damage | 30.0 | 30.0 | bIsPermanent=true, 1s per charge => 30 DPS; ArmorPiercing 5 |
| SoapBubbleDamage (line 17962) | EEffectType::Damage | 100.0 | 100.0 | big bubble hit |
| ParticleSoapBubbleDamage (line 18000) | EEffectType::Damage | 3.0 | 3.0 | per small particle |
| ToxicCloudDamage (line 20224) | EEffectType::Damage | 25.0 | 25.0 | bIsPermanent=true => 25 DPS; both Box + Cylinder variants |

### FIRE
| Effect struct | Type | ValueMin | ValueMax | Notes |
|---|---|---|---|---|
| FireAnomalyDPS (line 15594) | EEffectType::Damage | 60.0 | 60.0 | permanent => 60 DPS while inside |
| FireBurning (line 1628) | EEffectType::Damage | 10 | 12 | after-burn DoT: Duration 10, Charges 10 (10-12 dmg/s for 10 s) |
| HeatBurning (line 16470) | EEffectType::Damage | 8.0 | 8.0 | passive heat aura, permanent |
| SteamAnomalyDPS (line 15670) | EEffectType::Damage | 60.0 | 60.0 | permanent |
| SteamBurning (line 1666) | EEffectType::Damage | 10 | 12 | Duration 10, Charges 10 |
| SteamHeatBurning (line 16508) | EEffectType::Damage | 8.0 | 8.0 | permanent |
| ClickerAnomalyHit (line 17708) | EEffectType::Damage | 70.0 | 70.0 | per hit, DamageType Burn |
| LavaLampAnomalyFloor (line 15746) | EEffectType::Damage | 5.0 | 5.0 | floor contact, Duration 0.2 |
| LavaLampAnomalyHit (line 15784) | EEffectType::Damage | 15.0 | 15.0 | clot hit |
| FireBallAnomaly (line 15632) | EEffectType::Damage | 100.0 | 100.0 | per hit |

### GRAVITY
| Effect struct | Type | ValueMin | ValueMax | Notes |
|---|---|---|---|---|
| CarouselAnomaly (line 2001) | EEffectType::Damage | 105.0 | 105.0 | Strike/Carousel, per hit |
| RazorAnomalyDamageDPSLow (line 14928) | EEffectType::VelocityDamage | 20.0 | 25.0 | MinSpeed=191.0, MaxSpeed=819.0 — damage scales with move speed inside band |
| RazorAnomalyDamageDPSHigh (line 14968) | EEffectType::VelocityDamage | 100.0 | 100.0 | MinSpeed=820.0, MaxSpeed=10000.0 |
| RazorAnomalyLowBleed (line 15008) | EEffectType::VelocityBleeding | 20.0 | 20.0 | MinSpeed=191.0, MaxSpeed=819.0 |
| RazorAnomalyHighBleed (line 15044) | EEffectType::VelocityBleeding | 60.0 | 60.0 | MinSpeed=820.0, MaxSpeed=10000.0 |
| ExpulsionDamage (line 15708) | EEffectType::Damage | 60.0 | 65.0 | Strike, ArmorPiercing 4 |
| DiamondDPS (line 24921) | EEffectType::Damage | 15.0 | 15.0 | Strike |
| DiamondBleeding (line 25175) | EEffectType::Bleeding | 10 | 10 | |
| DiamondEquipDPS (line 24959) | EEffectType::Composite | 0.f | 0.f | equipment durability only — do NOT scale for HP damage |

### PSY (note only — no direct HP damage)
| Effect struct | Type | ValueMin | ValueMax | Notes |
|---|---|---|---|---|
| PsyAnomalyIncreaseRegen (line 13067) | EEffectType::DegenPsyPoints | -1.7 | -1.7 | permanent psy-points drain; used by PsyAnomaly, PSYControllerAnomaly, PSYEmitterAnomaly |
| FlycatcherSlowRegenHP (line 12206) | EEffectType::RegenHealth | -80% | -80% | percent string, permanent |
| FlycatcherSlowRegenFP (line 12240) | EEffectType::RegenStamina | -80% | -80% | percent string |

## Recommended per-element scaling sets (multiply ValueMin+ValueMax in EffectPrototypes.cfg)
- **Electro**: ElectroAnomaly, ElectroAnomalyPrologue
- **Chemical**: ChemicalDamage, SoapBubbleDamage, ParticleSoapBubbleDamage, ToxicCloudDamage
- **Fire**: FireAnomalyDPS, FireBurning, HeatBurning, SteamAnomalyDPS, SteamBurning, SteamHeatBurning, ClickerAnomalyHit, LavaLampAnomalyFloor, LavaLampAnomalyHit, FireBallAnomaly
- **Gravity**: CarouselAnomaly, RazorAnomalyDamageDPSLow, RazorAnomalyDamageDPSHigh, RazorAnomalyLowBleed, RazorAnomalyHighBleed, ExpulsionDamage, DiamondDPS, DiamondBleeding
- **PSY (optional slider)**: PsyAnomalyIncreaseRegen (scale magnitude of -1.7)

Corrosion SIDs (ElectroCorrosion, ChemicalCorrosion, CarouselCorrosion, RazorAnomalyCorrosionDPS, FireAnomalyCorrosion, BurningCorrosion, SteamAnomalyCorrosion, SteamCorrosion, SteamHeatBurning excluded, SoapBubbleCorrosion, ParticleSoapBubbleCorrosion, LavaLamp*Corrosion, ExpulsionCorrosion, ClickerCorrosion, ToxicCloudCorrosion, ElectroCorrosionPrologue, FireBallCorrosion) are `EEffectType::Composite` armor/durability effects with ValueMin/Max = 0 — exclude from HP damage scaling. ClickerFlasBangComposite, ExpulsionPostProcess, FlycatcherPostProcess, ChemicalAnomalyTurnRateChange (turn-rate) and ChemicalAnomalyVelocityChange (-50% speed, EEffectType::VelocityChange) are non-damage.

## Integer vs float formats (preserve when patching)
Most values are written `65.0` / `30.0` style; FireBurning/SteamBurning use bare ints `10` / `12`; DiamondBleeding uses `10` / `10`; Flycatcher uses percent strings `-80%`.

WARNUNGEN:
- Name collision: effect structs ElectroAnomaly, CarouselAnomaly, FireBallAnomaly in EffectPrototypes.cfg have the SAME names as anomaly structs in AnomalyPrototypes.cfg — patches must target the correct file, and grep-based tooling must not confuse them.
- Shared effects: the ElectroAnomaly effect is used by ElectroAnomaly, ElectroAnomaly_Dynamic and all three LightningBall anomalies; ToxicCloudDamage is shared by Box and Cylinder variants — one patch scales all users.
- The ElectroAnomaly effect SID is also referenced outside anomalies: AbilityPrototypes.cfg line 11091 (an NPC/ability effect list) and QuestNodePrototypes.cfg lines 589774 and 1899171 (EffectPrototypeSID = ElectroAnomaly). Scaling it also scales those quest/ability damage instances.
- Razor special case: RazorAnomalyDamageDPSLow/High and the two Bleed effects are EEffectType::VelocityDamage / VelocityBleeding with MinSpeed/MaxSpeed bands (191-819 and 820-10000); damage interpolates between ValueMin and ValueMax by player speed. Scale ValueMin and ValueMax by the same factor; do not touch MinSpeed/MaxSpeed.
- PSY anomalies deal no direct HP damage in these files — PsyAnomalyIncreaseRegen drains psy points (DegenPsyPoints -1.7/s); actual psy-HP conversion lives elsewhere. Flycatcher only debuffs regen/speed.
- PillowAnomaly, SpringboardAnomaly and QuestChemicalAnomaly ([1]) have no damage effects at all — impulse keys (CharacterPushingImpulse etc.) are physics, leave out of a damage tweak.
- DiamondEquipDPS is a Composite (equipment durability) with Value 0 — scaling it does nothing for HP; DiamondAnomaly local key EquipmentDamage=10.0 and LavaLampAnomaly local key DestructibleDamage=10.f are gear/object damage, not player HP.
- Value formats differ: FireBurning/SteamBurning/DiamondBleeding use bare integers (e.g. ValueMin = 10), others use x.0 floats — the generator should emit numbers in a format the bpatch system accepts for both.
- FlycatcherSlowRegenHP/FP values are percent strings (-80%) — arithmetic scaling would need percent parsing; recommended to exclude from numeric damage sliders.

# Consumable effect strengths (ItemPrototypes/EffectPrototypes) + Weather selection & emission layout

## Task 1 — Consumables and their effects

### 1a. Items inheriting TemplateConsumable (ItemPrototypes.cfg)

`TemplateConsumable` is defined at line 54017 (`TemplateConsumable : struct.begin {refurl=../ItemPrototypes.cfg;refkey=[0]}`). NOTE: this extraction has NO separate `ConsumablePrototypes.cfg` — everything is merged into `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg`; refurls like `{refurl=ConsumablePrototypes.cfg;refkey=Vodka}` resolve within this same file.

Direct children (`{refkey=TemplateConsumable}`) and 2nd-level children, with their `EffectPrototypeSIDs` arrays (key path inside each item: `EffectPrototypeSIDs : struct.begin / [N] = SID / struct.end`):

| Item SID (line) | EffectPrototypeSIDs |
|---|---|
| Bread (54061) | BreadHealing1, BreadSatiety2, RemoveDrunkness10 |
| FreshBread (54128, refkey=Bread) | FreshBreadHealing2, FreshBreadSatiety3, RemoveDrunkness25 |
| CannedFood (54196) | CannedHealing2, CannedSatiety3, RemoveDrunkness15 |
| SpoiledCannedFood (54264, refkey=CannedFood) | SpoiledCannedSatiety1, SpoiledCannedDamage1, RemoveDrunkness5, SpoiledFoodSound |
| Vodka (54334) | VodkaAntirad3, VodkaSatiety1, VodkaStaminaPenalty, VodkaDrunkness, VodkaPSYInstaDecrease |
| Sausage (54412) | SausageHealing2, SausageSatiety2, RemoveDrunkness15 |
| Energetic (54480) | EnegeticSatiety1, EnergeticStamina, EnergeticStaminaInstant3, EnergeticsPoppyFieldSleepiness, EnergeticSleepiness, EnergyDrinkPostProcess, EnergeticStaminaPerAction1, EnergeticOverusePoints, EnergeticTolerancePoints, EnergeticStaminaPerAction2 |
| Energetic_Limited (54577, refkey=Energetic) | EnegeticSatiety2, EnergeticLimitedStamina, EnergeticLimitedStaminaInstant4, EnergeticsLimitedPoppyFieldSleepiness, EnergyDrinkPostProcess, EnergeticOverusePoints, EnergeticTolerancePoints, EnergeticOverusePoints, EnergeticTolerancePoints, EnergeticStaminaPerAction2 |
| Bandage (54675) | BandageHealing2, BandageBleeding4 |
| Medkit (54728) | MedkitHealing3, MedkitBleeding2, MedkitPostProcess |
| ArmyMedkit (54787) | ArmyMedkitHealing4, ArmyMedkitBleeding3, MedkitPostProcess |
| EcoMedkit (54846) | EcoMedkitHealing4, EcoMedkitBleeding2, EcoMedkitAntirad3, MedkitPostProcess |
| AntiRad (54908) | Antirad4 |
| Hercules (54958) | HerculesWeight, HerculesWeight_Penalty |
| Cinnamon (55010) | CinnamonDegenBleeding |
| Beer (55060) | BeerAntirad1, BeerSatiety1, BeerStaminaPenalty, BeerDrunkness, BeerPSYInstaDecrease |
| Water (55136) | WaterSatiety1, WaterStamina2, RemoveDrunkness5, WaterStaminaInstant, WaterStaminaPerAction1 |
| Milk (55212) | MilkSatiety4, RemoveDrunkness5 |
| PSYBlocker (55278) | PSYBlockerIncreaseRegen |
| GuitarUsable (55330) | (empty: `EffectPrototypeSIDs =`) |

Quest variants elsewhere in the same file (also consumables, same effect SIDs): `DvupalovVodka` (line 61436, refkey=Vodka), `EQ08_FreshBread` (72298, refkey=FreshBread), `EQ82_konserva` (72367, refkey=SpoiledCannedFood). `TemplateQuestConsumable` (58476) has empty `EffectPrototypeSIDs`. Items also carry `AlternativeEffectPrototypeSIDs` (Artifact_WeirdKettle_* variants, used when the WeirdKettle artifact is active) and `NegativeEffectPrototypeSIDs` — those reference SEPARATE effect prototypes not in the table below.

### 1b. Effect table (EffectPrototypes.cfg — all values verbatim; every effect has ValueMin == ValueMax)

Key path per effect: `<SID>.Type`, `<SID>.ValueMin`, `<SID>.ValueMax` (top-level structs, all `{refkey=[0]}` unless noted). Full struct layout also contains: EffectLevel, Duration, Charges, TimePerChargeMin/Max, Positive (EBeneficial::Positive/Negative), DuplicationType, bIsPermanent, bIsSmooth, InstantFirstCharge, etc. Healing/Bleeding effects deliver total Value spread over `Charges` ticks (Charges=4 for all Health/Bleeding, 10 for all Radiation).

| Effect SID (line) | Type | ValueMin/Max | Duration | Charges |
|---|---|---|---|---|
| BreadHealing1 (808) | EEffectType::Health | 8 | 4.0 | 4 |
| FreshBreadHealing2 (842) | EEffectType::Health | 15 | 4.0 | 4 |
| CannedHealing2 (978) | EEffectType::Health | 18 | 6.0 | 4 |
| SausageHealing2 (1186) | EEffectType::Health | 12 | 4.0 | 4 |
| BandageHealing2 (40956) | EEffectType::Health | 20 | 1.0 | 4 |
| MedkitHealing3 (1526) | EEffectType::Health | 70 | 1.0 | 4 |
| ArmyMedkitHealing4 (25209) | EEffectType::Health | 85 | 1.0 | 4 |
| EcoMedkitHealing4 (25243) | EEffectType::Health | 100 | 1.0 | 4 |
| BandageBleeding4 (1492) | EEffectType::Bleeding | -100 | 2.0 | 4 |
| MedkitBleeding2 (1560) | EEffectType::Bleeding | -15 | 2.0 | 4 |
| ArmyMedkitBleeding3 (25277) | EEffectType::Bleeding | -35 | 2.0 | 4 |
| EcoMedkitBleeding2 (25379) | EEffectType::Bleeding | -25 | 2.0 | 4 |
| Antirad4 (1594) | EEffectType::Radiation | -100 | 2.0 | 10 |
| EcoMedkitAntirad3 (25345) | EEffectType::Radiation | -60 | 2.0 | 10 |
| VodkaAntirad3 (18252) | EEffectType::Radiation | -50 | 2.0 | 10 |
| BeerAntirad1 (18218) | EEffectType::Radiation | -10 | 2.0 | 10 |
| BreadSatiety2 (740) | EEffectType::HungerPoints | -20 | 0.f | — |
| FreshBreadSatiety3 (774) | EEffectType::HungerPoints | -35 | 0.f | — |
| CannedSatiety3 (910) | EEffectType::HungerPoints | -50 | 0.f | — |
| SpoiledCannedSatiety1 (944) | EEffectType::HungerPoints | -5 | 0.f | — |
| SausageSatiety2 (1118) | EEffectType::HungerPoints | -30 | 0.f | — |
| MilkSatiety4 (18388) | EEffectType::HungerPoints | -100 | 0.f | — |
| WaterSatiety1 (18354) | EEffectType::HungerPoints | -10 | 0.f | — |
| VodkaSatiety1 (1050) | EEffectType::HungerPoints | **+10** | 0.f | — |
| BeerSatiety1 (18106) | EEffectType::HungerPoints | **+10** | 0.f | — |
| EnegeticSatiety1 (1424) | EEffectType::HungerPoints | **+10** | 0.f | — |
| EnegeticSatiety2 (1458) | EEffectType::HungerPoints | **+5** | 0.f | — |
| WaterStamina2 (25413) | EEffectType::Stamina | 25% | 5.0 | — |
| WaterStaminaInstant (11633) | EEffectType::Stamina | 38% | 0.f | — |
| EnergeticStaminaInstant3 (11735) | EEffectType::Stamina | 50% | 0.f | — |
| EnergeticLimitedStaminaInstant4 (11769) | EEffectType::Stamina | 100% | 0.f | — |
| EnergeticStamina (1288) | EEffectType::RegenStamina | 200% | 45.0 | — |
| EnergeticLimitedStamina (1322) | EEffectType::RegenStamina | 500% | 45.0 | — |
| WaterStaminaPerAction1 (81299) | EEffectType::SPDrain | -10% | 30.0 | — |
| EnergeticStaminaPerAction1 (81211) | EEffectType::SPDrain | -30% | 15.0 | — |
| EnergeticStaminaPerAction2 (81255, refkey=EnergeticStaminaPerAction1) | EEffectType::SPDrain | -100% | 5.0 | — |
| VodkaStaminaPenalty (1742) | EEffectType::SPDrain | **200%** | 20 | — |
| BeerStaminaPenalty (18140) | EEffectType::SPDrain | **200%** | 20 | — |
| RemoveDrunkness25 (28378) | EEffectType::Drunkness | -25 | 5.0 | — |
| RemoveDrunkness15 (28446, refkey=RemoveDrunkness25) | EEffectType::Drunkness | -15 | 5.0 | — |
| RemoveDrunkness10 (28480, refkey=RemoveDrunkness25) | EEffectType::Drunkness | -10 | 5.0 | — |
| RemoveDrunkness5 (28514, refkey=RemoveDrunkness25) | EEffectType::Drunkness | -5 | 5.0 | — |
| VodkaDrunkness (18286) | EEffectType::Drunkness | **+30** | 5.0 | — |
| BeerDrunkness (18320) | EEffectType::Drunkness | **+15** | 5.0 | — |
| VodkaPSYInstaDecrease (41952) | EEffectType::PsyPoints | -5 | 0.f | — |
| BeerPSYInstaDecrease (41884) | EEffectType::PsyPoints | -1 | 0.f | — |
| PSYBlockerIncreaseRegen (18422) | EEffectType::DegenPsyPoints | 10 | 60.0 | — |
| EnergeticSleepiness (1356) | EEffectType::SleepinessPoints | -20 | 3.0 | — |
| EnergeticsPoppyFieldSleepiness (11130) | EEffectType::PoppyFieldRegenSleepiness | -3.5 | 25 | — |
| EnergeticsLimitedPoppyFieldSleepiness (11164) | EEffectType::PoppyFieldRegenSleepiness | -5.0 | 30 | — |
| CinnamonDegenBleeding (18072) | EEffectType::DegenBleeding | 10.0 | 180.f | — |
| HerculesWeight (18038) | EEffectType::AdditionalInventoryWeight | 20 | 300.f | — |
| HerculesWeight_Penalty (81387) | EEffectType::PenaltyLessWeight | 20 | 300.f | — |
| SpoiledCannedDamage1 (1012) | EEffectType::Damage | 15 | 0.f | — |
| SpoiledFoodSound (22199) | EEffectType::SoundEffect | 0.f | 0.f | — |
| EnergyDrinkPostProcess (28026) | EEffectType::PostProcessing | 0.f | 0.f | — |
| MedkitPostProcess (28063) | EEffectType::PostProcessing | 0.f | 0.f | — |
| EnergeticOverusePoints (83717) | EEffectType::EnergeticOveruse | 200 | 0.f | — |
| EnergeticTolerancePoints (83751) | EEffectType::EnergeticTolerance | 300 | 0.f | — |

Value formats seen (verbatim strings to preserve when patching): plain int (`8`, `-100`), float (`-3.5`, `10.0`), percent (`200%`, `-30%`, `50%`), and `0.f`. Sign conventions: HungerPoints negative = fills belly (positive on alcohol/energy drinks = makes hungrier); Bleeding/Radiation/Drunkness negative = removes the condition; SPDrain negative = cheaper actions (buff), positive = more drain (penalty).

### 1c. Shared/cross-referenced SIDs (scan of ALL .cfg under GameData, excluding EffectPrototypes.cfg itself)

Referenced from `QuestNodePrototypes.cfg` (quest scripts applying the effect directly to the player, key `EffectPrototypeSID = ...`): **BreadHealing1** (2x), **CannedHealing2** (2x), **SausageHealing2** (2x), **BandageHealing2**, **MedkitHealing3**, **ArmyMedkitHealing4**, **EcoMedkitHealing4**, **VodkaDrunkness** (6x — scripted drinking scenes). Scaling these also scales those quest moments (low risk: quest-given healing just heals more/less; VodkaDrunkness scaling changes scripted-drunkenness intensity — leave Drunkness out).

Inheritance fan-out inside EffectPrototypes.cfg: `RemoveDrunkness25` is parent of RemoveDrunkness20/15/10/5 (each child overrides its own ValueMin/ValueMax, so patching the parent does NOT leak — but a bpatch on the parent SID only affects RemoveDrunkness25 itself). `EnergeticStaminaPerAction1` is parent of `EnergeticStaminaPerAction2` (child has own values). No consumable effect SID is referenced by any non-consumable item, ability, or NPC config.

### 1d. Recommended EEffectType whitelist for a "consumable strength" scaler

Apply the scaler ONLY to the SIDs listed in 1b (never Type-wide — types like Health are used by hundreds of unrelated effects), and within that set only where Type is whitelisted:

**Safe to scale (beneficial, monotonic):** `EEffectType::Health`, `EEffectType::Bleeding` (all negative), `EEffectType::Radiation` (all negative), `EEffectType::HungerPoints` **restricted to negative values** (skip the +10/+5 hunger-adders on Vodka/Beer/Energetic, or they get worse), `EEffectType::Stamina`, `EEffectType::RegenStamina`, `EEffectType::PsyPoints` (negative), `EEffectType::DegenPsyPoints`, `EEffectType::SleepinessPoints`, `EEffectType::DegenBleeding`, `EEffectType::AdditionalInventoryWeight` (Hercules), and `EEffectType::Drunkness` restricted to the RemoveDrunkness* SIDs (negative).

**Exclude:** `Damage` (spoiled-food self-harm), `SPDrain` (mixed sign: −% = buff, +200% = penalty — either skip entirely or scale only negative), `Drunkness` positive (VodkaDrunkness/BeerDrunkness — also quest-referenced), `PoppyFieldRegenSleepiness` (anomaly counter-balance), `EnergeticOveruse`/`EnergeticTolerance` (addiction system), `SoundEffect`, `PostProcessing`, `PenaltyLessWeight` (HerculesWeight_Penalty — scaling it strengthens the debuff). Percent values must keep the trailing `%`, and `0.f` values must never be touched.

## Task 2 — Weather

### 2a. WeatherSelectionPrototypes.cfg layout

File: `C:/Users/Kathi/Desktop/stalker 2 mod/vanilla/Stalker2/Content/GameLite/GameData/WeatherSelectionPrototypes.cfg` (4230 lines, 45 top-level prototypes). Each prototype: `<Name> : struct.begin {refkey=...}` with keys `SID`, `Priority`, then TEN fixed weather-type sub-structs: `Clearly, Cloudy, Fogy, Stormy, LightRainy, Rainy, Thundery, Emission, CalmBeforeEmission, Underground`. Each sub-struct has exactly: `BlendWeight` (float, `40.f`/`20.0` style), `BlendWeightIncrease`, `WeatherDurationMin`, `WeatherDurationMax`, `MaximumRepeatAmount`, `MaximumCooldownWeatherAmount`, `bAllowInDialogueTransition`. Key path example: `SwampWeatherSelection.Rainy.BlendWeight`. Note some top-level structs are index-named: `[0]` (SID=Empty), `[1]` (SID=BaseWeatherHistory — the base almost everything refkeys), `[2]` (SID=VortexWeatherSelection), `[3]` (SID=EQ55_Weather), `[35]` (SID=E14_MQ02FoundationWeatherSelection) — bpatch must address them by struct name (`[1]`), not SID.

BlendWeight table (vanilla, `.f`/decimals stripped; Emission/CalmBeforeEmission/Underground are 0 everywhere):

| Prototype (SID) | Prio | Clearly | Cloudy | Fogy | Stormy | LightRainy | Rainy | Thundery |
|---|---|---|---|---|---|---|---|---|
| [0] Empty / [1] BaseWeatherHistory | 0 | 40 | 20 | 0 | 20 | 0 | 20 | 0 |
| [2] VortexWeatherSelection | 10 | 40 | 60 | 0 | 0 | 0 | 0 | 0 |
| [3] EQ55_Weather | 99 | 100 | 0 | 0 | 0 | 0 | 0 | 0 |
| SwampWeatherSelection | 1 | 20 | 20 | 20 | 10 | 20 | 10 | 0 |
| Region_ChemicalPlant | 15 | 20 | 35 | 5 | 5 | 25 | 10 | 0 |
| Region_PromZone | 14 | 30 | 25 | 15 | 5 | 15 | 10 | 0 |
| Region_WildIsland | 14 | 30 | 15 | 15 | 10 | 20 | 10 | 0 |
| YanovWeatherSelection | 1 | 20 | 30 | 10 | 5 | 25 | 10 | 0 |
| YantarWeatherSelection | 1 | 15 | 25 | 25 | 10 | 15 | 10 | 0 |
| KordonWeatherSelection | 1 | 30 | 35 | 5 | 0 | 20 | 10 | 0 |
| GradirniWeatherSelection | 1 | 30 | 30 | 10 | 10 | 10 | 10 | 0 |
| Gradirni_FireBreath_WeatherSelection | 1 | 15 | 60 | 0 | 25 | 0 | 0 | 0 |
| CementPlantWeatherSelection | 5 | 25 | 30 | 5 | 10 | 20 | 10 | 0 |
| JupiterWeatherSelection | 29 | 20 | 35 | 5 | 5 | 15 | 20 | 0 |
| RedForestWeatherSelectionMain | 27 | 20 | 40 | 10 | 5 | 25 | 0 | 0 |
| RedForestWeatherSelectionSide | 28 | 30 | 20 | 10 | 5 | 25 | 10 | 0 |
| RostokWeatherSelection | 0 | 30 | 25 | 10 | 5 | 20 | 10 | 0 |
| LesserZoneWeather | 0 | 30 | 20 | 10 | 5 | 30 | 5 | 0 |
| GarbageWeather | 0 | 15 | 40 | 10 | 10 | 15 | 10 | 0 |
| DugaRegionWeather | 0 | 30 | 20 | 10 | 10 | 10 | 20 | 0 |
| BurnForestRegionWeather | 0 | 10 | 30 | 30 | 0 | 20 | 10 | 0 |
| BackwaterWeatherSelection | 0 | 30 | 35 | 10 | 0 | 10 | 15 | 0 |
| MalahitWeatherSelection | 1 | 20 | 30 | 5 | 10 | 20 | 15 | 0 |
| Region_Prypiat | 0 | 20 | 30 | 15 | 5 | 20 | 10 | 0 |
| SQ10_NoEmission_Weather | 0 | 20 | 30 | 0 | 20 | 0 | 30 | 0 |
| PoppyField_WeatherSelection | 1 | 90 | 0 | 0 | 0 | 10 | 0 | 0 |
| WasteWarehouse_NoClear | 99 | 0 | 20 | 0 | 20 | 0 | 20 | 0 |
| BurnForest_Mist_WeatherSelection | 1 | 0 | 50 | 0 | 0 | 0 | 0 | 0 |

Single-weather/quest prototypes (only one weight = 100, not worth exposing in a weather tweak): EQ140_WeatherVolume & EQ37_Weather & SQ88_Weather (50/50 Clearly/Cloudy), Emission_E15_MQ02 (Emission=100!), DeadValleyWeatherSelection (Stormy 100), DeadForestWeatherSelection (Rainy 100), NoRainWeatherSelection / SIIRCAWeatherSelection / PrologueWeatherClearly / E03_MQ05_WeatherClearly (Clearly 100), E03_MQ06_WeatherStormy / StormyForced (Stormy 100), E08_MQ05_WeatherRainy (Rainy 100), E08_MQ05_WeatherCloudy (Cloudy 100), [35] (90/10 Clearly/Cloudy), UndergroundWeatherVolume (all 0). **Prototypes with multiple weights > 0** = the 28 rows of the table above (the 22 "region" ones with 4-6 nonzero weights are the real gameplay targets; Thundery is 0 EVERYWHERE in vanilla).

**Emission mechanics keys** (sub-struct `Emission` inside each prototype): `Emission.BlendWeight = 0.f` everywhere; the trigger is `Emission.BlendWeightIncrease` — vanilla `100.f` on all normal region prototypes (each weather cycle adds 100 to emission weight until it wins), quest variants use `7.f` (EQ140/EQ37/SQ88) or `0.f` (= emissions disabled: all E03/E08 forced-weather, NoRain, SIIRCA, Prologue, StormyForced, DeadValley/DeadForest, PoppyField, SQ10_NoEmission, [35], UndergroundWeatherVolume). `Emission.MaximumCooldownWeatherAmount` — vanilla `18` where emissions are on (must sit through 18 weather slots of cooldown before another emission), `3` on the 7.f-quest ones, `1`/`0` where disabled. `Emission.WeatherDurationMin/Max = 300.f/300.f` everywhere (50.f for Emission_E15_MQ02), `MaximumRepeatAmount = 1`. So an "emission frequency" tweak = scale `Emission.BlendWeightIncrease` (100.f base) and/or `Emission.MaximumCooldownWeatherAmount` (18 base) on the prototypes where BlendWeightIncrease is 100.f — do NOT touch the 0.f quest prototypes or emissions would fire in scripted no-emission areas.

### 2b. EmissionPrototypes.cfg Stages layout

File: 456 lines, 6 top-level prototypes, all index-named `[0]`..`[5]` with `SID` inside; `[1]`..`[5]` are `{refkey=[0]}`. `[0]` SID=Default is the free-roam emission; the rest are quest ones: Emission_E06_MQ01, Emission_E15_MQ02, Emission_E15_MQ01_1, Emission_E15_MQ01_2, Emission_E15_MQ01_3.

Layout: `[N].Stages : struct.begin` containing `[0]`..`[4]`, each `{ StageID = EEmissionStage::<X>, PhaseStartTime, PhaseDuration }`. Vanilla `[0]` (Default): BeforeTheStorm Start=`0.f` Dur=`60.0`; ActivateQuest Start=`0.0` Dur=`1.0`; ShockWave Start=`60.0` Dur=`10.0`; Active Start=`60.0` Dur=`60.0`; AfterTheStorm Start=`120.0` Dur=`20.0`. (Quest ones are shorter, e.g. Emission_E06_MQ01: Before 20, Active Start=20 Dur=30, After Start=50 Dur=5.) Key path example: `[0].Stages.[3].PhaseDuration` (= 60.0, the deadly Active phase of the roaming emission). PhaseStartTimes are cumulative offsets — lengthening a PhaseDuration requires shifting the later stages' PhaseStartTime accordingly (Active starts when BeforeTheStorm ends; AfterTheStorm at Start=120 = 60+60). Only patch `[0]` (Default) for a gameplay tweak; `[1]`-`[5]` are scripted quest emissions. Other tweakable keys on `[0]`: MinReactionOnEmissionTimeQuest=1.f, MaxReactionOnEmissionTimeQuest=3.f, MinReactionOnEmissionTimeALife=7.f, MaxReactionOnEmissionTimeALife=10.f, MinEmissionKillDelayALife=0.5f, MaxEmissionKillDelayALife=2.f, DamageSettings.EmissionDamageBlendTime=3.f.

WARNUNGEN:
- Struct names vs SIDs differ in both weather files: bpatch keys must use the struct name ([0], [1], [35], UndergroundWeatherVolume...), not the SID (Empty, BaseWeatherHistory, E14_MQ02FoundationWeatherSelection). All 6 EmissionPrototypes structs are index-named [0]..[5].
- Weather prototypes inherit via refkey chains ([1] refkeys [0]; nearly all regions refkey [1]) but every prototype REDECLARES all keys locally, so patching the base [1] does not propagate — a weather tweak must patch each region prototype individually.
- Do not scale Emission.BlendWeightIncrease/MaximumCooldownWeatherAmount on prototypes where BlendWeightIncrease is 0.f or 7.f (quest/no-emission volumes) — only on the 100.f ones; otherwise emissions can fire inside scripted no-emission areas.
- 8 healing SIDs and VodkaDrunkness are also applied directly by quest nodes in QuestNodePrototypes.cfg (EffectPrototypeSID = ...); scaling them scales those scripted moments too. Keep Drunkness-positive effects out of the whitelist for this reason.
- HungerPoints has inverted semantics: negative fills the belly. Vodka/Beer/Energetic have POSITIVE HungerPoints (+10/+5) — a naive 'stronger consumables' multiplier would make drinks hungrier. Whitelist by (Type, sign) or per-SID.
- SPDrain is mixed-sign: -10%/-30%/-100% are buffs (Water/Energetic), +200% are penalties (Vodka/Beer). Either exclude SPDrain or scale only negative values.
- Percent values (200%, -30%) must keep the % suffix when written back; 0.f-valued cosmetic effects (SoundEffect, PostProcessing) must not be patched at all.
- Consumables also have AlternativeEffectPrototypeSIDs (Artifact_WeirdKettle_* variants) — if only the main SIDs are scaled, effect strength silently reverts to vanilla-ish while the player carries the WeirdKettle artifact. Acceptable, but worth documenting.
- Energetic_Limited's EffectPrototypeSIDs lists EnergeticOverusePoints and EnergeticTolerancePoints TWICE ([5]+[7] and [6]+[8]) — vanilla data quirk, dedupe when collecting SIDs.
- EmissionPrototypes stage times are interlocking (Active.PhaseStartTime == BeforeTheStorm end; AfterTheStorm.PhaseStartTime == Start+Duration of Active): changing one PhaseDuration without shifting later PhaseStartTimes desyncs the emission timeline.
- This extraction merges ConsumablePrototypes.cfg into ItemPrototypes.cfg; refurl=ConsumablePrototypes.cfg strings appear but the file does not exist here. In the shipped game the consumables live in ItemPrototypes/ConsumablePrototypes.cfg — patch paths chosen for the pak must match the real game layout, not this merged dump.