#!/usr/bin/env python3
"""Balance-sheet anatomy, human vs animal pharma, from SEC 10-K filings.

Reads data/pharma-bs.json (EDGAR XBRL, FY-end instant values) and data/pharma-pnl.json
(for revenue scaling and the R&D% tie-in) and answers one question: what does each
balance sheet exist to protect — a pipeline (cash buffer + intangibles) or a plant
network (inventory + PP&E)?

The framing rule for anything published from this: NOT "how much cash they hoard".
A stock cannot fund a flow — R&D is paid from operating cash, and the pile is mostly
M&A capacity plus precautionary buffer. The defensible statement is the corporate-
finance one: R&D-intensive firms hold precautionary liquidity because a pipeline
cannot be collateralised and must never stop. Net cash (cash + ST investments − debt)
is the honest measure — gross cash flatters levered filers.

Rules of the house (same as analyse_pnl.py):
  - a company-year enters a ratio only if the needed fields are present that year;
    anything dropped or approximated is listed, never silently ignored
  - per-company figure = mean of its last 3 usable fiscal years
  - group figure = median across companies; Merck shown, pooled with neither group
  - ZTS/ELAN tag no short-term-investments line: treated as "not reported", cash-only
    liquidity is used and the flag travels with the company row
  - Phibro's debt tags stop at FY2024 → its net-cash uses FY2023–24 only, flagged

Writes data/pharma-bs-derived.json.  Run: python scripts/analyse_bs.py
"""
import json, os
from statistics import mean, median

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUMAN = ["PFIZER", "LILLY", "ABBVIE", "BMS"]
ANIMAL = ["ZOETIS", "ELANCO", "PHIBRO"]
MIXED = ["MERCK"]


def series(row, field):
    return row.get(field) or {}


def main():
    bs = json.load(open(os.path.join(ROOT, "data", "pharma-bs.json")))["series"]
    pnl = json.load(open(os.path.join(ROOT, "data", "pharma-pnl.json")))["series"]
    rnd = json.load(open(os.path.join(ROOT, "data", "pharma-pnl-derived.json")))["companies"]

    out = {"method": ("FY-end instant values from 10-K XBRL. Per company: mean of the "
                      "last 3 fiscal years where the numerator fields are tagged; a "
                      "year missing a field is skipped for that ratio only and listed. "
                      "Liquidity = cash (+ short-term investments where reported). "
                      "Net cash = liquidity − (long-term + current debt). Scaled by "
                      "revenue (same FY, from pharma-pnl.json) and by total assets. "
                      "Group figure: median. Global consolidated, fiscal year-ends "
                      "differ (Phibro June; others Dec/Nov)."),
           "companies": {}, "flags": {}}

    for label, row in bs.items():
        if not isinstance(row, dict):
            continue
        rev = series(pnl.get(label, {}), "revenue")
        cash, sti = series(row, "cash"), series(row, "sti")
        dlt, dst = series(row, "debt_lt"), series(row, "debt_st")
        inv, ppe = series(row, "inventory"), series(row, "ppe")
        gw, intan = series(row, "goodwill"), series(row, "intangibles")
        assets = series(row, "assets")
        flags = []
        if not sti:
            flags.append("no short-term-investments line tagged; liquidity is cash only")

        # a year is usable for net cash when cash, debt and revenue all exist
        nc_years = sorted(set(cash) & set(dlt) & set(rev), key=int)[-3:]
        # asset-anatomy years need the asset-side fields
        an_years = sorted(set(assets) & set(inv) & set(ppe) & set(gw) & set(intan),
                          key=int)[-3:]
        if not nc_years or not an_years:
            out["flags"][label] = flags + ["insufficient overlapping years — dropped"]
            continue
        if len(nc_years) < 3:
            flags.append(f"net-cash window is {nc_years} (debt tags missing elsewhere)")

        def ncash(y):
            return (cash[y] + sti.get(y, 0)) - (dlt[y] + dst.get(y, 0))
        liq = mean(cash[y] + sti.get(y, 0) for y in nc_years)
        debt = mean(dlt[y] + dst.get(y, 0) for y in nc_years)
        nc = mean(ncash(y) for y in nc_years)
        rv = mean(rev[y] for y in nc_years)
        at = mean(assets[y] for y in an_years)

        out["companies"][label] = {
            "netcash_fys": nc_years, "anatomy_fys": an_years,
            "liquidity_busd": round(liq / 1e9, 1),
            "gross_debt_busd": round(debt / 1e9, 1),
            "net_cash_busd": round(nc / 1e9, 1),
            "net_cash_pct_rev": round(nc / rv * 100, 1),
            "liquidity_pct_assets": round(liq / at * 100, 1),
            "inventory_pct_assets": round(mean(inv[y] for y in an_years) / at * 100, 1),
            "ppe_pct_assets": round(mean(ppe[y] for y in an_years) / at * 100, 1),
            "gw_intan_pct_assets": round(
                mean(gw[y] + intan[y] for y in an_years) / at * 100, 1),
            "rnd_pct_rev": rnd.get(label, {}).get("rnd_pct"),
            "concepts": {f: row.get(f + "_concept")
                         for f in ("cash", "sti", "debt_lt", "debt_st", "inventory",
                                   "ppe", "goodwill", "intangibles", "assets")},
            "flags": flags,
        }

    fields = ("net_cash_pct_rev", "liquidity_pct_assets", "inventory_pct_assets",
              "ppe_pct_assets", "gw_intan_pct_assets")

    def group(labels):
        rows = [out["companies"][l] for l in labels if l in out["companies"]]
        if not rows:
            return None
        return {"n": len(rows),
                **{f: round(median(r[f] for r in rows), 1) for f in fields}}

    out["groups"] = {"human_pure": group(HUMAN), "animal": group(ANIMAL),
                     "mixed_shown_not_pooled": group(MIXED)}

    # R&D vs liquidity, ordered pairs only — n=7 is an illustration, not a regression
    out["rnd_vs_liquidity"] = sorted(
        ({"company": l, "rnd_pct_rev": c["rnd_pct_rev"],
          "net_cash_pct_rev": c["net_cash_pct_rev"],
          "liquidity_pct_assets": c["liquidity_pct_assets"]}
         for l, c in out["companies"].items() if c["rnd_pct_rev"] is not None),
        key=lambda r: -r["rnd_pct_rev"])

    json.dump(out, open(os.path.join(ROOT, "data", "pharma-bs-derived.json"), "w"),
              separators=(",", ":"), ensure_ascii=False)

    hdr = (f"{'company':8s} {'liq $B':>7s} {'debt $B':>8s} {'net $B':>7s} {'net%rev':>8s}"
           f" {'liq%A':>6s} {'inv%A':>6s} {'ppe%A':>6s} {'gwI%A':>6s} {'R&D%':>5s}")
    print(hdr)
    for g, labels in (("HUMAN", HUMAN), ("ANIMAL", ANIMAL), ("MIXED", MIXED)):
        for l in labels:
            c = out["companies"].get(l)
            if not c:
                print(f"{l:8s} DROPPED: {out['flags'].get(l)}")
                continue
            print(f"{l:8s} {c['liquidity_busd']:7.1f} {c['gross_debt_busd']:8.1f} "
                  f"{c['net_cash_busd']:7.1f} {c['net_cash_pct_rev']:8.1f} "
                  f"{c['liquidity_pct_assets']:6.1f} {c['inventory_pct_assets']:6.1f} "
                  f"{c['ppe_pct_assets']:6.1f} {c['gw_intan_pct_assets']:6.1f} "
                  f"{c['rnd_pct_rev'] if c['rnd_pct_rev'] is not None else float('nan'):5.1f}"
                  + ("  <" + "; ".join(c["flags"]) if c["flags"] else ""))
        gg = out["groups"]["human_pure" if g == "HUMAN" else
                           "animal" if g == "ANIMAL" else "mixed_shown_not_pooled"]
        if gg:
            print(f"  {g} median{'':>14s} {gg['net_cash_pct_rev']:8.1f} "
                  f"{gg['liquidity_pct_assets']:6.1f} {gg['inventory_pct_assets']:6.1f} "
                  f"{gg['ppe_pct_assets']:6.1f} {gg['gw_intan_pct_assets']:6.1f}")
        print()
    print("[write] data/pharma-bs-derived.json")


if __name__ == "__main__":
    main()
