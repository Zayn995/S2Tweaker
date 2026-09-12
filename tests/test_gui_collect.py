"""Verify every fixed GUI control is collected into its Settings field.

This catches controls visible in the GUI but disconnected from export.
Use temporary settings paths and avoid persisting user state."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS
from s2tweaker.tweaks import Settings, summarize

app = gui.App()
app.update()

# --- 1) Neutral matches Settings() defaults ---
base = app._collect()
default = Settings()
off = [(k, f, getattr(base, f), getattr(default, f))
       for k, f in SLIDER_FIELDS.items()
       if abs(float(getattr(base, f)) - float(getattr(default, f))) > 1e-9]
assert not off, f"Slider default differs from Settings default: {off}"
off_c = [(k, f) for k, f in CHECK_FIELDS.items()
         if bool(getattr(base, f)) != bool(getattr(default, f))]
assert not off_c, f"Checkbox default differs: {off_c}"
print(f"Neutral: {len(SLIDER_FIELDS)} sliders + {len(CHECK_FIELDS)} "
      "Checkboxes use Settings defaults  OK")

# --- 2) Every slider changes its Settings field ---
dead = []
for key, field in SLIDER_FIELDS.items():
    row = app.sliders[key]
    lo, hi = row.lo, row.hi          # Use value units, including logarithmic controls.
    target = hi if abs(row.default - hi) > 1e-9 else lo
    row.set(target)
    moved = app._collect()
    if abs(float(getattr(moved, field)) - float(getattr(base, field))) < 1e-9:
        dead.append(key)
    row.set(row.default)
assert not dead, f"Sliders with no effect in _collect(): {dead}"
print(f"All {len(SLIDER_FIELDS)} sliders reach _collect()  OK")

dead_c = []
for key, field in CHECK_FIELDS.items():
    box = app.checks[key]
    box.select()
    if not getattr(app._collect(), field):
        dead_c.append(key)
    box.deselect()
assert not dead_c, f"Checkboxes with no effect in _collect(): {dead_c}"
print(f"All {len(CHECK_FIELDS)} checkboxes reach _collect()  OK")

# --- 3) Quest cooldown regression: 0% / 400% ---
row = app.sliders["rq_cooldown"]
row.set(0)
s = app._collect()
assert abs(s.repeatable_quest_factor) < 1e-9, s.repeatable_quest_factor
assert any("Repeatable quest cooldown" in line for line in summarize(s)), \
    summarize(s)
row.set(400)
assert abs(app._collect().repeatable_quest_factor - 4.0) < 1e-9
row.set(row.default)
assert not [line for line in summarize(app._collect())
            if "Repeatable quest cooldown" in line]
print("Quest cooldown 0% -> x0 in Settings and tweak list, 400% -> x4  OK")

try:
    app.destroy()
except Exception:
    pass
print("\nGUI-COLLECT-TEST OK")
