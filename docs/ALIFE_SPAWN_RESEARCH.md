# A-Life-Spawn-Recherche: Director + Lager (Lairs) — Stand 03.09.2026

Anlass: Nexus-Wunsch von MetalMessiah0 (= lux1109, 02.09.2026): „mehr Spawns
für Mutanten und Menschen, mehr Prozent Mutanten in jedem Gebiet, Mutanten-
TYP wählen (kleine Viecher / mittlere / große Räuber)". Seine Beobachtung:
der bestehende Regler „Max simultaneous A-Life agents" (AIGlobals
`MaxAgentsCount`) macht kaum einen spürbaren Unterschied. Dieses Dokument
erklärt, warum, und welche Werte den Spawn wirklich steuern. Alle Zahlen sind
gegen die extrahierten Vanilla-Daten (Patch 2.0.x, Stand 27.08.2026) gezählt,
nichts ist geschätzt. Pfade relativ zu `vanilla/Stalker2/Content/GameLite/GameData/`.

Kein Multi-Agent-Lauf — alles per Skript auf den lokalen Dateien (03.09.,
the development machine).

---

## 0. Kurzfazit

Der Spawn läuft über **zwei getrennte Systeme**, die beide per cfg/bpatch
erreichbar sind und die der Tool-Regler `MaxAgentsCount` NICHT anfasst — er
ist nur ein globaler Online-Deckel (52 Agenten), der erst greift, wenn die
beiden Systeme mehr liefern, als er erlaubt:

1. **Lager (Lairs)** — `LairPrototypes.cfg`: feste Orte auf der Karte (446
   Platzierungen, 74 Lager-Typen). Je Lager, Bewohner-Fraktion und Spieler-
   Rang steht dort **wie viele** Bewohner es hält (`MaxSpawnQuantity`), wie
   voll es startet, **wie schnell** Gefallene nachwachsen (drei Timer) und
   **welche Archetypen** mit welchem Gewicht. Das ist der Hebel für „mehr
   Mutanten in einem Gebiet" und „Arten wählen".
2. **Director** — `ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg`:
   Zufallsbegegnungen um den Spieler herum. Alle `SpawnDelay` Sekunden zieht
   er ein Szenario per Gewicht aus der Szenario-Gruppe der Region (Global,
   Hub, Quiet, …), begrenzt durch Rang-Deckel je Agententyp und eine Liste
   verbotener Arten. Das ist der Hebel für „wie oft" und „wie viel Prozent
   Mutanten" bei Zufallsbegegnungen.

**Machbar (bpatch, nur Skalar-Blätter):** Lager-Bestand ×Faktor getrennt für
Mutanten und Menschen; Lager-Respawn-Tempo; Director-Frequenz; Mutanten-
Anteil der Zufallsbegegnungen (Szenario-Gewichte); Rudel-Größe je Art
(Rang-Deckel); je Art die Begegnungs-Gewichte (Blinddog/Boar/Flesh/Tushkan/
Bloodsucker/Chimera/generisch). Zwei NEUE Dateien → `NEEDED_FILES` +
`CACHE_SCHEMA` 12→13. Details und Grenzen in Abschnitt 7, Verbote in 8.

**Nicht machbar / tabu:** neue Szenarien oder Arten anlegen (Array-Struktur),
Regionen anders zuordnen (steht in der 184-MB-Datei `SpawnActorPrototypes.cfg`),
verbotene Arten freischalten (Array `ProhibitedAgentTypes`), Quest-/Guard-
Lager.

Community-Beleg, dass genau diese Werte im Spiel wirken: Abschnitt 6.

---

## 1. Dateien

| Datei | Zeilen | Top-Level | Inhalt | Status im Tool |
|---|---|---|---|---|
| `ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg` | 2 233 | 1 (`ALifeDirectorPreset`, SID `Default`) | Director: Defaults, Rang-Deckel, Verbotslisten, 73 Szenarien, 13 Gruppen | NEU (82 KB, `.cfg.bin` vorhanden) |
| `LairPrototypes.cfg` | 19 794 | 75 (`[0]` + 74 Lager-Typen) | 196 (Lager, Fraktion)-Paare × 4 Ränge = 784 Rang-Blöcke, 2 709 Archetyp-Einträge | NEU (918 KB, `.cfg.bin` vorhanden) |
| `ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg` | 616 | 1 (`ALifePopulationManagerPreset`) | Fraktions-Expansion zwischen Lagern, 29 Fraktionen | optional |
| `ALifePrototypes/ALifePolicyPrototypes.cfg` | 14 | 1 (`Default`) | Refill-Cooldowns, Leichen-Deckel | optional |
| `AIGlobals.cfg` | 779 | — | `MaxAgentsCount = 52`, `MinALifeSpawnDistance = 2500`, `MinALifeDespawnDistance = 3000`, `RegionRank` (23 Regionen) | schon in NEEDED_FILES |
| `CoreVariables.cfg` | — | — | `ALifeGridVisionRadius = 8500`, `LairSearchingRadius = 130000`, `AlifeCorpsesHardcap = 1500`, `CorpseALifeOnlineTime = 1800` | schon in NEEDED_FILES |
| `SpawnActorPrototypes.cfg` | 184 MB | — | Platzierung der Lager (446 `LairPrototypeSID`) und Zuordnung Region → Szenario-Gruppe (63 `ALifeScenariosGroupSID`) | NICHT extrahieren, NICHT patchen |

Keine DLC-Überschreibungen (`DLCGameData` enthält keine ALife-/Lair-Dateien),
keine `refurl`-Verweise auf diese Dateien aus anderen cfgs.

---

## 2. Modell: wie beide Systeme zusammenspielen

- **Lager** sind auf der Karte platziert (446 Stück, Abschnitt 4.1). Jedes hat
  einen Lager-Typ mit erlaubten Bewohner-Fraktionen (`PossibleInhabitantFactions`)
  und einer Start-Fraktion (`InitialInhabitantFaction`). Der Population
  Manager lässt Fraktionen zwischen Lagern expandieren (Abschnitt 5). Je
  (Lager, Fraktion, Rang) gilt ein Bestand `MaxSpawnQuantity`, der zu
  `InitialSpawnQuantityPercent` gefüllt startet und über drei Timer nachwächst.
- **Der Director** erzeugt Begegnungen relativ zum Spieler. Die Region gibt
  die Szenario-Gruppe vor (63 Regionen: 41× `EmptyGroup` = keine Director-
  Spawns, 10× `Hub`, 5× `Quiet`, 4× `Global`, je 1× `Swamp_ScenarioGroups`,
  `HumanVsMutants_LesserZone`, `Emission`; ohne Eintrag gilt
  `DefaultScenarioGroup = Global`). Aus der Gruppe wird per `ScenarioWeight`
  gewürfelt; nach `SpawnDelayMin..Max` Sekunden der nächste Wurf, dazwischen
  `PostSpawnDirectorTimeout`.
- **Spieler-Rang** (Newbie/Experienced/Veteran/Master) kommt aus der Region
  (`AIGlobals.RegionRank`, Abschnitt 3.6) und schaltet Szenarien
  (`PlayerRequiredRank`) und Deckel je Agententyp frei.
- **`MaxAgentsCount = 52`** (bestehender Regler) deckelt nur, wie viele
  Agenten gleichzeitig ONLINE sind. Wer mehr Spawns will, muss Lager und
  Director drehen — und den Deckel ggf. mit anheben, sonst bremst er.

---

## 3. Director — `ALifeDirectorScenarioPrototypes.cfg`

Ein einziger Top-Level-Struct `ALifeDirectorPreset` (SID `Default`). Patch-
Pfade beginnen darum immer mit `ALifeDirectorPreset.`.

### 3.1 Default-Werte (Skalare, alle bpatch-bar)

| Schlüssel | Vanilla | Bedeutung (Hypothese, konsistent mit Gruppen-Werten) |
|---|---|---|
| `DefaultSpawnDelayMin` / `Max` | 100 / 180 | Sekunden zwischen zwei Director-Würfen, wenn die Gruppe keine eigenen hat |
| `DefaultPostSpawnDirectorTimeoutMin` / `Max` | 150 / 300 | Pause nach einem Spawn |
| `DefaultALifeLairExpansionToPlayerTimeMin` / `Max` | 120 / 180 | Zeit, bis eine Lager-Expansion Richtung Spieler zieht |
| `DefaultExpansionSquadNumMin` / `Max` | 4 / 7 | Squad-Größe bei Lager-Angriffen (Szenarien `*_AttackEnemyLair` überschreiben: Menschen 4/7, Mutanten 1/1) |
| `DefaultShouldDespawnNPCs` | true | |
| `DefaultEmissionScenarioGroup` / `DefaultScenarioGroup` / `DefaultEmptyScenarioGroup` | Emission / Global / EmptyGroup | |
| `FallbackMaxSpawnCount` | 3 | |

### 3.2 Rang-Deckel je Agententyp (`ALifeScenarioNPCArchetypesLimitsPerPlayerRank`)

Pfad: `ALifeDirectorPreset.ALifeScenarioNPCArchetypesLimitsPerPlayerRank.[i].Restrictions.[j].MaxCount`
(`[i]` = Rang 0..3, `[j]` = Typ 0..15 — Indizes sind je Rang gleich sortiert,
beim Patchen trotzdem über `AgentType` zuordnen, nicht über den Index).

| Typ | Newbie | Experienced | Veteran | Master | Director-spawnbar? |
|---|---|---|---|---|---|
| Human | 3 | 4 | 5 | 6 | ja |
| MutantGeneric | 3 | 4 | 4 | 4 | ja |
| Blinddog | 4 | 6 | 8 | 12 | ja |
| Boar | 2 | 3 | 5 | 6 | ja |
| Flesh | 2 | 3 | 5 | 6 | ja |
| Snork | 1 | 3 | 4 | 6 | ja |
| Tushkan | 6 | 8 | 12 | 16 | ja |
| Bloodsucker | 0 | 1 | 1 | 1 | ja (Newbie: 0) |
| Chimera | 1 | 1 | 1 | 1 | **verboten** (s. 3.3), Szenario `ChimeraSingle` existiert trotzdem |
| Controller | 0 | 1 | 1 | 1 | verboten |
| Burer | 1 | 1 | 1 | 2 | verboten |
| Poltergeist | 1 | 1 | 2 | 2 | verboten |
| PseudoDog | 1 | 1 | 1 | 1 | verboten |
| Cat | 1 | 1 | 1 | 2 | verboten |
| Deer | 1 | 1 | 1 | 1 | verboten |
| RatSwarm | 1 | 1 | 1 | 1 | verboten |

**Hypothese zur Rudel-Größe:** Szenarien nennen keine Stückzahl. Sie haben
`AliveMultiplierMin/Max` (fast immer 0.4/0.8). Rudel = Deckel × Multiplikator
passt zu den Szenario-Namen (Blinddog Newbie 4 × 0.4–0.8 ≈ 2–3 Hunde, Master
12 × 0.4–0.8 ≈ 5–10; „Blinddog3_5", „Boar5_7"). Muss im Spiel bestätigt werden.

### 3.3 Verbots- und Fallback-Listen (Arrays — NICHT patchen)

- `ProhibitedAgentTypes` (9): Chimera, Pseudogiant, Controller, Poltergeist,
  Burer, Cat, Deer, PseudoDog, RatSwarm. Widerspruch: `ChimeraSingle` steht
  mit Gewicht 2 in `Global` und 1 in `HumanVsMutants` (Rang Veteran). Deutung:
  die Verbotsliste gilt für die generische Auswahl (`AgentArchetype::Mutant`),
  explizite `AgentPrototypeSID`-Szenarien umgehen sie. Nicht verifiziert.
- `RestrictedObjPrototypeSIDs` (51): alle `GuardNPC_*` plus Spark-/Noon-/
  Scientist-Prototypen — die spawnt der Director nie als Zufallsbegegnung.
- `FallbackNPCTypes` (4): Bandits, Neutrals, Blinddog, Boar.

### 3.4 Szenarien (73)

Jedes Szenario: `PlayerRequiredRank`, `ScenarioSquads.[k]` mit ENTWEDER
`AgentArchetype` (`Human` / `Mutant` = generisch) ODER `AgentPrototypeSID`
(konkrete Art/Prototyp), `bPlayerEnemy`, `RelationGroup`,
`AliveMultiplierMin/Max`, `WoundedMultiplier`, `DeadMultiplier`,
`ScenarioGroupsTarget` (Player / TargetEachOther / AttackEnemyLair /
AllyLair / ContextualAction). **Achtung:** Struct-Schlüssel ≠ SID bei
`BlinddogPack` (SID `BlinddogPackSmall`) und `ChimeraSingle` (SID
`Mutant_Chimera`) — bpatch adressiert den Struct-Schlüssel.

Klassen (für einen „Mutanten-Anteil"-Regler):

- **Rein Mutanten (33):** `Mutants`, `DeadMutant`, `DeadMutants`,
  `Mutant_AttackEnemyLair`, `BlinddogPack`, `BoarPack`, `FleshPack`, `RatPack`,
  `TushkanPack`, `BloodsuckerSingle`, `BloodsuckerDuo`, `SnorkPack`, `CatPack`,
  `ChimeraSingle`, `Mutant3_5VsMutant3_5`, `Mutant5_7VsMutant5_7`,
  `Mutant3_5VsDeadMutant1_3`, `Mutant5_7VsDeadMutant3_5`, `Bloodsucker1`,
  `Boar3_5`, `Boar5_7`, `Blinddog3_5`, `Blinddog5_7`, `Flesh3_5`,
  `Tushkans7_10`, plus die 6 `Blinddog/Boar…Vs…`-Paare (alle Rang Newbie
  außer `ChimeraSingle` = Veteran).
- **Gemischt (3):** `HumansVsMutants`, `Humans_Wounded_Friendly_vs_Dead_Mutants`,
  `Humans_Wounded_Enemy_vs_Dead_Mutants`.
- **Rein Menschen (37):** alle übrigen (`HumansVsHumans`, `Humans_Friendly`,
  `Humans_Enemy`, Wounded-/Dead-Varianten, `Humans_AttackEnemyLair_*`,
  `*_MoveTo_AllyLair`, `*_ContextualAction_*`, 16 `Dead_<Fraktion>_<Rolle>_*`).
- `BloodsuckerSingle` hat `AliveMultiplier` 0.2/0.3, `Bloodsucker1` 0.2/0.4,
  alle anderen 0.4/0.8. Wounded-/Dead-Szenarien liefern Leichen/Verwundete
  (`AliveMultiplier` 0, `Wounded`/`DeadMultiplier` 0.1–0.6).

### 3.5 Szenario-Gruppen (13) — Gewichte, Delays, Karten-Nutzung

Pfad: `ALifeDirectorPreset.ScenarioGroups.<Gruppe>.ScenarioSIDs.<Szenario>.ScenarioWeight`
bzw. `…ScenarioGroups.<Gruppe>.SpawnDelayMin/Max`, `PostSpawnDirectorTimeoutMin/Max`.

| Gruppe | Delay | Timeout | auf der Karte | Gewichte (Mutanten fett) |
|---|---|---|---|---|
| **Global** (Default) | 60–90 | 130–180 | 4× explizit + überall ohne Eintrag | HumansVsHumans 20, HumansVsMutants 25, Humans_Friendly 15, Humans_Enemy 10, **Mutants 10**, **BlinddogPack 10**, **BoarPack 10**, **FleshPack 10**, **TushkanPack 5**, **BloodsuckerSingle 0**, **ChimeraSingle 2**, ContextualAction_Friendly 5, _Enemy 5, MoveTo_AllyLair 0/0 |
| Local | 30–60 | 150–210 | 0 | **Mutants 20**, HumansVsHumans 10, HumansVsMutants 10, Humans_Friendly 15, Humans_Enemy 10 |
| Hub | 45–90 | 90–120 | 10 | Humans_Friendly_MoveTo_AllyLair 5 |
| Quiet | 120–150 | 120–160 | 5 | 5 Dead*-Szenarien, alle Gewicht 0 |
| Global_LesserZone | 120–150 | 180–300 | 0 | HvH 10, HvM 10, Friendly 10, Enemy 4, **Mutants 4**, **Blinddog/Boar/FleshPack je 5**, Tushkan/Bloodsucker 0 |
| HumanVsMutants_LesserZone | 120–180 | 240–300 | 1 | wie Global_LesserZone |
| HumanVsMutants | 120–210 | 300–420 | 0 | HvH 10, HvM 20, Friendly 7, Enemy 7, MoveTo je 7, Contextual je 6, **ChimeraSingle 1** |
| CaptureLairs | 60–90 | 240–360 | 0 | AttackEnemyLair_Enemy 5, _Friendly 5, **Mutant_AttackEnemyLair 5** |
| ContextualActions | 5–30 | 120–150 | 0 | Contextual_Friendly 5, _Enemy 5 |
| Swamp_ScenarioGroups | 60–120 | 140–210 | 1 | **Mutant3_5VsMutant3_5 5**, **Mutant5_7VsMutant5_7 5**, 20 weitere mit Gewicht 0 |
| AllScenarios | 150–240 | 240–360 | 0 | 34 Szenarien, alle 5 (Dev-Gruppe) |
| Emission | 10–20 | 120–150 | 1 (+ Default bei Emission) | Humans_Friendly 6, Humans_Enemy 3 |
| EmptyGroup | 50–120 | 60–120 | 41 | keine Szenarien |

Rechnung Global: Summe 127; rein Mutanten 47 (37 %), mit `HumansVsMutants`
72 (57 %). Gruppen mit Karten-Nutzung 0 sind vermutlich Rest/Dev oder werden
per Quest gesetzt — Patches darauf sind harmlos, aber wirkungslos.

### 3.6 Spieler-Rang je Region (`AIGlobals.RegionRank`, 23 Einträge)

Newbie–Master: Zone. Newbie–Experienced: MalayaZona (Lesser Zone).
Experienced–Veteran: Bolota (Swamps), Kordon. Veteran–Master: Pripyat,
Generatory. Alle übrigen 17 Regionen: Experienced–Master. Der Rang gilt
also regional, nicht als XP-Fortschritt — „Newbie"-Deckel greifen praktisch
nur in der Lesser Zone.

---

## 4. Lager — `LairPrototypes.cfg`

### 4.1 Lager-Typen auf der Karte (446 Platzierungen, `LairPrototypeSID` in SpawnActorPrototypes)

BigLivingSpace 37, SmallLivingSpace 36, RestingLairDefault 35,
GenericHumansAndMutants 33, Monolith 29, WildField 23, Neutrals 17,
Militaries 17, WildUnderground 16, GenericHumansOnly 12, Bloodsucker 12,
Rat 11, GuardNeutrals 10, Poltergeist 9, Varta 8, Blinddog 8, GuardVarta 7,
Flesh 7, Burer 7, Mercenaries 6, LivingUnderground 6, Noon 5, NeutralZombies 5,
Freedom 5, Controller 5, Boar 5, Bandits 5, Snork 4, Pseudogiant 4,
Pseudodog 4, Poltergeist_Electro 4, GuardNoon 4, GuardCorpus 4, NeutralMSOP 3,
GuardFreedom 3, Duty 3, BanditZombies 3, WildForest 2, Spark 2,
Poltergeist_Toxic 2, Rest je ≤ 1 (u. a. Chimera, Deer, Tushkan, Bayun,
GenericMutantsOnly, Guard*_Sniper, RatSwarm_*, MALACHITE-/SIRCAA-Scientists).

### 4.2 Struktur eines Lager-Typs

```
<LagerTyp> : struct.begin
   SID = <LagerTyp>
   Preset : struct.begin
      InitialInhabitantFaction = <Fraktion>
      IsALifePoint = true
      PossibleInhabitantFactions : struct.begin
         <Fraktion> : struct.begin
            Faction = <Fraktion>
            FactionPriority = 3
            SpawnSettingsPerPlayerRanks : struct.begin
               Newbie : struct.begin            (ebenso Experienced/Veteran/Master)
                  MaxSpawnQuantity = 9
                  InitialSpawnQuantityPercent = 0.5
                  InitialSpawnQuantityRespawnTimeSeconds = 180.0
                  MaxSpawnQuantityRespawnTimeSeconds = 480.0
                  WipeRespawnTimeoutSeconds = 480.0
                  SpawnSettingsPerArchetypes : struct.begin
                     <Archetyp> : struct.begin
                        MinQuantityPerArchetype = 1
                        SpawnWeight = 1.0
```

Patch-Pfad also z. B.
`Blinddog.Preset.PossibleInhabitantFactions.Blinddog.SpawnSettingsPerPlayerRanks.Master.MaxSpawnQuantity`.
Kein `refkey` irgendwo — **jeder Block definiert alle Werte selbst** (784 von
784), also immer Einzel-Patches, keine Template-Vererbung.

### 4.3 Bestand je Fraktion und Rang (`MaxSpawnQuantity` N/E/V/M, `InitialSpawnQuantityPercent`)

Identisch in jedem Nicht-Guard-Lager-Typ, der die Fraktion erlaubt (per
Skript gegengeprüft; einzige Ausnahme Zombie mit zwei Varianten, s. u.):

| Fraktion | N/E/V/M | Start % | Archetypen |
|---|---|---|---|
| Blinddog, MoldyBlinddog | 9/9/9/9 | 0.5 | 1 |
| Tushkan | 14/16/20/24 | 0.5 | 1 |
| Snork | 8/8/9/9 | 0.5 | 1 |
| Boar | 5/5/5/5 | 0.5 | 1 |
| Flesh | 5/5/5/6 | 0.5 | 1 |
| Bloodsucker | 2/2/3/3 | 0.5 | 1 |
| Bayun | 2/2/2/2 | 0.5 | 1 |
| Pseudodog, Deer | 1/1/2/2 | 0.5 (Master 1.0) | 1 |
| Controller, Poltergeist (4 Varianten), Chimera, Burer, Pseudogiant | 1/1/1/2 | 0.5 (Master 1.0) | 1 |
| Rat (5 Lager-Typen) | 1/1/1/1 | 1.0 | RatSwarm_75/150/225/300 (ein Schwarm-Prototyp = 1 Bestand) |
| Zombie (Duty/Freedom/Bandit/Neutral) | 6/7/8/10 | 0.5 | 4–5 `GeneralZombie_*` |
| Zombie (Corpus, generische Lager) | 6/8/10/10 | 0.5 | 5 |
| Menschen-Fraktionen (Militaries, Neutrals, Varta, Mercenaries, Freedom, Bandits, Monolith, Duty, Noon, Scientists, Spark, Corpus …) | 6/6/6–8/7–8 | 0.5 | 2–5 `GeneralNPC_<Fraktion>_<Rolle>` mit `MinQuantityPerArchetype` (Recon-lastig) |
| Guard-Lager (`Guard<Fraktion>`) | 7/7/8/10 | 0.5 | `GuardNPC_*` (Basis-Wachen); `Guard*_Sniper` 1/1/1/1 |

Verteilung aller 784 Blöcke: Newbie 1×31, 2×16, 5×12, 6×101, 7×13, 8×6, 9×8,
14×9 · Master 1×12, 2×27, 3×8, 5×6, 6×6, 7×74, 8×14, 9×14, 10×26, 24×9.

Ausreißer (für Tests): `Tushkan` 24 (Master) ist der größte Bestand; die
„Exoten" (Controller, Chimera, Burer, Pseudogiant, Poltergeist) haben 1 und
starten erst bei Master zu 100 %.

### 4.4 Respawn-Timer

774 von 784 Blöcken: `InitialSpawnQuantityRespawnTimeSeconds = 180`,
`MaxSpawnQuantityRespawnTimeSeconds = 480`, `WipeRespawnTimeoutSeconds = 480`.
**10 Ausnahmen (6 / 30 / 30 s, nur Rang Newbie):** Diggers, IkarVarta,
SultanBandits, NeutralBandits, GuardDiggers, GuardSultanBandits sowie die vier
Zombie-Lager DutyZombies/FreedomZombies/BanditZombies/NeutralZombies — das
sind Story-/Tutorial-Lager (Lesser Zone), die sofort nachfüllen. **Nicht
anfassen** (Regel: nur Blöcke mit den Standard-Timern skalieren).

### 4.5 Sonderfall `RestingLairDefault` (35 Lagerfeuer)

Eigene Skalare im Preset: `LairType = ELairType::RestingLair`,
`RestingLairInstantSpawnScenarioChance = 0.4`,
`RestingLairShortDelayedSpawnScenarioChance = 0.4`,
`RestingLairMinNPCCount = 1`, `RestingLairMaxNPCCount = 5`,
`RestingLairShortDelaySpawnMin/Max = 60/120`, `RestingLairLongDelaySpawnMin/Max
= 600/1200`, `ALifeLairsSearchRadius = 65000`,
`GameTimeOfflineToRerollLairData = 14400` (4 Spielstunden — danach würfelt ein
lange nicht besuchtes Lager neu). Die Community-Mod (Abschnitt 6) schaltet die
Short-Delay-Spawns ab, weil sie „Pop-up-Spawns" nahe am Spieler erzeugen.
Bewusst NICHT im ersten Ausbau.

### 4.6 Vanilla-Inkonsistenz, die der Builder respektieren muss

In 7 Blöcken ist `Σ MinQuantityPerArchetype` (7) GRÖSSER als
`MaxSpawnQuantity` (6): Freedom, Rang Newbie, in allen 7 Freedom-fähigen
Lager-Typen. In 96 Blöcken ist die Summe gleich dem Maximum. Das Spiel
verkraftet das offenbar — aber ein Verkleinerungs-Faktor darf die Lücke nicht
vergrößern: **Untergrenze beim Skalieren nach unten = min(Vanilla-Max,
Σ MinQuantityPerArchetype), nie unter 1.**

---

## 5. Population Manager + Policy (nur Kontext, kein Regler im ersten Ausbau)

`ALifePopulationManagerPreset` (SID Default): `ALifeLairExpansionTime = 50`,
`ALifeLairExpansionRadius = 500000`, `ALifeStartSimulation = 48` (Stunden).
29 Fraktionen, jede `ALifeLairExpansionBattleChance = 50` und drei Ziele nach
Lager-Anzahl (Aggressive/Normal/Defensive mit `MinLairs/MaxLairs`), z. B.
Bandits 1–5 / 6–20 / 21–900, die meisten Mutanten 1–7 / 8–31 / 32–900,
Pseudogiant 1–7 / 8–10 / 11–900. `ALifePolicyPrototypes`: `TriggerExtinction
2000`, `MaxCorpsePerRadius 30` in `CorpseRadius 10000`, `SeenLongAgoByPlayerSec
900`, `FullWipeRefillCooldown 360`, `PartialWipeRefillCooldown 120`,
`MinRefillDistance/Max 20000/25000`. Tiefere Knöpfe (`OfflineCombatWeight`,
Need-Schwellen) liegen in `ObjPrototypes.cfg` — nicht analysiert.

---

## 6. Community-Belege (Wirkung im Spiel)

- **„A-Life Uh.. Found A Way"** (Nexus 1122, LetsWoolgather, 435 Endorsements,
  Version 1.8.13B vom 02.09.2026 mit 2.0.x-Beta): dreht laut Changelog exakt
  diese Werte — Lager-`MaxSpawnQuantity` („Lair Min/Max Quantity"), die drei
  Respawn-Timer („6 min & 16 min, Wipe 25 min"), `InitialSpawnQuantityPercent`
  („start with Max"), Szenario-Gruppen-Timeouts, `ExpansionSquadNum`,
  `DefaultALifeLairExpansionToPlayerTime`, `ALifeLairExpansionRadius`,
  Fraktions-Ziele, Policy-Cooldowns, Resting-Lair-Short-Delay. Berichtet
  beobachtete Wirkung und Nebenwirkungen (Leichenberge bei zu hohen
  Expansions-Gewichten, Pop-up-Spawns). Hinweis dort: Lager-Änderungen
  brauchen bei bestehenden Saves Zeit („ein paarmal schlafen / 30–40 min in
  einer anderen Region").
- **„More Enemies"** (Nexus 438, Nov. 2024): mehr Menschen, weniger Mutanten
  über `LairPrototypes`, `ALifeDirectorScenarioPrototypes`,
  `ALifePopulationManagerFactionPrototypes`, `AIGlobals`.
- „A-Life Extended" (273), „Roadside Panic" (210): gleiche Dateien.
- Diese Mods ersetzen die Dateien komplett bzw. patchen viele Blätter — mit
  einem S2Tweaker-Pak auf denselben Blättern entscheidet die Ladereihenfolge;
  der Mod-Scan würde die Überschneidung zeigen, sobald die Dateien in
  `NEEDED_FILES` sind.

---

## 7. Was daraus bauen — Vorschlag

Alle Regler multiplikativ, Default = Vanilla (kein Patch), Werte live über
`gd.resolve`/eigene Accessoren, nur Skalar-Blätter, Ganzzahlen gerundet.

| Regler | Datei | Was skaliert wird | Umfang | Ehrliche Grenze |
|---|---|---|---|---|
| **Lair population: mutants** (×0.5–3) | LairPrototypes | `MaxSpawnQuantity` aller Blöcke mit Mutanten-Fraktion (Blinddog, MoldyBlinddog, Bloodsucker, Boar, Flesh, Snork, Pseudodog, Tushkan, Bayun, Deer, Rat, Controller, Poltergeist, Chimera, Burer, Pseudogiant, Zombie) | 352 Blöcke | Untergrenze 4.6; Lager füllen nachträglich (4.5: Reroll nach 4 h Spielzeit) |
| **Lair population: humans** (×0.5–3) | LairPrototypes | `MaxSpawnQuantity` der Menschen-Fraktionen in Nicht-Guard-Lagern | 368 Blöcke (64 Guard-Blöcke bleiben vanilla) | Guard-Lager (Basis-Wachen) bleiben vanilla — eigenes Häkchen denkbar, erst nach Test |
| **Lair respawn speed** (×0.25–4) | LairPrototypes | die drei Timer ÷ Faktor, nur Standard-Blöcke 180/480/480 | 774 Blöcke | Story-Lager (6/30/30) tabu |
| **Random encounters: frequency** (×0.25–4) | Director | `SpawnDelayMin/Max` aller 13 Gruppen + `DefaultSpawnDelayMin/Max` ÷ Faktor (Min ≥ 5 s, Min ≤ Max); optional `PostSpawnDirectorTimeout` ÷ Faktor | 30 Blätter | Gruppen ohne Karten-Nutzung wirkungslos, harmlos |
| **Random encounters: mutant share** (×0–4) | Director | `ScenarioWeight` der 33 rein-Mutanten-Szenarien in allen Gruppen × Faktor, gerundet; Gewicht 0 bleibt 0 (keine neuen Arten) | ~40 Blätter | Anteil, nicht absolute Menge; 0 = keine Mutanten-Zufallsbegegnungen (Lager-Mutanten bleiben) |
| **Encounter pack size** (×0.5–2, experimentell) | Director | Rang-Deckel `MaxCount` der 8 Director-spawnbaren Typen × Faktor (≥ 1; Bloodsucker Newbie 0 bleibt 0) | 32 Blätter | Semantik (3.2) ist Hypothese → „experimental" |
| **Encounter weights per mutant kind** (Baum oder 7 Regler, ×0–4) | Director | je Art die Gewichte ihrer Pack-Szenarien in `Global` (Blinddog 10, Boar 10, Flesh 10, Tushkan 5, Bloodsucker 0, Chimera 2, generisch `Mutants` 10) + Lesser-Zone-Gruppen | ~25 Blätter | Bloodsucker von 0 hochsetzen = Verhalten, das Vanilla nie nutzt → „experimental"; Chimera trotz Verbotsliste (3.3) → Hypothese |

Erfüllt MetalMessiah0s drei Punkte: mehr Spawns (Lager + Frequenz), mehr
Prozent Mutanten (Anteil), Arten wählen (Gewichte je Art / Deckel je Typ).
„Kleine Viecher / mittlere / große Räuber" ließe sich als drei Gruppen-Regler
über die Arten legen (klein: Tushkan/Rat/Blinddog/Cat; mittel: Boar/Flesh/
Snork/Pseudodog; groß: Bloodsucker/Chimera/Controller/Burer/Pseudogiant).

Umsetzung: `NEEDED_FILES` + `ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg.bin`
+ `LairPrototypes.cfg.bin`, `CACHE_SCHEMA` 12→13, Accessoren `gd.director` /
`gd.lairs`, Patch-Dateien `ALifePrototypes/ALifeDirectorScenarioPrototypes/…_patch_<Mod>.cfg`
und `LairPrototypes/LairPrototypes_patch_<Mod>.cfg`, eigener Abschnitt im
NPCs-&-AI-Tab neben dem A-Life-Block, Tooltips mit dem Hinweis auf
`MaxAgentsCount` (mit anheben) und auf die Verzögerung bei bestehenden Saves.

---

## 8. WARNUNGEN

- **Arrays nie ersetzen:** `ProhibitedAgentTypes`, `RestrictedObjPrototypeSIDs`,
  `FallbackNPCTypes`, `ScenarioSquads.[k]`, Rang-/Typ-Listen. Nur Skalar-
  Blätter patchen (`MaxCount`, `ScenarioWeight`, Delays, `MaxSpawnQuantity`,
  Timer). Neue Szenarien/Arten anlegen ist tabu.
- **Story-Lager** mit 6/30/30-Timern (4.4) und **Guard-Lager** (Basis-Wachen)
  nicht skalieren. `RestingLairDefault`-Sonderschlüssel (4.5) im ersten
  Ausbau nicht anfassen.
- **Untergrenzen:** `MaxSpawnQuantity ≥ 1` und beim Verkleinern ≥
  min(Vanilla, Σ `MinQuantityPerArchetype`) (4.6); `MaxCount` ≥ 1, außer
  Vanilla 0 bleibt 0; `ScenarioWeight` ganzzahlig ≥ 0, Vanilla 0 bleibt 0;
  `SpawnDelayMin ≥ 5`, `Min ≤ Max`.
- **`MaxAgentsCount` (52)** deckelt alles Online — Tooltip: mit anheben, sonst
  bremst der Deckel; CPU-/Performance-Kosten ehrlich nennen.
- **Bestehende Saves:** Lager-Bestände werden nicht sofort neu gewürfelt
  (`GameTimeOfflineToRerollLairData` 14400 s Spielzeit, Refill-Cooldowns der
  Policy). Wirkung erst nach Schlafen/Regionswechsel — steht auch bei der
  Community-Mod.
- **Hypothesen, die der In-Game-Test klären muss:** Rudel = `MaxCount` ×
  `AliveMultiplier` (3.2); Verbotsliste vs. explizite Szenarien (3.3);
  ob Gewichte von 0 auf > 0 überhaupt Spawns erzeugen (Bloodsucker in Global).
- Keine absoluten lokalen Pfade in Code oder Doku; Werte nie hardcoden.
