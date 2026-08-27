// ---- Correlation Check: page logic ----
// Parsing, the worked pipeline, the two canvases and the results table.
// Statistics live in js/correlation-check.js.

const $ = (id) => document.getElementById(id);

/* ------------------------------ parsing ------------------------------ */
// Accepts CSV or TSV, pasted or uploaded. First column may be a date/label.
function parseTable(text) {
  const sep = text.indexOf("\t") >= 0 ? "\t" : ",";
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length < 4) return { error: "Need at least a header row and 3 data rows." };
  const rows = lines.map((l) => l.split(sep).map((c) => c.trim()));
  const width = rows[0].length;
  if (width < 2) return { error: "Need at least two columns (X and Y). Use commas or tabs." };
  if (rows.some((r) => r.length !== width)) return { error: "Rows have differing column counts — check for stray separators." };

  // A cell is numeric only if the WHOLE string is a number after stripping
  // symbols. parseFloat alone is not enough: parseFloat("2015-11") is 2015,
  // which would silently turn a date column into a data column.
  const clean = (s) => s.replace(/[%$€£\s]/g, "").replace(/,(?=\d{3}\b)/g, "").replace(",", ".");
  const isNum = (s) => s !== "" && /^[+-]?\d*\.?\d+(e[+-]?\d+)?$/i.test(clean(s));
  const hasHeader = !rows[0].every((c, i) => i === 0 || isNum(c));
  const header = hasHeader ? rows[0] : rows[0].map((_, i) => (i === 0 ? "period" : "col" + i));
  const body = hasHeader ? rows.slice(1) : rows;

  // Column roles are positional, as the instructions state: with two columns
  // both are data; with three or more, the first is the label column and the
  // rest are data, selectable as X, Y and an optional control. Guessing roles
  // from content fails on year columns — "1996" is a perfectly good number.
  const labelCol = width >= 3 ? 0 : -1;
  const dataCols = [];
  for (let i = 0; i < width; i++) if (i !== labelCol) dataCols.push(i);

  const toNum = (s) => parseFloat(clean(s));
  const labels = [], cols = dataCols.map(() => []);
  for (const r of body) {
    if (!dataCols.every((c) => isNum(r[c]))) continue;   // skip gap rows
    labels.push(labelCol >= 0 ? r[labelCol] : String(labels.length + 1));
    dataCols.forEach((c, j) => cols[j].push(toNum(r[c])));
  }
  if (labels.length < 8) return { error: "Fewer than 8 usable rows after cleaning — too few to say anything." };
  return {
    labels: labels,
    names: dataCols.map((c) => header[c]),
    cols: cols,
    monthly: /^\d{4}-\d{2}/.test(labels[0]),
  };
}

/* ------------------------------ helpers ------------------------------ */
const fmtP = (p) => (p < 0.001 ? p.toExponential(1) : p.toFixed(3));
const fmtR = (r) => (r >= 0 ? "+" : "") + r.toFixed(3);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function rowHTML(d) {
  if (!d) return "";
  const ci = d.ci ? `[${fmtR(d.ci[0])}, ${fmtR(d.ci[1])}]` : "—";
  const cls = d.sig ? "cc-sig" : "cc-ns";
  const verdictTxt = d.sig ? "significant" : "not significant";
  return `<tr>
    <th scope="row">${esc(d.label)}</th>
    <td>${d.n}</td><td><b>${fmtR(d.r)}</b></td><td>${(d.r2 * 100).toFixed(1)}%</td>
    <td>${fmtP(d.p)}</td><td>${d.nEff.toFixed(1)}</td>
    <td class="${cls}"><b>${fmtP(d.pAdj)}</b></td><td>${ci}</td>
    <td class="${cls}">${verdictTxt}</td>
  </tr>`;
}

/* ------------------------------ charts ------------------------------ */
// Palette: brand blue + orange (validated); text in ink tokens, never series color.
const COL = { x: "#2f9bff", y: "#ff6500", grid: "rgba(31,36,48,.10)", ink: "#1f2430", dim: "#5b6472" };

function fitCanvas(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr;
  const x = cv.getContext("2d");
  x.setTransform(dpr, 0, 0, dpr, 0, 0);
  x.clearRect(0, 0, w, h);
  return [x, w, h];
}

// Two series, each min-max scaled to its own [0,1] on ONE value axis
// ("each indexed to its own range"). Not a dual axis: one scale, stated in the caption.
function drawSeries(cv, labels, a, b, nameA, nameB) {
  const [x, W, H] = fitCanvas(cv);
  const L = 10, R = 10, T = 18, B = 26;
  const scale = (s) => {
    const lo = Math.min.apply(null, s), hi = Math.max.apply(null, s);
    return s.map((v) => (hi === lo ? 0.5 : (v - lo) / (hi - lo)));
  };
  const px = (i) => L + (i / (labels.length - 1)) * (W - L - R);
  const py = (v) => T + (1 - v) * (H - T - B);
  x.strokeStyle = COL.grid; x.lineWidth = 1;
  [0, 0.5, 1].forEach((g) => { x.beginPath(); x.moveTo(L, py(g)); x.lineTo(W - R, py(g)); x.stroke(); });
  [[scale(a), COL.x, nameA], [scale(b), COL.y, nameB]].forEach(([s, col, name], si) => {
    x.strokeStyle = col; x.lineWidth = 2; x.beginPath();
    s.forEach((v, i) => (i ? x.lineTo(px(i), py(v)) : x.moveTo(px(i), py(v))));
    x.stroke();
    x.fillStyle = COL.ink; x.font = "600 12px " + getComputedStyle(document.body).fontFamily;
    x.textAlign = "left";
    x.fillStyle = col; x.fillRect(L + si * 130, 4, 9, 9);
    x.fillStyle = COL.ink; x.fillText(String(name).slice(0, 16), L + 13 + si * 130, 13);
  });
  x.fillStyle = COL.dim; x.font = "11px " + getComputedStyle(document.body).fontFamily;
  x.textAlign = "left"; x.fillText(labels[0], L, H - 8);
  x.textAlign = "right"; x.fillText(labels[labels.length - 1], W - R, H - 8);
}

// Scatter of the changes, with the fitted line.
function drawScatter(cv, dx, dy, nameA, nameB) {
  const [x, W, H] = fitCanvas(cv);
  const L = 34, R = 12, T = 14, B = 30;
  const lox = Math.min.apply(null, dx), hix = Math.max.apply(null, dx);
  const loy = Math.min.apply(null, dy), hiy = Math.max.apply(null, dy);
  const px = (v) => L + ((v - lox) / (hix - lox || 1)) * (W - L - R);
  const py = (v) => T + (1 - (v - loy) / (hiy - loy || 1)) * (H - T - B);
  x.strokeStyle = COL.grid;
  if (lox < 0 && hix > 0) { x.beginPath(); x.moveTo(px(0), T); x.lineTo(px(0), H - B); x.stroke(); }
  if (loy < 0 && hiy > 0) { x.beginPath(); x.moveTo(L, py(0)); x.lineTo(W - R, py(0)); x.stroke(); }
  x.fillStyle = COL.x; x.globalAlpha = 0.55;
  for (let i = 0; i < dx.length; i++) { x.beginPath(); x.arc(px(dx[i]), py(dy[i]), 3.5, 0, 7); x.fill(); }
  x.globalAlpha = 1;
  const b1 = CC.slope(dx, dy);
  if (b1 !== null) {
    const mx = dx.reduce((s, v) => s + v, 0) / dx.length, my = dy.reduce((s, v) => s + v, 0) / dy.length;
    x.strokeStyle = COL.y; x.lineWidth = 2; x.beginPath();
    x.moveTo(px(lox), py(my + b1 * (lox - mx))); x.lineTo(px(hix), py(my + b1 * (hix - mx))); x.stroke();
  }
  x.fillStyle = COL.dim; x.font = "11px " + getComputedStyle(document.body).fontFamily;
  x.textAlign = "center"; x.fillText("change in " + String(nameA).slice(0, 20), (L + W - R) / 2, H - 8);
  x.save(); x.translate(11, (T + H - B) / 2); x.rotate(-Math.PI / 2);
  x.fillText("change in " + String(nameB).slice(0, 20), 0, 0); x.restore();
}

// Residuals against fitted values. A healthy fit is a structureless band
// around zero; any curve, funnel or drift is what the model got wrong.
function drawResiduals(cv, reg) {
  const [x, W, H] = fitCanvas(cv);
  const L = 34, R = 12, T = 14, B = 30;
  const f = reg.fitted, e = reg.resid;
  const lof = Math.min.apply(null, f), hif = Math.max.apply(null, f);
  const m = Math.max.apply(null, e.map(Math.abs)) || 1;
  const px = (v) => L + ((v - lof) / (hif - lof || 1)) * (W - L - R);
  const py = (v) => T + (1 - (v + m) / (2 * m)) * (H - T - B);
  x.strokeStyle = COL.grid; x.lineWidth = 1;
  x.beginPath(); x.moveTo(L, py(0)); x.lineTo(W - R, py(0)); x.stroke();
  x.fillStyle = COL.x; x.globalAlpha = 0.55;
  for (let i = 0; i < f.length; i++) { x.beginPath(); x.arc(px(f[i]), py(e[i]), 3.5, 0, 7); x.fill(); }
  x.globalAlpha = 1;
  x.fillStyle = COL.dim; x.font = "11px " + getComputedStyle(document.body).fontFamily;
  x.textAlign = "center"; x.fillText("fitted value", (L + W - R) / 2, H - 8);
  x.save(); x.translate(11, (T + H - B) / 2); x.rotate(-Math.PI / 2);
  x.fillText("residual", 0, 0); x.restore();
}

/* ------------------------------ pipeline ------------------------------ */
const CC = window.CC; // statistics module, attached below

/* --------------------------- minimal .xlsx reader -------------------------- */
// An .xlsx file is a zip of XML. Modern browsers ship the decompressor
// (DecompressionStream "deflate-raw"), so no library is needed for the
// simple case: first worksheet, values and shared strings.

async function inflateRaw(bytes) {
  const ds = new DecompressionStream("deflate-raw");
  const stream = new Blob([bytes]).stream().pipeThrough(ds);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function readXlsx(buf) {
  const b = new Uint8Array(buf);
  const dv = new DataView(buf);
  // find End Of Central Directory record (signature 0x06054b50), scan from end
  let eocd = -1;
  for (let i = b.length - 22; i >= 0; i--) {
    if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("not a zip");
  const count = dv.getUint16(eocd + 10, true);
  let off = dv.getUint32(eocd + 16, true);
  const entries = {};
  for (let e = 0; e < count; e++) {
    if (dv.getUint32(off, true) !== 0x02014b50) break;
    const method = dv.getUint16(off + 10, true);
    const csize = dv.getUint32(off + 20, true);
    const nameLen = dv.getUint16(off + 28, true);
    const extraLen = dv.getUint16(off + 30, true);
    const cmtLen = dv.getUint16(off + 32, true);
    const lho = dv.getUint32(off + 42, true);
    const name = new TextDecoder().decode(b.subarray(off + 46, off + 46 + nameLen));
    entries[name] = { method, csize, lho };
    off += 46 + nameLen + extraLen + cmtLen;
  }
  async function file(name) {
    const en = entries[name];
    if (!en) return null;
    const nl = dv.getUint16(en.lho + 26, true), xl = dv.getUint16(en.lho + 28, true);
    const start = en.lho + 30 + nl + xl;
    const raw = b.subarray(start, start + en.csize);
    const data = en.method === 0 ? raw : await inflateRaw(raw);
    return new TextDecoder().decode(data);
  }
  // shared strings
  const sstXml = await file("xl/sharedStrings.xml");
  const sst = [];
  if (sstXml) {
    for (const m of sstXml.matchAll(/<si[ >][\s\S]*?<\/si>/g)) {
      sst.push([...m[0].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map((t) => t[1]).join(""));
    }
  }
  // first worksheet: sheet1 by convention, else first sheetN present
  let sheet = await file("xl/worksheets/sheet1.xml");
  if (!sheet) {
    const cand = Object.keys(entries).filter((k) => /^xl\/worksheets\/sheet\d+\.xml$/.test(k)).sort();
    if (cand.length) sheet = await file(cand[0]);
  }
  if (!sheet) throw new Error("no worksheet found");
  const rows = [];
  for (const rm of sheet.matchAll(/<row[^>]*>([\s\S]*?)<\/row>/g)) {
    const cells = [];
    for (const cm of rm[1].matchAll(/<c([^>]*)>([\s\S]*?)<\/c>/g)) {
      const attrs = cm[1], inner = cm[2];
      const ref = /r="([A-Z]+)\d+"/.exec(attrs);
      let col = cells.length;
      if (ref) {
        col = 0;
        for (const ch of ref[1]) col = col * 26 + (ch.charCodeAt(0) - 64);
        col -= 1;
      }
      const vM = /<v>([\s\S]*?)<\/v>/.exec(inner);
      const tM = /<t[^>]*>([\s\S]*?)<\/t>/.exec(inner);
      let val = "";
      if (/t="s"/.test(attrs) && vM) val = sst[+vM[1]] ?? "";
      else if (/t="inlineStr"/.test(attrs) && tM) val = tM[1];
      else if (vM) val = vM[1];
      while (cells.length < col) cells.push("");
      cells[col] = val.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
    }
    if (cells.some((c) => c !== "")) rows.push(cells.join(","));
  }
  return rows.join("\n");
}

/* ----------------------------- python export -------------------------------- */

function buildPython() {
  if (!lastRun) return null;
  const L = lastRun;
  const zPart = L.z.length
    ? `Z = df.iloc[:, ${JSON.stringify(L.z.map((i) => i + 1))}]           # controls: ${L.zNames.join(", ")}\n`
    : "";
  const zModel = L.z.length
    ? `X_multi = sm.add_constant(pd.concat([dx] + [Z.iloc[:, i].pct_change(H).dropna() for i in range(Z.shape[1])], axis=1).dropna())
m2 = sm.OLS(dy.loc[X_multi.index], X_multi).fit(cov_type="HAC", cov_kwds={"maxlags": LAGS})
print("\\nWith controls held constant:")
print(m2.summary().tables[1])\n`
    : "";
  return `# ${document.title}
# Generated by the Correlation & Regression Check — the same analysis in Python.
# Requires: pandas, numpy, scipy, statsmodels.
import io
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

${scPyData(L.d)}

df = pd.read_csv(io.StringIO(DATA))
x = df.iloc[:, ${L.x + 1}].astype(float)   # ${L.nameA}
y = df.iloc[:, ${L.y + 1}].astype(float)   # ${L.nameB}
${zPart}H = ${L.h}                                # change horizon (12 = year-on-year on monthly data)

# --- levels vs changes: the correlation, twice --------------------------------
def n_effective(a, b):
    """Sample size discounted for autocorrelation (Bartlett/Quenouille).
    A long monthly series is not a large sample: each month is mostly last
    month, and the naive p-value silently assumes it is not."""
    r1, r2 = a.autocorr(1), b.autocorr(1)
    prod = r1 * r2
    return max(3.0, len(a) * (1 - prod) / (1 + prod)) if prod < 1 else 3.0

def honest_corr(a, b, label):
    r, p_naive = stats.pearsonr(a, b)
    ne = n_effective(a, b)
    t = r * np.sqrt(ne - 2) / np.sqrt(1 - r * r)
    p_adj = 2 * stats.t.sf(abs(t), ne - 2)
    print(f"{label:8s} n={len(a):4d}  r={r:+.3f}  p_naive={p_naive:.2e}  "
          f"n_eff={ne:6.1f}  p_adjusted={p_adj:.3f}"
          + ("   <-- the p that matters" if label != "levels" else ""))
    return r, p_adj

dx = x.pct_change(H).dropna()
dy = y.pct_change(H).dropna()
honest_corr(x, y, "levels")
honest_corr(dx, dy, "changes")

# --- regression on changes, autocorrelation-robust errors ---------------------
LAGS = max(1, int(4 * (len(dx) / 100) ** (2 / 9)))     # Newey-West bandwidth
m = sm.OLS(dy.values, sm.add_constant(dx.values)).fit(
    cov_type="HAC", cov_kwds={"maxlags": LAGS})
print(f"\\nslope = {m.params[1]:+.4f}  NW se = {m.bse[1]:.4f}  p = {m.pvalues[1]:.4g}")
${zModel}
# --- cointegration: the one honest exception to "distrust levels" -------------
tau, p_coint, _ = coint(y, x, trend="c", maxlag=1, autolag=None)
print(f"\\nEngle-Granger tau = {tau:.2f}, p = {p_coint:.3f}"
      "  (only a strong pass rescues a levels correlation)")
`;
}

/* ------------------------------- report export ------------------------------ */
// Everything on screen, as a markdown block: data-integrity rule 10 says the
// numbers travel with their method or they do not travel.

function buildReport() {
  const strip = (id) => ($(id).textContent || "").replace(/\s+/g, " ").trim();
  const lines = ["# Correlation & Regression Check — verification report", ""];
  lines.push("Generated by https://namikakmandev.github.io/correlation-check.html — all computation in-browser, data never uploaded.", "");
  const warn = $("cc-warnbox").hidden ? "" : strip("cc-warnings");
  if (warn) lines.push("## Warnings", warn, "");
  lines.push("## Correlation (levels vs changes)", "");
  lines.push("| form | n | r | R² | p naive | n_eff | p adjusted | 95% CI | verdict |");
  lines.push("|---|---|---|---|---|---|---|---|---|");
  for (const tr of $("cc-tbody").rows) {
    lines.push("| " + [...tr.cells].map((c) => c.textContent.trim()).join(" | ") + " |");
  }
  lines.push("", "## Verdict", strip("cc-verdict"), "");
  if (!$("cc-regbox").hidden) lines.push("## Regression", strip("cc-regbody"), "");
  if (!$("cc-ctrlbox").hidden) lines.push("## Confounder control", strip("cc-ctrlbody"), "");
  if (!$("cc-robbox").hidden) {
    lines.push("## Robustness", "");
    for (const tr of $("cc-robtbody").rows)
      lines.push("- **" + tr.cells[0].textContent.trim() + "**: " + tr.cells[1].textContent.trim() + " — " + tr.cells[2].textContent.trim());
    lines.push("");
  }
  const led = strip("cc-ledger");
  if (led) lines.push("## Multiple-testing note", led, "");
  lines.push("---", "Method: Pearson r; exact t-distribution p; Fisher-z CI; effective sample size from lag-1 autocorrelations; permutation test; MAD break detection; Bonferroni-corrected lag scan; OLS with Newey–West (HAC) errors; Engle–Granger cointegration (MacKinnon finite-sample critical values); moving-block bootstrap; 70/30 out-of-sample split.");
  lines.push("Generated: " + new Date().toISOString().slice(0, 10));
  return lines.join("\n");
}

const ledger = { count: 0 };

/* Real-data examples: the committed datasets this site's studies are built on,
   loaded straight from data/*.json. Each carries its own story card, because a
   number without its source and span is not a finding (data-integrity rule 9). */
const REAL_EXAMPLES = {
  corn: {
    story: "<strong>US cattle vs corn prices, 1971&ndash;2026</strong> &mdash; 55 years of " +
      "Bureau of Labor Statistics producer price indexes (WPU0131 slaughter cattle, WPU012202 corn), " +
      "667 monthly observations. In levels they correlate at r&nbsp;=&nbsp;0.59 with " +
      "p&nbsp;=&nbsp;10<sup>&minus;63</sup> &mdash; and almost all of it is shared inflation trend. " +
      "Watch the changes row, the effective sample size, and the verdict.",
    yoy: false,
    async load() {
      const d = await (await fetch("data/cattle-us.json")).json();
      return "month,cattle PPI,corn PPI\n" +
        d.rows.map((r) => `${r[0]},${r[1]},${r[2]}`).join("\n");
    },
  },
  parity: {
    story: "<strong>US vs EU cattle margins, 2015&ndash;2026</strong> &mdash; the meat-to-feed " +
      "price ratio in each market (BLS producer prices for the US; European Commission beef and " +
      "feed prices for the EU). This one is <em>real</em>: it survives every check &mdash; " +
      "significant in year-on-year changes after the autocorrelation discount, and strongly " +
      "cointegrated. An ocean apart, one margin cycle.",
    yoy: true,
    async load() {
      const [us, eu] = await Promise.all([
        (await fetch("data/cattle-us.json")).json(),
        (await fetch("data/cattle-eu.json")).json(),
      ]);
      const em = new Map(eu.rows.map((r) => [r[0], r[3]]));
      return "month,US margin,EU margin\n" +
        us.rows.filter((r) => em.has(r[0]))
          .map((r) => `${r[0]},${r[3]},${em.get(r[0])}`).join("\n");
    },
  },
  vet: {
    story: "<strong>EU veterinary spending vs the cattle herd, 2005&ndash;2024</strong> &mdash; " +
      "Eurostat agricultural accounts (vet expenses, million EUR) against FAOSTAT cattle stocks. " +
      "A published analysis once put this relationship at r&nbsp;=&nbsp;&minus;0.94. Deflated and " +
      "checked honestly, there is <em>no detectable relationship at all</em> &mdash; and twenty " +
      "annual points of two slow series carry about five independent facts. An honest null.",
    yoy: false,
    async load() {
      const [vet, herd] = await Promise.all([
        (await fetch("data/eu-vet-expenses.json")).json(),
        (await fetch("data/herd-cattle.json")).json(),
      ]);
      const v = vet.series.EU27_2020, h = herd.series.EU;
      const years = Object.keys(v).filter((y) => y in h).sort();
      return "year,vet spend mEUR,cattle herd\n" +
        years.map((y) => `${y},${v[y]},${h[y]}`).join("\n");
    },
  },
};

async function loadRealExample(key, btn) {
  const ex = REAL_EXAMPLES[key];
  const label = btn.textContent;
  btn.textContent = "Loading\u2026";
  try {
    $("cc-input").value = await ex.load();
    $("cc-yoy").checked = ex.yoy;
    $("cc-story").innerHTML = ex.story;
    $("cc-story").hidden = false;
    run._fromExample = true;
    run();
  } catch (e) {
    $("cc-error").textContent = "Could not load the dataset (this works on the live site, " +
      "where the data files sit next to the page).";
  }
  btn.textContent = label;
}
let lastRun = null;   // state of the most recent successful run, for share/export

function run() {
  if (!run._fromExample) $("cc-story").hidden = true;
  run._fromExample = false;
  const parsed = parseTable($("cc-input").value);
  const out = $("cc-results"), errBox = $("cc-error");
  errBox.textContent = ""; out.hidden = true;
  if (parsed.error) { errBox.textContent = parsed.error; return; }

  // Column pickers: shown whenever a third data column exists (a control
  // candidate). Options are rebuilt only when the column set changes, so the
  // user's selection survives re-runs on the same data.
  const key = parsed.names.join("\u0001");
  const pickers = ["cc-colx", "cc-coly", "cc-colz"].map($);
  if ($("cc-colbar").dataset.key !== key) {
    $("cc-colbar").dataset.key = key;
    pickers.forEach((sel, which) => {
      sel.innerHTML = parsed.names.map((nm, i) => `<option value="${i}">${esc(nm)}</option>`).join("");
      if (which === 2) { sel.value = null; [...sel.options].forEach((o) => (o.selected = false)); }
      else sel.value = String(which);
    });
  }
  $("cc-colbar").hidden = parsed.names.length <= 2;
  const xi = +pickers[0].value, yi = +pickers[1].value;
  const zIdx = [...pickers[2].selectedOptions].map((o) => +o.value)
    .filter((i) => i !== xi && i !== yi);
  if (xi === yi) { errBox.textContent = "X and Y are the same column."; return; }
  let xs = parsed.cols[xi], ys = parsed.cols[yi];
  const nameA = parsed.names[xi], nameB = parsed.names[yi], labels = parsed.labels;
  const zCols = zIdx.map((i) => parsed.cols[i]);
  const zNames = zIdx.map((i) => parsed.names[i]);
  const h = parsed.monthly && $("cc-yoy").checked ? 12 : 1;

  // 1 · warnings first: breaks and zero crossings
  const breaks = [];
  CC.findBreaks(xs, labels, esc(nameA)).forEach((b) => breaks.push("Possible methodology break — " + b));
  CC.findBreaks(ys, labels, esc(nameB)).forEach((b) => breaks.push("Possible methodology break — " + b));
  // A wall of warnings is as unreadable as none: cap the break list. But cap
  // ONLY the break list — the zero-crossing note changes how the whole
  // changes row is computed and must never be squeezed out by it.
  let shown = breaks;
  if (breaks.length > 5)
    shown = breaks.slice(0, 4).concat(
      `&hellip;and ${breaks.length - 4} more single-period jumps. In a long volatile series ` +
      `these are usually genuine shocks rather than methodology breaks &mdash; but a break ` +
      `hiding among them would look identical, so scan the list before comparing across it.`);
  if (CC.crossesZero(xs)) shown.push(esc(nameA) + " crosses zero — changes use absolute differences, not percent.");
  if (CC.crossesZero(ys)) shown.push(esc(nameB) + " crosses zero — changes use absolute differences, not percent.");
  $("cc-warnings").innerHTML = shown.map((w) => `<li>${w}</li>`).join("");
  $("cc-warnbox").hidden = !shown.length;

  // 2 · levels vs changes
  const dx = CC.change(xs, h), dy = CC.change(ys, h);
  const lev = CC.describe("Levels", xs, ys);
  const chg = CC.describe(h > 1 ? "Year-on-year changes" : "Changes", dx, dy);
  $("cc-tbody").innerHTML = rowHTML(lev) + rowHTML(chg);

  // 3 · verdict
  const v = [];
  if (lev && chg) {
    if (lev.p < 0.05 && !lev.sig)
      v.push(`The levels correlation of <b>${fmtR(lev.r)}</b> looks overwhelming (p = ${fmtP(lev.p)}), but ${lev.n} observations carry only ~${Math.round(lev.nEff)} independent facts. Adjusted for that, it is <b>not significant</b>.`);
    if (!chg.sig) {
      v.push(lev.p < 0.05
        ? "The correlation does not survive in changes. Most likely two trends passing each other — <b>do not publish the levels figure</b>."
        : "No relationship detectable in either form. An honest null — which is still a finding.");
    } else {
      v.push(`Survives in changes: r = <b>${fmtR(chg.r)}</b>, adjusted p = ${fmtP(chg.pAdj)}. It explains ${(chg.r2 * 100).toFixed(0)}% of the variance — the other ${(100 - chg.r2 * 100).toFixed(0)}% is something else.`);
      if (Math.abs(lev.r) - Math.abs(chg.r) > 0.3)
        v.push(`It shrank by ${(Math.abs(lev.r) - Math.abs(chg.r)).toFixed(2)} from the levels figure — the levels number was inflated by shared trend. Quote the changes figure.`);
      const pp = CC.permPValue(dx, dy);
      v.push(`Assumption-free check: shuffling one series 2,000 times, a correlation this large appears by luck with probability ${fmtP(pp)}.`);
      const b1 = CC.slope(dx, dy);
      if (b1 !== null)
        v.push(`Slope: a 1${h > 1 || !CC.crossesZero(xs) ? "%" : "-unit"} move in ${esc(nameA)} goes with a <b>${(b1 >= 0 ? "+" : "") + b1.toFixed(2)}${!CC.crossesZero(ys) ? "%" : "-unit"}</b> move in ${esc(nameB)}.`);
    }
  }
  // Cointegration: the one honest exception to "distrust levels". Only worth
  // asking when the levels correlate strongly but the changes are weak.
  if (lev && chg && Math.abs(lev.r) > 0.6 && xs.length >= 30) {
    const eg = CC.engleGranger(xs, ys);
    if (eg) {
      if (eg.verdict === "strong")
        v.push(`Cointegration (Engle&ndash;Granger): &tau; = ${eg.tau.toFixed(2)} against a 1% critical value of ${eg.crit.p01.toFixed(2)} &mdash; <b>the levels move together long-run</b>. This is the one case where a levels relationship is real even though each series trends: differencing throws it away, so report the levels link as cointegration, with this test attached.`);
      else if (eg.verdict === "borderline")
        v.push(`Cointegration (Engle&ndash;Granger): &tau; = ${eg.tau.toFixed(2)}, past the 5% value (${eg.crit.p05.toFixed(2)}) but not the 1% (${eg.crit.p01.toFixed(2)}). <b>Borderline</b> &mdash; 1 in 20 pairs of unrelated trending series also gets here, so treat it as a hypothesis, not a finding.`);
      else
        v.push(`Cointegration (Engle&ndash;Granger): &tau; = ${eg.tau.toFixed(2)}, short of the 5% critical value (${eg.crit.p05.toFixed(2)}). <b>No long-run link</b> &mdash; the levels co-movement really is just trend.`);
    }
  }
  $("cc-verdict").innerHTML = v.map((t) => `<p>${t}</p>`).join("");

  // Multiple-testing ledger: every check run this session raises the honest
  // bar. Scanning many pairs and keeping the best is many tests, not one.
  ledger.count++;
  const bar = 0.05 / ledger.count;
  $("cc-ledger").innerHTML = ledger.count === 1
    ? ""
    : `Check <b>#${ledger.count}</b> this session. If you are hunting through pairs and will keep the best, the honest bar is p &lt; <b>${bar.toPrecision(2)}</b> (0.05 &divide; ${ledger.count}), not 0.05.`;

  // 3b · regression on changes — the slope is the number someone can act on
  const reg = CC.ols(dx, dy);
  const unitX = CC.crossesZero(xs) ? " units" : "%";
  const unitY = CC.crossesZero(ys) ? " units" : "%";
  if (reg) {
    const rv = [];
    rv.push(`<p class="cc-eq">Δ${esc(nameB)} = ${fmtR(reg.a)} ${reg.b >= 0 ? "+" : "−"} ${Math.abs(reg.b).toFixed(3)} · Δ${esc(nameA)}</p>`);
    rv.push(`<p>A 1${unitX} move in ${esc(nameA)} goes with a <b>${(reg.b >= 0 ? "+" : "") + reg.b.toFixed(2)}${unitY}</b> move in ${esc(nameB)} &mdash; 95% CI [${reg.ciB[0].toFixed(2)}, ${reg.ciB[1].toFixed(2)}], adjusted p = ${fmtP(reg.pAdj)} ${reg.pAdj < 0.05 ? '<span class="cc-sig">(slope distinguishable from zero)</span>' : '<span class="cc-ns">(slope NOT distinguishable from zero — do not quote it as an effect)</span>'}.</p>`);
    rv.push(`<p>The regression explains ${(reg.r2 * 100).toFixed(0)}% of the variance in the changes; the other ${(100 - reg.r2 * 100).toFixed(0)}% is something this pair does not capture.</p>`);
    const mk = CC.olsK([dx], dy);
    if (mk) {
      const b = mk.beta[1], se = mk.seNW[1], pnw = mk.pNW[1];
      rv.push(`<p>Newey&ndash;West errors (${mk.nwLags} lags): slope ${b.toFixed(3)} &plusmn; ${(1.96 * se).toFixed(3)}, p = ${fmtP(pnw)} ${pnw < 0.05 ? '<span class="cc-sig">(holds under autocorrelation-robust errors)</span>' : '<span class="cc-ns">(does not survive autocorrelation-robust errors)</span>'}.</p>`);
    }
    if (reg.dw < 1.2 || reg.dw > 2.8)
      rv.push(`<p>Durbin&ndash;Watson = ${reg.dw.toFixed(2)} &mdash; the residuals are ${reg.dw < 1.2 ? "positively" : "negatively"} autocorrelated, so even these adjusted errors are on the optimistic side. Whatever the model misses, it misses persistently.</p>`);
    $("cc-regbody").innerHTML = rv.join("");
    $("cc-regbox").hidden = false;
  } else $("cc-regbox").hidden = true;

  // 3c · confounder controls: does X survive holding the others constant?
  if (zCols.length && reg) {
    const dzs = zCols.map((zc) => CC.change(zc, h));
    const m = CC.olsK([dx].concat(dzs), dy);
    if (m) {
      const bx = m.beta[1], px = m.pNW[1];
      const collapse = Math.abs(bx) < Math.abs(reg.b) * 0.5 || px >= 0.05;
      const zLabel = zNames.map(esc).join(", ");
      const rows = [`<p>Alone, the ${esc(nameA)} slope is <b>${reg.b.toFixed(3)}</b>. Holding ${zLabel} constant it becomes <b>${bx.toFixed(3)}</b> (Newey&ndash;West p = ${fmtP(px)}). The full model explains ${(m.r2 * 100).toFixed(0)}% of the variance (adjusted ${(m.adjR2 * 100).toFixed(0)}%).</p>`];
      rows.push('<div class="cc-table-wrap"><table class="cc-table"><thead><tr><th>predictor</th><th>coefficient</th><th>&plusmn;95% (NW)</th><th>p (NW)</th>' + (m.vif ? "<th>VIF</th>" : "") + "</tr></thead><tbody>" +
        [nameA].concat(zNames).map((nm, i) => {
          const j = i + 1;
          const vifCell = m.vif ? `<td>${m.vif[i] >= 5 ? "<b>" + m.vif[i].toFixed(1) + "</b> !" : m.vif[i].toFixed(1)}</td>` : "";
          return `<tr><th scope="row">${esc(nm)}</th><td>${m.beta[j].toFixed(3)}</td><td>${(1.96 * m.seNW[j]).toFixed(3)}</td><td>${fmtP(m.pNW[j])}</td>${vifCell}</tr>`;
        }).join("") + "</tbody></table></div>");
      if (m.vif && m.vif.some((v) => v >= 5))
        rows.push("<p>A VIF above 5 means that predictor is mostly a recombination of the others &mdash; its coefficient and p-value are unstable. Drop one of the overlapping predictors.</p>");
      rows.push(collapse
        ? `<p><b>The ${esc(nameA)} effect does not survive the controls.</b> Most of what it appeared to explain is carried by ${zLabel} — treat ${esc(nameA)} as a proxy until something rules that out.</p>`
        : `<p>The ${esc(nameA)} effect survives the controls &mdash; whatever ${zLabel} contributes, it does not account for this relationship.</p>`);
      $("cc-ctrlbody").innerHTML = rows.join("");
      $("cc-ctrlbox").hidden = false;
    } else {
      $("cc-ctrlbody").innerHTML = `<p>The controls are collinear with ${esc(nameA)} — the model cannot be separated.</p>`;
      $("cc-ctrlbox").hidden = false;
    }
  } else $("cc-ctrlbox").hidden = true;

  // 3d · robustness: four ways one number can be fragile
  {
    const rows = [];
    const sp = CC.spearman(dx, dy);
    if (sp !== null && chg) {
      const gap = Math.abs(sp - chg.r);
      rows.push(["Rank (Spearman)", fmtR(sp),
        gap > 0.15 ? "far from Pearson — the relationship is nonlinear or outlier-driven; plot it" : "close to Pearson — the linear reading is fair"]);
    }
    const inf = CC.influence(dx, dy);
    if (inf) rows.push(["Drop-one influence", "±" + inf.maxShift.toFixed(3),
      inf.maxShift > 0.1 ? "one observation (" + esc(labels[Math.min(inf.index + h, labels.length - 1)]) + ") moves r by this much — fragile" : "no single observation controls the result"]);
    const sh = CC.splitHalf(dx, dy);
    if (sh && sh.first !== null && sh.second !== null) {
      const agree = sh.first * sh.second > 0 && Math.abs(sh.first - sh.second) < 0.35;
      rows.push(["Split-half", fmtR(sh.first) + " / " + fmtR(sh.second),
        agree ? "both halves agree" : "the halves disagree — the finding may be one period, not a relationship"]);
    }
    const bb = CC.blockBootstrapCI(dx, dy, 2000, h);
    if (bb) {
      const straddles = bb.lo * bb.hi < 0;
      rows.push(["Block-bootstrap 95% CI",
        `[${fmtR(bb.lo)}, ${fmtR(bb.hi)}]`,
        (straddles ? "straddles zero — the sign is not established. " : "") +
        `resampled in blocks of ${bb.blockLen} so the autocorrelation survives into the interval`]);
    }
    const oos = CC.outOfSample(dx, dy);
    if (oos) rows.push(["Out-of-sample R²", (oos.r2 * 100).toFixed(0) + "%",
      oos.r2 <= 0 ? "fit on the first " + oos.nTrain + ", the model does WORSE than guessing the mean on the last " + oos.nTest : "fit on the first " + oos.nTrain + " points, holds up on the last " + oos.nTest]);
    $("cc-robtbody").innerHTML = rows.map((r) =>
      `<tr><th scope="row">${r[0]}</th><td>${r[1]}</td><td class="cc-note">${r[2]}</td></tr>`).join("");
    $("cc-robbox").hidden = !rows.length;
  }

  // 4 · lag scan
  const span = Math.min(6, Math.floor(labels.length / 8));
  const lagBox = $("cc-lagbox");
  if (span >= 2) {
    const sc = CC.scanLags(xs, ys, span, h);
    if (sc) {
      $("cc-lagtbody").innerHTML = sc.rows.map((d) => {
        const peak = d.lag === sc.best.lag, zero = d.lag === 0;
        const bar = Math.round(Math.abs(d.changes) * 160);
        return `<tr class="${peak ? "cc-peak" : ""}">
          <td>${d.lag > 0 ? "+" + d.lag : d.lag}</td><td>${fmtR(d.levels)}</td><td>${fmtR(d.changes)}</td>
          <td><span class="cc-bar" style="width:${bar}px"></span>${peak ? " ← peak" : zero ? " ← lag 0" : ""}</td></tr>`;
      }).join("");
      $("cc-lagverdict").textContent = sc.verdict + " (" + sc.k + " lags tested; the significance bar rises to p < " + sc.alpha.toFixed(4) + " to compensate.)";
      lagBox.hidden = false;
    } else lagBox.hidden = true;
  } else lagBox.hidden = true;

  // 5 · charts — unhide FIRST: a canvas inside display:none has zero width
  lastRun = { v: 1, d: $("cc-input").value, yoy: $("cc-yoy").checked,
              x: xi, y: yi, z: zIdx,
              names: parsed.names, h: h,
              nameA: nameA, nameB: nameB, zNames: zNames };
  out.hidden = false;
  drawSeries($("cc-chart-series"), labels, xs, ys, nameA, nameB);
  drawScatter($("cc-chart-scatter"), dx, dy, nameA, nameB);
  $("cc-resid-card").hidden = !reg;      // unhide BEFORE drawing: zero width inside display:none
  if (reg) drawResiduals($("cc-chart-resid"), reg);

  out.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ------------------------------ demo data ------------------------------ */
// Two independent random walks — true correlation exactly zero. Seeded, so
// everyone sees the same trap.
function demoData() {
  let seed = 7;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff - 0.5; };
  const rows = ["period,series A,series B"];
  let a = 100, b = 50;
  for (let i = 0; i < 120; i++) {
    a += 0.4 + rnd() * 2.2; b += 0.3 + rnd() * 2.2;
    const y = 2016 + Math.floor(i / 12), m = (i % 12) + 1;
    rows.push(`${y}-${String(m).padStart(2, "0")},${a.toFixed(2)},${b.toFixed(2)}`);
  }
  return rows.join("\n");
}

/* ------------------------------ wiring ------------------------------ */
document.addEventListener("DOMContentLoaded", () => {
  $("cc-run").addEventListener("click", run);
  $("cc-report").addEventListener("click", () => {
    if ($("cc-results").hidden) { run(); }
    if ($("cc-results").hidden) return;               // run failed
    const md = buildReport();
    navigator.clipboard && navigator.clipboard.writeText(md).catch(() => {});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
    a.download = "correlation-check-report.md";
    a.click();
    URL.revokeObjectURL(a.href);
  });
  ["corn", "parity", "vet"].forEach((k) =>
    $("cc-real-" + k).addEventListener("click", (e) => loadRealExample(k, e.target)));
  scInitShare("cc-share", () => lastRun);
  $("cc-python").addEventListener("click", () => {
    if (!lastRun) run();
    if (!lastRun) return;
    scShowCode("cc-codebox", buildPython());
  });
  scLoadShared((st) => {
    $("cc-input").value = st.d || "";
    $("cc-yoy").checked = !!st.yoy;
    run();                                     // builds pickers with defaults
    if (st.names && st.names.join("\u0001") === $("cc-colbar").dataset.key) {
      $("cc-colx").value = String(st.x);
      $("cc-coly").value = String(st.y);
      [...$("cc-colz").options].forEach((o) => (o.selected = (st.z || []).includes(+o.value)));
      run();                                   // as the change events would
    }
  });
  ["cc-colx", "cc-coly", "cc-colz"].forEach((id) =>
    $(id).addEventListener("change", () => { if (!$("cc-results").hidden) run(); }));
  $("cc-demo").addEventListener("click", () => { $("cc-input").value = demoData(); $("cc-yoy").checked = false; run(); });
  $("cc-file").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (/\.xlsx$/i.test(f.name)) {
      try {
        $("cc-input").value = await readXlsx(await f.arrayBuffer());
        run();
      } catch (err) {
        $("cc-error").textContent = "Could not read this .xlsx (" + err.message +
          "). Save the sheet as CSV and paste or upload that instead.";
      }
      e.target.value = "";
      return;
    }
    const rd = new FileReader();
    rd.onload = () => { $("cc-input").value = rd.result; run(); };
    rd.readAsText(f);
    e.target.value = "";
  });
  let t; window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => { if (!$("cc-results").hidden) run(); }, 150); });
  const realM = /[?&]real=(\w+)/.exec(location.search);
  if (realM && REAL_EXAMPLES[realM[1]])
    loadRealExample(realM[1], $("cc-real-" + realM[1]));
  else if (location.search.indexOf("demo") >= 0) {
    $("cc-input").value = demoData(); $("cc-yoy").checked = false; run();
    window.scrollTo(0, $("cc-results").offsetTop - 10);   // land on the verdict
  }
});
