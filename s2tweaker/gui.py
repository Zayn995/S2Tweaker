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
import weakref
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __version__, faq, game, modscan, pakio, theme
from .gamedata import GameData
from .tweaks import (
    ALL_CATEGORIES,
    input_ini,
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

# Werkseinstellung JETZT festhalten (nach set_default_color_theme, vor dem
# ersten Widget): "Default" fuehrt sonst nicht exakt hierher zurueck.
theme.snapshot()
# Und sofort das Standard-Design setzen — schwarzer Grund, dunkle Karten.
theme._theme_defaults(theme.get(theme.DEFAULT_NAME))

# Farben, die das Design mitzieht. Modul-Globale, weil sie an rund 60
# Stellen beim BAUEN der Widgets gelesen werden; _set_theme bindet sie neu.
PANEL = theme.get(theme.DEFAULT_NAME)["panel"]     # Karten
PANEL2 = theme.get(theme.DEFAULT_NAME)["panel2"]   # zweite Ebene
PANEL2_HOVER = theme.get(theme.DEFAULT_NAME)["panel2_hover"]
MUTED = theme.get(theme.DEFAULT_NAME)["secondary"]  # Erklaerzeilen

# --- Systemfarben: in JEDEM Design gleich (theme.py ist die Quelle) ------
# Gruen = bereit/erfolgreich, Rot = zerstoerend, Bernstein = Warnung. Ohne
# diese feste Ebene waere im Duty-Design ein roter "Remove from ~mods" nicht
# mehr von einem roten Bestaetigen-Knopf zu unterscheiden.
OK_GREEN = theme.SUCCESS
OK_GREEN_HOVER = theme.SUCCESS_HOVER
BAD_RED = theme.DANGER
BAD_RED_HOVER = theme.DANGER_HOVER
WARN_AMBER = theme.WARNING
OK_BORDER = theme.SUCCESS_BORDER
BAD_BORDER = theme.DANGER_BORDER
ATTENTION = theme.ATTENTION
ATTENTION_HOVER = theme.ATTENTION_HOVER
ATTENTION_BORDER = theme.ATTENTION_BORDER
SYS_BORDER = theme.SYSTEM_BORDER_WIDTH

# Grundschrift eine Stufe groesser (Besitzer 06.09.: "Schrift allgemein ein
# wenig groesser"). Muss VOR dem ersten Widget stehen: CTkFont() liest die
# Groesse beim Erzeugen aus dem Thema.
ctk.ThemeManager.theme["CTkFont"]["size"] = 14   # war 13
# Die ausdruecklich gesetzten Groessen im Rest der Datei (Erklaerungszeilen,
# Baum-Zeilen, Ueberschriften) wurden im selben Zug um genau 1 angehoben,
# damit das Groessenverhaeltnis untereinander gleich bleibt.

PAD = {"padx": 12, "pady": 3}

# Akzent des aktiven Designs: Suchtreffer, Override-Marker im Waffenbaum,
# "Changed only". WARNUNGEN benutzen ihn NICHT mehr — die haben mit
# WARN_AMBER ihre eigene, feste Farbe, damit eine Warnung in jedem Design
# als Warnung erkennbar bleibt.
ACCENT = theme.DEFAULT_ACCENT

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
    "protection": "Physical protection",
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
            fg_color="transparent", hover_color=PANEL2_HOVER, font=font_q,
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


# Schrittweiten, die auf einer Skala "rund" aussehen: 1, 2, 2.5 und 5 mal
# einer Zehnerpotenz. In 1/10000-Einheiten, damit alles ganzzahlig bleibt.
_NICE_STEPS = sorted(m * 10 ** e for e in range(0, 10)
                     for m in (1, 2, 25, 5) if m * 10 ** e <= 10 ** 9)


def grid_steps(lo: float, hi: float, default: float, step: float) -> int:
    """Anzahl Rasten fuer die Schiene — so, dass der VANILLA-WERT auf einer
    Raste liegt.

    customtkinter kennt keine Schrittweite, sondern nur eine Anzahl Rasten:
    es rastet auf lo + k*(hi-lo)/n. Geht (hi-lo)/Schritt nicht glatt auf,
    liegt der Vanilla-Wert zwischen zwei Rasten und ist mit der Maus nicht
    mehr einstellbar — ein neu gestartetes Werkzeug wuerde dann schon ohne
    Zutun des Benutzers patchen (gemessen 06.09.: 74 von 376 Reglern).
    Darum wird der gewuenschte Schritt hier auf den naechstkleineren
    verkleinert, der sowohl in die Spanne als auch genau auf den
    Vanilla-Wert passt; runde Schritte (0.05, 5, 10 ...) haben Vorrang."""
    span = hi - lo
    if span <= 0 or step <= 0:
        return 1
    unit = 10000                      # Rechnen in 1/10000, alles ganzzahlig
    span_i = int(round(span * unit))
    off_i = int(round((default - lo) * unit))
    if span_i <= 0:
        return 1
    # Groesster Schritt, der Spanne UND Vanilla-Wert trifft
    base = span_i if off_i <= 0 or off_i >= span_i else math.gcd(span_i, off_i)
    want = max(1, int(round(step * unit)))
    fits = [d for d in _NICE_STEPS if d <= want and base % d == 0]
    if fits:
        return max(1, span_i // fits[-1])
    # Kein runder Teiler: den groessten beliebigen Teiler <= want nehmen
    for k in range(max(1, -(-base // want)), base + 1):
        if base % k == 0:
            return max(1, span_i // (base // k))
    return max(1, span_i)


class SliderRow:
    """Label + Slider + Zahlenfeld + Wertanzeige + Reset auf Vanilla.

    Der Wert wird SELBST gehalten (`self._value`), nicht aus der Schiene
    gelesen. Nur so kann das Zahlenfeld Werte zwischen zwei Rasten
    annehmen ("custom Zahlen") und der Vanilla-Wert exakt getroffen werden.
    Die Schiene zeigt dann die naechstgelegene Raste — der gemeldete Wert
    bleibt der eingetippte."""

    # Scrollrad-Schalter (Besitzer 06.09.: "scrollen im Menue ohne
    # ausversehen slider verschieben"). customtkinter haengt das Mausrad an
    # die Schiene SELBST; das Blaettern der Seite kommt dagegen aus einer
    # bind_all-Bindung des Scroll-Rahmens. Loesen wir also nur die Bindung
    # der Schiene, bleibt das Blaettern erhalten und nur das versehentliche
    # Verstellen hoert auf. Klassenweit, damit auch die erst spaeter
    # aufgeklappten Baum-Regler (Waffen, Munition ...) sofort mitziehen.
    # Startwert False: beim ersten Start blaettert das Rad NUR, es verstellt
    # keinen Regler (Besitzer 06.09., Praezisierung: "das mousewheel soll
    # beim ersten start automatisch keine slider verschieben und rot sein.
    # Wenn man es aktiviert geht beides scrollen und slider moven").
    _wheel_enabled = False
    _instances: "weakref.WeakSet" = weakref.WeakSet()

    @classmethod
    def set_wheel_enabled(cls, enabled: bool) -> None:
        cls._wheel_enabled = bool(enabled)
        for row in list(cls._instances):
            try:
                row._apply_wheel()
            except Exception:
                pass          # Zeile schon zerstoert (Baum wieder zugeklappt)

    def _apply_wheel(self) -> None:
        canvas = self.slider._canvas
        handler = (self.slider._mouse_scroll_event if SliderRow._wheel_enabled
                   else self._wheel_scrolls_page)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(seq, handler)

    def _scroll_frame(self):
        """Der scrollbare Rahmen, in dem diese Zeile liegt (einmal gesucht)."""
        if self._scroller is None:
            widget = self.row
            while widget is not None:
                if isinstance(widget, ctk.CTkScrollableFrame):
                    self._scroller = widget
                    break
                widget = getattr(widget, "master", None)
        return self._scroller

    def _wheel_scrolls_page(self, event):
        """Rad ueber einem Regler bei ausgeschaltetem Schalter: die SEITE
        bewegen statt des Reglers.

        Das muss von Hand sein: customtkinter laesst ueber einem CTkSlider
        gar nicht blaettern (`_check_if_valid_scroll` liefert fuer alles
        unterhalb eines Reglers False, weil dort normalerweise der Regler
        das Rad bekommt). Ohne diese Zeilen taete das Rad ueber einem
        Regler nach dem Loesen der Bindung schlicht NICHTS."""
        frame = self._scroll_frame()
        if frame is None:
            return "break"
        canvas = frame._parent_canvas
        if canvas.yview() != (0.0, 1.0):
            if getattr(event, "num", 0) in (4, 5):
                canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
            else:
                canvas.yview("scroll", -int(event.delta / 6), "units")
        return "break"

    def __init__(self, parent, label: str, from_: float, to: float, step: float,
                 default: float, fmt, tooltip: str = "", on_change=None,
                 log: bool = False):
        self.default = default
        self.fmt = fmt
        self.on_change = on_change
        self._value = float(default)
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
        self._typing = False                 # Zahlenfeld hat gerade den Fokus
        self._scroller = None                # scrollbarer Rahmen (lazy)
        self.dot: ctk.CTkLabel | None = None
        self._dot_tip = ""
        # wraplength: ohne das schnitt der laengste Reglername ("Handling
        # upgrades (aim time, ADS move, sway, draw, recovery, capacity)")
        # bei 260 px einfach ab. Jetzt bricht er in eine zweite Zeile um.
        self.label = ctk.CTkLabel(row, text=label, width=260, anchor="w",
                                  justify="left", wraplength=255)
        self.label.pack(side="left")
        if self.log:
            # Logarithmische Schiene (GitHub #4 "Higher health value"): feine
            # Schritte nahe Vanilla, oben bis 100000. Bewusst OHNE
            # number_of_steps: CTkSlider.set() rastet sonst auf Log-Schritte
            # und aus set(250) wuerde 251 - get() rundet stattdessen auf
            # 3 signifikante Stellen.
            self.slider = ctk.CTkSlider(
                row, from_=math.log10(self.lo), to=math.log10(self.hi),
                command=self._on_rail
            )
            grid = 1.0
        else:
            steps = grid_steps(self.lo, self.hi, float(default), step)
            self.slider = ctk.CTkSlider(
                row, from_=from_, to=to, number_of_steps=steps, command=self._on_rail
            )
            grid = (self.hi - self.lo) / steps
        # Kennt die Schiene nur ganze Zahlen (Sekunden, Slots, Prozent),
        # dann rundet auch das Zahlenfeld — sonst stuende dort 3,7, waehrend
        # die Anzeige daneben "4" meldet.
        self._whole = (grid >= 1.0 and float(grid).is_integer()
                       and all(float(v).is_integer()
                               for v in (self.lo, self.hi, default)))
        self.slider.pack(side="left", fill="x", expand=True, padx=8)
        self.value_label = ctk.CTkLabel(row, text="", width=110, anchor="e")
        self.value_label.pack(side="left")
        # Zahlenfeld fuer eigene Werte (Besitzer 06.09.: "boxen hinter den
        # slidern um custom zahlen einzugeben"). Komma und Punkt gelten
        # beide als Dezimaltrenner.
        self.entry = ctk.CTkEntry(row, width=62, justify="right")
        self.entry.pack(side="left", padx=(6, 0))
        self.entry.bind("<FocusIn>", self._entry_focus)
        self.entry.bind("<Return>", self._entry_apply)
        self.entry.bind("<KP_Enter>", self._entry_apply)
        self.entry.bind("<FocusOut>", self._entry_apply)
        self.entry.bind("<Escape>", self._entry_cancel)
        self.reset_btn = ctk.CTkButton(row, text="↺", width=28, command=self.reset)
        self.reset_btn.pack(side="left", padx=(6, 0))
        self._orig_color = self.label.cget("text_color")
        SliderRow._instances.add(self)
        self._apply_wheel()
        self.set(default)
        if tooltip:
            # wraplength wie bei Checkboxen und Warnhinweisen: die
            # Erklaerzeilen der Regler waren als EINZIGE ohne Umbruch und
            # wurden am rechten Rand mitten im Wort abgeschnitten.
            hint = ctk.CTkLabel(parent, text="   " + tooltip, anchor="w",
                                justify="left", wraplength=780,
                                font=ctk.CTkFont(size=12), text_color=MUTED)
            hint.pack(fill="x", padx=12)

    def _on_rail(self, _=None):
        """Die Schiene wurde gezogen — ihr Rastwert ist jetzt der Wert."""
        if self.log:
            value = 10.0 ** float(self.slider.get())
            mag = 10.0 ** math.floor(math.log10(max(value, 1e-9)))
            value = round(value / mag * 100.0) / 100.0 * mag   # 3 signifikante Stellen
        else:
            value = float(self.slider.get())
        self._value = round(min(self.hi, max(self.lo, value)), 4)
        self._changed()

    def _changed(self, _=None):
        value = self.get()
        vanilla = "  (vanilla)" if abs(value - self.default) < 1e-9 else ""
        lock = "  \U0001f512" if self.locked else ""
        self.value_label.configure(text=self.fmt(value) + vanilla + lock)
        self._entry_show()
        if self.conflict_mods:
            self._update_dot()
        if self.on_change is not None:
            self.on_change()

    # ------------------------------------------------------- Zahlenfeld
    def _entry_focus(self, _=None):
        self._typing = True

    def _entry_cancel(self, _=None):
        self._typing = False
        self._entry_show()

    def _entry_show(self, _=None):
        """Feld auf den aktuellen Wert setzen — nicht waehrend des Tippens,
        sonst wird die Eingabe unter den Fingern ersetzt."""
        if self._typing:
            return
        text = f"{self.get():g}"
        if self.entry.get() == text:
            return
        # Ein gesperrtes Feld nimmt weder delete noch insert an; sonst
        # stuende dort eine veraltete Zahl, sobald Presets oder gespeicherte
        # Einstellungen geladen werden, bevor die Spieldaten da sind.
        state = str(self.entry.cget("state"))
        if state != "normal":
            self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        if state != "normal":
            self.entry.configure(state=state)

    def _entry_apply(self, _=None):
        """Eingetippte Zahl uebernehmen. Komma und Punkt gelten beide als
        Dezimaltrenner; Unsinn und Werte ausserhalb der Spanne fallen auf
        den erlaubten Bereich zurueck."""
        self._typing = False
        raw = self.entry.get().strip().replace(",", ".").replace("%", "")
        raw = raw.replace("×", "").replace("x", "").strip()
        try:
            value = float(raw)
        except ValueError:
            self._entry_show()
            return
        self.set(value)          # set() rundet ganzzahlige Raster selbst

    def _snap(self, value: float) -> float:
        """Ganzzahlige Raster (Stunden, Sekunden, Slots, Prozent) kennen
        keine halben Werte — egal ob sie aus dem Zahlenfeld, aus einem
        Preset oder aus einem Test kommen. Bewusst kaufmaennisch aufrunden
        statt mit Pythons round(), das aus 22,5 eine 22 machen wuerde."""
        return math.floor(value + 0.5) if self._whole else value

    def get(self) -> float:
        return self._value

    def set(self, value: float):
        value = self._snap(min(self.hi, max(self.lo, float(value))))
        self._value = round(value, 4)
        if self.log:
            self.slider.set(math.log10(max(self._value, 1e-9)))
        else:
            self.slider.set(self._value)
        self._changed()

    def reset(self):
        self.set(self.default)

    def set_state(self, state: str):
        # Basiszustand merken: eine Avoid-Sperre haelt den Regler auch dann
        # deaktiviert, wenn die GUI insgesamt wieder freigeschaltet wird.
        self._base_state = state
        self.slider.configure(state="disabled" if self.locked else state)
        self.entry.configure(state="disabled" if self.locked else state)
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
            self.entry.configure(state="disabled")
            self.reset_btn.configure(text="\U0001f513", command=self._unlock)
        else:
            self.slider.configure(state=self._base_state)
            self.entry.configure(state=self._base_state)
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


def fmt_sec(v: float) -> str:
    return f"{int(round(v))} s"


def fmt_hud(v: float) -> str:
    return {0: "vanilla (as the difficulty sets it)", 1: "always shown"}.get(int(round(v)), "always hidden")


def fmt_slot(v: float) -> str:
    return {0: "vanilla (pistols only)", 1: "+ SMGs", 2: "+ SMGs & shotguns"}.get(int(round(v)), "any weapon")


def fmt_lock(v: float) -> str:
    return {0: "no lock (travel overweight)", 1: "partial lock"}.get(int(round(v)), "vanilla (full lock)")


def fmt_fov(v: float) -> str:
    return f"{v:.0f}\u00b0"


def fmt_hours(v: float) -> str:
    return f"{int(round(v))} h"


def fmt_plus(v: float) -> str:
    return "vanilla" if int(round(v)) == 0 else f"+{int(round(v))}"


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


# Regler-Bereich je Kaskaden-Parameter (Besitzer 06.09.: "haltbarkeit bis
# maximal 4? lieber bis minimum 10"). Untergrenze bleibt bei den invertierten
# Parametern (firerate, aimtime) ueber 0 - der Builder ueberspringt dort
# Faktor 0, ein Regler mit 0 waere ein Blindgaenger.
WEAPON_PARAM_RANGE = {
    "damage": (0.1, 10.0),
    "spread": (0.1, 4.0),
    "recoil": (0.1, 4.0),
    "durability": (0.25, 10.0),
    "firerate": (0.25, 4.0),
    "range": (0.25, 4.0),
    "bleeding": (0.1, 5.0),
    "adsspeed": (0.25, 4.0),
    "aimtime": (0.25, 4.0),
    "magazine": (0.25, 10.0),
}


def weapon_param_range(param: str) -> tuple[float, float]:
    return WEAPON_PARAM_RANGE.get(param, (0.25, 4.0))


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
    "enc_wounded": "encounter_wounded_factor",   # 1.35.0
    "enc_dead": "encounter_dead_factor",
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
    "climb": "climb_speed_factor", "start_money": "starting_money",
    "art_slots": "artifact_slots_bonus", "shoot_shake": "shooting_shake_factor",
    "ads_zoom": "ads_zoom_factor",
    "dialog_fov": "dialog_fov", "cutscene_fov": "cutscene_fov", "default_fov": "default_fov",
    "hud_compass": "hud_compass", "hud_crosshair": "hud_crosshair",
    "hud_bodies": "hud_body_markers", "hud_stashes": "hud_stash_markers",
    "corpse_time": "corpse_time_factor", "corpse_max": "corpse_max_count",
    "weather_dur": "weather_duration_factor", "bullet_drop": "bullet_drop_factor",
    "bullet_speed": "bullet_speed_factor", "pistol_slot": "pistol_slot_level",
    "mprot": "mutant_protection_factor", "sleep_min": "min_sleep_hours",
    # 1.26.0
    "hands_zoom": "handless_zoom_factor", "crouch_vignette": "crouch_vignette_factor",
    "butt_wear": "butt_wear_factor", "expl_radius": "explosion_radius_factor",
    "expl_npc": "explosion_npc_damage_factor", "phantom_dog": "phantom_dog_damage_factor",
    "reload": "reload_speed_factor", "jam_clear": "jam_clear_factor",
    # 1.29.0
    "equip_speed": "equip_speed_factor", "anim_skip": "shooting_anim_skip",
    "mut_loot": "mutant_loot_chance_factor", "stash_clue": "stash_clue_factor",
    "alife_vision": "alife_vision_factor", "map_reveal": "map_reveal_factor",
    "ft_lock": "fast_travel_lock", "guide_delay": "guide_delay_factor",
    "prot_cap": "protection_cap_factor", "weird_art": "weird_artifact_factor",
    "clicker": "clicker_factor",
    # 1.27.0
    "back_speed": "back_speed_factor", "air_control": "air_control_factor",
    "limp": "limp_speed_factor", "jog_threshold": "slow_run_threshold_pct",
    "regen_delay": "hp_regen_delay", "rad_decay": "radiation_decay_factor",
    "bleed_stop": "bleeding_stop_factor", "psy_recover": "psy_recovery_factor",
    "sober": "sober_up_factor", "stealth_kill": "stealth_kill_range_factor",
    "wheel_time": "wheel_time_pct", "sleep_fade": "sleep_fade_factor",
    "corpse_drag": "corpse_drag_factor", "item_despawn": "item_despawn_factor",
    "day_start": "day_start_hour", "evening_start": "evening_start_hour",
    "calm_dmg": "calm_damage_factor", "last_bullet": "last_bullet_multiplier",
    "armor_diff": "armor_difference_factor", "deflect_chance": "armor_deflect_chance_pct",
    "deflect_dmg": "armor_deflect_damage_factor",
    "scope_zoom": "scope_zoom_factor", "scope_penalty": "scope_penalty_factor",
    "upg_accuracy": "upg_accuracy_factor", "upg_handling": "upg_handling_factor",
    "upg_durability": "upg_durability_factor", "upg_range": "upg_range_factor",
    "upg_damage": "upg_damage_factor", "upg_weight": "upg_weight_factor",
    "upg_breath": "upg_breath_factor", "upg_armor_prot": "upg_armor_protection_factor",
    "upg_armor_misc": "upg_armor_misc_factor",
    "warn_count": "weapon_warning_count", "warn_delay": "weapon_warning_delay_factor",
    "camper_time": "camper_time_factor", "npc_hip": "npc_hip_accuracy_factor",
    "dmg_mercy": "damage_mercy_factor", "psy_phantoms_n": "psy_phantom_factor",
    "min_resale": "min_resale_pct", "container_respawn": "container_respawn_hours",
    "energy_tol": "energy_tolerance_factor", "device_price": "device_price_factor",
    "sync_melee": "sync_melee_factor", "sync_ability": "sync_ability_factor",
    "sync_grenade": "sync_grenade_factor", "sync_suppress": "sync_suppress_factor",
    "darkness": "darkness_factor", "corpse_threat": "corpse_threat_factor",
    # 1.28.0 (Kern-Sweep P1)
    "limp_threshold": "limp_threshold_factor", "bleed_hit": "bleeding_hit_factor",
    "bleed_nonpen": "bleeding_nonpen_factor", "damage_screen": "damage_screen_factor",
    "quicksave_min": "quicksave_overwrite_min",
    # 1.28.0 (Kern-Sweep P2)
    "grenade_resist": "grenade_resist_factor", "armor_wear": "armor_wear_coef",
    "anomaly_armor_diff": "anomaly_armor_difference_factor",
    # 1.28.0 (Kern-Sweep P3)
    "wounded_chance": "wounded_heal_chance", "wounded_cd": "wounded_cooldown_s",
    "wounded_regen": "wounded_regen_factor", "wounded_threshold": "wounded_heal_threshold",
    "npc_focus": "npc_player_focus_factor", "npc_retarget": "npc_retarget_cooldown_factor",
    "npc_dmg_memory": "npc_damage_memory_factor",
    "cover_distance": "cover_distance_factor", "cover_path": "cover_path_factor",
    # 1.28.0 (Kern-Sweep P4)
    "mut_smell": "mutant_smell_factor", "burer_fire": "burer_fire_interval_factor",
    # 1.28.0 (Kern-Sweep P5)
    "squad_expansion": "squad_expansion_factor", "refill_cd": "refill_cooldown_factor",
    "refill_dist": "refill_distance_factor", "corpse_budget": "corpse_budget",
    "faction_battle": "faction_battle_chance", "faction_pace": "faction_expansion_pace_factor",
    "corpse_distance": "corpse_distance_factor", "corpse_hardcap": "alife_corpse_hardcap",
    # 1.28.0 (Kern-Sweep P6)
    "rad_dose": "radiation_dose_factor", "rad_filter": "radiation_filter_factor",
    "geiger": "geiger_volume_factor", "barbed_wire": "barbed_wire_factor",
    "exp_containers": "explosive_container_factor", "push_force": "push_force_factor",
    "weather_transition": "weather_transition_factor",
    "moon": "moon_brightness_factor", "sun": "sun_brightness_factor",
    "stars": "stars_brightness_factor", "cloud_opacity": "cloud_opacity_factor",
    "cloud_speed": "cloud_speed_factor", "dusk_length": "dusk_length_factor",
    "music_threshold": "music_combat_threshold", "music_lifetime": "music_combat_lifetime",
    "camp_life": "camp_life_factor",
    # 1.28.0 (Kern-Sweep P7)
    "art_radius": "artifact_radius_factor", "art_keepaway": "artifact_keepaway_factor",
    "art_hop_pause": "artifact_hop_pause_factor",
    # 1.35.0: kleine Kandidaten (Familien-Waechter + neunte Recherche)
    "art_hop_dist": "artifact_hop_distance_factor",
    "art_hop_count": "artifact_hop_count_factor",
    "npc_vs_player": "npc_vs_player_damage_factor",
    "npc_vs_friendly": "npc_vs_friendly_damage_factor",
    "bullet_pen_depth": "bullet_penetration_depth_factor",
    "look_h": "look_speed_h_factor", "look_v": "look_speed_v_factor",
    "cam_slowdown": "camera_slowdown_factor",
    "loot_reroll": "loot_reroll_radius_factor", "loot_reroll_time": "loot_reroll_timer_factor",
    # 1.28.0 (Kern-Sweep P8)
    "infotopic": "infotopic_refresh_hours",
    "ammo_dmg": "ammo_damage_factor",
    "ammo_ap": "ammo_piercing_factor", "ammo_ad": "ammo_armor_damage_factor",
    "ammo_cover": "ammo_cover_factor",
    "ammo_stack": "ammo_stack_factor",
    "jam_chance": "jam_chance_factor",
    "recoil_recovery": "recoil_recovery_factor",
    "spread_bloom": "spread_bloom_factor",
    "aim_steady": "aim_steady_factor",
    "zombie_spread": "zombie_spread_factor",
    "exp_armor_dmg": "explosion_armor_damage_factor",
    "exp_armor_pierce": "explosion_armor_pierce_factor",
    "exp_destructible": "explosion_destructible_factor",
    "bullet_pen": "bullet_penetration_factor",
    "bullet_range": "bullet_range_factor",
    "hip_steady": "hip_steady_factor",
    "move_steady": "move_steady_factor",
    "recoil_pattern": "recoil_pattern_factor",
    "dropped_ammo": "dropped_ammo_factor",
    "weapon_noise": "weapon_noise_factor",
    "item_grid": "item_grid_factor",
    "inv_action": "inventory_action_factor",
    "npc_anomaly": "npc_anomaly_ignore_factor",
    "ragdoll": "ragdoll_force_factor",
    "npc_retreat_dist": "npc_retreat_radius_factor",
    "npc_retreat_dmg": "npc_retreat_damage_factor",
    "npc_vs_npc": "npc_vs_npc_damage_factor",
    "upg_repair": "upgrade_repair_surcharge",
    "mut_series": "mutant_attack_series_factor",
    "mut_bleed": "mutant_attack_bleed_factor",
    "ammo_pack": "ammo_pack_factor",
    "ammo_bleed": "ammo_bleeding_factor",
    "ammo_recoil": "ammo_recoil_factor",
    "ammo_flat": "ammo_flatness_factor",
    "ammo_wear": "ammo_wear_factor",
    # 1.33.0 (neunte Datenrecherche, 27 fremde Mods gegengelesen)
    "ammo_disp": "ammo_dispersion_factor",
    "ammo_aimdisp": "ammo_aim_dispersion_factor",
    "anom_wear": "anomaly_wear_factor",
    "gear_dur": "gear_durability_factor",
    "far_damage": "far_damage_factor",
    "cap_other": "effect_cap_other_factor",
    "lair_initial": "lair_initial_fill_factor",
    "lair_rare": "lair_rare_archetype_factor",
    "lair_expand": "lair_expansion_player_factor",
    "fallback_spawn": "fallback_spawn_count",
    "cons_stack": "consumable_stack_factor", "anomaly": "anomaly_damage_factor",
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
    "stash_sets": "stash_sets_factor",
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
    "rq_jobs": "repeatable_jobs_per_round",
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
    "no_aim_mouse": "no_aim_assist_mouse",
    "no_aim_gamepad": "no_aim_assist_gamepad",
    "sleep_anytime": "sleep_anytime",
    "sleep_emission": "sleep_in_emission",
    # 1.26.0
    "no_knockdown": "no_knockdown", "no_water_slow": "no_water_slowdown",
    "ladder_look": "ladder_free_look", "look_down": "look_straight_down",
    "mut_anomalies": "mutants_trigger_anomalies", "guards_normal": "guards_no_instakill",
    "psy_phantoms": "psy_phantoms_only", "npc_no_loot": "npcs_no_corpse_loot",
    "map_regions": "map_all_regions", "teleports_instant": "instant_teleports",
    "skip_intro": "skip_intro", "traders_no_gear": "traders_no_gear_buy",
    "traders_map": "traders_on_map",           # 1.35.0
    "no_mouse_smooth": "no_mouse_smoothing",
    "no_view_accel": "no_view_acceleration",
    "art_no_detector": "artifacts_no_detector",
    "npc_no_pickup": "npcs_no_weapon_pickup",
    # 1.28.0 (Kern-Sweep P1)
    "no_limp": "no_landing_limp", "flashlight_dialog": "flashlight_dialog_bright",
    # 1.28.0 (Kern-Sweep P4)
    "mut_no_smell": "mutants_no_smell", "mut_loot_widget": "mutant_loot_widget",
    # 1.28.0 (Kern-Sweep P7)
    "art_no_hop": "artifacts_no_hop", "art_caches": "artifact_caches_drop",
    # 1.28.0 (Kern-Sweep P8)
    "repair_no_rep": "repair_cost_reputation",
    # 1.31.0 (GitHub Issue #8)
    "rq_jobs_instant": "repeatable_jobs_instant",
    "rq_jobs_multi": "repeatable_jobs_multi",
    "stat_bars": "stat_bars_follow",
    "chamber_round": "chamber_round",
}

# Sonderwerte, wo "Default x 2" keinen (sinnvollen) Patch ergaebe.
FOOTPRINT_PROBES: dict[str, float] = {
    "fall_damage_pct": 50.0,
    "fast_travel_lock": 0.0,
    "slow_run_threshold_pct": 25.0,
    "evening_start_hour": 22.0,
    "armor_deflect_chance_pct": 50.0,
    "npc_weapon_rank_add": 2.0,
    "scope_sway_pct": 50.0,
    "trader_min_durability_pct": 0.0,
    "hud_compass": 2.0, "hud_crosshair": 2.0, "hud_body_markers": 2.0,
    "hud_stash_markers": 2.0, "pistol_slot_level": 3.0,
    "armor_wear_coef": 0.5,          # Absolutwert 0..1 (Vanilla 0.7): x2 waere nur der Deckel
    "wounded_heal_chance": 50.0, "wounded_cooldown_s": 600.0,   # Absolutwerte (P3)
    "wounded_heal_threshold": 50.0,
    "corpse_budget": 60.0, "faction_battle_chance": 80.0,          # Absolutwerte (P5)
    "alife_corpse_hardcap": 3000.0,
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
    "rq_jobs": ("QuestNodePrototypes",
                frozenset({"VariableValue"})),
    "check:rq_jobs_instant": ("QuestNodePrototypes",
                              frozenset({"Name"})),
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
    "stash_sets": ("StashPrototypes",
                   frozenset({"ItemSetCount"})),
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
        if field_name is None:
            return None
        # stat_bars_follow SPIEGELT nur, was andere Regler tun: ohne
        # verstellten Schaden/Reichweite/Feuerrate schreibt es gar
        # nichts, der Fussabdruck waere leer. Eine Sonde mit Partner-
        # Regler wuerde stattdessen dessen Blaetter erben und bei jeder
        # fremden Reichweiten-Mod falschen Alarm schlagen. Also wie
        # npc_gear und die Baum-Regler: bewusst nicht markierbar - die
        # Waffenregler, denen es folgt, sind es ja.
        if field_name == "stat_bars_follow":
            return None
        # 1.35.0: die zwei Maus-Schalter schreiben ueberhaupt keine
        # GameData-Datei, sondern Stalker2/Config/UserInput.ini. Der
        # Scan vergleicht cfg-Blaetter - hier gibt es nichts zu
        # vergleichen, der Fussabdruck waere leer.
        if field_name in ("no_mouse_smoothing", "no_view_acceleration"):
            return None
        return [Settings(**{field_name: True})]
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
            hover_color=PANEL2_HOVER, font=app._iw_font_row,
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
                font=self.app._iw_font_hint, text_color=MUTED,
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
                font=self.app._iw_font_hint, text_color=MUTED,
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
                font=self.app._iw_font_hint, text_color=MUTED,
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
                lo, hi = weapon_param_range(param)
                self.sliders[param] = SliderRow(
                    self.body, WEAPON_PARAM_LABELS[param], lo, hi, 0.1, 1,
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
                     text_color=MUTED).pack(fill="x", padx=12, pady=(2, 0))
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
            hover_color=PANEL2_HOVER, font=app._iw_font_cat,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_row,
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
                         text_color=MUTED).pack(fill="x", padx=12,
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
                    self.body, AMMO_PARAM_LABELS[param], 0.1, 5, 0.1, 1,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_cat,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_row,
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
                         text_color=MUTED).pack(fill="x", padx=12,
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
                font=self.app._iw_font_hint, text_color=MUTED,
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
                    self.body, ARMOR_PARAM_LABELS[param], 0.1, 5, 0.1, 1,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_cat,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_cat,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_row,
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
                         text_color=MUTED).pack(fill="x", padx=12,
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
                lo, hi = (0.0, 5.0) if param in ("regen", "protection") else (0.1, 10.0)
                self.sliders[param] = SliderRow(
                    self.body, MUT_PARAM_LABELS[param], lo, hi, 0.1, 1,
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
            hover_color=PANEL2_HOVER, font=app._iw_font_cat,
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


# Ein kleines Zeichen vor jedem Tab-Namen (Besitzer 06.09.: "auch kleine
# Symbole koennten funktionieren ... aber sehr sparsam, sonst wird es schnell
# kitschig"). Fuenf davon hat er selbst vorgeschlagen (Player, Vaulting,
# Combat, Upgrades, World); der Rest folgt derselben Linie: thematisch, wo es
# eindeutig ist, sonst eine schlichte geometrische Form. Bewusst KEINE Emoji —
# die wuerden bunt gerendert und rissen die Leiste auseinander.
TAB_ICONS = {
    "Player": "◉", "Vaulting": "◈", "Weight & items": "⚖", "Combat": "⚔",
    "NPCs & AI": "◎", "Mutants": "☣", "Factions": "⚑", "Weapons": "◆",
    "Ammo": "▪", "Armor": "◇", "Upgrades": "⚙", "World": "☢",
    "Economy": "¤", "Traders": "⇄",
}


# Zeichen je Design fuer die Fusszeile. Bewusst KEINE Fraktionslogos aus dem
# Spiel: das ist GSC-Grafik, und dieses Projekt liefert grundsaetzlich keine
# Spieldateien mit (dieselbe Regel wie fuer vanilla/ und die Oodle-DLL).
# Das hier sind gewoehnliche Schriftzeichen.
THEME_MARKS = {
    "Standard": "◐", "Loners": "◈", "Bandits": "☠", "Duty": "⛨", "Freedom": "☘",
    "Military": "★", "Ward": "⚔", "Spark": "⌁", "Monolith": "◆",
    "Ecologists": "⚗", "Mercenaries": "⌾", "Clear Sky": "☁",
}


class TabBar(ctk.CTkFrame):
    """Tab-Leiste in MEHREREN Reihen (Besitzer 06.09.: "zusaetzlich eine
    2. Reihe fuer die Menues ... und dann die Namen wieder voll
    ausschreiben").

    CTkTabview quetscht alle Tabs in EINE Reihe: bei 14 Tabs und dem
    880-px-Minimum bleiben rund 60 px je Knopf, und Beschriftungen wie
    "Weight & items" werden abgeschnitten. Diese Leiste verteilt dieselben
    Knoepfe auf zwei Reihen und gibt jeder Spalte mindestens die Breite des
    laengsten Namens — damit steht ueberall der volle Name.

    Die Schnittstelle bleibt die von CTkTabview, soweit das Werkzeug sie
    nutzt: add(name) liefert den Inhalts-Frame, dazu set/get und die
    Attribute _tab_dict / _name_list."""

    def __init__(self, master, rows: int = 2, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._rows = max(1, int(rows))
        self._bar = ctk.CTkFrame(self, fg_color="transparent")
        self._bar.pack(fill="x")
        self._holder = ctk.CTkFrame(self, fg_color="transparent")
        self._holder.pack(fill="both", expand=True)
        self._tab_dict: dict[str, ctk.CTkFrame] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._labels: dict[str, str] = {}      # Name -> Aufschrift mit Symbol
        self._name_list: list[str] = []
        self._current_name = ""
        self._font = ctk.CTkFont(size=14)
        theme = ctk.ThemeManager.theme["CTkSegmentedButton"]
        self._sel = theme["selected_color"]
        self._sel_hover = theme["selected_hover_color"]
        self._unsel = theme["unselected_color"]
        self._unsel_hover = theme["unselected_hover_color"]

    # ---------------------------------------------------------- Aufbau
    def add(self, name: str) -> ctk.CTkFrame:
        if name in self._tab_dict:
            return self._tab_dict[name]
        frame = ctk.CTkFrame(self._holder, fg_color="transparent")
        icon = TAB_ICONS.get(name, "")
        label = (icon + "  " + name) if icon else name
        self._labels[name] = label
        btn = ctk.CTkButton(self._bar, text=label, height=28, width=1,
                            font=self._font, corner_radius=6,
                            fg_color=self._unsel, hover_color=self._unsel_hover,
                            command=lambda n=name: self.set(n))
        self._tab_dict[name] = frame
        self._buttons[name] = btn
        self._name_list.append(name)
        self._relayout()
        if len(self._name_list) == 1:
            self.set(name)
        return frame

    def _relayout(self) -> None:
        """Knoepfe gleichmaessig auf die Reihen verteilen und jeder Spalte
        die Breite des laengsten Namens sichern."""
        per_row = -(-len(self._name_list) // self._rows)   # aufgerundet
        for i, name in enumerate(self._name_list):
            row, col = divmod(i, per_row)
            self._buttons[name].grid(row=row, column=col, padx=2, pady=2,
                                     sticky="ew")
        # Jede Spalte nur so breit wie IHR laengster Name — nicht alle gleich
        # breit. Mit den Tab-Symbolen waeren gleich breite Knoepfe 945 px
        # und wuerden beim 880-px-Minimum abgeschnitten; so sind es 706 px.
        # Die zwei Reihen bleiben trotzdem sauber untereinander, weil sie
        # sich dieselben Spalten teilen.
        for col in range(per_row):
            widest = max(self._font.measure(self._labels[n])
                         for i, n in enumerate(self._name_list)
                         if i % per_row == col)
            self._bar.grid_columnconfigure(col, weight=1, uniform="",
                                           minsize=widest + 16)
        # Spalten einer frueheren, breiteren Aufteilung wieder freigeben
        for col in range(per_row, len(self._name_list)):
            self._bar.grid_columnconfigure(col, weight=0, uniform="",
                                           minsize=0)

    # ----------------------------------------------------------- Zugriff
    def set(self, name: str) -> None:
        if name not in self._tab_dict or name == self._current_name:
            if name in self._tab_dict:
                self._paint()
            return
        if self._current_name:
            self._tab_dict[self._current_name].pack_forget()
        self._current_name = name
        self._tab_dict[name].pack(fill="both", expand=True)
        self._paint()

    def get(self) -> str:
        return self._current_name

    def tab(self, name: str) -> ctk.CTkFrame:
        """Inhalts-Frame eines Tabs (wie CTkTabview.tab) — tools/
        make_screenshots.py greift darueber auf die Seiten zu."""
        return self._tab_dict[name]

    def restyle(self, pal: dict) -> None:
        """Farben eines Designs uebernehmen. Die Leiste faerbt sich selbst,
        weil ihre Knoepfe gewoehnliche CTkButtons sind — der allgemeine
        Umfaerber koennte sie nicht vom Rest unterscheiden.
        Aktiver Tab = Akzent, die uebrigen = zweite Ebene."""
        self._sel, self._sel_hover = pal["button"], pal["button_hover"]
        self._unsel, self._unsel_hover = pal["panel2"], pal["panel2_hover"]
        self._paint()

    def _paint(self) -> None:
        for name, btn in self._buttons.items():
            if name == self._current_name:
                btn.configure(fg_color=self._sel, hover_color=self._sel_hover)
            else:
                btn.configure(fg_color=self._unsel,
                              hover_color=self._unsel_hover)


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
        self.scope_overrides: dict[str, dict[str, float]] = {}   # 1.27.0
        self._isc_rows: dict[str, dict] = {}
        self._isc_btns: list = []                 # Klassen-Knoepfe (fuer den Sperrzustand)
        self._isc_loading = False
        self._scope_box = None
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
        self._iw_font_cat = ctk.CTkFont(size=14)
        self._iw_font_row = ctk.CTkFont(size=13)
        self._iw_font_hint = ctk.CTkFont(size=12)
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
        # Farbdesign. Muss VOR _build_header stehen (_set_theme liest es) und
        # faengt immer beim Standard an; _load_ui_settings schaltet danach
        # auf das gemerkte um.
        self.theme_name = theme.DEFAULT_NAME

        self._build_header()
        self._build_body()
        self._build_footer()
        # Einmal durch die Design-Routine, auch im Standard: setzt die
        # Schriftfarbe je Knopf und das Zeichen in der Fusszeile. Sonst
        # griffe beides erst beim ersten Design-Wechsel.
        self._set_theme(self.theme_name)

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
        # Erst nachdem der Spielordner gesucht wurde — sonst pulst der Knopf
        # kurz, obwohl er noch gesperrt ist.
        self._blink_job = None
        self.after(900, self._blink_confirm)

    def destroy(self):
        """Beim Schliessen den Puls-Auftrag abbestellen.

        Sonst feuert `after` noch einmal auf ein zerstoertes Fenster —
        Tk meldet dann "invalid command name ..._blink_confirm", und in der
        Testbatterie (die mehrere Fenster nacheinander baut) hat genau das
        den Prozess abgeschossen, ohne eine Zeile Ausgabe zu hinterlassen."""
        job = getattr(self, "_blink_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._blink_job = None
        super().destroy()

    def _blink_confirm(self):
        """"Confirm & load game data" pulsiert, solange die Spieldaten nicht
        geladen sind (Besitzer 06.09.: "soll lieber blinken solange nicht
        gedrueckt wurde"). Ohne diesen Klick tut das Werkzeug gar nichts —
        und genau den haben Nutzer uebersehen.

        Gepulst wird nur der RAND, nicht die Flaeche: Gruen bedeutet im
        ganzen Programm "bereit", und eine Flaeche, die zwischen zwei Gruens
        springt, wuerde diese Bedeutung verwaschen. Sobald die Daten stehen
        (oder das Fenster weg ist), hoert es von selbst auf."""
        self._blink_job = None
        if not self.winfo_exists():
            return
        if self.gd is not None:                      # geladen: gruen, Ruhe
            self.btn_confirm.configure(
                fg_color=OK_GREEN, hover_color=OK_GREEN_HOVER,
                border_color=OK_BORDER, text_color="#DCE4EE")
            return
        self._blink_on = not getattr(self, "_blink_on", False)
        if str(self.btn_confirm.cget("state")) == "normal":
            self.btn_confirm.configure(
                fg_color=ATTENTION, hover_color=ATTENTION_HOVER,
                text_color="#DCE4EE",
                border_color=ATTENTION_BORDER if self._blink_on else ATTENTION)
        self._blink_job = self.after(650, self._blink_confirm)

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

        Dort abgelegt wird die Datei gefunden (ensure_oodle sucht zuerst
        neben der EXE und legt eine Kopie in tools/ ab); das passt zum Bild
        und zum Text im Assistenten."""
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
            btn.configure(text="● Oodle ready", fg_color=OK_GREEN,
                          hover_color=OK_GREEN_HOVER,
                          border_width=SYS_BORDER, border_color=OK_BORDER)
        else:
            btn.configure(text="● Oodle missing", fg_color=BAD_RED,
                          hover_color=BAD_RED_HOVER,
                          border_width=SYS_BORDER, border_color=BAD_BORDER)

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
        win.geometry("880x740")
        win.minsize(820, 640)
        win.transient(self)

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(14, 6))
        nav = ctk.CTkFrame(win, fg_color="transparent")
        nav.pack(fill="x", padx=18, pady=(0, 12))

        state = {"page": 0, "images": []}
        back_btn = ctk.CTkButton(nav, text="←  Back", width=130, height=38,
                                 font=ctk.CTkFont(size=15))
        step_lbl = ctk.CTkLabel(nav, text="", text_color=MUTED,
                                font=ctk.CTkFont(size=15))
        next_btn = ctk.CTkButton(nav, text="Next  →", width=150, height=38,
                                 font=ctk.CTkFont(size=15, weight="bold"))
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
                         font=ctk.CTkFont(size=21, weight="bold")
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

        def tldr(*lines: str):
            """Kurzfassung in grosser Schrift ganz oben auf jeder Seite - fuer
            alle, die die Erklaerung nicht lesen wollen (Wunsch des
            Besitzers, 05.09.2026: „tool needs this, press copy, paste in
            browser, download, accept, put there")."""
            box = ctk.CTkFrame(body, fg_color="gray20", corner_radius=8)
            box.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(box, text="TL;DR", anchor="w", text_color="#FF5252",
                         font=ctk.CTkFont(size=18, weight="bold")
                         ).pack(fill="x", padx=14, pady=(8, 0))
            for line in lines:
                ctk.CTkLabel(box, text=line, anchor="w", justify="left",
                             wraplength=790,
                             font=ctk.CTkFont(size=25, weight="bold")
                             ).pack(fill="x", padx=14, pady=(2, 0))
            ctk.CTkLabel(box, text="", height=8).pack()

        # ---------------------------------------------------------- Seite 1
        def _page1():
            heading("S2Tweaker needs one extra file, once")
            tldr("The tool needs this one file.",
                 "→  Press “Copy” below.")
            ctk.CTkLabel(
                body,
                text="⚠   Without this file S2Tweaker cannot read the values "
                     "out of your game.",
                anchor="w", justify="left", wraplength=810,
                text_color="#E6B800",
                font=ctk.CTkFont(size=17, weight="bold"),
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
            entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=15), height=34)
            entry.insert(0, pakio.OODLE_URL)
            entry.configure(state="readonly")
            entry.pack(side="left", fill="x", expand=True)
            copy_btn = ctk.CTkButton(row, text="⧉  Copy", width=130, height=34,
                                     font=ctk.CTkFont(size=15))

            def do_copy():
                self.clipboard_clear()
                self.clipboard_append(pakio.OODLE_URL)
                copy_btn.configure(text="✓  Copied", fg_color=OK_GREEN,
                                   hover_color=OK_GREEN)

            copy_btn.configure(command=do_copy)
            copy_btn.pack(side="left", padx=(8, 0))
            para("Then click “Next” – the following steps show exactly what to "
                 "do with it.", "gray60", pady=(10, 0))

        # ---------------------------------------------------------- Seite 2
        def _page2():
            heading("Paste the link into your browser")
            tldr("→  Paste it into your browser and press Enter.",
                 "→  Download. If the browser asks “are you sure?”, say yes.")
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
            tldr("→  Put the file next to S2Tweaker.exe (folder below).",
                 "→  Restart S2Tweaker. Done.")
            picture("oodle_folder.png")
            # Kein Updater-Skript mehr als Wegmarke: das gibt es seit 1.19.1
            # nicht mehr im Download. Das Bild zeigt es noch (es ist der
            # Ordner des Besitzers) — deshalb nennt der Text nur Dateien,
            # die JEDER wirklich hat. Nie eine Datei als Orientierung
            # nennen, die beim Nutzer gar nicht liegt.
            para("Move the downloaded oo2core_9_win64.dll into the folder that "
                 "holds S2Tweaker.exe – the same place as README.txt. "
                 "Not into the “_internal” folder.")
            target = ctk.CTkEntry(body, font=ctk.CTkFont(size=15), height=34)
            target.insert(0, str(self._oodle_target_dir()))
            target.configure(state="readonly")
            target.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                body,
                text="When the file is in place: restart S2Tweaker. "
                     "That is all – it never asks again.",
                anchor="w", justify="left", wraplength=810,
                font=ctk.CTkFont(size=17, weight="bold"),
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
        # Die Mausrad-Sperre ist klassenweit: bei einem neuen Fenster (und in
        # den Tests, die mehrere Apps bauen) wieder auf den Startzustand.
        SliderRow.set_wheel_enabled(False)
        # Zeile 1: NUR der Spielordner (Wunsch des Besitzers: erst Ordner
        # bestaetigen, dann kommen die Werkzeuge — nichts vermischen)
        head = ctk.CTkFrame(self)
        head.pack(fill="x", padx=10, pady=(10, 4))
        self.game_label = ctk.CTkLabel(head, text="Game folder: searching ...", anchor="w")
        self.btn_confirm = ctk.CTkButton(
            head, text="✓ Confirm & load game data", width=200,
            fg_color=ATTENTION, hover_color=ATTENTION_HOVER,
            border_width=SYS_BORDER, border_color=ATTENTION_BORDER,
            command=self._confirm_game)
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
                                     fg_color=PANEL2, hover_color=PANEL2_HOVER,
                                     command=self._show_faq)
        self.btn_faq.pack(side="right", padx=(4, 10), pady=8)
        # Oodle-Ampel: auf einen Blick sichtbar, ob die Bibliothek da ist.
        # Klick oeffnet den Assistenten — auch dann, wenn alles stimmt, damit
        # man die Anleitung jederzeit nachlesen kann.
        self.btn_oodle = ctk.CTkButton(
            tools, text="● Oodle", width=132, fg_color=PANEL2,
            hover_color=PANEL2_HOVER, command=self._open_oodle_wizard)
        self.btn_oodle.pack(side="right", padx=4, pady=8)
        # Scrollrad-Schalter, direkt links neben der Oodle-Ampel und in
        # denselben Farben. Startet AUS (rot): das Rad blaettert dann nur,
        # niemand verstellt beim Scrollen aus Versehen einen Regler.
        self.btn_scroll = ctk.CTkButton(
            tools, text="● Wheel scrolls only", width=168,
            fg_color=BAD_RED, hover_color=BAD_RED_HOVER,
            border_width=SYS_BORDER, border_color=BAD_BORDER,
            command=self._toggle_wheel)
        self.btn_scroll.pack(side="right", padx=4, pady=8)
        # Farbdesigns (Fraktionen). Der Knopf traegt den Akzent des aktiven
        # Designs, damit man ohne Aufklappen sieht, worauf es steht.
        self.btn_theme = ctk.CTkButton(
            tools, text="◐ Theme", width=86, fg_color=PANEL2,
            hover_color=PANEL2_HOVER, command=self._show_theme_window)
        self.btn_theme.pack(side="right", padx=4, pady=8)
        self.btn_changed = ctk.CTkButton(
            tools, text="Changed only", width=105, fg_color=PANEL2,
            hover_color=PANEL2_HOVER, command=self._toggle_changed_only)
        self.btn_changed.pack(side="right", padx=4, pady=8)
        self.search_entry.bind("<KeyRelease>", self._apply_filter)

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(8, 2), padx=4)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        return frame

    def _slider(self, parent, key: str, label: str, from_: float, to: float,
                step: float, default: float, fmt, tooltip: str = "",
                log: bool = False) -> None:
        self.sliders[key] = SliderRow(parent, label, from_, to, step, default,
                                      fmt, tooltip, log=log)
        self.slider_tabs[key] = self._current_tab

    def _warning(self, parent, text: str, title: str = "Note") -> None:
        """Technische Warnbox: dunkles Panel, duenner Bernstein-Streifen
        links, Ueberschrift in Versalien, darunter der Text.

        Besitzer 06.09.: der alte einzeilige Hinweis sah "hineingeklatscht"
        aus — "ich wuerde daraus eine richtige technische Warnbox machen:
        dunkles Panel + duenne Amber-Linie links"."""
        box = ctk.CTkFrame(parent, fg_color=PANEL,
                           corner_radius=8)
        box.pack(fill="x", padx=12, pady=(4, 6))
        # Der Streifen: eigener schmaler Rahmen, der die volle Hoehe fuellt.
        # height=1 ist noetig — ein CTkFrame ohne Kinder behaelt sonst seine
        # Standardhoehe von 200 px und blaeht die Box auf.
        strip = ctk.CTkFrame(box, width=3, height=1, fg_color=WARN_AMBER,
                             corner_radius=2)
        strip.pack(side="left", fill="y", padx=(7, 0), pady=7)
        body = ctk.CTkFrame(box, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(11, 12), pady=8)
        # Mittig (Besitzer 06.09.: "known issue Nachrichten mittig sieht
        # denke ich besser aus") — Ueberschrift und Text zentriert, der
        # Streifen bleibt links.
        ctk.CTkLabel(
            body, text="⚠   " + title.upper(), anchor="center",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=WARN_AMBER).pack(fill="x")
        ctk.CTkLabel(body, text=text, anchor="center", justify="center",
                     wraplength=720, font=ctk.CTkFont(size=12),
                     text_color=("gray25", "gray72")).pack(fill="x",
                                                           pady=(4, 0))

    def _collapsible_category(self, parent, cat: str, label: str) -> None:
        """Aufklappbarer Block mit den 5 Parameter-Reglern einer Kategorie."""
        btn = ctk.CTkButton(parent, text="▸  " + label, anchor="w",
                            fg_color="transparent", hover_color=PANEL2_HOVER,
                            font=ctk.CTkFont(size=14))
        btn.pack(fill="x", padx=8, pady=1)
        content = ctk.CTkFrame(parent, fg_color="transparent")
        # Fuer die Suche merken: sonst bliebe dieser Block als einziger
        # Kategorie-Knopf im Fenster ungefaerbt, waehrend der gleich
        # aussehende Knopf im Overrides-Baum aufleuchtet.
        self._wcat_btns[cat] = (btn, label, btn.cget("text_color"), content)
        for param in WEAPON_PARAMS:
            lo, hi = weapon_param_range(param)
            self._slider(content, f"wcat_{cat}_{param}",
                         WEAPON_PARAM_LABELS[param], lo, hi, 0.1, 1, fmt_factor)

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
                         text_color=MUTED).pack(fill="x", padx=12)
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
    # -------------------------------------------- Einzel-Zielfernrohre (1.27.0)
    SCOPE_CLASS_LABELS = {"AimingFOVX2Effect": "2x scopes", "AimingFOVX3Effect": "3x scopes",
                          "AimingFOVX4Effect": "4x scopes", "AimingFOVX8Effect": "8x scopes",
                          None: "Collimators & holo sights (penalties only)"}

    def _isc_label(self, sid: str, zoom, pens) -> str:
        """Fernrohr-Name (aus der SID) plus Vanilla-Werte der Effekte."""
        parts = []
        for eff in ([zoom] if zoom else []) + list(pens):
            node = self.gd.effects.children.get(eff) if self.gd is not None else None
            raw = (node.values.get("ValueMin") or "").strip() if node is not None else ""
            if not raw:
                continue
            if eff.startswith("AimingFOVX"):
                parts.append(f"zoom {raw}")
            elif eff.startswith("ScopeAimingTimeNeg"):
                parts.append(f"aim time +{raw.lstrip('+')}")
            else:
                parts.append(f"ADS move {raw}")
        name = sid.replace("_", " ")
        return f"{name}   \u00b7   vanilla: " + ", ".join(parts) if parts else name

    def _isc_populate(self):
        """Fernrohr-Liste aus den Spieldaten aufbauen (je Klasse ein
        aufklappbarer Block). Wahrheit ist self.scope_overrides."""
        box = self._scope_box
        if box is None:
            return
        for child in box.winfo_children():
            child.destroy()
        self._isc_rows = {}
        self._isc_btns = []
        if self.gd is None:
            return
        table = self.gd.scope_effects()
        self.scope_overrides = {sid: p for sid, p in self.scope_overrides.items() if sid in table}
        groups: dict = {}
        for sid, (zoom, _pens) in table.items():
            groups.setdefault(zoom, []).append(sid)
        for key in ("AimingFOVX2Effect", "AimingFOVX3Effect", "AimingFOVX4Effect", "AimingFOVX8Effect", None):
            sids = sorted(groups.get(key, []))
            if sids:
                self._isc_block(box, self.SCOPE_CLASS_LABELS[key], sids, table)

    def _isc_block(self, parent, label: str, sids: list, table: dict) -> None:
        btn = ctk.CTkButton(parent, text="\u25b8  " + label, anchor="w",
                            fg_color="transparent", hover_color=PANEL2_HOVER,
                            font=ctk.CTkFont(size=14), state=self._ia_state)
        btn.pack(fill="x", padx=8, pady=1)
        self._isc_btns.append(btn)
        content = ctk.CTkFrame(parent, fg_color="transparent")
        prev = self._isc_loading
        self._isc_loading = True
        try:
            for sid in sids:
                zoom, pens = table[sid]
                ctk.CTkLabel(content, text=self._isc_label(sid, zoom, pens), anchor="w",
                             justify="left", wraplength=760,
                             font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", padx=12, pady=(6, 0))
                rows: dict = {}
                stored = self.scope_overrides.get(sid, {})
                if zoom:
                    rows["zoom"] = SliderRow(content, "Magnification", 0.25, 4, 0.1, 1, fmt_factor,
                                             on_change=lambda *_a, s=sid: self._isc_changed(s))
                    rows["zoom"].set(float(stored.get("zoom", 1.0)))
                if pens:
                    rows["penalty"] = SliderRow(content, "Handling penalties", 0, 4, 0.1, 1, fmt_factor,
                                                on_change=lambda *_a, s=sid: self._isc_changed(s))
                    rows["penalty"].set(float(stored.get("penalty", 1.0)))
                for row in rows.values():
                    row.set_state(self._ia_state)
                self._isc_rows[sid] = rows
        finally:
            self._isc_loading = prev

        def toggle():
            if content.winfo_manager():
                content.pack_forget()
                btn.configure(text="\u25b8  " + label)
            else:
                content.pack(fill="x", padx=16, after=btn)
                btn.configure(text="\u25be  " + label)

        btn.configure(command=toggle)

    def _isc_changed(self, sid: str) -> None:
        if self._isc_loading:
            return
        rows = self._isc_rows.get(sid, {})
        values = {p: float(r.get()) for p, r in rows.items() if abs(float(r.get()) - 1.0) > 1e-9}
        if values:
            self.scope_overrides[sid] = values
        else:
            self.scope_overrides.pop(sid, None)

    def _isc_clear_all(self):
        self.scope_overrides.clear()
        prev = self._isc_loading
        self._isc_loading = True
        try:
            for rows in self._isc_rows.values():
                for row in rows.values():
                    row.set(1.0)
        finally:
            self._isc_loading = prev

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
                         text_color=MUTED).pack(fill="x", padx=12)
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
                         text_color=MUTED).pack(fill="x", padx=12)
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
                         text_color=MUTED).pack(fill="x", padx=12)
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
        prot_by_species: dict[str, int] = {}
        for sid in self.gd.mutant_protections():
            species = self.gd.mutant_faction(sid)
            if species:
                prot_by_species[species] = prot_by_species.get(species, 0) + 1
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
            if prot_by_species.get(species):
                params.append("protection")
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
                         text_color=MUTED).pack(fill="x", padx=12)
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
            # wraplength seit 1.26.0: laengere Erklaerungen (Wachen, Karte)
            # wurden am Fensterrand abgeschnitten
            ctk.CTkLabel(parent, text="      " + tooltip, anchor="w", justify="left",
                         wraplength=780, font=ctk.CTkFont(size=12),
                         text_color=MUTED).pack(fill="x", padx=12)

    def _tab(self, name: str) -> ctk.CTkScrollableFrame:
        """Neuen Tab anlegen und scrollbaren Inhalts-Frame liefern."""
        self._current_tab = name
        tab = self.tabs.add(name)
        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        return frame

    def _build_body(self):
        self.tabs = TabBar(self, rows=2)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=0)

        body = self._tab("Player")
        f = self._section(body, "Player")
        self._slider(f, "hp", "Max health", 50, 100000, 10, 100, fmt_int,
                     "Logarithmic slider: fine steps near vanilla 100, up to "
                     "100000 for god-mode runs (a user reports the game "
                     "accepts it). Medkits heal a fixed amount (basic medkit "
                     "70 HP), so at very high health raise 'Medkit & bandage "
                     "healing' too.", log=True)
        self._slider(f, "hp_regen", "Passive health regen (HP/s)", 0, 20, 0.1, 0, fmt_dec,
                     "Vanilla: no passive regen. NPCs use 1 HP/s.")
        self._slider(f, "sp", "Max stamina", 50, 1000, 10, 100, fmt_int)
        self._slider(f, "sp_regen", "Stamina regen (per second)", 0, 50, 1, 5, fmt_dec)
        self._slider(f, "fall", "Fall damage", 0, 100, 5, 100, fmt_pct,
                     "0 % = no fall damage.")
        self._slider(f, "walk", "Walk & crouch speed", 50, 150, 5, 100, fmt_pct)
        self._slider(f, "run", "Run & sprint speed", 50, 150, 5, 100, fmt_pct,
                     "Animations and footstep sounds can't scale with speed "
                     "(engine limitation) – subtle changes feel best.")
        self._warning(f, "Players report that speed changes sometimes only "
                         "affect the animation instead of the actual movement. "
                         "Test in-game before settling on values. "
                         "(Status: 29 Aug 2026)",
                      title="Known issue — game patch 2.0")
        self._slider(f, "jump", "Jump height", 50, 200, 5, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Stamina costs (per action)")
        self._slider(f, "st_sprint", "Sprint (incl. continuous drain)", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "st_jump", "Jump", 0, 200, 5, 100, fmt_pct,
                     "Since 1.28.0 this also scales the stamina lost on "
                     "landing after a jump or fall (vanilla coefficient 0.5).")
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "vault_height", "Max vault height", 50, 250, 10, 100, fmt_pct,
                     "How high an obstacle you can still vault or climb over "
                     "(vanilla detection limit ~1.3 m). All vault sliders "
                     "stack on top of the preset below when both are used.")
        self._slider(f, "vault_distance", "Vault trigger distance", 100, 800, 10, 100, fmt_pct,
                     "From how far away vaulting triggers (vanilla is very "
                     "strict - the old vault mod used roughly 750 %).")
        self._slider(f, "vault_angle", "Vault approach angle", 100, 240, 10, 100, fmt_pct,
                     "How far off-center you may face an obstacle and still "
                     "vault it (capped at 180\u00b0).")
        self._slider(f, "vault_min_height", "Vault min obstacle height", 50, 200, 10, 100, fmt_pct,
                     "Below 100 % even small crates trigger vaulting; above, "
                     "only taller obstacles do.")
        self._slider(f, "vault_landing", "Vault landing tolerance", 100, 600, 10, 100, fmt_pct,
                     "How forgiving the landing check is: farther, steeper "
                     "and lower landing spots count (three game values "
                     "scaled together).")
        self._slider(f, "vault_over_depth", "Vault-over max thickness", 50, 300, 5, 100, fmt_pct,
                     "How deep/thick an obstacle may be and still be cleared "
                     "in one vault-over. The old vault mod HALVED this, "
                     "preferring quick climbs onto thick objects.")
        self._slider(f, "vault_over_offset", "Vault-over landing distance", 100, 500, 5, 100, fmt_pct,
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
                     "0.65 m, scaled the same way) - since 1.28.0 plus the "
                     "wide-trace, auto-interaction, mutant-harvest and "
                     "body-drag ranges. Not play-tested yet.")
        self._slider(f, "dialog_range", "Talk distance (NPC dialog)", 50, 300, 10, 100, fmt_pct,
                     "How close you have to be to start a conversation "
                     "(vanilla 1.3 m). The 'Social Distancing' idea from "
                     "Nexus. Not play-tested yet.")
        self._slider(f, "climb", "Ladder climb speed", 50, 300, 10, 100, fmt_pct,
                     "How fast Skif climbs ladders (vanilla coefficient "
                     "0.6) - since 1.28.0 including the five ladder "
                     "animation play-rates. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "New game")
        self._slider(f, "start_money", "Starting money (new game only)", 0, 100000, 1000, 0, fmt_int,
                     "Coupons Skif starts a NEW game with (vanilla 0). Has "
                     "no effect on an existing save. Not play-tested yet.")
        self._check(f, "skip_intro", "Skip the intro video",
                    "Cuts the opening video's start link in the quest graph "
                    "(same route as 'SkipIntroCutscene'). Only matters for a new "
                    "game. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Camera & HUD")
        self._slider(f, "dialog_fov", "Dialog field of view", 50, 110, 5, 70, fmt_fov,
                     "The camera zooms in during conversations (vanilla 70). "
                     "Set it to your normal FOV to stop the zoom. Not "
                     "play-tested yet.")
        self._slider(f, "cutscene_fov", "Cutscene field of view", 50, 120, 5, 90, fmt_fov,
                     "Vanilla 90. Not play-tested yet.")
        self._slider(f, "default_fov", "Default field of view", 50, 120, 5, 90, fmt_fov,
                     "The game's default gameplay FOV (vanilla 90). If you use "
                     "the FOV setting in the game's own options, that setting "
                     "most likely wins; this only changes the default. Not "
                     "play-tested yet.")
        ctk.CTkLabel(
            f, text="   HUD elements: the Master difficulty hides all four, the "
                    "other difficulties show them. These force one state on "
                    "every difficulty. Not play-tested yet.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "hud_compass", "Compass", 0, 2, 1, 0, fmt_hud)
        self._slider(f, "hud_crosshair", "Crosshair", 0, 2, 1, 0, fmt_hud)
        self._slider(f, "hud_bodies", "Dead body markers", 0, 2, 1, 0, fmt_hud)
        self._slider(f, "hud_stashes", "Stash markers", 0, 2, 1, 0, fmt_hud)
        self._slider(f, "hands_zoom", "Hands-free zoom (right mouse, no weapon)", 40, 125, 5, 100, fmt_pct,
                     "How far the view zooms when you hold aim with empty "
                     "hands (vanilla FOV factor 0.8; lower = stronger zoom, "
                     "Ace's CoreVariables list suggests 0.55 = 70 %). Capped "
                     "between 0.2 and 1.0. Not play-tested yet.")
        self._slider(f, "crouch_vignette", "Crouch vignette", 0, 150, 10, 100, fmt_pct,
                     "The dark screen edges while crouching (vanilla intensity "
                     "0.6). 0 % = none, like 'Remove Crouch Vignette'. Not "
                     "play-tested yet.")
        self._slider(f, "look_h", "Look speed, horizontal", 50, 200, 5, 100, fmt_pct,
                     "Turning speed left and right. Vanilla is 40 on the "
                     "player and 50 in the core config - so you turn a third "
                     "faster sideways than you look up and down, and the "
                     "game's own sensitivity setting moves both together and "
                     "cannot change that ratio. Both places are scaled the "
                     "same. Not play-tested yet.")
        self._slider(f, "look_v", "Look speed, vertical", 50, 200, 5, 100, fmt_pct,
                     "Looking up and down (vanilla 30 in both places). Set "
                     "this to about 133 % to match the horizontal speed. Not "
                     "play-tested yet.")
        self._slider(f, "cam_slowdown", "Camera slowdown from hazards", 0, 200, 5, 100, fmt_pct,
                     "How much your view is slowed while a chemical anomaly, "
                     "barbed wire or a flycatcher has hold of you (vanilla "
                     "-60 %, -80 %, -70 %). 0 % = no slowdown at all. The "
                     "bloodsucker roar uses a different key with an unknown "
                     "unit and is left alone. Not play-tested yet.")
        self._check(f, "no_mouse_smooth", "Turn off mouse smoothing",
                    "Unreal smooths mouse input by default and the "
                    "game's options cannot switch it off. This writes "
                    "Stalker2/Config/UserInput.ini into the pak - the "
                    "only thing this tool builds that is not a game "
                    "data patch, so the mod scan cannot see conflicts "
                    "with another mod shipping the same file. Removing "
                    "the pak removes it again. Not play-tested yet.")
        self._check(f, "no_view_accel", "Turn off view acceleration",
                    "The second flag in the same file: the camera "
                    "speeding up while you keep turning. Same "
                    "caveats as above. Not play-tested yet.")
        self._slider(f, "damage_screen", "Damage screen effects", 0, 100, 10, 100, fmt_pct,
                     "The red directional hit flash and the burn, steam, "
                     "chemical, electric, darkness and quicksilver overlays "
                     "(15 post-effect processors, vanilla intensity 1.0). "
                     "0 % also removes the visual warning inside chemical "
                     "fields. Not play-tested yet.")
        self._check(f, "flashlight_dialog", "Flashlight stays bright in dialogue",
                    "Vanilla dims your flashlight to 52.5 % while you talk; "
                    "this keeps it at 100 %. Not play-tested yet.")
        self._slider(f, "map_reveal", "Map: location reveal distance", 50, 500, 10, 100, fmt_pct,
                     "How close you must come before a place appears on the "
                     "PDA map and counts as explored (vanilla mostly 100 m / "
                     "20 m, scaled together) - since 1.28.0 plus the three "
                     "global HUD marker distances (300 / 30 / 20 m). Not "
                     "play-tested yet.")
        self._check(f, "map_regions", "Map: show all region names from the start",
                    "The 23 region names start hidden in vanilla. Like the "
                    "'all location names on the map' mod. Not play-tested yet.")
        self._slider(f, "wheel_time", "Time speed while the quick wheel is open", 5, 100, 5, 30, fmt_pct,
                     "The game slows to 30 % while the item selector is open "
                     "(vanilla). 100 % = real time, 5 % = almost paused. Not "
                     "play-tested yet.")
        self._slider(f, "music_threshold", "Combat music threshold", 5, 100, 5, 20, fmt_int,
                     "How much nearby danger it takes before combat music "
                     "starts (vanilla 20 points; one ordinary stalker counts "
                     "10, a heavy one 20, a dog 7 - so two normal enemies "
                     "trigger it). Higher = music only in big fights. Not "
                     "play-tested yet.")
        self._slider(f, "music_lifetime", "Combat music lingers", 5, 60, 5, 25, fmt_sec,
                     "How long an attack keeps counting as combat, i.e. how "
                     "long the music keeps playing after the shooting stops "
                     "(vanilla 25 s). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Sleep")
        self._check(f, "sleep_anytime", "Sleep whenever you like (no 'not tired enough')",
                    "Vanilla lets you sleep only from 50 % tiredness. Not "
                    "play-tested yet.")
        self._slider(f, "sleep_min", "Minimum sleep", 1, 12, 1, 7, fmt_hours,
                     "The shortest sleep the game allows (vanilla 7 h). Not "
                     "play-tested yet.")
        self._check(f, "sleep_emission", "Allow sleeping during emissions",
                    "Vanilla forbids it. Not play-tested yet.")
        self._slider(f, "sleep_fade", "Sleep fade time", 0, 200, 10, 100, fmt_pct,
                     "The fade to black (vanilla 1.5 s) and the black screen "
                     "(3.5 s) when sleeping. 0 % = instant. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Body & movement")
        self._check(f, "no_knockdown", "Skif can't be knocked down",
                    "Mutant charges and blasts no longer throw you to the "
                    "ground (vanilla: they can). Like 'CantBeKnockedDown'. Not "
                    "play-tested yet.")
        self._check(f, "no_water_slow", "No slowdown in water",
                    "Removes the turn-rate and movement penalties while wading "
                    "(like 'NoSluggishWater'). Stamina drain in deep water "
                    "stays. Not play-tested yet.")
        self._check(f, "ladder_look", "Free look on ladders",
                    "Look around while climbing (vanilla 30° sideways, 40° "
                    "up/down; this sets 90°). Not play-tested yet.")
        self._check(f, "look_down", "Look straight down",
                    "Vanilla stops the camera at 80° below the horizon; this "
                    "allows 90°. Not play-tested yet.")
        self._slider(f, "back_speed", "Backward & sideways speed", 50, 200, 10, 100, fmt_pct,
                     "Walking backwards is 50 % of forward speed in vanilla, "
                     "running backwards 43 %, crouched 47-54 %, diagonal 72-75 %. "
                     "Capped at forward speed. Not play-tested yet.")
        self._slider(f, "air_control", "Air control while jumping", 50, 500, 10, 100, fmt_pct,
                     "How much you can steer mid-air (vanilla coefficient 0.1, "
                     "capped at 1.0). Not play-tested yet.")
        self._slider(f, "limp", "Limping speed (wounded)", 50, 200, 10, 100, fmt_pct,
                     "Movement speed while limping (vanilla 50 % of normal, "
                     "capped at 100 %). Not play-tested yet.")
        self._slider(f, "limp_threshold", "Limp threshold after hard landings", 1, 8, 0.1, 1, fmt_factor,
                     "How hard a landing must be before Skif starts limping "
                     "(vanilla thresholds 25 for the short limp, 65 for the "
                     "longer one; \u00d7 2 = twice as hard). Not play-tested yet.")
        self._check(f, "no_limp", "Never limp after landings",
                    "Pushes both landing thresholds to 1000x vanilla, so no "
                    "landing triggers the limp any more (overrides the slider "
                    "above). Not play-tested yet.")
        self._slider(f, "jog_threshold", "Jog below stamina", 0, 90, 5, 50, fmt_pct,
                     "Below this share of stamina Skif can only jog (vanilla "
                     "50 %). 0 % = sprint until the bar is empty. Not "
                     "play-tested yet.")
        self._slider(f, "stealth_kill", "Stealth kill reach", 50, 300, 5, 100, fmt_pct,
                     "How close you must be behind an NPC for a stealth kill "
                     "(vanilla 1.8 m). Not play-tested yet.")
        self._slider(f, "corpse_drag", "Corpse dragging speed", 50, 170, 10, 100, fmt_pct,
                     "Speed while dragging a body (vanilla 60 % of normal, "
                     "capped at 100 %); since 1.28.0 the time to grab a body "
                     "(vanilla 2 s) shrinks the same way. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Recovery & vitals")
        self._slider(f, "regen_delay", "Health regen delay", 0, 30, 1, 5, fmt_dec,
                     "Seconds after the last hit before health regeneration "
                     "starts (vanilla 5). Pairs with the passive regen slider "
                     "above. Not play-tested yet.")
        self._slider(f, "rad_decay", "Natural radiation decay", 0, 500, 10, 100, fmt_pct,
                     "How fast accumulated radiation fades on its own (vanilla "
                     "0.05 per second). 0 % = only pills and vodka help. Not "
                     "play-tested yet.")
        self._slider(f, "bleed_stop", "Bleeding stops by itself", 0, 500, 10, 100, fmt_pct,
                     "How fast bleeding fades without a bandage (vanilla 0.3 "
                     "per second). Not play-tested yet.")
        self._slider(f, "bleed_hit", "Bleeding per hit", 0, 300, 5, 100, fmt_pct,
                     "Bleeding points a wounding hit adds (vanilla 10 on a "
                     "bar of 100). 0 % = hits never make you bleed. Not "
                     "play-tested yet.")
        self._slider(f, "bleed_nonpen", "Bleeding from non-penetrating hits", 0, 300, 5, 100, fmt_pct,
                     "Chance and amount of bleeding from hits your armor "
                     "stops (vanilla modifiers 1.0). 0 % = only hits that "
                     "get through make you bleed. Not play-tested yet.")
        self._slider(f, "psy_recover", "Psy recovery", 25, 500, 10, 100, fmt_pct,
                     "How fast psy damage recovers (vanilla 1 per second). Not "
                     "play-tested yet.")
        self._slider(f, "sober", "Sober-up speed", 25, 500, 10, 100, fmt_pct,
                     "How fast drunkenness wears off (vanilla 1 per second). "
                     "Not play-tested yet.")
        self._slider(f, "energy_tol", "Energy drink tolerance (Cost of Hope)", 25, 400, 5, 100, fmt_pct,
                     "How many energy drinks Skif takes before overuse and "
                     "tolerance effects kick in (vanilla overuse 1000, "
                     "tolerance 2500 points). Not play-tested yet.")
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
        self._slider(f, "quicksave_min", "Quicksave overwrite window", 0, 60, 1, 5, fmt_min,
                     "For how long a new quicksave overwrites the previous "
                     "slot instead of starting a new one (vanilla 5 min). "
                     "0 = every quicksave gets its own slot, up to the quick "
                     "save slot limit above. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Weight & items")
        f = self._section(body, "Weight & inventory")
        self._slider(f, "carry", "Max carry weight (hard limit)", 20, 500, 5, 80, fmt_kg)
        self._slider(f, "penalty", "Overweight penalty starts at", 10, 500, 5, 50, fmt_kg,
                     "Below this weight: no slowdown at all. Stages scale up to the hard limit.")
        self._check(f, "no_overweight", "No overweight penalty at all",
                    "Removes the speed/stamina penalties entirely (between "
                    "penalty start and hard limit) - and, since 1.28.0, the "
                    "small stamina drain from carried weight below the "
                    "penalty line as well.")
        self._warning(f, "Changed carry-weight limits can break walking "
                         "animations, especially combined with movement-speed "
                         "changes. Test in-game. (Status: 29 Aug 2026)",
                      title="Known issue — game patch 2.0")
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
        self._slider(f, "cons_stack", "Food & medicine stack size", 1, 20, 0.5, 1, fmt_factor,
                     "How many of one food, drink or medical item fit in a "
                     "single inventory slot (vanilla 999 for all 24 of them). "
                     "Honest note: 999 is a limit you will almost never reach "
                     "- ammunition is the one that actually bites, and it has "
                     "its own slider in the Ammo tab. Not play-tested yet.")
        self._slider(f, "item_grid", "Inventory space per item", 25, 200, 5, 100,
                     fmt_pct,
                     "How many grid cells an item takes up (vanilla 1x1 for "
                     "small things up to 6x3 for a rifle). 50 % roughly "
                     "halves every footprint; nothing ever drops below one "
                     "cell. Whole cells only, so small items may not change "
                     "at all. Not play-tested yet.")
        self._slider(f, "inv_action", "Inventory action speed", 25, 400, 5, 100,
                     fmt_pct,
                     "How long using something from the inventory takes "
                     "(vanilla 2.5 to 5 s). 200 % = half the time. Not "
                     "play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Combat")
        f = self._section(body, "Combat")
        self._slider(f, "pdmg", "Player damage (guns)", 0.25, 10, 0.1, 1, fmt_factor,
                     "Applied via difficulty multipliers, all difficulty levels.")
        self._slider(f, "headshot", "Player headshot damage", 0.25, 5, 0.1, 1, fmt_factor)
        self._slider(f, "aimpunch", "Hit camera shake (aim punch)", 0, 300, 5, 100, fmt_pct,
                     "Camera kick when YOU get shot. 0 % = no flinch, "
                     "300 % = heavy aim punch.")
        self._slider(f, "expl", "Explosion damage", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "dur", "Weapon durability", 0.5, 10, 0.1, 1, fmt_factor,
                     "Weapons wear less per shot fired.")
        self._slider(f, "jam", "Weapon jamming", 0, 2, 0.1, 1, fmt_factor,
                     "× 0 = weapons never jam.")
        self._slider(f, "expl_radius", "Explosion radius", 50, 300, 5, 100, fmt_pct,
                     "Blast, impulse and concussion radius of grenades, "
                     "launcher rounds, barrels and gas cylinders (vanilla "
                     "RGD-5 7 m, F1 10 m). Like 'IncreaseGrenadeRadius'. Not "
                     "play-tested yet.")
        self._slider(f, "exp_armor_dmg", "Explosion armor damage", 0, 400, 5, 100,
                     fmt_pct,
                     "How much an explosion wears your armor and NPC armor "
                     "(vanilla 20 to 50 per blast). 0 % = blasts hurt but "
                     "leave the suit intact. Not play-tested yet.")
        self._slider(f, "exp_armor_pierce", "Explosion armor penetration", 0, 400, 5,
                     100, fmt_pct,
                     "How well a blast goes through armor (vanilla 4 to 6). "
                     "Lower = heavy armor protects more against grenades. Not "
                     "play-tested yet.")
        self._slider(f, "exp_destructible", "Explosion damage to objects", 0, 400, 5,
                     100, fmt_pct,
                     "Damage to destructible props - crates, barrels, gas "
                     "bottles (vanilla 1000 to 4000). Not play-tested yet.")
        self._slider(f, "ragdoll", "Ragdoll force on death", 0, 400, 5, 100, fmt_pct,
                     "How hard a body is thrown by the shot that kills it "
                     "(vanilla multipliers 2 and 3 on every prototype). "
                     "0 % = bodies drop where they stand. Cosmetic. Not "
                     "play-tested yet.")
        self._slider(f, "expl_npc", "Explosion damage to NPCs", 0.25, 5, 0.1, 1, fmt_factor,
                     "The DamageNPC value of every explosion type (vanilla "
                     "RGD-5 260, RPG 2700). Damage to YOU is the slider above. "
                     "Not play-tested yet.")
        self._check(f, "guards_normal", "Base guards use normal weapon damage (no instant death)",
                    "Vanilla guard weapons deal 500 damage per hit and restricted "
                    "areas kill you with an invisible sniper shot; this gives "
                    "guards their weapon's normal NPC damage and removes the "
                    "sniper effect (like 'NoInstaGibByGuards'). Guards are "
                    "meant to be deadly - use at your own risk. Not play-tested "
                    "yet.")
        self._slider(f, "calm_dmg", "Damage to unaware NPCs", 25, 400, 5, 100, fmt_pct,
                     "Your hits on NPCs that have not noticed you deal 2.5x in "
                     "vanilla (a hidden sneak-attack bonus). Not play-tested yet.")
        self._slider(f, "last_bullet", "Last-bullet damage multiplier", 1, 5, 0.1, 2, fmt_factor,
                     "A hidden multiplier the game keeps for the last bullet "
                     "(vanilla 2.0). Honest note: which shot it applies to is "
                     "not verified - x 1 switches it off. Not play-tested yet.")
        self._slider(f, "armor_diff", "Armor vs. bullet difference weight", 25, 300, 5, 100, fmt_pct,
                     "How strongly the gap between armor rating and bullet "
                     "penetration changes damage (vanilla coefficients 2.0 "
                     "global, 1.6 projectiles, 1.3 melee). Experimental, not "
                     "play-tested.")
        self._slider(f, "deflect_chance", "Armor deflection chance", 0, 100, 1, 93, fmt_pct,
                     "Chance that armor far above a bullet's class deflects "
                     "the hit (vanilla 93 %). Experimental, not play-tested.")
        self._slider(f, "deflect_dmg", "Deflected-hit damage", 0, 300, 5, 100, fmt_pct,
                     "Damage coefficient of a deflected hit on humans and "
                     "mutants (vanilla 1.5). Experimental, not play-tested.")
        self._slider(f, "anomaly_armor_diff", "Armor vs. anomaly strike weight (experimental)", 0, 300, 5, 100, fmt_pct,
                     "How strongly your armor rating counts against the "
                     "physical strike of anomalies (vanilla coefficient 1.0, "
                     "the sibling of the bullet weight above; formula "
                     "unknown). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("NPCs & AI")
        f = self._section(body, "Human NPCs")
        self._slider(f, "npcdmg", "NPC damage (to you)", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "npchp", "NPC health", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "npc_acc", "NPC accuracy", 0.25, 3, 0.1, 1, fmt_factor,
                     "× 2 = NPCs shoot twice as precisely (smaller bullet spread).")
        self._slider(f, "zombie_spread", "Zombie spread penalty", 0, 300, 5, 100,
                     fmt_pct,
                     "Zombified stalkers shoot with an extra 30 of spread on "
                     "top of the weapon's own (vanilla, all 75 NPC weapon "
                     "profiles). 0 % = zombies aim as well as anyone else. Not "
                     "play-tested yet.")
        self._slider(f, "npc_anomaly", "NPCs walk into anomalies", 0, 400, 5, 100,
                     fmt_pct,
                     "Chance that a stalker or mutant ignores the anomaly "
                     "it is standing next to (vanilla 10 %, a few 40 to "
                     "50 %). Capped at 100 %. 0 % = they never blunder in. "
                     "Not play-tested yet.")
        self._slider(f, "npc_retreat_dist", "NPC retreat distance", 25, 400, 5, 100,
                     fmt_pct,
                     "How far an NPC falls back when it decides to retreat "
                     "(vanilla 8 to 25 m). Only the 32 prototypes that "
                     "retreat at all are touched. Not play-tested yet.")
        self._slider(f, "npc_retreat_dmg", "NPC damage before retreating", 25, 400,
                     5, 100, fmt_pct,
                     "How much damage an NPC soaks up before it pulls back "
                     "(vanilla 20 to 1000 depending on the type). Lower = "
                     "they break sooner. Not play-tested yet.")
        self._slider(f, "npc_vs_npc", "NPC vs NPC damage", 0, 400, 5, 100, fmt_pct,
                     "How hard stalkers hit EACH OTHER - vanilla is 70 % "
                     "of normal damage on every weapon, so faction fights "
                     "drag on. Does not touch what they do to you or you "
                     "to them. Not play-tested yet.")
        self._slider(f, "npc_vs_player", "NPC vs player damage", 0, 400, 5, 100, fmt_pct,
                     "How hard NPC bullets hit YOU - a per-weapon key, not the "
                     "difficulty slider called 'NPC damage (to you)' further up: "
                     "the two stack. Vanilla 100 % on all 150 weapon settings. "
                     "0 % = their guns cannot hurt you. Found by "
                     "the key-family check in 1.35.0. Not play-tested yet.")
        self._slider(f, "npc_vs_friendly", "NPC vs allies damage", 0, 400, 5, 100, fmt_pct,
                     "The third key of the same group: how hard NPCs hit "
                     "characters friendly to you, vanilla 30 %. Raise it and "
                     "escort partners die fast; lower it and they soak fire. "
                     "Not play-tested yet.")
        self._slider(f, "npc_vision", "NPC vision range", 10, 200, 5, 100, fmt_pct,
                     "How far human NPCs (incl. the Faust fight) can see you. "
                     "Korshunov & Scar boss senses stay vanilla. "
                     "10 % vision + 10 % hearing ≈ ghost mode.")
        self._slider(f, "npc_hearing", "NPC hearing range", 10, 200, 5, 100, fmt_pct,
                     "Footsteps, shots, voices etc. Mutants are unaffected "
                     "(except Supersoldiers – they use NPC hearing).")
        self._slider(f, "npc_reaction", "NPC reaction delay", 25, 400, 5, 100, fmt_pct,
                     "How long NPCs take to report threats/enemies to their "
                     "squad (vanilla 2–3 s). 400 % = slow, sleepy AI; "
                     "25 % = instant alarm.")
        self._slider(f, "npc_grenades", "NPC grenade usage", 0, 300, 10, 100, fmt_pct,
                     "0 % = NPCs never throw grenades (scripted bosses keep theirs).")
        self._check(f, "npc_no_heal", "NPCs don't self-heal",
                    "Vanilla: NPCs passively regenerate health (guards up to 20 HP/s) "
                    "while the player regenerates none. Includes bosses.")
        self._slider(f, "npc_gear", "NPC gear quality", 25, 400, 5, 100, fmt_pct,
                     "Tilts each squad's weapon/armor lottery toward the "
                     "pricier gear it can ALREADY carry (400 % = the best "
                     "gun in a pool is 4x as likely, 25 % = rust buckets "
                     "everywhere). Never adds gear a faction or rank "
                     "wouldn't carry in vanilla - and their dropped loot "
                     "changes accordingly.")
        self._check(f, "npc_no_loot", "NPCs don't loot bodies",
                    "Human NPCs stop searching corpses (vanilla: they take "
                    "gear before you arrive). Like 'NPCsDontLootCorpses'. Not "
                    "play-tested yet.")
        self._check(f, "psy_phantoms", "Psy fields spawn phantoms instead of real stalkers",
                    "The psy-field effect normally spawns real hostile NPCs; "
                    "this switches it to the harmless phantom variant (like "
                    "'NoPsyStalkerSpawns'). Not play-tested yet.")
        self._check(f, "npc_no_pickup", "NPCs don't pick up weapons",
                    "Vanilla NPCs grab weapons from bodies and the ground "
                    "(better ones by price). Not play-tested yet.")
        self._slider(f, "corpse_threat", "Bodies alarm NPCs", 0, 400, 5, 100, fmt_pct,
                     "How long a fresh body counts as a threat sign for NPCs "
                     "(vanilla 120 s). 0 % = they ignore bodies. Not "
                     "play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "NPC combat behaviour (experimental)")
        self._warning(f, "These are the hidden per-weapon AI profiles behind "
                         "'aimbot' complaints (same data the 'Grounded Combat' "
                         "and 'Better Gunfights' mods edit). Every NPC weapon "
                         "profile, rank and distance scales together. Not "
                         "play-tested yet.",
                      title="Experimental — NPC aim profiles")
        self._slider(f, "npc_free_shots", "NPC guaranteed-hit shots", 0, 200, 10, 100, fmt_pct,
                     "Shots per burst that NPCs fire with ZERO spread - the "
                     "opening 'laser' fire (vanilla e.g. rifles 2-3 at long, "
                     "4-6 at short range). 0 % = every NPC shot uses normal "
                     "spread; shotguns and launchers already have 0.")
        self._slider(f, "npc_burst", "NPC burst length", 25, 300, 5, 100, fmt_pct,
                     "Shots per burst (vanilla e.g. rifles 3-6 at long, 8-16 "
                     "at short range).")
        self._slider(f, "npc_fire_pause", "NPC fire pauses", 25, 400, 5, 100, fmt_pct,
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

        f = self._section(body, "Wounded NPCs")
        self._slider(f, "wounded_chance", "Wounded NPCs: chance to recover", 0, 100, 5, 70, fmt_pct,
                     "When a human NPC goes down wounded, this is the chance "
                     "(vanilla 70 %) that they heal over time instead of "
                     "bleeding out. 0 % = every downed NPC bleeds out. Not "
                     "play-tested yet.")
        self._slider(f, "wounded_cd", "Wounded-state cooldown", 30, 1800, 30, 300, fmt_sec,
                     "Seconds before the same NPC can go down wounded again "
                     "(vanilla 300). Very low values = NPCs drop again and "
                     "again. Not play-tested yet.")
        self._slider(f, "wounded_regen", "Wounded NPC health regen", 0, 400, 5, 100, fmt_pct,
                     "Health per second a wounded NPC regains (vanilla 5). "
                     "0 % = none. Not play-tested yet.")
        self._slider(f, "wounded_threshold", "Wounded heal threshold (experimental)", 5, 95, 5, 35, fmt_int,
                     "The game's HpThresholdToHealWound (vanilla 35). Either "
                     "'healable below this many HP' or 'wakes up with this "
                     "many HP' - the direction is not proven. Not play-tested "
                     "yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Target choice (experimental)")
        self._warning(f, "How NPCs pick whom to shoot at - one scoring "
                         "profile shared by every NPC (EnemyEvaluator). The "
                         "formula is not documented and the sign of the "
                         "player term is unproven. Not play-tested yet.",
                      title="Experimental — NPC target choice")
        self._slider(f, "npc_focus", "NPC focus on the player", 0, 400, 5, 100, fmt_pct,
                     "Scales the 'not the player' weight in target scoring "
                     "(vanilla 0.15). Whether higher means MORE or LESS "
                     "attention on you is unproven - try 0 % and 400 % and "
                     "tell us. Not play-tested yet.")
        self._slider(f, "npc_retarget", "NPC target-switch cooldown", 25, 400, 5, 100, fmt_pct,
                     "Minimum seconds before an NPC changes its target "
                     "(vanilla 3). Not play-tested yet.")
        self._slider(f, "npc_dmg_memory", "NPC damage memory", 25, 400, 5, 100, fmt_pct,
                     "How long recent damage keeps counting when NPCs weigh "
                     "who hurt them (vanilla 7 s). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Cover behaviour (experimental)")
        self._warning(f, "The shared cover profile of ~1600 human NPCs "
                         "(DefaultCoverEvaluator); story bosses keep their own. "
                         "Distances are game units (100 = 1 m) and the "
                         "evaluator formula is not documented. Not play-tested "
                         "yet.",
                      title="Experimental — NPC cover")
        self._slider(f, "cover_distance", "NPC cover distance to enemy", 50, 200, 10, 100, fmt_pct,
                     "The distance band NPCs prefer for a cover spot (vanilla "
                     "8-70 m from the enemy), both ends scaled together. Not "
                     "play-tested yet.")
        self._slider(f, "cover_path", "NPC cover search path", 50, 400, 5, 100, fmt_pct,
                     "How far NPCs will run to reach a cover spot (vanilla "
                     "path length 20 m). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Stealth: how NPCs notice you (experimental)")
        self._slider(f, "darkness", "Night darkness for NPC eyes", 0, 200, 10, 100, fmt_pct,
                     "The base light level NPC eyes assume by time of day "
                     "(vanilla night 0.2, dawn 0.3, morning 0.6, day 1.0). "
                     "0 % = pitch black nights for NPCs; only values below 1 "
                     "scale, capped at 1.0. Experimental, not play-tested.")
        self._slider(f, "stealth_crouch", "Crouch stealth", 25, 400, 5, 100, fmt_pct,
                     "How much crouching and crawling hide you from eyes AND "
                     "ears (vanilla: crouched you are 25 % less visible and "
                     "much quieter). 200 % = twice as hard to notice while "
                     "crouched.")
        self._slider(f, "stealth_noise", "Movement noise", 0, 200, 10, 100, fmt_pct,
                     "Noise of walking, running and sprinting (vanilla 0.6 / "
                     "0.8 / 1.0). 0 % = silent feet; crouch noise has its "
                     "own slider above.")
        self._slider(f, "stealth_weather", "Bad-weather stealth", 0, 300, 5, 100, fmt_pct,
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
        self._slider(f, "npc_alertness", "NPC alertness", 25, 300, 5, 100, fmt_pct,
                     "How little suspicion it takes before NPCs turn their "
                     "head (200), search (350), move in (500) or call allies "
                     "(700 points; a gunshot is worth 700). 200 % = they react "
                     "at half the suspicion. Human NPCs only.")
        self._slider(f, "npc_search", "NPC search time", 25, 400, 5, 100, fmt_pct,
                     "How long NPCs stay suspicious and keep searching "
                     "(vanilla: suspicion frozen 30 s, then fades 30 points/s). "
                     "25 % = they forget you fast.")
        self._slider(f, "npc_courage", "NPC courage", 25, 300, 5, 100, fmt_pct,
                     "Confidence needed before human squads attack or fall "
                     "back (vanilla bandits 2 / 1, monolith 0.5 / 0, others "
                     "3 / 0.5). Higher = braver. Mutants stay vanilla.")
        self._slider(f, "npc_stagger", "NPC stagger threshold", 25, 400, 5, 100, fmt_pct,
                     "Damage within 2 s that makes a human NPC flinch (vanilla "
                     "40; bosses far higher). 25 % = they stagger from almost "
                     "any hit, 400 % = they barely flinch.")
        self._slider(f, "warn_count", "Weapon-out warnings before guards turn hostile", 1, 10, 1, 3, fmt_int,
                     "How often guards warn you to holster before they attack "
                     "(vanilla 3). Not play-tested yet.")
        self._slider(f, "warn_delay", "Time between weapon-out warnings", 25, 400, 5, 100, fmt_pct,
                     "Vanilla 10 s between warnings. Not play-tested yet.")
        self._slider(f, "camper_time", "Camper detection time", 25, 500, 10, 100, fmt_pct,
                     "How long you may stay in one spot (5 m radius) before "
                     "NPCs treat you as a camper and flank (vanilla 10 s). Not "
                     "play-tested yet.")
        self._slider(f, "npc_hip", "NPC hip-fire accuracy", 0.25, 3, 0.1, 1, fmt_factor,
                     "The difficulty multiplier for NPC hip fire (vanilla 1.0 "
                     "everywhere). Direction assumed: higher = more precise. "
                     "Not play-tested yet.")
        self._slider(f, "dmg_mercy", "Hidden damage mercy", 0, 300, 5, 100, fmt_pct,
                     "The game dampens damage you take in quick succession; "
                     "the curve weights are 0.33-0.75 on Medium, 0.15-0.5 on "
                     "Hard, 0.12-0.4 on Stalker, 1.0 on Easy. Scaled per "
                     "difficulty, capped at 1.0. Direction not verified - "
                     "experimental.")
        self._slider(f, "psy_phantoms_n", "Psy phantom count (Stalker difficulty)", 25, 400, 5, 100, fmt_pct,
                     "The Stalker difficulty spawns twice the psy phantoms "
                     "(multiplier 2.0); other difficulties have no entry. Not "
                     "play-tested yet.")
        self._slider(f, "npc_attack_cd", "NPC attack cooldown", 25, 400, 5, 100, fmt_pct,
                     "Difficulty multiplier on human NPC attack cooldowns "
                     "(vanilla 1.0 on every difficulty). Effect scope not "
                     "verified in-game - experimental.")
        self._slider(f, "npc_rank_add", "NPC weapon rank bonus", 0, 3, 1, 0, fmt_int,
                     "Raises every NPC's weapon behaviour rank by this many "
                     "steps (Newbie -> Experienced -> Veteran -> Master): "
                     "deadlier enemies without health sponges. Difficulty "
                     "value, vanilla 0.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Simultaneous attackers (experimental)")
        ctk.CTkLabel(
            f, text="   The game hands out attack tokens per difficulty and player "
                    "rank: only so many enemies may melee, use special "
                    "abilities, throw grenades or lay suppressive fire at the "
                    "same time. Ranged shots are unlimited in vanilla. Never "
                    "below 1. Not play-tested yet.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "sync_melee", "Simultaneous melee attackers", 25, 400, 5, 100, fmt_pct,
                     "Vanilla 5 on every difficulty.")
        self._slider(f, "sync_ability", "Simultaneous special attacks", 100, 500, 5, 100, fmt_pct,
                     "Abilities and knockdowns (vanilla 1 at a time).")
        self._slider(f, "sync_grenade", "Simultaneous grenade throwers", 100, 500, 5, 100, fmt_pct,
                     "Vanilla 1 at a time.")
        self._slider(f, "sync_suppress", "Simultaneous suppressive fire", 25, 400, 5, 100, fmt_pct,
                     "Vanilla 2 to 5 depending on difficulty and rank.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "NPC flashlights (experimental)")
        ctk.CTkLabel(
            f, text="   The one flashlight all 1,600 human NPCs carry. Your own "
                    "flashlight is not affected: its light values sit in the "
                    "game's Blueprint assets, out of reach for config patches.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12)).pack(fill="x", padx=12, pady=(2, 4))
        self._slider(f, "npc_light", "NPC flashlight brightness & reach", 25, 400, 5, 100, fmt_pct,
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
        self._warning(f, "These change how the living world spawns around "
                         "you. Large values can hurt performance or break "
                         "quest pacing – change in small steps and keep a "
                         "backup save.",
                      title="Experimental — A-Life spawns")
        self._slider(f, "alife_agents", "Max simultaneous NPCs & mutants", 50, 200, 10, 100, fmt_pct,
                     "Vanilla: 52 A-Life agents around the player. "
                     "200 % = a much busier Zone (heavy CPU load!).")
        self._slider(f, "alife_distance", "A-Life spawn distance", 50, 200, 10, 100, fmt_pct,
                     "Vanilla: squads spawn ≥ 2500 m away. Lower = encounters "
                     "pop up closer to you; higher = quieter surroundings.")
        self._slider(f, "alife_vision", "NPC visibility distance (A-Life grid)", 50, 300, 10, 100, fmt_pct,
                     "How far away NPC models are shown and simulated (vanilla "
                     "85 m; 'Distant Horizons' uses 150 to 250 m). Higher costs "
                     "performance. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "A-Life spawns: lairs & random encounters (experimental)")
        self._warning(f, "Two systems feed the Zone: LAIRS (fixed places with a "
                         "population that respawns) and the DIRECTOR (random "
                         "encounters rolled around you). 'Max simultaneous NPCs "
                         "& mutants' above is only a cap on top of both – raise it "
                         "too. Existing saves re-roll lairs slowly (sleep or "
                         "change region). Not play-tested yet.",
                      title="How the Zone spawns")
        self._slider(f, "lair_mutants", "Lair population: mutants", 50, 300, 5, 100, fmt_pct,
                     "How many mutants a lair holds (all species, per player "
                     "rank). Story lairs and base guards are never touched.")
        self._slider(f, "lair_humans", "Lair population: humans", 50, 300, 5, 100, fmt_pct,
                     "How many stalkers a faction lair holds. Base guards "
                     "(Guard lairs) stay vanilla on purpose.")
        self._slider(f, "lair_respawn", "Lair respawn speed", 25, 400, 5, 100, fmt_pct,
                     "How fast fallen lair members are replaced (vanilla 3 / 8 "
                     "min, wipe 8 min). Story lairs with instant refill stay as "
                     "they are.")
        self._slider(f, "lair_initial", "Lair starting occupancy", 50, 200, 5, 100, fmt_pct,
                     "How full a lair is the first time it spawns - vanilla "
                     "fills most of them only half (0.5), a few completely. "
                     "200 % = every lair starts at its full head count "
                     "(capped there). Base-guard lairs stay vanilla. Not "
                     "play-tested yet.")
        self._slider(f, "lair_rare", "Rare lair archetypes", 100, 500, 10, 100, fmt_pct,
                     "Inside a lair every archetype has a draw weight: most "
                     "sit at 1.0, but 170 entries are rarities at 0.2 or 0.5 "
                     "(the odd sniper or close-combat specialist). This "
                     "raises only those, capped at 1.0 - so the unusual ones "
                     "show up more often. Archetypes at 0 stay at 0: the game "
                     "means them not to appear there. Not play-tested yet.")
        self._slider(f, "refill_cd", "Lair refill cooldown", 25, 400, 5, 100, fmt_pct,
                     "The A-Life policy's pause before a wiped-out lair is "
                     "refilled (vanilla 360 s after a full wipe, 120 s after a "
                     "partial one). 25 % = lairs come back four times as fast. "
                     "Not play-tested yet.")
        self._slider(f, "refill_dist", "Lair refill distance", 50, 300, 5, 100, fmt_pct,
                     "How far from you a lair must be before it refills "
                     "(vanilla 200-250 m band). Not play-tested yet.")
        self._slider(f, "corpse_budget", "Offline corpse budget", 5, 120, 5, 30, fmt_int,
                     "How many A-Life bodies may pile up within a lair radius "
                     "(100 m) before offline decomposition kicks in (vanilla "
                     "30). Not play-tested yet.")
        self._slider(f, "enc_freq", "Random encounters: frequency", 25, 400, 5, 100, fmt_pct,
                     "How often the director rolls a new encounter around you "
                     "(vanilla 60–90 s in the open world, plus a timeout after "
                     "each spawn – both scale).")
        self._slider(f, "enc_mutants", "Random encounters: mutant share", 0, 400, 5, 100, fmt_pct,
                     "Weight of pure-mutant encounters against human ones "
                     "(vanilla ~37 % of the open-world rolls). 0 % = no random "
                     "mutant packs (lair mutants stay). Weights the game never "
                     "uses (0) stay 0.")
        self._slider(f, "enc_pack", "Random encounters: pack size (experimental)", 50, 200, 10, 100, fmt_pct,
                     "Scales the per-rank cap of each spawnable type (blind "
                     "dogs 4–12, fleshes 2–6 ...) – our best reading of how pack "
                     "size is derived, unverified. Types the director never "
                     "spawns (chimera, controller, burer ...) are skipped.")
        self._slider(f, "enc_wounded", "Random encounters: wounded stalkers", 25, 400, 5, 100, fmt_pct,
                     "The game has eight scenarios that spawn wounded "
                     "stalkers (friendly and hostile, single and in "
                     "groups), but their share sits at 10 to 20 %. This "
                     "scales that share, capped at 100 %. Squads that "
                     "spawn nobody wounded in vanilla stay that way - "
                     "the slider scales what exists, it does not invent "
                     "wounded encounters. Not play-tested yet.")
        self._slider(f, "enc_dead", "Random encounters: dead bodies", 25, 400, 5, 100, fmt_pct,
                     "Same for the share that arrives already dead "
                     "(vanilla 20 to 60 % in 36 of the 95 squad entries, "
                     "zero in the rest - an ambush that already happened). "
                     "Capped at 100 %. Not play-tested yet.")
        self._slider(f, "lair_expand", "Lairs expand toward you", 25, 400, 5, 100, fmt_pct,
                     "How long the simulation waits before a faction pushes a "
                     "lair in your direction (vanilla 120 min). 400 % = every "
                     "30 minutes. Offline behaviour, so expect it to show up "
                     "slowly. Not play-tested yet.")
        self._slider(f, "fallback_spawn", "Fallback spawn count", 1, 20, 1, 3, fmt_int,
                     "What the director spawns when it finds no matching "
                     "scenario at all (vanilla 3). Rarely used, but it is the "
                     "floor under every encounter. Not play-tested yet.")
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
            self._slider(f, key, label, 0, 400, 5, 100, fmt_pct,
                         tip + " Stacks with the mutant-share slider. Bloodsuckers "
                         "have no slider: the open world never rolls them (weight 0).")
        self._slider(f, "squad_expansion", "A-Life squad expansion (experimental)", 25, 300, 5, 100, fmt_pct,
                     "How quickly the urge to send out expansion squads grows "
                     "in 16 NPC need presets (vanilla 6-10 points per minute "
                     "for humans, zombies 1-3, mutants 7-11; a squad leaves at "
                     "100). More squads roaming = more CPU load. Not "
                     "play-tested yet.")
        self._slider(f, "faction_battle", "Faction expansion battle chance (experimental)", 0, 100, 5, 50, fmt_pct,
                     "Chance that a faction's offline expansion into a foreign "
                     "lair turns into a battle (vanilla 50 % for all 29 "
                     "factions). Offline simulation, rarely visible. Not "
                     "play-tested yet.")
        self._slider(f, "faction_pace", "Faction expansion pace (experimental)", 25, 400, 5, 100, fmt_pct,
                     "Scales the population manager's ALifeLairExpansionTime "
                     "(vanilla 50) inversely: 200 % = factions expand twice as "
                     "often, if the value is a time at all - its unit is not "
                     "proven. Lair-count bands stay vanilla. Not play-tested "
                     "yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Camp life (atmosphere)")
        self._slider(f, "camp_life", "Camp life", 50, 300, 5, 100, fmt_pct,
                     "How often stalkers in camps feel like playing the "
                     "guitar, telling a joke, chatting, smoking, sleeping, "
                     "resting, eating or drinking (vanilla e.g. guitar 4-6, "
                     "jokes 3-6, talk 5-8 points per minute, across 25 NPC "
                     "presets). Work, patrols, guard duty and emission "
                     "behaviour stay vanilla. This writes a lot of small "
                     "changes, so the mod scan may report overlaps with other "
                     "A-Life mods. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Mutants")
        f = self._section(body, "All mutants (global)")
        self._slider(f, "mhp", "Mutant health (all species)", 0.1, 5, 0.1, 1, fmt_factor)
        self._slider(f, "mdmg", "Mutant damage (all species)", 0.1, 5, 0.1, 1, fmt_factor,
                     "Via difficulty multiplier – species overrides below "
                     "scale the individual attack values on top.")
        self._slider(f, "mspeed", "Mutant speed (all species)", 0.25, 2, 0.1, 1, fmt_factor,
                     "Walk/run/sprint speed of every mutant species.")
        self._slider(f, "mhearing", "Mutant hearing range", 10, 200, 5, 100, fmt_pct,
                     "All mutant species share one hearing sensor. Mutants "
                     "have no config-side vision range – sight is engine "
                     "logic, so no slider is offered.")
        self._slider(f, "mut_regen", "Mutant health regen", 0, 4, 0.1, 1, fmt_factor,
                     "Mutants passively regenerate health, just like human "
                     "NPCs (vanilla varies by species). × 0 = wounds stay "
                     "– the mutant counterpart of 'NPCs don't self-heal'.")
        self._slider(f, "mut_series", "Mutant attacks per series", 0.5, 3, 0.1, 1,
                     fmt_factor,
                     "How many blows a mutant lands in one go before it "
                     "backs off (vanilla 1 to 3, depending on the attack; "
                     "many attacks have no series at all and stay that "
                     "way). Rounded to whole hits, never below one. Human "
                     "and boss attacks are left alone. Not play-tested "
                     "yet.")
        self._slider(f, "mut_bleed", "Mutant bleeding buildup", 0, 3, 0.1, 1,
                     fmt_factor,
                     "How fast a mutant hit builds up bleeding. × 0 = "
                     "claws no longer make you bleed. Bosses and human "
                     "melee keep their vanilla values. Not play-tested "
                     "yet.")
        self._slider(f, "mprot", "Mutant physical protection", 0, 4, 0.1, 1, fmt_factor,
                     "The Protection values of every mutant (vanilla: mostly "
                     "melee 'Strike' protection, 1 to 4; bullet protection is "
                     "0 everywhere and stays 0). \u00d7 0 = no protection, like "
                     "'No More Tanky Mutants'. Per-species overrides in the "
                     "tree below. Not play-tested yet.")
        self._slider(f, "mut_attack_cd", "Mutant attack cooldown", 25, 400, 5, 100, fmt_pct,
                     "Difficulty multiplier on the pause between mutant "
                     "attacks (vanilla 1.0 on every difficulty). 200 % = "
                     "mutants attack half as often. Not play-tested yet.")
        self._check(f, "mut_anomalies", "All mutants trigger anomalies",
                    "Bloodsuckers, chimeras, controllers, poltergeists, "
                    "pseudodogs, pseudogiants, deer and rats are immune to "
                    "anomalies in vanilla; dogs, boars, fleshes, snorks and "
                    "burers are not. Like 'AnomaliesHitAllMutants'. Not "
                    "play-tested yet.")
        self._slider(f, "phantom_dog", "Pseudodog phantom damage", 0, 300, 5, 100, fmt_pct,
                     "Bite and bleeding of the pseudodog's illusions (vanilla "
                     "5 + bleeding). 0 % = phantoms are harmless, like "
                     "'NoPseudoDogCloneDamage'. Not play-tested yet.")
        self._slider(f, "mut_loot", "Mutant trophy drop chance", 0, 1000, 10, 100, fmt_pct,
                     "Chance that a dead mutant leaves a body part (vanilla: "
                     "blind dog 15 %, tushkan 10 %, boar/flesh/snork 20 %, "
                     "bloodsucker 50 %, poltergeist 65 %, the rest 100 %). "
                     "Capped at 100 %; 1000 % = every mutant drops, like "
                     "'100% Chance Mutant Loot'. Not play-tested yet.")
        self._check(f, "mut_loot_widget", "Mutant harvest: open the loot window instead of the quick animation (experimental)",
                    "Vanilla harvests mutants with an animation and no loot "
                    "window (UseMutantLootWithoutWidget = true; both "
                    "animation sets ship with the game). This flips the "
                    "flag to false, the loot-window flow. Read from the key "
                    "name only. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Bloodsucker cloaking")
        self._slider(f, "bs_cloak", "Bloodsucker cloaking speed", 0.25, 4, 0.1, 1, fmt_factor,
                     "× 4 = bloodsuckers vanish almost instantly.")
        self._slider(f, "bs_uncloak", "Bloodsucker uncloak from damage", 0, 20, 0.1, 1, fmt_factor,
                     "Higher = hitting them breaks the cloak much harder. "
                     "× 0 = damage never reveals them.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Sense of smell")
        self._slider(f, "mut_smell", "Mutant sense of smell", 25, 200, 5, 100, fmt_pct,
                     "Range and speed of the mutants' scent sense. One "
                     "sensor serves 38 species incl. blind dogs (40 m); "
                     "chimeras (70 m), fleshes (20 m) and poltergeists "
                     "(10 m) have their own, front-facing ranges scale along "
                     "where they exist. Proof it matters: the Weird Flower "
                     "artifact changes this sense by 60 %. The bad-weather "
                     "stealth factor (FlairCoef) still applies on top; story "
                     "bosses are untouched. Not play-tested yet.")
        self._check(f, "mut_no_smell", "Mutants cannot smell you",
                    "Switches the same scent sensors off (IsActive = "
                    "false); hearing and sight stay. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Burer telekinesis")
        self._slider(f, "burer_fire", "Burer weapon fire interval", 50, 400, 5, 100, fmt_pct,
                     "Seconds between shots of a weapon a burer levitates "
                     "and fires (vanilla 0.5 to 4 s depending on the ammo "
                     "type). 200 % = half as many shots. Not play-tested "
                     "yet.")
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(
            fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a size group, then a species, to edit its "
                    "factors.",
            anchor="w", font=ctk.CTkFont(size=12),
            text_color=MUTED).pack(fill="x", padx=12, pady=(0, 2))
        self.im_info = ctk.CTkLabel(
            f, text="No per-species overrides set.", anchor="w",
            justify="left", wraplength=780, font=self._iw_font_hint,
            text_color=MUTED)
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
            f, "The "
               "game copies relations into your save when a playthrough "
               "starts. This tool also raises the game's internal "
               "RelationVersion so existing saves should pick the new "
               "values up – unverified until in-game testing. Quests and "
               "scripted story characters can still override relations at "
               "any time (that is by design), and local hostility slowly "
               "rolls back on its own. Keep a backup save.",
            title="Experimental — existing saves")
        ctk.CTkLabel(
            f, text="   Baseline stance between factions, on the game's own "
                    "scale: −800 or lower = enemy (kill on sight), −799 to "
                    "−201 = wary (the game calls it 'Disaffection' – talking "
                    "and trading still work), −200 to 200 = neutral, 201 and "
                    "up = friend. Vanilla uses values like −599 on purpose – "
                    "just past a threshold. Story, boss and arena factions "
                    "are deliberately not listed.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(
            fill="x", padx=12)
        # Mod-Scan-Hinweis (Pseudo-Schluessel "tree:factions"): der Baum hat
        # keine Regler-Punkte, dafuer diese eine ehrliche Zeile.
        self.if_conflict_label = ctk.CTkLabel(
            f, text="", anchor="w", justify="left", wraplength=780,
            font=self._iw_font_hint, text_color=MARK_INFO)
        self.if_info = ctk.CTkLabel(
            f, text="No relations changed.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color=MUTED)
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
        self._slider(f, "rel_rollback", "Reputation rollback time", 25, 400, 5, 100, fmt_pct,
                     "How long the game remembers LOCAL hostility before "
                     "forgiving it (vanilla 60 min in the field, faster in "
                     "hubs). 400 % = grudges last four times longer; "
                     "25 % = quick forgiveness. Permanent faction-wide "
                     "reputation is a separate system and is not affected.")
        self._slider(f, "rel_reaction", "Reputation reaction strength", 25, 400, 5, 100, fmt_pct,
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
        self._slider(f, "wrange", "Weapon effective range", 50, 200, 10, 100, fmt_pct,
                     "Scales effective fire distance and damage drop-off "
                     "start/length together.")
        self._slider(f, "far_damage", "Damage at extreme range", 25, 400, 5, 100, fmt_pct,
                     "Past the drop-off distance a shot keeps only a fraction "
                     "of its damage - vanilla 10 to 60 % depending on the gun. "
                     "This is the floor under that, capped at 100 % (full "
                     "damage at any range). Armour penetration at range moves "
                     "with it, but it already sits at 100 % in vanilla, so "
                     "there only values below 100 % change anything. The range "
                     "slider above moves the distances, this one the damage "
                     "left behind them. Not play-tested yet.")
        self._slider(f, "wbleed", "Weapon bleeding", 0, 300, 5, 100, fmt_pct,
                     "Bleeding chance and intensity your shots inflict. "
                     "0 % = your bullets never cause bleeding.")
        self._slider(f, "adsmove", "ADS movement speed", 50, 200, 10, 100, fmt_pct,
                     "How fast you move while aiming down sights "
                     "(vanilla varies 58–150 % of run speed per weapon).")
        self._slider(f, "aimspeed", "ADS aim-in speed", 25, 400, 5, 100, fmt_pct,
                     "How fast the weapon comes up into the sights, incl. "
                     "offset and lean aiming (vanilla ~0.5 s). 200 % = "
                     "twice as snappy. Not play-tested yet – watch for "
                     "aim animation glitches and report back.")
        self._slider(f, "magazine", "Magazine size", 50, 300, 5, 100, fmt_pct,
                     "Scales weapon base capacity AND all magazine "
                     "attachments (launchers never drop below 1 round). "
                     "Per category or per weapon: 'Magazine size' is the "
                     "tenth factor in the trees below.")
        self._slider(f, "melee", "Melee damage (knife & butt strike)", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "shoot_shake", "Shooting camera shake", 0, 200, 10, 100, fmt_pct,
                     "How much the camera shakes when YOU fire (every "
                     "weapon's own shake entry, vanilla scale 1.0). 0 % = "
                     "none, like the 'No Screenshake' mod. Being hit is "
                     "the separate 'Hit camera shake' slider on the Combat "
                     "tab. Not play-tested yet.")
        self._slider(f, "ads_zoom", "ADS zoom", 0, 200, 10, 100, fmt_pct,
                     "How much the view zooms in when aiming down sights "
                     "(vanilla FOV factor 0.92 for most weapons, 0.83 for "
                     "some). 0 % = no zoom at all, 200 % = twice the vanilla "
                     "zoom. Scopes keep their own magnification. Not "
                     "play-tested yet.")
        self._slider(f, "bullet_drop", "Bullet drop", 0, 300, 5, 100, fmt_pct,
                     "How far bullets fall over distance (vanilla drop height "
                     "170 on every weapon class). 0 % = flat trajectory, like "
                     "'Fully Unlocked Ballistics'. NPC bullets are unchanged. "
                     "Not play-tested yet.")
        self._slider(f, "bullet_speed", "Bullet speed", 50, 300, 5, 100, fmt_pct,
                     "Flight speed of the 11 bullet types (vanilla 20000 to "
                     "42000). Gauss, RPG and grenade launcher rounds are "
                     "untouched. Faster = less lead on moving targets. Not "
                     "play-tested yet.")
        self._slider(f, "melee_range", "Melee range (knife & butt strike)", 50, 300, 5, 100, fmt_pct,
                     "How far the knife and the butt strike reach (vanilla "
                     "1.6 m for both). The 'Increased Melee Range' idea from "
                     "Nexus. Not play-tested yet.")
        self._slider(f, "reload", "Reload speed", 50, 300, 5, 100, fmt_pct,
                     "Scales every reload-time multiplier the game keeps per "
                     "weapon and magazine (vanilla 1.0 everywhere, the fields "
                     "the official Zone Kit guide points at). 200 % = half the "
                     "time. Edition weapons (Deluxe/Pre-order) stay vanilla. "
                     "NOT play-tested yet - the animation may or may not "
                     "follow, report back.")
        self._slider(f, "anim_skip", "Skipped shooting animations (experimental)", 0, 3, 1, 0, fmt_int,
                     "The game's own ShootingAnimationNumberToSkip, vanilla 0 "
                     "on every weapon. It is the only config key that touches "
                     "the shooting animation at all - speed and sound live in "
                     "baked assets no config patch can reach. If you raise a "
                     "weapon's fire rate and the animation lags behind, try 1 "
                     "(skip every other animation) or 2. The animation gets "
                     "choppier, but it stops trailing the shots. Read from the "
                     "key name only, never play-tested - tell us what you see.")
        self._slider(f, "equip_speed", "Weapon draw & holster speed", 50, 400, 5, 100, fmt_pct,
                     "How fast a weapon is raised and put away (the game's "
                     "ShowEquipmentTime and HideEquipmentTime, vanilla 1.0 on "
                     "every weapon). 200 % = half the time. Unlike the reload "
                     "slider this one also covers the Deluxe and Pre-order "
                     "weapons. The same animation caveat applies: the timing "
                     "value changes, the animation may not follow. Not "
                     "play-tested yet.")
        self._check(f, "stat_bars",
                    "Inventory stat bars follow your changes",
                    "The damage/range/fire-rate bars in the inventory are "
                    "decoration: the game never computes them from the "
                    "real values, they are fixed numbers on every weapon. "
                    "Tick this and they move with your sliders, per "
                    "weapon and per category. Accuracy and handling are "
                    "left alone - they mix dispersion, recoil and weight, "
                    "and there is no honest formula for them. Cosmetic "
                    "only, it changes no damage. Not play-tested yet.")
        self._slider(f, "jam_chance", "Weapon jam chance", 0, 200, 5, 100, fmt_pct,
                     "How often a worn weapon jams. Vanilla runs from 4.5 "
                     "to 15 depending on the gun, and this scales each "
                     "one; 0 % = weapons never jam at all. The condition "
                     "at which jamming starts is left alone. Stacks with "
                     "the difficulty jamming multiplier. Not play-tested "
                     "yet.")
        self._slider(f, "jam_clear", "Jam clearing speed", 50, 400, 5, 100, fmt_pct,
                     "How fast a jam is cleared (vanilla 4 to 5.5 s per "
                     "weapon). 200 % = half the time. Not play-tested yet.")
        self._slider(f, "recoil_recovery", "Recoil & spread recovery", 25, 400, 5, 100,
                     fmt_pct,
                     "How quickly the weapon settles back down after a shot. "
                     "Recoil and spread each have their own recovery time in "
                     "vanilla (0.25 to 0.8 s); 200 % halves both. Not "
                     "play-tested yet.")
        self._slider(f, "spread_bloom", "Spread build-up", 0, 300, 5, 100, fmt_pct,
                     "How much the spread widens while you keep firing "
                     "(vanilla up to 1.5, and 39 weapons have no build-up at "
                     "all - those stay that way). 0 % = the spread never grows "
                     "during a burst. Recoil has no build-up in vanilla, so "
                     "this only touches spread. Not play-tested yet.")
        self._slider(f, "aim_steady", "Aim & crouch steadiness", 0, 300, 5, 100,
                     fmt_pct,
                     "How much aiming down the sights and crouching calm the "
                     "weapon (experimental). Vanilla: crouching takes 15 % off "
                     "the recoil, and on 71 weapons aiming removes the spread "
                     "entirely. Capped at 'removes it completely' - the game "
                     "data has nothing stronger, and what it would do with "
                     "more is anyone's guess. Not play-tested yet.")
        self._slider(f, "bullet_pen", "Bullet wall penetration", 0, 300, 5, 100,
                     fmt_pct,
                     "Chance that a bullet carries on through what it hits "
                     "(vanilla 0 to 1.0 depending on the round; rounds at 0 "
                     "stay at 0). Capped at 100 %. Not play-tested yet.")
        self._slider(f, "bullet_pen_depth", "Bullet penetration depth", 25, 400, 5, 100,
                     fmt_pct,
                     "How thick a wall a bullet can still come through "
                     "(vanilla 150 to 300 on the 16 projectile types). The "
                     "slider above decides IF it punches through, this one "
                     "how far. Not play-tested yet.")
        self._slider(f, "bullet_range", "Bullet max range", 25, 400, 5, 100, fmt_pct,
                     "How far a projectile flies before it is removed "
                     "(vanilla 100000 for every round - 1 km). Rarely the "
                     "limit you notice, but it is the hard ceiling. Not "
                     "play-tested yet.")
        self._slider(f, "hip_steady", "Hip-fire stance effect", 0, 300, 5, 100,
                     fmt_pct,
                     "How much your stance changes hip fire. Vanilla: "
                     "crouching takes 0.2 off the spread, jumping adds 0.3. "
                     "0 % = stance makes no difference from the hip, 200 % "
                     "doubles both. The aiming counterpart is the slider "
                     "above. Not play-tested yet.")
        self._slider(f, "move_steady", "Movement effect on aim", 0, 300, 5, 100,
                     fmt_pct,
                     "How much walking and running spoil your aim (vanilla "
                     "adds 0.1 to 1.0 to the spread, depending on the "
                     "weapon). 0 % = moving costs you no accuracy at all. "
                     "Not play-tested yet.")
        self._slider(f, "recoil_pattern", "Recoil pattern reset", 25, 400, 5, 100,
                     fmt_pct,
                     "How long you have to stop shooting before the recoil "
                     "pattern starts from the top again (vanilla 0.3 s, a "
                     "few weapons 1 to 5 s). The pattern's DIRECTION lives "
                     "in a packed asset and cannot be changed from config - "
                     "only this pause and the strength. Not play-tested yet.")
        self._check(f, "chamber_round",
                    "Every weapon keeps a round in the chamber",
                    "65 of the 92 weapons already give you one extra round "
                    "after reloading; this brings the other 27 in line. Not "
                    "play-tested yet.")
        self._slider(f, "dropped_ammo", "Ammo in dropped weapons", 0, 400, 5, 100,
                     fmt_pct,
                     "How much ammunition sits in the weapon of a dead NPC "
                     "(vanilla 1 to 10 rounds). Weapons whose value is unset "
                     "in vanilla are left alone. Whole rounds. Not "
                     "play-tested yet.")
        self._slider(f, "weapon_noise", "Weapon noise", 0, 300, 5, 100, fmt_pct,
                     "How loud your weapon is - what NPCs actually hear "
                     "(vanilla 0.6 to 0.8; silenced cases sit at 0 and stay "
                     "there). 0 % = nobody hears your shots. This is the "
                     "missing half of the stealth sliders, which so far only "
                     "changed how well NPCs hear. Not play-tested yet.")
        self._slider(f, "butt_wear", "Weapon wear per butt strike", 0, 300, 5, 100, fmt_pct,
                     "Every butt strike costs the weapon 5 durability in "
                     "vanilla. 0 % = bash crates for free, like 'The weapon "
                     "doesn't break when used to strike with the butt'. Not "
                     "play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Pistol slot")
        self._slider(f, "pistol_slot", "Pistol slot accepts", 0, 3, 1, 0, fmt_slot,
                     "Lets SMGs, shotguns or any weapon sit in the sidearm "
                     "slot; the two main slots keep taking every weapon. The "
                     "'SMG in pistol slot' and 'Any weapon as sidearm' mods. "
                     "Not play-tested yet.")
        ctk.CTkLabel(
            f, text="   \u26a0 Compatibility: NOT compatible with OXA (it redefines "
                    "the weapons) and it conflicts with any mod that patches "
                    "the same weapon entries (Better Ballistics and the like; "
                    "the mod scan will tell you). Known quirks from the Nexus "
                    "mods: the stat comparison then always compares against "
                    "the sidearm-slot weapon, and long guns are still held "
                    "two-handed.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color="#E0A040").pack(fill="x", padx=12)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Aim assist (controls)")
        ctk.CTkLabel(
            f, text="   The game applies aim assist to gamepads AND, more "
                    "lightly, to the mouse (stickiness and magnetism cones). "
                    "Its strength lives in curve assets that cannot be "
                    "patched, so these switches turn it off completely by "
                    "unhooking the cones. Not play-tested yet.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._check(f, "no_aim_mouse", "Turn aim assist off for the mouse")
        self._check(f, "no_aim_gamepad", "Turn aim assist off for gamepads")
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._warning(f, "A Nexus user reports the fire-rate factor desyncs the "
                         "firing animation and sound from the actual shots "
                         "\u2013 same engine limitation as movement speed. Test "
                         "in-game before settling on values. "
                         "(Status: 01 Sep 2026)",
                      title="Known issue \u2014 game patch 2.0")
        for cat, cat_label in WEAPON_CATEGORY_LABELS.items():
            self._collapsible_category(f, cat, cat_label)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single weapon overrides (advanced)")
        ctk.CTkLabel(
            f, text="   ×1 (vanilla) = no override – the category/global "
                    "factors still apply to this weapon.",
            anchor="w", font=ctk.CTkFont(size=12),
            text_color=MUTED).pack(fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a category, then a weapon, to edit its factors.",
            anchor="w", font=ctk.CTkFont(size=12),
            text_color=MUTED).pack(fill="x", padx=12, pady=(0, 2))
        # Uebersicht und "alles loeschen" stehen UEBER dem Baum: der kann auf
        # 79 Zeilen anwachsen, darunter waeren beide nur mit Scrollen erreichbar.
        self.iw_info = ctk.CTkLabel(
            f, text="No per-weapon overrides set.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color=MUTED)
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "ammo_dmg", "Ammo damage", 25, 300, 5, 100, fmt_pct)
        self._slider(f, "ammo_ap", "Ammo armor piercing", 0, 300, 5, 100, fmt_pct)
        self._slider(f, "ammo_ad", "Ammo armor damage", 25, 300, 5, 100, fmt_pct)
        self._slider(f, "ammo_cover", "Ammo cover penetration", 0, 300, 5, 100, fmt_pct,
                     "How well bullets punch through wooden walls, fences etc.")
        self._slider(f, "ammo_stack", "Ammo stack size", 1, 20, 0.5, 1, fmt_factor,
                     "How many rounds fit in one inventory slot (vanilla 900 "
                     "for every round). × 10 = 9000. Per round in the tree "
                     "below as the fifth factor. Worth pairing with 'Max carry "
                     "weight' and 'Item weight': in vanilla you hit the weight "
                     "limit long before the stack limit - 900 rounds of 7.62 "
                     "already weigh 21.6 kg of your 80. Not play-tested yet.")
        self._slider(f, "ammo_pack", "Ammo pack size", 25, 400, 5, 100, fmt_pct,
                     "How many rounds one picked-up pack contains "
                     "(vanilla 30 for rifle rounds, 10 to 50 for the "
                     "rest). Launcher grenades come one at a time in "
                     "vanilla and stay that way. Whole numbers, never "
                     "below one. Not play-tested yet.")
        self._slider(f, "ammo_bleed", "Ammo bleeding", 0, 300, 5, 100, fmt_pct,
                     "How much bleeding a hit from this round causes. "
                     "Vanilla is 1.0 on every round, so this is a clean "
                     "global dial; 0 % = rounds never start bleeding. The "
                     "weapon's own bleeding value applies on top. Not "
                     "play-tested yet.")
        self._slider(f, "ammo_recoil", "Ammo recoil", 0, 300, 5, 100, fmt_pct,
                     "Recoil contributed by the round itself (vanilla 1.0 "
                     "everywhere). Stacks with the weapon recoil slider "
                     "and with recoil upgrades. Not play-tested yet.")
        self._slider(f, "ammo_flat", "Ammo trajectory flatness", 25, 300, 5, 100,
                     fmt_pct,
                     "Higher = flatter flight path, so less drop at "
                     "distance. Vanilla runs from 1.0 to 1.9 depending on "
                     "the round, and this scales each one. Not "
                     "play-tested yet.")
        self._slider(f, "ammo_wear", "Ammo weapon wear", 0, 300, 5, 100, fmt_pct,
                     "How hard a round is on the barrel (vanilla 0.8 to "
                     "1.3 - cheap rounds wear more). 0 % = this round "
                     "never wears the weapon. Stacks with the weapon "
                     "durability slider. Not play-tested yet.")
        self._slider(f, "ammo_disp", "Ammo spread", 0, 300, 5, 100, fmt_pct,
                     "Spread the round itself adds (vanilla 1.0 on 33 of "
                     "the 35 rounds, 1.2 on two). 0 % = the round adds no "
                     "spread at all. Stacks with the weapon spread slider. "
                     "Not play-tested yet.")
        self._slider(f, "ammo_aimdisp", "Ammo spread while aiming", 0, 300, 5, 100,
                     fmt_pct,
                     "The same thing while aiming down sights (vanilla 1.0, "
                     "two rounds sit at 10.0 - those are the ones that are "
                     "meant to be fired from the hip). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single ammo overrides (advanced)")
        ctk.CTkLabel(
            f, text="   ×1 (vanilla) = no override – the global ammo slider "
                    "above applies to this round. Any other value REPLACES "
                    "the global slider for that factor on this round – the "
                    "two do not stack.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12),
            text_color=MUTED).pack(fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a caliber, then a round, to edit its factors.",
            anchor="w", font=ctk.CTkFont(size=12),
            text_color=MUTED).pack(fill="x", padx=12, pady=(0, 2))
        self.ia_info = ctk.CTkLabel(
            f, text="No per-ammo overrides set.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color=MUTED)
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "ap_strike", "Physical (bullets & melee)", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "ap_burn", "Burn (fire)", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "ap_shock", "Shock (electric)", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "ap_chem", "Chemical", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "ap_rad", "Radiation", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "ap_psy", "PSY", 25, 400, 5, 100, fmt_pct)
        self._slider(f, "dur_armor", "Armor durability", 0.5, 10, 0.1, 1, fmt_factor,
                     "Armor takes more punishment before breaking.")
        self._slider(f, "armor_wear", "Armor wear coefficient (experimental)", 0, 1, 0.05, 0.7, fmt_dec,
                     "The game's ArmorDurabilityParamsCoef and "
                     "HelmetDurabilityParamsCoef (vanilla 0.7). They tie a "
                     "piece's condition to its protection, but the direction "
                     "is unknown: either 'protection left at zero durability' "
                     "or the opposite. Try 0.3 against 1.0 in-game and tell "
                     "us. Not play-tested yet.")
        self._slider(f, "ap_carry", "Armor carry-weight bonuses", 0, 300, 5, 100, fmt_pct,
                     "Exoskeleton & armor/upgrade carry bonuses. "
                     "0 % = armor grants no extra carry weight.")
        self._slider(f, "art_slots", "Extra artifact slots on every body armor", 0, 4, 1, 0, fmt_plus,
                     "Adds slots to each body armor's own count (vanilla: "
                     "most have 2, a few 0, 1, 3 or 4, three have 5). Capped "
                     "at 5, the game's maximum. Helmets are untouched. "
                     "Like the 'Armor Artifact Slots' mod. Not play-tested yet.")
        self._slider(f, "prot_cap", "Protection caps", 50, 200, 5, 100, fmt_pct,
                     "The game caps your total protection at 90 % (85 % "
                     "radiation, physical 4.5) - anything armor and artifacts "
                     "give beyond that is lost. 111 % lifts the percent caps to "
                     "100 (the maximum), physical scales freely. Like the 'Max "
                     "Stats Patch'. Not play-tested yet.")
        self._slider(f, "cap_other", "Stamina & bleeding caps", 50, 1000, 10, 100, fmt_pct,
                     "The same list holds two more ceilings that nothing else "
                     "here touches: stamina regeneration from artifacts and "
                     "upgrades stops counting at 30, bleeding resistance at 5. "
                     "Worth raising if you stack stamina artifacts. Not "
                     "play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Gear condition")
        self._slider(f, "gear_dur", "Weapon & armor max condition", 25, 500, 5, 100, fmt_pct,
                     "The condition bar's full length - vanilla runs from "
                     "1,125 to 3,000 for guns and 520 to 1,040 for armor. "
                     "500 % = five times as much to wear through, like "
                     "'Better Durability'. ⚠ An item's condition is stored in "
                     "your save, so this only shows on gear that spawns AFTER "
                     "you install the mod. Not play-tested yet.")
        self._slider(f, "anom_wear", "Anomaly wear on gear", 0, 300, 5, 100, fmt_pct,
                     "How much condition an anomaly hit costs your armour, "
                     "helmet and both weapons (vanilla 0.2 to 25 per hit "
                     "depending on the anomaly - the Clicker and Carousel are "
                     "the brutal ones). 0 % = anomalies no longer damage your "
                     "gear at all. Separate from the butt-strike slider in the "
                     "Weapons tab. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Grenades vs armor")
        self._slider(f, "grenade_resist", "Armor grenade resistance", 0, 300, 5, 100, fmt_pct,
                     "How much grenade and explosion damage each armor class "
                     "absorbs (vanilla 0 / 10 / 20 / 40 / 60 % for physical "
                     "protection classes 0-4, capped at 100 %). 0 % = "
                     "grenades ignore armor. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single armor overrides (advanced)")
        ctk.CTkLabel(
            f, text="   \u00d71 (vanilla) = no override \u2013 the global sliders "
                    "above apply to this armor. Any other value REPLACES the "
                    "global slider for that protection type on this piece "
                    "\u2013 the two do not stack. Durability and carry bonuses "
                    "stay global: they work through different game systems.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        ctk.CTkLabel(
            f, text="   Expand a group, then an armor piece, to edit its "
                    "protection factors.",
            anchor="w", font=ctk.CTkFont(size=12),
            text_color=MUTED).pack(fill="x", padx=12, pady=(0, 2))
        self.ir_info = ctk.CTkLabel(
            f, text="No per-armor overrides set.", anchor="w", justify="left",
            wraplength=780, font=self._iw_font_hint, text_color=MUTED)
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

        body = self._tab("Upgrades")
        f = self._section(body, "Upgrade strength (technician upgrades)")
        ctk.CTkLabel(
            f, text="   Scales what each installed upgrade does (vanilla mostly "
                    "+10 to +30 %). Only upgrades you actually install change; "
                    "penalty parts of an upgrade stay vanilla. Percent bonuses "
                    "cap at 100 %. Not play-tested yet.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "upg_accuracy", "Accuracy upgrades (spread)", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "recoil_upgrades", "Recoil reduction from upgrades", 100, 2000, 10, 100, fmt_pct,
                     "Multiplies the recoil reduction of weapon upgrades and "
                     "attachments (vanilla -5 % to -30 %), capped at -100 %. "
                     "2000 % = any recoil upgrade removes the kick entirely. "
                     "Community-proven on patch 2.0 (same route as the "
                     "'Dead Steady' mod).")
        self._slider(f, "upg_handling", "Handling upgrades (aim time, ADS move, sway, draw, recovery, capacity)", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_durability", "Durability upgrades (weapons & armor)", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_range", "Range & ballistics upgrades", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_damage", "Damage & penetration upgrades", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_weight", "Weight reduction upgrades", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_breath", "Breath-hold upgrades", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_armor_prot", "Armor protection upgrades", 0, 500, 10, 100, fmt_pct)
        self._slider(f, "upg_armor_misc", "Armor stamina-regen upgrades", 0, 500, 10, 100, fmt_pct)
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Technician upgrade rules")
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

        f = self._section(body, "Scopes")
        self._slider(f, "scope_zoom", "Scope magnification", 25, 200, 5, 100, fmt_pct,
                     "Scales the zoom of every scope class (vanilla 2x -43 %, "
                     "3x -51 %, 4x -60 %, 8x -70 % of the FOV; capped at -90 %). "
                     "Not play-tested yet.")
        self._slider(f, "scope_penalty", "Scope handling penalties", 0, 200, 10, 100, fmt_pct,
                     "The aim-time and ADS-movement penalties scopes carry "
                     "(vanilla +7 to +20 % aim time, -5 to -10 % movement). "
                     "0 % = none. Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Single scope overrides (advanced)")
        ctk.CTkLabel(
            f, text="   Open a scope class and set magnification and handling "
                    "penalties per scope. A scope's own factor REPLACES the two "
                    "global sliders above for that scope. Collimators and holo "
                    "sights have no zoom effect; those with an aim-time penalty "
                    "are listed. The list fills after the game data is loaded. "
                    "Not play-tested yet.",
            anchor="w", justify="left", wraplength=780,
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._scope_box = ctk.CTkFrame(f, fg_color="transparent")
        self._scope_box.pack(fill="x")
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
        self._slider(f, "exp_containers", "Explosive containers durability (experimental)", 25, 300, 5, 100, fmt_pct,
                     "How much damage gas cylinders, canisters and fuel barrels "
                     "take before they blow (vanilla threshold 20 to 50). 25 % "
                     "= they pop from almost any hit - which also means "
                     "scripted set pieces can go off earlier than intended. "
                     "Not play-tested yet.")
        self._slider(f, "push_force", "Push and kick force (experimental)", 25, 300, 5, 100, fmt_pct,
                     "How hard you shove physics props and bodies out of the "
                     "way (vanilla 20 for a lab jar up to 27000 for an ammo "
                     "crate, 3500 for a corpse). High values can throw objects "
                     "around wildly. Not play-tested yet.")
        self._slider(f, "clicker", "Clicker anomaly strength", 0, 200, 10, 100, fmt_pct,
                     "The flashbang-like Clicker anomaly: number of flashes "
                     "(vanilla 20) and burn per hit (vanilla 70). 0 % = one "
                     "harmless flash, like 'FlashbangAnomalyNerf'. Not "
                     "play-tested yet.")
        self._slider(f, "radiation", "Radiation accumulation", 0, 5, 0.1, 1, fmt_factor,
                     "× 0 = no radiation buildup.")
        self._slider(f, "rad_dose", "Radiation dose per second", 25, 300, 5, 100, fmt_pct,
                     "How fast radiation fields fill your bar (vanilla 1 / 3 / "
                     "6 points per second for light, medium and strong fields; "
                     "the strong ones fill it in about 17 s). Stacks with "
                     "'Radiation accumulation' above. The deadly map-border "
                     "zones are never touched. Not play-tested yet.")
        self._slider(f, "rad_filter", "Radiation screen filter", 0, 150, 10, 100, fmt_pct,
                     "Strength of the green screen filter inside radiation "
                     "fields (vanilla 0.45 to 0.75, capped at 1). 0 % = no "
                     "filter - watch the geiger counter instead. Not "
                     "play-tested yet.")
        self._slider(f, "geiger", "Geiger counter volume", 0, 200, 10, 100, fmt_pct,
                     "How loud the geiger crackle gets in a field (vanilla 0.2 "
                     "to 0.8, capped at 1). Not play-tested yet.")
        self._slider(f, "barbed_wire", "Barbed wire damage", 0, 300, 5, 100, fmt_pct,
                     "Damage, bleeding and armor wear from barbed wire "
                     "(vanilla 10 damage, 25 bleeding points, 5 armor damage, "
                     "10 % bleeding chance; both fence types). 0 % = wire is "
                     "harmless. Not play-tested yet.")
        self._slider(f, "bleeding", "Bleeding intensity", 0, 5, 0.1, 1, fmt_factor)
        self._slider(f, "hunger", "Hunger rate", 0, 300, 10, 100, fmt_pct,
                     "0 % = never get hungry.")
        self._slider(f, "sleep", "Sleepiness rate", 0, 300, 10, 100, fmt_pct,
                     "0 % = never get sleepy.")
        self._slider(f, "consumable", "Consumable strength", 25, 300, 5, 100, fmt_pct,
                     "Medkits, bandages, food, drinks: healing, bleeding/"
                     "radiation removal, stamina etc. Penalties (drunkness, "
                     "spoiled food) stay vanilla.")
        self._slider(f, "healing", "Medkit & bandage healing", 25, 400, 5, 100, fmt_pct,
                     "Health restored by medical items only (medkits and "
                     "bandages, vanilla 20\u2013100 HP) \u2013 food and drink healing "
                     "is not affected. Stacks with Consumable strength: "
                     "both at 200 % = 4\u00d7 healing.")
        self._slider(f, "cons_duration", "Consumable effect duration", 25, 400, 5, 100, fmt_pct,
                     "How long running consumable effects last (energy "
                     "drink 45 s, Hercules 5 min, cinnamon, vodka/psy-block "
                     "...). Instant effects (healing, bleeding stop, "
                     "anti-rad, 1-2 s) are untouched on purpose.")
        self._slider(f, "rain", "Rain & storm frequency", 0, 300, 5, 100, fmt_pct,
                     "Weight of rainy/stormy/thunder weather in the rotation. "
                     "0 % = practically always dry.")
        self._slider(f, "emission", "Emission frequency", 25, 400, 5, 100, fmt_pct,
                     "How often emissions build up (quest-controlled "
                     "no-emission zones stay untouched).")
        self._slider(f, "emission_dur", "Emission duration", 25, 400, 5, 100, fmt_pct,
                     "Stretches the whole emission timeline together - "
                     "warning siren, shockwave, deadly phase and aftermath "
                     "(vanilla ~1 min warning + ~1 min active). Story "
                     "emissions keep their scripted timing.")
        self._slider(f, "day_length", "Day length", 25, 400, 5, 100, fmt_pct,
                     "How long a full day-night cycle takes in real time "
                     "(vanilla: one game day per real hour). 200 % = two "
                     "hours per day, the day/night ratio stays vanilla.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Sky & night (experimental — untested file)")
        self._warning(f, "These six values live in a game file no mod has "
                         "patched before, and their names do not appear in the "
                         "game executable - the engine may read them from a "
                         "blueprint instead, or ignore them entirely. Nothing "
                         "here is verified in-game. Try them, and tell us what "
                         "you see.",
                      title="Untested file — sky & night")
        self._slider(f, "moon", "Moon brightness", 0, 300, 5, 100, fmt_pct,
                     "Vanilla 1.046. 0 % = pitch-black nights. Not play-tested yet.")
        self._slider(f, "sun", "Sun brightness", 50, 200, 10, 100, fmt_pct,
                     "Vanilla 3.14. Not play-tested yet.")
        self._slider(f, "stars", "Stars", 0, 500, 10, 100, fmt_pct,
                     "Vanilla 0.1 - the stars are barely visible. Not "
                     "play-tested yet.")
        self._slider(f, "cloud_opacity", "Cloud opacity", 30, 140, 10, 100, fmt_pct,
                     "Vanilla 0.7, capped at 1. Not play-tested yet.")
        self._slider(f, "cloud_speed", "Cloud speed", 25, 400, 5, 100, fmt_pct,
                     "Vanilla 1. Not play-tested yet.")
        self._slider(f, "dusk_length", "Dusk & dawn length", 25, 300, 5, 100, fmt_pct,
                     "How long the light takes to fade between day and night "
                     "(vanilla 2 game hours). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Bodies & weather")
        self._slider(f, "corpse_time", "Bodies stay", 25, 500, 10, 100, fmt_pct,
                     "How long dead bodies remain (vanilla 30 min near you, "
                     "15 min once seen, 5 min once looted). Since 1.28.0 also "
                     "the 3 s grace after you look away and the offline "
                     "coefficient. Like 'Corpse Despawn Time Increased'. Not "
                     "play-tested yet.")
        self._slider(f, "corpse_max", "Max bodies near you", 4, 40, 1, 10, fmt_int,
                     "How many bodies the game keeps around you before it "
                     "starts removing the oldest (vanilla 10). Higher costs "
                     "performance. Not play-tested yet.")
        self._slider(f, "corpse_distance", "Corpse distance", 50, 300, 5, 100, fmt_pct,
                     "The radii the corpse system works with: bodies go "
                     "offline beyond 100 m, the time and count rules apply "
                     "within 50 / 30 m, overpopulated bodies are destroyed "
                     "beyond 300 m - all scaled together (the game stores "
                     "the first three squared, the tool squares the factor). "
                     "Not play-tested yet.")
        self._slider(f, "corpse_hardcap", "A-Life corpse hard cap", 500, 5000, 100, 1500, fmt_int,
                     "Global ceiling of bodies the A-Life keeps at all "
                     "(vanilla 1500). Not play-tested yet.")
        self._slider(f, "weather_dur", "Weather duration", 25, 400, 5, 100, fmt_pct,
                     "How long each weather lasts before the next roll "
                     "(vanilla mostly 8 to 20 minutes). Not play-tested yet.")
        self._slider(f, "weather_transition", "Weather transition speed (experimental)", 25, 400, 5, 100, fmt_pct,
                     "How fast one weather morphs into the next (vanilla "
                     "multiplier 1 on all 22 transition steps). 200 % = twice "
                     "as fast. The exact meaning of the multiplier is not "
                     "verified. Not play-tested yet.")
        self._slider(f, "item_despawn", "Dropped items stay", 25, 500, 10, 100, fmt_pct,
                     "How long items lying in the world remain (vanilla 1 h "
                     "untouched, 3 h otherwise). Not play-tested yet.")
        self._slider(f, "day_start", "Day starts at", 3, 10, 1, 6, fmt_hours,
                     "The hour the game counts as day (vanilla 6; dawn 4 "
                     "moves along if needed). Which systems read these "
                     "phases is not verified - experimental.")
        self._slider(f, "evening_start", "Evening starts at", 16, 23, 1, 20, fmt_hours,
                     "The hour the game counts as evening (vanilla 20). "
                     "Experimental.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Travel & teleports")
        self._slider(f, "ft_lock", "Fast travel when overweight", 0, 2, 1, 2, fmt_lock,
                     "Vanilla guides refuse to travel while you are overweight "
                     "('Full' lock). 'Partial' and 'No lock' are the two other "
                     "values the game engine knows. Not play-tested yet.")
        self._slider(f, "guide_delay", "Guide delay", 0, 300, 5, 100, fmt_pct,
                     "The GuideDelay value every guide carries (vanilla 120). "
                     "Its exact meaning in-game is not verified; 0 % = no delay. "
                     "The cost is on the Economy tab. Not play-tested yet.")
        self._check(f, "teleports_instant", "Instant teleports (no fade to black)",
                    "Every teleport effect (guides, quests) becomes instant "
                    "(like 'InstaTeleports'). Not play-tested yet.")
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "stash_loot", "Stash & body loot amount", 25, 400, 5, 100, fmt_pct,
                     "How many items a stash or body yields (whole numbers, "
                     "never below 1).")
        self._slider(f, "stash_chance", "Stash & body find chance", 25, 400, 5, 100, fmt_pct,
                     "Chance that a slot yields anything at all. Capped at "
                     "100 %, so raising it helps less than the number suggests "
                     "– many slots already sit close to the cap. Lowering it "
                     "works in full.")
        self._slider(f, "stash_ammo", "Stash & body ammo bonus", 25, 400, 5, 100, fmt_pct,
                     "Extra rounds handed out to match the weapon caliber, on "
                     "top of the item list above.")
        self._slider(f, "stash_sets", "Stash item variety", 25, 400, 5, 100, fmt_pct,
                     "How many different item groups a stash rolls "
                     "(vanilla 2 to 5, a few up to 15). This is the other "
                     "axis to the amount slider above: more KINDS of loot "
                     "rather than bigger piles. Whole numbers, never below "
                     "one. Not play-tested yet.")
        self._slider(f, "stash_clue", "Stash clues on bodies", 0, 1000, 10, 100, fmt_pct,
                     "Chance that a dead NPC carries a stash clue (vanilla 2 % "
                     "plus 1 % per clue already found, per region; capped at "
                     "100 %). 0 % = never, like 'More Stash Clues' in reverse. "
                     "Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Loot amount (NPCs, containers, world)")
        self._slider(f, "container_respawn", "Containers refill after", 0, 168, 6, 0, fmt_hours,
                     "Respawn time of every container type (vanilla 0 = never). "
                     "Experimental: in-game hours, could refill world crates and "
                     "safes. Not play-tested yet.")
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
            font=ctk.CTkFont(size=12), text_color=MUTED).pack(fill="x", padx=12)
        self._slider(f, "loot_reroll", "Loot re-roll radius on rank-up", 25, 500, 10, 100, fmt_pct,
                     "When your rank goes up, the game re-rolls the loot in "
                     "containers and stashes within 400 m (vanilla). Larger = "
                     "more of the world refreshes at once. Not play-tested yet.")
        self._slider(f, "loot_reroll_time", "Loot re-roll delay on rank-up", 25, 500, 10, 100, fmt_pct,
                     "How long the game waits after the rank-up before it "
                     "re-rolls (vanilla 10 s). Not play-tested yet.")
        self._slider(f, "loot_amount", "Loot amount (NPCs, containers, world)",
                     25, 400, 5, 100, fmt_pct,
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
               "afterwards, put this slider back to 100 %.",
            title="Large patch")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Artifacts")
        self._slider(f, "art_effect", "Artifact effect strength", 25, 300, 5, 100, fmt_pct,
                     "Scales what artifacts do on your belt – positive effects "
                     "AND side effects alike (radiation has its own slider below).")
        self._slider(f, "art_radiation", "Artifact radiation side-effect", 0, 200, 10, 100, fmt_pct,
                     "0 % = artifacts emit no radiation at all.")
        self._slider(f, "art_spawn", "Artifact spawn chance", 25, 400, 5, 100, fmt_pct,
                     "Chance that anomaly fields spawn an artifact "
                     "(vanilla 25–40 %, capped at 100 %).")
        self._slider(f, "art_rarity", "Rare artifact bias", 25, 500, 10, 100, fmt_pct,
                     "Shifts the rarity roll toward Uncommon/Rare/Epic at "
                     "Common's expense. Ranks that can't roll Rare/Epic in "
                     "vanilla (e.g. Newbie) still won't.")
        self._slider(f, "art_count", "Artifacts per anomaly field", 1, 5, 0.1, 1, fmt_factor,
                     "How many artifacts a field hands out per spawn "
                     "(vanilla 1). Which artifacts a field CAN spawn stays "
                     "its vanilla list.")
        self._slider(f, "art_respawn", "Artifact respawn speed", 25, 400, 5, 100, fmt_pct,
                     "How fast fields cool down before the next artifact "
                     "(vanilla mostly 3-15, some 60-120). Fields with no "
                     "cooldown stay as they are.")
        self._slider(f, "weird_art", "Weird artifacts (DLC): charge & duration", 25, 1000, 10, 100, fmt_pct,
                     "The Cost of Hope 'weird' artifacts run on a charge "
                     "(bolt 300) or a timer (flower 2 h). 1000 % = practically "
                     "no recharge, like 'NoWeirdArtifactRecharge'. Not "
                     "play-tested yet.")
        self._slider(f, "art_radius", "Artifact 'Radius' value (unproven)", 1, 20, 0.1, 1, fmt_factor,
                     "Every artifact carries a Radius of 40 cm. We built this "
                     "slider believing that is what 'Less Shy Artifacts' "
                     "changes - since then we have read that mod's files, and "
                     "it does something else entirely: it raises the "
                     "DETECTOR's ShowArtifactRadius. So what this key does is "
                     "genuinely unknown, and the slider may do nothing. If you "
                     "want artifacts to show up from further away, use "
                     "'Detector & scanner range' in the World tab instead - "
                     "that is the key the mod actually uses. Not play-tested "
                     "yet.")
        self._check(f, "art_no_hop", "Artifacts don't hop away",
                    "146 of the 154 artifacts jump away when you get close; "
                    "this switches that off. The eight that already stay put "
                    "(the weird DLC ones and two quest artifacts) are left "
                    "alone. Not play-tested yet.")
        self._slider(f, "art_keepaway", "Artifact keep-away distance (experimental)", 25, 300, 5, 100, fmt_pct,
                     "How far a hopping artifact tries to stay away from you "
                     "(vanilla 10 m, plus the 6 m at which hopping starts at "
                     "all). Whether lower really means easier to catch is "
                     "untested. Not play-tested yet.")
        self._slider(f, "art_hop_pause", "Artifact hop pause (experimental)", 25, 400, 5, 100, fmt_pct,
                     "Pause between two hop series (vanilla 15 to 45 s "
                     "depending on the artifact) and, since 1.35.0, the "
                     "shorter pause between the single hops of one series "
                     "(3 or 6 s). Higher = they sit still longer. Not "
                     "play-tested yet.")
        self._slider(f, "art_hop_dist", "Artifact hop distance (experimental)", 25, 300, 5, 100, fmt_pct,
                     "How far and high one hop carries the artifact (vanilla "
                     "15 m distance, 1 m height, force 15). Lower = it barely "
                     "gets away from you. Not play-tested yet.")
        self._slider(f, "art_hop_count", "Artifact hops per series (experimental)", 25, 300, 5, 100, fmt_pct,
                     "How many hops in a row before the artifact rests "
                     "(vanilla 3, 5, 7 or 9 depending on the artifact; the "
                     "two that never hop stay at zero). Whole numbers, never "
                     "below one. Not play-tested yet.")
        self._check(f, "art_no_detector", "Artifacts are visible without a detector (experimental)",
                    "147 of the 154 artifacts require a detector to be shown "
                    "at all; this clears that flag on those 147 and leaves "
                    "the seven that already don't need one alone. Whether "
                    "the game then draws them at any distance or still uses "
                    "the visibility radius is untested.")
        self._check(f, "art_caches", "Uncommon artifact caches actually drop (experimental)",
                    "One world loot group, 'ArtifactUncommon', has nine places "
                    "on the map but all 20 of its entries carry weight 0 - so "
                    "those caches come up empty. This gives each entry weight 1. "
                    "Whether the game rolls such a group at all is unproven. "
                    "Not play-tested yet.")
        self._slider(f, "detector", "Detector & scanner range", 50, 300, 10, 100, fmt_pct,
                     "Artifact detectors (Echo, Bear, Veles, Gilka), the "
                     "anomaly beeper and the searchpoint scanner.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Economy")
        f = self._section(body, "Economy & traders")
        self._slider(f, "buyprice", "Trader buy prices (what you get)", 0.25, 4, 0.1, 1, fmt_factor,
                     "Since 1.28.0 this also patches the nine traders that "
                     "carry their own buy coefficient on the NPC itself "
                     "(precedence between the two is unverified).")
        self._slider(f, "sellprice", "Trader sell prices (what you pay)", 0.25, 4, 0.1, 1, fmt_factor,
                     "Since 1.28.0 this also patches the nine traders that "
                     "carry their own sell coefficient on the NPC itself "
                     "(precedence between the two is unverified).")
        self._slider(f, "repair", "Repair cost", 0, 200, 5, 100, fmt_pct,
                     "0 % = free repairs.")
        self._check(f, "repair_no_rep", "Reputation doesn't affect repair prices",
                    "Vanilla charges by standing: enemies pay double, "
                    "disaffected 1.5x, neutral normal, friends 25 % less. "
                    "This puts every level on the neutral price. Not "
                    "play-tested yet.")
        self._slider(f, "infotopic", "NPC rumour refresh", 1, 72, 1, 24, fmt_hours,
                     "Game hours before stalkers have something new to say "
                     "(vanilla 24). Lower = fresh rumours and hints sooner. "
                     "Not play-tested yet.")
        self._slider(f, "upgrade", "Upgrade cost", 0, 200, 5, 100, fmt_pct)
        self._slider(f, "upg_repair", "Repair surcharge per upgrade",
                     0, 1, 0.05, 0.2, fmt_dec,
                     "Every part you have fitted makes repairs dearer. "
                     "Vanilla charges 0.2 per upgrade on top - which is "
                     "why a fully modded rifle costs a fortune to fix. 0 = "
                     "upgrades are free to maintain, your repair bill only "
                     "follows the weapon itself. Same value on all 1288 "
                     "upgrades in vanilla. Not play-tested yet.")
        self._slider(f, "questreward", "Quest money rewards", 0.25, 10, 0.1, 1, fmt_factor)
        self._slider(f, "rq_cooldown", "Repeatable quest cooldown", 0, 400, 5, 100, fmt_pct,
                     "Wait time until task givers offer new repeatable "
                     "jobs (vanilla 24 in-game hours). 0 % = new jobs "
                     "right away. A cooldown already ticking in your "
                     "save finishes at its old pace first.")
        self._slider(f, "rq_jobs", "Repeatable jobs per round", 1, 10, 1, 3,
                     fmt_int,
                     "How many jobs a task giver hands out before he runs "
                     "dry and the cooldown above has to pass (vanilla 3). "
                     "Each giver is capped at the number of different jobs "
                     "he actually has (6 to 10, depending on the giver) - "
                     "asking for more would only repeat them. Pair it with "
                     "the switch below, or the extra jobs only show up "
                     "after the cooldown. Not play-tested yet.")
        self._check(f, "rq_jobs_instant",
                    "Task giver's dialog opens while he still has jobs",
                    "Vanilla arms the job dialog only once the giver has "
                    "finished stocking up. This arms it while he is still "
                    "below the limit above. ⚠ Play-tested by Molkerr on "
                    "1.31.0 (GitHub #9): on its own this does NOT let you "
                    "take a second job in the same conversation - for that "
                    "use the switch below. Kept because it re-arms the "
                    "dialog earlier after a round resets.")
        self._check(f, "rq_jobs_multi",
                    "Accept several jobs in one conversation (experimental)",
                    "Accepting a job switches the giver's dialog off, so this "
                    "adds two nodes per giver: one clears that result, the "
                    "other re-opens the dialog a second later. You can then "
                    "keep taking jobs until the round limit above is reached. "
                    "It also flips one key on the giver's round-end node: "
                    "vanilla shuts down everything in his quest as soon as "
                    "any one job is handed in, which would take the jobs you "
                    "are still carrying with it. (634 of the game's 1395 end "
                    "nodes already ship with that key off, so it is a normal "
                    "value, not a hack.) Play-tested by Molkerr on 1.33.0 "
                    "(GitHub #9) - that is how the first two bugs here were "
                    "found. WARNING: the hand-in case is the riskiest thing "
                    "this tool does and is still untested; the author of "
                    "'Zone Borders / Contracts' (Nexus 2638) failed at the "
                    "same spot with a much bigger rewrite. We add no save "
                    "variables and clear nothing the game does not clear "
                    "itself, so removing the pak leaves no trace.")
        self._slider(f, "fasttravel", "Fast travel cost", 0, 400, 5, 100, fmt_pct,
                     "0 % = guides take you anywhere for free.")
        self._slider(f, "price_weapon", "Weapon prices", 0.25, 4, 0.1, 1, fmt_factor,
                     "Per-category price multipliers – these stack with the "
                     "trader buy/sell sliders above.")
        self._slider(f, "price_armor", "Armor prices", 0.25, 4, 0.1, 1, fmt_factor)
        self._slider(f, "price_ammo", "Ammo prices", 0.25, 4, 0.1, 1, fmt_factor)
        self._slider(f, "price_artifact", "Artifact prices", 0.25, 4, 0.1, 1, fmt_factor)
        self._slider(f, "price_consumable", "Consumable prices", 0.25, 4, 0.1, 1, fmt_factor)
        self._slider(f, "device_price", "Device prices (binoculars, night vision)", 0.25, 4, 0.1, 1, fmt_factor,
                     "The two remaining per-category price factors. Not "
                     "play-tested yet.")
        self._slider(f, "min_resale", "Minimum resale value", 0, 100, 5, 10, fmt_pct,
                     "Broken gear never sells for less than this share of its "
                     "price (vanilla 10 %). Not play-tested yet.")
        ctk.CTkLabel(f, text="", height=2).pack()

        body = self._tab("Traders")
        f = self._section(body, "Stock (what traders have on the shelf)")
        self._slider(f, "trader_stock", "Trader stock amount", 25, 400, 5, 100, fmt_pct,
                     "Scales the quantities on offer (ammo boxes, medkit "
                     "stacks ...). Weapons and armor are single items – "
                     "they only multiply from 150 % up, like loot.")
        self._slider(f, "trader_variety", "Trader stock variety", 25, 400, 5, 100, fmt_pct,
                     "Each catalog item has a chance to be in stock after a "
                     "restock. Higher = fuller shelves (chance is capped at "
                     "100 %), lower = patchier stock. What a trader CAN "
                     "carry stays their vanilla catalog – honest limit: "
                     "this tool does not add new items to traders.")
        self._slider(f, "restock", "Trader restock time", 25, 400, 5, 100, fmt_pct,
                     "How long traders take to refresh their stock "
                     "(vanilla: 8 h to 7 days depending on the trader; "
                     "day-based traders can't go below 1 day).")
        ctk.CTkLabel(f, text="", height=2).pack()

        f = self._section(body, "Wallet & buying")
        self._slider(f, "trader_money", "Trader money", 0.25, 10, 0.1, 1, fmt_factor,
                     "Scales the coupon wallet traders pay you from. "
                     "Honest note: most traders (59 of 73) already have "
                     "unlimited money in vanilla – this affects the "
                     "finite wallets (bartenders etc.). Since 1.28.0 it also "
                     "scales the coupon amounts carried on the NPC structs "
                     "themselves (22 of them, precedence unverified).")
        self._check(f, "trader_inf_money", "All traders have unlimited money",
                    "Switches the remaining finite wallets to unlimited "
                    "(most are already unlimited in vanilla).")
        self._slider(f, "trader_dur", "Traders buy gear from durability", 0, 100, 5, 40, fmt_pct,
                     "0 % = traders buy weapons/armor in any condition (vanilla: 40 %).")
        self._check(f, "traders_no_gear", "Traders don't buy weapons or armor (hardcore)",
                    "Adds Weapon and Armor to every trader's buy restrictions "
                    "(existing restrictions stay). Like 'TradersDontBuy"
                    "WeaponsArmor'. Not play-tested yet.")
        self._check(f, "traders_map", "Show traders, technicians, medics and guides on the map",
                    "80 NPCs already carry a map symbol in the game data - 34 "
                    "traders, 18 technicians, 14 guides, 14 medics - but their "
                    "display flag is off; only eight are shown in vanilla. "
                    "This turns the flag on for exactly those 80. Nobody new "
                    "is added, and NPCs without a symbol are untouched. Not "
                    "play-tested yet.")
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
            font=ctk.CTkFont(size=15, weight="bold"), command=self._generate_output)
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
                                        fg_color=BAD_RED, hover_color=BAD_RED_HOVER,
                                        border_width=SYS_BORDER,
                                        border_color=BAD_BORDER,
                                        command=self._remove_mod)
        self.btn_remove.pack(side="left", padx=4)

        # Statuszeile links, rechts daneben das Zeichen des aktiven Designs
        # (Besitzer 06.09.: "unter remove from mods ist Platz fuer jeweils
        # ein Logo"). Bewusst KEIN Fraktionslogo aus dem Spiel — das ist
        # GSC-Grafik; hier steht das Tab-Symbol plus der Name des Designs.
        status_row = ctk.CTkFrame(foot, fg_color="transparent")
        status_row.pack(fill="x", padx=12, pady=(0, 2))
        self.theme_mark = ctk.CTkLabel(
            status_row, text="", anchor="e", width=150,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        self.theme_mark.pack(side="right")
        self.status = ctk.CTkLabel(status_row, text="Starting ...", anchor="w",
                                   text_color="gray70")
        self.status.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            foot,
            text="ℹ Only values you change are written to the pak. Sliders at "
                 "(vanilla) are left untouched, so other mods keep working.",
            anchor="w", font=ctk.CTkFont(size=12), text_color="gray55",
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
        for rows in self._isc_rows.values():
            for row in rows.values():
                row.set_state(state)
        for btn in self._isc_btns:     # Klassen-Knoepfe des Fernrohr-Baums: beim ersten
            btn.configure(state=state)  # Laden entstehen sie noch im Sperrzustand
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
                    self._isc_populate()
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
            encounter_wounded_factor=s["enc_wounded"].get() / 100.0,
            encounter_dead_factor=s["enc_dead"].get() / 100.0,
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
            mutant_attack_series_factor=s["mut_series"].get(),
            mutant_attack_bleed_factor=s["mut_bleed"].get(),
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
            climb_speed_factor=s["climb"].get() / 100.0,
            starting_money=int(s["start_money"].get()),
            artifact_slots_bonus=int(s["art_slots"].get()),
            shooting_shake_factor=s["shoot_shake"].get() / 100.0,
            ads_zoom_factor=s["ads_zoom"].get() / 100.0,
            no_aim_assist_mouse=bool(self.checks["no_aim_mouse"].get()),
            no_aim_assist_gamepad=bool(self.checks["no_aim_gamepad"].get()),
            dialog_fov=float(s["dialog_fov"].get()),
            cutscene_fov=float(s["cutscene_fov"].get()),
            default_fov=float(s["default_fov"].get()),
            hud_compass=int(s["hud_compass"].get()),
            hud_crosshair=int(s["hud_crosshair"].get()),
            hud_body_markers=int(s["hud_bodies"].get()),
            hud_stash_markers=int(s["hud_stashes"].get()),
            corpse_time_factor=s["corpse_time"].get() / 100.0,
            corpse_max_count=int(s["corpse_max"].get()),
            weather_duration_factor=s["weather_dur"].get() / 100.0,
            bullet_drop_factor=s["bullet_drop"].get() / 100.0,
            bullet_speed_factor=s["bullet_speed"].get() / 100.0,
            pistol_slot_level=int(s["pistol_slot"].get()),
            mutant_protection_factor=s["mprot"].get(),
            sleep_anytime=bool(self.checks["sleep_anytime"].get()),
            min_sleep_hours=int(s["sleep_min"].get()),
            sleep_in_emission=bool(self.checks["sleep_emission"].get()),
            # 1.26.0
            no_knockdown=bool(self.checks["no_knockdown"].get()),
            no_water_slowdown=bool(self.checks["no_water_slow"].get()),
            ladder_free_look=bool(self.checks["ladder_look"].get()),
            look_straight_down=bool(self.checks["look_down"].get()),
            handless_zoom_factor=s["hands_zoom"].get() / 100.0,
            crouch_vignette_factor=s["crouch_vignette"].get() / 100.0,
            look_speed_h_factor=s["look_h"].get() / 100.0,
            look_speed_v_factor=s["look_v"].get() / 100.0,
            camera_slowdown_factor=s["cam_slowdown"].get() / 100.0,
            butt_wear_factor=s["butt_wear"].get() / 100.0,
            mutants_trigger_anomalies=bool(self.checks["mut_anomalies"].get()),
            guards_no_instakill=bool(self.checks["guards_normal"].get()),
            explosion_radius_factor=s["expl_radius"].get() / 100.0,
            explosion_npc_damage_factor=s["expl_npc"].get(),
            phantom_dog_damage_factor=s["phantom_dog"].get() / 100.0,
            psy_phantoms_only=bool(self.checks["psy_phantoms"].get()),
            reload_speed_factor=s["reload"].get() / 100.0,
            equip_speed_factor=s["equip_speed"].get() / 100.0,
            shooting_anim_skip=int(s["anim_skip"].get()),
            jam_chance_factor=s["jam_chance"].get() / 100.0,
            recoil_recovery_factor=s["recoil_recovery"].get() / 100.0,
            spread_bloom_factor=s["spread_bloom"].get() / 100.0,
            aim_steady_factor=s["aim_steady"].get() / 100.0,
            zombie_spread_factor=s["zombie_spread"].get() / 100.0,
            explosion_armor_damage_factor=s["exp_armor_dmg"].get() / 100.0,
            explosion_armor_pierce_factor=s["exp_armor_pierce"].get() / 100.0,
            explosion_destructible_factor=s["exp_destructible"].get() / 100.0,
            bullet_penetration_factor=s["bullet_pen"].get() / 100.0,
            bullet_penetration_depth_factor=s["bullet_pen_depth"].get() / 100.0,
            bullet_range_factor=s["bullet_range"].get() / 100.0,
            hip_steady_factor=s["hip_steady"].get() / 100.0,
            move_steady_factor=s["move_steady"].get() / 100.0,
            recoil_pattern_factor=s["recoil_pattern"].get() / 100.0,
            chamber_round=bool(self.checks["chamber_round"].get()),
            dropped_ammo_factor=s["dropped_ammo"].get() / 100.0,
            weapon_noise_factor=s["weapon_noise"].get() / 100.0,
            item_grid_factor=s["item_grid"].get() / 100.0,
            inventory_action_factor=s["inv_action"].get() / 100.0,
            npc_anomaly_ignore_factor=s["npc_anomaly"].get() / 100.0,
            ragdoll_force_factor=s["ragdoll"].get() / 100.0,
            npc_retreat_radius_factor=s["npc_retreat_dist"].get() / 100.0,
            npc_retreat_damage_factor=s["npc_retreat_dmg"].get() / 100.0,
            npc_vs_npc_damage_factor=s["npc_vs_npc"].get() / 100.0,
            npc_vs_player_damage_factor=s["npc_vs_player"].get() / 100.0,
            npc_vs_friendly_damage_factor=s["npc_vs_friendly"].get() / 100.0,
            stat_bars_follow=bool(self.checks["stat_bars"].get()),
            jam_clear_factor=s["jam_clear"].get() / 100.0,
            mutant_loot_chance_factor=s["mut_loot"].get() / 100.0,
            stash_clue_factor=s["stash_clue"].get() / 100.0,
            npcs_no_corpse_loot=bool(self.checks["npc_no_loot"].get()),
            alife_vision_factor=s["alife_vision"].get() / 100.0,
            map_reveal_factor=s["map_reveal"].get() / 100.0,
            map_all_regions=bool(self.checks["map_regions"].get()),
            fast_travel_lock=int(s["ft_lock"].get()),
            guide_delay_factor=s["guide_delay"].get() / 100.0,
            instant_teleports=bool(self.checks["teleports_instant"].get()),
            protection_cap_factor=s["prot_cap"].get() / 100.0,
            weird_artifact_factor=s["weird_art"].get() / 100.0,
            skip_intro=bool(self.checks["skip_intro"].get()),
            traders_no_gear_buy=bool(self.checks["traders_no_gear"].get()),
            traders_on_map=bool(self.checks["traders_map"].get()),
            no_mouse_smoothing=bool(self.checks["no_mouse_smooth"].get()),
            no_view_acceleration=bool(self.checks["no_view_accel"].get()),
            clicker_factor=s["clicker"].get() / 100.0,
            # 1.27.0
            back_speed_factor=s["back_speed"].get() / 100.0,
            air_control_factor=s["air_control"].get() / 100.0,
            limp_speed_factor=s["limp"].get() / 100.0,
            slow_run_threshold_pct=float(s["jog_threshold"].get()),
            hp_regen_delay=float(s["regen_delay"].get()),
            radiation_decay_factor=s["rad_decay"].get() / 100.0,
            bleeding_stop_factor=s["bleed_stop"].get() / 100.0,
            psy_recovery_factor=s["psy_recover"].get() / 100.0,
            sober_up_factor=s["sober"].get() / 100.0,
            stealth_kill_range_factor=s["stealth_kill"].get() / 100.0,
            wheel_time_pct=float(s["wheel_time"].get()),
            sleep_fade_factor=s["sleep_fade"].get() / 100.0,
            corpse_drag_factor=s["corpse_drag"].get() / 100.0,
            item_despawn_factor=s["item_despawn"].get() / 100.0,
            day_start_hour=int(s["day_start"].get()),
            evening_start_hour=int(s["evening_start"].get()),
            calm_damage_factor=s["calm_dmg"].get() / 100.0,
            last_bullet_multiplier=float(s["last_bullet"].get()),
            armor_difference_factor=s["armor_diff"].get() / 100.0,
            armor_deflect_chance_pct=float(s["deflect_chance"].get()),
            armor_deflect_damage_factor=s["deflect_dmg"].get() / 100.0,
            scope_zoom_factor=s["scope_zoom"].get() / 100.0,
            scope_penalty_factor=s["scope_penalty"].get() / 100.0,
            upg_accuracy_factor=s["upg_accuracy"].get() / 100.0,
            upg_handling_factor=s["upg_handling"].get() / 100.0,
            upg_durability_factor=s["upg_durability"].get() / 100.0,
            upg_range_factor=s["upg_range"].get() / 100.0,
            upg_damage_factor=s["upg_damage"].get() / 100.0,
            upg_weight_factor=s["upg_weight"].get() / 100.0,
            upg_breath_factor=s["upg_breath"].get() / 100.0,
            upg_armor_protection_factor=s["upg_armor_prot"].get() / 100.0,
            upg_armor_misc_factor=s["upg_armor_misc"].get() / 100.0,
            weapon_warning_count=int(s["warn_count"].get()),
            weapon_warning_delay_factor=s["warn_delay"].get() / 100.0,
            camper_time_factor=s["camper_time"].get() / 100.0,
            sync_melee_factor=s["sync_melee"].get() / 100.0,
            sync_ability_factor=s["sync_ability"].get() / 100.0,
            sync_grenade_factor=s["sync_grenade"].get() / 100.0,
            sync_suppress_factor=s["sync_suppress"].get() / 100.0,
            npcs_no_weapon_pickup=bool(self.checks["npc_no_pickup"].get()),
            darkness_factor=s["darkness"].get() / 100.0,
            corpse_threat_factor=s["corpse_threat"].get() / 100.0,
            damage_mercy_factor=s["dmg_mercy"].get() / 100.0,
            psy_phantom_factor=s["psy_phantoms_n"].get() / 100.0,
            min_resale_pct=float(s["min_resale"].get()),
            container_respawn_hours=float(s["container_respawn"].get()),
            energy_tolerance_factor=s["energy_tol"].get() / 100.0,
            npc_hip_accuracy_factor=s["npc_hip"].get(),
            device_price_factor=s["device_price"].get(),
            # 1.28.0 P1
            limp_threshold_factor=s["limp_threshold"].get(),
            no_landing_limp=bool(self.checks["no_limp"].get()),
            bleeding_hit_factor=s["bleed_hit"].get() / 100.0,
            bleeding_nonpen_factor=s["bleed_nonpen"].get() / 100.0,
            damage_screen_factor=s["damage_screen"].get() / 100.0,
            flashlight_dialog_bright=bool(self.checks["flashlight_dialog"].get()),
            quicksave_overwrite_min=float(s["quicksave_min"].get()),
            # 1.28.0 P2
            grenade_resist_factor=s["grenade_resist"].get() / 100.0,
            armor_wear_coef=float(s["armor_wear"].get()),
            anomaly_armor_difference_factor=s["anomaly_armor_diff"].get() / 100.0,
            # 1.28.0 P3
            wounded_heal_chance=int(s["wounded_chance"].get()),
            wounded_cooldown_s=int(s["wounded_cd"].get()),
            wounded_regen_factor=s["wounded_regen"].get() / 100.0,
            wounded_heal_threshold=int(s["wounded_threshold"].get()),
            npc_player_focus_factor=s["npc_focus"].get() / 100.0,
            npc_retarget_cooldown_factor=s["npc_retarget"].get() / 100.0,
            npc_damage_memory_factor=s["npc_dmg_memory"].get() / 100.0,
            cover_distance_factor=s["cover_distance"].get() / 100.0,
            cover_path_factor=s["cover_path"].get() / 100.0,
            # 1.28.0 P4
            mutant_smell_factor=s["mut_smell"].get() / 100.0,
            mutants_no_smell=bool(self.checks["mut_no_smell"].get()),
            burer_fire_interval_factor=s["burer_fire"].get() / 100.0,
            mutant_loot_widget=bool(self.checks["mut_loot_widget"].get()),
            # 1.28.0 P5
            squad_expansion_factor=s["squad_expansion"].get() / 100.0,
            refill_cooldown_factor=s["refill_cd"].get() / 100.0,
            refill_distance_factor=s["refill_dist"].get() / 100.0,
            corpse_budget=int(s["corpse_budget"].get()),
            faction_battle_chance=int(s["faction_battle"].get()),
            faction_expansion_pace_factor=s["faction_pace"].get() / 100.0,
            corpse_distance_factor=s["corpse_distance"].get() / 100.0,
            alife_corpse_hardcap=int(s["corpse_hardcap"].get()),
            # 1.28.0 P6
            radiation_dose_factor=s["rad_dose"].get() / 100.0,
            radiation_filter_factor=s["rad_filter"].get() / 100.0,
            geiger_volume_factor=s["geiger"].get() / 100.0,
            barbed_wire_factor=s["barbed_wire"].get() / 100.0,
            explosive_container_factor=s["exp_containers"].get() / 100.0,
            push_force_factor=s["push_force"].get() / 100.0,
            weather_transition_factor=s["weather_transition"].get() / 100.0,
            moon_brightness_factor=s["moon"].get() / 100.0,
            sun_brightness_factor=s["sun"].get() / 100.0,
            stars_brightness_factor=s["stars"].get() / 100.0,
            cloud_opacity_factor=s["cloud_opacity"].get() / 100.0,
            cloud_speed_factor=s["cloud_speed"].get() / 100.0,
            dusk_length_factor=s["dusk_length"].get() / 100.0,
            music_combat_threshold=float(s["music_threshold"].get()),
            music_combat_lifetime=float(s["music_lifetime"].get()),
            camp_life_factor=s["camp_life"].get() / 100.0,
            # 1.28.0 P7
            artifact_radius_factor=s["art_radius"].get(),
            artifacts_no_hop=bool(self.checks["art_no_hop"].get()),
            artifact_keepaway_factor=s["art_keepaway"].get() / 100.0,
            artifact_hop_pause_factor=s["art_hop_pause"].get() / 100.0,
            artifact_hop_distance_factor=s["art_hop_dist"].get() / 100.0,
            artifact_hop_count_factor=s["art_hop_count"].get() / 100.0,
            artifacts_no_detector=bool(self.checks["art_no_detector"].get()),
            artifact_caches_drop=bool(self.checks["art_caches"].get()),
            loot_reroll_radius_factor=s["loot_reroll"].get() / 100.0,
            loot_reroll_timer_factor=s["loot_reroll_time"].get() / 100.0,
            # 1.28.0 P8
            repair_cost_reputation=bool(self.checks["repair_no_rep"].get()),
            infotopic_refresh_hours=int(s["infotopic"].get()),
            scope_overrides={sid: dict(v) for sid, v in self.scope_overrides.items()},
            ammo_damage_factor=s["ammo_dmg"].get() / 100.0,
            ammo_piercing_factor=s["ammo_ap"].get() / 100.0,
            ammo_armor_damage_factor=s["ammo_ad"].get() / 100.0,
            ammo_cover_factor=s["ammo_cover"].get() / 100.0,
            ammo_stack_factor=s["ammo_stack"].get(),
            ammo_pack_factor=s["ammo_pack"].get() / 100.0,
            ammo_bleeding_factor=s["ammo_bleed"].get() / 100.0,
            ammo_recoil_factor=s["ammo_recoil"].get() / 100.0,
            ammo_flatness_factor=s["ammo_flat"].get() / 100.0,
            ammo_wear_factor=s["ammo_wear"].get() / 100.0,
            # 1.33.0 (neunte Datenrecherche)
            ammo_dispersion_factor=s["ammo_disp"].get() / 100.0,
            ammo_aim_dispersion_factor=s["ammo_aimdisp"].get() / 100.0,
            anomaly_wear_factor=s["anom_wear"].get() / 100.0,
            gear_durability_factor=s["gear_dur"].get() / 100.0,
            far_damage_factor=s["far_damage"].get() / 100.0,
            effect_cap_other_factor=s["cap_other"].get() / 100.0,
            lair_initial_fill_factor=s["lair_initial"].get() / 100.0,
            lair_rare_archetype_factor=s["lair_rare"].get() / 100.0,
            lair_expansion_player_factor=s["lair_expand"].get() / 100.0,
            fallback_spawn_count=int(s["fallback_spawn"].get()),
            consumable_stack_factor=s["cons_stack"].get(),
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
            stash_sets_factor=s["stash_sets"].get() / 100.0,
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
            upgrade_repair_surcharge=s["upg_repair"].get(),
            quest_reward_factor=s["questreward"].get(),
            repeatable_quest_factor=s["rq_cooldown"].get() / 100.0,
            repeatable_jobs_per_round=int(s["rq_jobs"].get()),
            repeatable_jobs_instant=bool(self.checks["rq_jobs_instant"].get()),
            repeatable_jobs_multi=bool(self.checks["rq_jobs_multi"].get()),
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
    # ------------------------------------------------------- Farbdesigns
    def _set_theme(self, name: str) -> None:
        """Design umschalten — sofort sichtbar, ohne Neustart.

        `ACCENT` ist ein Modul-Global und wird von Suchtreffern, Warnboxen
        und Override-Markern beim AUFRUF gelesen; darum reicht es, ihn hier
        neu zu binden, damit alles Kuenftige die neue Farbe nimmt. Alles
        Vorhandene faerbt theme.apply() um."""
        global ACCENT, PANEL, PANEL2, PANEL2_HOVER, MUTED
        if name not in theme.THEMES:
            name = theme.DEFAULT_NAME
        previous = self.theme_name
        self.theme_name = name
        pal = theme.get(name)
        theme.apply(self, name, previous)
        self.tabs.restyle(pal)          # nach dem allgemeinen Umfaerben
        theme.apply_button_text(self)   # und danach die Knopfschrift
        ACCENT = pal["accent"]
        PANEL, PANEL2 = pal["panel"], pal["panel2"]
        PANEL2_HOVER, MUTED = pal["panel2_hover"], pal["secondary"]
        # Zeichen des Designs in der Fusszeile
        mark = getattr(self, "theme_mark", None)
        if mark is not None:
            glyph = THEME_MARKS.get(name, "◐")
            mark.configure(text=f"{glyph}  {name.upper()}", text_color=ACCENT)
        # Der Design-Knopf traegt den neuen Akzent (Default: neutral grau)
        if name == theme.DEFAULT_NAME:
            self.btn_theme.configure(fg_color=PANEL2, hover_color=PANEL2_HOVER,
                                     text_color=self.btn_faq.cget("text_color"))
        else:
            self.btn_theme.configure(fg_color=ACCENT,
                                     hover_color=pal["bright"],
                                     text_color="gray10")
        # "Changed only" ist im aktiven Zustand bernsteinfarben — mitziehen
        if self.changed_only:
            self.btn_changed.configure(fg_color=ACCENT, text_color="gray10")
        for row in self.sliders.values():
            if row.conflict_mods:
                row._update_dot()

    def _show_theme_window(self):
        """Kleines Fenster mit den Paletten. Klick faerbt sofort um, damit
        man sieht, was man waehlt, statt einen Namen zu raten."""
        existing = getattr(self, "_theme_win", None)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_set()
            return
        win = ctk.CTkToplevel(self)
        self._theme_win = win
        win.title("S2Tweaker — colour themes")
        win.geometry("460x520")
        win.minsize(420, 360)
        win.transient(self)
        ctk.CTkLabel(
            win, text="Colour themes", anchor="w",
            font=ctk.CTkFont(size=17, weight="bold")).pack(
                fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(
            win, anchor="w", justify="left", wraplength=410,
            font=ctk.CTkFont(size=12), text_color=MUTED,
            text="Cosmetic only — nothing about the mod you build changes. "
                 "The colours are my own take on how the factions look "
                 "in-game; the game files carry no faction palette. Green "
                 "and red stay green and red: they mean ready, missing and "
                 "off.").pack(fill="x", padx=16, pady=(2, 8))
        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        marks: dict[str, ctk.CTkLabel] = {}

        def choose(name: str):
            self._set_theme(name)
            for key, mark in marks.items():
                mark.configure(text="✓" if key == name else "")

        for name in theme.names():
            pal = theme.get(name)
            row = ctk.CTkFrame(body, fg_color=PANEL,
                               corner_radius=8)
            row.pack(fill="x", padx=4, pady=3)
            swatch = ctk.CTkFrame(row, width=34, height=34, corner_radius=6,
                                  fg_color=pal["accent"])
            swatch.pack(side="left", padx=(10, 4), pady=8)
            swatch.pack_propagate(False)
            bar = ctk.CTkFrame(row, width=12, height=34, corner_radius=4,
                               fg_color=pal["button"])
            bar.pack(side="left", padx=(0, 10), pady=8)
            bar.pack_propagate(False)
            text = ctk.CTkFrame(row, fg_color="transparent")
            text.pack(side="left", fill="both", expand=True, pady=6)
            ctk.CTkLabel(text, text=name, anchor="w",
                         font=ctk.CTkFont(size=14, weight="bold")).pack(
                             fill="x")
            ctk.CTkLabel(text, text=pal.get("note", ""), anchor="w",
                         justify="left", wraplength=250,
                         font=ctk.CTkFont(size=12),
                         text_color=MUTED).pack(fill="x")
            mark = ctk.CTkLabel(row, width=26,
                                text="✓" if name == self.theme_name else "",
                                font=ctk.CTkFont(size=16, weight="bold"))
            mark.pack(side="left", padx=(0, 6))
            marks[name] = mark
            ctk.CTkButton(row, text="Use", width=62,
                          command=lambda n=name: choose(n)).pack(
                              side="left", padx=(0, 10))
        ctk.CTkButton(win, text="Close", width=100,
                      command=win.destroy).pack(pady=(0, 12))

    def _toggle_wheel(self):
        """Mausrad am Regler ein- und ausschalten.

        AUS (rot, Startzustand) = das Rad blaettert nur die Seite, kein
        Regler bewegt sich beim Scrollen. AN (gruen) = beides, wie in
        customtkinter vorgesehen. Bewusst NICHT gespeichert: der Schalter
        steht bei jedem Start wieder auf aus (Besitzer: "beim ersten start
        automatisch keine slider verschieben und rot")."""
        SliderRow.set_wheel_enabled(not SliderRow._wheel_enabled)
        on = SliderRow._wheel_enabled
        self.btn_scroll.configure(
            text="● Wheel moves sliders" if on else "● Wheel scrolls only",
            fg_color=OK_GREEN if on else BAD_RED,
            hover_color=OK_GREEN_HOVER if on else BAD_RED_HOVER,
            border_color=OK_BORDER if on else BAD_BORDER)

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
                             text_color=MUTED)
        count.pack(side="left", padx=(8, 0))

        body = ctk.CTkScrollableFrame(win)
        body.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        font_q = ctk.CTkFont(size=14)
        font_a = ctk.CTkFont(size=13)
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
                      hover_color=PANEL2_HOVER,
                      command=lambda: answer("later")).pack(side="left", padx=6)
        ctk.CTkButton(row, text="Don't ask again", width=120, fg_color="gray35",
                      hover_color=PANEL2_HOVER,
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
        bold = ctk.CTkFont(size=14, weight="bold")

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
                     "this tool's settings.", text_color=MUTED)
            if info.note:
                line(info.note, text_color=MUTED)
        if broken:
            line("These mods contain data I can't read:", font=bold)
            for info in broken:
                line(f"{info.name} \u2014 {info.note}", text_color=MUTED)
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
                 text_color=MUTED)
        line("Affected settings are marked with a dot: blue = a mod changes "
             "it while you are at (vanilla), violet = you changed it too. "
             "Your pak usually wins shared values because its zzz_ name "
             "loads last. The dots stay until you scan again.",
             text_color=MUTED)

        foot = ctk.CTkFrame(win, fg_color="transparent")
        foot.pack(fill="x", padx=12, pady=(0, 10))
        avoid_box = ctk.CTkCheckBox(
            foot, text="Avoid conflicts – reset & lock every setting "
                       "these mods change")
        if self.avoid_conflicts:
            avoid_box.select()
        avoid_hint = ctk.CTkLabel(
            foot, text="", anchor="w", justify="left", wraplength=580,
            font=ctk.CTkFont(size=12), text_color=MUTED)

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
        self._isc_clear_all()
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
            "scope_overrides": self.scope_overrides,
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
                "theme": self.theme_name,
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
            self._isc_populate()
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
        # Design VOR "changed only" setzen: der Toggle faerbt seinen Knopf
        # mit dem dann gueltigen Akzent.
        if data.get("theme"):
            self._set_theme(theme.resolve(data["theme"]))
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
                         if p in ("hp", "speed", "damage", "regen", "protection")
                         and abs(float(v) - 1.0) > 1e-9}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.mutant_overrides[species] = clean
        for sid, params in (data.get("scope_overrides") or {}).items():
            try:
                clean = {p: float(v) for p, v in params.items()
                         if p in ("zoom", "penalty") and abs(float(v) - 1.0) > 1e-9
                         and (p != "zoom" or float(v) > 0)}
            except (TypeError, ValueError, AttributeError):
                continue
            if clean:
                self.scope_overrides[sid] = clean
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
        # 1.35.0: die zwei Maus-Schalter schreiben KEINE GameData-Datei,
        # sondern Stalker2/Config/UserInput.ini an die Pak-Wurzel. Sie
        # muessen darum an der Leer-Pruefung unten vorbei.
        ini = input_ini(s)
        # summarize() kennt nur die Settings, build_patches() auch die
        # Vanilla-Werte: ein Faktor auf einen Vanilla-0-Wert (viele
        # ArmorPiercingMod/CoverPiercingMod) oder ein Item-Gewicht ohne
        # angehakte Kategorie steht in "active", erzeugt aber keine Zeile.
        # Ohne diesen Riegel bekaeme der Packer einen leeren Ordner und der
        # Benutzer einen rohen Python-Traceback statt einer Erklaerung.
        if not patches and ini is None:
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
        root_files = {MANIFEST_NAME: self._build_manifest(s, active)}
        if ini is not None:
            root_files["Stalker2/Config/UserInput.ini"] = ini
        pakio.pack_mod(patches, out_pak, root_files=root_files)

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
            self._isc_populate()
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
