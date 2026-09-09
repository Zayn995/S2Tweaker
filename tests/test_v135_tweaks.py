"""Die kleinen Kandidaten aus 1.35.0 (Besitzer 08.09.2026: "alles aus klein").

Herkunft: der Familien-Waechter (tests/test_key_families.py) und die neunte
Datenrecherche (docs/ROADMAP.md). Acht Sachen gebaut, eine verworfen:

  1. NPC-Schaden gegen SPIELER und gegen VERBUENDETE - der Dreiersatz um
     NPCToNPCDamageScaler, von dem 1.31.0 nur einen genommen hatte
  2. Haendler/Techniker/Medics/Fuehrer auf der Karte (nur eine Fahne)
  3. Blicktempo waagerecht/senkrecht getrennt
  4. Kamera-Bremsen (Chemie, Stacheldraht, Fliegenfaenger)
  5. Durchschlagstiefe je Geschoss (Geschwister der Durchschlagschance)
  6. Artefakte ohne Detektor sichtbar
  7. Sprungweite der Artefakte
  8. Spruenge je Serie
  VERWORFEN: Durst (`RegenThirstPoints`) - steht in Vanilla auf 0.0, und das
  Wort "Thirst" kommt im ganzen Spiel NUR in ObjPrototypes vor: kein Effekt,
  kein Getraenk, kein Schwierigkeitsgrad-Schluessel fuettert den Zaehler.
  Es gibt also nichts zu skalieren (steht in test_key_families als IGNORED).

Alle Sollwerte kommen live aus vanilla/.
"""
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
check(build() == {}, "Vanilla-Stellung erzeugt keine einzige Datei")

# --- 1) NPC-Schaden: der Dreiersatz ------------------------------------
print("\n1) NPC-Schaden gegen Spieler und Verbuendete")
live = {}
for key in ("NPCToNPCDamageScaler", "NPCToPlayerDamageScaler",
            "NPCToFriendlyDamageScaler"):
    live[key] = {sid: n.values[key].strip()
                 for sid, n in gd.weaponsettings.children.items()
                 if key in n.values}
check(all(len(v) == 150 for v in live.values()),
      f"alle drei Schluessel stehen an 150 Structs: "
      f"{ {k: len(v) for k, v in live.items()} }")
check({v for v in live["NPCToPlayerDamageScaler"].values()} == {"1.0"}
      and {v for v in live["NPCToFriendlyDamageScaler"].values()} == {"0.3"},
      "Vanilla: gegen den Spieler 1.0, gegen Verbuendete 0.3")

p = build(npc_vs_player_damage_factor=0.5)
n = nodes(p[CWS])
check(len(n) == 150 and all(list(v.values) == ["NPCToPlayerDamageScaler"]
                            for v in n.values()),
      "der Spieler-Regler fasst NUR seinen eigenen Schluessel an")
check(all(v.values["NPCToPlayerDamageScaler"] == "0.5" for v in n.values()),
      "1.0 x 0.5 = 0.5 an allen 150")

p = build(npc_vs_friendly_damage_factor=2.0)
n = nodes(p[CWS])
check(all(v.values["NPCToFriendlyDamageScaler"] == "0.6" for v in n.values()),
      "Verbuendete: 0.3 x 2 = 0.6")

p = build(npc_vs_npc_damage_factor=2.0, npc_vs_player_damage_factor=0.0,
          npc_vs_friendly_damage_factor=0.5)
n = nodes(p[CWS])
first = n[sorted(n)[0]].values
check(set(first) == {"NPCToNPCDamageScaler", "NPCToPlayerDamageScaler",
                     "NPCToFriendlyDamageScaler"},
      "alle drei zusammen landen in EINEM Struct")
check(first["NPCToPlayerDamageScaler"] == "0.0",
      "0 % ist erlaubt (NPC-Kugeln tun dann nichts)")

# --- 2) Karten-Marker ---------------------------------------------------
print("\n2) Haendler und Co. auf der Karte")
with_marker, already_on = [], []
for sid, node in gd.npcprototypes.children.items():
    if sid == "[0]" or "#" in sid:
        continue
    marker = (node.values.get("NPCMarker") or "").strip().rstrip(";").strip()
    if not marker or marker.split("::")[-1] in ("", "Empty"):
        continue
    flag = (node.values.get("UpdateMarkerOnMap") or "").strip().rstrip(";").strip()
    (already_on if flag.lower() == "true" else with_marker).append(sid)
check(len(with_marker) == 80 and len(already_on) == 8,
      f"{len(with_marker)} NPCs mit Symbol, aber ausgeschaltet; "
      f"{len(already_on)} sind vanilla schon an")

p = build(traders_on_map=True)
check(list(p) == [NPCP], f"genau eine Patchdatei: {list(p)}")
n = nodes(p[NPCP])
check(sorted(n) == sorted(with_marker),
      "gepatcht wird exakt die Menge mit Symbol und ausgeschalteter Fahne")
check(all(v.values == {"UpdateMarkerOnMap": "true"} for v in n.values()),
      "je Eintrag genau ein Schluessel, und der auf true")
check(not (set(n) & set(already_on)), "die acht schon sichtbaren bleiben aussen vor")

# Die 1,8-MB-Datei darf nur bei Bedarf geparst werden (Regel seit 1.28.0 P8)
fresh = GameData(VANILLA)
build_patches(fresh, Settings(mod_name="X"))
check("npcprototypes" not in fresh.__dict__,
      "ohne den Schalter wird NPCPrototypes gar nicht erst gelesen")

# --- 3) Blicktempo ------------------------------------------------------
print("\n3) Blicktempo waagerecht/senkrecht")
turn = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.BaseTurnRate"))
look = parse_number(gd.resolve(gd.obj, "Player", "MovementParams.BaseLookUpRate"))
check(turn == 40.0 and look == 30.0,
      f"Vanilla am Player: waagerecht {turn}, senkrecht {look} "
      f"(waagerecht ist ein Drittel schneller)")
check(gd.corevar("BaseTurnRate", 0.0) == 50.0
      and gd.corevar("BaseLookUpRate", 0.0) == 30.0,
      "dieselben zwei Schluessel stehen mit 50/30 auch in CoreVariables")

p = build(look_speed_v_factor=2.0)
check(sorted(p) == sorted([OBJ, CORE]), f"beide Ablagen werden bedient: {sorted(p)}")
mv = nodes(p[OBJ])["Player"].children["MovementParams"].values
check(mv == {"BaseLookUpRate": "60.0"}, f"Player: 30 x 2 = 60 ({mv})")
cv = nodes(p[CORE])["DefaultConfig"].values
check(cv == {"BaseLookUpRate": "60.0"}, f"CoreVariables: 30 x 2 = 60 ({cv})")
p = build(look_speed_h_factor=0.5)
check(nodes(p[OBJ])["Player"].children["MovementParams"].values
      == {"BaseTurnRate": "20.0"}, "waagerecht laesst senkrecht in Ruhe")

# --- 4) Kamera-Bremsen --------------------------------------------------
print("\n4) Kamera-Bremsen")
brakes, water, concussion = [], [], []
for sid, node in gd.effects.children.items():
    typ = (node.values.get("Type") or "").replace("EEffectType::", "").strip()
    if typ in ("TurnRateChangeYaw", "TurnRateChangePitch"):
        (water if parse_number(node.values.get("ValueMin")) == 0 else brakes).append(sid)
    elif typ == "Concussion":
        concussion.append(sid)
check(len(brakes) == 6 and len(water) == 2 and len(concussion) == 2,
      f"{len(brakes)} bremsende Effekte, {len(water)} auf 0 % (Wasser), "
      f"{len(concussion)} Concussion")

p = build(camera_slowdown_factor=0.0)
n = nodes(p[EFF])
check(sorted(n) == sorted(brakes), "nur die sechs mit Wirkung werden gepatcht")
check(all(set(v.values) == {"ValueMin", "ValueMax"} for v in n.values()),
      "je Effekt beide Werte")
check(all(parse_number(v.values["ValueMin"]) == 0 for v in n.values()),
      "0 % = keine Bremse mehr")
check(not (set(n) & set(concussion)) and not (set(n) & set(water)),
      "Blutsauger-Schrei und Wasser bleiben unangetastet")
p = build(camera_slowdown_factor=4.0)
worst = min(parse_number(v.values["ValueMin"]) for v in nodes(p[EFF]).values())
check(worst == -1.0, f"der Betrag ist bei 1.0 gedeckelt (kleinster Wert {worst})")

# --- 5) Durchschlagstiefe ----------------------------------------------
print("\n5) Durchschlagstiefe")
depth = {sid: n.values["PenetrationTraceLenght"].strip()
         for sid, n in gd.projectiles.children.items()
         if "PenetrationTraceLenght" in n.values}
check(len(depth) == 16 and set(depth.values()) == {"150.0", "200.0", "300.0"},
      f"16 Geschosse, Vanilla {sorted(set(depth.values()))}")
p = build(bullet_penetration_depth_factor=2.0)
n = nodes(p[PROJ])
check(len(n) == 16 and all(list(v.values) == ["PenetrationTraceLenght"]
                           for v in n.values()),
      "die Chance daneben bleibt unberuehrt")
for sid, node in n.items():
    want = parse_number(depth[sid]) * 2
    got = parse_number(node.values["PenetrationTraceLenght"])
    assert abs(got - want) < 1e-6, (sid, depth[sid], node.values)
check(True, "jede der 16 Tiefen ist exakt verdoppelt")

# --- 6/7/8) Artefakte ---------------------------------------------------
print("\n6-8) Artefakte")
arts = {sid: n for sid, n in gd.items.children.items() if "Strafe" in n.values}
need_det = [sid for sid, n in arts.items()
            if (n.values.get("DetectorRequired") or "").strip().rstrip(";").lower() == "true"]
check(len(arts) == 154 and len(need_det) == 147,
      f"{len(arts)} Artefakte, davon {len(need_det)} mit Detektorpflicht")

p = build(artifacts_no_detector=True)
n = nodes(p[ITEMS])
check(sorted(n) == sorted(need_det), "genau die 147 werden umgestellt")
check(all(v.values == {"DetectorRequired": "false"} for v in n.values()),
      "je Artefakt genau dieser eine Schluessel")

p = build(artifact_hop_distance_factor=0.5)
n = nodes(p[ITEMS])
keys = {k for v in n.values() for k in v.values}
check(keys == {"JumpDistance", "JumpHeight", "JumpForce"},
      f"Sprungweite fasst genau drei Schluessel an: {sorted(keys)}")

p = build(artifact_hop_count_factor=2.0)
n = nodes(p[ITEMS])
vanilla_counts = {sid: parse_number(a.values["JumpAmount"]) for sid, a in arts.items()}
zeros = [sid for sid, v in vanilla_counts.items() if v == 0]
check(len(zeros) == 2 and not (set(n) & set(zeros)),
      "die zwei Artefakte ohne Spruenge bleiben bei null")
check(all(float(v.values["JumpAmount"]).is_integer() for v in n.values()),
      "Spruenge bleiben ganzzahlig")
check(n[sorted(n)[0]].values["JumpAmount"]
      == str(int(vanilla_counts[sorted(n)[0]] * 2)), "verdoppelt")

# eingefaltet: JumpDelay in die Pause, ReturnDistanceValue in den Abstand
p = build(artifact_hop_pause_factor=2.0)
keys = {k for v in nodes(p[ITEMS]).values() for k in v.values}
check(keys == {"JumpSeriesDelay", "JumpDelay"},
      f"der Pausen-Regler nimmt jetzt beide Pausen mit: {sorted(keys)}")
p = build(artifact_keepaway_factor=2.0)
keys = {k for v in nodes(p[ITEMS]).values() for k in v.values}
check(keys == {"PlayerDistance", "ReturnDistanceValue"},
      f"der Abstands-Regler nimmt die Rueckkehr-Distanz mit: {sorted(keys)}")

# --- 10) Begegnungen: lebend / verwundet / tot -------------------------
print("\n10) Zustand der Begegnungen")
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
      f"{len(squads)} Squad-Eintraege, {len(wounded)} mit Verwundeten, "
      f"{len(dead)} mit Toten")
check(all("Wounded" in s for s, _k in wounded),
      "die acht sitzen alle in den eigenen Wounded-Szenarien "
      "(Vanilla HAT sie, sie sind nur selten)")

DIR = "ALifePrototypes/ALifeDirectorScenarioPrototypes/ALifeDirectorScenarioPrototypes_patch_S2Tweaker.cfg"
p3 = build(encounter_wounded_factor=3.0)
scen_out = nodes(p3[DIR])["ALifeDirectorPreset"].children["Scenarios"].children
touched = [(s, k) for s, sc in scen_out.items()
           for k in sc.children["ScenarioSquads"].children]
check(sorted(touched) == sorted(wounded),
      "nur die acht vorhandenen werden angefasst - Nullen bleiben Nullen")
entry = scen_out[wounded[0][0]].children["ScenarioSquads"].children[wounded[0][1]].values
check(set(entry) == {"AgentArchetype", "bPlayerEnemy", "RelationGroup",
                     "AliveMultiplierMin", "AliveMultiplierMax",
                     "WoundedMultiplier", "DeadMultiplier"},
      "der Array-Eintrag geht KOMPLETT raus (alle sieben Schluessel)")
check(parse_number(entry["WoundedMultiplier"]) == 0.3, "0.1 x 3 = 0.3")
p3 = build(encounter_wounded_factor=20.0)
vals = [parse_number(sc.children["ScenarioSquads"].children[k].values["WoundedMultiplier"])
        for s, sc in nodes(p3[DIR])["ALifeDirectorPreset"].children["Scenarios"].children.items()
        for k in sc.children["ScenarioSquads"].children]
check(max(vals) == 1.0, f"gedeckelt bei 1.0 (groesster Wert {max(vals)})")
p3 = build(encounter_dead_factor=0.5)
touched = [(s, k) for s, sc in
           nodes(p3[DIR])["ALifeDirectorPreset"].children["Scenarios"].children.items()
           for k in sc.children["ScenarioSquads"].children]
check(sorted(touched) == sorted(dead), "der Toten-Regler trifft genau die 36")

# --- 11) UserInput.ini: der zweite Auslieferungsweg --------------------
print("\n11) UserInput.ini")
check(input_ini(Settings()) is None, "ohne Schalter wird keine INI erzeugt")
ini = input_ini(Settings(no_mouse_smoothing=True, no_view_acceleration=True))
check(ini.splitlines()[0] == "[/Script/Engine.InputSettings]",
      "Unreal-Standardsektion als erste Zeile")
check("bEnableMouseSmoothing=False" in ini and "bViewAccelerationEnabled=False" in ini,
      "beide Fahnen stehen drin")
only = input_ini(Settings(no_mouse_smoothing=True))
check("bViewAccelerationEnabled" not in only,
      "jeder Schalter schreibt NUR seine eigene Zeile")
check(build(no_mouse_smoothing=True, no_view_acceleration=True) == {},
      "die Schalter erzeugen bewusst KEINE GameData-Datei")

# --- 12) Bewusst NICHT gebaut: MaterialCoefficient ---------------------
print("\n12) Verworfen, damit es niemand nochmal versucht")
from s2tweaker import gamedata as gd_mod
check(not [n for n in gd_mod.NEEDED_FILES if "ImpactPhysicalMaterial" in n],
      "ImpactPhysicalMaterialPrototypes steht NICHT in NEEDED_FILES: "
      "MaterialCoefficient sitzt dort zwischen Niagara-Partikeln, Decals und "
      "Decal-Groessen - die Bedeutung ist unbelegt, und die Datei waere ein "
      "CACHE_SCHEMA-Bump fuer jeden Nutzer")
# 1.35.0 las keine neue Spieldatei (Schema 22). 1.36.0 liest mit
# DialogPrototypes wieder eine - bewusst, fuer den Menue-Boden des
# Mehrfach-Job-Schalters (Schema 23). Die MaterialCoefficient-Entscheidung
# oben bleibt davon unberuehrt.
check(gd_mod.CACHE_SCHEMA >= 22,
      f"CACHE_SCHEMA {gd_mod.CACHE_SCHEMA} - 1.35.0 selbst las keine neue Spieldatei")

# --- 13) Tweak-Liste -----------------------------------------------------
print("\n13) Tweak-Liste")
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
check(True, "alle zehn Bedienelemente stehen in der Tweak-Liste")

print(f"\n=== {ok} Pruefungen gruen ===")
