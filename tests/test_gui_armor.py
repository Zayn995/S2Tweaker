"""Armor-Baum-Test: Patchlogik, GUI-Baum, Suche, Preset-Rundlauf."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
# Frisch starten: eine liegengebliebene Datei (z.B. von einem frueheren
# Agenten-Lauf) wuerde den Neutral-Check faelschlich ausloesen.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize, armor_label,
                              ARMOR_PARAMS)
from s2tweaker.cfgparse import parse

gd = GameData(VANILLA)

# --- 1) Patchlogik: Override ERSETZT global ------------------------------
armors = gd.player_armors()
sid = "Exoskeleton_Dolg_Armor"
assert sid in armors, sorted(armors)[:5]
slot, prot = armors[sid]
print(f"Testobjekt: {armor_label(sid)} ({slot}), vanilla={prot}")

# Nur Override, kein Global
p = build_patches(gd, Settings(armor_overrides={sid: {"strike": 2.0}}))
key = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
assert key in p, list(p)
tree = parse(p[key])
assert sid in tree.children, "Struct fehlt"
val = float(tree.children[sid].children["Protection"].values["Strike"])
assert abs(val - prot["Strike"] * 2.0) < 1e-6, (val, prot["Strike"])
assert len(tree.children) == 1, f"nur {sid} erwartet: {list(tree.children)[:5]}"
print(f"Override allein: Strike {prot['Strike']:g} -> {val:g}  OK")

# Global x3 + Override x2: Override gewinnt an DIESER Ruestung, Rest x3
p = build_patches(gd, Settings(armor_strike_factor=3.0,
                               armor_overrides={sid: {"strike": 2.0}}))
tree = parse(p[key])
val = float(tree.children[sid].children["Protection"].values["Strike"])
assert abs(val - prot["Strike"] * 2.0) < 1e-6, "Override ersetzt nicht"
other = "SEVA_Neutral_Armor"
oprot = armors[other][1]
oval = float(tree.children[other].children["Protection"].values["Strike"])
assert abs(oval - oprot["Strike"] * 3.0) < 1e-6, "Global wirkt nicht auf Rest"
print(f"Kaskade: {sid} x2 (ersetzt), {other} x3 (global)  OK")

# Override auf Schutzart, die es an der Ruestung nicht gibt -> kein Patch
no_psy = next(s for s, (_sl, v) in sorted(armors.items()) if "PSY" not in v)
p = build_patches(gd, Settings(armor_overrides={no_psy: {"psy": 3.0}}))
assert key not in p or no_psy not in parse(p[key]).children, \
    f"{no_psy} hat kein PSY, darf keinen Patch bekommen"
print(f"{armor_label(no_psy)}: psy-Override auf Vanilla-0 -> kein Patch  OK")

# summarize
lines = summarize(Settings(armor_overrides={sid: {"strike": 2.0, "burn": 0.5}}))
al = [l for l in lines if l.startswith("Armor ")]
print("summarize:", al)
assert len(al) == 2 and "Exoskeleton (Duty)" in al[0]

# --- 2) GUI --------------------------------------------------------------
app = gui.App()
app.gd = gd
app._set_body_state(True)
app._ir_populate()
app.update()
assert "Armor" in app.tabs._tab_dict, list(app.tabs._tab_dict)
assert len(app._ir_blocks) == 2, list(app._ir_blocks)
body_block = app._ir_blocks["Body"]
head_block = app._ir_blocks["Head"]
print(f"Baum: Body {len(body_block.sids)}, Head {len(head_block.sids)}")
assert len(body_block.sids) == 42 and len(head_block.sids) == 10

# Aufklappen + Override setzen wie ein Nutzer
body_block.expand()
app.update()
row = body_block.rows[sid]
row.build()
app.update()
assert set(row.sliders) == set(row.params)
row.sliders["strike"].set(2.0)
app.update()
assert app.armor_overrides == {sid: {"strike": 2.0}}, app.armor_overrides
assert "1 of 6 factors changed" in row.btn.cget("text")
assert "1 of 42 overridden" in body_block.btn.cget("text")
assert "Exoskeleton (Duty)" in app.ir_info.cget("text")
print("Baum-Interaktion: Override, Marker, Info-Zeile  OK")

# Aufklappen darf gespeicherte Werte NICHT loeschen (die alte Baum-Falle)
app.armor_overrides["SEVA_Neutral_Armor"] = {"burn": 0.5}
seva = body_block.rows["SEVA_Neutral_Armor"]
seva.build()
app.update()
assert app.armor_overrides.get("SEVA_Neutral_Armor") == {"burn": 0.5}, \
    "build() hat den gespeicherten Override geloescht!"
assert abs(seva.sliders["burn"].get() - 0.5) < 1e-9
print("Lazy-Build loescht keine gespeicherten Overrides  OK")

# _collect + Patch aus der GUI
s = app._collect()
assert s.armor_overrides[sid] == {"strike": 2.0}
out = build_patches(gd, s)
assert key in out
print("collect -> build  OK")

# Suche: "seva" findet und klappt auf; Status nennt den Armor-Tab
app.search_entry.insert(0, "seva")
app._apply_filter()
t0 = time.time()
while time.time() - t0 < 0.6:
    app.update()
    time.sleep(0.02)
assert "Armor (" in app.status.cget("text"), app.status.cget("text")
app.search_entry.delete(0, "end")
app._apply_filter()
app.update()
print("Suche: SEVA -> Armor-Tab gemeldet  OK")

# Preset-Rundlauf — wie im echten Ablauf ueber JSON (Presets/settings.json
# serialisieren sofort; _ui_state() selbst liefert lebende Referenzen)
import json
state = json.loads(json.dumps(app._ui_state()))
assert state["armor_overrides"] == app.armor_overrides
app._reset_all()
app.update()
assert not app.armor_overrides
app._apply_ui_state(state)
app.update()
assert app.armor_overrides.get(sid) == {"strike": 2.0}
print("Preset-Rundlauf inkl. Reset  OK")

# Verwaisten Override raeumt _ir_populate ab
app.armor_overrides["Gibt_Es_Nicht_Armor"] = {"strike": 2.0}
app._ir_populate()
assert "Gibt_Es_Nicht_Armor" not in app.armor_overrides
print("Verwaiste Overrides bereinigt  OK")

app.destroy()
print("\nARMOR-TEST OK")
