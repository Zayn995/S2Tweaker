# Additional armor settings (v1.37.0)

The Armor tab now offers 18 additional controls per body armor, and the
applicable subset per helmet. Expand a piece under Single armor overrides.
The six existing protection-factor controls remain available and keep their
previous profile format.

| Controls | Behavior |
| --- | --- |
| Weight, base price, maximum durability | Set the individual item's absolute value. Price still goes through economy/trader multipliers; existing items may retain their saved condition. |
| Inventory width and height | Set whole grid cells, at least one in each direction. |
| Base artifact slots | Set 0–5 on body armor; technician upgrades remain separate. |
| Absolute physical/fire/electric/chemical/radiation/PSY protection | Override the corresponding factor/global item result, including setting a previously zero protection to a nonzero value. These are raw protection values, not multipliers. |
| Fall protection | Armor-specific absolute protection; experimental. |
| Armor noise coefficient | The individual armor's NoiseCoef field; AI/audible behavior is unverified. |
| Prevent limping | Control bPreventFromLimping; separate from player knockdown immunity. Experimental. |
| Allow a separate helmet | Invert bBlockHead on body armor; equipment visuals and combined protection require gameplay validation. |
| Remove armor sprint restriction | Remove the armor's conditional sprint blocker; does not change movement speed or unrelated concussion blockers. Experimental. |
| Shield first artifact slots | Append a native composite that applies the game's radiation-blocking effects to slots 1 through N. N must fit the generated base slot count. Does not remove protection provided by installed upgrades. Experimental. |

There are also two optional global checkboxes: remove armor sprint
restrictions, and make body armor prevent limping. Per-piece explicit values
take priority over these switches.

## Defaults and priority

Every additional control starts at **Inherit (-1)**. Inherit leaves the existing
global controls and protection factors in charge. An explicit zero is a real
choice and is preserved by profiles, manifests, favorites and settings history.
For sprint specifically, Off keeps that armor's original restriction; it does
not add a sprint restriction to armor that did not have one.

Priority for a protection field is: explicit absolute armor value, existing
individual protection factor, global protection factor. Difficulty modifiers,
technician upgrades and protection caps still apply through their own systems.
Choosing an original value explicitly also removes an earlier global patch
to that field in the same generated output. Other fields are preserved.

Only visible player armor from the loaded game data is offered. Edition
armor is patched in its own DLCGameData branch. NPC protection is not edited.
No new extraction inputs or cache schema change were required.

## Patch format and compatibility

Item fields use sparse bpatch structures. Sprint removal replaces only the
identified armor-conditional effect entry with empty; other native effects
remain. Shielding uses a native wildcard append to EffectPrototypeSIDs and a
new Composite cfg structure with a mod-name/item namespace. The new structure
has no bpatch attribute because it does not replace an existing structure.
No cooked asset, DLL, injector, network component or executable change is needed.

The general mod scan now includes an additional-armor group footprint and
effect-list replacement markers. Its warning does not automatically lock the
individual armor rows. List order changes can still conflict with the indexed
sprint removal. Neither this footprint nor bpatch establishes universal mod
compatibility.

Native data checked: ItemPrototypes armor fields, ArmorConditionalEffect and
BlockSprintEffect, and ArtifactSlotBlockEffect3_Slot1 through Slot5 in
EffectPrototypes. The slot effects are also referenced by native lead-container
upgrades. Their type, slot and blocked radiation effects are checked before
export; an unexpected definition causes an explicit error instead of guessing.
Historical author examples for feasibility:
[Exi's exoskeleton sprint](https://www.nexusmods.com/stalker2heartofchornobyl/mods/299?tab=description)
and [Project Y's lead containers](https://www.nexusmods.com/stalker2heartofchornobyl/mods/1647).
Those examples are not proof of current game compatibility.

## Verification boundary

The dedicated headless suite covers 19 tests, including every new control
against the installed data, neutral output, zero-valued settings, priority,
edition routing, slot limits, namespace separation, source-definition checks,
effect preservation, conflict footprints, profile roundtrip and armor-row state
loading/reset without Tk. The general end-to-end test Pak includes the new
armor options alongside the earlier loot/world and existing game tweaks.

The EXE and existing runtime binaries are retained byte for byte when preparing
the separate preview. GUI layout and actual gameplay effects are not established
by these headless tests. The game and application window are not started by the
test runner.

Verified on 2026-09-09: all 43 release headless suites passed in 1.9 minutes. The
end-to-end Pak was read back completely: 69 entries, 6,829,690 bytes. The
selected armor values, sprint removal and three-slot composite reference
were verified in the resulting archive.

The historical local preview is `out/preview_armor/S2Tweaker/S2Tweaker.exe`.
All 24 application Python files match the workspace. All 19 EXE/DLL/PYD
files match the previous runtime and have valid Authenticode signatures.
The starter SHA-256 remains
`58B39B6D8DC9F51A94F1A3143E49B7498FB804A101F2B33BAA14BD72D45298F8`.
Reports beside the preview: `runtime_integrity.json`, `signatures.json`,
and `armor_validation.json`. The inherited version label remains 1.36.1;
this is an unpublished development preview.

This preview uses Python 3.14.2. Published releases use the separate Python
3.12 build from GitHub Actions; the v1.36.1 release starter has SHA-256
`d72294fb338bc2fc8896d25a7395a4db466425427e1559e77185d5135a830681`.
The release starter is compared with that reference before publication.
