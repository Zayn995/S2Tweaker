"""Verify the application and launcher contain no networking implementation.

Displayed URLs are allowed for manual copying; fetching them is not part
of the application."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from s2tweaker import gui
SCRATCH = ROOT / "tests" / "_tmp"
SCRATCH.mkdir(exist_ok=True)
gui.SETTINGS_FILE = SCRATCH / "throwaway_settings.json"
gui.SETTINGS_FILE.unlink(missing_ok=True)

PAKET = ROOT / "s2tweaker"
VERBOTEN = {"urllib", "socket", "http", "requests", "ssl", "ftplib",
            "smtplib", "telnetlib", "webbrowser", "xmlrpc", "asyncio"}
VERBOTENE_AUFRUFE = {"urlopen", "urlretrieve", "socket", "create_connection",
                     "getaddrinfo", "connect"}

# Check package modules and the distributed sitecustomize launcher for network imports.
for datei in sorted(PAKET.glob("*.py")) + [ROOT / "tools" / "launcher.py"]:
    baum = ast.parse(datei.read_text(encoding="utf-8-sig"))
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            for alias in knoten.names:
                wurzel = alias.name.split(".")[0]
                assert wurzel not in VERBOTEN, \
                    f"{datei.name}:{knoten.lineno} imports {alias.name}"
        elif isinstance(knoten, ast.ImportFrom) and knoten.module:
            wurzel = knoten.module.split(".")[0]
            assert wurzel not in VERBOTEN, \
                f"{datei.name}:{knoten.lineno} imports from {knoten.module}"
        elif isinstance(knoten, ast.Call):
            ziel = knoten.func
            name = (ziel.attr if isinstance(ziel, ast.Attribute)
                    else ziel.id if isinstance(ziel, ast.Name) else "")
            assert name not in VERBOTENE_AUFRUFE, \
                f"{datei.name}:{knoten.lineno} calls {name}()"
print("No network imports or calls in the package  OK")

# Removed update-check symbols must remain absent.
for name in ("UPDATE_API_URL", "UPDATER_URL", "RELEASES_PAGE",
             "update_verdict", "_version_tuple"):
    assert not hasattr(gui, name), f"gui.{name} has returned"
print("Old update symbols removed  OK")

# --- 3) No obsolete update buttons; inspect source without opening windows ---
gui_tree = ast.parse((PAKET / "gui.py").read_text(encoding="utf-8-sig"))
attributes = {node.attr for node in ast.walk(gui_tree)
              if isinstance(node, ast.Attribute)}
assert not attributes & {"btn_update", "btn_updater"}, \
    "An obsolete update button has returned"
print("No update buttons in GUI source  OK")

# Do not include an updater script in the repository or player archive.
assert not (ROOT / "release" / "update.bat").exists(), \
    "release/update.bat has returned - the updater was intentionally removed"
zips = (ROOT / "tools" / "make_release_zips.py").read_text(encoding="utf-8")
assert '"update.bat" not in names' in zips, "ZIP builder regression guard missing"
print("No updater in the repository or ZIP  OK")

print("\nAll checks passed: no network access in the tool.")
