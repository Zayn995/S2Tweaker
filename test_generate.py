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
    artifact_slots_bonus=2, shooting_shake_factor=0.0, ads_zoom_factor=2.0,   # 1.24.0
    climb_speed_factor=2.0, starting_money=5000,
    no_aim_assist_mouse=True, no_aim_assist_gamepad=True,
    dialog_fov=90, cutscene_fov=100, default_fov=100, hud_compass=1, hud_crosshair=2,   # 1.25.0
    hud_body_markers=2, hud_stash_markers=1, corpse_time_factor=3.0, corpse_max_count=20,
    weather_duration_factor=0.5, bullet_drop_factor=0.0, bullet_speed_factor=1.5,
    pistol_slot_level=2, mutant_protection_factor=0.5,
    sleep_anytime=True, min_sleep_hours=3, sleep_in_emission=True,
    no_knockdown=True, no_water_slowdown=True, ladder_free_look=True,          # 1.26.0
    look_straight_down=True, handless_zoom_factor=0.7, crouch_vignette_factor=0.0,
    butt_wear_factor=0.0, mutants_trigger_anomalies=True, guards_no_instakill=True,
    explosion_radius_factor=1.5, explosion_npc_damage_factor=2.0,
    phantom_dog_damage_factor=0.0, psy_phantoms_only=True, reload_speed_factor=1.5,
    jam_clear_factor=2.0, mutant_loot_chance_factor=3.0, stash_clue_factor=2.0,
    npcs_no_corpse_loot=True, alife_vision_factor=1.5, map_reveal_factor=2.0,
    map_all_regions=True, fast_travel_lock=0, guide_delay_factor=0.0,
    instant_teleports=True, protection_cap_factor=1.2, weird_artifact_factor=3.0,
    skip_intro=True, traders_no_gear_buy=True, clicker_factor=0.5,
    back_speed_factor=1.5, air_control_factor=3.0, limp_speed_factor=1.5,            # 1.27.0
    slow_run_threshold_pct=25, hp_regen_delay=2, radiation_decay_factor=2.0,
    bleeding_stop_factor=2.0, psy_recovery_factor=2.0, sober_up_factor=3.0,
    stealth_kill_range_factor=1.5, wheel_time_pct=10, sleep_fade_factor=0.0,
    corpse_drag_factor=1.5, item_despawn_factor=3.0, day_start_hour=5, evening_start_hour=21,
    calm_damage_factor=2.0, last_bullet_multiplier=1.0, armor_difference_factor=0.5,
    armor_deflect_chance_pct=50, armor_deflect_damage_factor=0.5, scope_zoom_factor=1.25,
    scope_penalty_factor=0.0, upg_accuracy_factor=2.0, upg_handling_factor=1.5,
    upg_durability_factor=2.0, upg_range_factor=1.5, upg_damage_factor=2.0,
    upg_weight_factor=2.0, upg_breath_factor=1.3, upg_armor_protection_factor=2.0,
    upg_armor_misc_factor=2.0, weapon_warning_count=5, weapon_warning_delay_factor=2.0,
    camper_time_factor=3.0, sync_melee_factor=0.4, sync_ability_factor=2.0,
    sync_grenade_factor=2.0, sync_suppress_factor=0.5, npcs_no_weapon_pickup=True,
    darkness_factor=0.5, corpse_threat_factor=2.0, damage_mercy_factor=0.5,
    psy_phantom_factor=0.5, min_resale_pct=25, container_respawn_hours=24,
    energy_tolerance_factor=2.0, npc_hip_accuracy_factor=1.5, device_price_factor=0.5,
    limp_threshold_factor=3.0, bleeding_hit_factor=0.5, bleeding_nonpen_factor=0.0,   # 1.28.0 P1
    damage_screen_factor=0.3, flashlight_dialog_bright=True, quicksave_overwrite_min=0,
    grenade_resist_factor=0.0, armor_wear_coef=0.3, anomaly_armor_difference_factor=2.0,   # 1.28.0 P2
    wounded_heal_chance=0, wounded_cooldown_s=60, wounded_regen_factor=2.0,                 # 1.28.0 P3
    wounded_heal_threshold=50, npc_player_focus_factor=2.0, npc_retarget_cooldown_factor=0.5,
    npc_damage_memory_factor=2.0, cover_distance_factor=0.5, cover_path_factor=2.0,
    mutant_smell_factor=0.5, mutants_no_smell=True, burer_fire_interval_factor=2.0,   # 1.28.0 P4
    mutant_loot_widget=True,
    squad_expansion_factor=2.0, refill_cooldown_factor=0.5, refill_distance_factor=2.0,   # 1.28.0 P5
    corpse_budget=60, faction_battle_chance=80, faction_expansion_pace_factor=2.0,
    corpse_distance_factor=2.0, alife_corpse_hardcap=3000,
    radiation_dose_factor=0.5, radiation_filter_factor=0.0, geiger_volume_factor=2.0,   # 1.28.0 P6
    barbed_wire_factor=0.0, explosive_container_factor=0.5, push_force_factor=2.0,
    weather_transition_factor=2.0, moon_brightness_factor=2.0, sun_brightness_factor=1.5,
    stars_brightness_factor=5.0, cloud_opacity_factor=1.4, cloud_speed_factor=3.0,
    dusk_length_factor=2.0, music_combat_threshold=50, music_combat_lifetime=10,
    camp_life_factor=2.0,
    artifact_radius_factor=10.0, artifacts_no_hop=True, artifact_keepaway_factor=0.5,   # 1.28.0 P7
    artifact_hop_pause_factor=2.0, artifact_caches_drop=True,
    loot_reroll_radius_factor=2.0, loot_reroll_timer_factor=0.5,
    repair_cost_reputation=True, infotopic_refresh_hours=6,   # 1.28.0 P8
    equip_speed_factor=2.0, shooting_anim_skip=1,             # 1.29.0
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
    repeatable_jobs_per_round=6,     # Issue #8: 3 -> 6 Jobs je Runde
    repeatable_jobs_instant=True,    # Geber bietet sofort den naechsten an
    # 1.31.0 aus der Mod-Ausbeute (Stalker Unlimited)
    ammo_bleeding_factor=2.0,        # BleedingMod je Sorte
    ammo_recoil_factor=0.5,          # RecoilMod je Sorte
    ammo_flatness_factor=1.5,        # FlatnessMod (flachere Flugbahn)
    ammo_wear_factor=0.5,            # WeaponExhaustionMod
    # --- 1.33.0: neunte Datenrecherche (27 fremde Mods gegengelesen) ---
    anomaly_wear_factor=0.25,        # Corrosion-Familie (Anomalien fressen Ausruestung)
    gear_durability_factor=3.0,      # ItemPrototypes BaseDurability
    far_damage_factor=2.0,           # CWS MinBulletDistance*Modifier (Deckel 1.0)
    effect_cap_other_factor=2.0,     # ObjEffectMaxParams RegenStamina/DegenBleeding
    lair_initial_fill_factor=1.5,    # LairPrototypes InitialSpawnQuantityPercent
    lair_rare_archetype_factor=2.0,  # dito SpawnWeight der seltenen Archetypen
    lair_expansion_player_factor=2.0,  # ALifeDirectorScenario Ausbreitungszeit
    fallback_spawn_count=6,          # dito FallbackMaxSpawnCount
    ammo_dispersion_factor=0.5,      # ItemPrototypes DispersionMod
    ammo_aim_dispersion_factor=0.5,  # dito AimDispersionMod
    jam_chance_factor=0.0,           # Waffen klemmen nie
    npc_vs_npc_damage_factor=2.0,    # Fraktionskaempfe kuerzer
    stat_bars_follow=True,           # Anzeigebalken ziehen mit
    mutant_attack_series_factor=2.0, # Angriffe je Serie
    mutant_attack_bleed_factor=0.0,  # Krallen lassen nicht mehr bluten
    upgrade_repair_surcharge=0.0,    # Upgrades verteuern Reparatur nicht
    ammo_pack_factor=2.0,            # Packungsgroesse beim Aufsammeln
    stash_sets_factor=2.0,           # Fundgruppen je Versteck
    # 1.32.0: Schussverhalten, Explosionen, Geschosse
    recoil_recovery_factor=2.0,      # Erholung nach dem Schuss (invers)
    spread_bloom_factor=0.0,         # kein Streuungsaufbau bei Dauerfeuer
    aim_steady_factor=2.0,           # Zielen/Ducken beruhigen doppelt
    zombie_spread_factor=0.0,        # Zombies zielen wie normale Stalker
    explosion_armor_damage_factor=0.0,
    explosion_armor_pierce_factor=2.0,
    explosion_destructible_factor=3.0,
    bullet_penetration_factor=2.0,
    bullet_range_factor=2.0,
    # 1.32.0, zweite Runde (Maklane's Better Zone)
    hip_steady_factor=2.0,
    move_steady_factor=0.0,
    recoil_pattern_factor=2.0,
    chamber_round=True,
    dropped_ammo_factor=3.0,
    weapon_noise_factor=0.5,
    item_grid_factor=0.5,
    inventory_action_factor=2.0,
    npc_anomaly_ignore_factor=0.0,
    ragdoll_force_factor=3.0,
    npc_retreat_radius_factor=2.0,
    npc_retreat_damage_factor=0.5,
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
