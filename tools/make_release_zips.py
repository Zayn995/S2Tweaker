"""Release-ZIPs bauen: Spieler-ZIP (Programmordner + README) und Source-ZIP.

    python tools/make_release_zips.py 1.11.0
    python tools/make_release_zips.py 1.11.0 --dist C:\\pfad\\zu\\S2Tweaker

Seit 04.09.2026 baut build.bat mit --onedir (Begruendung dort: die
--onefile-EXE war ein selbstentpackendes Archiv und flog bei Windows
Defender und beim Nexus-Virenscan auf). Das Spieler-ZIP enthaelt darum
den ganzen Programmordner FLACH in der ZIP-Wurzel:

    S2Tweaker.exe
    _internal\\...
    README.txt
    update.bat

Fuer den Spieler aendert sich damit nichts an der Bedienung — entpacken,
S2Tweaker.exe doppelklicken —, es liegt nur zusaetzlich ein _internal-
Ordner daneben.

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
        z.write(out / "update.bat", "update.bat")
    print(f"{player.name}: {player.stat().st_size:,} bytes")

    # Gegenprobe Spieler-ZIP: der Starter liegt in der Wurzel und die
    # Laufzeit ist wirklich dabei (ein leeres _internal gaebe eine EXE,
    # die beim Doppelklick sofort stirbt).
    with zipfile.ZipFile(player) as z:
        names = z.namelist()
    assert "S2Tweaker.exe" in names, names[:10]
    internal = [n for n in names if n.startswith("_internal/")]
    assert len(internal) > 100, f"nur {len(internal)} Dateien in _internal/"
    assert "README.txt" in names and "update.bat" in names, names[:10]
    print(f"Gegenprobe: S2Tweaker.exe + {len(internal)} Dateien in "
          "_internal/ + README + update.bat OK")

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
