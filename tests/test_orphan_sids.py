"""Validate generated patch structure and SID references against installed data.

Check balanced structs, matching named identities, valid bpatch/refkey targets,
new-node uniqueness and referenced SIDs. Build broad probes, including scope,
caliber and quest changes, to catch references invalidated by game updates."""
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GAMELITE = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite"
VANILLA = GAMELITE / "GameData"

from s2tweaker.gamedata import GameData
from s2tweaker import cfgparse
from s2tweaker.tweaks import Settings, build_patches, swappable_calibers
from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS

gd = GameData(str(VANILLA))
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


# Probe every control, using special values for zero baselines and capped defaults.
SPECIAL = {
    "fall_damage_pct": 50.0, "fast_travel_lock": 0.0, "slow_run_threshold_pct": 25.0,
    "evening_start_hour": 22.0, "armor_deflect_chance_pct": 50.0,
    "npc_weapon_rank_add": 2.0, "scope_sway_pct": 50.0,
    "trader_min_durability_pct": 0.0, "hud_compass": 2.0, "hud_crosshair": 2.0,
    "hud_body_markers": 2.0, "hud_stash_markers": 2.0, "pistol_slot_level": 3.0,
}

kw = {}
_default = Settings()
for field in sorted(set(SLIDER_FIELDS.values()) | set(CHECK_FIELDS.values())):
    value = getattr(_default, field)
    if isinstance(value, bool):
        kw[field] = not value
    elif field in SPECIAL:
        kw[field] = SPECIAL[field]
    elif isinstance(value, (int, float)):
        probe = value * 2 if value else 1.0
        kw[field] = (int(probe) or 1) if isinstance(value, int) else probe

# Include scope-derived effects and caliber projectile references chosen from game data.
scope_sid = sorted(gd.scope_effects())[0]
kw["scope_overrides"] = {scope_sid: {"zoom": 1.5, "penalty": 0.5}}

_tables = swappable_calibers(gd)
_weapon = sorted(gd.player_weapons())[0]
_own = gd.weapon_caliber(_weapon)
_other = sorted(c for c in _tables if c != _own and _tables[c])[0]
kw["weapon_calibers"] = {_weapon: _other}

# Include player/faction and faction/faction runtime nodes and launch scripts.
kw["faction_relations"] = {k: v for k, v in (
    (gd.relation_pair_key("Duty", "Player"), 800),
    (gd.relation_pair_key("Duty", "Freedom"), -800)) if k}

# Include simultaneous-job probes to validate their quest references.
kw["repeatable_jobs_multi"] = True

t0 = time.time()
PATCHES = build_patches(gd, Settings(mod_name="S2Tweaker", **kw))
build_s = time.time() - t0
check(len(PATCHES) > 50,
      f"Broad probe generates {len(PATCHES)} patch files ({build_s:.1f}s)")


# --- 1) Read structure ---
BEGIN = re.compile(r"^(\S+)\s*:\s*struct\.begin\s*(\{[^}]*\})?\s*$")
LEAF = re.compile(r"^\s*([A-Za-z_\[][A-Za-z0-9_\]\[]*)\s*=\s*(.*?)\s*$")


def scan(text):
    """Return top-level structs, SID references and structural-balance errors.

    Struct entries include name, attributes and line; references include
    source struct, field and target."""
    tops, refs, problems = [], [], []
    depth, current = 0, None
    parents = []
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        m = BEGIN.match(stripped)
        if m:
            if depth == 0:
                current = m.group(1)
                tops.append((current, m.group(2) or "", n))
            depth += 1
            parents.append(m.group(1))
            continue
        if stripped == "struct.end":
            depth -= 1
            if parents:
                parents.pop()
            if depth < 0:
                problems.append(f"Line {n}: unexpected struct.end")
                depth = 0
            continue
        leaf = LEAF.match(line)
        if leaf and current:
            key, value = leaf.group(1), leaf.group(2)
            if key.startswith("[") and parents and parents[-1] == "Descriptions":
                key = "Description"  # localization key, not a prototype reference
            refs.append((current, key, value, depth, n))
    if depth != 0:
        problems.append(f"Missing at end of file: {depth} struct.end")
    return tops, refs, problems


# Enumerate actual SID-reference fields explicitly; localization keys such as
# Title/Description do not reference cfg structs.
REF_KEYS = {
    "ItemPrototypeSID", "ItemGeneratorPrototypeSID", "PrototypeSID",
    "AgentPrototypeSID", "QuestSID", "EffectSID",
    "FalseEffectSID", "WeatherSID", "GlobalVariablePrototypeSID",
    "StickinessAimAssistConeSID", "SnappingAimAssistConeSID",
    "MovingTrackingAimAssistConeSID", "StationaryTrackingAimAssistConeSID",
    "NextDialogSID",               # Include dialogue-menu targets.
    "JournalQuestSID", "JournalQuestStageSID",
}
# Lists whose indexed values are SID references.
REF_LISTS = {"NodesToCleanUpResults", "AmmoTypeProjectiles"}
NOT_A_SID = {"", "empty", "Empty", "None", "true", "false", "True", "False"}


def references(refs):
    """Filter raw parsed fields to actual SID references."""
    out = []
    for struct, key, value, depth, line in refs:
        if "::" in value or value in NOT_A_SID:
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            continue          # Numbers, literals, paths.
        # Top-level SID is an identity; nested SID is a reference.
        if key == "SID" and depth >= 2:
            out.append((struct, key, value, line))
        elif key in REF_KEYS:
            out.append((struct, key, value, line))
        elif key.startswith("[") and value:
            out.append((struct, key, value, line))
    return out


# Extract launch-script targets from the last word of XStartQuestNodeBySID lines.
SCRIPT_CMDS = ("XStartQuestNodeBySID", "XStartQuestBySID",
               "XExecuteAdditionalScript")


def script_references(text):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*\[[^\]]*\]\s*=\s*(\S+)\s+(\S+)\s*$", line)
        if m and m.group(1) in SCRIPT_CMDS:
            out.append(("ScriptsArray", m.group(1), m.group(2), n))
    return out


# Index nested as well as top-level names, including indented weather SIDs.
TOP_RE = re.compile(r"^\s*([A-Za-z0-9_\[][^\s:]*)\s*:\s*struct\.begin", re.M)
SID_RE = re.compile(r"^\s*SID\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", re.M)

# Defer very large mostly unrelated files; search them on demand before
# reporting an unresolved reference.
INDEX_SKIP = {"SpawnActorPrototypes.cfg", "DialogPrototypes.cfg",
              "MeshGeneratorPrototypes.cfg", "BodyMeshPrototypes.cfg",
              "GroomGeneratorPrototypes.cfg"}

t0 = time.time()
KNOWN = set()
_files = 0
for f in GAMELITE.rglob("*.cfg"):
    if f.name in INDEX_SKIP:
        continue
    text = f.read_text(encoding="utf-8-sig", errors="replace")
    KNOWN.update(TOP_RE.findall(text))
    KNOWN.update(SID_RE.findall(text))
    _files += 1
index_s = time.time() - t0
check(len(KNOWN) > 100_000,
      f"Index covering {_files} game files: {len(KNOWN)} known names "
      f"({index_s:.1f}s)")


_big_texts: dict[Path, str] = {}


def resolve_late(name: str) -> bool:
    """Resolve unknown names from lazily loaded large files, caching their content."""
    needle = re.compile(rf"^\s*{re.escape(name)}\s*:\s*struct\.begin|"
                        rf"^\s*SID\s*=\s*{re.escape(name)}\s*$", re.M)
    for big in INDEX_SKIP:
        for f in GAMELITE.rglob(big):
            if f not in _big_texts:
                _big_texts[f] = f.read_text(encoding="utf-8-sig", errors="replace")
            if needle.search(_big_texts[f]):
                KNOWN.add(name)
                return True
    return False

_base_cache: dict[Path, set[str]] = {}


def base_names(path: Path) -> set[str] | None:
    """Read top-level struct names from the prototype-family target file."""
    if path not in _base_cache:
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        _base_cache[path] = {m.group(1) for m in
                             re.finditer(r"^([A-Za-z0-9_\[][^\s:]*)\s*:\s*struct\.begin",
                                         text, re.M)}
    return _base_cache[path]


PATCH_NAME = re.compile(r"(.+?)(?:\.cfg)?_patch_[^.]+\.cfg$")


def base_file(patch_path: str) -> Path:
    """Infer the vanilla family from standard direct or family-directory patch paths.

    A leading // selects the Content-relative edition branch."""
    if patch_path.startswith("//"):
        p = GAMELITE.parent / patch_path[2:]
    else:
        p = VANILLA / patch_path
    m = PATCH_NAME.match(p.name)
    if m is None:
        # Allow arbitrary new filenames within a prototype-family directory.
        return p.parent.with_suffix(".cfg")
    stem = m.group(1)
    if p.parent.name == stem:
        return p.parent.with_suffix(".cfg")
    return p.parent / f"{stem}.cfg"


# --- 3) The four checks ---
def audit(patches: dict[str, str]) -> list[str]:
    """Return all findings across the complete patch set."""
    bad = []
    # All explicitly generated new nodes count as existing targets.
    own = set()
    for path, text in patches.items():
        for name, attrs, _line in scan(text)[0]:
            if "bpatch" not in attrs or "refkey=" in attrs:
                own.add(name)
        # Journal stages are definitions nested inside a new journal.
        # A launcher SID is only a reference: its [index] name differs.
        for top in cfgparse.parse(text).children.values():
            if "bpatch" not in top.attrs:
                for node in top.walk():
                    if not node.name.startswith("[") and node.values.get("SID") == node.name:
                        own.add(node.name)

    for path, text in sorted(patches.items()):
        tops, raw, problems = scan(text)
        bad += [f"{path}: {p}" for p in problems]
        if text.count("{") != text.count("}") or text.count("[") != text.count("]"):
            bad.append(f"{path}: unmatched braces")

        base = base_file(path)
        names = base_names(base)
        if names is None:
            bad.append(f"{path}: target file {base.name} does not exist")
            continue

        for name, attrs, line in tops:
            refkey = re.search(r"refkey=([^;}\s]+)", attrs)
            if refkey:
                if refkey.group(1) not in names and refkey.group(1) not in KNOWN:
                    bad.append(f"{path}:{line} refkey={refkey.group(1)} "
                               f"does not exist")
            elif "bpatch" in attrs:
                if name not in names:
                    bad.append(f"{path}:{line} {name} is absent from "
                               f"{base.name} (renamed? Patch has no matching target)")
            elif name in names:
                bad.append(f"{path}:{line} {name} is a NEW node "
                           f"written, but already exists in {base.name}")

        # Require SID/name equality only for named structs; indexed structs have separate SIDs.
        for struct, key, value, depth, line in raw:
            if (key == "SID" and depth == 1 and value
                    and not struct.startswith("[") and value != struct):
                bad.append(f"{path}:{line} SID = {value} in Struct {struct}")

        # Orphaned references.
        for struct, key, value, line in references(raw) + script_references(text):
            if value in KNOWN or value in own:
                continue
            if resolve_late(value):
                continue
            bad.append(f"{path}:{line} {struct}.{key} points to "
                       f"'{value}' - does not exist anywhere")
    return bad


t0 = time.time()
findings = audit(PATCHES)
audit_s = time.time() - t0
n_tops = sum(len(scan(t)[0]) for t in PATCHES.values())
n_refs = sum(len(references(scan(t)[1])) + len(script_references(t))
             for t in PATCHES.values())

check(not findings,
      f"{n_tops} top-level structs and {n_refs} SID references are valid"
      + ("\n      " + "\n      ".join(findings[:25]) if findings else ""))
print(f"      ({audit_s:.1f}s for {len(PATCHES)} patch files)")


# Validate all discovered repeatable-job graph anchors.
givers = gd.repeatable_quest_givers()
check(len(givers) == 8,
      "Eight job givers found ("
      + ", ".join(sorted(g["quest"] for g in givers)) + ")")

# Every discovered node name must resolve in installed data.
ANCHOR_KEYS = ("quest_sid", "cap_key", "dialog_key", "accept",
               "cleanup_sid", "end_sid")
lost = sorted({f"{g['quest']}.{k}={g[k]}" for g in givers for k in ANCHOR_KEYS
               if g.get(k) and g[k] not in KNOWN and not resolve_late(g[k])})
check(not lost,
      f"All {len(givers) * len(ANCHOR_KEYS)} quest anchors for the eight givers "
      f"exist in the game data" + (f" - MISSING: {lost}" if lost else ""))

quest_patch = next((t for p, t in PATCHES.items()
                    if p.endswith("QuestNodePrototypes_patch_S2Tweaker.cfg")), "")
tops = scan(quest_patch)[0]
new_nodes = {n for n, attrs, _l in tops if "bpatch" not in attrs}
# Existing-node bpatch files must not contain new quest nodes.
check(not new_nodes and len(tops) >= 8 * 3,
      f"The quest patch file contains {len(tops)} existing nodes and no new ones")
# New runtime-relation nodes belong in a separate non-bpatch file.
rel_patch = next((t for p, t in PATCHES.items() if p.endswith("_Relations.cfg")), "")
rel_nodes = {n for n, attrs, _l in scan(rel_patch)[0]}
check(rel_nodes == {"S2T_Relations_Start", "S2T_Rel_01", "S2T_Rel_02"}
      and "{bpatch}" not in rel_patch,
      f"Runtime relationships are separate, without {{bpatch}} ({sorted(rel_nodes)})")
new_nodes |= rel_nodes
# New node names must not collide with existing game nodes.
collide = sorted(n for n in new_nodes if n in KNOWN)
check(not collide, "No new nodes collide with vanilla nodes"
      + (f" - KOLLISION: {collide}" if collide else ""))


# Verify the validator itself detects deliberately malformed references/structure.
sample = ("RSQ01_SetTimer : struct.begin {bpatch}\n"
          "   InGameHours = 48\n"
          "struct.end\n")
probe_path = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"

check(not audit({probe_path: sample}), "Self-test: valid patch is accepted")

check(any("has no matching target" in f for f in audit(
          {probe_path: sample.replace("RSQ01_SetTimer", "RSQ01_SetTimerXX")})),
      "Self-test: detects renamed struct")

broken = ("RSQ01_S2T_ClearAccept : struct.begin\n"
          "   SID = RSQ01_S2T_ClearAccept\n"
          "   NodesToCleanUpResults : struct.begin\n"
          "      [0] = RSQ01_Technical_GetQuestXX\n"
          "   struct.end\n"
          "struct.end\n")
check(any("does not exist anywhere" in f for f in audit({probe_path: broken})),
      "Self-test: detects reference to an invented SID")

check(any("SID = " in f for f in audit(
          {probe_path: sample.replace("   InGameHours = 48",
                                      "   SID = SomethingElse")})),
      "Self-test: detects incorrect SID field")

check(any("struct.end" in f for f in audit(
          {probe_path: sample.replace("struct.end\n", "")})),
      "Self-test: detects missing struct.end")

print(f"\n=== {ok} checks passed "
      f"({n_tops} Structs, {n_refs} references, {len(KNOWN)} known names) ===")
