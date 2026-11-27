#!/usr/bin/env python3
"""Terminal 'install our project' SVG: clone -> pip install -> run -> heatmap.

Same SMIL approach as generate_matrix.py, but the finale is the real
contribution calendar drawn as terminal blocks instead of Matrix rain.

Usage: generate_install.py <username> <output.svg>
"""

import re
import sys
import urllib.request
from datetime import date, timedelta
from xml.sax.saxutils import escape

W, H = 880, 340
TITLE_H = 30
PAD_X = 16
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
CYCLE = 28.0
CELL, GAP = 11, 3
LEVEL_COLORS = ["#1a2420", "#0e4429", "#006d32", "#26a641", "#39d353"]


def fetch_days(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    days = []
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-level="(\d)"', html):
        y, mo, d = (int(x) for x in m.group(1).split("-"))
        days.append((date(y, mo, d), int(m.group(2))))
    if not days:
        for m in re.finditer(r'data-level="(\d)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"', html):
            y, mo, d = (int(x) for x in m.group(2).split("-"))
            days.append((date(y, mo, d), int(m.group(1))))
    days.sort()
    total = None
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    if m:
        total = int(m.group(1).replace(",", ""))
    return days, total


def grid(days):
    """Return list of 53 columns, each a list of 7 levels (Sun..Sat)."""
    if not days:
        return [[0] * 7 for _ in range(53)]
    first = days[0][0]
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    cols = {}
    for d, lvl in days:
        idx = (d - start).days // 7
        row = (d.weekday() + 1) % 7
        cols.setdefault(idx, [0] * 7)[row] = lvl
    out = [cols.get(i, [0] * 7) for i in range(max(cols) + 1)]
    return out[-53:] if len(out) >= 53 else [[0] * 7] * (53 - len(out)) + out


def reveal(t_on, t_off=27.2):
    a = t_on / CYCLE
    b = min(a + 0.004, 0.99)
    c = t_off / CYCLE
    return (
        f'<animate attributeName="opacity" values="0;0;1;1;0" '
        f'keyTimes="0;{a:.3f};{b:.3f};{c:.3f};1" dur="{CYCLE}s" '
        f'repeatCount="indefinite"/>'
    )


def typed_command(x, y, prompt, cmd, t_start, per_char=0.09):
    tspans = [f'<tspan fill="#39ff6a">{escape(prompt)}</tspan>']
    for i, ch in enumerate(cmd):
        tspans.append(
            f'<tspan fill="#e6edf3">{escape(ch)}{reveal(t_start + i * per_char)}</tspan>'
        )
    text = (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="13.5" '
        f'xml:space="preserve">{"".join(tspans)}</text>'
    )
    cx = x + (len(prompt) + len(cmd)) * 8.1 + 2
    cursor = (
        f'<g>{reveal(0.0, t_off=t_start + len(cmd) * per_char + 0.4)}'
        f'<rect x="{cx:.0f}" y="{y - 11}" width="8" height="15" fill="#39ff6a">'
        f'<animate attributeName="opacity" values="1;0;1" dur="1s" '
        f'repeatCount="indefinite"/></rect></g>'
    )
    return text + cursor


def out_line(x, y, text, fill, t_on):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="12.5" '
        f'fill="{fill}" xml:space="preserve">{escape(text)}{reveal(t_on)}</text>'
    )


def build_svg(user, cols, total):
    p_home = f"{user}@arch ~ $ "
    p_proj = f"{user}@arch ~/solvd-solver $ "
    y = TITLE_H + 26
    term = [
        typed_command(PAD_X, y, p_home,
                      "git clone https://github.com/rixa/solvd-solver",
                      t_start=0.5, per_char=0.055),
        out_line(PAD_X, y + 19, "Cloning into 'solvd-solver'... done.",
                 "#8b949e", 3.4),
        typed_command(PAD_X, y + 38, p_home,
                      "cd solvd-solver && pip install -r requirements.txt",
                      t_start=3.9, per_char=0.055),
        out_line(PAD_X, y + 57, "Successfully installed web3-7.14.0 requests-2.32.3",
                 "#8b949e", 6.9),
        typed_command(PAD_X, y + 76, p_proj, "python3 solve.py --daily",
                      t_start=7.4, per_char=0.08),
        out_line(PAD_X, y + 95, "[ok] puzzle solved in 0.42s", "#39ff6a", 9.6),
        typed_command(PAD_X, y + 114, p_proj, "./contributions.sh",
                      t_start=10.1, per_char=0.08),
        out_line(PAD_X, y + 133,
                 f":: {total} contributions in the last year",
                 "#39ff6a", 11.8),
    ]
    # heatmap finale: columns fade in left -> right
    gx, gy = PAD_X + 6, y + 152
    cells = []
    for i, col in enumerate(cols):
        rects = []
        for r, lvl in enumerate(col):
            rects.append(
                f'<rect x="{gx + i * (CELL + GAP)}" y="{gy + r * (CELL + GAP)}" '
                f'width="{CELL}" height="{CELL}" rx="2" fill="{LEVEL_COLORS[lvl]}"/>'
            )
        cells.append(f'<g>{reveal(12.3 + i * 0.045)}{"".join(rects)}</g>')
    legend = (
        f'<g>{reveal(15.0)}'
        f'<text x="{gx}" y="{gy + 7 * (CELL + GAP) + 16}" font-family="{FONT}" '
        f'font-size="11" fill="#8b949e">Less</text>'
        + "".join(
            f'<rect x="{gx + 36 + k * (CELL + GAP)}" y="{gy + 7 * (CELL + GAP) + 6}" '
            f'width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>'
            for k, c in enumerate(LEVEL_COLORS)
        )
        + f'<text x="{gx + 36 + 5 * (CELL + GAP) + 4}" y="{gy + 7 * (CELL + GAP) + 16}" '
          f'font-family="{FONT}" font-size="11" fill="#8b949e">More</text></g>'
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Terminal installing solvd-solver, showing {user} GitHub contributions">
<defs><clipPath id="panel"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="10"/></clipPath></defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="10" fill="#0c0f0d" stroke="#1e3a24"/>
<g clip-path="url(#panel)">
<rect x="1" y="1" width="{W-2}" height="{TITLE_H}" fill="#161b18"/>
<circle cx="20" cy="{TITLE_H//2 + 1}" r="6" fill="#ff5f56"/>
<circle cx="40" cy="{TITLE_H//2 + 1}" r="6" fill="#ffbd2e"/>
<circle cx="60" cy="{TITLE_H//2 + 1}" r="6" fill="#27c93f"/>
<text x="{W//2}" y="{TITLE_H//2 + 5}" font-family="{FONT}" font-size="12" fill="#8b949e" text-anchor="middle">{user}@archlinux: ~</text>
{''.join(term)}
{''.join(cells)}
{legend}
</g>
</svg>'''


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "rixa"
    out = sys.argv[2] if len(sys.argv) > 2 else "install.svg"
    days, total = fetch_days(user)
    cols = grid(days)
    svg = build_svg(user, cols, total)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out}: {len(days)} days, total={total}, cols={len(cols)}, {len(svg)} bytes")


if __name__ == "__main__":
    main()
