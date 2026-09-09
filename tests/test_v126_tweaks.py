"""1.26.0-Paket (06.09.2026, Recherche auf anderen Mod-Seiten): 26 neue
Stellschrauben. Sollwerte live aus vanilla/; Anker sind nur die bekannten
Vanilla-Groessen (siehe docs/ROADMAP.md "Vierte Datenrecherche").
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker import cfgparse                       # noqa: E402
from s2tweaker.cfgparse import parse_number          # noqa: E402
from s2tweaker.gamedata import GameData              # noqa: E402
from s2tweaker.tweaks import Settings, build_patches, summarize  # noqa: E402

gd = GameData(VANILLA)
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
POST = "PostEffectProcessorPrototypes/PostEffectProcessorPrototypes_patch_S2Tweaker.cfg"
EFF = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"
CWS = "WeaponData/CharacterWeaponSettingsPrototypes/CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg"
EXPL = "ExplosionPrototypes/ExplosionPrototypes_patch_S2Tweaker.cfg"
ABIL = "AbilityPrototypes/AbilityPrototypes_patch_S2Tweaker.cfg"
WGS = "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg"
GEN = "ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_S2Tweaker.cfg"
CLUE = "CorpseClueStashPrototypes/CorpseClueStashPrototypes_patch_S2Tweaker.cfg"
MARK = "MarkerPrototypes/MarkerPrototypes_patch_S2Tweaker.cfg"
FT = "FastTravelPrototypes/FastTravelPrototypes_patch_S2Tweaker.cfg"
EMAX = "ObjEffectMaxParamsPrototypes/ObjEffectMaxParamsPrototypes_patch_S2Tweaker.cfg"
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
QUEST = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"
TRADE = "TradePrototypes/TradePrototypes_patch_S2Tweaker.cfg"
ANOM = "AnomalyPrototypes/AnomalyPrototypes_patch_S2Tweaker.cfg"


def parsed(patches, name):
    return cfgparse.parse(patches[name]) if name in patches else None


def S(**kw):
    return Settings(mod_name="S2Tweaker", **kw)


# --- 0) Neutral -----------------------------------------------------------
neutral = build_patches(gd, S())
for name in (POST, EXPL, CLUE, MARK, ANOM, FT, EMAX, QUEST, ABIL):
    assert name not in neutral, name
for name, keys in ((OBJ, ("CanBeKnockedDown", "WaterContactInfo", "ShouldTriggerAnomalies", "CanProcessCorpses")),
                   (CORE, ("ClimbView", "HandlessFOV", "ALifeGrid", "ViewPitchDown")),
                   (EFF, ("ButtStroke", "KillVolume", "TeleportType", "ClickerAnomalyHit", "SpawnPSYPhantoms")),
                   (WGS, ("ReloadTime", "FullJamTime")), (CWS, ("GuardGun",)),
                   (TRADE, ("BuyLimitations",)), (ITEMS, ("AArtifactWeird",))):
    text = neutral.get(name, "")
    assert not any(k in text for k in keys), (name, keys)
print("Neutral: keine 1.26.0-Schluessel  OK")

# --- 1) Spieler: nicht umwerfbar, kein Wasser-Schleichgang ----------------
player = parsed(build_patches(gd, S(no_knockdown=True, no_water_slowdown=True)), OBJ).children["Player"]
assert player.values["CanBeKnockedDown"] == "false"
water = player.children["WaterContactInfo"]
emptied = [e for grp in water.children.values() for e in grp.children.values()]
assert len(emptied) == 3 and all(e.values["EffectSID"] == "empty" for e in emptied), len(emptied)
print("Spieler: CanBeKnockedDown false, 3 Wasser-Effekte geleert  OK")

# --- 2) CoreVariables: Leiter, nach unten, Zoom, A-Life-Sicht ------------
assert (gd.corevar("ClimbViewYawLimit"), gd.corevar("ClimbViewPitchLimit"), gd.corevar("ViewPitchDownLimit"),
        gd.corevar("HandlessFOVAimModifier"), gd.corevar("ALifeGridVisionRadius"),
        gd.corevar("GenericModelGridVisionRadius")) == (30.0, 40.0, -80.0, 0.8, 8500.0, 7500.0)
core = parsed(build_patches(gd, S(ladder_free_look=True, look_straight_down=True, handless_zoom_factor=0.5,
                                  alife_vision_factor=2.0)), CORE).children["DefaultConfig"].values
# 1.36.0: "Free look on ladders" ist zurueckgezogen (GitHub #11, craigduk76:
# dieselbe Pak, dasselbe Struct, ViewPitchDownLimit wirkte, die zwei
# Leiter-Schluessel nicht). Das Feld existiert noch, schreibt aber nichts.
assert "ClimbViewYawLimit" not in core and "ClimbViewPitchLimit" not in core, core
assert core["ViewPitchDownLimit"] == "-90.0" and core["HandlessFOVAimModifier"] == "0.4"
assert core["ALifeGridVisionRadius"] == "17000.0" and core["GenericModelGridVisionRadius"] == "15000.0"
core = parsed(build_patches(gd, S(handless_zoom_factor=0.1)), CORE).children["DefaultConfig"].values
assert core["HandlessFOVAimModifier"] == "0.2", core            # Deckel
print("CoreVariables: Leiter 90/90, -90, Zoom 0.4 (Deckel 0.2), A-Life 17000/15000  OK")

# --- 3) Duck-Vignette -----------------------------------------------------
post = parsed(build_patches(gd, S(crouch_vignette_factor=0.5)), POST).children["CrouchEffectProcessor"].values
assert post["Intensity"] == "0.3", post
post = parsed(build_patches(gd, S(crouch_vignette_factor=2.0)), POST).children["CrouchEffectProcessor"].values
assert post["Intensity"] == "1.0", post
print("Vignette: 0.6 -> 0.3, Deckel 1.0  OK")

# --- 4) EffectPrototypes: Kolben, Wachen, Psy, Teleports, Klicker --------
eff = parsed(build_patches(gd, S(butt_wear_factor=0.0, guards_no_instakill=True, psy_phantoms_only=True,
                                 instant_teleports=True, clicker_factor=0.5)), EFF)
butt = eff.children["ButtStroke_Corrosion"].values
assert butt["ValueMin"] == "0.0f" and butt["ValueMax"] == "0.0f", butt
kill = eff.children["KillVolumeEffect"].children["ApplyExtraEffectPrototypeSIDs"].values
assert kill == {"[0]": "empty", "[1]": "empty", "[2]": "empty"}, kill
assert eff.children["ConditionalSpawnPSYNPC"].values["FalseEffectSID"] == "SpawnPSYPhantoms"
vanilla_teleports = [sid for sid, n in gd.effects.children.items()
                     if n.values.get("TeleportType", "").strip() not in ("", "EGSCTeleportType::Instant")]
tele = [sid for sid, n in eff.children.items() if n.values.get("TeleportType") == "EGSCTeleportType::Instant"]
assert len(vanilla_teleports) >= 8 and sorted(tele) == sorted(vanilla_teleports), (len(tele), len(vanilla_teleports))
assert eff.children["ClickerAnomalyHit"].values["ValueMin"] == "35.0"
print(f"Effekte: Kolben 0, KillVolume geleert, Psy-Phantome, {len(tele)} Teleports instant, Klicker 35  OK")

# --- 5) ObjPrototypes-Schalter: Anomalien, Leichen ------------------------
obj = parsed(build_patches(gd, S(mutants_trigger_anomalies=True)), OBJ)
for sid in ("Bloodsucker", "Chimera", "Controller", "Poltergeist", "PseudoDog", "Pseudogiant"):
    assert obj.children[sid].values["ShouldTriggerAnomalies"] == "true", sid
for sid in ("Boar", "Flesh", "Snork", "Player", "NPCBase"):
    assert sid not in obj.children, sid
obj = parsed(build_patches(gd, S(npcs_no_corpse_loot=True)), OBJ)
assert obj.children["NPCBase"].values["CanProcessCorpses"] == "false"
assert "Bloodsucker" not in obj.children and "Player" not in obj.children
assert len(obj.children) > 100, len(obj.children)
print(f"Obj-Schalter: immune Arten -> true, {len(obj.children)} menschliche NPCs pluendern nicht  OK")

# --- 6) Wachen: BaseDamage der normalen NPC-Waffe -------------------------
cws = parsed(build_patches(gd, S(guards_no_instakill=True)), CWS)
guards = [sid for sid in cws.children if sid.startswith("GuardGun")]
assert len(guards) == 32, len(guards)
assert cws.children["GuardGunAK74_ST_NPC"].values["BaseDamage"] == "9.5"
assert parse_number(gd.resolve(gd.weaponsettings, "GuardGunAK74_ST_NPC", "BaseDamage")) == 500.0
print("Wachen: 32 GuardGun-Structs, AK 500 -> 9.5  OK")

# --- 7) Explosionen -------------------------------------------------------
ex = parsed(build_patches(gd, S(explosion_radius_factor=2.0, explosion_npc_damage_factor=0.5)), EXPL)
rgd = ex.children["ExplosionRGD5"].values
assert (rgd["Radius"], rgd["ImpulseRadius"], rgd["ConcussionRadius"], rgd["DamageNPC"]) == ("1400.0", "1100.0", "1300.0", "130.0"), rgd
assert "Empty" not in ex.children and "ExplosionPG7V" in ex.children
print("Explosionen: RGD5 Radius 700 -> 1400, DamageNPC 260 -> 130  OK")

# --- 8) Pseudohund-Phantome -----------------------------------------------
ab = parsed(build_patches(gd, S(phantom_dog_damage_factor=0.0)), ABIL)
base = ab.children["PseudoDogSummon_RunAttack_Base"].values
assert base["Damage"] == "0.0" and base["Bleeding"] == "0.0f", base
print("Phantome: Damage 5 -> 0, Bleeding 10 -> 0  OK")

# --- 9) Nachladen / Klemmer -----------------------------------------------
wgs = parsed(build_patches(gd, S(reload_speed_factor=2.0, jam_clear_factor=2.0)), WGS)
reload_rows = [e for n in wgs.children.values() if "WeaponReloadTimePerAttachment" in n.children
               for e in n.children["WeaponReloadTimePerAttachment"].children.values()]
RELOAD_KEYS = ("TacticalReloadTimeMultiplier", "FullReloadTimeMultiplier", "SingleBulletReloadTimeMultiplier",
               "TwinReloadTimeMultiplier", "TwinTacticalReloadTimeMultiplier")
assert len(reload_rows) >= 100, len(reload_rows)
assert all(set(e.values) <= set(RELOAD_KEYS) and set(e.values.values()) == {"0.5"} for e in reload_rows)
assert sum(1 for e in reload_rows if "TacticalReloadTimeMultiplier" in e.values) >= 100
jam_rows = [e for n in wgs.children.values() if "WeaponJamParams" in n.children
            for e in n.children["WeaponJamParams"].children.values()]
assert len(jam_rows) >= 50 and any(e.values["FullJamTime"] == "2.5" for e in jam_rows), len(jam_rows)
assert not any(e.values["FullJamTime"] == "0.0" for e in jam_rows)
assert "[0]" not in wgs.children
print(f"Nachladen: {len(reload_rows)} Magazin-Eintraege 1.0 -> 0.5, {len(jam_rows)} Klemmer-Zeiten halbiert  OK")

# --- 10) Mutanten-Trophaeen -------------------------------------------------
gen = parsed(build_patches(gd, S(mutant_loot_chance_factor=2.0)), GEN)
blind = gen.children["BlinddogLootGenerator"].children["ItemGenerator"].children["[0]"].children["PossibleItems"].children["[0]"].values
assert blind["Chance"] == "0.3", blind
assert "ChimeraLootGenerator" not in gen.children          # schon 1.0
gen = parsed(build_patches(gd, S(mutant_loot_chance_factor=10.0)), GEN)
assert gen.children["BlinddogLootGenerator"].children["ItemGenerator"].children["[0]"].children["PossibleItems"].children["[0]"].values["Chance"] == "1.0"
print("Trophaeen: Blinddog 0.15 -> 0.3, Deckel 1.0, Chimaere unangetastet  OK")

# --- 11) Versteck-Hinweise -------------------------------------------------
clue = parsed(build_patches(gd, S(stash_clue_factor=2.0)), CLUE)
assert len(clue.children) == 24, len(clue.children)
assert clue.children["Default"].values == {"BaseSpawnChance": "0.04", "AddSpawnChance": "0.02"}
print("Versteck-Hinweise: 24 Regionen, 0.02/0.01 -> 0.04/0.02  OK")

# --- 12) PDA-Karte ----------------------------------------------------------
mark = parsed(build_patches(gd, S(map_reveal_factor=2.0)), MARK)
assert len(mark.children) >= 300, len(mark.children)
assert any(n.values.get("MarkerRevealDistance") == "20000.0" and n.values.get("MarkerExploreDistance") == "4000.0"
           for n in mark.children.values())
mark = parsed(build_patches(gd, S(map_all_regions=True)), MARK)
assert len(mark.children) == 23 and all(n.values["InitDiscoverState"] == "EMarkerState::Explored"
                                        for n in mark.children.values()), len(mark.children)
print("Karte: Distanzen verdoppelt, 23 Regionen sichtbar  OK")

# --- 13) Schnellreise -------------------------------------------------------
ft = parsed(build_patches(gd, S(fast_travel_lock=0, guide_delay_factor=0.5)), FT)
assert len(ft.children) == 14, len(ft.children)
assert all(n.values["OverweightLock"] == "EOverweightLock::NoLock" and n.values["GuideDelay"] == "60.0"
           for n in ft.children.values())
assert parsed(build_patches(gd, S(fast_travel_lock=1)), FT).children["[1]"].values["OverweightLock"] == "EOverweightLock::Partial"
assert FT not in build_patches(gd, S(fast_travel_lock=2))
print("Schnellreise: 14 Guides NoLock/Partial, GuideDelay 120 -> 60  OK")

# --- 14) Schutz-Deckel ------------------------------------------------------
emax = parsed(build_patches(gd, S(protection_cap_factor=1.5)), EMAX)
entries = emax.children["DefaultEffectMaxParamsSID"].children["MaxEffectValues"].children
by_kind = {e.values["EffectSID"]: e.values["MaxValue"] for e in entries.values()}
assert by_kind["EEffectType::ProtectionShock"] == "100.0f" and by_kind["EEffectType::ProtectionStrike"] == "6.75f"
assert by_kind["EEffectType::ProtectionRadiation"] == "100.0f" and "EEffectType::PenaltyLessWeight" not in by_kind
carry_only = parsed(build_patches(gd, S(max_carry_weight=160.0)), EMAX)
assert set(carry_only.children["DefaultEffectMaxParamsSID"].children["MaxEffectValues"].children) == {"[1]", "[9]"}
print("Schutz-Deckel: 90 -> 100 (Deckel), Strike 4.5 -> 6.75, Tragegewicht-Pfad unveraendert  OK")

# --- 15) Weird-Artefakte ----------------------------------------------------
items = parsed(build_patches(gd, S(weird_artifact_factor=2.0)), ITEMS)
assert items.children["AArtifactWeirdFlower"].values["EffectsDuration"] == "14400.0f"
assert items.children["AArtifactWeirdBolt"].values["MaxCharge"] == "600.0"
print("Weird-Artefakte: Flower 7200 -> 14400, Bolt 300 -> 600  OK")

# --- 16) Intro ueberspringen -------------------------------------------------
quest = parsed(build_patches(gd, S(skip_intro=True)), QUEST)
conn = quest.children["E01_MQ01_PlayVideo"].children["Launchers"].children["[0]"].children["Connections"].children["[0]"]
assert conn.values["SID"] == "empty", conn.values
print("Intro: E01_MQ01_PlayVideo Startverbindung geleert  OK")

# --- 17) Haendler kaufen keine Ausruestung -----------------------------------
trade = parsed(build_patches(gd, S(traders_no_gear_buy=True)), TRADE)
basic = trade.children["BasicTrader"].children["TradeGenerators"].children["[0]"].children["BuyLimitations"].values
assert basic == {"[0]": "EItemType::Weapon", "[1]": "EItemType::Armor"}, basic
vanilla_gens = sum(len(n.children["TradeGenerators"].children) for sid, n in gd.trade.children.items()
                   if sid != "[0]" and "TradeGenerators" in n.children)
patched_gens = sum(len(n.children["TradeGenerators"].children) for n in trade.children.values())
assert patched_gens < vanilla_gens, (patched_gens, vanilla_gens)   # die mit Weapon+Armor bleiben unangetastet
for n in trade.children.values():
    for gen_node in n.children["TradeGenerators"].children.values():
        vals = list(gen_node.children["BuyLimitations"].values.values())
        assert "EItemType::Weapon" in vals and "EItemType::Armor" in vals and len(vals) == len(set(vals))
print(f"Haendler: {patched_gens} von {vanilla_gens} Generatoren ergaenzt, vorhandene Sperren bleiben  OK")

# --- 18) Klicker-Anomalie ---------------------------------------------------
an = parsed(build_patches(gd, S(clicker_factor=0.5)), ANOM)
assert an.children["ClickerAnomaly"].values["ParticleMaxCount"] == "10"
assert parsed(build_patches(gd, S(clicker_factor=0.0)), ANOM).children["ClickerAnomaly"].values["ParticleMaxCount"] == "1"
print("Klicker: 20 -> 10, Minimum 1  OK")

# --- 19) Zusammenfassung ---------------------------------------------------
joined = "\n".join(summarize(S(no_knockdown=True, no_water_slowdown=True, ladder_free_look=True, look_straight_down=True,
                               handless_zoom_factor=0.5, crouch_vignette_factor=0.0, butt_wear_factor=0.0,
                               mutants_trigger_anomalies=True, guards_no_instakill=True, explosion_radius_factor=2.0,
                               explosion_npc_damage_factor=0.5, phantom_dog_damage_factor=0.0, psy_phantoms_only=True,
                               reload_speed_factor=2.0, jam_clear_factor=2.0, mutant_loot_chance_factor=10.0,
                               stash_clue_factor=2.0, npcs_no_corpse_loot=True, alife_vision_factor=2.0,
                               map_reveal_factor=2.0, map_all_regions=True, fast_travel_lock=0, guide_delay_factor=0.0,
                               instant_teleports=True, protection_cap_factor=1.5, weird_artifact_factor=2.0,
                               skip_intro=True, traders_no_gear_buy=True, clicker_factor=0.0)))
for needle in ("knocked down", "water", "straight down", "Hands-free zoom", "Crouch vignette", "Butt-strike",
               "trigger anomalies", "Base guards", "Explosion radius", "Explosion damage to NPCs", "Pseudodog phantom",
               "Psy fields", "Reload speed", "Jam clearing", "Mutant trophy", "Stash clues", "loot bodies",
               "visibility distance", "reveal distance", "region names", "overweight: allowed", "Guide delay",
               "Instant teleports", "Protection caps", "Weird artifact", "Intro video", "Traders don't buy",
               "Clicker"):
    assert needle in joined, needle
assert not any(k in "\n".join(summarize(S())) for k in ("knocked", "Reload", "Clicker"))
print("Zusammenfassung: 29 Zeilen vorhanden, neutral leer  OK")

print("\n1.26.0-TEST OK")
