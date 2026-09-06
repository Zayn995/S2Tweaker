"""1.24.0-Paket (06.09.2026): Artefakt-Slots je Ruestung, Kamerawackeln beim
Schiessen, ADS-Zoom, Klettertempo, Startgeld, Aim-Assist-Schalter fuer Maus
und Gamepad. Sollwerte live aus vanilla/; Anker sind nur die bekannten
Vanilla-Groessen (Slots 0-5, Scale 1.0, FOV 0.92/0.83, ClimbSpeedCoef 0.6,
PlayerStartingMoney 0, Empty-Kegel).
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
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
SHAKE = "CameraShakePrototypes/CameraShakePrototypes_patch_S2Tweaker.cfg"
SETUP = "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg"
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
AIM = "AimAssistPresetPrototypes/AimAssistPresetPrototypes_patch_S2Tweaker.cfg"


def parsed(patches, name):
    return cfgparse.parse(patches[name]) if name in patches else None


def values(node, key):
    out = {}
    for sid, child in node.children.items():
        if key in child.values:
            out[sid] = child.values[key]
    return out


# --- 0) Neutral: keine der neuen Dateien/Schluessel --------------------
neutral = build_patches(gd, Settings(mod_name="S2Tweaker"))
assert AIM not in neutral, "Aim-Assist-Patch ohne Schalter"
for name in (ITEMS, SHAKE, SETUP, OBJ, CORE):
    text = neutral.get(name, "")
    for key in ("ArtifactSlots", "ShootCameraShake", "AimingFOVModifier",
                "ClimbSpeedCoef", "PlayerStartingMoney"):
        assert key not in text, f"{key} im Neutralzustand ({name})"
print("Neutral: keine 1.24.0-Schluessel  OK")

# --- 1) Artefakt-Slots: +2, Deckel 5, Helme unberuehrt ------------------
slots = gd.armor_artifact_slots()
assert 40 <= len(slots) <= 120, len(slots)
assert all(0 <= v <= 5 for v, _ed in slots.values())
p = build_patches(gd, Settings(mod_name="S2Tweaker", artifact_slots_bonus=2))
got = values(parsed(p, ITEMS), "ArtifactSlots")
checked = 0
for sid, (vanilla, edition) in slots.items():
    if edition is not None:
        continue                     # Editions-Ruestungen liegen im DLC-Zweig
    expected = min(5, vanilla + 2)
    if expected == vanilla:
        assert sid not in got, f"{sid}: 5-Slot-Ruestung wurde gepatcht"
    else:
        assert got.get(sid) == str(expected), (sid, vanilla, got.get(sid))
        checked += 1
assert checked >= 35, checked
helmets = [sid for sid, (slot, _v) in gd.player_armors().items() if slot == "Head"]
assert helmets and not any(h in got for h in helmets), "Helm gepatcht"
five = [sid for sid, (v, ed) in slots.items() if v == 5 and ed is None]
assert five and not any(sid in got for sid in five)
dlc_names = [n for n in p if n.startswith("//GameLite/DLCGameData/")]
if any(ed for _v, ed in slots.values()):
    assert any("ArtifactSlots" in p[n] for n in dlc_names), "DLC-Ruestungen ohne Slot-Patch"
print(f"Artefakt-Slots: {checked} Ruestungen +2 (Deckel 5), {len(helmets)} Helme unberuehrt  OK")

# --- 2) Kamerawackeln beim Schiessen ------------------------------------
p = build_patches(gd, Settings(mod_name="S2Tweaker", shooting_shake_factor=0.5))
got = values(parsed(p, SHAKE), "Scale")
shoot = [n for n in gd.camerashake.children
         if n == "ShootingCameraShake" or n.endswith("ShootCameraShake")]
assert len(shoot) >= 30, len(shoot)
for name in shoot:
    vanilla = parse_number(gd.camerashake.children[name].get("Scale"), 1.0)
    assert abs(parse_number(got[name]) - vanilla * 0.5) < 1e-6, (name, got.get(name))
assert set(got) == set(shoot), set(got) ^ set(shoot)
assert "ProjectileHitCameraShake" not in got, "Aim Punch ohne Regler mitgepatcht"
p2 = build_patches(gd, Settings(mod_name="S2Tweaker", shooting_shake_factor=0.5, aim_punch_factor=2.0))
got2 = values(parsed(p2, SHAKE), "Scale")
assert "ProjectileHitCameraShake" in got2 and len(got2) == len(shoot) + 1
print(f"Kamerawackeln: {len(shoot)} Schuss-Eintraege halbiert, Treffer-Wackeln getrennt  OK")

# --- 3) ADS-Zoom: 0 = kein Zoom, 2 = doppelt, Deckel 0.2 ----------------
fov = gd.weapon_general_values("AimingFOVModifier")
assert len(fov) >= 80, len(fov)
p0 = build_patches(gd, Settings(mod_name="S2Tweaker", ads_zoom_factor=0.0))
got0 = values(parsed(p0, SETUP), "AimingFOVModifier")
assert set(got0) == set(fov) and all(parse_number(v) == 1.0 for v in got0.values())
p2 = build_patches(gd, Settings(mod_name="S2Tweaker", ads_zoom_factor=2.0))
got2 = values(parsed(p2, SETUP), "AimingFOVModifier")
for sid, vanilla in fov.items():
    expected = max(0.2, 1.0 - (1.0 - vanilla) * 2.0)
    assert abs(parse_number(got2[sid]) - expected) < 1e-6, (sid, vanilla, got2[sid])
off = values(parsed(p2, SETUP), "OffsetAimingFOVModifier")
assert len(off) >= 80, len(off)
print(f"ADS-Zoom: {len(fov)} Waffen, 0 % -> 1.0, 200 % -> 0.84 bei 0.92  OK")

# --- 4) Klettertempo ------------------------------------------------------
vanilla_climb = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.ClimbSpeedCoef"))
assert abs(vanilla_climb - 0.6) < 1e-6, vanilla_climb
p = build_patches(gd, Settings(mod_name="S2Tweaker", climb_speed_factor=2.0))
climb = parsed(p, OBJ).children["Player"].children["MovementParams"].values["ClimbSpeedCoef"]
assert abs(parse_number(climb) - 1.2) < 1e-6, climb
print("Klettertempo: 0.6 -> 1.2  OK")

# --- 5) Startgeld ----------------------------------------------------------
assert gd.corevar("PlayerStartingMoney", -1.0) == 0.0
p = build_patches(gd, Settings(mod_name="S2Tweaker", starting_money=5000))
assert "PlayerStartingMoney = 5000" in p[CORE], p[CORE]
assert "PlayerStartingMoney" not in build_patches(gd, Settings(mod_name="S2Tweaker", starting_money=0)).get(CORE, "")
print("Startgeld: 0 -> 5000  OK")

# --- 6) Aim Assist: Maus und Gamepad getrennt ----------------------------
presets = [n for n in gd.aimassist.children if "#" not in n and n != "Empty"]
mouse = [n for n in presets if "Mouse" in n]
pad = [n for n in presets if "Gamepad" in n]
assert len(mouse) == 2 and len(pad) >= 10, (mouse, len(pad))
empty = gd.aimassist.children["Empty"].values["StickinessAimAssistConeSID"].strip()
p = build_patches(gd, Settings(mod_name="S2Tweaker", no_aim_assist_mouse=True))
node = parsed(p, AIM)
assert set(node.children) == set(mouse), set(node.children)
for name in mouse:
    cfg = node.children[name]
    assert cfg.values.get("StickinessAimAssistConeSID", "").strip() == empty
    magnet = cfg.children.get("MagnetismAimAssistConeSIDs")
    assert magnet is not None and all(v.strip() == empty for v in magnet.values.values())
    assert "SnappingAimAssistConeSID" not in cfg.values, "Snapping war schon Empty - darf nicht auftauchen"
p = build_patches(gd, Settings(mod_name="S2Tweaker", no_aim_assist_gamepad=True))
node = parsed(p, AIM)
assert set(node.children) == set(pad), set(node.children) ^ set(pad)
p = build_patches(gd, Settings(mod_name="S2Tweaker", no_aim_assist_mouse=True, no_aim_assist_gamepad=True))
assert set(parsed(p, AIM).children) == set(mouse) | set(pad)
print(f"Aim Assist: {len(mouse)} Maus- und {len(pad)} Gamepad-Presets getrennt auf {empty}  OK")

# --- 7) Zusammenfassung ---------------------------------------------------
text = summarize(Settings(mod_name="S2Tweaker", artifact_slots_bonus=1, shooting_shake_factor=0.0,
                          ads_zoom_factor=0.0, climb_speed_factor=1.5, starting_money=1000,
                          no_aim_assist_mouse=True, no_aim_assist_gamepad=True))
joined = "\n".join(text) if isinstance(text, (list, tuple)) else str(text)
for needle in ("Artifact slots +1", "Shooting camera shake", "ADS zoom", "Ladder climb speed",
               "Starting money 1000", "Aim assist off (mouse)", "Aim assist off (gamepad)"):
    assert needle in joined, needle
print("Zusammenfassung nennt alle sieben  OK")

print("\nV124-TEST OK")
