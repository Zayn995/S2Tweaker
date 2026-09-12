"""Scan other mods and compare their cfg changes with control footprints.

Read only GameData/DLCGameData cfg entries. Match (top-level struct, leaf)
to cover arbitrary patch filenames and legacy refkey targets. For full
struct copies, omit values equal to known vanilla baselines.

Top-level Weight is item mass; nested loot weights have a separate marker.
Positional loot lists also depend on item identity and ordering.

Read loose cfg entries from the Pak even when sibling IoStore containers
exist. Cooked assets in .ucas/.utoc remain uninspected. Merge duplicated
Workshop layouts by display name and source."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import cfgparse, loot_conflicts, pakio, vendor_bin2cfg
from .cfgparse import CfgStruct

# Include sibling DLC configs when reporting changed configuration files.
GAMEDATA_MARKERS = ("/GameLite/GameData/", "/GameLite/DLCGameData/")

# Notes appear verbatim in reports; avoid '; ' because _join_notes uses it as a separator.
NO_CFG_NOTE = "no config changes (probably meshes, textures or audio)"
PACKED_NOTE = ("also ships packed assets (IoStore .ucas/.utoc) this tool "
               "can't inspect - only its config changes are compared")
PACKED_NO_CFG_NOTE = ("no config overrides in its .pak part - its packed "
                      "assets (IoStore .ucas/.utoc) can't be inspected")

_INDEX_KEY = re.compile(r"^\[\d+\]$")
_EFFECT_LISTS = frozenset({"EffectPrototypeSIDs", "ShouldShowEffects"})
EFFECT_LIST_LEAF = "@effect-list"


class _VanillaIndex(dict):
    """Keep the leaf index API plus position-sensitive loot identities."""

    def __init__(self, game_data_dir=None):
        super().__init__()
        self.loot_layouts: dict[str, loot_conflicts.LootLayout] = {}
        self.effect_lists: dict[str, dict[str, dict[str, str]]] = {}
        self._spawn_source = (Path(game_data_dir) / "SpawnActorPrototypes.cfg"
                              if game_data_dir is not None else None)
        self._spawn_indexed = False

    def index_stash_assignments(self):
        """Read relevant container references only when a mod touches them.

        SpawnActorPrototypes is much larger than the ordinary cfg trees.
        Reuse the bounded streaming reader from the stash builder instead
        of parsing the whole file or loading it for every ordinary scan.
        """
        if self._spawn_indexed:
            return
        self._spawn_indexed = True
        if self._spawn_source is None or not self._spawn_source.is_file():
            return
        from .loot_extensions import _stream_spawn_containers
        try:
            for name, top in _stream_spawn_containers(self._spawn_source):
                assignments = top.children.get("ItemGeneratorSettings")
                if assignments is None:
                    continue
                for node in assignments.walk():
                    value = node.values.get("PrototypeSID")
                    if value is not None:
                        self.setdefault((name.split("#", 1)[0], "PrototypeSID"),
                                        set()).add(_norm_value(value))
        except OSError:
            # Missing/unreadable dev data remains conservatively unknown,
            # like other unavailable trees in build_vanilla_index.
            return

# Use already known cached GameData properties for full-copy baseline comparisons.
_GD_TREES = (
    "obj", "items", "difficulty", "weightparams", "effectmax", "effects",
    "floatproviders", "weaponsettings", "weaponattributes", "trade",
    "holdbreath", "weapongeneral", "corevars", "stashes", "aiglobals",
    "hearingsensors", "visionscanners", "camerashake", "artifactspawners",
    "passivedetectors", "fasttravel", "boolproviders", "abilities", "melee",
    "weatherselection", "itemgenerators", "relations",
    # Index unbinarized core overrides so full copies do not mark unchanged values.
    "corevarscustom", "quicksave",
    # NPC target selection and cover profiles.
    "enemyevaluators", "coverevaluators",
    # Mutant scent detection.
    "flairsensors",
    # Squad expansion, A-Life policy and faction expansion.
    "needspresets", "alifepolicy", "alifefactions",
    # Index barbed wire, destructibles, physics, weather chains and sky constants.
    "barbedwire", "destructibles", "physicsinteractions", "weatherchains",
    "singletonconstants",
    # World loot piles.
    "packofitems",
)


@dataclass
class ModInfo:
    """Scan result for one external Pak."""

    name: str                       # Filename without .pak.
    path: Path
    readable: bool = True
    note: str = ""                  # For example, "contains data I can't read".
    n_cfg: int = 0                  # CFG files found under GameData.
    pairs: set = field(default_factory=set)       # {(top-level struct, leaf name)}
    base_names: set = field(default_factory=set)  # {"DifficultyPrototypes", ...}
    source: str = "~mods"           # "~mods" | "workshop"
    packed_assets: bool = False     # Adjacent .ucas/.utoc files for IoStore assets.
    n_paks: int = 1                 # Greater than 1 when merge_same_name() combined entries.


def find_mod_paks(mods_dir: Path, exclude_names: set[str]) -> list[Path]:
    """Find external Paks recursively under ~mods, excluding this tool's output."""
    if not mods_dir.is_dir():
        return []
    excl = {n.lower() for n in exclude_names}
    return sorted(
        p for p in mods_dir.rglob("*.pak")
        if p.name.lower() not in excl
    )


def find_workshop_paks(workshop_dir: Path | None) -> list[Path]:
    """Find subscribed Steam Workshop Paks recursively in their original locations."""
    if workshop_dir is None or not workshop_dir.is_dir():
        return []
    return sorted(workshop_dir.rglob("*.pak"))


def workshop_mod_name(pak: Path, workshop_dir: Path) -> str:
    """Derive the Workshop name from its last Stalker2/Mods/ path segment or item ID.

    Distinguish NewContent Paks so separate parts of a mod have distinct labels."""
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
    """Detect sibling IoStore containers whose cooked assets the scan cannot inspect.

    The Pak's loose cfg entries remain readable."""
    return (pak.with_suffix(".utoc").is_file()
            or pak.with_suffix(".ucas").is_file())


def _join_notes(*notes: str) -> str:
    """Join distinct, nonempty notes with '; '."""
    seen: list[str] = []
    for note in notes:
        for part in note.split("; "):
            part = part.strip()
            if part and part not in seen:
                seen.append(part)
    return "; ".join(seen)


def merge_same_name(infos: list["ModInfo"]) -> list["ModInfo"]:
    """Merge Paks sharing a display name and source.

    Union changed pairs and basenames, retain the first path/order, and use the
    largest cfg count. Any readable component makes the merged entry readable."""
    merged: dict[tuple[str, str], ModInfo] = {}
    for info in infos:
        key = (info.name, info.source)
        first = merged.get(key)
        if first is None:
            merged[key] = info
            continue
        first.n_paks += 1
        first.pairs |= info.pairs
        first.base_names |= info.base_names
        first.n_cfg = max(first.n_cfg, info.n_cfg)
        first.readable = first.readable or info.readable
        first.packed_assets = first.packed_assets or info.packed_assets
        first.note = _join_notes(first.note, info.note)
    out = list(merged.values())
    for info in out:
        if info.n_paks == 1:
            continue
        if info.n_cfg:
            # Remove a no-config note when another component contains configs.
            info.note = "; ".join(
                p for p in info.note.split("; ")
                if p not in (NO_CFG_NOTE, PACKED_NO_CFG_NOTE))
        info.note = _join_notes(
            info.note, f"{info.n_paks} pak files with this name were "
                       "merged into one entry")
    return out


def _short_error(exc: Exception) -> str:
    """Reduce verbose extraction errors to one short display line."""
    text = str(exc).strip()
    if "version unsupported" in text or "trying version" in text:
        return "not a readable .pak file"
    first = text.splitlines()[0] if text else "unknown error"
    return first[:120]


def _split_marker(path: str) -> str | None:
    """Return the path after the GameData/DLCGameData marker, or None."""
    norm = path.replace("\\", "/")
    for marker in GAMEDATA_MARKERS:
        if marker in norm:
            return norm.split(marker, 1)[1]
    return None


def _is_cfg_name(name: str) -> bool:
    """Recognize .cfg anywhere in filenames, including Base.cfg_patch_<Mod>."""
    return ".cfg" in name


def _norm_value(raw: str) -> str:
    """Normalize equivalent numeric spellings and case-insensitive boolean literals."""
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


def _effect_lists(top: CfgStruct) -> dict[str, dict[str, str]]:
    """Direct item effect lists; nested weight-threshold lists stay separate."""
    out = {}
    for key in _EFFECT_LISTS:
        child = top.children.get(key)
        if child is not None:
            out[key] = {slot: _norm_value(value)
                        for slot, value in child.values.items()}
        elif key in top.values:
            out[key] = {}              # explicit list clear
    return out


def _effect_list_pairs(root: CfgStruct, vanilla=None, *, footprint=False) -> set:
    """Relate wildcard appends to foreign effect-list rewrites.

    An independent native [*] append preserves existing entries. Numeric
    replacements, full list replacements and clears can affect the same
    item and receive a qualified marker, regardless of array key spelling.
    """
    pairs = set()
    for top_key, top in root.children.items():
        own = top_key.split("#", 1)[0]
        attrs = top.attr_dict()
        ref = attrs.get("refkey", "").strip()
        names = {own}
        if ref and not _INDEX_KEY.fullmatch(ref):
            names.add(ref)
        current = _effect_lists(top)
        if footprint:
            if current:
                pairs.update((name, EFFECT_LIST_LEAF) for name in names)
            continue
        original = vanilla.get(own) if vanilla is not None else None
        full_copy = original is not None and "bpatch" not in attrs
        if original is None and vanilla is not None and ref in names:
            original = vanilla.get(ref)
        changed = bool(full_copy and original.keys() - current.keys())
        for list_name, values in current.items():
            child = top.children.get(list_name)
            sparse = ("bpatch" in attrs and child is not None
                      and "bpatch" in child.attr_dict())
            if sparse and values and set(values) == {"[*]"}:
                continue              # two independent appends coexist
            old = original.get(list_name) if original is not None else None
            if old is None:
                changed = True
            elif sparse:
                changed |= any(old.get(slot) != value for slot, value in values.items())
            else:
                changed |= values != old
        if changed:
            pairs.update((name, EFFECT_LIST_LEAF) for name in names)
    return pairs


def build_vanilla_index(gd) -> dict[tuple[str, str], set[str]]:
    """Index normalized vanilla values by (top-level struct, leaf) across known files."""
    index = _VanillaIndex(getattr(gd, "dir", None))
    for attr in _GD_TREES:
        try:
            tree = getattr(gd, attr)
        except Exception:
            continue                     # Allow missing files in the development dump.
        if attr == "itemgenerators":
            index.loot_layouts = loot_conflicts.build_loot_index(tree)
        elif attr == "items":
            index.effect_lists = {name.split("#", 1)[0]: _effect_lists(top)
                                  for name, top in tree.children.items()}
        for top_key, top in tree.children.items():
            top_name = top_key.split("#")[0]
            for node in top.walk():
                for key, value in node.values.items():
                    index.setdefault((top_name, key), set()).add(
                        _norm_value(value))
    return index


def collect_pairs(root: CfgStruct,
                  vanilla_index: dict | None = None) -> set[tuple[str, str]]:
    """Collect (top-level struct, leaf) pairs from parsed cfg.

    Remove duplicate-name suffixes, include legacy refkey targets, and exclude
    known unchanged values in full copies. Treat only top-level Weight as mass."""
    pairs: set[tuple[str, str]] = set()
    for top_key, top in root.children.items():
        if (isinstance(vanilla_index, _VanillaIndex)
                and "ItemGeneratorSettings" in top.children):
            vanilla_index.index_stash_assignments()
        own = top_key.split("#")[0]
        names = {own}
        attrs = top.attr_dict()
        refkey = (attrs.get("refkey") or "").strip()
        if refkey and not _INDEX_KEY.fullmatch(refkey):
            names.add(refkey)
        check_vanilla = (vanilla_index is not None
                         and "bpatch" not in attrs)
        effect_nodes = {id(top.children[key]) for key in _EFFECT_LISTS
                        if key in top.children}
        for node in top.walk():
            for key, value in node.values.items():
                if (id(node) in effect_nodes
                        and (key == "[*]" or _INDEX_KEY.fullmatch(key))):
                    # Bare array indices lose the list identity and make
                    # two independent [*] appends look like a conflict.
                    continue
                if key == "Weight" and node is not top:
                    continue
                if check_vanilla:
                    # Compare against the struct's own vanilla identity first; use its refkey
                    # target only for unknown legacy names. Comparing both would misclassify
                    # legitimate inherited overrides as changes.
                    vals = vanilla_index.get((own, key))
                    if vals is None and refkey in names:
                        vals = vanilla_index.get((refkey, key))
                    if vals is not None and _norm_value(value) in vals:
                        continue         # Whole-file copy repeats vanilla values.
                for name in names:
                    pairs.add((name, key))
    # Original values can be the same set after an item moves to another
    # array index. Compare those lists by position as well; lottery Weight
    # gets its own marker and cannot collide with an item's mass in kg.
    pairs |= loot_conflicts.changed_pairs(
        root, getattr(vanilla_index, "loot_layouts", None))
    pairs |= _effect_list_pairs(root, getattr(vanilla_index, "effect_lists", None))
    return pairs


def base_segments(rel_after_gamedata: str) -> set[str]:
    """Return GameData path segments without .cfg suffixes for cheap scan prefilters.

    Actual matching still uses struct/leaf pairs."""
    return {part.split(".cfg")[0]
            for part in rel_after_gamedata.split("/") if part}


def _escape_glob(entry: str) -> str:
    """Escape opening brackets for glob-based extraction filters.

    Brackets in literal paths must not become character classes."""
    return entry.replace("\\", "/").replace("[", "[[]")


def scan_pak(pak: Path, progress=None, vanilla_index: dict | None = None) -> ModInfo:
    """Scan another mod's pak: list, extract and parse CFG entries."""
    info = ModInfo(name=pak.stem, path=pak)
    # Sibling IoStore containers do not prevent reading loose cfg patches from the Pak.
    info.packed_assets = is_iostore(pak)

    try:
        entries = pakio.list_pak(pak)
    except Exception as exc:  # Report unreadable Paks without aborting the scan.
        info.readable = False
        info.note = f"contains data I can't read ({_short_error(exc)})"
        return info

    cfg_entries = [e for e in entries
                   if _split_marker(e) is not None
                   and _is_cfg_name(e.replace("\\", "/").split("/")[-1])]
    info.n_cfg = len(cfg_entries)
    if not cfg_entries:
        info.note = PACKED_NO_CFG_NOTE if info.packed_assets else NO_CFG_NOTE
        return info

    with tempfile.TemporaryDirectory(prefix="s2tweaker_scan_") as tmp:
        out = Path(tmp)
        if progress:
            progress(f"Scanning {pak.name} "
                     f"({info.n_cfg} config file{'s' if info.n_cfg != 1 else ''}) ...")
        try:
            # Extract all selected cfg entries together, never the entire Pak.
            pakio.unpack_many(pak, out,
                              [_escape_glob(e) for e in cfg_entries])
        except Exception as exc:
            info.readable = False
            info.note = f"contains data I can't read ({_short_error(exc)})"
            return info
        # Collect extracted files without assuming a fixed mount-point layout.
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
                # Continue scanning other entries after an individual parse failure.
                info.note = "some files could not be read"
                continue
            parsed += 1
            info.pairs |= collect_pairs(root, vanilla_index)
            info.base_names |= base_segments(rel)
        # Report missing requested files even if extraction otherwise succeeded.
        if parsed < info.n_cfg and not info.note:
            info.note = "some files could not be read"
    if info.packed_assets:
        info.note = _join_notes(info.note, PACKED_NOTE)
    return info


def pairs_from_patches(patches: dict[str, str]) -> set[tuple[str, str]]:
    """Collect generated (top-level struct, leaf) patch footprints.

    Omit unchanged Type anchors from this side of the comparison; otherwise
    unrelated Default structs sharing a Type field could produce false conflicts."""
    pairs: set[tuple[str, str]] = set()
    for text in patches.values():
        root = cfgparse.parse(text)
        # Source-side structural markers describe a foreign replacement.
        # A generated append using named sibling groups does not depend
        # on existing array indices; its footprint gets only the explicit
        # positional dependencies below.
        pairs |= {(top, leaf) for top, leaf in collect_pairs(root)
                  if leaf != loot_conflicts.LAYOUT_LEAF}
        pairs |= loot_conflicts.layout_dependencies(root)
        pairs |= _effect_list_pairs(root, footprint=True)
    return {(top, leaf) for top, leaf in pairs if leaf != "Type"}
