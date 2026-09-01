"""End-to-End: echter Scan-Thread ueber eine Fake-~mods im Temp-Spielordner."""
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

with tempfile.TemporaryDirectory(prefix="s2t_e2e_") as tmp:
    game_dir = Path(tmp)
    mods = game_dir / "Stalker2" / "Content" / "Paks" / "~mods"
    mods.mkdir(parents=True)

    gd = GameData(VANILLA)
    fake = build_patches(gd, Settings(mod_name="OXA_Fake",
                                      player_damage_factor=2.0,
                                      npc_grenade_factor=0.0))
    pakio.pack_mod(fake, mods / "OXA_Fake_P.pak")
    (mods / "Broken_P.pak").write_bytes(b"junk")
    (mods / "Broken_P.utoc").write_bytes(b"")

    app = gui.App()
    app.gd = gd
    app.game_dir = game_dir
    app.update()

    # Angebots-Dialog: erscheint genau einmal
    app._maybe_offer_modscan()
    app.update()
    dialogs = [w for w in app.winfo_children()
               if isinstance(w, gui.ctk.CTkToplevel)]
    assert dialogs, "Angebots-Dialog fehlt"
    dialogs[0].destroy()          # "Not now" simulieren wir per destroy
    assert app._modscan_offered
    app._maybe_offer_modscan()    # zweiter Aufruf darf NICHT mehr fragen
    app.update()
    assert len([w for w in app.winfo_children()
                if isinstance(w, gui.ctk.CTkToplevel)]) == 0
    print("Angebots-Dialog: genau einmal  OK")

    # Echten Scan fahren (Thread + Queue + Ergebnisdialog)
    app._start_modscan()
    t0 = time.time()
    while app._modscan_payload is None and not app.mod_conflicts:
        app.update()
        time.sleep(0.05)
        if time.time() - t0 > 60:
            raise SystemExit("Scan haengt")
    # Nachrichtenschleife weiterlaufen lassen, bis _finish_modscan lief
    t0 = time.time()
    while not app.modscan_results:
        app.update()
        time.sleep(0.05)
        if time.time() - t0 > 30:
            raise SystemExit("modscan_done kam nie an")
    print("Scan fertig:", [(i.name, i.readable) for i in app.modscan_results])

    assert "pdmg" in app.mod_conflicts, app.mod_conflicts
    assert "npc_grenades" in app.mod_conflicts
    assert app.mod_conflicts["pdmg"] == ["OXA_Fake_P"]
    broken = [i for i in app.modscan_results if not i.readable]
    assert len(broken) == 1 and "can't read" in broken[0].note
    row = app.sliders["pdmg"]
    assert row.dot is not None and row.dot.winfo_manager()
    assert row.dot.cget("text_color") == gui.MARK_INFO
    labels = app._conflict_labels("OXA_Fake_P")
    print("Klartext-Regler:", labels)
    assert any("damage" in l.lower() for l in labels)
    # Ergebnis-Dialog offen? (transient Toplevel)
    tops = [w for w in app.winfo_children() if isinstance(w, gui.ctk.CTkToplevel)]
    assert tops, "Ergebnis-Dialog fehlt"
    for w in tops:
        w.destroy()
    app.destroy()

print("\nE2E-MODSCAN-TEST OK")
