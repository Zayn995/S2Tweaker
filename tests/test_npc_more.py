"""Stealth-Paket, NPC-Wachsamkeit/Mut/Wanken, Difficulty-Einzeiler (03.09.2026,
Vorschlag nach dem NPC-Scan). Sollwerte live aus vanilla/; Anker: Pose-
Koeffizienten (Crouch 0.75/0.1, Sprint 1.2/1.0), Wetter Fogy 0.7/0.4,
Threat-Aktionen 200/500/700/350, Taktik Bandits 2/1.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import cfgparse
from s2tweaker.cfgparse import parse_number
from s2tweaker.gamedata import GameData, NEEDED_FILES, CACHE_SCHEMA
from s2tweaker.tweaks import Settings, build_patches, summarize

assert "AIPrototypes/ThreatPrototypes.cfg.bin" in NEEDED_FILES and CACHE_SCHEMA >= 15
gd = GameData(VANILLA)
AIG = "AIGlobals.cfg_patch_S2Tweaker.cfg"
OBJ = "ObjPrototypes/ObjPrototypes_patch_S2Tweaker.cfg"
THR = "AIPrototypes/ThreatPrototypes/ThreatPrototypes_patch_S2Tweaker.cfg"
DIF = "DifficultyPrototypes/DifficultyPrototypes_patch_S2Tweaker.cfg"
DIR = ("ALifePrototypes/ALifeDirectorScenarioPrototypes/"
       "ALifeDirectorScenarioPrototypes_patch_S2Tweaker.cfg")


def ai(p):
    return cfgparse.parse(p[AIG]).children["AISettings"]


# --- 1) Crouch stealth x2: Pose-Eintraege komplett, Player-Koeffizienten ---
p = build_patches(gd, Settings(crouch_stealth_factor=2.0))
assert set(p) == {AIG, OBJ}, set(p)
poses = ai(p).children["CharacterPoseSettings"].children
assert set(poses) == {"[0]", "[1]"}, set(poses)
assert poses["[1]"].values == {"Pose": "EStateTag::Crouch", "VisibilityCoef": "0.375",
                               "NoiseCoef": "0.05"}, poses["[1]"].values
assert poses["[0]"].values["Pose"] == "EStateTag::LowCrouchInPlace"
pl = cfgparse.parse(p[OBJ]).children["Player"].children["StealthParams"].values
assert pl == {"VisibilityCrouchCoef": "0.15", "NoiseCrouchCoef": "0.15"}, pl
print("Crouch stealth x2: 2 Posen komplett + Player 0.3 -> 0.15  OK")

# --- 2) Movement noise x0: Walk/Run/Sprint/None, Sichtbarkeit unveraendert ---
p = build_patches(gd, Settings(movement_noise_factor=0.0))
poses = ai(p).children["CharacterPoseSettings"].children
assert {e.values["Pose"].split("::")[-1] for e in poses.values()} == {"Walk", "Run", "Sprint", "None"}
assert all(e.values["NoiseCoef"] == "0.0" for e in poses.values())
sprint = next(e for e in poses.values() if e.values["Pose"].endswith("Sprint"))
assert sprint.values["VisibilityCoef"] == "1.2"
assert OBJ not in p
print("Movement noise x0: 4 Posen lautlos, Sichtbarkeit unveraendert  OK")

# --- 3) Wetter x2 / x0: Abschlaege verdoppelt bzw. weg, Clearly nie im Patch ---
p = build_patches(gd, Settings(weather_stealth_factor=2.0))
w = {e.values["WeatherSID"]: e.values for e in ai(p).children["WeatherSettings"].children.values()}
assert "Clearly" not in w
assert w["Fogy"]["VisibilityCoef"] == "0.4" and w["Fogy"]["HearingDistanceCoef"] == "0.05", w["Fogy"]
assert w["Thundery"]["HearingDistanceCoef"] == "0.05" and w["Thundery"]["VisibilityCoef"] == "0.6"
p = build_patches(gd, Settings(weather_stealth_factor=0.0))
w = {e.values["WeatherSID"]: e.values for e in ai(p).children["WeatherSettings"].children.values()}
assert all(v[k] == "1.0" for v in w.values() for k in ("VisibilityCoef", "HearingDistanceCoef", "FlairCoef"))
print("Wetter x2 / x0: Fogy 0.7->0.4, Deckel 0.05, x0 = alles 1.0  OK")

# --- 4) Taschenlampe x0 ------------------------------------------------------
p = build_patches(gd, Settings(flashlight_stealth_factor=0.0))
fl = ai(p).children["PlayerFlashlightVisionSettings"].values
assert fl == {"FlashlightMinVisionScorePerSecond": "0.0f", "FlashlightMaxVisionScorePerSecond": "0.0f"}, fl
assert cfgparse.parse(p[OBJ]).children["Player"].children["StealthParams"].values == {"FlashLightCoef": "0.0"}
print("Taschenlampe x0: Sichtpunkte 0 + Player-Koeffizient 0  OK")

# --- 5) Wachsamkeit x2 + Suchzeit x2: nur DefaultNPC, komplette Aktionen ---
p = build_patches(gd, Settings(npc_alertness_factor=2.0, npc_search_time_factor=2.0))
assert list(p) == [THR]
root = cfgparse.parse(p[THR])
assert list(root.children) == ["[1]"], list(root.children)     # DefaultNPC, nicht Boss/Mutanten
prof = root.children["[1]"]
assert prof.values == {"DefaultThreatValueFreezeTimeSeconds": "60.0",
                       "DefaultThreatValueLossPerSecond": "15.0"}, prof.values
acts = {a.values["Type"].split("::")[-1]: a.values for a in prof.children["Actions"].children.values()}
assert acts["TurnHead"]["ThreatLevelValueMin"] == "100" and acts["CallAllies"]["ThreatLevelValueMin"] == "350"
assert acts["SearchEnemy"]["ThreatValueFreezeTimeSeconds"] == "60.0" and acts["SearchEnemy"]["ThreatValueLossPerSecond"] == "10.0"
assert all(set(a) >= {"Type", "ThreatLevelValueMin", "ThreatLevelValueMax"} for a in acts.values())
# Wachsamkeit x0.5 mit Deckel MaxThreatLevelValue
p = build_patches(gd, Settings(npc_alertness_factor=0.5))
acts = {a.values["Type"].split("::")[-1]: a.values for a in cfgparse.parse(p[THR]).children["[1]"].children["Actions"].children.values()}
assert acts["CallAllies"]["ThreatLevelValueMin"] == "1000" and acts["TurnHead"]["ThreatLevelValueMin"] == "400"
print("Wachsamkeit x2 / x0.5 + Suchzeit x2: DefaultNPC, Aktionen komplett, Deckel 1000  OK")

# --- 6) Mut x2: drei Menschen-Typen, Mutant tabu -----------------------------
p = build_patches(gd, Settings(npc_courage_factor=2.0))
tac = ai(p).children["CombatTacticsSettings"].children["CombatTacticsParamsPerFactions"].children
assert set(tac) == {"Bandits", "Monolith", "Humanoid"}, set(tac)
assert tac["Bandits"].values == {"ConfidenceToAttack": "1.0f", "ConfidenceToRetreat": "0.5f"}
assert tac["Monolith"].values == {"ConfidenceToAttack": "0.25f"}      # Retreat 0 bleibt weg
print("Mut x2: Bandits 2/1 -> 1/0.5, Monolith-Rueckzug 0 bleibt, Mutant tabu  OK")

# --- 7) Wanken x0.5: menschliche Prototypen, Mutanten/Player tabu -------------
p = build_patches(gd, Settings(npc_stagger_factor=0.5))
root = cfgparse.parse(p[OBJ])
humans = set(gd.human_npc_sids())
assert set(root.children) <= humans and len(root.children) >= 1500, len(root.children)
assert "Player" not in root.children and "Bloodsucker" not in root.children
assert parse_number(root.children["GeneralNPC_Neutral_Recon"].values["CriticalDamageThreshold"]) == 20
print(f"Wanken x0.5: {len(root.children)} menschliche Prototypen, Neutral_Recon 40 -> 20  OK")

# --- 8) Difficulty: Cooldowns x, Rang +2 additiv -----------------------------
p = build_patches(gd, Settings(npc_weapon_rank_add=2, npc_attack_cooldown_factor=1.5,
                               mutant_attack_cooldown_factor=2.0))
assert list(p) == [DIF]
root = cfgparse.parse(p[DIF])
assert len(root.children) == len(gd.difficulty_values("NPCCombatDifficulty.NPC_HP"))
for sid, node in root.children.items():
    npc = node.children["NPCCombatDifficulty"].values
    assert npc == {"NPC_AttackCooldown": "1.5", "NPC_Weapon_Rank_Add": "2"}, (sid, npc)
    assert node.children["MutantCombatDifficulty"].values == {"Mutant_AttackCooldown": "2.0"}
assert not build_patches(gd, Settings(npc_weapon_rank_add=0))
print(f"Difficulty: {len(root.children)} Schwierigkeiten, Cooldowns + Rang +2  OK")

# --- 9) Director-Deckel: [i]-Eintraege komplett (AgentType + MaxCount) --------
p = build_patches(gd, Settings(encounter_pack_factor=2.0))
lim = (cfgparse.parse(p[DIR]).children["ALifeDirectorPreset"]
       .children["ALifeScenarioNPCArchetypesLimitsPerPlayerRank"])
entry = lim.children["[0]"].children["Restrictions"].children["[0]"].values
assert set(entry) == {"AgentType", "MaxCount"} and entry["AgentType"].startswith("EAgentType::"), entry
print("Director-Deckel: komplette [i]-Eintraege  OK")

# --- 10) Neutral + Summary --------------------------------------------------
assert not build_patches(gd, Settings())
s = Settings(crouch_stealth_factor=2.0, movement_noise_factor=0.5, weather_stealth_factor=2.0,
             flashlight_stealth_factor=0.5, npc_alertness_factor=0.5, npc_search_time_factor=2.0,
             npc_courage_factor=2.0, npc_stagger_factor=2.0, npc_attack_cooldown_factor=2.0,
             npc_weapon_rank_add=1, mutant_attack_cooldown_factor=2.0)
lines = summarize(s)
for needle in ("Crouch stealth", "Movement noise", "Bad-weather stealth", "Flashlight gives you away",
               "NPC alertness", "NPC search time", "NPC courage", "NPC stagger threshold",
               "NPC attack cooldown", "NPC weapon rank +1", "Mutant attack cooldown"):
    assert any(needle in l for l in lines), (needle, lines)
assert set(build_patches(gd, s)) == {AIG, OBJ, THR, DIF}
print("Neutral = kein Patch, 11 Summary-Zeilen, 4 Patch-Dateien  OK")

print("\nNPC-MORE-TEST OK")
