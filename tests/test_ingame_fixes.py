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
      nicht. Sein "seltsames" Symptom (Abbruch-Zeile bleibt stehen) ist
      die Nebenwirkung unseres End-Knoten-Schluessels - der EINZIGE
      {bpatch} des Schalters, und der kam an. -> Dritter Entwurf, nur
      noch {bpatch} an vorhandenen Knoten (Block 1); der Pin-Schalter
      ist zurueckgezogen.

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


# --- 1) Mehrere Jobs je Gespraech (dritter Entwurf, 09.09.2026) -----------
# Die ersten zwei Entwuerfe haengten neue Knoten an und taten im Spiel
# nichts. Dieser besteht nur aus {bpatch} an vorhandenen Knoten - der Art
# Aenderung, die nachweislich ankommt (der Pool-Regler, der End-Knoten).
# Vorlage: Zone Borders / Contracts (Nexus 2638) entfernt genau die
# Abschalt-Launcher am Dialog; wir drehen dieselben auf Excluding = false.
print("\n1) Accept several jobs in one conversation")
check(build() == {}, "Vanilla-Stellung erzeugt nichts")

MENU = "DialogPrototypes/DialogPrototypes_patch_S2Tweaker.cfg"
JOBS = "QuestNodePrototypes/S2Tweaker_Jobs.cfg"
p = build(repeatable_jobs_multi=True)
check(set(p) == {QUESTS, MENU, JOBS},
      f"drei Patchdateien - Wachen, Menue-Boden, Taken/Clear: {sorted(p)}")
raw = p[QUESTS]
nodes = cfgparse.parse(raw).children
givers = gd.repeatable_quest_givers()
check(len(givers) == 8, f"{len(givers)} Auftraggeber erkannt")

# 1a) KEIN neuer Knoten: jeder Top-Level-Struct existiert in Vanilla und
#     alles traegt {bpatch} - es wird nur zusammengefuehrt, nie angehaengt.
new = [sid for sid in nodes if sid not in gd.questnodes.children]
check(not new, f"kein einziger neuer Knoten{new}")
check(raw.count(" : struct.begin") == raw.count("{bpatch}"),
      "jeder Struct und jeder Array-Eintrag traegt {bpatch}")

# 1b) Je Geber: die Zusage-Wache und die Job-Start-Wachen des Dialogs
#     stehen auf Excluding = false, jeder Eintrag KOMPLETT (alle
#     Verbindungen mit SID), auf seinem Vanilla-Index. Die Finish-Wache
#     bleibt unangetastet - wie bei der Vorlage.
total_flipped, total_starts = 0, 0
for giver in givers:
    dlg = nodes[giver["dialog_sid"]]
    vanilla = gd.questnodes.children[giver["dialog_sid"]].children["Launchers"].children
    flipped = dlg.children["Launchers"].children
    assert list(dlg.children) == ["Launchers"] and not dlg.values, giver["quest"]
    for idx, entry in flipped.items():
        assert idx in vanilla, (giver["quest"], idx)
        assert entry.values == {"Excluding": "false"}, (giver["quest"], idx, entry.values)
        v_conns = vanilla[idx].children["Connections"].children
        p_conns = entry.children["Connections"].children
        assert list(p_conns) == list(v_conns), (giver["quest"], idx)
        for cidx in v_conns:
            assert p_conns[cidx].values["SID"] == v_conns[cidx].values["SID"].strip()
    sources = {c.values["SID"] for e in flipped.values()
               for c in e.children["Connections"].children.values()}
    assert giver["accept"] in sources, giver["quest"]

    def _sources(entry):
        return [c.values.get("SID", "").strip()
                for c in entry.children["Connections"].children.values()]

    excluding = {i: e for i, e in vanilla.items()
                 if e.values.get("Excluding", "").strip() == "true"}
    finish = [i for i, e in excluding.items() if any(s.endswith("_Finish") for s in _sources(e))]
    starts = [i for i, e in excluding.items()
              if all("OnJournalQuestEvent" in s and s.endswith("_Start") for s in _sources(e))]
    assert finish and not (set(finish) & set(flipped)), (giver["quest"], finish)
    assert set(starts) <= set(flipped), (giver["quest"], starts, list(flipped))
    assert len(flipped) == 1 + len(starts), (giver["quest"], len(flipped), len(starts))
    total_flipped += len(flipped)
    total_starts += len(starts)
check(total_flipped == 8 + total_starts and total_starts == 22,
      f"{total_flipped} Wachen gedreht: 8 Zusagen + {total_starts} Job-Start-Wachen; "
      f"die 8 Finish-Wachen bleiben")

# 1c) Gegenprobe an den Spieldaten: in Vanilla schaltet die Zusage den
#     Dialog wirklich per Excluding ab - die Messung, auf der alles beruht.
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

# 1d) Die Zusage selbst wartet eine Sekunde (StartDelay 1.0) und ist
#     wiederholbar - darum reicht das Umdrehen: sie startet den Dialog
#     danach selbst neu.
for giver in givers:
    acc = gd.questnodes.children[giver["accept"]]
    assert acc.values.get("Repeatable", "").strip() == "true", giver["quest"]
    assert acc.values.get("StartDelay", "").strip() == "1.0", giver["quest"]
check(True, "jede Zusage ist wiederholbar und wartet 1 s - der Dialog kommt nach ihr zurueck")

# 1e) Das Abgeben: der End-Knoten hinter dem Rundenaufraeumer raeumt in
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
    assert end_sid and giver["end_exclude"] == "true", giver["quest"]
    assert nodes[end_sid].values == {"ExcludeAllNodesInContainer": "false"}, end_sid
    assert not nodes[end_sid].children, end_sid
check(True, "jeder der acht End-Knoten bekommt GENAU diesen einen Schluessel auf false")

# 1f) Der Aufraeumer, die Zusage und der Abbruch-Dialog bleiben vanilla.
for giver in givers:
    assert giver["cleanup_sid"] not in nodes and giver["accept"] not in nodes, giver["quest"]
check(True, "Aufraeumer und Zusage werden nicht angefasst")

# Gegenprobe: ohne den Schalter bleiben Dialog und End-Knoten unberuehrt
only_limit = build(repeatable_jobs_per_round=6)
if only_limit:
    assert "ExcludeAllNodesInContainer" not in only_limit.get(QUESTS, "")
    assert "Excluding" not in only_limit.get(QUESTS, "")
    assert MENU not in only_limit and JOBS not in only_limit
check(True, "ohne den Schalter fasst nichts den Dialog, den End-Knoten oder das Menue an")

# 1g) Teil 2 - der Menue-Boden in DialogPrototypes ({bpatch}, erste
#     Patchdatei des Werkzeugs dort). Jede Kette beginnt mit einem If:
#     Zusage noch nicht erfolgt -> Menue, sonst -> Abbruch-Zweig. Der
#     False-Zweig zeigt jetzt auf dasselbe Ziel wie der True-Zweig.
menu = cfgparse.parse(p[MENU]).children
check(len(menu) == 8, f"{len(menu)} If-Knoten, einer je Dialogkette")
for giver in givers:
    chain = giver["dialog_node"].values["DialogChainPrototypeSID"].strip()
    if_sid, menu_target, cancel_target = gd.job_menu_switch(chain, giver["accept"])
    node = menu[if_sid]
    assert not node.values and list(node.children) == ["NextDialogOptions"], if_sid
    branches = node.children["NextDialogOptions"].children
    assert list(branches) == ["False"], (if_sid, list(branches))
    assert branches["False"].values == {"NextDialogSID": menu_target}, if_sid
    assert menu_target != cancel_target, if_sid
    # Ziel und If-Knoten existieren in Vanilla; Vanilla-False fuehrt woandershin
    vanilla_if = gd.dialogs.children[if_sid]
    assert menu_target in gd.dialogs.children and cancel_target in gd.dialogs.children, if_sid
    v_false = vanilla_if.children["NextDialogOptions"].children["False"].values["NextDialogSID"].strip()
    assert v_false == cancel_target, (if_sid, v_false)
check(True, "je Kette zeigt nur der False-Zweig um - auf das Vanilla-Ziel des True-Zweigs")
check(raw.count(" : struct.begin") == raw.count("{bpatch}") and
      p[MENU].count(" : struct.begin") == p[MENU].count("{bpatch}"),
      "auch im Menue-Boden traegt jeder Struct {bpatch}")

# 1h) Teil 3 - Taken/Clear je Job in einer EIGENEN Datei ohne {bpatch},
#     Knoten fuer Knoten wie bei der Vorlage.
jobs = cfgparse.parse(p[JOBS]).children
slots = {g["quest_sid"]: gd.repeatable_job_slots(g["quest_sid"]) for g in givers}
n_slots = sum(len(v) for v in slots.values())
check(n_slots == 69 and all(len(slots[g["quest_sid"]]) == g["pool"] for g in givers),
      f"{n_slots} Auftrags-Behaelter, je Geber genau so viele wie sein Pool")
check(len(jobs) == 2 * n_slots and "{bpatch}" not in p[JOBS],
      f"{len(jobs)} neue Knoten (Taken + Clear je Behaelter), kein {{bpatch}}")


def _conn(node):
    return node.children["Launchers"].children["[0]"].children["Connections"].children["[0]"].values["SID"]


for g in givers:
    for slot in slots[g["quest_sid"]]:
        tag = slot["container"].rsplit("_", 1)[-1]
        taken = jobs[f"S2T_{g['quest_sid']}_Taken_{tag}"]
        clear = jobs[f"S2T_{g['quest_sid']}_Clear_{tag}"]
        assert taken.values["NodeType"] == "EQuestNodeType::Technical" and taken.values["StartDelay"] == "3.0"
        assert taken.values["Repeatable"] == "true" and clear.values["Repeatable"] == "true"
        assert _conn(taken) == slot["pin"], (taken.values["SID"], _conn(taken))
        assert _conn(clear) == taken.values["SID"]
        assert clear.values["NodeType"] == "EQuestNodeType::BridgeCleanUp"
        cleaned = list(clear.children["NodesToCleanUpResults"].values.values())
        assert cleaned == [slot["add"], g["accept"]], (clear.values["SID"], cleaned)
        for sid in (slot["pin"], slot["add"], slot["container"]):
            assert sid in gd.questnodes.children, sid
        assert taken.values["SID"] not in gd.questnodes.children
check(True, "jeder Taken-Knoten haengt am Pin seines Behaelters, jeder Clear loescht "
            "GENAU Add_C0x + Zusage - alle Ziele existieren, keiner der Namen kollidiert")

# Vanilla-Gegenprobe zur Menue-Steuerung: die Optionen der Warlock-Kette
# haengen per Bridge-Bedingung an den sechs Add_C0x - darum blendet das
# Loeschen den Job aus.
warlock = next(g for g in givers if g["quest"] == "RSQ01")
adds = {s["add"] for s in slots[warlock["quest_sid"]]}
chain = warlock["dialog_node"].values["DialogChainPrototypeSID"].strip()
linked = set()
for node in gd.dialogs.children.values():
    if (node.values.get("DialogChainPrototypeSID") or "").strip() != chain:
        continue
    stack = [node]
    while stack:
        cur = stack.pop()
        v = (cur.values.get("LinkedNodePrototypeSID") or "").strip()
        if v in adds:
            linked.add(v)
        stack.extend(cur.children.values())
check(linked == adds, f"das Warlock-Menue haengt an allen {len(adds)} Add_C0x ({len(linked)} gefunden)")

# Zusammenspiel mit den zwei aelteren Reglern derselben Familie
both = build(repeatable_jobs_multi=True, repeatable_jobs_per_round=6,
             repeatable_quest_factor=0.04)
txt = both[QUESTS]
check("Excluding = false" in txt and "VariableValue = 6" in txt and "InGameHours = 1" in txt,
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
gone = {"dialog_fov"} & set(SLIDER_FIELDS) | {"ladder_look", "rq_jobs_instant"} & set(CHECK_FIELDS)
check(not gone, f"die drei zurueckgezogenen Bedienelemente sind weg{sorted(gone)}")
check("sober" in SLIDER_FIELDS and "rq_jobs" in SLIDER_FIELDS and "look_down" in CHECK_FIELDS
      and "rq_jobs_multi" in CHECK_FIELDS,
      "die bestaetigten Nachbarn bleiben, der Mehrfach-Job-Schalter ist als dritter Entwurf da")

print(f"\n=== {ok} Pruefungen gruen ===")
