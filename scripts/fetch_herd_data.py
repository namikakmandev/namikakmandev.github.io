#!/usr/bin/env python3
"""Fetch cattle HEAD COUNT (herd inventory) for the parity story.

Runs inside GitHub Actions (open internet). The point is to test — not assert —
the mechanism the study claims: feed gets expensive -> herds are liquidated ->
some years later beef is scarce and parity peaks.

Writes:
  data/herd-cattle.json   — annual cattle stocks (head) for US / EU / TR
  data/herd-report.json   — what each source returned, so failures are visible

Every source is tried independently; one failing does not block the others.
"""
import csv, io, json, sys, urllib.request
from collections import defaultdict

UA = {"User-Agent": "namikakmandev-cattle-story/1.0 (github actions)"}
report = {}


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def try_source(name, fn):
    try:
        out = fn()
        n = len(out) if out else 0
        report[name] = {"ok": bool(out), "points": n,
                        "first": min(out) if out else None,
                        "last": max(out) if out else None}
        print(f"[ok]   {name}: {n} points {min(out) if out else '-'}..{max(out) if out else '-'}")
        return out or {}
    except Exception as e:  # noqa: BLE001 - we want the reason in the report
        report[name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print(f"[fail] {name}: {type(e).__name__}: {e}")
        return {}


# ---------------------------------------------------------------- FAO via OWID
def owid_cattle():
    """FAOSTAT cattle stocks via Our World in Data -> {market: {year: head}}.

    The grapher CSV has lowercase headers: entity,code,year,<slug>.
    """
    raw = get("https://ourworldindata.org/grapher/cattle-livestock-count-heads.csv"
              "?v=1&csvType=full&useColumnShortNames=true").decode()
    rdr = csv.DictReader(io.StringIO(raw))
    cols = rdr.fieldnames or []
    valcol = next(c for c in cols if c not in ("entity", "code", "year"))
    want = {"United States": "US", "Turkey": "TR", "Türkiye": "TR",
            "European Union (27)": "EU"}
    out = defaultdict(dict)
    for row in rdr:
        key = want.get((row.get("entity") or "").strip())
        if not key:
            continue
        try:
            out[key][int(row["year"])] = float(row[valcol])
        except (KeyError, ValueError, TypeError):
            continue
    return {k: v for k, v in out.items() if v}


# ---------------------------------------------------------------- Eurostat
def eurostat_cattle():
    """Eurostat apro_mt_lscatl, total live bovines, EU aggregate -> {year: head}"""
    # NB: do not filter on `month` — the annual bovine population series returns
    # an empty month dimension and the query silently yields no values.
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/apro_mt_lscatl"
           "?format=JSON&lang=EN&animals=A2000&unit=THS_HD&geo=EU27_2020")
    body = get(url).decode()
    print("[diag] eurostat first 300 chars:", body[:300])
    j = json.loads(body)
    print("[diag] eurostat top keys:", list(j)[:10], "n values:", len(j.get("value", {})))
    idx = j["dimension"]["time"]["category"]["index"]
    vals = j["value"]
    inv = {v: k for k, v in idx.items()}
    out = {}
    for pos, val in vals.items():
        yr = inv.get(int(pos))
        if yr and val is not None:
            out[int(yr)] = float(val) * 1000.0
    return out


# ---------------------------------------------------------------- USDA via FRED
def fred_series(series_id):
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}").decode()
    out = {}
    for row in csv.DictReader(io.StringIO(raw)):
        date = (row.get("DATE") or row.get("observation_date") or "").strip()
        val = (row.get(series_id) or "").strip()
        if len(date) >= 4 and val not in ("", "."):
            out[int(date[:4])] = float(val)
    return out


def usda_cattle_fred():
    """A few plausible FRED ids for US cattle inventory; first that works wins."""
    for sid in ("CATTLEINVENTORY", "A01SCA", "M01SCA", "USCATTLE"):
        try:
            s = fred_series(sid)
            if s:
                report.setdefault("_fred_id_used", sid)
                return s
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("no working FRED id for US cattle inventory")


def main():
    owid = try_source("owid_fao_cattle", owid_cattle)
    euro = try_source("eurostat_cattle", eurostat_cattle)
    usda = {}  # no keyless FRED series for US cattle inventory; FAO/OWID covers the US

    series = {}
    if owid.get("US"):
        series["US"] = owid["US"]
    if usda:
        series["US_usda"] = usda
    series["EU"] = euro or owid.get("EU", {})
    if owid.get("TR"):
        series["TR"] = owid["TR"]

    series = {k: v for k, v in series.items() if v}
    years = sorted({y for v in series.values() for y in v})
    payload = {
        "source": "FAOSTAT via Our World in Data (cattle stocks, head); "
                  "Eurostat apro_mt_lscatl for the EU aggregate; FRED where available",
        "unit": "head of cattle",
        "columns": ["year"] + list(series),
        "rows": [[y] + [series[k].get(y) for k in series] for y in years],
    }
    json.dump(payload, open("data/herd-cattle.json", "w"), separators=(",", ":"))
    json.dump(report, open("data/herd-report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))
    if years:
        print(f"years {years[0]}..{years[-1]}  series {list(series)}")
    else:
        print("no herd series retrieved — see diagnostics above")


if __name__ == "__main__":
    main()
