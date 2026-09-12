"""Check additional control families introduced in 1.35.0 against live data.

Cover NPC damage, map markers, look rates, camera slowing, penetration and
artifact behavior. The inactive thirst mechanism remains excluded."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, input_ini,
                              parse_number, summarize)
from s2tweaker import cfgparse

gd = GameData(VANILLA)

CWS = "WeaponData/CharacterWeaponSettingsPrototypes/CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg"
NPCP = "NPCPrototypes/NPCPrototypes_patch_S2Tweaker.cfg"
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"
EFF = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"
PROJ = "ProjectilePrototypes/ProjectilePrototypes_patch_S2Tweaker.cfg"
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"

ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


def build(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


def nodes(patch_text):
    return cfgparse.parse(patch_text).children


print("\n0) Vanilla")
check(build() == {}, "Vanilla settings produce no files")

# Check the three NPC damage relationships.
print("\n1) NPC damage against player and allies")
live = {}
for key in ("NPCToNPCDamageScaler", "NPCToPlayerDamageScaler",
            "NPCToFriendlyDamageScaler"):
    live[key] = {sid: n.values[key].strip()
                 for sid, n in gd.weaponsettings.children.items()
                 if key in n.values}
check(all(len(v) == 150 for v in live.values()),
      f"All three keys appear on 150 structs: "
      f"{ {k: len(v) for k, v in live.items()} }")
check({v for v in live["NPCToPlayerDamageScaler"].values()} == {"1.0"}
      and {v for v in live["NPCToFriendlyDamageScaler"].values()} == {"0.3"},
      "Vanilla: 1.0 against player, 0.3 against allies")

p = build(npc_vs_player_damage_factor=0.5)
n = nodes(p[CWS])
check(len(n) == 150 and all(list(v.values) == ["NPCToPlayerDamageScaler"]
                            for v in n.values()),
      "Player slider modifies ONLY its own key")
check(all(v.values["NPCToPlayerDamageScaler"] == "0.5" for v in n.values()),
      "1.0 x 0.5 = 0.5 on all 150")

p = build(npc_vs_friendly_damage_factor=2.0)
n = nodes(p[CWS])
check(all(v.values["NPCToFriendlyDamageScaler"] == "0.6" for v in n.values()),
      "Allies: 0.3 x 2 = 0.6")

p = build(npc_vs_npc_damage_factor=2.0, npc_vs_player_damage_factor=0.0,
          npc_vs_friendly_damage_factor=0.5)
n = nodes(p[CWS])
first = n[sorted(n)[0]].values
check(set(first) == {"NPCToNPCDamageScaler", "NPCToPlayerDamageScaler",
                     "NPCToFriendlyDamageScaler"},
      "All three combined use ONE struct")
check(first["NPCToPlayerDamageScaler"] == "0.0",
      "0% is allowed (NPC bullets cause no damage)")

# --- 2) Map markers ---
print("\n2) Traders and other NPCs on the map")
with_marker, already_on = [], []
for sid, node in gd.npcprototypes.children.items():
    if sid == "[0]" or "#" in sid:
        continue
    marker = (node.values.get("NPCMarker") or "").strip().rstrip(";").strip()
    if not marker or marker.split("::")[-1] in ("", "Empty"):
        continue
    flag = (node.values.get("UpdateMarkerOnMap") or "").strip().rstrip(";").strip()
    (already_on if flag.lower() == "true" else with_marker).append(sid)
check(bool(with_marker) and bool(already_on),
      f"{len(with_marker)} NPCs with icons but disabled visibility; "
      f"{len(already_on)} are already enabled in vanilla")

p = build(traders_on_map=True)
check(list(p) == [NPCP], f"Exactly one patch file: {list(p)}")
n = nodes(p[NPCP])
check(sorted(n) == sorted(with_marker),
      "Patch exactly the entries with an icon and a disabled flag")
check(all(v.values == {"UpdateMarkerOnMap": "true"} for v in n.values()),
      "Exactly one key per entry, set to true")
check(not (set(n) & set(already_on)), "Already visible entries remain excluded")

# Parse the large NPC file only when required.
fresh = GameData(VANILLA)
build_patches(fresh, Settings(mod_name="X"))
check("npcprototypes" not in fresh.__dict__,
      "Without the toggle, NPCPrototypes is not read")

# --- 3) Look speed ------------------------------------------------------
print("\n3) Horizontal/vertical look speed")
turn = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.BaseTurnRate"))
look = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.BaseLookUpRate"))
check(turn == 40.0 and look == 30.0,
      f"Vanilla player: horizontal {turn}, vertical {look} "
      f"(horizontal movement is one third faster)")
check(gd.corevar("BaseTurnRate", 0.0) == 50.0
      and gd.corevar("BaseLookUpRate", 0.0) == 30.0,
      "The same two keys also appear in CoreVariables at 50/30")

p = build(look_speed_v_factor=2.0)
check(sorted(p) == sorted([OBJ, CORE]), f"Both locations are updated: {sorted(p)}")
mv = nodes(p[OBJ])["Player"].children["MovementParams"].values
check(mv == {"BaseLookUpRate": "60.0"}, f"Player: 30 x 2 = 60 ({mv})")
cv = nodes(p[CORE])["DefaultConfig"].values
check(cv == {"BaseLookUpRate": "60.0"}, f"CoreVariables: 30 x 2 = 60 ({cv})")
p = build(look_speed_h_factor=0.5)
check(nodes(p[OBJ])["Player"].children["MovementParams"].values
      == {"BaseTurnRate": "20.0"}, "Horizontal settings leave vertical settings unchanged")

# --- 4) Camera slowdown ---
print("\n4) Camera smoothing")
brakes, water, concussion = [], [], []
for sid, node in gd.effects.children.items():
    typ = (node.values.get("Type") or "").replace("EEffectType::", "").strip()
    if typ in ("TurnRateChangeYaw", "TurnRateChangePitch"):
        (water if parse_number(node.values.get("ValueMin")) == 0 else brakes).append(sid)
    elif typ == "Concussion":
        concussion.append(sid)
check(len(brakes) == 6 and len(water) == 2 and len(concussion) == 2,
      f"{len(brakes)} slowdown effects, {len(water)} set to 0% (water), "
      f"{len(concussion)} Concussion")

p = build(camera_slowdown_factor=0.0)
n = nodes(p[EFF])
check(sorted(n) == sorted(brakes), "Only the six effective entries are patched")
check(all(set(v.values) == {"ValueMin", "ValueMax"} for v in n.values()),
      "Both values per effect")
check(all(parse_number(v.values["ValueMin"]) == 0 for v in n.values()),
      "0% removes the slowdown")
check(not (set(n) & set(concussion)) and not (set(n) & set(water)),
      "Bloodsucker scream and water remain unchanged")
p = build(camera_slowdown_factor=4.0)
worst = min(parse_number(v.values["ValueMin"]) for v in nodes(p[EFF]).values())
check(worst == -1.0, f"Magnitude capped at 1.0 (minimum value {worst})")

# --- 5) Penetration depth ----------------------------------------------
print("\n5) Penetration depth")
depth = {sid: n.values["PenetrationTraceLenght"].strip()
         for sid, n in gd.projectiles.children.items()
         if "PenetrationTraceLenght" in n.values}
check(len(depth) == 16 and set(depth.values()) == {"150.0", "200.0", "300.0"},
      f"16 projectiles, vanilla {sorted(set(depth.values()))}")
p = build(bullet_penetration_depth_factor=2.0)
n = nodes(p[PROJ])
check(len(n) == 16 and all(list(v.values) == ["PenetrationTraceLenght"]
                           for v in n.values()),
      "Adjacent chance value remains unchanged")
for sid, node in n.items():
    want = parse_number(depth[sid]) * 2
    got = parse_number(node.values["PenetrationTraceLenght"])
    assert abs(got - want) < 1e-6, (sid, depth[sid], node.values)
check(True, "Each of the 16 depths is exactly doubled")

# --- 6/7/8) Artifacts ---------------------------------------------------
print("\n6-8) Artifacts")
arts = {sid: n for sid, n in gd.items.children.items() if "Strafe" in n.values}
need_det = [sid for sid, n in arts.items()
            if (n.values.get("DetectorRequired") or "").strip().rstrip(";").lower() == "true"]
check(len(arts) == 154 and len(need_det) == 147,
      f"{len(arts)} artifacts, including {len(need_det)} require a detector")

p = build(artifacts_no_detector=True)
n = nodes(p[ITEMS])
check(sorted(n) == sorted(need_det), "Exactly those 147 are changed")
check(all(v.values == {"DetectorRequired": "false"} for v in n.values()),
      "Exactly this one key per artifact")

p = build(artifact_hop_distance_factor=0.5)
n = nodes(p[ITEMS])
keys = {k for v in n.values() for k in v.values}
check(keys == {"JumpDistance", "JumpHeight", "JumpForce"},
      f"Jump distance modifies exactly three keys: {sorted(keys)}")

p = build(artifact_hop_count_factor=2.0)
n = nodes(p[ITEMS])
vanilla_counts = {sid: parse_number(a.values["JumpAmount"]) for sid, a in arts.items()}
zeros = [sid for sid, v in vanilla_counts.items() if v == 0]
check(len(zeros) == 2 and not (set(n) & set(zeros)),
      "The two artifacts without jumps remain at zero")
check(all(float(v.values["JumpAmount"]).is_integer() for v in n.values()),
      "Jump counts remain integral")
check(n[sorted(n)[0]].values["JumpAmount"]
      == str(int(vanilla_counts[sorted(n)[0]] * 2)), "doubled")

# Compose JumpDelay with pause and ReturnDistanceValue with spacing.
p = build(artifact_hop_pause_factor=2.0)
keys = {k for v in nodes(p[ITEMS]).values() for k in v.values}
check(keys == {"JumpSeriesDelay", "JumpDelay"},
      f"Pause slider now includes both pauses: {sorted(keys)}")
p = build(artifact_keepaway_factor=2.0)
keys = {k for v in nodes(p[ITEMS]).values() for k in v.values}
check(keys == {"PlayerDistance", "ReturnDistanceValue"},
      f"Distance slider now includes return distance: {sorted(keys)}")

# --- 10) Encounters: alive / wounded / dead ---
print("\n10) Encounter condition")
preset = gd.director_preset()
squads = []
for scen_key, scen in preset.children["Scenarios"].children.items():
    sq = scen.children.get("ScenarioSquads")
    for skey, e in (sq.children.items() if sq else ()):
        squads.append((scen_key, skey, e))
wounded = [(s, k) for s, k, e in squads
           if parse_number(e.values.get("WoundedMultiplier")) > 0]
dead = [(s, k) for s, k, e in squads
        if parse_number(e.values.get("DeadMultiplier")) > 0]
check(len(squads) == 95 and len(wounded) == 8 and len(dead) == 36,
      f"{len(squads)} squad entries, {len(wounded)} with wounded NPCs, "
      f"{len(dead)} with dead NPCs")
check(all("Wounded" in s for s, _k in wounded),
      "All eight belong to dedicated Wounded scenarios "
      "(vanilla contains them, but they are rare)")

DIR = "ALifePrototypes/ALifeDirectorScenarioPrototypes/ALifeDirectorScenarioPrototypes_patch_S2Tweaker.cfg"
p3 = build(encounter_wounded_factor=3.0)
scen_out = nodes(p3[DIR])["ALifeDirectorPreset"].children["Scenarios"].children
touched = [(s, k) for s, sc in scen_out.items()
           for k in sc.children["ScenarioSquads"].children]
check(sorted(touched) == sorted(wounded),
      "Only the eight existing entries are changed; zeros remain zero")
entry = scen_out[wounded[0][0]].children["ScenarioSquads"].children[wounded[0][1]].values
check(set(entry) == {"AgentArchetype", "bPlayerEnemy", "RelationGroup",
                     "AliveMultiplierMin", "AliveMultiplierMax",
                     "WoundedMultiplier", "DeadMultiplier"},
      "Emit the COMPLETE array entry (all seven keys)")
check(parse_number(entry["WoundedMultiplier"]) == 0.3, "0.1 x 3 = 0.3")
p3 = build(encounter_wounded_factor=20.0)
vals = [parse_number(sc.children["ScenarioSquads"].children[k].values["WoundedMultiplier"])
        for s, sc in nodes(p3[DIR])["ALifeDirectorPreset"].children["Scenarios"].children.items()
        for k in sc.children["ScenarioSquads"].children]
check(max(vals) == 1.0, f"Capped at 1.0 (maximum value {max(vals)})")
p3 = build(encounter_dead_factor=0.5)
touched = [(s, k) for s, sc in
           nodes(p3[DIR])["ALifeDirectorPreset"].children["Scenarios"].children.items()
           for k in sc.children["ScenarioSquads"].children]
check(sorted(touched) == sorted(dead), "Dead-NPC slider reaches exactly those 36")

# Check UserInput.ini output separately from cfg patches.
print("\n11) UserInput.ini")
check(input_ini(Settings()) is None, "Without a toggle, no INI is generated")
ini = input_ini(Settings(no_mouse_smoothing=True, no_view_acceleration=True))
check(ini.splitlines()[0] == "[/Script/Engine.InputSettings]",
      "Standard Unreal section on the first line")
check("bEnableMouseSmoothing=False" in ini and "bViewAccelerationEnabled=False" in ini,
      "Both flags are present")
only = input_ini(Settings(no_mouse_smoothing=True))
check("bViewAccelerationEnabled" not in only,
      "Each toggle writes ONLY its own line")
check(build(no_mouse_smoothing=True, no_view_acceleration=True) == {},
      "These toggles intentionally generate NO GameData file")

# --- 12) Intentionally unsupported: MaterialCoefficient ---
print("\n12) Unsupported MaterialCoefficient")
from s2tweaker import gamedata as gd_mod
check(not [n for n in gd_mod.NEEDED_FILES if "ImpactPhysicalMaterial" in n],
      "ImpactPhysicalMaterialPrototypes is NOT in NEEDED_FILES: "
      "MaterialCoefficient appears among Niagara particles, decals and "
      "decal sizes; its meaning is unverified, and adding the file requires a "
      "CACHE_SCHEMA bump for every user")
# Dialogue extraction required a later cache-schema bump;
# this is independent of material-coefficient scope.
check(gd_mod.CACHE_SCHEMA >= 22,
      f"CACHE_SCHEMA {gd_mod.CACHE_SCHEMA} - 1.35.0 itself added no new game-data files")

# --- 13) Tweak list -----------------------------------------------------
print("\n13) Tweak list")
text = "\n".join(summarize(Settings(
    npc_vs_player_damage_factor=0.5, npc_vs_friendly_damage_factor=2.0,
    traders_on_map=True, look_speed_h_factor=1.5, look_speed_v_factor=1.5,
    camera_slowdown_factor=0.0, bullet_penetration_depth_factor=2.0,
    artifacts_no_detector=True, artifact_hop_distance_factor=0.5,
    artifact_hop_count_factor=2.0)))
for phrase in ("NPC vs player damage", "NPC vs allies damage",
               "Traders, technicians", "Look speed, horizontal",
               "Look speed, vertical", "Camera slowdown", "penetration depth",
               "without a detector", "hop distance", "hops per series"):
    assert phrase in text, (phrase, text)
check(True, "All ten controls appear in the tweak list")

print(f"\n=== {ok} checks passed ===")
