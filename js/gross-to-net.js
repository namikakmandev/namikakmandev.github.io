// Product margin waterfall (mirrors assets/gross_to_net.py)
function marginWaterfall(gross, rebates, discounts, markups, cogs, opex, other) {
  const netPrice = gross - rebates - discounts + markups;
  const grossMargin = netPrice - cogs;
  const operatingProfit = grossMargin - opex - other;
  const pct = (v) => (netPrice > 0 ? (v / netPrice) * 100 : 0);
  const markupOnCogs = cogs > 0 ? ((netPrice - cogs) / cogs) * 100 : 0;
  return {
    gross, rebates, discounts, markups, cogs, opex, other,
    netPrice, grossMargin, operatingProfit,
    grossMarginPct: pct(grossMargin),
    operatingMarginPct: pct(operatingProfit),
    markupOnCogs,
  };
}

function fmt(n) {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
function num(id) {
  const v = parseFloat(document.getElementById(id).value);
  return isNaN(v) || v < 0 ? 0 : v;
}
function set(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// Draw the SVG waterfall chart
function buildChart(r) {
  const svg = document.getElementById("wf-svg");
  const W = 960, H = 480, mL = 18, mR = 18, mT = 36, mB = 96;
  const plotW = W - mL - mR, plotH = H - mT - mB;

  const steps = [
    { label: "Gross", kind: "total", value: r.gross },
    { label: "Rebates", kind: "dec", delta: r.rebates },
    { label: "Discounts", kind: "dec", delta: r.discounts },
    { label: "Markups", kind: "inc", delta: r.markups },
    { label: "Net Price", kind: "sub", value: r.netPrice, accent: "blue" },
    { label: "COGS", kind: "dec", delta: r.cogs },
    { label: "Gross Margin", kind: "sub", value: r.grossMargin, accent: r.grossMargin < 0 ? "loss" : "green" },
    { label: "OpEx", kind: "dec", delta: r.opex },
    { label: "Other", kind: "dec", delta: r.other },
    {
      label: "Op. Profit",
      kind: "total",
      value: r.operatingProfit,
      accent: r.operatingProfit < 0 ? "loss" : "green",
    },
  ];

  let run = 0;
  const bars = steps.map((s) => {
    let lo, hi;
    if (s.kind === "total" || s.kind === "sub") {
      lo = Math.min(0, s.value);
      hi = Math.max(0, s.value);
      run = s.value;
    } else if (s.kind === "dec") {
      const start = run;
      run = run - s.delta;
      lo = Math.min(start, run);
      hi = Math.max(start, run);
    } else {
      const start = run;
      run = run + s.delta;
      lo = Math.min(start, run);
      hi = Math.max(start, run);
    }
    return Object.assign({}, s, { lo: lo, hi: hi, top: run });
  });

  const maxV = Math.max(0, ...bars.map((b) => b.hi));
  const minV = Math.min(0, ...bars.map((b) => b.lo));
  const span = maxV - minV || 1;
  const y = (v) => mT + ((maxV - v) / span) * plotH;

  const n = steps.length;
  const slot = plotW / n;
  const bw = Math.min(64, slot * 0.62);
  const yz = y(0);
  let out =
    `<line x1="${mL}" y1="${yz.toFixed(1)}" x2="${W - mR}" y2="${yz.toFixed(
      1
    )}" stroke="var(--border)" stroke-width="1"/>`;

  bars.forEach((b, i) => {
    const cx = mL + slot * i + slot / 2;
    const x = cx - bw / 2;
    const yTop = y(b.hi);
    const yBot = y(b.lo);
    const h = Math.max(1, yBot - yTop);
    let fill;
    if (b.accent === "blue") fill = "var(--accent)";
    else if (b.accent === "green") fill = "var(--accent-2)";
    else if (b.accent === "orange") fill = "var(--accent-3)";
    else if (b.accent === "loss") fill = "var(--loss)";
    else if (b.kind === "total" || b.kind === "inc") fill = "var(--accent)";
    else fill = "var(--text-dim)";
    const op = b.kind === "dec" ? "0.5" : "1";
    out +=
      `<rect x="${x.toFixed(1)}" y="${yTop.toFixed(1)}" width="${bw.toFixed(
        1
      )}" height="${h.toFixed(1)}" rx="3" style="fill:${fill};opacity:${op}"/>`;

    const sign = b.kind === "dec" ? "-" : b.kind === "inc" ? "+" : "";
    const amount = b.kind === "dec" || b.kind === "inc" ? b.delta : b.value;
    out +=
      `<text x="${cx.toFixed(1)}" y="${(yTop - 7).toFixed(
        1
      )}" text-anchor="middle" class="wf-vlabel">${sign}${fmt(amount)}</text>`;

    const ly = H - mB + 18;
    out +=
      `<text x="${cx.toFixed(1)}" y="${ly.toFixed(
        1
      )}" text-anchor="end" class="wf-clabel" transform="rotate(-35 ${cx.toFixed(
        1
      )} ${ly.toFixed(1)})">${b.label}</text>`;

    if (i < bars.length - 1) {
      const yr = y(b.top);
      const nx = mL + slot * (i + 1) + slot / 2 - bw / 2;
      out +=
        `<line x1="${(x + bw).toFixed(1)}" y1="${yr.toFixed(1)}" x2="${nx.toFixed(
          1
        )}" y2="${yr.toFixed(
          1
        )}" stroke="var(--text-dim)" stroke-width="1" stroke-dasharray="3 3" opacity="0.45"/>`;
    }
  });

  svg.innerHTML = out;
}

function render() {
  const r = marginWaterfall(
    num("gross"), num("rebates"), num("discounts"), num("markups"),
    num("cogs"), num("opex"), num("other")
  );
  set("k-net", fmt(r.netPrice));
  set("k-gm", fmt(r.grossMargin));
  set("k-gm-pct", r.grossMarginPct.toFixed(1) + "%");
  set("k-op", fmt(r.operatingProfit));
  set("k-op-pct", r.operatingMarginPct.toFixed(1) + "%");

  // Operating Profit goes orange (warning) if negative
  const opRow = document.getElementById("k-op-row");
  if (opRow) opRow.classList.toggle("loss", r.operatingProfit < 0);

  buildChart(r);

  set(
    "w-extra",
    "Gross margin: " + r.grossMarginPct.toFixed(1) +
      "%  ·  Operating margin: " + r.operatingMarginPct.toFixed(1) +
      "%  ·  Markup on COGS: " + r.markupOnCogs.toFixed(1) + "%"
  );
}

// ---- Minimal in-browser XLSX writer (no external library) ----
const _crcTable = (() => {
  const t = [];
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = _crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function u8(str) {
  return new TextEncoder().encode(str);
}
function zip(files) {
  const enc = new TextEncoder();
  const parts = [];
  const central = [];
  let offset = 0;
  files.forEach((f) => {
    const nameBytes = enc.encode(f.name);
    const data = f.data;
    const crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true);
    lh.setUint16(4, 20, true);
    lh.setUint16(6, 0, true);
    lh.setUint16(8, 0, true);
    lh.setUint16(10, 0, true);
    lh.setUint16(12, 0, true);
    lh.setUint32(14, crc, true);
    lh.setUint32(18, data.length, true);
    lh.setUint32(22, data.length, true);
    lh.setUint16(26, nameBytes.length, true);
    lh.setUint16(28, 0, true);
    parts.push(new Uint8Array(lh.buffer), nameBytes, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true);
    ch.setUint16(4, 20, true);
    ch.setUint16(6, 20, true);
    ch.setUint16(8, 0, true);
    ch.setUint16(10, 0, true);
    ch.setUint16(12, 0, true);
    ch.setUint16(14, 0, true);
    ch.setUint32(16, crc, true);
    ch.setUint32(20, data.length, true);
    ch.setUint32(24, data.length, true);
    ch.setUint16(28, nameBytes.length, true);
    ch.setUint16(30, 0, true);
    ch.setUint16(32, 0, true);
    ch.setUint16(34, 0, true);
    ch.setUint16(36, 0, true);
    ch.setUint32(38, 0, true);
    ch.setUint32(42, offset, true);
    central.push(new Uint8Array(ch.buffer), nameBytes);
    offset += 30 + nameBytes.length + data.length;
  });
  let cdSize = 0;
  central.forEach((c) => (cdSize += c.length));
  const eocd = new DataView(new ArrayBuffer(22));
  eocd.setUint32(0, 0x06054b50, true);
  eocd.setUint16(8, files.length, true);
  eocd.setUint16(10, files.length, true);
  eocd.setUint32(12, cdSize, true);
  eocd.setUint32(16, offset, true);
  return new Blob([...parts, ...central, new Uint8Array(eocd.buffer)], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}
function xesc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function exportXLSX() {
  const r = marginWaterfall(
    num("gross"), num("rebates"), num("discounts"), num("markups"),
    num("cogs"), num("opex"), num("other")
  );
  const gmL = r.grossMargin < 0, opL = r.operatingProfit < 0;
  // F(formula, cachedValue) marks a cell as a live Excel formula
  const F = (formula, cached) => ({ f: formula, v: cached });
  // [label, labelStyle, bCell, bStyle, cCell, cStyle] — cell: number|string|F|null
  const rows = [
    ["Product Margin Waterfall", 1, null, 1, null, 1],
    null,
    ["Line item", 2, "Amount", 2, "% of Net Price", 2],
    ["Gross / List Price", 3, r.gross, 4, null, 3],
    ["Rebates", 3, -r.rebates, 4, null, 3],
    ["Discounts", 3, -r.discounts, 4, null, 3],
    ["Markups / Surcharges", 3, r.markups, 4, null, 3],
    ["Net Price", 5, F("B4+B5+B6+B7", r.netPrice), 6, F("IFERROR(B8/$B$8,0)", 1), 10],
    ["COGS", 3, -r.cogs, 4, null, 3],
    ["Gross Margin", gmL ? 13 : 7, F("B8+B9", r.grossMargin), gmL ? 14 : 8, F("IFERROR(B10/$B$8,0)", r.grossMarginPct / 100), gmL ? 15 : 11],
    ["OpEx", 3, -r.opex, 4, null, 3],
    ["Other", 3, -r.other, 4, null, 3],
    ["Operating Profit", opL ? 13 : 7, F("B10+B11+B12", r.operatingProfit), opL ? 14 : 8, F("IFERROR(B13/$B$8,0)", r.operatingMarginPct / 100), opL ? 15 : 11],
    null,
    ["Markup on COGS", 3, null, 4, F("IFERROR(B10/-B9,0)", r.markupOnCogs / 100), 12],
  ];

  const cell = (ref, spec, st) => {
    if (spec === null || spec === undefined) return `<c r="${ref}" s="${st}"/>`;
    if (typeof spec === "number") return `<c r="${ref}" s="${st}"><v>${spec}</v></c>`;
    if (typeof spec === "string")
      return `<c r="${ref}" t="inlineStr" s="${st}"><is><t xml:space="preserve">${xesc(spec)}</t></is></c>`;
    return `<c r="${ref}" s="${st}"><f>${xesc(spec.f)}</f><v>${spec.v}</v></c>`;
  };

  let sd = "";
  rows.forEach((row, i) => {
    const rn = i + 1;
    if (!row) {
      sd += `<row r="${rn}"/>`;
      return;
    }
    const [lbl, ls, b, bs, c, cs] = row;
    sd +=
      `<row r="${rn}">` +
      cell(`A${rn}`, lbl, ls) +
      cell(`B${rn}`, b, bs) +
      cell(`C${rn}`, c, cs) +
      `</row>`;
  });

  // ---- Helper data feeding a native Excel chart (stacked-column waterfall) ----
  const G = r.gross, NP = r.netPrice, GM = r.grossMargin, OP = r.operatingProfit;
  const afterDisc = G - r.rebates - r.discounts;
  const markBase = Math.min(afterDisc, NP);
  const markDec = r.markups < 0 ? -r.markups : 0;
  const markStr = r.markups >= 0 ? r.markups : 0;
  // [category, base, decrease(grey), structure(blue), margin(green), loss(red)]
  const chartRows = [
    ["Gross", 0, 0, G, 0, 0],
    ["Rebates", G - r.rebates, r.rebates, 0, 0, 0],
    ["Discounts", afterDisc, r.discounts, 0, 0, 0],
    ["Markups", markBase, markDec, markStr, 0, 0],
    ["Net Price", 0, 0, NP, 0, 0],
    ["COGS", GM, r.cogs, 0, 0, 0],
    ["Gross Margin", 0, 0, 0, Math.max(GM, 0), Math.min(GM, 0)],
    ["OpEx", GM - r.opex, r.opex, 0, 0, 0],
    ["Other", OP, r.other, 0, 0, 0],
    ["Operating Profit", 0, 0, 0, Math.max(OP, 0), Math.min(OP, 0)],
  ];
  // formula per [base, decrease, structure, margin, loss]; null = constant 0
  const hF = [
    [null, null, "B4", null, null],
    ["B4+B5", "-B5", null, null, null],
    ["B4+B5+B6", "-B6", null, null, null],
    ["MIN(B4+B5+B6,B8)", "IF(B7<0,-B7,0)", "IF(B7>=0,B7,0)", null, null],
    [null, null, "B8", null, null],
    ["B10", "-B9", null, null, null],
    [null, null, null, "IF(B10>=0,B10,0)", "IF(B10<0,B10,0)"],
    ["B10+B11", "-B11", null, null, null],
    ["B13", "-B12", null, null, null],
    [null, null, null, "IF(B13>=0,B13,0)", "IF(B13<0,B13,0)"],
  ];
  let vis =
    `<row r="17">` +
    `<c r="A17" t="inlineStr" s="2"><is><t xml:space="preserve">Waterfall data</t></is></c>` +
    `<c r="B17" t="inlineStr" s="2"><is><t>Base</t></is></c>` +
    `<c r="C17" t="inlineStr" s="2"><is><t>Decrease</t></is></c>` +
    `<c r="D17" t="inlineStr" s="2"><is><t>Structure</t></is></c>` +
    `<c r="E17" t="inlineStr" s="2"><is><t>Margin</t></is></c>` +
    `<c r="F17" t="inlineStr" s="2"><is><t>Loss</t></is></c></row>`;
  const hCols = ["B", "C", "D", "E", "F"];
  chartRows.forEach((cr, idx) => {
    const rn = 18 + idx;
    let cs = `<c r="A${rn}" t="inlineStr" s="3"><is><t xml:space="preserve">${xesc(cr[0])}</t></is></c>`;
    for (let j = 0; j < 5; j++) {
      const f = hF[idx][j];
      const cached = cr[j + 1];
      cs += f
        ? `<c r="${hCols[j]}${rn}" s="4"><f>${xesc(f)}</f><v>${cached}</v></c>`
        : `<c r="${hCols[j]}${rn}" s="4"><v>${cached}</v></c>`;
    }
    vis += `<row r="${rn}">${cs}</row>`;
  });

  const sheet =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
    `<cols><col min="1" max="1" width="26" customWidth="1"/>` +
    `<col min="2" max="2" width="16" customWidth="1"/>` +
    `<col min="3" max="3" width="16" customWidth="1"/></cols>` +
    `<sheetData>${sd}${vis}</sheetData>` +
    `<mergeCells count="1"><mergeCell ref="A1:C1"/></mergeCells>` +
    `<drawing r:id="rId1"/></worksheet>`;

  const SN = "'Margin Waterfall'";
  const ser = (idx, nameCell, valRange, color) => {
    const fill =
      color === "none"
        ? `<c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>`
        : `<c:spPr><a:solidFill><a:srgbClr val="${color}"/></a:solidFill><a:ln><a:noFill/></a:ln></c:spPr>`;
    return (
      `<c:ser><c:idx val="${idx}"/><c:order val="${idx}"/>` +
      `<c:tx><c:strRef><c:f>${SN}!${nameCell}</c:f></c:strRef></c:tx>` +
      fill +
      `<c:invertIfNegative val="0"/>` +
      `<c:cat><c:strRef><c:f>${SN}!$A$18:$A$27</c:f></c:strRef></c:cat>` +
      `<c:val><c:numRef><c:f>${SN}!${valRange}</c:f></c:numRef></c:val>` +
      `</c:ser>`
    );
  };
  const chartXml =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
    `<c:chart>` +
    `<c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Margin Waterfall</a:t></a:r></a:p></c:rich></c:tx><c:overlay val="0"/></c:title>` +
    `<c:autoTitleDeleted val="0"/>` +
    `<c:plotArea><c:layout/>` +
    `<c:barChart><c:barDir val="col"/><c:grouping val="stacked"/><c:varyColors val="0"/>` +
    ser(0, "$B$17", "$B$18:$B$27", "none") +
    ser(1, "$C$17", "$C$18:$C$27", "AAB3C0") +
    ser(2, "$D$17", "$D$18:$D$27", "2F9BFF") +
    ser(3, "$E$17", "$E$18:$E$27", "19C37D") +
    ser(4, "$F$17", "$F$18:$F$27", "E5484D") +
    `<c:gapWidth val="40"/><c:overlap val="100"/>` +
    `<c:axId val="111111111"/><c:axId val="222222222"/></c:barChart>` +
    `<c:catAx><c:axId val="111111111"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:crossAx val="222222222"/></c:catAx>` +
    `<c:valAx><c:axId val="222222222"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:crossAx val="111111111"/></c:valAx>` +
    `</c:plotArea><c:plotVisOnly val="1"/></c:chart></c:chartSpace>`;

  const drawingXml =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">` +
    `<xdr:twoCellAnchor editAs="oneCell">` +
    `<xdr:from><xdr:col>6</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>1</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>` +
    `<xdr:to><xdr:col>19</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>30</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>` +
    `<xdr:graphicFrame macro="">` +
    `<xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="MarginChart"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>` +
    `<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>` +
    `<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">` +
    `<c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId1"/>` +
    `</a:graphicData></a:graphic>` +
    `</xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>`;

  const styles =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0.00;-#,##0.00"/><numFmt numFmtId="165" formatCode="0.0%"/></numFmts>` +
    `<fonts count="7">` +
    `<font><sz val="11"/><name val="Calibri"/><color rgb="FF1F2937"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FF1F2937"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FF19C37D"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFF6500"/></font>` +
    `<font><b/><sz val="14"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFE5484D"/></font>` +
    `</fonts>` +
    `<fills count="9">` +
    `<fill><patternFill patternType="none"/></fill>` +
    `<fill><patternFill patternType="gray125"/></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FF2F9BFF"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FFEAF4FF"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FFEAF8F1"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FF19C37D"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FFAAB3C0"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FFFF6500"/></patternFill></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FFFDECEC"/></patternFill></fill>` +
    `</fills>` +
    `<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>` +
    `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>` +
    `<cellXfs count="16">` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="0" fontId="5" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>` +
    `<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyFont="1"/>` +
    `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `<xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="164" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `<xf numFmtId="0" fontId="2" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="164" fontId="3" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `<xf numFmtId="164" fontId="4" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `<xf numFmtId="165" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `<xf numFmtId="165" fontId="3" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `<xf numFmtId="0" fontId="6" fillId="8" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="164" fontId="6" fillId="8" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `<xf numFmtId="165" fontId="6" fillId="8" borderId="0" xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1"/>` +
    `</cellXfs>` +
    `<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>` +
    `</styleSheet>`;

  const files = [
    {
      name: "[Content_Types].xml",
      data: u8(
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
          `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
          `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
          `<Default Extension="xml" ContentType="application/xml"/>` +
          `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
          `<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>` +
          `<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>` +
          `<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>` +
          `<Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>` +
          `</Types>`
      ),
    },
    {
      name: "_rels/.rels",
      data: u8(
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
          `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
          `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>` +
          `</Relationships>`
      ),
    },
    {
      name: "xl/workbook.xml",
      data: u8(
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
          `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">` +
          `<sheets><sheet name="Margin Waterfall" sheetId="1" r:id="rId1"/></sheets></workbook>`
      ),
    },
    {
      name: "xl/_rels/workbook.xml.rels",
      data: u8(
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
          `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
          `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>` +
          `<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>` +
          `</Relationships>`
      ),
    },
    { name: "xl/styles.xml", data: u8(styles) },
    { name: "xl/worksheets/sheet1.xml", data: u8(sheet) },
    {
      name: "xl/worksheets/_rels/sheet1.xml.rels",
      data: u8(
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
          `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
          `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/>` +
          `</Relationships>`
      ),
    },
    { name: "xl/drawings/drawing1.xml", data: u8(drawingXml) },
    {
      name: "xl/drawings/_rels/drawing1.xml.rels",
      data: u8(
        `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
          `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
          `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/>` +
          `</Relationships>`
      ),
    },
    { name: "xl/charts/chart1.xml", data: u8(chartXml) },
  ];

  const blob = zip(files);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "product-margin.xlsx";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

document.getElementById("export-btn").addEventListener("click", exportXLSX);

// Industry presets — typical gross-to-net shapes (per 1,000 of list price)
const PRESETS = {
  pharma:      { gross: 1000, rebates: 180, discounts: 120, markups: 0, cogs: 220, opex: 160, other: 40 },
  distributor: { gross: 1000, rebates: 20,  discounts: 60,  markups: 0, cogs: 780, opex: 90,  other: 20 },
  medtech:     { gross: 1000, rebates: 40,  discounts: 90,  markups: 0, cogs: 380, opex: 240, other: 50 },
  retail:      { gross: 1000, rebates: 30,  discounts: 150, markups: 0, cogs: 520, opex: 180, other: 50 },
  usedcar:     { gross: 18000, rebates: 600, discounts: 500, markups: 900, cogs: 14500, opex: 700, other: 400 },
};

// Each industry relabels the fields in its own language + a one-line context note
const DEFAULT_LABELS = {
  gross: "Gross / List Price", rebates: "Rebates (−)", discounts: "Discounts (−)",
  markups: "Markups (+)", cogs: "COGS (−)", opex: "OpEx (−)", other: "Other costs (−)",
};
const LABELS = {
  pharma: {
    gross: "List / WAC price", rebates: "Payer & GPO rebates (−)",
    discounts: "Channel discounts (−)", markups: "Surcharges (+)",
    cogs: "Manufacturing cost (−)", opex: "Sales & medical cost (−)",
    other: "Distribution & other (−)",
    _note: "Branded prescription drug — heavy payer & GPO rebates plus channel discounts erode the list price before any cost: the classic pharma gross-to-net.",
  },
  distributor: {
    gross: "Resale price", rebates: "Volume rebates (−)",
    discounts: "Customer discounts (−)", markups: "Service surcharge (+)",
    cogs: "Purchase cost (−)", opex: "Warehouse & logistics (−)",
    other: "Other costs (−)",
    _note: "Wholesale distribution — thin margin sitting on a high purchase cost; small pricing or discount leakage moves the whole result.",
  },
  medtech: {
    gross: "List price", rebates: "Tender / GPO rebates (−)",
    discounts: "Deal discounts (−)", markups: "Install & training (+)",
    cogs: "Device COGS (−)", opex: "Sales & field service (−)",
    other: "Regulatory & other (−)",
    _note: "Medical device — lower rebates, but heavy sales, field-service and regulatory cost make operating cost the swing factor.",
  },
  retail: {
    gross: "Shelf price", rebates: "Supplier rebates (−)",
    discounts: "Promotions & markdowns (−)", markups: "Surcharges (+)",
    cogs: "Cost of goods (−)", opex: "Store & staff cost (−)",
    other: "Shrinkage & other (−)",
    _note: "Retail — promotions and markdowns are the biggest lever on a moderate product-cost base.",
  },
  usedcar: {
    gross: "Sale price", rebates: "Trade-in over-allowance (−)",
    discounts: "Customer discount (−)", markups: "F&I income (+)",
    cogs: "Vehicle buy cost (−)", opex: "Reconditioning (−)",
    other: "Holding & finance (−)",
    _note: "One used-car deal — sale price, minus what you 'gave away' on the trade-in (Inzahlungnahme) and the negotiated discount, plus finance & warranty income (F&I), against the buy cost, reconditioning (Aufbereitung) and days-on-lot holding cost (Standkosten).",
  },
};
const SCEN_NAME = { pharma: "Pharma Rx", distributor: "Distributor", medtech: "Medtech", retail: "Retail", usedcar: "Used-car deal" };

const FIELDS = ["gross", "rebates", "discounts", "markups", "cogs", "opex", "other"];
const presetBtns = document.querySelectorAll("#mg-presets button");
const mgNote = document.getElementById("mg-note");
const chartTitle = document.querySelector(".sim2-chart h3");

function setLabels(map) {
  FIELDS.forEach((id) => {
    const lab = document.querySelector('label[for="' + id + '"]');
    if (lab) lab.textContent = map[id];
  });
}

function applyPreset(key) {
  const p = PRESETS[key];
  if (!p) return;
  FIELDS.forEach((id) => (document.getElementById(id).value = p[id]));
  presetBtns.forEach((b) => b.classList.toggle("on", b.dataset.p === key));
  setLabels(LABELS[key]);
  if (mgNote) mgNote.textContent = LABELS[key]._note;
  if (chartTitle) chartTitle.textContent = "Margin Waterfall — " + SCEN_NAME[key];
  render();
}
presetBtns.forEach((b) =>
  b.addEventListener("click", () => applyPreset(b.dataset.p))
);

// Live update as the user types; a manual edit means "custom" — reset to generic labels
FIELDS.forEach((id) =>
  document.getElementById(id).addEventListener("input", () => {
    if (document.querySelector("#mg-presets button.on")) {
      presetBtns.forEach((b) => b.classList.remove("on"));
      setLabels(DEFAULT_LABELS);
      if (mgNote) mgNote.textContent = "Custom inputs — edit any field, or pick an industry above to load a typical shape.";
      if (chartTitle) chartTitle.textContent = "Margin Waterfall — Custom";
    }
    render();
  })
);

// Start on the default active preset (Pharma Rx) so labels & note match on load
if (mgNote) mgNote.textContent = LABELS.pharma._note;
if (chartTitle) chartTitle.textContent = "Margin Waterfall — Pharma Rx";
setLabels(LABELS.pharma);

render();
