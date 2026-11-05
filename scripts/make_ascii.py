"""Turn a portrait on a plain light background into a self-typing ASCII-art SVG.

One ink colour on a dark terminal window. Each row is wiped in left to right with
a block cursor riding the edge, top to bottom, then it holds (SMIL, no JS).
Run once per photo; the result is committed.

    python scripts/make_ascii.py [photo] [out.svg]
"""
import html
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "photo.jpg"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "portrait.svg"

# calibration knobs, tuned by eye for assets/photo.jpg
CROP = (132, 110, 932, 910)  # square around head and shoulders; None = whole photo
BG_CUTOFF = 0.90             # pixels lighter than this are background (photo is on near-white)
LINE_WEIGHT = 0.55           # how hard edges (eyes, brows, beard line) are pushed darker
GAMMA = 1.4                  # >1 darkens mid-tones (sparser skin), <1 brightens them
# Positive image on a dark terminal: bright skin prints dense, dark hair/suit prints as
# faint dots, the background prints nothing. (A negative made black hair/suit glow.)
RAMP = " .`:-=+*cs#%@"       # sparse (dark) -> dense (bright); index 0 is reserved for background

COLS = int(os.environ.get("COLS", 180))
ART_W = 800
CELL_W = ART_W / COLS
CELL_H = CELL_W * 15 / 8       # monospace glyphs are ~1.875x taller than wide
ROWS = round(COLS * 8 / 15)    # keeps the art square
PAD, TITLE_H, STATUS_H = 20, 30, 34
W, H = ART_W + 2 * PAD, TITLE_H + ROWS * CELL_H + STATUS_H + PAD

BG, BG2, FRAME, MUTED, INK, ACCENT = "#0d1117", "#11161f", "#30363d", "#7d8590", "#c9d1d9", "#e8ff2a"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
PRINT_SECONDS = 5.5            # whole portrait prints in this long, at any resolution
STATIC = bool(os.environ.get("STATIC"))  # STATIC=1 -> finished frame, no animation (for previews)


def blur(a, r):
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255


def to_rows(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("L")
    if CROP:
        im = im.crop(CROP)
    g = np.asarray(im, np.float32) / 255
    subject = blur((g < BG_CUTOFF).astype(np.float32), 2) > 0.5

    # stretch contrast over the subject only, so the white background doesn't eat the range
    eq = np.asarray(ImageOps.equalize(im, Image.fromarray(subject.astype(np.uint8) * 255)), np.float32) / 255
    # darken thin dark strokes that averaging would wash out at character size
    lines = np.clip((blur(eq, 5) - blur(eq, 1.2)) * 4, 0, 1)
    tone = np.clip(eq - LINE_WEIGHT * lines, 0, 1)

    def shrink(a):
        return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((COLS, ROWS), Image.LANCZOS),
                          np.float32) / 255

    lum = shrink(tone) ** GAMMA
    on_subject = shrink(subject.astype(np.float32)) > 0.5
    idx = 1 + np.clip((lum * (len(RAMP) - 2) + 0.5).astype(int), 0, len(RAMP) - 2)
    idx[~on_subject] = 0
    return ["".join(RAMP[i] for i in row) for row in idx]


def render(rows):
    row_dur = PRINT_SECONDS / len(rows)
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" '
        f'font-family="{FONT}">',
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H:.0f}" rx="12" fill="url(#bg)"/>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1:.0f}" rx="12" fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{FRAME}"/>',
    ]
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{PAD + i * 16}" cy="{TITLE_H / 2}" r="5" fill="{c}"/>')
    p.append(f'<text x="{W / 2}" y="{TITLE_H / 2 + 4}" fill="{MUTED}" font-size="12" text-anchor="middle">'
             f'usman@github: ~$ ./portrait.sh</text>')

    fs = CELL_H * 0.86
    # a no-op filter makes browsers smooth the text in grey; without it Windows ClearType
    # paints the tiny glyphs with red/blue fringes and the portrait looks like rainbow static
    p.append('<filter id="gray"><feOffset dx="0" dy="0"/></filter><g filter="url(#gray)">')
    for r, line in enumerate(rows):
        if not line.strip():
            continue  # blank rows need no markup
        top = TITLE_H + r * CELL_H
        t0 = r * row_dur
        # textLength pins every row to the same width whatever monospace font the viewer has
        text = (f'xml:space="preserve" x="{PAD}" y="{top + CELL_H * 0.78:.1f}" fill="{INK}" '
                f'font-size="{fs:.2f}" textLength="{ART_W}" lengthAdjust="spacing">{html.escape(line)}</text>')
        if STATIC:
            p.append("<text " + text)
            continue
        p.append(
            f'<clipPath id="r{r}"><rect x="{PAD}" y="{top:.1f}" width="0" height="{CELL_H:.2f}">'
            f'<animate attributeName="width" from="0" to="{ART_W}" begin="{t0:.3f}s" dur="{row_dur:.3f}s" '
            f'fill="freeze"/></rect></clipPath>'
            f'<text clip-path="url(#r{r})" {text}'
            f'<rect y="{top + 1:.1f}" width="{CELL_W:.2f}" height="{CELL_H - 2:.2f}" fill="{ACCENT}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + ART_W}" begin="{t0:.3f}s" dur="{row_dur:.3f}s" '
            f'fill="freeze"/><set attributeName="opacity" to="0.9" begin="{t0:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{t0 + row_dur:.3f}s"/></rect>'
        )
    p.append("</g>")

    # status bar: prompt + name + blinking cursor
    sy = TITLE_H + ROWS * CELL_H + 8
    prompt, name = "usman@github:~$ whoami ", "Usman Masood"
    text_w = (len(prompt) + len(name)) * 13 * 0.6
    p += [
        f'<line x1="0" y1="{sy:.1f}" x2="{W}" y2="{sy:.1f}" stroke="{FRAME}"/>',
        f'<text x="{PAD}" y="{sy + 24:.1f}" font-size="13" fill="{MUTED}" textLength="{text_w:.1f}">'
        f'{prompt}<tspan fill="{INK}">{name}</tspan></text>',
        f'<rect x="{PAD + text_w + 4:.1f}" y="{sy + 12:.1f}" width="8" height="15" fill="{ACCENT}">'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.51;1" dur="1s" '
        f'begin="{PRINT_SECONDS:.1f}s" repeatCount="indefinite"/></rect>',
        "</svg>",
    ]
    return "".join(p)


if __name__ == "__main__":
    rows = to_rows(SRC)
    svg = render(rows)
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(svg):,} bytes, {COLS}x{ROWS}, {W}x{H:.0f})")
