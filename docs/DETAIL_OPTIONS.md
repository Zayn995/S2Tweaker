# Additional detail settings

Available since **1.41.0**. These additions edit existing configuration data and require
neither UE4SS nor the Dev Kit. Gameplay effects remain experimental.

Open **World → Additional detail settings**, choose a group and an item or
profile, then **Edit selected detail settings**. Edit the values in the list
and press Apply. Details shows the loaded baseline and the meaning of each
setting. Profile save/load, favorites, reset, undo/redo, conflict protection
and the generated-Pak preview use the existing editor workflow.

Optional helmets are in **World → NPC equipment by faction & player progression**:
choose a faction, role and an **Optional helmet** group. Their percentages are
generation chances, unlike the relative weights of weapon/body-armor choices.

## Available options

Counts refer to the checked local 2.0.5 snapshot, including installed edition
definitions. Only supported live entries are shown. A saved setting that becomes
unsupported remains visible as inactive so it can be reset.

| Group | Available values | What can be changed |
| --- | ---: | --- |
| Special artifacts | 4 | Weird Nut bleeding benefit and healing drawback; Weird Water paired capacity bonus and minimum intoxication |
| Medicine and buffs | 16 | Individual healing, bleeding/radiation removal and buff strength for eight items; ongoing duration for Hercules, Cinnamon and PSY-Blocker |
| Weapon item properties | 336 | Weight, base price and inventory width/height for 84 items, including 12 installed edition items |
| Weather senses | 18 | Separate sight, hearing and scent coefficients for six native weather entries |
| Camp activities | 8 | Guitar, jokes, conversations, smoking, sleeping, eating, resting and drinking need rates |
| NPC grenade budgets | 12 | Four ranks in each of three native ordinary groups |
| Upgrade bonuses | 14 | Supported damage, penetration, capacity, dispersion and armor-protection bonus types |
| Passive scanners | 2 | Anomaly warning and search-point radii independently |
| Optional helmets | 76 | Existing helmet rolls within ordinary faction/role/player-rank routes |
| **Total added** | **486** | Possible editor values, not simultaneously rendered slider widgets |

Two further registered upgrade types are inactive because their loaded effects
do not have the supported bonus direction. A penalty is not silently converted
into a bonus. Native clear-weather coefficients of 1 and zero grenade budgets
remain unchanged by a multiplier.

## Inheritance and combinations

- Special-artifact magnitude, medicine/buff, weather, camp and grenade
  percentages use **100% = inherit**. The local percentage multiplies the
  applicable existing global result; original live values are read once.
- Weapon item properties, scanner radii and minimum intoxication use
  **-1 = inherit**. An explicit value replaces that setting. Choosing the
  original live value can therefore override a global factor for one item
  without writing an unnecessary vanilla patch.
- Upgrade detail uses **-1 = inherit**; a chosen percentage replaces its
  existing family factor for that bonus type only. It does not multiply the
  family a second time. Penalties keep their current values.
- Helmets use **100% = inherit**. The local factor multiplies the already
  globally adjusted, capped chance, then caps it at 100% again. Zero is valid
  for an optional helmet roll. It is not a body-armor drop setting.

Hercules and Weird Water keep paired capacity/penalty-threshold effects. The
existing broad carry slider affects capacity separately, so an already chosen
global carry factor can still make their two final values differ. Hercules
field repair stays independent and instantaneous.

## Limits that matter

**No new movement, reload, aim-in, draw/holster or animation-recovery controls
were added.** Animation-dependent extensions and the reload coverage audit
remain deferred. Existing controls keep their previous behavior. Longer buff
duration means a longer gameplay effect, not a stretched item-use animation.
Camp rates affect the need to choose existing activities; their animation
playback is unchanged.

Medical effects retain their native identities so the game's SID-specific
Master difficulty modifiers still apply. Only the eight audited items and
their exclusive numeric effects are supported. New sharing, item descendants,
alternative lists, unsupported providers or curves disable affected options.
Medical healing/removal delivery durations and postprocessing remain unchanged.

The Nut and Water use isolated effect clones. Unequip before replacing the mod,
then re-equip; saved-effect transitions still need game testing. A raw healing
drawback percentage is not a measured final medkit-speed percentage. Setting
Water's minimum intoxication to zero does not establish that every scripted
intoxication behavior is disabled.

Weapon edits apply to copies of the selected item, including NPC/vendor/world
copies. Base price still combines with difficulty, reputation and trader
factors. Quest-locked, guard, tutorial and special actor variants are outside
the audited item list. Edition items appear only when their definitions exist.

Camp details target supported ordinary faction presets, checking their child
rows before modifying a parent. Explicit guard/quest/mutant/zombie presets are
excluded, but ordinary presets can also be used in missions. Weather senses
use a shared AI table. Grenade groups are native Bandits, Army and Humanoid
fallback groups, not independently selectable equipment factions; the boss's
unlimited sentinel is excluded.

Upgrade effects can be shared by several users. Mixed composite descriptions
retain their original summary number when their children no longer share one
factor. Use Preview to inspect actual emitted values. Passive scanner range
does not change the native list of excluded anomaly types or the quest collar
scanner.

## Validation and research

Focused tests cover neutral output, composition and cancellation, native
medical identity, field-repair independence, special-artifact clones, future
sharing/descendant rejection, edition routing, weather/scanner/camp isolation,
upgrade exclusions, and combined helmet/weapon generator branches. All 57 local
headless suites passed, including the full generated test Pak.
The portable GUI check also passed editing, profile save/load, undo/redo,
reset and Pak export across every new detail group and a helmet setting.
The exported Pak was read back and its entry hashes verified. All 19
portable binary files retain valid signatures and are unchanged.

Detailed source evidence:

- [Artifact/medicine ownership and difficulty modifiers](DETAIL_EFFECT_ISOLATION_RESEARCH.md)
- [Weapon item scope and non-timing upgrade effects](WEAPON_ITEM_DETAIL_RESEARCH.md)
- [Helmet routes and camp descendants](NPC_HELMET_DETAIL_RESEARCH.md)
- [Original inventory and prioritization](SLIDER_AUDIT_1_40_1.md)

Automated exports establish the generated data and UI workflow, not gameplay
confirmation. The scope-category navigation metadata has also been corrected:
individual scopes now point to their actual **Upgrades** tab.
