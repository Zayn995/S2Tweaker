"""Verdrahtungs-Pruefung OHNE Fenster (neu am 08.09.2026).

Besitzer, nachdem die Batterie zwanzig Minuten und zwanzig Fenster
gebraucht hatte: "bau es richtig unter 5 minuten nur das was muss" und
"nicht 1000 mal oeffnen schliessen".

**Warum das geht.** Die alten GUI-Suiten bauen ein komplettes App-Fenster,
nur um an Widgets zu wackeln. Die Fragen, die beim Einbauen eines Reglers
wirklich schiefgehen, sind aber Verdrahtungsfragen — und die stehen im
Quelltext und in der Settings-Datenklasse:

  1. Steht der Regler in der Feldtabelle (SLIDER_FIELDS / CHECK_FIELDS)?
  2. Wird sein Feld in `_collect()` ueberhaupt eingesammelt? Genau das war
     der Fehler von 1.16.1: `rq_cooldown` wurde nie gelesen, der Regler war
     tot, und keine Suite hat es gemerkt.
  3. Bewirkt er etwas — kommt bei verstelltem Wert ein Patch heraus?
  4. Steht er in der Tweak-Liste, die der Benutzer nach dem Bauen sieht?
  5. Und andersherum: erzeugt die Vanilla-Stellung wirklich NICHTS?

Punkt 1, 2 und 5 sind statisch bzw. reine Datenpruefungen, 3 und 4 laufen
ueber `build_patches`/`summarize`. Kein Tk, kein Fenster, kein Fokus-Klau.

Was hier NICHT geprueft wird und darum vor einem Release weiterhin die
Fenster-Suiten braucht (`python tests/run_all.py --all`): Aussehen, Layout-
Breiten, Designs, Mausrad, Dialoge. Das sind Sachen, die sich seit Releases
nicht mehr bewegt haben.
"""
import ast
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, input_ini, summarize
# NUR das Modul, KEIN App(): der Import baut kein Fenster.
from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS

gd = GameData(str(VANILLA))
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


# --- 1) Was sammelt _collect() wirklich ein? ----------------------------
# Statisch aus dem Quelltext gelesen, nicht durch Klicken.
source = (ROOT / "s2tweaker" / "gui.py").read_text(encoding="utf-8")
tree = ast.parse(source)
collect = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "_collect":
        collect = node
        break
assert collect is not None, "_collect() nicht gefunden"
collected = set()
for node in ast.walk(collect):
    if isinstance(node, ast.keyword) and node.arg:
        collected.add(node.arg)

fields = set(SLIDER_FIELDS.values()) | set(CHECK_FIELDS.values())
missing = sorted(fields - collected)
check(not missing,
      f"jedes der {len(fields)} Bedienelemente wird in _collect() eingesammelt"
      + (f" - FEHLT: {missing}" if missing else ""))

known = {f.name for f in Settings.__dataclass_fields__.values()}
unknown = sorted(f for f in fields if f not in known)
check(not unknown, f"jede Feldtabelle zeigt auf ein echtes Settings-Feld{unknown}")

# --- 2) Vanilla erzeugt nichts -----------------------------------------
check(build_patches(gd, Settings(mod_name="S2Tweaker")) == {},
      "Vanilla-Stellung erzeugt keine einzige Patchdatei")
check(not summarize(Settings()), "Vanilla-Stellung erzeugt keine Tweak-Zeile")
check(input_ini(Settings()) is None, "Vanilla-Stellung erzeugt keine INI")

# --- 3) Jedes Bedienelement bewirkt etwas ------------------------------
# Sonden: fuer Faktoren das Doppelte bzw. die Haelfte des Vanilla-Werts,
# fuer Absolutwerte eine Stufe daneben, fuer Schalter True.
SPECIAL = {                      # Regler, deren Vanilla-Wert 0 oder Deckel ist
    "fall_damage_pct": 50.0, "fast_travel_lock": 0.0, "slow_run_threshold_pct": 25.0,
    "evening_start_hour": 22.0, "armor_deflect_chance_pct": 50.0,
    "npc_weapon_rank_add": 2.0, "scope_sway_pct": 50.0,
    "trader_min_durability_pct": 0.0, "hud_compass": 2.0, "hud_crosshair": 2.0,
    "hud_body_markers": 2.0, "hud_stash_markers": 2.0, "pistol_slot_level": 3.0,
}
# Bewusst wirkungslos ALLEIN (Begruendung jeweils im Code):
#   stat_bars_follow spiegelt nur die Waffenregler
#   no_mouse_smoothing/no_view_acceleration schreiben eine INI statt cfg
ALONE_EMPTY = {"stat_bars_follow", "no_mouse_smoothing", "no_view_acceleration"}

t0 = time.time()
dead, no_line = [], []
for field in sorted(fields):
    default = getattr(Settings(), field)
    if isinstance(default, bool):
        probe = not default
    elif field in SPECIAL:
        probe = SPECIAL[field]
    elif isinstance(default, (int, float)):
        probe = default * 2 if default else 1.0
        if isinstance(default, int):
            probe = int(probe) or 1
    else:
        continue                      # dicts (Baeume) haben eigene Suiten
    s = Settings(mod_name="S2Tweaker", **{field: probe})
    if not build_patches(gd, s) and field not in ALONE_EMPTY:
        # zweite Sonde in die andere Richtung (Deckel!)
        if isinstance(default, (int, float)) and not isinstance(default, bool):
            s2 = Settings(mod_name="S2Tweaker", **{field: type(default)(default * 0.5)})
            if build_patches(gd, s2):
                s = s2
            else:
                dead.append(field)
        else:
            dead.append(field)
    if field in ALONE_EMPTY:
        # muss wenigstens eine INI oder eine Zeile erzeugen
        if not (input_ini(s) or summarize(s)):
            dead.append(field)
    if not summarize(s):
        no_line.append(field)
check(not dead, f"jedes Bedienelement erzeugt einen Patch{dead}")
check(not no_line, f"jedes Bedienelement steht in der Tweak-Liste{no_line}")
print(f"      ({len(fields)} Bedienelemente in {time.time() - t0:.1f}s, ohne ein Fenster)")

print(f"\n=== {ok} Pruefungen gruen ===")
