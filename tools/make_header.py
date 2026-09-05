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


# Tagline. Der Satz "Sliders in.  .pak out.  41 tweaks - zero modding
# knowledge needed." ist der MASTER (Vorgabe des Besitzers, 05.09.2026):
# er steht woertlich und an fester Stelle, die 41 durchgestrichen. Alle
# spaeteren Zahlen - die durchgestrichenen UND die aktuelle in Bernstein -
# sind Nachtraege, die sich dazwischenquetschen: erst um die 41 herum,
# dann ueber und unter den naechsten Woertern des Satzes. Wo die aktuelle
# Zahl landet, ergibt sich aus der Anzahl der Nachtraege; ob am Ende
# jemand die Tweak-Zahl ablesen kann, ist egal. Es geht um die vielen
# Aenderungen, und es darf unbeholfen aussehen.
tag_font = font(28, variation="SemiBold")
X0, X_MAX, Y_BASE = 197, 1268, 186
PREFIX = "Sliders in.  .pak out.  "
SUFFIX = " tweaks \u2013 zero modding knowledge needed."
STRUCK_GREY = (128, 130, 134)

x = X0
d.text((x, Y_BASE), PREFIX, font=tag_font, fill=GREY)
x += int(d.textlength(PREFIX, font=tag_font))
anchor = scribbled_number(STRUCK_NUMBERS[0], 28, STRUCK_GREY, angle=-2.5)
ax, ay = x - 12, Y_BASE - 12            # Schnipsel-Rand ausgleichen: 41 im Textfluss
img.paste(anchor, (ax, ay), anchor)
x += anchor.width - 18
suffix_x = x
d.text((x, Y_BASE), SUFFIX, font=tag_font, fill=GREY)
if x + int(d.textlength(SUFFIX, font=tag_font)) > X_MAX:
    raise SystemExit("Der Master-Satz passt nicht mehr ins Bild - PREFIX/SUFFIX kuerzen.")


def word_x(word: str) -> int:
    """Linke Kante eines Wortes des Satzes im Bild (Praefix oder Schluss)."""
    if word in PREFIX:
        return X0 + int(d.textlength(PREFIX[:PREFIX.index(word)], font=tag_font))
    return suffix_x + int(d.textlength(SUFFIX[:SUFFIX.index(word)], font=tag_font))


# Plaetze fuer Nachtraege, in der Reihenfolge, in der sie belegt werden:
# (x, y, Groesse, Winkel). Erst die vier Ecken der 41, danach ueber und
# unter den Woertern - immer das naechstgelegene freie Wort zuerst,
# abwechselnd rechts und links der 41. Wo die aktuelle Zahl landet, ist
# damit einfach der naechste freie Platz.
ABOVE, BELOW = ay - 27, ay + 32
SLOTS = [
    (ax - 32, ABOVE + 1, 20, 11),             # ueber der 41, links
    (ax + 18, ABOVE - 4, 20, -8),             # ueber der 41, rechts
    (ax - 38, BELOW, 22, -6),                 # unter der 41, links
    (ax + 22, BELOW + 3, 22, 7),              # unter der 41, rechts
]
# "out." fehlt absichtlich: der Platz darueber/darunter gehoert schon den
# linken Ecken der 41.
NEAREST_FIRST = ("tweaks", ".pak", "zero", "in.", "modding", "Sliders",
                 "knowledge", "needed")
for k, word in enumerate(NEAREST_FIRST):
    wx = word_x(word) + (30 if word in SUFFIX else -4)
    SLOTS.append((wx, ABOVE - 2 + 5 * (k % 2), 20, (5, -5, 10, -7, 4, -9, 6, -3)[k]))
    SLOTS.append((wx + 6, BELOW + 2 - 4 * (k % 2), 22, (-9, 8, -4, 6, -8, 5, -7, 9)[k]))

later = [(n, True) for n in STRUCK_NUMBERS[1:]] + [(CURRENT_NUMBER, False)]
if len(later) > len(SLOTS):
    raise SystemExit(f"{len(later)} Nachtraege, aber nur {len(SLOTS)} Plaetze - "
                     "SLOTS in tools/make_header.py erweitern.")
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
print(f"Master-Satz fest (41), {len(later)} Nachtraege auf {len(SLOTS)} Plaetzen; "
      f"aktuell {CURRENT_NUMBER} sitzt auf Platz {len(later)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("gespeichert:", OUT, img.size)
