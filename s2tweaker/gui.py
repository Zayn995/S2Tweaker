"""S2Tweaker GUI (customtkinter, dunkel, englische Oberflaeche)."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __version__, game, pakio
from .gamedata import GameData
from .tweaks import (
    ALL_CATEGORIES,
    CATEGORY_LABELS,
    Settings,
    build_patches,
    summarize,
)

APP_TITLE = f"S2Tweaker {__version__} – S.T.A.L.K.E.R. 2 Mod Generator"


def app_dir() -> Path:
    """Ordner der EXE (gefroren) bzw. des Projekts (Entwicklung).

    Das Tool ist PORTABLE: Einstellungen, Cache und Output liegen alle
    neben der EXE — Ordner loeschen entfernt alles restlos.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def output_dir() -> Path:
    return app_dir() / "output"


def cache_dir() -> Path:
    return app_dir() / "cache"


SETTINGS_FILE = app_dir() / "settings.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

PAD = {"padx": 12, "pady": 3}


class SliderRow:
    """Label + Slider + Wertanzeige + Reset auf Vanilla."""

    def __init__(self, parent, label: str, from_: float, to: float, step: float,
                 default: float, fmt, tooltip: str = ""):
        self.default = default
        self.fmt = fmt
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", **PAD)
        self.label = ctk.CTkLabel(row, text=label, width=260, anchor="w")
        self.label.pack(side="left")
        steps = max(1, int(round((to - from_) / step)))
        self.slider = ctk.CTkSlider(
            row, from_=from_, to=to, number_of_steps=steps, command=self._changed
        )
        self.slider.pack(side="left", fill="x", expand=True, padx=8)
        self.value_label = ctk.CTkLabel(row, text="", width=110, anchor="e")
        self.value_label.pack(side="left")
        self.reset_btn = ctk.CTkButton(row, text="↺", width=28, command=self.reset)
        self.reset_btn.pack(side="left", padx=(6, 0))
        self.set(default)
        if tooltip:
            hint = ctk.CTkLabel(parent, text="   " + tooltip, anchor="w",
                                font=ctk.CTkFont(size=11), text_color="gray60")
            hint.pack(fill="x", padx=12)

    def _changed(self, _=None):
        value = self.get()
        vanilla = "  (vanilla)" if abs(value - self.default) < 1e-9 else ""
        self.value_label.configure(text=self.fmt(value) + vanilla)

    def get(self) -> float:
        return round(float(self.slider.get()), 4)

    def set(self, value: float):
        self.slider.set(value)
        self._changed()

    def reset(self):
        self.set(self.default)

    def set_state(self, state: str):
        self.slider.configure(state=state)
        self.reset_btn.configure(state=state)


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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1010x860")
        self.minsize(880, 640)

        self.gd: GameData | None = None
        self.game_dir: Path | None = None
        self.sliders: dict[str, SliderRow] = {}
        self.checks: dict[str, ctk.CTkCheckBox] = {}
        self.cat_checks: dict[str, ctk.CTkCheckBox] = {}
        self._msgs: "queue.Queue[tuple[str, str]]" = queue.Queue()

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

    # ------------------------------------------------------------ layout
    def _build_header(self):
        head = ctk.CTkFrame(self)
        head.pack(fill="x", padx=10, pady=(10, 4))
        self.game_label = ctk.CTkLabel(head, text="Game folder: searching ...", anchor="w")
        self.game_label.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        self.btn_confirm = ctk.CTkButton(
            head, text="✓ Confirm & load game data", width=200,
            fg_color="#2d6a3f", hover_color="#377f4c", command=self._confirm_game)
        self.btn_confirm.pack(side="right", padx=(4, 10), pady=8)
        self.btn_browse = ctk.CTkButton(head, text="Browse …", width=100,
                                        command=self._pick_game_dir)
        self.btn_browse.pack(side="right", padx=4, pady=8)

    def _section(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="x", pady=(8, 2), padx=4)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        return frame

    def _slider(self, parent, key: str, label: str, from_: float, to: float,
                step: float, default: float, fmt, tooltip: str = "") -> None:
        self.sliders[key] = SliderRow(parent, label, from_, to, step, default, fmt, tooltip)

    def _check(self, parent, key: str, label: str, tooltip: str = "") -> None:
        box = ctk.CTkCheckBox(parent, text=label)
        box.pack(anchor="w", **PAD)
        self.checks[key] = box
        if tooltip:
            ctk.CTkLabel(parent, text="      " + tooltip, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="gray60").pack(fill="x", padx=12)

    def _build_body(self):
        self.body = ctk.CTkScrollableFrame(self)
        self.body.pack(fill="both", expand=True, padx=10, pady=4)

        f = self._section("Player")
        self._slider(f, "hp", "Max health", 50, 1000, 10, 100, fmt_int)
        self._slider(f, "hp_regen", "Passive health regen (HP/s)", 0, 20, 0.5, 0, fmt_dec,
                     "Vanilla: no passive regen. NPCs use 1 HP/s.")
        self._slider(f, "sp", "Max stamina", 50, 1000, 10, 100, fmt_int)
        self._slider(f, "sp_regen", "Stamina regen (per second)", 0, 50, 1, 5, fmt_dec)
        self._slider(f, "fall", "Fall damage", 0, 100, 5, 100, fmt_pct,
                     "0 % = no fall damage.")
        self._slider(f, "move", "Movement speed (all gaits)", 50, 200, 5, 100, fmt_pct)
        self._slider(f, "jump", "Jump height", 50, 200, 5, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section("Stamina costs (per action)")
        self._slider(f, "st_sprint", "Sprint (incl. continuous drain)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_jump", "Jump", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_melee_l", "Melee attack (light)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_melee_s", "Melee attack (strong)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_butt", "Rifle butt strike", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_vault", "Vault / climb", 0, 200, 5, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section("Weight & inventory")
        self._slider(f, "carry", "Max carry weight (hard limit)", 20, 500, 5, 80, fmt_kg)
        self._slider(f, "penalty", "Overweight penalty starts at", 10, 500, 5, 50, fmt_kg,
                     "Below this weight: no slowdown at all. Stages scale up to the hard limit.")
        self._check(f, "no_overweight", "No overweight penalty at all",
                    "Removes the speed/stamina penalties entirely (between penalty start and hard limit).")
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
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section("Combat")
        self._slider(f, "pdmg", "Player damage (guns)", 0.25, 10, 0.25, 1, fmt_factor,
                     "Applied via difficulty multipliers, all difficulty levels.")
        self._slider(f, "headshot", "Player headshot damage", 0.25, 5, 0.25, 1, fmt_factor)
        self._slider(f, "npcdmg", "Human NPC damage (to you)", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "npchp", "Human NPC health", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "mhp", "Mutant health", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "mdmg", "Mutant damage", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "expl", "Explosion damage", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "dur", "Weapon & armor durability", 0.5, 10, 0.5, 1, fmt_factor,
                     "Weapons wear less per shot; armor takes more punishment.")
        self._slider(f, "jam", "Weapon jamming", 0, 2, 0.1, 1, fmt_factor,
                     "× 0 = weapons never jam.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section("Weapon handling")
        self._slider(f, "sway", "Scoped aim sway", 0, 100, 5, 100, fmt_pct,
                     "0 % = steady scopes. Iron-sight sway is animation-driven and not cfg-tweakable.")
        self._slider(f, "breath_drain", "Breath-hold drain", 0, 200, 5, 100, fmt_pct,
                     "0 % = hold breath forever while aiming.")
        self._slider(f, "breath_regen", "Breath recovery", 50, 400, 10, 100, fmt_pct)
        self._slider(f, "spread", "Weapon spread (bullet dispersion)", 0, 200, 5, 100, fmt_pct,
                     "0 % = laser accuracy (hip fire, aiming and first shot).")
        self._slider(f, "recoil", "Weapon recoil", 0, 200, 5, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section("World & survival")
        self._slider(f, "anomaly", "Anomaly damage", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "radiation", "Radiation accumulation", 0, 5, 0.25, 1, fmt_factor,
                     "× 0 = no radiation buildup.")
        self._slider(f, "bleeding", "Bleeding intensity", 0, 5, 0.25, 1, fmt_factor)
        self._slider(f, "hunger", "Hunger rate", 0, 300, 10, 100, fmt_pct,
                     "0 % = never get hungry.")
        self._slider(f, "sleep", "Sleepiness rate", 0, 300, 10, 100, fmt_pct,
                     "0 % = never get sleepy.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section("Economy & traders")
        self._slider(f, "trader_dur", "Traders buy gear from durability", 0, 100, 5, 40, fmt_pct,
                     "0 % = traders buy weapons/armor in any condition (vanilla: 40 %).")
        self._slider(f, "buyprice", "Trader buy prices (what you get)", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "sellprice", "Trader sell prices (what you pay)", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "repair", "Repair cost", 0, 200, 5, 100, fmt_pct,
                     "0 % = free repairs.")
        self._slider(f, "upgrade", "Upgrade cost", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "questreward", "Quest money rewards", 0.25, 10, 0.25, 1, fmt_factor)
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
        for row in self.sliders.values():
            row.set_state(state)
        for box in list(self.checks.values()) + list(self.cat_checks.values()):
            box.configure(state=state)

    def _set_status(self, text: str):
        self._msgs.put(("status", text))

    def _poll_msgs(self):
        """Nachrichten des Hintergrund-Threads im GUI-Thread verarbeiten."""
        try:
            while True:
                kind, payload = self._msgs.get_nowait()
                if kind == "status":
                    self.status.configure(text=payload)
                elif kind == "game_label":
                    self.game_label.configure(text=payload)
                elif kind == "ready":
                    self._set_busy(False)
                    self._set_body_state(True)
                    self.btn_confirm.configure(state="normal",
                                               text="↻ Reload game data")
                    self.btn_browse.configure(state="normal")
                elif kind == "loadfail":
                    self.btn_confirm.configure(state="normal")
                    self.btn_browse.configure(state="normal")
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
                f"{n_weap} weapons, {n_mut} mutant prototypes.")
            self._msgs.put(("ready", ""))
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
            movement_speed_factor=s["move"].get() / 100.0,
            jump_height_factor=s["jump"].get() / 100.0,
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
            player_damage_factor=s["pdmg"].get(),
            headshot_factor=s["headshot"].get(),
            npc_damage_factor=s["npcdmg"].get(),
            npc_hp_factor=s["npchp"].get(),
            mutant_hp_factor=s["mhp"].get(),
            mutant_damage_factor=s["mdmg"].get(),
            explosion_damage_factor=s["expl"].get(),
            durability_factor=s["dur"].get(),
            jamming_factor=s["jam"].get(),
            scope_sway_pct=s["sway"].get(),
            breath_drain_factor=s["breath_drain"].get() / 100.0,
            breath_regen_factor=s["breath_regen"].get() / 100.0,
            spread_factor=s["spread"].get() / 100.0,
            recoil_factor=s["recoil"].get() / 100.0,
            anomaly_damage_factor=s["anomaly"].get(),
            radiation_factor=s["radiation"].get(),
            bleeding_factor=s["bleeding"].get(),
            hunger_rate_factor=s["hunger"].get() / 100.0,
            sleepiness_rate_factor=s["sleep"].get() / 100.0,
            trader_min_durability_pct=s["trader_dur"].get(),
            trader_buy_price_factor=s["buyprice"].get(),
            trader_sell_price_factor=s["sellprice"].get(),
            repair_cost_factor=s["repair"].get() / 100.0,
            upgrade_cost_factor=s["upgrade"].get() / 100.0,
            quest_reward_factor=s["questreward"].get(),
        )

    def _reset_all(self):
        for slider in self.sliders.values():
            slider.reset()
        for box in self.checks.values():
            box.deselect()
        for box in self.cat_checks.values():
            box.select()

    def _save_ui_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "game_dir": str(self.game_dir) if self.game_dir else None,
                "mod_name": self.name_entry.get(),
                "sliders": {k: v.get() for k, v in self.sliders.items()},
                "checks": {k: bool(v.get()) for k, v in self.checks.items()},
                "cats": {k: bool(v.get()) for k, v in self.cat_checks.items()},
                "debug_cfg": bool(self.debug_check.get()),
            }
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

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
        for key, value in data.get("sliders", {}).items():
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
        if data.get("debug_cfg"):
            self.debug_check.select()

    def _on_close(self):
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
        pakio.pack_mod(patches, out_pak)

        debug_note = ""
        if self.debug_check.get():
            debug_root = out_pak.parent / f"{s.mod_name}_cfg"
            for rel, content in patches.items():
                target = debug_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            debug_note = f"\n\nDebug: {len(patches)} patch .cfg files in\n{debug_root}"

        self._save_ui_settings()
        messagebox.showinfo(
            APP_TITLE,
            "Mod pak created:\n" + str(out_pak) + debug_note
            + "\n\nActive tweaks:\n– " + "\n– ".join(active))
        return True

    def _out_name(self) -> str:
        s = self._collect()
        return f"zzz_{s.mod_name}_P.pak"

    def _generate_output(self):
        out = output_dir()
        try:
            out.mkdir(parents=True, exist_ok=True)
            target = out / self._out_name()
            if self._generate(target):
                self.status.configure(text=f"Built: {target}")
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
                self.status.configure(text=f"Installed: {mods / self._out_name()}")
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
            self.status.configure(text=f"Removed: {target}")
            messagebox.showinfo(APP_TITLE, f"Mod removed:\n{target}")
        else:
            messagebox.showinfo(APP_TITLE, f"No mod file found:\n{target}")


def run():
    app = App()
    app.mainloop()
