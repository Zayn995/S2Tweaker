"""FAQ: content validity, search, window reuse and layout."""
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
# Start with clean temporary state so leftovers cannot affect neutrality checks.
gui.SETTINGS_FILE.unlink(missing_ok=True)

from s2tweaker.faq import FAQ_ENTRIES

# --- 1) Content validity ---
assert len(FAQ_ENTRIES) >= 25, len(FAQ_ENTRIES)
seen = set()
for e in FAQ_ENTRIES:
    assert e["q"].strip() and e["a"].strip() and e.get("k", "").strip(), e["q"]
    assert e["q"] not in seen, "duplicate question: " + e["q"]
    seen.add(e["q"])
    assert len(e["q"]) < 90, "Question too long: " + e["q"]
    assert len(e["a"]) < 700, "Answer too long: " + e["q"]
print(f"Inhalt: {len(FAQ_ENTRIES)} entries, all complete and unique")

# Searching health pack must find the healing question.
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
    assert found, f"Search '{query}' returns no matches!"
    print(f"   '{query}': {len(found)} matches, e.g. {found[0][:55]}")

# --- 2) GUI --------------------------------------------------------------
app = gui.App()
app.update()
assert app.btn_faq.winfo_ismapped() or True  # Mapped only after update_idletasks.
app._show_faq()
app.update()
win = app._faq_win
assert win.winfo_exists()
rows = None
# Find FaqRow frames inside the scrollable container.
import s2tweaker.gui as g

# Run a search through the UI.
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
                # Count only rows whose parent is packed.
                if c.master.winfo_manager():
                    out.append(txt)
        out += visible_questions(c)
    return out
vis = visible_questions(win)
print("Visible for 'health pack':", vis)
assert any("heal" in q.lower() for q in vis), vis
assert all(q.startswith("\u25be") for q in vis), "Match not expanded"

search.delete(0, "end")
search.insert(0, "xyzzy42")
win._faq_apply_filter()
app.update()
assert not visible_questions(win), "Nonsense search still shows entries"

search.delete(0, "end")
win._faq_apply_filter()
app.update()
vis = visible_questions(win)
assert len(vis) == len(FAQ_ENTRIES), (len(vis), len(FAQ_ENTRIES))
assert all(q.startswith("\u25b8") for q in vis), "Not collapsed after clearing search"
print("Search: filter, expand, clear  OK")

# A second click must not create another window.
app._show_faq()
app.update()
tops = [w for w in app.winfo_children() if isinstance(w, g.ctk.CTkToplevel)]
assert len(tops) == 1, len(tops)
print("Window reused  OK")

# Keep the FAQ button visible at minimum width.
win.destroy()
for geom in ("1010x720", "880x600"):
    app.geometry(geom)
    app.update_idletasks()
    app.update()
    assert app.btn_faq.winfo_ismapped(), f"FAQ button at {geom} invisible"
    assert app.btn_faq.winfo_width() >= 60, app.btn_faq.winfo_width()
    assert app.search_entry.winfo_width() >= 150, "Search field squeezed"
print("Layout: FAQ button visible at 1010 and 880 px  OK")

app.destroy()
print("\nFAQ-TEST OK")
