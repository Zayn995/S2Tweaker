# NPC equipment by faction and player progression

Research decision, 2026-09-11, game 2.0.5. Implementation starts only after the
inventory, consumer and composition audits recorded here.

- [Complete baselines and paths](NPC_EQUIPMENT_BASELINES.md), including the
  [1,483-row baseline table](NPC_EQUIPMENT_BASELINES.csv).
- [Object, quest and spawn consumers](NPC_EQUIPMENT_SCOPE.md).
- [Composition with existing loot controls](NPC_EQUIPMENT_COMPOSITION.md).

## Implementation decision

Expose existing weighted equipment choices for the 50 audited ordinary NPC
object profiles across 12 factions and their roles. Rank means **PlayerRank**
(player progression), not an individual NPC's rank. Preserve native combined
rank masks and difficulty restrictions. Single-candidate lotteries have no
relative choice and are omitted. Chance lists, empty candidates, unaudited
items, the malformed Mercenaries Master pool and the malformed Bandit pistol
rank mask are excluded.

Changing the shared generators directly would also change named NPCs and
other factions. Instead, clone the effective generator and the necessary
equipment-helper branches for the selected ordinary object profile, then
patch only that object's `ItemGeneratorPrototypeSID`. Original generators
retain only independently requested global tweaks. The 50 objects have their
own generator links, `refkey=NPCBase`, non-zombie metadata and generated names;
all 82 direct descendants also have their own links. Validate these properties
and inheritance shielding against loaded data before enabling an edit.

An edited ordinary profile may itself be placed by a quest. This does not
isolate A-Life encounters from all missions. Explicit quest generator
reassignments can override the profile. No promise is made about replacing
equipment stored on already spawned NPCs, changing appearance/meshes or
turning equipped armor into loot. Native clone/relink behavior needs an
in-game test; CFG and Pak tests are not gameplay verification.

Store audited identities and selectors, never numeric game baselines. Each
source identity includes its actual `refurl` as well as `refkey`; the current
roots refer back to `../ItemGeneratorPrototypes.cfg`. New branches preserve
these attributes in the same relative patch directory. NPC-only invisible
armor is valid for equipment choices, even though it is excluded from new
player-loot lotteries. Its inventory visibility flags remain unchanged.

Each candidate's 100% setting inherits the existing global quality and loot result;
0% disables that candidate when another final candidate remains. Multiplying
every candidate equally leaves relative frequencies unchanged. Added
lower-rank variety candidates retain their existing settings. Copy all active
ammo, condition, helmet and separate armor-loot changes into cloned branches.
Preserve every array entry and attribute when creating a new generator.

Fractional source weights exist (0.1 and 0.5). Correct the existing global
quality calculation to preserve them; keep its established integer rounding
for integer baselines. Reject non-finite inputs and all-zero final pools.

No additional extraction inputs are required; `CACHE_SCHEMA` stays unchanged.
The UI uses deferred controls in the existing paged editor, so presets,
undo/redo, reset, summaries and conflict controls share the normal registry.
Unavailable saved targets remain visible for reset and cannot silently retarget
another item after a game update.
