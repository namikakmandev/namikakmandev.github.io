#!/usr/bin/env python3
"""Fold the repo's pricescraper data files into the published tracker page.

    python3 scripts/refresh_pricescraper_artifact.py IN.html OUT.html [REPO]

IN.html is the current published Animal Pharma Price Tracker artifact (as
saved by an artifact read). The script merges data/pricescraper-daily.json
and data/pricescraper-history.json into the page's embedded-data JSON —
observations only, deduplicated by (day, venue, sku, pack size) with the
repo files winning; pack size is part of the key because one venue can
sell the same SKU in two pack sizes on the same day. meta.updated is
bumped to the daily file's timestamp, and OUT.html is written.

It changes nothing else: layout, notes, queue, FX and every other market's
data pass through byte-identical. Publishing decisions belong to the caller:

    exit 0, prints "CHANGED new=<n>"   -> republish OUT.html
    exit 0, prints "UNCHANGED"         -> do not publish, nothing new
    exit 2                             -> refuse: the merge would REMOVE
                                          observations or the page has no
                                          embedded data; never publish this

Used by the daily artifact-refresh Routine; safe to run by hand.
"""
import json, os, re, sys


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    repo = sys.argv[3] if len(sys.argv) > 3 else "."

    page = open(src, encoding="utf-8").read()
    m = re.search(r'(<script type="application/json" id="embedded-data">)(.*?)(</script>)',
                  page, re.S)
    if not m:
        print("REFUSE: no embedded-data block in", src)
        return 2
    d = json.loads(m.group(2))
    obs = d["data"]["observations"]
    before = len(obs)

    key = lambda o: (o["d"], o["venue"], o["sku"], o.get("n"))
    have = {key(o): o for o in obs}
    incoming = {}
    for fn in ("data/pricescraper-daily.json", "data/pricescraper-history.json"):
        path = os.path.join(repo, fn)
        if not os.path.exists(path):
            print(f"note: {fn} missing, skipped")
            continue
        f = json.load(open(path, encoding="utf-8"))
        for o in f.get("observations", []):
            incoming[key(o)] = o
        if fn.endswith("daily.json") and f.get("updated"):
            d["data"]["meta"]["updated"] = f["updated"].replace("Z", "+00:00")

    new_keys = [k for k in incoming if k not in have]
    changed_keys = [k for k in incoming
                    if k in have and have[k] != incoming[k]]
    have.update(incoming)
    merged = sorted(have.values(), key=lambda o: (o["d"], o["venue"], o["sku"]))

    if len(merged) < before:
        print(f"REFUSE: merge would shrink observations {before} -> {len(merged)}")
        return 2

    d["data"]["observations"] = merged
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    open(dst, "w", encoding="utf-8").write(page[:m.start(2)] + blob + page[m.end(2):])

    if new_keys or changed_keys:
        print(f"CHANGED new={len(new_keys)} revised={len(changed_keys)} "
              f"total={len(merged)} updated={d['data']['meta']['updated']}")
    else:
        print(f"UNCHANGED total={len(merged)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
