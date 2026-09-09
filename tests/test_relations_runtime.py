"""Fraktionsbeziehungen im LAUFENDEN Spielstand (1.36.0).

Bis 1.35.0 schrieb der Fraktions-Tab nur die Baseline in
RelationPrototypes.cfg — und die liest das Spiel beim ANLEGEN eines
Spielstands. Der Zusatz `RelationVersion = Vanilla+1` sollte das
ausgleichen; am 08.09.2026 hat das Gegenlesen von "Relation System
Overhaul" (Nexus 2009) diese Annahme widerlegt.

Der Weg, der wirklich wirkt, ist RSOs: eine eigene Mini-Quest aus
`EQuestNodeType::ChangeRelationships`-Knoten, angeworfen von einer Datei in
`GameData/Scripts/OnGameLaunch/`. Beides ist Vanilla-Mechanik.

Diese Suite haelt genau die Messungen fest, auf denen der Builder steht —
und meldet sich, wenn ein Spiel-Update eine davon umstoesst.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize,
                              PLAYER_TARGET_GUID, RELATIONS_QUEST_SID,
                              RELATIONS_START_SID)
from s2tweaker.gui import FACTION_CHOICES

gd = GameData(str(VANILLA))
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


QUEST_TEXT = (VANILLA / "QuestNodePrototypes.cfg").read_text(
    encoding="utf-8-sig", errors="replace")

# --- 1) Die Vanilla-Mechanik, auf die wir uns stuetzen ------------------
n_nodes = QUEST_TEXT.count("EQuestNodeType::ChangeRelationships")
check(n_nodes > 1000,
      f"EQuestNodeType::ChangeRelationships ist Vanilla-Mechanik ({n_nodes} Knoten)")

launch_dir = VANILLA / "Scripts" / "OnGameLaunch"
launch_files = sorted(launch_dir.glob("*.cfg"))
check(len(launch_files) > 100,
      f"Scripts/OnGameLaunch ist ein Vanilla-Ordner ({len(launch_files)} Dateien)")
check(any("XStartQuestNodeBySID" in f.read_text(encoding="utf-8-sig",
                                                errors="replace")
          for f in launch_files),
      "das Spiel benutzt XStartQuestNodeBySID dort selbst")

# Absolutes Setzen (UsePreset=false, UseDeltaValue=false) ist eine echte
# Vanilla-Form - und ihre Werte liegen auf UNSERER Skala.
blocks = re.findall(r"^(\S+) : struct\.begin.*?\n(.*?)\n^struct\.end",
                    QUEST_TEXT, re.M | re.S)


def val(body, key):
    m = re.search(rf"^\s*{key}\s*=\s*(\S*)\s*$", body, re.M)
    return m.group(1) if m else None


rel_blocks = [b for _n, b in blocks
              if "EQuestNodeType::ChangeRelationships" in b]
absolute = [b for b in rel_blocks
            if val(b, "UsePreset") == "false" and val(b, "UseDeltaValue") == "false"]
check(len(absolute) > 50,
      f"absolutes Setzen ist Vanilla-Praxis ({len(absolute)} Knoten)")
values = {val(b, "RelationshipValue") for b in absolute}
check("-800" in values,
      f"und benutzt unsere Skala (u.a. -800; gefunden: {sorted(values)[:6]})")

# Der Spieler wird ueber eine GUID adressiert, nie als zweites Ziel.
firsts = re.findall(r"^\s*FirstTargetSID\s*=\s*(\S*)\s*$", QUEST_TEXT, re.M)
seconds = re.findall(r"^\s*SecondTargetSID\s*=\s*(\S*)\s*$", QUEST_TEXT, re.M)
check(firsts.count(PLAYER_TARGET_GUID) > 1000 and
      seconds.count(PLAYER_TARGET_GUID) == 0,
      f"die Spieler-GUID steht {firsts.count(PLAYER_TARGET_GUID)}x als erstes "
      f"und nie als zweites Ziel")
# ⚠ Die Ziel-GUIDs sind 32 HEX-Zeichen und bestehen damit selbst aus
# Buchstaben - ein blosser Bezeichner-Test haelt sie faelschlich fuer
# Namen (erster Lauf dieser Suite meldete 1665 statt 35).
GUID = re.compile(r"[0-9A-F]{32}")
named_first = [v for v in firsts
               if v and not GUID.fullmatch(v)
               and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v)]
check(len(named_first) > 10,
      f"ein Fraktionsname als erstes Ziel kommt in Vanilla vor "
      f"({len(named_first)}x, u.a. {sorted(set(named_first))[:5]}) - "
      f"Basis fuer Fraktion gegen Fraktion")

# --- 2) Jede Fraktion, die der Tab anbietet, gibt es auch ---------------
pairs = gd.relation_pairs()
unknown = [sid for sid, _label in FACTION_CHOICES
           if gd.relation_pair_key(sid, "Player") is None]
check(not unknown,
      f"alle {len(FACTION_CHOICES)} angebotenen Fraktionen haben ein "
      f"Spieler-Paar{unknown}")

# --- 3) Aus, oder ohne Paare: nichts ------------------------------------
duty_player = gd.relation_pair_key("Duty", "Player")
duty_freedom = gd.relation_pair_key("Duty", "Freedom")

def files(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


check(not [p for p in files(faction_relations={duty_player: 800})
           if "QuestPrototypes" in p or "OnGameLaunch" in p],
      "ohne den Schalter entstehen weder Quest noch Startskript")
check(not [p for p in files(relations_runtime=True)
           if "QuestPrototypes" in p or "OnGameLaunch" in p],
      "mit Schalter, aber ohne verstelltes Paar ebenfalls nicht")
# Ein Paar auf seinem Vanilla-Wert ist kein verstelltes Paar.
check(not [p for p in files(relations_runtime=True,
                            faction_relations={duty_player: pairs[duty_player]})
           if "OnGameLaunch" in p],
      "ein Paar auf Vanilla erzeugt keinen Knoten")

# --- 4) An, mit zwei Paaren ---------------------------------------------
out = files(relations_runtime=True,
            faction_relations={duty_player: 800, duty_freedom: -800})
quest_patch = next(t for p, t in out.items() if p.endswith("_Relations.cfg"))
proto_patch = next(t for p, t in out.items() if "QuestPrototypes" in p)
script_patch = next(t for p, t in out.items() if "OnGameLaunch" in p)
check(True, "Knoten, Quest und Startskript werden erzeugt")
# Die Knoten bekommen eine EIGENE Datei im QuestNode-Ordner (wie RSO und
# Living Zone es tun) - nicht die {bpatch}-Datei der uebrigen Quest-Regler.
check(not any(p.endswith("QuestNodePrototypes_patch_S2Tweaker.cfg") for p in out)
      and "{bpatch}" not in quest_patch,
      "die neuen Knoten liegen fuer sich, ohne ein einziges {bpatch}")

nodes = re.findall(r"^(S2T_Rel_\d+) : struct\.begin(.*)$", quest_patch, re.M)
check(len(nodes) == 2, f"je verstelltem Paar genau ein Knoten ({len(nodes)})")
check(all(not attrs.strip() for _n, attrs in nodes),
      "die neuen Knoten tragen KEIN {bpatch} (es gibt nichts zusammenzufuehren)")

def node_body(sid):
    m = re.search(rf"^{sid} : struct\.begin.*?\n(.*?)\n^struct\.end",
                  quest_patch, re.M | re.S)
    return m.group(1)


bodies = {sid: node_body(sid) for sid, _ in nodes}
player_node = next(b for b in bodies.values()
                   if val(b, "FirstTargetSID") == PLAYER_TARGET_GUID)
check(val(player_node, "SecondTargetSID") == "Duty",
      "Spieler-Paar: erste Seite die Spieler-GUID, zweite die Fraktion")
check(val(player_node, "RelationshipValue") == "800",
      "der Reglerwert geht unveraendert als RelationshipValue raus")
check(val(player_node, "UseDeltaValue") == "false"
      and val(player_node, "UsePreset") == "false",
      "absolut statt Delta oder Preset")
check(val(player_node, "SetFactionRelationshipAsPersonal") == "false"
      and val(player_node, "ShouldLockPersonalRelationship") == "false",
      "die zwei Sonderfahnen bleiben aus (wie bei RSO und in Vanilla)")

ff_node = next(b for b in bodies.values()
               if val(b, "FirstTargetSID") != PLAYER_TARGET_GUID)
check({val(ff_node, "FirstTargetSID"), val(ff_node, "SecondTargetSID")}
      == {"Duty", "Freedom"},
      "Fraktion gegen Fraktion: beide Seiten als Name")

# --- 5) Die Kette haengt zusammen ---------------------------------------
check(all(val(b, "QuestSID") == RELATIONS_QUEST_SID for b in bodies.values()),
      f"alle Knoten gehoeren zur eigenen Quest {RELATIONS_QUEST_SID}")
check(all(RELATIONS_START_SID in b for b in bodies.values()),
      "jeder Knoten haengt am Startknoten")
start = node_body(RELATIONS_START_SID)
check(val(start, "LaunchOnQuestStart") == "true" and val(start, "StartDelay"),
      "der Startknoten startet mit der Quest und wartet kurz")
check(f"SID = {RELATIONS_QUEST_SID}" in proto_patch,
      "die Quest steht in QuestPrototypes")
check(f"XStartQuestNodeBySID {RELATIONS_START_SID}" in script_patch,
      "das Startskript wirft genau diesen Knoten an")
check(script_patch.lstrip().startswith("[*]"),
      "das Skript haengt sich an ([*]), statt einen Index zu belegen")
check("{bpatch}" not in script_patch and "{bpatch}" not in proto_patch,
      "weder Quest noch Skript tragen {bpatch}")

# --- 6) Der Rest bleibt, wie er war -------------------------------------
check("Faction relations are also applied to a running save" in summarize(
          Settings(relations_runtime=True)),
      "die Tweak-Liste nennt den Schalter")
rel_patch = next(t for p, t in out.items() if "RelationPrototypes" in p)
check("Duty<->Player = 800" in rel_patch,
      "die Baseline wird weiterhin geschrieben (fuer NEUE Spielstaende)")

# --- 7) Und der Weg bis in die fertige Pak ------------------------------
# `Scripts/OnGameLaunch/` ist eine Ebene tiefer als alles, was das Werkzeug
# bisher geschrieben hat - dass der Pak-Bauer den Pfad haelt, wird hier
# einmal wirklich nachgesehen statt angenommen.
import tempfile
from s2tweaker import pakio

pak = Path(tempfile.mkdtemp()) / "zzz_RelRuntimeTest_P.pak"
pakio.pack_mod(out, pak)
names = pakio.list_pak(pak)
base = "Stalker2/Content/GameLite/GameData/"
for want in ("QuestNodePrototypes/S2Tweaker_Relations.cfg",
             "QuestPrototypes/QuestPrototypes_patch_S2Tweaker.cfg",
             "Scripts/OnGameLaunch/OnGameLaunchScripts_patch_S2Tweaker.cfg"):
    check(base + want in names, f"liegt in der Pak unter {want}")

back = pak.parent / "back"
script_in_pak = base + "Scripts/OnGameLaunch/OnGameLaunchScripts_patch_S2Tweaker.cfg"
pakio.unpack_many(pak, back, [script_in_pak])
check((back / script_in_pak).read_text(encoding="utf-8", errors="replace")
      == script_patch,
      "und kommt aus der Pak unveraendert wieder heraus")

print(f"\n=== {ok} Pruefungen gruen ===")
