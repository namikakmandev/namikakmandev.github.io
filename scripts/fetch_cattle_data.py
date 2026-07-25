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

def _agrifood_monthly(url):
    """EC agrifood weekly records -> {YYYY-MM: monthly mean}. Tolerant field parsing."""
    recs = json.loads(get(url).decode())
    monthly = defaultdict(list)
    for rec in recs:
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
    return {m: sum(v) / len(v) for m, v in monthly.items()}

def build_eu():
    # Young bulls R3 carcass price. API returns a 100x-scaled figure; normalise to EUR/100kg
    # (sanity anchor: EU young-bull R3 was ~EUR320/100kg in 2010).
    beef = _agrifood_monthly(
        "https://www.ec.europa.eu/agrifood/api/beef/prices"
        "?memberStateCodes=EU&categories=young%20bulls&qualities=R3"
        "&beginDate=01/01/2010&endDate=31/12/2026")
    if not beef:
        raise RuntimeError("EU beef API returned no parsable rows")
    scale = 100 if sum(beef.values()) / len(beef) > 3000 else 1
    beef = {m: v / scale for m, v in beef.items()}
    # Feed maize, all member states averaged as EU proxy (no EU aggregate on this endpoint).
    feed = {}
    for prod in ("Feed%20maize", "Maize", "Feed%20barley"):
        try:
            feed = _agrifood_monthly(
                "https://www.ec.europa.eu/agrifood/api/cereal/prices"
                f"?productCodes={prod}&beginDate=01/01/2010&endDate=31/12/2026")
        except Exception:
            feed = {}
        if feed:
            fscale = 100 if sum(feed.values()) / len(feed) > 2000 else 1
            feed = {m: v / fscale for m, v in feed.items()}
            break
    months = sorted(set(beef) & set(feed)) if feed else sorted(beef)
    rows = []
    for m in months:
        b = round(beef[m], 2)
        f = round(feed[m], 2) if feed else None
        rows.append([m, b, f, round(b / f, 4) if f else None])
    return {
        "source": "EC agri-food data portal: young bulls R3 EU avg (EUR/100kg) + feed grain MS avg (EUR/t), monthly means of weekly quotes",
        "columns": ["month", "beef_r3_eur_100kg", "feed_eur_t", "parity_beef_over_feed"],
        "rows": rows,
    }

def build_tr_discovery():
    """If EVDS_KEY is present, search TCMB EVDS for candidate TR cattle/feed series."""
    import os
    key = os.environ.get("EVDS_KEY", "").strip()
    if not key:
        raise RuntimeError("EVDS_KEY not set — skipping TR discovery")
    from evds import evdsAPI
    api = evdsAPI(key)
    hits = []
    kw = ("sığır", "sigir", "dana", "kırmızı et", "kirmizi et", "yem", "karkas", "canlı hayvan")
    try:
        mains = api.main_categories
        for _, mrow in mains.iterrows():
            name = str(mrow.get("TOPIC_TITLE_TR", ""))
            if not any(k in name.lower() for k in ("fiyat", "üfe", "ufe", "tarım", "tarim", "enflasyon")):
                continue
            try:
                subs = api.get_sub_categories(mrow["CATEGORY_ID"])
            except Exception:
                continue
            for _, srow in subs.iterrows():
                code = srow.get("DATAGROUP_CODE")
                try:
                    series = api.get_series(code)
                except Exception:
                    continue
                for _, row in series.iterrows():
                    nm = str(row.get("SERIE_NAME", ""))
                    if any(k in nm.lower() for k in kw):
                        hits.append({"code": row.get("SERIE_CODE"), "name": nm,
                                     "group": str(srow.get("DATAGROUP_NAME", ""))})
    except Exception as e:
        raise RuntimeError(f"EVDS discovery failed: {e}")
    if not hits:
        raise RuntimeError("EVDS discovery found no matching series")
    return {"source": "TCMB EVDS series discovery (keywords: sığır/dana/kırmızı et/yem/karkas)",
            "candidates": hits[:200]}

def build_merged():
    """Apples-to-apples file: per region, meat & feed indexed to 2015=100 + parity index."""
    def load(path):
        with open(path) as f:
            return json.load(f)
    def rebase(series):  # {m: v} -> 2015=100
        base = [v for m, v in series.items() if m.startswith("2015") and v]
        if not base:
            return {}
        b = sum(base) / len(base)
        return {m: round(v / b * 100, 2) for m, v in series.items() if v}
    out = {"base": "2015=100", "regions": {}}
    us = load("data/cattle-us.json")["rows"]
    meat = rebase({r[0]: r[1] for r in us if r[0] >= "2010"})
    feed = rebase({r[0]: r[2] for r in us if r[0] >= "2010"})
    out["regions"]["US"] = {
        "source": "FRED/BLS PPIs (slaughter cattle, corn)",
        "columns": ["month", "meat_idx", "feed_idx", "parity_idx"],
        "rows": [[m, meat[m], feed[m], round(meat[m] / feed[m], 4)]
                 for m in sorted(set(meat) & set(feed))]}
    eu = load("data/cattle-eu.json")["rows"]
    meat = rebase({r[0]: r[1] for r in eu})
    feed = rebase({r[0]: r[2] for r in eu if r[2]})
    if feed:
        out["regions"]["EU"] = {
            "source": "EC agrifood: young bull R3 carcass, feed grain",
            "columns": ["month", "meat_idx", "feed_idx", "parity_idx"],
            "rows": [[m, meat[m], feed[m], round(meat[m] / feed[m], 4)]
                     for m in sorted(set(meat) & set(feed))]}
    with open("data/cattle-parity.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    return out

def main():
    ok, fail = [], []
    for name, fn in [("data/cattle-us.json", build_us),
                     ("data/cattle-eu.json", build_eu),
                     ("data/tr-series-candidates.json", build_tr_discovery)]:
        try:
            obj = fn()
            with open(name, "w") as f:
                json.dump(obj, f, separators=(",", ":"))
            ok.append(f"{name} ({len(obj['rows'])} rows)")
        except Exception as e:  # noqa: BLE001 — report and continue
            fail.append(f"{name}: {type(e).__name__}: {e}")
    try:
        merged = build_merged()
        ok.append("data/cattle-parity.json (regions: " + ",".join(merged["regions"]) + ")")
    except Exception as e:  # noqa: BLE001
        fail.append(f"data/cattle-parity.json: {type(e).__name__}: {e}")
    print("OK:", "; ".join(ok) or "none")
    print("FAILED:", "; ".join(fail) or "none")
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
