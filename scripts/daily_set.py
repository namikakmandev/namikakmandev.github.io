#!/usr/bin/env python3
"""The datasets worth refreshing every day: those whose stored series are daily, weekly or
monthly, from providers that are cheap to ask again. Annual and quarterly sources change
a few times a year and wait for the monthly full run. Prints space-separated names for
the fetch workflow's daily schedule.

    python3 scripts/daily_set.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_PROVIDERS = {"fred", "evds", "eurostat", "ecb", "yahoo", "csv", "worldbank"}
SKIP = {"valuation-multiples"}   # Yahoo rate-limits the quote endpoint; once a month is enough


def main():
    cfg = json.load(open(os.path.join(ROOT, "data-sources.json")))["sources"]
    catalog = {d["file"]: d for d in json.load(open(os.path.join(ROOT, "data", "_catalog.json")))["datasets"]}
    names = []
    for s in cfg:
        if s.get("enabled") is False or s["name"] in SKIP or s.get("provider") not in DAILY_PROVIDERS:
            continue
        cat = catalog.get(s.get("out", ""))
        last = str(((cat or {}).get("coverage") or {}).get("last") or "")
        if re.match(r"^\d{4}-\d{2}(-\d{2})?$", last):   # monthly or daily keys
            names.append(s["name"])
    print(" ".join(names))


if __name__ == "__main__":
    main()
