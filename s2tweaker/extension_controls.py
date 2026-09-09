"""Declarative controls for the optional loot and world extensions.

All widgets use the normal slider/check registry, so presets, reset, search,
changed-only filtering and conflict avoidance share the existing mechanisms.
No Tk import: collection and footprint probes can be checked without a window.
"""
import re
from .world_extensions import SURFACES, WEATHERS

SPECIES = ("Tushkan", "Flesh", "Boar", "Blinddog", "Snork", "Cat", "Bloodsucker",
           "Pseudodog", "Poltergeist", "Burer", "Controller", "Chimera", "Deer", "Pseudogiant")

# field: (section, label, lower, upper, step, UI default, divisor, tooltip)
SLIDERS = {
    "stash_extra_chance_pct": ("Extra stash finds", "Extra find chance per enabled category", 0, 100, 1, 10, 1,
        "Rolls each enabled category separately in ordinary world stashes. Existing contents remain. Already generated containers may not refresh. Not play-tested yet."),
    "npc_armor_drop_chance_pct": ("NPC equipment & armor loot", "NPC armor loot chance", 0, 100, 1, 0, 1,
        "Adds an ordinary body armor roll from the NPC's faction/rank pool. It does not copy the exact armor being worn. 0 = disabled. Not play-tested yet."),
    "npc_armor_drop_min_pct": ("NPC equipment & armor loot", "Looted armor minimum condition", 0, 100, 1, 20, 1,
        "Condition of the extra armor drops above. If minimum exceeds maximum, the endpoints are sorted."),
    "npc_armor_drop_max_pct": ("NPC equipment & armor loot", "Looted armor maximum condition", 0, 100, 1, 80, 1,
        "Condition of the extra armor drops above. Requires armor loot chance above zero."),
    "npc_loaded_ammo_factor": ("NPC equipment & armor loot", "Ammo loaded in found NPC weapons", 0, 400, 5, 100, 100,
        "Scales the ammo already loaded in generated NPC weapons, separately from loose ammunition and loot stack amounts. Not play-tested yet."),
    "npc_helmet_chance_factor": ("NPC equipment & armor loot", "NPC helmet generation chance", 0, 400, 5, 100, 100,
        "Scales existing optional helmet rolls in ordinary NPC equipment. Guaranteed helmet lists remain guaranteed. Not play-tested yet."),
    "vegetation_translucency_factor": ("Vegetation & NPC weapon dispersion", "AI sight through grass and leaves", 0, 300, 5, 100, 100,
        "Scales AI material translucency for grass and leaves. Lower values make vegetation less transparent to AI. Does not change the rendered vegetation. Not play-tested yet."),
    "npc_dispersion_distance_factor": ("Vegetation & NPC weapon dispersion", "NPC dispersion distance", 1, 400, 1, 100, 100,
        "Experimental: changes FireDistanceDispersion in NPC weapon settings. Its exact effect on hit accuracy is not verified; player weapon settings are excluded."),
    "mutant_loot_range_factor": ("Mutant looting", "Mutant loot interaction range", 25, 400, 5, 100, 100,
        "Multiplier on mutant looting reach. Combines multiplicatively with the general interaction range slider. Not play-tested yet."),
    "mutant_loot_height_factor": ("Mutant looting", "Mutant loot maximum interaction height", 25, 400, 5, 100, 100,
        "Scales the top of the mutant looting height window. Combines with general interaction range."),
    "mutant_cut_radius_factor": ("Mutant looting", "Mutant cut radius (experimental)", 25, 400, 5, 100, 100,
        "Scales CutRadiusModifier. It may affect the cut mark rather than looting reach; its gameplay effect is unverified."),
    "mutant_trophy_weight_factor": ("Mutant trophies", "Mutant trophy weight", 0, 400, 5, 100, 100,
        "Scales the weight of native mutant trophies. These items have their own template and are separate from ordinary item weight categories."),
    "mutant_trophy_value_factor": ("Mutant trophies", "Mutant trophy base value", 0, 400, 5, 100, 100,
        "Scales trophy base prices. Trader buying/selling multipliers still apply separately."),
    "decal_lifetime_factor": ("Blood & bullet marks", "Blood / projectile decal lifetime", 10, 1000, 10, 100, 100,
        "Scales projectile decal lifetime on the world and corpses. More persistent marks can increase resource usage. Not play-tested yet."),
    "decal_count_factor": ("Blood & bullet marks", "Blood / projectile decal capacity", 25, 1000, 25, 100, 100,
        "Scales agent, mesh and corpse decal pools and saved corpse marks. Footstep pools are separate. Not play-tested yet."),
    "field_repair_body_pct": ("Hercules field repair (experimental)", "Body armor repair per Hercules", 0, 25, 1, 0, 1,
        "Adds native negative-corrosion repair effects when consuming Hercules. 0 = off. Its normal effects remain. Repair behavior has not been verified in-game."),
    "field_repair_head_pct": ("Hercules field repair (experimental)", "Helmet repair per Hercules", 0, 25, 1, 0, 1,
        "Optional repair bonus on Hercules for the equipped helmet. Experimental native effect; 0 = off."),
    "field_repair_weapons_pct": ("Hercules field repair (experimental)", "Equipped weapon repair per Hercules", 0, 25, 1, 0, 1,
        "Applies to primary weapon, secondary weapon and pistol slots. Experimental native effect; 0 = off."),
    "bolt_lifetime_factor": ("Artifact & bolt options", "Thrown bolt lifetime", 10, 2500, 10, 100, 100,
        "Scales how long a thrown bolt remains before disappearing. Does not add collectible or consumable bolts. Not play-tested yet."),
}

# field: (section, label, tooltip)
CHECKS = {
    "stash_extra_artifacts": ("Extra stash finds", "Extra artifacts in ordinary stashes", "Adds a separate roll from current ordinary artifact pools; quest and unique artifacts are excluded."),
    "stash_extra_weapons": ("Extra stash finds", "Extra weapons in ordinary stashes", "Adds a separate ordinary weapon roll; quest and unique weapons are excluded."),
    "stash_extra_armor": ("Extra stash finds", "Extra armor & helmets in ordinary stashes", "Adds a separate ordinary armor or helmet roll."),
    "stash_extra_attachments": ("Extra stash finds", "Extra attachments in ordinary stashes", "Adds a separate ordinary weapon attachment roll."),
    "npc_equipment_variety": ("NPC equipment & armor loot", "Keep lower-rank NPC equipment in the pool", "Retains ordinary lower-rank gear within the same faction and equipment slot. Higher ranks can also roll simpler equipment. Not play-tested yet."),
    "mutant_loot_ground_access": ("Mutant looting", "Allow mutant looting down to ground level", "Sets the lower interaction height to zero. The upper height has its own slider. Not play-tested yet."),
    "weird_flower_permanent": ("Artifact & bolt options", "Permanent Weird Flower stealth effect", "Appends the existing permanent flair-distance effect to Weird Flower. Separate from its charge/duration slider. Not play-tested yet."),
}


def label(value):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)


def build_controls(app, body, fmt_pct):
    sections = {}
    for field, (section, title, lo, hi, step, default, divisor, tip) in SLIDERS.items():
        if section not in sections:
            sections[section] = app._section(body, section)
        app._slider(sections[section], field, title, lo, hi, step, default, fmt_pct, tip)
    for field, (section, title, tip) in CHECKS.items():
        if section not in sections:
            sections[section] = app._section(body, section)
        app._check(sections[section], field, title, tip)
    frame = app._section(body, "Movement noise by surface")
    for material in SURFACES:
        app._slider(frame, "surface_noise:" + material, label(material), 0, 300, 5, 100, fmt_pct,
                    "Scales the existing character noise coefficient on this physical surface. Combines with general movement noise. Not play-tested yet.")
    frame = app._section(body, "Weather luminance for AI visibility")
    for weather in WEATHERS:
        app._slider(frame, "weather_luminance:" + weather, label(weather), 0, 200, 5, 100, fmt_pct,
                    "Scales the environment luminance contribution for this weather. Separate from weather hearing/visibility sliders; it does not change screen brightness. Not play-tested yet.")
    frame = app._section(body, "Trophy drops by mutant species")
    for species in SPECIES:
        for key, title in (("chance_factor", "drop chance"), ("amount_factor", "drop amount")):
            app._slider(frame, f"mutant_loot:{species}:{key}", f"{label(species)} {title}",
                        0, 400, 5, 100, fmt_pct,
                        "Additional multiplier for this species' native trophies. Chance combines with the global mutant loot chance; amount combines with global loot amount. Chance is capped, counts are whole numbers. Not play-tested yet.")


def collect_factors(sliders, prefix):
    return {key[len(prefix):]: row.get() / 100 for key, row in sliders.items()
            if key.startswith(prefix) and abs(row.get() - 100) > 1e-6}


def collect_mutant_loot(sliders):
    result = {}
    for key, value in collect_factors(sliders, "mutant_loot:").items():
        species, param = key.split(":", 1)
        result.setdefault(species, {})[param] = value
    return result


def dict_probe(key):
    for prefix, field in (("surface_noise:", "surface_noise_overrides"),
                          ("weather_luminance:", "weather_luminance_overrides")):
        if key.startswith(prefix):
            return {field: {key[len(prefix):]: .5}}
    if key.startswith("mutant_loot:"):
        species, param = key[len("mutant_loot:"):].split(":", 1)
        return {"mutant_loot_overrides": {species: {param: .5 if param == "chance_factor" else 2}}}
    return None
