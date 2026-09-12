# Optional helmet detail controls: consumer and integration audit

2026-09-11; research only against the installed 2.0.5 CFG snapshot and current
1.40.1 equipment implementation. The scope is additional equipment options
that do not require animation changes. This audit changes no application code and does
not perform a game test. It covers optional helmets and the camp-profile
descendant check; NPC firing/animation timing and NVG behavior are outside scope.

## Decision and exact scope

The 23 previously identified native helmet `Chance` rows produce **76 optional
helmet controls for 48 ordinary roles across 11 factions** when resolved through
the existing object and generator routes. Both Scientists roles have no audited
optional helmet group and receive no new control. All 23 source rows are
reachable. All 50 existing object predicates pass on the local snapshot.

Every selected Head group contains exactly one `[0]` candidate with only
`ItemPrototypeSID` and `Chance`. There are no weighted alternatives in this
set. All native chances are positive and below 1, so zero can safely mean
"do not generate this optional helmet" without invalidating an equipment
weight lottery. This does not remove or replace the NPC's body armor.

The limits and grouping remain relative to existing game rules. Helmets are
not proven lootable and equipment profiles can be used for generic mission
NPCs. Named/custom object links are preserved by the existing clone boundary.
See [base equipment scope](NPC_EQUIPMENT_SCOPE.md), [composition audit](NPC_EQUIPMENT_COMPOSITION.md)
and the [earlier world/NPC audit](SLIDER_AUDIT_WORLD_NPC.md).

## Existing source files

Paths relative to `vanilla/Stalker2/Content/GameLite/GameData/`:

| CFG | Lines | Top-level structs |
| --- | --- | --- |
| ItemGeneratorPrototypes.cfg | 277353 | 3086 |
| ObjPrototypes.cfg | 1318780 | 1660 |
| ItemPrototypes.cfg | 92232 | 1375 |
| NPCNeedsPresetPrototypes.cfg | 3862 | 26 |

`NPCPrototypes.cfg` is also used by the existing `_object_ok` predicate, through
the normal lazy GameData property. No new extraction input is needed for this
extension. Keep `CACHE_SCHEMA` unchanged unless implementation adds another
required input. Source hashes and full private evidence are recorded under
`out/slider_audit_1401/world_npc/`.

## Stable identity and native row validation

Use a dedicated key prefix for probability controls:

```text
npc_helmet:<object SID>:<source generator SID>:<slot key>:<row key>
```

Example:

```text
npc_helmet:GeneralNPC_Neutral_Recon:GeneralNPC_Neutral_Recon_ItemGenerator:[12]:[0]
```

The complete source identity also records the expected item, category, raw
`PlayerRank`, raw `Diff`, and expected source attributes in the code allowlist.
Only identities belong in code; load the actual chance with
`gd.resolve(gd.itemgenerators, source, "ItemGenerator.<slot>.PossibleItems.<row>.Chance")`.
The root attributes are the same for every selected source:
`refurl=../ItemGeneratorPrototypes.cfg; refkey=[0]`.

A strict catalog validator should require:

1. The existing `_object_ok` and `_source_ok` checks, including the current
   ordinary object metadata and unchanged audited source routes.
2. Category exactly `EItemGenerationCategory::Head`, exact native rank/difficulty
   masks, no slot inheritance, exactly the expected `PossibleItems` shape.
3. One `[0]` row, empty row attributes, no nested children, exact expected
   `ItemPrototypeSID`, a finite native `Chance` strictly between 0 and 1, no
   `Weight` or generator reference. Skip newly guaranteed/native-zero rows
   instead of changing their meaning as an optional multiplier control.
4. `_item_ok(gd, item)` and `gd.item_category(item) == "armor"`. Do not require
   visible player inventory to edit equipment generation; do not create loot.

Fail closed and mark saved controls inactive if these identities no longer
match live data. Do not silently retarget a moved index, renamed item or new
candidate row. An implementation may locate an exact identity dynamically,
but must not turn a different item into the old saved setting.

The actual difficulty field is **`Diff`**, not `GameDifficulty`. All 23 local
Head groups have no direct `Diff`; effective restrictions must still be derived
by intersecting each enclosing route's masks. Do not infer "all ranks" from a
helper whose own PlayerRank is absent.

## Complete source identity and live baseline table

Path for every row:
`<source>.ItemGenerator.<slot>.PossibleItems.[0].Chance`.
The `Head` category and `[0]` row are common to all entries below. A dash means
the raw rank is absent. All candidate rows and slots have empty attributes.

| Source | Slot | Raw PlayerRank | Item | Chance |
| --- | --- | --- | --- | --- |
| GeneralNPC_Bandit_Armor | [2] | ERank::Experienced, ERank::Veteran, ERank::Master | Light_Bandit_Helmet | 0.3 |
| GeneralNPC_Corpus_Armor | [3] | ERank::Newbie, ERank::Experienced | Light_Military_Helmet | 0.3 |
| GeneralNPC_Corpus_Armor | [4] | ERank::Veteran | Heavy_Military_Helmet | 0.3 |
| GeneralNPC_Duty_Armor | [4] | ERank::Newbie | Light_Duty_Helmet | 0.3 |
| GeneralNPC_Duty_Armor_Experienced_var1 | [1] | — | Heavy_Duty_Helmet | 0.3 |
| GeneralNPC_Freedom_Armor | [4] | ERank::Experienced | Heavy_Svoboda_Helmet | 0.3 |
| GeneralNPC_Mercenaries_Armor | [4] | ERank::Newbie, ERank::Experienced | Light_Mercenaries_Helmet | 0.3 |
| GeneralNPC_Militaries_Armor | [3] | ERank::Newbie | Light_Military_Helmet | 0.3 |
| GeneralNPC_Militaries_Armor | [4] | ERank::Experienced | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Militaries_Armor_var2 | [1] | — | Heavy_Military_Helmet | 0.9 |
| GeneralNPC_Monolith_Armor | [3] | ERank::Newbie, ERank::Experienced | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator | [13] | ERank::Newbie, ERank::Experienced | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_CloseCombat_ItemGenerator | [14] | ERank::Veteran, ERank::Master | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Neutral_Recon_ItemGenerator | [12] | ERank::Newbie, ERank::Experienced | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_Recon_ItemGenerator | [13] | ERank::Veteran, ERank::Master | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Neutral_Sniper_ItemGenerator | [13] | ERank::Newbie, ERank::Experienced | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_Sniper_ItemGenerator | [14] | ERank::Veteran, ERank::Master | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Neutral_Stormtrooper_ItemGenerator | [9] | ERank::Newbie, ERank::Experienced | Light_Neutral_Helmet | 0.3 |
| GeneralNPC_Neutral_Stormtrooper_ItemGenerator | [10] | ERank::Veteran, ERank::Master | Light_Neutral_Helmet | 0.7 |
| GeneralNPC_Noon_Armor | [3] | ERank::Newbie, ERank::Experienced | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Noon_Armor | [4] | ERank::Veteran | Heavy_Military_Helmet | 0.3 |
| GeneralNPC_Spark_Armor | [3] | ERank::Newbie, ERank::Experienced | Battle_Military_Helmet | 0.3 |
| GeneralNPC_Varta_Armor | [3] | ERank::Experienced, ERank::Veteran | Heavy_Varta_Helmet | 0.7 |

## Effective controls by object, role and rank

Each row below is one control with identity `(object, source, slot, [0])`.
The source candidate/item is given in the preceding table. In this snapshot,
every effective context permits Easy, Medium, Hard and Stalker. Rank names
refer to **player progression**, not an individual NPC's personal rank.
Native combined rank groups remain one control; no additional overlapping
groups are introduced.

| Object / role | Source | Slot | Effective player ranks | Clones if this control alone changes |
| --- | --- | --- | --- | --- |
| GeneralNPC_Bandit_CloseCombat | GeneralNPC_Bandit_Armor | [2] | Experienced + Veteran + Master | 2 |
| GeneralNPC_Bandit_Heavy | GeneralNPC_Bandit_Armor | [2] | Experienced + Veteran + Master | 2 |
| GeneralNPC_Bandit_Recon | GeneralNPC_Bandit_Armor | [2] | Experienced + Veteran + Master | 2 |
| GeneralNPC_Bandit_Stormtrooper | GeneralNPC_Bandit_Armor | [2] | Experienced + Veteran + Master | 2 |
| GeneralNPC_Corpus_CloseCombat | GeneralNPC_Corpus_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Corpus_CloseCombat | GeneralNPC_Corpus_Armor | [4] | Veteran | 2 |
| GeneralNPC_Corpus_Heavy | GeneralNPC_Corpus_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Corpus_Heavy | GeneralNPC_Corpus_Armor | [4] | Veteran | 2 |
| GeneralNPC_Corpus_Recon | GeneralNPC_Corpus_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Corpus_Recon | GeneralNPC_Corpus_Armor | [4] | Veteran | 2 |
| GeneralNPC_Corpus_Sniper | GeneralNPC_Corpus_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Corpus_Sniper | GeneralNPC_Corpus_Armor | [4] | Veteran | 2 |
| GeneralNPC_Corpus_Stormtrooper | GeneralNPC_Corpus_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Corpus_Stormtrooper | GeneralNPC_Corpus_Armor | [4] | Veteran | 2 |
| GeneralNPC_Duty_CloseCombat | GeneralNPC_Duty_Armor | [4] | Newbie | 2 |
| GeneralNPC_Duty_CloseCombat | GeneralNPC_Duty_Armor_Experienced_var1 | [1] | Experienced | 3 |
| GeneralNPC_Duty_Heavy | GeneralNPC_Duty_Armor | [4] | Newbie | 2 |
| GeneralNPC_Duty_Heavy | GeneralNPC_Duty_Armor_Experienced_var1 | [1] | Experienced | 3 |
| GeneralNPC_Duty_Recon | GeneralNPC_Duty_Armor | [4] | Newbie | 2 |
| GeneralNPC_Duty_Recon | GeneralNPC_Duty_Armor_Experienced_var1 | [1] | Experienced | 3 |
| GeneralNPC_Duty_Sniper | GeneralNPC_Duty_Armor | [4] | Newbie | 2 |
| GeneralNPC_Duty_Sniper | GeneralNPC_Duty_Armor_Experienced_var1 | [1] | Experienced | 3 |
| GeneralNPC_Duty_Stormtrooper | GeneralNPC_Duty_Armor | [4] | Newbie | 2 |
| GeneralNPC_Duty_Stormtrooper | GeneralNPC_Duty_Armor_Experienced_var1 | [1] | Experienced | 3 |
| GeneralNPC_Freedom_CloseCombat | GeneralNPC_Freedom_Armor | [4] | Experienced | 2 |
| GeneralNPC_Freedom_Recon | GeneralNPC_Freedom_Armor | [4] | Experienced | 2 |
| GeneralNPC_Freedom_Sniper | GeneralNPC_Freedom_Armor | [4] | Experienced | 2 |
| GeneralNPC_Freedom_Stormtrooper | GeneralNPC_Freedom_Armor | [4] | Experienced | 2 |
| GeneralNPC_Mercenaries_CloseCombat | GeneralNPC_Mercenaries_Armor | [4] | Newbie + Experienced | 2 |
| GeneralNPC_Mercenaries_Recon | GeneralNPC_Mercenaries_Armor | [4] | Newbie + Experienced | 2 |
| GeneralNPC_Mercenaries_Sniper | GeneralNPC_Mercenaries_Armor | [4] | Newbie + Experienced | 2 |
| GeneralNPC_Mercenaries_Stormtrooper | GeneralNPC_Mercenaries_Armor | [4] | Newbie + Experienced | 2 |
| GeneralNPC_Militaries_CloseCombat | GeneralNPC_Militaries_Armor | [3] | Newbie | 2 |
| GeneralNPC_Militaries_CloseCombat | GeneralNPC_Militaries_Armor | [4] | Experienced | 2 |
| GeneralNPC_Militaries_CloseCombat | GeneralNPC_Militaries_Armor_var2 | [1] | Veteran | 3 |
| GeneralNPC_Militaries_Heavy | GeneralNPC_Militaries_Armor | [3] | Newbie | 2 |
| GeneralNPC_Militaries_Heavy | GeneralNPC_Militaries_Armor | [4] | Experienced | 2 |
| GeneralNPC_Militaries_Heavy | GeneralNPC_Militaries_Armor_var2 | [1] | Veteran | 3 |
| GeneralNPC_Militaries_Recon | GeneralNPC_Militaries_Armor | [3] | Newbie | 2 |
| GeneralNPC_Militaries_Recon | GeneralNPC_Militaries_Armor | [4] | Experienced | 2 |
| GeneralNPC_Militaries_Recon | GeneralNPC_Militaries_Armor_var2 | [1] | Veteran | 3 |
| GeneralNPC_Militaries_Sniper | GeneralNPC_Militaries_Armor | [3] | Newbie | 2 |
| GeneralNPC_Militaries_Sniper | GeneralNPC_Militaries_Armor | [4] | Experienced | 2 |
| GeneralNPC_Militaries_Sniper | GeneralNPC_Militaries_Armor_var2 | [1] | Veteran | 3 |
| GeneralNPC_Militaries_Stormtrooper | GeneralNPC_Militaries_Armor | [3] | Newbie | 2 |
| GeneralNPC_Militaries_Stormtrooper | GeneralNPC_Militaries_Armor | [4] | Experienced | 2 |
| GeneralNPC_Militaries_Stormtrooper | GeneralNPC_Militaries_Armor_var2 | [1] | Veteran | 3 |
| GeneralNPC_Monolith_CloseCombat | GeneralNPC_Monolith_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Monolith_Recon | GeneralNPC_Monolith_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Monolith_Sniper | GeneralNPC_Monolith_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Monolith_Stormtrooper | GeneralNPC_Monolith_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Neutral_CloseCombat | GeneralNPC_Neutral_CloseCombat_ItemGenerator | [13] | Newbie + Experienced | 1 |
| GeneralNPC_Neutral_CloseCombat | GeneralNPC_Neutral_CloseCombat_ItemGenerator | [14] | Veteran + Master | 1 |
| GeneralNPC_Neutral_Recon | GeneralNPC_Neutral_Recon_ItemGenerator | [12] | Newbie + Experienced | 1 |
| GeneralNPC_Neutral_Recon | GeneralNPC_Neutral_Recon_ItemGenerator | [13] | Veteran + Master | 1 |
| GeneralNPC_Neutral_Sniper | GeneralNPC_Neutral_Sniper_ItemGenerator | [13] | Newbie + Experienced | 1 |
| GeneralNPC_Neutral_Sniper | GeneralNPC_Neutral_Sniper_ItemGenerator | [14] | Veteran + Master | 1 |
| GeneralNPC_Neutral_Stormtrooper | GeneralNPC_Neutral_Stormtrooper_ItemGenerator | [9] | Newbie + Experienced | 1 |
| GeneralNPC_Neutral_Stormtrooper | GeneralNPC_Neutral_Stormtrooper_ItemGenerator | [10] | Veteran + Master | 1 |
| GeneralNPC_Noon_CloseCombat | GeneralNPC_Noon_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Noon_CloseCombat | GeneralNPC_Noon_Armor | [4] | Veteran | 2 |
| GeneralNPC_Noon_Recon | GeneralNPC_Noon_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Noon_Recon | GeneralNPC_Noon_Armor | [4] | Veteran | 2 |
| GeneralNPC_Noon_Sniper | GeneralNPC_Noon_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Noon_Sniper | GeneralNPC_Noon_Armor | [4] | Veteran | 2 |
| GeneralNPC_Noon_Stormtrooper | GeneralNPC_Noon_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Noon_Stormtrooper | GeneralNPC_Noon_Armor | [4] | Veteran | 2 |
| GeneralNPC_Spark_CloseCombat | GeneralNPC_Spark_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Spark_Recon | GeneralNPC_Spark_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Spark_Sniper | GeneralNPC_Spark_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Spark_Stormtrooper | GeneralNPC_Spark_Armor | [3] | Newbie + Experienced | 2 |
| GeneralNPC_Varta_CloseCombat | GeneralNPC_Varta_Armor | [3] | Experienced + Veteran | 2 |
| GeneralNPC_Varta_Heavy | GeneralNPC_Varta_Armor | [3] | Experienced + Veteran | 2 |
| GeneralNPC_Varta_Recon | GeneralNPC_Varta_Armor | [3] | Experienced + Veteran | 2 |
| GeneralNPC_Varta_Sniper | GeneralNPC_Varta_Armor | [3] | Experienced + Veteran | 2 |
| GeneralNPC_Varta_Stormtrooper | GeneralNPC_Varta_Armor | [3] | Experienced + Veteran | 2 |

Two important caller-derived cases:

- `GeneralNPC_Duty_Armor_Experienced_var1.[1]` is **Experienced only** for
  all five Duty roles, inherited from the calling armor branch.
- `GeneralNPC_Militaries_Armor_var2.[1]` is **Veteran only** for all five
  Militaries roles, inherited from its caller.

These sources remain distinct from their sibling helper variants. Do not
rename them into four independent rank choices or clone only a helper without
redirecting every ancestor along its selected object branch.

| Clones needed for a single effective edit | Controls |
| --- | --- |
| 1 | 8 |
| 2 | 58 |
| 3 | 10 |

The private `helmet_control_identities.json` contains all 76 keys, effective
contexts and full root-to-source clone paths. Each currently has one reachable
path from its ordinary object root. No assumption of this count should replace
future route validation; deduplicate identity/context if an audited helper is
reachable through multiple permitted branches.

## Integration with the existing API

Prefer one equipment registry and one clone pass:

- Add a separate identity-only `HELMET_POOLS`/`HEAD_POOLS` mapping. Keep existing
  weighted `POOLS` validation intact. Add a control kind or a `HelmetControl`
  with the existing object/source/slot/row/item/context interface and the new
  key prefix. `chance` must not be handled as a weight.
- Merge helmet controls into `npc_equipment.CONTROLS` and `catalog(gd)` after
  their own validator. Retain `Settings.npc_equipment_overrides` as the common
  saved mapping: keys already disambiguate the two mechanisms. Then
  `control_specs`, `collect`, `changes`, `summarize`, `available` and `probe`
  can share the existing settings/undo/reset/profile/conflict integration.
- The `pool`, `title`, `help` and `label` properties must state "Optional helmet
  chance (%)" and "100% inherits global helmet chance". Do not look up a
  helmet in weighted `POOLS`, display "relative weight", or require another
  helmet choice above zero. Scope/group selectors in `workbench_ui` already
  consume the generic interface.
- Extend **the existing `apply()`** to collect both kinds by object/source,
  and build one private branch per `(mod_name, object, source)`. Continue using
  `clone_sid` and the existing source attributes. Calling separate clone passes
  for weapon weights and helmets can collide on names or replace one another's
  object links; do not do that.
- Only Weight edits enter the touched-weight-pool/all-zero validation.
  Chance edits use finite probability checks and clamping. A zero optional
  Chance is valid and must not be sent through the all-zero Weight error.
- Keep `footprint()` at its current whole-cloned-branch granularity. A helmet
  helper clone also copies other fields that another mod might change. Keep
  the object's generator-link footprint too.

`extension_controls.build_controls` already creates an `ArtifactControl` for
any registered equipment control with compatible `validate`, limits and
metadata. `_wb_equipment_choices` and `_wb_equipment_editor` select by
`faction`, `role`, `pool` and `selection`. `_wb_edit` dispatches validation and
availability by registry membership. Update the equipment introduction and
Details/native-value wording so a probability is not called a weight.

## Exact composition order

`build_patches()` currently combines global generator patches before
`npc_equipment.apply()`:

1. Loot amount, dropped condition, global gear quality and trader stock.
2. Loot extensions, including global helmet chance, ammo, extra armor loot
   and lower-rank variety.
3. The single equipment clone/edit/relink pass.

Preserve that order. Clone the live source and merge `original_patches` before
editing the selected Chance. The global helmet logic already clamps each
native chance; all 23 selected rows were independently checked using global
factor 2 and matched the expected results.

Recommended semantics are a multiplier of the **inherited effective chance**:

```text
inherited = clamp(native chance * global helmet factor, 0, 1)
final = clamp(inherited * local percentage / 100, 0, 1)
```

Do not multiply `global helmet factor` again inside the clone. Use the merged
row's actual Chance, because that is the inherited result. Sequential saturation
is deliberate and must be covered by tests: it preserves what 100% inherits.

| Native chance | Global factor | Local % | Inherited chance | Final chance |
| --- | --- | --- | --- | --- |
| 0.3 | 1 | 200 | 0.3 | 0.6 |
| 0.3 | 2 | 50 | 0.6 | 0.3 |
| 0.9 | 2 | 50 | 1 | 0.5 |
| 0.7 | 0 | 400 | 0 | 0 |
| 0.3 | 1 | 0 | 0.3 | 0 |
| 0.9 | 2 | 200 | 1 | 1 |

The third row would be 0.9 if factors were incorrectly collapsed before the
global saturation; that is not the inherited-result contract. The last row
has no additional effective change and must not create a helmet-only clone.
Likewise, a local 100% produces no clone on its own. Other edits may still
require a clone, in which case global helmet changes are preserved in it.

The selected Head groups do not receive global quality changes because they
have Chance rather than Weight. `_add_earlier_equipment` explicitly excludes
Chance groups, so optional helmet detail must not inject lower-rank helmets or
NVG candidates. Preserve unrelated cloned weapon/ammo/condition and extra
armor-drop branches. These are equipment-generation chances conditional on
their native caller, not unconditional encounter or corpse-loot probabilities.

## Camp activities: complete descendant closure

The 12 pilot presets from the earlier audit contain 88 selected activity rows.
Their **complete** local descendant closure has eight nodes, all direct guard
children at depth one. There are no grandchildren or deeper descendants in
the 26-root file. All 59 relevant guard activity rows explicitly repeat the
matching indexed `NeedType` and both `IncreaseRateMin/Max` leaves.

| Pilot parent | Complete audited descendants | Depth | Explicit shielding rows |
| --- | --- | --- | --- |
| BanditsNeedsPreset | BanditsNeedsPreset_Guard | 1 | 8 |
| CorpusNeedsPreset | none | 0 | 0 |
| DutyNeedsPreset | DutyNeedsPreset_Guard | 1 | 8 |
| FreedomsNeedsPreset | FreedomsNeedsPreset_Guard | 1 | 8 |
| MercenariesNeedsPreset | none | 0 | 0 |
| MilitariesNeedsPreset | MilitariesNeedsPreset_Guard | 1 | 7 |
| MonolitNeedsPreset | MonolitNeedsPreset_Guard | 1 | 7 |
| NeutralsNeedsPreset | NeutralsNeedsPreset_Guard | 1 | 8 |
| NoonNeedsPreset | NoonNeedsPreset_Guard | 1 | 6 |
| ScientistsNeedsPreset | none | 0 | 0 |
| SparkNeedsPreset | none | 0 | 0 |
| VartaNeedsPreset | VartaNeedsPreset_Guard | 1 | 7 |

For new detail controls use this conservative live skip rule:

1. Rebuild the current same-file refkey graph and recursively traverse the
   complete closure of the selected parent, using cycle detection. Do not stop
   after checking direct guards.
2. Require the closure to equal the audited set in the table. If a new
   descendant appears at any depth, a known relationship changes, an external
   `refurl` cannot be resolved, or a cycle is detected, leave that parent's
   new detail edit inactive. Do not silently apply it only because its direct
   child looks safe. A new branch can be reviewed separately.
3. For every selected parent activity leaf, require the known guard descendant
   to have the same indexed `NeedType`, empty row inheritance and its own
   finite rate pair. If it inherits either targeted leaf or the index is
   repurposed, skip the affected parent's detail edit. The runtime validator
   must use current leaf values, not hardcoded rate constants.
4. Keep the generic `HumanGenericNeedsPreset`, quest, guard, mutant, zombie and
   empty presets outside the new detail target allowlist. Preserve existing
   independently selected global camp settings; only suppress the unsafe new
   detail contribution and explain its inactive status.

This is definition-level shielding. Ordinary needs presets can still be
assigned directly to quest NPCs; it is not proof that every quest behavior is
unaffected. This extension changes need accumulation rates, not animation
playback speed or durations.

## Meaningful verification for implementation

- Neutral settings create no new clones or object links; non-neutral settings
  that saturate to the inherited value also create no helmet-only clone.
- Check direct Neutral root, shared armor helper and caller-restricted Duty/
  Militaries helper paths. The latter require three clones for a single edit.
- Combine a helmet and weighted weapon edit on the same role in one pass;
  verify one coherent object link, no duplicate clone SID, both edits present.
- Combine global helmet chance with detail including saturation, zero, and
  cancellation examples above. Read numeric baselines from changed synthetic
  fixture values so tests do not merely repeat this snapshot.
- Original shared definitions and an unedited role remain unchanged except
  independently requested global changes. Named object links remain original.
- Masks, category, source attrs, references, single candidate shape, slot/item
  identity and local probability are validated; malformed live rows become
  unavailable. Future guaranteed/native-zero rows are not made optional.
- Camp tests include a new direct child, new grandchild, cycle, external-parent
  reference, changed NeedType, missing override leaf and unchanged known guards.
- Profile save/load, reset/undo, inactive saved keys, final preview wording and
  generated-Pak readback remain covered by the existing workflow. In-game
  generation for new NPC inventories still needs a game test.

Private evidence: `out/slider_audit_1401/world_npc/helmet_scope.py`,
`helmet_scope.json`, `helmet_report.py`, `helmet_control_identities.json`.
Source CFG contents are not included in the document or a release artifact.
