"""Index-adressierte Top-Level-Eintraege ([0], [1] ...) werden KOMPLETT
ausgegeben — Wetter-Vorlagen (Regen-/Emissions-Regler) und das DefaultNPC-
Profil in ThreatPrototypes. Anlass: Nexus-Wetterbericht 04.09. („seit 1.6.1
aendert sich das Wetter nicht mehr"). Ob das Spiel solche Eintraege beim
{bpatch} zusammenfuehrt oder ersetzt, ist unbelegt; komplett ist unter
beiden Lesarten richtig. Benannte Prototypen bleiben Teil-Patches."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import cfgparse
from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import (Settings, build_patches, _resolved_struct,
                              _struct_dict)

gd = GameData(VANILLA)


def keyset(d: dict, prefix: str = "") -> set:
    """Alle Pfade eines verschachtelten dicts (Structs und Blaetter)."""
    out = set()
    for k, v in d.items():
        out.add(prefix + k)
        if isinstance(v, dict):
            out |= keyset(v, prefix + k + "/")
    return out


def weather_root(patches: dict):
    key = [k for k in patches if "WeatherSelection" in k]
    assert len(key) == 1, list(patches)
    return cfgparse.parse(patches[key[0]])


ws = gd.weatherselection
idx = [k for k in ws.children if k.startswith("[")]
assert idx == ["[0]", "[1]", "[2]", "[3]", "[35]"], idx

# --- 0) Helfer: refkey-Vererbung wird aufgeloest --------------------------
full1 = _resolved_struct(ws, ws.children["[1]"])
assert full1["SID"] == "BaseWeatherHistory", full1["SID"]
for wtype in ("Clearly", "Cloudy", "Fogy", "Stormy", "LightRainy", "Rainy",
              "Thundery", "Emission", "CalmBeforeEmission", "Underground"):
    assert set(full1[wtype]) == {
        "BlendWeight", "BlendWeightIncrease", "WeatherDurationMin",
        "WeatherDurationMax", "MaximumRepeatAmount",
        "MaximumCooldownWeatherAmount", "bAllowInDialogueTransition"}, (
        wtype, sorted(full1[wtype]))
print("_resolved_struct: [1] mit allen 10 Wetterarten x 7 Schluesseln  OK")

# --- 1) Regen-Regler x2 ---------------------------------------------------
# Nur Vorlagen MIT Regen-Gewicht > 0 werden gepatcht ([2]/[3]/[35] sind
# Quest-/Sonderwetter ohne Regen und bleiben unangetastet).
root = weather_root(build_patches(gd, Settings(rain_factor=2.0)))
patched_idx = [k for k in root.children if k.startswith("[")]
assert set(patched_idx) >= {"[0]", "[1]"}, patched_idx
assert set(patched_idx) <= set(idx), patched_idx
for k in patched_idx:
    got = _struct_dict(root.children[k])
    want = _resolved_struct(ws, ws.children[k])
    assert keyset(got) == keyset(want), (k, keyset(want) ^ keyset(got))
    for wtype, sub in want.items():
        if not isinstance(sub, dict):
            assert got[wtype] == sub, (k, wtype, sub, got[wtype])
            continue
        for leaf, val in sub.items():
            if (leaf == "BlendWeight" and wtype in gd.RAIN_WEATHER_TYPES
                    and parse_number(val) > 0):
                assert abs(parse_number(got[wtype][leaf])
                           - 2 * parse_number(val)) < 1e-6, (
                    k, wtype, val, got[wtype][leaf])
            else:
                assert got[wtype][leaf] == val, (
                    k, wtype, leaf, val, got[wtype][leaf])
named = [k for k in root.children if not k.startswith("[")]
assert len(named) >= 20, named
for k in named:
    d = _struct_dict(root.children[k])
    assert all(isinstance(v, dict) for v in d.values()), (k, d)
    leaves = {leaf for sub in d.values() for leaf in sub}
    assert leaves == {"BlendWeight"}, (k, leaves)
    assert set(d) <= set(gd.RAIN_WEATHER_TYPES), (k, sorted(d))
print(f"Regen x2: {len(patched_idx)} von {len(idx)} Index-Vorlagen gepatcht, "
      f"alle komplett (nur Regen-Gewichte veraendert), {len(named)} Regionen "
      "als reiner BlendWeight-Teilpatch  OK")

# --- 2) Emissions-Regler x2 ----------------------------------------------
root = weather_root(build_patches(gd, Settings(emission_factor=2.0)))
patched_idx = [k for k in root.children if k.startswith("[")]
assert set(patched_idx) >= {"[0]", "[1]"}, patched_idx
for k in patched_idx:
    got = _struct_dict(root.children[k])
    want = _resolved_struct(ws, ws.children[k])
    assert keyset(got) == keyset(want), k
    assert abs(parse_number(got["Emission"]["BlendWeightIncrease"])
               - 2 * parse_number(want["Emission"]["BlendWeightIncrease"])
               ) < 1e-6, (k, got["Emission"])
    got["Emission"]["BlendWeightIncrease"] = want["Emission"]["BlendWeightIncrease"]
    assert got == want, k
print("Emission x2: Index-Vorlagen komplett, nur BlendWeightIncrease verdoppelt  OK")

# --- 3) ThreatPrototypes [1] = DefaultNPC ----------------------------------
p = build_patches(gd, Settings(npc_alertness_factor=2.0))
key = [k for k in p if "Threat" in k]
assert len(key) == 1, list(p)
root = cfgparse.parse(p[key[0]])
assert list(root.children) == ["[1]"], list(root.children)
prof = gd.threats.children["[1]"]
assert prof.values.get("SID", "").strip() == "DefaultNPC"
got = _struct_dict(root.children["[1]"])
want = _resolved_struct(gd.threats, prof)
assert keyset(got) == keyset(want), (keyset(want) ^ keyset(got))
changed = [i for i, e in got["Actions"].items()
           if e["ThreatLevelValueMin"] != want["Actions"][i]["ThreatLevelValueMin"]]
assert changed, "keine Schwelle veraendert?"
for i in changed:
    assert int(got["Actions"][i]["ThreatLevelValueMin"]) == max(1, round(
        parse_number(want["Actions"][i]["ThreatLevelValueMin"]) / 2)), i
for k2, v in want.items():
    if k2 != "Actions":
        assert got[k2] == v, k2
print(f"ThreatPrototypes [1]: komplett ausgegeben, {len(changed)} Schwellen "
      "halbiert, alles ausserhalb Actions identisch  OK")

# --- 4) Neutral bleibt neutral ---------------------------------------------
assert not build_patches(gd, Settings())
print("\nINDEX-ENTRIES-TEST OK")
