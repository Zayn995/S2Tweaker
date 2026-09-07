"""Jobs je Runde bei wiederholbaren Auftraegen (GitHub Issue #8, Molkerr).

Die Anfrage (07.09.2026): "is it possible to make function to talk to the
quest giver multiple times and accept several repeatable quests at once?"

Gemessen VOR dem Bauen (Projektregel: erst die Daten, dann Code). Jeder der
acht Auftraggeber hat in QuestNodePrototypes.cfg denselben Aufbau:

  * eine eigene Zaehler-Variable, die per `Add 1` je ausgegebenem Job
    hochzaehlt — im ganzen 77-MB-File gibt es dazu KEIN Herunterzaehlen,
    nur ein einziges `Set 0` (der Reset nach dem Timer). Der Zaehler zaehlt
    also ausgegebene Jobs pro Runde, nicht gehaltene.
  * einen If-Knoten `Less <Zaehler> 3` — das Limit. Das ist die einzige
    Zahl, die begrenzt.
  * einen SetTimer mit 24 Stunden, der den Zaehler zurueksetzt — das ist
    der vorhandene Cooldown-Regler.
  * einen SetDialog-Knoten, der in Vanilla am FALSE-Ausgang des Limit-
    Knotens haengt: der Job-Dialog wird erst wieder scharf, wenn der Geber
    LEER ist. Genau das ist der Grund, warum man vanilla einen Job je
    Besuch bekommt.

Gegengeprueft an der Nexus-Mod "New Game Start" (1211): sie setzt genau
diese Zahl auf 6 und haengt genau diese Verbindung auf True — inklusive der
Eigenheit, dass der Verbindungs-Index NICHT bei allen Gebern gleich ist
(viermal [0], viermal [1]). Der Accessor sucht ihn darum, statt ihn
anzunehmen; dieser Test haelt das fest.

Prueft: Live-Bestand, Neutralzustand (und dass die 75-MB-Datei dann gar
nicht erst angefasst wird), Limit-Patch mit komplettem Bedingungs-Eintrag,
Deckelung je Aufgaben-Topf, Dialog-Umbau mit komplettem Launcher-Eintrag,
dass nur RSQ-Knoten angefasst werden, das Zusammenspiel mit dem Cooldown-
Regler und die Zeilen in der Tweak-Liste.
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
KEY = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"


def nodes(patches):
    assert KEY in patches, sorted(patches)
    return cfgparse.parse(patches[KEY]).children


# --- 1) Live-Bestand gegen die echten Spieldaten ------------------------
givers = gd.repeatable_quest_givers()
assert len(givers) == 8, [g["quest"] for g in givers]
assert [g["quest"] for g in givers] == [
    "RSQ01", "RSQ04", "RSQ05", "RSQ06", "RSQ07", "RSQ08", "RSQ09", "RSQ10"]
assert {g["cap"] for g in givers} == {3.0}, sorted({g["cap"] for g in givers})
assert {g["pin"] for g in givers} == {"False"}, sorted({g["pin"] for g in givers})
pools = {g["quest"]: g["pool"] for g in givers}
assert pools == {"RSQ01": 6, "RSQ04": 10, "RSQ05": 8, "RSQ06": 9,
                 "RSQ07": 9, "RSQ08": 9, "RSQ09": 9, "RSQ10": 9}, pools
print(f"Live: 8 Geber, Limit ueberall 3, Toepfe {sorted(set(pools.values()))}  OK")

# Der Verbindungs-Index ist NICHT einheitlich - genau deshalb wird er gesucht
conn_idx = {g["quest"]: g["link_path"][1] for g in givers}
assert set(conn_idx.values()) == {"[0]", "[1]"}, conn_idx
print(f"Verbindungs-Index gemischt ({sorted(set(conn_idx.values()))}) und je Geber gesucht  OK")

# --- 2) Neutral: kein Patch, und die 75-MB-Datei bleibt ungelesen -------
fresh = GameData(VANILLA)
assert not build_patches(fresh, Settings())
assert "questnodes" not in fresh.__dict__, "Neutralzustand parst QuestNodePrototypes"
print("Neutral: kein Patch, 75-MB-Datei nicht angefasst  OK")

# --- 3) Limit-Patch: kompletter Bedingungs-Eintrag ----------------------
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6)))
assert len(p) == 8, sorted(p)
for sid, node in p.items():
    entry = node.children["Conditions"].children["[0]"].children["[0]"]
    # Array-Eintrag KOMPLETT (nicht nur der geaenderte Schluessel) - unter
    # beiden {bpatch}-Lesarten richtig, siehe docs/SPEC.md par. 0
    assert set(entry.values) == {
        "ConditionType", "ConditionComparance", "GlobalVariablePrototypeSID",
        "ChangeValueMode", "VariableValue"}, (sid, sorted(entry.values))
    assert entry.values["ConditionComparance"] == "EConditionComparance::Less"
    assert entry.values["VariableValue"] == "6", (sid, entry.values["VariableValue"])
print("Limit 6: 8 Knoten, Bedingung komplett mit allen fuenf Schluesseln  OK")

# --- 4) Deckelung je Aufgaben-Topf --------------------------------------
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=10)))
got = {sid: n.children["Conditions"].children["[0]"].children["[0]"].values["VariableValue"]
       for sid, n in p.items()}
by_quest = {q: got[g["cap_key"]] for q, g in
            ((g["quest"], g) for g in givers)}
assert by_quest == {"RSQ01": "6", "RSQ04": "10", "RSQ05": "8", "RSQ06": "9",
                    "RSQ07": "9", "RSQ08": "9", "RSQ09": "9", "RSQ10": "9"}, by_quest
print("Regler 10 wird je Geber auf seinen Topf gedeckelt (Warlock 6)  OK")

# Unter Vanilla geht auch
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=1)))
assert len(p) == 8
vals = {n.children["Conditions"].children["[0]"].children["[0]"].values["VariableValue"]
        for n in p.values()}
assert vals == {"1"}, vals
print("Regler 1: strenger als Vanilla, alle acht auf 1  OK")

# --- 5) Dialog-Umbau: kompletter Launcher-Eintrag -----------------------
p = nodes(build_patches(gd, Settings(repeatable_jobs_instant=True)))
assert len(p) == 8, sorted(p)
for giver in givers:
    node = p[giver["dialog_key"]]
    launcher_key, conn_key = giver["link_path"]
    launcher = node.children["Launchers"].children[launcher_key]
    # Der Launcher-Eintrag geht komplett raus: Excluding + ALLE Verbindungen
    assert "Excluding" in launcher.values, giver["quest"]
    conns = launcher.children["Connections"].children
    vanilla_conns = (giver["dialog_node"].children["Launchers"]
                     .children[launcher_key].children["Connections"].children)
    assert set(conns) == set(vanilla_conns), (giver["quest"], sorted(conns))
    for key, conn in conns.items():
        # SID bleibt an jeder Verbindung stehen
        assert conn.values["SID"] == vanilla_conns[key].values["SID"], (giver["quest"], key)
        want = "True" if key == conn_key else vanilla_conns[key].values.get("Name", "")
        assert conn.values.get("Name", "") == want, (giver["quest"], key, conn.values)
print("Dialog-Umbau: nur der eine Pin auf True, SIDs und Nachbarn unveraendert  OK")

# --- 6) Nur RSQ-Knoten, nichts aus Story-/Nebenquests -------------------
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6,
                                     repeatable_jobs_instant=True)))
assert len(p) == 16, sorted(p)
assert all(sid.startswith("RSQ") for sid in p), sorted(p)
print("16 Knoten, alle RSQ - Story- und Nebenquests bleiben vanilla  OK")

# --- 7) Zusammenspiel mit dem Cooldown-Regler (eine Datei) --------------
p = nodes(build_patches(gd, Settings(repeatable_jobs_per_round=6,
                                     repeatable_jobs_instant=True,
                                     repeatable_quest_factor=0.0)))
timers = [sid for sid, n in p.items() if "InGameHours" in n.values]
assert len(timers) == 8, timers
assert {n.values["InGameHours"] for sid, n in p.items() if sid in timers} == {"0"}
assert len(p) == 24, len(p)   # 8 Limit + 8 Dialog + 8 Timer, kein Knoten doppelt
print("Limit, Dialog und Cooldown teilen sich eine Patchdatei (24 Knoten)  OK")

# --- 8) Tweak-Liste ------------------------------------------------------
lines = summarize(Settings(repeatable_jobs_per_round=6, repeatable_jobs_instant=True))
assert any("Repeatable jobs per round 6" in l for l in lines), lines
assert any("next job right away" in l for l in lines), lines
assert not any("Repeatable jobs per round" in l for l in summarize(Settings()))
print("Zeilen in der Tweak-Liste  OK")

print("\nTEST JOBS JE RUNDE OK")
