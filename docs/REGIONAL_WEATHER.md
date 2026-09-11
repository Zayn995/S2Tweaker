# Regional weather — S2Tweaker 1.38.0

Open **World → Regional weather (experimental)**, choose a region, then click
**Edit this region's weather**. Load the game data first. The button opens the
existing settings list filtered to that region.

Each available weather type has two percentage settings:

- **Selection weight:** 100% keeps its regional baseline; 200% doubles its
  weight, and 0% removes both the starting weight and its history increase.
  This is a relative weight, not a probability. Other weather types, history,
  repeat limits and cooldowns affect the actual selection.
- **Duration:** 25–400% of the installed game's minimum and maximum duration.
  Both ends scale together, preserving the range. 100% makes no regional change.

For example, choose Lesser Zone, set Fog selection weight to 200% and Fog
duration to 150%, then generate your pak. The changes apply to that region's
ordinary fog selection. They do not force fog immediately or change another
region's ordinary weather profile.

Return a value to **100** to remove that regional change. Favorites, search,
undo/redo, profiles, settings persistence and conflict avoidance work through
the existing editor. **Reset all to vanilla** also resets regional weather.

## Available regions and weather

The first implementation supports 18 selections: Lesser Zone, Garbage,
Industrial Zone, Wild Island, Zaton (Backwater), Swamps, Cordon, Cooling Towers,
Cement Factory, Rostok, Malachite, Yantar, Duga, Burnt Forest, Yaniv, Jupiter,
Prypiat and Red Forest. Red Forest scales two distinct ordinary profiles using
each profile's own installed values. Industrial Zone and Zaton/Backwater labels
follow internal identifiers; exact geographic boundaries have not been checked
in-game.

After data loading, the list shows only currently enabled weather with complete
verified numeric fields. On the audited 2.0.5 snapshot this means **94 weather
rows / 188 settings** across 19 underlying profiles. Storm appears only in
regions where its vanilla weight is positive. Thunderstorm has zero weight in
all supported profiles and is consequently not offered. These factors never
invent a positive starting value for previously disabled weather.

If a later game update makes a saved selection unavailable, it remains visible
as **inactive** so it can be reset to 100%; it produces no regional patch. A
partly inherited or malformed entry is also inactive until reviewed.

## Combining settings

Regional and global factors multiply:

| Changed value | Calculation |
|---|---|
| Rain-type starting weight | Installed value × global Rain & storms × regional selection weight |
| Clear/cloudy/fog starting weight | Installed value × regional selection weight |
| Ordinary weather history increase | Installed value × regional selection weight |
| Minimum and maximum duration | Installed value × global Weather duration × regional duration |

The existing global Rain & storms control does not scale history increases;
its previous behavior is preserved. If two factors cancel back to the installed
value, that leaf is omitted from the generated patch. A history increase may
still differ even when its starting weight cancels back to vanilla.

The generator rejects a combination that leaves no positive ordinary starting
weight in a changed region, including the effect of global Rain & storms. It
does not silently choose a fallback weather or normalize your weights.

## Scope and validation limits

Regional settings modify only the audited named profiles and ordinary weather
types. They exclude emissions, the calm before an emission, underground,
quests, forced/anomaly weather, SIRCAA and the unconfirmed Chemical Plant
profile. Priority, cooldown/repetition rules, transition flags and spawn volumes
remain untouched by the regional controls. Existing **global** controls retain
their broader scope when explicitly changed.

Available since 1.38.0; **not play-tested**. Configuration tests cannot
prove runtime weather transitions: quests and forced weather may override an
ordinary region, and changes may wait for a later transition. No UE4SS or other
runtime loader is required; output uses the existing cfg-patch pak mechanism.

Research, complete baseline tables and scope evidence:
[REGIONAL_WEATHER_RESEARCH.md](REGIONAL_WEATHER_RESEARCH.md).
Regression checks: `tests/test_regional_weather.py`. The optional single-window
check is `tools/check_gui_resources.py --open-window --regional-weather
--vanilla <GameData folder> --report <report.json>` (add `--portable <tool folder>`
to exercise an assembled portable copy).
