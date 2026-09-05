"""Erzeugt das Nexus-Header-Bild (1300x372) in release/NEXUS_HEADER.png.

    python tools\\make_header.py

Braucht Pillow. Stil wie das bisherige Header-Bild: dunkler Grund,
grosses Radioaktiv-Symbol als Wasserzeichen rechts, Bernstein-Trefoil
neben dem Titel, drei Slider.

Running-Gag des Besitzers (02.09.): die Tweak-Zahl sieht aus, als
waere sie immer wieder von Hand unsauber durchgestrichen und ersetzt
worden. Beim naechsten grossen Release einfach die aktuelle Zahl an
STRUCK_NUMBERS anhaengen und CURRENT_NUMBER neu setzen — fertig.
Die Zahlen sind die echte Historie (v1.0 / v1.3 / v1.7).
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STRUCK_NUMBERS = ["41", "124", "160", "180", "195", "200", "210"]
CURRENT_NUMBER = "230"

W, H = 1300, 372
OUT = Path(__file__).resolve().parent.parent / "release" / "NEXUS_HEADER.png"

BG = (24, 24, 26)
TITLE = (198, 200, 204)
AMBER = (217, 166, 72)          # ACCENT der GUI
AMBER_DIM = (46, 38, 20)        # Wasserzeichen
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
    """Radioaktiv-Symbol: drei 60-Grad-Fluegel + Nabe."""
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

# Wasserzeichen-Trefoil rechts, bewusst angeschnitten
trefoil(d, W - 210, 180, 260, AMBER_DIM)

# Kleines Bernstein-Trefoil + Titel
trefoil(d, 118, 62, 52, AMBER)
d.text((195, 8), "S2TWEAKER", font=font(96), fill=TITLE)

d.text((197, 122), "BUILD YOUR OWN S.T.A.L.K.E.R. 2 TWEAK MOD",
       font=font(35), fill=AMBER)


def scribbled_number(text: str, size: int, color, strike=True,
                     angle: float = 0.0) -> Image.Image:
    """Eine Zahl als RGBA-Schnipsel \u2014 auf Wunsch von Hand durchgestrichen
    (zwei wacklige Linien), leicht gedreht wie hastig hingeschrieben."""
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


# Tagline: "Sliders in. .pak out." + die immer wieder korrigierte Zahl.
# Idee des Besitzers (05.09.2026): die urspruengliche 41 steht fest im
# Satz, und alle spaeteren Korrekturen sind drumherum gequetscht - links,
# rechts, oben, unten, schief und kleiner, wie von Hand nachgetragen.
# Direkt vor dem Satz steht die bisher endgueltige Zahl in Bernstein.
# Bewusst unbeholfen; es muss nicht sauber aussehen. Jede weitere Zahl
# bekommt den naechsten Platz aus SLOTS; sind die Plaetze aufgebraucht,
# geht es unter dem Satz nach rechts weiter.
tag_font = font(28, variation="SemiBold")
X0, X_MAX, Y_BASE = 197, 1268, 182
PREFIX = "Sliders in.  .pak out.  "
SUFFIX = " tweaks \u2013 zero modding knowledge needed."
STRUCK_GREY = (128, 130, 134)
GAP_BEFORE = 26      # Luft vor der 41 (fuer die Zahl links davon)
GAP_AFTER = 62       # Luft zwischen 41 und aktueller Zahl (fuer die Zahl dazwischen)
# (dx, dy) relativ zur linken oberen Ecke des 41-Schnipsels, Groesse, Winkel
SLOTS = [
    (60, 7, 22, -11),      # rechts daneben, zwischen 41 und aktueller Zahl
    (30, -23, 20, 9),      # oben rechts, ueber den Rand der 41 geschoben
    (-38, 33, 23, -7),     # unten links
    (30, 35, 23, 5),       # unten rechts
    (-28, -24, 20, 13),    # oben links
    (92, 31, 24, -4),      # weiter unten rechts
]

x = X0
d.text((x, Y_BASE), PREFIX, font=tag_font, fill=GREY)
x += int(d.textlength(PREFIX, font=tag_font)) + GAP_BEFORE
anchor = scribbled_number(STRUCK_NUMBERS[0], 28, STRUCK_GREY, angle=-2.5)
ax, ay = x, Y_BASE - 12
img.paste(anchor, (ax, ay), anchor)
x += anchor.width - 8 + GAP_AFTER
current = scribbled_number(CURRENT_NUMBER, 31, AMBER, strike=False, angle=-2.0)
img.paste(current, (x, Y_BASE - 16), current)
x += current.width - 14
d.text((x, Y_BASE), SUFFIX, font=tag_font, fill=GREY)
if x + int(d.textlength(SUFFIX, font=tag_font)) > X_MAX:
    raise SystemExit("Die Tagline passt nicht mehr ins Bild - PREFIX/SUFFIX kuerzen.")

for i, number in enumerate(STRUCK_NUMBERS[1:]):
    if i < len(SLOTS):
        dx, dy, size, angle = SLOTS[i]
    else:                                   # Nachzuegler: unter dem Satz nach rechts
        k = i - len(SLOTS)
        dx, dy, size, angle = 150 + 66 * k, 32, 20, (-6, 4, -3, 8)[k % 4]
    tile = scribbled_number(number, size, STRUCK_GREY, angle=angle)
    img.paste(tile, (ax + dx, ay + dy), tile)

slider(d, 200, 740, 276, 0.67)
slider(d, 200, 740, 318, 0.29)
slider(d, 200, 740, 358, 0.51)
print(f"Tagline: 41 fest, {len(STRUCK_NUMBERS) - 1} Korrekturen drumherum, "
      f"aktuell {CURRENT_NUMBER}")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("gespeichert:", OUT, img.size)
