"""Render data/contributions.json as an animated contribution-graph SVG.

Boxes drop in once on a diagonal sweep (CSS keyframes, no JS), then hold.
Colours follow GitHub's own 0-4 levels, so the scale adapts to your activity.

    python scripts/render_heatmap.py
"""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]  # GitHub's own dark-mode greens, level 0..4
BG, BG2, FRAME, MUTED, TEXT, ACCENT = "#0d1117", "#11161f", "#30363d", "#7d8590", "#e6edf3", "#39d353"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

CELL, GAP = 12, 3
STEP = CELL + GAP
PAD, LEFT, TOP, TITLE_H, FOOT_H = 22, 32, 22, 32, 100
COL_T, ROW_T, DUR = 0.018, 0.045, 0.42  # reveal timing: per column, per row, per box


def grid(days):
    """[(col, row, date, level)] with weeks as columns, Sunday on top, like GitHub."""
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # Monday=0 -> Sunday=0
    out = []
    for d in days:
        col, row = divmod((datetime.date.fromisoformat(d["date"]) - first).days + lead, 7)
        out.append((col, row, d["date"], d["level"]))
    return out


def render(data):
    cells = grid(data["days"])
    cols = cells[-1][0] + 1
    w = PAD + LEFT + cols * STEP - GAP + PAD
    h = TITLE_H + TOP + 7 * STEP + FOOT_H
    gx, gy = PAD + LEFT, TITLE_H + TOP

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">',
        "<style>@keyframes in{from{opacity:0;transform:translateY(-6px)}}"
        f".c{{animation:in {DUR}s cubic-bezier(.2,.8,.2,1) both}}"
        "@media (prefers-reduced-motion:reduce){.c{animation:none}}</style>",
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#bg)"/>',
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLE_H}" x2="{w}" y2="{TITLE_H}" stroke="{FRAME}"/>',
    ]
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{PAD + i * 16}" cy="{TITLE_H / 2}" r="5" fill="{c}"/>')
    p.append(f'<text x="{w / 2}" y="{TITLE_H / 2 + 4}" fill="{MUTED}" font-size="12" text-anchor="middle">'
             f'usman@github: ~/contributions --graph</text>')

    # month labels over the column holding the 1st of each month
    last_label_col = -9
    for col, row, date, _ in cells:
        if date.endswith("-01") and col - last_label_col >= 3:
            month = datetime.date.fromisoformat(date).strftime("%b")
            p.append(f'<text x="{gx + col * STEP}" y="{TITLE_H + 15}" fill="{MUTED}" font-size="10">{month}</text>')
            last_label_col = col
    for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        p.append(f'<text x="{PAD}" y="{gy + row * STEP + 9.5}" fill="{MUTED}" font-size="9">{name}</text>')

    for col, row, _, level in cells:
        p.append(f'<rect class="c" x="{gx + col * STEP}" y="{gy + row * STEP}" width="{CELL}" height="{CELL}" '
                 f'rx="2.5" fill="{LEVELS[min(level, 4)]}" style="animation-delay:{col * COL_T + row * ROW_T:.3f}s"/>')

    # Less [] [] [] [] [] More, right-aligned under the grid
    ly = gy + 7 * STEP + 6
    lx = w - PAD - 34 - len(LEVELS) * STEP
    p.append(f'<text x="{lx - 6}" y="{ly + 9.5}" fill="{MUTED}" font-size="10" text-anchor="end">Less</text>')
    for i, c in enumerate(LEVELS):
        p.append(f'<rect x="{lx + i * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="2.5" fill="{c}"/>')
    p.append(f'<text x="{lx + len(LEVELS) * STEP + 3}" y="{ly + 9.5}" fill="{MUTED}" font-size="10">More</text>')

    sy = ly + CELL + 14
    p.append(f'<line x1="0" y1="{sy}" x2="{w}" y2="{sy}" stroke="{FRAME}"/>')
    best, rng = data["best_day"], data["range"]
    plural = lambda n, word: f"{n:,} {word}{'' if n == 1 else 's'}"
    p += [
        f'<text x="{PAD}" y="{sy + 26}" font-size="13" fill="{MUTED}"><tspan fill="{ACCENT}" font-weight="700">'
        f'{data["total"]:,}</tspan> contributions in the last year</text>',
        f'<text x="{w - PAD}" y="{sy + 26}" font-size="12" fill="{MUTED}" text-anchor="end">'
        f'{rng["start"]} &#8594; {rng["end"]}</text>',
        f'<text x="{PAD}" y="{sy + 52}" font-size="13" fill="{MUTED}">current streak <tspan fill="{TEXT}" '
        f'font-weight="700">{plural(data["current_streak"], "day")}</tspan>   &#183;   longest <tspan fill="{TEXT}" '
        f'font-weight="700">{plural(data["longest_streak"], "day")}</tspan></text>',
        f'<text x="{w - PAD}" y="{sy + 52}" font-size="12" fill="{MUTED}" text-anchor="end">best day '
        f'<tspan fill="{ACCENT}" font-weight="700">{best["count"]}</tspan> on {best["date"]}</text>',
        "</svg>",
    ]
    return "".join(p)


if __name__ == "__main__":
    svg = render(json.loads(IN.read_text()))
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(svg):,} bytes)")
