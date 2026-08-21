#!/usr/bin/env python3
"""Annual broiler meat/feed parity for Türkiye, Poland, Egypt, Saudi Arabia.

Route chosen by the me-parity probe (data/_me-parity-probe.json): the FAOSTAT
API returns 401 from Actions, but the bulk-download service answers 200 — so
this pulls the Producer Prices bulk zip, filters the four countries, and writes

  data/broiler-annual.json          — the series + per-country parity KPI
  data/_broiler-annual-report.json  — everything found, chosen and rejected

Runs in GitHub Actions only (this dev sandbox has no egress to FAO).

The KPI is meat producer price / feed-grain producer price, both farm-gate,
both LCU/tonne, so each country's ratio is unitless and internally consistent.
Levels are NOT comparable across countries (feed mixes, subsidies, market
structure differ) — the KPI for cross-reading is parity indexed to the
country's own norm window, and the page must present it that way.
"""
import csv, io, json, os, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions)"}

AREAS = {"223": "TR", "173": "PL", "59": "EG", "194": "SA"}
AREA_NAMES = {"TR": "Türkiye", "PL": "Poland", "EG": "Egypt", "SA": "Saudi Arabia"}
MEAT_KW = ("chicken",)
# report everything feed-like; the parity denominator is chosen by preference below
FEED_KW = ("maize", "wheat", "barley", "sorghum", "soya", "soybean")
FEED_PREFERENCE = ("maize", "wheat", "barley", "sorghum")
NORM_WINDOW = (2015, 2024)  # parity indexed to each country's own mean over this window

report = {"route": "FAOSTAT bulk zip (API is 401 from Actions — see _me-parity-probe.json)"}


def get(url, timeout=600):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def find_prices_zip():
    """Resolve the Prices bulk file URL from the live listing — never guess it."""
    listing = json.loads(get("https://bulks-faostat.fao.org/production/datasets_E.json"))
    ds = listing["Datasets"]["Dataset"]
    if isinstance(ds, dict):
        ds = [ds]
    pp = [d for d in ds if d.get("DatasetCode") == "PP"]
    if not pp:
        names = sorted(d.get("DatasetCode", "?") for d in ds)
        raise SystemExit(f"no PP dataset in bulk listing; codes present: {names}")
    loc = pp[0]["FileLocation"]
    report["pp_dataset"] = {k: pp[0].get(k) for k in
                            ("DatasetName", "DateUpdate", "FileSize", "FileRows", "FileLocation")}
    # prefer the long-format variant if it exists alongside the listed file
    norm = loc.replace("All_Data.zip", "All_Data_(Normalized).zip")
    if norm != loc:
        try:
            req = urllib.request.Request(norm, headers=UA, method="HEAD")
            urllib.request.urlopen(req, timeout=60)
            report["pp_dataset"]["using"] = norm
            return norm
        except Exception:
            pass
    report["pp_dataset"]["using"] = loc
    return loc


def keyword(name, kws):
    n = name.lower()
    return any(k in n for k in kws)


def rows_from_zip(url):
    """Yield dict rows from the main CSV inside the bulk zip, wide or long format."""
    raw = get(url)
    report["zip_bytes"] = len(raw)
    zf = zipfile.ZipFile(io.BytesIO(raw))
    members = [n for n in zf.namelist()
               if n.lower().endswith(".csv") and "flag" not in n.lower()
               and "note" not in n.lower() and "code" not in n.lower()]
    if not members:
        raise SystemExit(f"no data CSV in zip; members: {zf.namelist()}")
    member = max(members, key=lambda n: zf.getinfo(n).file_size)
    report["zip_member"] = member
    with zf.open(member) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace")
        rdr = csv.DictReader(text)
        report["csv_columns"] = rdr.fieldnames
        year_cols = [c for c in (rdr.fieldnames or [])
                     if c.startswith("Y") and c[1:].isdigit()]
        for row in rdr:
            code = (row.get("Area Code") or "").strip().strip('"')
            if code not in AREAS:
                continue
            if year_cols:  # wide format: one row per series, Y1991..Y20xx columns
                for yc in year_cols:
                    v = (row.get(yc) or "").strip()
                    if v:
                        yield row, int(yc[1:]), v
            else:  # long format: Year + Value columns
                y, v = (row.get("Year") or "").strip(), (row.get("Value") or "").strip()
                if y.isdigit() and v:
                    yield row, int(y), v


def main():
    url = find_prices_zip()
    print("fetching", url)

    # found[cc][item][element] = {"unit": u, "months": {label: {year: value}}}
    found = {cc: {} for cc in AREAS.values()}
    for row, year, value in rows_from_zip(url):
        item = (row.get("Item") or "").strip()
        if not (keyword(item, MEAT_KW) or keyword(item, FEED_KW)):
            continue
        cc = AREAS[(row.get("Area Code") or "").strip().strip('"')]
        element = (row.get("Element") or "").strip()
        months = (row.get("Months") or "Annual value").strip()
        try:
            val = float(value)
        except ValueError:
            continue
        slot = found[cc].setdefault(item, {}).setdefault(
            element, {"unit": (row.get("Unit") or "").strip(), "months": {}})
        slot["months"].setdefault(months, {})[year] = val

    # coverage report: every matched series, its span, and monthly availability
    coverage = {}
    for cc, items in found.items():
        cov = {}
        for item, elements in items.items():
            cov[item] = {}
            for el, slot in elements.items():
                ann = slot["months"].get("Annual value", {})
                monthly = {m: len(ys) for m, ys in slot["months"].items() if m != "Annual value"}
                cov[item][el] = {
                    "unit": slot["unit"],
                    "annual_span": [min(ann), max(ann)] if ann else None,
                    "annual_n": len(ann),
                    "monthly_rows": sum(monthly.values()),
                }
        coverage[cc] = cov
    report["coverage"] = coverage

    # build the KPI per country: chicken LCU/t over preferred feed grain LCU/t
    def pick(items, kws):
        """Longest annual LCU series among items matching kws; (item, el, {yr: v})."""
        best = None
        for item, elements in items.items():
            if not keyword(item, kws):
                continue
            for el, slot in elements.items():
                if "producer price" not in el.lower() or "lcu" not in el.lower():
                    continue
                ann = slot["months"].get("Annual value", {})
                if ann and (best is None or len(ann) > len(best[2])):
                    best = (item, el, ann)
        return best

    out = {"meta": {
        "source": "FAOSTAT Producer Prices (PP), annual, farm-gate, LCU/tonne — bulk download",
        "dataset": report.get("pp_dataset"),
        "kpi": "parity = chicken meat price / feed grain price (tonnes of grain one tonne "
               "of chicken buys); parity_idx = parity as % of the country's own "
               f"{NORM_WINDOW[0]}–{NORM_WINDOW[1]} mean",
        "honesty": [
            "Parity LEVELS are not comparable across countries: feed composition, "
            "subsidy regimes and market structure differ. Compare parity_idx only.",
            "The denominator is a single feed GRAIN, not compound broiler feed — "
            "a proxy; soymeal and other components are outside it.",
            "SA/EG feed is heavily imported; a domestic grain producer price "
            "understates true feed-cost swings there.",
        ],
        "norm_window": list(NORM_WINDOW),
    }, "countries": {}}

    decisions = {}
    for cc, items in found.items():
        meat = pick(items, MEAT_KW)
        feed = None
        for kw in FEED_PREFERENCE:
            feed = pick(items, (kw,))
            if feed:
                break
        dec = {"meat": meat and {"item": meat[0], "element": meat[1],
                                 "span": [min(meat[2]), max(meat[2])]},
               "feed": feed and {"item": feed[0], "element": feed[1],
                                 "span": [min(feed[2]), max(feed[2])]}}
        if not meat or not feed:
            dec["verdict"] = "EXCLUDED — missing " + ("meat" if not meat else "feed") + " side"
            decisions[cc] = dec
            continue
        years = sorted(set(meat[2]) & set(feed[2]))
        parity = {y: round(meat[2][y] / feed[2][y], 3) for y in years if feed[2][y]}
        normy = [parity[y] for y in parity if NORM_WINDOW[0] <= y <= NORM_WINDOW[1]]
        dec["overlap_years"] = len(parity)
        if len(parity) < 5 or len(normy) < 3:
            dec["verdict"] = f"EXCLUDED — only {len(parity)} overlap years " \
                             f"({len(normy)} in norm window)"
            decisions[cc] = dec
            continue
        mean = sum(normy) / len(normy)
        dec["verdict"] = "INCLUDED"
        decisions[cc] = dec
        out["countries"][cc] = {
            "name": AREA_NAMES[cc],
            "meat_item": meat[0], "feed_item": feed[0], "element": meat[1],
            "meat": {str(y): meat[2][y] for y in years},
            "feed": {str(y): feed[2][y] for y in years},
            "parity": {str(y): parity[y] for y in parity},
            "parity_idx": {str(y): round(parity[y] / mean * 100, 1) for y in parity},
            "norm_mean": round(mean, 3),
        }
        if cc in ("SA", "EG"):
            out["countries"][cc]["caveat"] = (
                "feed largely imported — domestic grain producer price is a weak "
                "proxy for actual feed cost; read direction, not level")
    report["decisions"] = decisions

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "_broiler-annual-report.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    included = list(out["countries"])
    if included:
        with open(os.path.join(ROOT, "data", "broiler-annual.json"), "w") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
    print("\n== decisions ==")
    print(json.dumps(decisions, indent=1, ensure_ascii=False))
    print(f"\nincluded: {included or 'NONE — read the report before building anything'}")


if __name__ == "__main__":
    main()
