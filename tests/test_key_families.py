"""Waechter gegen halbe Schluesselgruppen (07.09.2026).

An einem einzigen Tag sind beim Gegenlesen fremder Mods VIER Faelle
derselben Sorte aufgefallen:

  1. `WeaponJamParams.[i]` haelt zwei Schluessel - wir schrieben seit
     1.26.0 nur `FullJamTime` hinein (gefunden in Maklane's Better Zone).
  2. `NPCToNPCDamageScaler` hat zwei Geschwister, `NPCToPlayerDamageScaler`
     und `NPCToFriendlyDamageScaler` - 1.31.0 nahm nur den ersten
     (gefunden in Better Ballistics Core).
  3. `PenetrationSpawnChance` hat `PenetrationTraceLenght` daneben
     (dieselbe Mod).
  4. Die Huepf-Familie der Artefakte: wir fassen `JumpSeriesDelay` an,
     nicht `JumpAmount`, `JumpDelay`, `JumpForce`, `JumpDistance`,
     `JumpHeight` (gefunden in ScrN Artifact Overhaul).

Viermal derselbe Fehler ist ein Muster, kein Zufall - dieser Test sucht
danach systematisch, statt auf die naechste fremde Mod zu warten.

METHODE: Aus unserem Code werden alle Schluesselnamen gesammelt, die wir
kennen. Dann wird jede Struktur der Dateien durchgegangen, die das
Werkzeug einliest: steht neben einem Schluessel, den wir anfassen, ein
NACHBAR mit verwandtem Namen (gemeinsame Wortbestandteile), den unser
Code nirgends erwaehnt? Genau das ist eine halbe Gruppe.

Der Bestand unten ist eingefroren. Taucht ein NEUER Nachbar auf - etwa
nach einem Spiel-Update -, wird der Test rot und jemand muss ihn
einsortieren: bauen, oder mit Begruendung in IGNORED aufnehmen.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker import cfgparse
from s2tweaker import gamedata as gd_mod

# --- 1) Was kennt unser Code? -------------------------------------------
SOURCE = "\n".join((ROOT / "s2tweaker" / f).read_text(encoding="utf-8")
                   for f in ("tweaks.py", "gamedata.py"))
KNOWN_KEYS = (set(re.findall(r'"(b?[A-Z][A-Za-z0-9_]{3,})"', SOURCE))
              | set(re.findall(r"'(b?[A-Z][A-Za-z0-9_]{3,})'", SOURCE)))

# Nicht-numerische Nachbarn interessieren nicht: Pfade, Meshes, Sounds,
# Icons, Namen. Die kann ein Regler ohnehin nicht sinnvoll skalieren.
COSMETIC = re.compile(r"(SID|Path|Mesh|Sound|Icon|Particle|VFX|PFX|Blueprint|"
                      r"Texture|Localization|Text|Hint|Image|Socket|Anim|Curve|"
                      r"Name|Prototype|Class|Type|Tag|Guid|Description)", re.I)

# Wortbestandteile; Min/Max/Base/Default sind zu allgemein, um eine
# Verwandtschaft zu begruenden (sonst waere jedes Min* mit jedem Max*
# verwandt) - sie fliegen darum aus dem Vergleich.
GENERIC = {"min", "max", "base", "default", "b"}


def tokens(key: str) -> set[str]:
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", key)
    return {p for p in parts if p.lower() not in GENERIC}


def walk(node, path=""):
    yield path, node
    for name, child in node.children.items():
        yield from walk(child, f"{path}/{name}" if path else name)


def suspicious() -> dict[str, dict]:
    """{Nachbar-Schluessel: {structs, known, example}}"""
    # NEEDED_FILES traegt teils Pfade ("WeaponData/..."), verglichen wird
    # aber der reine Dateiname - sonst faellt die halbe Waffendatei raus.
    wanted = {Path(gd_mod._cfg_name(n)).name.lower() for n in gd_mod.NEEDED_FILES}
    # 1.36.0: DialogPrototypes (31,6 MB) wird nur fuer EINEN If-Knoten je
    # Job-Dialogkette gelesen. Seine Schluessel sind Gespraechs-STRUKTUR
    # (NextDialogSID, Terminate, AnswerTo, MainReply ...), keine
    # Stellschrauben - als Nachbarn waeren sie nur Rauschen, und die Datei
    # wuerde den Lauf um ein Drittel verlaengern.
    wanted -= {"dialogprototypes.cfg"}
    found: dict[str, dict] = defaultdict(
        lambda: {"structs": 0, "known": set(), "example": None})
    for path in sorted(VANILLA.rglob("*.cfg")):
        if path.name.lower() not in wanted:
            continue
        try:
            root = cfgparse.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for top, node in root.children.items():
            for sub, inner in walk(node):
                # In RelationPrototypes sind die Eintraege unter "Relations"
                # bzw. unter "Factions" die Fraktions-NAMEN (WildBandits,
                # AzimutVarta ...) - keine
                # Schluesselfamilie - der Rest der Datei zaehlt aber.
                if (path.name.startswith("RelationPrototypes")
                        and sub.split("/")[0] in ("Relations", "Factions")):
                    continue
                keys = list(inner.values)
                for key in (k for k in keys if k in KNOWN_KEYS):
                    ours = tokens(key)
                    if not ours:
                        continue
                    for other in keys:
                        if (other in KNOWN_KEYS or "#" in other
                                or COSMETIC.search(other)):
                            continue
                        theirs = tokens(other)
                        shared = ours & theirs
                        if len(shared) >= 2 or (shared and len(ours) == 1
                                                and len(theirs) <= 2):
                            entry = found[other]
                            entry["structs"] += 1
                            entry["known"].add(key)
                            if entry["example"] is None:
                                entry["example"] = f"{path.name}:{top}" + (f"/{sub}" if sub else "")
    return found


# --- 2) Eingefrorener Bestand -------------------------------------------
# Echte halbe Gruppen: gemessen, in docs/ROADMAP.md als Kandidat notiert,
# aber (noch) nicht gebaut. Wer einen davon baut, nimmt ihn hier raus.
CANDIDATES = {
    "OffsetAimDispersionMod", "SpawnChanceBonus",
    "ThreatLevelValueMax", "MaxDistanceToAlly",
    "TwinAuxReloadTimeMultiplier", "TwinTacticalAuxReloadTimeMultiplier",
    "AmmoMinCount", "AmmoMaxCount",
    "FireDistanceRecoilMin", "FireDistanceRecoilMax", "FireDistanceDispersion",
    "PerBulletReloadingAmmoCount", "LastClipBulletsCount", "LastTotalBulletsCount",
    "DamageAccumulationMinValue", "DamageAccumulationMaxValue",
    "MinDeadThreatForgetTime", "MaxDeadThreatForgetTime",
    "HoldBreathCooldown", "HoldBreathMaxStamina", "HoldBreathStaminaThreshold",
    "ClimbFastAscendingSpeedScale", "ClimbMediumAscendingSpeedScale",
    "MutantLootInteractHeightMin", "VoidRadiusMin", "VoidRadiusMax",
    "EMIRadius", "EMIDuration", "DamageRadius", "EpicenterRadius",
    "DefaultALifeLairExpansionToPlayerTimeMax", "ALifeLairExpansionRadius",
    "ALifeStartSimulation", "CorpseRadius", "FactionPriority",
    "HitDetectionAngle", "HitDetectionRadius", "DamageDelay", "DamageDistance",
    "bAddIntensity", "PsyNPCDurabilityDamageMultiplier", "bPsyNPCApplyBleeding",
    "VitalEnergeticOveruseDegen", "VitalEnergeticToleranceDegen",
    "VitalEnergeticToleranceDegenDelay", "SleepHoursMultiplier",
    "HPThresholdToKill", "MinHP", "NPC_Armor_Strike_Add", "Effect_Degen_Bleeding",
    "ExplosionArmorDifferenceCoef", "PlayerMeleeArmorDifferenceCoef",
    "LastBulletStartScalingPlayerHPPercent", "DefaultArtifactRadius",
    "ArtifactSpawnDistanceDelta", "DefaultAnomalyRadius", "MinAngle",
    "ViewPitchUpLimit", "IdleSwayTimeModifier", "SnappingAimAlphaThreshold",
    "SuppressionMinSpeed", "MaxThreatLevelValueBeforeIndentification",
    "TooCloseVisionDistance", "TooCloseVisionDistanceMultiplier",
    "LoseVisionDistanceExtensionMultiplier", "FrontSensingAngle",
    "FlashlightVisionConeLength", "FlashlightVisionConeHalfAngle",
    "UnkillableNPCWoundedStateResurrectionTime", "WoundedHealHoldInteractTime",
    "AccumulateNPCToPlayerDamageSeconds", "PlayerSelectedAsTargetByOtherCoeff",
    "ReputationRollbackRadius", "HubReputationRollbackCooldownModifier",
    "LairReputationRollbackCooldownModifier", "NightStartTime", "StartDay",
    "AutoSaveOnFailRetryIntervalTime", "PutDeadBodyDistance",
    "DeadBodyStaminaJumpMultiplier", "DeadBodyInvalidationTime",
    "PsyNPCCorpseTimeout", "FaustCloneCorpseTimeout", "MinWeight", "MaxWeight",
    "RequireWeight", "ChargeThreshold", "bUseCharge", "TargetValue",
    "MinDistanceToFloorOnSpawn",
    "BleedingChanceStackMaxSize", "MPC_FOV", "AimFOVRestoreTime",
    "NarrowTraceInteractionRadius", "WideTraceInteractionRadius",
    "AccumulatedDamageReductionIncludesHealedHealth", "ApplyImpulseToHitLocationFromPlayer",
    # 07.09. abends dazugekommen, als der Test auch ObjPrototypes mitnahm:
    "MaxHungerPoints", "MaxSleepinessPoints", "MaxDrunknessPoints",
    "MaxOverDrunknessPoints", "RegenPoppyFieldSleepiness",
    "NoiseJumpCoef", "NoiseObstacleCoef",          # Stealth: wir nehmen nur Ducken/Gehen
    "VisibilityJumpCoef", "VisibilityObstacleBodyCoef", "VisibilityObstacleHeadCoef",
    "VaultOverCrouchingHeight", "VaultOverStandingHeight",
    "CriticalDamageCoefThreshold", "CriticalDamageCooldownMin",
    "CriticalDamageCooldownMax", "CriticalDamageAccumulationPeriod",
    "DegenSuppressionPoints", "DegenSuppressionDelayTimeSeconds",
    "HealthPercentToRetreat", "MinRetreatActivationRadius",
    "SafeDistanceToEnemy", "SafeDistanceToExplosives", "EffectiveDistanceToEnemy",
    "AimSpeedCoef", "WalkTransitionCoef", "EnteringDuration",
    "DialogInteractDistance",
}

# Bewusst nicht angefasst - mit Grund. Die Kategorien:
#   (a) in der Doku als tabu vermerkt,
#   (b) Zaehler/Schalter ohne sinnvolle Skala,
#   (c) Zeiten und Radien reiner Technik (Traces, Decals, Ticks, Audio),
#   (d) Enum/Struktur statt Zahl.
IGNORED = {
    # 08.09.2026 gemessen: Durst ist ein toter Zaehler. RegenThirstPoints
    # steht bei Spieler UND Basis auf 0.0, und das Wort "Thirst" kommt im
    # ganzen Spiel NUR in ObjPrototypes vor - kein Effekt, kein Getraenk,
    # kein Schwierigkeitsgrad-Schluessel fuettert ihn. Nichts zu skalieren.
    "RegenThirstPoints",
    # 09.09.2026 IM SPIEL WIDERLEGT (craigduk76, GitHub #10/#11, 1.35.0):
    # die zwei Leiter-Schluessel und der Dialog-Zoom standen bis 1.35.0 im
    # Werkzeug. Sein Debug-Export beweist, dass der Patch ankam
    # (ViewPitchDownLimit aus demselben Struct wirkte) - diese drei tun
    # nichts. Zurueckgezogen; nie wieder bauen, es sei denn jemand findet,
    # was sie ueberhaupt liest.
    "ClimbViewYawLimit", "ClimbViewPitchLimit", "DialogFOVDefault",
    # 08.09.2026, aufgetaucht als 1.35.0 das Blicktempo baute:
    # AimLookUpCoef/AimTurnCoef (0.8) sitzen an 47 MUTANTEN-Prototypen,
    # der Player ist NICHT dabei - das ist KI-Drehtempo beim Anvisieren,
    # nicht die Blickempfindlichkeit des Spielers.
    "AimLookUpCoef",
    # dito MinJumpDistance (300-800) unter JumpActionData/
    # JumpToEnemyActionData: Sprung-Geometrie von Mutanten-Angriffen,
    # nicht die Huepf-Familie der Artefakte.
    "MinJumpDistance",
    "RadiusExtensionBulletCount",      # (a) docs/ROADMAP.md: ausdruecklich tabu
    "DamageIgnoranceThreshold",        # (a) HANDOVER P6: Phasen-Unterarray bewusst nicht
    "CorpseRagdollQuestProtectionCheckTime",   # (a) Quest-Schutz, P5 tabu
    "CorpseRagdollQuestProtectionEnableTime",  # (a) dito
    "ALifeGridUpdateDelay", "bALifeTick", "NumTracePointsPerVisionUpdate",
    "CoefTimeForInterp", "WaitingTimeToRotationCamera",          # (c) Leistung/Technik
    "ProjectileDecalMaxSaveCountOnCorpse", "ProjectileDecalLifeSpanOnCorpse",
    "ProjectileDecalFadeOutTime", "FootstepsDecalFadeOutTime",   # (c) Decals
    "ProjectileAdditionalTraceDistance", "IKTraceDistance",
    "UnfocusableWeaponTraceDistance", "UnfocusableKnifeTraceDistance",
    "InteractionDotsTraceRadius",                                # (c) Traces
    "DetectorWorkSFX", "FireIntervalRTPCParameter",
    "PlayerAudioLogVolumeDecreaseTime", "EnergeticOveruseParameter",  # (c) Audio/Parameter
    "DefaultTeleportScreenHideDelay", "DefaultTeleportScreenShowDelay",
    "FlashlightDialogIntensityLerpTime",                         # (c) Blenden
    "LadderEnterUpZOffset", "LadderEnterUpXOffset",              # (c) Geometrie
    "DamageSource", "CombatStateAction", "CombatStateActionEnd",
    "StaticItemContainer", "SkeletalItemContainer",
    "bIdentifyEnemyByThreatLevel", "NPCWeaponAttributes",        # (d) Enum/Referenz
    "DamagePlayer",                    # (d) heisst in ExplosionPrototypes anders als gemeint
    "ManualHub",              # (d) Fraktions-/Hub-Namen
    # 07.09. abends geprueft und mit Grund ausgelassen:
    "InGameMinutes",       # (b) GEMESSEN: kein einziger SetTimer benutzt Minuten
                           #     (alle 0) - der Cooldown-Regler ist vollstaendig
    "MovementSpeedCoef",   # (a) NPC-Tempo, seit der Anim-Recherche bewusst tabu
    "LowCrouch",           # (b) StaminaPerAction: vanilla 0, ein Faktor bleibt 0
    "CanDailyScheduleBeOverride",  # (d) Schalter fuer Tagesablaeufe, Fehltreffer
    "ChangeValue",         # (d) Quest-Knoten-Feld, gehoert zur Struktur
    "WindowBackTraceHeightModifier", "WindowBackTraceRadiusModifier",
                           # (a) Vault-Trace-Interna: laut ROADMAP bewusst nur im Preset
}

BASELINE = CANDIDATES | IGNORED

# --- 3) Pruefung ---------------------------------------------------------
found = suspicious()
names = set(found)

print(f"Bekannte Schluesselnamen aus unserem Code: {len(KNOWN_KEYS)}")
print(f"Verdaechtige Nachbarn in den gelesenen Dateien: {len(names)}\n")

new = sorted(names - BASELINE)
gone = sorted(BASELINE - names)

if new:
    print("NEUE halbe Gruppen - bitte einsortieren:")
    for key in new:
        e = found[key]
        print(f"  {key:<42} {e['structs']:>5}x neben {', '.join(sorted(e['known'])[:2])}")
        print(f"      {e['example']}")
assert not new, (f"{len(new)} unbekannte Nachbar-Schluessel: {new[:8]} - entweder "
                 f"bauen oder mit Begruendung in IGNORED aufnehmen")

# Verschwundene sind KEIN Fehler (Spiel-Update, oder wir haben sie gebaut),
# aber sie sollen auffallen, damit der Bestand nicht verrottet.
if gone:
    print("Nicht mehr gefunden (gebaut oder aus dem Spiel verschwunden):")
    for key in gone:
        print(f"  {key}")

# --- 4) Der Detektor selbst muss die vier Faelle von 07.09. finden -------
# Sonst koennte er stillschweigend kaputtgehen und immer gruen melden.
# (Die urspruenglichen Referenzen NPCToPlayerDamageScaler und JumpDelay sind
#  seit 1.35.0 gebaut und tauchen darum nicht mehr als Nachbarn auf. Neue
#  Anker: zwei halbe Gruppen, die bewusst offen bleiben.)
for key, why in (("DegenSuppressionPoints", "Unterdrueckungsfeuer"),
                 ("NoiseJumpCoef", "halbe Stealth-Familie")):
    assert key in names, f"Detektor findet {why} nicht mehr - Regel kaputt?"
print(f"\nDer Detektor findet die Referenzfaelle weiterhin.")

built = {"FullJamTime", "PenetrationSpawnChance", "MaxStackCount"}
assert built <= KNOWN_KEYS, "erwartete gebaute Schluessel fehlen im Code"

print(f"\n=== {len(names)} Nachbarn geprueft, {len(CANDIDATES)} als Kandidat "
      f"notiert, {len(IGNORED)} bewusst ausgelassen ===")
