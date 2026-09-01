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
]

# Bei Aenderungen an NEEDED_FILES erhoehen -> alte Caches werden neu aufgebaut
CACHE_SCHEMA = 10

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
            if progress:
                progress("Converting cfg.bin to readable cfg ...")
            for bin_path in sorted(gd.rglob("*.cfg.bin")):
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
