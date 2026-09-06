"""1.25.0-Paket (06.09.2026): Dialog-/Cutscene-/Standard-FOV, HUD-Schalter je
Schwierigkeitsgrad, Leichen-Zeiten und -Hoechstzahl, Wetterdauer,
Geschossabfall, Geschoss-Geschwindigkeit, Pistolenslot, Mutantenschutz,
Schlaf. Sollwerte live aus vanilla/; Anker sind nur die bekannten
Vanilla-Groessen (FOV 70/90/90, Corpse 1800/900/300/1800/6000 + 10,
BulletDropHeight 170, Speed 20000-42000, MinSleepHours 7, Slots 99/20).
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
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
DIFF = "DifficultyPrototypes/DifficultyPrototypes_patch_S2Tweaker.cfg"
WEATHER = "WeatherSelectionPrototypes/WeatherSelectionPrototypes_patch_S2Tweaker.cfg"
CWS = "WeaponData/CharacterWeaponSettingsPrototypes/CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg"
PROJ = "ProjectilePrototypes/ProjectilePrototypes_patch_S2Tweaker.cfg"
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
SLEEP = "ObjSleepParamsPrototypes/ObjSleepParamsPrototypes_patch_S2Tweaker.cfg"


def parsed(patches, name):
    return cfgparse.parse(patches[name]) if name in patches else None


def S(**kw):
    return Settings(mod_name="S2Tweaker", **kw)


# --- 0) Neutral -----------------------------------------------------------
neutral = build_patches(gd, S())
for name in (PROJ, SLEEP, WEATHER):
    assert name not in neutral, name
for name, keys in ((CORE, ("FOVDefault", "Corpse")), (DIFF, ("bShouldDisable",)),
                   (CWS, ("BulletDrop",)), (ITEMS, ("ItemSlotType",)), (OBJ, ("Protection",))):
    text = neutral.get(name, "")
    assert not any(k in text for k in keys), (name, keys)
print("Neutral: keine 1.25.0-Schluessel  OK")

# --- 1) FOV ----------------------------------------------------------------
assert (gd.corevar("DialogFOVDefault"), gd.corevar("CutsceneFOVDefault"), gd.corevar("FOVDefault")) == (70.0, 90.0, 90.0)
core = parsed(build_patches(gd, S(dialog_fov=90, cutscene_fov=100, default_fov=110)), CORE).children["DefaultConfig"].values
assert (core["DialogFOVDefault"], core["CutsceneFOVDefault"], core["FOVDefault"]) == ("90.0", "100.0", "110.0"), core
assert "FOV" not in build_patches(gd, S(dialog_fov=70, cutscene_fov=90, default_fov=90)).get(CORE, "")
print("FOV: 70/90/90 -> 90/100/110, Vanilla-Werte erzeugen nichts  OK")

# --- 2) HUD-Schalter: je Grad nur die Abweichung -------------------------
levels = [sid for sid in gd.difficulty.children if sid != "[0]" and "#" not in sid]
stalker = [sid for sid in levels if sid.startswith("Stalker")]
assert len(levels) >= 10 and len(stalker) == 2, (len(levels), stalker)
p = build_patches(gd, S(hud_compass=1))
node = parsed(p, DIFF)
assert set(node.children) == set(stalker), set(node.children)
assert all(node.children[sid].children["EnvironmentDifficulty"].values["bShouldDisableCompass"] == "false" for sid in stalker)
p = build_patches(gd, S(hud_crosshair=2))
node = parsed(p, DIFF)
assert set(node.children) == set(levels) - set(stalker), set(node.children) ^ (set(levels) - set(stalker))
assert all(c.children["EnvironmentDifficulty"].values["bShouldDisableCrosshair"] == "true" for c in node.children.values())
p = build_patches(gd, S(hud_body_markers=2, hud_stash_markers=1))
text = p[DIFF]
assert text.count("bShouldDisableDeadBodyMarkers = true") == len(levels) - 2 and text.count("bShouldDisableStashMarkers = false") == 2
print(f"HUD: {len(levels)} Grade, Master-Paar {stalker}, nur Abweichungen  OK")

# --- 3) Leichen ------------------------------------------------------------
core = parsed(build_patches(gd, S(corpse_time_factor=2.0, corpse_max_count=25)), CORE).children["DefaultConfig"].values
assert core["CorpseOnlineTime"] == "3600.0" and core["CorpseSeenOnlineTime"] == "1800.0", core
assert core["CorpseLootedOnlineTime"] == "600.0" and core["CorpseALifeOnlineTime"] == "3600.0", core
assert core["CorpseTimeout"] == "12000", core["CorpseTimeout"]
assert core["CorpseConditionOnlineCount"] == "25"
assert "Corpse" not in build_patches(gd, S(corpse_max_count=10)).get(CORE, "")
print("Leichen: Zeiten x2 (Literalform erhalten), Hoechstzahl 25  OK")

# --- 4) Wetterdauer --------------------------------------------------------
p = build_patches(gd, S(weather_duration_factor=2.0))
root = parsed(p, WEATHER)
vanilla_root = gd.weatherselection
checked = 0
for sid, node in root.children.items():
    for wtype, sub in node.children.items():
        for key in ("WeatherDurationMin", "WeatherDurationMax"):
            if key not in sub.values:
                continue
            van = gd.resolve(vanilla_root, sid, f"{wtype}.{key}")
            if van is None or parse_number(van) <= 0:
                continue
            assert abs(parse_number(sub.values[key]) - 2 * parse_number(van)) < 1e-6, (sid, wtype, key, sub.values[key], van)
            assert sub.values[key].endswith("f") == van.strip().endswith("f")
            checked += 1
assert checked >= 300, checked
print(f"Wetterdauer: {checked} Min/Max-Werte verdoppelt, Suffix erhalten  OK")

# --- 5) Geschossabfall -----------------------------------------------------
p = build_patches(gd, S(bullet_drop_factor=0.0))
cws = parsed(p, CWS)
heights = {sid: c.values["BulletDropHeight"] for sid, c in cws.children.items() if "BulletDropHeight" in c.values}
assert len(heights) >= 8 and all(parse_number(v) == 0 for v in heights.values()), heights
assert "TemplateWeapon" in heights and not any(sid.endswith("_NPC") for sid in heights), sorted(heights)[:5]
vanilla_h = parse_number(gd.weaponsettings.children["TemplateWeapon"].values["BulletDropHeight"])
assert vanilla_h == 170.0, vanilla_h
p = build_patches(gd, S(bullet_drop_factor=0.5))
assert parsed(p, CWS).children["TemplateWeapon"].values["BulletDropHeight"] == "85.0"
print(f"Geschossabfall: {len(heights)} Vorlagen, 170 -> 0 / 85, NPC-Settings unberuehrt  OK")

# --- 6) Geschoss-Geschwindigkeit -------------------------------------------
p = build_patches(gd, S(bullet_speed_factor=2.0))
proj = parsed(p, PROJ)
assert 8 <= len(proj.children) <= 14, len(proj.children)
for sid, c in proj.children.items():
    van = parse_number(gd.projectiles.children[sid].values["Speed"])
    assert 10000 <= van < 1_000_000 and abs(parse_number(c.values["Speed"]) - 2 * van) < 1e-6, (sid, van)
assert not any(sid in proj.children for sid in ("PGA", "PPG7V", "PHEDP", "PVOG", "empty"))
print(f"Geschoss-Geschwindigkeit: {len(proj.children)} Kugeln x2, Gauss/RPG/Granaten unberuehrt  OK")

# --- 7) Pistolenslot -------------------------------------------------------
weapons = gd.slot_weapon_items()
base = {sid: v for sid, v in weapons.items() if v[2] is None}
assert sum(1 for v in base.values() if v[1] == "PrimaryWeapon") >= 90 and sum(1 for v in base.values() if v[1] == "Pistol") >= 15
literal = gd.pistol_slot_literal()
assert literal and literal.endswith("::Pistol"), literal
p = build_patches(gd, S(pistol_slot_level=1))
got = {sid: c.values["ItemSlotType"] for sid, c in parsed(p, ITEMS).children.items() if "ItemSlotType" in c.values}
smgs = {sid for sid, (cat, slot, ed) in base.items() if cat == "smg" and slot == "PrimaryWeapon"}
assert set(got) == smgs and all(v == literal for v in got.values()), (set(got) ^ smgs)
p = build_patches(gd, S(pistol_slot_level=3))
got3 = {sid for sid, c in parsed(p, ITEMS).children.items() if "ItemSlotType" in c.values}
assert got3 == {sid for sid, (cat, slot, ed) in base.items() if slot == "PrimaryWeapon"}
assert not any(sid in got3 for sid, (cat, slot, ed) in base.items() if slot == "Pistol")
print(f"Pistolenslot: Stufe 1 = {len(smgs)} MPs, Stufe 3 = {len(got3)} Hauptwaffen, Pistolen unberuehrt  OK")

# --- 8) Mutantenschutz -----------------------------------------------------
prot = gd.mutant_protections()
assert len(prot) >= 40, len(prot)
p = build_patches(gd, S(mutant_protection_factor=0.5))
obj = parsed(p, OBJ)
for sid, values in prot.items():
    node = obj.children[sid].children["Protection"]
    for key, van in values.items():
        assert abs(parse_number(node.values[key]) - van * 0.5) < 1e-6, (sid, key)
    assert "Shot" not in node.values, sid
p = build_patches(gd, S(mutant_overrides={"Bloodsucker": {"protection": 0.0}}))
obj = parsed(p, OBJ)
bs = [sid for sid in prot if gd.mutant_faction(sid) == "Bloodsucker"]
assert bs and all(parse_number(obj.children[sid].children["Protection"].values["Strike"]) == 0 for sid in bs)
assert not any(sid in obj.children for sid in prot if gd.mutant_faction(sid) != "Bloodsucker")
print(f"Mutantenschutz: {len(prot)} Prototypen x0.5, Art-Override Bloodsucker -> 0  OK")

# --- 9) Schlaf --------------------------------------------------------------
sleep = parsed(build_patches(gd, S(sleep_anytime=True, min_sleep_hours=2, sleep_in_emission=True)), SLEEP)
v = sleep.children["DefaultSleepParams"].values
assert v == {"AllowSleepThreshold": "0", "MinSleepHours": "2", "bAllowEmissionSleep": "true"}, v
assert SLEEP not in build_patches(gd, S(min_sleep_hours=7))
print("Schlaf: Schwelle 0, 2 h, Emission erlaubt  OK")

# --- 10) Zusammenfassung ---------------------------------------------------
joined = "\n".join(summarize(S(dialog_fov=80, hud_crosshair=2, corpse_time_factor=2.0, corpse_max_count=20,
                               weather_duration_factor=0.5, bullet_drop_factor=0.0, bullet_speed_factor=2.0,
                               pistol_slot_level=3, mutant_protection_factor=0.0, sleep_anytime=True,
                               min_sleep_hours=3, sleep_in_emission=True)))
for needle in ("Dialog FOV 80", "Crosshair always hidden", "Bodies stay", "Max bodies near you 20",
               "Weather duration", "Bullet drop", "Bullet speed", "Pistol slot accepts any weapon",
               "Mutant physical protection", "Sleep whenever you like", "Minimum sleep 3 h",
               "Sleeping during emissions allowed"):
    assert needle in joined, needle
print("Zusammenfassung nennt alle zwoelf  OK")

print("\nV125-TEST OK")
