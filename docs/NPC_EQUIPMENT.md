# NPC equipment by faction and player progression

Included in 1.40.0; experimental and not play-tested. No UE4SS is needed.

Open **World → NPC equipment by faction & player progression**, after loading
your game data. Choose a faction, a role and an equipment group, then select
**Edit equipment choices**. The current 2.0.5 snapshot offers 12 factions,
50 ordinary role profiles and 370 equipment groups, with 1,028 candidate
controls. Known weapon and armor names are shown where available; otherwise
the game-data identifier is used.

Each number changes the **relative selection weight of an existing item**:

| Setting | Meaning |
| --- | --- |
| 100% | Inherit the existing global gear-quality result |
| 200% | Double this candidate's relative weight |
| 50% | Halve this candidate's relative weight |
| 0% | Disable this candidate, provided another final choice remains |

For example, two candidates with weights 10 and 5 have a 2:1 ratio. Setting
the second to 200% produces weights 10 and 10, a 1:1 ratio. These numbers are
not drop chances. Scaling both equally leaves their relative frequencies
unchanged. The editor does not introduce items from another faction's pool.

## Rank, difficulty and shared groups

**Rank means the player's progression (`PlayerRank`), not the rank of an
individual NPC.** Newbie, Experienced, Veteran and Master are the game's enum
names. If an entry says “Experienced + Veteran + Master”, these stages share
the same native group and this one setting affects all three. Difficulty
filters are also retained, including the separate Stalker difficulty.

Single-choice groups are hidden because changing their relative weight cannot
select a different item. Chance-based helmet/night-vision rolls are separate
from these weighted weapon, pistol and body-armor choices. The existing global
helmet chance option remains available.

## Scope and interaction with other settings

Changes create a private copy of the equipment generator for the selected
ordinary NPC object profile. Modified armor or pistol helpers are copied too.
Only that profile's generator link is changed. Shared vanilla generators and
other object profiles are not edited by these individual settings.

Ordinary profiles are also used for generic enemies and corpses in missions;
this is not an A-Life-only feature. Named/custom object definitions retain
their original links, and scripted inventory reassignment may override the
new profile. This is a definition-level boundary, not a guarantee that every
encounter or mission will behave identically.

Global quality, weapon condition, loaded ammo, optional helmet chance and
additional lower-rank variety are copied into the effective private branch.
Individual percentages affect only the selected native candidate. Extra
variety candidates keep their global settings. Extra lootable armor is a
separate lottery and does not automatically follow the equipped-armor choice.
Editing NPC-only armor does not make it player-lootable or change NPC meshes.

Use the normal **Profiles**, **Undo/Redo**, **Reset settings**, favorites and
**My changes** functions. **Details** shows the loaded native weight and item
identifier. An old selection that no longer matches loaded data is marked
inactive; reset it to 100%. Conflicts include the generator branches copied
by this feature, because another mod may change fields within those branches.

## Verification and remaining game test

Local checks cover neutral output, live values, cloned reference chains,
unchanged original definitions, native rank/difficulty masks, fractional
weights, zero-pool rejection, global composition, profiles and GUI operation.
The complete 55-suite headless run passed. The portable GUI test exercises
weapon, armor and combined-rank selections with save/load, undo/redo and reset.
Pak contents are read back and checked against generated definitions.

The engine's loading of new equipment-generator IDs and changes to newly
spawned NPCs still need an actual game test. Existing saved inventories may
not refresh. Compare newly spawned ordinary NPCs of the selected profile and
progression stage; also inspect another role/faction, a named NPC, save/load
and any mission encounter using the edited profile. A sample or two cannot
establish the exact distribution of a weighted lottery.

[Research, complete baselines and implementation boundaries](NPC_EQUIPMENT_RESEARCH.md).
