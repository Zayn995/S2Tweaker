"""Factions-Tab: Baum, Werte, Patch, Reset, Persistenz, Suche.

Der vierte Baum (Beziehungspaare als direkte SliderRows). Prueft auch die
Kernmechanik des Builders: nur abweichende Paare landen im Patch, und
RelationVersion wird genau dann (+1) geschrieben."""
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
assert len(pairs) == 582, f"582 Paare erwartet, {len(pairs)} gefunden"
assert gd.relation_version() == 7, gd.relation_version()

app = gui.App()
app.gd = gd
app._if_populate()
app._set_body_state(True)
app.update()

# --- 1) Baum-Aufbau: Player-Block offen, 13 Zeilen, keine Phantome ------
player = app._if_blocks["player"]
assert player.expanded and len(player.rows) == 13, (
    player.expanded, len(player.rows))
assert app.faction_relations == {}, f"Phantom-Werte: {app.faction_relations}"
for key, row in player.rows.items():
    assert abs(row.default - pairs[key]) < 1e-9, (key, row.default)
# Kuratierung: Story-/Boss-Fraktionen duerfen NIRGENDS auftauchen
forbidden = {"ScarBoss_Faction", "KorshunovBoss_Faction", "ArenaEnemy",
             "ArenaFriend", "EnemyVarta", "VartaSIRCAA", "NoonFaustians"}
for key in app._if_vanilla:
    a, _, b = key.partition("<->")
    assert not ({a, b} & forbidden), f"Story-Fraktion in GUI: {key}"
print(f"Baum: {len(app._if_blocks)} Bloecke, {len(app._if_vanilla)} Paare, "
      f"Player-Defaults = Vanilla, Story-Fraktionen draussen  OK")

# --- 2) Wert aendern -> Patch mit RelationVersion-Bump ------------------
key = gd.relation_pair_key("Bandits", "Player")
player.rows[key].set(800)
app.update()
assert app.faction_relations == {key: 800}
p = build_patches(gd, app._collect())
rel = [k for k in p if "RelationPrototypes" in k]
assert len(rel) == 1 and len(p) == 1, list(p)
text = p[rel[0]]
assert "Bandits<->Player = 800" in text
assert "RelationVersion = 8" in text, "Version-Bump fehlt"
assert "{bpatch}" in text
assert any("Faction relations: 1 pair changed" in line
           for line in summarize(app._collect()))
print("Bandits<->Player 800: Patch + RelationVersion 8  OK")

# --- 3) Zurueck auf Vanilla -> neutral; Rollback-only bumpt NICHT -------
player.rows[key].set(pairs[key])
app.update()
assert app.faction_relations == {}
assert not build_patches(gd, app._collect()), "muss neutral sein"
p = build_patches(gd, Settings(relation_rollback_factor=2.0))
text = p["RelationPrototypes/RelationPrototypes_patch_S2Tweaker.cfg"]
assert "ReputationRollbackCooldown = 7200" in text
assert "RelationVersion" not in text, (
    "Rollback allein darf die RelationVersion nicht anfassen")
assert text.count("= 1800") == 19, "19 Fraktions-Cooldowns x2 erwartet"
print("Neutral-Reset + Rollback ohne Version-Bump  OK")

# --- 4) Builder-Hygiene: vanilla-gleiche/unbekannte/kaputte Paare -------
s = Settings(faction_relations={
    "Mutant<->Player": -800,         # == Vanilla -> raus
    "Gibtsnicht<->Player": 500,      # unbekannt -> raus
    "Freedom<->Duty": "quatsch",     # kaputt -> raus
})
assert not build_patches(gd, s), "Hygiene-Filter versagt"
print("Builder-Hygiene  OK")

# --- 5) Fraktions-Block: Duty<->Freedom (-599, krummer Vanilla-Wert) ----
duty = app._if_blocks["Duty"]
duty.expand()
app.update()
dfkey = gd.relation_pair_key("Duty", "Freedom")
drow = duty.rows[dfkey]
assert abs(drow.default - (-599)) < 1e-9, drow.default
assert "(vanilla)" in drow.value_label.cget("text"), (
    "krummer Default muss als (vanilla) angezeigt werden")
drow.set(-800)
app.update()
assert app.faction_relations == {dfkey: -800}
print("Duty-Block: krummer Default -599 sauber, -800 gesetzt  OK")

# --- 6) Reset all + Persistenz-Roundtrip (ueber JSON wie im echten Fluss)
state = json.loads(json.dumps(app._ui_state()))
app._reset_all()
app.update()
assert app.faction_relations == {} and not build_patches(gd, app._collect())
app._apply_ui_state(state)
app.update()
assert app.faction_relations == {dfkey: -800}
assert abs(duty.rows[dfkey].get() - (-800)) < 1e-9
print("Reset all + Persistenz-Roundtrip  OK")

# --- 7) Preset mit Vanilla-Wert wird beim Populate bereinigt ------------
app._reset_all()
app._apply_ui_state({"faction_relations": {dfkey: -599, "Kaputt": 1}})
assert dfkey in app.faction_relations          # vor Populate noch roh
app._if_populate()
app.update()
assert app.faction_relations == {}, app.faction_relations
print("Populate bereinigt Vanilla-gleiche/unbekannte Eintraege  OK")

# --- 8) Suche + Changed-only ueber den Fraktions-Baum -------------------
# Achtung: _if_populate in Schritt 7 hat den Baum NEU gebaut — alte
# Block-/Zeilen-Referenzen zeigen auf zerstoerte Widgets.
duty = app._if_blocks["Duty"]
duty.expand()
app.update()
hits = app._if_filter("freedom")
assert hits > 0, "Suche findet Freedom-Paare nicht"
app._if_filter("")
duty.rows[dfkey].set(-800)
app.update()
app._apply_changed_only()
assert duty._hitset == {dfkey}, duty._hitset
print(f"Suche ({hits} Treffer) + Changed-only-Filter  OK")

# --- 9) Mod-Scan kennt den Fraktions-Baum (Review-Befund 02.09.) --------
from s2tweaker import modscan
assert "relations" in modscan._GD_TREES, "_GD_TREES ohne relations"
fp = app._faction_tree_footprint(gd)
assert ("Default", "Bandits<->Player") in fp, "Paar-Blatt fehlt im Fussabdruck"
assert ("Default", "RelationVersion") in fp, "RelationVersion fehlt"
assert len(fp) >= 90, f"nur {len(fp)} Blaetter im Sammel-Fussabdruck"
# Fremde Mod, die dasselbe Paar patcht -> Pseudo-Schluessel im Ergebnis
fake = modscan.ModInfo(name="FactionMod_Fake", path=Path("FactionMod_Fake.pak"),
                       pairs={("Default", "Bandits<->Player")},
                       base_names={"RelationPrototypes"})
conflicts = app._match_conflicts(gd, [fake])
assert conflicts.get("tree:factions") == ["FactionMod_Fake"], conflicts
# Hinweis-Label: erscheint mit Konflikt, verschwindet ohne
app.mod_conflicts = conflicts
assert "Faction relations (Factions tab)" in app._conflict_labels("FactionMod_Fake")
app._apply_conflict_marks()
app.update()
assert app.if_conflict_label.winfo_manager(), "Hinweis nicht gepackt"
assert "FactionMod_Fake" in app.if_conflict_label.cget("text")
app.mod_conflicts = {}
app._apply_conflict_marks()
app.update()
assert not app.if_conflict_label.winfo_manager(), "Hinweis nicht entfernt"
print("Mod-Scan: Fussabdruck, Pseudo-Schluessel, Tab-Hinweis  OK")

app.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("\nFACTIONS-TEST OK")
