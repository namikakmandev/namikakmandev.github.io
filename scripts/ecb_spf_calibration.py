#!/usr/bin/env python3
"""Are the ECB forecasters' stated uncertainties honest?

The ECB's Survey of Professional Forecasters asks around fifty banks and
research houses, every quarter, for a probability DISTRIBUTION over euro-area
inflation — not a number. The ECB publishes every individual response. That
makes the useful question answerable, and it is not the one usually asked.

The usual question is whether the central forecast was right, which is easy to
mock and tells you little. The question worth asking is whether the stated
UNCERTAINTY was truthful: when a forecaster draws a range they are 80% sure
about, does the outcome land inside it 80% of the time?

It does not. It lands inside 53% of the time — and the failures are not spread
evenly. They cluster into the years that mattered, where they are total: in
2008, 2021, 2022 and 2023, not one forecaster in the panel had the outcome
inside their own range. In calm years nearly all of them do.

That is the finding. A consensus range is a fair-weather instrument: precise
when nobody needs it, and wrong in unison exactly when somebody does.

Method notes that matter:
  - Individual forecasters only. FCT_SOURCE also carries the ECB's own
    aggregate rows (AVG, VAR, NUM, PFC); averaging those in with people
    produces probabilities above 100%, which is how the mistake announces
    itself.
  - Responses whose probabilities do not sum to about 100 are dropped as
    incomplete rather than renormalised.
  - The top bucket is open-ended ("4.0% or more"), so a 2022 outcome of 8.4%
    can only be scored as "above their range", never by how far. The
    questionnaire could not express what happened, which is part of the story.

Stdlib only, deterministic.

  python3 scripts/ecb_spf_calibration.py
"""
import collections, json, re, statistics, sys

PANEL = "data/ecb-spf.json"
OUT = "data/ecb-spf-results.json"
TOL = 5.0            # how far a response's probabilities may sum from 100
BANDS = (0.80, 0.90)


def bucket_range(code):
    """'F1_5T1_9' -> (1.5, 1.9). Open ends become +/-99."""
    def num(neg, s):
        v = float(s.replace("_", "."))
        return -v if neg else v
    m = re.fullmatch(r"F(N?)(\d+_\d+)T(N?)(\d+_\d+)", code)
    if m:
        a, b = num(m.group(1), m.group(2)), num(m.group(3), m.group(4))
        return (min(a, b), max(a, b))
    m = re.fullmatch(r"F(N?)(\d+_\d+)", code)          # "from X upwards"
    if m:
        return (num(m.group(1), m.group(2)), 99.0)
    m = re.fullmatch(r"T(N?)(\d+_\d+)", code)          # "up to X"
    if m:
        return (-99.0, num(m.group(1), m.group(2)))
    return None


def quantile(bins, q):
    """Interpolated quantile of a bucketed distribution."""
    total = sum(bins.values())
    if total <= 0:
        return None
    cum = 0.0
    for lo, hi in sorted(bins):
        p = bins[(lo, hi)] / total
        if cum + p >= q:
            if hi >= 99:                                # open top
                return lo
            if lo <= -99:                               # open bottom
                return hi
            return lo + (hi - lo) * ((q - cum) / p if p > 0 else 0.0)
        cum += p
    return None


def rows_of(doc):
    """Expand the committed panel: 'target|round' -> parallel who/bucket/v."""
    for key, g in doc["grouped"].items():
        target, rnd = key.split("|", 1)
        for who, bucket, v in zip(g["who"], g["bucket"], g["v"]):
            yield {"target": int(target), "round": rnd, "who": who,
                   "bucket": bucket, "v": v}


def load():
    d = json.load(open(PANEL))
    actual = {int(k): v for k, v in d["actual_hicp"].items()}
    d["forecasts"] = list(rows_of(d))
    rows = [r for r in d["forecasts"] if str(r["who"]).isdigit()]
    dists = collections.defaultdict(dict)
    points = {}
    for r in rows:
        if r["bucket"] == "POINT":
            points[(r["target"], r["round"], r["who"])] = r["v"]
            continue
        if r["bucket"] in ("SUM", "NUM"):
            continue
        rng = bucket_range(r["bucket"])
        if rng:
            dists[(r["target"], r["round"], r["who"])][rng] = r["v"]
    return d, actual, dists, points


def coverage(dists, actual, round_filter, band=0.80):
    """-> per-year and pooled coverage of each forecaster's own band."""
    tail = (1 - band) / 2
    per_year = collections.defaultdict(lambda: {"in": 0, "lo": 0, "hi": 0})
    for (t, rd, who), bins in dists.items():
        if t not in actual or not rd or not round_filter(t, rd):
            continue
        if abs(sum(bins.values()) - 100.0) > TOL:
            continue
        lo, hi = quantile(bins, tail), quantile(bins, 1 - tail)
        if lo is None or hi is None:
            continue
        a = actual[t]
        slot = "in" if lo <= a <= hi else ("lo" if a < lo else "hi")
        per_year[t][slot] += 1
    tot = {"in": 0, "lo": 0, "hi": 0}
    for v in per_year.values():
        for k in tot:
            tot[k] += v[k]
    n = sum(tot.values())
    return per_year, tot, n


def hr(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main():
    doc, actual, dists, points = load()
    one_year = lambda t, rd: rd.startswith(f"{t - 1}-Q4")

    hr("0. The data")
    print(f"  source        {doc['source']}")
    print(f"  fetched       {doc['fetched_at']}")
    print(f"  forecasters   {len({w for _, _, w in dists})} individual "
          f"(ECB aggregate rows AVG/VAR/NUM/PFC excluded)")
    print(f"  distributions {len(dists):,} across "
          f"{len({t for t, _, _ in dists})} target years")
    print(f"  buckets       top is open-ended; the form's widest option was "
          f"'4.0% or more'")

    hr("1. Do their stated ranges hold? (one year ahead)")
    for band in BANDS:
        per_year, tot, n = coverage(dists, actual, one_year, band)
        print(f"  a {band * 100:.0f}% range should contain the outcome "
              f"{band * 100:.0f}% of the time")
        print(f"    it contains it            {tot['in']:>5} of {n:,}  "
              f"({tot['in'] / n * 100:.1f}%)")
        print(f"    outcome came in ABOVE     {tot['hi']:>5}  "
              f"({tot['hi'] / n * 100:.1f}%)")
        print(f"    outcome came in BELOW     {tot['lo']:>5}  "
              f"({tot['lo'] / n * 100:.1f}%)\n")

    hr("2. The failures are not spread out — they are total, in the years that mattered")
    per_year, _, _ = coverage(dists, actual, one_year, 0.80)
    print(f"    {'year':<6}{'inflation':>11}{'forecasters':>13}"
          f"{'outcome inside their own 80% range':>36}")
    zero_years = []
    for t in sorted(per_year):
        v = per_year[t]
        n = v["in"] + v["lo"] + v["hi"]
        if not n:
            continue
        share = v["in"] / n
        if v["in"] == 0:
            zero_years.append(t)
        bar = "#" * round(share * 28)
        print(f"    {t:<6}{actual[t]:>10.2f}%{n:>13}"
              f"{v['in']:>10}/{n:<4}{share * 100:>5.0f}%  {bar}")
    print(f"\n  Years where NOT ONE forecaster contained the outcome: "
          f"{zero_years}")
    print("  Those are the financial crisis and the inflation shock — the only")
    print("  years anyone actually needed the forecast.")

    hr("3. 2021: the year nobody in Europe saw it coming")
    F = [r for r in doc["forecasts"] if str(r["who"]).isdigit()]
    print(f"  Target 2022. Actual inflation: {actual[2022]:.2f}%.")
    print(f"  The survey's top box was 'inflation of 4.0% or more'.\n")
    print(f"    {'survey round':<14}{'panel':>7}{'mean P(>=4%)':>14}"
          f"{'said exactly 0%':>17}{'most worried':>14}")
    for rd in sorted({r["round"] for r in F if r["target"] == 2022}):
        vals = [r["v"] for r in F
                if r["target"] == 2022 and r["bucket"] == "F4_0"
                and r["round"] == rd]
        if not vals:
            continue
        print(f"    {rd:<14}{len(vals):>7}{statistics.mean(vals):>13.2f}%"
              f"{sum(1 for v in vals if v == 0):>12}/{len(vals):<4}"
              f"{max(vals):>13.0f}%")
    print("\n  In the last survey before the year began, two-thirds of the panel")
    print("  put the probability at exactly zero. The most alarmed forecaster in")
    print("  Europe said 6%. It came in at more than double the threshold they")
    print("  were dismissing.")

    hr("4. Were the few who worried simply always worried?")
    rd = "2021-Q4"
    top = sorted([(r["who"], r["v"]) for r in F
                  if r["target"] == 2022 and r["bucket"] == "F4_0"
                  and r["round"] == rd], key=lambda x: -x[1])
    print(f"    {'forecaster':<12}{'P(>=4%) for 2022':>18}"
          f"{'their own average, 2000-2021':>30}")
    for who, v in top[:6]:
        prior = [r["v"] for r in F if r["who"] == who and r["bucket"] == "F4_0"
                 and r["target"] < 2022]
        avg = statistics.mean(prior) if prior else float("nan")
        print(f"    #{who:<11}{v:>17.0f}%{avg:>29.2f}%")
    allp = [r["v"] for r in F if r["bucket"] == "F4_0" and r["target"] < 2022]
    print(f"\n  Panel-wide average P(>=4%) before 2022: "
          f"{statistics.mean(allp):.2f}%")
    print("  So the ones who worried were not permanent pessimists being ignored.")
    print("  There were no pessimists. The maximum concern anyone expressed was 6%.")

    hr("5. Robustness")
    print("  5a. the same test at other forecast horizons")
    for label, filt in (
            ("1 year ahead  (prior Q4)", lambda t, rd: rd.startswith(f"{t-1}-Q4")),
            ("~1.75 years   (prior Q1)", lambda t, rd: rd.startswith(f"{t-1}-Q1")),
            ("same year     (own Q1)", lambda t, rd: rd.startswith(f"{t}-Q1"))):
        _, tot, n = coverage(dists, actual, filt, 0.80)
        if n:
            print(f"      {label:<26} {tot['in'] / n * 100:>5.1f}% inside  "
                  f"(n={n:,})")

    print("\n  5b. dropping the crisis years entirely")
    calm = {t for t in actual if t not in (2008, 2009, 2021, 2022, 2023)}
    _, tot, n = coverage({k: v for k, v in dists.items() if k[0] in calm},
                         actual, one_year, 0.80)
    print(f"      excluding 2008-09 and 2021-23   {tot['in'] / n * 100:.1f}% "
          f"inside (n={n:,})")
    print("      Even with every turbulent year removed, the ranges are still")
    print("      too narrow — the problem is not only the crises.")

    print("\n  5c. was the panel ever well calibrated?")
    for lo, hi in ((2000, 2007), (2008, 2014), (2015, 2025)):
        era = {t for t in actual if lo <= t <= hi}
        _, tot, n = coverage({k: v for k, v in dists.items() if k[0] in era},
                             actual, one_year, 0.80)
        if n:
            print(f"      {lo}-{hi}   {tot['in'] / n * 100:>5.1f}% inside "
                  f"(n={n:,})")

    # ------------------------------------------------------------------ export
    per_year80, tot80, n80 = coverage(dists, actual, one_year, 0.80)
    out = {
        "generated_by": "scripts/ecb_spf_calibration.py",
        "source_url": doc["source_url"], "fetched_at": doc["fetched_at"],
        "n_distributions": n80,
        "n_forecasters": len({w for _, _, w in dists}),
        "coverage80": {"inside": tot80["in"], "above": tot80["hi"],
                       "below": tot80["lo"],
                       "share_inside": round(tot80["in"] / n80, 4)},
        "by_year": [{"year": t, "actual": round(actual[t], 3),
                     "n": per_year80[t]["in"] + per_year80[t]["lo"]
                          + per_year80[t]["hi"],
                     "inside": per_year80[t]["in"],
                     "share": round(per_year80[t]["in"] /
                                    max(1, per_year80[t]["in"]
                                        + per_year80[t]["lo"]
                                        + per_year80[t]["hi"]), 4)}
                    for t in sorted(per_year80)],
        "zero_years": zero_years,
        "target2022": [
            {"round": rd,
             "n": len([r for r in F if r["target"] == 2022
                       and r["bucket"] == "F4_0" and r["round"] == rd]),
             "mean_p_ge4": round(statistics.mean(
                 [r["v"] for r in F if r["target"] == 2022
                  and r["bucket"] == "F4_0" and r["round"] == rd]), 3),
             "said_zero": sum(1 for r in F if r["target"] == 2022
                              and r["bucket"] == "F4_0" and r["round"] == rd
                              and r["v"] == 0),
             "max": max([r["v"] for r in F if r["target"] == 2022
                         and r["bucket"] == "F4_0" and r["round"] == rd])}
            for rd in sorted({r["round"] for r in F if r["target"] == 2022})
            if [r for r in F if r["target"] == 2022
                and r["bucket"] == "F4_0" and r["round"] == rd]],
        "actual_2022": round(actual[2022], 3),
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {OUT}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
