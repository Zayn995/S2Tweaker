"""Spiel-Installation finden (Steam/GOG/Xbox) und Pfade bereitstellen."""

from __future__ import annotations

import re
from pathlib import Path

GAME_DIR_NAME = "S.T.A.L.K.E.R. 2 Heart of Chornobyl"


def _steam_roots() -> list[Path]:
    roots = []
    for base in (Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Games\Steam")):
        if base.is_dir():
            roots.append(base)
    # Alle Steam-Bibliotheken aus libraryfolders.vdf einsammeln
    extra = []
    for root in roots:
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            try:
                text = vdf.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                    extra.append(Path(m.group(1).replace("\\\\", "\\")))
            except OSError:
                pass
    return roots + extra


def find_game() -> Path | None:
    """Installationsordner des Spiels suchen."""
    candidates: list[Path] = []
    for lib in _steam_roots():
        candidates.append(lib / "steamapps" / "common" / GAME_DIR_NAME)
    for drive in "CDEFGH":
        candidates.append(Path(f"{drive}:/Games/Steam/steamapps/common") / GAME_DIR_NAME)
        candidates.append(Path(f"{drive}:/GOG Games") / GAME_DIR_NAME)
        candidates.append(Path(f"{drive}:/XboxGames") / GAME_DIR_NAME)
    for c in candidates:
        if is_game_dir(c):
            return c
    return None


def is_game_dir(path: Path) -> bool:
    return (Path(path) / "Stalker2" / "Content" / "Paks").is_dir()


def paks_dir(game: Path) -> Path:
    return Path(game) / "Stalker2" / "Content" / "Paks"


def mods_dir(game: Path) -> Path:
    return paks_dir(game) / "~mods"


# Steam-App-ID von S.T.A.L.K.E.R. 2 — Ablage abonnierter Workshop-Mods.
STEAM_WORKSHOP_APPID = "1643320"


def steam_workshop_dir(game: Path) -> Path | None:
    """Workshop-Ablage der Steam-Bibliothek dieser Installation, oder None.

    Steam legt abonnierte Mods NICHT in ~mods ab, sondern in
    <Bibliothek>\\steamapps\\workshop\\content\\1643320\\<item-id>\\ —
    das Spiel liest sie von dort (verifiziert 02.09.: nichts wird in den
    Spielordner kopiert). GOG-Installationen haben keinen Workshop."""
    parts = [p.lower().rstrip("\\/") for p in game.parts]
    if len(parts) >= 3 and parts[-2] == "common" and parts[-3] == "steamapps":
        ws = (game.parent.parent / "workshop" / "content"
              / STEAM_WORKSHOP_APPID)
        if ws.is_dir():
            return ws
    return None


def main_pak(game: Path) -> Path:
    return paks_dir(game) / "pakchunk0-Windows.pak"
