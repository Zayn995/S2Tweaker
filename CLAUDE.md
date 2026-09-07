# S2Tweaker — Anweisungen für Claude

GUI-Tool (Python/customtkinter), das aus Reglern eine `.pak`-Tweak-Mod für
S.T.A.L.K.E.R. 2 erzeugt. Besitzer: Zayn995 (kann nicht coden — erkläre
Änderungen einfach und erledige technische Schritte komplett selbst).
Kompletter Projektstand: siehe `HANDOVER.md` und `docs/ROADMAP.md` —
beide liegen NUR lokal im Ordner (nicht im Repo, siehe .gitignore).
Architektur & Mechanik: [README.md](README.md) · Recherche: [docs/SPEC.md](docs/SPEC.md).

## Eiserne Regeln

- **NIEMALS `vanilla/`, `cache/` oder `oo2core*.dll` committen** — extrahierte
  Spieldateien sind GSC-Copyright, die Oodle-DLL ist proprietär. `.gitignore`
  schützt das; nicht aufweichen.
- Patches erzeugen **nur abweichende Werte** (`_neq`-Checks in tweaks.py).
  Vanilla-Regler = kein Patch. Nie Spielwerte hardcoden — immer live aus der
  Installation lesen (`gd.resolve(...)`).
- Bei neuen Dateien in `NEEDED_FILES` (gamedata.py): **`CACHE_SCHEMA` erhöhen**.
- UI-Sprache: Englisch. Konversation mit dem Besitzer: Deutsch.

## Kommandos

```
pip install -r requirements.txt
python main.py            # GUI starten (Dev-Modus nutzt vanilla/, falls vorhanden)
python tests/run_all.py   # der Testlauf: 32 Suiten, ~1,2 min, OEFFNET KEIN FENSTER
python test_generate.py   # Ende-zu-Ende-Test: baut Test-Pak mit vielen Tweaks
build.bat                 # baut dist\S2Tweaker\ (signierte pythonw.exe + _internal, KEIN PyInstaller)
```

Hinweis: Auf manchen Rechnern zeigen `python` und `pip` auf verschiedene
Installationen (WindowsApps-Alias!). Bei ModuleNotFoundError nach pip install:
`python -c "import sys; print(sys.executable)"` mit `pip --version` vergleichen
und den expliziten Interpreter-Pfad verwenden.

⚠ **Testen (Regel seit 08.09.2026, ausdrücklich vom Besitzer):** Es gibt
keinen Lauf mehr, der Fenster aufmacht. Die GUI-Suiten sind aus jeder
automatischen Auswahl draußen — sie hängen sich auf und stören einander.
Was am Aussehen neu ist, wird **von Hand** geprüft
(`python tools/make_screenshots.py`, ein Fenster, dabei nichts anfassen).
**Nie zwei Läufe gleichzeitig starten**, und nichts Langlaufendes ohne
Ansage: der Besitzer sitzt am selben Rechner.

## Workflows

- Neuen Tweak einbauen: Skill `add-tweak`
- Großen, noch unerschlossenen cfg-Bereich analysieren (Vorstufe zum Bauen):
  Skill `research-cfg-block`
- Tweaks im Spiel gegenprüfen und Disclaimer pflegen: Skill `test-ingame`
- Neue Version veröffentlichen: Skill `release-version`
