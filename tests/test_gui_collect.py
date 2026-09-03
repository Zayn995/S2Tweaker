"""GUI-Test: jeder feste Regler und jede Checkbox kommt in _collect() an.

Hintergrund (Nexus-Bug, max25091997, 02.09.2026): "Repeatable quest
cooldown" stand in der GUI, aber _collect() las den Regler nie aus - der
Wert blieb Vanilla, es gab weder Patch noch Zeile in der Tweak-Liste.
Alle anderen Suiten bauen Settings direkt und konnten das nicht sehen.
Hier wird jeder Regler einzeln verstellt und geprueft, dass sich das
Settings-Feld aus SLIDER_FIELDS/CHECK_FIELDS mitbewegt. Braucht keine
Spieldaten.

Wie immer: SETTINGS_FILE umbiegen, nie _on_close/_save_ui_settings rufen.
"""
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

# --- 1) Neutralzustand == Settings()-Defaults ---------------------------
base = app._collect()
default = Settings()
off = [(k, f, getattr(base, f), getattr(default, f))
       for k, f in SLIDER_FIELDS.items()
       if abs(float(getattr(base, f)) - float(getattr(default, f))) > 1e-9]
assert not off, f"Regler-Default weicht vom Settings-Default ab: {off}"
off_c = [(k, f) for k, f in CHECK_FIELDS.items()
         if bool(getattr(base, f)) != bool(getattr(default, f))]
assert not off_c, f"Checkbox-Default weicht ab: {off_c}"
print(f"Neutral: {len(SLIDER_FIELDS)} Regler + {len(CHECK_FIELDS)} "
      "Checkboxen auf Settings-Default  OK")

# --- 2) Jeder Regler bewegt sein Settings-Feld --------------------------
dead = []
for key, field in SLIDER_FIELDS.items():
    row = app.sliders[key]
    lo, hi = row.lo, row.hi          # Wert-Einheiten, auch bei Log-Reglern
    target = hi if abs(row.default - hi) > 1e-9 else lo
    row.set(target)
    moved = app._collect()
    if abs(float(getattr(moved, field)) - float(getattr(base, field))) < 1e-9:
        dead.append(key)
    row.set(row.default)
assert not dead, f"Regler ohne Wirkung in _collect(): {dead}"
print(f"Alle {len(SLIDER_FIELDS)} Regler erreichen _collect()  OK")

dead_c = []
for key, field in CHECK_FIELDS.items():
    box = app.checks[key]
    box.select()
    if not getattr(app._collect(), field):
        dead_c.append(key)
    box.deselect()
assert not dead_c, f"Checkboxen ohne Wirkung in _collect(): {dead_c}"
print(f"Alle {len(CHECK_FIELDS)} Checkboxen erreichen _collect()  OK")

# --- 3) Der konkrete Nexus-Fall: Quest-Cooldown 0 % / 400 % ------------
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
print("Quest-Cooldown 0 % -> x0 in Settings + Tweak-Liste, 400 % -> x4  OK")

try:
    app.destroy()
except Exception:
    pass
print("\nGUI-COLLECT-TEST OK")
