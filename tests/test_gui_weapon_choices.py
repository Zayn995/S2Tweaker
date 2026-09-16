"""One isolated GUI check: lazy rows, persistence, collection and reset."""
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import gui
from s2tweaker.gamedata import GameData

with tempfile.TemporaryDirectory(prefix="s2t_weapon_choices_") as temporary:
    gui.app_dir = lambda: Path(temporary)
    gui.SETTINGS_FILE = Path(temporary) / "settings.json"
    app = gui.App()
    app.withdraw()
    try:
        app.gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
        app._iw_populate()
        app.weapon_fire_modes = {"GunAK74_ST": "Queue"}
        app.weapon_ammo_types = {"GunAK74_ST": "ArmorPiercing"}
        category = app._iw_blocks[app._iw_categories["GunAK74_ST"]]
        category.ensure_rows()
        row = category.rows["GunAK74_ST"]
        row.build()
        assert app.weapon_fire_modes == {"GunAK74_ST": "Queue"}, "Lazy construction erased choices"
        assert row.choice_menus["weapon_fire_modes"].get() == "Burst"
        assert row.choice_menus["weapon_ammo_types"].get() == "Armor-piercing"
        collected = app._collect()
        assert collected.weapon_fire_modes == app.weapon_fire_modes
        assert collected.weapon_ammo_types == app.weapon_ammo_types
        snapshot = json.loads(json.dumps(app._ui_state()))
        app._iw_clear_all()
        assert not app.weapon_fire_modes and not app.weapon_ammo_types
        app._apply_ui_state(snapshot)
        assert app.weapon_fire_modes == {"GunAK74_ST": "Queue"}
        assert app.weapon_ammo_types == {"GunAK74_ST": "ArmorPiercing"}
        row._choice_changed("weapon_ammo_types", "Expanding")
        assert app.weapon_ammo_types == {"GunAK74_ST": "Expanding"}
        row._caliber_changed(gui.caliber_label("A918"))
        assert not app.weapon_ammo_types, "Unavailable expanding round survived caliber change"
        assert "Expanding" not in row.choice_menus["weapon_ammo_types"].cget("values")
        row.set_state("disabled")
        assert all(menu.cget("state") == "disabled" for menu in row.choice_menus.values())
        row.set_state("normal")
        row.reset()
        assert not app.weapon_fire_modes and not app.weapon_ammo_types and not app.weapon_calibers
        assert row.choice_menus["weapon_fire_modes"].get().startswith("Vanilla")
        assert not app._collect().weapon_fire_modes
        print("GUI weapon choices: lazy build, menus, preset, collection, caliber cleanup, locks and reset passed.")
    finally:
        app.destroy()
