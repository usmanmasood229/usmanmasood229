"""Render a neofetch-style info card SVG. Edit LINES below, then re-run.

Same window size as the ASCII portrait so the two sit side by side at equal height.
Each line fades in on a short stagger (CSS keyframes, no JS).

    python scripts/make_info_card.py        STATIC=1 for a finished frame
"""
import html
import os
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "info-card.svg"

# (key, value). key "" = continuation line, None = blank line
LINES = [
    ("Role", "Full Stack & AI Automation Engineer"),
    ("Company", "Mantaq"),
    ("Frontend", "Next.js · React · React Native"),
    ("Backend", "Node · Fastify · PostgreSQL · Supabase"),
    ("Cloud", "AWS"),
    ("AI", "OpenAI · n8n · AI agents · WhatsApp bots"),
    ("Edu", "SZABIST, class of 2026"),
    None,
    ("Worked on", ""),
    ("", "› HIPAA claims platform, web + mobile"),
    ("", "› HR automation on 20+ n8n workflows"),
    ("", "› Grant receipt reconciliation app"),
    ("", "› Compliance portal with a workflow builder"),
    ("", "› Self-hosted AI agent team on AWS"),
    None,
    ("Site", "usman-portfolio-snowy.vercel.app"),
]

W, H = 840, 884                     # matches portrait.svg
PAD, TITLE_H, STATUS_H = 40, 30, 46
FS, LINE_H, KEY_W = 23, 38, 160
BG, BG2, FRAME, MUTED, INK, ACCENT = "#0d1117", "#11161f", "#30363d", "#7d8590", "#c9d1d9", "#e8ff2a"
SWATCHES = ["#ff5f56", "#ffbd2e", "#27c93f", "#e8ff2a", "#58a6ff", "#bc8cff", "#39c5cf", "#c9d1d9"]
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
START, STAGGER = 0.3, 0.09          # seconds before the first line, between lines
STATIC = bool(os.environ.get("STATIC"))


def render():
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
        "" if STATIC else  # resting state is the finished card, so reduced motion just skips the show
        "<style>@media (prefers-reduced-motion:no-preference){@keyframes in{from{opacity:0;transform:translateX(-10px)}}"
        ".l{animation:in .45s ease-out both}@keyframes blink{50%{opacity:0}}.b{animation:blink 1s step-end 2s 5}}</style>",
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
        f'<stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{FRAME}"/>',
    ]
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{20 + i * 16}" cy="{TITLE_H / 2}" r="5" fill="{c}"/>')
    p.append(f'<text x="{W / 2}" y="{TITLE_H / 2 + 4}" fill="{MUTED}" font-size="12" text-anchor="middle">'
             f'usman@github:~$ neofetch</text>')

    n = 0  # animated element counter, drives the stagger

    def line(body):
        nonlocal n
        p.append(f'<g class="l" style="animation-delay:{START + n * STAGGER:.2f}s">{body}</g>')
        n += 1

    y = TITLE_H + 62
    line(f'<text x="{PAD}" y="{y}" font-size="{FS + 3}" font-weight="700" fill="{ACCENT}" textLength="{12 * (FS + 3) * 0.6:.0f}">usman'
            f'<tspan fill="{MUTED}">@</tspan>github</text>')
    y += 22
    line(f'<line x1="{PAD}" y1="{y}" x2="{PAD + 12 * (FS + 3) * 0.6:.0f}" y2="{y}" stroke="{MUTED}" '
            f'stroke-width="2" stroke-dasharray="6 4"/>')
    y += 14

    for item in LINES:
        y += LINE_H
        if item is None:
            y -= LINE_H // 2
            continue
        key, value = (html.escape(s) for s in item)
        body = ""
        if key:
            body += f'<text x="{PAD}" y="{y}" font-size="{FS}" font-weight="700" fill="{ACCENT}">{key}</text>'
        if value:
            x = PAD + (KEY_W if key else 24)
            body += f'<text x="{x}" y="{y}" font-size="{FS}" fill="{INK}">{value}</text>'
        line(body)

    y += 66
    sw = 44
    line("".join(f'<rect x="{PAD + i * sw}" y="{y - 26}" width="{sw}" height="26" fill="{c}"/>'
                    for i, c in enumerate(SWATCHES)))

    # status bar, mirrors the portrait's
    sy = H - STATUS_H
    p += [
        f'<line x1="0" y1="{sy}" x2="{W}" y2="{sy}" stroke="{FRAME}"/>',
        f'<text x="20" y="{sy + 24}" font-size="13" fill="{MUTED}" textLength="{15 * 13 * 0.6:.1f}">usman@github:~$</text>',
        f'<rect class="b" x="{20 + 16 * 13 * 0.6:.1f}" y="{sy + 12}" width="8" height="15" fill="{ACCENT}"/>',
        "</svg>",
    ]
    if y > sy - 20:
        raise SystemExit(f"card content overflows into the status bar (y={y}, bar at {sy}); trim LINES")
    return "".join(p)


if __name__ == "__main__":
    svg = render()
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(svg):,} bytes)")
