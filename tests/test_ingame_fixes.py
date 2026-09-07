"""Was Molkerrs erster In-Game-Test ergeben hat (GitHub #9, 07.09.2026).

Sein Bericht, Punkt fuer Punkt:
  1. Stapelgroessen wirken  -> bestaetigt, nichts zu tun
  2. "Accepting multiple quests doesn't work" -> stimmt: der Limit-Regler
     aus 1.31.0 erhoeht nur den VORRAT je Runde. Neu in 1.33.0: ein
     zusaetzlicher Knoten je Geber macht den Dialog nach der Zusage wieder
     scharf (Schalter "Accept several jobs in one conversation").
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

new_nodes = [s for s in nodes if s.endswith("_S2T_ReArmDialog")]
check(len(new_nodes) == 8, f"{len(new_nodes)} neue Knoten, einer je Geber")
check(not [s for s in new_nodes if s in gd.questnodes.children],
      "keiner der neuen Namen existiert in Vanilla (wird also angehaengt)")

raw = p[QUESTS]
for sid in new_nodes:
    start = raw.index(f"{sid} : struct.begin")
    end = raw.index("\nstruct.end", start)
    block = raw[start:end]
    assert "{bpatch}" not in block, f"{sid} traegt bpatch"
check(True, "kein neuer Knoten traegt {bpatch} (nichts zum Zusammenfuehren)")

by_quest = {g["quest_sid"]: g for g in givers}
for sid in new_nodes:
    node = nodes[sid]
    quest = node.values["QuestSID"]
    giver = by_quest[quest]
    conn = node.children["Launchers"].children["[0]"].children["Connections"].children["[0]"]
    assert conn.values["SID"] == giver["accept"], (sid, conn.values["SID"])
    assert node.values["NodeType"] == "EQuestNodeType::Technical"
    assert node.values["Repeatable"] == "true"
check(True, "jeder neue Knoten haengt an der Zusage seines eigenen Gebers")

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

print(f"\n=== {ok} Pruefungen gruen ===")
