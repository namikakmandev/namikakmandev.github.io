#!/usr/bin/env python3
"""Precompute every number the four-market deck quotes, from data/cattle-*.json.

Writes JSON to the path given as argv[1]. scripts/gen_parity_deck.js consumes it.
Keeping the numbers computed (never typed) is what makes the deck auditable.
"""
import json, statistics, sys

out = {}
def load(p): return json.load(open(p))["rows"]
series = {"US": load("data/cattle-us.json"), "EU": load("data/cattle-eu.json"),
          "TR": load("data/cattle-tr.json"), "IL": load("data/cattle-il.json")}
for k, rows in series.items():
    par = [(r[0], r[3]) for r in rows if r[3]]
    base = statistics.mean(v for m, v in par if m.startswith("2016"))
    idx = [(m, v / base * 100) for m, v in par]
    vals = [v for _, v in par]
    q = {}
    for m, v in idx:
        if m >= "2010":
            q.setdefault(m[:4] + "-Q" + str((int(m[5:7]) - 1) // 3 + 1), []).append(v)
    last10 = [v for m, v in par if m >= "2016-07"]
    out[k] = {"span": [par[0][0], par[-1][0]], "months": len(par),
              "mean": round(statistics.mean(vals), 4),
              "min": min(par, key=lambda t: t[1]), "max": max(par, key=lambda t: t[1]),
              "last": par[-1], "band": round(max(vals) / min(vals), 2),
              "idx_last": round(idx[-1][1]),
              "q_idx": {k2: round(statistics.mean(v), 1) for k2, v in sorted(q.items())},
              "cv10": round(statistics.pstdev(last10) / statistics.mean(last10) * 100)}
il_par = [(r[0], r[3]) for r in series["IL"]]
base = statistics.mean(v for m, v in il_par if m.startswith("2016"))
out["IL_monthly_idx"] = [[m, round(v / base * 100, 1)] for m, v in il_par]
# pair-choice robustness vs data/cattle-il-alt.json (TR-parallel pair)
try:
    alt = {r[0]: r[3] for r in load("data/cattle-il-alt.json")}
    P = dict(il_par)
    common = sorted(set(P) & set(alt))
    def i16(d):
        b = statistics.mean(v for m, v in d.items() if m.startswith("2016"))
        return {m: v / b * 100 for m, v in d.items()}
    Pi, Ai = i16(P), i16(alt)
    r_lvl = statistics.correlation([Pi[m] for m in common], [Ai[m] for m in common])
    def yoy(d, m):
        pm = f"{int(m[:4])-1}{m[4:]}"
        return d[m] / d[pm] - 1 if pm in d else None
    pairs = [(yoy(Pi, m), yoy(Ai, m)) for m in common]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    out["robustness"] = {"n": len(common), "r_level": round(r_lvl, 2),
                        "r_yoy": round(statistics.correlation([a for a, _ in pairs],
                                                              [b for _, b in pairs]), 2)}
except FileNotFoundError:
    out["robustness"] = None

json.dump(out, open(sys.argv[1], "w"), indent=1)
for k in ("US", "EU", "TR", "IL"):
    d = out[k]
    print(k, "| band x%.1f" % d["band"], "| today idx", d["idx_last"])
print("robustness:", out["robustness"])
