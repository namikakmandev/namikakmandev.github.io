#!/usr/bin/env python3
"""Derive every number that appears in the vet-medicine API study, and check it.

Reads only committed data files. Prints a block of JSON that the study page embeds,
plus the integrity checks the repo's data-integrity skill requires:

  * base-year sensitivity  — if a "level" moves when the base moves, it was never a level
  * deflated correlations  — nominal money series trend, and two trends correlate
  * methodology breaks     — a single implausible year-on-year step
  * variance decomposition — which side of the ratio actually moves
  * lag test               — a peak off zero is only a lead if it clearly beats lag 0

Run:  python scripts/analyse_vetapi.py
"""
import json, math, os
from statistics import mean, pvariance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)


def annual(monthly):
    """{YYYY-MM: v} -> {YYYY: mean}. Partial years are kept but flagged by count."""
    buckets = {}
    for k, v in monthly.items():
        buckets.setdefault(k[:4], []).append(v)
    return {y: mean(vs) for y, vs in buckets.items()}, {y: len(vs) for y, vs in buckets.items()}


def dlog(seq):
    return [math.log(seq[i]) - math.log(seq[i - 1]) for i in range(1, len(seq))]


def corr(a, b):
    if len(a) < 3 or len(a) != len(b):
        return None
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return round(num / den, 3) if den else None


def rebase(series, base_key):
    """Index a series so base_key = 100. The whole point: the choice is visible."""
    b = series.get(base_key)
    if not b:
        return {}
    return {k: round(v / b * 100, 2) for k, v in series.items()}


def biggest_step(series):
    """Largest one-period % change — a methodology break usually shows up here."""
    ks = sorted(series)
    steps = [(ks[i], round((series[ks[i]] / series[ks[i - 1]] - 1) * 100, 2))
             for i in range(1, len(ks)) if series[ks[i - 1]]]
    if not steps:
        return None
    return max(steps, key=lambda kv: abs(kv[1]))


def variance_share_denominator(num, den):
    """Of the movement in num/den, how much comes from the denominator? (integrity #7)"""
    dn, dd = dlog(num), dlog(den)
    if len(dn) < 3:
        return None
    vn, vd = pvariance(dn), pvariance(dd)
    mn, md = mean(dn), mean(dd)
    cov = sum((a - mn) * (b - md) for a, b in zip(dn, dd)) / len(dn)
    tot = vn + vd - 2 * cov
    return round((vd - cov) / tot, 3) if tot else None


def lag_profile(a, b, lags=range(-12, 13)):
    """Correlation of year-on-year change at each shift. A lead must clearly beat lag 0."""
    out = {}
    for L in lags:
        pairs = [(a[k], b[k + L]) for k in range(len(a))
                 if 0 <= k + L < len(b)]
        if len(pairs) > 24:
            out[L] = corr([p[0] for p in pairs], [p[1] for p in pairs])
    return {k: v for k, v in out.items() if v is not None}


def yoy(monthly):
    ks = sorted(monthly)
    return [monthly[ks[i]] / monthly[ks[i - 12]] - 1
            for i in range(12, len(ks)) if monthly[ks[i - 12]]]


def main():
    result = {"markets": {}, "checks": {}}

    # ---------------------------------------------------------------- US
    us = load("vetapi-us.json")["series"]
    api, prep, cpi = us["api_ppi"], us["prep_ppi"], us["cpi"]
    months = sorted(set(api) & set(prep))
    span = [months[0], months[-1]]
    parity = {m: prep[m] / api[m] for m in months}

    # integrity #1 — is the level meaningful, or only the change?
    result["checks"]["us_base_sensitivity"] = {
        "what": "prep/api ratio, latest month, on three different base months",
        "note": ("The ratio of two indexes is not a quantity. Rebasing both series moves "
                 "the ratio's level but not its shape — which is why only changes between "
                 "dates are quoted in the study."),
        "latest_raw_ratio": round(parity[months[-1]], 4),
        "on_2005_01_base": round(
            (rebase(prep, "2005-01")[months[-1]] / rebase(api, "2005-01")[months[-1]]), 4)
        if "2005-01" in prep and "2005-01" in api else None,
        "on_2015_01_base": round(
            (rebase(prep, "2015-01")[months[-1]] / rebase(api, "2015-01")[months[-1]]), 4)
        if "2015-01" in prep and "2015-01" in api else None,
    }

    # real (CPI-deflated) index of each side, 2015 = 100
    def real(series):
        out = {}
        for m in series:
            if m in cpi and cpi[m]:
                out[m] = series[m] / cpi[m]
        base = mean([v for k, v in out.items() if k.startswith("2015")] or [0]) or 1
        return {k: round(v / base * 100, 2) for k, v in out.items()}

    result["markets"]["US"] = {
        "span": span,
        "api_real_2015_100": real(api),
        "prep_real_2015_100": real(prep),
        "parity_2015_100": (lambda p: {k: round(v / mean(
            [x for kk, x in p.items() if kk.startswith("2015")]) * 100, 2)
            for k, v in p.items()})(parity),
        "breaks": {"api": biggest_step(api), "prep": biggest_step(prep)},
        "variance_share_from_api": variance_share_denominator(
            [prep[m] for m in months], [api[m] for m in months]),
    }
    result["checks"]["us_lag"] = {
        "what": "corr of year-on-year change, API side shifted against preparations side",
        "profile": lag_profile(yoy({m: prep[m] for m in months}),
                               yoy({m: api[m] for m in months})),
    }

    # ---------------------------------------------------------------- EU
    try:
        eu = load("vetapi-eu.json")["series"]
        e_api, e_prep = eu.get("api_ppi", {}), eu.get("prep_ppi", {})
        yrs = sorted(set(e_api) & set(e_prep))
        if yrs:
            e_par = {y: e_prep[y] / e_api[y] for y in yrs}
            result["markets"]["EU"] = {
                "span": [yrs[0], yrs[-1]],
                "api": {y: e_api[y] for y in yrs},
                "prep": {y: e_prep[y] for y in yrs},
                "parity_first_year_100": {y: round(e_par[y] / e_par[yrs[0]] * 100, 2)
                                          for y in yrs},
                "breaks": {"api": biggest_step(e_api), "prep": biggest_step(e_prep)},
                "variance_share_from_api": variance_share_denominator(
                    [e_prep[y] for y in yrs], [e_api[y] for y in yrs]),
            }
    except FileNotFoundError:
        result["markets"]["EU"] = {"error": "data/vetapi-eu.json not fetched"}

    # ---------------------------------------------------------------- TR
    try:
        tr = load("vetapi-tr.json")["series"]
        dom, dom212, imp = (tr.get("ppi_nace21", {}), tr.get("ppi_nace212", {}),
                            tr.get("import_ppi_nace21", {}))
        common = sorted(set(dom212) & set(imp))
        # Domestic 21 vs 21.2: if these are near-identical, TR has almost no 21.1 stage
        both21 = sorted(set(dom) & set(dom212))
        gap = [abs(dom[m] - dom212[m]) / dom[m] for m in both21 if dom[m]]
        result["checks"]["tr_nace21_vs_212"] = {
            "what": "TÜİK NACE 21 against NACE 21.2 — how much of division 21 is not 21.2",
            "mean_abs_gap_pct": round(mean(gap) * 100, 3) if gap else None,
            "max_abs_gap_pct": round(max(gap) * 100, 3) if gap else None,
            "reading": ("A near-zero gap means TÜİK's division-21 index is carried almost "
                        "entirely by preparations — i.e. there is no separately measured "
                        "domestic basic-pharmaceutical (21.1) stage to compare against."),
        }
        if common:
            result["markets"]["TR"] = {
                "span": [common[0], common[-1]],
                "domestic_prep": {m: dom212[m] for m in common},
                "imported_input": {m: imp[m] for m in common},
                "ratio_first_month_100": (lambda r: {m: round(r[m] / r[common[0]] * 100, 2)
                                                     for m in common})(
                    {m: dom212[m] / imp[m] for m in common}),
                "breaks": {"domestic": biggest_step(dom212), "imported": biggest_step(imp)},
                "variance_share_from_import": variance_share_denominator(
                    [dom212[m] for m in common], [imp[m] for m in common]),
            }
    except FileNotFoundError:
        result["markets"]["TR"] = {"error": "data/vetapi-tr.json not fetched"}

    print(json.dumps(result, indent=1, ensure_ascii=False, default=str))
    with open(os.path.join(ROOT, "data", "vetapi-derived.json"), "w") as f:
        json.dump(result, f, separators=(",", ":"), ensure_ascii=False)


if __name__ == "__main__":
    main()
