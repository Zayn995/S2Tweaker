"""GUI-Test des Mod-Scans: Vollstaendigkeit der Fussabdruecke + Markierungen.

Wie immer: SETTINGS_FILE umbiegen, nie _on_close/_save_ui_settings rufen.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
# Frisch starten: eine liegengebliebene Datei (z.B. von einem frueheren
# Agenten-Lauf) wuerde den Neutral-Check faelschlich ausloesen.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.gui import (SLIDER_FIELDS, CHECK_FIELDS, MARK_INFO, MARK_WARN,
                           footprint_settings)
from s2tweaker.tweaks import build_patches

app = gui.App()
app.gd = GameData(VANILLA)
app.update()

# --- 1) Vollstaendigkeit: jeder feste Regler hat einen Fussabdruck -------
missing = [k for k in app.sliders
           if k not in SLIDER_FIELDS and not k.startswith("wcat_")]
assert not missing, f"Regler ohne SLIDER_FIELDS-Eintrag: {missing}"
missing_c = [k for k in app.checks if k not in CHECK_FIELDS]
assert not missing_c, f"Checkboxen ohne CHECK_FIELDS-Eintrag: {missing_c}"
stale = [k for k in SLIDER_FIELDS if k not in app.sliders]
assert not stale, f"SLIDER_FIELDS-Eintraege ohne Regler: {stale}"
print(f"Vollstaendigkeit: {len(SLIDER_FIELDS)} Regler + "
      f"{len(CHECK_FIELDS)} Checkboxen abgedeckt")

# --- 2) Jeder Fussabdruck ist gueltig und NICHT leer ---------------------
# Bewusste Ausnahme: npc_gear patcht nur Weight-Blaetter, die der
# Scan-Vergleich absichtlich ausschliesst (Kollisions-Haertung) — der
# Regler ist deklariert unmarkierbar wie die Baum-Regler.
unscannable = {k for k in SLIDER_FIELDS if footprint_settings(k) is None}
assert unscannable == {"npc_gear"}, unscannable
t0 = time.time()
empty = []
for key in [k for k in SLIDER_FIELDS if k not in unscannable] \
        + ["check:" + k for k in CHECK_FIELDS]:
    probes = footprint_settings(key)
    assert probes is not None, key
    pairs = set()
    for s in probes:
        pairs |= gui.modscan.pairs_from_patches(build_patches(app.gd, s))
    if not pairs:
        empty.append(key)
assert not empty, f"Leere Fussabdruecke: {empty}"
print(f"Alle {len(SLIDER_FIELDS) + len(CHECK_FIELDS)} Fussabdruecke "
      f"nicht leer ({time.time()-t0:.1f}s)")
assert footprint_settings("wcat_pistol_damage") is None    # bewusst nicht
assert footprint_settings("does_not_exist") is None

# --- 3) Markierungen am Regler ------------------------------------------
row = app.sliders["pdmg"]
row.set_conflict(["OXA_Overhaul"])
app.update()
assert row.dot is not None and row.dot.winfo_manager(), "Punkt fehlt"
assert row.dot.cget("text_color") == MARK_INFO
assert "also changed by OXA_Overhaul" in row._dot_tip
row.set(2.0)          # Regler verstellen -> Warnstufe
app.update()
assert row.dot.cget("text_color") == MARK_WARN
assert "your value wins" in row._dot_tip
print("Slider-Punkt: info -> warn beim Verstellen  OK")

# --- 4) "Reset all to vanilla" loescht die Markierung NICHT --------------
app.mod_conflicts = {"pdmg": ["OXA_Overhaul"], "check:npc_no_heal": ["OXA_Overhaul"]}
app.checks["npc_no_heal"].select()
app._update_check_dot("npc_no_heal")
app.update()
assert app.check_dots["npc_no_heal"].cget("text_color") == MARK_WARN
app._reset_all()
app.update()
assert row.dot.winfo_manager(), "Reset hat den Punkt entfernt!"
assert row.dot.cget("text_color") == MARK_INFO, "Punkt nicht auf Info zurueck"
assert app.check_dots["npc_no_heal"].cget("text") == "\u25cf"
assert app.check_dots["npc_no_heal"].cget("text_color") == MARK_INFO
print("Reset all: Punkte bleiben, Stufe faellt auf Info zurueck  OK")

# --- 5) Abwaehlen der Markierung raeumt auf ------------------------------
app.mod_conflicts = {}
app._apply_conflict_marks()
app.update()
assert not row.dot.winfo_manager()
assert app.check_dots["npc_no_heal"].cget("text") == ""
print("Erneuter Scan ohne Treffer entfernt die Punkte  OK")

# --- 6) Scan-Knopf und Einstellung ---------------------------------------
assert hasattr(app, "btn_scan")
assert app.modscan_pref == "ask"
app.destroy()
print("\nGUI-MODSCAN-TEST OK")
