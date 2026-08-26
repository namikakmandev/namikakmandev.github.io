// ---- Correlation Check ----
// Is that correlation real? Runs entirely in the browser; no data leaves the page.
// Statistics are a port of scripts/corr_check.py and are validated against it.

/* ============================== statistics ============================== */

function pearson(x, y) {
  const n = x.length;
  if (n < 3) return null;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += x[i]; my += y[i]; }
  mx /= n; my /= n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    const a = x[i] - mx, b = y[i] - my;
    sxy += a * b; sxx += a * a; syy += b * b;
  }
  if (sxx === 0 || syy === 0) return null;
  return sxy / Math.sqrt(sxx * syy);
}

function slope(x, y) {
  const n = x.length;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += x[i]; my += y[i]; }
  mx /= n; my /= n;
  let sxy = 0, sxx = 0;
  for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; }
  return sxx === 0 ? null : sxy / sxx;
}

function tStat(r, n) {
  if (Math.abs(r) >= 1) return Infinity;
  return r * Math.sqrt(n - 2) / Math.sqrt(1 - r * r);
}

// log-gamma, Lanczos — needed by the incomplete beta below
function lgamma(z) {
  const g = [76.18009172947146, -86.50532032941677, 24.01409824083091,
             -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
  let x = z, y = z, tmp = x + 5.5;
  tmp -= (x + 0.5) * Math.log(tmp);
  let ser = 1.000000000190015;
  for (let j = 0; j < 6; j++) ser += g[j] / ++y;
  return -tmp + Math.log(2.5066282746310005 * ser / x);
}

// regularised incomplete beta I_x(a,b), by continued fraction
function betainc(a, b, x) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  if (x > (a + 1) / (a + b + 2)) return 1 - betainc(b, a, 1 - x);
  const lbeta = lgamma(a) + lgamma(b) - lgamma(a + b);
  const front = Math.exp(Math.log(x) * a + Math.log(1 - x) * b - lbeta) / a;
  let f = 1, c = 1, d = 0;
  for (let i = 0; i < 300; i++) {
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

// two-sided p-value for Student's t
function tPValue(t, df) {
  t = Math.abs(t);
  if (!isFinite(t)) return 0;
  if (df <= 0) return 1;
  return betainc(df / 2, 0.5, df / (df + t * t));
}

// confidence interval on r, via Fisher's z transform
function fisherCI(r, n, z) {
  z = z || 1.959964;
  if (n <= 3 || Math.abs(r) >= 1) return null;
  const se = 1 / Math.sqrt(n - 3), zr = Math.atanh(r);
  return [Math.tanh(zr - z * se), Math.tanh(zr + z * se)];
}

// smallest |r| clearing alpha at this sample size
function critR(n, alpha) {
  let lo = 0, hi = 0.999999;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    if (tPValue(tStat(mid, n), n - 2) > alpha) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

function lag1(s) {
  if (s.length < 3) return 0;
  const r = pearson(s.slice(0, -1), s.slice(1));
  return r === null ? 0 : r;
}

// Sample size discounted for autocorrelation (Bartlett / Quenouille).
// 120 monthly observations of a slow-moving series are nowhere near 120
// independent facts. This is what the p-value should really be based on.
function effectiveN(x, y) {
  const prod = lag1(x) * lag1(y);
  if (prod >= 1) return 3;
  return Math.max(3, Math.min(x.length, x.length * (1 - prod) / (1 + prod)));
}

// Percent change is undefined across a sign flip: the denominator passes
// through zero. A margin — a small difference between two large numbers — is
// the usual case, so fall back to absolute differences there.
function crossesZero(s) { return Math.min.apply(null, s) <= 0 && Math.max.apply(null, s) >= 0; }

function change(s, h) {
  h = h || 1;
  const out = [], abs = crossesZero(s);
  for (let i = 0; i + h < s.length; i++) {
    out.push(abs ? s[i + h] - s[i] : (s[i + h] - s[i]) / s[i]);
  }
  return out;
}

// Assumption-free p-value: shuffle one series, count how often luck wins.
// Deterministic seed, so the same data always gives the same answer.
function permPValue(x, y, iters) {
  iters = iters || 2000;
  const obs = Math.abs(pearson(x, y));
  const ys = y.slice();
  let seed = 12345, hits = 0;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let k = 0; k < iters; k++) {
    for (let i = ys.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      const t = ys[i]; ys[i] = ys[j]; ys[j] = t;
    }
    const r = pearson(x, ys);
    if (r !== null && Math.abs(r) >= obs) hits++;
  }
  return (hits + 1) / (iters + 1);
}

// A methodology change shows up as one implausible step. Median absolute
// deviation, so the break cannot widen the threshold that would catch it.
function findBreaks(series, labels, name) {
  const abs = crossesZero(series);           // change() fell back to differences
  const ch = change(series, 1);
  if (ch.length < 8) return [];
  const sorted = ch.slice().sort((a, b) => a - b);
  const med = sorted[Math.floor(sorted.length / 2)];
  const devs = ch.map((c) => Math.abs(c - med)).sort((a, b) => a - b);
  const mad = devs[Math.floor(devs.length / 2)];
  if (mad === 0) return [];
  // the size floor and the label depend on which form change() returned
  const range = Math.max.apply(null, series) - Math.min.apply(null, series);
  const floor = abs ? 0.10 * range : 0.10;
  const fmt = (c) => abs ? (c >= 0 ? "+" : "") + c.toFixed(1) + " (absolute)"
                         : (c >= 0 ? "+" : "") + (c * 100).toFixed(1) + "%";
  const out = [];
  for (let i = 0; i < ch.length; i++) {
    if (Math.abs(ch[i] - med) > 6 * mad && Math.abs(ch[i]) > floor) {
      out.push(name + ": " + labels[i] + " → " + labels[i + 1] + "  " + fmt(ch[i]));
    }
  }
  return out;
}

/* ------------------------- matrix OLS with honest errors ------------------- */

// Solve A b = v for symmetric positive-definite A by Gaussian elimination.
// k is small (predictors + intercept), so no numerical heroics needed.
function solveSym(A, v) {
  const k = v.length;
  const M = A.map((row, i) => row.concat([v[i]]));
  for (let c = 0; c < k; c++) {
    let piv = c;
    for (let r = c + 1; r < k; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    if (Math.abs(M[piv][c]) < 1e-12) return null;               // singular: collinear
    [M[c], M[piv]] = [M[piv], M[c]];
    for (let r = 0; r < k; r++) {
      if (r === c) continue;
      const f = M[r][c] / M[c][c];
      for (let j = c; j <= k; j++) M[r][j] -= f * M[c][j];
    }
  }
  return M.map((row, i) => row[k] / M[i][i]);
}

function invSym(A) {
  const k = A.length, out = [];
  for (let j = 0; j < k; j++) {
    const e = new Array(k).fill(0); e[j] = 1;
    const col = solveSym(A, e);
    if (!col) return null;
    out.push(col);
  }
  // out is columns; transpose to rows (symmetric anyway)
  return out[0].map((_, i) => out.map((c) => c[i]));
}

// OLS of y on any number of predictors, with intercept.
// Reports BOTH classic standard errors and Newey-West (HAC) errors, which stay
// honest when the residuals are autocorrelated - the normal state of affairs
// in time series. The HAC ones drive the p-values shown.
function olsK(Xcols, y) {
  const n = y.length, k = Xcols.length + 1;
  if (n < k + 3) return null;
  const row = (t) => [1].concat(Xcols.map((c) => c[t]));
  // X'X and X'y
  const XtX = Array.from({ length: k }, () => new Array(k).fill(0));
  const Xty = new Array(k).fill(0);
  for (let t = 0; t < n; t++) {
    const x = row(t);
    for (let i = 0; i < k; i++) {
      Xty[i] += x[i] * y[t];
      for (let j = i; j < k; j++) XtX[i][j] += x[i] * x[j];
    }
  }
  for (let i = 0; i < k; i++) for (let j = 0; j < i; j++) XtX[i][j] = XtX[j][i];
  const beta = solveSym(XtX.map((r) => r.slice()), Xty);
  if (!beta) return null;
  const XtXinv = invSym(XtX.map((r) => r.slice()));
  if (!XtXinv) return null;

  const my = y.reduce((a, b) => a + b, 0) / n;
  let sse = 0, sst = 0;
  const resid = new Array(n), fitted = new Array(n);
  for (let t = 0; t < n; t++) {
    const x = row(t);
    let f = 0;
    for (let i = 0; i < k; i++) f += beta[i] * x[i];
    fitted[t] = f; resid[t] = y[t] - f;
    sse += resid[t] * resid[t]; sst += (y[t] - my) ** 2;
  }
  const df = n - k;
  const sigma2 = sse / df;
  const se = beta.map((_, i) => Math.sqrt(Math.max(0, sigma2 * XtXinv[i][i])));

  // Newey-West: sandwich (X'X)^-1 S (X'X)^-1 with Bartlett-weighted
  // autocovariances of the score x_t * e_t. Standard bandwidth rule.
  const L = Math.max(1, Math.floor(4 * Math.pow(n / 100, 2 / 9)));
  const S = Array.from({ length: k }, () => new Array(k).fill(0));
  const score = (t) => { const x = row(t); return x.map((v) => v * resid[t]); };
  for (let t = 0; t < n; t++) {
    const g = score(t);
    for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) S[i][j] += g[i] * g[j];
  }
  for (let l = 1; l <= L; l++) {
    const w = 1 - l / (L + 1);
    for (let t = l; t < n; t++) {
      const g = score(t), h = score(t - l);
      for (let i = 0; i < k; i++) for (let j = 0; j < k; j++)
        S[i][j] += w * (g[i] * h[j] + h[i] * g[j]);
    }
  }
  const tmp = XtXinv.map((r) => {
    return r.map((_, j) => r.reduce((acc, v, m) => acc + v * S[m][j], 0));
  });
  const seNW = beta.map((_, i) => {
    let v = 0;
    for (let m = 0; m < k; m++) v += tmp[i][m] * XtXinv[m][i];
    return Math.sqrt(Math.max(0, v));
  });

  let dwNum = 0;
  for (let t = 1; t < n; t++) dwNum += (resid[t] - resid[t - 1]) ** 2;

  const p = beta.map((b, i) => se[i] > 0 ? tPValue(b / se[i], df) : 1);
  const pNW = beta.map((b, i) => seNW[i] > 0 ? tPValue(b / seNW[i], df) : 1);

  // VIF per predictor (excluding intercept), from the predictor correlation
  // matrix inverse: how much each predictor is explained by the others.
  let vif = null;
  if (Xcols.length >= 2) {
    const kp = Xcols.length;
    const C = Array.from({ length: kp }, () => new Array(kp).fill(0));
    for (let i = 0; i < kp; i++) for (let j = 0; j < kp; j++)
      C[i][j] = i === j ? 1 : (pearson(Xcols[i], Xcols[j]) ?? 0);
    const Cinv = invSym(C.map((r) => r.slice()));
    if (Cinv) vif = Cinv.map((r, i) => r[i]);
  }

  return { beta, se, seNW, p, pNW, nwLags: L,
           r2: sst > 0 ? 1 - sse / sst : 0,
           adjR2: sst > 0 ? 1 - (sse / df) / (sst / (n - 1)) : 0,
           dw: sse > 0 ? dwNum / sse : 2,
           resid, fitted, n, k, vif };
}

/* ------------------------ block bootstrap CI for r -------------------------- */

// Resample the paired series in contiguous blocks, so the autocorrelation
// inside each block survives into the resample. The percentile spread of r
// across resamples is a confidence interval that does not assume independence.
function blockBootstrapCI(x, y, iters, h) {
  const n = x.length;
  if (n < 20) return null;
  iters = iters || 2000;
  // Blocks must be long enough to contain the dependence. Year-on-year
  // changes overlap by h-1 periods by construction, so the block has to
  // span at least 2h or the resample destroys exactly the autocorrelation
  // it exists to preserve, and the interval comes out flattering.
  const b = Math.min(Math.max(2, Math.round(Math.pow(n, 1 / 3)), 2 * (h || 1)),
                     Math.floor(n / 4));
  let seed = 987654321;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const rs = [];
  for (let it = 0; it < iters; it++) {
    const bx = [], by = [];
    while (bx.length < n) {
      const start = Math.floor(rnd() * (n - b + 1));
      for (let j = 0; j < b && bx.length < n; j++) { bx.push(x[start + j]); by.push(y[start + j]); }
    }
    const r = pearson(bx, by);
    if (r !== null) rs.push(r);
  }
  if (rs.length < 100) return null;
  rs.sort((a, c) => a - c);
  return { lo: rs[Math.floor(rs.length * 0.025)],
           hi: rs[Math.floor(rs.length * 0.975)],
           blockLen: b, iters: rs.length };
}

/* --------------------- Engle-Granger cointegration test --------------------- */

// Augmented Dickey-Fuller t-statistic on a series, no constant (used on
// regression residuals, which are mean zero by construction).
function adfStat(u, lags) {
  const n = u.length;
  const du = [];
  for (let t = 1; t < n; t++) du.push(u[t] - u[t - 1]);
  const T = du.length - lags;
  if (T < 10) return null;
  const yv = [], cols = [[]];
  for (let l = 0; l < lags; l++) cols.push([]);
  for (let t = lags; t < du.length; t++) {
    yv.push(du[t]);
    cols[0].push(u[t]);                       // u_{t-1} relative to du index
    for (let l = 1; l <= lags; l++) cols[l].push(du[t - l]);
  }
  // no-constant OLS: strip the intercept by demeaning nothing - build manually
  const k = cols.length;
  const XtX = Array.from({ length: k }, () => new Array(k).fill(0));
  const Xty = new Array(k).fill(0);
  for (let t = 0; t < yv.length; t++) {
    for (let i = 0; i < k; i++) {
      Xty[i] += cols[i][t] * yv[t];
      for (let j = i; j < k; j++) XtX[i][j] += cols[i][t] * cols[j][t];
    }
  }
  for (let i = 0; i < k; i++) for (let j = 0; j < i; j++) XtX[i][j] = XtX[j][i];
  const beta = solveSym(XtX.map((r) => r.slice()), Xty);
  const XtXinv = invSym(XtX.map((r) => r.slice()));
  if (!beta || !XtXinv) return null;
  let sse = 0;
  for (let t = 0; t < yv.length; t++) {
    let f = 0;
    for (let i = 0; i < k; i++) f += beta[i] * cols[i][t];
    sse += (yv[t] - f) ** 2;
  }
  const sig2 = sse / (yv.length - k);
  const seb = Math.sqrt(Math.max(1e-300, sig2 * XtXinv[0][0]));
  return beta[0] / seb;
}

// Two series cointegrate when a linear combination of their LEVELS is
// stationary - they are tied together long-run even though each one trends.
// That is the one honest exception to "do not trust a levels correlation".
// Critical values: MacKinnon (1991) response surface for the two-variable
// case with a constant in the cointegrating regression. Finite-sample:
// CV(T) = b_inf + b1/T + b2/T^2, more negative for short samples.
function egCrit(T) {
  const rs = { p01: [-3.9001, -10.534, -30.03],
               p05: [-3.3377, -5.967, -8.98],
               p10: [-3.0462, -4.069, -5.73] };
  const out = {};
  for (const k in rs) out[k] = rs[k][0] + rs[k][1] / T + rs[k][2] / (T * T);
  return out;
}

function engleGranger(x, y) {
  if (x.length < 30) return null;
  const b = slope(x, y);
  if (b === null) return null;
  const my = y.reduce((a, c) => a + c, 0) / y.length;
  const mx = x.reduce((a, c) => a + c, 0) / x.length;
  const a = my - b * mx;
  const u = x.map((v, t) => y[t] - (a + b * v));
  const tau = adfStat(u, 1);
  if (tau === null) return null;
  const crit = egCrit(x.length);
  // Tiered on purpose: a bare 5% pass is the level at which 1 in 20 pairs of
  // unrelated random walks also passes, so it is reported as borderline,
  // never as a finding.
  const verdict = tau < crit.p01 ? "strong" : tau < crit.p05 ? "borderline" : "none";
  return { tau, crit, verdict, cointegrated: verdict === "strong" };
}

/* ------------------------- regression & robustness ------------------------- */

// OLS of y on x with intercept. Standard errors both naive and discounted for
// autocorrelation via the same effective-n used for correlation, so the
// regression cannot claim confidence the correlation was already denied.
function ols(x, y) {
  const n = x.length;
  if (n < 4) return null;
  const b = slope(x, y);
  if (b === null) return null;
  let mx = 0, my = 0;
  for (let i = 0; i < n; i++) { mx += x[i]; my += y[i]; }
  mx /= n; my /= n;
  const a = my - b * mx;
  let sse = 0, sst = 0, sxx = 0;
  const resid = new Array(n);
  for (let i = 0; i < n; i++) {
    const e = y[i] - (a + b * x[i]);
    resid[i] = e; sse += e * e; sst += (y[i] - my) ** 2; sxx += (x[i] - mx) ** 2;
  }
  const df = n - 2;
  const seB = Math.sqrt(sse / df / sxx);
  const nEff = effectiveN(x, y), dfAdj = Math.max(1, nEff - 2);
  const seBAdj = seB * Math.sqrt(df / dfAdj);        // fewer real facts, wider error
  const t = seB > 0 ? b / seB : Infinity;
  const tAdj = seBAdj > 0 ? b / seBAdj : Infinity;
  // Durbin-Watson: ~2 means independent residuals; near 0, they trend together
  let dwNum = 0;
  for (let i = 1; i < n; i++) dwNum += (resid[i] - resid[i - 1]) ** 2;
  const dw = sse > 0 ? dwNum / sse : 2;
  const tcrit = 1.96 * Math.sqrt(df / dfAdj);        // rough, matched to seBAdj
  return {
    a: a, b: b, n: n, nEff: nEff, r2: sst > 0 ? 1 - sse / sst : 0,
    seB: seB, seBAdj: seBAdj,
    p: tPValue(t, df), pAdj: tPValue(tAdj, dfAdj),
    ciB: [b - 1.96 * seBAdj, b + 1.96 * seBAdj],
    dw: dw, resid: resid,
    fitted: x.map((v) => a + b * v),
  };
}

// Two-predictor OLS: y on x controlling for z. This answers the question
// correlation cannot: does x still matter once z is held constant?
function ols2(x, z, y) {
  const n = y.length;
  if (n < 5) return null;
  const mean = (s) => s.reduce((t, v) => t + v, 0) / n;
  const mx = mean(x), mz = mean(z), my = mean(y);
  let sxx = 0, szz = 0, sxz = 0, sxy = 0, szy = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - mx, dz = z[i] - mz, dy = y[i] - my;
    sxx += dx * dx; szz += dz * dz; sxz += dx * dz; sxy += dx * dy; szy += dz * dy;
  }
  const det = sxx * szz - sxz * sxz;
  if (Math.abs(det) < 1e-12) return null;            // x and z collinear
  const bx = (szz * sxy - sxz * szy) / det;
  const bz = (sxx * szy - sxz * sxy) / det;
  const a = my - bx * mx - bz * mz;
  let sse = 0, sst = 0;
  for (let i = 0; i < n; i++) {
    const e = y[i] - (a + bx * x[i] + bz * z[i]);
    sse += e * e; sst += (y[i] - my) ** 2;
  }
  const df = n - 3;
  const seBx = df > 0 ? Math.sqrt(sse / df * szz / det) : Infinity;
  return { a: a, bx: bx, bz: bz, seBx: seBx,
           p: tPValue(seBx > 0 ? bx / seBx : Infinity, df),
           r2: sst > 0 ? 1 - sse / sst : 0 };
}

// Partial correlation of x and y with z held constant.
function partialR(x, y, z) {
  const rxy = pearson(x, y), rxz = pearson(x, z), ryz = pearson(y, z);
  if (rxy === null || rxz === null || ryz === null) return null;
  const den = Math.sqrt((1 - rxz * rxz) * (1 - ryz * ryz));
  return den > 0 ? (rxy - rxz * ryz) / den : null;
}

// Spearman rank correlation. Far from Pearson => nonlinear or outlier-driven.
function spearman(x, y) {
  const rank = (s) => {
    const idx = s.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
    const rk = new Array(s.length);
    let i = 0;
    while (i < idx.length) {
      let j = i;
      while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
      const avg = (i + j) / 2 + 1;                    // average rank over ties
      for (let k = i; k <= j; k++) rk[idx[k][1]] = avg;
      i = j + 1;
    }
    return rk;
  };
  return pearson(rank(x), rank(y));
}

// Drop each point once; report how far r can be moved by one observation.
function influence(x, y) {
  const full = pearson(x, y);
  if (full === null || x.length < 6) return null;
  let worst = 0, at = -1;
  for (let i = 0; i < x.length; i++) {
    const xs = x.slice(0, i).concat(x.slice(i + 1));
    const ys = y.slice(0, i).concat(y.slice(i + 1));
    const r = pearson(xs, ys);
    if (r !== null && Math.abs(r - full) > worst) { worst = Math.abs(r - full); at = i; }
  }
  return { full: full, maxShift: worst, index: at };
}

// r in each half of the sample. A finding that lives in only one half is a period.
function splitHalf(x, y) {
  const m = Math.floor(x.length / 2);
  if (m < 5) return null;
  return { first: pearson(x.slice(0, m), y.slice(0, m)),
           second: pearson(x.slice(m), y.slice(m)) };
}

// Fit on the first 70%, score on the last 30%. R2 out of sample can be
// negative: the model does worse than guessing the mean. That is a verdict.
function outOfSample(x, y) {
  const cut = Math.floor(x.length * 0.7);
  if (cut < 6 || x.length - cut < 4) return null;
  const fit = ols(x.slice(0, cut), y.slice(0, cut));
  if (!fit) return null;
  const hold = y.slice(cut), mh = hold.reduce((t, v) => t + v, 0) / hold.length;
  let sse = 0, sst = 0;
  for (let i = cut; i < x.length; i++) {
    sse += (y[i] - (fit.a + fit.b * x[i])) ** 2;
    sst += (y[i] - mh) ** 2;
  }
  return { r2: sst > 0 ? 1 - sse / sst : 0, nTrain: cut, nTest: x.length - cut };
}

// One row of the results table.
function describe(label, x, y) {
  const r = pearson(x, y);
  if (r === null) return null;
  const n = x.length, nEff = effectiveN(x, y);
  return {
    label: label, n: n, r: r, r2: r * r, nEff: nEff,
    p: tPValue(tStat(r, n), n - 2),
    pAdj: nEff > 3 ? tPValue(tStat(r, nEff), nEff - 2) : 1,
    ci: fisherCI(r, Math.round(nEff)),
    sig: (nEff > 3 ? tPValue(tStat(r, nEff), nEff - 2) : 1) < 0.05,
  };
}

// r at every lag from -span to +span. Positive lag = X leads Y.
function scanLags(xs, ys, span, h) {
  const dx = change(xs, h), dy = change(ys, h), rows = [];
  const at = (a, b, L) => {
    const p = L >= 0 ? a.slice(0, a.length - L || undefined) : a.slice(-L);
    const q = L >= 0 ? b.slice(L) : b.slice(0, L);
    return p.length >= 10 ? { r: pearson(p, q), n: p.length } : null;
  };
  for (let L = -span; L <= span; L++) {
    const lv = at(xs, ys, L), cg = at(dx, dy, L);
    if (!lv || !cg || lv.r === null || cg.r === null) continue;
    rows.push({ lag: L, levels: lv.r, changes: cg.r, n: cg.n });
  }
  if (!rows.length) return null;
  const zero = rows.find((d) => d.lag === 0);
  let best = rows[0];
  for (const d of rows) if (Math.abs(d.changes) > Math.abs(best.changes)) best = d;
  // The peak was SELECTED from many lags. Testing k lags and keeping the best
  // inflates significance, so the threshold has to rise to match.
  const k = rows.length, alpha = 0.05 / k;
  const pPeak = tPValue(tStat(best.changes, best.n), best.n - 2);
  const gain = zero ? Math.abs(best.changes) - Math.abs(zero.changes) : null;
  let verdict;
  if (!zero) verdict = "";
  else if (best.lag === 0) verdict = "Peak is at lag 0. There is no lead here — the series move together.";
  else if (pPeak > alpha) verdict = "Peak does not survive testing " + k + " lags. Treat it as noise, not a lead.";
  else if (gain < 0.05) verdict = "Survives, but the gain of " + gain.toFixed(3) + " over lag 0 is noise. Not a lead.";
  else if (gain < 0.10) verdict = "Survives, but marginal. No lead without a stated mechanism.";
  else verdict = "Survives, gain " + gain.toFixed(3) + ". Worth investigating, with a mechanism.";
  return { rows: rows, zero: zero, best: best, gain: gain, k: k,
           alpha: alpha, pPeak: pPeak, crit: critR(best.n, alpha), verdict: verdict };
}

const CC_API = { pearson, slope, tPValue, tStat, fisherCI, critR, effectiveN,
                 crossesZero, change, permPValue, findBreaks, describe, scanLags, lag1,
                 ols, ols2, partialR, spearman, influence, splitHalf, outOfSample,
                 olsK, blockBootstrapCI, engleGranger, adfStat, solveSym, invSym };
if (typeof module !== "undefined" && module.exports) module.exports = CC_API;
if (typeof window !== "undefined") window.CC = CC_API;
