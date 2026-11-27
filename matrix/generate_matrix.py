#!/usr/bin/env python3
"""Generate a Matrix-rain SVG from a GitHub contribution calendar.

Each week of the last year becomes one falling column of glyphs.
Brighter/faster columns = more active weeks. Animation is pure SMIL
(animateTransform) so it runs behind GitHub's camo image proxy.

Usage: generate_matrix.py <username> <output.svg>
No third-party deps: fetches the public contributions HTML and parses
data-date / data-level attributes.
"""

import random
import re
import sys
import urllib.request
from datetime import date, timedelta
from xml.sax.saxutils import escape

GLYPHS = "01234567890123456789<>/\\|+=*#%@:;01"

W, H = 880, 230
PAD_X = 14
COLS = 53
COL_W = (W - 2 * PAD_X) / COLS
CHAR_H = 15
ROWS = (H - 34) // CHAR_H  # leave room for caption line
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"


def fetch_days(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    days = []
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"', html):
        y, mo, d = (int(x) for x in m.group(1).split("-"))
        days.append((date(y, mo, d), int(m.group(2))))
    if not days:  # attribute order flipped
        for m in re.finditer(r'data-level="(\d)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"', html):
            y, mo, d = (int(x) for x in m.group(2).split("-"))
            days.append((date(y, mo, d), int(m.group(1))))
    days.sort()
    total = None
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    if m:
        total = int(m.group(1).replace(",", ""))
    return days, total


def weekly_levels(days):
    if not days:
        return [0] * COLS
    first = days[0][0]
    # align columns to Sundays
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    weeks = {}
    for d, lvl in days:
        idx = (d - start).days // 7
        weeks[idx] = weeks.get(idx, 0) + lvl
    out = [weeks.get(i, 0) for i in range(max(weeks) + 1)]
    return out[-COLS:].rjust(COLS, 0) if len(out) < COLS else out[-COLS:]


def col_color(intensity):
    """intensity 0..1 -> (head, mid, tail) greens."""
    if intensity <= 0.02:
        return ("#7dffa0", "#1d7a33", "#0a3315")
    if intensity < 0.35:
        return ("#baffcb", "#2ee65c", "#0d4d1e")
    if intensity < 0.7:
        return ("#e2ffe9", "#4dff7a", "#12702a")
    return ("#ffffff", "#7dff9e", "#1a8f38")


def stream(x, rng, head, mid, tail, opacity, dur, begin):
    """One seamless falling column: two stacked copies of a glyph block."""
    n = ROWS + 2
    chars = [rng.choice(GLYPHS) for _ in range(n)]
    parts = []
    for copy in range(2):
        tspans = []
        for i, ch in enumerate(chars):
            # i=0 is top (tail), last is bottom (head)
            frac = i / max(n - 1, 1)
            if i == n - 1:
                fill, op = head, 1.0
            elif frac > 0.55:
                fill, op = mid, 0.45 + 0.55 * frac
            else:
                fill, op = tail, 0.12 + 0.5 * frac
            tspans.append(
                f'<tspan x="{x:.1f}" dy="{CHAR_H}" fill="{fill}" '
                f'fill-opacity="{op:.2f}">{escape(ch)}</tspan>'
            )
        y0 = copy * n * CHAR_H - CHAR_H
        parts.append(
            f'<text x="{x:.1f}" y="{y0}" font-family="{FONT}" font-size="13" '
            f'text-anchor="middle">{"".join(tspans)}</text>'
        )
    block_h = n * CHAR_H
    base_off = -rng.uniform(0, block_h)  # static state: frozen mid-fall
    return (
        f'<g opacity="{opacity:.2f}" transform="translate(0 {base_off:.0f})">'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="0 0" to="0 -{block_h}" dur="{dur:.1f}s" begin="{begin:.1f}s" '
        f'repeatCount="indefinite"/>{"".join(parts)}</g>'
    )


def build_svg(user, weeks, total):
    rng_bg = random.Random(f"{user}-bg")
    body = []
    # faint background rain (decorative, data-independent)
    for _ in range(18):
        x = rng_bg.uniform(10, W - 10)
        body.append(stream(x, rng_bg, "#9dffb4", "#1f8f3d", "#0a3315",
                           opacity=0.16, dur=rng_bg.uniform(14, 26),
                           begin=-rng_bg.uniform(0, 20)))
    # data columns
    max_lvl = max(weeks) if weeks else 1
    for i, lvl in enumerate(weeks):
        x = PAD_X + COL_W * i + COL_W / 2
        inten = min(lvl / max(max_lvl, 1), 1.0)
        head, mid, tail = col_color(inten)
        rng = random.Random(f"{user}-w{i}")
        if lvl == 0:
            opacity, dur = 0.5, rng.uniform(20, 30)
        else:
            opacity = 0.55 + 0.45 * inten
            dur = 16 - 10 * inten + rng.uniform(-1.5, 1.5)
        body.append(stream(x, rng, head, mid, tail, opacity, max(dur, 4),
                           begin=-rng.uniform(0, 18)))
    caption = f"$ contributions --last-year: {total}" if total is not None else "$ contributions --last-year"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Matrix rain of {user} GitHub contributions">
<defs><clipPath id="panel"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="10"/></clipPath></defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="10" fill="#04070a" stroke="#1e3a24"/>
<g clip-path="url(#panel)">
{''.join(body)}
<rect x="1" y="{H-30}" width="{W-2}" height="29" fill="#04070a" fill-opacity="0.85"/>
</g>
<text x="16" y="{H-11}" font-family="{FONT}" font-size="12" fill="#39ff6a">{caption}<animate attributeName="opacity" values="1;1;0.35;1" keyTimes="0;0.7;0.85;1" dur="2.4s" repeatCount="indefinite"/></text>
</svg>'''


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "rixa"
    out = sys.argv[2] if len(sys.argv) > 2 else "matrix.svg"
    days, total = fetch_days(user)
    weeks = weekly_levels(days)
    svg = build_svg(user, weeks, total)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out}: {len(days)} days, total={total}, weeks={len(weeks)}, {len(svg)} bytes")


if __name__ == "__main__":
    main()
