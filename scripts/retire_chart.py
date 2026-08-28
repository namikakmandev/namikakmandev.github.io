#!/usr/bin/env python3
"""The one chart for the 4% rule post.

Ending wealth after a 30-year retirement drawing 4% a year, by the year the
retirement began. The point of the picture: the rule's entire failure record is
one cluster. Six retirements ran out of money and all six started between 1964
and 1969. Everyone else finished with something, and a few finished rich.

It also shows what the rule's overlapping windows really look like — the line is
smooth because neighbouring retirements share 29 of their 30 years, which is why
"95% of all historical periods" is not 95 independent tests.

Numbers come from data/retire-results.json, written by retire_4pct.py.
Reuses the PNG rasteriser from fte_chart.py. Stdlib only.

  python3 scripts/retire_chart.py
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import render_png                                # noqa: E402

BLUE, ORANGE, RED = "#2f9bff", "#ff6500", "#d92b2b"
INK, DIM, GRID, PAPER = "#1f2430", "#5b6472", "#d6dce4", "#ffffff"
W, H = 1600, 1000
L, R, T, B = 120, 60, 155, 150
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")
YMAX = 5.5


def main():
    res = json.load(open("data/retire-results.json"))
    pts = res["by_start_year"]
    fails = [p for p in pts if not p["survived"]]
    y0, y1 = pts[0]["year"], pts[-1]["year"]
    pw, ph = W - L - R, H - T - B

    def x(year):
        return L + (year - y0) / (y1 - y0) * pw

    def y(v):
        return T + (1 - min(v, YMAX) / YMAX) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<text x="{L}" y="56" font-size="38" font-weight="700" fill="{INK}">'
         f'Every 4% retirement that ran out of money began in the same six '
         f'years</text>',
         f'<text x="{L}" y="98" font-size="23" fill="{DIM}">'
         f'What you had left after a 30-year retirement drawing 4% a year, '
         f'inflation-adjusted, from a 50/50 portfolio.</text>',
         f'<text x="{L}" y="128" font-size="23" fill="{DIM}">'
         f'One dot per starting year, {y0}&#8211;{y1}. Replication of Bengen '
         f'(1994) and the Trinity Study (1998) on Shiller&#8217;s data.</text>']

    # grid
    for i in range(int(YMAX) + 1):
        o.append(f'<line x1="{L}" y1="{y(i):.1f}" x2="{L + pw}" y2="{y(i):.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{L - 16}" y="{y(i) + 8:.1f}" font-size="21" '
                 f'fill="{DIM}" text-anchor="end">{i}&#215;</text>')
    for yr in range(1880, y1 + 1, 20):
        o.append(f'<line x1="{x(yr):.1f}" y1="{T}" x2="{x(yr):.1f}" '
                 f'y2="{T + ph}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{x(yr):.1f}" y="{T + ph + 38}" font-size="21" '
                 f'fill="{DIM}" text-anchor="middle">{yr}</text>')

    # "you ended with what you started" reference
    o.append(f'<line x1="{L}" y1="{y(1):.1f}" x2="{L + pw}" y2="{y(1):.1f}" '
             f'stroke="{DIM}" stroke-width="2.5" stroke-dasharray="9 7"/>')

    # the failure band
    fx0, fx1 = x(fails[0]["year"]) - 6, x(fails[-1]["year"]) + 6
    o.append(f'<rect x="{fx0:.1f}" y="{T}" width="{fx1 - fx0:.1f}" '
             f'height="{ph}" fill="{RED}" opacity="0.10"/>')

    # the series
    d = " ".join(f"{'M' if i == 0 else 'L'}{x(p['year']):.1f},{y(p['ending']):.1f}"
                 for i, p in enumerate(pts))
    o.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="3.2" '
             f'stroke-linejoin="round"/>')
    for p in pts:
        c = RED if not p["survived"] else BLUE
        o.append(f'<circle cx="{x(p["year"]):.1f}" cy="{y(p["ending"]):.1f}" '
                 f'r="{6.5 if not p["survived"] else 3.4}" fill="{c}"/>')

    # callouts
    cx = (fx0 + fx1) / 2
    o += [f'<text x="{cx:.1f}" y="{y(3.55):.1f}" font-size="25" '
          f'font-weight="700" fill="{RED}" text-anchor="middle">'
          f'{len(fails)} failures</text>',
          f'<text x="{cx:.1f}" y="{y(3.30):.1f}" font-size="22" '
          f'fill="{RED}" text-anchor="middle">'
          f'{fails[0]["year"]}&#8211;{fails[-1]["year"]}</text>',
          f'<text x="{cx:.1f}" y="{y(3.06):.1f}" font-size="20" '
          f'fill="{DIM}" text-anchor="middle">of {len(pts)} starting '
          f'years</text>']

    # the best case, labelled to the left so it cannot run off the canvas
    best = max(pts, key=lambda p: p["ending"])
    o += [f'<text x="{x(best["year"]) - 16:.1f}" y="{y(best["ending"]) + 7:.1f}" '
          f'font-size="20" fill="{DIM}" text-anchor="end">retired '
          f'{best["year"]}: finished with {best["ending"]:.1f}&#215;</text>']

    # legend, parked in the empty top-left block
    lx, ly = x(1884), y(5.15)
    o += [f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{lx + 44:.1f}" y2="{ly:.1f}" '
          f'stroke="{DIM}" stroke-width="2.5" stroke-dasharray="9 7"/>',
          f'<text x="{lx + 58:.1f}" y="{ly + 7:.1f}" font-size="21" '
          f'fill="{DIM}">ended with what they started with</text>',
          f'<circle cx="{lx + 22:.1f}" cy="{y(4.75):.1f}" r="6.5" '
          f'fill="{RED}"/>',
          f'<text x="{lx + 58:.1f}" y="{y(4.75) + 7:.1f}" font-size="21" '
          f'fill="{DIM}">ran out of money</text>']

    # axis labels + source
    o += [f'<text x="{L + pw / 2:.0f}" y="{T + ph + 82}" font-size="24" '
          f'fill="{INK}" text-anchor="middle">the year the retirement '
          f'began</text>',
          f'<text x="30" y="{T + ph / 2:.0f}" font-size="24" fill="{INK}" '
          f'text-anchor="middle" transform="rotate(-90 30 '
          f'{T + ph / 2:.0f})">wealth left after 30 years</text>',
          f'<text x="{L}" y="{H - 26}" font-size="18" fill="{DIM}">'
          f'Data: Robert Shiller&#8217;s series via github.com/datasets/'
          f's-and-p-500, government bonds  &#183;  method, limitations and '
          f'every number: namikakmandev.github.io/four-percent-rule.html</text>',
          '</svg>']

    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/four-percent-rule.svg"
    svg = "\n".join(o)
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    render_png(svg, "assets/linkedin/four-percent-rule.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
