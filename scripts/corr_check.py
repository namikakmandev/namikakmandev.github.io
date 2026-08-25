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
    """Read a data/*.json file into {column: {key: value}} keyed on the first column."""
    d = json.load(open(path))
    if "rows" not in d:
        sys.exit(f"{path}: no 'rows' key. Expected the data/*.json shape.")
    cols, rows = d["columns"], d["rows"]
    out = {c: {} for c in cols[1:]}
    for row in rows:
        key = row[0]
        for c, v in zip(cols[1:], row[1:]):
            if isinstance(v, (int, float)):
                out[c][key] = float(v)
    return out, cols


def align(a, b):
    """Keep only the periods present in both series, in order."""
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
    if len(argv) == 3:                       # one file, two columns
        f1, c1, c2 = argv[0], argv[1], argv[2]
        f2 = f1
    elif len(argv) == 4:                     # two files, one column each
        f1, c1, f2, c2 = argv
    else:
        sys.exit(__doc__)
    d1, cols1 = load(f1)
    d2, cols2 = load(f2)
    if c1 not in d1:
        sys.exit(f"{f1}: no column '{c1}'. Available: {', '.join(d1)}")
    if c2 not in d2:
        sys.exit(f"{f2}: no column '{c2}'. Available: {', '.join(d2)}")
    xs, ys, keys = align(d1[c1], d2[c2])
    if len(xs) < 5:
        sys.exit(f"Only {len(xs)} overlapping periods. Too few to test.")
    title = f"{f1}:{c1}  vs  {f2}:{c2}   [{keys[0]} to {keys[-1]}]"
    analyse(title, xs, ys)


if __name__ == "__main__":
    main(sys.argv[1:])
