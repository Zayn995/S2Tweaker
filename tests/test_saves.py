"""Speicherstaende-Limit (SaveLoadVariables.cfg) und Autosave-Intervall
(AutoSaveVariables.cfg) - Nexus-Recherche 05.09.2026 ("Bode's Unlimited
Saves", 343 Endorsements; das Intervall als Komfortidee dazu).

Beide Dateien sind unbinarisiert wie CoreVariables, die Patch-Datei heisst
darum <Name>.cfg_patch_<Mod>.cfg direkt in GameData/.

Prueft: Dateien im Extraktionsumfang + Schema-Bump, Vanilla-Werte live ==
Settings-Defaults (sonst wuerde die Vanilla-Stellung patchen), Patch-Format
({bpatch} auf beiden Ebenen, nur geaenderte Schluessel, Ganzzahlen), das
Intervall in Sekunden, Neutralzustand, Tweak-Zeilen.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData, NEEDED_FILES, CACHE_SCHEMA
from s2tweaker.tweaks import Settings, build_patches, summarize

for name in ("SaveLoadVariables.cfg", "AutoSaveVariables.cfg"):
    assert name in NEEDED_FILES, f"{name} fehlt im Extraktionsumfang"
assert CACHE_SCHEMA >= 17, "neue Dateien ohne Schema-Bump"
gd = GameData(VANILLA)
SL = "SaveLoadVariables.cfg_patch_S2Tweaker.cfg"
AS = "AutoSaveVariables.cfg_patch_S2Tweaker.cfg"

# --- 1) Vanilla live == Settings-Defaults --------------------------------
limits = gd.saveload.children["DefaultConfig"].children["SavesLimit"].values
default = Settings()
for key, field in (("Manual", "manual_save_slots"), ("Quick", "quick_save_slots"),
                   ("Auto", "auto_save_slots")):
    vanilla = int(parse_number(limits[key]))
    assert vanilla == getattr(default, field), (key, vanilla, getattr(default, field))
interval = parse_number(gd.autosave.children["DefaultConfig"].values["AutoSaveIntervalTime"])
assert abs(interval - default.autosave_interval_min * 60.0) < 1e-9, interval
print(f"Vanilla: Manual {limits['Manual']}, Quick {limits['Quick']}, Auto {limits['Auto']}, "
      f"Autosave {interval:g} s == Defaults  OK")

# --- 2) Nur geaenderte Schluessel, Ganzzahlen, {bpatch} ------------------
text = build_patches(gd, Settings(manual_save_slots=200, quick_save_slots=10))[SL]
assert "DefaultConfig : struct.begin {bpatch}" in text, text
assert "SavesLimit : struct.begin {bpatch}" in text, text
assert "Manual = 200" in text and "Quick = 10" in text, text
assert "Auto" not in text, "Auto geschrieben, obwohl auf Vanilla"
assert text.count("struct.end") == 2, text
text = build_patches(gd, Settings(autosave_interval_min=5))[AS]
assert "DefaultConfig : struct.begin {bpatch}" in text and "AutoSaveIntervalTime = 300" in text, text
text = build_patches(gd, Settings(autosave_interval_min=2.5))[AS]
assert "AutoSaveIntervalTime = 150" in text, text
print("Patches: SavesLimit nur Manual+Quick, Autosave 5 min -> 300 s  OK")

# --- 3) Neutral + Tweak-Zeilen --------------------------------------------
neutral = build_patches(gd, Settings())
assert SL not in neutral and AS not in neutral
lines = summarize(Settings(manual_save_slots=200, quick_save_slots=10,
                           auto_save_slots=20, autosave_interval_min=5))
for needle in ("Manual save slots 200", "Quick save slots 10", "Autosave slots 20",
               "Autosave every 5 min"):
    assert any(needle in ln for ln in lines), (needle, lines)
print("Neutral leer, 4 Tweak-Zeilen  OK")

print("\nSPEICHER-TEST OK")
