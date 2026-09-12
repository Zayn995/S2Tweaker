"""Check faction-tree values, patches, reset, persistence and search.

Only changed pairs should be emitted; RelationVersion must remain untouched."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)
pairs = gd.relation_pairs()
assert len(pairs) == 582, f"582 pairs erwartet, {len(pairs)} gefunden"
assert gd.relation_version() == 7, gd.relation_version()

app = gui.App()
app.gd = gd
app._if_populate()
app._set_body_state(True)
app.update()

# Check initial player-block expansion and real pair rows.
player = app._if_blocks["player"]
assert player.expanded and len(player.rows) == 13, (
    player.expanded, len(player.rows))
assert app.faction_relations == {}, f"Phantom values: {app.faction_relations}"
for key, row in player.rows.items():
    assert abs(row.default - pairs[key]) < 1e-9, (key, row.default)
# Story/boss factions must not appear anywhere in the selection.
forbidden = {"ScarBoss_Faction", "KorshunovBoss_Faction", "ArenaEnemy",
             "ArenaFriend", "EnemyVarta", "VartaSIRCAA", "NoonFaustians"}
for key in app._if_vanilla:
    a, _, b = key.partition("<->")
    assert not ({a, b} & forbidden), f"Story faction in GUI: {key}"
print(f"Tree: {len(app._if_blocks)} blocks, {len(app._if_vanilla)} pairs, "
      f"Player defaults match vanilla; story factions excluded  OK")

# --- 2) Change value -> patch without RelationVersion bump ---
key = gd.relation_pair_key("Bandits", "Player")
player.rows[key].set(800)
app.update()
assert app.faction_relations == {key: 800}
p = build_patches(gd, app._collect())
rel = [k for k in p if "RelationPrototypes" in k]
assert len(rel) == 1 and len(p) == 1, list(p)
text = p[rel[0]]
assert "Bandits<->Player = 800" in text
assert "RelationVersion" not in text, "RelationVersion must no longer be bumped"
assert "{bpatch}" in text
assert any("Faction relations: 1 pair changed" in line
           for line in summarize(app._collect()))
print("Bandits<->Player 800: patch, no RelationVersion bump  OK")

# Resetting to vanilla is neutral; rollback-only does not change RelationVersion.
player.rows[key].set(pairs[key])
app.update()
assert app.faction_relations == {}
assert not build_patches(gd, app._collect()), "Must be neutral"
p = build_patches(gd, Settings(relation_rollback_factor=2.0))
text = p["RelationPrototypes/RelationPrototypes_patch_S2Tweaker.cfg"]
assert "ReputationRollbackCooldown = 7200" in text
assert "RelationVersion" not in text, (
    "Rollback alone must not modify RelationVersion")
assert text.count("= 1800") == 19, "Expected 19 faction cooldowns x2"
print("Neutral reset + rollback without version bump  OK")

# --- 4) Builder filtering: vanilla, unknown and invalid pairs ---
s = Settings(faction_relations={
    "Mutant<->Player": -800,         # Vanilla-equivalent -> remove.
    "Gibtsnicht<->Player": 500,      # Unknown -> remove.
    "Freedom<->Duty": "quatsch",     # Invalid -> remove.
})
assert not build_patches(gd, s), "Eligibility filter failed"
print("Builder eligibility filtering  OK")

# --- 5) Faction section: Duty<->Freedom (-599, irregular vanilla value) ---
duty = app._if_blocks["Duty"]
duty.expand()
app.update()
dfkey = gd.relation_pair_key("Duty", "Freedom")
drow = duty.rows[dfkey]
assert abs(drow.default - (-599)) < 1e-9, drow.default
assert "(vanilla)" in drow.value_label.cget("text"), (
    "Irregular default must be displayed as (vanilla)")
drow.set(-800)
app.update()
assert app.faction_relations == {dfkey: -800}
print("Duty group: exact irregular default -599, -800 applied  OK")

# --- 6) Reset all and JSON persistence roundtrip ---
state = json.loads(json.dumps(app._ui_state()))
app._reset_all()
app.update()
assert app.faction_relations == {} and not build_patches(gd, app._collect())
app._apply_ui_state(state)
app.update()
assert app.faction_relations == {dfkey: -800}
assert abs(duty.rows[dfkey].get() - (-800)) < 1e-9
print("Reset all and persistence roundtrip  OK")

# Remove vanilla-equivalent pairs when populating from presets.
app._reset_all()
app._apply_ui_state({"faction_relations": {dfkey: -599, "Kaputt": 1}})
assert dfkey in app.faction_relations          # Raw data before population.
app._if_populate()
app.update()
assert app.faction_relations == {}, app.faction_relations
print("Populate removes vanilla-equivalent and unknown entries  OK")

# Check search/Changed-only using fresh references after rebuilding the tree.
duty = app._if_blocks["Duty"]
duty.expand()
app.update()
hits = app._if_filter("freedom")
assert hits > 0, "Search does not find Freedom pairs"
app._if_filter("")
duty.rows[dfkey].set(-800)
app.update()
app._apply_changed_only()
assert duty._hitset == {dfkey}, duty._hitset
print(f"Suche ({hits} matches) and Changed only filter  OK")

# --- 9) Mod scan covers the faction tree ---
from s2tweaker import modscan
assert "relations" in modscan._GD_TREES, "_GD_TREES lacks relations"
fp = app._faction_tree_footprint(gd)
assert ("Default", "Bandits<->Player") in fp, "Pair leaf missing from footprint"
assert ("Default", "RelationVersion") not in fp, "Version bump was removed and must be absent from the footprint"
assert len(fp) >= 90, f"only {len(fp)} leaves in the combined footprint"
# Report overlapping faction pairs under the tree pseudo-key.
fake = modscan.ModInfo(name="FactionMod_Fake", path=Path("FactionMod_Fake.pak"),
                       pairs={("Default", "Bandits<->Player")},
                       base_names={"RelationPrototypes"})
conflicts = app._match_conflicts(gd, [fake])
assert conflicts.get("tree:factions") == ["FactionMod_Fake"], conflicts
# Show the faction summary only when conflicts exist.
app.mod_conflicts = conflicts
assert "Faction relations (Factions tab)" in app._conflict_labels("FactionMod_Fake")
app._apply_conflict_marks()
app.update()
assert app.if_conflict_label.winfo_manager(), "Notice not packed"
assert "FactionMod_Fake" in app.if_conflict_label.cget("text")
app.mod_conflicts = {}
app._apply_conflict_marks()
app.update()
assert not app.if_conflict_label.winfo_manager(), "Notice not removed"
print("Mod scan: footprint, pseudo key, tab notice  OK")

app.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("\nFACTIONS-TEST OK")
