#!/usr/bin/env python3
"""Food Basket Explorer -> basket-explorer.html (site root, interactive).

Static page + vanilla JS; loads data/food-cpi-eu.json at runtime and computes
the ratio metric (class index ÷ food index, window start = 100) client-side.
Two pivots: one category across all countries, or one country across all
categories. Flags and names embedded from the shared modules so the tool
matches the post visuals.

State is shareable: view/category/country/window round-trip through the URL
query string (?view=cat&cat=CP0112&win=2021), so a link can point at a
specific selection.
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
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta name="description" content="Which foods outpaced the food basket in
your country? Relative prices of every HICP food class, 27 European markets,
from Eurostat data.">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#06090c; color:{S['ink']}; font-family:"IBM Plex Sans","Segoe UI",
  system-ui,sans-serif; padding:28px 16px 60px; }}
.wrap {{ max-width:1020px; margin:0 auto; }}
.bar {{ display:flex; justify-content:space-between; margin-bottom:14px; gap:12px;
  flex-wrap:wrap; }}
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
.seg button:focus-visible {{ outline:2px solid {S['blue']}; outline-offset:-2px; }}
select {{ background:{S['surface']}; color:{S['ink']}; border:1px solid {S['grid']};
  border-radius:8px; font:inherit; font-size:14px; padding:8px 10px; }}
select:focus-visible {{ outline:2px solid {S['blue']}; outline-offset:1px; }}
#headline {{ font-size:17px; margin:14px 0 4px; color:{S['ink']}; }}
#headline b.up {{ color:{S['orange']}; }} #headline b.down {{ color:{S['blue']}; }}
#headline .latest {{ color:{S['muted']}; font-size:13.5px; white-space:nowrap; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr));
  gap:16px 22px; margin-top:14px; }}
.cell {{ background:{S['surface']}; border-radius:8px; padding:10px 12px; }}
.cell svg.chart {{ width:100%; height:auto; display:block; touch-action:pan-y; }}
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
#tip {{ position:fixed; z-index:10; pointer-events:none; background:#1a212b;
  border:1px solid {S['grid']}; border-radius:6px; padding:5px 9px;
  font-size:12.5px; color:{S['ink']}; font-variant-numeric:tabular-nums;
  white-space:nowrap; box-shadow:0 4px 14px rgba(0,0,0,.45); }}
@media (max-width:520px) {{
  body {{ padding:20px 12px 48px; }}
  h1 {{ font-size:26px; }}
  .controls {{ gap:8px; }}
  .seg {{ display:flex; width:100%; }}
  .seg button {{ flex:1; min-height:44px; padding:8px 6px; }}
  select {{ width:100%; min-height:44px; }}
  .grid {{ gap:12px; }}
}}
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
  <span class="seg" id="viewSeg" role="group" aria-label="View">
    <button data-v="cat" class="on" aria-pressed="true">One category, all countries</button>
    <button data-v="geo" aria-pressed="false">One country, all categories</button>
  </span>
  <select id="catSel" aria-label="Food category"></select>
  <select id="geoSel" aria-label="Country" style="display:none"></select>
  <span class="seg" id="winSeg" role="group" aria-label="Time window">
    <button data-w="2021-01" class="on" aria-pressed="true">since 2021</button>
    <button data-w="2017-01" aria-pressed="false">since 2017</button>
  </span>
</div>
<div id="headline" aria-live="polite"></div>
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
const WINS = {{ "2021": "2021-01", "2017": "2017-01" }};
let DATA = null, view = "cat", cat = "CP0112", geo = "TR", win = "2021-01";
let ROWS = [];  // rows of the current render, for the hover tooltip

// --- restore state from the URL (?view=cat&cat=CP0112&win=2021) ---
(function () {{
  const p = new URLSearchParams(location.search);
  const v = p.get("view");
  if (v === "cat" || v === "geo") view = v;
  const c = (p.get("cat") || "").toUpperCase();
  if (CLASSES[c]) cat = c;
  const g = (p.get("geo") || "").toUpperCase();
  if (NAMES[g]) geo = g;
  const w = (p.get("win") || "").slice(0, 4);
  if (WINS[w]) win = WINS[w];
}})();

function syncURL() {{
  const p = new URLSearchParams();
  p.set("view", view);
  if (view === "cat") p.set("cat", cat); else p.set("geo", geo);
  p.set("win", win.slice(0, 4));
  history.replaceState(null, "", "?" + p.toString());
}}

const catSel = document.getElementById("catSel");
const geoSel = document.getElementById("geoSel");
for (const [c, n] of Object.entries(CLASSES))
  catSel.add(new Option(n, c));
for (const g of Object.keys(NAMES).sort((a, b) => NAMES[a].localeCompare(NAMES[b])))
  geoSel.add(new Option(NAMES[g], g));

function applyControls() {{
  catSel.value = cat;
  geoSel.value = geo;
  document.querySelectorAll("#viewSeg button").forEach(b => {{
    const on = b.dataset.v === view;
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", on);
  }});
  document.querySelectorAll("#winSeg button").forEach(b => {{
    const on = b.dataset.w === win;
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", on);
  }});
  catSel.style.display = view === "cat" ? "" : "none";
  geoSel.style.display = view === "geo" ? "" : "none";
}}
applyControls();

// Ratio series, memoized per (geo, class, window). Same math as always:
// class ÷ food, re-based so the window-start month = 100; a series needs the
// window-start month in both indices and at least 12 usable months to count.
const CACHE = new Map();
function series(geoK, clsK) {{
  const key = geoK + "|" + clsK + "|" + win;
  if (CACHE.has(key)) return CACHE.get(key);
  let out = null;
  const c = DATA[geoK + "|" + clsK], f = DATA[geoK + "|CP011"];
  if (c && f && c[win] && f[win]) {{
    const months = Object.keys(c).filter(m => m >= win && f[m]).sort();
    if (months.length >= 12) {{
      const base = c[win] / f[win];
      out = {{ months, vals: months.map(m => (c[m] / f[m]) / base * 100) }};
    }}
  }}
  CACHE.set(key, out);
  return out;
}}

function mini(vals) {{
  const W = 230, H = 96;
  const lo = Math.min(...vals, 98) - 2, hi = Math.max(...vals, 102) + 2;
  const X = i => i / Math.max(vals.length - 1, 1) * W;
  const Y = v => H - 6 - (v - lo) / (hi - lo) * (H - 12);
  const pts = vals.map((v, i) => X(i).toFixed(1) + "," + Y(v).toFixed(1)).join(" ");
  const end = vals[vals.length - 1] - 100;
  const colour = end > 1 ? ORANGE : end < -1 ? BLUE : INK2;
  const t = end.toFixed(0);  // avoid a signed "-0%" / "+0%" on flat panels
  const disp = (t === "0" || t === "-0") ? "0%" : (end > 0 ? "+" : "") + t + "%";
  return {{ pts, y100: Y(100).toFixed(1), end, colour, disp }};
}}

function chartSVG(r, label) {{
  const W = 230, H = 96, m = r.s.m;
  const dir = m.end > 1 ? "above" : m.end < -1 ? "below" : "level with";
  const alab = label + ": " + m.disp +
    " vs the food basket since " + win.slice(0, 4) + ", " + dir +
    " basket, latest month " + r.s.months[r.s.months.length - 1];
  return `<svg class="chart" viewBox="0 0 ${{W}} ${{H}}" role="img"` +
    ` aria-label="${{alab}}">` +
    `<line x1="0" y1="${{m.y100}}" x2="${{W}}" y2="${{m.y100}}"` +
    ` stroke="${{GRID}}" stroke-width="1.2"/>` +
    `<polyline points="${{m.pts}}" fill="none" stroke="${{m.colour}}"` +
    ` stroke-width="2.3" stroke-linejoin="round"/></svg>`;
}}

function render() {{
  const grid = document.getElementById("grid");
  const head = document.getElementById("headline");
  if (!DATA) return;
  const rows = [];
  if (view === "cat") {{
    for (const g of Object.keys(NAMES)) {{
      const s = series(g, cat);
      if (s) rows.push({{ key: g, label: NAMES[g], flag: FLAGS[g], s }});
    }}
  }} else {{
    for (const c of Object.keys(CLASSES)) {{
      const s = series(geo, c);
      if (s) rows.push({{ key: c, label: CLASSES[c], flag: null, s }});
    }}
  }}
  rows.forEach(r => {{ if (!r.s.m) r.s.m = mini(r.s.vals); }});
  rows.sort((a, b) => b.s.m.end - a.s.m.end);
  ROWS = rows;
  const up = rows.filter(r => r.s.m.end > 1).length,
        dn = rows.filter(r => r.s.m.end < -1).length;
  const what = view === "cat" ? CLASSES[cat] : NAMES[geo];
  document.title = what + " · Food Basket Explorer";
  const latest = rows.length ?
    rows.map(r => r.s.months[r.s.months.length - 1]).sort().pop() : "";
  head.innerHTML = rows.length ?
    `<b>${{what}}</b>, since ${{win.slice(0, 4)}}: ` +
    `<b class="up">${{up}} above</b> the food basket, ` +
    `<b class="down">${{dn}} below</b>, ${{rows.length - up - dn}} flat. ` +
    `<span class="latest">latest month: ${{latest}}</span>` :
    `<b>${{what}}</b>, since ${{win.slice(0, 4)}}:`;
  grid.innerHTML = rows.map((r, i) =>
    `<div class="cell" data-i="${{i}}"><div class="ch"><span class="nm">` +
    (r.flag ? `<svg class="flag" viewBox="0 0 24 16" aria-hidden="true">${{r.flag}}</svg>` : "") +
    `<em>${{r.label}}</em></span>` +
    `<span class="v" style="color:${{r.s.m.colour}}">${{r.s.m.disp}}</span></div>` +
    chartSVG(r, r.label) + "</div>").join("") ||
    `<div class="nodata">No data for this selection.</div>`;
}}

// --- hover / tap tooltip: month and relative-price change at the cursor ---
const tip = document.createElement("div");
tip.id = "tip"; tip.hidden = true; document.body.appendChild(tip);
function showTip(e) {{
  const cell = e.target.closest(".cell");
  const r = cell && ROWS[+cell.dataset.i];
  const svg = cell && cell.querySelector("svg.chart");
  if (!r || !svg) {{ tip.hidden = true; return; }}
  const b = svg.getBoundingClientRect();
  const frac = Math.min(1, Math.max(0, (e.clientX - b.left) / b.width));
  const i = Math.round(frac * (r.s.vals.length - 1));
  const d = r.s.vals[i] - 100;
  tip.textContent = r.s.months[i] + " · " + (d > 0 ? "+" : "") +
    d.toFixed(1) + "% vs basket";
  tip.hidden = false;
  const x = Math.max(4, Math.min(e.clientX + 12,
    window.innerWidth - tip.offsetWidth - 8));
  tip.style.left = x + "px";
  tip.style.top = (e.clientY + 16) + "px";
}}
const gridEl = document.getElementById("grid");
gridEl.addEventListener("pointermove", showTip);
gridEl.addEventListener("pointerdown", showTip);
gridEl.addEventListener("pointerleave", () => {{ tip.hidden = true; }});
window.addEventListener("scroll", () => {{ tip.hidden = true; }}, {{ passive: true }});

document.getElementById("viewSeg").addEventListener("click", e => {{
  const b = e.target.closest("button[data-v]");
  if (!b || b.dataset.v === view) return;
  view = b.dataset.v;
  applyControls(); syncURL(); render();
}});
document.getElementById("winSeg").addEventListener("click", e => {{
  const b = e.target.closest("button[data-w]");
  if (!b || b.dataset.w === win) return;
  win = b.dataset.w;
  applyControls(); syncURL(); render();
}});
catSel.addEventListener("change", () => {{ cat = catSel.value; syncURL(); render(); }});
geoSel.addEventListener("change", () => {{ geo = geoSel.value; syncURL(); render(); }});

fetch("data/food-cpi-eu.json")
  .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
  .then(j => {{
    if (!j || !j.series) throw new Error("bad payload");
    DATA = j.series; render();
  }})
  .catch(() => {{
    const st = document.getElementById("status");
    if (st) st.textContent = "Could not load data/food-cpi-eu.json.";
  }});
</script>
</body></html>"""

open(os.path.join(ROOT, "basket-explorer.html"), "w").write(html)
print("wrote basket-explorer.html")
