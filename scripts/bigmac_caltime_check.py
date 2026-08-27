#!/usr/bin/env python3
"""Calendar-time check of the Big Mac reversion headline.

The published script counts k ROWS ahead and assumes semi-annual spacing, but
2000-2010 spacing is irregular (annual early on). Here each episode instead
pairs date t with the observation CLOSEST to t + 2.0 calendar years (accepted
only within +/-0.35y), and the half-life uses the episodes' actual mean span.
Same expanding past-only demeaning, same country-clustered bootstrap.
"""
import json, math, random
import numpy as np

eur = json.load(open('data/bigmac-eur.json'))['series']

def yearfrac(d):
    y, m, dd = d.split("-")
    return int(y) + (int(m) - 1) / 12 + (int(dd) - 1) / 365

def slope(rows):
    x = np.array([r[1] for r in rows]); y = np.array([r[2] for r in rows])
    X = np.column_stack([np.ones_like(x), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ b
    r2 = 1 - resid.var() / y.var() if y.var() > 0 else 0
    return b[1], r2, len(rows)

def cluster_boot(rows, iters=2000, seed=42):
    rng = random.Random(seed)
    ccs = sorted({r[0] for r in rows})
    by = {cc: [r for r in rows if r[0] == cc] for cc in ccs}
    bs = []
    for _ in range(iters):
        sample = []
        for _ in ccs: sample += by[rng.choice(ccs)]
        if len(sample) > 10: bs.append(slope(sample)[0])
    bs.sort()
    return bs[int(len(bs)*0.025)], bs[int(len(bs)*0.975)]

TARGET, TOL, MIN_HIST = 2.0, 0.35, 6
rows, spans = [], []
for cc, ser in eur.items():
    if cc == "EUZ": continue
    obs = sorted(ser.items())
    obs = [(d, v) for d, v in obs if v is not None and np.isfinite(v)]
    if len(obs) < 10: continue
    ts = [yearfrac(d) for d, _ in obs]
    vals = [v for _, v in obs]
    for i in range(len(obs)):
        if i < MIN_HIST: continue
        # closest future observation to t_i + TARGET
        best, bestgap = None, TOL
        for j in range(i + 1, len(obs)):
            gap = abs(ts[j] - ts[i] - TARGET)
            if gap <= bestgap: best, bestgap = j, gap
            if ts[j] - ts[i] > TARGET + TOL: break
        if best is None: continue
        dev = vals[i] - np.mean(vals[:i])
        rows.append((cc, dev, vals[best] - vals[i]))
        spans.append(ts[best] - ts[i])

b, r2, n = slope(rows)
lo, hi = cluster_boot(rows)
span = float(np.mean(spans))
def hl(bb): return span * math.log(0.5) / math.log(1 + bb) if -1 < bb < 0 else float("nan")
print(f"episodes kept n={n} (mean span {span:.2f}y, sd {np.std(spans):.2f}, "
      f"max {max(spans):.2f}, min {min(spans):.2f})")
print(f"calendar-time: b={b:+.3f}  cluster-CI[{lo:+.3f},{hi:+.3f}]  R2={r2*100:.0f}%")
print(f"half-life: {hl(b):.1f}y  CI [{hl(hi):.1f}, {hl(lo):.1f}]y")
