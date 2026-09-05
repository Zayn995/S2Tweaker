# Code signing policy

*This page exists because the SignPath Foundation requires every project it
signs for to publish one. It is linked from the [README](../README.md).*

## Who builds and signs S2Tweaker

S2Tweaker is a single-maintainer open-source project. There is no company
behind it and no paid work involved.

| Role | Who |
|---|---|
| **Authors** (may commit to the repository) | the [owners of `Zayn995/S2Tweaker`](https://github.com/Zayn995/S2Tweaker) |
| **Reviewers** (review external contributions) | the owners of `Zayn995/S2Tweaker` |
| **Approvers** (approve a release for signing) | the owners of `Zayn995/S2Tweaker` |

All roles are held by the same maintainer, who works under the pseudonym
**Zayn995**. Multi-factor authentication is enabled on the GitHub account
and on SignPath.

## How a release is built

Released binaries are **not** built on a personal computer. Every build runs
in GitHub Actions from the public source of this repository
([`.github/workflows/build.yml`](../.github/workflows/build.yml)), which
calls [`tools/build_exe.py`](../tools/build_exe.py) — the same script the
local `build.bat` uses, so there is only one build recipe and it cannot
drift.

Since 1.21.0 the build does not use PyInstaller or any other packer. The
shipped folder is assembled from the python.org installation on the build
machine:

- **`S2Tweaker.exe` is `pythonw.exe` from python.org, byte for byte**, signed
  by the Python Software Foundation. It is renamed, nothing else; the
  workflow fails if its SHA-256 differs from the runner's `pythonw.exe` or
  if the signature is not valid.
- `python3XX.dll` and the extension modules in `_internal` are the ones from
  that installation, signed by the Python Software Foundation; the Visual C++
  runtime DLLs are signed by Microsoft. The workflow fails if any DLL, PYD
  or EXE in the folder is unsigned — with exactly one exception, `repak.exe`
  (see below).
- The tool's own code ships as readable `.py` files in
  `_internal/s2tweaker`, next to the pure-Python libraries it uses
  (customtkinter, darkdetect, packaging). A small start-up module,
  `_internal/sitecustomize.py` ([`tools/launcher.py`](../tools/launcher.py)
  in the repository), is what Python's `import site` runs; it starts the GUI.
- The standard library ships as `_internal/python3XX.zip`, compiled from the
  same installation, **without** `socket`, `ssl`, `asyncio` and `sqlite3`.
  No OpenSSL library and no socket extension are in the package, so the
  program could not open a network connection even if its code tried.

Each build runs a self-test before it is accepted: a copy of the folder is
started, imports every bundled module, proves that `socket` and `ssl` are
absent, runs the bundled `repak.exe` once, builds the main window and tears
it down again.

Each release is approved manually.

## Third-party binaries

Two things in the shipped folder are not built from this repository's
source, and both are stated openly:

- **`repak.exe`** (inside `_internal`) — the pak packer/unpacker by
  [trumank](https://github.com/trumank/repak), MIT OR Apache-2.0. The
  release does not use the upstream binary: the workflow compiles repak from
  source at a pinned tag ([`tools/build_repak.py`](../tools/build_repak.py))
  with its runtime download function and its whole HTTP/TLS stack removed.
  It is the only unsigned executable in the folder. Its licence ships with
  the tool ([THIRD_PARTY_LICENSES.txt](../THIRD_PARTY_LICENSES.txt)).
- **`oo2core_9_win64.dll`** (Oodle, proprietary, by RAD Game Tools /
  Epic Games) — **not** part of the download and never fetched by the tool.
  Reading the game's packed configuration files requires it, so the user
  places that file once, guided by a setup window that names the source and
  the target folder. The tool verifies it against the SHA-256 checksum repak
  expects. It is never redistributed by this project.

## Privacy

S2Tweaker collects nothing. There is no telemetry, no analytics, no account
and no usage reporting.

Since 1.19.2 it makes **no outbound requests at all**. There is no networking
code left in the program: no `urllib`, no sockets, no HTTP client. The
bundled `repak.exe` is compiled from source with its download function and
its entire HTTP/TLS stack removed, so it cannot make a request either. Since
1.21.0 the package does not even contain Python's `socket` and `ssl` modules.
These claims are enforced by
[tests/test_no_network.py](../tests/test_no_network.py),
[tests/test_no_download.py](../tests/test_no_download.py) and
[tests/test_build_layout.py](../tests/test_build_layout.py) on every build,
and anyone can verify them by grepping this repository or listing the
shipped folder.

Two earlier network paths were removed deliberately:

1. **"Check for updates"** — dropped in 1.19.2. Nexus Mods' file submission
   guidelines prohibit executables that connect to the internet "unless where
   it is crucial", and state that "'auto update' functionality does not
   qualify as crucial". Updating is now a manual file swap.
2. **Oodle library download** — dropped in 1.19.1. A program that fetches a
   library and then loads it is dropper-shaped, and it caused antivirus false
   positives. The user places that file once, guided by a setup window.

Everything else — settings, presets, cache, generated mods — stays in the
tool's own folder on the user's machine.

## Attribution

Free code signing provided by [SignPath.io](https://signpath.io), certificate
by the [SignPath Foundation](https://signpath.org).
