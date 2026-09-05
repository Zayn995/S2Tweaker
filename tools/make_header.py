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


# Tagline: "Sliders in. .pak out." + immer wieder durchgestrichene Zahlen.
# Die Zahlen fliessen wie Woerter: was rechts nicht mehr passt, wandert in
# die naechste Zeile (Wunsch des Besitzers, 05.09.2026 - vorher schob die
# Reihe den Satz aus dem Bild). Die aktuelle Zahl und der Satz dahinter
# bleiben immer zusammen. Bei zwei Zeilen ruecken die Slider etwas nach
# unten; reichen zwei Zeilen nicht, werden die Zahlen kleiner gesetzt.
tag_font = font(28, variation="SemiBold")
X0, X_MAX, Y_BASE, LINE_H = 197, 1268, 172, 40
PREFIX = "Sliders in.  .pak out.  "
SUFFIX = " tweaks \u2013 zero modding knowledge needed."


def layout(struck_size: int, current_size: int):
    """Zeilen aus Praefix, Zahlen-Schnipseln und Schlusssatz zusammensetzen.
    Liefert eine Liste von Zeilen; jede Zeile ist eine Liste von
    (x, art, nutzlast, dy)."""
    lines = [[]]
    x = X0
    lines[-1].append((x, "text", PREFIX, 0))
    x += int(d.textlength(PREFIX, font=tag_font))
    for i, number in enumerate(STRUCK_NUMBERS):
        tile = scribbled_number(number, struck_size, (128, 130, 134),
                                angle=(-2.5, 2.0, -1.5)[i % 3])
        if x + tile.width > X_MAX:
            lines.append([])
            x = X0 - 12       # Schnipsel-Rand (14 px) ausgleichen: Ziffer buendig mit "Sliders"
        lines[-1].append((x, "tile", tile, (-12, -17, -9)[i % 3]))
        x += tile.width - 8
    current = scribbled_number(CURRENT_NUMBER, current_size, AMBER,
                               strike=False, angle=-2.0)
    tail = (current.width - 14) + int(d.textlength(SUFFIX, font=tag_font))
    if x + tail > X_MAX:
        lines.append([])
        x = X0 - 12
    lines[-1].append((x, "tile", current, -16))
    x += current.width - 14
    lines[-1].append((x, "text", SUFFIX, 0))
    return lines


lines = layout(28, 31)
if len(lines) > 2:
    lines = layout(23, 31)
if len(lines) > 2:
    raise SystemExit("Zu viele durchgestrichene Zahlen fuer zwei Zeilen - "
                     "STRUCK_NUMBERS kuerzen oder LINE_H/Slider anpassen.")

for row, line in enumerate(lines):
    y = Y_BASE + row * LINE_H
    for x, kind, payload, dy in line:
        if kind == "text":
            d.text((x, y), payload, font=tag_font, fill=GREY)
        else:
            img.paste(payload, (x, y + dy), payload)

# Slider: bei einer Tagline-Zeile wie bisher, bei zwei etwas tiefer, damit
# die zweite Zeile nicht in den ersten Regler laeuft.
slider_ys = (266, 312, 356) if len(lines) == 1 else (282, 322, 358)
slider(d, 200, 740, slider_ys[0], 0.67)
slider(d, 200, 740, slider_ys[1], 0.29)
slider(d, 200, 740, slider_ys[2], 0.51)
print(f"Tagline: {len(lines)} Zeile(n), {len(STRUCK_NUMBERS)} durchgestrichene "
      f"Zahlen, aktuell {CURRENT_NUMBER}")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("gespeichert:", OUT, img.size)
