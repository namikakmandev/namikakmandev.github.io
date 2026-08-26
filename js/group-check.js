/* Group & Category Check — statistics engine.
   Group comparison, crosstabs and distributions with the same discipline as
   the correlation checker: effect sizes are mandatory, assumption checks run
   themselves, and every formula ships with a shuffle-based alternative.
   No dependencies beyond the primitives in correlation-check.js (CC). */

"use strict";

const GC_CC = typeof module !== "undefined" && module.exports
  ? require("./correlation-check.js")
  : window.CC;

/* ------------------------------ distributions ------------------------------ */

// Regularised lower incomplete gamma P(a, x): series for x < a+1, continued
// fraction otherwise (Numerical Recipes construction).
function gammaincP(a, x) {
  if (x <= 0) return 0;
  if (x < a + 1) {
    let sum = 1 / a, term = sum;
    for (let k = 1; k < 300; k++) {
      term *= x / (a + k);
      sum += term;
      if (Math.abs(term) < Math.abs(sum) * 1e-12) break;
    }
    return sum * Math.exp(-x + a * Math.log(x) - lgamma(a));
  }
  let b = x + 1 - a, c = 1e300, d = 1 / b, f = d;
  for (let k = 1; k < 300; k++) {
    const an = -k * (k - a);
    b += 2;
    d = an * d + b; if (Math.abs(d) < 1e-300) d = 1e-300;
    c = b + an / c; if (Math.abs(c) < 1e-300) c = 1e-300;
    d = 1 / d;
    const del = d * c;
    f *= del;
    if (Math.abs(del - 1) < 1e-12) break;
  }
  return 1 - Math.exp(-x + a * Math.log(x) - lgamma(a)) * f;
}

function lgamma(z) {
  // Lanczos approximation
  const g = [676.5203681218851, -1259.1392167224028, 771.32342877765313,
             -176.61502916214059, 12.507343278686905, -0.13857109526572012,
             9.9843695780195716e-6, 1.5056327351493116e-7];
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - lgamma(1 - z);
  z -= 1;
  let x = 0.99999999999980993;
  for (let i = 0; i < g.length; i++) x += g[i] / (z + i + 1);
  const t = z + g.length - 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}

// Upper-tail p for a chi-square statistic.
function chi2P(x, df) {
  if (x <= 0) return 1;
  return Math.max(0, Math.min(1, 1 - gammaincP(df / 2, x / 2)));
}

// Upper-tail p for an F statistic, through the incomplete beta already
// validated in the correlation engine (via its t p-value at df2=∞ edge the
// same machinery applies).
function fP(f, df1, df2) {
  if (f <= 0) return 1;
  // P(F > f) = I_{df2/(df2+df1*f)}(df2/2, df1/2)
  return betaI(df2 / (df2 + df1 * f), df2 / 2, df1 / 2);
}

// Regularised incomplete beta, continued fraction (mirrors the correlation
// engine's internal implementation, re-stated here so this file stands alone
// in Node tests as well).
function betaI(x, a, b) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const lbeta = lgamma(a) + lgamma(b) - lgamma(a + b);
  const front = Math.exp(Math.log(x) * a + Math.log(1 - x) * b - lbeta) / a;
  if (x > (a + 1) / (a + b + 2)) return 1 - betaI(1 - x, b, a);
  let f = 1, c = 1, d = 0;
  for (let i = 0; i <= 200; i++) {
    const m = Math.floor(i / 2);
    let num;
    if (i === 0) num = 1;
    else if (i % 2 === 0) num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m));
    else num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1));
    d = 1 + num * d; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
    c = 1 + num / c; if (Math.abs(c) < 1e-30) c = 1e-30;
    f *= c * d;
    if (Math.abs(1 - c * d) < 1e-10) break;
  }
  return front * (f - 1);
}

// Standard normal two-sided p from |z|.
function zP(z) {
  z = Math.abs(z);
  // Abramowitz-Stegun 7.1.26 erf approximation
  const t = 1 / (1 + 0.3275911 * (z / Math.SQRT2));
  const erf = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                    - 0.284496736) * t + 0.254829592) * t * Math.exp(-z * z / 2);
  return Math.max(0, Math.min(1, 1 - erf));
}

/* ------------------------------- descriptives ------------------------------ */

function describeSeries(v) {
  const n = v.length;
  if (!n) return null;
  const sorted = v.slice().sort((a, b) => a - b);
  const mean = v.reduce((a, b) => a + b, 0) / n;
  const median = n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
  let m2 = 0, m3 = 0, m4 = 0;
  for (const x of v) {
    const d = x - mean;
    m2 += d * d; m3 += d * d * d; m4 += d * d * d * d;
  }
  const varr = m2 / (n - 1 || 1);
  const sd = Math.sqrt(varr);
  const skew = n > 2 && sd > 0 ? (m3 / n) / Math.pow(m2 / n, 1.5) : 0;
  const kurt = n > 3 && sd > 0 ? (m4 / n) / Math.pow(m2 / n, 2) - 3 : 0;
  const absdev = sorted.map((x) => Math.abs(x - median)).sort((a, b) => a - b);
  const mad = n % 2 ? absdev[(n - 1) / 2] : (absdev[n / 2 - 1] + absdev[n / 2]) / 2;
  // outliers by the MAD rule (robust: the outliers cannot hide the threshold)
  const cut = 1.4826 * mad * 3.5;
  const outliers = mad > 0
    ? v.map((x, i) => [x, i]).filter(([x]) => Math.abs(x - median) > cut)
    : [];
  // Jarque-Bera normality
  const jb = n > 7 ? (n / 6) * (skew * skew + (kurt * kurt) / 4) : null;
  return { n, mean, median, sd, mad, skew, kurt,
           min: sorted[0], max: sorted[n - 1],
           q1: quantile(sorted, 0.25), q3: quantile(sorted, 0.75),
           outliers, jb, jbP: jb !== null ? chi2P(jb, 2) : null };
}

function quantile(sorted, q) {
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

/* ------------------------------- two groups -------------------------------- */

// Welch's t-test is the default on purpose: it does not assume equal
// variances, and costs nearly nothing when they happen to be equal.
function welch(a, b) {
  const n1 = a.length, n2 = b.length;
  if (n1 < 3 || n2 < 3) return null;
  const d1 = describeSeries(a), d2 = describeSeries(b);
  const v1 = d1.sd * d1.sd / n1, v2 = d2.sd * d2.sd / n2;
  const se = Math.sqrt(v1 + v2);
  if (se === 0) return null;
  const t = (d1.mean - d2.mean) / se;
  const df = (v1 + v2) ** 2 / (v1 * v1 / (n1 - 1) + v2 * v2 / (n2 - 1));
  const p = GC_CC.tPValue(t, df);
  // Hedges' g: Cohen's d with the small-sample bias correction applied,
  // because reporting the biased number when the fix is one multiply is
  // exactly the kind of quiet flattery this tool exists to stop.
  const sp = Math.sqrt(((n1 - 1) * d1.sd * d1.sd + (n2 - 1) * d2.sd * d2.sd) / (n1 + n2 - 2));
  const d = sp > 0 ? (d1.mean - d2.mean) / sp : 0;
  const g = d * (1 - 3 / (4 * (n1 + n2) - 9));
  const seG = Math.sqrt((n1 + n2) / (n1 * n2) + g * g / (2 * (n1 + n2)));
  return { t, df, p, meanDiff: d1.mean - d2.mean,
           ciDiff: [d1.mean - d2.mean - 1.96 * se, d1.mean - d2.mean + 1.96 * se],
           g, ciG: [g - 1.96 * seG, g + 1.96 * seG],
           varRatio: Math.max(d1.sd, d2.sd) ** 2 / Math.max(1e-300, Math.min(d1.sd, d2.sd) ** 2),
           d1, d2 };
}

// Mann-Whitney U with tie-corrected normal approximation, plus the
// rank-biserial effect size (the probability-of-superiority translation).
function mannWhitney(a, b) {
  const n1 = a.length, n2 = b.length;
  if (n1 < 3 || n2 < 3) return null;
  const all = a.map((v) => [v, 0]).concat(b.map((v) => [v, 1]))
    .sort((x, y) => x[0] - y[0]);
  const ranks = new Array(all.length);
  let tieSum = 0;
  for (let i = 0; i < all.length;) {
    let j = i;
    while (j + 1 < all.length && all[j + 1][0] === all[i][0]) j++;
    const avg = (i + j) / 2 + 1, tie = j - i + 1;
    if (tie > 1) tieSum += tie * tie * tie - tie;
    for (let k = i; k <= j; k++) ranks[k] = avg;
    i = j + 1;
  }
  let r1 = 0;
  for (let i = 0; i < all.length; i++) if (all[i][1] === 0) r1 += ranks[i];
  const u1 = r1 - n1 * (n1 + 1) / 2;
  const u = Math.min(u1, n1 * n2 - u1);
  const mu = n1 * n2 / 2;
  const N = n1 + n2;
  const sig = Math.sqrt(n1 * n2 / 12 * ((N + 1) - tieSum / (N * (N - 1))));
  if (sig === 0) return null;
  const z = (u1 - mu) / sig;
  return { u, z, p: zP(z), rankBiserial: 1 - 2 * (n1 * n2 - u1) / (n1 * n2),
           probSuperiority: u1 / (n1 * n2) };
}

// Permutation test on the difference in means: shuffle the group labels,
// count how often luck matches the observed gap. Deterministic seed.
function permMeanDiff(a, b, iters) {
  iters = iters || 4000;
  const obs = Math.abs(a.reduce((x, y) => x + y, 0) / a.length -
                       b.reduce((x, y) => x + y, 0) / b.length);
  const pool = a.concat(b);
  let seed = 24601, hits = 0;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let it = 0; it < iters; it++) {
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    let s1 = 0;
    for (let i = 0; i < a.length; i++) s1 += pool[i];
    let s2 = 0;
    for (let i = a.length; i < pool.length; i++) s2 += pool[i];
    if (Math.abs(s1 / a.length - s2 / b.length) >= obs) hits++;
  }
  return (hits + 1) / (iters + 1);
}

/* ------------------------------ many groups -------------------------------- */

// Classic one-way ANOVA F plus omega-squared, the less-flattering cousin of
// eta-squared (eta rewards adding groups; omega does not).
function anova(groups) {
  const k = groups.length;
  if (k < 3 || groups.some((g) => g.length < 3)) return null;
  const all = groups.flat();
  const N = all.length;
  const grand = all.reduce((a, b) => a + b, 0) / N;
  let ssb = 0, ssw = 0;
  for (const g of groups) {
    const m = g.reduce((a, b) => a + b, 0) / g.length;
    ssb += g.length * (m - grand) ** 2;
    for (const x of g) ssw += (x - m) ** 2;
  }
  const df1 = k - 1, df2 = N - k;
  if (ssw === 0) return null;
  const F = (ssb / df1) / (ssw / df2);
  const msw = ssw / df2;
  const omega2 = Math.max(0, (ssb - df1 * msw) / (ssb + ssw + msw));
  const eta2 = ssb / (ssb + ssw);
  // variance homogeneity flag: largest to smallest group SD
  const sds = groups.map((g) => describeSeries(g).sd);
  return { F, df1, df2, p: fP(F, df1, df2), eta2, omega2,
           varRatio: Math.max(...sds) ** 2 / Math.max(1e-300, Math.min(...sds) ** 2),
           pairs: k * (k - 1) / 2 };
}

// Kruskal-Wallis H with tie correction: the rank-based alternative that does
// not care about normality or outliers.
function kruskal(groups) {
  const k = groups.length;
  if (k < 3 || groups.some((g) => g.length < 3)) return null;
  const all = [];
  groups.forEach((g, gi) => g.forEach((v) => all.push([v, gi])));
  all.sort((a, b) => a[0] - b[0]);
  const N = all.length;
  const ranks = new Array(N);
  let tieSum = 0;
  for (let i = 0; i < N;) {
    let j = i;
    while (j + 1 < N && all[j + 1][0] === all[i][0]) j++;
    const avg = (i + j) / 2 + 1, tie = j - i + 1;
    if (tie > 1) tieSum += tie * tie * tie - tie;
    for (let m = i; m <= j; m++) ranks[m] = avg;
    i = j + 1;
  }
  const rsum = new Array(k).fill(0);
  for (let i = 0; i < N; i++) rsum[all[i][1]] += ranks[i];
  let H = 0;
  for (let gi = 0; gi < k; gi++) H += rsum[gi] ** 2 / groups[gi].length;
  H = 12 / (N * (N + 1)) * H - 3 * (N + 1);
  const corr = 1 - tieSum / (N * N * N - N);
  if (corr > 0) H /= corr;
  return { H, df: k - 1, p: chi2P(H, k - 1),
           epsilon2: Math.max(0, (H - k + 1) / (N - k)) };
}

// Permutation F: shuffle all labels, recompute F.
function permF(groups, iters) {
  iters = iters || 3000;
  const base = anova(groups);
  if (!base) return null;
  const sizes = groups.map((g) => g.length);
  const pool = groups.flat();
  let seed = 31415, hits = 0;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let it = 0; it < iters; it++) {
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    const gs = [];
    let off = 0;
    for (const s of sizes) { gs.push(pool.slice(off, off + s)); off += s; }
    const r = anova(gs);
    if (r && r.F >= base.F) hits++;
  }
  return (hits + 1) / (iters + 1);
}

/* -------------------------------- crosstab --------------------------------- */

// Chi-square test of independence with bias-corrected Cramér's V and the
// expected-count check that decides whether the formula can be trusted.
function chiSquare(rowsLabels, colsLabels, counts) {
  const R = rowsLabels.length, C = colsLabels.length;
  const rowT = counts.map((r) => r.reduce((a, b) => a + b, 0));
  const colT = colsLabels.map((_, j) => counts.reduce((a, r) => a + r[j], 0));
  const N = rowT.reduce((a, b) => a + b, 0);
  if (N === 0 || R < 2 || C < 2) return null;
  let chi2 = 0, lowCells = 0;
  const expected = counts.map((row, i) => row.map((_, j) => {
    const e = rowT[i] * colT[j] / N;
    if (e < 5) lowCells++;
    if (e > 0) chi2 += (counts[i][j] - e) ** 2 / e;
    return e;
  }));
  const df = (R - 1) * (C - 1);
  const kmin = Math.min(R, C);
  const v = Math.sqrt(chi2 / (N * (kmin - 1)));
  // Bergsma bias correction: small tables on small N flatter V upward
  const phi2 = Math.max(0, chi2 / N - (R - 1) * (C - 1) / (N - 1));
  const rAdj = R - (R - 1) ** 2 / (N - 1), cAdj = C - (C - 1) ** 2 / (N - 1);
  const vCorr = Math.sqrt(phi2 / Math.max(1e-300, Math.min(rAdj - 1, cAdj - 1)));
  return { chi2, df, p: chi2P(chi2, df), N, v, vCorr,
           expected, lowCells, cells: R * C,
           lowShare: lowCells / (R * C) };
}

// Permutation chi-square: shuffle one categorical column against the other.
function permChi2(aVals, bVals, iters) {
  iters = iters || 3000;
  const build = (av, bv) => {
    const ra = [...new Set(av)], rb = [...new Set(bv)];
    const idxA = new Map(ra.map((v, i) => [v, i]));
    const idxB = new Map(rb.map((v, i) => [v, i]));
    const m = ra.map(() => rb.map(() => 0));
    for (let i = 0; i < av.length; i++) m[idxA.get(av[i])][idxB.get(bv[i])]++;
    return chiSquare(ra, rb, m);
  };
  const base = build(aVals, bVals);
  if (!base) return null;
  const bv = bVals.slice();
  let seed = 27183, hits = 0;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let it = 0; it < iters; it++) {
    for (let i = bv.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [bv[i], bv[j]] = [bv[j], bv[i]];
    }
    const r = build(aVals, bv);
    if (r && r.chi2 >= base.chi2) hits++;
  }
  return (hits + 1) / (iters + 1);
}

const GC_API = { gammaincP, chi2P, fP, betaI, zP, lgamma,
                 describeSeries, quantile,
                 welch, mannWhitney, permMeanDiff,
                 anova, kruskal, permF,
                 chiSquare, permChi2 };
if (typeof module !== "undefined" && module.exports) module.exports = GC_API;
if (typeof window !== "undefined") window.GC = GC_API;
