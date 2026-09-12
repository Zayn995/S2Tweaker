"""Verify library discovery is local-only and missing Oodle produces setup guidance.

Pak handling uses Python, with no bundled repak executable. No game or
network access is required by this suite."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker import pakio

# --- 1) No download path in application code ---
src = (ROOT / "s2tweaker" / "pakio.py").read_text(encoding="utf-8")
for verboten in ("urllib", "urlopen", "_download_oodle", "requests."):
    assert verboten not in src, f"pakio.py contains again: {verboten!r}"
assert not hasattr(pakio, "_download_oodle"), "Download function has returned"
print("pakio.py: no download code  OK")

# Missing Oodle must produce the manual setup guide.
missing = SCRATCH / "kein_oodle"
missing.mkdir(exist_ok=True)
(missing / "repak.exe").write_bytes(b"dummy fixture")
real_candidates = pakio._local_oodle_candidates
real_cache = pakio.oodle_cache_dir
pakio._local_oodle_candidates = lambda pak=None: []
pakio.oodle_cache_dir = lambda: missing
try:
    pakio.ensure_oodle()
except pakio.OodleError as exc:
    text = str(exc)
    assert "never downloads it" in text, text[:200]
    assert pakio.OODLE_URL in text, "Source link missing from help text"
    assert "Confirm & load game data" in text, "Action instructions missing"
    # Name the S2Tweaker.exe directory consistently with the illustrated guide.
    assert str(pakio.app_dir()) in text, "Destination folder not mentioned"
    assert "_internal" not in text, "Error text names _internal again"
else:
    raise AssertionError("ensure_oodle() succeeded without the DLL")
finally:
    pakio._local_oodle_candidates = real_candidates
    pakio.oodle_cache_dir = real_cache
print("ensure_oodle: clear instructions instead of a download  OK")

# Pak handling must not require repak.exe.
src = (ROOT / "s2tweaker" / "pakio.py").read_text(encoding="utf-8")
assert "subprocess" not in src, "pakio.py invokes an external program again"
assert not (ROOT / "tools" / "build_repak.py").exists(), "tools/build_repak.py has returned"
from s2tweaker import pakfile
assert pakfile.PakFile and pakfile.write_pak and pakfile.load_oodle
print("pakio/pakfile: no external program, no repak build script  OK")

# Show the setup guide when the library is absent.
app = gui.App()
app.update()
real_avail = pakio.oodle_available
try:
    pakio.oodle_available = lambda pak=None: True
    app._check_oodle_present()
    assert getattr(app, "_oodle_win", None) is None,         "Wizard appeared although the library is present"

    pakio.oodle_available = lambda pak=None: False
    app._check_oodle_present()
    win = getattr(app, "_oodle_win", None)
    assert win is not None and win.winfo_exists(), "Wizard did not appear"
    app.update()

    def texte(w):
        """Collect visible text, including link-entry contents."""
        out = []
        for child in w.winfo_children():
            try:
                if child.cget("text"):
                    out.append(str(child.cget("text")))
            except Exception:
                pass
            try:
                if hasattr(child, "get") and not hasattr(child, "winfo_children_x"):
                    value = child.get()
                    if isinstance(value, str) and value:
                        out.append(value)
            except Exception:
                pass
            out += texte(child)
        return out

    def klick(label, w=None):
        """Invoke a button with this label anywhere in the widget tree."""
        for child in (w or win).winfo_children():
            try:
                if label in str(child.cget("text")) and hasattr(child, "invoke"):
                    child.invoke()
                    return True
            except Exception:
                pass
            if klick(label, child):
                return True
        return False

    # Page 1: warning, apology, copy button, link.
    seite1 = " ".join(texte(win))
    assert "Without this file" in seite1, "Yellow warning missing"
    assert "Sorry that this is on you" in seite1, "Apology missing"
    assert "Copy" in seite1, "Copy button missing"
    assert "Step 1 of 3" in seite1, "Step indicator missing"
    # Each guide page has a short action summary.
    assert "TL;DR" in seite1 and "Press “Copy” below" in seite1, "TL;DR missing from page 1"
    # The copy button must populate the clipboard and acknowledge completion.
    assert klick("Copy"), "Copy button not found"
    app.update()
    assert app.clipboard_get() == pakio.OODLE_URL, "Link not copied to clipboard"
    assert "Copied" in " ".join(texte(win)), "Button does not acknowledge the click"

    # The download page includes its browser illustration and security-prompt guidance.
    assert klick("Next"), "Next button missing"
    app.update()
    seite2 = " ".join(texte(win))
    assert "Step 2 of 3" in seite2
    assert "unverified" in seite2, "Browser warning notice missing"
    assert "TL;DR" in seite2 and "say yes" in seite2, "TL;DR missing from page 2"

    # Page 3: destination folder and restart.
    assert klick("Next")
    app.update()
    seite3 = " ".join(texte(win))
    assert "Step 3 of 3" in seite3
    assert "restart S2Tweaker" in seite3, "Restart notice missing"
    assert "TL;DR" in seite3 and "Restart S2Tweaker. Done." in seite3, "TL;DR missing from page 3"
    # The destination must be the executable folder, matching the accompanying text.
    assert str(gui.app_dir()) in seite3, "Destination folder missing or incorrect"
    assert "_internal" not in str(app._oodle_target_dir()), \
        "Wizard incorrectly names _internal as the destination folder again"
    assert app._oodle_target_dir() == gui.app_dir()

    # The final page uses Done; no removed updater page remains.
    assert "Done" in seite3, "Finish button missing"
    assert "update.bat" not in seite3, "Wizard advertises the removed updater again"
finally:
    pakio.oodle_available = real_avail
    try:
        app.destroy()
    except Exception:
        pass
print("Wizard: 3 pages, warning, apology, copy, restart  OK")

# --- 4c) Status indicators display both states ---
app2 = gui.App()
app2.update()
real_avail2 = pakio.oodle_available
try:
    pakio.oodle_available = lambda pak=None: True
    app2._refresh_oodle_badge()
    assert "ready" in app2.btn_oodle.cget("text"), app2.btn_oodle.cget("text")
    pakio.oodle_available = lambda pak=None: False
    app2._refresh_oodle_badge()
    assert "missing" in app2.btn_oodle.cget("text"), app2.btn_oodle.cget("text")
    assert not hasattr(app2, "btn_updater"),         "Updater indicator has returned although the updater was removed"
finally:
    pakio.oodle_available = real_avail2
    try:
        app2.destroy()
    except Exception:
        pass
print("Status: Oodle ready/missing, no updater indicator  OK")

# Bundle the guide illustrations.
for name in ("oodle_browser.png", "oodle_folder.png"):
    img = ROOT / "assets" / "help" / name
    assert img.is_file() and img.stat().st_size > 5000, f"{name} missing"
assert gui._asset("help", "oodle_browser.png").is_file()
print("Wizard images present  OK")

print("\nNO DOWNLOAD TEST PASSED")
