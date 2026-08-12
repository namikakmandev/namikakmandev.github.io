#!/usr/bin/env python3
"""Draft study page -> livestock-insurance.html (site root, noindex, DRAFT).

Reads data/livestock-ins-tarsim.json (TARSİM annual reports, page-pinned) and
data/herd-cattle.json (FAOSTAT via OWID) — every figure recomputable.

Integrity decisions:
- No nominal-lira charts across 2013–2025 (TR inflation would be the chart).
  Money appears only as the unitless loss ratio (paid loss ÷ written premium,
  as published). Quantities are physical head counts.
- Penetration shown through 2024 only: FAOSTAT herd for 2025 not yet
  published; 2025 insured head stated as text.
- US (USDA RMA) and Spain (ENESA) panels are declared as in-progress, not
  silently absent.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "livestock-insurance.html")

S = dict(surface="#0f1419", ink="#f4f6f8", ink2="#9aa3ad", grid="#232a33",
         muted="#3d4654", blue="#3987e5", green="#199e70", orange="#d95926",
         yellow="#c98500")

T = json.load(open(os.path.join(ROOT, "data", "livestock-ins-tarsim.json")))["tarsim_series"]
HERD = json.load(open(os.path.join(ROOT, "data", "herd-cattle.json")))["series"]["TR"]

KF = T["key_figures"]
INS_CATTLE = {y: v["value"] for y, v in KF["Number of Insured Cattle (Head)"].items()}
INS_SHEEP = {y: v["value"] for y, v in KF["Number of Insured Sheep and Goats (Head)"].items()}
PREMIUM = {y: v["value"] for y, v in KF["Total Premium"].items()}
PAID = {y: v["value"] for y, v in KF["Total Paid Loss"].items()}
CATTLE_LINE = T["lines"].get("Cattle", {})

US = json.load(open(os.path.join(ROOT, "data", "livestock-ins-usa.json")))["rma_final"]["series"]
US_HERD = json.load(open(os.path.join(ROOT, "data", "herd-cattle.json")))["series"]["US"]

def us_cattle(metric):
    out = {}
    for y, rows in US.items():
        if not ("2003" <= y <= "2025"):
            continue
        v = sum(r[metric] for k, r in rows.items()
                if k in ("LRP|Feeder Cattle", "LRP|Fed Cattle"))
        if v:
            out[y] = v
    return out

US_HEAD = us_cattle("quantity")
US_PREM = us_cattle("premium")
US_IND = us_cattle("indemnity")
# loss ratio only through 2024: 2025 endorsements are still settling
US_LR = {y: US_IND[y] / US_PREM[y] * 100 for y in sorted(US_PREM)
         if y in US_IND and y <= "2024"}
DRP_LR = {y: sum(r["indemnity"] for k, r in US[y].items() if k == "DRP|Milk")
             / max(1, sum(r["premium"] for k, r in US[y].items() if k == "DRP|Milk")) * 100
          for y in sorted(US) if "2019" <= y <= "2024"}

PEN = {y: INS_CATTLE[y] / HERD[y] * 100 for y in sorted(INS_CATTLE) if y in HERD}
LR_POOL = {y: PAID[y] / PREMIUM[y] * 100 for y in sorted(PAID) if y in PREMIUM}
LR_CATTLE = {y: r["paid_loss"] / r["premium"] * 100 for y, r in sorted(CATTLE_LINE.items())
             if r.get("premium")}


def line_chart(series_list, y_fmt, y_ticks, aria, W=940, H=430, PADR=230):
    all_v = [v for _, d, *_ in series_list for v in d.values()]
    ylo, yhi = 0, max(all_v) * 1.12
    years = sorted({int(y) for _, d, *_ in series_list for y in d})
    xlo, xhi = years[0], years[-1]
    X = lambda t: (t - xlo) / (xhi - xlo) * (W - PADR)
    Y = lambda v: H - 40 - (v - ylo) / (yhi - ylo) * (H - 70)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{aria}">']
    for yt in y_ticks:
        if yt > yhi: continue
        out.append(f'<line x1="0" y1="{Y(yt):.0f}" x2="{W - PADR + 40}" y2="{Y(yt):.0f}" '
                   f'stroke="{S["grid"]}" stroke-width="1.2"/>')
        out.append(f'<text x="4" y="{Y(yt) - 7:.0f}" fill="{S["muted"]}" '
                   f'font-size="17">{y_fmt(yt)}</text>')
    for yr in range(xlo, xhi + 1, 2):
        anchor = "start" if X(yr) < 30 else "middle"
        out.append(f'<text x="{X(yr):.0f}" y="{H - 8}" fill="{S["ink2"]}" '
                   f'font-size="18" text-anchor="{anchor}">{yr}</text>')
    for name, d, colour in series_list:
        pts = " ".join(f"{X(int(y)):.1f},{Y(v):.1f}" for y, v in sorted(d.items()))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                   f'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>')
        ly = sorted(d.items())[-1]
        out.append(f'<text x="{X(int(ly[0])) + 10:.0f}" y="{Y(ly[1]) + 7:.0f}" '
                   f'fill="{colour}" font-size="20" font-weight="700">{name}</text>')
    out.append("</svg>")
    return "".join(out)


chartA = line_chart([("share of herd", PEN, S["green"])],
                    lambda v: f"{v:.0f}%", [0, 10, 20, 30, 40, 50],
                    "Share of Turkish cattle herd insured, 2013-2024")
chartB = line_chart([("whole pool", LR_POOL, S["orange"]),
                     ("cattle line", LR_CATTLE, S["blue"])],
                    lambda v: f"{v:.0f}%", [0, 20, 40, 60, 80],
                    "TARSIM paid losses as share of written premium")
chartC = line_chart([("cattle", {y: v / 1e6 for y, v in INS_CATTLE.items()}, S["blue"]),
                     ("sheep & goats", {y: v / 1e6 for y, v in INS_SHEEP.items()}, S["yellow"])],
                    lambda v: f"{v:.0f}M", [0, 5, 10, 15, 20],
                    "Insured animals, million head, 2013-2025")

chartD = line_chart([("head insured (LRP)", {y: v / 1e6 for y, v in US_HEAD.items()}, S["blue"])],
                    lambda v: f"{v:.0f}M", [0, 2, 4, 6],
                    "US cattle head insured under LRP, 2003-2025")
chartE = line_chart([("LRP cattle", US_LR, S["blue"]),
                     ("DRP milk", DRP_LR, S["yellow"])],
                    lambda v: f"{v:.0f}%", [0, 50, 100, 150],
                    "US livestock program loss ratios")

us_head24 = US_HEAD["2024"] / 1e6
us_pen24 = US_HEAD["2024"] / US_HERD["2024"] * 100
us_sub24 = sum(r["subsidy"] for k, r in US["2024"].items()
               if k.startswith("LRP|F")) / max(1, US_PREM["2024"]) * 100
us_sub15 = sum(r["subsidy"] for k, r in US["2015"].items()
               if k.startswith("LRP|F")) / max(1, US_PREM["2015"]) * 100

pen24 = PEN["2024"]; pen13 = PEN["2013"]
ins25 = INS_CATTLE["2025"] / 1e6
lr25 = LR_POOL["2025"]; lr24 = LR_POOL["2024"]

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Livestock insurance — draft study</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#06090c; color:{S['ink']}; font-family:"IBM Plex Sans","Segoe UI",
  system-ui,sans-serif; padding:32px 18px 70px; }}
.wrap {{ max-width:980px; margin:0 auto; }}
.draft {{ display:inline-block; background:{S['yellow']}; color:#0f1419;
  font-weight:700; font-size:13px; letter-spacing:.06em; padding:3px 10px;
  border-radius:4px; margin-bottom:14px; }}
.kicker {{ color:{S['blue']}; font-weight:700; letter-spacing:.06em;
  font-size:15px; margin-bottom:10px; }}
h1 {{ font-size:40px; line-height:1.15; margin-bottom:14px; }}
h2 {{ font-size:24px; margin:44px 0 6px; }}
p.sub {{ color:{S['ink2']}; font-size:17px; line-height:1.5; max-width:70ch; }}
.chart {{ margin:18px 0 6px; background:{S['surface']}; border-radius:8px;
  padding:18px; }}
.chart svg {{ width:100%; height:auto; display:block; }}
p.note {{ color:{S['muted']}; font-size:13.5px; line-height:1.45; max-width:80ch; }}
.typo {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
  gap:14px; margin:18px 0; }}
.tcard {{ background:{S['surface']}; border-radius:8px; padding:14px 16px; }}
.tcard h3 {{ font-size:16px; margin-bottom:6px; }}
.tcard p {{ font-size:13.5px; color:{S['ink2']}; line-height:1.45; }}
.tcard .tag {{ font-size:11px; font-weight:700; letter-spacing:.05em;
  padding:2px 7px; border-radius:3px; }}
.src {{ border-top:1px solid {S['grid']}; margin-top:44px; padding-top:16px;
  color:{S['ink2']}; font-size:13.5px; line-height:1.55; max-width:86ch; }}
.src b {{ color:{S['ink']}; }}
</style></head><body><div class="wrap">
<span class="draft">DRAFT — INTERNAL REVIEW</span>
<div class="kicker">LIVESTOCK INSURANCE · STUDY IN PROGRESS</div>
<h1>Who insures the herd?</h1>
<p class="sub">Penetration, physical coverage and loss ratios of livestock
insurance schemes, from the schemes' own published data. Türkiye first —
TARSİM's annual reports are the best public dataset in this field; the US
(USDA RMA) and Spain (ENESA) extractions are in progress.</p>

<h2>Türkiye: from 3% of the herd to 41% in eleven years</h2>
<p class="sub">Share of the national cattle herd covered by TARSİM
cattle-life insurance.</p>
<div class="chart">{chartA}</div>
<p class="note">Insured cattle head (TARSİM annual reports, key-figures
tables) ÷ national cattle stock (FAOSTAT). 2013: {pen13:.0f}% → 2024:
{pen24:.0f}%. 2025 insured head is published ({ins25:.1f}M, +45% on 2024)
but the 2025 herd figure is not yet — the penetration point is therefore
not drawn.</p>

<h2>What the pool pays out</h2>
<p class="sub">Paid losses as a share of written premium, as published —
unitless, so twelve years of lira inflation cancel out.</p>
<div class="chart">{chartB}</div>
<p class="note">Whole pool from 2017 (earlier reports do not publish paid
loss); cattle line from 2021 (line-level tables begin there). {lr24:.0f}%
in 2024 → {lr25:.0f}% in 2025 — the source reports the jump; this draft
does not attribute a cause. Paid loss excludes outstanding claims;
premiums are written, not earned.</p>

<h2>Physical coverage</h2>
<div class="chart">{chartC}</div>
<p class="note">Insured animals in million head — quantities, immune to
currency and inflation. Sheep &amp; goats shown without a penetration line:
the herd denominator is not yet in the data set.</p>

<h2>United States: the price-risk analogue took off too</h2>
<p class="sub">Cattle head covered by Livestock Risk Protection (LRP) —
price insurance, not mortality cover, so shown beside Türkiye, never
summed with it.</p>
<div class="chart">{chartD}</div>
<p class="note">USDA RMA livestock participation files, national totals of
net head, feeder + fed cattle. 2015: 0.2M head → 2024: {us_head24:.1f}M —
roughly {us_pen24:.0f}% of the Jan-1 cattle inventory (a flow-vs-stock
approximation, stated as such). The take-off follows the 2019–20 premium
subsidy expansion: subsidy was {us_sub15:.0f}% of premium in 2015,
{us_sub24:.0f}% in 2024 — from the same files.</p>

<h2>US program loss ratios</h2>
<div class="chart">{chartE}</div>
<p class="note">Indemnity ÷ total premium, national, per commodity year.
Shown through 2024 — 2025 endorsements are still settling, so its near-zero
indemnities are an artefact of timing, not performance. DRP's 2020 spike is
the pandemic milk-price collapse, visible in the source data.</p>

<h2>One market ≠ one product</h2>
<div class="typo">
  <div class="tcard"><span class="tag" style="background:{S['green']};color:#0f1419">DATA EXTRACTED</span>
    <h3>Türkiye — TARSİM</h3><p>State-subsidized pool. Mortality &amp; disease
    cover for registered animals; ~50% premium subsidy. Annual reports publish
    head counts, premiums, claims.</p></div>
  <div class="tcard"><span class="tag" style="background:{S['green']};color:#0f1419">DATA EXTRACTED</span>
    <h3>United States — USDA RMA</h3><p>Subsidized <i>price and margin</i>
    programs. LRP and DRP extracted from RMA participation files (layouts
    from RMA's own documentation); LGM omitted — field names unmapped,
    smallest of the three programs.</p></div>
  <div class="tcard"><span class="tag" style="background:{S['muted']};color:{S['ink']}">PARKED</span>
    <h3>Spain — Agroseguro / ENESA</h3><p>Subsidized pool incl. livestock
    life lines. No machine-readable public series located: the insurer's
    site blocks automated access and the ministry pages are script-rendered.
    Declared, not silently dropped.</p></div>
  <div class="tcard"><span class="tag" style="background:{S['muted']};color:{S['ink']}">NOT INSURANCE</span>
    <h3>Germany — Tierseuchenkassen</h3><p>Compulsory public epidemic funds
    levied per animal. Low private-insurance uptake does not mean unmanaged
    risk — this category is kept separate by design.</p></div>
</div>
<p class="note">Because the products differ (mortality vs price risk),
loss ratios and penetration are compared within a scheme over time, not
ranked across schemes.</p>

<div class="src">
<b>Sources &amp; method.</b> TARSİM annual reports 2016, 2020, 2024, 2025
(tarsim.gov.tr, English PDFs) — key-figures tables give four years each;
overlapping windows agreed with zero conflicts. Every extracted value
carries its report and page in <b>data/livestock-ins-tarsim.json</b>.
USDA RMA livestock &amp; dairy participation files (pubfs-rma.fpac.usda.gov),
column maps parsed from RMA's own record-layout PDFs and recorded in
<b>data/livestock-ins-usa.json</b>; LRP/DRP national aggregates, LGM omitted
(unmapped), commodity years 2026–27 excluded. Herd denominators: FAOSTAT
cattle stocks via Our World in Data (<b>data/herd-cattle.json</b>).
Loss ratio = paid loss (TR) or indemnity (US) ÷ written premium, as
published. Data cut 12 Aug 2026. Personal analysis of public statistics;
draft, not for distribution.</div>
</div></body></html>"""

open(OUT, "w").write(html)
print("wrote", OUT)
