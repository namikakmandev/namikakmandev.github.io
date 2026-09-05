#!/usr/bin/env python3
"""Build the Poland broiler feed/meat parity series from fetched Eurostat data.

Input   data/pl-broiler-ppi.json      (scripts/fetch.py pl-broiler-ppi)
        data/pl-anchor-chicken.json   (optional; Eurostat apri_ap_anouta
                                       11510000 — live chickens, PLN/100 kg
                                       LIVE weight, annual)
        data/pl-anchor-feed.json      (optional; Eurostat apri_ap_ina
                                       20624502 — complete broiler feed in
                                       bulk, PLN/100 kg, annual)
Output  data/broiler-parity-pl.json   {"meta": ..., "series": [[YYYY-MM, parity,
                                       meat_idx, feed_idx], ...]}

Anchoring, mirroring the TR construction (broiler-margin.html): the monthly
movement is the C1012÷C1091 index ratio; the level is scaled so the anchor
year's average equals the absolute kg-feed-per-kg-chicken parity from Eurostat
annual prices. The Eurostat chicken price is per kg LIVE weight while the TR
anchor (TEPGE) is per kg meat, so the live price is converted to
carcass-equivalent with a disclosed yield constant before anchoring — the
approximation and the raw live-based value both land in meta so the page can
state them. Without an anchor the ratio is published as-is with
meta.anchored=false — the page then uses it for the indexed comparison only and
must NOT label it kg/kg.

No network access here: this runs after fetch.py, in Actions or locally.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "pl-broiler-ppi.json")
ANCHOR_CHICKEN = os.path.join(ROOT, "data", "pl-anchor-chicken.json")
ANCHOR_FEED = os.path.join(ROOT, "data", "pl-anchor-feed.json")
OUT = os.path.join(ROOT, "data", "broiler-parity-pl.json")

MEAT, FEED = "C1012", "C1091"
# EU broiler carcass yield (eviscerated, ~65% grillers to 78% w/ giblets; the
# conventional planning figure is ~0.75-0.77). Any change must also change the
# method note on broiler-parity-pl-tr.html.
CARCASS_YIELD = 0.76


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

    anchored, anchor_year, anchor_value, live_value, scale = False, None, None, None, None
    if os.path.exists(ANCHOR_CHICKEN) and os.path.exists(ANCHOR_FEED):
        # both files are single-series, keyed by geo ("PL": {year: PLN/100kg})
        first = lambda p: next(iter(json.load(open(p)).get("series", {}).values()), {})
        chicken, feed_abs = first(ANCHOR_CHICKEN), first(ANCHOR_FEED)
        yrs = [y for y in sorted(set(chicken) & set(feed_abs), reverse=True)
               if feed_abs[y] and len([m for m in months if m[:4] == str(y)]) == 12]
        if yrs:
            anchor_year = yrs[0]
            live_value = chicken[anchor_year] / feed_abs[anchor_year]
            anchor_value = live_value / CARCASS_YIELD
            yr_mean = (sum(ratio[m] for m in months if m[:4] == str(anchor_year))
                       / 12)
            scale = anchor_value / yr_mean
            anchored = True

    out_series = [[m, round(ratio[m] * (scale or 1.0), 4),
                   round(meat[m], 2), round(feed[m], 2)] for m in months]
    meta = {
        "metric": "broiler parity — chicken-meat price / feed price",
        "construction": "Eurostat sts_inppd_m PL: PPI C1012 / PPI C1091",
        "columns": ["month", "parity", "meat_idx", "feed_idx"],
        "anchored": anchored,
        "anchor": ({"year": anchor_year, "kg_feed_per_kg_chicken":
                    round(anchor_value, 3),
                    "basis": f"carcass-equivalent: live-weight price / "
                             f"{CARCASS_YIELD} yield",
                    "live_weight_parity": round(live_value, 3),
                    "source": "Eurostat annual prices: live chickens 11510000 / "
                              "complete broiler feed 20624502, PLN"}
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
