#!/usr/bin/env python3
"""Pharma share of GDP — the core table behind the study.

share_gdp  = C21 gross value added / GDP at market prices
share_gva  = C21 gross value added / total gross value added   (like-for-like)
share_manu = C21 gross value added / manufacturing gross value added

All three come from the same Eurostat vintage, in national currency, so no
exchange rate enters the ratio.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pharma_share_audit import NAMES, AGGREGATES, load  # noqa: E402


def shares():
    pharma, gdp = load("pharma-gva.json"), load("gdp-total.json")
    gva, manu = load("gva-total.json"), load("manuf-gva.json")
    out = {}
    for geo, p in pharma.items():
        if geo in AGGREGATES:
            continue
        rows = {}
        for y, v in p.items():
            d_gdp = gdp.get(geo, {}).get(y)
            d_gva = gva.get(geo, {}).get(y)
            d_man = manu.get(geo, {}).get(y)
            if not d_gdp:
                continue
            rows[int(y)] = {
                "pharma_gva": v,
                "share_gdp": 100 * v / d_gdp,
                "share_gva": 100 * v / d_gva if d_gva else None,
                "share_manu": 100 * v / d_man if d_man else None,
            }
        if rows:
            out[geo] = rows
    return out


def main():
    s = shares()
    eur = load("pharma-gva-eur.json")

    # ---- latest available year per country, ranked
    latest = []
    for geo, rows in s.items():
        y = max(rows)
        first = min(rows)
        latest.append((geo, y, rows[y], first, rows[first]))
    latest.sort(key=lambda r: -r[2]["share_gdp"])

    print("PHARMA SHARE OF GDP — latest available year, ranked")
    print(f"{'':<4}{'country':<24}{'yr':<6}{'%GDP':>7}{'%GVA':>7}{'%manuf':>8}"
          f"{'  first yr':<10}{'%GDP then':>10}{'  change':>9}")
    print("-" * 90)
    for geo, y, r, fy, fr in latest:
        chg = r["share_gdp"] - fr["share_gdp"]
        man = f"{r['share_manu']:.1f}" if r["share_manu"] else "  -"
        gv = f"{r['share_gva']:.2f}" if r["share_gva"] else "  -"
        print(f"{geo:<4}{NAMES.get(geo, geo):<24}{y:<6}{r['share_gdp']:>7.2f}{gv:>7}"
              f"{man:>8}{fy:>8}  {fr['share_gdp']:>8.2f}{chg:>+9.2f}")

    # ---- trajectory of the countries that matter, on a common grid
    print("\n\nTRAJECTORY — share of GDP, %")
    focus = [g for g, *_ in latest[:10]]
    years = [1995, 2000, 2005, 2010, 2014, 2019, 2023]
    print(f"{'':<4}{'country':<24}" + "".join(f"{y:>8}" for y in years))
    print("-" * 84)
    for geo in focus:
        cells = ""
        for y in years:
            v = s[geo].get(y)
            cells += f"{v['share_gdp']:>8.2f}" if v else f"{'·':>8}"
        print(f"{geo:<4}{NAMES.get(geo, geo):<24}{cells}")

    # ---- absolute size, latest common year
    print("\n\nABSOLUTE PHARMA GVA (million EUR), latest available")
    sz = []
    for geo, rows in eur.items():
        if geo in AGGREGATES:
            continue
        y = max(int(k) for k in rows)
        sz.append((geo, y, rows[str(y)]))
    sz.sort(key=lambda r: -r[2])
    for geo, y, v in sz[:15]:
        print(f"{geo:<4}{NAMES.get(geo, geo):<24}{y:<6}{v:>12,.0f}")

    json.dump(
        {"note": "C21 gross value added as % of GDP / total GVA / manufacturing GVA. "
                 "Eurostat nama_10_a64 + nama_10_gdp, current prices, national currency.",
         "shares": {g: {str(y): r for y, r in rows.items()} for g, rows in s.items()}},
        open(os.path.join(ROOT, "data", "pharma-share.json"), "w"),
        separators=(",", ":"))


if __name__ == "__main__":
    main()
