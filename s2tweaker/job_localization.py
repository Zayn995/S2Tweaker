"""Supplemental journal translations, read lazily from the loaded installation."""
import hashlib
import json
from pathlib import Path
import re
import tempfile

from . import localization, pakio

NAMESPACE = "ST_S2BaseGameLocalization"
PREFIX = "Stalker2/Content/Localization/Game/"
CACHE_VERSION = 1


def _validate(rows, cultures, aliases):
    if not isinstance(rows, dict) or set(rows) != set(cultures):
        raise ValueError("Incomplete job localization cultures.")
    for entries in rows.values():
        if not isinstance(entries, dict) or set(entries) != set(aliases):
            raise ValueError("Incomplete job localization aliases.")
        for row in entries.values():
            if (not isinstance(row, (list, tuple)) or len(row) != 2
                    or type(row[0]) is not int or row[0] != 0
                    or not isinstance(row[1], str) or not row[1] or "\0" in row[1]):
                raise ValueError("Unsupported job localization source entry.")


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
            cache = gd.dir / ".optional" / f"job-localization-{signature}.json"
            rows = None
            if cache.is_file():
                try:
                    saved = json.loads(cache.read_text(encoding="utf-8"))
                    candidate = saved["entries"]
                    checksum = hashlib.sha256(json.dumps(candidate, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                    if saved["identity"] != identity or saved["sha256"] != checksum:
                        raise ValueError("Invalid job localization cache.")
                    _validate(candidate, paths, aliases)
                    rows = candidate
                except (ValueError, KeyError, TypeError, OSError):
                    pass  # A damaged derived cache is rebuilt from the current installation.
            if rows is None:
                if gd._progress:
                    gd._progress("Preparing job translations from the installed languages ...")
                rows = {}
                for culture, path in sorted(paths.items()):
                    source = localization.read_resource(pak.read(path))
                    entries = {}
                    for alias, original in aliases.items():
                        if (NAMESPACE, alias) in source or (NAMESPACE, original) not in source:
                            raise ValueError(f"Unsupported job translation identity in {culture}: {original}")
                        entries[alias] = source[NAMESPACE, original]
                    rows[culture] = entries
                _validate(rows, paths, aliases)
                current()
                cache.parent.mkdir(parents=True, exist_ok=True)
                saved = {"identity": identity, "entries": rows,
                         "sha256": hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
                with tempfile.TemporaryDirectory(prefix="job-text-", dir=cache.parent) as temp:
                    target = Path(temp) / "entries.json"
                    target.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
                    current()
                    target.replace(cache)
        current()
        return {PREFIX + culture + "/S2Tweaker_JobLocalization.locres":
                localization.write_resource(NAMESPACE, entries) for culture, entries in sorted(rows.items())}
