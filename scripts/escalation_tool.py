#!/usr/bin/env python3
"""Cost Escalation Reference -> escalation-reference.html (site root).

Dashboard: pick a country on the Europe map (or the select), pick two dates,
compose your factor set — pharma PPI, manufacturing PPI, energy-supply PPI,
electricity, natural gas, consumer prices, labour costs, FX — with an
include/exclude chip and a weight per factor. Included factors combine into a
weighted blend over the chosen interval, the way escalation formulas are
actually written. Every element clamps to its own publication calendar and
says so on the card.

Integrity: reference points, not a price formula — stated. Missing series
declared. Türkiye/Switzerland/UK etc. shown on the map but marked as not
covered by Eurostat STS. Map: Natural Earth (public domain), filtered.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meat_grid as M  # NAMES + palette

ROOT = M.ROOT
S = M.S

GEOS = [g for g in M.GEOS if g != "TR"]
LOCAL_FX = {"PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON",
            "SE": "SEK", "DK": "DKK", "NO": "NOK"}

names_js = json.dumps({g: M.NAMES[g] for g in GEOS})
flags_js = json.dumps({g: M.FLAGS[g] for g in GEOS})
fx_js = json.dumps(LOCAL_FX)

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cost Escalation Reference</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta name="description" content="Pick a European country on the map, two
dates, and your factor set — producer prices (incl. pharma), electricity,
natural gas, consumer prices, labour costs, FX — and see each factor's change
plus a weighted blend, from Eurostat data.">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#06090c; color:{S['ink']}; font-family:"IBM Plex Sans","Segoe UI",
  system-ui,sans-serif; padding:28px 16px 60px; }}
.wrap {{ max-width:1060px; margin:0 auto; }}
.bar {{ display:flex; justify-content:space-between; margin-bottom:14px; gap:12px;
  flex-wrap:wrap; }}
.bar a {{ color:{S['ink2']}; text-decoration:none; font-size:14px; }}
.bar a:hover {{ color:{S['blue']}; }}
.kicker {{ color:{S['blue']}; font-weight:700; letter-spacing:.06em;
  font-size:14px; margin-bottom:8px; }}
h1 {{ font-size:34px; line-height:1.15; margin-bottom:10px; }}
p.sub {{ color:{S['ink2']}; font-size:15.5px; line-height:1.5; max-width:78ch;
  margin-bottom:16px; }}
.top {{ display:grid; grid-template-columns:minmax(280px,420px) 1fr; gap:22px;
  align-items:start; }}
#map {{ background:{S['surface']}; border-radius:10px; padding:8px; }}
#map > svg {{ width:100%; height:auto; display:block; }}
#map path {{ fill:#2b3844; stroke:#0b0f14; stroke-width:.7; cursor:pointer;
  transition:fill .12s; }}
#map path.ctx {{ fill:#161c23; cursor:not-allowed; }}
#map path:hover {{ fill:#40546a; }}
#map path.ctx:hover {{ fill:#1b232c; }}
#map path.sel {{ fill:{S['blue']}; }}
#maphint {{ color:{S['ink2']}; font-size:13px; padding:6px 8px 2px; min-height:24px;
  display:flex; align-items:center; gap:7px; }}
.flag {{ width:22px; height:15px; border-radius:2.5px; flex:none; vertical-align:-2px;
  outline:1px solid rgba(255,255,255,.16); outline-offset:-1px; }}
#headline .flag {{ width:26px; height:17px; margin-right:8px; }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:12px;
  align-items:center; }}
.controls label {{ color:{S['ink2']}; font-size:13.5px; }}
select {{ background:{S['surface']}; color:{S['ink']}; border:1px solid {S['grid']};
  border-radius:8px; font:inherit; font-size:14px; padding:8px 10px; }}
select:focus-visible, input:focus-visible, button:focus-visible {{
  outline:2px solid {S['blue']}; outline-offset:1px; }}
button.copy {{ background:{S['surface']}; color:{S['ink']}; border:1px solid {S['grid']};
  border-radius:8px; font:inherit; font-size:14px; padding:8px 14px; cursor:pointer; }}
button.copy:hover {{ border-color:{S['blue']}; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 14px; }}
.chip {{ display:inline-flex; align-items:center; gap:7px; border:1px solid {S['grid']};
  border-radius:20px; padding:6px 12px; font-size:13.5px; color:{S['ink2']};
  cursor:pointer; background:none; font:inherit; }}
.chip.on {{ border-color:{S['blue']}; color:{S['ink']}; background:#12202f; }}
.chip .w {{ width:44px; background:none; border:none; border-bottom:1px solid {S['grid']};
  color:{S['ink']}; font:inherit; font-size:13px; text-align:right; }}
.chip .w:disabled {{ opacity:.35; }}
.chip .pct {{ color:{S['muted']}; font-size:12px; }}
#headline {{ font-size:17px; margin:10px 0 4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:16px; margin-top:12px; }}
.card {{ background:{S['surface']}; border-radius:10px; padding:14px 16px; }}
.card.blend {{ border:1px solid {S['blue']}; }}
.card h3 {{ font-size:15.5px; margin-bottom:2px; }}
.card .def {{ color:{S['muted']}; font-size:12px; margin-bottom:8px; }}
.card .big {{ font-size:30px; font-weight:700; font-variant-numeric:tabular-nums; }}
.card .big.up {{ color:{S['orange']}; }} .card .big.down {{ color:{S['blue']}; }}
.card .big.flat {{ color:{S['ink2']}; }}
.card svg {{ width:100%; height:auto; display:block; margin-top:8px; }}
.card .na {{ color:{S['muted']}; font-size:13.5px; padding:14px 0; }}
.card .sub2 {{ color:{S['ink2']}; font-size:12.5px; margin-top:6px; line-height:1.4; }}
.src {{ border-top:1px solid {S['grid']}; margin-top:34px; padding-top:14px;
  color:{S['muted']}; font-size:13px; line-height:1.55; max-width:95ch; }}
.src b {{ color:{S['ink2']}; }}
#status {{ color:{S['muted']}; font-size:14px; margin-top:20px; }}
.notice {{ background:{S['surface']}; border-left:3px solid {S['yellow']};
  border-radius:0 8px 8px 0; padding:10px 14px; font-size:13.5px;
  color:{S['ink2']}; line-height:1.5; margin:16px 0 4px; max-width:88ch; }}
@media (max-width:760px) {{
  .top {{ grid-template-columns:1fr; }}
  h1 {{ font-size:26px; }}
  select, button.copy {{ width:100%; min-height:44px; }}
  .controls label {{ width:100%; }}
}}
</style></head><body><div class="wrap">
<div class="bar"><a href="/">← namikakman — projects</a>
  <a href="basket-explorer.html">Food Basket Explorer →</a></div>
<div class="kicker">COST ESCALATION REFERENCE · EUROPEAN MARKETS</div>
<h1>What do the indices actually say?</h1>
<p class="sub">Price-increase requests cite energy, wages, inflation and
currency. Pick a country on the map, choose two dates — your last price
agreement and today — then compose the factor set with the chips below.
Each factor shows its own published change; the included factors combine
into a <b>weighted blend</b>, the way escalation formulas are written.</p>
<div class="top">
  <div>
    <div id="map"><div id="maphint">Click a country · grey = not covered by
    Eurostat short-term statistics</div></div>
  </div>
  <div>
    <div class="controls">
      <label>Country <select id="geoSel" aria-label="Country"></select></label>
      <label>From <select id="fromSel" aria-label="Start month"></select></label>
      <label>To <select id="toSel" aria-label="End month"></select></label>
      <button class="copy" id="copyBtn">Copy summary</button>
    </div>
    <div class="chips" id="chips" role="group" aria-label="Factors"></div>
    <div id="headline" aria-live="polite"></div>
    <div class="grid" id="grid"><div id="status">Loading data…</div></div>
  </div>
</div>
<div class="notice"><b>Reference points, not a price formula.</b> National
indices are averages; no individual supplier's cost structure matches them,
and the weights here are yours, not evidence. This is a starting point for a
conversation about what changed — not what any specific price should be.</div>
<div class="src"><b>Sources — all Eurostat.</b> Producer prices, domestic
market, monthly, unadjusted (sts_inppd_m, 2021=100): C21 pharma
manufacturing, C total manufacturing, D energy supply. Electricity
(nrg_pc_205, band IC: 500–1 999 MWh) and natural gas (nrg_pc_203, band I3:
10 000–99 999 GJ): non-household prices excluding recoverable taxes, in
national currency, semi-annual — the standard mid-size industrial bands — national currency on purpose, so the FX factor stays separate.
HICP all items, monthly. Labour cost index, industry B–E, quarterly,
seasonally and calendar adjusted (lc_lci_r2_q). Monthly average exchange
rates (ert_bil_eur_m); Bulgaria's lev is pegged and not published monthly.
Each factor is clamped to its own latest published period and the card says
so. Countries not publishing a series say "not published" — including the
pharma-specific index in several smaller markets. Türkiye, Switzerland and
the UK appear on the map but are not covered by Eurostat short-term
statistics. Map: Natural Earth (public domain). Data refreshes monthly via
this site's pipeline; files: data/ppi-eu.json · data/lci-eu.json ·
data/fx-eur-m.json · data/meat-cpi-eu.json · data/elec-eu.json ·
data/gas-eu.json. Personal analysis of public statistics; views my own.</div>
</div>
<script>
const NAMES = {names_js};
const FLAGS = {flags_js};
const LOCAL_FX = {fx_js};
const ORANGE = "{S['orange']}", BLUE = "{S['blue']}", INK2 = "{S['ink2']}",
      GRID = "{S['grid']}", MUTED = "{S['muted']}";
let PPI, LCI, FX, CPI, ELEC, GAS, GEO;
let geo = "PL", from = null, to = null;

// factor registry: id, label, definition, kind, series-getter, default state
const KPIS = [
  {{ id: "pharma", n: "Pharma producer prices", d: "manufacturers' output prices, NACE C21",
     kind: "M", s: g => PPI[g + "|C21"], on: 1, w: 15 }},
  {{ id: "manuf", n: "Manufacturing producer prices", d: "all manufacturing, NACE C",
     kind: "M", s: g => PPI[g + "|C"], on: 1, w: 15 }},
  {{ id: "energy", n: "Energy-supply producer prices", d: "electricity/gas/steam supply, NACE D",
     kind: "M", s: g => PPI[g + "|D"], on: 0, w: 0 }},
  {{ id: "elec", n: "Electricity price", d: "non-household band IC (500\u20131 999 MWh), excl. recoverable taxes, national currency",
     kind: "S", s: g => ELEC[g], on: 1, w: 10 }},
  {{ id: "gas", n: "Natural gas price", d: "non-household band I3 (10 000\u201399 999 GJ), excl. recoverable taxes, national currency",
     kind: "S", s: g => GAS[g], on: 1, w: 5 }},
  {{ id: "cpi", n: "Consumer prices", d: "HICP, all items",
     kind: "M", s: g => CPI[g + "|CP00"], on: 1, w: 15 }},
  {{ id: "labour", n: "Labour costs, industry", d: "labour cost index, NACE B\\u2013E",
     kind: "Q", s: g => LCI[g + "|B-E"], on: 1, w: 40 }},
  {{ id: "fx", n: "Exchange rate", d: "monthly average vs EUR",
     kind: "M", s: g => LOCAL_FX[g] ? FX[LOCAL_FX[g]] : FX["USD"], on: 0, w: 0 }},
];

const monthsOf = s => Object.keys(s).sort();
const qOf = m => m.slice(0, 4) + "-Q" + (Math.floor((+m.slice(5, 7) - 1) / 3) + 1);
const sOf = m => m.slice(0, 4) + "-S" + (+m.slice(5, 7) <= 6 ? 1 : 2);

function effRange(series, a, b, kind) {{
  if (!series) return null;
  const A = kind === "Q" ? qOf(a) : kind === "S" ? sOf(a) : a;
  const B = kind === "Q" ? qOf(b) : kind === "S" ? sOf(b) : b;
  const ks = monthsOf(series);
  const aE = ks.find(k => k >= A), bE = [...ks].reverse().find(k => k <= B);
  if (!aE || !bE || aE >= bE) return null;
  return [aE, bE];
}}

function spark(series, a, b) {{
  const ks = monthsOf(series).filter(m => m >= a && m <= b);
  if (ks.length < 2) return "";
  const vals = ks.map(k => series[k] / series[a] * 100);
  const W = 260, H = 56;
  const lo = Math.min(...vals, 99) - 1, hi = Math.max(...vals, 101) + 1;
  const X = i => i / (vals.length - 1) * W;
  const Y = v => H - 4 - (v - lo) / (hi - lo) * (H - 8);
  const pts = vals.map((v, i) => X(i).toFixed(1) + "," + Y(v).toFixed(1)).join(" ");
  return `<svg viewBox="0 0 ${{W}} ${{H}}" aria-hidden="true">` +
    `<line x1="0" y1="${{Y(100).toFixed(1)}}" x2="${{W}}" y2="${{Y(100).toFixed(1)}}"` +
    ` stroke="${{GRID}}" stroke-width="1"/>` +
    `<polyline points="${{pts}}" fill="none" stroke="${{INK2}}"` +
    ` stroke-width="1.8" stroke-linejoin="round"/></svg>`;
}}

function evalKpi(k) {{
  const ser = k.s(geo);
  const r = effRange(ser, from, to, k.kind);
  if (!r) return {{ v: null, sub: null, spark: "" }};
  const v = (ser[r[1]] / ser[r[0]] - 1) * 100;
  const kindNote = k.kind === "Q" ? " (quarterly)" : k.kind === "S" ? " (semi-annual)" : "";
  const clamped = k.kind !== "M" || r[0] !== from || r[1] !== to;
  let extra = "";
  if (k.id === "fx" && v !== null) {{
    const cur = LOCAL_FX[geo];
    extra = cur
      ? (v > 0.5 ? cur + " per EUR \\u2014 currency weakened" :
         v < -0.5 ? cur + " per EUR \\u2014 currency strengthened" : cur + " per EUR, stable")
      : "USD per EUR (euro-area country, context)";
  }}
  return {{ v,
    sub: [clamped ? r[0] + " \\u2192 " + r[1] + kindNote : null, extra || null]
      .filter(Boolean).join(" \\u00b7 "),
    spark: spark(ser, r[0], r[1]) }};
}}

function fmt(v) {{
  const r = Math.round(v * 10) / 10;
  return (r > 0 ? "+" : "") + r.toFixed(1) + "%";
}}

function blend(results) {{
  const inc = KPIS.filter(k => k.on);
  const avail = inc.filter(k => results[k.id].v !== null && k.w > 0);
  const wsum = avail.reduce((s, k) => s + k.w, 0);
  if (!avail.length || wsum <= 0) return null;
  const val = avail.reduce((s, k) => s + k.w / wsum * results[k.id].v, 0);
  const dropped = inc.filter(k => results[k.id].v === null).map(k => k.n);
  return {{ val, avail, wsum, dropped }};
}}

function render() {{
  if (!PPI) return;
  const results = {{}};
  for (const k of KPIS) results[k.id] = k.on ? evalKpi(k) : null;
  document.getElementById("headline").innerHTML =
    `<b>${{NAMES[geo]}}</b>, ${{from}} \\u2192 ${{to}}:`;
  const cards = [];
  const bl = blend(results);
  if (bl) {{
    const cls = bl.val > 0.5 ? "up" : bl.val < -0.5 ? "down" : "flat";
    const parts = bl.avail.map(k =>
      Math.round(k.w / bl.wsum * 100) + "% " + k.n.toLowerCase()).join(" + ");
    cards.push(`<div class="card blend"><h3>Weighted blend \\u2014 your formula</h3>` +
      `<div class="def">${{parts}}</div>` +
      `<div class="big ${{cls}}">${{fmt(bl.val)}}</div>` +
      (bl.dropped.length ? `<div class="sub2">Excluded (not published here): ` +
        bl.dropped.join(", ") + `; weights renormalized.</div>` : "") + `</div>`);
  }}
  for (const k of KPIS) {{
    if (!k.on) continue;
    const r = results[k.id];
    const body = r.v === null
      ? `<div class="na">Not published for this country.</div>`
      : `<div class="big ${{r.v > 0.5 ? "up" : r.v < -0.5 ? "down" : "flat"}}">` +
        `${{fmt(r.v)}}</div>` + r.spark +
        (r.sub ? `<div class="sub2">${{r.sub}}</div>` : "");
    cards.push(`<div class="card"><h3>${{k.n}}</h3>` +
      `<div class="def">${{k.d}}</div>` + body + `</div>`);
  }}
  document.getElementById("grid").innerHTML = cards.join("") ||
    `<div id="status">Add at least one factor above.</div>`;
  const kparam = KPIS.filter(k => k.on).map(k => k.id + ":" + k.w).join(",");
  history.replaceState(null, "",
    location.pathname + "?" + new URLSearchParams({{ geo, from, to, k: kparam }}));
  document.title = `Cost Escalation Reference \\u2014 ${{NAMES[geo]}}`;
  document.querySelectorAll("#map path[data-geo]").forEach(p =>
    p.classList.toggle("sel", p.dataset.geo === geo));
}}

// ---- chips
function buildChips() {{
  const box = document.getElementById("chips");
  box.innerHTML = "";
  for (const k of KPIS) {{
    const c = document.createElement("span");
    c.className = "chip" + (k.on ? " on" : "");
    c.innerHTML = `<button aria-pressed="${{!!k.on}}" style="all:unset;cursor:pointer">` +
      `${{k.on ? "\\u2713 " : "+ "}}${{k.n}}</button>` +
      `<input class="w" type="number" min="0" max="100" value="${{k.w}}"` +
      ` ${{k.on ? "" : "disabled"}} aria-label="Weight of ${{k.n}}"><span class="pct">%</span>`;
    c.querySelector("button").addEventListener("click", () => {{
      k.on = k.on ? 0 : 1;
      if (k.on && k.w === 0) k.w = 10;
      buildChips(); render();
    }});
    c.querySelector("input").addEventListener("change", e => {{
      k.w = Math.max(0, Math.min(100, +e.target.value || 0)); render();
    }});
    box.appendChild(c);
  }}
}}

// ---- map
function buildMap() {{
  const LON0 = -25, LON1 = 45, LAT0 = 34, LAT1 = 71.5, K = Math.cos(52.5 * Math.PI / 180);
  const W = 460, U = W / ((LON1 - LON0) * K), H = (LAT1 - LAT0) * U;
  const px = lon => ((lon - LON0) * K * U).toFixed(1);
  const py = lat => ((LAT1 - lat) * U).toFixed(1);
  const inWin = r => r.some(c => c[0] > LON0 - 1 && c[0] < LON1 + 1 &&
                                 c[1] > LAT0 - 1 && c[1] < LAT1 + 1);
  const ring = r => "M" + r.map(c => px(c[0]) + "," + py(c[1])).join("L") + "Z";
  const geom = f => f.geometry.type === "Polygon"
    ? (inWin(f.geometry.coordinates[0]) ? f.geometry.coordinates.map(ring).join("") : "")
    : f.geometry.coordinates.filter(p => inWin(p[0])).map(p => p.map(ring).join("")).join("");
  const parts = [];
  for (const f of GEO.features) {{
    let code = f.properties.iso2 === "GR" ? "EL" : f.properties.iso2;
    const covered = !!NAMES[code];
    parts.push(`<path d="${{geom(f)}}" ${{covered ? `data-geo="${{code}}"` : 'class="ctx"'}}>` +
      `<title>${{covered ? NAMES[code] : (f.properties.name || code) +
        " \\u2014 not covered by Eurostat STS"}}</title></path>`);
  }}
  const svg = `<svg viewBox="0 0 ${{W}} ${{H.toFixed(0)}}" role="group"` +
    ` aria-label="Europe map, click to select a country">${{parts.join("")}}</svg>`;
  document.getElementById("map").insertAdjacentHTML("afterbegin", svg);
  document.getElementById("map").addEventListener("click", e => {{
    const p = e.target.closest("path[data-geo]");
    if (!p) return;
    geo = p.dataset.geo; document.getElementById("geoSel").value = geo;
    fillDates(); render();
  }});
  const hint = document.getElementById("maphint");
  const hintDefault = hint.innerHTML;
  document.getElementById("map").addEventListener("mousemove", e => {{
    const p = e.target.closest("path");
    if (!p) {{ hint.innerHTML = hintDefault; return; }}
    const code = p.dataset.geo;
    hint.innerHTML = code
      ? `<svg class="flag" viewBox="0 0 24 16">${{FLAGS[code]}}</svg>` +
        `<span>${{NAMES[code]}} \u2014 click to select</span>`
      : `<span>${{p.querySelector("title").textContent}}</span>`;
  }});
  document.getElementById("map").addEventListener("mouseleave",
    () => {{ hint.innerHTML = hintDefault; }});
}}

// ---- dates
const geoSel = document.getElementById("geoSel"),
      fromSel = document.getElementById("fromSel"),
      toSel = document.getElementById("toSel");
for (const g of Object.keys(NAMES).sort((a, b) => NAMES[a].localeCompare(NAMES[b])))
  geoSel.add(new Option(NAMES[g], g));

function fillDates() {{
  const ms = monthsOf(PPI[geo + "|C"] || PPI[geo + "|C21"] || {{}});
  const oldF = from, oldT = to;
  fromSel.innerHTML = ""; toSel.innerHTML = "";
  for (const m of ms) {{ fromSel.add(new Option(m, m)); toSel.add(new Option(m, m)); }}
  to = ms.includes(oldT) ? oldT : ms[ms.length - 1];
  from = ms.includes(oldF) ? oldF : ms[Math.max(0, ms.length - 37)];
  if (from >= to) from = ms[0];
  fromSel.value = from; toSel.value = to;
}}
geoSel.addEventListener("change", () => {{ geo = geoSel.value; fillDates(); render(); }});
fromSel.addEventListener("change", () => {{ from = fromSel.value;
  if (from >= to) {{ to = monthsOf(PPI[geo + "|C"]).slice(-1)[0]; toSel.value = to; }}
  render(); }});
toSel.addEventListener("change", () => {{ to = toSel.value;
  if (to <= from) {{ from = monthsOf(PPI[geo + "|C"])[0]; fromSel.value = from; }}
  render(); }});

// ---- copy
document.getElementById("copyBtn").addEventListener("click", () => {{
  const results = {{}};
  for (const k of KPIS) results[k.id] = k.on ? evalKpi(k) : null;
  const bl = blend(results);
  const lines = [`Public cost indices, ${{NAMES[geo]}}, ${{from}} \\u2192 ${{to}}`,
    `(Eurostat; reference points, not a price formula)`, ``];
  for (const k of KPIS) {{
    if (!k.on) continue;
    const r = results[k.id];
    lines.push(`${{k.n}}: ${{r.v === null ? "not published" : fmt(r.v)}}` +
      (r.sub ? ` (${{r.sub}})` : ""));
  }}
  if (bl) {{
    const parts = bl.avail.map(k =>
      Math.round(k.w / bl.wsum * 100) + "% " + k.n.toLowerCase()).join(" + ");
    lines.push(``, `Weighted blend (${{parts}}): ${{fmt(bl.val)}}`);
  }}
  lines.push(``, `Source: ${{location.href}}`);
  navigator.clipboard.writeText(lines.join("\\n")).then(() => {{
    const b = document.getElementById("copyBtn");
    b.textContent = "Copied \\u2713";
    setTimeout(() => b.textContent = "Copy summary", 1600);
  }});
}});

// ---- boot
Promise.all([
  "data/ppi-eu.json", "data/lci-eu.json", "data/fx-eur-m.json",
  "data/meat-cpi-eu.json", "data/elec-eu.json", "data/gas-eu.json",
  "data/europe-map.json",
].map(u => fetch(u).then(r => {{
  if (!r.ok) throw new Error(u); return r.json(); }}))
).then(([p, l, f, c, e, g, geoJ]) => {{
  PPI = p.series; LCI = l.series; FX = f.series; CPI = c.series;
  ELEC = e.series; GAS = g.series; GEO = geoJ;
  const q = new URLSearchParams(location.search);
  if (q.get("geo") && NAMES[q.get("geo").toUpperCase()]) geo = q.get("geo").toUpperCase();
  if (q.get("k")) {{
    for (const k of KPIS) {{ k.on = 0; }}
    for (const part of q.get("k").split(",")) {{
      const [id, w] = part.split(":");
      const k = KPIS.find(x => x.id === id);
      if (k) {{ k.on = 1; k.w = Math.max(0, Math.min(100, +w || 0)); }}
    }}
    if (!KPIS.some(k => k.on)) {{ KPIS[0].on = 1; KPIS[0].w = 100; }}
  }}
  geoSel.value = geo;
  buildMap(); buildChips(); fillDates();
  const okM = m => /^20\\d\\d-\\d\\d$/.test(m || "");
  if (okM(q.get("from"))) {{ from = q.get("from"); fromSel.value = from; }}
  if (okM(q.get("to"))) {{ to = q.get("to"); toSel.value = to; }}
  if (from >= to) fillDates();
  render();
}}).catch(err => {{
  document.getElementById("status").textContent =
    "Could not load " + err.message + " \\u2014 data may still be publishing.";
}});
</script>
</body></html>"""

open(os.path.join(ROOT, "escalation-reference.html"), "w").write(html)
print("wrote escalation-reference.html")
