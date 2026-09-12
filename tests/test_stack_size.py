"""Check inventory stack sizes against live ItemPrototypes.

Exclude counts <= 1, retain integers and enforce the supported upper cap.
Per-ammunition overrides replace their global factor."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker import cfgparse

gd = GameData(VANILLA)
KEY = "ItemPrototypes/ItemPrototypes_patch_S2Tweaker.cfg"


def items(patches):
    return cfgparse.parse(patches[KEY]).children


# Verify current stackable item inventory.
ammo = gd.stack_counts("ammo")
cons = gd.stack_counts("consumable")
assert len(ammo) == 34, len(ammo)
assert set(ammo.values()) == {900}, sorted(set(ammo.values()))
assert len(cons) == 22, len(cons)
assert set(cons.values()) == {999}, sorted(set(cons.values()))
print(f"Live: {len(ammo)} ammunition types set to 900, {len(cons)} consumables set to 999  OK")

# Items intentionally restricted to single units must remain excluded.
for sid in ("Binoculars_01", "Veles", "AArtifactWeirdBolt", "MoneyCommon", "GuitarUsable"):
    for cat in ("ammo", "consumable", "misc", "artifact"):
        assert sid not in gd.stack_counts(cat), f"{sid} must not become stackable"
print("Binoculars, detectors, weird artifacts, money cards and guitar remain excluded  OK")

# --- 2) Neutral produces nothing ---
assert not build_patches(gd, Settings())
print("Neutral: no patch  OK")

# --- 3) Global ammunition slider ---
p = items(build_patches(gd, Settings(ammo_stack_factor=10.0)))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert len(hit) == 34, len(hit)
assert set(hit.values()) == {"9000"}, set(hit.values())
assert "TemplateAmmo" not in hit, "Template is not patched"
print(f"Ammunition x10: {len(hit)} types set to 9000, integers  OK")

# Check upper and lower bounds.
p = items(build_patches(gd, Settings(ammo_stack_factor=1000.0)))
werte = {n.values["MaxStackCount"] for n in p.values() if "MaxStackCount" in n.values}
assert werte == {"300000"}, werte      # 900 * 1000 = 900000 -> capped
p = items(build_patches(gd, Settings(ammo_stack_factor=0.0)))
werte = {n.values["MaxStackCount"] for n in p.values() if "MaxStackCount" in n.values}
assert werte == {"1"}, werte           # Never below 1.
print("Upper cap 300000 and lower bound 1 hold  OK")

# --- 5) Separate food and medicine ---
p = items(build_patches(gd, Settings(consumable_stack_factor=3.0)))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert len(hit) == 22 and set(hit.values()) == {"2997"}, (len(hit), set(hit.values()))
assert not any(sid in hit for sid in ammo), "Ammunition must not be included here"
print("Food/medicine x3: 22 items set to 2997, ammunition unchanged  OK")

# Check per-ammunition overrides.
p = items(build_patches(gd, Settings(ammo_overrides={"A545D": {"stack": 5.0}})))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert hit == {"A545D": "4500"}, hit
print("Individual type x5: only A545D set to 4500  OK")

# Individual ammunition overrides replace the global factor.
p = items(build_patches(gd, Settings(ammo_stack_factor=2.0,
                                     ammo_overrides={"A545D": {"stack": 5.0}})))
hit = {sid: n.values["MaxStackCount"] for sid, n in p.items()
       if "MaxStackCount" in n.values}
assert hit["A545D"] == "4500" and hit["A762D"] == "1800", (hit["A545D"], hit["A762D"])
print("Individual type overrides global (4500 alongside 1800)  OK")

# --- 7) The four existing modifiers remain unchanged ---
p = items(build_patches(gd, Settings(ammo_stack_factor=2.0)))
for sid, node in p.items():
    assert set(node.values) == {"MaxStackCount"}, (sid, node.values)
print("Stack slider leaves DamageMod and other modifiers unchanged  OK")

# --- 8) Tweak list -----------------------------------------------------
lines = summarize(Settings(ammo_stack_factor=10.0, consumable_stack_factor=2.0))
assert any("Ammo stack size" in l for l in lines), lines
assert any("Food & medicine stack size" in l for l in lines), lines
print("Lines in the tweak list  OK")

print("\nSTACK SIZE TEST PASSED")
