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

W, H = 880, 364
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


def cell_reveal(t_on, t_off):
    """Fade in at t_on, stay, then vanish quickly at t_off (hunter pass)."""
    a = t_on / CYCLE
    b = min(a + 0.004, 0.99)
    c = t_off / CYCLE
    d = min(c + 0.012, 0.995)
    return (
        f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
        f'keyTimes="0;{a:.3f};{b:.3f};{c:.3f};{d:.3f};1" dur="{CYCLE}s" '
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


SPRITE = [
    "...HHHHHH...",
    "..HHHHHHHH..",
    "....SSSS....",
    "....SEES....",
    "....SSSS....",
    "..TTTTTTTT..",
    "..TTTTTTTT..",
    ".STTTTTTTTS.",
    "....PPPP....",
    "....PPPP....",
    "...PP..PP...",
    "...BB..BB...",
]
SPRITE_COLORS = {
    "H": "#f5c542", "S": "#ffd9a0", "E": "#111111",
    "T": "#ff8c42", "P": "#3b82f6", "B": "#5b3a29",
}
PX = 2.4


def hunter_sprite():
    rects = []
    for r, row in enumerate(SPRITE):
        for c, ch in enumerate(row):
            if ch in SPRITE_COLORS:
                rects.append(
                    f'<rect x="{c * PX:.1f}" y="{r * PX:.1f}" width="{PX}" '
                    f'height="{PX}" fill="{SPRITE_COLORS[ch]}"/>'
                )
    net = (
        f'<line x1="{11 * PX:.0f}" y1="{7 * PX:.0f}" x2="{15 * PX:.0f}" '
        f'y2="{3 * PX:.0f}" stroke="#c0c0c0" stroke-width="2"/>'
        f'<circle cx="{16.5 * PX:.0f}" cy="{2.2 * PX:.0f}" r="{3.2 * PX:.0f}" '
        f'fill="#ffffff" fill-opacity="0.08" stroke="#e6edf3" stroke-width="1.6"/>'
    )
    return "".join(rects) + net


def hunter_sweep(gx, gy, grid_w, grid_h, active_days):
    """Hunter walks left->right across the grid, scanning each column."""
    t0, t1 = 15.0, 25.0
    x0, x1 = gx - 34, gx + grid_w - 6
    feet_y = gy + grid_h + 4
    sprite_h = len(SPRITE) * PX
    # per-column flash when the hunter passes
    flashes = []
    for i in range(53):
        cx = gx + i * (CELL + GAP) + CELL / 2
        ti = t0 + (t1 - t0) * (cx - x0) / (x1 - x0)
        a, b, c = ti / CYCLE, min(ti / CYCLE + 0.012, 0.99), min(ti / CYCLE + 0.05, 0.995)
        flashes.append(
            f'<rect x="{gx + i * (CELL + GAP) - 1}" y="{gy - 2}" '
            f'width="{CELL + 2}" height="{grid_h + 4}" rx="3" fill="#7dff9e" '
            f'opacity="0"><animate attributeName="opacity" values="0;0;0.35;0" '
            f'keyTimes="0;{a:.3f};{b:.3f};{c:.3f}" dur="{CYCLE}s" '
            f'repeatCount="indefinite"/></rect>'
        )
    scan = (
        f'<rect x="-8" y="{-grid_h - 6}" width="{CELL + 6}" height="{grid_h + 4}" '
        f'fill="#39ff6a" opacity="0.10"/>'
    )
    mid_x = gx + grid_w / 2
    hunter = (
        f'<g transform="translate({mid_x:.0f} {feet_y:.0f})">{reveal(t0)}'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{x0:.0f} {feet_y:.0f};{x0:.0f} {feet_y:.0f};'
        f'{x1:.0f} {feet_y:.0f};{x1:.0f} {feet_y:.0f}" '
        f'keyTimes="0;{t0 / CYCLE:.3f};{t1 / CYCLE:.3f};1" dur="{CYCLE}s" '
        f'repeatCount="indefinite"/>'
        f'{scan}'
        f'<g transform="translate(0 {-sprite_h:.0f})">'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0 {-sprite_h:.0f};0 {-sprite_h - 2:.0f};0 {-sprite_h:.0f}" '
        f'dur="0.5s" repeatCount="indefinite" additive="sum"/>'
        f'{hunter_sprite()}</g></g>'
    )
    status = out_line(
        gx, gy + grid_h + 38,
        f"[ok] scan complete — {active_days} active days, 0 bugs escaped",
        "#39ff6a", 25.3,
    )
    return "".join(flashes) + hunter + status


def build_svg(user, cols, total, active_days):
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
    # heatmap finale: columns fade in left -> right, then vanish as the
    # hunter sweeps past them
    gx, gy = PAD_X + 6, y + 152
    grid_w = 53 * (CELL + GAP)
    hx0, hx1 = gx - 34, gx + grid_w - 6
    cells = []
    for i, col in enumerate(cols):
        rects = []
        for r, lvl in enumerate(col):
            rects.append(
                f'<rect x="{gx + i * (CELL + GAP)}" y="{gy + r * (CELL + GAP)}" '
                f'width="{CELL}" height="{CELL}" rx="2" fill="{LEVEL_COLORS[lvl]}"/>'
            )
        cx = gx + i * (CELL + GAP) + CELL / 2
        t_pass = 15.0 + 10.0 * (cx - hx0) / (hx1 - hx0)
        cells.append(
            f'<g>{cell_reveal(12.3 + i * 0.045, t_pass)}{"".join(rects)}</g>'
        )
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
{hunter_sweep(gx, gy, 53 * (CELL + GAP), 7 * (CELL + GAP), active_days)}
</g>
</svg>'''


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "rixa"
    out = sys.argv[2] if len(sys.argv) > 2 else "install.svg"
    days, total = fetch_days(user)
    cols = grid(days)
    active_days = sum(1 for _, lvl in days if lvl > 0)
    svg = build_svg(user, cols, total, active_days)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out}: {len(days)} days, total={total}, cols={len(cols)}, {len(svg)} bytes")


if __name__ == "__main__":
    main()
