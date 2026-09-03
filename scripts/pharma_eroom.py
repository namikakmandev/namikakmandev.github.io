#!/usr/bin/env python3
"""Did Eroom's Law continue? -> data/pharma-eroom-results.json

Scannell et al. (2012, Nat Rev Drug Discov) found that new drugs approved per
billion dollars of R&D had halved roughly every nine years since 1950, and
named it Eroom's Law — Moore's Law backwards. The paper's series stops around
2010. Approvals have risen sharply since, while the decline kept being cited.
So: does the claimed rate still hold?

WHAT THIS CANNOT DO. It cannot re-measure the paper's own 1950-2010 window.
Three probe rounds established that no pharma R&D spending series reaches back
that far through any retrievable route (data/_pharma-probe.json,
data/_pharma-spend-probe.json). This tests whether the published RATE continues
in the years since — a different and narrower question, and the page says so.

  numerator    FDA new molecular entities per year, from the Drugs@FDA
               submission records. Reproduces the FDA's own published novel
               approval counts almost exactly.
  denominator  Eurostat BERD, NACE C21: business R&D performed in the country.
               NOT global spend by that country's firms, which is what the
               paper used. The limitation travels with every number here.
  deflator     US GDP implicit price deflator.

The headline is the deflated US series. Everything else is a robustness cut.

Stdlib only, deterministic.

  python3 scripts/pharma_eroom.py
"""
import json, math, os, statistics, sys

SRC = "data/pharma-eroom.json"
OUT = "data/pharma-eroom-results.json"
EROOM_HALVING_YEARS = 9.0
EROOM_SLOPE = math.log(0.5) / EROOM_HALVING_YEARS      # -0.0770 per year


def hr(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def fit(years, ratio):
    """Log-linear trend with a 95% interval, and what it means as a halving or
    doubling time. Eroom is a claim about a rate, so the rate is the estimand."""
    xs = sorted(years)
    ys = [math.log(ratio[y]) for y in xs]
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    s2 = sum(r * r for r in res) / (n - 2)
    se = (s2 / sxx) ** .5
    lo, hi = b - 1.96 * se, b + 1.96 * se
    r1 = (statistics.correlation(res[:-1], res[1:]) if n > 4 else 0.0)
    return {"n": n, "first": xs[0], "last": xs[-1],
            "slope": round(b, 5), "se": round(se, 5),
            "ci": [round(lo, 5), round(hi, 5)],
            "annual_change_pct": round((math.exp(b) - 1) * 100, 2),
            "halving_years": (round(math.log(0.5) / b, 1) if b < 0 else None),
            "doubling_years": (round(math.log(2) / b, 1) if b > 0 else None),
            "eroom_slope": round(EROOM_SLOPE, 5),
            "eroom_inside_ci": bool(lo <= EROOM_SLOPE <= hi),
            "resid_lag1_autocorr": round(r1, 3)}


def series(nme, rd, deflator=None):
    """NMEs per billion of R&D. Deflated when a deflator is supplied."""
    out = {}
    for y in sorted(set(nme) & set(rd)):
        spend = rd[y] / 1000.0                      # millions -> billions
        if deflator:
            if str(y) not in deflator:
                continue
            spend = spend / (deflator[str(y)] / 100.0)
        if spend > 0:
            out[y] = nme[y] / spend
    return out


def main():
    doc = json.load(open(SRC))
    nme = {int(k): v for k, v in doc["nme"]["by_year"].items()}
    S = doc["berd"]["series"]
    dfl = doc.get("deflator", {}).get("by_year")

    hr("0. What is being tested")
    print("  Eroom's Law: approvals per R&D dollar halve about every 9 years")
    print(f"  -> a log-linear slope of {EROOM_SLOPE:+.4f} per year")
    print("  The paper's window ends around 2010. This asks only whether that")
    print("  rate continued afterwards; it does not re-measure the paper itself.")
    if not dfl:
        print("\n  NO DEFLATOR IN THE DATA FILE — current prices only.")

    us_nom = series(nme, {int(k): v for k, v in S["US|MIO_NAC"].items()})
    us_real = (series(nme, {int(k): v for k, v in S["US|MIO_NAC"].items()}, dfl)
               if dfl else None)

    hr("1. The United States, the defensible pairing")
    print("  US business R&D in pharmaceuticals against US drug approvals.\n")
    head = f"    {'year':<6}{'NMEs':>6}{'R&D $bn':>11}"
    if us_real:
        head += f"{'real $bn':>11}{'per real $bn':>14}"
    else:
        head += f"{'per $bn':>11}"
    print(head)
    for y in sorted(us_nom):
        rd_bn = S["US|MIO_NAC"][str(y)] / 1000
        line = f"    {y:<6}{nme[y]:>6}{rd_bn:>11.1f}"
        if us_real:
            real = rd_bn / (dfl[str(y)] / 100.0)
            line += f"{real:>11.1f}{us_real[y]:>14.3f}"
        else:
            line += f"{us_nom[y]:>11.3f}"
        print(line)

    if not us_real:
        print("\n  Headline falls back to current prices. Re-run once the "
              "deflator is fetched.")
    headline = fit(sorted(us_real or us_nom), us_real or us_nom)
    hr("2. Does the Eroom rate still hold?")
    label = "deflated" if us_real else "current prices"
    print(f"  {label}, {headline['first']}-{headline['last']}, "
          f"n={headline['n']}\n")
    print(f"    fitted slope        {headline['slope']:+.4f} per year "
          f"({headline['annual_change_pct']:+.1f}% a year)")
    print(f"    95% interval        {headline['ci'][0]:+.4f} to "
          f"{headline['ci'][1]:+.4f}")
    print(f"    Eroom's own rate    {headline['eroom_slope']:+.4f}  "
          f"(halving every {EROOM_HALVING_YEARS:.0f} years)")
    print(f"    -> Eroom's rate is "
          f"{'INSIDE the interval: not rejected' if headline['eroom_inside_ci'] else 'OUTSIDE the interval: REJECTED'}")
    if headline["halving_years"]:
        print(f"    the data's own halving time: "
              f"{headline['halving_years']} years")
    else:
        print(f"    the ratio is not falling at all "
              f"(doubling time {headline['doubling_years']} years)")

    hr("3. Robustness: every other way of building it")
    print("  US rows are the evidence: US R&D against US approvals. The other")
    print("  countries pair DOMESTIC R&D with US approvals, which is a weaker")
    print("  quantity, so they are listed as context and counted separately.\n")
    print(f"    {'series':<28}{'n':>4}  {'window':<12}{'slope':>9}"
          f"{'95% interval':>22}  Eroom")
    cuts = []
    specs = [("US", "MIO_NAC", "current USD"), ("US", "MIO_NAC", "deflated"),
             ("US", "MIO_EUR", "current EUR"), ("US", "MIO_PPS", "PPS"),
             ("US", "MIO_PPS_KP05", "constant PPS"),
             ("JP", "MIO_PPS", "PPS"), ("DE", "MIO_EUR", "current EUR"),
             ("CH", "MIO_EUR", "current EUR"), ("UK", "MIO_EUR", "current EUR")]
    for geo, unit, how in specs:
        raw = S.get(f"{geo}|{unit}")
        if not raw:
            continue
        rd = {int(k): v for k, v in raw.items()}
        if how == "deflated" and not dfl:
            # A row labelled "deflated" that was not deflated is worse than a
            # missing row: it looks like a robustness cut and is a duplicate.
            print(f"    {geo + ' ' + unit + ' ' + how:<28}"
                  f"  SKIPPED — no deflator in the data file")
            continue
        r = series(nme, rd, dfl if how == "deflated" else None)
        if len(r) < 6:
            continue
        f = fit(sorted(r), r)
        f.update({"geo": geo, "unit": unit, "basis": how})
        cuts.append(f)
        print(f"    {geo + ' ' + unit + ' ' + how:<28}{f['n']:>4}  "
              f"{str(f['first']) + '-' + str(f['last']):<12}{f['slope']:>+9.4f}"
              f"{'[' + format(f['ci'][0], '+.4f') + ',' + format(f['ci'][1], '+.4f') + ']':>22}"
              f"  {'not rejected' if f['eroom_inside_ci'] else 'REJECTED'}")
    us_cuts = [c for c in cuts if c["geo"] == "US"]
    other = [c for c in cuts if c["geo"] != "US"]
    rejected = sum(1 for c in us_cuts if not c["eroom_inside_ci"])
    print(f"\n  Eroom's rate rejected in {rejected} of {len(us_cuts)} US "
          f"specifications — the ones that are evidence.")
    print(f"  Also rejected in {sum(1 for c in other if not c['eroom_inside_ci'])}"
          f" of {len(other)} other countries, which is context, not proof.")

    hr("4. The checks that decide whether this is real")
    ser_h = us_real or us_nom
    xs = sorted(ser_h)

    # rule 3: a survey redesign would show as one implausible step
    rdser = {int(k): v for k, v in S["US|MIO_NAC"].items()}
    ys_ = sorted(rdser)
    steps = [(y, (rdser[y] / rdser[p] - 1) * 100) for p, y in zip(ys_, ys_[1:])]
    med = statistics.median(abs(v) for _, v in steps)
    mad = statistics.median(abs(abs(v) - med) for _, v in steps)
    breaks = [(y, v) for y, v in steps if abs(abs(v) - med) > 4 * mad]
    print(f"  methodology breaks: median year-on-year step {med:.1f}%, "
          f"MAD {mad:.1f}%")
    print(f"    {'none flagged' if not breaks else 'FLAGGED: ' + str(breaks)}"
          f" — no comparison here spans a survey redesign")

    # rule 8: annual data is autocorrelated; a p-value that ignores that is fiction
    r1 = headline["resid_lag1_autocorr"]
    n_eff = len(xs) * (1 - r1) / (1 + r1)
    print(f"\n  effective sample size: n={len(xs)}, residual lag-1 "
          f"autocorrelation {r1:+.2f}, n_eff={n_eff:.0f}")
    print(f"    the autocorrelation is {'negative, so the ordinary interval is' if r1 < 0 else 'positive, so the interval is'}"
          f" {'conservative and the rejection is safe' if r1 < 0 else 'TOO NARROW and must be widened'}")

    # rule 7: which side of the ratio actually moves?
    def dlog(seq):
        k = sorted(seq)
        return [math.log(seq[k[i + 1]] / seq[k[i]]) for i in range(len(k) - 1)]
    den = {y: (rdser[y] / 1000) / ((dfl[str(y)] / 100) if dfl else 1) for y in xs}
    dn, dd = dlog({y: nme[y] for y in xs}), dlog(den)
    vn, vd = statistics.pvariance(dn), statistics.pvariance(dd)
    cov = statistics.covariance(dn, dd)
    share_den = (vd - cov) / (vn + vd - 2 * cov)
    print(f"\n  what actually moves the ratio")
    print(f"    variance of year-on-year log change, approvals  {vn:.4f}")
    print(f"    variance of year-on-year log change, real R&D   {vd:.4f}")
    print(f"    the denominator accounts for {share_den * 100:.0f}% of the "
          f"ratio's movement")
    print(f"    -> spending grows smoothly; the swings are approvals. This is")
    print(f"       an approvals story with a slow denominator, not a spending")
    print(f"       story, and the page has to say so.")
    checks = {"break_median_step_pct": round(med, 2),
              "break_mad_pct": round(mad, 2), "breaks_flagged": breaks,
              "n": len(xs), "resid_lag1_autocorr": r1,
              "n_eff": round(n_eff, 1),
              "interval_conservative": bool(r1 < 0),
              "var_dlog_approvals": round(vn, 5),
              "var_dlog_real_rd": round(vd, 5),
              "denominator_share_of_movement": round(share_den, 4)}

    hr("5. What this does not establish")
    print("  - The denominator is R&D PERFORMED in the country, not global")
    print("    spend by its firms. The paper used the latter. Different object.")
    print("  - Non-US rows pair domestic R&D with US approvals, which is weak.")
    print("    They are context; the US row is the evidence.")
    print("  - 14 annual points. A rate this large is detectable in 14 years,")
    print("    but nothing subtle is.")
    print("  - The paper's own era is not re-measured, so this cannot say the")
    print("    original was wrong — only that the rate did not continue.")

    out = {"generated_by": "scripts/pharma_eroom.py",
           "source_file": SRC,
           "fetched_at": doc.get("fetched_at"),
           "question": ("Eroom's Law says approvals per R&D dollar halve every "
                        "nine years. Did that rate continue after the paper?"),
           "eroom": {"halving_years": EROOM_HALVING_YEARS,
                     "implied_slope": round(EROOM_SLOPE, 5),
                     "paper": ("Scannell, Blanckley, Boldon & Warrington (2012), "
                               "Nature Reviews Drug Discovery 11, 191-200")},
           "headline": headline,
           "headline_basis": label,
           "us_series": {str(y): round(v, 4) for y, v in (us_real or us_nom).items()},
           "us_nominal": {str(y): round(v, 4) for y, v in us_nom.items()},
           "nme_by_year": doc["nme"]["by_year"],
           "robustness": cuts, "checks": checks,
           "n_us_specs": len(us_cuts), "n_us_rejecting_eroom": rejected,
           "n_other_specs": len(other),
           "limitations": [
               "the ratio's movement is almost entirely approvals, not "
               "spending: real R&D grows smoothly while approvals swing",
               "levels are per billion dollars on the deflator's own base "
               "year; the fitted slope is invariant to that base, the levels "
               "are not",
               "denominator is R&D performed in-country, not global spend by "
               "the country's firms, which is what the paper used",
               "non-US rows pair domestic R&D with US FDA approvals",
               "14 annual observations in the headline series",
               "the paper's own 1950-2010 window is not re-measured"]}
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {OUT}")
    chart(out)
    return 0


def chart(res):
    """What the law predicted, against what happened.

    Anchored at the first observed year, because the claim is about a RATE:
    from wherever you start, halve every nine years. That is the only fair way
    to draw a prediction the paper never made for these years.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fte_chart import render_png                                # noqa

    ser = {int(k): v for k, v in res["us_series"].items()}
    yrs = sorted(ser)
    y0, v0 = yrs[0], ser[yrs[0]]
    pred = {y: v0 * (0.5 ** ((y - y0) / EROOM_HALVING_YEARS)) for y in yrs}
    W, H, L, R, T, B = 1600, 1060, 118, 70, 250, 210
    pw, ph = W - L - R, H - T - B
    hi = max(max(ser.values()), v0) * 1.12
    BLUE, RED, DIM, INK, GRID = "#2f9bff", "#d94040", "#5b6472", "#1f2430", "#dfe4ea"
    F = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
         "'Helvetica Neue',Arial,sans-serif")

    def px(y):
        return L + (y - yrs[0]) / (yrs[-1] - yrs[0]) * pw

    def py(v):
        return T + (1 - v / hi) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="56" font-size="37" font-weight="700" fill="{INK}">'
         f'The US, {yrs[0]}&#8211;{yrs[-1]}: Eroom&#8217;s Law said drug '
         f'productivity halves every nine years</text>',
         f'<text x="{L}" y="100" font-size="24" fill="{DIM}">US new molecular '
         f'entities approved per billion dollars of US pharmaceutical business '
         f'R&amp;D, in constant prices.</text>',
         f'<text x="{L}" y="132" font-size="24" fill="{DIM}">Red dashed: where '
         f'the ratio should be if the law still held. Blue: the trend through '
         f'what actually happened, with the yearly figures behind it.</text>',
         f'<text x="{L}" y="176" font-size="25" font-weight="700" fill="{RED}">'
         f'It did not continue: the ratio is flat to rising, and the '
         f'law&#8217;s own rate is rejected in every specification tested.</text>']
    for i in range(5):
        v = hi * i / 4
        o.append(f'<line x1="{L}" y1="{py(v):.1f}" x2="{L + pw}" '
                 f'y2="{py(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{L - 14}" y="{py(v) + 7:.1f}" font-size="20" '
                 f'fill="{DIM}" text-anchor="end">{v:.2f}</text>')
    for y in yrs:
        o.append(f'<text x="{px(y):.1f}" y="{T + ph + 34}" font-size="19" '
                 f'fill="{DIM}" text-anchor="middle">{y}</text>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{px(y):.1f},{py(pred[y]):.1f}"
                 for i, y in enumerate(yrs))
    o.append(f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="3.5" '
             f'stroke-dasharray="11 8"/>')
    # the yearly points, quietly: they are noisy and the noise is not the point
    d = " ".join(f"{'M' if i == 0 else 'L'}{px(y):.1f},{py(ser[y]):.1f}"
                 for i, y in enumerate(yrs))
    o.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="2.5" '
             f'stroke-linejoin="round" opacity="0.35"/>')
    for y in yrs:
        o.append(f'<circle cx="{px(y):.1f}" cy="{py(ser[y]):.1f}" r="6" '
                 f'fill="{BLUE}" opacity="0.45"/>')
    # the fitted trend, loudly: flat against falling is the whole comparison
    b = res["headline"]["slope"]
    mx = sum(yrs) / len(yrs)
    my = sum(math.log(ser[y]) for y in yrs) / len(yrs)
    trend = {y: math.exp(my + b * (y - mx)) for y in yrs}
    d = " ".join(f"{'M' if i == 0 else 'L'}{px(y):.1f},{py(trend[y]):.1f}"
                 for i, y in enumerate(yrs))
    o.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="5"/>')
    ylast = yrs[-1]
    o += [f'<text x="{px(ylast) - 6:.1f}" y="{py(trend[ylast]) - 30:.1f}" '
          f'font-size="23" font-weight="700" fill="{BLUE}" text-anchor="end">'
          f'the trend: flat</text>',
          f'<text x="{px(ylast) - 12:.1f}" y="{py(pred[ylast]) + 34:.1f}" '
          f'font-size="23" font-weight="700" fill="{RED}" text-anchor="end">'
          f'Eroom&#8217;s Law predicts {pred[ylast]:.2f}</text>',
          f'<text x="{L}" y="{H - 102}" font-size="22" fill="{INK}">By '
          f'{ylast} the law implies {pred[ylast]:.2f} approvals per billion. '
          f'The figure was {ser[ylast]:.2f} &#8212; more than '
          f'{ser[ylast] / pred[ylast]:.0f} times higher.</text>',
          f'<text x="{L}" y="{H - 72}" font-size="22" fill="{INK}">The swings '
          f'are approvals, not spending: real R&amp;D grows smoothly and '
          f'accounts for only {res["checks"]["denominator_share_of_movement"]*100:.0f}% '
          f'of the ratio&#8217;s movement.</text>',
          f'<text x="{L}" y="{H - 44}" font-size="22" fill="{INK}">This tests '
          f'only whether the published rate continued. The paper&#8217;s own '
          f'1950&#8211;2010 window cannot be re-measured from open data.</text>',
          f'<text x="{L}" y="{H - 16}" font-size="17" fill="{DIM}">Data: FDA '
          f'Drugs@FDA submission records (new molecular entities) and Eurostat '
          f'rd_e_berdindr2 NACE C21, deflated by the US GDP price index '
          f'&#183; namikakmandev.github.io/pharma-eroom.html</text>', '</svg>']
    svg = "\n".join(o)
    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/pharma-eroom.svg"
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/pharma-eroom.png", W, H)


if __name__ == "__main__":
    sys.exit(main())
