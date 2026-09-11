# Game 2.0.5 compatibility check

Local validation on 11 September 2026, Steam build **25222692**, fully installed
(`StateFlags=4`). The decoder fix ships in **S2Tweaker 1.37.4**.

The updated game uses binary cfg **format 2**. The previous reader ignored the
version and became misaligned: 60 of 62 required/edition binaries failed, and
the two remaining files produced incorrect root counts without raising errors.
Format 2 adds a four-byte metadata slot before each record's flags byte,
including the outer block. The reader now handles versions 1 and 2 separately
and rejects unknown versions explicitly. Cache schema 27 prevents reuse of
incorrectly decoded data; conversion failures name the affected file.

## Validation

- All 63 required files were freshly extracted from the installed game, plus
  six edition files. All 62 binary cfg files decoded successfully.
- Of the 63 required configs, 54 match the previous local baseline and nine
  changed: AI globals, dialogs, difficulty, item generators, items, NPCs,
  objects, quest nodes and weather selection. No required file disappeared.
- The optional spawn file also decoded using the streaming reader: 130,058
  roots. For developer reference checks, another 88 configs and 333 launch
  scripts were extracted from the current game. Old data was not substituted.
- All **49 release headless suites** passed after completing the developer
  dataset and updating three tests' outdated weather/NPC expectations. Those
  tests now check actual patch membership and values against the live baseline.
  The 10 CI suites are covered, including six synthetic binary-format tests.
- The reference audit verified 10,216 emitted root structures and 4,261 SID
  references, including repeatable-job anchors and story cancellation checks.
- The generated 6,830,426-byte test pak contains 69 entries. All entries were
  read back with the local fix's pak reader and their cfg text parsed.
- The release uses the existing GitHub Actions workflow and hash-pinned
  runtime. All 19 binaries remain unchanged. The local preview already
  passed signature checks and its headless self-test; the published release
  notes link the checks for the final tagged artifact.

No game launch, savegame test, rendering test, or mod installation was performed.
Passing these checks establishes extraction and patch generation, not in-game
behavior. Release 1.37.4 contains no slow-motion prototype or UE4SS.

Private reports and the local executable are under `out/game_update_2_0_5/`.
Extracted game files and the Oodle library remain excluded from Git and releases.
