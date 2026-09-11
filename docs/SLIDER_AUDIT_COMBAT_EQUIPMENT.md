# Combat and equipment slider audit — 1.40.1

Research date: 11 September 2026. This is an audit of the released controls and
the locally extracted game data, not a new feature implementation or gameplay
test. All paths below are relative to the repository. Values describe this
snapshot; a future builder must resolve the installed values dynamically.

The useful next step is more precise scope and independent controls. Raising
the existing maximum factors adds little and does not solve animation limits.

## Existing coverage and boundaries

The weapon editor already has ten parameters with individual > category >
global precedence: damage, spread, recoil, durability, fire rate, effective
range, bleeding, ADS movement speed, aim-in speed, and magazine size. Caliber
selection is already individual. `gd.player_weapons()` returns 91 weapon setup
IDs, including 11 distinct edition setups; their availability filter yields
905 parameter/setup pairs. The actual GUI excludes the uncategorized
`MeleeStub`, leaving 90 setups and 897 visible individual parameter pairs.
These counts do not mean every listed setup has identical scope or behavior.

Ammo already has individual damage, armor piercing, armor damage, cover
penetration, stack size, bleeding, recoil, flatness, wear, dispersion and aimed
dispersion. Projectile speed and other global ballistic controls also exist.
Armor already has individual protection and a substantial absolute-value
editor: weight, price, durability, dimensions, artifact slots, radiation
shielding, sprint permission and other fields. Scopes have individual zoom and
penalty overrides. None of those should be advertised again as a new feature.

The relevant gaps are:

| Candidate | Current limitation | Useful extension | Effort / uncertainty |
|---|---|---|---|
| Reload detail and weapon scope | One global reload factor; edition-owned fields skipped; five of seven observed reload multipliers handled | Separate tactical, empty, single-round and paired-magazine timings; individual/category overrides; edition support | Medium implementation; animation behavior still needs gameplay tests |
| Separate movement states | Two factors each change three states | Independent walk, crouch, low crouch, run, jog and sprint overrides | Small implementation; existing animation/save-state limitations remain |
| Individual weapon item properties | Weapon factors do not expose individual item weight, base price or inventory dimensions | Item editor like the armor editor, initially weight/price/dimensions | Medium because item IDs, shared setups and special weapons need a clear scope |
| More precise upgrade strength | One handling factor changes eight effect types; one damage factor changes three | Separate aim-in, sway, ADS movement, draw/holster, recovery, capacity and penetration strengths | Medium; shared effects and composite UI descriptions must remain accurate |
| Condition window for malfunctions | Chance, difficulty multiplier and clearing time exist; condition thresholds remain untouched | Optional per-weapon high/low condition thresholds | Small data patch; higher semantic uncertainty because interpolation is an asset |

Source implementation: [`tweaks.py`](../s2tweaker/tweaks.py),
[`gamedata.py`](../s2tweaker/gamedata.py), [`gui.py`](../s2tweaker/gui.py),
[`armor_extensions.py`](../s2tweaker/armor_extensions.py),
[`faq.py`](../s2tweaker/faq.py).

## Source snapshot

Paths in this table are under `vanilla/Stalker2/Content/GameLite/GameData/`.
Counts include templates and special entries; they are not editable-item counts.

| File | Lines | Top-level structs |
|---|---:|---:|
| `ObjPrototypes.cfg` | 1,318,780 | 1,660 |
| `ItemPrototypes.cfg` | 92,232 | 1,375 |
| `WeaponData/WeaponGeneralSetupPrototypes.cfg` | 32,332 | 92 |
| `WeaponData/CharacterWeaponSettingsPrototypes.cfg` | 10,101 | 150 |
| `WeaponData/WeaponAttributesPrototypes.cfg` | 26,603 | 148 |
| `UpgradePrototypes.cfg` | 46,006 | 1,288 |
| `EffectPrototypes.cfg` | 85,869 | 2,426 |

Private reproducibility evidence is in `out/slider_audit_1401/combat/`:
`audit.py`, `audit.json`, `check_current.py`, and `current_checks.json`.
The JSON records hashes, all 91 setup chains, 131 slot-bearing weapon items,
raw values and defining owners. It also records the complete investigated
upgrade effect lists. Extracted game files remain private.

The files required for these five candidates are already available through
the game-data loader, including its existing optional edition support. No new
extraction file is identified by this audit. Any additional file introduced
during implementation would require a `CACHE_SCHEMA` bump.

## 1. Reload detail, individual scope and edition support

The current `RELOAD_KEYS` tuple has exactly five entries:

| Key | Existing coverage |
|---|---|
| `TacticalReloadTimeMultiplier` | Direct setup and attachment rows |
| `FullReloadTimeMultiplier` | Direct setup and attachment rows |
| `SingleBulletReloadTimeMultiplier` | Direct setup and attachment rows |
| `TwinReloadTimeMultiplier` | Direct setup and attachment rows |
| `TwinTacticalReloadTimeMultiplier` | Direct setup and attachment rows |
| `TwinAuxReloadTimeMultiplier` | Present in game data, absent from tuple |
| `TwinTacticalAuxReloadTimeMultiplier` | Present in game data, absent from tuple |

In the bounded AK74 example, every timing value below is explicitly defined
in the setup's own attachment row, rather than borrowed from a magazine item:

| Exact path | Live value | Current output at reload ×2 |
|---|---:|---:|
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].TacticalReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].FullReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].SingleBulletReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].TwinReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].TwinTacticalReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].TwinAuxReloadTimeMultiplier` | 1.0 | Unchanged |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[0].TwinTacticalAuxReloadTimeMultiplier` | 1.0 | Unchanged |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[1].TacticalReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[1].FullReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[2].TwinReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[2].TwinTacticalReloadTimeMultiplier` | 1.0 | 0.5 |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[2].TwinAuxReloadTimeMultiplier` | 1.0 | Unchanged |
| `GunAK74_ST.WeaponReloadTimePerAttachment.[2].TwinTacticalAuxReloadTimeMultiplier` | 1.0 | Unchanged |

Rows `[0]`, `[1]`, `[2]` identify `GunAK74_MagDefault`,
`GunAK74_MagIncreased`, `GunAK_MagPaired`, respectively. Row `[0]` also has
`UnloadTime=0.0`, which is not a reload multiplier and should remain untouched.
This proves a coverage discrepancy with the UI phrase "every reload-time
multiplier"; it does not prove how the auxiliary fields affect animation.

The direct path `GunM860_SG.SingleBulletReloadTimeMultiplier` is also `1.0`,
as are its direct tactical and full multipliers. The Deluxe setup
`Gun_Monolit_SG_GS` explicitly defines those same three values and its own
attachment row. Its inheritance chain is
`Gun_Monolit_SG_GS -> GunM860_SG -> TemplateShotgun -> TemplateWeapon`.
Therefore a base setup patch alone cannot establish consistent edition-owned
timings. In the current ×2 probe, the edition patch dictionary is empty.

Suggested behavior: retain the global factor as the inherited default, then
allow weapon-category and individual overrides, with an optional detail panel
for reload mode. A faster single-shell load should not necessarily make every
empty-magazine reload faster. The paired-magazine primary and auxiliary
timings need a deliberate combined default, with gameplay verification before
offering them independently.

Resolve attachment indices and inheritance from live data. Preserve the
attachment identity and other row members when constructing patches; do not
assume `[2]` always means a paired magazine. Keep stubs, story-only weapons and
launchers out of a new ordinary-gun preset. A general setup can also be shared
by NPC equipment and multiple item variants, so the scope must be displayed
honestly. A timing change does not retime a baked animation or its audio.

## 2. Independent movement states

These are the complete six values controlled by the two existing speed
factors. All six are explicitly present on `Player`, whose parent is `[0]`:

| Exact path in `ObjPrototypes.cfg` | Live value | Existing factor |
|---|---:|---|
| `Player.MovementParams.WalkSpeed` | 160 | `walk_speed_factor` |
| `Player.MovementParams.CrouchSpeed` | 190 | `walk_speed_factor` |
| `Player.MovementParams.LowCrouchSpeed` | 130 | `walk_speed_factor` |
| `Player.MovementParams.RunSpeed` | 370 | `run_speed_factor` |
| `Player.MovementParams.JoggingSpeed` | 625 | `run_speed_factor` |
| `Player.MovementParams.SprintSpeed` | 820 | `run_speed_factor` |

For example, current `run_speed_factor=1.1` emits all three values:
`RunSpeed=407.0`, `JoggingSpeed=687.5`, `SprintSpeed=902.0`. A sprint-only
override could emit just `SprintSpeed=902.0`. This enables faster traversal
without also changing ordinary movement. Crouching is currently tied to
walking even though the live crouch value, 190, exceeds the walk value, 160;
do not assume an ordered speed ladder or normalize these values.

Keep existing profile semantics by making the six detailed overrides inherit
the two current groups when absent. Patch only `Player`, not the shared base
`[0]` or NPC movement profiles. Backward speed, air control, limp speed,
ladder speed, vault parameters and individual stamina costs already exist.
Do not duplicate them.

The FAQ already documents community-reported animation desynchronization and
save-state caching. Separate controls improve precision; they do not fix
those engine/animation issues. In-game timing over a known distance and a
save/load check are still required before claiming an effective speed change.

## 3. Individual weapon item properties

The existing weapon cascade controls setup/combat properties. Weight,
category prices and grid size are global/category features; there is no
weapon equivalent of `armor_custom` for individual absolute values.

The four ordinary weapons selected below provide a complete bounded example.
Each value is explicitly defined on the corresponding `ItemPrototypes.cfg`
item; none of these twenty values comes from its template.

| Item SID | `.Weight` | `.Cost` | `.BaseDurability` | `.ItemGridWidth` | `.ItemGridHeight` |
|---|---:|---:|---:|---:|---:|
| `GunPM_HG` | 0.5 | 950.0 | 1500.0 | 2 | 1 |
| `GunAK74_ST` | 3.3 | 10000.0 | 1950.0 | 5 | 2 |
| `GunTOZ_SG` | 3.1 | 3000.0 | 2250.0 | 5 | 2 |
| `GunPKP_MG` | 6.8 | 30000.0 | 3000.0 | 6 | 2 |

For example, `GunAK74_ST.Weight` could be set to `3.0` independently, while
`GunAK74_ST.Cost` stays `10000.0`. This is a distinct use case from reducing
the weight of every weapon. `Cost` is a base price; difficulty, condition,
reputation and trader multipliers still contribute to actual trade prices.

Start with weight, price and the two inventory dimensions. Durability can be
a later option because existing item condition is stored in saves and must
not be described as instantly repairing carried weapons. The current
weapon cascade durability factor changes wear per shot; a separate global
`gear_durability_factor` already changes maximum durability. Only an
individual absolute maximum would extend that existing coverage, and its
interaction with the two current factors would need explanation.

The inventory helper returns 131 slot-bearing weapon items, which is not a
ready-made safe scope: it includes guards, melee stubs/shovels and special
story equipment. `Gun_SkifGun_HG` is explicitly marked as a quest item in this
set. Check both `IsQuestItem` and `IsQuestItemPrototype` through inheritance;
absence of those markers alone does not establish ordinary loot. `Invisible`
is `false` on all 131, so visibility cannot exclude the special entries.

Use item IDs for these properties, not `GeneralWeaponSetup` IDs: several
items share a setup, and some unique items have distinct player attribute
chains. Existing named weapons and edition variants need deliberate handling.
On the four examples above, both `PlayerWeaponAttributes` and
`NPCWeaponAttributes` exist. Changing an item prototype can affect every copy
of that item, including NPC or vendor copies, not only the owner's inventory.
Changing base price may also affect any generator selection based on price.

## 4. Split upgrade strengths by useful effect

`_upgrade_strength_patch` already scans effects referenced by technician
upgrades and applies nine family factors. This candidate adds detail within
families, not a second global upgrade-strength slider. All strengths below
are raw `EffectPrototypes.cfg.<EffectSID>.ValueMin` and `.ValueMax`; min and max
match in every listed value group.

Complete value groups for the two investigated families:

| Effect type | Referenced effect IDs | All raw values present | Existing family |
|---|---:|---|---|
| `AimingTime` | 6 | `-5%`, `-7%`, `-10%`, `-15%`, `10%`, `15%` | Handling |
| `AimingMovementSpeed` | 5 | `10%`, `12%`, `15%`, `20%`, `30%` | Handling |
| `IdleSwayXModifier` | 3 | `-10%`, `-15%`, `-20%` | Handling |
| `IdleSwayYModifier` | 3 | `-10%`, `-15%`, `-20%` | Handling |
| `ShowEquipmentTime` | 4 | `15%`, `20%`, `25%`, `30%` | Handling |
| `HideEquipmentTime` | 4 | `15%`, `20%`, `25%`, `30%` | Handling |
| `RecoilRadiusNormalizationInterval` | 3 | `-10%`, `-15%`, `-20%` | Handling |
| `AmmoCapacity` | 2 | `50.0`, `50%` | Handling |
| `BaseDamage` | 4 | `-10%`, `15%`, `20%`, `28%` | Damage |
| `ArmorPiercing` | 8 | `10%`, `12%`, `15%`, `20%`, `25%`, `30%`, `50%`, `100%` | Damage |
| `CoverPiercing` | 8 | `10%`, `12%`, `15%`, `20%`, `25%`, `30%`, `50%`, `100%` | Damage |

There are 30 referenced effects in the handling family. Two `AimingTime`
entries are penalties and the current builder correctly leaves them alone.
The damage family contains 20 referenced effects, including one damage
penalty that likewise remains untouched.

Concrete current-output checks at handling ×2:

| Exact effect paths, each with `.ValueMin` and `.ValueMax` | Live | Current ×2 |
|---|---:|---:|
| `AimingTimePos15Effect` | `-15%` | `-30.0%` |
| `WeaponWithdrawPos20ShowEffect` | `20%` | `40.0%` |
| `AmmoCapacityIncrease` | `50.0` | `100.0` |
| `AmmoCapacityIncrease1` | `50%` | `100.0%` |
| `AimingTimeNeg10Effect` | `10%` | Unchanged |

Thus selecting stronger aim-in upgrades currently also changes capacity and
draw speed. Independent values would allow stronger aim-in or penetration
without changing those other bonuses. Preserve literal units: `50.0` and
`50%` are not interchangeable. Do not infer bonus direction from names alone.

Global effect edits affect all upgrades using that effect. For example,
`AimingTimePos10Effect` is directly referenced by 42 upgrades. Across all
upgrades, 57 referenced effect IDs also occur in direct item effect lists;
this is a conservative direct-reference intersection, not a full inherited
consumer graph. The positive `AimingTimeNeg10Effect` penalty is shared with
paired magazines and must remain untouched by bonus controls.

A per-stat global override is feasible with the existing effect family
approach. A true per-weapon technician-upgrade editor is substantially larger:
it needs cloned effect references or another proven isolation mechanism, plus
an audit of composite effects and upgrade descriptions. A composite containing
children changed by different factors cannot truthfully display one scaled
percentage. Do not silently rewrite all users of a shared effect to satisfy
one selected gun.

## 5. Malfunction condition thresholds

The game has two condition threshold fields next to its existing chance
fields. The current builder intentionally leaves them alone. Across all 91
setup IDs returned by `gd.player_weapons()` (including the GUI-excluded
`MeleeStub`), the complete distributions are:

| Field | Values and counts |
|---|---|
| `MinJamDurabilityThreshold` | `0.6` ×1, `0.65` ×2, `0.7` ×19, `0.75` ×65, `0.8` ×4 |
| `MaxJamDurabilityThreshold` | `0.05` ×9, `0.1` ×78, `0.15` ×4 |

Complete values for the four bounded ordinary-gun examples, all defined on
the setup itself in `WeaponGeneralSetupPrototypes.cfg`:

| Setup SID | `.MinJamChance` | `.MaxJamChance` | `.MinJamDurabilityThreshold` | `.MaxJamDurabilityThreshold` |
|---|---:|---:|---:|---:|
| `GunPM_HG` | 0.0 | 8.0 | 0.7 | 0.1 |
| `GunAK74_ST` | 0.0 | 4.0 | 0.7 | 0.1 |
| `GunTOZ_SG` | 0.0 | 15.0 | 0.75 | 0.1 |
| `GunPKP_MG` | 0.0 | 2.0 | 0.75 | 0.05 |

The apparent meaning is an upper/lower condition window used by the jamming
calculation. This is an inference from field names and neighboring values,
not a verified formula. Every one of the 91 setups resolves to the same
`WeaponDurabilityCurve` asset reference. The actual curve is not represented
as editable numeric CFG points in this audit.

A useful optional feature would let the owner delay the condition range in
which malfunctions grow, without disabling malfunctions entirely. Keep the
two condition values ordered (`MaxJamDurabilityThreshold` below
`MinJamDurabilityThreshold`) and within `[0,1]`, resolving per-gun defaults.
Do not present a predicted jam probability, and do not replace the referenced
curve with guessed data. Existing difficulty jamming, raw chance, wear and
clearing time remain separate controls.

The wider inventory contains important outliers: `GunRpg7_GL` has
`MaxJamChance=50.0`, while the PKP/Korshunov/Tank setups have `2.0`.
`Gun_Lummox_AR_GS` has nonzero `MinJamChance=0.2`. The old general UI wording
"4.5 to 15" is therefore not an exhaustive range for this snapshot. This
reinforces the need for live values and a narrower ordinary-firearm scope.

## Implementation boundaries and priority

1. Prioritize independent movement states and individual weapon item
   weight/price/dimensions: their data mapping is straightforward and their
   user benefit is easy to explain.
2. Expand reload scope/modes as one coherent change, including edition data
   and the paired-magazine auxiliary fields. Correct the universal coverage
   wording when doing so; actual animation behavior still requires testing.
3. Add per-stat upgrade overrides with explicit inherited values, retaining
   the existing family controls and bonus-only sign checks.
4. Keep malfunction condition thresholds experimental until condition-level
   gameplay comparisons establish their behavior.

No production code, presets, installed mods, version metadata or GitHub state
were changed for this audit. Current builder probes confirm the existing
output and neutral weapon output `({}, {})`; they do not test any proposed
new implementation. No new Pak was installed or game session run.
