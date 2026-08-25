#!/usr/bin/env python3
"""Test whether a correlation is real, not just large.

Reports r together with the three things that decide whether it means anything:
significance (is it distinguishable from zero?), a confidence interval (how
precisely is it pinned down?), and the levels-vs-changes comparison (is it just
two trends passing each other?).

Stdlib only, so it runs anywhere.

  python3 scripts/corr_check.py data/cattle-us.json meat_idx feed_idx
  python3 scripts/corr_check.py data/cattle-us.json meat_idx data/cattle-eu.json meat_idx
  python3 scripts/corr_check.py --demo      # the spurious-correlation trap, shown

Money series MUST be deflated before correlating (data-integrity rule 2):

  python3 scripts/corr_check.py data/eu-vet-expenses.json EU27_2020 \
      data/herd-cattle.json EU \
      --per-x data/herd-cattle.json:EU \
      --deflate-x data/eu-hicp.json:hicp

  --from PERIOD / --to PERIOD     restrict the span, e.g. to one side of a
                                  methodology break
  --lag N                         correlate X at t against Y at t+N
  --scan-lags K                   print r at every lag from -K to +K, and judge
                                  whether any peak is a real lead or just noise
  --per-x / --per-y FILE:COL      divide that side through (e.g. to get per head)
  --deflate-x / --deflate-y F:C   divide by a price index, and name it in the output

Reading the output:
  p          probability of seeing an |r| this big if the true correlation were zero
  95% CI     range the true r plausibly lies in; if it straddles 0, you have nothing
  R2         share of the variance in one series explained by the other
  n_eff      sample size after discounting for autocorrelation (time series only)
"""
import json, math, random, sys

Z95 = 1.959964


# ---------------------------------------------------------------- statistics

def pearson(x, y):
    """Correlation coefficient. Returns None if either series is constant."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def slope(x, y):
    """OLS slope of y on x: how much y moves per one unit of x."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx


def t_stat(r, n):
    if abs(r) >= 1:
        return math.inf
    return r * math.sqrt(n - 2) / math.sqrt(1 - r * r)


def t_pvalue(t, df):
    """Two-sided p-value for Student's t, via the incomplete beta function."""
    t = abs(t)
    if t == math.inf:
        return 0.0
    return _betainc(df / 2.0, 0.5, df / (df + t * t))


def _betainc(a, b, x):
    """Regularised incomplete beta I_x(a, b), by continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _betainc(b, a, 1 - x)
    f, c, d = 1.0, 1.0, 0.0
    for i in range(200):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d
        c = 1.0 + num / c
        c = 1e-30 if abs(c) < 1e-30 else c
        f *= c * d
        if abs(1.0 - c * d) < 1e-10:
            break
    return front * (f - 1.0)


def fisher_ci(r, n, z=Z95):
    """Confidence interval on r via Fisher's z transform."""
    if n <= 3 or abs(r) >= 1:
        return None
    se = 1.0 / math.sqrt(n - 3)
    zr = math.atanh(r)
    return math.tanh(zr - z * se), math.tanh(zr + z * se)


def perm_pvalue(x, y, iters=5000, seed=1):
    """Assumption-free p-value: shuffle one series, count how often luck wins."""
    rng = random.Random(seed)
    obs = abs(pearson(x, y))
    ys, hits = list(y), 0
    for _ in range(iters):
        rng.shuffle(ys)
        r = pearson(x, ys)
        if r is not None and abs(r) >= obs:
            hits += 1
    return (hits + 1) / (iters + 1)


def lag1(s):
    """Lag-1 autocorrelation: how much each point is predicted by the previous."""
    if len(s) < 3:
        return 0.0
    r = pearson(s[:-1], s[1:])
    return r if r is not None else 0.0


def effective_n(x, y):
    """Sample size discounted for autocorrelation (Bartlett / Quenouille).

    120 monthly observations of a slow-moving series are nowhere near 120
    independent facts. This is what the p-value should really be based on.
    """
    a, b = lag1(x), lag1(y)
    prod = a * b
    if prod >= 1:
        return 3.0
    n_eff = len(x) * (1 - prod) / (1 + prod)
    return max(3.0, min(float(len(x)), n_eff))


# ---------------------------------------------------------------- reporting

def pct_change(s):
    """Period-on-period change. The form most economic series should be read in."""
    out = []
    for a, b in zip(s, s[1:]):
        out.append((b - a) / a if a not in (0, None) else 0.0)
    return out


def _crit_r(n, alpha):
    """Smallest |r| that clears alpha at this sample size."""
    lo, hi = 0.0, 0.999999
    for _ in range(60):
        mid = (lo + hi) / 2
        if t_pvalue(t_stat(mid, n), n - 2) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def find_breaks(series, keys, name):
    """Flag single-period jumps far outside the normal range of movement.

    A methodology change (data-integrity rule 3) shows up as one implausible
    step. Correlations spanning it are comparing two different definitions.
    Uses median absolute deviation, so the break cannot hide the threshold.
    """
    ch = pct_change(series)
    if len(ch) < 8:
        return []
    med = sorted(ch)[len(ch) // 2]
    devs = sorted(abs(c - med) for c in ch)
    mad = devs[len(devs) // 2]
    if mad == 0:
        return []
    out = []
    for i, c in enumerate(ch):
        if abs(c - med) > 6 * mad and abs(c) > 0.10:
            out.append(f"{name}: {keys[i]} -> {keys[i+1]}  {c:+.1%}")
    return out


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


def report(label, x, y, adjust=True):
    """One line of verdict for a pair of aligned series."""
    n = len(x)
    r = pearson(x, y)
    if r is None:
        print(f"  {label:<9} constant series, no correlation defined")
        return None
    n_eff = effective_n(x, y) if adjust else float(n)
    p_raw = t_pvalue(t_stat(r, n), n - 2)
    p_adj = t_pvalue(t_stat(r, n_eff), n_eff - 2) if n_eff > 3 else 1.0
    ci = fisher_ci(r, int(n_eff) if adjust else n)
    ci_s = f"[{ci[0]:+.2f}, {ci[1]:+.2f}]" if ci else "     n/a     "
    print(f"  {label:<9} n={n:<5d} r={r:+.3f}  R2={r*r:5.1%}  "
          f"p={p_raw:.2e} {stars(p_raw):<4}  n_eff={n_eff:6.1f}  "
          f"p_adj={p_adj:.2e} {stars(p_adj):<4}  95% CI {ci_s}")
    return {"r": r, "n": n, "n_eff": n_eff, "p": p_raw, "p_adj": p_adj, "ci": ci}


def verdict(lev, chg):
    print()
    print("  VERDICT")
    if lev is None or chg is None:
        print("    Not enough data to judge.")
        return
    if lev["p"] < 0.05 and lev["p_adj"] >= 0.05:
        print(f"    WARNING: levels r={lev['r']:+.3f} looks overwhelming (p={lev['p']:.1e}),")
        print(f"    but {lev['n']} observations carry only ~{lev['n_eff']:.0f} independent facts.")
        print("    Adjusted for that, the levels correlation is NOT significant.")
        print()
    if chg["p_adj"] >= 0.05:
        if lev["p_adj"] < 0.05 or lev["p"] < 0.05:
            print("    The correlation in LEVELS does not survive in CHANGES.")
            print("    Most likely two trends passing each other. Do not publish the levels r.")
        else:
            print("    No relationship detectable in either form. Honest null.")
    else:
        drop = abs(lev["r"]) - abs(chg["r"])
        print(f"    Survives in changes: r={chg['r']:+.3f}, p_adj={chg['p_adj']:.2e}.")
        if drop > 0.3:
            print(f"    But it shrank by {drop:.2f} from the levels figure — the levels")
            print("    number was inflated by shared trend. Quote the changes figure.")
        if chg["ci"] and chg["ci"][0] * chg["ci"][1] < 0:
            print("    CI straddles zero once autocorrelation is accounted for. Treat as weak.")
        print("    Next: get the slope in units, and check what drives it.")
    print()
    print("    Still to check by hand: shared denominator, methodology breaks,")
    print("    confounders, out-of-sample. See .claude/skills/data-integrity/SKILL.md")


def scan_lags(xs, ys, span):
    """r at every lag from -span to +span, in levels AND in changes.

    Positive lag = X leads Y. A peak away from zero is only a lead if it is
    CLEARLY above lag zero (data-integrity rule 6). The levels column is shown
    only for comparison: on trending series every lag correlates, so the
    changes column is the one to read.
    """
    dx, dy = pct_change(xs), pct_change(ys)

    def at(a, b, L):
        p, q = (a[:-L or None], b[L:]) if L >= 0 else (a[-L:], b[:L])
        return (pearson(p, q), len(p)) if len(p) >= 10 else (None, len(p))

    print("\n  LAG PROFILE (positive lag = X leads Y)")
    print("    lag     n      r levels    r CHANGES")
    rows = []
    for L in range(-span, span + 1):
        rl, n = at(xs, ys, L)
        rc, _ = at(dx, dy, L)
        if rl is None or rc is None:
            continue
        rows.append((L, rl, rc, n))
    if not rows:
        return
    r0 = {L: rc for L, _, rc, _ in rows}.get(0)
    best = max(rows, key=lambda t: abs(t[2]))
    for L, rl, rc, n in rows:
        bar = "#" * int(abs(rc) * 40)
        mark = "  <- peak" if L == best[0] else ("  <- lag 0" if L == 0 else "")
        print(f"    {L:+3d}  {n:5d}    {rl:+.3f}      {rc:+.3f}  {bar}{mark}")
    if r0 is None:
        return
    print()
    if best[0] == 0:
        print("    Peak is AT lag 0. There is no lead here — the series move together.")
        return
    gain = abs(best[2]) - abs(r0)
    print(f"    Peak at lag {best[0]:+d} (r={best[2]:+.3f}) vs lag 0 (r={r0:+.3f}), gain {gain:+.3f}.")

    # The peak was SELECTED from many lags. Testing k lags and reporting the
    # best inflates significance; the threshold has to rise to match.
    k, n = len(rows), best[3]
    p_peak = t_pvalue(t_stat(best[2], n), n - 2)
    alpha = 0.05 / k
    crit = _crit_r(n, alpha)
    print(f"    {k} lags were tested and the best was kept, so the bar rises:")
    print(f"    peak p={p_peak:.4f} vs Bonferroni threshold {alpha:.4f} "
          f"(needs |r| > {crit:.3f} at n={n}).")
    if p_peak > alpha:
        print("    DOES NOT SURVIVE multiple testing. Treat the peak as noise.")
    elif gain < 0.05:
        print("    Survives, but the gain over lag 0 is noise. Not a lead.")
    elif gain < 0.10:
        print("    Survives, but marginal. No lead without a stated mechanism.")
    else:
        print("    Survives. Worth investigating — with a mechanism and out-of-sample.")


def analyse(name, xs, ys, unit_x="", unit_y=""):
    print(f"\n{name}")
    print("=" * len(name))
    lev = report("LEVELS", xs, ys)
    dx, dy = pct_change(xs), pct_change(ys)
    chg = report("CHANGES", dx, dy)
    b = slope(dx, dy)
    if b is not None:
        print(f"\n  Slope (changes): a 1% move in X goes with a {b:+.2f}% move in Y")
    print(f"  Permutation p (changes, assumption-free): {perm_pvalue(dx, dy):.4f}")
    verdict(lev, chg)


# ---------------------------------------------------------------- data loading

def load(path):
    """Read a data/*.json file into ({column: {period: value}}, source).

    Handles both shapes in data/: the {columns, rows} table used by the cattle
    files, and the {series: {name: {period: value}}} dict used by the Eurostat
    and FRED fetches.
    """
    d = json.load(open(path))
    src = d.get("source", "")
    if "rows" in d and "columns" in d:
        cols, rows = d["columns"], d["rows"]
        out = {c: {} for c in cols[1:]}
        for row in rows:
            for c, v in zip(cols[1:], row[1:]):
                if isinstance(v, (int, float)):
                    out[c][row[0]] = float(v)
        return out, src
    if "series" in d and isinstance(d["series"], dict):
        out = {}
        for name, obj in d["series"].items():
            if isinstance(obj, dict):
                out[name] = {k: float(v) for k, v in obj.items()
                             if isinstance(v, (int, float))}
        # deflators shipped alongside the data, e.g. 'cpi' or 'hicp'
        for extra in ("cpi", "hicp", "deflator"):
            if isinstance(d.get(extra), dict):
                out[extra] = {k: float(v) for k, v in d[extra].items()
                              if isinstance(v, (int, float))}
        return out, src
    sys.exit(f"{path}: unrecognised shape. Expected 'rows' or 'series'.")


def spec(text, what):
    """Parse a FILE:COL argument into its series, plus the source line."""
    if ":" not in text:
        sys.exit(f"{what}: expected FILE:COLUMN, got '{text}'")
    path, col = text.rsplit(":", 1)
    data, src = load(path)
    if col not in data:
        sys.exit(f"{path}: no column '{col}'. Available: {', '.join(data)}")
    return data[col], f"{path}:{col} — {src}"


def to_annual(series):
    """Collapse monthly YYYY-MM keys to annual means. Annual input passes through."""
    if not any("-" in k for k in series):
        return series
    buckets = {}
    for k, v in series.items():
        buckets.setdefault(k.split("-")[0], []).append(v)
    return {y: sum(vs) / len(vs) for y, vs in buckets.items()}


def divide(num, den):
    """Elementwise ratio on the overlapping periods, matching annual to monthly."""
    if any("-" in k for k in num) != any("-" in k for k in den):
        num, den = to_annual(num), to_annual(den)
    return {k: num[k] / den[k] for k in set(num) & set(den) if den[k]}


def align(a, b):
    """Keep only the periods present in both series, in order.

    If one side is monthly and the other annual, the monthly one is averaged
    to annual first — otherwise the keys never intersect.
    """
    if any("-" in k for k in a) != any("-" in k for k in b):
        a, b = to_annual(a), to_annual(b)
    keys = sorted(set(a) & set(b))
    return [a[k] for k in keys], [b[k] for k in keys], keys


def demo():
    """Two series with NO relationship by construction. Watch levels lie."""
    rng = random.Random(7)
    a, b = [100.0], [50.0]
    for _ in range(119):
        a.append(a[-1] + 0.4 + rng.gauss(0, 1))
        b.append(b[-1] + 0.3 + rng.gauss(0, 1))
    print("\nDEMO — two independent random walks, true correlation is exactly zero.")
    print("If a method calls this significant, that method cannot protect you.")
    analyse("Independent random walks", a, b)


def main(argv):
    if "--demo" in argv:
        return demo()

    opts, pos = {}, []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            if i + 1 >= len(argv):
                sys.exit(f"{argv[i]} needs a FILE:COLUMN argument")
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1

    if len(pos) == 3:                        # one file, two columns
        f1, c1, f2, c2 = pos[0], pos[1], pos[0], pos[2]
    elif len(pos) == 4:                      # two files, one column each
        f1, c1, f2, c2 = pos
    else:
        sys.exit(__doc__)

    d1, _ = load(f1)
    d2, _ = load(f2)
    if c1 not in d1:
        sys.exit(f"{f1}: no column '{c1}'. Available: {', '.join(d1)}")
    if c2 not in d2:
        sys.exit(f"{f2}: no column '{c2}'. Available: {', '.join(d2)}")

    X, Y = d1[c1], d2[c2]
    notes = []
    for flag, side in (("--per-x", "X"), ("--per-y", "Y")):
        if flag in opts:
            den, src = spec(opts[flag], flag)
            if side == "X":
                X = divide(X, den)
            else:
                Y = divide(Y, den)
            notes.append(f"  {side} divided by  {src}")
    for flag, side in (("--deflate-x", "X"), ("--deflate-y", "Y")):
        if flag in opts:
            defl, src = spec(opts[flag], flag)
            if side == "X":
                X = divide(X, defl)
            else:
                Y = divide(Y, defl)
            notes.append(f"  {side} DEFLATED by  {src}")

    # data-integrity rule 6: dividing X by the very series you correlate it
    # against manufactures a negative correlation out of arithmetic alone.
    shared = []
    if opts.get("--per-x", "").replace(":", "|") == f"{f2}|{c2}":
        shared.append(f"X is divided by {f2}:{c2}, which IS Y")
    if opts.get("--per-y", "").replace(":", "|") == f"{f1}|{c1}":
        shared.append(f"Y is divided by {f1}:{c1}, which IS X")
    if shared:
        print()
        print("  !! SHARED DENOMINATOR")
        for line in shared:
            print(f"     {line}.")
        print("     Part of any correlation here is arithmetic, not economics.")
        print("     Re-run without --per to see how much of it survives.")

    if "--from" in opts or "--to" in opts:
        END = chr(0xFFFF)
        lo, hi = opts.get("--from", ""), opts.get("--to", END)
        X = {k: v for k, v in X.items() if lo <= k <= hi}
        Y = {k: v for k, v in Y.items() if lo <= k <= hi}
        span = f"{lo or 'start'} .. {'end' if hi == END else hi}"
        notes.append(f"  restricted to {span}")

    xs, ys, keys = align(X, Y)
    if len(xs) < 5:
        sys.exit(f"Only {len(xs)} overlapping periods. Too few to test.")

    breaks = find_breaks(xs, keys, "X") + find_breaks(ys, keys, "Y")
    if breaks:
        print()
        print("  !! POSSIBLE METHODOLOGY BREAK")
        for b in breaks:
            print(f"     {b}")
        print("     A correlation spanning a break compares two definitions.")
        print("     Split the series there and test each regime separately.")
    label_x = f"{f1}:{c1}" + (" per unit" if "--per-x" in opts else "") + \
              (" (real)" if "--deflate-x" in opts else " (NOMINAL)" if "--deflate-y" in opts else "")
    label_y = f"{f2}:{c2}" + (" per unit" if "--per-y" in opts else "")
    title = f"{label_x}  vs  {label_y}   [{keys[0]} to {keys[-1]}]"
    if notes:
        print()
        print("Transformations applied:")
        for n in notes:
            print(n)

    if "--scan-lags" in opts:
        print(f"\n{title}")
        print("=" * len(title))
        scan_lags(xs, ys, int(opts["--scan-lags"]))
        return

    if "--lag" in opts:
        L = int(opts["--lag"])
        xs, ys = (xs[:-L or None], ys[L:]) if L >= 0 else (xs[-L:], ys[:L])
        title += f"   [X leads by {L}]" if L else ""

    analyse(title, xs, ys)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except BrokenPipeError:          # piping into head/less is not an error
        sys.stderr.close()
