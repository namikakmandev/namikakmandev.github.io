#!/usr/bin/env python3
"""Generic public-data fetcher. Config-driven, runs in GitHub Actions.

Why it exists: this sandbox cannot reach FRED/Eurostat/USDA/OWID directly, so all
fetching happens in Actions. Adding a new series should mean editing JSON, not
writing a new script.

Usage
  python scripts/fetch.py                 # fetch everything enabled in data-sources.json
  python scripts/fetch.py NAME [NAME...]  # fetch only these entries
  MODE=discover python scripts/fetch.py NAME
        -> do not parse; dump what the source actually returns (columns, dimension
           names, category codes) so a parser can be written against reality

Providers: fred | eurostat | owid | csv
Every run writes data/_fetch-report.json recording what each source returned, so a
silent zero is visible instead of looking like a real answer.
"""
import csv, io, json, os, re, sys, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "data-sources.json")
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions)"}
MODE = os.environ.get("MODE", "").strip()
report = {}


def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ----------------------------------------------------------------- providers
def fred(entry):
    """Any FRED series -> {series_key: {YYYY-MM: value}}. Keyless CSV endpoint.

    One bad series id must not kill the rest of the entry: a probe listing ten
    candidate ids is the normal way to find out which of them exist, so failures
    are recorded per series instead of raised.
    """
    out, errors = {}, {}
    for key, sid in entry["series"].items():
        try:
            raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}").decode()
        except Exception as ex:  # noqa: BLE001 — a missing id is a result, not a crash
            errors[key] = f"{sid}: {type(ex).__name__}: {ex}"
            out[key] = {}
            continue
        vals = {}
        for row in csv.DictReader(io.StringIO(raw)):
            date = (row.get("DATE") or row.get("observation_date") or "").strip()
            val = (row.get(sid) or "").strip()
            if len(date) >= 7 and val not in ("", "."):
                vals[date[:7]] = float(val)
        out[key] = vals
    if MODE == "discover":
        return {"_discover": {
            "ids": entry["series"],
            "found": {k: {"n": len(v), "span": [min(v), max(v)]}
                      for k, v in out.items() if v},
            "missing": sorted(k for k, v in out.items() if not v),
            "errors": errors}}
    if errors:
        report.setdefault("_errors", {})[entry["name"]] = errors
    return out


def _jsonstat(j):
    """JSON-stat 2.0 -> list of (dict_of_dimension_codes, value). Handles any shape."""
    ids = j["id"]
    sizes = j["size"]
    dims = j["dimension"]
    # position -> code, per dimension
    codes = []
    for d in ids:
        idx = dims[d]["category"]["index"]
        if isinstance(idx, dict):
            inv = {v: k for k, v in idx.items()}
            codes.append([inv[i] for i in range(len(inv))])
        else:  # already a list
            codes.append(list(idx))
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    out = []
    for pos, val in (j.get("value") or {}).items():
        if val is None:
            continue
        p = int(pos)
        key = {}
        for i, d in enumerate(ids):
            key[d] = codes[i][(p // strides[i]) % sizes[i]]
        out.append((key, float(val)))
    return out


def eurostat(entry):
    """Any Eurostat dataset. entry['dataset'] + entry['params'] (dict)."""
    base = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
            + entry["dataset"] + "?format=JSON&lang=EN")
    # a list value repeats the parameter: am_item=X&am_item=Y. Needed because an
    # unfiltered aact_eaa01 query is refused with HTTP 413.
    qs = ""
    for k, v in entry.get("params", {}).items():
        qs += "".join(f"&{k}={x}" for x in (v if isinstance(v, list) else [v]))
    j = json.loads(get(base + qs).decode())
    if MODE == "discover":
        # cap high enough to show a full item catalogue: at 40 the EAA input
        # lines (AM2xxxxx) fell off the end and the dump looked like an
        # output-only dataset
        dims = {d: list(j["dimension"][d]["category"]["label"].items())[:500]
                for d in j["id"]}
        return {"_discover": {"dimension_ids": j["id"], "sizes": j["size"],
                              "categories": dims}}
    rows = _jsonstat(j)
    # Without split_dim the output is keyed on geo alone, so a query returning
    # several animal categories or cost items collapses them into one key and
    # silently overwrites. Name the dimensions that separate the series.
    split = entry.get("split_dim") or (["geo"] if "geo" in j["id"] else [])
    if isinstance(split, str):
        split = [split]
    out = defaultdict(dict)
    for key, val in rows:
        t = key.get("time")
        g = "|".join(key.get(d, "") for d in split) or "ALL"
        if t:
            out[g][t] = val
    return dict(out)


def owid(entry):
    """Any Our World in Data grapher slug. entry['slug'] + entry['entities'] map."""
    raw = get(f"https://ourworldindata.org/grapher/{entry['slug']}.csv"
              "?v=1&csvType=full&useColumnShortNames=true").decode()
    rdr = csv.DictReader(io.StringIO(raw))
    cols = rdr.fieldnames or []
    if MODE == "discover":
        rows = list(rdr)[:3]
        ents = sorted({r.get("entity") or r.get("Entity") or "" for r in csv.DictReader(
            io.StringIO(raw))})
        return {"_discover": {"columns": cols, "sample": rows,
                              "n_entities": len(ents), "entities_sample": ents[:60]}}
    ent_col = "entity" if "entity" in cols else "Entity"
    yr_col = "year" if "year" in cols else "Year"
    valcol = next(c for c in cols if c.lower() not in ("entity", "code", "year"))
    want = entry.get("entities") or {}
    out = defaultdict(dict)
    for row in rdr:
        name = (row.get(ent_col) or "").strip()
        key = want.get(name)
        if not key:
            continue
        try:
            out[key][int(row[yr_col])] = float(row[valcol])
        except (ValueError, TypeError, KeyError):
            continue
    return dict(out)


def csv_source(entry):
    """Any plain CSV. entry['url'] + optional 'filters' (col->value) and 'pivot'."""
    text = get(entry["url"]).decode("utf-8", "replace")
    rdr = csv.DictReader(io.StringIO(text))
    cols = rdr.fieldnames or []
    if MODE == "discover":
        rows = list(rdr)[:5]
        return {"_discover": {"columns": cols, "sample": rows}}
    filters = entry.get("filters", {})
    kcol, vcol = entry["key_col"], entry["value_col"]
    group = entry.get("group_col")
    out = defaultdict(dict)
    for row in rdr:
        if any((row.get(c) or "").strip() != v for c, v in filters.items()):
            continue
        try:
            g = (row.get(group) or "ALL").strip() if group else "ALL"
            out[g][row[kcol].strip()] = float(row[vcol])
        except (ValueError, TypeError, KeyError):
            continue
    return dict(out)


PROVIDERS = {"fred": fred, "eurostat": eurostat, "owid": owid, "csv": csv_source}


# ----------------------------------------------------------------- runner
def run(entry):
    name = entry["name"]
    fn = PROVIDERS[entry["provider"]]
    data = fn(entry)
    if "_discover" in data:
        report[name] = {"mode": "discover", **data["_discover"]}
        print(json.dumps(data["_discover"], indent=1, default=str)[:4000])
        return
    counts = {k: len(v) for k, v in data.items()}
    empty = [k for k, n in counts.items() if n == 0]
    report[name] = {"ok": bool(data) and not empty, "counts": counts,
                    "empty_keys": empty,
                    "span": {k: [min(v), max(v)] for k, v in data.items() if v}}
    if not data or empty:
        print(f"[WARN] {name}: empty series {empty or 'all'}")
    else:
        print(f"[ok]   {name}: " + ", ".join(f"{k}={n}" for k, n in counts.items()))
    out_path = os.path.join(ROOT, entry["out"])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"source": entry.get("source", entry["provider"]),
               "fetched_by": "scripts/fetch.py",
               "config": {k: entry[k] for k in entry if k not in ("out",)},
               "series": data},
              open(out_path, "w"), separators=(",", ":"))


def main():
    cfg = json.load(open(CONFIG))
    only = set(sys.argv[1:])
    # naming an entry runs it even when disabled: `enabled` governs the scheduled
    # sweep, while a probe is always a deliberate, explicit request
    entries = [e for e in cfg["sources"]
               if e["name"] in only or (not only and e.get("enabled", True))]
    if not entries:
        sys.exit(f"no matching sources (asked for {only or 'all'})")
    failed = []
    for e in entries:
        try:
            run(e)
        except Exception as ex:  # noqa: BLE001 — one bad source must not stop the rest
            report[e["name"]] = {"ok": False, "error": f"{type(ex).__name__}: {ex}"}
            print(f"[FAIL] {e['name']}: {type(ex).__name__}: {ex}")
            failed.append(e["name"])
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump(report, open(os.path.join(ROOT, "data", "_fetch-report.json"), "w"), indent=1)
    print("\n" + json.dumps(report, indent=1, default=str)[:3000])
    if failed:
        print(f"\n{len(failed)} source(s) failed: {failed}")


if __name__ == "__main__":
    main()
