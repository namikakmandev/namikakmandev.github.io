#!/usr/bin/env python3
"""Euro-member panel: does Big Mac mispricing revert when FX cannot move?

The published half-life study (scripts/bigmac_reversion.py) covers all 55
index countries but the euro area enters as ONE entity, because that is how
The Economist publishes the index. Its source data, though, carries local
prices for the euro members individually (data/bigmac-src-eur.json). Those
countries share a currency: their valuation against the euro-area average has
no exchange-rate channel, so any reversion must come through burger prices
alone. This panel is therefore a MECHANISM check, kept separate from the
headline numbers on purpose — pooling it into the main panel would mix two
different adjustment processes.

Method mirrors the published script: deviation = price_cc / price_EUZ - 1,
expanding past-only demeaning (no look-ahead), k counted in semi-annual rows
(spacing is regular from 2011 on — the mean pair span is printed to prove it),
country-clustered bootstrap CI, seeded and deterministic.

Data guards, from the source CSV itself:
  * LTU rows before 2015 are litas prices mislabeled EUR upstream — dropped.
  * BGR (n=1) and HRV (EUR only from 2023, n=7) fall under the min-obs rule.
"""
import json, math, random
import numpy as np

SRC = json.load(open('data/bigmac-src-eur.json'))['series']

EURO_ADOPTED = {   # first year the euro is legal tender; rows before are dropped
    "AUT": 1999, "BEL": 1999, "DEU": 1999, "ESP": 1999, "FIN": 1999,
    "FRA": 1999, "IRL": 1999, "ITA": 1999, "NLD": 1999, "PRT": 1999,
    "GRC": 2001, "SVN": 2007, "SVK": 2009, "EST": 2011, "LVA": 2014,
    "LTU": 2015, "HRV": 2023, "BGR": 2026,
}
MIN_OBS, MIN_HIST = 10, 6

euz = dict(sorted(SRC["EUZ"].items()))

def yearfrac(d):
    y, m, dd = d.split("-")
    return int(y) + (int(m) - 1) / 12 + (int(dd) - 1) / 365

def panel():
    """-> {cc: [(date, price/EUZ - 1)]}, guards applied."""
    out = {}
    for cc, ser in SRC.items():
        if cc == "EUZ": continue
        obs = [(d, v / euz[d] - 1) for d, v in sorted(ser.items())
               if d in euz and int(d[:4]) >= EURO_ADOPTED.get(cc, 9999)]
        if len(obs) >= MIN_OBS: out[cc] = obs
    return out

def build_xy(pan, k, mode):
    rows = []   # (cc, dev, future_change, date, span_years)
    for cc, obs in pan.items():
        vals = [v for _, v in obs]
        full_mean = np.mean(vals)
        for i in range(len(obs) - k):
            v = vals[i]
            if mode == "raw":    dev = v
            elif mode == "full": dev = v - full_mean
            else:
                if i < MIN_HIST: continue
                dev = v - np.mean(vals[:i])
            span = yearfrac(obs[i + k][0]) - yearfrac(obs[i][0])
            rows.append((cc, dev, vals[i + k] - v, obs[i][0], span))
    return rows

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

def halflife_years(b, mean_span):
    rho = 1 + b
    if not (0 < rho < 1): return None
    return mean_span * math.log(0.5) / math.log(rho)

def report(tag, pan, k=4, modes=("raw", "full", "past")):
    print(f"\n== {tag}  (horizon {k/2:.0f}y in rows) " + "=" * 24)
    for mode in modes:
        rows = build_xy(pan, k, mode)
        if len(rows) < 50:
            print(f"  {mode:5s}: too few obs (n={len(rows)})"); continue
        b, r2, n = slope(rows)
        lo, hi = cluster_boot(rows)
        span = float(np.mean([r[4] for r in rows]))
        hl = halflife_years(b, span)
        sig = "SIG" if hi < 0 or lo > 0 else "ns "
        print(f"  {mode:5s}: b={b:+.3f}  cluster-CI[{lo:+.3f},{hi:+.3f}] {sig}  "
              f"R2={r2*100:4.0f}%  n={n:5d}  mean-span={span:.2f}y  "
              f"halflife={f'{hl:.1f}y' if hl else '—'}")

pan = panel()
print(f"panel: {len(pan)} euro members "
      f"({', '.join(sorted(pan))})")
print(f"dropped by guards/min-obs: "
      f"{', '.join(sorted(set(SRC) - set(pan) - {'EUZ'}))}")
dev_now = {cc: obs[-1] for cc, obs in pan.items()}
big = sorted(dev_now.items(), key=lambda x: -abs(x[1][1]))[:5]
print("largest current gaps vs euro-area average: "
      + ", ".join(f"{cc} {d[1]:+.0%}" for cc, d in big))

report("Euro members vs euro-area average, prices only", pan)

# horizons with the honest method
print()
for k in (2, 4, 6):
    rows = build_xy(pan, k, "past")
    if len(rows) < 50:
        print(f"  past-mean, horizon {k/2:.0f}y: too few obs (n={len(rows)})"); continue
    b, r2, n = slope(rows); lo, hi = cluster_boot(rows)
    span = float(np.mean([r[4] for r in rows]))
    hl = halflife_years(b, span)
    print(f"  past-mean, horizon {k/2:.0f}y: b={b:+.3f} CI[{lo:+.3f},{hi:+.3f}]  "
          f"R2={r2*100:.0f}%  n={n}  halflife={f'{hl:.1f}y' if hl else '—'}")

# 2011 cohort only (drops the 2014-2018 joiners -> no entry-composition drift)
cohort = {cc: obs for cc, obs in pan.items() if obs[0][0] <= "2011-12-31"}
report("2011 cohort only", cohort, modes=("past",))
