#!/usr/bin/env python3
"""Every number on tr-power.html, recomputed from the committed data files.

    python3 scripts/tr_power_study.py     # writes data/tr-power-study.json

Inputs (all in data/): electricity-mix (Ember via OWID, TWh by source), renewables-share
(Ember via OWID, %), elec-eu (Eurostat nrg_pc_205, industrial band IC, national currency
per kWh, excl. VAT and recoverable taxes, half-yearly), energy-household-eu (Eurostat
nrg_pc_204, household band DC, EUR per kWh incl. all taxes, half-yearly), tr-cpi-ppi
(TÜİK CPI 2025 = 100 via EVDS, the deflator), tr-fx-monthly (EUR/TRY via EVDS),
wb-commodities (World Bank Pink Sheet: European natural gas, Australian coal).

Rules applied from .claude/skills/data-integrity: money is deflated and the deflator
named; the effective sample size discounts autocorrelation before any p is read;
nothing here spans a known break without saying so.
"""
import json
import math
import os
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def series(name):
    return json.load(open(os.path.join(ROOT, "data", name + ".json")))["series"]


def half_mean(s, year, half):
    months = [f"{year}-{m:02d}" for m in (range(1, 7) if half == 1 else range(7, 13))]
    v = [s[m] for m in months if m in s]
    return sum(v) / len(v) if v else None


def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    den = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / den if den else float("nan")


def ac1(a):
    return corr(a[:-1], a[1:])


def t_p(r, n):
    """Two-sided p for a correlation with n observations, Student t via the normal approximation
    for the tail (adequate here; the point is the order of magnitude)."""
    if n <= 2 or abs(r) >= 1:
        return float("nan")
    t = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2
    # Student t survival by numeric integration of the density (no scipy in the sandbox)
    def dens(x):
        return math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2)) * (1 + x * x / df) ** (-(df + 1) / 2)
    hi, steps = abs(t) + 40, 4000
    h = (hi - abs(t)) / steps
    tail = sum(dens(abs(t) + (i + 0.5) * h) for i in range(steps)) * h
    return 2 * tail


def stats(x, y):
    n = len(x)
    r = corr(x, y)
    r1, r2 = ac1(x), ac1(y)
    n_eff = n * (1 - r1 * r2) / (1 + r1 * r2)
    return {"n": n, "r": round(r, 3), "p": round(t_p(r, n), 4), "n_eff": round(n_eff, 1), "p_adj": round(t_p(r, max(3, round(n_eff))), 3),
            "ac1_x": round(r1, 2), "ac1_y": round(r2, 2)}


def main():
    mix = series("electricity-mix")
    share = series("renewables-share")["TR"]
    ind = series("elec-eu")["TR"]
    hh = series("energy-household-eu")["TR"]
    cpi = series("tr-cpi-ppi")["cpi"]
    fx = series("tr-fx-monthly")["eur_try"]
    wb = series("wb-commodities")

    sources = ["coal", "gas", "hydro", "wind", "solar", "bioenergy", "other_renewables", "oil", "nuclear"]
    years = sorted(y for y in mix["TR|coal"] if y >= "2000")
    gen = {s: [[y, mix[f"TR|{s}"].get(y)] for y in years] for s in sources}
    total = {y: sum(mix[f"TR|{s}"].get(y, 0) or 0 for s in sources) for y in years}
    shares = {}
    for y in ("2010", "2015", "2020", "2025"):
        t = total[y]
        shares[y] = {"total_twh": round(t, 1), "coal": round(100 * mix["TR|coal"][y] / t, 1), "gas": round(100 * mix["TR|gas"][y] / t, 1),
                     "hydro": round(100 * mix["TR|hydro"][y] / t, 1), "wind_solar": round(100 * (mix["TR|wind"][y] + mix["TR|solar"][y]) / t, 1),
                     "renewables_ember": round(share[y], 1)}

    # Prices, half-yearly: nominal lira, lira at 2025 prices (CPI 2025 = 100), euro at the half-year average rate.
    price = []
    for k in sorted(ind):
        y, h = int(k[:4]), int(k[6])
        c, f = half_mean(cpi, y, h), half_mean(fx, y, h)
        if not c or not f:
            continue
        price.append({"period": k, "industrial_try": round(ind[k], 4), "industrial_try_2025": round(ind[k] / c * 100, 3),
                      "industrial_eur": round(ind[k] / f, 4), "household_eur": round(hh[k], 4) if k in hh else None,
                      "cpi": round(c, 2), "eur_try": round(f, 3)})

    # Fuel import prices, annual means (USD per MMBtu, USD per tonne).
    def annual_mean(s):
        ys = {}
        for d, v in s.items():
            ys.setdefault(d[:4], []).append(v)
        return {y: round(sum(v) / len(v), 2) for y, v in sorted(ys.items())}
    gas_eur = annual_mean(wb["natgas_eur"])
    coal_aus = annual_mean(wb["coal_aus"])

    # The test: renewables share against the real industrial price, annual means of the halves.
    by_year = {}
    for p in price:
        by_year.setdefault(p["period"][:4], []).append(p["industrial_try_2025"])
    yrs = sorted(y for y in by_year if y in share and len(by_year[y]) == 2)
    x = [share[y] for y in yrs]
    yv = [sum(by_year[y]) / 2 for y in yrs]
    levels = stats(x, yv)
    dx = [x[i] - x[i - 1] for i in range(1, len(x))]
    dy = [yv[i] / yv[i - 1] - 1 for i in range(1, len(yv))]
    changes = stats(dx, dy)
    # and the same price against the European gas price, the rival explanation
    gyrs = [y for y in yrs if y in gas_eur]
    gas_levels = stats([gas_eur[y] for y in gyrs], [sum(by_year[y]) / 2 for y in gyrs])
    gas_changes = stats([gas_eur[gyrs[i]] / gas_eur[gyrs[i - 1]] - 1 for i in range(1, len(gyrs))],
                        [sum(by_year[gyrs[i]]) / 2 / (sum(by_year[gyrs[i - 1]]) / 2) - 1 for i in range(1, len(gyrs))])

    out = {
        "_readme": "Written by scripts/tr_power_study.py from the committed data files; tr-power.html draws from this and nothing else.",
        "generated_from": {"electricity-mix": "Ember via Our World in Data, TWh", "renewables-share": "Ember via Our World in Data, % of generation",
                            "elec-eu": "Eurostat nrg_pc_205, band IC (500-1 999 MWh), excl. VAT and recoverable taxes, TRY per kWh, half-yearly",
                            "energy-household-eu": "Eurostat nrg_pc_204, band DC (2 500-4 999 kWh), all taxes, EUR per kWh, half-yearly",
                            "tr-cpi-ppi": "TÜİK CPI 2025 = 100 via TCMB EVDS (deflator)", "tr-fx-monthly": "EUR/TRY monthly via TCMB EVDS, half-year means",
                            "wb-commodities": "World Bank Pink Sheet: European natural gas USD/MMBtu, Australian coal USD/t, annual means"},
        "years": years,
        "generation_twh": gen,
        "total_twh": [[y, round(total[y], 1)] for y in years],
        "renewables_share": [[y, share[y]] for y in years if y in share],
        "shares": shares,
        "price": price,
        "gas_eur_usd_mmbtu": gas_eur,
        "coal_aus_usd_t": coal_aus,
        "test": {
            "years": [yrs[0], yrs[-1]],
            "share_vs_real_price_levels": levels,
            "share_vs_real_price_changes": changes,
            "gas_vs_real_price_levels": gas_levels,
            "gas_vs_real_price_changes": gas_changes,
            "note": "Levels of two trending series; n_eff discounts for lag-1 autocorrelation (n_eff = n(1-r1 r2)/(1+r1 r2)). p_adj is the p at n_eff. Sign of the share-price correlation is positive: the share rose while the real price rose.",
        },
    }
    with open(os.path.join(ROOT, "data", "tr-power-study.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({"shares": shares, "test": out["test"]}, indent=1))


if __name__ == "__main__":
    main()
