#!/usr/bin/env python3
"""Index every dataset in data/ -> data/_catalog.json

Why: data/ grew to 44 files from several different scripts, in a dozen different
shapes. Starting a new study meant grepping old files to work out what existed
and how it was laid out. This walks the directory and writes one manifest:
what each file is, what produced it, what it covers, how fresh it is, and what
caveat travels with it.

It records what it can verify and flags what it cannot. A file with no traceable
producer is reported as unattributed rather than quietly listed as fine.

  python3 scripts/build_catalog.py        # write data/_catalog.json
  python3 scripts/build_catalog.py --check # exit 1 if anything is unattributed
"""
import glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SCRIPTS = os.path.join(ROOT, "scripts")
SKIP = {"_catalog.json", "_fetch-report.json"}
# Files starting with "_" are probes and reports written by one-off scripts
# (data/_pharma-probe.json, ...). They are working notes, not datasets.
SKIP_PREFIX = "_"

# Datasets that are not produced by any script — pulled by hand and committed.
# They cannot self-refresh, so they carry an explicit as-of and a refresh note.
MANUAL = {
    "data/glp1-valuation.json": {
        "source": "Company fundamentals and consensus estimates via Bigdata.com",
        "as_of": "2026-08-05",
        "refresh": "manual — re-pull via the Bigdata.com connector; not on the cron",
        "note": "Trailing multiples are company-level and on reported earnings; "
                "consensus growth is on an adjusted basis. Basis differs by company "
                "(TTM for one, FY2025 for the rest) and is carried per row.",
    },
}

# YYYY, YYYY-MM, YYYY-MM-DD, and Eurostat's YYYY-Qn / YYYY-Sn
DATE = re.compile(r"^\d{4}(-(\d{2}|Q\d|S\d))?(-\d{2})?$")


def git_last_commit(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", path],
                             cwd=ROOT, capture_output=True, text=True, timeout=20)
        return (out.stdout.strip() or None)
    except Exception:
        return None


def producer_script(fname):
    """Which script writes this file? Only counts a script that also writes JSON."""
    hits = []
    for s in sorted(glob.glob(os.path.join(SCRIPTS, "*.py"))):
        try:
            src = open(s, encoding="utf-8").read()
        except Exception:
            continue
        if fname in src and ("json.dump" in src or "to_json" in src):
            hits.append(os.path.basename(s))
    return hits


def describe(obj):
    """Shape, series count, observation count and coverage — without assuming a schema."""
    def span(d):
        ks = [str(k) for k in d if DATE.match(str(k))]
        return (min(ks), max(ks)) if ks else None

    if not isinstance(obj, dict):
        return {"shape": type(obj).__name__, "series": None, "observations": None,
                "coverage": None}

    def table(t):
        """columns + rows, first column is the date (the cattle price tables)."""
        cols, rows = t.get("columns") or [], t.get("rows") or []
        dates = [str(r[0]) for r in rows if r and DATE.match(str(r[0]))]
        return {"series": max(len(cols) - 1, 0), "observations": len(rows),
                "coverage": {"first": min(dates), "last": max(dates)} if dates else None}

    if isinstance(obj.get("columns"), list) and isinstance(obj.get("rows"), list):
        return {"shape": "table", **table(obj)}

    body = None
    for key in ("series", "shares", "regions", "countries", "groups", "molecules"):
        if isinstance(obj.get(key), (dict, list)):
            body, shape = obj[key], key
            break
    else:
        body, shape = obj, "bespoke"

    if isinstance(body, list):
        return {"shape": shape, "series": len(body), "observations": len(body),
                "coverage": None}

    nseries, nobs, first, last = 0, 0, None, None
    for v in body.values():
        if isinstance(v, dict) and isinstance(v.get("rows"), list):   # regions of tables
            t = table(v)
            nseries += t["series"]
            nobs += t["observations"]
            if t["coverage"]:
                first = t["coverage"]["first"] if first is None else min(first, t["coverage"]["first"])
                last = t["coverage"]["last"] if last is None else max(last, t["coverage"]["last"])
        elif isinstance(v, dict):
            nseries += 1
            nobs += len(v)
            sp = span(v)
            if sp:
                first = sp[0] if first is None else min(first, sp[0])
                last = sp[1] if last is None else max(last, sp[1])
        else:
            nobs += 1
    sp_top = span(body)
    if not first and sp_top:
        first, last = sp_top
        nseries = 1
    return {"shape": shape, "series": nseries or len(body), "observations": nobs,
            "coverage": {"first": first, "last": last} if first else None}


MAX_KEYS = 100


def series_keys(obj):
    """Top-level series names, so a search over the catalog can hit 'hicp' or 'TR'.

    For the fetch.py shape that is the keys of "series"; for a table it is the
    column names after the date; for regions/shares/countries it is the region
    or country codes. Capped — the MCP server lists the full set on demand.
    """
    if not isinstance(obj, dict):
        return []
    if isinstance(obj.get("columns"), list):
        return [str(c) for c in obj["columns"][1:]][:MAX_KEYS]
    for key in ("series", "shares", "regions", "countries", "groups"):
        body = obj.get(key)
        if isinstance(body, dict):
            return [str(k) for k in body][:MAX_KEYS]
    return []


def main():
    cfg = json.load(open(os.path.join(ROOT, "data-sources.json")))["sources"]
    by_out = {s["out"]: s for s in cfg}

    entries, unattributed = [], []
    for path in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        base = os.path.basename(path)
        if base in SKIP or base.startswith(SKIP_PREFIX):
            continue
        rel = "data/" + base
        try:
            obj = json.load(open(path, encoding="utf-8"))
        except Exception as ex:
            entries.append({"file": rel, "error": f"{type(ex).__name__}: {ex}"})
            continue

        e = {"file": rel, "bytes": os.path.getsize(path)}
        e.update(describe(obj))
        e["series_keys"] = series_keys(obj)
        e["last_commit"] = git_last_commit(rel)

        if rel in by_out:                                   # fetch.py, on the cron
            s = by_out[rel]
            e.update(provenance="pipeline", producer=s["name"],
                     provider=s.get("provider"), auto_refresh=True,
                     source=s.get("source") or obj.get("source"),
                     note=s.get("note"))
        elif rel in MANUAL:                                 # pulled by hand
            m = MANUAL[rel]
            e.update(provenance="manual", producer="manual pull", auto_refresh=False,
                     source=m["source"], note=m["note"], as_of=m["as_of"],
                     refresh=m["refresh"])
        else:
            scripts = producer_script(base)
            if scripts:                                     # another script writes it
                e.update(provenance="script", producer=", ".join(scripts),
                         auto_refresh=False,
                         source=obj.get("source") if isinstance(obj, dict) else None,
                         note=obj.get("note") if isinstance(obj, dict) else None)
            else:                                           # nothing claims it
                e.update(provenance="unattributed", producer=None, auto_refresh=False,
                         source=obj.get("source") if isinstance(obj, dict) else None,
                         note="No script writes this file and it is not in "
                              "data-sources.json. Provenance unknown — verify or remove.")
                unattributed.append(rel)
        entries.append(e)

    counts = {}
    for e in entries:
        counts[e.get("provenance", "error")] = counts.get(e.get("provenance", "error"), 0) + 1

    out = {
        "_readme": "Index of every dataset in data/. Written by scripts/build_catalog.py. "
                   "provenance: pipeline = fetched by scripts/fetch.py on a schedule; "
                   "script = written by another script, run by hand; "
                   "manual = pulled by hand, cannot self-refresh; "
                   "unattributed = nothing claims it, treat with suspicion.",
        "generated_by": "scripts/build_catalog.py",
        "totals": {"datasets": len(entries), "by_provenance": counts,
                   "observations": sum(e.get("observations") or 0 for e in entries)},
        "datasets": entries,
    }
    with open(os.path.join(DATA, "_catalog.json"), "w") as f:
        json.dump(out, f, indent=1)

    print(f"catalogued {len(entries)} datasets · "
          + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"total observations: {out['totals']['observations']:,}")
    if unattributed:
        print(f"\nUNATTRIBUTED ({len(unattributed)}) — nothing writes these:")
        for u in unattributed:
            print("   ", u)
    if "--check" in sys.argv and unattributed:
        sys.exit(1)


if __name__ == "__main__":
    main()
