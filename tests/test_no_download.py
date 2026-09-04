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

# --- 4) Der Assistent erscheint genau dann, wenn die DLL fehlt ---------
app = gui.App()
app.update()
real_avail = pakio.oodle_available
try:
    pakio.oodle_available = lambda pak=None: True
    app._check_oodle_present()
    assert getattr(app, "_oodle_win", None) is None,         "Assistent kam, obwohl die Bibliothek da ist"

    pakio.oodle_available = lambda pak=None: False
    app._check_oodle_present()
    win = getattr(app, "_oodle_win", None)
    assert win is not None and win.winfo_exists(), "Assistent kam nicht"
    app.update()

    def texte(w):
        """Alle sichtbaren Texte einsammeln — auch den Inhalt von
        Eingabefeldern, in denen die Links stehen."""
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
        """Knopf mit dieser Beschriftung druecken (beliebig tief)."""
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

    # Seite 1: Warnung, Entschuldigung, Kopierknopf, Link
    seite1 = " ".join(texte(win))
    assert "Without this file" in seite1, "gelbe Warnung fehlt"
    assert "Sorry that this is on you" in seite1, "Entschuldigung fehlt"
    assert "Copy" in seite1, "Kopierknopf fehlt"
    assert "Step 1 of 4" in seite1, "Schrittanzeige fehlt"
    # Kopierknopf fuellt die Zwischenablage und quittiert
    assert klick("Copy"), "Kopierknopf nicht gefunden"
    app.update()
    assert app.clipboard_get() == pakio.OODLE_URL, "Link nicht in der Ablage"
    assert "Copied" in " ".join(texte(win)), "Knopf quittiert den Klick nicht"

    # Seite 2: Browser-Bild + Hinweis auf die Sicherheitsabfrage
    assert klick("Next"), "Weiter-Knopf fehlt"
    app.update()
    seite2 = " ".join(texte(win))
    assert "Step 2 of 4" in seite2
    assert "unverified" in seite2, "Hinweis zur Browser-Warnung fehlt"

    # Seite 3: Zielordner + Neustart
    assert klick("Next")
    app.update()
    seite3 = " ".join(texte(win))
    assert "Step 3 of 4" in seite3
    assert "restart S2Tweaker" in seite3, "Neustart-Hinweis fehlt"

    # Seite 4: der Updater ist FREIWILLIG und wird als solcher benannt
    assert klick("Next")
    app.update()
    seite4 = " ".join(texte(win))
    assert "Step 4 of 4" in seite4
    assert "you do not need it" in seite4, "Freiwilligkeit steht nicht da"
    assert gui.UPDATER_URL in seite4, "Bezugsquelle des Updaters fehlt"
    assert "Done" in seite4, "Abschluss-Knopf fehlt"
finally:
    pakio.oodle_available = real_avail
    try:
        app.destroy()
    except Exception:
        pass
print("Assistent: 4 Seiten, Warnung, Entschuldigung, Kopieren, Neustart, "
      "optionaler Updater  OK")

# --- 4c) Die Ampeln zeigen beide Zustaende ------------------------------
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
    app2._refresh_updater_badge()
    assert app2.btn_updater.cget("text") in ("● Updater ready",
                                             "● Updater optional")
finally:
    pakio.oodle_available = real_avail2
    try:
        app2.destroy()
    except Exception:
        pass
print("Ampeln: Oodle ready/missing und Updater ready/optional  OK")

# --- 4b) Die Bilder liegen bei -----------------------------------------
for name in ("oodle_browser.png", "oodle_folder.png"):
    img = ROOT / "assets" / "help" / name
    assert img.is_file() and img.stat().st_size > 5000, f"{name} fehlt"
assert gui._asset("help", "oodle_browser.png").is_file()
print("Assistenten-Bilder vorhanden  OK")

# --- 5) Das Bau-Skript fuer repak ist da und pinnt eine Version --------
script = (ROOT / "tools" / "build_repak.py").read_text(encoding="utf-8")
assert re.search(r'REPAK_TAG = "v\d+\.\d+\.\d+"', script), "repak-Version nicht gepinnt"
assert "ureq" in script, "der Eingriff entfernt ureq nicht mehr"
print("tools/build_repak.py: Version gepinnt, Eingriff vorhanden  OK")

print("\nKEIN-DOWNLOAD-TEST OK")
