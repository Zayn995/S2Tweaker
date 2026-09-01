"""Avoid-conflicts-Test: Sperren, Entsperren, Wiederherstellen, Persistenz."""
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
from s2tweaker.tweaks import build_patches

gd = GameData(VANILLA)

app = gui.App()
app.gd = gd
app._set_body_state(True)
app.update()

# Ausgangslage: Nutzerwerte gesetzt, Scan meldet Konflikte auf 3 Zielen
app.sliders["pdmg"].set(2.0)
app.sliders["npchp"].set(1.5)
app.checks["npc_no_heal"].select()
app.mod_conflicts = {"pdmg": ["OXA_Fake"], "npchp": ["OXA_Fake"],
                     "check:npc_no_heal": ["OXA_Fake"]}
app._apply_conflict_marks()
app.update()
assert not app.sliders["pdmg"].locked, "ohne Avoid darf nichts gesperrt sein"

# --- 1) Avoid AN: Reset auf Vanilla + Sperre -----------------------------
app._set_avoid_mode(True)
app.update()
for key in ("pdmg", "npchp"):
    row = app.sliders[key]
    assert row.locked and abs(row.get() - row.default) < 1e-9, key
    assert str(row.slider.cget("state")) == "disabled", key
    assert "\U0001f513" in row.reset_btn.cget("text"), "kein Unlock-Knopf"
assert "npc_no_heal" in app._locked_checks
assert not bool(app.checks["npc_no_heal"].get())
assert str(app.checks["npc_no_heal"].cget("state")) == "disabled"
assert app.check_dots["npc_no_heal"].cget("text") == "\U0001f512"
assert not build_patches(gd, app._collect()), "gesperrt muss neutral sein"
print(f"Avoid AN: {app._avoid_lock_count()} gesperrt, Pak neutral  OK")

# --- 2) Einen Regler bewusst freischalten -> Wert kommt zurueck ----------
app.sliders["pdmg"]._unlock()
app.update()
row = app.sliders["pdmg"]
assert not row.locked and abs(row.get() - 2.0) < 1e-9, row.get()
assert str(row.slider.cget("state")) == "normal"
assert "pdmg" in app.avoid_unlocked
assert app.sliders["npchp"].locked, "npchp muss gesperrt bleiben"
print("Unlock: pdmg frei, Wert 2.0 zurueck, npchp bleibt zu  OK")

# --- 3) Re-Scan (Marks neu anwenden): Unlock bleibt bestehen -------------
app._apply_conflict_marks()
app.update()
assert not app.sliders["pdmg"].locked and app.sliders["npchp"].locked
print("Re-Scan: bewusster Unlock ueberlebt  OK")

# --- 3b) Scan verliert einen Konflikt -> Sperre faellt, Wert kommt zurueck
app.mod_conflicts = {"pdmg": ["OXA_Fake"], "check:npc_no_heal": ["OXA_Fake"]}
app._apply_conflict_marks()
app.update()
assert not app.sliders["npchp"].locked, "verwaiste Sperre nicht geloest"
assert abs(app.sliders["npchp"].get() - 1.5) < 1e-9, "Wert nicht zurueck"
app.mod_conflicts["npchp"] = ["OXA_Fake"]
app._apply_conflict_marks()
app.update()
assert app.sliders["npchp"].locked
print("Konflikt weg -> Sperre weg -> Konflikt wieder da -> Sperre wieder  OK")

# --- 3c) Bewusstes Wieder-Einschalten sperrt auch Freigeschaltetes -------
assert "pdmg" in app.avoid_unlocked and not app.sliders["pdmg"].locked
app._set_avoid_mode(True)
app.update()
assert not app.avoid_unlocked, "Einschalten muss Freischaltungen leeren"
assert app.sliders["pdmg"].locked, "pdmg muss wieder gesperrt sein"
app.sliders["pdmg"]._unlock()
app.update()
print("Re-Enable sperrt alles wieder; Unlock danach weiter moeglich  OK")

# --- 4) Body sperren/entsperren laesst die Avoid-Sperre stehen -----------
app._set_body_state(False)
app._set_body_state(True)
app.update()
assert app.sliders["npchp"].locked
assert str(app.sliders["npchp"].slider.cget("state")) == "disabled"
assert str(app.checks["npc_no_heal"].cget("state")) == "disabled"
print("Body-Toggle: Sperren bleiben  OK")

# --- 5) Avoid AUS: alles frei, gemerkte Werte zurueck --------------------
app._set_avoid_mode(False)
app.update()
assert not app.sliders["npchp"].locked
assert abs(app.sliders["npchp"].get() - 1.5) < 1e-9, "npchp-Wert weg"
assert bool(app.checks["npc_no_heal"].get()), "Checkbox-Wert weg"
assert not app._locked_checks
print("Avoid AUS: Werte wiederhergestellt  OK")

# --- 6) Persistenz: avoid + unlocked landen in settings.json -------------
app.avoid_conflicts = True
app._save_ui_settings()
data = json.loads(gui.SETTINGS_FILE.read_text(encoding="utf-8"))
assert data["modscan_avoid"] is True
assert "pdmg" in data["modscan_unlocked"]
print("Persistenz: modscan_avoid + modscan_unlocked gespeichert  OK")

app.destroy()

# Neustart: Einstellungen kommen zurueck (Sperren erst nach neuem Scan)
app2 = gui.App()
app2.update()
assert app2.avoid_conflicts is True
assert "pdmg" in app2.avoid_unlocked
assert app2._avoid_lock_count() == 0, "ohne Scan darf nichts gesperrt sein"
app2.destroy()
gui.SETTINGS_FILE.unlink(missing_ok=True)
print("Neustart: Einstellung geladen, keine Sperre ohne Scan  OK")

print("\nAVOID-TEST OK")
