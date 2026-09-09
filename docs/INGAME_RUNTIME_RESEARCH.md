# Native in-game menu: local development prerequisites

Checked on 2026-09-09. Scope: an optional native menu for **S2Tweaker-generated
mods only**, without an MCM dependency. Third-party mod adapters and imports are
outside the current request.

## Result

The required Zone Kit editor/cooker is unavailable in the checked development
environment. Current scope and status:
[INGAME_MENU_PLAN.md](INGAME_MENU_PLAN.md).

No installed Zone Kit or Unreal Editor/cooker was found in the checked launcher
manifests, engine registrations, standard installation directories, command
search path, project files or game installation. The available tools can build
S2Tweaker and write config Paks, but do not provide the required native Blueprint
asset authoring/cooking toolchain.

This establishes a local build prerequisite, not that a native menu is
unsupported by the current game. Older statements that Blueprint mods are
categorically unavailable must not be used to reject the feature.

## Evidence and search boundaries

Machine-specific paths are recorded only in the ignored local report
`out/ingame_runtime_environment_2026-09-09.json`. The following source paths use
installation-relative names and do not disclose the user's account directory.

| Source | Checked content | Finding |
| --- | --- | --- |
| Steam `steamapps/libraryfolders.vdf` | Registered Steam libraries | One library is registered. |
| Steam `steamapps/appmanifest_*.acf` | 34 installed-app manifests | The game is present; no Zone Kit or Unreal Editor app is listed. |
| Steam `steamapps/appmanifest_1643320.acf` | Game installation record | Identifies the installed S.T.A.L.K.E.R. 2 game, not a developer editor. |
| Epic launcher `Data/Manifests` under its standard machine-data directory | Launcher installation manifests | Directory absent. |
| Standard Epic Games and UnrealEngine installation directories | Editor installation roots | Checked directories absent. |
| Per-user Unreal Engine `Builds` registration and both machine EpicGames Unreal Engine registrations | Custom engine installation paths | Registration keys absent. |
| Command search path | UnrealEditor, UnrealEditor-Cmd, UnrealPak, RunUAT, AutomationTool | None found. |
| Installed game directory | UnrealEditor executables, UnrealPak, AutomationTool, RunUAT, ZoneKit-named files, `.uproject` files | No matching files found. |
| Project tree | Unreal editor executables, `.uproject` / `.uplugin`, ZoneKit tools | No local editable native-menu project or editor toolchain found. |
| Windows installed-program records | Development software | Visual Studio Community 2022 17.13.6 and Windows SDK 10.0.22000 are installed. |
| Visual Studio and Windows SDK tool locations | MSBuild and SignTool | Both executables exist. |
| `tools/repak.exe` | Existing legacy Pak utility | Present. It is not a Blueprint compiler or cooker. |
| `s2tweaker/pakio.py`, `s2tweaker/pakfile.py` | Current S2Tweaker packaging | Current config Pak generation is implemented in Python; the legacy repak executable is not required by that runtime. |

Only the system volume was mounted, apart from a temporary-directory drive
alias. These checks are not a claim to have searched every unregistered custom
folder on disk. A portable/custom Zone Kit copy outside the checked locations
would need its actual editor/project path identified.

## Concrete missing prerequisite

To produce a real native menu artifact, the workspace needs an accessible
**official Zone Kit installation matching the current game**, including the
editor/cooker and exposed game Blueprint classes used by the native mod
subsystem. The current game target documented by this project is UE 5.5.4; a
generic editor or C++ compiler by itself does not establish compatibility with
the game's custom Blueprint classes and packaging process.

With that toolchain available, development still requires our own editable mod
project, menu widget and subsystem Blueprints, their settings/profile discovery
contract, and a cooked package that can be loaded by the game. The existing
Python Pak writer can package files, but cannot turn a text description or cfg
into these cooked Blueprint assets.

No MCM or Lootable Zone assets, code, identifiers or packaging are adopted as
the implementation. An own runtime module can use the game's official native
mod interfaces once their current API and packaging requirements are applied.
Exact API design is a separate concern from the local tool availability checked
here; this report does not infer callable functions from compiled asset names.

## Work performed

Read-only inventory of local manifests, registry installation records, known
tool locations and project/game filenames. No installation, download, game or
editor/GUI launch, runtime injection, product-code change, or test run occurred
for this investigation.
