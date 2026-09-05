"""Das Werkzeug laedt NICHTS nach — weder wir noch das mitgelieferte repak.

Hintergrund (04.09.2026): Bis dahin holte S2Tweaker die proprietaere
oo2core_9_win64.dll bei Bedarf selbst aus dem Netz, und die
Upstream-repak.exe konnte das ebenfalls. Ein Programm, das zur Laufzeit
eine Bibliothek herunterlaedt und als nativen Code ausfuehrt, zeigt exakt
das Verhalten eines Droppers — einer der Gruende, warum Virenscanner
solche Werkzeuge markieren, und der Nexus-Support die Datei nicht
freigeben konnte.

Seitdem gilt: die DLL wird nur noch LOKAL gesucht, und fehlt sie, bekommt
der Nutzer einen Klartext-Dialog mit Link und Zielordner. Ein repak.exe
gibt es seit 05.09.2026 gar nicht mehr: Paks liest und schreibt
s2tweaker/pakfile.py in reinem Python, die DLL wird per ctypes geladen.

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
    pakio.ensure_oodle()
except pakio.OodleError as exc:
    text = str(exc)
    assert "never downloads it" in text, text[:200]
    assert pakio.OODLE_URL in text, "Bezugsquelle fehlt im Hilfetext"
    assert "Confirm & load game data" in text, "Handlungsanweisung fehlt"
    # Genannt wird der Ordner mit S2Tweaker.exe — NICHT der interne
    # Ablageort neben repak.exe. Sonst widerspricht der Fehlertext dem
    # Assistenten und dem Bild darin.
    assert str(pakio.app_dir()) in text, "Zielordner wird nicht genannt"
    assert "_internal" not in text, "Fehlertext nennt wieder _internal"
else:
    raise AssertionError("ensure_oodle() ist ohne DLL durchgelaufen")
finally:
    pakio._local_oodle_candidates = real_candidates
    pakio.oodle_cache_dir = real_cache
print("ensure_oodle: klare Anleitung statt Download  OK")

# --- 3) Kein repak.exe mehr: Paks liest und schreibt reines Python -----
src = (ROOT / "s2tweaker" / "pakio.py").read_text(encoding="utf-8")
assert "subprocess" not in src, "pakio.py ruft wieder ein externes Programm auf"
assert not (ROOT / "tools" / "build_repak.py").exists(), "tools/build_repak.py ist zurueck"
from s2tweaker import pakfile
assert pakfile.PakFile and pakfile.write_pak and pakfile.load_oodle
print("pakio/pakfile: kein externes Programm, kein repak-Bauskript  OK")

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
    assert "Step 1 of 3" in seite1, "Schrittanzeige fehlt"
    # Kurzfassung fuer Nicht-Leser (Besitzer, 05.09.2026) auf jeder Seite
    assert "TL;DR" in seite1 and "Press “Copy” below" in seite1, "TL;DR Seite 1 fehlt"
    # Kopierknopf fuellt die Zwischenablage und quittiert
    assert klick("Copy"), "Kopierknopf nicht gefunden"
    app.update()
    assert app.clipboard_get() == pakio.OODLE_URL, "Link nicht in der Ablage"
    assert "Copied" in " ".join(texte(win)), "Knopf quittiert den Klick nicht"

    # Seite 2: Browser-Bild + Hinweis auf die Sicherheitsabfrage
    assert klick("Next"), "Weiter-Knopf fehlt"
    app.update()
    seite2 = " ".join(texte(win))
    assert "Step 2 of 3" in seite2
    assert "unverified" in seite2, "Hinweis zur Browser-Warnung fehlt"
    assert "TL;DR" in seite2 and "say yes" in seite2, "TL;DR Seite 2 fehlt"

    # Seite 3: Zielordner + Neustart
    assert klick("Next")
    app.update()
    seite3 = " ".join(texte(win))
    assert "Step 3 of 3" in seite3
    assert "restart S2Tweaker" in seite3, "Neustart-Hinweis fehlt"
    assert "TL;DR" in seite3 and "Restart S2Tweaker. Done." in seite3, "TL;DR Seite 3 fehlt"
    # Der genannte Ordner MUSS der mit S2Tweaker.exe sein. Frueher stand
    # dort der Ordner von repak.exe — im Ordner-Build also `_internal`,
    # und damit widersprach das Feld dem Bild und dem Satz daneben
    # ("not into the _internal folder"). Genau das darf nicht zurueckkommen.
    assert str(gui.app_dir()) in seite3, "Zielordner fehlt oder ist falsch"
    assert "_internal" not in str(app._oodle_target_dir()), \
        "Der Assistent nennt wieder den _internal-Ordner als Ablageort"
    assert app._oodle_target_dir() == gui.app_dir()

    # Seite 3 ist die letzte: kein "Next" mehr, sondern "Done".
    # Frueher folgte hier eine vierte Seite fuer update.bat. Die ist mit
    # 1.19.2 weg, weil die Update-Funktion selbst weg ist.
    assert "Done" in seite3, "Abschluss-Knopf fehlt"
    assert "update.bat" not in seite3, "Der Assistent bewirbt wieder den Updater"
finally:
    pakio.oodle_available = real_avail
    try:
        app.destroy()
    except Exception:
        pass
print("Assistent: 3 Seiten, Warnung, Entschuldigung, Kopieren, Neustart  OK")

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
    assert not hasattr(app2, "btn_updater"),         "Die Updater-Ampel ist zurueck - die Update-Funktion ist weg"
finally:
    pakio.oodle_available = real_avail2
    try:
        app2.destroy()
    except Exception:
        pass
print("Ampel: Oodle ready/missing, keine Updater-Ampel mehr  OK")

# --- 4b) Die Bilder liegen bei -----------------------------------------
for name in ("oodle_browser.png", "oodle_folder.png"):
    img = ROOT / "assets" / "help" / name
    assert img.is_file() and img.stat().st_size > 5000, f"{name} fehlt"
assert gui._asset("help", "oodle_browser.png").is_file()
print("Assistenten-Bilder vorhanden  OK")

print("\nKEIN-DOWNLOAD-TEST OK")
