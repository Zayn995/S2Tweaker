# Native quest-giver availability markers

Audited 11 September 2026 against the installed S.T.A.L.K.E.R. 2 2.0.5
config data. This is research for comparing repeatable-job mods; no
availability-marker option or production patch was added by this audit.

## Conclusion

`EQuestNodeType::SetQuestGiver` is a native mechanism for marking an NPC as
a source of available work. The ordinary off mechanism is an **excluding
launcher on that same node**, not a guessed `Visible=false`, `Enable=false`
or `RemoveMarker` flag. Of 98 native examples, 95 have one or more explicit
`Excluding=true` launchers, commonly triggered by accepting the quest,
finishing the relevant dialog, hostility, death or a story-state change.

This is separate from a job's return objective. SetQuestGiver has
`TargetQuestGuid`, `MainQuest` and `MarkerDescription`; it has no
JournalQuestSID, JournalQuestStageSID or Markers array. It therefore does
not restore ownership of a surviving journal's return marker. The existing
[experimental return-marker repair](JOB_COMPLETED_MARKER_FOLLOWUP.md)
should remain separate.

A future "show available repeatable work" option is plausible, but cannot
be safely implemented as a permanent marker on every giver. It needs a live
offer-availability predicate, the native removal lifecycle, and explicit
checks after loading a save. This audit does not approve or implement that
feature.

## Sources and measured scope

| Relative source | Lines | Top-level structs |
|---|---:|---:|
| `vanilla/Stalker2/Content/GameLite/GameData/QuestNodePrototypes.cfg` | 2,366,619 | 84,244 |
| `vanilla/Stalker2/Content/GameLite/GameData/MarkerPrototypes.cfg` | 6,103 | 359 |

`QuestNodePrototypes.cfg` SHA-256:
`85508c26fc44b5e18e004c34dd8cbb599f463e97fdff18189c072193731eee01`.

| SetQuestGiver measurement | Result |
|---|---:|
| Native nodes / distinct target GUIDs | 98 / 82 |
| Nodes with an excluding launcher | 95 |
| Non-excluding / excluding launcher rows | 102 / 192 |
| Nodes explicitly Repeatable=true | 2 |
| Nodes with LaunchOnQuestStart on SetQuestGiver itself | 0 |
| Nodes with a Launchers child / empty Launchers scalar | 97 / 1 |
| MainQuest=false / true | 95 / 3 |
| Empty MarkerDescription | 92 |
| Nodes using refkey/refurl attributes | 0 |
| Nodes owned by the eight repeatable giver quests or their 69 jobs | 0 |

All 98 nodes explicitly define TargetQuestGuid, MainQuest and
MarkerDescription. The six nonempty descriptions are `Merc` twice,
`MainQuest` once, `SideQuest` once and `TestScenarioMQ` twice. These are not
evidence that arbitrary descriptions are localized or that a display style
can substitute for a journal stage. Ninety-seven nodes define
NodePrototypeVersion; `SQ01_OWL_SetQuestGiver_Warlock` omits it.

MarkerPrototypes contains static/service/region/location categories and no
quest-giver or journal-objective prototype in this dataset. SetQuestGiver,
SetJournal and ShowMarker are separate native node types. There is no
RemoveQuestGiver node type in the complete quest-node inventory.

## Verified native off paths

### Acceptance excludes the availability marker

`E02_SQ01_SetQuestGiver_BP_NPC_Zorik`, source line 183070:

- `TargetQuestGuid = BE942D4E418586FD35EBF59DFC2AEDA2`;
- `MainQuest = false`, `MarkerDescription` empty;
- `Launchers.[0].Excluding = false`, from a conversation invitation;
- `Launchers.[1].Excluding = true`;
- `Launchers.[1].Connections.[0].SID = E02_SQ01_Quest_Start`;
- `Launchers.[3].Excluding = true`, from a player-aggression bridge event.

The quest-start edge shuts down the availability node rather than
modifying its target or converting it into a return-stage marker.

### Explicit availability and terminal-state guards

`E10_SQ01_P_SetQuestGiver_BP_NPC_ArhipLishajnik_1`, line 754723, has both a
normal activation path and a state-checked activation path. Its latter
activation launcher `[1]` requires an OnTick event and
`E10_SQ01_P_SetQuestGiver_BP_NPC_ArhipLishajnik_1_Pin_1` together.
That condition requires journal quest `E10_MQ01` to be Finished.

Its off launcher is:

- `Launchers.[2].Excluding = true`;
- `Connections.[0].SID = E10_SQ01_P_SetQuestGiver_BP_NPC_ArhipLishajnik_1_Pin_2`;
- `Connections.[1].SID = E10_SQ01_P_OnTickEvent_1`.

The off condition's `Conditions.[0].[0]` and `[0].[1]` explicitly test
`E10_SQ01` for Active or Finished with
`ConditionCheckType = EConditionCheckType::Or`. This is concrete evidence
of an availability marker being excluded once that work is already taken
or finished. It is not a general predicate for arbitrary repeatable jobs.

### Marker-node state can participate in story logic

`E02_SQ02_SetQuestGiver_Malar`, line 188752, activates only after a
PersonalRelationship condition greater than Disaffection. Its excluding
launchers `[1]` and `[2]` respectively observe the main dialog finishing
and Malar's force-hide node finishing, each through a tick/condition pair.

`E02_SQ02_Technical_CanelQuest_Pin_0.Conditions.[0].[0]`, line 188941,
explicitly tests:

- `ConditionType = EQuestConditionType::NodeState`;
- `TargetNode = E02_SQ02_SetQuestGiver_Malar`;
- `NodeState = EQuestNodeState::Excluded`.

This is the only explicit reference back to a SetQuestGiver node found in
other quest-node scalar values. It is evidence against globally disabling
native availability markers: at least one native quest uses the marker
node's state in its own logic. This audit found no BridgeCleanUp resetting
a SetQuestGiver node's result, and no native consumer chain launched by a
SetQuestGiver output.

### Repeatable example and exceptions

`EQ54_C3_SetQuestGiver_BP_NPC_EQ54_FreedomKoren`, line 1176053, is
Repeatable=true. It activates from `EQ54_C3_Start` and has three excluding
launchers: main conversation completion, the NPC becoming an enemy, and
the NPC's death. This supports repeatable node wiring with explicit
removal; it does not prove arbitrary reactivation after exclusion or save
restoration.

The three exceptions with no excluding launcher must not be generalized:

| Node | Exception |
|---|---|
| `EQ32_P_SetQuestGiver_BP_NPC_ANCQ02_Leshyi` | Has an activation edge, but both local End nodes have empty launchers and ExcludeAllNodesInContainer=false. No clean local off path was established. |
| `SQ13_OWL_SetQuestGiver_not_set!` | Has an activation edge; its parent has a populated End with ExcludeAllNodesInContainer=true. Another native marker targets the same NPC. |
| `SQ98_SetQuestGiver_BP_NPC_SQ98_Medulin` | Repeatable=true but Launchers is empty; there is no explicit local activation edge. Its parent has an excluding End. This is not a working always-on template. |

## Save/load evidence and limits

`EQ68_SetQuestGiver_Zivotko.Launchers.[7]`, source line 1236108, is an
explicit excluding edge from `EQ68_If_SaveLoad_Fix` / `True`.

The path is:

`EQ68_OnTickEvent_NewFix_ToExcludeGoldenPass`
→ `EQ68_Technical_SaveLoadFix`
→ `EQ68_If_SaveLoad_Fix`
→ the existing SetQuestGiver node's excluding launcher.

The tick is LaunchOnQuestStart=true and TrackBeforeActive=false. The If
checks the native Excluded state of four dialog/comment nodes. These exact
nodes are `EQ68_SetComment_KubrakAfterShootAboutPay`,
`EQ68_SetComment_AfterPassGood`, `EQ68_SetDialog_after_shooting`, and
`EQ68_SetDialog_EQ68_Comment_SkifTooFar`.

The name is a native label, not a test result. The graph demonstrates a
state-based recovery/removal path in addition to event-driven exclusions.
It does not establish how dynamically added marker nodes serialize,
whether changing a generated pak removes a previously saved marker, or
whether multiple owners targeting the same NPC are reference-counted.
Those behaviors still require gameplay tests.

## Shared actor risk

Three native SetQuestGiver nodes already target repeatable-job giver actors:

| Native marker | Target / ordinary repeatable giver |
|---|---|
| `SQ01_OWL_SetQuestGiver_Warlock` | `0D0457214D9959BD245322A0F6502D49` / Warlock |
| `SQ89_P_SetQuestGiver_BP_NPC_Sidorovich` | `50D530D64ECEC8C5C8499C95EA5BA59B` / Sidorovich |
| `SQ90_SetQuestGiver_not_set!` | `1792AC6A4539617277E8189ABA6B917E` / Rostok giver |

They belong to different story/side quests. Their absence from the RSQ
graphs does not mean those actors never have native availability markers.
A new RSQ availability marker might overlap these native markers or a
return marker. No safe ownership isolation or independent removal behavior
for that overlap was proven by config inspection. Do not modify those
native story markers to clear a new marker.

## Necessary availability gate for a future option

The existing eight giver/69-slot discovery can identify the NPC and the
currently selected job pool, but **no-active-jobs** is not equivalent to
**work available**. It can be true during cooldown or after all selectable
jobs have been exhausted. Conversely, multi-job mode can offer another
job while a different job is already active.

The native round cap is also not a direct availability predicate.
For example, `RSQ04_If_LessThen3Tasks.Conditions.[0].[0]` tests
`RSQ04_DrabadansQuests < 3`, but `RSQ04_Inc_GlobalVariable_1` increments that
variable from `RSQ04_Add_C01`, before the acceptance condition starts the
job container. The cap controls pool construction. A filled pool can have
selectable jobs when Less 3 is already false.

Actual menu options use the selected slot's Bridge result. In
`DialogPrototypes.cfg`, Drabadan's first option requires:

- `ConditionType = EQuestConditionType::Bridge`;
- `ConditionComparance = EConditionComparance::Equal`;
- `LinkedNodePrototypeSID = RSQ04_Add_C01`;
- `CompletedNodeLauncherNames.[0]` empty.

Its first occurrence is at line 674987; other options use their own live
Add-node SID. A future availability gate would need the live OR of valid
offer-slot predicates together with the giver's current offer/story
lifecycle. It must account for accepted slots being cleared by the
multi-job path, exhausted pools, cooldown, cancellation, parent End,
hostility, death and story shutdown. A persistent marker derived only from
the giver's existence, one initial Start event, the cap or journal Active
is not enough.

This audit establishes native ingredients, not a fully verified new
repeatable-availability state machine. No such feature is added to the
current repair.

## Warnings and follow-up boundary

- Do not substitute SetQuestGiver for SetJournal return markers or claim
  that it fixes issue #9's completed-sibling marker disappearance.
- Do not invent a visibility/removal field or change the target to a new
  GUID. There is no supported marker identity override in these nodes.
- Preserve existing story marker nodes and all their excluding launchers.
- Do not enable every marker on quest start, suppress cleanup or use
  repeated ticks without a verified on/off state machine.
- A future test must cover offer available, one accepted with another
  available, all offers exhausted, cooldown, death/hostility/story shutdown,
  save/reload, and turning the option back off. Check story and return
  markers separately during overlap.

Private audit scripts and exact node/source-link data are under
`out/issue9_reference_deepening/native_markers/`. No production files,
settings, tests or installed paks were changed by this research.

## Complete native SetQuestGiver inventory

The table records direct native values. `—` means an empty description or
an omitted Repeatable field; it does not assert a runtime default. `Off`
counts explicit Excluding=true launcher rows on that node.

| Node SID | Line | TargetQuestGuid | MainQuest | MarkerDescription | Repeatable | Off |
|---|---:|---|---|---|---|---:|
| `E02_SQ01_SetQuestGiver_BP_NPC_Zorik` | 183070 | `BE942D4E418586FD35EBF59DFC2AEDA2` | false | — | — | 2 |
| `E02_SQ02_SetQuestGiver_Malar` | 188752 | `2371A37D416253FE1B2B2F92E4A750EA` | false | — | — | 2 |
| `E04_SQ02_SetQuestGiver_BP_ProfLodochka` | 312129 | `F337B7D84CABA3335D3DF0BB35FB4C83` | false | — | — | 1 |
| `E05_EQ03_SetQuestGiver_BP_NPC_E05_EQ03_Kemarik` | 321446 | `474529BA403A9C7A56D9D2A2637F5953` | false | — | — | 1 |
| `E05_MQ01_SetQuestGiver_Kudravyj` | 340418 | `8D689C424B0A4208D4C9FE8CB1E3AA25` | false | — | — | 1 |
| `E05_SQ01_OWL_SetQuestGiver_BP_NPC_VartaMedic` | 373319 | `850DAE85431B38C4C92869AF33C8E820` | false | — | — | 1 |
| `E05_SQ03_P_SetQuestGiver_BP_IKARTechician` | 376998 | `0027C2C14F2D5F7D31FF7F9AC15B82CA` | false | — | — | 1 |
| `E05_SQ03_P_SetQuestGiver_BP_IKARTechician_start` | 377036 | `0027C2C14F2D5F7D31FF7F9AC15B82CA` | false | — | — | 1 |
| `E05_SQ04_SetQuestGiver_BP_NPC_VartaCaptainSenkevich_ST207546` | 379981 | `2539474544EA13AB7CF4F89D6EE01D30` | false | — | — | 1 |
| `E07_SQ01_SetQuestGiver_SereneGladeBatya` | 555472 | `9E62763F44CA4F403B9631998C383627` | false | — | — | 3 |
| `E09_EQ01_SetQuestGiver_BP_NPC_Lazarenko_E09_EQ01` | 694357 | `2C3CA6DF49E345DC72E90CAD4B7C1F81` | false | — | — | 2 |
| `E09_EQ02_SetQuestGiver_BP_NPC_Hollywood_E09_EQ02` | 700652 | `21C72A7B4196250BB607F6B582FC5E46` | false | — | — | 1 |
| `E10_SQ01_SetQuestGiver_BP_NPC_ArhipLishajnik` | 753387 | `7E3F3EDA434D25066C400C8D8F4CFCE3` | false | — | — | 1 |
| `E10_SQ01_P_SetQuestGiver_BP_NPC_ArhipLishajnik` | 754586 | `7E3F3EDA434D25066C400C8D8F4CFCE3` | false | — | — | 3 |
| `E10_SQ01_P_SetQuestGiver_BP_NPC_ArhipLishajnik_1` | 754723 | `7E3F3EDA434D25066C400C8D8F4CFCE3` | false | — | — | 2 |
| `EQ04_SetQuestGiver_not_set!` | 982907 | `280CFA274909BEB6DA2DABA87AADFFAF` | false | — | — | 2 |
| `EQ08_SetQuestGiver_BP_NPCPlaceholder_EQ08_Trader` | 996328 | `1EC2F53C4CA500324CAA9FB063FF36E4` | false | — | — | 3 |
| `EQ10_SetQuestGiver_VitkaQuestGiver` | 1001981 | `2E2F7EAE48D41772E50D49BEF0D3F98F` | false | — | — | 1 |
| `EQ11_SetQuestGiver_BP_NPC_EQ11_Mol` | 1017192 | `237034C041486C7795C0A2B95A207FE0` | false | Merc | — | 3 |
| `EQ11_SetQuestGiver_BP_NPC_EQ11_Mol_Again` | 1018248 | `237034C041486C7795C0A2B95A207FE0` | false | Merc | — | 2 |
| `EQ14_SetQuestGiver_BP_NPC_EQ14_Kuza` | 1036935 | `60C352E449027BE06F90E3A499399970` | false | — | — | 1 |
| `EQ140_SetQuestGiver_BP_NPC_EQ140_IluhaVorobej` | 1040605 | `35CEB01E4AA0139E57FD758DE0C0D992` | false | — | — | 3 |
| `EQ148_SetQuestGiver_BP_NPC_EQ148_Kostas` | 1058312 | `7151A8854C64E5DB2408EBA8D09AA951` | false | — | — | 2 |
| `EQ156_SetQuestGiver_BP_NPC_EQ156_Moroz` | 1077430 | `1CD199C640A149B33EA11D9ED0136555` | false | — | — | 4 |
| `EQ16_SetQuestGiver_not_set!` | 1081125 | `F056EDD44714FECA773E00AC2ED27024` | false | — | — | 1 |
| `EQ163_SetQuestGiver_BP_NPC_EQ163_SerjantNecereda` | 1087759 | `7B885CAC4CFB274CB032118A63D7A029` | false | — | — | 2 |
| `EQ164_SetQuestGiver_VadikPetard` | 1090292 | `C33BBC0D4776BE65A20F4996924702C7` | false | — | — | 1 |
| `EQ166_SetQuestGiver_BP_NPC_OtecValerian` | 1103005 | `FA4691D847EC726AE197F5B50E496BB7` | false | — | — | 1 |
| `EQ26_SetQuestGiver_BP_NPC_EQ26_LevsaZombie` | 1109739 | `8D3166D14927344EFB45FEBABA87BC5B` | false | — | — | 3 |
| `EQ32_P_SetQuestGiver_BP_NPC_ANCQ02_Leshyi` | 1116572 | `EE06C0D34C05E707D0F50D86BD81A1E8` | false | — | — | 0 |
| `EQ35_SetQuestGiver_BP_NPC_EQ35_Master` | 1124814 | `943EF8C943A0E97F3C8838BA5F7BEC64` | false | — | — | 3 |
| `EQ35_SetQuestGiver_BP_NPC_EQ35_Master_1` | 1126913 | `943EF8C943A0E97F3C8838BA5F7BEC64` | false | — | — | 2 |
| `EQ35_SetQuestGiver_BP_NPC_EQ35_Master_2` | 1129429 | `943EF8C943A0E97F3C8838BA5F7BEC64` | false | — | — | 2 |
| `EQ36_SetQuestGiver_BP_NPC_EQ36_Kucer` | 1134836 | `237397294F8D880D237FC8B025B0641C` | false | — | — | 3 |
| `EQ37_SetQuestGiver_BP_NPC_EQ37_Grom` | 1137531 | `3B0EB5F948C3D63D580404896F7BC7E7` | false | — | — | 3 |
| `EQ43_SetQuestGiver_BP_NPC_EQ43_Kirya` | 1145600 | `794BAEBA40D338410B29ECB38D39A923` | false | — | — | 3 |
| `EQ50_SetQuestGiver_BP_NPC_EQ50_SergSemidomov` | 1151044 | `3C2B68B243592BA2C6576B82CB1673C3` | false | — | — | 4 |
| `EQ51_SetQuestGiver_BP_NPC_EQ51_TemaJet` | 1158888 | `7CA95E4644DFFD9ABC308A82121DBBBE` | false | — | — | 2 |
| `EQ52_P_SetQuestGiver_BP_NPC_EQ52_Ura_Fantomas` | 1169075 | `B80D7683401F5D93E99169B54CA72CA1` | false | — | — | 2 |
| `EQ54_C01_SetQuestGiver_BP_NPC_EQ54_FreedomKoren` | 1175822 | `AAD363C24D535A1F3373B5B145539F73` | false | — | — | 3 |
| `EQ54_C3_SetQuestGiver_BP_NPC_EQ54_FreedomKoren` | 1176053 | `AAD363C24D535A1F3373B5B145539F73` | false | — | true | 3 |
| `EQ55_SetQuestGiver_BP_NPC_EQ55_LenaShprot` | 1179286 | `1A9159704726B34CDB0BA4B757997F4E` | false | — | — | 1 |
| `EQ57_SetQuestGiver_BP_NPC_Borodulin_EQ57` | 1192367 | `ED952073472128F876D41792BF89C360` | true | — | — | 3 |
| `EQ60_P_SetQuestGiver_BP_NPC_EQ60_Vovchik` | 1205112 | `742A83D945A553731D2C07B0DB864905` | false | — | — | 3 |
| `EQ65_SetQuestGiver_BP_NPC_EQ65_Piavka` | 1219788 | `EDC23D0C4A95B7073CB82CAFAA2C622E` | false | — | — | 1 |
| `EQ68_SetQuestGiver_Zivotko` | 1236108 | `26B70A3F4F7DD46A41BCBAB6F625C2D3` | false | — | — | 7 |
| `EQ70_SetQuestGiver_BP_NPC_EQ70_Strateg` | 1240987 | `0A0AA6EA44E34BF9627857BFE185263F` | false | — | — | 2 |
| `EQ71_SetQuestGiver_BP_NPC_EQ71_KiruhaMelkij` | 1243861 | `FB1011874FD257E7CAAA628B9424888E` | false | — | — | 3 |
| `EQ74_SetQuestGiver_BP_NPC_EQ74_Jitnichenko` | 1253464 | `58FDDE084FAAE22237825A8E8BBE26D9` | false | — | — | 3 |
| `EQ75_P_SetQuestGiver_BP_NPC_EQ75_Bynya` | 1259385 | `9CB7D7F34F3F228EA7D840AA4B86B44C` | false | — | — | 3 |
| `EQ82_SetQuestGiver_BP_NPC_EQ82_Efim` | 1268736 | `4B75588748187365A596D694CD801B41` | false | — | — | 1 |
| `EQ97_SetQuestGiver_NPCPlaceholder_EQ97_Bespredel` | 1287455 | `36285D8844AD030F2C59DEB05AFCFA3C` | false | — | — | 4 |
| `EQ98_SetQuestGiver_NPC_EQ98_VovaAmalgama` | 1293731 | `8519EC2D4EC2D53F7DD3FDAA2406AD99` | false | — | — | 2 |
| `SQ01_OWL_SetQuestGiver_Warlock` | 1810376 | `0D0457214D9959BD245322A0F6502D49` | false | — | — | 1 |
| `SQ02_OWL_SetQuestGiver_Mit` | 1817969 | `B2FFD44D4C8ED41E84F7758A546C1EA7` | false | — | — | 1 |
| `SQ03_OWL_SetQuestGiver_Linza` | 1834901 | `68E561A54F2C212446EB0A8CA539D385` | false | — | — | 1 |
| `SQ06_OWL_SetQuestGiver_BP_NPC_Tihiy` | 1851932 | `85105C034927E31E5BEC6B8797F1A16F` | false | — | — | 1 |
| `SQ10_SetQuestGiver_Jamper` | 1858807 | `AD0A988342B4B1B64C6B509300987A54` | false | — | — | 3 |
| `SQ100_P_SetQuestGiver_BP_NPC_Banzai` | 1863650 | `67BDA3C2414975CF53CA8BB0FA1890E0` | false | — | — | 1 |
| `SQ102_SetQuestGiver_SQ102_BP_NPCPlaceholder_Vozatij` | 1878452 | `3450989648AD9787C64E9DA03D9B897D` | false | — | — | 1 |
| `SQ103_P_SetQuestGiver_BP_NPC_Konder` | 1908636 | `89C2E4ED4585164E4C09019157B846A5` | false | — | — | 1 |
| `SQ13_OWL_SetQuestGiver_not_set!` | 1929025 | `B65CEEE64B2EF4E36EA410A21E3E7F19` | false | — | — | 0 |
| `SQ13_OWL_SetQuestGiver_BP_NPC_Matiush` | 1929064 | `B65CEEE64B2EF4E36EA410A21E3E7F19` | false | — | — | 1 |
| `SQ18_OWL_SetQuestGiver_Boroda` | 1944660 | `CE8D61C34FC45128DE0025925F36A232` | false | — | — | 1 |
| `SQ20_SetQuestGiver_BP_NPCPlaceholder_Arnie` | 1960704 | `AF6D4A5540A555F7663A6FA4A26001DD` | false | — | — | 2 |
| `SQ20_SetQuestGiver_BP_NPCPlaceholder_Arnie_1` | 1964894 | `AF6D4A5540A555F7663A6FA4A26001DD` | false | — | — | 1 |
| `SQ20_P_SetQuestGiver_BP_NPCPlaceholder_Ganza` | 1972132 | `26B285DC4F7090B7FBB2AD92B89D6FE0` | false | — | — | 2 |
| `SQ20_P_SetQuestGiver_BP_NPCPlaceholder_Ganza_1` | 1977570 | `26B285DC4F7090B7FBB2AD92B89D6FE0` | false | — | — | 1 |
| `SQ25_OWL_SetQuestGiver_Start` | 1992755 | `B0A85E044F53CCE1C975D5ADAE49D160` | false | — | — | 2 |
| `SQ47_C01_SetQuestGiver_SQ47_BP_NPCPlaceholder_Akopan` | 2009050 | `8A07D2D64D6907493F0C1DB39A9F456A` | false | — | — | 1 |
| `SQ47_OWL_SetQuestGiver_not_set` | 2015315 | `AA331FDF415DC569809A46BEB3E95450` | false | — | — | 3 |
| `SQ47_OWL_SetQuestGiver_SQ47_BP_NPCPlaceholder_Zahar` | 2017134 | `AA331FDF415DC569809A46BEB3E95450` | false | — | — | 3 |
| `SQ50_OWL_SetQuestGiver_Sonya` | 2021254 | `494BC23B4528A02FB65F3CA22E549E39` | false | — | — | 1 |
| `SQ50_OWL_SetQuestGiver_Sultan` | 2021283 | `C0B669CE4CC8B6F6A93774943ADDAC8B` | false | — | — | 1 |
| `SQ81_SetQuestGiver_BP_NPC_Skadovsk_Bartender` | 2032254 | `494BC23B4528A02FB65F3CA22E549E39` | false | — | — | 1 |
| `SQ86_SetQuestGiver_SQ86_BP_NPC_SQ86_Genij` | 2041841 | `153027874EC8559F801C37982D03FABB` | false | — | — | 3 |
| `SQ87_P_SetQuestGiver_Zhenya` | 2059444 | `64FE31A049734D16CF56AE907CF4BE52` | false | — | — | 5 |
| `SQ88_SetQuestGiver_BP_NPC_SQ88_Kuvalda` | 2072506 | `3CBECE9B4CA9E18227E59CAE8E27F340` | false | — | — | 2 |
| `SQ89_P_SetQuestGiver_BP_NPC_Sidorovich` | 2096576 | `50D530D64ECEC8C5C8499C95EA5BA59B` | false | — | — | 1 |
| `SQ90_SetQuestGiver_BP_NPC_SQ90_Freedom_Zazim` | 2104553 | `856944C74DC8A67D900B688AE31A7975` | false | — | — | 2 |
| `SQ90_SetQuestGiver_not_set!` | 2104907 | `1792AC6A4539617277E8189ABA6B917E` | false | — | — | 1 |
| `SQ91_SetQuestGiver_Rodetsky` | 2119459 | `53982D75434381853FBAD7A0BA331066` | false | — | — | 3 |
| `SQ92_SetQuestGiver_YarikMangust` | 2129431 | `CB1A656047F60ECE70F46996E619786D` | false | — | — | 2 |
| `SQ93_SetQuestGiver_BP_NPC_Malahit_Hub_Trader` | 2140002 | `C3CD7B514534EF47CDD8478E1FF7A0FF` | false | — | — | 1 |
| `SQ94_P_SetQuestGiver_BP_NPC_Gonta` | 2165726 | `5D3B3203402D88C59FF8ADB98752A28F` | false | — | — | 3 |
| `SQ95_P_SetQuestGiver_Banzai` | 2180368 | `A1207A0D49AD8CAEE19390A53A07B8A1` | false | — | — | 1 |
| `SQ96_C02_SetQuestGiver_BP_NPC_Banzai` | 2185506 | `67BDA3C2414975CF53CA8BB0FA1890E0` | false | — | — | 5 |
| `SQ96_C02_SetQuestGiver_BP_NPCPlaceholder_Banzai` | 2185995 | `9594C469421CCBD20848A684D2E86E37` | false | — | — | 5 |
| `SQ96_C02_SetQuestGiver_BP_NPC_Banzai_1` | 2186901 | `67BDA3C2414975CF53CA8BB0FA1890E0` | false | — | — | 4 |
| `SQ96_C03_SetQuestGiver_BP_NPC_Banzai` | 2187982 | `67BDA3C2414975CF53CA8BB0FA1890E0` | false | — | — | 1 |
| `SQ97_SetQuestGiver_BP_NPCPlaceholder_Scoutmaster_1` | 2193161 | `DC6E432640E882FD3D62FD9B5297B9FD` | false | — | — | 1 |
| `SQ97_SetQuestGiver_BP_NPCPlaceholder_Scoutmaster_2` | 2193634 | `DC6E432640E882FD3D62FD9B5297B9FD` | false | — | — | 1 |
| `SQ97_P_SetQuestGiver_BP_NPC_Vozatiy` | 2194951 | `EDF684D64C119037FAC6C1948632D711` | false | — | — | 2 |
| `SQ98_SetQuestGiver_BP_NPC_SQ98_Medulin` | 2198517 | `3BA9067D49A7CA107FBA4892C885A7D0` | false | — | true | 0 |
| `UI_QTC_Quest_SetQuestGiver_BP_NPCPlaceholder6` | 2303163 | `148E50A7416351CD27D8D899534F3C70` | true | MainQuest | — | 1 |
| `UI_QTC_Quest_SetQuestGiver_BP_NPCPlaceholder7_1` | 2304725 | `54D1988C45C6E30D82D678A5E4632DAC` | false | SideQuest | — | 1 |
| `UI_QTC_TestCase6_main_SetQuestGiver_BP_NPCPlaceholder17` | 2310464 | `2C9A83A14F5E982F28B3518B9ECDDFC0` | true | TestScenarioMQ | — | 1 |
| `UI_QTC_TestCase6_main_SetQuestGiver_BP_NPCPlaceholder18` | 2310600 | `EC71771D49446A954EF55BA5F3D38D4E` | false | TestScenarioMQ | — | 1 |
