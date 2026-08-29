# S2Tweaker — Anweisungen für Claude

GUI-Tool (Python/customtkinter), das aus Reglern eine `.pak`-Tweak-Mod für
S.T.A.L.K.E.R. 2 erzeugt. Besitzer: Zayn995 (kann nicht coden — erkläre
Änderungen einfach und erledige technische Schritte komplett selbst).
Kompletter Projektstand: siehe [HANDOVER.md](HANDOVER.md).
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
python test_generate.py   # Ende-zu-Ende-Test: baut Test-Pak mit vielen Tweaks
build.bat                 # baut dist\S2Tweaker.exe (PyInstaller)
```

Hinweis: Auf manchen Rechnern zeigen `python` und `pip` auf verschiedene
Installationen (WindowsApps-Alias!). Bei ModuleNotFoundError nach pip install:
`python -c "import sys; print(sys.executable)"` mit `pip --version` vergleichen
und den expliziten Interpreter-Pfad verwenden.

## Workflows

- Neue Version veröffentlichen: Skill `release-version`
- Neuen Tweak einbauen: Skill `add-tweak`
