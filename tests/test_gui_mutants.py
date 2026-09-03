"""Mutants-Tab: Arten-Baum, Regen-Regler, Patch-Merge, Persistenz, Suche.

Der fuenfte Baum (Dropdown-Abloesung; mutant_overrides-Dict unveraendert,
alte Presets muessen weiterlaufen)."""
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

# --- 1) Baum-Aufbau + ehrliches Regler-Angebot je Art -------------------
assert len(app._im_species) >= 15, app._im_species
assert set(app._im_blocks) >= {"small", "medium", "humanoid", "large"}
assert app.mutant_overrides == {}, f"Phantom: {app.mutant_overrides}"
assert "damage" not in app._im_params["Poltergeist"], "Poltergeist wirkt indirekt"
assert "damage" not in app._im_params["Rat"], "Rat wirkt indirekt"
assert set(app._im_params["Bloodsucker"]) == {"hp", "speed", "damage", "regen"}
assert "regen" in app._im_params["Poltergeist"]
n_regen_species = sum(1 for p in app._im_params.values() if "regen" in p)
print(f"Baum: {len(app._im_blocks)} Bloecke, {len(app._im_species)} Arten, "
      f"{n_regen_species} mit Regen-Regler  OK")

# --- 2) Tab-Leiste passt beim 880-px-Minimum (12 Tabs) ------------------
app.update_idletasks()
# winfo_reqwidth liefert physische Pixel: bei 150 % Windows-Skalierung
# (Zayns PC, 03.09.) sind das 1238 px fuer dieselben ~825 Layout-Pixel.
# Darum auf 100 % normieren, sonst haengt das Ergebnis am Monitor.
seg = app.tabs._segmented_button
req = round(seg.winfo_reqwidth() / seg._get_widget_scaling())
assert req <= 860, f"Tab-Leiste {req}px - zu breit fuer das 880-px-Minimum"
names = list(app.tabs._name_list)
assert names.index("Mutants") == names.index("NPCs & AI") + 1
assert names[-1] == "Traders" and len(names) == 13, names
print(f"Tab-Leiste: {req}px bei 13 Tabs  OK")

# --- 3) Override setzen -> Patch mit VitalParams-MERGE ------------------
blk = app._im_blocks["humanoid"]
blk.expand()
app.update()
row = blk.rows["Bloodsucker"]
row.toggle()
app.update()
assert app.mutant_overrides == {}, "Aufklappen darf nichts speichern"
row.sliders["hp"].set(2.0)
row.sliders["regen"].set(0.0)
app.update()
assert app.mutant_overrides == {"Bloodsucker": {"hp": 2.0, "regen": 0.0}}
p = build_patches(gd, app._collect())
obj_key = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
text = p[obj_key]
m = re.search(r"^Bloodsucker : struct.begin \{bpatch\}\n(.*?)^struct.end",
              text, re.S | re.M)
assert m, "Bloodsucker-Prototyp fehlt im Patch"
block = m.group(1)
assert block.count("VitalParams") == 1, "VitalParams muss EIN Knoten sein"
assert "MaxHP" in block and "RegenHP = 0" in block, block
vanilla_hp = gd.mutants()["Bloodsucker"]
hp_m = re.search(r"MaxHP = ([^\s;]+)", block)
assert abs(float(hp_m.group(1)) - vanilla_hp * 2) < 1e-6, hp_m.group(1)
print("Bloodsucker hp x2 + regen x0: EIN VitalParams-Knoten, Werte exakt  OK")

# --- 4) Globaler Regen-Regler x0 trifft alle Regen-Prototypen -----------
app._reset_all()
app.update()
app.sliders["mut_regen"].set(0)
app.update()
p = build_patches(gd, app._collect())
text = p[obj_key]
n_zero = text.count("RegenHP = 0")
assert n_zero == len(gd.mutant_regens()), (n_zero, len(gd.mutant_regens()))
assert any("Mutant health regen" in line for line in summarize(app._collect()))
print(f"Global regen x0: {n_zero} Prototypen auf 0  OK")

# --- 5) Persistenz-Roundtrip (JSON) inkl. regen; alte Presets laufen ----
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
# Preset aus Dropdown-Zeiten (nur hp/speed/damage) bleibt gueltig,
# Unbekanntes fliegt beim Populate raus
app._reset_all()
app._apply_ui_state({"mutant_overrides": {
    "Boar": {"hp": 2.0}, "Gibtsnicht": {"hp": 3.0},
    "Poltergeist": {"damage": 2.0}}})
app._im_populate()
app.update()
assert app.mutant_overrides == {"Boar": {"hp": 2.0}}, app.mutant_overrides
print("Persistenz + Alt-Preset-Migration  OK")

# --- 6) Suche + Changed-only --------------------------------------------
hits = app._im_filter("bloodsucker")
assert hits > 0
app._im_filter("")
blk = app._im_blocks["medium"]
blk.expand()
app.update()
app._apply_changed_only()
assert blk._hitset == {"Boar"}, blk._hitset
print(f"Suche ({hits} Treffer) + Changed-only  OK")

app.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("\nMUTANTS-TEST OK")
