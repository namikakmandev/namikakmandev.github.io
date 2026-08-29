#!/usr/bin/env python3
"""Find prices that are parse artifacts rather than price movements.

The scraper already refuses a price it cannot attribute to a specific
strength. That stops a category page's minimum from entering as a new SKU,
but it does not stop a DECLARED SKU's page from yielding the wrong number on
one particular snapshot - a "Save $99" badge, a per-tablet figure on a page
priced per pack, an autoship rate. Those land inside an otherwise coherent
series and look like a price movement.

They are distinguishable from one, though. A real price change persists: the
new level is still there at the next observation. An artifact is a single
point sitting far from BOTH of its neighbours in the same
(venue, SKU, pack size) series, with the series closing back up around it.

  EntirelyPets Apoquel 16 mg x100:  ... 369.99, 99.00, 389.99 ...
  Diermedicatie Apoquel 16 mg x10:  ... 31.50, 2.95, 31.50 ...

Only interior points are judged, because an endpoint has nothing on one side
to bracket it and a genuine launch or clearance price would be indistinguish-
able from an artifact.

Neighbour comparison alone misses artifacts that repeat, though: Diermedicatie
served the same wrong number on two consecutive monthly snapshots, and each
one then had the other as a "neighbour" to hide behind. So a second test runs
on any series with four or more points and compares each point to the series
MEDIAN, which two bad points cannot drag. That test is off for short series,
where the median is not yet a stable idea of the price.

Neither test can see an artifact that lasts long enough to become the median,
and neither is a substitute for a real price falling by more than the factor -
which is why the factor is 2.5 and not something tighter. Run with --purge to
remove what it finds; without it the script only reports, on purpose.
"""

import json
import sys
from collections import defaultdict

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import fetch_pharma_prices as fp

FACTOR = 2.5          # how far from both neighbours counts as "not a movement"


def find(observations):
    series = defaultdict(list)
    for i, o in enumerate(observations):
        if o.get("price", 0) > 0 and o.get("unit"):
            series[(o["venue"], o["sku"], o.get("n"))].append((o["d"], o["unit"], i))

    flagged, seen = [], set()
    for key, pts in series.items():
        pts.sort()
        units = sorted(p[1] for p in pts)
        med = units[len(units) // 2] if len(units) % 2 else \
              (units[len(units) // 2 - 1] + units[len(units) // 2]) / 2

        for j in range(1, len(pts) - 1):
            prev, cur, nxt = pts[j - 1][1], pts[j][1], pts[j + 1][1]
            low = cur * FACTOR < min(prev, nxt)
            high = cur > max(prev, nxt) * FACTOR
            if low or high:
                flagged.append({
                    "venue": key[0], "sku": key[1], "n": key[2], "d": pts[j][0],
                    "unit": cur, "ref": f"{prev:.3f}/{nxt:.3f}", "test": "neighbours",
                    "kind": "dip" if low else "spike", "idx": pts[j][2],
                })
                seen.add(pts[j][2])

        if len(pts) < 4:
            continue
        for j in range(1, len(pts) - 1):        # interior only, same reasoning
            cur, idx = pts[j][1], pts[j][2]
            if idx in seen:
                continue
            low = cur * FACTOR < med
            high = cur > med * FACTOR
            if low or high:
                flagged.append({
                    "venue": key[0], "sku": key[1], "n": key[2], "d": pts[j][0],
                    "unit": cur, "ref": f"median {med:.3f}", "test": "median",
                    "kind": "dip" if low else "spike", "idx": idx,
                })
                seen.add(idx)
    return flagged


def main():
    purge = "--purge" in sys.argv
    store = json.loads(fp.DATA.read_text())
    obs = store["observations"]
    flagged = find(obs)

    for f in sorted(flagged, key=lambda x: (x["venue"], x["sku"], x["d"])):
        print(f"{f['kind']:5s} {f['venue']:13s} {f['sku']:26s} n={f['n']} {f['d']} "
              f"unit={f['unit']:8.3f}  vs {f['ref']:18s} [{f['test']}]")
    print(f"\n{len(flagged)} points more than {FACTOR}x from their own series")

    if purge and flagged:
        drop = {f["idx"] for f in flagged}
        store["observations"] = [o for i, o in enumerate(obs) if i not in drop]
        store["meta"]["outliers_purged"] = store["meta"].get("outliers_purged", 0) + len(drop)
        fp.DATA.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
        print(f"purged {len(drop)}; {len(store['observations'])} observations remain")
    elif flagged:
        print("(report only - pass --purge to remove them)")


if __name__ == "__main__":
    main()
