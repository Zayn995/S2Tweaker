"""Manual GUI release smoke checks for weapon/ammunition trees, presets,
neutral output and loot controls."""
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
# Start with clean temporary state so leftovers cannot affect neutrality checks.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker import __version__
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import build_patches, summarize

app = gui.App()
app.gd = GameData(VANILLA)
app.update()
print("version:", __version__, "| window title:", app.title())

# --- Default state: nothing to patch ---
assert not build_patches(app.gd, app._collect()), "Neutral settings produce patches"
print("neutral -> nothing to patch  OK")

# --- Weapon tree ---
app._set_body_state(True)
app._iw_populate()
app.update()
cat = next(iter(app._iw_blocks)) if hasattr(app, "_iw_blocks") else None
print("weapon categories:", len(getattr(app, "_iw_blocks", {})))
app.weapon_overrides["GunAK74_ST"] = {"damage": 3.0}
s = app._collect()
line = [l for l in summarize(s) if "AK74" in l or "damage" in l.lower()]
print("weapon override summary:", line[:2])
out = build_patches(app.gd, s)
assert any("WeaponData" in k for k in out), list(out)
print("weapon override patches:", [k.split('/')[-1] for k in out])
app.weapon_overrides.clear()

# --- Ammunition tree ---------------------------------------------------------
app._ia_populate()
app.update()
kinds = app.gd.ammo_kinds()
print("ammo kinds:", len(kinds))
app.ammo_overrides["A545A"] = {"damage": 2.0}
s = app._collect()
print("ammo override summary:", [l for l in summarize(s) if "Ammo" in l][:2])
out = build_patches(app.gd, s)
assert any("ItemPrototypes" in k for k in out), list(out)
print("ammo override patches OK")

# A type with a vanilla value of zero must not produce an effective patch.
app.ammo_overrides.clear()
zero = [sid for sid in kinds
        if not float(app.gd.resolve(app.gd.items, sid, "ArmorPiercingMod") or 0)]
print("rounds with ArmorPiercingMod == 0:", len(zero), zero[:3])
if zero:
    app.ammo_overrides[zero[0]] = {"piercing": 3.0}
    out = build_patches(app.gd, app._collect())
    assert not out, f"0 x factor produces a patch: {list(out)}"
    print(f"{zero[0]}: piercing x3 -> nothing to patch  OK")
    app.ammo_overrides.clear()

# --- Loot sliders ---
app.sliders["loot_amount"].set(200)
app.update()
s = app._collect()
out = build_patches(app.gd, s)
key = [k for k in out if "ItemGeneratorPrototypes" in k]
assert key, list(out)
print(f"loot slider 200 %: {key[0].split('/')[-1]}  {len(out[key[0]]):,} chars, "
      f"{out[key[0]].count(chr(10)):,} lines")

# --- Presets: save, change everything, load ---
state = app._ui_state()
app.sliders["loot_amount"].set(400)
app.sliders["hp"].set(250)
app.update()
app._apply_ui_state(state)
app.update()
assert app.sliders["loot_amount"].get() == 200, app.sliders["loot_amount"].get()
assert app.sliders["hp"].get() == 100, app.sliders["hp"].get()
print("preset save/load round-trip  OK")

app.sliders["loot_amount"].set(100)
app.update()
assert not build_patches(app.gd, app._collect())
print("reset -> nothing to patch  OK")

app.destroy()
print("\nRELEASE-GUI-TEST OK")
