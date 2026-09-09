"""Opt-in GUI diagnostics for a single Windows process; never run on import."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback


def measure(args):
    from s2tweaker import gui
    from s2tweaker.gamedata import GameData
    from s2tweaker.workbench_ui import OVERVIEW_PAGE_SIZE

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    user.GetGuiResources.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    user.GetGuiResources.restype = wintypes.DWORD
    process = kernel.GetCurrentProcess()
    report = {"python": sys.version, "samples": [], "errors": [], "passed": False}
    app = None
    started = time.perf_counter()

    def write():
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    def callback_error(exc, value, tb):
        report["errors"].append("".join(traceback.format_exception(exc, value, tb)))

    def sample(stage):
        app.update()
        pending = [app]
        widgets = 0
        while pending:
            widget = pending.pop()
            widgets += 1
            pending.extend(widget.winfo_children())
        record = {"stage": stage, "elapsed_s": round(time.perf_counter() - started, 3),
                  "tk_widgets": widgets}
        for name, flag in (("gdi", 0), ("user", 1), ("gdi_peak", 2), ("user_peak", 4)):
            record[name] = user.GetGuiResources(process, flag)
        report["samples"].append(record)
        print(json.dumps(record), flush=True)
        write()
        if not record["user"] or not record["gdi"]:
            raise AssertionError("GetGuiResources did not return usable counts")
        # Leave room below the standard 10,000-object process quotas.
        if max(record[key] for key in ("user", "gdi", "user_peak", "gdi_peak")) >= 8000:
            raise AssertionError("GUI resource budget exceeded (must stay below 8,000)")
        if report["errors"]:
            raise AssertionError("Tk callback raised an error")

    try:
        with tempfile.TemporaryDirectory(prefix="s2tweaker-gui-check-") as temp:
            temp = Path(temp)
            gui.SETTINGS_FILE = temp / "settings.json"
            gui.app_dir = lambda: temp
            gui.output_dir = lambda: temp / "output"
            # Skip only installation discovery/prompts, not window construction.
            gui.App._prefill_game = lambda self: None
            gui.App._check_oodle_present = lambda self: None
            gui.App.report_callback_exception = lambda self, *error: callback_error(*error)
            app = gui.App()
            app.geometry("1280x850")
            sample("startup")
            if getattr(args, "design_review", False):
                from s2tweaker import theme
                report["mode"] = "all palettes, visible toolbar and manual design review"
                app._set_body_state(True)
                app.geometry("1000x760")
                app.tabs.set("Player")
                sample("minimum window width")
                for control in (app.btn_theme, app.btn_scroll, app.btn_oodle, app.search_entry):
                    assert control.winfo_ismapped()
                    assert control.winfo_width() >= 80
                    assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
                assert not gui.SliderRow._wheel_enabled
                assert app.btn_scroll.cget("fg_color") == gui.BAD_RED
                app.btn_scroll.invoke()
                assert gui.SliderRow._wheel_enabled
                assert app.btn_scroll.cget("fg_color") == gui.OK_GREEN
                first = app.sliders["hp"]
                for name in theme.names():
                    app._set_theme(name)
                    pal = theme.get(name)
                    assert app.btn_scroll.cget("fg_color") == gui.OK_GREEN
                    assert first.value_label.cget("foreground").lower() == theme._solid(pal["text"]).lower()
                    assert first.entry.cget("text_color") == pal["text"]
                    for tab in ("Overview", "Player"):
                        app.tabs.set(tab)
                        for button in app.tabs._buttons.values():
                            assert theme.contrast(button.cget("text_color"), button.cget("fg_color")) >= 4.5
                    for mode in ("Favorites", "My changes"):
                        app.wb_modes.set(mode)
                        for button in app.wb_modes._buttons_dict.values():
                            assert theme.contrast(button.cget("text_color"), button.cget("fg_color")) >= 4.5
                    sample("design: " + name)
                app.btn_scroll.invoke()
                assert not gui.SliderRow._wheel_enabled
                assert app.btn_scroll.cget("fg_color") == gui.BAD_RED
                app._set_theme("Duty")
                app.geometry("1280x850")
                app.btn_theme.invoke()
                sample("design chooser")
                # Reserve shutdown time inside the parent's 90-second limit.
                remaining_ms = int((80 - (time.perf_counter() - started)) * 1000)
                app.after(max(1, min(20000, remaining_ms)), app.quit)
                app.mainloop()
                sample("design visual review")
                report["passed"] = True
                app.destroy()
                app = None
                return 0
            if getattr(args, "visual_review", False):
                report["mode"] = "visual review (not the full resource sweep)"
                app._set_body_state(True)
                app.tabs.set("Player")
                app.after(60000, app.quit)
                app.mainloop()
                sample("visual review")
                app.destroy()
                app = None
                report["passed"] = True
                return 0
            if args.vanilla:
                app.gd = GameData(args.vanilla)
                for populate in (app._iw_populate, app._ia_populate, app._isc_populate,
                                 app._ir_populate, app._if_populate, app._im_populate):
                    populate()
                sample("item trees loaded")
            app._set_body_state(True)
            if args.vanilla:
                app.tabs.set("Armor")
                # Switching individual items must release the previous editor.
                for block in app._ir_blocks.values():
                    block.expand()
                    for row in list(block.rows.values())[:3]:
                        row.toggle()
                        sample("armor: " + row.sid)
                    block.collapse()
                active = getattr(app, "_ir_active_row", None)
                if active is not None:
                    active.release_editor()
            # Build real paged cards and edit a deferred value through the UI.
            app._wb_extra_controls()
            app._wb_edit(("sliders", "npc_armor_drop_chance_pct"), "25")
            assert app._collect().npc_armor_drop_chance_pct == 25
            sample("optional controls edited")
            app._wb_choose_view("Browse controls")
            sample("browse first page")
            first_page = report["samples"][-1]["user"]
            for _ in range(3):
                app._wb_change_page(1)
                assert len(app.wb_rows.winfo_children()) <= OVERVIEW_PAGE_SIZE
                sample("browse next page")
            if report["samples"][-1]["user"] > first_page + 100:
                raise AssertionError("Overview paging retains old controls")
            app._wb_set_density("Detailed")
            for tab in list(app.tabs._name_list):
                app.tabs.set(tab)
                if tab != "Overview":
                    assert not app.wb_rows.winfo_children()
                sample("detailed: " + tab)
            app._wb_set_density("Compact")
            app._wb_set_scale("115%")
            sample("115% scale")
            app._wb_set_scale("100%")
            # Creating a real menu was the reported fatal operation in 1.37.0.
            app._wb_context(type("Position", (), {"x_root": app.winfo_rootx() + 40,
                                                  "y_root": app.winfo_rooty() + 40})(),
                            ("sliders", "hp"))
            app._wb_menu.unpost()
            sample("context menu")
            app.tabs.set("Player")
            sample("final")
            report["passed"] = True
            app.destroy()
            app = None
    except Exception:
        report["errors"].append(traceback.format_exc())
        report["passed"] = False
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                report["errors"].append(traceback.format_exc())
        report["elapsed_s"] = round(time.perf_counter() - started, 3)
        write()
    return 0 if report["passed"] and not report["errors"] else 1
