"""Scrollable build summaries with a confirmation button outside the report."""
from __future__ import annotations

import sys

import customtkinter as ctk


def _work_area(parent):
    """Return the parent's monitor work area in pixels, excluding the taskbar."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
            user32.GetMonitorInfoW.restype = wintypes.BOOL
            monitor = user32.MonitorFromWindow(parent.winfo_id(), 2)
            info = MonitorInfo(cbSize=ctypes.sizeof(MonitorInfo))
            if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                rect = info.rcWork
                return rect.left, rect.top, rect.right, rect.bottom
        except (OSError, AttributeError):
            pass
    return 0, 0, parent.winfo_screenwidth(), parent.winfo_screenheight()


class BuildResultDialog(ctk.CTkToplevel):
    """Keep arbitrarily long build details inside a resizable, bounded window."""

    def __init__(self, parent, title: str, report: str):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.report = ctk.CTkTextbox(self, wrap="word")
        self.report.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        self.report.insert("1.0", report)
        self.report.configure(state="disabled")
        self.confirm = ctk.CTkButton(self, text="OK", width=110, command=self.destroy)
        self.confirm.grid(row=1, column=0, sticky="e", padx=16, pady=(0, 16))
        for key in ("<Return>", "<KP_Enter>", "<Escape>"):
            self.bind(key, self._dismiss)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._fit(parent)
        # CTk updates its Windows title bar and monitor DPI after opening.
        self._settle_id = self.after(300, lambda: self._settle(parent))

    def _fit(self, parent):
        left, top, right, bottom = _work_area(parent)
        scale = self._get_window_scaling()
        # Reserve space for the window frame, title bar and monitor edges.
        available_width = max(1, int((right - left - 48 * scale) / scale))
        available_height = max(1, int((bottom - top - 80 * scale) / scale))
        width, height = min(820, available_width), min(620, available_height)
        self.minsize(min(420, width), min(260, height))
        self.maxsize(available_width, available_height)
        pixel_width, pixel_height = round(width * scale), round(height * scale)
        x = max(left + 16, min(parent.winfo_rootx() + (parent.winfo_width() - pixel_width) // 2,
                              right - pixel_width - 16))
        y = max(top + 16, min(parent.winfo_rooty() + (parent.winfo_height() - pixel_height) // 2,
                             bottom - pixel_height - round(64 * scale)))
        # CTk scales dimensions but keeps position coordinates in screen pixels.
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _settle(self, parent):
        self._settle_id = None
        self._fit(parent)
        self.focus_set()

    def _dismiss(self, event=None):
        self.destroy()
        return "break"

    def destroy(self):
        if getattr(self, "_settle_id", None) is not None:
            self.after_cancel(self._settle_id)
            self._settle_id = None
        super().destroy()


def show_build_result(parent, title: str, report: str) -> None:
    """Wait for acknowledgement, preserving the build action's modal behavior."""
    dialog = BuildResultDialog(parent, title, report)
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    dialog.wait_window()
