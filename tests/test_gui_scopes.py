"""Upgrades tab scope tree: category buttons work after the first load.
Exercise expansion, overrides, locking, rebuild, clear-all and persistence."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData

gd = GameData(VANILLA)

app = gui.App()
app.update()
assert app._ia_state == "disabled", app._ia_state
app.gd = gd
# Match startup order: populate trees while the body is still disabled.
app._iw_populate()
app._ia_populate()
app._isc_populate()
app._ir_populate()
app._if_populate()
app._im_populate()
app._set_busy(False)
app._set_body_state(True)
app.update()

# --- 1) All five category buttons are enabled ---
btns = [w for w in app._scope_box.winfo_children() if isinstance(w, gui.ctk.CTkButton)]
assert len(btns) == 5, [b.cget("text") for b in btns]
bad = [(b.cget("text"), b.cget("state")) for b in btns if b.cget("state") != "normal"]
assert not bad, f"Category buttons locked: {bad}"
assert len(app._isc_btns) == 5 and set(app._isc_btns) == set(btns)
assert len(app._isc_rows) == 17, len(app._isc_rows)

# --- 2) Expand through button ---
four = next(b for b in btns if "4x scopes" in b.cget("text"))
four.invoke()
app.update()
assert four.cget("text").startswith("▾"), four.cget("text")
shown = [w for w in app._scope_box.winfo_children()
         if isinstance(w, gui.ctk.CTkFrame) and w.winfo_manager()]
assert len(shown) == 1, len(shown)
four.invoke()
app.update()
assert four.cget("text").startswith("▸"), four.cget("text")

# Store scope factors only when they differ from 1.0.
app._isc_rows["SVDM_Scope"]["zoom"].set(1.5)
app._isc_rows["SVDM_Scope"]["penalty"].set(0.5)
assert app.scope_overrides == {"SVDM_Scope": {"zoom": 1.5, "penalty": 0.5}}, app.scope_overrides
app._isc_rows["SVDM_Scope"]["zoom"].set(1.0)
assert app.scope_overrides == {"SVDM_Scope": {"penalty": 0.5}}, app.scope_overrides
assert "zoom" not in app._isc_rows["RU_ColimScope_2"], "Collimator has no zoom slider"

# Busy-state locking also applies to scope-category buttons.
app._set_body_state(False)
assert all(b.cget("state") == "disabled" for b in app._isc_btns)
assert app._isc_rows["SVDM_Scope"]["penalty"].slider.cget("state") == "disabled"
app._set_body_state(True)
assert all(b.cget("state") == "normal" for b in app._isc_btns)

# --- 5) Preset/manifest rebuild preserves overrides and replaces buttons ---
old_btns = list(app._isc_btns)
app._isc_populate()
app.update()
assert len(app._isc_btns) == 5 and not (set(app._isc_btns) & set(old_btns))
assert all(b.cget("state") == "normal" for b in app._isc_btns)
assert app.scope_overrides == {"SVDM_Scope": {"penalty": 0.5}}, app.scope_overrides
assert abs(app._isc_rows["SVDM_Scope"]["penalty"].get() - 0.5) < 1e-9

# --- 6) Clear all -----------------------------------------------------------
app._isc_clear_all()
assert app.scope_overrides == {}, app.scope_overrides
assert abs(app._isc_rows["SVDM_Scope"]["penalty"].get() - 1.0) < 1e-9

# Roundtrip scope overrides through UI state and Settings.
app._isc_rows["EN_X8Scope_1"]["zoom"].set(2.0)
state = app._ui_state()
assert state["scope_overrides"] == {"EN_X8Scope_1": {"zoom": 2.0}}, state["scope_overrides"]
s = app._collect()
assert s.scope_overrides == {"EN_X8Scope_1": {"zoom": 2.0}}, s.scope_overrides

app.destroy()
print("test_gui_scopes: OK")
