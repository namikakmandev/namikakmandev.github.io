#!/usr/bin/env python3
"""Backfill price history from the archived product URLs the probe found.

backfill_pharma_prices.py asks the archive for the exact URL we scrape today.
That works for shops whose URLs never moved, and returns nothing for the ones
that re-slugged or changed platform - which was every continental European
venue. probe_wayback_coverage.py found their pages under other URLs and
harvest_wayback_targets.py read the SKU out of each slug; this fetches them.

Each candidate is a fully declared SKU (product, form, strength, pack), so
the archived page only has to yield a price - the same rule the live scraper
follows for a "sku" target, and the reason a category page's minimum can
never sneak in here.

Duplicate listings are the one hazard the harvest cannot remove: Farmapets
has sixteen distinct URLs whose slugs all read "apoquel 16 mg 100 compresse",
one of them filed under ear-cleaning products. Rather than pick between them
arbitrarily, every URL is fetched and the LOWEST price wins the day, with the
number of contributing URLs and the high/low spread recorded so a duplicate
that is secretly a different product shows up as a wide spread instead of
disappearing into the series.
"""

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import fetch_pharma_prices as fp

CDX = "https://web.archive.org/cdx/search/cdx"
CANDIDATES = fp.ROOT / "data" / "_wayback-candidates.json"
OUT = fp.ROOT / "data" / "_wayback-harvest-report.json"
MAX_SNAPSHOTS = 24
FROM_YEAR = "2016"
PAUSE = 1.2


def snapshots_for(session, url):
    try:
        r = session.get(CDX, params={
            "url": url, "output": "json", "fl": "timestamp",
            "filter": "statuscode:200", "collapse": "timestamp:6",
            "from": FROM_YEAR, "limit": str(MAX_SNAPSHOTS + 10),
        }, timeout=90)
        if r.status_code != 200 or not r.text.strip():
            return []
        rows = r.json()
        return [row[0] for row in rows[1:]][:MAX_SNAPSHOTS]
    except (requests.RequestException, ValueError):
        return []


def fetch_snapshot(session, ts, url):
    try:
        r = session.get(f"https://web.archive.org/web/{ts}id_/{url}",
                        headers=fp.HEADERS, timeout=90)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def main():
    session = requests.Session()
    cand = json.loads(CANDIDATES.read_text())["candidates"]
    store = json.loads(fp.DATA.read_text())
    assert store.get("schema") == 2
    # pack size is part of a row's identity: the live scraper records Apoquel
    # 16 mg in 20s AND in 100s at one venue on one day, and sku_id carries only
    # product-form-strength. Leaving n out of the key pools two different goods.
    have = {(o["d"], o["sku"], o["venue"], o.get("n")) for o in store["observations"]}

    # (day, sku, venue, pack) -> prices seen across genuinely duplicate URLs
    pool = defaultdict(list)
    meta_of = {}
    report = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "mode": "wayback-harvest-backfill", "candidates": len(cand), "urls": []}

    for c in cand:
        venue = fp.VENUES[c["venue"]]
        t = {"product": c["product"], "form": c["form"], "mg": c["mg"],
             "n": c["n"], "url": c["url"], "kind": "sku", "venue": c["venue"]}
        stamps = snapshots_for(session, c["url"])
        time.sleep(PAUSE)
        row = {"venue": c["venue"], "country": c["country"], "product": c["product"],
               "mg": c["mg"], "n": c["n"], "snapshots": len(stamps), "priced": 0,
               "url": c["url"]}
        for ts in stamps:
            day = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
            html = fetch_snapshot(session, ts, c["url"])
            time.sleep(PAUSE)
            if html is None:
                continue
            one = fp.scrape_sku(html, t, venue["currency"])
            if not one or one.get("mg") is None:
                continue
            price = one["price"]
            if not (fp.PRICE_MIN <= price <= fp.PRICE_MAX):
                continue
            sku = fp.sku_id(c["product"], c["form"], c["mg"])
            key = (day, sku, c["venue"], c["n"])
            if key in have:                  # live data and earlier passes always win
                continue
            pool[key].append(price)
            meta_of[key] = (c, one["method"])
            row["priced"] += 1
        report["urls"].append(row)
        print(f"{c['country']} {c['venue']:14s} {c['product']:17s} {c['mg']:5.1f}mg "
              f"n={c['n']:3d} snaps={row['snapshots']:3d} priced={row['priced']:3d}")

    added, wide = 0, []
    for key, prices in sorted(pool.items()):
        day, sku, venue_key, _pack = key
        c, method = meta_of[key]
        lo, hi = min(prices), max(prices)
        if len(prices) > 1 and hi > lo * 1.5:
            wide.append({"day": day, "sku": sku, "venue": venue_key, "n": c["n"],
                         "urls": len(prices), "low": lo, "high": hi})
        store["observations"].append({
            "d": day, "sku": sku, "product": c["product"], "form": c["form"],
            "mg": c["mg"], "n": c["n"], "venue": venue_key,
            "country": fp.VENUES[venue_key]["country"],
            "cur": fp.VENUES[venue_key]["currency"], "price": round(lo, 2),
            "unit": round(lo / (c["n"] or 1), 4),
            "method": method + "+wayback-harvest", "hist": True,
            "dupes": len(prices) if len(prices) > 1 else None,
        })
        added += 1

    for o in store["observations"]:
        if o.get("dupes") is None:
            o.pop("dupes", None)

    store["observations"].sort(key=lambda o: (o["d"], o["sku"], o["venue"]))
    store["meta"]["harvest_backfill"] = report["run"]
    report["added"] = added
    report["wide_duplicate_spreads"] = wide
    fp.DATA.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(f"\nadded {added} historical observations; "
          f"{len(wide)} day/SKU keys had duplicate URLs disagreeing by >50%")


if __name__ == "__main__":
    main()
