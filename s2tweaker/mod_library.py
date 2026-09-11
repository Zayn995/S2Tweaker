"""Read our manifests and retain previous Paks before replacing them."""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from . import editor_state, pakfile, pakio, cfgparse

MANIFEST = "S2Tweaker_Manifest.json"


@dataclass
class OwnMod:
    path: Path
    manifest: dict

    @property
    def name(self):
        return str(self.manifest.get("mod_name") or self.path.stem)


def read_own_mod(path):
    path = Path(path)
    with pakfile.PakFile(path) as pak:
        key = next((name for name in pak.files() if pak.stripped(name) == MANIFEST), None)
        if key is None:
            return None
        if pak.entries[key].uncompressed > 4 * 1024 * 1024:
            raise ValueError("S2Tweaker manifest is larger than 4 MB.")
        data = json.loads(pak.read(key).decode("utf-8-sig"))
    if not isinstance(data, dict) or not str(data.get("tool", "")).startswith("S2Tweaker "):
        return None
    if data.get("manifest_version") != 1:
        raise ValueError("Unsupported S2Tweaker manifest version.")
    editor_state.state_only(data.get("ui_state"))
    return OwnMod(path, data)


def list_own_mods(roots):
    mods, errors, seen = [], [], set()
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.pak")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                mod = read_own_mod(path)
                if mod is not None:
                    mods.append(mod)
            except (OSError, ValueError, pakfile.PakError) as exc:
                errors.append(f"{path.name}: {exc}")
    return mods, errors


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def backup_pak(path, directory):
    path, directory = Path(path), Path(directory)
    if not path.exists():
        return None
    if path.suffix.lower() != ".pak":
        raise ValueError("Only Pak files can be backed up here.")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = directory / f"{path.stem}_{stamp}.pak"
    # Exclusive creation avoids overwriting a previous backup.
    with path.open("rb") as source, backup.open("xb") as target:
        shutil.copyfileobj(source, target)
    if digest(path) != digest(backup):
        raise OSError("Pak backup verification failed. Original was preserved.")
    return backup


def build_safely(patches, target, root_files, history_dir):
    target = Path(target)
    if target.suffix.lower() != ".pak":
        raise ValueError("The generated file must be a .pak.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".s2tweaker-build-", dir=target.parent) as directory:
        staged = Path(directory) / target.name
        pakio.pack_mod(patches, staged, root_files=root_files)
        expected = dict(root_files)
        for path, value in patches.items():
            full = "Stalker2/Content/" + path[2:] if path.startswith("//") else pakio.GAMEDATA_PREFIX + "/" + path
            expected[full] = value
        with pakfile.PakFile(staged) as pak:
            actual = {pak.stripped(key): key for key in pak.files()}
            if set(actual) != set(expected):
                raise ValueError("Generated Pak inventory did not match its input.")
            for path, value in expected.items():
                # pack_mod uses platform text newlines; compare decoded content.
                raw = pak.read(actual[path])
                matches = (raw == value if isinstance(value, bytes) else
                           raw.decode("utf-8").replace("\r\n", "\n") == value.replace("\r\n", "\n"))
                if not matches:
                    raise ValueError(f"Generated Pak readback failed: {path}")
        backup = backup_pak(target, history_dir)
        os.replace(staged, target)
    return backup


def restore_pak(source, target, history_dir):
    """User-selected own Pak restore. No manifest-supplied filesystem paths."""
    source, target = Path(source), Path(target)
    if read_own_mod(source) is None or target.suffix.lower() != ".pak":
        raise ValueError("Choose an S2Tweaker Pak and a .pak destination.")
    if source.resolve() == target.resolve():
        raise ValueError("Source and destination are the same file.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".s2tweaker-restore-", dir=target.parent) as directory:
        staged = Path(directory) / target.name
        shutil.copyfile(source, staged)
        if digest(source) != digest(staged):
            raise OSError("Restore copy verification failed.")
        backup = backup_pak(target, history_dir)
        os.replace(staged, target)
    return backup


def patch_leaves(text):
    def walk(node, path):
        for key, value in node.values.items():
            yield path + (key,), value
        for name, child in node.children.items():
            yield from walk(child, path + (name,))
    return list(walk(cfgparse.parse(text), ()))


def own_patch_targets(path):
    """Exact cfg targets only; overlaps are evidence, not a full load-order simulator."""
    if read_own_mod(path) is None:
        raise ValueError("This Pak was not identified as an S2Tweaker mod.")
    targets = {}
    with pakfile.PakFile(path) as pak:
        for key in pak.files():
            name = pak.stripped(key)
            if name.endswith(".cfg") and ("/GameData/" in name or "/DLCGameData/" in name):
                directory, filename = name.rsplit("/", 1)
                # Unbinarized cfg patches sit beside their base, not in a
                # per-prototype folder. Keep separate bases distinct.
                family = (directory + "/" + filename.split(".cfg_patch_", 1)[0]
                          if ".cfg_patch_" in filename else directory)
                for leaf, value in patch_leaves(pak.read(key).decode("utf-8-sig")):
                    targets[(family, leaf)] = value
            elif name == "Stalker2/Config/UserInput.ini":
                targets[(name, ())] = pak.read(key).decode("utf-8-sig")
    return targets


def compare_own_mods(left, right):
    a, b = own_patch_targets(left), own_patch_targets(right)
    return [(path, a[path], b[path]) for path in sorted(a.keys() & b.keys())]
