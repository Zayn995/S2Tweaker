# Regional weather selection research

Verified from the local Steam 2.0.5 snapshot on 2026-09-11, before implementation.
This is a configuration audit, not an in-game verification of weather behavior.
Numeric baselines below belong in this document only; application code must read
the installed snapshot through `gd.resolve(...)`.

## Sources and exact inventory

Primary source: `vanilla/Stalker2/Content/GameLite/GameData/WeatherSelectionPrototypes.cfg`.
It contains **4,230 lines, 45 top-level structures, and 450 weather children**
(exactly 10 per root). There are 5 indexed and 40 named roots. All 450 children
explicitly contain the same seven scalar leaves:
`BlendWeight`, `BlendWeightIncrease`, `WeatherDurationMin`, `WeatherDurationMax`,
`MaximumRepeatAmount`, `MaximumCooldownWeatherAmount`, and
`bAllowInDialogueTransition`. That is 3,150 child scalar values, with no missing
weight or duration leaf in this snapshot. There are no child `refkey`/`refurl`
attributes. Top-level inheritance is 35 `refkey=[1]`, 7 `refkey=[0]`, and 3 roots
without a parent; there are no cross-file `refurl` references.

The preserved pre-2.0.5 snapshot has the same 45 root names. Numeric comparison of
the starting-weight and two duration leaves finds **254 changes: 66 selection weights,
94 minimum durations, and 94 maximum durations**. All 254 occur in the same
20 candidate regional profiles listed below. This is supporting scope evidence,
not proof that every profile is currently used by a loaded map volume.

Independent map-volume and quest-reference checks are recorded below.
Chemical Plant has a
regional-looking updated profile but its active volume usage is unconfirmed;
exclude it from the first UI unless further evidence establishes usage.
The confirmed implementation scope is **19 profiles, grouped into 18 UI regions**
(Red Forest uses both main and side profiles). These profiles are referenced by
21 broad world volumes, all with `SpawnOnStart=true` and `bForceWeather=false`.
No direct profile-name or corresponding volume-GUID reference was found in the
full extracted QuestNode snapshot. The following scope audit records those volume lines
and the limits of that negative evidence. “Industrial Zone” and “Zaton
(Backwater)” are display mappings inferred from internal names, not an in-game
verification of region boundaries.

## Region-volume evidence

The second source is
`vanilla/Stalker2/Content/GameLite/GameData/SpawnActorPrototypes.cfg`.
It contains **5,068,665 lines and 130,058 top-level structures** (counted from
decoded text). It is only a reference-evidence source for this feature; no
spawn-actor edits or new runtime extraction requirement are proposed.
The following are the start lines of the world-volume roots referencing each
included weather profile. All 21 references belong to broad volumes with
`SpawnOnStart=true` and `bForceWeather=false`; two profiles each have two
references. This is an explicit allowlist, not a blanket rule that every
non-forced volume is safe.

| Profile | Volume root line(s) | UI group |
|---|---|---|
| `LesserZoneWeather` | 3230850 | Lesser Zone |
| `GarbageWeather` | 4331698 | Garbage |
| `Region_PromZone` | 3073665 | Industrial Zone |
| `Region_WildIsland` | 3209083, 3998799 | Wild Island |
| `BackwaterWeatherSelection` | 1298343 | Zaton (Backwater) |
| `SwampWeatherSelection` | 1558566 | Swamps |
| `KordonWeatherSelection` | 1602639 | Cordon |
| `GradirniWeatherSelection` | 1735659 | Cooling Towers |
| `CementPlantWeatherSelection` | 1919052 | Cement Factory |
| `RostokWeatherSelection` | 3102169 | Rostok |
| `MalahitWeatherSelection` | 2204413 | Malachite |
| `YantarWeatherSelection` | 2746519 | Yantar |
| `DugaRegionWeather` | 4459947 | Duga |
| `BurnForestRegionWeather` | 2684834, 4505490 | Burnt Forest |
| `YanovWeatherSelection` | 1510135 | Yaniv |
| `JupiterWeatherSelection` | 1536052 | Jupiter |
| `Region_Prypiat` | 954956 | Prypiat |
| `RedForestWeatherSelectionMain` | 3021543 | Red Forest |
| `RedForestWeatherSelectionSide` | 4782787 | Red Forest |

The two Red Forest selections have different priorities and numeric baselines;
group their controls, but calculate each target independently. The
`RegionMusicPrototype.Gradirni` asset path supports the “Cooling Towers” label.
“Industrial Zone” is a conservative mapping of the internal Promzona name;
do not relabel that profile as Chemical Plant without further evidence.
“Zaton (Backwater)” is a display-name inference.

Forced-volume checks support excluding `PoppyField_WeatherSelection`
(volume priority 100), `Gradirni_FireBreath_WeatherSelection` (51),
`BurnForest_Mist_WeatherSelection` (52), `WasteWarehouse_NoClear` (52),
`NoRainWeatherSelection` (0), `DeadValleyWeatherSelection` (0),
`DeadForestWeatherSelection` (0), and `SIIRCAWeatherSelection` (1).
Each has `bForceWeather=true` in its inspected volume. `Region_ChemicalPlant`
has no `VolumeSID` reference in the inspected full snapshot and remains
unconfirmed. A non-forced volume is insufficient by itself: `SQ10_NoEmission_Weather`
is quest-linked and priority 99, while `CNPP_Archanomaly_WeatherSelection` is a
small priority-99 special volume whose profile is absent from the 45-root file.
Both remain excluded. Full extracted QuestNode scans found zero direct matches
for the 19 included profile names or their 21 corresponding volume GUIDs;
indirect engine, map, or quest control is still possible.

## Every top-level root

For the 40 named roots, the structure key equals its `SID`. Only the five indexed
roots have a different `SID`, shown explicitly below. Line numbers refer to the
decoded primary source above. Priority is the selection-profile value, not a
spawn-volume priority; `UndergroundWeatherVolume` has no explicit priority.

| Root / patch key | SID when different | Line | Parent | Priority | Scope |
|---|---|---:|---|---:|---|
| `[0]` | `Empty` | 1 | none | 0 | Indexed template / special: exclude |
| `[1]` | `BaseWeatherHistory` | 95 | [0] | 0 | Indexed template / special: exclude |
| `[2]` | `VortexWeatherSelection` | 189 | none | 10 | Indexed template / special: exclude |
| `[3]` | `EQ55_Weather` | 283 | [0] | 99 | Indexed template / special: exclude |
| `SwampWeatherSelection` | same | 377 | [1] | 1 | Ordinary regional candidate |
| `Region_ChemicalPlant` | same | 471 | [1] | 15 | Regional candidate; verify usage |
| `Region_PromZone` | same | 565 | [1] | 14 | Ordinary regional candidate |
| `Region_WildIsland` | same | 659 | [1] | 14 | Ordinary regional candidate |
| `YanovWeatherSelection` | same | 753 | [1] | 1 | Ordinary regional candidate |
| `YantarWeatherSelection` | same | 847 | [1] | 1 | Ordinary regional candidate |
| `KordonWeatherSelection` | same | 941 | [1] | 1 | Ordinary regional candidate |
| `GradirniWeatherSelection` | same | 1035 | [1] | 1 | Ordinary regional candidate |
| `Gradirni_FireBreath_WeatherSelection` | same | 1129 | [1] | 1 | Special location / forced / underground: exclude |
| `CementPlantWeatherSelection` | same | 1223 | [1] | 5 | Ordinary regional candidate |
| `JupiterWeatherSelection` | same | 1317 | [1] | 29 | Ordinary regional candidate |
| `RedForestWeatherSelectionMain` | same | 1411 | [1] | 27 | Ordinary regional candidate |
| `RedForestWeatherSelectionSide` | same | 1505 | [1] | 28 | Ordinary regional candidate |
| `RostokWeatherSelection` | same | 1599 | [1] | 0 | Ordinary regional candidate |
| `LesserZoneWeather` | same | 1693 | [1] | 0 | Ordinary regional candidate |
| `GarbageWeather` | same | 1787 | [1] | 0 | Ordinary regional candidate |
| `DugaRegionWeather` | same | 1881 | [1] | 0 | Ordinary regional candidate |
| `BurnForestRegionWeather` | same | 1975 | [1] | 0 | Ordinary regional candidate |
| `BackwaterWeatherSelection` | same | 2069 | [1] | 0 | Ordinary regional candidate |
| `MalahitWeatherSelection` | same | 2163 | [1] | 1 | Ordinary regional candidate |
| `EQ140_WeatherVolume` | same | 2257 | [1] | 0 | Quest / prologue: exclude |
| `EQ37_Weather` | same | 2351 | [1] | 6 | Quest / prologue: exclude |
| `Emission_E15_MQ02` | same | 2445 | [1] | 5 | Quest / prologue: exclude |
| `DeadValleyWeatherSelection` | same | 2540 | [1] | 0 | Special location / forced / underground: exclude |
| `DeadForestWeatherSelection` | same | 2634 | [1] | 0 | Special location / forced / underground: exclude |
| `NoRainWeatherSelection` | same | 2728 | [1] | 0 | Special location / forced / underground: exclude |
| `PoppyField_WeatherSelection` | same | 2822 | [1] | 1 | Special location / forced / underground: exclude |
| `SQ10_NoEmission_Weather` | same | 2916 | [1] | 0 | Quest / prologue: exclude |
| `SIIRCAWeatherSelection` | same | 3010 | [1] | 17 | Special location / forced / underground: exclude |
| `SQ88_Weather` | same | 3104 | [1] | 0 | Quest / prologue: exclude |
| `PrologueWeatherClearly` | same | 3198 | [0] | 99 | Quest / prologue: exclude |
| `[35]` | `E14_MQ02FoundationWeatherSelection` | 3292 | [1] | 1 | Indexed template / special: exclude |
| `E03_MQ06_WeatherStormy` | same | 3386 | [0] | 99 | Quest / prologue: exclude |
| `E03_MQ05_WeatherClearly` | same | 3480 | [0] | 99 | Quest / prologue: exclude |
| `E08_MQ05_WeatherRainy` | same | 3574 | [0] | 99 | Quest / prologue: exclude |
| `BurnForest_Mist_WeatherSelection` | same | 3668 | [1] | 1 | Special location / forced / underground: exclude |
| `E08_MQ05_WeatherCloudy` | same | 3762 | [0] | 99 | Quest / prologue: exclude |
| `WasteWarehouse_NoClear` | same | 3856 | [1] | 99 | Special location / forced / underground: exclude |
| `Region_Prypiat` | same | 3950 | [1] | 0 | Ordinary regional candidate |
| `StormyForced` | same | 4044 | [1] | 18 | Special location / forced / underground: exclude |
| `UndergroundWeatherVolume` | same | 4138 | none | absent | Special location / forced / underground: exclude |

## Exact editable paths and all candidate values

The patch keys are the top-level structure names, not invented region names.
For each candidate `R` and ordinary weather child `W`, only these leaves are
within the proposed feature's scope:

```text
R.W.BlendWeight
R.W.BlendWeightIncrease
R.W.WeatherDurationMin
R.W.WeatherDurationMax
```

For example: `LesserZoneWeather.Fogy.BlendWeight`,
`LesserZoneWeather.Fogy.WeatherDurationMin`, and
`LesserZoneWeather.Fogy.WeatherDurationMax`.
The spelling **`Fogy`** is the actual game key, despite the UI label “Fog”.
Ordinary `W` keys are `Clearly`, `Cloudy`, `Fogy`, `Stormy`, `LightRainy`,
`Rainy`, and `Thundery`; these are weather categories, not guaranteed exact
rendering descriptions. `Stormy` and `Thundery` must remain distinct.

Each cell below is **weight / minimum duration / maximum duration**, in raw
numeric cfg units (duration is treated as seconds by the existing weather tool).
Literal suffixes such as `.f` are omitted for compactness; no rounding is applied.
Each triple was read from the current file, including zero-weight categories.
This table is all 420 editable candidate values (20 × 7 × 3), not a sample.

| Profile / intended display label | Clearly | Cloudy | Fogy | Stormy | LightRainy | Rainy | Thundery |
|---|---:|---:|---:|---:|---:|---:|---:|
| `SwampWeatherSelection` — Swamps | 20/1500/2000 | 20/1500/2000 | 20/1000/1500 | 0/200/400 | 20/1000/1500 | 10/1000/1500 | 0/500/700 |
| `Region_ChemicalPlant` — Chemical Plant (usage unconfirmed) | 30/1500/2000 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 20/1000/1500 | 10/1000/1500 | 0/500/700 |
| `Region_PromZone` — Industrial Zone | 30/1500/2000 | 30/2000/2500 | 15/1000/1500 | 0/200/400 | 15/1000/1500 | 10/1000/1500 | 0/500/700 |
| `Region_WildIsland` — Wild Island | 20/1500/2000 | 40/2000/2500 | 10/1000/1500 | 10/200/400 | 15/1000/1500 | 15/1000/1500 | 0/500/700 |
| `YanovWeatherSelection` — Yaniv | 25/1500/2000 | 30/2000/2500 | 15/1000/1500 | 0/300/600 | 15/1000/1500 | 15/1000/1500 | 0/500/700 |
| `YantarWeatherSelection` — Yantar | 20/1500/2000 | 30/2000/2500 | 15/1000/1500 | 5/200/400 | 10/1000/1500 | 20/1500/2000 | 0/600/1200 |
| `KordonWeatherSelection` — Cordon | 30/1500/2000 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 20/1000/1500 | 10/1000/1500 | 0/600/1200 |
| `GradirniWeatherSelection` — Cooling Towers | 25/1500/2000 | 30/1500/2000 | 10/1000/1500 | 5/200/400 | 10/1000/1500 | 20/1000/1500 | 0/600/1200 |
| `CementPlantWeatherSelection` — Cement Factory | 25/1500/2000 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 20/1000/1500 | 15/1000/1500 | 0/600/1200 |
| `JupiterWeatherSelection` — Jupiter | 30/1500/2000 | 30/1500/2000 | 10/1000/1500 | 0/200/400 | 10/1000/1500 | 20/1000/1500 | 0/600/1200 |
| `RedForestWeatherSelectionMain` — Red Forest — main volume | 40/1500/2000 | 30/1500/2000 | 10/1000/1500 | 0/200/400 | 10/1000/1500 | 10/1000/1500 | 0/600/1200 |
| `RedForestWeatherSelectionSide` — Red Forest — side volume | 30/1500/2000 | 20/1000/1500 | 10/1000/1500 | 0/200/400 | 30/1000/1500 | 10/1000/1500 | 0/600/1200 |
| `RostokWeatherSelection` — Rostok | 30/1000/1500 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 20/1000/1500 | 10/1000/1500 | 0/600/1200 |
| `LesserZoneWeather` — Lesser Zone | 30/2000/2500 | 30/1500/2000 | 10/1000/1500 | 0/150/300 | 20/1000/1500 | 10/1000/1500 | 0/500/700 |
| `GarbageWeather` — Garbage | 30/1500/2000 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 15/1000/1500 | 10/1000/1500 | 0/500/700 |
| `DugaRegionWeather` — Duga | 30/1000/1500 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 10/1000/1500 | 20/1000/1500 | 0/500/700 |
| `BurnForestRegionWeather` — Burnt Forest | 10/1000/1500 | 30/1000/1500 | 20/1000/1500 | 0/200/400 | 20/1000/1500 | 20/1000/1500 | 0/500/700 |
| `BackwaterWeatherSelection` — Zaton | 20/1000/1500 | 30/1000/1500 | 10/1000/1500 | 0/200/400 | 10/1000/1500 | 30/1000/1500 | 0/500/700 |
| `MalahitWeatherSelection` — Malachite | 20/1000/1500 | 30/2000/2500 | 10/1000/1500 | 0/200/400 | 20/1000/1500 | 20/1000/1500 | 0/600/1200 |
| `Region_Prypiat` — Prypiat | 30/2000/2500 | 30/1500/2000 | 10/2000/2500 | 5/200/400 | 15/1000/1500 | 10/1000/1500 | 0/500/700 |

The fourth editable leaf, `BlendWeightIncrease`, is 0 for **137 of 140**
ordinary candidate entries. This is the complete list of its three exceptions:

| Exact path | Value | First-version scope |
|---|---:|---|
| `Region_ChemicalPlant.LightRainy.BlendWeightIncrease` | 15 | Excluded, usage unconfirmed |
| `YanovWeatherSelection.LightRainy.BlendWeightIncrease` | 15 | Included |
| `BurnForestRegionWeather.LightRainy.BlendWeightIncrease` | 30 | Included |

Thus the supported 19 profiles contain exactly **2 nonzero and 131 zero**
ordinary increases. Scale this leaf with the regional weight factor as well
as `BlendWeight`; setting only the initial weight to 0 would leave a positive
history increase and could allow weight to accumulate later. This describes
the configuration risk; the exact accumulation timing has not been play-tested.

All 20 candidates also have these identical, **excluded** weight/duration values:

| Weather child | Weight | Minimum | Maximum | Weight increase |
|---|---:|---:|---:|---:|
| `Emission` | 0 | 300 | 300 | 100 |
| `CalmBeforeEmission` | 0 | 120 | 120 | 0 |
| `Underground` | 0 | 0 | 24 | 0 |

Do not infer from emission weight 0 that emissions are disabled: their
`BlendWeightIncrease` is 100 and their history/cooldown parameters are separate.

### Zero weights and outliers

Across the 20 candidates, 104 of 140 ordinary weather entries have positive
selection weights; 36 have zero weight. `Clearly`, `Cloudy`, `Fogy`,
`LightRainy`, and `Rainy` are positive in all 20. `Stormy` is positive only in
`Region_WildIsland` (10), `YantarWeatherSelection` (5),
`GradirniWeatherSelection` (5), and `Region_Prypiat` (5).
`Thundery` has zero weight in all 20. Multiplying a zero weight cannot enable
that weather type. A live-positive-only UI avoids ineffective controls and
does not invent new game values. Excluding the unconfirmed Chemical Plant
profile leaves 19 supported profiles and 99 positive entries.

Ordinary weight sums are **90 for Swamp, 110 for Wild Island, 95 for Garbage,
and 100 for the other 17**. Therefore neither raw weights nor a factor should
be labeled as the probability of that weather occurring. Repetition limits,
cooldowns, priority, forced volumes, quests, and weather history also matter.
There is no evidence here for the precise runtime selection algorithm.

Durations differ by region and weather: for example, Lesser Zone clear weather
is 2000–2500, while Rostok clear weather is 1000–1500; Lesser Zone storm is
150–300, while Yaniv storm is 300–600. Prypiat fog is 2000–2500. A generic
500–1200 baseline would be wrong for many current entries.

## Inheritance and patching traps

Every candidate profile inherits `refkey=[1]`; `[1]` in turn inherits `[0]`.
The current decoded profiles nevertheless explicitly restate all weather
leaves. Read through `gd.resolve(root, sid, path)` for the actual baseline,
but require all four target leaves to be explicitly declared in the selected
profile for first-version eligibility. A later partial/inherited schema must
become inactive until reviewed: otherwise an omitted local leaf plus a changed
global template could leak through when global and regional factors cancel.
Do not copy the numbers from this document into code, and do not assume the
explicit ordering of weather children is fixed (it differs between profiles).

Do not patch `[0]`, `[1]`, `[2]`, `[3]`, or `[35]` for a regional setting.
Indexed roots have their own emission behavior in the existing patch writer,
and base changes may affect children outside the intended region. Named
regional roots can carry narrow `bpatch` leaves without serializing the entire
base. Their `SID` and `Priority` must remain untouched.

The existing global weather controls already patch a broader set of profiles
and duration children. A new regional-only setting must emit only allowlisted
regional ordinary-weather leaves; it must not silently expand its scope to
match that older global behavior. When used together, clearly define
multiplicative composition for the existing rain-type set:

```text
BlendWeight = vanilla weight × global rain factor × regional weight factor
BlendWeightIncrease = vanilla increase × regional weight factor
DurationMin/Max = vanilla duration × global duration factor × regional duration factor
```

For non-rain types, the global rain factor is 1. Existing global rain behavior
does not scale ordinary `BlendWeightIncrease`; preserve that distinction.
Emit only final values different from resolved vanilla, including when two
factors cancel back to 1 for one leaf but not another.

## WARNINGS

- Keep all 25 noncandidate roots outside this feature, plus Chemical Plant
  until its active usage is verified. This includes base/indexed roots,
  quest/prologue weather, forced anomalous or special locations, and underground.
  A name without a quest prefix is insufficient evidence of an ordinary region.
- `Emission_E15_MQ02` is an explicit quest emission, with its own
  `EmissionPrototypeSID` and 50/50 emission durations. Broad matching would
  change this scripted sequence. Never touch it for regional weather.
- Never change `Emission`, `CalmBeforeEmission`, `Underground`, priority,
  special-weather `BlendWeightIncrease`, repeat/cooldown counts, dialogue-transition flags,
  forced-volume flags, or spawn actors for the regional feature.
- Preserve zero weights. A duration-only edit to a zero-weight category may
  have no visible effect; presenting it as a way to enable that weather would
  be misleading. Read active categories from the installed data.
- Reject a combination that disables every ordinary positive weather weight
  of a target profile. Do not invent a fallback weather or silently normalize
  the remaining weights. Validate finite nonnegative weight factors and
  positive duration factors; scale min and max together.
- Configuration validation and pak readback do not demonstrate that the game
  picked a profile, loaded a region, or changed weather correctly. Forced/quest
  weather can override normal selection, and effects may wait for a later
  weather transition. Retain an experimental / not play-tested notice.

## Bounded implementation recommendation

Expose verified ordinary profiles through a region selector and reuse the
existing paged overview so control count does not grow the entire window's
native handle footprint. Start with live-positive ordinary weather entries:
one relative selection-weight factor and one shared min/max duration factor
per entry. Baseline is 1×; the nested saved map
`regional_weather_overrides[ui_region_key][weather][weight|duration]` keeps
unmodified combinations absent and maps a grouped region to its target profiles.
No new file is required: the source is already
in `NEEDED_FILES`, so this feature alone does not require a cache-schema bump.

At the data level the 20 candidates offer 104 active entries (208 controls);
excluding unconfirmed Chemical Plant gives 99 entries (198 controls) before
grouping the two Red Forest profiles. UI grouping must still use each
profile's own live baseline, including differing values within Red Forest.
The five shared Red Forest weather rows then become five grouped rows, so the
current snapshot yields **94 active UI rows / 188 weight-and-duration controls**
across the 18 supported regions, while retaining 99 underlying profile targets.
First implementation uses these 19 profiles / 18 regions. Only baseline-positive,
explicitly declared weather rows become active once game data is loaded.
Unavailable unchanged settings stay hidden; saved changes that become
unavailable remain visibly inactive and resettable rather than silently applying
to a different target.
Test exact scope, changed-value-only emission, vanilla no-op, zero-weight
handling, per-region isolation, min/max scaling, global/regional composition,
save/load, and generated pak readback. Confirm both ordinary weather transitions
and unchanged quest/emission behavior in-game before removing the warning.
