"""S2Tweaker – Einstiegspunkt (fuer python main.py und den EXE-Build)."""

import multiprocessing


def main():
    from s2tweaker.gui import run
    run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
