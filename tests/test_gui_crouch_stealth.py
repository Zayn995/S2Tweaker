"""Isolated GUI check for stealth migration, collection, export and reset."""
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import editor_state, gui, modscan
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches

with tempfile.TemporaryDirectory(prefix="s2t_crouch_stealth_") as temporary:
    gui.app_dir = lambda: Path(temporary)
    gui.SETTINGS_FILE = Path(temporary) / "settings.json"
    gui.SETTINGS_FILE.write_text(json.dumps({"sliders": {"stealth_crouch": 235}}))
    app = gui.App()
    app.withdraw()
    try:
        gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        app.gd = gd
        keys = ("stealth_crouch_sight", "stealth_crouch_sound")
        assert "stealth_crouch" not in app.sliders
        assert all(app.sliders[key].get() == 235 for key in keys)
        assert build_patches(gd, app._collect()) == build_patches(gd, Settings(crouch_stealth_factor=2.35))
        app.sliders[keys[1]].set(100)
        collected = app._collect()
        assert collected.crouch_visibility_factor == 2.35 and collected.crouch_noise_factor == 1
        assert collected.crouch_stealth_factor == 1
        assert all("Noise" not in leaf for _, leaf in modscan.pairs_from_patches(build_patches(gd, collected)))
        state = editor_state.state_only(app._ui_state())
        assert "stealth_crouch" not in state["sliders"]
        for key in keys:
            app.sliders[key].reset()
        assert not build_patches(gd, app._collect())
        app._apply_ui_state(state)
        assert app.sliders[keys[0]].get() == 235 and app.sliders[keys[1]].get() == 100
        footprints = []
        for key in keys:
            pairs = set()
            for probe in gui.footprint_settings(key):
                pairs |= modscan.pairs_from_patches(build_patches(gd, probe))
            footprints.append(pairs)
        assert all(footprints) and not footprints[0] & footprints[1]
        print("GUI stealth: startup migration, independent controls, export, restore, reset and conflict footprints passed.")
    finally:
        app.destroy()
