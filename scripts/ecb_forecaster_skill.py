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


def records(dists, actual):
    """-> {forecaster: [(year, hit)]} one year ahead, their own 80% band."""
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
        rec[who].append((t, 1 if lo <= actual[t] <= hi else 0))
    return {w: v for w, v in rec.items() if len(v) >= MIN_YEARS}


def year_difficulty(elig):
    """Panel coverage per year — how hard that year was for everyone."""
    by = collections.defaultdict(list)
    for v in elig.values():
        for t, h in v:
            by[t].append(h)
    return {t: sum(h) / len(h) for t, h in by.items()}


def skill(elig, p_y):
    """Hits above what the same years would give an average forecaster."""
    return {w: (sum(h for _, h in v) - sum(p_y[t] for t, _ in v)) / len(v)
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
          f"{sum(h for v in elig.values() for _, h in v) / sum(len(v) for v in elig.values()) * 100:.1f}%")
    print("  Forecasters are anonymous. The ECB publishes them only by number,")
    print("  and nothing here attempts to identify them.")

    hr("1. Year difficulty — the confounder that had to go first")
    for t in sorted(p_y):
        bar = "#" * round(p_y[t] * 30)
        print(f"    {t}  {p_y[t] * 100:>5.0f}%  {bar}")
    print("\n  A forecaster active only in 2003-2007 would look brilliant for")
    print("  free. Every score below is measured against what an average")
    print("  forecaster facing that forecaster's own years would have managed.")

    hr("2. Is the spread wider than luck?")
    obs = statistics.pstdev(list(score.values()))
    sims = []
    for _ in range(ITERS):
        s = []
        for v in elig.values():
            exp = sum(p_y[t] for t, _ in v)
            got = sum(1 for t, _ in v if rng.random() < p_y[t])
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
            return (sum(x for _, x in part)
                    - sum(p_y[t] for t, _ in part)) / len(part)
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

    hr("4. But almost nobody clears the bar")
    cov = {w: sum(h for _, h in v) / len(v) for w, v in elig.items()}
    good = sorted((c for c in cov.values() if c >= BAND), reverse=True)
    print(f"  forecasters whose 80% ranges actually held 80% of the time: "
          f"{len(good)} of {len(cov)}")
    print("  Skill in being honest about uncertainty is real, persistent, and")
    print("  almost universally insufficient.")

    # ------------------------------------------------------------------ export
    pool = []
    for _ in range(4000):
        for v in elig.values():
            exp = sum(p_y[t] for t, _ in v)
            got = sum(1 for t, _ in v if rng.random() < p_y[t])
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
        "spread": {"observed_sd": round(obs, 4),
                   "null_median_sd": round(statistics.median(sims), 4),
                   "p": round(p_spread, 4)},
        "split_half": {"n": len(pairs), "r": round(r, 4),
                       "p": round(p_split, 4)},
        "luck_band": [round(luck[0], 4), round(luck[1], 4)],
        "above_bar": len(good),
        "scores": [{"who": w, "skill": round(v, 4), "years": len(elig[w]),
                    "coverage": round(cov[w], 4)} for w, v in srt],
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {OUT}")
    chart(out)
    return 0


def chart(res):
    """One bar per forecaster, sorted, against the band luck alone would give."""
    srt = sorted(res["scores"], key=lambda r: r["skill"])
    lo_b, hi_b = res["luck_band"]
    W, H, L, R, T, B = 1600, 1000, 90, 60, 175, 140
    pw, ph = W - L - R, H - T - B
    n = len(srt)
    slot = pw / n
    bw = slot * 0.72
    lim = 0.38
    BLUE, RED, DIM, INK, GRID = "#2f9bff", "#d92b2b", "#5b6472", "#1f2430", "#d6dce4"
    F = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
         "'Helvetica Neue',Arial,sans-serif")

    def x(i):
        return L + i * slot + (slot - bw) / 2

    def y(v):
        return T + (1 - (v + lim) / (2 * lim)) * ph

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="52" font-size="37" font-weight="700" fill="{INK}">'
         f'They are not interchangeable &#8212; and the consensus hides it</text>',
         f'<text x="{L}" y="94" font-size="23" fill="{DIM}">Each bar is one '
         f'anonymous ECB forecaster: how much better or worse their 80% ranges '
         f'held up than an average</text>',
         f'<text x="{L}" y="124" font-size="23" fill="{DIM}">forecaster facing '
         f'the same years. {n} forecasters with {res["min_years"]}+ scored '
         f'years, euro-area inflation, 2000&#8211;2025.</text>',
         f'<text x="{L}" y="154" font-size="21" fill="{DIM}">Grey band = the '
         f'spread pure luck would produce if every forecaster were equally '
         f'good.</text>',
         f'<rect x="{L}" y="{y(hi_b):.1f}" width="{pw}" '
         f'height="{y(lo_b) - y(hi_b):.1f}" fill="{DIM}" opacity="0.13"/>']
    for g in (-0.3, -0.15, 0, 0.15, 0.3):
        o.append(f'<line x1="{L}" y1="{y(g):.1f}" x2="{L + pw}" y2="{y(g):.1f}" '
                 f'stroke="{GRID if g else INK}" stroke-width="{2 if g == 0 else 1}"/>')
        o.append(f'<text x="{L - 12}" y="{y(g) + 7:.1f}" font-size="20" '
                 f'fill="{DIM}" text-anchor="end">{g * 100:+.0f}pp</text>')
    for i, r in enumerate(srt):
        v = r["skill"]
        col = BLUE if v >= 0 else RED
        y0, y1 = (y(v), y(0)) if v >= 0 else (y(0), y(v))
        o.append(f'<rect x="{x(i):.1f}" y="{y0:.1f}" width="{bw:.1f}" '
                 f'height="{max(1, y1 - y0):.1f}" fill="{col}" rx="2"/>')
    best, worst = srt[-1], srt[0]
    o += [f'<text x="{x(n - 1) + bw / 2:.1f}" y="{y(best["skill"]) - 16:.1f}" '
          f'font-size="21" font-weight="700" fill="{BLUE}" text-anchor="end">'
          f'#{best["who"]}: {best["skill"] * 100:+.0f}pp</text>',
          f'<text x="{x(0) + bw / 2:.1f}" y="{y(worst["skill"]) + 30:.1f}" '
          f'font-size="21" font-weight="700" fill="{RED}" text-anchor="start">'
          f'#{worst["who"]}: {worst["skill"] * 100:+.0f}pp</text>',
          f'<text x="{L + pw / 2:.0f}" y="{T + ph + 62}" font-size="24" '
          f'fill="{INK}" text-anchor="middle">one bar per forecaster, worst to '
          f'best</text>',
          f'<text x="{L}" y="{H - 26}" font-size="18" fill="{DIM}">Data: ECB '
          f'Survey of Professional Forecasters, individual responses. '
          f'Forecasters are anonymous; the ECB publishes them only by '
          f'number.</text>', '</svg>']
    svg = "\n".join(o)
    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/ecb-forecaster-skill.svg"
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/ecb-forecaster-skill.png")


if __name__ == "__main__":
    sys.exit(main())
