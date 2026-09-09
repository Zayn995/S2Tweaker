# Bericht: Animations-Desync, Carry-Weight-Interaktion und Empfehlungen für S2Tweaker v1.2

Stand: 30.08.2026, Spielversion 2.0.4 (UE 5.5.4). Unsichere Punkte sind mit **[unsicher]** markiert.

**Aktualisierung 09.09.2026 nach Dateipruefung:** NoHeadBob v2 und
Movement Modifications 2x/3x/UNINSTALL liegen nun lokal vor. Sie enthalten
nur cfg-Patches, keinen zusaetzlichen Animationsfix. Alle 17 Reset-Werte
stimmen mit der installierten Vanilla ueberein, aber die Datei hat keinen
Refresh-/Zustandswechsel-Mechanismus. Alle acht Carry-Weight-Paks von
Long Days 3.0 und 3.1 sind **byteidentisch**; die fruehere Gewichts-Fix-
Hypothese ist widerlegt (unten korrigiert). SCAM 2.3 liegt ebenfalls
bereits lokal vor. Detaillierte aktuelle Belege:
`out/workshop_review_2026-09-09/NEUE_DOWNLOADS_ERGEBNIS.md`.
Die uebrigen Engine-/Savegame-Aussagen dieses historischen Berichts sind
teils Hypothesen aus Nutzerberichten und keine eigenen Laufzeitnachweise.

---

## 1. Gibt es einen fertigen Fix/Workaround-Mod?

**In den bisher untersuchten Mods ist kein echter Fix nachgewiesen.** Die sechs am 09.09. geprueften Archive enthalten keinen Patch fuer Locomotion-Animationsraten oder passende neue Animationen. Daraus folgt keine Aussage ueber saemtliche veroeffentlichten Mods.

**Einziger verlinkbarer Workaround:**
- **"No HeadBob While Sprinting (CS Movement)"** — Nexus-Mod-Id **2414**, Autor blcksw0rdsman, lokal gepruefte Hauptdatei v2 vom 25.08.2026: https://www.nexusmods.com/stalker2heartofchornobyl/mods/2414
- **Arbeitsweise, Dateibefund v2 vom 09.09.:** Aendert Geschwindigkeitswerte in ObjPrototypes (Walk 370, Run 820, Jogging/Sprint/Crouch 370) sowie Ausdauer und ADS-Tempo. Der Autor verwendet dazu andere Tastenbelegungen. Der Sprint-Zustand wird nicht aus der Engine entfernt. Eine kleinere visuelle Animationsabweichung ist damit nicht nachgewiesen.
- **Grenzen:** Nutzer muss Keybinds selbst umlegen (Walk→Shift, Sprint→X); Footstep-Sounds laut Autor "slightly mismatched"; Sprint-Waffenabsenk-Animation entfällt. Ob der *visuelle* Bein-Desync ganz verschwindet, ist unbestätigt (nur 3 Endorsements, 103 Downloads) **[unsicher]**.

**Nicht geeignet als Fix, aber relevant:** "Faster Animations" (Nexus **2409**, onikenobi, v0.5) beweist, dass Play-Rate-Edits via Animation-**Montages** auf 2.0.x funktionieren — deckt aber bewusst nur Interaktionsanimationen ab, nicht die Blendspace-getriebene Locomotion. Auf SCAM (Nexus **672**) ist per-Stance-Animationsgeschwindigkeit nur ein unbeantworteter User-Wunsch (KoSm1cZny, 24.08.2026); SCAM-Autor v3fish diagnostiziert noch (29.08.: bittet um Video-Repro), kein Fix released.

---

## 2. Carry-Weight-Interaktion (wichtigster Teil für S2Tweaker)

**Betroffene Mod:** "Long Days - Carry Wght - Rep Cost - Upg Cost - MODULAR", Nexus-Mod **410**, Autor J412536987: https://www.nexusmods.com/stalker2heartofchornobyl/mods/410

**Was den Anim-Bruch triggert:** Seit Update 2.0 scheint die Locomotion-Animationsrate an den Encumbrance-Zustand und die Encumbrance-Schwellwerte gekoppelt. Long Days v3.0 änderte in `ObjWeightParamsPrototypes.cfg` MaxInventoryMass + Penalty-Schwellen (z. B. auf 9999/9997/9998); in Kombination mit SCAMs MovementParams-Änderungen brachen die Walk-Animationen ("Skif is taking 500 steps a minute"). Carry-Weight auf Default zurück → SCAM lief wieder. Das ist die Hypothese eines einzelnen Users (dogsounds, 21.08.2026), aber konsistent mit dem verifizierten Vanilla-Mechanismus (WeightEffectParams-Thresholds 50/60/70/80 kg → OverweightMovementVelocityChange-Effekte, VelocityChangeNoCap −15 %) **[unsicher: Kopplungsformel unbekannt]**.

**Was v3.1 (21.08.2026) aenderte, jetzt am Archiv verifiziert:** Nur die acht Upgrade-Cost-Paks wurden geaendert; Upgrade_Cost liegt dort nun unter EconomyDifficulty. Alle acht Carry-Weight-Paks sind in 3.0 und 3.1 byteidentisch. Die fruehere Vermutung, Gewichts-Patches seien neu erzeugt worden und haetten dadurch die Animation korrigiert, ist widerlegt. Die Ursache der damaligen Nutzerbeobachtung ist weiter offen.

**Konkret für S2Tweakers Gewichts-Patch:**
- **Aktuelle Daten verwenden:** S2Tweaker liest die Basiswerte aus der Installation (`gd.resolve`). Nach Spiel-Updates muss das Tweak-Pak neu erzeugt werden. Der Long-Days-Vergleich belegt dabei einen Struktur-Fix fuer Upgrade-Kosten, keinen Fix fuer Gewicht oder Animation.
- **Sicher:** Vanilla-Werte (kein Patch — ist schon so implementiert). Reines Gewichts-Tweaken *ohne* gleichzeitige Speed-Änderung gilt als unkritisch.
- **Riskant:** Encumbrance-Schwellen abweichend von Default **plus** MovementParams-Speed-Änderungen gleichzeitig — das ist die dokumentierte Bruch-Kombination.
- **Wenn Schwellen geändert werden:** konsistent als Satz verschieben (Long-Days-Muster: Penalties knapp unter neues Maximum, z. B. 9997/9998/9999), nie nur MaxInventoryMass isoliert.
- **Refresh-Trigger dokumentieren:** WeightParams greifen erst nach In-Game-Trigger (Hercules trinken oder Carry-Weight-Artefakt/Armor an- und ablegen); Speed-Werte erst nach Wasser/Granate/Health-Änderung — seit 2.0 werden Movement-Stats im **Savegame gecacht** (Mod 2375 liefert deshalb eine Uninstall-.pak).
- **`WalkTransitionCoef` (Vanilla 1.3, Player.MovementParams): niemals erhöhen** — macht Anim-Übergänge "stupidly fast" (User-Report KoSm1cZny, 29.08.2026) **[unsicher: Einzelquelle]**.

---

## 3. AnimBP/Asset-Lage und Machbarkeit eines echten Sync-Fixes

- **Asset:** Der exakte Pfad des Player-Locomotion-AnimBlueprints ist öffentlich **nirgends dokumentiert**. Bekannt: Player-Pawn = `Blueprint'/Game/GameLite/Blueprints/Characters/Player/BP_Stalker2Character'`; Player-Animationen unter `/Game/_STALKER2/Animations/Player/` (AnimCollections, Curves); das `AnimPath`-Feld der Player-BodyMesh-Prototypen ist **leer** → AnimInstance wird nativ/im Pawn-BP zugewiesen. Laut Autor von Auto-Walk (Nexus 2485) liegt die Gait-Auswahl und das Speed→PlayRate-Mapping in **nativem Code** — kein Blueprint-Hook.
- **Was ein echter Fix bräuchte:** Locomotion-Blendspace/AnimBP auschecken, editieren, für UE 5.5 neu cooken.
- **Machbarkeit:**
  - **Zone Kit (voll, ~700 GB):** Einziger theoretischer Weg — aber offizieller Known Issue: Blueprint-basierte Mods werden **in-game noch nicht unterstützt** (WIP). Selbst mit 700 GB Invest also derzeit ungewiss, ob ein editierter AnimBP überhaupt lädt **[unsicher, ob AnimBPs unter diesen Known Issue fallen]**.
  - **Mini SDK:** cfg-only (CreateMod.bat/PakCfgMod.bat), kann keine Assets/Blueprints anfassen → **für einen Anim-Fix nutzlos**.
  - **UE4SS auf 2.0.3/2.0.4:** Nur via "RE-UE4SS Compatibility Fix for Update 2.0" (Nexus **2341**, MigamaN142) auf experimentellem Build, alle Engine-Hooks müssen deaktiviert werden; 2.0.3-Kompatibilität fraglich, Crash-Report direkt nach 2.0.4. Da das Anim-Mapping nativ ist, ist ein Lua-basierter Play-Rate-Fix unbewiesen und unwahrscheinlich.
- **Fazit:** Für S2Tweaker (cfg-only-Tool) ist ein echter Sync-Fix **nicht realistisch**. Abwarten: Zone-Kit-Blueprint-Support oder ein SCAM-/Community-Fix (SCAM-Posts-Tab in 1–2 Wochen erneut prüfen).

---

## 4. Empfehlungen für S2Tweaker v1.2

**Tun:**
1. **Tooltip-Warnung auf allen Speed-Slidern:** "Speed-Änderungen desynchronisieren Lauf-Animation/Schritte — Spiel-Limitierung, kein Mod-Bug. Je weiter von Vanilla, desto sichtbarer. Seit Update 2.0 greifen Änderungen erst nach Trigger (ins Wasser treten / Granate)."
2. **Empfohlene Slider-Bereiche kennzeichnen:** ±10–20 % um Vanilla als "grüner" Bereich. Begründung: Mod 82 (−5 % Run/−20 % Sprint) läuft seit Nov 2024 ohne Desync-Beschwerden; Autor von Mod 2375 berichtet, dass Reduktion 3x→2x den Anim-Bruch sichtbar milderte — extreme Multiplikatoren brechen härter. Werte außerhalb farblich markieren (nicht hart begrenzen).
3. **Gait-Verhältnisse wahren:** Warnung, wenn Walk/Run/Jog/Sprint-Verhältnisse stark gestaucht werden (Bruch-Repro war Walk=160/Run=165). Vanilla: 160/370/625/820. Optional: gemeinsamer Faktor-Modus statt Einzelwerte.
4. **Kombi-Warnung Gewicht+Speed:** Wenn sowohl Gewichts- als auch Speed-Slider von Vanilla abweichen, UI-Hinweis auf die dokumentierte Konflikt-Konstellation (Abschnitt 2).
5. **Gewichts-Schwellen als Satz patchen** (Penalties konsistent unters neue Maximum), plus Refresh-Hinweis (Hercules/Artefakt-Trick).
6. **Save-Persistenz dokumentieren/abfangen:** MovementParams landen im Savegame; ohne Reset bleiben Werte nach Mod-Entfernung bestehen. Option "Reset-Pak mit Vanilla-Werten generieren" anbieten (Vorbild: Uninstall-File von Mod 2375).
7. **Companion-Link:** Mod 2414 (No HeadBob While Sprinting / CS Movement) als optionalen Workaround erwähnen — mit Hinweis auf Grenzen und Konfliktpotenzial (patcht dieselben ObjPrototypes/WeaponGeneralSetupPrototypes wie S2Tweaker; nicht kombinieren mit eigenen Speed-Tweaks).
8. **README-Hinweis:** Nach jedem Spiel-Update .pak neu generieren (bpatch gegen aktuelle cfg-Strukturen — die Lehre aus Long Days 3.0→3.1).

**Nicht tun:**
- Keinen `WalkTransitionCoef`-Slider anbieten; falls doch, nur ≤1.3 zulassen.
- Keine eigenen Animations-Asset-Edits versuchen (Zone-Kit-Territorium, BP-Mods in-game nicht unterstützt).
- Keine UE4SS-Abhängigkeit einführen (fragil pro Patch, Hooks deaktiviert, Ansatz unbewiesen).
- Nicht behaupten, ein Fix-Mod existiere — es gibt keinen; nur den State-Swap-Workaround 2414.
- Kein Time-Dilation-Trick (uetools_slomo o. Ä.) — bleibt zwar synchron, skaliert aber alles uniform und UETools ist auf 2.0.x tot (Nexus 64, unmaintained).

**Offen halten / beobachten:** SCAM-Posts (672) auf v3fish-Fix; ob 2.0.x-Micropatches die MovementParams-Semantik geändert haben (mehrere Berichte 27.–29.08.: Werte skalieren nur noch Animation, nicht Velocity) **[unsicher — vor v1.2-Release am lokalen Spiel gegenprüfen]**.

Quellen: https://www.nexusmods.com/stalker2heartofchornobyl/mods/2414 · https://www.nexusmods.com/stalker2heartofchornobyl/mods/672?tab=posts · https://www.nexusmods.com/stalker2heartofchornobyl/mods/410 · https://www.nexusmods.com/stalker2heartofchornobyl/mods/2409 · https://www.nexusmods.com/stalker2heartofchornobyl/mods/2375 · https://www.nexusmods.com/stalker2heartofchornobyl/mods/2341 · https://www.nexusmods.com/stalker2heartofchornobyl/mods/2485 · https://zonekit-support.stalker2.com/hc/en-us/articles/38198531582481 · https://zonekit-support.stalker2.com/hc/en-us/articles/39349140740369
