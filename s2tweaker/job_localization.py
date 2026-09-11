"""Extend installed Game.locres resources with isolated journal identities."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile
import zlib

from . import localization, pakio

NAMESPACE = "ST_S2BaseGameLocalization"
PREFIX = "Stalker2/Content/Localization/Game/"
CACHE_VERSION = 2


def resources(gd, aliases):
    if not aliases:
        return {}
    if gd._source_pak is None:
        raise FileNotFoundError("Job translations need the game installation. Select your game folder and reload game data.")

    def current():
        if gd._pak_stamp() != gd._source_stamp:
            raise RuntimeError("Game files changed. Reload game data before building job translations.")

    with gd._optional_lock:
        current()
        with pakio._open(gd._source_pak) as pak:
            paths = {}
            for path in pak.files():
                clean = pak.stripped(path)
                if clean.startswith(PREFIX) and clean.endswith("/Game.locres"):
                    culture = clean[len(PREFIX):-len("/Game.locres")]
                    if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", culture) or culture in paths:
                        raise ValueError("Unsupported game localization layout.")
                    paths[culture] = path
            if "en" not in paths:
                raise ValueError("The installed game has no native English localization resource.")
            identity = {"version": CACHE_VERSION, "source": list(gd._source_stamp),
                        "aliases": aliases, "cultures": sorted(paths)}
            signature = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            cache = gd.dir / ".optional" / f"job-localization-{signature}.zip"
            names = {culture: PREFIX + culture + "/Game.locres" for culture in paths}
            files = None
            if cache.is_file():
                try:
                    with zipfile.ZipFile(cache) as archive:
                        expected = {"manifest.json", *names.values()}
                        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
                            raise ValueError("Incomplete job localization cache.")
                        saved = json.loads(archive.read("manifest.json"))
                        if saved["identity"] != identity or set(saved["files"]) != set(names.values()):
                            raise ValueError("Invalid job localization cache.")
                        candidate = {}
                        for name in sorted(names.values()):
                            raw = archive.read(name)
                            if saved["files"][name] != {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}:
                                raise ValueError("Damaged job localization cache.")
                            candidate[name] = raw
                        files = candidate
                except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, RuntimeError, zlib.error):
                    pass  # Rebuild a damaged derived cache from the installation.
            if files is None:
                if gd._progress:
                    gd._progress("Preparing job translations from all installed languages ...")
                files = {}
                for culture, path in sorted(paths.items()):
                    files[names[culture]] = localization.append_aliases(pak.read(path), NAMESPACE, aliases)
                current()
                cache.parent.mkdir(parents=True, exist_ok=True)
                saved = {"identity": identity, "files": {
                    name: {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                    for name, raw in files.items()}}
                with tempfile.TemporaryDirectory(prefix="job-text-", dir=cache.parent) as temp:
                    target = Path(temp) / "resources.zip"
                    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        archive.writestr("manifest.json", json.dumps(saved, sort_keys=True))
                        for name, raw in sorted(files.items()):
                            archive.writestr(name, raw)
                    current()
                    target.replace(cache)
        current()
        return files
