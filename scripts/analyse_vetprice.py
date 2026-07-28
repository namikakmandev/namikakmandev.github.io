#!/usr/bin/env python3
"""Where the pricing power is: US pharmaceutical prices by therapeutic class, 2001–2026.

The parity study asked whether finished medicine prices track the ingredient inside
them. This one asks the follow-up a seller actually needs: *which parts of the book
hold real price, and which erode* — and where the antibiotic line sits among them.

Every class is deflated by CPI-U, because a nominal price that rises 2% a year in a
3% inflation is a price cut. Reads only committed data, writes data/vetprice-derived.json.

Run:  python scripts/analyse_vetprice.py
"""
import json, os
from statistics import mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Titles as published by FRED, read off the source — never inferred from the series id.
LABELS = {
    "all_preparations":      ("All pharmaceutical preparations",            "WPU0638"),
    "neoplasm_endocrine":    ("Neoplasms, endocrine & metabolic",           "WPU063801"),
    "cns_sense":             ("Central nervous system & sense organs",      "WPU063802"),
    "cardiovascular":        ("Cardiovascular",                             "WPU063803"),
    "respiratory":           ("Respiratory",                                "WPU063804"),
    "digestive_gu":          ("Digestive & genito-urinary",                 "WPU063805"),
    "skin":                  ("Skin",                                       "WPU063806"),
    "vitamin_nutrient":      ("Vitamin, nutrient & hematinic",              "WPU063807"),
    "parasitic_infective":   ("Parasitic & infective diseases",             "WPU063808"),
    "antibiotics_broad_medium": ("Broad & medium spectrum antibiotics",     "WPU06380802"),
}
CLASSES = [k for k in LABELS if k not in ("all_preparations", "antibiotics_broad_medium")]


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)


def main():
    s = load("vetprice-classes.json")["series"]
    cpi = s["cpi"]
    api = s["api_input"]

    def real(series):
        return {m: series[m] / cpi[m] for m in series if m in cpi}

    def rebase(series, base):
        b = series[base]
        return {m: round(series[m] / b * 100, 2) for m in sorted(series)}

    out = {"deflator": "US CPI-U, FRED CPIAUCSL",
           "note": ("Real terms throughout. Index numbers, not quantities — every figure "
                    "is a change between two dated observations, never a level."),
           "classes": {}, "checks": {}}

    # ---- the common window every eight-class series shares
    common = sorted(set.intersection(*[set(real(s[k])) for k in CLASSES]))
    c0, c1 = common[0], common[-1]
    out["common_window"] = [c0, c1, len(common)]

    rows = []
    for k in CLASSES + ["all_preparations"]:
        r = real(s[k])
        ks = sorted(r)
        peak_m = max(ks, key=lambda m: r[m])
        rows.append({
            "key": k, "label": LABELS[k][0], "series_id": LABELS[k][1],
            "span": [ks[0], ks[-1]], "n": len(ks),
            "real_change_pct": round((r[c1] / r[c0] - 1) * 100, 1),
            "peak_month": peak_m,
            "since_peak_pct": round((r[ks[-1]] / r[peak_m] - 1) * 100, 1),
            "indexed": rebase(r, c0),
        })
    rows.sort(key=lambda x: -x["real_change_pct"])
    out["ranking"] = [{kk: r[kk] for kk in r if kk != "indexed"} for r in rows]
    for r in rows:
        out["classes"][r["key"]] = r

    # ---- the antibiotic line: shorter span, so compared only on its own window
    ab = real(s["antibiotics_broad_medium"])
    ab_ks = sorted(ab)
    a0, a1 = ab_ks[0], ab_ks[-1]
    peers = {}
    for k in CLASSES + ["all_preparations"]:
        r = real(s[k])
        if a0 in r:
            peers[LABELS[k][0]] = round((r[a1] / r[a0] - 1) * 100, 1)
    out["antibiotics"] = {
        "series_id": LABELS["antibiotics_broad_medium"][1],
        "label": LABELS["antibiotics_broad_medium"][0],
        "span": [a0, a1], "n": len(ab_ks),
        "real_change_pct": round((ab[a1] / ab[a0] - 1) * 100, 1),
        "peak_month": max(ab_ks, key=lambda m: ab[m]),
        "since_peak_pct": round((ab[a1] / ab[max(ab_ks, key=lambda m: ab[m])] - 1) * 100, 1),
        "indexed": rebase(ab, a0),
        "peers_same_window": dict(sorted(peers.items(), key=lambda kv: -kv[1])),
        "caveat": (f"WPU06380802 begins {a0}, eight years after the eight-class panel. It is "
                   "compared only against the same window, never against the 2001 figures."),
    }
    # the ingredient input on the same window, so the margin direction is visible
    ra = real(api)
    out["antibiotics"]["api_input_same_window_pct"] = round((ra[a1] / ra[a0] - 1) * 100, 1)
    out["antibiotics"]["api_input_indexed"] = rebase(
        {m: ra[m] for m in ra if m >= a0}, a0)

    # ---- integrity: the input side over the eight-class window
    out["checks"]["api_input"] = {
        "series_id": "PCU325411325411",
        "real_change_pct_common_window": round((ra[c1] / ra[c0] - 1) * 100, 1),
        "window": [c0, c1],
        "meaning": ("The ingredient cost fell in real terms over the same window. A class "
                    "whose real price also fell was therefore losing ground on BOTH sides."),
    }
    # ---- integrity #3: any single implausible step would be a redesign, not a market
    breaks = {}
    for k in CLASSES + ["all_preparations", "antibiotics_broad_medium"]:
        v = s[k]
        ks = sorted(v)
        st = [(ks[i], round((v[ks[i]] / v[ks[i - 1]] - 1) * 100, 2))
              for i in range(1, len(ks)) if v[ks[i - 1]]]
        breaks[LABELS[k][1]] = max(st, key=lambda kv: abs(kv[1]))
    out["checks"]["largest_single_month_move"] = breaks

    with open(os.path.join(ROOT, "data", "vetprice-derived.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)

    print(f"US therapeutic classes, real (CPI-deflated), {c0} → {c1}  (n={len(common)} months)\n")
    print(f"{'class':40s} {'series':13s} {'real %':>9s} {'peak':>9s} {'since peak':>11s}")
    for r in rows:
        print(f"{r['label']:40s} {r['series_id']:13s} {r['real_change_pct']:+9.1f} "
              f"{r['peak_month']:>9s} {r['since_peak_pct']:+10.1f}%")
    A = out["antibiotics"]
    print(f"\nAntibiotics (own window {A['span'][0]} → {A['span'][1]}, n={A['n']}): "
          f"{A['real_change_pct']:+.1f}% real, peak {A['peak_month']}, "
          f"{A['since_peak_pct']:+.1f}% since")
    print(f"  ingredient input over the same window: {A['api_input_same_window_pct']:+.1f}% real")
    print("  peers on the same window:")
    for lab, v in A["peers_same_window"].items():
        print(f"    {lab:40s} {v:+7.1f}%")
    print(f"\ningredient input {c0}→{c1}: "
          f"{out['checks']['api_input']['real_change_pct_common_window']:+.1f}% real")
    print("\n[write] data/vetprice-derived.json")


if __name__ == "__main__":
    main()
