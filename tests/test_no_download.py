"""Das Werkzeug laedt NICHTS nach — weder wir noch das mitgelieferte repak.

Hintergrund (04.09.2026): Bis dahin holte S2Tweaker die proprietaere
oo2core_9_win64.dll bei Bedarf selbst aus dem Netz, und die
Upstream-repak.exe konnte das ebenfalls. Ein Programm, das zur Laufzeit
eine Bibliothek herunterlaedt und als nativen Code ausfuehrt, zeigt exakt
das Verhalten eines Droppers — einer der Gruende, warum Virenscanner
solche Werkzeuge markieren, und der Nexus-Support die Datei nicht
freigeben konnte.

Seitdem gilt: die DLL wird nur noch LOKAL gesucht, und fehlt sie, bekommt
der Nutzer einen Klartext-Dialog mit Link und Zielordner. repak wird aus
dem Quellcode gebaut, wobei die Download-Funktion samt HTTP-/TLS-Stack
entfernt wird (tools/build_repak.py).

Dieser Test haelt beide Haelften fest. Er braucht weder Spiel noch Netz.
"""
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

# --- 1) In unserem Code gibt es keinen Download-Weg mehr ----------------
src = (ROOT / "s2tweaker" / "pakio.py").read_text(encoding="utf-8")
for verboten in ("urllib", "urlopen", "_download_oodle", "requests."):
    assert verboten not in src, f"pakio.py enthaelt wieder {verboten!r}"
assert not hasattr(pakio, "_download_oodle"), "Download-Funktion ist zurueck"
print("pakio.py: kein Download-Code  OK")

# --- 2) Fehlt die DLL, kommt die Anleitung (kein stiller Versuch) -------
missing = SCRATCH / "kein_oodle"
missing.mkdir(exist_ok=True)
(missing / "repak.exe").write_bytes(b"nur eine Attrappe")
real_candidates = pakio._local_oodle_candidates
real_cache = pakio.oodle_cache_dir
pakio._local_oodle_candidates = lambda pak=None: []
pakio.oodle_cache_dir = lambda: missing
try:
    pakio.ensure_oodle(missing / "repak.exe")
except pakio.OodleError as exc:
    text = str(exc)
    assert "never downloads it" in text, text[:200]
    assert pakio.OODLE_URL in text, "Bezugsquelle fehlt im Hilfetext"
    assert "Confirm & load game data" in text, "Handlungsanweisung fehlt"
    assert str(missing) in text, "Zielordner wird nicht genannt"
else:
    raise AssertionError("ensure_oodle() ist ohne DLL durchgelaufen")
finally:
    pakio._local_oodle_candidates = real_candidates
    pakio.oodle_cache_dir = real_cache
print("ensure_oodle: klare Anleitung statt Download  OK")

# --- 3) Die mitgelieferte repak.exe ist UNSER Build ---------------------
repak = ROOT / "tools" / "repak.exe"
assert repak.is_file(), "tools/repak.exe fehlt"
blob = repak.read_bytes().lower()
for stack in (b"ureq", b"rustls", b"webpki"):
    assert stack not in blob, (
        f"tools/repak.exe enthaelt {stack!r} — das ist der Upstream-Build "
        "mit Download-Funktion. Neu bauen: python tools/build_repak.py")
print(f"tools/repak.exe ({repak.stat().st_size:,} B): kein HTTP-/TLS-Stack  OK")

# --- 4) Der Start-Hinweis erscheint genau dann, wenn die DLL fehlt ------
shown = []
gui.messagebox.showinfo = lambda title, msg: shown.append(msg)
app = gui.App()
app.update()
real_avail = pakio.oodle_available
try:
    pakio.oodle_available = lambda pak=None: True
    app._check_oodle_present()
    assert not shown, "Dialog kam, obwohl die Bibliothek da ist"
    pakio.oodle_available = lambda pak=None: False
    app._check_oodle_present()
    assert len(shown) == 1, f"erwartet 1 Dialog, bekam {len(shown)}"
    assert pakio.OODLE_URL in shown[0] and "only needed to read" in shown[0]
finally:
    pakio.oodle_available = real_avail
    try:
        app.destroy()
    except Exception:
        pass
print("Start-Hinweis: nur bei fehlender Bibliothek, mit Link  OK")

# --- 5) Das Bau-Skript fuer repak ist da und pinnt eine Version --------
script = (ROOT / "tools" / "build_repak.py").read_text(encoding="utf-8")
assert re.search(r'REPAK_TAG = "v\d+\.\d+\.\d+"', script), "repak-Version nicht gepinnt"
assert "ureq" in script, "der Eingriff entfernt ureq nicht mehr"
print("tools/build_repak.py: Version gepinnt, Eingriff vorhanden  OK")

print("\nKEIN-DOWNLOAD-TEST OK")
