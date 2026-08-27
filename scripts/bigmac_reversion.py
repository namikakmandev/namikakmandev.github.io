#!/usr/bin/env python3
"""Full data-integrity pass on the Big Mac mean-reversion finding.

Question: does today's Big Mac valuation predict its own subsequent correction?
The probe said yes with half-life ~1y — but it demeaned by each country's
FULL-SAMPLE mean, which includes the future. This pass removes that and every
other flattery we could identify.
"""
import json, math, random
import numpy as np

eur = json.load(open('data/bigmac-eur.json'))['series']
usd = json.load(open('data/bigmac-usd.json'))['series']

def panel(series, transform=None, drop=()):
    """-> {cc: [(date, value)]} sorted, transformed, countries dropped."""
    out = {}
    for cc, ser in series.items():
        if cc in drop: continue
        obs = sorted(ser.items())
        if transform: obs = [(d, transform(cc, d, v)) for d, v in obs]
        obs = [(d, v) for d, v in obs if v is not None and np.isfinite(v)]
        if len(obs) >= 10: out[cc] = obs
    return out

def build_xy(pan, k, mode, min_hist=6):
    """Pairs (deviation_t, val_{t+k}-val_t) per country. mode: raw|full|past."""
    rows = []   # (cc, dev, fut_change, date)
    for cc, obs in pan.items():
        vals = [v for _, v in obs]
        full_mean = np.mean(vals)
        for i in range(len(obs) - k):
            v = vals[i]
            if mode == "raw":       dev = v
            elif mode == "full":    dev = v - full_mean
            else:                   # past: expanding window, no look-ahead
                if i < min_hist: continue
                dev = v - np.mean(vals[:i])
            rows.append((cc, dev, vals[i + k] - v, obs[i][0]))
    return rows

def slope(rows):
    x = np.array([r[1] for r in rows]); y = np.array([r[2] for r in rows])
    X = np.column_stack([np.ones_like(x), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ b
    r2 = 1 - resid.var() / y.var() if y.var() > 0 else 0
    return b[1], r2, len(rows)

def cluster_boot(rows, iters=2000, seed=42):
    """Resample COUNTRIES with replacement -> percentile CI on the slope."""
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

def halflife_years(b, k):
    rho_k = 1 + b
    if not (0 < rho_k < 1): return None
    return (k * math.log(0.5) / math.log(rho_k)) / 2   # semiannual periods

def report(tag, pan, k=4, modes=("raw", "full", "past")):
    print(f"\n== {tag}  (horizon {k/2:.0f}y) " + "="*30)
    for mode in modes:
        rows = build_xy(pan, k, mode)
        if len(rows) < 50: print(f"  {mode:5s}: too few obs"); continue
        b, r2, n = slope(rows)
        lo, hi = cluster_boot(rows)
        hl = halflife_years(b, k)
        sig = "SIG" if hi < 0 or lo > 0 else "ns "
        print(f"  {mode:5s}: b={b:+.3f}  cluster-CI[{lo:+.3f},{hi:+.3f}] {sig}  "
              f"R2={r2*100:4.0f}%  n={n:5d}  halflife={f'{hl:.1f}y' if hl else '—'}")
    return build_xy(pan, k, "past")

# ---------------- 1. EUR base, all countries -------------------------------
pan_eur = panel(eur, drop={"EUZ"})
rows_main = report("EUR base, all countries", pan_eur)

# ---------------- 2. outlier audit -----------------------------------------
devs = sorted(rows_main, key=lambda r: -abs(r[1]))[:8]
print("\n  largest past-mean deviations (country, date, dev):")
for cc, dev, fut, d in devs: print(f"    {cc} {d}  dev={dev:+.2f}  future_chg={fut:+.2f}")
crazy = {cc for cc, dev, _, _ in rows_main if abs(dev) > 1.0 for cc in [cc]}
print(f"  countries with any |dev|>100%: {sorted(crazy)}")
pan_clean = panel(eur, drop={"EUZ"} | crazy)
report("EUR base, extreme countries dropped", pan_clean, modes=("past",))

# ---------------- 3. USD base robustness -----------------------------------
usa = dict(usd["USA"])
def usd_val(cc, d, v):
    u = usa.get(d)
    return math.log(v / u) if u and v > 0 else None
pan_usd = panel(usd, transform=usd_val, drop={"USA"})
report("USD base (log price ratio vs US)", pan_usd, modes=("past",))

# ---------------- 4. subperiod stability -----------------------------------
early = [r for r in rows_main if r[3] < "2013"]
late  = [r for r in rows_main if r[3] >= "2013"]
for tag, rows in (("2000-2012", early), ("2013-2026", late)):
    b, r2, n = slope(rows); lo, hi = cluster_boot(rows)
    hl = halflife_years(b, 4)
    print(f"\n  past-mean, {tag}: b={b:+.3f} CI[{lo:+.3f},{hi:+.3f}]  n={n}  "
          f"halflife={f'{hl:.1f}y' if hl else '—'}")

# ---------------- 5. horizons with the honest method -----------------------
print()
for k in (2, 4, 6):
    rows = build_xy(pan_eur, k, "past")
    b, r2, n = slope(rows); lo, hi = cluster_boot(rows)
    hl = halflife_years(b, k)
    print(f"  past-mean, horizon {k/2:.0f}y: b={b:+.3f} CI[{lo:+.3f},{hi:+.3f}]  "
          f"R2={r2*100:.0f}%  halflife={f'{hl:.1f}y' if hl else '—'}")
