# Fraktionsbeziehungen — Recherche (verifiziert am 02.09.2026)

Quelle: `vanilla/Stalker2/Content/GameLite/GameData/RelationPrototypes.cfg`
(1.210 Zeilen, **genau EIN** Top-Level-Struct `Default`). Daneben liegen
`Relations.csv` (Dev-Matrix derselben Werte, gute Gegenprobe) und
`RelationColors*.json` (nur UI-Farben).

**Korrektur zur ROADMAP:** Dort standen „644 Paare" — tatsächlich sind es
**582** (programmatisch gezählt, Quersumme unten). Die ROADMAP-Zeile ist
korrigiert.

## Struktur von `Default` (alle Pfade in Patch-Schreibweise)

| Pfad | Inhalt | Vanilla |
|---|---|---|
| `Default.RelationVersion` | Versionszähler des Beziehungs-Datensatzes | **7** |
| `Default.Relations.<A><->B>` | 582 Beziehungspaare, diskrete Werte | siehe Tabellen |
| `Default.Factions.<Kind>` | 93 Fraktionen als Baum (`Kind = Eltern`) | 3 Wurzeln: `Humanoid`, `Player`, `Mutant` |
| `Default.RelationLevelRanges` | 5 Bereiche Zahl → Level | s. u. |
| `Default.MinRelationLevelToTrade` | Handels-Schwelle | `ERelationLevel::Disaffection` |
| `Default.CharacterReactions` | 8 Event-Tabellen (Damage/Kill/Heal/Wounded/KillWounded/Grenade/FractionDamage/Melee), Reputations-Deltas je Übergang | z. B. Kill: `Neutral->Friend = -2000` |
| `Default.FactionReactions` | dieselben 8 Events auf Fraktionsebene (kleinere Werte, z. B. Kill `Neutral->Friend = -10`); **`[5]` (Grenade) ist LEER** | |
| `Default.ReputationRollbackCooldown` | Rollback lokaler Reaktionen (Sekunden) | 3600 |
| `Default.Hub/LairReputationRollbackCooldownModifier` | Rollback-Tempo in Hubs/Lagern | 0.05 / 0.1 |
| `Default.FactionRollbackCooldowns.<Fraktion>` | Kürzerer Rollback je Fraktion (19 Einträge) | alle 900 |
| `Default.RelationUpdateDeltas` | **Update-Mechanismus für Saves** (s. u.) | ein leerer Eintrag `[0]` mit `RelationVersion = 0` |
| `Default.ExpansionPolicies.AttackLairRestrictions` | wer darf wessen Lager angreifen (A-Life), `A->B = true` | 74 Einträge |
| `Default.PositiveReactionsExcludedFactions` / `Negative…` | Story-Schutz: Paare ohne Reputations-Drift (Arrays, 36 / 26 Einträge) | u. a. `Player<->Monolith` |

### RelationLevelRanges (Zahl → Verhalten)

| Bereich | Level | Bedeutung (belegt durch CoreVariables + RSO-Mod, s. u.) |
|---|---|---|
| ≤ −800 | `Enemy` | Kill on sight, kein Handel |
| −799 … −201 | `Disaffection` | reden/handeln erlaubt (Vanilla-Handelsschwelle) |
| −200 … 200 | `Neutral` | Standard |
| 201 … 99999 | `Friend` | beste Techniker-Preise |
| exakt 100000 | 5. Stufe (intern, vmtl. „Self") | taucht in Reaktions-Tabellen als Ziel `…->Self` auf |

`CoreVariables.cfg` → `ReputationRepairCostModifiers`: Reparaturkosten
skalieren mit dem Level (Enemy 2.0 / Disaffection 1.5 / Neutral 1.0 /
Friend 0.75) — Beziehungen haben also auch einen Ökonomie-Effekt.

### Die diskrete Werteskala

Vanilla benutzt NUR diese 10 Werte (Verteilung über alle 582 Paare):
0 (×324), −800 (×167), −799 (×27), 800 (×21), 600 (×19), −599 (×11),
201 (×7), −600 (×3), −399 (×2), −299 (×1).
**Achtung Grenzfälle:** −799 ist noch Disaffection, −800 ist Enemy;
201 ist schon Friend. GSC setzt bewusst „−599 statt −600" u. ä., um klar
im gewünschten Level zu bleiben.

## Zählungen (Quersumme)

- 582 Paare gesamt = 62 mit `Player` + 520 ohne.
- Player: 11 ≠ 0 (7× −800: `Mutant`, `ArenaEnemy`, `Bandits`, `Monolith`,
  `Militaries`, `Mercenaries`, `EnemyVarta`; 3× −600: `VaranBandits`,
  `ShahBandits`, `NoonFaustians`; 1× +800: `ArenaFriend`), 51× 0.
- Ohne Player: 247 ≠ 0, 273 × 0. (62+247+273 = 582 ✓)

## Der Save-Mechanismus (RelationVersion) — WICHTIGSTE ERKENNTNIS

- Die Beziehungswerte werden **beim Spielstart in den Save kopiert und
  leben danach im Save** (Reputation ändert sich durchs Spielen). Ein
  geänderter Baseline-Wert in der cfg erreicht einen bestehenden
  Spielstand daher NICHT automatisch.
- GSC hat dafür einen eingebauten Migrationsweg: `RelationVersion = 7`
  plus `RelationUpdateDeltas` (im Vanilla-Stand ein leerer Eintrag
  `[0]` mit `RelationVersion = 0`, `RelationDeltas =` leer). Es gibt
  **kein befülltes Vanilla-Beispiel** — die exakte Delta-Syntax ist
  unbekannt und `RelationVersion`/`RelationDeltas` kommen in KEINER
  anderen cfg der Spieldaten vor (geprüft per Volltextsuche).
- Praxis-Beleg aus der Community: Der größte Relations-Mod
  ([RSO, Nexus-Mod 2009](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2009))
  schreibt „Only works with New game / NOT working with Story mode" —
  der Autor hat Save-Migration also nicht gelöst oder nicht versucht.
- **Plan für unser Tool:** Baseline-Werte patchen UND `RelationVersion`
  live gelesen +1 patchen (aktuell also 7 → 8). Hypothese: Beim Laden
  merkt das Spiel „Save-Version < cfg-Version" und übernimmt die neuen
  Werte. **Das ist bis zum In-Game-Test eine HYPOTHESE** — der Tab
  bekommt bis dahin einen ehrlichen Disclaimer („verified on new games;
  effect on existing saves untested"). Der In-Game-Test ist einfach:
  `Bandits<->Player` auf +800, bestehenden Save laden, schauen ob
  Banditen im Feld freundlich sind.
- Risiko des Bumps: Speichert ein Save unsere Version 8 und GSC liefert
  später selbst Version 8 mit echten Deltas, würden diese Saves GSCs
  Migration überspringen. Bewusst in Kauf genommen (GSC hat in 2 Jahren
  Patches genau 7 Versionen verbraucht); ins FAQ schreiben.

## Runtime-Verhalten, das der Patch NICHT kontrolliert

(belegt durch RSO-Erfahrungsbericht + Struktur der Datei)

1. **Quests/Skripte ändern Beziehungen zur Laufzeit** —
   `ERelationLevel::` wird auch in `QuestNodePrototypes.cfg`,
   `DialogPrototypes.cfg`, `InfotopicPrototypes.cfg`,
   `AIPrototypes/ThreatPrototypes.cfg` benutzt. Story-Beats überschreiben
   unsere Werte gezielt (und sollen das).
2. **Scripted NPCs** haben feste Individual-Beziehungen (nicht
   fraktionsgebunden).
3. **Rollback**: Das Spiel setzt lokale Verschlechterungen nach
   `ReputationRollbackCooldown` zurück; Hub-Wachen können in gedrehten
   Konstellationen buggy „neutral" zurückfallen (RSO Known issue 1/2).
4. `CharacterReactions` (groß, lokal, temporär) vs. `FactionReactions`
   (klein, global, permanent) — zwei getrennte Systeme.

## WARNUNGEN — nicht anfassen / nicht in die GUI

- **Story-/Boss-/Arena-Fraktionen** dürfen NICHT in die GUI (Kämpfe und
  Quest-Logik hängen daran): `ScarBoss_Faction`, `KorshunovBoss_Faction`,
  `StrelokBoss_Faction`, `FaustBoss_Faction`, `ArenaEnemy`, `ArenaFriend`,
  `EnemyVarta`, `SQ72_Varta`, `SQ89_SidorMercs`,
  `CNPP_Archanomaly_PhantomZombie`, `NoonFaustians` (Faust-Anhänger),
  `VartaSIRCAA`, `SIRCAA_Scientist`, `MALACHITE_Scientist`,
  `DepoVictims`, `DocileLabMutants`, `YantarZombie`, `NoahLesya`,
  `Lessy`, `FriendlyBlinddog`, `MoldyBlinddog`, `CrazyGuardians` und
  alle Sub-Banditen-Lager (`VaranStashBandits` …) — kurz: **alles, was
  nicht in der Haupt-Fraktionsliste unten steht.**
- `PositiveReactionsExcludedFactions`/`Negative…` sind Arrays — per
  bpatch nur index-weise überschreibbar, ANHÄNGEN ungeklärt. Nicht
  patchen (Story-Schutz von GSC, RSO hat sie entfernt und braucht
  deshalb New Game).
- `RelationUpdateDeltas` nicht befüllen (Syntax unbekannt, s. o.).
- `Factions`-Baum nicht umhängen (NPC-Prototypen referenzieren die
  Fraktions-SIDs; Vererbung der Paare läuft über den Baum).
- Werte außerhalb −800…800 nicht anbieten (Vanilla-Skala; RSO berichtet
  „can go below −800 / above 800" nur durch Laufzeit-Drift).
- Die leere `FactionReactions[5]`-Tabelle (Grenade) leer lassen.

## Empfehlung für den Tab (Umsetzung mit `add-tweak`)

**Haupt-Fraktionen für die GUI** (12 + Mutanten-Schirm; PDA-Namen in
Klammern = Anzeigename): `Neutrals` (Loners), `Bandits`, `Militaries`
(Military), `Varta` (Ward), `Duty`, `Freedom`, `Mercenaries`, `Monolith`,
`Noon` (Noontide), `Spark`, `Corpus` (Corps), `Scientists` — plus
`Mutant` (Schirm-Fraktion aller Mutanten).

1. **Sektion „Player vs. factions"**: je Haupt-Fraktion eine
   5-Stufen-Auswahl (OptionMenu): `(vanilla)` / Enemy −800 /
   Disaffected −400 / Neutral 0 / Friend 600 / Ally 800. Vanilla-Wert
   live aus `Default.Relations.<X><->Player>` lesen; `(vanilla)` = kein
   Patch (eiserne Regel). 13 Steuerelemente.
2. **Sektion „Faction vs. faction"**: aufklappbarer Baum wie beim
   Waffen-Baum — je Haupt-Fraktion ein Block mit ihren Paaren zu den
   anderen Haupt-Fraktionen (66 einzigartige Paare + 12
   `X<->Mutant`-Paare), gleiche 5-Stufen-Auswahl. Lazy bauen wie
   `IwCategoryBlock`.
3. **Sektion „Reputation mechanics"** (Regler): Rollback-Cooldown-Faktor
   (`ReputationRollbackCooldown` ×25–400 %, inkl. der 19
   `FactionRollbackCooldowns` und beider Modifier), optional später:
   Handels-Schwelle, Reaktions-Stärke.
4. Patch schreibt zusätzlich IMMER `RelationVersion = <vanilla+1>`,
   sobald mindestens ein Beziehungswert abweicht.
5. Datei in `NEEDED_FILES` aufnehmen ⇒ **CACHE_SCHEMA 10 → 11**.
6. Disclaimer im Tab (englisch): quests/scripts override relations at
   any time; effect on existing saves is untested; changes are designed
   for the living world (A-Life), not for story encounters.

Quellen neben den Spieldaten:
[RSO-Mod](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2009)
(Mechanik-Erfahrungswerte),
[Faction Relations Live PDA Tab](https://www.nexusmods.com/stalker2heartofchornobyl/mods/2557)
(liest Beziehungen aus dem Save — Beleg für „Werte leben im Save").

---

# Vollständige Vanilla-Tabellen (generiert aus der cfg, 02.09.2026)

### Fraktionsbaum (93 Fraktionen, Kind → Eltern-Vererbung)

- **`Humanoid`** (Wurzel)
  - `Bandits`
    - `WildBandits`
    - `NeutralBandits`
    - `VaranBandits`
      - `VaranStashBandits`
    - `RooseveltBandits`
    - `ShahBandits`
    - `LokotBandits`
    - `DepoBandits`
    - `DocentBandits`
    - `KosakBandits`
    - `SultanBandits`
    - `KabanBandits`
    - `SQ89_SidorMercs`
  - `Monolith`
    - `FaustBoss_Faction`
  - `FreeStalkers`
    - `Freedom`
    - `Neutrals`
      - `Diggers`
      - `ShevchenkoStalkers`
      - `MoleStalkers`
      - `NoahLesya`
    - `Noon`
      - `NoonFaustians`
    - `Scientists`
      - `SIRCAA_Scientist`
      - `MALACHITE_Scientist`
    - `Flame`
    - `Spark`
      - `SparkLesnichestvo`
      - `CrazyGuardians`
      - `ScarBoss_Faction`
  - `Army`
    - `Duty`
    - `Varta`
      - `AzimutVarta`
      - `VartaLesnichestvo`
      - `IkarVarta`
      - `EnemyVarta`
      - `VartaSIRCAA`
      - `KorshunovBoss_Faction`
    - `Militaries`
      - `GarmataMilitaries`
      - `SphereMilitaries`
      - `AzimuthMilitaries`
      - `DrozdMilitaries`
      - `NeutralMSOP`
    - `Mercenaries`
      - `UdavMercenaries`
      - `KlenMercenaries`
    - `Law`
    - `Corpus`
      - `YanovCorpus`
      - `CorpusStorm`
  - `DepoVictims`
  - `SafariHunters`
  - `ArenaEnemy`
  - `ArenaFriend`
    - `CNPP_Archanomaly_PhantomZombie`
  - `SQ72_Varta`
- **`Player`** (Wurzel)
- **`Mutant`** (Wurzel)
  - `Controller`
  - `Poltergeist`
  - `Bloodsucker`
  - `Zombie`
    - `YantarZombie`
  - `Chimera`
  - `Burer`
  - `Pseudogiant`
  - `Anamorph`
  - `Sinister`
  - `Pseudobear`
  - `Snork`
  - `Pseudodog`
  - `Boar`
  - `Flesh`
  - `Beaver`
  - `Ratwolf`
  - `Deer`
  - `Rat`
  - `Tushkan`
  - `Stickman`
  - `Blinddog`
    - `FriendlyBlinddog`
    - `Lessy`
    - `MoldyBlinddog`
  - `Bayun`
  - `DocileLabMutants`
  - `AlliedMutants`
  - `StrelokBoss_Faction`

### Alle Player-Paare (62)

| Paar | Vanilla | Level |
|---|---|---|
| `Army<->Player` | 0 | Neutral |
| `FreeStalkers<->Player` | 0 | Neutral |
| `Mutant<->Player` | -800 | Enemy |
| `Humanoid<->Player` | 0 | Neutral |
| `AlliedMutants<->Player` | 0 | Neutral |
| `ArenaEnemy<->Player` | -800 | Enemy |
| `Bandits<->Player` | -800 | Enemy |
| `Monolith<->Player` | -800 | Enemy |
| `Duty<->Player` | 0 | Neutral |
| `Freedom<->Player` | 0 | Neutral |
| `Varta<->Player` | 0 | Neutral |
| `Neutrals<->Player` | 0 | Neutral |
| `Militaries<->Player` | -800 | Enemy |
| `Noon<->Player` | 0 | Neutral |
| `Scientists<->Player` | 0 | Neutral |
| `Mercenaries<->Player` | -800 | Enemy |
| `Spark<->Player` | 0 | Neutral |
| `Corpus<->Player` | 0 | Neutral |
| `NeutralBandits<->Player` | 0 | Neutral |
| `VaranBandits<->Player` | -600 | Disaffection |
| `RooseveltBandits<->Player` | 0 | Neutral |
| `ShahBandits<->Player` | -600 | Disaffection |
| `DepoBandits<->Player` | 0 | Neutral |
| `DocentBandits<->Player` | 0 | Neutral |
| `SultanBandits<->Player` | 0 | Neutral |
| `Diggers<->Player` | 0 | Neutral |
| `UdavMercenaries<->Player` | 0 | Neutral |
| `ShevchenkoStalkers<->Player` | 0 | Neutral |
| `SIRCAA_Scientist<->Player` | 0 | Neutral |
| `MALACHITE_Scientist<->Player` | 0 | Neutral |
| `NoonFaustians<->Player` | -600 | Disaffection |
| `IkarVarta<->Player` | 0 | Neutral |
| `NeutralMSOP<->Player` | 0 | Neutral |
| `EnemyVarta<->Player` | -800 | Enemy |
| `Law<->Player` | 0 | Neutral |
| `Flame<->Player` | 0 | Neutral |
| `DepoVictims<->Player` | 0 | Neutral |
| `SphereMilitaries<->Player` | 0 | Neutral |
| `VaranStashBandits<->Player` | 0 | Neutral |
| `SafariHunters<->Player` | 0 | Neutral |
| `GarmataMilitaries<->Player` | 0 | Neutral |
| `AzimutVarta<->Player` | 0 | Neutral |
| `AzimuthMilitaries<->Player` | 0 | Neutral |
| `KabanBandits<->Player` | 0 | Neutral |
| `YanovCorpus<->Player` | 0 | Neutral |
| `VartaLesnichestvo<->Player` | 0 | Neutral |
| `SparkLesnichestvo<->Player` | 0 | Neutral |
| `CrazyGuardians<->Player` | 0 | Neutral |
| `KlenMercenaries<->Player` | 0 | Neutral |
| `DrozdMilitaries<->Player` | 0 | Neutral |
| `LokotBandits<->Player` | 0 | Neutral |
| `FriendlyBlinddog<->Player` | 0 | Neutral |
| `KosakBandits<->Player` | 0 | Neutral |
| `MoleStalkers<->Player` | 0 | Neutral |
| `SQ72_Varta<->Player` | 0 | Neutral |
| `VartaSIRCAA<->Player` | 0 | Neutral |
| `NoahLesya<->Player` | 0 | Neutral |
| `YantarZombie<->Player` | 0 | Neutral |
| `DocileLabMutants<->Player` | 0 | Neutral |
| `Lessy<->Player` | 0 | Neutral |
| `ArenaFriend<->Player` | 800 | Friend |
| `Player<->Player` | 0 | Neutral |

### Nicht-neutrale Paare ohne Player (247; die uebrigen 273 Nicht-Player-Paare stehen alle auf 0)

| Paar | Vanilla | Level |
|---|---|---|
| `AlliedMutants<->AlliedMutants` | 600 | Friend |
| `ArenaEnemy<->ArenaEnemy` | 600 | Friend |
| `ArenaFriend<->ArenaEnemy` | -800 | Enemy |
| `Bandits<->Bandits` | 600 | Friend |
| `Bandits<->FreeStalkers` | -800 | Enemy |
| `Bandits<->Humanoid` | -800 | Enemy |
| `Bandits<->Mutant` | -800 | Enemy |
| `Bayun<->Bayun` | 800 | Friend |
| `Bayun<->Blinddog` | -800 | Enemy |
| `Bayun<->Bloodsucker` | -800 | Enemy |
| `Bayun<->Boar` | -800 | Enemy |
| `Bayun<->Burer` | -800 | Enemy |
| `Bayun<->Chimera` | -800 | Enemy |
| `Bayun<->Controller` | -800 | Enemy |
| `Bayun<->Flesh` | -800 | Enemy |
| `Bayun<->Pseudodog` | -800 | Enemy |
| `Bayun<->Pseudogiant` | -800 | Enemy |
| `Bayun<->Snork` | -800 | Enemy |
| `Bayun<->Tushkan` | -800 | Enemy |
| `Bayun<->Zombie` | -800 | Enemy |
| `Blinddog<->Blinddog` | 800 | Friend |
| `Blinddog<->Bloodsucker` | -800 | Enemy |
| `Blinddog<->Boar` | -800 | Enemy |
| `Blinddog<->Burer` | -800 | Enemy |
| `Blinddog<->Chimera` | -800 | Enemy |
| `Blinddog<->Controller` | -800 | Enemy |
| `Blinddog<->Flesh` | -800 | Enemy |
| `Blinddog<->Snork` | -800 | Enemy |
| `Blinddog<->Tushkan` | -800 | Enemy |
| `Blinddog<->Zombie` | -800 | Enemy |
| `Bloodsucker<->Bloodsucker` | 800 | Friend |
| `Bloodsucker<->Controller` | -800 | Enemy |
| `Boar<->Bloodsucker` | -800 | Enemy |
| `Boar<->Boar` | 800 | Friend |
| `Boar<->Burer` | -800 | Enemy |
| `Boar<->Chimera` | -800 | Enemy |
| `Boar<->Controller` | -800 | Enemy |
| `Boar<->Pseudodog` | -800 | Enemy |
| `Boar<->Pseudogiant` | -800 | Enemy |
| `Boar<->Snork` | -800 | Enemy |
| `Boar<->Zombie` | -800 | Enemy |
| `Burer<->Bloodsucker` | -800 | Enemy |
| `Burer<->Burer` | 800 | Friend |
| `Burer<->Chimera` | -800 | Enemy |
| `Burer<->Controller` | -800 | Enemy |
| `Burer<->Zombie` | -800 | Enemy |
| `Chimera<->Bloodsucker` | -800 | Enemy |
| `Chimera<->Chimera` | 800 | Friend |
| `Chimera<->Zombie` | -800 | Enemy |
| `Controller<->Controller` | 800 | Friend |
| `Corpus<->Bandits` | -800 | Enemy |
| `Corpus<->Corpus` | 600 | Friend |
| `Corpus<->Duty` | 201 | Friend |
| `Corpus<->Mercenaries` | -799 | Disaffection |
| `Corpus<->Monolith` | -800 | Enemy |
| `Corpus<->Mutant` | -800 | Enemy |
| `Corpus<->Noon` | -599 | Disaffection |
| `Corpus<->Scientists` | 201 | Friend |
| `Deer<->Bloodsucker` | -800 | Enemy |
| `Deer<->Burer` | -800 | Enemy |
| `Deer<->Controller` | -800 | Enemy |
| `Deer<->Deer` | 800 | Friend |
| `Deer<->Snork` | -800 | Enemy |
| `Deer<->Zombie` | -800 | Enemy |
| `DocentBandits<->Corpus` | -800 | Enemy |
| `DocentBandits<->DocentBandits` | 600 | Friend |
| `DocentBandits<->Duty` | -800 | Enemy |
| `DocentBandits<->Mercenaries` | -799 | Disaffection |
| `DocentBandits<->Militaries` | -800 | Enemy |
| `DocentBandits<->Monolith` | -800 | Enemy |
| `DocentBandits<->Mutant` | -800 | Enemy |
| `DocentBandits<->Neutrals` | -800 | Enemy |
| `DocentBandits<->Noon` | -800 | Enemy |
| `DocentBandits<->Scientists` | -799 | Disaffection |
| `DocentBandits<->Spark` | -799 | Disaffection |
| `DocentBandits<->Varta` | -799 | Disaffection |
| `Duty<->Bandits` | -800 | Enemy |
| `Duty<->Duty` | 600 | Friend |
| `Duty<->Monolith` | -800 | Enemy |
| `Duty<->Mutant` | -800 | Enemy |
| `Flesh<->Bloodsucker` | -800 | Enemy |
| `Flesh<->Burer` | -800 | Enemy |
| `Flesh<->Chimera` | -800 | Enemy |
| `Flesh<->Controller` | -800 | Enemy |
| `Flesh<->Flesh` | 800 | Friend |
| `Flesh<->Pseudodog` | -800 | Enemy |
| `Flesh<->Pseudogiant` | -800 | Enemy |
| `Flesh<->Snork` | -800 | Enemy |
| `Flesh<->Zombie` | -800 | Enemy |
| `Freedom<->Bandits` | -800 | Enemy |
| `Freedom<->Duty` | -599 | Disaffection |
| `Freedom<->Freedom` | 600 | Friend |
| `Freedom<->Monolith` | -800 | Enemy |
| `Freedom<->Mutant` | -800 | Enemy |
| `Humanoid<->Mutant` | -800 | Enemy |
| `Mercenaries<->Bandits` | -599 | Disaffection |
| `Mercenaries<->Duty` | -799 | Disaffection |
| `Mercenaries<->Freedom` | -599 | Disaffection |
| `Mercenaries<->Mercenaries` | 600 | Friend |
| `Mercenaries<->Militaries` | -800 | Enemy |
| `Mercenaries<->Monolith` | -800 | Enemy |
| `Mercenaries<->Mutant` | -800 | Enemy |
| `Mercenaries<->Neutrals` | -799 | Disaffection |
| `Mercenaries<->Noon` | -799 | Disaffection |
| `Mercenaries<->Varta` | -599 | Disaffection |
| `Militaries<->Bandits` | -800 | Enemy |
| `Militaries<->Freedom` | -799 | Disaffection |
| `Militaries<->Militaries` | 600 | Friend |
| `Militaries<->Monolith` | -800 | Enemy |
| `Militaries<->Mutant` | -800 | Enemy |
| `Militaries<->Neutrals` | -800 | Enemy |
| `Monolith<->Bandits` | -800 | Enemy |
| `Monolith<->Humanoid` | -800 | Enemy |
| `Monolith<->Monolith` | 600 | Friend |
| `Monolith<->Mutant` | -800 | Enemy |
| `Mutant<->Army` | -800 | Enemy |
| `Mutant<->FreeStalkers` | -800 | Enemy |
| `NeutralBandits<->Corpus` | -800 | Enemy |
| `NeutralBandits<->Duty` | -800 | Enemy |
| `NeutralBandits<->Mercenaries` | -599 | Disaffection |
| `NeutralBandits<->Militaries` | -800 | Enemy |
| `NeutralBandits<->Monolith` | -800 | Enemy |
| `NeutralBandits<->Mutant` | -800 | Enemy |
| `NeutralBandits<->NeutralBandits` | 600 | Friend |
| `NeutralBandits<->Noon` | -799 | Disaffection |
| `NeutralBandits<->Scientists` | -799 | Disaffection |
| `NeutralBandits<->Spark` | -799 | Disaffection |
| `NeutralBandits<->Varta` | -799 | Disaffection |
| `Neutrals<->Bandits` | -800 | Enemy |
| `Neutrals<->Monolith` | -800 | Enemy |
| `Neutrals<->Mutant` | -800 | Enemy |
| `Neutrals<->Neutrals` | 600 | Friend |
| `Neutrals<->Varta` | -399 | Disaffection |
| `Noon<->Bandits` | -800 | Enemy |
| `Noon<->Duty` | -599 | Disaffection |
| `Noon<->Freedom` | -599 | Disaffection |
| `Noon<->Militaries` | -800 | Enemy |
| `Noon<->Monolith` | -800 | Enemy |
| `Noon<->Mutant` | -800 | Enemy |
| `Noon<->Neutrals` | -599 | Disaffection |
| `Noon<->Noon` | 600 | Friend |
| `Noon<->Varta` | -399 | Disaffection |
| `Poltergeist<->Poltergeist` | 800 | Friend |
| `Pseudodog<->Bloodsucker` | -800 | Enemy |
| `Pseudodog<->Burer` | -800 | Enemy |
| `Pseudodog<->Chimera` | -800 | Enemy |
| `Pseudodog<->Pseudodog` | 800 | Friend |
| `Pseudodog<->Pseudogiant` | -800 | Enemy |
| `Pseudodog<->Snork` | -800 | Enemy |
| `Pseudodog<->Zombie` | -800 | Enemy |
| `Pseudogiant<->Burer` | -800 | Enemy |
| `Pseudogiant<->Chimera` | -800 | Enemy |
| `Pseudogiant<->Controller` | -800 | Enemy |
| `Pseudogiant<->Pseudogiant` | 800 | Friend |
| `Pseudogiant<->Zombie` | -800 | Enemy |
| `Rat<->Rat` | 800 | Friend |
| `RooseveltBandits<->Corpus` | -800 | Enemy |
| `RooseveltBandits<->Mercenaries` | -799 | Disaffection |
| `RooseveltBandits<->Militaries` | -800 | Enemy |
| `RooseveltBandits<->Monolith` | -800 | Enemy |
| `RooseveltBandits<->Mutant` | -800 | Enemy |
| `RooseveltBandits<->Neutrals` | -800 | Enemy |
| `RooseveltBandits<->Noon` | -800 | Enemy |
| `RooseveltBandits<->RooseveltBandits` | 600 | Friend |
| `RooseveltBandits<->Scientists` | -799 | Disaffection |
| `RooseveltBandits<->Spark` | -799 | Disaffection |
| `RooseveltBandits<->Varta` | -799 | Disaffection |
| `Scientists<->Bandits` | -800 | Enemy |
| `Scientists<->Duty` | 201 | Friend |
| `Scientists<->Militaries` | 201 | Friend |
| `Scientists<->Monolith` | -800 | Enemy |
| `Scientists<->Mutant` | -800 | Enemy |
| `Scientists<->Scientists` | 600 | Friend |
| `ShahBandits<->Corpus` | -800 | Enemy |
| `ShahBandits<->Duty` | -800 | Enemy |
| `ShahBandits<->Freedom` | 201 | Friend |
| `ShahBandits<->Mercenaries` | -799 | Disaffection |
| `ShahBandits<->Militaries` | -800 | Enemy |
| `ShahBandits<->Monolith` | -800 | Enemy |
| `ShahBandits<->Mutant` | -800 | Enemy |
| `ShahBandits<->Neutrals` | -800 | Enemy |
| `ShahBandits<->Noon` | -800 | Enemy |
| `ShahBandits<->RooseveltBandits` | -800 | Enemy |
| `ShahBandits<->Scientists` | -799 | Disaffection |
| `ShahBandits<->ShahBandits` | 600 | Friend |
| `ShahBandits<->Spark` | -799 | Disaffection |
| `ShahBandits<->Varta` | -799 | Disaffection |
| `Snork<->Bloodsucker` | -800 | Enemy |
| `Snork<->Burer` | -800 | Enemy |
| `Snork<->Chimera` | -800 | Enemy |
| `Snork<->Controller` | -800 | Enemy |
| `Snork<->Pseudogiant` | -800 | Enemy |
| `Snork<->Snork` | 800 | Friend |
| `Snork<->Zombie` | -800 | Enemy |
| `Spark<->Bandits` | -800 | Enemy |
| `Spark<->Mercenaries` | -799 | Disaffection |
| `Spark<->Militaries` | -800 | Enemy |
| `Spark<->Monolith` | -800 | Enemy |
| `Spark<->Mutant` | -800 | Enemy |
| `Spark<->Noon` | -599 | Disaffection |
| `Spark<->Scientists` | 201 | Friend |
| `Spark<->Spark` | 600 | Friend |
| `Spark<->Varta` | -599 | Disaffection |
| `SultanBandits<->Corpus` | -799 | Disaffection |
| `SultanBandits<->Duty` | -800 | Enemy |
| `SultanBandits<->Mercenaries` | -799 | Disaffection |
| `SultanBandits<->Militaries` | -800 | Enemy |
| `SultanBandits<->Monolith` | -800 | Enemy |
| `SultanBandits<->Mutant` | -800 | Enemy |
| `SultanBandits<->Noon` | -799 | Disaffection |
| `SultanBandits<->Scientists` | -799 | Disaffection |
| `SultanBandits<->SultanBandits` | 600 | Friend |
| `SultanBandits<->Varta` | -799 | Disaffection |
| `Tushkan<->Bloodsucker` | -800 | Enemy |
| `Tushkan<->Boar` | -800 | Enemy |
| `Tushkan<->Burer` | -800 | Enemy |
| `Tushkan<->Chimera` | -800 | Enemy |
| `Tushkan<->Controller` | -800 | Enemy |
| `Tushkan<->Flesh` | -800 | Enemy |
| `Tushkan<->Pseudodog` | -800 | Enemy |
| `Tushkan<->Pseudogiant` | -800 | Enemy |
| `Tushkan<->Snork` | -800 | Enemy |
| `Tushkan<->Tushkan` | 800 | Friend |
| `Tushkan<->Zombie` | -800 | Enemy |
| `Varta<->Bandits` | -800 | Enemy |
| `Varta<->Duty` | 201 | Friend |
| `Varta<->Monolith` | -800 | Enemy |
| `Varta<->Mutant` | -800 | Enemy |
| `Varta<->Varta` | 600 | Friend |
| `VartaSIRCAA<->AlliedMutants` | -800 | Enemy |
| `VartaSIRCAA<->ArenaEnemy` | -800 | Enemy |
| `VartaSIRCAA<->Bandits` | -800 | Enemy |
| `VartaSIRCAA<->DepoBandits` | -800 | Enemy |
| `VartaSIRCAA<->DocentBandits` | -800 | Enemy |
| `VartaSIRCAA<->Monolith` | -800 | Enemy |
| `VartaSIRCAA<->Mutant` | -800 | Enemy |
| `VartaSIRCAA<->RooseveltBandits` | -800 | Enemy |
| `VartaSIRCAA<->SIRCAA_Scientist` | 800 | Friend |
| `VartaSIRCAA<->Scientists` | 800 | Friend |
| `VartaSIRCAA<->ShahBandits` | -800 | Enemy |
| `VartaSIRCAA<->Spark` | -299 | Disaffection |
| `VartaSIRCAA<->SultanBandits` | -800 | Enemy |
| `VartaSIRCAA<->VaranBandits` | -800 | Enemy |
| `VartaSIRCAA<->Varta` | 800 | Friend |
| `Zombie<->Bloodsucker` | -800 | Enemy |
| `Zombie<->Controller` | 800 | Friend |
| `Zombie<->Zombie` | 800 | Friend |

### Werteverteilung aller 582 Paare

| Wert | Anzahl | Level |
|---|---|---|
| -800 | 167 | Enemy |
| -799 | 27 | Disaffection |
| -600 | 3 | Disaffection |
| -599 | 11 | Disaffection |
| -399 | 2 | Disaffection |
| -299 | 1 | Disaffection |
| 0 | 324 | Neutral |
| 201 | 7 | Friend |
| 600 | 19 | Friend |
| 800 | 21 | Friend |
