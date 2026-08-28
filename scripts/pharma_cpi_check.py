#!/usr/bin/env python3
"""Do scraped pet-pharma prices outrun consumer inflation? Matched test.

Compares each scraped SKU-venue price series against the SAME COUNTRY's
official price index over the SAME WINDOW. Anything else — a global drug
median against a single country's CPI, or against a period the drug series
does not cover — is not a comparison.

Benchmarks (both already committed in this repo):
  EU  Eurostat HICP monthly index, 2015=100 (data/vet-cpi-eu.json)
      CP00   all-items
      CP0934 pets and related products   <- includes pet medicines
      CP0935 veterinary and other services for pets
  US  BLS via FRED (data/vet-cpi-us.json)
      CPIAUCNS      all-items, US city average, NSA
      CUUR0000SS62031  pet services including veterinary, NSA

Scope limits, stated rather than hidden:
  * Only series with >=5 observations spanning >=2 years are tested.
  * Only the US and the Netherlands can be tested at all: the UK and
    Australia are not in either CPI file, and Slovakia's HICP ends before
    its drug series does.
  * A ratio is reported alongside the percentage-point gap because a ratio
    inflates when the denominator is small; the gap is the safer figure.
  * The 24 series are NOT 24 independent facts — several share a venue and
    a product. No p-value is computed here, and none should be quoted.
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_OBS, MIN_SPAN_Y, MIN_CPI_SPAN_Y = 5, 2.0, 1.5

obs = json.loads((ROOT / "data/pharma-prices.json").read_text())
VEN = obs["meta"]["venues"]
EU = json.loads((ROOT / "data/vet-cpi-eu.json").read_text())["series"]
US = json.loads((ROOT / "data/vet-cpi-us.json").read_text())["series"]
US_MAP = {"CP00": "cpi_nsa", "CP0934": "pet_svcs_nsa", "CP0935": "pet_svcs_nsa"}


def yearfrac(d):
    return int(d[:4]) + int(d[5:7]) / 12


def cagr(a, b, years):
    return ((b / a) ** (1 / years) - 1) * 100


def cpi_cagr(cc, code, d0, d1):
    """Annualised drift of one CPI series between two dates, same country."""
    s = US.get(US_MAP[code]) if cc == "US" else EU.get(f"{cc}|{code}")
    if not s:
        return None
    keys = sorted(k for k in s if s[k] is not None)
    a = [k for k in keys if k <= d0[:7]]
    b = [k for k in keys if k <= d1[:7]]
    if not a or not b or a[-1] == b[-1]:
        return None
    years = yearfrac(b[-1] + "-01") - yearfrac(a[-1] + "-01")
    if years < MIN_CPI_SPAN_Y:
        return None
    return cagr(s[a[-1]], s[b[-1]], years)


def main():
    series = defaultdict(list)
    for o in obs["observations"]:
        series[(o["sku"], o["venue"])].append((o["d"], o["unit"]))

    rows = []
    for (sku, ven), pts in series.items():
        pts.sort()
        if len(pts) < MIN_OBS:
            continue
        span = yearfrac(pts[-1][0]) - yearfrac(pts[0][0])
        if span < MIN_SPAN_Y:
            continue
        cc = VEN[ven]["country"]
        rows.append({
            "cc": cc, "sku": sku, "venue": ven, "span": span,
            "drug": cagr(pts[0][1], pts[-1][1], span),
            "all": cpi_cagr(cc, "CP00", pts[0][0], pts[-1][0]),
            "petprod": cpi_cagr(cc, "CP0934", pts[0][0], pts[-1][0]),
            "vetsvc": cpi_cagr(cc, "CP0935", pts[0][0], pts[-1][0]),
        })

    fmt = lambda v: f"{v:8.1f}" if v is not None else "     n/a"
    print(f"{'cc':3s} {'sku':24s} {'drug':>8s} {'CPI all':>8s} {'petprod':>8s} {'vetsvc':>8s}  gap")
    for r in sorted(rows, key=lambda r: (r["cc"], r["sku"])):
        gap = f"{r['drug'] - r['all']:+6.1f}pp" if r["all"] else "      —"
        print(f"{r['cc']:3s} {r['sku']:24s} {r['drug']:8.1f} {fmt(r['all'])}"
              f" {fmt(r['petprod'])} {fmt(r['vetsvc'])}  {gap}")

    matched = [r for r in rows if r["all"] and r["all"] > 0.5]
    print(f"\n{len(rows)} series tested; {len(matched)} have a matched-country CPI")
    print(f"median drug drift, all series: {statistics.median(r['drug'] for r in rows):+.1f}%/yr")
    for cc in sorted({r["cc"] for r in matched}):
        g = [r for r in matched if r["cc"] == cc]
        d, c = statistics.median(r["drug"] for r in g), statistics.median(r["all"] for r in g)
        print(f"  {cc}: drugs {d:+.1f}%/yr vs all-items CPI {c:+.1f}%/yr"
              f"  = {d / c:.1f}x, gap {d - c:+.1f}pp  (n={len(g)})")
    print(f"median ratio across matched series: "
          f"{statistics.median(r['drug'] / r['all'] for r in matched):.1f}x")
    print(f"median gap across matched series:   "
          f"{statistics.median(r['drug'] - r['all'] for r in matched):+.1f}pp/yr")


if __name__ == "__main__":
    main()
