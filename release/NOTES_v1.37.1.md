S2Tweaker 1.37.1 repairs the mostly black window and startup failure in the withdrawn 1.37.0 release. It includes the expanded editor, armor controls and optional loot/world settings from that version.

### Startup and memory

- Removed the extra favorite/details buttons from every control row. Right-click a label for these actions, or use the visible actions in Overview.
- Overview shows 20 entries per page and releases its cards when you leave it. Individual armor editors release their widgets when closed or when another armor is opened.
- Additional loot/world values remain available under **World → Edit loot & world settings** and **Overview → Loot & world**, without building 85 extra sliders at startup.
- Avoided the redundant 100% scale redraw. Plain value displays use fewer native windows.
- The large SpawnActor file is no longer part of every user's startup cache. Extra stash finds request a compact container index only when exporting that feature.

### Designs and toolbar

- **Mousewheel** and **Design** are visible in the toolbar. Mousewheel starts **red/OFF** (scroll the page) and switches to **green/ON** (change sliders).
- All twelve palettes have clearer hint/highlight text, readable normal/hover button captions and consistent selection controls. Standard keeps its blue-on-black appearance.
- The design chooser shows individual palette previews and marks the active choice. Warning captions stay amber, and their text wraps to the available window width.

### Updating

Download **S2Tweaker_v1.37.1.zip** for the program; the other ZIP is source code. Extract the complete program ZIP over your existing tool folder, keeping the DLLs and `_internal` alongside the EXE. Personal settings, profiles, cache and Pak history are not included in the ZIP. The next game-data load refreshes the cache once. Existing presets remain readable.

The Oodle setup guide remains available. The tool does not download the library or update itself.

### Verification and remaining limits

All **46 local headless suites passed**, covering config generation against game data, editor history/profiles, archive round-trips and the startup/cache regressions. GitHub runs nine CI suites, the portable self-test and binary signature checks before the release artifact is accepted.

The repaired window was checked in Windows with the actual portable runtime: categories, six armor editors, Overview paging, optional-value editing, display scaling and a native context menu. The complete repair check peaked at **7,481 USER handles**. A subsequent check of all twelve designs and the visible toolbar peaked at **6,652**. Both stayed below our 8,000-object budget; no Tk callback errors occurred. Startup in the complete repair check took about **8.8 seconds** on the local test machine. These are local measurements, not guarantees for every PC.

The release uses the same EXE and runtime DLL/PYD bytes as 1.36.1, assembled with the current readable Python source in GitHub Actions. The baseline ZIP is fixed by SHA-256, and every runtime binary is compared and signature-checked. No new VirusTotal result is claimed for this ZIP.

**The new gameplay effects remain unverified in-game.** Experimental armor, loot and world options retain their labels. Movement/fire-rate animation desynchronization remains unresolved. Existing saves may already contain generated loot, and no native in-game menu is included.

Details: [startup repair](https://github.com/Zayn995/S2Tweaker/blob/v1.37.1/docs/STARTUP_REPAIR.md), [editor workspace](https://github.com/Zayn995/S2Tweaker/blob/v1.37.1/docs/EDITOR_WORKSPACE.md), [armor controls](https://github.com/Zayn995/S2Tweaker/blob/v1.37.1/docs/ARMOR_EXTENSIONS.md), [optional loot/world additions](https://github.com/Zayn995/S2Tweaker/blob/v1.37.1/docs/OPTIONAL_EXTENSIONS.md).
