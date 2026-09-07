"""Komplette Testbatterie mit echten Exit-Codes.

    python tests/run_all.py              # alles
    python tests/run_all.py --changed    # nur, was die Aenderung beruehrt
    python tests/run_all.py --only theme gui_layout

Braucht die Vanilla-Daten (vanilla/-Ordner im Repo, oder einmal die GUI
laden lassen und den Cache-Inhalt dorthin kopieren). Jeder Test laeuft als
eigener Prozess — ein Absturz in einem GUI-Test reisst so nicht den Rest
mit. Exit-Code 0 = alles gruen. Die Lehre hinter diesem Runner: Pipes wie
"| tail" verschlucken Exit-Codes; hier wird jeder Code einzeln geprueft.
"""
import ast
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [
    "test_loot_paths.py",
    "test_modscan_filter.py",
    "test_gui_release.py",
    "test_gui_collect.py",
    "test_slider_sweep.py",
    "test_log_slider.py",
    "test_slider_entry.py",
    "test_theme.py",
    "test_gui_armor.py",
    "test_gui_avoid.py",
    "test_gui_qol.py",
    "test_gui_faq.py",
    "test_gui_modscan.py",
    "test_modscan_e2e.py",
    "test_gui_factions.py",
    "test_gui_mutants.py",
    "test_gui_scopes.py",
    "test_quest_ads.py",
    "test_zero_factors.py",
    "test_recoil_upgrades.py",
    "test_magazine_cascade.py",
    "test_ammo_caliber.py",
    "test_stack_size.py",
    "test_upgrades.py",
    "test_alife_spawns.py",
    "test_v118_tweaks.py",
    "test_npc_combat.py",
    "test_npc_more.py",
    "test_npc_flashlight.py",
    "test_saves.py",
    "test_pakfile.py",
    "test_v124_tweaks.py",
    "test_v125_tweaks.py",
    "test_v126_tweaks.py",
    "test_v127_tweaks.py",
    "test_v128_tweaks.py",
    "test_index_entries.py",
    "test_trader_condition.py",
    "test_emission_relext.py",
    "test_dlc_weapons.py",
    "test_names.py",
    "test_no_network.py",
    "test_no_download.py",
    "test_build_layout.py",
    "test_workshop_scan.py",
    "test_gui_layout.py",
]


ALL = ORDER + ["test_generate.py"]


def path_of(name):
    """test_generate.py liegt im Wurzelverzeichnis, alles andere in tests/."""
    return HERE.parent / name if name == "test_generate.py" else HERE / name


def _imports(path):
    """Welche s2tweaker-Module importiert diese Datei direkt?"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "s2tweaker":
                out |= {a.name for a in node.names}
            elif node.module.startswith("s2tweaker."):
                out.add(node.module.split(".", 1)[1])
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("s2tweaker."):
                    out.add(a.name.split(".", 1)[1])
    return out


def affected_by(changed):
    """Suiten, die von den geaenderten Dateien betroffen sein KOENNEN.

    Ueber den echten Import-Graphen, nicht ueber eine von Hand gepflegte
    Tabelle: ein geaendertes Modul zieht alle Module nach sich, die es
    importieren, und am Ende jede Suite, die eines davon benutzt.
    Lieber eine Suite zu viel als eine zu wenig - darum transitiv.
    Fuer den Stand VOR einem Release gilt weiter der volle Lauf."""
    deps = {m.stem: _imports(m)
            for m in (HERE.parent / "s2tweaker").glob("*.py")}
    hit = {Path(c).stem for c in changed
           if c.startswith("s2tweaker/") and c.endswith(".py")}
    grew = True
    while grew:
        grew = False
        for mod, used in deps.items():
            if mod not in hit and used & hit:
                hit.add(mod)
                grew = True
    picked = []
    for name in ALL:
        if f"tests/{name}" in changed or name in changed:
            picked.append(name)
        elif hit and _imports(path_of(name)) & hit:
            picked.append(name)
    return picked


args = sys.argv[1:]
picked = ALL
if "--changed" in args:
    git = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                         cwd=HERE.parent, capture_output=True, text=True)
    new = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                         cwd=HERE.parent, capture_output=True, text=True)
    changed = {ln.strip() for ln in (git.stdout + new.stdout).splitlines()
               if ln.strip()}
    picked = affected_by(changed)
    print(f"--changed: {len(changed)} geaenderte Datei(en) -> "
          f"{len(picked)} von {len(ALL)} Suiten")
    if not picked:
        print("Nichts Relevantes geaendert.")
        sys.exit(0)
elif "--only" in args:
    pats = [a for a in args[args.index("--only") + 1:] if not a.startswith("-")]
    picked = [n for n in ALL if any(p.lower() in n.lower() for p in pats)]
    if not picked:
        print("Kein Treffer fuer:", " ".join(pats))
        sys.exit(2)

env = dict(os.environ, PYTHONIOENCODING="utf-8")
failed = []
times = []
t_all = time.time()
for name in picked:
    t0 = time.time()
    r = subprocess.run([sys.executable, str(path_of(name))], env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    dt = time.time() - t0
    times.append((dt, name))
    mark = "OK  " if r.returncode == 0 else "FAIL"
    print(f"{mark}  {name:<28} {dt:5.1f}s")
    if r.returncode != 0:
        failed.append(name)
        both = r.stdout + "\n" + r.stderr
        for line in both.strip().splitlines()[-12:]:
            print("      " + line)

print()
print(f"Gesamt {(time.time() - t_all) / 60:.1f} min. Die fuenf laengsten:")
for dt, name in sorted(times, reverse=True)[:5]:
    print(f"   {dt:5.1f}s  {name}")
print()
if failed:
    print("ROT:", ", ".join(failed))
    sys.exit(1)
print(f"ALLE {len(picked)} SUITEN GRUEN")
