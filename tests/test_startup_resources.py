"""Resource regressions without creating Tk windows; real counts are opt-in."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import extension_controls as ext
from s2tweaker.editor_state import History
from s2tweaker.workbench_ui import WorkbenchMixin, OVERVIEW_PAGE_SIZE


class Registry(WorkbenchMixin):
    def __init__(self):
        self.sliders, self.checks, self.slider_tabs, self._wb_meta = {}, {}, {}, {}
        self._current_tab = "World"
        self._wb_bindings = {}
        self._wb_busy = self._wb_restoring = False
        self._wb_favorites = set()
        self._wb_render_overview = Mock()
        self._wb_update_history_buttons = Mock()
        self._wb_build_overview = Mock()
        self._wb_tick = Mock()
        self.cat_checks = {}
        self.name_entry = SimpleNamespace(get=lambda: "OwnMod")
        self.tabs = SimpleNamespace(set=Mock(), get=lambda: "Overview")
        self.bind_all = self.bind = Mock()
        ext.build_controls(self, None, None)
        self._wb_history = History(self._wb_snapshot())

    def _section(self, *args):
        return None

    def _check(self, parent, key, title, tip):
        self.checks[key] = False

    def _build_extension_link(self, body):
        pass

    def _body_enabled_state(self):
        return "normal"

    def _ui_state(self):
        return {"sliders": {key: row.get() for key, row in self.sliders.items()}}


class StartupResources(unittest.TestCase):
    def test_unavailable_regional_weather_stays_visible_only_for_reset(self):
        app = Registry()
        app._wb_defaults = {"sliders": {k: r.default for k, r in app.sliders.items()}}
        region = "LesserZoneWeather"
        app.gd = SimpleNamespace(regional_weather={region: {"Fogy": {region: {}}}})
        active = ("sliders", ext.regional_weather.control_key(region, "Fogy", "weight"))
        inactive = ("sliders", ext.regional_weather.control_key(region, "Thundery", "weight"))
        rows = {r[0]: r for r in app._wb_catalog()}
        self.assertIn(active, rows)
        self.assertNotIn(inactive, rows)
        app.sliders[inactive[1]].set(200)  # a preset from a different game snapshot
        rows = {r[0]: r for r in app._wb_catalog()}
        self.assertIn("inactive", rows[inactive][1])
        self.assertIn("Reset to 100%", app._wb_info(inactive)[2])
        with patch("s2tweaker.workbench_ui.messagebox.showinfo") as error:
            app._wb_edit(inactive, "250")
            error.assert_called_once()
        self.assertEqual(app.sliders[inactive[1]].get(), 200)
        app._wb_edit(inactive, "100")
        self.assertNotIn(inactive, {r[0] for r in app._wb_catalog()})
        self.assertEqual(ext.regional_weather.collect(app.sliders), {})

    def test_region_shortcut_filters_the_existing_overview(self):
        app = Registry()
        app.gd = SimpleNamespace(regional_weather={})
        app.wb_search = Mock()
        app._wb_choose_view = Mock()
        app._wb_regional_weather("Red Forest")
        app.wb_search.insert.assert_called_once_with(0, "Regional weather: Red Forest /")
        app._wb_choose_view.assert_called_once_with("Loot & world")

    def test_optional_registry_is_complete_without_any_slider_widgets(self):
        app = Registry()  # no _slider method: eager creation fails this test
        specs = list(ext.control_specs())
        self.assertEqual(len(specs), len(ext.SLIDERS) + len(ext.SURFACES) + len(ext.WEATHERS)
                         + 2 * len(ext.SPECIES) + len(list(ext.regional_weather.control_specs()))
                         + len(ext.artifact_extensions.CONTROLS) + len(ext.npc_equipment.CONTROLS) + len(ext.detail_controls.CONTROLS))
        self.assertEqual(len(app.sliders), len(specs))
        self.assertEqual(len(app._extension_paths), len(specs) + len(ext.CHECKS))
        self.assertFalse(app._wb_bindings)
        self.assertEqual(ext.collect_factors(app.sliders, "surface_noise:"), {})
        self.assertEqual(ext.collect_mutant_loot(app.sliders), {})

    def test_deferred_edits_enter_history_and_export_collections(self):
        app = Registry()
        path = ("sliders", "mutant_loot:Flesh:amount_factor")
        app._wb_edit(path, "250")
        self.assertEqual(ext.collect_mutant_loot(app.sliders), {"Flesh": {"amount_factor": 2.5}})
        self.assertEqual(len(app._wb_history.past), 1)
        snapshot = app._wb_history.undo()
        for key, value in snapshot["sliders"].items():
            app.sliders[key].set(value)
        self.assertEqual(ext.collect_mutant_loot(app.sliders), {})
        for key, value in app._wb_history.redo()["sliders"].items():
            app.sliders[key].set(value)
        self.assertEqual(app.sliders[path[1]].get(), 250)
        app.sliders[path[1]].reset()
        self.assertEqual(app.sliders[path[1]].get(), 100)

    def test_locks_and_invalid_edits_are_enforced_in_overview(self):
        app = Registry()
        path = ("sliders", "npc_armor_drop_chance_pct")
        row = app.sliders[path[1]]
        unlock = Mock()
        row.set_locked(True, unlock)
        with patch("s2tweaker.workbench_ui.messagebox.showinfo") as error:
            app._wb_edit(path, "50")
            self.assertEqual(row.get(), 0)
            error.assert_called_once()
        row._unlock()
        unlock.assert_called_once()
        row.set_locked(False)
        row.set_state("disabled")
        with patch("s2tweaker.workbench_ui.messagebox.showinfo"):
            app._wb_edit(path, "50")
        self.assertEqual(row.get(), 0)
        row.set_state("normal")
        for value in ("nan", "inf", "101", "-1"):
            with patch("s2tweaker.workbench_ui.messagebox.showinfo") as error:
                app._wb_edit(path, value)
                error.assert_called_once()
            self.assertEqual(row.get(), 0)
        app._wb_edit(path, "22,5")
        self.assertEqual(row.get(), 23)  # same whole-number rounding as SliderRow
        row.set_conflict(["A", "B"], ["A", "C"], ["B", "C"])
        self.assertEqual(row.conflict_after, {"A"})
        self.assertEqual(row.conflict_unknown, {"B"})

    def test_setup_does_not_rescale_the_built_window(self):
        app = Registry()
        app._wb_scale = 100
        with patch("s2tweaker.workbench_ui.ctk.set_widget_scaling") as scale:
            app._wb_setup()
            app._wb_set_scale("100%")
            scale.assert_not_called()

    def test_saved_scale_is_applied_once_before_build(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "editor.json").write_text('{"scale":115}', encoding="utf-8")
            app = Registry()
            with patch("s2tweaker.gui.app_dir", return_value=Path(folder)), patch(
                    "s2tweaker.workbench_ui.ctk.set_widget_scaling") as scale:
                app._wb_init()
                app._wb_setup()
                app._wb_set_scale("115%")
                scale.assert_called_once_with(1.15)

    def test_registration_has_no_per_row_buttons_and_overview_is_bounded(self):
        # Budget backstop for the precise regression; this does NOT measure
        # native Windows resources (tools/check_gui_resources.py does that).
        for file, method in (("workbench_ui.py", "_wb_register"), ("gui.py", "_check")):
            tree = ast.parse((ROOT / "s2tweaker" / file).read_text(encoding="utf-8"))
            func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == method)
            calls = [n.func.attr for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
            self.assertNotIn("CTkButton", calls)
        self.assertLessEqual(OVERVIEW_PAGE_SIZE, 20)

    def test_leaving_overview_destroys_hidden_cards(self):
        app = Registry()
        cards = [Mock(), Mock()]
        app.wb_rows = SimpleNamespace(winfo_children=lambda: cards)
        app.tabs.get = lambda: "Player"
        app._wb_check_hints = {}
        app._wb_tab_changed()
        for card in cards:
            card.destroy.assert_called_once()
        self.assertIsNone(app._wb_render_stamp)

    def test_releasing_armor_widgets_preserves_values_and_removes_bindings(self):
        from s2tweaker.gui import IrArmorRow
        app = SimpleNamespace(armor_overrides={"Suit": {"physical": 2}},
                              armor_custom={"Suit": {"weight": 4}},
                              _wb_bindings={("armor_overrides", "Suit", "physical"): Mock(),
                                            ("armor_custom", "Suit", "weight"): Mock(),
                                            ("sliders", "hp"): Mock()})
        row = IrArmorRow.__new__(IrArmorRow)
        row.app, row.sid, row.body, row.btn = app, "Suit", Mock(), Mock()
        row.sliders, row.custom_sliders = {"physical": Mock()}, {"weight": Mock()}
        row.refresh = Mock()
        app._ir_active_row = row
        body = row.body
        row.release_editor()
        body.destroy.assert_called_once()
        self.assertEqual(set(app._wb_bindings), {("sliders", "hp")})
        self.assertEqual(app.armor_custom, {"Suit": {"weight": 4}})
        self.assertEqual(app.armor_overrides, {"Suit": {"physical": 2}})
        self.assertFalse(row.expanded)
        self.assertIsNone(row.body)
        self.assertIsNone(app._ir_active_row)
        row.release_editor()  # repeated collapse must remain harmless

    def test_native_value_display_uses_surrounding_font_scale_and_background(self):
        from s2tweaker.gui import SliderRow
        row = SliderRow.__new__(SliderRow)
        row.row, row.label, row.value_label = Mock(), Mock(), Mock()
        row._orig_color = "text"
        row.row.cget.return_value = "panel"
        row.row._apply_appearance_mode.return_value = "#202020"
        row.label._apply_appearance_mode.return_value = "#eeeeee"
        row.label.cget.return_value = "font object"
        row.label._apply_font_scaling.return_value = ("Segoe UI", -15)
        row._sync_value_label()
        row.value_label.configure.assert_called_once_with(
            background="#202020", foreground="#eeeeee", font=("Segoe UI", -15))
        row.row.cget.assert_called_once_with("bg_color")
        row.label._apply_font_scaling.assert_called_once_with("font object")


if __name__ == "__main__":
    unittest.main()
