"""Farbdesigns in Fraktionsfarben (1.29.0, s2tweaker/theme.py).

Der Wunsch kam vom Besitzer: "verschiedene Designs in den Farben der
Fraktionen im spiel wir koennen standart ja lassen das was wir jetzt haben
und dann bekommen die Designs noch irgendwo knoepfe".

Was hier festgehalten wird — jeder Punkt hat beim Bauen einmal WEHGETAN:

* `theme.snapshot()` muss NACH `set_default_color_theme` laufen. Beim ersten
  Anlauf lief es beim Import und hielt die Farben des falschen Themas fest;
  der Umfaerber verglich dann mit Farben, die im Fenster nirgends vorkamen,
  und traf keinen einzigen Knopf.
* Jede Rolle braucht ihren eigenen Ton. Die erste Fassung war eine reine
  Farbtabelle "alt -> neu"; benutzt ein Design denselben Ton fuer Knopf,
  Regler und Tab, laesst sich beim ZURUECK-Schalten nicht mehr sagen, welcher
  Standardwert gemeint war — Regler kamen mit der Knopffarbe zurueck.
* Gruen und Rot duerfen NIE mitfaerben: Confirm, Oodle-Ampel,
  Mausrad-Schalter und "Remove from ~mods" bedeuten etwas.

Wie immer: SETTINGS_FILE umbiegen, nie _on_close/_save_ui_settings rufen.
"""
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

# --- 1) Paletten sind vollstaendig und in sich eindeutig -----------------
assert theme.names()[0] == theme.DEFAULT_NAME, theme.names()
assert len(theme.names()) >= 6, theme.names()
for name in theme.names():
    pal = theme.get(name)
    for role in ROLES:
        assert role in pal, f"{name}: {role} fehlt"
        assert pal[role], f"{name}: {role} leer"
    assert pal.get("note"), f"{name}: Beschreibung fehlt"
    # DIE zentrale Bedingung: teilen sich mehrere Rollen dasselbe Farbfeld
    # derselben Widget-Klasse, muessen ihre Farben verschieden sein - sonst
    # ist beim Zurueckschalten nicht entscheidbar, welche Rolle gemeint war
    # (die erste Fassung brachte so die Knopffarbe auf die Regler).
    for (klass, attr), roles in theme._ROLES.items():
        if len(roles) < 2:
            continue
        seen = [str(pal[r]) for r in roles]
        assert len(set(seen)) == len(seen), f"{name}: {klass}.{attr} {roles} {seen}"
print(f"{len(theme.names())} Designs, alle Rollen belegt und unterscheidbar  OK")

# Der Standard fuehrt exakt auf die Werkseinstellung zurueck
factory = dict(theme._FACTORY)
assert factory, "snapshot() wurde nie gerufen"
for role, value in factory.items():
    assert theme.get(theme.DEFAULT_NAME)[role] == value, role
print("Default == Werkseinstellung des customtkinter-Themas  OK")

# --- 2) Umschalten im echten Fenster ------------------------------------
app = gui.App()
app.update()
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
# Im Standard-Design sind Knopffarbe (blau) und Hervorhebung (bernstein)
# ABSICHTLICH verschieden - genau daran ist die erste Fassung gescheitert.
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
print("Duty: Knoepfe, Regler, aktiver Tab und Akzent umgestellt  OK")

# Ampeln unberuehrt - in JEDEM Design
for name in theme.names():
    app._set_theme(name)
    for key, want in ampeln.items():
        btn = {"confirm": app.btn_confirm, "oodle": app.btn_oodle,
               "wheel": app.btn_scroll, "remove": app.btn_remove}[key]
        assert str(btn.cget("fg_color")) == str(want), f"{name}: {key} verfaerbt"
print("Confirm, Oodle, Mausrad und Remove bleiben in allen Designs gleich  OK")

# --- 3) Hin und zurueck ist verlustfrei ----------------------------------
for name in theme.names():
    app._set_theme(name)
    app._set_theme(theme.DEFAULT_NAME)
    assert str(app.btn_build.cget("fg_color")) == str(start["button"]), name
    assert str(row.slider.cget("button_color")) == str(start["bright"]), name
    assert str(row.slider.cget("progress_color")) == str(start["progress"]), name
    assert str(app.tabs._buttons["Player"].cget("fg_color")) == str(start["tab"]), name
    assert str(app.cget("fg_color")) == str(start["base"]), name
    assert gui.ACCENT == start["accent"], name
print("Jedes Design fuehrt verlustfrei auf Default zurueck  OK")

# --- 4) Spaeter gebaute Regler bekommen die Design-Farben ---------------
app._set_theme("Monolith")
late = gui.SliderRow(row.row.master, "spaet", 0, 10, 1, 5, gui.fmt_int)
mono = theme.get("Monolith")
assert str(late.slider.cget("button_color")) == str(mono["bright"]), \
    late.slider.cget("button_color")
late.row.destroy()
print("Erst spaeter gebaute Regler (Baeume) kommen schon im Design  OK")

# --- 5) Ein Design aendert NICHTS am gebauten Mod ------------------------
before = app._ui_state()
app._set_theme("Freedom")
assert app._ui_state() == before, "Design darf keine Reglerwerte anfassen"
print("Reglerzustand vom Design unberuehrt  OK")

# --- 6) Die Wahl wird gemerkt (settings.json, NICHT im Preset) ----------
assert "theme" not in before, "Design gehoert nicht in Presets"
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
app2._set_theme(theme.DEFAULT_NAME)          # Prozess sauber hinterlassen
try:
    app2.destroy()
except Exception:
    pass
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("Gemerktes Design wird beim Start wieder gesetzt  OK")

# --- 7) Bestaetigen-Knopf: orange bis gedrueckt, danach gruen ------------
# Besitzer: "Orange pulsierend solange nicht gedrueckt danach so wie jetzt
# gruen". Der Puls laeuft ueber den RAND, die Flaeche bleibt orange - sonst
# waere die Ampelfarbe des Knopfes nicht mehr eindeutig.
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
assert str(app3.btn_confirm.cget("fg_color")) == theme.ATTENTION, "Flaeche pulst"
app3.gd = GameData(VANILLA)
for _ in range(20):
    app3.update()
    time.sleep(0.05)
assert str(app3.btn_confirm.cget("fg_color")) == theme.SUCCESS, \
    app3.btn_confirm.cget("fg_color")
assert str(app3.btn_confirm.cget("border_color")) == theme.SUCCESS_BORDER
print("Confirm: orange pulsierend, nach dem Laden gruen und ruhig  OK")

# --- 8) Standard heisst "Standard" und zeigt seinen Namen ----------------
assert theme.DEFAULT_NAME == "Standard", theme.DEFAULT_NAME
assert theme.resolve("Default") == "Standard", "alte Wahl muss weiter greifen"
assert theme.resolve("gibtsnicht") == "Standard"
assert "STANDARD" in app3.theme_mark.cget("text"), app3.theme_mark.cget("text")
app3._set_theme("Duty")
assert "DUTY" in app3.theme_mark.cget("text"), app3.theme_mark.cget("text")
try:
    app3.destroy()
except Exception:
    pass
print("Standard heisst Standard und steht wie die anderen in der Fusszeile  OK")

print("\nDESIGN-TEST OK")
