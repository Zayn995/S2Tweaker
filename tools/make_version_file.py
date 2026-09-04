"""Erzeugt die Windows-Versions-Ressource fuer die EXE.

    python tools/make_version_file.py            -> build/version_info.txt
    python tools/make_version_file.py <pfad>

Warum das noetig ist (Nexus-Quarantaene, 04.09.2026): die bis dahin
gebaute EXE hatte GAR KEINE Versions-Ressource — Hersteller, Produkt,
Beschreibung und Version waren leer. Eine unsignierte Datei ohne jede
Herkunftsangabe ist fuer die ML-Heuristiken von Windows Defender & Co.
ein starkes Verdachtsmerkmal (nachgemessen mit Get-Item .VersionInfo).
Der Nexus-Support konnte die Datei deshalb nicht freigeben.

Die Nummern kommen aus s2tweaker.__version__ — nichts wird doppelt
gepflegt, ein Release kann nicht mit einer veralteten Zahl in der
Ressource herauskommen.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from s2tweaker import __version__

COMPANY = "Zayn995"
PRODUCT = "S2Tweaker"
DESCRIPTION = "S2Tweaker - S.T.A.L.K.E.R. 2 Mod Generator"
COPYRIGHT = "MIT License - https://github.com/Zayn995/S2Tweaker"

TEMPLATE = """# Wird von tools/make_version_file.py erzeugt - nicht von Hand aendern.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={nums},
    prodvers={nums},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{company}'),
        StringStruct('FileDescription', '{description}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{product}'),
        StringStruct('LegalCopyright', '{copyright}'),
        StringStruct('OriginalFilename', '{product}.exe'),
        StringStruct('ProductName', '{product}'),
        StringStruct('ProductVersion', '{version}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """'1.18.3' -> (1, 18, 3, 0); Windows will immer genau vier Zahlen."""
    parts = [int(p) for p in version.split(".") if p.isdigit()]
    parts += [0] * (4 - len(parts))
    return tuple(parts[:4])


def write(target: Path) -> Path:
    """Ressource schreiben; wird auch von tools/build_exe.py aufgerufen."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        TEMPLATE.format(nums=version_tuple(__version__), company=COMPANY,
                        product=PRODUCT, description=DESCRIPTION,
                        copyright=COPYRIGHT, version=__version__),
        encoding="utf-8")
    return target


def main() -> None:
    target = write(Path(sys.argv[1]) if len(sys.argv) > 1
                   else REPO / "build" / "version_info.txt")
    print(f"{target}: S2Tweaker {__version__} {version_tuple(__version__)}")


if __name__ == "__main__":
    main()
