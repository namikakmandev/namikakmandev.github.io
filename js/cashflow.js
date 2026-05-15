// ---- Cash Flow & Runway Simulator ----
const H = 12;
const MON = ["M1","M2","M3","M4","M5","M6","M7","M8","M9","M10","M11","M12"];
const SCEN = {
  best:  { sales: 1.10, cost: 0.95, label: "Best" },
  base:  { sales: 1.00, cost: 1.00, label: "Base" },
  worst: { sales: 0.85, cost: 1.10, label: "Worst" },
};
let scenario = "base";

const num = (id) => {
  const v = parseFloat(document.getElementById(id).value);
  return isNaN(v) ? 0 : v;
};
const sliders = () => {
  const o = {};
  document.querySelectorAll(".cf-inputs .se-slider").forEach((el) => {
    o[el.dataset.k] = +el.querySelector("input").value;
  });
  return o;
};
const fmt = (n) =>
  (n < 0 ? "-" : "") + "€" +
  Math.round(Math.abs(n)).toLocaleString(undefined, { maximumFractionDigits: 0 });

// ---- Editable line items ----
const INDUSTRIES = {
  generic: {
    in: [
      { name: "Product sales", amt: 50000, g: 3 },
      { name: "Services", amt: 12000, g: 2 },
    ],
    out: [
      { name: "Salaries", type: "fixed", val: 35000 },
      { name: "Rent & office", type: "fixed", val: 12000 },
      { name: "Marketing", type: "fixed", val: 8000 },
      { name: "COGS", type: "pct", val: 35 },
    ],
  },
  saas: {
    in: [
      { name: "Subscription (recurring)", amt: 60000, g: 6 },
      { name: "Expansion / upsell", amt: 9000, g: 8 },
      { name: "Professional services", amt: 8000, g: 2 },
    ],
    out: [
      { name: "Engineering & product", type: "fixed", val: 42000 },
      { name: "Sales & marketing", type: "fixed", val: 30000 },
      { name: "G&A", type: "fixed", val: 14000 },
      { name: "Cloud / infrastructure", type: "pct", val: 12 },
    ],
  },
  retail: {
    in: [
      { name: "In-store sales", amt: 70000, g: 1.5 },
      { name: "Online sales", amt: 45000, g: 5 },
    ],
    out: [
      { name: "COGS", type: "pct", val: 55 },
      { name: "Store rent & utilities", type: "fixed", val: 22000 },
      { name: "Staff wages", type: "fixed", val: 30000 },
      { name: "Marketing", type: "fixed", val: 10000 },
      { name: "Fulfilment / logistics", type: "pct", val: 8 },
    ],
  },
  manufacturing: {
    in: [
      { name: "Product sales", amt: 110000, g: 2 },
      { name: "Spare parts & service", amt: 18000, g: 3 },
    ],
    out: [
      { name: "Raw materials (COGS)", type: "pct", val: 45 },
      { name: "Direct labour", type: "fixed", val: 38000 },
      { name: "Factory overhead", type: "fixed", val: 24000 },
      { name: "SG&A", type: "fixed", val: 20000 },
      { name: "Logistics", type: "pct", val: 7 },
    ],
  },
  services: {
    in: [
      { name: "Project fees", amt: 70000, g: 3 },
      { name: "Retainers", amt: 25000, g: 1 },
    ],
    out: [
      { name: "Consultant salaries", type: "fixed", val: 55000 },
      { name: "Subcontractors", type: "pct", val: 18 },
      { name: "Office & tools", type: "fixed", val: 12000 },
      { name: "Travel & expenses", type: "pct", val: 6 },
      { name: "G&A", type: "fixed", val: 9000 },
    ],
  },
  pharma: {
    in: [
      { name: "Product sales", amt: 130000, g: 2.5 },
      { name: "Tenders & contracts", amt: 30000, g: 1 },
    ],
    out: [
      { name: "COGS", type: "pct", val: 30 },
      { name: "Field force & medical", type: "fixed", val: 60000 },
      { name: "Marketing & education", type: "fixed", val: 22000 },
      { name: "Distribution", type: "pct", val: 8 },
      { name: "Regulatory & compliance", type: "fixed", val: 14000 },
    ],
  },
  hospitality: {
    in: [
      { name: "Rooms / F&B revenue", amt: 85000, g: 2 },
      { name: "Events & catering", amt: 20000, g: 3 },
    ],
    out: [
      { name: "Food & beverage cost", type: "pct", val: 32 },
      { name: "Staff wages", type: "fixed", val: 34000 },
      { name: "Rent & utilities", type: "fixed", val: 20000 },
      { name: "Marketing & OTA fees", type: "pct", val: 9 },
    ],
  },
};
const esc = (s) => String(s).replace(/"/g, "&quot;");
function inRow(d) {
  return `<div class="cf-line"><input class="ln-name" value="${esc(d.name)}" />` +
    `<input class="ln-amt" type="number" step="500" value="${d.amt}" title="€ / month" />` +
    `<input class="ln-g" type="number" step="0.5" value="${d.g}" title="monthly growth %" />` +
    `<button class="ln-x" type="button" title="remove">×</button></div>`;
}
function outRow(d) {
  return `<div class="cf-line"><input class="ln-name" value="${esc(d.name)}" />` +
    `<select class="ln-type"><option value="fixed"${d.type === "fixed" ? " selected" : ""}>Fixed €</option>` +
    `<option value="pct"${d.type === "pct" ? " selected" : ""}>% inflow</option></select>` +
    `<input class="ln-val" type="number" step="${d.type === "pct" ? 1 : 500}" value="${d.val}" />` +
    `<button class="ln-x" type="button" title="remove">×</button></div>`;
}
function renderLines() {
  const key = document.getElementById("cf-industry").value || "generic";
  const t = INDUSTRIES[key] || INDUSTRIES.generic;
  document.getElementById("cf-inflows").innerHTML = t.in.map(inRow).join("");
  document.getElementById("cf-outflows").innerHTML = t.out.map(outRow).join("");
}
function gatherIn() {
  return [...document.querySelectorAll("#cf-inflows .cf-line")].map((r) => ({
    amt: parseFloat(r.querySelector(".ln-amt").value) || 0,
    g: (parseFloat(r.querySelector(".ln-g").value) || 0) / 100,
  }));
}
function gatherOut() {
  return [...document.querySelectorAll("#cf-outflows .cf-line")].map((r) => ({
    type: r.querySelector(".ln-type").value,
    val: parseFloat(r.querySelector(".ln-val").value) || 0,
  }));
}

// Build the 12-month projection for a given scenario key
function project(sKey) {
  const s = SCEN[sKey];
  const sl = sliders();
  const salesMult = s.sales * (1 + sl.sales / 100);
  const costMult = s.cost * (1 + sl.cost / 100);
  const k = Math.min(1, sl.delay / 30); // fraction of a month's inflow that slips

  const cash0 = num("i-cash");
  const ins = gatherIn();
  const outs = gatherOut();
  const fixedSum = outs.filter((o) => o.type === "fixed").reduce((t, o) => t + o.val, 0);
  const pctSum = outs.filter((o) => o.type === "pct").reduce((t, o) => t + o.val, 0) / 100;

  const rows = [];
  let prevClose = cash0, prevGross = 0;
  for (let m = 0; m < H; m++) {
    const gross =
      ins.reduce((t, ln) => t + ln.amt * Math.pow(1 + ln.g, m), 0) * salesMult;
    const received = (1 - k) * gross + k * prevGross;
    const outflow = (fixedSum + pctSum * gross) * costMult;
    const opening = m === 0 ? cash0 : prevClose;
    const net = received - outflow;
    const closing = opening + net;
    rows.push({ m: m + 1, opening, inflow: received, outflow, net, closing });
    prevClose = closing;
    prevGross = gross;
  }
  // runway = last month index that is still >= 0 (consecutive from start)
  let runway = H;
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].closing < 0) { runway = i; break; }
  }
  const low = rows.reduce((a, b) => (b.closing < a.closing ? b : a), rows[0]);
  return {
    rows, runway,
    low: low.closing, lowM: low.m,
    end: rows[H - 1].closing,
    cumNet: rows.reduce((t, r) => t + r.net, 0),
  };
}

function svg(id, content, vb) {
  const el = document.getElementById(id);
  if (vb) el.setAttribute("viewBox", vb);
  el.innerHTML = content;
}

function drawChart(p) {
  const W = 900, He = 360, mL = 70, mR = 16, mT = 18, mB = 34;
  const pw = W - mL - mR, ph = He - mT - mB;
  const vals = p.rows.map((r) => r.closing).concat([0, num("i-cash")]);
  const max = Math.max(...vals), min = Math.min(...vals);
  const span = max - min || 1;
  const X = (i) => mL + (i / (H - 1)) * pw;
  const Y = (v) => mT + ph - ((v - min) / span) * ph;
  const y0 = Y(0);
  let s = "";
  // zero line
  s += `<line x1="${mL}" y1="${y0.toFixed(1)}" x2="${mL + pw}" y2="${y0.toFixed(1)}" stroke="var(--loss)" stroke-dasharray="4 4" opacity="0.7"/>`;
  s += `<text x="${mL - 8}" y="${y0.toFixed(1)}" text-anchor="end" dominant-baseline="middle" class="cp-ax">0</text>`;
  // area + line
  let area = `M ${X(0).toFixed(1)} ${y0.toFixed(1)} `;
  let line = "";
  p.rows.forEach((r, i) => {
    const x = X(i), y = Y(r.closing);
    area += `L ${x.toFixed(1)} ${y.toFixed(1)} `;
    line += (i ? "L" : "M") + ` ${x.toFixed(1)} ${y.toFixed(1)} `;
  });
  area += `L ${X(H - 1).toFixed(1)} ${y0.toFixed(1)} Z`;
  s += `<path d="${area}" fill="var(--accent)" opacity="0.10"/>`;
  s += `<path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2.5"/>`;
  // points
  p.rows.forEach((r, i) => {
    const neg = r.closing < 0;
    s += `<circle cx="${X(i).toFixed(1)}" cy="${Y(r.closing).toFixed(1)}" r="4" style="fill:${neg ? "var(--loss)" : "var(--accent)"}"><title>Month ${r.m}: ${fmt(r.closing)}</title></circle>`;
    s += `<text x="${X(i).toFixed(1)}" y="${He - 12}" text-anchor="middle" class="cp-ax">${r.m}</text>`;
  });
  // runway marker
  if (p.runway < H) {
    const rx = X(p.runway);
    s += `<line x1="${rx.toFixed(1)}" y1="${mT}" x2="${rx.toFixed(1)}" y2="${mT + ph}" stroke="var(--loss)" stroke-width="1.5"/>`;
    s += `<text x="${(rx + 6).toFixed(1)}" y="${mT + 12}" class="cp-ax" style="fill:var(--loss)">cash runs out</text>`;
  }
  svg("cf-chart", s);
}

function render() {
  const p = project(scenario);
  document.getElementById("cf-scen-lbl").textContent = "(" + SCEN[scenario].label + ")";
  document.getElementById("cf-tbl-lbl").textContent = "(" + SCEN[scenario].label + ")";

  document.getElementById("k-runway").textContent =
    p.runway >= H ? "12+ months" : p.runway + (p.runway === 1 ? " month" : " months");
  const kr = document.getElementById("k-runway");
  kr.style.color = p.runway >= H ? "var(--accent-2)" : "var(--loss)";
  document.getElementById("k-low").innerHTML =
    fmt(p.low) + ' <em style="font-weight:400;color:var(--text-dim);font-size:.7rem">@ M' + p.lowM + "</em>";
  document.getElementById("k-low").style.color = p.low < 0 ? "var(--loss)" : "var(--text)";
  document.getElementById("k-end").textContent = fmt(p.end);
  document.getElementById("k-end").style.color = p.end < 0 ? "var(--loss)" : "var(--text)";
  document.getElementById("k-net").textContent = fmt(p.cumNet);

  drawChart(p);

  // scenario comparison
  const cmp = ["best", "base", "worst"].map((sk) => {
    const q = project(sk);
    return { sk, label: SCEN[sk].label,
      run: q.runway >= H ? "12+" : q.runway + "m", end: q.end };
  });
  document.getElementById("cf-cmp").innerHTML =
    `<table class="ins-tbl"><tr><th>Scenario</th><th>Runway</th><th>Ending cash</th></tr>` +
    cmp.map((c) =>
      `<tr><td>${c.label}${c.sk === scenario ? " ◀" : ""}</td><td>${c.run}</td>` +
      `<td style="color:${c.end < 0 ? "var(--loss)" : "var(--text)"}">${fmt(c.end)}</td></tr>`).join("") +
    `</table>`;

  // table
  document.getElementById("cf-tbody").innerHTML = p.rows.map((r) =>
    `<tr><td>M${r.m}</td><td class="num">${fmt(r.opening)}</td>` +
    `<td class="num">${fmt(r.inflow)}</td><td class="num">${fmt(r.outflow)}</td>` +
    `<td class="num">${fmt(r.net)}</td>` +
    `<td class="num" style="color:${r.closing < 0 ? "var(--loss)" : "var(--text)"};font-weight:600">${fmt(r.closing)}</td></tr>`
  ).join("");
  window._cfP = p;
}

// listeners
document.getElementById("cf-industry").addEventListener("change", () => {
  renderLines();
  render();
});
document.getElementById("i-cash").addEventListener("input", render);
["cf-inflows", "cf-outflows"].forEach((id) => {
  const c = document.getElementById(id);
  c.addEventListener("input", render);
  c.addEventListener("change", render);
  c.addEventListener("click", (e) => {
    if (e.target.classList.contains("ln-x")) {
      e.target.closest(".cf-line").remove();
      render();
    }
  });
});
document.querySelectorAll(".cf-add").forEach((btn) =>
  btn.addEventListener("click", () => {
    if (btn.dataset.list === "in")
      document.getElementById("cf-inflows").insertAdjacentHTML(
        "beforeend", inRow({ name: "New inflow", amt: 0, g: 0 }));
    else
      document.getElementById("cf-outflows").insertAdjacentHTML(
        "beforeend", outRow({ name: "New cost", type: "fixed", val: 0 }));
    render();
  }));
document.querySelectorAll(".cf-inputs .se-slider input").forEach((inp) =>
  inp.addEventListener("input", (e) => {
    const sl = e.target.closest(".se-slider");
    const k = sl.dataset.k;
    const v = e.target.value;
    sl.querySelector("b").textContent = k === "delay" ? v + " days" : v + "%";
    render();
  }));
document.getElementById("cf-scenario").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-s]");
  if (!b) return;
  scenario = b.dataset.s;
  document.querySelectorAll("#cf-scenario button").forEach((x) =>
    x.classList.toggle("on", x === b));
  render();
});

// ---- Excel export (compact in-browser writer) ----
const _ct = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crc32(b){let c=0xffffffff;for(let i=0;i<b.length;i++)c=_ct[(c^b[i])&0xff]^(c>>>8);return (c^0xffffffff)>>>0;}
const u8 = (s) => new TextEncoder().encode(s);
function zip(files){const parts=[],cen=[];let off=0;files.forEach((f)=>{const nm=u8(f.name),d=f.data,crc=crc32(d);const lh=new DataView(new ArrayBuffer(30));lh.setUint32(0,0x04034b50,true);lh.setUint16(4,20,true);lh.setUint32(14,crc,true);lh.setUint32(18,d.length,true);lh.setUint32(22,d.length,true);lh.setUint16(26,nm.length,true);parts.push(new Uint8Array(lh.buffer),nm,d);const ch=new DataView(new ArrayBuffer(46));ch.setUint32(0,0x02014b50,true);ch.setUint16(4,20,true);ch.setUint16(6,20,true);ch.setUint32(16,crc,true);ch.setUint32(20,d.length,true);ch.setUint32(24,d.length,true);ch.setUint16(28,nm.length,true);ch.setUint32(42,off,true);cen.push(new Uint8Array(ch.buffer),nm);off+=30+nm.length+d.length;});let cs=0;cen.forEach((c)=>(cs+=c.length));const e=new DataView(new ArrayBuffer(22));e.setUint32(0,0x06054b50,true);e.setUint16(8,files.length,true);e.setUint16(10,files.length,true);e.setUint32(12,cs,true);e.setUint32(16,off,true);return new Blob([...parts,...cen,new Uint8Array(e.buffer)],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});}
const xe = (s) => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

function cfExport() {
  const p = window._cfP || project(scenario);
  const H1 = ["Month", "Opening", "Inflow", "Outflow", "Net", "Closing"];
  let sd =
    `<row r="1"><c r="A1" t="inlineStr" s="1"><is><t>Cash Flow &amp; Runway — ${xe(SCEN[scenario].label)} scenario</t></is></c></row><row r="2"/>` +
    `<row r="3">` + H1.map((h, i) =>
      `<c r="${String.fromCharCode(65 + i)}3" t="inlineStr" s="2"><is><t>${xe(h)}</t></is></c>`).join("") + `</row>`;
  p.rows.forEach((r, i) => {
    const rn = i + 4;
    sd += `<row r="${rn}">` +
      `<c r="A${rn}" t="inlineStr" s="3"><is><t>M${r.m}</t></is></c>` +
      `<c r="B${rn}" s="4"><v>${Math.round(r.opening)}</v></c>` +
      `<c r="C${rn}" s="4"><v>${Math.round(r.inflow)}</v></c>` +
      `<c r="D${rn}" s="4"><v>${Math.round(r.outflow)}</v></c>` +
      `<c r="E${rn}" s="4"><v>${Math.round(r.net)}</v></c>` +
      `<c r="F${rn}" s="4"><v>${Math.round(r.closing)}</v></c></row>`;
  });
  const rn = p.rows.length + 5;
  sd += `<row r="${rn}"><c r="A${rn}" t="inlineStr" s="2"><is><t>Runway</t></is></c>` +
    `<c r="B${rn}" t="inlineStr" s="3"><is><t>${p.runway >= H ? "12+ months" : p.runway + " months"}</t></is></c></row>`;
  const lastRow = p.rows.length + 3; // data rows 4..15
  const sheet =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
    `<cols><col min="1" max="1" width="10"/><col min="2" max="6" width="15"/></cols>` +
    `<sheetData>${sd}</sheetData>` +
    `<mergeCells count="1"><mergeCell ref="A1:F1"/></mergeCells>` +
    `<drawing r:id="rId1"/></worksheet>`;

  const SN = "'Cash Flow'";
  const lser = (idx, nameCell, valRange, color) =>
    `<c:ser><c:idx val="${idx}"/><c:order val="${idx}"/>` +
    `<c:tx><c:strRef><c:f>${SN}!${nameCell}</c:f></c:strRef></c:tx>` +
    `<c:spPr><a:ln w="22000"><a:solidFill><a:srgbClr val="${color}"/></a:solidFill></a:ln></c:spPr>` +
    `<c:marker><c:symbol val="circle"/><c:size val="5"/><c:spPr><a:solidFill><a:srgbClr val="${color}"/></a:solidFill></c:spPr></c:marker>` +
    `<c:cat><c:strRef><c:f>${SN}!$A$4:$A$${lastRow}</c:f></c:strRef></c:cat>` +
    `<c:val><c:numRef><c:f>${SN}!${valRange}</c:f></c:numRef></c:val></c:ser>`;
  const chartXml =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
    `<c:chart><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Projected cash — ${xe(SCEN[scenario].label)}</a:t></a:r></a:p></c:rich></c:tx><c:overlay val="0"/></c:title>` +
    `<c:autoTitleDeleted val="0"/><c:plotArea><c:layout/>` +
    `<c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>` +
    lser(0, "$F$3", "$F$4:$F$" + lastRow, "2F9BFF") +
    lser(1, "$E$3", "$E$4:$E$" + lastRow, "19C37D") +
    `<c:marker val="1"/><c:axId val="111111111"/><c:axId val="222222222"/></c:lineChart>` +
    `<c:catAx><c:axId val="111111111"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:crossAx val="222222222"/></c:catAx>` +
    `<c:valAx><c:axId val="222222222"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:crossAx val="111111111"/></c:valAx>` +
    `</c:plotArea><c:legend><c:legendPos val="b"/><c:overlay val="0"/></c:legend><c:plotVisOnly val="1"/></c:chart></c:chartSpace>`;
  const drawingXml =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">` +
    `<xdr:twoCellAnchor editAs="oneCell">` +
    `<xdr:from><xdr:col>7</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>2</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>` +
    `<xdr:to><xdr:col>17</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>22</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>` +
    `<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="CashChart"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>` +
    `<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>` +
    `<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">` +
    `<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId1"/>` +
    `</a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>`;
  const styles =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0;(#,##0)"/></numFmts>` +
    `<fonts count="3"><font><sz val="11"/><name val="Calibri"/><color rgb="FF1F2937"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>` +
    `<font><b/><sz val="13"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font></fonts>` +
    `<fills count="3"><fill><patternFill patternType="none"/></fill>` +
    `<fill><patternFill patternType="gray125"/></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FF2F9BFF"/></patternFill></fill></fills>` +
    `<borders count="1"><border/></borders>` +
    `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>` +
    `<cellXfs count="5">` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
  const files = [
    { name: "[Content_Types].xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/><Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/></Types>`) },
    { name: "_rels/.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
    { name: "xl/workbook.xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Cash Flow" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
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
  a.href = url; a.download = "cash-flow-runway.xlsx";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
document.getElementById("cf-export").addEventListener("click", cfExport);

renderLines();
render();
