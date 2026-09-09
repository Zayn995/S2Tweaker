S2Tweaker 1.37.0 expands the desktop editor and adds more control over armor, loot and the world. Existing presets remain readable; new options are off or inherit the game's values by default.

### Desktop editor

- An editable Overview brings together My changes, Favorites and Browse controls, with left navigation and changed-setting counts.
- Undo/redo restores whole selections, including individual overrides. Profiles support names, descriptions, duplication and comparison.
- My mods reads your generated Paks, loads their settings and compares exact config targets. Previous Paks are backed up before replacement or removal and can be restored.
- Preview shows the generated changes and original values where they can be resolved. Display options include compact explanations and 85/100/115/130% scaling.

### Armor

- Up to 18 additional controls per eligible armor piece: weight, price, maximum durability, inventory width/height, artifact slots, six absolute protection values, fall protection, noise, limp protection, helmet allowance, sprint permission and shielded artifact slots.
- Absolute protection values can add protection where the original value was zero. Explicit individual values take priority over the existing individual and global factors; old presets retain their behavior.
- Two global switches target armor-related sprint restrictions and limp protection. Edition armor uses its own data branch; body-only options are excluded from helmets.

### Loot and world

- Optional extra artifact, weapon, armor and attachment finds in eligible ordinary stashes.
- NPC armor loot with its own condition range, loaded ammunition, equipment variety and helmet chance.
- Vegetation visibility, per-surface noise, weather visibility contributions and NPC dispersion distance.
- Mutant looting reach, trophy weight/value and per-species drop controls.
- Blood/projectile mark persistence, permanent Weird Flower effects, an optional Hercules field-repair bonus and thrown-bolt lifetime.

### Compatibility and updating

Existing game structures receive selective `{bpatch}` changes. New generators and composite effects use separate namespaced structures. The general mod scan now also checks loot identities and effect-list changes. Overlapping assignments and reordered lists can still conflict; the additional armor group reports warnings without automatically locking its individual controls.

Extract the complete player ZIP over your existing tool folder. Settings, profiles, editor preferences and Pak history are not included in the download. The first game-data load after this update refreshes the extraction cache once for the added stash data. Rebuild your Pak to use the new settings.

### Verification and limits

All 43 local headless suites passed, including config targeting against game data, settings/profile roundtrips, undo/redo, Pak backup/restore and generated archive readback. All six CI suites also passed locally. The GitHub build checks binary signatures, packaging, imports in the bundled runtime, the absence of socket/TLS modules and a Pak roundtrip without creating a window.

**The new gameplay effects and redesigned visual layout have not been play-tested or interactively reviewed.** Sprint, limp, helmet, noise/fall protection, shielded slots, NPC dispersion, cut radius, Weird Flower and Hercules repair remain experimental. Existing save data may already contain generated loot. Movement/fire-rate animation desynchronization is still unresolved. A native in-game menu is not included.

The program continues to ship readable Python source beside the unmodified PSF-signed Python starter, with no updater, injector, added runtime binary or application networking. No VirusTotal result is claimed for the new ZIP.

Details: [armor controls](https://github.com/Zayn995/S2Tweaker/blob/v1.37.0/docs/ARMOR_EXTENSIONS.md), [editor workspace](https://github.com/Zayn995/S2Tweaker/blob/v1.37.0/docs/EDITOR_WORKSPACE.md), [18 optional additions](https://github.com/Zayn995/S2Tweaker/blob/v1.37.0/docs/OPTIONAL_EXTENSIONS.md).
