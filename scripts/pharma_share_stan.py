#!/usr/bin/env python3
"""Pharma share of total value added from OECD STAN — the non-European leg.

share_gva = ISIC C21 value added / total-economy value added, both from
DSD_STAN@DF_STAN_2025 at current prices in national currency, so the ratio is
internally consistent and carries no exchange rate.

Validation (2026-08): of 11 countries present in both STAN and the Eurostat
set, 10 agree to within ±0.15 pp at matched years. Switzerland does not
(STAN 4.75 vs Eurostat 6.45 in 2022) — the merge below therefore prefers
Eurostat for European countries and uses STAN only where Eurostat is silent
or truncated: the non-OECD-Europe world, the UK, Türkiye and Ireland.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAMES3 = {
    "USA": "United States", "JPN": "Japan", "KOR": "South Korea",
    "CAN": "Canada", "MEX": "Mexico", "AUS": "Australia",
    "NZL": "New Zealand", "CHL": "Chile", "COL": "Colombia",
    "CRI": "Costa Rica", "ISR": "Israel", "GBR": "United Kingdom",
    "TUR": "Türkiye", "IRL": "Ireland", "JPN": "Japan",
}
# countries the merged dataset takes from STAN (everything Eurostat lacks).
# NZL excluded: its C21 series drops from ~299 to 11 MNZD between 2017 and
# 2018 — a collection break, not an industry collapse.
TAKE = ["USA", "JPN", "KOR", "CAN", "MEX", "AUS", "CHL", "COL",
        "CRI", "ISR", "GBR", "TUR", "IRL"]


def load(name):
    with open(os.path.join(ROOT, "data", name)) as f:
        return json.load(f)["series"]


# observations that are collection artefacts, not economics: Colombia's C21
# reads 4,315bn COP (2019) → 193bn (2020) → 1,222bn (2021) → 5,422bn (2022).
DROP = {("COL", "2020"), ("COL", "2021")}


def shares():
    p, t = load("stan-pharma.json"), load("stan-total.json")
    out = {}
    for geo in TAKE:
        if geo not in p or geo not in t:
            continue
        rows = {}
        for y in sorted(set(p[geo]) & set(t[geo])):
            if (geo, y) in DROP:
                continue
            v = p[geo][y]
            if v <= 0:      # suppressed or meaningless
                continue
            rows[int(y)] = {"pharma_va": v,
                            "share_gva": 100 * v / t[geo][y]}
        if rows:
            out[geo] = rows
    return out


def main():
    s = shares()
    print("STAN pharma share of total value added — latest year each")
    print(f"{'geo':<5}{'country':<16}{'span':<12}{'latest':>7}{'share':>8}")
    for geo, rows in sorted(s.items(), key=lambda kv: -kv[1][max(kv[1])]["share_gva"]):
        y0, y1 = min(rows), max(rows)
        print(f"{geo:<5}{NAMES3.get(geo, geo):<16}{y0}-{y1:<6}{y1:>6}"
              f"{rows[y1]['share_gva']:>7.2f}%")
    json.dump(
        {"note": "ISIC C21 value added as % of total-economy value added. "
                 "OECD STAN DF_STAN_2025, current prices, national currency. "
                 "Only countries the Eurostat set lacks or truncates.",
         "shares": {g: {str(y): r for y, r in rows.items()}
                    for g, rows in s.items()}},
        open(os.path.join(ROOT, "data", "pharma-share-stan.json"), "w"),
        separators=(",", ":"))
    print("wrote data/pharma-share-stan.json")


if __name__ == "__main__":
    main()
