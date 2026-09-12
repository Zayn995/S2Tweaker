"""Check edition weapon discovery and DLC patch routing.

Skip when local vanilla data lacks the DLCGameData branch."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches
from s2tweaker.cfgparse import parse_number
from s2tweaker import pakio

gd = GameData(VANILLA)
if not gd.dlc_editions:
    print("SKIP: no DLCGameData beside vanilla/GameData - suite "
          "skipped (not a failure).")
    sys.exit(0)

# --- 1) Inventory --------------------------------------------------------
dlc = gd.dlc_player_weapons()
eds = {ed for _c, _w, ed in dlc.values()}
assert eds == {"PreOrder", "Deluxe", "Ultimate"}, eds
assert "Gun_Gabion_AR_GS" in dlc, sorted(dlc)
cat, cws, ed = dlc["Gun_Gabion_AR_GS"]
assert ed == "Deluxe" and cat == "rifle", (cat, ed)
assert cws and cws in gd.weaponsettings.children, cws
# Do not duplicate edition skins reusing base-game setups.
assert "GunAK74_ST" not in {s for s in dlc}, "Base setup listed as DLC"
pw = gd.player_weapons()
assert "Gun_Gabion_AR_GS" in pw and pw["Gun_Gabion_AR_GS"][0] == "rifle"
print(f"Inventory: {len(dlc)} edition weapons in {len(eds)} editions, "
      "Gabion=rifle, CWS in base data  OK")

# An individual edition weapon override must produce an edition patch.
p = build_patches(gd, Settings(
    weapon_overrides={"Gun_Gabion_AR_GS": {"firerate": 2.0}}))
dlc_keys = [k for k in p if k.startswith("//GameLite/DLCGameData/Deluxe/")]
assert dlc_keys, list(p)
text = p[dlc_keys[0]]
vanilla_fi = parse_number(
    gd.dlc_resolve_weapon("Deluxe", "Gun_Gabion_AR_GS", "FireInterval"))
assert vanilla_fi > 0
import re
m = re.search(r"FireInterval = ([^\s;]+)", text)
assert m and abs(float(m.group(1)) - vanilla_fi / 2) < 1e-9, (
    m and m.group(1), vanilla_fi)
print(f"Gabion-Override x2: DLC-Patch {dlc_keys[0].split('/')[-1]}, "
      f"FireInterval {vanilla_fi} -> {m.group(1)}  OK")

# --- 3) Global slider reaches self-defined DLC values ---
p = build_patches(gd, Settings(aim_time_factor=2.0))
n_dlc = sum(1 for k in p if k.startswith("//GameLite/DLCGameData/"))
n_self = len(gd.dlc_weapon_general_values("AimingTime"))
if n_self:
    assert n_dlc >= 1, list(p)
print(f"Global aimtime x2: {n_self} self-defined DLC durations, "
      f"{n_dlc} DLC-patch files  OK")

# Verify edition paths survive the Pak roundtrip.
out = ROOT / "tests" / "_tmp" / "dlc_test.pak"
p = build_patches(gd, Settings(
    weapon_overrides={"Gun_Gabion_AR_GS": {"firerate": 2.0}}))
pakio.pack_mod(p, out)
names = pakio.list_pak(out)
assert any(n.startswith("Stalker2/Content/GameLite/DLCGameData/Deluxe/")
           for n in names), names
out.unlink(missing_ok=True)
print("Pak roundtrip: DLCGameData path mounted correctly  OK")

# Debug export must treat //GameLite paths as relative markers, not UNC paths.
import shutil
dbg_root = ROOT / "tests" / "_tmp" / "dlc_debug_cfg"
shutil.rmtree(dbg_root, ignore_errors=True)
naive = dbg_root / dlc_keys[0]
assert naive.is_absolute() and dbg_root not in naive.parents, (
    "A naive merge would displace the base entry", naive)
written = pakio.export_cfgs(p, dbg_root)
assert len(written) == len(p), (len(written), len(p))
for t in written:
    assert t.is_file() and dbg_root in t.parents, t
dlc_written = [t for t in written
               if "DLCGameData" in t.as_posix()]
assert dlc_written and all(
    t.relative_to(dbg_root).as_posix().startswith("GameLite/DLCGameData/")
    for t in dlc_written), [t.as_posix() for t in dlc_written]
shutil.rmtree(dbg_root, ignore_errors=True)
print(f"export_cfgs: {len(written)} files, {len(dlc_written)} of them under "
      "GameLite/DLCGameData/, nothing outside the base directory  OK")

# GUI flow: debug enabled and a global weapon slider changed ->
# Edition patches: _generate() must produce both pak and export.
from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)
app = gui.App()
app.gd = gd
app.game_dir = SCRATCH
app.update()
key = next(k for k, f in gui.SLIDER_FIELDS.items() if f == "aim_time_factor")
app.sliders[key].set(200)
assert abs(app._collect().aim_time_factor - 2.0) < 1e-9, \
    app._collect().aim_time_factor
app.debug_check.select()
seen = []
orig_info = gui.messagebox.showinfo
gui.messagebox.showinfo = lambda *a, **k: seen.append(a)
out_pak = SCRATCH / "zzz_DlcDebug_P.pak"
try:
    ok = app._generate(out_pak)
finally:
    gui.messagebox.showinfo = orig_info
assert ok and out_pak.is_file(), (ok, out_pak)
mod_name = app._collect().mod_name
dbg_gui = SCRATCH / f"{mod_name}_cfg"
assert (dbg_gui / "GameLite" / "DLCGameData").is_dir(), \
    sorted(x.as_posix() for x in dbg_gui.rglob("*.cfg"))[:5]
msg = "\n".join(str(x) for x in seen)
assert "Debug:" in msg and "patch .cfg files" in msg and "failed" not in msg, msg
out_pak.unlink(missing_ok=True)
shutil.rmtree(dbg_gui, ignore_errors=True)
for w in [x for x in app.winfo_children()
          if isinstance(x, gui.ctk.CTkToplevel)]:
    w.destroy()
app.destroy()
print("GUI _generate with debug + edition patches: pak + export without "
      "Traceback  OK")

# --- 5) Edition armors in the armor tree ---
dlc_armor = gd.dlc_player_armors()
assert len(dlc_armor) >= 5, sorted(dlc_armor)
assert "SEVA_Monolith_Armor" in dlc_armor
slot, values, ed = dlc_armor["SEVA_Monolith_Armor"]
assert slot == "Body" and ed == "Deluxe" and values.get("Strike") == 2.0, (
    slot, ed, values)
pa = gd.player_armors()
assert "SEVA_Monolith_Armor" in pa and "Zorya_Tourist_Armor" in pa
# Edition armor overrides must use the correct cascade and output branch.
p = build_patches(gd, Settings(
    armor_overrides={"SEVA_Monolith_Armor": {"strike": 3.0}}))
key = "//GameLite/DLCGameData/Deluxe/ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
assert key in p, list(p)
assert "Strike = 6" in p[key], p[key]
assert "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg" not in p, (
    "Base file may remain empty for a DLC-only override")
# Global protection slider reaches base AND edition items.
p = build_patches(gd, Settings(armor_strike_factor=2.0))
dlc_files = [k for k in p if k.startswith("//GameLite/DLCGameData/")]
assert len(dlc_files) == 3, list(p)
print(f"Armors: {len(dlc_armor)} edition items, SEVA-Monolith-"
      "Override x3 -> 6.0 in Deluxe branch; global reaches all 3 editions  OK")

# --- 5b) Display-name aliases, including Riemann/Lullaby ---
from s2tweaker.names import WEAPON_ALIASES
from s2tweaker.gui import weapon_display, weapon_sid_hit
assert "Riemann" in WEAPON_ALIASES["Gun_Logarithm_SMG_GS"]
assert "Lullaby" in WEAPON_ALIASES["Gun_Novator_AR_GS"]
for alias_sid in dlc:
    assert alias_sid in WEAPON_ALIASES, f"Unnamed edition weapon: {alias_sid}"
assert weapon_sid_hit("Gun_Logarithm_SMG_GS", "riemann")
assert weapon_sid_hit("Gun_Novator_AR_GS", "lullaby")
assert not weapon_sid_hit("GunAK74_ST", "riemann")
assert "Riemann" in weapon_display("Gun_Logarithm_SMG_GS")
print("Aliases: all 11 edition weapons named, Riemann/Lullaby searchable  OK")

# --- 6) DLC checker text ---
summary = gd.dlc_summary()
assert "Deluxe" in summary and "Ultimate" in summary and "Pre-order" in summary
assert "11 guns" in summary and "5 armor pieces" in summary, summary
print("Checker:", summary)

# --- 7) Neutral remains neutral ---
assert not build_patches(gd, Settings())
print("Neutral = no patch  OK")

print("\nDLC WEAPONS TEST PASSED")
