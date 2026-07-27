#!/usr/bin/env python3
"""Test the hypothesis: does veterinary + medicine spend PER HEAD rise as herds shrink?

USDA ERS publishes commodity costs and returns, including a
"veterinary and medicine" line for cow-calf operations, per bred cow.

Two modes:
  MODE=discover  -> crawl the ERS product pages and report every data-file link
  (default)      -> download the file named in ERS_URL and parse the vet line

Writes data/vetcost-report.json either way, so a failure is visible rather than silent.
"""
import io, json, os, re, sys, urllib.request

UA = {"User-Agent": "namikakmandev-cattle-story/1.0 (github actions)"}
report = {}


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


PAGES = [
    "https://www.ers.usda.gov/data-products/commodity-costs-and-returns",
    "https://www.ers.usda.gov/data-products/commodity-costs-and-returns/commodity-costs-and-returns",
]


def discover():
    found = {}
    for page in PAGES:
        try:
            html = get(page).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            found[page] = f"ERROR {type(e).__name__}: {e}"
            continue
        links = re.findall(r'href="([^"]+)"', html)
        data = [l for l in links
                if re.search(r"\.(xlsx?|csv)(\?|$)", l, re.I)
                or "webdocs/DataFiles" in l]
        # keep the cattle-relevant ones first
        cattle = [l for l in data if re.search(r"cow|calf|cattle|beef", l, re.I)]
        found[page] = {"total_data_links": len(data),
                       "cattle_links": cattle[:25],
                       "sample_other": data[:15]}
    report["discover"] = found
    print(json.dumps(found, indent=1)[:6000])


def parse_file(url):
    raw = get(url)
    report["file"] = {"url": url, "bytes": len(raw)}
    name = url.lower()
    if name.endswith(".csv") or ".csv?" in name:
        text = raw.decode("utf-8", "replace")
        lines = text.splitlines()
        report["head"] = lines[:8]
        rows = [r for r in lines if re.search(r"veterinar", r, re.I)]
        report["vet_rows"] = rows[:40]
        print("HEAD:"); print("\n".join(lines[:8]))
        print("VET ROWS:", len(rows)); print("\n".join(rows[:40]))
        return
    # xls/xlsx
    try:
        import openpyxl  # noqa: PLC0415
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
        out = {}
        for ws in wb.worksheets:
            hits = []
            for row in ws.iter_rows(values_only=True):
                cells = [c for c in row if c is not None]
                if cells and any(isinstance(c, str) and re.search(r"veterinar", c, re.I) for c in cells):
                    hits.append([str(c)[:40] for c in cells][:30])
            if hits:
                out[ws.title] = hits[:5]
        report["sheets_with_vet"] = out
        print(json.dumps(out, indent=1)[:6000])
    except Exception as e:  # noqa: BLE001
        report["parse_error"] = f"{type(e).__name__}: {e}"
        print("parse error:", e)


def build_series(url):
    """ERS cow-calf CSV -> data/vetcost-us.json (US total, $/cow) + CPI deflator."""
    import csv as _csv
    text = get(url).decode("utf-8", "replace")
    rdr = _csv.DictReader(io.StringIO(text))
    want = {"Veterinary and medicine", "Total, operating costs",
            "Total, costs listed", "Total, allocated overhead"}
    series = {}
    for row in rdr:
        if row.get("Region") != "U.S. total":
            continue
        item = (row.get("Item") or "").strip()
        if item not in want:
            continue
        try:
            series.setdefault(item, {})[int(row["Year"])] = float(row["Value"])
        except (ValueError, TypeError, KeyError):
            continue
    # CPI so we can look at real terms
    cpi = {}
    try:
        raw = get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL").decode()
        acc = {}
        for r in _csv.DictReader(io.StringIO(raw)):
            d = (r.get("DATE") or r.get("observation_date") or "").strip()
            v = (r.get("CPIAUCSL") or "").strip()
            if len(d) >= 7 and v not in ("", "."):
                acc.setdefault(int(d[:4]), []).append(float(v))
        cpi = {y: sum(v) / len(v) for y, v in acc.items() if len(v) >= 6}
    except Exception as e:  # noqa: BLE001
        report["cpi_error"] = str(e)
    payload = {"source": "USDA ERS commodity costs and returns, cow-calf, U.S. total",
               "unit": "dollars per cow", "series": series,
               "cpi": cpi, "cpi_source": "FRED CPIAUCSL annual mean"}
    json.dump(payload, open("data/vetcost-us.json", "w"), separators=(",", ":"))
    report["series_items"] = {k: [min(v), max(v), len(v)] for k, v in series.items()}
    print(json.dumps(report["series_items"], indent=1))


def main():
    os.makedirs("data", exist_ok=True)
    mode = os.environ.get("MODE", "").strip()
    url = os.environ.get("ERS_URL", "").strip()
    if mode == "eaa":
        eaa_vet()
    elif mode == "discover" or not url:
        discover()
    elif mode == "series":
        build_series(url)
    else:
        parse_file(url)
    json.dump(report, open("data/vetcost-report.json", "w"), indent=1)




# ---------------------------------------------------------------- EU / TR
def eaa_vet():
    """Eurostat Economic Accounts for Agriculture -> veterinary expenses by country.

    NOTE: the EAA veterinary line covers ALL livestock, not cattle alone. That
    limitation must travel with any per-head number derived from it.
    """
    base = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/aact_eaa01"
            "?format=JSON&lang=EN")
    probe = json.loads(get(base + "&geo=EU27_2020&time=2020").decode())
    dims = probe.get("dimension", {})
    item_dim, vet_codes = None, {}
    for dk, dv in dims.items():
        labs = dv.get("category", {}).get("label", {})
        hit = {k: v for k, v in labs.items() if "veterinar" in str(v).lower()}
        if hit:
            item_dim, vet_codes = dk, hit
            break
    units = list(dims.get("unit", {}).get("category", {}).get("label", {}).items())
    indics = list(dims.get("indic_agr", {}).get("category", {}).get("label", {}).items())
    report["eaa_probe"] = {"item_dim": item_dim, "vet_codes": vet_codes,
                           "units": units[:10], "indics": indics[:10]}
    print("item dim:", item_dim, "vet codes:", vet_codes)
    print("units:", units[:10])
    print("indics:", indics[:10])
    if not item_dim:
        return

    out = {}
    for code in vet_codes:
        for geo in ("EU27_2020", "TR", "DE", "FR"):
            url = f"{base}&{item_dim}={code}&geo={geo}&unit=MIO_EUR"
            try:
                j = json.loads(get(url).decode())
                tcat = j["dimension"]["time"]["category"]["index"]
                inv = {v: k for k, v in tcat.items()}
                # flat index -> time position depends on remaining dims; when every
                # other dim is pinned to one value the flat index IS the time index
                vals = {}
                for pos, val in (j.get("value") or {}).items():
                    yr = inv.get(int(pos) % len(tcat))
                    if yr and val is not None:
                        vals[int(yr)] = float(val)
                if vals:
                    out[geo] = vals
                    print(f"  {geo}: {len(vals)} pts {min(vals)}..{max(vals)} "
                          f"last={vals[max(vals)]:.0f} MIO_EUR")
            except Exception as e:  # noqa: BLE001
                print(f"  {geo}: {type(e).__name__}: {e}")
    if out:
        json.dump({"source": "Eurostat aact_eaa01 veterinary expenses, million EUR at current "
                             "prices; ALL livestock, not cattle only",
                   "series": out}, open("data/vetcost-eu-tr.json", "w"), separators=(",", ":"))
    report["eaa_series"] = {k: [min(v), max(v), len(v)] for k, v in out.items()}


if __name__ == "__main__":
    main()
