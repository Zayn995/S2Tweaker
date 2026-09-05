"""S2Tweaker GUI (customtkinter, dunkel, englische Oberflaeche)."""

from __future__ import annotations

import datetime
import json
import math
import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __version__, faq, game, modscan, pakio
from .gamedata import GameData
from .tweaks import (
    ALL_CATEGORIES,
    AMMO_CALIBER_LABELS,
    CALIBERS_ODD,
    ARMOR_PARAM_LABELS,
    ARMOR_PARAMS,
    AMMO_PARAM_KEYS,
    AMMO_PARAM_LABELS,
    AMMO_PARAMS,
    AMMO_TYPE_LABELS,
    CATEGORY_LABELS,
    WEAPON_CATEGORY_LABELS,
    WEAPON_PARAM_LABELS,
    WEAPON_PARAMS,
    Settings,
    ammo_label,
    armor_label,
    build_patches,
    caliber_label,
    caliber_warning,
    summarize,
    swappable_calibers,
    weapon_available_params,
)

APP_TITLE = f"S2Tweaker {__version__} – S.T.A.L.K.E.R. 2 Mod Generator"

# KEIN Netzwerkcode. Seit 1.19.2 stellt das Programm ueberhaupt keine
# Verbindung mehr her — auch nicht auf Knopfdruck. Grund: Nexus' eigene
# Regeln nennen internetfaehige Programme unzulaessig, "unless where it is
# crucial", und sagen ausdruecklich, dass "'auto update' functionality does
# not qualify as crucial". Ohne urllib laesst sich das im oeffentlichen
# Quelltext mit einem einzigen grep nachpruefen — und genau diese
# Nachpruefbarkeit ist gegenueber Moderation und Virenscannern mehr wert
# als der Komfort eines Update-Knopfes. Nicht wieder einbauen.


def app_dir() -> Path:
    """Ordner der EXE (gefroren) bzw. des Projekts (Entwicklung).

    Das Tool ist PORTABLE: Einstellungen, Cache und Output liegen alle
    neben der EXE — Ordner loeschen entfernt alles restlos.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _asset(*parts: str) -> Path:
    """Pfad zu einer mitgelieferten Datei (Bilder, Icon).

    Der `assets`-Ordner liegt neben dem Paket: im Repo `assets/`, im
    ausgelieferten Programmordner `_internal/assets/` (tools/build_exe.py
    kopiert ihn dorthin). Derselbe Weg in beiden Faellen."""
    return Path(__file__).resolve().parent.parent / "assets" / Path(*parts)


def output_dir() -> Path:
    return app_dir() / "output"


def cache_dir() -> Path:
    return app_dir() / "cache"


def presets_dir() -> Path:
    return app_dir() / "presets"


SETTINGS_FILE = app_dir() / "settings.json"

# Eingebettetes Manifest an der Pak-WURZEL (nicht unter GameData — dort
# scannt das Spiel nach Configs; an der Wurzel ist die Datei garantiert
# wirkungslos). Macht jede gebaute Pak zu einem wieder ladbaren Preset.
MANIFEST_NAME = "S2Tweaker_Manifest.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

PAD = {"padx": 12, "pady": 3}

# Bernstein: eine einzige Quelle fuer Suchtreffer, Warnhinweise und
# Override-Marker im Waffenbaum.
ACCENT = "#d9a648"

# Mod-Scan-Markierungen: bewusst WEDER rot (Gefahr/Remove-Knopf) NOCH das
# Bernstein der Warnhinweise und Suchtreffer — beides hat schon eine
# Bedeutung. Blau = reine Information, Violett = Warnstufe.
MARK_INFO = "#5da8dc"   # fremde Mod aendert den Wert, Regler steht auf (vanilla)
MARK_WARN = "#b07fe0"   # fremde Mod aendert den Wert UND der Regler ist verstellt

# --- Fraktionsbeziehungen (Tab "Factions") -------------------------------
# Kuratierte Haupt-Fraktionen: (cfg-SID, englischer PDA-Anzeigename).
# Story-/Boss-/Arena-Fraktionen bleiben bewusst draussen
# (docs/FACTION_RELATIONS_RESEARCH.md, Abschnitt WARNUNGEN). "Mutant"
# ist die Schirm-Fraktion aller Mutanten und steht als letzte, damit
# jeder Fraktions-Block seine "vs. Mutants"-Zeile bekommt.
FACTION_CHOICES = [
    ("Neutrals", "Loners"),
    ("Bandits", "Bandits"),
    ("Militaries", "Military"),
    ("Varta", "Ward"),
    ("Duty", "Duty"),
    ("Freedom", "Freedom"),
    ("Mercenaries", "Mercenaries"),
    ("Monolith", "Monolith"),
    ("Noon", "Noontide"),
    ("Spark", "Spark"),
    ("Corpus", "Corps"),
    ("Scientists", "Scientists"),
    ("Mutant", "Mutants (all)"),
]


def relation_level(value: float) -> str:
    """Kurzer Levelname zur Zahl (RelationLevelRanges der Spieldaten:
    <= -800 Enemy, -799..-201 Disaffection, -200..200 Neutral, ab 201
    Friend). "wary" statt "Disaffection", damit es neben den Slider passt;
    der Sektions-Hinweis nennt den offiziellen Begriff."""
    v = int(round(value))
    if v <= -800:
        return "enemy"
    if v <= -201:
        return "wary"
    if v <= 200:
        return "neutral"
    return "friend"


def fmt_relation(value: float) -> str:
    return f"{int(round(value))} · {relation_level(value)}"


# Anzeigenamen (Waffen + Ruestungen): s2tweaker/names.py — verifizierte
# Community-Masterliste des Besitzers (02.09.). Reine UI-/Suchhilfe.
from .names import WEAPON_ALIASES


def weapon_display(sid: str) -> str:
    alias = WEAPON_ALIASES.get(sid)
    return f"{sid}  ·  „{alias}“" if alias else sid


def weapon_sid_hit(sid: str, query: str) -> bool:
    """Suchtreffer auf SID ODER Anzeigenamen (AKM-74S, Riemann & Co.)."""
    return (query in sid.lower()
            or query in WEAPON_ALIASES.get(sid, "").lower())


def fmt_trade_level(value: float) -> str:
    """Handels-Schwelle als Levelname (0..3; Vanilla = Disaffected)."""
    level = max(0, min(3, int(round(value))))
    return ("Enemy", "Disaffected", "Neutral", "Friend")[level]


# --- Mutanten-Tab: Arten-Baum --------------------------------------------
MUT_PARAM_LABELS = {  # Reihenfolge = Regler-Reihenfolge je Art
    "hp": "Health",
    "speed": "Speed",
    "damage": "Damage (each attack)",
    "regen": "Health regen",
}

# Reine ANZEIGE-Gruppierung (nach Groesse/Charakter, keine Spielwerte);
# Arten, die hier nicht stehen (kuenftige Spiel-Patches, "Mutant"-Generika),
# landen automatisch im Block "Other species".
MUT_GROUPS = [
    ("small", "Small critters",
     ["Rat", "Tushkan", "Blinddog", "MoldyBlinddog", "Bayun"]),
    ("medium", "Medium beasts",
     ["Boar", "Flesh", "Deer", "Pseudodog", "Snork"]),
    ("humanoid", "Humanoids & psi mutants",
     ["Bloodsucker", "Burer", "Controller", "Poltergeist"]),
    ("large", "Large predators",
     ["Chimera", "Pseudogiant"]),
]

MUT_SPECIES_LABELS = {
    "Bayun": "Bayun (cat)",
    "Blinddog": "Blind dog",
    "MoldyBlinddog": "Moldy blind dog",
    "Mutant": "Generic mutant",
    "Rat": "Rat swarm",
}


def mutant_species_label(species: str) -> str:
    return MUT_SPECIES_LABELS.get(species, species)


class FaqRow:
    """Eine Frage im FAQ-Fenster: Frage-Knopf, Antwort klappt auf.

    Die Suche laeuft ueber q + a + die unsichtbaren Schlagworte (k) aus
    faq.py — so findet "health pack" auch den Consumable-Regler."""

    def __init__(self, parent, entry: dict, font_q, font_a):
        self.entry = entry
        self.haystack = " ".join(
            (entry["q"], entry["a"], entry.get("k", ""))).lower()
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.btn = ctk.CTkButton(
            self.frame, text="\u25b8  " + entry["q"], anchor="w",
            fg_color="transparent", hover_color="gray25", font=font_q,
            command=self.toggle)
        self.btn.pack(fill="x")
        self.answer = ctk.CTkLabel(
            self.frame, text=entry["a"], anchor="w", justify="left",
            wraplength=640, font=font_a, text_color="gray80")
        self.open = False

    def toggle(self):
        self.set_open(not self.open)

    def set_open(self, open_: bool):
        self.open = open_
        if open_:
            self.answer.pack(fill="x", padx=24, pady=(0, 6))
            self.btn.configure(text="\u25be  " + self.entry["q"])
        else:
            self.answer.pack_forget()
            self.btn.configure(text="\u25b8  " + self.entry["q"])

    def matches(self, words: list[str]) -> bool:
        return all(w in self.haystack for w in words)


class HoverTip:
    """Minimaler Hover-Tooltip (fuer die Scan-Punkte an Reglern/Checkboxen).

    text_fn wird erst beim Zeigen ausgewertet — der Text eines Punkts
    aendert sich mit dem Reglerzustand (Info- vs. Warnstufe)."""

    def __init__(self, widget, text_fn):
        self.widget = widget
        self.text_fn = text_fn
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        text = self.text_fn()
        if not text or self.tip is not None:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(
            f"+{self.widget.winfo_rootx() + 12}+{self.widget.winfo_rooty() + 24}")
        tk.Label(self.tip, text=text, justify="left", bg="#1f1f1f",
                 fg="#e6e6e6", relief="solid", borderwidth=1,
                 font=("Segoe UI", 9), padx=8, pady=4, wraplength=380).pack()

    def _hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class SliderRow:
    """Label + Slider + Wertanzeige + Reset auf Vanilla."""

    def __init__(self, parent, label: str, from_: float, to: float, step: float,
                 default: float, fmt, tooltip: str = "", on_change=None,
                 log: bool = False):
        self.default = default
        self.fmt = fmt
        self.on_change = on_change
        # Wertebereich in WERT-Einheiten (auch im Log-Modus); get()/set()
        # sprechen immer Werte, nur die Schiene rechnet intern in log10.
        self.lo, self.hi = float(from_), float(to)
        self.log = bool(log)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", **PAD)
        self.row = row
        self.conflict_mods: list[str] = []   # Mod-Scan: wer aendert das auch?
        self.conflict_after: set[str] = set()
        self.conflict_unknown: set[str] = set()  # Workshop: Reihenfolge unklar
        self.locked = False                  # Avoid-conflicts-Sperre
        self._on_unlock = None
        self._base_state = "normal"
        self.dot: ctk.CTkLabel | None = None
        self._dot_tip = ""
        self.label = ctk.CTkLabel(row, text=label, width=260, anchor="w")
        self.label.pack(side="left")
        if self.log:
            # Logarithmische Schiene (GitHub #4 "Higher health value"): feine
            # Schritte nahe Vanilla, oben bis 100000. Bewusst OHNE
            # number_of_steps: CTkSlider.set() rastet sonst auf Log-Schritte
            # und aus set(250) wuerde 251 - get() rundet stattdessen auf
            # 3 signifikante Stellen.
            self.slider = ctk.CTkSlider(
                row, from_=math.log10(self.lo), to=math.log10(self.hi),
                command=self._changed
            )
        else:
            steps = max(1, int(round((to - from_) / step)))
            self.slider = ctk.CTkSlider(
                row, from_=from_, to=to, number_of_steps=steps, command=self._changed
            )
        self.slider.pack(side="left", fill="x", expand=True, padx=8)
        self.value_label = ctk.CTkLabel(row, text="", width=110, anchor="e")
        self.value_label.pack(side="left")
        self.reset_btn = ctk.CTkButton(row, text="↺", width=28, command=self.reset)
        self.reset_btn.pack(side="left", padx=(6, 0))
        self._orig_color = self.label.cget("text_color")
        self.set(default)
        if tooltip:
            hint = ctk.CTkLabel(parent, text="   " + tooltip, anchor="w",
                                font=ctk.CTkFont(size=11), text_color="gray60")
            hint.pack(fill="x", padx=12)

    def _changed(self, _=None):
        value = self.get()
        vanilla = "  (vanilla)" if abs(value - self.default) < 1e-9 else ""
        lock = "  \U0001f512" if self.locked else ""
        self.value_label.configure(text=self.fmt(value) + vanilla + lock)
        if self.conflict_mods:
            self._update_dot()
        if self.on_change is not None:
            self.on_change()

    def get(self) -> float:
        if self.log:
            value = 10.0 ** float(self.slider.get())
            mag = 10.0 ** math.floor(math.log10(max(value, 1e-9)))
            value = round(value / mag * 100.0) / 100.0 * mag   # 3 signifikante Stellen
            return round(min(self.hi, max(self.lo, value)), 4)
        return round(float(self.slider.get()), 4)

    def set(self, value: float):
        if self.log:
            self.slider.set(math.log10(min(self.hi, max(self.lo, float(value)))))
        else:
            self.slider.set(value)
        self._changed()

    def reset(self):
        self.set(self.default)

    def set_state(self, state: str):
        # Basiszustand merken: eine Avoid-Sperre haelt den Regler auch dann
        # deaktiviert, wenn die GUI insgesamt wieder freigeschaltet wird.
        self._base_state = state
        self.slider.configure(state="disabled" if self.locked else state)
        self.reset_btn.configure(state=state)

    def set_locked(self, locked: bool, on_unlock=None):
        """Avoid-conflicts-Sperre: Regler deaktiviert, der Reset-Knopf wird
        zum Entsperr-Knopf (bewusstes Freischalten je Regler)."""
        if locked == self.locked:
            self._on_unlock = on_unlock or self._on_unlock
            return
        self.locked = locked
        self._on_unlock = on_unlock
        if locked:
            self.slider.configure(state="disabled")
            self.reset_btn.configure(text="\U0001f513", command=self._unlock)
        else:
            self.slider.configure(state=self._base_state)
            self.reset_btn.configure(text="\u21ba", command=self.reset)
        self._changed()
        if self.conflict_mods:
            self._update_dot()

    def _unlock(self):
        if self._on_unlock is not None:
            self._on_unlock()

    def set_highlight(self, mode: str):
        """Suchfilter: 'match' = hervorheben, 'dim' = abdunkeln."""
        if mode == "match":
            color = ACCENT
        elif mode == "dim":
            color = "gray35"
        else:
            color = self._orig_color
        self.label.configure(text_color=color)

    # ------------------------------------------------- Mod-Scan-Markierung
    def set_conflict(self, mods, loads_after=(), order_unknown=()):
        """Farbpunkt "eine andere Mod aendert das auch" setzen/entfernen.

        loads_after: Teilmenge der Mods, deren Pak ALPHABETISCH nach der
        eigenen Ausgabe-Pak laedt — dort gewinnt im Konfliktfall die fremde
        Mod, und der Tooltip darf nicht "your value wins" behaupten.
        order_unknown: Steam-Workshop-Mods — deren Ladereihenfolge regelt
        das Spiel selbst, "your value wins" waere dort geraten.

        Der Punkt haengt NICHT am Reglerwert: "Reset all to vanilla" laesst
        ihn absichtlich stehen (die fremde Mod ist ja weiterhin installiert)
        — nur seine Stufe wechselt dann von Warnung auf Information."""
        self.conflict_mods = sorted(mods or [])
        self.conflict_after = set(loads_after) & set(self.conflict_mods)
        self.conflict_unknown = set(order_unknown) & set(self.conflict_mods)
        self._update_dot()

    def _update_dot(self):
        if not self.conflict_mods:
            if self.dot is not None:
                self.dot.pack_forget()
            self._dot_tip = ""
            return
        if self.dot is None:
            self.dot = ctk.CTkLabel(self.row, text="\u25cf", width=16)
            HoverTip(self.dot, lambda: self._dot_tip)
        names = ", ".join(self.conflict_mods)
        if self.locked:
            self.dot.configure(text_color=MARK_INFO)
            self._dot_tip = (f"locked by Avoid conflicts \u2014 {names} changes "
                             "this; click \U0001f513 to unlock this slider")
        elif abs(self.get() - self.default) < 1e-9:
            self.dot.configure(text_color=MARK_INFO)
            self._dot_tip = f"also changed by {names}"
        else:
            self.dot.configure(text_color=MARK_WARN)
            notes = []
            if self.conflict_after:
                notes.append(", ".join(sorted(self.conflict_after))
                             + " loads AFTER your pak, so its value may win")
            if self.conflict_unknown:
                notes.append(", ".join(sorted(self.conflict_unknown))
                             + " is loaded by the game's own mod manager "
                             "(load order unknown), so its value may win")
            if notes:
                self._dot_tip = (f"{names} changes this too \u2014 and "
                                 + "; ".join(notes))
            else:
                self._dot_tip = (
                    f"{names} changes this too \u2014 your value wins")
        if not self.dot.winfo_manager():
            self.dot.pack(side="left", after=self.label)


def fmt_min(v: float) -> str:
    return f"{int(round(v))} min"


def fmt_int(v: float) -> str:
    return f"{v:.0f}"


def fmt_pct(v: float) -> str:
    return f"{v:.0f} %"


def fmt_factor(v: float) -> str:
    return f"× {v:g}"


def fmt_kg(v: float) -> str:
    return f"{v:.0f} kg"


def fmt_dec(v: float) -> str:
    return f"{v:g}"


# ------------------------------------------------------------------ Mod-Scan
# Zuordnung GUI-Schluessel -> Settings-Feld. Wird NUR vom Mod-Scan benutzt,
# um den Fussabdruck EINES Reglers zu bestimmen (build_patches mit genau
# einem verstellten Wert -> welche (Struct, Blatt)-Paare entstehen?).
# Der Release-GUI-Test prueft die Vollstaendigkeit gegen app.sliders —
# ein neuer Regler ohne Eintrag hier faellt dort auf, nicht erst auf Nexus.
SLIDER_FIELDS: dict[str, str] = {
    "hp": "max_hp", "hp_regen": "hp_regen", "sp": "max_stamina",
    "sp_regen": "stamina_regen", "fall": "fall_damage_pct",
    "walk": "walk_speed_factor", "run": "run_speed_factor",
    "jump": "jump_height_factor", "vault_height": "vault_height_factor",
    "vault_distance": "vault_distance_factor",
    "vault_angle": "vault_angle_factor",
    "vault_min_height": "vault_min_height_factor",
    "vault_landing": "vault_landing_factor",
    "vault_over_depth": "vault_over_depth_factor",
    "vault_over_offset": "vault_over_offset_factor",
    "st_sprint": "stamina_sprint",
    "st_jump": "stamina_jump", "st_melee_l": "stamina_melee_light",
    "st_melee_s": "stamina_melee_strong", "st_butt": "stamina_buttstock",
    "st_vault": "stamina_vault", "carry": "max_carry_weight",
    "penalty": "penalty_start_weight", "weight": "item_weight_factor",
    "pdmg": "player_damage_factor", "headshot": "headshot_factor",
    "aimpunch": "aim_punch_factor", "npcdmg": "npc_damage_factor",
    "npchp": "npc_hp_factor", "npc_acc": "npc_accuracy_factor",
    "npc_vision": "npc_vision_factor", "npc_hearing": "npc_hearing_factor",
    "npc_reaction": "npc_reaction_factor", "npc_grenades": "npc_grenade_factor",
    "alife_agents": "max_agents_factor", "alife_distance": "spawn_distance_factor",
    "lair_mutants": "lair_mutant_factor", "lair_humans": "lair_human_factor",
    "lair_respawn": "lair_respawn_factor",
    "enc_freq": "encounter_frequency_factor",
    "enc_mutants": "encounter_mutant_factor", "enc_pack": "encounter_pack_factor",
    "enc_blinddog": "enc_blinddog_factor", "enc_boar": "enc_boar_factor",
    "enc_flesh": "enc_flesh_factor", "enc_tushkan": "enc_tushkan_factor",
    "enc_chimera": "enc_chimera_factor",
    "enc_generic": "enc_generic_mutant_factor",
    "npc_gear": "npc_gear_quality_factor",
    "npc_free_shots": "npc_free_shots_factor", "npc_burst": "npc_burst_factor",
    "npc_fire_pause": "npc_fire_pause_factor", "npc_engage": "npc_engage_range_factor",
    "npc_range": "npc_weapon_range_factor", "npc_regen": "npc_regen_factor",
    "stealth_crouch": "crouch_stealth_factor", "stealth_noise": "movement_noise_factor",
    "stealth_weather": "weather_stealth_factor",
    "stealth_flashlight": "flashlight_stealth_factor",
    "npc_alertness": "npc_alertness_factor", "npc_search": "npc_search_time_factor",
    "npc_courage": "npc_courage_factor", "npc_stagger": "npc_stagger_factor",
    "npc_attack_cd": "npc_attack_cooldown_factor",
    "npc_rank_add": "npc_weapon_rank_add",
    "npc_light": "npc_flashlight_factor", "npc_light_cone": "npc_flashlight_cone_factor",
    "npc_light_combat": "npc_flashlight_combat_factor",
    "npc_light_on": "npc_flashlight_on_hour", "npc_light_off": "npc_flashlight_off_hour",
    "save_manual": "manual_save_slots", "save_quick": "quick_save_slots",
    "save_auto": "auto_save_slots", "autosave_min": "autosave_interval_min",
    "mut_attack_cd": "mutant_attack_cooldown_factor",
    "mhp": "mutant_hp_factor", "mdmg": "mutant_damage_factor",
    "mspeed": "mutant_speed_factor", "mhearing": "mutant_hearing_factor",
    "mut_regen": "mutant_regen_factor",
    "bs_cloak": "bloodsucker_cloak_factor", "bs_uncloak": "bloodsucker_uncloak_factor",
    "expl": "explosion_damage_factor", "dur": "durability_factor",
    "dur_armor": "armor_durability_factor", "jam": "jamming_factor",
    "ap_strike": "armor_strike_factor", "ap_burn": "armor_burn_factor",
    "ap_shock": "armor_shock_factor", "ap_chem": "armor_chemical_factor",
    "ap_rad": "armor_radiation_factor", "ap_psy": "armor_psy_factor",
    "ap_carry": "armor_carry_bonus_factor", "sway": "scope_sway_pct",
    "breath_drain": "breath_drain_factor", "breath_regen": "breath_regen_factor",
    "spread": "spread_factor", "recoil": "recoil_factor",
    "recoil_upgrades": "recoil_upgrade_factor",
    "wrange": "weapon_range_factor", "wbleed": "weapon_bleeding_factor",
    "adsmove": "ads_speed_factor", "aimspeed": "aim_time_factor",
    "magazine": "magazine_factor",
    "melee": "melee_damage_factor", "melee_range": "melee_range_factor",
    "interact": "interaction_range_factor", "dialog_range": "dialog_range_factor",
    "ammo_dmg": "ammo_damage_factor",
    "ammo_ap": "ammo_piercing_factor", "ammo_ad": "ammo_armor_damage_factor",
    "ammo_cover": "ammo_cover_factor", "anomaly": "anomaly_damage_factor",
    "anom_electro": "anomaly_electro_factor", "anom_chem": "anomaly_chemical_factor",
    "anom_fire": "anomaly_fire_factor", "anom_grav": "anomaly_gravity_factor",
    "radiation": "radiation_factor", "bleeding": "bleeding_factor",
    "hunger": "hunger_rate_factor", "sleep": "sleepiness_rate_factor",
    "consumable": "consumable_factor", "healing": "healing_factor",
    "cons_duration": "consumable_duration_factor", "day_length": "day_length_factor",
    "art_count": "artifact_count_factor", "art_respawn": "artifact_respawn_factor",
    "rain": "rain_factor",
    "emission": "emission_factor", "stash_loot": "stash_loot_factor",
    "stash_chance": "stash_chance_factor", "stash_ammo": "stash_ammo_factor",
    "loot_amount": "loot_amount_factor", "art_effect": "artifact_effect_factor",
    "art_radiation": "artifact_radiation_factor", "art_spawn": "artifact_spawn_factor",
    "art_rarity": "artifact_rarity_factor", "detector": "detector_range_factor",
    "fasttravel": "fast_travel_cost_factor", "restock": "trader_restock_factor",
    "trader_dur": "trader_min_durability_pct",
    "drop_cond": "dropped_condition_pct",
    "trader_stock": "trader_stock_factor",
    "trader_variety": "trader_variety_factor",
    "trader_money": "trader_money_factor",
    "buyprice": "trader_buy_price_factor",
    "sellprice": "trader_sell_price_factor", "repair": "repair_cost_factor",
    "upgrade": "upgrade_cost_factor", "questreward": "quest_reward_factor",
    "rq_cooldown": "repeatable_quest_factor",
    "price_weapon": "weapon_price_factor", "price_armor": "armor_price_factor",
    "price_ammo": "ammo_price_factor", "price_artifact": "artifact_price_factor",
    "price_consumable": "consumable_price_factor",
    "rel_rollback": "relation_rollback_factor",
    "rel_reaction": "relation_reaction_factor",
    "rel_trade": "trade_min_level",
    "emission_dur": "emission_duration_factor",
}

CHECK_FIELDS: dict[str, str] = {
    "improved_vaulting": "improved_vaulting",
    "vault_sprint": "vault_sprint",
    "no_overweight": "no_overweight_penalty",
    "ignore_equipped": "ignore_equipped_weight",
    "quest_weightless": "quest_items_weightless",
    "npc_no_heal": "npc_no_heal",
    "drop_cond_exact": "dropped_condition_exact",
    "trader_inf_money": "trader_infinite_money",
    "upgrades_take_both": "upgrades_take_both",
    "upgrades_no_blueprint": "upgrades_no_blueprint",
    "upgrades_no_tiers": "upgrades_no_tiers",
}

# Sonderwerte, wo "Default x 2" keinen (sinnvollen) Patch ergaebe.
FOOTPRINT_PROBES: dict[str, float] = {
    "fall_damage_pct": 50.0,
    "npc_weapon_rank_add": 2.0,
    "scope_sway_pct": 50.0,
    "trader_min_durability_pct": 0.0,
}

# Teure Fussabdruecke: nur berechnen, wenn die gescannten Mods plausibel
# etwas Passendes anfassen — loot_amount parst sonst grundlos die
# 9,3-MB-Datei, npc_no_heal geht ueber 1.601 NPC-Prototypen. Zwei billige
# Ausloeser je Schluessel: der Basis-Dateiname taucht in einem Pfadsegment
# auf ODER eines der typischen Blattfelder in den gescannten Paaren —
# {bpatch}-Dateien duerfen naemlich unter voellig freiem Namen irgendwo
# unter GameData liegen, der Dateiname allein reicht nachweislich nicht.
EXPENSIVE_FOOTPRINTS: dict[str, tuple[str, frozenset]] = {
    "rq_cooldown": ("QuestNodePrototypes",
                    frozenset({"InGameHours"})),
    "loot_amount": ("ItemGeneratorPrototypes",
                    frozenset({"MinCount", "MaxCount"})),
    "drop_cond": ("ItemGeneratorPrototypes",
                  frozenset({"MinDurability", "MaxDurability"})),
    "check:drop_cond_exact": ("ItemGeneratorPrototypes",
                              frozenset({"MinDurability", "MaxDurability"})),
    "trader_stock": ("ItemGeneratorPrototypes",
                     frozenset({"MinCount", "MaxCount"})),
    "trader_variety": ("ItemGeneratorPrototypes",
                       frozenset({"Chance"})),
    "stash_loot": ("StashPrototypes",
                   frozenset({"MinCount", "MaxCount"})),
    "stash_chance": ("StashPrototypes",
                     frozenset({"MinSpawnChance", "MaxSpawnChance"})),
    "stash_ammo": ("StashPrototypes",
                   frozenset({"MainWeaponAmmoCount"})),
    "check:npc_no_heal": ("ObjPrototypes", frozenset({"RegenHP"})),
    "check:upgrades_take_both": ("UpgradePrototypes",
                                 frozenset({"BlockingUpgradePrototypeSIDs"})),
    "check:upgrades_no_blueprint": ("UpgradePrototypes",
                                    frozenset({"RequiredItemPrototypeSIDs"})),
    "check:upgrades_no_tiers": ("UpgradePrototypes",
                                frozenset({"RequiredUpgradePrototypeSIDs"})),
    "lair_mutants": ("LairPrototypes", frozenset({"MaxSpawnQuantity"})),
    "lair_humans": ("LairPrototypes", frozenset({"MaxSpawnQuantity"})),
    "lair_respawn": ("LairPrototypes",
                     frozenset({"InitialSpawnQuantityRespawnTimeSeconds",
                                "MaxSpawnQuantityRespawnTimeSeconds",
                                "WipeRespawnTimeoutSeconds"})),
}


def footprint_settings(key: str) -> list[Settings] | None:
    """Settings-Sonden mit GENAU EINEM verstellten Regler (Fussabdruck).

    Liefert bis zu ZWEI Sonden (Default x2 UND x0.5): Builder mit Deckel
    oder Boden emittieren sonst nur die halbe Wahrheit — bei x2 fehlen z.B.
    alle Fundchancen, die in Vanilla schon auf 1.0 stehen (nachgewiesen:
    9 von 19 Stash-Prototypen), bei x0.5 die Werte am unteren Anschlag.
    Der Fussabdruck ist die VEREINIGUNG beider Sonden.

    None = Schluessel bewusst nicht markierbar: die wcat_-Kategorie- und die
    Baum-Regler (Waffen/Munition/Mutanten) laufen ueber die globalen Regler
    mit — deren Fussabdruck deckt dieselben Dateien ab."""
    if key.startswith("check:"):
        field_name = CHECK_FIELDS.get(key[len("check:"):])
        return None if field_name is None else [Settings(**{field_name: True})]
    field_name = SLIDER_FIELDS.get(key)
    if field_name is None:
        return None
    # npc_gear patcht AUSSCHLIESSLICH Weight-Blaetter — und genau die
    # schliesst der Scan-Vergleich bewusst aus (Kollisions-Haertung,
    # ROADMAP Mod-Scan). Ein Fussabdruck waere immer leer; der Regler ist
    # damit wie die Baum-Regler nicht markierbar.
    if field_name == "npc_gear_quality_factor":
        return None
    default = getattr(Settings(), field_name)
    if field_name in FOOTPRINT_PROBES:
        probes = [FOOTPRINT_PROBES[field_name]]
    elif default:
        probes = [default * 2, default * 0.5]
    else:
        probes = [1.0]
    extra = {}
    if field_name == "item_weight_factor":
        # Der Gewichts-Builder patcht nur die angehakten Kategorien
        extra["item_weight_categories"] = set(ALL_CATEGORIES)
    return [Settings(**{field_name: p}, **extra) for p in probes]


class IwWeaponRow:
    """Aufklappbare Zeile EINER Waffe im Overrides-Baum.

    Die Regler entstehen erst beim ERSTEN Aufklappen (lazy) und werden
    danach wiederverwendet. Einzige Wahrheit bleibt app.weapon_overrides —
    eine nie geoeffnete Waffe hat gar keine Widgets, die veralten koennten.
    """

    def __init__(self, app, parent, sid: str, cat: str):
        self.app = app
        self.sid = sid
        self.cat = cat
        # Nur die Parameter, die es fuer diese Waffe in den Spieldaten gibt
        # (wie im Munitions- und Ruestungsbaum). Ohne bekannte Liste bleibt
        # es bei allen zehn.
        self.params = list(app._iw_params.get(sid) or WEAPON_PARAMS)
        self.body = None                       # CTkFrame, erst bei build()
        self.sliders: dict[str, SliderRow] = {}
        self.cal_menu = None                   # Kaliber-Dropdown (Issue #6)
        self.cal_warn = None                   # Warnzeile darunter
        self._cal_vanilla = None
        self._cal_values: list[str] = []
        self._cal_labels: list[str] = []
        self.reset_btn = None
        self.expanded = False
        self._highlight = "normal"
        self._state = app._iw_state            # zuletzt durchgereichter Zustand
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_row,
            command=self.toggle, state=app._iw_state)
        self.btn.pack(fill="x", padx=(16, 8), pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.refresh()

    # ------------------------------------------------------------ Aufbau
    def build(self):
        """Lazy: Hinweis, 8 Regler und Reset-Knopf einmalig erzeugen."""
        if self.body is not None:
            return
        self.body = ctk.CTkFrame(self.frame, fg_color="transparent")
        shared = self.app._iw_share.get(self.sid)
        if shared:
            ctk.CTkLabel(
                self.body,
                text="   shares combat stats with: " + ", ".join(shared),
                anchor="w", justify="left", wraplength=700,
                font=self.app._iw_font_hint, text_color="gray60",
            ).pack(fill="x", padx=12, pady=(2, 0))
        edition = self.app._iw_dlc.get(self.sid)
        if edition:
            name = {"PreOrder": "Pre-order"}.get(edition, edition)
            ctk.CTkLabel(
                self.body,
                text=f"   {name}-edition weapon – overrides on it patch "
                     "the DLC config branch (untested in-game; harmless "
                     "if you don't own that edition).",
                anchor="w", justify="left", wraplength=700,
                font=self.app._iw_font_hint, text_color="gray60",
            ).pack(fill="x", padx=12, pady=(2, 0))
        if len(self.params) < len(WEAPON_PARAMS):
            missing = [WEAPON_PARAM_LABELS[p].lower()
                       for p in WEAPON_PARAMS if p not in self.params]
            ctk.CTkLabel(
                self.body,
                text="   the game data has no " + ", ".join(missing)
                     + (" values" if len(missing) > 1 else " value")
                     + " for this weapon – no slider is offered for "
                     + ("them." if len(missing) > 1 else "it."),
                anchor="w", justify="left", wraplength=700,
                font=self.app._iw_font_hint, text_color="gray60",
            ).pack(fill="x", padx=12, pady=(2, 0))
        self._build_caliber_row()
        # Sperre waehrend des Aufbaus: SliderRow.__init__ ruft set(default)
        # und damit _changed auf — ohne Sperre wuerde der halb gefuellte
        # Regler-Satz den gespeicherten Override der Waffe ueberschreiben.
        # Alten Wert merken und zuruecklegen, damit ein verschachtelter
        # Aufruf (z. B. aus _iw_refresh_all heraus) die Sperre nicht loest.
        prev = self.app._iw_loading
        self.app._iw_loading = True
        # Der Aufbau der 8 Regler dauert spuerbar (~0,4 s): Sanduhr zeigen,
        # damit der erste Klick auf eine Waffe nicht wie ein Haenger wirkt.
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for param in self.params:
                self.sliders[param] = SliderRow(
                    self.body, WEAPON_PARAM_LABELS[param], 0.25, 4, 0.25, 1,
                    fmt_factor, on_change=self._changed)
        finally:
            self.app._iw_loading = prev
            try:
                self.app.configure(cursor="")
            except Exception:
                pass
        self.reset_btn = ctk.CTkButton(
            self.body, text="↺  Reset this weapon", width=170,
            fg_color="transparent", border_width=1, command=self.reset)
        self.reset_btn.pack(anchor="w", padx=12, pady=(2, 4))
        # Duenne Trennlinie: sonst klebt der Knopf optisch an der naechsten Waffe
        ctk.CTkFrame(self.body, height=2, corner_radius=0,
                     fg_color="gray35").pack(fill="x", padx=12, pady=(4, 6))
        self.load_values()                      # setzt _iw_loading selbst
        # Leerer Merkwert erzwingt das Durchreichen an die NEUEN Regler,
        # auch wenn sich der Zustand seit dem Zeilenbau nicht geaendert hat.
        self._state = ""
        self.set_state(self.app._iw_state)      # koennte noch gesperrt sein

    # ----------------------------------------------------------- Kaliber
    def _build_caliber_row(self):
        """Dropdown "Ammunition" (GitHub Issue #6, Wunsch von Molkerr).

        Steht ueber den Reglern, weil es die Waffe grundsaetzlicher
        veraendert als jeder Faktor. KEIN Kaskaden-Element: ein Kaliber
        ist ein Name, kein Faktor — es stapelt nicht mit Kategorie oder
        globalem Regler und gibt es deshalb nur je Waffe.

        Es wird bewusst NICHTS gesperrt: auch Schrot, Gauss und Werfer
        stehen drin. Was dabei kaputtgeht, sagt die Warnzeile darunter —
        mit der echten, aus den Spieldaten gerechneten Zahl."""
        vanilla = self.app._iw_caliber.get(self.sid)
        if vanilla is None:
            return                      # Waffe ohne Kaliber (Messer o. Ae.)
        options = self.app._iw_caliber_options
        if not options:
            return
        self._cal_vanilla = vanilla
        self._cal_values = [""] + [c for c in options if c != vanilla]
        labels = [f"vanilla ({caliber_label(vanilla)})"] + [
            caliber_label(c) for c in self._cal_values[1:]]
        self._cal_labels = labels
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(row, text="Ammunition", width=260, anchor="w",
                     font=self.app._iw_font_row).pack(side="left")
        self.cal_menu = ctk.CTkOptionMenu(
            row, values=labels, width=230, command=self._caliber_changed)
        self.cal_menu.pack(side="left")
        # Zwei Hinweise, die immer gelten (also nicht erst bei Auswahl):
        # der Schaden bleibt, und NPC-Waffen haengen mit dran.
        users = self.app._iw_setup_users.get(self.sid, 1)
        note = ("Changes which rounds the weapon takes - not its damage. "
                "Damage comes from the weapon itself (the slider below); "
                "a swap changes penetration, bullet flight, price and how "
                "easy the ammo is to find.")
        if users > 1:
            note += (f" This weapon setup is shared by {users} items, so "
                     "the change applies to the NPC and boss versions of "
                     "this gun as well.")
        ctk.CTkLabel(self.body, text="   " + note, anchor="w",
                     justify="left", wraplength=700,
                     font=self.app._iw_font_hint,
                     text_color="gray60").pack(fill="x", padx=12, pady=(2, 0))
        self.cal_warn = ctk.CTkLabel(
            self.body, text="", anchor="w", justify="left", wraplength=700,
            font=self.app._iw_font_hint, text_color="#E6B800")
        self.cal_warn.pack(fill="x", padx=12, pady=(0, 2))
        self._refresh_caliber_warning()

    def _caliber_changed(self, label: str):
        if self.app._iw_loading or self.cal_menu is None:
            return
        self.app._iw_auto_opened.discard(self.cat)   # siehe toggle()
        try:
            wanted = self._cal_values[self._cal_labels.index(label)]
        except ValueError:
            return
        if wanted:
            self.app.weapon_calibers[self.sid] = wanted
        else:
            self.app.weapon_calibers.pop(self.sid, None)
        self._refresh_caliber_warning()
        self.refresh()
        self.app._iw_after_change(self.cat)

    def _refresh_caliber_warning(self):
        if self.cal_warn is None:
            return
        chosen = self.app.weapon_calibers.get(self.sid)
        text = ""
        if chosen and self.app.gd is not None:
            text = caliber_warning(self.app.gd, self._cal_vanilla, chosen)
        self.cal_warn.configure(text=("   " + text) if text else "")

    def toggle(self):
        # Jede Interaktion in einer Kategorie macht sie zur Benutzer-Kategorie:
        # das Leeren des Suchfelds darf sie danach nicht mehr zuklappen.
        self.app._iw_auto_opened.discard(self.cat)
        if self.expanded:
            self.body.pack_forget()
            self.expanded = False
        else:
            self.build()
            # Tiefer eingerueckt als der Waffenknopf: die Knopfbeschriftung
            # sitzt selbst schon ~20 px innen, sonst stuenden die Regler-
            # Beschriftungen genau unter dem Waffennamen statt darunter-innen.
            self.body.pack(fill="x", padx=(36, 0), after=self.btn)
            self.expanded = True
        self.refresh()

    # ------------------------------------------------------------- Werte
    def load_values(self):
        """weapon_overrides -> Regler, ohne dass _changed zurueckschreibt."""
        if self.cal_menu is not None:
            chosen = self.app.weapon_calibers.get(self.sid, "")
            prev = self.app._iw_loading
            self.app._iw_loading = True
            try:
                index = (self._cal_values.index(chosen)
                         if chosen in self._cal_values else 0)
                self.cal_menu.set(self._cal_labels[index])
            finally:
                self.app._iw_loading = prev
            self._refresh_caliber_warning()
        if self.sliders:
            stored = self.app.weapon_overrides.get(self.sid, {})
            prev = self.app._iw_loading
            self.app._iw_loading = True
            try:
                for param, row in self.sliders.items():
                    row.set(stored.get(param, 1.0))
            finally:
                self.app._iw_loading = prev
        self.refresh()

    def _changed(self):
        """Reglerbewegung NUR dieser Waffe in weapon_overrides schreiben."""
        if self.app._iw_loading or not self.sliders:
            return
        self.app._iw_auto_opened.discard(self.cat)   # siehe toggle()
        values = {p: r.get() for p, r in self.sliders.items()}
        values = {p: v for p, v in values.items() if abs(v - 1.0) > 1e-9}
        if values:
            self.app.weapon_overrides[self.sid] = values
        else:
            self.app.weapon_overrides.pop(self.sid, None)
        self.refresh()
        self.app._iw_after_change(self.cat)

    def reset(self):
        self.app.weapon_overrides.pop(self.sid, None)
        self.app.weapon_calibers.pop(self.sid, None)
        self.load_values()
        self.app._iw_after_change(self.cat)

    # -------------------------------------------------------- Darstellung
    def refresh(self):
        n = len(self.app.weapon_overrides.get(self.sid, {}))
        arrow = "▾" if self.expanded else "▸"
        # "N of 10 factors" statt "N overrides": die Kategorie-Kopfzeile zaehlt
        # WAFFEN, diese Zeile zaehlt PARAMETER — gleiche Zahl, andere Einheit.
        # Nenner ist self.params: Waffen ohne Abnutzungswert & Co. haben
        # weniger Regler, sonst stuende dort eine unerreichbare Zahl.
        mark = f"     ●  {n} of {len(self.params)} factors changed" if n else ""
        cal = self.app.weapon_calibers.get(self.sid)
        if cal:
            # Das Kaliber zaehlt NICHT als Faktor mit (es ist keiner), steht
            # aber in der zugeklappten Zeile — sonst uebersieht man den
            # weitreichendsten Eingriff, den es an einer Waffe gibt.
            mark += (f"     ●  {caliber_label(cal)}" if mark
                     else f"     ●  {caliber_label(cal)}")
        self.btn.configure(text=f"{arrow}  {weapon_display(self.sid)}{mark}")
        self._apply_color(n or (1 if cal else 0))

    def _apply_color(self, n: int):
        """Vorrang: abgedunkelt > Suchtreffer > vorhandene Overrides."""
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str):
        self._highlight = mode
        self._apply_color(len(self.app.weapon_overrides.get(self.sid, {}))
                          or (1 if self.app.weapon_calibers.get(self.sid) else 0))

    def set_state(self, state: str):
        # Frueh raus, wenn sich nichts aendert: bei 79 offenen Waffen haengen
        # sonst 632 Regler an einem einzigen "Reload"-Klick.
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        if self.reset_btn is not None:
            self.reset_btn.configure(state=state)
        if self.cal_menu is not None:
            self.cal_menu.configure(state=state)
        for row in self.sliders.values():
            row.set_state(state)


class IwCategoryBlock:
    """Aufklappbarer Kategorie-Block im Overrides-Baum.

    Die Waffenzeilen entstehen beim ERSTEN Aufklappen (lazy) und bleiben
    dann bis zum naechsten Neuaufbau des Baums bestehen.
    """

    def __init__(self, app, parent, cat: str, label: str, sids: list[str]):
        self.app = app
        self.cat = cat
        self.label = label
        self.sids = sids                        # bereits sortiert
        self.rows: dict[str, IwWeaponRow] = {}  # leer bis zum ersten Oeffnen
        self.expanded = False
        self._highlight = "normal"
        self._note = ""                         # Zusatz in der Kopfzeile
        self._note_hint = False                 # zugeklappt: "click to show"
        self._state = app._iw_state             # zuletzt durchgereicht
        # Treffersatz der laufenden Suche; None = keine Suche aktiv. Wird
        # gebraucht, damit SPAETER gebaute Zeilen die Suchfarbe erben.
        self._hitset: set[str] | None = None
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_cat,
            command=self.toggle, state=app._iw_state)
        self.btn.pack(fill="x", padx=8, pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.content = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.refresh()

    def ensure_rows(self):
        """Lazy: die Waffenzeilen dieser Kategorie einmalig erzeugen."""
        if self.rows:
            return
        # Bis zu 25 Zeilen auf einmal dauern spuerbar — Sanduhr wie beim
        # Aufklappen einer einzelnen Waffe (IwWeaponRow.build).
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for sid in self.sids:
                row = IwWeaponRow(self.app, self.content, sid, self.cat)
                row.set_highlight(self._row_mode(sid))  # laufende Suche erben
                self.rows[sid] = row
        finally:
            try:
                self.app.configure(cursor="")
            except Exception:
                pass

    def _row_mode(self, sid: str) -> str:
        if self._hitset is None:
            return "normal"
        return "match" if sid in self._hitset else "dim"

    def set_row_filter(self, hitset: "set[str] | None"):
        """Treffersatz merken und alle SCHON gebauten Zeilen einfaerben."""
        self._hitset = hitset
        for sid, row in self.rows.items():
            row.set_highlight(self._row_mode(sid))

    def expand(self):
        if self.expanded:
            return
        self.ensure_rows()
        self.content.pack(fill="x", padx=(8, 0), after=self.btn)
        self.expanded = True
        self.refresh()

    def collapse(self):
        if not self.expanded:
            return
        self.content.pack_forget()
        self.expanded = False
        self.refresh()

    def toggle(self):
        # Benutzer-Klick hebt das Auto-Aufklappen der Suche auf
        self.app._iw_auto_opened.discard(self.cat)
        self.collapse() if self.expanded else self.expand()

    def refresh(self):
        # Eine gewaehlte Munition zaehlt hier mit: sonst steht ueber einer
        # Kategorie "0 of 12 overridden", obwohl darin eine Waffe auf ein
        # anderes Kaliber steht — der weitreichendste Eingriff von allen.
        n_over = sum(1 for sid in self.sids
                     if sid in self.app.weapon_overrides
                     or sid in self.app.weapon_calibers)
        arrow = "▾" if self.expanded else "▸"
        extra = (f"     ●  {n_over} of {len(self.sids)} overridden"
                 if n_over else "")
        extra += self._note
        # Nur an einem zugeklappten Block — hier und nicht beim Suchen
        # angehaengt, sonst bliebe der Hinweis nach einem Klick auf den
        # Kopf ueber den dann sichtbaren Waffen stehen.
        if self._note_hint and not self.expanded:
            extra += "     click to show"
        # Trenner statt Klammern: "Marksman rifles (DMR)" traegt selbst schon eine
        self.btn.configure(
            text=f"{arrow}  {self.label}  ·  {len(self.sids)}{extra}")
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n_over:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str, note: str = "", hint: bool = False):
        """note: fertig formatierter Zusatz der Suche (inkl. Abstand).

        hint: Block enthaelt Treffer -> zugeklappt "click to show" anzeigen.
        """
        self._highlight = mode
        self._note = note
        self._note_hint = hint
        self.refresh()

    def set_state(self, state: str):
        if state == self._state:      # siehe IwWeaponRow.set_state
            return
        self._state = state
        self.btn.configure(state=state)
        for row in self.rows.values():
            row.set_state(state)


class IaAmmoRow:
    """Aufklappbare Zeile EINER Munitionssorte im Ammo-Baum.

    Zwillingsklasse zu IwWeaponRow, bewusst KEINE Ableitung: der Waffenbaum
    ist frisch verifiziert und bleibt unangetastet. Der Preis sind ein paar
    doppelte Zeilen, der Gewinn ist, dass an den Waffen strukturell nichts
    kaputtgehen kann. Geteilt werden nur SliderRow, ACCENT, fmt_factor und
    die drei CTkFont-Objekte (nur lesend!).

    Die 4 Regler entstehen erst beim ERSTEN Aufklappen (lazy). Einzige
    Wahrheit bleibt app.ammo_overrides.
    """

    def __init__(self, app, parent, sid: str, cal: str, ammo_type: str,
                 show_type: bool):
        self.app = app
        self.sid = sid
        self.cal = cal
        self.ammo_type = ammo_type      # lesbar, z.B. "Armor-piercing"
        self.show_type = show_type      # False bei Ein-Sorten-Kalibern
        # Regler nur fuer Werte, die sich ueberhaupt skalieren lassen: bei 18
        # der 34 Sorten stehen ArmorPiercingMod UND CoverPiercingMod auf 0.0,
        # ein Faktor darauf bleibt 0.0. Solche Regler taeuschen eine Wirkung
        # vor, die es nicht gibt (und waren als einzige Aenderung sogar ein
        # Absturzgrund beim Bauen). Ohne bekannte Vanilla-Werte -- oder wenn
        # ALLES 0 waere -- bleibt es bei allen vier.
        mods = app._ia_mods.get(sid, {})
        usable = [p for p in AMMO_PARAMS
                  if abs(mods.get(AMMO_PARAM_KEYS[p], 0.0)) > 1e-9]
        self.params = usable if (mods and usable) else list(AMMO_PARAMS)
        self.body = None
        self.sliders: dict[str, SliderRow] = {}
        self.reset_btn = None
        self.expanded = False
        self._highlight = "normal"
        self._state = app._ia_state              # NICHT app._iw_state
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_row,
            command=self.toggle, state=app._ia_state)
        self.btn.pack(fill="x", padx=(16, 8), pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.refresh()

    # ------------------------------------------------------------ Aufbau
    def build(self):
        if self.body is not None:
            return
        self.body = ctk.CTkFrame(self.frame, fg_color="transparent")
        # Vanilla-Werte zeigen: bei vielen Sorten steht in ArmorPiercingMod
        # und CoverPiercingMod 0.0 -- ein Faktor darauf bleibt 0.0. Ohne
        # diesen Hinweis sieht das wie ein kaputter Regler aus.
        mods = self.app._ia_mods.get(self.sid, {})
        if mods:
            parts = [f"{AMMO_PARAM_LABELS[p].lower()} {mods[AMMO_PARAM_KEYS[p]]:g}"
                     for p in AMMO_PARAMS if AMMO_PARAM_KEYS[p] in mods]
            text = "   vanilla: " + ", ".join(parts)
            if len(self.params) < len(AMMO_PARAMS):
                text += ("\n   Values that are 0 in vanilla stay 0 – "
                         "no slider is offered for them.")
            # Expanding-Munition hat NEGATIVE Piercing-Werte (−0.7): ein
            # Faktor > 1 macht die Strafe groesser, nicht kleiner.
            if any(v < 0 for v in mods.values()):
                text += ("\n   A negative value is a penalty – a factor "
                         "above ×1 makes that penalty bigger.")
            ctk.CTkLabel(self.body, text=text, anchor="w", justify="left",
                         wraplength=700, font=self.app._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12,
                                                   pady=(2, 0))
        # Sperre waehrend des Aufbaus: SliderRow.__init__ ruft set(default)
        # und damit _changed auf -- ohne Sperre wuerde der halb gefuellte
        # Regler-Satz den gespeicherten Override loeschen. Alten Wert merken
        # und zuruecklegen (nicht hart True/False), damit ein verschachtelter
        # Aufruf aus _ia_refresh_all die Sperre nicht vorzeitig loest.
        prev = self.app._ia_loading
        self.app._ia_loading = True
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for param in self.params:
                self.sliders[param] = SliderRow(
                    self.body, AMMO_PARAM_LABELS[param], 0.25, 4, 0.25, 1,
                    fmt_factor, on_change=self._changed)
        finally:
            self.app._ia_loading = prev
            try:
                self.app.configure(cursor="")
            except Exception:
                pass
        self.reset_btn = ctk.CTkButton(
            self.body, text="↺  Reset this round", width=170,
            fg_color="transparent", border_width=1, command=self.reset)
        self.reset_btn.pack(anchor="w", padx=12, pady=(2, 4))
        ctk.CTkFrame(self.body, height=2, corner_radius=0,
                     fg_color="gray35").pack(fill="x", padx=12, pady=(4, 6))
        self.load_values()
        self._state = ""            # erzwingt Durchreichen an die NEUEN Regler
        self.set_state(self.app._ia_state)

    def toggle(self):
        self.app._ia_auto_opened.discard(self.cal)
        if self.expanded:
            self.body.pack_forget()
            self.expanded = False
        else:
            self.build()
            self.body.pack(fill="x", padx=(36, 0), after=self.btn)
            self.expanded = True
        self.refresh()

    # ------------------------------------------------------------- Werte
    def load_values(self):
        if self.sliders:
            stored = self.app.ammo_overrides.get(self.sid, {})
            prev = self.app._ia_loading
            self.app._ia_loading = True
            try:
                for param, row in self.sliders.items():
                    row.set(stored.get(param, 1.0))
            finally:
                self.app._ia_loading = prev
        self.refresh()

    def _changed(self):
        if self.app._ia_loading or not self.sliders:
            return
        self.app._ia_auto_opened.discard(self.cal)
        values = {p: r.get() for p, r in self.sliders.items()}
        values = {p: v for p, v in values.items() if abs(v - 1.0) > 1e-9}
        if values:
            self.app.ammo_overrides[self.sid] = values
        else:
            self.app.ammo_overrides.pop(self.sid, None)
        self.refresh()
        self.app._ia_after_change(self.cal)

    def reset(self):
        self.app.ammo_overrides.pop(self.sid, None)
        self.load_values()
        self.app._ia_after_change(self.cal)

    # -------------------------------------------------------- Darstellung
    def refresh(self):
        n = len(self.app.ammo_overrides.get(self.sid, {}))
        arrow = "▾" if self.expanded else "▸"
        # Die Sorte steht im TITEL: A545A/A545D/A545E sind sonst nicht zu
        # unterscheiden. Bei Kalibern mit nur EINER Sorte weggelassen.
        kind = f"  ·  {self.ammo_type}" if self.show_type else ""
        # len(self.params), NICHT len(self.sliders): die Regler entstehen erst
        # beim Aufklappen, die Zahl muss aber schon vorher stimmen.
        mark = (f"     ●  {n} of {len(self.params)} factors changed"
                if n else "")
        self.btn.configure(text=f"{arrow}  {self.sid}{kind}{mark}")
        self._apply_color(n)

    def _apply_color(self, n: int):
        """Vorrang: abgedunkelt > Suchtreffer > vorhandene Overrides."""
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str):
        self._highlight = mode
        self._apply_color(len(self.app.ammo_overrides.get(self.sid, {})))

    def set_state(self, state: str):
        # Frueh raus: sonst haengen bei allen offenen Sorten 136 Regler an
        # einem einzigen "Reload"-Klick.
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        if self.reset_btn is not None:
            self.reset_btn.configure(state=state)
        for row in self.sliders.values():
            row.set_state(state)


class IaCaliberBlock:
    """Aufklappbarer Kaliber-Block im Ammo-Baum (1-4 Sorten).

    Zwillingsklasse zu IwCategoryBlock -- siehe Begruendung bei IaAmmoRow.
    """

    def __init__(self, app, parent, cal: str, label: str, sids: list[str]):
        self.app = app
        self.cal = cal
        self.label = label
        self.sids = sids                       # bereits nach Sorte sortiert
        self.rows: dict[str, IaAmmoRow] = {}
        self.expanded = False
        self._highlight = "normal"
        self._note = ""
        self._note_hint = False
        self._state = app._ia_state
        self._hitset: set[str] | None = None
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_cat,
            command=self.toggle, state=app._ia_state)
        self.btn.pack(fill="x", padx=8, pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.content = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.refresh()

    def ensure_rows(self):
        """Lazy. Ohne Sanduhr: hoechstens 4 Knoepfe (gemessen ~15 ms),
        anders als die Waffen-Variante mit bis zu 25 Zeilen."""
        if self.rows:
            return
        for sid in self.sids:
            ammo_type = self.app._ia_types.get(sid, "")
            row = IaAmmoRow(self.app, self.content, sid, self.cal, ammo_type,
                            len(self.sids) > 1 and bool(ammo_type))
            row.set_highlight(self._row_mode(sid))   # laufende Suche erben
            self.rows[sid] = row

    def _row_mode(self, sid: str) -> str:
        if self._hitset is None:
            return "normal"
        return "match" if sid in self._hitset else "dim"

    def set_row_filter(self, hitset: "set[str] | None"):
        self._hitset = hitset
        for sid, row in self.rows.items():
            row.set_highlight(self._row_mode(sid))

    def expand(self):
        if self.expanded:
            return
        self.ensure_rows()
        self.content.pack(fill="x", padx=(8, 0), after=self.btn)
        self.expanded = True
        self.refresh()

    def collapse(self):
        if not self.expanded:
            return
        self.content.pack_forget()
        self.expanded = False
        self.refresh()

    def toggle(self):
        self.app._ia_auto_opened.discard(self.cal)
        self.collapse() if self.expanded else self.expand()

    def refresh(self):
        n_over = sum(1 for sid in self.sids if sid in self.app.ammo_overrides)
        arrow = "▾" if self.expanded else "▸"
        extra = (f"     ●  {n_over} of {len(self.sids)} overridden"
                 if n_over else "")
        extra += self._note
        # NUR am zugeklappten Block -- hier und nicht beim Suchen angehaengt,
        # sonst bliebe der Hinweis nach einem Klick auf den Kopf stehen.
        if self._note_hint and not self.expanded:
            extra += "     click to show"
        self.btn.configure(
            text=f"{arrow}  {self.label}  ·  {len(self.sids)}{extra}")
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n_over:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str, note: str = "", hint: bool = False):
        self._highlight = mode
        self._note = note
        self._note_hint = hint
        self.refresh()

    def set_state(self, state: str):
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        for row in self.rows.values():
            row.set_state(state)


class IrArmorRow:
    """Aufklappbare Zeile EINER Ruestung im Armor-Baum.

    Dritte Zwillingsklasse neben IwWeaponRow und IaAmmoRow, bewusst KEINE
    Ableitung — dieselbe Begruendung wie dort: die verifizierten Baeume
    bleiben strukturell unangetastet. Wahrheit ist app.armor_overrides.
    Regler nur fuer Schutzarten, die in Vanilla > 0 sind (0 x Faktor = 0)."""

    def __init__(self, app, parent, sid: str, group: str):
        self.app = app
        self.sid = sid
        self.group = group
        self.label = app._ir_labels.get(sid, sid)
        self.params = [p for p in ARMOR_PARAMS
                       if p in app._ir_prot.get(sid, {})]
        self.body = None
        self.sliders: dict[str, SliderRow] = {}
        self.reset_btn = None
        self.expanded = False
        self._highlight = "normal"
        self._state = app._ir_state
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_row,
            command=self.toggle, state=app._ir_state)
        self.btn.pack(fill="x", padx=(16, 8), pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.refresh()

    # ------------------------------------------------------------ Aufbau
    def build(self):
        if self.body is not None:
            return
        self.body = ctk.CTkFrame(self.frame, fg_color="transparent")
        prot = self.app._ir_prot.get(self.sid, {})
        if prot:
            parts = [f"{ARMOR_PARAM_LABELS[p].lower()} {prot[p]:g}"
                     for p in ARMOR_PARAMS if p in prot]
            text = "   vanilla protection: " + ", ".join(parts)
            if len(self.params) < len(ARMOR_PARAMS):
                text += ("\n   Protection types that are 0 in vanilla stay 0 "
                         "\u2013 no slider is offered for them.")
            ctk.CTkLabel(self.body, text=text, anchor="w", justify="left",
                         wraplength=700, font=self.app._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12,
                                                   pady=(2, 0))
        edition = self.app._ir_dlc.get(self.sid)
        if edition:
            name = {"PreOrder": "Pre-order"}.get(edition, edition)
            ctk.CTkLabel(
                self.body,
                text=f"   {name}-edition armor – overrides on it patch "
                     "the DLC config branch (untested in-game; harmless "
                     "if you don't own that edition).",
                anchor="w", justify="left", wraplength=700,
                font=self.app._iw_font_hint, text_color="gray60",
            ).pack(fill="x", padx=12, pady=(2, 0))
        # Sperre waehrend des Aufbaus: SliderRow.__init__ ruft set(default)
        # und damit _changed — ohne Sperre loescht der halb gebaute Satz den
        # gespeicherten Override (die Lehre aus dem Waffenbaum-Review).
        prev = self.app._ir_loading
        self.app._ir_loading = True
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for param in self.params:
                self.sliders[param] = SliderRow(
                    self.body, ARMOR_PARAM_LABELS[param], 0.25, 4, 0.25, 1,
                    fmt_factor, on_change=self._changed)
        finally:
            self.app._ir_loading = prev
            try:
                self.app.configure(cursor="")
            except Exception:
                pass
        self.reset_btn = ctk.CTkButton(
            self.body, text="\u21ba  Reset this armor", width=170,
            fg_color="transparent", border_width=1, command=self.reset)
        self.reset_btn.pack(anchor="w", padx=12, pady=(2, 4))
        ctk.CTkFrame(self.body, height=2, corner_radius=0,
                     fg_color="gray35").pack(fill="x", padx=12, pady=(4, 6))
        self.load_values()
        self._state = ""            # erzwingt Durchreichen an die NEUEN Regler
        self.set_state(self.app._ir_state)

    def toggle(self):
        self.app._ir_auto_opened.discard(self.group)
        if self.expanded:
            self.body.pack_forget()
            self.expanded = False
        else:
            self.build()
            self.body.pack(fill="x", padx=(36, 0), after=self.btn)
            self.expanded = True
        self.refresh()

    # ------------------------------------------------------------- Werte
    def load_values(self):
        if self.sliders:
            stored = self.app.armor_overrides.get(self.sid, {})
            prev = self.app._ir_loading
            self.app._ir_loading = True
            try:
                for param, row in self.sliders.items():
                    row.set(stored.get(param, 1.0))
            finally:
                self.app._ir_loading = prev
        self.refresh()

    def _changed(self):
        if self.app._ir_loading or not self.sliders:
            return
        self.app._ir_auto_opened.discard(self.group)
        values = {p: r.get() for p, r in self.sliders.items()}
        values = {p: v for p, v in values.items() if abs(v - 1.0) > 1e-9}
        if values:
            self.app.armor_overrides[self.sid] = values
        else:
            self.app.armor_overrides.pop(self.sid, None)
        self.refresh()
        self.app._ir_after_change(self.group)

    def reset(self):
        self.app.armor_overrides.pop(self.sid, None)
        self.load_values()
        self.app._ir_after_change(self.group)

    # -------------------------------------------------------- Darstellung
    def refresh(self):
        n = len(self.app.armor_overrides.get(self.sid, {}))
        arrow = "\u25be" if self.expanded else "\u25b8"
        mark = (f"     \u25cf  {n} of {len(self.params)} factors changed"
                if n else "")
        self.btn.configure(text=f"{arrow}  {self.label}{mark}")
        self._apply_color(n)

    def _apply_color(self, n: int):
        """Vorrang: abgedunkelt > Suchtreffer > vorhandene Overrides."""
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str):
        self._highlight = mode
        self._apply_color(len(self.app.armor_overrides.get(self.sid, {})))

    def set_state(self, state: str):
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        if self.reset_btn is not None:
            self.reset_btn.configure(state=state)
        for row in self.sliders.values():
            row.set_state(state)


class IrGroupBlock:
    """Aufklappbarer Gruppen-Block im Armor-Baum (Body armor / Helmets)."""

    def __init__(self, app, parent, group: str, label: str, sids: list[str]):
        self.app = app
        self.group = group
        self.label = label
        self.sids = sids                       # bereits nach Label sortiert
        self.rows: dict[str, IrArmorRow] = {}
        self.expanded = False
        self._highlight = "normal"
        self._note = ""
        self._note_hint = False
        self._state = app._ir_state
        self._hitset: set[str] | None = None
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_cat,
            command=self.toggle, state=app._ir_state)
        self.btn.pack(fill="x", padx=8, pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.content = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.refresh()

    def ensure_rows(self):
        """Lazy wie beim Waffenbaum: bis zu 42 Zeilen — mit Sanduhr."""
        if self.rows:
            return
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for sid in self.sids:
                row = IrArmorRow(self.app, self.content, sid, self.group)
                row.set_highlight(self._row_mode(sid))
                self.rows[sid] = row
        finally:
            try:
                self.app.configure(cursor="")
            except Exception:
                pass

    def _row_mode(self, sid: str) -> str:
        if self._hitset is None:
            return "normal"
        return "match" if sid in self._hitset else "dim"

    def set_row_filter(self, hitset: "set[str] | None"):
        self._hitset = hitset
        for sid, row in self.rows.items():
            row.set_highlight(self._row_mode(sid))

    def expand(self):
        if self.expanded:
            return
        self.ensure_rows()
        self.content.pack(fill="x", padx=(8, 0), after=self.btn)
        self.expanded = True
        self.refresh()

    def collapse(self):
        if not self.expanded:
            return
        self.content.pack_forget()
        self.expanded = False
        self.refresh()

    def toggle(self):
        self.app._ir_auto_opened.discard(self.group)
        self.collapse() if self.expanded else self.expand()

    def refresh(self):
        n_over = sum(1 for sid in self.sids if sid in self.app.armor_overrides)
        arrow = "\u25be" if self.expanded else "\u25b8"
        extra = (f"     \u25cf  {n_over} of {len(self.sids)} overridden"
                 if n_over else "")
        extra += self._note
        if self._note_hint and not self.expanded:
            extra += "     click to show"
        self.btn.configure(
            text=f"{arrow}  {self.label}  \u00b7  {len(self.sids)}{extra}")
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n_over:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str, note: str = "", hint: bool = False):
        self._highlight = mode
        self._note = note
        self._note_hint = hint
        self.refresh()

    def set_state(self, state: str):
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        for row in self.rows.values():
            row.set_state(state)


class IfFactionBlock:
    """Aufklappbarer Block im Fraktions-Baum (Tab "Factions").

    Vierter Verwandter der Baum-Bloecke (Waffen/Ammo/Ruestung), bewusst
    KEINE Ableitung — dieselbe Begruendung wie dort. Anders als bei den
    Zwillingen ist eine Zeile hier direkt eine SliderRow (ein
    Beziehungspaar = ein Regler, -800..800). Wahrheit ist
    app.faction_relations; `sids` sind Paar-Schluessel wie
    "Bandits<->Player" (Attributname wie bei den anderen Baeumen, damit
    Suche und Changed-only denselben Code benutzen koennen)."""

    def __init__(self, app, parent, group: str, label: str, sids: list[str]):
        self.app = app
        self.group = group
        self.label = label
        self.sids = sids
        self.rows: dict[str, SliderRow] = {}
        self.expanded = False
        self._highlight = "normal"
        self._note = ""
        self._note_hint = False
        self._state = app._if_state
        self._hitset: set[str] | None = None
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_cat,
            command=self.toggle, state=app._if_state)
        self.btn.pack(fill="x", padx=8, pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.content = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.refresh()

    def ensure_rows(self):
        """Lazy wie bei den anderen Baeumen. Sperre waehrend des Aufbaus:
        SliderRow.__init__ ruft set(default) -> on_change — ohne Sperre
        wuerde der halb gebaute Satz gespeicherte Werte loeschen (die
        Lehre aus dem Waffenbaum-Review)."""
        if self.rows:
            return
        prev = self.app._if_loading
        self.app._if_loading = True
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for key in self.sids:
                row = SliderRow(
                    self.content, self.app._if_labels.get(key, key),
                    -800, 800, 1, self.app._if_vanilla.get(key, 0),
                    fmt_relation,
                    on_change=lambda k=key: self.app._if_row_changed(k))
                row.set_highlight(self._row_mode(key))
                self.rows[key] = row
                self.app._if_rows[key] = row
        finally:
            self.app._if_loading = prev
            try:
                self.app.configure(cursor="")
            except Exception:
                pass
        self.load_values()
        self._state = ""            # erzwingt Durchreichen an die NEUEN Regler
        self.set_state(self.app._if_state)

    def load_values(self):
        """Gebaute Regler an app.faction_relations angleichen."""
        if not self.rows:
            return
        prev = self.app._if_loading
        self.app._if_loading = True
        try:
            for key, row in self.rows.items():
                row.set(self.app.faction_relations.get(
                    key, self.app._if_vanilla.get(key, 0)))
        finally:
            self.app._if_loading = prev

    def _row_mode(self, key: str) -> str:
        if self._hitset is None:
            return "normal"
        return "match" if key in self._hitset else "dim"

    def set_row_filter(self, hitset: "set[str] | None"):
        self._hitset = hitset
        for key, row in self.rows.items():
            row.set_highlight(self._row_mode(key))

    def expand(self):
        if self.expanded:
            return
        self.ensure_rows()
        self.content.pack(fill="x", padx=(8, 0), after=self.btn)
        self.expanded = True
        self.refresh()

    def collapse(self):
        if not self.expanded:
            return
        self.content.pack_forget()
        self.expanded = False
        self.refresh()

    def toggle(self):
        self.app._if_auto_opened.discard(self.group)
        self.collapse() if self.expanded else self.expand()

    def refresh(self):
        n = sum(1 for key in self.sids if key in self.app.faction_relations)
        arrow = "▾" if self.expanded else "▸"
        extra = (f"     ●  {n} of {len(self.sids)} changed" if n else "")
        extra += self._note
        if self._note_hint and not self.expanded:
            extra += "     click to show"
        self.btn.configure(
            text=f"{arrow}  {self.label}  ·  {len(self.sids)}{extra}")
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str, note: str = "", hint: bool = False):
        self._highlight = mode
        self._note = note
        self._note_hint = hint
        self.refresh()

    def set_state(self, state: str):
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        for row in self.rows.values():
            row.set_state(state)


class ImSpeciesRow:
    """Aufklappbare Zeile EINER Mutanten-Art im Mutants-Baum.

    Fuenfter Verwandter (Waffen/Ammo/Ruestung/Fraktionen), bewusst KEINE
    Ableitung. Wahrheit ist app.mutant_overrides — dasselbe Dict wie zu
    Dropdown-Zeiten, darum laufen alte Presets unveraendert. Regler nur
    fuer Parameter, die die Art wirklich hat (app._im_params): kein
    Damage-Regler fuer Poltergeist/Rat (indirekter Schaden), kein
    Regen-Regler ohne Vanilla-Regeneration."""

    def __init__(self, app, parent, species: str, group: str):
        self.app = app
        self.species = species
        self.group = group
        self.label = mutant_species_label(species)
        self.params = list(app._im_params.get(species, []))
        self.body = None
        self.sliders: dict[str, SliderRow] = {}
        self.reset_btn = None
        self.expanded = False
        self._highlight = "normal"
        self._state = app._im_state
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_row,
            command=self.toggle, state=app._im_state)
        self.btn.pack(fill="x", padx=(16, 8), pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.refresh()

    # ------------------------------------------------------------ Aufbau
    def build(self):
        if self.body is not None:
            return
        self.body = ctk.CTkFrame(self.frame, fg_color="transparent")
        hint = self.app._im_hints.get(self.species)
        if hint:
            ctk.CTkLabel(self.body, text="   " + hint, anchor="w",
                         justify="left", wraplength=700,
                         font=self.app._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12,
                                                   pady=(2, 0))
        # Sperre waehrend des Aufbaus: SliderRow.__init__ ruft set(default)
        # -> on_change (die Waffenbaum-Lehre, wie bei allen Baeumen).
        prev = self.app._im_loading
        self.app._im_loading = True
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for param in self.params:
                lo, hi = (0.0, 4.0) if param == "regen" else (0.25, 5.0)
                self.sliders[param] = SliderRow(
                    self.body, MUT_PARAM_LABELS[param], lo, hi, 0.25, 1,
                    fmt_factor, on_change=self._changed)
        finally:
            self.app._im_loading = prev
            try:
                self.app.configure(cursor="")
            except Exception:
                pass
        self.reset_btn = ctk.CTkButton(
            self.body, text="↺  Reset this species", width=170,
            fg_color="transparent", border_width=1, command=self.reset)
        self.reset_btn.pack(anchor="w", padx=12, pady=(2, 4))
        ctk.CTkFrame(self.body, height=2, corner_radius=0,
                     fg_color="gray35").pack(fill="x", padx=12, pady=(4, 6))
        self.load_values()
        self._state = ""            # erzwingt Durchreichen an die NEUEN Regler
        self.set_state(self.app._im_state)

    def toggle(self):
        self.app._im_auto_opened.discard(self.group)
        if self.expanded:
            self.body.pack_forget()
            self.expanded = False
        else:
            self.build()
            self.body.pack(fill="x", padx=(36, 0), after=self.btn)
            self.expanded = True
        self.refresh()

    # ------------------------------------------------------------- Werte
    def load_values(self):
        if self.sliders:
            stored = self.app.mutant_overrides.get(self.species, {})
            prev = self.app._im_loading
            self.app._im_loading = True
            try:
                for param, row in self.sliders.items():
                    row.set(stored.get(param, 1.0))
            finally:
                self.app._im_loading = prev
        self.refresh()

    def _changed(self):
        if self.app._im_loading or not self.sliders:
            return
        self.app._im_auto_opened.discard(self.group)
        values = {p: r.get() for p, r in self.sliders.items()}
        values = {p: v for p, v in values.items() if abs(v - 1.0) > 1e-9}
        if values:
            self.app.mutant_overrides[self.species] = values
        else:
            self.app.mutant_overrides.pop(self.species, None)
        self.refresh()
        self.app._im_after_change(self.group)

    def reset(self):
        self.app.mutant_overrides.pop(self.species, None)
        self.load_values()
        self.app._im_after_change(self.group)

    # -------------------------------------------------------- Darstellung
    def refresh(self):
        n = len(self.app.mutant_overrides.get(self.species, {}))
        arrow = "▾" if self.expanded else "▸"
        mark = (f"     ●  {n} of {len(self.params)} factors changed"
                if n else "")
        self.btn.configure(text=f"{arrow}  {self.label}{mark}")
        self._apply_color(n)

    def _apply_color(self, n: int):
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str):
        self._highlight = mode
        self._apply_color(len(self.app.mutant_overrides.get(self.species, {})))

    def set_state(self, state: str):
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        if self.reset_btn is not None:
            self.reset_btn.configure(state=state)
        for row in self.sliders.values():
            row.set_state(state)


class ImGroupBlock:
    """Aufklappbarer Groessen-Block im Mutanten-Baum."""

    def __init__(self, app, parent, group: str, label: str, sids: list[str]):
        self.app = app
        self.group = group
        self.label = label
        self.sids = sids                       # Arten, bereits sortiert
        self.rows: dict[str, ImSpeciesRow] = {}
        self.expanded = False
        self._highlight = "normal"
        self._note = ""
        self._note_hint = False
        self._state = app._im_state
        self._hitset: set[str] | None = None
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x")
        self.btn = ctk.CTkButton(
            self.frame, text="", anchor="w", fg_color="transparent",
            hover_color="gray25", font=app._iw_font_cat,
            command=self.toggle, state=app._im_state)
        self.btn.pack(fill="x", padx=8, pady=1)
        self._orig_color = self.btn.cget("text_color")
        self.content = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.refresh()

    def ensure_rows(self):
        if self.rows:
            return
        try:
            self.app.configure(cursor="watch")
            self.app.update_idletasks()
        except Exception:
            pass
        try:
            for species in self.sids:
                row = ImSpeciesRow(self.app, self.content, species, self.group)
                row.set_highlight(self._row_mode(species))
                self.rows[species] = row
        finally:
            try:
                self.app.configure(cursor="")
            except Exception:
                pass

    def _row_mode(self, species: str) -> str:
        if self._hitset is None:
            return "normal"
        return "match" if species in self._hitset else "dim"

    def set_row_filter(self, hitset: "set[str] | None"):
        self._hitset = hitset
        for species, row in self.rows.items():
            row.set_highlight(self._row_mode(species))

    def expand(self):
        if self.expanded:
            return
        self.ensure_rows()
        self.content.pack(fill="x", padx=(8, 0), after=self.btn)
        self.expanded = True
        self.refresh()

    def collapse(self):
        if not self.expanded:
            return
        self.content.pack_forget()
        self.expanded = False
        self.refresh()

    def toggle(self):
        self.app._im_auto_opened.discard(self.group)
        self.collapse() if self.expanded else self.expand()

    def refresh(self):
        n_over = sum(1 for s in self.sids if s in self.app.mutant_overrides)
        arrow = "▾" if self.expanded else "▸"
        extra = (f"     ●  {n_over} of {len(self.sids)} overridden"
                 if n_over else "")
        extra += self._note
        if self._note_hint and not self.expanded:
            extra += "     click to show"
        self.btn.configure(
            text=f"{arrow}  {self.label}  ·  {len(self.sids)}{extra}")
        if self._highlight == "dim":
            color = "gray35"
        elif self._highlight == "match" or n_over:
            color = ACCENT
        else:
            color = self._orig_color
        self.btn.configure(text_color=color)

    def set_highlight(self, mode: str, note: str = "", hint: bool = False):
        self._highlight = mode
        self._note = note
        self._note_hint = hint
        self.refresh()

    def set_state(self, state: str):
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        for row in self.rows.values():
            row.set_state(state)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        # Hoehe passt dank Tabs auch auf kleinere/skalierte Bildschirme
        self.geometry("1010x720")
        self.minsize(880, 600)
        self._set_icon()
        self.after(300, self._set_icon)  # CustomTkinter setzt sonst sein eigenes

        self.gd: GameData | None = None
        self.game_dir: Path | None = None
        self.sliders: dict[str, SliderRow] = {}
        self.slider_tabs: dict[str, str] = {}
        self._current_tab = ""
        self.checks: dict[str, ctk.CTkCheckBox] = {}
        self.cat_checks: dict[str, ctk.CTkCheckBox] = {}
        # Einzelwaffen-Overrides: {WGS-SID: {param: faktor}} (nur != 1.0)
        self.weapon_overrides: dict[str, dict[str, float]] = {}
        # Mutanten-Overrides pro Art: {Art: {hp/speed/damage/regen: faktor}}
        # Fuenfter Baum (Tab "Mutants"), fuenfter eigener Namensraum (_im_*).
        # Das Dict hiess schon in der Dropdown-Aera so — settings.json,
        # Presets und Pak-Manifeste laufen unveraendert weiter.
        self.mutant_overrides: dict[str, dict[str, float]] = {}
        self._im_loading = False
        self._im_species: list[str] = []
        self._im_params: dict[str, list[str]] = {}   # Art -> erlaubte Regler
        self._im_hints: dict[str, str] = {}          # Art -> Vanilla-Infozeile
        self._im_blocks: dict[str, "ImGroupBlock"] = {}
        self._im_auto_opened: set[str] = set()
        self._im_expand_job: str | None = None
        self._im_state = "disabled"
        self._iw_loading = False
        self._iw_categories: dict[str, str] = {}
        self._iw_share: dict[str, list[str]] = {}  # Waffen mit geteiltem CWS-Struct
        self._iw_params: dict[str, list[str]] = {}  # WGS-SID -> vorhandene Parameter
        self._iw_dlc: dict[str, str] = {}          # WGS-SID -> DLC-Edition
        self._iw_caliber: dict[str, str | None] = {}   # WGS-SID -> Vanilla-Kaliber
        self._iw_caliber_options: list[str] = []       # Auswahl im Dropdown
        self._iw_setup_users: dict[str, int] = {}      # Items je Setup (NPC-Zwillinge)
        # Kaliberwechsel je Waffe: {WGS-SID: "A556"} — nur Abweichungen von
        # Vanilla. Bewusst NEBEN weapon_overrides: dort stehen Faktoren.
        self.weapon_calibers: dict[str, str] = {}
        self._iw_blocks: dict[str, IwCategoryBlock] = {}
        self._iw_auto_opened: set[str] = set()     # von der Suche aufgeklappt
        # Kategorie-Knoepfe im Abschnitt "Weapon categories": {cat: (btn, label, farbe)}
        self._wcat_btns: dict[str, tuple] = {}
        self._wcat_notes: dict[str, str] = {}   # Suchzusatz je Kategorie-Kopf
        self._iw_expand_job: str | None = None  # laufender after()-Auftrag
        # Einzelmunitions-Overrides: {Ammo-SID: {param: faktor}} (nur != 1.0)
        self.ammo_overrides: dict[str, dict[str, float]] = {}
        # Einzelruestungs-Overrides: {Item-SID: {param: faktor}} (nur != 1.0)
        # Dritter Baum, dritter strikt eigener Namensraum (_ir_*).
        self.armor_overrides: dict[str, dict[str, float]] = {}
        self._ir_loading = False
        self._ir_groups: dict[str, str] = {}              # SID -> Body/Head
        self._ir_prot: dict[str, dict[str, float]] = {}   # SID -> Vanilla
        self._ir_labels: dict[str, str] = {}              # SID -> Anzeige
        self._ir_dlc: dict[str, str] = {}                 # SID -> DLC-Edition
        self._ir_blocks: dict[str, IrGroupBlock] = {}
        self._ir_auto_opened: set[str] = set()
        self._ir_expand_job: str | None = None
        self._ir_state = "disabled"
        # Fraktionsbeziehungen: {Paar-Schluessel: Zielwert int, nur != Vanilla}
        # Vierter Baum, vierter strikt eigener Namensraum (_if_*).
        self.faction_relations: dict[str, int] = {}
        self._if_loading = False
        self._if_vanilla: dict[str, int] = {}    # Paar -> Vanilla-Wert
        self._if_labels: dict[str, str] = {}     # Paar -> "Duty ↔ Freedom"
        self._if_rows: dict[str, SliderRow] = {} # nur GEBAUTE Zeilen
        self._if_blocks: dict[str, "IfFactionBlock"] = {}
        self._if_groups: list[tuple[str, str, list[str]]] = []
        self._if_player_keys: list[str] = []
        self._if_auto_opened: set[str] = set()
        self._if_expand_job: str | None = None
        self._if_state = "disabled"
        # Strikt eigener Namensraum. NICHTS davon mit den _iw_*-Feldern
        # teilen: eine gemeinsame Sperre/ein gemeinsamer after()-Auftrag
        # wuerde Overrides der jeweils anderen Seite verschlucken.
        self._ia_loading = False
        self._ia_calibers: dict[str, str] = {}            # SID -> Kaliber
        self._ia_types: dict[str, str] = {}               # SID -> lesbare Sorte
        self._ia_mods: dict[str, dict[str, float]] = {}   # SID -> Vanilla-Werte
        self._ia_blocks: dict[str, IaCaliberBlock] = {}
        self._ia_auto_opened: set[str] = set()
        self._ia_expand_job: str | None = None
        self._ia_state = "disabled"
        # Statuszeile vor dem ersten Tastendruck im Suchfeld
        self._status_before_search: str | None = None
        self._iw_state = "disabled"                # gilt fuer lazy Widgets
        # Schriften EINMAL bauen und an alle Baum-Zeilen weiterreichen —
        # CTkFont-Objekte sind teuer, 79 Waffen x eigene Font waere Verschwendung
        self._iw_font_cat = ctk.CTkFont(size=13)
        self._iw_font_row = ctk.CTkFont(size=12)
        self._iw_font_hint = ctk.CTkFont(size=11)
        self._msgs: "queue.Queue[tuple[str, str]]" = queue.Queue()
        # Mod-Scan (Vorab-Scan fremder Paks in ~mods)
        self.modscan_pref = "ask"               # "ask" | "never"
        self.mod_conflicts: dict[str, list[str]] = {}
        self.modscan_results: list[modscan.ModInfo] = []
        self._footprints: dict[str, set | None] = {}
        self._modscan_offered = False
        self._modscan_payload = None
        self._scan_running = False
        self._mods_after: set[str] = set()   # Paks, die NACH unserer laden
        self._mods_unknown: set[str] = set()  # Workshop: Reihenfolge unklar
        # Avoid-conflicts-Modus: betroffene Regler auf Vanilla + gesperrt.
        self.avoid_conflicts = False
        self.avoid_unlocked: set[str] = set()   # bewusst freigeschaltet
        self._avoid_saved: dict[str, float | bool] = {}  # Werte vor der Sperre
        self._locked_checks: set[str] = set()
        self.check_dots: dict[str, ctk.CTkLabel] = {}
        self._check_tips: dict[str, str] = {}
        # "Changed only": dimmt alles, was auf Vanilla steht
        self.changed_only = False
        self._oc_job: str | None = None

        self._build_header()
        self._build_body()
        self._build_footer()

        self._load_ui_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_body_state(False)
        try:
            output_dir().mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.after(100, self._poll_msgs)
        self.after(150, self._prefill_game)
        self.after(600, self._check_oodle_present)

    def _check_oodle_present(self):
        """Beim Start pruefen, ob die Oodle-Bibliothek da ist.

        Das Werkzeug laedt sie bewusst NICHT herunter (siehe pakio-Kopf:
        ein Programm, das zur Laufzeit Bibliotheken nachlaedt, sieht fuer
        Virenscanner wie ein Dropper aus). Fehlt sie, fuehrt ein
        dreiseitiger Assistent durch das einmalige Danebenlegen — statt
        den Nutzer erst beim Laden der Spieldaten auflaufen zu lassen."""
        try:
            self._refresh_oodle_badge()
            if pakio.oodle_available():
                return
            self._open_oodle_wizard()
            self._set_status("Oodle library missing – follow the setup "
                             "window; building a pak does not need it.")
        except Exception:
            pass        # eine fehlende Vorabwarnung darf den Start nie kippen

    def _oodle_target_dir(self) -> Path:
        """Der Ordner, den der Nutzer sehen soll: der mit S2Tweaker.exe.

        NICHT der Ordner von repak.exe — der liegt im Ordner-Build in
        `_internal`, und genau das widerspraeche dem Bild und dem Text
        ("neben S2Tweaker.exe, nicht in _internal"). Dort abgelegt wird
        die Datei gefunden; weiterverteilt wird sie vom Programm selbst
        (ensure_oodle legt eine Kopie neben repak und in tools/)."""
        return app_dir()

    def _close_oodle_wizard(self):
        win = getattr(self, "_oodle_win", None)
        if win is not None and win.winfo_exists():
            win.destroy()
        self._refresh_oodle_badge()

    def _refresh_oodle_badge(self):
        """Ampel neben dem FAQ-Knopf: gruen = da, rot = fehlt.

        Wird beim Start und nach jedem Laden der Spieldaten aufgefrischt —
        legt der Nutzer die Datei waehrend der Sitzung dazu, springt sie um,
        sobald er auf 'Confirm & load game data' drueckt."""
        btn = getattr(self, "btn_oodle", None)
        if btn is None:
            return
        try:
            ok = pakio.oodle_available()
        except Exception:
            ok = False
        if ok:
            btn.configure(text="● Oodle ready", fg_color="#2E7D32",
                          hover_color="#256428")
        else:
            btn.configure(text="● Oodle missing", fg_color="#B3261E",
                          hover_color="#8C1D18")

    def _open_oodle_wizard(self, page: int = 0):
        """Dreiseitiger Assistent: Link kopieren, herunterladen, ablegen.

        Bewusst Schritt fuer Schritt mit Bildern: der Nutzer muss eine
        fremde DLL von Hand besorgen — das ist erklaerungsbeduerftig, und
        eine Textwand liest niemand. Die Bilder liegen als PNG bei (Tk
        kann PNG von Haus aus; Pillow ist im Build absichtlich draussen)."""
        existing = getattr(self, "_oodle_win", None)
        if existing is not None and existing.winfo_exists():
            existing.deiconify(); existing.lift(); existing.focus_set()
            return
        win = ctk.CTkToplevel(self)
        self._oodle_win = win
        win.title("S2Tweaker – one file is missing")
        win.geometry("880x680")
        win.minsize(820, 600)
        win.transient(self)

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(14, 6))
        nav = ctk.CTkFrame(win, fg_color="transparent")
        nav.pack(fill="x", padx=18, pady=(0, 12))

        state = {"page": 0, "images": []}
        back_btn = ctk.CTkButton(nav, text="←  Back", width=130, height=38,
                                 font=ctk.CTkFont(size=14))
        step_lbl = ctk.CTkLabel(nav, text="", text_color="gray60",
                                font=ctk.CTkFont(size=14))
        next_btn = ctk.CTkButton(nav, text="Next  →", width=150, height=38,
                                 font=ctk.CTkFont(size=14, weight="bold"))
        back_btn.pack(side="left")
        step_lbl.pack(side="left", expand=True)
        next_btn.pack(side="right")

        def show(page: int):
            # Erst hier zusammenstellen: die Seitenfunktionen entstehen
            # weiter unten, ein Tupel auf Modulebene waere zu frueh.
            pages = (_page1, _page2, _page3)
            page = max(0, min(page, len(pages) - 1))
            state["page"] = page
            for child in body.winfo_children():
                child.destroy()
            pages[page]()
            step_lbl.configure(text=f"Step {page + 1} of {len(pages)}")
            back_btn.configure(state="normal" if page else "disabled")
            last = page == len(pages) - 1
            next_btn.configure(
                text="Done" if last else "Next  →",
                command=(self._close_oodle_wizard if last
                         else lambda: show(state["page"] + 1)))

        back_btn.configure(command=lambda: show(max(0, state["page"] - 1)))

        def heading(text: str):
            ctk.CTkLabel(body, text=text, anchor="w", justify="left",
                         font=ctk.CTkFont(size=20, weight="bold")
                         ).pack(fill="x", pady=(0, 10))

        def para(text: str, color: str | None = None, pady=(0, 10), size=15):
            ctk.CTkLabel(body, text=text, anchor="w", justify="left",
                         wraplength=810, text_color=color,
                         font=ctk.CTkFont(size=size)).pack(fill="x", pady=pady)

        def picture(name: str):
            path = _asset("help", name)
            try:
                img = tk.PhotoImage(file=str(path))
            except Exception:
                para(f"(image {name} could not be loaded)", "gray60")
                return
            state["images"].append(img)      # sonst raeumt der GC sie weg
            ctk.CTkLabel(body, image=img, text="").pack(pady=(4, 10))

        # ---------------------------------------------------------- Seite 1
        def _page1():
            heading("S2Tweaker needs one extra file, once")
            ctk.CTkLabel(
                body,
                text="⚠   Without this file S2Tweaker cannot read the values "
                     "out of your game.",
                anchor="w", justify="left", wraplength=810,
                text_color="#E6B800",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(fill="x", pady=(0, 10))
            para("Your game stores its configuration compressed. Unpacking that "
                 "needs Oodle (oo2core_9_win64.dll, 0.6 MB) – a library that "
                 "may not be shipped with this tool.\n\n"
                 "S2Tweaker does not download it, on purpose: a program that "
                 "fetches a library from the internet and then runs it looks "
                 "exactly like malware, and that is one reason antivirus "
                 "scanners flag tools like this one. So you fetch it once, "
                 "yourself – it takes a minute.")
            para("Sorry that this is on you. I did try to get rid of this step: "
                 "the library cannot legally be bundled, it cannot be taken out "
                 "of the game (it is compiled into the game's own executable), "
                 "and the open re-implementations carry no licence that would "
                 "allow shipping them. Fetching it automatically was the old "
                 "answer – and that is precisely what got this tool flagged as "
                 "a virus. One manual minute is the honest way out.", "gray60")
            para("1)  Copy the download link:", pady=(4, 4))
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x")
            entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=14), height=34)
            entry.insert(0, pakio.OODLE_URL)
            entry.configure(state="readonly")
            entry.pack(side="left", fill="x", expand=True)
            copy_btn = ctk.CTkButton(row, text="⧉  Copy", width=130, height=34,
                                     font=ctk.CTkFont(size=14))

            def do_copy():
                self.clipboard_clear()
                self.clipboard_append(pakio.OODLE_URL)
                copy_btn.configure(text="✓  Copied", fg_color="#2E7D32",
                                   hover_color="#2E7D32")

            copy_btn.configure(command=do_copy)
            copy_btn.pack(side="left", padx=(8, 0))
            para("Then click “Next” – the following steps show exactly what to "
                 "do with it.", "gray60", pady=(10, 0))

        # ---------------------------------------------------------- Seite 2
        def _page2():
            heading("Paste the link into your browser")
            picture("oodle_browser.png")
            para("Paste it into the address bar and press Enter. The download "
                 "starts on its own – there is no page to click through.")
            para("Your browser may warn that this file is unverified, or ask "
                 "whether you really want to keep it. That is normal for a "
                 ".dll and you have to confirm it. The file comes from Epic's "
                 "official Oodle release for Unreal Engine; S2Tweaker checks "
                 "its checksum before using it and refuses anything else.",
                 "#E6B800")

        # ---------------------------------------------------------- Seite 3
        def _page3():
            heading("Put the file next to S2Tweaker.exe")
            picture("oodle_folder.png")
            # Kein Updater-Skript mehr als Wegmarke: das gibt es seit 1.19.1
            # nicht mehr im Download. Das Bild zeigt es noch (es ist der
            # Ordner des Besitzers) — deshalb nennt der Text nur Dateien,
            # die JEDER wirklich hat. Nie eine Datei als Orientierung
            # nennen, die beim Nutzer gar nicht liegt.
            para("Move the downloaded oo2core_9_win64.dll into the folder that "
                 "holds S2Tweaker.exe – the same place as README.txt. "
                 "Not into the “_internal” folder.")
            target = ctk.CTkEntry(body, font=ctk.CTkFont(size=14), height=34)
            target.insert(0, str(self._oodle_target_dir()))
            target.configure(state="readonly")
            target.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                body,
                text="When the file is in place: restart S2Tweaker. "
                     "That is all – it never asks again.",
                anchor="w", justify="left", wraplength=810,
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(fill="x")

        show(page)
        win.after(250, win.lift)

    def _set_icon(self):
        try:
            ico = _asset("icon.ico")
            if ico.is_file():
                self.iconbitmap(str(ico))
        except Exception:
            pass

    # ------------------------------------------------------------ layout
    def _build_header(self):
        # Zeile 1: NUR der Spielordner (Wunsch des Besitzers: erst Ordner
        # bestaetigen, dann kommen die Werkzeuge — nichts vermischen)
        head = ctk.CTkFrame(self)
        head.pack(fill="x", padx=10, pady=(10, 4))
        self.game_label = ctk.CTkLabel(head, text="Game folder: searching ...", anchor="w")
        self.btn_confirm = ctk.CTkButton(
            head, text="✓ Confirm & load game data", width=200,
            fg_color="#2d6a3f", hover_color="#377f4c", command=self._confirm_game)
        self.btn_confirm.pack(side="right", padx=(4, 10), pady=8)
        self.btn_browse = ctk.CTkButton(head, text="Browse …", width=100,
                                        command=self._pick_game_dir)
        self.btn_browse.pack(side="right", padx=4, pady=8)
        # Der Pfad-Text wird ZULETZT gepackt und nimmt sich nur den Rest:
        # sonst draengt ein langer Spielpfad die Knoepfe zusammen.
        self.game_label.pack(side="left", padx=10, pady=8, fill="x", expand=True)

        # Zeile 2: Werkzeuge — Suche (waechst mit), Changed only, FAQ,
        # Oodle-Ampel. KEIN Update-Knopf mehr (1.19.2): das Programm
        # spricht mit keinem Server mehr, siehe Kopf der Datei.
        tools = ctk.CTkFrame(self)
        tools.pack(fill="x", padx=10, pady=(0, 4))
        self.search_entry = ctk.CTkEntry(tools, width=230,
                                         placeholder_text="🔍 Find a slider, weapon or ammo …")
        self.search_entry.pack(side="left", padx=(10, 4), pady=8,
                               fill="x", expand=True)
        self.btn_faq = ctk.CTkButton(tools, text="? FAQ", width=70,
                                     fg_color="gray30", hover_color="gray25",
                                     command=self._show_faq)
        self.btn_faq.pack(side="right", padx=(4, 10), pady=8)
        # Oodle-Ampel: auf einen Blick sichtbar, ob die Bibliothek da ist.
        # Klick oeffnet den Assistenten — auch dann, wenn alles stimmt, damit
        # man die Anleitung jederzeit nachlesen kann.
        self.btn_oodle = ctk.CTkButton(
            tools, text="● Oodle", width=132, fg_color="gray30",
            hover_color="gray25", command=self._open_oodle_wizard)
        self.btn_oodle.pack(side="right", padx=4, pady=8)
        self.btn_changed = ctk.CTkButton(
            tools, text="Changed only", width=105, fg_color="gray30",
            hover_color="gray25", command=self._toggle_changed_only)
        self.btn_changed.pack(side="right", padx=4, pady=8)
        self.search_entry.bind("<KeyRelease>", self._apply_filter)

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(8, 2), padx=4)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        return frame

    def _slider(self, parent, key: str, label: str, from_: float, to: float,
                step: float, default: float, fmt, tooltip: str = "",
                log: bool = False) -> None:
        self.sliders[key] = SliderRow(parent, label, from_, to, step, default,
                                      fmt, tooltip, log=log)
        self.slider_tabs[key] = self._current_tab

    def _warning(self, parent, text: str) -> None:
        """Auffaelliger (bernsteinfarbener) Hinweis unterhalb von Reglern."""
        ctk.CTkLabel(parent, text="⚠ " + text, anchor="w", justify="left",
                     wraplength=780, font=ctk.CTkFont(size=11),
                     text_color=ACCENT).pack(fill="x", padx=12, pady=(2, 4))

    def _collapsible_category(self, parent, cat: str, label: str) -> None:
        """Aufklappbarer Block mit den 5 Parameter-Reglern einer Kategorie."""
        btn = ctk.CTkButton(parent, text="▸  " + label, anchor="w",
                            fg_color="transparent", hover_color="gray25",
                            font=ctk.CTkFont(size=13))
        btn.pack(fill="x", padx=8, pady=1)
        content = ctk.CTkFrame(parent, fg_color="transparent")
        # Fuer die Suche merken: sonst bliebe dieser Block als einziger
        # Kategorie-Knopf im Fenster ungefaerbt, waehrend der gleich
        # aussehende Knopf im Overrides-Baum aufleuchtet.
        self._wcat_btns[cat] = (btn, label, btn.cget("text_color"), content)
        for param in WEAPON_PARAMS:
            self._slider(content, f"wcat_{cat}_{param}",
                         WEAPON_PARAM_LABELS[param], 0.25, 4, 0.25, 1, fmt_factor)

        def toggle():
            if content.winfo_manager():
                content.pack_forget()
            else:
                content.pack(fill="x", padx=16, after=btn)
            self._wcat_render(cat)

        btn.configure(command=toggle)
        self._wcat_render(cat)

    def _wcat_render(self, cat: str) -> None:
        """Beschriftung eines 'Weapon categories'-Knopfes neu zusammensetzen.

        Pfeil und Suchzusatz stecken beide in derselben Beschriftung — ohne
        diese eine Stelle wuerde das Auf-/Zuklappen den Suchhinweis wieder
        loeschen (und umgekehrt).
        """
        btn, label, _orig, content = self._wcat_btns[cat]
        open_ = bool(content.winfo_manager())
        arrow = "▾" if open_ else "▸"
        note = self._wcat_notes.get(cat, "")
        # Der Hinweis gehoert NUR an einen zugeklappten Block — er wird hier
        # und nicht beim Suchen angehaengt, sonst bliebe er nach einem Klick
        # auf den Kopf stehen ("click to show" ueber offenen Reglern).
        if note and not open_:
            note += "     click to show"
        btn.configure(text=f"{arrow}  {label}{note}")

    # -------------------------------------------- Einzelwaffen-Overrides
    def _iw_populate(self):
        """Waffenliste einlesen und den Overrides-Baum neu aufbauen."""
        if self.gd is None:
            return
        weapons = self.gd.player_weapons()
        self._iw_categories = {
            sid: cat for sid, (cat, _cws) in weapons.items() if cat
        }
        self._iw_dlc = self.gd.dlc_weapon_editions()
        # Waffen, die sich ein CharacterWeaponSettings-Struct teilen
        # (damage/spread/durability wirken dann auf die ganze Gruppe)
        by_cws: dict[str, list[str]] = {}
        for sid, (cat, cws) in weapons.items():
            if cat and cws:
                by_cws.setdefault(cws, []).append(sid)
        self._iw_share = {
            sid: sorted(o for o in group if o != sid)
            for group in by_cws.values() if len(group) > 1
            for sid in group
        }
        # Parameter, die die Waffe wirklich hat (wie _ia_mods/_ir_prot in den
        # anderen beiden Baeumen): fuer einen Wert, den es in den Spieldaten
        # nicht gibt, wird kein Regler gebaut.
        self._iw_params = {
            sid: weapon_available_params(self.gd, cws)
            for sid, (cat, cws) in weapons.items() if cat
        }
        # Verwaiste Overrides (Spiel-Update, andere Installation) verwerfen —
        # auch einzelne Parameter, die es fuer diese Waffe nicht mehr gibt
        # (sonst zaehlt die Zeile Overrides mit, zu denen der Regler fehlt).
        self.weapon_overrides = {
            sid: kept
            for sid, params in self.weapon_overrides.items()
            if sid in self._iw_categories
            and (kept := {p: v for p, v in params.items()
                          if p in self._iw_params.get(sid, WEAPON_PARAMS)})
        }
        # Kaliber (GitHub Issue #6): Vanilla-Wert je Waffe, die Auswahlliste
        # und wie viele Item-Prototypen an diesem Setup haengen. Letzteres
        # ist die ehrliche Zahl fuer den Hinweis "trifft auch NPCs": das
        # Kaliber sitzt am WeaponGeneralSetup, und die Spieler-AK-74,
        # Korshunovs AK und die Wach-AK teilen sich genau eines.
        self._iw_caliber = {
            sid: self.gd.weapon_caliber(sid, self._iw_dlc.get(sid))
            for sid in self._iw_categories
        }
        self._iw_caliber_options = sorted(
            swappable_calibers(self.gd),
            key=lambda c: (c in CALIBERS_ODD, caliber_label(c)))
        self._iw_setup_users = {
            sid: self.gd.weapon_caliber_users(sid)
            for sid in self._iw_categories
        }
        # Verwaiste Kaliberwahl genauso verwerfen wie verwaiste Overrides
        self.weapon_calibers = {
            sid: cal for sid, cal in self.weapon_calibers.items()
            if sid in self._iw_categories and cal in self._iw_caliber_options
        }
        self._iw_build_tree()

    def _iw_build_tree(self):
        """Baum verwerfen und neu aufbauen.

        Erst die Python-Referenzen loeschen, DANN die Widgets zerstoeren:
        danach kann kein Dict und keine Callback mehr auf einen zerstoerten
        Regler zeigen. Alles kommt zugeklappt zurueck.
        """
        # Ein noch wartendes Auto-Aufklappen wuerde gleich auf zerstoerte
        # Bloecke zugreifen — vor dem Abriss abbestellen.
        self._iw_cancel_expand()
        self._iw_blocks.clear()
        self._iw_auto_opened.clear()
        for child in list(self.iw_tree.winfo_children()):
            child.destroy()
        if not self._iw_categories:
            # Ohne Spieldaten: Aufforderung. MIT Spieldaten, aber ohne Waffen:
            # ehrliche Meldung statt einer schon erledigten Aufforderung.
            text = ("   – load game data first –" if self.gd is None else
                    "   – no player weapons found in this game version –")
            ctk.CTkLabel(self.iw_tree, text=text,
                         anchor="w", font=self._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12)
            self._iw_update_info()
            return
        by_cat: dict[str, list[str]] = {}
        for sid, cat in self._iw_categories.items():
            by_cat.setdefault(cat, []).append(sid)
        for cat, label in WEAPON_CATEGORY_LABELS.items():
            if by_cat.get(cat):
                self._iw_blocks[cat] = IwCategoryBlock(
                    self, self.iw_tree, cat, label, sorted(by_cat[cat]))
        # Unbekannte Kategorien (kuenftige Spiel-Patches) nicht verstecken
        for cat in sorted(set(by_cat) - set(WEAPON_CATEGORY_LABELS)):
            self._iw_blocks[cat] = IwCategoryBlock(
                self, self.iw_tree, cat, cat.title(), sorted(by_cat[cat]))
        self._iw_update_info()

    def _iw_after_change(self, cat: str):
        """Nach einer Aenderung: Kategorie-Zaehler und Info-Zeile auffrischen."""
        block = self._iw_blocks.get(cat)
        if block is not None:
            block.refresh()
        self._iw_update_info()

    def _iw_update_info(self):
        namen = sorted(set(self.weapon_overrides) | set(self.weapon_calibers))
        if namen:
            text = "Overrides set for: " + ", ".join(namen)
        else:
            text = "No per-weapon overrides set."
        self.iw_info.configure(text=text)

    def _iw_refresh_all(self):
        """Alle GEBAUTEN Regler und Marker an weapon_overrides angleichen."""
        for block in self._iw_blocks.values():
            for row in block.rows.values():
                row.load_values()
            block.refresh()
        self._iw_update_info()

    def _iw_clear_all(self):
        self.weapon_overrides.clear()
        self.weapon_calibers.clear()
        self._iw_refresh_all()

    def _iw_note(self, block, cat_hit: bool, sid_hits: list, hits) -> None:
        """Kopfzeile eines Kategorie-Blocks fuer die laufende Suche setzen."""
        if sid_hits:
            note = (f"     {len(sid_hits)} match"
                    f"{'es' if len(sid_hits) != 1 else ''}")
        elif cat_hit:
            note = "     category match"   # keine Zahl: siehe _iw_filter
        else:
            note = ""
        block.set_highlight("match" if hits else "dim", note, bool(hits))

    def _iw_cancel_expand(self) -> None:
        if self._iw_expand_job is not None:
            try:
                self.after_cancel(self._iw_expand_job)
            except Exception:
                pass
            self._iw_expand_job = None

    def _iw_filter(self, query: str) -> int:
        """Suchfeld auf den Waffenbaum anwenden; liefert die Trefferzahl.

        Gesucht wird in block.sids / block.label (reine Strings), gefaerbt
        wird nur, was schon gebaut ist -- daher nie ein Absturz auf noch
        nicht aufgeklappten Zeilen. Der Treffersatz bleibt im Block liegen
        (set_row_filter), damit spaeter gebaute Zeilen die Farbe erben.

        Faerben passiert SOFORT, das Auto-Aufklappen erst verzoegert in
        _iw_auto_expand: das Bauen von Waffenzeilen kostet spuerbar Zeit,
        und beim Tippen von "rifle" waere das Fenster sonst mitten im Wort
        mehrfach eingefroren.
        """
        self._iw_cancel_expand()
        if not query:
            for cat in list(self._iw_auto_opened):
                block = self._iw_blocks.get(cat)
                if block is not None:
                    block.collapse()
            self._iw_auto_opened.clear()
            for block in self._iw_blocks.values():
                block.set_highlight("normal", "")
                block.set_row_filter(None)
            return 0
        hits_total = 0
        for cat, block in self._iw_blocks.items():
            cat_hit = query in block.label.lower() or query in cat.lower()
            sid_hits = [sid for sid in block.sids
                        if weapon_sid_hit(sid, query)]
            # Hervorgehoben wird bei einem Kategorie-Treffer die ganze
            # Kategorie, gezaehlt werden aber nur echte Waffentreffer bzw.
            # EIN Treffer fuer die Kategorie -- Kopfzeile und Statuszeile
            # muessen dieselbe Zahl nennen.
            hits = block.sids if cat_hit else sid_hits
            hits_total += len(sid_hits) if sid_hits else (1 if cat_hit else 0)
            # Treffersatz VOR dem Aufklappen setzen, damit frisch gebaute
            # Zeilen sofort in der richtigen Farbe erscheinen.
            block.set_row_filter(set(hits))
            # Kategorien, die die Suche frueher aufgeklappt hat und die jetzt
            # nicht mehr passen, wieder zuklappen (von Hand geoeffnete nicht:
            # die stehen dank IwCategoryBlock.toggle nicht in _iw_auto_opened).
            if not hits and cat in self._iw_auto_opened:
                block.collapse()
                self._iw_auto_opened.discard(cat)
            self._iw_note(block, cat_hit, sid_hits, hits)
        if self._iw_blocks:
            self._iw_expand_job = self.after(
                250, lambda q=query: self._iw_auto_expand(q))
        return hits_total

    def _iw_auto_expand(self, query: str) -> None:
        """Verzoegerter Teil der Suche: passende Kategorien aufklappen.

        Laeuft erst, wenn 250 ms lang nichts mehr getippt wurde, und bricht
        ab, falls das Suchfeld inzwischen etwas anderes enthaelt.
        """
        self._iw_expand_job = None
        if self.search_entry.get().strip().lower() != query:
            return
        built = 0            # in DIESEM Durchgang neu erzeugte Waffenzeilen
        for cat, block in self._iw_blocks.items():
            cat_hit = query in block.label.lower() or query in cat.lower()
            sid_hits = [sid for sid in block.sids
                        if weapon_sid_hit(sid, query)]
            hits = block.sids if cat_hit else sid_hits
            # Auto-Aufklappen nur bei einer GEZIELTEN Suche und nur, solange
            # das Budget an neu zu bauenden Zeilen reicht. Entscheidend ist,
            # wie viele Zeilen dabei entstehen -- nicht wie viele Treffer es
            # gibt: jede Waffen-SID beginnt mit "Gun", ein "gu" haette sonst
            # den halben Baum im Hintergrund erzeugt. Schon gebaute
            # Kategorien kosten nichts und duerfen immer wieder auf.
            specific = len(sid_hits) <= 8      # nicht "passt sowieso alles"
            if hits and specific and len(query) >= 3 and not block.expanded:
                cost = 0 if block.rows else len(block.sids)
                if built + cost <= 30:
                    built += cost
                    block.expand()   # refresh() nimmt den Hinweis selbst weg
                    self._iw_auto_opened.add(cat)

    # -------------------------------------------- Einzelmunitions-Overrides
    def _ia_populate(self):
        """Munitionsliste einlesen und den Ammo-Baum neu aufbauen."""
        if self.gd is None:
            return
        kinds = self.gd.ammo_kinds()
        self._ia_mods = self.gd.ammo_mods()
        self._ia_calibers = {sid: cal for sid, (cal, _t) in kinds.items()}
        self._ia_types = {
            sid: AMMO_TYPE_LABELS.get(typ, typ)
            for sid, (_c, typ) in kinds.items()
        }
        # Verwaiste Overrides (Spiel-Update, andere Installation) verwerfen.
        # Erst HIER moeglich: vorher sind die gueltigen SIDs nicht bekannt.
        # Dazu Faktoren auf Werte werfen, die in dieser Spielversion 0 sind:
        # sie erzeugen keinen Patch (0 × Faktor = 0), wuerden aber im
        # Ergebnis-Dialog auftauchen und die Zaehler der Zeilen sprengen.
        cleaned = {}
        for sid, params in self.ammo_overrides.items():
            if sid not in self._ia_calibers:
                continue
            mods = self._ia_mods.get(sid, {})
            kept = {p: v for p, v in params.items()
                    if not mods or p not in AMMO_PARAM_KEYS
                    or abs(mods.get(AMMO_PARAM_KEYS[p], 0.0)) > 1e-9}
            if kept:
                cleaned[sid] = kept
        self.ammo_overrides = cleaned
        self._ia_build_tree()

    def _ia_build_tree(self):
        """Baum verwerfen und neu aufbauen (erst Referenzen, dann Widgets)."""
        self._ia_cancel_expand()
        self._ia_blocks.clear()
        self._ia_auto_opened.clear()
        for child in list(self.ia_tree.winfo_children()):
            child.destroy()
        if not self._ia_calibers:
            text = ("   – load game data first –" if self.gd is None else
                    "   – no ammo found in this game version –")
            ctk.CTkLabel(self.ia_tree, text=text, anchor="w",
                         font=self._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12)
            self._ia_update_info()
            return
        by_cal: dict[str, list[str]] = {}
        for sid, cal in self._ia_calibers.items():
            by_cal.setdefault(cal, []).append(sid)
        # Innerhalb eines Kalibers nach SORTE sortieren (Standard zuerst),
        # nicht alphabetisch: die SIDs sind fuer den Benutzer bedeutungslos.
        order = list(AMMO_TYPE_LABELS.values())

        def sort_key(sid: str):
            label = self._ia_types.get(sid, "")
            rank = order.index(label) if label in order else len(order)
            return (rank, sid)

        for cal, label in AMMO_CALIBER_LABELS.items():
            if by_cal.get(cal):
                self._ia_blocks[cal] = IaCaliberBlock(
                    self, self.ia_tree, cal, label,
                    sorted(by_cal[cal], key=sort_key))
        # Unbekannte Kaliber (kuenftige Spiel-Patches) nicht verstecken:
        # Beschriftung = roher Enum-Schwanz. Die Karte ist Nachschlagewerk,
        # kein Filter. sorted() bekommt nie None (ammo_kinds liefert "").
        for cal in sorted(set(by_cal) - set(AMMO_CALIBER_LABELS)):
            self._ia_blocks[cal] = IaCaliberBlock(
                self, self.ia_tree, cal, cal or "Other",
                sorted(by_cal[cal], key=sort_key))
        self._ia_update_info()

    def _ia_after_change(self, cal: str):
        block = self._ia_blocks.get(cal)
        if block is not None:
            block.refresh()
        self._ia_update_info()

    def _ia_update_info(self):
        if self.ammo_overrides:
            # Lesbare Namen statt SIDs: "A012D" sagt ausserhalb des Baums
            # niemandem etwas, "12 gauge standard" schon.
            text = "Overrides set for: " + ", ".join(
                ammo_label(sid) for sid in sorted(self.ammo_overrides))
        else:
            text = "No per-ammo overrides set."
        self.ia_info.configure(text=text)

    def _ia_refresh_all(self):
        """Alle GEBAUTEN Regler und Marker an ammo_overrides angleichen.
        Vertraegt einen leeren Baum -- laeuft auch ohne Spieldaten."""
        for block in self._ia_blocks.values():
            for row in block.rows.values():
                row.load_values()
            block.refresh()
        self._ia_update_info()

    def _ia_clear_all(self):
        self.ammo_overrides.clear()
        self._ia_refresh_all()

    def _ia_note(self, block, cal_hit: bool, sid_hits: list, hits) -> None:
        if sid_hits:
            note = (f"     {len(sid_hits)} match"
                    f"{'es' if len(sid_hits) != 1 else ''}")
        elif cal_hit:
            note = "     caliber match"    # keine Zahl: siehe _ia_filter
        else:
            note = ""
        block.set_highlight("match" if hits else "dim", note, bool(hits))

    def _ia_cancel_expand(self) -> None:
        if self._ia_expand_job is not None:
            try:
                self.after_cancel(self._ia_expand_job)
            except Exception:
                pass
            self._ia_expand_job = None

    @staticmethod
    def _ia_norm(text: str) -> str:
        """'5.45×39 mm' -> '5.45x39 mm'. Das Malzeichen steht auf keiner
        Tastatur -- ohne diese Normalisierung fiele die Kaliber-Suche aus."""
        return text.lower().replace("×", "x")

    def _ia_sid_hit(self, sid: str, q: str) -> bool:
        """SID oder Sorte ("armor-piercing", "standard", ...): die Sorte ist
        das einzige unterscheidende Merkmal zwischen A545A/A545D/A545E und
        steht als einzige nicht schon im zugeklappten Baum."""
        return q in sid.lower() or q in self._ia_norm(
            self._ia_types.get(sid, ""))

    def _ia_filter(self, query: str) -> int:
        """Suchfeld auf den Ammo-Baum anwenden; liefert die Trefferzahl.
        Faerben sofort, Auto-Aufklappen verzoegert (siehe _ia_auto_expand)."""
        self._ia_cancel_expand()
        if not query:
            for cal in list(self._ia_auto_opened):
                block = self._ia_blocks.get(cal)
                if block is not None:
                    block.collapse()
            self._ia_auto_opened.clear()
            for block in self._ia_blocks.values():
                block.set_highlight("normal", "")
                block.set_row_filter(None)
            return 0
        q = self._ia_norm(query)
        hits_total = 0
        for cal, block in self._ia_blocks.items():
            cal_hit = q in self._ia_norm(block.label) or q in cal.lower()
            sid_hits = [sid for sid in block.sids if self._ia_sid_hit(sid, q)]
            # Gleiche Zaehlregel wie im Waffenbaum: entweder die echten
            # SID-Treffer oder EIN Treffer fuer das Kaliber -- Kopfzeile und
            # Statuszeile muessen dieselbe Zahl nennen.
            hits = block.sids if cal_hit else sid_hits
            hits_total += len(sid_hits) if sid_hits else (1 if cal_hit else 0)
            block.set_row_filter(set(hits))
            if not hits and cal in self._ia_auto_opened:
                block.collapse()
                self._ia_auto_opened.discard(cal)
            self._ia_note(block, cal_hit, sid_hits, hits)
        if self._ia_blocks:
            self._ia_expand_job = self.after(
                250, lambda x=q: self._ia_auto_expand(x))
        return hits_total

    def _ia_auto_expand(self, q: str) -> None:
        """Verzoegerter Teil: passende Kaliber aufklappen. Bricht ab, falls
        im Suchfeld inzwischen etwas anderes steht. Eigenes Budget -- der
        Ammo-Baum darf dem Waffenbaum keine Zeilen wegnehmen."""
        self._ia_expand_job = None
        if self._ia_norm(self.search_entry.get().strip()) != q:
            return
        built = 0
        for cal, block in self._ia_blocks.items():
            cal_hit = q in self._ia_norm(block.label) or q in cal.lower()
            sid_hits = [sid for sid in block.sids if self._ia_sid_hit(sid, q)]
            hits = block.sids if cal_hit else sid_hits
            specific = len(sid_hits) <= 8
            if hits and specific and len(q) >= 3 and not block.expanded:
                cost = 0 if block.rows else len(block.sids)
                if built + cost <= 30:
                    built += cost
                    block.expand()
                    self._ia_auto_opened.add(cal)

    # -------------------------------------------- Einzelruestungs-Baum
    ARMOR_GROUP_LABELS = {"Body": "Body armor", "Head": "Helmets"}

    def _ir_populate(self):
        """Ruestungsliste einlesen und den Armor-Baum neu aufbauen."""
        if self.gd is None:
            return
        from .tweaks import ARMOR_PARAM_KEYS
        key_to_param = {v: k for k, v in ARMOR_PARAM_KEYS.items()}
        armors = self.gd.player_armors()
        self._ir_groups = {sid: slot for sid, (slot, _v) in armors.items()}
        self._ir_prot = {
            sid: {key_to_param[key]: value for key, value in values.items()
                  if key in key_to_param}
            for sid, (_s, values) in armors.items()
        }
        self._ir_labels = {sid: armor_label(sid) for sid in armors}
        self._ir_dlc = self.gd.dlc_armor_editions()
        # Verwaiste Overrides verwerfen (Spiel-Update, andere Installation);
        # dazu Faktoren auf Schutzarten, die es an dieser Ruestung nicht
        # gibt (0 in Vanilla -> kein Regler, kein Patch).
        cleaned = {}
        for sid, params in self.armor_overrides.items():
            if sid not in self._ir_prot:
                continue
            kept = {p: v for p, v in params.items()
                    if p in self._ir_prot[sid]}
            if kept:
                cleaned[sid] = kept
        self.armor_overrides = cleaned
        self._ir_build_tree()

    def _ir_build_tree(self):
        """Baum verwerfen und neu aufbauen (erst Referenzen, dann Widgets)."""
        self._ir_cancel_expand()
        self._ir_blocks.clear()
        self._ir_auto_opened.clear()
        for child in list(self.ir_tree.winfo_children()):
            child.destroy()
        if not self._ir_groups:
            text = ("   \u2013 load game data first \u2013" if self.gd is None else
                    "   \u2013 no armor found in this game version \u2013")
            ctk.CTkLabel(self.ir_tree, text=text, anchor="w",
                         font=self._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12)
            self._ir_update_info()
            return
        by_group: dict[str, list[str]] = {}
        for sid, group in self._ir_groups.items():
            by_group.setdefault(group, []).append(sid)

        def sort_key(sid: str):
            return self._ir_labels.get(sid, sid).lower()

        for group, label in self.ARMOR_GROUP_LABELS.items():
            if by_group.get(group):
                self._ir_blocks[group] = IrGroupBlock(
                    self, self.ir_tree, group, label,
                    sorted(by_group[group], key=sort_key))
        # Unbekannte Slots kuenftiger Spiel-Patches nicht verstecken.
        for group in sorted(set(by_group) - set(self.ARMOR_GROUP_LABELS)):
            self._ir_blocks[group] = IrGroupBlock(
                self, self.ir_tree, group, group or "Other",
                sorted(by_group[group], key=sort_key))
        self._ir_update_info()

    def _ir_after_change(self, group: str):
        block = self._ir_blocks.get(group)
        if block is not None:
            block.refresh()
        self._ir_update_info()

    def _ir_update_info(self):
        if self.armor_overrides:
            # armor_label als Fallback: VOR dem Laden der Spieldaten ist
            # _ir_labels leer, rohe SIDs sollen trotzdem nie erscheinen
            # (Gleichstand mit dem Ammo-Zwilling, der ammo_label nutzt).
            text = "Overrides set for: " + ", ".join(
                self._ir_labels.get(sid) or armor_label(sid)
                for sid in sorted(self.armor_overrides))
        else:
            text = "No per-armor overrides set."
        self.ir_info.configure(text=text)

    def _ir_refresh_all(self):
        """Alle GEBAUTEN Regler und Marker an armor_overrides angleichen.
        Vertraegt einen leeren Baum -- laeuft auch ohne Spieldaten."""
        for block in self._ir_blocks.values():
            for row in block.rows.values():
                row.load_values()
            block.refresh()
        self._ir_update_info()

    def _ir_clear_all(self):
        self.armor_overrides.clear()
        self._ir_refresh_all()

    def _ir_cancel_expand(self) -> None:
        if self._ir_expand_job is not None:
            try:
                self.after_cancel(self._ir_expand_job)
            except Exception:
                pass
            self._ir_expand_job = None

    def _ir_sid_hit(self, sid: str, q: str) -> bool:
        """SID oder lesbares Label ("SEVA (Loners)"): der Nutzer sucht nach
        dem, was er im Spiel sieht, nicht nach SIDs."""
        return q in sid.lower() or q in self._ir_labels.get(sid, "").lower()

    def _ir_filter(self, query: str) -> int:
        """Suchfeld auf den Armor-Baum anwenden; liefert die Trefferzahl."""
        self._ir_cancel_expand()
        if not query:
            for group in list(self._ir_auto_opened):
                block = self._ir_blocks.get(group)
                if block is not None:
                    block.collapse()
            self._ir_auto_opened.clear()
            for block in self._ir_blocks.values():
                block.set_highlight("normal", "")
                block.set_row_filter(None)
            return 0
        q = query.lower()
        hits_total = 0
        for group, block in self._ir_blocks.items():
            group_hit = q in block.label.lower() or q in group.lower()
            sid_hits = [sid for sid in block.sids if self._ir_sid_hit(sid, q)]
            hits = block.sids if group_hit else sid_hits
            hits_total += len(sid_hits) if sid_hits else (1 if group_hit else 0)
            block.set_row_filter(set(hits))
            if not hits and group in self._ir_auto_opened:
                block.collapse()
                self._ir_auto_opened.discard(group)
            if sid_hits:
                note = (f"     {len(sid_hits)} match"
                        f"{'es' if len(sid_hits) != 1 else ''}")
            elif group_hit:
                note = "     group match"
            else:
                note = ""
            block.set_highlight("match" if hits else "dim", note, bool(hits))
        if self._ir_blocks:
            self._ir_expand_job = self.after(
                250, lambda x=q: self._ir_auto_expand(x))
        return hits_total

    def _ir_auto_expand(self, q: str) -> None:
        """Verzoegerter Teil: passende Gruppen aufklappen. Eigenes Budget,
        damit der Armor-Baum Waffen und Munition keine Zeilen wegnimmt."""
        self._ir_expand_job = None
        if self.search_entry.get().strip().lower() != q:
            return
        built = 0
        for group, block in self._ir_blocks.items():
            group_hit = q in block.label.lower() or q in group.lower()
            sid_hits = [sid for sid in block.sids if self._ir_sid_hit(sid, q)]
            hits = block.sids if group_hit else sid_hits
            specific = len(sid_hits) <= 8
            if hits and specific and len(q) >= 3 and not block.expanded:
                cost = 0 if block.rows else len(block.sids)
                if built + cost <= 45:
                    built += cost
                    block.expand()
                    self._ir_auto_opened.add(group)

    # -------------------------------------------- Fraktionsbeziehungen
    def _if_populate(self):
        """Beziehungspaare der kuratierten Haupt-Fraktionen einlesen und
        den Fraktions-Baum neu aufbauen (docs/FACTION_RELATIONS_RESEARCH.md).
        Nur Paare anbieten, die es in den Spieldaten wirklich gibt."""
        if self.gd is None:
            return
        pairs = self.gd.relation_pairs()
        self._if_vanilla = {}
        self._if_labels = {}
        player_keys: list[str] = []
        for sid, label in FACTION_CHOICES:
            key = self.gd.relation_pair_key(sid, "Player")
            if key is None:
                continue
            self._if_vanilla[key] = pairs[key]
            self._if_labels[key] = f"{label} ↔ you"
            player_keys.append(key)
        groups: list[tuple[str, str, list[str]]] = []
        for i, (sid, label) in enumerate(FACTION_CHOICES):
            keys: list[str] = []
            for sid2, label2 in FACTION_CHOICES[i + 1:]:
                key = self.gd.relation_pair_key(sid, sid2)
                if key is None or key in self._if_vanilla:
                    continue
                self._if_vanilla[key] = pairs[key]
                self._if_labels[key] = f"{label} ↔ {label2}"
                keys.append(key)
            if keys:
                groups.append((sid, label, keys))
        self._if_player_keys = player_keys
        self._if_groups = groups
        # Verwaiste (anderes Spiel/altes Preset) und Vanilla-gleiche
        # Eintraege verwerfen — dieselbe Hygiene wie bei den Overrides.
        cleaned: dict[str, int] = {}
        for key, value in self.faction_relations.items():
            vanilla = self._if_vanilla.get(key)
            if vanilla is None:
                continue
            try:
                v = int(round(float(value)))
            except (TypeError, ValueError):
                continue
            if v != vanilla:
                cleaned[key] = v
        self.faction_relations = cleaned
        self._if_build_tree()

    def _if_build_tree(self):
        """Baum verwerfen und neu aufbauen; der Spieler-Block startet
        aufgeklappt (er ist der Hauptanwendungsfall des Tabs)."""
        self._if_cancel_expand()
        self._if_blocks.clear()
        self._if_rows.clear()
        self._if_auto_opened.clear()
        for child in list(self.if_tree.winfo_children()):
            child.destroy()
        if not self._if_vanilla:
            text = ("   – load game data first –" if self.gd is None
                    else "   – no faction relations found in this game "
                         "version –")
            ctk.CTkLabel(self.if_tree, text=text, anchor="w",
                         font=self._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12)
            self._if_update_info()
            return
        if self._if_player_keys:
            self._if_blocks["player"] = IfFactionBlock(
                self, self.if_tree, "player", "You (Skif) ↔ factions",
                list(self._if_player_keys))
        for sid, label, keys in self._if_groups:
            self._if_blocks[sid] = IfFactionBlock(
                self, self.if_tree, sid, f"{label} ↔ others", list(keys))
        player = self._if_blocks.get("player")
        if player is not None:
            player.expand()
        self._if_update_info()

    def _if_row_changed(self, key: str):
        if self._if_loading:
            return
        row = self._if_rows.get(key)
        vanilla = self._if_vanilla.get(key)
        if row is None or vanilla is None:
            return
        value = int(round(row.get()))
        if value != vanilla:
            self.faction_relations[key] = value
        else:
            self.faction_relations.pop(key, None)
        self._if_after_change()

    def _if_after_change(self):
        for block in self._if_blocks.values():
            block.refresh()
        self._if_update_info()
        self._if_update_conflict_note()   # Warnstufe haengt am eigenen Stand

    def _if_update_info(self):
        if self.faction_relations:
            parts = []
            for key in sorted(self.faction_relations):
                label = self._if_labels.get(key, key)
                parts.append(f"{label}: {fmt_relation(self.faction_relations[key])}")
            text = "Changed: " + "  ·  ".join(parts)
        else:
            text = "No relations changed."
        self.if_info.configure(text=text)

    def _if_refresh_all(self):
        """Alle GEBAUTEN Regler und Marker an faction_relations angleichen.
        Vertraegt einen leeren Baum — laeuft auch ohne Spieldaten."""
        for block in self._if_blocks.values():
            block.load_values()
            block.refresh()
        self._if_update_info()

    def _if_clear_all(self):
        self.faction_relations.clear()
        self._if_refresh_all()

    def _if_cancel_expand(self) -> None:
        if self._if_expand_job is not None:
            try:
                self.after_cancel(self._if_expand_job)
            except Exception:
                pass
            self._if_expand_job = None

    def _if_pair_hit(self, key: str, q: str) -> bool:
        """Paar-Schluessel ODER Anzeigename ("Duty ↔ Freedom"): der Nutzer
        sucht nach dem, was er im Spiel sieht."""
        return q in key.lower() or q in self._if_labels.get(key, "").lower()

    def _if_filter(self, query: str) -> int:
        """Suchfeld auf den Fraktions-Baum anwenden; liefert die Trefferzahl."""
        self._if_cancel_expand()
        if not query:
            for group in list(self._if_auto_opened):
                block = self._if_blocks.get(group)
                if block is not None:
                    block.collapse()
            self._if_auto_opened.clear()
            for block in self._if_blocks.values():
                block.set_highlight("normal", "")
                block.set_row_filter(None)
            return 0
        q = query.lower()
        hits_total = 0
        for group, block in self._if_blocks.items():
            group_hit = q in block.label.lower() or q in group.lower()
            key_hits = [key for key in block.sids if self._if_pair_hit(key, q)]
            hits = block.sids if group_hit else key_hits
            hits_total += len(key_hits) if key_hits else (1 if group_hit else 0)
            block.set_row_filter(set(hits))
            if not hits and group in self._if_auto_opened:
                block.collapse()
                self._if_auto_opened.discard(group)
            if key_hits:
                note = (f"     {len(key_hits)} match"
                        f"{'es' if len(key_hits) != 1 else ''}")
            elif group_hit:
                note = "     group match"
            else:
                note = ""
            block.set_highlight("match" if hits else "dim", note, bool(hits))
        if self._if_blocks:
            self._if_expand_job = self.after(
                250, lambda x=q: self._if_auto_expand(x))
        return hits_total

    def _if_auto_expand(self, q: str) -> None:
        """Verzoegerter Teil: passende Bloecke aufklappen (eigenes Budget,
        damit der Fraktions-Baum den anderen Baeumen nichts wegnimmt)."""
        self._if_expand_job = None
        if self.search_entry.get().strip().lower() != q:
            return
        built = 0
        for group, block in self._if_blocks.items():
            group_hit = q in block.label.lower() or q in group.lower()
            key_hits = [key for key in block.sids if self._if_pair_hit(key, q)]
            hits = block.sids if group_hit else key_hits
            specific = len(key_hits) <= 8
            if hits and specific and len(q) >= 3 and not block.expanded:
                cost = 0 if block.rows else len(block.sids)
                if built + cost <= 45:
                    built += cost
                    block.expand()
                    self._if_auto_opened.add(group)

    # -------------------------------------------- Mutanten-Overrides
    def _im_populate(self):
        """Mutanten-Arten einlesen und den Arten-Baum neu aufbauen.

        Je Art nur die Regler anbieten, die wirklich wirken: hp/speed
        immer (jeder Prototyp hat MaxHP/MovementParams), damage nur bei
        Arten mit Damage-Attacken in AbilityPrototypes (Poltergeist/Rat
        wirken indirekt), regen nur bei Vanilla-Regeneration > 0."""
        if self.gd is None:
            return
        hp_by_species: dict[str, list[float]] = {}
        proto_count: dict[str, int] = {}
        for sid, hp in self.gd.mutants().items():
            species = self.gd.mutant_faction(sid)
            if species:
                hp_by_species.setdefault(species, []).append(hp)
                proto_count[species] = proto_count.get(species, 0) + 1
        regen_by_species: dict[str, list[float]] = {}
        for sid, regen in self.gd.mutant_regens().items():
            species = self.gd.mutant_faction(sid)
            if species:
                regen_by_species.setdefault(species, []).append(regen)
        species_list = sorted(hp_by_species)
        self._im_species = species_list
        self._im_params = {}
        self._im_hints = {}
        for species in species_list:
            params = ["hp", "speed"]
            attacks = self.gd.mutant_attack_damages(species)
            if attacks:
                params.append("damage")
            if regen_by_species.get(species):
                params.append("regen")
            self._im_params[species] = params
            hps = hp_by_species[species]
            parts = [f"{proto_count[species]} prototype"
                     f"{'s' if proto_count[species] != 1 else ''}",
                     (f"vanilla HP {min(hps):g}" if len(hps) == 1 or
                      min(hps) == max(hps)
                      else f"vanilla HP {min(hps):g}–{max(hps):g}")]
            if attacks:
                parts.append(f"{len(attacks)} attack"
                             f"{'s' if len(attacks) != 1 else ''}")
            else:
                parts.append("damage dealt indirectly – no damage slider")
            regs = regen_by_species.get(species)
            if regs:
                parts.append(f"regen {min(regs):g}"
                             + ("" if min(regs) == max(regs)
                                else f"–{max(regs):g}") + " HP/s")
            self._im_hints[species] = " · ".join(parts)
        # Verwaiste Arten/Parameter verwerfen (Spiel-Update, alter Preset)
        cleaned: dict[str, dict[str, float]] = {}
        for sp, params in self.mutant_overrides.items():
            if sp not in self._im_params:
                continue
            kept = {p: v for p, v in params.items()
                    if p in self._im_params[sp]}
            if kept:
                cleaned[sp] = kept
        self.mutant_overrides = cleaned
        self._im_build_tree()

    def _im_build_tree(self):
        self._im_cancel_expand()
        self._im_blocks.clear()
        self._im_auto_opened.clear()
        for child in list(self.im_tree.winfo_children()):
            child.destroy()
        if not self._im_species:
            text = ("   – load game data first –" if self.gd is None else
                    "   – no mutants found in this game version –")
            ctk.CTkLabel(self.im_tree, text=text, anchor="w",
                         font=self._iw_font_hint,
                         text_color="gray60").pack(fill="x", padx=12)
            self._im_update_info()
            return
        assigned: set[str] = set()
        for group, label, members in MUT_GROUPS:
            sids = [s for s in members if s in self._im_params]
            if sids:
                self._im_blocks[group] = ImGroupBlock(
                    self, self.im_tree, group, label, sids)
                assigned |= set(sids)
        rest = sorted(set(self._im_species) - assigned,
                      key=lambda s: mutant_species_label(s).lower())
        if rest:
            self._im_blocks["other"] = ImGroupBlock(
                self, self.im_tree, "other", "Other species", rest)
        self._im_update_info()

    def _im_after_change(self, group: str):
        block = self._im_blocks.get(group)
        if block is not None:
            block.refresh()
        self._im_update_info()

    def _im_update_info(self):
        if self.mutant_overrides:
            text = "Overrides set for: " + ", ".join(
                mutant_species_label(s) for s in sorted(self.mutant_overrides))
        else:
            text = "No per-species overrides set."
        self.im_info.configure(text=text)

    def _im_refresh_all(self):
        for block in self._im_blocks.values():
            for row in block.rows.values():
                row.load_values()
            block.refresh()
        self._im_update_info()

    def _im_clear_all(self):
        self.mutant_overrides.clear()
        self._im_refresh_all()

    def _im_cancel_expand(self) -> None:
        if self._im_expand_job is not None:
            try:
                self.after_cancel(self._im_expand_job)
            except Exception:
                pass
            self._im_expand_job = None

    def _im_species_hit(self, species: str, q: str) -> bool:
        return (q in species.lower()
                or q in mutant_species_label(species).lower())

    def _im_filter(self, query: str) -> int:
        """Suchfeld auf den Mutanten-Baum anwenden; liefert Trefferzahl."""
        self._im_cancel_expand()
        if not query:
            for group in list(self._im_auto_opened):
                block = self._im_blocks.get(group)
                if block is not None:
                    block.collapse()
            self._im_auto_opened.clear()
            for block in self._im_blocks.values():
                block.set_highlight("normal", "")
                block.set_row_filter(None)
            return 0
        q = query.lower()
        hits_total = 0
        for group, block in self._im_blocks.items():
            group_hit = q in block.label.lower() or q in group.lower()
            sid_hits = [s for s in block.sids if self._im_species_hit(s, q)]
            hits = block.sids if group_hit else sid_hits
            hits_total += len(sid_hits) if sid_hits else (1 if group_hit else 0)
            block.set_row_filter(set(hits))
            if not hits and group in self._im_auto_opened:
                block.collapse()
                self._im_auto_opened.discard(group)
            if sid_hits:
                note = (f"     {len(sid_hits)} match"
                        f"{'es' if len(sid_hits) != 1 else ''}")
            elif group_hit:
                note = "     group match"
            else:
                note = ""
            block.set_highlight("match" if hits else "dim", note, bool(hits))
        if self._im_blocks:
            self._im_expand_job = self.after(
                250, lambda x=q: self._im_auto_expand(x))
        return hits_total

    def _im_auto_expand(self, q: str) -> None:
        self._im_expand_job = None
        if self.search_entry.get().strip().lower() != q:
            return
        built = 0
        for group, block in self._im_blocks.items():
            group_hit = q in block.label.lower() or q in group.lower()
            sid_hits = [s for s in block.sids if self._im_species_hit(s, q)]
            hits = block.sids if group_hit else sid_hits
            specific = len(sid_hits) <= 8
            if hits and specific and len(q) >= 3 and not block.expanded:
                cost = 0 if block.rows else len(block.sids)
                if built + cost <= 45:
                    built += cost
                    block.expand()
                    self._im_auto_opened.add(group)

    def _check(self, parent, key: str, label: str, tooltip: str = "") -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(anchor="w", fill="x", **PAD)
        box = ctk.CTkCheckBox(row, text=label,
                              command=lambda k=key: self._update_check_dot(k))
        box.pack(side="left")
        self.checks[key] = box
        dot = ctk.CTkLabel(row, text="", width=16)
        dot.pack(side="left")
        self.check_dots[key] = dot
        HoverTip(dot, lambda k=key: self._check_tips.get(k, ""))
        # Klick auf das Schloss schaltet eine Avoid-Sperre frei
        dot.bind("<Button-1>",
                 lambda _e, k=key: (k in self._locked_checks
                                    and self._avoid_unlock("check:" + k)))
        if tooltip:
            ctk.CTkLabel(parent, text="      " + tooltip, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)

    def _tab(self, name: str) -> ctk.CTkScrollableFrame:
        """Neuen Tab anlegen und scrollbaren Inhalts-Frame liefern."""
        self._current_tab = name
        tab = self.tabs.add(name)
        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        return frame

    def _build_body(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=0)

        body = self._tab("Player")
        f = self._section(body, "Player")
        self._slider(f, "hp", "Max health", 50, 100000, 10, 100, fmt_int,
                     "Logarithmic slider: fine steps near vanilla 100, up to "
                     "100000 for god-mode runs (a user reports the game "
                     "accepts it). Medkits heal a fixed amount (basic medkit "
                     "70 HP), so at very high health raise 'Medkit & bandage "
                     "healing' too.", log=True)
        self._slider(f, "hp_regen", "Passive health regen (HP/s)", 0, 20, 0.5, 0, fmt_dec,
                     "Vanilla: no passive regen. NPCs use 1 HP/s.")
        self._slider(f, "sp", "Max stamina", 50, 1000, 10, 100, fmt_int)
        self._slider(f, "sp_regen", "Stamina regen (per second)", 0, 50, 1, 5, fmt_dec)
        self._slider(f, "fall", "Fall damage", 0, 100, 5, 100, fmt_pct,
                     "0 % = no fall damage.")
        self._slider(f, "walk", "Walk & crouch speed", 50, 150, 5, 100, fmt_pct)
        self._slider(f, "run", "Run & sprint speed", 50, 150, 5, 100, fmt_pct,
                     "Animations and footstep sounds can't scale with speed "
                     "(engine limitation) – subtle changes feel best.")
        self._warning(f, "Known issue since game patch 2.0 (20 Aug 2026): "
                         "players report that speed changes sometimes only "
                         "affect the animation instead of the actual movement. "
                         "Test in-game before settling on values. "
                         "(Status: 29 Aug 2026)")
        self._slider(f, "jump", "Jump height", 50, 200, 5, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Stamina costs (per action)")
        self._slider(f, "st_sprint", "Sprint (incl. continuous drain)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_jump", "Jump", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_melee_l", "Melee attack (light)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_melee_s", "Melee attack (strong)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_butt", "Rifle butt strike", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_vault", "Vault / climb", 0, 200, 5, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Vaulting")
        # Eigener Tab (Wunsch des Besitzers): 7 Regler + 2 Schalter sind zu
        # viel fuer den Player-Tab. Die Schluessel bleiben identisch ->
        # settings.json, Presets und Pak-Manifeste laufen unveraendert.
        f = self._section(body, "Vaulting & climbing")
        ctk.CTkLabel(
            f, text="   How Skif climbs and vaults over obstacles. All "
                    "values are detection limits in the game's units "
                    "(roughly centimeters - the vanilla max vault height of "
                    "130 is about 1.3 m). The sliders scale vanilla, or the "
                    "community preset when it is enabled - they stack. "
                    "Rebuilt from the vault mod that broke with game patch "
                    "2.0 (thanks to BigTinz on GitHub for the request and "
                    "the old values). Not play-tested in-game yet: whether "
                    "the vault animation keeps up with extreme values is "
                    "exactly what needs testing.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        self._slider(f, "vault_height", "Max vault height", 50, 250, 10, 100, fmt_pct,
                     "How high an obstacle you can still vault or climb over "
                     "(vanilla detection limit ~1.3 m). All vault sliders "
                     "stack on top of the preset below when both are used.")
        self._slider(f, "vault_distance", "Vault trigger distance", 100, 800, 50, 100, fmt_pct,
                     "From how far away vaulting triggers (vanilla is very "
                     "strict - the old vault mod used roughly 750 %).")
        self._slider(f, "vault_angle", "Vault approach angle", 100, 240, 10, 100, fmt_pct,
                     "How far off-center you may face an obstacle and still "
                     "vault it (capped at 180\u00b0).")
        self._slider(f, "vault_min_height", "Vault min obstacle height", 50, 200, 10, 100, fmt_pct,
                     "Below 100 % even small crates trigger vaulting; above, "
                     "only taller obstacles do.")
        self._slider(f, "vault_landing", "Vault landing tolerance", 100, 600, 25, 100, fmt_pct,
                     "How forgiving the landing check is: farther, steeper "
                     "and lower landing spots count (three game values "
                     "scaled together).")
        self._slider(f, "vault_over_depth", "Vault-over max thickness", 50, 300, 25, 100, fmt_pct,
                     "How deep/thick an obstacle may be and still be cleared "
                     "in one vault-over. The old vault mod HALVED this, "
                     "preferring quick climbs onto thick objects.")
        self._slider(f, "vault_over_offset", "Vault-over landing distance", 100, 500, 25, 100, fmt_pct,
                     "How far beyond the obstacle you land when vaulting "
                     "over it (the old mod used 500 % - clean jumps over "
                     "fences instead of stopping on them).")
        self._check(f, "improved_vaulting", "Improved vaulting (community preset)",
                    "Restores the tuned vaulting of the pre-2.0 vault mod "
                    "(broken since the game's 2.0 update): steeper approach "
                    "angles, vault from farther away, higher obstacles, more "
                    "generous landing. Player only - NPCs keep vanilla "
                    "vaulting. Not play-tested on 2.0.x yet.")
        self._check(f, "vault_sprint", "Start vaulting while sprinting (experimental)",
                    "Sets the game's StartWithSprintPressed flag. Its exact "
                    "in-game effect is NOT verified yet - it reads like "
                    "'vault can trigger while sprint is held'. Try it and "
                    "tell us.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Interaction reach")
        self._slider(f, "interact", "Interaction reach (pick up, loot, containers)", 50, 300, 10, 100, fmt_pct,
                     "How far away you can pick up items, open stashes and "
                     "containers and loot bodies (vanilla 2 m; bodies "
                     "0.65 m, scaled the same way). Not play-tested yet.")
        self._slider(f, "dialog_range", "Talk distance (NPC dialog)", 50, 300, 10, 100, fmt_pct,
                     "How close you have to be to start a conversation "
                     "(vanilla 1.3 m). The 'Social Distancing' idea from "
                     "Nexus. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Saving (quality of life)")
        self._slider(f, "save_manual", "Manual save slots", 10, 999, 1, 31, fmt_int,
                     "How many manual saves a campaign may hold before the "
                     "game makes you delete one (vanilla 31). The 'Unlimited "
                     "Saves' idea from Nexus. Not play-tested yet.")
        self._slider(f, "save_quick", "Quick save slots", 1, 30, 1, 3, fmt_int,
                     "How many quick saves are kept (vanilla 3).")
        self._slider(f, "save_auto", "Autosave slots", 1, 50, 1, 10, fmt_int,
                     "How many timed autosaves are kept (vanilla 10).")
        self._slider(f, "autosave_min", "Autosave interval", 1, 60, 1, 10, fmt_min,
                     "Minutes between timed autosaves (vanilla 10).")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Weight & items")
        f = self._section(body, "Weight & inventory")
        self._slider(f, "carry", "Max carry weight (hard limit)", 20, 500, 5, 80, fmt_kg)
        self._slider(f, "penalty", "Overweight penalty starts at", 10, 500, 5, 50, fmt_kg,
                     "Below this weight: no slowdown at all. Stages scale up to the hard limit.")
        self._check(f, "no_overweight", "No overweight penalty at all",
                    "Removes the speed/stamina penalties entirely (between penalty start and hard limit).")
        self._warning(f, "Known issue since game patch 2.0 (20 Aug 2026): "
                         "changed carry-weight limits can break walking "
                         "animations, especially combined with movement-speed "
                         "changes. Test in-game. (Status: 29 Aug 2026)")
        self._slider(f, "weight", "Item weight", 0, 200, 5, 100, fmt_pct,
                     "0 % = selected categories weigh nothing.")
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x", padx=24, pady=2)
        for i, cat in enumerate(sorted(ALL_CATEGORIES, key=lambda c: CATEGORY_LABELS[c])):
            box = ctk.CTkCheckBox(grid, text=CATEGORY_LABELS[cat])
            box.grid(row=i // 2, column=i % 2, sticky="w", padx=6, pady=2)
            box.select()
            self.cat_checks[cat] = box
        self._check(f, "ignore_equipped", "Equipped items are weightless",
                    "Worn armor and held weapons don't count toward inventory weight.")
        self._check(f, "quest_weightless", "Quest items weigh nothing",
                    "Sets the weight of every quest item to 0 (most of them "
                    "weigh something, up to 25 kg). Helps with "
                    "quest items that get stuck in the inventory.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Combat")
        f = self._section(body, "Combat")
        self._slider(f, "pdmg", "Player damage (guns)", 0.25, 10, 0.25, 1, fmt_factor,
                     "Applied via difficulty multipliers, all difficulty levels.")
        self._slider(f, "headshot", "Player headshot damage", 0.25, 5, 0.25, 1, fmt_factor)
        self._slider(f, "aimpunch", "Hit camera shake (aim punch)", 0, 300, 25, 100, fmt_pct,
                     "Camera kick when YOU get shot. 0 % = no flinch, "
                     "300 % = heavy aim punch.")
        self._slider(f, "expl", "Explosion damage", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "dur", "Weapon durability", 0.5, 10, 0.5, 1, fmt_factor,
                     "Weapons wear less per shot fired.")
        self._slider(f, "jam", "Weapon jamming", 0, 2, 0.1, 1, fmt_factor,
                     "× 0 = weapons never jam.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("NPCs & AI")
        f = self._section(body, "Human NPCs")
        self._slider(f, "npcdmg", "NPC damage (to you)", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "npchp", "NPC health", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "npc_acc", "NPC accuracy", 0.25, 3, 0.25, 1, fmt_factor,
                     "× 2 = NPCs shoot twice as precisely (smaller bullet spread).")
        self._slider(f, "npc_vision", "NPC vision range", 10, 200, 5, 100, fmt_pct,
                     "How far human NPCs (incl. the Faust fight) can see you. "
                     "Korshunov & Scar boss senses stay vanilla. "
                     "10 % vision + 10 % hearing ≈ ghost mode.")
        self._slider(f, "npc_hearing", "NPC hearing range", 10, 200, 5, 100, fmt_pct,
                     "Footsteps, shots, voices etc. Mutants are unaffected "
                     "(except Supersoldiers – they use NPC hearing).")
        self._slider(f, "npc_reaction", "NPC reaction delay", 25, 400, 25, 100, fmt_pct,
                     "How long NPCs take to report threats/enemies to their "
                     "squad (vanilla 2–3 s). 400 % = slow, sleepy AI; "
                     "25 % = instant alarm.")
        self._slider(f, "npc_grenades", "NPC grenade usage", 0, 300, 10, 100, fmt_pct,
                     "0 % = NPCs never throw grenades (scripted bosses keep theirs).")
        self._check(f, "npc_no_heal", "NPCs don't self-heal",
                    "Vanilla: NPCs passively regenerate health (guards up to 20 HP/s) "
                    "while the player regenerates none. Includes bosses.")
        self._slider(f, "npc_gear", "NPC gear quality", 25, 400, 25, 100, fmt_pct,
                     "Tilts each squad's weapon/armor lottery toward the "
                     "pricier gear it can ALREADY carry (400 % = the best "
                     "gun in a pool is 4x as likely, 25 % = rust buckets "
                     "everywhere). Never adds gear a faction or rank "
                     "wouldn't carry in vanilla - and their dropped loot "
                     "changes accordingly.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "NPC combat behaviour (experimental)")
        self._warning(f, "These are the hidden per-weapon AI profiles behind "
                         "'aimbot' complaints (same data the 'Grounded Combat' "
                         "and 'Better Gunfights' mods edit). Every NPC weapon "
                         "profile, rank and distance scales together. Not "
                         "play-tested yet.")
        self._slider(f, "npc_free_shots", "NPC guaranteed-hit shots", 0, 200, 10, 100, fmt_pct,
                     "Shots per burst that NPCs fire with ZERO spread - the "
                     "opening 'laser' fire (vanilla e.g. rifles 2-3 at long, "
                     "4-6 at short range). 0 % = every NPC shot uses normal "
                     "spread; shotguns and launchers already have 0.")
        self._slider(f, "npc_burst", "NPC burst length", 25, 300, 25, 100, fmt_pct,
                     "Shots per burst (vanilla e.g. rifles 3-6 at long, 8-16 "
                     "at short range).")
        self._slider(f, "npc_fire_pause", "NPC fire pauses", 25, 400, 25, 100, fmt_pct,
                     "Pause between bursts (vanilla ~0.8-2.5 s) and between "
                     "single shots of semi-auto weapons. 200 % = NPCs shoot "
                     "half as often.")
        self._slider(f, "npc_engage", "NPC engagement range", 25, 200, 5, 100, fmt_pct,
                     "Distance band in which NPCs open fire with a weapon "
                     "(vanilla e.g. pistols 2-25 m, rifles 15-60 m, snipers "
                     "25-100 m).")
        self._slider(f, "npc_range", "NPC weapon range", 25, 200, 5, 100, fmt_pct,
                     "Effective distance and damage drop-off of NPC weapon "
                     "profiles only - the NPC-side twin of 'Weapon effective "
                     "range'. Player weapons stay as they are.")
        self._slider(f, "npc_regen", "NPC health regen", 0, 300, 10, 100, fmt_pct,
                     "Passive regeneration of human NPCs (vanilla 1 HP/s, "
                     "guards 20 HP/s). 0 % = same as the 'don't self-heal' "
                     "box, which always wins when ticked.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Stealth: how NPCs notice you (experimental)")
        self._slider(f, "stealth_crouch", "Crouch stealth", 25, 400, 25, 100, fmt_pct,
                     "How much crouching and crawling hide you from eyes AND "
                     "ears (vanilla: crouched you are 25 % less visible and "
                     "much quieter). 200 % = twice as hard to notice while "
                     "crouched.")
        self._slider(f, "stealth_noise", "Movement noise", 0, 200, 10, 100, fmt_pct,
                     "Noise of walking, running and sprinting (vanilla 0.6 / "
                     "0.8 / 1.0). 0 % = silent feet; crouch noise has its "
                     "own slider above.")
        self._slider(f, "stealth_weather", "Bad-weather stealth", 0, 300, 25, 100, fmt_pct,
                     "How much fog, rain and thunder blind and deafen NPCs "
                     "(vanilla: fog -30 % sight / -60 % hearing, thunder "
                     "-20 % / -70 %). 0 % = weather changes nothing, 300 % = "
                     "storms make you nearly invisible.")
        self._slider(f, "stealth_flashlight", "Flashlight gives you away", 0, 200, 10, 100, fmt_pct,
                     "How strongly your own flashlight fills NPC vision "
                     "(cone 10 m / 15\u00b0 in vanilla). 0 % = the beam never "
                     "reveals you.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "NPC awareness & nerve (experimental)")
        self._slider(f, "npc_alertness", "NPC alertness", 25, 300, 25, 100, fmt_pct,
                     "How little suspicion it takes before NPCs turn their "
                     "head (200), search (350), move in (500) or call allies "
                     "(700 points; a gunshot is worth 700). 200 % = they react "
                     "at half the suspicion. Human NPCs only.")
        self._slider(f, "npc_search", "NPC search time", 25, 400, 25, 100, fmt_pct,
                     "How long NPCs stay suspicious and keep searching "
                     "(vanilla: suspicion frozen 30 s, then fades 30 points/s). "
                     "25 % = they forget you fast.")
        self._slider(f, "npc_courage", "NPC courage", 25, 300, 25, 100, fmt_pct,
                     "Confidence needed before human squads attack or fall "
                     "back (vanilla bandits 2 / 1, monolith 0.5 / 0, others "
                     "3 / 0.5). Higher = braver. Mutants stay vanilla.")
        self._slider(f, "npc_stagger", "NPC stagger threshold", 25, 400, 25, 100, fmt_pct,
                     "Damage within 2 s that makes a human NPC flinch (vanilla "
                     "40; bosses far higher). 25 % = they stagger from almost "
                     "any hit, 400 % = they barely flinch.")
        self._slider(f, "npc_attack_cd", "NPC attack cooldown", 25, 400, 25, 100, fmt_pct,
                     "Difficulty multiplier on human NPC attack cooldowns "
                     "(vanilla 1.0 on every difficulty). Effect scope not "
                     "verified in-game - experimental.")
        self._slider(f, "npc_rank_add", "NPC weapon rank bonus", 0, 3, 1, 0, fmt_int,
                     "Raises every NPC's weapon behaviour rank by this many "
                     "steps (Newbie -> Experienced -> Veteran -> Master): "
                     "deadlier enemies without health sponges. Difficulty "
                     "value, vanilla 0.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "NPC flashlights (experimental)")
        ctk.CTkLabel(
            f, text="   The one flashlight all 1,600 human NPCs carry. Your own "
                    "flashlight is not affected: its light values sit in the "
                    "game's Blueprint assets, out of reach for config patches.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11)).pack(fill="x", padx=12, pady=(2, 4))
        self._slider(f, "npc_light", "NPC flashlight brightness & reach", 25, 400, 25, 100, fmt_pct,
                     "Scales the intensity and the attenuation radius of NPC "
                     "flashlights (vanilla intensity 7-18 and radius "
                     "1.75-5 m, growing with the distance the beam travels). "
                     "Makes NPCs easier or harder to spot at night. Not "
                     "play-tested yet.")
        self._slider(f, "npc_light_cone", "NPC flashlight beam width", 50, 200, 10, 100, fmt_pct,
                     "Outer cone angle of NPC flashlights (vanilla 45-80 "
                     "degrees by distance, capped at 170). Not play-tested yet.")
        self._slider(f, "npc_light_combat", "NPC flashlight use in combat", 0, 200, 10, 100, fmt_pct,
                     "Chance that an NPC keeps the flashlight on while "
                     "fighting, by rank (vanilla newbie 100 %, experienced "
                     "75 %, veteran 50 %, master 25 %; capped at 100 %). "
                     "0 % = never. Not play-tested yet.")
        self._slider(f, "npc_light_on", "NPCs switch flashlights on at (hour)", 16, 23, 1, 22, fmt_int,
                     "In-game hour at which NPCs turn their flashlights on "
                     "(vanilla 22).")
        self._slider(f, "npc_light_off", "NPCs switch flashlights off at (hour)", 2, 10, 1, 5, fmt_int,
                     "In-game hour at which NPCs turn their flashlights off "
                     "(vanilla 5).")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "A-Life population (experimental)")
        self._warning(f, "Experimental: these change how the living world "
                         "spawns around you. Large values can hurt "
                         "performance or break quest pacing – change in "
                         "small steps and keep a backup save.")
        self._slider(f, "alife_agents", "Max simultaneous NPCs & mutants", 50, 200, 10, 100, fmt_pct,
                     "Vanilla: 52 A-Life agents around the player. "
                     "200 % = a much busier Zone (heavy CPU load!).")
        self._slider(f, "alife_distance", "A-Life spawn distance", 50, 200, 10, 100, fmt_pct,
                     "Vanilla: squads spawn ≥ 2500 m away. Lower = encounters "
                     "pop up closer to you; higher = quieter surroundings.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "A-Life spawns: lairs & random encounters (experimental)")
        self._warning(f, "Two systems feed the Zone: LAIRS (fixed places with a "
                         "population that respawns) and the DIRECTOR (random "
                         "encounters rolled around you). 'Max simultaneous NPCs "
                         "& mutants' above is only a cap on top of both – raise it "
                         "too. Existing saves re-roll lairs slowly (sleep or "
                         "change region). Not play-tested yet.")
        self._slider(f, "lair_mutants", "Lair population: mutants", 50, 300, 25, 100, fmt_pct,
                     "How many mutants a lair holds (all species, per player "
                     "rank). Story lairs and base guards are never touched.")
        self._slider(f, "lair_humans", "Lair population: humans", 50, 300, 25, 100, fmt_pct,
                     "How many stalkers a faction lair holds. Base guards "
                     "(Guard lairs) stay vanilla on purpose.")
        self._slider(f, "lair_respawn", "Lair respawn speed", 25, 400, 25, 100, fmt_pct,
                     "How fast fallen lair members are replaced (vanilla 3 / 8 "
                     "min, wipe 8 min). Story lairs with instant refill stay as "
                     "they are.")
        self._slider(f, "enc_freq", "Random encounters: frequency", 25, 400, 25, 100, fmt_pct,
                     "How often the director rolls a new encounter around you "
                     "(vanilla 60–90 s in the open world, plus a timeout after "
                     "each spawn – both scale).")
        self._slider(f, "enc_mutants", "Random encounters: mutant share", 0, 400, 25, 100, fmt_pct,
                     "Weight of pure-mutant encounters against human ones "
                     "(vanilla ~37 % of the open-world rolls). 0 % = no random "
                     "mutant packs (lair mutants stay). Weights the game never "
                     "uses (0) stay 0.")
        self._slider(f, "enc_pack", "Random encounters: pack size (experimental)", 50, 200, 10, 100, fmt_pct,
                     "Scales the per-rank cap of each spawnable type (blind "
                     "dogs 4–12, fleshes 2–6 ...) – our best reading of how pack "
                     "size is derived, unverified. Types the director never "
                     "spawns (chimera, controller, burer ...) are skipped.")
        for key, label, tip in (
                ("enc_blinddog", "Encounters: blind dogs", "Weight of blind-dog packs."),
                ("enc_boar", "Encounters: boars", "Weight of boar packs."),
                ("enc_flesh", "Encounters: fleshes", "Weight of flesh packs."),
                ("enc_tushkan", "Encounters: tushkans", "Weight of tushkan packs."),
                ("enc_chimera", "Encounters: chimeras",
                 "Weight of the single-chimera encounter (veteran regions only)."),
                ("enc_generic", "Encounters: mixed mutant packs",
                 "Weight of the generic 'mutants' encounters, which pick any "
                 "spawnable species.")):
            self._slider(f, key, label, 0, 400, 25, 100, fmt_pct,
                         tip + " Stacks with the mutant-share slider. Bloodsuckers "
                         "have no slider: the open world never rolls them (weight 0).")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Mutants")
        f = self._section(body, "All mutants (global)")
        self._slider(f, "mhp", "Mutant health (all species)", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "mdmg", "Mutant damage (all species)", 0.1, 5, 0.1, 1, fmt_factor,
                     "Via difficulty multiplier – species overrides below "
                     "scale the individual attack values on top.")
        self._slider(f, "mspeed", "Mutant speed (all species)", 0.25, 2, 0.25, 1, fmt_factor,
                     "Walk/run/sprint speed of every mutant species.")
        self._slider(f, "mhearing", "Mutant hearing range", 10, 200, 5, 100, fmt_pct,
                     "All mutant species share one hearing sensor. Mutants "
                     "have no config-side vision range – sight is engine "
                     "logic, so no slider is offered.")
        self._slider(f, "mut_regen", "Mutant health regen", 0, 4, 0.25, 1, fmt_factor,
                     "Mutants passively regenerate health, just like human "
                     "NPCs (vanilla varies by species). × 0 = wounds stay "
                     "– the mutant counterpart of 'NPCs don't self-heal'.")
        self._slider(f, "mut_attack_cd", "Mutant attack cooldown", 25, 400, 25, 100, fmt_pct,
                     "Difficulty multiplier on the pause between mutant "
                     "attacks (vanilla 1.0 on every difficulty). 200 % = "
                     "mutants attack half as often. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Bloodsucker cloaking")
        self._slider(f, "bs_cloak", "Bloodsucker cloaking speed", 0.25, 4, 0.25, 1, fmt_factor,
                     "× 4 = bloodsuckers vanish almost instantly.")
        self._slider(f, "bs_uncloak", "Bloodsucker uncloak from damage", 0, 20, 1, 1, fmt_factor,
                     "Higher = hitting them breaks the cloak much harder. "
                     "× 0 = damage never reveals them.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Per-species overrides (advanced)")
        ctk.CTkLabel(
            f, text="   ×1 (vanilla) = no override – the global sliders "
                    "above still apply to that species. Health and speed "
                    "scale the species' prototypes directly (incl. story "
                    "variants), damage scales each attack individually. "
                    "Species without a slider for something genuinely have "
                    "nothing to scale there (Poltergeist & rat swarms deal "
                    "damage indirectly).",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(
            fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a size group, then a species, to edit its "
                    "factors.",
            anchor="w", font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12, pady=(0, 2))
        self.im_info = ctk.CTkLabel(
            f, text="No per-species overrides set.", anchor="w",
            justify="left", wraplength=780, font=self._iw_font_hint,
            text_color="gray60")
        self.im_info.pack(fill="x", padx=12, pady=(2, 2))
        self.im_clear_btn = ctk.CTkButton(
            f, text="Clear all species overrides", width=200,
            command=self._im_clear_all)
        self.im_clear_btn.pack(anchor="w", padx=12, pady=(2, 6))
        # Container: wird EINMAL gepackt, nur sein Inhalt wird ausgetauscht.
        self.im_tree = ctk.CTkFrame(f, fg_color="transparent")
        self.im_tree.pack(fill="x", pady=(2, 2))
        self._im_build_tree()            # zeigt zunaechst nur den Platzhalter
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Factions")
        f = self._section(body, "Faction relations (living world)")
        self._warning(
            f, "Experimental & not play-tested on existing saves yet: the "
               "game copies relations into your save when a playthrough "
               "starts. This tool also raises the game's internal "
               "RelationVersion so existing saves should pick the new "
               "values up – unverified until in-game testing. Quests and "
               "scripted story characters can still override relations at "
               "any time (that is by design), and local hostility slowly "
               "rolls back on its own. Keep a backup save.")
        ctk.CTkLabel(
            f, text="   Baseline stance between factions, on the game's own "
                    "scale: −800 or lower = enemy (kill on sight), −799 to "
                    "−201 = wary (the game calls it 'Disaffection' – talking "
                    "and trading still work), −200 to 200 = neutral, 201 and "
                    "up = friend. Vanilla uses values like −599 on purpose – "
                    "just past a threshold. Story, boss and arena factions "
                    "are deliberately not listed.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(
            fill="x", padx=12)
        # Mod-Scan-Hinweis (Pseudo-Schluessel "tree:factions"): der Baum hat
        # keine Regler-Punkte, dafuer diese eine ehrliche Zeile.
        self.if_conflict_label = ctk.CTkLabel(
            f, text="", anchor="w", justify="left", wraplength=780,
            font=self._iw_font_hint, text_color=MARK_INFO)
        self.if_info = ctk.CTkLabel(
            f, text="No relations changed.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color="gray60")
        self.if_info.pack(fill="x", padx=12, pady=(2, 2))
        self.if_clear_btn = ctk.CTkButton(
            f, text="Reset all relations to vanilla", width=220,
            command=self._if_clear_all)
        self.if_clear_btn.pack(anchor="w", padx=12, pady=(2, 6))
        # Container: wird EINMAL gepackt, nur sein Inhalt wird ausgetauscht.
        self.if_tree = ctk.CTkFrame(f, fg_color="transparent")
        self.if_tree.pack(fill="x", pady=(2, 2))
        self._if_build_tree()            # zeigt zunaechst nur den Platzhalter
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Reputation mechanics")
        self._slider(f, "rel_rollback", "Reputation rollback time", 25, 400, 25, 100, fmt_pct,
                     "How long the game remembers LOCAL hostility before "
                     "forgiving it (vanilla 60 min in the field, faster in "
                     "hubs). 400 % = grudges last four times longer; "
                     "25 % = quick forgiveness. Permanent faction-wide "
                     "reputation is a separate system and is not affected.")
        self._slider(f, "rel_reaction", "Reputation reaction strength", 25, 400, 25, 100, fmt_pct,
                     "How hard kills, heals and assaults move reputation - "
                     "scales both the local squad reaction and the "
                     "permanent faction-wide part. 400 % = every action "
                     "matters four times as much; 25 % = an almost "
                     "indifferent Zone.")
        self._slider(f, "rel_trade", "Trading requires standing", 0, 3, 1, 1, fmt_trade_level,
                     "Vanilla: traders deal with you from 'Disaffected' "
                     "(wary) upward. 'Neutral' or 'Friend' = hardcore "
                     "reputation play; 'Enemy' = everyone trades with "
                     "anyone.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Weapons")
        f = self._section(body, "Weapon handling (global – all weapons)")
        self._slider(f, "sway", "Scoped aim sway", 0, 100, 5, 100, fmt_pct,
                     "0 % = steady scopes. Iron-sight sway is animation-driven and not cfg-tweakable.")
        self._slider(f, "breath_drain", "Breath-hold drain", 0, 200, 5, 100, fmt_pct,
                     "0 % = hold breath forever while aiming.")
        self._slider(f, "breath_regen", "Breath recovery", 50, 400, 10, 100, fmt_pct)
        self._slider(f, "spread", "Weapon spread (bullet dispersion)", 0, 200, 5, 100, fmt_pct,
                     "0 % = laser accuracy (hip fire, aiming and first shot).")
        self._slider(f, "recoil", "Weapon recoil", 0, 200, 5, 100, fmt_pct,
                     "Scales the kick per shot (RecoilRadius). 0 % = no kick. "
                     "The per-shot pattern shape is a game asset and keeps "
                     "its direction, only its size follows the slider. Not "
                     "play-tested yet - report back.")
        self._slider(f, "recoil_upgrades", "Recoil reduction from upgrades", 100, 2000, 100, 100, fmt_pct,
                     "Multiplies the recoil reduction of weapon upgrades and "
                     "attachments (vanilla -5 % to -30 %), capped at -100 %. "
                     "2000 % = any recoil upgrade removes the kick entirely. "
                     "Only weapons with such an upgrade installed change. "
                     "Community-proven on patch 2.0 (same route as the "
                     "'Dead Steady' mod).")
        self._slider(f, "wrange", "Weapon effective range", 50, 200, 10, 100, fmt_pct,
                     "Scales effective fire distance and damage drop-off "
                     "start/length together.")
        self._slider(f, "wbleed", "Weapon bleeding", 0, 300, 25, 100, fmt_pct,
                     "Bleeding chance and intensity your shots inflict. "
                     "0 % = your bullets never cause bleeding.")
        self._slider(f, "adsmove", "ADS movement speed", 50, 200, 10, 100, fmt_pct,
                     "How fast you move while aiming down sights "
                     "(vanilla varies 58–150 % of run speed per weapon).")
        self._slider(f, "aimspeed", "ADS aim-in speed", 25, 400, 25, 100, fmt_pct,
                     "How fast the weapon comes up into the sights, incl. "
                     "offset and lean aiming (vanilla ~0.5 s). 200 % = "
                     "twice as snappy. Not play-tested yet – watch for "
                     "aim animation glitches and report back.")
        self._slider(f, "magazine", "Magazine size", 50, 300, 25, 100, fmt_pct,
                     "Scales weapon base capacity AND all magazine "
                     "attachments (launchers never drop below 1 round). "
                     "Per category or per weapon: 'Magazine size' is the "
                     "tenth factor in the trees below.")
        self._slider(f, "melee", "Melee damage (knife & butt strike)", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "melee_range", "Melee range (knife & butt strike)", 50, 300, 25, 100, fmt_pct,
                     "How far the knife and the butt strike reach (vanilla "
                     "1.6 m for both). The 'Increased Melee Range' idea from "
                     "Nexus. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Weapon categories")
        ctk.CTkLabel(
            f, text="   Factors for every weapon of a category. ×1 (vanilla) "
                    "falls back to the global sliders above; single-weapon "
                    "overrides below beat both. Damage stacks with the global "
                    "'Player damage' slider in Combat. Spread, recoil and "
                    "fire rate live in shared game data – NPCs using these "
                    "weapons are affected too.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        self._warning(f, "Known issue since game patch 2.0 (20 Aug 2026): a Nexus "
                         "user reports the fire-rate factor desyncs the firing "
                         "animation and sound from the actual shots \u2013 same "
                         "engine limitation as movement speed. Test in-game "
                         "before settling on values. (Status: 01 Sep 2026)")
        for cat, cat_label in WEAPON_CATEGORY_LABELS.items():
            self._collapsible_category(f, cat, cat_label)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single weapon overrides (advanced)")
        ctk.CTkLabel(
            f, text="   ×1 (vanilla) = no override – the category/global "
                    "factors still apply to this weapon.",
            anchor="w", font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a category, then a weapon, to edit its factors.",
            anchor="w", font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12, pady=(0, 2))
        # Uebersicht und "alles loeschen" stehen UEBER dem Baum: der kann auf
        # 79 Zeilen anwachsen, darunter waeren beide nur mit Scrollen erreichbar.
        self.iw_info = ctk.CTkLabel(
            f, text="No per-weapon overrides set.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color="gray60")
        self.iw_info.pack(fill="x", padx=12, pady=(2, 2))
        self.iw_clear_btn = ctk.CTkButton(
            f, text="Clear all weapon overrides", width=200,
            command=self._iw_clear_all)
        self.iw_clear_btn.pack(anchor="w", padx=12, pady=(2, 6))
        # Container fuer den Baum: wird EINMAL gepackt und nie neu gepackt,
        # nur sein Inhalt wird bei _iw_build_tree() ausgetauscht.
        self.iw_tree = ctk.CTkFrame(f, fg_color="transparent")
        self.iw_tree.pack(fill="x", pady=(2, 2))
        self._iw_build_tree()            # zeigt zunaechst nur den Platzhalter
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Ammo")
        # Die 4 globalen Regler standen frueher im Weapons-Tab. Sie MUESSEN
        # nach _tab("Ammo") entstehen: _slider() stempelt den aktuellen
        # Tab-Namen in slider_tabs, sonst nennt die Suche den falschen Tab.
        f = self._section(body, "Ammo (all calibers)")
        ctk.CTkLabel(
            f, text="   Scales each ammo type's own modifiers, so special "
                    "ammo keeps its character: AP stays the armor king, "
                    "buckshot stays bad at it – just more or less extreme.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        self._slider(f, "ammo_dmg", "Ammo damage", 25, 300, 25, 100, fmt_pct)
        self._slider(f, "ammo_ap", "Ammo armor piercing", 0, 300, 25, 100, fmt_pct)
        self._slider(f, "ammo_ad", "Ammo armor damage", 25, 300, 25, 100, fmt_pct)
        self._slider(f, "ammo_cover", "Ammo cover penetration", 0, 300, 25, 100, fmt_pct,
                     "How well bullets punch through wooden walls, fences etc.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single ammo overrides (advanced)")
        ctk.CTkLabel(
            f, text="   ×1 (vanilla) = no override – the global ammo slider "
                    "above applies to this round. Any other value REPLACES "
                    "the global slider for that factor on this round – the "
                    "two do not stack.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a caliber, then a round, to edit its factors.",
            anchor="w", font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12, pady=(0, 2))
        self.ia_info = ctk.CTkLabel(
            f, text="No per-ammo overrides set.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color="gray60")
        self.ia_info.pack(fill="x", padx=12, pady=(2, 2))
        self.ia_clear_btn = ctk.CTkButton(
            f, text="Clear all ammo overrides", width=200,
            command=self._ia_clear_all)
        self.ia_clear_btn.pack(anchor="w", padx=12, pady=(2, 6))
        # Container: wird EINMAL gepackt, nur sein Inhalt wird ausgetauscht.
        self.ia_tree = ctk.CTkFrame(f, fg_color="transparent")
        self.ia_tree.pack(fill="x", pady=(2, 2))
        self._ia_build_tree()            # zeigt zunaechst nur den Platzhalter
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Armor")
        # Die globalen Schutz-Regler standen frueher im Combat-Tab. Sie
        # MUESSEN nach _tab("Armor") entstehen: _slider() stempelt den
        # aktuellen Tab-Namen in slider_tabs (Suche nennt sonst den falschen
        # Tab). Die Schluessel bleiben gleich -> settings.json und Presets
        # laufen unveraendert weiter.
        f = self._section(body, "Armor protection (all armor & helmets)")
        ctk.CTkLabel(
            f, text="   Scales YOUR armor's protection values per damage "
                    "type. NPC armor is untouched (use 'NPC health' for "
                    "that). Upgrade bonuses stay vanilla.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        self._slider(f, "ap_strike", "Physical (bullets & melee)", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "ap_burn", "Burn (fire)", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "ap_shock", "Shock (electric)", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "ap_chem", "Chemical", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "ap_rad", "Radiation", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "ap_psy", "PSY", 25, 400, 25, 100, fmt_pct)
        self._slider(f, "dur_armor", "Armor durability", 0.5, 10, 0.5, 1, fmt_factor,
                     "Armor takes more punishment before breaking.")
        self._slider(f, "ap_carry", "Armor carry-weight bonuses", 0, 300, 25, 100, fmt_pct,
                     "Exoskeleton & armor/upgrade carry bonuses. "
                     "0 % = armor grants no extra carry weight.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single armor overrides (advanced)")
        ctk.CTkLabel(
            f, text="   \u00d71 (vanilla) = no override \u2013 the global sliders "
                    "above apply to this armor. Any other value REPLACES the "
                    "global slider for that protection type on this piece "
                    "\u2013 the two do not stack. Durability and carry bonuses "
                    "stay global: they work through different game systems.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a group, then an armor piece, to edit its "
                    "protection factors.",
            anchor="w", font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12, pady=(0, 2))
        self.ir_info = ctk.CTkLabel(
            f, text="No per-armor overrides set.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color="gray60")
        self.ir_info.pack(fill="x", padx=12, pady=(2, 2))
        self.ir_clear_btn = ctk.CTkButton(
            f, text="Clear all armor overrides", width=200,
            command=self._ir_clear_all)
        self.ir_clear_btn.pack(anchor="w", padx=12, pady=(2, 6))
        # Container: wird EINMAL gepackt, nur sein Inhalt wird ausgetauscht.
        self.ir_tree = ctk.CTkFrame(f, fg_color="transparent")
        self.ir_tree.pack(fill="x", pady=(2, 2))
        self._ir_build_tree()            # zeigt zunaechst nur den Platzhalter
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("World")
        f = self._section(body, "World & survival")
        self._slider(f, "anomaly", "Anomaly damage (all types)", 0.1, 5, 0.1, 1, fmt_factor,
                     "Global difficulty multiplier – stacks with the "
                     "per-type sliders below.")
        self._slider(f, "anom_electro", "Anomaly damage: electro", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "anom_chem", "Anomaly damage: chemical", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "anom_fire", "Anomaly damage: fire", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "anom_grav", "Anomaly damage: gravity", 0.1, 5, 0.1, 1, fmt_factor,
                     "Carousel, Razor, Expulsion, Diamond … "
                     "(PSY anomalies drain psy, not health – no slider).")
        self._slider(f, "radiation", "Radiation accumulation", 0, 5, 0.25, 1, fmt_factor,
                     "× 0 = no radiation buildup.")
        self._slider(f, "bleeding", "Bleeding intensity", 0, 5, 0.25, 1, fmt_factor)
        self._slider(f, "hunger", "Hunger rate", 0, 300, 10, 100, fmt_pct,
                     "0 % = never get hungry.")
        self._slider(f, "sleep", "Sleepiness rate", 0, 300, 10, 100, fmt_pct,
                     "0 % = never get sleepy.")
        self._slider(f, "consumable", "Consumable strength", 25, 300, 25, 100, fmt_pct,
                     "Medkits, bandages, food, drinks: healing, bleeding/"
                     "radiation removal, stamina etc. Penalties (drunkness, "
                     "spoiled food) stay vanilla.")
        self._slider(f, "healing", "Medkit & bandage healing", 25, 400, 25, 100, fmt_pct,
                     "Health restored by medical items only (medkits and "
                     "bandages, vanilla 20\u2013100 HP) \u2013 food and drink healing "
                     "is not affected. Stacks with Consumable strength: "
                     "both at 200 % = 4\u00d7 healing.")
        self._slider(f, "cons_duration", "Consumable effect duration", 25, 400, 25, 100, fmt_pct,
                     "How long running consumable effects last (energy "
                     "drink 45 s, Hercules 5 min, cinnamon, vodka/psy-block "
                     "...). Instant effects (healing, bleeding stop, "
                     "anti-rad, 1-2 s) are untouched on purpose.")
        self._slider(f, "rain", "Rain & storm frequency", 0, 300, 25, 100, fmt_pct,
                     "Weight of rainy/stormy/thunder weather in the rotation. "
                     "0 % = practically always dry.")
        self._slider(f, "emission", "Emission frequency", 25, 400, 25, 100, fmt_pct,
                     "How often emissions build up (quest-controlled "
                     "no-emission zones stay untouched).")
        self._slider(f, "emission_dur", "Emission duration", 25, 400, 25, 100, fmt_pct,
                     "Stretches the whole emission timeline together - "
                     "warning siren, shockwave, deadly phase and aftermath "
                     "(vanilla ~1 min warning + ~1 min active). Story "
                     "emissions keep their scripted timing.")
        self._slider(f, "day_length", "Day length", 25, 400, 25, 100, fmt_pct,
                     "How long a full day-night cycle takes in real time "
                     "(vanilla: one game day per real hour). 200 % = two "
                     "hours per day, the day/night ratio stays vanilla.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Loot in stashes & on bodies")
        ctk.CTkLabel(
            f, text="   Covers the game's smart-loot lists: ammo, medicine, "
                    "food and grenades in hidden stashes and on NPC bodies. "
                    "Weapons, armor and artifacts come from a different "
                    "system and are NOT affected by these sliders. Note that "
                    "vanilla only puts smart loot on bodies on Easy and "
                    "Medium difficulty – on Hard and Stalker there is nothing "
                    "to scale on bodies, only in stashes.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        self._slider(f, "stash_loot", "Stash & body loot amount", 25, 400, 25, 100, fmt_pct,
                     "How many items a stash or body yields (whole numbers, "
                     "never below 1).")
        self._slider(f, "stash_chance", "Stash & body find chance", 25, 400, 25, 100, fmt_pct,
                     "Chance that a slot yields anything at all. Capped at "
                     "100 %, so raising it helps less than the number suggests "
                     "– many slots already sit close to the cap. Lowering it "
                     "works in full.")
        self._slider(f, "stash_ammo", "Stash & body ammo bonus", 25, 400, 25, 100, fmt_pct,
                     "Extra rounds handed out to match the weapon caliber, on "
                     "top of the item list above.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Loot amount (NPCs, containers, world)")
        ctk.CTkLabel(
            f, text="   The game's other, much larger loot system: the item "
                    "generators behind dead stalkers and mutants and behind "
                    "the stashes scattered around the Zone. The slider changes "
                    "HOW MANY of an item a slot yields – not how often you "
                    "find something, and not which items show up. Amounts are "
                    "whole numbers and never drop below 1, so a slot that "
                    "yields a single item stays at 1 until you reach 150 %. "
                    "Coupons are never scaled: neither a generator's money "
                    "block nor the money cards lying in stashes. Quest, "
                    "story-reward, unique-weapon and trader-stock generators "
                    "are skipped, and so are quest marker items sitting in "
                    "otherwise normal loot – so scripted items are left alone, "
                    "and a named trader's stock stays vanilla.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)
        self._slider(f, "loot_amount", "Loot amount (NPCs, containers, world)",
                     25, 400, 25, 100, fmt_pct,
                     "Only ammo and part of the food & medicine lists come as "
                     "real stacks and scale smoothly. Almost everything else "
                     "(detectors, grenades, artifacts, weapons, armor, mutant "
                     "parts) is one item per slot: unchanged below 150 %, "
                     "then 2 from 150 %, 3 from 275 % and so on.")
        self._slider(f, "drop_cond", "Dropped weapon condition", 10, 100, 2.5, 37.5, fmt_pct,
                     "AVERAGE condition of weapons found on bodies and in "
                     "the world (vanilla ~37.5 % for primary weapons). The "
                     "game keeps rolling randomly around it, exactly like "
                     "vanilla – at 80 % most drops land between ~67 and "
                     "~93 %. Armor, helmets, artifacts and trader stock "
                     "stay vanilla.")
        self._check(f, "drop_cond_exact", "Exact condition (no random spread)",
                    "Every dropped weapon spawns at exactly the value above "
                    "(or at its own vanilla average if the slider is "
                    "untouched).")
        self._warning(
            f, "This is by far the largest patch this tool can build "
               "(around 25,000 lines). If the game starts noticeably slower "
               "afterwards, put this slider back to 100 %.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Artifacts")
        self._slider(f, "art_effect", "Artifact effect strength", 25, 300, 25, 100, fmt_pct,
                     "Scales what artifacts do on your belt – positive effects "
                     "AND side effects alike (radiation has its own slider below).")
        self._slider(f, "art_radiation", "Artifact radiation side-effect", 0, 200, 10, 100, fmt_pct,
                     "0 % = artifacts emit no radiation at all.")
        self._slider(f, "art_spawn", "Artifact spawn chance", 25, 400, 25, 100, fmt_pct,
                     "Chance that anomaly fields spawn an artifact "
                     "(vanilla 25–40 %, capped at 100 %).")
        self._slider(f, "art_rarity", "Rare artifact bias", 25, 500, 25, 100, fmt_pct,
                     "Shifts the rarity roll toward Uncommon/Rare/Epic at "
                     "Common's expense. Ranks that can't roll Rare/Epic in "
                     "vanilla (e.g. Newbie) still won't.")
        self._slider(f, "art_count", "Artifacts per anomaly field", 1, 5, 1, 1, fmt_factor,
                     "How many artifacts a field hands out per spawn "
                     "(vanilla 1). Which artifacts a field CAN spawn stays "
                     "its vanilla list.")
        self._slider(f, "art_respawn", "Artifact respawn speed", 25, 400, 25, 100, fmt_pct,
                     "How fast fields cool down before the next artifact "
                     "(vanilla mostly 3-15, some 60-120). Fields with no "
                     "cooldown stay as they are.")
        self._slider(f, "detector", "Detector & scanner range", 50, 300, 10, 100, fmt_pct,
                     "Artifact detectors (Echo, Bear, Veles, Gilka), the "
                     "anomaly beeper and the searchpoint scanner.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Economy")
        f = self._section(body, "Economy & traders")
        self._slider(f, "buyprice", "Trader buy prices (what you get)", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "sellprice", "Trader sell prices (what you pay)", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "repair", "Repair cost", 0, 200, 5, 100, fmt_pct,
                     "0 % = free repairs.")
        self._slider(f, "upgrade", "Upgrade cost", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "questreward", "Quest money rewards", 0.25, 10, 0.25, 1, fmt_factor)
        self._slider(f, "rq_cooldown", "Repeatable quest cooldown", 0, 400, 25, 100, fmt_pct,
                     "Wait time until task givers offer new repeatable "
                     "jobs (vanilla 24 in-game hours). 0 % = new jobs "
                     "right away. A cooldown already ticking in your "
                     "save finishes at its old pace first.")
        self._slider(f, "fasttravel", "Fast travel cost", 0, 400, 25, 100, fmt_pct,
                     "0 % = guides take you anywhere for free.")
        self._slider(f, "price_weapon", "Weapon prices", 0.25, 4, 0.25, 1, fmt_factor,
                     "Per-category price multipliers – these stack with the "
                     "trader buy/sell sliders above.")
        self._slider(f, "price_armor", "Armor prices", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "price_ammo", "Ammo prices", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "price_artifact", "Artifact prices", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "price_consumable", "Consumable prices", 0.25, 4, 0.25, 1, fmt_factor)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Technician upgrades (weapons & armor)")
        self._check(f, "upgrades_take_both", "Take both of mutually exclusive upgrades",
                    "Upgrade branches that normally exclude each other (barrel A "
                    "or barrel B ...) can all be installed. Same idea as the "
                    "'Take Both Upgrades' Nexus mod. Not play-tested yet.")
        self._check(f, "upgrades_no_blueprint", "Upgrades need no blueprint",
                    "Upgrades that normally need a blueprint item become "
                    "available without it. Technicians still only service the "
                    "gear they are scripted for. Both boxes above = "
                    "'Unrestricted Upgrades'.")
        self._check(f, "upgrades_no_tiers", "No upgrade tiers (skip earlier tiers)",
                    "Tier 2/3 upgrades no longer require the earlier tier "
                    "first. All three boxes = 'Unrestricted Upgrades - "
                    "NoTiers'. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Traders")
        f = self._section(body, "Stock (what traders have on the shelf)")
        self._slider(f, "trader_stock", "Trader stock amount", 25, 400, 25, 100, fmt_pct,
                     "Scales the quantities on offer (ammo boxes, medkit "
                     "stacks ...). Weapons and armor are single items – "
                     "they only multiply from 150 % up, like loot.")
        self._slider(f, "trader_variety", "Trader stock variety", 25, 400, 25, 100, fmt_pct,
                     "Each catalog item has a chance to be in stock after a "
                     "restock. Higher = fuller shelves (chance is capped at "
                     "100 %), lower = patchier stock. What a trader CAN "
                     "carry stays their vanilla catalog – honest limit: "
                     "this tool does not add new items to traders.")
        self._slider(f, "restock", "Trader restock time", 25, 400, 25, 100, fmt_pct,
                     "How long traders take to refresh their stock "
                     "(vanilla: 8 h to 7 days depending on the trader; "
                     "day-based traders can't go below 1 day).")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Wallet & buying")
        self._slider(f, "trader_money", "Trader money", 0.25, 10, 0.25, 1, fmt_factor,
                     "Scales the coupon wallet traders pay you from. "
                     "Honest note: most traders (59 of 73) already have "
                     "unlimited money in vanilla – this affects the "
                     "finite wallets (bartenders etc.).")
        self._check(f, "trader_inf_money", "All traders have unlimited money",
                    "Switches the remaining finite wallets to unlimited "
                    "(most are already unlimited in vanilla).")
        self._slider(f, "trader_dur", "Traders buy gear from durability", 0, 100, 5, 40, fmt_pct,
                     "0 % = traders buy weapons/armor in any condition (vanilla: 40 %).")
        ctk.CTkLabel(f, text="", height=2).pack()

    def _build_footer(self):
        foot = ctk.CTkFrame(self)
        foot.pack(fill="x", padx=10, pady=(4, 10))

        row1 = ctk.CTkFrame(foot, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(row1, text="Mod name:").pack(side="left", padx=(4, 6))
        self.name_entry = ctk.CTkEntry(row1, width=180)
        self.name_entry.insert(0, "S2Tweaker")
        self.name_entry.pack(side="left")
        self.debug_check = ctk.CTkCheckBox(
            row1, text="Debug: also export patch .cfg files")
        self.debug_check.pack(side="left", padx=14)
        ctk.CTkButton(row1, text="Reset all to vanilla ↺", width=150,
                      command=self._reset_all).pack(side="right", padx=4)
        ctk.CTkButton(row1, text="Load preset …", width=110,
                      command=self._load_preset).pack(side="right", padx=4)
        ctk.CTkButton(row1, text="Save preset …", width=110,
                      command=self._save_preset).pack(side="right", padx=4)

        row2 = ctk.CTkFrame(foot, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(2, 4))
        self.btn_build = ctk.CTkButton(
            row2, text="Build pak  →  output folder", height=36,
            font=ctk.CTkFont(size=14, weight="bold"), command=self._generate_output)
        self.btn_build.pack(side="left", fill="x", expand=True, padx=4)
        self.btn_install = ctk.CTkButton(row2, text="Install to ~mods", width=130,
                                         command=self._generate_install)
        self.btn_install.pack(side="left", padx=4)
        self.btn_open = ctk.CTkButton(row2, text="Open output", width=100,
                                      command=self._open_output)
        self.btn_open.pack(side="left", padx=4)
        # In row2 statt row1: row1 ist mit Mod-Name + Debug + 3 Preset-
        # Knoepfen schon voll — dort wuerde der Scan-Knopf beim
        # 880-px-Minimum als erstes abgeschnitten. row2 hat den breiten
        # Build-Knopf als Puffer (expand=True schrumpft zuerst).
        self.btn_scan = ctk.CTkButton(row2, text="Scan ~mods", width=110,
                                      state="disabled",
                                      command=self._start_modscan)
        self.btn_scan.pack(side="left", padx=4)
        self.btn_remove = ctk.CTkButton(row2, text="Remove from ~mods", width=150,
                                        fg_color="#7a2d2d", hover_color="#8f3838",
                                        command=self._remove_mod)
        self.btn_remove.pack(side="left", padx=4)

        self.status = ctk.CTkLabel(foot, text="Starting ...", anchor="w",
                                   text_color="gray70")
        self.status.pack(fill="x", padx=12, pady=(0, 2))
        ctk.CTkLabel(
            foot,
            text="ℹ Only values you change are written to the pak. Sliders at "
                 "(vanilla) are left untouched, so other mods keep working.",
            anchor="w", font=ctk.CTkFont(size=11), text_color="gray55",
        ).pack(fill="x", padx=12, pady=(0, 8))
        self._set_busy(True)

    # ------------------------------------------------------------ startup
    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for b in (self.btn_build, self.btn_install, self.btn_remove):
            b.configure(state=state)

    def _set_body_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._iw_state = state   # gilt auch fuer spaeter gebaute Zeilen/Regler
        self._ia_state = state   # dito fuer den Ammo-Baum
        for row in self.sliders.values():
            row.set_state(state)
        for key, box in self.checks.items():
            locked = key in self._locked_checks
            box.configure(state="disabled" if locked else state)
        for box in self.cat_checks.values():
            box.configure(state=state)
        self.iw_clear_btn.configure(state=state)
        for block in self._iw_blocks.values():
            block.set_state(state)
        self.ia_clear_btn.configure(state=state)
        for block in self._ia_blocks.values():
            block.set_state(state)
        self._ir_state = state   # dito fuer den Armor-Baum
        self.ir_clear_btn.configure(state=state)
        for block in self._ir_blocks.values():
            block.set_state(state)
        self._if_state = state   # dito fuer den Fraktions-Baum
        self.if_clear_btn.configure(state=state)
        for block in self._if_blocks.values():
            block.set_state(state)
        self._im_state = state   # dito fuer den Mutanten-Baum
        self.im_clear_btn.configure(state=state)
        for block in self._im_blocks.values():
            block.set_state(state)

    def _set_status(self, text: str):
        self._msgs.put(("status", text))

    def _status_write(self, text: str):
        """Statuszeile schreiben UND den Merkwert der Suche verwerfen.

        Das Suchfeld legt die vorherige Meldung beiseite und stellt sie beim
        Leeren wieder her. Ohne dieses Verwerfen kaeme bei aktiver Suche eine
        laengst ueberholte Meldung zurueck ("… load game data" nach dem
        Laden, statt "Built: …").
        """
        self._status_before_search = None
        self.status.configure(text=text)

    def _poll_msgs(self):
        """Nachrichten des Hintergrund-Threads im GUI-Thread verarbeiten."""
        try:
            while True:
                kind, payload = self._msgs.get_nowait()
                if kind == "status":
                    self._status_write(payload)
                elif kind == "game_label":
                    self.game_label.configure(text=payload)
                elif kind == "ready":
                    self._refresh_oodle_badge()
                    self._iw_populate()
                    self._ia_populate()
                    self._ir_populate()
                    self._if_populate()
                    self._im_populate()
                    self._set_busy(False)
                    self._set_body_state(True)
                    # Laufende Suche auf den frisch gebauten Baum anwenden
                    self._apply_filter()
                    self.btn_confirm.configure(state="normal",
                                               text="↻ Reload game data")
                    self.btn_browse.configure(state="normal")
                    # Nach einem (Neu-)Laden sind alte Fussabdruecke wertlos:
                    # sie wurden gegen die vorherigen Spieldaten gerechnet.
                    self._footprints.clear()
                    self.btn_scan.configure(state="normal")
                    self.after(400, self._maybe_offer_modscan)
                elif kind == "modscan_done":
                    self._finish_modscan()
                elif kind == "loadfail":
                    self.btn_confirm.configure(state="normal")
                    self.btn_browse.configure(state="normal")
                    if self.gd is not None:      # alte Daten weiter nutzbar
                        self.btn_scan.configure(state="normal")
                elif kind == "oodle":
                    self._open_oodle_wizard()
                elif kind == "error":
                    messagebox.showerror(APP_TITLE, payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_msgs)

    def _prefill_game(self):
        """Beim Start: Spielordner nur VORSCHLAGEN, nichts laden."""
        def detect():
            if self.game_dir is None or not game.is_game_dir(self.game_dir):
                self.game_dir = game.find_game()
            if self.game_dir is not None:
                self._msgs.put(("game_label", f"Game folder: {self.game_dir}"))
                self._set_status(
                    "Check the game folder above, then click "
                    "'Confirm & load game data'.")
            else:
                self._msgs.put(("game_label", "Game folder: not found"))
                self._set_status(
                    "Game not found – click 'Browse …' and select your "
                    "S.T.A.L.K.E.R. 2 folder, then confirm.")
        threading.Thread(target=detect, daemon=True).start()

    def _confirm_game(self):
        if self.game_dir is None or not game.is_game_dir(self.game_dir):
            messagebox.showwarning(
                APP_TITLE,
                "Please select your game folder first (Browse …).\n"
                "Expected: the folder containing Stalker2\\Content\\Paks.")
            return
        self.btn_confirm.configure(state="disabled")
        self.btn_browse.configure(state="disabled")
        self.btn_scan.configure(state="disabled")
        self._set_busy(True)
        self._set_body_state(False)
        threading.Thread(target=self._load_gamedata, daemon=True).start()

    def _load_gamedata(self):
        try:
            # Entwicklungsmodus: vanilla/-Ordner im Projektverzeichnis
            dev = Path(__file__).resolve().parent.parent / "vanilla" / \
                "Stalker2" / "Content" / "GameLite" / "GameData"
            if dev.is_dir():
                self._set_status("Loading vanilla data (dev folder) ...")
                gd = GameData(dev)
            else:
                self._set_status(
                    "First start: extracting game data (takes a moment) ...")
                gd = GameData.from_game(self.game_dir, cache_root=cache_dir(),
                                        progress=self._set_status)

            self._set_status("Analyzing game data ...")
            n_mut = len(gd.mutants())
            n_items = len(gd.item_weights())
            n_weap = len(gd.player_weapon_wear())
            self.gd = gd
            self._set_status(
                f"Ready. Analyzed your game version: {n_items} items, "
                f"{n_weap} weapons, {n_mut} mutant prototypes. "
                + (gd.dlc_summary()
                   or "No edition (DLC) content in this install."))
            self._msgs.put(("ready", ""))
        except pakio.OodleError:
            # Der Assistent erklaert es Schritt fuer Schritt mit Bildern —
            # besser als eine Textwand im Fehlerdialog.
            self._set_status("Missing Oodle library – see the setup window.")
            self._msgs.put(("loadfail", ""))
            self._msgs.put(("oodle", ""))
        except Exception:
            err = traceback.format_exc()
            self._set_status("Failed to load game data – see error dialog.")
            self._msgs.put(("loadfail", ""))
            self._msgs.put(("error", err))

    def _pick_game_dir(self):
        path = filedialog.askdirectory(title="Select the S.T.A.L.K.E.R. 2 game folder")
        if not path:
            return
        p = Path(path)
        if not game.is_game_dir(p):
            messagebox.showerror(
                APP_TITLE,
                "That doesn't look like the game folder.\n"
                "Expected: the folder containing Stalker2\\Content\\Paks.")
            return
        self.game_dir = p
        self.gd = None
        self._set_busy(True)
        self._set_body_state(False)
        self.btn_confirm.configure(text="✓ Confirm & load game data")
        self.game_label.configure(text=f"Game folder: {p}")
        self.status.configure(
            text="Folder selected – now click 'Confirm & load game data'.")

    # ------------------------------------------------------------ settings
    def _collect_weapon_cats(self) -> dict:
        """{Kategorie: {param: faktor}} — nur Abweichungen von 1.0."""
        result: dict = {}
        for cat in WEAPON_CATEGORY_LABELS:
            factors = {}
            for param in WEAPON_PARAMS:
                value = self.sliders[f"wcat_{cat}_{param}"].get()
                if abs(value - 1.0) > 1e-9:
                    factors[param] = value
            if factors:
                result[cat] = factors
        return result

    def _collect(self) -> Settings:
        s = self.sliders
        cats = {c for c, box in self.cat_checks.items() if box.get()}
        name = "".join(ch for ch in self.name_entry.get().strip() if ch.isalnum() or ch in "_-")
        return Settings(
            mod_name=name or "S2Tweaker",
            max_hp=s["hp"].get(),
            hp_regen=s["hp_regen"].get(),
            max_stamina=s["sp"].get(),
            stamina_regen=s["sp_regen"].get(),
            fall_damage_pct=s["fall"].get(),
            walk_speed_factor=s["walk"].get() / 100.0,
            run_speed_factor=s["run"].get() / 100.0,
            jump_height_factor=s["jump"].get() / 100.0,
            vault_height_factor=s["vault_height"].get() / 100.0,
            vault_distance_factor=s["vault_distance"].get() / 100.0,
            vault_angle_factor=s["vault_angle"].get() / 100.0,
            vault_min_height_factor=s["vault_min_height"].get() / 100.0,
            vault_landing_factor=s["vault_landing"].get() / 100.0,
            vault_over_depth_factor=s["vault_over_depth"].get() / 100.0,
            vault_over_offset_factor=s["vault_over_offset"].get() / 100.0,
            vault_sprint=bool(self.checks["vault_sprint"].get()),
            improved_vaulting=bool(self.checks["improved_vaulting"].get()),
            stamina_sprint=s["st_sprint"].get() / 100.0,
            stamina_jump=s["st_jump"].get() / 100.0,
            stamina_melee_light=s["st_melee_l"].get() / 100.0,
            stamina_melee_strong=s["st_melee_s"].get() / 100.0,
            stamina_buttstock=s["st_butt"].get() / 100.0,
            stamina_vault=s["st_vault"].get() / 100.0,
            max_carry_weight=s["carry"].get(),
            penalty_start_weight=s["penalty"].get(),
            no_overweight_penalty=bool(self.checks["no_overweight"].get()),
            item_weight_factor=s["weight"].get() / 100.0,
            item_weight_categories=cats,
            ignore_equipped_weight=bool(self.checks["ignore_equipped"].get()),
            quest_items_weightless=bool(self.checks["quest_weightless"].get()),
            player_damage_factor=s["pdmg"].get(),
            headshot_factor=s["headshot"].get(),
            aim_punch_factor=s["aimpunch"].get() / 100.0,
            npc_damage_factor=s["npcdmg"].get(),
            npc_hp_factor=s["npchp"].get(),
            npc_accuracy_factor=s["npc_acc"].get(),
            npc_vision_factor=s["npc_vision"].get() / 100.0,
            npc_hearing_factor=s["npc_hearing"].get() / 100.0,
            npc_reaction_factor=s["npc_reaction"].get() / 100.0,
            npc_grenade_factor=s["npc_grenades"].get() / 100.0,
            npc_no_heal=bool(self.checks["npc_no_heal"].get()),
            npc_gear_quality_factor=s["npc_gear"].get() / 100.0,
            npc_free_shots_factor=s["npc_free_shots"].get() / 100.0,
            npc_burst_factor=s["npc_burst"].get() / 100.0,
            npc_fire_pause_factor=s["npc_fire_pause"].get() / 100.0,
            npc_engage_range_factor=s["npc_engage"].get() / 100.0,
            npc_weapon_range_factor=s["npc_range"].get() / 100.0,
            npc_regen_factor=s["npc_regen"].get() / 100.0,
            crouch_stealth_factor=s["stealth_crouch"].get() / 100.0,
            movement_noise_factor=s["stealth_noise"].get() / 100.0,
            weather_stealth_factor=s["stealth_weather"].get() / 100.0,
            flashlight_stealth_factor=s["stealth_flashlight"].get() / 100.0,
            npc_alertness_factor=s["npc_alertness"].get() / 100.0,
            npc_search_time_factor=s["npc_search"].get() / 100.0,
            npc_courage_factor=s["npc_courage"].get() / 100.0,
            npc_stagger_factor=s["npc_stagger"].get() / 100.0,
            npc_attack_cooldown_factor=s["npc_attack_cd"].get() / 100.0,
            npc_weapon_rank_add=s["npc_rank_add"].get(),
            npc_flashlight_factor=s["npc_light"].get() / 100.0,
            npc_flashlight_cone_factor=s["npc_light_cone"].get() / 100.0,
            npc_flashlight_combat_factor=s["npc_light_combat"].get() / 100.0,
            npc_flashlight_on_hour=int(s["npc_light_on"].get()),
            npc_flashlight_off_hour=int(s["npc_light_off"].get()),
            mutant_attack_cooldown_factor=s["mut_attack_cd"].get() / 100.0,
            max_agents_factor=s["alife_agents"].get() / 100.0,
            spawn_distance_factor=s["alife_distance"].get() / 100.0,
            lair_mutant_factor=s["lair_mutants"].get() / 100.0,
            lair_human_factor=s["lair_humans"].get() / 100.0,
            lair_respawn_factor=s["lair_respawn"].get() / 100.0,
            encounter_frequency_factor=s["enc_freq"].get() / 100.0,
            encounter_mutant_factor=s["enc_mutants"].get() / 100.0,
            encounter_pack_factor=s["enc_pack"].get() / 100.0,
            enc_blinddog_factor=s["enc_blinddog"].get() / 100.0,
            enc_boar_factor=s["enc_boar"].get() / 100.0,
            enc_flesh_factor=s["enc_flesh"].get() / 100.0,
            enc_tushkan_factor=s["enc_tushkan"].get() / 100.0,
            enc_chimera_factor=s["enc_chimera"].get() / 100.0,
            enc_generic_mutant_factor=s["enc_generic"].get() / 100.0,
            mutant_hp_factor=s["mhp"].get(),
            mutant_damage_factor=s["mdmg"].get(),
            mutant_speed_factor=s["mspeed"].get(),
            mutant_hearing_factor=s["mhearing"].get() / 100.0,
            mutant_regen_factor=s["mut_regen"].get(),
            mutant_overrides={sp: dict(v)
                              for sp, v in self.mutant_overrides.items()},
            bloodsucker_cloak_factor=s["bs_cloak"].get(),
            bloodsucker_uncloak_factor=s["bs_uncloak"].get(),
            explosion_damage_factor=s["expl"].get(),
            durability_factor=s["dur"].get(),
            armor_durability_factor=s["dur_armor"].get(),
            jamming_factor=s["jam"].get(),
            armor_strike_factor=s["ap_strike"].get() / 100.0,
            armor_burn_factor=s["ap_burn"].get() / 100.0,
            armor_shock_factor=s["ap_shock"].get() / 100.0,
            armor_chemical_factor=s["ap_chem"].get() / 100.0,
            armor_radiation_factor=s["ap_rad"].get() / 100.0,
            armor_psy_factor=s["ap_psy"].get() / 100.0,
            armor_carry_bonus_factor=s["ap_carry"].get() / 100.0,
            scope_sway_pct=s["sway"].get(),
            breath_drain_factor=s["breath_drain"].get() / 100.0,
            breath_regen_factor=s["breath_regen"].get() / 100.0,
            spread_factor=s["spread"].get() / 100.0,
            recoil_factor=s["recoil"].get() / 100.0,
            recoil_upgrade_factor=s["recoil_upgrades"].get() / 100.0,
            weapon_range_factor=s["wrange"].get() / 100.0,
            weapon_bleeding_factor=s["wbleed"].get() / 100.0,
            ads_speed_factor=s["adsmove"].get() / 100.0,
            aim_time_factor=s["aimspeed"].get() / 100.0,
            magazine_factor=s["magazine"].get() / 100.0,
            melee_damage_factor=s["melee"].get() / 100.0,
            melee_range_factor=s["melee_range"].get() / 100.0,
            interaction_range_factor=s["interact"].get() / 100.0,
            dialog_range_factor=s["dialog_range"].get() / 100.0,
            manual_save_slots=int(s["save_manual"].get()),
            quick_save_slots=int(s["save_quick"].get()),
            auto_save_slots=int(s["save_auto"].get()),
            autosave_interval_min=float(s["autosave_min"].get()),
            ammo_damage_factor=s["ammo_dmg"].get() / 100.0,
            ammo_piercing_factor=s["ammo_ap"].get() / 100.0,
            ammo_armor_damage_factor=s["ammo_ad"].get() / 100.0,
            ammo_cover_factor=s["ammo_cover"].get() / 100.0,
            weapon_category_factors=self._collect_weapon_cats(),
            weapon_overrides={sid: dict(v)
                              for sid, v in self.weapon_overrides.items()},
            weapon_calibers=dict(self.weapon_calibers),
            ammo_overrides={sid: dict(v)
                            for sid, v in self.ammo_overrides.items()},
            armor_overrides={sid: dict(v)
                             for sid, v in self.armor_overrides.items()},
            faction_relations=dict(self.faction_relations),
            relation_rollback_factor=s["rel_rollback"].get() / 100.0,
            relation_reaction_factor=s["rel_reaction"].get() / 100.0,
            trade_min_level=s["rel_trade"].get(),
            anomaly_damage_factor=s["anomaly"].get(),
            anomaly_electro_factor=s["anom_electro"].get(),
            anomaly_chemical_factor=s["anom_chem"].get(),
            anomaly_fire_factor=s["anom_fire"].get(),
            anomaly_gravity_factor=s["anom_grav"].get(),
            radiation_factor=s["radiation"].get(),
            bleeding_factor=s["bleeding"].get(),
            hunger_rate_factor=s["hunger"].get() / 100.0,
            sleepiness_rate_factor=s["sleep"].get() / 100.0,
            consumable_factor=s["consumable"].get() / 100.0,
            healing_factor=s["healing"].get() / 100.0,
            consumable_duration_factor=s["cons_duration"].get() / 100.0,
            day_length_factor=s["day_length"].get() / 100.0,
            rain_factor=s["rain"].get() / 100.0,
            emission_factor=s["emission"].get() / 100.0,
            emission_duration_factor=s["emission_dur"].get() / 100.0,
            stash_loot_factor=s["stash_loot"].get() / 100.0,
            stash_chance_factor=s["stash_chance"].get() / 100.0,
            stash_ammo_factor=s["stash_ammo"].get() / 100.0,
            loot_amount_factor=s["loot_amount"].get() / 100.0,
            dropped_condition_pct=s["drop_cond"].get(),
            dropped_condition_exact=bool(self.checks["drop_cond_exact"].get()),
            trader_stock_factor=s["trader_stock"].get() / 100.0,
            trader_variety_factor=s["trader_variety"].get() / 100.0,
            trader_money_factor=s["trader_money"].get(),
            trader_infinite_money=bool(self.checks["trader_inf_money"].get()),
            upgrades_take_both=bool(self.checks["upgrades_take_both"].get()),
            upgrades_no_blueprint=bool(self.checks["upgrades_no_blueprint"].get()),
            upgrades_no_tiers=bool(self.checks["upgrades_no_tiers"].get()),
            artifact_effect_factor=s["art_effect"].get() / 100.0,
            artifact_radiation_factor=s["art_radiation"].get() / 100.0,
            artifact_spawn_factor=s["art_spawn"].get() / 100.0,
            artifact_count_factor=s["art_count"].get(),
            artifact_respawn_factor=s["art_respawn"].get() / 100.0,
            artifact_rarity_factor=s["art_rarity"].get() / 100.0,
            detector_range_factor=s["detector"].get() / 100.0,
            fast_travel_cost_factor=s["fasttravel"].get() / 100.0,
            trader_restock_factor=s["restock"].get() / 100.0,
            trader_min_durability_pct=s["trader_dur"].get(),
            trader_buy_price_factor=s["buyprice"].get(),
            trader_sell_price_factor=s["sellprice"].get(),
            repair_cost_factor=s["repair"].get() / 100.0,
            upgrade_cost_factor=s["upgrade"].get() / 100.0,
            quest_reward_factor=s["questreward"].get(),
            repeatable_quest_factor=s["rq_cooldown"].get() / 100.0,
            weapon_price_factor=s["price_weapon"].get(),
            armor_price_factor=s["price_armor"].get(),
            ammo_price_factor=s["price_ammo"].get(),
            artifact_price_factor=s["price_artifact"].get(),
            consumable_price_factor=s["price_consumable"].get(),
        )

    def _apply_filter(self, _event=None):
        """Suchfeld: passende Regler hervorheben, Rest abdunkeln."""
        query = self.search_entry.get().strip().lower()
        counts: dict[str, int] = {}
        for key, row in self.sliders.items():
            label = row.label.cget("text").lower()
            if not query:
                row.set_highlight("normal")
            elif query in label:
                row.set_highlight("match")
                tab = self.slider_tabs.get(key, "?")
                counts[tab] = counts.get(tab, 0) + 1
            else:
                row.set_highlight("dim")
        # Kategorie-Knoepfe des Abschnitts "Weapon categories" mitfaerben.
        # Ein Block zaehlt auch dann als Treffer, wenn NUR seine (zugeklappt
        # unsichtbaren) Regler passen — sonst meldet die Statuszeile Treffer,
        # die der Benutzer nirgends aufleuchten sieht.
        for cat, (btn, label, orig, content) in self._wcat_btns.items():
            if not query:
                self._wcat_notes.pop(cat, None)
                btn.configure(text_color=orig)
            else:
                n_in = sum(
                    1 for param in WEAPON_PARAMS
                    if query in self.sliders[
                        f"wcat_{cat}_{param}"].label.cget("text").lower())
                label_hit = query in label.lower() or query in cat.lower()
                if n_in:
                    note = f"     {n_in} match{'es' if n_in != 1 else ''}"
                elif label_hit:
                    note = "     category match"
                else:
                    note = ""
                self._wcat_notes[cat] = note
                btn.configure(text_color=ACCENT if note else "gray35")
            self._wcat_render(cat)
        iw_hits = self._iw_filter(query)
        if query and iw_hits:
            counts["Weapons"] = counts.get("Weapons", 0) + iw_hits
        # Eigene Zeile, NICHT in iw_hits mitgezaehlt: sonst schickt die
        # Statuszeile den Benutzer wegen "A545" in den Weapons-Tab.
        ia_hits = self._ia_filter(query)
        if query and ia_hits:
            counts["Ammo"] = counts.get("Ammo", 0) + ia_hits
        ir_hits = self._ir_filter(query)
        if query and ir_hits:
            counts["Armor"] = counts.get("Armor", 0) + ir_hits
        if_hits = self._if_filter(query)
        if query and if_hits:
            counts["Factions"] = counts.get("Factions", 0) + if_hits
        im_hits = self._im_filter(query)
        if query and im_hits:
            counts["Mutants"] = counts.get("Mutants", 0) + im_hits
        if query:
            if self._status_before_search is None:
                self._status_before_search = self.status.cget("text")
            if counts:
                self.status.configure(text="Matches: " + ", ".join(
                    f"{tab} ({n})" for tab, n in counts.items()))
            else:
                self.status.configure(
                    text="No slider, weapon, ammo, armor, mutant or "
                         "faction matches your search.")
        elif self._status_before_search is not None:
            # Suchfeld geleert: alte Meldung zurueck statt eines stehen
            # gebliebenen "No slider, weapon or ammo matches your search."
            self.status.configure(text=self._status_before_search)
            self._status_before_search = None
        # Ohne Suchbegriff uebernimmt die Changed-only-Ansicht das Dimmen;
        # mit Suchbegriff hat die Suche Vorrang (Treffer sollen leuchten).
        if not query and self.changed_only:
            self._apply_changed_only()
        elif not query:
            self._clear_changed_only_view()

    # -------------------------------------------------------- Changed only
    def _toggle_changed_only(self):
        """Alles dimmen, was auf Vanilla steht — S2Tweaker wird zur
        Editor-Ansicht des aktuell gebauten Mods. Rein visuell (dimmen statt
        ausblenden): Layout und Reihenfolge bleiben stabil, gedimmte Regler
        sind weiter bedienbar. Eine laufende Suche hat Vorrang."""
        self.changed_only = not self.changed_only
        self.btn_changed.configure(
            fg_color=ACCENT if self.changed_only else "gray30",
            text_color="gray10" if self.changed_only else
            self.btn_faq.cget("text_color"))
        self._oc_cancel()
        self._apply_filter()
        if self.changed_only:
            self._oc_job = self.after(700, self._oc_tick)

    def _oc_cancel(self):
        if self._oc_job is not None:
            try:
                self.after_cancel(self._oc_job)
            except Exception:
                pass
            self._oc_job = None

    def _oc_tick(self):
        """Leichter Puls: haelt die Dimmung aktuell, wenn der Benutzer im
        aktiven Modus Regler bewegt (ein bewegter Regler soll sofort hell
        werden, ein zurueckgestellter wieder abdunkeln)."""
        self._oc_job = None
        if not self.changed_only:
            return
        if not self.search_entry.get().strip():
            self._apply_changed_only()
        self._oc_job = self.after(700, self._oc_tick)

    def _slider_changed_from_vanilla(self, row) -> bool:
        return abs(row.get() - row.default) > 1e-9

    def _apply_changed_only(self):
        """Dimm-Pass: Vanilla-Regler grau, Geaendertes normal; die fuenf
        Override-Baeume filtern auf ihre Overrides/geaenderten Paare."""
        for key, row in self.sliders.items():
            row.set_highlight(
                "normal" if self._slider_changed_from_vanilla(row) else "dim")
        for cat, (btn, label, orig, content) in self._wcat_btns.items():
            n = sum(1 for param in WEAPON_PARAMS
                    if self._slider_changed_from_vanilla(
                        self.sliders[f"wcat_{cat}_{param}"]))
            btn.configure(text_color=orig if n else "gray35")
        for key, box in self.checks.items():
            changed = bool(box.get()) or key in self._locked_checks
            box.configure(text_color=("gray95" if changed else "gray45"))
        for cat, box in self.cat_checks.items():
            box.configure(text_color=(
                "gray45" if bool(box.get()) else "gray95"))
        for blocks, overrides in (
                (self._iw_blocks, self.weapon_overrides),
                (self._ia_blocks, self.ammo_overrides),
                (self._ir_blocks, self.armor_overrides),
                (self._if_blocks, self.faction_relations),
                (self._im_blocks, self.mutant_overrides)):
            for block in blocks.values():
                hits = [sid for sid in block.sids if sid in overrides]
                block.set_row_filter(set(hits))
                block.set_highlight("match" if hits else "dim")

    def _clear_changed_only_view(self):
        """Dimmung zuruecknehmen (Toggle aus oder Suche uebernimmt)."""
        for box in list(self.checks.values()) + list(self.cat_checks.values()):
            box.configure(text_color="gray95")
        for cat, (btn, label, orig, content) in self._wcat_btns.items():
            btn.configure(text_color=orig)

    # ------------------------------------------------------------------ FAQ
    def _show_faq(self):
        """Durchsuchbares FAQ-Fenster (Inhalt: s2tweaker/faq.py).

        Nicht modal — man soll nebenher an den Reglern arbeiten koennen.
        Ein zweiter Klick holt das offene Fenster nach vorn, statt ein
        weiteres zu bauen."""
        existing = getattr(self, "_faq_win", None)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_set()
            return
        win = ctk.CTkToplevel(self)
        self._faq_win = win
        win.title("S2Tweaker FAQ")
        win.geometry("760x560")
        # Ohne minsize laesst sich das Fenster so schmal ziehen, dass die
        # fest umbrochenen Antworten (wraplength) rechts abgeschnitten sind.
        win.minsize(700, 320)
        win.transient(self)

        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        search = ctk.CTkEntry(
            top, placeholder_text="🔍 Search the FAQ … (e.g. medkit, loot, "
                                  "animation, antivirus)")
        search.pack(side="left", fill="x", expand=True)
        count = ctk.CTkLabel(top, text="", width=150, anchor="e",
                             text_color="gray60")
        count.pack(side="left", padx=(8, 0))

        body = ctk.CTkScrollableFrame(win)
        body.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        font_q = ctk.CTkFont(size=13)
        font_a = ctk.CTkFont(size=12)
        rows = [FaqRow(body, entry, font_q, font_a)
                for entry in faq.FAQ_ENTRIES]

        def apply_filter(_event=None):
            words = search.get().strip().lower().split()
            visible = [r for r in rows if r.matches(words)] if words else rows
            # Reihenfolge bleibt stabil: erst alle raus, dann die
            # sichtbaren in Originalreihenfolge wieder rein (pack haengt
            # sonst wieder Eingeblendete ans Ende).
            for row in rows:
                row.frame.pack_forget()
            for row in visible:
                row.frame.pack(fill="x", padx=4, pady=1)
                # Treffer direkt aufklappen — wer sucht, will die Antwort
                # sehen; ohne Suchbegriff wieder kompakt zuklappen.
                row.set_open(bool(words))
            if not words:
                count.configure(text=f"{len(rows)} questions")
            elif visible:
                count.configure(text=f"{len(visible)} match"
                                     f"{'es' if len(visible) != 1 else ''}")
            else:
                count.configure(text="no matches \u2013 try another word")

        search.bind("<KeyRelease>", apply_filter)
        # Fuer Tests erreichbar machen (KeyRelease landet am inneren
        # tk-Widget der CTkEntry und ist per event_generate nicht triggerbar)
        win._faq_rows = rows
        win._faq_search = search
        win._faq_apply_filter = apply_filter
        apply_filter()
        # CTkToplevel zieht den Fokus waehrend seiner withdraw/deiconify-
        # Einrichtung wieder weg — direkt gesetzter Fokus geht verloren.
        win.after(250, search.focus_set)

    # ------------------------------------------------------------ mod scan
    def _maybe_offer_modscan(self):
        """Nach dem Laden der Spieldaten EINMAL fragen, ob fremde Mods in
        ~mods gescannt werden sollen. NIE ungefragt scannen — Overhaul-Mods
        koennen 2 GB gross sein, und der Besitzer soll entscheiden."""
        if (self._modscan_offered or self.modscan_pref == "never"
                or self.gd is None or self.game_dir is None
                or self._scan_running):
            return
        paks = modscan.find_mod_paks(game.mods_dir(self.game_dir),
                                     {self._out_name()})
        ws = modscan.find_workshop_paks(
            game.steam_workshop_dir(self.game_dir))
        if not paks and not ws:
            return
        self._modscan_offered = True
        n = len(paks)
        parts = []
        if n:
            parts.append(f"{n} mod file{'s' if n != 1 else ''} in your "
                         "~mods folder")
        if ws:
            parts.append(f"{len(ws)} Steam Workshop mod file"
                         f"{'s' if len(ws) != 1 else ''}")
        win = ctk.CTkToplevel(self)
        win.title("Other mods found")
        win.transient(self)
        win.grab_set()
        ctk.CTkLabel(
            win, wraplength=430, justify="left",
            text=f"Found {' and '.join(parts)}. "
                 "Scan them to see what they change?\n\n"
                 "The scan reads only config entries, never whole paks, so "
                 "it is quick even for very large mods.").pack(
            padx=18, pady=(18, 10))
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(pady=(4, 16))

        def answer(what):
            win.destroy()
            if what == "scan":
                self._start_modscan()
            elif what == "never":
                self.modscan_pref = "never"

        ctk.CTkButton(row, text="Scan now", width=110,
                      command=lambda: answer("scan")).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Not now", width=100, fg_color="gray35",
                      hover_color="gray25",
                      command=lambda: answer("later")).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Don't ask again", width=120, fg_color="gray35",
                      hover_color="gray25",
                      command=lambda: answer("never")).pack(side="left", padx=6)

    def _start_modscan(self):
        if self.gd is None or self.game_dir is None or self._scan_running:
            return
        paks = modscan.find_mod_paks(game.mods_dir(self.game_dir),
                                     {self._out_name()})
        ws_dir = game.steam_workshop_dir(self.game_dir)
        # Workshop-Paks bekommen ihren Mod-Namen als Anzeigename mit —
        # der Dateiname allein ("...-Windows-OverrideContent") sagt nichts.
        jobs = [(p, None) for p in paks]
        jobs += [(p, modscan.workshop_mod_name(p, ws_dir))
                 for p in modscan.find_workshop_paks(ws_dir)]
        if not jobs:
            # Fruehere Markierungen aufraeumen — die Mods sind offenbar weg
            self.mod_conflicts = {}
            self.modscan_results = []
            self._mods_after = set()
            self._mods_unknown = set()
            self._apply_conflict_marks()
            self._status_write(
                "No other mods found (~mods and Steam Workshop).")
            return
        # Scan und (Neu-)Laden schliessen sich gegenseitig aus: sonst
        # rechnet der Worker gegen halb ausgetauschte Spieldaten und
        # fuellt den frisch geleerten Fussabdruck-Cache mit alten Werten.
        self._scan_running = True
        self.btn_scan.configure(state="disabled")
        self.btn_confirm.configure(state="disabled")
        self.btn_browse.configure(state="disabled")
        threading.Thread(target=self._run_modscan, args=(self.gd, jobs),
                         daemon=True).start()

    def _run_modscan(self, gd, jobs):
        """Hintergrund-Thread: Paks scannen und mit den Reglern abgleichen.
        jobs: Liste (Pak-Pfad, Workshop-Anzeigename oder None).

        gd ist ein SNAPSHOT — der Worker darf nie self.gd lesen, sonst
        crasht er, wenn der Besitzer waehrenddessen den Spielordner
        wechselt (self.gd wird dort auf None gesetzt)."""
        try:
            self._set_status("Indexing vanilla values ...")
            vanilla = modscan.build_vanilla_index(gd)
            infos = []
            for p, ws_name in jobs:
                info = modscan.scan_pak(p, progress=self._set_status,
                                        vanilla_index=vanilla)
                if ws_name is not None:
                    info.name = ws_name
                    info.source = "workshop"
                infos.append(info)
            # Workshop-Abos liegen oft doppelt vor (alter + neuer Pfad,
            # gleicher Anzeigename) -> ein Eintrag je Mod, nicht zwei.
            infos = modscan.merge_same_name(infos)
            self._set_status("Comparing with this tool's settings ...")
            conflicts = self._match_conflicts(gd, infos)
            self._modscan_payload = (infos, conflicts)
            self._msgs.put(("modscan_done", ""))
        except Exception:
            self._msgs.put(("modscan_done", ""))
            self._msgs.put(("error", traceback.format_exc()))

    def _footprint(self, gd, key: str) -> set | None:
        """Fussabdruck eines Reglers, im Speicher gecacht: welche
        (Top-Level-Struct, Blattname)-Paare patcht er? Vereinigung der
        Sonden aus footprint_settings (x2 UND x0.5)."""
        if key not in self._footprints:
            probes = footprint_settings(key)
            if probes is None:
                self._footprints[key] = None
            else:
                pairs: set = set()
                for s in probes:
                    pairs |= modscan.pairs_from_patches(build_patches(gd, s))
                self._footprints[key] = pairs
        return self._footprints[key]

    def _match_conflicts(self, gd, infos) -> dict[str, list[str]]:
        segments: set[str] = set()
        leaves: set[str] = set()
        for info in infos:
            segments |= info.base_names
            leaves |= {leaf for _, leaf in info.pairs}
        conflicts: dict[str, list[str]] = {}
        keys = list(self.sliders) + ["check:" + k for k in self.checks]
        for key in keys:
            guard = EXPENSIVE_FOOTPRINTS.get(key)
            if guard and key not in self._footprints:
                fragment, guard_leaves = guard
                if (not any(fragment in seg for seg in segments)
                        and not (guard_leaves & leaves)):
                    continue
            pairs = self._footprint(gd, key)
            if not pairs:
                continue
            mods = [info.name for info in infos if info.pairs & pairs]
            if mods:
                conflicts[key] = mods
        # Vierter Baum (Fraktionsbeziehungen): seine Zeilen liegen nicht in
        # self.sliders, und anders als bei Waffen/Ammo/Ruestung deckt KEIN
        # globaler Regler die Relations-Blaetter ab (Befund des Feature-
        # Reviews 02.09.). Ein Sammel-Fussabdruck ueber alle kuratierten
        # Paare stopft das Loch: fremde Mods auf denselben Paaren erscheinen
        # unter dem Pseudo-Schluessel "tree:factions" im Dialog, im Report
        # und als Hinweis im Factions-Tab. Bewusst KEINE Regler-Punkte und
        # KEINE Avoid-Sperre je Zeile — der Hinweistext sagt das ehrlich.
        pairs = self._faction_tree_footprint(gd)
        if pairs:
            mods = [info.name for info in infos if info.pairs & pairs]
            if mods:
                conflicts["tree:factions"] = mods
        return conflicts

    def _faction_tree_footprint(self, gd) -> set:
        """Vereinigter Fussabdruck aller kuratierten Beziehungspaare
        (+ RelationVersion), gecacht wie die Regler-Fussabdruecke."""
        key = "tree:factions"
        if key not in self._footprints:
            rel = gd.relation_pairs()
            probe: dict[str, int] = {}
            for i, (sid, _label) in enumerate(FACTION_CHOICES):
                for other in ["Player"] + [s for s, _l in
                                           FACTION_CHOICES[i + 1:]]:
                    pk = gd.relation_pair_key(sid, other)
                    if pk is not None and pk in rel:
                        probe[pk] = rel[pk] + 1     # garantiert != Vanilla
            pairs: set = set()
            if probe:
                pairs = modscan.pairs_from_patches(
                    build_patches(gd, Settings(faction_relations=probe)))
            self._footprints[key] = pairs
        return self._footprints[key] or set()

    def _finish_modscan(self):
        self._scan_running = False
        self.btn_scan.configure(state="normal")
        self.btn_confirm.configure(state="normal")
        self.btn_browse.configure(state="normal")
        if self._modscan_payload is None:
            return
        infos, conflicts = self._modscan_payload
        self._modscan_payload = None
        self.modscan_results = infos
        self.mod_conflicts = conflicts
        # Ladereihenfolge in ~mods ist alphabetisch (deshalb das zzz_-
        # Praefix). Mods, deren Pak NACH unserer sortiert, ueberschreiben
        # gemeinsame Werte — "your value wins" waere dort gelogen.
        # Workshop-Mods laufen ueber den Mod-Manager des Spiels: ihre
        # Reihenfolge relativ zu ~mods ist unverifiziert -> eigener Topf.
        own = self._out_name().lower()
        self._mods_after = {info.name for info in infos
                            if info.source != "workshop"
                            and info.path.name.lower() > own}
        self._mods_unknown = {info.name for info in infos
                              if info.source == "workshop"}
        self._apply_conflict_marks()
        if conflicts:
            extra = ""
            if self.avoid_conflicts:
                n = self._avoid_lock_count()
                extra = f" Avoid conflicts: {n} locked."
            self._status_write(
                f"Scanned {len(infos)} mod(s): {len(conflicts)} of this "
                f"tool's settings are also changed by them (see the dots)."
                f"{extra}")
        else:
            self._status_write(
                f"Scanned {len(infos)} mod(s): no overlap with this "
                "tool's settings.")
        self._show_modscan_results()

    def _apply_conflict_marks(self):
        for key, row in self.sliders.items():
            row.set_conflict(self.mod_conflicts.get(key), self._mods_after,
                             self._mods_unknown)
        self._if_update_conflict_note()
        self._apply_conflict_locks()
        self._refresh_check_dots()

    def _if_update_conflict_note(self):
        """Scan-Hinweis im Factions-Tab: fremde Mods auf denselben
        Beziehungspaaren. Info-Blau bei unverstellten, Warn-Violett bei
        verstellten eigenen Paaren — dieselbe Stufenlogik wie die Punkte."""
        if not hasattr(self, "if_conflict_label"):
            return
        mods = sorted(self.mod_conflicts.get("tree:factions") or [])
        if not mods:
            self.if_conflict_label.pack_forget()
            return
        after = sorted(set(mods) & self._mods_after)
        unknown = sorted(set(mods) & self._mods_unknown)
        text = "●  Mod scan: also changing faction relations: " + ", ".join(mods)
        if after:
            text += ("  —  " + ", ".join(after)
                     + " loads AFTER your pak and wins shared values")
        if unknown:
            text += ("  —  " + ", ".join(unknown)
                     + " is loaded by the game's mod manager (load order "
                     "unknown)")
        text += (".  The Avoid-conflicts switch does not lock these rows – "
                 "reset them yourself if you want to stay neutral here.")
        self.if_conflict_label.configure(
            text="   " + text,
            text_color=MARK_WARN if self.faction_relations else MARK_INFO)
        self.if_conflict_label.pack(fill="x", padx=12, pady=(0, 2),
                                    before=self.if_info)

    # ------------------------------------------------ Avoid-conflicts-Modus
    def _apply_conflict_locks(self):
        """Avoid-conflicts anwenden: jeden vom Scan gemeldeten Regler auf
        Vanilla setzen und sperren — ausser der Benutzer hat ihn bewusst
        freigeschaltet. Beim Sperren wird der bisherige Wert gemerkt und
        beim Entsperren (in DIESER Sitzung) zurueckgelegt."""
        conflicted = set(self.mod_conflicts) if self.avoid_conflicts else set()
        for key, row in self.sliders.items():
            want = key in conflicted and key not in self.avoid_unlocked
            if want and not row.locked:
                current = row.get()
                if abs(current - row.default) > 1e-9:
                    self._avoid_saved[key] = current
                row.set(row.default)
                row.set_locked(True, lambda k=key: self._avoid_unlock(k))
            elif not want and row.locked:
                row.set_locked(False)
                saved = self._avoid_saved.pop(key, None)
                if saved is not None:
                    row.set(saved)
            elif want:
                # schon gesperrt: Unlock-Callback aktuell halten UND die
                # Sperre durchsetzen — ein Preset-Load schreibt sonst einen
                # Wert auf den gesperrten Regler und die Pak waere nicht
                # mehr neutral (empirisch belegt).
                row.set_locked(True, lambda k=key: self._avoid_unlock(k))
                if abs(row.get() - row.default) > 1e-9:
                    self._avoid_saved[key] = row.get()
                    row.set(row.default)
        for key, box in self.checks.items():
            ckey = "check:" + key
            want = ckey in conflicted and ckey not in self.avoid_unlocked
            locked_now = key in self._locked_checks
            if want and not locked_now:
                if bool(box.get()):
                    self._avoid_saved[ckey] = True
                box.deselect()
                box.configure(state="disabled")
                self._locked_checks.add(key)
            elif not want and locked_now:
                self._locked_checks.discard(key)
                box.configure(state=self._body_enabled_state())
                if self._avoid_saved.pop(ckey, None):
                    box.select()
        self._refresh_check_dots()

    def _body_enabled_state(self) -> str:
        """Aktueller Grundzustand der Bedienelemente (an _iw_state gekoppelt,
        das _set_body_state fuer alle Baeume pflegt)."""
        return self._iw_state

    def _avoid_unlock(self, key: str):
        """EINEN Regler bewusst freischalten (bleibt ueber Re-Scans und —
        weil persistiert — auch ueber Neustarts hinweg frei)."""
        self.avoid_unlocked.add(key)
        self._apply_conflict_locks()
        label = key
        if key.startswith("check:"):
            box = self.checks.get(key[len("check:"):])
            if box is not None:
                label = str(box.cget("text"))
        elif key in self.sliders:
            label = str(self.sliders[key].label.cget("text"))
        self._status_write(f"Unlocked: {label} — your value applies again "
                           "even though another mod changes it too.")

    def _avoid_lock_count(self) -> int:
        return (sum(1 for r in self.sliders.values() if r.locked)
                + len(self._locked_checks))

    def _set_avoid_mode(self, enabled: bool):
        # Bewusstes EINSCHALTEN sperrt wieder ALLES: sonst gaebe es keinen
        # Weg, einen frueher freigeschalteten Regler je wieder zu sperren.
        # Solange der Modus an bleibt (auch ueber Neustarts), gelten die
        # Freischaltungen weiter — nur der explizite Schalter setzt sie
        # zurueck.
        if enabled:
            self.avoid_unlocked.clear()
        self.avoid_conflicts = enabled
        self._apply_conflict_locks()
        if enabled:
            n = self._avoid_lock_count()
            self._status_write(
                f"Avoid conflicts ON: {n} setting{'s' if n != 1 else ''} "
                "reset to vanilla and locked (\U0001f513 unlocks one).")
        else:
            self._status_write("Avoid conflicts OFF: all settings unlocked "
                               "(previous values restored).")

    def _refresh_check_dots(self):
        for key in self.check_dots:
            self._update_check_dot(key)

    def _update_check_dot(self, key: str):
        dot = self.check_dots.get(key)
        if dot is None:
            return
        mods = self.mod_conflicts.get("check:" + key) or []
        if not mods:
            dot.configure(text="")
            self._check_tips[key] = ""
            return
        names = ", ".join(sorted(mods))
        if key in self._locked_checks:
            dot.configure(text="\U0001f512", text_color=MARK_INFO)
            self._check_tips[key] = (
                f"locked by Avoid conflicts \u2014 {names} changes this; "
                "click the lock to unlock this setting")
            return
        if bool(self.checks[key].get()):
            dot.configure(text="\u25cf", text_color=MARK_WARN)
            notes = []
            losers = sorted(set(mods) & self._mods_after)
            unknown = sorted(set(mods) & self._mods_unknown)
            if losers:
                notes.append(f"{', '.join(losers)} loads AFTER your pak, "
                             "so its value may win")
            if unknown:
                notes.append(f"{', '.join(unknown)} is loaded by the "
                             "game's own mod manager (load order unknown), "
                             "so its value may win")
            if notes:
                self._check_tips[key] = (
                    f"{names} changes this too \u2014 and "
                    + "; ".join(notes))
            else:
                self._check_tips[key] = (
                    f"{names} changes this too \u2014 your value wins")
        else:
            dot.configure(text="\u25cf", text_color=MARK_INFO)
            self._check_tips[key] = f"also changed by {names}"

    def _conflict_labels(self, mod_name: str) -> list[str]:
        """Lesbare Regler-Namen, die sich mit einer Mod ueberschneiden."""
        labels = []
        for key, mods in sorted(self.mod_conflicts.items()):
            if mod_name not in mods:
                continue
            if key.startswith("check:"):
                box = self.checks.get(key[len("check:"):])
                if box is not None:
                    labels.append(str(box.cget("text")))
            elif key == "tree:factions":
                labels.append("Faction relations (Factions tab)")
            elif key in self.sliders:
                labels.append(str(self.sliders[key].label.cget("text")))
        return labels

    def _build_compat_report(self) -> str:
        """Kompatibilitaets-Bericht als Klartext — zum Anhaengen an
        Nexus-Kommentare ("doesn't work with X" -> "send me the report")."""
        now = datetime.datetime.now().isoformat(timespec="seconds")
        own = self._out_name()
        fp = self._game_fingerprint()
        lines = [
            "S2Tweaker compatibility report",
            f"Generated: {now}  |  S2Tweaker {__version__}  |  "
            f"game pak fingerprint: {fp if fp else 'n/a'}",
            f"Own output pak: {own}  (load order in ~mods is alphabetical)",
            f"Avoid-conflicts mode: {'ON' if self.avoid_conflicts else 'off'}"
            + (f", consciously unlocked: "
               + ", ".join(sorted(self.avoid_unlocked))
               if self.avoid_conflicts and self.avoid_unlocked else ""),
            "",
            f"Scanned mods ({len(self.modscan_results)}):",
        ]
        for info in self.modscan_results:
            if info.source == "workshop":
                order = ("Steam Workshop mod - activation and load order "
                         "are managed by the game (not verified)")
            elif info.name in self._mods_after:
                order = "loads AFTER your pak - ITS values win shared conflicts"
            else:
                order = "loads before your pak - your values win"
            lines.append(f"  {info.name}  [{info.path.name}]"
                         if info.source == "workshop"
                         else f"  {info.path.name}")
            if not info.readable:
                lines.append(f"      {info.note}")
                lines.append("      overlap unknown - this tool cannot "
                             "look inside this format")
                continue
            labels = self._conflict_labels(info.name)
            lines.append(f"      {info.n_cfg} config file"
                         f"{'s' if info.n_cfg != 1 else ''}, {order}")
            if labels:
                lines.append("      overlapping settings: "
                             + ", ".join(labels))
            elif info.n_cfg:
                lines.append("      no overlap with this tool's settings")
            if info.note:
                lines.append(f"      note: {info.note}")
        if self.mod_conflicts:
            lines += ["", "Details per setting (advanced - the game "
                          "structs/properties both sides touch):"]
            for key, mods in sorted(self.mod_conflicts.items()):
                if key.startswith("check:"):
                    box = self.checks.get(key[len("check:"):])
                    label = str(box.cget("text")) if box else key
                elif key == "tree:factions":
                    label = "Faction relations (Factions tab)"
                else:
                    row = self.sliders.get(key)
                    label = str(row.label.cget("text")) if row else key
                lines.append(f"  {label}")
                pairs = self._footprints.get(key) or set()
                for info in self.modscan_results:
                    if info.name not in mods:
                        continue
                    overlap = sorted(pairs & info.pairs)
                    shown = ", ".join(f"{a}.{b}" for a, b in overlap[:10])
                    more = ("" if len(overlap) <= 10
                            else f" (+{len(overlap) - 10} more)")
                    lines.append(f"      {info.name}: {shown}{more}")
        lines += ["", "Notes: only values off (vanilla) are written to the "
                      "pak; shared values are decided by ~mods load order "
                      "(alphabetical).", ""]
        return "\n".join(lines)

    def _export_compat_report(self):
        path = filedialog.asksaveasfilename(
            title="Export compatibility report", defaultextension=".txt",
            initialdir=output_dir(),
            initialfile="S2Tweaker_Compatibility_Report.txt",
            filetypes=[("Text file", "*.txt")])
        if not path:
            return
        try:
            Path(path).write_text(self._build_compat_report(),
                                  encoding="utf-8")
            self._status_write(f"Compatibility report saved: {path}")
        except OSError:
            messagebox.showerror(APP_TITLE, traceback.format_exc())

    def _show_modscan_results(self):
        win = ctk.CTkToplevel(self)
        win.title("What your other mods change")
        win.geometry("660x520")
        win.transient(self)
        frame = ctk.CTkScrollableFrame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        bold = ctk.CTkFont(size=13, weight="bold")

        def line(text, **kw):
            ctk.CTkLabel(frame, text=text, anchor="w", justify="left",
                         wraplength=580, **kw).pack(fill="x", padx=8, pady=2)

        readable = [i for i in self.modscan_results if i.readable]
        broken = [i for i in self.modscan_results if not i.readable]
        for info in readable:
            line(info.name, font=bold)
            labels = self._conflict_labels(info.name)
            if labels:
                line("Changes settings this tool also covers: "
                     + ", ".join(labels), text_color="gray80")
            elif info.n_cfg:
                line("Changes game configs, but none that overlap with "
                     "this tool's settings.", text_color="gray60")
            if info.note:
                line(info.note, text_color="gray60")
        if broken:
            line("These mods contain data I can't read:", font=bold)
            for info in broken:
                line(f"{info.name} \u2014 {info.note}", text_color="gray60")
        after = sorted(self._mods_after
                       & {i.name for i in self.modscan_results})
        if after:
            line("\u26a0 " + ", ".join(after) + " load(s) AFTER this "
                 "tool's pak (~mods loads alphabetically) \u2014 for any "
                 "shared value THAT mod wins, not your slider.",
                 text_color=ACCENT)
        ws = sorted(self._mods_unknown
                    & {i.name for i in self.modscan_results})
        if ws:
            line("Steam Workshop: " + ", ".join(ws) + " \u2014 subscribed via "
                 "the Steam Workshop. Whether such a mod is actually "
                 "ACTIVE is decided in the game's own mods menu, and its "
                 "load order versus this tool's pak is managed by the "
                 "game (not verified) \u2014 shared values may go either way.",
                 text_color="gray60")
        line("Affected settings are marked with a dot: blue = a mod changes "
             "it while you are at (vanilla), violet = you changed it too. "
             "Your pak usually wins shared values because its zzz_ name "
             "loads last. The dots stay until you scan again.",
             text_color="gray60")

        foot = ctk.CTkFrame(win, fg_color="transparent")
        foot.pack(fill="x", padx=12, pady=(0, 10))
        avoid_box = ctk.CTkCheckBox(
            foot, text="Avoid conflicts – reset & lock every setting "
                       "these mods change")
        if self.avoid_conflicts:
            avoid_box.select()
        avoid_hint = ctk.CTkLabel(
            foot, text="", anchor="w", justify="left", wraplength=580,
            font=ctk.CTkFont(size=11), text_color="gray60")

        def refresh_hint():
            if self.avoid_conflicts:
                n = self._avoid_lock_count()
                avoid_hint.configure(
                    text=f"{n} setting{'s' if n != 1 else ''} locked at "
                         "(vanilla). Unlock one with its \U0001f513 button "
                         "– unlocks are remembered while this stays on; "
                         "re-ticking the box locks everything again. The "
                         "override trees are not locked: for weapons/ammo/"
                         "armor their global sliders are locked instead; "
                         "faction relations are only reported (see the "
                         "note on the Factions tab).")
            else:
                avoid_hint.configure(
                    text="Locks the marked settings at (vanilla) so this "
                         "tool cannot fight the mods above. Your current "
                         "values come back when you turn it off.")

        def on_avoid():
            self._set_avoid_mode(bool(avoid_box.get()))
            refresh_hint()

        avoid_box.configure(command=on_avoid)
        if self.mod_conflicts:
            avoid_box.pack(anchor="w", pady=(0, 2))
            refresh_hint()
            avoid_hint.pack(fill="x", padx=28)
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=(0, 10))
        ctk.CTkButton(btns, text="Export report \u2026", width=140,
                      command=self._export_compat_report).pack(
            side="left", padx=6)
        ctk.CTkButton(btns, text="Close", width=100,
                      command=win.destroy).pack(side="left", padx=6)

    def _reset_all(self):
        for slider in self.sliders.values():
            slider.reset()
        for box in self.checks.values():
            box.deselect()
        for box in self.cat_checks.values():
            box.select()
        self._iw_clear_all()
        self._ia_clear_all()
        self._ir_clear_all()
        self._if_clear_all()
        self._im_clear_all()
        # Scan-Punkte bleiben absichtlich stehen (die fremden Mods sind ja
        # weiterhin installiert) — nur die Stufe faellt auf Info zurueck.
        # Gemerkte Vor-Sperr-Werte verfallen: nach "Reset all to vanilla"
        # soll ein spaeteres Entsperren nicht einen alten Wert zurueckholen.
        self._avoid_saved.clear()
        self._refresh_check_dots()

    def _ui_state(self) -> dict:
        """Kompletter Regler-Zustand (fuer settings.json UND Presets)."""
        return {
            "sliders": {k: v.get() for k, v in self.sliders.items()},
            "checks": {k: bool(v.get()) for k, v in self.checks.items()},
            "cats": {k: bool(v.get()) for k, v in self.cat_checks.items()},
            "weapon_overrides": self.weapon_overrides,
            "weapon_calibers": self.weapon_calibers,
            "ammo_overrides": self.ammo_overrides,
            "armor_overrides": self.armor_overrides,
            "mutant_overrides": self.mutant_overrides,
            "faction_relations": self.faction_relations,
        }

    def _save_ui_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "game_dir": str(self.game_dir) if self.game_dir else None,
                "mod_name": self.name_entry.get(),
                "debug_cfg": bool(self.debug_check.get()),
                "modscan_pref": self.modscan_pref,
                "modscan_avoid": self.avoid_conflicts,
                "changed_only": self.changed_only,
                "modscan_unlocked": sorted(self.avoid_unlocked),
                **self._ui_state(),
            }
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _save_preset(self):
        presets_dir().mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save preset", defaultextension=".json",
            initialdir=presets_dir(), initialfile="my_preset.json",
            filetypes=[("S2Tweaker preset", "*.json")])
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps(self._ui_state(), indent=2), encoding="utf-8")
            self._status_write(f"Preset saved: {path}")
        except OSError:
            messagebox.showerror(APP_TITLE, traceback.format_exc())

    def _load_preset(self):
        presets_dir().mkdir(parents=True, exist_ok=True)
        path = filedialog.askopenfilename(
            title="Load preset or S2Tweaker pak", initialdir=presets_dir(),
            filetypes=[("S2Tweaker preset or pak", "*.json;*.pak"),
                       ("S2Tweaker preset", "*.json"),
                       ("S2Tweaker pak", "*.pak")])
        if not path:
            return
        if path.lower().endswith(".pak"):
            # Jede vom Tool gebaute Pak traegt ihr Manifest in sich und ist
            # damit selbst ein Preset (GitHub-/ChatGPT-Wunschliste).
            self._import_pak(Path(path))
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            messagebox.showerror(APP_TITLE, "Could not read that preset file.")
            return
        # Erst auf Vanilla zuruecksetzen: ein Preset beschreibt einen
        # KOMPLETTEN Zustand. Sonst blieben Regler stehen, die es beim
        # Speichern des Presets noch gar nicht gab, und wanderten unbemerkt
        # in die gebaute Pak.
        self._reset_all()
        self._apply_ui_state(data)
        if self.gd is not None:
            self._iw_populate()
            self._ia_populate()
            self._ir_populate()
            self._if_populate()
            self._im_populate()
        # _apply_ui_state gleicht die Regler schon ab; hier nur noch eine
        # laufende Suche wieder auf den neu gebauten Baum anwenden.
        self._apply_filter()
        self._status_write(f"Preset loaded: {path}")

    def _load_ui_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if data.get("game_dir"):
            p = Path(data["game_dir"])
            if game.is_game_dir(p):
                self.game_dir = p
        if data.get("mod_name"):
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, data["mod_name"])
        if data.get("debug_cfg"):
            self.debug_check.select()
        if data.get("modscan_pref") in ("ask", "never"):
            self.modscan_pref = data["modscan_pref"]
        self.avoid_conflicts = bool(data.get("modscan_avoid"))
        if data.get("changed_only"):
            # Ueber den Toggle, damit Knopf-Farbe und Tick-Loop stimmen
            self.after(200, self._toggle_changed_only)
        self.avoid_unlocked = {str(k) for k in
                               (data.get("modscan_unlocked") or [])}
        self._apply_ui_state(data)

    def _apply_ui_state(self, data: dict):
        sliders = data.get("sliders", {})
        # Migration: alter Einzelregler "move" -> "walk" + "run"
        if "move" in sliders:
            sliders.setdefault("walk", sliders["move"])
            sliders.setdefault("run", sliders["move"])
        # Migration: "dur" war frueher Waffen+Ruestung gemeinsam
        if "dur" in sliders:
            sliders.setdefault("dur_armor", sliders["dur"])
        for key, value in sliders.items():
            if key in self.sliders:
                try:
                    self.sliders[key].set(float(value))
                except (TypeError, ValueError):
                    pass
        for key, value in data.get("checks", {}).items():
            if key in self.checks:
                self.checks[key].select() if value else self.checks[key].deselect()
        for key, value in data.get("cats", {}).items():
            if key in self.cat_checks:
                self.cat_checks[key].select() if value else self.cat_checks[key].deselect()
        for sid, params in (data.get("weapon_overrides") or {}).items():
            # Sind die Spieldaten schon geladen, zaehlen nur Parameter, die
            # DIESE Waffe hat — ein Preset von einer anderen Spielversion
            # brachte sonst einen Override mit, zu dem es keinen Regler gibt
            # und der nie einen Patch erzeugt.
            allowed = self._iw_params.get(sid, WEAPON_PARAMS)
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in allowed and abs(float(v) - 1.0) > 1e-9}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.weapon_overrides[sid] = clean
        # Kaliberwechsel (Issue #6): nur Waffen und Kaliber uebernehmen, die
        # es in DIESER Installation gibt — ein Preset von einer anderen
        # Spielversion brachte sonst eine Wahl mit, die nie einen Patch
        # erzeugt. Sind die Spieldaten noch nicht geladen, sind beide
        # Listen leer und _iw_populate raeumt spaeter auf.
        for sid, caliber in (data.get("weapon_calibers") or {}).items():
            if not isinstance(caliber, str) or not caliber:
                continue
            if self._iw_categories and sid not in self._iw_categories:
                continue                      # Waffe gibt es hier nicht
            if self._iw_caliber_options and caliber not in self._iw_caliber_options:
                continue
            if self._iw_caliber and self._iw_caliber.get(sid) == caliber:
                continue                      # entspricht Vanilla
            self.weapon_calibers[sid] = caliber
        for species, params in (data.get("mutant_overrides") or {}).items():
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in ("hp", "speed", "damage", "regen")
                         and abs(float(v) - 1.0) > 1e-9}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.mutant_overrides[species] = clean
        for sid, params in (data.get("ammo_overrides") or {}).items():
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in AMMO_PARAMS and abs(float(v) - 1.0) > 1e-9}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.ammo_overrides[sid] = clean
        for sid, params in (data.get("armor_overrides") or {}).items():
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in ARMOR_PARAMS and abs(float(v) - 1.0) > 1e-9}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.armor_overrides[sid] = clean
        for key, value in (data.get("faction_relations") or {}).items():
            # Vanilla-gleiche und unbekannte Paare fliegen erst in
            # _if_populate raus (dort sind die Vanilla-Werte bekannt).
            try:
                self.faction_relations[str(key)] = int(round(float(value)))
            except (TypeError, ValueError):
                continue
        # Unbekannte SIDs koennen erst in _ia_populate weg (dort sind die
        # gueltigen Kaliber bekannt) -- genau wie beim Waffenbaum.
        # Bereits gebaute Waffen-Regler auf die geladenen Werte ziehen (und
        # entfallene Overrides zurueck auf ×1). Ohne gebaute Zeilen faellt das
        # auf die reine Info-Zeile zurueck, gilt also auch ohne Spieldaten.
        self._iw_refresh_all()
        self._ia_refresh_all()
        self._ir_refresh_all()
        self._if_refresh_all()
        self._im_refresh_all()
        # Avoid-Sperren wieder durchsetzen: das Preset kann Werte auf
        # gesperrte Regler geschrieben haben (werden gemerkt + auf Vanilla
        # zurueckgesetzt). Beim Start ohne Scan ist mod_conflicts leer ->
        # No-Op. Zieht auch die Scan-Punkte nach.
        self._apply_conflict_locks()

    def _on_close(self):
        # Ein wartendes Auto-Aufklappen wuerde sonst noch Widgets in einem
        # gerade zerstoerten Fenster bauen wollen.
        self._iw_cancel_expand()
        self._ia_cancel_expand()
        self._ir_cancel_expand()
        self._if_cancel_expand()
        self._im_cancel_expand()
        self._oc_cancel()
        self._save_ui_settings()
        self.destroy()

    # ------------------------------------------------------------ actions
    def _generate(self, out_pak: Path) -> bool:
        if self.gd is None:
            messagebox.showwarning(APP_TITLE, "Game data is not loaded yet.")
            return False
        s = self._collect()
        active = summarize(s)
        if not active:
            messagebox.showinfo(
                APP_TITLE,
                "Everything is set to vanilla – nothing to patch.")
            return False
        patches = build_patches(self.gd, s)
        # summarize() kennt nur die Settings, build_patches() auch die
        # Vanilla-Werte: ein Faktor auf einen Vanilla-0-Wert (viele
        # ArmorPiercingMod/CoverPiercingMod) oder ein Item-Gewicht ohne
        # angehakte Kategorie steht in "active", erzeugt aber keine Zeile.
        # Ohne diesen Riegel bekaeme repak einen leeren Ordner und der
        # Benutzer einen rohen Python-Traceback statt einer Erklaerung.
        if not patches:
            # Ursachen-Hinweis nur nennen, wenn er auch passen KANN — sonst
            # erklaert der Dialog dem Benutzer etwas ueber Munition, waehrend
            # in Wahrheit die Gewichts-Kategorien abgehakt sind.
            ammo_touched = bool(s.ammo_overrides) or any(
                abs(v - 1.0) > 1e-9 for v in (
                    s.ammo_damage_factor, s.ammo_piercing_factor,
                    s.ammo_armor_damage_factor, s.ammo_cover_factor))
            why = ("\n\nA factor on a value that is 0 in vanilla stays 0."
                   if ammo_touched else
                   "\n\nCheck that the categories belonging to your changed "
                   "sliders are still ticked.")
            messagebox.showinfo(
                APP_TITLE,
                "The values you changed have no effect on the game data – "
                "nothing to patch." + why)
            return False
        pakio.pack_mod(patches, out_pak,
                       root_files={MANIFEST_NAME:
                                   self._build_manifest(s, active)})

        debug_note = ""
        if self.debug_check.get():
            debug_root = out_pak.parent / f"{s.mod_name}_cfg"
            # Der Export darf die schon gebaute Pak nie als Fehlschlag
            # erscheinen lassen (Issue #5: Traceback statt Erfolgsmeldung).
            try:
                written = pakio.export_cfgs(patches, debug_root)
                debug_note = (f"\n\nDebug: {len(written)} patch .cfg files "
                              f"in\n{debug_root}")
            except OSError as exc:
                debug_note = ("\n\nDebug export failed (the pak itself is "
                              f"fine): {exc}")

        self._save_ui_settings()
        messagebox.showinfo(
            APP_TITLE,
            "Mod pak created:\n" + str(out_pak) + debug_note
            + "\n\nActive tweaks:\n– " + "\n– ".join(active))
        return True

    def _game_fingerprint(self) -> int | None:
        """Groesse von pakchunk0 als billiger Versions-Fingerabdruck
        (dasselbe Mass wie der Extraktions-Cache)."""
        try:
            if self.game_dir is not None:
                pak = (Path(self.game_dir) / "Stalker2" / "Content" / "Paks"
                       / "pakchunk0-Windows.pak")
                if pak.is_file():
                    return pak.stat().st_size
        except OSError:
            pass
        return None

    def _build_manifest(self, s, active: list[str]) -> str:
        """Eingebettetes Manifest: macht jede gebaute Pak nachvollziehbar
        (Support!) und ueber "Load preset ..." wieder ladbar."""
        return json.dumps({
            "manifest_version": 1,
            "tool": f"S2Tweaker {__version__}",
            "built": datetime.datetime.now().isoformat(timespec="seconds"),
            "game_pak_fingerprint": self._game_fingerprint(),
            "mod_name": s.mod_name,
            "active_tweaks": active,
            "ui_state": self._ui_state(),
        }, indent=2)

    def _import_pak(self, path: Path) -> None:
        """Einstellungen aus einer vom Tool gebauten Pak zurueckladen."""
        try:
            entries = pakio.list_pak(path)
        except Exception:
            messagebox.showerror(
                APP_TITLE, "That file could not be read as a .pak.")
            return
        if MANIFEST_NAME not in entries:
            messagebox.showinfo(
                APP_TITLE,
                "This pak carries no S2Tweaker manifest.\n\n"
                "Paks built with S2Tweaker 1.10.0 or newer embed their "
                "settings; older or foreign paks cannot be imported.")
            return
        import tempfile
        try:
            with tempfile.TemporaryDirectory(prefix="s2tweaker_import_") as tmp:
                pakio.unpack(path, Path(tmp), include=MANIFEST_NAME)
                data = json.loads(
                    (Path(tmp) / MANIFEST_NAME).read_text(encoding="utf-8"))
        except Exception:
            messagebox.showerror(
                APP_TITLE, "The manifest in this pak could not be read.")
            return
        state = data.get("ui_state")
        if not isinstance(state, dict):
            messagebox.showerror(
                APP_TITLE, "The manifest in this pak is incomplete.")
            return
        # Gleicher Weg wie ein Preset: erst Vanilla, dann anwenden
        self._reset_all()
        self._apply_ui_state(state)
        if self.gd is not None:
            self._iw_populate()
            self._ia_populate()
            self._ir_populate()
            self._if_populate()
            self._im_populate()
        self._apply_filter()
        name = str(data.get("mod_name") or "").strip()
        if name:
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, name)
        note = ""
        fp = data.get("game_pak_fingerprint")
        if fp and self._game_fingerprint() and fp != self._game_fingerprint():
            note = (" (built for a different game version - factors were "
                    "re-applied to your current values)")
        self._status_write(
            f"Loaded settings from {path.name}"
            f" - built {data.get('built', '?')} with "
            f"{data.get('tool', 'S2Tweaker')}{note}")

    def _out_name(self) -> str:
        s = self._collect()
        return f"zzz_{s.mod_name}_P.pak"

    def _generate_output(self):
        out = output_dir()
        try:
            out.mkdir(parents=True, exist_ok=True)
            target = out / self._out_name()
            if self._generate(target):
                self._status_write(f"Built: {target}")
        except Exception:
            messagebox.showerror(APP_TITLE, traceback.format_exc())

    def _generate_install(self):
        if self.game_dir is None:
            messagebox.showwarning(APP_TITLE, "No game folder selected.")
            return
        mods = game.mods_dir(self.game_dir)
        mods.mkdir(parents=True, exist_ok=True)
        try:
            if self._generate(mods / self._out_name()):
                self._status_write(f"Installed: {mods / self._out_name()}")
        except Exception:
            messagebox.showerror(APP_TITLE, traceback.format_exc())

    def _open_output(self):
        out = output_dir()
        try:
            out.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(out)  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", str(out)])
        except OSError:
            messagebox.showinfo(APP_TITLE, f"Output folder:\n{out}")

    def _remove_mod(self):
        if self.game_dir is None:
            return
        target = game.mods_dir(self.game_dir) / self._out_name()
        if target.is_file():
            target.unlink()
            self._status_write(f"Removed: {target}")
            messagebox.showinfo(APP_TITLE, f"Mod removed:\n{target}")
        else:
            messagebox.showinfo(APP_TITLE, f"No mod file found:\n{target}")


def run():
    app = App()
    app.mainloop()
