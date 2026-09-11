# Control inventory and extension priorities — 1.40.1

Audit date: 11 September 2026. Baseline: released S2Tweaker 1.40.1 at
`fc90e3cfcddf06ad925b9439b451ae268d6e4570`, with the local 2.0.5 game-data
snapshot. The release is [published as a regular release](https://github.com/Zayn995/S2Tweaker/releases/tag/v1.40.1).
This subsequent audit changes no application code or installed mod. Candidate
fields have been checked against extracted data; their new gameplay effects
have not been tested.

The strongest next additions are independent controls for special artifacts,
individual medicines and buffs, movement states, and weapon reload modes.
Several broad settings currently change different effects together. Adding
detail within the existing editors would give users more useful control.

## Complete current inventory

The [CSV inventory](SLIDER_INVENTORY_1_40_1.csv) records each setting's tab,
scope, key, label, range, step, neutral value and current availability. It
contains 5,573 registered setting rows, of which **5,396 are available** in
this installation: 5,344 numeric editor values and 52 tweak checkboxes.

These are possible editable values, **not thousands of simultaneously rendered
sliders or distinct gameplay mechanisms**. Repeated per-weapon parameters,
collapsed editors, number entries and numeric inherit/yes/no selectors are
included. Separate UI selectors are listed below and excluded from this sum.
Counts can change with installed edition content and future game updates.

### Main controls

There are **350 main sliders and 45 main tweak checkboxes**, before weapon
category controls and optional editors. Category names follow the physical UI.

| Tab | Sliders | Checkboxes | Existing coverage |
| --- | ---: | ---: | --- |
| Player | 14 | 0 | Core player values and stamina costs by action |
| Vaulting | 50 | 13 | Climbing, camera/HUD, movement, sleep, recovery, saves and interaction reach |
| Weight & items | 6 | 3 | Weight and inventory rules |
| Combat | 18 | 1 | Global combat and damage-related factors |
| NPCs & AI | 85 | 4 | Population, spawns, camp needs, perception, combat, cover, targeting and wounded behavior |
| Mutants | 15 | 3 | Global mutant settings, smell, Bloodsucker and Burer behavior |
| Factions | 3 | 1 | Reputation mechanics; individual relationships are counted below |
| Weapons | 35 | 4 | Global weapon factors, handling, aim assist and pistol slot |
| Ammo | 12 | 0 | Global ammunition and ballistic factors |
| Armor | 15 | 2 | Protection, condition and grenade interaction |
| Upgrades | 12 | 3 | Technician rules, upgrade effect families and scopes |
| World | 63 | 6 | Artifacts, survival, loot, travel, sky/night, bodies and weather |
| Economy | 17 | 2 | Prices, fees and trader economics |
| Traders | 5 | 3 | Wallet, buying and stock |
| **Total** | **350** | **45** | |

### Detail controls and selectors

| Editor / scope | Available numeric values | Meaning |
| --- | ---: | --- |
| Weapon categories | 80 | Eight categories, ten parameters each |
| Individual weapons | 897 | 90 categorized weapon setups; availability varies by parameter |
| Individual ammo | 338 | 34 ammunition entries |
| Individual armor protection | 317 | Available protection types across 57 armor/helmet entries |
| Armor item properties | 986 | Absolute values and inherit/yes/no selectors across those entries |
| Individual scopes | 31 | Available zoom/handling values across 17 entries; physically under Upgrades |
| Individual mutants | 82 | Available parameters across 17 species |
| Faction relationships | 91 | 13 player relationships and 78 faction pairs |
| Artifact editor | 871 | Artifacts, extra bonuses, detectors, Weird Ball, moving anomalies and rarity profiles |
| NPC equipment editor | 1,028 | Existing faction/role/rank equipment choices |
| Regional weather editor | 188 | Native supported region/weather entries |
| Other optional world controls | 85 | Remaining extension, surface, weather and mutant-loot values |

The optional editors also contain seven tweak checkboxes, making **52** with
the 45 main switches. The UI separately has **90 caliber dropdowns** and
**eight weight-category filter checkboxes**. Navigation, profiles, favorites,
design choices and debugging buttons are outside the setting-row total.

The CSV keeps 177 unsupported optional rows with `available=False`: 113
artifact rows and 64 regional-weather rows. Those are registered identities,
not missing working sliders. Source-field and zero-baseline availability rules
must continue to be respected.

The raw weapon helper returns 91 setups / 905 parameter pairs. Its additional
`MeleeStub` has no category and is excluded by the actual GUI population code;
the inventory therefore uses 90 / 897.

## Recommended extensions

Every proposal below extends a gap verified against current code. None needs
UE4SS for the scoped CFG design. Static data availability does not establish
runtime behavior; precise limits and required game checks are in the detailed
reports linked below.

| Priority | Extension | Concrete benefit | Scope and implementation limit |
| --- | --- | --- | --- |
| 1 | Weird Nut: benefit and drawback separately | Adjust bleeding protection without tying it to the healing drawback | Two existing equipped effects; use item-specific references. The raw modifier is not a proven final healing percentage. |
| 2 | Weird Water: capacity and minimum intoxication separately | Adjust its capacity benefit while choosing the separate minimum-intoxication value | Keep both weight effects consistent and compose with existing carry settings. A zero minimum does not prove all intoxication disappears. |
| 3 | Individual medicine/buff editor | Stronger bandages, different medkit healing/bleeding removal, longer Hercules or PSY-Block | Start with eight medical/buff items. Clone shared effects where needed; distinguish healing delivery time from an ongoing buff duration. |
| 4 | Movement states separately | Faster sprinting while retaining ordinary running or crouching speeds | Six explicit player fields currently share two factors; detailed values inherit the existing groups. Animation limits remain. |
| 5 | Reload by weapon/category and reload mode | Change one shotgun or tactical reloads independently | Complete edition and auxiliary multiplier coverage at the same time. Animation and audio still need focused game checks. |
| 6 | Weather perception separately | Make rain affect hearing more strongly without also changing sight | Six native weather rows with 18 sight/hearing/scent coefficients. The shared AI table also affects users outside ordinary human NPCs. |
| 7 | Individual weapon item properties | Change one weapon's weight, base price or inventory dimensions | Use item IDs, which are different from combat setup IDs. Filter story/stub items and account for shared copies. |
| 8 | Camp activities separately | More guitar or conversations without equally increasing sleep, food or smoking needs | Eight activity types; a bounded pilot covers 88 existing entries in 12 ordinary faction presets. These are need rates, not guaranteed performance frequency. |
| 9 | Grenade budgets by group/rank | Give novice and veteran opponents different grenade budgets | Three native ordinary groups × four ranks. Preserve zero budgets and exclude the boss's negative sentinel; do not advertise separate control of every faction. |
| 10 | Selective helmet chances | Tune optional helmets for an existing faction/role/rank route | 23 existing helmet chance rows; extend the established equipment clone/relink system. Global helmet chance already exists. |
| 11 | Upgrade effects separately | Strengthen aim-in or penetration upgrades without also changing magazine capacity or draw speed | Existing handling strength groups eight effect types. Keep penalties untouched and descriptions consistent for composite/shared effects. |
| 12 | Passive anomaly warning and search range separately | Tune the anomaly beeper independently of the search scanner | Two ordinary roots already have independent radii. Keep the quest collar scanner outside the new detail controls. |

For an artifact-focused next update, start with **Weird Nut and Weird Water**.
The next broadly useful feature is the **individual medical/buff editor**.
Independent movement is a smaller addition with a particularly clear mapping.
Reload coverage and detail belong together in a focused weapon change.

## Findings to correct with the next relevant change

1. **Reload coverage:** the current reload tuple covers five of seven observed
   timing multipliers. An AK74 reload ×2 probe halves the handled paired-magazine
   fields while both auxiliary fields stay at their native values. The probe
   also produces no edition-owned reload patches. This is a confirmed data
   coverage gap behind the current “every reload-time multiplier” wording;
   an actual animation failure has not been demonstrated. See the
   [combat audit](SLIDER_AUDIT_COMBAT_EQUIPMENT.md).
2. **Scope category metadata:** `workbench_ui.TREE_TABS` maps
   `scope_overrides` to `Ammo`, while `gui.App._build_body` creates the scope
   editor under `Upgrades`. `_wb_register` uses that mapping and the details
   dialog's “Open category” button uses the resulting tab. Correct the mapping
   when revisiting the overview; the CSV records the physical `Upgrades` tab.
   This finding follows the code path and was not separately clicked in the GUI.

Neither finding was changed as part of this research-only follow-up. The
regular release's automated and GUI export checks remain recorded separately;
they are not evidence that every game mechanic was play-tested.

## Lower-priority research

- **Malfunction condition thresholds:** two fields provide a possible upper/lower
  condition window, but the actual interpolation is in an asset. Do not promise
  an exact jam probability from CFG names alone.
- **NPC bursts and pauses by rank/distance:** three full example profiles are
  documented; a broader consumer/inheritance audit is needed because named and
  guard weapon profiles share parents.
- **Food/drink penalties:** individual alcohol and hunger effects are promising.
  Stamina-percentage endpoints, quest descendants and alternative effect lists
  need separate treatment. Energy-drink tolerance/overuse remains deferred.
- **Moving-anomaly pursuit memory:** target-lost delay is exposed in the data;
  artifact-count sensitivity and carried/equipped detection semantics need
  runtime evidence before becoming user promises.
- **NPC night-vision equipment:** 47 generation chance entries exist. These prove
  equipment choices, not improved NPC vision, and their selection semantics need
  further research.

Existing detector detail controls, Weird Ball, artifact rarity, additional
artifact bonuses, NPC equipment selection, regional weather, loot additions
and upgrade rules should not be proposed again as new features. The raw
artifact-radius setting, Weird Bolt charge fields and the Weird Kettle flag
do not justify stronger claims or larger slider maxima. Bullet Time remains
deferred under the existing UE4SS compatibility decision.

## Implementation approach

Keep the current broad controls and profiles usable. Add optional detail
panels to the existing editors, with a clear inherited default, final-value
preview, reset, undo/redo and profile persistence. Specify whether each detail
value replaces or scales its parent; never silently apply the same factor twice.
Weapon detail should retain individual > category > global precedence.

Resolve values and array identities from the installed data, preserve units,
sentinels, attributes and inheritance, and emit only real deviations. Do not
make an unavailable or native-zero feature appear by guessing game values.
All currently scoped candidates use already extracted CFG files. Any new
required file discovered during implementation still requires a cache-schema
increment. No existing gameplay-confirmed status transfers automatically to a
new control.

## Evidence and method

- [Artifact, detector and consumable audit](SLIDER_AUDIT_ARTIFACTS.md): complete
  bounded field tables, effect links, live values and known limitations.
- [Combat and equipment audit](SLIDER_AUDIT_COMBAT_EQUIPMENT.md): reload output
  probes, movement fields, item/setup distinctions and upgrade effects.
- [World and NPC audit](SLIDER_AUDIT_WORLD_NPC.md): activity inheritance,
  weather coefficients, grenade budgets, equipment chances and firing profiles.
- [Full CSV inventory](SLIDER_INVENTORY_1_40_1.csv): all registered entries,
  including explicit availability flags.

The inventory parses actual GUI declarations and checks their identities
against `SLIDER_FIELDS` / `CHECK_FIELDS`, expands the encounter loop, and uses
extension availability checks. Individual values come from the actual GUI
population methods with tree rendering disabled and from the live scope helper.
It does not estimate individual control counts by multiplying every item by
every possible parameter. Local scripts and machine-readable results are under
`out/slider_audit_1401/`; extracted game sources remain private.
