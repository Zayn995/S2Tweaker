"""Check scan-button visibility at minimum window size and browse/reload locks during scans."""
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui, pakio
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
# Start with clean temporary state so leftovers cannot affect neutrality checks.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches

app = gui.App()
app.update()

for geom in ("1010x720", "880x600"):
    app.geometry(geom)
    app.update_idletasks()
    app.update()
    w = app.btn_scan.winfo_width()
    mapped = bool(app.btn_scan.winfo_ismapped())
    print(f"{geom}: btn_scan mapped={mapped} width={w}px")
    assert mapped, f"Scan button at {geom} invisible"
    assert w >= 100, f"Scan button at {geom} clipped ({w}px)"
    # Keep adjacent controls visible.
    for name in ("btn_build", "btn_install", "btn_open", "btn_remove"):
        b = getattr(app, name)
        assert b.winfo_ismapped() and b.winfo_width() > 50, \
            f"{name} at {geom}: {b.winfo_width()}px"
    # Keep second-row controls visible; there is no network update button.
    for name in ("search_entry", "btn_changed", "btn_faq", "btn_oodle",
                 "btn_scroll"):
        b = getattr(app, name)
        assert b.winfo_ismapped() and b.winfo_width() > 60, \
            f"{name} at {geom}: {b.winfo_width()}px"
print("Layout OK (1010x720 and 880x600)")

# --- Buttons remain locked during a scan ---
with tempfile.TemporaryDirectory(prefix="s2t_lock_") as tmp:
    game_dir = Path(tmp)
    mods = game_dir / "Stalker2" / "Content" / "Paks" / "~mods"
    mods.mkdir(parents=True)
    gd = GameData(VANILLA)
    pakio.pack_mod(build_patches(gd, Settings(mod_name="X",
                                              player_damage_factor=2.0)),
                   mods / "X_P.pak")
    app.gd = gd
    app.game_dir = game_dir
    app._start_modscan()
    app.update()
    assert app._scan_running
    assert str(app.btn_browse.cget("state")) == "disabled"
    assert str(app.btn_confirm.cget("state")) == "disabled"
    assert str(app.btn_scan.cget("state")) == "disabled"
    # Ignore an attempt to start a second concurrent scan.
    app._start_modscan()
    print("While scanning: Browse/Reload/Scan locked  OK")
    t0 = time.time()
    while app._scan_running:
        app.update()
        time.sleep(0.05)
        if time.time() - t0 > 60:
            raise SystemExit("Scan stalled")
    assert str(app.btn_browse.cget("state")) == "normal"
    assert str(app.btn_confirm.cget("state")) == "normal"
    assert str(app.btn_scan.cget("state")) == "normal"
    print("After scan: all controls unlocked  OK")
    for w in [x for x in app.winfo_children()
              if isinstance(x, gui.ctk.CTkToplevel)]:
        w.destroy()

app.destroy()
print("\nLAYOUT/LOCK-TEST OK")
