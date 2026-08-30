S2Tweaker - S.T.A.L.K.E.R. 2 Mod Generator
==========================================

Build your own personal tweak mod with sliders and checkboxes - no modding
knowledge needed. S2Tweaker reads the vanilla values from YOUR installed game
version and generates a clean patch-based .pak mod from exactly the values
you change. Everything left at "(vanilla)" is not touched, so it plays nice
with your other mods.

~120 tweaks in 7 tabs, including:
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
- Weapon tweaks on THREE levels: global sliders, 8 weapon categories
  (damage, spread, recoil, durability, fire rate each) and per-weapon
  overrides for 79 weapons incl. all uniques
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
- DLC-specific items (Cost of Hope etc.) are not covered by the per-item
  weight slider; the global multipliers still apply to them.
- The in-game "Custom Rules" difficulty writes some of the same multipliers;
  precedence is untested - prefer the standard difficulties when using
  damage/durability tweaks.


CREDITS
-------
- repak by trumank (pak packing/unpacking, MIT/Apache-2.0)
  https://github.com/trumank/repak
- cfg.bin decoding based on bin2cfg.py by joric, building on S2CfgToJSON
  by sdwvit with binary reader by thexii (public domain / MIT)
  https://github.com/joric/stalker/wiki
  https://github.com/sdwvit/S2CfgToJSON
- Thanks to the S.T.A.L.K.E.R. 2 modding community for documenting the
  {bpatch} config-patch system, and to GSC Game World for the game.
