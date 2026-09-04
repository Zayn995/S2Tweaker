"""Die Suiten, die OHNE Spieldaten laufen — fuer GitHub Actions.

    python tests/run_ci.py

`tests/run_all.py` braucht den `vanilla/`-Ordner (extrahierte GameData).
Der darf NIE ins Repo (GSC-Copyright, siehe CLAUDE.md), also kann die CI
die volle Batterie nicht fahren. Diese zwei Suiten kommen ohne aus und
decken trotzdem das ab, was auf einem fremden Rechner schiefgehen kann:
dass die GUI ueberhaupt startet, dass jeder Regler in _collect() ankommt
und dass kein Netzwerkcode zurueckkehrt.

Die vollstaendige Batterie (32 Suiten) laeuft weiterhin lokal vor jedem
Release — die release-version-Skill besteht darauf.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [
    "test_gui_collect.py",
    "test_no_network.py",
]

env = dict(os.environ, PYTHONIOENCODING="utf-8")
failed = []
for name in ORDER:
    r = subprocess.run([sys.executable, str(HERE / name)], env=env,
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
print(f"ALLE {len(ORDER)} CI-SUITEN GRUEN "
      "(die uebrigen 30 brauchen Spieldaten und laufen lokal)")
