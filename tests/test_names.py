"""Anzeigenamen-Modul: jeder Alias zeigt auf eine real existierende
Waffe/Ruestung DIESES Spielstands (nach Spiel-Updates faengt diese Suite
verwaiste Namen — dann Zeile entfernen statt raten)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.names import WEAPON_ALIASES, ARMOR_ALIASES
from s2tweaker.tweaks import armor_label
from s2tweaker.gui import weapon_display, weapon_sid_hit

gd = GameData(VANILLA)
pw = gd.player_weapons()
pa = gd.player_armors()
dlc_w = set(gd.dlc_weapon_editions())
dlc_a = set(gd.dlc_armor_editions())

# Ohne DLC-Zweig (z.B. frisch geklonter Haupt-PC) sind genau die
# Editions-Aliase erwartbar verwaist — die werden dann uebersprungen,
# alles andere MUSS aufloesen.
DLC_W = {"Gun_Gabion_AR_GS", "Gun_Logarithm_SMG_GS", "Gun_Novator_AR_GS",
         "Gun_Margach_SG_GS", "Gun_ModelSpecial_HG_GS",
         "Gun_SMGMonolith_SMG_GS", "Gun_Monolit_HG_GS", "Gun_Monolit_AR_GS",
         "Gun_Monolit_SG_GS", "Gun_Zvirolov_SR_GS", "Gun_Veteran_AR_GS"}
DLC_A = {"SEVA_Monolith_Armor", "HeavyAnomaly_SIRCA_Armor",
         "UltraLight_Mercenaries_Armor", "HeavyExoskeleton_Varta_Armor",
         "Zorya_Tourist_Armor"}
skip_w = set() if gd.dlc_editions else DLC_W
skip_a = set() if gd.dlc_editions else DLC_A
missing_w = [sid for sid in WEAPON_ALIASES
             if sid not in pw and sid not in skip_w]
missing_a = [sid for sid in ARMOR_ALIASES
             if sid not in pa and sid not in skip_a]
assert not missing_w, f"verwaiste Waffen-Aliase: {missing_w}"
assert not missing_a, f"verwaiste Ruestungs-Aliase: {missing_a}"

n_alias_w = sum(1 for sid in pw if sid in WEAPON_ALIASES)
n_alias_a = sum(1 for sid in pa if sid in ARMOR_ALIASES)
assert n_alias_w >= 70, n_alias_w
assert n_alias_a >= 49, n_alias_a

# Stichproben: Anzeige + Suche + Armor-Label-Vorrang
assert "AKM-74S" in weapon_display("GunAK74_ST")
assert weapon_sid_hit("GunAK74_ST", "akm-74s")
assert weapon_sid_hit("Gun_Sharpshooter_AR_GS", "clusterfuck")
assert armor_label("SEVA_Neutral_Armor") == "SEVA Suit"
assert armor_label("Newbee_Neutral_Armor") == "Debut Suit"
assert armor_label("supack_vozmercform") == "supack_vozmercform"

print(f"Aliase: {n_alias_w}/{len(pw)} Waffen, {n_alias_a}/{len(pa)} "
      f"Ruestungen benannt, keine Verwaisten\nNAMES-TEST OK")
