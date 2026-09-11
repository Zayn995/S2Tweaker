# NPC equipment editor: composition audit

Research snapshot: 2026-09-11, installed game data 2.0.5. This document audits
the existing 1.39.0 implementation and recommends a composition model. It is
config and source evidence, not an in-game verification or an engine contract.

The selected implementation after the separate caller/scope audit is narrower
than the optional group-quality model explored below: **individual original
candidate Weight percentages, using the existing global quality control, with
isolated cloned generator paths assigned to audited ordinary NPC objects**.
No additional slot-quality control is required. The rank/difficulty pool
selector identifies a native shared group; it does not split those restrictions.

## Sources and scope

All data paths below are relative to
`vanilla/Stalker2/Content/GameLite/GameData/`.

| File | Lines | Parsed top-level structs | Purpose |
| --- | ---: | ---: | --- |
| `ItemGeneratorPrototypes.cfg` | 277,353 | 3,086 | Equipment rows, restrictions, weights and chances |
| `ItemPrototypes.cfg` | 92,232 | 1,375 | Live resolved base item prices and item safety |

Code reviewed: `GameData.gear_weight_pools`, `GameData.loot_generators`,
`_gear_quality_patch`, `_loot_condition_patch`, `build_patches`, and
`loot_extensions._npc_patches`, `_add_earlier_equipment`,
`_expanded_gear_quality`, `_scaled_bounds`, `_restrictions`.
There is no function named `npc_gear_pools` or `_npc_gear_quality_patch` in
this snapshot; those informal names refer to the first and third functions.

The existing ordinary-NPC traversal returns 105 roots beginning `GeneralNPC_`.
Of these, 87 have equipment: 384 direct slots and 892 direct candidate rows.
**These counts describe an audit population, not an approved editor allowlist.**
The existing filter admits `GeneralNPC_Neutral_CloseCombat_ItemGenerator_Prolog`
and `_Prolog_Medkit`, as well as explicit no-armor variants. A new editor must
use a separately audited identity list and validate the live slot structure.

| Category | Slots | Rows with Weight | Rows with Chance | Total rows |
| --- | ---: | ---: | ---: | ---: |
| WeaponPrimary | 237 | 624 | 4 | 628 |
| WeaponSecondary | 0 | 0 | 0 | 0 |
| WeaponPistol | 36 | 73 | 0 | 73 |
| BodyArmor | 75 | 152 | 3 | 155 |
| Head | 36 | 5 | 31 | 36 |
| Total | 384 | 854 | 38 | 892 |

None of these 892 direct rows mixes Weight and Chance. None has neither.
Six rows reference `empty`, a native no-equipment outcome; they have no price
and are not ordinary item candidates. Another 47 ordinary item references
fail the visible-item check used for inventory additions. Visibility is not
the same as suitability for existing equipped NPC gear: never turn an
invisible equipped-armor prototype into a player inventory drop.

## Exact paths and inheritance

The patch identity is the complete tuple `(generator root, slot key, row key)`:

```text
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[0].PossibleItems.[1].Weight
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[0].PossibleItems.[1].AmmoMinCount
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[0].PossibleItems.[1].AmmoMaxCount
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[0].PossibleItems.[1].MinDurability
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[0].PossibleItems.[1].MaxDurability
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[0].PlayerRank
GeneralNPC_Neutral_Recon_ItemGenerator.ItemGenerator.[2].Diff
```

All 384 inspected equipment slots have no inheritance attributes; their direct
candidate rows also have no inheritance attributes. Of the 87 containing
roots, 84 reference the `[0]` template through `refurl`, and the three
`GeneralNPC_Neutral_{Recon,Stormtrooper,CloseCombat}_No_Armor_ItemGenerator`
roots inherit their corresponding role generator. Each of these three writes
local named `BodyArmor` and `Head` slots with `empty`, Weight 15.0,
`bAllowSameCategoryGeneration = false`, and all four PlayerRank tokens. Do not
flatten parent equipment into these intentional overrides.

One malformed-looking native nested structure must not be flattened:
`GeneralNPC_Mercenaries_Recon_ItemGenerator.ItemGenerator.[2].PossibleItems.[1]`
is `GunIntegral_PP`, Weight 1000, and contains an additional child `[6]` with
`GunFora230_PP`, Weight 400. Both have durability 0.25/0.5 and ammo 0/7.
This is literally nested in the CFG around lines 38,684–38,701, not a parser
invented row. A candidate editor must not expose the child as a sibling or
rewrite the surrounding structure. Fail closed for such a slot when a full
candidate-pool model is required.

## PlayerRank arrays and difficulty are slot restrictions

The actual field is `PlayerRank`. UI text must identify this as player
progression rank, rather than promise control over each NPC's personal rank.
One native slot may serve several ranks simultaneously. Writing its Weight
changes that same row for every permitted rank; a rank dropdown does not make
these occurrences independent.

Complete observed PlayerRank string distribution:

| Raw value, with `ERank::` abbreviated except where malformed | Slots |
| --- | ---: |
| No PlayerRank field | 8 |
| Newbie | 53 |
| Experienced | 44 |
| Veteran | 84 |
| Master | 95 |
| Newbie, Experienced | 50 |
| Newbie, Experienced, Veteran | 5 |
| Newbie, Experienced, Veteran, Master (one space before last token) | 8 |
| Newbie, Experienced, Veteran, Master (two spaces before last token) | 4 |
| Experienced, Veteran | 3 |
| Experienced, Veteran, Master | 11 |
| Veteran, Master (both fully qualified) | 18 |
| Literal `ERank::Veteran, Master` | 1 |

The malformed last string belongs to
`GeneralNPC_Bandit_WeaponPistol.ItemGenerator.[2]`. The existing substring
parser recognizes Veteran and silently misses the unqualified Master token.
Do not guess whether the engine accepts that token or silently repair it.
Exclude that slot from a strict rank editor, or expose the literal restriction
without claiming verified Master behavior.

The eight rankless slots belong to four armor helper roots plus the two
prologue variants: Duty Armor Experienced var1 `[0]`/`[1]`, var2 `[0]`,
Militaries Armor var2 `[0]`/`[1]`, var1 `[0]`, and the two prologue Head slots.
A helper's effective rank can come from its caller. Its name alone does not
prove applicability, and absence of PlayerRank must not be labelled a verified
all-ranks assignment without auditing callers.

Complete difficulty distribution:

| Raw Diff | Slots |
| --- | ---: |
| No Diff field | 252 |
| `EGameDifficulty::Easy, EGameDifficulty::Medium, EGameDifficulty::Hard` | 66 |
| `EGameDifficulty::Stalker` | 66 |

Recommended first editor: preserve original rank groups and difficulty groups
as selectable pool identities. A label such as `Newbie + Experienced / Stalker`
is accurate. Do not split PlayerRank arrays or add overlapping slots merely to
provide four independent sliders; this would require a separate generation and
same-category precedence investigation and in-game tests.

## Weight and Chance are separate mechanisms

For a pure Weight list, use relative candidate weights and display a conditional
share `weight / sum(weights)`. This share is conditional on the containing
generator and equipment slot running; caller Chance, restrictions, and other
generation rules may further affect the actual spawn probability. A global
quality factor of four multiplies the most expensive item's weight by four;
it does **not** generally multiply its final probability by four.

Reference arithmetic from the live Newbie Neutral Recon pool:

| Item | Cost | Vanilla Weight | Quality 400% Weight |
| --- | ---: | ---: | ---: |
| GunViper_PP | 3,000 | 1,000 | 1,000 |
| GunAKU_PP | 6,000 | 100 | 400 |

The AKU conditional share goes from `100/1100 = 9.09%` to
`400/1400 = 28.57%`, not 36.36%. Quality is a price-order proxy, not an audited
weapon effectiveness tier. Read unmodified installed `Cost` with `gd.resolve`;
item-price, economy and trader tweaks must not reorder the equipment tier model.

Chance rows must not receive Weight, be normalized as a lottery, or be imported
into a Weight list. There are 31 optional Head rows (21 at 0.3, nine at 0.7,
one at 0.9). The other seven Chance rows are three fixed armor helper rows at
1/1.0 and four fixed weapon rows at 1.0 in
`GeneralNPC_Neutral_Sniper_ItemGeneratorCustom`. All 38 must be handled as their
native mechanism; a weight-only editor can leave them unavailable.

## Fractional weights: existing rounding defect

The old quality builders calculate `max(1, round(weight * factor**price_rank))`.
There are 38 fractional candidate weights among all global quality pools, and
18 among the 892 GeneralNPC audit rows. In the latter, 16 are 0.1 and two 0.5.
Rounding and clamping turns these into 1, even when the cheapest item should
keep its weight. This can reverse the intended direction of a quality slider.

Live counterexample, `GeneralNPC_Neutral_WeaponPistol.ItemGenerator.[3]`:

| Item | Cost | Weight | Old output at quality 25% |
| --- | ---: | ---: | ---: |
| GunPM_HG | 950 | 0.5 | 1 |
| GunUDP_HG | 1,425 | 1 | 1 |
| GunM10_HG | 5,700 | 1 | 1 |
| GunAPB_HG | 14,000 | 0.1 | 1 |
| GunKora_HG | 6,000 | 1 | 1 |

The expensive APB receives 20% of the old resulting lottery, versus 2.78%
vanilla, even though the slider was lowered to 25%. This is a config-output
defect; no gameplay observation is required to prove the numeric mismatch.

Minimal compatible quality rounding recommendation:

1. Compute the combined quality factor `q = global_quality * slot_quality`
   before doing any quality calculation. Compute price ranks once over the
   final candidate pool, including permitted Variety additions.
2. If `q == 1` or the candidate's price rank is zero, retain its exact native
   numeric weight. Missing/nonpositive prices do not participate in price
   ordering; they keep their original weight.
3. For a positive integral native weight, retain the existing
   `max(1, round(native_weight * q**rank))` behavior. For a positive fractional
   native weight, preserve the scaled fraction, with a finite decimal formatter
   of about nine significant digits and no minimum of one.
4. Multiply an explicitly edited original candidate by its additional
   percentage factor **after** this quality calculation. Do not round that
   percentage product back to an integer: 50% of 1 must be representable as
   0.5. An explicit candidate factor of zero disables that candidate.
5. Validate that the final supported pool retains at least one positive
   candidate. Do not turn an existing zero-weight row on via an additive
   offset, and do not use an epsilon floor which silently defeats “Off”.

This keeps existing integral quality behavior and fixes the fractional baseline
defect. Fully continuous quality for all native integer weights is a coherent
alternative, but changes many existing medium-price outputs beyond the defect;
it should be a deliberate documented behavior change.

Global factor 4 and slot factor 0.25 must cancel before rounding. If the final
original-row Weight equals vanilla, remove only the earlier Weight leaf from
the merged patch and prune empty ancestors. Writing vanilla Weight explicitly
would unnecessarily override another mod. Keep all other changed leaves,
including ammo, durability and any custom added candidates.

## Composition with current global and optional settings

| Setting | Existing scope/mechanism | Required editor composition |
| --- | --- | --- |
| `npc_gear_quality_factor` | 4,153 safe Weight pools; only 268 are GeneralNPC; 763 other roots also contain qualifying pools | Preserve its broader scope. New slot controls operate on audited identities only. |
| `npc_equipment_variety` | Copies ordinary visible earlier-rank candidates inside the same generator and category, respecting difficulty subset checks | Build additions first; apply combined quality over the final pool. Original candidate overrides belong only to their exact target slot and row. |
| `npc_loaded_ammo_factor` | Scales 701 GeneralNPC weapon rows' existing AmmoMinCount/AmmoMaxCount, including copied candidates | Weight edits preserve both ammo leaves and do not treat loaded ammo as loot stack counts. |
| `dropped_condition_pct`, `dropped_condition_exact` | Existing weapon row durability; Variety explicitly reproduces the transformation for copied weapon candidates | Weight cleanup must preserve MinDurability/MaxDurability. Never apply weapon condition to copied armor. |
| `npc_helmet_chance_factor` | Scales the 31 native optional Head Chance rows, clamped 0..1 | Leave Chance rows separate from Weight quality and candidate weight controls. |
| `npc_armor_drop_chance_pct` | Adds 63 helper lotteries with 105 visible BodyArmor rows in the audit snapshot | Preserve independent extra-inventory-loot behavior and caller restrictions. It does not clone the actual worn suit. |
| `loot_amount_factor` | Existing loot count leaves | Do not add counts to equipped weapon/armor candidates merely because their weight changed. |
| Item base cost/trader multipliers | Separate item/economy patches | Use loaded vanilla costs for quality order, never already patched retail values. |

Variety adds 309 candidate rows to 146 target slots: 212 copied weapons with
ammo and durability fields, and 97 other equipment rows. At global quality
400%, 247 original-row Weight outputs in the expanded model differ from the
earlier global-only output, including cases where the earlier builder emitted
no leaf. Therefore applying new settings to the already globally rounded
Weight and blindly multiplying again is incorrect.

Existing Variety chooses candidates by the earliest permitted rank of source
and target slots and de-duplicates ItemPrototypeSID within a target. A new
original candidate override must not propagate by SID to another role, rank
group or copied candidate. Example: editing Spark Newbie+Experienced's Kora
does not silently alter a copy in a Veteran+Master target. Copied candidates
inherit the target slot's quality factor, while their candidate factor stays
neutral unless a future explicit added-candidate editor is designed.

The armor-drop helper currently reads untouched source BodyArmor weights before
gear quality or Variety is merged. Consequently a changed equipped lottery
does not currently redefine the extra armor-drop lottery. Keep this explicit
in UI/help; changing both systems silently would broaden the user's equipment
selection. The helper may also contain a rankless source whose caller supplies
restrictions, another reason not to invent independent rank settings from names.

All 701 weapon ammo bounds exist in pairs, are finite/nonnegative, and have no
inverted pair. AmmoMinCount is zero in 569 rows, so a multiplicative setting
must preserve these zeros. Native minimum values are 0, 1, 2, 3, 4, 10, 15, 60;
native maximum values are 2, 3, 4, 5, 6, 7, 8, 15, 20, 25, 60. The helper rounds
counts to integers, skips missing/negative/nonfinite/invalid bounds, and preserves
minimum <= maximum. This count-specific rule must not be reused for Weight.

There are 703 row durability pairs: 701 at 0.25/0.5, one at 0.35/0.55 and one
at 0.8/0.9. The two exceptions are not normal weapon rows, and must not be
converted by a weapon condition control.

## Required tests before implementation can be called verified

1. Neutral settings generate no extra files/Weight leaves; unknown identities,
   mismatched SID/category/rank/Diff, malformed ranks, nested candidate rows,
   unsupported Chance or mixed lists, and prohibited roots fail closed.
2. One original candidate edit changes only its root/slot/row Weight. Same SID
   in another rank, faction, role, difficulty or a Variety addition is unchanged.
3. Shared rank groups show their complete restriction in UI and summaries;
   different controls cannot overwrite the same physical slot by rank aliases.
4. Native 0.1 and 0.5 remain fractions; the cheapest candidate remains exact;
   Native 1/100/1000 preserve intended legacy quality rounding. Include the
   Neutral Master APB and Spark Newbie+Experienced Kora counterexamples.
5. Price ties share an exponent; one priced tier does not trigger quality;
   missing/zero/negative prices stay untouched by quality. Cost slider edits
   do not change quality ordering. Quality factor and candidate factor have
   separate validation and semantics.
6. Compute global 4 × slot 0.25 once, remove only canceled Weight leaves, and
   retain ammo/durability changes. Check cancellation with and without Variety
   and with an active candidate factor, including repeated build determinism.
7. An expanded pool recomputes all affected native and added ranks. A copied
   cheaper item may turn a formerly cheapest original into a middle-price item.
   Preserve difficulty gating, duplicate checks, namespaced row keys and
   `__new__` emission for additions.
8. Candidate zero works if alternatives remain. Turning every possible weight
   to zero is rejected. A one-candidate pool needs an explicit decision: hide
   meaningless relative-weight edits or reject its last-candidate zero. Do not
   invent missing alternatives or enable native zero rows.
9. Changing all candidate percentages equally leaves relative probabilities
   equal. If such scaling is retained as raw Weight behavior, label it honestly;
   do not claim more NPCs or more equipment. No normalization is necessary for
   relative weights, and normalization must not erase an explicit zero.
10. Weight edits neither scale nor create Chance, AmmoMinCount/AmmoMaxCount,
    MinCount/MaxCount or MinDurability/MaxDurability. Active helmet chance,
    weapon condition, loaded ammo and extra armor drops survive the merge.
11. Existing loot tests remain meaningful: helper identity namespaces,
    visible/quest filtering, difficulty subset restrictions, armor-vs-weapon
    condition, and precise 8/1 expanded-quality fixture outputs.
12. Profile save/load/reset, undo/redo, selected group filtering, summaries,
    unavailable saved keys and conflict footprint cover the real control keys.
    Every output candidate identity must be checked against loaded data before
    exporting a Pak; old profiles must not target a moved row after an update.

`tests/test_trader_condition.py` currently asserts all parsed quality weights
are integers >=1 by extracting `Weight = (\d+)`. A correct fractional fix makes
this assertion fail because `0.025` is misread as `0`. Replace that assertion
with a numeric parser and a positive-finite invariant, plus explicit fractional
regressions. The same test's exact Recon Weight 400 and untouched Weight 1000
expectations remain valid. `tests/test_loot_extensions.py`'s expanded quality
fixture requires exact Weight strings `8` and `1`; both remain valid under the
minimal compatible model. Modscan tests inspect conflict identities rather
than intermediate price-rank rounding.

The unmodified baseline tests were executed during this audit:
`tests/test_loot_extensions.py` passed all 12 synthetic tests and
`tests/test_trader_condition.py` passed its live-data checks. Passing these old
tests does not cover the fractional defect or establish game behavior.

## Selected isolated-clone implementation

The separate scope audit supplies ordinary object identities and verified
generator-reference paths. This composition audit does not independently
establish those caller classifications. Given that identity boundary:

1. Construct the effective source generator from installed data and the complete
   active global/optional patch tree. The clone must include current quality,
   Variety additions, ammo and durability outputs before the new candidate
   percentage is applied. Recomputing just a raw vanilla row would silently
   lose already selected global behavior.
2. Clone only the selected generator path and necessary ordinary parent/helper
   links into stable namespaced identities. Rewire the audited ordinary object
   to its isolated root. The new editor must not add an individual Weight leaf
   to the original shared generator. Existing global settings may still patch
   that original according to their established scope.
3. Match a candidate by the verified original root/slot/row plus current
   ItemPrototypeSID. Keep the complete native PlayerRank and Diff restrictions.
   Change the matching cloned candidate only; do not propagate by SID to another
   slot or to a Variety addition copied from that item elsewhere.
4. Apply the requested multiplier to the final quality-adjusted candidate weight
   and retain fractions. No separate slot-quality control is necessary: the
   optional combined-factor model above reduces to `q = global_quality`.
5. Validate nonzero total Weight over the **entire effective target pool**,
   including permitted added candidates. A copied Variety alternative can keep
   a target valid when all editable original candidates are disabled. Disabling
   the last effective positive alternative is an error.
6. A neutral editor selection creates no clone, object relink or custom helper.
   When the only edited factor returns to 100%, remove the entire now-unused
   isolated path. Whole cloned definitions must contain the data needed for
   standalone operation; sparsity means no unused clone and only the selected
   ordinary relinks, rather than stripping required vanilla fields from a new
   definition.
7. Preserve any needed generated helper references. For example an active extra
   armor-drop option may have inserted a `S2Tweaker_Loot_*` helper in the source
   root; copying its reference without the helper definition creates a broken
   graph. Do not rewrite unrelated shared helpers as a shortcut to isolation.

Additional clone-specific tests: compare the full effective source and target
after ignoring identity/relink fields and the intended candidate Weight; assert
all other leaves match. Verify that named/story consumers of the original keep
their existing link and that inherited consumers are protected according to the
scope design. Assert every emitted custom reference resolves, a second profile's
namespace cannot collide, resetting removes all unused custom definitions, and
global-only behavior remains byte-for-byte unchanged except for the separately
tested fractional-weight defect fix. Test two selected pools sharing a parent,
two parents sharing a helper, and concurrent ammo/condition/Variety/armor-drop
settings to detect relink loss and duplicated helper generation.

## Warnings and implementation boundary

- `GeneralNPC_` plus the existing generic loot filter is not a complete quest,
  prologue or world-instance isolation guarantee. Shared callers must be audited
  separately before advertising “all ordinary NPCs only”.
- A pure Weight editor can change existing choices without adding equipment
  that does not belong to the pool. It cannot prove retroactive regeneration of
  already spawned NPCs or their inventories. This remains an in-game test.
- Keep native player-rank and difficulty groups intact. No promise of four
  independent NPC-rank settings when the CFG supplies a shared slot.
- Read every numeric baseline live. Static metadata may identify audited roots,
  slot/row keys and expected identities; no numeric baseline belongs in code.
- No new game-data extraction source is needed for this composition layer.

Conclusion: isolated per-original-candidate Weight factors are feasible while
retaining the existing global quality control, provided cloning preserves the
effective composed generator graph and ordinary caller isolation is verified.
The alternative per-slot quality calculation is documented above for future use.
Separate rank-slot generation, exact worn-armor drops, and immediate changes to
existing spawned NPCs are outside the verified model.
