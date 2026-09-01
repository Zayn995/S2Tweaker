"""FAQ-Test: Inhalt-Sanity, Suche, Fenster-Wiederverwendung, Layout."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
# Frisch starten: eine liegengebliebene Datei (z.B. von einem frueheren
# Agenten-Lauf) wuerde den Neutral-Check faelschlich ausloesen.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.faq import FAQ_ENTRIES

# --- 1) Inhalt-Sanity ----------------------------------------------------
assert len(FAQ_ENTRIES) >= 25, len(FAQ_ENTRIES)
seen = set()
for e in FAQ_ENTRIES:
    assert e["q"].strip() and e["a"].strip() and e.get("k", "").strip(), e["q"]
    assert e["q"] not in seen, "doppelte Frage: " + e["q"]
    seen.add(e["q"])
    assert len(e["q"]) < 90, "Frage zu lang: " + e["q"]
    assert len(e["a"]) < 700, "Antwort zu lang: " + e["q"]
print(f"Inhalt: {len(FAQ_ENTRIES)} Eintraege, alle vollstaendig und eindeutig")

# Der Anlass-Fall MUSS funktionieren: "health pack" findet die Heil-Frage
def hits(query):
    words = query.lower().split()
    return [e["q"] for e in FAQ_ENTRIES
            if all(w in " ".join((e["q"], e["a"], e.get("k", ""))).lower()
                   for w in words)]
for query in ("health pack", "medkit", "medikit", "heal", "antivirus",
              "loot", "animation", "stealth", "dot", "oodle",
              "uninstall", "carry weight", "overweight", "inventory",
              "jamming", "jam", "anomaly", "emission", "alife",
              "spawn", "performance", "fps", "gamepass", "firerate",
              "slowmo", "weight"):
    found = hits(query)
    assert found, f"Suche '{query}' findet nichts!"
    print(f"   '{query}': {len(found)} Treffer, z.B. {found[0][:55]}")

# --- 2) GUI --------------------------------------------------------------
app = gui.App()
app.update()
assert app.btn_faq.winfo_ismapped() or True  # gemappt erst nach update_idletasks
app._show_faq()
app.update()
win = app._faq_win
assert win.winfo_exists()
rows = None
# Zeilen ueber das Fenster finden: FaqRow-Frames im ScrollableFrame
import s2tweaker.gui as g

# Suche ausfuehren wie ein Nutzer
entry = None
def find_entries(w):
    out = []
    for c in w.winfo_children():
        if isinstance(c, g.ctk.CTkEntry):
            out.append(c)
        out += find_entries(c)
    return out
search = win._faq_search
search.insert(0, "health pack")
win._faq_apply_filter()
app.update()

def visible_questions(w):
    out = []
    for c in w.winfo_children():
        if isinstance(c, g.ctk.CTkButton):
            txt = c.cget("text")
            if txt.startswith(("\u25b8", "\u25be")) and c.winfo_manager():
                # nur sichtbare (Eltern-Frame gepackt)
                if c.master.winfo_manager():
                    out.append(txt)
        out += visible_questions(c)
    return out
vis = visible_questions(win)
print("sichtbar bei 'health pack':", vis)
assert any("heal" in q.lower() for q in vis), vis
assert all(q.startswith("\u25be") for q in vis), "Treffer nicht aufgeklappt"

search.delete(0, "end")
search.insert(0, "xyzzy42")
win._faq_apply_filter()
app.update()
assert not visible_questions(win), "Nonsens-Suche zeigt noch Eintraege"

search.delete(0, "end")
win._faq_apply_filter()
app.update()
vis = visible_questions(win)
assert len(vis) == len(FAQ_ENTRIES), (len(vis), len(FAQ_ENTRIES))
assert all(q.startswith("\u25b8") for q in vis), "nach Leeren nicht zugeklappt"
print("Suche: filtern, aufklappen, leeren  OK")

# Zweiter Klick baut KEIN zweites Fenster
app._show_faq()
app.update()
tops = [w for w in app.winfo_children() if isinstance(w, g.ctk.CTkToplevel)]
assert len(tops) == 1, len(tops)
print("Fenster wird wiederverwendet  OK")

# Layout: FAQ-Knopf auch beim Minimum sichtbar
win.destroy()
for geom in ("1010x720", "880x600"):
    app.geometry(geom)
    app.update_idletasks()
    app.update()
    assert app.btn_faq.winfo_ismapped(), f"FAQ-Knopf bei {geom} unsichtbar"
    assert app.btn_faq.winfo_width() >= 60, app.btn_faq.winfo_width()
    assert app.search_entry.winfo_width() >= 150, "Suchfeld gequetscht"
print("Layout: FAQ-Knopf bei 1010 und 880 px sichtbar  OK")

app.destroy()
print("\nFAQ-TEST OK")
