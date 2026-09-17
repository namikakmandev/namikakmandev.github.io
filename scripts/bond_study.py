#!/usr/bin/env python3
"""Every number on bonds.html, recomputed from the committed data files.

    python3 scripts/bond_study.py     # writes data/bond-study.json

Inputs (all in data/): long-yields (ten-year government yields, monthly averages, six
countries, via FRED), us-treasury-daily (2-, 10-, 30-year, TIPS real yield and the ACM term
premium, business daily), us-fiscal (federal debt held by the public, deficit and net
interest, % of GDP), imf-weo (general government gross debt and net lending, % of GDP,
actuals and IMF projections).

Rules applied from .claude/skills/data-integrity: the effective sample size discounts
autocorrelation before any p is read; projections are separated from actuals; every
decomposition is an identity in the data, not a model.
"""
import json
import math
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTRIES = ["US", "GB", "FR", "IT", "DE", "JP"]
WEO_LAST_ACTUAL = "2025"   # the WEO file does not mark the split; the release's last actual year


def series(name):
    return json.load(open(os.path.join(ROOT, "data", name + ".json")))["series"]


def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    den = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / den if den else float("nan")


def ac1(a):
    return corr(a[:-1], a[1:])


def t_p(r, n):
    """Two-sided p for a correlation with n observations (Student t, numeric tail)."""
    if n <= 2 or abs(r) >= 1:
        return float("nan")
    t = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2

    def dens(x):
        return math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2)) * (1 + x * x / df) ** (-(df + 1) / 2)
    hi, steps = abs(t) + 40, 4000
    h = (hi - abs(t)) / steps
    return 2 * sum(dens(abs(t) + (i + 0.5) * h) for i in range(steps)) * h


def test(a, b):
    """Correlation with the Bartlett-style effective sample size n(1-r1 r2)/(1+r1 r2)."""
    n = len(a)
    r = corr(a, b)
    r1, r2 = ac1(a), ac1(b)
    n_eff = n * (1 - r1 * r2) / (1 + r1 * r2)
    return {"r": round(r, 3), "n": n, "ac1_a": round(r1, 2), "ac1_b": round(r2, 2), "n_eff": round(n_eff, 1),
            "p_naive": round(t_p(r, n), 4), "p_adj": round(t_p(r, max(n_eff, 3)), 4)}


def annual_mean(s, first=None):
    by = {}
    for k, v in s.items():
        y = k[:4]
        if first and y < first:
            continue
        by.setdefault(y, []).append(v)
    return {y: sum(v) / len(v) for y, v in sorted(by.items()) if len(v) >= 6}


def highest_since(s, key):
    """The last date before `key` at which the series was at or above its value at `key`."""
    v = s[key]
    for k in sorted(s, reverse=True):
        if k < key and s[k] >= v:
            return k
    return None


def main():
    ly = series("long-yields")
    tr = series("us-treasury-daily")
    fi = series("us-fiscal")
    weo = series("imf-weo")

    # --- ten-year yields, six countries -------------------------------------------------
    last_m = max(ly["US"])
    yields = {}
    for c in COUNTRIES:
        s = ly[c]
        lm = max(s)
        yields[c] = {
            "last": lm, "value": round(s[lm], 2),
            "dec_2025": round(s.get("2025-12", float("nan")), 2),
            "dec_2021": round(s.get("2021-12", float("nan")), 2),
            "change_since_dec_2025": round(s[lm] - s["2025-12"], 2) if "2025-12" in s else None,
            "change_since_dec_2021": round(s[lm] - s["2021-12"], 2) if "2021-12" in s else None,
            "highest_since": highest_since(s, lm),
            "first": min(s),
        }
    monthly = {c: [[k, round(v, 3)] for k, v in sorted(ly[c].items()) if k >= "1990-01"] for c in COUNTRIES}

    # --- the US curve, daily ----------------------------------------------------------------
    days = sorted(tr["y10"])
    last_d = days[-1]
    def at(key, d):
        s = tr[key]
        if d in s:
            return s[d]
        prev = [k for k in s if k <= d]
        return s[max(prev)] if prev else None
    ref = "2025-12-31"
    curve = {k: {"last": last_d, "value": at(k, last_d), "dec_2025": at(k, ref), "change": round(at(k, last_d) - at(k, ref), 2)}
             for k in ("y2", "y10", "y30", "real10", "term_premium10")}
    breakeven_now = at("y10", last_d) - at("real10", last_d)
    breakeven_ref = at("y10", ref) - at("real10", ref)
    expected_now = at("y10", last_d) - at("term_premium10", last_d)
    expected_ref = at("y10", ref) - at("term_premium10", ref)
    decomposition = {
        "window": [ref, last_d],
        "ten_year_change": round(at("y10", last_d) - at("y10", ref), 2),
        "real_yield_change": round(at("real10", last_d) - at("real10", ref), 2),
        "breakeven_change": round(breakeven_now - breakeven_ref, 2),
        "term_premium_change": round(at("term_premium10", last_d) - at("term_premium10", ref), 2),
        "expected_rates_change": round(expected_now - expected_ref, 2),
        "breakeven_now": round(breakeven_now, 2), "expected_rates_now": round(expected_now, 2),
        "note": "Two identities on the same 10-year yield: nominal = TIPS real yield + inflation compensation; nominal = ACM term premium + expected average short rate. The first is market prices; the second is a model's split.",
    }
    y30 = tr["y30"]
    hi30 = highest_since(y30, last_d)
    peak30 = max((v, k) for k, v in y30.items() if k >= "2026-01-01")
    peak30_since = highest_since(y30, peak30[1])
    y10_since = highest_since(tr["y10"], last_d)
    slope = {"now": round(at("y10", last_d) - at("y2", last_d), 2), "dec_2025": round(at("y10", ref) - at("y2", ref), 2)}
    # Turkish rates, for the reader verdicts: what a lira deposit pays against a 5% Treasury
    trr = series("tr-rates")
    tr_last = max(trr["deposit_3m"])
    tr_rates = {"last": tr_last, "deposit_3m": round(trr["deposit_3m"][tr_last], 1), "policy_rate": round(trr["policy_rate"][max(trr["policy_rate"])], 1)}
    daily = {k: [[d, tr[k][d]] for d in sorted(tr[k]) if d >= "2021-01-01"] for k in ("y2", "y10", "y30", "real10", "term_premium10")}
    # thin the daily lines to weekly points for the page (last observation of each week)
    def weekly(pts):
        out, seen = [], set()
        for d, v in reversed(pts):
            import datetime as dt
            wk = dt.date.fromisoformat(d).isocalendar()[:2]
            if wk in seen:
                continue
            seen.add(wk)
            out.append([d, v])
        return list(reversed(out))
    daily = {k: weekly(v) for k, v in daily.items()}

    # --- US fiscal --------------------------------------------------------------------------
    interest = fi["interest_pct_gdp"]
    deficit = fi["deficit_pct_gdp"]
    debt = fi["debt_held_by_public_pct_gdp"]
    ly_i, ly_d, lq = max(interest), max(deficit), max(debt)
    avg_rate = interest[ly_i] / debt[max(k for k in debt if k[:4] == ly_i)] * 100   # effective rate on the stock
    fiscal = {
        "interest_pct_gdp": {"last": ly_i, "value": round(interest[ly_i], 2), "highest_since": highest_since(interest, ly_i),
                             "series": [[k, round(v, 2)] for k, v in sorted(interest.items()) if k >= "1962"]},
        "deficit_pct_gdp": {"last": ly_d, "value": round(deficit[ly_d], 2), "series": [[k, round(v, 2)] for k, v in sorted(deficit.items()) if k >= "1962"]},
        "debt_held_by_public_pct_gdp": {"last": lq, "value": round(debt[lq], 1), "series": [[k, round(v, 1)] for k, v in sorted(debt.items())]},
        "effective_rate_on_debt_pct": round(avg_rate, 2),
        "arithmetic": {
            "marginal_10y": round(at("y10", last_d), 2),
            "interest_if_stock_repriced_at_10y": round(debt[lq] * at("y10", last_d) / 100, 2),
            "note": "Debt held by the public times today's ten-year yield, as a share of GDP. Not a forecast: the stock reprices only as it matures, over years, and the Treasury borrows across the curve, much of it in bills. It is the level the interest bill drifts towards if yields stay where they are and the debt ratio does not move.",
        },
    }

    # --- IMF WEO debt and deficits -------------------------------------------------------
    weo_out = {}
    for c in COUNTRIES:
        d, b = weo[f"{c}|GGXWDG_NGDP"], weo[f"{c}|GGXCNL_NGDP"]
        weo_out[c] = {
            "debt": [[k, round(v, 1)] for k, v in sorted(d.items()) if k >= "2000"],
            "balance": [[k, round(v, 1)] for k, v in sorted(b.items()) if k >= "2000"],
            "debt_2025": round(d["2025"], 1), "debt_2031": round(d["2031"], 1), "balance_2025": round(b["2025"], 1), "balance_2031": round(b["2031"], 1),
        }

    # --- the test: does the deficit time the yield? --------------------------------------
    us_annual = annual_mean(ly["US"])
    years = [y for y in sorted(deficit) if y in us_annual and "1966" <= y <= WEO_LAST_ACTUAL]
    a = [us_annual[y] for y in years]
    b = [-deficit[y] for y in years]   # deficit as a positive number
    lvl = test(a, b)
    chg = test([a[i] - a[i - 1] for i in range(1, len(a))], [b[i] - b[i - 1] for i in range(1, len(b))])
    # and the same for debt held by the public, annual (Q4 value)
    debt_y = {k[:4]: v for k, v in sorted(debt.items()) if k.endswith("Q4")}
    years2 = [y for y in years if y in debt_y]
    lvl_debt = test([us_annual[y] for y in years2], [debt_y[y] for y in years2])
    cross = [{"country": c, "yield": yields[c]["value"], "debt_2025": weo_out[c]["debt_2025"], "balance_2025": weo_out[c]["balance_2025"]} for c in COUNTRIES]
    cross_r_debt = corr([x["yield"] for x in cross], [x["debt_2025"] for x in cross])
    cross_r_bal = corr([x["yield"] for x in cross], [-x["balance_2025"] for x in cross])

    out = {
        "generated_from": {"long-yields": last_m, "us-treasury-daily": last_d, "us-fiscal": ly_i, "imf-weo": "actuals to " + WEO_LAST_ACTUAL + ", projections to 2031"},
        "yields": yields, "monthly": monthly,
        "curve": curve, "decomposition": decomposition,
        "thirty_year": {"last": last_d, "value": at("y30", last_d), "highest_since": hi30, "peak_2026": {"date": peak30[1], "value": peak30[0], "highest_since": peak30_since}},
        "ten_year_daily_highest_since": y10_since, "slope_2s10s": slope, "tr_rates": tr_rates,
        "daily": daily,
        "fiscal": fiscal, "weo": weo_out, "weo_last_actual": WEO_LAST_ACTUAL,
        "test": {
            "years": [years[0], years[-1]],
            "us_yield_vs_deficit_levels": lvl, "us_yield_vs_deficit_changes": chg, "us_yield_vs_debt_levels": lvl_debt,
            "cross_section": cross, "cross_r_yield_vs_debt": round(cross_r_debt, 2), "cross_r_yield_vs_deficit": round(cross_r_bal, 2),
            "note": "Annual means of the monthly ten-year yield against the federal deficit (positive = deficit) and debt held by the public, fiscal years. The cross-section is six points and is printed, not tested.",
        },
    }
    with open(os.path.join(ROOT, "data", "bond-study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("yields", "curve", "decomposition", "thirty_year", "test")}, indent=1)[:6000])
    print("fiscal", {k: v for k, v in fiscal.items() if k != "interest_pct_gdp" and k != "deficit_pct_gdp" and k != "debt_held_by_public_pct_gdp"}, fiscal["interest_pct_gdp"]["value"], fiscal["interest_pct_gdp"]["highest_since"])


if __name__ == "__main__":
    main()
