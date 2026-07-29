#!/usr/bin/env python3
"""Veterinary vs human pharmaceutical prices, US, 1982–2026 — the split, finally measured.

WPU0634 / WPU063403 (one signal, cross-confirmed at r=+1.00) give a veterinary-only
finished-preparations price. The comparator is the whole finished industry
(PCU325412325412) — human-dominated by value, so vet-vs-aggregate reads as vet-vs-human.

The veterinary series has publication gaps (1988-91 for the group, 1994-98, 2001,
2021-23 shared). NOTHING here spans a gap: every figure lives inside one continuous
segment, and segments of different lengths are compared on annualized rates.

Writes data/vethuman-derived.json.  Run: python scripts/analyse_vet_human.py
"""
import json, math, os
from statistics import mean, pstdev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)


def mnum(k):
    return int(k[:4]) * 12 + int(k[5:7])


def main():
    vet = load("vetapi-vet.json")["series"]["vet_prep_ppi"]
    u = load("vetapi-us.json")["series"]
    prep, api, cpi = u["prep_ppi"], u["api_ppi"], u["cpi"]

    common = sorted(set(vet) & set(prep) & set(api) & set(cpi))
    # split into continuous runs of the vet series
    segs, cur = [], [common[0]]
    for k in common[1:]:
        if mnum(k) - mnum(cur[-1]) == 1:
            cur.append(k)
        else:
            segs.append(cur)
            cur = [k]
    segs.append(cur)
    segs = [s for s in segs if len(s) >= 24]     # a segment under 2 years proves nothing

    def real(s, ks):
        return {k: s[k] / cpi[k] for k in ks}

    def chg(r, ks):
        return (r[ks[-1]] / r[ks[0]] - 1) * 100

    def ann(r, ks):
        months = mnum(ks[-1]) - mnum(ks[0])
        return ((r[ks[-1]] / r[ks[0]]) ** (12 / months) - 1) * 100

    def yoy_corr(ra, rb, ks):
        kset = set(ks)
        xs, ys = [], []
        for k in ks:
            prev = f"{int(k[:4])-1}-{k[5:7]}"
            if prev in kset:
                xs.append(ra[k] / ra[prev] - 1)
                ys.append(rb[k] / rb[prev] - 1)
        if len(xs) < 24:
            return None, len(xs)
        ma, mb = mean(xs), mean(ys)
        den = math.sqrt(sum((x-ma)**2 for x in xs) * sum((y-mb)**2 for y in ys))
        return (sum((x-ma)*(y-mb) for x, y in zip(xs, ys)) / den if den else None), len(xs)

    out = {"comparator_note": ("PCU325412325412 covers human + veterinary together, but "
                               "veterinary is a single-digit share of industry value, so "
                               "the aggregate is read as the human side. No pure-human "
                               "index exists to subtract against."),
           "segments": []}

    for ks in segs:
        rv, rp, ra = real(vet, ks), real(prep, ks), real(api, ks)
        r, n = yoy_corr(rv, rp, ks)
        out["segments"].append({
            "span": [ks[0], ks[-1]], "months": len(ks),
            "real_change_pct": {"vet": round(chg(rv, ks), 1),
                                "human_industry": round(chg(rp, ks), 1),
                                "ingredient": round(chg(ra, ks), 1)},
            "annualized_pct": {"vet": round(ann(rv, ks), 2),
                               "human_industry": round(ann(rp, ks), 2),
                               "ingredient": round(ann(ra, ks), 2)},
            "yoy_corr_vet_vs_human": None if r is None else round(r, 2),
            "yoy_n": n,
        })

    # volatility, full overlap (monthly changes only — gaps skipped, not bridged)
    def vol(s):
        ds = []
        for i in range(1, len(common)):
            if mnum(common[i]) - mnum(common[i-1]) == 1:
                ds.append(math.log(s[common[i]] / s[common[i-1]]))
        return pstdev(ds)
    out["monthly_volatility"] = {"vet": round(vol(vet), 4), "human_industry": round(vol(prep), 4),
                                 "note": "stdev of month-on-month log changes within continuous months"}

    # where vet would rank among the human therapeutic classes, on the long clean window
    big = max(segs, key=len)
    cls = load("vetprice-classes.json")["series"]
    a, b = big[0], big[-1]
    rows = []
    for key, sid in [("cardiovascular", "WPU063803"), ("cns_sense", "WPU063802"),
                     ("neoplasm_endocrine", "WPU063801"), ("parasitic_infective", "WPU063808"),
                     ("respiratory", "WPU063804"), ("digestive_gu", "WPU063805"),
                     ("skin", "WPU063806"), ("vitamin_nutrient", "WPU063807")]:
        s = cls[key]
        if a in s and b in s:
            rows.append((key, round((s[b]/cpi[b]) / (s[a]/cpi[a]) * 100 - 100, 1)))
    rv = real(vet, big)
    rows.append(("VETERINARY", round(chg(rv, big), 1)))
    rows.sort(key=lambda t: -t[1])
    out["rank_on_long_segment"] = {"window": [a, b], "ranking": rows,
                                   "vet_rank": [i+1 for i, t in enumerate(rows)
                                                if t[0] == "VETERINARY"][0],
                                   "of": len(rows)}

    with open(os.path.join(ROOT, "data", "vethuman-derived.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)

    print(f"{'segment':22s} {'m':>4s} {'vet %/yr':>9s} {'human %/yr':>11s} {'ingr %/yr':>10s}  corr")
    for s in out["segments"]:
        a_ = s["annualized_pct"]
        print(f"{s['span'][0]}→{s['span'][1]:8s} {s['months']:4d} {a_['vet']:+9.2f} "
              f"{a_['human_industry']:+11.2f} {a_['ingredient']:+10.2f}  "
              f"{s['yoy_corr_vet_vs_human']}")
    print("\nvolatility:", out["monthly_volatility"])
    print(f"\nvet's rank among human classes on {out['rank_on_long_segment']['window']}: "
          f"{out['rank_on_long_segment']['vet_rank']} of {out['rank_on_long_segment']['of']}")
    for k, v in out["rank_on_long_segment"]["ranking"]:
        print(f"   {k:22s} {v:+7.1f}%")
    print("\n[write] data/vethuman-derived.json")


if __name__ == "__main__":
    main()
