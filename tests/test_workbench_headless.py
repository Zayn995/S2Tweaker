"""Exercise editor transactions with in-memory controls, never a Tk window."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from s2tweaker.editor_state import History, clone
from s2tweaker.workbench_ui import WorkbenchMixin


class NameField:
    def __init__(self):
        self.value = "OwnMod"
    def get(self):
        return self.value
    def delete(self, *args):
        self.value = ""
    def insert(self, where, value):
        self.value = value


class EditorHarness(WorkbenchMixin):
    def __init__(self):
        self.values = {"sliders": {"hp": 100}, "weapon_overrides": {}}
        self.name_entry = NameField()
        self.gd = None
        self._wb_busy = self._wb_restoring = self._wb_dragging = False
        self._wb_history = History(self._wb_snapshot())
        self.notes = []
    def _ui_state(self):
        return self.values
    def _reset_all(self):
        self.values = {"sliders": {"hp": 100}, "weapon_overrides": {}}
    def _apply_ui_state(self, data):
        self.values = {key: clone(value) for key, value in data.items() if key != "mod_name"}
    def _body_enabled_state(self):
        return "normal"
    def _wb_update_history_buttons(self):
        pass
    def _apply_filter(self):
        pass
    def _status_write(self, text):
        self.notes.append(text)
    def after_idle(self, callback):
        callback()


class TransactionTests(unittest.TestCase):
    def test_drag_is_one_edit_even_after_initial_thumb_jump(self):
        editor = EditorHarness()
        editor.values["sliders"]["hp"] = 120
        editor._wb_press()
        editor.values["sliders"]["hp"] = 180
        editor.values["sliders"]["hp"] = 300
        editor._wb_release()
        self.assertEqual(len(editor._wb_history.past), 1)
        editor._wb_undo()
        self.assertEqual(editor.values["sliders"]["hp"], 100)
        editor._wb_redo()
        self.assertEqual(editor.values["sliders"]["hp"], 300)

    def test_profile_load_is_one_undoable_complete_replacement(self):
        editor = EditorHarness()
        editor.values["sliders"]["hp"] = 200
        editor.values["weapon_overrides"] = {"Gun": {"damage": 3}}
        editor._wb_checkpoint()
        editor._wb_restore({"sliders": {"hp": 400}, "weapon_overrides": {}, "mod_name": "Loaded"})
        editor._wb_checkpoint()
        editor._wb_undo()
        self.assertEqual(editor.values["weapon_overrides"], {"Gun": {"damage": 3}})
        self.assertEqual(editor.values["sliders"]["hp"], 200)
        self.assertEqual(editor.name_entry.get(), "OwnMod")
        editor._wb_redo()
        self.assertEqual(editor.values["weapon_overrides"], {})
        self.assertEqual(editor.name_entry.get(), "Loaded")

    def test_reset_can_be_undone_and_busy_blocks_undo(self):
        editor = EditorHarness()
        editor.values["sliders"]["hp"] = 600
        editor._wb_action(editor._reset_all)
        editor._wb_busy = True
        editor._wb_undo()
        self.assertEqual(editor.values["sliders"]["hp"], 100)
        editor._wb_busy = False
        editor._wb_undo()
        self.assertEqual(editor.values["sliders"]["hp"], 600)


if __name__ == "__main__":
    unittest.main()
