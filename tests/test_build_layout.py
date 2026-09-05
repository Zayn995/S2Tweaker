"""Der Programmordner OHNE PyInstaller (seit 1.21.0): baut nach
tests/_tmp/dist und prueft die Zusagen, die README, FAQ und Nexus-Texte
machen.

Hintergrund (05.09.2026): 1.20.0 stand bei VirusTotal auf 2/70, und die
beiden Treffer galten dem Anhang, den PyInstaller an seinen Starter
haengt - der nackte Starter selbst war bei allen Scannern sauber. Seitdem
ist S2Tweaker.exe die unveraenderte, von der Python Software Foundation
signierte pythonw.exe; alles andere liegt lesbar in _internal. Diese
Suite haelt fest, was das Paket enthalten muss und was nicht.
tools/build_exe.py macht dieselben Gegenproben selbst und dazu den
Selbsttest (Fenster aufbauen); hier wird der Bau als Ganzes von aussen
angestossen, so wie CI und build.bat es tun.

Dauer: rund eine halbe Minute (die Standardbibliothek wird kompiliert).
Braucht keine Spieldaten, aber eine python.org-Installation als
Interpreter (pythonw.exe, DLLs\\, tcl\\ neben python.exe).
"""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "tests" / "_tmp" / "dist"
if DIST.exists():
    shutil.rmtree(DIST)

r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_exe.py"),
                    "--distpath", str(DIST)], cwd=ROOT)
assert r.returncode == 0, "tools/build_exe.py ist fehlgeschlagen"
app = DIST / "S2Tweaker"
internal = app / "_internal"
ver = f"{sys.version_info.major}{sys.version_info.minor}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --- 1) Der Starter ist Byte fuer Byte pythonw.exe ----------------------
assert sha(app / "S2Tweaker.exe") == sha(Path(sys.base_prefix) / "pythonw.exe")
print("S2Tweaker.exe == pythonw.exe der Python-Installation  OK")

# --- 2) Genau zwei ausfuehrbare Dateien --------------------------------
exes = sorted(p.relative_to(app).as_posix() for p in app.rglob("*.exe"))
assert exes == ["S2Tweaker.exe", "_internal/repak.exe"], exes

# --- 3) Kein Netz, kein TLS, kein OpenSSL, kein PyInstaller -------------
names = [p.name.lower() for p in app.rglob("*")]
for bad in ("_ssl", "_socket", "_hashlib", "libssl", "libcrypto", "sqlite",
            "_multiprocessing", "pyimod", "base_library.zip"):
    hits = [n for n in names if n.startswith(bad)]
    assert not hits, hits
with zipfile.ZipFile(internal / f"python{ver}.zip") as z:
    zipped = set(z.namelist())
for need in ("site.pyc", "encodings/__init__.pyc", "tkinter/__init__.pyc",
             "json/__init__.pyc", "subprocess.pyc", "zipfile/__init__.pyc"):
    assert need in zipped, need
for bad in ("ssl.pyc", "socket.pyc", "asyncio/__init__.pyc",
            "sqlite3/__init__.pyc", "test/__init__.pyc",
            "idlelib/__init__.pyc", "ensurepip/__init__.pyc"):
    assert bad not in zipped, bad
print("Layout: zwei EXEs, keine Netz-/TLS-Module, Stdlib-Zip  OK")

# --- 4) Suchpfad und Starter --------------------------------------------
pth = (app / f"python{ver}._pth").read_text(encoding="ascii").splitlines()
assert pth == [f"_internal\\python{ver}.zip", "_internal", "import site"], pth
assert (internal / "sitecustomize.py").read_bytes() == \
    (ROOT / "tools" / "launcher.py").read_bytes(), \
    "sitecustomize.py weicht von tools/launcher.py ab"
print("._pth und sitecustomize.py  OK")

# --- 5) Quelltext lesbar + vorkompiliert, Beigaben, Lizenzen ------------
for rel in ("s2tweaker/gui.py", "s2tweaker/__pycache__",
            "customtkinter/__init__.py", "darkdetect/__init__.py",
            "packaging/version.py", "assets/icon.ico",
            "assets/help/oodle_browser.png", "repak.exe",
            "licenses/PYTHON-LICENSE.txt",
            "licenses/THIRD_PARTY_LICENSES.txt", "tcl"):
    assert (internal / rel).exists(), rel
pycs = sorted((internal / "s2tweaker" / "__pycache__").glob(f"*.cpython-{ver}.pyc"))
assert len(pycs) >= 10, pycs
# Vorkompiliert mit unchecked-hash (Flag-Bits 0b01): wird ohne Blick auf
# den Zeitstempel der .py benutzt, das Programm schreibt beim Start nichts.
flags = int.from_bytes(pycs[0].read_bytes()[4:8], "little")
assert flags & 0b11 == 0b01, f"pyc-Flags {flags:#x} (erwartet unchecked-hash)"
print("Quelltext + __pycache__ (unchecked-hash), Beigaben, Lizenzen  OK")

# --- 6) Keine Nutzerdaten und keine Reste des Selbsttests im Paket ------
for junk in ("settings.json", "cache", "output", "presets",
             "S2Tweaker_error.log"):
    assert not (app / junk).exists(), junk

# --- 7) Groesse: kleiner Starter, nichts eingebettet --------------------
exe_size = (app / "S2Tweaker.exe").stat().st_size
assert exe_size < 200_000, exe_size
total = sum(p.stat().st_size for p in app.rglob("*") if p.is_file())
print(f"Groesse: Starter {exe_size:,} B, Ordner gesamt {total:,} B")

print("\nBAU-LAYOUT-TEST OK")
