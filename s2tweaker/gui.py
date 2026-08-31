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
    AMMO_CALIBER_LABELS,
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


def presets_dir() -> Path:
    return app_dir() / "presets"


SETTINGS_FILE = app_dir() / "settings.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

PAD = {"padx": 12, "pady": 3}

# Bernstein: eine einzige Quelle fuer Suchtreffer, Warnhinweise und
# Override-Marker im Waffenbaum.
ACCENT = "#d9a648"


class SliderRow:
    """Label + Slider + Wertanzeige + Reset auf Vanilla."""

    def __init__(self, parent, label: str, from_: float, to: float, step: float,
                 default: float, fmt, tooltip: str = "", on_change=None):
        self.default = default
        self.fmt = fmt
        self.on_change = on_change
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
        self._orig_color = self.label.cget("text_color")
        self.set(default)
        if tooltip:
            hint = ctk.CTkLabel(parent, text="   " + tooltip, anchor="w",
                                font=ctk.CTkFont(size=11), text_color="gray60")
            hint.pack(fill="x", padx=12)

    def _changed(self, _=None):
        value = self.get()
        vanilla = "  (vanilla)" if abs(value - self.default) < 1e-9 else ""
        self.value_label.configure(text=self.fmt(value) + vanilla)
        if self.on_change is not None:
            self.on_change()

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

    def set_highlight(self, mode: str):
        """Suchfilter: 'match' = hervorheben, 'dim' = abdunkeln."""
        if mode == "match":
            color = ACCENT
        elif mode == "dim":
            color = "gray35"
        else:
            color = self._orig_color
        self.label.configure(text_color=color)


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


class IwWeaponRow:
    """Aufklappbare Zeile EINER Waffe im Overrides-Baum.

    Die 8 Regler entstehen erst beim ERSTEN Aufklappen (lazy) und werden
    danach wiederverwendet. Einzige Wahrheit bleibt app.weapon_overrides —
    eine nie geoeffnete Waffe hat gar keine Widgets, die veralten koennten.
    """

    def __init__(self, app, parent, sid: str, cat: str):
        self.app = app
        self.sid = sid
        self.cat = cat
        self.body = None                       # CTkFrame, erst bei build()
        self.sliders: dict[str, SliderRow] = {}
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
            for param in WEAPON_PARAMS:
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
        self.load_values()
        self.app._iw_after_change(self.cat)

    # -------------------------------------------------------- Darstellung
    def refresh(self):
        n = len(self.app.weapon_overrides.get(self.sid, {}))
        arrow = "▾" if self.expanded else "▸"
        # "N of 8 factors" statt "N overrides": die Kategorie-Kopfzeile zaehlt
        # WAFFEN, diese Zeile zaehlt PARAMETER — gleiche Zahl, andere Einheit.
        mark = f"     ●  {n} of {len(WEAPON_PARAMS)} factors changed" if n else ""
        self.btn.configure(text=f"{arrow}  {self.sid}{mark}")
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
        self._apply_color(len(self.app.weapon_overrides.get(self.sid, {})))

    def set_state(self, state: str):
        # Frueh raus, wenn sich nichts aendert: bei 79 offenen Waffen haengen
        # sonst 632 Regler an einem einzigen "Reload"-Klick.
        if state == self._state:
            return
        self._state = state
        self.btn.configure(state=state)
        if self.reset_btn is not None:
            self.reset_btn.configure(state=state)
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
        n_over = sum(1 for sid in self.sids
                     if sid in self.app.weapon_overrides)
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
        # Mutanten-Overrides pro Art: {Art: {hp/speed/damage: faktor}}
        self.mutant_overrides: dict[str, dict[str, float]] = {}
        self.mut_sliders: dict[str, SliderRow] = {}
        self._mut_current: str | None = None
        self._mut_loading = False
        self._mut_species: list[str] = []
        self._iw_loading = False
        self._iw_categories: dict[str, str] = {}
        self._iw_share: dict[str, list[str]] = {}  # Waffen mit geteiltem CWS-Struct
        self._iw_blocks: dict[str, IwCategoryBlock] = {}
        self._iw_auto_opened: set[str] = set()     # von der Suche aufgeklappt
        # Kategorie-Knoepfe im Abschnitt "Weapon categories": {cat: (btn, label, farbe)}
        self._wcat_btns: dict[str, tuple] = {}
        self._wcat_notes: dict[str, str] = {}   # Suchzusatz je Kategorie-Kopf
        self._iw_expand_job: str | None = None  # laufender after()-Auftrag
        # Einzelmunitions-Overrides: {Ammo-SID: {param: faktor}} (nur != 1.0)
        self.ammo_overrides: dict[str, dict[str, float]] = {}
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

    def _set_icon(self):
        try:
            if getattr(sys, "frozen", False):
                ico = Path(sys._MEIPASS) / "icon.ico"  # type: ignore[attr-defined]
            else:
                ico = app_dir() / "assets" / "icon.ico"
            if ico.is_file():
                self.iconbitmap(str(ico))
        except Exception:
            pass

    # ------------------------------------------------------------ layout
    def _build_header(self):
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
        # Breit genug, damit der Platzhaltertext ganz hineinpasst
        self.search_entry = ctk.CTkEntry(head, width=230,
                                         placeholder_text="🔍 Find a slider, weapon or ammo …")
        self.search_entry.pack(side="right", padx=4, pady=8)
        # Der Pfad-Text wird ZULETZT gepackt und nimmt sich nur den Rest:
        # sonst draengt ein langer Spielpfad die Knoepfe und das Suchfeld
        # zusammen und schneidet den Platzhaltertext ab.
        self.game_label.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._apply_filter)

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(8, 2), padx=4)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        return frame

    def _slider(self, parent, key: str, label: str, from_: float, to: float,
                step: float, default: float, fmt, tooltip: str = "") -> None:
        self.sliders[key] = SliderRow(parent, label, from_, to, step, default, fmt, tooltip)
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
        # Verwaiste Overrides (Spiel-Update, andere Installation) verwerfen
        self.weapon_overrides = {
            sid: params for sid, params in self.weapon_overrides.items()
            if sid in self._iw_categories
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
        if self.weapon_overrides:
            text = "Overrides set for: " + ", ".join(sorted(self.weapon_overrides))
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
            sid_hits = [sid for sid in block.sids if query in sid.lower()]
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
            sid_hits = [sid for sid in block.sids if query in sid.lower()]
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

    # -------------------------------------------- Mutanten-Overrides
    def _mut_populate(self):
        if self.gd is None:
            return
        species = sorted({f for f in (
            self.gd.mutant_faction(sid) for sid in self.gd.mutants()) if f})
        self._mut_species = species
        self.mutant_overrides = {
            sp: params for sp, params in self.mutant_overrides.items()
            if sp in species
        }
        if not species:
            return
        self.mut_menu.configure(values=species, state="normal")
        current = (self._mut_current if self._mut_current in species
                   else ("Bloodsucker" if "Bloodsucker" in species else species[0]))
        self.mut_menu.set(current)
        self._mut_select(current)

    def _mut_select(self, species: str):
        self._mut_current = species
        if self.mut_menu.get() != species:
            self.mut_menu.set(species)
        self._mut_loading = True
        stored = self.mutant_overrides.get(species, {})
        for param, slider_row in self.mut_sliders.items():
            slider_row.set(stored.get(param, 1.0))
        self._mut_loading = False
        self._mut_update_info()

    def _mut_changed(self):
        if self._mut_loading or self._mut_current is None:
            return
        values = {p: row.get() for p, row in self.mut_sliders.items()}
        values = {p: v for p, v in values.items() if abs(v - 1.0) > 1e-9}
        if values:
            self.mutant_overrides[self._mut_current] = values
        else:
            self.mutant_overrides.pop(self._mut_current, None)
        self._mut_update_info()

    def _mut_update_info(self):
        if self.mutant_overrides:
            self.mut_info.configure(
                text="Overrides: " + ", ".join(sorted(self.mutant_overrides)))
        else:
            self.mut_info.configure(text="No species overrides set.")

    def _check(self, parent, key: str, label: str, tooltip: str = "") -> None:
        box = ctk.CTkCheckBox(parent, text=label)
        box.pack(anchor="w", **PAD)
        self.checks[key] = box
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
        self._slider(f, "hp", "Max health", 50, 1000, 10, 100, fmt_int)
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
        self._slider(f, "dur_armor", "Armor durability", 0.5, 10, 0.5, 1, fmt_factor,
                     "Armor takes more punishment before breaking.")
        self._slider(f, "jam", "Weapon jamming", 0, 2, 0.1, 1, fmt_factor,
                     "× 0 = weapons never jam.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Mutants")
        self._slider(f, "mhp", "Mutant health (all species)", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "mdmg", "Mutant damage (all species)", 0.1, 5, 0.1, 1, fmt_factor,
                     "Via difficulty multiplier – species overrides below "
                     "scale the individual attack values on top.")
        self._slider(f, "mspeed", "Mutant speed (all species)", 0.25, 2, 0.25, 1, fmt_factor,
                     "Walk/run/sprint speed of every mutant species.")
        self._slider(f, "mhearing", "Mutant hearing range", 10, 200, 5, 100, fmt_pct,
                     "All mutant species share one hearing sensor.")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", **PAD)
        ctk.CTkLabel(row, text="Species override", width=260, anchor="w").pack(side="left")
        self.mut_menu = ctk.CTkOptionMenu(
            row, values=["– load game data first –"], command=self._mut_select,
            state="disabled", width=220, dynamic_resizing=False)
        self.mut_menu.set("– load game data first –")
        self.mut_menu.pack(side="left", padx=8)
        self.mut_info = ctk.CTkLabel(row, text="", anchor="w", justify="left",
                                     wraplength=420, text_color="gray60")
        self.mut_info.pack(side="left", padx=8)
        for param, label in (("hp", "Health"), ("speed", "Speed"), ("damage", "Damage")):
            self.mut_sliders[param] = SliderRow(
                f, label, 0.25, 5, 0.25, 1, fmt_factor,
                on_change=self._mut_changed)
        ctk.CTkLabel(
            f, text="   ×1 (vanilla) = no override – the global mutant "
                    "sliders above still apply to this species. Damage "
                    "overrides scale each attack individually (Poltergeist "
                    "& Rat deal damage indirectly – no effect there).",
            anchor="w", font=ctk.CTkFont(size=11),
            text_color="gray60").pack(fill="x", padx=12)
        self._slider(f, "bs_cloak", "Bloodsucker cloaking speed", 0.25, 4, 0.25, 1, fmt_factor,
                     "× 4 = bloodsuckers vanish almost instantly.")
        self._slider(f, "bs_uncloak", "Bloodsucker uncloak from damage", 0, 20, 1, 1, fmt_factor,
                     "Higher = hitting them breaks the cloak much harder. "
                     "× 0 = damage never reveals them.")
        ctk.CTkLabel(f, text="", height=2).pack()

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
        self._slider(f, "ap_carry", "Armor carry-weight bonuses", 0, 300, 25, 100, fmt_pct,
                     "Exoskeleton & armor/upgrade carry bonuses. "
                     "0 % = armor grants no extra carry weight.")
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

        body = self._tab("Weapons")
        f = self._section(body, "Weapon handling (global – all weapons)")
        self._slider(f, "sway", "Scoped aim sway", 0, 100, 5, 100, fmt_pct,
                     "0 % = steady scopes. Iron-sight sway is animation-driven and not cfg-tweakable.")
        self._slider(f, "breath_drain", "Breath-hold drain", 0, 200, 5, 100, fmt_pct,
                     "0 % = hold breath forever while aiming.")
        self._slider(f, "breath_regen", "Breath recovery", 50, 400, 10, 100, fmt_pct)
        self._slider(f, "spread", "Weapon spread (bullet dispersion)", 0, 200, 5, 100, fmt_pct,
                     "0 % = laser accuracy (hip fire, aiming and first shot).")
        self._slider(f, "recoil", "Weapon recoil", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "wrange", "Weapon effective range", 50, 200, 10, 100, fmt_pct,
                     "Scales effective fire distance and damage drop-off "
                     "start/length together.")
        self._slider(f, "wbleed", "Weapon bleeding", 0, 300, 25, 100, fmt_pct,
                     "Bleeding chance and intensity your shots inflict. "
                     "0 % = your bullets never cause bleeding.")
        self._slider(f, "adsmove", "ADS movement speed", 50, 200, 10, 100, fmt_pct,
                     "How fast you move while aiming down sights "
                     "(vanilla varies 58–150 % of run speed per weapon).")
        self._slider(f, "magazine", "Magazine size", 50, 300, 25, 100, fmt_pct,
                     "Scales weapon base capacity AND all magazine "
                     "attachments (launchers never drop below 1 round).")
        self._slider(f, "melee", "Melee damage (knife & butt strike)", 25, 400, 25, 100, fmt_pct)
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
        self._slider(f, "rain", "Rain & storm frequency", 0, 300, 25, 100, fmt_pct,
                     "Weight of rainy/stormy/thunder weather in the rotation. "
                     "0 % = practically always dry.")
        self._slider(f, "emission", "Emission frequency", 25, 400, 25, 100, fmt_pct,
                     "How often emissions build up (quest-controlled "
                     "no-emission zones stay untouched).")
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
        self._slider(f, "detector", "Detector & scanner range", 50, 300, 10, 100, fmt_pct,
                     "Artifact detectors (Echo, Bear, Veles, Gilka), the "
                     "anomaly beeper and the searchpoint scanner.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Economy")
        f = self._section(body, "Economy & traders")
        self._slider(f, "trader_dur", "Traders buy gear from durability", 0, 100, 5, 40, fmt_pct,
                     "0 % = traders buy weapons/armor in any condition (vanilla: 40 %).")
        self._slider(f, "buyprice", "Trader buy prices (what you get)", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "sellprice", "Trader sell prices (what you pay)", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "repair", "Repair cost", 0, 200, 5, 100, fmt_pct,
                     "0 % = free repairs.")
        self._slider(f, "upgrade", "Upgrade cost", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "questreward", "Quest money rewards", 0.25, 10, 0.25, 1, fmt_factor)
        self._slider(f, "fasttravel", "Fast travel cost", 0, 400, 25, 100, fmt_pct,
                     "0 % = guides take you anywhere for free.")
        self._slider(f, "restock", "Trader restock time", 25, 400, 25, 100, fmt_pct,
                     "How long traders take to refresh their stock "
                     "(vanilla: 8 h to 7 days depending on the trader; "
                     "day-based traders can't go below 1 day).")
        self._slider(f, "price_weapon", "Weapon prices", 0.25, 4, 0.25, 1, fmt_factor,
                     "Per-category price multipliers – these stack with the "
                     "trader buy/sell sliders above.")
        self._slider(f, "price_armor", "Armor prices", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "price_ammo", "Ammo prices", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "price_artifact", "Artifact prices", 0.25, 4, 0.25, 1, fmt_factor)
        self._slider(f, "price_consumable", "Consumable prices", 0.25, 4, 0.25, 1, fmt_factor)
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
        for row in self.mut_sliders.values():
            row.set_state(state)
        for box in list(self.checks.values()) + list(self.cat_checks.values()):
            box.configure(state=state)
        self.iw_clear_btn.configure(state=state)
        for block in self._iw_blocks.values():
            block.set_state(state)
        self.ia_clear_btn.configure(state=state)
        for block in self._ia_blocks.values():
            block.set_state(state)
        # Dropdown nur aktivieren, wenn die Liste geladen ist
        self.mut_menu.configure(
            state=state if (enabled and self._mut_species) else "disabled")

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
                    self._iw_populate()
                    self._ia_populate()
                    self._mut_populate()
                    self._set_busy(False)
                    self._set_body_state(True)
                    # Laufende Suche auf den frisch gebauten Baum anwenden
                    self._apply_filter()
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
            aim_punch_factor=s["aimpunch"].get() / 100.0,
            npc_damage_factor=s["npcdmg"].get(),
            npc_hp_factor=s["npchp"].get(),
            npc_accuracy_factor=s["npc_acc"].get(),
            npc_vision_factor=s["npc_vision"].get() / 100.0,
            npc_hearing_factor=s["npc_hearing"].get() / 100.0,
            npc_reaction_factor=s["npc_reaction"].get() / 100.0,
            npc_grenade_factor=s["npc_grenades"].get() / 100.0,
            npc_no_heal=bool(self.checks["npc_no_heal"].get()),
            max_agents_factor=s["alife_agents"].get() / 100.0,
            spawn_distance_factor=s["alife_distance"].get() / 100.0,
            mutant_hp_factor=s["mhp"].get(),
            mutant_damage_factor=s["mdmg"].get(),
            mutant_speed_factor=s["mspeed"].get(),
            mutant_hearing_factor=s["mhearing"].get() / 100.0,
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
            weapon_range_factor=s["wrange"].get() / 100.0,
            weapon_bleeding_factor=s["wbleed"].get() / 100.0,
            ads_speed_factor=s["adsmove"].get() / 100.0,
            magazine_factor=s["magazine"].get() / 100.0,
            melee_damage_factor=s["melee"].get() / 100.0,
            ammo_damage_factor=s["ammo_dmg"].get() / 100.0,
            ammo_piercing_factor=s["ammo_ap"].get() / 100.0,
            ammo_armor_damage_factor=s["ammo_ad"].get() / 100.0,
            ammo_cover_factor=s["ammo_cover"].get() / 100.0,
            weapon_category_factors=self._collect_weapon_cats(),
            weapon_overrides={sid: dict(v)
                              for sid, v in self.weapon_overrides.items()},
            ammo_overrides={sid: dict(v)
                            for sid, v in self.ammo_overrides.items()},
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
            rain_factor=s["rain"].get() / 100.0,
            emission_factor=s["emission"].get() / 100.0,
            artifact_effect_factor=s["art_effect"].get() / 100.0,
            artifact_radiation_factor=s["art_radiation"].get() / 100.0,
            artifact_spawn_factor=s["art_spawn"].get() / 100.0,
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
        if query:
            if self._status_before_search is None:
                self._status_before_search = self.status.cget("text")
            if counts:
                self.status.configure(text="Matches: " + ", ".join(
                    f"{tab} ({n})" for tab, n in counts.items()))
            else:
                self.status.configure(
                    text="No slider, weapon or ammo matches your search.")
        elif self._status_before_search is not None:
            # Suchfeld geleert: alte Meldung zurueck statt eines stehen
            # gebliebenen "No slider, weapon or ammo matches your search."
            self.status.configure(text=self._status_before_search)
            self._status_before_search = None

    def _reset_all(self):
        for slider in self.sliders.values():
            slider.reset()
        for box in self.checks.values():
            box.deselect()
        for box in self.cat_checks.values():
            box.select()
        self._iw_clear_all()
        self._ia_clear_all()
        self.mutant_overrides.clear()
        if self._mut_current is not None:
            self._mut_select(self._mut_current)

    def _ui_state(self) -> dict:
        """Kompletter Regler-Zustand (fuer settings.json UND Presets)."""
        return {
            "sliders": {k: v.get() for k, v in self.sliders.items()},
            "checks": {k: bool(v.get()) for k, v in self.checks.items()},
            "cats": {k: bool(v.get()) for k, v in self.cat_checks.items()},
            "weapon_overrides": self.weapon_overrides,
            "ammo_overrides": self.ammo_overrides,
            "mutant_overrides": self.mutant_overrides,
        }

    def _save_ui_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "game_dir": str(self.game_dir) if self.game_dir else None,
                "mod_name": self.name_entry.get(),
                "debug_cfg": bool(self.debug_check.get()),
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
            title="Load preset", initialdir=presets_dir(),
            filetypes=[("S2Tweaker preset", "*.json")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            messagebox.showerror(APP_TITLE, "Could not read that preset file.")
            return
        self.weapon_overrides.clear()
        self.ammo_overrides.clear()
        self.mutant_overrides.clear()
        self._apply_ui_state(data)
        if self.gd is not None:
            self._iw_populate()
            self._ia_populate()
            self._mut_populate()
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
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in WEAPON_PARAMS and abs(float(v) - 1.0) > 1e-9}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.weapon_overrides[sid] = clean
        for species, params in (data.get("mutant_overrides") or {}).items():
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in ("hp", "speed", "damage")
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
        # Unbekannte SIDs koennen erst in _ia_populate weg (dort sind die
        # gueltigen Kaliber bekannt) -- genau wie beim Waffenbaum.
        # Bereits gebaute Waffen-Regler auf die geladenen Werte ziehen (und
        # entfallene Overrides zurueck auf ×1). Ohne gebaute Zeilen faellt das
        # auf die reine Info-Zeile zurueck, gilt also auch ohne Spieldaten.
        self._iw_refresh_all()
        self._ia_refresh_all()

    def _on_close(self):
        # Ein wartendes Auto-Aufklappen wuerde sonst noch Widgets in einem
        # gerade zerstoerten Fenster bauen wollen.
        self._iw_cancel_expand()
        self._ia_cancel_expand()
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
