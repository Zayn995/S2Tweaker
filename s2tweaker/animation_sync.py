"""Export and install the optional native animation and sound companion.

Only the companion's own files and its separate numeric profile are managed.
The generated CFG Pak remains the source of gameplay timing values.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from .animation_profile import parse
from . import sound_sync, cfgparse

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "animation_sync"
PROFILE_SLOT = "S2Tweaker_AnimationProfile_v1"
MOD_ROOT = "Stalker2/Mods/S2TRuntimeLab"
RECEIPT = MOD_ROOT + "/S2Tweaker_AnimationSync.json"
FORMAT = "S2Tweaker.AnimationSync.1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def factors(settings):
    result = {}
    for key, field in (("movement.crouch", "walk_speed_factor"),
                       ("movement.sprint", "run_speed_factor"),
                       ("movement.walk", "walk_speed_factor"),
                       ("movement.run", "run_speed_factor")):
        value = getattr(settings, field)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 100:
            raise ValueError(f"Invalid animation multiplier: {field}")
        if not math.isclose(value, 1.0, rel_tol=0, abs_tol=1e-9):
            result[key] = value
    return result


def limp_values(settings, gd):
    factor = settings.limp_speed_factor
    if type(factor) not in (int, float) or not math.isfinite(factor) or not 0 < factor <= 100:
        raise ValueError("Invalid limping multiplier.")
    if not factors(settings) and math.isclose(factor, 1):
        return {}
    ratio = 1
    if not math.isclose(factor, 1):
        if gd is None:
            raise ValueError("Load installed game data before synchronizing limping.")
        baseline = cfgparse.parse_number(gd.resolve(gd.obj, "Player", "MovementParams.LimpSpeedCoef"))
        if baseline <= 0:
            raise ValueError("The installed limping-speed coefficient is unavailable.")
        ratio = min(1, baseline * factor) / baseline
    return {"movement.limp.walk": ratio * settings.walk_speed_factor,
            "movement.limp.run": ratio * settings.run_speed_factor}


def enabled(settings):
    return ((bool(settings.animation_sync) and
             (bool(factors(settings)) or not math.isclose(settings.limp_speed_factor, 1)))
            or bool(sound_sync.action_factors(settings))
            or sound_sync.equipment_requested(settings)
            or bool(sound_sync.movement_factors(settings))
            or bool(visual_values(settings)))


def visual_values(settings):
    values = {}
    for active, value, limit, key, label in (
        (settings.weapon_sway_sync, settings.weapon_sway_pct, 400, "visual.sway", "Weapon idle sway"),
        (settings.weapon_shot_sync, settings.weapon_shot_pct, 100, "visual.shot", "Firing animation movement"),
    ):
        if not active:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= limit:
            raise ValueError(f"{label} supports 0% to {limit}%.")
        # Positive profile values encode a zero-capable factor plus one.
        if not math.isclose(value, 100):
            values[key] = 1 + value / 100
    return values


def profile_values(settings, gd=None):
    values = factors(settings) if settings.animation_sync else {}
    if settings.animation_sync:
        values.update(limp_values(settings, gd))
    return {**values, **sound_sync.profile_values(settings, gd), **visual_values(settings)}


def profile_bytes(settings, gd=None):
    values = profile_values(settings, gd)
    payload = "S2T1" + "".join(f"\n{k}={v:.12f}".rstrip("0").rstrip(".")
                              for k, v in sorted(values.items()))
    return parse((ASSETS / "profile.sav").read_bytes()).encode(payload)


def default_save_dir():
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise OSError("LOCALAPPDATA is unavailable; cannot locate the animation profile directory.")
    return Path(local) / "Stalker2" / "Saved" / "SaveGames"


def _relative(name):
    path = PurePosixPath(name)
    if ("\\" in name or ":" in name or path.is_absolute() or ".." in path.parts
            or not name.startswith(MOD_ROOT + "/")):
        raise ValueError("Invalid companion file path.")
    return path


def runtime_files():
    manifest = json.loads((ASSETS / "runtime.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or not manifest.get("files"):
        raise ValueError("Unsupported animation companion bundle.")
    with zipfile.ZipFile(ASSETS / "runtime.zip") as archive:
        if len(archive.infolist()) != len(manifest["files"]) or set(archive.namelist()) != set(manifest["files"]):
            raise ValueError("Animation companion inventory mismatch.")
        result = {}
        for info in archive.infolist():
            _relative(info.filename)
            if info.file_size > 16 * 1024 * 1024:
                raise ValueError("Animation companion file exceeds the expected size.")
            data = archive.read(info)
            if digest(data) != manifest["files"][info.filename]:
                raise ValueError(f"Animation companion checksum failed: {info.filename}")
            result[info.filename] = data
    return result


def _target(root, relative):
    root = Path(root).resolve()
    result = root.joinpath(*_relative(relative).parts)
    if not result.resolve().is_relative_to(root):
        raise ValueError("Companion path resolves outside the selected game folder.")
    return result


def _profile_target(save_dir):
    directory = Path(save_dir).resolve()
    target = directory / (PROFILE_SLOT + ".sav")
    if target.is_symlink() or not target.resolve().is_relative_to(directory):
        raise ValueError("Animation profile path must remain in the save directory.")
    return target


def _owned_files(game_dir):
    path = _target(game_dir, RECEIPT)
    if not path.exists():
        return {}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("format") != FORMAT or not isinstance(receipt.get("files"), dict):
        raise ValueError("Unrecognized animation companion installation record.")
    owned = {}
    for name, expected in receipt["files"].items():
        target = _target(game_dir, name)
        if name == RECEIPT:
            raise ValueError("Invalid companion installation record.")
        if target.exists() and digest(target.read_bytes()) != expected:
            raise ValueError(f"Companion file was changed outside S2Tweaker: {target.name}")
        owned[target] = None
    owned[path] = None
    return owned


def installation_changes(settings, game_dir, save_dir=None, *, gd=None):
    """Preflight all destinations before replacing a generated Pak or companion."""
    changes = _owned_files(game_dir)
    active = enabled(settings)
    if not active and not changes:
        return {}
    profile = _profile_target(save_dir if save_dir is not None else default_save_dir())
    if profile.exists():
        parse(profile.read_bytes())  # Reject every class except the companion profile.
    if active:
        payload = runtime_files()
        for relative, data in payload.items():
            target = _target(game_dir, relative)
            if target.exists() and target not in changes and target.read_bytes() != data:
                raise ValueError(f"A different mod already occupies {target}.")
            changes[target] = data
        receipt = {"format": FORMAT, "files": {p: digest(b) for p, b in payload.items()},
                   "profile_slot": PROFILE_SLOT, "factors": profile_values(settings, gd)}
        changes[_target(game_dir, RECEIPT)] = json.dumps(receipt, indent=2).encode("utf-8")
        changes[profile] = profile_bytes(settings, gd)
    elif changes:
        changes[profile] = None
    return changes


def export_files(settings, out_pak, *, gd=None):
    """Prepare the same companion files for portable and loose debug exports."""
    if not enabled(settings):
        return {}
    files = runtime_files()
    files["Profile/" + PROFILE_SLOT + ".sav"] = profile_bytes(settings, gd)
    files["S2Tweaker_AnimationSync.json"] = json.dumps({
        "format": FORMAT, "cfg_pak": Path(out_pak).name, "factors": profile_values(settings, gd),
    }, indent=2).encode("utf-8")
    files["README.txt"] = (
        "S2Tweaker native animation and sound companion (experimental)\n\n"
        "Windows PC only.\n"
        "Exit the game before installation; restart it after changing the profile.\n"
        "1. Copy Stalker2 into the game installation directory.\n"
        "2. Copy Profile/" + PROFILE_SLOT + ".sav into\n"
        "   %LOCALAPPDATA%/Stalker2/Saved/SaveGames/\n"
        "3. Install the matching " + Path(out_pak).name + " in Stalker2/Content/Paks/~mods/.\n\n"
        "Use only one active S2Tweaker companion profile. The .sav above contains\n"
        "only numeric configuration, not player progress. Never replace campaign saves.\n"
        "For automatic installation, use Install to ~mods in S2Tweaker instead.\n"
        "To remove this companion, delete only Stalker2/Mods/S2TRuntimeLab and\n"
        "the named animation profile. Restore movement settings in the CFG Pak separately.\n\n"
        "Walk, run, crouch and sprint animation rates follow the selected movement factors.\n"
        "Active action montages retain native gameplay timing. Existing animation\n"
        "assets are not replaced. Optional sound controls change reload/jam or\n"
        "movement sound duration independently without replacing original media.\n"
        "Optional idle-sway and firing-pose controls adjust animation amplitude.\n"
        "The firing control retains full reload/equip motion; camera shake and\n"
        "weapon inertia remain separate. Other slot-layer replacements can conflict.\n"
        "Other audio mods using the same effect slots can conflict. This is not\n"
        "a general fix for every animation/sound; campaign testing remains open.\n"
    ).encode("utf-8")
    return files


def export_changes(settings, out_pak, *, gd=None):
    target = Path(out_pak).with_name(Path(out_pak).stem + "_AnimationSync.zip")
    if target.exists():
        with zipfile.ZipFile(target) as existing:
            if json.loads(existing.read("S2Tweaker_AnimationSync.json")).get("format") != FORMAT:
                raise ValueError("The companion export path contains a different archive.")
    files = export_files(settings, out_pak, gd=gd)
    if not files:
        return {target: None} if target.exists() else {}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    return {target: stream.getvalue()}


def debug_changes(settings, out_pak, root, *, gd=None):
    """Export loose companion files and decoded configuration beside CFG patches.

    Clear known previous companion outputs when disabled, preserving unrelated
    debug notes. No files from the installed game or campaign saves are read.
    """
    root = Path(root).resolve()
    directory = root / "AnimationSync"
    if directory.is_symlink() or not directory.resolve().is_relative_to(root):
        raise ValueError("Companion debug output must remain inside the debug folder.")
    marker = directory / "S2Tweaker_AnimationSync.json"
    previous = set()
    if marker.exists():
        if json.loads(marker.read_text(encoding="utf-8")).get("format") != FORMAT:
            raise ValueError("The companion debug folder contains a different export.")
        previous = set(runtime_files()) | {
            "S2Tweaker_AnimationSync.json", "README.txt",
            "Profile/" + PROFILE_SLOT + ".sav", "Profile/" + PROFILE_SLOT + ".txt",
        }
    files = export_files(settings, out_pak, gd=gd)
    if files:
        profile = files["Profile/" + PROFILE_SLOT + ".sav"]
        files["Profile/" + PROFILE_SLOT + ".txt"] = (parse(profile).payload + "\n").encode("utf-8")
    changes = {}
    for name in sorted(previous | set(files)):
        target = directory.joinpath(*PurePosixPath(name).parts)
        if target.is_symlink() or not target.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Companion debug file resolves outside its output folder.")
        if name in files or target.exists():
            changes[target] = files.get(name)
    return changes


@contextmanager
def file_transaction(changes):
    """Rollback companion changes if the generated CFG Pak cannot be committed."""
    original, staged, applied = {}, {}, []
    try:
        for path, data in changes.items():
            path = Path(path)
            original[path] = path.read_bytes() if path.exists() else None
            if data is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(prefix=".s2t-animation-", dir=path.parent)
                staged[path] = Path(name)
                with os.fdopen(fd, "wb") as output:
                    output.write(data)
        for path, data in changes.items():
            path = Path(path)
            if data is None:
                path.unlink(missing_ok=True)
            else:
                os.replace(staged[path], path)
            applied.append(path)
        yield
    except BaseException:
        for path in reversed(applied):
            if original[path] is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original[path])
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)
