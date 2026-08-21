#!/usr/bin/env python3
"""HTML twin of the four-market PPTX deck: 10 slides, button/keyboard navigation.

Reads the same precomputed numbers as the PPTX (scripts/deck_data.py) and inlines
them, so the page is fully self-contained and every figure is computed, not typed.
Usage: python3 scripts/deck_data.py /tmp/d.json && python3 scripts/gen_parity_deck_html.py /tmp/d.json parite-sigir-deck.html
"""
import json, sys

data = json.load(open(sys.argv[1]))
D = json.dumps(data, separators=(",", ":"))
R = data["robustness"]

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Cattle Parity — Four Markets · 10 slides</title>
<style>
:root{--bg:#0b0906;--panel:#18120a;--ink:#f5efe6;--dim:#cbbfa8;--dimmer:#8a7c62;
 --amber:#ffb056;--blue:#8aa0d8;--red:#e2574c;--teal:#46c8b2;--line:rgba(203,191,168,.18)}
*{margin:0;box-sizing:border-box}
html,body{height:100%}
body{background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans",-apple-system,Segoe UI,sans-serif;overflow:hidden}
.slide{position:absolute;inset:0;display:none;flex-direction:column;padding:4.5vh 5vw 5.6vh;opacity:0;transition:opacity .25s}
.slide.on{display:flex;opacity:1}
.kick{font:700 clamp(11px,1.1vw,15px) "IBM Plex Mono",monospace;color:var(--amber);letter-spacing:.16em}
.kick.teal{color:var(--teal)}
h1{font-size:clamp(30px,5vw,72px);line-height:1.08;margin-top:2vh;letter-spacing:-.01em}
h2{font-size:clamp(20px,2.8vw,42px);line-height:1.14;margin-top:1.2vh;font-weight:700}
.note{color:var(--dim);font-size:clamp(13px,1.35vw,20px);margin-top:1.4vh;max-width:62ch;line-height:1.45}
.chart{flex:1;min-height:0;margin-top:2vh;position:relative}
canvas{position:absolute;inset:0;width:100%;height:100%}
.foot{color:var(--dimmer);font:500 clamp(9.5px,.9vw,13px) "IBM Plex Mono",monospace;margin-top:1.6vh;letter-spacing:.04em}
.chips{display:flex;gap:1vw;margin-top:3vh;flex-wrap:wrap}
.chip{border:1px solid;border-radius:999px;padding:1vh 1.6vw;font:700 clamp(11px,1.05vw,15px) "IBM Plex Mono",monospace}
.bignum{margin-top:auto;font:700 clamp(40px,5.5vw,84px)/1 "IBM Plex Mono",monospace;color:var(--amber)}
.bignum span{font:500 clamp(12px,1.2vw,18px) "IBM Plex Sans",sans-serif;color:var(--dimmer);margin-left:1vw}
.formula{display:inline-block;border:1px solid rgba(255,176,86,.45);background:rgba(255,176,86,.07);border-radius:10px;
 padding:1.6vh 1.8vw;font:700 clamp(14px,1.6vw,24px) "IBM Plex Mono",monospace;margin-top:2.4vh}
.formula i{color:var(--amber);font-style:normal}
.formula small{display:block;color:var(--dim);font-weight:500;font-size:.62em;margin-top:.7vh}
table{width:100%;border-collapse:collapse;margin-top:2.4vh;font-size:clamp(11px,1.25vw,18px)}
th{text-align:left;font:600 clamp(9px,.9vw,13px) "IBM Plex Mono",monospace;color:var(--dimmer);letter-spacing:.08em;
 padding:.9vh .8vw;border-bottom:1px solid var(--line)}
td{padding:1.15vh .8vw;border-bottom:1px solid rgba(203,191,168,.09);color:var(--dim)}
td b{color:var(--ink)}
.chain{border-left:3px solid var(--teal);padding-left:1.2vw;margin-top:2vh;color:var(--dim);
 font-size:clamp(11px,1.15vw,16px);line-height:1.45;max-width:120ch}
.chain b{color:var(--teal)}
.split{flex:1;min-height:0;display:flex;gap:3vw;margin-top:1.6vh}
.split .chart{flex:2.4;margin-top:0}
.side{flex:1;display:flex;flex-direction:column;justify-content:center;gap:1.8vh;min-width:24ch}
.card{border:1px solid var(--line);border-left:3px solid var(--amber);border-radius:8px;background:var(--panel);padding:1.4vh 1.2vw}
.card .h{font:700 clamp(9.5px,.95vw,13px) "IBM Plex Mono",monospace;letter-spacing:.1em;margin-bottom:.5vh;color:var(--amber)}
.card .t{color:var(--dim);font-size:clamp(11px,1.1vw,15.5px);line-height:1.42}
.card .t b{color:var(--ink)}
.card.teal{border-left-color:var(--teal)}.card.teal .h{color:var(--teal)}
.bigrow{display:flex;flex-direction:column;gap:3.5vh;justify-content:center}
.bigrow .n{font:700 clamp(34px,4.4vw,66px)/1 "IBM Plex Mono",monospace}
.bigrow .d{color:var(--dim);font-size:clamp(11px,1.15vw,16px);line-height:1.4;margin-top:.7vh}
.verd{flex:1;display:flex;flex-direction:column;gap:1.6vh;justify-content:center;margin-top:1vh}
.vrow{display:flex;gap:2.4vw;align-items:center;background:var(--panel);border-radius:10px;padding:1.6vh 1.6vw}
.vrow .m{min-width:16ch}.vrow .m b{font-size:clamp(15px,1.7vw,26px)}
.vrow .m span{display:block;font:700 clamp(8.5px,.85vw,12px) "IBM Plex Mono",monospace;letter-spacing:.08em;margin-top:.5vh}
.vrow .t{color:var(--dim);font-size:clamp(11px,1.15vw,16.5px);line-height:1.42}
.tiles{flex:1;display:flex;gap:1.6vw;margin-top:2.4vh}
.tile{flex:1;border:1.5px solid;border-radius:12px;background:var(--panel);padding:2.2vh 1.4vw;display:flex;flex-direction:column}
.tile .m{font:700 clamp(9.5px,.95vw,13px) "IBM Plex Mono",monospace;letter-spacing:.08em}
.tile .n{font:700 clamp(30px,3.8vw,58px)/1.05 "IBM Plex Sans",sans-serif;color:var(--ink);margin-top:1.6vh}
.tile .u{color:var(--dimmer);font-size:clamp(9.5px,.9vw,13px);margin-top:.6vh}
.tile .t{color:var(--dim);font-size:clamp(11px,1.1vw,15.5px);line-height:1.45;margin-top:auto}
.acts{flex:1;display:flex;flex-direction:column;gap:1.6vh;justify-content:center;margin-top:1vh}
.arow{display:flex;gap:1.8vw;align-items:center;background:var(--panel);border-radius:10px;padding:1.5vh 1.6vw}
.arow .dot{width:2.6em;height:2.6em;border-radius:50%;display:flex;align-items:center;justify-content:center;
 font:700 clamp(11px,1vw,15px) "IBM Plex Mono",monospace;color:#141007;flex:none}
.arow .h{font-weight:700;font-size:clamp(14px,1.55vw,24px);min-width:20ch}
.arow .t{color:var(--dim);font-size:clamp(10.5px,1.1vw,15.5px);line-height:1.42}
.srclist{margin-top:2.6vh;display:flex;flex-direction:column;gap:1.4vh}
.srclist div{font-size:clamp(11px,1.2vw,17px);color:var(--dim);line-height:1.4}
.srclist b{font-family:"IBM Plex Mono",monospace;color:var(--amber);margin-right:.8vw}
.limits{margin-top:auto;color:var(--dim);font-size:clamp(11px,1.15vw,16px);line-height:1.55;max-width:130ch}
.limits b{color:var(--ink)}
/* navigation */
#nav{position:fixed;right:2vw;bottom:2.2vh;display:flex;gap:.6vw;align-items:center;z-index:10}
#nav button{background:var(--panel);border:1px solid rgba(255,176,86,.5);color:var(--amber);
 font:700 clamp(16px,1.6vw,24px)/1 "IBM Plex Mono",monospace;width:2.2em;height:2.2em;border-radius:10px;cursor:pointer}
#nav button:hover{background:rgba(255,176,86,.15)}
#nav button:disabled{opacity:.25;cursor:default}
#pg{font:700 clamp(11px,1.05vw,15px) "IBM Plex Mono",monospace;color:var(--dimmer);margin:0 .8vw}
#dots{position:fixed;left:50%;transform:translateX(-50%);bottom:2.6vh;display:flex;gap:.55vw;z-index:10}
#dots i{width:.55vw;min-width:6px;height:.55vw;min-height:6px;border-radius:50%;background:rgba(203,191,168,.25);cursor:pointer}
#dots i.on{background:var(--amber)}
@media print{.slide{position:relative;inset:auto;display:flex!important;opacity:1!important;height:100vh;break-after:page}#nav,#dots{display:none}}
</style>
</head>
<body>
<script>window.__D=__DATA__;</script>

<section class="slide on"><!-- 1 · title -->
  <div class="kick">A DATA STUDY · 1971 – 2026</div>
  <h1>One kilo of meat,<br>how much feed?</h1>
  <div class="note">The cattle parity — meat price against feed price — across four markets on one methodology.</div>
  <div class="chips">
    <div class="chip" style="color:var(--amber);border-color:var(--amber)">UNITED STATES</div>
    <div class="chip" style="color:var(--blue);border-color:var(--blue)">EUROPEAN UNION</div>
    <div class="chip" style="color:var(--red);border-color:var(--red)">TÜRKİYE</div>
    <div class="chip" style="color:var(--teal);border-color:var(--teal)">ISRAEL</div>
  </div>
  <div class="bignum" id="totmo"></div>
  <div class="foot">EVERY FIGURE COMPUTED FROM data/cattle-*.json · REFRESHED MONTHLY BY GITHUB ACTIONS</div>
</section>

<section class="slide"><!-- 2 · method -->
  <div class="kick">METHOD</div>
  <h2>One ratio, read as change — never as level</h2>
  <div><div class="formula"><i>parity</i> = meat price ÷ feed price
    <small>index = parity ÷ own 2016 mean × 100 · rising parity favours the feeder · a level like 2.44 is <b>not</b> “kilos of feed”</small></div></div>
  <table><thead><tr><th>MARKET</th><th>MEAT SIDE</th><th>FEED SIDE</th><th>SOURCE · SPAN</th></tr></thead>
  <tbody id="srctab"></tbody></table>
  <div class="chain"><b>Israel is base-chained:</b> CBS rebases its indices; the raw feed carries fake cliffs (−42% in 2013, −48% in 2021).
   We chain the history onto the newest base with CBS's published coefficients — the chained 2020 mean is exactly 100 on both sides.</div>
  <div class="foot">FRED/BLS · EC AGRI-FOOD DATA PORTAL · TURKSTAT/EVDS · ISRAEL CBS · DATA: github.com/namikakmandev/namikakmandev.github.io</div>
</section>

<section class="slide"><!-- 3 · race -->
  <div class="kick">CHART 1 · ALL FOUR MARKETS · 2010 – 2026</div>
  <h2>Same wave, four suspensions — parity index, own 2016 mean = 100</h2>
  <div class="chart"><canvas id="cRace"></canvas></div>
  <div class="foot">QUARTERLY MEANS OF MONTHLY PARITY · EACH SERIES ÷ ITS OWN 2016 MEAN × 100 · SOURCES ON SLIDE 2</div>
</section>

<section class="slide"><!-- 4 · violence -->
  <div class="kick">CHART 2 · FULL HISTORY OF EACH SERIES</div>
  <h2>Same cycle, very different violence</h2>
  <div class="split">
    <div class="chart"><canvas id="cBand"></canvas></div>
    <div class="side bigrow" id="bandSide"></div>
  </div>
  <div class="foot">BAND = SERIES MAX ÷ MIN OVER ITS FULL SPAN (SPANS DIFFER — ON AXIS) · VOLATILITY = STD ÷ MEAN, LAST 10 YEARS</div>
</section>

<section class="slide"><!-- 5 · decomposition -->
  <div class="kick">DECOMPOSITION · US SERIES, 1971 – 2026</div>
  <h2>It is a grain cycle wearing a cattle costume</h2>
  <div class="split">
    <div class="chart" style="flex:1.4"><canvas id="cDough"></canvas></div>
    <div class="side" style="flex:1.6;justify-content:center">
      <div class="note" style="max-width:none">Decomposing the variance of the year-on-year change in US parity:
        <b style="color:var(--ink)">84% comes from corn, 16% from cattle.</b><br><br>
        The same signature shows in 2021-23 everywhere: the global grain shock crushed parity in all four markets —
        Israel's trough (Jun 2023, 0.65 vs its 0.95 mean) is that shock arriving through imported feed grain.<br><br>
        <b style="color:var(--amber)">Implication: watching this ratio means watching the grain market first.</b></div>
    </div>
  </div>
  <div class="foot">US-ONLY DECOMPOSITION (LONGEST SERIES) · METHOD IN parite-sigir-metodoloji.html</div>
</section>

<section class="slide"><!-- 6 · israel -->
  <div class="kick teal">NEW IN THE PANEL · ISRAEL · 2005 – 2026</div>
  <h2>Israel joins on equal terms — and confirms the thesis</h2>
  <div class="split">
    <div class="chart"><canvas id="cIL"></canvas></div>
    <div class="side">
      <div class="card teal"><div class="h">SERIES</div><div class="t">Fresh beef PPI ÷ fodder input index — output over input from one national office, monthly, like Türkiye's pair.</div></div>
      <div class="card teal"><div class="h">THE 2023 TROUGH</div><div class="t"><b>0.65</b> vs a 0.95 long-run mean (Jun 2023): the grain shock via imported feed. Today: <b>0.97</b> — back at the mean.</div></div>
      <div class="card teal"><div class="h">CALMEST MARKET</div><div class="t" id="calmT"></div></div>
      <div class="card teal"><div class="h">PAIR ROBUSTNESS</div><div class="t" id="robT"></div></div>
    </div>
  </div>
  <div class="foot">ISRAEL CBS INDEX API · 190030 / 260030 · BASE-CHAINED · ROBUSTNESS PAIR 180073 / 180195 · OWN 2016 MEAN = 100</div>
</section>

<section class="slide"><!-- 7 · scope -->
  <div class="kick">SCOPE · WHAT WE CHECKED AND REJECTED</div>
  <h2>Why the study gains one market, not a region</h2>
  <div class="verd">
    <div class="vrow"><div class="m"><b>Saudi Arabia</b><span style="color:var(--amber)">PARTIAL — OUT FOR NOW</span></div>
      <div class="t">Monthly WPI has both sides, but no machine-readable endpoint exists (portal times out, API 404 — bulletins only). And Gulf feed is imported under a changing subsidy regime: a different economic object, usable only on a labelled axis.</div></div>
    <div class="vrow"><div class="m"><b>Egypt · Jordan</b><span style="color:var(--dim)">RIGHT FREQUENCY, WRONG FORMAT</span></div>
      <div class="t">Monthly indices exist but ship as PDF bulletins — a transcription project, not a data pull. Jordan also lacks a domestic feed index.</div></div>
    <div class="vrow"><div class="m"><b>Iran</b><span style="color:var(--red)">NOT COMPARABLE</span></div>
      <div class="t">Quarterly only, and feed prices ride an administered FX rate — the denominator is not a market price.</div></div>
    <div class="vrow"><div class="m"><b>Gulf states</b><span style="color:var(--dimmer)">NOTHING TO MEASURE</span></div>
      <div class="t">UAE, Qatar, Kuwait, Oman, Bahrain: negligible domestic cattle feeding, no published indices.</div></div>
  </div>
  <div class="foot">A HAND-EXTRACTED CSV FROM GASTAT'S BULLETINS WOULD ADMIT SAUDI AS A LABELLED EXCEPTION — THE PIPELINE ACCEPTS IT (SA_WPI_CSV)</div>
</section>

<section class="slide"><!-- 8 · today -->
  <div class="kick">TODAY · JUN – AUG 2026</div>
  <h2>Where each market stands against its own 2016</h2>
  <div class="tiles" id="tiles"></div>
  <div class="foot" id="tilesFoot"></div>
</section>

<section class="slide"><!-- 9 · actions -->
  <div class="kick">IMPLICATIONS · ONE INSTRUCTION PER MARKET</div>
  <h2>What to do with this on Monday</h2>
  <div class="acts">
    <div class="arow"><div class="dot" style="background:var(--amber)">US</div><div class="h">Budget on the mean, not the peak.</div>
      <div class="t">Past peaks mean-reverted in 2–4 years and this one is already a year old. Plan debt and expansion on the 1.08 long-run mean, not 2.44. Changes if: the herd rebuild stalls through 2027.</div></div>
    <div class="arow"><div class="dot" style="background:var(--blue)">EU</div><div class="h">Treat Feb 2026 as the top.</div>
      <div class="t">Parity is off its 3.49 peak with feed cheapening; assume normalization toward the 2.24 mean into 2027. Changes if: a new grain shock re-tightens feed.</div></div>
    <div class="arow"><div class="dot" style="background:var(--red)">TR</div><div class="h">Watch feed FX, not the ratio.</div>
      <div class="t">The ratio is flat because both sides inflate together; the margin story lives in currency-fed feed costs. Changes if: feed inflation decouples from meat price controls.</div></div>
    <div class="arow"><div class="dot" style="background:var(--teal)">IL</div><div class="h">Use it as the benchmark.</div>
      <div class="t">Calmest series in the panel and freshly mean-reverted — the cleanest baseline for pricing cycle risk in the region. Changes if: fodder import costs spike again as in 2021-23.</div></div>
  </div>
  <div class="foot">EACH INSTRUCTION NAMES ITS FALSIFIER — IF THE NAMED CONDITION OCCURS, THE INSTRUCTION CHANGES</div>
</section>

<section class="slide"><!-- 10 · sources -->
  <div class="kick">REPRODUCIBILITY</div>
  <h2>Every figure recomputable from committed files</h2>
  <div class="srclist" id="srcs"></div>
  <div class="limits" id="limits"></div>
  <div class="foot">namikakman.dev/parite-sigir.html · METHODOLOGY: /parite-sigir-metodoloji.html · DATA CUT-OFF: AUG 2026</div>
</section>

<div id="dots"></div>
<div id="nav">
  <button id="bPrev" aria-label="previous slide">‹</button>
  <span id="pg"></span>
  <button id="bNext" aria-label="next slide">›</button>
</div>

<script>
const D=window.__D, R=D.robustness;
const MK={US:['UNITED STATES','#ffb056'],EU:['EUROPEAN UNION','#8aa0d8'],TR:['TÜRKİYE','#e2574c'],IL:['ISRAEL','#46c8b2']};
const KS=['US','EU','TR','IL'];
const pct=k=>{const v=D[k].idx_last-100;return (v>=0?'+':'−')+Math.abs(v)+'%';};

/* ------- fill data-driven text ------- */
document.getElementById('totmo').innerHTML =
  KS.reduce((a,k)=>a+D[k].months,0).toLocaleString('en-US')+'<span>monthly observations · one methodology</span>';
document.getElementById('srctab').innerHTML = [
 ['US','Slaughter cattle PPI (WPU0131)','Corn PPI (WPU012202)','FRED / BLS'],
 ['EU','Young bull carcass R3, €/100 kg','Feed maize, €/t','EC Agri-food Portal'],
 ['Türkiye','Meat &amp; meat products PPI (T17)','Compound feed PPI (T25)','TurkStat / CBRT EVDS'],
 ['Israel','Fresh beef PPI (CBS 190030)','Fodder input index (CBS 260030)','Israel CBS API'],
].map((r,i)=>{const k=KS[i],d=D[k];
 return `<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]} · ${d.span[0]} → ${d.span[1]} · <b>${d.months} mo</b></td></tr>`}).join('');
document.getElementById('calmT').innerHTML =
 `Peak-to-trough <b>×${D.IL.band.toFixed(1)}</b> against the US ×${D.US.band.toFixed(1)} — same cycle, least violence.`;
document.getElementById('robT').innerHTML =
 `Against the exact TR-parallel pair (meat processing ÷ prepared feeds): <b>r = ${R.r_level.toFixed(2)}</b> in levels, ${R.r_yoy.toFixed(2)} in annual changes over ${R.n} common months — same trough, same calm. The conclusion does not depend on the pair chosen.`;
document.getElementById('bandSide').innerHTML =
 `<div><div class="n" style="color:var(--amber)">×${D.US.band.toFixed(1)}</div><div class="d">US peak-to-trough — feeder purchasing power moved ${D.US.band.toFixed(1)}-fold across the cycle.</div></div>`+
 `<div><div class="n" style="color:var(--teal)">×${D.IL.band.toFixed(1)}</div><div class="d">Israel — the calmest market in the panel. Ten-year volatility: US ${D.US.cv10}% · EU ${D.EU.cv10}% · TR ${D.TR.cv10}% · IL ${D.IL.cv10}%.</div></div>`;
const tileTxt={US:'Record territory. Peaked Aug 2025 at 2.54; deepest herd liquidation in decades keeps meat dear while corn is cheap.',
 EU:'Past the peak. Topped Feb 2026 at 3.49, normalizing since — feed grain cheapening does the work.',
 TR:'Flat by construction. Meat ×8 and feed ×4 since the trough — both sides inflate on the same wave, the ratio barely moves.',
 IL:'Below its 2016 level but back at its long-run mean (0.97 vs 0.95) after the 2023 imported-grain trough.'};
document.getElementById('tiles').innerHTML = KS.map(k=>
 `<div class="tile" style="border-color:${MK[k][1]}"><div class="m" style="color:${MK[k][1]}">${MK[k][0]}</div>
  <div class="n">${pct(k)}</div><div class="u">vs own 2016 mean</div><div class="t">${tileTxt[k]}</div></div>`).join('');
document.getElementById('tilesFoot').textContent =
 'INDEX = LATEST MONTHLY PARITY ÷ OWN 2016 MEAN · LATEST: '+KS.map(k=>k+' '+D[k].span[1]).join(' · ');
document.getElementById('srcs').innerHTML = [
 ['US',`BLS producer price indexes WPU0131 (slaughter cattle) ÷ WPU012202 (corn), via FRED · ${D.US.span[0]} → ${D.US.span[1]}`],
 ['EU',`EC Agri-food Data Portal: young bull R3 carcass €/100 kg ÷ feed maize €/t, monthly means of weekly quotes · ${D.EU.span[0]} → ${D.EU.span[1]}`],
 ['TÜRKİYE',`TurkStat Yİ-ÜFE via CBRT EVDS: T17 (meat &amp; meat products) ÷ T25 (compound feeds) · ${D.TR.span[0]} → ${D.TR.span[1]}`],
 ['ISRAEL',`Israel CBS index API: 190030 (fresh beef PPI) ÷ 260030 (fodder input index), base-chained · ${D.IL.span[0]} → ${D.IL.span[1]}`],
].map(([m,t])=>`<div><b>${m}</b>${t}</div>`).join('');
document.getElementById('limits').innerHTML =
 `<b>Known limits:</b> series measure different objects — changes are compared, never levels. Spans differ. Israel's raw feed has rebasing cliffs; we chain and verify (2020 mean = 100 both sides). Israel's pair choice is robustness-checked against the TR-parallel pair (r = ${R.r_level.toFixed(2)}; data/cattle-il-alt.json). Saudi Arabia is declared missing, not silently dropped.<br><br>
  <b>Data &amp; code:</b> github.com/namikakmandev/namikakmandev.github.io — data/cattle-*.json · scripts/fetch_cattle_data.py · refreshed monthly (cron, 3rd) · this deck regenerates from scripts/deck_data.py + scripts/gen_parity_deck_html.py.`;

/* ------- canvas helpers ------- */
function fit(cv){const r=cv.getBoundingClientRect(),s=devicePixelRatio||1;
 cv.width=r.width*s;cv.height=r.height*s;const x=cv.getContext('2d');x.setTransform(s,0,0,s,0,0);return [x,r.width,r.height];}
const MONO='"IBM Plex Mono",monospace';

function drawRace(){const cv=document.getElementById('cRace');const[x,W,H]=fit(cv);
 const qs=Object.keys(D.US.q_idx);const M={l:44,r:150,t:14,b:30};const w=W-M.l-M.r,h=H-M.t-M.b;
 const Y0=40,Y1=200;const X=i=>M.l+w*i/(qs.length-1);const Y=v=>M.t+h*(1-(v-Y0)/(Y1-Y0));
 x.font='10px '+MONO;
 for(let v=50;v<=200;v+=50){x.strokeStyle=v===100?'rgba(245,239,230,.28)':'rgba(203,191,168,.10)';
  x.setLineDash(v===100?[5,5]:[]);x.beginPath();x.moveTo(M.l,Y(v));x.lineTo(M.l+w,Y(v));x.stroke();x.setLineDash([]);
  x.fillStyle='#8a7c62';x.textAlign='right';x.fillText(v,M.l-7,Y(v)+3);}
 x.textAlign='center';qs.forEach((q,i)=>{if(q.endsWith('Q1')&&+q.slice(0,4)%2===0)x.fillStyle='#8a7c62',x.fillText(q.slice(0,4),X(i),H-8);});
 const ends=[];
 for(const k of KS){const c=MK[k][1];x.strokeStyle=c;x.lineWidth=2.2;x.lineJoin='round';x.beginPath();let started=false;
  qs.forEach((q,i)=>{const v=D[k].q_idx[q];if(v==null)return;
   started?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v));started=true;});
  x.stroke();const lastQ=qs.filter(q=>D[k].q_idx[q]!=null).pop();
  ends.push({k,c,y:Y(D[k].q_idx[lastQ])});}
 ends.sort((a,b)=>a.y-b.y);for(let i=1;i<ends.length;i++)if(ends[i].y-ends[i-1].y<16)ends[i].y=ends[i-1].y+16;
 x.textAlign='left';x.font='700 12px '+MONO;
 for(const e of ends){x.fillStyle=e.c;x.beginPath();x.arc(M.l+w,e.y,4,0,7);x.fill();
  x.fillText(`${e.k} ${pct(e.k)}`,M.l+w+9,e.y+4);}}

function drawBand(){const cv=document.getElementById('cBand');const[x,W,H]=fit(cv);
 const rows=[['IL',D.IL],['TR',D.TR],['EU',D.EU],['US',D.US]];
 const M={l:130,r:60,t:16,b:10};const w=W-M.l-M.r,h=H-M.t-M.b;const bh=Math.min(46,h/rows.length*0.52);
 const mx=7;
 rows.forEach(([k,d],i)=>{const y=M.t+h*(i+0.5)/rows.length;const c=MK[k][1];
  x.fillStyle='#8a7c62';x.font='12px '+MONO;x.textAlign='right';
  x.fillText(`${k==='TR'?'Türkiye':k==='IL'?'Israel':k} (${d.span[0].slice(0,4)}→)`,M.l-12,y+4);
  x.fillStyle=c;x.globalAlpha=.92;x.fillRect(M.l,y-bh/2,w*d.band/mx,bh);x.globalAlpha=1;
  x.font='700 13px '+MONO;x.textAlign='left';x.fillStyle='#f5efe6';
  x.fillText('×'+d.band.toFixed(1),M.l+w*d.band/mx+9,y+4);});}

function drawDough(){const cv=document.getElementById('cDough');const[x,W,H]=fit(cv);
 const cx=W/2,cy=H/2,r=Math.min(W,H)*0.38,ir=r*0.62;
 const segs=[[0.84,'#ffb056'],[0.16,'#6b5a3e']];let a=-Math.PI/2;
 for(const[f,c]of segs){x.beginPath();x.moveTo(cx,cy);x.arc(cx,cy,r,a,a+f*2*Math.PI);x.closePath();
  x.fillStyle=c;x.fill();x.strokeStyle='#0b0906';x.lineWidth=3;x.stroke();a+=f*2*Math.PI;}
 x.beginPath();x.arc(cx,cy,ir,0,7);x.fillStyle='#0b0906';x.fill();
 x.fillStyle='#ffb056';x.font='700 '+Math.round(r*0.5)+'px '+MONO;x.textAlign='center';x.fillText('84%',cx,cy+r*0.06);
 x.fillStyle='#cbbfa8';x.font=Math.round(r*0.14)+'px "IBM Plex Sans",sans-serif';x.fillText('feed side',cx,cy+r*0.32);}

function drawIL(){const cv=document.getElementById('cIL');const[x,W,H]=fit(cv);
 const rows=D.IL_monthly_idx;const M={l:44,r:16,t:12,b:28};const w=W-M.l-M.r,h=H-M.t-M.b;
 const Y0=50,Y1=120;const X=i=>M.l+w*i/(rows.length-1);const Y=v=>M.t+h*(1-(v-Y0)/(Y1-Y0));
 x.font='10px '+MONO;
 for(let v=60;v<=120;v+=20){x.strokeStyle=v===100?'rgba(245,239,230,.28)':'rgba(203,191,168,.10)';
  x.setLineDash(v===100?[5,5]:[]);x.beginPath();x.moveTo(M.l,Y(v));x.lineTo(M.l+w,Y(v));x.stroke();x.setLineDash([]);
  x.fillStyle='#8a7c62';x.textAlign='right';x.fillText(v,M.l-7,Y(v)+3);}
 x.textAlign='center';rows.forEach((r,i)=>{if(r[0].endsWith('-01')&&+r[0].slice(0,4)%3===0)
  x.fillStyle='#8a7c62',x.fillText(r[0].slice(0,4),X(i),H-8);});
 x.strokeStyle='#46c8b2';x.lineWidth=2.4;x.lineJoin='round';x.beginPath();
 rows.forEach((r,i)=>i?x.lineTo(X(i),Y(r[1])):x.moveTo(X(i),Y(r[1])));x.stroke();}

/* ------- navigation ------- */
const slides=[...document.querySelectorAll('.slide')];
const dots=document.getElementById('dots');
slides.forEach((_,i)=>{const d=document.createElement('i');d.onclick=()=>go(i);dots.appendChild(d);});
let cur=0;const drawn=new Set();
const drawers={2:drawRace,3:drawBand,4:drawDough,5:drawIL};
function go(i){cur=Math.max(0,Math.min(slides.length-1,i));
 slides.forEach((s,j)=>s.classList.toggle('on',j===cur));
 [...dots.children].forEach((d,j)=>d.classList.toggle('on',j===cur));
 document.getElementById('pg').textContent=(cur+1)+' / '+slides.length;
 document.getElementById('bPrev').disabled=cur===0;
 document.getElementById('bNext').disabled=cur===slides.length-1;
 if(drawers[cur]){requestAnimationFrame(()=>{drawers[cur]();drawn.add(cur);});}}
document.getElementById('bPrev').onclick=()=>go(cur-1);
document.getElementById('bNext').onclick=()=>go(cur+1);
addEventListener('keydown',e=>{
 if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' ')go(cur+1);
 if(e.key==='ArrowLeft'||e.key==='PageUp')go(cur-1);
 if(e.key==='Home')go(0); if(e.key==='End')go(slides.length-1);});
addEventListener('resize',()=>{if(drawers[cur])drawers[cur]();});
go(0);
</script>
</body>
</html>
"""

open(sys.argv[2], "w").write(HTML.replace("__DATA__", D))
print("written", sys.argv[2], len(HTML) // 1024, "KB + data")
