"""Check GUI scan-footprint coverage and markers with temporary settings."""
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
# Start with clean temporary state so leftovers cannot affect neutrality checks.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.gui import (SLIDER_FIELDS, CHECK_FIELDS, MARK_INFO, MARK_WARN,
                           footprint_settings)
from s2tweaker.tweaks import build_patches

app = gui.App()
app.gd = GameData(VANILLA)
app.update()

# Every fixed control must have appropriate footprint coverage.
missing = [k for k in app.sliders
           if k not in SLIDER_FIELDS and not k.startswith("wcat_")]
assert not missing, f"Sliders without SLIDER_FIELDS entries: {missing}"
missing_c = [k for k in app.checks if k not in CHECK_FIELDS]
assert not missing_c, f"Checkboxes without CHECK_FIELDS entries: {missing_c}"
stale = [k for k in SLIDER_FIELDS if k not in app.sliders]
assert not stale, f"SLIDER_FIELDS entries without sliders: {stale}"
print(f"Completeness: {len(SLIDER_FIELDS)} sliders + "
      f"{len(CHECK_FIELDS)} checkboxes covered")

# Require valid nonempty footprints. Loot lottery weights are separate from
# item mass; stat-bar synchronization has no independent patch footprint.
unscannable = {k for k in SLIDER_FIELDS if footprint_settings(k) is None}
unscannable |= {"check:" + k for k in CHECK_FIELDS
                if footprint_settings("check:" + k) is None}
# Input INI controls have no cfg footprint. Runtime relation changes are
# covered by the faction-pair tree footprint.
assert unscannable == {"check:stat_bars", "check:art_stat_labels",
                       "check:no_mouse_smooth", "check:no_view_accel",
                       "check:relations_runtime"}, unscannable
t0 = time.time()
empty = []
for key in [k for k in SLIDER_FIELDS if k not in unscannable] \
        + [c for c in ("check:" + k for k in CHECK_FIELDS)
           if c not in unscannable]:
    probes = footprint_settings(key)
    assert probes is not None, key
    pairs = set()
    for s in probes:
        pairs |= gui.modscan.pairs_from_patches(build_patches(app.gd, s))
    if not pairs:
        empty.append(key)
assert not empty, f"Empty footprints: {empty}"
print(f"All {len(SLIDER_FIELDS) + len(CHECK_FIELDS)} footprints "
      f"not empty ({time.time()-t0:.1f}s)")
assert footprint_settings("wcat_pistol_damage") is None    # Intentionally excluded.
assert footprint_settings("does_not_exist") is None

# --- 3) Slider markings ---
row = app.sliders["pdmg"]
row.set_conflict(["OXA_Overhaul"])
app.update()
assert row.dot is not None and row.dot.winfo_manager(), "Dot missing"
assert row.dot.cget("text_color") == MARK_INFO
assert "also changed by OXA_Overhaul" in row._dot_tip
row.set(2.0)          # Change slider -> warning severity.
app.update()
assert row.dot.cget("text_color") == MARK_WARN
assert "your value wins" in row._dot_tip
print("Slider dot: info -> warning when changed  OK")

# Resetting values must retain scan markers.
app.mod_conflicts = {"pdmg": ["OXA_Overhaul"], "check:npc_no_heal": ["OXA_Overhaul"]}
app.checks["npc_no_heal"].select()
app._update_check_dot("npc_no_heal")
app.update()
assert app.check_dots["npc_no_heal"].cget("text_color") == MARK_WARN
app._reset_all()
app.update()
assert row.dot.winfo_manager(), "Reset removed the dot"
assert row.dot.cget("text_color") == MARK_INFO, "Dot not reset to Info"
assert app.check_dots["npc_no_heal"].cget("text") == "\u25cf"
assert app.check_dots["npc_no_heal"].cget("text_color") == MARK_INFO
print("Reset all: dots remain, severity returns to Info  OK")

# Disabling marker display must clear its UI state.
app.mod_conflicts = {}
app._apply_conflict_marks()
app.update()
assert not row.dot.winfo_manager()
assert app.check_dots["npc_no_heal"].cget("text") == ""
print("A new scan without matches removes dots  OK")

# Check scan-button state and stored preferences.
assert hasattr(app, "btn_scan")
assert app.modscan_pref == "ask"
app.destroy()
print("\nGUI-MODSCAN-TEST OK")
