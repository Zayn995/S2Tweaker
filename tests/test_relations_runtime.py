"""Check runtime faction quest generation and the vanilla mechanisms it uses.

Validate ChangeRelationships targets, absolute values and OnGameLaunch output.
The generator does not modify RelationVersion."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, summarize,
                              PLAYER_TARGET_GUID, RELATIONS_QUEST_SID,
                              RELATIONS_START_SID)
from s2tweaker.gui import FACTION_CHOICES

gd = GameData(str(VANILLA))
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


QUEST_TEXT = (VANILLA / "QuestNodePrototypes.cfg").read_text(
    encoding="utf-8-sig", errors="replace")

# Verify supporting vanilla quest/script patterns.
n_nodes = QUEST_TEXT.count("EQuestNodeType::ChangeRelationships")
check(n_nodes > 1000,
      f"EQuestNodeType::ChangeRelationships is a vanilla mechanic ({n_nodes} Knoten)")

launch_dir = VANILLA / "Scripts" / "OnGameLaunch"
launch_files = sorted(launch_dir.glob("*.cfg"))
check(len(launch_files) > 100,
      f"Scripts/OnGameLaunch is a vanilla directory ({len(launch_files)} files)")
check(any("XStartQuestNodeBySID" in f.read_text(encoding="utf-8-sig",
                                                errors="replace")
          for f in launch_files),
      "The game itself uses XStartQuestNodeBySID there")

# Absolute relation targets must match existing node forms and value scales.
blocks = re.findall(r"^(\S+) : struct\.begin.*?\n(.*?)\n^struct\.end",
                    QUEST_TEXT, re.M | re.S)


def val(body, key):
    m = re.search(rf"^\s*{key}\s*=\s*(\S*)\s*$", body, re.M)
    return m.group(1) if m else None


rel_blocks = [b for _n, b in blocks
              if "EQuestNodeType::ChangeRelationships" in b]
absolute = [b for b in rel_blocks
            if val(b, "UsePreset") == "false" and val(b, "UseDeltaValue") == "false"]
check(len(absolute) > 50,
      f"Absolute assignment is used in vanilla ({len(absolute)} Knoten)")
values = {val(b, "RelationshipValue") for b in absolute}
check("-800" in values,
      f"and uses the same scale (including -800; found: {sorted(values)[:6]})")

# Address Player by GUID as the first target.
firsts = re.findall(r"^\s*FirstTargetSID\s*=\s*(\S*)\s*$", QUEST_TEXT, re.M)
seconds = re.findall(r"^\s*SecondTargetSID\s*=\s*(\S*)\s*$", QUEST_TEXT, re.M)
check(firsts.count(PLAYER_TARGET_GUID) > 1000 and
      seconds.count(PLAYER_TARGET_GUID) == 0,
      f"The player GUID appears {firsts.count(PLAYER_TARGET_GUID)} times as the first "
      f"and never as the second target")
# Recognize 32-character hexadecimal GUIDs separately from named factions.
GUID = re.compile(r"[0-9A-F]{32}")
named_first = [v for v in firsts
               if v and not GUID.fullmatch(v)
               and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v)]
check(len(named_first) > 10,
      f"A faction name as the first target occurs in vanilla "
      f"({len(named_first)}x, u.a. {sorted(set(named_first))[:5]}) - "
      f"Baseline for faction vs faction")

# Every offered faction must exist in the game data.
pairs = gd.relation_pairs()
unknown = [sid for sid, _label in FACTION_CHOICES
           if gd.relation_pair_key(sid, "Player") is None]
check(not unknown,
      f"All {len(FACTION_CHOICES)} available factions have a "
      f"Player pair{unknown}")

# --- 3) Disabled, or no pairs: no output ---
duty_player = gd.relation_pair_key("Duty", "Player")
duty_freedom = gd.relation_pair_key("Duty", "Freedom")

def files(**kw):
    return build_patches(gd, Settings(mod_name="S2Tweaker", **kw))


check(not [p for p in files(faction_relations={duty_player: 800})
           if "QuestPrototypes" in p or "OnGameLaunch" in p],
      "Without the toggle, neither quest nor startup script is generated")
check(not [p for p in files(relations_runtime=True)
           if "QuestPrototypes" in p or "OnGameLaunch" in p],
      "Enabled without a modified pair also produces nothing")
# A target equal to vanilla is not a changed pair.
check(not [p for p in files(relations_runtime=True,
                            faction_relations={duty_player: pairs[duty_player]})
           if "OnGameLaunch" in p],
      "A pair at vanilla produces no node")

# Enable runtime updates with two changed pairs.
out = files(relations_runtime=True,
            faction_relations={duty_player: 800, duty_freedom: -800})
quest_patch = next(t for p, t in out.items() if p.endswith("_Relations.cfg"))
proto_patch = next(t for p, t in out.items() if "QuestPrototypes" in p)
script_patch = next(t for p, t in out.items() if "OnGameLaunch" in p)
check(True, "Nodes, quest and startup script are generated")
# New nodes belong in their own quest-family file, separate from existing-node patches.
check(not any(p.endswith("QuestNodePrototypes_patch_S2Tweaker.cfg") for p in out)
      and "{bpatch}" not in quest_patch,
      "New nodes are separate, without any {bpatch}")

nodes = re.findall(r"^(S2T_Rel_\d+) : struct\.begin(.*)$", quest_patch, re.M)
check(len(nodes) == 2, f"Exactly one node per changed pair ({len(nodes)})")
check(all(not attrs.strip() for _n, attrs in nodes),
      "New nodes carry NO {bpatch} because there is nothing to merge")

def node_body(sid):
    m = re.search(rf"^{sid} : struct\.begin.*?\n(.*?)\n^struct\.end",
                  quest_patch, re.M | re.S)
    return m.group(1)


bodies = {sid: node_body(sid) for sid, _ in nodes}
player_node = next(b for b in bodies.values()
                   if val(b, "FirstTargetSID") == PLAYER_TARGET_GUID)
check(val(player_node, "SecondTargetSID") == "Duty",
      "Player pair: player GUID first, faction second")
check(val(player_node, "RelationshipValue") == "800",
      "Slider value is emitted unchanged as RelationshipValue")
check(val(player_node, "UseDeltaValue") == "false"
      and val(player_node, "UsePreset") == "false",
      "Absolute assignment rather than delta or preset")
check(val(player_node, "SetFactionRelationshipAsPersonal") == "false"
      and val(player_node, "ShouldLockPersonalRelationship") == "false",
      "The two special flags remain off (as in RSO and vanilla)")

ff_node = next(b for b in bodies.values()
               if val(b, "FirstTargetSID") != PLAYER_TARGET_GUID)
check({val(ff_node, "FirstTargetSID"), val(ff_node, "SecondTargetSID")}
      == {"Duty", "Freedom"},
      "Faction vs faction: both targets use names")

# --- 5) The chain is connected ---
check(all(val(b, "QuestSID") == RELATIONS_QUEST_SID for b in bodies.values()),
      f"All nodes belong to their own quest {RELATIONS_QUEST_SID}")
check(all(RELATIONS_START_SID in b for b in bodies.values()),
      "Every node depends on the start node")
start = node_body(RELATIONS_START_SID)
check(val(start, "LaunchOnQuestStart") == "true" and val(start, "StartDelay"),
      "Start node begins with the quest and waits briefly")
check(f"SID = {RELATIONS_QUEST_SID}" in proto_patch,
      "Quest appears in QuestPrototypes")
check(f"XStartQuestNodeBySID {RELATIONS_START_SID}" in script_patch,
      "Startup script launches exactly this node")
check(script_patch.lstrip().startswith("[*]"),
      "Script appends with [*] instead of occupying an index")
check("{bpatch}" not in script_patch and "{bpatch}" not in proto_patch,
      "Neither quest nor script carries {bpatch}")

# --- 6) Other behavior remains unchanged ---
check("Faction relations are also applied to a running save" in summarize(
          Settings(relations_runtime=True)),
      "Tweak list includes the toggle")
rel_patch = next(t for p, t in out.items() if "RelationPrototypes" in p)
check("Duty<->Player = 800" in rel_patch,
      "Baseline is still written for NEW saves")

# Read back the generated Pak to verify nested OnGameLaunch script paths.
import tempfile
from s2tweaker import pakio

pak = Path(tempfile.mkdtemp()) / "zzz_RelRuntimeTest_P.pak"
pakio.pack_mod(out, pak)
names = pakio.list_pak(pak)
base = "Stalker2/Content/GameLite/GameData/"
for want in ("QuestNodePrototypes/S2Tweaker_Relations.cfg",
             "QuestPrototypes/QuestPrototypes_patch_S2Tweaker.cfg",
             "Scripts/OnGameLaunch/OnGameLaunchScripts_patch_S2Tweaker.cfg"):
    check(base + want in names, f"Located in the pak under {want}")

back = pak.parent / "back"
script_in_pak = base + "Scripts/OnGameLaunch/OnGameLaunchScripts_patch_S2Tweaker.cfg"
pakio.unpack_many(pak, back, [script_in_pak])
check((back / script_in_pak).read_text(encoding="utf-8", errors="replace")
      == script_patch,
      "And extracted unchanged from the pak")

print(f"\n=== {ok} checks passed ===")
