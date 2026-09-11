"""Optional editor views sharing the existing GUI's settings and export engine."""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from . import editor_state as state, mod_library, theme, armor_extensions, regional_weather, artifact_extensions

OVERVIEW_PAGE_SIZE = 20

TREE_TABS = {"weapon_overrides": "Weapons", "weapon_calibers": "Weapons",
             "ammo_overrides": "Ammo", "scope_overrides": "Ammo",
             "armor_overrides": "Armor", "armor_custom": "Armor", "mutant_overrides": "Mutants",
             "faction_relations": "Factions", "cats": "Weight & items"}
# Recorded user reports in the existing control descriptions, not inferred tests.
CONFIRMED = {("checks", "art_no_hop"), ("checks", "art_no_detector"),
             ("sliders", "rq_jobs")}


def ui():
    # Lazy import: gui owns the original widget classes and labels.
    from . import gui
    return gui


def value_text(value):
    if value is None:
        return "default"
    if isinstance(value, bool):
        return "On" if value else "Off"
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


class WorkbenchMixin:
    def _wb_init(self):
        self._wb_bindings = {}
        self._wb_meta = {}
        self._wb_check_tabs = {}
        self._wb_check_hints = {}
        self._wb_menu = None
        self._wb_favorites = set()
        self._wb_compact = True
        self._wb_scale = 100
        self._wb_dragging = False
        self._wb_restoring = False
        self._wb_busy = False
        self._wb_job = None
        self._wb_async_job = None
        self._wb_windows = {}
        self._wb_history = None
        self._wb_view = "My changes"
        self._wb_page = 0
        self._wb_page_filter = None
        self._wb_render_stamp = None
        self._wb_global_query = ""
        self._wb_preferences = ui().app_dir() / "editor.json"
        try:
            prefs = json.loads(self._wb_preferences.read_text(encoding="utf-8"))
            self._wb_favorites = {tuple(p) for p in prefs.get("favorites", [])
                                  if isinstance(p, list) and 2 <= len(p) <= 3
                                  and all(isinstance(k, str) for k in p)
                                  and p[0] in state.GROUPS}
            self._wb_compact = bool(prefs.get("compact", True))
            if prefs.get("scale") in (85, 100, 115, 130):
                self._wb_scale = prefs["scale"]
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        # Apply a saved non-default scale BEFORE constructing the controls.
        # Calling this at 100% after construction redraws every CTk widget.
        if self._wb_scale != 100:
            ctk.set_widget_scaling(self._wb_scale / 100)

    def _wb_save_preferences(self):
        try:
            state.write_json(self._wb_preferences, {
                "version": 1, "favorites": sorted(self._wb_favorites),
                "compact": self._wb_compact, "scale": self._wb_scale})
        except (OSError, ValueError) as exc:
            self._status_write(f"Editor preferences could not be saved: {exc}")

    def _wb_setup(self):
        self._wb_defaults = {
            "sliders": {key: row.default for key, row in self.sliders.items()},
            "checks": {key: False for key in self.checks},
            "cats": {key: True for key in self.cat_checks}}
        self._wb_history = state.History(self._wb_snapshot())
        self.bind_all("<ButtonPress-1>", self._wb_press, add="+")
        self.bind_all("<ButtonRelease-1>", self._wb_release, add="+")
        self.bind("<Control-z>", lambda e: self._wb_undo(), add="+")
        self.bind("<Control-y>", lambda e: self._wb_redo(), add="+")
        self.bind("<Control-Shift-Z>", lambda e: self._wb_redo(), add="+")
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set(), add="+")
        self._wb_build_overview()
        self.tabs.set("Overview")
        self._wb_tick()

    def _wb_snapshot(self):
        return state.clone({**self._ui_state(), "mod_name": self.name_entry.get()})

    def _wb_press(self, event=None):
        # CTk's widget binding has already moved the thumb by this point.
        # Keep the pre-gesture snapshot until release instead of splitting it.
        self._wb_dragging = True

    def _wb_release(self, event=None):
        self._wb_dragging = False
        if self._wb_history is not None:
            self.after_idle(self._wb_checkpoint)

    def _wb_checkpoint(self):
        if self._wb_history is None or self._wb_restoring or self._wb_busy:
            return
        changed = self._wb_history.commit(self._wb_snapshot())
        self._wb_update_history_buttons()
        if changed:
            self._wb_render_stamp = None

    def _wb_update_history_buttons(self):
        enabled = not self._wb_busy and self._body_enabled_state() == "normal"
        for button, stack in ((self.wb_undo_btn, self._wb_history.past),
                              (self.wb_redo_btn, self._wb_history.future)):
            button.configure(state="normal" if enabled and stack else "disabled")

    def _wb_tick(self):
        self._wb_job = None
        if not self._wb_dragging:
            self._wb_checkpoint()
        self._wb_update_counts()
        if self.tabs.get() == "Overview" and not self._wb_dragging:
            self._wb_render_overview()
        self._wb_job = self.after(600, self._wb_tick)

    def _wb_restore(self, snapshot):
        self._wb_restoring = True
        try:
            self._reset_all()
            self._apply_ui_state(state.clone(snapshot))
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, snapshot.get("mod_name", "S2Tweaker"))
            if self.gd is not None:
                # Scope rows have no refresh_all helper; rebuild those only.
                self._isc_populate()
            self._apply_filter()
        finally:
            self._wb_restoring = False
        # Conflict locks can legitimately normalize a restored state.
        self._wb_render_stamp = None
        self._wb_update_history_buttons()

    def _wb_undo(self):
        if self._wb_busy or self._body_enabled_state() != "normal":
            return "break"
        self._wb_checkpoint()
        snapshot = self._wb_history.undo()
        if snapshot is not None:
            self._wb_restore(snapshot)
            self._wb_history.current = self._wb_snapshot()
            self._status_write("Undid the last settings edit.")
        return "break"

    def _wb_redo(self):
        if self._wb_busy or self._body_enabled_state() != "normal":
            return "break"
        self._wb_checkpoint()
        snapshot = self._wb_history.redo()
        if snapshot is not None:
            self._wb_restore(snapshot)
            self._wb_history.current = self._wb_snapshot()
            self._status_write("Redid the settings edit.")
        return "break"

    def _wb_action(self, callback):
        self._wb_checkpoint()
        callback()
        self._wb_checkpoint()

    def _wb_register(self, path, row, tab=None, help_text=""):
        path = tuple(path)
        self._wb_bindings[path] = row
        label = row.label.cget("text")
        if path[0] == "sliders" and path[1].startswith("wcat_"):
            category = path[1][5:].rsplit("_", 1)[0]
            label = ui().WEAPON_CATEGORY_LABELS.get(category, category) + " · " + label
        if path[0] in state.NESTED_GROUPS:
            key = path[1]
            owner = (ui().weapon_display(key) if path[0] == "weapon_overrides" else
                     ui().ammo_label(key) if path[0] == "ammo_overrides" else
                     self._ir_labels.get(key, key) if path[0] in ("armor_overrides", "armor_custom") else key)
            label = owner + " · " + label
        self._wb_meta[path] = (label,
                              tab or TREE_TABS.get(path[0], self._current_tab), help_text)
        row.editor_help = help_text
        row.editor_path = path
        row.editor_label = row.label.cget("text")
        self._wb_mark_favorite(path, row.label, row.editor_label)
        row.label.bind("<Button-3>", lambda e: self._wb_context(e, path), add="+")
        row.entry.bind("<Button-3>", lambda e: self._wb_context(e, path), add="+")
        self._wb_density_row(row)

    def _wb_context(self, event, path):
        # One native menu shared by all rows, allocated only when requested.
        if self._wb_menu is None:
            self._wb_menu = tk.Menu(self, tearoff=False)
        menu = self._wb_menu
        menu.delete(0, "end")
        menu.add_command(label="Remove favorite" if path in self._wb_favorites else "Add favorite",
                         command=lambda: self._wb_toggle_favorite(path))
        menu.add_command(label="Details", command=lambda: self._wb_details(path))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _wb_mark_favorite(self, path, widget, label):
        widget.configure(text=("★ " if path in self._wb_favorites else "") + label)

    def _wb_density_row(self, row):
        tab = self._wb_meta.get(row.editor_path, (None, None))[1]
        row.show_hint(not self._wb_compact and self.tabs.get() == tab)
        if getattr(row, "_editor_compact", None) != self._wb_compact:
            row.row.pack_configure(pady=1 if self._wb_compact else 5)
            row._editor_compact = self._wb_compact

    def _wb_tab_changed(self):
        if not hasattr(self, "tabs"):
            return
        if self.tabs.get() != "Overview" and hasattr(self, "wb_rows"):
            for widget in self.wb_rows.winfo_children():
                widget.destroy()
            self._wb_render_stamp = None
        for row in list(self._wb_bindings.values()):
            if row.row.winfo_exists():
                self._wb_density_row(row)
        for key, data in self._wb_check_hints.items():
            parent, row, tip, hint = data
            visible = not self._wb_compact and self.tabs.get() == self._wb_check_tabs[key]
            if visible and hint is None:
                hint = ctk.CTkLabel(parent, text="      " + tip, anchor="w", justify="left",
                                    wraplength=680, font=ctk.CTkFont(size=12), text_color=ui().MUTED)
                hint.pack(fill="x", padx=12, after=row)
                data[3] = hint
            elif not visible and hint is not None:
                hint.destroy()
                data[3] = None

    def _wb_toggle_favorite(self, path):
        if path in self._wb_favorites:
            self._wb_favorites.remove(path)
        else:
            self._wb_favorites.add(path)
        row = self._wb_bindings.get(path)
        if row is not None and row.row.winfo_exists():
            self._wb_mark_favorite(path, row.label, row.editor_label)
        if path[0] == "checks" and path[1] in self.checks:
            self._wb_mark_favorite(path, self.checks[path[1]], self._wb_meta[path][0])
        self._wb_save_preferences()
        self._wb_render_stamp = None
        if self.tabs.get() == "Overview":
            self._wb_render_overview()

    def _wb_info(self, path):
        if path in self._wb_meta:
            label, tab, description = self._wb_meta[path]
            parts = regional_weather.split_key(path[1]) if path[0] == "sliders" else None
            if parts:
                region, weather, _param = parts
                gd = getattr(self, "gd", None)
                if gd is None or weather not in gd.regional_weather.get(region, {}):
                    label += " (inactive)"
                    description = ("Inactive: this weather is unavailable in the loaded game data. "
                                   "Reset to 100% to remove the saved change. " + description)
            if path[0] == "sliders" and path[1] in artifact_extensions.CONTROLS:
                gd = getattr(self, "gd", None)
                data = artifact_extensions.available(gd)
                spec = artifact_extensions.CONTROLS[path[1]]
                if path[1] not in data:
                    label += " (inactive)"
                    description = f"Inactive in this game data. Reset to {spec.default:g} to remove the saved change. " + description
                elif gd is not None:
                    source, paths = data[path[1]]
                    if spec.group == "item" and artifact_extensions.effect_family(spec.param):
                        baseline = gd.resolve(gd.effects, spec.param, "ValueMin")
                    else:
                        root = {"ItemPrototypes": gd.items, "AnomalyPrototypes": gd.anomalies,
                                "ArtifactSpawnerPrototypes": gd.artifactspawners}[source]
                        baseline = gd.resolve(root, spec.target, paths[0])
                    description = f"Loaded baseline: {baseline}. " + description
            return label, tab, description
        group, key, *param = path
        if group == "checks" and key in self.checks:
            return self.checks[key].cget("text"), self._wb_check_tabs.get(key, "Player"), ""
        if group == "cats":
            return "Weight category: " + key, "Weight & items", ""
        label = key
        if group in ("weapon_overrides", "weapon_calibers"):
            label = ui().weapon_display(key)
        elif group == "faction_relations":
            label = self._if_labels.get(key, key)
        elif group in ("armor_overrides", "armor_custom"):
            label = self._ir_labels.get(key, key)
        if param:
            spec = armor_extensions.CONTROLS.get(param[0]) if group == "armor_custom" else None
            label += " · " + (spec.label if spec else param[0].replace("_", " "))
        elif group == "weapon_calibers":
            label += " · caliber"
        return label, TREE_TABS.get(group, "Player"), ""

    def _wb_neutral(self, path):
        group, key, *param = path
        if group == "armor_custom":
            return -1
        if group in state.OVERRIDES:
            return 1.0
        if group == "faction_relations":
            return self._if_vanilla.get(key)
        if group == "weapon_calibers":
            return self._iw_caliber.get(key)
        return self._wb_defaults.get(group, {}).get(key)

    def _wb_catalog(self):
        current = state.flatten(self._ui_state())
        paths = current.keys() | self._wb_favorites
        gd = getattr(self, "gd", None)
        weather_keys = regional_weather.available_keys(gd.regional_weather) if gd else set()
        artifact_keys = artifact_extensions.available(gd)
        result = []
        for path in paths:
            default = self._wb_neutral(path)
            value = current.get(path, default)
            label, tab, description = self._wb_info(path)
            if path[0] == "sliders" and path[1].startswith(regional_weather.PREFIX):
                if path[1] not in weather_keys:
                    if state.equal(default, value) and path not in self._wb_favorites:
                        continue
            if path[0] == "sliders" and path[1] in artifact_extensions.CONTROLS and path[1] not in artifact_keys:
                if state.equal(default, value) and path not in self._wb_favorites:
                    continue
            result.append((path, label, tab, default, value, description))
        return sorted(result, key=lambda row: (row[2], row[1].casefold(), row[0]))

    def _wb_update_counts(self):
        counts = Counter(row[2] for row in self._wb_catalog() if not state.equal(row[3], row[4]))
        self.tabs.set_counts(counts)

    def _wb_build_overview(self):
        page = self.tabs.add("Overview")
        self.tabs._name_list.remove("Overview")
        self.tabs._name_list.insert(0, "Overview")
        self.tabs._relayout()
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(header, text="Your workspace", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        self.wb_overview_note = ctk.CTkLabel(header, text="", anchor="w", wraplength=680)
        self.wb_overview_note.pack(fill="x")
        modes = theme.SegmentedButton(header, values=["My changes", "Favorites", "Browse controls", "Loot & world"],
                                      command=self._wb_choose_view)
        modes.set(self._wb_view)
        self.wb_modes = modes
        modes.pack(anchor="w", pady=6)
        self.wb_search = ctk.CTkEntry(header, placeholder_text="Filter this list…")
        self.wb_search.pack(fill="x")
        self.wb_search.bind("<KeyRelease>", lambda e: self._wb_render_overview(force=True))
        paging = ctk.CTkFrame(header, fg_color="transparent")
        paging.pack(fill="x", pady=4)
        self.wb_previous = ctk.CTkButton(paging, text="Previous", width=80,
                                        command=lambda: self._wb_change_page(-1))
        self.wb_previous.pack(side="left")
        self.wb_page_label = ctk.CTkLabel(paging, text="")
        self.wb_page_label.pack(side="left", padx=10)
        self.wb_next = ctk.CTkButton(paging, text="Next", width=80,
                                    command=lambda: self._wb_change_page(1))
        self.wb_next.pack(side="left")
        self.wb_rows = ctk.CTkScrollableFrame(page, fg_color="transparent")
        self.wb_rows.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _wb_choose_view(self, value):
        self._wb_view = value
        self.wb_modes.set(value)
        self.tabs.set("Overview")
        self._wb_render_overview(force=True)

    def _wb_change_page(self, delta):
        self._wb_page = max(0, self._wb_page + delta)
        self._wb_render_overview(force=True)

    def _wb_extra_controls(self):
        self.wb_search.delete(0, "end")
        self._wb_choose_view("Loot & world")

    def _wb_regional_weather(self, label):
        if label not in {entry[0] for entry in regional_weather.REGIONS.values()}:
            return
        if getattr(self, "gd", None) is None:
            messagebox.showinfo("Regional weather", "Load the game data first to see available weather.", parent=self)
            return
        self.wb_search.delete(0, "end")
        self.wb_search.insert(0, f"Regional weather: {label} /")
        self._wb_choose_view("Loot & world")

    def _wb_build_artifact_editor(self, body):
        frame = self._section(body, "Artifact editor & related settings (experimental)")
        self.artifact_editor_note = ctk.CTkLabel(frame, text="", justify="left", anchor="w", wraplength=660)
        self.artifact_editor_note.pack(fill="x", padx=12, pady=6)
        self.artifact_editor_group = ctk.CTkOptionMenu(frame, values=list(artifact_extensions.GROUPS.values()),
                                                      width=260, command=self._wb_artifact_targets)
        self.artifact_editor_group.pack(anchor="w", padx=12, pady=4)
        self.artifact_editor_target = ctk.CTkOptionMenu(frame, values=["Load game data first"], width=360)
        self.artifact_editor_target.pack(anchor="w", padx=12, pady=4)
        self.artifact_editor_edit = ctk.CTkButton(frame, text="Edit selected settings",
                                                command=lambda: self._wb_artifact_editor(self.artifact_editor_group.get(), self.artifact_editor_target.get()))
        self.artifact_editor_edit.pack(anchor="w", padx=12, pady=6)
        self._wb_artifact_targets(self.artifact_editor_group.get())

    def _wb_artifact_targets(self, label):
        group = next((key for key, name in artifact_extensions.GROUPS.items() if name == label), None)
        gd = getattr(self, "gd", None)
        data = artifact_extensions.available(gd)
        targets = sorted({c.target for k, c in artifact_extensions.CONTROLS.items()
                          if c.group == group and (gd is None or k in data)})
        self.artifact_editor_target.configure(values=targets or ["Unavailable in this game data"])
        if self.artifact_editor_target.get() not in targets:
            self.artifact_editor_target.set(targets[0] if targets else "Unavailable in this game data")
        self.artifact_editor_note.configure(text=(
            "Rarity weights are normalized per rank. These shared profiles also affect quest placements, including E06_MQ01. Not play-tested yet."
            if group == "rarity" else
            "Choose an item or profile, then edit its available values. Inherit restores global behavior. Artifact names use their game-data identifiers. Not play-tested yet."))

    def _wb_artifact_editor(self, label, target):
        gd = getattr(self, "gd", None)
        if gd is None:
            messagebox.showinfo("Artifact editor", "Load the game data first.", parent=self)
            return
        group = next((key for key, name in artifact_extensions.GROUPS.items() if name == label), None)
        if not any(c.group == group and c.target == target and k in artifact_extensions.available(gd)
                   for k, c in artifact_extensions.CONTROLS.items()):
            self._wb_artifact_targets(label)
            return
        self.wb_search.delete(0, "end")
        self.wb_search.insert(0, f"{label} / {target} /")
        self._wb_choose_view("Loot & world")

    def _wb_sync_search(self, query):
        if not hasattr(self, "wb_search") or not (query or self._wb_global_query):
            return
        self._wb_global_query = query
        self.wb_search.delete(0, "end")
        self.wb_search.insert(0, query)
        self._wb_choose_view("Browse controls")
        if query:
            self.tabs.set("Overview")

    def _wb_render_overview(self, force=False):
        if not hasattr(self, "wb_rows") or self.tabs.get() != "Overview":
            return
        query = self.wb_search.get().casefold().strip()
        catalog = self._wb_catalog()
        rows = [r for r in catalog if
                (self._wb_view != "My changes" or not state.equal(r[3], r[4])) and
                (self._wb_view != "Favorites" or r[0] in self._wb_favorites) and
                (self._wb_view != "Loot & world" or r[0] in self._extension_paths) and
                (not query or query in (r[1] + " " + r[2] + " " + "/".join(r[0])).casefold())]
        page_filter = self._wb_view, query
        if page_filter != self._wb_page_filter:
            self._wb_page = 0
            self._wb_page_filter = page_filter
        pages = max(1, (len(rows) + OVERVIEW_PAGE_SIZE - 1) // OVERVIEW_PAGE_SIZE)
        self._wb_page = min(self._wb_page, pages - 1)
        stamp = (repr(rows), self._wb_view, query, self._body_enabled_state(), self._wb_busy,
                 tuple(sorted(self._wb_favorites)), self._wb_page)
        if not force and stamp == self._wb_render_stamp:
            return
        self._wb_render_stamp = stamp
        self.wb_page_label.configure(text=f"Page {self._wb_page + 1} / {pages} · {len(rows)} settings")
        self.wb_previous.configure(state="normal" if self._wb_page else "disabled")
        self.wb_next.configure(state="normal" if self._wb_page + 1 < pages else "disabled")
        for widget in self.wb_rows.winfo_children():
            widget.destroy()
        changed = sum(not state.equal(r[3], r[4]) for r in catalog)
        self.wb_overview_note.configure(text=f"{changed} changed settings · {len(self._wb_favorites)} favorites. "
                                        "Values here are editor settings; Preview shows the generated result.")
        if not rows:
            ctk.CTkLabel(self.wb_rows, text="No matching controls. Use Browse controls or right-click a setting's label to add a favorite.",
                         wraplength=630).pack(pady=24)
        start = self._wb_page * OVERVIEW_PAGE_SIZE
        for path, label, tab, default, value, description in rows[start:start + OVERVIEW_PAGE_SIZE]:
            card = ctk.CTkFrame(self.wb_rows)
            card.pack(fill="x", padx=4, pady=3)
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkButton(card, text="★" if path in self._wb_favorites else "☆", width=28,
                          fg_color="transparent", command=lambda p=path: self._wb_toggle_favorite(p)).grid(row=0, column=0, padx=5)
            ctk.CTkLabel(card, text=label, anchor="w", wraplength=340).grid(row=0, column=1, sticky="ew", pady=5)
            ctk.CTkLabel(card, text=tab + " · " + self._wb_status(path), text_color=theme.get(self.theme_name)["secondary"],
                         anchor="w", font=ctk.CTkFont(size=11)).grid(row=1, column=1, sticky="w", pady=(0, 5))
            entry = ctk.CTkEntry(card, width=86)
            entry.insert(0, armor_extensions.format_value(path[2], value) if path[0] == "armor_custom" else
                         "Inherit" if path[0] == "sliders" and path[1] in artifact_extensions.CONTROLS and value == -1 else value_text(value))
            entry.grid(row=0, column=2, padx=5)
            entry.bind("<Return>", lambda e, p=path, w=entry: self._wb_edit(p, w.get()))
            ctk.CTkButton(card, text="Apply", width=52, command=lambda p=path, w=entry: self._wb_edit(p, w.get()),
                          state="normal" if self._body_enabled_state() == "normal" and not self._wb_busy else "disabled").grid(row=0, column=3, padx=3)
            ctk.CTkButton(card, text="Details", width=62, command=lambda p=path: self._wb_details(p)).grid(row=0, column=4, padx=5)

    def _wb_find_row(self, path):
        if path[0] == "sliders":
            return self.sliders.get(path[1])
        row = self._wb_bindings.get(path)
        if row is not None and row.row.winfo_exists():
            return row
        group, key, *param = path
        if group in state.NESTED_GROUPS and group != "scope_overrides":
            prefix = {"weapon_overrides": "iw", "ammo_overrides": "ia",
                      "armor_overrides": "ir", "armor_custom": "ir", "mutant_overrides": "im"}[group]
            for block in getattr(self, f"_{prefix}_blocks").values():
                if key in getattr(block, "sids", getattr(block, "species", [])):
                    block.ensure_rows()
                    owner = block.rows.get(key)
                    if owner is not None:
                        owner.build()
                    break
        elif group == "faction_relations":
            for block in self._if_blocks.values():
                if key in block.sids:
                    block.ensure_rows()
                    break
        row = self._wb_bindings.get(path)
        return row if row is not None and row.row.winfo_exists() else None

    def _wb_edit(self, path, text):
        if self._wb_busy or self._body_enabled_state() != "normal":
            return
        try:
            self._wb_checkpoint()
            group, key, *param = path
            if group in ("checks", "cats"):
                if text.strip().casefold() not in ("on", "off", "true", "false", "1", "0"):
                    raise ValueError("Enter On or Off.")
                box = (self.checks if group == "checks" else self.cat_checks)[key]
                if box.cget("state") == "disabled":
                    raise ValueError("This setting is locked. Resolve its conflict in the category first.")
                enabled = text.strip().casefold() in ("on", "true", "1")
                box.select() if enabled else box.deselect()
                if group == "checks":
                    self._update_check_dot(key)
            elif group == "weapon_calibers":
                wanted = text.strip()
                if wanted not in self._iw_caliber_options:
                    raise ValueError("Choose a supported caliber in the weapon's category.")
                if wanted == self._iw_caliber.get(key):
                    self.weapon_calibers.pop(key, None)
                else:
                    self.weapon_calibers[key] = wanted
                self._iw_refresh_all()
            else:
                raw = text.strip().replace(",", ".")
                if group == "armor_custom":
                    aliases = {"inherit": -1, "default": -1}
                    if param[0] in armor_extensions.TOGGLES:
                        aliases.update({"on": 1, "off": 0})
                    value = aliases.get(raw.lower())
                    if value is None:
                        value = float(raw)
                    armor_extensions.clean({param[0]: value})
                elif group == "sliders" and key in artifact_extensions.CONTROLS:
                    spec = artifact_extensions.CONTROLS[key]
                    value = {"inherit": spec.default, "default": spec.default, "off": 0}.get(raw.lower())
                    if value is None:
                        value = float(raw)
                    value = spec.validate(value)
                    if value != spec.default and key not in artifact_extensions.available(getattr(self, "gd", None)):
                        raise ValueError(f"This control is unavailable in the loaded game data. Reset to {spec.default:g}.")
                else:
                    value = float(raw)
                if not math.isfinite(value):
                    raise ValueError("Enter a finite number.")
                weather_parts = regional_weather.split_key(key) if group == "sliders" else None
                if weather_parts and value != 100:
                    region, weather, _param = weather_parts
                    gd = getattr(self, "gd", None)
                    if gd is None or weather not in gd.regional_weather.get(region, {}):
                        raise ValueError("This weather is unavailable in the loaded game data. Reset to 100%.")
                row = self._wb_find_row(path)
                if row is None:
                    raise ValueError("Open this setting in its category to edit it.")
                if row.locked or row._base_state == "disabled":
                    raise ValueError("This setting is locked. Resolve its conflict in the category first.")
                if not row.lo <= value <= row.hi:
                    raise ValueError(f"Enter a value between {row.lo:g} and {row.hi:g}.")
                row.set(value)
            self._wb_checkpoint()
            self._wb_render_overview(force=True)
        except (ValueError, KeyError) as exc:
            messagebox.showinfo("Edit setting", str(exc), parent=self)

    def _wb_status(self, path):
        label, tab, description = self._wb_info(path)
        if path in self._extension_paths and path[0] == "sliders":
            row = self.sliders[path[1]]
            if row.locked:
                return "Locked by Avoid conflicts · see Details"
            if row.conflict_mods:
                return "Potential mod conflict · see Details"
        if path[0] == "armor_custom":
            spec = armor_extensions.CONTROLS.get(path[2])
            if spec and spec.experimental:
                return "△ Experimental"
        if "experimental" in (label + description).casefold() or path[1].startswith("field_repair_"):
            return "△ Experimental"
        if path in CONFIRMED:
            return "✓ Reported in-game"
        return "○ No recorded play-test"

    def _wb_details(self, path):
        label, tab, description = self._wb_info(path)
        text = f"{label}\n{tab}\n\n{self._wb_status(path)}\n"
        text += "Automated export checks and play-test reports are separate evidence.\n\n"
        text += description or "This setting is included only when it changes the generated result."
        group = path[0]
        if group == "weapon_overrides":
            key, param = path[1:]
            category = self._iw_categories.get(key)
            chosen = self.weapon_overrides.get(key, {}).get(param)
            cat = self._collect_weapon_cats().get(category, {}).get(param)
            text += "\n\nWeapon priority: individual weapon > weapon category > global."
            text += (f"\nThis weapon uses its individual factor: ×{chosen:g}." if chosen is not None else
                     f"\nThis weapon inherits its category factor: ×{cat:g}." if cat is not None else
                     "\nThis weapon inherits the global factor.")
            text += "\nThese three levels do not multiply together. Shared weapon settings and ammunition can still affect the final result."
        elif group == "armor_custom":
            spec = armor_extensions.CONTROLS.get(path[2])
            if spec and not description:
                text += "\n\n" + spec.help
            text += "\n\nExplicit item values take priority over protection factors and global item controls. Inherit (-1) removes this override. Difficulty and technician upgrades still apply."
        elif group in ("ammo_overrides", "armor_overrides", "mutant_overrides", "scope_overrides"):
            text += "\n\nAn individual value takes priority over the corresponding global control. Returning to ×1 removes the individual override."
        elif path[0] == "sliders" and path[1].startswith("wcat_"):
            text += "\n\nWeapon priority: individual weapon > category > global. An individual override takes priority over this category value."
        text += "\n\nEditor default: " + value_text(self._wb_neutral(path))
        buttons = [("Open category", lambda: self.tabs.set(tab)),
                   ("Toggle favorite", lambda: self._wb_toggle_favorite(path))]
        if path in self._extension_paths and path[0] == "sliders":
            row = self.sliders[path[1]]
            if path[1] in artifact_extensions.CONTROLS:
                spec = artifact_extensions.CONTROLS[path[1]]
                text += f"\nAllowed range: {spec.minimum:g}–{spec.maximum:g}; reset: {spec.default:g}. Up to {spec.decimals} decimal places."
            else:
                text += f"\nAllowed range: {row.lo:g}–{row.hi:g}. Whole percentage values."
            if row.conflict_mods:
                text += "\nConflicting mods: " + ", ".join(row.conflict_mods)
            if row.locked:
                text += "\nLocked by Avoid conflicts. Unlock explicitly to edit."
                buttons.append(("Unlock setting", lambda: self._wb_unlock_control(row)))
        self._wb_text_window(label, text, buttons=buttons)

    def _wb_unlock_control(self, row):
        if not self._wb_busy and self._body_enabled_state() == "normal":
            self._wb_action(row._unlock)

    def _wb_window(self, title, size="780x600"):
        existing = self._wb_windows.get(title)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return None
        win = ctk.CTkToplevel(self)
        win.title("S2Tweaker · " + title)
        win.geometry(size)
        win.minsize(620, 420)
        win.transient(self)
        self._wb_windows[title] = win
        return win

    def _wb_text_window(self, title, text, buttons=()):
        existing = self._wb_windows.get(title)
        if existing is not None and existing.winfo_exists() and hasattr(existing, "editor_text"):
            existing.editor_text.configure(state="normal")
            existing.editor_text.delete("1.0", "end")
            existing.editor_text.insert("1.0", text)
            existing.editor_text.configure(state="disabled")
            existing.lift()
            return
        win = self._wb_window(title)
        if win is None:
            return
        box = ctk.CTkTextbox(win, wrap="word")
        win.editor_text = box
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.insert("1.0", text)
        box.configure(state="disabled")
        footer = ctk.CTkFrame(win, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 12))
        for label, command in buttons:
            ctk.CTkButton(footer, text=label, command=command).pack(side="left", padx=4)
        ctk.CTkButton(footer, text="Close", command=win.destroy).pack(side="right")

    def _wb_options(self):
        win = self._wb_window("More options", "670x510")
        if win is None:
            return
        body = ctk.CTkScrollableFrame(win)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(body, text="Display", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=6)
        density = theme.SegmentedButton(body, values=["Compact", "Detailed"], command=self._wb_set_density)
        density.set("Compact" if self._wb_compact else "Detailed")
        density.pack(anchor="w", pady=6)
        scale = ctk.CTkOptionMenu(body, values=["85%", "100%", "115%", "130%"], command=self._wb_set_scale)
        scale.set(f"{self._wb_scale}%")
        scale.pack(anchor="w", pady=6)
        ctk.CTkLabel(body, text="More actions", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=6)
        for label, callback in (("Scan installed mods", self._start_modscan),
                                ("Open output folder", self._open_output),
                                ("Load preset file…", lambda: self._wb_action(self._load_preset)),
                                ("Save preset file…", self._save_preset),
                                ("Remove current named mod", self._remove_mod)):
            ctk.CTkButton(body, text=label, command=callback).pack(fill="x", pady=3)
        debug = ctk.CTkCheckBox(body, text="Also export patch .cfg files", command=lambda: (
            self.debug_check.select() if debug.get() else self.debug_check.deselect()))
        if self.debug_check.get():
            debug.select()
        debug.pack(anchor="w", pady=10)

    def _wb_set_density(self, value):
        self._wb_compact = value == "Compact"
        self._wb_tab_changed()
        self._wb_save_preferences()

    def _wb_set_scale(self, value):
        scale = int(value.rstrip("%"))
        if scale == self._wb_scale:
            return
        self._wb_scale = scale
        ctk.set_widget_scaling(self._wb_scale / 100)
        self._wb_save_preferences()

    def _wb_profiles(self):
        win = self._wb_window("Profiles", "850x630")
        if win is None:
            return
        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=10)
        name = ctk.CTkEntry(header, placeholder_text="Profile name")
        name.pack(fill="x", pady=3)
        description = ctk.CTkEntry(header, placeholder_text="Description (optional)")
        description.pack(fill="x", pady=3)
        listing = ctk.CTkScrollableFrame(win)
        listing.pack(fill="both", expand=True, padx=12, pady=6)
        selected = tk.StringVar(value="")
        profiles = {}

        def refresh():
            profiles.clear()
            for child in listing.winfo_children():
                child.destroy()
            ui().presets_dir().mkdir(parents=True, exist_ok=True)
            for path in sorted(ui().presets_dir().glob("*.json")):
                try:
                    profile = state.read_profile(path)
                    profiles[str(path)] = profile
                    count = len(state.differences(self._wb_defaults, profile.state, self._wb_defaults))
                    row = ctk.CTkFrame(listing)
                    row.pack(fill="x", pady=3)
                    ctk.CTkRadioButton(row, text=f"{profile.name} · {count} changes", variable=selected,
                                       value=str(path), command=lambda p=profile: fill(p)).pack(anchor="w", padx=8, pady=5)
                    ctk.CTkLabel(row, text=profile.description or path.name, anchor="w", wraplength=680).pack(fill="x", padx=8)
                except (OSError, ValueError) as exc:
                    ctk.CTkLabel(listing, text=f"Skipped {path.name}: {exc}", wraplength=680).pack(anchor="w")
            if not profiles:
                ctk.CTkLabel(listing, text="No profiles yet. Name your current settings and save them above.").pack(pady=12)

        def fill(profile):
            name.delete(0, "end")
            name.insert(0, profile.name)
            description.delete(0, "end")
            description.insert(0, profile.description)

        def save(duplicate=False):
            profile = profiles.get(selected.get())
            if duplicate and profile is None:
                return
            label = name.get().strip() or "My profile"
            if duplicate:
                label += " copy"
            path = state.unique_profile_path(ui().presets_dir(), label)
            try:
                state.save_profile(path, profile.state if duplicate else self._ui_state(), label,
                                   description.get(), profile.mod_name if duplicate else self.name_entry.get())
                refresh()
                selected.set(str(path))
                self._status_write(f"Saved profile: {path.name}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Profiles", str(exc), parent=win)

        def load():
            profile = profiles.get(selected.get())
            if profile is None or self._wb_busy:
                return
            self._wb_checkpoint()
            snapshot = {**profile.state, "mod_name": profile.mod_name or self.name_entry.get()}
            self._wb_restore(snapshot)
            self._wb_checkpoint()
            self._status_write(f"Loaded profile: {profile.name}")

        def compare():
            profile = profiles.get(selected.get())
            if profile is None:
                return
            changes = state.differences(self._ui_state(), profile.state, self._wb_defaults)
            text = "Current settings → " + profile.name + f"\n{len(changes)} differences\n\n"
            text += "\n".join(f"{self._wb_info(p)[0]}: {value_text(a)} → {value_text(b)}" for p, a, b in changes)
            self._wb_text_window("Profile comparison", text or "No differences.")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(fill="x", pady=6)
        actions.grid_columnconfigure((0, 1), weight=1)
        for index, (label, callback) in enumerate((("Save current as new", save), ("Duplicate selected", lambda: save(True)),
                                                  ("Compare with current", compare), ("Load selected", load))):
            ctk.CTkButton(actions, text=label, width=130, command=callback).grid(row=index // 2, column=index % 2,
                                                                             sticky="ew", padx=3, pady=3)
        refresh()

    def _wb_run(self, title, work, done):
        if self._wb_busy or self._scan_running or self.btn_confirm.cget("state") == "disabled":
            self._status_write("Wait for the current operation to finish.")
            return
        self._wb_checkpoint()
        self._wb_busy = True
        self._set_busy(True)
        self._set_body_state(False)
        self.btn_confirm.configure(state="disabled")
        self.btn_browse.configure(state="disabled")
        self.btn_scan.configure(state="disabled")
        self._status_write(title + "…")
        result = queue.Queue()

        def worker():
            try:
                result.put((True, work()))
            except Exception as exc:
                result.put((False, str(exc)))

        def poll():
            self._wb_async_job = None
            try:
                success, payload = result.get_nowait()
            except queue.Empty:
                self._wb_async_job = self.after(150, poll)
                return
            self._wb_busy = False
            self.btn_confirm.configure(state="normal")
            self.btn_browse.configure(state="normal")
            self._set_busy(self.gd is None)
            self._set_body_state(self.gd is not None)
            self.btn_scan.configure(state="normal" if self.gd is not None else "disabled")
            if success:
                self._status_write(title + " complete.")
                done(payload)
            else:
                self._status_write(title + " failed.")
                messagebox.showerror(title, payload, parent=self)

        threading.Thread(target=worker, daemon=True).start()
        self._wb_async_job = self.after(150, poll)

    def _wb_preview(self):
        if self.gd is None:
            self._status_write("Load game data before previewing the generated result.")
            return
        from .editor_preview import describe_output
        settings = self._collect()
        gd = self.gd
        self._wb_run("Preparing preview", lambda: describe_output(gd, settings),
                     lambda text: self._wb_text_window("Generated result preview", text))

    def _wb_mods(self):
        roots = [ui().output_dir(), ui().app_dir() / "pak_history"]
        if self.game_dir is not None:
            roots.append(ui().game.mods_dir(self.game_dir))
        self._wb_run("Reading S2Tweaker manifests", lambda: mod_library.list_own_mods(roots), self._wb_show_mods)

    def _wb_show_mods(self, result):
        win = self._wb_window("My generated mods", "900x640")
        if win is None:
            return
        mods, errors = result
        ctk.CTkLabel(win, text="Own generated Paks and retained versions", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(12, 3))
        ctk.CTkLabel(win, text="Select one to load or restore; select two to compare exact patch targets.", wraplength=780).pack()
        listing = ctk.CTkScrollableFrame(win)
        listing.pack(fill="both", expand=True, padx=12, pady=8)
        selected = {}
        for mod in mods:
            variable = tk.BooleanVar(value=False)
            selected[mod.path] = variable
            row = ctk.CTkFrame(listing)
            row.pack(fill="x", pady=3)
            ctk.CTkCheckBox(row, variable=variable, text=mod.name + " · " + str(mod.manifest.get("built", "date unknown"))).pack(anchor="w", padx=8, pady=5)
            ctk.CTkLabel(row, text=str(mod.path), wraplength=780, anchor="w", font=ctk.CTkFont(size=11)).pack(fill="x", padx=8)
        if not mods:
            ctk.CTkLabel(listing, text="No S2Tweaker manifest found in output, history or the selected game's ~mods folder.", wraplength=750).pack(pady=20)
        if errors:
            ctk.CTkLabel(listing, text=f"{len(errors)} archives could not be read; other entries are still shown.", wraplength=750).pack()
            ctk.CTkButton(listing, text="Read errors", command=lambda: self._wb_text_window("Archive read errors", "\n".join(errors))).pack()

        def chosen():
            return [path for path, variable in selected.items() if variable.get()]

        def load():
            paths = chosen()
            if len(paths) != 1:
                messagebox.showinfo("My generated mods", "Select one Pak.", parent=win)
                return
            self._wb_action(lambda: self._import_pak(paths[0]))

        def details():
            paths = chosen()
            if len(paths) != 1:
                messagebox.showinfo("My generated mods", "Select one Pak.", parent=win)
                return
            mod = next(mod for mod in mods if mod.path == paths[0])
            data = mod.manifest
            text = f"{mod.name}\n{mod.path}\nBuilt: {data.get('built', '?')}\nTool: {data.get('tool', '?')}\n\n"
            text += "\n".join(str(item) for item in data.get("active_tweaks", []))
            self._wb_text_window("Pak details", text)

        def compare():
            paths = chosen()
            if len(paths) != 2:
                messagebox.showinfo("My generated mods", "Select two Paks.", parent=win)
                return
            def show(overlaps):
                text = f"{paths[0].name}\n{paths[1].name}\n\n{len(overlaps)} shared exact targets.\n"
                text += "Shared values and different values are both listed. No overlap here is not a guarantee of compatibility: list edits, inheritance and load order need separate analysis.\n\n"
                text += "\n".join(f"{family} / {'.'.join(leaf)}\n  {a} → {b}" for (family, leaf), a, b in overlaps[:500])
                if len(overlaps) > 500:
                    text += "\nOnly the first 500 targets are shown."
                self._wb_text_window("Own Pak overlap comparison", text)
            self._wb_run("Comparing own Paks", lambda: mod_library.compare_own_mods(*paths), show)

        def restore():
            paths = chosen()
            if len(paths) != 1:
                messagebox.showinfo("Restore Pak", "Select one Pak to restore.", parent=win)
                return
            target = filedialog.asksaveasfilename(parent=win, title="Restore selected Pak to…",
                initialdir=ui().output_dir(), initialfile=paths[0].name, defaultextension=".pak",
                filetypes=[("Pak mod", "*.pak")])
            if target:
                self._wb_run("Restoring Pak", lambda: mod_library.restore_pak(paths[0], target, ui().app_dir() / "pak_history"),
                             lambda backup: self._status_write("Pak restored. Previous destination retained in pak_history." if backup else "Pak restored."))

        actions = ctk.CTkFrame(win, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=10)
        for label, callback in (("Details", details), ("Load settings", load), ("Compare two", compare), ("Restore copy…", restore)):
            ctk.CTkButton(actions, text=label, width=110, command=callback).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Refresh", width=90, command=lambda: (win.destroy(), self._wb_mods())).pack(side="right")

    def _wb_close(self):
        for name in ("_wb_job", "_wb_async_job"):
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, name, None)
