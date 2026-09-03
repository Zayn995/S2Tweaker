"""Logarithmischer "Max health"-Regler (GitHub Issue #4, NooB9496, 03.09.2026).

Der Regler geht jetzt von 50 bis 100000 auf einer log10-Schiene; get()/set()
sprechen weiter Werte (3 signifikante Stellen), Persistenz/Presets/Import
merken davon nichts. Prueft Mapping, Randfaelle, Roundtrip ueber
_ui_state/_apply_ui_state und den erzeugten Patch.

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
from s2tweaker.tweaks import build_patches, summarize

app = gui.App()
app.gd = GameData(VANILLA)
app.update()
hp = app.sliders["hp"]

# --- 1) Der HP-Regler ist log, alle anderen linear; lo/hi in Werten -----
assert hp.log and hp.lo == 50 and hp.hi == 100000, (hp.log, hp.lo, hp.hi)
others = [k for k, r in app.sliders.items() if r.log and k != "hp"]
assert not others, others
assert app.sliders["sp"].lo == 50 and app.sliders["sp"].hi == 1000
assert all(hasattr(r, "lo") and hasattr(r, "hi") for r in app.sliders.values())
print("HP-Regler log 50..100000, Rest linear, lo/hi ueberall  OK")

# --- 2) Mapping: set(x) -> get() == x fuer 3-stellige Werte, Clamp ------
for value in (50, 100, 250, 999, 1000, 4560, 25000, 100000):
    hp.set(value)
    assert abs(hp.get() - value) < 1e-9, (value, hp.get())
hp.set(99999)
assert hp.get() == 100000, hp.get()          # 3 signifikante Stellen
hp.set(20)
assert hp.get() == 50, hp.get()              # unter Minimum -> Minimum
hp.set(500000)
assert hp.get() == 100000, hp.get()          # ueber Maximum -> Maximum
hp.reset()
assert hp.get() == 100 and "(vanilla)" in hp.value_label.cget("text")
print("Mapping exakt (100/250/999/1000/4560/25000/100000), Clamp, Reset  OK")

# --- 3) Roundtrip ueber Preset-Zustand + Patch -------------------------
hp.set(100000)
state = app._ui_state()
assert state["sliders"]["hp"] == 100000, state["sliders"]["hp"]
hp.reset()
app._apply_ui_state(state)
assert hp.get() == 100000
s = app._collect()
assert s.max_hp == 100000
assert any("Max health 100000" in line for line in summarize(s))
p = build_patches(app.gd, s)
key = [k for k in p if "ObjPrototypes" in k]
assert key, list(p)
assert "MaxHP = 100000" in p[key[0]], p[key[0]][:300]
hp.reset()
assert not build_patches(app.gd, app._collect())
print("Roundtrip Preset -> Regler -> Settings -> Patch (MaxHP = 100000)  OK")

try:
    app.destroy()
except Exception:
    pass
print("\nLOG-SLIDER-TEST OK")
