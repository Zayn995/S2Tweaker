# Player recovery and wounded-NPC interaction controls

These optional CFG controls use the installed game data as their baseline. Their neutral value is 100%, which emits no patch. They require neither animation changes nor additional sound assets. Runtime behavior has not yet been play-tested.

| Control | Target | Meaning |
| --- | --- | --- |
| Sprint exhaustion threshold | `Player.VitalParams.StaminaDisableThresholds` / Sprint-only row / `Threshold` | 25-400% of the installed threshold in stamina points; independent of maximum stamina. |
| Exhausted stamina recovery delay | Same row / `RegenerationDelay` | 0-400% of the installed recovery delay for this state. |
| Suppression recovery speed | `Player.VitalParams.DegenSuppressionPoints` | 25-400% of the installed decay rate. Higher rates shorten suppression, including its temporary blur and accuracy penalties. The existing onset delay remains unchanged. |
| Hold time to help a wounded NPC | `CoreVariables.DefaultConfig.WoundedHealHoldInteractTime` | 25-400% of the installed input hold duration, without changing healing amount or animation speed. |

The Sprint row is selected by its sole `EStateTag::Sprint` tag, not a fixed array index. Native array entries are cloned from resolved installed data; unrelated rows and tags are preserved. Missing or ambiguous rows and requests that cross another installed threshold produce an explicit error. No fallback game values are hardcoded. Configure both exhaustion options in the same generated Pak: they share a native array, so separate mods replacing that array may conflict.

Suppression recovery targets the Player override rather than the shared object template. It does not edit the weapon recoil or spread fields. Wounded-NPC healing chance, health threshold, cooldown and regeneration remain independent controls.

Validation covers installed data, inherited non-default fixtures, reordered array entries, invalid inputs, neutral output, desktop settings persistence, and combinations with maximum stamina, stamina regeneration and sprint cost. These checks verify generated configuration, not campaign outcomes.
