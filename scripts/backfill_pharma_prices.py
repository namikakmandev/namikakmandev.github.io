#!/usr/bin/env python3
"""Backfill pharma price history from Wayback Machine snapshots.

For each non-optional tracker target, pulls the Internet Archive's monthly
snapshots of the SAME product page (CDX API, collapsed to one per month),
runs the SAME extractors the daily scraper uses, and inserts observations
dated by snapshot capture date. This turns day-one charts into real price
evolution wherever the archive has the page.

Guards:
  * Shopify live-JSON extraction is disabled (allow_shopify=False) — it would
    stamp TODAY's price onto a historical date. Archived HTML only.
  * A (date, sku, venue) that already exists is never overwritten, so the
    live daily scrape always wins over the archive.
  * Snapshots are capped (MAX_SNAPSHOTS per target, from 2016) and fetched
    politely; a failed or unparseable snapshot is skipped and counted.
  * Backfilled rows carry "hist": true and "+wayback" on the method so they
    are distinguishable from live observations forever.
"""

import json
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import fetch_pharma_prices as fp

CDX = "https://web.archive.org/cdx/search/cdx"
MAX_SNAPSHOTS = 36
FROM_YEAR = "2016"


def snapshots_for(session, url):
    try:
        r = session.get(CDX, params={
            "url": url, "output": "json", "fl": "timestamp,statuscode",
            "filter": "statuscode:200", "collapse": "timestamp:6",
            "from": FROM_YEAR, "limit": str(MAX_SNAPSHOTS + 20),
        }, timeout=60)
        if r.status_code != 200:
            return []
        rows = r.json()
        return [row[0] for row in rows[1:]][:MAX_SNAPSHOTS]
    except (requests.RequestException, ValueError):
        return []


def fetch_snapshot(session, ts, url):
    # id_ serves the original bytes without the wayback toolbar/rewrites
    try:
        r = session.get(f"https://web.archive.org/web/{ts}id_/{url}",
                        headers=fp.HEADERS, timeout=60)
        if r.status_code != 200:
            return None
        return r.text
    except requests.RequestException:
        return None


def main():
    session = requests.Session()
    store = json.loads(fp.DATA.read_text())
    assert store.get("schema") == 2
    have = {(o["d"], o["sku"], o["venue"]) for o in store["observations"]}

    report = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "mode": "wayback-backfill", "targets": []}
    added_total = 0

    for t in fp.TARGETS:
        if t.get("optional"):
            continue
        venue = fp.VENUES[t["venue"]]
        stamps = snapshots_for(session, t["url"])
        entry = {"product": t["product"], "venue": t["venue"],
                 "snapshots": len(stamps), "added": 0, "empty": 0}
        for ts in stamps:
            day = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
            html = fetch_snapshot(session, ts, t["url"])
            time.sleep(1.5)
            if html is None:
                entry["empty"] += 1
                continue
            if t["kind"] == "sku":
                one = fp.scrape_sku(html, t, venue["currency"])
                rows = [one] if one else []
            else:
                rows = fp.scrape_multi(session, html, t, venue["currency"],
                                       allow_shopify=False)
            if not rows:
                entry["empty"] += 1
                continue
            for r in rows:
                sku = fp.sku_id(t["product"], t["form"], r.get("mg"))
                key = (day, sku, t["venue"])
                if key in have:
                    continue
                have.add(key)
                n = r.get("n") or 1
                store["observations"].append({
                    "d": day, "sku": sku, "product": t["product"],
                    "form": t["form"], "mg": r.get("mg"), "n": n,
                    "venue": t["venue"], "country": venue["country"],
                    "cur": venue["currency"], "price": round(r["price"], 2),
                    "unit": round(r["price"] / n, 4),
                    "method": r["method"] + "+wayback", "hist": True,
                })
                entry["added"] += 1
                added_total += 1
        report["targets"].append(entry)
        print(f"{t['product']:17s} {t['venue']:10s} snaps={entry['snapshots']:3d} "
              f"added={entry['added']:3d} empty={entry['empty']:3d}")

    store["observations"].sort(key=lambda o: (o["d"], o["sku"], o["venue"]))
    store["meta"]["backfill"] = report["run"]
    fp.DATA.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
    fp.REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(f"\nbackfilled {added_total} historical observations")


if __name__ == "__main__":
    main()
