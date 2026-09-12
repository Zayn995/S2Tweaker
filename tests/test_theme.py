"""Check theme completeness, role-based restoration and fixed system colors.

Capture defaults after selecting the CTk theme. Verify existing and lazy
widgets using temporary settings."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import gui, theme
from s2tweaker.gamedata import GameData
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")
gui.SETTINGS_FILE = SCRATCH / "throwaway_theme_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

ROLES = theme.ROLES

# Check complete, unambiguous palette roles.
assert theme.names()[0] == theme.DEFAULT_NAME, theme.names()
assert len(theme.names()) >= 6, theme.names()
for name in theme.names():
    pal = theme.get(name)
    for role in ROLES:
        assert role in pal, f"{name}: {role} missing"
        assert pal[role], f"{name}: {role} empty"
    assert pal.get("note"), f"{name}: description missing"
    # Roles competing for the same widget/color field need distinguishable colors
    # so restoration can identify the original role.
    for (klass, attr), roles in theme._ROLES.items():
        if len(roles) < 2:
            continue
        seen = [str(pal[r]) for r in roles]
        assert len(set(seen)) == len(seen), f"{name}: {klass}.{attr} {roles} {seen}"
print(f"{len(theme.names())} themes, all roles assigned and distinguishable  OK")

# Color selection must not change the common control geometry.
geometry = None
for name in theme.names():
    theme._theme_defaults(theme.get(name))
    current = {kind: {key: value for key, value in fields.items()
                      if key in ("corner_radius", "border_width", "button_length")}
               for kind, fields in theme.ctk.ThemeManager.theme.items()}
    assert geometry is None or current == geometry, name
    geometry = current
theme._theme_defaults(theme.get(theme.DEFAULT_NAME))
print("Every color palette uses the same control geometry  OK")

# --- 2) Switch themes in a real window ---
app = gui.App()
app.update()
app.tabs.set("Player")
row = app.sliders["pdmg"]
ampeln = {
    "confirm": app.btn_confirm.cget("fg_color"),
    "oodle": app.btn_oodle.cget("fg_color"),
    "wheel": app.btn_scroll.cget("fg_color"),
    "remove": app.btn_remove.cget("fg_color"),
}
start = {
    "button": app.btn_build.cget("fg_color"),
    "bright": row.slider.cget("button_color"),
    "progress": row.slider.cget("progress_color"),
    "tab": app.tabs._buttons["Player"].cget("fg_color"),
    "accent": gui.ACCENT,
    "base": app.cget("fg_color"),
}
# Standard button fills and highlights intentionally differ.
assert str(start["button"]) != str(gui.ACCENT)
assert app.theme_name == theme.DEFAULT_NAME

app._set_theme("Duty")
pal = theme.get("Duty")
assert app.theme_name == "Duty"
assert str(app.btn_build.cget("fg_color")) == str(pal["button"])
assert str(row.slider.cget("button_color")) == str(pal["bright"])
assert str(row.slider.cget("progress_color")) == str(pal["progress"])
assert str(app.tabs._buttons["Player"].cget("fg_color")) == str(pal["button"])
assert str(app.cget("fg_color")) == str(pal["base"])
assert gui.ACCENT == pal["accent"]
assert gui.PANEL == pal["panel"] and gui.PANEL2 == pal["panel2"]
print("Duty: buttons, sliders, active tab and accent changed  OK")

# Status indicators remain unchanged in EVERY theme.
for name in theme.names():
    app._set_theme(name)
    for key, want in ampeln.items():
        btn = {"confirm": app.btn_confirm, "oodle": app.btn_oodle,
               "wheel": app.btn_scroll, "remove": app.btn_remove}[key]
        assert str(btn.cget("fg_color")) == str(want), f"{name}: {key} changed color"
print("Confirm, Oodle, mouse wheel and Remove remain consistent across themes  OK")

# Switching themes and back must preserve original role colors.
for name in theme.names():
    app._set_theme(name)
    app._set_theme(theme.DEFAULT_NAME)
    assert str(app.btn_build.cget("fg_color")) == str(start["button"]), name
    assert str(row.slider.cget("button_color")) == str(start["bright"]), name
    assert str(row.slider.cget("progress_color")) == str(start["progress"]), name
    assert str(app.tabs._buttons["Player"].cget("fg_color")) == str(start["tab"]), name
    assert str(app.cget("fg_color")) == str(start["base"]), name
    assert gui.ACCENT == start["accent"], name
print("Every theme returns to Default without losing values  OK")

# New lazy sliders inherit the selected palette.
app._set_theme("Monolith")
late = gui.SliderRow(row.row.master, "spaet", 0, 10, 1, 5, gui.fmt_int)
mono = theme.get("Monolith")
assert str(late.slider.cget("button_color")) == str(mono["bright"]), \
    late.slider.cget("button_color")
late.row.destroy()
print("Lazily created tree sliders use the selected theme  OK")

# --- 5) A theme must not change the generated mod ---
before = app._ui_state()
app._set_theme("Freedom")
assert app._ui_state() == before, "Theme must not change slider values"
print("Slider state unaffected by theme  OK")

# Store theme preference in settings, not gameplay presets.
assert "theme" not in before, "Theme does not belong in presets"
app._set_theme("Ward")
gui.SETTINGS_FILE.write_text(json.dumps({"theme": "Ward"}), encoding="utf-8")
try:
    app.destroy()
except Exception:
    pass
app2 = gui.App()
app2.update()
assert app2.theme_name == "Ward", app2.theme_name
assert gui.ACCENT == theme.get("Ward")["accent"]
app2._set_theme(theme.DEFAULT_NAME)          # Leave the process in a clean state.
try:
    app2.destroy()
except Exception:
    pass
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("Remembered theme is restored at startup  OK")

# Check the load button's pending/ready indication and border pulse.
app3 = gui.App()
app3.update()
assert str(app3.btn_confirm.cget("fg_color")) == theme.ATTENTION, \
    app3.btn_confirm.cget("fg_color")
raender = set()
for _ in range(40):
    app3.update()
    time.sleep(0.05)
    raender.add(str(app3.btn_confirm.cget("border_color")))
assert raender == {theme.ATTENTION, theme.ATTENTION_BORDER}, raender
assert str(app3.btn_confirm.cget("fg_color")) == theme.ATTENTION, "Panel background pulses"
app3.gd = GameData(VANILLA)
for _ in range(20):
    app3.update()
    time.sleep(0.05)
assert str(app3.btn_confirm.cget("fg_color")) == theme.SUCCESS, \
    app3.btn_confirm.cget("fg_color")
assert str(app3.btn_confirm.cget("border_color")) == theme.SUCCESS_BORDER
print("Confirm: pulsing orange, steady green after loading  OK")

# Display the Standard theme name consistently.
assert theme.DEFAULT_NAME == "Standard", theme.DEFAULT_NAME
assert theme.resolve("Default") == "Standard", "Previous selection must remain effective"
assert theme.resolve("gibtsnicht") == "Standard"
assert "STANDARD" in app3.theme_mark.cget("text"), app3.theme_mark.cget("text")
app3._set_theme("Duty")
assert "DUTY" in app3.theme_mark.cget("text"), app3.theme_mark.cget("text")
try:
    app3.destroy()
except Exception:
    pass
print("Standard is named Standard and appears in the footer with the other themes  OK")

print("\nDESIGN-TEST OK")
