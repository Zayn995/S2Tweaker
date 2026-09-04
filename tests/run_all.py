"""Komplette Testbatterie mit echten Exit-Codes.

    python tests/run_all.py

Braucht die Vanilla-Daten (vanilla/-Ordner im Repo, oder einmal die GUI
laden lassen und den Cache-Inhalt dorthin kopieren). Jeder Test laeuft als
eigener Prozess — ein Absturz in einem GUI-Test reisst so nicht den Rest
mit. Exit-Code 0 = alles gruen. Die Lehre hinter diesem Runner: Pipes wie
"| tail" verschlucken Exit-Codes; hier wird jeder Code einzeln geprueft.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [
    "test_loot_paths.py",
    "test_modscan_filter.py",
    "test_gui_release.py",
    "test_gui_collect.py",
    "test_slider_sweep.py",
    "test_log_slider.py",
    "test_gui_armor.py",
    "test_gui_avoid.py",
    "test_gui_qol.py",
    "test_gui_faq.py",
    "test_gui_modscan.py",
    "test_modscan_e2e.py",
    "test_gui_factions.py",
    "test_gui_mutants.py",
    "test_quest_ads.py",
    "test_zero_factors.py",
    "test_recoil_upgrades.py",
    "test_magazine_cascade.py",
    "test_upgrades.py",
    "test_alife_spawns.py",
    "test_v118_tweaks.py",
    "test_npc_combat.py",
    "test_npc_more.py",
    "test_index_entries.py",
    "test_trader_condition.py",
    "test_emission_relext.py",
    "test_dlc_weapons.py",
    "test_names.py",
    "test_update_check.py",
    "test_workshop_scan.py",
    "test_gui_layout.py",
]

env = dict(os.environ, PYTHONIOENCODING="utf-8")
failed = []
for name in ORDER:
    r = subprocess.run([sys.executable, str(HERE / name)], env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    print(("OK  " if r.returncode == 0 else "FAIL") + "  " + name)
    if r.returncode != 0:
        failed.append(name)
        tail = (r.stdout + "\n" + r.stderr).strip().splitlines()[-12:]
        for line in tail:
            print("      " + line)

# Ende-zu-Ende-Pak-Bau (liegt im Repo-Wurzelverzeichnis)
r = subprocess.run([sys.executable, str(HERE.parent / "test_generate.py")],
                   env=env, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
print(("OK  " if r.returncode == 0 else "FAIL") + "  test_generate.py")
if r.returncode != 0:
    failed.append("test_generate.py")

print()
if failed:
    print("ROT:", ", ".join(failed))
    sys.exit(1)
print(f"ALLE {len(ORDER) + 1} SUITEN GRUEN")
