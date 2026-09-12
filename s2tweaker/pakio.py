"""Extract game data and generate S.T.A.L.K.E.R. 2 Paks using pakfile.py.

Write uncompressed, unencrypted V8B Paks mounted at ../../../.
Reading Oodle-compressed game entries requires a user-supplied proprietary
DLL; packing does not. Locate it locally and verify its SHA-256 before
loading native code. Missing libraries produce the manual setup guide.
No library downloads or repak executable are used."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

from . import pakfile

GAMEDATA_PREFIX = "Stalker2/Content/GameLite/GameData"

# Accept only the verified Oodle library hash before loading native code.
OODLE_DLL = "oo2core_9_win64.dll"
OODLE_SHA256 = "6f5d41a7892ea6b2db420f2458dad2f84a63901c9a93ce9497337b16c195f457"
OODLE_URL = (
    "https://github.com/WorkingRobot/OodleUE/raw/refs/heads/main/Engine/Source"
    "/Programs/Shared/EpicGames.Oodle/Sdk/2.9.10/win/redist/" + OODLE_DLL
)

OODLE_HELP = """S2Tweaker needs the Oodle decompression library ({dll})
to read packed game data. It was not found in the usual locations.

{reason}

S2Tweaker never downloads it, on purpose: a program that pulls a library
off the internet and then runs it is exactly what malware does, and that
is one of the reasons scanners flag tools like this one. So this is a
manual step, once:

  1) Get {dll} here:
     {url}

  2) Put it next to S2Tweaker.exe, in this folder:
     {target}

  3) Click "Confirm & load game data" again.

That is all - the file stays there and you never have to think about it
again. It has to be exactly this build (SHA-256 starting with {hash8});
other Oodle 2.9.x builds are rejected on purpose.

You may already have this file: every Unreal Engine installation ships
it, and so do some other S.T.A.L.K.E.R. 2 modding tools.

Note: Writing the Pak itself does not need Oodle. Reading packed game
data does, including the first preparation of optional job translations
or extra stash data during export. Already prepared, current caches can
be reused without decompressing those files again."""


class OodleError(RuntimeError):
    """The required Oodle library is missing; include readable setup guidance."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_ok(path: Path) -> bool:
    try:
        return path.is_file() and _sha256(path) == OODLE_SHA256
    except OSError:
        return False


def app_dir() -> Path:
    """Return the executable directory or development project root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".s2tweaker_write_test"
        probe.write_bytes(b"")
        probe.unlink()
        return True
    except OSError:
        return False


def _oodle_error(reason: str) -> "OodleError":
    # The setup guide directs users to the folder containing S2Tweaker.exe.
    where = str(app_dir())
    return OodleError(OODLE_HELP.format(
        dll=OODLE_DLL, url=OODLE_URL, hash8=OODLE_SHA256[:8],
        reason=reason, target=where))


def oodle_cache_dir() -> Path:
    """Return the portable DLL cache directory.

    If the program folder is unwritable, fall back to LOCALAPPDATA."""
    primary = app_dir() / "tools"
    if _writable(primary):
        return primary
    fallback = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "S2Tweaker" / "tools"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _oodle_error(f"no writable place to keep it: neither "
                           f"{primary} nor {fallback} ({exc})") from exc
    return fallback


def _place(src: Path, dst: Path) -> None:
    """Copy without inheriting read-only attributes, replacing a read-only destination."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            try:
                os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass
        shutil.copyfile(src, dst)
        try:
            os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass
    except OSError as exc:
        raise _oodle_error(f"could not copy the library to {dst}: {exc}") from exc


def _local_oodle_candidates(pak: Path | None) -> list[Path]:
    """Yield local locations that may already contain a usable DLL."""
    dirs = [app_dir(), app_dir() / "tools", Path.cwd(),
            Path(__file__).resolve().parent.parent / "tools"]
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).parent)
    if pak is not None:
        # <game>/Stalker2/Content/Paks/pakchunk0-Windows.pak -> <game>
        game_root = pak.resolve().parents[3] if len(pak.resolve().parents) > 3 else None
        if game_root is not None:
            dirs += [
                game_root,
                game_root / "Stalker2" / "Binaries" / "Win64",
                game_root / "Engine" / "Binaries" / "ThirdParty" / "Oodle" / "Win64",
            ]
    out: list[Path] = []
    for directory in dirs:
        candidate = directory / OODLE_DLL
        if candidate not in out:
            out.append(candidate)
    return out


def oodle_available(pak: Path | None = None) -> bool:
    """Check whether a verified local Oodle library is available."""
    try:
        if _hash_ok(oodle_cache_dir() / OODLE_DLL):
            return True
    except OodleError:
        pass
    return any(_hash_ok(c) for c in _local_oodle_candidates(pak))


def ensure_oodle(pak: Path | None = None, progress=None) -> Path:
    """Locate a verified Oodle DLL locally without downloading anything.

    Check the cache and known local locations; cache a usable copy when possible.
    Raise a readable setup error if absent. Retain progress for API compatibility."""
    cache = oodle_cache_dir() / OODLE_DLL
    if _hash_ok(cache):
        return cache
    rejected = []
    for candidate in _local_oodle_candidates(pak):
        if candidate == cache or not candidate.is_file():
            continue
        if _hash_ok(candidate):
            try:
                _place(candidate, cache)
            except OodleError:
                return candidate          # Use the verified source directly if caching is unavailable.
            if _hash_ok(cache):
                return cache
            return candidate
        rejected.append(str(candidate))
    reason = "\n".join(
        f"There is a {OODLE_DLL} at {path}, but it is a different "
        "Oodle build (its checksum is not the one this tool needs)."
        for path in rejected) or "It is not in any of the usual places."
    raise _oodle_error(reason)


_decompressors: dict[Path, object] = {}


def oodle_decompressor(pak: Path | None = None, progress=None):
    """Load the Oodle library once and return its decompression wrapper."""
    dll = ensure_oodle(pak, progress)
    fn = _decompressors.get(dll)
    if fn is None:
        fn = pakfile.load_oodle(dll)
        _decompressors[dll] = fn
    return fn


def _open(pak: Path) -> pakfile.PakFile:
    """Open a Pak, loading Oodle only when a compressed entry actually requires it."""
    pak = Path(pak)

    def lazy(comp: bytes, raw_len: int) -> bytes:
        return oodle_decompressor(pak)(comp, raw_len)

    return pakfile.PakFile(pak, oodle=lazy)


def export_cfgs(cfg_files: dict[str, str], root: Path) -> list[Path]:
    """Export loose cfg patches under root using the same path rules as pack_mod.

    Normal paths are relative to GameData; // edition paths are relative to
    Content. Strip the marker before joining paths so pathlib cannot interpret
    it as a UNC network path (issue #5)."""
    root = Path(root)
    written: list[Path] = []
    for rel, content in cfg_files.items():
        target = root / rel.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def pack_mod(cfg_files: dict[str, str], out_pak: Path,
             root_files: dict[str, str | bytes] | None = None) -> Path:
    """Pack cfg_files and optional root_files into a mod Pak.

    cfg_files paths are relative to GameData; // paths are relative to Content.
    root_files are relative to the Pak mount, outside config scanning when used
    for manifests. out_pak is the destination file.

    Use a staging folder to retain established write_text newline behavior."""
    out_pak = Path(out_pak)
    out_pak.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="s2tweaker_") as tmp:
        staging = Path(tmp) / out_pak.stem
        staging.mkdir(parents=True, exist_ok=True)
        for rel, content in cfg_files.items():
            if rel.startswith("//"):
                target = staging / "Stalker2" / "Content" / rel[2:]
            else:
                target = staging / GAMEDATA_PREFIX / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for rel, content in (root_files or {}).items():
            # Root files may be nested, e.g. Stalker2/Config/UserInput.ini.
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")
        pakfile.pack_dir(staging, out_pak)

    if not out_pak.is_file():
        raise RuntimeError(f"Pak was not created: {out_pak}")
    return out_pak


def export_root_files(files: dict[str, str | bytes], root: Path) -> list[Path]:
    """Keep supplementary binary resources byte-exact in the debug export."""
    written = []
    for rel, content in files.items():
        target = Path(root) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def list_pak(pak: Path) -> list[str]:
    """List Pak entry paths without ../../../ by reading only the index.

    No decompression library is needed."""
    with _open(Path(pak)) as pk:
        return [pk.stripped(name) for name in pk.files()]


def _extract(pak: Path, out_dir: Path, patterns: list[str] | None,
             progress=None) -> int:
    """Extract matching entries under out_dir, stripping ../../../ from their paths."""
    pak, out_dir = Path(pak), Path(out_dir)
    regexes = [pakfile.glob_regex(p) for p in patterns] if patterns else None
    written = 0
    with _open(pak) as pk:
        selected = []
        for name in pk.files():
            stripped = pk.stripped(name)
            if regexes is None or pakfile.matches(regexes, stripped):
                selected.append((name, stripped))
        # Check required decompression support before writing any output.
        if pk.uses_oodle([name for name, _ in selected]):
            ensure_oodle(pak, progress)
        for name, stripped in selected:
            parts = stripped.split("/")
            if any(part in ("..", "") for part in parts):
                raise pakfile.PakError(f"refusing to write outside {out_dir}: {stripped}")
            target = out_dir.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(pk.read(name))
            written += 1
    return written


def unpack_many(pak: Path, out_dir: Path, includes: list[str],
                progress=None) -> None:
    """Extract several include globs in one pass; escape literal '[' as '[[]'."""
    _extract(pak, out_dir, list(includes), progress)


def unpack(pak: Path, out_dir: Path, include: str | None = None,
           progress=None) -> None:
    """Extract matching Pak entries, or all entries without an include glob.

    Patterns use paths without ../../../. Oodle entries require the verified
    local library or raise a setup error."""
    _extract(pak, out_dir, [include] if include else None, progress)
