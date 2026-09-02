"""Update-Check (GitHub Issue #3): Versionsvergleich pur + Header-Zeile 2.

Bewusst OHNE Netzzugriff: die Entscheidungslogik (update_verdict) ist eine
pure Funktion, der echte GET wird nie ausgeloest. Wie immer: SETTINGS_FILE
umbiegen, nie _on_close/_save_ui_settings rufen.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker import __version__
from s2tweaker.gui import _version_tuple, update_verdict

# --- 1) Versionslogik pur (ohne Netz) ------------------------------------
assert _version_tuple("v1.14.0") == (1, 14, 0)
assert _version_tuple("1.2") == (1, 2)
assert _version_tuple("") == ()
assert update_verdict("v9.9.9", "1.14.0") == "newer"
assert update_verdict("v2.0", "1.14.0") == "newer"
assert update_verdict("v1.10.0", "1.9.0") == "newer"      # 10 > 9, kein Textvergleich
assert update_verdict("v1.14.0", "1.14.0") == "current"
assert update_verdict("v1.13.9", "1.14.0") == "current"   # aelter = kein Update
assert update_verdict(None, "1.14.0") == "error"
assert update_verdict("", "1.14.0") == "error"
assert update_verdict("release", "1.14.0") == "error"
assert update_verdict("v" + __version__, __version__) == "current"
print("Versionslogik OK")

# --- 2) Header-Zeile 2 existiert und ist verkabelt ------------------------
app = gui.App()
app.update()
assert app.btn_update.cget("text").endswith("Check for updates")
assert str(app.btn_update.cget("state")) == "normal"
# Suche/Changed only/FAQ/Update leben in Zeile 2 UNTER der Spielordner-Zeile
assert app.search_entry.winfo_rooty() > app.btn_confirm.winfo_rooty(), \
    "Suchfeld muss unter der Spielordner-Zeile liegen"
for name in ("search_entry", "btn_changed", "btn_faq", "btn_update"):
    wdg = getattr(app, name)
    assert wdg.winfo_ismapped(), name + " nicht sichtbar"

# Doppelklick-Schutz: laeuft schon ein Check, passiert beim zweiten nichts
app._update_running = True
app._check_updates()
assert str(app.btn_update.cget("state")) == "normal", \
    "zweiter Klick darf den Knopf nicht anfassen"
print("Header-Zeile 2 OK")

# Das FAQ kennt den Update-Weg (Suchbegriff "autoupdate")
from s2tweaker.faq import FAQ_ENTRIES
hits = [e for e in FAQ_ENTRIES if "autoupdate" in e["k"]]
assert len(hits) == 1, f"FAQ-Eintrag zum Update fehlt/doppelt: {len(hits)}"
assert "update.bat" in hits[0]["a"], "FAQ-Antwort nennt update.bat nicht"
print(f"FAQ OK ({len(FAQ_ENTRIES)} Eintraege)")

# --- 3) update.bat: vorhanden, ASCII, richtige Ziele ----------------------
bat = ROOT / "release" / "update.bat"
raw = bat.read_bytes()
assert raw.isascii(), "update.bat muss reines ASCII sein (cmd liest cp437)"
text = raw.decode("ascii")
assert "api.github.com/repos/Zayn995/S2Tweaker/releases/latest" in text
assert "S2Tweaker.exe.bak" in text, "Backup der alten EXE fehlt"
assert "RELAUNCHED" in text, "Selbst-Ersetz-Schutz (Kopie in %TEMP%) fehlt"
assert "'*source*'" in text, "Source-ZIP-Ausschluss fehlt"
assert "pause" in text, "Fehlerpfade muessen lesbar bleiben (pause)"
# kein Versionsstand einkodiert: die bat holt IMMER releases/latest
import re
assert not re.search(r"v\d+\.\d+\.\d+", text), "Versionsnummer hardcodiert"

# das Spieler-ZIP liefert die Datei mit
zips = (ROOT / "tools" / "make_release_zips.py").read_text(encoding="utf-8")
assert 'update.bat' in zips, "make_release_zips packt update.bat nicht ein"

# im Dev-Modus (nicht eingefroren) bietet die GUI den Bat-Weg nicht an —
# es gibt ja keine EXE zum Ersetzen
assert app._updater_path() is None
print("update.bat OK")
