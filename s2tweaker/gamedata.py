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
]

# Bei Aenderungen an NEEDED_FILES erhoehen -> alte Caches werden neu aufgebaut
CACHE_SCHEMA = 7

GAMEDATA_REL = "Stalker2/Content/GameLite/GameData"

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
                progress("Extrahiere GameData aus pakchunk0 ...")
            for name in NEEDED_FILES:
                pakio.unpack(pak, cache, include=f"{GAMEDATA_REL}/{name}")
            if progress:
                progress("Konvertiere cfg.bin nach cfg ...")
            for bin_path in sorted(gd.rglob("*.cfg.bin")):
                out = bin_path.with_name(bin_path.name[: -len(".bin")])
                if not out.exists():
                    roots = vendor_bin2cfg.read_binary_cfg(bin_path.read_bytes())
                    out.write_text(
                        "\n".join(r.to_string() for r in roots), encoding="utf-8"
                    )
            marker.write_text("ok", encoding="utf-8")
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
