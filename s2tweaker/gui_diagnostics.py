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
            if getattr(args, "detail_editor", False):
                from s2tweaker import detail_controls as details, npc_equipment, editor_state, cfgparse, pakio
                from s2tweaker.tweaks import build_patches
                if not args.vanilla:
                    raise ValueError("Detail editor diagnostics require --vanilla.")
                app.gd = GameData(args.vanilla)
                app._set_body_state(True)
                assert build_patches(app.gd, app._collect()) == {}
                expected = {details.PREFIX + suffix: value for suffix, value in {
                    "special:AArtifactWeirdNut:healing_drawback": 50,
                    "special:AArtifactWeirdWater:minimum": 3.75,
                    "medicine:Medkit:healing": 125,
                    "weapon_item:GunPM_HG:Weight": .25,
                    "weather:Rainy:HearingDistanceCoef": 150,
                    "camp:Ordinary faction camps:Guitar": 150,
                    "grenade:Army:Veteran": 50,
                    "upgrade:Technician bonuses:ArmorPiercing": 150,
                    "scanner:PlayerDetector:DetectorRadius": 800}.items()}
                for key, value in expected.items():
                    spec = details.CONTROLS[key]
                    app.tabs.set("World")
                    app.detail_group.set(details.GROUPS[spec.group])
                    app._wb_detail_targets(app.detail_group.get())
                    app.detail_target.set(spec.target)
                    app._wb_detail_open()
                    app.update()
                    assert app.tabs.get() == "Overview"
                    assert 0 < len(app.wb_rows.winfo_children()) <= OVERVIEW_PAGE_SIZE
                    app._wb_edit(("sliders", key), str(value))
                assert app._collect().detail_overrides == expected
                app._wb_undo()
                assert key not in app._collect().detail_overrides
                app._wb_redo()
                assert app._collect().detail_overrides == expected
                helmet = next(c for k, c in npc_equipment.CONTROLS.items()
                              if c.kind == "Chance" and k in npc_equipment.available(app.gd))
                app._wb_edit(("sliders", helmet.key), "50")
                assert app._collect().npc_equipment_overrides == {helmet.key: 50}
                profile = temp / "detail-profile.json"
                editor_state.save_profile(profile, app._ui_state(), "Detail settings")
                app._reset_all()
                assert build_patches(app.gd, app._collect()) == {}
                app._apply_ui_state(editor_state.read_profile(profile).state)
                assert app._collect().detail_overrides == expected
                assert app._collect().npc_equipment_overrides == {helmet.key: 50}
                patches = build_patches(app.gd, app._collect())
                pakio.pack_mod(patches, args.report.parent / "detail_gui_test.pak")
                assert patches
                assert all(cfgparse.parse(text).children for text in patches.values())
                # Keep one concrete screen for visual review without repeated windows.
                app.detail_group.set(details.GROUPS['medicine'])
                app._wb_detail_targets(app.detail_group.get())
                app.detail_target.set("Medkit")
                app._wb_detail_open()
                sample("all detail families and helmet edited, profile restored, Pak exported")
                # The unchanged portable runtime intentionally has no Pillow.
                # An external diagnostic host may capture this exact app window.
                report['capture_rect'] = [app.winfo_rootx(), app.winfo_rooty(), app.winfo_rootx() + app.winfo_width(), app.winfo_rooty() + app.winfo_height()]
                sample("detail screenshot")
                time.sleep(2)
                app._reset_all()
                assert build_patches(app.gd, app._collect()) == {}
                sample("detail reset")
                report['available_detail_controls'] = len(details.available(app.gd))
                report['helmet_controls'] = sum(c.kind == 'Chance' for k, c in npc_equipment.CONTROLS.items() if k in npc_equipment.available(app.gd))
                report['profile_undo_redo_reset_export'] = True
                report['passed'] = True
                app.destroy()
                app = None
                return 0
            if getattr(args, "npc_equipment", False):
                from s2tweaker import npc_equipment as equipment, editor_state, cfgparse
                from s2tweaker.tweaks import build_patches
                if not args.vanilla:
                    raise ValueError("NPC equipment diagnostics require --vanilla.")
                app.gd = GameData(args.vanilla)
                app._set_body_state(True)
                app._wb_equipment_choices()
                assert build_patches(app.gd, app._collect()) == {}
                available = equipment.available(app.gd)
                controls = [c for k, c in equipment.CONTROLS.items() if k in available]
                first = next(c for c in controls if c.obj == "GeneralNPC_Neutral_CloseCombat" and c.source == equipment.OBJECTS[c.obj][2] and c.slot == "[0]" and c.row == "[0]")
                helper = next(c for c in controls if c.obj == "GeneralNPC_Duty_Recon" and c.source != equipment.OBJECTS[c.obj][2] and "Armor" in c.source)
                shared = next(c for c in controls if c.obj == "GeneralNPC_Bandit_Recon" and " + " in c.context.split(" / ")[0])
                expected = {first.key: 200, helper.key: 50, shared.key: 0}
                def show(c):
                    app.tabs.set("World")
                    app.equipment_faction.set(c.faction)
                    app._wb_equipment_choices()
                    app.equipment_role.set(c.role)
                    app._wb_equipment_choices()
                    app.equipment_pool.set(c.pool)
                    app.equipment_edit.invoke()
                    assert app.tabs.get() == "Overview"
                    assert app.wb_search.get() == c.selection
                    assert 0 < len(app.wb_rows.winfo_children()) <= OVERVIEW_PAGE_SIZE
                for c in (first, helper, shared):
                    show(c)
                    app._wb_edit(("sliders", c.key), str(expected[c.key]))
                assert app._collect().npc_equipment_overrides == expected
                app._wb_undo()
                assert shared.key not in app._collect().npc_equipment_overrides
                app._wb_redo()
                assert app._collect().npc_equipment_overrides == expected
                profile = temp / "npc-equipment.json"
                editor_state.save_profile(profile, app._ui_state(), "NPC equipment")
                app._reset_all()
                assert not app._collect().npc_equipment_overrides
                app._apply_ui_state(editor_state.read_profile(profile).state)
                assert app._collect().npc_equipment_overrides == expected
                patches = build_patches(app.gd, app._collect())
                assert len(patches) == 2
                obj_file = next(v for k, v in patches.items() if k.startswith("ObjPrototypes/"))
                assert set(cfgparse.parse(obj_file).children) == {first.obj, helper.obj, shared.obj}
                sample("NPC equipment edited, restored and exported")
                app.tabs.set("World")
                app.update()
                body = app.equipment_frame.master
                canvas = body._parent_canvas
                canvas.yview_moveto(app.equipment_frame.winfo_y() / max(1, body.winfo_height()))
                sample("equipment screenshot selector")
                time.sleep(.8)
                for label, c in (("weapon", first), ("armor", helper), ("ranks", shared)):
                    show(c)
                    sample("equipment screenshot " + label)
                    time.sleep(.8)
                app._reset_all()
                assert build_patches(app.gd, app._collect()) == {}
                sample("NPC equipment reset")
                report["available_controls"] = len(available)
                report["profiles_checked"] = 3
                report["passed"] = True
                app.destroy()
                app = None
                return 0
            if getattr(args, "artifact_editor", False):
                from s2tweaker import artifact_extensions as artifacts, editor_state
                from s2tweaker.tweaks import build_patches
                if not args.vanilla:
                    raise ValueError("Artifact editor diagnostics require --vanilla.")
                app.gd = GameData(args.vanilla)
                app._set_body_state(True)
                assert build_patches(app.gd, app._collect()) == {}
                app.checks["art_stat_labels"].select()
                assert app._collect().artifact_stat_labels_follow
                assert build_patches(app.gd, app._collect()) == {}
                selections = (("item", "CArtifactLiquidStone"), ("detector", "Echo"),
                              ("ball", "AArtifactWeirdBall"), ("anomaly", "FireBallAnomaly"),
                              ("rarity", "UniversalArtifactSpawner"))
                def show(group, target):
                    label = artifacts.GROUPS[group]
                    app.tabs.set("World")
                    app.artifact_editor_group.set(label)
                    app._wb_artifact_targets(label)
                    app.artifact_editor_target.set(target)
                    app.artifact_editor_edit.invoke()
                    assert app.tabs.get() == "Overview"
                    assert app.wb_search.get() == f"{label} / {target} /"
                    assert 0 < len(app.wb_rows.winfo_children()) <= OVERVIEW_PAGE_SIZE
                for group, target in selections:
                    show(group, target)
                expected = {artifacts.PREFIX + k: v for k, v in {
                    "item:EArtifactFlash:weight": .125,
                    "item:EArtifactFlash:ArtifactProtectionShock1": 150,
                    "item:EArtifactFlash:radiation": 2,
                    "item:CArtifactLiquidStone:extra_ProtectionBurn": 200,
                    "item:CArtifactLiquidStone:extra_AdditionalInventoryWeight": 100,
                    "detector:Echo:reveal": 500,
                    "ball:AArtifactWeirdBall:MaxWeight": 3.75,
                    "anomaly:FireBallAnomaly:speed": 50,
                    "rarity:UniversalArtifactSpawner:Experienced.Rare": 200}.items()}
                for key, value in expected.items():
                    app._wb_edit(("sliders", key), str(value))
                assert app._collect().artifact_overrides == expected
                app._wb_undo()
                assert len(app._collect().artifact_overrides) == len(expected) - 1
                app._wb_redo()
                assert app._collect().artifact_overrides == expected
                profile = temp / "artifact-profile.json"
                editor_state.save_profile(profile, app._ui_state(), "Artifact editor")
                app._reset_all()
                assert not app._collect().artifact_overrides
                assert not app._collect().artifact_stat_labels_follow
                app._apply_ui_state(editor_state.read_profile(profile).state)
                assert app._collect().artifact_overrides == expected
                assert app._collect().artifact_stat_labels_follow
                patches = build_patches(app.gd, app._collect())
                assert len(patches) == 4
                assert any("EffectLevel = EEffectLevel::Medium" in text for text in patches.values())
                assert any("refkey=ArtifactProtectionBurn1" in text for text in patches.values())
                assert any("refkey=ArtifactPenaltyLessWeightEffect1" in text for text in patches.values())
                sample("five artifact families edited, restored and exported")
                report["screenshots"] = []
                for group, target in (selections[0], selections[1], selections[4]):
                    show(group, target)
                    app.update()
                    shot = args.report.with_name("artifact_editor_" + group + ".png")
                    report["screenshots"].append(str(shot))
                    # An external diagnostic host can capture this exact window.
                    # The portable player package intentionally has no Pillow.
                    sample("artifact screenshot " + group)
                    time.sleep(.7)
                app._reset_all()
                assert build_patches(app.gd, app._collect()) == {}
                sample("artifact editor reset")
                if getattr(args, "source_pak", None):
                    from s2tweaker import pakfile, localization, job_localization
                    app.gd = GameData(args.vanilla, source_pak=args.source_pak)
                    app.checks["rq_jobs_multi"].select()
                    target = temp / "jobs.pak"
                    showinfo = gui.messagebox.showinfo
                    try:
                        gui.messagebox.showinfo = lambda *args, **kwargs: None
                        assert app._generate(target)
                    finally:
                        gui.messagebox.showinfo = showinfo
                    with pakfile.PakFile(target) as pak:
                        paths = [path for path in pak.files() if path.endswith(".locres")]
                        assert paths
                        for path in paths:
                            assert path.endswith("/Game.locres")
                            entries = localization.read_resource(pak.read(path))
                            assert (job_localization.NAMESPACE, "sid_journal_S2T_Job_RSQ04_C02_Name") in entries
                            assert sum("S2T_Job_" in key for _ns, key in entries) == 208
                            assert any("S2T_Job_" not in key for _ns, key in entries)
                    report["exported_job_languages"] = len(paths)
                    app._reset_all()
                    assert build_patches(app.gd, app._collect()) == {}
                    sample("automatic job translations exported through GUI")
                report["families_checked"] = len(selections)
                report["available_controls"] = len(app.gd.artifact_editor)
                report["passed"] = True
                app.destroy()
                app = None
                return 0
            if getattr(args, "dialog_range", False):
                from s2tweaker import editor_state, cfgparse
                from s2tweaker.tweaks import build_patches
                if not args.vanilla:
                    raise ValueError("Talk-distance diagnostics require --vanilla.")
                app.gd = GameData(args.vanilla)
                app._set_body_state(True)
                app.tabs.set(app.slider_tabs["dialog_max_range"])
                control = app.sliders["dialog_max_range"]
                assert control.get() == 100
                app._wb_edit(("sliders", "dialog_max_range"), "180")
                settings = app._collect()
                assert settings.dialog_range_factor == 1
                assert settings.dialog_max_range_factor == 1.8
                app._wb_undo()
                assert control.get() == 100
                app._wb_redo()
                assert control.get() == 180
                profile = temp / "talk-distance.json"
                editor_state.save_profile(profile, app._ui_state(), "Maximum talk distance")
                app._reset_all()
                app._apply_ui_state(editor_state.read_profile(profile).state)
                assert app._collect().dialog_max_range_factor == 1.8
                patches = build_patches(app.gd, app._collect())
                assert len(patches) == 1
                tree = cfgparse.parse(next(iter(patches.values())))
                assert all(set(n.values) == {"MaxDialogInteractDistance"}
                           for n in tree.children.values())
                app.update_idletasks()
                frame = control._scroll_frame()
                canvas = frame._parent_canvas
                bounds = canvas.bbox("all")
                top = canvas.canvasy(0) + control.row.winfo_rooty() - canvas.winfo_rooty()
                canvas.yview_moveto(max(0, top - 110) / max(1, bounds[3]))
                sample("maximum talk distance edited, restored and exported")
                app._reset_all()
                assert build_patches(app.gd, app._collect()) == {}
                sample("maximum talk distance reset")
                report["participants_checked"] = len(tree.children)
                report["passed"] = True
                app.destroy()
                app = None
                return 0
            if getattr(args, "regional_weather", False):
                from s2tweaker import regional_weather as weather, editor_state
                from s2tweaker.tweaks import build_patches
                if not args.vanilla:
                    raise ValueError("Regional weather diagnostics require --vanilla.")
                app.gd = GameData(args.vanilla)
                app._set_body_state(True)
                for region in app.gd.regional_weather:
                    app.tabs.set("World")
                    label = weather.REGIONS[region][0]
                    app.regional_weather_choice.set(label)
                    app.regional_weather_edit.invoke()
                    assert app.tabs.get() == "Overview"
                    assert app.wb_search.get() == f"Regional weather: {label} /"
                    assert 0 < len(app.wb_rows.winfo_children()) <= OVERVIEW_PAGE_SIZE
                region = "LesserZoneWeather"
                app.regional_weather_choice.set(weather.REGIONS[region][0])
                app.regional_weather_edit.invoke()
                key = weather.control_key(region, "Fogy", "weight")
                duration = weather.control_key(region, "Fogy", "duration")
                app._wb_edit(("sliders", key), "250")
                app._wb_edit(("sliders", duration), "150")
                expected = {region: {"Fogy": {"weight": 2.5, "duration": 1.5}}}
                assert app._collect().regional_weather_overrides == expected
                app._wb_undo()
                assert app.sliders[duration].get() == 100
                app._wb_redo()
                assert app._collect().regional_weather_overrides == expected
                profile = temp / "weather-profile.json"
                editor_state.save_profile(profile, app._ui_state(), "Regional weather")
                app._reset_all()
                assert not app._collect().regional_weather_overrides
                app._apply_ui_state(editor_state.read_profile(profile).state)
                assert app._collect().regional_weather_overrides == expected
                patches = build_patches(app.gd, app._collect())
                assert len(patches) == 1 and "WeatherSelectionPrototypes/" in next(iter(patches))
                sample("regional weather edited, restored and exported")
                app._reset_all()
                assert build_patches(app.gd, app._collect()) == {}
                sample("regional weather reset")
                report["regions_checked"] = len(app.gd.regional_weather)
                report["passed"] = True
                app.destroy()
                app = None
                return 0
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
