"""Check per-weapon caliber conversion using real installed game data.

Derive choices from weapon setups and damage implications from ammunition.
This local suite requires vanilla data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker.gamedata import GameData
from s2tweaker import tweaks as T

VANILLA = ROOT / "vanilla" / "Stalker2/Content/GameLite/GameData"
if not VANILLA.is_dir():
    print("vanilla/ missing - test skipped")
    raise SystemExit(0)
gd = GameData(VANILLA)

# --- 1) Verify the source data ---
assert gd.weapon_caliber("GunAK74_ST") == "A545"
slots = gd.weapon_ammo_slots("GunAK74_ST")
assert slots == {"[0]": "Default", "[1]": "ArmorPiercing",
                 "[2]": "Expanding"}, slots

# Read ammunition types from each index; some rifles use Supersonic at [0].
svd = gd.weapon_ammo_slots("GunSVDM_SP")
assert svd.get("[0]") == "Supersonic", svd
assert "Default" not in svd.values(), svd

# Verify each weapon declares its caliber instead of inheriting it from siblings.
eigene = sum(1 for n in gd.weapongeneral.children.values()
             if "AmmoCaliber" in n.values)
gesamt = len(gd.weapongeneral.children)
assert eigene == gesamt, f"{eigene} of {gesamt} structs with their own caliber"
for tmpl in ("TemplateRifle", "TemplatePistol"):
    if tmpl in gd.weapongeneral.children:
        assert gd.weapon_caliber(tmpl) is None, tmpl
print(f"Daten: {gesamt} structs, all with their own caliber  OK")

# Choices must be derived from weapon data.
angebot = T.swappable_calibers(gd)
assert "A545" in angebot and "A556" in angebot and "A012" in angebot
# The checked unused caliber must be absent because no weapon references it.
assert "A762" not in angebot, "7.62x39 is available - incorrect table extraction"
for caliber, tabelle in angebot.items():
    assert tabelle, caliber
    assert all(v.startswith("P") for v in tabelle.values()), (caliber, tabelle)
assert angebot["A012"]["Default"] == "P012"
assert angebot["A012"]["ArmorPiercing"] == "P012F"   # Shotgun slug
print(f"Angebot: {len(angebot)} calibers, all with projectiles  OK")

# Vanilla choices must emit no patch.
s = T.Settings()
s.weapon_calibers = {"GunAK74_ST": "A545"}
patches, _dlc = T._weapon_general_patch(gd, s)
assert "GunAK74_ST" not in patches, "Vanilla caliber produces a patch"

# Discard unsupported caliber choices.
s.weapon_calibers = {"GunAK74_ST": "A999"}
patches, _dlc = T._weapon_general_patch(gd, s)
assert "GunAK74_ST" not in patches
print("Vanilla and invalid values produce no patch  OK")

# --- 4) The generated patch ---
s = T.Settings()
s.weapon_calibers = {"GunAK74_ST": "A556"}
patches, _dlc = T._weapon_general_patch(gd, s)
node = patches["GunAK74_ST"]
assert node["AmmoCaliber"] == "EAmmoCaliber::A556"
block = node["AmmoTypeProjectiles"]
# Keep exactly the existing slot count; array resizing is not a verified assumption.
assert set(block) == set(slots), (set(block), set(slots))
for index, sorte in slots.items():
    assert block[index]["AmmoType"] == f"EAmmoType::{sorte}"
    assert block[index]["ProjectilePrototypeSID"] == "P556"

# Resolve types from data, never from index position.
s.weapon_calibers = {"GunSVDM_SP": "A762NATO"}
patches, _dlc = T._weapon_general_patch(gd, s)
svd_block = patches["GunSVDM_SP"]["AmmoTypeProjectiles"]
assert svd_block["[0]"]["AmmoType"] == "EAmmoType::Supersonic"

# Fall back to the target caliber's Default projectile for unsupported types.
s.weapon_calibers = {"GunAK74_ST": "A918"}
patches, _dlc = T._weapon_general_patch(gd, s)
exp = patches["GunAK74_ST"]["AmmoTypeProjectiles"]["[2]"]
assert exp["AmmoType"] == "EAmmoType::Expanding"
assert exp["ProjectilePrototypeSID"] == angebot["A918"]["Default"], exp
print("Patch: slot count, types and fallback are correct  OK")

# Allow supported caliber combinations while explaining their consequences.
s.weapon_calibers = {"GunTOZ_SG": "A545", "GunAK74_ST": "A012"}
patches, _dlc = T._weapon_general_patch(gd, s)
assert "GunTOZ_SG" in patches, "Shotgun caliber can no longer be changed"
assert "GunAK74_ST" in patches, "Rifle cannot be set to shotgun ammunition"

mods = gd.caliber_damage_mods()
assert mods["A545"] == 1.0 and mods["A556"] == 1.0
assert mods["A012"] < 0.2, mods["A012"]      # Calculated per pellet.

assert T.caliber_warning(gd, "A545", "A556") == "", "Unexpected warning"
assert T.caliber_warning(gd, "A545", "A545") == ""
runter = T.caliber_warning(gd, "A545", "A012")
hoch = T.caliber_warning(gd, "A012", "A545")
assert "%" in runter and "Warning" in runter, runter
assert "x its current damage" in hoch, hoch
# Check ratio direction: conversion to buckshot reduces the per-projectile multiplier.
assert "8 %" in runter, runter
assert "12x" in hoch, hoch
assert "gauss" in T.caliber_warning(gd, "A545", "AGA").lower()
print("No blocked choices; warnings match conversion direction  OK")

# NPC-sharing warnings must use actual linked-item counts.
assert gd.weapon_caliber_users("GunAK74_ST") == 3   # Player, Korshunov, guard.
assert gd.weapon_caliber_users("GunTOZ_SG") == 4
print("Shared weapon setups counted  OK")

# --- 7) End to end: generated patch file ---
s = T.Settings()
s.weapon_calibers = {"GunAK74_ST": "A556"}
dateien = T.build_patches(gd, s)
ziel = [n for n in dateien if "WeaponGeneralSetup" in n]
assert ziel, "No WeaponGeneralSetup patch file was built"
inhalt = dateien[ziel[0]]
assert "AmmoCaliber = EAmmoCaliber::A556" in inhalt
assert "ProjectilePrototypeSID = P556" in inhalt
assert inhalt.count("{bpatch}") >= 5      # Struct + list + 3 slots.
zeilen = T.summarize(s)
assert any("ammunition ->" in z for z in zeilen), zeilen
print("End to end: patch file and summary  OK")

print("\nCALIBER TEST PASSED")

# Check preset roundtrips when a GUI environment is explicitly available.
import json
try:
    from s2tweaker import gui
    gui.SETTINGS_FILE = ROOT / "tests" / "_tmp" / "kaliber_wegwerf.json"
    gui.SETTINGS_FILE.parent.mkdir(exist_ok=True)
    gui.SETTINGS_FILE.unlink(missing_ok=True)
    app = gui.App()
except Exception as exc:                       # pragma: no cover
    print(f"GUI unavailable ({exc}) - preset section skipped")
else:
    try:
        app.gd = gd
        app._iw_populate()
        app.update()
        assert app._iw_caliber.get("GunAK74_ST") == "A545"
        assert app._iw_setup_users.get("GunAK74_ST") == 3

        app.weapon_calibers["GunAK74_ST"] = "A556"
        # Roundtrip through JSON to avoid comparing a live state object with itself.
        zustand = json.loads(json.dumps(app._ui_state()))
        assert zustand["weapon_calibers"] == {"GunAK74_ST": "A556"}, zustand
        app.weapon_calibers.clear()
        app._apply_ui_state(zustand)
        assert app.weapon_calibers == {"GunAK74_ST": "A556"}

        # Remove default, unknown-weapon and unknown-caliber entries from imported presets.
        app.weapon_calibers.clear()
        app._apply_ui_state({"weapon_calibers": {
            "GunAK74_ST": "A545", "GibtsNicht": "A556", "GunPM_HG": "A999"}})
        assert app.weapon_calibers == {}, app.weapon_calibers

        # Check dropdown labeling, state updates and reset.
        zeile = next(b.rows["GunAK74_ST"] for b in app._iw_blocks.values()
                     if (b.ensure_rows() or "GunAK74_ST" in b.rows))
        zeile.toggle()
        app.update()
        assert zeile.cal_menu is not None, "Caliber dropdown missing"
        assert zeile._cal_labels[0].startswith("vanilla ("), zeile._cal_labels[0]
        zeile._caliber_changed(T.caliber_label("A012"))
        app.update()
        assert app.weapon_calibers == {"GunAK74_ST": "A012"}
        assert "Warning" in zeile.cal_warn.cget("text"), "Warning missing"
        assert "12 gauge" in zeile.btn.cget("text"), zeile.btn.cget("text")
        zeile._caliber_changed(T.caliber_label("A556"))
        app.update()
        assert zeile.cal_warn.cget("text").strip() == "", "Unexpected warning"
        zeile.reset()
        app.update()
        assert app.weapon_calibers == {}
        assert zeile.cal_menu.get().startswith("vanilla (")
        print("GUI: dropdown, warning, preset and reset  OK")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

print("\nCALIBER TEST PASSED")
