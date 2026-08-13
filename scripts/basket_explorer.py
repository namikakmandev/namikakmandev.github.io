#!/usr/bin/env python3
"""Food Basket Explorer -> basket-explorer.html (site root, interactive).

Static page + vanilla JS; loads data/food-cpi-eu.json at runtime and computes
the ratio metric (class index ÷ food index, window start = 100) client-side.
Two pivots: one category across all countries, or one country across all
categories. Flags and names embedded from the shared modules so the tool
matches the post visuals.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meat_grid as M  # FLAGS (incl. crests), NAMES, house palette via H

ROOT = M.ROOT
S = M.S

GEOS = M.GEOS  # 27 Eurostat geos
CLASSES = {
    "CP0111": "Bread & cereals",
    "CP0112": "Meat",
    "CP0113": "Fish & seafood",
    "CP0114": "Milk, cheese & eggs",
    "CP0115": "Oils & fats",
    "CP0116": "Fruit",
    "CP0117": "Vegetables",
    "CP0118": "Sugar & sweets",
    "CP0121": "Coffee, tea & cocoa",
    "CP0122": "Soft drinks & juices",
}

flags_js = json.dumps({g: M.FLAGS[g] for g in GEOS})
names_js = json.dumps({g: M.NAMES[g] for g in GEOS})
classes_js = json.dumps(CLASSES)

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Food Basket Explorer</title>
<meta name="description" content="Which foods outpaced the food basket in
your country? Relative prices of every HICP food class, 27 European markets,
from Eurostat data.">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#06090c; color:{S['ink']}; font-family:"IBM Plex Sans","Segoe UI",
  system-ui,sans-serif; padding:28px 16px 60px; }}
.wrap {{ max-width:1020px; margin:0 auto; }}
.bar {{ display:flex; justify-content:space-between; margin-bottom:14px; }}
.bar a {{ color:{S['ink2']}; text-decoration:none; font-size:14px; }}
.bar a:hover {{ color:{S['blue']}; }}
.kicker {{ color:{S['blue']}; font-weight:700; letter-spacing:.06em;
  font-size:14px; margin-bottom:8px; }}
h1 {{ font-size:34px; line-height:1.15; margin-bottom:10px; }}
p.sub {{ color:{S['ink2']}; font-size:15.5px; line-height:1.5; max-width:75ch;
  margin-bottom:18px; }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:8px;
  align-items:center; }}
.seg {{ display:inline-flex; border:1px solid {S['grid']}; border-radius:8px;
  overflow:hidden; }}
.seg button {{ background:none; border:none; color:{S['ink2']}; font:inherit;
  font-size:14px; padding:8px 14px; cursor:pointer; }}
.seg button.on {{ background:{S['blue']}; color:#0f1419; font-weight:700; }}
select {{ background:{S['surface']}; color:{S['ink']}; border:1px solid {S['grid']};
  border-radius:8px; font:inherit; font-size:14px; padding:8px 10px; }}
#headline {{ font-size:17px; margin:14px 0 4px; color:{S['ink']}; }}
#headline b.up {{ color:{S['orange']}; }} #headline b.down {{ color:{S['blue']}; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr));
  gap:16px 22px; margin-top:14px; }}
.cell {{ background:{S['surface']}; border-radius:8px; padding:10px 12px; }}
.cell svg.chart {{ width:100%; height:auto; display:block; }}
.ch {{ display:flex; justify-content:space-between; align-items:center;
  font-size:14.5px; font-weight:700; margin-bottom:4px; gap:6px; }}
.ch .nm {{ display:flex; align-items:center; gap:7px; min-width:0; }}
.ch .nm em {{ font-style:normal; overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap; }}
.flag {{ width:21px; height:14px; border-radius:2.5px; flex:none;
  outline:1px solid rgba(255,255,255,.14); outline-offset:-1px; }}
.ch .v {{ font-variant-numeric:tabular-nums; flex:none; }}
.nodata {{ color:{S['muted']}; font-size:13px; padding:24px 0; text-align:center; }}
.src {{ border-top:1px solid {S['grid']}; margin-top:34px; padding-top:14px;
  color:{S['muted']}; font-size:13px; line-height:1.5; max-width:90ch; }}
.src b {{ color:{S['ink2']}; }}
#status {{ color:{S['muted']}; font-size:14px; margin-top:20px; }}
</style></head><body><div class="wrap">
<div class="bar"><a href="/">← namikakman — projects</a>
  <a href="meat-vs-food.html">the meat chart that started this →</a></div>
<div class="kicker">FOOD BASKET EXPLORER · 27 EUROPEAN MARKETS</div>
<h1>What outpaced the food basket — and where?</h1>
<p class="sub">Every line is a <b>relative price</b>: one food category's index
divided by the whole food index, re-based to 100 at the window start. Above
100 — the category outpaced the basket; below — it fell behind. Ratios cancel
the general inflation level, so every market is comparable, Türkiye included.</p>
<div class="controls">
  <span class="seg" id="viewSeg">
    <button data-v="cat" class="on">One category, all countries</button>
    <button data-v="geo">One country, all categories</button>
  </span>
  <select id="catSel"></select>
  <select id="geoSel" style="display:none"></select>
  <span class="seg" id="winSeg">
    <button data-w="2021-01" class="on">since 2021</button>
    <button data-w="2017-01">since 2017</button>
  </span>
</div>
<div id="headline"></div>
<div class="grid" id="grid"><div id="status">Loading data…</div></div>
<div class="src"><b>Method &amp; sources.</b> Eurostat HICP, monthly
(prc_hicp_midx, 2015=100): food classes CP0111–CP0122 against CP011 food.
Coffee/tea and soft drinks are non-alcoholic beverages (CP012x) shown against
the same food index, stated here. Each panel has its own scale; the number is
the change in the relative price by the latest common month. Data refreshes
monthly via this site's data pipeline; the file behind this page is
<a style="color:{S['ink2']}" href="data/food-cpi-eu.json">data/food-cpi-eu.json</a>
— every figure recomputable. Personal analysis of public statistics; views my
own.</div>
</div>
<script>
const FLAGS = {flags_js};
const NAMES = {names_js};
const CLASSES = {classes_js};
const ORANGE = "{S['orange']}", BLUE = "{S['blue']}", INK2 = "{S['ink2']}",
      GRID = "{S['grid']}", MUTED = "{S['muted']}";
let DATA = null, view = "cat", cat = "CP0112", geo = "TR", win = "2021-01";

const catSel = document.getElementById("catSel");
const geoSel = document.getElementById("geoSel");
for (const [c, n] of Object.entries(CLASSES))
  catSel.add(new Option(n, c));
catSel.value = cat;
for (const g of Object.keys(NAMES).sort((a, b) => NAMES[a].localeCompare(NAMES[b])))
  geoSel.add(new Option(NAMES[g], g));
geoSel.value = geo;

function ratio(geoK, clsK) {{
  const c = DATA[geoK + "|" + clsK], f = DATA[geoK + "|CP011"];
  if (!c || !f || !c[win] || !f[win]) return null;
  const months = Object.keys(c).filter(m => m >= win && f[m]).sort();
  if (months.length < 12) return null;
  const base = c[win] / f[win];
  return months.map(m => (c[m] / f[m]) / base * 100);
}}

function mini(vals) {{
  const W = 230, H = 96;
  const lo = Math.min(...vals, 98) - 2, hi = Math.max(...vals, 102) + 2;
  const X = i => i / (vals.length - 1) * W;
  const Y = v => H - 6 - (v - lo) / (hi - lo) * (H - 12);
  const pts = vals.map((v, i) => X(i).toFixed(1) + "," + Y(v).toFixed(1)).join(" ");
  const end = vals[vals.length - 1] - 100;
  const colour = end > 1 ? ORANGE : end < -1 ? BLUE : INK2;
  return {{ svg: `<svg class="chart" viewBox="0 0 ${{W}} ${{H}}">` +
    `<line x1="0" y1="${{Y(100).toFixed(1)}}" x2="${{W}}" y2="${{Y(100).toFixed(1)}}"` +
    ` stroke="${{GRID}}" stroke-width="1.2"/>` +
    `<polyline points="${{pts}}" fill="none" stroke="${{colour}}"` +
    ` stroke-width="2.3" stroke-linejoin="round"/></svg>`, end, colour }};
}}

function render() {{
  const grid = document.getElementById("grid");
  const head = document.getElementById("headline");
  if (!DATA) return;
  const rows = [];
  if (view === "cat") {{
    for (const g of Object.keys(NAMES)) {{
      const vals = ratio(g, cat);
      if (vals) rows.push({{ key: g, label: NAMES[g], flag: FLAGS[g], vals }});
    }}
  }} else {{
    for (const c of Object.keys(CLASSES)) {{
      const vals = ratio(geo, c);
      if (vals) rows.push({{ key: c, label: CLASSES[c], flag: null, vals }});
    }}
  }}
  rows.forEach(r => r.m = mini(r.vals));
  rows.sort((a, b) => b.m.end - a.m.end);
  const up = rows.filter(r => r.m.end > 1).length,
        dn = rows.filter(r => r.m.end < -1).length;
  const what = view === "cat" ? CLASSES[cat] : NAMES[geo];
  head.innerHTML = `<b>${{what}}</b>, since ${{win.slice(0, 4)}}: ` +
    `<b class="up">${{up}} above</b> the food basket, ` +
    `<b class="down">${{dn}} below</b>, ${{rows.length - up - dn}} flat.`;
  grid.innerHTML = rows.map(r =>
    `<div class="cell"><div class="ch"><span class="nm">` +
    (r.flag ? `<svg class="flag" viewBox="0 0 24 16">${{r.flag}}</svg>` : "") +
    `<em>${{r.label}}</em></span>` +
    `<span class="v" style="color:${{r.m.colour}}">` +
    (r.m.end > 0 ? "+" : "") + r.m.end.toFixed(0) + "%</span></div>" +
    r.m.svg + "</div>").join("") ||
    `<div class="nodata">No data for this selection.</div>`;
}}

document.getElementById("viewSeg").addEventListener("click", e => {{
  if (!e.target.dataset.v) return;
  view = e.target.dataset.v;
  document.querySelectorAll("#viewSeg button").forEach(b =>
    b.classList.toggle("on", b.dataset.v === view));
  catSel.style.display = view === "cat" ? "" : "none";
  geoSel.style.display = view === "geo" ? "" : "none";
  render();
}});
document.getElementById("winSeg").addEventListener("click", e => {{
  if (!e.target.dataset.w) return;
  win = e.target.dataset.w;
  document.querySelectorAll("#winSeg button").forEach(b =>
    b.classList.toggle("on", b.dataset.w === win));
  render();
}});
catSel.addEventListener("change", () => {{ cat = catSel.value; render(); }});
geoSel.addEventListener("change", () => {{ geo = geoSel.value; render(); }});

fetch("data/food-cpi-eu.json").then(r => r.json()).then(j => {{
  DATA = j.series; render();
}}).catch(() => {{
  document.getElementById("status").textContent =
    "Could not load data/food-cpi-eu.json.";
}});
</script>
</body></html>"""

open(os.path.join(ROOT, "basket-explorer.html"), "w").write(html)
print("wrote basket-explorer.html")
