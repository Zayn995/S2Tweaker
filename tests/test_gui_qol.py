"""Quality-of-life checks: manifest/pak import, Changed only, compatibility report."""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui, pakio, modscan
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import build_patches, summarize

gd = GameData(VANILLA)

app = gui.App()
app.gd = gd
app._set_body_state(True)
app._ir_populate()
app.update()

with tempfile.TemporaryDirectory(prefix="s2t_qol_") as tmp:
    # Verify the embedded manifest is complete.
    app.sliders["hp"].set(250)
    app.sliders["loot_amount"].set(200)
    app.checks["improved_vaulting"].select()
    app.armor_overrides["SEVA_Neutral_Armor"] = {"radiation": 2.0}
    app.name_entry.delete(0, "end")
    app.name_entry.insert(0, "QolTest")
    app.update()
    s = app._collect()
    active = summarize(s)
    patches = build_patches(gd, s)
    pak = Path(tmp) / "zzz_QolTest_P.pak"
    text = app._build_manifest(s, active)
    pakio.pack_mod(patches, pak, root_files={gui.MANIFEST_NAME: text})
    entries = pakio.list_pak(pak)
    assert gui.MANIFEST_NAME in entries, entries[:5]
    assert all(e == gui.MANIFEST_NAME or e.startswith("Stalker2/")
               for e in entries), "Manifest must be at the root"
    print("Manifest embedded at pak root  OK")

    # The manifest carries the changed settings only. Storing the complete state
    # of every editor control added roughly 240 KB to each Pak (issue #22).
    stored = json.loads(text)["ui_state"]
    assert len(text) < 8 * 1024, f"manifest carries defaults again: {len(text)} bytes"
    assert len(app.sliders) > 2000, f"control inventory unexpectedly small: {len(app.sliders)}"
    assert abs(stored["sliders"]["hp"] - 250) < 1e-9, stored["sliders"].get("hp")
    assert abs(stored["sliders"]["loot_amount"] - 200) < 1e-9
    assert stored["checks"] == {"improved_vaulting": True}, stored["checks"]
    assert stored["armor_overrides"] == {"SEVA_Neutral_Armor": {"radiation": 2.0}}
    assert "cats" not in stored, "all categories are ticked by default"
    untouched = [key for key in ("decal_count_factor", "bolt_lifetime_factor",
                                "aimpunch", "carry") if key in stored["sliders"]]
    assert not untouched, untouched
    print(f"Manifest stores {len(stored['sliders'])} of {len(app.sliders)} sliders, "
          f"{len(text)} bytes  OK")

    # Reset then restore all state from the Pak.
    app._reset_all()
    app.name_entry.delete(0, "end")
    app.name_entry.insert(0, "Anders")
    app.update()
    assert abs(app.sliders["hp"].get() - 100) < 1e-9
    app._import_pak(pak)
    app.update()
    assert abs(app.sliders["hp"].get() - 250) < 1e-9
    assert abs(app.sliders["loot_amount"].get() - 200) < 1e-9
    assert bool(app.checks["improved_vaulting"].get())
    assert app.armor_overrides.get("SEVA_Neutral_Armor") == {"radiation": 2.0}
    assert app.name_entry.get() == "QolTest"
    print("Pak import restores slider, checkbox, armor override and name  OK")

    # Foreign pak without a manifest: clear message instead of a crash (messagebox
    # intercepted for headless execution).
    naked = Path(tmp) / "foreign_P.pak"
    pakio.pack_mod({"DifficultyPrototypes/x.cfg":
                    "Easy : struct.begin {bpatch}\n   Weapon_BaseDamage = 2\nstruct.end\n"},
                   naked)
    seen = []
    orig_info = gui.messagebox.showinfo
    gui.messagebox.showinfo = lambda *a, **k: seen.append(a)
    try:
        app._import_pak(naked)
    finally:
        gui.messagebox.showinfo = orig_info
    assert seen and "manifest" in seen[0][1].lower()
    print("Foreign pak without a manifest: explanatory message  OK")

# --- 3) Changed only -----------------------------------------------------
def hl(key):
    row = app.sliders[key]
    c = row.label.cget("text_color")
    if c == "gray35":
        return "dim"
    if c == gui.ACCENT:
        return "match"
    return "normal"

assert not app.changed_only
app._toggle_changed_only()
app.update()
assert app.changed_only
assert hl("hp") == "normal"        # Changed to 250.
assert hl("npchp") == "dim"        # vanilla
seva_row = None
blk = app._ir_blocks["Body"]
assert blk._hitset == {"SEVA_Neutral_Armor"}, blk._hitset
# Live update: move a slider -> highlight on the next pass.
app.sliders["npchp"].set(2.0)
app._apply_changed_only()
assert hl("npchp") == "normal"
# Search takes precedence; clearing restores Changed only.
app.search_entry.insert(0, "medkit")
app._apply_filter(); app.update()
assert hl("healing") == "match"
app.search_entry.delete(0, "end")
app._apply_filter(); app.update()
assert hl("healing") == "dim"      # vanilla + changed-only
app._toggle_changed_only()
app.update()
assert not app.changed_only
assert hl("npchp") == "normal"
print("Changed only: dimming, live update, search priority, toggle off  OK")

# --- 4) Compat-Report ----------------------------------------------------
info_a = modscan.ModInfo(name="zzz_OXA_P", path=Path(r"C:\x\zzz_zOXA_P.pak"),
                         n_cfg=3)
info_a.pairs = {("Easy", "Weapon_BaseDamage"), ("Hard", "Weapon_BaseDamage")}
info_b = modscan.ModInfo(name="Big_P", path=Path(r"C:\x\Big_P.pak"),
                         readable=False,
                         note="contains data I can't read (not a readable "
                              ".pak file)")
info_c = modscan.ModInfo(name="WsMod (Workshop)",
                         path=Path(r"C:\x\WsMod.pak"), n_cfg=2,
                         source="workshop", packed_assets=True,
                         note=modscan.PACKED_NOTE)
app.modscan_results = [info_a, info_b, info_c]
app.mod_conflicts = {"pdmg": ["zzz_OXA_P"]}
app._mods_after = {"zzz_OXA_P"}
app._footprints["pdmg"] = {("Easy", "Weapon_BaseDamage"),
                           ("Medium", "Weapon_BaseDamage")}
report = app._build_compat_report()
print("--- Report excerpt ---")
print("\n".join(report.splitlines()[:14]))
assert "zzz_zOXA_P.pak" in report
assert "filename sorts AFTER your pak" in report
assert "not a readable .pak file" in report and "overlap unknown" in report
assert "note: " + modscan.PACKED_NOTE in report, \
    "Packed-assets note missing from report"
assert "Player damage (guns)" in report
assert "Easy.Weapon_BaseDamage" in report
assert "Medium.Weapon_BaseDamage" not in report.split("Details")[1], \
    "Only the intersection belongs in the details"
print("Report: load order, IoStore, property details  OK")

# Check header layout with the preset-import action.
for geom in ("1010x720", "880x600"):
    app.geometry(geom)
    app.update_idletasks(); app.update()
    assert app.btn_changed.winfo_ismapped(), geom
    assert app.btn_faq.winfo_ismapped(), geom
    assert app.search_entry.winfo_width() >= 150, geom
print("Layout: Changed-only button visible at 1010/880 px  OK")

# --- 5) settings.json stores the changed settings only -------------------
app._reset_all()
app.sliders["hp"].set(250)
app.checks["improved_vaulting"].select()
app.name_entry.delete(0, "end")
app.name_entry.insert(0, "QolTest")
app.update()
app._save_ui_settings()
saved = gui.SETTINGS_FILE.read_text(encoding="utf-8")
data = json.loads(saved)
assert len(saved) < 8 * 1024, f"settings file carries defaults again: {len(saved)} bytes"
assert abs(data["sliders"]["hp"] - 250) < 1e-9, data["sliders"].get("hp")
assert data["checks"] == {"improved_vaulting": True}, data["checks"]
assert "cats" not in data, "all categories are ticked by default"
assert "decal_count_factor" not in data["sliders"], "editor defaults saved again"
print(f"settings.json stores {len(data['sliders'])} of {len(app.sliders)} sliders, "
      f"{len(saved)} bytes  OK")

app.destroy()

# The reduced settings file restores the same state on the next start, because
# freshly built controls already sit at the defaults it leaves out.
app2 = gui.App()
app2.update()
assert abs(app2.sliders["hp"].get() - 250) < 1e-9, "changed slider not restored"
assert bool(app2.checks["improved_vaulting"].get()), "changed checkbox not restored"
assert app2.name_entry.get() == "QolTest"
untouched = app2.sliders["decal_count_factor"]
assert abs(untouched.get() - untouched.default) < 1e-9, untouched.get()
assert all(bool(box.get()) for box in app2.cat_checks.values()), "categories lost"
app2.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("Restart restores the state from the reduced settings file  OK")
print("\nQOL-TEST OK")
