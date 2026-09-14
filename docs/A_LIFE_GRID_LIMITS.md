# A-Life grid distance: scope and save risks

`NPC visibility distance (A-Life grid)` multiplies `ALifeGridVisionRadius` and
`GenericModelGridVisionRadius` in the installed `CoreVariables.cfg`. In the local
2.0.5 snapshot these are 8500 and 7500; at 200% the generated values are 17000 and
15000. The builder reads these baselines live. At 100% it emits neither value.

These config numbers do not establish the game's effective render or simulation
distance. The previous tooltip's fixed metre comparison was too strong. This
control has not been demonstrated to reproduce Distant Horizons, and no safe
threshold has been established for it. The 139 m default discussed for that mod
is not a default or safety boundary for this percentage control.

## Published reports reviewed on 13 September 2026

- The [Distant Horizons author](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1879)
  describes experimental changes affecting several gameplay systems.
- Its [file instructions](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1879?tab=files)
  warn that saving after using that mod prevents a simple return to the previous
  behavior; removal and a save from before its use are required.
- In the [mod's discussion](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1879?tab=posts),
  Feuerpfote's 27 August report describes missing or already-dead story and
  underground NPCs at 170 m on a pre-2.0 playthrough, and occasional crashes near
  200 m. These are that player's observations with that mod, not controlled
  results for S2Tweaker or evidence that any lower range is universally safe.

The in-tool warning therefore identifies the external reports and the uncertainty
for this grid-only control. The range and default remain 50–300% and 100%; they
are input bounds, not a safety rating.

## Save handling and remaining checks

Removing a Pak prevents its patches from loading again. It does not reverse NPC
deaths, completed events or other consequences the game has already saved. Whether
these specific grid values themselves persist after removal remains unverified.
Keep a separate save from before testing and preserve the original mod setup.
Do not treat a saved experimental playthrough as a reversible graphics preset.

Game checks should compare the same pre-test save at default and changed values,
including story/underground encounters, restart and save/load behavior, and removal
with restoration of the pre-test save. Config generation tests prove the written
fields and neutral output; they do not prove the engine uses both values as expected
or that a changed value is safe for a full playthrough.
