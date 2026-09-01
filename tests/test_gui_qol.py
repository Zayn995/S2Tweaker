"""QoL-Test: Manifest+Pak-Import, Changed-only, Compat-Report."""
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
    # --- 1) Manifest wird eingebettet und ist vollstaendig ---------------
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
    pakio.pack_mod(patches, pak,
                   root_files={gui.MANIFEST_NAME:
                               app._build_manifest(s, active)})
    entries = pakio.list_pak(pak)
    assert gui.MANIFEST_NAME in entries, entries[:5]
    assert all(e == gui.MANIFEST_NAME or e.startswith("Stalker2/")
               for e in entries), "Manifest muss an der Wurzel liegen"
    print("Manifest an der Pak-Wurzel eingebettet  OK")

    # --- 2) Import: Reset, dann alles aus der Pak zurueck ----------------
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
    print("Pak-Import: Regler, Checkbox, Armor-Override, Name zurueck  OK")

    # Fremde Pak ohne Manifest: klare Meldung statt Crash (messagebox
    # abfangen, headless)
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
    print("Fremde Pak ohne Manifest: hoefliche Meldung  OK")

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
assert hl("hp") == "normal"        # geaendert (250)
assert hl("npchp") == "dim"        # vanilla
seva_row = None
blk = app._ir_blocks["Body"]
assert blk._hitset == {"SEVA_Neutral_Armor"}, blk._hitset
# Live-Puls: Regler bewegen -> beim naechsten Pass hell
app.sliders["npchp"].set(2.0)
app._apply_changed_only()
assert hl("npchp") == "normal"
# Suche hat Vorrang, Leeren stellt Changed-only wieder her
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
print("Changed only: dimmen, Live-Puls, Suche-Vorrang, Toggle aus  OK")

# --- 4) Compat-Report ----------------------------------------------------
info_a = modscan.ModInfo(name="zzz_OXA_P", path=Path(r"C:\x\zzz_zOXA_P.pak"),
                         n_cfg=3)
info_a.pairs = {("Easy", "Weapon_BaseDamage"), ("Hard", "Weapon_BaseDamage")}
info_b = modscan.ModInfo(name="Big_P", path=Path(r"C:\x\Big_P.pak"),
                         readable=False,
                         note="contains data I can't read (IoStore format)")
app.modscan_results = [info_a, info_b]
app.mod_conflicts = {"pdmg": ["zzz_OXA_P"]}
app._mods_after = {"zzz_OXA_P"}
app._footprints["pdmg"] = {("Easy", "Weapon_BaseDamage"),
                           ("Medium", "Weapon_BaseDamage")}
report = app._build_compat_report()
print("--- Report-Auszug ---")
print("\n".join(report.splitlines()[:14]))
assert "zzz_zOXA_P.pak" in report
assert "loads AFTER your pak" in report
assert "IoStore" in report and "overlap unknown" in report
assert "Player damage (guns)" in report
assert "Easy.Weapon_BaseDamage" in report
assert "Medium.Weapon_BaseDamage" not in report.split("Details")[1], \
    "nur die Schnittmenge gehoert in die Details"
print("Report: Ladereihenfolge, IoStore, Property-Details  OK")

# --- 5) Layout mit neuem Header-Knopf ------------------------------------
for geom in ("1010x720", "880x600"):
    app.geometry(geom)
    app.update_idletasks(); app.update()
    assert app.btn_changed.winfo_ismapped(), geom
    assert app.btn_faq.winfo_ismapped(), geom
    assert app.search_entry.winfo_width() >= 150, geom
print("Layout: Changed-only-Knopf bei 1010/880 px sichtbar  OK")

app.destroy()
print("\nQOL-TEST OK")
