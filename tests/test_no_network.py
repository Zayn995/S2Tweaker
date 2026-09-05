"""Das Programm darf ueberhaupt kein Netz mehr anfassen (seit 1.19.2).

Ersetzt test_update_check.py. Der Update-Check ist entfernt worden, und
zwar nicht aus Sicherheitsgefuehl, sondern weil Nexus' Regeln woertlich
sagen: "Files (especially executables) that connect to the internet to
download or send information and/or files are prohibited unless where it
is crucial for the functioning of the mod/utility" — und direkt danach:
"'auto update' functionality does not qualify as crucial".

Der Wert der Entfernung liegt darin, dass sie NACHPRUEFBAR ist: wer den
oeffentlichen Quelltext greppt, findet kein urllib und keinen Socket.
Genau das prueft diese Datei — damit die Zusage nicht beim naechsten
bequemen Einfall wieder still kaputtgeht.

URL-Zeichenketten sind erlaubt und bleiben: der Oodle-Assistent ZEIGT
eine Adresse zum Kopieren an. Verboten ist, sie abzurufen.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

PAKET = ROOT / "s2tweaker"
VERBOTEN = {"urllib", "socket", "http", "requests", "ssl", "ftplib",
            "smtplib", "telnetlib", "webbrowser", "xmlrpc", "asyncio"}
VERBOTENE_AUFRUFE = {"urlopen", "urlretrieve", "socket", "create_connection",
                     "getaddrinfo", "connect"}

# --- 1) Kein Modul des Pakets importiert etwas Netzfaehiges --------------
# Mitgeprueft: der Starter des Programmordners (wird als sitecustomize.py
# ausgeliefert) - er ist Teil dessen, was beim Nutzer laeuft.
for datei in sorted(PAKET.glob("*.py")) + [ROOT / "tools" / "launcher.py"]:
    baum = ast.parse(datei.read_text(encoding="utf-8-sig"))
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            for alias in knoten.names:
                wurzel = alias.name.split(".")[0]
                assert wurzel not in VERBOTEN, \
                    f"{datei.name}:{knoten.lineno} importiert {alias.name}"
        elif isinstance(knoten, ast.ImportFrom) and knoten.module:
            wurzel = knoten.module.split(".")[0]
            assert wurzel not in VERBOTEN, \
                f"{datei.name}:{knoten.lineno} importiert aus {knoten.module}"
        elif isinstance(knoten, ast.Call):
            ziel = knoten.func
            name = (ziel.attr if isinstance(ziel, ast.Attribute)
                    else ziel.id if isinstance(ziel, ast.Name) else "")
            assert name not in VERBOTENE_AUFRUFE, \
                f"{datei.name}:{knoten.lineno} ruft {name}() auf"
print("Kein Netz-Import, kein Netz-Aufruf im Paket  OK")

# --- 2) Die Symbole der alten Update-Funktion sind wirklich weg ----------
for name in ("UPDATE_API_URL", "UPDATER_URL", "RELEASES_PAGE",
             "update_verdict", "_version_tuple"):
    assert not hasattr(gui, name), f"gui.{name} lebt wieder"
print("Alte Update-Symbole entfernt  OK")

# --- 3) Auch kein Knopf dafuer in der Oberflaeche ------------------------
app = gui.App()
app.update()
try:
    for name in ("btn_update", "btn_updater"):
        assert not hasattr(app, name), f"App.{name} ist zurueck"
    # Was in Zeile 2 bleiben MUSS
    for name in ("search_entry", "btn_changed", "btn_faq", "btn_oodle"):
        wdg = getattr(app, name)
        assert wdg.winfo_ismapped(), name + " nicht sichtbar"
    assert app.search_entry.winfo_rooty() > app.btn_confirm.winfo_rooty(), \
        "Suchfeld muss unter der Spielordner-Zeile liegen"
finally:
    try:
        app.destroy()
    except Exception:
        pass
print("Werkzeugleiste ohne Update-Knopf  OK")

# --- 4) update.bat wandert weiterhin NICHT ins Spieler-ZIP ---------------
# Sie liegt nur noch als eigenstaendiger Download im Repo; im Paket der
# Spieler hat ein Skript, das Programmdateien ersetzt, nichts verloren.
zips = (ROOT / "tools" / "make_release_zips.py").read_text(encoding="utf-8")
assert 'z.write(out / "update.bat"' not in zips, \
    "update.bat wandert wieder ungefragt ins Spieler-ZIP"
assert '"update.bat" not in names' in zips, "Gegenprobe im ZIP-Bauer fehlt"

bat = ROOT / "release" / "update.bat"
if bat.is_file():
    roh = bat.read_text(encoding="utf-8")
    assert roh.isascii(), "update.bat muss reines ASCII sein (cmd liest cp437)"
print("update.bat bleibt aussen vor  OK")

print("\nAlles gruen: das Werkzeug kann nicht mehr ins Netz.")
