# Job localization loading follow-up

Audit date: 2026-09-11. Installed game data: 2.0.5. This is follow-up research for [Molkerr's 1.40.0 report in issue #9](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5639882302). The reporter says the added artifact effects work, but the isolated journal text still does not translate. This document records a repair candidate that was not verified in-game at the audit date.

## What the existing result establishes

Version 1.40.0 creates `Stalker2/Content/Localization/Game/<culture>/S2Tweaker_JobLocalization.locres`, a Compact-format sibling of the game's translation resource. Its aliases were verified against the installed text, but discovery of that extra filename was an explicit runtime uncertainty in [the original asset research](JOB_LOCALIZATION_ASSETS_RESEARCH.md).

The new report does not establish whether the game ignores the sibling filename, uses a different loading path for this namespace, rejects that format in its custom loader, or encounters another runtime condition. It establishes that the previous candidate must not be described as a confirmed translation fix. Native `Game.locres` replacement removes the unverified filename and format assumptions together; a successful game test would not, on its own, distinguish which assumption failed.

## Native loading evidence

The same installed `pakchunk0-Windows.pak` contains:

| Native file | Measured evidence |
| --- | --- |
| `Stalker2/Content/Localization/Game/Game.locmeta` | 190 bytes; metadata version 1; native culture `en`; explicitly stored native resource path `en/Game.locres`; 18 culture identities |
| `Stalker2/Content/Localization/Game/<culture>/Game.locres` | 18 files; all format 3; each has the namespace `ST_S2BaseGameLocalization` |
| `Stalker2/Config/DefaultGame.ini` | The game localization settings select `ST_S2BaseGameLocalization` and `%GAMEDIR%Content/Localization/Game`; see the original research for exact settings |

The metadata therefore directly names the native English file. The exact role of that metadata in Stalker 2's custom loader remains unobserved. No game process was started or modified for this audit. The proposed output uses each existing resource's exact virtual path and keeps `Game.locmeta`, all ini files, journal SIDs, and stage SIDs unchanged.

Epic identifies format 3 as `Optimized_CityHash64_UTF16`, with precomputed identity hashes and string-pool reference counts. This agrees with all 18 installed files. [Epic's format enum](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Core/FTextLocalizationResourceVersion/ELocResVersion).

## Hash algorithm: verified against the native files

The new identity hash is calculated from UTF-16LE bytes without the terminating NUL:

1. Calculate `h = CityHash64(bytes)`.
2. Calculate `(low32(h) + high32(h) * 23) modulo 2^32`.
3. The empty identity has hash zero.

This is the formula implemented by [UnrealLocres' writer](https://github.com/akintos/UnrealLocres/blob/master/LocresLib/LocresFile.cs). A private Python implementation was adapted from [Google's CityHash64 reference](https://github.com/google/cityhash/blob/master/src/city.cc), rather than using CRC32 or truncating the 64-bit result. Google's implementation is MIT licensed; its complete notice is retained in the private script. A production adaptation must retain the same notice, including in source distributions. [Google's license](https://github.com/google/cityhash/blob/master/COPYING).

The formula was checked against **all 898,875 serialized native key hashes across the 18 resources**, plus every serialized namespace hash. There were zero mismatches. The distinct native key set contains 82,857 keys, spanning 26–234 UTF-16LE bytes in English; the 208 generated aliases and the namespace were also calculated. Hash checking uses a local memoization cache for repeated identities across cultures. This validates the concrete algorithm against the installed files; it does not infer the hash from the name of the format alone.

## Minimal native-format append

The private candidate does not reconstruct or normalize the game's translated strings. It parses the full resource strictly and then performs these bounded edits:

1. Resolve the same 208 new-to-original identities from the live journal repair: 69 titles and 139 stages. No new description aliases are needed.
2. Append each alias record to the existing namespace, using the new identity's verified hash, the original record's source hash, and **the original record's existing pool index**.
3. Increase that namespace's entry count and the header's total count by 208.
4. Advance the pool-offset field by the inserted record bytes.
5. Increase the reference count of each reused pool slot by exactly the number of new aliases pointing to it.

Every original key record remains byte-for-byte intact. Every original pool string, including its length, byte/UTF-16 representation and terminator, remains byte-for-byte intact. Pool order, size and all original indices are unchanged. Other namespaces, if present, must also be preserved. The live originals currently have zero source hashes, but the append operation copies their actual values instead of manufacturing a new source hash.

Strict validation must reject unsupported formats, duplicate aliases, missing originals, invalid pool indices, inconsistent counts, or a source Pak changed since the loaded game data. The export is optional and must remain empty when the multiple-jobs option is disabled. Existing version-1 alias caches cannot satisfy the new output: use a new optional-cache version/identity and an atomic cache replacement. No translated game text or generated native resource belongs in application/source archives.

## All installed cultures: measured result

Cultures were discovered from the live Pak directory index, without a two-language allowlist. A synthetic two-culture fixture is sufficient for individual unit-test cases but must never limit production discovery.

Each output adds exactly **13,357 bytes**, **208 entries**, and **zero pool strings**. All rows below passed native hash verification, strict readback, unchanged original-record checks, unchanged pool-string checks, and exact inverse reconstruction of the source bytes.

| Culture | Original entries | Output entries | Original bytes | Output bytes | Preserved pool strings |
| --- | ---: | ---: | ---: | ---: | ---: |
| ar | 47,528 | 47,736 | 8,533,827 | 8,547,184 | 39,728 |
| cs | 47,528 | 47,736 | 8,842,536 | 8,855,893 | 39,664 |
| de | 47,526 | 47,734 | 9,414,852 | 9,428,209 | 39,798 |
| en | 82,857 | 83,065 | 10,309,460 | 10,322,817 | 42,055 |
| es-419 | 47,528 | 47,736 | 9,323,041 | 9,336,398 | 39,610 |
| es | 47,512 | 47,720 | 9,308,698 | 9,322,055 | 39,754 |
| fr | 47,529 | 47,737 | 9,843,918 | 9,857,275 | 39,946 |
| it | 47,528 | 47,736 | 8,541,140 | 8,554,497 | 39,835 |
| ja | 47,549 | 47,757 | 6,421,836 | 6,435,193 | 40,071 |
| ko | 47,660 | 47,868 | 6,694,002 | 6,707,359 | 40,271 |
| pl | 47,541 | 47,749 | 9,196,923 | 9,210,280 | 39,505 |
| pt-BR | 47,530 | 47,738 | 9,290,392 | 9,303,749 | 40,119 |
| ru | 54,250 | 54,458 | 9,891,537 | 9,904,894 | 46,825 |
| sr | 47,584 | 47,792 | 8,576,096 | 8,589,453 | 40,439 |
| tr | 47,522 | 47,730 | 8,781,508 | 8,794,865 | 39,566 |
| uk | 48,623 | 48,831 | 8,920,088 | 8,933,445 | 42,258 |
| zh-Hans | 47,544 | 47,752 | 5,687,031 | 5,700,388 | 40,190 |
| zh-Hant | 47,536 | 47,744 | 5,796,838 | 5,810,195 | 39,819 |

Resource totals: **153,373,723 original bytes → 153,614,149 output bytes**; all 898,875 original entries preserved and 3,744 aliases added. The all-language uncompressed localization-only Pak is **153,617,285 bytes** (approximately 146.5 MiB). Its private ZIP is **38,402,360 bytes**. The larger Pak is required because a virtual `Game.locres` override replaces the file as a whole; it is not a record-level merge.

The private audit, including extraction, repeated strict parsing, all native hash checks, semantic checks, byte-preservation checks, and inverse reconstruction, took **20.518 seconds** to generate the resources on this machine. Building and rereading the Pak, followed by maximum ZIP compression, brought total audit time to **42.816 seconds**. These are measured audit timings, not promised export times or a benchmark of optimized production caching.

Private artifacts are confined to ignored `out/issue9_140_followup/localization_research/`:

- `cityhash_probe.py` and `cityhash_report.json` record the initial independent hash check.
- `native_append_probe.py` and `native_append_report.json` record the complete live-culture audit.
- `S2Tweaker_NativeJobLocalization_PRIVATE_P.pak` has SHA-256 `e032bb8c2b062b9f725fdb0f6b704da00a783f6abb5d881f3ba519824fefdec7`.
- The Pak was reopened; all 18 virtual paths and all resource payloads matched exactly. It has not been installed, uploaded or published.

## Costs, conflicts, and remaining game checks

**Whole-file localization conflicts are the main tradeoff.** Another translation mod that replaces the same `Game.locres` path cannot automatically merge with this Pak. Whichever resource wins the game's Pak priority supplies that complete culture file. Building from unmodified installed game data preserves GSC's current text, but does not preserve another mod's changes. A mod scan that only examines cfg patches must not claim it detects this conflict; inspect native localization paths separately or communicate the limitation clearly.

The generated resources must be rebuilt after game updates. The native target path is a more defensible loading candidate than a new sibling filename, but visible journal rendering still needs a game test. Test Russian, which the reporter uses, and native English separately; the implementation and export must include every installed culture regardless of those initial test languages.

For a controlled test, keep the 1.40.0 job graph and its isolated IDs unchanged, add the native-path translation candidate, and avoid another translation replacement mod. Check a missing isolated title and stage that appear in the reporter's footage, then check ordinary quests/menu text for regressions. Do not combine this translation test with a speculative marker or stage-identity change. Retest journal persistence and return-to-giver behavior, but do not attribute a marker result to localization alone.

**Conclusion:** A live-generated, byte-preserving version-3 replacement for every installed `Game.locres` is technically feasible and locally validated. Its loading and rendering remain experimental until confirmed by an in-game test. It increases generated Pak size and introduces an explicit whole-file translation-mod conflict.
