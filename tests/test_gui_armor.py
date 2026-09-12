"""Armor tree: patch logic, GUI tree, search and preset roundtrip."""
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
# Start with clean temporary state so leftovers cannot affect neutrality checks.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize, armor_label,
                              ARMOR_PARAMS)
from s2tweaker.cfgparse import parse

gd = GameData(VANILLA)

# --- 1) Patch logic: override replaces global ---
armors = gd.player_armors()
sid = "Exoskeleton_Dolg_Armor"
assert sid in armors, sorted(armors)[:5]
slot, prot = armors[sid]
print(f"Test object: {armor_label(sid)} ({slot}), vanilla={prot}")

# Individual override without a global factor.
p = build_patches(gd, Settings(armor_overrides={sid: {"strike": 2.0}}))
key = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
assert key in p, list(p)
tree = parse(p[key])
assert sid in tree.children, "Struct missing"
val = float(tree.children[sid].children["Protection"].values["Strike"])
assert abs(val - prot["Strike"] * 2.0) < 1e-6, (val, prot["Strike"])
assert len(tree.children) == 1, f"only {sid} expected: {list(tree.children)[:5]}"
print(f"Override alone: Strike {prot['Strike']:g} -> {val:g}  OK")

# Global x3 + override x2: this armor uses x2, others use x3.
p = build_patches(gd, Settings(armor_strike_factor=3.0,
                               armor_overrides={sid: {"strike": 2.0}}))
tree = parse(p[key])
val = float(tree.children[sid].children["Protection"].values["Strike"])
assert abs(val - prot["Strike"] * 2.0) < 1e-6, "Override does not replace value"
other = "SEVA_Neutral_Armor"
oprot = armors[other][1]
oval = float(tree.children[other].children["Protection"].values["Strike"])
assert abs(oval - oprot["Strike"] * 3.0) < 1e-6, "Global factor does not affect remaining items"
print(f"Cascade: {sid} x2 (replaced), {other} x3 (global)  OK")

# Unsupported armor protection must produce no patch.
no_psy = next(s for s, (_sl, v) in sorted(armors.items()) if "PSY" not in v)
p = build_patches(gd, Settings(armor_overrides={no_psy: {"psy": 3.0}}))
assert key not in p or no_psy not in parse(p[key]).children, \
    f"{no_psy} has no PSY protection and must not receive a patch"
print(f"{armor_label(no_psy)}: PSY override on vanilla zero -> no patch  OK")

# summarize
lines = summarize(Settings(armor_overrides={sid: {"strike": 2.0, "burn": 0.5}}))
al = [l for l in lines if l.startswith("Armor ")]
print("summarize:", al)
# Prefer the known armor display alias; retain SID-derived fallback.
assert len(al) == 2 and armor_label(sid) in al[0], (al, armor_label(sid))

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
print(f"Tree: Body {len(body_block.sids)}, Head {len(head_block.sids)}")
# Include base armor plus available edition items; missing DLC contributes zero.
n_dlc_body = sum(1 for _s, (slot, _v, _e) in gd.dlc_player_armors().items()
                 if slot == "Body")
n_dlc_head = len(gd.dlc_player_armors()) - n_dlc_body
assert len(body_block.sids) == 42 + n_dlc_body, (len(body_block.sids), n_dlc_body)
assert len(head_block.sids) == 10 + n_dlc_head, (len(head_block.sids), n_dlc_head)

# Expand and set an override through the UI.
body_block.expand()
app.update()
row = body_block.rows[sid]
row.build()
app.update()
assert set(row.sliders) == set(row.params)
row.sliders["strike"].set(2.0)
app.update()
assert app.armor_overrides == {sid: {"strike": 2.0}}, app.armor_overrides
assert "1 settings changed" in row.btn.cget("text")
assert (f"1 of {42 + n_dlc_body} overridden"
        in body_block.btn.cget("text")), body_block.btn.cget("text")
assert armor_label(sid) in app.ir_info.cget("text")
print("Tree interaction: override, marker, info line  OK")

# Expanding a row must not erase stored overrides.
app.armor_overrides["SEVA_Neutral_Armor"] = {"burn": 0.5}
seva = body_block.rows["SEVA_Neutral_Armor"]
seva.build()
app.update()
assert app.armor_overrides.get("SEVA_Neutral_Armor") == {"burn": 0.5}, \
    "build() deleted the saved override"
assert abs(seva.sliders["burn"].get() - 0.5) < 1e-9
print("Lazy build preserves saved overrides  OK")

# Collect GUI state and build its patch.
s = app._collect()
assert s.armor_overrides[sid] == {"strike": 2.0}
out = build_patches(gd, s)
assert key in out
print("collect -> build  OK")

# Search should reveal armor matches and identify the Armor tab.
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
print("Search: SEVA -> Armor tab reported  OK")

# Preset roundtrip through JSON, matching immediate serialization of
# presets/settings; _ui_state() itself returns live references.
import json
state = json.loads(json.dumps(app._ui_state()))
assert state["armor_overrides"] == app.armor_overrides
app._reset_all()
app.update()
assert not app.armor_overrides
app._apply_ui_state(state)
app.update()
assert app.armor_overrides.get(sid) == {"strike": 2.0}
print("Preset roundtrip including reset  OK")

# _ir_populate removes orphaned overrides.
app.armor_overrides["Gibt_Es_Nicht_Armor"] = {"strike": 2.0}
app._ir_populate()
assert "Gibt_Es_Nicht_Armor" not in app.armor_overrides
print("Orphaned overrides removed  OK")

app.destroy()
print("\nARMOR-TEST OK")
