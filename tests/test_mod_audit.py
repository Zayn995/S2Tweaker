"""Neunte Datenrecherche (07.09.2026): was beim Gegenlesen von 27 fremden
Mods herauskam — zwei Korrekturen an ausgeliefertem Code und zehn neue
Stellschrauben.

Alle Sollwerte werden LIVE aus vanilla/ gelesen; die Zahlen in den
Kommentaren sind der Messstand vom 07.09.2026 und dienen nur der Lesbarkeit.

Aufbau wie in tests/test_mod_harvest.py: ein Block je Fund.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize, UPGRADE_FAMILIES
from s2tweaker import cfgparse

gd = GameData(VANILLA)
EFFECTS = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
CWS = "WeaponData/CharacterWeaponSettingsPrototypes/CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg"
EFFMAX = "ObjEffectMaxParamsPrototypes/ObjEffectMaxParamsPrototypes_patch_S2Tweaker.cfg"
LAIRS = "LairPrototypes/LairPrototypes_patch_S2Tweaker.cfg"
DIRECTOR = ("ALifePrototypes/ALifeDirectorScenarioPrototypes/"
            "ALifeDirectorScenarioPrototypes_patch_S2Tweaker.cfg")

ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


def parse(patches, key):
    assert key in patches, f"Patchdatei fehlt: {key}\nda: {sorted(patches)[:12]}"
    return cfgparse.parse(patches[key]).children


def build(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


# --- 0) Neutral erzeugt nichts ------------------------------------------
print("\n0) Neutral")
check(build() == {}, "Vanilla-Stellung erzeugt keine Datei")


# --- 1) Ausruestungs-Verschleiss in Anomalien ---------------------------
print("\n1) Anomaly wear on gear (Corrosion-Familie)")
corrosion = {sid for sid, n in gd.effects.children.items()
             if (n.values.get("Type") or "").replace("EEffectType::", "").strip()
             in ("Corrosion", "VelocityCorrosion")}
check(len(corrosion) >= 25, f"vanilla fuehrt {len(corrosion)} Corrosion-Effekte")
check("ButtStroke_Corrosion" in corrosion, "der Kolbenschlag gehoert derselben Familie an")

eff = parse(build(anomaly_wear_factor=0.5), EFFECTS)
scaled = {sid for sid in eff if sid in corrosion}
check("ButtStroke_Corrosion" not in eff,
      "der Kolbenschlag bleibt seinem eigenen Regler ueberlassen")
check(len(scaled) >= 24, f"{len(scaled)} Corrosion-Effekte werden halbiert")
carousel = eff.get("CarouselCorrosion_Body")
check(carousel is not None and carousel.values.get("ValueMin") == "5.0",
      f"CarouselCorrosion_Body 10 -> {carousel.values.get('ValueMin') if carousel else '-'}")
check("CarouselCorrosion" not in eff,
      "der Composite-Elternteil (0.f) bleibt unberuehrt")

both = parse(build(anomaly_wear_factor=0.5, butt_wear_factor=0.5), EFFECTS)
check("ButtStroke_Corrosion" in both and both["ButtStroke_Corrosion"].values.get("ValueMin"),
      "zusammen mit dem Kolbenschlag-Regler stehen beide in der Datei")


# --- 2) Maximale Haltbarkeit --------------------------------------------
print("\n2) Weapon & armor max condition (BaseDurability)")
gear = gd.gear_durability()
check(len(gear) > 100, f"{len(gear)} Waffen/Ruestungen tragen eine BaseDurability")
check(all(v > 1.0 for _c, v in gear.values()),
      "der 1.0-Platzhalter des Basis-Structs ist ausgefiltert")
items = parse(build(gear_durability_factor=2.0), ITEMS)
sample = next(sid for sid, (_c, v) in sorted(gear.items()) if v > 1000)
vanilla = gear[sample][1]
got = float(items[sample].values["BaseDurability"])
check(abs(got - vanilla * 2) < 0.01, f"{sample}: {vanilla} -> {got}")
check(len([s for s in items if "BaseDurability" in items[s].values]) == len(gear),
      "jede Ausruestung bekommt genau eine Zeile")


# --- 3) Zwei weitere Munitions-Faktoren ---------------------------------
print("\n3) Ammo spread / spread while aiming")
kinds = gd.ammo_mods()
with_disp = [sid for sid, m in kinds.items() if "DispersionMod" in m]
# 35 Treffer stehen in der Datei, davon ist einer die Vorlage TemplateAmmo -
# ammo_mods() liefert nur die echten Sorten.
check(len(with_disp) == 34, f"{len(with_disp)} echte Sorten tragen DispersionMod")
ammo = parse(build(ammo_dispersion_factor=2.0), ITEMS)
sid = sorted(with_disp)[0]
check(float(ammo[sid].values["DispersionMod"]) == kinds[sid]["DispersionMod"] * 2,
      f"{sid}: DispersionMod verdoppelt")
aim = parse(build(ammo_aim_dispersion_factor=0.5), ITEMS)
check("AimDispersionMod" in aim[sorted(with_disp)[0]].values,
      "AimDispersionMod wird separat geschrieben")
# Override je Sorte schlaegt den globalen Regler (Kaskade wie bei den anderen)
over = parse(build(ammo_dispersion_factor=2.0,
                   ammo_overrides={sid: {"dispersion": 4.0}}), ITEMS)
check(float(over[sid].values["DispersionMod"]) == kinds[sid]["DispersionMod"] * 4,
      "Einzelsorten-Override ersetzt den globalen Faktor")


# --- 4) Schaden auf Extremdistanz ---------------------------------------
print("\n4) Damage at extreme range")
far = parse(build(far_damage_factor=2.0), CWS)
rows = [n for n in far.values() if "MinBulletDistanceDamageModifier" in n.values]
# Der Schluessel steht an allen 150 CWS-Structs, aber der Regler ist ein
# SPIELER-Regler: er trifft nur die Structs der Spielerwaffen (die NPC-
# Seite hat ihren eigenen Reichweiten-Regler).
check(50 <= len(rows) <= 100, f"{len(rows)} Spieler-CWS-Structs bekommen den Boden angehoben")
values = [float(n.values["MinBulletDistanceDamageModifier"]) for n in rows]
check(max(values) <= 1.0, f"Deckel 1.0 haelt (groesster Wert {max(values)})")
check(not [n for n in far.values()
           if "MinBulletDistanceArmorPiercingModifier" in n.values],
      "nach oben ruehrt der Regler den Durchschlag nicht an (steht schon auf 1.0)")
down = parse(build(far_damage_factor=0.5), CWS)
ap = [n for n in down.values() if "MinBulletDistanceArmorPiercingModifier" in n.values]
check(len(ap) >= 50, f"nach unten schon: {len(ap)} Structs verlieren Durchschlag auf Distanz")
check(build(far_damage_factor=1.0) == {}, "auf Vanilla erzeugt der Regler nichts")


# --- 5) Die zwei restlichen Effekt-Deckel -------------------------------
print("\n5) Stamina & bleeding caps")
caps = parse(build(effect_cap_other_factor=2.0), EFFMAX)
entries = caps["DefaultEffectMaxParamsSID"].children["MaxEffectValues"].children
sids = {e.values.get("EffectSID") for e in entries.values()}
check(sids == {"EEffectType::RegenStamina", "EEffectType::DegenBleeding"},
      f"genau die zwei bisher ungedeckten Eintraege: {sorted(sids)}")
for e in entries.values():
    if e.values["EffectSID"].endswith("RegenStamina"):
        check(e.values["MaxValue"] == "60.0f", f"RegenStamina 30 -> {e.values['MaxValue']}")


# --- 6) Lager: Startbefuellung und seltene Archetypen -------------------
print("\n6) Lair starting occupancy / rare archetypes")
blocks = gd.lair_blocks()
inis = [b for b in blocks if b["initial"] and not b["guard"]]
check(len(inis) > 500, f"{len(inis)} Nicht-Wachen-Bloecke tragen eine Startbefuellung")
lair = parse(build(lair_initial_fill_factor=2.0), LAIRS)


def walk(node, path):
    for seg in path:
        node = node.children[seg]
    return node


hits = 0
for name, node in lair.items():
    for fac in node.children["Preset"].children["PossibleInhabitantFactions"].children.values():
        for rank in fac.children["SpawnSettingsPerPlayerRanks"].children.values():
            v = rank.values.get("InitialSpawnQuantityPercent")
            if v is not None:
                hits += 1
                check(float(v) <= 1.0, "Startbefuellung ist bei 1.0 gedeckelt") if hits == 1 else None
check(hits > 500, f"{hits} Bloecke bekommen die neue Startbefuellung")
check(not any(n.startswith("Guard") for n in lair),
      "Wachen-Lager bleiben unangetastet")

rare = parse(build(lair_rare_archetype_factor=2.0), LAIRS)
weights = []
for node in rare.values():
    for fac in node.children["Preset"].children["PossibleInhabitantFactions"].children.values():
        for rank in fac.children["SpawnSettingsPerPlayerRanks"].children.values():
            arch = rank.children.get("SpawnSettingsPerArchetypes")
            for a in (arch.children.values() if arch else ()):
                weights.append(float(a.values["SpawnWeight"]))
check(weights, f"{len(weights)} Archetyp-Gewichte werden angehoben")
check(all(0 < w <= 1.0 for w in weights),
      f"nur echte Seltenheiten, Deckel 1.0 (min {min(weights)}, max {max(weights)})")


# --- 7) Director: Ausbreitung und Notnagel ------------------------------
print("\n7) Lair expansion / fallback spawn count")
d = parse(build(lair_expansion_player_factor=2.0), DIRECTOR)
preset = next(iter(d.values()))
check(preset.values.get("DefaultALifeLairExpansionToPlayerTimeMin") == "60",
      f"120 min -> {preset.values.get('DefaultALifeLairExpansionToPlayerTimeMin')} (invers)")
d2 = parse(build(fallback_spawn_count=10), DIRECTOR)
check(next(iter(d2.values())).values.get("FallbackMaxSpawnCount") == "10",
      "FallbackMaxSpawnCount wird absolut gesetzt")
check(build(fallback_spawn_count=3) == {}, "der Vanilla-Wert 3 erzeugt nichts")


# --- 8) Korrektur: Upgrade-Familien -------------------------------------
print("\n8) Korrektur - Accuracy und MovementSpeed haengen jetzt an einem Regler")
types = {t for fam in UPGRADE_FAMILIES.values() for t in fam}
check("Accuracy" in types, "Effekt-Typ Accuracy ist einer Familie zugeordnet")
check("MovementSpeed" in types, "Effekt-Typ MovementSpeed ebenso")
acc = parse(build(upg_accuracy_factor=2.0), EFFECTS)
check("AccuracyEffect" in acc,
      f"AccuracyUpgrade wird jetzt skaliert: {acc.get('AccuracyEffect').values if 'AccuracyEffect' in acc else '-'}")
check(acc["AccuracyEffect"].values["ValueMin"] == "100.0%",
      f"50 % x2 = {acc['AccuracyEffect'].values['ValueMin']}")
mov = parse(build(upg_armor_misc_factor=2.0), EFFECTS)
check("MovementSpeedEffect" in mov, "MovementSpeedUpgrade ebenso")
# Die zwei mehrdeutigen Aim-Modifikatoren bleiben unberuehrt: ihre
# Vanilla-Werte sind positiv (+70 %), und "neg" skaliert nur Boni.
check("DispersionAimModifierNeg70Effect" not in acc,
      "der +70-%-Eintrag des Rhino-Upgrades bleibt vanilla (Vorzeichen unklar)")


# --- 9) Korrektur: Composite-Effekte ------------------------------------
print("\n9) Korrektur - Composite-Effekte ziehen mit")
comp = parse(build(upg_accuracy_factor=2.0, upg_handling_factor=2.0), EFFECTS)
accs = comp.get("BattleExoskeleton_Varta_Armor_accuracy")
check(accs is not None,
      "der Composite 'Accuracy 20 %' wird mitskaliert, wenn alle Kinder denselben Faktor haben")
check(accs.values.get("ValueMin") == "40.0%", f"20 % -> {accs.values.get('ValueMin')}")
only_one = parse(build(upg_handling_factor=2.0), EFFECTS)
check("BattleExoskeleton_Varta_Armor_accuracy" not in only_one,
      "bei gemischten Faktoren (nur handling) bleibt die Anzeige vanilla")


# --- 10) Statbalken: Accuracy und Handling ------------------------------
print("\n10) Statbalken - Accuracy und Handling")
bars = parse(build(stat_bars_follow=True, spread_factor=0.5, aim_time_factor=2.0), CWS)
acc_rows = [n for n in bars.values() if "AccuracyUI" in n.values]
hand_rows = [n for n in bars.values() if "HandlingUI" in n.values]
check(acc_rows, f"{len(acc_rows)} Structs bekommen einen Genauigkeits-Balken")
check(hand_rows, f"{len(hand_rows)} Structs bekommen einen Handling-Balken")
check(all(float(n.values["AccuracyUI"]) <= 1.0 for n in acc_rows),
      "der Balken bleibt bei 1.0 gedeckelt")
check(not [n for n in parse(build(spread_factor=0.5), CWS).values() if "AccuracyUI" in n.values],
      "ohne die Checkbox bewegt sich kein Balken")


# --- 11) Zusammenfassung nennt die neuen Regler -------------------------
print("\n11) Tweak-Liste")
text = "\n".join(summarize(Settings(
    anomaly_wear_factor=0.5, gear_durability_factor=2.0, far_damage_factor=2.0,
    effect_cap_other_factor=2.0, lair_initial_fill_factor=2.0,
    lair_rare_archetype_factor=2.0, lair_expansion_player_factor=2.0,
    fallback_spawn_count=10, ammo_dispersion_factor=2.0,
    ammo_aim_dispersion_factor=2.0)))
for needle in ("Anomaly wear", "max condition", "extreme range", "caps",
               "starting occupancy", "Rare lair", "expansion", "Fallback",
               "Ammo spread"):
    check(needle in text, f"Tweak-Liste nennt '{needle}'")

print(f"\n=== {ok} Pruefungen gruen ===")
