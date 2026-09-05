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
  for (let l = 0; l <= L; l++) {
    const w = l === 0 ? 1 : 1 - l / (L + 1);
    for (let t = l; t < n; t++) {
      for (let a = 0; a < k; a++) for (let b = 0; b < k; b++) {
        const term = g[t][a] * g[t - l][b];
        S[a][b] += w * (l === 0 ? term : term + g[t - l][a] * g[t][b]);
      }
    }
  }
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
    if (rows.length <= rows[0].length + 2) continue;
    try {
      const fit = ols(target, rows);
      if (fit.aic < best.aic) best = { p, aic: fit.aic, fit };
    } catch { /* singular at this lag; skip */ }
  }
  if (!best.fit) throw new Error("ADF regression could not be estimated");
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

/** Quandt-Andrews sup-F scan over the middle (1 - 2*trim) of the sample. Critical values differ from F; treat as a locator. */
export function supF(y: number[], X: number[][], trim = 0.15): { best: ChowResult; scan: Array<{ index: number; F: number }> } {
  const n = y.length, lo = Math.max(Math.floor(n * trim), X[0].length + 2), hi = Math.min(Math.ceil(n * (1 - trim)), n - X[0].length - 2);
  let best: ChowResult | null = null;
  const scan: Array<{ index: number; F: number }> = [];
  for (let b = lo; b <= hi; b++) {
    try {
      const r = chow(y, X, b);
      scan.push({ index: b, F: r.F });
      if (!best || r.F > best.F) best = r;
    } catch { /* skip */ }
  }
  if (!best) throw new Error("No admissible break points");
  return { best, scan };
}
