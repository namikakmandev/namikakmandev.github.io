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


check("KPSS: does not reject for white noise, rejects for a random walk", () => {
  const r = rng(21);
  const wn = Array.from({ length: 300 }, () => r.normal());
  const rw = [0]; for (let i = 1; i < 300; i++) rw.push(rw[i - 1] + r.normal());
  assert.equal(S.kpss(wn, "c").reject_stationarity_at, null, `wn stat ${S.kpss(wn, "c").statistic}`);
  assert.ok(S.kpss(rw, "c").reject_stationarity_at !== null, `rw stat ${S.kpss(rw, "c").statistic}`);
});

check("symmetric eigen solver matches a known 2x2", () => {
  const { values, vectors } = S.symEigen([[2, 1], [1, 2]]);
  close(values[0], 3, 1e-9); close(values[1], 1, 1e-9);
  close(Math.abs(vectors[0][0]), Math.SQRT1_2, 1e-6);
});

check("Johansen: rank 1 for a cointegrated triple, rank 0 for independent walks", () => {
  const r = rng(31);
  const n = 400;
  const w1 = [0], w2 = [0]; for (let i = 1; i < n; i++) { w1.push(w1[i - 1] + r.normal()); w2.push(w2[i - 1] + r.normal()); }
  // y3 = 2*w1 - w2 + stationary noise -> one cointegrating relation among (w1, w2, y3)
  const y3 = w1.map((v, i) => 2 * v - w2[i] + 0.5 * r.normal());
  const Y = w1.map((_, i) => [w1[i], w2[i], y3[i]]);
  const j = S.johansen(Y, 1);
  assert.equal(j.rank_at_5pct, 1, JSON.stringify(j.trace.map((t) => [t.r, +t.statistic.toFixed(1), t.critical["5%"]])));
  const w3 = [0]; for (let i = 1; i < n; i++) w3.push(w3[i - 1] + r.normal());
  const j0 = S.johansen(w1.map((_, i) => [w1[i], w2[i], w3[i]]), 1);
  assert.equal(j0.rank_at_5pct, 0, JSON.stringify(j0.trace.map((t) => +t.statistic.toFixed(1))));
});

check("VECM: recovers the long-run vector and puts the adjustment on the dependent series", () => {
  const r = rng(53);
  const n = 500;
  const x = [0]; for (let i = 1; i < n; i++) x.push(x[i - 1] + r.normal());
  // y = 2x + u, u AR(1) with 0.5 persistence: y adjusts toward 2x, x is a pure random walk (weakly exogenous)
  const y = []; let u = 0;
  for (let i = 0; i < n; i++) { u = 0.5 * u + r.normal(); y.push(2 * x[i] + u); }
  const Y = y.map((v, i) => [v, x[i]]);
  const m = S.vecm(Y, 1);
  assert.equal(m.rank, 1);
  close(m.beta[1][0], -2, 0.15, "beta on x");
  assert.ok(m.alpha[0][0] < -0.2 && m.alpha_p[0][0] < 0.01, `alpha_y ${m.alpha[0][0]} p ${m.alpha_p[0][0]}`);
  assert.ok(Math.abs(m.alpha[1][0]) < 0.15, `alpha_x ${m.alpha[1][0]} should be near zero`);
  assert.equal(m.ect.length, n);
  assert.throws(() => S.vecm(Y, 1, 2), /below the number of series/);
});

check("GARCH(1,1): recovers persistence on simulated data, ARCH-LM detects clustering", () => {
  const r = rng(71);
  const n = 1500;
  const e = []; let h = 1;
  for (let t = 0; t < n; t++) { h = 0.05 + 0.1 * (t ? e[t - 1] ** 2 : 1) + 0.85 * h; e.push(Math.sqrt(h) * r.normal()); }
  const g = S.garch11(e);
  assert.ok(g.arch_lm.p < 0.01, `ARCH-LM p ${g.arch_lm.p}`);
  close(g.persistence, 0.95, 0.06, "persistence");
  assert.ok(g.alpha > 0.03 && g.alpha < 0.2, `alpha ${g.alpha}`);
  assert.equal(g.cond_variance.length, n);
  const white = Array.from({ length: 400 }, () => r.normal());
  assert.ok(S.archLM(white, 5).p > 0.05, "white noise should show no ARCH");
});

check("quantile regression: median slope near truth, tails differ under heteroskedastic noise", () => {
  const r = rng(83);
  const n = 800;
  const x = Array.from({ length: n }, () => 5 + 2 * r.normal());
  const y = x.map((v) => 1 + 2 * v + (0.5 + 0.4 * Math.abs(v - 5)) * r.normal());
  const X = x.map((v) => [1, v]);
  const med = S.quantileRegress(y, X, 0.5);
  close(med.beta[1], 2, 0.15, "median slope");
  close(med.beta[0], 1, 0.6, "median intercept");
  const lo = S.quantileRegress(y, X, 0.1), hi = S.quantileRegress(y, X, 0.9);
  assert.ok(lo.beta[0] < med.beta[0] && med.beta[0] < hi.beta[0], "intercepts ordered across quantiles");
});

check("PCA: one common factor explains most variance and loads on every series", () => {
  const r = rng(97);
  const n = 300;
  const f = Array.from({ length: n }, () => r.normal());
  const Y = f.map((v) => [v + 0.3 * r.normal(), 0.8 * v + 0.3 * r.normal(), -0.9 * v + 0.3 * r.normal()]);
  const p = S.pca(Y);
  assert.ok(p.explained[0] > 0.8, `first component ${p.explained[0]}`);
  assert.ok(p.loadings[0].every((l) => Math.abs(l) > 0.4));
  assert.ok(Math.sign(p.loadings[0][0]) !== Math.sign(p.loadings[0][2]), "third series loads with opposite sign");
  assert.equal(p.scores.length, n);
});

check("panel regression: within recovers the true slope where pooled OLS flips its sign", () => {
  const r = rng(101);
  const G = 10, T = 20;
  const y = [], X = [], unit = [], time = [];
  for (let i = 0; i < G; i++) for (let t = 0; t < T; t++) {
    const x = 5 * i + 0.2 * t + 0.3 * r.normal();          // richer countries have higher x
    y.push(-10 * i + 1.0 * x + 0.3 * r.normal());          // but a large negative country effect
    X.push([x]); unit.push(i); time.push(t);
  }
  const p = S.panelRegress(y, X, unit, time, "unit");
  close(p.estimate.beta[0], 1.0, 0.05, "within slope");
  assert.ok(p.pooled.beta[1] < 0, `pooled slope ${p.pooled.beta[1]} should flip sign`);
  assert.ok(p.f_unit_effects && p.f_unit_effects.p < 0.001, "country effects should be significant");
  assert.equal(p.units, G); assert.equal(p.periods, T); assert.ok(p.balanced);
  assert.ok(p.estimate.se[0] > 0 && p.estimate.p[0] < 0.01, "clustered se should still be significant");

  // A common year shock is absorbed by two-way effects
  const y2 = y.map((v, idx) => v + 4 * Math.sin(time[idx] / 2));
  const two = S.panelRegress(y2, X, unit, time, "unit_time");
  close(two.estimate.beta[0], 1.0, 0.08, "two-way slope with a global shock");
});

check("VAR(1): recovers coefficients, Granger direction and decaying impulse responses", () => {
  const r = rng(41);
  const n = 500;
  const y = [[0, 0]];
  for (let t = 1; t < n; t++) {
    const [a, b] = y[t - 1];
    y.push([0.5 * a + 0.3 * b + 0.5 * r.normal(), 0.4 * b + 0.5 * r.normal()]);
  }
  const m = S.varModel(y, 1, 10);
  close(m.coef[0][1], 0.5, 0.1, "a on a"); close(m.coef[0][2], 0.3, 0.1, "a on b"); close(m.coef[1][1], 0, 0.1, "b on a");
  const ba = m.granger.find((g) => g.cause === 1 && g.effect === 0), ab = m.granger.find((g) => g.cause === 0 && g.effect === 1);
  assert.ok(ba.p < 0.001 && ab.p > 0.05, `b->a p=${ba.p}, a->b p=${ab.p}`);
  assert.ok(Math.abs(m.irf[10][0][0]) < Math.abs(m.irf[0][0][0]), "own response decays");
  assert.equal(S.varSelectLag(y, 4), 1);
});

check("ARIMA: MA(1) coefficient recovered and auto order picks d=1 for a random walk", () => {
  const r = rng(51);
  const n = 600, e = Array.from({ length: n }, () => r.normal());
  const y = e.map((v, t) => 1 + v + (t ? 0.6 * e[t - 1] : 0));
  const m = S.arima(y, 0, 0, 1, 3);
  close(m.ma[0], 0.6, 0.1, "theta");
  close(m.const, S.mean(y), 0.05, "const equals the sample mean for a pure MA");
  const rw = [0]; for (let i = 1; i < 300; i++) rw.push(rw[i - 1] + r.normal());
  const auto = S.autoArima(rw, 4);
  assert.equal(auto.d, 1);
  assert.equal(auto.forecast.length, 4);
  assert.ok(Math.abs(auto.forecast[0] - rw[rw.length - 1]) < 3, "forecast continues from the last level");
});

console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
