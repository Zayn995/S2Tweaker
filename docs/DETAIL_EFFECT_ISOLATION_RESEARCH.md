# Isolation rules for special-artifact and medical detail effects

Research for the authorized detail controls, 2026-09-11. No animation, asset, injector, Dev Kit, production-code or game-installation changes were made by this audit. Numeric effect settings do not require animation edits. This is a static implementation design, not a gameplay result.

All game paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`. The inventory and scalar baseline are also documented in [SLIDER_AUDIT_ARTIFACTS.md](SLIDER_AUDIT_ARTIFACTS.md). Private reproducible evidence: `out/slider_audit_1401/artifacts/isolation.py` and `isolation.json`.

## Scope and measured source relationships

The audit parsed `ItemPrototypes.cfg` (92,232 lines, 1,375 roots) and `EffectPrototypes.cfg` (85,869 lines, 2,426 roots), then inspected the difficulty route to a discovered SID-specific modifier. Ten selected item roots reach 21 distinct effect roots when Weird Water's two composite children are included. References in items/effects were checked; arbitrary Blueprint or unscanned quest-script users cannot be ruled out by this inventory.

| Selected item | Native main effect list, by exact index | Alternative list | Direct/transitive item descendants |
| --- | --- | --- | --- |
| Bandage | `[0] BandageHealing2`, `[1] BandageBleeding4` | None, including ancestors | 0 / 0 |
| Medkit | `[0] MedkitHealing3`, `[1] MedkitBleeding2`, `[2] MedkitPostProcess` | None, including ancestors | 0 / 0 |
| ArmyMedkit | `[0] ArmyMedkitHealing4`, `[1] ArmyMedkitBleeding3`, `[2] MedkitPostProcess` | None, including ancestors | 0 / 0 |
| EcoMedkit | `[0] EcoMedkitHealing4`, `[1] EcoMedkitBleeding2`, `[2] EcoMedkitAntirad3`, `[3] MedkitPostProcess` | None, including ancestors | 0 / 0 |
| AntiRad | `[0] Antirad4` | None, including ancestors | 0 / 0 |
| Hercules | `[0] HerculesWeight`, `[1] HerculesWeight_Penalty` | None, including ancestors | 0 / 0 |
| Cinnamon | `[0] CinnamonDegenBleeding` | None, including ancestors | 0 / 0 |
| PSYBlocker | `[0] PSYBlockerIncreaseRegen` | None, including ancestors | 0 / 0 |
| AArtifactWeirdNut | `[0] DegenBleeding10`, `[1] RegenHealthModifier` | None, including ancestors | 0 / 0 |
| AArtifactWeirdWater | `[0] WeirdWaterWeightChangeCompositeEffect`, `[1] ArtifactProtectionRadiation1` | None, including ancestors | 0 / 0 |

Paths for the first table are `ItemPrototypes.cfg: <item>.EffectPrototypeSIDs.[index]`. Every main list is directly declared, contains only scalar numeric indices, and has no list attributes. All eight medical/buff roots inherit `TemplateConsumable`; both special artifacts inherit `TemplateArtifact`. All 21 reached effect roots inherit `[0]`, explicitly declare their selected values and have no direct effect descendants in the inspected effect inventory.

The descendant scan intentionally followed every `refkey`, including entries with `refurl`: merged item data contains same-parent names with cross-file attributes. For these ten roots there are no candidate children at all, including quest-marked children. A future data update adding descendants must trigger a fresh support decision rather than inheriting this conclusion.

Eight medical/buff items resolve to `Type=EItemType::Consumable`, `Usable=true`, `ConsumeOnUse=true`. The two special artifacts resolve to Artifact / false / false. The two quest flags are absent on these ten roots and their current ancestor chains; absence should not be rewritten to false. Reject a future true quest flag. Do not admit arbitrary category members: other consumable branches have quest descendants and alternative use paths.

## A discovered constraint: Master difficulty addresses healing SIDs

Three medical sources are explicitly looked up by SID in `EffectPrototypes.cfg: MasterEffectModifier.EffectModifiers`:

| Exact native row | EffectPrototypeSID | DurationMultiplier | ValueMultiplier |
| --- | --- | --- | --- |
| `MasterEffectModifier.EffectModifiers.[1]` | BandageHealing2 | 0.f | 0.25f |
| `MasterEffectModifier.EffectModifiers.[9]` | MedkitHealing3 | 0.f | 0.71 |
| `MasterEffectModifier.EffectModifiers.[10]` | ArmyMedkitHealing4 | 0.f | 0.82 |

The modifier has type `EEffectType::EffectModifier`. `MasterEffectModifierNegativeMechanics.MechanicsEffect.ConditionEffects.LowHPThreshold.ApplicableEffects.[0].EffectSID` activates it, and `DifficultyPrototypes.cfg: Stalker.EnvironmentDifficulty.AdditionalMechanicsEffects.[4]` names that mechanics effect. `Stalker_Xbox` inherits Stalker. This is a real difficulty dependency; cloning a heal and assigning a new SID could bypass its exact-SID modifier.

**Recommended initial medical implementation:** patch the native numeric effect roots for the 14 listed medical/buff effects, retaining original item references. Each has precisely one direct item consumer among the complete item inventory, no item descendants under that owner, no effect descendants, and no other discovered item/effect consumers except the three modifier lookups above. The modifier lookup must remain intact. Native-root patches also retain existing effect identity when a timed buff is already present in a save.

Validate this restricted ownership from the loaded data; do not generalize native-root editing to shared food/drink effects or to the postprocess source. A newly shared source, extra descendant or unsupported modifier should disable the affected option until its scope is handled. This explicit eight-item case gives meaningful per-item controls without needing an unproven modifier-duplication system.

If implementation nevertheless clones the three healing sources, it must handle the modifier dependency. One possible design is to append a new row for each clone to every applicable native SID-specific modifier, preserving both multipliers and all original rows. That requires its own implementation/test scope, preserving other mod additions and validating whether the engine matches exact IDs or inheritance. It is **not** justified to silently omit the mapping, rename the original modifier row, or assume inheritance automatically preserves it. Do not hardcode these difficulty multipliers into the heal values: doing so would affect other difficulty levels and miss runtime changes.

## Complete medical scalar/control table

`ValueMin` equals `ValueMax` in every row. The two values must both change. All paths are `EffectPrototypes.cfg: <SID>.<leaf>`.

| Effect SID | Type suffix | ValueMin = ValueMax | Duration | Duplication | Local controls |
| --- | --- | --- | --- | --- | --- |
| BandageHealing2 | Health | 20 | 1.0 | KeepAll | Magnitude only |
| BandageBleeding4 | Bleeding | -100 | 2.0 | KeepAll | Magnitude only |
| MedkitHealing3 | Health | 70 | 1.0 | KeepAll | Magnitude only |
| MedkitBleeding2 | Bleeding | -15 | 2.0 | KeepAll | Magnitude only |
| ArmyMedkitHealing4 | Health | 85 | 1.0 | KeepAll | Magnitude only |
| ArmyMedkitBleeding3 | Bleeding | -35 | 2.0 | KeepAll | Magnitude only |
| EcoMedkitHealing4 | Health | 100 | 1.0 | KeepAll | Magnitude only |
| EcoMedkitBleeding2 | Bleeding | -25 | 2.0 | KeepAll | Magnitude only |
| EcoMedkitAntirad3 | Radiation | -60 | 2.0 | KeepAll | Magnitude only |
| Antirad4 | Radiation | -100 | 2.0 | KeepAll | Magnitude only |
| HerculesWeight | AdditionalInventoryWeight | 20 | 300.f | KeepNew | Paired magnitude and duration |
| HerculesWeight_Penalty | PenaltyLessWeight | 20 | 300.f | KeepNew | Same local factors as HerculesWeight |
| CinnamonDegenBleeding | DegenBleeding | 10.0 | 180.f | KeepNew | Magnitude and duration |
| PSYBlockerIncreaseRegen | DegenPsyPoints | 10 | 60.0 | KeepNew | Magnitude and duration |

All 14 are nonpermanent, have `ValueProviderSID=Empty`, an empty curve path and native localization keys. Keep medical 1–2-second durations fixed in the first scope: stretching them changes delivery speed, which has not been researched as a user option. Leave `MedkitPostProcess` and all animation/sound references unchanged.

### Exact interaction with existing globals

The audit invoked `_effects_patch` independently with each global factor at 2.0 and recorded the actual output. Use live source literals, multiply the appropriate current global factors once, then apply the local detail factor. This table describes the existing behavior to preserve:

| Source(s) | Existing magnitude factors | Existing duration factor |
| --- | --- | --- |
| Four medical Health effects | `consumable_factor × healing_factor` | None |
| Medical Bleeding/Radiation removal, Cinnamon, PSYBlocker | `consumable_factor` | Cinnamon and PSYBlocker: `consumable_duration_factor` |
| HerculesWeight | `armor_carry_bonus_factor` | `consumable_duration_factor` |
| HerculesWeight_Penalty | None | `consumable_duration_factor` |
| DegenBleeding10 / RegenHealthModifier | None | None |
| WeirdWaterCarryWeightEffect | `armor_carry_bonus_factor` | None |
| WeirdWaterPenaltyLessWeightEffect | None | None |
| Weird Water's untouched ArtifactProtectionRadiation1 | `artifact_effect_factor` | None |

`artifact_effect_factor` does not currently scale the named Nut effects or Weird Water's carry composite. `anomaly_wear_factor` changed none of the 21 inspected native sources. Do not introduce new broad factor membership as a side effect of a detail control.

Two arithmetic checks:

- Medkit heal with global consumables 1.2, global medical healing 1.5 and local healing 1.25: `70 × 1.2 × 1.5 × 1.25 = 157.5`. Its native SID and Master modifier relationship remain.
- Hercules with global armor carry 2, global duration 2, local paired magnitude 1.5 and local duration 1.5: capacity 60, threshold 30, both durations 900 seconds. The differing magnitude is the pre-existing broad carry-factor behavior; a local paired setting must not silently change global semantics.

When a combined selected magnitude equals the original live literal, remove that leaf from the accumulated native patch rather than writing a redundant vanilla value. Keep independent duration changes. Neutral local controls must not emit clones, list rewrites or guards. Do not multiply values already calculated by `_effects_patch` and then multiply the same globals again.

## Safe special-artifact clone and repoint construction

The special items can use deterministic effect clones without altering shared native roots. Their selected effects are simple values except for Weird Water's explicitly inspected two-child composite.

### Weird Nut

Create one new root for each selected changed effect, using `__new__=True`, `__attrs__=refkey=<native SID>`, and a new explicit `SID`. Override only the chosen `ValueMin`/`ValueMax` pair, computed from the original live source. Preserve percentage literals (`DegenBleeding10=2000.0%`), the permanent `KeepAll` lifecycle, curve/provider state and native localization identity.

Repoint only item `[0]` for bleeding and/or `[1]` for the health drawback. If both are changed, merge both replacements into one main-list patch. Do not touch the other special-artifact objects or any ordinary artifact. `RegenHealthModifier.LocalizationSID=Empty` is intentional and its display is hidden: do not invent a localized title by replacing Empty with the new SID.

Both special items explicitly set `ShouldShowEffects =` and `EffectsDisplayTypes =` as empty scalar values, rather than structured arrays. Leave them unchanged. Applying the ordinary-artifact extra-bonus array/visibility helper would fail the source shape and would introduce new UI behavior.

### Weird Water

For a changed paired carry factor, create two leaf clones and one composite clone:

1. Capacity leaf inherits `WeirdWaterCarryWeightEffect`; write `live 50.0% × existing armor-carry factor × local factor` to both magnitude leaves.
2. Threshold leaf inherits `WeirdWaterPenaltyLessWeightEffect`; write `live 50.0% × local factor` to both leaves.
3. Composite clone inherits `WeirdWaterWeightChangeCompositeEffect`, has its own SID, and declares `ApplyExtraEffectPrototypeSIDs.[0]` as the capacity clone and `[1]` as the threshold clone. These two indices replace both existing native child references of the clone; no wildcard append is needed.
4. Repoint only `AArtifactWeirdWater.EffectPrototypeSIDs.[0]` to the composite clone. Preserve the native radiation-removal source at `[1]` and the empty display metadata.

Leaf effects remain permanent `KeepNew`; the composite remains nonpermanent `KeepAll`, `Duration=0.f`, with the native dialog/save settings. Do not turn the composite into a permanent loop, clone its zero magnitudes as if they were the buff, or append new children alongside native children. Minimum intoxication is an independent item scalar at `AArtifactWeirdWater.MinimalDrunkenness=15.0`; changing it alone needs no effect clones.

A 150% local carry factor with global carry 100% gives 75% capacity and 75% threshold. With existing global carry 200%, the same local factor gives 150% capacity and 75% threshold. Preserve the percent unit; neither means a fixed number of kilograms.

If the native composite gains any additional child, nested list shape, provider or changed type, either preserve and explicitly validate that entire new branch or disable the control. Do not accidentally narrow a future composite to the currently observed two children.

### Clone helpers and limitations

- [artifact_extensions.py](../s2tweaker/artifact_extensions.py) `clone_sid()` already hashes mod name, item and effect identity with separators. A distinct detail-role token in the third argument can keep a new use disjoint from existing artifact clones. A dedicated prefix following the same pattern is also reasonable.
- Its `_literal()` preserves `%`/`f` suffixes, and `_put()` implements sparse leaf placement/removal. These are useful patterns, but `_effect_change()` assumes the global artifact factor and ordinary artifact localization semantics; do not call it blindly for medicine or Nut/Water.
- [emit.py](../s2tweaker/emit.py) handles `__new__` correctly: new roots and their children are emitted without `bpatch`, while existing item roots remain patches.
- [repair_extensions.py](../s2tweaker/repair_extensions.py) `effect_namespace()` demonstrates collision-resistant named effect groups and checks both root keys and explicit SID values. Check all planned clone IDs against both forms and against each other before writing anything.
- `GameData.resolve()` reads live scalar inheritance, but `_resolve_chain()` stops a cycle or missing parent silently and does not validate `refurl`. It is not itself a support validator. Validate the selected chain and list shape first; do not accept unresolved data because a scalar happened to resolve.
- `artifact_additions.descendants()` deliberately ignores cross-file `refurl` entries. It is not a general consumable-descendant detector. The current ten targets have zero candidate descendants even when all parent names are included; future cross-file children must fail closed or receive a researched resolver.
- `_scope_override_patch()` predates the newer `__new__`/collision pattern. Its whole-list replacement is not suitable for preserving Hercules repair appends.

Changing effect identity can leave an old native timed/permanent effect active in a saved game alongside its replacement, and `KeepNew` with different identities may not behave like repeated use of one identity. Test clean equip/unequip and expired consumable buffs, then saved-state transitions. This is another reason to prefer native medical-root edits in this bounded first phase. Static construction does not establish runtime duplicate resolution for new IDs.

## Hercules field repair must remain independent

The current repair module creates a new instantaneous composite plus one corrosion leaf per selected equipment slot. Its only item modifications are:

- `Hercules.EffectPrototypeSIDs.[*] = <repair composite SID>`
- `Hercules.ShouldShowEffects.[*] = false`

The repair roots inherit native `[0]`, with negative Corrosion percentages and no native Hercules duration. The existing builder computes these extensions before its normal item/effect passes and merges them into those passes.

Native medical-root editing leaves both appends and original item metadata untouched. If a detail path uses clones, merge numeric-slot replacements into the **already accumulated** item patch with `setdefault(...).update(...)`, retaining any `[*]` append. Do not assign `item_patch['EffectPrototypeSIDs']` from a vanilla copy after repair has added its wildcard. Likewise do not replace `ShouldShowEffects` just to redraw ordinary benefit rows.

Hercules has only `[0]` in `EffectsDisplayTypes` (`ValueAndTime`), while `[1]` in `ShouldShowEffects` is false. That asymmetric native layout is valid; do not fill missing display rows as a prerequisite for two effect replacements.

Magnitude/duration controls must target only the two original Hercules sources. They must not scale the repair composite, repair Corrosion percentage, or any generated leaf found by traversing the final modified list. A field-repair 10% setting remains 10% even when Hercules strength and duration are doubled. The repair remains instantaneous; it must not become a repeating 600-second corrosion effect.

## Focused implementation checks

1. Neutral detail state adds no output and leaves all currently selected global/repair output unchanged.
2. Native medical path preserves all item lists and the three Master modifier SID lookups. A changed per-item source does not alter another item source; exact ownership changes disable the option.
3. Combined medical global/local factors are applied once, signs and literal units are preserved, and combined-one leaves are removed while independent duration stays.
4. Nut repoints only selected existing slots and retains empty display metadata. Water has precisely one replacement composite with two leaf references; radiation and native sources remain independently controlled.
5. Global carry and local paired factors produce the documented asymmetric results where the user already chose a global carry change.
6. Every Hercules native/detail combination preserves one repair wildcard and its hidden display append. Repair magnitudes, lifecycle and slot routing remain unchanged.
7. Detect new quest children, cross-file ambiguity, alternate lists, effect sharing, composite shape changes, duplicate generated IDs, providers/curves, missing sources and nonnumeric leaves before partial output.
8. In game, check Master-difficulty healing, repeated buff use, expire/reuse, equip/unequip and save/load. These are required validation targets, not completed tests.

No additional cfg extraction is needed for these scoped effects. Food/drink expansion, Master modifier cloning, hidden alternative lists and new effect-row UI remain outside this first implementation unless separately handled. The current eight medical targets do not require any animation change.
