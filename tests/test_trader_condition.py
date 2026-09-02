"""Zustands-Regler (gedroppte Waffen) + Haendler-Bestand/-Geldbeutel.

Rein tweaks-/gamedata-seitig; Sollwerte werden aus den Vanilla-Daten
nachgerechnet (docs/GENERATOR_RESEARCH.md, Kap. 3.3 und 7)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker.cfgparse import parse_number
from s2tweaker import cfgparse

gd = GameData(VANILLA)
GEN_KEY = "ItemGeneratorPrototypes/ItemGeneratorPrototypes_patch_S2Tweaker.cfg"
TRADE_KEY = "TradePrototypes/TradePrototypes_patch_S2Tweaker.cfg"

# --- 1) Inventar: Zustands-Eintraege nur in Waffen-Slots ----------------
dur = gd.loot_durability_entries()
assert len(dur) > 3000, len(dur)
for key, gen_key, slot_key, item_key, item in dur[:200]:
    assert "MinDurability" in item.values and "MaxDurability" in item.values
# Haendler-Huelle strikt getrennt vom Loot
stock_gens = set(gd.trader_stock_generators())
assert stock_gens, "leere Haendler-Huelle"
assert not (stock_gens & set(gd.loot_generators())), "Huellen ueberlappen!"
wallets = gd.trader_wallets()
finite = {sid for sid, (m, inf) in wallets.items() if not inf}
print(f"Inventar: {len(dur)} Zustands-Eintraege, {len(stock_gens)} "
      f"Haendler-Structs, {len(wallets)} Boersen ({len(finite)} endlich)  OK")

# --- 2) Zustand 80 %: Mitte wandert, Spanne bleibt, Klammer haelt -------
p = build_patches(gd, Settings(dropped_condition_pct=80.0))
assert list(p) == [GEN_KEY], list(p)
root = cfgparse.parse_file if False else None
text = p[GEN_KEY]
assert "MinDurability = 0.675" in text and "MaxDurability = 0.925" in text, \
    "Hauptcluster 0.25/0.5 muss zu 0.675/0.925 werden"
assert "MaxDurability = 1.05" not in text and " = -0" not in text
# 100 %: Klammer bei 1.0
p100 = build_patches(gd, Settings(dropped_condition_pct=100.0))
t100 = p100[GEN_KEY]
assert "MaxDurability = 1" in t100
assert "1.125" not in t100, "Klammer 0..1 verletzt"
print("Zustand 80 %: 0.25/0.5 -> 0.675/0.925; 100 % geklammert  OK")

# --- 3) Exact-Checkbox: Spanne kollabiert auf die Mitte -----------------
p = build_patches(gd, Settings(dropped_condition_exact=True))
text = p[GEN_KEY]
assert "MinDurability = 0.375" in text and "MaxDurability = 0.375" in text
p = build_patches(gd, Settings(dropped_condition_pct=80.0,
                               dropped_condition_exact=True))
text = p[GEN_KEY]
assert "MinDurability = 0.8" in text and "MaxDurability = 0.8" in text
assert "0.675" not in text
# Neutralstellung -> gar kein Patch
assert not build_patches(gd, Settings())
print("Exact: Spanne -> Mitte (0.375 bzw. 0.8); neutral = kein Patch  OK")

# --- 4) Merge: Mengen + Zustand + Bestand in EINER Datei ----------------
p = build_patches(gd, Settings(loot_amount_factor=2.0,
                               dropped_condition_pct=80.0,
                               trader_stock_factor=2.0))
assert list(p) == [GEN_KEY]
text = p[GEN_KEY]
assert "MinCount" in text and "MinDurability" in text
print("Merge: eine Generator-Patchdatei mit Mengen UND Zustand  OK")

# --- 5) Haendler-Bestand x2 / Sortiment gedeckelt -----------------------
p = build_patches(gd, Settings(trader_stock_factor=2.0))
text = p[GEN_KEY]
sample = gd.trader_stock_entries()
n_scalable = sum(1 for *_k, item in sample
                 if any(k in item.values for k in ("MinCount", "MaxCount")))
assert n_scalable > 300, n_scalable
assert text.count("MinCount") + text.count("MaxCount") > 300
p = build_patches(gd, Settings(trader_variety_factor=4.0))
text = p[GEN_KEY]
assert "Chance" in text
import re
for m in re.finditer(r"Chance = ([^\s;]+)", text):
    assert float(m.group(1)) <= 1.0 + 1e-9, m.group(1)
print(f"Bestand: {n_scalable} Mengen-Eintraege skaliert; "
      "Sortiment-Chance sauber bei 1.0 gedeckelt  OK")

# --- 6) Geldbeutel ------------------------------------------------------
p = build_patches(gd, Settings(trader_infinite_money=True))
text = p[TRADE_KEY]
assert text.count("bInfiniteMoney = true") == len(finite), (
    text.count("bInfiniteMoney = true"), len(finite))
p = build_patches(gd, Settings(trader_money_factor=2.0))
text = p[TRADE_KEY]
n_money = text.count("Money =") - text.count("bInfiniteMoney =")
n_expected = sum(1 for sid in finite if wallets[sid][0] > 0)
assert n_money == n_expected, (n_money, n_expected)
# Merge mit trader_dur im selben TradePrototypes-Patch
p = build_patches(gd, Settings(trader_money_factor=2.0,
                               trader_min_durability_pct=0))
assert list(p) == [TRADE_KEY]
assert "Money" in p[TRADE_KEY] and "MinDurability" in p[TRADE_KEY]
print(f"Geldbeutel: {len(finite)} auf unendlich; {n_expected} skaliert; "
      "Merge mit trader_dur  OK")

# --- 7) summarize -------------------------------------------------------
lines = summarize(Settings(dropped_condition_pct=80.0,
                           dropped_condition_exact=True,
                           trader_stock_factor=2.0,
                           trader_infinite_money=True))
joined = " | ".join(lines)
for frag in ("Dropped weapon condition ~80", "exact", "Trader stock",
             "unlimited money"):
    assert frag in joined, (frag, joined)
print("summarize  OK")

print("\nTRADER/CONDITION-TEST OK")
