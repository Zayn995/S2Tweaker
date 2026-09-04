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
drift. The workflow fails if the produced executable is missing its version
resource or is not the expected `--onedir` layout.

Each release is approved manually before it is signed.

## Third-party binaries

Two things in the shipped folder are not built from this repository's
source, and both are stated openly:

- **`repak.exe`** (inside `_internal`) — the pak packer/unpacker by
  [trumank](https://github.com/trumank/repak), MIT OR Apache-2.0. It is
  committed to this repository as a prebuilt executable and is bundled
  unchanged. Its licence ships with the tool
  ([THIRD_PARTY_LICENSES.txt](../THIRD_PARTY_LICENSES.txt)).
- **`oo2core_9_win64.dll`** (Oodle, proprietary, by RAD Game Tools /
  Epic Games) — **not** part of the download. Reading the game's packed
  configuration files requires it, so on first use the tool fetches it once
  from the public OodleUE mirror on GitHub, verifies its official SHA-256
  checksum and keeps it next to the executable. It is never redistributed
  by this project.

## Privacy

S2Tweaker collects nothing. There is no telemetry, no analytics, no account
and no usage reporting.

Since 1.19.2 it makes **no outbound requests at all**. There is no networking
code left in the program: no `urllib`, no sockets, no HTTP client. The
bundled `repak.exe` is compiled from source with its download function and
its entire HTTP/TLS stack removed, so it cannot make a request either. Both
claims are enforced by [tests/test_no_network.py](../tests/test_no_network.py)
and [tests/test_no_download.py](../tests/test_no_download.py) on every build,
and anyone can verify them by grepping this repository.

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
