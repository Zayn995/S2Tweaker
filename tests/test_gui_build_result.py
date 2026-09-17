"""Check long build reports in real windows; run separately from headless CI."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from s2tweaker import build_result


def flush(app):
    app.after(450, app.quit)
    app.mainloop()
    app.update()


def check_layout(dialog, area):
    left, top, right, bottom = area
    x, y = dialog.winfo_rootx(), dialog.winfo_rooty()
    assert left <= x and top <= y
    assert x + dialog.winfo_width() <= right
    assert y + dialog.winfo_height() <= bottom
    button = dialog.confirm
    assert button.winfo_ismapped()
    assert button.winfo_rooty() >= dialog.report.winfo_rooty() + dialog.report.winfo_height()
    assert button.winfo_rooty() + button.winfo_height() <= y + dialog.winfo_height()


app = ctk.CTk()
app.geometry("540x320+80+80")
app.update()
report = ("Mod pak created:\nC:/" + "long-folder/" * 45 + "example.pak\n\n"
          "Matching animation / sound companion:\nexample_AnimationSync.zip\n"
          "Debug: 120 generated files\n\nActive tweaks:\n"
          + "\n".join(f"Setting {i}: changed value — complete details" for i in range(350)))
try:
    actual = build_result._work_area(app)
    area = (actual[0], actual[1], min(actual[2], actual[0] + 800),
            min(actual[3], actual[1] + 600))
    for scaling in (1, 1.5):
        ctk.set_window_scaling(scaling)
        ctk.set_widget_scaling(scaling)
        with patch.object(build_result, "_work_area", return_value=area):
            dialog = build_result.BuildResultDialog(app, "Build report layout check", report)
            flush(app)
            check_layout(dialog, area)
            assert dialog.report.get("1.0", "end-1c") == report
            dialog.report.insert("end", "must remain read-only")
            assert dialog.report.get("1.0", "end-1c") == report
            assert dialog.report.yview()[1] < 1
            dialog.report.see("end")
            app.update()
            assert dialog.report.yview()[1] == 1
            check_layout(dialog, area)
            dialog.geometry("420x260")
            app.update()
            check_layout(dialog, area)
            dialog.confirm.invoke()
            assert not dialog.winfo_exists()

    ctk.set_window_scaling(1)
    ctk.set_widget_scaling(1)
    for key in ("<Return>", "<Escape>"):
        failures = []

        def acknowledge():
            dialog = next(w for w in app.winfo_children()
                          if isinstance(w, build_result.BuildResultDialog))
            try:
                assert dialog.grab_current() == dialog
                dialog.event_generate(key)
                assert not dialog.winfo_exists()
            except BaseException as exc:
                failures.append(exc)
                dialog.destroy()

        app.after(650, acknowledge)
        build_result.show_build_result(app, "Build report keyboard check", report)
        assert not failures, failures
        assert app.grab_current() is None
    print("Build report GUI: 350 changes, long path, 800x600 work area, 100/150% scaling, "
          "minimum resize, complete read-only text, scrolling, visible OK and modal Enter/Escape passed.")
finally:
    app.destroy()
