"""Generate a ribbon over the locally supplied Nexus icon using Pillow.

Read release/NEXUS_ICON_BASE.png and write release/NEXUS_ICON.png.
--pos controls the corner distance; --text separates lines with |."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "release" / "NEXUS_ICON_BASE.png"
OUT = REPO / "release" / "NEXUS_ICON.png"

AMBER = (217, 166, 72, 255)       # GUI accent.
EDGE = (120, 88, 30, 255)         # Ribbon edge lines.
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
                    help="Separate lines with |")
    ap.add_argument("--pos", type=float, default=0.5,
                    help="Where the ribbon intersects the edges (0.5 = center)")
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

    # Draw the ribbon horizontally, then rotate 45 degrees.
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

    # Ribbon midpoint between (0, pos*H) and (pos*W, 0).
    cx, cy = int(W * args.pos / 2), int(H * args.pos / 2)
    img.paste(rot, (cx - rot.width // 2, cy - rot.height // 2), rot)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(args.out)
    print(f"saved: {args.out} {img.size}, font {size} px, "
          f"{len(lines)} line(s)")


if __name__ == "__main__":
    main()
