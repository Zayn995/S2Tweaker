"""Layout-Test: Scan-Knopf muss auch beim 880x600-Minimum sichtbar sein,
und waehrend eines Scans sind Browse/Reload gesperrt."""
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
# Frisch starten: eine liegengebliebene Datei (z.B. von einem frueheren
# Agenten-Lauf) wuerde den Neutral-Check faelschlich ausloesen.
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
    assert mapped, f"Scan-Knopf bei {geom} unsichtbar"
    assert w >= 100, f"Scan-Knopf bei {geom} abgeschnitten ({w}px)"
    # auch die Nachbarn muessen sichtbar bleiben
    for name in ("btn_build", "btn_install", "btn_open", "btn_remove"):
        b = getattr(app, name)
        assert b.winfo_ismapped() and b.winfo_width() > 50, \
            f"{name} bei {geom}: {b.winfo_width()}px"
    # Header-Zeile 2 (Suche / Changed only / FAQ / Update) ebenso
    for name in ("search_entry", "btn_changed", "btn_faq", "btn_update"):
        b = getattr(app, name)
        assert b.winfo_ismapped() and b.winfo_width() > 60, \
            f"{name} bei {geom}: {b.winfo_width()}px"
print("Layout OK (1010x720 und 880x600)")

# --- Buttons waehrend eines Scans gesperrt -------------------------------
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
    # Zweiter Start waehrend des Laufs: stiller No-Op
    app._start_modscan()
    print("waehrend Scan: Browse/Reload/Scan gesperrt  OK")
    t0 = time.time()
    while app._scan_running:
        app.update()
        time.sleep(0.05)
        if time.time() - t0 > 60:
            raise SystemExit("Scan haengt")
    assert str(app.btn_browse.cget("state")) == "normal"
    assert str(app.btn_confirm.cget("state")) == "normal"
    assert str(app.btn_scan.cget("state")) == "normal"
    print("nach Scan: alles wieder frei  OK")
    for w in [x for x in app.winfo_children()
              if isinstance(x, gui.ctk.CTkToplevel)]:
        w.destroy()

app.destroy()
print("\nLAYOUT/LOCK-TEST OK")
