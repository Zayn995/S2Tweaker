"""Release-ZIPs bauen: Spieler-ZIP (Programmordner + README) und Source-ZIP.

    python tools/make_release_zips.py 1.11.0
    python tools/make_release_zips.py 1.11.0 --dist C:\\pfad\\zu\\S2Tweaker

Das Spieler-ZIP enthaelt den ganzen Programmordner FLACH in der
ZIP-Wurzel (Aufbau: tools/build_exe.py):

    S2Tweaker.exe          (= signierte pythonw.exe, unveraendert)
    python3XX.dll, vcruntime140*.dll, python3XX._pth
    _internal\\...
    README.txt

Fuer den Spieler: entpacken, S2Tweaker.exe doppelklicken. Zum
Aktualisieren das neue ZIP ueber den alten Ordner entpacken - Einstellungen,
Presets, Cache und Output sind nicht im ZIP und bleiben unberuehrt.

Das Source-ZIP entsteht aus `git ls-files`, also exakt der versionierten
Menge — damit koennen vanilla/, cache/, dist/, settings.json und die
proprietaere Oodle-DLL gar nicht erst hineinrutschen (.gitignore schuetzt).
Release-ZIPs und Screenshots werden zusaetzlich ausgefiltert.

--dist: Ausweich-Ordner angeben, wenn dist\\ durch eine laufende Instanz
gesperrt war und mit --distpath woanders gebaut wurde.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Aufruf: python tools/make_release_zips.py <version> "
                         "[--exe <pfad>]")
    version = sys.argv[1]
    app = REPO / "dist" / "S2Tweaker"
    if "--dist" in sys.argv:
        app = Path(sys.argv[sys.argv.index("--dist") + 1])
    if not (app / "S2Tweaker.exe").is_file():
        raise SystemExit(f"Programmordner fehlt: {app} — erst build.bat "
                         "laufen lassen (oder --dist angeben).")

    tracked = subprocess.run(["git", "ls-files"], cwd=REPO,
                             capture_output=True, text=True,
                             check=True).stdout.splitlines()
    source_files = [f for f in tracked
                    if not f.endswith(".zip")
                    and not f.startswith("release/screenshots")]

    out = REPO / "release"
    player = out / f"S2Tweaker_v{version}.zip"
    with zipfile.ZipFile(player, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(app.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(app).as_posix())
        z.write(out / "README.txt", "README.txt")
    print(f"{player.name}: {player.stat().st_size:,} bytes")

    # Gegenprobe Spieler-ZIP: der Starter liegt in der Wurzel und die
    # Laufzeit ist wirklich dabei (ein leeres _internal gaebe eine EXE,
    # die beim Doppelklick sofort stirbt).
    with zipfile.ZipFile(player) as z:
        names = z.namelist()
    assert "S2Tweaker.exe" in names, names[:10]
    internal = [n for n in names if n.startswith("_internal/")]
    assert len(internal) > 100, f"nur {len(internal)} Dateien in _internal/"
    assert "README.txt" in names, names[:10]
    # Einen Updater gibt es seit 05.09.2026 nirgends mehr (Nexus-Pruefung);
    # ein Skript, das ein Release laedt und Programmdateien ersetzt, darf
    # auch nicht still ins Paket zurueckkehren.
    assert "update.bat" not in names, "update.bat gehoert nicht ins Spieler-ZIP"
    # Seit 1.21.0: Suchpfad-Datei und Starter-Modul muessen dabei sein,
    # Netz-/TLS-Module und Nutzerdaten (Reste einer Startprobe) nicht.
    assert any(n.startswith("python3") and n.endswith("._pth") for n in names), \
        "python3XX._pth fehlt - der Starter faende seinen Code nicht"
    assert "_internal/sitecustomize.py" in names, "Starter-Modul fehlt"
    verboten = [n for n in names if n.rsplit("/", 1)[-1].lower().startswith(
        ("_ssl", "_socket", "_hashlib", "libssl", "libcrypto", "sqlite3"))]
    assert not verboten, verboten
    reste = [n for n in names
             if n.split("/")[0] in ("settings.json", "cache", "output", "presets")]
    assert not reste, reste
    print(f"Gegenprobe: S2Tweaker.exe + ._pth + {len(internal)} Dateien in "
          "_internal/ + README, ohne Updater/Netzmodule/Nutzerdaten OK")

    src = out / f"S2Tweaker_v{version}_source.zip"
    with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in source_files:
            z.write(REPO / rel, rel)
    print(f"{src.name}: {src.stat().st_size:,} bytes, "
          f"{len(source_files)} Dateien")

    with zipfile.ZipFile(src) as z:
        names = z.namelist()
    forbidden = [n for n in names
                 if n.startswith(("vanilla/", "cache/", "dist/", "build/"))
                 or "oo2core" in n or n.endswith("settings.json")]
    assert not forbidden, forbidden
    print("Gegenprobe: keine vanilla/cache/dist/oo2core/settings-Dateien OK")


if __name__ == "__main__":
    main()
