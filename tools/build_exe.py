"""Baut den Programmordner dist/S2Tweaker/ - seit 1.21.0 OHNE PyInstaller.

    python tools/build_exe.py
    python tools/build_exe.py --distpath <ordner>
    python tools/build_exe.py --no-selftest     (nur zusammenstellen)

EINZIGE Bau-Anweisung: build.bat und .github/workflows/build.yml rufen
beide dieses Skript. Zwei Kopien des Rezepts waeren irgendwann
auseinandergelaufen - und darauf beruht die Zusage, dass die
veroeffentlichte Datei aus genau diesem Quellcode stammt.

WARUM OHNE PYINSTALLER (05.09.2026, gemessen; Details in HANDOVER/ROADMAP)
--------------------------------------------------------------------------
1.20.0 stand bei VirusTotal auf 2/70 (Microsoft Wacatac.B!ml, Zillya
Dropper.Agent). Die EXE war bis auf Icon/Versionsinfo und ein 26-KB-Overlay
byte-identisch mit PyInstallers offiziellem Starter runw.exe - und DER
steht bei VirusTotal auf 0/53. Die Treffer galten also dem Anhang, den
PyInstaller anfuegt, also der PyInstaller-Kennung selbst. Innerhalb von
PyInstaller war nichts mehr zu gewinnen: --onedir, noarchive und die
Versions-Ressource hatten nur einen von drei Motoren ueberzeugt.

WAS STATTDESSEN ENTSTEHT
------------------------
    S2Tweaker.exe        pythonw.exe der python.org-Installation, Byte fuer
                         Byte, signiert von der Python Software Foundation
    python3XX.dll        die Laufzeit, ebenfalls PSF-signiert
    vcruntime140*.dll    Microsoft-signiert
    python3XX._pth       Modul-Suchpfad: nur _internal. Umgebungsvariablen
                         und ein installiertes Python werden ignoriert;
                         `import site` ruft den Starter
    _internal\\
        sitecustomize.py = tools/launcher.py, startet die GUI
        python3XX.zip    Standardbibliothek als .pyc (wie im offiziellen
                         "embeddable package"), OHNE socket/ssl/asyncio/
                         sqlite3/test
        *.pyd, *.dll     nur die Erweiterungen, die das Programm braucht
                         (EXTENSIONS), samt ihren DLLs - kein _ssl, kein
                         libcrypto, kein _socket
        tcl\\             Tcl/Tk-Skriptbibliotheken
        s2tweaker\\, customtkinter\\, darkdetect\\, packaging\\
                         lesbarer Quelltext plus vorkompiliertes __pycache__
        assets\\, repak.exe, licenses\\

Jede ausfuehrbare Datei im Paket ist damit signiert - ausser repak.exe,
das die CI aus dem Quelltext baut (tools/build_repak.py). verify() prueft
das am Ende nach (Signaturen per Get-AuthenticodeSignature, Hash-Gleichheit
S2Tweaker.exe == pythonw.exe, verbotene Dateien, keine Heimpfade) und
laesst eine Kopie des Ordners den Selbsttest aus tools/launcher.py fahren.

Der Interpreter, der dieses Skript ausfuehrt, liefert die Laufzeit: eine
python.org-Installation (pythonw.exe, DLLs\\, Lib\\, tcl\\ nebeneinander).
Lokal ist das z. B. 3.14, in der CI 3.12 - das Release kommt aus der CI.
"""
from __future__ import annotations

import argparse
import compileall
import hashlib
import importlib.metadata
import importlib.util
import os
import py_compile
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from s2tweaker import __version__  # noqa: E402

APP = "S2Tweaker"
PREFIX = Path(sys.base_prefix)
PYTAG = f"{sys.version_info.major}{sys.version_info.minor}"   # z. B. "312"
PYDLL = f"python{PYTAG}.dll"
PTH = f"python{PYTAG}._pth"
STDLIB_ZIP = f"python{PYTAG}.zip"
UNCHECKED = py_compile.PycInvalidationMode.UNCHECKED_HASH
ZIP_TIME = (2026, 1, 1, 0, 0, 0)   # feste Zeitstempel: gleicher Bau = gleiche Bytes

# Erweiterungsmodule aus DLLs\\, die das Programm braucht. Das ist die Menge,
# die PyInstallers statische Analyse fuer 1.20.0 ergab, MINUS:
#   _ssl + libssl/libcrypto  (TLS - das Programm hat keinen Netzcode)
#   _hashlib                 (OpenSSL-Hashes; hashlib nimmt die eingebauten)
#   _socket                  (Netz; kein Modul im Programm importiert socket)
#   _multiprocessing         (main.py brauchte es nur fuer PyInstaller)
# Der Selbsttest in tools/launcher.py prueft, dass alles Noetige da ist und
# socket/ssl wirklich fehlen.
EXTENSIONS = ("_bz2", "_ctypes", "_decimal", "_lzma", "_queue", "_tkinter",
              "_wmi", "pyexpat", "select", "unicodedata")
SITE_PACKAGES = ("customtkinter", "darkdetect", "packaging")
STDLIB_SKIP_DIRS = {"site-packages", "test", "tests", "idlelib", "lib2to3",
                    "turtledemo", "ensurepip", "venv", "pydoc_data",
                    "sqlite3", "asyncio", "__pycache__"}
STDLIB_SKIP_FILES = {"socket.py", "ssl.py"}          # nur auf oberster Ebene
TCL_SKIP_DIRS = {"demos"}
# Dateinamen-Praefixe, die im fertigen Ordner nirgends auftauchen duerfen.
FORBIDDEN = ("_ssl", "_hashlib", "_socket", "_multiprocessing", "_sqlite3",
             "sqlite3", "libssl", "libcrypto", "_asyncio", "_overlapped",
             "pyimod", "base_library")


def log(msg: str) -> None:
    print(msg, flush=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- PE-Importtabellen lesen (ohne Fremdpaket) ---------------------------
def _pe_imports(path: Path) -> list[str]:
    """Namen der DLLs, die eine EXE/DLL/PYD laut Import- und Delay-Import-
    Tabelle laedt (kleingeschrieben)."""
    data = path.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError(f"{path}: keine PE-Datei")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic != 0x20B:
        raise ValueError(f"{path}: kein 64-Bit-PE")
    ndirs = struct.unpack_from("<I", data, opt + 108)[0]
    dirs = opt + 112
    sections = []
    sec = opt + opt_size
    for i in range(nsec):
        vsize, vaddr, rsize, roff = struct.unpack_from("<IIII", data, sec + i * 40 + 8)
        sections.append((vaddr, max(vsize, rsize), roff))

    def rva2off(rva: int) -> int:
        for vaddr, size, roff in sections:
            if vaddr <= rva < vaddr + size:
                return roff + (rva - vaddr)
        raise ValueError(f"{path}: RVA {rva:#x} in keiner Sektion")

    names: list[str] = []
    for index, entry_size, name_at in ((1, 20, 12), (13, 32, 4)):
        if index >= ndirs:
            continue
        rva, _size = struct.unpack_from("<II", data, dirs + index * 8)
        if not rva:
            continue
        off = rva2off(rva)
        while True:
            entry = data[off:off + entry_size]
            if len(entry) < entry_size or not any(entry):
                break
            name_rva = struct.unpack_from("<I", entry, name_at)[0]
            if not name_rva:
                break
            noff = rva2off(name_rva)
            names.append(data[noff:data.index(b"\0", noff)].decode("ascii").lower())
            off += entry_size
    return names


def _python_dlls() -> dict[str, Path]:
    """Alle DLLs der Python-Installation; alles andere gilt als Windows."""
    pool: dict[str, Path] = {}
    for folder in (PREFIX, PREFIX / "DLLs"):
        for f in folder.glob("*.dll"):
            pool.setdefault(f.name.lower(), f)
    return pool


def _resolve_deps(binaries: list[Path]) -> list[Path]:
    """DLLs der Python-Installation, die diese Binaerdateien (transitiv)
    brauchen. python3XX.dll selbst liegt immer in der Wurzel."""
    pool = _python_dlls()
    todo = list(binaries)
    seen: set[Path] = set()
    out: list[Path] = []
    while todo:
        item = todo.pop()
        if item in seen:
            continue
        seen.add(item)
        for name in _pe_imports(item):
            if name == PYDLL.lower():
                continue
            dep = pool.get(name)
            if dep is not None and dep not in out:
                out.append(dep)
                todo.append(dep)
    return sorted(out)


# --- Kopieren und kompilieren ------------------------------------------
def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _copy_tree(src: Path, dst: Path, *, skip_dirs: set[str] = frozenset(),
               only_suffixes: tuple[str, ...] | None = None,
               skip_suffixes: tuple[str, ...] = ()) -> int:
    count = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
        for name in sorted(files):
            if only_suffixes and not name.endswith(only_suffixes):
                continue
            if skip_suffixes and name.endswith(skip_suffixes):
                continue
            path = Path(root) / name
            _copy(path, dst / path.relative_to(src))
            count += 1
    return count


def _build_stdlib_zip(target: Path) -> int:
    """Standardbibliothek als .pyc-Zip, so wie python.org sie im embeddable
    package ausliefert. unchecked-hash: kein Zeitstempel im pyc, also
    reproduzierbar, und nie ein Blick auf eine .py, die es nicht gibt."""
    lib = PREFIX / "Lib"
    count = 0
    with tempfile.TemporaryDirectory(prefix="s2t_pyc_") as tmp, \
            zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        cfile = Path(tmp) / "module.pyc"
        for root, dirs, files in os.walk(lib):
            dirs[:] = sorted(d for d in dirs if d not in STDLIB_SKIP_DIRS)
            rel_root = Path(root).relative_to(lib)
            top = rel_root == Path(".")
            for name in sorted(files):
                if not name.endswith(".py") or (top and name in STDLIB_SKIP_FILES):
                    continue
                rel = (rel_root / name).as_posix()
                py_compile.compile(str(Path(root) / name), cfile=str(cfile),
                                   dfile=rel, doraise=True, optimize=0,
                                   invalidation_mode=UNCHECKED)
                info = zipfile.ZipInfo(rel[:-3] + ".pyc", date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, cfile.read_bytes())
                count += 1
    return count


def _compile_tree(path: Path, ddir: str) -> None:
    """__pycache__ vorkompilieren (unchecked-hash). ddir: der Name, der im
    pyc landet - relativ, damit kein Pfad des Bau-Rechners mitreist."""
    ok = compileall.compile_dir(str(path), ddir=ddir, quiet=1, force=True,
                                optimize=0, invalidation_mode=UNCHECKED)
    if not ok:
        raise SystemExit(f"Kompilieren fehlgeschlagen in {path}")


def _package_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or not spec.submodule_search_locations:
        raise SystemExit(f"Paket {name} fehlt - pip install -r requirements.txt")
    return Path(next(iter(spec.submodule_search_locations)))


def _licence_files(name: str) -> list[Path]:
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return []
    out = []
    for p in dist.files or []:
        if (len(p.parts) >= 2 and p.parts[0].endswith(".dist-info")
                and any(k in p.name.upper() for k in ("LICEN", "COPYING"))):
            out.append(Path(str(p.locate())))
    return sorted(out)


# --- Gegenprobe --------------------------------------------------------
def _signatures_via(shell: str, files: list[Path]) -> tuple[dict[Path, tuple[str, str]], str]:
    """Ein Durchlauf mit einer PowerShell. Liefert (Ergebnis, Rohausgabe)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8-sig") as fh:
        fh.write("\n".join(str(p) for p in files))
        listfile = fh.name
    # Fehler je Datei landen als 'ERROR ...' in der Ausgabe statt nur auf
    # stderr - eine Gegenprobe darf nie stumm mit leeren Werten enden.
    script = (
        "Import-Module Microsoft.PowerShell.Security -ErrorAction SilentlyContinue; "
        "$paths = Get-Content -LiteralPath '" + listfile.replace("'", "''") + "'; "
        "foreach ($p in $paths) { if (-not $p) { continue }; try { "
        "$s = Get-AuthenticodeSignature -LiteralPath $p -ErrorAction Stop; "
        "$cn = ''; if ($s.SignerCertificate) { $cn = $s.SignerCertificate.Subject }; "
        "Write-Output ('{0}|{1}|{2}' -f $s.Status, $cn, $p) } catch { "
        "Write-Output ('ERROR {0}||{1}' -f ($_.Exception.Message -replace '[\\r\\n|]', ' '), $p) } }")
    try:
        r = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
    finally:
        os.unlink(listfile)
    raw = f"[{shell}] exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    out: dict[Path, tuple[str, str]] = {}
    for line in r.stdout.splitlines():
        if line.count("|") >= 2:
            status, signer, path = line.split("|", 2)
            out[Path(path.strip())] = (status.strip(), signer.strip())
    return out, raw


def _signatures(files: list[Path]) -> dict[Path, tuple[str, str]]:
    """Authenticode-Status und Unterzeichner je Datei (Windows-Bordmittel).

    Zuerst PowerShell 7 (pwsh), dann Windows PowerShell. Grund (CI-Lauf
    33960974956, 05.09.2026): aus einem pwsh-Elternprozess heraus lieferte
    Windows PowerShell fuer JEDE Datei einen leeren Status, und die
    Gegenprobe meldete signierte Dateien als unsigniert. Jetzt gilt ein
    Durchlauf nur, wenn er fuer jede Datei einen echten Status liefert."""
    shells = [s for s in (shutil.which("pwsh"), shutil.which("powershell")) if s]
    if not shells:
        raise SystemExit("Weder pwsh noch powershell gefunden - Signaturen nicht pruefbar.")
    attempts = []
    for shell in shells:
        out, raw = _signatures_via(shell, files)
        complete = (len(out) == len(files)
                    and all(out[p][0] and not out[p][0].startswith("ERROR") for p in files))
        if complete:
            log(f"  Signaturen geprueft mit {Path(shell).name}")
            return out
        attempts.append(raw)
    raise SystemExit("Signaturpruefung unvollstaendig:\n" + "\n".join(a[-3000:] for a in attempts))


def _selftest(out: Path) -> str:
    """Kopie des Ordners starten (Umgebungsvariable S2TWEAKER_SELFTEST, siehe
    tools/launcher.py). Die Kopie, damit der ausgelieferte Ordner keine
    settings.json oder Cache-Reste aus der Probe enthaelt."""
    with tempfile.TemporaryDirectory(prefix="s2t_selftest_",
                                     ignore_cleanup_errors=True) as tmp:
        copy = Path(tmp) / APP
        shutil.copytree(out, copy)
        report = Path(tmp) / "selftest.txt"
        env = dict(os.environ, S2TWEAKER_SELFTEST=str(report))
        try:
            r = subprocess.run([str(copy / f"{APP}.exe")], cwd=copy, env=env,
                               timeout=300)
            code: int | str = r.returncode
        except subprocess.TimeoutExpired:
            code = "Timeout"
        text = report.read_text(encoding="utf-8") if report.is_file() else "(keine Ausgabe)"
        if code != 0 or not text.rstrip().endswith("OK"):
            raise SystemExit(f"SELBSTTEST FEHLGESCHLAGEN (Exit {code}):\n{text}")
        return text


def verify(out: Path, selftest: bool = True) -> None:
    internal = out / "_internal"
    exe = out / f"{APP}.exe"
    problems: list[str] = []

    # 1) Byte fuer Byte pythonw.exe
    if _sha256(exe) != _sha256(PREFIX / "pythonw.exe"):
        problems.append(f"{exe.name} ist nicht die unveraenderte pythonw.exe")

    # 2) Signaturen: alles gueltig, einzige Ausnahme repak.exe
    binaries = sorted(p for p in out.rglob("*")
                      if p.suffix.lower() in (".exe", ".dll", ".pyd"))
    sigs = _signatures(binaries)
    for p in binaries:
        status, signer = sigs.get(p, ("?", ""))
        if p == internal / "repak.exe":
            if status == "Valid":
                log(f"  Hinweis: repak.exe ist signiert ({signer})")
            continue
        if status != "Valid":
            problems.append(f"{p.relative_to(out)}: Signatur {status}")
    if "Python Software Foundation" not in sigs.get(exe, ("", ""))[1]:
        problems.append(f"{exe.name}: nicht von der Python Software Foundation signiert")

    # 3) Layout: genau zwei EXEs, keine verbotenen Dateien, Pflichtdateien
    exes = sorted(p.relative_to(out).as_posix() for p in binaries
                  if p.suffix.lower() == ".exe")
    if exes != [f"{APP}.exe", "_internal/repak.exe"]:
        problems.append(f"ausfuehrbare Dateien: {exes}")
    for p in out.rglob("*"):
        if p.name.lower().startswith(FORBIDDEN):
            problems.append(f"verbotene Datei: {p.relative_to(out)}")
    for rel in (PTH, PYDLL, f"_internal/{STDLIB_ZIP}", "_internal/sitecustomize.py",
                "_internal/repak.exe", "_internal/s2tweaker/gui.py",
                "_internal/assets/icon.ico", "_internal/customtkinter/__init__.py"):
        if not (out / rel).is_file():
            problems.append(f"fehlt: {rel}")
    if (internal / STDLIB_ZIP).is_file():
        with zipfile.ZipFile(internal / STDLIB_ZIP) as z:
            zipped = set(z.namelist())
        for need in ("site.pyc", "encodings/__init__.pyc", "tkinter/__init__.pyc"):
            if need not in zipped:
                problems.append(f"{STDLIB_ZIP}: {need} fehlt")
        for bad in ("ssl.pyc", "socket.pyc", "asyncio/__init__.pyc"):
            if bad in zipped:
                problems.append(f"{STDLIB_ZIP}: {bad} darf nicht drin sein")

    # 4) Keine Nutzerdaten, keine Reste, keine Heimpfade des Bau-Rechners.
    #    repak.exe ist ausgenommen: Rust kompiliert Registry-Pfade des
    #    Bau-Nutzers ein (in der CI "runneradmin"), das ist nicht unser Code.
    for junk in ("settings.json", "cache", "output", "presets", f"{APP}_error.log"):
        if (out / junk).exists():
            problems.append(f"gehoert nicht ins Paket: {junk}")
    homes = {str(Path.home()).lower()}
    if os.environ.get("USERPROFILE"):
        homes.add(os.environ["USERPROFILE"].lower())
    needles = [h.encode() for h in homes] + [h.encode("utf-16-le") for h in homes]
    for p in out.rglob("*"):
        if not p.is_file() or p.name == "repak.exe" or p.stat().st_size > 40_000_000:
            continue
        blob = p.read_bytes().lower()
        if any(n in blob for n in needles):
            problems.append(f"enthaelt einen Heimpfad des Bau-Rechners: {p.relative_to(out)}")

    if problems:
        raise SystemExit("GEGENPROBE FEHLGESCHLAGEN:\n  " + "\n  ".join(problems))

    files = [p for p in out.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    log(f"Gegenprobe OK: {len(files)} Dateien, {total:,} Bytes, "
        f"{len(binaries)} Binaerdateien signiert (Ausnahme repak.exe), "
        f"{exe.name} == pythonw.exe")
    if selftest:
        text = _selftest(out)
        log("Selbsttest OK:\n    " + "\n    ".join(text.rstrip().splitlines()))


# --- Der Bau -----------------------------------------------------------
def build(distpath: Path) -> Path:
    if sys.platform != "win32":
        raise SystemExit("Der Programmordner wird nur unter Windows gebaut.")
    missing = [n for n in ("pythonw.exe", PYDLL, "DLLs", "Lib", "tcl", "LICENSE.txt")
               if not (PREFIX / n).exists()]
    if missing:
        raise SystemExit(f"{PREFIX} ist keine python.org-Installation, es fehlt: "
                         + ", ".join(missing))
    log(f"S2Tweaker {__version__} mit Python {sys.version.split()[0]} aus {PREFIX}")

    out = distpath / APP
    if out.exists():
        try:
            shutil.rmtree(out)
        except OSError as exc:
            raise SystemExit(f"{out} laesst sich nicht entfernen ({exc}) - "
                             "laeuft noch eine S2Tweaker.exe? Sonst --distpath.")
    internal = out / "_internal"
    internal.mkdir(parents=True)

    # 1) Wurzel: Starter, Laufzeit, deren DLLs, Suchpfad
    _copy(PREFIX / "pythonw.exe", out / f"{APP}.exe")
    _copy(PREFIX / PYDLL, out / PYDLL)
    root_deps = _resolve_deps([PREFIX / "pythonw.exe", PREFIX / PYDLL])
    for dep in root_deps:
        _copy(dep, out / dep.name)
    (out / PTH).write_text(f"_internal\\{STDLIB_ZIP}\n_internal\nimport site\n",
                           encoding="ascii")
    log(f"Wurzel: {APP}.exe (= pythonw.exe), {PYDLL}, "
        + ", ".join(d.name for d in root_deps) + f", {PTH}")

    # 2) Erweiterungsmodule und ihre DLLs
    pyds = []
    for name in EXTENSIONS:
        src = PREFIX / "DLLs" / f"{name}.pyd"
        if not src.is_file():
            raise SystemExit(f"Erweiterung fehlt in der Installation: {src}")
        _copy(src, internal / src.name)
        pyds.append(src)
    ext_deps = _resolve_deps(pyds)
    for dep in ext_deps:
        _copy(dep, internal / dep.name)
    # repak.exe und die Erweiterungen brauchen die VC-Laufzeit auch in
    # _internal, damit nichts vom Systemordner abhaengt.
    for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
        if (out / name).is_file():
            _copy(out / name, internal / name)
    log(f"Erweiterungen: {len(pyds)} .pyd + " + ", ".join(d.name for d in ext_deps))

    # 3) Standardbibliothek
    n = _build_stdlib_zip(internal / STDLIB_ZIP)
    log(f"Standardbibliothek: {n} Module in {STDLIB_ZIP} "
        f"({(internal / STDLIB_ZIP).stat().st_size:,} Bytes)")

    # 4) Tcl/Tk-Skripte (tcl8.6, tk8.6 und der Modulordner tcl8)
    tcl_count = 0
    for d in sorted((PREFIX / "tcl").iterdir()):
        if d.is_dir() and (d.name.startswith("tcl") or d.name.startswith("tk")) \
                and d.name[2:3] != "s" and not d.name.startswith("tclConfig"):
            tcl_count += _copy_tree(d, internal / "tcl" / d.name,
                                    skip_dirs=TCL_SKIP_DIRS,
                                    skip_suffixes=(".lib", ".sh"))
    log(f"Tcl/Tk: {tcl_count} Dateien")

    # 5) Pakete: lesbarer Quelltext + vorkompiliertes __pycache__
    n = _copy_tree(REPO / "s2tweaker", internal / "s2tweaker",
                   skip_dirs={"__pycache__"}, only_suffixes=(".py",))
    log(f"s2tweaker: {n} Dateien")
    for name in SITE_PACKAGES:
        n = _copy_tree(_package_dir(name), internal / name,
                       skip_dirs={"__pycache__"}, skip_suffixes=(".pyc",))
        for lic in _licence_files(name):
            _copy(lic, internal / "licenses" / f"{name}-{lic.name}")
        log(f"{name}: {n} Dateien")
    for name in ("s2tweaker", *SITE_PACKAGES):
        _compile_tree(internal / name, f"_internal/{name}")

    # 6) Starter
    _copy(REPO / "tools" / "launcher.py", internal / "sitecustomize.py")
    if not compileall.compile_file(str(internal / "sitecustomize.py"),
                                   ddir="_internal", quiet=1, force=True,
                                   optimize=0, invalidation_mode=UNCHECKED):
        raise SystemExit("sitecustomize.py kompiliert nicht")

    # 7) Beigaben und Lizenzen
    _copy(REPO / "assets" / "icon.ico", internal / "assets" / "icon.ico")
    _copy_tree(REPO / "assets" / "help", internal / "assets" / "help")
    _copy(REPO / "tools" / "repak.exe", internal / "repak.exe")
    _copy(PREFIX / "LICENSE.txt", internal / "licenses" / "PYTHON-LICENSE.txt")
    _copy(REPO / "THIRD_PARTY_LICENSES.txt",
          internal / "licenses" / "THIRD_PARTY_LICENSES.txt")
    for terms in sorted((internal / "tcl").rglob("license.terms")):
        _copy(terms, internal / "licenses" / "TCL-TK-license.terms")
        break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--distpath", default=str(REPO / "dist"),
                    help="Zielordner (Standard: dist/); darin entsteht S2Tweaker/")
    ap.add_argument("--no-selftest", action="store_true",
                    help="Ordner nur zusammenstellen, nicht probestarten")
    args = ap.parse_args()

    out = build(Path(args.distpath).resolve())
    verify(out, selftest=not args.no_selftest)
    files = sum(1 for p in out.rglob("*") if p.is_file())
    log(f"\nFertig: {out} ({files} Dateien)")


if __name__ == "__main__":
    main()
