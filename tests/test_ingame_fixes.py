"""Was die In-Game-Tests der Spieler ergeben haben (GitHub #9 bis #12).

Nachtrag 09.09.2026 - ein zweiter Tester, craigduk76, drei Berichte auf
1.35.0, dazu Molkerrs dritter Bericht:
  #12 Ausnuechtern bei 25 % wirkt (erste Bestaetigung); Wunsch: 1 %.
      -> Untergrenze 1 %, der Regler schreibt saubere Fliesskommawerte.
  #11 "Free look on ladders" wirkt nicht, "Look straight down" schon -
      dieselbe Pak, dasselbe Struct. Die zwei Leiter-Schluessel sind tot.
      -> Schalter zurueckgezogen, Feld bleibt fuer alte Presets.
  #10 Gespraechsabstand und Dialog-Zoom wirken nicht. Nachgezaehlt:
      Min/MaxDialogInteractDistance deklariert JEDER der 1608 Menschen
      selbst, wir schrieben nur den Spieler -> jetzt beide Seiten.
      DialogFOVDefault hat keinen zweiten Hebel -> Regler zurueckgezogen.
  #9  Der Mehrfach-Job-Schalter wirkt auch nach der 1.34.0-Reparatur
      nicht -> beide Job-Schalter zurueckgezogen, Builder bleiben.

Molkerrs erster Bericht (07.09.2026), Punkt fuer Punkt:
  1. Stapelgroessen wirken  -> bestaetigt, nichts zu tun
  2. "Accepting multiple quests doesn't work" -> stimmt: der Limit-Regler
     aus 1.31.0 erhoeht nur den VORRAT je Runde. Neu in 1.33.0: ein
     zusaetzlicher Knoten je Geber macht den Dialog nach der Zusage wieder
     scharf (Schalter "Accept several jobs in one conversation").
     1.34.0: repariert - die Zusage schaltet den Dialog per
     Excluding-Launcher AB, darum raeumt jetzt ein BridgeCleanUp-Knoten
     ihr Ergebnis weg, und der neue Launcher-Eintrag geht ohne {bpatch}
     raus (Diagnose 08.09.2026, siehe _quest_multi_patch).
  3. Fadenkreuz beim Zielen -> kein Fehler, normales Spielverhalten
  4. "Resizing icons doesn't work with DLC armor and weapons" -> stimmt:
     die 22 Editions-Gegenstaende deklarieren Weight, ItemGridWidth/-Height,
     InventoryActionTime und BaseDurability selbst, wurden von den
     allgemeinen Item-Reglern aber nie erfasst.

Alle Sollwerte kommen live aus vanilla/.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker import cfgparse

gd = GameData(VANILLA)
QUESTS = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"

ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


def build(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


# --- 1) Mehrere Jobs je Gespraech ---------------------------------------
print("\n1) Accept several jobs in one conversation")
check(build() == {}, "Vanilla-Stellung erzeugt nichts")

p = build(repeatable_jobs_multi=True)
check(list(p) == [QUESTS], f"genau eine Patchdatei: {list(p)}")
nodes = cfgparse.parse(p[QUESTS]).children
givers = gd.repeatable_quest_givers()
check(len(givers) == 8, f"{len(givers)} Auftraggeber erkannt")

rearm = [s for s in nodes if s.endswith("_S2T_ReArmDialog")]
clear = [s for s in nodes if s.endswith("_S2T_ClearAccept")]
check(len(rearm) == 8 and len(clear) == 8,
      f"{len(clear)} Aufraeum- und {len(rearm)} Wieder-scharf-Knoten, je einer pro Geber")
check(not [s for s in rearm + clear if s in gd.questnodes.children],
      "keiner der neuen Namen existiert in Vanilla (wird also angehaengt)")

raw = p[QUESTS]
for sid in rearm + clear:
    start = raw.index(f"{sid} : struct.begin")
    end = raw.index("\nstruct.end", start)
    assert "{bpatch}" not in raw[start:end], f"{sid} traegt bpatch"
check(True, "kein neuer Knoten traegt {bpatch} (nichts zum Zusammenfuehren)")

by_quest = {g["quest_sid"]: g for g in givers}

# 1a) Der Aufraeum-Knoten haengt an der Zusage und loescht GENAU deren
#     Ergebnis - der Grund, warum die 1.33.0-Fassung nicht wirkte: der
#     SetDialog-Knoten wird von der Zusage per Excluding-Launcher
#     abgeschaltet und bleibt es, solange das Ergebnis steht.
for sid in clear:
    node = nodes[sid]
    giver = by_quest[node.values["QuestSID"]]
    assert node.values["NodeType"] == "EQuestNodeType::BridgeCleanUp", sid
    assert node.values["Repeatable"] == "true", sid
    conn = node.children["Launchers"].children["[0]"].children["Connections"].children["[0]"]
    assert conn.values["SID"] == giver["accept"], (sid, conn.values["SID"])
    cleaned = list(node.children["NodesToCleanUpResults"].values.values())
    assert cleaned == [giver["accept"]], (sid, cleaned)
check(True, "jeder Aufraeum-Knoten loescht NUR das Ergebnis der Zusage seines Gebers")

# 1b) Die Add_C0x-Knoten bleiben unberuehrt. Genau die raeumt das Vorbild
#     (Nexus 2638) mit weg - und genau daran zerbricht es laut seinem Autor.
adds = {k for k in gd.questnodes.children if "_Add_C" in k}
for sid in clear:
    cleaned = set(nodes[sid].children["NodesToCleanUpResults"].values.values())
    assert not (cleaned & adds), (sid, cleaned & adds)
check(True, "kein Auftragsbehaelter (Add_C0x) wird aufgeraeumt")

# 1c) Kette Zusage -> Aufraeumen -> Dialog wieder scharf
for sid in rearm:
    node = nodes[sid]
    quest = node.values["QuestSID"]
    conn = node.children["Launchers"].children["[0]"].children["Connections"].children["[0]"]
    assert conn.values["SID"] == f"{quest}_S2T_ClearAccept", (sid, conn.values["SID"])
    assert node.values["NodeType"] == "EQuestNodeType::Technical"
    assert node.values["Repeatable"] == "true"
    assert node.values["StartDelay"] == "1.0"
check(True, "der Wieder-scharf-Knoten haengt hinter dem Aufraeumen, nicht direkt an der Zusage")

for giver in givers:
    dlg = nodes[giver["dialog_sid"]]
    launchers = dlg.children["Launchers"].children
    idx = f"[{giver['next_launcher']}]"
    assert list(launchers) == [idx], (giver["quest"], list(launchers))
    conn = launchers[idx].children["Connections"].children["[0]"]
    assert conn.values["SID"] == f"{giver['quest_sid']}_S2T_ReArmDialog"
    # der Index muss FREI gewesen sein - sonst haetten wir Vanilla ueberschrieben
    vanilla_launchers = gd.questnodes.children[giver["dialog_sid"]].children["Launchers"].children
    assert idx not in vanilla_launchers, (giver["quest"], idx)
check(True, "der Dialog bekommt genau EINEN zusaetzlichen Launcher auf einem freien Index")

# 1d) Der neue Launcher-Eintrag ist NEU - er darf kein {bpatch} tragen
#     (zweiter Grund, warum 1.33.0 nicht wirkte: bpatch heisst
#     "zusammenfuehren", und es gibt nichts, womit man ihn zusammenfuehren
#     koennte). Seine Eltern muessen es dagegen tragen.
for giver in givers:
    head = raw.index(f"{giver['dialog_sid']} : struct.begin")
    block = raw[head:raw.index("\nstruct.end\n", head)]
    idx = f"[{giver['next_launcher']}] : struct.begin"
    assert "Launchers : struct.begin {bpatch}" in block, giver["quest"]
    assert idx + "\n" in block + "\n", (giver["quest"], idx)
    assert idx + " {bpatch}" not in block, (giver["quest"], idx)
check(True, "der neue Launcher-Eintrag geht ohne {bpatch} raus, seine Eltern mit")

# 1e) Gegenprobe an den Spieldaten: der Dialog wird von der Zusage wirklich
#     per Excluding-Launcher abgeschaltet (die Messung, auf der der Umbau
#     beruht), und kein einziger Bedingungsknoten liest das Ergebnis der
#     Zusage - deshalb ist Aufraeumen gefahrlos.
def _walk(node, path=""):
    for k, v in node.values.items():
        yield path, k, v
    for k, ch in node.children.items():
        yield from _walk(ch, f"{path}/{k}")

excluded = 0
for giver in givers:
    dlg = gd.questnodes.children[giver["dialog_sid"]]
    for lnode in dlg.children["Launchers"].children.values():
        conns = lnode.children.get("Connections")
        for c in (conns.children.values() if conns else ()):
            if c.values.get("SID", "").strip() == giver["accept"]:
                assert lnode.values.get("Excluding", "").strip() == "true", giver["quest"]
                excluded += 1
check(excluded == 8, f"bei allen {excluded} Gebern schaltet die Zusage den Dialog per Excluding ab")

readers = [k for k, n in gd.questnodes.children.items()
           for _p, key, val in _walk(n)
           if key == "LinkedNodePrototypeSID" and "Technical_GetQuest" in (val or "")]
check(not readers, "keine Bedingung im Spiel liest das Ergebnis eines Zusage-Knotens")

# 1f) Das Abgeben: der End-Knoten hinter dem Rundenaufraeumer raeumt in
#     Vanilla ALLES in der Quest ab - auch die Behaelter der Auftraege, die
#     man noch traegt. Genau dieser eine Schluessel geht auf false.
vanilla_ends = {k: n for k, n in gd.questnodes.children.items()
                if (n.values.get("NodeType") or "").strip() == "EQuestNodeType::End"}
falses = [k for k, n in vanilla_ends.items()
          if (n.values.get("ExcludeAllNodesInContainer") or "").strip() == "false"]
check(len(falses) >= 500,
      f"false ist kein Sonderwert: {len(falses)} von {len(vanilla_ends)} End-Knoten "
      f"stehen in Vanilla selbst darauf")

for giver in givers:
    end_sid = giver["end_sid"]
    assert end_sid, giver["quest"]
    assert giver["end_exclude"] == "true", (giver["quest"], giver["end_exclude"])
    assert nodes[end_sid].values == {"ExcludeAllNodesInContainer": "false"}, \
        (end_sid, nodes[end_sid].values)
    assert not nodes[end_sid].children, end_sid
check(True, "jeder der acht End-Knoten bekommt GENAU diesen einen Schluessel auf false")

# der Aufraeumer selbst bleibt vanilla - wir loeschen nichts zusaetzlich
for giver in givers:
    assert giver["cleanup_sid"] not in nodes, giver["cleanup_sid"]
check(True, "der Vanilla-Aufraeumer wird nicht angefasst")

# Gegenprobe: ohne den Schalter bleibt der End-Knoten unberuehrt
only_limit = build(repeatable_jobs_per_round=6)
if only_limit:
    assert "ExcludeAllNodesInContainer" not in only_limit.get(QUESTS, "")
check(True, "ohne den Schalter fasst nichts den End-Knoten an")

# Zusammenspiel mit den zwei aelteren Reglern derselben Familie
both = build(repeatable_jobs_multi=True, repeatable_jobs_per_round=6,
             repeatable_quest_factor=0.04)
txt = both[QUESTS]
check("_S2T_ReArmDialog" in txt and "VariableValue = 6" in txt and "InGameHours = 1" in txt,
      "Schalter, Rundenlimit und Cooldown landen zusammen in einer Datei")
check("Accept several repeatable jobs" in "\n".join(summarize(Settings(repeatable_jobs_multi=True))),
      "die Tweak-Liste nennt den Schalter")


# --- 2) Die 22 Editions-Gegenstaende ------------------------------------
print("\n2) DLC-Gegenstaende (Molkerr Punkt 4)")
dlc_items = {ed: trees["items"].children for ed, trees in gd.dlc_editions.items()}
total = sum(len(v) for v in dlc_items.values())
check(total >= 20, f"{total} Editions-Gegenstaende in {len(dlc_items)} Editionen")
for ed, kids in dlc_items.items():
    n = sum(1 for x in kids.values() if "ItemGridWidth" in x.values)
    assert n == len(kids), (ed, n, len(kids))
check(True, "jedes davon deklariert seine Rastergroesse selbst")


def dlc_files(patches):
    return {k: v for k, v in patches.items() if k.startswith("//")}


grid = build(item_grid_factor=2.0)
files = dlc_files(grid)
check(files, f"Rastergroesse erzeugt jetzt DLC-Dateien: {sorted(files)[:2]}")
hits = 0
for text in files.values():
    for node in cfgparse.parse(text).children.values():
        if "ItemGridWidth" in node.values:
            hits += 1
check(hits >= 20, f"{hits} Editions-Gegenstaende bekommen ein groesseres Raster")

dur = dlc_files(build(gear_durability_factor=2.0))
hits = sum(1 for t in dur.values() for n in cfgparse.parse(t).children.values()
           if "BaseDurability" in n.values)
# 17 statt 22: fuenf Editions-Eintraege stehen auf BaseDurability 1.0 -
# der Platzhalter fuer Sachen ohne Zustand (PDA, Flashdrive, Magazin,
# zwei Umbausaetze). Dieselbe Regel wie im Basiszweig.
check(hits == 17, f"{hits} Editions-Gegenstaende bekommen den neuen Maximalzustand")

act = dlc_files(build(inventory_action_factor=2.0))
check(act, "auch die Benutzungszeit erreicht den DLC-Zweig")

weight = dlc_files(build(item_weight_factor=0.5,
                         item_weight_categories={"weapon", "armor"}))
hits = sum(1 for t in weight.values() for n in cfgparse.parse(t).children.values()
           if "Weight" in n.values)
check(hits > 0, f"{hits} Editions-Gegenstaende folgen den Gewichts-Reglern")

check(not dlc_files(build(item_weight_factor=0.5, item_weight_categories={"consumable"})),
      "eine Kategorie ohne Editions-Stuecke erzeugt dort auch nichts")
check(not dlc_files(build()), "Vanilla-Stellung ruehrt den DLC-Zweig nicht an")

# --- craigduk76, 1.35.0 (GitHub #10, #11, #12) ---------------------------
print("\n--- craigduk76 (#10/#11/#12) ---")
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
CORE = "CoreVariables.cfg_patch_S2Tweaker.cfg"

# #10 Gespraechsabstand: bis 1.35.0 nur am Spieler - und der Tester musste
# genauso nah heran. Jeder Mensch traegt beide Schluessel selbst.
humans = gd.human_npc_sids()
carriers = [sid for sid in humans
            if gd.obj.children[sid].values.get("MaxDialogInteractDistance")]
check(len(carriers) == len(humans) and len(humans) > 1500,
      f"alle {len(humans)} menschlichen NPCs deklarieren den Gespraechsabstand selbst")
obj = cfgparse.parse(build_patches(gd, Settings(dialog_range_factor=1.5))[OBJ])
touched = {sid for sid, node in obj.children.items()
           if "MaxDialogInteractDistance" in node.values}
check("Player" in touched and len(touched & set(humans)) == len(humans),
      f"1.36.0: Spieler UND alle {len(humans)} Menschen bekommen den neuen Abstand")
check(not touched - set(humans) - {"Player"},
      "Mutanten bleiben draussen (sie reden nicht)")
check(obj.children["Player"].values["MinDialogInteractDistance"] == "112.5"
      and obj.children["Player"].values["MaxDialogInteractDistance"] == "195.0",
      "Spieler: 75/130 -> 112.5/195.0 (wie im Debug-Export des Testers)")
sample = next(sid for sid in humans
              if gd.obj.children[sid].values.get("MaxDialogInteractDistance", "").strip() == "250.f")
check(obj.children[sample].values["MaxDialogInteractDistance"] == "375.0f",
      f"Literalform bleibt: {sample} 250.f -> 375.0f")
check(OBJ not in build_patches(gd, Settings(dialog_range_factor=1.0)),
      "Vanilla-Stellung schreibt keinen einzigen NPC")

# #10 Dialog-Zoom / #11 Leiter: die Felder gibt es noch (alte Presets),
# aber sie schreiben nichts mehr - im Spiel nachweislich ohne Wirkung.
core = build_patches(gd, Settings(dialog_fov=105, ladder_free_look=True,
                                  look_straight_down=True)).get(CORE, "")
check("DialogFOVDefault" not in core and "ClimbView" not in core,
      "zurueckgezogen: Dialog-Zoom und Leiter-Umschauen schreiben nichts mehr")
check("ViewPitchDownLimit = -90.0" in core,
      "'Look straight down' bleibt - vom Tester bestaetigt")

# #12 Ausnuechtern: 25 % bestaetigt, Wunsch 1 % - kein Rundungsloch.
for factor, want in ((0.25, "0.25"), (0.01, "0.01")):
    obj = cfgparse.parse(build_patches(gd, Settings(sober_up_factor=factor))[OBJ])
    check(obj.children["Player"].children["VitalParams"].values["DegenDrunknessPoints"] == want,
          f"Ausnuechtern {factor:.0%} -> DegenDrunknessPoints = {want}")

# #9/#10/#11: was die Oberflaeche NICHT mehr anbietet (statisch, kein Fenster)
from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS
gone = {"dialog_fov"} & set(SLIDER_FIELDS) | {"ladder_look", "rq_jobs_instant",
                                              "rq_jobs_multi"} & set(CHECK_FIELDS)
check(not gone, f"die vier zurueckgezogenen Bedienelemente sind weg{sorted(gone)}")
check("sober" in SLIDER_FIELDS and "rq_jobs" in SLIDER_FIELDS and "look_down" in CHECK_FIELDS,
      "die bestaetigten Nachbarn bleiben")

print(f"\n=== {ok} Pruefungen gruen ===")
