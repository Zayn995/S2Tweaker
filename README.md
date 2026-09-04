# S2Tweaker — S.T.A.L.K.E.R. 2 Mod Generator

A Windows GUI tool that builds a personal tweak mod (`.pak`) for
**S.T.A.L.K.E.R. 2: Heart of Chornobyl** from sliders and checkboxes —
no modding knowledge needed.

**Open source (MIT).** Everything in this repo was written by Claude
(Anthropic's AI) — the project owner can't code and considers this a working
**concept** for people who can: fork it, improve it, find bugs, build on it.
Everyone is free to use it. This README tells you everything you need.

## What it does

- Reads the **vanilla values from YOUR installed game version** (extracts the
  needed `.cfg.bin` GameData from `pakchunk0` and decodes it) — so multiplier
  tweaks stay correct after game patches.
- Generates **`{bpatch}` config patches** (the official patch system since
  game version 1.6): only the values you change are written; everything at
  "(vanilla)" is untouched and cannot conflict with other mods.
- Packs them with **repak** into `zzz_<Name>_P.pak` (pak V8B, mount point
  `../../../`) — into an `output` folder, or directly into `~mods`.
- Fully **portable**: settings, cache and output live next to the exe.

~180 tweaks in 13 tabs (Player, Vaulting, Weight & items, Combat, NPCs & AI,
Mutants, Factions, Weapons, Ammo, Armor, World, Economy, Traders), plus per-weapon overrides
for 91 weapons (unique named guns and the Pre-order/Deluxe/Ultimate
edition guns included), per-round overrides for 34
ammo types and per-piece
overrides for 57 armors/helmets (edition armor included): health/stamina/regen, per-action
stamina costs, fall damage, movement speed, jump height, carry weight +
penalty threshold, item weights per category, player/NPC/mutant damage &
health (incl. a per-species mutant tree with health/speed/damage/regen
and bloodsucker cloaking; mutant health regen ×0 = the mutant version
of "NPCs don't self-heal"),
headshots, explosions, armor protection per damage type, weapon damage/
spread/recoil/durability/fire rate/range/bleeding/ADS move speed/ADS
aim-in speed/magazine size on three levels, technician upgrade locks (take both / no blueprint / no tiers), A-Life spawns (lair population, respawn, encounter frequency, mutant share, pack size, per-species weights), day length, consumable effect duration, artifacts per field + respawn, weightless quest items, NPC combat behaviour (guaranteed-hit shots, burst length, fire pauses, engagement range, NPC weapon range, NPC regen), stealth (crouch, movement noise, weather, flashlight), NPC awareness & nerve (alertness, search time, courage, stagger, attack cooldowns, weapon rank bonus), melee, jamming, scoped sway,
breath hold, repeatable-quest cooldown, ammo
damage/armor piercing/armor damage/cover penetration, NPC accuracy/vision/
hearing/grenades, NPC gear quality (tilts squad loadout rolls toward
the pricier gear in their vanilla pools), faction relations
(player-vs-faction and faction-vs-faction baselines plus reputation
rollback time, reaction strength and the trading threshold),
artifacts & detectors, anomaly/radiation/bleeding,
hunger/sleep rates, weather & emissions (frequency and duration),
loot amounts in stashes, on bodies
and in the world's item generators, dropped-weapon condition (average +
vanilla-style random spread, or exact), trader prices & min. durability,
trader stock amount/variety/restock and wallets, repair/upgrade costs,
fast travel, quest rewards.

The override trees add up to 720 weapon and 100 ammo sliders (plus the
armor, faction and mutant trees) on top of the fixed ones — they are
built lazily when you expand a category, so startup stays fast.

## How it works (the important mechanics)

| Layer | Details |
|---|---|
| Network | **None.** Since 1.19.2 the program contains no networking code at all — no `urllib`, no sockets, no HTTP client — and the bundled repak is compiled without its HTTP/TLS stack. Both are enforced on every build ([tests/test_no_network.py](tests/test_no_network.py), [tests/test_no_download.py](tests/test_no_download.py)) and can be verified with one `grep` of this repository. The update check was removed with 1.19.2: Nexus' file submission guidelines prohibit internet-connecting executables "unless where it is crucial" and say "'auto update' functionality does not qualify as crucial". Updating is a manual file swap. |
| Vanilla data | `repak unpack` of `pakchunk0-Windows.pak` (only the 29 needed GameData files), then `.cfg.bin` → text via the vendored decoder ([s2tweaker/vendor_bin2cfg.py](s2tweaker/vendor_bin2cfg.py)). Cached in `cache/vanilla-<pakSize>-s<schema>/`; a game update changes the fingerprint → automatic re-extraction. |
| Oodle | The game's config archives are Oodle-compressed, so reading them needs the proprietary `oo2core_9_win64.dll`. The game does **not** ship it (Oodle is linked into the game executable), and **S2Tweaker never downloads it**: a program that pulls a library off the internet and then runs it looks exactly like a dropper, which is one reason scanners flag tools like this. The user places the file once; the tool looks in the usual local spots, always verifies the SHA-256, and says so at startup with a link and a target folder if it is missing. The bundled repak cannot fetch it either - it is built from source with the download function and its HTTP/TLS stack removed ([tools/build_repak.py](tools/build_repak.py)). Packing never needs Oodle. |
| Parsing | [cfgparse.py](s2tweaker/cfgparse.py) parses GSC's cfg text format (`Name : struct.begin {refkey=...}` … `struct.end`) into a tree; `refkey` inheritance chains are resolved to get effective vanilla values. |
| Patch output | [emit.py](s2tweaker/emit.py) writes `{bpatch}` structs. Patch files follow the proven convention `<BaseCfg>/<BaseCfg>_patch_<Mod>.cfg` under `Stalker2/Content/GameLite/GameData/`. |
| Packing | [pakio.py](s2tweaker/pakio.py) stages the files and calls the bundled `tools/repak.exe` (defaults are exactly what the game wants: V8B, mount `../../../`, uncompressed). |
| Key game files | `ObjPrototypes` (player + mutants), `ItemPrototypes`, `TradePrototypes`, `DifficultyPrototypes` (per-difficulty multiplier groups), `EffectPrototypes` (overweight effects), `FloatProviderPrototypes` (scope-sway constant — patched instead of the sway effects so offset-aiming keeps working), `WeaponData/*` (damage, wear, spread, recoil), `CoreVariables` (repair costs, stamina drain), `ObjWeightParamsPrototypes` (carry weight), `ObjHoldBreathParamsPrototypes`, `StashPrototypes` (smart loot in stashes and on bodies), `ItemGeneratorPrototypes` (9.3 MB — the world's loot generators; only `MinCount`/`MaxCount` under `PossibleItems` is scaled, and only on generators that pass a two-stage safety filter, see below), `RelationPrototypes` (faction relations: 582 pair baselines + the RelationVersion counter the patch raises so saves notice changes — research: [docs/FACTION_RELATIONS_RESEARCH.md](docs/FACTION_RELATIONS_RESEARCH.md)). |

Deep research notes with sources, vanilla values and risk analysis:
[docs/SPEC.md](docs/SPEC.md).

## The ~mods pre-scan

On request the tool scans the OTHER mods in the game's `~mods` folder (never
without asking — overhaul paks can be 2 GB) and tells the user in plain
language which of its own settings those mods also change. Affected sliders
keep a colored dot: blue while the slider sits at (vanilla) ("also changed by
X"), violet once the user moves it ("X changes this too — your value wins",
because the tool's `zzz_` pak loads last). "Reset all to vanilla" keeps the
dots — the foreign mods are still installed; only a re-scan updates them.

Mechanics ([modscan.py](s2tweaker/modscan.py)): per pak only the cfg entries
under `GameData`/`DLCGameData` are listed (recursively — UE5 mounts `~mods`
subfolders too, and players commonly sort their mods into subfolders) and
extracted in one
batched, glob-escaped `repak` call (`.cfg.bin` is converted; the official
`Base.cfg_patch_<Mod>` naming without a trailing `.cfg` counts as a config
too). Mods with an IoStore container next to the pak (`.utoc`/`.ucas` —
typical for Steam Workshop items) are scanned through their `.pak` part, which
is where UE5 keeps loose files such as cfg patches; only the packed assets stay
uninspected, and the result says so per mod. Duplicate Workshop layouts (old
and new path, same mod name) are merged into one entry. Each slider's "footprint" is
computed dynamically — `build_patches()` probed in BOTH directions (×2 and
×0.5, so capped values are covered) — and compared against the mod's content
on the level of (top-level struct + leaf key), deliberately not the full
path: foreign mods patch the same values through different file layouts.
Three refinements keep the matches honest: legacy `refkey` patches under a
free struct name are counted under their target prototype; full-file copies
are value-compared against vanilla so a 60 MB overhaul only marks what it
actually changes; and re-emitted anchor keys (`Type`) plus the ambiguous
nested `Weight` are excluded from the comparison. Expensive footprints (the
9.3 MB loot file, the 1,601-prototype no-heal walk) are only computed when a
scanned mod plausibly touches them. The scan runs in a worker thread against
a GameData snapshot; Browse/Reload are locked while it runs. If a foreign
pak sorts alphabetically AFTER the tool's `zzz_` pak, the tooltip and the
results dialog say so instead of claiming "your value wins".

## The loot-amount safety filter

`ItemGeneratorPrototypes.cfg` holds 3,085 loot generators, and the same field
names (`MinCount`/`MaxCount`) mean *stack size* under `PossibleItems` and
*coupons* under `MoneyGenerator`. There is no quest flag in that file at all,
so [gamedata.py](s2tweaker/gamedata.py) filters in two stages before anything
is patched (`loot_generators()`):

1. **By name**, on both the struct key *and* its SID: story/quest prefixes
   (`MQ`/`EQ`/`SQ`/`RSQ`/`ANCQ`), `Reward`, `Container`, `BP_`, `UAID_`,
   `Key`, `Safe`, `PDA`, `Icon`, `Boss`, `Player`, `Template`, `Trade` …
2. **By content**: every `ItemPrototypeSID` in the block is resolved against
   `ItemPrototypes.cfg`. If one of them is a quest item, matches the
   unique-weapon pattern `^Gun_[A-Z]`, or cannot be found there at all, the
   whole generator is dropped. Both quest markers count — `IsQuestItem` and
   `IsQuestItemPrototype`; 291 items carry only the second one, among them the
   note PDAs wired to `OnPlayerGetItemEvent`.

Two item kinds are skipped per *entry* instead, so the rest of an otherwise
ordinary generator still scales: **money cards** (identified live by their
pickup effect `EEffectType::AddMoney`, not by name — currency exists as a
regular item in `PossibleItems`, not just in the `MoneyGenerator` branch) and
items whose *name* matches the quest pattern without carrying a quest marker
(in practice the invisible `GuardQuestItem` marker on 31 guard generators).

Plus the structural exclusions: the base template `[0]` (1,773 generators
inherit from it) and the developer `All*` generators that already ship with
`MinCount = 900`. Trader stock is excluded as well, but carefully: the
transitive hull is taken only from generators `TradePrototypes.cfg` actually
references, while generators that merely carry "Trade" in their name are
excluded themselves without propagating — otherwise a single bartender drags
`GeneralNPC_Consumables_*` out with it, and those blocks supply the medicine
and food of 239 and 281 ordinary NPCs.

Stage 1 alone provably leaks quest keys and unique weapons, which is why both
stages are mandatory. Struct keys, slot keys and array indices are always read
from the file — 226 generators are keyed `[N]` rather than by their SID, and
724 slots are named (`Head`, `BodyArmor`, …) instead of indexed, so a
constructed path would create a new node instead of patching an existing one.

What survives on the current game data: **2,026 of 3,085 generators**, 3,310
scalable count entries, and at 200 % a patch of about 25,000 lines — by far
the largest file the tool produces. (`GamePass` is deliberately NOT a
blacklist token: the 17 `GamePass_Stash_*` tables are ordinary base-game
world stashes — 167 live containers on the main map, content-identical to
the `Stash_Cheap/Medium/Expensive` tables — and the content check plus the
money skip cover them fully.)

## Project structure

```
main.py                 entry point (also the PyInstaller entry)
s2tweaker/
  gui.py                customtkinter GUI (dark, English)
  tweaks.py             Settings dataclass + one builder per feature
  gamedata.py           extraction pipeline, parsing, inheritance resolution
  cfgparse.py           GSC cfg text parser
  emit.py               {bpatch} cfg writer
  pakio.py              repak wrapper (pack/unpack)
  game.py               game folder auto-detection (Steam/GOG/Xbox)
  vendor_bin2cfg.py     cfg.bin → cfg decoder (vendored, public domain)
tools/repak.exe         pak tool (MIT/Apache-2.0, by trumank)
docs/SPEC.md            research: every tweak's mechanism + sources
release/README.txt      end-user readme shipped with the exe
THIRD_PARTY_LICENSES.txt licences of the bundled components
test_generate.py        end-to-end dev test (builds a test pak)
build.bat               builds dist/S2Tweaker/ (exe + _internal)
```

## Building from source

```
pip install -r requirements.txt
python main.py          # run the GUI directly
build.bat               # or build dist/S2Tweaker/S2Tweaker.exe
```

`tools/repak.exe` is not the upstream release binary: `python tools/build_repak.py` rebuilds it from source (pinned tag) with the runtime Oodle download removed, so nothing in the shipped folder can fetch anything. The CI does this on every build.

The build is deliberately **`--onedir`, not `--onefile`**: a one-file
PyInstaller exe is a self-extracting archive that unpacks itself into
`%TEMP%` and runs from there, which antivirus ML heuristics read as
dropper behaviour — that got the release quarantined on Nexus Mods in
September 2026 and deleted by Windows Defender once. `--onedir` keeps the
launcher at ~3 MB with nothing embedded, and `--version-file` stamps
company/product/version into the exe (it had no version resource at all
before). The tool stays portable either way: settings, cache, presets and
output are created next to the exe.

Python 3.12+ recommended. For development, the GUI prefers a local
`vanilla/Stalker2/Content/GameLite/GameData/` folder if present (create it by
running the tool once and copying the contents of `cache/vanilla-*/`), else
it extracts from the game on "Confirm & load game data".
`python test_generate.py` builds a test pak with many tweaks active.

## Adding a new tweak (3 steps)

1. **[tweaks.py](s2tweaker/tweaks.py)** — add a field to `Settings`
   (default = vanilla), then write/extend a builder that emits a `{bpatch}`
   dict only when the value deviates (`_neq(...)`), using vanilla values read
   via `gd.resolve(...)`. Add a line to `summarize()`.
2. **[gamedata.py](s2tweaker/gamedata.py)** — if you need a GameData file that
   isn't extracted yet, add it to `NEEDED_FILES` and **bump `CACHE_SCHEMA`**
   (this invalidates old caches automatically).
3. **[gui.py](s2tweaker/gui.py)** — add a `self._slider(...)` /
   `self._check(...)` row in `_build_body()` and map it in `_collect()`.
   Two exceptions to that recipe: the per-weapon sliders (`IwWeaponRow`) and
   the per-ammo sliders (`IaAmmoRow`) are built directly as `SliderRow(...)`
   and are deliberately **not** registered in `self.sliders` — they live in
   `self.weapon_overrides` / `self.ammo_overrides`.

Golden rule: patch only what the user changed, compute from vanilla values of
the *installed* version, and never hardcode game numbers.

## Legal / contributor notes

- **Never commit or upload extracted game files** (`vanilla/`, `cache/`) —
  that content is copyrighted by GSC Game World. `.gitignore` covers this.
- Released builds are produced by GitHub Actions from this repository, not
  on a personal machine — see the
  [code signing policy](docs/CODE_SIGNING_POLICY.md) for who builds and
  approves a release, and for the two third-party binaries involved.
- Tool code is MIT (see [LICENSE](LICENSE)). Bundled: repak (MIT OR
  Apache-2.0), cfg.bin decoder based on public-domain code by
  joric/sdwvit/thexii. Their licence texts ship with the tool:
  [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt) in the source, and the
  repak MIT notice is also reprinted in `release/README.txt` (the file inside
  the player ZIP, since repak.exe is embedded in the exe).
- Known limits: DLC items aren't covered by the per-item weight slider;
  iron-sight sway is animation-driven (not cfg-tweakable); the in-game
  "Custom Rules" difficulty overlaps some multipliers (precedence untested).

## Credits

- [repak](https://github.com/trumank/repak) by trumank
- [bin2cfg](https://github.com/joric/stalker/wiki) by joric,
  [S2CfgToJSON](https://github.com/sdwvit/S2CfgToJSON) by sdwvit (+ thexii)
- The S.T.A.L.K.E.R. 2 modding community for documenting the `{bpatch}`
  system, and GSC Game World for the game.
