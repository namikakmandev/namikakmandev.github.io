/* Group & Category Check — page logic.
   Parsing, shape detection, verdict prose and charts. All statistics live in
   group-check.js (window.GC); shared primitives in correlation-check.js. */

"use strict";

const GCU = window.GC;
const $g = (id) => document.getElementById(id);
const escG = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmtN = (v, d) => Number(v).toLocaleString("en-US", { maximumFractionDigits: d ?? 3 });
const fmtPg = (p) => p < 1e-4 ? p.toExponential(1) : p.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");

/* ------------------------------- parsing ----------------------------------- */

function parseGrid(text) {
  const lines = text.trim().split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length < 4) return { error: "Need at least a header row and 3 data rows." };
  const delim = lines[0].includes("\t") ? "\t" : lines[0].includes(";") ? ";" : ",";
  const grid = lines.map((l) => l.split(delim).map((c) => c.trim()));
  const width = Math.min(...grid.map((r) => r.length));
  if (width < 1) return { error: "Could not detect columns." };
  const isNum = (v) => v !== "" && isFinite(Number(v.replace?.(/%$/, "") ?? v));
  const body0 = grid.slice(1);
  const hasHeader = grid[0].some((c) => !isNum(c));
  const header = hasHeader ? grid[0] : grid[0].map((_, i) => "column " + (i + 1));
  const body = hasHeader ? body0 : grid;
  const cols = [];
  for (let j = 0; j < width; j++) {
    const raw = body.map((r) => r[j]);
    const filled = raw.filter((v) => v !== "");
    const numeric = filled.length > 0 && filled.every(isNum);
    cols.push({ name: header[j], raw, numeric,
                nums: numeric ? raw.map((v) => v === "" ? null : Number(v.replace(/%$/, ""))) : null });
  }
  return { cols, nRows: body.length };
}

// Decide what analysis the data supports.
function detectShape(cols) {
  const numeric = cols.filter((c) => c.numeric);
  const categorical = cols.filter((c) => !c.numeric);
  if (cols.length === 1 && numeric.length === 1) return "distribution";
  if (categorical.length >= 1 && numeric.length >= 1) {
    const cat = categorical[0];
    const levels = new Set(cat.raw.filter((v) => v !== "")).size;
    if (levels >= 2 && levels <= 12) return "groups-long";
  }
  if (categorical.length >= 2) return "crosstab";
  if (numeric.length >= 2) {
    // wide: every numeric column is a group — but a first column of years
    // (all 4-digit, increasing) is a label column, not a group
    return "groups-wide";
  }
  if (numeric.length === 1) return "distribution";
  return null;
}

// Extract group arrays for either format.
function extractGroups(cols, shape) {
  if (shape === "groups-long") {
    const cat = cols.find((c) => !c.numeric);
    const num = cols.find((c) => c.numeric);
    const map = new Map();
    cat.raw.forEach((g, i) => {
      const v = num.nums[i];
      if (g === "" || v === null || !isFinite(v)) return;
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(v);
    });
    return { names: [...map.keys()], groups: [...map.values()],
             valueName: num.name, groupName: cat.name };
  }
  const numeric = cols.filter((c) => c.numeric);
  return { names: numeric.map((c) => c.name),
           groups: numeric.map((c) => c.nums.filter((v) => v !== null && isFinite(v))),
           valueName: "value", groupName: "column" };
}

/* --------------------------------- prose ----------------------------------- */

function gLabel(g) {
  const a = Math.abs(g);
  if (a < 0.2) return "negligible";
  if (a < 0.5) return "small";
  if (a < 0.8) return "medium";
  return "large";
}

function checkAssumptions(names, groups) {
  const warns = [];
  groups.forEach((g, i) => {
    const d = GCU.describeSeries(g);
    if (d.jbP !== null && d.jbP < 0.01)
      warns.push(`${escG(names[i])} is far from normal (skew ${d.skew.toFixed(1)}, ` +
        `excess kurtosis ${d.kurt.toFixed(1)}) — read the rank-based line, not the t-test.`);
    if (d.outliers.length)
      warns.push(`${escG(names[i])} has ${d.outliers.length} outlier${d.outliers.length > 1 ? "s" : ""} ` +
        `by the MAD rule (e.g. ${fmtN(d.outliers[0][0])}) — the mean and the t-test follow outliers; the median and ranks do not.`);
    if (g.length < 10)
      warns.push(`${escG(names[i])} has only ${g.length} observations — every number below is fragile.`);
  });
  return warns;
}

/* ------------------------------- rendering --------------------------------- */

const gLedger = { count: 0 };

function descTable(names, groups) {
  const rows = names.map((nm, i) => {
    const d = GCU.describeSeries(groups[i]);
    return `<tr><th scope="row">${escG(nm)}</th><td>${d.n}</td><td>${fmtN(d.mean)}</td>` +
      `<td>${fmtN(d.median)}</td><td>${fmtN(d.sd)}</td><td>${fmtN(d.min)}</td><td>${fmtN(d.max)}</td>` +
      `<td>${d.outliers.length || "—"}</td></tr>`;
  }).join("");
  return `<div class="cc-table-wrap"><table class="cc-table"><thead><tr>` +
    `<th>group</th><th>n</th><th>mean</th><th>median</th><th>SD</th><th>min</th><th>max</th><th>outliers</th>` +
    `</tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderTwoGroups(names, groups, out) {
  const [a, b] = groups;
  const w = GCU.welch(a, b);
  const mw = GCU.mannWhitney(a, b);
  if (!w || !mw) { out.push("<p>Too few observations per group (need at least 3 each).</p>"); return; }
  const pp = GCU.permMeanDiff(a, b);

  out.push(`<h3>${escG(names[0])} vs ${escG(names[1])}</h3>`);
  out.push(descTable(names, groups));
  out.push(`<p>Difference in means: <b>${fmtN(w.meanDiff)}</b>, 95% CI [${fmtN(w.ciDiff[0])}, ${fmtN(w.ciDiff[1])}]. ` +
    `Welch's t = ${w.t.toFixed(2)} (df ${w.df.toFixed(1)}), p = <b>${fmtPg(w.p)}</b>. ` +
    `Welch is the default here because it does not assume equal spread.</p>`);
  out.push(`<p>Effect size: Hedges' g = <b>${w.g.toFixed(2)}</b>, 95% CI [${w.ciG[0].toFixed(2)}, ${w.ciG[1].toFixed(2)}] — ` +
    `a <b>${gLabel(w.g)}</b> effect${Math.abs(w.g) >= 0.2 && w.ciG[0] * w.ciG[1] < 0 ? ", but the interval includes zero, so the size is not established" : ""}. ` +
    `A p-value says whether the difference is detectable; g says whether it is big enough to matter. Report both or neither.</p>`);
  out.push(`<p>Rank-based check (Mann&ndash;Whitney): p = ${fmtPg(mw.p)}; probability that a random ` +
    `${escG(names[0])} value exceeds a random ${escG(names[1])} value: <b>${(mw.probSuperiority * 100).toFixed(0)}%</b> ` +
    `(50% would mean no separation). This line ignores outliers and distribution shape.</p>`);
  out.push(`<p>Assumption-free check: shuffling the group labels 4,000 times, a mean gap this large ` +
    `appears by luck with probability ${fmtPg(pp)}.</p>`);
  if (w.varRatio > 4)
    out.push(`<p>The two spreads differ by ${w.varRatio.toFixed(1)}&times; in variance — the difference in ` +
      `<i>variability</i> may matter as much as the difference in means.</p>`);

  const agree = (w.p < 0.05) === (mw.p < 0.05) && (w.p < 0.05) === (pp < 0.05);
  out.push(`<p><b>Verdict:</b> ${
    agree && w.p < 0.05 ? `all three tests agree the difference is real, and it is ${gLabel(w.g)} (g = ${w.g.toFixed(2)}).`
    : agree ? "no detectable difference by any of the three tests. An honest null — which is still a finding."
    : "the tests disagree — usually outliers or skew. Trust the rank-based and shuffle lines over the t-test."}</p>`);
}

function renderManyGroups(names, groups, out) {
  const an = GCU.anova(groups);
  const kw = GCU.kruskal(groups);
  if (!an || !kw) { out.push("<p>Each group needs at least 3 observations.</p>"); return; }
  const pf = GCU.permF(groups);
  out.push(`<h3>${names.length} groups compared</h3>`);
  out.push(descTable(names, groups));
  out.push(`<p>One-way ANOVA: F(${an.df1}, ${an.df2}) = ${an.F.toFixed(2)}, p = <b>${fmtPg(an.p)}</b>. ` +
    `Effect size &omega;&sup2; = <b>${an.omega2.toFixed(2)}</b> — the share of all variation explained by group membership ` +
    `(&omega;&sup2; rather than &eta;&sup2; = ${an.eta2.toFixed(2)}, which flatters small samples).</p>`);
  out.push(`<p>Rank-based check (Kruskal&ndash;Wallis): H = ${kw.H.toFixed(2)}, p = ${fmtPg(kw.p)}.</p>`);
  if (pf !== null)
    out.push(`<p>Assumption-free check: shuffling all labels 3,000 times, an F this large appears ` +
      `by luck with probability ${fmtPg(pf)}.</p>`);
  if (an.varRatio > 4)
    out.push(`<p>Group variances differ by ${an.varRatio.toFixed(1)}&times; — the classic F assumes they are equal, ` +
      `so weight the rank-based and shuffle lines.</p>`);
  out.push(`<p><b>A significant ANOVA only says "not all groups are equal" — it does not say which.</b> ` +
    `Comparing all pairs is ${an.pairs} tests, so any pairwise p must clear ` +
    `${(0.05 / an.pairs).toPrecision(2)}, not 0.05.</p>`);
  out.push(`<p><b>Verdict:</b> ${an.p < 0.05 && kw.p < 0.05
    ? `group membership matters — it explains ${(an.omega2 * 100).toFixed(0)}% of the variation.`
    : an.p >= 0.05 && kw.p >= 0.05
    ? "no detectable difference between the groups by either test."
    : "the parametric and rank tests disagree — inspect the outlier and skew warnings above."}</p>`);
}

function renderCrosstab(cols, out) {
  const cats = cols.filter((c) => !c.numeric);
  const a = cats[0], b = cats[1];
  const keep = a.raw.map((v, i) => [v, b.raw[i]]).filter(([x, y]) => x !== "" && y !== "");
  const av = keep.map((r) => r[0]), bv = keep.map((r) => r[1]);
  const ra = [...new Set(av)], rb = [...new Set(bv)];
  if (ra.length < 2 || rb.length < 2) { out.push("<p>Both columns need at least two categories.</p>"); return; }
  if (ra.length > 20 || rb.length > 20) { out.push("<p>Too many categories (over 20) — this looks like free text, not categories.</p>"); return; }
  const counts = ra.map((x) => rb.map((y) => keep.filter(([p, q]) => p === x && q === y).length));
  const cs = GCU.chiSquare(ra, rb, counts);
  if (!cs) { out.push("<p>Not enough data for a crosstab.</p>"); return; }
  const pp = GCU.permChi2(av, bv);

  out.push(`<h3>${escG(a.name)} &times; ${escG(b.name)}</h3>`);
  const head = `<tr><th></th>${rb.map((y) => `<th>${escG(y)}</th>`).join("")}</tr>`;
  const rows = ra.map((x, i) =>
    `<tr><th scope="row">${escG(x)}</th>` + rb.map((_, j) =>
      `<td>${counts[i][j]} <span class="cc-note">(${cs.expected[i][j].toFixed(1)})</span></td>`).join("") + "</tr>").join("");
  out.push(`<div class="cc-table-wrap"><table class="cc-table"><thead>${head}</thead><tbody>${rows}</tbody></table></div>`);
  out.push(`<p class="cc-note">Each cell: observed count (expected under independence).</p>`);
  out.push(`<p>&chi;&sup2;(${cs.df}) = ${cs.chi2.toFixed(2)}, p = <b>${fmtPg(cs.p)}</b>, n = ${cs.N}.</p>`);
  out.push(`<p>Effect size: bias-corrected Cram&eacute;r's V = <b>${cs.vCorr.toFixed(2)}</b> ` +
    `(uncorrected ${cs.v.toFixed(2)}). On a 0&ndash;1 scale: below 0.1 is trivial, 0.1&ndash;0.3 weak, ` +
    `0.3&ndash;0.5 moderate, above 0.5 strong. A tiny p with a tiny V means "definitely a relationship, ` +
    `definitely too weak to matter" — common at large n.</p>`);
  if (cs.lowShare > 0.2)
    out.push(`<p>${cs.lowCells} of ${cs.cells} cells expect fewer than 5 observations — the &chi;&sup2; formula ` +
      `is unreliable here. <b>Use the shuffle line below as the p-value.</b></p>`);
  if (pp !== null)
    out.push(`<p>Assumption-free check: shuffling one column 3,000 times, a &chi;&sup2; this large appears ` +
      `by luck with probability ${fmtPg(pp)}.</p>`);
  out.push(`<p><b>Verdict:</b> ${(cs.lowShare > 0.2 ? pp : cs.p) < 0.05
    ? `the two variables are associated (V = ${cs.vCorr.toFixed(2)}, ${cs.vCorr < 0.1 ? "trivial" : cs.vCorr < 0.3 ? "weak" : cs.vCorr < 0.5 ? "moderate" : "strong"}).`
    : "no detectable association."}</p>`);
}

function renderDistribution(col, out) {
  const v = col.nums.filter((x) => x !== null && isFinite(x));
  const d = GCU.describeSeries(v);
  if (!d || d.n < 8) { out.push("<p>Need at least 8 values.</p>"); return; }
  out.push(`<h3>${escG(col.name)} — distribution</h3>`);
  out.push(`<div class="cc-table-wrap"><table class="cc-table"><tbody>` +
    `<tr><th>n</th><td>${d.n}</td><th>mean</th><td>${fmtN(d.mean)}</td><th>median</th><td>${fmtN(d.median)}</td></tr>` +
    `<tr><th>SD</th><td>${fmtN(d.sd)}</td><th>MAD</th><td>${fmtN(d.mad)}</td><th>IQR</th><td>${fmtN(d.q1)} &ndash; ${fmtN(d.q3)}</td></tr>` +
    `<tr><th>min</th><td>${fmtN(d.min)}</td><th>max</th><td>${fmtN(d.max)}</td><th>skew / kurt</th><td>${d.skew.toFixed(2)} / ${d.kurt.toFixed(2)}</td></tr>` +
    `</tbody></table></div>`);
  // Normalised by the robust MAD scale, not the SD: the outliers inflate the
  // SD, which would let them hide the very distortion this check looks for.
  const robustScale = 1.4826 * d.mad;
  const meanShift = robustScale > 0 ? Math.abs(d.mean - d.median) / robustScale : 0;
  if (meanShift > 0.5)
    out.push(`<p>The mean (${fmtN(d.mean)}) and the median (${fmtN(d.median)}) disagree by ` +
      `${meanShift.toFixed(1)}&times; the robust spread — the distribution is skewed or outlier-driven, ` +
      `and <b>the mean is the wrong summary for it</b>. Quote the median.</p>`);
  if (d.outliers.length)
    out.push(`<p>${d.outliers.length} outlier${d.outliers.length > 1 ? "s" : ""} by the MAD rule: ` +
      d.outliers.slice(0, 6).map(([x]) => fmtN(x)).join(", ") + (d.outliers.length > 6 ? ", …" : "") +
      `. Check whether they are data errors before they steer any average.</p>`);
  if (d.jbP !== null)
    out.push(`<p>Normality (Jarque&ndash;Bera): p = ${fmtPg(d.jbP)} — ${d.jbP < 0.05
      ? "not normal. Methods that assume normality (t-tests on small samples, control charts, &plusmn;2SD rules) will misbehave on this."
      : "consistent with normal, as far as this sample can tell."}</p>`);
}

/* -------------------------------- charts ----------------------------------- */

function fitCanvasG(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth || 600, h = cv.clientHeight || 260;
  cv.width = w * dpr; cv.height = h * dpr;
  const x = cv.getContext("2d");
  x.setTransform(dpr, 0, 0, dpr, 0, 0);
  x.clearRect(0, 0, w, h);
  return [x, w, h];
}

const GCOL = { mark: "#2f9bff", line: "#ff6500", dim: "#5b6472", grid: "rgba(91,100,114,.25)" };

// Strip plot with median bars: shows every observation, so outliers and
// spread differences are visible instead of averaged away.
function drawStrips(cv, names, groups) {
  const [x, W, H] = fitCanvasG(cv);
  const L = 40, R = 12, T = 14, B = 34;
  const all = groups.flat();
  const lo = Math.min(...all), hi = Math.max(...all);
  const py = (v) => T + (1 - (v - lo) / (hi - lo || 1)) * (H - T - B);
  const k = groups.length;
  const cx = (i) => L + ((i + 0.5) / k) * (W - L - R);
  x.font = "11px " + getComputedStyle(document.body).fontFamily;
  let seed = 42;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  groups.forEach((g, i) => {
    const jit = Math.min(28, (W - L - R) / k * 0.3);
    x.fillStyle = GCOL.mark; x.globalAlpha = 0.55;
    for (const v of g) {
      x.beginPath();
      x.arc(cx(i) + (rnd() - 0.5) * 2 * jit, py(v), 3.2, 0, 7);
      x.fill();
    }
    x.globalAlpha = 1;
    const d = GCU.describeSeries(g);
    x.strokeStyle = GCOL.line; x.lineWidth = 2.5;
    x.beginPath(); x.moveTo(cx(i) - jit - 6, py(d.median)); x.lineTo(cx(i) + jit + 6, py(d.median)); x.stroke();
    x.fillStyle = GCOL.dim; x.textAlign = "center";
    x.fillText(String(names[i]).slice(0, 14), cx(i), H - 12);
  });
  x.fillStyle = GCOL.dim; x.textAlign = "left";
  x.fillText(fmtN(hi), 4, T + 8); x.fillText(fmtN(lo), 4, H - B);
}

function drawHistogram(cv, values) {
  const [x, W, H] = fitCanvasG(cv);
  const L = 14, R = 14, T = 12, B = 30;
  const lo = Math.min(...values), hi = Math.max(...values);
  const bins = Math.max(8, Math.min(30, Math.round(Math.sqrt(values.length))));
  const count = new Array(bins).fill(0);
  for (const v of values) {
    let b = Math.floor((v - lo) / (hi - lo || 1) * bins);
    if (b >= bins) b = bins - 1;
    count[b]++;
  }
  const mx = Math.max(...count);
  const bw = (W - L - R) / bins;
  x.fillStyle = GCOL.mark;
  count.forEach((c, i) => {
    const h = (c / mx) * (H - T - B);
    x.fillRect(L + i * bw + 1, H - B - h, bw - 2, h);
  });
  x.font = "11px " + getComputedStyle(document.body).fontFamily;
  x.fillStyle = GCOL.dim; x.textAlign = "left"; x.fillText(fmtN(lo), L, H - 10);
  x.textAlign = "right"; x.fillText(fmtN(hi), W - R, H - 10);
}

/* -------------------------------- pipeline --------------------------------- */

function runG() {
  const parsed = parseGrid($g("gc-input").value);
  const err = $g("gc-error"), res = $g("gc-results");
  err.textContent = ""; res.hidden = true;
  if (parsed.error) { err.textContent = parsed.error; return; }

  const mode = $g("gc-mode").value;
  const shape = mode === "auto" ? detectShape(parsed.cols) : mode;
  if (!shape) { err.textContent = "Could not tell what this data is. Choose an analysis manually."; return; }

  const out = [];
  const chartBox = $g("gc-chart-card");
  chartBox.hidden = true;

  if (shape === "distribution" ||
      (mode === "distribution")) {
    const col = parsed.cols.find((c) => c.numeric);
    if (!col) { err.textContent = "No numeric column found."; return; }
    renderDistribution(col, out);
    const v = col.nums.filter((q) => q !== null && isFinite(q));
    if (v.length >= 8) {
      chartBox.hidden = false;
      $g("gc-chart-cap").textContent = "Histogram — the shape the summary numbers are hiding.";
      requestAnimationFrame(() => drawHistogram($g("gc-chart"), v));
    }
  } else if (shape === "crosstab") {
    if (parsed.cols.filter((c) => !c.numeric).length < 2) {
      err.textContent = "A crosstab needs two categorical columns."; return;
    }
    renderCrosstab(parsed.cols, out);
  } else {
    const gd = extractGroups(parsed.cols, shape);
    if (gd.groups.length < 2) { err.textContent = "Need at least two groups."; return; }
    const warns = checkAssumptions(gd.names, gd.groups);
    if (warns.length)
      out.push(`<div class="cc-input-card"><strong>Before the tests</strong>` +
        warns.map((w) => `<p>${w}</p>`).join("") + "</div>");
    if (gd.groups.length === 2) renderTwoGroups(gd.names, gd.groups, out);
    else renderManyGroups(gd.names, gd.groups, out);
    chartBox.hidden = false;
    $g("gc-chart-cap").textContent =
      "Every observation, with the median bar per group. Spread and outliers stay visible.";
    requestAnimationFrame(() => drawStrips($g("gc-chart"), gd.names, gd.groups));
  }

  gLedger.count++;
  if (gLedger.count > 1)
    out.push(`<p class="cc-note">Check <b>#${gLedger.count}</b> this session. Hunting through comparisons and ` +
      `keeping the best means the honest bar is p &lt; <b>${(0.05 / gLedger.count).toPrecision(2)}</b>, not 0.05.</p>`);

  $g("gc-body").innerHTML = out.join("\n");
  res.hidden = false;
  res.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* --------------------------------- demos ----------------------------------- */

function demoGroups() {
  let seed = 99;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const gauss = () => (rnd() + rnd() + rnd() + rnd() - 2) * 1.7;
  const rows = ["treatment,recovery_days"];
  for (let i = 0; i < 28; i++) rows.push("drug," + (11.1 + gauss()).toFixed(1));
  for (let i = 0; i < 26; i++) rows.push("placebo," + (12.4 + gauss()).toFixed(1));
  $g("gc-input").value = rows.join("\n");
  $g("gc-mode").value = "auto";
  runG();
}

function demoCrosstab() {
  let seed = 7;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const rows = ["region,churned"];
  const spec = [["north", 0.22, 90], ["south", 0.28, 80], ["east", 0.45, 40], ["west", 0.25, 70]];
  for (const [name, rate, n] of spec)
    for (let i = 0; i < n; i++) rows.push(name + "," + (rnd() < rate ? "yes" : "no"));
  $g("gc-input").value = rows.join("\n");
  $g("gc-mode").value = "auto";
  runG();
}

function demoDist() {
  let seed = 13;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const rows = ["invoice_amount"];
  for (let i = 0; i < 60; i++) rows.push((120 + (rnd() + rnd() - 1) * 40).toFixed(0));
  rows.push("2600"); rows.push("1900");            // the two invoices that own the mean
  $g("gc-input").value = rows.join("\n");
  $g("gc-mode").value = "auto";
  runG();
}

/* --------------------------------- report ---------------------------------- */

function buildReportG() {
  const strip = $g("gc-body").textContent.replace(/\s+/g, " ").trim();
  return ["# Group & Category Check — verification report", "",
    "Generated by https://namikakmandev.github.io/group-check.html — all computation in-browser, data never uploaded.",
    "", strip, "", "---",
    "Method: Welch's t (unequal variances assumed by default); Hedges' g with CI; Mann–Whitney with tie correction and probability of superiority; label-shuffle permutation tests; one-way ANOVA with omega-squared; Kruskal–Wallis with tie correction; chi-square with bias-corrected Cramér's V and expected-count checks; MAD outlier rule; Jarque–Bera normality.",
    "Generated: " + new Date().toISOString().slice(0, 10)].join("\n");
}

/* --------------------------------- wiring ---------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  $g("gc-run").addEventListener("click", runG);
  $g("gc-demo-groups").addEventListener("click", demoGroups);
  $g("gc-demo-crosstab").addEventListener("click", demoCrosstab);
  $g("gc-demo-dist").addEventListener("click", demoDist);
  $g("gc-mode").addEventListener("change", () => { if (!$g("gc-results").hidden) runG(); });
  $g("gc-report").addEventListener("click", () => {
    if ($g("gc-results").hidden) runG();
    if ($g("gc-results").hidden) return;
    const md = buildReportG();
    navigator.clipboard && navigator.clipboard.writeText(md).catch(() => {});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
    a.download = "group-check-report.md";
    a.click();
    URL.revokeObjectURL(a.href);
  });
  $g("gc-file").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => { $g("gc-input").value = rd.result; runG(); };
    rd.readAsText(f);
    e.target.value = "";
  });
  if (/[?&]demo\b/.test(location.search)) demoGroups();
});
