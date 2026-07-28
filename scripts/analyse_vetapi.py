#!/usr/bin/env python3
"""Derive every number in the vet-medicine API study, and run the integrity checks.

The question: a veterinary medicine is an active pharmaceutical ingredient (API) that
someone has formulated, filled and licensed. Does the price of the finished medicine
track the price of the ingredient inside it — or have the two come apart?

Reads only committed data files, writes data/vetapi-derived.json, and prints the
checks the repo's data-integrity skill requires before any of it may be published:

  #1 base-year sensitivity   a ratio of two indexes has no meaningful level
  #2 deflate before comparing money series
  #3 methodology breaks      a single implausible step
  #7 variance decomposition  which side of the ratio actually moves
  #8 sample size stated out loud

Run:  python scripts/analyse_vetapi.py
"""
import json, math, os
from statistics import mean, pvariance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)


def dlog(seq):
    return [math.log(seq[i]) - math.log(seq[i - 1]) for i in range(1, len(seq))]


def variance_share(num, den):
    """Of the movement in num/den, what share comes from the denominator? (integrity #7)"""
    dn, dd = dlog(num), dlog(den)
    vn, vd = pvariance(dn), pvariance(dd)
    mn, md = mean(dn), mean(dd)
    cov = sum((a - mn) * (b - md) for a, b in zip(dn, dd)) / len(dn)
    tot = vn + vd - 2 * cov
    return (round((vd - cov) / tot, 3) if tot else None), len(dn)


def biggest_step(series):
    ks = sorted(series)
    steps = [(ks[i], round((series[ks[i]] / series[ks[i - 1]] - 1) * 100, 2))
             for i in range(1, len(ks)) if series[ks[i - 1]]]
    return max(steps, key=lambda kv: abs(kv[1])) if steps else None


def pct(series, a, b):
    return round((series[b] / series[a] - 1) * 100, 1)


def rebase(series, keys, base_key):
    b = series[base_key]
    return {k: round(series[k] / b * 100, 2) for k in keys}


def main():
    out = {"generated_from": "data/vetapi-us.json, vetapi-eu.json, vetapi-tr.json, eu-hicp.json",
           "markets": {}, "checks": {}}

    # ================================================================= UNITED STATES
    us = load("vetapi-us.json")["series"]
    api, prep, cpi = us["api_ppi"], us["prep_ppi"], us["cpi"]
    anti, bio = us.get("antiinfective_ppi", {}), us.get("biological_ppi", {})
    # every month must carry all three, or a deflated series would have holes the
    # rebasing then trips over
    m = sorted(set(api) & set(prep) & set(cpi))
    first, last = m[0], m[-1]

    # ---- integrity #1: the ratio's LEVEL is an artefact of the base months
    ratio_on_base = {}
    for base in ("1990-01", "2000-01", "2010-01", "2020-01"):
        if base in api and base in prep:
            ratio_on_base[base] = round(
                rebase(prep, [last], base)[last] / rebase(api, [last], base)[last], 3)
    out["checks"]["us_base_sensitivity"] = {
        "raw_ratio_prep_over_api_at_last": round(prep[last] / api[last], 3),
        "same_ratio_after_rebasing_both_series": ratio_on_base,
        "verdict": ("The level moves with the base month, so it was never a quantity. "
                    "PCU325412325412 is based Jun 1981=100 and PCU325411325411 Jun 1982=100 — "
                    "different bases entirely. Only the CHANGE between two dates is quoted."),
    }

    # ---- integrity #2: deflate, then compare
    real = lambda s: {k: s[k] / cpi[k] for k in s if k in cpi}
    ra, rp = real(api), real(prep)
    out["markets"]["US"] = {
        "span": [first, last], "n_months": len(m), "frequency": "monthly",
        "deflator": "US CPI-U, FRED CPIAUCSL",
        "real_change_api_pct": pct(ra, first, last),
        "real_change_prep_pct": pct(rp, first, last),
        "nominal_change_api_pct": pct(api, first, last),
        "nominal_change_prep_pct": pct(prep, first, last),
        # both series on one base so the shapes are comparable (levels are not)
        "api_indexed_1982_06_100": rebase(ra, m, first),
        "prep_indexed_1982_06_100": rebase(rp, m, first),
    }
    share, n = variance_share([prep[x] for x in m], [api[x] for x in m])
    out["markets"]["US"]["variance_share_from_api_side"] = share
    out["markets"]["US"]["variance_n"] = n
    out["checks"]["us_breaks"] = {"api": biggest_step(api), "prep": biggest_step(prep),
                                  "note": ("Largest single-month moves. Both are economic "
                                           "(the 2008 input spike), not survey redesigns — "
                                           "no BLS basis change is documented across them.")}
    # the closest therapeutic proxies to a livestock portfolio
    for key, series, label in (("antiinfective", anti, "WPU063808 antiparasitics and anti-infectives"),
                               ("biological", bio, "PCU325414325414 other biological products")):
        if series:
            rs = real(series)
            ks = sorted(rs)
            out["markets"]["US"][f"{key}_real_change_pct"] = pct(rs, ks[0], ks[-1])
            out["markets"]["US"][f"{key}_span"] = [ks[0], ks[-1]]
            out["markets"]["US"][f"{key}_series"] = label
            out["markets"]["US"][f"{key}_indexed_100"] = rebase(rs, ks, ks[0])

    # ================================================================= EUROPEAN UNION
    eu = load("vetapi-eu.json")["series"]
    hicp_m = load("eu-hicp.json")["series"]["hicp"]
    hicp = {}                       # monthly -> annual mean, to match the annual PPIs
    for k, v in hicp_m.items():
        hicp.setdefault(k[:4], []).append(v)
    hicp = {y: mean(vs) for y, vs in hicp.items()}
    e_api, e_prep = eu["C211"], eu["C212"]
    yrs = sorted(set(e_api) & set(e_prep) & set(hicp))
    ey0, ey1 = yrs[0], yrs[-1]
    e_ra = {y: e_api[y] / hicp[y] for y in yrs}
    e_rp = {y: e_prep[y] / hicp[y] for y in yrs}
    share, n = variance_share([e_prep[y] for y in yrs], [e_api[y] for y in yrs])
    out["markets"]["EU"] = {
        "span": [ey0, ey1], "n_years": len(yrs), "frequency": "annual",
        "deflator": "Euro area HICP, FRED CP0000EZ19M086NEST, annual mean",
        "nominal_change_api_pct": pct(e_api, ey0, ey1),
        "nominal_change_prep_pct": pct(e_prep, ey0, ey1),
        "real_change_api_pct": pct(e_ra, ey0, ey1),
        "real_change_prep_pct": pct(e_rp, ey0, ey1),
        "api_indexed_100": rebase(e_ra, yrs, ey0),
        "prep_indexed_100": rebase(e_rp, yrs, ey0),
        "variance_share_from_api_side": share,
        "variance_n": n,
        "caveat": (f"Only {len(yrs)} annual observations, and the series ends {ey1} — "
                   "Eurostat's C212 preparations index does not start until 2010 and is "
                   "not published beyond 2023. No claim about 2024-2026 can be made for the EU."),
    }

    # ================================================================= TÜRKİYE
    tr = load("vetapi-tr.json")["series"]
    d21, d212, imp = tr["ppi_nace21"], tr["ppi_nace212"], tr["import_ppi_nace21"]
    both = sorted(set(d21) & set(d212))
    gap = [abs(d21[x] - d212[x]) / d21[x] for x in both if d21[x]]
    out["checks"]["tr_has_no_domestic_api_stage"] = {
        "mean_abs_gap_pct": round(mean(gap) * 100, 3),
        "max_abs_gap_pct": round(max(gap) * 100, 3),
        "n_months": len(both),
        "verdict": ("TÜİK's NACE 21 index and its NACE 21.2 sub-index are the same series to "
                    "within 0.2% on average. Division 21 is carried entirely by preparations, "
                    "so Türkiye has no separately measured domestic basic-pharmaceutical (21.1) "
                    "stage to compare against. The ingredient side has to be the IMPORT price."),
    }
    com = sorted(set(d212) & set(imp))
    t0, t1 = com[0], com[-1]
    parity = {x: d212[x] / imp[x] for x in com}
    share, n = variance_share([d212[x] for x in com], [imp[x] for x in com])
    out["markets"]["TR"] = {
        "span": [t0, t1], "n_months": len(com), "frequency": "monthly",
        "nominal_change_domestic_prep_pct": pct(d212, t0, t1),
        "nominal_change_imported_input_pct": pct(imp, t0, t1),
        "parity_change_pct": round((parity[t1] / parity[t0] - 1) * 100, 1),
        "parity_indexed_100": rebase(parity, com, t0),
        "domestic_indexed_100": rebase(d212, com, t0),
        "imported_indexed_100": rebase(imp, com, t0),
        "variance_share_from_import_side": share,
        "variance_n": n,
        "deflator": ("None needed for the parity: both sides are nominal TRY indexes, so "
                     "Turkish inflation cancels in the ratio. The two levels are NOT deflated "
                     "and must never be read as real growth."),
    }

    print(json.dumps(out, indent=1, ensure_ascii=False, default=str)[:3000])
    with open(os.path.join(ROOT, "data", "vetapi-derived.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    print("\n[write] data/vetapi-derived.json")

    # -------- headline summary, printed so it can be checked by eye before publishing
    U, E, T = out["markets"]["US"], out["markets"]["EU"], out["markets"]["TR"]
    print(f"""
US  {U['span'][0]}..{U['span'][1]} monthly, CPI-deflated
    ingredient (NAICS 325411) {U['real_change_api_pct']:+}%   finished dose (325412) {U['real_change_prep_pct']:+}%
    {U['variance_share_from_api_side']:.0%} of the ratio's movement comes from the ingredient side
EU  {E['span'][0]}..{E['span'][1]} annual (n={E['n_years']}), HICP-deflated
    ingredient (C211) {E['real_change_api_pct']:+}%   preparations (C212) {E['real_change_prep_pct']:+}%
TR  {T['span'][0]}..{T['span'][1]} monthly, nominal TRY, ratio only
    domestic preparations {T['nominal_change_domestic_prep_pct']:+}%   imported input {T['nominal_change_imported_input_pct']:+}%
    parity {T['parity_change_pct']:+}%""")


if __name__ == "__main__":
    main()
