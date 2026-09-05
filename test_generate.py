"""Entwickler-Test: erzeugt eine Test-Pak mit vielen aktiven Tweaks."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker import pakio

VANILLA = Path(__file__).parent / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "out"

gd = GameData(VANILLA)

print("=== Inventar (neuer Build) ===")
mutants = gd.mutants()
print(f"Mutanten: {len(mutants)}, Waffen: {len(gd.player_weapon_wear())}, "
      f"Items: {len(gd.item_weights())}")
print("Kategorien:", Counter(cat for cat, _ in gd.item_weights().values()))
traders = gd.traders()
n_dur = sum(1 for t in traders.values() for v in t.values() if "WeaponSellMinDurability" in v)
n_buy = sum(1 for t in traders.values() for v in t.values() if "BuyModifier" in v)
print(f"Händler: {len(traders)} (Generatoren mit MinDurability: {n_dur}, mit BuyModifier: {n_buy})")
print("Difficulty Weapon_BaseDamage:", gd.difficulty_values("EnvironmentDifficulty.Weapon_BaseDamage"))
print("Jamming:", gd.difficulty_values("NPCCombatDifficulty.Weapon_JammingMultiplier"))
print("Upgrade_Cost:", gd.difficulty_values("EconomyDifficulty.Upgrade_Cost"))
from s2tweaker.cfgparse import parse_number
print("HoldBreath Drain/Regen:",
      gd.resolve(gd.holdbreath, "DefaultHoldBreathParams", "HoldBreathDrainPerSecond"),
      gd.resolve(gd.holdbreath, "DefaultHoldBreathParams", "HoldBreathRegenPerSecond"))
print("Sway-Provider (Vanilla):",
      gd.resolve(gd.floatproviders, "ScopeIdleSwayConstValue", "Value"))
print("Player Sprint-Kosten:", gd.resolve(gd.obj, "Player", "StaminaPerAction.Sprint"))
print("Player RunSpeed:", gd.resolve(gd.obj, "Player", "MovementParams.RunSpeed"))
weapons = gd.player_weapons()
from collections import Counter as _C
print("Spieler-Waffen:", len(weapons), dict(_C(c for c, _ in weapons.values())))

s = Settings(
    max_hp=200, hp_regen=2, max_stamina=300, stamina_regen=10,
    fall_damage_pct=25, walk_speed_factor=1.1, run_speed_factor=0.8,
    jump_height_factor=1.3,
    stamina_sprint=0.5, stamina_jump=0.25, stamina_melee_light=0.5,
    stamina_melee_strong=0.5, stamina_buttstock=0.0, stamina_vault=0.75,
    max_carry_weight=200, penalty_start_weight=120, no_overweight_penalty=True,
    item_weight_factor=0.5, ignore_equipped_weight=True,
    player_damage_factor=2.0, headshot_factor=1.5, npc_damage_factor=0.75,
    npc_hp_factor=1.25, mutant_hp_factor=0.8, mutant_damage_factor=0.75,
    explosion_damage_factor=0.5, durability_factor=3.0, jamming_factor=0.0,
    scope_sway_pct=0, breath_drain_factor=0.0, breath_regen_factor=2.0,
    anomaly_damage_factor=0.5, radiation_factor=0.5, bleeding_factor=0.5,
    hunger_rate_factor=0.5, sleepiness_rate_factor=0.0,
    trader_min_durability_pct=0, trader_buy_price_factor=1.5,
    trader_sell_price_factor=0.75, repair_cost_factor=0.5,
    upgrade_cost_factor=0.5, quest_reward_factor=2.0,
    weapon_price_factor=1.5, armor_price_factor=0.75, ammo_price_factor=0.5,
    artifact_price_factor=2.0, consumable_price_factor=1.25,
    weapon_category_factors={"shotgun": {"damage": 2.0, "firerate": 1.5},
                             "pistol": {"spread": 0.5, "aimtime": 2.0}},
    weapon_overrides={"GunM860_SG": {"damage": 3.0},
                      "GunAK74_ST": {"recoil": 0.5, "aimtime": 1.5}},
    npc_accuracy_factor=2.0, npc_vision_factor=0.5, npc_hearing_factor=0.5,
    npc_grenade_factor=2.0, npc_no_heal=True,
    aim_punch_factor=2.0, npc_reaction_factor=2.0,
    max_agents_factor=1.5, spawn_distance_factor=0.5,
    artifact_effect_factor=2.0, artifact_radiation_factor=0.0,
    artifact_spawn_factor=3.0,
    recoil_upgrade_factor=4.0,       # -5 % .. -30 % -> -20 % .. -100 % (Deckel)
    upgrades_take_both=True, upgrades_no_tiers=True,   # UpgradePrototypes (1,9 MB)
    lair_mutant_factor=2.0, lair_respawn_factor=2.0,   # LairPrototypes
    encounter_frequency_factor=2.0, encounter_mutant_factor=1.5,  # Director
    enc_blinddog_factor=2.0, encounter_pack_factor=1.5,
    day_length_factor=2.0, consumable_duration_factor=3.0,   # v1.18
    artifact_count_factor=2.0, artifact_respawn_factor=2.0,
    quest_items_weightless=True,
    npc_free_shots_factor=0.0, npc_burst_factor=1.5,          # NPC-Kampfverhalten
    npc_fire_pause_factor=2.0, npc_engage_range_factor=0.5,
    npc_weapon_range_factor=0.75, npc_regen_factor=0.25,
    crouch_stealth_factor=2.0, movement_noise_factor=0.5,     # Stealth + Wachsamkeit
    weather_stealth_factor=2.0, flashlight_stealth_factor=0.0,
    npc_alertness_factor=0.5, npc_search_time_factor=2.0, npc_courage_factor=2.0,
    npc_stagger_factor=0.5, npc_attack_cooldown_factor=1.5, npc_weapon_rank_add=1,
    mutant_attack_cooldown_factor=1.5,
    armor_durability_factor=2.0, weapon_range_factor=1.5,
    armor_strike_factor=2.0, armor_burn_factor=1.5, armor_psy_factor=3.0,
    armor_carry_bonus_factor=2.0, artifact_rarity_factor=3.0,
    mutant_speed_factor=1.25, mutant_hearing_factor=0.5,
    mutant_regen_factor=0.5,
    mutant_overrides={"Bloodsucker": {"hp": 2.0, "damage": 0.5, "regen": 0.0},
                      "Boar": {"speed": 1.5, "damage": 2.0}},
    bloodsucker_cloak_factor=2.0, bloodsucker_uncloak_factor=10.0,
    ads_speed_factor=1.2, magazine_factor=2.0, melee_damage_factor=2.0,
    melee_range_factor=1.5, interaction_range_factor=2.0, dialog_range_factor=2.0,
    npc_flashlight_factor=2.0, npc_flashlight_cone_factor=1.5,
    npc_flashlight_combat_factor=0.5, npc_flashlight_on_hour=20,
    npc_flashlight_off_hour=6,
    manual_save_slots=200, quick_save_slots=10, auto_save_slots=20,
    autosave_interval_min=5,
    anomaly_electro_factor=0.5, anomaly_fire_factor=2.0,
    consumable_factor=2.0, rain_factor=2.0, emission_factor=0.5,
    emission_duration_factor=2.0,
    relation_reaction_factor=2.0, trade_min_level=2,
    weapon_bleeding_factor=2.0, ammo_damage_factor=1.5,
    ammo_piercing_factor=2.0, ammo_armor_damage_factor=1.25,
    ammo_cover_factor=0.5,
    # A545A: Override schlaegt den globalen Regler (Kaskade).
    # A012D: ArmorDamageMod = 0.084, kein glatter 1.0-Ausreisser.
    # AVOG: ArmorPiercingMod = 0.0 -> darf KEINE Patch-Zeile erzeugen.
    ammo_overrides={"A545A": {"damage": 2.0, "piercing": 1.5},
                    "A012D": {"armordamage": 2.0},
                    "AVOG": {"piercing": 3.0}},
    # Exoskelett: strike-Override ERSETZT den globalen ap_strike-Faktor.
    # Battle_Dolg_Armor hat PSY = 0 in Vanilla -> dieser psy-Override darf
    # KEINE Patch-Zeile erzeugen (0 x Faktor = 0, kein Schluessel anlegen).
    armor_overrides={"Exoskeleton_Dolg_Armor": {"strike": 2.0},
                     "Battle_Dolg_Armor": {"psy": 0.5},
                     "Light_Bandit_Helmet": {"burn": 3.0}},
    detector_range_factor=2.0,
    fast_travel_cost_factor=0.5, trader_restock_factor=0.25,
    stash_loot_factor=2.0, stash_chance_factor=1.5, stash_ammo_factor=2.0,
    loot_amount_factor=2.0, healing_factor=1.5,
    dropped_condition_pct=80.0,          # Mitte 0.375 -> 0.8, Spanne bleibt
    trader_stock_factor=2.0, trader_variety_factor=1.5,
    trader_money_factor=2.0, trader_infinite_money=True,
    vault_height_factor=1.5, improved_vaulting=True,
    vault_distance_factor=2.0, vault_landing_factor=6.0, vault_sprint=True,
    vault_over_offset_factor=5.0,
    # Fraktionsbeziehungen: ein Player-Paar, ein Fraktions-Paar mit
    # krummem Vanilla-Wert (-599), ein Vanilla-gleiches Paar (DARF keine
    # Patch-Zeile erzeugen) — dazu der Rollback-Faktor.
    faction_relations={"Bandits<->Player": 800,
                       "Freedom<->Duty": -800,
                       "Mutant<->Player": -800},
    relation_rollback_factor=0.5,
    aim_time_factor=2.0,             # global: alle Aiming-Zeiten halbiert
    repeatable_quest_factor=0.25,    # 24 h -> 6 h (parst die 75-MB-Datei)
)

print(f"\n=== Aktive Tweaks: {len(summarize(s))} ===")
for line in summarize(s):
    print(" -", line)

patches = build_patches(gd, s)
print("\n=== Patch-Dateien ===")
for path, content in patches.items():
    print(f"  {len(content):>8,} chars  {path}")

OUT.mkdir(parents=True, exist_ok=True)
pak = OUT / "zzz_S2Tweaker_Test_P.pak"
pakio.pack_mod(patches, pak)
print(f"\nPak erzeugt: {pak}  ({pak.stat().st_size:,} bytes)")
