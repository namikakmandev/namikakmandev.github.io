#!/usr/bin/env python3
"""Time-series tests for the cattle parity study.

Answers four questions that the correlations on parite-sigir.html cannot:
  1. Is a parity LEVEL meaningful, or only its change?      -> ADF / KPSS
  2. Are meat and feed genuinely tied, or just co-drifting?  -> Engle-Granger + Johansen
  3. How fast does parity return to its own mean?            -> AR(1) half-life with a CI
  4. Does feed move first?                                   -> cross-corr + Granger
  5. Has the relationship itself shifted?                    -> Zivot-Andrews + subsamples
  6. Do the two Israel pairs say the same thing?             -> horizon corr + cointegration

Reads data/cattle-*.json, writes data/cattle-parity-tests.json.
"""
import contextlib, io, json, math, os, warnings
import numpy as np
from statsmodels.tsa.stattools import adfuller, kpss, coint, grangercausalitytests, zivot_andrews
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")

MARKETS = [
    ("US", "cattle-us.json",     "slaughter cattle PPI", "corn PPI"),
    ("EU", "cattle-eu.json",     "young bull R3 carcass", "feed grain"),
    ("TR", "cattle-tr.json",     "meat & meat products PPI", "compound feed PPI"),
    ("IL", "cattle-il.json",     "fresh beef PPI", "fodder input index"),
    ("IL-alt", "cattle-il-alt.json", "meat processing PPI", "prepared feeds"),
]

def load(fn):
    rows = json.load(open(os.path.join(D, fn)))["rows"]
    months = [r[0] for r in rows]
    meat = np.array([r[1] for r in rows], float)
    feed = np.array([r[2] for r in rows], float)
    return months, meat, feed

def adf(x, regression="c"):
    s, p, lag, n = adfuller(x, autolag="AIC", regression=regression)[:4]
    return {"stat": round(float(s), 3), "p": round(float(p), 4), "lags": int(lag), "n": int(n)}

def kpss_t(x, regression="c"):
    s, p, lag = kpss(x, regression=regression, nlags="auto")[:3]
    return {"stat": round(float(s), 3), "p": round(float(p), 4), "lags": int(lag)}

def ar1_halflife(x):
    """rho from AR(1); half-life = ln(.5)/ln(rho) months."""
    y, ylag = x[1:], x[:-1]
    res = sm.OLS(y, sm.add_constant(ylag)).fit()
    rho, se = float(res.params[1]), float(res.bse[1])
    hl = lambda r: math.log(0.5) / math.log(r) if 0 < r < 1 else None
    lo, hi = rho - 1.96 * se, rho + 1.96 * se
    return {"rho": round(rho, 4), "rho_se": round(se, 4),
            "half_life_months": round(hl(rho), 1) if hl(rho) else None,
            # the CI matters more than the point estimate: rho sits close to 1,
            # so the upper bound is often "never returns"
            "half_life_ci": [round(hl(lo), 1) if hl(lo) else None,
                             round(hl(hi), 1) if hl(hi) else None]}

def run_market(code, fn, meat_name, feed_name):
    months, meat, feed = load(fn)
    lm, lf = np.log(meat), np.log(feed)
    lp = lm - lf                      # log parity == log(meat/feed)
    d_lm, d_lf = np.diff(lm), np.diff(lf)

    r_lvl = float(np.corrcoef(meat, feed)[0, 1])
    r_chg = float(np.corrcoef(d_lm, d_lf)[0, 1])

    st = {
        "log_meat_adf": adf(lm),
        "log_feed_adf": adf(lf),
        "log_parity_adf": adf(lp),
        "log_parity_kpss": kpss_t(lp),
        "d_log_parity_adf": adf(np.diff(lp)),
    }

    eg_stat, eg_p, eg_crit = coint(lm, lf, trend="c", autolag="AIC")
    beta_fit = sm.OLS(lm, sm.add_constant(lf)).fit()
    beta = float(beta_fit.params[1])
    t_beta_is_1 = float((beta - 1.0) / beta_fit.bse[1])

    hl = ar1_halflife(lp)

    n = len(d_lm)
    xcorr = {}
    for k in range(-12, 13):
        if k >= 0:      # feed leads meat by k months
            a, b = d_lf[:n - k], d_lm[k:]
        else:
            a, b = d_lf[-k:], d_lm[:n + k]
        xcorr[k] = round(float(np.corrcoef(a, b)[0, 1]), 3)
    best_lag = max(xcorr, key=lambda k: abs(xcorr[k]))

    gr, maxlag = {}, 6
    try:
      # grangercausalitytests prints a full report per lag; we only want the p-values
      with contextlib.redirect_stdout(io.StringIO()):
        g = grangercausalitytests(np.column_stack([d_lm, d_lf]), maxlag=maxlag)
        gr["feed_causes_meat_p"] = {L: round(float(g[L][0]["ssr_ftest"][1]), 4)
                                    for L in range(1, maxlag + 1)}
        g2 = grangercausalitytests(np.column_stack([d_lf, d_lm]), maxlag=maxlag)
        gr["meat_causes_feed_p"] = {L: round(float(g2[L][0]["ssr_ftest"][1]), 4)
                                    for L in range(1, maxlag + 1)}
    except Exception as e:
        gr["error"] = str(e)

    # Johansen trace test — second opinion on cointegration; Engle-Granger has
    # low power in short samples and the two tests do disagree here.
    joh = coint_johansen(np.column_stack([lm, lf]), det_order=0, k_ar_diff=4)
    johansen = {"trace_r0": round(float(joh.lr1[0]), 2),
                "crit_5pct_r0": round(float(joh.cvt[0, 1]), 2),
                "cointegrated_5pct": bool(joh.lr1[0] > joh.cvt[0, 1])}

    # Zivot-Andrews — unit root allowing ONE break in the mean. A parity that
    # looks non-reverting may just have moved to a new plateau.
    za_stat, za_p, za_crit, _, za_bp = zivot_andrews(lp, regression="c", autolag="AIC")
    za = {"stat": round(float(za_stat), 3), "p": round(float(za_p), 4),
          "crit_5pct": round(float(za_crit["5%"]), 3), "break_month": months[za_bp]}

    # does imposing the 1:-1 ratio help or hurt vs a freely fitted beta?
    free_resid_adf = adf(beta_fit.resid)

    d_lp = np.diff(lp)
    var_share_feed = float(-np.cov(d_lf, d_lp)[0, 1] / np.var(d_lp, ddof=1))
    var_share_meat = float(np.cov(d_lm, d_lp)[0, 1] / np.var(d_lp, ddof=1))

    return {
        "code": code, "meat": meat_name, "feed": feed_name,
        "span": f"{months[0]}..{months[-1]}", "n": len(months),
        "corr_levels": round(r_lvl, 3), "corr_changes": round(r_chg, 3),
        "stationarity": st,
        "cointegration": {
            "eg_stat": round(float(eg_stat), 3), "eg_p": round(float(eg_p), 4),
            "crit_5pct": round(float(eg_crit[1]), 3),
            "beta_meat_on_feed": round(beta, 3),
            "beta_se": round(float(beta_fit.bse[1]), 3),
            "t_beta_equals_1": round(t_beta_is_1, 2),
        },
        "johansen": johansen,
        "structural_break": za,
        "free_beta_residual_adf": free_resid_adf,
        "mean_reversion": hl,
        "lead_lag": {"xcorr_dlogfeed_to_dlogmeat": xcorr,
                     "peak_lag_months": int(best_lag),
                     "peak_corr": xcorr[best_lag], "granger_p": gr},
        "variance_share_of_parity_change": {
            "feed": round(var_share_feed, 3), "meat": round(var_share_meat, 3)},
    }

out = {"generated_from": "data/cattle-*.json", "tests": {}}
for code, fn, mn, fnm in MARKETS:
    out["tests"][code] = run_market(code, fn, mn, fnm)
    print(f"  {code} done ({out['tests'][code]['n']} months)")

mA, meatA, feedA = load("cattle-il.json")
mB, meatB, feedB = load("cattle-il-alt.json")
common = sorted(set(mA) & set(mB))
iA = {m: i for i, m in enumerate(mA)}; iB = {m: i for i, m in enumerate(mB)}
pA = np.array([math.log(meatA[iA[m]] / feedA[iA[m]]) for m in common])
pB = np.array([math.log(meatB[iB[m]] / feedB[iB[m]]) for m in common])
s, p, crit = coint(pA, pB, trend="c", autolag="AIC")
rA, rB = np.exp(pA), np.exp(pB)
horizons = {}
for h, lab in [(1, "monthly"), (3, "quarterly"), (12, "annual")]:
    a, b = rA[h:] / rA[:-h] - 1, rB[h:] / rB[:-h] - 1
    horizons[lab] = round(float(np.corrcoef(a, b)[0, 1]), 3)
out["israel_robustness"] = {
    "span": f"{common[0]}..{common[-1]}", "n": len(common),
    "corr_levels": round(float(np.corrcoef(rA, rB)[0, 1]), 3),
    "corr_by_horizon": horizons,
    "coint_p": round(float(p), 4), "coint_stat": round(float(s), 3),
    "crit_5pct": round(float(crit[1]), 3),
    "spread_adf": adf(pA - pB),
}
print("  IL robustness done")

# --- US subsamples: is the pre- and post-ethanol cattle cycle the same object? ---
months, meat, feed = load("cattle-us.json")
lm, lf = np.log(meat), np.log(feed)
lp = lm - lf
idx = {m: i for i, m in enumerate(months)}
subs = {}
for lab, a, b in [("1971-1985", "1971-01", "1985-12"), ("1986-2005", "1986-01", "2005-12"),
                  ("2006-2015", "2006-01", "2015-12"), ("2016-2026", "2016-01", "2026-07"),
                  ("1971-2005", "1971-01", "2005-12"), ("2006-2026", "2006-01", "2026-07")]:
    i, j = idx[a], idx[b] + 1
    subs[lab] = {"n": j - i,
                 "mean_parity": round(float(np.exp(lp[i:j]).mean()), 3),
                 "sd_parity": round(float(np.exp(lp[i:j]).std()), 3),
                 "parity_adf_p": round(float(adfuller(lp[i:j], autolag="AIC")[1]), 4),
                 "coint_p": round(float(coint(lm[i:j], lf[i:j], trend="c", autolag="AIC")[1]), 4)}
par = meat / feed
i16 = [i for i, m in enumerate(months) if m.startswith("2016")]
out["us_subsamples"] = subs
out["us_base_year_check"] = {
    "full_sample_mean": round(float(par.mean()), 4),
    "mean_2016": round(float(par[i16].mean()), 4),
    "base_vs_long_run_pct": round(100 * float(par[i16].mean() / par.mean() - 1), 1),
}
print("  US subsamples done")

json.dump(out, open(os.path.join(D, "cattle-parity-tests.json"), "w"), indent=1)
print("wrote data/cattle-parity-tests.json")
