#!/usr/bin/env python3
"""The one chart for the ECB forecaster post.

For each year: what share of the ECB's professional forecasters had the actual
inflation outcome inside their OWN stated 80% confidence range, measured from
the survey taken a year earlier.

An honest 80% range should contain the outcome 80% of the time — the dashed
line. The bars sit well below it, and in four years they vanish entirely: 2008,
2021, 2022 and 2023, where not one forecaster in the panel contained the
outcome. Those are the financial crisis and the inflation shock. The years the
bars reach the top are the years nobody needed a forecast.

Numbers come from data/ecb-spf-results.json. Reuses the PNG rasteriser from
fte_chart.py. Stdlib only.

  python3 scripts/ecb_chart.py
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import render_png                                # noqa: E402

BLUE, RED, DIM = "#2f9bff", "#d92b2b", "#5b6472"
INK, GRID, PAPER = "#1f2430", "#d6dce4", "#ffffff"
W, H = 1600, 1000
L, R, T, B = 110, 55, 165, 150
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")


def main():
    res = json.load(open("data/ecb-spf-results.json"))
    rows = [r for r in res["by_year"] if r["n"]]
    zero = set(res["zero_years"])
    pw, ph = W - L - R, H - T - B
    n = len(rows)
    slot = pw / n
    bw = slot * 0.68

    def x(i):
        return L + i * slot + (slot - bw) / 2

    def y(v):
        return T + (1 - v) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<text x="{L}" y="52" font-size="37" font-weight="700" fill="{INK}">'
         f'When Europe&#8217;s forecasters say they are 80% sure, they are '
         f'right 53% of the time</text>',
         f'<text x="{L}" y="94" font-size="23" fill="{DIM}">'
         f'Share of ECB Survey of Professional Forecasters panellists whose own '
         f'80% range contained actual euro-area inflation,</text>',
         f'<text x="{L}" y="124" font-size="23" fill="{DIM}">'
         f'from the survey taken one year earlier. '
         f'{res["n_distributions"]:,} individual forecasts, '
         f'{res["n_forecasters"]} forecasters, 2000&#8211;2025.</text>']

    for g in (0, 0.25, 0.5, 0.75, 1.0):
        o.append(f'<line x1="{L}" y1="{y(g):.1f}" x2="{L + pw}" '
                 f'y2="{y(g):.1f}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{L - 14}" y="{y(g) + 8:.1f}" font-size="21" '
                 f'fill="{DIM}" text-anchor="end">{g * 100:.0f}%</text>')

    # what an honest 80% range would look like
    o += [f'<line x1="{L}" y1="{y(0.8):.1f}" x2="{L + pw}" y2="{y(0.8):.1f}" '
          f'stroke="{INK}" stroke-width="2.5" stroke-dasharray="9 7"/>',
          f'<text x="{L + pw * 0.34:.0f}" y="{y(0.8) - 13:.1f}" '
          f'font-size="21" font-weight="600" fill="{INK}">'
          f'an honest 80% range would sit here</text>']

    for i, r in enumerate(rows):
        share, yr = r["share"], r["year"]
        col = RED if yr in zero else BLUE
        if share > 0:
            o.append(f'<rect x="{x(i):.1f}" y="{y(share):.1f}" '
                     f'width="{bw:.1f}" height="{(1 - share) * 0 + y(0) - y(share):.1f}" '
                     f'fill="{col}" rx="3"/>')
        else:
            # a zero bar is invisible; mark it so it reads as "none", not "no data"
            o.append(f'<rect x="{x(i):.1f}" y="{y(0) - 5:.1f}" '
                     f'width="{bw:.1f}" height="5" fill="{RED}"/>')
        if yr % 5 == 0 or yr in zero:
            o.append(f'<text x="{x(i) + bw / 2:.1f}" y="{T + ph + 30}" '
                     f'font-size="20" fill="{RED if yr in zero else DIM}" '
                     f'font-weight="{"700" if yr in zero else "400"}" '
                     f'text-anchor="middle">{yr}</text>')

    # call out the four total failures
    zi = [i for i, r in enumerate(rows) if r["year"] in zero]
    if zi:
        cx = x(zi[0]) + bw / 2
        o += [f'<text x="{cx:.1f}" y="{y(0.30):.1f}" font-size="24" '
              f'font-weight="700" fill="{RED}">not one forecaster</text>',
              f'<text x="{cx:.1f}" y="{y(0.30) + 30:.1f}" font-size="21" '
              f'fill="{RED}">in the whole panel</text>',
              f'<text x="{cx:.1f}" y="{y(0.30) + 58:.1f}" font-size="20" '
              f'fill="{DIM}">2008 &#183; 2021 &#183; 2022 &#183; 2023</text>']
        for i in zi:
            o.append(f'<line x1="{x(i) + bw / 2:.1f}" y1="{y(0.0) - 10:.1f}" '
                     f'x2="{x(i) + bw / 2:.1f}" y2="{y(0.22):.1f}" '
                     f'stroke="{RED}" stroke-width="1.5" '
                     f'stroke-dasharray="4 4"/>')

    o += [f'<text x="{L + pw / 2:.0f}" y="{T + ph + 78}" font-size="24" '
          f'fill="{INK}" text-anchor="middle">the year being forecast</text>',
          f'<text x="{L}" y="{H - 26}" font-size="18" fill="{DIM}">'
          f'Data: ECB Survey of Professional Forecasters, individual responses, '
          f'data.ecb.europa.eu  &#183;  method and every number: '
          f'namikakmandev.github.io/ecb-forecasts.html</text>',
          '</svg>']

    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/ecb-forecasts.svg"
    svg = "\n".join(o)
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    render_png(svg, "assets/linkedin/ecb-forecasts.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
