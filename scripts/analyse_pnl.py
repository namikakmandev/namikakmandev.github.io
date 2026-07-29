#!/usr/bin/env python3
"""Cost anatomy, human vs animal pharma, from SEC 10-K filings.

Reads data/pharma-pnl.json (EDGAR XBRL, annual FY values) and answers one question:
what share of a revenue dollar goes to COGS, R&D and SG&A — and how differently do
human and animal pharma companies answer it?

Rules of the house:
  - a company-year enters only if revenue, COGS, R&D and SG&A are ALL present;
    anything dropped is listed, never silently ignored
  - per-company figure = mean of its last 3 complete fiscal years (one-off years
    smooth out; a single year is a headline risk)
  - group figure = median across companies (Pfizer's COVID swings should not drag
    a mean around)
  - Merck is reported but EXCLUDED from the human group median: ~9% of its revenue
    is animal health, so it is not a pure-human filer

Writes data/pharma-pnl-derived.json.  Run: python scripts/analyse_pnl.py
"""
import json, os
from statistics import mean, median

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUMAN = ["PFIZER", "LILLY", "ABBVIE", "BMS"]          # pure human filers
ANIMAL = ["ZOETIS", "ELANCO", "PHIBRO"]
MIXED = ["MERCK"]                                     # shown, not pooled


def main():
    src = json.load(open(os.path.join(ROOT, "data", "pharma-pnl.json")))
    data = src["series"] if "series" in src else src

    out = {"method": ("Per company: mean of the last 3 fiscal years where revenue, "
                      "COGS, R&D and SG&A are all tagged in the 10-K. Group figure: "
                      "median across companies. Global consolidated USD — not US-only. "
                      "COGS is not the ingredient: no filer splits API out of COGS."),
           "companies": {}, "dropped": {}}

    for label, row in data.items():
        if not isinstance(row, dict) or "revenue" not in row:
            out["dropped"][label] = "no revenue concept found"
            continue
        years = sorted(row["revenue"], key=int)
        complete = [y for y in years
                    if all(f in row and y in row[f] for f in ("cogs", "rnd", "sga"))]
        missing = [y for y in years[-5:] if y not in complete]
        use = complete[-3:]
        if not use:
            out["dropped"][label] = f"no complete FY rows (checked {years[-5:]})"
            continue
        ratios = {f: mean(row[f][y] / row["revenue"][y] for y in use) * 100
                  for f in ("cogs", "rnd", "sga")}
        rev_b = mean(row["revenue"][y] for y in use) / 1e9
        out["companies"][label] = {
            "fiscal_years_used": use,
            "avg_revenue_busd": round(rev_b, 1),
            "cogs_pct": round(ratios["cogs"], 1),
            "rnd_pct": round(ratios["rnd"], 1),
            "sga_pct": round(ratios["sga"], 1),
            "concepts": {f: row.get(f + "_concept") for f in ("revenue", "cogs", "rnd", "sga")},
            "incomplete_recent_years": missing,
        }

    def group(labels):
        rows = [out["companies"][l] for l in labels if l in out["companies"]]
        if not rows:
            return None
        return {"n": len(rows),
                "cogs_pct": round(median(r["cogs_pct"] for r in rows), 1),
                "rnd_pct": round(median(r["rnd_pct"] for r in rows), 1),
                "sga_pct": round(median(r["sga_pct"] for r in rows), 1)}

    out["groups"] = {"human_pure": group(HUMAN), "animal": group(ANIMAL),
                     "mixed_shown_not_pooled": group(MIXED)}

    json.dump(out, open(os.path.join(ROOT, "data", "pharma-pnl-derived.json"), "w"),
              separators=(",", ":"), ensure_ascii=False)

    print(f"{'company':10s} {'FYs':16s} {'rev $B':>7s} {'COGS%':>7s} {'R&D%':>6s} {'SG&A%':>7s}")
    for g, labels in (("HUMAN", HUMAN), ("ANIMAL", ANIMAL), ("MIXED", MIXED)):
        for l in labels:
            c = out["companies"].get(l)
            if not c:
                print(f"{l:10s} DROPPED: {out['dropped'].get(l)}")
                continue
            print(f"{l:10s} {str(c['fiscal_years_used']):16s} {c['avg_revenue_busd']:7.1f} "
                  f"{c['cogs_pct']:7.1f} {c['rnd_pct']:6.1f} {c['sga_pct']:7.1f}")
        gg = out["groups"]["human_pure" if g == "HUMAN" else
                           "animal" if g == "ANIMAL" else "mixed_shown_not_pooled"]
        if gg:
            print(f"{'  ' + g + ' median':10s} {'':16s} {'':7s} {gg['cogs_pct']:7.1f} "
                  f"{gg['rnd_pct']:6.1f} {gg['sga_pct']:7.1f}")
        print()
    if out["dropped"]:
        print("dropped:", out["dropped"])
    print("[write] data/pharma-pnl-derived.json")


if __name__ == "__main__":
    main()
