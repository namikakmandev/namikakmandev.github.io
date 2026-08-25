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

function run() {
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
      sel.innerHTML = (which === 2 ? '<option value="-1">none</option>' : "") +
        parsed.names.map((nm, i) => `<option value="${i}">${esc(nm)}</option>`).join("");
      sel.value = which === 2 ? "-1" : String(which);
    });
  }
  $("cc-colbar").hidden = parsed.names.length <= 2;
  const xi = +pickers[0].value, yi = +pickers[1].value, zi = +pickers[2].value;
  if (xi === yi) { errBox.textContent = "X and Y are the same column."; return; }
  let xs = parsed.cols[xi], ys = parsed.cols[yi];
  const zs = zi >= 0 && zi !== xi && zi !== yi ? parsed.cols[zi] : null;
  const nameA = parsed.names[xi], nameB = parsed.names[yi], labels = parsed.labels;
  const nameZ = zs ? parsed.names[zi] : null;
  const h = parsed.monthly && $("cc-yoy").checked ? 12 : 1;

  // 1 · warnings first: breaks and zero crossings
  const warns = [];
  CC.findBreaks(xs, labels, esc(nameA)).forEach((b) => warns.push("Possible methodology break — " + b));
  CC.findBreaks(ys, labels, esc(nameB)).forEach((b) => warns.push("Possible methodology break — " + b));
  if (CC.crossesZero(xs)) warns.push(esc(nameA) + " crosses zero — changes use absolute differences, not percent.");
  if (CC.crossesZero(ys)) warns.push(esc(nameB) + " crosses zero — changes use absolute differences, not percent.");
  $("cc-warnings").innerHTML = warns.map((w) => `<li>${w}</li>`).join("");
  $("cc-warnbox").hidden = !warns.length;

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
  $("cc-verdict").innerHTML = v.map((t) => `<p>${t}</p>`).join("");

  // 3b · regression on changes — the slope is the number someone can act on
  const reg = CC.ols(dx, dy);
  const unitX = CC.crossesZero(xs) ? " units" : "%";
  const unitY = CC.crossesZero(ys) ? " units" : "%";
  if (reg) {
    const rv = [];
    rv.push(`<p class="cc-eq">Δ${esc(nameB)} = ${fmtR(reg.a)} ${reg.b >= 0 ? "+" : "−"} ${Math.abs(reg.b).toFixed(3)} · Δ${esc(nameA)}</p>`);
    rv.push(`<p>A 1${unitX} move in ${esc(nameA)} goes with a <b>${(reg.b >= 0 ? "+" : "") + reg.b.toFixed(2)}${unitY}</b> move in ${esc(nameB)} &mdash; 95% CI [${reg.ciB[0].toFixed(2)}, ${reg.ciB[1].toFixed(2)}], adjusted p = ${fmtP(reg.pAdj)} ${reg.pAdj < 0.05 ? '<span class="cc-sig">(slope distinguishable from zero)</span>' : '<span class="cc-ns">(slope NOT distinguishable from zero — do not quote it as an effect)</span>'}.</p>`);
    rv.push(`<p>The regression explains ${(reg.r2 * 100).toFixed(0)}% of the variance in the changes; the other ${(100 - reg.r2 * 100).toFixed(0)}% is something this pair does not capture.</p>`);
    if (reg.dw < 1.2 || reg.dw > 2.8)
      rv.push(`<p>Durbin&ndash;Watson = ${reg.dw.toFixed(2)} &mdash; the residuals are ${reg.dw < 1.2 ? "positively" : "negatively"} autocorrelated, so even these adjusted errors are on the optimistic side. Whatever the model misses, it misses persistently.</p>`);
    $("cc-regbody").innerHTML = rv.join("");
    $("cc-regbox").hidden = false;
  } else $("cc-regbox").hidden = true;

  // 3c · confounder control: does X survive holding Z constant?
  if (zs && reg) {
    const dz = CC.change(zs, h);
    const m = CC.ols2(dx, dz, dy), pr = CC.partialR(dx, dy, dz);
    if (m && pr !== null) {
      const collapse = Math.abs(m.bx) < Math.abs(reg.b) * 0.5 || m.p >= 0.05;
      $("cc-ctrlbody").innerHTML =
        `<p>Alone, the ${esc(nameA)} slope is <b>${reg.b.toFixed(3)}</b>. Holding ${esc(nameZ)} constant it becomes <b>${m.bx.toFixed(3)}</b> (p = ${fmtP(m.p)}); the partial correlation is ${fmtR(pr)} against a raw ${fmtR(chg ? chg.r : 0)}.</p>` +
        (collapse
          ? `<p><b>The ${esc(nameA)} effect does not survive the control.</b> Most of what it appeared to explain is carried by ${esc(nameZ)} — treat ${esc(nameA)} as a proxy until something rules that out.</p>`
          : `<p>The ${esc(nameA)} effect survives the control &mdash; whatever ${esc(nameZ)} contributes, it does not account for this relationship.</p>`);
      $("cc-ctrlbox").hidden = false;
    } else {
      $("cc-ctrlbody").innerHTML = `<p>${esc(nameZ)} is collinear with ${esc(nameA)} — the control cannot be separated.</p>`;
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
  ["cc-colx", "cc-coly", "cc-colz"].forEach((id) =>
    $(id).addEventListener("change", () => { if (!$("cc-results").hidden) run(); }));
  $("cc-demo").addEventListener("click", () => { $("cc-input").value = demoData(); $("cc-yoy").checked = false; run(); });
  $("cc-file").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => { $("cc-input").value = rd.result; run(); };
    rd.readAsText(f);
  });
  let t; window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => { if (!$("cc-results").hidden) run(); }, 150); });
  if (location.search.indexOf("demo") >= 0) {
    $("cc-input").value = demoData(); $("cc-yoy").checked = false; run();
    window.scrollTo(0, $("cc-results").offsetTop - 10);   // land on the verdict
  }
});
