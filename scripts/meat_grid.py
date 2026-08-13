#!/usr/bin/env python3
"""Draft post image: relative price of meat vs the rest of the food basket.
-> notes/meat-post-draft.html (one 1080x1350 slide, 28 panels)

Metric: ratio of HICP meat (CP0112) to HICP food (CP011), both re-based to
Jan 2021 = 100 — unitless, so it is comparable across all inflation levels,
including Türkiye's. A line above 100 means meat outpacing the food basket.

Data: data/meat-cpi-eu.json (Eurostat) + data/meat-cpi-us.json (BLS via FRED).
US basket caveat: SAF112 is 'meats, poultry, fish and eggs' — wider than
EU CP0112 (meat incl. poultry); stated on the image.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vetcpi_carousel_html as H  # flags + esc + house palette conventions

ROOT = H.ROOT
S = H.S

FLAGS = dict(H.FLAGS)
FLAGS["SK"] = (H.FLAGS["SK"]
               + '<path d="M5,4.5 h4.6 v4.6 l-2.3,2.2 l-2.3,-2.2 Z" fill="#EE1620" '
                 'stroke="#fff" stroke-width="0.5"/>'
                 '<path d="M7.3,5.3 v4.2 M5.9,6.4 h2.8 M6.1,7.8 h2.4" stroke="#fff" '
                 'stroke-width="0.65" fill="none"/>')
FLAGS.update({
    "IE": H._rects((0, 0, 8, 16, "#169B62"), (8, 0, 8, 16, "#fff"),
                   (16, 0, 8, 16, "#FF883E")),
    "LU": H._rects((0, 0, 24, 5.33, "#EF3340"), (0, 5.33, 24, 5.33, "#fff"),
                   (0, 10.67, 24, 5.33, "#00A2E1")),
    "SI": H._rects((0, 0, 24, 5.33, "#fff"), (0, 5.33, 24, 5.33, "#005DA4"),
                   (0, 10.67, 24, 5.33, "#ED1C24"))
          + '<path d="M4.5,2.5 h4.6 v3.6 l-2.3,2.4 l-2.3,-2.4 Z" fill="#005DA4" '
            'stroke="#fff" stroke-width="0.5"/>'
            '<path d="M5.3,6 l1.5,-1.7 l0.8,0.9 l0.6,-0.7 l1.4,1.5" stroke="#fff" '
            'stroke-width="0.6" fill="none"/>',
    "HR": H._rects((0, 0, 24, 5.33, "#FF0000"), (0, 5.33, 24, 5.33, "#fff"),
                   (0, 10.67, 24, 5.33, "#171796")),
    "LT": H._rects((0, 0, 24, 5.33, "#FDB913"), (0, 5.33, 24, 5.33, "#006A44"),
                   (0, 10.67, 24, 5.33, "#C1272D")),
    "LV": H._rects((0, 0, 24, 6.4, "#9E3039"), (0, 6.4, 24, 3.2, "#fff"),
                   (0, 9.6, 24, 6.4, "#9E3039")),
    "EE": H._rects((0, 0, 24, 5.33, "#0072CE"), (0, 5.33, 24, 5.33, "#000"),
                   (0, 10.67, 24, 5.33, "#fff")),
})
NAMES = {**H.GNAMES, "IE": "Ireland", "LU": "Luxembourg", "SI": "Slovenia",
         "HR": "Croatia", "LT": "Lithuania", "LV": "Latvia", "EE": "Estonia",
         "TR": "Türkiye"}

EU = json.load(open(os.path.join(ROOT, "data", "meat-cpi-eu.json")))["series"]
USD = json.load(open(os.path.join(ROOT, "data", "meat-cpi-us.json")))["series"]

FRM, TO = "2021-01", "2025-12"
GEOS = ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL", "CZ", "HU", "RO",
        "PT", "DK", "SE", "FI", "TR", "EL", "SK", "SI", "HR", "BG", "LT",
        "LV", "EE", "NO", "IE", "LU"]


def ratio_series(meat, food):
    keys = sorted(k for k in meat if FRM <= k <= TO and k in food)
    base = (meat[FRM] / food[FRM])
    return {k: (meat[k] / food[k]) / base * 100 for k in keys}


panels = [(g, ratio_series(EU[f"{g}|CP0112"], EU[f"{g}|CP011"])) for g in GEOS]
panels.append(("US", ratio_series(USD["meat_pfe_nsa"], USD["food_home_nsa"])))
panels = [(g, r, r[max(r)] - 100) for g, r in panels]
panels.sort(key=lambda p: -p[2])


def mini(r, endv):
    W, Hh, LBL = 230, 96, 15
    keys = sorted(r)
    vals = [r[k] for k in keys]
    lo, hi = min(vals + [98]) - 2, max(vals + [102]) + 2
    X = lambda i: i / (len(keys) - 1) * W
    Y = lambda v: Hh - LBL - 3 - (v - lo) / (hi - lo) * (Hh - LBL - 8)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    colour = S["orange"] if endv > 1 else S["blue"] if endv < -1 else S["ink2"]
    return (f'<svg viewBox="0 0 {W} {Hh}">'
            f'<line x1="0" y1="{Y(100):.1f}" x2="{W}" y2="{Y(100):.1f}" '
            f'stroke="{S["grid"]}" stroke-width="1.2"/>'
            f'<polyline points="{pts}" fill="none" stroke="{colour}" '
            f'stroke-width="2.4" stroke-linejoin="round"/>'
            f'<text x="0" y="{Hh - 2}" fill="{S["muted"]}" font-size="14">2021</text>'
            f'<text x="{W}" y="{Hh - 2}" fill="{S["muted"]}" font-size="14" '
            f'text-anchor="end">2025</text></svg>'), colour


cells = []
for g, r, endv in panels:
    svg, colour = mini(r, endv)
    cells.append(
        f'<div class="cell"><div class="ch"><span>'
        f'<svg class="flag" viewBox="0 0 24 16">{FLAGS[g]}</svg>{H.esc(NAMES[g])}</span>'
        f'<span style="color:{colour}">{endv:+.0f}%</span></div>{svg}</div>')

html = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meat vs the food basket — draft</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#06090c; font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;
  color:{S['ink']}; display:flex; justify-content:center; padding:20px 0; }}
.slide {{ width:1080px; height:1350px; background:{S['surface']}; position:relative;
  padding:80px 80px; }}
.rule {{ position:absolute; top:64px; left:80px; width:86px; height:5px;
  border-radius:3px; background:{S['blue']}; }}
.kicker {{ color:{S['blue']}; font-weight:700; font-size:22px; letter-spacing:.05em;
  margin:14px 0 14px; }}
h1 {{ font-size:47px; line-height:1.12; margin-bottom:12px; }}
p.lead {{ font-size:21.5px; line-height:1.38; color:{S['ink2']}; margin-bottom:16px; }}
p.lead b {{ color:{S['ink']}; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px 22px; }}
.cell > svg {{ width:100%; height:auto; display:block; }}
.ch {{ display:flex; justify-content:space-between; align-items:center;
  font-size:16.5px; font-weight:700; margin-bottom:2px; }}
.ch span:first-child {{ display:flex; align-items:center; gap:7px; }}
.flag {{ width:23px; height:15px; border-radius:2.5px; flex:none;
  outline:1px solid rgba(255,255,255,.14); outline-offset:-1px; }}
.ch span:last-child {{ font-variant-numeric:tabular-nums; font-size:15.5px; }}
.note {{ position:absolute; left:80px; right:80px; bottom:96px; font-size:15px;
  color:{S['muted']}; line-height:1.4; }}
.footer {{ position:absolute; left:80px; right:80px; bottom:32px; display:flex;
  justify-content:space-between; align-items:flex-end; color:{S['ink2']};
  font-size:19px; }}
.footer small {{ color:{S['muted']}; font-size:15px; }}
</style>
<div class="slide" id="s1">
  <div class="rule"></div>
  <div class="kicker">MEAT VS THE FOOD BASKET · 28 MARKETS · 2021 → 2025</div>
  <h1>Did meat get expensive — or did everything?</h1>
  <p class="lead">Each line: the price of meat <b>relative to the whole food
  basket</b> (Jan 2021 = 100). <span style="color:{S['orange']}">Orange — meat
  outpaced food</span>; <span style="color:{S['blue']}">blue — meat fell
  behind</span>. The number is the change by Dec 2025.</p>
  <div class="grid">{''.join(cells)}</div>
  <div class="note">Ratio of two price indices (meat ÷ food), so it is
  comparable across all inflation levels — Türkiye included. Own scale per
  panel. Sources: Eurostat HICP, CP0112 meat vs CP011 food · US: BLS CPI,
  meats/poultry/fish/eggs vs food at home (wider basket than the EU meat
  class — stated, not hidden). Own analysis of public data.</div>
  <div class="footer">
    <span><b>Namık Akman</b><br><small>namikakmandev.github.io</small></span>
  </div>
</div>
"""
open(os.path.join(ROOT, "notes", "meat-post-draft.html"), "w").write(html)
print("wrote notes/meat-post-draft.html —", len(panels), "panels")
