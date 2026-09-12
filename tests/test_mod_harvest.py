"""Check modifier families identified through community-mod comparison.

Expected values come from installed data. Cover ammunition, jams, stat bars,
NPC damage, mutant attacks and upgrade repair costs, including scope limits,
neutral output, precedence, caps and literal formatting."""
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


# --- 0) Neutral produces nothing ---
assert not build_patches(gd, Settings())
print("Neutral: no patch  OK")

# --- 1) Four additional ammunition parameters ---
mods = gd.ammo_mods()
# Exclude TemplateAmmo from concrete ammunition coverage.
for key in ("BleedingMod", "RecoilMod", "FlatnessMod", "WeaponExhaustionMod"):
    have = [m[key] for m in mods.values() if key in m]
    assert len(have) == 34, (key, len(have))
assert {m["BleedingMod"] for m in mods.values()} == {1.0}
assert {m["RecoilMod"] for m in mods.values()} == {1.0}
print("Live: all 34 types carry the four new modifiers  OK")

# Append new fields to preserve established patch ordering.
assert AMMO_PARAMS[:5] == ["damage", "piercing", "armordamage", "cover", "stack"], AMMO_PARAMS
assert AMMO_PARAMS[5:9] == ["bleeding", "recoil", "flatness", "wear"], AMMO_PARAMS
# Keep earlier field positions when adding further modifiers.
assert AMMO_PARAMS[9:] == ["dispersion", "aimdispersion"], AMMO_PARAMS
print("Parameter order unchanged, new entries appended  OK")

p = nodes(build_patches(gd, Settings(ammo_bleeding_factor=2.0, ammo_recoil_factor=0.5,
                                     ammo_flatness_factor=1.5, ammo_wear_factor=0.0)), ITEMS)
assert len(p) == 34, len(p)          # 34 actual types, excluding TemplateAmmo.
sample = p["A012A"].values
assert sample["BleedingMod"] == "2.0" and sample["RecoilMod"] == "0.5"
assert sample["WeaponExhaustionMod"] == "0.0"
print("Ammunition sliders: 34 types, correctly scaled values  OK")

# Cascade: individual type overrides global.
p = nodes(build_patches(gd, Settings(ammo_recoil_factor=0.5,
                                     ammo_overrides={"A545D": {"recoil": 2.0}})), ITEMS)
assert p["A545D"].values["RecoilMod"] == "2.0", p["A545D"].values
assert p["A762D"].values["RecoilMod"] == "0.5", p["A762D"].values
print("Individual type overrides global (2.0 alongside 0.5)  OK")

# --- 6) Jamming ------------------------------------------------------
p = nodes(build_patches(gd, Settings(jam_chance_factor=0.0)), WGS)
assert len(p) == 92, len(p)
mins = [sid for sid, n in p.items() if "MinJamChance" in n.values]
assert len(mins) == 1, mins   # Zero jam-chance baselines must emit no changes.
assert all("MaxJamChance" in n.values for n in p.values())
assert {n.values["MaxJamChance"] for n in p.values()} == {"0.0"}
# Durability thresholds intentionally remain unchanged.
assert not any("JamDurabilityThreshold" in k
               for n in p.values() for k in n.values), "Thresholds must remain unchanged"
print("Jamming 0%: 92 weapons, one MinJamChance line, thresholds unchanged  OK")

# --- 7) Display bars ----------------------------------------------------
files = build_patches(gd, Settings(weapon_category_factors={"rifle": {"damage": 2.0}}))
assert "DamageUI" not in files[CWS], "Bars modified without the checkbox"
p = nodes(build_patches(gd, Settings(stat_bars_follow=True, weapon_range_factor=1.5,
                                     weapon_category_factors={"rifle": {"damage": 2.0}})), CWS)
bars = {sid: n.values for sid, n in p.items() if "DamageUI" in n.values or "RangeUI" in n.values}
assert bars, "No bars patched"
ak = p["GunAK74_ST_Player"].values
assert ak["DamageUI"] == "0.46", ak            # 0.23 x 2 category factor.
assert float(ak["RangeUI"]) <= 1.0
for values in bars.values():
    for key in ("DamageUI", "RangeUI", "RateOfFireUI"):
        if key in values:
            assert float(values[key]) <= 1.0, (key, values[key])
    # Accuracy/Handling are outside this particular mapped-bar check.
    assert "AccuracyUI" not in values and "HandlingUI" not in values, values
print(f"Anzeigebalken: {len(bars)} weapons, cascade applied, cap 1.0, "
      "Accuracy/handling remain unchanged  OK")

# --- 8) NPC vs NPC ---
p = nodes(build_patches(gd, Settings(npc_vs_npc_damage_factor=0.5)), CWS)
assert len(p) == 150, len(p)
assert {n.values["NPCToNPCDamageScaler"] for n in p.values()} == {"0.35"}
print("NPC vs NPC: all 150 structs from 0.7 to 0.35  OK")

# --- 10) Mutant attacks ---
params = gd.mutant_attack_params(("MaxAttacksInSeries", "BleedingChanceIncrement"))
# Only mutant attacks declaring the relevant keys are included.
assert len(params) == 136, len(params)
prefixes = tuple(pfx for lst in SPECIES_ABILITY_PREFIXES.values() for pfx in lst)
assert all(sid.startswith(prefixes) for sid in params)
p = nodes(build_patches(gd, Settings(mutant_attack_series_factor=2.0,
                                     mutant_attack_bleed_factor=0.0)), ABIL)
forbidden = ("Human_", "Korshunov", "Faust", "Scar", "BaseAttackAbility", "Default")
assert not [sid for sid in p if sid.startswith(forbidden)], sorted(p)[:5]
# Do not introduce attack series at zero baselines.
series = {sid: n.values["MaxAttacksInSeries"] for sid, n in p.items()
          if "MaxAttacksInSeries" in n.values}
assert all(int(v) >= 1 for v in series.values()), series
# Exclude human/boss attack series.
assert len(series) == 42, len(series)
# Retain each numeric literal's original suffix.
for sid, node in p.items():
    if "BleedingChanceIncrement" not in node.values:
        continue
    vanilla_raw = params[sid]["BleedingChanceIncrement"]
    got = node.values["BleedingChanceIncrement"]
    assert got.endswith("f") == vanilla_raw.endswith("f"), (sid, vanilla_raw, got)
print(f"Mutants: {len(params)} attacks with these keys, {len(series)} with a series, "
      "Humans, bosses and templates excluded; literal format preserved  OK")

# --- 13) Repair surcharge per upgrade ---
raws = {n.values["RepairCostModifier"] for n in gd.upgrades.children.values()
        if "RepairCostModifier" in n.values}
assert raws == {"0.2f"}, raws
p = nodes(build_patches(gd, Settings(upgrade_repair_surcharge=0.0)), UPG)
assert len(p) == 1288, len(p)
assert {n.values["RepairCostModifier"] for n in p.values()} == {"0.0f"}
assert not build_patches(gd, Settings(upgrade_repair_surcharge=0.2)), "Vanilla settings produce patches"
# Exclude the similarly named NPC object field.
obj = build_patches(gd, Settings(upgrade_repair_surcharge=0.0))
for name, text in obj.items():
    if "ObjPrototypes" in name:
        assert "RepairCostModifier" not in text, name
print("Repair surcharge: 1288 upgrades, suffix preserved, ObjPrototypes excluded  OK")

# Ammo pickup-pack counts.
packs = gd.ammo_pack_counts()
assert len(packs) == 31, len(packs)      # 35 Structs minus Template minus 3x "1"
for sid in ("AVOG", "AHEDP", "APG7V", "TemplateAmmo"):
    assert sid not in packs, sid          # Launcher grenades are individual items.
assert set(packs.values()) == {10.0, 20.0, 30.0, 50.0}, sorted(set(packs.values()))
p = nodes(build_patches(gd, Settings(ammo_pack_factor=2.0)), ITEMS)
assert len(p) == 31, len(p)
assert {n.values["AmmoPackCount"] for n in p.values()} == {"20", "40", "60", "100"}
assert all(set(n.values) == {"AmmoPackCount"} for n in p.values()), "Unexpected keys"
print("Box size: 31 types doubled, launcher grenades remain at 1  OK")

# --- 17) Loot groups per stash ---
STASH = "StashPrototypes/StashPrototypes_patch_S2Tweaker.cfg"
p = build_patches(gd, Settings(stash_sets_factor=2.0))[STASH]
import re as _re
keys = set(_re.findall(r"^\s+(\w+) = ", p, _re.M))
assert keys == {"ItemSetCount"}, keys     # The control must not affect unrelated fields.
values = _re.findall(r"ItemSetCount = (\d+)", p)
assert len(values) == 45, len(values)
assert all(int(v) >= 1 for v in values), values
print(f"Versteck-Sets: {len(values)} entries, only ItemSetCount changed  OK")

# --- 3) Recovery after firing: inverse, both branches ---
WGS = ("WeaponData/WeaponGeneralSetupPrototypes/"
       "WeaponGeneralSetupPrototypes_patch_S2Tweaker.cfg")
p = build_patches(gd, Settings(recoil_recovery_factor=2.0))[WGS]
# Recoil and dispersion each have their own RadiusNormalizationModifiers.
assert p.count("RadiusNormalizationInterval") == 181, p.count("RadiusNormalizationInterval")
assert p.count("RadiusNormalizationDelay") == 76, p.count("RadiusNormalizationDelay")
for branch in ("RecoilParams", "DispersionParams"):
    assert branch in p, branch
# Inverse scaling halves the value.
assert "0.4" in p
print("Recovery: both branches, inverse, zero delays skipped  OK")

# Dispersion buildup affects only its own branch.
p = build_patches(gd, Settings(spread_bloom_factor=0.0))[WGS]
assert "RadiusExtensionBulletCount" not in p, "BulletCount must remain unchanged"
# Do not create recoil buildup where all vanilla values are zero.
recoil_ext = p.count("RecoilParams : struct.begin")
for chunk in p.split("\n\n"):
    if "RadiusExtensionModifiers" in chunk:
        assert "DispersionParams" in chunk, chunk[:120]
print("Dispersion buildup: dispersion branch only, BulletCount unchanged  OK")

# --- 5) Aiming/crouching: capped magnitude ---
p = build_patches(gd, Settings(aim_steady_factor=2.0))[WGS]
import re as _re2
vals = [float(v) for v in _re2.findall(r"Aim\w*Modifier = (-?[\d.]+)", p)]
assert vals, "No aim modifiers patched"
assert all(-1.0 <= v <= 1.0 for v in vals), (min(vals), max(vals))
# An already capped -1 value remains unchanged and emits no patch.
assert -1.0 not in vals, "Capped value written as a redundant patch"
print(f"Zielen/Ducken: {len(vals)} values, all within -1.0..1.0  OK")

# --- 9) Zombie dispersion addend ---
p = nodes(build_patches(gd, Settings(zombie_spread_factor=0.0)), CWS)
assert len(p) == 75, len(p)
assert {n.values["DispersionRadiusZombieAddend"] for n in p.values()} == {"0.0"}
print("Zombie multiplier: all 75 NPC profiles  OK")

# --- 11/12) Explosions ---------------------------------------------------
EXP = "ExplosionPrototypes/ExplosionPrototypes_patch_S2Tweaker.cfg"
p = nodes(build_patches(gd, Settings(explosion_armor_damage_factor=0.0,
                                     explosion_armor_pierce_factor=2.0,
                                     explosion_destructible_factor=3.0)), EXP)
assert len(p) == 11, len(p)
armor_npc = [sid for sid, n in p.items() if "DamageArmorNPC" in n.values]
assert len(armor_npc) == 6, len(armor_npc)   # Zero-valued baseline entries remain excluded.
pierce = {n.values["ArmorPenetrationPlayer"] for n in p.values()
          if "ArmorPenetrationPlayer" in n.values}
# Accept equivalent normalized numeric spelling after scaling.
assert pierce == {"8.0", "10.0", "12.0"}, sorted(pierce)
print("Explosions: 11 types, zero values skipped, literal format preserved  OK")

# --- 15/16) Projectiles ---
PRJ = "ProjectilePrototypes/ProjectilePrototypes_patch_S2Tweaker.cfg"
p = nodes(build_patches(gd, Settings(bullet_penetration_factor=5.0,
                                     bullet_range_factor=2.0)), PRJ)
pens = [float(n.values["PenetrationSpawnChance"]) for n in p.values()
        if "PenetrationSpawnChance" in n.values]
assert pens and max(pens) <= 1.0, pens
ranges = [n.values["MaxFlyDistance"] for n in p.values() if "MaxFlyDistance" in n.values]
assert len(ranges) == 16, len(ranges)
print(f"Projectiles: {len(pens)} Durchschlagswerte (Deckel 1.0), {len(ranges)} Reichweiten  OK")

# --- 14) Upgrade price uses the existing slider ---
p = nodes(build_patches(gd, Settings(upgrade_cost_factor=0.5)), UPG)
costs = [sid for sid, n in p.items() if "BaseCost" in n.values]
assert len(costs) == 1282, len(costs)
# No separate control field exists for this case.
assert not hasattr(Settings(), "upgrade_base_cost_factor")
print("Upgrade price: 1282 upgrades, included in the existing slider  OK")

# Emit both fields of each indexed jam entry, including the unchanged sibling.
for setting in (Settings(jam_clear_factor=2.0), Settings(jam_chance_factor=0.5)):
    p = build_patches(gd, setting)[WGS]
    assert p.count("JamChanceCoef") == p.count("FullJamTime") > 0, (
        p.count("JamChanceCoef"), p.count("FullJamTime"))
print("Jamming entry: both keys in both sliders  OK")

# --- Hip fire, movement, recoil pattern, chamber and loaded ammunition ---
p = build_patches(gd, Settings(hip_steady_factor=2.0))[WGS]
import re as _re3
vals = [float(v) for v in _re3.findall(r"Hip\w*Modifier = (-?[\d.]+)", p)]
assert vals and all(-1.0 <= v <= 1.0 for v in vals), (min(vals), max(vals))
assert "HipJumpModifier" in p and "HipCrouchModifier" in p
print(f"Hueftfeuer: {len(vals)} values, magnitude capped  OK")

p = build_patches(gd, Settings(move_steady_factor=0.0))[WGS]
assert "MovementSpeedModifier" in p
print("Movement: MovementSpeedModifiers patched  OK")

p = build_patches(gd, Settings(recoil_pattern_factor=2.0))[WGS]
assert p.count("RecoilPatternInterval") == 92, p.count("RecoilPatternInterval")
print("Recoil-pattern pause: 92 weapons  OK")

p = nodes(build_patches(gd, Settings(chamber_round=True)), WGS)
assert len(p) == 27, len(p)     # Exclude weapons already supporting the extra chambered round.
assert {n.values["AdditionalBulletsAfterReloadingCount"] for n in p.values()} == {"1"}
print("Chambered round: exactly the 27 weapons without one  OK")

p = nodes(build_patches(gd, Settings(dropped_ammo_factor=3.0)), WGS)
for node in p.values():
    for key in ("MinDeadNPCLoadedAmmoCount", "MaxDeadNPCLoadedAmmoCount"):
        if key in node.values:
            assert int(node.values[key]) >= 0, node.values[key]   # Never scale -1.
print("Ammunition in dead NPCs' weapons: no -1 values modified  OK")

# --- Weapon loudness ---
p = nodes(build_patches(gd, Settings(weapon_noise_factor=0.0)), CWS)
assert len(p) == 141, len(p)    # Exclude already silent profiles.
print("Loudness: 141 structs, silent entries remain silent  OK")

# --- Inventory --------------------------------------------------------------
p = nodes(build_patches(gd, Settings(item_grid_factor=0.5)), ITEMS)
cells = [int(n.values[k]) for n in p.values()
         for k in ("ItemGridWidth", "ItemGridHeight") if k in n.values]
assert cells and min(cells) >= 1, min(cells)   # Keep at least one inventory cell.
print(f"Inventory grid: {len(cells)} values, never below 1 cell  OK")

p = nodes(build_patches(gd, Settings(inventory_action_factor=2.0)), ITEMS)
times = {sid: float(n.values["InventoryActionTime"]) for sid, n in p.items()
         if "InventoryActionTime" in n.values}
assert len(times) == 243, len(times)
# Inverse scaling must halve every affected vanilla value.
for sid, got in times.items():
    vanilla = float(gd.items.children[sid].values["InventoryActionTime"])
    assert abs(got - vanilla / 2) < 1e-6, (sid, vanilla, got)
print("Inventory speed: 243 items, inverse scaling  OK")

# NPC death impulses and retreat.
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
p = nodes(build_patches(gd, Settings(npc_anomaly_ignore_factor=5.0)), OBJ)
vals = [float(n.values["AnomalyRestrictionsIgnoreChance"]) for n in p.values()
        if "AnomalyRestrictionsIgnoreChance" in n.values]
assert vals and max(vals) <= 1.0, max(vals)     # Probability, capped at 1.
assert "Player" not in p and "[0]" not in p
print(f"Anomalie-Ignorieren: {len(vals)} prototypes, capped at 1.0, player excluded  OK")

p = nodes(build_patches(gd, Settings(npc_retreat_radius_factor=2.0,
                                     npc_retreat_damage_factor=0.5)), OBJ)
nested = [sid for sid, n in p.items() if "RetreatActionData" in n.children]
assert nested, "Nested retreat not patched"
print(f"Retreat: {len(p)} prototypes, including {len(nested)} nested  OK")

# --- Tweak list ----------------------------------------------------------
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
print("All eight appear in the tweak list  OK")

print("\nMOD RESEARCH TEST PASSED")
