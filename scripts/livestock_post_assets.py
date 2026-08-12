#!/usr/bin/env python3
"""Final LinkedIn assets for the livestock insurance study.

Outputs:
  notes/livestock-ins-post.html   1080x1350 slide (screenshot to PNG at 2x)
  notes/livestock-ins-onepager.html  A4 one-pager (render to PDF)

Data comes via scripts/livestock_ins_page.py so the assets, the study page
and the committed data files can never disagree.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import livestock_ins_page as L  # noqa: E402  (also regenerates the study page)

ROOT = L.ROOT
S = L.S

# ---------------------------------------------------------------- post slide
tr_chart = L.line_chart([("share of herd", L.PEN, S["green"])],
                        lambda v: f"{v:.0f}%", [0, 10, 20, 30, 40],
                        "Share of Turkish cattle herd insured",
                        W=940, H=300, PADR=230)
us_chart = L.line_chart([("head insured", {y: v / 1e6 for y, v in L.US_HEAD.items()},
                          S["blue"])],
                        lambda v: f"{v:.0f}M", [0, 2, 4, 6],
                        "US cattle head insured under LRP",
                        W=940, H=300, PADR=230, xstep=4)

pen13, pen24 = L.PEN["2013"], L.PEN["2024"]
us15 = L.US_HEAD["2015"] / 1e6
us24 = L.US_HEAD["2024"] / 1e6

POST = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Who insures the herd — post image</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#06090c; font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;
  color:{S['ink']}; display:flex; justify-content:center; padding:20px 0; }}
.slide {{ width:1080px; height:1350px; background:{S['surface']}; position:relative;
  padding:86px 84px; }}
.rule {{ position:absolute; top:70px; left:84px; width:86px; height:5px;
  border-radius:3px; background:{S['blue']}; }}
.kicker {{ color:{S['blue']}; font-weight:700; font-size:23px; letter-spacing:.05em;
  margin:16px 0 20px; }}
h1 {{ font-size:56px; line-height:1.15; margin-bottom:20px; }}
p.lead {{ font-size:24px; line-height:1.4; color:{S['ink2']}; margin-bottom:20px; }}
h2 {{ font-size:27px; margin:6px 0 4px; }}
h2 small {{ font-size:19px; color:{S['ink2']}; font-weight:400; }}
.chart svg {{ width:100%; height:auto; display:block; }}
p.fig {{ font-size:19px; color:{S['ink2']}; margin:2px 0 14px; }}
p.fig b {{ color:{S['ink']}; }}
.note {{ position:absolute; left:84px; right:84px; bottom:116px; font-size:17px;
  color:{S['muted']}; line-height:1.42; }}
.footer {{ position:absolute; left:84px; right:84px; bottom:36px; display:flex;
  justify-content:space-between; align-items:flex-end; color:{S['ink2']};
  font-size:20px; }}
.footer span small {{ color:{S['muted']}; font-size:16px; }}
</style>
<div class="slide" id="s1">
  <div class="rule"></div>
  <div class="kicker">LIVESTOCK INSURANCE · TÜRKİYE &amp; UNITED STATES</div>
  <h1>Who insures the herd?</h1>
  <p class="lead">Two countries, two different products — mortality cover in
  Türkiye, price cover in the US. Both took off within the same few years.</p>

  <h2>Türkiye <small>— share of the cattle herd insured (TARSİM,
  mortality &amp; disease cover)</small></h2>
  <div class="chart">{tr_chart}</div>
  <p class="fig"><b>{pen13:.0f}% (2013) → {pen24:.0f}% (2024)</b> of the national
  cattle herd. 2025 insured head: 10.0M; herd figure not yet published.</p>

  <h2>United States <small>— cattle head insured (USDA LRP, price
  cover)</small></h2>
  <div class="chart">{us_chart}</div>
  <p class="fig"><b>{us15:.1f}M (2015) → {us24:.1f}M head (2024)</b> — about 7% of
  the Jan-1 cattle inventory. In both countries the take-off follows an
  expansion of the premium subsidy.</p>

  <div class="note">Different products — never summed or ranked against each
  other. Sources: TARSİM annual reports (insured head, key-figures tables) ·
  TÜİK/FAOSTAT herd · USDA RMA livestock participation files (net head,
  LRP feeder + fed cattle). Own analysis of public data.</div>
  <div class="footer">
    <span><b>Namık Akman</b><br><small>namikakmandev.github.io/livestock-insurance.html</small></span>
  </div>
</div>
"""
open(os.path.join(ROOT, "notes", "livestock-ins-post.html"), "w").write(POST)

# ---------------------------------------------------------------- one-pager
BLUE = "#2F6BE0"; ORANGE = "#FF6500"; GREEN = "#0E8A5F"; INK = "#1b2230"
DIM = "#5e6675"; LINE = "#e6e9ef"; SOFT = "#f6f8fb"


def light_chart(series, colour, y_fmt, y_ticks, W=430, H=210):
    vals = list(series.values())
    ylo, yhi = 0, max(vals) * 1.12
    years = sorted(int(y) for y in series)
    X = lambda t: (t - years[0]) / (years[-1] - years[0]) * (W - 20)
    Y = lambda v: H - 26 - v / yhi * (H - 40)
    out = [f'<svg viewBox="0 0 {W} {H}">']
    for yt in y_ticks:
        if yt > yhi: continue
        out.append(f'<line x1="0" y1="{Y(yt):.0f}" x2="{W - 14}" y2="{Y(yt):.0f}" '
                   f'stroke="{LINE}" stroke-width="1"/>')
        out.append(f'<text x="2" y="{Y(yt) - 4:.0f}" fill="#9aa2af" font-size="11">'
                   f'{y_fmt(yt)}</text>')
    pts = " ".join(f"{X(int(y)):.1f},{Y(v):.1f}" for y, v in sorted(series.items()))
    out.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
               f'stroke-width="2.6" stroke-linejoin="round"/>')
    for yr in (years[0], years[-1]):
        anch = "start" if yr == years[0] else "end"
        out.append(f'<text x="{X(yr):.0f}" y="{H - 8}" fill="#77808c" font-size="12" '
                   f'text-anchor="{anch}">{yr}</text>')
    out.append("</svg>")
    return "".join(out)


op_tr = light_chart(L.PEN, GREEN, lambda v: f"{v:.0f}%", [0, 20, 40])
op_us = light_chart({y: v / 1e6 for y, v in L.US_HEAD.items()}, BLUE,
                    lambda v: f"{v:.0f}M", [0, 3, 6])
op_lr = light_chart(L.LR_POOL, ORANGE, lambda v: f"{v:.0f}%", [0, 40, 80])
lr25 = L.LR_POOL["2025"]

ONE = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Livestock insurance — one-pager</title>
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
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:14px; }}
.kpi {{ background:{SOFT}; border:1px solid {LINE}; border-radius:8px; padding:8px 10px; }}
.kpi .l {{ font-size:8.5px; color:{DIM}; text-transform:uppercase; letter-spacing:.05em; }}
.kpi .v {{ font-size:16px; font-weight:700; margin-top:3px; }}
.kpi .d {{ font-size:9.5px; margin-top:2px; color:{DIM}; }}
.charts {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:6px; }}
.card h3 {{ font-size:11px; margin-bottom:2px; }}
.card p.cap {{ font-size:9px; color:{DIM}; margin-bottom:4px; }}
.card svg {{ width:100%; height:auto; }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:10px; }}
h2 {{ font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:{BLUE};
  margin-bottom:6px; border-bottom:1px solid {LINE}; padding-bottom:4px; }}
.notes p {{ font-size:9.8px; line-height:1.45; margin-bottom:6px; }}
.foot {{ margin-top:10px; border-top:1px solid {LINE}; padding-top:7px;
  display:flex; justify-content:space-between; color:{DIM}; font-size:8.8px; }}
table {{ width:100%; border-collapse:collapse; font-size:9.5px; }}
th, td {{ text-align:left; padding:4px 6px; border-bottom:1px solid {LINE}; }}
th {{ color:{DIM}; font-size:8.5px; text-transform:uppercase; letter-spacing:.04em; }}
</style></head><body><div class="page">
  <div class="top">
    <div><div class="co">namikakmandev.github.io · personal analysis of public statistics</div>
      <h1>Who insures the herd? Livestock insurance in Türkiye and the US</h1></div>
    <div class="per">Namık Akman<br>August 2026</div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="l">Türkiye penetration</div><div class="v">3% → 41%</div>
      <div class="d">of the cattle herd insured, 2013 → 2024 (TARSİM)</div></div>
    <div class="kpi"><div class="l">Türkiye 2025</div><div class="v">10.0M head</div>
      <div class="d">insured cattle; pool loss ratio {lr25:.0f}%</div></div>
    <div class="kpi"><div class="l">US LRP cattle</div><div class="v">0.2M → 6.2M</div>
      <div class="d">head insured, 2015 → 2024 (price cover)</div></div>
    <div class="kpi"><div class="l">US subsidy share</div><div class="v">13% → 35%</div>
      <div class="d">of LRP premium, 2015 → 2024 — precedes the take-off</div></div>
  </div>
  <div class="charts">
    <div class="card"><h3>Türkiye — share of herd insured</h3>
      <p class="cap">TARSİM insured cattle ÷ FAOSTAT herd, 2013–2024</p>{op_tr}</div>
    <div class="card"><h3>US — LRP cattle head insured</h3>
      <p class="cap">RMA participation files, feeder + fed, 2003–2025, million head</p>{op_us}</div>
    <div class="card"><h3>Türkiye — pool loss ratio</h3>
      <p class="cap">Paid loss ÷ written premium, as published, 2017–2025</p>{op_lr}</div>
  </div>
  <table>
    <tr><th>Market</th><th>Scheme &amp; product</th><th>Data</th></tr>
    <tr><td>Türkiye</td><td>TARSİM — subsidized pool; mortality &amp; disease cover</td>
      <td>Annual reports 2016–2025, key-figures tables; zero overlap conflicts</td></tr>
    <tr><td>United States</td><td>USDA RMA — subsidized price (LRP) and margin/revenue (DRP) cover</td>
      <td>Participation files; layouts from RMA's own documentation; LGM omitted (unmapped)</td></tr>
    <tr><td>Spain</td><td>Agroseguro/ENESA — subsidized pool</td>
      <td>No machine-readable public series located; excluded, declared</td></tr>
    <tr><td>Germany</td><td>Tierseuchenkassen — compulsory public epidemic funds</td>
      <td>Not insurance; kept as a separate category, not zero</td></tr>
  </table>
  <div class="cols notes">
    <div><h2>Reading</h2>
      <p><b>Different products.</b> Mortality cover (TR) and price cover (US) are
      never summed or ranked against each other; each series is compared with
      itself over time.</p>
      <p><b>Loss ratio.</b> Paid loss (TR) or indemnity (US) ÷ written premium,
      as published — unitless, immune to currency and inflation. US 2025 shown
      without a loss ratio: endorsements are still settling.</p></div>
    <div><h2>Sources</h2>
      <p>TARSİM annual reports (tarsim.gov.tr, English PDFs) — every value pinned
      to report and page in data/livestock-ins-tarsim.json. USDA RMA livestock
      &amp; dairy participation files (pubfs-rma.fpac.usda.gov) — column maps in
      data/livestock-ins-usa.json. Herd: FAOSTAT via Our World in Data.
      Data cut 12 Aug 2026; every figure recomputable from the committed files.</p></div>
  </div>
  <div class="foot"><span>Full study: namikakmandev.github.io/livestock-insurance.html</span>
    <span>Views my own · not investment advice</span></div>
</div></body></html>"""
open(os.path.join(ROOT, "notes", "livestock-ins-onepager.html"), "w").write(ONE)
print("wrote post + onepager html")
