"""Headless-Test des Mod-Scans inkl. Regressionsfaellen aus dem Review."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import modscan, pakio
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches
from s2tweaker.gui import (SLIDER_FIELDS, CHECK_FIELDS, EXPENSIVE_FOOTPRINTS,
                           footprint_settings)

VAN = VANILLA
gd = GameData(VAN)
vanilla_index = modscan.build_vanilla_index(gd)
print(f"vanilla index: {len(vanilla_index):,} (top, leaf)-Paare")

footprints = {}
def fp(key):
    if key not in footprints:
        probes = footprint_settings(key)
        if probes is None:
            footprints[key] = None
        else:
            pairs = set()
            for s in probes:
                pairs |= modscan.pairs_from_patches(build_patches(gd, s))
            footprints[key] = pairs
    return footprints[key]

def match(infos):
    segments, leaves = set(), set()
    for i in infos:
        segments |= i.base_names
        leaves |= {l for _, l in i.pairs}
    conflicts = {}
    for key in list(SLIDER_FIELDS) + ["check:" + k for k in CHECK_FIELDS]:
        guard = EXPENSIVE_FOOTPRINTS.get(key)
        if guard and key not in footprints:
            frag, gl = guard
            if not any(frag in s for s in segments) and not (gl & leaves):
                continue
        pairs = fp(key)
        if not pairs:
            continue
        hit = [i.name for i in infos if i.pairs & pairs]
        if hit:
            conflicts[key] = hit
    return conflicts

with tempfile.TemporaryDirectory(prefix="s2t_modscan_test_") as tmp:
    mods = Path(tmp) / "~mods"
    (mods / "sub").mkdir(parents=True)

    # 1) Fake-Overhaul (bpatch, Standard-Layout)
    fake = build_patches(gd, Settings(
        mod_name="FakeOverhaul", player_damage_factor=2.0,
        npc_hp_factor=1.5, quest_reward_factor=3.0, npc_vision_factor=0.5))
    pakio.pack_mod(fake, mods / "zzz_FakeOverhaul_P.pak")

    # 2) Fake-Loot-Mod im UNTERORDNER (Review: OXA liegt in ~mods\oxa\)
    loot = build_patches(gd, Settings(mod_name="FakeLoot",
                                      loot_amount_factor=0.5))
    pakio.pack_mod(loot, mods / "sub" / "FakeLoot_P.pak")

    # 3) IoStore-Attrappe + eigene Ausgabe-Pak
    (mods / "BigOverhaul_P.pak").write_bytes(b"not a real pak")
    (mods / "BigOverhaul_P.utoc").write_bytes(b"")
    (mods / "zzz_S2Tweaker_P.pak").write_bytes(b"own")

    # 4) OFFIZIELLES Namensschema ohne .cfg-Endung (Review-Fund 1)
    pakio.pack_mod(
        {"DifficultyPrototypes.cfg_patch_Official":
         "Hard : struct.begin {bpatch}\n   Weapon_BaseDamage = 3.0\nstruct.end\n"},
        mods / "OfficialStyle_P.pak")

    # 5) Legacy-refkey-Patch unter freiem Namen (Review-Fund 2)
    pakio.pack_mod(
        {"ObjPrototypes/Legacy.cfg":
         "SuperPatch : struct.begin {refurl=../ObjPrototypes.cfg;refkey=Player}\n"
         "   VitalParams : struct.begin\n      MaxHP = 300\n   struct.end\n"
         "struct.end\n"},
        mods / "LegacyMod_P.pak")

    # 6) Eckige Klammern im Pfad (Review-Fund 7: -i ist ein Glob)
    pakio.pack_mod(
        {"[patch] v1/Weird.cfg":
         "Player : struct.begin {bpatch}\n   VitalParams : struct.begin {bpatch}\n"
         "      MaxSP = 250\n   struct.end\nstruct.end\n"},
        mods / "BracketMod_P.pak")

    # 7) VOLLKOPIE mit reinen Vanilla-Werten (Review: darf NICHTS markieren)
    van_text = (Path(VAN) / "DifficultyPrototypes.cfg").read_text(
        encoding="utf-8-sig", errors="replace")
    pakio.pack_mod({"DifficultyPrototypes.cfg": van_text},
                   mods / "VanillaCopy_P.pak")

    # 8) Anker-Kollision: Default+Type (RelationPrototypes-Muster)
    pakio.pack_mod(
        {"RelationPrototypes.cfg":
         "Default : struct.begin\n   Type = ERelationChangingEvent::Kill\n"
         "   Deltas : struct.begin\n      [0] = 5\n   struct.end\nstruct.end\n"},
        mods / "FactionMod_P.pak")

    # 9) Weight-Kollision: Lotterie-Weight tief verschachtelt
    pakio.pack_mod(
        {"PackOfItemsGroupPrototypes.cfg":
         "Bandage : struct.begin\n   Items : struct.begin\n"
         "      [0] : struct.begin\n         Weight = 3\n      struct.end\n"
         "   struct.end\nstruct.end\n"},
        mods / "PackMod_P.pak")

    # 10) Frei benannte Loot-Datei (Review: Guard darf nicht nur auf den
    #     Dateinamen schauen)
    pakio.pack_mod(
        {"LootTweaks/changes.cfg":
         "Arnie_ItemGenerator : struct.begin {bpatch}\n"
         "   ItemGenerator : struct.begin {bpatch}\n"
         "      [0] : struct.begin {bpatch}\n"
         "         PossibleItems : struct.begin {bpatch}\n"
         "            [0] : struct.begin {bpatch}\n"
         "               MaxCount = 99\n            struct.end\n"
         "         struct.end\n      struct.end\n   struct.end\nstruct.end\n"},
        mods / "FreeNameLoot_P.pak")

    # 11) Fundchance am Vanilla-Deckel (Review-Fund 3: Sonde x2 blind)
    pakio.pack_mod(
        {"StashPrototypes/StashPrototypes_patch_MoreStashes.cfg":
         "StashFood_Cheap : struct.begin {bpatch}\n"
         "   ItemGenerators : struct.begin {bpatch}\n"
         "      [0] : struct.begin {bpatch}\n"
         "         SmartLootParams : struct.begin {bpatch}\n"
         "            ConsumablesParams : struct.begin {bpatch}\n"
         "               [0] : struct.begin {bpatch}\n"
         "                  MinSpawnChance = 0.9f\n"
         "                  MaxSpawnChance = 0.95f\n"
         "               struct.end\n            struct.end\n"
         "         struct.end\n      struct.end\n   struct.end\nstruct.end\n"},
        mods / "StashChance_P.pak")

    paks = modscan.find_mod_paks(mods, {"zzz_S2Tweaker_P.pak"})
    names = [p.name for p in paks]
    assert "zzz_S2Tweaker_P.pak" not in names
    assert "FakeLoot_P.pak" in names, "Unterordner-Pak nicht gefunden"
    print("found paks:", len(paks))

    infos = [modscan.scan_pak(p, vanilla_index=vanilla_index) for p in paks]
    by = {i.name: i for i in infos}

    io = by["BigOverhaul_P"]
    assert not io.readable and "can't read" in io.note
    assert len(io.note) < 160, f"Fehlertext zu lang: {len(io.note)}"

    assert by["OfficialStyle_P"].n_cfg == 1, by["OfficialStyle_P"].note
    assert ("Hard", "Weapon_BaseDamage") in by["OfficialStyle_P"].pairs
    print("offizielles Namensschema erkannt  OK")

    assert ("Player", "MaxHP") in by["LegacyMod_P"].pairs, \
        sorted(by["LegacyMod_P"].pairs)
    print("Legacy-refkey unter freiem Namen aufgeloest  OK")

    assert ("Player", "MaxSP") in by["BracketMod_P"].pairs, \
        (by["BracketMod_P"].pairs, by["BracketMod_P"].note)
    print("Glob-Klammern im Pfad ueberlebt  OK")

    vc = by["VanillaCopy_P"]
    print(f"Vanilla-Vollkopie: {len(vc.pairs)} Paare uebrig")

    conflicts = match(infos)
    print("\nconflicts:")
    for k, v in sorted(conflicts.items()):
        print(f"   {k:16} <- {v}")

    def marked_by(key, mod):
        return mod in conflicts.get(key, [])

    assert marked_by("pdmg", "zzz_FakeOverhaul_P")
    assert marked_by("npchp", "zzz_FakeOverhaul_P")
    assert marked_by("npc_vision", "zzz_FakeOverhaul_P")
    assert marked_by("loot_amount", "FakeLoot_P")
    assert marked_by("pdmg", "OfficialStyle_P"), "offizielles Schema ohne Treffer"
    assert marked_by("hp", "LegacyMod_P"), "Legacy-refkey ohne Treffer"
    assert marked_by("sp", "BracketMod_P"), "Klammer-Pfad ohne Treffer"
    assert marked_by("loot_amount", "FreeNameLoot_P"), \
        "frei benannte Loot-Datei nicht markiert (Guard zu eng)"
    assert marked_by("stash_chance", "StashChance_P"), \
        "Fundchance am Deckel nicht markiert (Sonde nur x2?)"
    assert not any("VanillaCopy_P" in v for v in conflicts.values()), \
        f"Vanilla-Vollkopie markiert: {[k for k,v in conflicts.items() if 'VanillaCopy_P' in v]}"
    assert not marked_by("npc_hearing", "FactionMod_P"), "Type-Anker-Kollision"
    assert not marked_by("mhearing", "FactionMod_P")
    assert not marked_by("weight", "PackMod_P"), "Lotterie-Weight-Kollision"
    assert "hp" not in conflicts or "zzz_FakeOverhaul_P" not in conflicts["hp"]

print("\nMODSCAN-TEST OK")
