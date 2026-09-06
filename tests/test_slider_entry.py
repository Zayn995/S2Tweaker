"""Regler-Raster und Zahlenfelder (1.29.0).

Zwei Dinge, die am 06.09.2026 zusammen entstanden sind:

1. **Jeder Regler muss seinen Vanilla-Wert exakt treffen.** customtkinter
   kennt keine Schrittweite, sondern nur eine Anzahl Rasten; geht
   (max - min) / Schritt nicht glatt auf, liegt Vanilla ZWISCHEN zwei
   Rasten. Gemessen an dem Tag: 74 von 376 Reglern - ein frisch
   gestartetes Werkzeug haette Spielerschaden, alle Haendlerpreise und
   fuenf Faktoren jeder Waffenkategorie gepatcht, ohne dass jemand etwas
   angefasst hat. `gui.grid_steps()` verkleinert den gewuenschten Schritt
   darum auf den naechstkleineren, der Spanne UND Vanilla trifft.

2. **Zahlenfeld hinter jedem Regler** (Besitzer: "boxen hinter den slidern
   um custom zahlen einzugeben . oder , sollen dabei die gleiche Funktion
   haben"). Der Wert liegt seitdem in der Zeile selbst, nicht in der
   Schiene - nur so sind Werte zwischen zwei Rasten moeglich.

Wie immer: SETTINGS_FILE umbiegen, nie _on_close/_save_ui_settings rufen.
"""
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

# --- 1) grid_steps: Rechnung ohne GUI -----------------------------------
cases = [
    # (min, max, vanilla, Wunsch-Schritt, erwartete Rastweite)
    (0.25, 4.0, 1.0, 0.1, 0.05),     # 37,5 Rasten waeren krumm -> 0,05
    (0.25, 10.0, 1.0, 0.1, 0.05),
    (0.25, 3.0, 1.0, 0.1, 0.05),
    (25.0, 500.0, 100.0, 10.0, 5.0),
    (25.0, 1000.0, 100.0, 10.0, 5.0),
    (0.0, 300.0, 100.0, 5.0, 5.0),   # geht schon auf -> unveraendert
    (1.0, 8.0, 1.0, 0.1, 0.1),       # Vanilla am Rand -> unveraendert
    (0.0, 100.0, 93.0, 1.0, 1.0),    # krummer Vanilla-Wert, Schritt passt
    (100.0, 2000.0, 100.0, 10.0, 10.0),
]
for lo, hi, default, step, want in cases:
    n = gui.grid_steps(lo, hi, default, step)
    got = (hi - lo) / n
    assert abs(got - want) < 1e-9, (lo, hi, default, step, got, want)
    # Vanilla MUSS auf einer Raste liegen
    k = (default - lo) / got
    assert abs(k - round(k)) < 1e-9, (lo, hi, default, got)
    assert got <= step + 1e-9, (got, step)   # nie groeber als gewuenscht
print(f"grid_steps: {len(cases)} Faelle, Vanilla immer auf einer Raste  OK")

# --- 2) Alle Regler der echten GUI treffen ihren Vanilla-Wert ------------
app = gui.App()
app.gd = GameData(VANILLA)
app._set_body_state(True)
app.update()

missed = [(k, r.default, r.get()) for k, r in app.sliders.items()
          if abs(r.get() - r.default) > 1e-9]
assert not missed, f"{len(missed)} Regler verfehlen Vanilla: {missed[:8]}"
# und zwar auch ueber die Schiene erreichbar, nicht nur rechnerisch
unreachable = []
for key, row in app.sliders.items():
    if row.log:
        continue
    row.slider.set(row.default)          # rastet auf die naechste Raste
    if abs(float(row.slider.get()) - row.default) > 1e-9:
        unreachable.append(key)
    row.reset()
assert not unreachable, f"Vanilla nicht anfahrbar: {unreachable[:8]}"
print(f"{len(app.sliders)} Regler: Vanilla exakt und mit der Maus erreichbar  OK")

# Neutral bleibt neutral (der eigentliche Schaden des alten Rasters)
assert not build_patches(app.gd, app._collect())
print("Neutrale GUI erzeugt keinen einzigen Patch  OK")

# --- 3) Zahlenfeld: Punkt und Komma, Grenzen, Unsinn --------------------
row = app.sliders["pdmg"]                # x 0.25 .. 10, Vanilla x 1


def typed(r, text):
    r.entry.delete(0, "end")
    r.entry.insert(0, text)
    r._entry_apply()
    return r.get()


assert typed(row, "1,37") == 1.37, row.get()      # Komma
assert row.entry.get() == "1.37", row.entry.get()  # normalisiert angezeigt
assert typed(row, "2.5") == 2.5, row.get()        # Punkt
assert typed(row, "x 3,25") == 3.25, row.get()    # mit Einheit getippt
assert typed(row, "999") == 10.0, row.get()       # ueber Maximum -> Maximum
assert typed(row, "0") == 0.25, row.get()         # unter Minimum -> Minimum
assert typed(row, "quatsch") == 0.25, row.get()   # Unsinn: Wert bleibt
assert row.entry.get() == "0.25", row.entry.get()
row.reset()
assert row.get() == 1.0 and row.entry.get() == "1"
print("Zahlenfeld: Komma = Punkt, Klemmen, Unsinn faellt zurueck  OK")

# Zwischenwerte kommen wirklich im Patch an (der Sinn der Uebung)
row.set(1.37)
s = app._collect()
assert abs(s.player_damage_factor - 1.37) < 1e-9, s.player_damage_factor
assert build_patches(app.gd, s), "x 1,37 muss patchen"
row.reset()

# Prozent-Regler: ganze Zahlen bleiben ganze Zahlen
pct = app.sliders["stealth_kill"]                 # 50..300 %, Vanilla 100
assert typed(pct, "137") == 137.0, pct.get()
assert "137 %" in pct.value_label.cget("text")
assert typed(pct, "137,6") == 138.0, pct.get()    # ganzzahliges Raster
pct.reset()

# Genau .5 wird AUFgerundet - Pythons round() macht aus 22,5 eine 22, und
# ein Stunden-Regler stuende damit wieder auf Vanilla (fiel als
# "Blindgaenger" in test_slider_sweep auf).
hour = app.sliders["npc_light_on"]                # 16..23 h, Vanilla 22
hour.set(22.5)
assert hour.get() == 23, hour.get()
assert typed(hour, "18,5") == 19, hour.get()
hour.reset()

# Log-Regler (Max health): getippte Zahl bleibt exakt
hp = app.sliders["hp"]
assert typed(hp, "4321") == 4321.0, hp.get()
hp.reset()
assert hp.get() == 100
print("Prozent-, Ganzzahl- und Log-Regler nehmen eigene Zahlen an  OK")

# --- 4) Und umgekehrt: die Schiene folgt dem Feld ------------------------
# (Besitzer: "wenn es moeglich ist sollen die slider sich bewegen wenn man
# was in den Boxen aendert")
typed(row, "2,5")
assert abs(float(row.slider.get()) - 2.5) < 1e-9, row.slider.get()
typed(row, "1,37")           # Zwischenwert: Schiene geht auf die naechste
assert abs(float(row.slider.get()) - 1.35) < 1e-9, row.slider.get()
assert row.get() == 1.37, row.get()          # gemeldet wird die Zahl selbst
row.reset()
assert abs(float(row.slider.get()) - 1.0) < 1e-9

# --- 5) Feld folgt dem Regler und ist mitgesperrt ------------------------
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
print("Feld folgt der Schiene, wird mit gesperrt und wieder frei  OK")

# --- 6) Mausrad am Regler ------------------------------------------------
# Besitzer: "das mousewheel soll beim ersten start automatisch keine slider
# verschieben und rot sein. Wenn man es aktiviert geht beides scrollen und
# slider moven". Also: Start AUS/rot, ein Klick bindet das Rad an die
# Schienen und faerbt gruen. Das Blaettern der Seite haengt an einer
# bind_all-Bindung des Scroll-Rahmens und bleibt in beiden Zustaenden.
assert gui.SliderRow._wheel_enabled is False
assert str(app.btn_scroll.cget("fg_color")) == gui.BAD_RED
assert "scrolls only" in app.btn_scroll.cget("text")


def spin(r, times=3):
    for _ in range(times):
        r.slider._canvas.event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        app.update()


# Auch Regler, die ERST JETZT entstehen (aufgeklappter Baum), sind still
late = gui.SliderRow(app.sliders["pdmg"].row.master, "spaet", 0, 10, 1, 5,
                     gui.fmt_int)
spin(late)
assert late.get() == 5, f"neue Zeile ignoriert den Startzustand ({late.get()})"
app._toggle_wheel()
assert gui.SliderRow._wheel_enabled is True
assert str(app.btn_scroll.cget("fg_color")) == gui.OK_GREEN
assert "moves sliders" in app.btn_scroll.cget("text")
spin(late)
assert late.get() != 5, "nach dem Einschalten muss auch die neue Zeile folgen"
app._toggle_wheel()
assert str(app.btn_scroll.cget("fg_color")) == gui.BAD_RED
late.row.destroy()

# Und jetzt das eigentliche Verhalten, mit echten Rad-Ereignissen ueber
# einem Regler. WICHTIG: customtkinter laesst ueber einem CTkSlider von
# sich aus GAR NICHT blaettern (_check_if_valid_scroll liefert dort False),
# darum blaettert SliderRow im roten Zustand selbst - ohne das taete das
# Rad ueber einem Regler nichts mehr.
app.geometry("1010x760")
app.update_idletasks()
app.update()
wheel_row = app.sliders["sp_regen"]              # weit oben im Player-Tab
page = wheel_row._scroll_frame()._parent_canvas


def wheel(times=5):
    for _ in range(times):
        wheel_row.slider._canvas.event_generate("<MouseWheel>", delta=-120,
                                                x=5, y=5)
        app.update()


v0, y0 = wheel_row.get(), page.yview()[0]
wheel()
assert wheel_row.get() == v0, f"rot: Regler bewegt sich ({v0} -> {wheel_row.get()})"
assert page.yview()[0] > y0, "rot: Seite blaettert nicht"
app._toggle_wheel()                              # gruen
v1, y1 = wheel_row.get(), page.yview()[0]
wheel()
assert wheel_row.get() != v1, "gruen: Regler bewegt sich nicht"
app._toggle_wheel()                              # zurueck auf rot
wheel_row.reset()
print("Mausrad: rot = Seite blaettert und Regler still, gruen = Regler folgt  OK")

# --- 7) Eine Ampel-Farbe fuer alle Knoepfe -------------------------------
app._refresh_oodle_badge()
assert str(app.btn_confirm.cget("fg_color")) == gui.OK_GREEN
assert str(app.btn_oodle.cget("fg_color")) in (gui.OK_GREEN, gui.BAD_RED), \
    app.btn_oodle.cget("fg_color")
print("Confirm, Oodle und Mausrad teilen dasselbe Gruen/Rot  OK")

try:
    app.destroy()
except Exception:
    pass
print("\nREGLER-RASTER/ZAHLENFELD-TEST OK")
