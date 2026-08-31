#!/usr/bin/env python3
"""Is any individual ECB forecaster consistently honest about uncertainty?

The companion study (ecb_spf_calibration.py) scored the panel as a whole: when
these forecasters mark out a range they are 80% sure about, the outcome lands
inside it 53% of the time. This asks a different question of the same data.

The ECB anonymises panellists by number and publishes no mapping, so nobody
outside the ECB knows which institution is which — and this makes no attempt to
find out. But the numbers are stable identities: #016 in 2000 is the same desk
as #016 in 2022. So an individual record can be followed for a quarter of a
century without ever knowing whose it is.

The confounder that had to be removed first: forecasters cover different years,
and years differ enormously in difficulty — the panel managed 100% coverage in
2007 and 0% in 2008. Anyone active only in the calm years would look brilliant
for free. So each forecaster is scored against what an average forecaster
facing THEIR EXACT YEARS would have achieved. Controlling for it makes the
result stronger, not weaker; it had been masking the signal.

Two tests, both against explicit null distributions rather than a table:
  - is the spread across forecasters wider than luck would produce, if every
    forecaster were equally good?
  - does the first half of a forecaster's career predict the second half?

Stdlib only, seeded, deterministic.

  python3 scripts/ecb_forecaster_skill.py
"""
import collections, json, os, random, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecb_spf_calibration import load, quantile, TOL          # noqa: E402
from fte_chart import render_png                              # noqa: E402

SEED = 42
ITERS = 20_000
MIN_YEARS = 10          # a record shorter than this says nothing either way
BAND = 0.80
OUT = "data/ecb-forecaster-skill.json"


def clipped(bins, q):
    """True if quantile q falls in an open-ended bucket, where the boundary is
    substituted for the true percentile — which narrows the measured range."""
    total = sum(bins.values())
    cum = 0.0
    for lo, hi in sorted(bins):
        pr = bins[(lo, hi)] / total
        if cum + pr >= q:
            return hi >= 99 or lo <= -99
        cum += pr
    return False


def records(dists, actual):
    """-> {forecaster: [(year, hit, width, lo, hi, clipped)]} one year ahead."""
    one = lambda t, rd: rd.startswith(f"{t - 1}-Q4")
    rec = collections.defaultdict(list)
    tail = (1 - BAND) / 2
    for (t, rd, who), bins in dists.items():
        if t not in actual or not rd or not one(t, rd):
            continue
        if abs(sum(bins.values()) - 100.0) > TOL:
            continue
        lo, hi = quantile(bins, tail), quantile(bins, 1 - tail)
        if lo is None or hi is None:
            continue
        rec[who].append((t, 1 if lo <= actual[t] <= hi else 0, hi - lo,
                         round(lo, 2), round(hi, 2),
                         clipped(bins, tail) or clipped(bins, 1 - tail)))
    return {w: v for w, v in rec.items() if len(v) >= MIN_YEARS}


def year_difficulty(elig):
    """Panel coverage per year — how hard that year was for everyone."""
    by = collections.defaultdict(list)
    for v in elig.values():
        for t, h, *_ in v:
            by[t].append(h)
    return {t: sum(h) / len(h) for t, h in by.items()}


def skill(elig, p_y):
    """Hits above what the same years would give an average forecaster."""
    return {w: (sum(h for _, h, *_ in v) - sum(p_y[t] for t, *_ in v)) / len(v)
            for w, v in elig.items()}


def hr(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main():
    doc, actual, dists, _ = load()
    elig = records(dists, actual)
    p_y = year_difficulty(elig)
    score = skill(elig, p_y)
    rng = random.Random(SEED)

    hr("0. The panel, followed individually")
    print(f"  forecasters with {MIN_YEARS}+ scored years   {len(elig)}")
    print(f"  forecasts scored                    "
          f"{sum(len(v) for v in elig.values()):,}")
    print(f"  pooled coverage                     "
          f"{sum(h for v in elig.values() for _, h, *_ in v) / sum(len(v) for v in elig.values()) * 100:.1f}%")
    print("  Forecasters are anonymous. The ECB publishes them only by number,")
    print("  and nothing here attempts to identify them.")

    hr("1. Year difficulty — the confounder that had to go first")
    for t in sorted(p_y):
        bar = "#" * round(p_y[t] * 30)
        print(f"    {t}  {p_y[t] * 100:>5.0f}%  {bar}")
    print("\n  A forecaster active only in 2003-2007 would look brilliant for")
    print("  free. Every score below is measured against what an average")
    print("  forecaster facing that forecaster's own years would have managed.")

    hr("1b. When the panel fails, which way does it fail?")
    # A miss is not a direction-free event. Either the outcome beat the top of
    # the range (they were short) or it fell under the bottom (they were high).
    side = {}
    for t in sorted(p_y):
        ins = low = high = 0
        for v in elig.values():
            for yr, h, d, lo, hi, _c in v:
                if yr != t:
                    continue
                if h:                  ins += 1
                elif actual[t] > hi:   low += 1
                else:                  high += 1
        side[t] = (ins, low, high)
    print(f"    {'year':<7}{'n':>4}{'inside':>8}{'too low':>9}{'too high':>10}"
          f"   actual")
    for t in sorted(side):
        ins, low, high = side[t]
        flag = "   <- nobody inside" if ins == 0 else ""
        print(f"    {t:<7}{ins + low + high:>4}{ins:>8}{low:>9}{high:>10}"
              f"   {actual[t]:>5.2f}%{flag}")
    dead = [t for t in side if side[t][0] == 0]
    dn = sum(side[t][1] + side[t][2] for t in dead)
    dlow = sum(side[t][1] for t in dead)
    ins = sum(v[0] for v in side.values())
    low = sum(v[1] for v in side.values())
    high = sum(v[2] for v in side.values())
    print(f"\n  pooled: {ins} inside, {low} too low, {high} too high")
    print(f"  of the {low + high} misses, {low / (low + high) * 100:.0f}% were "
          f"too low — the panel is wrong in both directions, but more often")
    print(f"  wrong by underestimating.")
    print(f"\n  in the {len(dead)} years nobody was inside "
          f"({', '.join(str(t) for t in sorted(dead))}):")
    print(f"    {dlow} of {dn} forecasts too low, {dn - dlow} too high")
    print(f"  -> {'every single one was short' if dlow == dn else 'mixed'}. "
          f"When this panel fails completely, it fails one way.")

    hr("2. Is the spread wider than luck?")
    obs = statistics.pstdev(list(score.values()))
    sims = []
    for _ in range(ITERS):
        s = []
        for v in elig.values():
            exp = sum(p_y[t] for t, *_ in v)
            got = sum(1 for t, *_ in v if rng.random() < p_y[t])
            s.append((got - exp) / len(v))
        sims.append(statistics.pstdev(s))
    sims.sort()
    p_spread = sum(1 for x in sims if x >= obs) / len(sims)
    print(f"  observed spread across forecasters   {obs * 100:.1f}pp")
    print(f"  if every forecaster were equal       median "
          f"{statistics.median(sims) * 100:.1f}pp, 95th "
          f"{sims[int(0.95 * len(sims))] * 100:.1f}pp")
    print(f"  p = {p_spread:.4f}  -> "
          f"{'real differences between forecasters' if p_spread < 0.05 else 'indistinguishable from luck'}")

    srt = sorted(score.items(), key=lambda x: -x[1])
    print(f"\n  best  " + ", ".join(f"#{w} {v * 100:+.0f}pp" for w, v in srt[:5]))
    print(f"  worst " + ", ".join(f"#{w} {v * 100:+.0f}pp" for w, v in srt[-5:]))
    print(f"  gap between best and worst: "
          f"{(srt[0][1] - srt[-1][1]) * 100:.0f} percentage points")

    hr("3. Does a good record keep being good?")
    pairs = []
    for w, v in elig.items():
        v = sorted(v)
        if len(v) < 12:
            continue
        h = len(v) // 2

        def sc(part):
            return (sum(x for _, x, *_ in part)
                    - sum(p_y[t] for t, *_ in part)) / len(part)
        pairs.append((sc(v[:h]), sc(v[h:])))
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** .5
    r = num / den if den else float("nan")
    hit = 0
    for _ in range(ITERS):
        sh = ys[:]
        rng.shuffle(sh)
        m2 = statistics.mean(sh)
        nn = sum((a - mx) * (b - m2) for a, b in zip(xs, sh))
        dd = (sum((a - mx) ** 2 for a in xs)
              * sum((b - m2) ** 2 for b in sh)) ** .5
        if dd and abs(nn / dd) >= abs(r):
            hit += 1
    p_split = hit / ITERS
    print(f"  first half of a career vs second half, n={len(pairs)} forecasters")
    print(f"  r = {r:+.3f}   permutation p = {p_split:.4f}")
    print(f"  -> {'honesty about uncertainty is a durable trait' if p_split < 0.05 else 'no persistence'}")

    hr("4. Is the best forecaster better, or just vaguer?")
    width = {w: statistics.median(d for _, _, d, *_ in v) for w, v in elig.items()}
    xs = [width[w] for w in elig]
    ys = [score[w] for w in elig]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs)
           * sum((b - my) ** 2 for b in ys)) ** .5
    r_w = num / den if den else float("nan")
    print("  A forecaster who always quotes a wide range will be inside it more")
    print("  often without knowing anything more. So how much of the score is")
    print("  simply width?\n")
    print(f"  correlation between median range width and skill: r = {r_w:+.3f}")
    print(f"  width explains {r_w * r_w * 100:.0f}% of the skill score")
    print(f"  median range width across the panel: "
          f"{statistics.median(xs):.2f} percentage points\n")
    srt_w = sorted(elig, key=lambda w: -score[w])
    print(f"    {'forecaster':<12}{'skill':>9}{'median range width':>22}")
    for w in srt_w[:3] + srt_w[-3:]:
        print(f"    #{w:<11}{score[w] * 100:>+8.0f}pp{width[w]:>20.2f}pp")
    narrow = [w for w in elig if width[w] < statistics.median(xs)]
    wide = [w for w in elig if width[w] >= statistics.median(xs)]
    print()
    for name, grp in (("narrower-than-median", narrow), ("wider-than-median", wide)):
        sk = [score[w] for w in grp]
        print(f"    among {name} forecasters (n={len(grp)}): spread still "
              f"{statistics.pstdev(sk) * 100:.1f}pp, "
              f"best {max(sk) * 100:+.0f}pp worst {min(sk) * 100:+.0f}pp")
    # Does the persistence survive width? Split each career in half, take each
    # half's score AND its median width, strip the width effect with one pooled
    # regression line, and re-run the split-half correlation on the residuals.
    halves = []
    for w, v in elig.items():
        v = sorted(v)
        if len(v) < 12:
            continue
        h = len(v) // 2

        def hs(part):
            return ((sum(x for _, x, *_ in part)
                     - sum(p_y[t] for t, *_ in part)) / len(part),
                    statistics.median(d for _, _, d, *_ in part))
        halves.append((hs(v[:h]), hs(v[h:])))
    ws = [d for pair in halves for _, d in pair]
    ss = [q for pair in halves for q, _ in pair]
    mw, ms = statistics.mean(ws), statistics.mean(ss)
    sw = sum((a - mw) ** 2 for a in ws)
    b = sum((a - mw) * (q - ms) for a, q in zip(ws, ss)) / sw if sw else 0.0
    res = [(q1 - (ms + b * (d1 - mw)), q2 - (ms + b * (d2 - mw)))
           for (q1, d1), (q2, d2) in halves]
    r_res, p_res = corr_perm(res, rng, ITERS)
    print(f"\n  persistence on raw scores:            r = {r:+.3f}")
    print(f"  persistence after removing width:     r = {r_res:+.3f}   "
          f"permutation p = {p_res:.4f}")
    print(f"  -> {'a durable habit of quoting wider ranges explains part of it,' if p_res < 0.05 else 'nothing survives:'}")
    print(f"     {'but something that is not width still persists' if p_res < 0.05 else 'the persistence was width all along'}")

    # The open-ended buckets substitute a boundary for a percentile, which
    # narrows the measured range. Re-run the width correlation on the years
    # where no boundary was substituted, and see whether it moves.
    clean = {w: [x for x in v if not x[5]] for w, v in elig.items()}
    clean = {w: v for w, v in clean.items() if len(v) >= MIN_YEARS}
    n_clip = sum(1 for v in elig.values() for x in v if x[5])
    n_all = sum(len(v) for v in elig.values())
    cw = {w: statistics.median(d for _, _, d, *_ in v) for w, v in clean.items()}
    cxs = [cw[w] for w in clean]
    cys = [score[w] for w in clean]
    mcx, mcy = statistics.mean(cxs), statistics.mean(cys)
    cnum = sum((a - mcx) * (b - mcy) for a, b in zip(cxs, cys))
    cden = (sum((a - mcx) ** 2 for a in cxs)
            * sum((b - mcy) ** 2 for b in cys)) ** .5
    r_clean = cnum / cden if cden else float("nan")
    print(f"\n  robustness: {n_clip} of {n_all} forecasts ({n_clip / n_all * 100:.1f}%) "
          f"had a percentile fall in an open-ended bucket,")
    print(f"  where the boundary is substituted and the measured range narrows.")
    print(f"  dropping them ({len(clean)} forecasters still have {MIN_YEARS}+ years): "
          f"r = {r_clean:+.3f} against {r_w:+.3f}")

    print("\n  So roughly half the score is style, not skill. Something remains")
    print("  after width is held roughly constant — but the headline number")
    print("  overstates how much of it is knowing anything.")

    hr("5. But almost nobody clears the bar")
    cov = {w: sum(h for _, h, *_ in v) / len(v) for w, v in elig.items()}
    good = sorted((c for c in cov.values() if c >= BAND), reverse=True)
    print(f"  forecasters whose 80% ranges actually held 80% of the time: "
          f"{len(good)} of {len(cov)}")

    # Whoever clears the bar deserves the same scrutiny as everyone else:
    # a short record, a wide range, or an absence from the hard years all
    # make the achievement cheaper than it looks.
    dead_set = set(dead)
    cleared = []
    for w in sorted(cov, key=lambda k: -cov[k]):
        if cov[w] < BAND:
            continue
        yrs = sorted(t for t, *_ in elig[w])
        faced = sorted(dead_set & set(yrs))
        narrower = sum(1 for o in width if width[o] < width[w])
        cleared.append({"who": w, "coverage": round(cov[w], 4),
                        "years": len(yrs), "first": yrs[0], "last": yrs[-1],
                        "width": round(width[w], 3),
                        "width_rank_narrowest": narrower + 1,
                        "zero_years_faced": faced,
                        "zero_years_missed": sorted(dead_set - set(yrs))})
        print(f"\n  #{w}: inside {round(cov[w] * len(yrs))} of {len(yrs)} years "
              f"({cov[w] * 100:.0f}%), {yrs[0]}-{yrs[-1]}")
        print(f"    median range width {width[w]:.2f}pp against a panel median "
              f"of {statistics.median(xs):.2f}pp")
        print(f"    -> the {narrower + 1}th narrowest of {len(width)}; "
              f"{'one of the widest on the panel' if narrower + 1 > len(width) * .75 else 'mid-pack on width'}")
        print(f"    of the {len(dead_set)} years nobody was inside, it faced "
              f"{faced or 'none'} and was off the panel for "
              f"{sorted(dead_set - set(yrs)) or 'none'}")
    print("\n  Skill in being honest about uncertainty is real, persistent, and")
    print("  almost universally insufficient.")

    # ------------------------------------------------------------------ export
    pool = []
    for _ in range(4000):
        for v in elig.values():
            exp = sum(p_y[t] for t, *_ in v)
            got = sum(1 for t, *_ in v if rng.random() < p_y[t])
            pool.append((got - exp) / len(v))
    pool.sort()
    luck = [pool[int(0.025 * len(pool))], pool[int(0.975 * len(pool))]]

    out = {
        "generated_by": "scripts/ecb_forecaster_skill.py",
        "source_url": doc["source_url"], "fetched_at": doc["fetched_at"],
        "note": ("Forecasters are anonymous; the ECB publishes them only by "
                 "number and this makes no attempt to identify them."),
        "seed": SEED, "iters": ITERS, "min_years": MIN_YEARS,
        "n_forecasters": len(elig),
        "n_forecasts": sum(len(v) for v in elig.values()),
        "year_difficulty": {str(t): round(p, 4) for t, p in sorted(p_y.items())},
        "miss_direction": {
            "by_year": {str(t): {"inside": a, "too_low": b, "too_high": c}
                        for t, (a, b, c) in sorted(side.items())},
            "pooled": {"inside": ins, "too_low": low, "too_high": high},
            "zero_coverage_years": sorted(dead),
            "zero_coverage_all_too_low": dlow == dn,
            "zero_coverage_n": dn},
        "spread": {"observed_sd": round(obs, 4),
                   "null_median_sd": round(statistics.median(sims), 4),
                   "p": round(p_spread, 4)},
        "split_half": {"n": len(pairs), "r": round(r, 4),
                       "p": round(p_split, 4)},
        "luck_band": [round(luck[0], 4), round(luck[1], 4)],
        "above_bar": len(good),
        "cleared_the_bar": cleared,
        "width": {"r_with_skill": round(r_w, 4),
                  "r2": round(r_w * r_w, 4),
                  "median_width_pp": round(statistics.median(xs), 3),
                  "by_forecaster": {w: round(width[w], 3) for w in elig},
                  "clipping_cut": {"n_clipped": n_clip, "n_all": n_all,
                                   "n_forecasters": len(clean),
                                   "r": round(r_clean, 4)},
                  "split_half_residual": {"n": len(halves),
                                          "r": round(r_res, 4),
                                          "p": round(p_res, 4)},
                  "strata": {name: {"n": len(grp),
                                    "sd": round(statistics.pstdev(
                                        [score[w] for w in grp]), 4)}
                             for name, grp in (("narrow", narrow),
                                               ("wide", wide))}},
        "grid": [{"who": w, "skill": round(v, 4),
                  "width": round(width[w], 3),
                  "years": {str(t): int(h) for t, h, *_ in sorted(elig[w])}}
                 for w, v in srt],
        "examples": {w: [{"year": t, "lo": lo, "hi": hi,
                          "actual": round(actual[t], 2), "hit": int(h)}
                         for t, h, d, lo, hi, _c in sorted(elig[w])]
                     for w in (srt[0][0], srt[-1][0])},
        "scores": [{"who": w, "skill": round(v, 4), "years": len(elig[w]),
                    "coverage": round(cov[w], 4)} for w, v in srt],
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {OUT}")
    chart(out)
    chart_hero(out)
    chart_ranges(out)
    return 0


def corr_perm(pairs, rng, iters):
    """Pearson r over (x, y) pairs, with a two-sided permutation p-value."""
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx = sum((a - mx) ** 2 for a in xs)

    def rr(zs):
        mz = statistics.mean(zs)
        dd = (sx * sum((b - mz) ** 2 for b in zs)) ** .5
        if not dd:
            return float("nan")
        return sum((a - mx) * (b - mz) for a, b in zip(xs, zs)) / dd
    r = rr(ys)
    hit = 0
    for _ in range(iters):
        sh = ys[:]
        rng.shuffle(sh)
        v = rr(sh)
        if v == v and abs(v) >= abs(r):
            hit += 1
    return r, hit / iters


def chart(res):
    """Forecaster x year: which years each one was inside its own range."""
    rows = sorted(res["grid"], key=lambda r: -r["skill"])
    years = list(range(2000, 2026))
    diff = {int(k): v for k, v in res["year_difficulty"].items()}
    n = len(rows)
    W, L, T, R = 1600, 118, 300, 56
    CW, CH, BARW, GAP = 44.0, 12.0, 170, 26
    GW = CW * len(years)
    H = int(T + CH * n + 246)
    GREEN, RED, ABSENT = "#2e9e5b", "#d94040", "#eceff3"
    BLUE, DIM, INK, GRID = "#2f9bff", "#5b6472", "#1f2430", "#c9d1db"
    F = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
         "'Helvetica Neue',Arial,sans-serif")
    BX = L + GW + GAP

    def cx(t):
        return L + (t - years[0]) * CW

    def sx(v):
        return BX + BARW / 2 + (v / 0.40) * (BARW / 2)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="54" font-size="36" font-weight="700" fill="{INK}">'
         f'ECB inflation panel, 2000&#8211;2025: green = the outcome landed '
         f'inside their range</text>',
         f'<text x="{L}" y="98" font-size="23" fill="{DIM}">One row per '
         f'anonymous ECB forecaster ({n} of them, sorted best at the top), one '
         f'column per year. Each said where euro-area</text>',
         f'<text x="{L}" y="128" font-size="23" fill="{DIM}">inflation would '
         f'land with 80% confidence. '
         f'<tspan fill="{GREEN}" font-weight="700">Green</tspan> = it did. '
         f'<tspan fill="{RED}" font-weight="700">Red</tspan> = it did not. '
         f'Grey = not on the panel that year.</text>']

    # ---- legend
    ly = 158
    for i, (col, lab) in enumerate(((GREEN, "inside their range"),
                                    (RED, "missed"),
                                    (ABSENT, "not on the panel"))):
        lx = L + i * 300
        o.append(f'<rect x="{lx}" y="{ly}" width="26" height="15" fill="{col}" '
                 f'rx="2"/>')
        o.append(f'<text x="{lx + 36}" y="{ly + 13}" font-size="21" '
                 f'fill="{DIM}">{lab}</text>')

    # ---- year headers
    for t in years:
        hard = diff.get(t, 1) == 0
        o.append(f'<text x="{cx(t) + CW / 2:.1f}" y="{T - 46}" font-size="17" '
                 f'font-weight="{700 if hard else 400}" '
                 f'fill="{RED if hard else DIM}" text-anchor="middle">'
                 f'{t}</text>')
        o.append(f'<text x="{cx(t) + CW / 2:.1f}" y="{T - 22}" font-size="16" '
                 f'font-weight="{700 if hard else 400}" '
                 f'fill="{RED if hard else DIM}" text-anchor="middle">'
                 f'{diff.get(t, 0) * 100:.0f}%</text>')
    o.append(f'<text x="{L - 14}" y="{T - 22}" font-size="16" fill="{DIM}" '
             f'text-anchor="end">panel inside</text>')

    # ---- cells
    for r, row in enumerate(rows):
        yy = T + r * CH
        for t in years:
            h = row["years"].get(str(t))
            col = ABSENT if h is None else (GREEN if h else RED)
            o.append(f'<rect x="{cx(t):.1f}" y="{yy:.1f}" '
                     f'width="{CW - 1.5:.1f}" height="{CH - 1.5:.1f}" '
                     f'fill="{col}"/>')

    # ---- skill bars on the right
    o.append(f'<text x="{BX + BARW / 2:.0f}" y="{T - 46}" font-size="17" '
             f'fill="{DIM}" text-anchor="middle">their score</text>')
    o.append(f'<text x="{BX + BARW / 2:.0f}" y="{T - 22}" font-size="16" '
             f'fill="{DIM}" text-anchor="middle">vs an average panellist</text>')
    o.append(f'<line x1="{sx(0):.1f}" y1="{T}" x2="{sx(0):.1f}" '
             f'y2="{T + CH * n:.1f}" stroke="{GRID}" stroke-width="1"/>')
    for r, row in enumerate(rows):
        v, yy = row["skill"], T + r * CH
        x0, x1 = (sx(0), sx(v)) if v >= 0 else (sx(v), sx(0))
        o.append(f'<rect x="{x0:.1f}" y="{yy + 1:.1f}" '
                 f'width="{max(1.0, x1 - x0):.1f}" height="{CH - 3:.1f}" '
                 f'fill="{BLUE if v >= 0 else RED}" opacity="0.85"/>')
    for r, lab in ((0, "best"), (n - 1, "worst")):
        row, yy = rows[r], T + r * CH + CH - 2
        o.append(f'<text x="{L - 14}" y="{yy:.1f}" font-size="18" '
                 f'font-weight="700" fill="{INK}" text-anchor="end">'
                 f'{lab} #{row["who"]}</text>')
        o.append(f'<text x="{BX + BARW + 12}" y="{yy:.1f}" font-size="18" '
                 f'font-weight="700" fill="{INK}">'
                 f'{row["skill"] * 100:+.0f}pp</text>')

    # ---- the all-red columns
    gy = T + CH * n
    runs, cur = [], []
    for t in years:
        if diff.get(t, 1) == 0:
            cur.append(t)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    for run in runs:
        x0, x1 = cx(run[0]), cx(run[-1]) + CW - 1.5
        o.append(f'<path d="M{x0:.1f} {gy + 10} L{x0:.1f} {gy + 20} '
                 f'L{x1:.1f} {gy + 20} L{x1:.1f} {gy + 10}" fill="none" '
                 f'stroke="{RED}" stroke-width="2"/>')
        o.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{gy + 44}" font-size="19" '
                 f'font-weight="700" fill="{RED}" text-anchor="middle">'
                 f'{"nobody" if len(run) == 1 else "nobody, 3 years running"}'
                 f'</text>')

    o += [f'<text x="{L}" y="{H - 104}" font-size="22" fill="{INK}">'
          f'The columns are the story: in 2008, and again through '
          f'2021&#8211;2023, not one of the {n} was inside the range they '
          f'themselves had published.</text>',
          f'<text x="{L}" y="{H - 74}" font-size="22" fill="{INK}">The rows '
          f'are the other story: some are green far more often than others '
          f'&#8212; but the best of them still quotes a wider range.</text>',
          f'<text x="{L}" y="{H - 42}" font-size="18" fill="{DIM}">Data: ECB '
          f'Survey of Professional Forecasters, individual responses, '
          f'one-year-ahead (Q4 round of the year before) vs euro-area HICP, '
          f'{res["min_years"]}+ scored years each.</text>',
          f'<text x="{L}" y="{H - 16}" font-size="18" fill="{DIM}">Forecasters '
          f'are anonymous; the ECB publishes them only by number. &#183; method '
          f'and every number: '
          f'namikakmandev.github.io/ecb-forecaster-skill.html</text>',
          '</svg>']
    svg = "\n".join(o)
    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/ecb-forecaster-skill.svg"
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/ecb-forecaster-skill.png", W, H)


def chart_hero(res):
    """A feed-legible opener. The grid is unreadable at phone width; this is the
    one column-story from it, in type large enough to survive the downscale."""
    diff = {int(k): v for k, v in res["year_difficulty"].items()}
    years = sorted(diff)
    W, H, L, R, T, B = 1600, 1600, 130, 70, 470, 360
    pw, ph = W - L - R, H - T - B
    GREEN, RED, DIM, INK, GRID = ("#2e9e5b", "#d94040", "#5b6472", "#1f2430",
                                  "#dfe4ea")
    F = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
         "'Helvetica Neue',Arial,sans-serif")
    slot = pw / len(years)
    bw = slot * 0.66

    def bx(t):
        return L + (t - years[0]) * slot + (slot - bw) / 2

    def by(v):
        return T + (1 - v) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="120" font-size="62" font-weight="700" fill="{INK}">'
         f'Four years when Europe&#8217;s inflation</text>',
         f'<text x="{L}" y="196" font-size="62" font-weight="700" fill="{INK}">'
         f'forecasters <tspan fill="{RED}">all missed together</tspan></text>',
         f'<text x="{L}" y="270" font-size="33" fill="{DIM}">Each bar: the share '
         f'of the ECB&#8217;s forecaster panel whose own 80% range</text>',
         f'<text x="{L}" y="314" font-size="33" fill="{DIM}">contained that '
         f'year&#8217;s euro-area inflation. 64 forecasters, 2000&#8211;2025.</text>',
         f'<text x="{L}" y="378" font-size="30" font-weight="700" fill="{RED}">'
         f'In 2008, and again in 2021, 2022 and 2023: not one of them.</text>']

    for g in (0, .25, .5, .75, 1):
        o.append(f'<line x1="{L}" y1="{by(g):.1f}" x2="{L + pw}" '
                 f'y2="{by(g):.1f}" stroke="{GRID if g else "#9aa4b2"}" '
                 f'stroke-width="{1 if g else 2}"/>')
        o.append(f'<text x="{L - 18}" y="{by(g) + 11:.1f}" font-size="30" '
                 f'fill="{DIM}" text-anchor="end">{g * 100:.0f}%</text>')

    for t in years:
        v = diff[t]
        zero = v == 0
        o.append(f'<rect x="{bx(t):.1f}" y="{by(v):.1f}" width="{bw:.1f}" '
                 f'height="{max(3.0, by(0) - by(v)):.1f}" '
                 f'fill="{RED if zero else GREEN}" rx="3"/>')
        o.append(f'<text x="{bx(t) + bw / 2:.1f}" y="{by(0) + 44:.1f}" '
                 f'font-size="{28 if zero else 25}" '
                 f'font-weight="{700 if zero else 400}" '
                 f'fill="{RED if zero else DIM}" text-anchor="middle">'
                 f'&#8217;{str(t)[2:]}</text>')
        if zero:
            o.append(f'<text x="{bx(t) + bw / 2:.1f}" y="{by(0) - 16:.1f}" '
                     f'font-size="30" font-weight="700" fill="{RED}" '
                     f'text-anchor="middle">0%</text>')

    sy = T + ph + 130
    sk = [r["skill"] for r in res["scores"]]
    stats = ((f'{res["n_forecasters"]}', 'forecasters, followed'),
             (f'{(max(sk) - min(sk)) * 100:.0f}pp', 'best to worst'),
             (f'{res["above_bar"]} of {res["n_forecasters"]}',
              'cleared their own bar'))
    for i, (big, lab) in enumerate(stats):
        x = L + i * (pw / 3)
        o.append(f'<text x="{x:.0f}" y="{sy}" font-size="66" font-weight="700" '
                 f'fill="{INK}">{big}</text>')
        o.append(f'<text x="{x:.0f}" y="{sy + 44}" font-size="29" fill="{DIM}">'
                 f'{lab}</text>')

    o += [f'<text x="{L}" y="{H - 62}" font-size="26" fill="{DIM}">Data: ECB '
          f'Survey of Professional Forecasters, individual responses, '
          f'one-year-ahead vs euro-area HICP.</text>',
          f'<text x="{L}" y="{H - 26}" font-size="26" fill="{DIM}">Method and '
          f'every number: '
          f'namikakmandev.github.io/ecb-forecaster-skill.html</text>', '</svg>']
    svg = "\n".join(o)
    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/ecb-forecaster-hero.svg"
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/ecb-forecaster-hero.png", W, H)


def chart_ranges(res):
    """The best and the worst forecaster, year by year, in percentage points."""
    ex = res["examples"]
    who = [r["who"] for r in sorted(res["grid"], key=lambda r: -r["skill"])]
    best, worst = who[0], who[-1]
    years = list(range(2000, 2026))
    W, L, R, PH, TOP, GAPY = 1600, 118, 60, 340, 232, 128
    H = TOP + PH + GAPY + PH + 148
    PW = W - L - R
    LO, HI = -1.4, 9.2
    GREEN, RED, DIM, INK, GRID = ("#2e9e5b", "#d94040", "#5b6472", "#1f2430",
                                  "#dfe4ea")
    F = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
         "'Helvetica Neue',Arial,sans-serif")
    slot = PW / len(years)

    def px(t):
        return L + (t - years[0]) * slot + slot / 2

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="54" font-size="38" font-weight="700" fill="{INK}">'
         f'What a miss looks like &#8212; ECB panel, euro-area inflation, '
         f'2000&#8211;2025</text>',
         f'<text x="{L}" y="112" font-size="23" fill="{DIM}">Each bar is the '
         f'range one forecaster published for that year&#8217;s euro-area '
         f'inflation &#8212; the middle 80% of what they thought possible.</text>',
         f'<text x="{L}" y="142" font-size="23" fill="{DIM}">The dot is what '
         f'inflation actually did. Dot inside the bar = '
         f'<tspan fill="{GREEN}" font-weight="700">a hit</tspan>. Dot outside '
         f'= <tspan fill="{RED}" font-weight="700">a miss</tspan>. '
         f'A year with no bar is a year they were not on the panel.</text>']

    for k, (w, title) in enumerate(((best, "the best of the panel"),
                                    (worst, "the worst of the panel"))):
        t0 = TOP + k * (PH + GAPY)
        rec = {r["year"]: r for r in ex[w]}
        hits = sum(r["hit"] for r in ex[w])

        def py(v, t0=t0):
            return t0 + (HI - v) / (HI - LO) * PH

        o.append(f'<text x="{L}" y="{t0 - 30}" font-size="27" '
                 f'font-weight="700" fill="{INK}">Forecaster #{w} '
                 f'<tspan font-weight="400" fill="{DIM}">&#8212; {title}: '
                 f'inside its own range {hits} years out of '
                 f'{len(ex[w])}</tspan></text>')
        for g in (0, 2, 4, 6, 8):
            o.append(f'<line x1="{L}" y1="{py(g):.1f}" x2="{L + PW}" '
                     f'y2="{py(g):.1f}" stroke="{GRID if g else "#9aa4b2"}" '
                     f'stroke-width="1"/>')
            o.append(f'<text x="{L - 12}" y="{py(g) + 7:.1f}" font-size="19" '
                     f'fill="{DIM}" text-anchor="end">{g}%</text>')
        bw = slot * 0.42
        for t in years:
            r = rec.get(t)
            o.append(f'<text x="{px(t):.1f}" y="{t0 + PH + 30}" '
                     f'font-size="15" fill="{DIM}" text-anchor="middle">'
                     f'{str(t)[2:]}</text>')
            if not r:
                continue
            col = GREEN if r["hit"] else RED
            o.append(f'<rect x="{px(t) - bw / 2:.1f}" y="{py(r["hi"]):.1f}" '
                     f'width="{bw:.1f}" '
                     f'height="{max(2.0, py(r["lo"]) - py(r["hi"])):.1f}" '
                     f'fill="{col}" opacity="0.30" rx="2"/>')
            o.append(f'<rect x="{px(t) - bw / 2:.1f}" y="{py(r["hi"]):.1f}" '
                     f'width="{bw:.1f}" '
                     f'height="{max(2.0, py(r["lo"]) - py(r["hi"])):.1f}" '
                     f'fill="none" stroke="{col}" stroke-width="2" rx="2"/>')
            o.append(f'<circle cx="{px(t):.1f}" cy="{py(r["actual"]):.1f}" '
                     f'r="5.5" fill="{col}"/>')
            if t == 2022:
                o.append(f'<text x="{px(t) - 14:.1f}" '
                         f'y="{py(r["actual"]) + 6:.1f}" font-size="19" '
                         f'font-weight="700" fill="{RED}" text-anchor="end">'
                         f'8.4% &#8212; they said up to '
                         f'{r["hi"]:.1f}%</text>')

    o += [f'<text x="{L}" y="{H - 76}" font-size="22" fill="{INK}">Both were '
          f'wrong about 2022. The difference is that #{best} publishes ranges '
          f'wide enough to be right the rest of the time.</text>',
          f'<text x="{L}" y="{H - 42}" font-size="18" fill="{DIM}">Data: ECB '
          f'Survey of Professional Forecasters, individual responses, '
          f'one-year-ahead (Q4 round of the year before), vs euro-area HICP.'
          f'</text>',
          f'<text x="{L}" y="{H - 16}" font-size="18" fill="{DIM}">Forecasters '
          f'are anonymous; the ECB publishes them only by number. &#183; method '
          f'and every number: '
          f'namikakmandev.github.io/ecb-forecaster-skill.html</text>',
          '</svg>']
    svg = "\n".join(o)
    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/ecb-forecaster-ranges.svg"
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/ecb-forecaster-ranges.png", W, H)


if __name__ == "__main__":
    sys.exit(main())
