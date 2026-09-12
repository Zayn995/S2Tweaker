"""Extract, cache and resolve vanilla GameData from the installed game.

Read the selected Pak entries, decode cfg.bin with vendor_bin2cfg, then
parse cfg text and resolve refkey inheritance. Tweaks use these live
baselines so multipliers track the installed game version."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import threading
from functools import cached_property
from pathlib import Path

from . import cfgparse, pakio, vendor_bin2cfg
from .cfgparse import CfgStruct, parse_number

# Extract only required files to limit decoding time and cache size.
NEEDED_FILES = [
    "ObjPrototypes.cfg.bin",
    "ItemPrototypes.cfg.bin",
    "TradePrototypes.cfg.bin",
    "DifficultyPrototypes.cfg.bin",
    "EffectPrototypes.cfg.bin",
    "FloatProviderPrototypes.cfg.bin",
    "ObjWeightParamsPrototypes.cfg.bin",
    "ObjEffectMaxParamsPrototypes.cfg.bin",
    "ObjHoldBreathParamsPrototypes.cfg.bin",
    "WeaponData/CharacterWeaponSettingsPrototypes.cfg.bin",
    "WeaponData/WeaponGeneralSetupPrototypes.cfg.bin",
    "WeaponData/WeaponAttributesPrototypes.cfg.bin",
    "CoreVariables.cfg",
    "AIGlobals.cfg",
    "AIPrototypes/HearingSensorPrototypes.cfg.bin",
    "AIPrototypes/VisionScannerPrototypes.cfg.bin",
    "CameraShakePrototypes.cfg.bin",
    "ArtifactSpawnerPrototypes.cfg.bin",
    "PassiveDetectorPrototypes.cfg.bin",
    "FastTravelPrototypes.cfg.bin",
    "BoolProviderPrototypes.cfg.bin",
    "AbilityPrototypes.cfg.bin",
    "MeleeWeaponPrototypes.cfg.bin",
    "WeatherSelectionPrototypes.cfg.bin",
    "StashPrototypes.cfg.bin",
    "ItemGeneratorPrototypes.cfg.bin",
    "RelationPrototypes.cfg.bin",
    "QuestNodePrototypes.cfg.bin",
    "EmissionPrototypes.cfg.bin",
    "UpgradePrototypes.cfg.bin",
    "LairPrototypes.cfg.bin",
    "ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg.bin",
    "AIPrototypes/ThreatPrototypes.cfg.bin",
    "FlashlightPrototypes.cfg.bin",          # NPC flashlights.
    "SaveLoadVariables.cfg",                 # Save-count limit (unbinarized).
    "AutoSaveVariables.cfg",                 # Autosave interval (unbinarized).
    "AimAssistPresetPrototypes.cfg.bin",     # Mouse/gamepad aim assist.
    "ProjectilePrototypes.cfg.bin",          # Projectile speed.
    "ObjSleepParamsPrototypes.cfg.bin",      # Sleep (06.09.2026)
    "PostEffectProcessorPrototypes.cfg.bin", # Crouch vignette.
    "ExplosionPrototypes.cfg.bin",           # Grenade radius.
    "CorpseClueStashPrototypes.cfg.bin",     # Stash clues.
    "MarkerPrototypes.cfg.bin",              # PDA map.
    "AnomalyPrototypes.cfg.bin",             # Clicker anomaly.
    "CombatSynchronizationPrototypes.cfg.bin",  # Concurrent attackers.
    "ItemContainerPrototypes.cfg.bin",       # Containers-Respawn (1.27.0)
    "QuickSaveVariables.cfg",                # Quicksave window (unbinarized).
    "CoreVariablesCustom.cfg",               # CustomConfigOverride confirmation (unbinarized).
    "EnemyEvaluatorPrototypes.cfg.bin",      # NPC target selection.
    "CoverEvaluatorPrototypes.cfg.bin",      # NPC cover profiles.
    "AIPrototypes/FlairSensorPrototypes.cfg.bin",   # Mutant scent detection.
    "NPCNeedsPresetPrototypes.cfg.bin",      # A-Life squad expansion.
    "ALifePrototypes/ALifePolicyPrototypes.cfg.bin",   # A-Life refill.
    "ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg.bin",   # Faction expansion.
    "BarbedWirePrototypes.cfg.bin",          # Barbed wire.
    "DestructibleObjectPrototypes.cfg.bin",  # explodierende Containers (1.28.0 P6, 536 KB - lazy geparst)
    "PhysicsInteractionPrototypes.cfg.bin",  # Push impulse.
    "WeatherChainPrototypes.cfg.bin",        # Weather transitions.
    "SingletonConstants.cfg",                # Night/sky settings (unbinarized).
    "PackOfItemsGroupPrototypes.cfg.bin",    # World loot piles.
    "NPCPrototypes.cfg.bin",                 # NPC-level traders; parsed lazily.
    "DialogPrototypes.cfg.bin",              # Job-giver dialogue chains; parsed lazily for simultaneous jobs.
    "JournalQuestPrototypes.cfg.bin",        # separate journal entries for simultaneous jobs
]

# Increment when NEEDED_FILES changes to invalidate incomplete old caches.
CACHE_SCHEMA = 27   # rebuild caches decoded without binary cfg version 2 support
OPTIONAL_SPAWN = "SpawnActorPrototypes.cfg.bin"

# Mutant factions mapped to attack-struct prefixes in AbilityPrototypes.cfg.
# See docs/V15_DATA_RESEARCH.md. Rat, Poltergeist and Mutant have no damage attacks.
SPECIES_ABILITY_PREFIXES = {
    "Bloodsucker": ["Bloodsucker_", "AshyBloodsucker_", "MistBloodsucker_",
                    "PrologueBloodsucker_"],
    "Boar": ["Boar_", "HelmedBoar_", "PorcupineBoar_", "ChargeAbility_Boar",
             "ChargeAbility_HelmedBoar", "ChargeAbility_PorcupineBoar"],
    "Flesh": ["Flesh_", "BoggyFlesh_"],
    "Pseudodog": ["PseudoDog_", "PseudoDogSummon_"],
    "Blinddog": ["BlindDog_"],
    "MoldyBlinddog": ["MoldyBlindDog_"],
    "Snork": ["Snork_"],
    "Controller": ["Controller_"],
    "Burer": ["Burer_"],
    "Pseudogiant": ["Pseudogiant_", "ChargeAbility_Pseudogiant"],
    "Chimera": ["Chimera_"],
    "Deer": ["Deer_", "ChargeAbility_Deer"],
    "Tushkan": ["Tushkan_"],
    "Bayun": ["Cat_"],
}

GAMEDATA_REL = "Stalker2/Content/GameLite/GameData"

# Edition weapons use separate Paks and a DLCGameData branch.
# Missing optional Paks simply omit those weapons.
DLCGAMEDATA_REL = "Stalker2/Content/GameLite/DLCGameData"
DLC_SOURCES = {
    "PreOrder": "pakchunk101-Windows.pak",
    "Deluxe": "pakchunk102-Windows.pak",
    "Ultimate": "pakchunk104-Windows.pak",
}
DLC_FILES = ("ItemPrototypes.cfg.bin",
             "WeaponData/WeaponGeneralSetupPrototypes.cfg.bin")


def _cfg_name(needed: str) -> str:
    """Map a NEEDED_FILES entry to its decoded cfg filename."""
    return needed[: -len(".bin")] if needed.endswith(".cfg.bin") else needed

# Creature factions identify mutants; zombie stalkers count as humans.
MUTANT_FACTIONS = {
    "Bayun", "Blinddog", "Bloodsucker", "Boar", "Burer", "Chimera",
    "Controller", "Deer", "Flesh", "MoldyBlinddog", "Mutant", "Poltergeist",
    "Pseudodog", "Pseudogiant", "Rat", "Snork", "Tushkan",
}

WEAPON_TEMPLATES = {"TemplateWeapon"}
ARMOR_TEMPLATES = {"TemplateArmor"}

# Category templates in WeaponGeneralSetupPrototypes.cfg: every weapon inherits
# Through refkey, potentially via intermediate unique-item prototypes.
WEAPON_CATEGORY_TEMPLATES = {
    "TemplatePistol": "pistol",
    "TemplateMAC": "smg",           # Machine pistols belong to the SMG category.
    "TemplateSMG": "smg",
    "TemplateRifle": "rifle",
    "TemplateRifleSingleFire": "rifle",
    "TemplateShotgun": "shotgun",
    "TemplateDMR": "dmr",
    "TemplateSniper": "sniper",
    "TemplateMG": "mg",
    "TemplateGLaunch": "launcher",
}

# RPG-7 inherits TemplateSniper in game data but belongs to grenade launchers.
WEAPON_CATEGORY_OVERRIDES = {
    "GunRpg7_GL": "launcher",
}

CATEGORY_TEMPLATES = {
    "TemplateWeapon": "weapon",
    "TemplateArmor": "armor",
    "TemplateAmmo": "ammo",
    "TemplateArtifact": "artifact",
    "TemplateAttach": "attach",
    "TemplateConsumable": "consumable",
    "TemplateGrenade": "grenade",
    "TemplateDetector": "misc",
    "TemplateBinoculars": "misc",
    "TemplateNightVisionGoggles": "misc",
}


def default_cache_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "S2Tweaker"
    return base


# Group repeatable jobs by the leading RSQ<number> in QuestSID,
# e.g. RSQ01 or RSQ06_C00___SIDOROVICH.
_RSQ_GROUP_RE = re.compile(r"^(RSQ\d+)")


def _less_condition(node: CfgStruct,
                    variables: set[str]) -> tuple[tuple[str, str], float] | None:
    """Find a Less condition on a listed variable in an If node's Conditions.

    Return ((outer_key, inner_key), limit) so the builder can emit the complete
    array entry at that path."""
    conds = node.children.get("Conditions")
    if conds is None:
        return None
    for outer_key, outer in conds.children.items():
        for inner_key, inner in outer.children.items():
            values = inner.values
            comparance = (values.get("ConditionComparance") or "").strip()
            variable = (values.get("GlobalVariablePrototypeSID") or "").strip()
            if comparance == "EConditionComparance::Less" and variable in variables:
                return (outer_key, inner_key), parse_number(values.get("VariableValue"))
    return None


def _launcher_link(node: CfgStruct,
                   source_sid: str) -> tuple[tuple[str, str], str] | None:
    """Find the incoming launcher connection from source_sid.

    Return ((launcher_key, connection_key), pin_name). Name identifies the
    source node's output pin. Connection indices vary between job givers,
    so resolve the link from the graph instead of assuming an index."""
    launchers = node.children.get("Launchers")
    if launchers is None:
        return None
    for launcher_key, launcher in launchers.children.items():
        connections = launcher.children.get("Connections")
        if connections is None:
            continue
        for conn_key, conn in connections.children.items():
            if (conn.values.get("SID") or "").strip() == source_sid:
                return (launcher_key, conn_key), (conn.values.get("Name") or "").strip()
    return None


class GameData:
    def __init__(self, gamedata_dir: Path, *, source_pak=None, progress=None):
        """Initialize from decoded cfg text under Stalker2/Content/GameLite/GameData."""
        self.dir = Path(gamedata_dir)
        self._source_pak = Path(source_pak) if source_pak else None
        self._source_stamp = self._pak_stamp() if source_pak else None
        self._progress = progress
        self._optional_lock = threading.Lock()

    def _pak_stamp(self):
        stat = self._source_pak.stat()
        return stat.st_size, stat.st_mtime_ns

    def job_localization_files(self, aliases):
        """Optional native resources; no localization work during normal loading."""
        from .job_localization import resources
        return resources(self, aliases)

    def stash_spawn_source(self):
        """Load the large spawn file only for enabled extra stash finds.

        The optional index is deliberately separate from the full vanilla cfg:
        conflict scans must never mistake a selective index for complete data.
        Extraction and binary decoding happen in the existing export worker.
        """
        full = self.dir / "SpawnActorPrototypes.cfg"
        if full.is_file():
            return full  # existing developer data; never rewrite it
        with self._optional_lock:
            if self._source_pak is None:
                raise FileNotFoundError("Extra stash finds need the game installation. Reload game data before building.")
            if self._pak_stamp() != self._source_stamp:
                raise RuntimeError("Game files changed. Reload game data before building extra stash finds.")
            optional = self.dir / ".optional"
            size, modified = self._source_stamp
            target = optional / f"stash-spawns-{size}-{modified}.cfg"
            if target.is_file():
                return target
            if self._progress:
                self._progress("Preparing extra stash finds for the first time (large optional game file) ...")
            optional.mkdir(parents=True, exist_ok=True)
            # TemporaryDirectory also cleans up the 175 MB binary on failure.
            with tempfile.TemporaryDirectory(prefix="stash-", dir=optional) as temp:
                temp = Path(temp)
                pakio.unpack(self._source_pak, temp,
                             include=f"{GAMEDATA_REL}/{OPTIONAL_SPAWN}", progress=self._progress)
                binary = (temp / GAMEDATA_REL / OPTIONAL_SPAWN).read_bytes()
                compact = temp / "containers.cfg"
                seen = 0
                with compact.open("w", encoding="utf-8") as output:
                    for root in vendor_bin2cfg.iter_binary_cfg(binary):
                        seen += 1
                        if root.get("SpawnType") == "ESpawnType::ItemContainer":
                            output.write(root.to_string() + "\n")
                if not seen:
                    raise ValueError("The optional spawn file contains no readable game data.")
                if self._pak_stamp() != self._source_stamp:
                    raise RuntimeError("Game files changed during extraction. Reload game data and retry.")
                compact.replace(target)
            return target

    # ---------------------------------------------------------------- setup
    @classmethod
    def from_game(cls, game_dir: Path, cache_root: Path | None = None,
                  progress=None) -> "GameData":
        """Extract and cache vanilla data from the game installation."""
        pak = Path(game_dir) / "Stalker2/Content/Paks/pakchunk0-Windows.pak"
        cache_root = cache_root or default_cache_dir()

        if not pak.is_file():
            # If the game files are temporarily unavailable, reuse only a cache with
            # the current schema; older schemas may lack required files.
            fallback = sorted(
                (d for d in cache_root.glob(f"vanilla-*-s{CACHE_SCHEMA}")
                 if (d / ".complete").is_file()),
                key=lambda d: d.stat().st_mtime,
            )
            if fallback:
                if progress:
                    progress("Game files busy (Steam update?) - using cached data.")
                return cls(fallback[-1] / GAMEDATA_REL)
            raise FileNotFoundError(
                f"pakchunk0 not found: {pak}\n\n"
                "Is Steam currently updating or verifying the game? "
                "Wait for the update to finish, then restart this tool.")

        # Pak size provides an inexpensive version fingerprint.
        tag = f"vanilla-{pak.stat().st_size}-s{CACHE_SCHEMA}"
        cache = cache_root / tag
        gd = cache / GAMEDATA_REL
        marker = cache / ".complete"

        # Supplement complete caches missing newly required files;
        # rebuild incomplete caches.
        fresh = not marker.is_file()
        to_extract = (list(NEEDED_FILES) if fresh else
                      [name for name in NEEDED_FILES
                       if not (gd / _cfg_name(name)).is_file()])
        if to_extract:
            cache.mkdir(parents=True, exist_ok=True)
            if progress:
                progress("Extracting game data from pakchunk0 ...")
            for name in to_extract:
                pakio.unpack(pak, cache, include=f"{GAMEDATA_REL}/{name}",
                             progress=progress)
            # Optional edition Paks have their own cfg branch; extraction failure
            # must not prevent using the base game data.
            for edition, pakname in (DLC_SOURCES.items() if fresh else ()):
                dlc_pak = Path(game_dir) / "Stalker2/Content/Paks" / pakname
                if not dlc_pak.is_file():
                    continue
                for name in DLC_FILES:
                    try:
                        pakio.unpack(
                            dlc_pak, cache,
                            include=f"{DLCGAMEDATA_REL}/{edition}/{name}",
                            progress=progress)
                    except Exception:
                        break
            if progress:
                progress("Converting cfg.bin to readable cfg ...")
            for bin_path in sorted((cache / "Stalker2/Content/GameLite")
                                   .rglob("*.cfg.bin")):
                out = bin_path.with_name(bin_path.name[: -len(".bin")])
                if not out.exists():
                    try:
                        roots = vendor_bin2cfg.read_binary_cfg(bin_path.read_bytes())
                    except (ValueError, RecursionError) as exc:
                        raise ValueError(
                            f"Could not decode {bin_path.relative_to(cache)}: {exc}"
                        ) from exc
                    out.write_text(
                        "\n".join(r.to_string() for r in roots), encoding="utf-8"
                    )
            # Verify required files before marking the cache complete. An include
            # pattern may match nothing even when extraction reports success.
            missing = [name for name in NEEDED_FILES
                       if not (gd / _cfg_name(name)).is_file()]
            if missing:
                raise FileNotFoundError(
                    "These game files could not be extracted:\n  "
                    + "\n  ".join(missing)
                    + "\n\nYour game version may have moved or renamed them. "
                      "Please report this together with your game version.")
            marker.write_text("ok", encoding="utf-8")
            # Remove obsolete schema caches to avoid accumulating unused data.
            for old in cache_root.glob("vanilla-*"):
                if old.is_dir() and not old.name.endswith(f"-s{CACHE_SCHEMA}"):
                    shutil.rmtree(old, ignore_errors=True)
        return cls(gd, source_pak=pak, progress=progress)

    # ---------------------------------------------------------------- parsing
    def _parse(self, name: str) -> CfgStruct:
        return cfgparse.parse_file(self.dir / name)

    @cached_property
    def obj(self) -> CfgStruct:
        return self._parse("ObjPrototypes.cfg")

    @cached_property
    def items(self) -> CfgStruct:
        return self._parse("ItemPrototypes.cfg")

    @cached_property
    def difficulty(self) -> CfgStruct:
        return self._parse("DifficultyPrototypes.cfg")

    @cached_property
    def weightparams(self) -> CfgStruct:
        return self._parse("ObjWeightParamsPrototypes.cfg")

    @cached_property
    def effectmax(self) -> CfgStruct:
        return self._parse("ObjEffectMaxParamsPrototypes.cfg")

    @cached_property
    def effects(self) -> CfgStruct:
        return self._parse("EffectPrototypes.cfg")

    @cached_property
    def floatproviders(self) -> CfgStruct:
        return self._parse("FloatProviderPrototypes.cfg")

    @cached_property
    def weaponsettings(self) -> CfgStruct:
        return self._parse("WeaponData/CharacterWeaponSettingsPrototypes.cfg")

    @cached_property
    def weaponattributes(self) -> CfgStruct:
        return self._parse("WeaponData/WeaponAttributesPrototypes.cfg")

    @cached_property
    def trade(self) -> CfgStruct:
        return self._parse("TradePrototypes.cfg")

    @cached_property
    def holdbreath(self) -> CfgStruct:
        return self._parse("ObjHoldBreathParamsPrototypes.cfg")

    @cached_property
    def weapongeneral(self) -> CfgStruct:
        return self._parse("WeaponData/WeaponGeneralSetupPrototypes.cfg")

    @cached_property
    def corevars(self) -> CfgStruct:
        return self._parse("CoreVariables.cfg")

    @cached_property
    def stashes(self) -> CfgStruct:
        return self._parse("StashPrototypes.cfg")

    @cached_property
    def itemgenerators(self) -> CfgStruct:
        return self._parse("ItemGeneratorPrototypes.cfg")

    @cached_property
    def relations(self) -> CfgStruct:
        return self._parse("RelationPrototypes.cfg")

    @cached_property
    def emissions(self) -> CfgStruct:
        return self._parse("EmissionPrototypes.cfg")

    @cached_property
    def questnodes(self) -> CfgStruct:
        """Lazily parse quest nodes only when needed; the checked file was ~75 MB
        with ~84,000 structs. Access has the same cost considerations as itemgenerators."""
        return self._parse("QuestNodePrototypes.cfg")

    @cached_property
    def dialogs(self) -> CfgStruct:
        """Lazily parse DialogPrototypes for simultaneous-job dialogue gates.

        The checked file was 31.6 MB."""
        return self._parse("DialogPrototypes.cfg")

    @cached_property
    def journals(self) -> CfgStruct:
        """Loaded only when exporting simultaneous repeatable jobs."""
        return self._parse("JournalQuestPrototypes.cfg")

    @cached_property
    def aiglobals(self) -> CfgStruct:
        return self._parse("AIGlobals.cfg")

    @cached_property
    def hearingsensors(self) -> CfgStruct:
        return self._parse("AIPrototypes/HearingSensorPrototypes.cfg")

    @cached_property
    def visionscanners(self) -> CfgStruct:
        return self._parse("AIPrototypes/VisionScannerPrototypes.cfg")

    @cached_property
    def camerashake(self) -> CfgStruct:
        return self._parse("CameraShakePrototypes.cfg")

    @cached_property
    def artifactspawners(self) -> CfgStruct:
        return self._parse("ArtifactSpawnerPrototypes.cfg")

    @cached_property
    def passivedetectors(self) -> CfgStruct:
        return self._parse("PassiveDetectorPrototypes.cfg")

    @cached_property
    def fasttravel(self) -> CfgStruct:
        return self._parse("FastTravelPrototypes.cfg")

    @cached_property
    def boolproviders(self) -> CfgStruct:
        return self._parse("BoolProviderPrototypes.cfg")

    @cached_property
    def abilities(self) -> CfgStruct:
        return self._parse("AbilityPrototypes.cfg")

    @cached_property
    def melee(self) -> CfgStruct:
        return self._parse("MeleeWeaponPrototypes.cfg")

    @cached_property
    def flashlights(self) -> CfgStruct:
        """Read FlashlightPrototypes.

        Only NPCFlashlight has cfg light values in the checked data; player light
        behavior is controlled by Blueprint curves."""
        return self._parse("FlashlightPrototypes.cfg")

    @cached_property
    def projectiles(self) -> CfgStruct:
        """Read ProjectilePrototypes for bullets, Gauss, RPG and grenades."""
        return self._parse("ProjectilePrototypes.cfg")

    @cached_property
    def sleepparams(self) -> CfgStruct:
        """ObjSleepParamsPrototypes: DefaultSleepParams (AllowSleepThreshold 50,
        SleepHoursMultiplier 0.08, MinSleepHours 7, bAllowEmissionSleep)."""
        return self._parse("ObjSleepParamsPrototypes.cfg")

    MUTANT_PROTECTION_KEYS = ("Strike", "Shot", "Burn", "Shock", "ChemicalBurn",
                              "Radiation", "PSY")

    def mutant_protections(self) -> dict[str, dict[str, float]]:
        """Return {SID: {protection_type: value}} for mutants with positive protection.

        In the checked 2.0.x data, 46 of 47 had protection, mainly Strike; Shot was zero."""
        result: dict[str, dict[str, float]] = {}
        for sid in self.mutants():
            values: dict[str, float] = {}
            for key in self.MUTANT_PROTECTION_KEYS:
                value = parse_number(self.resolve(self.obj, sid, f"Protection.{key}"))
                if value > 0:
                    values[key] = value
            if values:
                result[sid] = values
        return result

    def slot_weapon_items(self) -> dict[str, tuple[str | None, str, str | None]]:
        """Return {item_SID: (category, slot, edition_or_None)} for non-template weapons."""
        result: dict[str, tuple[str | None, str, str | None]] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "weapon":
                continue
            slot = (self.resolve(self.items, sid, "ItemSlotType") or "").split("::")[-1].strip()
            if slot:
                result[sid] = (self.weapon_category(sid), slot, None)
        for edition, trees in self.dlc_editions.items():
            items = trees.get("items")
            for sid in (items.children if items else ()):
                if sid in result or "#" in sid or sid.startswith("Template"):
                    continue
                chain = self.dlc_item_chain(edition, sid)
                if not any(n.name == "TemplateWeapon" or n.name in WEAPON_CATEGORY_TEMPLATES
                           for n in chain):
                    continue
                slot = (self._chain_get(chain, "ItemSlotType") or "").split("::")[-1].strip()
                if slot:
                    result[sid] = (self.dlc_weapon_category(edition, sid), slot, edition)
        return result

    def pistol_slot_literal(self) -> str | None:
        """Read the pistol-slot enum from an installed pistol item."""
        for sid, (_cat, slot, edition) in self.slot_weapon_items().items():
            if slot == "Pistol" and edition is None:
                raw = self.resolve(self.items, sid, "ItemSlotType")
                if raw:
                    return raw.strip()
        return None

    @cached_property
    def aimassist(self) -> CfgStruct:
        """Read mouse/gamepad aim-assist presets and weapon-class variants.

        Strength is in CurveFloat assets; cfg can disable assistance by replacing
        cone SIDs with the Empty cone."""
        return self._parse("AimAssistPresetPrototypes.cfg")

    def armor_artifact_slots(self) -> dict[str, tuple[int, str | None]]:
        """Return {SID: (vanilla_artifact_slots, edition_or_None)} for player body armor.

        Head-slot items are excluded."""
        result: dict[str, tuple[int, str | None]] = {}
        for sid, (slot, _values) in self.player_armors().items():
            if slot != "Body":
                continue
            dlc = self.dlc_player_armors().get(sid)
            if dlc is not None:
                chain = self.dlc_item_chain(dlc[2], sid)
                raw = self._chain_get(chain, "ArtifactSlots")
                edition: str | None = dlc[2]
            else:
                raw = self.resolve(self.items, sid, "ArtifactSlots")
                edition = None
            if raw is None:
                continue
            result[sid] = (int(parse_number(raw, 0.0)), edition)
        return result

    @cached_property
    def saveload(self) -> CfgStruct:
        """Unbinarized SaveLoadVariables: DefaultConfig.SavesLimit per save type; 0 = unlimited."""
        return self._parse("SaveLoadVariables.cfg")

    @cached_property
    def autosave(self) -> CfgStruct:
        """Unbinarized AutoSaveVariables: DefaultConfig.AutoSaveIntervalTime in seconds."""
        return self._parse("AutoSaveVariables.cfg")

    # --- 1.28.0 (core controls P1) ---
    @cached_property
    def quicksave(self) -> CfgStruct:
        """Read QuickSaveOverwriteTime in seconds from unbinarized QuickSaveVariables.

        This is the window in which quicksaves overwrite the same slot."""
        return self._parse("QuickSaveVariables.cfg")

    @cached_property
    def corevarscustom(self) -> CfgStruct:
        """Read unbinarized CoreVariablesCustom overrides.

        CustomConfigOverride repeats DefaultConfig keys and may override core
        patches at load time; _corevars_custom_patch mirrors affected keys there.
        See docs/CORE_SWEEP_RESEARCH.md, section 0."""
        return self._parse("CoreVariablesCustom.cfg")

    # --- 1.28.0 (core controls P3) ---
    @cached_property
    def enemyevaluators(self) -> CfgStruct:
        """Read the shared NPC target evaluator (EnemyEvaluatorPrototypes [0]).

        See docs/CORE_SWEEP_RESEARCH.md, section 2.5."""
        return self._parse("EnemyEvaluatorPrototypes.cfg")

    @cached_property
    def coverevaluators(self) -> CfgStruct:
        """Read cover evaluators, including special/boss children with explicit keys.

        See docs/CORE_SWEEP_RESEARCH.md, section 2.5."""
        return self._parse("CoverEvaluatorPrototypes.cfg")

    # --- 1.28.0 (core controls P4) ---
    @cached_property
    def flairsensors(self) -> CfgStruct:
        """Read scent sensors, whose children declare their own values.

        See docs/CORE_SWEEP_RESEARCH.md, section 2.4."""
        return self._parse("AIPrototypes/FlairSensorPrototypes.cfg")

    # --- 1.28.0 (core controls P5) ---
    @cached_property
    def needspresets(self) -> CfgStruct:
        """Read NPC needs presets, including GoalNeeds entries for AI.Need.Expansion.

        Array positions vary; MutantGeneric uses [1] in the checked data."""
        return self._parse("NPCNeedsPresetPrototypes.cfg")

    @cached_property
    def alifepolicy(self) -> CfgStruct:
        """ALifePolicyPrototypes: one Default struct with refill cooldowns,
        distance range and corpse budget; extinction thresholds are excluded."""
        return self._parse("ALifePrototypes/ALifePolicyPrototypes.cfg")

    @cached_property
    def alifefactions(self) -> CfgStruct:
        """Read ALifePopulationManagerFactionPrototypes without altering camp bands."""
        return self._parse("ALifePrototypes/ALifePopulationManagerFactionPrototypes.cfg")

    # --- 1.28.0 (core controls P6) ---
    @cached_property
    def barbedwire(self) -> CfgStruct:
        """Read the empty base and explicit Limiting/Overlappable barbed-wire children."""
        return self._parse("BarbedWirePrototypes.cfg")

    @cached_property
    def destructibles(self) -> CfgStruct:
        """Lazily read destructible objects when their controls differ from vanilla.

        Struct keys are [N] indices; the SID is stored inside each struct."""
        return self._parse("DestructibleObjectPrototypes.cfg")

    @cached_property
    def physicsinteractions(self) -> CfgStruct:
        """Read physics interaction prototypes and their explicit PlayerPushImpulse."""
        return self._parse("PhysicsInteractionPrototypes.cfg")

    @cached_property
    def weatherchains(self) -> CfgStruct:
        """WeatherChainPrototypes: 18 chains, 21 transition steps,
        22 WeatherTransitionTimeMultiplier values across two array levels."""
        return self._parse("WeatherChainPrototypes.cfg")

    @cached_property
    def singletonconstants(self) -> CfgStruct:
        """Read unbinarized TimeManager sky constants.

        Latitude, Longitude, TimeZone, NorthOffsetAngle and Start* keys are excluded."""
        return self._parse("SingletonConstants.cfg")

    # --- 1.28.0 (core controls P7) ---
    @cached_property
    def packofitems(self) -> CfgStruct:
        """Read hand-placed loot groups.

        The base tweak targets ArtifactUncommon; other groups' rank gates are excluded."""
        return self._parse("PackOfItemsGroupPrototypes.cfg")

    # --- 1.28.0 (core controls P8) ---
    @cached_property
    def npcprototypes(self) -> CfgStruct:
        """Lazily read NPC trader coefficients and money when trader controls change."""
        return self._parse("NPCPrototypes.cfg")

    @cached_property
    def weatherselection(self) -> CfgStruct:
        return self._parse("WeatherSelectionPrototypes.cfg")

    @cached_property
    def regional_weather(self) -> dict:
        """Audited region/weather choices available in this installed snapshot."""
        from .regional_weather import catalog
        return catalog(self)

    @cached_property
    def artifact_editor(self) -> dict:
        """Audited ordinary artifacts and related controls in the loaded data."""
        from .artifact_extensions import catalog
        return catalog(self)

    @cached_property
    def npc_equipment_editor(self) -> dict:
        """Validated object links and weighted choices for ordinary NPC roles."""
        from .npc_equipment import catalog
        return catalog(self)

    @cached_property
    def detail_editor(self) -> dict:
        """Available data-only detail settings for this installed snapshot."""
        from .detail_controls import catalog
        return catalog(self)

    # --- 1.26.0 ---
    @cached_property
    def posteffects(self) -> CfgStruct:
        """PostEffectProcessorPrototypes: CrouchEffectProcessor.Intensity 0.6."""
        return self._parse("PostEffectProcessorPrototypes.cfg")

    @cached_property
    def explosions(self) -> CfgStruct:
        """ExplosionPrototypes: RGD5/F1/VOG25/M203/PG7V, barrels and gas cylinders."""
        return self._parse("ExplosionPrototypes.cfg")

    @cached_property
    def corpseclues(self) -> CfgStruct:
        """CorpseClueStashPrototypes: Default + 23 regions, Base/AddSpawnChance."""
        return self._parse("CorpseClueStashPrototypes.cfg")

    @cached_property
    def markers(self) -> CfgStruct:
        """MarkerPrototypes: 359 PDA markers for places, regions, traders and other targets."""
        return self._parse("MarkerPrototypes.cfg")

    @cached_property
    def combatsync(self) -> CfgStruct:
        """Read combat synchronization presets with rank-specific FilterGroups budgets."""
        return self._parse("CombatSynchronizationPrototypes.cfg")

    @cached_property
    def containers(self) -> CfgStruct:
        """ItemContainerPrototypes: 25 container types, RespawnTimeSeconds 0."""
        return self._parse("ItemContainerPrototypes.cfg")

    @cached_property
    def anomalies(self) -> CfgStruct:
        """Read anomaly prototypes; the existing tweak targets ClickerAnomaly."""
        return self._parse("AnomalyPrototypes.cfg")

    def human_npcs(self) -> list[str]:
        """Return human NPC prototype SIDs, excluding mutant factions, Player and [0]."""
        out: list[str] = []
        for sid in self.obj.children:
            if sid in ("[0]", "Player") or "#" in sid:
                continue
            faction = self._chain_get(self._resolve_chain(self.obj, sid), "Faction")
            if faction is None or faction in MUTANT_FACTIONS:
                continue
            out.append(sid)
        return out

    def scope_effects(self) -> dict[str, tuple[str | None, list[str]]]:
        """Return {scope_SID: (zoom_effect_or_None, [penalty_effects])} for real scopes.

        Resolve AimingFOVX*, ScopeAimingTimeNeg* and ScopeAimingMovementNeg* from
        EffectPrototypeSIDs. Each checked vanilla scope declares its own list."""
        result: dict[str, tuple[str | None, list[str]]] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            chain = self._resolve_chain(self.items, sid)
            if self._chain_get(chain, "AttachType") != "EAttachType::Scope":
                continue
            effects: list[str] = []
            for node in chain:
                if "EffectPrototypeSIDs" in node.children:
                    effects = [v.strip() for v in node.children["EffectPrototypeSIDs"].values.values()]
                    break
            zoom = next((e for e in effects if e.startswith("AimingFOVX")), None)
            pens = [e for e in effects if e.startswith(("ScopeAimingTimeNeg", "ScopeAimingMovementNeg"))]
            if zoom or pens:
                result[sid] = (zoom, pens)
        return result

    def scope_effect_list(self, sid: str) -> dict[str, str]:
        """Return {index: effect_SID} from the nearest declared scope-effect list."""
        for node in self._resolve_chain(self.items, sid):
            if "EffectPrototypeSIDs" in node.children:
                return {k: v.strip() for k, v in node.children["EffectPrototypeSIDs"].values.items()}
        return {}

    @cached_property
    def trade_text(self) -> str:
        return (self.dir / "TradePrototypes.cfg").read_text(
            encoding="utf-8-sig", errors="replace"
        )

    # ------------------------------------------------------------ inheritance
    @staticmethod
    def _resolve_chain(root: CfgStruct, sid: str) -> list[CfgStruct]:
        """Follow same-file refkey inheritance: [prototype, parent, grandparent, ...]."""
        chain: list[CfgStruct] = []
        seen: set[str] = set()
        current: str | None = sid
        while current is not None and current not in seen:
            seen.add(current)
            node = root.children.get(current)
            if node is None:
                break
            chain.append(node)
            current = node.attr_dict().get("refkey")
        return chain

    @staticmethod
    def _chain_get(chain: list[CfgStruct], path: str) -> str | None:
        for node in chain:
            value = node.get(path)
            if value is not None:
                return value
        return None

    def resolve(self, root: CfgStruct, sid: str, path: str) -> str | None:
        return self._chain_get(self._resolve_chain(root, sid), path)

    def template_of(self, sid: str) -> str | None:
        """Find the first Template* ancestor in an item's inheritance chain."""
        for node in self._resolve_chain(self.items, sid):
            if node.name.startswith("Template"):
                # Continue through quest templates to their underlying base template.
                if node.name.startswith("TemplateQuest"):
                    continue
                return node.name
        return None

    def item_category(self, sid: str) -> str | None:
        for node in self._resolve_chain(self.items, sid):
            name = node.name
            if name in CATEGORY_TEMPLATES:
                return CATEGORY_TEMPLATES[name]
        return None

    # ------------------------------------------------------------- inventories
    def mutants(self) -> dict[str, float]:
        """Return {SID: effective vanilla MaxHP} for all mutant prototypes."""
        result: dict[str, float] = {}
        for sid, node in self.obj.children.items():
            if sid == "[0]" or "#" in sid:
                continue
            chain = self._resolve_chain(self.obj, sid)
            faction = self._chain_get(chain, "Faction")
            if faction not in MUTANT_FACTIONS:
                continue
            hp = self._chain_get(chain, "VitalParams.MaxHP")
            if hp is None:
                continue
            result[sid] = parse_number(hp)
        return result

    MUTANT_SPEED_KEYS = ("WalkSpeed", "RunSpeed", "SprintSpeed")

    def mutant_speeds(self) -> dict[str, dict[str, float]]:
        """Return {SID: {SpeedKey: value}} for all resolved mutant prototypes."""
        result: dict[str, dict[str, float]] = {}
        for sid in self.mutants():
            speeds = {}
            for key in self.MUTANT_SPEED_KEYS:
                value = parse_number(self.resolve(self.obj, sid, f"MovementParams.{key}"))
                if value > 0:
                    speeds[key] = value
            if speeds:
                result[sid] = speeds
        return result

    def mutant_faction(self, sid: str) -> str | None:
        """Return a mutant prototype's creature faction (species)."""
        faction = self._chain_get(self._resolve_chain(self.obj, sid), "Faction")
        return faction if faction in MUTANT_FACTIONS else None

    def mutant_regens(self) -> dict[str, float]:
        """Return positive VitalParams.RegenHP values for mutant prototypes."""
        result: dict[str, float] = {}
        for sid in self.mutants():
            value = parse_number(
                self.resolve(self.obj, sid, "VitalParams.RegenHP"))
            if value > 0:
                result[sid] = value
        return result

    def mutant_attack_damages(self, species: str) -> dict[str, tuple[str, float]]:
        """Return {attack_struct: (damage_path, vanilla_value)} for one mutant species.

        Damage is normally top-level, but ChargeAbility_* uses DamageParams.
        Skip utility abilities with nonpositive damage."""
        prefixes = SPECIES_ABILITY_PREFIXES.get(species, [])
        result: dict[str, tuple[str, float]] = {}
        for sid, node in self.abilities.children.items():
            if "#" in sid or not any(sid.startswith(p) for p in prefixes):
                continue
            for path in ("Damage", "DamageParams.Damage"):
                value = parse_number(node.get(path))
                if value > 0:
                    result[sid] = (path, value)
                    break
        return result

    # Bloodsucker prototypes with InvisibilityFeatureData.
    INVISIBILITY_KEYS = ("ToVisibleSeconds", "ToInvisibleSeconds",
                        "InvisibilityLossFromDamage")

    def invisibility_prototypes(self) -> dict[str, dict[str, float]]:
        """Return {SID: {key: value}} for prototypes declaring invisibility data."""
        result: dict[str, dict[str, float]] = {}
        for sid, node in self.obj.children.items():
            if "#" in sid:
                continue
            data = node.children.get("InvisibilityFeatureData")
            if data is None:
                continue
            values = {}
            for key in self.INVISIBILITY_KEYS:
                value = parse_number(data.values.get(key))
                if value > 0:
                    values[key] = value
            if values:
                result[sid] = values
        return result

    # Scalable consumable-effect types; sign rules are documented in
    # docs/V15_DATA_RESEARCH.md.
    CONSUMABLE_SAFE_TYPES = {
        "EEffectType::Health", "EEffectType::Bleeding", "EEffectType::Radiation",
        "EEffectType::HungerPoints", "EEffectType::Stamina",
        "EEffectType::RegenStamina", "EEffectType::PsyPoints",
        "EEffectType::DegenPsyPoints", "EEffectType::SleepinessPoints",
        "EEffectType::DegenBleeding", "EEffectType::Drunkness",
    }
    # Positive values increase hunger/intoxication for these types;
    # scale only their negative values.
    CONSUMABLE_NEGATIVE_ONLY = {"EEffectType::HungerPoints",
                                "EEffectType::Drunkness"}

    def medical_healing_effects(self) -> set[str]:
        """Return positive Health-effect SIDs referenced by medical consumables.

        Identify medicine by its negative Bleeding effect, rather than item names.
        This separates medkits/bandages from food and drinks in the checked data."""
        out: set[str] = set()
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "consumable":
                continue
            effect_sids: list[str] = []
            for node in self._resolve_chain(self.items, sid):
                effects = node.children.get("EffectPrototypeSIDs")
                if effects is not None:
                    effect_sids = [v for v in effects.values.values()]
                    break
            nodes = [self.effects.children.get(e) for e in effect_sids]
            nodes = [n for n in nodes if n is not None]
            stops_bleeding = any(
                n.values.get("Type") == "EEffectType::Bleeding"
                and parse_number(n.values.get("ValueMin")) < 0
                for n in nodes)
            if not stops_bleeding:
                continue
            for effect_sid, node in zip(effect_sids, nodes):
                if (node.values.get("Type") == "EEffectType::Health"
                        and parse_number(node.values.get("ValueMin")) > 0):
                    out.add(effect_sid)
        return out

    def consumable_effects(self) -> dict[str, CfgStruct]:
        """Return {effect SID: effect node} for supported effects referenced by consumables."""
        sids: set[str] = set()
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "consumable":
                continue
            for node in self._resolve_chain(self.items, sid):
                effects = node.children.get("EffectPrototypeSIDs")
                if effects is not None:
                    sids.update(effects.values.values())
                    break
        result: dict[str, CfgStruct] = {}
        for sid in sids:
            node = self.effects.children.get(sid)
            if node is None:
                continue
            etype = node.values.get("Type", "")
            if etype not in self.CONSUMABLE_SAFE_TYPES:
                continue
            if etype in self.CONSUMABLE_NEGATIVE_ONLY:
                if parse_number(node.values.get("ValueMin")) >= 0:
                    continue
            result[sid] = node
        return result

    # Anomaly damage-effect SIDs by element; values are read live.
    # PSY effects do not directly damage HP.
    ANOMALY_EFFECT_SETS = {
        "electro": ["ElectroAnomaly", "ElectroAnomalyPrologue"],
        "chemical": ["ChemicalDamage", "SoapBubbleDamage",
                     "ParticleSoapBubbleDamage", "ToxicCloudDamage"],
        "fire": ["FireAnomalyDPS", "FireBurning", "HeatBurning",
                 "SteamAnomalyDPS", "SteamBurning", "SteamHeatBurning",
                 "ClickerAnomalyHit", "LavaLampAnomalyFloor",
                 "LavaLampAnomalyHit", "FireBallAnomaly"],
        "gravity": ["CarouselAnomaly", "RazorAnomalyDamageDPSLow",
                    "RazorAnomalyDamageDPSHigh", "RazorAnomalyLowBleed",
                    "RazorAnomalyHighBleed", "ExpulsionDamage",
                    "DiamondDPS", "DiamondBleeding"],
    }

    # Weather substructs classified as rain/storm.
    RAIN_WEATHER_TYPES = ("Stormy", "LightRainy", "Rainy", "Thundery")

    # Never patch the zero-valued stash template: its item SID is empty.
    # Activating it would introduce invalid item references in inheriting stashes.
    # See docs/GENERATOR_RESEARCH.md.
    STASH_TEMPLATE = "empty"

    # Skip inactive vanilla generators: *_MainLoot entries have zero maximum
    # spawn chance, and the checked *_Corpse structs have no GameData references.
    STASH_UNUSED = {
        "Stash_AmmoSNG_Smart_MainLoot", "Stash_AmmoNATO_Smart_MainLoot",
        "StashMedicine_Corpse", "StashVodka_Corpse",
    }

    def stash_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Yield smart-loot entries from stash/corpse generators.

        Return (stash_SID, generator_key, group_key, entry_key, node), preserving
        actual keys. Available ranks and groups differ between structs."""
        out: list[tuple[str, str, str, str, CfgStruct]] = []
        for sid, node in self.stashes.children.items():
            if sid == self.STASH_TEMPLATE or sid in self.STASH_UNUSED or "#" in sid:
                continue
            gens = node.children.get("ItemGenerators")
            if gens is None:
                continue
            for gen_key, gen in gens.children.items():
                params = gen.children.get("SmartLootParams")
                if params is None:
                    continue
                for group, group_node in params.children.items():
                    for entry_key, entry in group_node.children.items():
                        out.append((sid, gen_key, group, entry_key, entry))
        return out

    # Loot quantities: scale MinCount/MaxCount only under PossibleItems.
    # MoneyGenerator uses the same names for currency and must remain unchanged.
    # Filter both struct key/SID patterns and referenced ItemPrototypeSIDs;
    # name filtering alone misses quest items and unique equipment.
    # See docs/GENERATOR_RESEARCH.md, section 5.

    # Empty base template inherited by 1,773 prototypes. Never patch it.
    LOOT_TEMPLATE_KEY = "[0]"

    # Exclude story, reward, container, trader and developer names.
    # Trade also catches inventories not linked through TradePrototypes.
    LOOT_UNSAFE_NAME = re.compile(
        r"(?:^|_)(MQ|EQ|SQ|RSQ|ANCQ)(?=\d|_|$)|Quest|QSBIG|GDEQ|Reward|^C_"
        r"|(?:^|_)BP_|UAID_|Container|Template|Player|Boss|Arena"
        r"|(?:^|_)Key|(?:^|_)Safe|Icon|PDA|Trade"
    )
    # GamePass_Stash_* tables are ordinary base-game world stashes.
    # Content validation and currency exclusion cover them; their names alone
    # are not grounds for exclusion.

    # Trader traversal uses the same filter without Trade, which would
    # otherwise exclude the very inventories being collected.
    TRADER_UNSAFE_NAME = re.compile(
        r"(?:^|_)(MQ|EQ|SQ|RSQ|ANCQ)(?=\d|_|$)|Quest|QSBIG|GDEQ|Reward|^C_"
        r"|(?:^|_)BP_|UAID_|Container|Template|Player|Boss|Arena"
        r"|(?:^|_)Key|(?:^|_)Safe|Icon|PDA"
    )

    # Unique weapons use Gun_<name>_<class>; standard weapons use GunAK74_ST, etc.
    LOOT_UNIQUE_ITEM = re.compile(r"^Gun_[A-Z]")

    # Intentional placeholder SID absent from ItemPrototypes; allow its block.
    LOOT_EMPTY_ITEMS = {"empty", "Empty"}

    # Explicitly exclude the quest collar generator: neither normal filter
    # catches it, and duplicate collars can obstruct quest progression.
    LOOT_DENY_SIDS = {"MutantElectrocollarGenerator"}

    # Resolve both independent quest markers. IsQuestItem alone misses items
    # marked only by IsQuestItemPrototype, including event-linked PDAs.
    LOOT_QUEST_FLAGS = ("IsQuestItem", "IsQuestItemPrototype")

    # Currency also appears as PossibleItems money cards. Detect it through
    # pickup-effect types, independently of item names.
    LOOT_MONEY_EFFECT = "EEffectType::AddMoney"
    LOOT_EFFECT_KEYS = ("EffectOnPickPrototypeSIDs", "EffectPrototypeSIDs")

    @cached_property
    def _quest_item_sids(self) -> set[str]:
        """Return item SIDs with either quest marker, resolving inherited values."""
        out: set[str] = set()
        for sid in self.items.children:
            for flag in self.LOOT_QUEST_FLAGS:
                value = self.resolve(self.items, sid, flag)
                if value is None:
                    continue
                if value.strip().rstrip(";").strip().lower() in ("true", "1"):
                    out.add(sid)
                    break
        return out

    @cached_property
    def _money_item_sids(self) -> set[str]:
        """Return items whose resolved pickup effects include AddMoney."""
        money_effects = {
            sid for sid, node in self.effects.children.items()
            if self.LOOT_MONEY_EFFECT in (node.values.get("Type") or "")
        }
        if not money_effects:
            return set()
        out: set[str] = set()
        for sid in self.items.children:
            for node in self._resolve_chain(self.items, sid):
                for key in self.LOOT_EFFECT_KEYS:
                    child = node.children.get(key)
                    if child and any(v.strip() in money_effects
                                     for v in child.values.values()):
                        out.add(sid)
                        break
                if sid in out:
                    break
        return out

    @cached_property
    def _generator_key_by_sid(self) -> dict[str, str]:
        """Map SID to the actual struct key.

        Indexed [N] keys must be preserved or bpatch would create a different node."""
        out: dict[str, str] = {}
        for key, node in self.itemgenerators.children.items():
            out.setdefault((node.values.get("SID") or key).strip(), key)
            out.setdefault(key, key)
        return out

    @cached_property
    def _trade_generator_keys(self) -> set[str]:
        """Find trader inventory generators excluded from the general loot tweak.

        Traverse roots linked by TradePrototypes transitively. Also exclude
        generators with Trade in their names, but do not propagate that exclusion:
        they can share consumable pools with ordinary NPCs."""
        root = self.itemgenerators
        roots: set[str] = set()
        for node in self.trade.children.values():
            for sub in node.walk():
                value = sub.values.get("ItemGeneratorPrototypeSID")
                key = self._generator_key_by_sid.get((value or "").strip())
                if key:
                    roots.add(key)

        hull: set[str] = set()
        stack = list(roots)
        while stack:
            key = stack.pop()
            if key in hull:
                continue
            hull.add(key)
            node = root.children.get(key)
            for sub in (node.walk() if node else ()):
                value = sub.values.get("ItemGeneratorPrototypeSID")
                child = self._generator_key_by_sid.get((value or "").strip())
                if child and child not in hull:
                    stack.append(child)

        hull.update(key for key, node in root.children.items()
                    if "Trade" in key or "Trade" in (node.values.get("SID") or ""))
        return hull

    def _loot_block_is_safe(self, node: CfgStruct) -> bool:
        """Validate every ItemPrototypeSID in a generator.

        Reject the entire prototype if any item is a quest item, unique, or absent
        from ItemPrototypes and therefore unverifiable."""
        for gen_key, gen in node.children.items():
            if gen_key != "ItemGenerator":
                continue
            for slot in gen.children.values():
                items = slot.children.get("PossibleItems")
                for item in (items.children.values() if items else ()):
                    sid = (item.values.get("ItemPrototypeSID") or "").strip()
                    if not sid or sid in self.LOOT_EMPTY_ITEMS:
                        continue
                    if sid in self._quest_item_sids:
                        return False
                    if self.LOOT_UNIQUE_ITEM.match(sid):
                        return False
                    if sid not in self.items.children:
                        return False
        return True

    def loot_generators(self) -> list[str]:
        """Return generator struct keys eligible for quantity scaling."""
        safe: list[str] = []
        for key, node in self.itemgenerators.children.items():
            sid = (node.values.get("SID") or key).strip()
            if key == self.LOOT_TEMPLATE_KEY or "#" in key:
                continue
            if key in self.LOOT_DENY_SIDS or sid in self.LOOT_DENY_SIDS:
                continue
            if key in self._trade_generator_keys:
                continue
            if sid.startswith("All"):        # Development collection generators (900 items).
                continue
            if (self.LOOT_UNSAFE_NAME.search(key)
                    or self.LOOT_UNSAFE_NAME.search(sid)):
                continue
            if not self._loot_block_is_safe(node):
                continue
            safe.append(key)
        return safe

    def _loot_item_is_skippable(self, sid: str) -> bool:
        """Skip individual currency entries and unmarked quest-pattern items.

        These isolated entries do not invalidate otherwise ordinary loot pools."""
        if sid in self._money_item_sids:
            return True
        return bool(self.LOOT_UNSAFE_NAME.search(sid))

    def loot_count_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Yield scalable quantities from eligible generator prototypes.

        Return (struct_key, generator_key, slot_key, item_key, node), preserving
        named and indexed keys. Traverse ItemGenerator, never MoneyGenerator."""
        out: list[tuple[str, str, str, str, CfgStruct]] = []
        root = self.itemgenerators
        for key in self.loot_generators():
            node = root.children[key]
            for gen_key, gen in node.children.items():
                if gen_key != "ItemGenerator":
                    continue
                for slot_key, slot in gen.children.items():
                    if "#" in slot_key:
                        continue
                    items = slot.children.get("PossibleItems")
                    for item_key, item in (items.children.items() if items else ()):
                        if "#" in item_key:
                            continue
                        item_sid = (item.values.get("ItemPrototypeSID") or "").strip()
                        if item_sid and self._loot_item_is_skippable(item_sid):
                            continue
                        if "MinCount" in item.values or "MaxCount" in item.values:
                            out.append((key, gen_key, slot_key, item_key, item))
        return out

    # Weapon slot categories for condition scaling; exclude armor and other items.
    CONDITION_CATEGORIES = frozenset({
        "EItemGenerationCategory::WeaponPrimary",
        "EItemGenerationCategory::WeaponSecondary",
        "EItemGenerationCategory::WeaponPistol",
    })

    def loot_durability_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Yield weapon condition entries from eligible non-trader loot.

        Require both MinDurability and MaxDurability, with a positive maximum,
        so patches cannot introduce missing fields."""
        out: list[tuple[str, str, str, str, CfgStruct]] = []
        root = self.itemgenerators
        for key in self.loot_generators():
            node = root.children[key]
            for gen_key, gen in node.children.items():
                if gen_key != "ItemGenerator":
                    continue
                for slot_key, slot in gen.children.items():
                    if "#" in slot_key:
                        continue
                    category = (slot.values.get("Category") or "").strip()
                    if category not in self.CONDITION_CATEGORIES:
                        continue
                    items = slot.children.get("PossibleItems")
                    for item_key, item in (items.children.items()
                                           if items else ()):
                        if "#" in item_key:
                            continue
                        if ("MinDurability" not in item.values
                                or "MaxDurability" not in item.values):
                            continue
                        if parse_number(item.values.get("MaxDurability")) <= 0:
                            continue
                        item_sid = (item.values.get("ItemPrototypeSID")
                                    or "").strip()
                        if item_sid and self._loot_item_is_skippable(item_sid):
                            continue
                        out.append((key, gen_key, slot_key, item_key, item))
        return out

    # Weapon/armor categories for NPC gear-quality weighted pools.
    GEAR_CATEGORIES = frozenset({
        "EItemGenerationCategory::WeaponPrimary",
        "EItemGenerationCategory::WeaponSecondary",
        "EItemGenerationCategory::WeaponPistol",
        "EItemGenerationCategory::BodyArmor",
        "EItemGenerationCategory::Head",
    })

    def gear_weight_pools(self):
        """Yield eligible equipment pools with at least two weighted choices.

        Each result is (struct, generator, slot, [(item_key, node, weight, cost)]).
        Unresolved prices remain None so their weights stay unchanged."""
        out = []
        root = self.itemgenerators
        for key in self.loot_generators():
            gen = root.children[key].children.get("ItemGenerator")
            if gen is None:
                continue
            for slot_key, slot in gen.children.items():
                if (slot.values.get("Category")
                        or "").strip() not in self.GEAR_CATEGORIES:
                    continue
                items = slot.children.get("PossibleItems")
                if not items:
                    continue
                pool = []
                for item_key, item in items.children.items():
                    if "#" in item_key or "Weight" not in item.values:
                        continue
                    weight = parse_number(item.values.get("Weight"))
                    if weight <= 0:
                        continue
                    isid = (item.values.get("ItemPrototypeSID") or "").strip()
                    cost = None
                    if isid and not self._loot_item_is_skippable(isid):
                        raw = self.resolve(self.items, isid, "Cost")
                        if raw is not None and parse_number(raw) > 0:
                            cost = parse_number(raw)
                    pool.append((item_key, item, weight, cost))
                if len(pool) >= 2:
                    out.append((key, "ItemGenerator", slot_key, pool))
        return out

    def trader_stock_generators(self) -> list[str]:
        """Return transitive trader-generator keys linked from TradePrototypes.

        Exclude All* developer collections and quest-name matches. This is the
        inventory set excluded by general loot scaling; see GENERATOR_RESEARCH.md."""
        root = self.itemgenerators
        roots: set[str] = set()
        for node in self.trade.children.values():
            for sub in node.walk():
                value = sub.values.get("ItemGeneratorPrototypeSID")
                key = self._generator_key_by_sid.get((value or "").strip())
                if key:
                    roots.add(key)
        hull: set[str] = set()
        stack = list(roots)
        while stack:
            key = stack.pop()
            if key in hull:
                continue
            hull.add(key)
            node = root.children.get(key)
            for sub in (node.walk() if node else ()):
                value = sub.values.get("ItemGeneratorPrototypeSID")
                child = self._generator_key_by_sid.get((value or "").strip())
                if child and child not in hull:
                    stack.append(child)
        safe: list[str] = []
        for key in sorted(hull):
            node = root.children.get(key)
            if node is None or "#" in key:
                continue
            sid = (node.values.get("SID") or key).strip()
            if sid.startswith("All") or key.startswith("All"):
                continue
            if key in self.LOOT_DENY_SIDS or sid in self.LOOT_DENY_SIDS:
                continue
            if (self.TRADER_UNSAFE_NAME.search(key)
                    or self.TRADER_UNSAFE_NAME.search(sid)):
                continue
            safe.append(key)
        return safe

    def trader_stock_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Yield trader stock quantity/chance entries.

        Skip currency and quest-pattern items individually; never traverse MoneyGenerator."""
        out: list[tuple[str, str, str, str, CfgStruct]] = []
        root = self.itemgenerators
        for key in self.trader_stock_generators():
            node = root.children[key]
            for gen_key, gen in node.children.items():
                if gen_key != "ItemGenerator":
                    continue
                for slot_key, slot in gen.children.items():
                    if "#" in slot_key:
                        continue
                    items = slot.children.get("PossibleItems")
                    for item_key, item in (items.children.items()
                                           if items else ()):
                        if "#" in item_key:
                            continue
                        item_sid = (item.values.get("ItemPrototypeSID")
                                    or "").strip()
                        if item_sid and self._loot_item_is_skippable(item_sid):
                            continue
                        if ("MinCount" in item.values
                                or "MaxCount" in item.values
                                or "Chance" in item.values):
                            out.append((key, gen_key, slot_key, item_key, item))
        return out

    def trader_wallets(self) -> dict[str, tuple[float, bool]]:
        """Return {trader_SID: (Money, bInfiniteMoney)} for traders with a Money field."""
        result: dict[str, tuple[float, bool]] = {}
        for sid, node in self.trade.children.items():
            if sid == "[0]" or "#" in sid:
                continue
            raw = node.values.get("Money")
            if raw is None:
                continue
            infinite = (node.values.get("bInfiniteMoney")
                        or "").strip().lower() == "true"
            result[sid] = (parse_number(raw), infinite)
        return result

    def npcs_with_regen(self) -> dict[str, float]:
        """Return positive RegenHP values for human NPCs, excluding mutants and Player."""
        result: dict[str, float] = {}
        for sid in self.obj.children:
            if sid in ("[0]", "Player") or "#" in sid:
                continue
            chain = self._resolve_chain(self.obj, sid)
            faction = self._chain_get(chain, "Faction")
            if faction is None or faction in MUTANT_FACTIONS:
                continue
            regen = parse_number(self._chain_get(chain, "VitalParams.RegenHP"))
            if regen > 0:
                result[sid] = regen
        return result

    def player_weapon_wear(self) -> dict[str, float]:
        """Return {SID: DurabilityDamagePerShot} for all *_Player weapon settings."""
        return self._player_weapon_values("DurabilityDamagePerShot")

    def player_weapon_dispersion(self) -> dict[str, float]:
        """Return {SID: DispersionRadius} for all *_Player weapon settings."""
        return self._player_weapon_values("DispersionRadius")

    def _player_weapon_values(self, key: str) -> dict[str, float]:
        result: dict[str, float] = {}
        for sid in self.weaponsettings.children:
            if "_Player" not in sid or "#" in sid:
                continue
            value = self.resolve(self.weaponsettings, sid, key)
            if value is None:
                continue
            number = parse_number(value)
            if number > 0:
                result[sid] = number
        return result

    def weapon_category(self, sid: str) -> str | None:
        """Resolve a weapon category through its WeaponGeneralSetup refkey chain.

        None indicates a quest/special weapon affected only by global controls."""
        for node in self._resolve_chain(self.weapongeneral, sid):
            if node.name in WEAPON_CATEGORY_OVERRIDES:
                return WEAPON_CATEGORY_OVERRIDES[node.name]
            if node.name in WEAPON_CATEGORY_TEMPLATES:
                return WEAPON_CATEGORY_TEMPLATES[node.name]
        return None

    def player_weapons(self) -> dict[str, tuple[str | None, str | None]]:
        """Return {WGS_SID: (category, CWS_struct_SID)} for player weapons.

        Follow Item -> PlayerWeaponAttributes -> DefaultWeaponSettingsSID -> CWS.
        Do not infer CWS names: unique weapons may use *_Player_WS, and several
        weapons can share one CWS struct."""
        result: dict[str, tuple[str | None, str | None]] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "weapon":
                continue
            wgs = self.resolve(self.items, sid, "GeneralWeaponSetup")
            attrs = self.resolve(self.items, sid, "PlayerWeaponAttributes")
            if not wgs or wgs in result:
                continue
            cws = None
            if attrs:
                cws = self.resolve(self.weaponattributes, attrs,
                                   "DefaultWeaponSettingsSID") or attrs
            result[wgs] = (self.weapon_category(wgs), cws)
        # Include edition weapons; omit duplicate skins pointing to base-game setups.
        for wgs, (cat, cws, _ed) in self.dlc_player_weapons().items():
            if wgs not in result:
                result[wgs] = (cat, cws)
        return result

    # ------------------------------------------------------- DLC editions
    @cached_property
    def dlc_editions(self) -> dict[str, dict[str, CfgStruct]]:
        """Return installed DLCGameData trees as {edition: {items/weapongeneral: tree}}.

        Missing edition Paks or old caches yield no edition entries."""
        result: dict[str, dict[str, CfgStruct]] = {}
        base = self.dir.parent / "DLCGameData"
        if not base.is_dir():
            return result
        for ed_dir in sorted(base.iterdir()):
            if not ed_dir.is_dir():
                continue
            entry: dict[str, CfgStruct] = {}
            items = ed_dir / "ItemPrototypes.cfg"
            wgs = ed_dir / "WeaponData" / "WeaponGeneralSetupPrototypes.cfg"
            if items.is_file():
                entry["items"] = cfgparse.parse_file(items)
            if wgs.is_file():
                entry["weapongeneral"] = cfgparse.parse_file(wgs)
            if entry:
                result[ed_dir.name] = entry
        return result

    def dlc_weapon_chain(self, edition: str, sid: str) -> list[CfgStruct]:
        """Follow edition WGS inheritance, crossing refurl into base WeaponData
        and continuing through the base file's refkey chain."""
        tree = self.dlc_editions.get(edition, {}).get("weapongeneral")
        if tree is None:
            return self._resolve_chain(self.weapongeneral, sid)
        chain: list[CfgStruct] = []
        seen: set[str] = set()
        current: str | None = sid
        while current and current not in seen:
            seen.add(current)
            node = tree.children.get(current)
            if node is None:
                # Continue in the base file when the edition tree has no matching struct.
                return chain + self._resolve_chain(self.weapongeneral, current)
            chain.append(node)
            attrs = node.attr_dict()
            nxt = attrs.get("refkey")
            if nxt and "WeaponGeneralSetupPrototypes" in (
                    attrs.get("refurl") or ""):
                return chain + self._resolve_chain(self.weapongeneral, nxt)
            current = nxt
        return chain

    def dlc_weapon_category(self, edition: str, sid: str) -> str | None:
        for node in self.dlc_weapon_chain(edition, sid):
            if node.name in WEAPON_CATEGORY_OVERRIDES:
                return WEAPON_CATEGORY_OVERRIDES[node.name]
            if node.name in WEAPON_CATEGORY_TEMPLATES:
                return WEAPON_CATEGORY_TEMPLATES[node.name]
        return None

    def dlc_resolve_weapon(self, edition: str, sid: str,
                           path: str) -> str | None:
        return self._chain_get(self.dlc_weapon_chain(edition, sid), path)

    def dlc_player_weapons(self) -> dict[str, tuple[str | None, str | None, str]]:
        """Return {WGS_SID: (category, CWS_SID, edition)} for edition-specific setups.

        Exclude skins that reuse a base-game setup."""
        result: dict[str, tuple[str | None, str | None, str]] = {}
        for edition, trees in self.dlc_editions.items():
            items = trees.get("items")
            wgs_tree = trees.get("weapongeneral")
            for sid, node in (items.children.items() if items else ()):
                wgs = (node.values.get("GeneralWeaponSetup") or "").strip()
                if not wgs or wgs in result:
                    continue
                if wgs_tree is None or wgs not in wgs_tree.children:
                    continue
                attrs = (node.values.get("PlayerWeaponAttributes")
                         or "").strip()
                cws = None
                if attrs:
                    cws = self.resolve(self.weaponattributes, attrs,
                                       "DefaultWeaponSettingsSID") or attrs
                result[wgs] = (self.dlc_weapon_category(edition, wgs),
                               cws, edition)
        return result

    def dlc_weapon_editions(self) -> dict[str, str]:
        """Return {WGS_SID: edition} for routing patches and labeling edition setups."""
        return {wgs: ed
                for wgs, (_c, _w, ed) in self.dlc_player_weapons().items()}

    def dlc_item_chain(self, edition: str, sid: str) -> list[CfgStruct]:
        """Follow edition item inheritance across refurl into base ItemPrototypes."""
        tree = self.dlc_editions.get(edition, {}).get("items")
        if tree is None:
            return self._resolve_chain(self.items, sid)
        chain: list[CfgStruct] = []
        seen: set[str] = set()
        current: str | None = sid
        while current and current not in seen:
            seen.add(current)
            node = tree.children.get(current)
            if node is None:
                return chain + self._resolve_chain(self.items, current)
            chain.append(node)
            attrs = node.attr_dict()
            nxt = attrs.get("refkey")
            if nxt and "ItemPrototypes" in (attrs.get("refurl") or ""):
                return chain + self._resolve_chain(self.items, nxt)
            current = nxt
        return chain

    # Protection keys corresponding to ARMOR_PARAM_KEYS in tweaks.py.
    ARMOR_PROTECTION_KEYS = ("Strike", "Burn", "Shock", "ChemicalBurn",
                             "Radiation", "PSY")

    def dlc_player_armors(self) -> dict[str, tuple[str, dict[str, float], str]]:
        """Return {SID: (slot, protection_values, edition)} for edition armor.

        Identify it by the ArmorPrototypes refurl and resolve protection across files."""
        result: dict[str, tuple[str, dict[str, float], str]] = {}
        for edition, trees in self.dlc_editions.items():
            items = trees.get("items")
            for sid, node in (items.children.items() if items else ()):
                if sid in result:
                    continue
                refurl = node.attr_dict().get("refurl") or ""
                if "ArmorPrototypes" not in refurl:
                    continue
                chain = self.dlc_item_chain(edition, sid)
                invisible = (self._chain_get(chain, "Invisible") or "")
                if invisible.strip().rstrip(";").strip().lower() == "true":
                    continue
                values: dict[str, float] = {}
                for key in self.ARMOR_PROTECTION_KEYS:
                    value = parse_number(
                        self._chain_get(chain, f"Protection.{key}"))
                    if value > 0:
                        values[key] = value
                if not values:
                    continue
                slot = (self._chain_get(chain, "ItemSlotType") or "")
                slot = slot.split("::")[-1].strip() or "Body"
                result[sid] = (slot, values, edition)
        return result

    def dlc_armor_editions(self) -> dict[str, str]:
        return {sid: ed
                for sid, (_s, _v, ed) in self.dlc_player_armors().items()}

    def dlc_summary(self) -> str:
        """Describe installed edition content for the status line."""
        if not self.dlc_editions:
            return ""
        n_guns = len(self.dlc_player_weapons())
        n_armor = len(self.dlc_player_armors())
        names = {"PreOrder": "Pre-order"}
        eds = ", ".join(names.get(e, e) for e in sorted(self.dlc_editions))
        return (f"Edition content found ({eds}): {n_guns} guns, "
                f"{n_armor} armor pieces.")

    def dlc_weapon_general_values(self, path: str) -> dict[tuple[str, str], float]:
        """Return {(edition, SID): value} for explicit positive DLC WGS path values.

        Inherited values are already affected by their base patch."""
        result: dict[tuple[str, str], float] = {}
        for edition, trees in self.dlc_editions.items():
            tree = trees.get("weapongeneral")
            for sid, node in (tree.children.items() if tree else ()):
                if "#" in sid:
                    continue
                raw = node.get(path)
                if raw is None:
                    continue
                value = parse_number(raw)
                if value > 0:
                    result[(edition, sid)] = value
        return result

    @cached_property
    def upgrades(self) -> CfgStruct:
        return self._parse("UpgradePrototypes.cfg")

    def upgrade_sids_with(self, key: str) -> list[str]:
        """Return technician upgrade SIDs with nonempty prerequisite/blocking lists.

        Nonempty lists use indexed child structs; empty lists use the scalar 'Key ='.
        Emit that scalar to clear blocking branches, tiers or blueprint requirements."""
        out: list[str] = []
        for sid, node in self.upgrades.children.items():
            if "#" in sid or sid == "[0]":      # [0] is the base template for all upgrades.
                continue
            child = node.children.get(key)
            # Empty strings and 'empty' are placeholders.
            if child is not None and any(
                    v.strip() not in ("", "empty") for v in child.values.values()):
                out.append(sid)
        return out

    # ------------------------------------------------ A-Life: lairs and Director
    # Research and constraints: docs/ALIFE_SPAWN_RESEARCH.md.
    LAIR_RANKS = ("Newbie", "Experienced", "Veteran", "Master")
    LAIR_MUTANT_FACTIONS = frozenset({
        "Blinddog", "MoldyBlinddog", "Bloodsucker", "Boar", "Flesh", "Snork",
        "Pseudodog", "Tushkan", "Bayun", "Deer", "Rat", "Controller",
        "Poltergeist", "Chimera", "Burer", "Pseudogiant", "Zombie",
    })
    LAIR_TIMER_KEYS = ("InitialSpawnQuantityRespawnTimeSeconds",
                       "MaxSpawnQuantityRespawnTimeSeconds",
                       "WipeRespawnTimeoutSeconds")

    @cached_property
    def lairs(self) -> CfgStruct:
        return self._parse("LairPrototypes.cfg")

    @cached_property
    def director(self) -> CfgStruct:
        return self._parse("ALifePrototypes/ALifeDirectorScenarioPrototypes.cfg")

    def lair_blocks(self) -> list[dict]:
        """Yield camp entries by type, resident faction and rank.

        Include MaxSpawnQuantity, summed MinQuantityPerArchetype, raw respawn timers,
        and guard/mutant flags. Exclude the [0] template."""
        out: list[dict] = []
        for lair, node in self.lairs.children.items():
            if lair == "[0]" or "#" in lair:
                continue
            preset = node.children.get("Preset")
            pif = preset.children.get("PossibleInhabitantFactions") if preset else None
            if pif is None:
                continue
            for fkey, fac in pif.children.items():
                faction = (fac.values.get("Faction") or fkey).strip()
                ranks = fac.children.get("SpawnSettingsPerPlayerRanks")
                if ranks is None:
                    continue
                for rank in self.LAIR_RANKS:
                    blk = ranks.children.get(rank)
                    if blk is None:
                        continue
                    q = parse_number(blk.values.get("MaxSpawnQuantity"))
                    arch = blk.children.get("SpawnSettingsPerArchetypes")
                    min_sum = sum(
                        parse_number(a.values.get("MinQuantityPerArchetype"))
                        for a in (arch.children.values() if arch else ()))
                    out.append({
                        "lair": lair, "faction_key": fkey, "faction": faction,
                        "rank": rank, "quantity": q, "min_sum": min_sum,
                        "timers": tuple((blk.values.get(k) or "").strip()
                                        for k in self.LAIR_TIMER_KEYS),
                        "guard": lair.startswith("Guard"),
                        "mutant": faction in self.LAIR_MUTANT_FACTIONS,
                        # Initial camp fill and archetype weights. Archetype entries are named,
                        # so individual fields support partial bpatch updates.
                        "initial": (blk.values.get("InitialSpawnQuantityPercent") or "").strip(),
                        "archetypes": {k: (a.values.get("SpawnWeight") or "").strip()
                                       for k, a in (arch.children.items() if arch else ())},
                    })
        return out

    def lair_standard_timers(self) -> tuple[str, str, str]:
        """Find the most common respawn-timer triple for ordinary camps.

        Scale only matching camps; preserve story camps with immediate refill."""
        counts: dict[tuple[str, str, str], int] = {}
        for blk in self.lair_blocks():
            counts[blk["timers"]] = counts.get(blk["timers"], 0) + 1
        return max(counts, key=counts.get) if counts else ("", "", "")

    def director_preset(self) -> CfgStruct | None:
        return self.director.children.get("ALifeDirectorPreset")

    def director_scenario_tokens(self) -> dict[str, frozenset]:
        """Return {scenario_key: squad_tokens}.

        Normalize human prototypes to Human; mutants keep generic Mutant or their
        concrete prototype SID. A mutant-only scenario has no Human token."""
        d = self.director_preset()
        out: dict[str, frozenset] = {}
        if d is None:
            return out
        for key, sc in d.children.get("Scenarios", CfgStruct("x")).children.items():
            tokens = set()
            for sq in sc.children.get("ScenarioSquads", CfgStruct("x")).children.values():
                arch = (sq.values.get("AgentArchetype") or "").split("::")[-1].strip()
                proto = (sq.values.get("AgentPrototypeSID") or "").strip()
                if arch == "Human" or proto.startswith(("General", "Guard")):
                    tokens.add("Human")
                elif proto:
                    tokens.add(proto)
                elif arch:
                    tokens.add(arch)
            out[key] = frozenset(tokens)
        return out

    def director_prohibited(self) -> set[str]:
        d = self.director_preset()
        if d is None:
            return set()
        node = d.children.get("ProhibitedAgentTypes")
        return {v.split("::")[-1].strip() for v in (node.values.values() if node else ())}

    def director_limits(self) -> list[tuple[str, str, str, float]]:
        """Yield (rank_index, type_index, agent_type, MaxCount) from rank limits."""
        d = self.director_preset()
        out: list[tuple[str, str, str, float]] = []
        if d is None:
            return out
        lim = d.children.get("ALifeScenarioNPCArchetypesLimitsPerPlayerRank")
        for ri, rank in (lim.children.items() if lim else ()):
            for ti, entry in rank.children.get("Restrictions", CfgStruct("x")).children.items():
                atype = (entry.values.get("AgentType") or "").split("::")[-1].strip()
                out.append((ri, ti, atype, parse_number(entry.values.get("MaxCount"))))
        return out

    def consumable_duration_effects(self, min_seconds: float = 10.0) -> dict[str, str]:
        """Return raw durations of beneficial consumable effects lasting min_seconds.

        Exclude instant healing/bleeding/radiation effects and EBeneficial::Negative
        penalties from this duration control."""
        out: dict[str, str] = {}
        for sid, node in self.items.children.items():
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "consumable":
                continue
            refs = node.children.get("EffectPrototypeSIDs")
            for ref in (refs.values.values() if refs else ()):
                eff = ref.strip()
                enode = self.effects.children.get(eff)
                if enode is None or eff in out:
                    continue
                # Negative effects: intoxication, stamina hangover and Hercules aftereffects.
                # Remain vanilla, as with the consumable-strength slider.
                if (enode.values.get("Positive") or "").strip().endswith("Negative"):
                    continue
                raw = enode.values.get("Duration")
                if raw is not None and parse_number(raw) >= min_seconds:
                    out[eff] = raw
        return out

    def quest_items_with_weight(self) -> dict[str, float]:
        """Return positive weights of items carrying either resolved quest marker.

        Quest items lack ordinary weight categories and use a separate control."""
        out: dict[str, float] = {}
        for sid in self._quest_item_sids:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            w = parse_number(self.resolve(self.items, sid, "Weight"))
            if w > 0:
                out[sid] = w
        return out

    @cached_property
    def threats(self) -> CfgStruct:
        return self._parse("AIPrototypes/ThreatPrototypes.cfg")

    def human_npc_sids(self) -> list[str]:
        """Return human NPC prototypes, excluding mutant factions, Player and [0]."""
        out: list[str] = []
        for sid in self.obj.children:
            if sid in ("[0]", "Player") or "#" in sid:
                continue
            faction = self.resolve(self.obj, sid, "Faction")
            if faction is None or faction in MUTANT_FACTIONS:
                continue
            out.append(sid)
        return out

    def magazine_items(self) -> dict[str, float]:
        """Return positive Magazine.MaxAmmo values for concrete magazine attachments.

        Exclude templates and [0]."""
        result: dict[str, float] = {}
        for sid, node in self.items.children.items():
            if "#" in sid or sid.startswith("Template") or sid == "[0]":
                continue
            mag = node.children.get("Magazine")
            if mag is None:
                continue
            value = parse_number(mag.values.get("MaxAmmo"))
            if value > 0:
                result[sid] = value
        return result

    def weapon_magazines(self) -> dict[str, list[str]]:
        """Return {WGS_SID: [magazine_item_SIDs]} from reload attachment entries.

        Resolve WeaponReloadTimePerAttachment through base or edition inheritance
        and retain real magazine_items. A magazine can be shared by several weapons."""
        mags = self.magazine_items()

        def from_chain(chain) -> list[str]:
            for node in chain:
                block = node.children.get("WeaponReloadTimePerAttachment")
                if block is None:
                    continue
                found = []
                for entry in block.children.values():
                    sid = (entry.values.get("AttachPrototypeSID") or "").strip()
                    if sid in mags and sid not in found:
                        found.append(sid)
                return found
            return []

        result: dict[str, list[str]] = {}
        for sid in self.weapongeneral.children:
            if "#" in sid or sid.startswith("Template"):
                continue
            found = from_chain(self._resolve_chain(self.weapongeneral, sid))
            if found:
                result[sid] = found
        for edition, trees in self.dlc_editions.items():
            tree = trees.get("weapongeneral")
            for sid in (tree.children if tree else ()):
                if "#" in sid or sid in result:
                    continue
                found = from_chain(self.dlc_weapon_chain(edition, sid))
                if found:
                    result[sid] = found
        return result

    def weapon_general_values(self, path: str,
                              signed: bool = False) -> dict[str, float]:
        """Return explicit WeaponGeneralSetup values at a possibly nested path.

        Inherited values scale through the parent patch. By default require values
        above zero; signed=True also includes zero and negative aim/crouch modifiers."""
        result: dict[str, float] = {}
        for sid, node in self.weapongeneral.children.items():
            if "#" in sid:
                continue
            raw = node.get(path)
            if raw is None:
                continue
            number = parse_number(raw)
            if signed or number > 0:
                result[sid] = number
        return result

    # AmmoCaliber and AmmoTypeProjectiles define caliber and allowed projectiles
    # in the same setup struct as MaxAmmo. Every checked weapon declares both;
    # patches must target that setup rather than infer caliber from item names.

    def weapon_caliber(self, sid: str, edition: str | None = None) -> str | None:
        """Return weapon caliber without the EAmmoCaliber:: prefix, e.g. A545."""
        raw = (self.dlc_resolve_weapon(edition, sid, "AmmoCaliber")
               if edition is not None
               else self.resolve(self.weapongeneral, sid, "AmmoCaliber"))
        if not raw:
            return None
        name = str(raw).split("::")[-1].strip()
        return None if name in ("", "None") else name

    def weapon_ammo_slots(self, sid: str,
                          edition: str | None = None) -> dict[str, str]:
        """Return {array_index: ammo_type} for one weapon.

        Indices do not imply ammo type: some rifles use Supersonic at [0].
        Always read the type at each index."""
        chain = (self.dlc_weapon_chain(edition, sid) if edition is not None
                 else self._resolve_chain(self.weapongeneral, sid))
        for node in chain:
            block = node.children.get("AmmoTypeProjectiles")
            if block is None:
                continue
            slots: dict[str, str] = {}
            for index, entry in block.children.items():
                kind = entry.values.get("AmmoType")
                if kind:
                    slots[index] = str(kind).split("::")[-1].strip()
            if slots:
                return slots
        return {}

    def ammo_caliber_projectiles(self) -> dict[str, dict[str, str]]:
        """Return {caliber: {ammo_type: projectile_SID}} from weapon data.

        Buckshot and shotgun slugs use different projectiles. Exclude calibers unused
        by any weapon, even if an ammunition item exists."""
        result: dict[str, dict[str, str]] = {}
        trees = [self.weapongeneral] + [
            entry["weapongeneral"] for entry in self.dlc_editions.values()
            if entry.get("weapongeneral") is not None]
        for tree in trees:
            for sid, node in tree.children.items():
                if "#" in sid:
                    continue
                raw = node.values.get("AmmoCaliber")
                if not raw:
                    continue
                caliber = str(raw).split("::")[-1].strip()
                if caliber in ("", "None"):
                    continue
                block = node.children.get("AmmoTypeProjectiles")
                if block is None:
                    continue
                table = result.setdefault(caliber, {})
                for entry in block.children.values():
                    kind = entry.values.get("AmmoType")
                    shot = entry.values.get("ProjectilePrototypeSID")
                    if kind and shot:
                        table.setdefault(str(kind).split("::")[-1].strip(),
                                         str(shot).strip())
        return {c: t for c, t in result.items() if t}

    def caliber_damage_mods(self) -> dict[str, float]:
        """Return each caliber's default ammunition DamageMod.

        BaseDamage belongs to CharacterWeaponSettings; ammunition supplies a
        multiplier. Shotgun pellet multipliers differ substantially from rifle/pistol
        rounds, so caliber conversion needs this value for its damage estimate."""
        result: dict[str, float] = {}
        for node in self.items.children.values():
            if node.values.get("AmmoType") != "EAmmoType::Default":
                continue
            raw = node.values.get("Caliber")
            mod = node.values.get("DamageMod")
            if not raw or mod is None:
                continue
            caliber = str(raw).split("::")[-1].strip()
            number = parse_number(mod)
            if caliber and number > 0:
                result.setdefault(caliber, number)
        return result

    def weapon_caliber_users(self, sid: str) -> int:
        """Count item prototypes sharing a WeaponGeneralSetup.

        Caliber changes affect every linked player, NPC and boss weapon."""
        count = 0
        for node in self.items.children.values():
            if node.values.get("GeneralWeaponSetup") == sid:
                count += 1
        return count

    TRADE_KEYS = (
        "WeaponSellMinDurability", "ArmorSellMinDurability",
        "BuyModifier", "SellModifier",
    )

    def traders(self) -> dict[str, dict[str, dict[str, float]]]:
        """Return {trader_SID: {generator_index: {key: vanilla_value}}}.

        Include only explicitly declared TRADE_KEYS."""
        result: dict[str, dict[str, dict[str, float]]] = {}
        for sid, node in self.trade.children.items():
            if sid == "[0]" or "#" in sid:
                continue
            gens = node.children.get("TradeGenerators")
            if gens is None:
                continue
            entries: dict[str, dict[str, float]] = {}
            for idx, gen in gens.children.items():
                found = {
                    key: parse_number(gen.values[key])
                    for key in self.TRADE_KEYS
                    if key in gen.values
                }
                if found:
                    entries[idx] = found
            if entries:
                result[sid] = entries
        return result

    # MaxStackCount is editable per ammunition type alongside its modifiers
    # (issue #7).
    AMMO_MOD_KEYS = ("DamageMod", "ArmorPiercingMod", "ArmorDamageMod",
                     "CoverPiercingMod", "MaxStackCount",
                     # Each checked ammunition type declares these additional modifiers.
                     "BleedingMod", "RecoilMod", "FlatnessMod",
                     "WeaponExhaustionMod",
                     # These modifiers were identified in community mods and verified in game data.
                     "DispersionMod", "AimDispersionMod")

    def ammo_mods(self) -> dict[str, dict[str, float]]:
        """Return {SID: {ModKey: resolved vanilla value}} for all ammunition items."""
        result: dict[str, dict[str, float]] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "ammo":
                continue
            mods = {}
            for key in self.AMMO_MOD_KEYS:
                raw = self.resolve(self.items, sid, key)
                if raw is not None:
                    mods[key] = parse_number(raw)
            if mods:
                result[sid] = mods
        return result

    def stack_counts(self, category: str) -> dict[str, int]:
        """Return vanilla MaxStackCount for one item category.

        Exclude values <= 1, which identify intentionally nonstackable items."""
        result: dict[str, int] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != category:
                continue
            raw = self.resolve(self.items, sid, "MaxStackCount")
            if raw is None:
                continue
            value = int(parse_number(raw))
            if value > 1:
                result[sid] = value
        return result

    def ammo_kinds(self) -> dict[str, tuple[str, str]]:
        """Return {SID: (caliber, ammo_type)} using enums without their prefixes.

        Missing fields become empty strings. Derive the set from ammo_mods() so
        the UI cannot offer ammunition unsupported by the item patch builder."""
        result: dict[str, tuple[str, str]] = {}
        for sid in self.ammo_mods():
            cal = self.resolve(self.items, sid, "Caliber") or ""
            typ = self.resolve(self.items, sid, "AmmoType") or ""
            result[sid] = (cal.split("::")[-1].strip(),
                           typ.split("::")[-1].strip())
        return result

    ARMOR_PROTECTION_KEYS = ("Strike", "Burn", "Shock", "ChemicalBurn",
                             "Radiation", "PSY")

    def armor_protection(self) -> dict[str, dict[str, float]]:
        """Return positive player Protection values for armor and helmets.

        ProtectionNPC is outside this control."""
        result: dict[str, dict[str, float]] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "armor":
                continue
            values = {}
            for key in self.ARMOR_PROTECTION_KEYS:
                value = parse_number(self.resolve(self.items, sid, f"Protection.{key}"))
                if value > 0:
                    values[key] = value
            if values:
                result[sid] = values
        return result

    def player_armors(self) -> dict[str, tuple[str, dict[str, float]]]:
        """Return {SID: (slot, player_protection)} for obtainable armor and helmets.

        Exclude Invisible NPC-only items from the per-item editor. Global protection
        scaling still uses armor_protection(). Resolve slot as Body or Head."""
        result: dict[str, tuple[str, dict[str, float]]] = {}
        for sid, values in self.armor_protection().items():
            invisible = (self.resolve(self.items, sid, "Invisible") or "")
            if invisible.strip().rstrip(";").strip().lower() == "true":
                continue
            slot = (self.resolve(self.items, sid, "ItemSlotType") or "")
            slot = slot.split("::")[-1].strip() or "Body"
            result[sid] = (slot, values)
        # Include edition armors such as SEVA Monolith.
        for sid, (slot, values, _ed) in self.dlc_player_armors().items():
            if sid not in result:
                result[sid] = (slot, values)
        return result

    DETECTOR_RANGE_KEYS = ("ShowArtifactRadius", "MinDetectRadius",
                           "DetectorWorkRadius", "SonarRadius",
                           "AnomalyDetectionRadius")

    def detector_items(self) -> dict[str, dict[str, float]]:
        """Return artifact detector radii as {SID: {radius_key: value}}."""
        result: dict[str, dict[str, float]] = {}
        for sid in self.items.children:
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.template_of(sid) != "TemplateDetector":
                continue
            radii = {}
            for key in self.DETECTOR_RANGE_KEYS:
                value = parse_number(self.resolve(self.items, sid, key))
                if value > 0:
                    radii[key] = value
            if radii:
                result[sid] = radii
        return result

    def effect_percent(self, sid: str) -> float:
        """Parse an effect's ValueMin percentage, e.g. '-15%' becomes -15."""
        node = self.effects.children.get(sid)
        if node is None:
            return 0.0
        raw = (node.get("ValueMin") or "0").strip().rstrip("%")
        return parse_number(raw)

    def gear_durability(self) -> dict[str, tuple[str, float]]:
        """Return {SID: (category, vanilla_BaseDurability)} for weapons and armor."""
        result: dict[str, tuple[str, float]] = {}
        for sid, node in self.items.children.items():
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            cat = self.item_category(sid)
            if cat not in ("weapon", "armor"):
                continue
            dur = self.resolve(self.items, sid, "BaseDurability")
            if dur is None:
                continue
            value = parse_number(dur)
            if value <= 1.0:  # 1.0 is the base struct's placeholder durability.
                continue
            result[sid] = (cat, value)
        return result

    def item_weights(self) -> dict[str, tuple[str, float]]:
        """Return {SID: (category, vanilla_Weight)} for items with positive weight."""
        result: dict[str, tuple[str, float]] = {}
        for sid, node in self.items.children.items():
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            cat = self.item_category(sid)
            if cat is None:
                continue
            w = self.resolve(self.items, sid, "Weight")
            if w is None:
                continue
            value = parse_number(w)
            if value <= 0:
                continue
            result[sid] = (cat, value)
        return result

    def difficulty_values(self, key_path: str) -> dict[str, float]:
        """Resolve a difficulty path through refkey inheritance for each difficulty SID."""
        result: dict[str, float] = {}
        for sid in self.difficulty.children:
            if sid == "[0]" or "#" in sid:
                continue
            value = self.resolve(self.difficulty, sid, key_path)
            if value is not None:
                result[sid] = parse_number(value)
        return result

    def player(self) -> CfgStruct | None:
        return self.obj.children.get("Player")

    def weight_params(self) -> CfgStruct | None:
        return self.weightparams.children.get("DefaultWeightParams")

    def corevar(self, key: str, default: float = 0.0) -> float:
        node = self.corevars.children.get("DefaultConfig")
        if node is None:
            return default
        return parse_number(node.get(key), default)

    # ------------------------------------------------------ Emission duration
    def emission_default_timeline(self):
        """Return (struct_key, Stages, AIEvents) for the recurring DEFAULT emission.

        Exclude story emissions. The patch key is its array index, not its SID."""
        for key, node in self.emissions.children.items():
            if (node.values.get("SID") or "").strip() == "Default":
                return (key, node.children.get("Stages"),
                        node.children.get("AIEvents"))
        return (None, None, None)

    # ------------------------------------------- Repeatable quest timers
    def repeatable_quest_timers(self) -> dict[str, float]:
        """Return InGameHours for RSQ SetTimer nodes, excluding story/side quests.

        This requires parsing the large quest file; call lazily."""
        result: dict[str, float] = {}
        for sid, node in self.questnodes.children.items():
            if "#" in sid:
                continue
            if not (node.values.get("QuestSID") or "").strip().startswith("RSQ"):
                continue
            ntype = (node.values.get("NodeType") or "").strip()
            if ntype != "EQuestNodeType::SetTimer":
                continue
            hours = node.values.get("InGameHours")
            if hours is None:
                continue
            value = parse_number(hours)
            if value > 0:
                result[sid] = value
        return result

    def ammo_pack_counts(self) -> dict[str, float]:
        """Return AmmoPackCount for ammunition packs.

        Exclude counts <= 1, including templates and individually collected launcher rounds."""
        result: dict[str, float] = {}
        for sid, node in self.items.children.items():
            if sid == "[0]" or "#" in sid or sid.startswith("Template"):
                continue
            if self.item_category(sid) != "ammo":
                continue
            raw = self.resolve(self.items, sid, "AmmoPackCount")
            if raw is None:
                continue
            value = parse_number(raw)
            if value > 1:
                result[sid] = value
        return result

    # --------------------------------------- Mutant attack details
    def mutant_attack_params(self, keys: tuple[str, ...]) -> dict[str, dict[str, str]]:
        """Return {ability_SID: {path: raw_literal}} for selected mutant attack keys.

        Use SPECIES_ABILITY_PREFIXES to exclude human, boss and template abilities
        sharing those keys. Preserve raw literals for the patch builder."""
        result: dict[str, dict[str, str]] = {}
        prefixes = tuple(p for lst in SPECIES_ABILITY_PREFIXES.values() for p in lst)
        for sid, node in self.abilities.children.items():
            if "#" in sid or not sid.startswith(prefixes):
                continue
            found: dict[str, str] = {}

            def walk(current, path: str) -> None:
                for key, raw in current.values.items():
                    if key in keys:
                        found[f"{path}{key}" if path else key] = raw.strip()
                for name, child in current.children.items():
                    walk(child, f"{path}{name}.")

            walk(node, "")
            if found:
                result[sid] = found
        return result

    # ------------------------------------ Repeatable jobs: limit per giver
    def repeatable_quest_givers(self) -> list[dict]:
        """Discover repeatable-job givers and their pool limits/dialogue links.

        A per-giver variable increments on acceptance and resets with the cooldown;
        its Less limit counts jobs per round, not currently held jobs. In vanilla,
        the dialogue rearms from the limit check's False output.

        Discover the Add/Less relationship within each quest rather than relying
        on node names. Return cap and connection paths, pool size and relevant nodes.
        Parsing the large quest file is deferred until needed."""
        groups: dict[str, list[tuple[str, CfgStruct]]] = {}
        for key, node in self.questnodes.children.items():
            quest = (node.values.get("QuestSID") or "").strip()
            match = _RSQ_GROUP_RE.match(quest)
            if match:
                groups.setdefault(match.group(1), []).append((key, node))

        givers: list[dict] = []
        for group, nodes in sorted(groups.items()):
            counters = {
                (n.values.get("GlobalVariablePrototypeSID") or "").strip()
                for _k, n in nodes
                if (n.values.get("NodeType") or "").strip()
                == "EQuestNodeType::SetGlobalVariable"
                and (n.values.get("ChangeValueMode") or "").strip()
                == "EChangeValueMode::Add"
            }
            counters.discard("")
            if not counters:
                continue

            cap = None
            for key, node in nodes:
                if (node.values.get("NodeType") or "").strip() != "EQuestNodeType::If":
                    continue
                hit = _less_condition(node, counters)
                if hit is not None:
                    cap = (key, node, hit[0], hit[1])
                    break
            if cap is None:
                continue
            cap_key, cap_node, cond_path, cap_value = cap
            cap_sid = (cap_node.values.get("SID") or "").strip() or cap_key

            pool = sum(
                1 for _k, n in nodes
                if (n.values.get("NodeType") or "").strip()
                == "EQuestNodeType::Container"
            )

            dialog = None
            for key, node in nodes:
                if (node.values.get("NodeType") or "").strip() != "EQuestNodeType::SetDialog":
                    continue
                link = _launcher_link(node, cap_sid)
                if link is not None:
                    dialog = (key, node, link[0], link[1])
                    break
            if dialog is None:
                continue
            dialog_key, dialog_node, link_path, pin = dialog

            # Find the acceptance Technical node by its link to the dialogue's
            # confirm output, rather than a fixed Technical_GetQuest name.
            dialog_sid = (dialog_node.values.get("SID") or "").strip() or dialog_key
            quest_sid = (dialog_node.values.get("QuestSID") or "").strip()
            accept = None
            for key, node in nodes:
                if (node.values.get("NodeType") or "").strip() != "EQuestNodeType::Technical":
                    continue
                launchers = node.children.get("Launchers")
                for lnode in (launchers.children.values() if launchers else ()):
                    conns = lnode.children.get("Connections")
                    for cnode in (conns.children.values() if conns else ()):
                        if ((cnode.values.get("SID") or "").strip() == dialog_sid
                                and "confirm" in (cnode.values.get("Name") or "").lower()):
                            accept = (node.values.get("SID") or "").strip() or key
                            break
                    if accept:
                        break
                if accept:
                    break

            # Allocate a free launcher index without replacing existing dialogue links.
            dlg_launchers = dialog_node.children.get("Launchers")
            used = []
            for lkey in (dlg_launchers.children if dlg_launchers else {}):
                match_idx = re.match(r"^\[(\d+)\]$", lkey)
                if match_idx:
                    used.append(int(match_idx.group(1)))
            next_launcher = (max(used) + 1) if used else 0

            # Find the round's BridgeCleanUp and linked End node by graph structure.
            # End's ExcludeAllNodesInContainer can terminate sibling jobs on hand-in.
            cleanup_sid = end_sid = end_exclude = None
            for key, node in nodes:
                if (node.values.get("NodeType") or "").strip() == "EQuestNodeType::BridgeCleanUp":
                    cleanup_sid = (node.values.get("SID") or "").strip() or key
                    break
            if cleanup_sid:
                for key, node in nodes:
                    if (node.values.get("NodeType") or "").strip() != "EQuestNodeType::End":
                        continue
                    if _launcher_link(node, cleanup_sid) is None:
                        continue
                    end_sid = (node.values.get("SID") or "").strip() or key
                    end_exclude = (node.values.get(
                        "ExcludeAllNodesInContainer") or "").strip()
                    break

            givers.append({
                "quest": group,
                "quest_sid": quest_sid,
                "cleanup_sid": cleanup_sid,
                "end_sid": end_sid,
                "end_exclude": end_exclude,
                "cap_key": cap_key,
                "cap_node": cap_node,
                "cap": cap_value,
                "cond_path": cond_path,
                "pool": pool,
                "dialog_key": dialog_key,
                "dialog_node": dialog_node,
                "dialog_sid": dialog_sid,
                "link_path": link_path,
                "pin": pin,
                "accept": accept,
                "next_launcher": next_launcher,
            })
        return givers

    def repeatable_job_slots(self, quest_sid: str) -> list[dict]:
        """Discover one giver's job containers as [{container, add, pin}].

        Require a launcher with both pool-add Technical and acceptance Condition
        connections. Both must complete to start the job. Parse quest nodes lazily."""
        nodes = self.questnodes.children
        slots: list[dict] = []
        for key, node in nodes.items():
            if (node.values.get("QuestSID") or "").strip() != quest_sid:
                continue
            if (node.values.get("NodeType") or "").strip() != "EQuestNodeType::Container":
                continue
            launchers = node.children.get("Launchers")
            if launchers is None:
                continue
            for entry in launchers.children.values():
                conns = entry.children.get("Connections")
                if conns is None:
                    continue
                sources = [(c.values.get("SID") or "").strip()
                           for c in conns.children.values()]
                if len(sources) != 2:
                    continue
                kinds = {}
                for src in sources:
                    ref = nodes.get(src)
                    kinds[src] = (ref.values.get("NodeType") or "").strip() if ref is not None else ""
                adds = [x for x, k in kinds.items() if k == "EQuestNodeType::Technical"]
                pins = [x for x, k in kinds.items() if k == "EQuestNodeType::Condition"]
                if len(adds) == 1 and len(pins) == 1:
                    slots.append({"container": (node.values.get("SID") or "").strip() or key,
                                  "add": adds[0], "pin": pins[0]})
        slots.sort(key=lambda d: d["container"])
        return slots

    def job_menu_switch(self, chain_sid: str, accept_sid: str):
        """Return (If_node, menu_target, cancel_target) for a job dialogue gate, or None.

        Identify the initial NotEqual bridge condition on quest acceptance, rather
        than its varying node name. A retained acceptance result routes reopened
        dialogues to cancellation. Parse DialogPrototypes lazily."""
        def _mentions(node, sid: str) -> bool:
            for value in node.values.values():
                if (value or "").strip() == sid:
                    return True
            return any(_mentions(child, sid) for child in node.children.values())

        for key, node in self.dialogs.children.items():
            if (node.values.get("DialogChainPrototypeSID") or "").strip() != chain_sid:
                continue
            options = node.children.get("NextDialogOptions")
            if options is None:
                continue
            true = options.children.get("True")
            false = options.children.get("False")
            if true is None or false is None:
                continue
            conditions = true.children.get("Conditions")
            if conditions is None or not _mentions(conditions, accept_sid):
                continue
            if not _mentions(conditions, "EConditionComparance::NotEqual"):
                continue
            return ((node.values.get("SID") or "").strip() or key,
                    (true.values.get("NextDialogSID") or "").strip(),
                    (false.values.get("NextDialogSID") or "").strip())
        return None

    # ------------------------------------------------- Faction relationships
    # Research: docs/FACTION_RELATIONS_RESEARCH.md (582 pairs, 2.0.x snapshot).

    def _relations_default(self) -> CfgStruct | None:
        return self.relations.children.get("Default")

    def relation_pairs(self) -> dict[str, int]:
        """Return existing faction-pair keys and their vanilla relation values.

        Preserve the exact pair order; creation of new pairs is untested."""
        d = self._relations_default()
        if d is None:
            return {}
        rel = d.children.get("Relations")
        if rel is None:
            return {}
        result: dict[str, int] = {}
        for key, raw in rel.values.items():
            try:
                result[key] = int(round(parse_number(raw)))
            except (TypeError, ValueError):
                continue
        return result

    def relation_pair_key(self, a: str, b: str) -> str | None:
        """Find the existing key for pair (a, b), accepting either input order.

        Game data stores only one direction for each pair."""
        pairs = self.relation_pairs()
        for key in (f"{a}<->{b}", f"{b}<->{a}"):
            if key in pairs:
                return key
        return None

    def relation_version(self) -> int:
        """Read RelationVersion for diagnostics and mod scanning; never increment it.

        The version counter belongs to GSC's RelationUpdateDeltas migration scheme.
        A counter bump without a matching delta is not a verified save migration.
        The optional relations_runtime patch is the separate runtime mechanism."""
        d = self._relations_default()
        if d is None:
            return 0
        return int(round(parse_number(d.values.get("RelationVersion"), 0)))

    def relation_reaction_tables(self):
        """Yield (table, index, node) from local CharacterReactions and global
        FactionReactions, skipping entries without values."""
        d = self._relations_default()
        out = []
        for table in ("CharacterReactions", "FactionReactions"):
            node = d.children.get(table) if d is not None else None
            for idx, entry in (node.children.items() if node else ()):
                out.append((table, idx, entry))
        return out

    def faction_rollback_cooldowns(self) -> dict[str, float]:
        """Return faction cooldowns in seconds from FactionRollbackCooldowns."""
        d = self._relations_default()
        if d is None:
            return {}
        node = d.children.get("FactionRollbackCooldowns")
        if node is None:
            return {}
        return {fac: parse_number(raw) for fac, raw in node.values.items()}
