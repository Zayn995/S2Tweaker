"""Pak-Erzeugung und -Entpacken fuer S.T.A.L.K.E.R. 2 - in reinem Python.

Funktionierende Mod-Paks im Spiel sind: Version V8B, Mount-Point ../../../,
unkomprimiert, unverschluesselt. Genau das schreibt s2tweaker/pakfile.py,
und genau das schrieb bis 1.22.0 das mitgelieferte repak.exe.

Kein repak.exe mehr (05.09.2026)
--------------------------------
repak.exe (Rust, von uns aus dem Quelltext gebaut) war die einzige
unsignierte ausfuehrbare Datei im Paket - und wurde am 05.09.2026 von
Microsofts Machine-Learning-Erkennung als Trojaner markiert, zweimal, fuer
Binaerdateien, die sich nur im Zeitstempel unterschieden. Die Aufgabe
uebernimmt seitdem pakfile.py mit der Standardbibliothek; die Gegenprobe
gegen repak an den echten Spieldateien steht in tests/test_pakfile.py.

Oodle: wird gebraucht, aber NIE mitgeliefert und NIE heruntergeladen
--------------------------------------------------------------------
pakchunk0 des Spiels ist Oodle-komprimiert, deshalb braucht das ENTPACKEN
die proprietaere oo2core_9_win64.dll (zum PACKEN nicht - unsere Paks sind
unkomprimiert, verifiziert). Geladen wird sie per ctypes, so wie repak sie
per LoadLibrary lud.

Beschafft wird sie seit 04.09.2026 NICHT mehr von uns. Zwei Gruende:

  1. Ein Programm, das zur Laufzeit eine Bibliothek aus dem Netz holt und
     als nativen Code laedt, zeigt exakt das Verhalten eines Droppers -
     einer der Gruende, warum Virenscanner solche Werkzeuge markieren.
     Die Freigabe auf Nexus scheiterte an genau solchen Fehlalarmen.
  2. Der Download war ohnehin die fehleranfaelligste Stelle: Bugreport
     foxce (31.08.2026), Abbruch mit InvalidCertificate(UnknownIssuer)
     hinter einer AV-/Proxy-HTTPS-Inspektion.

Stattdessen: lokal suchen (SHA-256 immer pruefen, die Datei wird gleich
darauf als nativer Code geladen), und wenn sie fehlt, den Nutzer per
Klartext-Dialog bitten, sie einmal selbst danebenzulegen - mit Link und
Zielordner (OODLE_HELP).
"""

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

# Die Oodle-Version, mit der die Spielpaks nachweislich gelesen werden
# (dieselbe, die repak 0.2.3 verlangte) - nur mit diesem Hash wird die
# DLL akzeptiert und geladen.
OODLE_DLL = "oo2core_9_win64.dll"
OODLE_SHA256 = "6f5d41a7892ea6b2db420f2458dad2f84a63901c9a93ce9497337b16c195f457"
OODLE_URL = (
    "https://github.com/WorkingRobot/OodleUE/raw/refs/heads/main/Engine/Source"
    "/Programs/Shared/EpicGames.Oodle/Sdk/2.9.10/win/redist/" + OODLE_DLL
)

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
again. It has to be exactly this build (SHA-256 starting with {hash8});
other Oodle 2.9.x builds are rejected on purpose.

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


def _oodle_error(reason: str) -> "OodleError":
    # Dem Nutzer wird IMMER der Ordner mit S2Tweaker.exe genannt - dort
    # sucht ensure_oodle zuerst, und dorthin zeigen Anleitung und Bild im
    # Assistenten.
    where = str(app_dir())
    return OodleError(OODLE_HELP.format(
        dll=OODLE_DLL, url=OODLE_URL, hash8=OODLE_SHA256[:8],
        reason=reason, target=where))


def oodle_cache_dir() -> Path:
    """Dauerhafter Ablageort der DLL - portabel neben der EXE.

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
    try:
        if _hash_ok(oodle_cache_dir() / OODLE_DLL):
            return True
    except OodleError:
        pass
    return any(_hash_ok(c) for c in _local_oodle_candidates(pak))


def ensure_oodle(pak: Path | None = None, progress=None) -> Path:
    """Pfad zur (echten) Oodle-DLL - OHNE Download.

    Gesucht wird ausschliesslich LOKAL: erst der Cache neben der EXE, dann
    die ueblichen Stellen (Programmordner, Spielordner ...). Ein Fund wird
    in den Cache kopiert, damit er beim naechsten Mal sofort da ist. Fehlt
    die Datei ueberall, gibt es einen Klartext-Fehler mit Anleitung;
    heruntergeladen wird nichts (Begruendung im Modul-Kopf). `progress`
    bleibt nur der Signatur wegen erhalten.

    Es wird immer der SHA-256 geprueft, nie nur die Existenz - die Datei
    wird gleich darauf als nativer Code geladen."""
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
                return candidate          # nicht kopierbar, aber benutzbar
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
    """OodleLZ_Decompress als Python-Funktion - laedt die DLL einmal."""
    dll = ensure_oodle(pak, progress)
    fn = _decompressors.get(dll)
    if fn is None:
        fn = pakfile.load_oodle(dll)
        _decompressors[dll] = fn
    return fn


def _open(pak: Path) -> pakfile.PakFile:
    """Pak oeffnen; Oodle wird erst geladen, wenn ein Eintrag es braucht -
    sonst wuerde ein Offline-Rechner ohne DLL jede harmlose (unkomprimierte
    oder Zlib-)Mod als unlesbar melden."""
    pak = Path(pak)

    def lazy(comp: bytes, raw_len: int) -> bytes:
        return oodle_decompressor(pak)(comp, raw_len)

    return pakfile.PakFile(pak, oodle=lazy)


def export_cfgs(cfg_files: dict[str, str], root: Path) -> list[Path]:
    """Die Patch-Dateien als lose .cfg unter root ablegen (Debug-Export).

    Gleiche Pfad-Regel wie pack_mod(): normale Eintraege landen direkt unter
    root (wie bisher, z.B. root/DifficultyPrototypes/..._patch_X.cfg), die
    "//"-Eintraege der Editions-Waffen unter root/GameLite/DLCGameData/...

    GitHub Issue #5 (KobaltRaven, 03.09.2026): der fruehere Export machte
    `root / rel` - und ein rel, das mit "//" beginnt, ist fuer pathlib ein
    ABSOLUTER UNC-Pfad (\\\\GameLite\\DLCGameData\\...), der die Basis
    verdraengt. mkdir versuchte dann, einen Netzwerkpfad anzulegen
    (WinError 53), sobald ein Editions-Patch dabei war - also bei jedem
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

    Der Umweg ueber einen Staging-Ordner bleibt absichtlich: die Dateien
    werden wie bisher mit write_text abgelegt (Windows-Zeilenenden), damit
    die Pak byteidentisch mit der bisherigen repak-Erzeugung bleibt.
    """
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
            (staging / rel).write_text(content, encoding="utf-8")
        pakfile.pack_dir(staging, out_pak)

    if not out_pak.is_file():
        raise RuntimeError(f"Pak wurde nicht erzeugt: {out_pak}")
    return out_pak


def list_pak(pak: Path) -> list[str]:
    """Dateiliste einer Pak (fuer den Mod-Scan), Pfade ohne ../../../ wie
    bei `repak list`. Liest nur den Index - braucht kein Oodle und ist auch
    bei 2-GB-Paks schnell."""
    with _open(Path(pak)) as pk:
        return [pk.stripped(name) for name in pk.files()]


def _extract(pak: Path, out_dir: Path, patterns: list[str] | None,
             progress=None) -> int:
    """Eintraege, die ein Muster treffen (alle ohne Muster), nach out_dir
    schreiben - Ablage wie `repak unpack`: out_dir/<Pfad ohne ../../../>."""
    pak, out_dir = Path(pak), Path(out_dir)
    regexes = [pakfile.glob_regex(p) for p in patterns] if patterns else None
    written = 0
    with _open(pak) as pk:
        selected = []
        for name in pk.files():
            stripped = pk.stripped(name)
            if regexes is None or pakfile.matches(regexes, stripped):
                selected.append((name, stripped))
        # Fehlt die DLL, soll der Klartext-Fehler kommen, BEVOR etwas
        # geschrieben wird - nicht mitten im Entpacken.
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
    """Mehrere Eintraege in einem Rutsch entpacken (fuer den Mod-Scan).
    `includes` sind Glob-Muster wie bei `repak unpack -i` ('[' als '[[]')."""
    _extract(pak, out_dir, list(includes), progress)


def unpack(pak: Path, out_dir: Path, include: str | None = None,
           progress=None) -> None:
    """Pak entpacken (fuer die Vanilla-GameData-Extraktion); `include` ist
    ein Glob-Muster auf den Pfad ohne ../../../ - ohne Muster alles.

    Braucht bei Oodle-komprimierten Eintraegen die DLL; fehlt sie, kommt
    der Klartext-Fehler mit Anleitung (siehe Modul-Kopf)."""
    _extract(pak, out_dir, [include] if include else None, progress)
