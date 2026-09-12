"""Run headless suites in isolated processes with checked exit codes.

Examples:
    python tests/run_all.py
    python tests/run_all.py --only editor_state -j 2

Requires local vanilla data for game-data suites. Exclude window-based suites
from all selections, including --all; run visual checks separately.
Use bounded parallel workers and per-suite timeouts."""
import ast
import concurrent.futures
import os
import subprocess
import sys
import time
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
    "test_armor_extensions.py",
    "test_editor_state.py",
    "test_mod_library.py",
    "test_workbench_headless.py",
    "test_wiring.py",
    "test_loot_extensions.py",
    "test_repair_extensions.py",
    "test_world_extensions.py",
    "test_loot_conflicts.py",
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
    "test_repeatable_jobs.py",
    "test_job_isolation.py",
    "test_job_story_cleanup.py",
    "test_mod_harvest.py",
    "test_mod_audit.py",
    "test_ingame_fixes.py",
    "test_v135_tweaks.py",
    "test_key_families.py",
    "test_orphan_sids.py",
    "test_relations_runtime.py",
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
    """test_generate.py is at the repository root; other suites are in tests/."""
    return HERE.parent / name if name == "test_generate.py" else HERE / name


def _imports(path):
    """Which s2tweaker modules does this file import directly?"""
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
    """Find potentially affected suites through transitive imports of changed modules."""
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


def opens_window(name):
    """Detect suites constructing real app windows from their source."""
    try:
        return "gui.App()" in path_of(name).read_text(encoding="utf-8")
    except OSError:
        return False


args = sys.argv[1:]
# Full portable-build verification is a separate release check.
RELEASE_ONLY = ["test_build_layout.py"]
WINDOW = [n for n in ALL if opens_window(n) or n in RELEASE_ONLY]
picked = [n for n in ALL if n not in WINDOW]
# Exclude window suites from --all as well; individual manual runs remain available.
if "--only" in args:
    pats = []
    for argument in args[args.index("--only") + 1:]:
        if argument.startswith("-"):
            break
        pats.append(argument)
    matches = [n for n in ALL if any(p.lower() in n.lower() for p in pats)]
    picked = [n for n in matches if n not in WINDOW]
    skipped = [n for n in matches if n in WINDOW]
    if skipped:
        print("Window/release suites excluded:", ", ".join(skipped))
    if not picked:
        print("No match for:", " ".join(pats))
        sys.exit(2)

env = dict(os.environ, PYTHONIOENCODING="utf-8")
failed = []
times = []
t_all = time.time()
# Enforce per-suite timeouts so a stalled process cannot block the full run.
TIMEOUT = 900

# Parallelize headless suites only; window-based selection requires serial execution.
SLOW_FIRST = ["test_key_families.py", "test_modscan_filter.py",
              "test_build_layout.py", "test_wiring.py", "test_v128_tweaks.py",
              "test_orphan_sids.py"]


def _jobs():
    if any(opens_window(n) for n in picked):
        print("GUI suites selected -> serial execution to avoid window interference.")
        return 1
    for index, a in enumerate(args):
        if a.startswith("-j"):
            try:
                value = args[index + 1] if a == "-j" else a[2:]
                return max(1, int(value))
            except (ValueError, IndexError):
                pass
    return min(4, (os.cpu_count() or 2))


def run_one(name):
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(path_of(name))], env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT)
        code, out = r.returncode, r.stdout + "\n" + r.stderr
    except subprocess.TimeoutExpired:
        code, out = -1, f"TIMEOUT after {TIMEOUT} s - Did the test process stop responding?"
    return name, code, out, time.time() - t0


jobs = _jobs()
order = ([n for n in SLOW_FIRST if n in picked]
         + [n for n in picked if n not in SLOW_FIRST])
print(f"{len(order)} suites, {jobs} parallel")
done = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
    for name, code, out, dt in pool.map(run_one, order):
        done += 1
        times.append((dt, name))
        mark = "OK  " if code == 0 else ("TIME" if code == -1 else "FAIL")
        print(f"{mark}  {done:2d}/{len(order)}  {name:<28} {dt:5.1f}s", flush=True)
        if code != 0:
            failed.append(name)
            for line in out.strip().splitlines()[-12:]:
                print("      " + line)
print()
print(f"Total {(time.time() - t_all) / 60:.1f} min. The five slowest:")
for dt, name in sorted(times, reverse=True)[:5]:
    print(f"   {dt:5.1f}s  {name}")
print()
if failed:
    print("FAIL:", ", ".join(failed))
    sys.exit(1)
print(f"ALL {len(picked)} SUITES PASSED")
