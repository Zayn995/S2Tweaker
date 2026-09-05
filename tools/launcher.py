"""S2Tweaker launcher - the only glue between S2Tweaker.exe and the program.

This file is tools/launcher.py in the repository. tools/build_exe.py copies
it unchanged into the program folder as _internal/sitecustomize.py.

How the packaged program starts (there is no PyInstaller since 1.21.0):

1. S2Tweaker.exe is pythonw.exe from python.org, byte for byte, digitally
   signed by the Python Software Foundation. It loads python3XX.dll from
   the same folder.
2. The interpreter finds python3XX._pth next to that DLL. The file pins
   the module search path to _internal\\python3XX.zip and _internal -
   nothing else, not an installed Python, not PYTHONPATH - and contains
   the line "import site".
3. "site" imports a module named sitecustomize if one is on the path.
   That is Python's documented hook for site-specific start-up code, and
   this file is that module. It marks the build as packaged, points
   Tcl/Tk at their script libraries and starts the GUI.
4. When the window closes, this module ends the process explicitly
   (os._exit). Left to itself the interpreter would next try to read a
   program from standard input; started by a double-click there is none
   and it would exit anyway, but started from a shell with a pipe on
   stdin it would sit there invisibly until the pipe closes.

Self-test: with the environment variable S2TWEAKER_SELFTEST=<file> the
launcher does not open the GUI for real. It imports every bundled module
the program relies on, proves that no networking module is present, writes
and reads back a tiny pak in pure Python, builds the main window, tears it
down again and
writes a report to <file>. tools/build_exe.py runs this against a copy of
every build before the build counts as done.
"""
import os
import sys
import traceback
from pathlib import Path

INTERNAL = Path(__file__).resolve().parent      # ...\S2Tweaker\_internal
APP_DIR = INTERNAL.parent                       # the folder with S2Tweaker.exe

# Standard-library modules the program imports (s2tweaker/*.py) plus the
# ones customtkinter needs. Every one of them must come from the bundle.
STDLIB_NEEDED = (
    "dataclasses", "datetime", "functools", "hashlib", "json", "math",
    "os", "pathlib", "queue", "re", "shutil", "stat", "struct",
    "subprocess", "sys", "tempfile", "threading", "time", "tkinter",
    "tkinter.filedialog", "tkinter.messagebox", "traceback", "typing",
    "zipfile", "lzma", "bz2", "ctypes", "unicodedata", "decimal",
    "xml.parsers.expat", "select", "platform", "urllib.parse",
)
# ... and these must be ABSENT: the package ships without any networking
# capability at all, and that is checked, not promised.
STDLIB_ABSENT = ("socket", "ssl", "_socket", "_ssl")


def _prepare() -> None:
    # "frozen" is the marker py2exe, cx_Freeze and PyInstaller set on a
    # packaged program. s2tweaker reads it and then keeps settings, cache,
    # presets and output next to S2Tweaker.exe - the tool stays portable.
    sys.frozen = True
    # On Windows, `site` also appends sys.prefix - the folder with
    # S2Tweaker.exe, where settings, cache and output live - to sys.path.
    # The search path is _internal and nothing else, so drop everything
    # outside it.
    sys.path[:] = [p for p in sys.path
                   if Path(p).resolve().is_relative_to(INTERNAL)]
    # Tcl and Tk look for their script libraries relative to a Python
    # installation. Here they live in _internal\tcl, so name them
    # explicitly (PyInstaller's runtime hook did the same).
    tcl_root = INTERNAL / "tcl"
    for env, prefix, marker in (("TCL_LIBRARY", "tcl", "init.tcl"),
                                ("TK_LIBRARY", "tk", "tk.tcl")):
        for candidate in sorted(tcl_root.glob(prefix + "[0-9]*")):
            if (candidate / marker).is_file():
                os.environ[env] = str(candidate)
    # Until 1.22.0 the folder shipped repak.exe; an update extracted over
    # the old folder leaves it behind. It is not used any more (the pak
    # code is pure Python since 1.23.0) and Microsoft's ML engine dislikes
    # it - remove the leftover quietly.
    stale = INTERNAL / "repak.exe"
    if stale.exists():
        try:
            stale.unlink()
        except OSError:
            pass


def _selftest(report: Path) -> None:
    import hashlib
    import importlib

    lines = []
    from s2tweaker import __version__
    lines.append(f"S2Tweaker {__version__}")
    lines.append(f"executable={sys.executable}")
    lines.append(f"prefix={sys.prefix}")
    lines.append("path=" + ";".join(sys.path))
    assert all(Path(p).resolve().is_relative_to(INTERNAL) for p in sys.path), \
        f"search path leaves _internal: {sys.path}"

    for name in STDLIB_NEEDED:
        importlib.import_module(name)
    for name in STDLIB_ABSENT:
        try:
            importlib.import_module(name)
        except ImportError:
            continue
        raise AssertionError(
            f"{name} is importable - the package must not contain it")
    lines.append(f"stdlib: {len(STDLIB_NEEDED)} modules present, "
                 f"{'/'.join(STDLIB_ABSENT)} absent")

    # hashlib without OpenSSL (_hashlib is not shipped): built-in SHA-256
    empty = hashlib.sha256(b"").hexdigest()
    assert empty == ("e3b0c44298fc1c149afbf4c8996fb924"
                     "27ae41e4649b934ca495991b7852b855"), empty
    lines.append("hashlib: built-in sha256 OK")

    for name in ("cfgparse", "emit", "faq", "game", "gamedata", "gui",
                 "modscan", "names", "pakfile", "pakio", "tweaks",
                 "vendor_bin2cfg"):
        importlib.import_module("s2tweaker." + name)
    for name in ("customtkinter", "darkdetect", "packaging"):
        importlib.import_module(name)
    lines.append("s2tweaker, customtkinter, darkdetect, packaging import OK")

    from s2tweaker import gui, pakio
    # Compare resolved paths: sys.executable may carry an 8.3 short name
    # (C:\Users\RUNNER~1\...) when the folder was started via one.
    for name, got in (("gui", gui.app_dir()), ("pakio", pakio.app_dir())):
        assert Path(got).resolve() == APP_DIR, f"{name}.app_dir() = {got}"
    assert gui._asset("icon.ico").is_file(), gui._asset("icon.ico")
    assert gui._asset("help", "oodle_folder.png").is_file()
    # Paks in reinem Python (kein repak.exe mehr seit 05.09.2026): einmal
    # schreiben und zuruecklesen, und die alte Binaerdatei darf nicht da sein.
    import tempfile
    from s2tweaker import pakfile
    with tempfile.TemporaryDirectory(prefix="s2t_selftest_") as tmp:
        pak = pakfile.write_pak(Path(tmp) / "t.pak", [("a/b.cfg", b"x = 1\r\n")])
        with pakfile.PakFile(pak) as pk:
            assert pk.version.label == "V8B", pk.version
            assert pk.read("a/b.cfg") == b"x = 1\r\n"
    assert not (INTERNAL / "repak.exe").exists(), "repak.exe ist zurueck"
    lines.append("pak: pure-Python write/read roundtrip OK, no repak.exe")

    app = gui.App()
    app.update()
    lines.append(f"window: {app.title()} {app.geometry()}")
    app.destroy()
    lines.append("OK")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _report_crash(text: str) -> None:
    """pythonw.exe has no console: write the traceback next to the program
    and show it, otherwise the user only sees that nothing came up."""
    log = APP_DIR / "S2Tweaker_error.log"
    try:
        log.write_text(text, encoding="utf-8")
        where = f"\n\nThe full text was saved to:\n{log}"
    except OSError:
        where = ""
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("S2Tweaker could not start", text[-2000:] + where)
        root.destroy()
    except Exception:
        pass


def main() -> None:
    _prepare()
    report = os.environ.get("S2TWEAKER_SELFTEST")
    try:
        if report:
            _selftest(Path(report))
        else:
            from s2tweaker.gui import run
            run()
    except SystemExit as exc:
        # sys.exit() inside the program must not bubble up into `site`:
        # the interpreter would count that as a failed start-up (exit
        # code 1) instead of a clean exit.
        code = exc.code if isinstance(exc.code, int) else (
            0 if exc.code is None else 1)
        os._exit(code)
    except BaseException:
        text = traceback.format_exc()
        if report:
            try:
                Path(report).write_text("FAILED\n" + text, encoding="utf-8")
            finally:
                os._exit(2)
        _report_crash(text)
        os._exit(1)
    # Done. End the process here rather than returning into the
    # interpreter's start-up: it would go on to run argv[1] as a script (a
    # file dropped onto the exe) or read one from stdin (a pipe left open
    # by whoever started us) - see the module docstring, point 4. The
    # window is gone and every file the program writes is closed by then.
    os._exit(0)


main()
