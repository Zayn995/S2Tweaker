"""Regression checks for additional modifier families and corrected coverage.

Read expected values from installed vanilla data; recorded figures are
historical sanity checks, not generation baselines."""
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
    assert key in patches, f"Patch file missing: {key}\nda: {sorted(patches)[:12]}"
    return cfgparse.parse(patches[key]).children


def build(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


# --- 0) Neutral produces nothing ---
print("\n0) Neutral")
check(build() == {}, "Vanilla setting produces no file")


# --- 1) Equipment wear in anomalies ---
print("\n1) Anomaly wear on gear (Corrosion family)")
corrosion = {sid for sid, n in gd.effects.children.items()
             if (n.values.get("Type") or "").replace("EEffectType::", "").strip()
             in ("Corrosion", "VelocityCorrosion")}
check(len(corrosion) >= 25, f"Vanilla contains {len(corrosion)} corrosion effects")
check("ButtStroke_Corrosion" in corrosion, "Weapon bash belongs to the same family")

eff = parse(build(anomaly_wear_factor=0.5), EFFECTS)
scaled = {sid for sid in eff if sid in corrosion}
check("ButtStroke_Corrosion" not in eff,
      "Weapon bash remains controlled by its own slider")
check(len(scaled) >= 24, f"{len(scaled)} corrosion effects are halved")
carousel = eff.get("CarouselCorrosion_Body")
check(carousel is not None and carousel.values.get("ValueMin") == "5.0",
      f"CarouselCorrosion_Body 10 -> {carousel.values.get('ValueMin') if carousel else '-'}")
check("CarouselCorrosion" not in eff,
      "Composite parent (0.f) remains unchanged")

both = parse(build(anomaly_wear_factor=0.5, butt_wear_factor=0.5), EFFECTS)
check("ButtStroke_Corrosion" in both and both["ButtStroke_Corrosion"].values.get("ValueMin"),
      "Both effects share the file when combined with the weapon-bash slider")


# --- 2) Maximum durability ---
print("\n2) Weapon & armor max condition (BaseDurability)")
gear = gd.gear_durability()
check(len(gear) > 100, f"{len(gear)} weapons/armors carry a BaseDurability value")
check(all(v > 1.0 for _c, v in gear.values()),
      "The base struct's 1.0 placeholder is filtered out")
items = parse(build(gear_durability_factor=2.0), ITEMS)
sample = next(sid for sid, (_c, v) in sorted(gear.items()) if v > 1000)
vanilla = gear[sample][1]
got = float(items[sample].values["BaseDurability"])
check(abs(got - vanilla * 2) < 0.01, f"{sample}: {vanilla} -> {got}")
check(len([s for s in items if "BaseDurability" in items[s].values]) == len(gear),
      "Each equipment item receives exactly one line")


# --- 3) Two additional ammunition factors ---
print("\n3) Ammo spread / spread while aiming")
kinds = gd.ammo_mods()
with_disp = [sid for sid, m in kinds.items() if "DispersionMod" in m]
# Exclude TemplateAmmo when enumerating real ammunition types.
check(len(with_disp) == 34, f"{len(with_disp)} actual ammo types have DispersionMod")
ammo = parse(build(ammo_dispersion_factor=2.0), ITEMS)
sid = sorted(with_disp)[0]
check(float(ammo[sid].values["DispersionMod"]) == kinds[sid]["DispersionMod"] * 2,
      f"{sid}: DispersionMod doubled")
aim = parse(build(ammo_aim_dispersion_factor=0.5), ITEMS)
check("AimDispersionMod" in aim[sorted(with_disp)[0]].values,
      "AimDispersionMod is written separately")
# Per-type overrides replace global factors.
over = parse(build(ammo_dispersion_factor=2.0,
                   ammo_overrides={sid: {"dispersion": 4.0}}), ITEMS)
check(float(over[sid].values["DispersionMod"]) == kinds[sid]["DispersionMod"] * 4,
      "Individual ammunition override replaces the global factor")


# Extreme-distance damage.
print("\n4) Damage at extreme range")
far = parse(build(far_damage_factor=2.0), CWS)
rows = [n for n in far.values() if "MinBulletDistanceDamageModifier" in n.values]
# Apply this player control only to player CWS profiles.
check(50 <= len(rows) <= 100, f"{len(rows)} player CWS structs receive a higher minimum")
values = [float(n.values["MinBulletDistanceDamageModifier"]) for n in rows]
check(max(values) <= 1.0, f"1.0 cap holds (maximum value {max(values)})")
check(not [n for n in far.values()
           if "MinBulletDistanceArmorPiercingModifier" in n.values],
      "Increasing the slider leaves penetration unchanged (already 1.0)")
down = parse(build(far_damage_factor=0.5), CWS)
ap = [n for n in down.values() if "MinBulletDistanceArmorPiercingModifier" in n.values]
check(len(ap) >= 50, f"Decreasing it does: {len(ap)} structs lose penetration over distance")
check(build(far_damage_factor=1.0) == {}, "At vanilla, the slider produces nothing")


# --- 5) The two remaining effect caps ---
print("\n5) Stamina & bleeding caps")
caps = parse(build(effect_cap_other_factor=2.0), EFFMAX)
entries = caps["DefaultEffectMaxParamsSID"].children["MaxEffectValues"].children
sids = {e.values.get("EffectSID") for e in entries.values()}
check(sids == {"EEffectType::RegenStamina", "EEffectType::DegenBleeding"},
      f"Exactly the two previously uncapped entries: {sorted(sids)}")
for e in entries.values():
    if e.values["EffectSID"].endswith("RegenStamina"):
        check(e.values["MaxValue"] == "60.0f", f"RegenStamina 30 -> {e.values['MaxValue']}")


# Initial camp fill and rare archetypes.
print("\n6) Lair starting occupancy / rare archetypes")
blocks = gd.lair_blocks()
inis = [b for b in blocks if b["initial"] and not b["guard"]]
check(len(inis) > 500, f"{len(inis)} non-guard blocks carry an initial fill value")
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
                check(float(v) <= 1.0, "Initial fill is capped at 1.0") if hits == 1 else None
check(hits > 500, f"{hits} blocks receive the new initial fill")
check(not any(n.startswith("Guard") for n in lair),
      "Guard lairs remain unchanged")

rare = parse(build(lair_rare_archetype_factor=2.0), LAIRS)
weights = []
for node in rare.values():
    for fac in node.children["Preset"].children["PossibleInhabitantFactions"].children.values():
        for rank in fac.children["SpawnSettingsPerPlayerRanks"].children.values():
            arch = rank.children.get("SpawnSettingsPerArchetypes")
            for a in (arch.children.values() if arch else ()):
                weights.append(float(a.values["SpawnWeight"]))
check(weights, f"{len(weights)} archetype weights are increased")
check(all(0 < w <= 1.0 for w in weights),
      f"Only actual rarity weights, capped at 1.0 (min {min(weights)}, max {max(weights)})")


# Director expansion and fallback behavior.
print("\n7) Lair expansion / fallback spawn count")
d = parse(build(lair_expansion_player_factor=2.0), DIRECTOR)
preset = next(iter(d.values()))
check(preset.values.get("DefaultALifeLairExpansionToPlayerTimeMin") == "60",
      f"120 min -> {preset.values.get('DefaultALifeLairExpansionToPlayerTimeMin')} (invers)")
d2 = parse(build(fallback_spawn_count=10), DIRECTOR)
check(next(iter(d2.values())).values.get("FallbackMaxSpawnCount") == "10",
      "FallbackMaxSpawnCount is set to an absolute value")
check(build(fallback_spawn_count=3) == {}, "Vanilla value 3 produces nothing")


# --- 8) Upgrade-family regression ---
print("\n8) Regression: Accuracy and MovementSpeed now share one slider")
types = {t for fam in UPGRADE_FAMILIES.values() for t in fam}
check("Accuracy" in types, "Accuracy effect type belongs to a family")
check("MovementSpeed" in types, "MovementSpeed effect type also covered")
acc = parse(build(upg_accuracy_factor=2.0), EFFECTS)
check("AccuracyEffect" in acc,
      f"AccuracyUpgrade is now scaled: {acc.get('AccuracyEffect').values if 'AccuracyEffect' in acc else '-'}")
check(acc["AccuracyEffect"].values["ValueMin"] == "100.0%",
      f"50 % x2 = {acc['AccuracyEffect'].values['ValueMin']}")
mov = parse(build(upg_armor_misc_factor=2.0), EFFECTS)
check("MovementSpeedEffect" in mov, "MovementSpeedUpgrade also covered")
# Preserve positive aim penalties when scaling negative beneficial modifiers.
check("DispersionAimModifierNeg70Effect" not in acc,
      "Rhino upgrade's +70% entry remains vanilla (sign interpretation unclear)")


# --- 9) Composite-effect regression ---
print("\n9) Regression: composite effects follow their children")
comp = parse(build(upg_accuracy_factor=2.0, upg_handling_factor=2.0), EFFECTS)
accs = comp.get("BattleExoskeleton_Varta_Armor_accuracy")
check(accs is not None,
      "The 'Accuracy 20%' composite is scaled when all children share a factor")
check(accs.values.get("ValueMin") == "40.0%", f"20 % -> {accs.values.get('ValueMin')}")
only_one = parse(build(upg_handling_factor=2.0), EFFECTS)
check("BattleExoskeleton_Varta_Armor_accuracy" not in only_one,
      "With mixed factors (handling only), the display remains vanilla")


# Approximate Accuracy/Handling inventory bars.
print("\n10) Stat bars: accuracy and handling")
bars = parse(build(stat_bars_follow=True, spread_factor=0.5, aim_time_factor=2.0), CWS)
acc_rows = [n for n in bars.values() if "AccuracyUI" in n.values]
hand_rows = [n for n in bars.values() if "HandlingUI" in n.values]
check(acc_rows, f"{len(acc_rows)} structs receive an accuracy bar")
check(hand_rows, f"{len(hand_rows)} structs receive a handling bar")
check(all(float(n.values["AccuracyUI"]) <= 1.0 for n in acc_rows),
      "The bar remains capped at 1.0")
check(not [n for n in parse(build(spread_factor=0.5), CWS).values() if "AccuracyUI" in n.values],
      "Without the checkbox, all bars remain unchanged")


# Include new controls in the summary.
print("\n11) Tweak list")
text = "\n".join(summarize(Settings(
    anomaly_wear_factor=0.5, gear_durability_factor=2.0, far_damage_factor=2.0,
    effect_cap_other_factor=2.0, lair_initial_fill_factor=2.0,
    lair_rare_archetype_factor=2.0, lair_expansion_player_factor=2.0,
    fallback_spawn_count=10, ammo_dispersion_factor=2.0,
    ammo_aim_dispersion_factor=2.0)))
for needle in ("Anomaly wear", "max condition", "extreme range", "caps",
               "starting occupancy", "Rare lair", "expansion", "Fallback",
               "Ammo spread"):
    check(needle in text, f"Tweak list mentions '{needle}'")

print(f"\n=== {ok} checks passed ===")
