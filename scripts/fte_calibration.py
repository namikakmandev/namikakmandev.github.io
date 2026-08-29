#!/usr/bin/env python3
"""Full data-integrity pass on FiveThirtyEight's calibration claim.

The claim, in 538's own words on "How Good Are FiveThirtyEight Forecasts?":
when they said something had a 70% chance, it happened about 70% of the time.

Their archive makes that testable, and also makes it very easy to answer
flatteringly. Three ways a naive pass cheats, all removed here:

  1. Repeat forecasts. Most models re-ran daily, so one House race contributes
     ~100 rows. Pooling them turns a few hundred elections into n=855,178.
     Fixed: one snapshot per forecasting unit.
  2. In-play forecasts. A team 30 points up with two minutes left is a 99.9%
     call anyone gets right. 430k of the 3.1M rows are these. Excluded.
  3. Model variants. The same race is forecast by Lite, Classic and Deluxe.
     Counting all three triples the sample without adding information.
     Fixed: one flagship model per project-year.

And the inference is clustered, because neither rows nor even contests are
independent: a national polling error moves every race on one election night
together. Intervals are cluster-robust; where the cluster count is small enough
to bootstrap, both are reported and compared.

Stdlib only, seeded, deterministic.

  python3 scripts/fte_calibration.py
"""
import json, math, random, sys
from collections import defaultdict

SEED = 42
ITERS = 2000
BOOT_MAX_CLUSTERS = 6000     # above this the bootstrap is too slow to be worth it
BUCKETS = 20
PANEL = "data/fte-forecasts.json"
SLICES = "data/fte-slices.json"

# 538 ran several model variants side by side. Their flagship, in preference
# order; '-' is the only option for projects that never had variants.
MODEL_RANK = {"classic": 0, "polls-plus": 1, "-": 2,
              "polls-only": 3, "deluxe": 4, "lite": 5}


# ---------------------------------------------------------------- statistics

def calib_line(rows):
    """OLS of outcome on forecast probability.

    Perfect calibration is intercept 0, slope 1: a forecast of p is followed by
    the event exactly p of the time. Slope below 1 means overconfidence — the
    extremes were pushed further out than the record justified.
    """
    n = len(rows)
    if n < 3:
        return None
    mx = sum(p for p, _ in rows) / n
    my = sum(o for _, o in rows) / n
    sxx = sum((p - mx) ** 2 for p, _ in rows)
    if sxx == 0:
        return None
    sxy = sum((p - mx) * (o - my) for p, o in rows)
    b = sxy / sxx
    return b, my - b * mx, n


def clustered_ci(clusters):
    """Cluster-robust (sandwich) 95% interval for the calibration slope.

    Rows inside a cluster may be arbitrarily correlated — the two candidates in
    one race always are, since one wins if the other loses. Treating them as
    independent is what makes n=855,178 look like evidence.
    """
    rows = [r for c in clusters for r in c]
    fit = calib_line(rows)
    if fit is None:
        return None
    b, a, n = fit
    g = len(clusters)
    if g < 2:
        return None
    mx = sum(p for p, _ in rows) / n
    sxx = sum((p - mx) ** 2 for p, _ in rows)
    meat = 0.0
    for c in clusters:
        s = sum((p - mx) * (o - a - b * p) for p, o in c)
        meat += s * s
    corr = (g / (g - 1)) * ((n - 1) / max(n - 2, 1))
    var = corr * meat / (sxx * sxx)
    se = math.sqrt(var)
    return b, a, n, g, b - 1.959964 * se, b + 1.959964 * se


def brier(rows):
    """Mean squared error of the probabilities, and its Murphy decomposition.

    BS = reliability - resolution + uncertainty.
      reliability  how far each bin's outcome rate sits from the bin's forecast
                   (0 = perfectly calibrated; lower is better)
      resolution   how far the bins' outcome rates sit from the base rate
                   (higher is better; this is the part that makes a forecast
                   useful rather than merely honest)
      uncertainty  the base rate's own variance — the score earned by always
                   predicting the base rate and nothing else
    """
    n = len(rows)
    bs = sum((p - o) ** 2 for p, o in rows) / n
    base = sum(o for _, o in rows) / n
    bins = defaultdict(list)
    for p, o in rows:
        bins[min(BUCKETS - 1, int(p * BUCKETS))].append((p, o))
    rel = res = 0.0
    for members in bins.values():
        k = len(members)
        pbar = sum(p for p, _ in members) / k
        obar = sum(o for _, o in members) / k
        rel += k * (pbar - obar) ** 2
        res += k * (obar - base) ** 2
    unc = base * (1 - base)
    return {"brier": bs, "base": base, "reliability": rel / n,
            "resolution": res / n, "uncertainty": unc,
            "skill": 1 - bs / unc if unc > 0 else float("nan"), "n": n}


def curve(rows, bins=10):
    """Observed frequency against forecast probability, bin by bin."""
    acc = defaultdict(lambda: [0, 0.0, 0.0])
    for p, o in rows:
        a = acc[min(bins - 1, int(p * bins))]
        a[0] += 1
        a[1] += p
        a[2] += o
    return [(i, acc[i][0], acc[i][1] / acc[i][0], acc[i][2] / acc[i][0])
            for i in sorted(acc) if acc[i][0]]


def cluster_boot(clusters, iters=ITERS, seed=SEED):
    """Percentile CI on the slope, resampling whole clusters with replacement.

    Runs on per-cluster sufficient statistics, so one iteration is a sum over
    clusters rather than over rows. Only used where the cluster count is small.
    """
    if not (4 <= len(clusters) <= BOOT_MAX_CLUSTERS):
        return None, None
    stats = []
    for c in clusters:
        n = len(c)
        sp = sum(p for p, _ in c)
        stats.append((n, sp, sum(p * p for p, _ in c),
                      sum(o for _, o in c), sum(p * o for p, o in c)))
    rng = random.Random(seed)
    k = len(stats)
    out = []
    for _ in range(iters):
        N = SP = SP2 = SO = SPO = 0.0
        for s in rng.choices(stats, k=k):
            N += s[0]; SP += s[1]; SP2 += s[2]; SO += s[3]; SPO += s[4]
        sxx = SP2 - SP * SP / N
        if sxx > 0:
            out.append((SPO - SP * SO / N) / sxx)
    if len(out) < iters // 4:
        return None, None
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


# ---------------------------------------------------------------- data

def load_panel(path=PANEL):
    d = json.load(open(path))
    out = []
    for g in d["groups"]:
        for contest, cdate in zip(g["clusters"], g["dates"]):
            rows = []
            for cell in contest.split(";"):
                p, o, lead = cell[1:].split(",")
                rows.append({"snap": cell[0], "p": int(p) / 1000.0,
                             "o": int(o), "lead": int(lead)})
            out.append({"topic": g["topic"], "project": g["project"],
                        "model": g["model"], "year": g["year"],
                        "date": cdate, "rows": rows})
    return d, out


def flagship(contests):
    """Keep one model variant per project-year: 538's flagship for that cycle."""
    best = {}
    for c in contests:
        k = (c["project"], c["year"])
        r = MODEL_RANK.get(c["model"], 9)
        if k not in best or r < best[k]:
            best[k] = r
    return [c for c in contests
            if MODEL_RANK.get(c["model"], 9) == best[(c["project"], c["year"])]]


def select(contests, snap="f", topic=None, drop_projects=(), years=None):
    """-> (flat rows, clusters by contest, clusters by event date)."""
    by_contest, by_night = [], defaultdict(list)
    for c in contests:
        if topic and c["topic"] != topic:
            continue
        if c["project"] in drop_projects:
            continue
        if years and c["year"] not in years:
            continue
        rows = [(r["p"], r["o"]) for r in c["rows"] if r["snap"] == snap]
        if not rows:
            continue
        by_contest.append(rows)
        by_night[(c["project"], c["year"], c["date"])] += rows
    flat = [r for c in by_contest for r in c]
    return flat, by_contest, list(by_night.values())


def competitive(clusters, lo=0.10, hi=0.90):
    """Keep only forecasts that were genuinely uncertain.

    A forecast of 0.3% that a Democrat wins in a deep-red district is correct
    and worthless. 82% of 538's political forecasts are that kind. Conditioning
    on the forecast — never on the outcome — leaves the calls people argue about.
    """
    out = []
    for c in clusters:
        keep = [(p, o) for p, o in c if lo <= p < hi]
        if keep:
            out.append(keep)
    return out


# ---------------------------------------------------------------- report

def hr(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def report(label, flat, contests, nights=None, indent="  "):
    res = clustered_ci(contests)
    b, a, n, g, lo, hi = res
    print(f"{indent}{label:<34} slope={b:.3f} CI[{lo:.3f},{hi:.3f}]  "
          f"a={a:+.3f}  n={n:>7,}  contests={g:>6,}")
    print(f"{indent}{'':34} Brier={brier(flat)['brier']:.4f}  "
          f"skill={brier(flat)['skill']:+.3f}  "
          f"rel={brier(flat)['reliability']:.5f}  "
          f"res={brier(flat)['resolution']:.4f}  base={brier(flat)['base']:.3f}")
    blo, bhi = cluster_boot(contests)
    if blo is not None:
        print(f"{indent}{'':34} bootstrap over the same clusters: "
              f"CI[{blo:.3f},{bhi:.3f}]")
    if nights:
        r2 = clustered_ci(nights)
        if r2:
            print(f"{indent}{'':34} clustered by event date instead: "
                  f"CI[{r2[4]:.3f},{r2[5]:.3f}]  clusters={r2[3]:,}")
    return res


def main():
    meta, contests = load_panel()
    slices = json.load(open(SLICES))["slices"]

    hr("0. What the archive contains, and what survives the filters")
    print(f"  source        {meta['source']}")
    print(f"  archive       {meta['source_url']}")
    print(f"  fetched       {meta['fetched_at']}")
    print(f"  raw rows                        "
          f"{slices['all_dates_incl_live']['n']:>9,}")
    print(f"    in-play 'live' forecasts      {slices['live_only']['n']:>9,}"
          f"   excluded")
    print(f"    remaining, every date pooled  "
          f"{slices['all_dates_no_live']['n']:>9,}   reduced to one snapshot/unit")
    print(f"  forecasting units               {meta['n_units']:>9,}")
    print(f"  contests                        {meta['n_contests']:>9,}")

    main_set = flagship(contests)
    flat, byc, byn = select(main_set)
    pol_flat, pol_c, pol_n = select(main_set, topic="politics")
    spo_flat, spo_c, spo_n = select(main_set, topic="sports")
    print(f"  after one-flagship-model filter  {len(flat):>9,}   "
          f"({len(pol_flat):,} politics, {len(spo_flat):,} sports)")

    hr("1. Headline — was a 70% forecast followed by the event 70% of the time?")
    report("all forecasts, final, no live", flat, byc, byn)
    print()
    report("politics only", pol_flat, pol_c, pol_n)
    print()
    report("sports only", spo_flat, spo_c, spo_n)

    for label, rows in (("all forecasts", flat), ("politics only", pol_flat)):
        print(f"\n  calibration curve, {label} (final, no live):")
        print(f"    {'forecast band':<15}{'n':>9}{'mean forecast':>15}"
              f"{'happened':>11}{'gap':>9}")
        for i, n, mp, mo in curve(rows):
            print(f"    {i * 10:>3}-{i * 10 + 10:<11}{n:>9,}{mp * 100:>14.1f}%"
                  f"{mo * 100:>10.1f}%{(mo - mp) * 100:>+8.1f}")

    hr("2. The misreading — 'it said 71% and it was WRONG'")
    band = [(p, o) for p, o in pol_flat if 0.65 <= p < 0.75]
    exp = sum(p for p, _ in band) / len(band)
    got = sum(o for _, o in band) / len(band)
    print(f"  political forecasts in the 65-75% band: n={len(band):,}")
    print(f"    mean forecast {exp * 100:.1f}%  ->  the favourite won "
          f"{got * 100:.1f}% of the time")
    print(f"    so the favourite LOST {(1 - got) * 100:.1f}% of them, against "
          f"{(1 - exp) * 100:.1f}% expected.")
    print(f"    Losing roughly a quarter of your 70% calls is not the model "
          f"failing. It is")
    print(f"    the model being right about what 70% means.")
    conf = [(p, o) for p, o in pol_flat if p >= 0.95]
    misses = sum(1 for _, o in conf if o == 0)
    print(f"\n  political forecasts at 95%+: n={len(conf):,}   happened "
          f"{sum(o for _, o in conf) / len(conf) * 100:.2f}%  "
          f"(mean forecast {sum(p for p, _ in conf) / len(conf) * 100:.2f}%)")
    print(f"    {misses} of them did not happen. Those are the ones anyone "
          f"remembers.")

    hr("3. Calibrated is not the same as useful")
    print("  A forecaster who says the base rate every time is perfectly")
    print("  calibrated and carries no information whatsoever. The skill score")
    print("  is what separates 538 from that forecaster.\n")
    for label, rows in (("all", flat), ("politics", pol_flat),
                        ("sports", spo_flat)):
        b = brier(rows)
        print(f"  {label:<10} Brier={b['brier']:.4f}  vs always-say-base-rate "
              f"{b['uncertainty']:.4f}   skill {b['skill'] * 100:+.1f}%")
        print(f"  {'':10} resolution (the useful part) {b['resolution']:.4f}, "
              f"reliability (the error) {b['reliability']:.5f}")

    hr("4. Where the political record is thinner than it looks")
    print("  Most political forecasts are not forecasts of anything uncertain.")
    print("  Conditioning on the forecast (never on the outcome) isolates the")
    print("  races that were actually in doubt.\n")
    for label, cl in (("politics", pol_c), ("sports", spo_c)):
        allr = [r for c in cl for r in c]
        comp = competitive(cl)
        compr = [r for c in comp for r in c]
        share = (1 - len(compr) / len(allr)) * 100
        print(f"  {label}: {share:.1f}% of forecasts sit outside the 10-90% band")
        report("all of them", allr, cl, indent="    ")
        report("only the 10-90% ones", compr, comp, indent="    ")
        print()
    comp = competitive(pol_c)
    r = clustered_ci(comp)
    print(f"  On competitive races the slope is {r[0]:.2f}, CI[{r[4]:.2f},{r[5]:.2f}] "
          f"— above 1, not below.")
    print("  538's political forecasts were UNDERconfident: their favourites won")
    print("  more often than the model said. The popular complaint is the reverse.\n")
    print("  does that survive being cut up?")
    byp = defaultdict(list)
    for c in main_set:
        if c["topic"] == "politics":
            byp[c["project"]].append(c)
    for proj in sorted(byp):
        _, cl, _ = select(byp[proj])
        cc = competitive(cl)
        rr = clustered_ci(cc)
        if rr and rr[3] >= 8:
            print(f"      {proj:<26} slope={rr[0]:.3f} "
                  f"CI[{rr[4]:.3f},{rr[5]:.3f}]  races={rr[3]:>4}")
    gen = [c for c in main_set if c["topic"] == "politics"
           and c["project"] != "state-president-primary"]
    print("\n      by cycle, general elections only (no primaries):")
    byy = defaultdict(list)
    for c in gen:
        byy[c["year"]].append(c)
    for y in sorted(byy):
        _, cl, _ = select(byy[y])
        cc = competitive(cl)
        rr = clustered_ci(cc)
        if rr and rr[3] >= 8:
            flag = "   <- the year everyone remembers" if y == 2016 else ""
            print(f"      {y}                       slope={rr[0]:.3f} "
                  f"CI[{rr[4]:.3f},{rr[5]:.3f}]  races={rr[3]:>4}{flag}")

    hr("5. Robustness")
    print("  5a. the same slope, three definitions of the sample it rests on")
    fit = calib_line(pol_flat)
    b, a, n = fit
    mx = sum(p for p, _ in pol_flat) / n
    sxx = sum((p - mx) ** 2 for p, _ in pol_flat)
    s2 = sum((o - a - b * p) ** 2 for p, o in pol_flat) / (n - 2)
    se = math.sqrt(s2 / sxx)
    print(f"      politics, rows assumed independent    slope={b:.3f} "
          f"CI[{b - 1.96 * se:.3f},{b + 1.96 * se:.3f}]  n={n:,}")
    r = clustered_ci(pol_c)
    print(f"      politics, clustered by race           slope={r[0]:.3f} "
          f"CI[{r[4]:.3f},{r[5]:.3f}]  clusters={r[3]:,}")
    r = clustered_ci(pol_n)
    print(f"      politics, clustered by election date  slope={r[0]:.3f} "
          f"CI[{r[4]:.3f},{r[5]:.3f}]  clusters={r[3]:,}")
    print("      The estimate never moves, and — against expectation — clustering")
    print("      does not widen the interval here. It slightly narrows it, because")
    print("      the two candidates in a race are mechanically anti-correlated:")
    print("      one wins exactly when the other loses, so their residuals cancel")
    print("      inside the cluster. Worth stating plainly: the reason n=855,178")
    print("      is not evidence is that it is 48 election dates, not that the")
    print("      standard error explodes when you say so.")

    print("\n  5b. the slices the headline throws away")
    for name, label in (("all_dates_no_live", "every forecast date, no live"),
                        ("all_dates_incl_live", "every forecast date, incl. live"),
                        ("live_only", "in-play 'live' forecasts only")):
        s = slices[name]
        nn, sp, so = s["n"], s["sum_p"], s["sum_o"]
        sxx = s["sum_p2"] - sp * sp / nn
        bb = (s["sum_po"] - sp * so / nn) / sxx
        bs = (s["sum_p2"] - 2 * s["sum_po"] + so) / nn
        base = so / nn
        print(f"      {label:<32} slope={bb:.3f}  Brier={bs:.4f}  "
              f"skill={1 - bs / (base * (1 - base)):+.3f}  n={nn:,}")
    print("      Every excluded slice makes the numbers look better. That is "
          "why they are excluded.")

    print("\n  5c. the forecast made ~30 days out, not on the eve")
    matched = [c for c in main_set if any(r["snap"] == "l" for r in c["rows"])]
    leads = sorted(r["lead"] for c in matched for r in c["rows"]
                   if r["snap"] == "l" and r["lead"] >= 0)
    print(f"      contests carrying both snapshots: {len(matched):,}"
          + (f"   (median lead {leads[len(leads) // 2]} days)" if leads else ""))
    f_flat, f_c, _ = select(matched, snap="f")
    l_flat, l_c, _ = select(matched, snap="l")
    report("final forecast", f_flat, f_c, indent="      ")
    report("~30 days out", l_flat, l_c, indent="      ")

    print("\n  5d. era split")
    for label, yrs in (("2008-2016", set(range(2008, 2017))),
                       ("2017-2022", set(range(2017, 2023)))):
        fl, cl, _ = select(main_set, years=yrs)
        report(label, fl, cl, indent="      ")

    print("\n  5e. drop the project that dominates the sample")
    big = defaultdict(int)
    for c in main_set:
        big[c["project"]] += sum(1 for r in c["rows"] if r["snap"] == "f")
    top = max(big, key=big.get)
    print(f"      largest project: {top} "
          f"({big[top]:,} of {len(flat):,} forecasts)")
    fl, cl, _ = select(main_set, drop_projects=(top,))
    report(f"without {top}", fl, cl, indent="      ")

    print("\n  5f. every model variant kept, not just the flagship")
    fl, cl, _ = select(contests)
    report("all model variants", fl, cl, indent="      ")

    # ------------------------------------------------------------------ export
    # Every number the receipts page and the chart quote comes from here, so the
    # page cannot drift away from the script.
    def pack(flat, clusters):
        r = clustered_ci(clusters)
        b = brier(flat)
        return {"slope": round(r[0], 4), "intercept": round(r[1], 4),
                "ci": [round(r[4], 4), round(r[5], 4)],
                "n": r[2], "clusters": r[3],
                "brier": round(b["brier"], 5), "skill": round(b["skill"], 4),
                "reliability": round(b["reliability"], 6),
                "resolution": round(b["resolution"], 5),
                "base": round(b["base"], 4)}

    pol_comp = competitive(pol_c)
    out = {
        "generated_by": "scripts/fte_calibration.py",
        "source_url": meta["source_url"],
        "fetched_at": meta["fetched_at"],
        "seed": SEED, "bootstrap_iters": ITERS,
        "raw_rows": slices["all_dates_incl_live"]["n"],
        "live_rows": slices["live_only"]["n"],
        "units": meta["n_units"], "contests": meta["n_contests"],
        "headline": {"all": pack(flat, byc), "politics": pack(pol_flat, pol_c),
                     "sports": pack(spo_flat, spo_c),
                     "politics_competitive": pack(
                         [r for c in pol_comp for r in c], pol_comp),
                     "sports_competitive": pack(
                         [r for c in competitive(spo_c) for r in c],
                         competitive(spo_c))},
        "curve_all": [{"band": i * 10, "n": n, "forecast": round(mp, 4),
                       "happened": round(mo, 4)} for i, n, mp, mo in curve(flat)],
        "curve_politics": [{"band": i * 10, "n": n, "forecast": round(mp, 4),
                            "happened": round(mo, 4)}
                           for i, n, mp, mo in curve(pol_flat)],
        "curve_politics_competitive": [
            {"band": i * 10, "n": n, "forecast": round(mp, 4),
             "happened": round(mo, 4)}
            for i, n, mp, mo in curve([r for c in pol_comp for r in c])],
        "curve_sports": [{"band": i * 10, "n": n, "forecast": round(mp, 4),
                          "happened": round(mo, 4)}
                         for i, n, mp, mo in curve(spo_flat)],
    }
    with open("data/fte-results.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print("\n  wrote data/fte-results.json")
    print()


if __name__ == "__main__":
    sys.exit(main())
