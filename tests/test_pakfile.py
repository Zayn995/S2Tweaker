"""pakfile.py - der Pak-Leser/-Schreiber in reinem Python (kein repak.exe).

Prueft ohne Spieldaten den Roundtrip (packen wie pack_mod, lesen, Muster
wie `repak unpack -i`), das Footer-Layout von V8B und die Fehlerfaelle.
Liegt das Spiel samt Oodle-DLL vor, werden zusaetzlich die 36 benoetigten
Spieldateien aus pakchunk0 entpackt und byteweise mit vanilla/ verglichen
(das dort liegende Material stammt aus repak-Entpackungen) - und alle
geparkten Mod-Paks des Besitzers muessen lesbar sein.
"""
import hashlib
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import pakfile, pakio  # noqa: E402
from s2tweaker.gamedata import NEEDED_FILES, GAMEDATA_REL  # noqa: E402

# --- 1) Roundtrip ueber pack_mod: Pfade, Inhalte, Reihenfolge -------------
cfg = {
    "ObjPrototypes/ObjPrototypes_patch_T.cfg": "a : struct.begin {bpatch}\n   b = 1\nstruct.end\n",
    "CoreVariables.cfg_patch_T.cfg": "x = 2\n",
    "//GameLite/DLCGameData/PreOrder/ItemPrototypes/ItemPrototypes_patch_T.cfg": "dlc\n",
}
with tempfile.TemporaryDirectory(prefix="s2t_pak_") as tmp:
    tmp = Path(tmp)
    pak = pakio.pack_mod(cfg, tmp / "zzz_T_P.pak", root_files={"s2tweaker.json": "{}"})
    names = pakio.list_pak(pak)
    assert names == [
        "Stalker2/Content/GameLite/DLCGameData/PreOrder/ItemPrototypes/ItemPrototypes_patch_T.cfg",
        "Stalker2/Content/GameLite/GameData/CoreVariables.cfg_patch_T.cfg",
        "Stalker2/Content/GameLite/GameData/ObjPrototypes/ObjPrototypes_patch_T.cfg",
        "s2tweaker.json"], names
    with pakfile.PakFile(pak) as pk:
        assert pk.version.label == "V8B" and pk.mount_point == "../../../", (pk.version, pk.mount_point)
        assert pk.compression == [None] * 5, pk.compression
        # write_text schreibt Windows-Zeilenenden - so war es mit repak auch
        assert pk.read("Stalker2/Content/GameLite/GameData/CoreVariables.cfg_patch_T.cfg") == b"x = 2\r\n"
        for name in pk.files():
            entry = pk.entries[name]
            assert entry.hash == hashlib.sha1(pk.read(name)).digest(), name
            assert entry.compression is None and entry.blocks is None
    raw = pak.read_bytes()
    # Footer V8B: 221 Bytes - GUID(16) + encrypted(1) + magic(4) + version(4)
    # + index offset/size(16) + sha1(20) + 5 Namen a 32
    guid, enc, magic, major, ioff, isize = struct.unpack_from("<16sBIIQQ", raw, len(raw) - 221)
    assert guid == b"\0" * 16 and enc == 0 and magic == pakfile.MAGIC and major == 8
    assert raw[len(raw) - 221 + 41:len(raw) - 221 + 61] == hashlib.sha1(raw[ioff:ioff + isize]).digest()
    assert raw[-160:] == b"\0" * 160
    print("pack_mod/list_pak/read: V8B, ../../../, unkomprimiert, SHA-1 je Eintrag  OK")

    # unpack mit Muster: Datei, Ordner, '[' als '[[]'
    out = tmp / "u"
    pakio.unpack(pak, out, include="Stalker2/Content/GameLite/GameData/CoreVariables.cfg_patch_T.cfg")
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()) == [
        "Stalker2/Content/GameLite/GameData/CoreVariables.cfg_patch_T.cfg"]
    out2 = tmp / "u2"
    pakio.unpack_many(pak, out2, ["Stalker2/Content/GameLite/GameData", "s2tweaker.json"])
    got = sorted(p.relative_to(out2).as_posix() for p in out2.rglob("*") if p.is_file())
    assert got == names[1:], got
    out3 = tmp / "u3"
    pakio.unpack(pak, out3, include="does/not/match")
    assert not any(out3.rglob("*")) or not any(p.is_file() for p in out3.rglob("*"))
    print("unpack/unpack_many: Datei-, Ordner- und Fehlmuster wie repak -i  OK")

    # Sonderfaelle: leere Datei, Nicht-ASCII-Name, Reihenfolge '-' vor '/'
    files = [("a-x.txt", b"dash"), ("a/b.txt", b"slash"), ("empty.txt", b""),
             ("Umlaut-\u00e4.txt", b"non-ascii")]
    p2 = pakfile.write_pak(tmp / "s.pak", files)
    with pakfile.PakFile(p2) as pk:
        assert pk.files() == sorted(n for n, _ in files)
        assert all(pk.read(n) == d for n, d in files)
        assert pk.read("empty.txt") == b""
    print("Sonderfaelle: leerer Eintrag, UTF-16-Name, Sortierung  OK")

    # Muster-Regeln
    rx = [pakfile.glob_regex("Stalker2/Content/*/GameData/**.cfg"), pakfile.glob_regex("x[[]1]")]
    assert pakfile.matches(rx, "Stalker2/Content/GameLite/GameData/A/B.cfg")
    assert not pakfile.matches(rx, "Stalker2/Content/GameLite/Other/A.cfg")
    assert pakfile.matches(rx, "x[1]") and not pakfile.matches(rx, "x1")
    assert pakfile.matches([pakfile.glob_regex("a")], "a/b/c") and not pakfile.matches([pakfile.glob_regex("a")], "ab/c")
    print("Glob-Muster: '*' ohne '/', '**' mit, '[[]' literal, Ordner-Treffer  OK")

    # Fehlerfaelle
    (tmp / "junk.pak").write_bytes(b"not a pak" * 50)
    try:
        pakfile.PakFile(tmp / "junk.pak")
        raise AssertionError("Muell wurde als Pak akzeptiert")
    except pakfile.PakError:
        pass
    with pakfile.PakFile(pak) as pk:
        try:
            pk.read("nope")
            raise AssertionError("fehlender Eintrag ohne Fehler")
        except pakfile.PakError:
            pass
    print("Fehlerfaelle: kein Pak / fehlender Eintrag -> PakError  OK")

# --- 2) Gegen das echte Spiel (nur wenn vorhanden) -----------------------
GAME = Path(r"C:\Games\Steam\steamapps\common\S.T.A.L.K.E.R. 2 Heart of Chornobyl")
pak0 = GAME / "Stalker2" / "Content" / "Paks" / "pakchunk0-Windows.pak"
vanilla = ROOT / "vanilla" / GAMEDATA_REL
if pak0.is_file() and vanilla.is_dir() and pakio.oodle_available(pak0):
    with tempfile.TemporaryDirectory(prefix="s2t_pak_") as tmp:
        tmp = Path(tmp)
        for name in NEEDED_FILES:
            pakio.unpack(pak0, tmp, include=f"{GAMEDATA_REL}/{name}")
        checked = 0
        for name in NEEDED_FILES:
            ours = tmp / GAMEDATA_REL / name
            ref = vanilla / name
            assert ours.is_file(), f"{name} nicht entpackt"
            if ref.is_file():
                assert ours.read_bytes() == ref.read_bytes(), f"{name} weicht von vanilla/ ab"
                checked += 1
        assert checked >= len(NEEDED_FILES) // 2, checked
    print(f"pakchunk0 (Oodle): {len(NEEDED_FILES)} Dateien entpackt, {checked} byteidentisch mit vanilla/  OK")
    parked = GAME / "mods_geparkt_fuer_S2Tweaker_Tests"
    if parked.is_dir():
        n = 0
        for mp in sorted(parked.rglob("*.pak")):
            names = pakio.list_pak(mp)
            with pakfile.PakFile(mp, oodle=lambda c, r: pakio.oodle_decompressor(mp)(c, r)) as pk:
                for name in [x for x in pk.files() if ".cfg" in x.lower()][:5]:
                    assert len(pk.read(name)) == pk.entries[name].uncompressed
            n += 1
        print(f"{n} geparkte Mod-Paks (V3/V8B/V11, Zlib/Oodle/roh) gelistet und angelesen  OK")
else:
    print("Spiel/vanilla/Oodle nicht vorhanden - Spieldaten-Teil uebersprungen")

print("\nPAKFILE-TEST OK")
