"""Die Suiten, die OHNE Spieldaten laufen — fuer GitHub Actions.

    python tests/run_ci.py

`tests/run_all.py` braucht den `vanilla/`-Ordner (extrahierte GameData).
Der darf NIE ins Repo (GSC-Copyright, siehe CLAUDE.md), also kann die CI
die volle Batterie nicht fahren. Diese Suiten pruefen ohne Fenster die
Feldverdrahtung, das Netzwerkverbot, Pak-Roundtrips sowie Editor-Profile,
Undo/Redo und Sicherung/Wiederherstellung eigener Paks.

Die vollstaendige Batterie laeuft weiterhin lokal vor jedem
Release — die release-version-Skill besteht darauf.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [
    "test_detail_controls.py",
    "test_artifact_additions.py",
    "test_job_localization.py",
    "test_job_return_markers.py",
    "test_npc_equipment.py",
    "test_artifact_extensions.py",
    "test_dialog_range.py",
    "test_regional_weather.py",
    "test_binary_cfg.py",
    "test_theme_palette.py",
    "test_startup_resources.py",
    "test_optional_spawn_cache.py",
    "test_wiring.py",
    "test_no_network.py",
    "test_pakfile.py",      # Pak-Roundtrip in reinem Python; der Spieldaten-Teil ueberspringt sich selbst
    "test_editor_state.py",
    "test_mod_library.py",
    "test_workbench_headless.py",
]

env = dict(os.environ, PYTHONIOENCODING="utf-8")
failed = []
for name in ORDER:
    args = ["--static-only"] if name == "test_wiring.py" else []
    r = subprocess.run([sys.executable, str(HERE / name), *args], env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    print(("OK  " if r.returncode == 0 else "FAIL") + "  " + name, flush=True)
    if r.returncode != 0:
        failed.append(name)
        for line in (r.stdout + "\n" + r.stderr).strip().splitlines()[-15:]:
            print("      " + line)

print()
if failed:
    print("ROT:", ", ".join(failed))
    sys.exit(1)
print(f"ALLE {len(ORDER)} CI-SUITEN GRUEN (ohne Fenster; volle Batterie lokal)")
