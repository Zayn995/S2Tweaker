# Individual artifacts and related feature research

Implementation follow-up: [artifact editor implementation](ARTIFACT_EDITOR.md).
The audit below records the evidence and decisions made before that implementation.

Audited against the local Steam 2.0.5 configuration snapshot on 2026-09-11.
This document records available fields and design constraints before implementation.
No new controls, game modifications, release, or in-game verification are part of
this research. Baselines in the tables describe this snapshot; application code
must obtain the installed values through `gd.resolve(...)`.

## Findings and proposed order

1. **Individual artifact editor:** separate weight, base price and selected
   ordinary effect adjustments. Start with the 69 ordinary candidates listed in
   the item appendix; that count does not establish that every candidate is
   obtainable in normal play. Effects require item-specific references because
   many artifacts share the same effect definitions.
2. **Individual detector editor:** separate detection/work distance and artifact
   reveal distance for each supported detector. The existing global range control
   changes several distances together and also affects passive scanners.
3. **Special artifact controls:** the Weird Ball has its own damage-to-weight,
   damage-to-stamina and weight-recovery settings. These are distinct from the
   existing shared Weird Flower duration / Weird Bolt charge control.
4. **Moving anomaly controls:** selected electric/fire-ball anomaly prototypes
   expose pursuit range and movement speed. This is an adjacent gameplay option,
   not an artifact effect. Prologue and unknown special variants need exclusions.
5. **More precise artifact spawn settings:** some profiles have usable rank-based
   rarity distributions; element profiles instead use explicit lists with zero
   rarity weights. A universal per-element rarity slider is not established by
   those zero-valued fields. Keep the two selection mechanisms separate.

These are candidates for native configuration patches. No UE4SS dependency is
proposed. In-game behavior, save/reload handling and coexistence with other mods
remain separate verification steps.

## Complete evidence tables

- [Item inventory and all selected item baselines](ARTIFACT_ITEM_BASELINES.md):
  all 154 classified roots, field ownership, effect-list indices, fake and special
  exclusions, and the complete selected-field baseline CSV.
- [Effect graph and baseline audit](ARTIFACT_EFFECT_RESEARCH.md): direct and
  nested effect references, shared users, effect values, caps, radiation shielding
  and special-artifact dependencies.
- [Detectors, special artifacts, spawners and moving anomalies](ARTIFACT_ADJACENT_RESEARCH.md):
  exact candidate paths, complete selected-field tables and existing/new scope.

## Primary source inventory

Paths below are relative to `vanilla/Stalker2/Content/GameLite/GameData/`.
Counts are from decoded text, not `.cfg.bin` byte streams.

| File | Lines | Top-level structures | Already requested by the application |
| --- | ---: | ---: | --- |
| `ItemPrototypes.cfg` | 92,232 | 1,375 | Yes |
| `EffectPrototypes.cfg` | 85,869 | 2,426 | Yes |
| `ObjEffectMaxParamsPrototypes.cfg` | 48 | 2 | Yes |
| `ArtifactSpawnerPrototypes.cfg` | 6,848 | 98 | Yes |
| `AnomalyPrototypes.cfg` | 1,225 | 28 | Yes |
| `CoreVariables.cfg` | 1,439 | 4 | Yes |

The item appendix also checks the three extracted edition item files: no artifact
entries were found there. The effect appendix records the scope of its additional
reverse-reference audit. No extraction list or cache schema change was made.
If later work needs another file, add it to `NEEDED_FILES` and raise `CACHE_SCHEMA`.

| File | SHA-256 of the audited decoded text |
| --- | --- |
| `ItemPrototypes.cfg` | `95693d7b27c16de9155076caa191fcd54892393e3f93423bb08f5579880ed829` |
| `EffectPrototypes.cfg` | `ced30a0fc589f06f07960175b48612ee6d055cfe7a0a14c8f190bd16853ecabf` |
| `ObjEffectMaxParamsPrototypes.cfg` | `92f8fe887299a7f1f6272705b215cf607be4e622835a60a1f110fc70e80aa44f` |
| `ArtifactSpawnerPrototypes.cfg` | `4abdbc14d5741cfac6228a81d7a5dd65e3ce68fcfd42b873958a250885cd57c8` |
| `AnomalyPrototypes.cfg` | `096432472088c7a01d94b49626d7f8d27f000160a1f124897368cc68d1664ced` |
| `CoreVariables.cfg` | `294a19c981b601505234e7c798b9cf5c4aa632b3f50c8731a105484c018ade55` |

## Scope: 154 configuration roots are not 154 ordinary artifacts

The existing template-chain classification finds 154 roots. Only 153 have
`Type = EItemType::Artifact`: `TemplateQuestArtifact` has type `Info` despite
its artifact-related inheritance. Both independent item inventories agree.

| Group | Count | Proposed initial treatment |
| --- | ---: | --- |
| Ordinary C/E/F/G artifact candidates | 69 | Allowlist candidates; verify availability and behavior separately |
| Special PSY variant `PArtifactBrain` | 1 | Exclude initially; own spawn mechanism and Night Star localization reference |
| Fake artifact variants | 71 | Exclude; not extra ordinary artifacts |
| Weird archiartifacts | 6 | Separate specific controls, not the ordinary effect editor |
| Quest or prologue items | 5 | Exclude |
| Templates | 2 | Exclude from the item selector |
| **Total** | **154** | |

The selected scalar fields, where present, are explicitly repeated on the items
in this flattened snapshot. A change to `TemplateArtifact.Weight` alone would
not override each descendant's own `Weight`. Use per-item paths.
`refurl` strings and local `refkey` resolution must not be assumed equivalent
for every future extraction; validate the loaded shape before exporting.

No artifact display-name map currently exists in `s2tweaker/names.py`.
`LocalizationSID` is a key, not a verified English translation. A future selector
must preserve an SID fallback until names are verified; fake copies often point
at their real counterpart's localization key.

## What the tool already provides

| Existing feature | Current implementation | What would be new |
| --- | --- | --- |
| Global artifact effect strength and radiation | `tweaks._effects_patch`, `artifact_effect_factor`, `artifact_radiation_factor` | An individual item's effect choice or adjustment |
| Category weight and artifact economy factor | Item weight handling and `artifact_price_factor` | Independent item `Weight` and raw `Cost` |
| Spawn chance, count, cooldown and rare bias | `tweaks._artifact_spawner_patch` | Explicitly scoped profile/rank controls where the native mechanism is audited |
| Artifact visibility without detector and hopping controls | `tweaks._artifact_behaviour_patch` | These are already present; do not advertise them as new |
| Detector and scanner range | `detector_range_factor` | Per-detector controls with reveal/work distances separated |
| Weird Flower/Bolt duration and charge; permanent Flower effect | `_weird_artifact_patch` and optional world extensions | Other independently audited special fields, including Weird Ball |
| Extra slots and shielded armor slots | Armor controls and `armor_extensions` | Not a new artifact-editor feature; must remain compatible |
| Protection, stamina, bleeding and weight caps | `_effect_max_patch` | Caps are already controlled; a comparison display would be new UI only |

Existing global effect scope is name-based (`Artifact*`), which is not identical
to the ordinary-item allowlist. Do not reuse that broad scope for an individual
artifact selector. The effect audit also identifies the Weird Kettle consumable
dependencies hidden behind that prefix.

## Patch design constraints

### Simple item fields

An individual item's exact paths include `EArtifactFlash.Weight` and
`EArtifactFlash.Cost`. Its two native effect slots are
`EArtifactFlash.EffectPrototypeSIDs.[0] = ArtifactProtectionShock1` and
`EArtifactFlash.EffectPrototypeSIDs.[1] = ArtifactAddRadiation1`.
Preserve unrelated fields and the ordering of effect-display metadata.

Resolved values must be compared with the final combined output. Untouched
controls produce no patch. Explicit individual values should have a documented
priority over global item multipliers, matching the existing armor editor.
Cost remains an item base value: game difficulty, trader factors and other
economy settings can change actual buying and selling prices.

Hand calculations for later patch verification against this snapshot:

| Path | Baseline | Example operation | Expected raw target |
| --- | --- | --- | --- |
| `EArtifactFlash.Weight` | `0.3` | Multiply by 0.5 | `0.15` |
| `EArtifactFlash.Cost` | `12000.0` | Multiply by 1.5 | `18000` |
| `ArtifactProtectionShock1.ValueMin` / `.ValueMax` | `10` / `10` | Multiply by 1.5 | `15` / `15` |
| `ArtifactAddRadiation1.ValueMin` / `.ValueMax` | `-0.1` / `-0.1` | Multiply by 0.5 | `-0.05` / `-0.05` |

The effect rows demonstrate arithmetic only. Patching those original shared
effect SIDs would change every user, so that is not an individual-item solution.
No patch was emitted for these examples.

### Shared effects and radiation shielding

The current artifact-classified roots contain 419 direct effect references to
58 unique definitions. Following the two child references of Weird Water brings
the reachable set to 60 definitions. Do not interpret 419 as a count of distinct
effects or 60 as a count of independently adjustable ordinary bonuses.

For ordinary numeric effects, a possible design is a deterministic namespaced
effect definition plus replacement of the chosen item's existing effect-list
reference. Definition creation and ordinary `{bpatch}` edits are different
operations. The existing armor composites demonstrate how the writer represents
new native structures, but do not prove arbitrary cloned-effect behavior in game.
Preserve signs, raw units, effect type, duplication behavior, permanence and
unrelated metadata. A negative value is not a generic indication of a benefit:
the radiation side-effect definition here uses `DegenRadiation` with `-0.1`.

Radiation is a separate compatibility problem. Native lead-container effects
explicitly enumerate `ArtifactAddRadiation1` through `ArtifactAddRadiation4` in
`EffectsToBlockIDs`, with different subsets for different blockers. A new
radiation SID is not present in those lists. Cloning it and assuming that lead
containers still work would be unjustified. Keep native radiation references
in an initial benefit editor, or separately audit native-tier selection/removal
and the full shielding integration before offering arbitrary radiation scaling.
Selecting a different native tier keeps recognized identifiers, but intentionally
changes which partial lead containers block it. Four tutorial conditions also
refer to the original radiation SIDs, so shielding is not the only consumer.

The beneficial `ArtifactProtectionRadiation*` effects are also of type
`DegenRadiation`, using positive values. They remove radiation; they are not the
armor's `ProtectionRadiation` stat and must not be presented as subject to its
85-point cap.

Do not recursively clone unknown conditional graphs, ValueProviders, curves,
Blueprint behavior or consumable overrides merely because the name contains
`Artifact`. New names may also alter effect stacking and saved effect identity.

### Caps and comparison ideas

There are ten cap entries in this snapshot. Their complete table is in the effect
appendix. A future artifact comparison view could show item values and cap-aware
warnings, but a sum of config values is not a verified prediction of final player
stats. Armor, upgrades, slot blocking, effect duplication rules and dynamic special
artifacts also contribute. A full loadout calculator needs its own gameplay audit.

## Warnings and exclusions

- Preserve quest, prologue, fake, template and unknown special items. Ordinary-
  looking names and an artifact template chain alone are insufficient filters.
- Do not relabel `Radius` as detector reveal distance. Detector
  `ShowArtifactRadius` is a separate field; artifact `Radius` semantics remain
  unverified.
- Do not offer `LifeTime` as an inventory-expiration setting. Its runtime meaning
  has not been established. Avoid `Persistent`, `ArtifactSpawn`, type changes and
  other lifecycle fields in the first editor.
- Zero-valued spawn rarity weights may accompany explicit artifact lists.
  Multiplying zeros does not establish an effective rarity control. Do not enable
  previously absent tiers or add quest items as a side effect of a global preset.
  `UniversalArtifactSpawner` is also placed in an `E06_MQ01` quest logic level;
  changing its prototype cannot be advertised as isolated from quest placements.
- Shielding, saved active effects and mod conflicts must be checked when changing
  effect references. Sparse patches do not guarantee compatibility with another
  mod that changes the same list indices or definitions.
- Several Weird artifacts are partly implemented through their specialized
  behavior or other items. A short effect list does not imply a simple artifact.
  Weird Bolt declares charge fields while `bUseCharge=false` in this snapshot;
  field presence alone does not establish that a charge tweak is active.

## Handoff to implementation

The recorded item fields, effect definitions and references, caps, detector fields,
Weird Ball fields, moving-anomaly fields and all 392 spawner-rank records were
reconciled against the parsed sources in an independent pass. All 19,900 lookups
agreed, including checks for absent fields and overlapping reference checks.
Source counts were also cross-checked. This validates transcription and scope;
it does not test a new application feature or game patch.

The most direct next work is an individual item selector with live weight/base
price and a deliberately limited ordinary-effect editor. Per-detector reveal/work
range controls are a smaller independent extension. Weird Ball and pursuit
settings have concrete fields but need individual gameplay validation.

Use the `add-tweak` workflow when implementation is requested. Validation should
cover neutral output; global/individual priority; exclusion of all nonordinary
items; shared-effect isolation; suffix/sign preservation; ordered effect metadata;
profile/history/reset behavior; and Pak read-back. Any radiation extension also
needs lead-container coverage and actual equip/unequip/save/reload tests.
No claim of gameplay success follows from this configuration audit.
