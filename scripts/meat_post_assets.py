#!/usr/bin/env python3
"""Meat-vs-food post package: A4 one-pager + public share page.

Imports scripts/meat_grid.py (which regenerates notes/meat-post.html), so all
assets share one computation from data/meat-cpi-eu.json + data/meat-cpi-us.json.

Outputs:
  notes/meat-onepager.html  A4 one-pager (render to PDF with Chromium)
  meat-vs-food.html         public share page at the site root
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meat_grid as M  # noqa: E402

ROOT = M.ROOT

BLUE = "#2F6BE0"; ORANGE = "#FF6500"; INK = "#1b2230"; DIM = "#5e6675"
LINE = "#e6e9ef"; SOFT = "#f6f8fb"

n_up = sum(1 for _, _, e in M.panels if e > 1)
n_down = sum(1 for _, _, e in M.panels if e < -1)
n_flat = len(M.panels) - n_up - n_down
top = M.panels[0]; bottom = M.panels[-1]


def light_mini(r, endv):
    W, Hh = 170, 62
    keys = sorted(r)
    vals = [r[k] for k in keys]
    lo, hi = min(vals + [98]) - 2, max(vals + [102]) + 2
    X = lambda i: i / (len(vals) - 1) * W
    Y = lambda v: Hh - 4 - (v - lo) / (hi - lo) * (Hh - 8)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    colour = ORANGE if endv > 1 else BLUE if endv < -1 else "#8a93a0"
    return (f'<svg viewBox="0 0 {W} {Hh}">'
            f'<line x1="0" y1="{Y(100):.1f}" x2="{W}" y2="{Y(100):.1f}" '
            f'stroke="{LINE}" stroke-width="1"/>'
            f'<polyline points="{pts}" fill="none" stroke="{colour}" '
            f'stroke-width="1.8" stroke-linejoin="round"/></svg>'), colour


cells = []
for g, r, endv in M.panels:
    svg, colour = light_mini(r, endv)
    cells.append(
        f'<div class="cell"><div class="ch"><span>'
        f'<svg class="flag" viewBox="0 0 24 16">{M.FLAGS[g]}</svg>'
        f'{M.H.esc(M.NAMES[g])}</span>'
        f'<span style="color:{colour}">{endv:+.0f}%</span></div>{svg}</div>')

ONE = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Meat vs the food basket — one-pager</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  color:{INK}; background:#fff; }}
.page {{ width:210mm; height:297mm; padding:12mm 13mm; }}
.top {{ display:flex; justify-content:space-between; align-items:flex-end;
  border-bottom:3px solid {BLUE}; padding-bottom:8px; margin-bottom:12px; }}
.top h1 {{ font-size:19px; letter-spacing:-.02em; }}
.top .co {{ color:{DIM}; font-size:10.5px; margin-bottom:3px; }}
.top .per {{ text-align:right; color:{DIM}; font-size:10px; line-height:1.5; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:10px; }}
.kpi {{ background:{SOFT}; border:1px solid {LINE}; border-radius:8px; padding:7px 10px; }}
.kpi .l {{ font-size:8.5px; color:{DIM}; text-transform:uppercase; letter-spacing:.05em; }}
.kpi .v {{ font-size:15px; font-weight:700; margin-top:2px; }}
.kpi .d {{ font-size:9px; margin-top:2px; color:{DIM}; }}
.legend {{ font-size:9.5px; color:{DIM}; margin-bottom:8px; }}
.legend i {{ display:inline-block; width:18px; height:3px; border-radius:2px;
  margin:0 4px 0 10px; vertical-align:middle; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:6px 12px;
  margin-bottom:10px; }}
.cell > svg {{ width:100%; height:auto; display:block; }}
.ch {{ display:flex; justify-content:space-between; align-items:center;
  font-size:9.5px; font-weight:700; margin-bottom:1px; }}
.ch span:first-child {{ display:flex; align-items:center; gap:4px; }}
.flag {{ width:13px; height:9px; border-radius:1.5px; flex:none;
  outline:1px solid rgba(0,0,0,.12); outline-offset:-1px; }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:6px; }}
h2 {{ font-size:9.5px; text-transform:uppercase; letter-spacing:.06em; color:{BLUE};
  margin-bottom:5px; border-bottom:1px solid {LINE}; padding-bottom:3px; }}
.notes p {{ font-size:9.3px; line-height:1.42; margin-bottom:5px; }}
.foot {{ margin-top:8px; border-top:1px solid {LINE}; padding-top:6px;
  display:flex; justify-content:space-between; color:{DIM}; font-size:8.6px; }}
</style></head><body><div class="page">
  <div class="top">
    <div><div class="co">namikakmandev.github.io · personal analysis of public statistics</div>
      <h1>Meat vs the food basket — 28 markets, 2021–2025</h1></div>
    <div class="per">Namık Akman<br>August 2026</div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="l">Meat outpaced food</div><div class="v">{n_up} of 28</div>
      <div class="d">markets, Jan 2021 → Dec 2025</div></div>
    <div class="kpi"><div class="l">Meat fell behind</div><div class="v">{n_down} of 28</div>
      <div class="d">{n_flat} ended flat (within ±1%)</div></div>
    <div class="kpi"><div class="l">Top</div><div class="v">{M.NAMES[top[0]]} {top[2]:+.0f}%</div>
      <div class="d">meat vs the rest of the basket</div></div>
    <div class="kpi"><div class="l">Bottom</div><div class="v">{M.NAMES[bottom[0]]} {bottom[2]:+.0f}%</div>
      <div class="d">meat got relatively cheaper</div></div>
  </div>
  <div class="legend">Each panel: price of meat ÷ price of the whole food
  basket, Jan 2021 = 100, own scale.<i style="background:{ORANGE}"></i>meat
  outpaced food<i style="background:{BLUE}"></i>meat fell behind. Number =
  change by Dec 2025.</div>
  <div class="grid">{''.join(cells)}</div>
  <div class="cols notes">
    <div><h2>Reading</h2>
      <p><b>Why a ratio.</b> Dividing the meat index by the food index cancels
      the general inflation level, so a high-inflation market (Türkiye) and a
      low-inflation one (Ireland) are compared on the same footing.</p>
      <p><b>Definitions.</b> EU/EEA/Türkiye: HICP class CP0112 "Meat"
      (fresh, frozen and processed meat incl. poultry) vs CP011 "Food".
      US: BLS "meats, poultry, fish and eggs" vs "food at home" — a wider
      basket than the EU meat class, stated wherever shown.</p></div>
    <div><h2>Sources</h2>
      <p>Eurostat prc_hicp_midx, monthly, 2015=100 — CP0112 and CP011, 27
      geos incl. Türkiye. US: BLS CPI via FRED, monthly, NSA —
      CUUR0000SAF112 and CUUR0000SAF11. Data files: data/meat-cpi-eu.json ·
      data/meat-cpi-us.json, cut 13 Aug 2026 — every figure recomputable
      from them.</p></div>
  </div>
  <div class="foot"><span>Full-size chart: namikakmandev.github.io/meat-vs-food.html</span>
    <span>Views my own · not investment advice</span></div>
</div></body></html>"""
open(os.path.join(ROOT, "notes", "meat-onepager.html"), "w").write(ONE)

# ---------------------------------------------------------------- share page
slide = open(os.path.join(ROOT, "notes", "meat-post.html")).read()
body = slide.split("</style>", 1)[1]
css = slide.split("<style>", 1)[1].split("</style>", 1)[0]
share = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meat vs the food basket — 28 markets, 2021–2025</title>
<meta name="description" content="The price of meat relative to the whole
food basket, per country, Eurostat HICP and US BLS CPI, 2021–2025.">
<style>{css}
body {{ display:block; padding:24px 0 60px; }}
.bar {{ max-width:1080px; margin:0 auto 14px; padding:0 16px; display:flex;
  justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; }}
.bar a {{ color:#3987e5; text-decoration:none; font-size:15px; }}
.bar a:hover {{ text-decoration:underline; }}
.bar .home {{ color:#9aa3ad; }}
.wrap {{ display:flex; justify-content:center; }}
.slide {{ transform-origin:top center; }}
@media (max-width:1100px) {{ .slide {{ transform:scale(calc(96vw / 1080px)); }} }}
</style></head><body>
<div class="bar">
  <a class="home" href="/">← namikakman — projects</a>
  <a href="notes/meat-onepager.pdf" download>Download the one-pager (PDF)</a>
</div>
<div class="wrap">{body}</div>
<script>
function fit() {{ const k = Math.min(1, document.documentElement.clientWidth * 0.96 / 1080);
  const s = document.querySelector('.slide'); s.style.transform = `scale(${{k}})`;
  document.querySelector('.wrap').style.height = (1350 * k) + 'px'; }}
addEventListener('resize', fit); fit();
</script>
</body></html>"""
open(os.path.join(ROOT, "meat-vs-food.html"), "w").write(share)
print("wrote one-pager + share page")
