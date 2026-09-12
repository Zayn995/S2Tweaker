"""Development entry point: run with python main.py.

Portable builds launch through the signed pythonw.exe and
_internal/sitecustomize.py (tools/launcher.py)."""


def main():
    from s2tweaker.gui import run
    run()


if __name__ == "__main__":
    main()
