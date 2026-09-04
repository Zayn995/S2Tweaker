"""Kaliberwechsel je Waffe (GitHub Issue #6, Wunsch von Molkerr).

Prueft gegen die ECHTEN Spieldaten, nicht gegen Erwartungswerte im Code:
die Kaliber-Tabelle wird aus WeaponGeneralSetupPrototypes erhoben, die
Schadensfolge aus den Munitions-Items gerechnet.

Braucht vanilla/ (wie die anderen Datentests) und laeuft deshalb lokal,
nicht in der CI.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker.gamedata import GameData
from s2tweaker import tweaks as T

VANILLA = ROOT / "vanilla" / "Stalker2/Content/GameLite/GameData"
if not VANILLA.is_dir():
    print("vanilla/ fehlt - Test uebersprungen")
    raise SystemExit(0)
gd = GameData(VANILLA)

# --- 1) Die Daten sagen, was sie sagen sollen ---------------------------
assert gd.weapon_caliber("GunAK74_ST") == "A545"
slots = gd.weapon_ammo_slots("GunAK74_ST")
assert slots == {"[0]": "Default", "[1]": "ArmorPiercing",
                 "[2]": "Expanding"}, slots

# Die Indizes sagen NICHTS ueber die Sorte: sechs Scharfschuetzengewehre
# haben auf [0] Supersonic. Wer aus der Position auf die Sorte schliesst,
# baut genau hier einen falschen Patch.
svd = gd.weapon_ammo_slots("GunSVDM_SP")
assert svd.get("[0]") == "Supersonic", svd
assert "Default" not in svd.values(), svd

# Vererbung: jede Waffe deklariert ihr Kaliber selbst, Templates stehen auf
# None. Waere das nicht so, traefe ein Patch auf eine Waffe ihre Geschwister.
eigene = sum(1 for n in gd.weapongeneral.children.values()
             if "AmmoCaliber" in n.values)
gesamt = len(gd.weapongeneral.children)
assert eigene == gesamt, f"{eigene} von {gesamt} Structs mit eigenem Kaliber"
for tmpl in ("TemplateRifle", "TemplatePistol"):
    if tmpl in gd.weapongeneral.children:
        assert gd.weapon_caliber(tmpl) is None, tmpl
print(f"Daten: {gesamt} Structs, alle mit eigenem Kaliber  OK")

# --- 2) Auswahlliste kommt aus den Daten, nicht aus einer Liste im Code --
angebot = T.swappable_calibers(gd)
assert "A545" in angebot and "A556" in angebot and "A012" in angebot
# 7,62x39 existiert als Munition, aber KEINE Waffe benutzt es und es liegt
# in null Loot-Generatoren - eine darauf umgestellte Waffe waere
# unversorgbar. Es darf nur deshalb fehlen, weil die Tabelle aus den
# WAFFENdaten kommt; taucht es auf, ist die Erhebung kaputt.
assert "A762" not in angebot, "7,62x39 ist im Angebot - Tabelle falsch erhoben"
for caliber, tabelle in angebot.items():
    assert tabelle, caliber
    assert all(v.startswith("P") for v in tabelle.values()), (caliber, tabelle)
assert angebot["A012"]["Default"] == "P012"
assert angebot["A012"]["ArmorPiercing"] == "P012F"   # Flintenlaufgeschoss
print(f"Angebot: {len(angebot)} Kaliber, alle mit Projektil  OK")

# --- 3) Vanilla = kein Patch (eiserne Projektregel) ---------------------
s = T.Settings()
s.weapon_calibers = {"GunAK74_ST": "A545"}
patches, _dlc = T._weapon_general_patch(gd, s)
assert "GunAK74_ST" not in patches, "Vanilla-Kaliber erzeugt einen Patch"

# Unbekanntes Kaliber wird still verworfen, statt Unsinn zu schreiben
s.weapon_calibers = {"GunAK74_ST": "A999"}
patches, _dlc = T._weapon_general_patch(gd, s)
assert "GunAK74_ST" not in patches
print("Vanilla und Unsinn erzeugen keinen Patch  OK")

# --- 4) Der Patch selbst -------------------------------------------------
s = T.Settings()
s.weapon_calibers = {"GunAK74_ST": "A556"}
patches, _dlc = T._weapon_general_patch(gd, s)
node = patches["GunAK74_ST"]
assert node["AmmoCaliber"] == "EAmmoCaliber::A556"
block = node["AmmoTypeProjectiles"]
# Genau so viele Slots wie vorher: es wird keiner angelegt und keiner
# entfernt. Ob {bpatch} ein Array verlaengern kann, ist nie im Spiel
# geprueft worden - der Patch darf sich nicht darauf verlassen.
assert set(block) == set(slots), (set(block), set(slots))
for index, sorte in slots.items():
    assert block[index]["AmmoType"] == f"EAmmoType::{sorte}"
    assert block[index]["ProjectilePrototypeSID"] == "P556"

# Sorte wird pro Index gelesen, nie aus der Position geschlossen
s.weapon_calibers = {"GunSVDM_SP": "A762NATO"}
patches, _dlc = T._weapon_general_patch(gd, s)
svd_block = patches["GunSVDM_SP"]["AmmoTypeProjectiles"]
assert svd_block["[0]"]["AmmoType"] == "EAmmoType::Supersonic"

# Sorte, die das Zielkaliber nicht kennt, faellt auf dessen Default zurueck
# statt ins Leere zu zeigen: 9x18 hat kein Expanding, die AK-74 schon.
s.weapon_calibers = {"GunAK74_ST": "A918"}
patches, _dlc = T._weapon_general_patch(gd, s)
exp = patches["GunAK74_ST"]["AmmoTypeProjectiles"]["[2]"]
assert exp["AmmoType"] == "EAmmoType::Expanding"
assert exp["ProjectilePrototypeSID"] == angebot["A918"]["Default"], exp
print("Patch: Slot-Zahl, Sorten und Rueckfall stimmen  OK")

# --- 5) Es wird NICHTS gesperrt, aber alles benannt ---------------------
# Ausdrueckliche Ansage des Besitzers: auch kaputte Kombinationen sind
# erlaubt, es muss nur drangeschrieben stehen.
s.weapon_calibers = {"GunTOZ_SG": "A545", "GunAK74_ST": "A012"}
patches, _dlc = T._weapon_general_patch(gd, s)
assert "GunTOZ_SG" in patches, "Flinte laesst sich nicht mehr umstellen"
assert "GunAK74_ST" in patches, "Gewehr laesst sich nicht auf Schrot stellen"

mods = gd.caliber_damage_mods()
assert mods["A545"] == 1.0 and mods["A556"] == 1.0
assert mods["A012"] < 0.2, mods["A012"]      # je Schrotkugel gerechnet

assert T.caliber_warning(gd, "A545", "A556") == "", "Warnung ohne Anlass"
assert T.caliber_warning(gd, "A545", "A545") == ""
runter = T.caliber_warning(gd, "A545", "A012")
hoch = T.caliber_warning(gd, "A012", "A545")
assert "%" in runter and "Warning" in runter, runter
assert "x its current damage" in hoch, hoch
# Richtung nicht verwechseln: ZU Schrot wird schwaecher, WEG davon staerker
assert "8 %" in runter, runter
assert "12x" in hoch, hoch
assert "gauss" in T.caliber_warning(gd, "A545", "AGA").lower()
print("Nichts gesperrt, Warnungen mit der richtigen Richtung  OK")

# --- 6) Der Hinweis auf NPC-Waffen beruht auf echten Zahlen -------------
assert gd.weapon_caliber_users("GunAK74_ST") == 3   # Spieler, Korshunov, Wache
assert gd.weapon_caliber_users("GunTOZ_SG") == 4
print("Geteilte Waffen-Setups gezaehlt  OK")

# --- 7) Ende zu Ende: fertige Patch-Datei -------------------------------
s = T.Settings()
s.weapon_calibers = {"GunAK74_ST": "A556"}
dateien = T.build_patches(gd, s)
ziel = [n for n in dateien if "WeaponGeneralSetup" in n]
assert ziel, "keine WeaponGeneralSetup-Patchdatei gebaut"
inhalt = dateien[ziel[0]]
assert "AmmoCaliber = EAmmoCaliber::A556" in inhalt
assert "ProjectilePrototypeSID = P556" in inhalt
assert inhalt.count("{bpatch}") >= 5      # Struct + Liste + 3 Slots
zeilen = T.summarize(s)
assert any("ammunition ->" in z for z in zeilen), zeilen
print("Ende zu Ende: Patchdatei und Zusammenfassung  OK")

print("\nKALIBER-TEST OK")

# --- 8) Presets: speichern, laden, und Unsinn verwerfen -----------------
# Nur wenn eine GUI moeglich ist (kopfloser Rechner: ueberspringen).
import json
try:
    from s2tweaker import gui
    gui.SETTINGS_FILE = ROOT / "tests" / "_tmp" / "kaliber_wegwerf.json"
    gui.SETTINGS_FILE.parent.mkdir(exist_ok=True)
    gui.SETTINGS_FILE.unlink(missing_ok=True)
    app = gui.App()
except Exception as exc:                       # pragma: no cover
    print(f"GUI nicht verfuegbar ({exc}) - Presetteil uebersprungen")
else:
    try:
        app.gd = gd
        app._iw_populate()
        app.update()
        assert app._iw_caliber.get("GunAK74_ST") == "A545"
        assert app._iw_setup_users.get("GunAK74_ST") == 3

        app.weapon_calibers["GunAK74_ST"] = "A556"
        # Durch JSON, wie beim echten Speichern: _ui_state() gibt die
        # LEBENDE Referenz zurueck, ein Test ohne Kopie prueft sich selbst.
        zustand = json.loads(json.dumps(app._ui_state()))
        assert zustand["weapon_calibers"] == {"GunAK74_ST": "A556"}, zustand
        app.weapon_calibers.clear()
        app._apply_ui_state(zustand)
        assert app.weapon_calibers == {"GunAK74_ST": "A556"}

        # Preset von einer anderen Installation: Vanilla-Wahl, unbekannte
        # Waffe und unbekanntes Kaliber muessen alle drei rausfliegen,
        # sonst zaehlt die Waffenzeile eine Aenderung, die nie patcht.
        app.weapon_calibers.clear()
        app._apply_ui_state({"weapon_calibers": {
            "GunAK74_ST": "A545", "GibtsNicht": "A556", "GunPM_HG": "A999"}})
        assert app.weapon_calibers == {}, app.weapon_calibers

        # Dropdown selbst: da, beschriftet, schreibt zurueck, Reset raeumt auf
        zeile = next(b.rows["GunAK74_ST"] for b in app._iw_blocks.values()
                     if (b.ensure_rows() or "GunAK74_ST" in b.rows))
        zeile.toggle()
        app.update()
        assert zeile.cal_menu is not None, "Kaliber-Dropdown fehlt"
        assert zeile._cal_labels[0].startswith("vanilla ("), zeile._cal_labels[0]
        zeile._caliber_changed(T.caliber_label("A012"))
        app.update()
        assert app.weapon_calibers == {"GunAK74_ST": "A012"}
        assert "Warning" in zeile.cal_warn.cget("text"), "Warnung fehlt"
        assert "12 gauge" in zeile.btn.cget("text"), zeile.btn.cget("text")
        zeile._caliber_changed(T.caliber_label("A556"))
        app.update()
        assert zeile.cal_warn.cget("text").strip() == "", "Warnung ohne Anlass"
        zeile.reset()
        app.update()
        assert app.weapon_calibers == {}
        assert zeile.cal_menu.get().startswith("vanilla (")
        print("GUI: Dropdown, Warnung, Preset und Reset  OK")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

print("\nKALIBER-TEST OK")
