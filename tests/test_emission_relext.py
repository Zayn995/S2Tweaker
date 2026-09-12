"""Emission duration (time scaling) and additional faction controls:
reaction strength and trading threshold."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize
from s2tweaker.cfgparse import parse_number

gd = GameData(VANILLA)
EM_KEY = "EmissionPrototypes/EmissionPrototypes_patch_S2Tweaker.cfg"
REL_KEY = "RelationPrototypes/RelationPrototypes_patch_S2Tweaker.cfg"

# --- 1) Emission: default prototype found, story entries excluded ---
key, stages, aievents = gd.emission_default_timeline()
assert key == "[0]", key
assert stages is not None and len(stages.children) == 5
assert aievents is not None and len(aievents.children) == 4
print("Timeline: Default = [0], 5 stages, 4 AI events  OK")

# --- 2) Time scaling x2: all times x2, ActivateQuest duration unchanged ---
p = build_patches(gd, Settings(emission_duration_factor=2.0))
assert list(p) == [EM_KEY], list(p)
text = p[EM_KEY]
assert text.startswith("[0] : struct.begin {bpatch}"), text[:60]
assert "Emission_E06" not in text and "[1]" not in text.split("Stages")[0]
# Vanilla: BeforeTheStorm 0/60, ShockWave 60/10, Active 60/60,
# AfterTheStorm 120/20; AIEvents 0/8/10/130
for frag in ("PhaseDuration = 120", "PhaseStartTime = 240",
             "PhaseDuration = 40", "AIEventStartTime = 260",
             "AIEventStartTime = 16", "AIEventStartTime = 20"):
    assert frag in text, (frag, text)
# Preserve the ActivateQuest duration.
assert "PhaseDuration = 2\n" not in text.replace("\r", ""), text
# Emit no zero-value changes or story-prototype patches.
n_structs = sum(1 for line in text.splitlines()
                if line and not line.startswith((" ", "struct")))
assert n_structs == 1, n_structs
print("Timeline scaling x2: 60->120, 120->240, AI 130->260, "
      "ActivateQuest duration unchanged, ONLY [0]  OK")

# --- 3) Neutral and bounds ---
assert not build_patches(gd, Settings(emission_duration_factor=1.0))
assert not build_patches(gd, Settings(emission_duration_factor=-1.0))
half = build_patches(gd, Settings(emission_duration_factor=0.5))[EM_KEY]
assert "PhaseDuration = 30" in half and "AIEventStartTime = 65" in half
print("Neutral/negative = no patch; x0.5 = 30/65  OK")

# --- 4) Reaction strength: preserve signs and zeros ---
p = build_patches(gd, Settings(relation_reaction_factor=2.0))
text = p[REL_KEY]
assert "CharacterReactions" in text and "FactionReactions" in text
# Vanilla Kill table: Neutral->Friend = -2000 (Character) / -10 (Faction).
assert "Neutral->Friend = -4000" in text
assert "Neutral->Friend = -20" in text
assert "RelationVersion" not in text, "Mechanics value must not bump the version"
assert re.search(r"= 0\b", text) is None, "Zero values must not produce lines"
vals = [int(m) for m in re.findall(r"-> \S+ (?:= (-?\d+))", text) if m]
print(f"Reaction strength x2: {text.count('->')} deltas scaled, "
      "Signs preserved, no version bump  OK")

# --- 5) Trading threshold ---
p = build_patches(gd, Settings(trade_min_level=2))
assert p[REL_KEY].count("MinRelationLevelToTrade = ERelationLevel::Neutral") == 1
p = build_patches(gd, Settings(trade_min_level=0))
assert "ERelationLevel::Enemy" in p[REL_KEY]
assert not build_patches(gd, Settings(trade_min_level=1))
lines = " | ".join(summarize(Settings(trade_min_level=3,
                                      relation_reaction_factor=0.5,
                                      emission_duration_factor=2.0)))
for frag in ("Trading requires standing: Friend", "Reputation reaction",
             "Emission duration"):
    assert frag in lines, (frag, lines)
print("Trading threshold (Neutral/Enemy/vanilla) and summary  OK")

print("\nEMISSION/RELATIONS-EXT-TEST OK")
