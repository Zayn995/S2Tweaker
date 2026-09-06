"""Vanilla-GameData beschaffen und auswerten.

Pipeline beim ersten Start (bzw. nach Spiel-Update):
  1. repak unpack pakchunk0-Windows.pak  (nur GameData-Dateien, Auswahl unten)
  2. *.cfg.bin -> *.cfg konvertieren (vendor_bin2cfg)
  3. Ergebnis im Cache-Ordner ablegen (%LOCALAPPDATA%/S2Tweaker/vanilla-<size>)

Danach werden die cfg-Texte geparst und Vererbung (refkey) aufgeloest, damit
Multiplikator-Tweaks (Haltbarkeit x3, Mutanten-HP x2, ...) auf den echten
Vanilla-Werten der installierten Spielversion rechnen.
"""

from __future__ import annotations

import os
import re
import shutil
from functools import cached_property
from pathlib import Path

from . import cfgparse, pakio, vendor_bin2cfg
from .cfgparse import CfgStruct, parse_number

# Nur diese Dateien braucht das Tool (spart Zeit beim Entpacken/Konvertieren)
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
    "FlashlightPrototypes.cfg.bin",          # NPC-Taschenlampen (05.09.2026)
    "SaveLoadVariables.cfg",                 # Speicherstaende-Limit (unbinarisiert)
    "AutoSaveVariables.cfg",                 # Autosave-Intervall (unbinarisiert)
    "AimAssistPresetPrototypes.cfg.bin",     # Aim-Assist Maus/Gamepad (06.09.2026)
]

# Bei Aenderungen an NEEDED_FILES erhoehen -> alte Caches werden neu aufgebaut
CACHE_SCHEMA = 18

# Mutanten-Art (Fraktion) -> Praefixe der Attacken-Structs in
# AbilityPrototypes.cfg (verifiziert; docs/V15_DATA_RESEARCH.md).
# Rat, Poltergeist und "Mutant" haben keine Damage-Attacken.
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

# --- DLC-Editionen (Nexus-Wunsch zDusty 02.09.): die Editions-Waffen
# (Gabion, Veteran, Monolith-Set ...) liegen in EIGENEN Paks und einem
# eigenen DLCGameData-Zweig. Fehlende Paks sind KEIN Fehler — das Tool
# laeuft dann einfach ohne DLC-Waffen weiter.
DLCGAMEDATA_REL = "Stalker2/Content/GameLite/DLCGameData"
DLC_SOURCES = {
    "PreOrder": "pakchunk101-Windows.pak",
    "Deluxe": "pakchunk102-Windows.pak",
    "Ultimate": "pakchunk104-Windows.pak",
}
DLC_FILES = ("ItemPrototypes.cfg.bin",
             "WeaponData/WeaponGeneralSetupPrototypes.cfg.bin")


def _cfg_name(needed: str) -> str:
    """NEEDED_FILES-Eintrag -> Name der lesbaren cfg nach der Konvertierung."""
    return needed[: -len(".bin")] if needed.endswith(".cfg.bin") else needed

# Kreatur-Fraktionen = Mutanten (Zombie-Stalker zaehlen als Menschen)
MUTANT_FACTIONS = {
    "Bayun", "Blinddog", "Bloodsucker", "Boar", "Burer", "Chimera",
    "Controller", "Deer", "Flesh", "MoldyBlinddog", "Mutant", "Poltergeist",
    "Pseudodog", "Pseudogiant", "Rat", "Snork", "Tushkan",
}

WEAPON_TEMPLATES = {"TemplateWeapon"}
ARMOR_TEMPLATES = {"TemplateArmor"}

# Kategorie-Templates in WeaponGeneralSetupPrototypes.cfg: jede Waffe erbt
# per refkey (ggf. ueber Unikat-Zwischenstufen) von genau einem davon.
WEAPON_CATEGORY_TEMPLATES = {
    "TemplatePistol": "pistol",
    "TemplateMAC": "smg",           # Maschinenpistolen -> SMG-Kategorie
    "TemplateSMG": "smg",
    "TemplateRifle": "rifle",
    "TemplateRifleSingleFire": "rifle",
    "TemplateShotgun": "shotgun",
    "TemplateDMR": "dmr",
    "TemplateSniper": "sniper",
    "TemplateMG": "mg",
    "TemplateGLaunch": "launcher",
}

# Ausreisser in den Spieldaten: der RPG-7 erbt kurioserweise von
# TemplateSniper — fuer die Regler zaehlt er als Granatwerfer.
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


class GameData:
    def __init__(self, gamedata_dir: Path):
        """gamedata_dir: Ordner, der die cfg-TEXT-Dateien enthaelt
        (.../Stalker2/Content/GameLite/GameData)."""
        self.dir = Path(gamedata_dir)

    # ---------------------------------------------------------------- setup
    @classmethod
    def from_game(cls, game_dir: Path, cache_root: Path | None = None,
                  progress=None) -> "GameData":
        """Vanilla-Daten aus der Spielinstallation extrahieren (mit Cache)."""
        pak = Path(game_dir) / "Stalker2/Content/Paks/pakchunk0-Windows.pak"
        cache_root = cache_root or default_cache_dir()

        if not pak.is_file():
            # Steam aktualisiert gerade das Spiel o.ae. -> letzten Cache nutzen
            # (nur Caches des AKTUELLEN Schemas: aeltere haben nicht alle
            # NEEDED_FILES und wuerden beim Bauen crashen)
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

        # Pak-Groesse als billiger Versions-Fingerabdruck
        tag = f"vanilla-{pak.stat().st_size}-s{CACHE_SCHEMA}"
        cache = cache_root / tag
        gd = cache / GAMEDATA_REL
        marker = cache / ".complete"

        if not marker.is_file():
            cache.mkdir(parents=True, exist_ok=True)
            if progress:
                progress("Extracting game data from pakchunk0 ...")
            for name in NEEDED_FILES:
                pakio.unpack(pak, cache, include=f"{GAMEDATA_REL}/{name}",
                             progress=progress)
            # DLC-Editionen (optional): eigene Paks, eigener cfg-Zweig.
            # Bewusst fehlertolerant — ohne Editions-Pak gibt es einfach
            # keine DLC-Waffen im Baum, alles andere laeuft normal.
            for edition, pakname in DLC_SOURCES.items():
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
                    roots = vendor_bin2cfg.read_binary_cfg(bin_path.read_bytes())
                    out.write_text(
                        "\n".join(r.to_string() for r in roots), encoding="utf-8"
                    )
            # Erst pruefen, dann als fertig markieren: repak meldet Erfolg
            # auch, wenn ein Include-Muster auf nichts passt. Ohne diesen
            # Check bliebe ein unvollstaendiger Cache dauerhaft liegen und
            # der Fehler taeuchte erst beim Bauen als Traceback auf.
            missing = [name for name in NEEDED_FILES
                       if not (gd / _cfg_name(name)).is_file()]
            if missing:
                raise FileNotFoundError(
                    "These game files could not be extracted:\n  "
                    + "\n  ".join(missing)
                    + "\n\nYour game version may have moved or renamed them. "
                      "Please report this together with your game version.")
            marker.write_text("ok", encoding="utf-8")
            # Caches frueherer Schema-Versionen sind nie wieder nutzbar und
            # liegen sonst dauerhaft neben der EXE (~90 MB je Generation).
            for old in cache_root.glob("vanilla-*"):
                if old.is_dir() and not old.name.endswith(f"-s{CACHE_SCHEMA}"):
                    shutil.rmtree(old, ignore_errors=True)
        return cls(gd)

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
        """ACHTUNG: 75-MB-Datei, ~84.000 Structs, Parse ~3 s. NUR lazy
        anfassen — d.h. erst, wenn der Quest-Cooldown-Regler wirklich
        nicht auf 100 % steht (dasselbe Muster wie itemgenerators)."""
        return self._parse("QuestNodePrototypes.cfg")

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
        """FlashlightPrototypes: vier Structs [0]..[3] (Empty, PlayerFlashlight,
        NPCFlashlight, WeaponFlashlightTest). Nur die NPC-Lampe traegt
        Lichtwerte; die Spieler-Lampe sitzt in Blueprint-Kurven."""
        return self._parse("FlashlightPrototypes.cfg")

    @cached_property
    def aimassist(self) -> CfgStruct:
        """AimAssistPresetPrototypes: 15 Presets (Empty, Hip/AimMouse, Hip/
        AimGamepad + je Waffenklasse _AR/_PT/_SG/_SMG/_MG). Die Staerke
        steckt in CurveFloat-Assets, per cfg geht nur an/aus: Kegel-SIDs
        auf den Empty-Kegel setzen."""
        return self._parse("AimAssistPresetPrototypes.cfg")

    def armor_artifact_slots(self) -> dict[str, tuple[int, str | None]]:
        """{SID: (Vanilla-ArtifactSlots, Edition|None)} aller Spieler-
        Koerperruestungen (Slot Body; Helme haben 0 und bleiben draussen)."""
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
        """SaveLoadVariables (unbinarisiert): DefaultConfig.SavesLimit je
        Speichertyp, 0 = unbegrenzt."""
        return self._parse("SaveLoadVariables.cfg")

    @cached_property
    def autosave(self) -> CfgStruct:
        """AutoSaveVariables (unbinarisiert): DefaultConfig.AutoSaveIntervalTime
        in Sekunden."""
        return self._parse("AutoSaveVariables.cfg")

    @cached_property
    def weatherselection(self) -> CfgStruct:
        return self._parse("WeatherSelectionPrototypes.cfg")

    @cached_property
    def trade_text(self) -> str:
        return (self.dir / "TradePrototypes.cfg").read_text(
            encoding="utf-8-sig", errors="replace"
        )

    # ------------------------------------------------------------ inheritance
    @staticmethod
    def _resolve_chain(root: CfgStruct, sid: str) -> list[CfgStruct]:
        """Kette [Prototyp, Basis, Basis der Basis, ...] via refkey (gleiche Datei)."""
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
        """Erstes Template*-Glied in der Vererbungskette eines Items."""
        for node in self._resolve_chain(self.items, sid):
            if node.name.startswith("Template"):
                # Quest-Templates auf ihr Basis-Template weiterverfolgen
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
        """{SID: effektive Vanilla-MaxHP} aller Mutanten-Prototypen."""
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
        """{SID: {SpeedKey: Wert}} aller Mutanten-Prototypen (aufgeloest)."""
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
        """Kreatur-Fraktion (= Art) eines Mutanten-Prototyps."""
        faction = self._chain_get(self._resolve_chain(self.obj, sid), "Faction")
        return faction if faction in MUTANT_FACTIONS else None

    def mutant_regens(self) -> dict[str, float]:
        """{SID: VitalParams.RegenHP} aller Mutanten-Prototypen mit
        Regeneration > 0 (2.0.x: 44 von 47 — Mutanten heilen sich, wie
        die menschlichen NPCs)."""
        result: dict[str, float] = {}
        for sid in self.mutants():
            value = parse_number(
                self.resolve(self.obj, sid, "VitalParams.RegenHP"))
            if value > 0:
                result[sid] = value
        return result

    def mutant_attack_damages(self, species: str) -> dict[str, tuple[str, float]]:
        """{Attacken-Struct: (Damage-Pfad, Vanilla-Wert)} einer Mutanten-Art.

        Damage liegt top-level; nur die ChargeAbility_*-Structs nesten ihn
        unter DamageParams. Structs mit Damage <= 0 (Utility-Faehigkeiten)
        werden uebersprungen."""
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

    # Bloodsucker-Tarnung: Prototypen mit InvisibilityFeatureData
    INVISIBILITY_KEYS = ("ToVisibleSeconds", "ToInvisibleSeconds",
                        "InvisibilityLossFromDamage")

    def invisibility_prototypes(self) -> dict[str, dict[str, float]]:
        """{SID: {Key: Wert}} aller Prototypen mit eigener Tarnung."""
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

    # Consumable-Effekte: nur diese Typen sind gefahrlos skalierbar
    # (Vorzeichen-Regeln siehe docs/V15_DATA_RESEARCH.md)
    CONSUMABLE_SAFE_TYPES = {
        "EEffectType::Health", "EEffectType::Bleeding", "EEffectType::Radiation",
        "EEffectType::HungerPoints", "EEffectType::Stamina",
        "EEffectType::RegenStamina", "EEffectType::PsyPoints",
        "EEffectType::DegenPsyPoints", "EEffectType::SleepinessPoints",
        "EEffectType::DegenBleeding", "EEffectType::Drunkness",
    }
    # Bei diesen Typen sind POSITIVE Werte ein Malus (Hunger/Suff steigt) —
    # nur negative Werte skalieren
    CONSUMABLE_NEGATIVE_ONLY = {"EEffectType::HungerPoints",
                                "EEffectType::Drunkness"}

    def medical_healing_effects(self) -> set[str]:
        """Effekt-SIDs der GESUNDHEITS-Wirkung medizinischer Items.

        "Medizinisch" wird live aus den Daten abgeleitet, nicht ueber Namen:
        ein Consumable gilt als Medizin, wenn es AUCH einen
        blutungsstillenden Effekt referenziert (Bleeding mit negativem
        Wert). Das trifft Medkit/ArmyMedkit/EcoMedkit/Bandage — Essen und
        Getraenke stillen nie Blutungen. Geliefert werden nur deren
        positive Health-Effekte (das eigentliche Heilen)."""
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
        """{Effekt-SID: Effekt-Node} aller von Consumables referenzierten,
        gefahrlos skalierbaren Effekte."""
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

    # Anomalie-Schadens-Effekte je Element-Typ (SID-Sets verifiziert;
    # Werte werden live gelesen). PSY macht keinen direkten HP-Schaden.
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

    # Wetter: diese Sub-Structs gelten als "Regen/Sturm"
    RAIN_WEATHER_TYPES = ("Stormy", "LightRainy", "Rainy", "Thundery")

    # Das Null-Schema, von dem alle 18 echten Stash-Prototypen erben. NIE
    # patchen: es enthaelt nur Nullen und ItemPrototypeSID = empty; wuerde
    # man dort etwas aktivieren, tauchen ueberall Eintraege auf, die auf ein
    # nicht existierendes Item zeigen (docs/GENERATOR_RESEARCH.md, Warnung 17).
    STASH_TEMPLATE = "empty"

    # In Vanilla wirkungslos, deshalb nicht patchen (spart ~25 % Patch-Text):
    # die beiden *_MainLoot-Generatoren stehen in ALLEN Eintraegen auf
    # MaxSpawnChance = 0.f (von GSC bewusst abgeschaltet), die beiden
    # *_Corpse-Structs werden im gesamten GameData nirgends referenziert.
    STASH_UNUSED = {
        "Stash_AmmoSNG_Smart_MainLoot", "Stash_AmmoNATO_Smart_MainLoot",
        "StashMedicine_Corpse", "StashVodka_Corpse",
    }

    def stash_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Alle Smart-Loot-Eintraege der Verstecke/Leichen-Generatoren.

        Liefert (Stash-SID, ItemGenerators-Schluessel, Gruppe,
        Eintrags-Schluessel, Knoten) — die Schluessel kommen so, wie sie in
        der Datei stehen. Nichts wird konstruiert: Raenge und Gruppen sind
        je Struct unterschiedlich belegt (7 Structs haben nur [0], andere
        [0..3]; einzelnen Raengen fehlen ganze Gruppen)."""
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

    # ------------------------------------------------- Loot-Mengen (Generator)
    # ItemGeneratorPrototypes.cfg ist die grosse Loot-Datei (3.085 Prototypen).
    # Nur MinCount/MaxCount unter PossibleItems duerfen skaliert werden; die
    # gleichnamigen Felder unter MoneyGenerator sind Kupons und bleiben tabu
    # (Maximum 72.500 - ein Faktor darauf waere ein Wirtschafts-Exploit).
    # Der Sicherheitsfilter arbeitet ZWEISTUFIG, weil die Datei selbst keinen
    # Quest-Marker kennt (docs/GENERATOR_RESEARCH.md, Abschnitt 5):
    #   Stufe 1  Namensmuster auf Struct-Schluessel UND SID
    #   Stufe 2  jede ItemPrototypeSID des Blocks gegen ItemPrototypes.cfg
    # Stufe 1 allein laesst nachweislich Quest-Schluessel und Unikate durch.

    # Das leere Basis-Template, von dem 1.773 Prototypen erben. NIE patchen.
    LOOT_TEMPLATE_KEY = "[0]"

    # Stufe 1: Story-, Belohnungs-, Container-, Haendler- und Dev-Namen.
    # "Trade" steht mit drin, weil 13 Haendler-Lager (u.a.
    # MainTraderItemGeneratorV1 = Bestand von 32 Technikern/Medics/Guides)
    # NICHT ueber TradePrototypes.cfg verlinkt sind und sonst durchrutschen.
    LOOT_UNSAFE_NAME = re.compile(
        r"(?:^|_)(MQ|EQ|SQ|RSQ|ANCQ)(?=\d|_|$)|Quest|QSBIG|GDEQ|Reward|^C_"
        r"|(?:^|_)BP_|UAID_|Container|Template|Player|Boss|Arena"
        r"|(?:^|_)Key|(?:^|_)Safe|Icon|PDA|Trade"
    )
    # "GamePass" steht bewusst NICHT in der Blacklist (Review 01.09.): die 17
    # GamePass_Stash_*-Tabellen sind gewoehnliche Welt-Verstecke der Basis-
    # Version (167 Container mit SpawnOnStart auf der Hauptkarte, DLC=None),
    # inhaltlich 1:1-Klone der Stash_Cheap/Medium/Expensive-Tabellen. Die
    # Inhaltspruefung plus der Geldkarten-Skip decken sie vollstaendig ab.

    # Dasselbe Muster fuer die HAENDLER-Huelle - natuerlich ohne "Trade",
    # sonst filtert es genau die Structs weg, um die es geht (der
    # Trader/Condition-Test hat das gefangen: Huelle schrumpfte auf 2).
    TRADER_UNSAFE_NAME = re.compile(
        r"(?:^|_)(MQ|EQ|SQ|RSQ|ANCQ)(?=\d|_|$)|Quest|QSBIG|GDEQ|Reward|^C_"
        r"|(?:^|_)BP_|UAID_|Container|Template|Player|Boss|Arena"
        r"|(?:^|_)Key|(?:^|_)Safe|Icon|PDA"
    )

    # Unikat-Konvention auf Item-Ebene: Gun_<Name>_<Klasse> (Unterstrich nach
    # "Gun"), im Gegensatz zu Serienwaffen wie GunAK74_ST.
    LOOT_UNIQUE_ITEM = re.compile(r"^Gun_[A-Z]")

    # Platzhalter-Item; taucht 710x auf und existiert bewusst nicht in
    # ItemPrototypes.cfg. Kein Grund, einen Block zu verwerfen.
    LOOT_EMPTY_ITEMS = {"empty", "Empty"}

    # Faellt durch beide Stufen: der Elektrohalsband-Generator (Quest-Sache
    # ohne IsQuestItem-Marker; doppelte Exemplare koennen den Questfortschritt
    # blockieren - docs/GENERATOR_RESEARCH.md, Warnung 6).
    LOOT_DENY_SIDS = {"MutantElectrocollarGenerator"}

    # ItemPrototypes.cfg fuehrt ZWEI unabhaengige Quest-Marker. IsQuestItem
    # allein reicht nicht: 291 Items sind nur ueber IsQuestItemPrototype
    # markiert, darunter die Notiz-PDAs, die an OnPlayerGetItemEvent haengen.
    LOOT_QUEST_FLAGS = ("IsQuestItem", "IsQuestItemPrototype")

    # Geld ist in dieser Datei nicht nur der MoneyGenerator-Zweig: es liegt
    # auch als normales Item in PossibleItems (Geldkarten mit 500 bis 15.000
    # Kupons). Erkannt wird das am Effekt, nicht am Namen - ein Item ist
    # Waehrung, wenn einer seiner Aufsammel-Effekte diesen Typ hat.
    LOOT_MONEY_EFFECT = "EEffectType::AddMoney"
    LOOT_EFFECT_KEYS = ("EffectOnPickPrototypeSIDs", "EffectPrototypeSIDs")

    @cached_property
    def _quest_item_sids(self) -> set[str]:
        """Alle Item-SIDs mit einem der beiden Quest-Marker (refkey-Kette
        aufgeloest)."""
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
        """Item-SIDs, die beim Aufsammeln Kupons gutschreiben (Geldkarten).

        Live ueber den Effekt-Typ bestimmt, nicht ueber Namen: erst alle
        Effekte mit AddMoney sammeln, dann die Items, die einen davon
        auslesen (auch geerbt)."""
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
        """SID -> Struct-Schluessel. 226 Prototypen heissen [N] statt wie ihre
        SID; ein Patch MUSS den echten Schluessel treffen, sonst legt bpatch
        einen neuen Knoten an, statt zu patchen."""
        out: dict[str, str] = {}
        for key, node in self.itemgenerators.children.items():
            out.setdefault((node.values.get("SID") or key).strip(), key)
            out.setdefault(key, key)
        return out

    @cached_property
    def _trade_generator_keys(self) -> set[str]:
        """Alle Generatoren, die Haendler-Bestand erzeugen (transitiv).

        Zwei Quellen, die unterschiedlich behandelt werden:

        1. Die in TradePrototypes.cfg verlinkten Wurzeln - das ist die echte
           Handelskette. Von dort wird transitiv weitergegangen, weil sich
           mehrere Haendler Bausteine wie Trader_T2_Ammo teilen.
        2. Generatoren mit "Trade" im Namen. Die gehoeren 13x zu Haendlern,
           die NICHT ueber TradePrototypes verlinkt sind (z.B.
           MainTraderItemGeneratorV1, der Bestand von 32 Technikern und
           Medics). Sie werden selbst ausgeschlossen, geben ihre Sperre aber
           NICHT weiter: sonst reisst z.B. TraderEugene die Bausteine
           GeneralNPC_Consumables_Recon/_Stormtrooper mit hinaus, die 239
           bzw. 281 gewoehnliche NPC-Prototypen fuer ihre Medizin und
           Nahrung benutzen - dann wuerde der Leichen-Loot gar nicht mehr
           skalieren, also genau das, was der Regler verspricht.

        Haendler-Bestand ist bewusst NICHT Teil des Loot-Reglers."""
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
        """Stufe 2: jede ItemPrototypeSID des Blocks inhaltlich pruefen.

        Verworfen wird der GANZE Prototyp, sobald ein enthaltenes Item ein
        Quest-Item oder ein Unikat ist oder in ItemPrototypes.cfg gar nicht
        vorkommt (dann laesst es sich nicht pruefen - im Zweifel Finger weg;
        so fallen u.a. E07_MQ01PsySuit und E03_MQ02_HunterNote heraus)."""
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
        """Struct-Schluessel aller Prototypen, deren Stueckzahlen skaliert
        werden duerfen (Filter siehe oben)."""
        safe: list[str] = []
        for key, node in self.itemgenerators.children.items():
            sid = (node.values.get("SID") or key).strip()
            if key == self.LOOT_TEMPLATE_KEY or "#" in key:
                continue
            if key in self.LOOT_DENY_SIDS or sid in self.LOOT_DENY_SIDS:
                continue
            if key in self._trade_generator_keys:
                continue
            if sid.startswith("All"):        # Dev-Sammelgeneratoren (900 Stk.)
                continue
            if (self.LOOT_UNSAFE_NAME.search(key)
                    or self.LOOT_UNSAFE_NAME.search(sid)):
                continue
            if not self._loot_block_is_safe(node):
                continue
            safe.append(key)
        return safe

    def _loot_item_is_skippable(self, sid: str) -> bool:
        """Eintraege mit diesem Item ueberspringen, ohne den ganzen Prototyp
        zu verwerfen.

        Zwei Faelle, beide harmlose Einzelposten in sonst normalem Loot:
        Geldkarten (sonst waere der Regler ein Wirtschafts-Exploit, und die
        GUI verspricht ausdruecklich, Geld nicht anzufassen) und Items, deren
        NAME das Quest-Muster trifft, ohne einen Quest-Marker zu tragen -
        praktisch nur der unsichtbare Marker GuardQuestItem bei 31 Wachen
        und ein Debug-Artefakt auf der Testkarte."""
        if sid in self._money_item_sids:
            return True
        return bool(self.LOOT_UNSAFE_NAME.search(sid))

    def loot_count_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Alle skalierbaren Mengen-Eintraege der sicheren Prototypen.

        Liefert (Struct-Schluessel, Generator-Schluessel, Slot-Schluessel,
        Item-Schluessel, Knoten). Saemtliche Schluessel kommen aus der Datei:
        724 Slots heissen Head/BodyArmor/... statt [i]. Betreten wird nur der
        Zweig ItemGenerator - MoneyGenerator liegt daneben und bleibt
        unberuehrt."""
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

    # Waffen-Slots fuer den Zustands-Regler (Category am SLOT-Knoten;
    # Ruestung/Helme/Artefakte/Consumables bleiben bewusst draussen)
    CONDITION_CATEGORIES = frozenset({
        "EItemGenerationCategory::WeaponPrimary",
        "EItemGenerationCategory::WeaponSecondary",
        "EItemGenerationCategory::WeaponPistol",
    })

    def loot_durability_entries(self) -> list[tuple[str, str, str, str, CfgStruct]]:
        """Zustands-Eintraege (MinDurability+MaxDurability, Max > 0) in
        Waffen-Slots der SICHEREN Loot-Prototypen. Haendler-Ware ist ueber
        loot_generators() bereits ausgeschlossen; Eintraege mit nur einem
        der beiden Schluessel werden uebersprungen (Recherche, Warnung 14:
        ein Patch darf keinen neuen Schluessel anlegen)."""
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

    # Kategorien fuer den NPC-Gear-Quality-Regler (Weight-Lotterien)
    GEAR_CATEGORIES = frozenset({
        "EItemGenerationCategory::WeaponPrimary",
        "EItemGenerationCategory::WeaponSecondary",
        "EItemGenerationCategory::WeaponPistol",
        "EItemGenerationCategory::BodyArmor",
        "EItemGenerationCategory::Head",
    })

    def gear_weight_pools(self):
        """[(Struct, Gen, Slot, [(Item-Schluessel, Knoten, Weight, Cost)])]
        aller Waffen-/Ruestungs-Weight-Lotterien (>= 2 Eintraege) in den
        SICHEREN Loot-Prototypen — das sind die Rang-Loadout-Pools der
        NPCs. Items ohne aufloesbaren Preis (2.0.x: 18 von ~13.000)
        bleiben in der Liste, aber mit Cost None (der Builder laesst ihr
        Gewicht unangetastet)."""
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
        """Struct-Schluessel der Handelsketten-Huelle: transitiv ab den in
        TradePrototypes verlinkten Wurzeln (docs/GENERATOR_RESEARCH.md,
        Kap. 7), ohne Dev-Sammler (All*) und ohne Quest-Muster-Treffer.
        Das ist das GEGENSTUECK zum Loot-Regler, der genau diese Huelle
        ausschliesst."""
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
        """Bestands-Eintraege der Handelsketten-Huelle (Mengen und/oder
        Chance). Geldkarten und Quest-Muster-Items werden je Eintrag
        uebersprungen; der MoneyGenerator-Zweig wird nie betreten."""
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
        """{Trader-SID: (Money, bInfiniteMoney)} aller Laeden mit
        Money-Feld (2.0.x: 73, davon 59 vanilla unendlich)."""
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
        """{SID: RegenHP} aller menschlichen NPC-Prototypen mit
        Selbstheilung (Mutanten und Player ausgenommen)."""
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
        """{SID: DurabilityDamagePerShot} aller *_Player-Waffen-Settings."""
        return self._player_weapon_values("DurabilityDamagePerShot")

    def player_weapon_dispersion(self) -> dict[str, float]:
        """{SID: DispersionRadius} aller *_Player-Waffen-Settings."""
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
        """Kategorie einer Waffe (WeaponGeneralSetup-SID) ueber die
        refkey-Kette bis zum Kategorie-Template; None = keine Kategorie
        (Quest-/Sonderwaffen) -> nur globale Regler greifen."""
        for node in self._resolve_chain(self.weapongeneral, sid):
            if node.name in WEAPON_CATEGORY_OVERRIDES:
                return WEAPON_CATEGORY_OVERRIDES[node.name]
            if node.name in WEAPON_CATEGORY_TEMPLATES:
                return WEAPON_CATEGORY_TEMPLATES[node.name]
        return None

    def player_weapons(self) -> dict[str, tuple[str | None, str | None]]:
        """{WGS-SID: (Kategorie, CWS-Struct-SID)} aller Spieler-Waffen.

        Verknuepfungskette: Item -> PlayerWeaponAttributes
        (WeaponAttributesPrototypes.cfg) -> DefaultWeaponSettingsSID ->
        CharacterWeaponSettings-Struct. Der letzte Schritt ist Pflicht:
        bei 24 Unikaten heisst der CWS-Struct *_Player_WS, nicht *_Player,
        und mehrere Waffen koennen sich EIN CWS-Struct teilen
        (z.B. die ganze AK74-Familie -> GunAK74_ST_Player)."""
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
        # Editions-Waffen ergaenzen (Gabion & Co.); Skins wie
        # Deluxe_GunAK74_ST zeigen auf ein BASIS-Setup und werden nicht
        # doppelt gelistet.
        for wgs, (cat, cws, _ed) in self.dlc_player_weapons().items():
            if wgs not in result:
                result[wgs] = (cat, cws)
        return result

    # ------------------------------------------------------- DLC-Editionen
    @cached_property
    def dlc_editions(self) -> dict[str, dict[str, CfgStruct]]:
        """{Edition: {"items"/"weapongeneral": Baum}} der vorhandenen
        DLCGameData-Zweige. Ohne Editions-Paks / mit aelterem Cache leer —
        dann gibt es schlicht keine DLC-Waffen, sonst aendert sich nichts."""
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
        """Vererbungskette eines DLC-WGS-Structs: beginnt im Editions-Baum
        und springt beim refurl auf ../GameData/WeaponData/... in die
        Basis-Datei (dort geht es per normalem refkey weiter)."""
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
                # Kein Struct im Editions-Baum -> in der Basis weiter
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
        """{WGS-SID: (Kategorie, CWS-SID, Edition)} aller Editions-Waffen,
        deren Setup-Struct WIRKLICH im Editions-Baum liegt (Skins mit
        Basis-Setup wie Deluxe_GunAK74_ST fallen heraus — sie sind
        identisch mit der Basis-Waffe)."""
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
        """{WGS-SID: Edition} der echten Editions-Setups (fuer Patch-
        Zuordnung und GUI-Hinweis)."""
        return {wgs: ed
                for wgs, (_c, _w, ed) in self.dlc_player_weapons().items()}

    def dlc_item_chain(self, edition: str, sid: str) -> list[CfgStruct]:
        """Vererbungskette eines DLC-ITEM-Structs: beginnt im Editions-
        Baum und springt beim refurl auf ../GameData/ItemPrototypes/...
        in die Basis-ItemPrototypes (dort per refkey weiter)."""
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

    # Schutz-Schluessel (identisch mit ARMOR_PARAM_KEYS in tweaks.py)
    ARMOR_PROTECTION_KEYS = ("Strike", "Burn", "Shock", "ChemicalBurn",
                             "Radiation", "PSY")

    def dlc_player_armors(self) -> dict[str, tuple[str, dict[str, float], str]]:
        """{SID: (Slot, {Schutzart: Wert}, Edition)} der Editions-
        Ruestungen. Erkannt am refurl auf .../ArmorPrototypes.cfg; die
        Schutzwerte kommen aus der Quer-Datei-Kette (die DLC-Structs
        definieren ihre Protection-Bloecke selbst)."""
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
        """Klartext fuer die Statuszeile: welche Editions-Inhalte die
        Installation mitbringt (der 'DLC-Checker' des Besitzers)."""
        if not self.dlc_editions:
            return ""
        n_guns = len(self.dlc_player_weapons())
        n_armor = len(self.dlc_player_armors())
        names = {"PreOrder": "Pre-order"}
        eds = ", ".join(names.get(e, e) for e in sorted(self.dlc_editions))
        return (f"Edition content found ({eds}): {n_guns} guns, "
                f"{n_armor} armor pieces.")

    def dlc_weapon_general_values(self, path: str) -> dict[tuple[str, str], float]:
        """{(Edition, SID): Wert} aller DLC-WGS-Structs, die den Pfad
        SELBST definieren (Wert > 0) — Pendant zu weapon_general_values;
        geerbte Werte skalieren ueber den Basis-Patch automatisch mit."""
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
        """SIDs aller Techniker-Upgrades, deren Sperrliste `key` in Vanilla
        NICHT leer ist (BlockingUpgradePrototypeSIDs = sich ausschliessende
        Zweige, RequiredUpgradePrototypeSIDs = Vorstufen/Tiers,
        RequiredItemPrototypeSIDs = Blaupausen). Nicht-leere Listen stehen
        als Kind-Struct mit [i]-Eintraegen, leere als leerer Skalar
        `Key =` - genau so wird eine Liste per bpatch geleert."""
        out: list[str] = []
        for sid, node in self.upgrades.children.items():
            if "#" in sid or sid == "[0]":      # [0] = Basis-Template aller Upgrades
                continue
            child = node.children.get(key)
            # "" und "empty" sind Platzhalter (3 Ruestungs-Upgrades, [0])
            if child is not None and any(
                    v.strip() not in ("", "empty") for v in child.values.values()):
                out.append(sid)
        return out

    # ------------------------------------------------ A-Life: Lager + Director
    # Recherche: docs/ALIFE_SPAWN_RESEARCH.md (03.09.2026) - alle Regeln dort.
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
        """Ein Eintrag je (Lager-Typ, Bewohner-Fraktion, Rang) aus
        LairPrototypes.cfg (784 in Vanilla): quantity = MaxSpawnQuantity,
        min_sum = Summe MinQuantityPerArchetype (Untergrenze beim
        Verkleinern), timers = die drei Respawn-Zeiten als Rohtext,
        guard = Basis-Wachen-Lager (Guard*), mutant = Mutanten-Fraktion.
        Das [0]-Template bleibt draussen."""
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
                    })
        return out

    def lair_standard_timers(self) -> tuple[str, str, str]:
        """Das haeufigste Respawn-Timer-Tripel (Vanilla: 180/480/480 in 774
        von 784 Bloecken) - nur diese Bloecke skaliert der Respawn-Regler,
        die 10 Story-Lager mit Sofort-Nachfuellung (6/30/30) bleiben tabu."""
        counts: dict[tuple[str, str, str], int] = {}
        for blk in self.lair_blocks():
            counts[blk["timers"]] = counts.get(blk["timers"], 0) + 1
        return max(counts, key=counts.get) if counts else ("", "", "")

    def director_preset(self) -> CfgStruct | None:
        return self.director.children.get("ALifeDirectorPreset")

    def director_scenario_tokens(self) -> dict[str, frozenset]:
        """{Szenario-Struct-Key: Squad-Tokens} - Token = "Human" / "Mutant"
        (generische Archetypen) oder die konkrete AgentPrototypeSID
        (Blinddog, Boar, Chimera ...); Menschen-Prototypen (General*/Guard*)
        werden zu "Human". Rein-Mutanten-Szenarien = kein "Human"-Token."""
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
        """[(Rang-Index, Typ-Index, Agententyp, MaxCount)] aus
        ALifeScenarioNPCArchetypesLimitsPerPlayerRank (4 Raenge x 16 Typen)."""
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
        """{Effekt-SID: Duration-Rohwert} aller Effekte, die ein Consumable-
        Item (item_category == "consumable") referenziert und die mindestens
        min_seconds laufen - Vanilla (>= 10 s): Hercules 300 s (+ Penalty),
        Zimt 180 s, Vodka-PSY 90 s, PSY-Blocker 60 s, Energydrinks 45 s,
        Mohn-Schlaf 30 s. Sofort-Effekte (Heilung/Blutstopp/Antirad 1-2 s)
        und Malus-Effekte (EBeneficial::Negative) bleiben bewusst draussen."""
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
                # Malus-Effekte (Rausch, Stamina-Kater, Hercules-Nachwirkung)
                # bleiben vanilla - wie beim Consumable-Staerke-Regler
                if (enode.values.get("Positive") or "").strip().endswith("Negative"):
                    continue
                raw = enode.values.get("Duration")
                if raw is not None and parse_number(raw) >= min_seconds:
                    out[eff] = raw
        return out

    def quest_items_with_weight(self) -> dict[str, float]:
        """{SID: Vanilla-Gewicht} aller Quest-Items (beide Quest-Marker,
        refkey-Kette) mit Gewicht > 0 - Vanilla: 290 von 327, bis 25 kg.
        Die Gewichtsregler je Kategorie lassen Quest-Items aus (keine
        Kategorie), darum eine eigene Checkbox."""
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
        """Alle menschlichen NPC-Prototypen (Faction gesetzt, nicht Mutant,
        nicht Player/[0]) - Basis fuer per-Prototyp-Patches wie das Wanken."""
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
        """{Magazin-Item-SID: Magazine.MaxAmmo} aller konkreten Magazin-
        Aufsaetze der Basis-ItemPrototypes (Wert > 0; Templates/[0] raus)."""
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
        """{WGS-SID: [Magazin-Item-SIDs]} - welche Magazin-Aufsaetze eine
        Waffe benutzt. Quelle ist die Waffe selbst: der Block
        WeaponReloadTimePerAttachment.[i].AttachPrototypeSID im
        WeaponGeneralSetup (ueber die refkey-Kette aufgeloest, DLC-Waffen
        ueber ihre Editions-Kette). Nur Eintraege, die wirklich Magazine
        sind (magazine_items), z.B. GunAK74_ST -> GunAK74_MagDefault,
        GunAK74_MagIncreased, GunAK_MagPaired. Ein Magazin kann mehreren
        Waffen gehoeren (GunAK_MagPaired: AK-Familie)."""
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

    def weapon_general_values(self, path: str) -> dict[str, float]:
        """{SID: Wert} aller WeaponGeneralSetup-Structs, die den (ggf.
        verschachtelten) Pfad SELBST definieren (Wert > 0). Vererbte Werte
        skalieren automatisch ueber den Patch des Eltern-Structs mit."""
        result: dict[str, float] = {}
        for sid, node in self.weapongeneral.children.items():
            if "#" in sid:
                continue
            raw = node.get(path)
            if raw is None:
                continue
            number = parse_number(raw)
            if number > 0:
                result[sid] = number
        return result

    # ------------------------------------------------------------- Kaliber
    # Der EINZIGE Ort, an dem steht, welche Patrone eine Waffe frisst:
    # AmmoCaliber (ein Wert) plus AmmoTypeProjectiles (Liste der erlaubten
    # Sorten mit ihrem Projektil). Beides im selben Struct wie MaxAmmo.
    # Wichtig fuer Patches: JEDE Waffe deklariert beides selbst — nachgezaehlt
    # 92 von 92 Structs, davon 12 Templates auf ::None. Es wird also nichts
    # geerbt, und ein Patch auf eine Waffe trifft keine andere.

    def weapon_caliber(self, sid: str, edition: str | None = None) -> str | None:
        """Kaliber einer Waffe ohne das EAmmoCaliber::-Praefix, z.B. "A545"."""
        raw = (self.dlc_resolve_weapon(edition, sid, "AmmoCaliber")
               if edition is not None
               else self.resolve(self.weapongeneral, sid, "AmmoCaliber"))
        if not raw:
            return None
        name = str(raw).split("::")[-1].strip()
        return None if name in ("", "None") else name

    def weapon_ammo_slots(self, sid: str,
                          edition: str | None = None) -> dict[str, str]:
        """{"[0]": "Default", "[1]": "ArmorPiercing", ...} einer Waffe.

        Die Indizes sagen NICHTS ueber die Sorte: sechs Scharfschuetzen-
        gewehre (SVD, SVU, M701, Cavalier, Lynx, Whip) haben auf [0]
        Supersonic statt Default. Deshalb wird beim Patchen pro Index die
        dort stehende SORTE gelesen, nie die Position angenommen."""
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
        """{Kaliber: {Sorte: Projektil-SID}} — aus den Waffendaten erhoben,
        nicht aus Namen geraten.

        Fast jedes Kaliber benutzt EIN Projektil fuer alle Sorten; Schrot
        ist die Ausnahme (Default -> P012, AP/HP -> P012F, die Flinten-
        laufgeschosse). Kaliber, die keine Waffe benutzt, tauchen hier gar
        nicht erst auf — das haelt 7,62x39 draussen, dessen Munition zwar
        existiert, aber in keinem Loot-Generator vorkommt."""
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
        """{Kaliber: DamageMod seiner Standardpatrone}.

        Der Schaden selbst steht an der WAFFE (BaseDamage in
        CharacterWeaponSettings — dort kommt das Wort Caliber kein
        einziges Mal vor). Die Munition liefert nur diesen Multiplikator,
        und er ist ueber alle Gewehr- und Pistolenkaliber 1.0. Genau eine
        Ausnahme: Schrot steht bei 0.084, weil eine Schrotpatrone viele
        Kugeln verschiesst — die Flinte gleicht das mit BaseDamage 50.0
        gegen 9.5 beim Gewehr aus. Daraus laesst sich vorrechnen, was ein
        Wechsel mit dem Schaden macht, statt es zu behaupten."""
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
        """Wieviele Item-Prototypen (Spieler + NPC + Bosse) sich dieses
        WeaponGeneralSetup teilen.

        Zaehlt, weil das Kaliber am SETUP haengt: die Spieler-AK-74,
        Korshunovs AK und die Wach-AK teilen sich eines — wer die eine
        umstellt, stellt alle drei um. Bei TOZ und PM sind es vier."""
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
        """{Trader-SID: {Generator-Index: {Schluessel: Vanilla-Wert}}}.

        Erfasst nur Schluessel aus TRADE_KEYS, die der jeweilige
        Generator-Eintrag selbst definiert (bpatch-sicher).
        """
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

    AMMO_MOD_KEYS = ("DamageMod", "ArmorPiercingMod", "ArmorDamageMod",
                     "CoverPiercingMod")

    def ammo_mods(self) -> dict[str, dict[str, float]]:
        """{SID: {ModKey: aufgeloester Vanilla-Wert}} aller Munitions-Items."""
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

    def ammo_kinds(self) -> dict[str, tuple[str, str]]:
        """{SID: (Kaliber-Kuerzel, Munitionsart)} aller Munitions-Items.

        Beide Felder stehen als Enum in den Prototypen ("EAmmoCaliber::A545",
        "EAmmoType::ArmorPiercing"); zurueckgegeben wird nur der Teil hinter
        "::". Fehlt eines, steht "" drin -- der Baum zeigt das Item trotzdem.

        Bewusst ueber ammo_mods() statt ueber self.items: so kann der Baum
        strukturell keine Sorte anbieten, die _items_patch nicht kennt.
        """
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
        """{SID: {Schutzart: Wert}} der Spieler-Protection aller Ruestungen/
        Helme (nur Werte > 0; ProtectionNPC bleibt bewusst unberuehrt)."""
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
        """{SID: (Slot, {Schutzart: Vanilla-Wert})} aller Ruestungen/Helme,
        die der SPIELER bekommen kann — fuer den Einzelruestungs-Baum.

        NPC-only-Ruestungen (Invisible = true, z.B. NPC_Korshunov_Armor)
        bleiben draussen: ihre Spieler-Protection ist im Spiel bedeutungslos
        und wuerde den Baum nur aufblaehen. Der GLOBALE Schutz-Patch laeuft
        weiter ueber armor_protection() (alle 86) — harmlos und unveraendert.
        Slot ist "Body" oder "Head" (aus ItemSlotType, aufgeloest)."""
        result: dict[str, tuple[str, dict[str, float]]] = {}
        for sid, values in self.armor_protection().items():
            invisible = (self.resolve(self.items, sid, "Invisible") or "")
            if invisible.strip().rstrip(";").strip().lower() == "true":
                continue
            slot = (self.resolve(self.items, sid, "ItemSlotType") or "")
            slot = slot.split("::")[-1].strip() or "Body"
            result[sid] = (slot, values)
        # Editions-Ruestungen (SEVA Monolith & Co.) ergaenzen
        for sid, (slot, values, _ed) in self.dlc_player_armors().items():
            if sid not in result:
                result[sid] = (slot, values)
        return result

    DETECTOR_RANGE_KEYS = ("ShowArtifactRadius", "MinDetectRadius",
                           "DetectorWorkRadius", "SonarRadius",
                           "AnomalyDetectionRadius")

    def detector_items(self) -> dict[str, dict[str, float]]:
        """{SID: {RadiusKey: Wert}} der Artefakt-Detektor-Items (Echo & Co.)."""
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
        """ValueMin eines Effekts als Prozentzahl, z.B. -15 fuer '-15%'."""
        node = self.effects.children.get(sid)
        if node is None:
            return 0.0
        raw = (node.get("ValueMin") or "0").strip().rstrip("%")
        return parse_number(raw)

    def gear_durability(self) -> dict[str, tuple[str, float]]:
        """{SID: (kategorie, vanilla BaseDurability)} fuer Waffen + Ruestung."""
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
            if value <= 1.0:  # 1.0 = Platzhalter des Basis-Structs
                continue
            result[sid] = (cat, value)
        return result

    def item_weights(self) -> dict[str, tuple[str, float]]:
        """{SID: (kategorie, vanilla Weight)} aller Items mit Gewicht > 0."""
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
        """{Difficulty-SID: effektiver Wert} fuer einen Pfad wie
        "EnvironmentDifficulty.Weapon_BaseDamage" (aufgeloest ueber refkey)."""
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

    # ------------------------------------------------------ Emissions-Dauer
    def emission_default_timeline(self):
        """(Struct-Schluessel, Stages-Knoten, AIEvents-Knoten) des
        DEFAULT-Emissionsprototyps — der einzigen wiederkehrenden Welt-
        Emission. Die 5 uebrigen Prototypen sind Story-Emissionen
        (E06/E15) und bleiben tabu. ACHTUNG: der bpatch-Schluessel ist
        der INDEX ([0]), nicht die SID."""
        for key, node in self.emissions.children.items():
            if (node.values.get("SID") or "").strip() == "Default":
                return (key, node.children.get("Stages"),
                        node.children.get("AIEvents"))
        return (None, None, None)

    # ------------------------------------------- wiederholbare Quest-Timer
    def repeatable_quest_timers(self) -> dict[str, float]:
        """{Knoten-SID: InGameHours} aller SetTimer-Knoten von RSQ-Quests
        (repeatable side quests; Vanilla: 8 Knoten, alle 24 h). Story-
        und Nebenquest-Timer (E*/SQ*/EQ*) bleiben bewusst draussen.
        Parst die 75-MB-Datei — nur aufrufen, wenn wirklich noetig."""
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

    # ------------------------------------------------- Fraktionsbeziehungen
    # Recherche: docs/FACTION_RELATIONS_RESEARCH.md (582 Paare, Stand 2.0.x)

    def _relations_default(self) -> CfgStruct | None:
        return self.relations.children.get("Default")

    def relation_pairs(self) -> dict[str, int]:
        """{Paar-Schluessel wie "Bandits<->Player": Vanilla-Wert} — die
        Schluessel-Schreibweise (Reihenfolge der beiden Fraktionen) ist
        exakt die der Spieldaten; nur diese Schluessel darf ein Patch
        anfassen (neue Paare anzulegen ist ungetestet)."""
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
        """Vorhandenen Schluessel fuer das Paar (a, b) finden — die
        Spieldaten kennen je Paar nur EINE Richtung ("Duty<->Freedom"
        existiert, "Freedom<->Duty" nicht)."""
        pairs = self.relation_pairs()
        for key in (f"{a}<->{b}", f"{b}<->{a}"):
            if key in pairs:
                return key
        return None

    def relation_version(self) -> int:
        """Vanilla-RelationVersion (2.0.x: 7). Der Patch schreibt +1,
        damit bestehende Saves die neue Baseline bemerken (Hypothese,
        siehe Recherche-Dokument — bis zum In-Game-Test als 'untested on
        existing saves' beschriftet)."""
        d = self._relations_default()
        if d is None:
            return 0
        return int(round(parse_number(d.values.get("RelationVersion"), 0)))

    def relation_reaction_tables(self):
        """[(Tabelle, Index, Knoten)] der 2x8 Reaktions-Tabellen
        (CharacterReactions = lokal/temporaer, FactionReactions =
        global/permanent). Die Grenade-Tabelle der FactionReactions ist
        in Vanilla leer und faellt ueber ihre fehlenden Werte heraus."""
        d = self._relations_default()
        out = []
        for table in ("CharacterReactions", "FactionReactions"):
            node = d.children.get(table) if d is not None else None
            for idx, entry in (node.children.items() if node else ()):
                out.append((table, idx, entry))
        return out

    def faction_rollback_cooldowns(self) -> dict[str, float]:
        """{Fraktion: Sekunden} aus FactionRollbackCooldowns (Vanilla: 19
        Eintraege, alle 900)."""
        d = self._relations_default()
        if d is None:
            return {}
        node = d.children.get("FactionRollbackCooldowns")
        if node is None:
            return {}
        return {fac: parse_number(raw) for fac, raw in node.values.items()}
