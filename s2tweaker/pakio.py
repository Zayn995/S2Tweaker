"""Pak-Erzeugung fuer S.T.A.L.K.E.R. 2 (ueber repak.exe).

Funktionierende Mod-Paks im Spiel sind: Version V8B, Mount-Point ../../../,
unkomprimiert, unverschluesselt — exakt die repak-Defaults.

Oodle: wird gebraucht, aber NIE heruntergeladen
----------------------------------------------
pakchunk0 des Spiels ist Oodle-komprimiert, deshalb braucht repak zum
ENTPACKEN die proprietaere oo2core_9_win64.dll (zum PACKEN nicht — unsere
Paks sind unkomprimiert, verifiziert).

Beschafft wird sie seit 04.09.2026 NICHT mehr von uns. Zwei Gruende:

  1. Ein Programm, das zur Laufzeit eine Bibliothek aus dem Netz holt und
     als nativen Code laedt, zeigt exakt das Verhalten eines Droppers —
     einer der Gruende, warum Virenscanner solche Werkzeuge markieren.
     Die Freigabe auf Nexus scheiterte an genau solchen Fehlalarmen.
  2. Der Download war ohnehin die fehleranfaelligste Stelle: Bugreport
     foxce (31.08.2026), Abbruch mit InvalidCertificate(UnknownIssuer)
     hinter einer AV-/Proxy-HTTPS-Inspektion.

Stattdessen: lokal suchen (SHA-256 immer pruefen, die Datei wird gleich
darauf als nativer Code geladen), und wenn sie fehlt, den Nutzer per
Klartext-Dialog bitten, sie einmal selbst danebenzulegen — mit Link und
Zielordner (OODLE_HELP).

Auch das mitgelieferte repak kann nicht mehr laden: es wird aus dem
Quellcode gebaut, und dabei wird die Download-Funktion samt HTTP-/TLS-
Stack entfernt (siehe tools/build_repak.py). Nachgemessen: rustls 113 -> 0,
ureq 66 -> 0 Vorkommen im Binaercode.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GAMEDATA_PREFIX = "Stalker2/Content/GameLite/GameData"

# Exakt die Werte, die in repak 0.2.3 einkompiliert sind (aus repak.exe
# ausgelesen) — nur mit diesem Hash akzeptiert repak die DLL.
OODLE_DLL = "oo2core_9_win64.dll"
OODLE_SHA256 = "6f5d41a7892ea6b2db420f2458dad2f84a63901c9a93ce9497337b16c195f457"
OODLE_URL = (
    "https://github.com/WorkingRobot/OodleUE/raw/refs/heads/main/Engine/Source"
    "/Programs/Shared/EpicGames.Oodle/Sdk/2.9.10/win/redist/" + OODLE_DLL
)

# Erwartete Groesse ~640 KB; alles deutlich Groessere ist keine Antwort,
# die wir haben wollen (Blockseite, Captive Portal, boesartiger Proxy).
OODLE_MAX_BYTES = 8 << 20
OODLE_TIMEOUT_TOTAL = 90.0

OODLE_HELP = """S2Tweaker needs the Oodle decompression library ({dll})
to read the packed config files of your game, and it is not on this PC yet.

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
again. It has to be exactly the build repak expects (SHA-256 starting
with {hash8}); other Oodle 2.9.x builds are rejected on purpose.

You may already have this file: every Unreal Engine installation ships
it, and so do some other S.T.A.L.K.E.R. 2 modding tools.

Note: BUILDING a mod pak never needs Oodle - only reading the vanilla
values out of your game does. If you have loaded game data before, your
cached values keep working without it."""


class OodleError(RuntimeError):
    """Oodle-DLL fehlt und konnte nicht beschafft werden (Klartext-Hilfe)."""


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
    """Ordner der EXE (gefroren) bzw. des Projekts (Entwicklung)."""
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


def _oodle_error(reason: str, target: Path | None = None) -> "OodleError":
    where = str(target.parent) if target is not None else "your S2Tweaker folder"
    return OodleError(OODLE_HELP.format(
        dll=OODLE_DLL, url=OODLE_URL, hash8=OODLE_SHA256[:8],
        reason=reason, target=where))


def oodle_cache_dir() -> Path:
    """Dauerhafter Ablageort der DLL — portabel neben der EXE.

    Falls dort nicht geschrieben werden darf (EXE in Programme\\ o.ae.),
    weicht der Cache nach %LOCALAPPDATA% aus (in README/Nexus dokumentiert)."""
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
    """Kopieren OHNE Attribute (copy2 wuerde ein Read-only-Flag vererben und
    den Cache damit unersetzbar machen) und ueber eine evtl. vorhandene
    schreibgeschuetzte Datei hinweg."""
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
    """Stellen, an denen eine brauchbare DLL schon liegen koennte."""
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
    """Liegt irgendwo eine brauchbare Oodle-DLL? (fuer die Pruefung beim Start)"""
    repak = find_repak()
    if repak is not None and _hash_ok(repak.parent / OODLE_DLL):
        return True
    try:
        if _hash_ok(oodle_cache_dir() / OODLE_DLL):
            return True
    except OodleError:
        pass
    return any(_hash_ok(c) for c in _local_oodle_candidates(pak))


def ensure_oodle(repak: Path, pak: Path | None = None, progress=None) -> None:
    """Die (echte) Oodle-DLL neben repak.exe legen — OHNE Download.

    Gesucht wird ausschliesslich LOKAL. Fehlt die Datei, gibt es einen
    Klartext-Fehler mit Anleitung; heruntergeladen wird nichts (Begruendung
    im Modul-Kopf). `progress` bleibt nur der Signatur wegen erhalten.

    Es wird immer der SHA-256 geprueft, nie nur die Existenz — die Datei
    wird gleich darauf von repak als nativer Code geladen."""
    target = repak.parent / OODLE_DLL
    if _hash_ok(target):
        return

    cache = oodle_cache_dir() / OODLE_DLL
    if not _hash_ok(cache):
        source, rejected = None, []
        for candidate in _local_oodle_candidates(pak):
            if candidate == cache or not candidate.is_file():
                continue
            if _hash_ok(candidate):
                source = candidate
                break
            rejected.append(str(candidate))
        if source is None:
            reason = "\n".join(
                f"There is a {OODLE_DLL} at {path}, but it is a different "
                "Oodle build (its checksum is not the one repak needs)."
                for path in rejected) or "It is not in any of the usual places."
            raise _oodle_error(reason, target)
        _place(source, cache)

    if target != cache:
        _place(cache, target)
    if not _hash_ok(target):
        raise _oodle_error(
            f"The library next to repak.exe ({target}) did not pass the "
            f"checksum check after copying.", target)


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


def export_cfgs(cfg_files: dict[str, str], root: Path) -> list[Path]:
    """Die Patch-Dateien als lose .cfg unter root ablegen (Debug-Export).

    Gleiche Pfad-Regel wie pack_mod(): normale Eintraege landen direkt unter
    root (wie bisher, z.B. root/DifficultyPrototypes/..._patch_X.cfg), die
    "//"-Eintraege der Editions-Waffen unter root/GameLite/DLCGameData/...

    GitHub Issue #5 (KobaltRaven, 03.09.2026): der fruehere Export machte
    `root / rel` — und ein rel, das mit "//" beginnt, ist fuer pathlib ein
    ABSOLUTER UNC-Pfad (\\\\GameLite\\DLCGameData\\...), der die Basis
    verdraengt. mkdir versuchte dann, einen Netzwerkpfad anzulegen
    (WinError 53), sobald ein Editions-Patch dabei war — also bei jedem
    Waffen-Tweak seit v1.14.0 mit angehaktem Debug. Die Pak war zu dem
    Zeitpunkt laengst gebaut; der Benutzer sah nur den Traceback."""
    root = Path(root)
    written: list[Path] = []
    for rel, content in cfg_files.items():
        target = root / rel.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written


def pack_mod(cfg_files: dict[str, str], out_pak: Path,
             repak_exe: Path | None = None,
             root_files: dict[str, str] | None = None) -> Path:
    """cfg-Dateien in eine Mod-Pak packen.

    cfg_files: {"ObjPrototypes/zzz_S2Tweaker_Player.cfg": "<cfg-Text>", ...}
               Pfade relativ zu Stalker2/Content/GameLite/GameData/.
               Absolute Sonderfaelle (DLC) koennen mit "//" beginnen und sind
               dann relativ zu Stalker2/Content/ zu verstehen.
    root_files: Dateien DIREKT unter dem Pak-Mount (z.B. das eingebettete
               S2Tweaker-Manifest). Bewusst NICHT unter GameData: den Ordner
               durchsucht der Config-Scanner des Spiels, und Dateien, die
               das Spiel nie anfragt, sind an der Wurzel garantiert
               wirkungslos.
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
        for rel, content in (root_files or {}).items():
            (staging / rel).write_text(content, encoding="utf-8")

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


def list_pak(pak: Path, repak_exe: Path | None = None) -> list[str]:
    """Dateiliste einer Pak (fuer den Mod-Scan). Liest nur den Index —
    braucht kein Oodle und ist auch bei 2-GB-Paks schnell."""
    repak = repak_exe or find_repak()
    if repak is None:
        raise FileNotFoundError("repak.exe nicht gefunden")
    result = subprocess.run(
        [str(repak), "list", str(pak)],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"repak list fehlgeschlagen: {result.stderr.strip()}")
    return [line.strip().strip('"')
            for line in result.stdout.splitlines() if line.strip()]


def unpack_many(pak: Path, out_dir: Path, includes: list[str],
                repak_exe: Path | None = None, progress=None) -> None:
    """Mehrere Eintraege in EINEM Rutsch entpacken (fuer den Mod-Scan).

    repak akzeptiert -i mehrfach; gebuendelt ist das um Groessenordnungen
    schneller als ein Prozess pro Datei. Gegen das Windows-Limit fuer
    Kommandozeilen (~32k Zeichen) wird in Bloecke aufgeteilt."""
    repak = repak_exe or find_repak()
    if repak is None:
        raise FileNotFoundError("repak.exe nicht gefunden")
    # Oodle wird NICHT vorab besorgt: Mod-Paks sind fast immer unkomprimiert
    # oder Zlib (repak kann beides ohne die DLL). Erst wenn repak wirklich
    # ueber Oodle stolpert, wird die DLL einmal beschafft und der Block
    # wiederholt — sonst wuerde ein Offline-Rechner ohne gecachte DLL jede
    # harmlose Mod als unlesbar melden.
    chunk: list[str] = []
    length = 0
    chunks: list[list[str]] = []
    for inc in includes:
        if chunk and length + len(inc) > 24000:
            chunks.append(chunk)
            chunk, length = [], 0
        chunk.append(inc)
        length += len(inc) + 5
    if chunk:
        chunks.append(chunk)

    def run(part: list[str]):
        cmd = [str(repak), "unpack", str(pak), "-o", str(out_dir), "-q", "-f"]
        for inc in part:
            cmd += ["-i", inc]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    oodle_ready = False
    for part in chunks:
        result = run(part)
        if result.returncode != 0 and "oodle" in result.stderr.lower() \
                and not oodle_ready:
            ensure_oodle(repak, pak=Path(pak), progress=progress)
            oodle_ready = True
            result = run(part)
        if result.returncode != 0:
            err = result.stderr.strip()
            if "oodle" in err.lower():
                raise _oodle_error(err)
            raise RuntimeError(f"repak unpack fehlgeschlagen: {err}")


def unpack(pak: Path, out_dir: Path, include: str | None = None,
           repak_exe: Path | None = None, progress=None) -> None:
    """Pak entpacken (fuer die Vanilla-GameData-Extraktion).

    Braucht Oodle — die DLL wird vorher besorgt, damit repak sie nicht
    selbst herunterladen muss (siehe Modul-Kopf)."""
    repak = repak_exe or find_repak()
    if repak is None:
        raise FileNotFoundError("repak.exe nicht gefunden")
    ensure_oodle(repak, pak=Path(pak), progress=progress)
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
        err = result.stderr.strip()
        if "oodle" in err.lower():
            raise _oodle_error(err)
        raise RuntimeError(f"repak unpack fehlgeschlagen: {err}")
