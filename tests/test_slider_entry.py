"""Check exact vanilla slider positions and independent numeric-entry values.

Grid steps must divide both the range and vanilla offset. Typed values may
lie between rail steps and accept comma/period decimals. Use temporary settings."""
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

# --- 1) grid_steps: calculations without GUI ---
cases = [
    # (min, max, vanilla, desired step, expected grid spacing)
    (0.25, 4.0, 1.0, 0.1, 0.05),     # 37.5 steps would not align -> 0.05.
    (0.25, 10.0, 1.0, 0.1, 0.05),
    (0.25, 3.0, 1.0, 0.1, 0.05),
    (25.0, 500.0, 100.0, 10.0, 5.0),
    (25.0, 1000.0, 100.0, 10.0, 5.0),
    (0.0, 300.0, 100.0, 5.0, 5.0),   # Keep an already valid step grid unchanged.
    (1.0, 8.0, 1.0, 0.1, 0.1),       # Vanilla at the endpoint remains unchanged.
    (0.0, 100.0, 93.0, 1.0, 1.0),    # Irregular vanilla value, matching step size.
    (100.0, 2000.0, 100.0, 10.0, 10.0),
]
for lo, hi, default, step, want in cases:
    n = gui.grid_steps(lo, hi, default, step)
    got = (hi - lo) / n
    assert abs(got - want) < 1e-9, (lo, hi, default, step, got, want)
    # Vanilla must land exactly on a rail step.
    k = (default - lo) / got
    assert abs(k - round(k)) < 1e-9, (lo, hi, default, got)
    assert got <= step + 1e-9, (got, step)   # Never coarser than requested.
print(f"grid_steps: {len(cases)} cases, vanilla always aligns with a step  OK")

# Every real GUI slider must represent its default exactly.
app = gui.App()
app.gd = GameData(VANILLA)
app._set_body_state(True)
app.update()

missed = [(k, r.default, r.get()) for k, r in app.sliders.items()
          if abs(r.get() - r.default) > 1e-9]
assert not missed, f"{len(missed)} sliders cannot reach vanilla: {missed[:8]}"
# Verify rail reachability as well as arithmetic.
unreachable = []
for key, row in app.sliders.items():
    if row.log:
        continue
    row.slider.set(row.default)          # Snap the rail to its nearest step.
    if abs(float(row.slider.get()) - row.default) > 1e-9:
        unreachable.append(key)
    row.reset()
assert not unreachable, f"Vanilla value unreachable: {unreachable[:8]}"
print(f"{len(app.sliders)} sliders: exact vanilla value reachable with the mouse  OK")

# Untouched controls must remain neutral.
assert not build_patches(app.gd, app._collect())
print("Neutral GUI produces no patches  OK")

# Check numeric-entry decimals, bounds and invalid input.
row = app.sliders["pdmg"]                # x 0.25 .. 10, Vanilla x 1


def typed(r, text):
    r.entry.delete(0, "end")
    r.entry.insert(0, text)
    r._entry_apply()
    return r.get()


assert typed(row, "1,37") == 1.37, row.get()      # Comma
assert row.entry.get() == "1.37", row.entry.get()  # Displayed in normalized form.
assert typed(row, "2.5") == 2.5, row.get()        # Decimal point
assert typed(row, "x 3,25") == 3.25, row.get()    # Input including a unit.
assert typed(row, "999") == 10.0, row.get()       # Above maximum -> maximum.
assert typed(row, "0") == 0.25, row.get()         # Below minimum -> minimum.
assert typed(row, "quatsch") == 0.25, row.get()   # Invalid input: value remains unchanged.
assert row.entry.get() == "0.25", row.entry.get()
row.reset()
assert row.get() == 1.0 and row.entry.get() == "1"
print("Numeric entry: comma equals decimal point, clamping, invalid input fallback  OK")

# Intermediate typed values must reach generated patches.
row.set(1.37)
s = app._collect()
assert abs(s.player_damage_factor - 1.37) < 1e-9, s.player_damage_factor
assert build_patches(app.gd, s), "x1.37 must produce a patch"
row.reset()

# Percentage sliders preserve integer values.
pct = app.sliders["stealth_kill"]                 # 50..300 %, Vanilla 100
assert typed(pct, "137") == 137.0, pct.get()
assert "137 %" in pct.value_label.cget("text")
assert typed(pct, "137,6") == 138.0, pct.get()    # Integer grid.
pct.reset()

# Round exact halves upward; banker's rounding can collapse a change back to vanilla.
hour = app.sliders["npc_light_on"]                # 16..23 h, Vanilla 22
hour.set(22.5)
assert hour.get() == 23, hour.get()
assert typed(hour, "18,5") == 19, hour.get()
hour.reset()

# Logarithmic Max health slider preserves the exact typed value.
hp = app.sliders["hp"]
assert typed(hp, "4321") == 4321.0, hp.get()
hp.reset()
assert hp.get() == 100
print("Percentage, integer and logarithmic sliders accept typed values  OK")

# Numeric-entry changes must update the visual rail.
typed(row, "2,5")
assert abs(float(row.slider.get()) - 2.5) < 1e-9, row.slider.get()
typed(row, "1,37")           # Rail uses the nearest step for an intermediate value.
assert abs(float(row.slider.get()) - 1.35) < 1e-9, row.slider.get()
assert row.get() == 1.37, row.get()          # Reported value remains the exact accepted input.
row.reset()
assert abs(float(row.slider.get()) - 1.0) < 1e-9

# Entry display and enabled state must follow the slider.
row.slider.set(2.0)
row._on_rail()
assert row.entry.get() == "2", row.entry.get()
row.reset()
app._set_body_state(False)
assert str(row.entry.cget("state")) == "disabled"
app._set_body_state(True)
assert str(row.entry.cget("state")) == "normal"
row.set_locked(True)
assert str(row.entry.cget("state")) == "disabled"
row.set_locked(False)
assert str(row.entry.cget("state")) == "normal"
print("Entry follows slider, locks and unlocks with it  OK")

# Wheel adjustment starts off; enabling it binds slider-wheel handlers.
# Page scrolling remains available in both modes.
assert gui.SliderRow._wheel_enabled is False
assert str(app.btn_scroll.cget("fg_color")) == gui.BAD_RED
assert "scrolls only" in app.btn_scroll.cget("text")


def spin(r, times=3):
    for _ in range(times):
        r.slider._canvas.event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        app.update()


# Newly constructed lazy sliders inherit the disabled wheel mode.
late = gui.SliderRow(app.sliders["pdmg"].row.master, "spaet", 0, 10, 1, 5,
                     gui.fmt_int)
spin(late)
assert late.get() == 5, f"New row ignores initial state ({late.get()})"
app._toggle_wheel()
assert gui.SliderRow._wheel_enabled is True
assert str(app.btn_scroll.cget("fg_color")) == gui.OK_GREEN
assert "moves sliders" in app.btn_scroll.cget("text")
spin(late)
assert late.get() != 5, "After enabling, the new row must follow the setting too"
app._toggle_wheel()
assert str(app.btn_scroll.cget("fg_color")) == gui.BAD_RED
late.row.destroy()

# Check actual wheel events. When rail adjustment is off, SliderRow must
# forward page scrolling because CTkSlider blocks it by default.
app.geometry("1010x760")
app.update_idletasks()
app.update()
wheel_row = app.sliders["sp_regen"]              # Near the top of the Player tab.
page = wheel_row._scroll_frame()._parent_canvas


def wheel(times=5):
    for _ in range(times):
        wheel_row.slider._canvas.event_generate("<MouseWheel>", delta=-120,
                                                x=5, y=5)
        app.update()


v0, y0 = wheel_row.get(), page.yview()[0]
wheel()
assert wheel_row.get() == v0, f"Red: slider moves ({v0} -> {wheel_row.get()})"
assert page.yview()[0] > y0, "Red: page does not scroll"
app._toggle_wheel()                              # Green.
v1, y1 = wheel_row.get(), page.yview()[0]
wheel()
assert wheel_row.get() != v1, "Green: slider does not move"
app._toggle_wheel()                              # Return to the disabled wheel mode.
wheel_row.reset()
print("Mouse wheel: red = scroll page only, green = adjust slider  OK")

# Use consistent semantic colors across action buttons.
app._refresh_oodle_badge()
assert str(app.btn_confirm.cget("fg_color")) == gui.OK_GREEN
assert str(app.btn_oodle.cget("fg_color")) in (gui.OK_GREEN, gui.BAD_RED), \
    app.btn_oodle.cget("fg_color")
print("Confirm, Oodle and mouse-wheel indicators share green/red colors  OK")

try:
    app.destroy()
except Exception:
    pass
print("\nSLIDER GRID / NUMERIC ENTRY TEST PASSED")
