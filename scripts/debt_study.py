#!/usr/bin/env python3
"""Every number on debt.html, recomputed from the committed data files.

    python3 scripts/debt_study.py     # writes data/debt-study.json

Inputs (all in data/): imf-weo (general government gross and net debt, overall and primary
net lending, % of GDP, and nominal GDP in national currency, actuals and IMF projections)
and long-yields (ten-year government yields, monthly averages, via FRED).

The interest bill is an identity in the WEO data: net interest = primary balance - overall
balance. The rate paid on the stock is that bill over last year's debt, grossed up for
growth: r_t = i_t (1 + g_t) / d_{t-1}, with i and d in per cent of GDP and g nominal GDP
growth. The debt-stabilising primary balance is (r - g) / (1 + g) x d_{t-1}.
"""
import json
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Canada is left out: its net interest is negative (pension-fund asset income exceeds the
# interest it pays), so a rate on its gross debt means nothing. Japan stays, with the caveat.
COUNTRIES = ["US", "GB", "FR", "IT", "DE", "JP"]
WEO_LAST_ACTUAL = "2025"   # the WEO file does not mark the split; the release's last actual year
FIRST = "1995"


def series(name):
    return json.load(open(os.path.join(ROOT, "data", name + ".json")))["series"]


def r2(v, d=2):
    return None if v is None else round(v, d)


def mean(vals):
    vals = [v for v in vals if v is not None]
    return st.mean(vals) if vals else None


def highest_since(s, key):
    """The last year before `key` at which the series was at or above its value at `key`."""
    v = s[key]
    for k in sorted(s, reverse=True):
        if k < key and s[k] >= v:
            return k
    return None


def country(weo, c):
    gross, bal, prim, ngdp = (weo.get(f"{c}|{k}", {}) for k in ("GGXWDG_NGDP", "GGXCNL_NGDP", "GGXONLB_NGDP", "NGDP"))
    net = weo.get(f"{c}|GGXWDN_NGDP", {})
    rows = {}
    for y in sorted(set(gross) & set(bal) & set(prim) & set(ngdp)):
        prev = str(int(y) - 1)
        if prev not in gross or prev not in ngdp:
            continue
        i = prim[y] - bal[y]
        g = ngdp[y] / ngdp[prev] - 1
        r = i * (1 + g) / gross[prev]
        stab = (r - g) / (1 + g) * gross[prev]
        rows[y] = {
            "debt": gross[y], "net_debt": net.get(y), "balance": bal[y], "primary": prim[y], "interest": i,
            "g": g * 100, "r": r * 100, "r_minus_g": (r - g) * 100,
            "r_net": i * (1 + g) / net[prev] * 100 if net.get(prev, 0) > 5 else None,
            "stabilising_primary": stab, "primary_gap": prim[y] - stab,
            # debt dynamics split: change in the ratio = snowball (r-g) - primary balance + residual
            "d_change": gross[y] - gross[prev], "snowball": stab,
        }
    return rows


def main():
    weo = series("imf-weo")
    ly = series("long-yields")

    out_c, table = {}, []
    for c in COUNTRIES:
        rows = country(weo, c)
        if not rows:
            print("missing", c)
            continue
        years = [y for y in rows if y >= FIRST]
        interest = {y: rows[y]["interest"] for y in rows}
        actual = [y for y in years if y <= WEO_LAST_ACTUAL]
        low_i = min(actual, key=lambda y: interest[y] if y >= "2015" else 1e9)
        yl = ly.get(c)
        y10 = None
        if yl:
            lm = max(yl)
            y10 = {"last": lm, "value": r2(yl[lm]), "dec_2021": r2(yl.get("2021-12"))}
        a = rows[WEO_LAST_ACTUAL]
        pre = mean([rows[y]["r_minus_g"] for y in ("2015", "2016", "2017", "2018", "2019") if y in rows])
        cheap = mean([rows[y]["r_minus_g"] for y in ("2021", "2022", "2023") if y in rows])
        proj = rows.get("2031")
        entry = {
            "series": {k: [[y, r2(rows[y][k])] for y in years] for k in ("debt", "net_debt", "interest", "r", "g", "r_minus_g", "primary", "stabilising_primary")},
            "debt_2025": r2(a["debt"], 1), "net_debt_2025": r2(a["net_debt"], 1), "debt_2031": r2(proj["debt"], 1) if proj else None,
            "interest_2025": r2(a["interest"]), "interest_low": {"year": low_i, "value": r2(interest[low_i])},
            "interest_2031": r2(proj["interest"]) if proj else None,
            "interest_highest_since": highest_since({y: interest[y] for y in rows if y <= WEO_LAST_ACTUAL}, WEO_LAST_ACTUAL),
            "r_2025": r2(a["r"]), "g_2025": r2(a["g"]), "r_minus_g_2025": r2(a["r_minus_g"]),
            "r_net_2025": r2(a["r_net"]),
            "r_minus_g_2015_19": r2(pre), "r_minus_g_2021_23": r2(cheap),
            "r_2031": r2(proj["r"]) if proj else None, "g_2031": r2(proj["g"]) if proj else None,
            "r_minus_g_2031": r2(proj["r_minus_g"]) if proj else None,
            "primary_2025": r2(a["primary"]), "stabilising_2025": r2(a["stabilising_primary"]),
            "primary_2031": r2(proj["primary"]) if proj else None, "stabilising_2031": r2(proj["stabilising_primary"]) if proj else None,
            "ten_year": y10,
        }
        if y10:
            # where the bill drifts if the whole gross stock carried today's ten-year yield; an identity
            entry["interest_if_repriced"] = r2(a["debt"] * y10["value"] / 100)
            entry["yield_minus_r"] = r2(y10["value"] - a["r"])
            entry["yield_minus_g2031"] = r2(y10["value"] - proj["g"]) if proj else None
            # the primary balance that holds the 2031 debt ratio if the whole stock paid today's
            # ten-year yield and nominal growth ran at the IMF's 2031 rate: arithmetic, not a forecast
            yv, g31 = y10["value"] / 100, proj["g"] / 100
            entry["stabilising_at_market"] = r2((yv - g31) / (1 + g31) * proj["debt"])
            entry["gap_at_market"] = r2(proj["primary"] - (yv - g31) / (1 + g31) * proj["debt"])
        out_c[c] = entry
        table.append(c)

    out = {
        "generated_from": {"imf-weo": "actuals to " + WEO_LAST_ACTUAL + ", projections to 2031", "long-yields": max(ly["US"])},
        "weo_last_actual": WEO_LAST_ACTUAL, "countries": out_c,
        "note": "Net interest = primary balance - overall balance (IMF WEO, general government). r = interest over last year's gross debt, grossed up by nominal GDP growth g. r - g above zero means the debt ratio grows unless the primary balance is in surplus by (r - g)/(1 + g) times the debt.",
    }
    with open(os.path.join(ROOT, "data", "debt-study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    keys = ("debt_2025", "net_debt_2025", "debt_2031", "interest_low", "interest_2025", "interest_2031", "interest_highest_since",
            "r_2025", "r_net_2025", "g_2025", "r_minus_g_2015_19", "r_minus_g_2021_23", "r_minus_g_2025", "r_2031", "g_2031", "r_minus_g_2031",
            "primary_2025", "stabilising_2025", "primary_2031", "stabilising_2031", "ten_year", "interest_if_repriced", "yield_minus_r", "yield_minus_g2031", "stabilising_at_market", "gap_at_market")
    for c in table:
        print(c, json.dumps({k: out_c[c].get(k) for k in keys}))


if __name__ == "__main__":
    main()
