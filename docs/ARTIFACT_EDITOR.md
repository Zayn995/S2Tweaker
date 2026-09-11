# Artifact editor and related settings (1.39.0)

Open **World → Artifact editor & related settings (experimental)**. Select a
family, then an item or profile, and click **Edit selected settings**. The
Overview shows only the controls supported by the loaded game data. Type a value
and click Apply or press Enter. Details shows the installed baseline and the
control's meaning. These settings support search, favorites, profiles, Pak
manifests, undo/redo and reset.

The current 2.0.5 snapshot provides 353 controls across five families. These additions are experimental and have not been play-tested.
They are included in version 1.39.0. No UE4SS, injector, Blueprint package
or new extraction input is required; cache schema remains unchanged.

| Family | Controls and scope |
| --- | --- |
| Artifacts | Weight and base price for 69 ordinary candidates; 114 existing bonus controls; native radiation selection on the 44 candidates that already have a harmful radiation effect. |
| Detectors | 14 supported radius controls across Echo, Bear, Gilka and Veles. Reveal, work and near-detection radii are separate. Only Veles has sonar/anomaly-detection radius controls. |
| Weird Ball | Seven specific damage/stamina/weight parameters, including separate dynamic weight bounds and weight decrease parameters. |
| Moving anomalies | Speed and pursuit distance for four electric/fire-ball variants. Speed scales base and artifact-influenced maximum speed together. |
| Rarity profiles | 28 enabled tier/rank controls across UniversalArtifactSpawner and LesserZoneMagneticShortDistance. Disabled tiers remain unavailable. |

Artifact rows use stable game-data identifiers because an English alias map has
not yet been verified. The 69 candidates are a conservative configuration scope,
not a guarantee that all are currently obtainable in ordinary play. Fake,
template, quest, prologue and special PSY variants are excluded from the ordinary
editor. Weird artifacts have their own specific controls.

## Defaults and global settings

- **Inherit / -1:** restores the existing global behavior for absolute item,
  detector and Weird Ball values. Explicit zero is a real setting where allowed.
- **100%:** leaves the corresponding individual bonus, anomaly or rarity weight
  unchanged. Individual bonuses multiply the global artifact-strength result.
- **Weight and base price:** explicit absolute values. Weight overrides the
  global item-weight result. Actual shop prices still depend on difficulty and
  trader multipliers.
- **Detector radii:** explicit distances in centimetres, overriding the selected
  detector's corresponding global result. Reveal and near-detection radii must
  fit within the final work radius. Passive scanners and quest detectors retain
  their existing global behavior.
- **Weird Ball:** raw absolute values. Dynamic minimum weight must not exceed
  dynamic maximum weight. These bounds differ from static inventory weight.
  The exact rate/amount timing needs gameplay measurement.
- **Rarity:** factors apply after the global rare-artifact bias, then all four
  tiers are normalized to their original combined weight. These are relative
  weights, not direct encounter probabilities. Keep at least one enabled tier
  above zero. An equal factor on every enabled tier cancels out.

Neutral settings produce no patch. Explicit values that cancel a prior global
item change remove that generated leaf. Unavailable controls are hidden unless
they contain a saved change or are favorited; they then remain visible as
inactive so they can be reset. Unknown or unsupported game definitions are never
patched by guessing.

## Individual bonuses and radiation

Each edited ordinary bonus receives a stable mod/item/effect-specific definition
derived from the original native effect. Only that item's existing effect-list
entry is replaced. Global artifact controls keep their existing scope; unedited
items sharing the original effect are unaffected by the new individual control.
Suffixes, effect types and native duplication behavior are preserved. Carry
capacity and penalty-free carry weight are separately configurable bonuses.
The maximum-durability bonus is not labelled as a weapon wear-rate modifier.

Radiation offers **-1 = Inherit, 0 = Off, 1–4 = native tier**. It deliberately
uses the original game effect identities; no custom harmful-radiation effect
is introduced. Native and tool-added lead containers can still reference the
selected effect. A higher native tier may need stronger shielding, and the
global radiation factor still changes that tier's magnitude. Off removes only
the selected harmful-effect entry and hides its existing display entry.
Arbitrary individual radiation magnitudes are outside this implementation.

Radiation-removal bonuses use a different sign of the `DegenRadiation` effect;
they are not armor radiation protection and do not use its protection cap.
The general protection/weight/stamina/bleeding cap controls remain separate.

Re-equip changed artifacts after updating a mod. Effect persistence, stacking
multiple copies, save/load and removing a mod with active effects require actual
gameplay validation; a successful export cannot establish those behaviors.

## Shared spawners and anomaly scope

UniversalArtifactSpawner is used in ordinary world placements and an E06_MQ01
quest-logic placement. The editor explicitly identifies this shared use. Changing
the prototype also affects those quest placements; it is not a quest-isolated
rarity editor. Existing artifacts may persist until the game generates another
spawn. No placement graph, list membership or quest exclusion rule is changed.

The four element-specific explicit-list spawners have zero rarity distributions
in this snapshot and are excluded from the new rarity controls. Template, demo,
quest-named and Weird spawners are also excluded.

The moving-anomaly controls exclude LightningBallPrologueAnomaly. They leave
damage, targeting flags, eating mechanics and other lifecycle fields unchanged.
The relation between these numeric fields and actual pursuit behavior remains
experimental.

## Validation boundary

Automated checks cover live data scope, neutral output, isolated bonus references,
global composition, native radiation selection, shielding references, exclusions,
constraints, number suffixes, profile/history/reset behavior and complete Pak
read-back. A separate single-window diagnostic exercises all five families,
editing, profiles, undo/redo, export and reset while measuring GUI resources.
The implementation prepared on 2026-09-11 passed all 52 local headless suites and all 13 CI suites
run locally, plus the portable runtime self-test, signature verification, the
single-window GUI diagnostic and byte-for-byte read-back of six generated Paks.
All five editor families were exercised. Peak GUI resources were 6,744 USER and
106 GDI objects. Packaged files are checked against the tested preview.
None of these checks is an in-game test.

Underlying evidence and exact baseline tables are linked from
[the research overview](ARTIFACT_EDITOR_RESEARCH.md).
