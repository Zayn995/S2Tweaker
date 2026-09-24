# Consumable action timing research

Status: verified configuration, SDK asset/audio metadata, editor notify
inspection and a bounded native-action comparison in Zone Kit PIE. Drinking
at 100% and 150% preserved single consumption and normal completion; both
paired montage rates matched the selected speed. Sound-controller parameters
were observed, but audible alignment and packaged campaign play remain
unverified. No native animation or sound media is included.

## Desktop and profile integration

The desktop editor has separate experimental medicine, eating and drinking
speed controls under World. Their settings fields are
`consumable_medicine_speed`, `consumable_food_speed` and
`consumable_drink_speed`. Each defaults to 1.0, accepts finite numeric factors
from 0.25 to 4.0, and emits its `action.consumable.medicine`,
`action.consumable.food` or `action.consumable.drink` profile key only when
changed. Slider steps are five percentage points; direct entry permits finer
values. They request the companion independently of movement or weapon-sound
checkboxes and never patch `InventoryActionTime` or effect strength/duration.

Profiles can be prepared before the new runtime is packaged. Installation and
portable/debug export require the bundled runtime manifest to advertise
`consumable-actions`; older bundles reject changed consumable speeds instead
of silently accepting unsupported profile keys. This routing check is not
proof of native behavior. The shipped runtime's actual capabilities and the
remaining action/audio validation must be checked separately before release.

## Configuration scope

The installed `vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg`
contains 92,232 lines and 1,375 top-level structs. Of these, 24 resolve to
`Type = EItemType::Consumable`: one template, one guitar entry and 22 food or
medicine entries. The SDK source
`Stalker2/Content/GameLite/GameData/ItemPrototypes/ConsumablePrototypes.cfg`
contains 768 lines and 21 top-level structs. Three additional quest variants
are flattened into the installed item catalog.

All 24 entries resolve `InventoryActionTime` to `3.0`. This is a configuration
duration, **not evidence that every visible use montage lasts three seconds**.
The existing **Inventory action speed** control already divides this field by
its selected factor. Do not apply that same factor a second time without
checking whether native action playback already uses it.

| Item SID | Consumable type | Parent | Quest item |
| --- | --- | --- | --- |
| TemplateConsumable | None | `[0]` | No |
| Bread | Food | TemplateConsumable | No |
| FreshBread | Food | Bread | Yes |
| CannedFood | Food | TemplateConsumable | No |
| SpoiledCannedFood | Food | CannedFood | Yes |
| Vodka | Food | TemplateConsumable | No |
| Sausage | Food | TemplateConsumable | No |
| Energetic | Food | TemplateConsumable | No |
| Energetic_Limited | Food | Energetic | No |
| Bandage | Medicine | TemplateConsumable | No |
| Medkit | Medicine | TemplateConsumable | No |
| ArmyMedkit | Medicine | TemplateConsumable | No |
| EcoMedkit | Medicine | TemplateConsumable | No |
| AntiRad | Medicine | TemplateConsumable | No |
| Hercules | Medicine | TemplateConsumable | No |
| Cinnamon | Medicine | TemplateConsumable | No |
| Beer | Food | TemplateConsumable | No |
| Water | Food | TemplateConsumable | No |
| Milk | Food | TemplateConsumable | No |
| PSYBlocker | Medicine | TemplateConsumable | No |
| GuitarUsable | Guitar | TemplateConsumable | No |
| DvupalovVodka | Food | Vodka | Yes |
| EQ08_FreshBread | Food | FreshBread | Yes |
| EQ82_konserva | Food | SpoiledCannedFood | Yes |

All food/medicine entries have `ConsumeOnUse = true` and use both hands.
`GuitarUsable.ConsumeOnUse = false`; it and the template must be excluded from
consumable timing controls. Drinks and food share the `Food` enum and therefore
cannot be separated by `ConsumableType` alone.

Relevant live configuration paths are `<SID>.InventoryActionTime`,
`<SID>.ConsumableType`, `<SID>.AnimBlueprint`, `<SID>.MeshPath`,
`<SID>.ConsumeOnUse`, `<SID>.IsQuestItemPrototype`,
`<SID>.EffectPrototypeSIDs.[index]`,
`<SID>.AlternativeEffectPrototypeSIDs.[index]` and
`<SID>.NegativeEffectPrototypeSIDs.[index].Effect`. Timing work must leave the
effect arrays, chance, strength and effect duration untouched. Existing
consumable-strength and effect-duration controls have different purposes.

## Paired animation routes

The SDK contains separate player and held-item montages. Examples confirmed
in `FullEditor-WindowsModEditor.pak` are:

| Family | Player montage | Held-item montage |
| --- | --- | --- |
| Antirad | MG_fp_antirad_use | MG_antirad_fp_use |
| Bandage | MG_fp_bandage_use | MG_bandage_fp_use |
| Beer | MG_fp_beer_use | MG_beer_fp_use |
| Bread | MG_fp_bread_use | MG_bread_fp_use |
| Canned food | MG_fp_canned_food_use | MG_canned_food_fp_use |
| Condensed milk | MG_fp_condensed_milk_use | MG_canned_milk_fp_use |
| Energy drink | MG_fp_energy_drink_use | MG_energy_drink_fp_use |
| Medkit | MG_fp_medkit_common_use | MG_medkit_fp_use |
| Pills | MG_fp_pills_common_use | MG_hercules_fp_use |
| Sausage | MG_fp_sausage_use | MG_sausage_fp_use |
| Vodka | MG_fp_vodka_use | MG_vodka_fp_use |
| Water | MG_fp_water_use | MG_water_fp_use |

Player routes are under
`/Game/_STALKER2/Animations/Player/AnimSequences/Items/<family>/`; held-item
routes are under `/Game/_STALKER2/Animations/item/<family>/fp/`. Matching only
the substring `use`, `drink` or `medkit` is unsafe: SDK assets also include
dialogue, contextual NPC actions and quest-specific animations. Match verified
ordinary consumable routes, not third-person contextual or dialogue actions.

The installed item configurations share animation blueprints among variants:
all three medkits use `AnimBP_Medkit_fp`; Hercules, Cinnamon and PSYBlocker use
`AnimBP_Hercules`; both energy drinks use `AnimBP_Energy`; the bread, canned
food and vodka quest variants reuse their ordinary family blueprint. Different
per-item factors cannot be inferred reliably from the montage name alone.

Package references establish the route from each of the 17 ordinary item
definitions through its animation blueprint and `AnimCollection_fp_*` asset
to one of the 12 paired player/held-item use montages above. The three installed
DLC item catalogs contain 11 Deluxe, four PreOrder and seven Ultimate roots;
none is a consumable. The three DLC entries with `InventoryActionTime` are
weapon attachments, not consumable timing candidates.

A conservative item whitelist contains Bread, CannedFood, Vodka, Sausage,
Energetic, Energetic_Limited, Bandage, Medkit, ArmyMedkit, EcoMedkit, AntiRad,
Hercules, Cinnamon, Beer, Water, Milk and PSYBlocker. Exclude the template,
guitar and all five quest variants. However, mesh and montage matching alone
cannot enforce that exclusion: FreshBread and EQ08_FreshBread share the exact
Bread mesh and animation route. A runtime implementation that promises quest
exclusion must obtain the planned item SID; otherwise its actual scope is the
shared ordinary-use animation family and must be described that way. Merely
checking the native asset prefix excludes dialogue montages but does not
identify which inventory variant launched an ordinary-use montage.

## Exposed runtime API and ownership

SDK reflection confirms `PC.ConsumePlannedItem`,
`PC.ResetPlannedConsumableItem`, `PC.OnBeforeUseItemBP`,
`PC.OnItemUseEndedBP` and `PC.GetSecondaryHandItemMeshComponent`.
`AnimInstancePlayer.hand_item_data.item_skeletal` exposes the held-item mesh.
SDK reflection also exposes
`CppMediator.get_player_item_in_hands_data()`, returning the main/support hand
prototype IDs, and `get_items_count_in_inventory(obj, item_name)` for a count
check. Both native CppMediator UFunctions were found in the running editor.
An isolated editor use test established that the hand-ID getter returns the
equipped weapon before/after drinking and empty IDs during the native vodka
action. It cannot identify the consumable. Requiring those IDs prevented both
the animation and sound controllers from applying their selected factors.
The revised classifier therefore matches exact native use-montage paths.
Quest or mod-added variants reusing those paths share their family's speed;
item-level quest exclusion is not claimed. The existing cinematic guard and
full-path matching continue to exclude unrelated animation routes.

Editor inspection of all 24 paired montages and their 24 underlying sequences
found exactly one native `AnimNotify_UseConsumable` in each player montage,
none in held-item montages and no notifies in the underlying sequences. All
24 montage `RateScale` values are 1.0. This identifies the existing native
consumption trigger; it does not reveal the C++ implementation or prove
inventory/effect behavior after a speed change. A controller must retain that
notify, never call consumption itself and never add a completion callback.

| Family | Montage length, seconds | UseConsumable trigger, seconds |
| --- | ---: | ---: |
| Antirad | 1.700000 | 0.654145 |
| Bandage | 2.333333 | 1.821979 |
| Beer | 2.633333 | 1.650341 |
| Bread | 2.633333 | 0.593207 |
| Canned food | 4.966667 | 3.050596 |
| Condensed milk | 3.366667 | 2.357930 |
| Energy drink | 2.300000 | 1.340486 |
| Medkit | 1.700000 | 0.670000 |
| Pills | 2.117650 | 1.495138 |
| Sausage | 2.966667 | 0.854333 |
| Vodka | 3.633333 | 2.237496 |
| Water | 2.633333 | 1.676716 |

Each held-item montage has the same duration as its player counterpart.
The item montage carries the ordinary Wwise sound notifies; medkit cap,
injection and healing sound events are scheduled at 0.213559, 0.666674 and
0.670000 seconds. They attach to `jnt_cap` and `jnt_button` on the held item.
Player montage motion-audio notify states additionally start/stop clothing
sounds. Multiplying only the player montage rate would leave the object and
its sound events behind. Multiplying both paired rates preserves their native
event ordering; playback and consumption still need a short real-action check.

`AnimInstance.Montage_SetPlayRate` permits a per-instance rate change while
retaining the native montage and its events. `Montage_GetPlayRate` excludes
the asset's `RateScale`. `GetCurrentActiveMontage` returns only the first
active montage, so coverage of simultaneous slots is limited. The paired
player and held-item instances must both be included.

The current movement companion already compensates native action montages for
its own component-wide movement rate. Consumable scaling belongs in that same
rate-ownership path; a second independent montage writer could repeatedly
capture the other controller's output as its new baseline. Track the original
rate, the current montage identity and the last written rate, and restore only
values still owned by the companion. Defaults must leave native playback
unchanged. Pausing, interruption, same-montage replay and returning the slider
to its default require explicit handling.

## Audio metadata

Wwise `Actor-Mixer Hierarchy/S2 Live/Consumables.wwu` has 12 top-level folders.
These folders are organizational entries, **not runtime effect targets**.
The useful targets are their concrete random-sequence containers. Mapping the
corresponding `Events/S2 Live/Consumables.wwu` actions to target GUIDs yields
28 ordinary consumable containers with native event anchors:

| Target names | Runtime short IDs |
| --- | --- |
| CannedFoodLid, CannedFoodOpen, CannedFoodPrick | 902757381, 859589639, 388869288 |
| EnergeticOpen, EnergeticDrop | 540231150, 819188217 |
| CondensedMildKnifeHit, CondensedMildChug | 119293503, 87759253 |
| MedkitCap, MedkitInject, MedkitHealing | 815181542, 13951605, 545205152 |
| AntiradCap, AntiradButton, AntiradInject | 239850084, 277377809, 631622804 |
| BeerCap, BeerOpen | 280545231, 1059170500 |
| BreadBite, SausageBite | 301364914, 464524565 |
| BandageOpen, BandagePick, BandageRoll | 362436059, 167102883, 105900509 |
| PillsOpen, PillsDrop, PillsEat | 658900224, 636641230, 789079641 |
| Drink, Chew | 118529581, 828298796 |
| VodkaCapScrew, VodkaCapOff, VodkaLiquidShake | 546288389, 1060277111, 550011665 |

The native event `SFX_Consumables_Common_Chug` targets
`CondensedMildChug` (87759253), not the separate `Chug` container (792106969).
The latter has no direct event target in this work unit and should not be
silently treated as a verified anchor. Original event assets are under
`/Game/_STALKER2/Audio/WwiseAudio/Events/Consumables/`.

Exclude `HealingNPC`, `HealingNPC_ThirdPerson` and their child containers,
`Alcohol_PostEffect`, contextual-action work units and voiceover. A dedicated
consumable duration parameter should affect only local-player emitters, with
the default duration unchanged. Do not reuse the reload duration parameter:
that would couple two independent sound controllers. With the existing
duration effect, a speed factor of `1.5` requests `100 / 1.5 = 66.6667%`
duration. Native animation events must still schedule every sound; do not
replay or duplicate those events.

## Bounded runtime validation

Two fresh isolated PIE sessions used normal quickslot input to drink vodka at
100% and 150%. The observer did not write animation rates or call consumption.
Both player and held-item montage position velocities increased by a measured
factor of 1.499986. Each session consumed exactly one item and returned to the
equipped weapon. The observed delay from the first montage sample to native
consumption changed from 2.244 to 1.498 seconds, consistent with the existing
2.237496-second notify position and sampling latency.

At 150%, the sound controller reported factor 1.5 and 66.6667% duration for
consumable and clothing audio. The neutral profile left the consumable path
inactive. This verifies controller state, not recorded or listened-to audio
alignment. Medicine and food use the same verified paired-montage mechanism,
with metadata inspected for all 12 families; they were not individually played.

Remaining limits include campaign play, audible alignment, interruption and
extreme-rate combinations, and interaction with non-default **Inventory action
speed**. Effect strength and duration remain native; the drinking comparison
does not establish every medicine's effect semantics.
