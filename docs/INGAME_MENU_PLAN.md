# S2Tweaker in-game menu: scope and prerequisites

Status: 2026-09-09. Research only; no working menu has been built.
The required Zone Kit editor/cooker is unavailable in the checked development
environment, so the native game component remains pending. A checkbox that
only writes metadata would not provide a working menu.

## Requested behavior

- An optional export checkbox enables our own in-game menu.
- The menu exposes selected S2Tweaker settings with verified runtime support.
- Multiple S2Tweaker-generated mods register separately in one menu.
- No dependency on the third-party MCM framework. Targeted foreign-mod
  support was explicitly cancelled. The existing general conflict scanner
  is a separate feature.
- Preserve the approach of selective config patches and signed runtime binaries.

## Established route and remaining work

GSC's [Game Features guide](https://cdn.stalker2.com/guides/Game_Features_Modding_Guide.pdf)
describes native Blueprint content, generated registration assets, distinct
mod content mounts and cooking/staging/packaging. The current config-Pak
writer cannot create those assets. The
[save/load guide](https://cdn.stalker2.com/guides/Save_Load_system_for_mods.pdf)
documents ModWorldSubsystem persistence, not arbitrary config hot reload.

The [Blueprint API guide](https://cdn.stalker2.com/guides/Blueprint_API_Guide.pdf)
lists maximum-health and maximum-stamina getters/setters. These are initial
API candidates, not verified mappings of existing S2Tweaker controls.
One-shot healing and time-skip actions would not fulfill the requested menu.

Current `gui.py` places `S2Tweaker_Manifest.json` in every generated Pak.
The desktop importer reads archives individually; a runtime reading only
that shared mounted path cannot enumerate all own mods. A working design
needs unique profile identities, discoverable registrations, version checks,
duplicate handling and explicit ownership of overlapping settings. Do not
multiply already modified values again on menu open or save load. Old Paks
cannot be promised automatic runtime support without migration/regeneration.

GSC's [dependency guide](https://cdn.stalker2.com/guides/Simple_mod_dependency_system.pdf)
covers cooker dependencies, not automatic installation or resolution of
conflicting GameData patches.

When the prerequisite becomes available, create our own widget/subsystem
assets and verify two-mod registration, input focus, selected settings,
conflicts, reset and save/load before integrating the functional checkbox.

Evidence: [local tools](INGAME_RUNTIME_RESEARCH.md) and
[control candidates](INGAME_CONTROL_CAPABILITIES.md).
The earlier 1-18 preview contains no in-game menu.
