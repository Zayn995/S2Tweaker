"""Baut den Programmordner dist/S2Tweaker/ (exe + _internal).

    python tools/build_exe.py
    python tools/build_exe.py --distpath <ordner> --workpath <ordner>

EINZIGE Quelle der Bau-Anweisung: build.bat ruft dieses Skript, und der
GitHub-Actions-Workflow ruft dasselbe Skript. Frueher stand die
PyInstaller-Zeile nur in build.bat — mit einer zweiten Kopie im Workflow
waeren beide irgendwann auseinandergelaufen, und genau darauf beruht die
Zusage an SignPath/Nexus, dass die veroeffentlichte EXE aus diesem
Quellcode stammt.

Warum --onedir statt --onefile und warum --version-file: siehe build.bat
bzw. docs/ROADMAP.md („Virenscanner-Fehlalarm"). Kurz: die selbst-
entpackende Einzeldatei sah fuer Virenscanner wie ein Dropper aus, und
die EXE hatte gar keine Versions-Angaben.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.make_version_file import write as write_version_file  # noqa: E402


def build(distpath: str | None = None, workpath: str | None = None) -> int:
    version_file = write_version_file(REPO / "build" / "version_info.txt")
    print(f"Versions-Ressource: {version_file}", flush=True)

    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm",
        "--onedir",                      # NICHT --onefile, siehe Kopf
        "--windowed", "--name", "S2Tweaker",
        "--icon", str(REPO / "assets" / "icon.ico"),
        "--add-binary", f"{REPO / 'assets' / 'icon.ico'};.",
        "--add-binary", f"{REPO / 'tools' / 'repak.exe'};.",
        # Bilder des Oodle-Assistenten. Als PNG, weil Tk die von Haus aus
        # anzeigt — Pillow bleibt damit aus dem Build draussen (s. unten).
        "--add-data", f"{REPO / 'assets' / 'help'};help",
        "--collect-all", "customtkinter",
        "--version-file", str(version_file),
        # Pillow ist eine optionale customtkinter-Abhaengigkeit, die die App
        # nie benutzt (kein CTkImage; nur tools/make_screenshots.py braucht
        # sie). Ohne diesen Ausschluss waere die EXE auf Rechnern MIT Pillow
        # ~3 MB groesser als auf Rechnern ohne — der Build waere nicht mehr
        # reproduzierbar.
        "--exclude-module", "PIL",
        str(REPO / "main.py"),
    ]
    if distpath:
        cmd += ["--distpath", distpath]
    if workpath:
        cmd += ["--workpath", workpath]
    print("PyInstaller:", " ".join(cmd[2:]), flush=True)
    return subprocess.run(cmd, cwd=REPO).returncode


def main() -> None:
    args = sys.argv[1:]

    def opt(name: str) -> str | None:
        return args[args.index(name) + 1] if name in args else None

    code = build(opt("--distpath"), opt("--workpath"))
    if code != 0:
        raise SystemExit(code)
    out = Path(opt("--distpath") or (REPO / "dist")) / "S2Tweaker"
    exe = out / "S2Tweaker.exe"
    if not exe.is_file():
        raise SystemExit(f"Build lief durch, aber {exe} fehlt.")
    internal = list((out / "_internal").rglob("*")) if (out / "_internal").is_dir() else []
    print(f"\nFertig: {exe} ({exe.stat().st_size:,} Bytes), "
          f"_internal mit {len(internal)} Eintraegen")


if __name__ == "__main__":
    main()
