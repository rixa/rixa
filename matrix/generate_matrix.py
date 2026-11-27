#!/usr/bin/env python3
"""Generate a terminal-style Matrix-rain SVG from a GitHub contribution calendar.

A fake terminal window runs a staged dev session (cd, ls, ./run-daily.sh,
git push), then the "result" is Matrix rain where each column is one week
of contributions (brighter/faster = more active). Animation is pure SMIL so
it runs behind GitHub's camo image proxy. Static attributes are the
finished state, so the file still looks right if SMIL never runs.

Usage: generate_matrix.py <username> <output.svg>
No third-party deps.
"""

import random
import re
import sys
import urllib.request
from datetime import date, timedelta
from xml.sax.saxutils import escape

GLYPHS = "01234567890123456789<>/\\|+=*#%@:;01"

W, H = 880, 380
TITLE_H = 30
PAD_X = 16
COLS = 53
COL_W = (W - 2 * PAD_X) / COLS
CHAR_H = 15
RAIN_Y = 262
ROWS = (H - RAIN_Y - 12) // CHAR_H
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
CYCLE = 28.0  # seconds per full loop


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


def weekly_levels(days):
    if not days:
        return [0] * COLS
    first = days[0][0]
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    weeks = {}
    for d, lvl in days:
        idx = (d - start).days // 7
        weeks[idx] = weeks.get(idx, 0) + lvl
    out = [weeks.get(i, 0) for i in range(max(weeks) + 1)]
    return out[-COLS:] if len(out) >= COLS else [0] * (COLS - len(out)) + out


def col_color(intensity):
    if intensity <= 0.02:
        return ("#7dffa0", "#1d7a33", "#0a3315")
    if intensity < 0.35:
        return ("#baffcb", "#2ee65c", "#0d4d1e")
    if intensity < 0.7:
        return ("#e2ffe9", "#4dff7a", "#12702a")
    return ("#ffffff", "#7dff9e", "#1a8f38")


def stream(x, rng, head, mid, tail, opacity, dur, begin):
    n = ROWS + 2
    chars = [rng.choice(GLYPHS) for _ in range(n)]
    parts = []
    for copy in range(2):
        tspans = []
        for i, ch in enumerate(chars):
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
        y0 = RAIN_Y + copy * n * CHAR_H - CHAR_H
        parts.append(
            f'<text x="{x:.1f}" y="{y0}" font-family="{FONT}" font-size="13" '
            f'text-anchor="middle">{"".join(tspans)}</text>'
        )
    block_h = n * CHAR_H
    base_off = -rng.uniform(0, block_h)
    return (
        f'<g opacity="{opacity:.2f}" transform="translate(0 {base_off:.0f})">'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="0 0" to="0 -{block_h}" dur="{dur:.1f}s" begin="{begin:.1f}s" '
        f'repeatCount="indefinite"/>{"".join(parts)}</g>'
    )


def reveal(t_on, t_off=27.2):
    """SMIL opacity animation: hidden until t_on (s), visible, gone at loop end."""
    a = t_on / CYCLE
    b = min(a + 0.004, 0.99)
    c = t_off / CYCLE
    return (
        f'<animate attributeName="opacity" values="0;0;1;1;0" '
        f'keyTimes="0;{a:.3f};{b:.3f};{c:.3f};1" dur="{CYCLE}s" '
        f'repeatCount="indefinite"/>'
    )


def typed_command(x, y, prompt, cmd, t_start=0.6, per_char=0.11):
    """Prompt (always in cycle) + command chars revealed one by one."""
    tspans = [f'<tspan fill="#39ff6a">{escape(prompt)}</tspan>']
    for i, ch in enumerate(cmd):
        t = t_start + i * per_char
        tspans.append(
            f'<tspan fill="#e6edf3">{escape(ch)}{reveal(t)}</tspan>'
        )
    text = (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="13.5" '
        f'xml:space="preserve">{"".join(tspans)}</text>'
    )
    # blinking block cursor, visible while typing
    char_w = 8.1
    cx = x + (len(prompt) + len(cmd)) * char_w + 2
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


def build_svg(user, weeks, total):
    rng_bg = random.Random(f"{user}-bg")
    rain = []
    for _ in range(18):
        x = rng_bg.uniform(10, W - 10)
        rain.append(stream(x, rng_bg, "#9dffb4", "#1f8f3d", "#0a3315",
                           opacity=0.16, dur=rng_bg.uniform(14, 26),
                           begin=-rng_bg.uniform(0, 20)))
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
        rain.append(stream(x, rng, head, mid, tail, opacity, max(dur, 4),
                           begin=-rng.uniform(0, 18)))
    rain_group = (
        f'<g clip-path="url(#rainclip)">{reveal(9.7, t_off=27.2)}{"".join(rain)}</g>'
    )

    p_home = f"{user}@arch ~ $ "
    p_code = f"{user}@arch ~/code $ "
    y = TITLE_H + 26
    term = [
        typed_command(PAD_X, y, p_home, "cd ~/code", t_start=0.5, per_char=0.1),
        typed_command(PAD_X, y + 19, p_code, "ls", t_start=1.8, per_char=0.1),
        out_line(PAD_X, y + 38, "florin  solvd-solver  unsolvable-solver  bug-hunt",
                 "#58a6ff", 2.3),
        typed_command(PAD_X, y + 57, p_code, "./run-daily.sh",
                      t_start=2.9, per_char=0.1),
        out_line(PAD_X, y + 76, "[ok] florin session ok", "#39ff6a", 4.6),
        out_line(PAD_X, y + 95, "[ok] robinhood dex ok", "#39ff6a", 5.1),
        out_line(PAD_X, y + 114, "[ok] bug hunt check-in ok", "#39ff6a", 5.6),
        typed_command(PAD_X, y + 133, p_code, "git push origin main",
                      t_start=6.2, per_char=0.09),
        out_line(PAD_X, y + 152, "Enumerating objects: 5, done.", "#8b949e", 8.3),
        out_line(PAD_X, y + 171, "main -> main [ok]", "#39ff6a", 8.7),
        out_line(PAD_X, y + 190,
                 f":: {total} contributions in the last year — rendering...",
                 "#39ff6a", 9.2),
    ]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Terminal installing matrix rain of {user} GitHub contributions">
<defs>
<clipPath id="panel"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="10"/></clipPath>
<clipPath id="rainclip"><rect x="1" y="{RAIN_Y - 6}" width="{W-2}" height="{H - RAIN_Y - 2}"/></clipPath>
</defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="10" fill="#0c0f0d" stroke="#1e3a24"/>
<g clip-path="url(#panel)">
<rect x="1" y="1" width="{W-2}" height="{TITLE_H}" fill="#161b18"/>
<circle cx="20" cy="{TITLE_H//2 + 1}" r="6" fill="#ff5f56"/>
<circle cx="40" cy="{TITLE_H//2 + 1}" r="6" fill="#ffbd2e"/>
<circle cx="60" cy="{TITLE_H//2 + 1}" r="6" fill="#27c93f"/>
<text x="{W//2}" y="{TITLE_H//2 + 5}" font-family="{FONT}" font-size="12" fill="#8b949e" text-anchor="middle">{user}@archlinux: ~</text>
{''.join(term)}
{rain_group}
</g>
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
