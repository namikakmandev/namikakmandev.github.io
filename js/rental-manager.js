// ---- Rental Portfolio Manager ----
// A browser-only CRM for a short-term / summer rental business.
// Nothing is uploaded; all state lives in this page.

const $ = (id) => document.getElementById(id);
const DAY = 86400000;
const today = new Date();
today.setHours(0, 0, 0, 0);

let BOOKINGS = [];

// ---------- helpers ----------
const pad = (n) => String(n).padStart(2, "0");
const iso = (d) => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
const parseD = (s) => {
  const d = new Date(s + "T00:00:00");
  return isNaN(d) ? null : d;
};
const addDays = (d, n) => new Date(d.getTime() + n * DAY);
function money(n) {
  const sym = $("rm-cur").value;
  const s = Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
  return (n < 0 ? "-" : "") + (sym ? sym + " " : "") + s.replace("-", "");
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// ---------- sample portfolios ----------
const REGIONS = ["Seafront", "Old town", "Hillside", "Lakeside", "Marina"];
const NAMES = ["Aydın", "Maria", "John", "Lena", "Carlos", "Sofia", "Ahmet",
  "Emma", "Luca", "Nora", "Pavel", "Yuki", "Omar", "Clara", "Ivan", "Mei"];

function makePortfolio(kind) {
  const cfg = {
    coast:    { n: 20, label: "Coast Villa", base: 140, span: 7, clean: 70 },
    city:     { n: 12, label: "City Flat",   base: 95,  span: 4, clean: 45 },
    mountain: { n: 8,  label: "Chalet",      base: 175, span: 6, clean: 85 },
  }[kind];
  const list = [];
  const seasonStart = new Date(today.getFullYear(), 5, 1); // 1 June
  for (let i = 0; i < cfg.n; i++) {
    const prop = cfg.label + " " + pad(i + 1);
    const rate = cfg.base + ((i * 17) % 90); // deterministic spread
    // main summer booking
    const ci = addDays(seasonStart, (i * 11) % 90);
    const co = addDays(ci, cfg.span + (i % 3));
    list.push({
      prop, guest: NAMES[i % NAMES.length] + " " + NAMES[(i + 5) % NAMES.length][0] + ".",
      ci: iso(ci), co: iso(co), rate, clean: cfg.clean,
      status: "Confirmed", cleaned: false,
    });
    // every 3rd property: a past stay still needing its turnover (cleaning due)
    if (i % 3 === 0) {
      const pco = addDays(today, -(3 + (i % 9)));
      const pci = addDays(pco, -(cfg.span));
      list.push({
        prop, guest: NAMES[(i + 2) % NAMES.length] + " " + NAMES[(i + 9) % NAMES.length][0] + ".",
        ci: iso(pci), co: iso(pco), rate, clean: cfg.clean,
        status: "Checked-out", cleaned: false,
      });
    }
    // every 7th: a cancelled booking (excluded from totals)
    if (i % 7 === 3) {
      const cci = addDays(seasonStart, 40 + i);
      list.push({
        prop, guest: NAMES[(i + 4) % NAMES.length] + " C.",
        ci: iso(cci), co: iso(addDays(cci, cfg.span)), rate, clean: cfg.clean,
        status: "Cancelled", cleaned: false,
      });
    }
  }
  return list;
}

// ---------- per-booking computation ----------
function calc(b) {
  const ci = parseD(b.ci), co = parseD(b.co);
  const nights = ci && co ? Math.max(0, Math.round((co - ci) / DAY)) : 0;
  const active = b.status !== "Cancelled";
  const rent = nights * (+b.rate || 0);
  const cleanFee = +b.clean || 0;
  const net = rent - cleanFee;
  const cleaningDue =
    active && !b.cleaned && (b.status === "Checked-out" || (co && co < today));
  const soon =
    active && b.status === "Confirmed" && ci && ci >= today && ci <= addDays(today, 14);
  return { nights, active, rent, cleanFee, net, cleaningDue, soon };
}

// ---------- KPIs + chart ----------
function recompute() {
  let rev = 0, clean = 0, due = 0, soon = 0, bookedNights = 0, activeCount = 0;
  let minCI = null, maxCO = null;
  const props = new Set();
  const netByProp = {};

  BOOKINGS.forEach((b) => {
    props.add(b.prop || "—");
    const c = calc(b);
    if (!c.active) return;
    activeCount++;
    rev += c.rent;
    clean += c.cleanFee;
    bookedNights += c.nights;
    if (c.cleaningDue) due++;
    if (c.soon) soon++;
    netByProp[b.prop || "—"] = (netByProp[b.prop || "—"] || 0) + c.net;
    const ci = parseD(b.ci), co = parseD(b.co);
    if (ci && (!minCI || ci < minCI)) minCI = ci;
    if (co && (!maxCO || co > maxCO)) maxCO = co;
  });

  const nProps = props.size || 1;
  const spanDays = minCI && maxCO ? Math.max(1, Math.round((maxCO - minCI) / DAY)) : 1;
  const capacity = nProps * spanDays;
  const occ = capacity > 0 ? (bookedNights / capacity) * 100 : 0;

  $("k-rev").textContent = money(rev);
  $("k-clean").textContent = money(clean);
  $("k-net").textContent = money(rev - clean);
  $("k-occ").textContent = occ.toFixed(0) + "%";
  $("k-props").textContent = props.size;
  $("k-book").textContent = activeCount;
  $("k-due").textContent = due;
  $("k-due").style.color = due > 0 ? "var(--accent-3)" : "var(--accent-2)";
  $("k-soon").textContent = soon;

  drawBars(netByProp);
}

function drawBars(map) {
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 12);
  const rowH = 30, mT = 8, mL = 150, mR = 90, W = 720;
  const H = Math.max(80, mT * 2 + entries.length * rowH);
  const max = Math.max(...entries.map((e) => e[1]), 1);
  const pw = W - mL - mR;
  let s = "";
  entries.forEach(([k, v], i) => {
    const y = mT + i * rowH;
    const bw = Math.max(2, (Math.max(v, 0) / max) * pw);
    s += `<text x="${mL - 8}" y="${y + rowH / 2}" text-anchor="end" dominant-baseline="middle">${esc(k)}</text>`;
    s += `<rect x="${mL}" y="${y + 5}" width="${bw.toFixed(1)}" height="${rowH - 12}" rx="3" style="fill:var(--accent-2)"/>`;
    s += `<text x="${mL + bw + 6}" y="${y + rowH / 2}" dominant-baseline="middle">${money(v)}</text>`;
  });
  const svg = $("rm-bars");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = s || `<text x="20" y="40">No active bookings</text>`;
  $("rm-chart-sub").textContent = entries.length
    ? "(top " + entries.length + " by net)" : "";
}

// ---------- table ----------
function visibleIndexes() {
  const fp = $("f-prop").value, fs = $("f-status").value;
  const out = [];
  BOOKINGS.forEach((b, i) => {
    if (fp && b.prop !== fp) return;
    if (fs && b.status !== fs) return;
    out.push(i);
  });
  return out;
}

function statusSel(v) {
  return ["Confirmed", "Checked-out", "Cancelled"]
    .map((o) => `<option${o === v ? " selected" : ""}>${o}</option>`).join("");
}

function rowHTML(i) {
  const b = BOOKINGS[i];
  return (
    `<tr data-i="${i}">` +
    `<td><input data-f="prop" value="${esc(b.prop)}" /></td>` +
    `<td><input data-f="guest" value="${esc(b.guest)}" /></td>` +
    `<td><input data-f="ci" type="date" value="${esc(b.ci)}" /></td>` +
    `<td><input data-f="co" type="date" value="${esc(b.co)}" /></td>` +
    `<td class="calc c-nights">—</td>` +
    `<td><input data-f="rate" type="number" min="0" step="5" value="${+b.rate || 0}" /></td>` +
    `<td><input data-f="clean" type="number" min="0" step="5" value="${+b.clean || 0}" /></td>` +
    `<td><select data-f="status">${statusSel(b.status)}</select></td>` +
    `<td><select data-f="cleaned"><option value="no"${b.cleaned ? "" : " selected"}>No</option>` +
    `<option value="yes"${b.cleaned ? " selected" : ""}>Yes</option></select></td>` +
    `<td class="calc c-rent">—</td>` +
    `<td class="calc c-net">—</td>` +
    `<td class="c-flag">—</td>` +
    `<td><button class="rm-x" title="Remove" data-x="${i}">×</button></td>` +
    `</tr>`
  );
}

function refreshRow(tr) {
  const b = BOOKINGS[+tr.dataset.i];
  const c = calc(b);
  tr.querySelector(".c-nights").textContent = c.nights;
  tr.querySelector(".c-rent").textContent = c.active ? money(c.rent) : "—";
  tr.querySelector(".c-net").textContent = c.active ? money(c.net) : "—";
  const flag = tr.querySelector(".c-flag");
  if (!c.active) flag.innerHTML = `<span class="rm-flag">cancelled</span>`;
  else if (c.cleaningDue) flag.innerHTML = `<span class="rm-flag due">cleaning due</span>`;
  else flag.innerHTML = `<span class="rm-flag ok">ok</span>`;
}

function buildTable() {
  const idx = visibleIndexes();
  $("rm-tbody").innerHTML = idx.map(rowHTML).join("") ||
    `<tr><td colspan="13" style="text-align:center;color:var(--text-dim);padding:18px">No bookings match the filters.</td></tr>`;
  $("rm-count").textContent =
    "(" + idx.length + " of " + BOOKINGS.length + ")";
  document.querySelectorAll("#rm-tbody tr[data-i]").forEach(refreshRow);
}

function refreshAll() {
  recompute();
  document.querySelectorAll("#rm-tbody tr[data-i]").forEach(refreshRow);
  $("rm-count").textContent =
    "(" + visibleIndexes().length + " of " + BOOKINGS.length + ")";
}

function fillPropFilter() {
  const cur = $("f-prop").value;
  const props = [...new Set(BOOKINGS.map((b) => b.prop))].sort();
  $("f-prop").innerHTML =
    `<option value="">All</option>` +
    props.map((p) => `<option${p === cur ? " selected" : ""}>${esc(p)}</option>`).join("");
}

function loadPreset() {
  BOOKINGS = makePortfolio($("rm-preset").value);
  fillPropFilter();
  buildTable();
  recompute();
}

// ---------- events ----------
$("rm-tbody").addEventListener("input", (e) => {
  const el = e.target.closest("[data-f]");
  if (!el) return;
  const tr = el.closest("tr");
  const b = BOOKINGS[+tr.dataset.i];
  const f = el.dataset.f;
  b[f] = f === "rate" || f === "clean" ? parseFloat(el.value) || 0 : el.value;
  refreshRow(tr);
  recompute();
});
$("rm-tbody").addEventListener("change", (e) => {
  const el = e.target.closest("[data-f]");
  if (!el) return;
  const b = BOOKINGS[+el.closest("tr").dataset.i];
  if (el.dataset.f === "cleaned") b.cleaned = el.value === "yes";
  else if (el.dataset.f === "status") { b.status = el.value; buildTable(); }
  recompute();
});
$("rm-tbody").addEventListener("click", (e) => {
  const x = e.target.closest("[data-x]");
  if (!x) return;
  BOOKINGS.splice(+x.dataset.x, 1);
  fillPropFilter();
  buildTable();
  recompute();
});

$("rm-addbtn").addEventListener("click", () => {
  const ci = $("a-in").value || iso(today);
  const co = $("a-out").value || iso(addDays(parseD(ci) || today, 7));
  BOOKINGS.unshift({
    prop: $("a-prop").value.trim() || "New property",
    guest: $("a-guest").value.trim() || "New guest",
    ci, co,
    rate: parseFloat($("a-rate").value) || 0,
    clean: parseFloat($("a-clean").value) || 0,
    status: "Confirmed", cleaned: false,
  });
  ["a-prop", "a-guest"].forEach((id) => ($(id).value = ""));
  fillPropFilter();
  buildTable();
  recompute();
});

["rm-preset"].forEach((id) => $(id).addEventListener("change", loadPreset));
["f-prop", "f-status"].forEach((id) => $(id).addEventListener("change", buildTable));
$("rm-cur").addEventListener("change", refreshAll);

// ---------- Excel export (compact in-browser writer) ----------
const _ct = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crc32(b) { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = _ct[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
const u8 = (s) => new TextEncoder().encode(s);
function zip(files) {
  const parts = [], cen = []; let off = 0;
  files.forEach((f) => {
    const nm = u8(f.name), d = f.data, crc = crc32(d);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, d.length, true);
    lh.setUint32(22, d.length, true); lh.setUint16(26, nm.length, true);
    parts.push(new Uint8Array(lh.buffer), nm, d);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true);
    ch.setUint16(6, 20, true); ch.setUint32(16, crc, true);
    ch.setUint32(20, d.length, true); ch.setUint32(24, d.length, true);
    ch.setUint16(28, nm.length, true); ch.setUint32(42, off, true);
    cen.push(new Uint8Array(ch.buffer), nm);
    off += 30 + nm.length + d.length;
  });
  let cs = 0; cen.forEach((c) => (cs += c.length));
  const e = new DataView(new ArrayBuffer(22));
  e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true);
  e.setUint16(10, files.length, true); e.setUint32(12, cs, true);
  e.setUint32(16, off, true);
  return new Blob([...parts, ...cen, new Uint8Array(e.buffer)],
    { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}
const xe = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function exportXLSX() {
  const H = ["Property", "Guest", "Check-in", "Check-out", "Nights", "Rate",
    "Cleaning fee", "Status", "Cleaned", "Rent", "Net", "Turnover"];
  let sd =
    `<row r="1"><c r="A1" t="inlineStr" s="1"><is><t>Rental Portfolio — bookings &amp; contracts</t></is></c></row><row r="2"/>` +
    `<row r="3">` +
    H.map((h, i) => `<c r="${String.fromCharCode(65 + i)}3" t="inlineStr" s="2"><is><t xml:space="preserve">${xe(h)}</t></is></c>`).join("") +
    `</row>`;
  let rn = 4;
  BOOKINGS.forEach((b) => {
    const c = calc(b);
    const turn = !c.active ? "cancelled" : c.cleaningDue ? "cleaning due" : "ok";
    const cells = [
      ["A", "inlineStr", xe(b.prop)], ["B", "inlineStr", xe(b.guest)],
      ["C", "inlineStr", xe(b.ci)], ["D", "inlineStr", xe(b.co)],
      ["E", "n", c.nights], ["F", "n", +b.rate || 0],
      ["G", "n", +b.clean || 0], ["H", "inlineStr", xe(b.status)],
      ["I", "inlineStr", b.cleaned ? "Yes" : "No"],
      ["J", "n", c.active ? Math.round(c.rent) : 0],
      ["K", "n", c.active ? Math.round(c.net) : 0],
      ["L", "inlineStr", turn],
    ];
    sd += `<row r="${rn}">` + cells.map(([col, t, v]) =>
      t === "n"
        ? `<c r="${col}${rn}" s="3"><v>${v}</v></c>`
        : `<c r="${col}${rn}" t="inlineStr" s="4"><is><t xml:space="preserve">${v}</t></is></c>`
    ).join("") + `</row>`;
    rn++;
  });
  const sheet =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<cols><col min="1" max="2" width="18"/><col min="3" max="4" width="12"/>` +
    `<col min="5" max="11" width="11"/><col min="12" max="12" width="13"/></cols>` +
    `<sheetData>${sd}</sheetData>` +
    `<mergeCells count="1"><mergeCell ref="A1:L1"/></mergeCells></worksheet>`;
  const styles =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0"/></numFmts>` +
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
    `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
  const files = [
    { name: "[Content_Types].xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`) },
    { name: "_rels/.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
    { name: "xl/workbook.xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Bookings" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
    { name: "xl/_rels/workbook.xml.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
    { name: "xl/styles.xml", data: u8(styles) },
    { name: "xl/worksheets/sheet1.xml", data: u8(sheet) },
  ];
  const url = URL.createObjectURL(zip(files));
  const a = document.createElement("a");
  a.href = url; a.download = "rental-portfolio.xlsx";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
$("rm-export").addEventListener("click", exportXLSX);

// ---------- init ----------
loadPreset();
