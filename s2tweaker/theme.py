"""Faction-inspired interface palettes with fixed semantic system colors.

These palettes are designed UI colors, not values extracted from game assets.
base/panel/panel2 define surfaces; accent/bright define highlights; secondary
and text define typography. Success, destructive-action and warning colors
remain stable across themes.

Update both ThemeManager defaults for lazy widgets and existing widgets by
(class, color-field) role. A plain old-color/new-color mapping is ambiguous
when a palette reuses the same color for different roles."""
from __future__ import annotations

import customtkinter as ctk

# --- System colors: shared by every theme ---
SUCCESS = "#2d6a3f"        # Ready / confirm.
SUCCESS_HOVER = "#377f4c"
DANGER = "#7a2d2d"         # Destructive action or missing item.
DANGER_HOVER = "#8f3838"
WARNING = "#d9a648"        # Warning boxes and notices.
# Outline system buttons to distinguish them from similarly colored themes.
# Pulse the load border orange until game data is ready, then show green.
ATTENTION = "#A9701F"
ATTENTION_HOVER = "#C4832A"
ATTENTION_BORDER = "#E5AC4E"
SUCCESS_BORDER = "#4FA96B"
DANGER_BORDER = "#C0453F"
SYSTEM_BORDER_WIDTH = 2

# Keep button-fill and highlight roles separate. Standard uses blue buttons
# and amber highlights; faction text accents are brighter than button fills.
ROLES = ("base", "panel", "panel2", "panel2_hover", "button", "button_hover",
         "progress", "bright", "bright_hover", "accent", "button_text",
         "secondary", "text")


def _shade(color: str, factor: float) -> str:
    """Make the same hue lighter (factor > 1) or darker (factor < 1)."""
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


# Standard uses the tool's dark background; snapshot() captures CTk accent defaults.
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
    """Capture factory colors after ctk.set_default_color_theme(...).

    Capturing at import time would record the wrong defaults and prevent
    role matching against the actual widgets."""
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
    # Standard highlights stay amber, independently of blue button fills.
    THEMES[DEFAULT_NAME]["accent"] = DEFAULT_ACCENT


# Map widget class/color-field pairs to candidate roles in priority order.
# The tab bar applies its own active/inactive button roles.
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
    """Theme names in display order, Default first."""
    return list(THEMES)


# Accept the previous Default name in saved preferences.
ALIASES = {"Default": DEFAULT_NAME}


def resolve(name: str) -> str:
    """Resolve current and legacy names to an available theme."""
    name = ALIASES.get(name, name)
    return name if name in THEMES else DEFAULT_NAME


def get(name: str) -> dict:
    return THEMES[resolve(name)]


def _theme_defaults(pal: dict) -> None:
    """Set defaults for widgets created later, including lazy tree rows."""
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
    """Choose button text contrast from each button's own fill.

    One global text color cannot suit both bright accents and dark secondary buttons."""
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
                    # Use the normal text color on disabled system buttons for legibility.
                    # The pulsing load action identifies the prerequisite before they become enabled.
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
    """Recolor fields matching their old role color; preserve custom system colors."""
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
            break                      # One role match per color field is sufficient.
    if changes:
        widget.configure(**changes)
        n += len(changes)
    for child in widget.winfo_children():
        n += _repaint(child, old, new)
    return n


def apply(root, name: str, previous: str = DEFAULT_NAME) -> int:
    """Apply a theme and return the number of recolored fields for diagnostics."""
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
    """Refresh button text contrast after recoloring and tab-bar restyling."""
    return fix_button_text(root)
