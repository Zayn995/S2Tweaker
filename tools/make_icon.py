"""Erzeugt das Nexus-Icon mit Schaerpe: release/NEXUS_ICON.png.

    python tools\\make_icon.py
    python tools\\make_icon.py --text "NOW SHIPS WITHOUT|KEYLOGGERS OR TROJANS :D"
    python tools\\make_icon.py --pos 0.42        (Schaerpe naeher an die Ecke)

Grundlage ist release/NEXUS_ICON_BASE.png (das bisherige Icon, liegt nur
lokal - siehe .gitignore). Darauf kommt eine Schaerpe, die von der Mitte
der linken Kante zur Mitte der oberen Kante laeuft (--pos 0.5; kleiner =
naeher an der Ecke), Bernstein wie in der GUI, Text dunkel, Zeilen mit |
getrennt. Idee des Besitzers (05.09.2026): "new ships without keylogger
or trojans now :D" - der Witz zu den Fehlalarmen, nachdem 1.21.0 bei
allen Scannern sauber ist.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "release" / "NEXUS_ICON_BASE.png"
OUT = REPO / "release" / "NEXUS_ICON.png"

AMBER = (217, 166, 72, 255)       # ACCENT der GUI
EDGE = (120, 88, 30, 255)         # Kantenlinien der Schaerpe
DARK = (24, 24, 26, 255)          # Text
SHADOW = (0, 0, 0, 120)


def font(size: int, variation: str = "Bold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", size)
    try:
        f.set_variation_by_name(variation)
    except Exception:
        pass
    return f


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="NOW SHIPS WITHOUT|KEYLOGGERS OR TROJANS :D",
                    help="Zeilen mit | trennen")
    ap.add_argument("--pos", type=float, default=0.5,
                    help="wo die Schaerpe die Kanten schneidet (0.5 = Mitte)")
    ap.add_argument("--base", default=str(BASE))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    img = Image.open(args.base).convert("RGBA")
    W, H = img.size
    lines = args.text.split("|")
    size = int(W * 0.042)
    f = font(size)
    line_h = int(size * 1.12)
    band_h = line_h * len(lines) + int(size * 0.8)
    band_len = int(W * 2.2)

    # Schaerpe waagerecht zeichnen, dann um 45 Grad drehen
    top = 24
    layer = Image.new("RGBA", (band_len, band_h + 2 * top), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rectangle((0, top + 10, band_len, top + band_h + 10), fill=SHADOW)
    ld.rectangle((0, top, band_len, top + band_h), fill=AMBER)
    ld.line((0, top + 7, band_len, top + 7), fill=EDGE, width=3)
    ld.line((0, top + band_h - 7, band_len, top + band_h - 7), fill=EDGE, width=3)
    y = top + (band_h - line_h * len(lines)) // 2 - int(size * 0.08)
    for line in lines:
        tw = int(ld.textlength(line, font=f))
        ld.text(((band_len - tw) // 2, y), line, font=f, fill=DARK)
        y += line_h
    rot = layer.rotate(45, expand=True, resample=Image.BICUBIC)

    # Mittelpunkt der Schaerpe: halbe Strecke zwischen (0, pos*H) und (pos*W, 0)
    cx, cy = int(W * args.pos / 2), int(H * args.pos / 2)
    img.paste(rot, (cx - rot.width // 2, cy - rot.height // 2), rot)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(args.out)
    print(f"gespeichert: {args.out} {img.size}, Schrift {size} px, "
          f"{len(lines)} Zeile(n)")


if __name__ == "__main__":
    main()
