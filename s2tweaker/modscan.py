"""Fremde Mods in ~mods scannen und mit den eigenen Reglern abgleichen.

Ablauf (GUI ruft das hier auf, siehe gui.App._run_modscan):
  1. .pak-Dateien in ~mods finden, auch in Unterordnern: UE5 laedt Paks
     rekursiv, und Spieler sortieren ihre Mods gern selbst in
     Unterordner (z.B. ~mods\\oxa\\). Eigene Ausgabe-Pak ausnehmen.
  2. Je Pak nur die cfg-Eintraege unter GameData/DLCGameData listen und in
     EINEM gebuendelten repak-Aufruf extrahieren — NIE die ganze Pak
     (Overhaul-Mods sind bis zu 2 GB gross).
  3. Aus jeder cfg die Menge der (Top-Level-Struct, Blattname)-Paare ziehen.
  4. Die GUI vergleicht diese Paare mit dem "Fussabdruck" jedes Reglers
     (tweaks.build_patches mit genau EINEM verstellten Regler).

Verglichen wird bewusst auf (Top-Level-Struct + Blattname), NICHT auf dem
vollen Pfad: fremde Mods patchen denselben Wert oft ueber eine andere
Dateiablage oder Verschachtelung (volle Struct-Kopien statt {bpatch},
andere Patch-Ordner, das offizielle "Base.cfg_patch_<Mod>"-Namensschema
ohne .cfg-Endung, Legacy-refkey-Patches unter freiem Namen). Drei
Verfeinerungen halten die Trefferqualitaet hoch:

  - Legacy-Patches (refkey=<SID> statt {bpatch}) werden zusaetzlich unter
    ihrem ZIEL-Prototyp gezaehlt — der eigene Struct-Name ist frei waehlbar.
  - Vollkopien (Structs OHNE {bpatch}) wiederholen fast alle Vanilla-Werte;
    gezaehlt wird dort nur, was sich vom Vanilla-Wert unterscheidet (Index
    ueber die bereits geparsten Spieldaten; Unbekanntes bleibt vorsichtig
    drin). Sonst markiert eine 60-MB-Vollkopie fast jeden Regler.
  - "Weight" zaehlt nur direkt unter dem Top-Struct: in ItemPrototypes ist
    das die Masse (kg), tiefer verschachtelt ist es ueberall die
    Auswahl-Lotterie (PackOfItemsGroup, Loot-Listen) — eine andere Mechanik.

IoStore-Mods (.pak mit .ucas/.utoc daneben) kann repak nicht lesen — die
werden ehrlich als "contains data I can't read" gemeldet statt still
uebersprungen.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import cfgparse, pakio, vendor_bin2cfg
from .cfgparse import CfgStruct

# DLC-Konfigs liegen in einem Schwester-Ordner; kein Regler patcht dort,
# aber der Ergebnis-Dialog soll nicht "no config changes" behaupten.
GAMEDATA_MARKERS = ("/GameLite/GameData/", "/GameLite/DLCGameData/")

_INDEX_KEY = re.compile(r"^\[\d+\]$")

# Diese gd-Attribute (alle cached_property) bilden den Vanilla-Index fuer
# den Werte-Vergleich bei Vollkopien. Nur Dateien, die das Tool ohnehin
# kennt — mehr braucht der Abgleich nicht, denn nur dort liegen Regler.
_GD_TREES = (
    "obj", "items", "difficulty", "weightparams", "effectmax", "effects",
    "floatproviders", "weaponsettings", "weaponattributes", "trade",
    "holdbreath", "weapongeneral", "corevars", "stashes", "aiglobals",
    "hearingsensors", "visionscanners", "camerashake", "artifactspawners",
    "passivedetectors", "fasttravel", "boolproviders", "abilities", "melee",
    "weatherselection", "itemgenerators", "relations",
)


@dataclass
class ModInfo:
    """Ergebnis des Scans EINER fremden Pak."""

    name: str                       # Dateiname ohne .pak
    path: Path
    readable: bool = True
    note: str = ""                  # z.B. "contains data I can't read"
    n_cfg: int = 0                  # gefundene cfg-Dateien unter GameData
    pairs: set = field(default_factory=set)       # {(TopStruct, Blattname)}
    base_names: set = field(default_factory=set)  # {"DifficultyPrototypes", ...}
    source: str = "~mods"           # "~mods" | "workshop"


def find_mod_paks(mods_dir: Path, exclude_names: set[str]) -> list[Path]:
    """Alle fremden .pak-Dateien in ~mods, REKURSIV: UE5 mountet auch
    Unterordner, und Spieler legen sich dort gern eine eigene Ordnung
    an (manche Mods liefern Unterordner auch selbst mit)."""
    if not mods_dir.is_dir():
        return []
    excl = {n.lower() for n in exclude_names}
    return sorted(
        p for p in mods_dir.rglob("*.pak")
        if p.name.lower() not in excl
    )


def find_workshop_paks(workshop_dir: Path | None) -> list[Path]:
    """Alle .pak-Dateien abonnierter Steam-Workshop-Mods (rekursiv — die
    Struktur ist tief: <id>\\Windows\\{New,Override}Content\\...\\Paks\\...).
    Verifiziert 02.09.: das Spiel liest sie direkt von dort, kopiert wird
    nichts in den Spielordner."""
    if workshop_dir is None or not workshop_dir.is_dir():
        return []
    return sorted(workshop_dir.rglob("*.pak"))


def workshop_mod_name(pak: Path, workshop_dir: Path) -> str:
    """Anzeigename einer Workshop-Pak: der Mod-Ordner unter Stalker2/Mods/
    (letztes Vorkommen — so heisst die Mod wirklich), sonst die Item-ID.
    NewContent-Paks (neue Assets, Mount ausserhalb GameData) werden im
    Namen unterschieden, damit die zwei Paks einer Mod im Dialog nicht
    identisch heissen."""
    parts = pak.parts
    name = None
    for i in range(len(parts) - 2):
        if parts[i].lower() == "mods":
            name = parts[i + 1]
    if name is None:
        try:
            name = pak.relative_to(workshop_dir).parts[0]
        except ValueError:
            name = pak.stem
    kind = ", new content" if "newcontent" in pak.stem.lower() else ""
    return f"{name} (Workshop{kind})"


def is_iostore(pak: Path) -> bool:
    """IoStore-Mods bestehen aus .pak + .utoc + .ucas — repak liest nur
    klassische Paks; der .pak-Teil ist dann ein Stub ohne die Daten."""
    return (pak.with_suffix(".utoc").is_file()
            or pak.with_suffix(".ucas").is_file())


def _short_error(exc: Exception) -> str:
    """Fehlertext auf EINE kurze Zeile eindampfen — repak wirft sonst 1,7 KB
    Roh-stderr, die im Ergebnis-Dialog landen wuerden."""
    text = str(exc).strip()
    if "version unsupported" in text or "trying version" in text:
        return "not a readable .pak file"
    first = text.splitlines()[0] if text else "unknown error"
    return first[:120]


def _split_marker(path: str) -> str | None:
    """Pfad hinter dem GameData-/DLCGameData-Marker, sonst None."""
    norm = path.replace("\\", "/")
    for marker in GAMEDATA_MARKERS:
        if marker in norm:
            return norm.split(marker, 1)[1]
    return None


def _is_cfg_name(name: str) -> bool:
    """Config-Datei? ENTHAELT .cfg statt endswith: das offizielle
    Patch-Namensschema ist "Base.cfg_patch_<Mod>" OHNE weitere Endung
    (docs/SPEC.md, Abschnitt 0) — endswith(".cfg") uebersieht es."""
    return ".cfg" in name


def _norm_value(raw: str) -> str:
    """Wert fuer den Vanilla-Vergleich normalisieren: 1 / 1. / 1.0 / 1.f
    sind dieselbe Zahl, True/False/false dieselben Booleans."""
    v = raw.strip().rstrip(";").strip()
    if v.endswith("%"):
        core = v[:-1].strip()
        suffix = "%"
    else:
        core = v
        suffix = ""
    core2 = core.rstrip("fF").rstrip(".")
    try:
        return repr(float(core2)) + suffix
    except ValueError:
        return v.lower()


def build_vanilla_index(gd) -> dict[tuple[str, str], set[str]]:
    """(Top-Level-Struct, Blattname) -> {normalisierte Vanilla-Werte} ueber
    alle Spieldaten-Dateien, die das Tool kennt. Grundlage fuer den
    "hat die Vollkopie den Wert wirklich geaendert?"-Vergleich."""
    index: dict[tuple[str, str], set[str]] = {}
    for attr in _GD_TREES:
        try:
            tree = getattr(gd, attr)
        except Exception:
            continue                     # Datei fehlt im Dev-Dump: tolerieren
        for top_key, top in tree.children.items():
            top_name = top_key.split("#")[0]
            for node in top.walk():
                for key, value in node.values.items():
                    index.setdefault((top_name, key), set()).add(
                        _norm_value(value))
    return index


def collect_pairs(root: CfgStruct,
                  vanilla_index: dict | None = None) -> set[tuple[str, str]]:
    """(Top-Level-Struct, Blattname)-Paare einer geparsten cfg.

    - "#n"-Suffixe des Parsers (doppelte Namen) werden entfernt.
    - Legacy-Patches ({refkey=<SID>} mit freiem Struct-Namen) zaehlen
      ZUSAETZLICH unter ihrem Ziel-Prototyp.
    - Structs ohne {bpatch} gelten als Vollkopie: mit vanilla_index werden
      nur Werte gezaehlt, die sich von Vanilla unterscheiden (unbekannte
      Paare bleiben vorsichtig drin).
    - "Weight" nur direkt unter dem Top-Struct (siehe Modul-Docstring)."""
    pairs: set[tuple[str, str]] = set()
    for top_key, top in root.children.items():
        own = top_key.split("#")[0]
        names = {own}
        attrs = top.attr_dict()
        refkey = (attrs.get("refkey") or "").strip()
        if refkey and not _INDEX_KEY.fullmatch(refkey):
            names.add(refkey)
        check_vanilla = (vanilla_index is not None
                         and "bpatch" not in attrs)
        for node in top.walk():
            for key, value in node.values.items():
                if key == "Weight" and node is not top:
                    continue
                if check_vanilla:
                    # Geprueft wird gegen den EIGENEN Namen; nur wenn der in
                    # Vanilla unbekannt ist (Legacy-Patch unter freiem
                    # Namen), gegen das refkey-Ziel. Beides zugleich waere
                    # falsch: ein erbender Struct (Hard erbt von Empty)
                    # saehe sonst jeden eigenen Wert als "geaendert", weil
                    # er vom Basis-Wert abweicht.
                    vals = vanilla_index.get((own, key))
                    if vals is None and refkey in names:
                        vals = vanilla_index.get((refkey, key))
                    if vals is not None and _norm_value(value) in vals:
                        continue         # Vollkopie wiederholt Vanilla
                for name in names:
                    pairs.add((name, key))
    return pairs


def base_segments(rel_after_gamedata: str) -> set[str]:
    """Alle Pfadsegmente eines GameData-Eintrags, um ".cfg"-Endungen
    bereinigt. Dient nur als billiger Vorfilter fuer die teuren Regler
    ("kommt ItemGeneratorPrototypes in dieser Mod ueberhaupt vor?") —
    der eigentliche Vergleich laeuft ueber die (Struct, Blatt)-Paare."""
    return {part.split(".cfg")[0]
            for part in rel_after_gamedata.split("/") if part}


def _escape_glob(entry: str) -> str:
    """repak -i ist ein GLOB-Muster, kein Literal: "[...]" ist eine
    Zeichenklasse. "[" zuerst escapen macht alle uebrigen "]" literal
    (mehr Sonderzeichen sind in Windows-Dateinamen nicht erlaubt)."""
    return entry.replace("\\", "/").replace("[", "[[]")


def scan_pak(pak: Path, progress=None, vanilla_index: dict | None = None) -> ModInfo:
    """Eine fremde Pak scannen: cfg-Eintraege listen, entpacken, parsen."""
    info = ModInfo(name=pak.stem, path=pak)

    if is_iostore(pak):
        info.readable = False
        info.note = "contains data I can't read (IoStore format)"
        return info

    try:
        entries = pakio.list_pak(pak)
    except Exception as exc:  # kaputte/unlesbare Pak: melden, nicht crashen
        info.readable = False
        info.note = f"contains data I can't read ({_short_error(exc)})"
        return info

    cfg_entries = [e for e in entries
                   if _split_marker(e) is not None
                   and _is_cfg_name(e.replace("\\", "/").split("/")[-1])]
    info.n_cfg = len(cfg_entries)
    if not cfg_entries:
        info.note = "no config changes (probably meshes, textures or audio)"
        return info

    with tempfile.TemporaryDirectory(prefix="s2tweaker_scan_") as tmp:
        out = Path(tmp)
        if progress:
            progress(f"Scanning {pak.name} "
                     f"({info.n_cfg} config file{'s' if info.n_cfg != 1 else ''}) ...")
        try:
            # EIN gebuendelter repak-Aufruf statt einem Prozess pro Datei —
            # nur die cfg-Eintraege werden extrahiert, nie die ganze Pak.
            pakio.unpack_many(pak, out,
                              [_escape_glob(e) for e in cfg_entries])
        except Exception as exc:
            info.readable = False
            info.note = f"contains data I can't read ({_short_error(exc)})"
            return info
        # Statt die Ablage je Eintrag zu erraten (Mount-Points variieren je
        # Mod), einfach ALLES Extrahierte einsammeln — mehr als die
        # angeforderten cfg-Eintraege kann nicht dort liegen.
        parsed = 0
        for extracted in sorted(out.rglob("*")):
            if not extracted.is_file() or not _is_cfg_name(extracted.name):
                continue
            rel = _split_marker(extracted.as_posix())
            if rel is None:
                continue
            try:
                if ".cfg.bin" in extracted.name:
                    roots = vendor_bin2cfg.read_binary_cfg(
                        extracted.read_bytes())
                    text = "\n".join(r.to_string() for r in roots)
                else:
                    text = extracted.read_bytes().decode(
                        "utf-8-sig", errors="replace")
                root = cfgparse.parse(text)
            except Exception:
                # Einzelne kaputte Datei: den Rest der Pak trotzdem werten
                info.note = "some files could not be read"
                continue
            parsed += 1
            info.pairs |= collect_pairs(root, vanilla_index)
            info.base_names |= base_segments(rel)
        # Sicherheitsnetz: repak "erfolgreich", aber Dateien fehlen (z.B.
        # ein nicht abgefangenes Muster-Problem) -> nie stilles Alles-ok.
        if parsed < info.n_cfg and not info.note:
            info.note = "some files could not be read"
    return info


def pairs_from_patches(patches: dict[str, str]) -> set[tuple[str, str]]:
    """Fussabdruck eines Reglers: (Top-Struct, Blattname)-Paare aus den von
    tweaks.build_patches erzeugten Patch-Texten.

    "Type" fliegt heraus: einzelne Builder emittieren den Feldtyp als
    unveraenderten ANKER neben dem eigentlichen Wert (z.B. die
    Hearing-Patches). Im Fussabdruck wuerde ('Default', 'Type') sonst jede
    Mod treffen, die irgendein Struct namens Default mit einem Type-Feld
    patcht (nachgewiesen: RelationPrototypes). Die Mod-Seite behaelt ihre
    Type-Paare — nur der Fussabdruck verzichtet darauf."""
    pairs: set[tuple[str, str]] = set()
    for text in patches.values():
        pairs |= collect_pairs(cfgparse.parse(text))
    return {(top, leaf) for top, leaf in pairs if leaf != "Type"}
