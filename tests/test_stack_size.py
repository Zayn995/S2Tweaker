"""Stapelgroesse im Inventar (GitHub Issue #7, Molkerr, 07.09.2026).

Die Anfrage: "Is it possible to add a function to increase stack size in the
inventory (for example, ammo more than 900 per stack)?"

Gemessen VOR dem Bauen (Projektregel: erst die Daten, dann Code) — der
Schluessel `MaxStackCount` steht 1375x in ItemPrototypes.cfg:

    900     35x   Munition (TemplateAmmo + 34 Sorten)  <- die einzige Grenze,
                  die im Spiel wirklich stoert
    999    607x   Waffen, Ruestung, Artefakte, Aufsaetze, Nahrung, Medizin
    300000 701x   PDAs, Notizen, Schluessel, Questgegenstaende, Granaten
    1       31x   Ferngläser, Detektoren, Weird-Artefakte, GELDKARTEN
    100      1x   Malahit_KeyCard

Die 1er sind eine Design-Entscheidung des Spiels und bleiben unangetastet —
`stack_counts()` filtert alles <= 1 heraus. Das prueft dieser Test, ebenso
den Deckel bei 300000 (der Wert, den das Spiel selbst fuer "unbegrenzt"
benutzt) und dass Stueckzahlen ganzzahlig bleiben.
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
KEY = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"


def items(patches):
    return cfgparse.parse(patches[KEY]).children


# --- 1) Bestand live gegen die Spieldaten -------------------------------
ammo = gd.stack_counts("ammo")
cons = gd.stack_counts("consumable")
assert len(ammo) == 34, len(ammo)
assert set(ammo.values()) == {900}, sorted(set(ammo.values()))
assert len(cons) == 22, len(cons)
assert set(cons.values()) == {999}, sorted(set(cons.values()))
print(f"Live: {len(ammo)} Munitionssorten auf 900, {len(cons)} Konsumgueter auf 999  OK")

# Die bewussten Einzelstuecke duerfen NICHT auftauchen
for sid in ("Binoculars_01", "Veles", "AArtifactWeirdBolt", "MoneyCommon", "GuitarUsable"):
    for cat in ("ammo", "consumable", "misc", "artifact"):
        assert sid not in gd.stack_counts(cat), f"{sid} darf nicht stapelbar werden"
print("Ferngläser, Detektoren, Weird-Artefakte, Geldkarten und Gitarre bleiben draussen  OK")

# --- 2) Neutral erzeugt nichts ------------------------------------------
assert not build_patches(gd, Settings())
print("Neutral: kein Patch  OK")

# --- 3) Globaler Munitions-Regler ---------------------------------------
p = items(build_patches(gd, Settings(ammo_stack_factor=10.0)))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert len(hit) == 34, len(hit)
assert set(hit.values()) == {"9000"}, set(hit.values())
assert "TemplateAmmo" not in hit, "die Vorlage wird nicht gepatcht"
print(f"Munition x10: {len(hit)} Sorten auf 9000, ganzzahlig  OK")

# --- 4) Deckel und Untergrenze ------------------------------------------
p = items(build_patches(gd, Settings(ammo_stack_factor=1000.0)))
werte = {n.values["MaxStackCount"] for n in p.values() if "MaxStackCount" in n.values}
assert werte == {"300000"}, werte      # 900 * 1000 = 900000 -> gedeckelt
p = items(build_patches(gd, Settings(ammo_stack_factor=0.0)))
werte = {n.values["MaxStackCount"] for n in p.values() if "MaxStackCount" in n.values}
assert werte == {"1"}, werte           # nie unter 1
print("Deckel 300000 und Untergrenze 1 halten  OK")

# --- 5) Nahrung & Medizin getrennt --------------------------------------
p = items(build_patches(gd, Settings(consumable_stack_factor=3.0)))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert len(hit) == 22 and set(hit.values()) == {"2997"}, (len(hit), set(hit.values()))
assert not any(sid in hit for sid in ammo), "Munition darf hier nicht mitlaufen"
print("Nahrung/Medizin x3: 22 Gegenstaende auf 2997, Munition unberuehrt  OK")

# --- 6) Pro Sorte (der Baum im Ammo-Tab) --------------------------------
p = items(build_patches(gd, Settings(ammo_overrides={"A545D": {"stack": 5.0}})))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert hit == {"A545D": "4500"}, hit
print("Einzelne Sorte x5: nur A545D auf 4500  OK")

# Die eigene Sorte schlaegt den globalen Regler (wie bei den vier Mods)
p = items(build_patches(gd, Settings(ammo_stack_factor=2.0,
                                     ammo_overrides={"A545D": {"stack": 5.0}})))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert hit["A545D"] == "4500" and hit["A762D"] == "1800", (hit["A545D"], hit["A762D"])
print("Sorte schlaegt global (4500 neben 1800)  OK")

# --- 7) Die vier alten Mods bleiben unberuehrt --------------------------
p = items(build_patches(gd, Settings(ammo_stack_factor=2.0)))
for sid, node in p.items():
    assert set(node.values) == {"MaxStackCount"}, (sid, node.values)
print("Der Stapel-Regler fasst DamageMod & Co. nicht an  OK")

# --- 8) Tweak-Liste -----------------------------------------------------
lines = summarize(Settings(ammo_stack_factor=10.0, consumable_stack_factor=2.0))
assert any("Ammo stack size" in l for l in lines), lines
assert any("Food & medicine stack size" in l for l in lines), lines
print("Zeilen in der Tweak-Liste  OK")

print("\nSTAPELGROESSEN-TEST OK")
