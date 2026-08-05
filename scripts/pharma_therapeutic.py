#!/usr/bin/env python3
"""Therapeutic-class detail: what the leading producers actually make.

HS 4-digit chapters ("biologics", "finished dose") are customs categories, not
medicines. The 6-digit level names the product:

  2937.19  polypeptide / protein hormones, bulk   — the GLP-1 and insulin-analogue
                                                    active-substance class
  3002.41  vaccines for human medicine
  3002.15  immunological products in doses        — therapeutic antibodies
  3002.12  antisera and blood fractions           — plasma products
  3004.31  medicaments containing insulin
  3004.39  medicaments containing other hormones  — GLP-1 in finished form
  3004.90  other medicaments                      — small molecules, generics

Denmark withholds 3004.31, 3004.39 and 3004.90 (and most partner detail):
its pharmaceutical exports are concentrated in too few firms to publish. That
suppression is itself a finding and is carried through to the output as an
explicit "not published" residual rather than being silently dropped.

Writes data/pharma-therapeutic.json.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)["series"]


CLASSES = [
    ("293719", "Peptide hormones (bulk)"),
    ("300215", "Antibodies / immunological"),
    ("300241", "Vaccines"),
    ("300212", "Blood products"),
    ("300431", "Insulin medicines"),
    ("300439", "Other hormone medicines"),
    ("300490", "Other medicines"),
]
HS4 = ["3002", "3004", "2937"]
COUNTRY = {"IE": "Ireland", "BE": "Belgium", "DE": "Germany", "NL": "Netherlands",
           "IT": "Italy", "FR": "France", "DK": "Denmark"}
YEAR = "2024"


def main():
    hs6 = load("hs6-check.json")
    hs4 = load("pharma-exports.json")
    dest = load("pharma-dest.json")
    trend = load("pharma-hs6-trend.json")

    out = {"note": "Exports to world, EUR, 2024, Eurostat Comext DS-045409. "
                   "Classes are HS 6-digit; 'not published' is the residual "
                   "between the HS4 chapter total and the published detail.",
           "year": YEAR, "countries": {}, "trends": {}, "destinations": {}}

    for geo, name in COUNTRY.items():
        total = sum(hs4.get(f"{geo}|{p}", {}).get(YEAR, 0) for p in HS4)
        parts, named = {}, 0.0
        for code, label in CLASSES:
            v = hs6.get(f"{geo}|{code}", {}).get(YEAR, 0)
            if v:
                parts[label] = v / 1e9
                named += v
        residual = max(0.0, (total - named) / 1e9)
        out["countries"][geo] = {
            "name": name, "total_bn": total / 1e9,
            "classes": parts, "not_published_bn": residual,
            "suppressed": geo == "DK",
        }

    # trajectory of the classes that moved
    for geo, code in (("IE", "293719"), ("BE", "300241"), ("IE", "300215"),
                      ("IT", "300439"), ("DK", "293719"), ("DE", "300490")):
        s = trend.get(f"{geo}|{code}", {})
        if s:
            out["trends"][f"{geo}|{code}"] = {y: v / 1e9 for y, v in sorted(s.items())}

    # destination markets
    for geo in ("DK", "IE", "BE"):
        tot = sum(dest.get(f"{geo}|{p}|WORLD", {}).get(YEAR, 0) for p in HS4)
        agg = {}
        for key, series in dest.items():
            r, _, pa = key.split("|")
            if r == geo and pa != "WORLD":
                agg[pa] = agg.get(pa, 0) + series.get(YEAR, 0)
        top = sorted(agg.items(), key=lambda kv: -kv[1])[:6]
        out["destinations"][geo] = {
            "total_bn": tot / 1e9,
            "attributed_pct": 100 * sum(agg.values()) / tot if tot else 0,
            "top": [{"partner": p, "eur_bn": v / 1e9, "pct": 100 * v / tot} for p, v in top],
        }

    json.dump(out, open(os.path.join(ROOT, "data", "pharma-therapeutic.json"), "w"),
              separators=(",", ":"))

    for geo, d in sorted(out["countries"].items(), key=lambda kv: -kv[1]["total_bn"]):
        print(f"{d['name']:<12} €{d['total_bn']:>6.1f}bn  " +
              "  ".join(f"{k.split()[0]}={v:.1f}" for k, v in
                        sorted(d["classes"].items(), key=lambda kv: -kv[1])[:3]) +
              (f"   [not published €{d['not_published_bn']:.1f}bn]"
               if d["not_published_bn"] > 1 else ""))
    print()
    for geo, d in out["destinations"].items():
        t = ", ".join(f"{x['partner']} {x['pct']:.0f}%" for x in d["top"][:3])
        print(f"{geo}: {d['attributed_pct']:.0f}% of exports attributed — {t}")
    print("\nwrote data/pharma-therapeutic.json")


if __name__ == "__main__":
    main()
