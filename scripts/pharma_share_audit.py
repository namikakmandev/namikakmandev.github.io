#!/usr/bin/env python3
"""Coverage + sanity audit for the pharma-share-of-GDP study.

Runs before any chart is drawn. Answers, per country: does C21 gross value
added exist, over which years, and does the GDP denominator cover the same
span? Anything that fails here is a country the study cannot claim to cover.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)["series"]


NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CH": "Switzerland",
    "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark",
    "EE": "Estonia", "EL": "Greece", "ES": "Spain", "FI": "Finland",
    "FR": "France", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland",
    "IS": "Iceland", "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "MT": "Malta", "NL": "Netherlands", "NO": "Norway",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SE": "Sweden",
    "SI": "Slovenia", "SK": "Slovakia", "TR": "Türkiye", "RS": "Serbia",
    "MK": "North Macedonia", "AL": "Albania", "BA": "Bosnia and Herzegovina",
    "ME": "Montenegro", "XK": "Kosovo", "UA": "Ukraine", "MD": "Moldova",
    "LI": "Liechtenstein", "EU27_2020": "European Union (27)",
}
AGGREGATES = {"EU27_2020", "EA", "EA12", "EA19", "EA20", "EA21"}


def span(d):
    ys = sorted(int(y) for y in d)
    return (ys[0], ys[-1], len(ys)) if ys else (None, None, 0)


def main():
    pharma = load("pharma-gva.json")
    gdp = load("gdp-total.json")
    gva = load("gva-total.json")
    manu = load("manuf-gva.json")

    rows = []
    for geo, series in pharma.items():
        p0, p1, pn = span(series)
        g = gdp.get(geo, {})
        g0, g1, gn = span(g)
        overlap = sorted(set(series) & set(g), key=int)
        # gaps inside the pharma series
        ys = sorted(int(y) for y in series)
        gaps = [y for y in range(ys[0], ys[-1] + 1) if str(y) not in series] if ys else []
        rows.append({
            "geo": geo, "name": NAMES.get(geo, geo),
            "pharma": (p0, p1, pn), "gdp": (g0, g1, gn),
            "overlap": (int(overlap[0]), int(overlap[-1]), len(overlap)) if overlap else None,
            "gaps": gaps,
            "has_gva": geo in gva, "has_manu": geo in manu,
        })

    rows.sort(key=lambda r: (-(r["overlap"][2] if r["overlap"] else 0), r["geo"]))
    print(f"{'geo':<4} {'country':<26} {'C21 GVA':<16} {'GDP':<16} {'usable overlap':<18} gaps")
    print("-" * 104)
    for r in rows:
        p = "%s-%s (%d)" % r["pharma"]
        g = "%s-%s (%d)" % r["gdp"]
        o = "%s-%s (%d)" % r["overlap"] if r["overlap"] else "NONE"
        flag = "" if r["overlap"] and r["overlap"][2] >= 20 else "   <-- under 20y"
        gp = ",".join(str(x) for x in r["gaps"]) if r["gaps"] else "-"
        print(f"{r['geo']:<4} {r['name']:<26} {p:<16} {g:<16} {o:<18} {gp}{flag}")

    usable20 = [r for r in rows
                if r["overlap"] and r["overlap"][2] >= 20 and r["geo"] not in AGGREGATES]
    print(f"\ncountries with >= 20 usable years: {len(usable20)}")
    print("missing GVA denominator:", [r["geo"] for r in rows if not r["has_gva"]])
    print("missing manufacturing denominator:", [r["geo"] for r in rows if not r["has_manu"]])


if __name__ == "__main__":
    main()
