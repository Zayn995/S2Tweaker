S2Tweaker - S.T.A.L.K.E.R. 2 Mod Generator
==========================================

Build your own personal tweak mod with sliders and checkboxes - no modding
knowledge needed. S2Tweaker reads the vanilla values from YOUR installed game
version and generates a clean patch-based .pak mod from exactly the values
you change. Everything left at "(vanilla)" is not touched, so it plays nice
with your other mods.

Hundreds of controls in 14 categories plus Overview: Player, Vaulting, Weight & items, Combat,
NPCs & AI, Mutants, Factions, Weapons, Ammo, Armor, Upgrades, World, Economy,
Traders.

NEW IN 1.42.0 — DESKTOP DESIGN AND 24 COLOR PALETTES
--------------------------------------------------
- Teal/ice-blue Standard, olive/amber Zone PDA, Obsidian, ten more general palettes
  and all eleven faction palettes. Choose Design -> Standard for the new default.
- Clearer sections, quieter navigation, Segoe UI text and revised Overview cards.
- Game folder/Browse, Confirm/Reload, Oodle help and Mousewheel stay visible.
- Preview, build and install keep their place at larger interface scales.
- Mousewheel still starts OFF. Status colors keep their meaning in every palette.
- No gameplay settings or generated Pak contents change from choosing a palette.
- Extract the complete new ZIP. Preserve your settings.json/editor.json and
  presets if moving from a previous folder; keep all runtime files together.
- No Pak rebuild needed for this visual update. The signed runtime is unchanged.

INCLUDED FROM 1.41.0 — ADDITIONAL DETAIL SETTINGS
------------------------------------------
- 486 additional supported values on the checked game 2.0.5 data, including editions.
- Weird Nut/Water, individual medicine/buff strength and ongoing buff duration.
- Individual weight, base price and inventory size for 84 weapon items.
- Per-weather sight/hearing/scent, camp activity needs and ranked grenade budgets.
- Optional helmet chances by faction/role/player rank, selective upgrade bonuses
  and separate passive scanner radii.
- World -> Additional detail settings; helmets in the existing NPC equipment editor.
- Profiles, undo/redo, reset, conflict protection and sparse Pak exports supported.
- Medical effect identities preserve native Master difficulty modifiers.
- No new movement, reload or animation-timing changes; no UE4SS or Dev Kit needed.
- 57 local suites, portable GUI workflow and Pak readback checked. NOT play-tested.
- The 19 signed runtime binaries are unchanged; no scan result for this new ZIP yet.

Rebuild your personal Pak to apply your choices. Values are read from your game.

INCLUDED FROM 1.40.1 — JOB REPAIRS WITH LIMITED PLAYER CONFIRMATION
-----------------------------------------
Candidate repair for missing multi-job text and disappearing return markers.
All installed languages are discovered dynamically (18 checked, 208 aliases each).
Native Game.locres resources are extended; generated multi-job Paks grow by
about 147 MiB on the checked installation. Other Game.locres replacement mods
can conflict; the config conflict scan cannot identify these language conflicts.
No game translations or Oodle DLL ship inside this tool. No UE4SS is needed.

After one job ends, remaining return markers are reapplied only when their
job and return stage are active. On 12 September Molkerr reported working quest
translations and the second marker surviving a hand-in before/after save/load.
Other languages, givers, reward orders and save scenarios still need checks.
This is player feedback, not an independent gameplay test of every case.

Use a separate tool folder and save from before accepting jobs. Rebuild your
personal Pak, with the game closed before replacing it. Keep original saves
and the old Pak. Test translated job titles/objectives, two completed jobs handed
in separately, reverse order and save/reload. Both rewards should be paid once;
the other job's journal/marker/dialogue should remain after the first hand-in.
Keep the same Pak until test jobs end. Reverting requires the matching original
save and Pak together. Rebuild your personal Pak to apply these changes.

INCLUDED FROM 1.40.0
--------------
Extra artifact bonuses: World -> Artifact editor & related settings.
Add missing ordinary bonus types, including fire protection on Liquid Stone.
Nine supported families; 518 additions and 871 total artifact-editor controls on
the audited 2.0.5 data. Add controls: 0 off, 100% native Low, up to 1000%; global
artifact strength also applies. Existing bonus controls retain their meanings.
Optional Artifact bonus labels follow your changes selects the nearest native
tier and hides zero-strength rows. Labels remain approximate. Re-equip artifacts.

Multi-job exports include title/objective translations from the installed game.
The native-resource repair and compatibility limits are described above.
Existing journal/stage IDs are preserved. First preparation after a game update
may need Oodle to read compressed resources; see the tool's Oodle help.

World -> NPC equipment by faction & player progression: 12 factions, 50 ordinary
role profiles, 370 native groups and 1,028 relative-choice controls on 2.0.5.
100% inherits, 200% doubles a relative weight, 0 disables it if another remains.
Rank means player progression. Existing pools, shared rank groups and difficulty
filters remain. NPC-only body armor does not become lootable. Existing inventories
may not refresh; generic mission NPCs may use the edited ordinary profiles.

New bonuses/labels, inherited-variant protection, supplemental translations and
NPC equipment are NOT PLAY-TESTED. Many bonus rows have no verified engine limit.
Job marker checks and individual A-Life tests remain open. No UE4SS is needed.

INCLUDED FROM 1.39.0
-------------------
Artifact editor: World -> Artifact editor & related settings (experimental).
353 supported settings on game 2.0.5: individual artifact weight, base price,
bonuses and native radiation tiers; individual detectors; Weird Ball parameters;
moving lightning/fire-ball speed and pursuit distance; rank-based rarity weights.
Choose a family and target, then Edit selected settings. Supports profiles,
favorites, undo/redo, reset and conflict scans. Inherit/-1 restores global
behavior for absolute values; 100% restores individual multipliers.
Rarity weights are normalized and Universal also affects an E06_MQ01 quest
placement. Re-equip edited artifacts. Effects, stacking, save/load, ball behavior
and spawn distributions are NOT PLAY-TESTED. No UE4SS is needed.

Maximum talk distance only (100-300%), in Vaulting -> Interaction reach.
Leave Talk distance (minimum & maximum) at 100% to keep the vanilla minimum.
Existing profiles retain their behavior. Changed maximum factors multiply.
Profiles, undo/redo, reset and conflict scans supported. NOT PLAY-TESTED.
Multiple-job and individual A-Life game checks remain open. No UE4SS.

INCLUDED FROM 1.38.0
-------------------
Regional weather: World -> Regional weather (experimental), choose a region,
then Edit this region's weather. Selection weights 0-400%, duration 25-400%.
100% keeps the regional baseline. Supports 18 regions; only enabled ordinary
weather is offered. Global rain/duration factors combine with regional values.
Profiles, favorites, undo/redo and reset supported. No UE4SS needed.
NOT PLAY-TESTED: quests can override weather; transitions may take time.
All fixes from 1.37.4 are included. Runtime binaries remain unchanged.

INCLUDED FROM 1.37.4
-------------------
Fixes loading game data after game patch 2.0.5 (binary cfg format 2).
The cache rebuilds once. If conversion fails, the error names the file.
Load game data again after updating; rebuild your personal pak when needed.
No UE4SS or slow-motion add-on. Tested for extraction and pak generation;
NOT PLAY-TESTED. All 19 existing runtime binaries remain unchanged.

INCLUDED FROM 1.37.3
-------------------
Fixes a missed story cancellation in the experimental multi-job repair.
Zalissya's story cleanup now also cancels active Warlock job journals.
Finished and never-accepted jobs stay untouched. Rebuild your generated pak.
NOT PLAY-TESTED; recovery of saves already past the event is not promised.

INCLUDED FROM 1.37.2
-------------------
Experimental multi-job repair: each accepted job gets its own journal, and
round cleanup waits until none is active. NOT PLAY-TESTED. Use a save from
before accepting jobs: old active jobs cannot be migrated. Keep the generated
pak while its jobs are active. The shared cancel line cancels all current
jobs from that giver. Interact again to accept another job; no auto-dialog.

NPC search time now goes up to 1000%. The player report covers 400%; higher
values are not play-tested. Tooltips record the latest community reports.
The first game-data load rebuilds the cache to include journal prototypes.

INCLUDED FROM 1.37.1
-------------------
Repairs the black-window/startup failure in the withdrawn 1.37.0 release.
Fewer Windows handles, paged Overview, armor editors released when closed,
and optional loot/world controls loaded on demand. Mousewheel and Design
are visible in the toolbar; OFF is red, ON is green. All 12 designs have
clearer text and previews. The interface has been checked in a real window.

SpawnActor data is no longer part of every startup cache. Extra stash finds
request a compact container index only when needed. The first game-data load
after updating refreshes the cache once. All runtime binaries stay unchanged.

ALSO INCLUDED FROM 1.37.0
-------------------------
Editable Overview and Favorites, undo/redo, named profiles with comparison,
Pak history and restore, generated-value preview, left navigation and display
size/density options. Up to 18 additional per-piece armor controls plus two
global switches, and 18 optional loot/world additions.

New gameplay effects have not been play-tested. Experimental options are labelled.
The first game-data load refreshes the cache once. Rebuild your Pak to use
new settings. Existing presets remain readable. There is no in-game menu;
movement/fire-rate animation desynchronization remains unresolved.

Ammunition stacks at 900 per slot in vanilla - the Ammo tab can raise that,
globally or per round, and food and medicine have their own slider.

Every slider has a number box for exact values (dot and comma both work),
the mouse wheel only scrolls the page unless you switch it over, and the
Design button offers 24 color palettes, including teal/ice-blue Standard -
all purely cosmetic, the .pak you build is identical.

WHAT YOU CAN TWEAK (short tour)
-------------------------------
- Player: health, stamina (incl. per-action costs), walk/crouch and
  run/sprint speed, jump height, fall damage, breath hold, interaction
  reach and talk distance, ladder climb speed, save slots, autosave
  interval and quicksave overwrite window, limp thresholds after hard
  landings, bleeding per hit, damage screen effects, starting money for
  a new game, dialog/cutscene/default field
  of view, four HUD elements (compass, crosshair, body and stash markers)
  forced on or off, sleep rules (sleep whenever you like, minimum hours,
  sleep during emissions), max carry
  weight + where the overweight penalty starts, item weights per category,
  radiation, bleeding, hunger & sleepiness, headshot multiplier,
  explosions, hit camera shake / aim punch
- Vaulting: seven sliders for how Skif climbs and vaults, plus the
  'Improved vaulting' preset that restores the tuned community vault mod
- Weapons on THREE levels: global sliders, 8 category factors and
  per-weapon overrides for 91 weapons - all unique named guns and the
  Deluxe/Ultimate/Pre-order edition guns included. 9 factors each (damage,
  spread, recoil, durability, fire rate, effective range, bleeding, ADS
  move speed, ADS aim-in speed), plus magazine size, melee damage and
  range, jamming, scoped sway, shooting camera shake, ADS zoom, bullet
  drop, bullet speed, which weapon classes fit the pistol slot, and two
  switches that turn aim assist off for mouse or gamepad. Weapons are listed with their real in-game names
  ("GunAK74_ST - AKM-74S") and the search box finds both spellings
- Ammo on TWO levels: global sliders (damage, armor piercing, armor
  damage, cover penetration) and per-round overrides for all 34 rounds in
  14 calibers - a round's own factor beats the global one
- Armor: global protection sliders per damage type, extra artifact slots
  on every body armor (capped at the game's 5), per-armor overrides
  for all 57 armors and helmets (edition pieces included, real in-game
  names), armor durability, armor carry-weight bonuses; additional per-piece
  weight, price, grid size, durability, artifact slots and absolute protection,
  plus experimental sprint, limp, helmet, noise/fall and shielded-slot options
- NPCs & AI: damage, health, accuracy, vision & hearing range, grenade
  usage, reaction delay, "NPCs don't self-heal", NPC gear quality, NPC
  flashlights (brightness & reach, beam width, use in combat, on/off
  hours), experimental A-Life sliders
- Mutants: global damage/health/speed/hearing/regen/protection plus a
  per-species tree in four size groups; bloodsucker cloaking
- Factions (experimental): your standing with 13 factions, every
  faction-vs-faction pairing between the majors, reputation rollback time
  and reaction strength, "Trading requires standing"
- World: how long bodies stay and how many, weather duration, anomaly
  damage (global + per element type), consumable strength,
  medkit & bandage healing, rain/storm and emission frequency, emission
  duration, loot amounts (two separate game systems, four sliders),
  dropped weapon condition, artifact strength/radiation/spawn, detector &
  scanner range
- Economy & Traders: buy/sell prices, per-category price factors, repair &
  upgrade costs, quest rewards & repeatable-quest cooldown, fast travel
  cost, trader stock amount & variety, restock time, minimum buy
  durability, trader wallets

TOOL FEATURES
-------------
- Mod scan with 'Avoid conflicts' mode: on request the tool scans your
  other installed mods, marks every slider they also change, and one
  checkbox locks all of them for guaranteed hands-off compatibility
  (per-slider unlock buttons, plain-text report export)
- Every built pak is an editable preset: "Load preset ..." accepts .pak
  files and restores all settings exactly; JSON presets work too
- "Changed only" view to see your whole mod at a glance
- Search box that finds sliders, weapons, ammo rounds and armor by name
- Built-in searchable FAQ (50 entries) and a DLC checker in the status
  line that tells you which edition content the tool found
- No network access at all: the tool never checks for updates, never
  downloads anything, and the package does not even contain Python's
  networking modules (see TOOL UPDATES below)


HOW TO USE
----------
1. Extract this archive anywhere (e.g. a "S2Tweaker" folder on your desktop).
   Keep the files together: S2Tweaker.exe needs the DLLs and the "_internal"
   folder that sit next to it. Everything the tool creates later (settings,
   presets, cache, output) also lands in that same folder - delete it and
   nothing is left behind.
2. Run S2Tweaker.exe.
3. Check the suggested game folder, then click "Confirm & load game data".
   First load extracts ~85 MB of config data from your game (10-20 seconds).
4. Move sliders / tick checkboxes. Anything at "(vanilla)" stays untouched.
   Single weapons, ammo rounds, armor pieces, mutant species and faction
   pairs live in trees: on the matching tab click a category ("Assault
   rifles", a caliber, "Body armor", a size group ...) to open it, then
   click an entry to open its own factors. Items you changed are marked
   in amber ("N of 9 factors changed"). The search box also finds
   weapons, rounds and armor by name and opens their category for you.
   Note: an entry's own factor replaces the global slider for that
   parameter (it does not stack), and values that are zero in vanilla get
   no slider - a multiplier of zero could not do anything there.
5. Click "Build pak -> output folder", then copy the .pak from the "output"
   folder into <Game>\Stalker2\Content\Paks\~mods\
   (or click "Install to ~mods" to do that in one step - the ~mods folder
   is created automatically if it doesn't exist).
6. Optional: tick the debug checkbox to also export the raw patch .cfg
   files next to the pak, so you can inspect exactly what was generated.

PORTABLE: settings, game-data cache and output all live next to the exe.
Delete the folder and everything is gone. To uninstall the mod itself,
delete zzz_<YourModName>_P.pak from the ~mods folder (or use the
"Remove from ~mods" button).


GAME UPDATES
------------
After a game patch, just start S2Tweaker and confirm the game folder again -
it detects the new version automatically, re-reads the fresh vanilla values
and your next build is based on them. Multiplier tweaks therefore survive
balance patches.


TOOL UPDATES
------------
By hand, and on purpose: download the new ZIP from where you got this one
and extract it over your S2Tweaker folder, replacing what is there. Your
settings, presets, cache and output are not part of the download, so they
stay exactly as they are. The version you are running is in the window
title.

There is no update check and no auto-updater: the tool has no networking
code at all, and a program that talks to a server to fetch and replace its
own files is exactly the pattern antivirus scanners and mod sites object to.


WHAT IS IN THE FOLDER (and why the exe has a Python icon)
---------------------------------------------------------
S2Tweaker.exe is pythonw.exe from python.org, byte for byte, digitally
signed by the Python Software Foundation - that is why it carries the
Python icon and Python's version info; changing either would break the
signature. The tool's own code sits next to it as readable Python files in
_internal\s2tweaker, together with the Python runtime and Tcl/Tk (all
signed by the PSF or Microsoft). Since 1.23.0 there is no unsigned
executable at all: the pak files are read and written by plain Python
code (pakfile.py). Nothing is packed, nothing is embedded, nothing
unpacks into your temp folder, and the package does not even contain
Python's networking modules (socket, ssl) - it could not go online if it
tried. Earlier versions were built with PyInstaller, whose launcher is a
shape antivirus heuristics distrust; that is gone.


NOTES
-----
- Steam and GOG installs supported (auto-detected; you can also browse to
  any folder that contains Stalker2\Content\Paks).
- Windows only (Windows 10 or newer).
- If an antivirus tool still flags anything, it is a false positive - see
  the section above and the FAQ in the tool; please report it to your
  vendor as such.
- Oodle library: to read the game's packed config files, a proprietary
  decompression library (oo2core_9_win64.dll, 0.6 MB) is required. It cannot
  be shipped with this tool, and S2Tweaker does NOT download it - on purpose.
  A program that pulls a library off the internet and then runs it is exactly
  what malware does, and that is one of the reasons antivirus scanners flag
  tools like this one. So you place the file once, yourself: if it is
  missing, S2Tweaker tells you at startup and gives you both the download
  link and the folder to put it in (next to S2Tweaker.exe; only if that
  folder is not writable - e.g. the exe sits in Program Files - it goes to
  %LOCALAPPDATA%\S2Tweaker\tools instead). You may already have the file:
  every Unreal Engine installation ships it, and so do some other
  S.T.A.L.K.E.R. 2 modding tools. It has to be the exact build this tool
  expects; other Oodle 2.9.x builds are rejected, and the tool tells you
  when it found one. Building a mod pak never needs Oodle; only reading the
  vanilla values does.
- DLC-specific items (Cost of Hope etc.) are not covered by the per-item
  weight slider; the global multipliers still apply to them.
- The in-game "Custom Rules" difficulty writes some of the same multipliers;
  precedence is untested - prefer the standard difficulties when using
  damage/durability tweaks.


CREDITS
-------
- repak by trumank (https://github.com/trumank/repak, MIT OR Apache-2.0):
  the pak reader/writer in this tool was written against the format as
  repak implements it and verified against repak's output. No repak
  code or binary ships with the tool since 1.23.0.
- Python (Python Software Foundation, PSF licence), Tcl/Tk (BSD-style),
  customtkinter by Tom Schimansky (MIT), darkdetect by Alberto Sottile
  (BSD-3-Clause), packaging (Apache-2.0 OR BSD-2-Clause). Their licence
  texts are in _internal\licenses\.
- cfg.bin decoding based on bin2cfg.py by joric, building on S2CfgToJSON
  by sdwvit with binary reader by thexii (public domain / MIT)
  https://github.com/joric/stalker/wiki
  https://github.com/sdwvit/S2CfgToJSON
- Thanks to the S.T.A.L.K.E.R. 2 modding community for documenting the
  {bpatch} config-patch system, and to GSC Game World for the game.


LICENCES
--------
S2Tweaker itself is MIT licensed (source: https://github.com/Zayn995/S2Tweaker).

Bundled component - repak (https://github.com/trumank/repak), dual licensed
MIT OR Apache-2.0; MIT terms used:

  MIT License

  Copyright 2024 Truman Kilen, spuds

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.


