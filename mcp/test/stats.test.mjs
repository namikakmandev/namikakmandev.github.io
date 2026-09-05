// Numeric checks against known answers. Run: node test/stats.test.mjs (after npm run build)
import assert from "node:assert/strict";
import * as S from "../dist/stats.js";

let failures = 0;
function check(name, fn) {
  try { fn(); console.log("ok   ", name); }
  catch (e) { failures++; console.log("FAIL ", name, "\n     ", e.message.split("\n")[0]); }
}
const close = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg ?? ""} got ${a}, want ${b} ± ${tol}`);

// Seeded PRNG so failures reproduce.
function rng(seed) {
  let a = seed >>> 0;
  const u = () => { a += 0x6d2b79f5; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const normal = () => { const u1 = Math.max(u(), 1e-12), u2 = u(); return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2); };
  return { u, normal };
}

check("t, F, chi2 and normal p-values match tables", () => {
  close(S.tTwoSidedP(2.228, 10), 0.05, 0.001, "t(10) two-sided 5% point");
  close(S.tTwoSidedP(1.96, 1e6), 0.05, 0.001, "t -> normal");
  close(S.fUpperP(3.49, 2, 20), 0.05, 0.002, "F(2,20) 5% point");
  close(S.chi2UpperP(3.841, 1), 0.05, 0.001, "chi2(1) 5% point");
  close(S.chi2UpperP(5.991, 2), 0.05, 0.001, "chi2(2) 5% point");
  close(S.normalCdf(1.96), 0.975, 0.0005, "Phi(1.96)");
});

check("OLS recovers known coefficients and reports sensible fit", () => {
  const r = rng(1);
  const n = 400;
  const x1 = Array.from({ length: n }, () => r.normal()), x2 = Array.from({ length: n }, () => r.normal());
  const y = x1.map((v, i) => 1.5 + 2 * v - 0.5 * x2[i] + 0.3 * r.normal());
  const fit = S.ols(y, x1.map((v, i) => [1, v, x2[i]]));
  close(fit.beta[0], 1.5, 0.06, "const"); close(fit.beta[1], 2, 0.06, "b1"); close(fit.beta[2], -0.5, 0.06, "b2");
  assert.ok(fit.r2 > 0.95 && fit.p[1] < 1e-6 && fit.F_p < 1e-6);
  const hac = S.neweyWest(x1.map((v, i) => [1, v, x2[i]]), fit.resid, fit.XtXinv);
  assert.ok(hac.se.every((s, j) => s > 0 && Math.abs(s / fit.se[j] - 1) < 0.5), "HAC se same order as OLS se on iid data");
});

check("ADF: rejects for white noise, does not reject for a random walk", () => {
  const r = rng(7);
  const wn = Array.from({ length: 300 }, () => r.normal());
  const rw = [0]; for (let i = 1; i < 300; i++) rw.push(rw[i - 1] + r.normal());
  const a = S.adf(wn, "c"), b = S.adf(rw, "c");
  assert.equal(a.reject_unit_root_at, "1%", `white noise stat ${a.statistic}`);
  assert.equal(b.reject_unit_root_at, null, `random walk stat ${b.statistic}`);
  close(S.adfCritical("c", 1e9)["5%"], -2.86, 0.01, "asymptotic 5% cv with constant");
});

check("Engle-Granger: cointegrated pair detected, independent random walks not", () => {
  const r = rng(11);
  const x = [0]; for (let i = 1; i < 400; i++) x.push(x[i - 1] + r.normal());
  const y = x.map((v) => 3 + 2 * v + 0.5 * r.normal());
  const eg = S.engleGranger(y, x);
  close(eg.beta[1], 2, 0.05, "cointegrating slope");
  assert.ok(eg.cointegrated_at !== null, `stat ${eg.residual_adf.statistic}`);
  const z = [0]; for (let i = 1; i < 400; i++) z.push(z[i - 1] + r.normal());
  const eg2 = S.engleGranger(z, x);
  assert.equal(eg2.cointegrated_at, null, `independent walks stat ${eg2.residual_adf.statistic}`);
});

check("Granger: x -> y detected, y -> x not", () => {
  const r = rng(3);
  const n = 400;
  const x = Array.from({ length: n }, () => r.normal());
  const y = [0];
  for (let t = 1; t < n; t++) y.push(0.5 * y[t - 1] + 0.8 * x[t - 1] + 0.5 * r.normal());
  const xy = S.granger(y, x, 2), yx = S.granger(x, y, 2);
  assert.ok(xy.p < 1e-6, `x->y p=${xy.p}`);
  assert.ok(yx.p > 0.05, `y->x p=${yx.p}`);
});

check("cross-correlation peaks at the true lead", () => {
  const r = rng(5);
  const x = Array.from({ length: 300 }, () => r.normal());
  const y = x.map((_, t) => (t >= 3 ? x[t - 3] : 0) + 0.3 * r.normal());
  const cc = S.crossCorrelation(x, y, 6);
  const best = cc.reduce((a, b) => (b.r > a.r ? b : a));
  assert.equal(best.lag, 3, `peak at lag ${best.lag}`);
});

check("HP filter solves its system exactly and tracks a linear trend", () => {
  const r = rng(9);
  const n = 120, lambda = 129600;
  const y = Array.from({ length: n }, (_, t) => 10 + 0.5 * t + r.normal());
  const { trend, cycle } = S.hpFilter(y, lambda);
  // Verify (I + lambda K'K) tau = y directly
  for (let i = 0; i < n; i++) {
    let v = trend[i];
    const d2 = (j) => (j >= 0 && j + 2 < n ? trend[j] - 2 * trend[j + 1] + trend[j + 2] : 0);
    // (K'K tau)_i = d2(i-2) - 2 d2(i-1) + d2(i)
    v += lambda * (d2(i - 2) - 2 * d2(i - 1) + d2(i));
    close(v, y[i], 1e-6 * Math.max(1, Math.abs(y[i])), `row ${i}`);
  }
  const slope = (trend[n - 1] - trend[0]) / (n - 1);
  close(slope, 0.5, 0.05, "trend slope");
  close(S.mean(cycle), 0, 0.2, "cycle mean");
});

check("decomposition recovers seasonal factors", () => {
  const r = rng(2);
  const period = 12, n = 96;
  const season = [3, 2, 1, 0, -1, -2, -3, -2, -1, 0, 1, 2];
  const y = Array.from({ length: n }, (_, t) => 50 + 0.2 * t + season[t % period] + 0.2 * r.normal());
  const d = S.decompose(y, period);
  for (let i = 0; i < period; i++) close(d.seasonal_factors[i], season[i], 0.3, `factor ${i}`);
  assert.ok(d.seasonal_strength > 0.9, `strength ${d.seasonal_strength}`);
});

check("Holt-Winters forecasts continue trend and season", () => {
  const period = 12, n = 72;
  const season = [3, 2, 1, 0, -1, -2, -3, -2, -1, 0, 1, 2];
  const y = Array.from({ length: n }, (_, t) => 50 + 0.2 * t + season[t % period]);
  const hw = S.holtWinters(y, 12, period);
  const truth = Array.from({ length: 12 }, (_, i) => 50 + 0.2 * (n + i) + season[(n + i) % period]);
  const mape = S.mean(hw.forecast.map((f, i) => Math.abs(f - truth[i]) / truth[i]));
  assert.ok(mape < 0.02, `mape ${mape}`);
  assert.equal(typeof hw.gamma, "number");
});

check("AR(2) forecast runs and finds the coefficients", () => {
  const r = rng(4);
  const y = [0, 0];
  for (let t = 2; t < 500; t++) y.push(1 + 0.6 * y[t - 1] - 0.2 * y[t - 2] + r.normal());
  const ar = S.arForecast(y, 2, 6);
  close(ar.coef[1], 0.6, 0.1, "phi1"); close(ar.coef[2], -0.2, 0.1, "phi2");
  assert.equal(ar.forecast.length, 6);
});

check("Chow and sup-F locate a break", () => {
  const r = rng(8);
  const n = 200;
  const y = Array.from({ length: n }, (_, t) => (t < 120 ? 10 : 14) + 0.3 * r.normal());
  const X = y.map(() => [1]);
  const c = S.chow(y, X, 120);
  assert.ok(c.p < 1e-6);
  const s = S.supF(y, X);
  assert.ok(Math.abs(s.best.break_index - 120) <= 2, `located at ${s.best.break_index}`);
});

check("descriptives: Ljung-Box and Jarque-Bera behave", () => {
  const r = rng(6);
  const wn = Array.from({ length: 500 }, () => r.normal());
  assert.ok(S.ljungBox(wn, 10).p > 0.01);
  assert.ok(S.jarqueBera(wn).p > 0.01);
  const ar = [0]; for (let i = 1; i < 500; i++) ar.push(0.8 * ar[i - 1] + r.normal());
  assert.ok(S.ljungBox(ar, 10).p < 1e-6);
});

console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
