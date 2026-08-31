"""Pak-Erzeugung fuer S.T.A.L.K.E.R. 2 (ueber repak.exe).

Funktionierende Mod-Paks im Spiel sind: Version V8B, Mount-Point ../../../,
unkomprimiert, unverschluesselt — exakt die repak-Defaults.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GAMEDATA_PREFIX = "Stalker2/Content/GameLite/GameData"


def find_repak() -> Path | None:
    """repak.exe finden: neben der EXE gebuendelt, im tools-Ordner oder im PATH."""
    candidates = []
    if getattr(sys, "frozen", False):  # PyInstaller
        candidates.append(Path(sys._MEIPASS) / "repak.exe")  # type: ignore[attr-defined]
        candidates.append(Path(sys.executable).parent / "repak.exe")
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "tools" / "repak.exe")
    found = shutil.which("repak")
    if found:
        candidates.append(Path(found))
    for c in candidates:
        if c.is_file():
            return c
    return None


def pack_mod(cfg_files: dict[str, str], out_pak: Path, repak_exe: Path | None = None) -> Path:
    """cfg-Dateien in eine Mod-Pak packen.

    cfg_files: {"ObjPrototypes/zzz_S2Tweaker_Player.cfg": "<cfg-Text>", ...}
               Pfade relativ zu Stalker2/Content/GameLite/GameData/.
               Absolute Sonderfaelle (DLC) koennen mit "//" beginnen und sind
               dann relativ zu Stalker2/Content/ zu verstehen.
    out_pak:   Zielpfad der .pak-Datei (z.B. ...\\~mods\\zzz_S2Tweaker_P.pak).
    """
    repak = repak_exe or find_repak()
    if repak is None:
        raise FileNotFoundError("repak.exe nicht gefunden (tools/repak.exe fehlt?)")

    out_pak = Path(out_pak)
    out_pak.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="s2tweaker_") as tmp:
        # repak benutzt den Namen des Eingabeordners als Pak-Namen, deshalb
        # bauen wir einen Ordner, der exakt wie die Ziel-Pak (ohne .pak) heisst.
        staging = Path(tmp) / out_pak.stem
        # Auch bei leerem cfg_files anlegen: repak bricht sonst mit
        # "Input is not a directory" ab statt eine (leere) Pak zu bauen.
        staging.mkdir(parents=True, exist_ok=True)
        for rel, content in cfg_files.items():
            if rel.startswith("//"):
                target = staging / "Stalker2" / "Content" / rel[2:]
            else:
                target = staging / GAMEDATA_PREFIX / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        result = subprocess.run(
            [str(repak), "pack", "-q", str(staging), str(out_pak)],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode != 0:
            raise RuntimeError(f"repak pack fehlgeschlagen: {result.stderr.strip()}")

    if not out_pak.is_file():
        raise RuntimeError(f"Pak wurde nicht erzeugt: {out_pak}")
    return out_pak


def unpack(pak: Path, out_dir: Path, include: str | None = None,
           repak_exe: Path | None = None) -> None:
    """Pak entpacken (fuer die Vanilla-GameData-Extraktion)."""
    repak = repak_exe or find_repak()
    if repak is None:
        raise FileNotFoundError("repak.exe nicht gefunden")
    cmd = [str(repak), "unpack", str(pak), "-o", str(out_dir), "-q", "-f"]
    if include:
        cmd += ["-i", include]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"repak unpack fehlgeschlagen: {result.stderr.strip()}")
