"""Colour contrast and theme switching without starting a Tk window."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker import gui, theme


class Widget:
    def __init__(self, values, children=()):
        self.values, self.children = dict(values), children

    def cget(self, key):
        return self.values[key]

    def configure(self, **values):
        self.values.update(values)

    def winfo_children(self):
        return self.children


def widget(klass, values, children=()):
    return type(klass, (Widget,), {})(values, children)


class PaletteTests(unittest.TestCase):
    def tearDown(self):
        theme._theme_defaults(theme.get(theme.DEFAULT_NAME))

    def test_all_palettes_keep_small_text_and_hover_readable(self):
        for name in theme.names():
            pal = theme.get(name)
            with self.subTest(theme=name):
                for role in ("text", "secondary", "accent"):
                    for surface in ("base", "panel", "panel2"):
                        self.assertGreaterEqual(theme.contrast(pal[role], pal[surface]), 4.5)
                for surface in ("button", "button_hover"):
                    self.assertGreaterEqual(theme.contrast(pal["button_text"], pal[surface]), 4.5)

    def test_each_role_survives_every_theme_and_return_to_standard(self):
        # Isolate each role so shared colours cannot hide a failed round-trip.
        standard = theme.get(theme.DEFAULT_NAME)
        for (klass, attr), roles in theme._ROLES.items():
            for role in roles:
                item = widget(klass, {attr: standard[role]})
                previous = standard
                for name in [*theme.names(), theme.DEFAULT_NAME]:
                    pal = theme.get(name)
                    theme._repaint(item, previous, pal)
                    self.assertEqual(item.cget(attr), pal[role], (name, klass, attr, role))
                    previous = pal

    def test_system_colours_and_palette_previews_are_preserved(self):
        button = widget("CTkButton", {"fg_color": theme.DANGER, "hover_color": theme.DANGER_HOVER})
        preview_label = widget("CTkLabel", {"text_color": theme.get("Duty")["text"]})
        preview = widget("CTkFrame", {"fg_color": theme.get("Duty")["panel"]}, [preview_label])
        preview._theme_static = True
        root = widget("Root", {}, [button, preview])
        theme._repaint(root, theme.get("Duty"), theme.get("Monolith"))
        theme.fix_button_text(root)
        self.assertEqual(button.cget("fg_color"), theme.DANGER)
        self.assertEqual(button.cget("hover_color"), theme.DANGER_HOVER)
        self.assertEqual(button.cget("text_color"), button.cget("text_color_disabled"))
        self.assertEqual(preview.cget("fg_color"), theme.get("Duty")["panel"])
        self.assertEqual(preview_label.cget("text_color"), theme.get("Duty")["text"])

    def test_new_controls_use_the_current_palette(self):
        for name in theme.names():
            pal = theme.get(name)
            theme._theme_defaults(pal)
            defaults = theme.ctk.ThemeManager.theme
            for klass, attr, role in (("CTkEntry", "text_color", "text"),
                                     ("CTkTextbox", "fg_color", "panel2"),
                                     ("CTkCheckBox", "checkmark_color", "button_text"),
                                     ("CTkOptionMenu", "text_color", "button_text"),
                                     ("DropdownMenu", "text_color", "text"),
                                     ("CTkSegmentedButton", "selected_color", "button")):
                self.assertEqual(defaults[klass][attr], pal[role])


if __name__ == "__main__":
    unittest.main()
