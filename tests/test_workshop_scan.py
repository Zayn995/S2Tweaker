"""Steam-Workshop-Scan: Pfad-Erkennung, Namen, E2E ueber einen Fake-Steam-Baum.

Der Fake-Baum bildet die echte Ablage nach (verifiziert 02.09. am Spiel):
<Bibliothek>\\steamapps\\workshop\\content\\1643320\\<item>\\Windows\\
{New,Override}Content\\Windows\\Stalker2\\Mods\\<Name>\\Content\\Paks\\...
Wie immer: SETTINGS_FILE umbiegen, nie _on_close/_save_ui_settings rufen.
"""
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import game, gui, modscan, pakio
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches

with tempfile.TemporaryDirectory(prefix="s2t_ws_") as tmp:
    lib = Path(tmp)
    game_dir = lib / "steamapps" / "common" / "FakeStalker2"
    mods = game_dir / "Stalker2" / "Content" / "Paks" / "~mods"
    mods.mkdir(parents=True)
    ws = lib / "steamapps" / "workshop" / "content" / "1643320"

    # --- 1) Pfad-Erkennung ------------------------------------------------
    assert game.steam_workshop_dir(game_dir) is None, \
        "ohne Workshop-Ordner muss None kommen"
    ws.mkdir(parents=True)
    assert game.steam_workshop_dir(game_dir) == ws
    assert game.steam_workshop_dir(Path(tmp)) is None, \
        "Nicht-Steam-Pfad darf keinen Workshop melden"
    print("steam_workshop_dir OK")

    # --- 2) Fake-Workshop-Inhalte bauen ----------------------------------
    def item_paks(item: str, mod: str, kind: str) -> Path:
        d = (ws / item / "Windows" / kind / "Windows" / "Stalker2" / "Mods"
             / mod / "Content" / "Paks" / "Windows")
        d.mkdir(parents=True)
        return d

    gd = GameData(VANILLA)
    fake = build_patches(gd, Settings(mod_name="CoolMod",
                                      player_damage_factor=2.0))
    d = item_paks("111", "CoolMod", "OverrideContent")
    pakio.pack_mod(fake, d / "CoolModStalker2-Windows-OverrideContent.pak")

    d = item_paks("222", "IoMod", "NewContent")
    (d / "IoModStalker2-Windows-NewContent.pak").write_bytes(b"junk")
    (d / "IoModStalker2-Windows-NewContent.utoc").write_bytes(b"")

    (ws / "333").mkdir()
    (ws / "333" / "loose.pak").write_bytes(b"junk")

    paks = modscan.find_workshop_paks(ws)
    assert len(paks) == 3, [p.name for p in paks]
    assert modscan.find_workshop_paks(None) == []
    names = sorted(modscan.workshop_mod_name(p, ws) for p in paks)
    assert names == ["333 (Workshop)", "CoolMod (Workshop)",
                     "IoMod (Workshop, new content)"], names
    print("find_workshop_paks + Namen OK:", names)

    # --- 3) E2E: Scan sieht die Workshop-Mods -----------------------------
    app = gui.App()
    app.gd = gd
    app.game_dir = game_dir
    app.update()
    app._start_modscan()
    t0 = time.time()
    while not app.modscan_results:
        app.update()
        time.sleep(0.05)
        if time.time() - t0 > 60:
            raise SystemExit("Workshop-Scan haengt")
    by_name = {i.name: i for i in app.modscan_results}
    assert "CoolMod (Workshop)" in by_name, by_name.keys()
    assert by_name["CoolMod (Workshop)"].readable
    assert by_name["CoolMod (Workshop)"].source == "workshop"
    assert not by_name["IoMod (Workshop, new content)"].readable
    assert app.mod_conflicts.get("pdmg") == ["CoolMod (Workshop)"], \
        app.mod_conflicts.get("pdmg")
    assert app._mods_unknown == set(by_name), app._mods_unknown
    assert not app._mods_after, "Workshop-Mods duerfen nicht in _mods_after"

    # Tooltip: bei verstelltem Regler ehrlich "load order unknown"
    row = app.sliders["pdmg"]
    row.set(2.0)
    row.set_conflict(app.mod_conflicts["pdmg"], app._mods_after,
                     app._mods_unknown)
    assert "mod manager" in row._dot_tip and "may win" in row._dot_tip, \
        row._dot_tip
    print("Tooltip:", row._dot_tip)

    # Report nennt die Workshop-Sonderstellung
    report = app._build_compat_report()
    assert "Steam Workshop mod - activation and load order" in report
    assert "CoolMod (Workshop)" in report
    for w in [x for x in app.winfo_children()
              if isinstance(x, gui.ctk.CTkToplevel)]:
        w.destroy()
    app.destroy()

print("\nWORKSHOP-SCAN-TEST OK")
