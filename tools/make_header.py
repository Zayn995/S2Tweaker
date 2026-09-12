"""Generate the Nexus header image with Pillow.

The layout uses a dark background, amber symbols and crossed-out historical
feature counts. Output: release/NEXUS_HEADER.png."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STRUCK_NUMBERS = ["41", "124", "160", "180", "195", "200", "210", "230", "240", "250", "265", "290", "340", "400", "430", "450"]
CURRENT_NUMBER = "460"

W, H = 1300, 372
OUT = Path(__file__).resolve().parent.parent / "release" / "NEXUS_HEADER.png"

BG = (24, 24, 26)
TITLE = (198, 200, 204)
AMBER = (217, 166, 72)          # GUI accent.
AMBER_DIM = (46, 38, 20)        # Watermark.
GREY = (150, 152, 156)
BAR_BG = (90, 95, 102)
KNOB = (190, 192, 196)


def font(size: int, name: str = "bahnschrift.ttf", variation: str | None = "Bold"):
    f = ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)
    if variation and name.startswith("bahnschrift"):
        try:
            f.set_variation_by_name(variation)
        except Exception:
            pass
    return f


def trefoil(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float,
            color, bg=None):
    """Radiation symbol: three 60-degree blades and a central disc."""
    box = (cx - r, cy - r, cx + r, cy + r)
    for start in (-90 - 30, 30 - 30, 150 - 30):
        draw.pieslice(box, start, start + 60, fill=color)
    hole = r * 0.42
    draw.ellipse((cx - hole, cy - hole, cx + hole, cy + hole),
                 fill=bg or BG)
    hub = r * 0.22
    draw.ellipse((cx - hub, cy - hub, cx + hub, cy + hub), fill=color)


def slider(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, pos: float):
    h = 7
    knob_x = x0 + (x1 - x0) * pos
    draw.rounded_rectangle((x0, y - h // 2, x1, y + h // 2), radius=4,
                           fill=BAR_BG)
    draw.rounded_rectangle((x0, y - h // 2, knob_x, y + h // 2), radius=4,
                           fill=AMBER)
    r = 11
    draw.ellipse((knob_x - r, y - r, knob_x + r, y + r), fill=KNOB)
    draw.ellipse((knob_x - r + 3, y - r + 3, knob_x + r - 3, y + r - 3),
                 fill=(120, 123, 128))


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# Trefoil watermark on the right, intentionally cropped.
trefoil(d, W - 210, 180, 260, AMBER_DIM)

# Small amber trefoil and title.
trefoil(d, 118, 62, 52, AMBER)
d.text((195, 8), "S2TWEAKER", font=font(96), fill=TITLE)

d.text((197, 122), "BUILD YOUR OWN S.T.A.L.K.E.R. 2 TWEAK MOD",
       font=font(35), fill=AMBER)


def scribbled_number(text: str, size: int, color, strike=True,
                     angle: float = 0.0) -> Image.Image:
    """Render a rotated RGBA number, optionally crossed out with two uneven strokes."""
    f = font(size)
    pad = 14
    w = int(d.textlength(text, font=f)) + 2 * pad
    h = size + 2 * pad
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.text((pad, pad), text, font=f, fill=color)
    if strike:
        mid = pad + size * 0.56
        for pass_no, (dy0, dy1) in enumerate(((-2, 4), (5, -3))):
            points = []
            steps = 9
            for i in range(steps + 1):
                t = i / steps
                x = pad - 2 + t * (w - 2 * pad + 4)
                wobble = math.sin(t * math.pi * (2.4 + pass_no)) * 2.2
                y = mid + dy0 + (dy1 - dy0) * t + wobble
                points.append((x, y))
            td.line(points, fill=AMBER, width=3, joint="curve")
    return tile.rotate(angle, expand=True, resample=Image.BICUBIC)


# Keep the original tagline fixed and layer historical count revisions around it.
tag_font = font(28, variation="SemiBold")
X0, X_MAX, Y_BASE = 197, 1268, 186
PREFIX = "Sliders in.  .pak out.  "
SUFFIX = " tweaks \u2013 zero modding knowledge needed."
STRUCK_GREY = (128, 130, 134)

x = X0
d.text((x, Y_BASE), PREFIX, font=tag_font, fill=GREY)
x += int(d.textlength(PREFIX, font=tag_font))
anchor = scribbled_number(STRUCK_NUMBERS[0], 28, STRUCK_GREY, angle=-2.5)
ax, ay = x - 12, Y_BASE - 12            # Compensate for the cropped border: 41 pixels in text flow.
img.paste(anchor, (ax, ay), anchor)
x += anchor.width - 18
suffix_x = x
d.text((x, Y_BASE), SUFFIX, font=tag_font, fill=GREY)
if x + int(d.textlength(SUFFIX, font=tag_font)) > X_MAX:
    raise SystemExit("Header text no longer fits the image; shorten PREFIX/SUFFIX.")


def word_x(word: str) -> int:
    """Return a word's left edge within the rendered tagline."""
    if word in PREFIX:
        return X0 + int(d.textlength(PREFIX[:PREFIX.index(word)], font=tag_font))
    return suffix_x + int(d.textlength(SUFFIX[:SUFFIX.index(word)], font=tag_font))


# Allocate revision positions around the original count and adjacent words.
# Each position stores x, y, font size and rotation.
ABOVE, BELOW = ay - 27, ay + 32
SLOTS = [
    (ax - 32, ABOVE + 1, 20, 11),             # Above the count, left.
    (ax + 18, ABOVE - 4, 20, -8),             # Above the count, right.
    (ax - 38, BELOW, 22, -6),                 # Below the count, left.
    (ax + 22, BELOW + 3, 22, 7),              # Below the count, right.
]
# Reserve the space around out. for the count's left-side annotations.
NEAREST_FIRST = ("tweaks", ".pak", "zero", "in.", "modding", "Sliders",
                 "knowledge", "needed")
for k, word in enumerate(NEAREST_FIRST):
    wx = word_x(word) + (30 if word in SUFFIX else -4)
    SLOTS.append((wx, ABOVE - 2 + 5 * (k % 2), 20, (5, -5, 10, -7, 4, -9, 6, -3)[k]))
    SLOTS.append((wx + 6, BELOW + 2 - 4 * (k % 2), 22, (-9, 8, -4, 6, -8, 5, -7, 9)[k]))

later = [(n, True) for n in STRUCK_NUMBERS[1:]] + [(CURRENT_NUMBER, False)]
if len(later) > len(SLOTS):
    raise SystemExit(f"{len(later)} additions, but only {len(SLOTS)} slots - "
                     "Add more SLOTS in tools/make_header.py.")
for (number, struck), (sx, sy, size, angle) in zip(later, SLOTS):
    if struck:
        tile = scribbled_number(number, size, STRUCK_GREY, angle=angle)
    else:
        tile = scribbled_number(number, size + 4, AMBER, strike=False, angle=angle)
        sy -= 2
    img.paste(tile, (sx, sy), tile)

slider(d, 200, 740, 278, 0.67)
slider(d, 200, 740, 319, 0.29)
slider(d, 200, 740, 358, 0.51)
print(f"Master set fixed (41), {len(later)} additions in {len(SLOTS)} slots; "
      f"aktuell {CURRENT_NUMBER} occupies position {len(later)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("saved:", OUT, img.size)
