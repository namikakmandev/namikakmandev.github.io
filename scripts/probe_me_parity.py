#!/usr/bin/env python3
"""Discovery probe: can the cattle-parity study be extended to the Middle East?

Answers the open questions in notes/parite-sigir-middle-east.md. Runs in GitHub
Actions (this sandbox has no egress). It DISCOVERS ONLY — it writes
data/_me-parity-probe.json describing what each source returned, and never writes
a series into the analysis. Nothing here feeds a chart until a human has read the
dump and written a parser against the real shape.

Every probe is independent: a failure records itself and the next one still runs.
"""
import json, os, re, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions)"}
report = {}


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.headers.get("Content-Type", ""), r.read()


def peek(obj, depth=0):
    """Structure of a parsed JSON blob without dumping megabytes of values."""
    if depth > 3:
        return "..."
    if isinstance(obj, dict):
        return {k: peek(v, depth + 1) for k, v in list(obj.items())[:25]}
    if isinstance(obj, list):
        return [f"list[{len(obj)}]"] + ([peek(obj[0], depth + 1)] if obj else [])
    return type(obj).__name__


def probe(name, url, note=""):
    """Fetch one URL and record what came back. Never raises."""
    entry = {"url": url, "note": note}
    try:
        ctype, raw = get(url)
        entry["http"] = 200
        entry["content_type"] = ctype
        entry["bytes"] = len(raw)
        text = raw.decode("utf-8", "replace")
        if "json" in ctype or text.lstrip()[:1] in "{[":
            try:
                entry["structure"] = peek(json.loads(text))
            except ValueError as ex:
                entry["parse_error"] = repr(ex)
                entry["head"] = text[:1200]
        else:
            entry["head"] = text[:1200]
    except urllib.error.HTTPError as ex:
        entry["http"] = ex.code
        entry["error"] = f"HTTPError: {ex.reason}"
    except Exception as ex:  # noqa: BLE001 — a dead probe must not stop the others
        entry["error"] = f"{type(ex).__name__}: {ex}"
    report[name] = entry
    print(f"[{entry.get('http', 'ERR')}] {name}: {entry.get('error') or str(entry.get('bytes')) + ' bytes'}")
    return entry


# --------------------------------------------------------------- 1 · ISRAEL
# Q: what are the index ids for agricultural OUTPUT price and FODDER input price,
#    and does the keyless API serve them monthly?
def probe_israel():
    cat = probe("israel_catalog",
                "https://api.cbs.gov.il/index/catalog/catalog?lang=en&format=json&download=false",
                "CBS index catalog — hunting agricultural output / fodder input ids")
    # The catalog shape is unknown, so search the RAW text for the words that matter
    # rather than guessing a key path. Whatever surrounds them tells us the id.
    hits = []
    try:
        _, raw = get("https://api.cbs.gov.il/index/catalog/catalog?lang=en&format=json&download=false")
        text = raw.decode("utf-8", "replace")
        for m in re.finditer(r"[^{}]{0,220}(fodder|agricultur|farm|livestock|feed)[^{}]{0,220}",
                             text, re.I):
            hits.append(m.group(0)[:400])
    except Exception as ex:  # noqa: BLE001
        cat["keyword_scan_error"] = f"{type(ex).__name__}: {ex}"
    report["israel_catalog_keyword_hits"] = {"n": len(hits), "sample": hits[:40]}
    print(f"[scan] israel catalog: {len(hits)} agriculture/fodder mentions")
    # Also list the chapter index — chapter letters are undocumented, so try a few.
    for ch in ("a", "b", "c", "d", "e", "f"):
        probe(f"israel_price_all_chapter_{ch}",
              f"https://api.cbs.gov.il/index/data/price_all?lang=en&chapter={ch}&format=json&download=false",
              "which indices live in this chapter")


# ------------------------------------------------------------- 2 · FAOSTAT PP
# Q: which Middle East countries have MONTHLY cattle + maize/barley producer
#    prices, and from when? Annual is a known yes; monthly is the question.
FAO_AREAS = {"Israel": 105, "Iran": 102, "Egypt": 59, "Saudi Arabia": 194,
             "Jordan": 112, "Lebanon": 121, "Iraq": 103, "Turkiye": 223}
FAO_ITEMS = {"cattle_meat": 867, "maize": 56, "barley": 44}


def probe_faostat():
    probe("faostat_pp_dimensions",
          "https://faostatservices.fao.org/api/v1/en/dimensions/PP",
          "real dimension + element names for the Producer Prices domain")
    areas = ",".join(str(v) for v in FAO_AREAS.values())
    items = ",".join(str(v) for v in FAO_ITEMS.values())
    # Element 5539 = producer price index / 5530-5532 = price levels. Ask for all
    # elements and let the dump say which ones actually come back per country.
    probe("faostat_pp_monthly",
          "https://faostatservices.fao.org/api/v1/en/data/PP?"
          + urllib.parse.urlencode({"area": areas, "item": items, "year": "2015,2020,2023",
                                    "area_cs": "FAO", "item_cs": "FAO",
                                    "show_codes": "true", "show_unit": "true",
                                    "show_flags": "true", "null_values": "false",
                                    "output_type": "objects", "limit": "400"}),
          "does PP return month-level rows for these countries?")
    probe("faostat_bulk_listing",
          "https://bulks-faostat.fao.org/production/datasets_E.json",
          "bulk file names — the zip route if the API is unusable")


# ------------------------------------------------------------ 3 · SAUDI GASTAT
# Q: is the Wholesale Price Index machine-readable anywhere, or bulletins only?
def probe_saudi():
    for name, url in [
        ("saudi_opendata_search",
         "https://open.data.gov.sa/data/api/v1/datasets?q=wholesale%20price%20index"),
        ("saudi_gastat_wpi_page", "https://www.stats.gov.sa/en/w/wpi-1"),
        ("saudi_datasaudi", "https://datasaudi.sa/en/api/indicators"),
    ]:
        probe(name, url, "Saudi WPI: any machine-readable endpoint?")


def main():
    probe_israel()
    probe_faostat()
    probe_saudi()
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    out = os.path.join(ROOT, "data", "_me-parity-probe.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=1, default=str)
    ok = [k for k, v in report.items() if v.get("http") == 200]
    print(f"\nwrote {out}")
    print(f"reachable: {len(ok)}/{len(report)} -> {ok}")
    print("\n" + json.dumps(report, indent=1, default=str)[:20000])


if __name__ == "__main__":
    main()
