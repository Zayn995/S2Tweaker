# Native runtime control candidates for an S2Tweaker menu

Snapshot: 2026-09-09. Scope: an optional menu for **our own generated mods**, with separate names and settings for multiple S2Tweaker profiles. No foreign-mod registration, discovery or configuration support is proposed here. This document is a local, static capability audit; it does not implement or demonstrate a functioning menu.

## What is actually established

**Subsequent official API check:** GSC's
[Blueprint API Guide](https://cdn.stalker2.com/guides/Blueprint_API_Guide.pdf)
lists `Set Max HP` and `Set Max SP` with float inputs under `Stalker2.Obj`
(page 9), with `Get Max HP` and `Get Max SP` returning floats (page 14).
These are documented runtime API candidates beyond the quest-only evidence
below. Their integration with player lookup, active effects and our existing
config factors is not verified. The
[save/load guide](https://cdn.stalker2.com/guides/Save_Load_system_for_mods.pdf)
also documents `ModWorldSubsystem` save events and `SetDataForSave`.
The required Zone Kit editor/cooker is unavailable in the checked development
environment, so implementation remains pending. See [INGAME_MENU_PLAN.md](INGAME_MENU_PLAN.md).

The one-shot actions below are research evidence, not the requested menu's
feature list. The request is to edit selected existing settings in-game;
healing, clearing statuses or skipping time would not fulfill that request.

The installed game's `QuestNodePrototypes.cfg` contains native runtime operations that change the player and world after a quest node runs. These are stronger evidence than an arbitrary invented config key, but they are **quest-node schemas, not verified callable Blueprint functions**. A menu button still needs a supported bridge to execute the appropriate operation. The current Phase 2 Blueprint API documentation must determine that bridge; older statements in this repository about Blueprint support must not override current official documentation.

The inspected original contains 674 `SetCharacterParam`, 68 `SetCharacterEffect`, 732 `SetGlobalVariable` and 22 `TimeLock` nodes. These are occurrence counts, including development/quest entries, rather than counts of safe user controls. The examples below were selected from actual player-targeted quest definitions without a local BrokenGameDataFilter. They are **schema references only**: a menu must never run or modify the cited story-quest nodes themselves.

Source files are relative to `vanilla/Stalker2/Content/GameLite/GameData/`. The node audit reads the 77,336,667-byte QuestNode file one top-level struct at a time. Local reproducible extraction: `out/ingame_control_evidence.py`.

## Smallest supportable first control set

Seven operations have direct native examples. Most are **one-shot state changes**, not persistent replacements for S2Tweaker's existing stat multipliers. An eighth, temporary carrying bonus, has a native effect definition and an apply-effect route, but still needs end-to-end bridge validation.

| Candidate | Confirmed native schema and original example | What it does not establish |
| --- | --- | --- |
| Restore current health | `SetCharacterParam` → `Params.[0].ModifiedCharacterParam = EModifiedCharacterParam::HPPercent`, `ChangeValueMode = EChangeValueMode::Set`, `ChangeValue = 100.0`. `Arch_Bossfight_Faust_SetCharacterParam_Player`, QuestNode line 34884; `TargetQuestGuid = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`. | No proof of changing maximum health, regeneration rate or granting persistent invulnerability. |
| Restore current stamina | `SetCharacterParam` → `EModifiedCharacterParam::SP`, Set mode, `ChangeValue = 9999.0`. `E07_SQ01_SetCharacterParam_Player`, line 551235, same player GUID. | 9999 is a scripted refill example, not a documented normal stamina maximum or range for a slider. No proof of changing stamina cost or maximum. |
| Clear current hunger | `SetCharacterParam` → `EModifiedCharacterParam::HungerPoints`, Set mode, `ChangeValue = 0.0`. `E01_MQ01_SetCharacterParam_Player_Hunger_Zero`, line 124866, player target. | Does not disable hunger accumulation or change its rate. |
| Clear current sleepiness | `SetCharacterParam` → `Params.[2].ModifiedCharacterParam = EModifiedCharacterParam::Sleepiness`, Set mode, `ChangeValue = 0.0`. `E11_MQ03_SetPlayerStates_toNorm`, line 791266, player target. | Does not remove sleep mechanics or alter accumulation rate. |
| Stop current bleeding | Same node as above, `Params.[0]`, `EModifiedCharacterParam::Bleeding`, Set mode, `ChangeValue = 0.0`. Also appears in the health-reset example. | Does not grant bleeding immunity or change future wound severity. |
| Clear current radiation | Same node, `Params.[1]`, `EModifiedCharacterParam::Radiation`, Set mode, `ChangeValue = 0.0`. | Does not grant radiation resistance or change protection values. |
| Choose a time-of-day preset | `EQuestNodeType::SetTime`, `InGameHours = 21`, `InGameMinutes = 0` at `Arch_Bossfight_Faust_SetTime`, line 34605; another native example sets 1:00 at line 34993. | Does not change day length or global game speed. Story/weather schedules may react to a time jump. |
| Temporary carrying bonus, pending bridge validation | `EffectPrototypes.HerculesWeight`, line 18038: `EEffectType::AdditionalInventoryWeight`, `ValueMin = ValueMax = 20`, `Duration = 300.f`, `DuplicationType = EDuplicateResolveType::KeepNew`. Native `SetCharacterEffect` uses `TargetQuestGuid` and `EffectPrototypeSID`; player example `Arch_Bossfight_Faust_SetCharacterEffect...` at line 33976. | The effect exists, but a menu-driven application of our own equivalent has not been demonstrated. No arbitrary capacity setter, immediate remove API, indefinite toggle or confirmed save/load lifetime follows from this evidence. |

The exact common player-modification path is:

```text
<OurOwnQuestNode>.NodeType = EQuestNodeType::SetCharacterParam
<OurOwnQuestNode>.TargetQuestGuid = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
<OurOwnQuestNode>.Params.<entry>.ModifiedCharacterParam = <verified enum>
<OurOwnQuestNode>.Params.<entry>.ChangeValueMode = EChangeValueMode::Set
<OurOwnQuestNode>.Params.<entry>.ChangeValue = <validated value>
```

This shows the schema to generate an original node or validate a corresponding official API. It is not a claim that a UI can mutate the `ChangeValue` field of an already loaded prototype. Fixed presets could use separate original nodes if a repeatable execution bridge is available; free-form numeric sliders need a verified runtime setter or another supported parameter-passing mechanism.

## Execution and state evidence

`Scripts/OnGameLaunch/OnGameLaunchScripts.cfg` contains native script commands `XStartQuestBySID rootgraph` and `XStartQuestNodeBySID rootgraph_GDEQ_Global`. S2Tweaker already generates its own `XStartQuestNodeBySID` launcher for faction relations in `_relations_runtime_patch()`.

This proves a command spelling and a config-launched execution route. It does **not** establish that shipping-game widgets may invoke arbitrary console commands, that a completed one-shot node can be restarted indefinitely through the same call, or that an OnGameLaunch script also runs on every save reload. Those lifecycle questions remain separate from the menu layout.

Runtime global assignment is also explicit: `ANCQ23_P_SetGlobalVariable_ANCQ23_AtasStash`, QuestNode line 26334, uses `GlobalVariablePrototypeSID`, `EChangeValueMode::Set` and `VariableValue = false`. `GlobalVariablePrototypes.ANCQ23_AtasStash`, line 2686, supplies `Type = EGlobalVariableType::Bool` and `DefaultValue = False`.

These demonstrate typed globals and a quest-side writer. They do not demonstrate a widget getter, arbitrary UI parameter transport, per-profile preference storage, cross-session persistence, reset-to-default behavior or automatic synchronization with desktop settings. Our own implementation would require namespaced variables or another verified storage API, without reusing story globals.

## Live changes, reload and restart boundaries

| Layer | Appropriate behavior and present evidence |
| --- | --- |
| One-shot player-state operations | Native quests can perform them during play. If exposed, run on an explicit user action. Do not automatically replay healing, hunger/radiation clearing or time jumps on launch/load just because the previous menu value was saved. |
| Temporary effect | Native duration and duplicate-resolution fields exist. Whether an active custom effect survives a save/load, how to replace it safely and how to remove it early remain unverified. An indefinite carrying toggle is not ready on this evidence. |
| Persistent menu preferences | Need a verified save/read API plus the correct player-ready lifecycle. Reapply only settings whose runtime semantics and ownership have been established, not every stored UI value. Distinguish the game's current state from the menu's saved preference. |
| Generated config patches | There is no demonstrated hot-reload path for the existing generated cfg files in this audit. Treat changes to those static prototypes as requiring regeneration and game restart; some affect only newly created actors/items. A menu cannot automatically convert all existing desktop sliders into runtime controls. |
| Multiple S2Tweaker mods | Each menu entry and stored setting needs our own mod/profile identity. This is not a general foreign-mod plugin API. Shared player properties still need a defined ownership rule if two own profiles request different values. |

## Explicit exclusions and unanswered API questions

- `EModifiedCharacterParam::InventoryWeight` is observed in `Test_Conditions_InventoryWeightPlayer` at line 2249980. That is development/test evidence about inventory weight, **not** proof of a carrying-capacity setter. Do not present it as one.
- Current-state setters are not equivalent to `MaxHP`, `MaxSP`, regeneration, stamina consumption, hunger rate, day-length or the desktop movement-speed settings. No generic “set any cfg field live” API was established.
- `SetWeather` and `TimeLock` exist, but are outside the initial set. A lock's cleanup/unlock lifecycle must be proven before a menu toggle can safely own it. Merely finding the node name is insufficient.
- No removal operation named `RemoveCharacterEffect` was found in this QuestNode source. This does not rule out an official Blueprint/API removal function; it limits what the inspected cfg proves.
- Widget creation, key binding, input focus, opening/closing, player lookup, runtime getters/setters, restartable execution and persistence must be confirmed separately in the current official Blueprint APIs. No method names for those functions are invented here.
- No GUI/game launch, runtime test or product code change was performed for this audit. No foreign assets or mod interfaces are required by this proposal.

Conclusion: native data supports a modest first set of player-state actions and time presets, plus investigating a temporary carry effect. A functioning, persistent in-game settings menu remains an implementation task whose Blueprint execution and storage APIs must be verified first.
