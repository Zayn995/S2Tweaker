# S2Tweaker 1.41.0 - additional detail settings

Adds **486 supported setting values** on the checked game 2.0.5 data, including
installed edition items. Availability follows the data loaded from your game.
The new gameplay effects are experimental and **NOT play-tested**.

## New options

- **Special artifacts (4):** Weird Nut bleeding benefit/healing drawback, Weird
  Water paired capacity bonus/minimum intoxication.
- **Medicine and buffs (16):** individual healing, bleeding/radiation removal,
  buff strength and ongoing Hercules/Cinnamon/PSY-Blocker duration. Native
  medical effect IDs preserve the game's Master difficulty modifiers.
- **Weapon items (336):** weight, base price and inventory width/height for 84
  audited items, including 12 edition items when installed.
- **World and NPCs:** weather sight/hearing/scent (18), camp activity needs (8),
  ranked grenade budgets (12), optional helmet chances (76).
- **Equipment:** supported technician bonus types (14) and passive scanner
  radii (2). Two further registered upgrade types stay inactive because the
  loaded data contains only unsupported penalty directions.

Open **World -> Additional detail settings**, choose a group and target, then
**Edit selected detail settings**. Helmets are in **World -> NPC equipment by
faction & player progression -> Optional helmet** groups.

Profiles, favorites, undo/redo, reset, conflict protection and Pak previews
use the existing editor workflow. Neutral/inherited values produce no extra
patch. Individual scopes now point to their actual Upgrades tab in Overview.

## Installation and limits

Download `S2Tweaker_v1.41.0.zip`, extract the entire folder and run
`S2Tweaker.exe`. Keep the runtime files together. Rebuild your personal Pak
to apply your selected changes, then replace it while the game is closed.

No UE4SS or Dev Kit is needed. Movement, reload, aim-in, draw/holster and
animation-recovery extensions remain deferred. Existing controls retain their
previous behavior. Longer buff duration does not stretch item-use animations;
camp options change activity needs, not animation playback.

Weapon item changes can affect NPC/vendor/world copies of the selected item.
Weather uses shared AI tables; ordinary camp profiles can also occur in missions.
Helmet chances affect existing generation rolls, not guaranteed equipment on
NPCs already saved. Unequip special artifacts before replacing the mod, then
re-equip; saved-effect transitions need game testing. Upgrade effects may be
shared. See [the full detail guide](https://github.com/Zayn995/S2Tweaker/blob/v1.41.0/docs/DETAIL_OPTIONS.md) for composition,
scope and limitations.

The experimental multiple-job repairs from 1.40.1 are included. Their game
confirmation and individual A-Life checks remain open; this release does not
claim to resolve them. Multiple-job Paks can include large Game.locres resources
for every installed language and conflict with other language-resource mods.

## Verification

57 local headless suites passed, including the generated test Pak. The portable
GUI workflow covers all new detail groups and a helmet setting, profile save/load,
undo/redo, reset and Pak export. Generated data is checked against live baselines.
These checks do not establish the actual gameplay behavior.

The signed runtime remains unchanged; no new VirusTotal scan result is claimed
for this ZIP. No game data, translations or proprietary Oodle DLL are distributed.
The source ZIP contains the exact tagged repository files. The public build
workflow refreshes readable application source on the pinned signed runtime;
see `.github/workflows/build.yml` to reproduce it.
