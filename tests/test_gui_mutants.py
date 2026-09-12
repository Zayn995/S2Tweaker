"""Mutants tab: species tree, regeneration slider, patch merge, persistence, search.

The tree replaces the dropdown while preserving mutant_overrides and old presets."""
import json
import re
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
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)

app = gui.App()
app.gd = gd
app._im_populate()
app._set_body_state(True)
app.update()

# --- 1) Tree construction and supported sliders per species ---
assert len(app._im_species) >= 15, app._im_species
assert set(app._im_blocks) >= {"small", "medium", "humanoid", "large"}
assert app.mutant_overrides == {}, f"Phantom: {app.mutant_overrides}"
assert "damage" not in app._im_params["Poltergeist"], "Poltergeist uses indirect effects"
assert "damage" not in app._im_params["Rat"], "Rat uses indirect effects"
assert set(app._im_params["Bloodsucker"]) == {"hp", "speed", "damage", "regen", "protection"}
assert "regen" in app._im_params["Poltergeist"]
n_regen_species = sum(1 for p in app._im_params.values() if "regen" in p)
print(f"Tree: {len(app._im_blocks)} blocks, {len(app._im_species)} species, "
      f"{n_regen_species} with regeneration slider  OK")

# --- 2) Tab bar fits the 880-px minimum ---
app.update_idletasks()
# Normalize physical widget width by display scaling for monitor-independent checks.
bar = app.tabs._bar
req = round(bar.winfo_reqwidth() / app.tabs._get_widget_scaling())
assert req <= 860, f"Tab bar {req}px - too wide for the 880-px minimum"
names = list(app.tabs._name_list)
assert names.index("Mutants") == names.index("NPCs & AI") + 1
assert names[-1] == "Traders" and len(names) == 14, names
# Two tab rows keep full labels readable at minimum width.
rows = sorted({app.tabs._buttons[n].grid_info()["row"] for n in names})
assert rows == [0, 1], rows
app.geometry("880x600")
app.update_idletasks()
app.update()
font = app.tabs._font
for name in names:
    have = app.tabs._buttons[name].winfo_width()
    assert have >= font.measure(name), \
        f"Tab '{name}': {have}px for {font.measure(name)}px Text"
print(f"Tab bar: {req}px, 2 rows, all 14 names complete  OK")

# Verify mutant overrides merge within VitalParams.
blk = app._im_blocks["humanoid"]
blk.expand()
app.update()
row = blk.rows["Bloodsucker"]
row.toggle()
app.update()
assert app.mutant_overrides == {}, "Expanding must not save anything"
row.sliders["hp"].set(2.0)
row.sliders["regen"].set(0.0)
app.update()
assert app.mutant_overrides == {"Bloodsucker": {"hp": 2.0, "regen": 0.0}}
p = build_patches(gd, app._collect())
obj_key = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
text = p[obj_key]
m = re.search(r"^Bloodsucker : struct.begin \{bpatch\}\n(.*?)^struct.end",
              text, re.S | re.M)
assert m, "Bloodsucker prototype missing from patch"
block = m.group(1)
assert block.count("VitalParams") == 1, "VitalParams must be ONE node"
assert "MaxHP" in block and "RegenHP = 0" in block, block
vanilla_hp = gd.mutants()["Bloodsucker"]
hp_m = re.search(r"MaxHP = ([^\s;]+)", block)
assert abs(float(hp_m.group(1)) - vanilla_hp * 2) < 1e-6, hp_m.group(1)
print("Bloodsucker HP x2 + regeneration x0: ONE VitalParams node, exact values  OK")

# --- 4) Global regeneration x0 reaches all regeneration prototypes ---
app._reset_all()
app.update()
app.sliders["mut_regen"].set(0)
app.update()
p = build_patches(gd, app._collect())
text = p[obj_key]
n_zero = text.count("RegenHP = 0")
assert n_zero == len(gd.mutant_regens()), (n_zero, len(gd.mutant_regens()))
assert any("Mutant health regen" in line for line in summarize(app._collect()))
print(f"Global regen x0: {n_zero} prototypes set to zero  OK")

# --- 5) JSON persistence includes regeneration and supports old presets ---
app._reset_all()
blk = app._im_blocks["humanoid"]
blk.expand()
row = blk.rows["Bloodsucker"]
row.toggle()
row.sliders["speed"].set(1.5)
app.update()
state = json.loads(json.dumps(app._ui_state()))
app._reset_all()
app._apply_ui_state(state)
app.update()
assert app.mutant_overrides == {"Bloodsucker": {"speed": 1.5}}
# Retain old hp/speed/damage presets; discard unknown species during population.
app._reset_all()
app._apply_ui_state({"mutant_overrides": {
    "Boar": {"hp": 2.0}, "Gibtsnicht": {"hp": 3.0},
    "Poltergeist": {"damage": 2.0}}})
app._im_populate()
app.update()
assert app.mutant_overrides == {"Boar": {"hp": 2.0}}, app.mutant_overrides
print("Persistence and old preset migration  OK")

# --- 6) Search and Changed only ---
hits = app._im_filter("bloodsucker")
assert hits > 0
app._im_filter("")
blk = app._im_blocks["medium"]
blk.expand()
app.update()
app._apply_changed_only()
assert blk._hitset == {"Boar"}, blk._hitset
print(f"Suche ({hits} matches) and Changed only  OK")

app.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("\nMUTANTS-TEST OK")
