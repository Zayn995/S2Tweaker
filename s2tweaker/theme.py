"""Farbdesigns in den Farben der Spiel-Fraktionen (Besitzer 06.09.2026).

Zwei Ebenen — das ist der Kern der Sache:

* **Fraktion** bestimmt das Erscheinungsbild: Hintergrund, Karten, Akzent,
  Knoepfe, Regler, Textfarben.
* **System** bleibt in JEDEM Design gleich: Gruen = bereit/erfolgreich,
  Rot = zerstoerend, Bernstein = Warnung. Sonst waere im Duty-Design ein
  roter "Remove from ~mods" nicht mehr von einem roten Bestaetigen-Knopf zu
  unterscheiden — genau davor warnt der Vorschlag des Besitzers selbst.

Sieben Farben je Fraktion:
    base      Fensterhintergrund
    panel     Karten (Kopfzeile, Fusszeile, Abschnitte, Warnboxen)
    panel2    Zweite Ebene (inaktive Tabs, Eingabefelder, Nebenknoepfe)
    accent    aktiver Tab, Reglerbalken, Knoepfe, Suchtreffer, Override-Marker
    bright    Reglergriff, Hover — die hellere Stufe des Akzents
    secondary gedaempfter Text (Erklaerzeilen)
    text      normale Schrift

⚠ EHRLICHE HERKUNFT: diese Paletten stehen NICHT in den Spieldaten. Unter
GameData gibt es nur `DT_QuestColorPresets.json` (Quest-Farben, zwei
Presets); Fraktionsfarben stecken in UI-Assets, an die ein cfg-Werkzeug nicht
herankommt. Die Werte stammen aus dem Vorschlag des Besitzers und sind an den
Erkennungsmerkmalen der Fraktionen im Spiel orientiert — entworfen, nicht
ausgelesen. Das gehoert genauso in die Nexus-Beschreibung.

Technik: customtkinter liest Farben, wenn ein Widget ENTSTEHT. Ein Wechsel
zur Laufzeit braucht darum beides — die Vorgaben im ThemeManager fuer alles,
was noch kommt (die Baeume werden erst beim Aufklappen gebaut), und ein
Umfaerben der vorhandenen Widgets. Umgefaerbt wird ROLLENBASIERT: je
(Widget-Klasse, Farbfeld) gibt es eine kurze Liste moeglicher Rollen, und
getroffen wird nur, was exakt die alte Farbe DIESER Rolle traegt. Eine
schlichte Tabelle "alte Farbe -> neue Farbe" reichte nicht: benutzt ein
Design denselben Ton fuer zwei Rollen, laesst sich beim Zurueckschalten nicht
mehr sagen, welcher Standardwert gemeint war.
"""
from __future__ import annotations

import customtkinter as ctk

# --- Systemfarben: in JEDEM Design gleich --------------------------------
SUCCESS = "#2d6a3f"        # bereit, bestaetigen
SUCCESS_HOVER = "#377f4c"
DANGER = "#7a2d2d"         # zerstoerend, fehlt
DANGER_HOVER = "#8f3838"
WARNING = "#d9a648"        # Warnboxen, Hinweise
# Heller Rand um die Systemknoepfe. Ohne ihn verschwimmt "Remove from ~mods"
# im Duty-Design mit den roten Themenknoepfen — genau die Verwechslung, vor
# der der Entwurf warnt. Der Rand macht sie in JEDEM Design als Systemknopf
# kenntlich, unabhaengig von der Fraktionsfarbe.
# Orange = "hier fehlt noch ein Klick". Der Bestaetigen-Knopf traegt es
# pulsierend, solange die Spieldaten nicht geladen sind, und wird danach
# gruen (Besitzer 06.09.: "Orange pulsierend solange nicht gedrueckt danach
# so wie jetzt gruen").
ATTENTION = "#A9701F"
ATTENTION_HOVER = "#C4832A"
ATTENTION_BORDER = "#E5AC4E"
SUCCESS_BORDER = "#4FA96B"
DANGER_BORDER = "#C0453F"
SYSTEM_BORDER_WIDTH = 2

# Achtung, zwei verschiedene Dinge: "button" ist die Flaechenfarbe der
# Knoepfe, "accent" die Hervorhebungsfarbe (Suchtreffer, Override-Marker).
# Faction text accents are brighter than their button fills; Standard keeps
# blue buttons and amber highlights. Genau deshalb braucht es
# zwei Rollen; mit einer kam nach dem Zurueckschalten Blau als Suchfarbe an.
ROLES = ("base", "panel", "panel2", "panel2_hover", "button", "button_hover",
         "progress", "bright", "bright_hover", "accent", "button_text",
         "secondary", "text")


def _shade(color: str, factor: float) -> str:
    """Denselben Ton heller (factor > 1) oder dunkler (< 1) machen."""
    color = color.lstrip("#")
    rgb = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(
        max(0, min(255, int(round(c * factor)))) for c in rgb)


def _solid(value):
    """Use the dark-mode component of a CTk colour pair."""
    if isinstance(value, (list, tuple)):
        return value[-1] if value else None
    return value


def _rgb(color):
    color = _solid(color)
    if color.startswith("gray"):
        return (round(255 * float(color[4:]) / 100),) * 3
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def contrast(foreground, background):
    """Relative luminance contrast, including Tk's grayNN notation."""
    def luminance(color):
        channels = [c / 255 for c in _rgb(color)]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
                  for c in channels]
        return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b + .05) / (a + .05)


def _mix(color, target, amount):
    return "#%02X%02X%02X" % tuple(round(a + (b - a) * amount)
                                   for a, b in zip(_rgb(color), _rgb(target)))


def _readable(color, hover=None):
    """Choose text that remains readable on both normal and hover fills."""
    backgrounds = (color, hover or color)
    return max(("#101010", "#F5F7FA"),
               key=lambda text: min(contrast(text, bg) for bg in backgrounds))


def _lift_text(color, background):
    for step in range(101):
        result = _mix(color, "#F5F7FA", step / 100)
        if contrast(result, background) >= 4.5:
            return result
    return result


def _pal(base, panel, panel2, accent, bright, secondary, text, note):
    """Faction surfaces with brighter text accents and readable hover states."""
    button = accent
    if contrast(_readable(button), button) < 4.5:
        button = _shade(button, .9)
    button_text = _readable(button)
    # Keep the hover recognisable without crossing into an unreadable fill.
    hover = button
    for step in range(35, -1, -1):
        candidate = _mix(button, bright, step / 100)
        if contrast(button_text, candidate) >= 4.5:
            hover = candidate
            break
    return {
        "base": base, "panel": panel,
        "panel2": panel2, "panel2_hover": _shade(panel2, 1.35),
        "button": button, "button_hover": hover, "progress": accent,
        "button_text": button_text,
        "bright": bright, "bright_hover": _shade(bright, 1.15),
        "accent": _lift_text(bright, panel2),
        "secondary": _lift_text(secondary, panel2), "text": text, "note": note,
    }


# Der Standard: das eigene Blau des Werkzeugs auf schwarzem Grund. Die
# Akzentwerte fuellt snapshot() aus dem customtkinter-Thema nach.
DEFAULT_NAME = "Standard"
DEFAULT_ACCENT = "#d9a648"

THEMES: dict[str, dict] = {
    DEFAULT_NAME: {
        "base": "#000000", "panel": "#141414",
        "panel2": "#1E1E1E", "panel2_hover": "#2A2A2A",
        "secondary": "gray60",
        "note": "the tool's own blue on black",
    },
    "Loners": _pal("#171512", "#211F1A", "#29261F", "#9A7745", "#BD9657",
                   "#75664F", "#D0CBC0",
                   "earthy browns and brass — the Zone's oldest jacket"),
    "Bandits": _pal("#151311", "#211D18", "#29231C", "#875D36", "#AE7540",
                    "#66564A", "#C9C2B7",
                    "black, brown and dirty orange"),
    "Duty": _pal("#111211", "#1B1D1A", "#242622", "#9B3030", "#C23A35",
                 "#85857B", "#D5D2C8",
                 "military red on near-black — strict and authoritarian"),
    "Freedom": _pal("#111611", "#1B211B", "#242B23", "#557A3E", "#759D50",
                    "#7C8A6B", "#D3D5C8",
                    "deep jungle green — the anarchists of the Zone"),
    "Military": _pal("#111511", "#1B211B", "#242A23", "#526B43", "#718B58",
                     "#6A7063", "#D0D2C8",
                     "muted olive and field grey"),
    "Ward": _pal("#151713", "#20221C", "#292B23", "#71805A", "#9A9B68",
                 "#6F7765", "#D0D0C0",
                 "khaki, military green and grey"),
    "Spark": _pal("#101718", "#192123", "#222C2D", "#168A86", "#27B6A7",
                  "#3E755D", "#D2D9D5",
                  "teal and cyan — technological, experimental"),
    "Monolith": _pal("#0D0E0D", "#171817", "#202120", "#A8B59A", "#D4D7CF",
                     "#686D68", "#E0E1DA",
                     "black, grey and a cold, almost white green"),
    "Ecologists": _pal("#151715", "#20221F", "#292B26", "#C1B54D", "#D8CA62",
                       "#81945B", "#D9D9CE",
                       "off-white, marker yellow and lab green"),
    "Mercenaries": _pal("#0E1013", "#181B20", "#20242A", "#455D78", "#607C9A",
                        "#55585D", "#D0D1D2",
                        "anthracite and cold navy — professional, anonymous"),
    "Clear Sky": _pal("#101619", "#192125", "#222C31", "#4C91A5", "#71B4C5",
                      "#687B82", "#D5D9D8",
                      "light blue and white — calm and clear"),
}

_FACTORY: dict = {}


def snapshot() -> None:
    """Werkseinstellung des customtkinter-Themas festhalten und daraus die
    Akzentfarben des Standard-Designs bilden.

    MUSS von gui.py NACH `ctk.set_default_color_theme(...)` gerufen werden —
    beim blossen Import stuenden hier die Farben des Standardthemas ("blue"),
    waehrend die Widgets spaeter mit "dark-blue" gebaut werden. Genau das war
    beim ersten Anlauf der Fehler: der Umfaerber verglich mit Farben, die im
    Fenster nirgends vorkamen, und traf keinen einzigen Knopf."""
    if _FACTORY:
        return
    t = ctk.ThemeManager.theme
    _FACTORY.update({
        "button": t["CTkButton"]["fg_color"],
        "button_hover": t["CTkButton"]["hover_color"],
        "progress": t["CTkSlider"]["progress_color"],
        "bright": t["CTkSlider"]["button_color"],
        "bright_hover": t["CTkSlider"]["button_hover_color"],
        "text": t["CTkLabel"]["text_color"],
        "button_text": t["CTkButton"]["text_color"],
    })
    THEMES[DEFAULT_NAME].update(_FACTORY)
    # Die Hervorhebung bleibt im Standard bernstein, NICHT das Knopfblau.
    THEMES[DEFAULT_NAME]["accent"] = DEFAULT_ACCENT


# (Widget-Klasse, Farbfeld) -> moegliche Rollen, in dieser Reihenfolge
# geprueft. Die Tab-Leiste faerbt sich selbst um (TabBar.restyle): ihre
# Knoepfe sind gewoehnliche CTkButtons und waeren hier nicht zu unterscheiden.
_ROLES = {
    ("CTkToplevel", "fg_color"): ("base",),
    ("CTkFrame", "fg_color"): ("panel", "panel2"),
    ("CTkScrollableFrame", "fg_color"): ("panel", "panel2"),
    ("CTkButton", "fg_color"): ("button", "panel2"),
    ("CTkButton", "hover_color"): ("button_hover", "panel2_hover"),
    ("CTkSlider", "progress_color"): ("progress",),
    ("CTkSlider", "button_color"): ("bright",),
    ("CTkSlider", "button_hover_color"): ("bright_hover",),
    ("CTkCheckBox", "fg_color"): ("button",),
    ("CTkCheckBox", "hover_color"): ("button_hover",),
    ("CTkCheckBox", "checkmark_color"): ("button_text",),
    ("CTkCheckBox", "text_color"): ("text",),
    ("CTkEntry", "fg_color"): ("panel2",),
    ("CTkEntry", "text_color"): ("text",),
    ("CTkEntry", "placeholder_text_color"): ("secondary",),
    ("CTkTextbox", "fg_color"): ("panel2",),
    ("CTkTextbox", "text_color"): ("text",),
    ("CTkOptionMenu", "fg_color"): ("button",),
    ("CTkOptionMenu", "button_color"): ("button_hover",),
    ("CTkOptionMenu", "button_hover_color"): ("button_hover",),
    ("CTkOptionMenu", "text_color"): ("button_text",),
    ("CTkOptionMenu", "dropdown_fg_color"): ("panel2",),
    ("CTkOptionMenu", "dropdown_hover_color"): ("panel2_hover",),
    ("CTkOptionMenu", "dropdown_text_color"): ("text",),
    ("CTkSegmentedButton", "fg_color"): ("panel2",),
    ("CTkSegmentedButton", "selected_color"): ("button",),
    ("CTkSegmentedButton", "selected_hover_color"): ("button_hover",),
    ("CTkSegmentedButton", "unselected_color"): ("panel2",),
    ("CTkSegmentedButton", "unselected_hover_color"): ("panel2_hover",),
    ("CTkProgressBar", "progress_color"): ("progress",),
    ("CTkLabel", "text_color"): ("secondary", "accent", "text"),
}


def names() -> list[str]:
    """Design-Namen in Anzeige-Reihenfolge (Default zuerst)."""
    return list(THEMES)


# Bis heute hiess das Standard-Design "Default"; eine gespeicherte Wahl aus
# einer aelteren Fassung soll deswegen nicht ins Leere zeigen.
ALIASES = {"Default": DEFAULT_NAME}


def resolve(name: str) -> str:
    """Namen auf ein vorhandenes Design abbilden (inkl. alter Schreibweise)."""
    name = ALIASES.get(name, name)
    return name if name in THEMES else DEFAULT_NAME


def get(name: str) -> dict:
    return THEMES[resolve(name)]


def _theme_defaults(pal: dict) -> None:
    """Vorgaben fuer alles, was noch GEBAUT wird (Baeume klappen spaeter auf)."""
    t = ctk.ThemeManager.theme
    t["CTk"]["fg_color"] = pal["base"]
    t["CTkToplevel"]["fg_color"] = pal["base"]
    t["CTkFrame"]["fg_color"] = pal["panel"]
    t["CTkFrame"]["top_fg_color"] = pal["panel"]
    t["CTkButton"]["fg_color"] = pal["button"]
    t["CTkButton"]["hover_color"] = pal["button_hover"]
    t["CTkButton"]["text_color"] = pal["button_text"]
    t["CTkCheckBox"]["checkmark_color"] = pal["button_text"]
    t["CTkSlider"]["progress_color"] = pal["progress"]
    t["CTkSlider"]["button_color"] = pal["bright"]
    t["CTkSlider"]["button_hover_color"] = pal["bright_hover"]
    t["CTkCheckBox"]["fg_color"] = pal["button"]
    t["CTkCheckBox"]["hover_color"] = pal["button_hover"]
    t["CTkCheckBox"]["text_color"] = pal["text"]
    t["CTkEntry"]["fg_color"] = pal["panel2"]
    t["CTkEntry"]["text_color"] = pal["text"]
    t["CTkEntry"]["placeholder_text_color"] = pal["secondary"]
    t["CTkTextbox"]["fg_color"] = pal["panel2"]
    t["CTkTextbox"]["text_color"] = pal["text"]
    t["CTkOptionMenu"]["fg_color"] = pal["button"]
    t["CTkOptionMenu"]["button_color"] = pal["button_hover"]
    t["CTkOptionMenu"]["button_hover_color"] = pal["button_hover"]
    t["CTkOptionMenu"]["text_color"] = pal["button_text"]
    t["DropdownMenu"]["fg_color"] = pal["panel2"]
    t["DropdownMenu"]["hover_color"] = pal["panel2_hover"]
    t["DropdownMenu"]["text_color"] = pal["text"]
    t["CTkLabel"]["text_color"] = pal["text"]
    t["CTkSegmentedButton"]["fg_color"] = pal["panel2"]
    t["CTkSegmentedButton"]["selected_color"] = pal["button"]
    t["CTkSegmentedButton"]["selected_hover_color"] = pal["button_hover"]
    t["CTkSegmentedButton"]["unselected_color"] = pal["panel2"]
    t["CTkSegmentedButton"]["unselected_hover_color"] = pal["panel2_hover"]


def fix_button_text(widget) -> int:
    """Schriftfarbe JEDES Knopfes aus seiner EIGENEN Flaeche bestimmen.

    Eine einzige Vorgabe im ThemeManager reicht nicht: die Akzentknoepfe und
    die dunklen Nebenknoepfe (inaktive Tabs, FAQ, Changed only) brauchen
    entgegengesetzte Schrift. Im Monolith-Design (fast weisser Akzent) stand
    sonst entweder heller Text auf hellem Knopf oder dunkler auf dunklem —
    beides unlesbar, beides erst im Bild aufgefallen."""
    if getattr(widget, "_theme_static", False):
        return 0
    n = 0
    if widget.__class__.__name__ == "CTkButton":
        try:
            fg = _solid(widget.cget("fg_color"))
            hover = _solid(widget.cget("hover_color"))
            if isinstance(fg, str) and (fg.startswith("#") or fg.startswith("gray")):
                color = _readable(fg, hover)
                widget.configure(
                    text_color=color,
                    # GESPERRTE Schrift = normale Schrift. "Build pak",
                    # "Install to ~mods", "Scan ~mods" und "Remove from
                    # ~mods" sind vor dem Laden der Spieldaten gesperrt und
                    # sahen daneben blass aus; der Besitzer wollte zweimal
                    # ausdruecklich dieselbe Schriftfarbe wie bei "Save
                    # preset"/"Open output". Der Preis ist bewusst in Kauf
                    # genommen: die Schrift zeigt nicht mehr an, dass ein
                    # Knopf noch wartet — dafuer pulst jetzt "Confirm & load
                    # game data" orange und sagt, was zuerst dran ist.
                    text_color_disabled=color)
                n = 1
        except Exception:
            pass
    for child in widget.winfo_children():
        n += fix_button_text(child)
    return n


class SegmentedButton(ctk.CTkSegmentedButton):
    """Keep selected and unselected captions readable after every selection."""
    def set(self, *args, **kwargs):
        super().set(*args, **kwargs)
        fix_button_text(self)


def _repaint(widget, old: dict, new: dict) -> int:
    """Alles umfaerben, was noch EXAKT die alte Farbe seiner Rolle traegt.
    Ein Knopf mit eigener Farbe (die Systemfarben) faellt damit von selbst
    durch das Raster."""
    if getattr(widget, "_theme_static", False):
        return 0
    n = 0
    cls = "CTkSegmentedButton" if isinstance(widget, SegmentedButton) else widget.__class__.__name__
    changes = {}
    for (klass, attr), roles in _ROLES.items():
        if klass != cls:
            continue
        try:
            cur = str(widget.cget(attr))
        except Exception:
            continue
        for role in roles:
            was, now = old.get(role), new.get(role)
            if was is None or now is None or was == now:
                continue
            if cur != str(was):
                continue
            changes[attr] = now
            break                      # eine Rolle je Farbfeld genuegt
    if changes:
        widget.configure(**changes)
        n += len(changes)
    for child in widget.winfo_children():
        n += _repaint(child, old, new)
    return n


def apply(root, name: str, previous: str = DEFAULT_NAME) -> int:
    """Design umschalten. Liefert die Zahl der umgefaerbten Farbfelder
    (nur fuer Tests und Protokoll)."""
    new = get(name)
    old = get(previous)
    _theme_defaults(new)
    painted = 0
    try:
        if str(root.cget("fg_color")) == str(old["base"]):
            root.configure(fg_color=new["base"])
            painted += 1
    except Exception:
        pass
    painted += _repaint(root, old, new)
    return painted


def apply_button_text(root) -> int:
    """Nach dem Umfaerben (und nach TabBar.restyle) die Knopfschrift
    nachziehen — siehe fix_button_text."""
    return fix_button_text(root)
