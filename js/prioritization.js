// ---- Account & Portfolio Prioritization (whitespace engine) ----
const REQUIRED = ["AccountManager", "Customer", "Product", "Sales"];
const ADOPT_MIN = 0.4; // a product counts as "peers buy it" at >=40% adoption
let OPPS = []; // last computed opportunity rows

function parseCSV(text) {
  const rows = [];
  let row = [], val = "", q = false;
  text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') {
        if (text[i + 1] === '"') { val += '"'; i++; }
        else q = false;
      } else val += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(val); val = ""; }
    else if (c === "\n") { row.push(val); rows.push(row); row = []; val = ""; }
    else val += c;
  }
  if (val !== "" || row.length) { row.push(val); rows.push(row); }
  return rows.filter((r) => r.length && !(r.length === 1 && r[0].trim() === ""));
}

function toObjects(rows) {
  const head = rows[0].map((h) => h.trim());
  return {
    head,
    data: rows.slice(1).map((r) => {
      const o = {};
      head.forEach((h, i) => (o[h] = (r[i] !== undefined ? r[i] : "").trim()));
      return o;
    }),
  };
}

const median = (arr) => {
  if (!arr.length) return 0;
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const fmt = (n) =>
  Math.round(n).toLocaleString(undefined, { maximumFractionDigits: 0 });

function status(msg, ok) {
  const el = document.getElementById("up-status");
  el.textContent = msg;
  el.style.color = ok ? "var(--accent-2)" : "var(--loss)";
}

function process(text, fname) {
  let rows;
  try {
    rows = parseCSV(text);
  } catch (e) {
    return status("Could not read the CSV file.", false);
  }
  if (!rows.length) return status("The file looks empty.", false);
  const { head, data } = toObjects(rows);
  const missing = REQUIRED.filter((c) => !head.includes(c));
  if (missing.length)
    return status("Missing required column(s): " + missing.join(", "), false);

  const hasSeg = head.includes("Segment");
  const hasMargin = head.includes("Margin%");
  const hasGroup = head.includes("ProductGroup");

  // Build customers
  const cust = {};
  let bad = 0;
  data.forEach((r) => {
    const sales = parseFloat(String(r.Sales).replace(/[, ]/g, ""));
    if (!r.Customer || !r.Product || isNaN(sales)) { bad++; return; }
    const c = (cust[r.Customer] = cust[r.Customer] || {
      name: r.Customer, segment: hasSeg ? r.Segment || "—" : "—",
      products: {}, amTotals: {}, total: 0,
    });
    c.products[r.Product] = (c.products[r.Product] || 0) + sales;
    c.total += sales;
    if (r.AccountManager)
      c.amTotals[r.AccountManager] = (c.amTotals[r.AccountManager] || 0) + sales;
  });
  const customers = Object.values(cust);
  if (customers.length < 4)
    return status("Need at least a few customers to compare. Only " + customers.length + " found.", false);

  customers.forEach((c) => {
    c.am = Object.keys(c.amTotals).sort((a, b) => c.amTotals[b] - c.amTotals[a])[0] || "—";
  });

  // Product meta (group + margin)
  const pMeta = {};
  data.forEach((r) => {
    if (!r.Product) return;
    const m = pMeta[r.Product] = pMeta[r.Product] || { group: "—", margins: [] };
    if (hasGroup && r.ProductGroup) m.group = r.ProductGroup;
    if (hasMargin) {
      const mg = parseFloat(String(r["Margin%"]).replace(/[, ]/g, ""));
      if (!isNaN(mg)) m.margins.push(mg);
    }
  });
  const productList = Object.keys(pMeta);
  productList.forEach((p) => {
    const ms = pMeta[p].margins;
    pMeta[p].margin = ms.length ? ms.reduce((a, b) => a + b, 0) / ms.length : null;
  });

  // Size bands (terciles) within segment (or global)
  function bandMap(list) {
    const sorted = [...list].sort((a, b) => a.total - b.total);
    const n = sorted.length;
    sorted.forEach((c, i) => {
      c._band = i < n / 3 ? "S" : i < (2 * n) / 3 ? "M" : "L";
    });
  }
  if (hasSeg) {
    const bySeg = {};
    customers.forEach((c) => (bySeg[c.segment] = bySeg[c.segment] || []).push(c));
    Object.values(bySeg).forEach(bandMap);
  } else bandMap(customers);

  const peerKey = (c) => (hasSeg ? c.segment + "|" : "") + c._band;
  const keyGroups = {};
  customers.forEach((c) => (keyGroups[peerKey(c)] = keyGroups[peerKey(c)] || []).push(c));

  function peersOf(c) {
    let p = keyGroups[peerKey(c)].filter((x) => x !== c);
    if (p.length < 5 && hasSeg)
      p = customers.filter((x) => x !== c && x.segment === c.segment);
    if (p.length < 5) p = customers.filter((x) => x !== c);
    return p;
  }

  // Whitespace scoring
  OPPS = [];
  customers.forEach((c) => {
    const peers = peersOf(c);
    productList.forEach((p) => {
      const actual = c.products[p] || 0;
      const buyers = peers.filter((x) => (x.products[p] || 0) > 0);
      const adoption = buyers.length / peers.length;
      if (adoption < ADOPT_MIN) return;
      const spends = buyers.map((b) => b.products[p]);
      const medSpend = median(spends);
      const medPeerTotal = median(buyers.map((b) => b.total)) || c.total || 1;
      const scale = clamp(c.total / medPeerTotal, 0.5, 2.5);
      const benchmark = medSpend * scale;
      const opp = benchmark - actual;
      const floor = Math.max(500, 0.02 * c.total);
      if (opp <= floor) return;
      const mg = pMeta[p].margin;
      const score = opp * (mg != null ? mg / 100 : 1);
      OPPS.push({
        am: c.am, customer: c.name, segment: c.segment, product: p,
        group: pMeta[p].group, actual, adoption, opp, margin: mg, score,
        reason:
          buyers.length + " of " + peers.length + " similar customers buy " + p +
          " (median " + fmt(medSpend) + "); this customer buys " + fmt(actual) +
          " → est. opportunity ≈ " + fmt(opp),
      });
    });
  });
  OPPS.sort((a, b) => b.score - a.score);
  window.__CUST = customers.map((c) => ({
    name: c.name, am: c.am, segment: c.segment, total: c.total,
  }));
  window.__DATA = {
    customers: customers.map((c) => ({
      name: c.name, am: c.am, segment: c.segment, total: c.total,
      products: c.products,
    })),
    pMeta, productList, hasMargin, hasGroup,
  };

  // Populate AM filter
  const sel = document.getElementById("am-filter");
  const ams = [...new Set(OPPS.map((o) => o.am))].sort();
  sel.innerHTML =
    '<option value="">All</option>' +
    ams.map((a) => `<option>${a}</option>`).join("");

  status(
    "Loaded " + (fname || "data") + ": " + data.length + " rows, " +
      customers.length + " customers, " + productList.length + " products" +
      (bad ? " (" + bad + " rows skipped)" : "") + ".",
    true
  );
  window.__GRP = "";
  document.getElementById("results").hidden = false;
  render();
}

function _med(a) {
  if (!a.length) return 0;
  const s = [...a].sort((p, q) => p - q);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function drawMatrix(opps, f, g) {
  const el = document.getElementById("cp-matrix-svg");
  const cust = (window.__CUST || []).filter((c) => !f || c.am === f);
  if (!cust.length) { el.innerHTML = ""; return; }
  const ws = {};
  opps.forEach((o) => (ws[o.customer] = (ws[o.customer] || 0) + o.opp));
  let pts = cust.map((c) => ({ name: c.name, x: c.total, y: ws[c.name] || 0 }));
  if (g) pts = pts.filter((p) => p.y > 0); // group selected → only accounts with whitespace there
  if (!pts.length) { el.innerHTML = ""; return; }
  const W = 640, H = 470, mL = 70, mR = 20, mT = 18, mB = 46;
  const pw = W - mL - mR, ph = H - mT - mB;
  const xMax = Math.max(...pts.map((p) => p.x)) * 1.05 || 1;
  const yMax = Math.max(...pts.map((p) => p.y)) * 1.05 || 1;
  const mx = _med(pts.map((p) => p.x)), my = _med(pts.map((p) => p.y));
  const X = (v) => mL + (v / xMax) * pw;
  const Y = (v) => mT + ph - (v / yMax) * ph;
  let s = "";
  s += `<rect x="${mL}" y="${mT}" width="${pw}" height="${ph}" fill="none" stroke="var(--border)"/>`;
  s += `<line x1="${X(mx).toFixed(1)}" y1="${mT}" x2="${X(mx).toFixed(1)}" y2="${mT + ph}" stroke="var(--border)" stroke-dasharray="4 4"/>`;
  s += `<line x1="${mL}" y1="${Y(my).toFixed(1)}" x2="${mL + pw}" y2="${Y(my).toFixed(1)}" stroke="var(--border)" stroke-dasharray="4 4"/>`;
  s += `<text x="${mL + pw - 8}" y="${mT + 16}" text-anchor="end" class="cp-q">GROW</text>`;
  s += `<text x="${mL + 8}" y="${mT + 16}" class="cp-q">DEVELOP</text>`;
  s += `<text x="${mL + pw - 8}" y="${mT + ph - 8}" text-anchor="end" class="cp-q">DEFEND</text>`;
  s += `<text x="${mL + 8}" y="${mT + ph - 8}" class="cp-q">MAINTAIN</text>`;
  s += `<text x="${mL + pw / 2}" y="${H - 10}" text-anchor="middle" class="cp-ax">Current value (revenue) →</text>`;
  s += `<text x="16" y="${mT + ph / 2}" text-anchor="middle" class="cp-ax" transform="rotate(-90 16 ${mT + ph / 2})">Untapped whitespace →</text>`;
  pts.forEach((p) => {
    const hy = p.y >= my, hx = p.x >= mx;
    const color = hy && hx ? "var(--accent-2)" : hy || hx ? "var(--accent)" : "var(--text-dim)";
    s += `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="5" style="fill:${color};opacity:0.78"><title>${p.name} — current €${fmt(p.x)}, whitespace €${fmt(p.y)}</title></circle>`;
  });
  el.innerHTML = s;
}

function drawBars(id, map, clickable, selKey) {
  const el = document.getElementById(id);
  const sel = clickable ? selKey || "" : "";
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1]);
  const W = 420, rowH = 30, mL = 120, mR = 64, mT = 6;
  const H = Math.max(70, mT * 2 + entries.length * rowH);
  const max = Math.max(...entries.map((e) => e[1]), 1);
  const pw = W - mL - mR;
  let s = "";
  entries.forEach(([k, v], i) => {
    const y = mT + i * rowH;
    const bw = (v / max) * pw;
    const on = clickable && sel === k;
    const inner =
      `<text x="${mL - 8}" y="${y + rowH / 2}" text-anchor="end" dominant-baseline="middle" class="se-lbl"${on ? ' style="fill:var(--accent);font-weight:700"' : ""}>${k}</text>` +
      `<rect x="${mL}" y="${y + 5}" width="${bw.toFixed(1)}" height="${rowH - 12}" rx="3" style="fill:var(--accent);opacity:${on ? 1 : 0.85}"/>` +
      `<text x="${mL + bw + 6}" y="${y + rowH / 2}" dominant-baseline="middle" class="se-val">€${fmt(v)}</text>`;
    s += clickable
      ? `<g class="cp-clk" data-k="${k}" style="cursor:pointer"><rect x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent"/>${inner}</g>`
      : inner;
  });
  el.setAttribute("viewBox", `0 0 ${W} ${H}`);
  el.innerHTML = s;
}

function setHTML(id, h) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = h;
}
const pctf = (n) => Math.round(n) + "%";

function buildInsights(opps, f) {
  const D = window.__DATA;
  if (!D) return;
  const custs = D.customers.filter((c) => !f || c.am === f);
  if (!custs.length) return;
  const nC = custs.length;
  const wsC = {};
  opps.forEach((o) => (wsC[o.customer] = (wsC[o.customer] || 0) + o.opp));

  // 1 — Dormant / under-served
  const dorm = custs
    .map((c) => ({ n: c.name, cur: c.total, ws: wsC[c.name] || 0 }))
    .filter((d) => d.cur > 0 && d.ws >= d.cur)
    .sort((a, b) => b.ws - a.ws);
  setHTML(
    "ins-dormant",
    `<p class="ins-big">${dorm.length}<span> accounts with more upside than they capture</span></p>` +
      `<ul class="ins-list">` +
      dorm.slice(0, 5).map((d) =>
        `<li>${xe(d.n)} <em>cur €${fmt(d.cur)} · whitespace €${fmt(d.ws)}</em></li>`).join("") +
      `</ul>`
  );

  // 2 — Forgotten products
  const fp = D.productList.map((p) => {
    const buyers = custs.filter((c) => (c.products[p] || 0) > 0).length;
    const wsP = opps.filter((o) => o.product === p).reduce((s, o) => s + o.opp, 0);
    return { p, pen: nC ? buyers / nC : 0, ws: wsP };
  }).filter((x) => x.ws > 0).sort((a, b) => b.ws - a.ws);
  setHTML(
    "ins-forgotten",
    `<ul class="ins-list">` +
      fp.slice(0, 6).map((x) =>
        `<li>${xe(x.p)} <em>${pctf(x.pen * 100)} penetration · €${fmt(x.ws)} whitespace</em></li>`).join("") +
      `</ul>`
  );

  // 3 — Strategic product-group performance
  const groups = {};
  D.productList.forEach((p) => {
    const g = D.pMeta[p].group || "—";
    (groups[g] = groups[g] || { prods: [] }).prods.push(p);
  });
  let gRows = Object.entries(groups).map(([g, o]) => {
    let rev = 0, anyBuy = 0;
    custs.forEach((c) => {
      let cg = 0;
      o.prods.forEach((p) => (cg += c.products[p] || 0));
      rev += cg;
      if (cg > 0) anyBuy++;
    });
    const ws = opps.filter((x) => x.group === g).reduce((s, x) => s + x.opp, 0);
    const mgs = o.prods.map((p) => D.pMeta[p].margin).filter((m) => m != null);
    const mg = mgs.length ? mgs.reduce((a, b) => a + b, 0) / mgs.length : null;
    return { g, rev, ws, pen: nC ? anyBuy / nC : 0, mg };
  }).sort((a, b) => b.rev - a.rev);
  setHTML(
    "ins-group",
    `<table class="ins-tbl"><tr><th>Group</th><th>Revenue</th><th>Whitespace</th><th>Pen.</th>` +
      (D.hasMargin ? `<th>Margin</th>` : ``) + `</tr>` +
      gRows.map((r) =>
        `<tr><td>${xe(r.g)}</td><td>€${fmt(r.rev)}</td><td>€${fmt(r.ws)}</td><td>${pctf(r.pen * 100)}</td>` +
        (D.hasMargin ? `<td>${r.mg != null ? r.mg.toFixed(0) + "%" : "—"}</td>` : ``) + `</tr>`).join("") +
      `</table>`
  );

  // 4 — Account-manager scorecard
  const amList = f ? [f] : [...new Set(D.customers.map((c) => c.am))].sort();
  const amRows = amList.map((am) => {
    const cs = D.customers.filter((c) => c.am === am);
    const rev = cs.reduce((s, c) => s + c.total, 0);
    const ws = OPPS.filter((o) => o.am === am).reduce((s, o) => s + o.opp, 0);
    return { am, n: cs.length, rev, ws, cap: rev + ws > 0 ? (rev / (rev + ws)) * 100 : 0 };
  }).sort((a, b) => b.ws - a.ws);
  setHTML(
    "ins-amscore",
    `<table class="ins-tbl"><tr><th>AM</th><th>Acc.</th><th>Revenue</th><th>Whitespace</th><th>Capture</th></tr>` +
      amRows.map((r) =>
        `<tr><td>${xe(r.am)}</td><td>${r.n}</td><td>€${fmt(r.rev)}</td><td>€${fmt(r.ws)}</td><td>${pctf(r.cap)}</td></tr>`).join("") +
      `</table>`
  );

  // 5 — Quick wins (high peer adoption)
  const qw = opps.filter((o) => o.adoption >= 0.8).sort((a, b) => b.opp - a.opp);
  setHTML(
    "ins-quick",
    `<p class="ins-big">${qw.length}<span> easy, well-evidenced asks</span></p>` +
      `<ul class="ins-list">` +
      qw.slice(0, 5).map((o) =>
        `<li>${xe(o.customer)} · ${xe(o.product)} <em>${pctf(o.adoption * 100)} adoption · €${fmt(o.opp)}</em></li>`).join("") +
      `</ul>`
  );

  // 6 — Big bets
  const bb = [...opps].sort((a, b) => b.opp - a.opp);
  setHTML(
    "ins-big",
    `<p class="ins-big">€${fmt(bb.slice(0, 5).reduce((s, o) => s + o.opp, 0))}<span> in the top 5 moves</span></p>` +
      `<ul class="ins-list">` +
      bb.slice(0, 5).map((o) =>
        `<li>${xe(o.customer)} · ${xe(o.product)} <em>€${fmt(o.opp)}</em></li>`).join("") +
      `</ul>`
  );

  // 7 — Margin-priority opportunities
  const mv = (o) => (o.margin != null ? o.opp * (o.margin / 100) : o.opp);
  const mp = [...opps].sort((a, b) => mv(b) - mv(a));
  setHTML(
    "ins-margin",
    (D.hasMargin ? `` : `<p class="ins-note">Margin% not in data — ranked by revenue.</p>`) +
      `<ul class="ins-list">` +
      mp.slice(0, 5).map((o) =>
        `<li>${xe(o.customer)} · ${xe(o.product)} <em>€${fmt(mv(o))} margin${o.margin != null ? " · " + o.margin.toFixed(0) + "%" : ""}</em></li>`).join("") +
      `</ul>`
  );

  // 8 — Revenue concentration
  const sorted = [...custs].sort((a, b) => b.total - a.total);
  const tot = sorted.reduce((s, c) => s + c.total, 0) || 1;
  const top10 = sorted.slice(0, 10).reduce((s, c) => s + c.total, 0);
  setHTML(
    "ins-conc",
    `<p class="ins-big">${pctf((top10 / tot) * 100)}<span> of revenue from the top 10 customers</span></p>` +
      `<ul class="ins-list">` +
      sorted.slice(0, 3).map((c) =>
        `<li>${xe(c.name)} <em>€${fmt(c.total)}</em></li>`).join("") +
      `</ul>`
  );
}

function render() {
  const f = document.getElementById("am-filter").value;
  const g = window.__GRP || "";
  const mAm = (o) => !f || o.am === f;
  const mGrp = (o) => !g || o.group === g;
  const rows = OPPS.filter((o) => mAm(o) && mGrp(o));
  const fullGrp = OPPS.filter(mGrp); // AM chart: all AMs, respects group filter
  const fullAm = OPPS.filter(mAm);   // group chart: all groups, respects AM filter

  const total = rows.reduce((s, o) => s + o.opp, 0);
  document.getElementById("k-total").textContent = "€" + fmt(total);
  document.getElementById("k-count").textContent = rows.length;
  document.getElementById("k-custs").textContent =
    new Set(rows.map((o) => o.customer)).size;
  document.getElementById("k-max").textContent =
    "€" + fmt(rows.length ? Math.max(...rows.map((o) => o.opp)) : 0);
  document.getElementById("res-sub").textContent =
    "(" + (f || "all account managers") + (g ? " · " + g : "") + ")";

  drawMatrix(rows, f, g);
  const byAM = {}, byG = {};
  fullGrp.forEach((o) => (byAM[o.am] = (byAM[o.am] || 0) + o.opp));
  fullAm.forEach((o) => (byG[o.group] = (byG[o.group] || 0) + o.opp));
  drawBars("cp-am-svg", byAM, true, f);
  drawBars("cp-grp-svg", byG, true, g);
  buildInsights(rows, f);

  document.getElementById("res-tbody").innerHTML = rows
    .slice(0, 250)
    .map(
      (o, i) =>
        `<tr><td>${i + 1}</td><td>${o.am}</td><td>${o.customer}</td>` +
        `<td>${o.product}</td><td class="num">${fmt(o.actual)}</td>` +
        `<td class="num">${Math.round(o.adoption * 100)}%</td>` +
        `<td class="num"><b>€${fmt(o.opp)}</b></td>` +
        `<td class="why">${o.reason}</td></tr>`
    )
    .join("");
}

document.getElementById("csv-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const rd = new FileReader();
  rd.onload = () => process(rd.result, file.name);
  rd.onerror = () => status("Could not read that file.", false);
  rd.readAsText(file);
});
document.getElementById("sample-btn").addEventListener("click", () => {
  if (window.SAMPLE_CSV) process(window.SAMPLE_CSV, "sample data");
  else status("Sample data not available.", false);
});
document.getElementById("am-filter").addEventListener("change", render);
document.getElementById("cp-am-svg").addEventListener("click", (e) => {
  const g = e.target.closest("[data-k]");
  if (!g) return;
  const sel = document.getElementById("am-filter");
  const k = g.getAttribute("data-k");
  sel.value = sel.value === k ? "" : k; // click again to clear
  render();
});
document.getElementById("cp-grp-svg").addEventListener("click", (e) => {
  const g = e.target.closest("[data-k]");
  if (!g) return;
  const k = g.getAttribute("data-k");
  window.__GRP = window.__GRP === k ? "" : k; // click again to clear
  render();
});

// ---- Compact in-browser XLSX export ----
const _ct = (() => {
  const t = [];
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(b) {
  let c = 0xffffffff;
  for (let i = 0; i < b.length; i++) c = _ct[(c ^ b[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
const u8 = (s) => new TextEncoder().encode(s);
function zip(files) {
  const parts = [], cen = [];
  let off = 0;
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
  return new Blob([...parts, ...cen, new Uint8Array(e.buffer)], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}
const xe = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function exportXLSX() {
  const f = document.getElementById("am-filter").value;
  const rows = f ? OPPS.filter((o) => o.am === f) : OPPS;
  const H = ["Rank", "Account Manager", "Customer", "Segment", "Product",
    "Product Group", "Current", "Peer adoption %", "Est. opportunity", "Margin %", "Why"];
  let sd =
    `<row r="1"><c r="A1" t="inlineStr" s="1"><is><t>Account &amp; Portfolio Prioritization — whitespace opportunities</t></is></c></row><row r="2"/>` +
    `<row r="3">` +
    H.map((h, i) => `<c r="${String.fromCharCode(65 + i)}3" t="inlineStr" s="2"><is><t xml:space="preserve">${xe(h)}</t></is></c>`).join("") +
    `</row>`;
  rows.forEach((o, i) => {
    const rn = i + 4;
    sd +=
      `<row r="${rn}">` +
      `<c r="A${rn}" s="3"><v>${i + 1}</v></c>` +
      `<c r="B${rn}" t="inlineStr" s="4"><is><t>${xe(o.am)}</t></is></c>` +
      `<c r="C${rn}" t="inlineStr" s="4"><is><t>${xe(o.customer)}</t></is></c>` +
      `<c r="D${rn}" t="inlineStr" s="4"><is><t>${xe(o.segment)}</t></is></c>` +
      `<c r="E${rn}" t="inlineStr" s="4"><is><t>${xe(o.product)}</t></is></c>` +
      `<c r="F${rn}" t="inlineStr" s="4"><is><t>${xe(o.group)}</t></is></c>` +
      `<c r="G${rn}" s="5"><v>${Math.round(o.actual)}</v></c>` +
      `<c r="H${rn}" s="3"><v>${Math.round(o.adoption * 100)}</v></c>` +
      `<c r="I${rn}" s="5"><v>${Math.round(o.opp)}</v></c>` +
      `<c r="J${rn}" s="3"><v>${o.margin != null ? o.margin.toFixed(1) : ""}</v></c>` +
      `<c r="K${rn}" t="inlineStr" s="4"><is><t xml:space="preserve">${xe(o.reason)}</t></is></c>` +
      `</row>`;
  });
  const sheet =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<cols><col min="1" max="1" width="6"/><col min="2" max="6" width="16"/>` +
    `<col min="7" max="10" width="14"/><col min="11" max="11" width="70"/></cols>` +
    `<sheetData>${sd}</sheetData>` +
    `<mergeCells count="1"><mergeCell ref="A1:K1"/></mergeCells></worksheet>`;
  const styles =
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    `<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0"/></numFmts>` +
    `<fonts count="3">` +
    `<font><sz val="11"/><name val="Calibri"/><color rgb="FF1F2937"/></font>` +
    `<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>` +
    `<font><b/><sz val="13"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font></fonts>` +
    `<fills count="3"><fill><patternFill patternType="none"/></fill>` +
    `<fill><patternFill patternType="gray125"/></fill>` +
    `<fill><patternFill patternType="solid"><fgColor rgb="FF2F9BFF"/></patternFill></fill></fills>` +
    `<borders count="1"><border/></borders>` +
    `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>` +
    `<cellXfs count="6">` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>` +
    `<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>` +
    `</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
  const files = [
    { name: "[Content_Types].xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`) },
    { name: "_rels/.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
    { name: "xl/workbook.xml", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Prioritized Actions" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
    { name: "xl/_rels/workbook.xml.rels", data: u8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
    { name: "xl/styles.xml", data: u8(styles) },
    { name: "xl/worksheets/sheet1.xml", data: u8(sheet) },
  ];
  const url = URL.createObjectURL(zip(files));
  const a = document.createElement("a");
  a.href = url;
  a.download = "prioritized-actions.xlsx";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
document.getElementById("export-btn").addEventListener("click", exportXLSX);
