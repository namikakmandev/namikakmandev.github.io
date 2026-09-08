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

check("ADF: an explicit lag longer than the sample fails with a usable message", () => {
  const r = rng(13);
  const short = Array.from({ length: 20 }, () => r.normal());
  // Every candidate regression is empty here; the caller must be told why, not handed a TypeError.
  assert.throws(() => S.adf(short, "c", 25), (e) => e instanceof Error && !(e instanceof TypeError) && /needs more observations/.test(e.message), "explicit over-long lag");
  assert.throws(() => S.adf(short.slice(0, 8), "c"), /at least 12 observations/, "too short overall");
  assert.equal(S.adf(short, "c", 2).lags, 2, "a lag the sample supports still runs");
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

  assert.equal(p.f_unit_effects.df1, G - 1, "one-way restricts G-1 unit dummies");

  // A common year shock is absorbed by two-way effects
  const y2 = y.map((v, idx) => v + 4 * Math.sin(time[idx] / 2));
  const two = S.panelRegress(y2, X, unit, time, "unit_time");
  close(two.estimate.beta[0], 1.0, 0.08, "two-way slope with a global shock");
  // Two-way absorbs the year dummies too, so the F test restricts (G-1)+(T-1), not G-1.
  assert.equal(two.f_unit_effects.df1, (G - 1) + (T - 1), "two-way restriction count");
  assert.equal(two.f_unit_effects.df2, two.estimate.df, "denominator df matches the within fit");
  close(two.f_unit_effects.p, S.fUpperP(two.f_unit_effects.F, (G - 1) + (T - 1), two.f_unit_effects.df2), 1e-12, "p uses the same df");
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

check("local projections recover the impulse response of a known AR(1) system", () => {
  const r = rng(21);
  // y_t = 0.5 y_{t-1} + 0.8 x_t + e_t, x white noise: response 0.8, 0.4, 0.2, 0.1 ...
  const n = 1500, x = Array.from({ length: n }, () => r.normal()), y = [0];
  for (let t = 1; t < n; t++) y.push(0.5 * y[t - 1] + 0.8 * x[t] + 0.3 * r.normal());
  const lp = S.localProjections(y, x, 4, 2);
  assert.equal(lp.horizons.length, 5);
  close(lp.horizons[0].beta, 0.8, 0.05, "h=0"); close(lp.horizons[1].beta, 0.4, 0.06, "h=1");
  close(lp.horizons[2].beta, 0.2, 0.06, "h=2"); close(lp.horizons[4].beta, 0.05, 0.06, "h=4");
  assert.ok(lp.horizons[0].p < 1e-6 && lp.horizons[0].se > 0, "significant at impact");
  close(lp.shock_sd, 1, 0.08, "shock sd is the sd of x given the controls");
  assert.throws(() => S.localProjections(y.slice(0, 20), x.slice(0, 20), 8, 4), /Too few observations/);
});

check("Diebold-Mariano: separates a good forecaster from a bad one, not two equal ones", () => {
  const r = rng(33);
  const n = 80;
  const e1 = Array.from({ length: n }, () => r.normal()), e2 = Array.from({ length: n }, () => 2 * r.normal());
  const dm = S.dieboldMariano(e1, e2, 1);
  assert.equal(dm.better, 1, `stat ${dm.statistic} p ${dm.p}`);
  assert.ok(dm.statistic < -2.5 && dm.p < 0.02);
  const same = S.dieboldMariano(e1, e1, 1);
  assert.equal(same.statistic, 0); assert.equal(same.better, null);
  const e3 = Array.from({ length: n }, () => r.normal());
  const equal = S.dieboldMariano(e1, e3, 4);
  assert.equal(equal.better, null, `two iid N(0,1) error series, p ${equal.p}`);
  assert.throws(() => S.dieboldMariano(e1.slice(0, 4), e2.slice(0, 4)), /6 or more/);
  // A failed origin (NaN) is dropped, not allowed to poison the test.
  const holed = S.dieboldMariano([NaN, ...e1.slice(1)], e2, 1);
  assert.equal(holed.n, n - 1); assert.equal(holed.better, 1, `with a NaN pair: p ${holed.p}`);
  assert.throws(() => S.dieboldMariano([NaN, NaN, NaN, ...e1.slice(3, 8)], e2.slice(0, 8)), /6 or more/, "count after dropping");
  // A constant gap is a win at every origin, not a tie.
  const constant = S.dieboldMariano(new Array(10).fill(1), new Array(10).fill(2), 1);
  assert.equal(constant.better, 1); assert.equal(constant.degenerate, true); assert.equal(constant.p, 0);
  close(S.longRunVariance(e1, 0), S.variance(e1, 0), 1e-12, "lag 0 is the plain variance");
});

check("rolling-origin backtest: origins leave room for the horizon, errors line up with the actuals", () => {
  const y = Array.from({ length: 50 }, (_, i) => i);   // a straight line: a naive forecast errs by h
  const bt = S.rollingOrigin(y, (train) => new Array(3).fill(train[train.length - 1]), 3, 5, 10);
  assert.deepEqual(bt.origins, [42, 43, 44, 45, 46]);
  assert.deepEqual(bt.errors[0], [1, 2, 3]);
  assert.equal(bt.failures, 0);
  const stepped = S.rollingOrigin(y, (train) => [train[train.length - 1]], 1, 3, 10, 4);
  assert.deepEqual(stepped.origins, [40, 44, 48]);
  const failing = S.rollingOrigin(y, () => { throw new Error("no"); }, 2, 2, 10);
  assert.equal(failing.failures, 2); assert.ok(Number.isNaN(failing.errors[0][0]));
  assert.throws(() => S.rollingOrigin(y.slice(0, 5), () => [0], 3, 1, 10), /Too few observations/);
  const m = S.errorMetrics([1, -1, 2, NaN], [10, 10, 10, 10]);
  close(m.rmse, Math.sqrt(2), 1e-9, "rmse"); close(m.mae, 4 / 3, 1e-9, "mae"); close(m.mape, 1000 / 75, 1e-9, "mape"); assert.equal(m.n, 3);
  assert.equal(S.errorMetrics([1, 2], [0, 5]).mape, null, "mape undefined when an actual is zero");
});

check("2SLS removes the endogeneity bias OLS carries, and the diagnostics say why", () => {
  const r = rng(45);
  const n = 600;
  // x = 0.6 z1 + 0.4 z2 + u + v, y = 1 + 2 x + w + u: u is the confounder, z1 and z2 are clean instruments, w is exogenous
  const z1 = [], z2 = [], w = [], x = [], y = [];
  for (let i = 0; i < n; i++) {
    const u = r.normal(), a = r.normal(), b = r.normal(), c = r.normal();
    z1.push(a); z2.push(b); w.push(c);
    const xi = 0.6 * a + 0.4 * b + u + 0.5 * r.normal();
    x.push(xi); y.push(1 + 2 * xi + 0.7 * c + u + 0.3 * r.normal());
  }
  const iv = S.twoSLS(y, x.map((v) => [v]), z1.map((v, i) => [v, z2[i]]), w.map((v) => [v]));
  close(iv.beta[1], 2, 0.1, "2SLS slope on x");
  close(iv.beta[2], 0.7, 0.1, "exogenous slope");
  assert.ok(iv.ols.beta[1] > 2.3, `OLS is biased up, got ${iv.ols.beta[1]}`);
  assert.ok(iv.first_stage[0].F_excluded > 10 && iv.first_stage[0].F_p < 1e-6, "strong instruments");
  assert.ok(iv.wu_hausman.p < 0.01, `Wu-Hausman should reject exogeneity, p ${iv.wu_hausman.p}`);
  assert.ok(iv.sargan && iv.sargan.df === 1 && iv.sargan.p > 0.01, `valid instruments should pass Sargan, p ${iv.sargan?.p}`);
  assert.ok(iv.se[1] > 0 && iv.hac_se[1] > 0 && Math.abs(iv.hac_se[1] / iv.se[1] - 1) < 0.5, "HAC se same order as plain se on iid data");
  const just = S.twoSLS(y, x.map((v) => [v]), z1.map((v) => [v]));
  assert.equal(just.sargan, null, "just-identified: no Sargan test");
  close(just.beta[1], 2, 0.15, "just-identified slope");
  assert.throws(() => S.twoSLS(y, x.map((v, i) => [v, w[i]]), z1.map((v) => [v])), /Under-identified/);
  assert.throws(() => S.twoSLS(y, x.map((v) => [v]), x.map((v) => [2 * v + 1])), /reproduce endogenous regressor 1 exactly/);
  // A weak instrument is flagged by the first-stage F
  const weak = S.twoSLS(y, x.map((v) => [v]), z1.map(() => [r.normal()]));
  assert.ok(weak.first_stage[0].F_excluded < 10, `noise instrument F ${weak.first_stage[0].F_excluded}`);
});

check("sup-F critical values: white noise does not reject, a mean shift does and is located; sequential search finds two", () => {
  close(S.supFCritical(1)["5%"], 8.85, 0.05, "k=1 5% is Andrews' published value");
  close(S.supFCritical(1)["1%"], 12.35, 0.05, "k=1 1% is Andrews' published value");
  close(S.supFCritical(2)["5%"], 11.86 / 2, 0.01, "sup-F is sup-Wald / k");
  assert.throws(() => S.supFCritical(6), /tabulated for 1 to 5/);
  const r = rng(52);
  const n = 200, X = Array.from({ length: n }, () => [1]);
  const wn = Array.from({ length: n }, () => r.normal());
  const q = S.supF(wn, X);
  assert.equal(S.supFReject(q.best.F, 1), null, `white noise sup-F ${q.best.F}`);
  const shifted = wn.map((v, i) => v + (i >= 120 ? 1.5 : 0));
  const s1 = S.supF(shifted, X);
  assert.equal(S.supFReject(s1.best.F, 1), "1%");
  assert.ok(Math.abs(s1.best.break_index - 120) <= 3, `located at ${s1.best.break_index}`);
  const two = wn.map((v, i) => v + (i >= 70 ? 1.5 : 0) + (i >= 140 ? -2 : 0));
  const seq = S.sequentialBreaks(two, X, 4);
  assert.equal(seq.breaks.length, 2, `found ${seq.breaks.map((b) => b.index)} (${seq.stopped})`);
  assert.ok(Math.abs(seq.breaks[0].index - 70) <= 3 && Math.abs(seq.breaks[1].index - 140) <= 3, `at ${seq.breaks.map((b) => b.index)}`);
  assert.equal(seq.segments.length, 3);
  close(seq.segments[1].mean_y - seq.segments[0].mean_y, 1.5, 0.4, "segment means differ by the shift");
  assert.match(seq.stopped, /no further break/);
  const none = S.sequentialBreaks(wn, X, 3);
  assert.equal(none.breaks.length, 0); assert.equal(none.segments.length, 1);
  // The prefix-sum scan equals the explicit Chow test, for a constant and for a constant with a regressor.
  const xr = Array.from({ length: n }, () => r.normal());
  const yr = xr.map((v, i) => 0.5 + 0.8 * v + r.normal());
  const X2 = xr.map((v) => [1, v]);
  for (const [yy, XX] of [[shifted, X], [yr, X2]]) {
    const scan = S.supF(yy, XX);
    for (const e of scan.scan.filter((_, i) => i % 17 === 0)) close(e.F, S.chow(yy, XX, e.index).F, 1e-8, `F at ${e.index}`);
  }
  // A minimum segment in absolute terms keeps candidates away from the edges.
  const narrow = S.supF(shifted, X, 0.15, 60);
  assert.ok(narrow.scan.every((e) => e.index >= 60 && e.index <= n - 60));
  // After the first split the remainder is not scanned to its edges: a 40-point white-noise tail gets no break.
  const oneShift = wn.map((v, i) => v + (i >= 160 ? 2 : 0));
  const seq1 = S.sequentialBreaks(oneShift, X, 5);
  assert.equal(seq1.breaks.length, 1, `found ${seq1.breaks.map((b) => b.index)}`);
});

check("regression diagnostics: Breusch-Pagan, VIF and RESET react to what they should", () => {
  const r = rng(61);
  const n = 400;
  const x1 = Array.from({ length: n }, () => r.normal()), x2 = x1.map((v) => 0.95 * v + 0.3 * r.normal()), x3 = Array.from({ length: n }, () => r.normal());
  const X = x1.map((v, i) => [1, v, x3[i]]);
  const yHom = x1.map((v, i) => 1 + v + x3[i] + r.normal());
  const yHet = x1.map((v, i) => 1 + v + x3[i] + Math.exp(0.8 * v) * r.normal());
  assert.ok(S.breuschPagan(X, S.ols(yHom, X).resid).p > 0.05, "homoskedastic: no rejection");
  assert.ok(S.breuschPagan(X, S.ols(yHet, X).resid).p < 0.01, "heteroskedastic: rejection");
  const v = S.vif(x1.map((a, i) => [1, a, x2[i], x3[i]]));
  assert.ok(v[0] > 5 && v[1] > 5 && v[2] < 2, `VIFs ${v}`);
  assert.deepEqual(S.vif(X.map((row) => [row[0], row[1]])), [1], "one regressor: VIF 1");
  const yQuad = x1.map((v, i) => 1 + v + 0.8 * v * v + 0.5 * r.normal());
  assert.ok(S.reset(yQuad, X, S.ols(yQuad, X)).p < 0.01, "missing square: RESET rejects");
  assert.ok(S.reset(yHom, X, S.ols(yHom, X)).p > 0.05, "correct linear form: RESET does not reject");
});

check("Johansen with a restricted constant: rank on drift-free series, the constant recovered inside the relation", () => {
  const r = rng(77);
  const n = 500;
  const x = [0]; for (let i = 1; i < n; i++) x.push(x[i - 1] + r.normal());
  // y = 5 + 2x + u: no drift anywhere, a constant of 5 inside the relation
  const y = []; let u = 0;
  for (let i = 0; i < n; i++) { u = 0.4 * u + r.normal(); y.push(5 + 2 * x[i] + u); }
  const Y = y.map((v, i) => [v, x[i]]);
  const j = S.johansen(Y, 1, "restricted_constant");
  assert.equal(j.det, "restricted_constant");
  assert.equal(j.rank_at_5pct, 1, JSON.stringify(j.trace.map((t) => [t.r, +t.statistic.toFixed(1), t.critical["5%"]])));
  assert.equal(j.cointegrating_vector.length, 3, "vector carries the constant");
  close(j.cointegrating_vector[1], -2, 0.1, "slope"); close(j.cointegrating_vector[2], -5, 0.6, "constant in the relation");
  assert.equal(j.trace[0].critical["5%"], 20.2618, "MHM restricted-constant critical value for n-r=2");
  const m = S.vecm(Y, 1, undefined, "restricted_constant");
  close(m.beta_constant[0], -5, 0.6, "VECM reports the relation's constant");
  assert.ok(m.alpha[0][0] < -0.2 && m.alpha_p[0][0] < 0.01, `y adjusts: alpha ${m.alpha[0][0]}`);
  assert.ok(Math.abs(m.alpha[1][0]) < 0.15, `x is weakly exogenous: alpha ${m.alpha[1][0]}`);
  assert.deepEqual(m.constant, [0, 0], "no separate intercept in the differences");
  close(S.mean(m.ect.map((row) => row[0])), 0, 0.5, "the error-correction term is centred");
  // Two independent drift-free walks: rank 0 under the restricted constant
  const w = [0]; for (let i = 1; i < n; i++) w.push(w[i - 1] + r.normal());
  const j0 = S.johansen(x.map((v, i) => [v, w[i]]), 1, "restricted_constant");
  assert.equal(j0.rank_at_5pct, 0, JSON.stringify(j0.trace.map((t) => +t.statistic.toFixed(1))));
  // Drift check: a walk with drift has a large t, one without does not
  const drifted = x.map((v, i) => v + 0.3 * i);
  assert.ok(Math.abs(S.driftT(drifted)) > 4 && Math.abs(S.driftT(x)) < 2.5, `drift t ${S.driftT(drifted)} vs ${S.driftT(x)}`);
});

check("structural VAR: long-run restrictions recover permanent and transitory shocks, sign restrictions accept and band, bootstrap brackets the point", () => {
  const r = rng(88);
  const n = 800;
  // y = random walk driven by e1 (permanent) + 0.8 z, z = 0.5 z_{-1} + e2 (transitory): e2 has no long-run effect on y.
  const e1 = [], e2 = [], dy = [], z = []; let lvl = 0, zz = 0, prevY = 0;
  for (let t = 0; t < n; t++) {
    const a = r.normal(), b = r.normal(); e1.push(a); e2.push(b);
    lvl += a; zz = 0.5 * zz + b; const y = lvl + 0.8 * zz;
    dy.push(y - prevY); prevY = y; z.push(zz);
  }
  const Y = dy.map((v, i) => [v, z[i]]).slice(1);
  const m = S.varModel(Y, 2, 12);
  assert.equal(m.psi.length, 13); assert.equal(m.resid.length, 2);
  const { B, long_run } = S.identify(m, "long_run");
  close(long_run[0][1], 0, 1e-9, "long-run matrix is lower triangular by construction");
  // Structural shocks eps = B^-1 u should line up with the true e1 (shock 1) and e2 (shock 2)
  const Binv = S.inverseGeneral(B);
  const eps = m.resid[0].map((_, t) => Binv.map((row) => row[0] * m.resid[0][t] + row[1] * m.resid[1][t]));
  const off = Y.length - m.resid[0].length + 1;   // residuals start after p lags; Y dropped the first row
  const c1 = Math.abs(S.pearson(eps.map((e) => e[0]), e1.slice(off, off + eps.length)));
  const c2 = Math.abs(S.pearson(eps.map((e) => e[1]), e2.slice(off, off + eps.length)));
  assert.ok(c1 > 0.9 && c2 > 0.9, `shock recovery correlations ${c1.toFixed(2)}, ${c2.toFixed(2)}`);
  const BBt = S.matmul(B, S.transpose(B));
  close(BBt[0][0], m.sigma[0][0], 1e-8, "B B' = Sigma"); close(BBt[0][1], m.sigma[0][1], 1e-8, "B B' = Sigma off-diagonal");
  const chol = S.identify(m, "cholesky");
  close(chol.B[0][1], 0, 1e-12, "Cholesky B is lower triangular");
  assert.equal(chol.long_run, null);
  // Sign restrictions: shock 1 raises dy on impact, shock 2 raises z on impact
  const sr = S.signIdentify(m, [{ shock: 0, variable: 0, sign: 1, horizons: [0] }, { shock: 1, variable: 1, sign: 1, horizons: [0, 1] }], 100, 5000);
  assert.ok(sr.accepted >= 50, `accepted ${sr.accepted} of ${sr.draws}`);
  assert.ok(sr.irf_median[0][0][0] > 0 && sr.irf_median[0][1][1] > 0 && sr.irf_median[1][1][1] > 0, "median responses obey the restrictions");
  for (let h = 0; h < 13; h++) for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) assert.ok(sr.irf_lo[h][i][j] <= sr.irf_median[h][i][j] && sr.irf_median[h][i][j] <= sr.irf_hi[h][i][j], "bands bracket the median");
  const Bm = S.matmul(sr.B_median_target, S.transpose(sr.B_median_target));
  close(Bm[1][1], m.sigma[1][1], 1e-8, "the target draw is a valid impact matrix");
  assert.throws(() => S.signIdentify(m, [{ shock: 0, variable: 0, sign: 1, horizons: [0] }, { shock: 0, variable: 0, sign: -1, horizons: [0] }], 10, 200), /No draw/);
  assert.throws(() => S.signIdentify(m, [{ shock: 3, variable: 0, sign: 1, horizons: [0] }]), /outside/);
  // Bootstrap bands around the long-run IRF
  const bb = S.varBootstrap(Y, 2, 12, "long_run", 60);
  assert.ok(bb.reps >= 50);
  const point = S.structuralResponses(m.psi, B).irf;
  let inside = 0, total = 0;
  for (let h = 0; h < 13; h++) for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) { total++; if (bb.lo05[h][i][j] <= point[h][i][j] && point[h][i][j] <= bb.hi95[h][i][j]) inside++; assert.ok(bb.lo16[h][i][j] >= bb.lo05[h][i][j] && bb.hi84[h][i][j] <= bb.hi95[h][i][j], "68% band inside 90% band"); }
  assert.ok(inside / total > 0.8, `point inside the 90% band for ${inside}/${total}`);
  // An exactly singular long-run multiplier is refused; a general inverse round-trips
  assert.equal(S.inverseGeneral([[1, 2], [2, 4]]), null);
  const inv = S.inverseGeneral([[4, 7], [2, 6]]); const I = S.matmul([[4, 7], [2, 6]], inv);
  close(I[0][0], 1, 1e-12, "A A^-1 = I"); close(I[0][1], 0, 1e-12, "A A^-1 = I off-diagonal");
  assert.throws(() => S.identify({ ...m, a_sum: [[1, 0], [0, 1]] }, "long_run"), /unit root/);
});

check("Johansen with a restricted trend: a trending equilibrium gets rank 1 and the trend coefficient", () => {
  const r = rng(91);
  const n = 500;
  const x = [0]; for (let i = 1; i < n; i++) x.push(x[i - 1] + 0.1 + r.normal());
  // y = 2x + 0.05 t + u: the relation itself trends, so the trend belongs inside it
  const y = []; let u = 0;
  for (let i = 0; i < n; i++) { u = 0.4 * u + r.normal(); y.push(2 * x[i] + 0.05 * i + u); }
  const Y = y.map((v, i) => [v, x[i]]);
  const j = S.johansen(Y, 1, "restricted_trend");
  assert.equal(j.det, "restricted_trend");
  assert.equal(j.rank_at_5pct, 1, JSON.stringify(j.trace.map((t) => [t.r, +t.statistic.toFixed(1), t.critical["5%"]])));
  assert.equal(j.trace[0].critical["5%"], 25.8721, "MHM restricted-trend critical value for n-r=2");
  assert.equal(j.cointegrating_vector.length, 3);
  close(j.cointegrating_vector[1], -2, 0.1, "slope"); close(j.cointegrating_vector[2], -0.05, 0.02, "trend inside the relation");
  const m = S.vecm(Y, 1, undefined, "restricted_trend");
  close(m.beta_trend[0], -0.05, 0.02, "VECM reports the trend coefficient");
  assert.ok(m.alpha[0][0] < -0.2 && m.alpha_p[0][0] < 0.01, `y adjusts: alpha ${m.alpha[0][0]}`);
  assert.ok(m.constant.every((c) => Number.isFinite(c)), "differences keep an unrestricted constant");
  close(S.mean(m.ect.map((row) => row[0])), 0, 0.5, "the error-correction term is centred");
});

check("ADF picks its lag by comparing fits on one sample, so the test keeps its power", () => {
  // Every candidate lag must be scored on the same observations. Comparing AIC across
  // different sample sizes picks the longest lag almost always, and the test loses most
  // of its ability to see a stationary series.
  const r = rng(42);
  let maxPicked = 0, rejectsNoise = 0, powerAR = 0;
  const N = 120, MAXLAG = 12;
  for (let k = 0; k < N; k++) {
    const wn = Array.from({ length: 200 }, () => r.normal());
    const a = S.adf(wn, "c", "auto");
    if (a.lags >= MAXLAG) maxPicked++;
    if (a.reject_unit_root_at) rejectsNoise++;
    const ar = [0];
    for (let i = 1; i < 120; i++) ar.push(0.5 * ar[i - 1] + r.normal());
    if (S.adf(ar, "c", "auto").reject_unit_root_at) powerAR++;
  }
  assert.ok(maxPicked / N < 0.15, `auto lag lands on the maximum ${(100 * maxPicked / N).toFixed(0)}% of the time; the broken rule did it ~99%`);
  assert.ok(rejectsNoise / N > 0.95, `white noise rejected only ${(100 * rejectsNoise / N).toFixed(0)}% of the time`);
  assert.ok(powerAR / N > 0.9, `power against a stationary AR(1) is ${(100 * powerAR / N).toFixed(0)}%; the broken rule gave ~68%`);
});

check("KPSS refuses to judge a series with no variance rather than rejecting it", () => {
  const flat = new Array(60).fill(4.2);
  const k = S.kpss(flat, "c");
  assert.equal(k.reject_stationarity_at, null, "a constant series is not evidence against stationarity");
  assert.ok(k.degenerate, "and it says why");
  assert.ok(!Number.isFinite(k.statistic), "with no number pretending to back the claim");
  // A normal series still works
  const r = rng(5);
  const ok = Array.from({ length: 200 }, () => r.normal());
  assert.ok(Number.isFinite(S.kpss(ok, "c").statistic));
});

check("the break scan is corrected for serial correlation, and keeps its power", () => {
  // Persistence alone manufactures breaks in the uncorrected statistic: at first-order
  // autocorrelation 0.7 a series with no break at all is called broken four times in five.
  const r = rng(11);
  const crit = S.supFCritical(1)["5%"];
  const rate = (phi) => {
    let raw = 0, hac = 0, N = 120;
    for (let k = 0; k < N; k++) {
      const y = [0];
      for (let i = 1; i < 200; i++) y.push(phi * y[i - 1] + r.normal());
      const X = y.map(() => [1]);
      const s = S.supF(y, X);
      if (s.best.F > crit) raw++;
      if (s.best.F / S.hacInflation(y, X) > crit) hac++;
    }
    return { raw: raw / N, hac: hac / N };
  };
  const p7 = rate(0.7);
  assert.ok(p7.raw > 0.5, `uncorrected should fail badly here, got ${p7.raw}`);
  assert.ok(p7.hac < 0.2, `corrected false-break rate ${p7.hac} is too high`);
  // and a real break is still found every time
  let found = 0, N = 60;
  for (let k = 0; k < N; k++) {
    const y = [];
    for (let i = 0; i < 200; i++) y.push((i < 100 ? 0 : 1.5) + r.normal());
    const X = y.map(() => [1]);
    const s = S.supF(y, X);
    if (s.best.F / S.hacInflation(y, X) > crit) found++;
  }
  assert.ok(found / N > 0.9, `power against a real break fell to ${found / N}`);
});

console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
