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
    # CoolMod wie ein echtes Abo seit dem Layout-Wechsel: ZWEIMAL (neuer
    # OverrideContent-Pfad + alter Pfad direkt unter Stalker2/Mods), beide
    # als IoStore-Trio (.utoc/.ucas daneben, die .ucas 48 Bytes = leer —
    # genau so lagen 12 der 15 echten Abos des Besitzers am 04.09. vor).
    d = item_paks("111", "CoolMod", "OverrideContent")
    pak = d / "CoolModStalker2-Windows-OverrideContent.pak"
    pakio.pack_mod(fake, pak)
    pak.with_suffix(".utoc").write_bytes(b"\0" * 240)
    pak.with_suffix(".ucas").write_bytes(b"\0" * 48)
    legacy = (ws / "111" / "Stalker2" / "Mods" / "CoolMod" / "Content"
              / "Paks" / "Windows")
    legacy.mkdir(parents=True)
    pak2 = legacy / "CoolModStalker2-Windows.pak"
    pakio.pack_mod(fake, pak2)
    pak2.with_suffix(".utoc").write_bytes(b"\0" * 240)
    pak2.with_suffix(".ucas").write_bytes(b"\0" * 48)

    # Kaputte Pak MIT .utoc: bleibt unlesbar — wegen der Pak, nicht wegen
    # des Containers.
    d = item_paks("222", "IoMod", "NewContent")
    (d / "IoModStalker2-Windows-NewContent.pak").write_bytes(b"junk")
    (d / "IoModStalker2-Windows-NewContent.utoc").write_bytes(b"")

    (ws / "333").mkdir()
    (ws / "333" / "loose.pak").write_bytes(b"junk")

    # Reine Asset-Mod: gueltige Pak ohne cfg, Inhalt sitzt in der .ucas
    d = item_paks("444", "AssetOnly", "NewContent")
    pak3 = d / "AssetOnlyStalker2-Windows-NewContent.pak"
    pakio.pack_mod({"readme.txt": "assets live in the .ucas"}, pak3)
    pak3.with_suffix(".utoc").write_bytes(b"\0" * 1200)
    pak3.with_suffix(".ucas").write_bytes(b"\0" * 20000)

    paks = modscan.find_workshop_paks(ws)
    assert len(paks) == 5, [p.name for p in paks]
    assert modscan.find_workshop_paks(None) == []
    names = sorted(modscan.workshop_mod_name(p, ws) for p in paks)
    assert names == ["333 (Workshop)", "AssetOnly (Workshop, new content)",
                     "CoolMod (Workshop)", "CoolMod (Workshop)",
                     "IoMod (Workshop, new content)"], names
    print("find_workshop_paks + Namen OK:", names)

    # --- 2b) scan_pak: ein IoStore-Trio ist LESBAR (Fix 04.09.) -----------
    info = modscan.scan_pak(pak)
    assert info.readable and info.packed_assets and info.n_cfg == 1, \
        vars(info)
    assert any(leaf == "Weapon_BaseDamage" for _, leaf in info.pairs), \
        info.pairs
    assert info.note == modscan.PACKED_NOTE, info.note
    info = modscan.scan_pak(pak3)
    assert info.readable and info.packed_assets and info.n_cfg == 0, \
        vars(info)
    assert info.note == modscan.PACKED_NO_CFG_NOTE, info.note
    info = modscan.scan_pak(ws / "333" / "loose.pak")
    assert not info.readable and "can't read" in info.note, vars(info)
    print("scan_pak: IoStore-Trio lesbar, Asset-only ehrlich, Junk kaputt  OK")

    # --- 2c) merge_same_name: doppelte Abos werden EIN Eintrag ------------
    a, b = modscan.scan_pak(pak), modscan.scan_pak(pak2)
    a.name = b.name = "CoolMod (Workshop)"
    a.source = b.source = "workshop"
    other = modscan.ModInfo(name="Other", path=pak3)
    merged = modscan.merge_same_name([a, b, other])
    assert [m.name for m in merged] == ["CoolMod (Workshop)", "Other"], \
        [m.name for m in merged]
    m = merged[0]
    assert m.n_paks == 2 and m.n_cfg == 1 and m.readable and m.packed_assets
    assert "2 pak files" in m.note and m.note.count("packed assets") == 1, \
        m.note
    assert merged[1].n_paks == 1 and merged[1].note == ""
    # Haelfte ohne cfg + Haelfte mit cfg: "no config" faellt weg, Paare
    # sind die Vereinigung
    x = modscan.ModInfo(name="M", path=pak3, packed_assets=True,
                        note=modscan.PACKED_NO_CFG_NOTE)
    y = modscan.ModInfo(name="M", path=pak, n_cfg=2, packed_assets=True,
                        note=modscan.PACKED_NOTE)
    y.pairs = {("A", "b")}
    x.pairs = {("C", "d")}
    (m2,) = modscan.merge_same_name([x, y])
    assert m2.n_cfg == 2 and m2.pairs == {("A", "b"), ("C", "d")}, vars(m2)
    assert "no config" not in m2.note and "packed assets" in m2.note, m2.note
    # Kaputte + heile Haelfte: Eintrag lesbar, Fehler bleibt als Notiz
    broken = modscan.ModInfo(name="N", path=pak, readable=False,
                             note="contains data I can't read (x)")
    fine = modscan.ModInfo(name="N", path=pak2, n_cfg=1)
    (m3,) = modscan.merge_same_name([broken, fine])
    assert m3.readable and "can't read" in m3.note and m3.n_cfg == 1, \
        vars(m3)
    print("merge_same_name OK:", m.note)

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
    assert "can't read" in by_name["IoMod (Workshop, new content)"].note
    # Genau EIN Treffer trotz zwei CoolMod-Paks (merge_same_name im Worker)
    assert app.mod_conflicts.get("pdmg") == ["CoolMod (Workshop)"], \
        app.mod_conflicts.get("pdmg")
    cool = [i for i in app.modscan_results if i.name == "CoolMod (Workshop)"]
    assert len(cool) == 1 and cool[0].n_paks == 2, \
        [(i.name, i.n_paks) for i in app.modscan_results]
    assert cool[0].packed_assets and "packed assets" in cool[0].note, \
        cool[0].note
    asset = by_name["AssetOnly (Workshop, new content)"]
    assert asset.readable and asset.note == modscan.PACKED_NO_CFG_NOTE, \
        vars(asset)
    assert len(app.modscan_results) == 4, \
        [i.name for i in app.modscan_results]
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
    assert "note: " + modscan.PACKED_NOTE in report, \
        "Packed-Assets-Notiz fehlt im Report"
    assert modscan.PACKED_NO_CFG_NOTE in report
    for w in [x for x in app.winfo_children()
              if isinstance(x, gui.ctk.CTkToplevel)]:
        w.destroy()
    app.destroy()

print("\nWORKSHOP-SCAN-TEST OK")
