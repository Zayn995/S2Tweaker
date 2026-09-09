"""Portable editor state, history and profiles. No GUI or game process access."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile

GROUPS = ("sliders", "checks", "cats", "weapon_overrides", "weapon_calibers",
          "ammo_overrides", "scope_overrides", "armor_overrides",
          "mutant_overrides", "faction_relations", "armor_custom")
OVERRIDES = {"weapon_overrides", "ammo_overrides", "scope_overrides",
             "armor_overrides", "mutant_overrides"}
NESTED_GROUPS = OVERRIDES | {"armor_custom"}


def clone(value):
    return deepcopy(value)


def equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=0, abs_tol=1e-9)
    return a == b


def flatten(value, prefix=()):
    result = {}
    for key, item in value.items():
        path = prefix + (str(key),)
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def state_only(data):
    """Validate external profile/manifest input before it reaches widget setters."""
    if not isinstance(data, dict):
        raise ValueError("The settings must be a JSON object.")
    result = {}
    for group in GROUPS:
        value = data.get(group, {})
        if not isinstance(value, dict):
            raise ValueError(f"Invalid settings group: {group}")
        for path, leaf in flatten(value).items():
            depth = 2 if group in NESTED_GROUPS else 1
            if len(path) != depth or any(not part or len(part) > 400 for part in path):
                raise ValueError(f"Invalid setting path in {group}")
            if group in ("checks", "cats"):
                valid = isinstance(leaf, bool) or type(leaf) is int and leaf in (0, 1)
            elif group == "weapon_calibers":
                valid = isinstance(leaf, str) and 0 < len(leaf) < 100
            else:
                valid = type(leaf) in (int, float) and math.isfinite(leaf)
            if not valid:
                raise ValueError(f"Invalid value in {group}: {'.'.join(path)}")
        if group == "armor_custom":
            from .armor_extensions import clean
            result[group] = {sid: clean(params) for sid, params in value.items()}
        else:
            result[group] = clone(value)
    return result


def differences(left, right, defaults=None):
    """Compare settings, treating absent old-profile fields as their neutral values."""
    a, b = flatten(state_only(left)), flatten(state_only(right))
    neutral = flatten(defaults or {})
    result = []
    for path in sorted(a.keys() | b.keys()):
        fallback = neutral.get(path)
        if path[0] in OVERRIDES:
            fallback = 1.0
        elif path[0] == "armor_custom":
            fallback = -1
        old, new = a.get(path, fallback), b.get(path, fallback)
        if not equal(old, new):
            result.append((path, old, new))
    return result


class History:
    """Whole-edit transactions; callers commit once at the end of a slider drag."""
    def __init__(self, state, limit=100):
        self.current = clone(state)
        self.past = []
        self.future = []
        self.limit = limit

    def commit(self, state):
        if state == self.current:
            return False
        self.past.append(self.current)
        self.past = self.past[-self.limit:]
        self.current = clone(state)
        self.future.clear()
        return True

    def undo(self):
        if not self.past:
            return None
        self.future.append(self.current)
        self.current = self.past.pop()
        return clone(self.current)

    def redo(self):
        if not self.future:
            return None
        self.past.append(self.current)
        self.current = self.future.pop()
        return clone(self.current)


def write_json(path, data):
    """Replace one portable data file atomically; never write to an executable."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@dataclass
class Profile:
    path: Path
    name: str
    description: str
    state: dict
    mod_name: str = ""


def read_profile(path):
    path = Path(path)
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Profile is larger than 4 MB.")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    state = state_only(data)
    meta = data.get("_profile", {})
    if not isinstance(meta, dict):
        meta = {}
    return Profile(path, str(meta.get("name") or path.stem),
                   str(meta.get("description") or ""), state,
                   str(meta.get("mod_name") or ""))


def save_profile(path, state, name, description="", mod_name=""):
    data = state_only(state)
    # Keep the traditional top-level groups so older S2Tweaker can load it.
    data["_profile"] = {"version": 1, "name": str(name),
                        "description": str(description), "mod_name": str(mod_name)}
    write_json(path, data)


def unique_profile_path(directory, name):
    directory = Path(directory)
    stem = "".join(c for c in name if c.isalnum() or c in " _-").strip(" .")[:80] or "Profile"
    path = directory / (stem + ".json")
    index = 2
    while path.exists():
        path = directory / f"{stem} ({index}).json"
        index += 1
    return path
