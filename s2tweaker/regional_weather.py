"""Regional weather factors; audited scope in docs/REGIONAL_WEATHER_RESEARCH.md.

Identifiers below define scope, never numeric game baselines. Read current
values via GameData.resolve; missing or partially inherited rows stay inactive.
"""
from __future__ import annotations

import math
from .cfgparse import parse_number
from .emit import fmt_float

# Stable UI key: (display label, exact named profiles). Red Forest has two
# ordinary volumes with different baselines; one setting scales both separately.
REGIONS = {
    "LesserZoneWeather": ("Lesser Zone", ("LesserZoneWeather",)),
    "GarbageWeather": ("Garbage", ("GarbageWeather",)),
    "Region_PromZone": ("Industrial Zone", ("Region_PromZone",)),
    "Region_WildIsland": ("Wild Island", ("Region_WildIsland",)),
    "BackwaterWeatherSelection": ("Zaton (Backwater)", ("BackwaterWeatherSelection",)),
    "SwampWeatherSelection": ("Swamps", ("SwampWeatherSelection",)),
    "KordonWeatherSelection": ("Cordon", ("KordonWeatherSelection",)),
    "GradirniWeatherSelection": ("Cooling Towers", ("GradirniWeatherSelection",)),
    "CementPlantWeatherSelection": ("Cement Factory", ("CementPlantWeatherSelection",)),
    "RostokWeatherSelection": ("Rostok", ("RostokWeatherSelection",)),
    "MalahitWeatherSelection": ("Malachite", ("MalahitWeatherSelection",)),
    "YantarWeatherSelection": ("Yantar", ("YantarWeatherSelection",)),
    "DugaRegionWeather": ("Duga", ("DugaRegionWeather",)),
    "BurnForestRegionWeather": ("Burnt Forest", ("BurnForestRegionWeather",)),
    "YanovWeatherSelection": ("Yaniv", ("YanovWeatherSelection",)),
    "JupiterWeatherSelection": ("Jupiter", ("JupiterWeatherSelection",)),
    "Region_Prypiat": ("Prypiat", ("Region_Prypiat",)),
    "RedForestWeatherSelectionMain": ("Red Forest", (
        "RedForestWeatherSelectionMain", "RedForestWeatherSelectionSide")),
}
WEATHERS = {"Clearly": "Clear", "Cloudy": "Cloudy", "Fogy": "Fog",
            "Stormy": "Storm", "LightRainy": "Light rain", "Rainy": "Rain",
            "Thundery": "Thunderstorm"}
PARAMS = {"weight": ("selection weight", 0, 400),
          "duration": ("duration", 25, 400)}
PREFIX = "regional_weather:"
LEAVES = ("BlendWeight", "BlendWeightIncrease", "WeatherDurationMin", "WeatherDurationMax")


def control_key(region, weather, param):
    return f"{PREFIX}{region}:{weather}:{param}"


def split_key(key):
    if not key.startswith(PREFIX):
        return None
    parts = key[len(PREFIX):].split(":")
    if (len(parts) != 3 or parts[0] not in REGIONS
            or parts[1] not in WEATHERS or parts[2] not in PARAMS):
        return None
    return tuple(parts)


def control_specs():
    for region, (label, _targets) in REGIONS.items():
        for weather, weather_label in WEATHERS.items():
            for param, (title, lo, hi) in PARAMS.items():
                help_text = (
                    "Relative selection weight, not an occurrence probability. "
                    "Scales this weather's starting weight and history increase. "
                    "0% removes both weights; keep another weather type above 0%. "
                    "Combines with global Rain & storms for rainy weather."
                    if param == "weight" else
                    "Scales this weather's minimum and maximum duration together. "
                    "Combines with the global Weather duration setting.")
                yield (control_key(region, weather, param),
                       f"Regional weather: {label} / {weather_label} / {title} (%)",
                       lo, hi, 100,
                       help_text + " 100% = no regional change. Only weather already "
                       "enabled in this region is offered. Quest/forced weather can "
                       "override normal weather; changes may wait for a later "
                       "transition. Not play-tested yet.")


def catalog(gd):
    """Current eligible rows: region -> weather -> profile -> raw leaf values."""
    root = gd.weatherselection
    result = {}
    for region, (_label, profiles) in REGIONS.items():
        for weather in WEATHERS:
            baselines = {}
            for profile in profiles:
                node = root.children.get(profile)
                child = node.children.get(weather) if node else None
                # Explicit leaves make cancellation safe even when global
                # controls also patch the shared indexed parent template.
                if (node is None or node.values.get("SID") != profile
                        or node.attr_dict().get("refurl") or child is None
                        or child.attrs or not all(k in child.values for k in LEAVES)):
                    break
                raw = {k: gd.resolve(root, profile, f"{weather}.{k}") for k in LEAVES}
                nums = {k: parse_number(v, math.nan) for k, v in raw.items()}
                if (not all(math.isfinite(v) for v in nums.values())
                        or nums["BlendWeight"] <= 0 or nums["BlendWeightIncrease"] < 0
                        or nums["WeatherDurationMin"] <= 0
                        or nums["WeatherDurationMax"] < nums["WeatherDurationMin"]):
                    break
                baselines[profile] = raw
            else:
                result.setdefault(region, {})[weather] = baselines
    return result


def available_keys(data):
    return {control_key(r, w, p) for r, rows in data.items()
            for w in rows for p in PARAMS}


def collect(sliders):
    result = {}
    for key, row in sliders.items():
        parts = split_key(key)
        if parts and abs(row.get() - 100) > 1e-6:
            region, weather, param = parts
            result.setdefault(region, {}).setdefault(weather, {})[param] = row.get() / 100
    return result


def probe(key):
    parts = split_key(key)
    if parts:
        region, weather, param = parts
        return {"regional_weather_overrides": {region: {weather: {param: .5}}}}
    return None


def changes(overrides):
    """Validate supported saved factors; ignore foreign scope/unknown fields."""
    if not isinstance(overrides, dict):
        raise ValueError("Regional weather settings must be a mapping.")
    for region, rows in overrides.items():
        if region not in REGIONS:
            continue
        if not isinstance(rows, dict):
            raise ValueError("Invalid regional weather settings for " + REGIONS[region][0])
        for weather, params in rows.items():
            if weather not in WEATHERS:
                continue
            if not isinstance(params, dict):
                raise ValueError("Invalid regional weather factors.")
            for param, factor in params.items():
                if param not in PARAMS:
                    continue
                _title, lo, hi = PARAMS[param]
                if (isinstance(factor, bool) or not isinstance(factor, (int, float))
                        or not math.isfinite(factor) or not lo / 100 <= factor <= hi / 100):
                    raise ValueError(f"{REGIONS[region][0]} {WEATHERS[weather]} "
                                     f"{param}: enter {lo}-{hi}%.")
                if abs(factor - 1) > 1e-6:
                    yield region, weather, param, factor


def _set_final(patches, profile, weather, leaf, raw, factor):
    base = parse_number(raw)
    value = base * factor
    if (not math.isfinite(value) or value < 0
            or leaf.startswith("WeatherDuration") and value <= 0):
        raise ValueError("Regional weather needs finite, nonnegative weights and positive durations.")
    if math.isclose(value, base, rel_tol=1e-9, abs_tol=1e-8):
        # Remove an earlier global edit if the composed factors cancel.
        cfg = patches.get(profile, {})
        row = cfg.get(weather, {})
        row.pop(leaf, None)
        if not row:
            cfg.pop(weather, None)
        if not cfg:
            patches.pop(profile, None)
    else:
        patches.setdefault(profile, {}).setdefault(weather, {})[leaf] = fmt_float(value)


def apply(gd, settings, patches):
    """Compose regional settings into the existing global weather patch."""
    selected = list(changes(settings.regional_weather_overrides))
    if not selected:
        return patches
    data = gd.regional_weather
    weight_factors = {}
    touched = set()
    for region, weather, param, factor in selected:
        rows = data.get(region, {}).get(weather)
        if not rows:
            continue
        touched.add(region)
        if param == "weight":
            weight_factors[region, weather] = factor
        for profile, raw in rows.items():
            if param == "weight":
                global_factor = settings.rain_factor if weather in gd.RAIN_WEATHER_TYPES else 1
                _set_final(patches, profile, weather, "BlendWeight", raw["BlendWeight"],
                           global_factor * factor)
                _set_final(patches, profile, weather, "BlendWeightIncrease",
                           raw["BlendWeightIncrease"], factor)
            else:
                for leaf in ("WeatherDurationMin", "WeatherDurationMax"):
                    _set_final(patches, profile, weather, leaf, raw[leaf],
                               settings.weather_duration_factor * factor)
    for region in touched:
        for profile in REGIONS[region][1]:
            total = sum(parse_number(rows[profile]["BlendWeight"])
                        * weight_factors.get((region, weather), 1)
                        * (settings.rain_factor if weather in gd.RAIN_WEATHER_TYPES else 1)
                        for weather, rows in data[region].items())
            if not math.isfinite(total) or total <= 0:
                raise ValueError(f"{REGIONS[region][0]}: keep at least one weather "
                                 "selection weight above 0% (including global Rain & storms).")
    return patches


def summarize(overrides):
    return [f"Regional weather / {REGIONS[r][0]} / {WEATHERS[w]} "
            f"{PARAMS[p][0]}: {v * 100:g}%" for r, w, p, v in changes(overrides)]
