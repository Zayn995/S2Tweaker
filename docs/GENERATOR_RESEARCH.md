# Generator-Block: Datenlage (Loot, Drops, Händler, Verstecke)

Recherche-Stand **2026-09-01**, erstellt mit der Skill `research-cfg-block`
(6 parallele Agents auf den lokalen `vanilla/`-Dateien). **Kein Code** — dieses
Dokument ist die Grundlage für eine spätere Umsetzung mit `add-tweak`.

> **Nachtrag 01.09. (Stufe 1+2 sind gebaut).** Der gegnerische Review vor dem
> Commit hat vier Lücken in diesem Dokument gefunden — Geld existiert auch als
> *Item* (`MoneyCommon/Rare/Epic/Legendary`, Effekt `EEffectType::AddMoney`),
> es gibt einen **zweiten** Quest-Marker `IsQuestItemPrototype` (291 Items
> tragen nur ihn), die Händler-Hülle darf ihre Sperre nicht transitiv
> weitergeben, und der Namensfilter gehört auch auf Item-SIDs. Details und die
> daraus gebaute Filterlogik: `docs/ROADMAP.md`, Abschnitt „Was der Review an
> der Recherche korrigiert hat", sowie `README.md`. Zwei Angaben unten sind
> falsch: `LesserZone_Cabin` gibt es **nicht** 4× als gleichnamigen Schlüssel
> (die Datei hat 0 doppelte Top-Level-Schlüssel), und `Electrocollar` ist
> **kein** Quest-Item (`IsQuestItem = false`).

Alle Zahlen sind gezählt, nicht geschätzt; die Zählmethode steht jeweils dabei.
Werte gehören in dieses Dokument, **nicht in den Code** — dort immer live über
`gd.resolve(...)` lesen (eiserne Regel, siehe CLAUDE.md).

---

## Kurzfassung

| Frage | Antwort |
|---|---|
| Loot-Mengen regelbar? | **Ja**, aber nur mit zweistufigem Sicherheitsfilter (Name + Item-Inhalt). 2.049 von 3.085 Generatoren sind sicher. |
| Zustand gedroppter Waffen regelbar? | **Ja**, technisch sauber — aber teuer: bis zu ~23.000 Patch-Zeilen, weil kein Wert vererbt wird. |
| Händler-Bestände regelbar? | **Ja, als eigener Regler** — Handel und NPC-Loot sind fast disjunkt (Schnittmenge 6 von 95 bzw. 963 Generatoren). |
| Versteck-Inhalte regelbar? | **Ja, und das ist der billigste und sicherste Einstieg**: 19 Structs, nachweislich 0 Quest-Items, 0 Unikate. |
| „Mehr Leichen-Loot je Schwierigkeitsgrad"? | **So nicht verdrahtet** — der Vanilla-Anker existiert nur auf Easy und Medium (siehe unten). |

**Empfehlung: in zwei Stufen bauen.** Stufe 1 = `StashPrototypes.cfg`
(Verstecke + Leichen-Loot), klein, sicher, sofort testbar. Stufe 2 = die
Mengen im großen Generator, mit dem unten beschriebenen Filter. Der
Zustands-Regler und die Händler-Bestände sind je ein eigenes Thema danach.

---

## 1. Die beiden Dateien

| Datei | Zeilen | Top-Level-Structs | Größe |
|---|---|---|---|
| `ItemGeneratorPrototypes.cfg` | 277.318 | 3.085 | 9,3 MB |
| `StashPrototypes.cfg` | 10.681 | 19 | 0,4 MB |

Dazu als Nachbarn: `DifficultyPrototypes.cfg` (11 Structs, enthält
`CorpseSmartLoot`), `TradePrototypes.cfg` (74 Structs, Händler-Verknüpfung),
`ObjPrototypes.cfg` (1.659 NPC-Prototypen, Loadout-Verknüpfung),
`ItemPrototypes.cfg` (Quest-Item-Marker), `SpawnActorPrototypes.cfg`
(Versteck-Zuweisung).

---

## 2. Aufbau von ItemGeneratorPrototypes.cfg

Fünf Ebenen, Einrückung immer 3 Leerzeichen, keine Tabs, kein CR:

```
Prototyp                                   ← Patch-Schlüssel
   ItemGenerator | MoneyGenerator
      [N]  Slot mit Category + Filtern
         PossibleItems
            [M]  einzelner Kandidat mit den Zahlen
```

Beispiel (Zeilen 32–58, `SimpleFoodGenerator`, komplett selbstdefiniert):

```
SimpleFoodGenerator : struct.begin
   SID = SimpleFoodGenerator
   ItemGenerator : struct.begin
      [0] : struct.begin
         Category = EItemGenerationCategory::Consumable
         PossibleItems : struct.begin
            [0] : struct.begin
               ItemPrototypeSID = Bread
               Weight = 4
               MinCount = 1
               MaxCount = 1
            struct.end
            ...
```

**Nur 28 verschiedene Feldnamen** in 153.578 `Key = Wert`-Zeilen. Häufigkeit:

| Feld | Anzahl | Ebene |
|---|---|---|
| `ItemPrototypeSID` | 23.469 | Item |
| `Weight` | 17.520 | Item |
| `Category` | 13.940 | Slot |
| `MinDurability` / `MaxDurability` | 12.987 / 12.984 | Item |
| `AmmoMinCount` / `AmmoMaxCount` | 12.375 / 12.371 | Item |
| `Chance` | 10.587 | Item |
| `MinCount` / `MaxCount` | 6.962 / 6.147 | Item **und** MoneyGenerator |
| `PlayerRank` | 6.941 | Slot |
| `ItemGeneratorPrototypeSID` | 4.752 | Item (Sub-Generator) |
| `SID` | 3.085 | Prototyp |
| `SpecificRewardSound` | 2.485 | Prototyp |
| `Diff` | 2.364 | Slot |
| `bAllowSameCategoryGeneration` | 2.003 | Slot |
| `bRequireWeapon` | 1.103 | Item |
| `RefreshTime` | 799 | Prototyp (`1d` 794×, `1h` 5×) |
| `weight` (klein!) | 152 | Item — **Vanilla-Tippfehler** |
| `ID` | 66 | Prototyp |
| `bUnloadedWeapon` / `ReputationThreshold` / `AmmoMaxcount` | 5 / 4 / 4 | selten |
| `bRequireAmmo` / `GeneratedItems` / `Binoculars_03` | je 1 | kaputte Vanilla-Daten |

16 Kategorien (`EItemGenerationCategory::…`), im sicheren Rest verteilt als:
WeaponPrimary 3.858, SubItemGenerator 3.334, BodyArmor 1.670, Head 1.255,
Detector 838, Artifact 817, Consumable 297, WeaponPistol 210, Junk 150,
Ammo 144, Attach 102, WeaponSecondary 98, Mask 75, NightVision 30,
MutantLoot 15, None 1.

---

## 3. Die Stellschrauben

### 3.1 Stückzahlen — `MinCount` / `MaxCount`

Pfad: `<Prototyp>.ItemGenerator[i].PossibleItems[j].MinCount`

Die 6.962 `MinCount`-Zeilen verteilen sich auf **fünf verschiedene Pfadformen**,
die man nicht vermischen darf:

| Pfadform | MinCount | MaxCount | Bedeutung |
|---|---|---|---|
| `…PossibleItems[j]` | 6.479 | 5.665 | **Stückzahl (das Ziel)** |
| `<Prototyp>.MoneyGenerator` | 372 | 372 | **Geldbetrag — nie mitskalieren!** |
| `…ItemGenerator.Consumable.PossibleItems[j]` | 83 | 83 | benannter statt indizierter Slot |
| `…PossibleItems[j].Upgrades` | 20 | 19 | Waffen-Upgrades |
| `…PossibleItems[j].Attaches` | 8 | 8 | Anbauteile |

Verteilung in PossibleItems (n = 6.590 / 5.775):
`MinCount` 1 = 4.289 (65,1 %), 2 = 400, 10 = 342, 5 = 301, 30 = 195 …
`MaxCount` 1 = 3.070 (53,2 %), 2 = 494, 3 = 333, 10 = 278, 5 = 231 …
Häufigstes Paar (1,1) = 3.029 (52,7 %). **3.895 feste Mengen (Min == Max),
1.853 echte Spannen, 0 Fälle mit Min > Max.**

**814 Einträge haben `MinCount` OHNE `MaxCount`** (807× mit Wert 1) —
umgekehrt kein einziger. Ein Regler, der nur `MaxCount` anfasst, übersieht sie.

### 3.2 Munition in der Waffe — `AmmoMinCount` / `AmmoMaxCount`

Das ist **nicht** die Stückzahl der Ware, sondern die Munition, die einer
gefundenen Waffe beiliegt. 84,99 % der `AmmoMinCount` sind 0; `AmmoMaxCount`
konzentriert sich auf 7 (4.493), 6 (2.635), 5 (2.602). Häufigstes Paar
(0,7) = 4.486. 92,7 % hängen an `Category = WeaponPrimary`.
**315 Einträge unter `Consumable` stehen auf 0/0 — dort wirkt kein Faktor.**

### 3.3 Zustand — `MinDurability` / `MaxDurability`

12.981 reguläre Einträge (46,5 % aller PossibleItems). Extrem einseitig verteilt:

| Paar | Anzahl | Bedeutung |
|---|---|---|
| 0.25 / 0.5 | 11.431 (88,1 %) | Standard für geplünderte Waffen |
| 1.0 / 1.0 · 1 / 1 · 1. / 1. | 415 · 220 · 13 | Neuzustand (**drei Schreibweisen!**) |
| 0.0 / 0.0 | 319 | Platzhalter, meist Quest-Belohnungen |
| 0.4 / 0.9 | 263 | überwiegend WeaponSecondary |
| 0.8 / 0.9 | 162 | überwiegend WeaponPistol |
| 0.45 / 0.45 | 64 | überwiegend Artefakte |

**Der Zustand hängt klar an der Kategorie** — ein einzelner globaler Regler ist
damit widerlegt: WeaponPrimary 11.209 von 11.572 auf 0.25/0.5 (96,9 %),
BodyArmor 272 von 278 auf Neuzustand (97,8 %), Head 83 von 84 (98,8 %).
Wer Waffen-Zustand anhebt, tut bei Rüstung nichts; wer pauschal senkt, lässt
erstmals beschädigte Rüstung spawnen.

### 3.4 Auswahl — `Chance` vs. `Weight`

Zwei Mechaniken, die sich pro Liste ausschließen:

- **`Weight`** = gewichtete Lotterie, **genau ein** Item wird gezogen
  (Wahrscheinlichkeit = Weight / Summe). Summen völlig frei (0 bis 4.100).
- **`Chance`** = unabhängiger Einzelwurf je Item, mehrere können gleichzeitig
  fallen. **Chance-Werte addieren sich NICHT auf 1** — von 621 Listen mit ≥ 3
  Einträgen tun das nur 2. Beweis: `Monolit_bench_1_ItemGenerator`
  (Zeilen 27939–27995) hat 13 Einträge mit je `Chance = 1.0`.

Von 27.889 Einträgen: 17.329 nur Weight, 10.222 nur Chance, 337 beide, 1 keines.
Bei `Weight`-Listen erhöht ein Mengen-Faktor also nur das **eine** gezogene Item.

---

## 4. Vererbung und Adressierung — die Fallen

- **2.607 von 3.085** Structs tragen `{refurl=…;refkey=…}`, davon **1.773 auf
  `[0]`** (das leere Basis-Template).
- **`refkey=[N]` ist positionsbasiert, nicht namensbasiert.** 88 Structs zeigen
  auf `[1]` — und das zweite Top-Level-Struct heißt `MoneyGenerator`, nicht `[1]`.
- **Die in `refurl` genannten Dateien existieren nicht** (`DynamicItemGenerator.cfg`
  662×, `Gamepass_ItemGenerators.cfg` 12× …). Sie wurden beim Packen
  eingeschmolzen; 2.519 der 2.607 refkeys lösen **innerhalb** dieser Datei auf.
  `refurl` darf nie als Dateizugriff interpretiert werden.
- **Kein einziger Durability-Wert wird vererbt** (12.981 von 12.981 stehen lokal).
  Ein Template-Patch existiert für dieses Feld schlicht nicht.
- **226 Structs heißen `[N]` statt wie ihre SID**, 239 haben Schlüssel ≠ SID.
  Der bpatch-Schlüssel muss dann der Index sein — sonst entsteht laut
  SPEC-Semantik ein **neuer** Knoten statt eines Patches (wirkungslos + Müll).
- **724 Direktkinder unter `ItemGenerator` sind benannt statt indiziert**
  (Head 722, BodyArmor 669, Consumable 17, WeaponPrimary 13, WeaponPistol 2,
  Attach 1). Pfade müssen aus der Datei gelesen, nie konstruiert werden.
- **Doppelte SID:** `LesserZone_Cabin` existiert 4× als eigenständiges
  Top-Level-Struct. Ein SID-basiertes Dictionary verschluckt 3 davon.
- **Zahlen- und Boolean-Schreibweisen sind inkonsistent:** `1`, `1.`, `1.0`,
  `4.f` für dieselbe Zahl; `True` (601×), `False` (150×), `false` (352×).
  Ein textueller `_neq`-Vergleich erzeugt Phantom-Patches.

---

## 5. Was NICHT angefasst werden darf

Es gibt **kein Quest-Feld** in dieser Datei — 0 Treffer für `bQuest`, `IsQuest`,
`Unique` o. Ä. Der Marker liegt eine Ebene tiefer, in `ItemPrototypes.cfg`
(`IsQuestItem`, 327× true; nach Auflösung der refkey-Kette **326 Quest-Items**).
Ein sicherer Filter braucht deshalb **beide** Stufen:

**Stufe 1 — Namens-Blacklist** (auf SID *und* Struct-Schlüssel):
`(?:^|_)(MQ|EQ|SQ|RSQ|ANCQ)(?=\d|_|$)`, `Quest`, `QSBIG`, `GDEQ`, `Reward`,
`^C_`, `(?:^|_)BP_`, `UAID_`, `Container`, `Template`, `Player`, `Boss`,
`Arena`, `GamePass`, `(?:^|_)Key`, `(?:^|_)Safe`, `Icon`, `PDA`
→ entfernt **918** Structs.

**Stufe 2 — inhaltliche Prüfung**: Block verwerfen, wenn eine enthaltene
`ItemPrototypeSID` ein Quest-Item (`IsQuestItem = true`) ist oder dem
Unikat-Muster `^Gun_[A-Z]` entspricht → entfernt **5 weitere**.

**Ergebnis: 2.162 Structs (70,1 %), Gegenprobe 0 Quest-Items, 0 Unikate.**
Nach zusätzlichem Ausschluss von Händlern (97) und Sammel-Templates (17+1)
bleiben **2.049**.

**Stufe 1 allein reicht nachweislich nicht** — durch sie rutschen
`Electrocollar`, `Garbage_DetentionCenter_Key_Padlock`, `Gun_Encourage_HG`,
`Gun_Silence_SMG` und `Gun_Trophy_AR` durch.

> **Korrektur zum Auftrag:** Das Muster `Gun_*_GS` kommt in dieser Datei
> **0×** vor. `_GS` ist das Suffix eines *Waffen-Setups*, kein Unikat-Merkmal.
> Die richtige Unikat-Konvention auf Item-Ebene ist `Gun_<Name>_<Klasse>`
> (mit Unterstrich nach `Gun`), z. B. `Gun_Whip_SR` — im Gegensatz zu
> Serienwaffen wie `GunAK74_ST`. 39 solcher Unikate existieren, 7 davon
> liegen in 9 Generatoren.

---

## 6. StashPrototypes.cfg — der sichere Einstieg

19 Structs; `empty` (Zeile 1) ist ein **reines Null-Schema**, die anderen 18
erben per `{refkey=empty}`, definieren aber **alle Zahlen selbst**.
1.060 Items, 470 Parameter-Einträge. **Keine `[*]`-Arrays** — jede Position
ist stabil indiziert und damit bpatch-sicher. **0 Quest-Items, 0 Unikate,
0 Durability-Felder.**

Schema: `<Stash>.ItemGenerators[i]` (i = Rang) → `.SmartLootParams` →
eine von 7 Gruppen → `[j]` → `.Items[k]`.

Die 7 Gruppen: `HealthParams`, `AttachParams` (beide **nur im Template**, tot),
`PrimaryWeaponParams`, `SecondaryWeaponParams`, `PistolWeaponParams`,
`ConsumablesParams`, `GrenadesParams`.

Stellschrauben je Eintrag: `MinSpawnChance` / `MaxSpawnChance` (0…1),
`MainWeaponAmmoCount`, `ItemSetCount`, `PriorityCaliber` sowie je Item
`MinCount` / `MaxCount` / `Weight` (1.035×) bzw. `Chance` (25×).

Die drei NPC-Leichen-Generatoren vollständig:

| Generator | Newbie | Experienced | Veteran | Master |
|---|---|---|---|---|
| `NPC_Ammo_Smart` | 4 Einträge | 5 | 7 | 8 |
| `NPC_Medicine_Smart` | Medkit 1–2, Bandage 2–4 | + Antirad | + ArmyMedkit | Antirad W5 |
| `NPC_Water_Smart` | Water 1–1 | identisch | identisch | identisch |

`MinSpawnChance` ist in allen 39 Einträgen 0.1f; `MaxSpawnChance` 0.8f (Munition)
bzw. 0.7f (Medizin/Wasser).

**Nutzung (aus `SpawnActorPrototypes.cfg`, 2.972 Zuweisungen):** `Empty` 2.022×,
`StashMedicine_Smart` + `Stash_Ammo_Smart_CommonRare` 753 + 86×,
`… + Stash_Ammo_Smart_Cheap` 46×, `StashMedicine_Cheap` 16×,
`Stash_AmmoAll_Cheap` 13×. **Vier Generatoren decken 2.937 der 2.972
Zuweisungen ab** — das ist der günstigste Hebel.

### CorpseSmartLoot: anders verdrahtet als angenommen

> **Korrektur zum Auftrag:** `DifficultyPrototypes.EconomyDifficulty.CorpseSmartLoot`
> existiert, weist die Generatoren aber **nur auf 2 von 11 Schwierigkeits-Structs**
> zu: `Easy` → `NPC_Medicine_Smart, NPC_Ammo_Smart` (Zeile 83) und `Medium` →
> `NPC_Water_Smart` (Zeile 152). `Empty` und `Hard` setzen das Feld **explizit
> leer**, `Stalker`, `Custom`, `Default` und alle vier Xbox-Varianten erben leer.
> Auf Hard/Stalker gibt es also **keinen Vanilla-Anker zum Skalieren** — dort
> müsste der Block erst angelegt werden, und ob die Engine ihn dann auswertet,
> ist aus den Daten **nicht belegbar**.

Zusätzlich greift Smart-Loot nur bei NPCs mit
`EnableSmartLootIfPossible = true` (1.514 Einträge) — die UI darf also keine
Wirkung auf „alle Leichen" versprechen.

---

## 7. Händler — ein eigener Regler

Kette: `ObjPrototypes.<NPC>.TradePrototypeSID` →
`TradePrototypes.<Laden>.TradeGenerators[i].ItemGeneratorPrototypeSID` →
`ItemGeneratorPrototypes.<Gen>.ItemGenerator[i].PossibleItems[j].MinCount`.

- Transitive Händler-Hülle: **95 Structs** (68 Wurzeln + 27 geteilte Bausteine).
- NPC-Loot-Hülle: **963 Structs**. **Schnittmenge: nur 6.**
- Händler-Einträge setzen fast immer eine Menge (77,0 % vs. 13,4 % beim Loot),
  nutzen `Chance` statt `Weight` (892 von 904) und haben größere Mengen
  (Munition Median 60/120 gegen 10/15).
- **334 der 696 Mengenzeilen liegen in nur 27 geteilten Bausteinen**
  (`Trader_T1..T4_Guns/Ammo`, `Trader_Attachments_T2..T4`,
  `Trader_Cosnsumables`, `Trader_NatoAmmo`, `Trader_SovietAmmo`) — günstigster Hebel.
- Sicherer Kern ohne Dev-Generatoren: **62 Structs, 456 Einträge = 912 Wertzeilen.**

Zwei sinnvolle Zusatzregler liegen in `TradePrototypes.cfg`, nicht im
Generator-Block: **Händler-Geld** (`Money`, `bInfiniteMoney`) und
**Nachschub-Takt** (`RefreshConditionSID`, je 73–74 Einzelpatches).

`ObjPrototypes.cfg`: alle **1.659** NPC-Prototypen definieren
`ItemGeneratorPrototypeSID` **und** `TradePrototypeSID` selbst — keine
Template-Abkürzung. Häufigster Loot-Generator:
`GeneralNPC_Neutral_Recon_ItemGenerator` (586 NPCs). 1.304 NPCs haben
`TradePrototypeSID = NoTrade`; nur 303 handeln überhaupt.

---

## WARNUNGEN

**Global**

1. **Niemals `[0]` patchen** (SID `empty`, Zeilen 1–24). 1.773 Structs erben davon.
2. **Niemals `MoneyGenerator.MinCount/MaxCount` mitskalieren** — gleiche Feldnamen,
   aber Kupons. 372 Werte, Maximum **72.500** (`SQ94_RSQ_reward_var11`, Zeile 273582).
   Ein ×3-Regler ergäbe 217.500 Kupons.
3. **Niemals die 871 quest-markierten Structs anfassen** — feste Story-Belohnungen
   mit `Chance = 1` und `MinCount == MaxCount`.
4. **Niemals `E01_MQ01_PlayerItemGenerator` / `E02_MQ01_PlayerItemGenerator`** —
   das ist die Startausrüstung inklusive `Gun_SkifGun_HG`.
5. **Niemals die 9 Unikat-Verteiler**: `Stash_SQ01_ValenokStash`,
   `Promzona_StorageontheHill_StashGenerator2_1CBB…`, `VartaColonelKorshunov_ItemGenerator`,
   `VartaColonelKorshunovBoss_ItemGenerator`, `NeutralPaivka_ItemGenerator`,
   `SQ02_reward_var1`, `SQ20_reward_var5` + die beiden Player-Generatoren.
   **Drei davon tragen keinen Quest-Marker im Namen** und werden nur von der
   inhaltlichen Item-Prüfung gefangen.
6. **Niemals die 5 Schlüssel-/Dokument-Generatoren**: `KeyGeneratorRedForest`,
   `MutantElectrocollarGenerator`, `CementPlant_IslandNearKopachi_Safe`,
   `GarbageDetCenterCorpseItemGenerator`,
   `GDEQ_Duty_DeadBody_ConcreteForest_ItemGenerator` — doppelte Quest-Schlüssel
   können den Questfortschritt blockieren.
7. **Niemals die Index-Structs `[159]`, `[192]`, `[206]`, `[238]`, `[239]`** —
   Ikone, ShahPDA, StrangePDA, NestorNote, X18-Dokumente.
8. **Niemals leere Zuweisungen befüllen** (`ItemGenerator =` 261×,
   `PossibleItems =` 181×). Sie löschen geerbte Arrays absichtlich.
9. **Niemals über die SID adressieren, wenn der Schlüssel ein Index ist** (226 Fälle).
10. **Niemals `[i]`-Indizes unter `ItemGenerator` annehmen** — 724 benannte Slots.
11. **Niemals textuell vergleichen** — `1` / `1.` / `1.0` / `4.f`,
    `True` / `False` / `false`, dazu die Tippfehler-Felder `weight` (152×) und
    `AmmoMaxcount` (4×) sowie das kaputte Struct `DefaultReward` (Zeile 263011)
    mit den Pseudofeldern `GeneratedItems =` und `Binoculars_03 =`.
12. **Dev-Generatoren ausschließen**: `AllAmmosGenerator` `[12]` steht bereits auf
    `MinCount = MaxCount = 900`; ebenso `AllBodyArmors` `[13]`, `AllPrimaryWeapons` `[11]`,
    `AllHeads` `[14]`, `AllArtifacts` `[15]`, `AllPistols` `[10]`, `AllConsumables` `[16]`,
    `AllAttaches` `[18]`, `AllDetectors` `[17]`, `AllTraderItemGenerator` `[19]`.

**Zustand (Durability)**

13. **Händler-Ware nicht beschädigen**: 21 in `TradePrototypes.cfg` referenzierte
    Generatoren (183 Einträge, fast alle 1/1) ausschließen — **über die SID-Liste,
    nicht über ein Namensmuster**: 17 Structs mit „Trade"/„Trader" im Namen
    (196 Einträge) sind echter Loot, `RC_TraderNPC_ItemGenerator` und
    `DynamicTraderItemGenerator` sind umgekehrt echte Händler ohne passendes Suffix.
14. **Die 3 Einträge mit `MinDurability` ohne `MaxDurability` nicht ergänzen**
    (Zeilen 84229, 84300, 273981) — sonst legt der Patch einen neuen Schlüssel an.
15. **Den Vanilla-Struktur-Bug auslassen**: 12 Zeilen liegen eine Ebene zu tief
    (`…PossibleItems[1].[6]`) in 6 Mercenaries-Generatoren (Zeilen 38696, 60670,
    168628, 174251, 222560, 228415).
16. **Nie `Min > Max` erzeugen** — beim Skalieren auf 0…1 klemmen und
    `Min ≤ Max` erzwingen.

**Verstecke (Stashes)**

17. **Niemals `empty` in `StashPrototypes.cfg` patchen.** Alle 18 Structs erben
    davon. Wer dort `MaxSpawnChance` oder `ItemSetCount` anhebt, aktiviert überall
    geerbte Einträge mit `ItemPrototypeSID = empty` — **wahrscheinlichster
    Absturzkandidat des ganzen Blocks.**
18. **Keine Rang-Indizes hardcodieren**: 7 Structs haben nur `ItemGenerators[0]`,
    12 haben `[0..3]`; einzelnen Rängen fehlen ganze Gruppen
    (`Stash_Ammo_Smart_Cheap.ItemGenerators[0]` ohne `PrimaryWeaponParams`,
    `Stash_Ammo_Smart_CommonRare.ItemGenerators[2]/[3]` ohne `SecondaryWeaponParams`).
19. **Nicht pauschal `Weight` schreiben** — 25 Items nutzen stattdessen `Chance`.
20. **`SecondaryWeaponParams` mitpatchen** — in den großen Munitions-Stashes sind
    sie 1:1-Kopien der Primary-Blöcke; wer sie auslässt, wirkt nur zur Hälfte.
21. **Tote bzw. abgeschaltete Structs kennen**: `StashMedicine_Corpse` und
    `StashVodka_Corpse` haben **0 Referenzen**; `Stash_AmmoSNG_Smart_MainLoot`
    und `Stash_AmmoNATO_Smart_MainLoot` stehen in **allen** Einträgen auf
    `MaxSpawnChance = 0.f` (bewusst deaktiviert — ein additiver Regler würde sie
    einschalten, ein multiplikativer wirkt nicht).
22. **Parser-Härtung nötig**: `MinSpawnChance = 0.` (nackter Punkt, Zeile 171),
    `= 0` ohne `.f` (Zeilen 158, 197), `MaxSpawnChance = 0.5` ohne `f`
    (Zeilen 159, 172, 198).
23. **Items nicht über die SID deduplizieren** — 42 Einträge führen dieselbe SID
    mehrfach; Deduplizierung verschiebt die Array-Indizes.
24. **Beim Patchen von `CorpseSmartLoot`**: `Empty` (Zeile 17) und `Hard` (Zeile 230)
    schreiben die leere Kurzform `CorpseSmartLoot =` ohne Struct-Block. Diese in
    einen Block zu verwandeln ist eine andere Operation als das Überschreiben
    eines vorhandenen — ungetestet. Xbox-Varianten **nicht** zusätzlich patchen,
    sie erben automatisch.

**Datenlücke**

25. 2.206 Structs verweisen per `refurl` auf Dateien, die in `vanilla/` nicht
    existieren. Die Werte stehen zwar praktisch immer lokal (12.981 von 12.981
    Durability-Werten), aber ein Restrisiko bleibt.

---

## Fazit und Vorschlag für die Umsetzung

**Stufe 1 — Verstecke & Leichen-Loot (klein, sicher, empfohlener Anfang).**
Ziel: `StashPrototypes.cfg`. 19 Structs, alles explizit indiziert, keine
Quest-Items, keine Unikate, keine Händler-Überschneidung. Regler-Kandidaten:
Stückzahlen (`Items[k].MinCount/MaxCount`), Fundchance (`MaxSpawnChance`) und
Munition an der Waffe (`MainWeaponAmmoCount`). Vier Generatoren decken 98,8 %
der Zuweisungen ab. Aufwand: gering; Patch bleibt klein.
**Neue Datei in `NEEDED_FILES` → `CACHE_SCHEMA` erhöhen.**

**Stufe 2 — Loot-Mengen im großen Generator.**
Nur `MinCount`/`MaxCount` in `PossibleItems`, nur auf den 2.049 gefilterten
Structs. Braucht vier Bausteine, ohne die es zu riskant ist:
(a) verschachtelter Parser mit Index-Tracking (5 Ebenen, gemischt Index/Name),
(b) Cross-File-Lookup nach `ItemPrototypes.cfg` inkl. refkey-Auflösung für
`IsQuestItem`, (c) strikte Trennung von `MoneyGenerator` und `PossibleItems`,
(d) numerische statt textueller `_neq`-Vergleiche.

**Stufe 3 (optional, je eigener Regler).**
Zustand gedroppter Waffen — nur auf den Haupt-Cluster 0.25/0.5 der
Waffen-Kategorien (11.431 Einträge in 827 Structs), Rüstung/Helme getrennt
lassen. Achtung: **kein Wert wird vererbt**, deshalb ~22.900 Patch-Zeilen —
das sprengt alle bisherigen Blöcke um Größenordnungen. Vorher überlegen, ob
sich das gegenüber dem Nutzen lohnt.
Händler-Bestände als vierter, klar getrennter Regler (62 Structs / 912 Zeilen),
plus optional Händler-Geld und Nachschub-Takt aus `TradePrototypes.cfg`.

**Pflicht-Testfälle für jede Stufe** (die Ausreißer, an denen naive
Implementierungen scheitern): die 319 Einträge mit 0.0/0.0 (Faktor wirkungslos),
die 648 Neuzustand-Einträge in drei Schreibweisen, die 814 Einträge mit
`MinCount` ohne `MaxCount`, die 3 ohne `MaxDurability`, die 6 benannten
`ItemGenerator`-Slots (z. B. `NeutralEfim_ItemGenerator.ItemGenerator.WeaponPrimary`),
die 524 nur per Index adressierbaren Einträge, die 12 Zeilen des Struktur-Bugs,
`NPC_Ammo_Smart.ItemGenerators[0].…PrimaryWeaponParams[1].MaxSpawnChance = 0.9f`
(einziger 0.9f-Wert der Datei) und
`Stash_AmmoNATO_Smart.ItemGenerators[3].…SecondaryWeaponParams[7].Items[0]`
(Vanilla-Widerspruch `MinCount = 25 > MaxCount = 15`, Zeile 4695).
