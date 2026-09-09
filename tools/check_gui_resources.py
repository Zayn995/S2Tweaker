"""Explicit, single-window Windows resource check; never in automatic tests.

    python tools/check_gui_resources.py --open-window --report out/gui-resources.json

Optional: --vanilla PATH populates item trees from existing read-only game data.
--visual-review holds the Player page for manual visual inspection.
Settings/output are redirected to a temporary directory. No game is changed.
The parent enforces a timeout even if Tk fails during window construction.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open-window", action="store_true", help="explicit permission to open one test window")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--vanilla", type=Path)
    parser.add_argument("--portable", type=Path, help="check this existing portable S2Tweaker.exe with its own runtime")
    parser.add_argument("--visual-review", action="store_true", help="hold the Player page for 60 seconds for visual inspection instead of the resource sweep")
    parser.add_argument("--design-review", action="store_true", help="check palettes and toolbar, then hold the design chooser within the time budget")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.open_window:
        parser.error("This check opens a window. Run it explicitly with --open-window.")
    if sys.platform != "win32":
        parser.error("Windows is required for GetGuiResources.")
    args.report = args.report.resolve()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if not args.child:
        args.report.write_text(json.dumps({"passed": False, "samples": [],
                                          "errors": ["Check has not completed"]}), encoding="utf-8")
        env = dict(os.environ)
        if args.portable:
            command = [str(args.portable.resolve() / "S2Tweaker.exe")]
            env.pop("S2TWEAKER_SELFTEST", None)
            env["S2TWEAKER_GUI_CHECK"] = json.dumps({
                "report": str(args.report),
                "visual_review": args.visual_review,
                "design_review": args.design_review,
                "vanilla": str(args.vanilla.resolve()) if args.vanilla else None})
        else:
            command = [sys.executable, __file__, *sys.argv[1:], "--child"]
        try:
            result = subprocess.run(command, env=env, timeout=args.timeout)
            if result.returncode == 0:
                result_data = json.loads(args.report.read_text(encoding="utf-8"))
                if not result_data.get("passed") or result_data.get("errors"):
                    return 1
            return result.returncode
        except subprocess.TimeoutExpired:
            data = json.loads(args.report.read_text(encoding="utf-8"))
            data["passed"] = False
            data.setdefault("errors", []).append(f"Parent stopped the process after {args.timeout}s")
            args.report.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"GUI check stopped after {args.timeout}s; child process terminated.", flush=True)
            return 1
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from s2tweaker.gui_diagnostics import measure
    return measure(args)




if __name__ == "__main__":
    raise SystemExit(main())
