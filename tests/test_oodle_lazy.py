"""Die Oodle-DLL wird NUR bei echtem Bedarf geholt.

Hintergrund (04.09.2026): `unpack()` rief `ensure_oodle()` unbedingt auf,
also lud jede Erstbenutzung 0,6 MB proprietaere Bibliothek herunter — und
genau dieser Download ist die Stelle, an der es bei Nutzer foxce hinter
einer HTTPS-Inspektion scheiterte.

Gemessen am echten Spiel braucht es die DLL gar nicht: pakchunk0 fuehrt
Oodle zwar im Kopf, die GameData-Eintraege liegen aber unkomprimiert
darin. Ohne DLL kamen alle 33 NEEDED_FILES byte-identisch heraus, ebenso
die drei Editions-Paks und die cfg-Eintraege aus 11 fremden Mod-Paks mit
Oodle im Kopf.

Dieser Test haelt das Verhalten fest, OHNE Spiel und ohne Netz: repak wird
durch eine Attrappe ersetzt. Erfolgreicher Aufruf => ensure_oodle darf
NICHT angefasst werden. Bricht repak mit Oodle-Fehler ab => es muss geholt
und der Aufruf wiederholt werden.
"""
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import pakio

FAKE_REPAK = ROOT / "tools" / "repak.exe"      # muss nur existieren
assert FAKE_REPAK.is_file(), "repak.exe fehlt im Repo"


class Recorder:
    """Ersetzt subprocess.run und protokolliert die Aufrufe."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def __call__(self, cmd, **kw):
        self.calls += 1
        code, err = self.results[min(self.calls - 1, len(self.results) - 1)]
        return types.SimpleNamespace(returncode=code, stdout="", stderr=err)


def patched(results):
    """(subprocess-Attrappe, oodle-Zaehler) einsetzen und zurueckgeben."""
    rec = Recorder(results)
    fetched = []
    pakio.subprocess.run = rec
    pakio.ensure_oodle = lambda *a, **k: fetched.append(1)
    return rec, fetched


real_run, real_ensure = subprocess.run, pakio.ensure_oodle
try:
    # --- 1) Erfolg => kein Download -------------------------------------
    rec, fetched = patched([(0, "")])
    pakio.unpack(Path("x.pak"), Path("out"), repak_exe=FAKE_REPAK)
    assert rec.calls == 1, rec.calls
    assert not fetched, "unpack() hat die Oodle-DLL geholt, obwohl repak lief"
    print("unpack: Erfolg ohne Oodle-Download  OK")

    # --- 2) Oodle-Fehler => holen und WIEDERHOLEN ------------------------
    rec, fetched = patched([(1, "Oodle loader error: something"), (0, "")])
    pakio.unpack(Path("x.pak"), Path("out"), repak_exe=FAKE_REPAK)
    assert fetched, "Oodle-Fehler wurde nicht mit einem Download beantwortet"
    assert rec.calls == 2, f"kein zweiter Versuch nach dem Download: {rec.calls}"
    print("unpack: Oodle-Fehler -> geholt und wiederholt  OK")

    # --- 3) Anderer Fehler => sofort melden, NICHT herunterladen ---------
    rec, fetched = patched([(1, "some unrelated failure")])
    try:
        pakio.unpack(Path("x.pak"), Path("out"), repak_exe=FAKE_REPAK)
    except RuntimeError as exc:
        assert "unrelated" in str(exc), exc
    else:
        raise AssertionError("Fehler wurde verschluckt")
    assert not fetched, "fremder Fehler loeste einen Oodle-Download aus"
    print("unpack: fremder Fehler -> kein Download, klare Meldung  OK")

    # --- 4) Der Mod-Scan-Weg verhaelt sich genauso ----------------------
    rec, fetched = patched([(0, "")])
    pakio.unpack_many(Path("x.pak"), Path("out"), ["a/b.cfg"],
                      repak_exe=FAKE_REPAK)
    assert not fetched, "unpack_many() hat die DLL ohne Not geholt"
    print("unpack_many: Erfolg ohne Oodle-Download  OK")
finally:
    subprocess.run = real_run
    pakio.subprocess.run = real_run
    pakio.ensure_oodle = real_ensure

print("\nOODLE-LAZY-TEST OK")
