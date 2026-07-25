#!/usr/bin/env python3
"""Fetch cattle vs feed price series for the cattle-parity story.

Runs inside GitHub Actions (open internet). Writes JSON files under data/:
  data/cattle-us.json  — FRED monthly PPIs since 1926: slaughter cattle (WPU0131)
                         and corn (WPU012202) + parity ratio (cattle/corn, indexed)
  data/cattle-eu.json  — EU young-bull R3 carcass price (weekly -> monthly avg)
                         and EU feed maize price, from the EC agrifood API (best effort)

Each source is independent: a failure in one does not block the others.
"""
import csv, io, json, sys, urllib.request
from collections import defaultdict

UA = {"User-Agent": "namikakmandev-cattle-story/1.0 (github actions)"}

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fred_series(series_id):
    """FRED keyless CSV endpoint -> {YYYY-MM: value}"""
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}").decode()
    out = {}
    for row in csv.DictReader(io.StringIO(raw)):
        date = (row.get("DATE") or row.get("observation_date") or "").strip()
        val = (row.get(series_id) or "").strip()
        if len(date) >= 7 and val not in ("", "."):
            out[date[:7]] = float(val)
    return out

def build_us():
    cattle = fred_series("WPU0131")     # PPI slaughter cattle, monthly, 1926->
    corn = fred_series("WPU012202")     # PPI corn, monthly
    months = sorted(set(cattle) & set(corn))
    rows = [[m, round(cattle[m], 2), round(corn[m], 2),
             round(cattle[m] / corn[m], 4)] for m in months]
    return {
        "source": "FRED/BLS producer price indexes: WPU0131 (slaughter cattle), WPU012202 (corn)",
        "columns": ["month", "cattle_ppi", "corn_ppi", "parity_cattle_over_corn"],
        "rows": rows,
    }

def build_eu():
    # EC agrifood portal open API. Young bulls R3 carcass price, weekly, EU aggregate.
    beef_url = ("https://www.ec.europa.eu/agrifood/api/beef/prices"
                "?memberStateCodes=EU&categories=young%20bulls&qualities=R3"
                "&beginDate=01/01/2010&endDate=31/12/2026")
    beef = json.loads(get(beef_url).decode())
    monthly = defaultdict(list)
    for rec in beef:
        # date like 21/03/2022 ; price like "€483,15" or number, per 100 kg
        d = rec.get("beginDate") or rec.get("referencePeriod") or ""
        p = rec.get("price") or rec.get("unitPrice")
        if not d or p is None:
            continue
        if isinstance(p, str):
            p = p.replace("€", "").replace(".", "").replace(",", ".").strip()
        try:
            p = float(p)
        except ValueError:
            continue
        dd = d.split("/")
        if len(dd) == 3:
            monthly[f"{dd[2]}-{dd[1]}"].append(p)
    rows = [[m, round(sum(v) / len(v), 2)] for m, v in sorted(monthly.items())]
    if not rows:
        raise RuntimeError("EU beef API returned no parsable rows")
    return {
        "source": "EC agri-food data portal: beef carcass prices, young bulls R3, EU average, EUR/100kg (monthly mean of weekly quotes)",
        "columns": ["month", "beef_r3_eur_100kg"],
        "rows": rows,
    }

def main():
    ok, fail = [], []
    for name, fn in [("data/cattle-us.json", build_us), ("data/cattle-eu.json", build_eu)]:
        try:
            obj = fn()
            with open(name, "w") as f:
                json.dump(obj, f, separators=(",", ":"))
            ok.append(f"{name} ({len(obj['rows'])} rows)")
        except Exception as e:  # noqa: BLE001 — report and continue
            fail.append(f"{name}: {type(e).__name__}: {e}")
    print("OK:", "; ".join(ok) or "none")
    print("FAILED:", "; ".join(fail) or "none")
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
