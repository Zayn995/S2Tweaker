"""Build a portable folder under tests/_tmp and verify its distribution contract.

Check the unchanged signed pythonw.exe, runtime layout, forbidden modules
and absence of user data. Requires a python.org installation, not game data.
The build performs its own headless self-test."""
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
assert r.returncode == 0, "tools/build_exe.py failed"
app = DIST / "S2Tweaker"
internal = app / "_internal"
ver = f"{sys.version_info.major}{sys.version_info.minor}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# Launcher must be byte-identical to pythonw.exe.
assert sha(app / "S2Tweaker.exe") == sha(Path(sys.base_prefix) / "pythonw.exe")
print("S2Tweaker.exe matches the Python installation's pythonw.exe  OK")

# Exactly one executable; no repak binary.
exes = sorted(p.relative_to(app).as_posix() for p in app.rglob("*.exe"))
assert exes == ["S2Tweaker.exe"], exes

# No network/TLS/OpenSSL/PyInstaller components.
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
print("Layout: one EXE, no network/TLS modules, standard library ZIP  OK")

# Module search path and startup module.
pth = (app / f"python{ver}._pth").read_text(encoding="ascii").splitlines()
assert pth == [f"_internal\\python{ver}.zip", "_internal", "import site"], pth
assert (internal / "sitecustomize.py").read_bytes() == \
    (ROOT / "tools" / "launcher.py").read_bytes(), \
    "sitecustomize.py differs from tools/launcher.py"
print("._pth and sitecustomize.py  OK")

# --- 5) Readable and precompiled source, resources, licenses ---
for rel in ("s2tweaker/gui.py", "s2tweaker/__pycache__",
            "customtkinter/__init__.py", "darkdetect/__init__.py",
            "packaging/version.py", "assets/icon.ico",
            "assets/help/oodle_browser.png", "s2tweaker/pakfile.py",
            "licenses/PYTHON-LICENSE.txt",
            "licenses/THIRD_PARTY_LICENSES.txt", "tcl"):
    assert (internal / rel).exists(), rel
pycs = sorted((internal / "s2tweaker" / "__pycache__").glob(f"*.cpython-{ver}.pyc"))
assert len(pycs) >= 10, pycs
# Use unchecked-hash bytecode so startup does not depend on source timestamps.
flags = int.from_bytes(pycs[0].read_bytes()[4:8], "little")
assert flags & 0b11 == 0b01, f"pyc-Flags {flags:#x} (expected unchecked-hash)"
print("Source and __pycache__ (unchecked-hash), supporting files, licenses  OK")

# No user data or self-test leftovers in the distribution.
for junk in ("settings.json", "cache", "output", "presets",
             "S2Tweaker_error.log"):
    assert not (app / junk).exists(), junk

# --- 7) Size: small launcher, no embedded payload ---
exe_size = (app / "S2Tweaker.exe").stat().st_size
assert exe_size < 200_000, exe_size
total = sum(p.stat().st_size for p in app.rglob("*") if p.is_file())
print(f"Size: launcher {exe_size:,} B, total directory size {total:,} B")

print("\nBUILD LAYOUT TEST PASSED")
