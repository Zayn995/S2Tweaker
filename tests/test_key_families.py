"""Detect unreviewed neighboring numeric fields in supported game-data structs.

Compare related name components against keys known to the implementation.
Maintain reviewed exclusions with reasons; newly discovered neighbors fail
for investigation after code or game-data changes."""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker import cfgparse
from s2tweaker import gamedata as gd_mod

# --- 1) Keys referenced by the implementation ---
SOURCE = "\n".join((ROOT / "s2tweaker" / f).read_text(encoding="utf-8")
                   for f in ("tweaks.py", "gamedata.py", "loot_extensions.py",
                             "repair_extensions.py", "world_extensions.py"))
KNOWN_KEYS = (set(re.findall(r'"(b?[A-Z][A-Za-z0-9_]{3,})"', SOURCE))
              | set(re.findall(r"'(b?[A-Z][A-Za-z0-9_]{3,})'", SOURCE)))

# Ignore nonnumeric neighbors such as paths, assets and identifiers.
COSMETIC = re.compile(r"(SID|Path|Mesh|Sound|Icon|Particle|VFX|PFX|Blueprint|"
                      r"Texture|Localization|Text|Hint|Image|Socket|Anim|Curve|"
                      r"Name|Prototype|Class|Type|Tag|Guid|Description)", re.I)

# Ignore generic name components such as Min/Max/Base/Default when finding families.
GENERIC = {"min", "max", "base", "default", "b"}


def tokens(key: str) -> set[str]:
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", key)
    return {p for p in parts if p.lower() not in GENERIC}


def walk(node, path=""):
    yield path, node
    for name, child in node.children.items():
        yield from walk(child, f"{path}/{name}" if path else name)


def suspicious() -> dict[str, dict]:
    """Return {adjacent key: {structs, known, example}}."""
    # Compare filenames rather than NEEDED_FILES path prefixes.
    wanted = {Path(gd_mod._cfg_name(n)).name.lower() for n in gd_mod.NEEDED_FILES}
    # Exclude structural dialogue fields and streamed spawn helpers from numeric
    # control-family discovery.
    wanted -= {"dialogprototypes.cfg", "spawnactorprototypes.cfg"}
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
                # Faction names beneath Relations/Factions are data keys, not numeric field families.
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


# Known unimplemented neighbors; remove entries when coverage is added.
CANDIDATES = {
    "OffsetAimDispersionMod", "SpawnChanceBonus",
    "ThreatLevelValueMax", "MaxDistanceToAlly",
    "TwinAuxReloadTimeMultiplier", "TwinTacticalAuxReloadTimeMultiplier",
    "FireDistanceRecoilMin", "FireDistanceRecoilMax",
    "PerBulletReloadingAmmoCount", "LastClipBulletsCount", "LastTotalBulletsCount",
    "DamageAccumulationMinValue", "DamageAccumulationMaxValue",
    "MinDeadThreatForgetTime", "MaxDeadThreatForgetTime",
    "HoldBreathCooldown", "HoldBreathMaxStamina", "HoldBreathStaminaThreshold",
    "ClimbFastAscendingSpeedScale", "ClimbMediumAscendingSpeedScale",
    "VoidRadiusMin", "VoidRadiusMax",
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
    # Additional reviewed object-prototype neighbors.
    "MaxHungerPoints", "MaxSleepinessPoints", "MaxDrunknessPoints",
    "MaxOverDrunknessPoints", "RegenPoppyFieldSleepiness",
    "NoiseJumpCoef", "NoiseObstacleCoef",          # Stealth coverage currently targets crouching/walking.
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

# Reviewed exclusions: unsupported behavior, unsuitable counters/toggles,
# engine timing/geometry internals, and enum/struct fields.
IGNORED = {
    "Delay",  # post-process startup timing, not repair strength
    "DropOnPickup",  # item interaction behavior, not loot availability
    "FootStepsDecalsPoolSize",  # footstep tracks are separate from projectile/blood marks
    # Thirst is inert in the checked data: zero regeneration and no referenced
    # consumable/effect/difficulty mechanism.
    "RegenThirstPoints",
    # Retired ladder-view and dialogue-FOV keys failed community game tests.
    # Do not treat them as supported without evidence of an active consumer.
    "ClimbViewYawLimit", "ClimbViewPitchLimit", "DialogFOVDefault",
    # These aim-turn coefficients belong to mutant AI, not player sensitivity.
    "AimLookUpCoef",
    # These distances describe mutant attack geometry, not artifact jumps.
    "MinJumpDistance",
    "RadiusExtensionBulletCount",      # Intentionally excluded: unverified animation behavior.
    "DamageIgnoranceThreshold",        # Excluded nested destructible phase arrays.
    "CorpseRagdollQuestProtectionCheckTime",   # (a) Quest protection, excluded from this control
    "CorpseRagdollQuestProtectionEnableTime",  # (a) Likewise
    "ALifeGridUpdateDelay", "bALifeTick", "NumTracePointsPerVisionUpdate",
    "CoefTimeForInterp", "WaitingTimeToRotationCamera",          # Performance/technical behavior.
    "ProjectileDecalMaxSaveCountOnCorpse", "ProjectileDecalLifeSpanOnCorpse",
    "ProjectileDecalFadeOutTime", "FootstepsDecalFadeOutTime",   # (c) Decals
    "ProjectileAdditionalTraceDistance", "IKTraceDistance",
    "UnfocusableWeaponTraceDistance", "UnfocusableKnifeTraceDistance",
    "InteractionDotsTraceRadius",                                # (c) Traces
    "DetectorWorkSFX", "FireIntervalRTPCParameter",
    "PlayerAudioLogVolumeDecreaseTime", "EnergeticOveruseParameter",  # (c) Audio/Parameter
    "DefaultTeleportScreenHideDelay", "DefaultTeleportScreenShowDelay",
    "FlashlightDialogIntensityLerpTime",                         # Fades.
    "LadderEnterUpZOffset", "LadderEnterUpXOffset",              # Geometry.
    "DamageSource", "CombatStateAction", "CombatStateActionEnd",
    "StaticItemContainer", "SkeletalItemContainer",
    "bIdentifyEnemyByThreatLevel", "NPCWeaponAttributes",        # Enum/reference.
    "DamagePlayer",                    # Has a different meaning in ExplosionPrototypes.
    "ManualHub",              # Faction/hub names.
    # Additional reviewed exclusions.
    "InGameMinutes",       # All checked quest SetTimer minute values are zero.
                           # The existing cooldown control covers the used time unit.
    "MovementSpeedCoef",   # NPC movement timing remains outside the supported animation scope.
    "LowCrouch",           # StaminaPerAction: vanilla zero stays zero under multiplication.
    "CanDailyScheduleBeOverride",  # Schedule toggle, not a numeric control-family match.
    "ChangeValue",         # Structural quest-node field.
    "WindowBackTraceHeightModifier", "WindowBackTraceRadiusModifier",
                           # Vault trace internals belong only to the coordinated preset.
}

BASELINE = CANDIDATES | IGNORED

# --- 3) Verification ---
found = suspicious()
names = set(found)

print(f"Known key names in the code: {len(KNOWN_KEYS)}")
print(f"Suspicious adjacent keys in loaded files: {len(names)}\n")

new = sorted(names - BASELINE)
gone = sorted(BASELINE - names)

if new:
    print("NEW partially covered groups - classify these entries:")
    for key in new:
        e = found[key]
        print(f"  {key:<42} {e['structs']:>5}x neben {', '.join(sorted(e['known'])[:2])}")
        print(f"      {e['example']}")
assert not new, (f"{len(new)} unknown adjacent keys: {new[:8]} - entweder "
                 f"implement or add to IGNORED with a reason")

# Report disappeared neighbors without failing; they may be implemented or removed upstream.
if gone:
    print("No longer found (implemented or removed from the game):")
    for key in gone:
        print(f"  {key}")

# Verify the detector itself using known remaining family gaps,
# so a broken detector cannot silently pass everything.
for key, why in (("DegenSuppressionPoints", "Unterdrueckungsfeuer"),
                 ("NoiseJumpCoef", "halbe Stealth-Familie")):
    assert key in names, f"Detector no longer finds {why} - broken rule?"
print(f"\nThe detector still finds the reference cases.")

built = {"FullJamTime", "PenetrationSpawnChance", "MaxStackCount"}
assert built <= KNOWN_KEYS, "Expected implemented keys missing from code"

print(f"\n=== {len(names)} adjacent keys checked, {len(CANDIDATES)} candidate entries "
      f"notiert, {len(IGNORED)} intentionally excluded ===")
