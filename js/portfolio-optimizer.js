// ---- Product Portfolio Optimizer ----
// Allocate a limited resource across products to maximise total
// contribution margin, subject to per-product demand ceilings and
// strategic minimums. Optimal allocation = fill mandatory minimums,
// then greedily buy units in descending order of contribution earned
// per unit of the scarce resource (the divisible-knapsack / LP optimum).

const fmt = (n) =>
  (n < 0 ? "-" : "") + "€" +
  Math.round(Math.abs(n)).toLocaleString(undefined, { maximumFractionDigits: 0 });
const fmtU = (n) =>
  Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
const esc = (s) => String(s).replace(/"/g, "&quot;");
const numId = (id) => {
  const v = parseFloat(document.getElementById(id).value);
  return isNaN(v) ? 0 : v;
};

// name · price · cost · resource/unit · max demand · min units · current units
const INDUSTRIES = {
  generic: {
    res: "Capacity units", budget: 9000,
    rows: [
      { name: "Product A — premium", p: 180, c: 70, r: 6, d: 1400, m: 200, u: 300 },
      { name: "Product B — core",    p: 95,  c: 48, r: 3, d: 2600, m: 400, u: 500 },
      { name: "Product C — value",   p: 42,  c: 31, r: 2, d: 3000, m: 0,   u: 1500 },
      { name: "Product D — new",     p: 130, c: 60, r: 5, d: 900,  m: 0,   u: 150 },
      { name: "Product E — legacy",  p: 55,  c: 52, r: 4, d: 1200, m: 0,   u: 480 },
    ],
  },
  pharma: {
    res: "Field-force days", budget: 2200,
    rows: [
      { name: "Brand Alfa (in-patent)",   p: 240, c: 70,  r: 1.2, d: 6000, m: 300, u: 600 },
      { name: "Brand Beta (growth)",      p: 160, c: 55,  r: 1.0, d: 4500, m: 150, u: 300 },
      { name: "Brand Gama (mature)",      p: 90,  c: 40,  r: 0.7, d: 5000, m: 0,   u: 800 },
      { name: "Brand Delta (launch)",     p: 320, c: 110, r: 1.8, d: 1800, m: 0,   u: 100 },
      { name: "Generic line (tender)",    p: 28,  c: 24,  r: 0.4, d: 8000, m: 0,   u: 1000 },
    ],
  },
  manufacturing: {
    res: "Machine hours", budget: 7000,
    rows: [
      { name: "Assembly — Line 1", p: 420, c: 210, r: 2.5, d: 1600, m: 200, u: 500 },
      { name: "Assembly — Line 2", p: 260, c: 150, r: 1.8, d: 2400, m: 200, u: 900 },
      { name: "Spare parts kit",   p: 85,  c: 38,  r: 0.5, d: 5000, m: 0,   u: 1500 },
      { name: "Custom / project",  p: 950, c: 520, r: 6.0, d: 400,  m: 0,   u: 90 },
      { name: "Refurb / service",  p: 140, c: 120, r: 1.2, d: 1800, m: 0,   u: 1500 },
    ],
  },
  saas: {
    res: "Eng. sprint points", budget: 600,
    rows: [
      { name: "Enterprise tier",   p: 4800, c: 900,  r: 9, d: 220,  m: 10, u: 30 },
      { name: "Business tier",     p: 1400, c: 320,  r: 5, d: 900,  m: 20, u: 30 },
      { name: "Starter tier",      p: 360,  c: 110,  r: 3, d: 3000, m: 0,  u: 20 },
      { name: "Add-on: analytics", p: 280,  c: 60,   r: 4, d: 800,  m: 0,  u: 10 },
      { name: "Legacy self-host",  p: 600,  c: 540,  r: 7, d: 300,  m: 0,  u: 10 },
    ],
  },
  retail: {
    res: "Marketing budget (€000)", budget: 480,
    rows: [
      { name: "Electronics",   p: 320, c: 250, r: 0.9, d: 4000, m: 200, u: 120 },
      { name: "Apparel",       p: 70,  c: 30,  r: 0.6, d: 9000, m: 300, u: 320 },
      { name: "Home & living", p: 110, c: 62,  r: 0.7, d: 5000, m: 0,   u: 80 },
      { name: "Beauty",        p: 45,  c: 18,  r: 0.5, d: 7000, m: 0,   u: 80 },
      { name: "Clearance",     p: 25,  c: 23,  r: 0.3, d: 6000, m: 0,   u: 280 },
    ],
  },
  services: {
    res: "Consultant-days", budget: 2600,
    rows: [
      { name: "Strategy advisory",  p: 2400, c: 700, r: 2.0, d: 320,  m: 20, u: 100 },
      { name: "Implementation",     p: 1500, c: 650, r: 1.6, d: 800,  m: 40, u: 300 },
      { name: "Managed service",    p: 600,  c: 280, r: 0.8, d: 1500, m: 0,  u: 700 },
      { name: "Training",           p: 350,  c: 120, r: 0.5, d: 1200, m: 0,  u: 300 },
      { name: "Support retainer",   p: 220,  c: 200, r: 0.6, d: 900,  m: 0,  u: 800 },
    ],
  },
};

function pRow(d) {
  return `<div class="po-line">` +
    `<input class="ln-name" value="${esc(d.name)}" />` +
    `<input class="ln-p" type="number" step="1" value="${d.p}" title="price / unit" />` +
    `<input class="ln-c" type="number" step="1" value="${d.c}" title="cost / unit" />` +
    `<input class="ln-r" type="number" step="0.1" value="${d.r}" title="resource used / unit" />` +
    `<input class="ln-d" type="number" step="50" value="${d.d}" title="max demand (units)" />` +
    `<input class="ln-m" type="number" step="50" value="${d.m}" title="strategic minimum (units)" />` +
    `<input class="ln-u" type="number" step="50" value="${d.u}" title="current plan (units)" />` +
    `<button class="ln-x" type="button" title="remove">&times;</button></div>`;
}
function renderLines() {
  const key = document.getElementById("po-industry").value || "generic";
  const t = INDUSTRIES[key] || INDUSTRIES.generic;
  document.getElementById("po-budget").value = t.budget;
  document.getElementById("po-reslabel").value = t.res;
  document.getElementById("po-lines").innerHTML = t.rows.map(pRow).join("");
}
function gather() {
  return [...document.querySelectorAll("#po-lines .po-line")].map((r, i) => {
    const g = (cls) => parseFloat(r.querySelector(cls).value) || 0;
    const p = g(".ln-p"), c = g(".ln-c"), res = Math.max(0, g(".ln-r"));
    let d = Math.max(0, g(".ln-d"));
    let m = Math.max(0, g(".ln-m"));
    if (m > d) m = d;
    return {
      idx: i,
      name: r.querySelector(".ln-name").value || `Product ${i + 1}`,
      p, c, res, d, m,
      cur: Math.min(Math.max(0, g(".ln-u")), d),
      cm: p - c,                                  // contribution / unit
      eff: res > 0 ? (p - c) / res : Infinity,    // contribution per resource unit
    };
  });
}

// Core optimisation
function optimize() {
  const rows = gather();
  const budget = Math.max(0, numId("po-budget"));

  // 1) mandatory strategic minimums
  rows.forEach((x) => (x.opt = x.m));
  let used = rows.reduce((t, x) => t + x.res * x.opt, 0);
  const minsInfeasible = used > budget + 1e-9;
  let free = Math.max(0, budget - used);

  // 2) greedily fund the best contribution-per-resource first,
  //    only products that actually add positive contribution
  const queue = rows
    .filter((x) => x.cm > 0)
    .sort((a, b) => b.eff - a.eff);
  for (const x of queue) {
    const headroom = x.d - x.opt;
    if (headroom <= 0) continue;
    let take;
    if (x.res <= 0) {
      take = headroom;                            // no resource cost — fill to demand
    } else {
      const byBudget = Math.floor((free + 1e-9) / x.res);
      take = Math.min(headroom, byBudget);
    }
    if (take <= 0) continue;
    x.opt += take;
    free -= take * x.res;
    x.binding = x.opt >= x.d ? "demand" : "budget";
  }

  rows.forEach((x) => {
    x.optC = x.cm * x.opt;
    x.curC = x.cm * x.cur;
    x.optR = x.res * x.opt;
    if (x.cm <= 0) x.status = x.cm < 0 ? "Loss/unit — hold at floor" : "Zero margin — floor";
    else if (x.opt > x.cur + 0.5) x.status = "Scale up";
    else if (x.opt < x.cur - 0.5) x.status = "Scale down";
    else x.status = "Hold";
  });

  const optC = rows.reduce((t, x) => t + x.optC, 0);
  const curC = rows.reduce((t, x) => t + x.curC, 0);
  const optR = rows.reduce((t, x) => t + x.optR, 0);
  const curR = rows.reduce((t, x) => t + x.res * x.cur, 0);
  return {
    rows, budget, optC, curC, optR, curR,
    uplift: optC - curC,
    upliftPct: curC > 0 ? (optC - curC) / curC * 100 : 0,
    funded: rows.filter((x) => x.opt > 0).length,
    minsInfeasible, leftover: free,
  };
}

function barChart(R) {
  const rows = R.rows;
  if (!rows.length) { document.getElementById("po-chart").innerHTML = ""; return; }
  const W = 900, mL = 168, mR = 56, mT = 28, mB = 14, bandH = 46;
  const He = mT + mB + rows.length * bandH;
  const max = Math.max(1, ...rows.map((x) => Math.max(x.curC, x.optC)));
  const pw = W - mL - mR;
  const X = (v) => mL + Math.max(0, v) / max * pw;
  let s = "";
  // axis gridlines
  for (let g = 0; g <= 4; g++) {
    const gv = max * g / 4, gx = X(gv);
    s += `<line x1="${gx.toFixed(1)}" y1="${mT - 6}" x2="${gx.toFixed(1)}" y2="${He - mB}" stroke="var(--border)" stroke-width="1"/>`;
    s += `<text x="${gx.toFixed(1)}" y="${mT - 12}" text-anchor="middle" class="cp-ax">${fmt(gv)}</text>`;
  }
  rows.forEach((x, i) => {
    const y = mT + i * bandH;
    s += `<text x="${mL - 12}" y="${(y + bandH / 2).toFixed(1)}" text-anchor="end" dominant-baseline="middle" class="cp-ax" style="fill:var(--text)">${esc(x.name).slice(0, 22)}</text>`;
    // current (faint) then optimized (solid accent)
    const wc = X(x.curC) - mL, wo = X(x.optC) - mL;
    s += `<rect x="${mL}" y="${y + 6}" width="${Math.max(0, wc).toFixed(1)}" height="14" rx="2" fill="var(--accent)" opacity="0.30"><title>${esc(x.name)} — current ${fmt(x.curC)}</title></rect>`;
    s += `<rect x="${mL}" y="${y + 23}" width="${Math.max(0, wo).toFixed(1)}" height="14" rx="2" fill="var(--accent-2)"><title>${esc(x.name)} — optimized ${fmt(x.optC)}</title></rect>`;
    s += `<text x="${(X(x.optC) + 6).toFixed(1)}" y="${(y + 30).toFixed(1)}" dominant-baseline="middle" class="cp-ax" style="fill:var(--text)">${fmt(x.optC)}</text>`;
  });
  // legend
  s += `<rect x="${mL}" y="${He - 4}" width="12" height="6" rx="2" fill="var(--accent)" opacity="0.30"/>` +
       `<text x="${mL + 18}" y="${He}" class="cp-ax">Current plan</text>` +
       `<rect x="${mL + 110}" y="${He - 4}" width="12" height="6" rx="2" fill="var(--accent-2)"/>` +
       `<text x="${mL + 128}" y="${He}" class="cp-ax">Optimized</text>`;
  const svg = document.getElementById("po-chart");
  svg.setAttribute("viewBox", `0 0 ${W} ${He + 8}`);
  svg.innerHTML = s;
}

function render() {
  const R = optimize();
  window._poR = R;
  const reslab = document.getElementById("po-reslabel").value || "Resource";

  document.getElementById("k-opt").textContent = fmt(R.optC);
  const ku = document.getElementById("k-up");
  ku.textContent = (R.uplift >= 0 ? "+" : "") + fmt(R.uplift) +
    (R.curC > 0 ? `  ·  ${R.uplift >= 0 ? "+" : ""}${R.upliftPct.toFixed(1)}%` : "");
  ku.style.color = R.uplift >= 0 ? "var(--accent-2)" : "var(--loss)";
  const util = R.budget > 0 ? R.optR / R.budget * 100 : 0;
  document.getElementById("k-util").textContent =
    `${fmtU(R.optR)} / ${fmtU(R.budget)}`;
  document.getElementById("k-util").innerHTML +=
    ` <em style="font-weight:400;color:var(--text-dim);font-size:.7rem">${util.toFixed(0)}% used</em>`;
  document.getElementById("k-fund").textContent =
    `${R.funded} / ${R.rows.length}`;

  // insight line
  const movers = R.rows
    .filter((x) => Math.abs(x.opt - x.cur) > 0.5)
    .sort((a, b) => (b.optC - b.curC) - (a.optC - a.curC));
  let msg;
  if (R.minsInfeasible)
    msg = `<strong style="color:var(--loss)">Strategic minimums alone exceed the ${esc(reslab)} budget.</strong> ` +
      `Cut a floor or raise the budget — the plan below assumes minimums are met first.`;
  else if (!movers.length)
    msg = `<strong>Your current plan is already optimal</strong> for this ${esc(reslab)} budget — no reallocation adds contribution.`;
  else {
    const up = movers[0], dn = movers[movers.length - 1];
    msg = `<strong>Biggest move:</strong> shift ${esc(reslab)} toward ` +
      `<b>${esc(up.name)}</b> (${fmtU(up.cur)} → ${fmtU(up.opt)} units). ` +
      (dn.opt < dn.cur - 0.5
        ? `Pull back <b>${esc(dn.name)}</b> (${fmtU(dn.cur)} → ${fmtU(dn.opt)}). `
        : "") +
      `<span>Same ${esc(reslab)}, ${R.uplift >= 0 ? "+" : ""}${fmt(R.uplift)} more contribution.</span>`;
  }
  document.getElementById("po-insight").innerHTML = msg;

  barChart(R);

  // comparison strip
  document.getElementById("po-cmp").innerHTML =
    `<table class="ins-tbl"><tr><th>Plan</th><th>Contribution</th><th>${esc(reslab)} used</th></tr>` +
    `<tr><td>Current</td><td>${fmt(R.curC)}</td><td>${fmtU(R.curR)}` +
      `${R.curR > R.budget + 1e-9 ? ' <em style="color:var(--loss)">over</em>' : ""}</td></tr>` +
    `<tr><td>Optimized ◀</td><td style="color:var(--accent-2);font-weight:600">${fmt(R.optC)}</td>` +
      `<td>${fmtU(R.optR)}</td></tr>` +
    `<tr><td>Difference</td><td style="color:${R.uplift >= 0 ? "var(--accent-2)" : "var(--loss)"};font-weight:600">` +
      `${R.uplift >= 0 ? "+" : ""}${fmt(R.uplift)}</td><td>${R.budget > 0 ? (R.optR / R.budget * 100).toFixed(0) + "%" : "—"}</td></tr>` +
    `</table>`;

  // detail table
  document.getElementById("po-tbody").innerHTML = R.rows.map((x) => {
    const stCol = x.status === "Scale up" ? "var(--accent-2)"
      : x.status === "Scale down" ? "var(--accent)"
      : x.cm <= 0 ? "var(--loss)" : "var(--text-dim)";
    return `<tr><td>${esc(x.name)}</td>` +
      `<td class="num">${fmt(x.cm)}</td>` +
      `<td class="num">${x.res ? x.res.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—"}</td>` +
      `<td class="num">${x.eff === Infinity ? "∞" : fmt(x.eff)}</td>` +
      `<td class="num">${fmtU(x.cur)}</td>` +
      `<td class="num" style="font-weight:600">${fmtU(x.opt)}</td>` +
      `<td class="num">${fmt(x.optC)}</td>` +
      `<td style="color:${stCol};font-weight:600">${x.status}</td></tr>`;
  }).join("");
}

// listeners
document.getElementById("po-industry").addEventListener("change", () => {
  renderLines();
  render();
});
["po-budget", "po-reslabel"].forEach((id) =>
  document.getElementById(id).addEventListener("input", render));
const lc = document.getElementById("po-lines");
lc.addEventListener("input", render);
lc.addEventListener("click", (e) => {
  if (e.target.classList.contains("ln-x")) {
    e.target.closest(".po-line").remove();
    render();
  }
});
document.getElementById("po-add").addEventListener("click", () => {
  lc.insertAdjacentHTML("beforeend",
    pRow({ name: "New product", p: 100, c: 60, r: 2, d: 1000, m: 0, u: 0 }));
  render();
});

function poExport() {
  const R = window._poR || optimize();
  const reslab = document.getElementById("po-reslabel").value || "Resource";
  const F = (f, v) => `<f>${xe(f)}</f><v>${v}</v>`;
  const rows = R.rows;
  const PS = 7;                       // first product row
  const PE = PS + rows.length - 1;
  const TOT = PE + 1;

  let sd =
    `<row r="1"><c r="A1" t="inlineStr" s="2"><is><t>Product Portfolio Optimizer — maximise contribution within a ${xe(reslab)} budget</t></is></c></row><row r="2"/>` +
    `<row r="3"><c r="A3" t="inlineStr" s="1"><is><t>${xe(reslab)} budget</t></is></c><c r="B3" s="4"><v>${Math.round(R.budget)}</v></c>` +
      `<c r="D3" t="inlineStr" s="3"><is><t>Optimized units are computed by the tool (greedy by contribution per ${xe(reslab)}); all € figures recalculate live.</t></is></c></row>` +
    `<row r="4"/>` +
    `<row r="6">` +
    ["Product","Price/unit","Cost/unit","Contrib/unit","Res/unit","Max demand","Min units","Current units","Optimized units","Current contrib","Optimized contrib","Res used"]
      .map((h, i) => `<c r="${String.fromCharCode(65 + i)}6" t="inlineStr" s="2"><is><t>${h}</t></is></c>`).join("") +
    `</row>`;
  rows.forEach((x, i) => {
    const rr = PS + i;
    sd += `<row r="${rr}">` +
      `<c r="A${rr}" t="inlineStr" s="3"><is><t>${xe(x.name)}</t></is></c>` +
      `<c r="B${rr}" s="4"><v>${x.p}</v></c>` +
      `<c r="C${rr}" s="4"><v>${x.c}</v></c>` +
      `<c r="D${rr}" s="4">${F(`B${rr}-C${rr}`, Math.round(x.cm))}</c>` +
      `<c r="E${rr}" s="5"><v>${x.res}</v></c>` +
      `<c r="F${rr}" s="6"><v>${Math.round(x.d)}</v></c>` +
      `<c r="G${rr}" s="6"><v>${Math.round(x.m)}</v></c>` +
      `<c r="H${rr}" s="6"><v>${Math.round(x.cur)}</v></c>` +
      `<c r="I${rr}" s="7"><v>${Math.round(x.opt)}</v></c>` +
      `<c r="J${rr}" s="4">${F(`D${rr}*H${rr}`, Math.round(x.curC))}</c>` +
      `<c r="K${rr}" s="4">${F(`D${rr}*I${rr}`, Math.round(x.optC))}</c>` +
      `<c r="L${rr}" s="6">${F(`E${rr}*I${rr}`, Math.round(x.optR))}</c></row>`;
  });
  sd += `<row r="${TOT}"><c r="A${TOT}" t="inlineStr" s="2"><is><t>Total</t></is></c>` +
    `<c r="J${TOT}" s="8">${F(`SUM(J${PS}:J${PE})`, Math.round(R.curC))}</c>` +
    `<c r="K${TOT}" s="8">${F(`SUM(K${PS}:K${PE})`, Math.round(R.optC))}</c>` +
    `<c r="L${TOT}" s="8">${F(`SUM(L${PS}:L${PE})`, Math.round(R.optR))}</c></row>` +
    `<row r="${TOT + 1}"/>` +
    `<row r="${TOT + 2}"><c r="A${TOT + 2}" t="inlineStr" s="1"><is><t>Contribution uplift</t></is></c>` +
      `<c r="B${TOT + 2}" s="8">${F(`K${TOT}-J${TOT}`, Math.round(R.uplift))}</c></row>` +
    `<row r="${TOT + 3}"><c r="A${TOT + 3}" t="inlineStr" s="1"><is><t>${xe(reslab)} utilisation</t></is></c>` +
      `<c r="B${TOT + 3}" s="5">${F(`L${TOT}/B3`, R.budget > 0 ? Math.round(R.optR / R.budget * 100) / 100 : 0)}</c></row>`;

  const sheet =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
    `<cols><col min="1" max="1" width="28"/><col min="2" max="12" width="13"/></cols>` +
    `<sheetData>${sd}</sheetData>` +
    `<mergeCells count="1"><mergeCell ref="A1:L1"/></mergeCells>` +
    `<drawing r:id="rId1"/></worksheet>`;

  const SN = "'Portfolio'";
  const ser = (idx, nameCell, valRange, color) =>
    `<c:ser><c:idx val="${idx}"/><c:order val="${idx}"/>` +
    `<c:tx><c:strRef><c:f>${SN}!${nameCell}</c:f></c:strRef></c:tx>` +
    `<c:spPr><a:solidFill><a:srgbClr val="${color}"/></a:solidFill></c:spPr>` +
    `<c:cat><c:strRef><c:f>${SN}!$A$${PS}:$A$${PE}</c:f></c:strRef></c:cat>` +
    `<c:val><c:numRef><c:f>${SN}!${valRange}</c:f></c:numRef></c:val></c:ser>`;
  const chartXml =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
    `<c:chart><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Contribution — current vs optimized</a:t></a:r></a:p></c:rich></c:tx><c:overlay val="0"/></c:title>` +
    `<c:autoTitleDeleted val="0"/><c:plotArea><c:layout/>` +
    `<c:barChart><c:barDir val="bar"/><c:grouping val="clustered"/><c:varyColors val="0"/>` +
    ser(0, `$J$6`, `$J$${PS}:$J$${PE}`, "9CC3E8") +
    ser(1, `$K$6`, `$K$${PS}:$K$${PE}`, "19C37D") +
    `<c:axId val="111111111"/><c:axId val="222222222"/></c:barChart>` +
    `<c:catAx><c:axId val="111111111"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:crossAx val="222222222"/></c:catAx>` +
    `<c:valAx><c:axId val="222222222"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:crossAx val="111111111"/></c:valAx>` +
    `</c:plotArea><c:legend><c:legendPos val="b"/><c:overlay val="0"/></c:legend><c:plotVisOnly val="1"/></c:chart></c:chartSpace>`;
  const drawingXml =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">` +
    `<xdr:twoCellAnchor editAs="oneCell">` +
    `<xdr:from><xdr:col>13</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>5</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>` +
    `<xdr:to><xdr:col>24</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>27</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>` +
    `<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="PortfolioChart"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>` +
    `<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>` +
    `<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">` +
    `<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId1"/>` +
    `</a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>`;
  const styles =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0;(#,##0)"/><numFmt numFmtId="165" formatCode="0.00"/></numFmts>` +
    `<fonts count="3"><font><sz val="11"/><name val="Calibri"/><color rgb="FF1F2937"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>` +
    `<font><b/><sz val="13"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font></fonts>` +
    `<fills count="4"><fill><patternFill patternType="none"/></fill>` +
    `<fill><patternFill patternType="gray125"/></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FF2F9BFF"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FFEAF4FF"/></patternFill></fill></fills>` +
    `<borders count="1"><border/></borders>` +
    `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>` +
    `<cellXfs count="9">` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `<xf numFmtId="164" fontId="0" fillId="3" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1"/>` +
    `<xf numFmtId="164" fontId="1" fillId="2" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1"/>` +
    `</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
  const files = [
    { name: "[Content_Types].xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/><Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/></Types>`) },
    { name: "_rels/.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
    { name: "xl/workbook.xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Portfolio" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
    { name: "xl/_rels/workbook.xml.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
    { name: "xl/styles.xml", data: u8(styles) },
    { name: "xl/worksheets/sheet1.xml", data: u8(sheet) },
    { name: "xl/worksheets/_rels/sheet1.xml.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>`) },
    { name: "xl/drawings/drawing1.xml", data: u8(drawingXml) },
    { name: "xl/drawings/_rels/drawing1.xml.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/></Relationships>`) },
    { name: "xl/charts/chart1.xml", data: u8(chartXml) },
  ];
  const url = URL.createObjectURL(zip(files));
  const a = document.createElement("a");
  a.href = url; a.download = "portfolio-optimizer.xlsx";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
document.getElementById("po-export").addEventListener("click", poExport);

renderLines();
render();
