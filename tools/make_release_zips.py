"""Release-ZIPs bauen: Spieler-ZIP (EXE + README) und Source-ZIP.

    python tools/make_release_zips.py 1.11.0
    python tools/make_release_zips.py 1.11.0 --exe C:\\pfad\\zur\\S2Tweaker.exe

Das Source-ZIP entsteht aus `git ls-files`, also exakt der versionierten
Menge — damit koennen vanilla/, cache/, dist/, settings.json und die
proprietaere Oodle-DLL gar nicht erst hineinrutschen (.gitignore schuetzt).
Release-ZIPs und Screenshots werden zusaetzlich ausgefiltert.

--exe: Ausweich-EXE angeben, wenn dist\\ durch eine laufende Instanz
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
    exe = REPO / "dist" / "S2Tweaker.exe"
    if "--exe" in sys.argv:
        exe = Path(sys.argv[sys.argv.index("--exe") + 1])
    if not exe.is_file():
        raise SystemExit(f"EXE fehlt: {exe} — erst build.bat laufen lassen "
                         "(oder --exe angeben).")

    tracked = subprocess.run(["git", "ls-files"], cwd=REPO,
                             capture_output=True, text=True,
                             check=True).stdout.splitlines()
    source_files = [f for f in tracked
                    if not f.endswith(".zip")
                    and not f.startswith("release/screenshots")]

    out = REPO / "release"
    player = out / f"S2Tweaker_v{version}.zip"
    with zipfile.ZipFile(player, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, "S2Tweaker.exe")
        z.write(out / "README.txt", "README.txt")
        z.write(out / "update.bat", "update.bat")
    print(f"{player.name}: {player.stat().st_size:,} bytes")

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
