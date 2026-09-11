# Repeatable-job localization asset research

Audit date: 2026-09-11. Installed game data: 2.0.5. Research only; no game files were modified and no game process was launched. The private localization-only Pak described below is a serialization probe, not a verified repair.

## Finding

The original journal localization lives in compiled `.locres` resources, under namespace `ST_S2BaseGameLocalization`. The current isolated journals introduce new journal/stage SIDs without corresponding localization entries. Retaining a stage's `Description` field does not establish that the renderer uses that field to choose its text.

The reporter-supplied test video, reviewed separately in the same investigation, shows `S2T_Job_RSQ04_C02` as the title and `sid_journal_stage_S2T_Job_RSQ04_C02_RSQ04_C02_Start` as its missing stage label. Its Russian journal description is already translated. Therefore the candidate adds title/stage aliases only; it must preserve the existing `Descriptions` array and must not rewrite description localization.

## Local sources and inventory


| Source | Measured scope |
| --- | --- |
| `vanilla/Stalker2/Content/GameLite/GameData/JournalQuestPrototypes.cfg` | 10065 lines; 199 top-level structs |
| Installed `Stalker2/Content/Paks/*.pak` | 41 Pak directory indexes; localization paths occur in pakchunk0 |
| `pakchunk0-Windows.pak` | 5,170 entries; 80 localization-related paths; 71 .locres resources |
| `Stalker2/Content/Localization/Game/Game.locmeta` | 190 bytes; native culture en; 18 culture identities |
| `Stalker2/Content/Localization/Game/<culture>/Game.locres` | 18 resources; all version 3; exactly one namespace each |
| `Stalker2/Config/DefaultGame.ini` | Localization configuration at lines 426–457 |
| `Stalker2/AssetRegistry.bin` and 42 `.utoc` indexes (including global) | Read-only identity search; no extracted cooked assets |


No translated game text is included in this document or in production source. Raw inspection data and all generated translations are confined to ignored `out/molkerr_reply_review/localization_assets/`.

The complete game localization inventory is:


| Culture | Resource bytes | Entries | LUT strings | Required originals present |
| --- | --- | --- | --- | --- |
| ar | 8533827 | 47528 | 39728 | 94/94 |
| cs | 8842536 | 47528 | 39664 | 94/94 |
| de | 9414852 | 47526 | 39798 | 94/94 |
| en | 10309460 | 82857 | 42055 | 94/94 |
| es-419 | 9323041 | 47528 | 39610 | 94/94 |
| es | 9308698 | 47512 | 39754 | 94/94 |
| fr | 9843918 | 47529 | 39946 | 94/94 |
| it | 8541140 | 47528 | 39835 | 94/94 |
| ja | 6421836 | 47549 | 40071 | 94/94 |
| ko | 6694002 | 47660 | 40271 | 94/94 |
| pl | 9196923 | 47541 | 39505 | 94/94 |
| pt-BR | 9290392 | 47530 | 40119 | 94/94 |
| ru | 9891537 | 54250 | 46825 | 94/94 |
| sr | 8576096 | 47584 | 40439 | 94/94 |
| tr | 8781508 | 47522 | 39566 | 94/94 |
| uk | 8920088 | 48623 | 42258 | 94/94 |
| zh-Hans | 5687031 | 47544 | 40190 | 94/94 |
| zh-Hant | 5796838 | 47536 | 39819 | 94/94 |


Every culture contains all 94 original title/description/stage identities examined. Their source-string hashes are all zero and all 94 translations are nonempty. None contains a generated `S2T_Job_` key. The alias-only candidate needs 86 of these originals: eight titles and 78 distinct stage identities; the eight description identities remain untouched.

## Exact key format and cfg relationship

| Purpose | Original identity | Relevant live cfg |
| --- | --- | --- |
| Journal title | `sid_journal_RSQ01_Name` | `RSQ01.SID = RSQ01`; the original has no explicit Name |
| Journal description | `sid_journal_description_RSQ01_Description_0` | `RSQ01.Descriptions.[0] = RSQ01_Description_0` |
| Stage label | `sid_journal_stage_RSQ01_C01_Start` | `RSQ01.Stages.RSQ01_C01_Start.SID = RSQ01_C01_Start` |
| Stage Description metadata | No corresponding key ending `_Description` in the observed stage lookup | `RSQ01.Stages.RSQ01_C01_Start.Description = RSQ01_C01_Start_Description` |

The observed missing stage key uses its SID, including our generated prefix. This is evidence against repairing that stage by merely retaining or changing its Description field. The title fallback displays the journal SID; the candidate uses the title-key pattern measured for every original journal.

All eight source journals and generated identity counts:


| Original journal | Isolated journals | Stage aliases |
| --- | --- | --- |
| RSQ01 | 6 | 13 |
| RSQ04 | 10 | 20 |
| RSQ05 | 8 | 16 |
| RSQ06 | 9 | 18 |
| RSQ07 | 9 | 18 |
| RSQ08 | 9 | 18 |
| RSQ09 | 9 | 18 |
| RSQ10 | 9 | 18 |


All source metadata is resolved from the live journal and quest graph. The original descriptions already work in the supplied video, so adding the initially considered 69 description aliases would be unnecessary.

## Namespace loading and the StringTable question

The installed `DefaultGame.ini` contains these settings under `[/Script/Stalker2.GameLocalizationSettings]`:

- `LocalizationNamespaces` includes `ST_S2BaseGameLocalization`, `ST_S2DLC1Localization`, and `ST_S2TestLocalization`.
- `DefaultLocalizationNamespace = ST_S2BaseGameLocalization`.
- `DefaultLocalizationPath = %GAMEDIR%Content/Localization/Game`.
- `SIDMaskToLocalizationNamespace` maps the `DLC01_` prefix to the DLC namespace.
- The Internationalization section separately adds the S2_Test and S2_DLC1 localization directories.

The `ST_` prefix alone does not prove a cooked StringTable asset is required. Searches for `S2BaseGameLocalization`, `StringTable`, `LocalizationDatabase`, and `LocalizationManager` found no such identity in the base AssetRegistry. Searches of all 42 installed .utoc files likewise found no matching `S2BaseGameLocalization`, `StringTable`, or `LocalizationDatabase` bytes. This is a bounded metadata search, not a complete cooked-asset parser or proof of absence. No StringTable asset path was established.

The custom game localization namespace/path configuration, zero source-string hashes, and measured locres keys support a direct localization-resource route. Runtime source lookup and missing-key behavior are not established solely by this evidence.

Epic documents an engine API that loads all locres files in a directory. A sibling resource in each existing culture directory is therefore the smallest candidate that avoids replacing the entire game translation file. This is an inference about the candidate design, not proof that Stalker 2 calls that API for every culture. Native English loading may follow a different path from other cultures and needs its own check. [Epic: FTextLocalizationResource](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Core/FTextLocalizationResource).

## Verified binary formats

All 18 Game resources use format 3. It contains magic, version, string-pool offset, total entry count, namespace/key identities with precomputed hashes, source-string hashes, string-pool indices, and a string pool with reference counts. The private reader consumes every file exactly, checks all indices, and reconciles all reference counts.

Epic's enum identifies version 3 as `Optimized_CityHash64_UTF16`, version 2 as `Optimized_CRC32`, version 1 as `Compact`, and version 0 as `Legacy`. The version-3 key hash must not be guessed using CRC32. [Epic: ELocResVersion](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Core/FTextLocalizationResourceVersion/ELocResVersion).

The same installed pakchunk0 ships 39 version-1 Compact resources and 32 version-3 resources in total. The 39 Compact files belong to the OnlineSubsystem, OnlineSubsystemSteam and OnlineSubsystemUtils localization targets. They demonstrate the older format is still part of this installation.

The Compact layout measured on all 39 files is:

1. 16-byte magic, one-byte version 1, signed 64-bit string-pool offset.
2. Namespace count, each namespace FString and its entry count.
3. Each entry: key FString, uint32 source-string hash, int32 pool index.
4. Pool count followed by FStrings, without reference-count integers.

There are no precomputed namespace/key hashes in Compact. FString length/sign distinguishes byte strings from UTF-16LE and includes the terminator. The research reader/writer preserves that representation. Every one of the 39 installed Compact files roundtrips byte for byte through that reader/writer, independently of the new alias outputs.

Epic also documents string serialization and a path that discards serialized hashes when upgrading an older hashing algorithm; these APIs explain why guessing a current hash should be avoided. [Epic: FTextKey](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Core/FTextKey?application_version=5.5).

## Private candidate and verification

`out/molkerr_reply_review/localization_assets/compact_alias_probe.py` derives the original journal for each generated journal from the live giver/container/quest graph and calls the actual `build_job_isolation`. It generates 208 aliases per culture: 69 titles and 139 stages. Titles reuse the corresponding original giver-journal title. Stages reuse their exact original stage translation. These are new localization keys pointing to copied live translations, not a translation list shipped in tool source.

The candidate emits only:

`Stalker2/Content/Localization/Game/<culture>/S2Tweaker_JobLocalization.locres`

It does not overwrite `Game.locres`, `Game.locmeta`, ini files, journal cfg files, or any other asset. It is supplemental to the existing isolated-job Pak and does not contain the job-graph repair itself.

Validation performed:

- 39 existing version-1 resources reconstructed byte for byte.
- 18 generated Compact resources strictly reparsed, with exactly 208 entries each.
- All 3,744 generated entries resolve to the same live translation and source hash as the intended original for their culture.
- Original keys and translations were not emitted as replacement entries.
- No description aliases were emitted.
- The private 18-entry Pak was reopened; every payload matches its generated resource byte for byte.


| Private artifact | Bytes | SHA-256 |
| --- | --- | --- |
| S2Tweaker_JobLocalization_PRIVATE_CANDIDATE_P.pak | 382952 | 5d5138df1ab3af63ffcdbac8a2ba5dafa7959afce4096ecf9df5f771bbc1766b |


Per-culture candidate sizes and identities are recorded in the ignored `compact_candidate_report.json`. The candidate has not been installed, uploaded, released, or tested in the game.

## Remaining runtime checks and boundaries

- Confirm the engine discovers `S2Tweaker_JobLocalization.locres` beside the existing Game.locres files.
- Check both native English and a non-native culture; the supplied Russian report provides a useful baseline.
- Confirm the projected title-key pattern resolves, not just the observed stage pattern.
- Confirm changing only localization leaves job objectives, turn-in, rewards, and journal isolation behavior unchanged.
- Reusing original stage SIDs inside isolated journals might reduce required aliases, but this audit does not establish the runtime scope of those SIDs. Do not change stage identity semantics based on localization evidence alone.
- Do not replace whole Game.locres files as the first approach: doing so broadens conflicts and risks hiding translations from other mods.
- Do not add new cfg fields such as a guessed localization SID or namespace override without evidence the game supports them.
- Do not bundle copied game translations in a release/source archive. If integrated later, read only the needed translations from the user's current installation at export time.

The candidate is a measured, reversible experiment. File discovery and visible localized journal rendering still require an in-game result before this can be described as fixed.

## Complete alias identity map

All entries use namespace `ST_S2BaseGameLocalization` and preserve source hash `0` in the inspected game version. These are identifiers only; no translated text is reproduced.


| New alias | Live original |
| --- | --- |
| `sid_journal_S2T_Job_RSQ01_C01_Name` | `sid_journal_RSQ01_Name` |
| `sid_journal_S2T_Job_RSQ01_C02_Name` | `sid_journal_RSQ01_Name` |
| `sid_journal_S2T_Job_RSQ01_C03_Name` | `sid_journal_RSQ01_Name` |
| `sid_journal_S2T_Job_RSQ01_C04_Name` | `sid_journal_RSQ01_Name` |
| `sid_journal_S2T_Job_RSQ01_C05_Name` | `sid_journal_RSQ01_Name` |
| `sid_journal_S2T_Job_RSQ01_C06_Name` | `sid_journal_RSQ01_Name` |
| `sid_journal_S2T_Job_RSQ04_C01_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C02_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C03_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C04_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C05_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C06_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C07_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C08_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C09_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ04_C10_Name` | `sid_journal_RSQ04_Name` |
| `sid_journal_S2T_Job_RSQ05_C01_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C02_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C04_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C05_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C07_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C08_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C09_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ05_C10_Name` | `sid_journal_RSQ05_Name` |
| `sid_journal_S2T_Job_RSQ06_C01___K_Z_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C02___K_M_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C03___K_B_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C04___K_S_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C05___B_B_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C06___B_A_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C07___B_A_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C08___B_A_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ06_C09___S_P_Name` | `sid_journal_RSQ06_Name` |
| `sid_journal_S2T_Job_RSQ07_C01_K_Z_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C02_K_M_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C03_K_M_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C04_K_B_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C05_B_B_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C06_B_A_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C07_B_A_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C08_B_A_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ07_C09_S_P_Name` | `sid_journal_RSQ07_Name` |
| `sid_journal_S2T_Job_RSQ08_C01_K_M_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C02_K_B_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C03_K_S_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C04_B_B_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C05_B_B_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C06_B_A_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C07_B_A_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C08_B_A_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ08_C09_S_P_Name` | `sid_journal_RSQ08_Name` |
| `sid_journal_S2T_Job_RSQ09_C01_K_M_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C02_K_M_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C03_K_M_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C04_K_S_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C05_B_B_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C06_B_A_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C07_B_A_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C08_B_A_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ09_C09_S_P_Name` | `sid_journal_RSQ09_Name` |
| `sid_journal_S2T_Job_RSQ10_C01_K_M_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C02_K_M_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C03_K_S_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C04_K_S_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C05_B_B_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C06_B_A_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C07_B_A_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C08_B_A_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_S2T_Job_RSQ10_C09_S_P_Name` | `sid_journal_RSQ10_Name` |
| `sid_journal_stage_S2T_Job_RSQ01_C01_RSQ01_C01_Start` | `sid_journal_stage_RSQ01_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ01_C01_RSQ01_Finish` | `sid_journal_stage_RSQ01_Finish` |
| `sid_journal_stage_S2T_Job_RSQ01_C02_RSQ01_C02_Start` | `sid_journal_stage_RSQ01_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ01_C02_RSQ01_Finish` | `sid_journal_stage_RSQ01_Finish` |
| `sid_journal_stage_S2T_Job_RSQ01_C03_RSQ01_C03_Start` | `sid_journal_stage_RSQ01_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ01_C03_RSQ01_Finish` | `sid_journal_stage_RSQ01_Finish` |
| `sid_journal_stage_S2T_Job_RSQ01_C04_RSQ01_C04_Start` | `sid_journal_stage_RSQ01_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ01_C04_RSQ01_Finish` | `sid_journal_stage_RSQ01_Finish` |
| `sid_journal_stage_S2T_Job_RSQ01_C05_RSQ01_C05_Start` | `sid_journal_stage_RSQ01_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ01_C05_RSQ01_Finish` | `sid_journal_stage_RSQ01_Finish` |
| `sid_journal_stage_S2T_Job_RSQ01_C06_RSQ01_C06_Loot` | `sid_journal_stage_RSQ01_C06_Loot` |
| `sid_journal_stage_S2T_Job_RSQ01_C06_RSQ01_C06_Start` | `sid_journal_stage_RSQ01_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ01_C06_RSQ01_Finish` | `sid_journal_stage_RSQ01_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C01_RSQ04_C01_Start` | `sid_journal_stage_RSQ04_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C01_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C02_RSQ04_C02_Start` | `sid_journal_stage_RSQ04_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C02_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C03_RSQ04_C03_Start` | `sid_journal_stage_RSQ04_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C03_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C04_RSQ04_C04_Start` | `sid_journal_stage_RSQ04_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C04_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C05_RSQ04_C05_Start` | `sid_journal_stage_RSQ04_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C05_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C06_RSQ04_C06_Start` | `sid_journal_stage_RSQ04_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C06_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C07_RSQ04_C07_Start` | `sid_journal_stage_RSQ04_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C07_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C08_RSQ04_C08_Start` | `sid_journal_stage_RSQ04_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C08_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C09_RSQ04_C09_Start` | `sid_journal_stage_RSQ04_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C09_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ04_C10_RSQ04_C10_Start` | `sid_journal_stage_RSQ04_C10_Start` |
| `sid_journal_stage_S2T_Job_RSQ04_C10_RSQ04_Finish` | `sid_journal_stage_RSQ04_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C01_RSQ05_C01_Start` | `sid_journal_stage_RSQ05_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C01_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C02_RSQ05_C02_Start` | `sid_journal_stage_RSQ05_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C02_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C04_RSQ05_C04_Start` | `sid_journal_stage_RSQ05_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C04_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C05_RSQ05_C05_Start` | `sid_journal_stage_RSQ05_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C05_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C07_RSQ05_C07_Start` | `sid_journal_stage_RSQ05_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C07_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C08_RSQ05_C08_Start` | `sid_journal_stage_RSQ05_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C08_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C09_RSQ05_C09_Start` | `sid_journal_stage_RSQ05_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C09_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ05_C10_RSQ05_C10_Start` | `sid_journal_stage_RSQ05_C10_Start` |
| `sid_journal_stage_S2T_Job_RSQ05_C10_RSQ05_Finish` | `sid_journal_stage_RSQ05_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C01___K_Z_RSQ06_C01_Start` | `sid_journal_stage_RSQ06_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C01___K_Z_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C02___K_M_RSQ06_C02_Start` | `sid_journal_stage_RSQ06_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C02___K_M_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C03___K_B_RSQ06_C03_Start` | `sid_journal_stage_RSQ06_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C03___K_B_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C04___K_S_RSQ06_C04_Start` | `sid_journal_stage_RSQ06_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C04___K_S_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C05___B_B_RSQ06_C05_Start` | `sid_journal_stage_RSQ06_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C05___B_B_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C06___B_A_RSQ06_C06_Start` | `sid_journal_stage_RSQ06_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C06___B_A_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C07___B_A_RSQ06_C07_Start` | `sid_journal_stage_RSQ06_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C07___B_A_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C08___B_A_RSQ06_C08_Start` | `sid_journal_stage_RSQ06_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C08___B_A_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ06_C09___S_P_RSQ06_C09_Start` | `sid_journal_stage_RSQ06_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ06_C09___S_P_RSQ06_Finish` | `sid_journal_stage_RSQ06_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C01_K_Z_RSQ07_C01_Start` | `sid_journal_stage_RSQ07_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C01_K_Z_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C02_K_M_RSQ07_C02_Start` | `sid_journal_stage_RSQ07_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C02_K_M_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C03_K_M_RSQ07_C03_Start` | `sid_journal_stage_RSQ07_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C03_K_M_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C04_K_B_RSQ07_C04_Start` | `sid_journal_stage_RSQ07_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C04_K_B_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C05_B_B_RSQ07_C05_Start` | `sid_journal_stage_RSQ07_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C05_B_B_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C06_B_A_RSQ07_C06_Start` | `sid_journal_stage_RSQ07_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C06_B_A_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C07_B_A_RSQ07_C07_Start` | `sid_journal_stage_RSQ07_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C07_B_A_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C08_B_A_RSQ07_C08_Start` | `sid_journal_stage_RSQ07_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C08_B_A_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ07_C09_S_P_RSQ07_C09_Start` | `sid_journal_stage_RSQ07_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ07_C09_S_P_RSQ07_Finish` | `sid_journal_stage_RSQ07_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C01_K_M_RSQ08_C01_Start` | `sid_journal_stage_RSQ08_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C01_K_M_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C02_K_B_RSQ08_C02_Start` | `sid_journal_stage_RSQ08_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C02_K_B_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C03_K_S_RSQ08_C03_Start` | `sid_journal_stage_RSQ08_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C03_K_S_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C04_B_B_RSQ08_C04_Start` | `sid_journal_stage_RSQ08_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C04_B_B_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C05_B_B_RSQ08_C05_Start` | `sid_journal_stage_RSQ08_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C05_B_B_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C06_B_A_RSQ08_C06_Start` | `sid_journal_stage_RSQ08_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C06_B_A_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C07_B_A_RSQ08_C07_Start` | `sid_journal_stage_RSQ08_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C07_B_A_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C08_B_A_RSQ08_C08_Start` | `sid_journal_stage_RSQ08_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C08_B_A_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ08_C09_S_P_RSQ08_C09_Start` | `sid_journal_stage_RSQ08_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ08_C09_S_P_RSQ08_Finish` | `sid_journal_stage_RSQ08_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C01_K_M_RSQ09_C01_Start` | `sid_journal_stage_RSQ09_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C01_K_M_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C02_K_M_RSQ09_C02_Start` | `sid_journal_stage_RSQ09_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C02_K_M_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C03_K_M_RSQ09_C03_Start` | `sid_journal_stage_RSQ09_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C03_K_M_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C04_K_S_RSQ09_C04_Start` | `sid_journal_stage_RSQ09_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C04_K_S_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C05_B_B_RSQ09_C05_Start` | `sid_journal_stage_RSQ09_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C05_B_B_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C06_B_A_RSQ09_C06_Start` | `sid_journal_stage_RSQ09_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C06_B_A_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C07_B_A_RSQ09_C07_Start` | `sid_journal_stage_RSQ09_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C07_B_A_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C08_B_A_RSQ09_C08_Start` | `sid_journal_stage_RSQ09_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C08_B_A_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ09_C09_S_P_RSQ09_C09_Start` | `sid_journal_stage_RSQ09_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ09_C09_S_P_RSQ09_Finish` | `sid_journal_stage_RSQ09_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C01_K_M_RSQ10_C01_Start` | `sid_journal_stage_RSQ10_C01_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C01_K_M_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C02_K_M_RSQ10_C02_Start` | `sid_journal_stage_RSQ10_C02_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C02_K_M_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C03_K_S_RSQ10_C03_Start` | `sid_journal_stage_RSQ10_C03_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C03_K_S_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C04_K_S_RSQ10_C04_Start` | `sid_journal_stage_RSQ10_C04_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C04_K_S_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C05_B_B_RSQ10_C05_Start` | `sid_journal_stage_RSQ10_C05_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C05_B_B_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C06_B_A_RSQ10_C06_Start` | `sid_journal_stage_RSQ10_C06_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C06_B_A_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C07_B_A_RSQ10_C07_Start` | `sid_journal_stage_RSQ10_C07_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C07_B_A_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C08_B_A_RSQ10_C08_Start` | `sid_journal_stage_RSQ10_C08_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C08_B_A_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
| `sid_journal_stage_S2T_Job_RSQ10_C09_S_P_RSQ10_C09_Start` | `sid_journal_stage_RSQ10_C09_Start` |
| `sid_journal_stage_S2T_Job_RSQ10_C09_S_P_RSQ10_Finish` | `sid_journal_stage_RSQ10_Finish` |
