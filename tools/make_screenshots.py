"""Erzeugt die Screenshot-Serie fuer die Nexus-Mod-Seite.

    python tools\make_screenshots.py

Braucht Pillow (pip install pillow) und den vanilla/-Ordner (also einmal
"Confirm & load game data" im Tool gelaufen, oder ein GameData-Dump).
Ergebnis: release/screenshots/*.png (1280x850), danach von Hand als ZIP
packen und auf Nexus unter Manage -> Images hochladen.

Das Fenster wird waehrend des Laufs sichtbar auf- und zugeklappt — nicht
anfassen, sonst landet der Mauszeiger bzw. ein anderes Fenster im Bild.
Die echte settings.json wird NIE angefasst (SETTINGS_FILE zeigt woanders hin).
"""
import sys
import time
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "release" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from s2tweaker import gui as guimod            # noqa: E402
from s2tweaker.gamedata import GameData        # noqa: E402

# Umbiegen, damit ein Lauf NIE die echten Einstellungen ueberschreibt:
guimod.SETTINGS_FILE = OUT / "_throwaway_settings.json"
VANILLA = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite" / "GameData"

app = guimod.App()
app.geometry("1280x850+60+20")   # feste Position: sonst reicht das Fenster
app.update()                     # unter die Taskleiste und die kommt mit aufs Bild
app.update()
app.gd = GameData(VANILLA)
app._iw_populate()
app._ia_populate()
app._ir_populate()
app._if_populate()
app._mut_populate()
app._set_body_state(True)
app.status.configure(text="Ready. Analyzed your game version – 80 weapons, "
                          "34 ammo types, 41 mutant prototypes.")
app.update()


def scrollable_of(widget):
    w = widget
    while w is not None and not isinstance(w, guimod.ctk.CTkScrollableFrame):
        w = w.master
    return w


def scroll_to(widget, margin=40):
    sf = scrollable_of(widget)
    if sf is None:
        return
    app.update_idletasks()
    y = widget.winfo_rooty() - sf._parent_canvas.winfo_rooty()
    top = sf._parent_canvas.canvasy(0)
    box = sf._parent_canvas.bbox("all")
    if not box:
        return
    sf._parent_canvas.yview_moveto(max(0.0, (top + y - margin) / max(1, box[3])))
    app.update_idletasks()


def scroll_top(tab_widget):
    sf = scrollable_of(tab_widget)
    if sf is not None:
        sf._parent_canvas.yview_moveto(0.0)
        app.update_idletasks()


def shot(name):
    app.lift()
    app.focus_force()
    app.update()
    time.sleep(0.7)
    app.update()
    x0, y0 = app.winfo_rootx(), app.winfo_rooty()
    img = ImageGrab.grab((x0, y0, x0 + app.winfo_width(), y0 + app.winfo_height()))
    img.save(OUT / name)
    print("  saved", name, img.size)


S = app.sliders

# ---------------------------------------------------------------- 1 Player
app.tabs.set("Player")
S["hp"].set(200)
S["hp_regen"].set(1)
S["sp"].set(200)
S["fall"].set(25)
S["jump"].set(120)
scroll_top(app.tabs.tab("Player"))
shot("01_player.png")

# ------------------------------------------------------------ 2 Vaulting
app.tabs.set("Vaulting")
S["vault_height"].set(150)
S["vault_distance"].set(400)
app.checks["improved_vaulting"].select()
scroll_top(app.tabs.tab("Vaulting"))
shot("02_vaulting.png")
app.checks["improved_vaulting"].deselect()

# ------------------------------------------------------- 2 Weight & items
app.tabs.set("Weight & items")
S["carry"].set(250)
S["penalty"].set(200)
S["weight"].set(0.5)
scroll_top(app.tabs.tab("Weight & items"))
shot("03_weight.png")

# ------------------------------------------------------------- 3 Combat
app.tabs.set("Combat")
S["pdmg"].set(1.5)
S["npcdmg"].set(0.75)
S["headshot"].set(2)
scroll_top(app.tabs.tab("Combat"))
shot("04_combat.png")

# ------------------------------------- 4 Weapons: global + category blocks
app.tabs.set("Weapons")
S["spread"].set(75)
S["recoil"].set(60)
S["wrange"].set(130)
app._wcat_btns["shotgun"][0].invoke()      # nur EINE Kategorie offen zeigen
S["wcat_shotgun_damage"].set(2.0)
S["wcat_shotgun_firerate"].set(1.25)
S["wcat_pistol_recoil"].set(0.75)
S["wcat_sniper_damage"].set(1.5)
scroll_to(app._wcat_btns["pistol"][0], margin=95)   # Abschnitts-Titel mit drauf
shot("05_weapon_categories.png")

# --------------------------------------------- 5 Weapons: per-weapon tree
app._wcat_btns["shotgun"][0].invoke()      # wieder zuklappen
blk = app._iw_blocks["rifle"]
blk.expand()
row = blk.rows["GunAK74_ST"]
row.toggle()
row.sliders["damage"].set(1.5)
row.sliders["recoil"].set(0.5)
row.sliders["durability"].set(2.0)
other = blk.rows["GunGvintar_ST"]
other.toggle()
other.sliders["spread"].set(0.5)
other.toggle()
app.update()
scroll_to(blk.btn, margin=20)
shot("06_weapon_tree.png")

# ------------------------------------------------------------- 6 Ammo tab
app.tabs.set("Ammo")
S["ammo_dmg"].set(125)
S["ammo_ap"].set(150)
cal = app._ia_blocks["A545"]
cal.expand()
arow = cal.rows["A545A"]
arow.toggle()
arow.sliders["damage"].set(2.0)
arow.sliders["armordamage"].set(1.5)
erow = cal.rows["A545E"]
erow.toggle()
erow.sliders["damage"].set(1.25)
erow.toggle()
app.update()
scroll_to(app._ia_blocks["A918"].btn, margin=48)   # Knopf darueber nicht anschneiden
shot("07_ammo_tree.png")

# ------------------------------------------------------------ 7 Armor tab
app.tabs.set("Armor")
S["ap_strike"].set(150)
S["ap_rad"].set(125)
grp = app._ir_blocks["Body"]
grp.expand()
exo = grp.rows["Exoskeleton_Dolg_Armor"]
exo.toggle()
exo.sliders["strike"].set(2.0)
exo.sliders["burn"].set(1.5)
seva = grp.rows["SEVA_Neutral_Armor"]
seva.toggle()
seva.sliders["radiation"].set(2.0)
seva.toggle()
app.update()
scroll_to(exo.btn, margin=48)
shot("08_armor_tree.png")

# ------------------------------------------------------------- 8 NPCs & AI
app.tabs.set("NPCs & AI")
S["npc_acc"].set(0.75)
S["npc_vision"].set(40)
S["npc_hearing"].set(30)
S["npc_grenades"].set(0)
scroll_top(app.tabs.tab("NPCs & AI"))
shot("09_npcs_ai.png")

# ------------------------------------------------------------ 9 Factions
app.tabs.set("Factions")
pkey = app.gd.relation_pair_key("Bandits", "Player")
app._if_blocks["player"].rows[pkey].set(600)
dblk = app._if_blocks["Duty"]
dblk.expand()
dblk.rows[app.gd.relation_pair_key("Duty", "Freedom")].set(-800)
app.update()
scroll_top(app.tabs.tab("Factions"))
shot("10_factions.png")

# -------------------------------------------------------------- 10 Search
app.tabs.set("Weapons")
app.search_entry.delete(0, "end")
app.search_entry.insert(0, "ak74")
app._apply_filter()
end = time.perf_counter() + 1.0            # after()-Auftrag feuern lassen
while time.perf_counter() < end:
    app.update()
    time.sleep(0.01)
scroll_to(app._iw_blocks["rifle"].btn, margin=20)
shot("11_search.png")
app.search_entry.delete(0, "end")
app._apply_filter()

# -------------------------------------------------------------- 11 World
app.tabs.set("World")
S["anomaly"].set(1.5)
S["radiation"].set(0.5)
S["hunger"].set(50)
scroll_top(app.tabs.tab("World"))
shot("12_world.png")

# ------------------------------------------------------------ 12 Economy
app.tabs.set("Economy")
S["buyprice"].set(1.5)
S["sellprice"].set(0.75)
S["repair"].set(0.5)
scroll_top(app.tabs.tab("Economy"))
shot("13_economy.png")

print("\nweapon_overrides:", app.weapon_overrides)
print("ammo_overrides:", app.ammo_overrides)
app.destroy()
print("done ->", OUT)
