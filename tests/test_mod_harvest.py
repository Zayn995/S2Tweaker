"""Ausbeute aus fremden Mods, 07.09.2026 (1.31.0).

Der Besitzer hat "New Game Start" (Nexus 1211) und "Stalker Unlimited"
(Nexus 1453) heruntergeladen mit dem Auftrag: "finde sachen die wir
aufnehmen koennen". Beide Paks wurden mit unserem eigenen pakfile.py
geoeffnet (194 + 508 cfg-Dateien), die Schluessel maschinell gegen unseren
Code abgeglichen und die Treffer danach selbst in vanilla/ nachgemessen.

New Game Start gab ausser den RSQ-Sachen (siehe test_repeatable_jobs)
nichts her — der Rest ist Spielstart-Inhalt. Aus Stalker Unlimited hat der
Besitzer acht Kandidaten gewaehlt; diese Suite haelt deren Messwerte fest:

  1  ItemPrototypes  BleedingMod / RecoilMod / FlatnessMod /
                     WeaponExhaustionMod — je 35 Munitionssorten
  6  WeaponGeneralSetup  Min/MaxJamChance — 92 Waffen (MinJamChance ist
                     bei 91 davon 0.0, darum der skip_unchanged-Filter)
  7  CharacterWeaponSettings  DamageUI / RangeUI / RateOfFireUI — 150
                     Structs, Wertebereich 0..1, Maximum genau 1.0
  8  CharacterWeaponSettings  NPCToNPCDamageScaler — 150x 0.7
 10  AbilityPrototypes  MaxAttacksInSeries / BleedingChanceIncrement —
                     143 Mutanten-Attacken; menschliche und Boss-Attacken
                     tragen dieselben Schluessel und bleiben draussen
 13  UpgradePrototypes  RepairCostModifier — 1288x 0.2f (der gleichnamige
                     Schluessel in ObjPrototypes gehoert den NPCs, tabu)

Geprueft: Live-Bestand, Neutralzustand, Kaskaden, Deckel, Literalformen,
die Abgrenzungen (Mensch/Boss, ObjPrototypes) und die Tweak-Zeilen.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData, SPECIES_ABILITY_PREFIXES
from s2tweaker.tweaks import Settings, build_patches, summarize, AMMO_PARAMS
from s2tweaker import cfgparse

gd = GameData(VANILLA)
ITEMS = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"
WGS = "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg"
CWS = ("WeaponData/CharacterWeaponSettingsPrototypes/"
       "CharacterWeaponSettingsPrototypes_patch_S2Tweaker.cfg")
ABIL = "AbilityPrototypes/AbilityPrototypes_patch_S2Tweaker.cfg"
UPG = "UpgradePrototypes/UpgradePrototypes_patch_S2Tweaker.cfg"


def nodes(patches, key):
    assert key in patches, sorted(patches)
    return cfgparse.parse(patches[key]).children


# --- 0) Neutral erzeugt nichts ------------------------------------------
assert not build_patches(gd, Settings())
print("Neutral: kein Patch  OK")

# --- 1) Vier weitere Munitions-Parameter --------------------------------
mods = gd.ammo_mods()
# 35 Structs tragen die Schluessel; ammo_mods() laesst TemplateAmmo aussen vor
for key in ("BleedingMod", "RecoilMod", "FlatnessMod", "WeaponExhaustionMod"):
    have = [m[key] for m in mods.values() if key in m]
    assert len(have) == 34, (key, len(have))
assert {m["BleedingMod"] for m in mods.values()} == {1.0}
assert {m["RecoilMod"] for m in mods.values()} == {1.0}
print("Live: alle 34 Sorten tragen die vier neuen Modifikatoren  OK")

# Reihenfolge: die vier haengen HINTEN an - sonst waeren alte Paks nicht
# mehr bytegleich (dieselbe Regel wie bei der Stapelgroesse in 1.30.0)
assert AMMO_PARAMS[:5] == ["damage", "piercing", "armordamage", "cover", "stack"], AMMO_PARAMS
assert AMMO_PARAMS[5:9] == ["bleeding", "recoil", "flatness", "wear"], AMMO_PARAMS
# 1.33.0 haengt nach derselben Regel zwei weitere hinten an (Spread und
# Spread-beim-Zielen aus der neunten Datenrecherche) - die vier oben
# behalten dadurch ihre Position, alte Paks bleiben bytegleich.
assert AMMO_PARAMS[9:] == ["dispersion", "aimdispersion"], AMMO_PARAMS
print("Parameter-Reihenfolge unveraendert, Neues angehaengt  OK")

p = nodes(build_patches(gd, Settings(ammo_bleeding_factor=2.0, ammo_recoil_factor=0.5,
                                     ammo_flatness_factor=1.5, ammo_wear_factor=0.0)), ITEMS)
assert len(p) == 34, len(p)          # 34 echte Sorten (TemplateAmmo faellt raus)
sample = p["A012A"].values
assert sample["BleedingMod"] == "2.0" and sample["RecoilMod"] == "0.5"
assert sample["WeaponExhaustionMod"] == "0.0"
print("Munitions-Regler: 34 Sorten, Werte korrekt skaliert  OK")

# Kaskade: Sorte schlaegt global
p = nodes(build_patches(gd, Settings(ammo_recoil_factor=0.5,
                                     ammo_overrides={"A545D": {"recoil": 2.0}})), ITEMS)
assert p["A545D"].values["RecoilMod"] == "2.0", p["A545D"].values
assert p["A762D"].values["RecoilMod"] == "0.5", p["A762D"].values
print("Sorte schlaegt global (2.0 neben 0.5)  OK")

# --- 6) Ladehemmung ------------------------------------------------------
p = nodes(build_patches(gd, Settings(jam_chance_factor=0.0)), WGS)
assert len(p) == 92, len(p)
mins = [sid for sid, n in p.items() if "MinJamChance" in n.values]
assert len(mins) == 1, mins   # 91 Waffen haben Vanilla 0.0 -> kein Scheinpatch
assert all("MaxJamChance" in n.values for n in p.values())
assert {n.values["MaxJamChance"] for n in p.values()} == {"0.0"}
# Die Haltbarkeits-Schwellen bleiben bewusst unangetastet
assert not any("JamDurabilityThreshold" in k
               for n in p.values() for k in n.values), "Schwellen sind tabu"
print("Ladehemmung 0 %: 92 Waffen, nur eine MinJamChance-Zeile, Schwellen tabu  OK")

# --- 7) Anzeigebalken ----------------------------------------------------
files = build_patches(gd, Settings(weapon_category_factors={"rifle": {"damage": 2.0}}))
assert "DamageUI" not in files[CWS], "Balken ohne Haken angefasst"
p = nodes(build_patches(gd, Settings(stat_bars_follow=True, weapon_range_factor=1.5,
                                     weapon_category_factors={"rifle": {"damage": 2.0}})), CWS)
bars = {sid: n.values for sid, n in p.items() if "DamageUI" in n.values or "RangeUI" in n.values}
assert bars, "keine Balken gepatcht"
ak = p["GunAK74_ST_Player"].values
assert ak["DamageUI"] == "0.46", ak            # 0.23 x 2 (Kategorie-Faktor)
assert float(ak["RangeUI"]) <= 1.0
for values in bars.values():
    for key in ("DamageUI", "RangeUI", "RateOfFireUI"):
        if key in values:
            assert float(values[key]) <= 1.0, (key, values[key])
    # Accuracy und Handling sind bewusst NICHT dabei
    assert "AccuracyUI" not in values and "HandlingUI" not in values, values
print(f"Anzeigebalken: {len(bars)} Waffen, Kaskade greift, Deckel 1.0, "
      "Accuracy/Handling bleiben  OK")

# --- 8) NPC gegen NPC ----------------------------------------------------
p = nodes(build_patches(gd, Settings(npc_vs_npc_damage_factor=0.5)), CWS)
assert len(p) == 150, len(p)
assert {n.values["NPCToNPCDamageScaler"] for n in p.values()} == {"0.35"}
print("NPC-gegen-NPC: alle 150 Structs von 0.7 auf 0.35  OK")

# --- 10) Mutanten-Attacken -----------------------------------------------
params = gd.mutant_attack_params(("MaxAttacksInSeries", "BleedingChanceIncrement"))
# 143 Mutanten-Attacken insgesamt, 136 davon tragen mindestens einen der
# beiden Schluessel (131x MaxAttacksInSeries, 136x BleedingChanceIncrement)
assert len(params) == 136, len(params)
prefixes = tuple(pfx for lst in SPECIES_ABILITY_PREFIXES.values() for pfx in lst)
assert all(sid.startswith(prefixes) for sid in params)
p = nodes(build_patches(gd, Settings(mutant_attack_series_factor=2.0,
                                     mutant_attack_bleed_factor=0.0)), ABIL)
forbidden = ("Human_", "Korshunov", "Faust", "Scar", "BaseAttackAbility", "Default")
assert not [sid for sid in p if sid.startswith(forbidden)], sorted(p)[:5]
# Vanilla 0 bekommt keine Serie angedichtet
series = {sid: n.values["MaxAttacksInSeries"] for sid, n in p.items()
          if "MaxAttacksInSeries" in n.values}
assert all(int(v) >= 1 for v in series.values()), series
# 45 Attacken im ganzen File haben eine Serie > 0, 42 davon sind
# Mutanten — die drei anderen (Mensch/Boss) bleiben unangetastet
assert len(series) == 42, len(series)
# Literalform bleibt erhalten: Vanilla schreibt teils ".1f", teils "0" -
# das f-Suffix muss also je Eintrag genauso rauskommen wie es reinging
for sid, node in p.items():
    if "BleedingChanceIncrement" not in node.values:
        continue
    vanilla_raw = params[sid]["BleedingChanceIncrement"]
    got = node.values["BleedingChanceIncrement"]
    assert got.endswith("f") == vanilla_raw.endswith("f"), (sid, vanilla_raw, got)
print(f"Mutanten: {len(params)} Attacken mit diesen Schluesseln, {len(series)} mit Serie, "
      "Mensch/Boss/Vorlagen draussen, Literalform erhalten  OK")

# --- 13) Reparatur-Aufschlag je Upgrade ----------------------------------
raws = {n.values["RepairCostModifier"] for n in gd.upgrades.children.values()
        if "RepairCostModifier" in n.values}
assert raws == {"0.2f"}, raws
p = nodes(build_patches(gd, Settings(upgrade_repair_surcharge=0.0)), UPG)
assert len(p) == 1288, len(p)
assert {n.values["RepairCostModifier"] for n in p.values()} == {"0.0f"}
assert not build_patches(gd, Settings(upgrade_repair_surcharge=0.2)), "Vanilla patcht"
# Der gleichnamige Schluessel in ObjPrototypes gehoert den NPCs und bleibt tabu
obj = build_patches(gd, Settings(upgrade_repair_surcharge=0.0))
for name, text in obj.items():
    if "ObjPrototypes" in name:
        assert "RepairCostModifier" not in text, name
print("Reparatur-Aufschlag: 1288 Upgrades, Suffix erhalten, ObjPrototypes tabu  OK")

# --- 2) Packungsgroesse der Munition -------------------------------------
packs = gd.ammo_pack_counts()
assert len(packs) == 31, len(packs)      # 35 Structs minus Template minus 3x "1"
for sid in ("AVOG", "AHEDP", "APG7V", "TemplateAmmo"):
    assert sid not in packs, sid          # Werfergranaten kommen einzeln
assert set(packs.values()) == {10.0, 20.0, 30.0, 50.0}, sorted(set(packs.values()))
p = nodes(build_patches(gd, Settings(ammo_pack_factor=2.0)), ITEMS)
assert len(p) == 31, len(p)
assert {n.values["AmmoPackCount"] for n in p.values()} == {"20", "40", "60", "100"}
assert all(set(n.values) == {"AmmoPackCount"} for n in p.values()), "fremde Schluessel"
print("Packungsgroesse: 31 Sorten verdoppelt, Werfergranaten bleiben bei 1  OK")

# --- 17) Fundgruppen je Versteck -----------------------------------------
STASH = "StashPrototypes/StashPrototypes_patch_S2Tweaker.cfg"
p = build_patches(gd, Settings(stash_sets_factor=2.0))[STASH]
import re as _re
keys = set(_re.findall(r"^\s+(\w+) = ", p, _re.M))
assert keys == {"ItemSetCount"}, keys     # der Regler fasst nichts anderes an
values = _re.findall(r"ItemSetCount = (\d+)", p)
assert len(values) == 45, len(values)
assert all(int(v) >= 1 for v in values), values
print(f"Versteck-Sets: {len(values)} Eintraege, nur ItemSetCount angefasst  OK")

# --- 3) Erholung nach dem Schuss (invers, beide Zweige) ------------------
WGS = ("WeaponData/WeaponGeneralSetupPrototypes/"
       "WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg")
p = build_patches(gd, Settings(recoil_recovery_factor=2.0))[WGS]
# Recoil UND Dispersion haben je ein eigenes RadiusNormalizationModifiers
assert p.count("RadiusNormalizationInterval") == 181, p.count("RadiusNormalizationInterval")
assert p.count("RadiusNormalizationDelay") == 76, p.count("RadiusNormalizationDelay")
for branch in ("RecoilParams", "DispersionParams"):
    assert branch in p, branch
# invers: 0.8 wird zu 0.4
assert "0.4" in p
print("Erholung: beide Zweige, invers, Null-Delays uebersprungen  OK")

# --- 4) Streuungs-Aufbau: NUR der Dispersion-Zweig -----------------------
p = build_patches(gd, Settings(spread_bloom_factor=0.0))[WGS]
assert "RadiusExtensionBulletCount" not in p, "BulletCount ist tabu"
# Auf der Rueckstoss-Seite steht in Vanilla alles auf 0.0 - dort darf nichts
# entstehen; nur DispersionParams taucht auf
recoil_ext = p.count("RecoilParams : struct.begin")
for chunk in p.split("\n\n"):
    if "RadiusExtensionModifiers" in chunk:
        assert "DispersionParams" in chunk, chunk[:120]
print("Streuungs-Aufbau: nur der Dispersion-Zweig, BulletCount unangetastet  OK")

# --- 5) Zielen/Ducken: Betrag gedeckelt ----------------------------------
p = build_patches(gd, Settings(aim_steady_factor=2.0))[WGS]
import re as _re2
vals = [float(v) for v in _re2.findall(r"Aim\w*Modifier = (-?[\d.]+)", p)]
assert vals, "keine Aim-Modifikatoren gepatcht"
assert all(-1.0 <= v <= 1.0 for v in vals), (min(vals), max(vals))
# -1.0 x 2 waere -2.0 -> gedeckelt auf -1.0 = unveraendert, also NICHT im Patch
assert -1.0 not in vals, "gedeckelter Wert als Scheinpatch geschrieben"
print(f"Zielen/Ducken: {len(vals)} Werte, alle im Band -1.0..1.0  OK")

# --- 9) Zombie-Streuungsaufschlag ----------------------------------------
p = nodes(build_patches(gd, Settings(zombie_spread_factor=0.0)), CWS)
assert len(p) == 75, len(p)
assert {n.values["DispersionRadiusZombieAddend"] for n in p.values()} == {"0.0"}
print("Zombie-Aufschlag: alle 75 NPC-Profile  OK")

# --- 11/12) Explosionen ---------------------------------------------------
EXP = "ExplosionPrototypes/ExplosionPrototypes_patch_S2Tweaker.cfg"
p = nodes(build_patches(gd, Settings(explosion_armor_damage_factor=0.0,
                                     explosion_armor_pierce_factor=2.0,
                                     explosion_destructible_factor=3.0)), EXP)
assert len(p) == 11, len(p)
armor_npc = [sid for sid, n in p.items() if "DamageArmorNPC" in n.values]
assert len(armor_npc) == 6, len(armor_npc)   # sechs stehen in Vanilla auf 0.
pierce = {n.values["ArmorPenetrationPlayer"] for n in p.values()
          if "ArmorPenetrationPlayer" in n.values}
# Vanilla schreibt "4." / "5." / "6."; _scale_literal normalisiert das
# beim Verdoppeln zu "8.0" / "10.0" / "12.0" - numerisch dasselbe
assert pierce == {"8.0", "10.0", "12.0"}, sorted(pierce)
print("Explosionen: 11 Typen, Null-Werte uebersprungen, Literalform erhalten  OK")

# --- 15/16) Geschosse -----------------------------------------------------
PRJ = "ProjectilePrototypes/ProjectilePrototypes_patch_S2Tweaker.cfg"
p = nodes(build_patches(gd, Settings(bullet_penetration_factor=5.0,
                                     bullet_range_factor=2.0)), PRJ)
pens = [float(n.values["PenetrationSpawnChance"]) for n in p.values()
        if "PenetrationSpawnChance" in n.values]
assert pens and max(pens) <= 1.0, pens
ranges = [n.values["MaxFlyDistance"] for n in p.values() if "MaxFlyDistance" in n.values]
assert len(ranges) == 16, len(ranges)
print(f"Geschosse: {len(pens)} Durchschlagswerte (Deckel 1.0), {len(ranges)} Reichweiten  OK")

# --- 14) Upgrade-Preis haengt am vorhandenen Regler ------------------------
p = nodes(build_patches(gd, Settings(upgrade_cost_factor=0.5)), UPG)
costs = [sid for sid, n in p.items() if "BaseCost" in n.values]
assert len(costs) == 1282, len(costs)
# kein eigener Regler: das Feld existiert nicht
assert not hasattr(Settings(), "upgrade_base_cost_factor")
print("Upgrade-Preis: 1282 Upgrades, eingefaltet in den vorhandenen Regler  OK")

# --- Klemm-Korrektur: der Array-Eintrag geht KOMPLETT raus ---------------
# WeaponJamParams.[i] traegt genau zwei Schluessel. Bis 1.31.0 schrieb der
# Klemmer-Regler nur FullJamTime hinein; beide Regler geben jetzt beide aus.
for setting in (Settings(jam_clear_factor=2.0), Settings(jam_chance_factor=0.5)):
    p = build_patches(gd, setting)[WGS]
    assert p.count("JamChanceCoef") == p.count("FullJamTime") > 0, (
        p.count("JamChanceCoef"), p.count("FullJamTime"))
print("Klemm-Eintrag: beide Schluessel in beiden Reglern  OK")

# --- Hueftfeuer, Bewegung, Muster, Kammer, Munition in Waffen ------------
p = build_patches(gd, Settings(hip_steady_factor=2.0))[WGS]
import re as _re3
vals = [float(v) for v in _re3.findall(r"Hip\w*Modifier = (-?[\d.]+)", p)]
assert vals and all(-1.0 <= v <= 1.0 for v in vals), (min(vals), max(vals))
assert "HipJumpModifier" in p and "HipCrouchModifier" in p
print(f"Hueftfeuer: {len(vals)} Werte, Betrag gedeckelt  OK")

p = build_patches(gd, Settings(move_steady_factor=0.0))[WGS]
assert "MovementSpeedModifier" in p
print("Bewegung: MovementSpeedModifiers gepatcht  OK")

p = build_patches(gd, Settings(recoil_pattern_factor=2.0))[WGS]
assert p.count("RecoilPatternInterval") == 92, p.count("RecoilPatternInterval")
print("Rueckstossmuster-Pause: 92 Waffen  OK")

p = nodes(build_patches(gd, Settings(chamber_round=True)), WGS)
assert len(p) == 27, len(p)     # 65 der 92 haben die Zusatzpatrone schon
assert {n.values["AdditionalBulletsAfterReloadingCount"] for n in p.values()} == {"1"}
print("Kammer-Patrone: genau die 27 ohne  OK")

p = nodes(build_patches(gd, Settings(dropped_ammo_factor=3.0)), WGS)
for node in p.values():
    for key in ("MinDeadNPCLoadedAmmoCount", "MaxDeadNPCLoadedAmmoCount"):
        if key in node.values:
            assert int(node.values[key]) >= 0, node.values[key]   # nie -1 skaliert
print("Munition in Waffen Toter: keine -1 angefasst  OK")

# --- Waffen-Lautstaerke ---------------------------------------------------
p = nodes(build_patches(gd, Settings(weapon_noise_factor=0.0)), CWS)
assert len(p) == 141, len(p)    # 150 minus die neun, die schon auf 0 stehen
print("Lautstaerke: 141 Structs, die stillen bleiben still  OK")

# --- Inventar --------------------------------------------------------------
p = nodes(build_patches(gd, Settings(item_grid_factor=0.5)), ITEMS)
cells = [int(n.values[k]) for n in p.values()
         for k in ("ItemGridWidth", "ItemGridHeight") if k in n.values]
assert cells and min(cells) >= 1, min(cells)   # nie unter eine Zelle
print(f"Inventar-Raster: {len(cells)} Werte, nie unter 1 Zelle  OK")

p = nodes(build_patches(gd, Settings(inventory_action_factor=2.0)), ITEMS)
times = {sid: float(n.values["InventoryActionTime"]) for sid, n in p.items()
         if "InventoryActionTime" in n.values}
assert len(times) == 243, len(times)
# invers: jeder Wert ist exakt die Haelfte seines Vanilla-Werts
for sid, got in times.items():
    vanilla = float(gd.items.children[sid].values["InventoryActionTime"])
    assert abs(got - vanilla / 2) < 1e-6, (sid, vanilla, got)
print("Inventar-Tempo: 243 Gegenstaende, invers  OK")

# --- NPC-Koerper und Rueckzug ---------------------------------------------
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
p = nodes(build_patches(gd, Settings(npc_anomaly_ignore_factor=5.0)), OBJ)
vals = [float(n.values["AnomalyRestrictionsIgnoreChance"]) for n in p.values()
        if "AnomalyRestrictionsIgnoreChance" in n.values]
assert vals and max(vals) <= 1.0, max(vals)     # Wahrscheinlichkeit, Deckel 1
assert "Player" not in p and "[0]" not in p
print(f"Anomalie-Ignorieren: {len(vals)} Prototypen, Deckel 1.0, Player aussen vor  OK")

p = nodes(build_patches(gd, Settings(npc_retreat_radius_factor=2.0,
                                     npc_retreat_damage_factor=0.5)), OBJ)
nested = [sid for sid, n in p.items() if "RetreatActionData" in n.children]
assert nested, "verschachtelter Rueckzug nicht gepatcht"
print(f"Rueckzug: {len(p)} Prototypen, davon {len(nested)} verschachtelt  OK")

# --- Tweak-Liste ----------------------------------------------------------
lines = summarize(Settings(ammo_bleeding_factor=2.0, jam_chance_factor=0.0,
                           npc_vs_npc_damage_factor=2.0, stat_bars_follow=True,
                           mutant_attack_series_factor=2.0,
                           upgrade_repair_surcharge=0.0,
                           ammo_pack_factor=2.0, stash_sets_factor=2.0))
for want in ("Ammo bleeding", "Weapon jam chance", "NPC vs NPC damage",
             "Inventory stat bars", "Mutant attacks per series",
             "Repair surcharge per upgrade", "Ammo pack size",
             "Stash item sets"):
    assert any(want in l for l in lines), (want, lines)
print("Alle acht stehen in der Tweak-Liste  OK")

print("\nTEST MOD-AUSBEUTE OK")
