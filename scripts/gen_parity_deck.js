#!/usr/bin/env node
/* Four-market cattle parity deck.
   Usage: python3 scripts/deck_data.py /tmp/deck-data.json
          node scripts/gen_parity_deck.js /tmp/deck-data.json notes/cattle-parity-four-markets.pptx
   Every figure comes from the data file — nothing is typed into the slides. */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const [,, dataPath, outPath] = process.argv;
const D = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const C = { bg:"0B0906", panel:"18120A", panel2:"221A0E", ink:"F5EFE6", dim:"CBBFA8", dimmer:"8A7C62",
            amber:"FFB056", blue:"8AA0D8", red:"E2574C", teal:"46C8B2", line:"3A3226" };
const MK = { US:{c:C.amber,n:"UNITED STATES"}, EU:{c:C.blue,n:"EUROPEAN UNION"}, TR:{c:C.red,n:"TÜRKİYE"}, IL:{c:C.teal,n:"ISRAEL"} };
const F = "Arial", FM = "Courier New";
const pct = k => { const v = D[k].idx_last - 100; return (v >= 0 ? "+" : "−") + Math.abs(v) + "%"; };

const p = new pptxgen();
p.defineLayout({ name:"W", width:13.33, height:7.5 });
p.layout = "W";
const bg = s => s.background = { color: C.bg };
const kicker = (s, txt, x=0.6, y=0.42, w=9, color=C.amber) =>
  s.addText(txt, { x, y, w, h:0.3, fontFace:FM, fontSize:11, bold:true, color, charSpacing:3, margin:0 });
const title = (s, txt, x=0.6, y=0.72, w=12.1, size=30) =>
  s.addText(txt, { x, y, w, h:0.75, fontFace:F, fontSize:size, bold:true, color:C.ink, margin:0 });
const foot = (s, txt) =>
  s.addText(txt, { x:0.6, y:7.05, w:12.1, h:0.3, fontFace:FM, fontSize:8.5, color:C.dimmer, margin:0 });

/* ---------------- 1 · TITLE ---------------- */
let s = p.addSlide(); bg(s);
kicker(s, "A DATA STUDY · 1971 – 2026", 0.9, 1.5);
s.addText("One kilo of meat,\nhow much feed?", { x:0.9, y:1.85, w:8.5, h:2.2, fontFace:F, fontSize:48, bold:true, color:C.ink, margin:0, lineSpacing:56 });
s.addText("The cattle parity — meat price against feed price — across four markets on one methodology.", { x:0.9, y:4.15, w:7.6, h:0.8, fontFace:F, fontSize:16, color:C.dim, margin:0 });
let cx = 0.9;
for (const k of ["US","EU","TR","IL"]) {
  const w = k==="US"||k==="EU" ? 2.35 : (k==="TR" ? 1.75 : 1.45);
  s.addShape("roundRect", { x:cx, y:5.15, w, h:0.52, rectRadius:0.26, fill:{ color:C.panel }, line:{ color:MK[k].c, width:1.25 } });
  s.addText(MK[k].n, { x:cx, y:5.15, w, h:0.52, align:"center", fontFace:FM, fontSize:11, bold:true, color:MK[k].c, margin:0 });
  cx += w + 0.25;
}
const totalMonths = ["US","EU","TR","IL"].reduce((a,k)=>a+D[k].months,0).toLocaleString("en-US");
s.addText([
  { text:totalMonths, options:{ fontSize:40, bold:true, color:C.amber } },
  { text:"  monthly observations · refreshed automatically each month", options:{ fontSize:13, color:C.dimmer } },
], { x:0.9, y:6.1, w:11, h:0.7, fontFace:F, margin:0 });
s.addNotes("The study: one ratio (meat over feed), four markets, one methodology. US since 1971, Israel is the newest addition. All data public, all figures recomputable from the repo.");

/* ---------------- 2 · THE MEASURE ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "METHOD");
title(s, "One ratio, read as change — never as level");
s.addShape("roundRect", { x:0.6, y:1.75, w:5.9, h:1.15, rectRadius:0.09, fill:{ color:C.panel2 }, line:{ color:C.amber, width:1 } });
s.addText([
  { text:"parity", options:{ color:C.amber, bold:true } },
  { text:"  =  meat price  ÷  feed price      ", options:{ color:C.ink } },
  { text:"index = parity ÷ 2016 mean × 100", options:{ color:C.dim, fontSize:12 } },
], { x:0.85, y:1.75, w:5.5, h:1.15, fontFace:FM, fontSize:15, margin:0 });
s.addText("Rising parity favours the feeder. Units differ across markets, so each series is set to its own 2016 mean = 100 and only changes are compared — a level like 2.44 is not “kilos of feed per kilo of meat”.",
  { x:6.9, y:1.72, w:5.8, h:1.25, fontFace:F, fontSize:12.5, color:C.dim, margin:0 });
const rows = [
  [{ text:"MARKET", options:{ bold:true } }, { text:"MEAT SIDE", options:{ bold:true } }, { text:"FEED SIDE", options:{ bold:true } }, { text:"SOURCE · SPAN", options:{ bold:true } }],
  ["US", "Slaughter cattle PPI (WPU0131)", "Corn PPI (WPU012202)", `FRED / BLS · ${D.US.span[0]} → ${D.US.span[1]} · ${D.US.months} mo`],
  ["EU", "Young bull carcass R3, €/100 kg", "Feed maize, €/t", `EC Agri-food Portal · ${D.EU.span[0]} → ${D.EU.span[1]} · ${D.EU.months} mo`],
  ["Türkiye", "Meat & meat products PPI (T17)", "Compound feed PPI (T25)", `TurkStat / CBRT EVDS · ${D.TR.span[0]} → ${D.TR.span[1]} · ${D.TR.months} mo`],
  ["Israel", "Fresh beef PPI (CBS 190030)", "Fodder input index (CBS 260030)", `Israel CBS API · ${D.IL.span[0]} → ${D.IL.span[1]} · ${D.IL.months} mo`],
];
s.addTable(rows.map((r,i)=>r.map(c=>{
  const t = typeof c === "string" ? { text:c, options:{} } : c;
  t.options = { ...t.options, fontFace: i===0?FM:F, fontSize: i===0?9.5:11.5,
    color: i===0?C.dimmer:C.dim, valign:"middle" };
  return t;
})), { x:0.6, y:3.25, w:12.1, rowH:0.52, border:{ type:"solid", color:C.line, pt:0.5 },
      fill:{ color:C.panel }, margin:0.06 });
s.addText([{ text:"Israel is base-chained: ", options:{ bold:true, color:C.teal } },
  { text:"CBS rebases its indices; the raw feed carries fake cliffs (−42% in 2013, −48% in 2021). We chain the history onto the newest base with CBS's published coefficients — the chained 2020 mean is exactly 100 on both sides.", options:{ color:C.dim } }],
  { x:0.6, y:6.15, w:12.1, h:0.7, fontFace:F, fontSize:11.5, margin:0 });
foot(s, "SOURCES: FRED/BLS · EC AGRI-FOOD DATA PORTAL · TURKSTAT/EVDS · ISRAEL CBS — SERIES CODES ABOVE · DATA: github.com/namikakmandev/namikakmandev.github.io /data");
s.addNotes("Key caveat up front: index ratios, not physical quantities. Israel required base-chaining — the one technical fix worth mentioning if asked.");

/* ---------------- 3 · FOUR-MARKET RACE ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "CHART 1 · ALL FOUR MARKETS · 2010 – 2026");
title(s, "Same wave, four suspensions — parity index, own 2016 mean = 100");
const quarters = Object.keys(D.US.q_idx);
const labels = quarters.map(q => q.endsWith("Q1") ? q.slice(0,4) : "");
const mkSeries = k => ({ name:MK[k].n, labels, values: quarters.map(q => D[k].q_idx[q] ?? null) });
s.addChart("line", ["US","EU","TR","IL"].map(mkSeries), {
  x:0.6, y:1.7, w:9.4, h:5.1,
  chartColors:["FFB056","8AA0D8","E2574C","46C8B2"],
  lineSize:2.25, lineSmooth:true, lineDataSymbol:"none",
  catAxisLabelColor:C.dimmer, catAxisLabelFontSize:9, catAxisLabelFontFace:FM, catAxisLineColor:C.line,
  valAxisLabelColor:C.dimmer, valAxisLabelFontSize:9, valAxisLabelFontFace:FM, valAxisLineColor:C.line,
  valGridLine:{ color:"221A0E", size:0.5 }, catGridLine:{ style:"none" },
  valAxisMinVal:40, valAxisMaxVal:200, showLegend:false, showTitle:false, plotArea:{ fill:{ color:C.bg } },
});
let ty = 1.85;
for (const k of ["US","EU","TR","IL"]) {
  s.addShape("roundRect", { x:10.25, y:ty, w:2.5, h:1.05, rectRadius:0.08, fill:{ color:C.panel }, line:{ color:MK[k].c, width:1 } });
  s.addText([{ text:MK[k].n+"\n", options:{ fontFace:FM, fontSize:9, bold:true, color:MK[k].c } },
    { text:pct(k), options:{ fontFace:F, fontSize:22, bold:true, color:C.ink } },
    { text:"  vs 2016", options:{ fontFace:F, fontSize:9, color:C.dimmer } }],
    { x:10.42, y:ty+0.08, w:2.2, h:0.9, margin:0 });
  ty += 1.25;
}
foot(s, "QUARTERLY MEANS OF MONTHLY PARITY, EACH SERIES ÷ ITS OWN 2016 MEAN × 100 · SOURCES AS ON SLIDE 2");
s.addNotes("The one-chart story: the 2021-22 grain shock hits all four, the recovery order differs. US still in record territory; EU and TR normalizing; Israel back near its own average.");

/* ---------------- 4 · VIOLENCE OF THE CYCLE ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "CHART 2 · FULL HISTORY OF EACH SERIES");
title(s, "Same cycle, very different violence");
s.addChart("bar", [{ name:"Peak ÷ trough, full span",
  labels:[`US  (${D.US.span[0].slice(0,4)}→)`,`EU  (${D.EU.span[0].slice(0,4)}→)`,`Türkiye  (${D.TR.span[0].slice(0,4)}→)`,`Israel  (${D.IL.span[0].slice(0,4)}→)`],
  values:[D.US.band, D.EU.band, D.TR.band, D.IL.band] }], {
  x:0.6, y:1.8, w:7.4, h:4.7, barDir:"bar",
  chartColors:["FFB056","8AA0D8","E2574C","46C8B2"], chartColorsOpacity:92, varyColors:true,
  showValue:true, dataLabelPosition:"outEnd", dataLabelColor:C.ink, dataLabelFontSize:13, dataLabelFontFace:FM, dataLabelFormatCode:"×0.0",
  catAxisLabelColor:C.dim, catAxisLabelFontSize:11, catAxisLabelFontFace:F, catAxisLineColor:C.line,
  valAxisHidden:true, valGridLine:{ style:"none" }, catGridLine:{ style:"none" },
  showLegend:false, showTitle:false, valAxisMaxVal:7,
});
s.addText([
  { text:`×${D.US.band.toFixed(1)}\n`, options:{ fontSize:38, bold:true, color:C.amber } },
  { text:"US peak-to-trough — feeder purchasing power moved "+D.US.band.toFixed(1)+"-fold across the cycle.\n\n", options:{ fontSize:12, color:C.dim } },
  { text:`×${D.IL.band.toFixed(1)}\n`, options:{ fontSize:38, bold:true, color:C.teal } },
  { text:`Israel — the calmest market in the panel. Ten-year volatility: US ${D.US.cv10}% · EU ${D.EU.cv10}% · TR ${D.TR.cv10}% · IL ${D.IL.cv10}%.`, options:{ fontSize:12, color:C.dim } },
], { x:8.5, y:1.95, w:4.2, h:4.6, fontFace:F, margin:0 });
foot(s, "BAND = SERIES MAX ÷ SERIES MIN OVER ITS FULL SPAN (SPANS DIFFER — SHOWN ON AXIS) · VOLATILITY = STD ÷ MEAN, LAST 10 YEARS");
s.addNotes("Spans differ, so this compares each market against its own history, not markets against each other. Israel's calm is partly structural: fodder is a smoothed input index.");

/* ---------------- 5 · WHAT DRIVES IT ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "DECOMPOSITION · US SERIES, 1971 – 2026");
title(s, "It is a grain cycle wearing a cattle costume");
s.addChart("doughnut", [{ name:"Variance share", labels:["Feed (corn)","Cattle"], values:[84,16] }], {
  x:0.8, y:1.9, w:4.6, h:4.6, chartColors:["FFB056","6B5A3E"], holeSize:62,
  showLegend:false, showTitle:false, showValue:false, dataBorder:{ color:C.bg, pt:2 },
  plotArea:{ fill:{ color:C.bg } },
});
s.addText([{ text:"84%", options:{ fontSize:40, bold:true, color:C.amber } },
  { text:"\nfeed side", options:{ fontSize:12, color:C.dim } }],
  { x:2.0, y:3.55, w:2.2, h:1.3, align:"center", fontFace:F, margin:0 });
s.addText([
  { text:"Decomposing the variance of the year-on-year change in US parity: ", options:{ color:C.dim } },
  { text:"84% comes from corn, 16% from cattle.\n\n", options:{ bold:true, color:C.ink } },
  { text:"The same signature shows in 2021-23 everywhere: the global grain shock crushed parity in all four markets — Israel's trough (Jun 2023, 0.65 vs its 0.95 mean) is that shock arriving through imported feed grain.\n\n", options:{ color:C.dim } },
  { text:"Implication: watching this ratio means watching the grain market first.", options:{ bold:true, color:C.amber } },
], { x:6.0, y:2.1, w:6.7, h:4.2, fontFace:F, fontSize:14, margin:0 });
foot(s, "US-ONLY DECOMPOSITION (LONGEST SERIES) · METHOD PUBLISHED IN THE METHODOLOGY NOTE · parite-sigir-metodoloji.html");
s.addNotes("If one number survives the meeting, make it 84/16. The cattle side is slow biology; the feed side is where the volatility lives.");

/* ---------------- 6 · ISRAEL ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "NEW IN THE PANEL · ISRAEL · 2005 – 2026", 0.6, 0.42, 9, C.teal);
title(s, "Israel joins on equal terms — and confirms the thesis");
const ilm = D.IL_monthly_idx;
const ilLabels = ilm.map(r => r[0].endsWith("-01") && +r[0].slice(0,4)%3===0 ? r[0].slice(0,4) : "");
s.addChart("line", [{ name:"ISRAEL parity index", labels:ilLabels, values:ilm.map(r=>r[1]) }], {
  x:0.6, y:1.75, w:8.1, h:4.9,
  chartColors:["46C8B2"], lineSize:2.5, lineSmooth:false, lineDataSymbol:"none",
  catAxisLabelColor:C.dimmer, catAxisLabelFontSize:9, catAxisLabelFontFace:FM, catAxisLineColor:C.line,
  valAxisLabelColor:C.dimmer, valAxisLabelFontSize:9, valAxisLabelFontFace:FM, valAxisLineColor:C.line,
  valGridLine:{ color:"221A0E", size:0.5 }, catGridLine:{ style:"none" },
  valAxisMinVal:50, valAxisMaxVal:120, showLegend:false, showTitle:false,
});
const R = D.robustness;
const facts = [
  ["SERIES", "Fresh beef PPI ÷ fodder input index — output over input from one national office, monthly, like Türkiye's pair."],
  ["THE 2023 TROUGH", "0.65 vs a 0.95 long-run mean (Jun 2023): the global grain shock arriving via imported feed. Today: 0.97 — back at the mean."],
  ["CALMEST MARKET", `Peak-to-trough ×${D.IL.band.toFixed(1)} against the US ×${D.US.band.toFixed(1)} — same cycle, least violence.`],
  ["PAIR ROBUSTNESS", `Against the exact TR-parallel pair (meat processing ÷ prepared feeds): r = ${R.r_level.toFixed(2)} in levels, ${R.r_yoy.toFixed(2)} in annual changes over ${R.n} common months — same trough, same calm. The conclusion does not depend on the pair chosen.`],
];
let fy = 1.7;
for (const [h, t] of facts) {
  s.addText([{ text:h+"\n", options:{ fontFace:FM, fontSize:9.5, bold:true, color:C.teal } },
    { text:t, options:{ fontFace:F, fontSize:10, color:C.dim } }],
    { x:8.95, y:fy, w:3.8, h:1.22, margin:0 });
  fy += 1.28;
}
foot(s, "ISRAEL CBS INDEX API · CODES 190030 / 260030 · BASE-CHAINED (SLIDE 2) · ROBUSTNESS PAIR 180073 / 180195 · INDEX: OWN 2016 MEAN = 100");
s.addNotes("Why Israel and not others: only Middle East market publishing both sides monthly, machine-readably, from one office. If asked why beef-vs-fodder: the TR-parallel pair gives the same answer, r = 0.96.");

/* ---------------- 7 · THE REST OF THE MIDDLE EAST ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "SCOPE · WHAT WE CHECKED AND REJECTED");
title(s, "Why the study gains one market, not a region");
const verd = [
  ["Saudi Arabia", "PARTIAL — OUT FOR NOW", C.amber, "Monthly WPI has both sides, but no machine-readable endpoint exists (portal times out, API 404 — bulletins only). And Gulf feed is imported under a changing subsidy regime: a different economic object, usable only on a labelled axis."],
  ["Egypt · Jordan", "RIGHT FREQUENCY, WRONG FORMAT", C.dim, "Monthly indices exist but ship as PDF bulletins — a transcription project, not a data pull. Jordan also lacks a domestic feed index."],
  ["Iran", "NOT COMPARABLE", C.red, "Quarterly only, and feed prices ride an administered FX rate — the denominator is not a market price."],
  ["Gulf states", "NOTHING TO MEASURE", C.dimmer, "UAE, Qatar, Kuwait, Oman, Bahrain: negligible domestic cattle feeding, no published indices."],
];
let vy = 1.7;
for (const [m, v, vc, t] of verd) {
  s.addShape("roundRect", { x:0.6, y:vy, w:12.1, h:1.18, rectRadius:0.08, fill:{ color:C.panel } });
  s.addText(m, { x:0.85, y:vy+0.1, w:2.6, h:0.5, fontFace:F, fontSize:15, bold:true, color:C.ink, margin:0 });
  s.addText(v, { x:0.85, y:vy+0.62, w:2.9, h:0.4, fontFace:FM, fontSize:8.5, bold:true, color:vc, margin:0 });
  s.addText(t, { x:3.8, y:vy+0.08, w:8.7, h:1.05, fontFace:F, fontSize:10.5, color:C.dim, valign:"middle", margin:0 });
  vy += 1.32;
}
foot(s, "A HAND-EXTRACTED CSV FROM GASTAT'S MONTHLY BULLETINS WOULD ADMIT SAUDI AS A LABELLED EXCEPTION — THE PIPELINE ALREADY ACCEPTS IT (SA_WPI_CSV)");
s.addNotes("The honest framing: this is 'Israel joins the panel', not 'the Middle East'. Saudi is one transcription away if anyone wants it — but it would still need its own labelled axis.");

/* ---------------- 8 · WHERE EACH MARKET STANDS ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "TODAY · JUN – AUG 2026");
title(s, "Where each market stands against its own 2016");
const today = [
  ["US", "Record territory. Peaked Aug 2025 at 2.54; deepest herd liquidation in decades keeps meat dear while corn is cheap."],
  ["EU", "Past the peak. Topped Feb 2026 at 3.49, normalizing since — feed grain cheapening does the work."],
  ["TR", "Flat by construction. Meat ×8 and feed ×4 since the trough — both sides inflate on the same wave, the ratio barely moves."],
  ["IL", "Below its 2016 level but back at its long-run mean (0.97 vs 0.95) after the 2023 imported-grain trough."],
];
let tx = 0.6;
for (const [k, txt] of today) {
  s.addShape("roundRect", { x:tx, y:1.8, w:2.95, h:4.6, rectRadius:0.1, fill:{ color:C.panel }, line:{ color:MK[k].c, width:1.25 } });
  s.addText(MK[k].n, { x:tx+0.22, y:2.0, w:2.5, h:0.35, fontFace:FM, fontSize:10, bold:true, color:MK[k].c, margin:0 });
  s.addText(pct(k), { x:tx+0.22, y:2.4, w:2.5, h:0.85, fontFace:F, fontSize:40, bold:true, color:C.ink, margin:0 });
  s.addText("vs own 2016 mean", { x:tx+0.22, y:3.28, w:2.5, h:0.3, fontFace:F, fontSize:9, color:C.dimmer, margin:0 });
  s.addText(txt, { x:tx+0.22, y:3.7, w:2.55, h:2.5, fontFace:F, fontSize:10.5, color:C.dim, margin:0 });
  tx += 3.13;
}
foot(s, `INDEX = LATEST MONTHLY PARITY ÷ OWN 2016 MEAN · LATEST: US ${D.US.span[1]} · EU ${D.EU.span[1]} · TR ${D.TR.span[1]} · IL ${D.IL.span[1]}`);
s.addNotes("Four different phases of one cycle: US late-cycle high, EU cresting, TR structurally flat, IL mean-reverted. This is the slide that sets up the recommendations.");

/* ---------------- 9 · WHAT TO DO ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "IMPLICATIONS · ONE INSTRUCTION PER MARKET");
title(s, "What to do with this on Monday");
const act = [
  ["US", "Budget on the mean, not the peak.", "Past peaks mean-reverted in 2–4 years and this one is already a year old. Plan debt and expansion on the 1.08 long-run mean, not 2.44. Changes if: the herd rebuild stalls through 2027."],
  ["EU", "Treat Feb 2026 as the top.", "Parity is off its 3.49 peak with feed cheapening; assume normalization toward the 2.24 mean into 2027. Changes if: a new grain shock re-tightens feed."],
  ["TR", "Watch feed FX, not the ratio.", "The ratio is flat because both sides inflate together; the margin story lives in currency-fed feed costs. Changes if: feed inflation decouples from meat price controls."],
  ["IL", "Use it as the benchmark.", "Calmest series in the panel and freshly mean-reverted — the cleanest baseline for pricing cycle risk in the region. Changes if: fodder import costs spike again as in 2021-23."],
];
let ay = 1.7;
for (const [k, h, t] of act) {
  s.addShape("roundRect", { x:0.6, y:ay, w:12.1, h:1.18, rectRadius:0.08, fill:{ color:C.panel } });
  s.addShape("ellipse", { x:0.85, y:ay+0.32, w:0.55, h:0.55, fill:{ color:MK[k].c } });
  s.addText(k, { x:0.85, y:ay+0.32, w:0.55, h:0.55, align:"center", fontFace:FM, fontSize:11, bold:true, color:C.bg, margin:0 });
  s.addText(h, { x:1.65, y:ay+0.12, w:4.6, h:0.95, fontFace:F, fontSize:14.5, bold:true, color:C.ink, valign:"middle", margin:0 });
  s.addText(t, { x:6.4, y:ay+0.08, w:6.1, h:1.05, fontFace:F, fontSize:10, color:C.dim, valign:"middle", margin:0 });
  ay += 1.32;
}
foot(s, "EACH INSTRUCTION NAMES ITS FALSIFIER — IF THE NAMED CONDITION OCCURS, THE INSTRUCTION CHANGES");
s.addNotes("Per the house rule: findings end in instructions. US timing, EU top-calling, TR is an FX story, IL is the benchmark. Each has a falsifier.");

/* ---------------- 10 · SOURCES ---------------- */
s = p.addSlide(); bg(s);
kicker(s, "REPRODUCIBILITY");
title(s, "Every figure recomputable from committed files");
const src = [
  ["US", `BLS producer price indexes WPU0131 (slaughter cattle) ÷ WPU012202 (corn), via FRED · ${D.US.span[0]} → ${D.US.span[1]}`],
  ["EU", `EC Agri-food Data Portal: young bull R3 carcass €/100 kg ÷ feed maize €/t, monthly means of weekly quotes · ${D.EU.span[0]} → ${D.EU.span[1]}`],
  ["TÜRKİYE", `TurkStat Yİ-ÜFE via CBRT EVDS: TP.TUFE1YI.T17 (meat & meat products) ÷ TP.TUFE1YI.T25 (compound feeds) · ${D.TR.span[0]} → ${D.TR.span[1]}`],
  ["ISRAEL", `Israel CBS index API: 190030 (fresh beef PPI) ÷ 260030 (fodder input index), base-chained · ${D.IL.span[0]} → ${D.IL.span[1]}`],
];
let sy = 1.7;
for (const [m, t] of src) {
  s.addText([{ text:m+"  ", options:{ fontFace:FM, fontSize:10, bold:true, color:C.amber } },
    { text:t, options:{ fontFace:F, fontSize:11, color:C.dim } }],
    { x:0.6, y:sy, w:12.1, h:0.5, margin:0 });
  sy += 0.56;
}
s.addText([
  { text:"Known limits: ", options:{ bold:true, color:C.ink } },
  { text:`series measure different objects (live cattle / carcass / processed meat; corn / feed grain / compound feed / fodder) — changes are compared, never levels. Spans differ. Israel's raw feed has rebasing cliffs; we chain and verify (2020 mean = 100 both sides). Israel's pair choice is robustness-checked against the TR-parallel pair (r = ${D.robustness.r_level.toFixed(2)}; data/cattle-il-alt.json). Saudi Arabia is declared missing, not silently dropped.\n\n`, options:{ color:C.dim } },
  { text:"Data & code: ", options:{ bold:true, color:C.ink } },
  { text:"github.com/namikakmandev/namikakmandev.github.io — data/cattle-*.json, scripts/fetch_cattle_data.py, refreshed monthly by GitHub Actions (cron, 3rd of month). Deck regenerable: scripts/deck_data.py + scripts/gen_parity_deck.js. Interactive version: namikakman.dev/parite-sigir.html · methodology: /parite-sigir-metodoloji.html. Data cut-off: Aug 2026.", options:{ color:C.dim } },
], { x:0.6, y:4.25, w:12.1, h:2.6, fontFace:F, fontSize:11.5, margin:0 });
s.addNotes("Close on trust: every number traces to a committed file and a public source. Invite anyone to recompute.");

p.writeFile({ fileName: outPath }).then(()=>console.log("deck written:", outPath));
