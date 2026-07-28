#!/usr/bin/env python3
"""Vet-medicine API study: what the maker sells vs what the active ingredient costs.

The farm-side studies ask what a kilo of beef buys in feed. This one asks the same
question one link up the chain: what a finished veterinary medicine sells for, against
the price of the active pharmaceutical ingredient (API) that goes into it.

The split we need everywhere is the same:
  numerator   finished pharmaceutical preparations   NACE 21.2 / NAICS 325412
  denominator basic pharmaceutical products (API)    NACE 21.1 / NAICS 325411

Two modes:
  MODE=discover  -> do not parse. Dump what each source really returns: the BLS PPI
                    catalogue rows that mention veterinary/medicinal-botanical, the
                    Eurostat dimension ids and codes, the EVDS spans.
  (default)      -> fetch the series named in the CONFIRMED_* tables below.

Everything runs in GitHub Actions — the dev sandbox cannot reach BLS, FRED, Eurostat
or EVDS. Every run writes data/vetapi-report.json so a silent zero is visible.
"""
import csv, io, json, os, re, sys, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "namikakmandev-vetapi/1.0 (github actions; contact via repo)"}
MODE = os.environ.get("MODE", "").strip()
report = {}


def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def out(name, obj):
    path = os.path.join(ROOT, "data", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), separators=(",", ":"))
    print(f"[write] data/{name}")


# --------------------------------------------------------------- US · discovery
# BLS publishes its whole PPI catalogue as keyless flat files. Grepping the real
# catalogue beats guessing FRED ids: an id that does not exist returns an HTML error
# page from fredgraph, not an error, so a guess fails silently.
BLS_FILES = {
    "pc_series": "https://download.bls.gov/pub/time.series/pc/pc.series",
    "pc_product": "https://download.bls.gov/pub/time.series/pc/pc.product",
    "pc_industry": "https://download.bls.gov/pub/time.series/pc/pc.industry",
    "wp_series": "https://download.bls.gov/pub/time.series/wp/wp.series",
    "wp_item": "https://download.bls.gov/pub/time.series/wp/wp.item",
}
US_HUNT = re.compile(r"veterinar|medicinal|botanical|pharmaceutical", re.I)


def us_discover():
    found = {}
    for key, url in BLS_FILES.items():
        try:
            text = get(url).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            found[key] = f"ERROR {type(e).__name__}: {e}"
            continue
        lines = text.splitlines()
        hits = [l for l in lines if US_HUNT.search(l)]
        found[key] = {"total_rows": len(lines), "header": lines[0] if lines else "",
                      "matches": len(hits), "sample": hits[:60]}
    # probe the FRED ids we believe exist, so the report says which actually resolve
    probes = {}
    for sid in FRED_PROBE:
        probes[sid] = fred_probe(sid)
    found["fred_probe"] = probes
    report["us_discover"] = found
    print(json.dumps(found, indent=1, default=str)[:9000])


FRED_PROBE = [
    "PCU325411325411",    # medicinal & botanical mfg — bulk active ingredient
    "PCU325412325412",    # pharmaceutical preparation mfg — finished dose
    "PCU3254123254121",   # product lines under 325412; which exist is unknown
    "PCU3254123254123",
    "PCU3254123254125",
    "PCU3254123254127",
    "PCU3254123254129",
    "WPU0638",            # commodity: pharmaceutical preparations
    "WPU063807",
    "WPU06380701",
    "CPIAUCSL",           # deflator + a known-good control for the probe itself
]


def fred_csv(series_id):
    """FRED keyless CSV -> {YYYY-MM: value}. Raises if the id does not resolve."""
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}").decode(
        "utf-8", "replace")
    vals = {}
    for row in csv.DictReader(io.StringIO(raw)):
        date = (row.get("DATE") or row.get("observation_date") or "").strip()
        val = (row.get(series_id) or "").strip()
        if len(date) >= 7 and val not in ("", "."):
            vals[date[:7]] = float(val)
    if not vals:
        raise RuntimeError(f"{series_id}: no observations parsed (id probably invalid)")
    return vals


def fred_probe(series_id):
    try:
        v = fred_csv(series_id)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}
    ks = sorted(v)
    return {"ok": True, "n": len(v), "span": [ks[0], ks[-1]], "last": v[ks[-1]]}


# --------------------------------------------------------------- EU · discovery
# Eurostat industrial producer prices by NACE. C21 splits into C21_1 (basic
# pharmaceutical products = API) and C21_2 (preparations) — but whether both are
# actually published, and under which code spelling, has to be read off the source.
EU_DATASETS = ["sts_inpp_a", "sts_inppd_a", "sts_inppnd_a", "sts_inpp_m"]


def eurostat_json(dataset, params):
    base = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
            + dataset + "?format=JSON&lang=EN")
    qs = "".join(f"&{k}={v}" for k, v in params.items())
    return json.loads(get(base + qs).decode())


def eu_discover():
    found = {}
    for ds in EU_DATASETS:
        try:
            j = eurostat_json(ds, {"geo": "EU27_2020"})
            dims = {}
            for d in j["id"]:
                cat = j["dimension"][d]["category"].get("label", {})
                items = list(cat.items())
                # keep the pharma-relevant NACE codes in full, sample the rest
                pharma = [kv for kv in items if re.match(r"^C?21", kv[0])]
                dims[d] = {"n": len(items), "sample": items[:25], "pharma_codes": pharma}
            found[ds] = {"dimension_ids": j["id"], "sizes": j["size"], "dims": dims}
        except Exception as e:  # noqa: BLE001
            found[ds] = f"ERROR {type(e).__name__}: {e}"
    report["eu_discover"] = found
    print(json.dumps(found, indent=1, default=str)[:9000])


def _jsonstat(j):
    """JSON-stat 2.0 -> list of (dict_of_dimension_codes, value)."""
    ids, sizes, dims = j["id"], j["size"], j["dimension"]
    codes = []
    for d in ids:
        idx = dims[d]["category"]["index"]
        if isinstance(idx, dict):
            inv = {v: k for k, v in idx.items()}
            codes.append([inv[i] for i in range(len(inv))])
        else:
            codes.append(list(idx))
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    rows = []
    for pos, val in (j.get("value") or {}).items():
        if val is None:
            continue
        p = int(pos)
        rows.append(({d: codes[i][(p // strides[i]) % sizes[i]]
                      for i, d in enumerate(ids)}, float(val)))
    return rows


# --------------------------------------------------------------- TR · discovery
# TÜİK Yİ-ÜFE via TCMB EVDS. Confirmed present in data/tr-series-candidates.json:
#   TP.TUFE1YI.T59  3.12.  Temel eczacılık ürünleri ve müstahzarları   (NACE 21, whole)
#   TP.TUFE1YI.T60  3.12.1 Eczacılık müstahzarları                     (NACE 21.2)
#   TP.UFEYD16      3.12.  Temel eczacılık ürünleri (Yurt Dışı ÜFE)    (import prices)
# Note there is NO standalone NACE 21.1 line for TR — see the honest-scope note below.
TR_CODES = {
    "ppi_nace21": "TP.TUFE1YI.T59",
    "ppi_nace212": "TP.TUFE1YI.T60",
    "import_ppi_nace21": "TP.UFEYD16",
}


def evds_api():
    key = os.environ.get("EVDS_KEY", "").strip()
    if not key:
        raise RuntimeError("EVDS_KEY not set")
    from evds import evdsAPI  # noqa: PLC0415
    return evdsAPI(key)


def tr_fetch():
    api = evds_api()
    codes = list(TR_CODES.values())
    df = api.get_data(codes, startdate="01-01-2005", enddate="31-12-2026")
    cols = {k: c.replace(".", "_") for k, c in TR_CODES.items()}
    series = {k: {} for k in TR_CODES}
    for _, r in df.iterrows():
        t = str(r.get("Tarih", ""))
        parts = t.replace("/", "-").split("-")
        if len(parts) < 2:
            continue
        ym = f"{parts[0]}-{int(parts[1]):02d}"
        for k, col in cols.items():
            v = r.get(col)
            if v is None or str(v) == "nan":
                continue
            series[k][ym] = round(float(v), 3)
    empty = [k for k, v in series.items() if not v]
    report["tr"] = {"ok": not empty, "empty": empty,
                    "counts": {k: len(v) for k, v in series.items()},
                    "span": {k: [min(v), max(v)] for k, v in series.items() if v}}
    if empty:
        print(f"[WARN] TR empty series: {empty}")
    return {
        "source": ("TCMB EVDS / TÜİK: TP.TUFE1YI.T59 (Yİ-ÜFE, NACE 21 temel eczacılık "
                   "ürünleri ve müstahzarları), TP.TUFE1YI.T60 (Yİ-ÜFE, NACE 21.2 "
                   "eczacılık müstahzarları), TP.UFEYD16 (Yurt Dışı ÜFE, NACE 21)"),
        "note": ("TÜİK publishes no standalone NACE 21.1 (basic pharmaceutical products) "
                 "index. The API side for TR is proxied by the imported-goods price index "
                 "for NACE 21, which is an import price, not a domestic ingredient price."),
        "codes": TR_CODES,
        "series": series,
    }


def tr_discover():
    try:
        api = evds_api()
        df = api.get_data(list(TR_CODES.values()),
                          startdate="01-01-2005", enddate="31-12-2026")
        report["tr_discover"] = {"columns": list(df.columns), "rows": len(df),
                                 "head": df.head(3).to_dict("records"),
                                 "tail": df.tail(3).to_dict("records")}
    except Exception as e:  # noqa: BLE001
        report["tr_discover"] = f"ERROR {type(e).__name__}: {e}"
    print(json.dumps(report["tr_discover"], indent=1, default=str)[:4000])


# --------------------------------------------------------------- fetch (default)
def us_fetch():
    """Confirmed FRED ids only. Anything unresolved is reported, never silently dropped."""
    wanted = {
        "api_ppi": "PCU325411325411",       # NAICS 325411 medicinal & botanical
        "prep_ppi": "PCU325412325412",      # NAICS 325412 pharmaceutical preparations
        "cpi": "CPIAUCSL",                  # deflator
    }
    extra = json.loads(os.environ.get("US_EXTRA", "{}") or "{}")
    wanted.update(extra)
    series, errs = {}, {}
    for key, sid in wanted.items():
        try:
            series[key] = fred_csv(sid)
        except Exception as e:  # noqa: BLE001
            errs[key] = f"{sid}: {type(e).__name__}: {str(e)[:120]}"
    report["us"] = {"ok": not errs, "errors": errs,
                    "counts": {k: len(v) for k, v in series.items()},
                    "span": {k: [min(v), max(v)] for k, v in series.items() if v}}
    if errs:
        print(f"[WARN] US unresolved: {errs}")
    return {
        "source": ("BLS producer price indexes via FRED: PCU325411325411 (NAICS 325411 "
                   "medicinal and botanical manufacturing — bulk active ingredient), "
                   "PCU325412325412 (NAICS 325412 pharmaceutical preparation "
                   "manufacturing — finished dose), CPIAUCSL for deflating"),
        "note": ("Index numbers, not quantities. Only ratios between dates are meaningful. "
                 "325411/325412 cover human and animal pharma together unless a "
                 "veterinary product line is confirmed separately."),
        "codes": wanted,
        "series": series,
    }


def eu_fetch():
    """Eurostat industrial producer prices, NACE C21 split. Codes set by EU_NACE env
    once discovery has confirmed the spelling; defaults are the documented ones."""
    ds = os.environ.get("EU_DATASET", "sts_inpp_a").strip()
    nace = json.loads(os.environ.get("EU_NACE", "{}") or "{}") or {
        "api_ppi": "C21_1", "prep_ppi": "C21_2", "pharma_ppi": "C21"}
    series, errs = {}, {}
    for key, code in nace.items():
        try:
            j = eurostat_json(ds, {"geo": "EU27_2020", "nace_r2": code})
            vals = {}
            for dims, val in _jsonstat(j):
                t = dims.get("time")
                if t:
                    vals[t] = val
            if not vals:
                raise RuntimeError("no observations for this nace code")
            series[key] = vals
        except Exception as e:  # noqa: BLE001
            errs[key] = f"{code}: {type(e).__name__}: {str(e)[:140]}"
    report["eu"] = {"dataset": ds, "ok": not errs, "errors": errs,
                    "counts": {k: len(v) for k, v in series.items()},
                    "span": {k: [min(v), max(v)] for k, v in series.items() if v}}
    if errs:
        print(f"[WARN] EU unresolved: {errs}")
    return {
        "source": f"Eurostat {ds}, industrial producer price index, geo EU27_2020, "
                  f"NACE {', '.join(sorted(set(nace.values())))}",
        "note": ("NACE 21.1 basic pharmaceutical products is the active-ingredient stage; "
                 "21.2 pharmaceutical preparations is the finished dose. Both cover human "
                 "and veterinary pharma together — no veterinary-only split is published."),
        "codes": nace,
        "series": series,
    }


def main():
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    only = set(sys.argv[1:]) or {"us", "eu", "tr"}
    if MODE == "discover":
        if "us" in only:
            us_discover()
        if "eu" in only:
            eu_discover()
        if "tr" in only:
            tr_discover()
    else:
        for name, fn, path in (("us", us_fetch, "vetapi-us.json"),
                               ("eu", eu_fetch, "vetapi-eu.json"),
                               ("tr", tr_fetch, "vetapi-tr.json")):
            if name not in only:
                continue
            try:
                out(path, fn())
            except Exception as e:  # noqa: BLE001
                report[name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                print(f"[FAIL] {name}: {type(e).__name__}: {e}")
    json.dump(report, open(os.path.join(ROOT, "data", "vetapi-report.json"), "w"),
              indent=1, default=str)
    print("\n" + json.dumps(report, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
