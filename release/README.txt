S2Tweaker - S.T.A.L.K.E.R. 2 Mod Generator
==========================================

Build your own personal tweak mod with sliders and checkboxes - no modding
knowledge needed. S2Tweaker reads the vanilla values from YOUR installed game
version and generates a clean patch-based .pak mod from exactly the values
you change. Everything left at "(vanilla)" is not touched, so it plays nice
with your other mods.

Around 195 tweaks in 13 tabs: Player, Vaulting, Weight & items, Combat,
NPCs & AI, Mutants, Factions, Weapons, Ammo, Armor, World, Economy, Traders.

WHAT YOU CAN TWEAK (short tour)
-------------------------------
- Player: health, stamina (incl. per-action costs), walk/crouch and
  run/sprint speed, jump height, fall damage, breath hold, interaction
  reach and talk distance, max carry weight + where the overweight
  penalty starts, item weights per category,
  radiation, bleeding, hunger & sleepiness, headshot multiplier,
  explosions, hit camera shake / aim punch
- Vaulting: seven sliders for how Skif climbs and vaults, plus the
  'Improved vaulting' preset that restores the tuned community vault mod
- Weapons on THREE levels: global sliders, 8 category factors and
  per-weapon overrides for 91 weapons - all unique named guns and the
  Deluxe/Ultimate/Pre-order edition guns included. 9 factors each (damage,
  spread, recoil, durability, fire rate, effective range, bleeding, ADS
  move speed, ADS aim-in speed), plus magazine size, melee damage and
  range, jamming and scoped sway. Weapons are listed with their real in-game names
  ("GunAK74_ST - AKM-74S") and the search box finds both spellings
- Ammo on TWO levels: global sliders (damage, armor piercing, armor
  damage, cover penetration) and per-round overrides for all 34 rounds in
  14 calibers - a round's own factor beats the global one
- Armor: global protection sliders per damage type, per-armor overrides
  for all 57 armors and helmets (edition pieces included, real in-game
  names), armor durability, armor carry-weight bonuses
- NPCs & AI: damage, health, accuracy, vision & hearing range, grenade
  usage, reaction delay, "NPCs don't self-heal", NPC gear quality, NPC
  flashlights (brightness & reach, beam width, use in combat, on/off
  hours), experimental A-Life sliders
- Mutants: global damage/health/speed/hearing/regen plus a per-species
  tree in four size groups; bloodsucker cloaking
- Factions (experimental): your standing with 13 factions, every
  faction-vs-faction pairing between the majors, reputation rollback time
  and reaction strength, "Trading requires standing"
- World: anomaly damage (global + per element type), consumable strength,
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
signed by the PSF or Microsoft). The only unsigned file is
_internal\repak.exe, an open-source pak tool that the public build workflow
compiles from source. Nothing is packed, nothing is embedded, nothing
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
  S.T.A.L.K.E.R. 2 modding tools. It has to be the exact build repak
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
- repak by trumank (pak packing/unpacking, MIT OR Apache-2.0)
  https://github.com/trumank/repak
  repak.exe ships inside the "_internal" folder next to S2Tweaker.exe; its
  MIT notice is reproduced in full at the end of this file.
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


