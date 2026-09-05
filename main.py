"""S2Tweaker - Einstiegspunkt fuer die Entwicklung (python main.py).

Der ausgelieferte Programmordner startet NICHT ueber diese Datei: dort ist
S2Tweaker.exe die signierte pythonw.exe von python.org, und
_internal/sitecustomize.py (Quelle: tools/launcher.py) ruft die GUI.
"""


def main():
    from s2tweaker.gui import run
    run()


if __name__ == "__main__":
    main()
