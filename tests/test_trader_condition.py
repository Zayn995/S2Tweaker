"""Check dropped-weapon condition and trader stock/wallet controls.

Calculate expected results from live vanilla data."""
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
# Wallet controls also patch NPC-level money; precedence remains unverified.
NPC_KEY = "NPCPrototypes/NPCPrototypes_patch_S2Tweaker.cfg"

# Condition entries must be restricted to weapon slots.
dur = gd.loot_durability_entries()
assert len(dur) > 3000, len(dur)
for key, gen_key, slot_key, item_key, item in dur[:200]:
    assert "MinDurability" in item.values and "MaxDurability" in item.values
# Trader graph strictly separated from loot.
stock_gens = set(gd.trader_stock_generators())
assert stock_gens, "empty trader structure"
assert not (stock_gens & set(gd.loot_generators())), "Structures overlap!"
wallets = gd.trader_wallets()
finite = {sid for sid, (m, inf) in wallets.items() if not inf}
print(f"Inventory: {len(dur)} condition entries, {len(stock_gens)} "
      f"trader structs, {len(wallets)} wallets ({len(finite)} finite)  OK")

# --- 2) Condition 80%: shift midpoint, preserve width, clamp ---
p = build_patches(gd, Settings(dropped_condition_pct=80.0))
assert list(p) == [GEN_KEY], list(p)
root = cfgparse.parse_file if False else None
text = p[GEN_KEY]
assert "MinDurability = 0.675" in text and "MaxDurability = 0.925" in text, \
    "Main cluster 0.25/0.5 must become 0.675/0.925"
assert "MaxDurability = 1.05" not in text and " = -0" not in text
# Clamp full condition at 1.0.
p100 = build_patches(gd, Settings(dropped_condition_pct=100.0))
t100 = p100[GEN_KEY]
assert "MaxDurability = 1" in t100
assert "1.125" not in t100, "Klammer 0..1 verletzt"
print("Condition 80%: 0.25/0.5 -> 0.675/0.925; 100% clamped  OK")

# Exact mode collapses both bounds to their midpoint.
p = build_patches(gd, Settings(dropped_condition_exact=True))
text = p[GEN_KEY]
assert "MinDurability = 0.375" in text and "MaxDurability = 0.375" in text
p = build_patches(gd, Settings(dropped_condition_pct=80.0,
                               dropped_condition_exact=True))
text = p[GEN_KEY]
assert "MinDurability = 0.8" in text and "MaxDurability = 0.8" in text
assert "0.675" not in text
# Neutral settings emit no patch.
assert not build_patches(gd, Settings())
print("Exact: range -> midpoint (0.375 or 0.8); neutral = no patch  OK")

# --- 4) Merge: quantities, condition and stock in ONE file ---
p = build_patches(gd, Settings(loot_amount_factor=2.0,
                               dropped_condition_pct=80.0,
                               trader_stock_factor=2.0))
assert list(p) == [GEN_KEY]
text = p[GEN_KEY]
assert "MinCount" in text and "MinDurability" in text
print("Merge: one generator patch file with quantities AND condition  OK")

# --- 5) Trader stock x2, chance capped ---
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
print(f"Stock: {n_scalable} quantity entries scaled; "
      "Stock chance capped at 1.0  OK")

# --- 6) Wallets ------------------------------------------------------
p = build_patches(gd, Settings(trader_infinite_money=True))
text = p[TRADE_KEY]
assert text.count("bInfiniteMoney = true") == len(finite), (
    text.count("bInfiniteMoney = true"), len(finite))
p = build_patches(gd, Settings(trader_money_factor=2.0))
text = p[TRADE_KEY]
n_money = text.count("Money =") - text.count("bInfiniteMoney =")
n_expected = sum(1 for sid in finite if wallets[sid][0] > 0)
assert n_money == n_expected, (n_money, n_expected)
# Merge trader controls while also routing NPC-level wallet changes.
p = build_patches(gd, Settings(trader_money_factor=2.0,
                               trader_min_durability_pct=0))
assert sorted(p) == sorted([TRADE_KEY, NPC_KEY]), sorted(p)
assert "Money" in p[TRADE_KEY] and "MinDurability" in p[TRADE_KEY]
assert "Money" in p[NPC_KEY] and "MinDurability" not in p[NPC_KEY]
# Without wallet changes, do not emit NPC money patches.
assert list(build_patches(gd, Settings(trader_min_durability_pct=0))) == [TRADE_KEY]
print(f"Geldbeutel: {len(finite)} set to infinite; {n_expected} scaled; "
      "Merge with trader_dur, NPC wallets in a separate file  OK")

# Bias existing gear choices toward higher prices.
pools = gd.gear_weight_pools()
assert len(pools) > 3000, len(pools)
p = build_patches(gd, Settings(npc_gear_quality_factor=4.0))
text = p[GEN_KEY]
# Reference pool, Recon slot [0]: Viper(3000) W1000, AKU(6000) W100.
# Cheapest remains unchanged, most expensive x4.
m = re.search(r"^GeneralNPC_Neutral_Recon_ItemGenerator : struct.begin "
              r"\{bpatch\}\n(.*?)^struct.end", text, re.S | re.M)
assert m, "Recon loadout missing"
assert "Weight = 400" in m.group(1), m.group(1)[:600]
assert "Weight = 1000\n" not in m.group(1).replace("\r", ""), \
    "Cheapest item (factor 1) must not receive a patch line"
# Integer baselines keep a minimum of 1; positive fractions remain positive.
low = build_patches(gd, Settings(npc_gear_quality_factor=0.25))[GEN_KEY]
assert all(float(v) > 0 for v in re.findall(r"Weight = ([0-9.eE+-]+)", low))
assert "Weight" not in build_patches(
    gd, Settings(loot_amount_factor=2.0))[GEN_KEY]
print(f"NPC-Gear x4: {len(pools)} pools, exact reference pool, "
      "positive weights including fractions, neutral output empty  OK")

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
