"""Run CI suites that need neither game data nor application windows.

The full game-data suite runs locally because extracted GSC files must not
be published. Coverage includes wiring, offline behavior, Paks and editor state."""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [
    "test_public_files.py",
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
    "test_pakfile.py",      # Pure-Python Pak roundtrip; the game-data portion skips when unavailable.
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
    print("FAIL:", ", ".join(failed))
    sys.exit(1)
print(f"ALL {len(ORDER)} CI SUITES PASSED (headless; full suite available locally)")
