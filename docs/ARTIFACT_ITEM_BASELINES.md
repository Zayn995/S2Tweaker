# Artifact item inventory (game-data audit, 2026-09-11)

[Research overview and implementation priorities](ARTIFACT_EDITOR_RESEARCH.md)

Research only. Static config proves field availability and references; no in-game behavior is verified by this audit. Values must be resolved live if implemented.

## Sources

| File | Lines | Top-level structs | Explicit artifact Type |
| --- | --- | --- | --- |
| vanilla/Stalker2/Content/GameLite/GameData/ItemPrototypes.cfg | 92232 | 1375 | 153 |
| vanilla/Stalker2/Content/GameLite/DLCGameData/Deluxe/ItemPrototypes.cfg | 1092 | 11 | 0 |
| vanilla/Stalker2/Content/GameLite/DLCGameData/PreOrder/ItemPrototypes.cfg | 435 | 4 | 0 |
| vanilla/Stalker2/Content/GameLite/DLCGameData/Ultimate/ItemPrototypes.cfg | 732 | 7 | 0 |

## Counts

Selected 154 structs by `GameData.item_category == artifact` or effective `Type == EItemType::Artifact`. Grouping: `{'template': 2, 'ordinary-candidate': 69, 'fake': 71, 'special-psy-candidate': 1, 'quest-or-prologue': 5, 'archiartifact': 6}`. Effective item types: `{'EItemType::Artifact': 153, 'EItemType::Info': 1}`.

## Complete item scalar baselines

The table covers every selected struct. Monetary values are raw `Cost`, not guaranteed shop sell or buy prices. Weight is the raw config field, not a promised dynamic carried weight. LocalizationSID is a key, not a verified visible translation.

| SID | Line | Group | Refkey | Weight | Cost | Rarity | ArtifactType | LocalizationSID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TemplateArtifact | 15132 | template | [0] | 0.5 | 0.0 | EArtifactRarity::Common | EArtifactType::None | — |
| EArtifactFlash | 15213 | ordinary-candidate | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactFlash_Fake | 15301 | fake | EArtifactFlash | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactFlash |
| EArtifactSoul | 15390 | ordinary-candidate | TemplateArtifact | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Electro | — |
| EArtifactSoul_Fake | 15478 | fake | EArtifactSoul | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | EArtifactSoul |
| EArtifactSnowflake | 15572 | ordinary-candidate | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactSnowflake_Fake | 15660 | fake | EArtifactSnowflake | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactSnowflake |
| GArtifactNightStar | 15754 | ordinary-candidate | TemplateArtifact | 0.6 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Gravity | — |
| GArtifactNightStar_Fake | 15845 | fake | GArtifactNightStar | 0.6 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | GArtifactNightStar |
| EArtifactDummy | 15937 | ordinary-candidate | TemplateArtifact | 0.45 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactDummy_Fake | 16022 | fake | EArtifactDummy | 0.45 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactDummy |
| CArtifactCrystalThorn | 16108 | ordinary-candidate | TemplateArtifact | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactCrystalThorn_Fake | 16195 | fake | CArtifactCrystalThorn | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactCrystalThorn |
| EArtifactBattery | 16283 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactBattery_Fake | 16371 | fake | EArtifactBattery | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactBattery |
| FArtifactCrystal | 16460 | ordinary-candidate | TemplateArtifact | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactCrystal_Fake | 16548 | fake | FArtifactCrystal | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactCrystal |
| EArtifactMoonlight | 16637 | ordinary-candidate | TemplateArtifact | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Electro | — |
| EArtifactMoonlight_Fake | 16725 | fake | EArtifactMoonlight | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | EArtifactMoonlight |
| FArtifactMomsBeads | 16814 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactMomsBeads_Fake | 16902 | fake | FArtifactMomsBeads | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactMomsBeads |
| EArtifactJellyFish | 16991 | ordinary-candidate | TemplateArtifact | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactJellyFish_Fake | 17079 | fake | EArtifactJellyFish | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactJellyFish |
| EArtifactTow | 17168 | ordinary-candidate | TemplateArtifact | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Electro | — |
| EArtifactTow_Fake | 17259 | fake | EArtifactTow | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | EArtifactTow |
| EArtifactThunderHedgehog | 17351 | ordinary-candidate | TemplateArtifact | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Electro | — |
| EArtifactThunderHedgehog_Fake | 17439 | fake | EArtifactThunderHedgehog | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | EArtifactThunderHedgehog |
| EArtifactWorm | 17528 | ordinary-candidate | TemplateArtifact | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactWorm_Fake | 17619 | fake | EArtifactWorm | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactWorm |
| EArtifactCloud | 17711 | ordinary-candidate | TemplateArtifact | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Electro | — |
| EArtifactCloud_Fake | 17802 | fake | EArtifactCloud | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | EArtifactCloud |
| EArtifactAtom | 17894 | ordinary-candidate | TemplateArtifact | 0.3 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Electro | — |
| EArtifactAtom_Fake | 17982 | fake | EArtifactAtom | 0.3 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | EArtifactAtom |
| EArtifactRazor | 18071 | ordinary-candidate | TemplateArtifact | 0.55 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Electro | — |
| EArtifactRazor_Fake | 18162 | fake | EArtifactRazor | 0.55 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | EArtifactRazor |
| EArtifactSparkler | 18254 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactSparkler_Fake | 18342 | fake | EArtifactSparkler | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactSparkler |
| FArtifactFireBall | 18431 | ordinary-candidate | TemplateArtifact | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactFireBall_Fake | 18519 | fake | FArtifactFireBall | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactFireBall |
| GArtifactGoldFish | 18608 | ordinary-candidate | TemplateArtifact | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactGoldFish_Fake | 18697 | fake | GArtifactGoldFish | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactGoldFish |
| FArtifactSteak | 18787 | ordinary-candidate | TemplateArtifact | 0.55 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactSteak_Fake | 18875 | fake | FArtifactSteak | 0.55 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactSteak |
| GArtifactStoneDrop | 18964 | ordinary-candidate | TemplateArtifact | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactStoneDrop_Fake | 19054 | fake | GArtifactStoneDrop | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactStoneDrop |
| FArtifactBakedBolts | 19145 | ordinary-candidate | TemplateArtifact | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fire | — |
| FArtifactBakedBolts_Fake | 19237 | fake | FArtifactBakedBolts | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | FArtifactBakedBolts |
| FArtifactGlass | 19330 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactGlass_Fake | 19422 | fake | FArtifactGlass | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactGlass |
| FArtifactDeadSponge | 19515 | ordinary-candidate | TemplateArtifact | 0.3 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fire | — |
| FArtifactDeadSponge_Fake | 19603 | fake | FArtifactDeadSponge | 0.3 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | FArtifactDeadSponge |
| FArtifactHellishHedgehog | 19692 | ordinary-candidate | TemplateArtifact | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fire | — |
| FArtifactHellishHedgehog_Fake | 19784 | fake | FArtifactHellishHedgehog | 0.55 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | FArtifactHellishHedgehog |
| FArtifactPlasma | 19877 | ordinary-candidate | TemplateArtifact | 0.5 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fire | — |
| FArtifactPlasma_Fake | 19965 | fake | FArtifactPlasma | 0.5 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | FArtifactPlasma |
| FArtifactCandle | 20054 | ordinary-candidate | TemplateArtifact | 0.3 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fire | — |
| FArtifactCandle_Fake | 20142 | fake | FArtifactCandle | 0.3 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | FArtifactCandle |
| FArtifactRingOmnipotence | 20231 | ordinary-candidate | TemplateArtifact | 0.6 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Fire | — |
| FArtifactRingOmnipotence_Fake | 20322 | fake | FArtifactRingOmnipotence | 0.6 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Fake | FArtifactRingOmnipotence |
| FArtifactFireworks | 20414 | ordinary-candidate | TemplateArtifact | 0.4 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fire | — |
| FArtifactFireworks_Fake | 20502 | fake | FArtifactFireworks | 0.4 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | FArtifactFireworks |
| FArtifactCore | 20591 | ordinary-candidate | TemplateArtifact | 0.55 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fire | — |
| FArtifactCore_Fake | 20683 | fake | FArtifactCore | 0.55 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | FArtifactCore |
| FArtifactBurntHunk | 20776 | ordinary-candidate | TemplateArtifact | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactBurntHunk_Fake | 20864 | fake | FArtifactBurntHunk | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactBurntHunk |
| FArtifactResin | 20953 | ordinary-candidate | TemplateArtifact | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactResin_Fake | 21043 | fake | FArtifactResin | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactResin |
| GArtifactSpring | 21134 | ordinary-candidate | TemplateArtifact | 0.45 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Gravity | — |
| GArtifactSpring_Fake | 21223 | fake | GArtifactSpring | 0.45 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | GArtifactSpring |
| CArtifactPellicle | 21313 | ordinary-candidate | TemplateArtifact | 0.35 | 20000.0 | EArtifactRarity::Rare | EArtifactType::Chemical | — |
| CArtifactPellicle_Fake | 21401 | fake | CArtifactPellicle | 0.35 | 20000.0 | EArtifactRarity::Rare | EArtifactType::Fake | CArtifactPellicle |
| CArtifactChunkMeat | 21490 | ordinary-candidate | TemplateArtifact | 0.45 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactChunkMeat_Fake | 21578 | fake | CArtifactChunkMeat | 0.45 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactChunkMeat |
| GArtifactGravy | 21667 | ordinary-candidate | TemplateArtifact | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactGravy_Fake | 21756 | fake | GArtifactGravy | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactGravy |
| FArtifactDrops | 21846 | ordinary-candidate | TemplateArtifact | 0.45 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactDrops_Fake | 21934 | fake | FArtifactDrops | 0.45 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactDrops |
| FArtifactEye | 22023 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fire | — |
| FArtifactEye_Fake | 22110 | fake | FArtifactEye | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | FArtifactEye |
| CArtifactBun | 22198 | ordinary-candidate | TemplateArtifact | 0.45 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Chemical | — |
| CArtifactBun_Fake | 22286 | fake | CArtifactBun | 0.45 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | CArtifactBun |
| CArtifactThorn | 22375 | ordinary-candidate | TemplateArtifact | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactThorn_Fake | 22460 | fake | CArtifactThorn | 0.35 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactThorn |
| GArtifactWrenched | 22546 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactWrenched_Fake | 22633 | fake | GArtifactWrenched | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactWrenched |
| GArtifactBloodStone | 22721 | ordinary-candidate | TemplateArtifact | 0.55 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactBloodStone_Fake | 22810 | fake | GArtifactBloodStone | 0.55 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactBloodStone |
| GArtifactGraphiteBlock | 22900 | ordinary-candidate | TemplateArtifact | 0.6 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Gravity | — |
| GArtifactGraphiteBlock_Fake | 22991 | fake | GArtifactGraphiteBlock | 0.6 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | GArtifactGraphiteBlock |
| GArtifactSplitStone | 23083 | ordinary-candidate | TemplateArtifact | 0.6 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Gravity | — |
| GArtifactSplitStone_Fake | 23171 | fake | GArtifactSplitStone | 0.6 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | GArtifactSplitStone |
| GArtifactTrunk | 23260 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactTrunk_Fake | 23350 | fake | GArtifactTrunk | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactTrunk |
| GArtifactRubiksCube | 23441 | ordinary-candidate | TemplateArtifact | 0.5 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Gravity | — |
| GArtifactRubiksCube_Fake | 23529 | fake | GArtifactRubiksCube | 0.5 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Fake | GArtifactRubiksCube |
| GArtifactSponge | 23618 | ordinary-candidate | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactSponge_Fake | 23709 | fake | GArtifactSponge | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactSponge |
| GArtifactHedgehog | 23801 | ordinary-candidate | TemplateArtifact | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Gravity | — |
| GArtifactHedgehog_Fake | 23890 | fake | GArtifactHedgehog | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | GArtifactHedgehog |
| GArtifactBud | 23980 | ordinary-candidate | TemplateArtifact | 0.4 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Gravity | — |
| GArtifactBud_Fake | 24071 | fake | GArtifactBud | 0.4 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | GArtifactBud |
| GArtifactPlane | 24163 | ordinary-candidate | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactPlane_Fake | 24254 | fake | GArtifactPlane | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactPlane |
| CArtifactMica | 24346 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactMica_Fake | 24431 | fake | CArtifactMica | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactMica |
| CArtifactBubble | 24517 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactBubble_Fake | 24602 | fake | CArtifactBubble | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactBubble |
| CArtifactSlime | 24688 | ordinary-candidate | TemplateArtifact | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactSlime_Fake | 24776 | fake | CArtifactSlime | 0.65 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactSlime |
| CArtifactSlug | 24865 | ordinary-candidate | TemplateArtifact | 0.6 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactSlug_Fake | 24950 | fake | CArtifactSlug | 0.6 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactSlug |
| CArtifactEchinus | 25036 | ordinary-candidate | TemplateArtifact | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Chemical | — |
| CArtifactEchinus_Fake | 25121 | fake | CArtifactEchinus | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | CArtifactEchinus |
| GArtifactCompass | 25207 | ordinary-candidate | TemplateArtifact | 0.5 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Gravity | — |
| GArtifactCompass_Fake | 25295 | fake | GArtifactCompass | 0.5 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Fake | GArtifactCompass |
| CArtifactKryptonite | 25384 | ordinary-candidate | TemplateArtifact | 0.55 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactKryptonite_Fake | 25472 | fake | CArtifactKryptonite | 0.55 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactKryptonite |
| CArtifactBung | 25561 | ordinary-candidate | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactBung_Fake | 25652 | fake | CArtifactBung | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactBung |
| EArtifactCrystalGlass | 25744 | ordinary-candidate | TemplateArtifact | 0.45 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Electro | — |
| EArtifactCrystalGlass_Fake | 25832 | fake | EArtifactCrystalGlass | 0.45 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | EArtifactCrystalGlass |
| CArtifactCottonWool | 25921 | ordinary-candidate | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| CArtifactCottonWool_Fake | 26012 | fake | CArtifactCottonWool | 0.3 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | CArtifactCottonWool |
| GArtifactLandSlug | 26104 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Gravity | — |
| GArtifactLandSlug_Fake | 26192 | fake | GArtifactLandSlug | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | GArtifactLandSlug |
| CArtifactRosin | 26281 | ordinary-candidate | TemplateArtifact | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Chemical | — |
| CArtifactRosin_Fake | 26372 | fake | CArtifactRosin | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | CArtifactRosin |
| CArtifactPlasticine | 26464 | ordinary-candidate | TemplateArtifact | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Chemical | — |
| CArtifactPlasticine_Fake | 26555 | fake | CArtifactPlasticine | 0.35 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Fake | CArtifactPlasticine |
| EArtifactDope | 26647 | ordinary-candidate | TemplateArtifact | 0.5 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Electro | — |
| EArtifactDope_Fake | 26735 | fake | EArtifactDope | 0.5 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Fake | EArtifactDope |
| CArtifactBouncyBall | 26824 | ordinary-candidate | TemplateArtifact | 0.4 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Chemical | — |
| CArtifactBouncyBall_Fake | 26909 | fake | CArtifactBouncyBall | 0.4 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | CArtifactBouncyBall |
| CArtifactDevilsMushroom | 26995 | ordinary-candidate | TemplateArtifact | 0.45 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Chemical | — |
| CArtifactDevilsMushroom_Fake | 27086 | fake | CArtifactDevilsMushroom | 0.45 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | CArtifactDevilsMushroom |
| EArtifactChocolate | 27178 | ordinary-candidate | TemplateArtifact | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Electro | — |
| EArtifactChocolate_Fake | 27266 | fake | EArtifactChocolate | 0.4 | 12000.0 | EArtifactRarity::Common | EArtifactType::Fake | EArtifactChocolate |
| CArtifactLiquidStone | 27355 | ordinary-candidate | TemplateArtifact | 0.6 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Chemical | — |
| CArtifactLiquidStone_Fake | 27446 | fake | CArtifactLiquidStone | 0.6 | 70000.0 | EArtifactRarity::Epic | EArtifactType::Fake | CArtifactLiquidStone |
| PArtifactBrain | 27538 | special-psy-candidate | GArtifactNightStar | 0.6 | 36000.0 | EArtifactRarity::Rare | EArtifactType::PSY | GArtifactNightStar |
| PArtifactBrain_Fake | 27630 | fake | PArtifactBrain | 0.6 | 36000.0 | EArtifactRarity::Rare | EArtifactType::Fake | GArtifactNightStar |
| PQuestArtifactScraper | 27722 | quest-or-prologue | TemplateArtifact | 0.5 | 0.0 | EArtifactRarity::Common | EArtifactType::PSY | — |
| PQuestArtifactScraper_Fake | 27804 | fake | PQuestArtifactScraper | 0.5 | 0.0 | EArtifactRarity::Common | EArtifactType::Fake | PQuestArtifactScraper |
| AArtifactWeirdBall | 27887 | archiartifact | TemplateArtifact | 0.3 | 12000.0 | EArtifactRarity::Epic | EArtifactType::Chemical | — |
| AArtifactWeirdWater | 27975 | archiartifact | TemplateArtifact | 0.55 | 80000.0 | EArtifactRarity::Epic | EArtifactType::Electro | — |
| AArtifactWeirdNut | 28059 | archiartifact | TemplateArtifact | 0.3 | 80000.0 | EArtifactRarity::Epic | EArtifactType::Chemical | — |
| AArtifactWeirdFlower | 28141 | archiartifact | TemplateArtifact | 0.1 | 12000.0 | EArtifactRarity::Epic | EArtifactType::Chemical | — |
| AArtifactWeirdBolt | 28227 | archiartifact | TemplateArtifact | 0.3 | 80000.0 | EArtifactRarity::Epic | EArtifactType::Chemical | — |
| AArtifactWeirdKettle | 28403 | archiartifact | TemplateArtifact | 0.65 | 80000.0 | EArtifactRarity::Epic | EArtifactType::Chemical | — |
| CPrologArtifactSlug | 28484 | quest-or-prologue | CArtifactSlug | 0.6 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | CArtifactSlug |
| TemplateQuestArtifact | 58396 | template | TemplateArtifact | 0.5 | 0.0 | EArtifactRarity::Common | EArtifactType::None | — |
| SQ13_Soul | 63192 | quest-or-prologue | EArtifactSoul | 0.4 | 20000.0 | EArtifactRarity::Uncommon | EArtifactType::Electro | — |
| QuestArtifactCrystalThorn | 66664 | quest-or-prologue | CArtifactCrystalThorn | 0.5 | 12000.0 | EArtifactRarity::Common | EArtifactType::Chemical | — |
| QuestArtifactHeartofChornobyl | 72557 | quest-or-prologue | TemplateArtifact | 0.5 | 0.0 | EArtifactRarity::Epic | EArtifactType::PSY | QuestArtifactHeartOfChornobyl |

## Complete behavior baselines

| SID | DetectorRequired | Strafe | Radius | JumpAmount | JumpDelay | JumpSeriesDelay | JumpDistance | LifeTime | LifeTimeDependant | Persistent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TemplateArtifact | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactFlash | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactFlash_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactSoul | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactSoul_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactSnowflake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactSnowflake_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactNightStar | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| GArtifactNightStar_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactDummy | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactDummy_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactCrystalThorn | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactCrystalThorn_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactBattery | true | true | 10.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactBattery_Fake | true | true | 10.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactCrystal | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactCrystal_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactMoonlight | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactMoonlight_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactMomsBeads | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactMomsBeads_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactJellyFish | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactJellyFish_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactTow | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactTow_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactThunderHedgehog | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactThunderHedgehog_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactWorm | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactWorm_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactCloud | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactCloud_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactAtom | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactAtom_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactRazor | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactRazor_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactSparkler | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactSparkler_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactFireBall | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactFireBall_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactGoldFish | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactGoldFish_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactSteak | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactSteak_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactStoneDrop | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactStoneDrop_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactBakedBolts | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactBakedBolts_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactGlass | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactGlass_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactDeadSponge | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactDeadSponge_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactHellishHedgehog | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactHellishHedgehog_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactPlasma | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactPlasma_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| FArtifactCandle | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| FArtifactCandle_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| FArtifactRingOmnipotence | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| FArtifactRingOmnipotence_Fake | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| FArtifactFireworks | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| FArtifactFireworks_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| FArtifactCore | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| FArtifactCore_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| FArtifactBurntHunk | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactBurntHunk_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactResin | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactResin_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactSpring | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactSpring_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactPellicle | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| CArtifactPellicle_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| CArtifactChunkMeat | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactChunkMeat_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactGravy | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactGravy_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactDrops | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactDrops_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactEye | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| FArtifactEye_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBun | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBun_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactThorn | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactThorn_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactWrenched | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactWrenched_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactBloodStone | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactBloodStone_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactGraphiteBlock | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactGraphiteBlock_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactSplitStone | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactSplitStone_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactTrunk | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactTrunk_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactRubiksCube | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| GArtifactRubiksCube_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| GArtifactSponge | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactSponge_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactHedgehog | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactHedgehog_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactBud | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| GArtifactBud_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| GArtifactPlane | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactPlane_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactMica | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactMica_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBubble | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBubble_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactSlime | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactSlime_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactSlug | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactSlug_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactEchinus | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactEchinus_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| GArtifactCompass | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| GArtifactCompass_Fake | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| CArtifactKryptonite | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactKryptonite_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBung | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBung_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactCrystalGlass | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactCrystalGlass_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| CArtifactCottonWool | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactCottonWool_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactLandSlug | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| GArtifactLandSlug_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactRosin | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactRosin_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactPlasticine | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| CArtifactPlasticine_Fake | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| EArtifactDope | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| EArtifactDope_Fake | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBouncyBall | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| CArtifactBouncyBall_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| CArtifactDevilsMushroom | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| CArtifactDevilsMushroom_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| EArtifactChocolate | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| EArtifactChocolate_Fake | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| CArtifactLiquidStone | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| CArtifactLiquidStone_Fake | true | true | 40.0 | 9 | 3.0 | 15.0 | 1500.0 | 3600.0 | true | false |
| PArtifactBrain | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| PArtifactBrain_Fake | true | true | 40.0 | 7 | 3.0 | 25.0 | 1500.0 | 3600.0 | true | false |
| PQuestArtifactScraper | true | true | 40.0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | true | false |
| PQuestArtifactScraper_Fake | true | true | 40.0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | true | false |
| AArtifactWeirdBall | false | false | 10 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| AArtifactWeirdWater | false | false | 10 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | true |
| AArtifactWeirdNut | false | false | 10 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | true |
| AArtifactWeirdFlower | false | false | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | true |
| AArtifactWeirdBolt | false | false | 10 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | true |
| AArtifactWeirdKettle | false | false | 10 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | true |
| CPrologArtifactSlug | true | false | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | false | false |
| TemplateQuestArtifact | true | true | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |
| SQ13_Soul | true | true | 40.0 | 5 | 3.0 | 35.0 | 1500.0 | 3600.0 | true | false |
| QuestArtifactCrystalThorn | false | true | 40.0 | 999 | 0.5 | 0.5 | 20000.0 | 3600.0 | true | false |
| QuestArtifactHeartofChornobyl | true | false | 40.0 | 3 | 6.0 | 45.0 | 1500.0 | 3600.0 | true | false |

## Every audited scalar field distribution

| Key path suffix | Raw value counts | Inherited only |
| --- | --- | --- |
| Type | {"EItemType::Artifact": 153, "EItemType::Info": 1} | none |
| LocalizationSID | {"None": 80, "EArtifactFlash": 1, "EArtifactSoul": 1, "EArtifactSnowflake": 1, "GArtifactNightStar": 3, "EArtifactDummy": 1, "CArtifactCrystalThorn": 1, "EArtifactBattery": 1, "FArtifactCrystal": 1, "EArtifactMoonlight": 1, "FArtifactMomsBeads": 1, "EArtifactJellyFish": 1, "EArtifactTow": 1, "EArtifactThunderHedgehog": 1, "EArtifactWorm": 1, "EArtifactCloud": 1, "EArtifactAtom": 1, "EArtifactRazor": 1, "EArtifactSparkler": 1, "FArtifactFireBall": 1, "GArtifactGoldFish": 1, "FArtifactSteak": 1, "GArtifactStoneDrop": 1, "FArtifactBakedBolts": 1, "FArtifactGlass": 1, "FArtifactDeadSponge": 1, "FArtifactHellishHedgehog": 1, "FArtifactPlasma": 1, "FArtifactCandle": 1, "FArtifactRingOmnipotence": 1, "FArtifactFireworks": 1, "FArtifactCore": 1, "FArtifactBurntHunk": 1, "FArtifactResin": 1, "GArtifactSpring": 1, "CArtifactPellicle": 1, "CArtifactChunkMeat": 1, "GArtifactGravy": 1, "FArtifactDrops": 1, "FArtifactEye": 1, "CArtifactBun": 1, "CArtifactThorn": 1, "GArtifactWrenched": 1, "GArtifactBloodStone": 1, "GArtifactGraphiteBlock": 1, "GArtifactSplitStone": 1, "GArtifactTrunk": 1, "GArtifactRubiksCube": 1, "GArtifactSponge": 1, "GArtifactHedgehog": 1, "GArtifactBud": 1, "GArtifactPlane": 1, "CArtifactMica": 1, "CArtifactBubble": 1, "CArtifactSlime": 1, "CArtifactSlug": 2, "CArtifactEchinus": 1, "GArtifactCompass": 1, "CArtifactKryptonite": 1, "CArtifactBung": 1, "EArtifactCrystalGlass": 1, "CArtifactCottonWool": 1, "GArtifactLandSlug": 1, "CArtifactRosin": 1, "CArtifactPlasticine": 1, "EArtifactDope": 1, "CArtifactBouncyBall": 1, "CArtifactDevilsMushroom": 1, "EArtifactChocolate": 1, "CArtifactLiquidStone": 1, "PQuestArtifactScraper": 1, "QuestArtifactHeartOfChornobyl": 1} | none |
| Weight | {"0.5": 20, "0.3": 21, "0.4": 35, "0.6": 15, "0.45": 14, "0.65": 11, "0.55": 19, "0.35": 18, "0.1": 1} | none |
| Cost | {"0.0": 5, "12000.0": 76, "20000.0": 35, "36000.0": 24, "70000.0": 10, "80000.0": 4} | none |
| Rarity | {"EArtifactRarity::Common": 78, "EArtifactRarity::Uncommon": 33, "EArtifactRarity::Rare": 26, "EArtifactRarity::Epic": 17} | none |
| AnomalyElementType | {"EAnomalyElementType::None": 2, "EAnomalyElementType::Electro": 36, "EAnomalyElementType::Gravity": 37, "EAnomalyElementType::Chemical": 43, "EAnomalyElementType::Fire": 34, "EAnomalyElementType::PSY": 2} | none |
| ArtifactType | {"EArtifactType::None": 2, "EArtifactType::Electro": 19, "EArtifactType::Fake": 71, "EArtifactType::Gravity": 17, "EArtifactType::Chemical": 25, "EArtifactType::Fire": 17, "EArtifactType::PSY": 3} | none |
| ArchiartifactType | {"EArchiartifactType::None": 147, "EArchiartifactType::Ball": 1, "EArchiartifactType::Water": 1, "EArchiartifactType::Nut": 1, "EArchiartifactType::Flower": 1, "EArchiartifactType::Bolt": 1, "EArchiartifactType::Kettle": 1, "EArchiartifactType::HeartOfChornobyl": 1} | none |
| MaxStackCount | {"999": 148, "1": 6} | none |
| ItemGridWidth | {"1": 154} | none |
| ItemGridHeight | {"1": 153, "2": 1} | none |
| IsQuestItem | {"None": 150, "true": 4} | none |
| IsQuestItemPrototype | {"None": 151, "true": 3} | none |
| RequireWeight | {"None": 153, "false": 1} | none |
| IgnoreEquippedWeight | {"false": 154} | none |
| Invisible | {"false": 154} | none |
| InvisibleInPlayerInventory | {"false": 154} | none |
| DestroyOnPickup | {"false": 84, "true": 70} | none |
| DropOnPickup | {"false": 154} | none |
| DetectorRequired | {"true": 147, "false": 7} | none |
| Strafe | {"true": 146, "false": 8} | none |
| ArtifactSpawn | {"true": 152, "false": 2} | none |
| LifeTime | {"3600.0": 152, "0.0": 2} | none |
| LifeTimeDependant | {"true": 153, "false": 1} | none |
| Persistent | {"false": 149, "true": 5} | none |
| Radius | {"40.0": 147, "10.0": 2, "10": 5} | none |
| JumpAmount | {"3": 76, "5": 41, "7": 26, "9": 8, "0": 2, "999": 1} | none |
| JumpDistance | {"1500.0": 151, "0.0": 2, "20000.0": 1} | none |
| JumpDelay | {"6.0": 76, "3.0": 75, "0.0": 2, "0.5": 1} | none |
| JumpSeriesDelay | {"45.0": 76, "35.0": 41, "25.0": 26, "15.0": 8, "0.0": 2, "0.5": 1} | none |
| JumpHeight | {"100.0": 151, "0.0": 2, "150.0": 1} | none |
| JumpForce | {"15.0": 151, "0.0": 2, "20.0": 1} | none |
| JumpSpeedCoef | {"1.0": 153, "1.5": 1} | none |
| PlayerDistance | {"1000.0": 153, "100000.0": 1} | none |
| ReturnDistanceValue | {"10000.0": 153, "100000.0": 1} | none |
| StateTransitionDelay | {"1.0": 154} | none |
| DisableCollisionWhenHide | {"true": 154} | none |
| DamageToStaminaCoefficient | {"None": 153, "2.0": 1} | none |
| DamageToWeightCoefficient | {"None": 153, "0.01": 1} | none |
| MinWeight | {"None": 153, "0.5": 1} | none |
| MaxWeight | {"None": 153, "7.5": 1} | none |
| WeightDecreaseDelay | {"None": 153, "0.0": 1} | none |
| WeightDecreaseRate | {"None": 153, "10.0": 1} | none |
| WeightDecreaseAmount | {"None": 153, "0.2": 1} | none |
| MinimalDrunkenness | {"None": 153, "15.0": 1} | none |
| EffectsDuration | {"None": 153, "7200.f": 1} | none |
| MaxCharge | {"None": 153, "300.0": 1} | none |
| ChargeThreshold | {"None": 153, "1.0": 1} | none |
| ChargingSpeed | {"None": 153, "20.0": 1} | none |
| bUseCharge | {"None": 153, "false": 1} | none |
| LandingForce | {"None": 153, "300.0": 1} | none |

## Exact special item paths and baselines

| Path | Value |
| --- | --- |
| AArtifactWeirdBall.DamageToStaminaCoefficient | 2.0 |
| AArtifactWeirdBall.DamageToWeightCoefficient | 0.01 |
| AArtifactWeirdBall.MinWeight | 0.5 |
| AArtifactWeirdBall.MaxWeight | 7.5 |
| AArtifactWeirdBall.WeightDecreaseDelay | 0.0 |
| AArtifactWeirdBall.WeightDecreaseRate | 10.0 |
| AArtifactWeirdBall.WeightDecreaseAmount | 0.2 |
| AArtifactWeirdWater.MinimalDrunkenness | 15.0 |
| AArtifactWeirdFlower.EffectsDuration | 7200.f |
| AArtifactWeirdBolt.MaxCharge | 300.0 |
| AArtifactWeirdBolt.ChargeThreshold | 1.0 |
| AArtifactWeirdBolt.ChargingSpeed | 20.0 |
| AArtifactWeirdBolt.bUseCharge | false |
| QuestArtifactCrystalThorn.LandingForce | 300.0 |

## Complete artifact effect and metadata reference paths

| Path | Value |
| --- | --- |
| TemplateArtifact.EffectPrototypeSIDs.[0] | empty |
| TemplateArtifact.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactFlash.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactFlash.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactFlash.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactFlash.ShouldShowEffects.[0] | true |
| EArtifactFlash.ShouldShowEffects.[1] | true |
| EArtifactFlash.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactFlash.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactFlash_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactFlash_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactFlash_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactFlash_Fake.ShouldShowEffects.[0] | true |
| EArtifactFlash_Fake.ShouldShowEffects.[1] | true |
| EArtifactFlash_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactFlash_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactSoul.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina2 |
| EArtifactSoul.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| EArtifactSoul.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactSoul.ShouldShowEffects.[0] | true |
| EArtifactSoul.ShouldShowEffects.[1] | true |
| EArtifactSoul.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactSoul.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactSoul_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina2 |
| EArtifactSoul_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| EArtifactSoul_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactSoul_Fake.EffectOnPickPrototypeSIDs.ViewOffset.X | 0.0 |
| EArtifactSoul_Fake.EffectOnPickPrototypeSIDs.ViewOffset.Y | 3.0 |
| EArtifactSoul_Fake.EffectOnPickPrototypeSIDs.ViewOffset.Z | 0.0 |
| EArtifactSoul_Fake.ShouldShowEffects.[0] | true |
| EArtifactSoul_Fake.ShouldShowEffects.[1] | true |
| EArtifactSoul_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactSoul_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactSnowflake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactSnowflake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactSnowflake.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactSnowflake.ShouldShowEffects.[0] | true |
| EArtifactSnowflake.ShouldShowEffects.[1] | true |
| EArtifactSnowflake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactSnowflake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactSnowflake_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactSnowflake_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactSnowflake_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactSnowflake_Fake.EffectOnPickPrototypeSIDs.ViewOffset.X | 0.0 |
| EArtifactSnowflake_Fake.EffectOnPickPrototypeSIDs.ViewOffset.Y | 3.0 |
| EArtifactSnowflake_Fake.EffectOnPickPrototypeSIDs.ViewOffset.Z | 2.0 |
| EArtifactSnowflake_Fake.ShouldShowEffects.[0] | true |
| EArtifactSnowflake_Fake.ShouldShowEffects.[1] | true |
| EArtifactSnowflake_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactSnowflake_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactNightStar.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight3 |
| GArtifactNightStar.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| GArtifactNightStar.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect3 |
| GArtifactNightStar.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactNightStar.ShouldShowEffects.[0] | true |
| GArtifactNightStar.ShouldShowEffects.[1] | true |
| GArtifactNightStar.ShouldShowEffects.[2] | false |
| GArtifactNightStar.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactNightStar.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactNightStar.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactNightStar_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight3 |
| GArtifactNightStar_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| GArtifactNightStar_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect3 |
| GArtifactNightStar_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactNightStar_Fake.ShouldShowEffects.[0] | true |
| GArtifactNightStar_Fake.ShouldShowEffects.[1] | true |
| GArtifactNightStar_Fake.ShouldShowEffects.[2] | false |
| GArtifactNightStar_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactNightStar_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactNightStar_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactDummy.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactDummy.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactDummy.ShouldShowEffects.[0] | true |
| EArtifactDummy.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactDummy_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactDummy_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactDummy_Fake.ShouldShowEffects.[0] | true |
| EArtifactDummy_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactCrystalThorn.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactCrystalThorn.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactCrystalThorn.ShouldShowEffects.[0] | true |
| CArtifactCrystalThorn.ShouldShowEffects.[1] | true |
| CArtifactCrystalThorn.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactCrystalThorn.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactCrystalThorn_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactCrystalThorn_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactCrystalThorn_Fake.ShouldShowEffects.[0] | true |
| CArtifactCrystalThorn_Fake.ShouldShowEffects.[1] | true |
| CArtifactCrystalThorn_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactCrystalThorn_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactBattery.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactBattery.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactBattery.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactBattery.ShouldShowEffects.[0] | true |
| EArtifactBattery.ShouldShowEffects.[1] | true |
| EArtifactBattery.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactBattery.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactBattery_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactBattery_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactBattery_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactBattery_Fake.ShouldShowEffects.[0] | true |
| EArtifactBattery_Fake.ShouldShowEffects.[1] | true |
| EArtifactBattery_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactBattery_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCrystal.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactCrystal.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| FArtifactCrystal.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactCrystal.ShouldShowEffects.[0] | true |
| FArtifactCrystal.ShouldShowEffects.[1] | true |
| FArtifactCrystal.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactCrystal.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCrystal_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactCrystal_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| FArtifactCrystal_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactCrystal_Fake.ShouldShowEffects.[0] | true |
| FArtifactCrystal_Fake.ShouldShowEffects.[1] | true |
| FArtifactCrystal_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactCrystal_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactMoonlight.EffectPrototypeSIDs.[0] | ArtifactProtectionShock2 |
| EArtifactMoonlight.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| EArtifactMoonlight.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactMoonlight.ShouldShowEffects.[0] | true |
| EArtifactMoonlight.ShouldShowEffects.[1] | true |
| EArtifactMoonlight.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactMoonlight.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactMoonlight_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock2 |
| EArtifactMoonlight_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| EArtifactMoonlight_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactMoonlight_Fake.ShouldShowEffects.[0] | true |
| EArtifactMoonlight_Fake.ShouldShowEffects.[1] | true |
| EArtifactMoonlight_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactMoonlight_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactMomsBeads.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding2 |
| FArtifactMomsBeads.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| FArtifactMomsBeads.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactMomsBeads.ShouldShowEffects.[0] | true |
| FArtifactMomsBeads.ShouldShowEffects.[1] | true |
| FArtifactMomsBeads.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactMomsBeads.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactMomsBeads_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding2 |
| FArtifactMomsBeads_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| FArtifactMomsBeads_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactMomsBeads_Fake.ShouldShowEffects.[0] | true |
| FArtifactMomsBeads_Fake.ShouldShowEffects.[1] | true |
| FArtifactMomsBeads_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactMomsBeads_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactJellyFish.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina05 |
| EArtifactJellyFish.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding05 |
| EArtifactJellyFish.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactJellyFish.ShouldShowEffects.[0] | true |
| EArtifactJellyFish.ShouldShowEffects.[1] | true |
| EArtifactJellyFish.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactJellyFish.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactJellyFish_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina05 |
| EArtifactJellyFish_Fake.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding05 |
| EArtifactJellyFish_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactJellyFish_Fake.ShouldShowEffects.[0] | true |
| EArtifactJellyFish_Fake.ShouldShowEffects.[1] | true |
| EArtifactJellyFish_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactJellyFish_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactTow.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactTow.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding1 |
| EArtifactTow.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| EArtifactTow.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactTow.ShouldShowEffects.[0] | true |
| EArtifactTow.ShouldShowEffects.[1] | true |
| EArtifactTow.ShouldShowEffects.[2] | true |
| EArtifactTow.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactTow.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactTow.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactTow_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina1 |
| EArtifactTow_Fake.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding1 |
| EArtifactTow_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| EArtifactTow_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactTow_Fake.ShouldShowEffects.[0] | true |
| EArtifactTow_Fake.ShouldShowEffects.[1] | true |
| EArtifactTow_Fake.ShouldShowEffects.[2] | true |
| EArtifactTow_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactTow_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactTow_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactThunderHedgehog.EffectPrototypeSIDs.[0] | ArtifactProtectionShock2 |
| EArtifactThunderHedgehog.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation2 |
| EArtifactThunderHedgehog.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactThunderHedgehog.ShouldShowEffects.[0] | true |
| EArtifactThunderHedgehog.ShouldShowEffects.[1] | true |
| EArtifactThunderHedgehog.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactThunderHedgehog.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactThunderHedgehog_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock2 |
| EArtifactThunderHedgehog_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation2 |
| EArtifactThunderHedgehog_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactThunderHedgehog_Fake.ShouldShowEffects.[0] | true |
| EArtifactThunderHedgehog_Fake.ShouldShowEffects.[1] | true |
| EArtifactThunderHedgehog_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactThunderHedgehog_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactWorm.EffectPrototypeSIDs.[0] | ArtifactProtectionShock05 |
| EArtifactWorm.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding05 |
| EArtifactWorm.EffectPrototypeSIDs.[2] | ArtifactProtectionRadiation1 |
| EArtifactWorm.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactWorm.ShouldShowEffects.[0] | true |
| EArtifactWorm.ShouldShowEffects.[1] | true |
| EArtifactWorm.ShouldShowEffects.[2] | true |
| EArtifactWorm.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactWorm.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactWorm.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactWorm_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock05 |
| EArtifactWorm_Fake.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding05 |
| EArtifactWorm_Fake.EffectPrototypeSIDs.[2] | ArtifactProtectionRadiation1 |
| EArtifactWorm_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactWorm_Fake.ShouldShowEffects.[0] | true |
| EArtifactWorm_Fake.ShouldShowEffects.[1] | true |
| EArtifactWorm_Fake.ShouldShowEffects.[2] | true |
| EArtifactWorm_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactWorm_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactWorm_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactCloud.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactCloud.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding1 |
| EArtifactCloud.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| EArtifactCloud.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactCloud.ShouldShowEffects.[0] | true |
| EArtifactCloud.ShouldShowEffects.[1] | true |
| EArtifactCloud.ShouldShowEffects.[2] | true |
| EArtifactCloud.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactCloud.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactCloud.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactCloud_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactCloud_Fake.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding1 |
| EArtifactCloud_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| EArtifactCloud_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactCloud_Fake.ShouldShowEffects.[0] | true |
| EArtifactCloud_Fake.ShouldShowEffects.[1] | true |
| EArtifactCloud_Fake.ShouldShowEffects.[2] | true |
| EArtifactCloud_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactCloud_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactCloud_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactAtom.EffectPrototypeSIDs.[0] | ArtifactProtectionShock3 |
| EArtifactAtom.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| EArtifactAtom.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactAtom.ShouldShowEffects.[0] | true |
| EArtifactAtom.ShouldShowEffects.[1] | true |
| EArtifactAtom.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactAtom.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactAtom_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock3 |
| EArtifactAtom_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| EArtifactAtom_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactAtom_Fake.ShouldShowEffects.[0] | true |
| EArtifactAtom_Fake.ShouldShowEffects.[1] | true |
| EArtifactAtom_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactAtom_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactRazor.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina2 |
| EArtifactRazor.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding2 |
| EArtifactRazor.EffectPrototypeSIDs.[2] | ArtifactAddRadiation3 |
| EArtifactRazor.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactRazor.ShouldShowEffects.[0] | true |
| EArtifactRazor.ShouldShowEffects.[1] | true |
| EArtifactRazor.ShouldShowEffects.[2] | true |
| EArtifactRazor.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactRazor.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactRazor.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactRazor_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina2 |
| EArtifactRazor_Fake.EffectPrototypeSIDs.[1] | ArtifactDegenBleeding2 |
| EArtifactRazor_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation3 |
| EArtifactRazor_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactRazor_Fake.ShouldShowEffects.[0] | true |
| EArtifactRazor_Fake.ShouldShowEffects.[1] | true |
| EArtifactRazor_Fake.ShouldShowEffects.[2] | true |
| EArtifactRazor_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactRazor_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactRazor_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactSparkler.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactSparkler.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| EArtifactSparkler.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactSparkler.ShouldShowEffects.[0] | true |
| EArtifactSparkler.ShouldShowEffects.[1] | true |
| EArtifactSparkler.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactSparkler.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactSparkler_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactSparkler_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| EArtifactSparkler_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactSparkler_Fake.ShouldShowEffects.[0] | true |
| EArtifactSparkler_Fake.ShouldShowEffects.[1] | true |
| EArtifactSparkler_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactSparkler_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactFireBall.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactFireBall.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| FArtifactFireBall.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactFireBall.ShouldShowEffects.[0] | true |
| FArtifactFireBall.ShouldShowEffects.[1] | true |
| FArtifactFireBall.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactFireBall.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactFireBall_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactFireBall_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| FArtifactFireBall_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactFireBall_Fake.ShouldShowEffects.[0] | true |
| FArtifactFireBall_Fake.ShouldShowEffects.[1] | true |
| FArtifactFireBall_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactFireBall_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGoldFish.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactGoldFish.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactGoldFish.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactGoldFish.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactGoldFish.ShouldShowEffects.[0] | true |
| GArtifactGoldFish.ShouldShowEffects.[1] | true |
| GArtifactGoldFish.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactGoldFish.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGoldFish_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactGoldFish_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactGoldFish_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactGoldFish_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactGoldFish_Fake.ShouldShowEffects.[0] | true |
| GArtifactGoldFish_Fake.ShouldShowEffects.[1] | true |
| GArtifactGoldFish_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactGoldFish_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactSteak.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding1 |
| FArtifactSteak.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| FArtifactSteak.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactSteak.ShouldShowEffects.[0] | true |
| FArtifactSteak.ShouldShowEffects.[1] | true |
| FArtifactSteak.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactSteak.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactSteak_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding1 |
| FArtifactSteak_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| FArtifactSteak_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactSteak_Fake.ShouldShowEffects.[0] | true |
| FArtifactSteak_Fake.ShouldShowEffects.[1] | true |
| FArtifactSteak_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactSteak_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactStoneDrop.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactStoneDrop.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactStoneDrop.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactStoneDrop.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactStoneDrop.ShouldShowEffects.[0] | true |
| GArtifactStoneDrop.ShouldShowEffects.[1] | true |
| GArtifactStoneDrop.ShouldShowEffects.[2] | false |
| GArtifactStoneDrop.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactStoneDrop.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactStoneDrop_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactStoneDrop_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactStoneDrop_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactStoneDrop_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactStoneDrop_Fake.ShouldShowEffects.[0] | true |
| GArtifactStoneDrop_Fake.ShouldShowEffects.[1] | true |
| GArtifactStoneDrop_Fake.ShouldShowEffects.[2] | false |
| GArtifactStoneDrop_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactStoneDrop_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactBakedBolts.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding1 |
| FArtifactBakedBolts.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight1 |
| FArtifactBakedBolts.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| FArtifactBakedBolts.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect1 |
| FArtifactBakedBolts.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactBakedBolts.ShouldShowEffects.[0] | true |
| FArtifactBakedBolts.ShouldShowEffects.[1] | true |
| FArtifactBakedBolts.ShouldShowEffects.[2] | true |
| FArtifactBakedBolts.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactBakedBolts.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactBakedBolts.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactBakedBolts_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding1 |
| FArtifactBakedBolts_Fake.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight1 |
| FArtifactBakedBolts_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| FArtifactBakedBolts_Fake.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect1 |
| FArtifactBakedBolts_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactBakedBolts_Fake.ShouldShowEffects.[0] | true |
| FArtifactBakedBolts_Fake.ShouldShowEffects.[1] | true |
| FArtifactBakedBolts_Fake.ShouldShowEffects.[2] | true |
| FArtifactBakedBolts_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactBakedBolts_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactBakedBolts_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactGlass.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding05 |
| FArtifactGlass.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight05 |
| FArtifactGlass.EffectPrototypeSIDs.[2] | ArtifactAddRadiation1 |
| FArtifactGlass.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect05 |
| FArtifactGlass.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactGlass.ShouldShowEffects.[0] | true |
| FArtifactGlass.ShouldShowEffects.[1] | true |
| FArtifactGlass.ShouldShowEffects.[2] | true |
| FArtifactGlass.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactGlass.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactGlass.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactGlass_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding05 |
| FArtifactGlass_Fake.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight05 |
| FArtifactGlass_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation1 |
| FArtifactGlass_Fake.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect05 |
| FArtifactGlass_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactGlass_Fake.ShouldShowEffects.[0] | true |
| FArtifactGlass_Fake.ShouldShowEffects.[1] | true |
| FArtifactGlass_Fake.ShouldShowEffects.[2] | true |
| FArtifactGlass_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactGlass_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactGlass_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactDeadSponge.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding2 |
| FArtifactDeadSponge.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| FArtifactDeadSponge.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactDeadSponge.ShouldShowEffects.[0] | true |
| FArtifactDeadSponge.ShouldShowEffects.[1] | true |
| FArtifactDeadSponge.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactDeadSponge.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactDeadSponge_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding2 |
| FArtifactDeadSponge_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| FArtifactDeadSponge_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactDeadSponge_Fake.ShouldShowEffects.[0] | true |
| FArtifactDeadSponge_Fake.ShouldShowEffects.[1] | true |
| FArtifactDeadSponge_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactDeadSponge_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactHellishHedgehog.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactHellishHedgehog.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight1 |
| FArtifactHellishHedgehog.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| FArtifactHellishHedgehog.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect1 |
| FArtifactHellishHedgehog.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactHellishHedgehog.ShouldShowEffects.[0] | true |
| FArtifactHellishHedgehog.ShouldShowEffects.[1] | true |
| FArtifactHellishHedgehog.ShouldShowEffects.[2] | true |
| FArtifactHellishHedgehog.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactHellishHedgehog.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactHellishHedgehog.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactHellishHedgehog_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactHellishHedgehog_Fake.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight1 |
| FArtifactHellishHedgehog_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| FArtifactHellishHedgehog_Fake.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect1 |
| FArtifactHellishHedgehog_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactHellishHedgehog_Fake.ShouldShowEffects.[0] | true |
| FArtifactHellishHedgehog_Fake.ShouldShowEffects.[1] | true |
| FArtifactHellishHedgehog_Fake.ShouldShowEffects.[2] | true |
| FArtifactHellishHedgehog_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactHellishHedgehog_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactHellishHedgehog_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactPlasma.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn2 |
| FArtifactPlasma.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation2 |
| FArtifactPlasma.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactPlasma.ShouldShowEffects.[0] | true |
| FArtifactPlasma.ShouldShowEffects.[1] | true |
| FArtifactPlasma.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactPlasma.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactPlasma_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn2 |
| FArtifactPlasma_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation2 |
| FArtifactPlasma_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactPlasma_Fake.ShouldShowEffects.[0] | true |
| FArtifactPlasma_Fake.ShouldShowEffects.[1] | true |
| FArtifactPlasma_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactPlasma_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCandle.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding3 |
| FArtifactCandle.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| FArtifactCandle.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactCandle.ShouldShowEffects.[0] | true |
| FArtifactCandle.ShouldShowEffects.[1] | true |
| FArtifactCandle.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactCandle.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCandle_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding3 |
| FArtifactCandle_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| FArtifactCandle_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactCandle_Fake.ShouldShowEffects.[0] | true |
| FArtifactCandle_Fake.ShouldShowEffects.[1] | true |
| FArtifactCandle_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactCandle_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactRingOmnipotence.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding4 |
| FArtifactRingOmnipotence.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| FArtifactRingOmnipotence.EffectPrototypeSIDs.[2] | ArtifactProtectionBurn4 |
| FArtifactRingOmnipotence.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactRingOmnipotence.ShouldShowEffects.[0] | true |
| FArtifactRingOmnipotence.ShouldShowEffects.[1] | true |
| FArtifactRingOmnipotence.ShouldShowEffects.[2] | true |
| FArtifactRingOmnipotence.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactRingOmnipotence.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactRingOmnipotence.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactRingOmnipotence_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding4 |
| FArtifactRingOmnipotence_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| FArtifactRingOmnipotence_Fake.EffectPrototypeSIDs.[2] | ArtifactProtectionBurn4 |
| FArtifactRingOmnipotence_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactRingOmnipotence_Fake.ShouldShowEffects.[0] | true |
| FArtifactRingOmnipotence_Fake.ShouldShowEffects.[1] | true |
| FArtifactRingOmnipotence_Fake.ShouldShowEffects.[2] | true |
| FArtifactRingOmnipotence_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactRingOmnipotence_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactRingOmnipotence_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactFireworks.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn3 |
| FArtifactFireworks.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| FArtifactFireworks.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactFireworks.ShouldShowEffects.[0] | true |
| FArtifactFireworks.ShouldShowEffects.[1] | true |
| FArtifactFireworks.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactFireworks.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactFireworks_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn3 |
| FArtifactFireworks_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| FArtifactFireworks_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactFireworks_Fake.ShouldShowEffects.[0] | true |
| FArtifactFireworks_Fake.ShouldShowEffects.[1] | true |
| FArtifactFireworks_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactFireworks_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCore.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn2 |
| FArtifactCore.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight2 |
| FArtifactCore.EffectPrototypeSIDs.[2] | ArtifactAddRadiation3 |
| FArtifactCore.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect2 |
| FArtifactCore.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactCore.ShouldShowEffects.[0] | true |
| FArtifactCore.ShouldShowEffects.[1] | true |
| FArtifactCore.ShouldShowEffects.[2] | true |
| FArtifactCore.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactCore.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCore.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactCore_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn2 |
| FArtifactCore_Fake.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight2 |
| FArtifactCore_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation3 |
| FArtifactCore_Fake.EffectPrototypeSIDs.[3] | ArtifactPenaltyLessWeightEffect2 |
| FArtifactCore_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactCore_Fake.ShouldShowEffects.[0] | true |
| FArtifactCore_Fake.ShouldShowEffects.[1] | true |
| FArtifactCore_Fake.ShouldShowEffects.[2] | true |
| FArtifactCore_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactCore_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactCore_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactBurntHunk.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding1 |
| FArtifactBurntHunk.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| FArtifactBurntHunk.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactBurntHunk.ShouldShowEffects.[0] | true |
| FArtifactBurntHunk.ShouldShowEffects.[1] | true |
| FArtifactBurntHunk.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactBurntHunk.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactBurntHunk_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding1 |
| FArtifactBurntHunk_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| FArtifactBurntHunk_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactBurntHunk_Fake.ShouldShowEffects.[0] | true |
| FArtifactBurntHunk_Fake.ShouldShowEffects.[1] | true |
| FArtifactBurntHunk_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactBurntHunk_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactResin.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding05 |
| FArtifactResin.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight05 |
| FArtifactResin.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactResin.ShouldShowEffects.[0] | true |
| FArtifactResin.ShouldShowEffects.[1] | true |
| FArtifactResin.ShouldShowEffects.[2] | true |
| FArtifactResin.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactResin.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactResin.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| FArtifactResin_Fake.EffectPrototypeSIDs.[0] | ArtifactDegenBleeding05 |
| FArtifactResin_Fake.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight05 |
| FArtifactResin_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactResin_Fake.ShouldShowEffects.[0] | true |
| FArtifactResin_Fake.ShouldShowEffects.[1] | true |
| FArtifactResin_Fake.ShouldShowEffects.[2] | true |
| FArtifactResin_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactResin_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactResin_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactSpring.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight2 |
| GArtifactSpring.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| GArtifactSpring.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect2 |
| GArtifactSpring.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactSpring.ShouldShowEffects.[0] | true |
| GArtifactSpring.ShouldShowEffects.[1] | true |
| GArtifactSpring.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactSpring.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactSpring_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight2 |
| GArtifactSpring_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| GArtifactSpring_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect2 |
| GArtifactSpring_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactSpring_Fake.ShouldShowEffects.[0] | true |
| GArtifactSpring_Fake.ShouldShowEffects.[1] | true |
| GArtifactSpring_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactSpring_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactPellicle.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn3 |
| CArtifactPellicle.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation3 |
| CArtifactPellicle.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactPellicle.ShouldShowEffects.[0] | true |
| CArtifactPellicle.ShouldShowEffects.[1] | true |
| CArtifactPellicle.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactPellicle.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactPellicle_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn3 |
| CArtifactPellicle_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation3 |
| CArtifactPellicle_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactPellicle_Fake.ShouldShowEffects.[0] | true |
| CArtifactPellicle_Fake.ShouldShowEffects.[1] | true |
| CArtifactPellicle_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactPellicle_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactChunkMeat.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn1 |
| CArtifactChunkMeat.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| CArtifactChunkMeat.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactChunkMeat.ShouldShowEffects.[0] | true |
| CArtifactChunkMeat.ShouldShowEffects.[1] | true |
| CArtifactChunkMeat.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactChunkMeat.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactChunkMeat_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn1 |
| CArtifactChunkMeat_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| CArtifactChunkMeat_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactChunkMeat_Fake.ShouldShowEffects.[0] | true |
| CArtifactChunkMeat_Fake.ShouldShowEffects.[1] | true |
| CArtifactChunkMeat_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactChunkMeat_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGravy.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactGravy.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| GArtifactGravy.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactGravy.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactGravy.ShouldShowEffects.[0] | true |
| GArtifactGravy.ShouldShowEffects.[1] | true |
| GArtifactGravy.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactGravy.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGravy_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactGravy_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| GArtifactGravy_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactGravy_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactGravy_Fake.ShouldShowEffects.[0] | true |
| GArtifactGravy_Fake.ShouldShowEffects.[1] | true |
| GArtifactGravy_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactGravy_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactDrops.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactDrops.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| FArtifactDrops.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactDrops.ShouldShowEffects.[0] | true |
| FArtifactDrops.ShouldShowEffects.[1] | true |
| FArtifactDrops.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactDrops.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactDrops_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactDrops_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| FArtifactDrops_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactDrops_Fake.ShouldShowEffects.[0] | true |
| FArtifactDrops_Fake.ShouldShowEffects.[1] | true |
| FArtifactDrops_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactDrops_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactEye.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactEye.EffectOnPickPrototypeSIDs.[0] | empty |
| FArtifactEye.ShouldShowEffects.[0] | true |
| FArtifactEye.ShouldShowEffects.[1] | true |
| FArtifactEye.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactEye.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| FArtifactEye_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionBurn1 |
| FArtifactEye_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| FArtifactEye_Fake.ShouldShowEffects.[0] | true |
| FArtifactEye_Fake.ShouldShowEffects.[1] | true |
| FArtifactEye_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| FArtifactEye_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactBun.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn2 |
| CArtifactBun.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| CArtifactBun.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactBun.ShouldShowEffects.[0] | true |
| CArtifactBun.ShouldShowEffects.[1] | true |
| CArtifactBun.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBun.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactBun_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn2 |
| CArtifactBun_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| CArtifactBun_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactBun_Fake.ShouldShowEffects.[0] | true |
| CArtifactBun_Fake.ShouldShowEffects.[1] | true |
| CArtifactBun_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBun_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactThorn.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactThorn.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactThorn.ShouldShowEffects.[0] | true |
| CArtifactThorn.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactThorn_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactThorn_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactThorn_Fake.ShouldShowEffects.[0] | true |
| CArtifactThorn_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactWrenched.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| GArtifactWrenched.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactWrenched.ShouldShowEffects.[0] | true |
| GArtifactWrenched.ShouldShowEffects.[1] | true |
| GArtifactWrenched.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactWrenched.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactWrenched_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| GArtifactWrenched_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactWrenched_Fake.ShouldShowEffects.[0] | true |
| GArtifactWrenched_Fake.ShouldShowEffects.[1] | true |
| GArtifactWrenched_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactWrenched_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactBloodStone.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactBloodStone.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactBloodStone.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactBloodStone.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactBloodStone.ShouldShowEffects.[0] | true |
| GArtifactBloodStone.ShouldShowEffects.[1] | true |
| GArtifactBloodStone.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactBloodStone.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactBloodStone_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight1 |
| GArtifactBloodStone_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactBloodStone_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect1 |
| GArtifactBloodStone_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactBloodStone_Fake.ShouldShowEffects.[0] | true |
| GArtifactBloodStone_Fake.ShouldShowEffects.[1] | true |
| GArtifactBloodStone_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactBloodStone_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGraphiteBlock.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| GArtifactGraphiteBlock.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina1 |
| GArtifactGraphiteBlock.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| GArtifactGraphiteBlock.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactGraphiteBlock.ShouldShowEffects.[0] | true |
| GArtifactGraphiteBlock.ShouldShowEffects.[1] | true |
| GArtifactGraphiteBlock.ShouldShowEffects.[2] | true |
| GArtifactGraphiteBlock.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactGraphiteBlock.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGraphiteBlock.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactGraphiteBlock_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| GArtifactGraphiteBlock_Fake.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina1 |
| GArtifactGraphiteBlock_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation2 |
| GArtifactGraphiteBlock_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactGraphiteBlock_Fake.ShouldShowEffects.[0] | true |
| GArtifactGraphiteBlock_Fake.ShouldShowEffects.[1] | true |
| GArtifactGraphiteBlock_Fake.ShouldShowEffects.[2] | true |
| GArtifactGraphiteBlock_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactGraphiteBlock_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactGraphiteBlock_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactSplitStone.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike2 |
| GArtifactSplitStone.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| GArtifactSplitStone.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactSplitStone.ShouldShowEffects.[0] | true |
| GArtifactSplitStone.ShouldShowEffects.[1] | true |
| GArtifactSplitStone.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactSplitStone.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactSplitStone_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike2 |
| GArtifactSplitStone_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| GArtifactSplitStone_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactSplitStone_Fake.ShouldShowEffects.[0] | true |
| GArtifactSplitStone_Fake.ShouldShowEffects.[1] | true |
| GArtifactSplitStone_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactSplitStone_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactTrunk.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina05 |
| GArtifactTrunk.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight05 |
| GArtifactTrunk.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactTrunk.ShouldShowEffects.[0] | true |
| GArtifactTrunk.ShouldShowEffects.[1] | true |
| GArtifactTrunk.ShouldShowEffects.[2] | true |
| GArtifactTrunk.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactTrunk.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactTrunk.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactTrunk_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina05 |
| GArtifactTrunk_Fake.EffectPrototypeSIDs.[1] | ArtifactAdditionalInventoryWeight05 |
| GArtifactTrunk_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactTrunk_Fake.ShouldShowEffects.[0] | true |
| GArtifactTrunk_Fake.ShouldShowEffects.[1] | true |
| GArtifactTrunk_Fake.ShouldShowEffects.[2] | true |
| GArtifactTrunk_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactTrunk_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactTrunk_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactRubiksCube.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike3 |
| GArtifactRubiksCube.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| GArtifactRubiksCube.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactRubiksCube.ShouldShowEffects.[0] | true |
| GArtifactRubiksCube.ShouldShowEffects.[1] | true |
| GArtifactRubiksCube.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactRubiksCube.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactRubiksCube_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike3 |
| GArtifactRubiksCube_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| GArtifactRubiksCube_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactRubiksCube_Fake.ShouldShowEffects.[0] | true |
| GArtifactRubiksCube_Fake.ShouldShowEffects.[1] | true |
| GArtifactRubiksCube_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactRubiksCube_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactSponge.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike05 |
| GArtifactSponge.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina1 |
| GArtifactSponge.EffectPrototypeSIDs.[2] | ArtifactProtectionRadiation1 |
| GArtifactSponge.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactSponge.ShouldShowEffects.[0] | true |
| GArtifactSponge.ShouldShowEffects.[1] | true |
| GArtifactSponge.ShouldShowEffects.[2] | true |
| GArtifactSponge.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactSponge.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactSponge.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactSponge_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike05 |
| GArtifactSponge_Fake.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina1 |
| GArtifactSponge_Fake.EffectPrototypeSIDs.[2] | ArtifactProtectionRadiation1 |
| GArtifactSponge_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactSponge_Fake.ShouldShowEffects.[0] | true |
| GArtifactSponge_Fake.ShouldShowEffects.[1] | true |
| GArtifactSponge_Fake.ShouldShowEffects.[2] | true |
| GArtifactSponge_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactSponge_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactSponge_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactHedgehog.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight2 |
| GArtifactHedgehog.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation2 |
| GArtifactHedgehog.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect2 |
| GArtifactHedgehog.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactHedgehog.ShouldShowEffects.[0] | true |
| GArtifactHedgehog.ShouldShowEffects.[1] | true |
| GArtifactHedgehog.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactHedgehog.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactHedgehog_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight2 |
| GArtifactHedgehog_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation2 |
| GArtifactHedgehog_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect2 |
| GArtifactHedgehog_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactHedgehog_Fake.ShouldShowEffects.[0] | true |
| GArtifactHedgehog_Fake.ShouldShowEffects.[1] | true |
| GArtifactHedgehog_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactHedgehog_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactBud.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike2 |
| GArtifactBud.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina2 |
| GArtifactBud.EffectPrototypeSIDs.[2] | ArtifactAddRadiation3 |
| GArtifactBud.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactBud.ShouldShowEffects.[0] | true |
| GArtifactBud.ShouldShowEffects.[1] | true |
| GArtifactBud.ShouldShowEffects.[2] | true |
| GArtifactBud.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactBud.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactBud.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactBud_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike2 |
| GArtifactBud_Fake.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina2 |
| GArtifactBud_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation3 |
| GArtifactBud_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactBud_Fake.ShouldShowEffects.[0] | true |
| GArtifactBud_Fake.ShouldShowEffects.[1] | true |
| GArtifactBud_Fake.ShouldShowEffects.[2] | true |
| GArtifactBud_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactBud_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactBud_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactPlane.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike05 |
| GArtifactPlane.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina05 |
| GArtifactPlane.EffectPrototypeSIDs.[2] | ArtifactAddRadiation1 |
| GArtifactPlane.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactPlane.ShouldShowEffects.[0] | true |
| GArtifactPlane.ShouldShowEffects.[1] | true |
| GArtifactPlane.ShouldShowEffects.[2] | true |
| GArtifactPlane.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactPlane.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactPlane.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactPlane_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike05 |
| GArtifactPlane_Fake.EffectPrototypeSIDs.[1] | ArtifactIncreaseRegenStamina05 |
| GArtifactPlane_Fake.EffectPrototypeSIDs.[2] | ArtifactAddRadiation1 |
| GArtifactPlane_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactPlane_Fake.ShouldShowEffects.[0] | true |
| GArtifactPlane_Fake.ShouldShowEffects.[1] | true |
| GArtifactPlane_Fake.ShouldShowEffects.[2] | true |
| GArtifactPlane_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactPlane_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactPlane_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactMica.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactMica.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactMica.ShouldShowEffects.[0] | true |
| CArtifactMica.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactMica_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactMica_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactMica_Fake.ShouldShowEffects.[0] | true |
| CArtifactMica_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBubble.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation2 |
| CArtifactBubble.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactBubble.ShouldShowEffects.[0] | true |
| CArtifactBubble.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBubble_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation2 |
| CArtifactBubble_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactBubble_Fake.ShouldShowEffects.[0] | true |
| CArtifactBubble_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactSlime.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactSlime.EffectPrototypeSIDs.[1] | ArtifactDurabilityIncrease1 |
| CArtifactSlime.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactSlime.ShouldShowEffects.[0] | true |
| CArtifactSlime.ShouldShowEffects.[1] | true |
| CArtifactSlime.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactSlime.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactSlime_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactSlime_Fake.EffectPrototypeSIDs.[1] | ArtifactDurabilityIncrease1 |
| CArtifactSlime_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactSlime_Fake.ShouldShowEffects.[0] | true |
| CArtifactSlime_Fake.ShouldShowEffects.[1] | true |
| CArtifactSlime_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactSlime_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactSlug.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactSlug.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactSlug.ShouldShowEffects.[0] | true |
| CArtifactSlug.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactSlug_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CArtifactSlug_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactSlug_Fake.ShouldShowEffects.[0] | true |
| CArtifactSlug_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactEchinus.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation2 |
| CArtifactEchinus.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactEchinus.ShouldShowEffects.[0] | true |
| CArtifactEchinus.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactEchinus_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation2 |
| CArtifactEchinus_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactEchinus_Fake.ShouldShowEffects.[0] | true |
| CArtifactEchinus_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactCompass.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike4 |
| GArtifactCompass.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| GArtifactCompass.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactCompass.ShouldShowEffects.[0] | true |
| GArtifactCompass.ShouldShowEffects.[1] | true |
| GArtifactCompass.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactCompass.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactCompass_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike4 |
| GArtifactCompass_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| GArtifactCompass_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactCompass_Fake.ShouldShowEffects.[0] | true |
| GArtifactCompass_Fake.ShouldShowEffects.[1] | true |
| GArtifactCompass_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactCompass_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactKryptonite.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn1 |
| CArtifactKryptonite.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| CArtifactKryptonite.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactKryptonite.ShouldShowEffects.[0] | true |
| CArtifactKryptonite.ShouldShowEffects.[1] | true |
| CArtifactKryptonite.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactKryptonite.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactKryptonite_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn1 |
| CArtifactKryptonite_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| CArtifactKryptonite_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactKryptonite_Fake.ShouldShowEffects.[0] | true |
| CArtifactKryptonite_Fake.ShouldShowEffects.[1] | true |
| CArtifactKryptonite_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactKryptonite_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactBung.EffectPrototypeSIDs.[0] | ArtifactAddRadiation1 |
| CArtifactBung.EffectPrototypeSIDs.[1] | ArtifactProtectionChemicalBurn1 |
| CArtifactBung.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease1 |
| CArtifactBung.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactBung.ShouldShowEffects.[0] | true |
| CArtifactBung.ShouldShowEffects.[1] | true |
| CArtifactBung.ShouldShowEffects.[2] | true |
| CArtifactBung.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBung.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactBung.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactBung_Fake.EffectPrototypeSIDs.[0] | ArtifactAddRadiation1 |
| CArtifactBung_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionChemicalBurn1 |
| CArtifactBung_Fake.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease1 |
| CArtifactBung_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactBung_Fake.ShouldShowEffects.[0] | true |
| CArtifactBung_Fake.ShouldShowEffects.[1] | true |
| CArtifactBung_Fake.ShouldShowEffects.[2] | true |
| CArtifactBung_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBung_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactBung_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactCrystalGlass.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina3 |
| EArtifactCrystalGlass.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| EArtifactCrystalGlass.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactCrystalGlass.ShouldShowEffects.[0] | true |
| EArtifactCrystalGlass.ShouldShowEffects.[1] | true |
| EArtifactCrystalGlass.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactCrystalGlass.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactCrystalGlass_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina3 |
| EArtifactCrystalGlass_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| EArtifactCrystalGlass_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactCrystalGlass_Fake.ShouldShowEffects.[0] | true |
| EArtifactCrystalGlass_Fake.ShouldShowEffects.[1] | true |
| EArtifactCrystalGlass_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactCrystalGlass_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactCottonWool.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn1 |
| CArtifactCottonWool.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| CArtifactCottonWool.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease1 |
| CArtifactCottonWool.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactCottonWool.ShouldShowEffects.[0] | true |
| CArtifactCottonWool.ShouldShowEffects.[1] | true |
| CArtifactCottonWool.ShouldShowEffects.[2] | true |
| CArtifactCottonWool.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactCottonWool.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactCottonWool.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactCottonWool_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn1 |
| CArtifactCottonWool_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| CArtifactCottonWool_Fake.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease1 |
| CArtifactCottonWool_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactCottonWool_Fake.ShouldShowEffects.[0] | true |
| CArtifactCottonWool_Fake.ShouldShowEffects.[1] | true |
| CArtifactCottonWool_Fake.ShouldShowEffects.[2] | true |
| CArtifactCottonWool_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactCottonWool_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactCottonWool_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| GArtifactLandSlug.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| GArtifactLandSlug.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactLandSlug.EffectOnPickPrototypeSIDs.[0] | empty |
| GArtifactLandSlug.ShouldShowEffects.[0] | true |
| GArtifactLandSlug.ShouldShowEffects.[1] | true |
| GArtifactLandSlug.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactLandSlug.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| GArtifactLandSlug_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| GArtifactLandSlug_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| GArtifactLandSlug_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| GArtifactLandSlug_Fake.ShouldShowEffects.[0] | true |
| GArtifactLandSlug_Fake.ShouldShowEffects.[1] | true |
| GArtifactLandSlug_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| GArtifactLandSlug_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactRosin.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn2 |
| CArtifactRosin.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| CArtifactRosin.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease2 |
| CArtifactRosin.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactRosin.ShouldShowEffects.[0] | true |
| CArtifactRosin.ShouldShowEffects.[1] | true |
| CArtifactRosin.ShouldShowEffects.[2] | true |
| CArtifactRosin.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactRosin.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactRosin.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactRosin_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn2 |
| CArtifactRosin_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| CArtifactRosin_Fake.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease2 |
| CArtifactRosin_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactRosin_Fake.ShouldShowEffects.[0] | true |
| CArtifactRosin_Fake.ShouldShowEffects.[1] | true |
| CArtifactRosin_Fake.ShouldShowEffects.[2] | true |
| CArtifactRosin_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactRosin_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactRosin_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactPlasticine.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn2 |
| CArtifactPlasticine.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| CArtifactPlasticine.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease2 |
| CArtifactPlasticine.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactPlasticine.ShouldShowEffects.[0] | true |
| CArtifactPlasticine.ShouldShowEffects.[1] | true |
| CArtifactPlasticine.ShouldShowEffects.[2] | true |
| CArtifactPlasticine.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactPlasticine.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactPlasticine.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactPlasticine_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn2 |
| CArtifactPlasticine_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| CArtifactPlasticine_Fake.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease2 |
| CArtifactPlasticine_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactPlasticine_Fake.ShouldShowEffects.[0] | true |
| CArtifactPlasticine_Fake.ShouldShowEffects.[1] | true |
| CArtifactPlasticine_Fake.ShouldShowEffects.[2] | true |
| CArtifactPlasticine_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactPlasticine_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactPlasticine_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactDope.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina4 |
| EArtifactDope.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| EArtifactDope.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactDope.ShouldShowEffects.[0] | true |
| EArtifactDope.ShouldShowEffects.[1] | true |
| EArtifactDope.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactDope.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactDope_Fake.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina4 |
| EArtifactDope_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation4 |
| EArtifactDope_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactDope_Fake.ShouldShowEffects.[0] | true |
| EArtifactDope_Fake.ShouldShowEffects.[1] | true |
| EArtifactDope_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactDope_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactBouncyBall.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation3 |
| CArtifactBouncyBall.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactBouncyBall.ShouldShowEffects.[0] | true |
| CArtifactBouncyBall.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactBouncyBall_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation3 |
| CArtifactBouncyBall_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactBouncyBall_Fake.ShouldShowEffects.[0] | true |
| CArtifactBouncyBall_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactDevilsMushroom.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn3 |
| CArtifactDevilsMushroom.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| CArtifactDevilsMushroom.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease3 |
| CArtifactDevilsMushroom.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactDevilsMushroom.ShouldShowEffects.[0] | true |
| CArtifactDevilsMushroom.ShouldShowEffects.[1] | true |
| CArtifactDevilsMushroom.ShouldShowEffects.[2] | true |
| CArtifactDevilsMushroom.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactDevilsMushroom.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactDevilsMushroom.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactDevilsMushroom_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionChemicalBurn3 |
| CArtifactDevilsMushroom_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| CArtifactDevilsMushroom_Fake.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease3 |
| CArtifactDevilsMushroom_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactDevilsMushroom_Fake.ShouldShowEffects.[0] | true |
| CArtifactDevilsMushroom_Fake.ShouldShowEffects.[1] | true |
| CArtifactDevilsMushroom_Fake.ShouldShowEffects.[2] | true |
| CArtifactDevilsMushroom_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactDevilsMushroom_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactDevilsMushroom_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| EArtifactChocolate.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactChocolate.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactChocolate.EffectOnPickPrototypeSIDs.[0] | empty |
| EArtifactChocolate.ShouldShowEffects.[0] | true |
| EArtifactChocolate.ShouldShowEffects.[1] | true |
| EArtifactChocolate.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactChocolate.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| EArtifactChocolate_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| EArtifactChocolate_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation1 |
| EArtifactChocolate_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| EArtifactChocolate_Fake.ShouldShowEffects.[0] | true |
| EArtifactChocolate_Fake.ShouldShowEffects.[1] | true |
| EArtifactChocolate_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| EArtifactChocolate_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactLiquidStone.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation4 |
| CArtifactLiquidStone.EffectPrototypeSIDs.[1] | ArtifactProtectionChemicalBurn4 |
| CArtifactLiquidStone.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease4 |
| CArtifactLiquidStone.EffectOnPickPrototypeSIDs.[0] | empty |
| CArtifactLiquidStone.ShouldShowEffects.[0] | true |
| CArtifactLiquidStone.ShouldShowEffects.[1] | true |
| CArtifactLiquidStone.ShouldShowEffects.[2] | true |
| CArtifactLiquidStone.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactLiquidStone.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactLiquidStone.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| CArtifactLiquidStone_Fake.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation4 |
| CArtifactLiquidStone_Fake.EffectPrototypeSIDs.[1] | ArtifactProtectionChemicalBurn4 |
| CArtifactLiquidStone_Fake.EffectPrototypeSIDs.[2] | ArtifactDurabilityIncrease4 |
| CArtifactLiquidStone_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| CArtifactLiquidStone_Fake.ShouldShowEffects.[0] | true |
| CArtifactLiquidStone_Fake.ShouldShowEffects.[1] | true |
| CArtifactLiquidStone_Fake.ShouldShowEffects.[2] | true |
| CArtifactLiquidStone_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| CArtifactLiquidStone_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| CArtifactLiquidStone_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| PArtifactBrain.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight3 |
| PArtifactBrain.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| PArtifactBrain.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect3 |
| PArtifactBrain.EffectOnPickPrototypeSIDs.[0] | empty |
| PArtifactBrain.ShouldShowEffects.[0] | true |
| PArtifactBrain.ShouldShowEffects.[1] | true |
| PArtifactBrain.ShouldShowEffects.[2] | false |
| PArtifactBrain.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| PArtifactBrain.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| PArtifactBrain.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| PArtifactBrain_Fake.EffectPrototypeSIDs.[0] | ArtifactAdditionalInventoryWeight3 |
| PArtifactBrain_Fake.EffectPrototypeSIDs.[1] | ArtifactAddRadiation3 |
| PArtifactBrain_Fake.EffectPrototypeSIDs.[2] | ArtifactPenaltyLessWeightEffect3 |
| PArtifactBrain_Fake.EffectOnPickPrototypeSIDs.[0] | FakeArtifactsPSYPoints |
| PArtifactBrain_Fake.ShouldShowEffects.[0] | true |
| PArtifactBrain_Fake.ShouldShowEffects.[1] | true |
| PArtifactBrain_Fake.ShouldShowEffects.[2] | false |
| PArtifactBrain_Fake.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| PArtifactBrain_Fake.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| PArtifactBrain_Fake.EffectsDisplayTypes.[2] | EEffectDisplayType::EffectLevel |
| PQuestArtifactScraper.EffectPrototypeSIDs.[0] | ProtectionShock1 |
| PQuestArtifactScraper.EffectPrototypeSIDs.[1] | AddRadiation1 |
| PQuestArtifactScraper.EffectOnPickPrototypeSIDs.[0] | empty |
| PQuestArtifactScraper_Fake.EffectPrototypeSIDs.[0] | ProtectionShock1 |
| PQuestArtifactScraper_Fake.EffectPrototypeSIDs.[1] | AddRadiation1 |
| PQuestArtifactScraper_Fake.EffectOnPickPrototypeSIDs.[0] | empty |
| AArtifactWeirdBall.EffectPrototypeSIDs.[0] | ArtifactProtectionStrike1 |
| AArtifactWeirdBall.EffectOnPickPrototypeSIDs.[0] | empty |
| AArtifactWeirdWater.EffectPrototypeSIDs.[0] | WeirdWaterWeightChangeCompositeEffect |
| AArtifactWeirdWater.EffectPrototypeSIDs.[1] | ArtifactProtectionRadiation1 |
| AArtifactWeirdWater.EffectOnPickPrototypeSIDs.[0] | empty |
| AArtifactWeirdNut.EffectPrototypeSIDs.[0] | DegenBleeding10 |
| AArtifactWeirdNut.EffectPrototypeSIDs.[1] | RegenHealthModifier |
| AArtifactWeirdNut.EffectOnPickPrototypeSIDs.[0] | empty |
| AArtifactWeirdFlower.EffectPrototypeSIDs.[0] | empty |
| AArtifactWeirdFlower.EffectOnPickPrototypeSIDs.[0] | empty |
| AArtifactWeirdFlower.WakeUpEffectSIDs.[0] | FlairDistanceModifierEffect |
| AArtifactWeirdBolt.EffectPrototypeSIDs.[0] | ArtifactProtectionShock1 |
| AArtifactWeirdBolt.EffectPrototypeSIDs.[1] | ArtifactProtectionBurn1 |
| AArtifactWeirdBolt.EffectPrototypeSIDs.[2] | ArtifactDegenBleeding1 |
| AArtifactWeirdBolt.EffectPrototypeSIDs.[3] | ArtifactProtectionStrike1 |
| AArtifactWeirdBolt.EffectPrototypeSIDs.[4] | ArtifactProtectionChemicalBurn1 |
| AArtifactWeirdBolt.EffectOnPickPrototypeSIDs.[0] | empty |
| AArtifactWeirdBolt.PositiveEffectPrototypeSIDs.[0] | ArtifactProtectionShock4 |
| AArtifactWeirdBolt.PositiveEffectPrototypeSIDs.[1] | ArtifactProtectionBurn4 |
| AArtifactWeirdBolt.PositiveEffectPrototypeSIDs.[2] | ArtifactDegenBleeding4 |
| AArtifactWeirdBolt.PositiveEffectPrototypeSIDs.[3] | ArtifactProtectionStrike4 |
| AArtifactWeirdBolt.PositiveEffectPrototypeSIDs.[4] | ArtifactProtectionChemicalBurn4 |
| AArtifactWeirdBolt.NegativeEffectPrototypeSIDs.[0] | Artifact_WeirdBolt_NegativeEffect_SPDrain |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[0].AnomalyType | EAnomalyType::ElectroAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[0].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[0].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[0].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[1].AnomalyType | EAnomalyType::ChemicalAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[1].ChargeQuantity | 3.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[1].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[1].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[2].AnomalyType | EAnomalyType::CarouselAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[2].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[2].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[2].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[3].AnomalyType | EAnomalyType::RazorAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[3].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[3].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[3].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[4].AnomalyType | EAnomalyType::PSYAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[4].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[4].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[4].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[5].AnomalyType | EAnomalyType::ClassicFireAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[5].ChargeQuantity | 3.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[5].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[5].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[6].AnomalyType | EAnomalyType::LightningBallAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[6].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[6].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[6].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[7].AnomalyType | EAnomalyType::SoapBubbleAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[7].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[7].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[7].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[8].AnomalyType | EAnomalyType::LavaLampAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[8].ChargeQuantity | 3.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[8].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[8].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[9].AnomalyType | EAnomalyType::ExpulsionAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[9].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[9].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[9].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[10].AnomalyType | EAnomalyType::ClickerAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[10].ChargeQuantity | 33.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[10].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[10].TimeToReduceCharge | 0.1 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[11].AnomalyType | EAnomalyType::ToxicCloudAnomaly |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[11].ChargeQuantity | 3.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[11].DamageDeflection | 1.0 |
| AArtifactWeirdBolt.AnomalyDamageDeflections.[11].TimeToReduceCharge | 0.1 |
| AArtifactWeirdKettle.EffectPrototypeSIDs.[0] | WeirdKettleEffect |
| AArtifactWeirdKettle.EffectOnPickPrototypeSIDs.[0] | empty |
| CPrologArtifactSlug.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| CPrologArtifactSlug.EffectOnPickPrototypeSIDs.[0] | empty |
| CPrologArtifactSlug.ShouldShowEffects.[0] | true |
| CPrologArtifactSlug.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| TemplateQuestArtifact.EffectPrototypeSIDs.[0] | empty |
| TemplateQuestArtifact.EffectOnPickPrototypeSIDs.[0] | empty |
| SQ13_Soul.EffectPrototypeSIDs.[0] | ArtifactIncreaseRegenStamina2 |
| SQ13_Soul.EffectPrototypeSIDs.[1] | ArtifactAddRadiation2 |
| SQ13_Soul.EffectOnPickPrototypeSIDs.[0] | empty |
| SQ13_Soul.ShouldShowEffects.[0] | true |
| SQ13_Soul.ShouldShowEffects.[1] | true |
| SQ13_Soul.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| SQ13_Soul.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| QuestArtifactCrystalThorn.EffectPrototypeSIDs.[0] | ArtifactProtectionRadiation1 |
| QuestArtifactCrystalThorn.EffectOnPickPrototypeSIDs.[0] | empty |
| QuestArtifactCrystalThorn.ShouldShowEffects.[0] | true |
| QuestArtifactCrystalThorn.ShouldShowEffects.[1] | true |
| QuestArtifactCrystalThorn.EffectsDisplayTypes.[0] | EEffectDisplayType::EffectLevel |
| QuestArtifactCrystalThorn.EffectsDisplayTypes.[1] | EEffectDisplayType::EffectLevel |
| QuestArtifactHeartofChornobyl.EffectPrototypeSIDs.[0] | Artifact_HeartOfChornobyl_RegenHP |
| QuestArtifactHeartofChornobyl.EffectOnPickPrototypeSIDs.[0] | empty |

## Interpretation, inheritance and exclusions

- The conservative ordinary-item scope is **69 candidates**, identified as non-template, non-fake, non-quest/non-prologue, non-archiartifact C/E/F/G artifact structs. This is an editor research scope, not proof that all 69 can currently be obtained in normal play. There are no separate per-rank item variants; each item has one explicit `Rarity` value and shared numbered effect references.
- `PArtifactBrain` is a separate special PSY candidate, explicitly `ArtifactSpawn = false`, reusing `GArtifactNightStar` localization, icon and mesh. `ArtifactSpawnerPrototypes.cfg` contains `BrainArtifactSpawner.ListOfArtifacts.[0] = PArtifactBrain` (source line 5026), proving an explicit reference but not normal loot availability. Exclude from an initial ordinary editor until its intended runtime role is checked.
- **71 fake structs** have `ArtifactType = EArtifactType::Fake`. Of these, 70 have `DestroyOnPickup = true` and a `FakeArtifactsPSYPoints` pickup reference. The outlier `PQuestArtifactScraper_Fake` has `DestroyOnPickup = false`, pickup `empty`, and zero cost. Do not merge fake copies into ordinary artifact rows or turn them into ordinary loot.
- Exclude `TemplateArtifact` and `TemplateQuestArtifact` from user selections. The latter is `Type = EItemType::Info`, with explicit quest flags despite inheritance from `TemplateArtifact`; an artifact-category test alone is insufficient.
- Exclude `PQuestArtifactScraper`, `CPrologArtifactSlug`, `SQ13_Soul`, `QuestArtifactCrystalThorn`, and `QuestArtifactHeartofChornobyl`. Two have misleadingly ordinary parents (`CArtifactSlug`, `EArtifactSoul`); the Heart has no item quest flag in this snapshot, but is an explicitly named quest object and referenced by quest nodes. `PQuestArtifactScraper` likewise has no quest flags, so flag-only filtering is insufficient.
- `QuestArtifactCrystalThorn` is a critical outlier: `JumpDistance = 20000`, `JumpAmount = 999`, `JumpDelay = 0.5`, `JumpSeriesDelay = 0.5`, `PlayerDistance = 100000`, `ReturnDistanceValue = 100000`, `LandingForce = 300`. Generic hopping presets must not silently flatten this behavior.
- All audited scalar fields are **explicitly owned** when present in these decoded structs; none are inherited-only. `GameData.resolve(...)` agrees with direct values. A patch to `TemplateArtifact.Weight` alone cannot override the already present `Weight` on each child. A per-item patch must name its concrete SID.
- `refurl` remains in 5 selected headers: `TemplateArtifact` references `../ItemPrototypes.cfg`, while `TemplateQuestArtifact`, `SQ13_Soul`, `QuestArtifactCrystalThorn`, and `QuestArtifactHeartofChornobyl` contain historical artifact-file URLs.; same-file `refkey` names all exist in the flattened item tree. Current resolver follows same-file refkey only; do not claim it is a general refurl resolver.
- `EffectPrototypeSIDs.[n]`, `ShouldShowEffects.[n]`, and `EffectsDisplayTypes.[n]` are aligned metadata for ordinary item effects; preserve indices and hidden auxiliary effects. Special items have additional arrays. Replacing only one scalar effect globally would affect other users of that shared effect (effect graph audit is separate).
- `AArtifactWeirdBall.Weight = 0.3` coexists with `MinWeight = 0.5`, `MaxWeight = 7.5` and damage/weight recovery coefficients. A plain item weight setting cannot promise control over its complete dynamic weight behavior. Its extra fields are real config candidates, but timing and Blueprint use need in-game tests.
- `AArtifactWeirdWater` has `MinimalDrunkenness = 15`, plus a conditional weight effect reference, and occupies 1x2 inventory cells; all other selected items occupy 1x1. `AArtifactWeirdFlower.EffectsDuration = 7200.f` and `AArtifactWeirdBolt.MaxCharge = 300` are existing global feature inputs; the native special fields permit separate controls in principle, not a new verified gameplay feature yet.
- `AArtifactWeirdBolt.bUseCharge = false` is explicit alongside charge data. Changing charge fields cannot by itself prove any runtime effect; do not promise that a charge slider works without inspecting its Blueprint behavior or testing it.
- `LifeTime` is a world artifact actor field, not evidence of inventory expiry. `Radius` is an artifact field, not the detector's detection radius. Preserve raw facts and avoid inferring player-visible units or semantics from key names alone.
- No artifact aliases are defined in `s2tweaker/names.py`, and no extracted localization archive was found in `vanilla`. `LocalizationSID` is a reference key, not a translated item name. An initial editor needs honest SID fallback or a separately verified English alias source. Do not present guessed translations as confirmed in-game names.

## Feasible initial item editor

Per-item `Weight` and `Cost` are straightforward concrete-SID patches for the 69 conservative ordinary candidates, composing with existing global factors and emitting only deviations from installed vanilla. Example hand calculation: `EArtifactFlash.Weight 0.3 * 2 = 0.6`; `EArtifactFlash.Cost 12000 * 1.5 = 18000`. These are arithmetic checks, not generated patch or in-game validation. Costs remain item base values subject to difficulty and trader pricing.

Per-item effect tuning needs the separate shared-effect audit and usually isolated effect references; it should preserve effect ordering and UI metadata. Rarity changes are not a simple power slider: rarity is an enum used by selection logic, while numbered effect strength is a separate reference. Keep ordinary effects, special archiartifact mechanics, and loot distribution as distinct implementation scopes.

All relevant item/effect files are already in `NEEDED_FILES`; this item scope alone does not require a cache-schema change. No product code, game save, installed mod or release was changed by this audit.

The [complete scalar baseline CSV](ARTIFACT_ITEM_BASELINES.csv) records each selected field for all 154 roots; empty cells mean absent fields, not zero.
