"""Check the logarithmic health rail, value mapping, bounds, presets and patches.

Use temporary settings; serialization still stores ordinary numeric values."""
import math
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

# Only health uses the logarithmic rail; bounds remain in value units.
assert hp.log and hp.lo == 50 and hp.hi == 100000, (hp.log, hp.lo, hp.hi)
others = [k for k, r in app.sliders.items() if r.log and k != "hp"]
assert not others, others
assert app.sliders["sp"].lo == 50 and app.sliders["sp"].hi == 1000
assert all(hasattr(r, "lo") and hasattr(r, "hi") for r in app.sliders.values())
print("HP slider logarithmic 50..100000, others linear, lo/hi defined throughout  OK")

# Check mapping and clamping of three-significant-digit values.
for value in (50, 100, 250, 999, 1000, 4560, 25000, 100000):
    hp.set(value)
    assert abs(hp.get() - value) < 1e-9, (value, hp.get())
hp.set(99999)
assert hp.get() == 99999, hp.get()           # Exact typed value from the numeric entry.
# Rail interaction rounds to three significant figures.
hp.slider.set(math.log10(99999))
hp._on_rail()
assert hp.get() == 100000, hp.get()
hp.set(20)
assert hp.get() == 50, hp.get()              # Below minimum -> minimum.
hp.set(500000)
assert hp.get() == 100000, hp.get()          # Above maximum -> maximum.
hp.reset()
assert hp.get() == 100 and "(vanilla)" in hp.value_label.cget("text")
print("Exact mapping (100/250/999/1000/4560/25000/100000), clamp, reset  OK")

# --- 3) Preset-state and patch roundtrip ---
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
print("Roundtrip preset -> slider -> Settings -> patch (MaxHP = 100000)  OK")

try:
    app.destroy()
except Exception:
    pass
print("\nLOG-SLIDER-TEST OK")
