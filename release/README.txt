S2Tweaker - S.T.A.L.K.E.R. 2 Mod Generator
==========================================

Build your own personal tweak mod with sliders and checkboxes - no modding
knowledge needed. S2Tweaker reads the vanilla values from YOUR installed game
version and generates a clean patch-based .pak mod from exactly the values
you change. Everything left at "(vanilla)" is not touched, so it plays nice
with your other mods.

~160 tweaks in 8 tabs, plus per-weapon overrides for 79 weapons and
per-round overrides for 34 ammo types - including:
- NEW in 1.6.0: ammo has its own tab now, with per-round overrides for all
  34 rounds in 14 calibers (a round's own factor replaces the global
  slider); single-weapon overrides are a collapsible category > weapon
  tree instead of a dropdown; the search box also finds weapon and ammo
  names and opens their category for you
- NEW in 1.5.0: mutant overhaul (per-species health/speed/damage
  overrides, bloodsucker cloaking), ADS speed, magazine size, melee
  damage, anomaly damage per type, consumable strength, weather
- NEW in 1.4.0: armor protection per damage type, armor carry-weight
  bonuses, rare artifact bias
- NEW in 1.3.0: ammo tweaks (damage/armor piercing/armor damage/cover
  penetration), weapon effective range & bleeding (three-level system),
  separate weapon/armor durability, detector & scanner range, fast
  travel cost, trader restock time
- NEW in 1.2.0 (community requests): hit camera shake / aim punch 0-300 %,
  NPC reaction delay, experimental A-Life sliders (max simultaneous
  NPCs/mutants, spawn distance), artifact effect strength / radiation /
  spawn chance, save & load presets, slider search box
- Max health / stamina, passive regen, per-action stamina costs
- Fall damage 0-100 %, walk/crouch & run/sprint speed, jump height
- Max carry weight + where the overweight penalty starts (or off entirely)
- Item weights per category, weightless equipped gear
- Player/NPC/mutant damage & health, headshot multiplier, explosions
- Weapon & armor durability, weapon jamming, spread, recoil
- Scoped aim sway, breath hold
- Weapon tweaks on THREE levels: global sliders, 8 weapon categories and
  per-weapon overrides for 79 weapons incl. all uniques - 8 factors each
  (damage, spread, recoil, durability, fire rate, effective range,
  bleeding, ADS movement speed). Expand a category, then a weapon, to
  edit its factors
- Ammo on its own tab, on TWO levels: global sliders (damage, armor
  piercing, armor damage, cover penetration) and per-round overrides for
  all 34 rounds in 14 calibers - a round's own factor beats the global one.
  Expand a caliber, then a round, to edit its factors
- NPCs & AI: accuracy, vision range, hearing range, grenade usage,
  "NPCs don't self-heal"
- Anomaly damage, radiation, bleeding, hunger & sleepiness rates
- Trader min. durability for buying gear, buy/sell prices, repair &
  upgrade costs, quest money rewards, per-category price factors
  (weapons, armor, ammo, artifacts, consumables)


HOW TO USE
----------
1. Extract this archive anywhere (e.g. a "S2Tweaker" folder on your desktop).
2. Run S2Tweaker.exe.
3. Check the suggested game folder, then click "Confirm & load game data".
   First load extracts ~85 MB of config data from your game (10-20 seconds).
4. Move sliders / tick checkboxes. Anything at "(vanilla)" stays untouched.
   Single weapons and single ammo rounds live in trees: on the "Weapons" /
   "Ammo" tab click a category ("Assault rifles") or a caliber to open it,
   then click a weapon / round to open its own factors. Items you changed
   are marked in amber ("N of 8 factors changed"). The search box at the
   top also finds weapons and rounds by name and opens their category.
   Note: a round's own factor replaces the global ammo slider for that
   parameter (it does not stack), and rounds that have no armor piercing /
   cover penetration in vanilla (18 of 34) get no slider for it - a
   multiplier of zero could not do anything there.
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


NOTES
-----
- Steam and GOG installs supported (auto-detected; you can also browse to
  any folder that contains Stalker2\Content\Paks).
- Windows only. Some antivirus tools flag freshly built PyInstaller exes -
  that is a known false-positive pattern for Python-based tools.
- Oodle library: to read the game's packed config files, a proprietary
  decompression library (oo2core_9_win64.dll, 0.6 MB) is required. It cannot
  be shipped with this tool, so on first use S2Tweaker downloads it from the
  public OodleUE mirror on GitHub and verifies its official checksum. It is
  then kept in a "tools" folder next to the exe, so it downloads only once
  and everything works offline afterwards. (Only if that folder is not
  writable - e.g. the exe sits in Program Files - it goes to
  %LOCALAPPDATA%\S2Tweaker\tools instead.) If antivirus HTTPS inspection, a
  proxy or a VPN blocks github.com, just put that DLL next to S2Tweaker.exe
  yourself - the tool picks it up automatically. It has to be the exact build
  repak expects; other Oodle 2.9.x builds are rejected, and the tool tells
  you when it found one. Building a mod pak never needs Oodle; only reading
  the vanilla values does.
- DLC-specific items (Cost of Hope etc.) are not covered by the per-item
  weight slider; the global multipliers still apply to them.
- The in-game "Custom Rules" difficulty writes some of the same multipliers;
  precedence is untested - prefer the standard difficulties when using
  damage/durability tweaks.


CREDITS
-------
- repak by trumank (pak packing/unpacking, MIT OR Apache-2.0)
  https://github.com/trumank/repak
  repak.exe is bundled inside S2Tweaker.exe; its MIT notice is reproduced
  in full at the end of this file.
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


