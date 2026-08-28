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

41 tweaks: health/stamina/regen, per-action stamina costs, fall damage,
movement speed, jump height, carry weight + penalty threshold, item weights
per category, player/NPC/mutant damage & health, headshots, explosions,
durability, jamming, spread, recoil, scoped sway, breath hold, anomaly/
radiation/bleeding, hunger/sleep rates, trader prices & min. durability,
repair/upgrade costs, quest rewards.

## How it works (the important mechanics)

| Layer | Details |
|---|---|
| Vanilla data | `repak unpack` of `pakchunk0-Windows.pak` (only ~10 needed GameData files), then `.cfg.bin` → text via the vendored decoder ([s2tweaker/vendor_bin2cfg.py](s2tweaker/vendor_bin2cfg.py)). Cached in `cache/vanilla-<pakSize>-s<schema>/`; a game update changes the fingerprint → automatic re-extraction. |
| Parsing | [cfgparse.py](s2tweaker/cfgparse.py) parses GSC's cfg text format (`Name : struct.begin {refkey=...}` … `struct.end`) into a tree; `refkey` inheritance chains are resolved to get effective vanilla values. |
| Patch output | [emit.py](s2tweaker/emit.py) writes `{bpatch}` structs. Patch files follow the proven convention `<BaseCfg>/<BaseCfg>_patch_<Mod>.cfg` under `Stalker2/Content/GameLite/GameData/`. |
| Packing | [pakio.py](s2tweaker/pakio.py) stages the files and calls the bundled `tools/repak.exe` (defaults are exactly what the game wants: V8B, mount `../../../`, uncompressed). |
| Key game files | `ObjPrototypes` (player + mutants), `ItemPrototypes`, `TradePrototypes`, `DifficultyPrototypes` (per-difficulty multiplier groups), `EffectPrototypes` (overweight/sway effects), `WeaponData/*` (damage, wear, spread, recoil), `CoreVariables` (repair costs, stamina drain), `ObjWeightParamsPrototypes` (carry weight), `ObjHoldBreathParamsPrototypes`. |

Deep research notes with sources, vanilla values and risk analysis:
[docs/SPEC.md](docs/SPEC.md).

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
test_generate.py        end-to-end dev test (builds a test pak)
build.bat               builds dist/S2Tweaker.exe
```

## Building from source

```
pip install -r requirements.txt
python main.py          # run the GUI directly
build.bat               # or build dist/S2Tweaker.exe
```

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

Golden rule: patch only what the user changed, compute from vanilla values of
the *installed* version, and never hardcode game numbers.

## Legal / contributor notes

- **Never commit or upload extracted game files** (`vanilla/`, `cache/`) —
  that content is copyrighted by GSC Game World. `.gitignore` covers this.
- Tool code is MIT (see [LICENSE](LICENSE)). Bundled: repak (MIT/Apache-2.0),
  cfg.bin decoder based on public-domain code by joric/sdwvit/thexii.
- Known limits: DLC items aren't covered by the per-item weight slider;
  iron-sight sway is animation-driven (not cfg-tweakable); the in-game
  "Custom Rules" difficulty overlaps some multipliers (precedence untested).

## Credits

- [repak](https://github.com/trumank/repak) by trumank
- [bin2cfg](https://github.com/joric/stalker/wiki) by joric,
  [S2CfgToJSON](https://github.com/sdwvit/S2CfgToJSON) by sdwvit (+ thexii)
- The S.T.A.L.K.E.R. 2 modding community for documenting the `{bpatch}`
  system, and GSC Game World for the game.
