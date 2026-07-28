#!/usr/bin/env python3
"""Türkiye: when the lira moves, how much of it reaches the price — and how fast?

The parity study showed the Turkish parity halved because the imported input outran
domestic prices. It could not say *why* or *how fast*. This measures the two legs:

    leg 1   USD/TRY            ->  imported pharma input price   (TP.UFEYD16)
    leg 2   imported input     ->  domestic preparations price   (TP.TUFE1YI.T60)

Both legs are estimated on month-on-month log changes, so the trend common to every
nominal Turkish series cannot manufacture the result. Reported per lag, with the
cumulative pass-through over horizons.

Integrity rules that shape this file:
  #2  everything is a log CHANGE, never a level — three nominal TRY series all trend
  #6  a peak away from lag 0 is only a lead if it CLEARLY beats lag 0; the margin is
      printed so the reader can judge rather than take the argmax on trust
  #8  n is printed at every lag

Run:  python scripts/analyse_passthrough.py
"""
import json, math, os
from statistics import mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)


def dlog(series, months):
    """month-on-month log change, aligned to `months` (skips non-consecutive gaps)."""
    out = {}
    for i in range(1, len(months)):
        a, b = months[i - 1], months[i]
        if a in series and b in series and series[a] > 0:
            out[b] = math.log(series[b]) - math.log(series[a])
    return out


def corr(xs, ys):
    if len(xs) < 8:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / den if den else None


def ols(xs, ys):
    """slope of y on x — the pass-through coefficient, plus r."""
    if len(xs) < 8:
        return None, None, 0
    mx, my = mean(xs), mean(ys)
    sxx = sum((a - mx) ** 2 for a in xs)
    if not sxx:
        return None, None, len(xs)
    beta = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sxx
    return beta, corr(xs, ys), len(xs)


def shift_pairs(driver, response, lag, months):
    """response at t+lag against driver at t."""
    pairs = []
    for i, m in enumerate(months):
        j = i + lag
        if 0 <= j < len(months) and m in driver and months[j] in response:
            pairs.append((driver[m], response[months[j]]))
    return [p[0] for p in pairs], [p[1] for p in pairs]


def local_projection(driver, response, months, horizons=(0, 1, 3, 6, 9, 12)):
    """Cumulative pass-through, done properly.

    Summing the slopes of separate one-lag-at-a-time regressions DOUBLE COUNTS, because
    monthly FX changes are autocorrelated — that route produced a cumulative 204%
    pass-through, which is not a real number. Instead, for each horizon h regress the
    response's cumulative log change from t-1 to t+h on the driver's change at t. Each
    horizon is one clean regression, and the coefficient IS the cumulative response.
    """
    lvl_r = {}          # cumulative log level of the response, for summing over horizons
    run = 0.0
    for m in months:
        run += response.get(m, 0.0)
        lvl_r[m] = run
    out = {}
    for h in horizons:
        xs, ys = [], []
        for i, m in enumerate(months):
            j = i + h
            if j < len(months) and m in driver:
                # response change accumulated from month m through month m+h
                ys.append(lvl_r[months[j]] - lvl_r[m] + response.get(m, 0.0))
                xs.append(driver[m])
        beta, r, n = ols(xs, ys)
        if beta is not None:
            out[h] = {"beta": round(beta, 3), "r": round(r, 3), "n": n}
    return out


def _runner_up(prof, best):
    """The next-strongest lag. An argmax over a jagged profile is not a finding."""
    rest = [L for L in prof if L != best]
    if not rest:
        return None
    r2 = max(rest, key=lambda L: abs(prof[L]["r"]))
    return {"lag": r2, "r": prof[r2]["r"],
            "gap_from_peak": round(abs(prof[best]["r"]) - abs(prof[r2]["r"]), 3)}


def _clear_of_runner_up(prof, best, need=0.05):
    """A peak only counts if it beats the SECOND-best lag too, not just lag 0."""
    ru = _runner_up(prof, best)
    return ru is not None and ru["gap_from_peak"] >= need


def leg(driver, response, months, name, max_lag=12):
    prof = {}
    for L in range(0, max_lag + 1):
        xs, ys = shift_pairs(driver, response, L, months)
        beta, r, n = ols(xs, ys)
        if beta is not None:
            prof[L] = {"beta": round(beta, 4), "r": round(r, 3), "n": n}
    # rank by STRENGTH, not by signed r: the margin-ratio leg is a negative relationship,
    # and taking the most positive r there reported a meaningless "lead" at lag 2 while
    # ignoring a far stronger r = -0.53 at lag 0.
    best = max(prof, key=lambda L: abs(prof[L]["r"]))
    at0 = prof[0]["r"]
    margin = round(abs(prof[best]["r"]) - abs(at0), 3)
    cum = local_projection(driver, response, months)
    return {
        "name": name,
        "profile": prof,
        "peak_lag": best,
        "peak_r": prof[best]["r"],
        "r_at_lag0": at0,
        "peak_margin_over_lag0": margin,
        "lead_is_real": bool(margin >= 0.10 and _clear_of_runner_up(prof, best)),
        "runner_up": _runner_up(prof, best),
        "verdict": (f"peak r={prof[best]['r']} at lag {best} vs r={at0} at lag 0 — "
                    + ("a real lead" if (margin >= 0.10 and _clear_of_runner_up(prof, best))
                       else "NOT a usable lead: " + (
                           "the peak does not clearly beat lag 0"
                           if margin < 0.10 else
                           "the profile is jagged — the next-best lag is effectively tied, "
                           "so no single transmission lag can be pinned"))),
        "cumulative": cum,
        "cumulative_method": ("Local projection: for each horizon h, the response's "
                              "cumulative log change from t to t+h regressed on the "
                              "driver's change at t. One regression per horizon — the "
                              "coefficient is the cumulative pass-through, not a sum."),
    }


def main():
    tr = load("vetapi-tr.json")["series"]
    fx = load("vetapi-fx.json")["series"]
    fxk = next(iter(fx))                      # whichever FX series resolved
    fxs = fx[fxk]
    imp, dom = tr["import_ppi_nace21"], tr["ppi_nace212"]

    months = sorted(set(imp) & set(dom) & set(fxs))
    d_fx, d_imp, d_dom = (dlog(fxs, months), dlog(imp, months), dlog(dom, months))
    common = sorted(set(d_fx) & set(d_imp) & set(d_dom))
    d_fx = {m: d_fx[m] for m in common}
    d_imp = {m: d_imp[m] for m in common}
    d_dom = {m: d_dom[m] for m in common}
    # the margin ratio: domestic ÷ imported. Both sides are nominal TRY, so Turkish
    # inflation is in both and cancels — this is the one long-horizon measure that is
    # not contaminated by the regime, and it is the commercially relevant one.
    d_par = {m: d_dom[m] - d_imp[m] for m in common}

    out = {
        "window": [common[0], common[-1]], "n_months": len(common),
        "fx_series": fxk,
        "method": ("Month-on-month log changes throughout. Levels are never used: USD/TRY, "
                   "the imported input index and the domestic preparations index all trend "
                   "steeply in nominal terms, and correlating trends manufactures a result. "
                   "beta is the pass-through coefficient — the share of a 1% move that "
                   "appears in the response that month."),
        "leg1_fx_to_import": leg(d_fx, d_imp, common, "USD/TRY → imported pharma input"),
        "leg2_import_to_domestic": leg(d_imp, d_dom, common,
                                       "imported input → domestic preparations"),
        "margin_response": leg(d_fx, d_par, common,
                               "USD/TRY → the margin ratio (domestic ÷ imported)"),
        "why_margin_ratio": (
            "The nominal legs cannot be read beyond about six months. Turkish inflation "
            "runs through the import index and the domestic index alike, so a 12-month "
            "cumulative regression picks up the inflation regime and returns a "
            "pass-through above 100% — which is not a real quantity. The margin ratio "
            "(domestic ÷ imported) carries that inflation on BOTH sides, so it cancels. "
            "It is also the number that matters commercially: what a lira move does to "
            "the spread between what the maker pays and what it can charge."),
        "nominal_long_horizon_warning": (
            "Cumulative estimates past 6 months on the nominal legs exceed 1.0 and are "
            "reported here only so the contamination is visible. They are not quoted as "
            "pass-through anywhere in the study."),
    }

    with open(os.path.join(ROOT, "data", "passthrough-derived.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)

    print(f"Türkiye pass-through · {out['window'][0]} → {out['window'][1]} · "
          f"n={out['n_months']} monthly changes · FX = {fxk}\n")
    for k in ("leg1_fx_to_import", "leg2_import_to_domestic", "margin_response"):
        L = out[k]
        print(f"--- {L['name']}")
        print(f"    contemporaneous: beta={L['profile'][0]['beta']:+.3f}  r={L['profile'][0]['r']:+.3f}  n={L['profile'][0]['n']}")
        print(f"    {L['verdict']}")
        print("    cumulative pass-through (local projection): " +
              ", ".join(f"{h}m={L['cumulative'][h]['beta']:+.2f}"
                        for h in sorted(L['cumulative'])))
        print()
    print("[write] data/passthrough-derived.json")


if __name__ == "__main__":
    main()
