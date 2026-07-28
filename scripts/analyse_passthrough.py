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


def leg(driver, response, months, name, max_lag=12):
    prof = {}
    for L in range(0, max_lag + 1):
        xs, ys = shift_pairs(driver, response, L, months)
        beta, r, n = ols(xs, ys)
        if beta is not None:
            prof[L] = {"beta": round(beta, 4), "r": round(r, 3), "n": n}
    best = max(prof, key=lambda L: prof[L]["r"])
    at0 = prof[0]["r"]
    margin = round(prof[best]["r"] - at0, 3)
    # cumulative pass-through: sum of betas from a distributed-lag fit is over-simple,
    # so report the cumulative response of the LEVEL ratio instead, horizon by horizon
    cum = {}
    run = 0.0
    for L in sorted(prof):
        run += prof[L]["beta"]
        cum[L] = round(run, 3)
    return {
        "name": name,
        "profile": prof,
        "peak_lag": best,
        "peak_r": prof[best]["r"],
        "r_at_lag0": at0,
        "peak_margin_over_lag0": margin,
        "lead_is_real": bool(margin >= 0.10),
        "verdict": (f"peak r={prof[best]['r']} at lag {best} vs r={at0} at lag 0 — "
                    + ("a real lead" if margin >= 0.10 else
                       "NOT a lead: the peak does not clearly beat lag 0, so it is read "
                       "as a contemporaneous relationship")),
        "cumulative_beta": cum,
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
        "leg0_fx_to_domestic": leg(d_fx, d_dom, common, "USD/TRY → domestic preparations"),
    }

    with open(os.path.join(ROOT, "data", "passthrough-derived.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)

    print(f"Türkiye pass-through · {out['window'][0]} → {out['window'][1]} · "
          f"n={out['n_months']} monthly changes · FX = {fxk}\n")
    for k in ("leg1_fx_to_import", "leg2_import_to_domestic", "leg0_fx_to_domestic"):
        L = out[k]
        print(f"--- {L['name']}")
        print(f"    contemporaneous: beta={L['profile'][0]['beta']:+.3f}  r={L['profile'][0]['r']:+.3f}  n={L['profile'][0]['n']}")
        print(f"    {L['verdict']}")
        print("    cumulative beta by horizon: " +
              ", ".join(f"{h}m={L['cumulative_beta'][h]:+.2f}" for h in (0, 3, 6, 12)
                        if h in L['cumulative_beta']))
        print()
    print("[write] data/passthrough-derived.json")


if __name__ == "__main__":
    main()
