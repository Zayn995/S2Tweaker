# S2Tweaker 1.42.0 - desktop redesign and 24 color palettes

The editor now has a teal/ice-blue Standard palette, clearer sections and a
more consistent desktop layout. All 24 palettes share the same controls.

- Choose **Design** for Standard, Zone PDA, Obsidian, Graphite, Arctic, Deep
  Ocean, Cobalt, Emerald, Mint, Copper, Sunset, Rose, Plum and eleven faction
  palettes. Existing named choices are retained; select Standard to switch.
- Segoe UI text, quieter inactive navigation and clearer borders improve the
  separation of settings. Overview cards put each setting name first, with its
  category underneath and the complete label available on hover.
- Game folder/Browse, Confirm & load/Reload, Oodle status/setup and Mousewheel
  remain visible. Mousewheel starts OFF, and status colors stay consistent.
- Preview, build and install retain their space at larger interface scales.
  Empty scroll areas now update correctly when changing palettes.

This release changes the desktop presentation. Gameplay settings and the patch
generator retain their behavior; selecting colors does not change your Pak.
There are no new animation controls or UE4SS requirements.

## Updating

Download `S2Tweaker_v1.42.0.zip`, extract the complete archive and run
`S2Tweaker.exe`. Close the tool before replacing an older tool folder. Keep the
starter, runtime files and `_internal` together; replacing only the EXE does not
update the application. Preserve your local settings, editor preferences and
presets. **No personal Pak rebuild is needed just for this visual update.**

The source package is `S2Tweaker_v1.42.0_source.zip`.

## Player feedback and remaining gameplay limits

[Molkerr's 12 September follow-up](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5644157394)
reports working quest translations and the second quest's return marker staying
after the first hand-in, before and after save/load. He also reports Liquid Stone
resistances changing at slider values 100, 500 and 1000. This is limited player
feedback, not independent verification of every language, giver, reward order or
artifact combination. The message does not name an exact tool version. These
repairs were already included in previous releases; no new quest change is made
here. Experimental gameplay limits and outstanding A-Life checks still apply.

## Verification and runtime

Release checks cover the local headless suite, real Windows palette switching,
status colors, 100–130% interface scaling, and portable startup/Pak readback.
Artifact checks compare the packaged sources to the release tag and verify both
ZIPs after upload. These checks do not establish new gameplay behavior.

The signed starter and all 19 native runtime binaries remain byte-identical to
the previous release. No new antivirus scan result is claimed for this ZIP.
No game data, translations, private workspace notes or proprietary Oodle DLL
are distributed. The reproducible build workflow is
`.github/workflows/build.yml`, using readable source and the pinned runtime.
