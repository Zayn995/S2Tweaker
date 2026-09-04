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
and no usage reporting. It makes exactly two kinds of outbound request, both
of which the user triggers:

1. **"Check for updates"** (a button, never in the background): one request
   to `api.github.com` asking for the latest release tag.
2. **Oodle library**: one download from the public OodleUE mirror on GitHub,
   once, if the library is not already present on the machine.

Everything else — settings, presets, cache, generated mods — stays in the
tool's own folder on the user's machine.

## Attribution

Free code signing provided by [SignPath.io](https://signpath.io), certificate
by the [SignPath Foundation](https://signpath.org).
