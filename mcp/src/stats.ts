/**
 * Statistics and econometrics on plain number arrays. No dependencies, so it
 * runs inside a Worker. Everything here is the textbook estimator; the tool
 * layer adds dates, caveats and interpretation.
 */

// ---------------------------------------------------------------------------
// Special functions and distributions

function lgamma(x: number): number {
  // Lanczos approximation, g=7, n=9
  const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
  if (x < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * x)) - lgamma(1 - x);
  x -= 1;
  let a = c[0];
  const t = x + 7.5;
  for (let i = 1; i < 9; i++) a += c[i] / (x + i);
  return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
}

/** Regularized incomplete beta I_x(a, b), continued fraction (Numerical Recipes). */
export function betaInc(x: number, a: number, b: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * Math.log(x) + b * Math.log(1 - x));
  const cf = (x: number, a: number, b: number) => {
    const MAXIT = 300, EPS = 3e-14, FPMIN = 1e-300;
    const qab = a + b, qap = a + 1, qam = a - 1;
    let c = 1, d = 1 - (qab * x) / qap;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    d = 1 / d;
    let h = d;
    for (let m = 1; m <= MAXIT; m++) {
      const m2 = 2 * m;
      let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
      d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
      c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
      d = 1 / d; h *= d * c;
      aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
      d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
      c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
      d = 1 / d;
      const del = d * c;
      h *= del;
      if (Math.abs(del - 1) < EPS) break;
    }
    return h;
  };
  if (x < (a + 1) / (a + b + 2)) return (bt * cf(x, a, b)) / a;
  return 1 - (bt * cf(1 - x, b, a)) / b;
}

/** Regularized lower incomplete gamma P(a, x). */
export function gammaP(a: number, x: number): number {
  if (x <= 0) return 0;
  if (x < a + 1) {
    let sum = 1 / a, del = sum, ap = a;
    for (let n = 0; n < 500; n++) {
      ap += 1; del *= x / ap; sum += del;
      if (Math.abs(del) < Math.abs(sum) * 3e-14) break;
    }
    return sum * Math.exp(-x + a * Math.log(x) - lgamma(a));
  }
  // continued fraction for Q
  let b = x + 1 - a, c = 1 / 1e-300, d = 1 / b, h = d;
  for (let i = 1; i < 500; i++) {
    const an = -i * (i - a);
    b += 2;
    d = an * d + b; if (Math.abs(d) < 1e-300) d = 1e-300;
    c = b + an / c; if (Math.abs(c) < 1e-300) c = 1e-300;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 3e-14) break;
  }
  return 1 - Math.exp(-x + a * Math.log(x) - lgamma(a)) * h;
}

export function tTwoSidedP(t: number, df: number): number {
  if (!Number.isFinite(t) || df <= 0) return NaN;
  const x = df / (df + t * t);
  return betaInc(x, df / 2, 0.5);
}

export function fUpperP(F: number, d1: number, d2: number): number {
  if (!Number.isFinite(F) || F <= 0) return 1;
  return betaInc(d2 / (d2 + d1 * F), d2 / 2, d1 / 2);
}

export function chi2UpperP(x: number, k: number): number {
  if (!Number.isFinite(x) || x <= 0) return 1;
  return 1 - gammaP(k / 2, x / 2);
}

export function normalCdf(z: number): number {
  // Abramowitz-Stegun 7.1.26 via erfc with ~1e-7 accuracy, adequate for p-values
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989422804014327 * Math.exp((-z * z) / 2);
  const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
  return z >= 0 ? 1 - p : p;
}

// ---------------------------------------------------------------------------
// Basic descriptives

export const mean = (a: number[]) => a.reduce((s, x) => s + x, 0) / a.length;
export const variance = (a: number[], ddof = 1) => { const m = mean(a); return a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - ddof); };
export const sd = (a: number[], ddof = 1) => Math.sqrt(variance(a, ddof));
export function quantile(a: number[], q: number): number {
  const s = [...a].sort((x, y) => x - y);
  const pos = (s.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}
export function skewness(a: number[]): number {
  const m = mean(a), n = a.length, s = sd(a, 0);
  return a.reduce((t, x) => t + ((x - m) / s) ** 3, 0) / n;
}
export function kurtosis(a: number[]): number {
  const m = mean(a), n = a.length, s = sd(a, 0);
  return a.reduce((t, x) => t + ((x - m) / s) ** 4, 0) / n; // raw, 3 = normal
}
export function pearson(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length), mx = mean(x.slice(0, n)), my = mean(y.slice(0, n));
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { const dx = x[i] - mx, dy = y[i] - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : NaN;
}
export function autocorr(a: number[], lag: number): number {
  const n = a.length, m = mean(a);
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) den += (a[i] - m) ** 2;
  for (let i = lag; i < n; i++) num += (a[i] - m) * (a[i - lag] - m);
  return den ? num / den : NaN;
}
export function ljungBox(a: number[], lags: number): { Q: number; p: number; lags: number } {
  const n = a.length;
  let Q = 0;
  for (let k = 1; k <= lags; k++) { const r = autocorr(a, k); Q += (r * r) / (n - k); }
  Q *= n * (n + 2);
  return { Q, p: chi2UpperP(Q, lags), lags };
}
export function jarqueBera(a: number[]): { JB: number; p: number } {
  const n = a.length, S = skewness(a), K = kurtosis(a);
  const JB = (n / 6) * (S * S + ((K - 3) ** 2) / 4);
  return { JB, p: chi2UpperP(JB, 2) };
}
export const diff = (a: number[], d = 1) => a.slice(d).map((x, i) => x - a[i]);

// ---------------------------------------------------------------------------
// Linear algebra (small dense systems)

/** Solve A x = b for symmetric positive definite A by Cholesky. Returns null if singular. */
export function choleskySolve(A: number[][], B: number[][]): number[][] | null {
  const n = A.length;
  const L: number[][] = A.map((r) => r.map(() => 0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j <= i; j++) {
      let s = A[i][j];
      for (let k = 0; k < j; k++) s -= L[i][k] * L[j][k];
      if (i === j) { if (s <= 1e-12 * Math.max(1, Math.abs(A[i][i]))) return null; L[i][i] = Math.sqrt(s); }
      else L[i][j] = s / L[j][j];
    }
  }
  const m = B[0].length;
  const X: number[][] = Array.from({ length: n }, () => new Array<number>(m).fill(0));
  for (let c = 0; c < m; c++) {
    const y = new Array<number>(n).fill(0);
    for (let i = 0; i < n; i++) { let s = B[i][c]; for (let k = 0; k < i; k++) s -= L[i][k] * y[k]; y[i] = s / L[i][i]; }
    for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < n; k++) s -= L[k][i] * X[k][c]; X[i][c] = s / L[i][i]; }
  }
  return X;
}

export function inverse(A: number[][]): number[][] | null {
  const n = A.length;
  const I = A.map((_, i) => A.map((__, j) => (i === j ? 1 : 0)));
  return choleskySolve(A, I);
}

export interface OlsResult {
  n: number; k: number;
  beta: number[]; se: number[]; t: number[]; p: number[];
  resid: number[]; fitted: number[];
  rss: number; tss: number; r2: number; adj_r2: number; sigma: number;
  XtXinv: number[][];
  aic: number; bic: number;
  dw: number;
  F: number | null; F_p: number | null;
}

/** OLS of y on X (rows = observations, columns = regressors; include the constant yourself). */
export function ols(y: number[], X: number[][]): OlsResult {
  const n = y.length, k = X[0].length;
  if (n <= k) throw new Error(`OLS needs more observations (${n}) than regressors (${k})`);
  const XtX: number[][] = Array.from({ length: k }, () => new Array<number>(k).fill(0));
  const Xty: number[][] = Array.from({ length: k }, () => [0]);
  for (let i = 0; i < n; i++) {
    const r = X[i];
    for (let a = 0; a < k; a++) { Xty[a][0] += r[a] * y[i]; for (let b = a; b < k; b++) XtX[a][b] += r[a] * r[b]; }
  }
  for (let a = 0; a < k; a++) for (let b = 0; b < a; b++) XtX[a][b] = XtX[b][a];
  const XtXinv = inverse(XtX);
  if (!XtXinv) throw new Error("Regressors are collinear (X'X singular). Drop one.");
  const beta = XtXinv.map((row) => row.reduce((s, v, j) => s + v * Xty[j][0], 0));
  const fitted = X.map((r) => r.reduce((s, v, j) => s + v * beta[j], 0));
  const resid = y.map((v, i) => v - fitted[i]);
  const rss = resid.reduce((s, e) => s + e * e, 0);
  const my = mean(y);
  const tss = y.reduce((s, v) => s + (v - my) ** 2, 0);
  const df = n - k;
  const sigma2 = rss / df;
  const se = XtXinv.map((row, j) => Math.sqrt(Math.max(sigma2 * row[j], 0)));
  const t = beta.map((b, j) => (se[j] ? b / se[j] : NaN));
  const p = t.map((tv) => tTwoSidedP(tv, df));
  const r2 = tss ? 1 - rss / tss : NaN;
  const adj_r2 = tss ? 1 - ((1 - r2) * (n - 1)) / df : NaN;
  const ll = -(n / 2) * (Math.log(2 * Math.PI) + Math.log(rss / n) + 1);
  let dwn = 0;
  for (let i = 1; i < n; i++) dwn += (resid[i] - resid[i - 1]) ** 2;
  // F-test that all non-constant coefficients are zero, assuming column 0 is the constant when present
  const hasConst = X.every((r) => r[0] === 1);
  const q = hasConst ? k - 1 : k;
  const F = q > 0 && tss ? ((tss - rss) / q) / sigma2 : null;
  return {
    n, k, beta, se, t, p, resid, fitted, rss, tss, r2, adj_r2, sigma: Math.sqrt(sigma2), XtXinv,
    aic: -2 * ll + 2 * k, bic: -2 * ll + k * Math.log(n), dw: rss ? dwn / rss : NaN,
    F, F_p: F !== null ? fUpperP(F, q, df) : null,
  };
}

/** Newey-West HAC standard errors with Bartlett kernel. lag defaults to floor(4 (n/100)^(2/9)). */
export function neweyWest(X: number[][], resid: number[], XtXinv: number[][], lag?: number): { se: number[]; lag: number } {
  const n = X.length, k = X[0].length;
  const L = lag ?? Math.floor(4 * Math.pow(n / 100, 2 / 9));
  const S: number[][] = Array.from({ length: k }, () => new Array<number>(k).fill(0));
  const g = X.map((r, i) => r.map((v) => v * resid[i]));
  // Each lag's contribution g_t g_{t-l}' + g_{t-l} g_t' is symmetric, so only the upper triangle is accumulated.
  for (let l = 0; l <= L; l++) {
    const w = l === 0 ? 1 : 1 - l / (L + 1);
    for (let t = l; t < n; t++) {
      const gt = g[t], gl = g[t - l];
      for (let a = 0; a < k; a++) for (let b = a; b < k; b++) {
        S[a][b] += w * (l === 0 ? gt[a] * gt[b] : gt[a] * gl[b] + gl[a] * gt[b]);
      }
    }
  }
  for (let a = 0; a < k; a++) for (let b = 0; b < a; b++) S[a][b] = S[b][a];
  // V = (X'X)^-1 S (X'X)^-1
  const tmp = XtXinv.map((row) => S[0].map((_, j) => row.reduce((s, v, m) => s + v * S[m][j], 0)));
  const V = tmp.map((row) => XtXinv[0].map((_, j) => row.reduce((s, v, m) => s + v * XtXinv[m][j], 0)));
  return { se: V.map((row, j) => Math.sqrt(Math.max(row[j], 0))), lag: L };
}

// ---------------------------------------------------------------------------
// Unit roots and cointegration

export type AdfSpec = "n" | "c" | "ct";

/** MacKinnon (1991) response-surface critical values for the ADF tau statistic. */
export function adfCritical(spec: AdfSpec, T: number): { "1%": number; "5%": number; "10%": number } {
  const tab: Record<AdfSpec, number[][]> = {
    n: [[-2.5658, -1.960, -10.04], [-1.9393, -0.398, 0], [-1.6156, -0.181, 0]],
    c: [[-3.4336, -5.999, -29.25], [-2.8621, -2.738, -8.36], [-2.5671, -1.438, -4.48]],
    ct: [[-3.9638, -8.353, -47.44], [-3.4126, -4.039, -17.83], [-3.1279, -2.418, -7.58]],
  };
  const f = (r: number[]) => r[0] + r[1] / T + r[2] / (T * T);
  const [a, b, c] = tab[spec];
  return { "1%": f(a), "5%": f(b), "10%": f(c) };
}

/** Engle-Granger residual-based test, two variables, constant in the cointegrating regression (MacKinnon 1991). */
export function egCritical(T: number): { "1%": number; "5%": number; "10%": number } {
  const f = (r: number[]) => r[0] + r[1] / T + r[2] / (T * T);
  return { "1%": f([-3.9001, -10.534, -30.03]), "5%": f([-3.3377, -5.967, -8.98]), "10%": f([-3.0462, -4.069, -5.73]) };
}

export interface AdfResult {
  spec: AdfSpec; lags: number; nobs: number; statistic: number;
  critical: { "1%": number; "5%": number; "10%": number };
  reject_unit_root_at: "1%" | "5%" | "10%" | null;
  regression: { gamma: number; se: number };
}

export function adf(y: number[], spec: AdfSpec = "c", lags: number | "auto" = "auto"): AdfResult {
  const n = y.length;
  if (n < 12) throw new Error(`ADF needs at least 12 observations, got ${n}`);
  const maxLag = lags === "auto" ? Math.min(Math.floor(12 * Math.pow(n / 100, 0.25)), Math.floor((n - 5) / 3)) : lags;
  const dy = diff(y);
  const build = (p: number) => {
    const rows: number[][] = [], target: number[] = [];
    for (let t = p + 1; t < n; t++) {
      const r: number[] = [y[t - 1]];
      if (spec !== "n") r.push(1);
      if (spec === "ct") r.push(t);
      for (let j = 1; j <= p; j++) r.push(dy[t - 1 - j]);
      rows.push(r); target.push(dy[t - 1]);
    }
    return { rows, target };
  };
  let best = { p: 0, aic: Infinity, fit: null as OlsResult | null };
  const candidates = lags === "auto" ? Array.from({ length: maxLag + 1 }, (_, i) => i) : [lags];
  for (const p of candidates) {
    const { rows, target } = build(p);
    if (!rows.length || rows.length <= rows[0].length + 2) continue;
    try {
      const fit = ols(target, rows);
      if (fit.aic < best.aic) best = { p, aic: fit.aic, fit };
    } catch { /* singular at this lag; skip */ }
  }
  if (!best.fit) {
    throw new Error(lags === "auto"
      ? `ADF regression could not be estimated on ${y.length} observations`
      : `ADF with ${lags} lags needs more observations than the ${y.length} given; drop the lag or lengthen the sample`);
  }
  const stat = best.fit.t[0];
  const critical = adfCritical(spec, best.fit.n);
  const reject = stat < critical["1%"] ? "1%" : stat < critical["5%"] ? "5%" : stat < critical["10%"] ? "10%" : null;
  return { spec, lags: best.p, nobs: best.fit.n, statistic: stat, critical, reject_unit_root_at: reject, regression: { gamma: best.fit.beta[0], se: best.fit.se[0] } };
}

export interface EngleGrangerResult {
  beta: number[]; se: number[]; r2: number; residual_adf: AdfResult; critical: { "1%": number; "5%": number; "10%": number };
  cointegrated_at: "1%" | "5%" | "10%" | null;
}

export function engleGranger(y: number[], x: number[]): EngleGrangerResult {
  const X = x.map((v) => [1, v]);
  const fit = ols(y, X);
  const res = adf(fit.resid, "n", "auto");
  const critical = egCritical(fit.n);
  const s = res.statistic;
  const coint = s < critical["1%"] ? "1%" : s < critical["5%"] ? "5%" : s < critical["10%"] ? "10%" : null;
  return { beta: fit.beta, se: fit.se, r2: fit.r2, residual_adf: res, critical, cointegrated_at: coint };
}

// ---------------------------------------------------------------------------
// Granger causality

export interface GrangerResult { lags: number; F: number; p: number; nobs: number; rss_restricted: number; rss_unrestricted: number }

/** Does x Granger-cause y? Restricted: y on own lags. Unrestricted: plus lags of x. */
export function granger(y: number[], x: number[], lags: number): GrangerResult {
  const n = y.length;
  if (n !== x.length) throw new Error("Series must be aligned");
  if (n < 3 * lags + 5) throw new Error(`Too few observations (${n}) for ${lags} lags`);
  const target: number[] = [], Xr: number[][] = [], Xu: number[][] = [];
  for (let t = lags; t < n; t++) {
    const own = [1, ...Array.from({ length: lags }, (_, j) => y[t - 1 - j])];
    const other = Array.from({ length: lags }, (_, j) => x[t - 1 - j]);
    target.push(y[t]); Xr.push(own); Xu.push([...own, ...other]);
  }
  const r = ols(target, Xr), u = ols(target, Xu);
  const dfu = target.length - Xu[0].length;
  const F = ((r.rss - u.rss) / lags) / (u.rss / dfu);
  return { lags, F, p: fUpperP(F, lags, dfu), nobs: target.length, rss_restricted: r.rss, rss_unrestricted: u.rss };
}

// ---------------------------------------------------------------------------
// Cross-correlation, filters, decomposition

/** corr(x_t, y_{t+k}) for k in [-maxLag, maxLag]. Positive k: x leads y. */
export function crossCorrelation(x: number[], y: number[], maxLag: number): Array<{ lag: number; r: number; n: number }> {
  const out: Array<{ lag: number; r: number; n: number }> = [];
  for (let k = -maxLag; k <= maxLag; k++) {
    const xs: number[] = [], ys: number[] = [];
    for (let t = 0; t < x.length; t++) {
      const j = t + k;
      if (j >= 0 && j < y.length) { xs.push(x[t]); ys.push(y[j]); }
    }
    out.push({ lag: k, r: xs.length > 3 ? pearson(xs, ys) : NaN, n: xs.length });
  }
  return out;
}

/** Hodrick-Prescott filter, banded solve of (I + lambda K'K) tau = y. lambda 1600 quarterly, 129600 monthly, 100 annual. */
export function hpFilter(y: number[], lambda: number): { trend: number[]; cycle: number[] } {
  const n = y.length;
  if (n < 5) throw new Error("HP filter needs at least 5 observations");
  // Pentadiagonal symmetric matrix stored as diagonals d0 (main), d1 (first off), d2 (second off)
  const d0 = new Array<number>(n).fill(1 + 6 * lambda), d1 = new Array<number>(n - 1).fill(-4 * lambda), d2 = new Array<number>(n - 2).fill(lambda);
  d0[0] = d0[n - 1] = 1 + lambda; d0[1] = d0[n - 2] = 1 + 5 * lambda;
  d1[0] = d1[n - 2] = -2 * lambda;
  // Banded LDL' with half-bandwidth 2: L1[i] = L[i][i-1], L2[i] = L[i][i-2].
  //   D[i]   = a[i][i] - L1[i]^2 D[i-1] - L2[i]^2 D[i-2]
  //   L2[i]  = a[i][i-2] / D[i-2]
  //   L1[i]  = (a[i][i-1] - L2[i] L1[i-1] D[i-2]) / D[i-1]
  const D = new Array<number>(n).fill(0), L1 = new Array<number>(n).fill(0), L2 = new Array<number>(n).fill(0);
  for (let i = 0; i < n; i++) {
    let s = d0[i];
    if (i >= 1) s -= L1[i] * L1[i] * D[i - 1];
    if (i >= 2) s -= L2[i] * L2[i] * D[i - 2];
    D[i] = s;
    if (i + 2 < n) L2[i + 2] = d2[i] / D[i];
    if (i + 1 < n) L1[i + 1] = (d1[i] - (i >= 1 ? L2[i + 1] * L1[i] * D[i - 1] : 0)) / D[i];
  }
  // Forward: L z = y
  const z = new Array<number>(n).fill(0);
  for (let i = 0; i < n; i++) z[i] = y[i] - (i >= 1 ? L1[i] * z[i - 1] : 0) - (i >= 2 ? L2[i] * z[i - 2] : 0);
  // Diagonal
  for (let i = 0; i < n; i++) z[i] /= D[i];
  // Backward: L' tau = z
  const tau = new Array<number>(n).fill(0);
  for (let i = n - 1; i >= 0; i--) tau[i] = z[i] - (i + 1 < n ? L1[i + 1] * tau[i + 1] : 0) - (i + 2 < n ? L2[i + 2] * tau[i + 2] : 0);
  return { trend: tau, cycle: y.map((v, i) => v - tau[i]) };
}

export interface Decomposition { trend: Array<number | null>; seasonal: number[]; residual: Array<number | null>; seasonal_factors: number[]; seasonal_strength: number; trend_strength: number }

/** Classical additive decomposition with a centred moving average trend. */
export function decompose(y: number[], period: number): Decomposition {
  const n = y.length;
  if (n < 2 * period + 1) throw new Error(`Need at least two full periods (${2 * period + 1} obs), got ${n}`);
  const trend: Array<number | null> = new Array(n).fill(null);
  const half = Math.floor(period / 2);
  for (let t = half; t < n - half; t++) {
    let s = 0;
    if (period % 2 === 0) {
      for (let j = -half; j <= half; j++) s += (j === -half || j === half ? 0.5 : 1) * y[t + j];
      trend[t] = s / period;
    } else {
      for (let j = -half; j <= half; j++) s += y[t + j];
      trend[t] = s / period;
    }
  }
  const sums = new Array<number>(period).fill(0), counts = new Array<number>(period).fill(0);
  for (let t = 0; t < n; t++) if (trend[t] !== null) { sums[t % period] += y[t] - (trend[t] as number); counts[t % period]++; }
  const factors = sums.map((s, i) => (counts[i] ? s / counts[i] : 0));
  const fm = mean(factors);
  const sf = factors.map((f) => f - fm);
  const seasonal = y.map((_, t) => sf[t % period]);
  const residual = y.map((v, t) => (trend[t] === null ? null : v - (trend[t] as number) - seasonal[t]));
  const r = residual.filter((v): v is number => v !== null);
  const idx = residual.map((v, i) => (v !== null ? i : -1)).filter((i) => i >= 0);
  const rs = idx.map((i) => (residual[i] as number) + seasonal[i]);
  const rt = idx.map((i) => (residual[i] as number) + (trend[i] as number));
  const strength = (a: number[], b: number[]) => Math.max(0, 1 - variance(a) / variance(b));
  return { trend, seasonal, residual, seasonal_factors: sf, seasonal_strength: r.length > 3 ? strength(r, rs) : NaN, trend_strength: r.length > 3 ? strength(r, rt) : NaN };
}

// ---------------------------------------------------------------------------
// Forecasting

export interface HoltWintersResult { alpha: number; beta: number; gamma: number | null; fitted: number[]; forecast: number[]; sse: number; resid_sd: number; level: number; trend: number; seasonal: number[] }

/** Holt-Winters additive (seasonal when period > 1), parameters by grid search on in-sample SSE. */
export function holtWinters(y: number[], h: number, period: number): HoltWintersResult {
  const n = y.length;
  const seasonal = period > 1 && n >= 2 * period;
  const run = (a: number, b: number, g: number) => {
    let level: number, trend: number;
    let s: number[] = new Array(Math.max(period, 1)).fill(0);
    if (seasonal) {
      const first = mean(y.slice(0, period)), second = mean(y.slice(period, 2 * period));
      level = first; trend = (second - first) / period;
      s = y.slice(0, period).map((v) => v - first);
    } else { level = y[0]; trend = n > 1 ? y[1] - y[0] : 0; }
    const fitted: number[] = [];
    let sse = 0;
    for (let t = 0; t < n; t++) {
      const si = seasonal ? s[t % period] : 0;
      const f = level + trend + si;
      fitted.push(f);
      const e = y[t] - f;
      sse += e * e;
      const newLevel = a * (y[t] - si) + (1 - a) * (level + trend);
      trend = b * (newLevel - level) + (1 - b) * trend;
      if (seasonal) s[t % period] = g * (y[t] - newLevel) + (1 - g) * si;
      level = newLevel;
    }
    const forecast = Array.from({ length: h }, (_, i) => level + (i + 1) * trend + (seasonal ? s[(n + i) % period] : 0));
    return { fitted, forecast, sse, level, trend, s };
  };
  let best: { a: number; b: number; g: number; r: ReturnType<typeof run> } | null = null;
  const grid = [0.05, 0.15, 0.3, 0.5, 0.7, 0.9];
  for (const a of grid) for (const b of [0.01, 0.05, 0.1, 0.2, 0.4]) for (const g of seasonal ? grid : [0]) {
    const r = run(a, b, g);
    if (!best || r.sse < best.r.sse) best = { a, b, g, r };
  }
  const r = best!.r;
  return { alpha: best!.a, beta: best!.b, gamma: seasonal ? best!.g : null, fitted: r.fitted, forecast: r.forecast, sse: r.sse, resid_sd: Math.sqrt(r.sse / Math.max(n - 3, 1)), level: r.level, trend: r.trend, seasonal: seasonal ? r.s : [] };
}

export interface ArResult { order: number; coef: number[]; fitted: number[]; forecast: number[]; resid_sd: number; aic: number }

/** AR(p) by OLS with a constant, recursive forecasts. */
export function arForecast(y: number[], p: number, h: number): ArResult {
  const n = y.length;
  if (n < 3 * p + 5) throw new Error(`Too few observations (${n}) for AR(${p})`);
  const target: number[] = [], X: number[][] = [];
  for (let t = p; t < n; t++) { target.push(y[t]); X.push([1, ...Array.from({ length: p }, (_, j) => y[t - 1 - j])]); }
  const fit = ols(target, X);
  const hist = [...y];
  const forecast: number[] = [];
  for (let i = 0; i < h; i++) {
    const v = fit.beta[0] + fit.beta.slice(1).reduce((s, c, j) => s + c * hist[hist.length - 1 - j], 0);
    forecast.push(v); hist.push(v);
  }
  return { order: p, coef: fit.beta, fitted: fit.fitted, forecast, resid_sd: fit.sigma, aic: fit.aic };
}

// ---------------------------------------------------------------------------
// Structural breaks

export interface ChowResult { break_index: number; F: number; p: number; k: number; n1: number; n2: number }

/** Chow test for a break at index b in the regression y on X (X includes the constant). */
export function chow(y: number[], X: number[][], b: number): ChowResult {
  const k = X[0].length;
  if (b <= k + 1 || y.length - b <= k + 1) throw new Error("Break too close to the sample edge");
  const pooled = ols(y, X), a = ols(y.slice(0, b), X.slice(0, b)), c = ols(y.slice(b), X.slice(b));
  const F = ((pooled.rss - (a.rss + c.rss)) / k) / ((a.rss + c.rss) / (y.length - 2 * k));
  return { break_index: b, F, p: fUpperP(F, k, y.length - 2 * k), k, n1: b, n2: y.length - b };
}

/**
 * Residual sum of squares of y on X over rows [lo, hi) from prefix sums, for X = [1] or
 * [1, x]. Returns null when the segment cannot identify the slope.
 */
function segmentRssFactory(y: number[], X: number[][]): ((lo: number, hi: number) => number | null) | null {
  const k = X[0].length;
  if (k > 2 || X.some((r) => r[0] !== 1)) return null;
  const n = y.length;
  const Sy = new Float64Array(n + 1), Syy = new Float64Array(n + 1), Sx = new Float64Array(n + 1), Sxx = new Float64Array(n + 1), Sxy = new Float64Array(n + 1);
  for (let t = 0; t < n; t++) {
    const x = k === 2 ? X[t][1] : 0;
    Sy[t + 1] = Sy[t] + y[t]; Syy[t + 1] = Syy[t] + y[t] * y[t];
    Sx[t + 1] = Sx[t] + x; Sxx[t + 1] = Sxx[t] + x * x; Sxy[t + 1] = Sxy[t] + x * y[t];
  }
  return (lo, hi) => {
    const m = hi - lo;
    if (m <= k) return null;
    const sy = Sy[hi] - Sy[lo], syy = Syy[hi] - Syy[lo];
    let rss = syy - (sy * sy) / m;
    if (k === 2) {
      const sx = Sx[hi] - Sx[lo], sxx = Sxx[hi] - Sxx[lo], sxy = Sxy[hi] - Sxy[lo];
      const vx = sxx - (sx * sx) / m;
      if (vx <= 1e-12 * Math.max(1, sxx)) return null;
      const cxy = sxy - (sx * sy) / m;
      rss -= (cxy * cxy) / vx;
    }
    return Math.max(rss, 0);
  };
}

/**
 * Quandt-Andrews sup-F scan. Candidates run over the middle (1 - 2*trim) of the sample, or
 * keep at least `minSeg` observations on either side when given (the sequential search
 * passes the full-sample trim so short segments are not scanned to their edges). For a
 * constant or a constant and one regressor the scan uses prefix sums, O(n) in total.
 */
export function supF(y: number[], X: number[][], trim = 0.15, minSeg?: number): { best: ChowResult; scan: Array<{ index: number; F: number }> } {
  const n = y.length, k = X[0].length;
  const h = Math.max(minSeg ?? Math.floor(n * trim), k + 2);
  const lo = h, hi = n - h;
  let best: ChowResult | null = null;
  const scan: Array<{ index: number; F: number }> = [];
  const fast = segmentRssFactory(y, X);
  if (fast) {
    const pooled = fast(0, n);
    if (pooled === null) throw new Error("No admissible break points");
    const df2 = n - 2 * k;
    for (let b = lo; b <= hi; b++) {
      const a = fast(0, b), c = fast(b, n);
      if (a === null || c === null || df2 <= 0) continue;
      const F = ((pooled - (a + c)) / k) / ((a + c) / df2);
      scan.push({ index: b, F });
      if (!best || F > best.F) best = { break_index: b, F, p: fUpperP(F, k, df2), k, n1: b, n2: n - b };
    }
  } else {
    for (let b = lo; b <= hi; b++) {
      try {
        const r = chow(y, X, b);
        scan.push({ index: b, F: r.F });
        if (!best || r.F > best.F) best = r;
      } catch { /* skip */ }
    }
  }
  if (!best) throw new Error("No admissible break points");
  return { best, scan };
}

// ---------------------------------------------------------------------------
// KPSS stationarity test (null: stationary)

export interface KpssResult { trend: "c" | "ct"; lags: number; statistic: number; critical: { "10%": number; "5%": number; "2.5%": number; "1%": number }; reject_stationarity_at: "1%" | "2.5%" | "5%" | "10%" | null }

/** Kwiatkowski-Phillips-Schmidt-Shin, Bartlett long-run variance, lag floor(4(T/100)^(1/4)). */
export function kpss(y: number[], trend: "c" | "ct" = "c", lags?: number): KpssResult {
  const n = y.length;
  if (n < 12) throw new Error(`KPSS needs at least 12 observations, got ${n}`);
  const X = y.map((_, t) => (trend === "ct" ? [1, t] : [1]));
  const e = ols(y, X).resid;
  const L = lags ?? Math.floor(4 * Math.pow(n / 100, 0.25));
  const s2 = longRunVariance(e, L);   // residuals of a regression on a constant already have zero mean
  let S = 0, num = 0;
  for (let t = 0; t < n; t++) { S += e[t]; num += S * S; }
  const stat = num / (n * n * s2);
  const critical = trend === "ct"
    ? { "10%": 0.119, "5%": 0.146, "2.5%": 0.176, "1%": 0.216 }
    : { "10%": 0.347, "5%": 0.463, "2.5%": 0.574, "1%": 0.739 };
  const reject = stat > critical["1%"] ? "1%" : stat > critical["2.5%"] ? "2.5%" : stat > critical["5%"] ? "5%" : stat > critical["10%"] ? "10%" : null;
  return { trend, lags: L, statistic: stat, critical, reject_stationarity_at: reject };
}

// ---------------------------------------------------------------------------
// Matrix helpers for the multivariate tools

type Mat = number[][];
const zeros = (r: number, c: number): Mat => Array.from({ length: r }, () => new Array<number>(c).fill(0));
export function matmul(A: Mat, B: Mat): Mat {
  const out = zeros(A.length, B[0].length);
  for (let i = 0; i < A.length; i++) for (let k = 0; k < B.length; k++) { const a = A[i][k]; if (a === 0) continue; for (let j = 0; j < B[0].length; j++) out[i][j] += a * B[k][j]; }
  return out;
}
export const transpose = (A: Mat): Mat => A[0].map((_, j) => A.map((r) => r[j]));
/** Lower Cholesky factor of a symmetric positive definite matrix. */
export function cholesky(A: Mat): Mat {
  const n = A.length, L = zeros(n, n);
  for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) {
    let s = A[i][j];
    for (let k = 0; k < j; k++) s -= L[i][k] * L[j][k];
    if (i === j) { if (s <= 0) throw new Error("Matrix is not positive definite"); L[i][i] = Math.sqrt(s); } else L[i][j] = s / L[j][j];
  }
  return L;
}
/** Solve L X = B for lower-triangular L. */
function forwardSolve(L: Mat, B: Mat): Mat {
  const n = L.length, m = B[0].length, X = zeros(n, m);
  for (let c = 0; c < m; c++) for (let i = 0; i < n; i++) { let s = B[i][c]; for (let k = 0; k < i; k++) s -= L[i][k] * X[k][c]; X[i][c] = s / L[i][i]; }
  return X;
}
/** Eigen-decomposition of a symmetric matrix by cyclic Jacobi. Returns values descending and matching column vectors. */
export function symEigen(A: Mat): { values: number[]; vectors: Mat } {
  const n = A.length, M: Mat = A.map((r) => [...r]);
  const V: Mat = A.map((_, i) => A.map((__, j) => (i === j ? 1 : 0)));
  for (let sweep = 0; sweep < 100; sweep++) {
    let off = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) off += M[i][j] * M[i][j];
    if (off < 1e-22) break;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) {
      if (Math.abs(M[p][q]) < 1e-300) continue;
      const theta = (M[q][q] - M[p][p]) / (2 * M[p][q]);
      const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
      const c = 1 / Math.sqrt(t * t + 1), s = t * c;
      for (let k = 0; k < n; k++) { const mkp = M[k][p], mkq = M[k][q]; M[k][p] = c * mkp - s * mkq; M[k][q] = s * mkp + c * mkq; }
      for (let k = 0; k < n; k++) { const mpk = M[p][k], mqk = M[q][k]; M[p][k] = c * mpk - s * mqk; M[q][k] = s * mpk + c * mqk; }
      for (let k = 0; k < n; k++) { const vkp = V[k][p], vkq = V[k][q]; V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq; }
    }
  }
  const order = M.map((_, i) => i).sort((a, b) => M[b][b] - M[a][a]);
  return { values: order.map((i) => M[i][i]), vectors: V.map((row) => order.map((i) => row[i])) };
}

// ---------------------------------------------------------------------------
// Johansen cointegration (trace test, unrestricted constant)

export interface JohansenResult {
  k: number; lags: number; det: JohansenDet; nobs: number;
  eigenvalues: number[];
  trace: Array<{ r: number; statistic: number; critical: { "10%": number; "5%": number; "1%": number }; reject: boolean }>;
  rank_at_5pct: number;
  cointegrating_vector: number[] | null;
  /** All k candidate vectors (columns, ordered by eigenvalue), each normalised on the first series; with a restricted constant the last row is the constant. */
  vectors: number[][];
}

/** MacKinnon-Haug-Michelis trace critical values, unrestricted constant (statsmodels det_order=0), rows n-r = 1..5. */
const JOHANSEN_TRACE_CV = [
  [2.7055, 3.8415, 6.6349],
  [13.4294, 15.4943, 19.9349],
  [27.0669, 29.7961, 35.4628],
  [44.4929, 47.8545, 54.6815],
  [65.8202, 69.8189, 76.1631],
];
/**
 * Trace critical values with the constant restricted to the cointegrating relation (no drift
 * in the levels). 5% and 1% are MacKinnon-Haug-Michelis (1999); the 10% column is simulated
 * from the asymptotic distribution (40,000 draws of tr(∫dB F'(∫FF')⁻¹∫F dB') with F = (B, 1),
 * 1,000-point grid), a method that reproduces the table above to within 0.4.
 */
const JOHANSEN_TRACE_CV_RC = [
  [7.59, 9.1645, 12.7607],
  [17.76, 20.2618, 25.0781],
  [32.14, 35.1928, 41.1950],
  [50.29, 54.0790, 61.2669],
  [72.20, 76.9728, 85.3364],
];
/**
 * Trace critical values with an unrestricted constant and a linear trend restricted to the
 * cointegrating relation. 5% is MacKinnon-Haug-Michelis (1999); 10% and 1% are simulated as
 * for the restricted constant, with F = (B demeaned, u - 1/2); the simulation reproduces the
 * published 5% column to within 0.7.
 */
const JOHANSEN_TRACE_CV_RT = [
  [10.61, 12.5180, 16.39],
  [23.10, 25.8721, 31.06],
  [39.54, 42.9153, 49.27],
  [59.70, 63.8761, 71.00],
  [83.84, 88.8038, 97.01],
];
export type JohansenDet = "constant" | "restricted_constant" | "restricted_trend";

/**
 * Johansen trace test. det = "constant": unrestricted constant in the VAR, right for series
 * that drift (most price levels, logs of output). det = "restricted_constant": the constant
 * enters the cointegrating relation only, right for series without drift (interest rates,
 * ratios, real exchange rates); the vectors then carry an extra last element, the constant.
 * det = "restricted_trend": unrestricted constant plus a linear trend inside the relation, for
 * series that drift at different rates so the equilibrium itself trends; the extra element
 * is the trend coefficient.
 */
export function johansen(Y: number[][], lags = 1, det: JohansenDet = "constant"): JohansenResult {
  // Y: rows = time, columns = variables
  const T = Y.length, k = Y[0].length;
  if (k < 2 || k > 5) throw new Error("Johansen here supports 2 to 5 series");
  if (T < 10 * k + lags + 10) throw new Error(`Too few observations (${T}) for ${k} series with ${lags} lags`);
  const rc = det === "restricted_constant", rt = det === "restricted_trend";
  const dY = Y.slice(1).map((r, t) => r.map((v, j) => v - Y[t][j]));
  const rows: number[][] = [], dyT: number[][] = [], lagY: number[][] = [];
  for (let t = lags; t < dY.length; t++) {
    const z = rc ? [] : [1];
    for (let l = 1; l <= lags; l++) z.push(...dY[t - l]);
    rows.push(z); dyT.push(dY[t]); lagY.push(rc ? [...Y[t], 1] : rt ? [...Y[t], t] : Y[t]); // Y[t] is y_{t-1} relative to dY[t] = y_{t+1}-y_t
  }
  const n = rows.length;
  const residualsOn = (target: number[][]) => {
    if (!rows[0].length) return target.map((r) => [...r]);
    const out: number[][] = Array.from({ length: n }, () => new Array<number>(target[0].length).fill(0));
    for (let j = 0; j < target[0].length; j++) {
      const fit = ols(target.map((r) => r[j]), rows);
      for (let t = 0; t < n; t++) out[t][j] = fit.resid[t];
    }
    return out;
  };
  const R0 = residualsOn(dyT), R1 = residualsOn(lagY);
  const cross = (A: number[][], B: number[][]) => { const out = zeros(A[0].length, B[0].length); for (let t = 0; t < n; t++) for (let i = 0; i < A[0].length; i++) for (let j = 0; j < B[0].length; j++) out[i][j] += A[t][i] * B[t][j] / n; return out; };
  const S00 = cross(R0, R0), S01 = cross(R0, R1), S10 = transpose(S01), S11 = cross(R1, R1);
  const S00inv = inverse(S00);
  if (!S00inv) throw new Error("Residual covariance is singular");
  const L = cholesky(S11);
  // M = L^-1 S10 S00^-1 S01 L^-T  (symmetric); eigenvalues are the canonical correlations squared
  const A = matmul(matmul(S10, S00inv), S01);
  const Linv = forwardSolve(L, A.map((_, i) => A.map((__, j) => (i === j ? 1 : 0))));
  const M = matmul(matmul(Linv, A), transpose(Linv));
  const { values, vectors } = symEigen(M);
  // With the restricted constant M is (k+1)x(k+1) of rank k: the k largest eigenvalues are the test's.
  const eig = values.slice(0, k).map((v) => Math.min(Math.max(v, 0), 0.999999));
  const table = rc ? JOHANSEN_TRACE_CV_RC : rt ? JOHANSEN_TRACE_CV_RT : JOHANSEN_TRACE_CV;
  const trace = eig.map((_, r) => {
    let s = 0;
    for (let i = r; i < k; i++) s += Math.log(1 - eig[i]);
    const stat = -n * s;
    const cv = table[k - r - 1];
    return { r, statistic: stat, critical: { "10%": cv[0], "5%": cv[1], "1%": cv[2] }, reject: stat > cv[1] };
  });
  let rank = 0;
  for (const t of trace) { if (t.reject) rank = t.r + 1; else break; }
  // Eigenvectors back-transformed: beta = L^-T u, each column normalised on the first series
  const B = matmul(transpose(Linv), vectors);
  const cols: number[][] = [];
  for (let c = 0; c < k; c++) { const col = B.map((r) => r[c]); cols.push(col[0] !== 0 ? col.map((b) => b / col[0]) : col); }
  const betaAll = cols[0].map((_, i) => cols.map((col) => col[i]));   // (k or k+1) x k
  return { k, lags, det, nobs: n, eigenvalues: eig, trace, rank_at_5pct: rank, cointegrating_vector: rank > 0 ? cols[0] : null, vectors: betaAll };
}

// ---------------------------------------------------------------------------
// Vector error-correction model: dy_t = c + alpha (beta' y_{t-1}) + sum Gamma_l dy_{t-l} + e_t

export interface VecmResult {
  k: number; lags: number; rank: number; nobs: number; det: JohansenDet;
  beta: number[][];          // k x r, each column normalised on the first series
  beta_constant: number[];   // r constants inside the relations (zero unless restricted_constant)
  beta_trend: number[];      // r trend coefficients inside the relations (zero unless restricted_trend)
  alpha: number[][];         // k x r adjustment coefficients (row = equation)
  alpha_t: number[][];
  alpha_p: number[][];
  gamma: number[][][];       // [lag][equation][variable] short-run coefficients
  constant: number[];
  r2: number[];
  ect: number[][];           // error-correction terms beta' y_t for every t (rows = time, cols = r)
  johansen: JohansenResult;
}

export function vecm(Y: number[][], lags = 1, rank?: number, det: JohansenDet = "constant"): VecmResult {
  const j = johansen(Y, lags, det);
  const k = j.k;
  const rc = det === "restricted_constant", rt = det === "restricted_trend";
  const r = rank ?? j.rank_at_5pct;
  if (r < 1) throw new Error("No cointegrating relation at 5% (rank 0): estimate a VAR on differences instead, or pass rank explicitly.");
  if (r >= k) throw new Error(`Rank must be below the number of series (${k}); rank ${k} means every series is stationary in levels.`);
  const beta = Y[0].map((_, i) => j.vectors[i].slice(0, r));   // k x r
  const beta_constant = rc ? j.vectors[k].slice(0, r) : new Array<number>(r).fill(0);
  const beta_trend = rt ? j.vectors[k].slice(0, r) : new Array<number>(r).fill(0);
  // The trend index matches the one johansen used: the position of y_{t-1} in Y.
  const ectAt = (y: number[], t: number) => beta[0].map((_, c) => y.reduce((sum, v, i) => sum + v * beta[i][c], 0) + beta_constant[c] + beta_trend[c] * t);
  const dY = Y.slice(1).map((row, t) => row.map((v, i) => v - Y[t][i]));
  const X: number[][] = [], targets: number[][] = [];
  const off = rc ? 0 : 1;   // column of the first ECT
  for (let t = lags; t < dY.length; t++) {
    const z = [...(rc ? [] : [1]), ...ectAt(Y[t], t)];          // Y[t] is y_{t-1} for dY[t]
    for (let l = 1; l <= lags; l++) z.push(...dY[t - l]);
    X.push(z); targets.push(dY[t]);
  }
  const alpha: number[][] = [], alpha_t: number[][] = [], alpha_p: number[][] = [], constant: number[] = [], r2: number[] = [];
  const gamma: number[][][] = Array.from({ length: lags }, () => Array.from({ length: k }, () => new Array<number>(k).fill(0)));
  for (let eq = 0; eq < k; eq++) {
    const fit = ols(targets.map((row) => row[eq]), X);
    constant.push(rc ? 0 : fit.beta[0]);
    alpha.push(fit.beta.slice(off, off + r)); alpha_t.push(fit.t.slice(off, off + r)); alpha_p.push(fit.p.slice(off, off + r));
    for (let l = 0; l < lags; l++) for (let v = 0; v < k; v++) gamma[l][eq][v] = fit.beta[off + r + l * k + v];
    r2.push(fit.r2);
  }
  return { k, lags, rank: r, nobs: X.length, det, beta, beta_constant, beta_trend, alpha, alpha_t, alpha_p, gamma, constant, r2, ect: Y.map((y, t) => ectAt(y, t)), johansen: j };
}

/** t-statistic of the mean of first differences: does the series drift? */
export function driftT(y: number[]): number {
  const d = diff(y);
  if (d.length < 8) return NaN;
  return (mean(d) / sd(d)) * Math.sqrt(d.length);
}

// ---------------------------------------------------------------------------
// VAR(p) with orthogonalised impulse responses and variance decomposition

export interface VarResult {
  p: number; k: number; nobs: number;
  coef: number[][];              // k x (1 + k p): const, then A1..Ap column blocks
  sigma: number[][];
  aic: number; bic: number;
  irf: number[][][];             // [h][response][shock], orthogonalised (Cholesky, variable order = input order)
  fevd: number[][][];            // [h][variable][shock] shares
  granger: Array<{ cause: number; effect: number; F: number; p: number }>;
  fitted_last: number[];
  /** MA coefficient matrices Psi_0..Psi_horizon (Psi_0 = I), for structural identification. */
  psi: number[][][];
  /** Reduced-form residuals, one array per equation. */
  resid: number[][];
  /** Sum of the lag matrices A_1 + ... + A_p, for the long-run multiplier. */
  a_sum: number[][];
}

/** Several equations on the same regressors: one X'X inverse for all of them. */
function olsMulti(targets: number[][], X: number[][]): Array<{ beta: number[]; resid: number[]; fitted: number[]; rss: number }> {
  const n = X.length, k = X[0].length, m = targets[0].length;
  if (n <= k) throw new Error(`OLS needs more observations (${n}) than regressors (${k})`);
  const XtX: number[][] = Array.from({ length: k }, () => new Array<number>(k).fill(0));
  const Xty: number[][] = Array.from({ length: m }, () => new Array<number>(k).fill(0));
  for (let i = 0; i < n; i++) {
    const r = X[i], y = targets[i];
    for (let a = 0; a < k; a++) { for (let e = 0; e < m; e++) Xty[e][a] += r[a] * y[e]; for (let b = a; b < k; b++) XtX[a][b] += r[a] * r[b]; }
  }
  for (let a = 0; a < k; a++) for (let b = 0; b < a; b++) XtX[a][b] = XtX[b][a];
  const XtXinv = inverse(XtX);
  if (!XtXinv) throw new Error("Regressors are collinear (X'X singular). Drop one.");
  return Array.from({ length: m }, (_, e) => {
    const beta = XtXinv.map((row) => row.reduce((sum, v, j) => sum + v * Xty[e][j], 0));
    const fitted = X.map((r) => r.reduce((sum, v, j) => sum + v * beta[j], 0));
    const resid = targets.map((y, i) => y[e] - fitted[i]);
    return { beta, resid, fitted, rss: resid.reduce((sum, v) => sum + v * v, 0) };
  });
}

export function varModel(Y: number[][], p: number, horizon = 12, opts: { granger?: boolean } = {}): VarResult {
  const T = Y.length, k = Y[0].length;
  if (T < k * p * 3 + 10) throw new Error(`Too few observations (${T}) for VAR(${p}) with ${k} variables`);
  const X: number[][] = [], targets: number[][] = [];
  for (let t = p; t < T; t++) {
    const row = [1];
    for (let l = 1; l <= p; l++) row.push(...Y[t - l]);
    X.push(row); targets.push(Y[t]);
  }
  const n = X.length;
  const fits = olsMulti(targets, X);
  const coef = fits.map((f) => f.beta);
  const resid = fits.map((f) => f.resid);
  const sigma = zeros(k, k);
  for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) { let s = 0; for (let t = 0; t < n; t++) s += resid[i][t] * resid[j][t]; sigma[i][j] = s / (n - X[0].length); }
  const det = (() => { try { const L = cholesky(sigma); let d = 1; for (let i = 0; i < k; i++) d *= L[i][i] * L[i][i]; return d; } catch { return NaN; } })();
  const nparam = k * X[0].length;
  const aic = Math.log(det) + (2 * nparam) / n, bic = Math.log(det) + (Math.log(n) * nparam) / n;
  // MA representation
  const A = (l: number): Mat => coef.map((row) => row.slice(1 + (l - 1) * k, 1 + l * k));
  const eye: Mat = Array.from({ length: k }, (_, i) => Array.from({ length: k }, (__, j) => (i === j ? 1 : 0)));
  const Psi: Mat[] = [eye];
  for (let s = 1; s <= horizon; s++) {
    let acc = zeros(k, k);
    for (let l = 1; l <= Math.min(s, p); l++) { const term = matmul(A(l), Psi[s - l]); acc = acc.map((r, i) => r.map((v, j) => v + term[i][j])); }
    Psi.push(acc);
  }
  let P: Mat;
  try { P = cholesky(sigma); } catch { P = sigma.map((r, i) => r.map((_, j) => (i === j ? Math.sqrt(Math.max(sigma[i][i], 0)) : 0))); }
  const irf = Psi.map((Ps) => matmul(Ps, P));
  const fevd: number[][][] = [];
  const cum = zeros(k, k);
  for (let h = 0; h <= horizon; h++) {
    for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) cum[i][j] += irf[h][i][j] * irf[h][i][j];
    fevd.push(cum.map((row) => { const tot = row.reduce((a, b) => a + b, 0); return row.map((v) => (tot ? v / tot : 0)); }));
  }
  // Block Granger tests: does variable c help predict variable e beyond e's own lags and the other variables?
  const granger: VarResult["granger"] = [];
  if (opts.granger !== false) for (let e = 0; e < k; e++) for (let c = 0; c < k; c++) {
    if (c === e) continue;
    const keep = X[0].map((_, idx) => idx === 0 || ((idx - 1) % k) !== c);
    const Xr = X.map((row) => row.filter((_, idx) => keep[idx]));
    const r = ols(targets.map((row) => row[e]), Xr);
    const u = fits[e];
    const F = ((r.rss - u.rss) / p) / (u.rss / (n - X[0].length));
    granger.push({ cause: c, effect: e, F, p: fUpperP(F, p, n - X[0].length) });
  }
  const aSum = zeros(k, k);
  for (let l = 1; l <= p; l++) { const Al = A(l); for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) aSum[i][j] += Al[i][j]; }
  return { p, k, nobs: n, coef, sigma, aic, bic, irf, fevd, granger, fitted_last: fits.map((f) => f.fitted[f.fitted.length - 1]), psi: Psi, resid, a_sum: aSum };
}

export function varSelectLag(Y: number[][], maxLag: number): number {
  let best = 1, bestAic = Infinity;
  for (let p = 1; p <= maxLag; p++) {
    try { const m = varModel(Y, p, 1); if (m.aic < bestAic) { bestAic = m.aic; best = p; } } catch { break; }
  }
  return best;
}

// ---------------------------------------------------------------------------
// ARIMA(p, d, q) by conditional sum of squares with Nelder-Mead

function nelderMead(f: (x: number[]) => number, x0: number[], step = 0.1, iters = 2000): number[] {
  const n = x0.length;
  let simplex = [x0, ...x0.map((_, i) => x0.map((v, j) => (i === j ? v + step : v)))];
  let vals = simplex.map(f);
  for (let it = 0; it < iters; it++) {
    const order = vals.map((_, i) => i).sort((a, b) => vals[a] - vals[b]);
    simplex = order.map((i) => simplex[i]); vals = order.map((i) => vals[i]);
    if (Math.abs(vals[n] - vals[0]) < 1e-10 * (1 + Math.abs(vals[0]))) break;
    const centroid = x0.map((_, j) => simplex.slice(0, n).reduce((s, p) => s + p[j], 0) / n);
    const worst = simplex[n];
    const refl = centroid.map((c, j) => c + (c - worst[j]));
    const fr = f(refl);
    if (fr < vals[0]) {
      const exp = centroid.map((c, j) => c + 2 * (c - worst[j]));
      const fe = f(exp);
      if (fe < fr) { simplex[n] = exp; vals[n] = fe; } else { simplex[n] = refl; vals[n] = fr; }
    } else if (fr < vals[n - 1]) { simplex[n] = refl; vals[n] = fr; }
    else {
      const con = centroid.map((c, j) => c + 0.5 * (worst[j] - c));
      const fc = f(con);
      if (fc < vals[n]) { simplex[n] = con; vals[n] = fc; }
      else { for (let i = 1; i <= n; i++) { simplex[i] = simplex[i].map((v, j) => simplex[0][j] + 0.5 * (v - simplex[0][j])); vals[i] = f(simplex[i]); } }
    }
  }
  return simplex[vals.indexOf(Math.min(...vals))];
}

export interface ArimaResult { p: number; d: number; q: number; const: number; ar: number[]; ma: number[]; sse: number; aic: number; resid_sd: number; forecast: number[]; fitted: number[] }

function armaCss(y: number[], p: number, q: number, theta: number[]): { sse: number; resid: number[]; fitted: number[] } {
  const c = theta[0], phi = theta.slice(1, 1 + p), th = theta.slice(1 + p);
  const n = y.length, e = new Array<number>(n).fill(0), fitted = new Array<number>(n).fill(NaN);
  let sse = 0;
  for (let t = Math.max(p, q); t < n; t++) {
    let f = c;
    for (let i = 0; i < p; i++) f += phi[i] * y[t - 1 - i];
    for (let j = 0; j < q; j++) f += th[j] * e[t - 1 - j];
    e[t] = y[t] - f; fitted[t] = f; sse += e[t] * e[t];
  }
  return { sse, resid: e, fitted };
}

export function arima(series: number[], p: number, d: number, q: number, h: number): ArimaResult {
  let y = [...series];
  const lastLevels: number[][] = [];
  for (let i = 0; i < d; i++) { lastLevels.push([...y]); y = diff(y); }
  const n = y.length;
  if (n < 3 * (p + q) + 10) throw new Error(`Too few observations (${n}) for ARIMA(${p},${d},${q})`);
  // Start from OLS AR fit, MA at zero
  let x0: number[] = [mean(y), ...new Array<number>(p).fill(0), ...new Array<number>(q).fill(0)];
  if (p > 0) { try { const ar = arForecast(y, p, 1); x0 = [ar.coef[0], ...ar.coef.slice(1), ...new Array<number>(q).fill(0)]; } catch { /* keep zeros */ } }
  const obj = (th: number[]) => { const { sse } = armaCss(y, p, q, th); return Number.isFinite(sse) ? sse : 1e300; };
  const theta = p + q > 0 ? nelderMead(obj, x0, 0.05) : x0;
  const { sse, fitted } = armaCss(y, p, q, theta);
  const eff = n - Math.max(p, q);
  const kpar = 1 + p + q;
  const aic = eff * Math.log(sse / eff) + 2 * kpar;
  // Forecast on the differenced scale, then integrate
  const c = theta[0], phi = theta.slice(1, 1 + p), th = theta.slice(1 + p);
  const { resid } = armaCss(y, p, q, theta);
  const hist = [...y], errs = [...resid];
  const fc: number[] = [];
  for (let i = 0; i < h; i++) {
    let f = c;
    for (let j = 0; j < p; j++) f += phi[j] * hist[hist.length - 1 - j];
    for (let j = 0; j < q; j++) { const idx = errs.length - 1 - j; f += idx >= 0 && idx < resid.length + i ? th[j] * (idx < resid.length ? errs[idx] : 0) : 0; }
    fc.push(f); hist.push(f); errs.push(0);
  }
  let level = fc;
  for (let i = d - 1; i >= 0; i--) {
    const last = lastLevels[i][lastLevels[i].length - 1];
    let acc = last;
    level = level.map((v) => (acc += v));
  }
  return { p, d, q, const: c, ar: phi, ma: th, sse, aic, resid_sd: Math.sqrt(sse / eff), forecast: level, fitted };
}

/** Pick (p, d, q) by AIC on a small grid; d from the ADF test unless given. */
export function autoArima(series: number[], h: number, dFixed?: number, maxP = 3, maxQ = 2): ArimaResult {
  let d = dFixed ?? 0;
  if (dFixed === undefined) {
    try { const a = adf(series, "c"); if (!a.reject_unit_root_at) { d = 1; const b = adf(diff(series), "c"); if (!b.reject_unit_root_at) d = 2; } } catch { d = 1; }
  }
  let best: ArimaResult | null = null;
  for (let p = 0; p <= maxP; p++) for (let q = 0; q <= maxQ; q++) {
    if (p === 0 && q === 0 && d === 0) continue;
    try { const m = arima(series, p, d, q, h); if (!best || m.aic < best.aic) best = m; } catch { /* skip */ }
  }
  if (!best) throw new Error("No ARIMA order could be estimated");
  return best;
}


// ---------------------------------------------------------------------------
// GARCH(1,1) by maximum likelihood on demeaned series (Gaussian innovations)

export interface GarchResult {
  omega: number; alpha: number; beta: number;
  persistence: number;
  unconditional_variance: number;
  loglik: number; aic: number; bic: number;
  nobs: number;
  cond_variance: number[];           // one per observation
  arch_lm: { statistic: number; p: number; lags: number };   // Engle's test on the demeaned series before fitting
  mean: number;
}

/** Engle's ARCH-LM test: regress e^2 on its own lags, T·R² ~ chi²(lags). */
export function archLM(e: number[], lags = 5): { statistic: number; p: number; lags: number } {
  const sq = e.map((v) => v * v);
  const y: number[] = [], X: number[][] = [];
  for (let t = lags; t < sq.length; t++) { y.push(sq[t]); const row = [1]; for (let l = 1; l <= lags; l++) row.push(sq[t - l]); X.push(row); }
  const fit = ols(y, X);
  const stat = y.length * fit.r2;
  return { statistic: stat, p: chi2UpperP(stat, lags), lags };
}

export function garch11(series: number[]): GarchResult {
  const n = series.length;
  if (n < 60) throw new Error(`GARCH needs 60 or more observations, got ${n}`);
  const mu = mean(series);
  const e = series.map((v) => v - mu);
  const v0 = variance(e, 0);
  const lm = archLM(e, Math.min(5, Math.floor(n / 10)));
  // Parameterise so omega > 0, 0 <= alpha, beta and alpha + beta < 1 without constraints.
  const unpack = (x: number[]) => {
    const a = 1 / (1 + Math.exp(-x[0])), b = 1 / (1 + Math.exp(-x[1]));
    const alpha = 0.999 * a * (1 - b), beta = 0.999 * b;   // alpha + beta < 0.999
    const omega = Math.exp(x[2]);
    return { omega, alpha, beta };
  };
  const negll = (x: number[]) => {
    const { omega, alpha, beta } = unpack(x);
    let h = v0, ll = 0;
    for (let t = 0; t < n; t++) {
      if (t > 0) h = omega + alpha * e[t - 1] * e[t - 1] + beta * h;
      if (!(h > 0) || !Number.isFinite(h)) return 1e12;
      ll += -0.5 * (Math.log(2 * Math.PI) + Math.log(h) + (e[t] * e[t]) / h);
    }
    return -ll;
  };
  // Start at alpha 0.08, beta 0.85, omega = v0 * (1 - 0.93)
  const x0 = [Math.log(0.08 / 0.92 / (1 - 0.85 / 0.999) / 0.999), Math.log(0.85 / (0.999 - 0.85)), Math.log(Math.max(v0 * 0.07, 1e-12))];
  const best = nelderMead(negll, x0, 0.5, 4000);
  const { omega, alpha, beta } = unpack(best);
  const cond: number[] = [];
  let h = v0;
  for (let t = 0; t < n; t++) { if (t > 0) h = omega + alpha * e[t - 1] * e[t - 1] + beta * h; cond.push(h); }
  const ll = -negll(best);
  const k = 4;
  return { omega, alpha, beta, persistence: alpha + beta, unconditional_variance: alpha + beta < 1 ? omega / (1 - alpha - beta) : NaN,
    loglik: ll, aic: -2 * ll + 2 * k, bic: -2 * ll + k * Math.log(n), nobs: n, cond_variance: cond, arch_lm: lm, mean: mu };
}

// ---------------------------------------------------------------------------
// Quantile regression by iteratively reweighted least squares (Schlossmacher)

export function quantileRegress(y: number[], X: number[][], tau: number, iters = 200): { beta: number[]; objective: number; iterations: number } {
  const n = y.length, k = X[0].length;
  let beta = ols(y, X).beta;
  const eps = 1e-6;
  let it = 0, last = Infinity;
  for (; it < iters; it++) {
    const w = y.map((v, i) => { const r = v - X[i].reduce((s, x, j) => s + x * beta[j], 0); const a = r >= 0 ? tau : 1 - tau; return a / Math.max(Math.abs(r), eps); });
    // Weighted least squares: (X'WX) b = X'Wy
    const A: number[][] = Array.from({ length: k }, () => new Array<number>(k).fill(0));
    const b: number[] = new Array<number>(k).fill(0);
    for (let i = 0; i < n; i++) for (let a = 0; a < k; a++) { b[a] += w[i] * X[i][a] * y[i]; for (let c = 0; c < k; c++) A[a][c] += w[i] * X[i][a] * X[i][c]; }
    const inv = inverse(A);
    if (!inv) break;
    const nb = inv.map((row) => row.reduce((s, v, j) => s + v * b[j], 0));
    const obj = y.reduce((s, v, i) => { const r = v - X[i].reduce((q, x, j) => q + x * nb[j], 0); return s + (r >= 0 ? tau * r : (tau - 1) * r); }, 0);
    const moved = nb.reduce((s, v, j) => s + Math.abs(v - beta[j]), 0);
    beta = nb;
    if (moved < 1e-8 || Math.abs(last - obj) < 1e-10) { last = obj; break; }
    last = obj;
  }
  return { beta, objective: last, iterations: it };
}

// ---------------------------------------------------------------------------
// Principal components on standardised series

export interface PcaResult {
  k: number; nobs: number;
  eigenvalues: number[];
  explained: number[];              // share of variance per component
  loadings: number[][];             // [component][variable]
  scores: number[][];               // [t][component]
  correlation: number[][];
}

export function pca(Y: number[][]): PcaResult {
  const T = Y.length, k = Y[0].length;
  if (T < k + 5) throw new Error("Too few observations for the number of series");
  const cols = Array.from({ length: k }, (_, j) => Y.map((r) => r[j]));
  const mu = cols.map(mean), sdv = cols.map((c) => sd(c));
  const Z = Y.map((r) => r.map((v, j) => (sdv[j] ? (v - mu[j]) / sdv[j] : 0)));
  const C = zeros(k, k);
  for (let a = 0; a < k; a++) for (let b = 0; b < k; b++) { let sum = 0; for (let t = 0; t < T; t++) sum += Z[t][a] * Z[t][b]; C[a][b] = sum / (T - 1); }
  const { values, vectors } = symEigen(C);
  const total = values.reduce((s, v) => s + Math.max(v, 0), 0);
  const loadings = values.map((_, c) => vectors.map((row) => row[c]));
  // Sign convention: the largest absolute loading of each component is positive.
  for (const l of loadings) { let m = 0; for (const v of l) if (Math.abs(v) > Math.abs(l[m]) ) m = l.indexOf(v); if (l[m] < 0) for (let j = 0; j < l.length; j++) l[j] = -l[j]; }
  const scores = Z.map((r) => loadings.map((l) => l.reduce((s, v, j) => s + v * r[j], 0)));
  return { k, nobs: T, eigenvalues: values, explained: values.map((v) => (total ? Math.max(v, 0) / total : 0)), loadings, scores, correlation: C };
}


// ---------------------------------------------------------------------------
// Panel regression: pooled, one-way and two-way within (fixed effects), between,
// with standard errors clustered by unit.

export interface PanelFit {
  beta: number[]; se: number[]; t: number[]; p: number[];
  rss: number; r2: number; nobs: number; df: number;
}

export interface PanelResult {
  nobs: number; units: number; periods: number; k: number; balanced: boolean;
  effects: "pooled" | "unit" | "unit_time";
  estimate: PanelFit;            // the requested specification
  pooled: PanelFit;              // always, for comparison
  between: PanelFit | null;      // regression on unit means, when there are enough units
  f_unit_effects: { F: number; p: number; df1: number; df2: number } | null;
  unit_means: Array<{ unit: number; n: number; y: number }>;
}

const groupMeans = (v: number[], g: number[]) => {
  const acc = new Map<number, { s: number; n: number }>();
  for (let i = 0; i < v.length; i++) { const e = acc.get(g[i]) ?? { s: 0, n: 0 }; e.s += v[i]; e.n++; acc.set(g[i], e); }
  return acc;
};

const demean = (v: number[], g: number[]) => { const m = groupMeans(v, g); return v.map((x, i) => x - m.get(g[i])!.s / m.get(g[i])!.n); };

/** Cluster-robust standard errors: sandwich summed over clusters, with the usual finite-sample correction. */
function clusterSe(X: number[][], resid: number[], cluster: number[], dfResid: number): number[] | null {
  const k = X[0].length, n = X.length;
  const XtX = zeros(k, k);
  for (const row of X) for (let a = 0; a < k; a++) for (let b = 0; b < k; b++) XtX[a][b] += row[a] * row[b];
  const inv = inverse(XtX);
  if (!inv) return null;
  const acc = new Map<number, number[]>();
  for (let i = 0; i < n; i++) {
    let a = acc.get(cluster[i]);
    if (!a) { a = new Array<number>(k).fill(0); acc.set(cluster[i], a); }
    for (let j = 0; j < k; j++) a[j] += X[i][j] * resid[i];
  }
  const meat = zeros(k, k);
  for (const a of acc.values()) for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) meat[i][j] += a[i] * a[j];
  const G = acc.size;
  const corr = G > 1 ? (G / (G - 1)) * ((n - 1) / Math.max(dfResid, 1)) : 1;
  const V = matmul(matmul(inv, meat), inv);
  return V.map((_, i) => Math.sqrt(Math.max(V[i][i], 0) * corr));
}

function fitPanel(y: number[], X: number[][], cluster: number[], dfResid: number): PanelFit {
  const fit = ols(y, X);
  const se = clusterSe(X, fit.resid, cluster, dfResid) ?? fit.se;
  const t = fit.beta.map((b, j) => (se[j] ? b / se[j] : NaN));
  return { beta: fit.beta, se, t, p: t.map((v) => tTwoSidedP(v, Math.max(dfResid, 1))), rss: fit.rss, r2: fit.r2, nobs: fit.n, df: dfResid };
}

/**
 * y on X across units and periods. X excludes the intercept: pooled adds one,
 * the within estimators absorb it. Standard errors are clustered by unit throughout,
 * which is what cross-country panels need (shocks are serially correlated within a country).
 */
export function panelRegress(y: number[], X: number[][], unit: number[], time: number[], effects: "pooled" | "unit" | "unit_time" = "unit"): PanelResult {
  const n = y.length, k = X[0].length;
  const units = new Set(unit), periods = new Set(time);
  const G = units.size, Tn = periods.size;
  if (G < 2) throw new Error(`Panel needs 2 or more units, got ${G}`);
  if (n < k + G + 5) throw new Error(`Too few observations (${n}) for ${k} regressors across ${G} units`);
  const cols = Array.from({ length: k }, (_, j) => X.map((r) => r[j]));

  const pooledX = X.map((r) => [1, ...r]);
  const pooled = fitPanel(y, pooledX, unit, n - k - 1);

  let ey = y, eCols = cols, dfWithin = n - G - k;
  if (effects !== "pooled") {
    ey = demean(y, unit); eCols = cols.map((c) => demean(c, unit));
    if (effects === "unit_time") {
      // Sequential demeaning: exact two-way within on a balanced panel, approximate otherwise.
      ey = demean(ey, time);
      eCols = eCols.map((c) => demean(c, time));
      dfWithin = n - G - Tn - k + 1;
    }
  }
  const withinX = ey.map((_, i) => eCols.map((c) => c[i]));
  const estimate = effects === "pooled" ? pooled : fitPanel(ey, withinX, unit, Math.max(dfWithin, 1));

  // Between: one observation per unit, on unit means
  let between: PanelFit | null = null;
  if (G >= k + 3) {
    const my = groupMeans(y, unit);
    const mx = cols.map((c) => groupMeans(c, unit));
    const keys = [...units];
    const by = keys.map((u) => my.get(u)!.s / my.get(u)!.n);
    const bX = keys.map((u) => [1, ...mx.map((m) => m.get(u)!.s / m.get(u)!.n)]);
    try { between = fitPanel(by, bX, keys, G - k - 1); } catch { between = null; }
  }

  // F test for unit effects: pooled vs within residual sums of squares
  let f: PanelResult["f_unit_effects"] = null;
  if (effects !== "pooled" && dfWithin > 0) {
    // Against pooled, one-way absorbs G-1 dummies; two-way absorbs the time dummies as well.
    const df1 = effects === "unit_time" ? (G - 1) + (Tn - 1) : G - 1;
    const df2 = Math.max(dfWithin, 1);
    const F = ((pooled.rss - estimate.rss) / df1) / (estimate.rss / df2);
    if (Number.isFinite(F) && F > 0) f = { F, p: fUpperP(F, df1, df2), df1, df2 };
  }
  const perUnit = [...units].map((u) => { const m = groupMeans(y, unit).get(u)!; return { unit: u, n: m.n, y: m.s / m.n }; });
  return { nobs: n, units: G, periods: Tn, k, balanced: n === G * Tn, effects, estimate, pooled, between, f_unit_effects: f, unit_means: perUnit };
}

// ---------------------------------------------------------------------------
// Forecast evaluation: rolling-origin errors and the Diebold-Mariano test

/** Long-run variance of a series' mean by the Bartlett kernel with `lags` lags (Newey-West on a constant). */
export function longRunVariance(d: number[], lags: number): number {
  const n = d.length, m = mean(d);
  const gamma = (l: number) => { let s = 0; for (let t = l; t < n; t++) s += (d[t] - m) * (d[t - l] - m); return s / n; };
  let v = gamma(0);
  for (let l = 1; l <= lags; l++) v += 2 * (1 - l / (lags + 1)) * gamma(l);
  return Math.max(v, 0);
}

export interface DmResult { statistic: number; p: number; n: number; mean_loss_diff: number; better: 1 | 2 | null; degenerate?: boolean }

/**
 * Diebold-Mariano test of equal predictive accuracy between two h-step forecast error
 * series, squared-error loss, Harvey-Leybourne-Newbold small-sample correction,
 * p-value from t(n-1). A negative statistic favours forecast 1.
 */
export function dieboldMariano(e1: number[], e2: number[], h = 1, loss: "squared" | "absolute" = "squared"): DmResult {
  const L = (e: number) => (loss === "squared" ? e * e : Math.abs(e));
  // Pairs where either forecaster failed (NaN) are dropped, as errorMetrics does.
  const d: number[] = [];
  for (let t = 0; t < Math.min(e1.length, e2.length); t++) if (Number.isFinite(e1[t]) && Number.isFinite(e2[t])) d.push(L(e1[t]) - L(e2[t]));
  const n = d.length;
  if (n < 6) throw new Error(`Diebold-Mariano needs 6 or more paired errors (have ${n})`);
  const md = mean(d);
  const lrv = longRunVariance(d, Math.max(h - 1, 0));
  // A constant loss gap has no sampling variance: one forecaster wins (or ties) at every origin.
  if (lrv <= 1e-18 * Math.max(1, md * md)) return { statistic: md === 0 ? 0 : md < 0 ? -Infinity : Infinity, p: md === 0 ? 1 : 0, n, mean_loss_diff: md, better: md === 0 ? null : md < 0 ? 1 : 2, degenerate: true };
  const dm = md / Math.sqrt(lrv / n);
  const hln = Math.sqrt(Math.max((n + 1 - 2 * h + (h * (h - 1)) / n) / n, 1e-9));
  const stat = dm * hln;
  const p = tTwoSidedP(stat, n - 1);
  return { statistic: stat, p, n, mean_loss_diff: md, better: p < 0.05 ? (md < 0 ? 1 : 2) : null };
}

export interface BacktestErrors {
  /** errors[o][h-1] = actual - forecast for origin o at horizon h, NaN where the forecaster failed */
  errors: number[][];
  /** index in y of the last observation each origin trained on */
  origins: number[];
  failures: number;
}

/**
 * Rolling-origin evaluation. For each origin the forecaster sees y[0..origin] and returns
 * H forecasts, compared with y[origin+1..origin+H]. Origins are the last `nOrigins` points
 * that leave room for a full horizon, spaced `step` apart, so every origin has all H actuals.
 */
export function rollingOrigin(y: number[], forecaster: (train: number[]) => number[], H: number, nOrigins: number, minTrain: number, step = 1): BacktestErrors {
  const n = y.length;
  const last = n - 1 - H;
  const origins: number[] = [];
  for (let o = last; o >= minTrain - 1 && origins.length < nOrigins; o -= step) origins.push(o);
  origins.reverse();
  if (!origins.length) throw new Error(`Too few observations (${n}) for ${nOrigins} origins with horizon ${H} and at least ${minTrain} training points`);
  let failures = 0;
  const errors = origins.map((o) => {
    let f: number[];
    try { f = forecaster(y.slice(0, o + 1)); } catch { failures++; return new Array<number>(H).fill(NaN); }
    return Array.from({ length: H }, (_, h) => (Number.isFinite(f[h]) ? y[o + 1 + h] - f[h] : NaN));
  });
  return { errors, origins, failures };
}

export interface ErrorMetrics { rmse: number; mae: number; mape: number | null; bias: number; n: number }

/** Accuracy metrics over an error vector paired with the actuals it was measured against. */
export function errorMetrics(errors: number[], actuals: number[]): ErrorMetrics {
  const pairs = errors.map((e, i) => [e, actuals[i]] as const).filter(([e]) => Number.isFinite(e));
  const n = pairs.length;
  if (!n) return { rmse: NaN, mae: NaN, mape: null, bias: NaN, n: 0 };
  const rmse = Math.sqrt(pairs.reduce((s, [e]) => s + e * e, 0) / n);
  const mae = pairs.reduce((s, [e]) => s + Math.abs(e), 0) / n;
  const ape = pairs.filter(([, a]) => a !== 0).map(([e, a]) => Math.abs(e / a));
  const mape = ape.length === n ? (ape.reduce((s, x) => s + x, 0) / n) * 100 : null;
  const bias = pairs.reduce((s, [e]) => s + e, 0) / n;
  return { rmse, mae, mape, bias, n };
}

// ---------------------------------------------------------------------------
// Local projections (Jordà 2005)

export interface LpHorizon { h: number; beta: number; se: number; t: number; p: number; n: number; r2: number }
export interface LpResult { horizons: LpHorizon[]; lags: number; shock_sd: number; controls: number }

/**
 * Impulse response of y to x by local projections: for each horizon h, regress y[t+h] on
 * x[t], lags 1..p of y and x (and of any extra controls), and a constant. Standard errors
 * are Newey-West with bandwidth h (the h-step overlap makes the errors MA(h-1) by construction).
 * beta[h] is the response to a one-unit move in x[t]; shock_sd is the standard deviation
 * of x after the same controls, for scaling to a one-sd shock.
 */
export function localProjections(y: number[], x: number[], H: number, p: number, controls: number[][] = []): LpResult {
  const T = y.length;
  if (x.length !== T || controls.some((c) => c.length !== T)) throw new Error("local projections: series lengths differ");
  const k = 2 + p * (2 + controls.length);
  if (T - H - p < k + 8) throw new Error(`Too few observations (${T}) for horizon ${H} with ${p} lags: need at least ${H + p + k + 8}`);
  const row = (t: number): number[] => {
    const r = [1, x[t]];
    for (let l = 1; l <= p; l++) { r.push(y[t - l], x[t - l]); for (const c of controls) r.push(c[t - l]); }
    return r;
  };
  const horizons: LpHorizon[] = [];
  for (let h = 0; h <= H; h++) {
    const X: number[][] = [], yy: number[] = [];
    for (let t = p; t + h < T; t++) { X.push(row(t)); yy.push(y[t + h]); }
    const fit = ols(yy, X);
    const hac = neweyWest(X, fit.resid, fit.XtXinv, h);
    const se = hac.se[1];
    const t = fit.beta[1] / se;
    horizons.push({ h, beta: fit.beta[1], se, t, p: tTwoSidedP(t, fit.n - fit.k), n: fit.n, r2: fit.r2 });
  }
  // Size of a typical shock: sd of x once its own and y's lags are partialled out.
  const X0: number[][] = [], x0: number[] = [];
  for (let t = p; t < T; t++) { const r = row(t); X0.push([r[0], ...r.slice(2)]); x0.push(x[t]); }
  const shockFit = ols(x0, X0);
  return { horizons, lags: p, shock_sd: shockFit.sigma, controls: controls.length };
}

// ---------------------------------------------------------------------------
// Two-stage least squares (instrumental variables)

export interface FirstStage { r2: number; F_excluded: number; F_p: number; df: [number, number]; partial_r2: number }
export interface IvResult {
  n: number; k: number; m: number; L: number;
  beta: number[]; se: number[]; t: number[]; p: number[];
  hac_se: number[]; hac_lag: number;
  resid: number[]; sigma: number; r2: number;
  first_stage: FirstStage[];
  wu_hausman: { F: number; p: number; df: [number, number] };
  sargan: { statistic: number; p: number; df: number } | null;
  ols: OlsResult;
}

/**
 * 2SLS of y on X = [1, endogenous (m columns), exogenous], instrumented by Z = [1, excluded
 * instruments (L columns), the same exogenous]. Standard errors use the structural residuals
 * y - X b, not the second-stage ones. First-stage F is the test of the excluded instruments
 * only (the weak-instrument statistic); Wu-Hausman adds the first-stage residuals to OLS and
 * tests them; Sargan tests over-identifying restrictions when L > m.
 */
export function twoSLS(y: number[], endog: number[][], instruments: number[][], exog: number[][] = [], hacLag?: number): IvResult {
  const n = y.length, m = endog[0].length, L = instruments[0].length, kx = exog.length ? exog[0].length : 0;
  if (L < m) throw new Error(`Under-identified: ${m} endogenous regressor(s) need at least ${m} excluded instrument(s), have ${L}`);
  const X = y.map((_, t) => [1, ...endog[t], ...(kx ? exog[t] : [])]);
  const Z = y.map((_, t) => [1, ...instruments[t], ...(kx ? exog[t] : [])]);
  const Zr = y.map((_, t) => [1, ...(kx ? exog[t] : [])]);   // first stage without the excluded instruments
  const k = X[0].length;
  if (n <= Z[0].length + 2) throw new Error(`Too few observations (${n}) for ${Z[0].length} instruments`);
  const Xhat = X.map((r) => [...r]);
  const firstResid: number[][] = [];
  const first_stage: FirstStage[] = [];
  for (let j = 0; j < m; j++) {
    const col = endog.map((r) => r[j]);
    const u = ols(col, Z), r = ols(col, Zr);
    for (let t = 0; t < n; t++) Xhat[t][1 + j] = u.fitted[t];
    firstResid.push(u.resid);
    const df1 = L, df2 = n - Z[0].length;
    if (u.rss <= 1e-12 * Math.max(r.rss, 1) || u.r2 > 0.9999) throw new Error(`The instruments reproduce endogenous regressor ${j + 1} exactly (first-stage R² of 1): an instrument that is x itself, or a linear transform of it, is not excluded from the equation, so 2SLS collapses to OLS. Use a series that moves x but is not x.`);
    const F = ((r.rss - u.rss) / df1) / (u.rss / df2);
    first_stage.push({ r2: u.r2, F_excluded: F, F_p: fUpperP(F, df1, df2), df: [df1, df2], partial_r2: r.rss ? (r.rss - u.rss) / r.rss : NaN });
  }
  const second = ols(y, Xhat);
  const beta = second.beta;
  const resid = y.map((v, t) => v - X[t].reduce((s, x, j) => s + x * beta[j], 0));
  const rss = resid.reduce((s, e) => s + e * e, 0);
  const df = n - k;
  const sigma2 = rss / df;
  const se = second.XtXinv.map((row, j) => Math.sqrt(Math.max(sigma2 * row[j], 0)));
  const t = beta.map((b, j) => (se[j] ? b / se[j] : NaN));
  const p = t.map((tv) => tTwoSidedP(tv, df));
  const hac = neweyWest(Xhat, resid, second.XtXinv, hacLag);
  const my = mean(y), tss = y.reduce((s, v) => s + (v - my) ** 2, 0);
  // Wu-Hausman: do the first-stage residuals explain y once X is in?
  const aug = ols(y, X.map((r, i) => [...r, ...firstResid.map((fr) => fr[i])]));
  const plain = ols(y, X);
  const whF = ((plain.rss - aug.rss) / m) / (aug.rss / (n - k - m));
  const wu_hausman = { F: whF, p: fUpperP(whF, m, n - k - m), df: [m, n - k - m] as [number, number] };
  let sargan: IvResult["sargan"] = null;
  if (L > m) {
    const s = ols(resid, Z);
    const stat = n * s.r2;
    sargan = { statistic: stat, p: chi2UpperP(stat, L - m), df: L - m };
  }
  return { n, k, m, L, beta, se, t, p, hac_se: hac.se, hac_lag: hac.lag, resid, sigma: Math.sqrt(sigma2), r2: tss ? 1 - rss / tss : NaN, first_stage, wu_hausman, sargan, ols: plain };
}

// ---------------------------------------------------------------------------
// Sup-F critical values and sequential multiple breaks

/**
 * Asymptotic critical values of the sup-Wald statistic (Andrews 1993) with 15% trimming,
 * for k parameters allowed to break, simulated from the k-dimensional Brownian bridge:
 * 60,000 replications on grids of 2,000 and 8,000 points, the 5% and 1% levels extrapolated
 * in 1/sqrt(grid) to remove the discretisation bias (k=1 then reproduces Andrews' published
 * 8.85 and 12.35), the 10% level taken from the finer grid. The sup-F reported by supF is
 * sup-Wald / k, so compare k * F with these.
 */
const SUP_WALD_15 = [
  [7.26, 8.85, 12.33], [10.03, 11.86, 15.62], [12.30, 14.11, 18.30], [14.42, 16.58, 20.97], [16.31, 18.50, 23.13],
];
export function supFCritical(k: number): { "10%": number; "5%": number; "1%": number } {
  if (k < 1 || k > SUP_WALD_15.length) throw new Error(`sup-F critical values are tabulated for 1 to ${SUP_WALD_15.length} breaking parameters, not ${k}`);
  const row = SUP_WALD_15[k - 1];
  return { "10%": row[0] / k, "5%": row[1] / k, "1%": row[2] / k };
}
export function supFReject(F: number, k: number): "1%" | "5%" | "10%" | null {
  const c = supFCritical(k);
  return F > c["1%"] ? "1%" : F > c["5%"] ? "5%" : F > c["10%"] ? "10%" : null;
}

export interface BreakSegment { start: number; end: number; n: number; beta: number[]; mean_y: number }
export interface SequentialBreaksResult { breaks: Array<{ index: number; F: number; reject_at: "1%" | "5%" | "10%" | null }>; segments: BreakSegment[]; k: number; stopped: string }

/**
 * Sequential break detection in the spirit of Bai-Perron: locate the sup-F break in the
 * whole sample; if it clears the 5% Andrews critical value, split there and look for the
 * largest significant sup-F inside any segment; repeat until maxBreaks or nothing
 * significant. Every candidate keeps at least trim * n observations (n the full sample) on
 * either side, so a short remainder is never scanned to its edges.
 */
export function sequentialBreaks(y: number[], X: number[][], maxBreaks: number, trim = 0.15): SequentialBreaksResult {
  const k = X[0].length;
  const breaks: SequentialBreaksResult["breaks"] = [];
  let stopped = "reached max_breaks";
  // Minimum segment length is a share of the whole sample (Bai-Perron's h), not of the current segment.
  const h = Math.max(Math.floor(y.length * trim), k + 3);
  const bounds = () => [0, ...breaks.map((b) => b.index).sort((a, b) => a - b), y.length];
  while (breaks.length < maxBreaks) {
    const bs = bounds();
    let best: { index: number; F: number } | null = null;
    for (let s = 0; s + 1 < bs.length; s++) {
      const lo = bs[s], hi = bs[s + 1];
      if (hi - lo < 2 * h) continue;
      try {
        const r = supF(y.slice(lo, hi), X.slice(lo, hi), trim, h);
        if (supFReject(r.best.F, k) === null || supFReject(r.best.F, k) === "10%") continue;
        if (!best || r.best.F > best.F) best = { index: lo + r.best.break_index, F: r.best.F };
      } catch { /* segment too short */ }
    }
    if (!best) { stopped = breaks.length ? "no further break clears the 5% sup-F critical value" : "no break clears the 5% sup-F critical value"; break; }
    breaks.push({ ...best, reject_at: supFReject(best.F, k) });
  }
  breaks.sort((a, b) => a.index - b.index);
  const bs = bounds();
  const segments: BreakSegment[] = [];
  for (let s = 0; s + 1 < bs.length; s++) {
    const ys = y.slice(bs[s], bs[s + 1]), Xs = X.slice(bs[s], bs[s + 1]);
    let beta: number[];
    try { beta = ols(ys, Xs).beta; } catch { beta = new Array<number>(k).fill(NaN); }
    segments.push({ start: bs[s], end: bs[s + 1] - 1, n: ys.length, beta, mean_y: mean(ys) });
  }
  return { breaks, segments, k, stopped };
}

// ---------------------------------------------------------------------------
// Regression diagnostics

/** Breusch-Pagan (Koenker's studentised form): regress e² on X, n·R² ~ chi²(k-1). */
export function breuschPagan(X: number[][], resid: number[]): { statistic: number; p: number; df: number } {
  const e2 = resid.map((e) => e * e);
  const df = X[0].length - 1;
  if (df < 1) return { statistic: 0, p: 1, df: 0 };
  const fit = ols(e2, X);
  const stat = resid.length * fit.r2;
  return { statistic: stat, p: chi2UpperP(stat, df), df };
}

/** Variance inflation factor of each non-constant column of X (column 0 is the constant). */
export function vif(X: number[][]): number[] {
  const k = X[0].length;
  if (k <= 2) return new Array<number>(k - 1).fill(1);
  return Array.from({ length: k - 1 }, (_, j) => {
    const col = X.map((r) => r[1 + j]);
    const others = X.map((r) => r.filter((_, c) => c !== 1 + j));
    try { const f = ols(col, others); return f.r2 < 1 ? 1 / (1 - f.r2) : Infinity; } catch { return Infinity; }
  });
}

/** Ramsey RESET: add fitted² and fitted³ to the regression; F test on the two. */
export function reset(y: number[], X: number[][], base: OlsResult): { F: number; p: number; df: [number, number] } {
  const fitted = base.fitted;
  const scale = sd(fitted) || 1, m = mean(fitted);
  const z = fitted.map((f) => (f - m) / scale);
  const aug = ols(y, X.map((r, i) => [...r, z[i] ** 2, z[i] ** 3]));
  const df2 = y.length - X[0].length - 2;
  const F = ((base.rss - aug.rss) / 2) / (aug.rss / df2);
  return { F, p: fUpperP(F, 2, df2), df: [2, df2] };
}

// ---------------------------------------------------------------------------
// Structural identification of a VAR: impact matrix B with B B' = Sigma

export type SvarMethod = "cholesky" | "long_run";

/** Gauss-Jordan inverse of a general square matrix; null when singular. */
export function inverseGeneral(A: Mat): Mat | null {
  const n = A.length;
  const M = A.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let c = 0; c < n; c++) {
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    if (Math.abs(M[piv][c]) < 1e-12) return null;
    [M[c], M[piv]] = [M[piv], M[c]];
    const d = M[c][c];
    for (let j = 0; j < 2 * n; j++) M[c][j] /= d;
    for (let r = 0; r < n; r++) if (r !== c) { const f = M[r][c]; if (f) for (let j = 0; j < 2 * n; j++) M[r][j] -= f * M[c][j]; }
  }
  return M.map((r) => r.slice(n));
}

/** Impulse responses, cumulative responses and variance decomposition for a given impact matrix. */
export function structuralResponses(psi: Mat[], B: Mat): { irf: Mat[]; cumulative: Mat[]; fevd: number[][][] } {
  const k = B.length;
  const irf = psi.map((Ps) => matmul(Ps, B));
  const cumulative: Mat[] = [];
  const acc = zeros(k, k);
  for (const h of irf) { for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) acc[i][j] += h[i][j]; cumulative.push(acc.map((r) => [...r])); }
  const fevd: number[][][] = [];
  const cum = zeros(k, k);
  for (const h of irf) {
    for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) cum[i][j] += h[i][j] * h[i][j];
    fevd.push(cum.map((row) => { const tot = row.reduce((a, b) => a + b, 0); return row.map((v) => (tot ? v / tot : 0)); }));
  }
  return { irf, cumulative, fevd };
}

/**
 * Impact matrix by recursive (Cholesky) ordering, or by long-run restrictions (Blanchard-Quah):
 * the long-run multiplier Psi(1) B = (I - A(1))^-1 B is lower triangular, so shock j has no
 * permanent effect on variable i for i < j. Returns B and, for long_run, the long-run matrix.
 */
export function identify(m: VarResult, method: SvarMethod): { B: Mat; long_run: Mat | null } {
  const k = m.k;
  if (method === "cholesky") return { B: cholesky(m.sigma), long_run: null };
  const IminusA = Array.from({ length: k }, (_, i) => Array.from({ length: k }, (__, j) => (i === j ? 1 : 0) - m.a_sum[i][j]));
  const psi1 = inverseGeneral(IminusA);
  if (!psi1) throw new Error("The VAR has a unit root (I - A(1) is singular), so long-run effects are not defined; pass stationary series.");
  const S = matmul(matmul(psi1, m.sigma), transpose(psi1));
  const Ssym = S.map((r, i) => r.map((_, j) => (S[i][j] + S[j][i]) / 2));
  const C = cholesky(Ssym);            // long-run impact matrix, lower triangular
  const B = matmul(IminusA, C);        // Psi(1)^-1 C
  return { B, long_run: C };
}

export interface SignRestriction { shock: number; variable: number; sign: 1 | -1; horizons: number[] }
export interface SignResult { accepted: number; draws: number; irf_median: Mat[]; irf_lo: Mat[]; irf_hi: Mat[]; cumulative_median: Mat[]; fevd_median: number[][][]; B_median_target: Mat }

/** Haar-distributed orthogonal matrix: Gram-Schmidt on Gaussian columns with a positive diagonal. */
function randomOrthogonal(k: number, normal: () => number): Mat {
  const cols: number[][] = [];
  for (let c = 0; c < k; c++) {
    let v = Array.from({ length: k }, normal);
    for (const q of cols) { const d = v.reduce((s, x, i) => s + x * q[i], 0); v = v.map((x, i) => x - d * q[i]); }
    const nrm = Math.sqrt(v.reduce((s, x) => s + x * x, 0)) || 1;
    cols.push(v.map((x) => x / nrm));
  }
  return cols[0].map((_, i) => cols.map((c) => c[i]));   // columns = orthonormal vectors
}

function seededNormal(seed: number): () => number {
  let a = seed >>> 0;
  const u = () => { a += 0x6d2b79f5; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  return () => Math.sqrt(-2 * Math.log(Math.max(u(), 1e-12))) * Math.cos(2 * Math.PI * u());
}

/**
 * Sign-restriction identification (Uhlig 2005, Rubio-Ramirez et al. 2010): draw B = P Q with P
 * the Cholesky factor and Q Haar-distributed, keep the draws whose impulse responses carry the
 * requested signs at the requested horizons (each shock's column may be flipped, since a sign
 * restriction pins the sign of a shock). Reports pointwise median and 16/84% bands over the
 * accepted draws, which measure identification uncertainty, not sampling uncertainty.
 */
export function signIdentify(m: VarResult, restrictions: SignRestriction[], keep = 200, maxDraws = 20000, seed = 1): SignResult {
  const k = m.k;
  if (!restrictions.length) throw new Error("Sign identification needs at least one restriction");
  for (const r of restrictions) if (r.shock < 0 || r.shock >= k || r.variable < 0 || r.variable >= k) throw new Error(`Restriction refers to shock ${r.shock} or variable ${r.variable}, outside 0..${k - 1}`);
  const maxH = Math.max(...restrictions.flatMap((r) => r.horizons));
  if (maxH >= m.psi.length) throw new Error(`Restriction horizon ${maxH} exceeds the response horizon ${m.psi.length - 1}`);
  const P = cholesky(m.sigma);
  const normal = seededNormal(seed);
  const byShock = new Map<number, SignRestriction[]>();
  for (const r of restrictions) byShock.set(r.shock, [...(byShock.get(r.shock) ?? []), r]);
  const accepted: Mat[] = [];
  let draws = 0;
  while (accepted.length < keep && draws < maxDraws) {
    draws++;
    const Q = randomOrthogonal(k, normal);
    const B = matmul(P, Q);
    let ok = true;
    for (const [j, rs] of byShock) {
      const test = (flip: number) => rs.every((r) => r.horizons.every((h) => { let v = 0; for (let c = 0; c < k; c++) v += m.psi[h][r.variable][c] * B[c][j]; return flip * v * r.sign > 0; }));
      if (test(1)) continue;
      if (test(-1)) { for (let c = 0; c < k; c++) B[c][j] = -B[c][j]; continue; }
      ok = false; break;
    }
    if (ok) accepted.push(B);
  }
  if (!accepted.length) throw new Error(`No draw out of ${draws} satisfied the sign restrictions; they may be mutually inconsistent with the data's covariance.`);
  const H = m.psi.length;
  const all = accepted.map((B) => structuralResponses(m.psi, B));
  const q = (vals: number[], p: number) => { const a = [...vals].sort((x, y) => x - y); return a[Math.min(a.length - 1, Math.max(0, Math.floor(p * (a.length - 1))))]; };
  const pick = (f: (r: ReturnType<typeof structuralResponses>) => Mat[], p: number): Mat[] => Array.from({ length: H }, (_, h) => Array.from({ length: k }, (_, i) => Array.from({ length: k }, (_, j) => q(all.map((r) => f(r)[h][i][j]), p))));
  const irf_median = pick((r) => r.irf, 0.5), irf_lo = pick((r) => r.irf, 0.16), irf_hi = pick((r) => r.irf, 0.84);
  const cumulative_median = pick((r) => r.cumulative, 0.5);
  const fevd_median = Array.from({ length: H }, (_, h) => Array.from({ length: k }, (_, i) => Array.from({ length: k }, (_, j) => q(all.map((r) => r.fevd[h][i][j]), 0.5))));
  // The accepted draw closest to the pointwise median (Fry-Pagan), so one coherent model can be quoted.
  let best = 0, bestD = Infinity;
  all.forEach((r, idx) => { let d = 0; for (let h = 0; h < H; h++) for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) { const sc = Math.abs(irf_hi[h][i][j] - irf_lo[h][i][j]) || 1; d += ((r.irf[h][i][j] - irf_median[h][i][j]) / sc) ** 2; } if (d < bestD) { bestD = d; best = idx; } });
  return { accepted: accepted.length, draws, irf_median, irf_lo, irf_hi, cumulative_median, fevd_median, B_median_target: accepted[best] };
}

export interface BootstrapBands { reps: number; lo16: Mat[]; hi84: Mat[]; lo05: Mat[]; hi95: Mat[] }

/**
 * Residual bootstrap for structural impulse responses: resample the centred residuals,
 * rebuild the sample from the first p observations, refit, re-identify. Percentile bands.
 */
export function varBootstrap(Y: number[][], p: number, horizon: number, method: SvarMethod, reps = 200, seed = 7): BootstrapBands {
  const base = varModel(Y, p, horizon);
  const k = base.k, T = Y.length, n = base.nobs;
  const normal = seededNormal(seed);
  let a = (seed * 2654435761) >>> 0;
  const uni = () => { a += 0x6d2b79f5; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  void normal;
  const centred = base.resid.map((e) => { const m = mean(e); return e.map((v) => v - m); });
  const results: Mat[][] = [];
  for (let r = 0; r < reps; r++) {
    const Ys: number[][] = Y.slice(0, p).map((row) => [...row]);
    for (let t = p; t < T; t++) {
      const idx = Math.floor(uni() * n);
      const row = new Array<number>(k).fill(0);
      for (let e = 0; e < k; e++) {
        let v = base.coef[e][0];
        for (let l = 1; l <= p; l++) for (let j = 0; j < k; j++) v += base.coef[e][1 + (l - 1) * k + j] * Ys[t - l][j];
        row[e] = v + centred[e][idx];
      }
      Ys.push(row);
    }
    try {
      const mb = varModel(Ys, p, horizon, { granger: false });
      const { B } = identify(mb, method);
      results.push(structuralResponses(mb.psi, B).irf);
    } catch { /* a degenerate resample: skip */ }
  }
  if (results.length < 20) throw new Error("Bootstrap failed on most resamples");
  const H = horizon + 1;
  const q = (vals: number[], pr: number) => { const s = [...vals].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.floor(pr * (s.length - 1))))]; };
  const pick = (pr: number): Mat[] => Array.from({ length: H }, (_, h) => Array.from({ length: k }, (_, i) => Array.from({ length: k }, (_, j) => q(results.map((irf) => irf[h][i][j]), pr))));
  return { reps: results.length, lo16: pick(0.16), hi84: pick(0.84), lo05: pick(0.05), hi95: pick(0.95) };
}
