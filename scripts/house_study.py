#!/usr/bin/env python3
"""Every number on houses.html, recomputed from the committed data files.

    python3 scripts/house_study.py     # writes data/house-study.json

Inputs (all in data/): house-prices (BIS residential property prices via FRED, nominal and
CPI-deflated, quarterly, 14 countries), us-housing (Case-Shiller, median sale price, rent CPI,
starts), us-mortgage-rate (Freddie Mac 30-year, weekly), us-prices (US CPI, the deflator),
tr-house-prices (TCMB KFE, monthly, 2023 = 100, Türkiye and three cities), tr-cpi-ppi (TÜİK
CPI, the Turkish deflator), tr-rates (policy and deposit rates), long-yields (ten-year yields).

Rules applied from .claude/skills/data-integrity: money is deflated and the deflator named;
the effective sample size discounts autocorrelation before any p is read; a lag scan is
corrected for the number of lags; every derived measure has its definition in the file.
"""
import json
import math
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTRIES = ["TR", "NL", "AU", "PL", "US", "CA", "DE", "JP", "GB", "KR", "ES", "FR", "IT", "CN"]
YIELD_COUNTRIES = ["US", "GB", "FR", "IT", "DE", "JP"]


def series(name):
    return json.load(open(os.path.join(ROOT, "data", name + ".json")))["series"]


def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    den = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / den if den else float("nan")


def ac1(a):
    return corr(a[:-1], a[1:])


def t_p(r, n):
    if n <= 2 or abs(r) >= 1:
        return float("nan")
    t = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2

    def dens(x):
        return math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2)) * (1 + x * x / df) ** (-(df + 1) / 2)
    hi, steps = abs(t) + 40, 4000
    h = (hi - abs(t)) / steps
    return 2 * sum(dens(abs(t) + (i + 0.5) * h) for i in range(steps)) * h


def test(a, b, tests=1):
    n = len(a)
    r = corr(a, b)
    r1, r2 = ac1(a), ac1(b)
    n_eff = n * (1 - r1 * r2) / (1 + r1 * r2)
    p_adj = t_p(r, max(n_eff, 3))
    return {"r": round(r, 3), "n": n, "ac1_a": round(r1, 2), "ac1_b": round(r2, 2), "n_eff": round(n_eff, 1),
            "p_naive": round(t_p(r, n), 4), "p_adj": round(min(1.0, p_adj * tests), 4), "tests": tests}


def annual_mean(s):
    by = {}
    for k, v in s.items():
        by.setdefault(k[:4], []).append(v)
    return {y: sum(v) / len(v) for y, v in sorted(by.items()) if len(v) >= (4 if len(next(iter(s))) == 7 and "Q" in next(iter(s)) else 6)}


def quarter_of(month_key):
    y, m = int(month_key[:4]), int(month_key[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


def quarterly_mean(s):
    by = {}
    for k, v in s.items():
        by.setdefault(quarter_of(k) if len(k) >= 7 else k, []).append(v)
    return {q: sum(v) / len(v) for q, v in sorted(by.items())}


def yoy(s, step):
    keys = sorted(s)
    idx = {k: i for i, k in enumerate(keys)}
    out = {}
    for k in keys:
        i = idx[k]
        if i >= step:
            out[k] = (s[k] / s[keys[i - step]] - 1) * 100
    return out


def main():
    hp = series("house-prices")
    us = series("us-housing")
    mr = series("us-mortgage-rate")["fixed_30y"]
    uscpi = series("us-prices")["cpi"]
    kfe = series("tr-house-prices")
    trcpi = series("tr-cpi-ppi")["cpi"]
    trr = series("tr-rates")
    ly = series("long-yields")

    # --- real house prices, 14 countries ---------------------------------------------------
    real, table = {}, {}
    for c in COUNTRIES:
        r = hp[f"{c}|real"]
        ks = sorted(r)
        last = ks[-1]
        base = r.get("2015-Q1")
        peak = max(ks, key=lambda k: r[k])
        pre = r.get("2021-Q4")
        low_since_peak = min((k for k in ks if k >= peak), key=lambda k: r[k])
        table[c] = {
            "last": last, "value": round(r[last], 1),
            "since_2015_pct": round((r[last] / base - 1) * 100, 1) if base else None,
            "since_2021q4_pct": round((r[last] / pre - 1) * 100, 1) if pre else None,
            "peak": peak, "from_peak_pct": round((r[last] / r[peak] - 1) * 100, 1),
            "trough_since_peak": low_since_peak, "peak_to_trough_pct": round((r[low_since_peak] / r[peak] - 1) * 100, 1),
            "first": ks[0],
        }
        real[c] = [[k, round(r[k] / base * 100, 2)] for k in ks if k >= "2000-Q1"] if base else []
    # nominal against real, latest, for the note on Türkiye
    nominal_last = {c: round(hp[f"{c}|nominal"][max(hp[f"{c}|nominal"])], 1) for c in COUNTRIES}

    # --- the United States ---------------------------------------------------------------------
    cs = us["case_shiller"]
    cs_real = {k: cs[k] / uscpi[k] for k in sorted(cs) if k in uscpi}
    cs_base = cs_real["2000-01"]
    cs_real_idx = {k: v / cs_base * 100 for k, v in cs_real.items()}
    rent = us["rent_cpi"]
    price_to_rent = {k: cs[k] / rent[k] for k in sorted(cs) if k in rent}
    ptr_base = price_to_rent["2000-01"]
    ptr_idx = {k: v / ptr_base * 100 for k, v in price_to_rent.items()}
    # the mortgage payment on the median house: 80% loan, 30-year fixed at the quarter's average rate
    mr_q = quarterly_mean(mr)
    med = us["median_price_usd"]
    payment, payment_real = {}, {}
    cpi_q = quarterly_mean(uscpi)
    cpi_last_q = cpi_q[max(cpi_q)]
    for q in sorted(med):
        if q in mr_q and q in cpi_q:
            r = mr_q[q] / 100 / 12
            p = 0.8 * med[q] * r / (1 - (1 + r) ** -360)
            payment[q] = p
            payment_real[q] = p * cpi_last_q / cpi_q[q]
    last_q = max(payment)
    us_out = {
        "case_shiller_real_2000": [[k, round(v, 1)] for k, v in cs_real_idx.items()],
        "price_to_rent_2000": [[k, round(v, 1)] for k, v in ptr_idx.items()],
        "payment_nominal": [[k, round(v)] for k, v in payment.items() if k >= "1990-Q1"],
        "payment_real": [[k, round(v)] for k, v in payment_real.items() if k >= "1990-Q1"],
        "mortgage_rate_q": [[k, round(v, 2)] for k, v in mr_q.items() if k >= "1990-Q1"],
        "latest": {
            "case_shiller": {"date": max(cs), "value": cs[max(cs)]},
            "case_shiller_real_peak": max(cs_real_idx, key=lambda k: cs_real_idx[k]),
            "case_shiller_real_from_peak_pct": round((cs_real_idx[max(cs_real_idx)] / max(cs_real_idx.values()) - 1) * 100, 1),
            "case_shiller_real_vs_2006_peak_pct": round((cs_real_idx[max(cs_real_idx)] / max(v for k, v in cs_real_idx.items() if k < "2010-01") - 1) * 100, 1),
            "price_to_rent": {"date": max(ptr_idx), "value": round(ptr_idx[max(ptr_idx)], 1), "peak_2006": round(max(v for k, v in ptr_idx.items() if k < "2010-01"), 1)},
            "median_price": {"date": max(med), "value": med[max(med)]},
            "mortgage_rate": {"date": max(mr), "value": mr[max(mr)]},
            "payment": {"quarter": last_q, "nominal": round(payment[last_q]), "q4_2019": round(payment["2019-Q4"]), "q4_2021": round(payment["2021-Q4"]),
                        "real_q4_2019": round(payment_real["2019-Q4"]), "real_2006": round(payment_real["2006-Q2"]),
                        "real_peak": {"quarter": max(payment_real, key=lambda k: payment_real[k]), "value": round(max(payment_real.values()))},
                        "real_rank": sum(1 for v in payment_real.values() if v > payment_real[last_q]) + 1, "quarters": len(payment_real)},
            "definition": "Monthly payment on a 30-year fixed loan for 80% of the median sale price of houses sold (MSPUS) at the quarter's average Freddie Mac rate. Nominal USD, and in dollars of the latest quarter using the US CPI. No income series is in the collection, so this is a payment, not an affordability ratio.",
        },
    }

    # --- Türkiye: real KFE, monthly, and the cities ------------------------------------------
    tr_real = {}
    for k in ("turkey", "istanbul", "ankara", "izmir"):
        s = kfe[k]
        rr = {m: s[m] / trcpi[m] for m in sorted(s) if m in trcpi}
        b = rr["2015-01"]
        tr_real[k] = {m: v / b * 100 for m, v in rr.items()}
    tr_tab = {}
    for k, rr in tr_real.items():
        ks = sorted(rr)
        peak = max(ks, key=lambda m: rr[m])
        last = ks[-1]
        tr_tab[k] = {"last": last, "value": round(rr[last], 1), "peak": peak, "peak_value": round(rr[peak], 1), "from_peak_pct": round((rr[last] / rr[peak] - 1) * 100, 1),
                     "since_2015_pct": round(rr[last] - 100, 1), "low_2010s": round(min(v for m, v in rr.items() if "2010-01" <= m < "2020-01"), 1)}
    # real deposit rate: 3-month deposit rate minus CPI inflation over the past year (ex post)
    cpi_yoy = yoy(trcpi, 12)
    dep = trr["deposit_3m"]
    real_dep = {m: dep[m] - cpi_yoy[m] for m in sorted(dep) if m in cpi_yoy}
    hp_yoy = yoy(tr_real["turkey"], 12)
    months = [m for m in sorted(hp_yoy) if m in real_dep and m >= "2011-01"]
    tr_test_levels = test([hp_yoy[m] for m in months], [real_dep[m] for m in months])
    # lead: real deposit rate twelve months earlier against real house price growth now
    keys = sorted(real_dep)
    lag12 = {keys[i]: real_dep[keys[i - 12]] for i in range(12, len(keys))}
    months2 = [m for m in months if m in lag12]
    tr_test_lag = test([hp_yoy[m] for m in months2], [lag12[m] for m in months2], tests=2)
    tr_series = {
        "real_kfe_2015": {k: [[m, round(v, 1)] for m, v in rr.items()] for k, rr in tr_real.items()},
        "real_kfe_yoy": [[m, round(hp_yoy[m], 1)] for m in months],
        "real_deposit_rate": [[m, round(real_dep[m], 1)] for m in months],
        "latest": {"real_deposit_rate": {"date": months[-1], "value": round(real_dep[months[-1]], 1)}, "deposit_3m": dep[max(dep)], "cpi_yoy": round(cpi_yoy[max(cpi_yoy)], 1),
                   "policy_rate": trr["policy_rate"][max(trr["policy_rate"])], "housing_loan_rate": trr["loan_housing"][max(trr["loan_housing"])]},
    }

    # --- the tests: do rates move house prices? ------------------------------------------
    us_real_a = annual_mean(hp["US|real"])
    mr_a = annual_mean(mr)
    years = [y for y in sorted(us_real_a) if y in mr_a and "1972" <= y <= "2025"]
    dp = {years[i]: (us_real_a[years[i]] / us_real_a[years[i - 1]] - 1) * 100 for i in range(1, len(years))}
    dr = {years[i]: mr_a[years[i]] - mr_a[years[i - 1]] for i in range(1, len(years))}
    ys = sorted(dp)
    us_same = test([dp[y] for y in ys], [dr[y] for y in ys], tests=2)
    us_lag = test([dp[ys[i]] for i in range(1, len(ys))], [dr[ys[i - 1]] for i in range(1, len(ys))], tests=2)
    us_levels = test([us_real_a[y] for y in years], [mr_a[y] for y in years])
    cross = []
    for c in YIELD_COUNTRIES:
        y = ly[c]
        cross.append({"country": c, "real_price_change_pct": table[c]["since_2021q4_pct"], "yield_change_pts": round(y[max(y)] - y["2021-12"], 2)})
    cross_r = corr([x["real_price_change_pct"] for x in cross], [x["yield_change_pts"] for x in cross])

    out = {
        "generated_from": {"house-prices": max(hp["US|real"]), "us-housing": max(cs), "us-mortgage-rate": max(mr), "tr-house-prices": max(kfe["turkey"]), "tr-cpi-ppi": max(trcpi), "tr-rates": max(dep), "long-yields": max(ly["US"])},
        "countries": COUNTRIES, "table": table, "real_2015": real, "nominal_last": nominal_last,
        "us": us_out, "tr": {"table": tr_tab, **tr_series},
        "test": {
            "us_years": [ys[0], ys[-1]],
            "us_real_price_vs_mortgage_rate_levels": us_levels,
            "us_real_price_change_vs_rate_change": us_same,
            "us_real_price_change_vs_rate_change_lag1": us_lag,
            "tr_months": [months[0], months[-1]],
            "tr_real_price_yoy_vs_real_deposit_rate": tr_test_levels,
            "tr_real_price_yoy_vs_real_deposit_rate_lag12": tr_test_lag,
            "cross_section": cross, "cross_r": round(cross_r, 2),
            "note": "US: annual means of the BIS real index and the 30-year mortgage rate, year-on-year change in the first against the change in the second, same year and the rate change a year earlier (two lags tested, p_adj multiplied by two). Türkiye: real KFE growth over twelve months against the ex-post real three-month deposit rate, monthly, same month and twelve months earlier (two tests). Cross-section: six countries, printed not tested.",
        },
    }
    with open(os.path.join(ROOT, "data", "house-study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({"table": table, "us_latest": us_out["latest"], "tr_table": tr_tab, "tr_latest": tr_series["latest"], "test": out["test"]}, indent=1))


if __name__ == "__main__":
    main()
