#!/usr/bin/env python3
"""Cost Escalation Reference -> escalation-reference.html (site root).

Pick a country and two months; the tool shows how the public cost indices a
CMO price-increase letter typically cites moved between those dates:
pharma PPI (C21), manufacturing PPI (C), energy PPI (D), consumer prices
(HICP CP00), industry labour costs (LCI, quarterly), and the local currency
vs the euro. Data loads at runtime from the committed JSON files; all math is
client-side ratios between the two chosen dates.

Integrity: reference points for a discussion, not a price formula — stated on
the page. Missing series (e.g. C21 not published for a country) are declared,
never guessed. Türkiye is not in Eurostat STS — declared gap.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meat_grid as M  # FLAGS, NAMES, palette

ROOT = M.ROOT
S = M.S

GEOS = [g for g in M.GEOS if g != "TR"]  # Eurostat STS has no TR
LOCAL_FX = {"PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON",
            "SE": "SEK", "DK": "DKK", "NO": "NOK"}

flags_js = json.dumps({g: M.FLAGS[g] for g in GEOS})
names_js = json.dumps({g: M.NAMES[g] for g in GEOS})
fx_js = json.dumps(LOCAL_FX)

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cost Escalation Reference</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<meta name="description" content="How did the public cost indices behind a
price-increase request move between two dates? Producer prices (incl. pharma
manufacturing), energy, consumer prices, labour costs and FX — per European
country, from Eurostat data.">
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
p.sub {{ color:{S['ink2']}; font-size:15.5px; line-height:1.5; max-width:78ch;
  margin-bottom:18px; }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px;
  align-items:center; }}
.controls label {{ color:{S['ink2']}; font-size:13.5px; }}
select {{ background:{S['surface']}; color:{S['ink']}; border:1px solid {S['grid']};
  border-radius:8px; font:inherit; font-size:14px; padding:8px 10px; }}
select:focus-visible {{ outline:2px solid {S['blue']}; outline-offset:1px; }}
button.copy {{ background:{S['surface']}; color:{S['ink']}; border:1px solid {S['grid']};
  border-radius:8px; font:inherit; font-size:14px; padding:8px 14px; cursor:pointer; }}
button.copy:hover {{ border-color:{S['blue']}; }}
button.copy:focus-visible {{ outline:2px solid {S['blue']}; outline-offset:1px; }}
#headline {{ font-size:17px; margin:14px 0 4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:16px; margin-top:14px; }}
.card {{ background:{S['surface']}; border-radius:10px; padding:14px 16px; }}
.card h3 {{ font-size:15.5px; margin-bottom:2px; }}
.card .def {{ color:{S['muted']}; font-size:12px; margin-bottom:8px; }}
.card .big {{ font-size:30px; font-weight:700; font-variant-numeric:tabular-nums; }}
.card .big.up {{ color:{S['orange']}; }} .card .big.down {{ color:{S['blue']}; }}
.card .big.flat {{ color:{S['ink2']}; }}
.card svg {{ width:100%; height:auto; display:block; margin-top:8px; }}
.card .na {{ color:{S['muted']}; font-size:13.5px; padding:14px 0; }}
.card .sub2 {{ color:{S['ink2']}; font-size:12.5px; margin-top:6px; }}
.src {{ border-top:1px solid {S['grid']}; margin-top:34px; padding-top:14px;
  color:{S['muted']}; font-size:13px; line-height:1.55; max-width:92ch; }}
.src b {{ color:{S['ink2']}; }}
#status {{ color:{S['muted']}; font-size:14px; margin-top:20px; }}
.notice {{ background:{S['surface']}; border-left:3px solid {S['yellow']};
  border-radius:0 8px 8px 0; padding:10px 14px; font-size:13.5px;
  color:{S['ink2']}; line-height:1.5; margin:14px 0 4px; max-width:86ch; }}
@media (max-width:520px) {{
  h1 {{ font-size:26px; }}
  select, button.copy {{ width:100%; min-height:44px; }}
  .controls label {{ width:100%; }}
}}
</style></head><body><div class="wrap">
<div class="bar"><a href="/">← namikakman — projects</a>
  <a href="basket-explorer.html">Food Basket Explorer →</a></div>
<div class="kicker">COST ESCALATION REFERENCE · EUROPEAN MARKETS</div>
<h1>What do the indices actually say?</h1>
<p class="sub">Price-increase requests usually cite energy, inflation, wages
and currency. Pick a country and two dates — for instance your last price
agreement and today — and see how the <b>public indices</b> behind each of
those arguments actually moved in between. Every figure is a published
statistic; the change is simply the index at the end date over the index at
the start date.</p>
<div class="controls">
  <label>Country <select id="geoSel" aria-label="Country"></select></label>
  <label>From <select id="fromSel" aria-label="Start month"></select></label>
  <label>To <select id="toSel" aria-label="End month"></select></label>
  <button class="copy" id="copyBtn" title="Copy a plain-text summary">Copy summary</button>
</div>
<div id="headline" aria-live="polite"></div>
<div class="grid" id="grid"><div id="status">Loading data…</div></div>
<div class="notice"><b>Reference points, not a price formula.</b> National
indices describe averages; no individual supplier's cost structure matches
them. They are a starting point for a conversation about what changed — not
evidence of what any specific price should be.</div>
<div class="src"><b>Sources.</b> Eurostat, all series: producer prices in
industry, domestic market, monthly, unadjusted (sts_inppd_m, 2021=100) —
NACE C21 pharma manufacturing, C total manufacturing, D electricity/gas/steam
supply; HICP all items, monthly (prc_hicp_midx); labour cost index, industry
B–E, quarterly, seasonally and calendar adjusted so any pair of quarters is
comparable (lc_lci_r2_q, 2020=100); monthly average exchange rates
(ert_bil_eur_m). Monthly KPIs use the exact months chosen; labour costs use
the quarter containing each month, shown on the card. Bulgaria's lev is
pegged to the euro and not published monthly. Türkiye is not covered by
Eurostat short-term statistics — the honest answer is that no comparable
public series exists here. Where a country does not publish the pharma-
specific series, the card says so. Data refreshes monthly via this site's
pipeline; files: data/ppi-eu.json · data/lci-eu.json · data/fx-eur-m.json ·
data/meat-cpi-eu.json. Personal analysis of public statistics; views my own.</div>
</div>
<script>
const FLAGS = {flags_js};
const NAMES = {names_js};
const LOCAL_FX = {fx_js};
const ORANGE = "{S['orange']}", BLUE = "{S['blue']}", INK2 = "{S['ink2']}",
      GRID = "{S['grid']}", MUTED = "{S['muted']}";
let PPI = null, LCI = null, FX = null, CPI = null;
let geo = "PL", from = null, to = null;

const geoSel = document.getElementById("geoSel"),
      fromSel = document.getElementById("fromSel"),
      toSel = document.getElementById("toSel");
for (const g of Object.keys(NAMES).sort((a, b) => NAMES[a].localeCompare(NAMES[b])))
  geoSel.add(new Option(NAMES[g], g));

function months(series) {{ return Object.keys(series).sort(); }}
function quarterOf(m) {{
  return m.slice(0, 4) + "-Q" + (Math.floor((+m.slice(5, 7) - 1) / 3) + 1);
}}
function effRange(series, a, b) {{
  // clamp the requested window to what the series actually publishes
  if (!series) return null;
  const ks = months(series);
  const aE = ks.find(k => k >= a), bE = [...ks].reverse().find(k => k <= b);
  if (!aE || !bE || aE >= bE) return null;
  return [aE, bE];
}}
function pch(series, a, b) {{
  if (!series || !series[a] || !series[b]) return null;
  return (series[b] / series[a] - 1) * 100;
}}

function spark(series, a, b) {{
  const ks = months(series).filter(m => m >= a && m <= b);
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

function kpis() {{
  const out = [];
  const add = (name, def, series, a, b) => {{
    const r = effRange(series, a, b);
    if (!r) {{ out.push({{ name, def, v: null, sub: null, spark: "" }}); return; }}
    const v = pch(series, r[0], r[1]);
    const clamped = r[0] !== a || r[1] !== b;
    out.push({{ name, def, v,
      sub: clamped ? r[0] + " \u2192 " + r[1] + " (latest published)" : null,
      spark: v !== null ? spark(series, r[0], r[1]) : "" }});
  }};
  add("Pharma producer prices", "manufacturers' output prices, NACE C21",
      PPI[geo + "|C21"], from, to);
  add("Manufacturing producer prices", "all manufacturing, NACE C",
      PPI[geo + "|C"], from, to);
  add("Energy producer prices", "electricity, gas & steam supply, NACE D",
      PPI[geo + "|D"], from, to);
  add("Consumer prices", "HICP, all items",
      CPI[geo + "|CP00"], from, to);
  const lser = LCI[geo + "|B-E"];
  let lv = null, lsub = null;
  if (lser) {{
    const qs = Object.keys(lser).sort();
    const qa = qs.find(q => q >= quarterOf(from)),
          qb = [...qs].reverse().find(q => q <= quarterOf(to));
    if (qa && qb && qa < qb) {{
      lv = (lser[qb] / lser[qa] - 1) * 100;
      lsub = qa + " \\u2192 " + qb + " (quarterly series)";
    }}
  }}
  out.push({{ name: "Labour costs, industry", def: "labour cost index, NACE B\\u2013E",
    v: lv, sub: lsub, spark: "" }});
  const cur = LOCAL_FX[geo];
  if (cur) {{
    const s = FX[cur];
    const v = pch(s, from, to);
    out.push({{ name: cur + " per EUR", def: "monthly average exchange rate",
      v, sub: v === null ? null : (v > 0.5 ? NAMES[geo] + "'s currency weakened vs EUR"
        : v < -0.5 ? NAMES[geo] + "'s currency strengthened vs EUR" : "broadly stable"),
      spark: s ? spark(s, from, to) : "" }});
  }} else {{
    const s = FX["USD"];
    const v = pch(s, from, to);
    out.push({{ name: "USD per EUR", def: "euro-area country \\u2014 dollar rate for context",
      v, sub: v === null ? null : (v > 0.5 ? "euro stronger vs USD"
        : v < -0.5 ? "euro weaker vs USD" : "broadly stable"),
      spark: s ? spark(s, from, to) : "" }});
  }}
  return out;
}}

function fmt(v) {{
  if (v === null) return null;
  const r = Math.round(v * 10) / 10;
  return (r > 0 ? "+" : "") + r.toFixed(1) + "%";
}}

function render() {{
  if (!PPI) return;
  const grid = document.getElementById("grid");
  document.getElementById("headline").innerHTML =
    `<b>${{NAMES[geo]}}</b>, ${{from}} \\u2192 ${{to}}:`;
  grid.innerHTML = kpis().map(k => {{
    const cls = k.v === null ? "flat" : k.v > 0.5 ? "up" : k.v < -0.5 ? "down" : "flat";
    const body = k.v === null
      ? `<div class="na">Not published for this country.</div>`
      : `<div class="big ${{cls}}">${{fmt(k.v)}}</div>` + k.spark +
        (k.sub ? `<div class="sub2">${{k.sub}}</div>` : "");
    return `<div class="card"><h3>${{k.name}}</h3>` +
      `<div class="def">${{k.def}}</div>` + body + `</div>`;
  }}).join("");
  const q = new URLSearchParams({{ geo, from, to }});
  history.replaceState(null, "", location.pathname + "?" + q);
  document.title = `Cost Escalation Reference \\u2014 ${{NAMES[geo]}} ${{from}} \\u2192 ${{to}}`;
}}

document.getElementById("copyBtn").addEventListener("click", () => {{
  const lines = [`Public cost indices, ${{NAMES[geo]}}, ${{from}} \\u2192 ${{to}}`,
    `(Eurostat; reference points, not a price formula)`, ``];
  for (const k of kpis())
    lines.push(`${{k.name}}: ${{k.v === null ? "not published" : fmt(k.v)}}` +
      (k.sub ? ` (${{k.sub}})` : ""));
  lines.push(``, `Source: ${{location.href}}`);
  navigator.clipboard.writeText(lines.join("\\n")).then(() => {{
    const b = document.getElementById("copyBtn");
    b.textContent = "Copied \\u2713";
    setTimeout(() => b.textContent = "Copy summary", 1600);
  }});
}});

function fillDates() {{
  const ms = months(PPI[geo + "|C"] || PPI[geo + "|C21"] || {{}});
  const keep = (sel, v) => ms.includes(v) ? v : null;
  const oldF = from, oldT = to;
  fromSel.innerHTML = ""; toSel.innerHTML = "";
  for (const m of ms) {{ fromSel.add(new Option(m, m)); toSel.add(new Option(m, m)); }}
  to = keep(toSel, oldT) || ms[ms.length - 1];
  from = keep(fromSel, oldF) ||
    ms[Math.max(0, ms.length - 37)];  // default: three years back
  if (from >= to) from = ms[0];
  fromSel.value = from; toSel.value = to;
}}

geoSel.addEventListener("change", () => {{ geo = geoSel.value; fillDates(); render(); }});
fromSel.addEventListener("change", () => {{
  from = fromSel.value;
  if (from >= to) {{ to = months(PPI[geo + "|C"]).slice(-1)[0]; toSel.value = to; }}
  render();
}});
toSel.addEventListener("change", () => {{
  to = toSel.value;
  if (to <= from) {{ from = months(PPI[geo + "|C"])[0]; fromSel.value = from; }}
  render();
}});

Promise.all([
  fetch("data/ppi-eu.json").then(r => r.json()),
  fetch("data/lci-eu.json").then(r => r.json()),
  fetch("data/fx-eur-m.json").then(r => r.json()),
  fetch("data/meat-cpi-eu.json").then(r => r.json()),
]).then(([p, l, f, c]) => {{
  PPI = p.series; LCI = l.series; FX = f.series; CPI = c.series;
  const q = new URLSearchParams(location.search);
  if (q.get("geo") && NAMES[q.get("geo").toUpperCase()]) geo = q.get("geo").toUpperCase();
  geoSel.value = geo;
  fillDates();
  const okM = m => /^20\\d\\d-\\d\\d$/.test(m || "");
  if (okM(q.get("from"))) {{ from = q.get("from"); fromSel.value = from; }}
  if (okM(q.get("to"))) {{ to = q.get("to"); toSel.value = to; }}
  if (from >= to) fillDates();
  render();
}}).catch(() => {{
  document.getElementById("status").textContent = "Could not load the data files.";
}});
</script>
</body></html>"""

open(os.path.join(ROOT, "escalation-reference.html"), "w").write(html)
print("wrote escalation-reference.html")
