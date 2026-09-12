"""Avoid conflicts: locking, unlocking, restoration and persistence."""
import json
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
from s2tweaker.tweaks import build_patches

gd = GameData(VANILLA)

app = gui.App()
app.gd = gd
app._set_body_state(True)
app.update()

# Start with custom values and scan conflicts on three targets.
app.sliders["pdmg"].set(2.0)
app.sliders["npchp"].set(1.5)
app.checks["npc_no_heal"].select()
app.mod_conflicts = {"pdmg": ["OXA_Fake"], "npchp": ["OXA_Fake"],
                     "check:npc_no_heal": ["OXA_Fake"]}
app._apply_conflict_marks()
app.update()
assert not app.sliders["pdmg"].locked, "Without Avoid, nothing may be locked"

# Enabling Avoid-conflicts resets and locks affected controls.
app._set_avoid_mode(True)
app.update()
for key in ("pdmg", "npchp"):
    row = app.sliders[key]
    assert row.locked and abs(row.get() - row.default) < 1e-9, key
    assert str(row.slider.cget("state")) == "disabled", key
    assert "\U0001f513" in row.reset_btn.cget("text"), "Unlock button missing"
assert "npc_no_heal" in app._locked_checks
assert not bool(app.checks["npc_no_heal"].get())
assert str(app.checks["npc_no_heal"].cget("state")) == "disabled"
assert app.check_dots["npc_no_heal"].cget("text") == "\U0001f512"
assert not build_patches(gd, app._collect()), "Locked control must be neutral"
print(f"Avoid AN: {app._avoid_lock_count()} locked, neutral pak  OK")

# --- 2) Explicitly unlock a slider -> restore its value ---
app.sliders["pdmg"]._unlock()
app.update()
row = app.sliders["pdmg"]
assert not row.locked and abs(row.get() - 2.0) < 1e-9, row.get()
assert str(row.slider.cget("state")) == "normal"
assert "pdmg" in app.avoid_unlocked
assert app.sliders["npchp"].locked, "npchp must remain locked"
print("Unlock: pdmg unlocked, value 2.0 restored, npchp still locked  OK")

# --- 3) Rescan/reapply marks: explicit unlock survives ---
app._apply_conflict_marks()
app.update()
assert not app.sliders["pdmg"].locked and app.sliders["npchp"].locked
print("Rescan: explicit unlock survives  OK")

# Removing a conflict unlocks the control and restores its saved value.
app.mod_conflicts = {"pdmg": ["OXA_Fake"], "check:npc_no_heal": ["OXA_Fake"]}
app._apply_conflict_marks()
app.update()
assert not app.sliders["npchp"].locked, "Orphaned lock not released"
assert abs(app.sliders["npchp"].get() - 1.5) < 1e-9, "Value not restored"
app.mod_conflicts["npchp"] = ["OXA_Fake"]
app._apply_conflict_marks()
app.update()
assert app.sliders["npchp"].locked
print("Conflict gone -> unlocked -> conflict returns -> locked again  OK")

# Explicitly re-enabling the mode resets earlier unlock exceptions.
assert "pdmg" in app.avoid_unlocked and not app.sliders["pdmg"].locked
app._set_avoid_mode(True)
app.update()
assert not app.avoid_unlocked, "Enabling must clear explicit unlocks"
assert app.sliders["pdmg"].locked, "pdmg must be locked again"
app.sliders["pdmg"]._unlock()
app.update()
print("Re-enable locks everything; explicit unlock still works  OK")

# Global body enable/disable must preserve conflict locks.
app._set_body_state(False)
app._set_body_state(True)
app.update()
assert app.sliders["npchp"].locked
assert str(app.sliders["npchp"].slider.cget("state")) == "disabled"
assert str(app.checks["npc_no_heal"].cget("state")) == "disabled"
print("Body toggle preserves locks  OK")

# --- 5) Avoid OFF: unlock all and restore remembered values ---
app._set_avoid_mode(False)
app.update()
assert not app.sliders["npchp"].locked
assert abs(app.sliders["npchp"].get() - 1.5) < 1e-9, "npchp value lost"
assert bool(app.checks["npc_no_heal"].get()), "Checkbox value lost"
assert not app._locked_checks
print("Avoid OFF: values restored  OK")

# --- 6) Persist avoid and unlocked settings to settings.json ---
app.avoid_conflicts = True
app._save_ui_settings()
data = json.loads(gui.SETTINGS_FILE.read_text(encoding="utf-8"))
assert data["modscan_avoid"] is True
assert "pdmg" in data["modscan_unlocked"]
print("Persistence: modscan_avoid and modscan_unlocked saved  OK")

app.destroy()

# Restart restores settings; locks require a new scan.
app2 = gui.App()
app2.update()
assert app2.avoid_conflicts is True
assert "pdmg" in app2.avoid_unlocked
assert app2._avoid_lock_count() == 0, "Without a scan, nothing may be locked"
app2.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("Restart: setting loaded, no locks without a scan  OK")

print("\nAVOID-TEST OK")
