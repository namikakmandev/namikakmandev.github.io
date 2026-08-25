#!/usr/bin/env python3
"""Build the Poland broiler feed/meat parity series from fetched Eurostat data.

Input   data/pl-broiler-ppi.json      (scripts/fetch.py pl-broiler-ppi)
        data/pl-broiler-anchor.json   (optional; {"chicken": {year: PLN/100kg},
                                       "feed": {year: PLN/100kg}} — written by a
                                       later fetch entry once the probe confirms
                                       the apri_ap product codes)
Output  data/broiler-parity-pl.json   {"meta": ..., "series": [[YYYY-MM, parity,
                                       meat_idx, feed_idx], ...]}

Anchoring, mirroring the TR construction (broiler-margin.html): the monthly
movement is the C1012÷C1091 index ratio; the level is scaled so the anchor
year's average equals the absolute kg-feed-per-kg-chicken parity from Eurostat
annual prices. Without an anchor the ratio is published as-is with
meta.anchored=false — the page then uses it for the indexed comparison only and
must NOT label it kg/kg.

No network access here: this runs after fetch.py, in Actions or locally.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "pl-broiler-ppi.json")
ANCHOR = os.path.join(ROOT, "data", "pl-broiler-anchor.json")
OUT = os.path.join(ROOT, "data", "broiler-parity-pl.json")

MEAT, FEED = "C1012", "C1091"


def main():
    if not os.path.exists(SRC):
        print(f"[skip] {SRC} not fetched yet — nothing to build")
        return 0
    src = json.load(open(SRC))
    series = src.get("series", {})
    meat, feed = series.get(MEAT) or {}, series.get(FEED) or {}
    if not meat or not feed:
        print(f"[skip] pl-broiler-ppi has empty series (meat={len(meat)}, "
              f"feed={len(feed)}) — check data/_fetch-report.json / probe")
        return 0

    months = sorted(set(meat) & set(feed))
    ratio = {m: meat[m] / feed[m] for m in months if feed[m]}

    # integrity: contiguity — a silent gap must be visible in meta, not swallowed
    gaps = []
    for a, b in zip(months, months[1:]):
        ya, ma = map(int, a.split("-")); yb, mb = map(int, b.split("-"))
        if (yb - ya) * 12 + (mb - ma) != 1:
            gaps.append(f"{a}->{b}")

    anchored, anchor_year, anchor_value, scale = False, None, None, None
    if os.path.exists(ANCHOR):
        anc = json.load(open(ANCHOR)).get("series", {})
        chicken, feed_abs = anc.get("chicken") or {}, anc.get("feed") or {}
        yrs = [y for y in sorted(set(chicken) & set(feed_abs), reverse=True)
               if feed_abs[y] and len([m for m in months if m[:4] == str(y)]) == 12]
        if yrs:
            anchor_year = yrs[0]
            anchor_value = chicken[anchor_year] / feed_abs[anchor_year]
            yr_mean = (sum(ratio[m] for m in months if m[:4] == str(anchor_year))
                       / 12)
            scale = anchor_value / yr_mean
            anchored = True

    out_series = [[m, round(ratio[m] * (scale or 1.0), 4),
                   round(meat[m], 2), round(feed[m], 2)] for m in months]
    meta = {
        "metric": "broiler parity — chicken-meat price / feed price",
        "construction": "Eurostat sts_inppd_m PL: PPI C1012 / PPI C1091",
        "anchored": anchored,
        "anchor": ({"year": anchor_year, "kg_feed_per_kg_chicken":
                    round(anchor_value, 3),
                    "source": "Eurostat annual absolute prices (apri_ap)"}
                   if anchored else
                   "NONE — values are an index ratio (base-year ~1.0), NOT kg/kg;"
                   " dynamics only"),
        "span": [months[0], months[-1]],
        "n": len(months),
        "gaps": gaps,
        "unit_base": src.get("config", {}).get("params", {}).get("unit"),
        "built_by": "scripts/build_broiler_parity_pl.py",
    }
    json.dump({"meta": meta, "series": out_series}, open(OUT, "w"),
              separators=(",", ":"))
    print(f"[ok] {OUT}: {len(months)} months {months[0]}..{months[-1]}, "
          f"anchored={anchored}" + (f" ({anchor_year}: {anchor_value:.3f})"
                                    if anchored else "") +
          (f", GAPS: {gaps}" if gaps else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
