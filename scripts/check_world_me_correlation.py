#!/usr/bin/env python3
"""Does the world poultry/corn parity track the measured Middle East parities?

Reads data/broiler-parity.json only. Two coefficients per market, because the
level correlation of two trending ratios is mostly shared trend: r_level on
overlapping years, and r_dlog on log first differences (consecutive periods
only) — the honest test of co-movement. TR is monthly (year-over-year changes,
which also strips seasonality); the rest are annual against the annual mean of
the monthly world index.

Also checks what would drive any correlation: domestic maize vs world corn
(shared-denominator pass-through) per country.
"""
import json, math, os
from collections import defaultdict
from statistics import mean, pstdev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "data", "broiler-parity.json")))["regions"]


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my, sx, sy = mean(x), mean(y), pstdev(x), pstdev(y)
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (n * sx * sy)


def fmt(r):
    return "  n/a" if r is None else f"{r:5.2f}"


acc = defaultdict(list)
for m, _pi, _ci, par in d["WORLD"]["rows"]:
    acc[int(m[:4])].append(par)
wann = {y: mean(v) for y, v in acc.items() if len(v) >= 6}

print("annual country parity vs annual-mean world parity index")
print(f"{'ctry':5}{'n':>3} {'r_level':>8} {'r_dlog':>7}   span")
for k in ["EG", "QA", "IQ", "JO", "LB"]:
    rows = {r[0]: r[3] for r in d[k]["rows"]}
    yrs = sorted(set(rows) & set(wann))
    rl = pearson([rows[y] for y in yrs], [wann[y] for y in yrs])
    dx, dy = [], []
    for a, b in zip(yrs, yrs[1:]):
        if b == a + 1:
            dx.append(math.log(rows[b] / rows[a]))
            dy.append(math.log(wann[b] / wann[a]))
    print(f"{k:5}{len(yrs):>3} {fmt(rl):>8} {fmt(pearson(dx, dy)):>7}   "
          f"{yrs[0]}-{yrs[-1]} (dlog n={len(dx)})")

tr = {r[0]: r[3] for r in d["TR-monthly"]["rows"]}
wm = {r[0]: r[3] for r in d["WORLD"]["rows"]}
mths = sorted(set(tr) & set(wm))
rl = pearson([tr[m] for m in mths], [wm[m] for m in mths])
dx, dy = [], []
for m in mths:
    prev = f"{int(m[:4]) - 1}{m[4:]}"
    if prev in tr and prev in wm:
        dx.append(math.log(tr[m] / tr[prev]))
        dy.append(math.log(wm[m] / wm[prev]))
print(f"\nTR-monthly vs WORLD: n={len(mths)} r_level={fmt(rl)} "
      f"r_yoy={fmt(pearson(dx, dy))} (yoy n={len(dx)})")

wc = defaultdict(list)
for r in d["WORLD"]["rows"]:
    wc[int(r[0][:4])].append(r[2])
wcann = {y: mean(v) for y, v in wc.items() if len(v) >= 6}
print("\npass-through: domestic series vs world corn (log changes)")
for k in ["EG", "QA", "IQ"]:
    mz = {r[0]: r[2] for r in d[k]["rows"]}
    ch = {r[0]: r[1] for r in d[k]["rows"]}
    yrs = sorted(set(mz) & set(wcann))
    dmz, dwc, dch = [], [], []
    for a, b in zip(yrs, yrs[1:]):
        if b == a + 1:
            dmz.append(math.log(mz[b] / mz[a]))
            dwc.append(math.log(wcann[b] / wcann[a]))
            dch.append(math.log(ch[b] / ch[a]))
    print(f"{k}: maize~world corn {fmt(pearson(dmz, dwc))} | "
          f"chicken~world corn {fmt(pearson(dch, dwc))} (n={len(dmz)})")
