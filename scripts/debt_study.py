#!/usr/bin/env python3
"""Every number on debt.html, recomputed from the committed data files.

    python3 scripts/debt_study.py     # writes data/debt-study.json

Inputs (all in data/): imf-weo (general government gross and net debt, overall and primary
net lending and revenue, % of GDP; real growth; nominal GDP in national currency; actuals and
IMF projections) and long-yields (ten-year government yields, monthly averages, via FRED).

Identities used, with i, d, pb in per cent of GDP, g nominal and gamma real growth:
  net interest       i_t = pb_t - balance_t
  rate on the stock  r_t = i_t (1 + g_t) / d_{t-1}
  debt dynamics      d_t - d_{t-1} = i_t - pb_t - g_t/(1+g_t) d_{t-1} + residual
                     with the growth term split into real growth gamma_t/(1+g_t) d_{t-1}
                     and inflation (g_t - gamma_t)/(1+g_t) d_{t-1}
  holds the ratio    pb* = (r - g)/(1 + g) d_{t-1}
The one estimate on the page is the pass-through: r_t - r_{t-1} = a + lambda (y_t - r_{t-1}),
y the annual mean ten-year yield, OLS per country and pooled with country intercepts.
"""
import json
import math
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = ["US", "GB", "FR", "IT", "DE", "JP"]            # the six in bonds.html
# Canada and Korea are left out: their net interest is negative (pension and reserve assets
# earn more than the debt costs) and their gross-debt changes leave residuals of 14 to 30
# points, so neither the rate nor the debt dynamics can be read.
MORE = ["ES", "NL", "AU"]
# Japan's net interest is swamped by asset income and its yield was held by the central bank,
# so its pass-through is printed but kept out of the pooled estimate.
POOL_EXCLUDE = {"JP"}
WEO_LAST_ACTUAL = "2025"   # the WEO file does not mark the split; the release's last actual year
FIRST = "1990"
EST = ("1996", WEO_LAST_ACTUAL)                           # pass-through estimation window
WINDOWS = {"2021-25": ("2021", "2025"), "2026-31": ("2026", "2031")}


def series(name):
    return json.load(open(os.path.join(ROOT, "data", name + ".json")))["series"]


def r2(v, d=2):
    return None if v is None or v != v else round(v, d)


def mean(vals):
    vals = [v for v in vals if v is not None]
    return st.mean(vals) if vals else None


def ols(x, y):
    """Slope, its standard error and the intercept of y on x with a constant."""
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    a0 = my - b * mx
    res = [c - a0 - b * a for a, c in zip(x, y)]
    s2 = sum(e * e for e in res) / (n - 2)
    return b, math.sqrt(s2 / sxx), a0


def annual_mean(s):
    by = {}
    for k, v in s.items():
        by.setdefault(k[:4], []).append(v)
    return {y: sum(v) / len(v) for y, v in sorted(by.items()) if len(v) >= 6}


def country(weo, c):
    get = lambda k: weo.get(f"{c}|{k}", {})
    gross, bal, prim, ngdp, real, rev = (get(k) for k in ("GGXWDG_NGDP", "GGXCNL_NGDP", "GGXONLB_NGDP", "NGDP", "NGDP_RPCH", "GGR_NGDP"))
    net = get("GGXWDN_NGDP")
    rows = {}
    for y in sorted(set(gross) & set(bal) & set(prim) & set(ngdp)):
        prev = str(int(y) - 1)
        if prev not in gross or prev not in ngdp:
            continue
        i = prim[y] - bal[y]
        g = ngdp[y] / ngdp[prev] - 1
        gam = real[y] / 100 if y in real else None
        d0 = gross[prev]
        row = {
            "debt": gross[y], "net_debt": net.get(y), "balance": bal[y], "primary": prim[y], "interest": i,
            "revenue": rev.get(y), "interest_rev": i / rev[y] * 100 if rev.get(y) else None,
            "g": g * 100, "r": i * (1 + g) / d0 * 100, "stabilising_primary": (i * (1 + g) / d0 - g) / (1 + g) * d0,
            "d_change": gross[y] - d0,
            "c_primary": -prim[y], "c_interest": i,
            "c_real": -gam / (1 + g) * d0 if gam is not None else None,
            "c_inflation": -(g - gam) / (1 + g) * d0 if gam is not None else None,
        }
        row["r_minus_g"] = row["r"] - row["g"]
        if gam is not None:
            row["c_residual"] = row["d_change"] - (row["c_primary"] + row["c_interest"] + row["c_real"] + row["c_inflation"])
        rows[y] = row
    return rows


def window(rows, a, b, key):
    ys = [y for y in rows if a <= y <= b]
    vals = [rows[y].get(key) for y in ys]
    return sum(vals) if ys and None not in vals else None


def main():
    weo = series("imf-weo")
    ly = series("long-yields")
    out_c, pooled, iv_rows = {}, [], []
    for c in CORE + MORE:
        rows = country(weo, c)
        if not rows or WEO_LAST_ACTUAL not in rows:
            print("missing", c)
            continue
        a, proj = rows[WEO_LAST_ACTUAL], rows.get("2031")
        years = [y for y in rows if y >= FIRST]
        actual = [y for y in years if y <= WEO_LAST_ACTUAL]
        # Net interest near zero or negative means asset income swamps the coupon: the rate
        # on the stock is then not a rate, and the country is shown for debt dynamics only.
        rate_ok = min(rows[y]["interest"] for y in actual if y >= "2015") > 0.1
        e = {"rate_ok": rate_ok, "core": c in CORE}
        e["series"] = {k: [[y, r2(rows[y].get(k))] for y in years] for k in ("debt", "interest", "interest_rev", "r", "g", "r_minus_g")}
        for k in ("debt", "net_debt", "interest", "interest_rev", "r", "g", "r_minus_g", "primary", "stabilising_primary"):
            e[k + "_2025"] = r2(a.get(k))
            e[k + "_2031"] = r2(proj.get(k)) if proj else None
        e["r_minus_g_2015_19"] = r2(mean([rows[y]["r_minus_g"] for y in ("2015", "2016", "2017", "2018", "2019") if y in rows]))
        e["r_minus_g_2021_23"] = r2(mean([rows[y]["r_minus_g"] for y in ("2021", "2022", "2023") if y in rows]))
        # the 1990s benchmark and the post-2015 low
        nineties = [y for y in actual if "1990" <= y <= "1999"]
        if nineties:
            pk = max(nineties, key=lambda y: rows[y]["interest"])
            e["interest_90s_peak"] = {"year": pk, "value": r2(rows[pk]["interest"]), "rev": r2(rows[pk]["interest_rev"])}
        low = min((y for y in actual if y >= "2015"), key=lambda y: rows[y]["interest"])
        e["interest_low"] = {"year": low, "value": r2(rows[low]["interest"]), "rev": r2(rows[low]["interest_rev"])}
        # debt dynamics over two windows, points of GDP summed over the years
        e["dynamics"] = {}
        for w, (lo, hi) in WINDOWS.items():
            if lo not in rows or hi not in rows:
                continue
            e["dynamics"][w] = {k: r2(window(rows, lo, hi, k), 1) for k in ("d_change", "c_primary", "c_interest", "c_real", "c_inflation", "c_residual")}
            e["dynamics"][w]["from"] = r2(rows[str(int(lo) - 1)]["debt"], 1) if str(int(lo) - 1) in rows else None
            e["dynamics"][w]["to"] = r2(rows[hi]["debt"], 1)
        # yields: latest month, and the pass-through estimate
        if c in ly:
            s = ly[c]
            lm = max(s)
            y10 = s[lm]
            e["ten_year"] = {"last": lm, "value": r2(y10), "first": min(s)}
            if rate_ok and proj:
                g31 = proj["g"] / 100
                e["yield_minus_g2031"] = r2(y10 - proj["g"])
                e["stabilising_at_market"] = r2((y10 / 100 - g31) / (1 + g31) * proj["debt"])
                e["gap_at_market"] = r2(proj["primary"] - (y10 / 100 - g31) / (1 + g31) * proj["debt"])
            ya = annual_mean(s)
            est = [y for y in actual if EST[0] <= y <= EST[1] and y in ya and str(int(y) - 1) in rows]
            if rate_ok and len(est) >= 12:
                x = [ya[y] - rows[str(int(y) - 1)]["r"] for y in est]
                dy = [rows[y]["r"] - rows[str(int(y) - 1)]["r"] for y in est]
                lam, se, a0 = ols(x, dy)
                e["pass_through"] = {"lambda": r2(lam, 3), "se": r2(se, 3), "n": len(est), "years": [est[0], est[-1]],
                                     "half_life": r2(math.log(0.5) / math.log(1 - lam), 1) if 0 < lam < 1 else None}
                if c not in POOL_EXCLUDE:
                    pooled.append((c, est, x, dy))
                    # instrument: the same gap measured against r two years back, which shares no
                    # measurement error with this year's change
                    ok = [i for i, y in enumerate(est) if str(int(y) - 2) in rows]
                    iv_rows.append(([x[i] for i in ok], [dy[i] for i in ok], [ya[est[i]] - rows[str(int(est[i]) - 2)]["r"] for i in ok]))
        out_c[c] = e

    # pooled pass-through with country intercepts (demean within country)
    X, Y = [], []
    for c, est, x, dy in pooled:
        mx, my = st.mean(x), st.mean(dy)
        X += [v - mx for v in x]
        Y += [v - my for v in dy]
    lam = sum(a * b for a, b in zip(X, Y)) / sum(a * a for a in X)
    res = [b - lam * a for a, b in zip(X, Y)]
    se = math.sqrt(sum(v * v for v in res) / (len(X) - len(pooled) - 1) / sum(a * a for a in X))
    dm = lambda v: [a - st.mean(v) for a in v]
    Xi, Yi, Zi = [], [], []
    for x, dy, z in iv_rows:
        Xi += dm(x); Yi += dm(dy); Zi += dm(z)
    lam_iv = sum(a * b for a, b in zip(Zi, Yi)) / sum(a * b for a, b in zip(Zi, Xi))
    pool = {"lambda": r2(lam, 3), "se": r2(se, 3), "n": len(X), "countries": [p[0] for p in pooled],
            "half_life": r2(math.log(0.5) / math.log(1 - lam), 1),
            "lambda_iv": r2(lam_iv, 3), "half_life_iv": r2(math.log(0.5) / math.log(1 - lam_iv), 1)}
    # where the rate on the stock goes by 2031 if the ten-year stays at today's level, at the pooled speed
    for c, e in out_c.items():
        if "ten_year" in e and e["rate_ok"] and e.get("r_2025") is not None:
            r, y = e["r_2025"], e["ten_year"]["value"]
            for _ in range(6):
                r += lam * (y - r)
            e["r_2031_at_market"] = r2(r)
            if e.get("g_2031") is not None:
                e["r_minus_g_2031_at_market"] = r2(r - e["g_2031"])

    out = {
        "generated_from": {"imf-weo": "actuals to " + WEO_LAST_ACTUAL + ", projections to 2031", "long-yields": max(ly["US"])},
        "weo_last_actual": WEO_LAST_ACTUAL, "core": CORE, "more": MORE, "pass_through_pooled": pool, "countries": out_c,
        "note": "Net interest = primary balance - overall balance (IMF WEO, general government). r = interest over last year's gross debt, grossed up by nominal GDP growth g. Debt dynamics split the change in the gross debt ratio into the primary deficit, interest, real growth, inflation (GDP deflator) and a residual (stock-flow adjustments). Pass-through: OLS of the yearly change in r on the gap between the annual-mean ten-year yield and last year's r.",
    }
    with open(os.path.join(ROOT, "data", "debt-study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("pooled", pool)
    for c, e in out_c.items():
        print(c, json.dumps({k: v for k, v in e.items() if k != "series"}))


if __name__ == "__main__":
    main()
