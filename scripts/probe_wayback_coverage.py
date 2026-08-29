#!/usr/bin/env python3
"""Ask the Internet Archive what it actually holds for each tracked venue.

The first backfill pass asked the CDX index for the EXACT product URL we
scrape today, and 89 of 129 targets came back with zero snapshots. For every
continental European venue the count was zero across all products, which
leaves two very different explanations that the run could not tell apart:

  (a) the archive never crawled that shop at all - a structural blank, the
      same kind of finding as Poland having no public retail prices; or
  (b) the archive holds the shop, but under a different product URL than the
      one live today, because the shop re-slugged, moved to a new platform,
      or serves the page from a query string.

(b) is recoverable and (a) is not, and the difference decides whether the
European cross-country ranking can ever be more than one day deep. So this
probe asks two questions per venue instead of one:

  1. is the DOMAIN in the archive at all, and from when
  2. which archived URLs anywhere on that domain mention one of the five
     products, regardless of whether they match a URL we track

Output is data/_wayback-coverage.json - a report, not price data. Nothing
here writes an observation; discovered URLs become backfill candidates only
after a human reads the report, which is the same rule the discover mode
follows for live pages.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import fetch_pharma_prices as fp

CDX = "https://web.archive.org/cdx/search/cdx"
OUT = fp.ROOT / "data" / "_wayback-coverage.json"
SLUGS = ["apoquel", "cytopoint", "zenrelia", "numelvi", "lokivetmab", "oclacitinib"]
PAUSE = 2.0


def cdx(session, **params):
    params.setdefault("output", "json")
    for attempt in range(3):
        try:
            r = session.get(CDX, params=params, timeout=90)
            if r.status_code == 200 and r.text.strip():
                rows = r.json()
                return rows[1:] if rows else []
            if r.status_code == 200:
                return []
        except (requests.RequestException, ValueError):
            pass
        time.sleep(4 * (attempt + 1))
    return None            # None means "asked and failed", [] means "asked, nothing there"


def hosts_for_venue():
    """Map venue key -> the hosts we actually scrape for it."""
    hosts = {}
    for t in fp.TARGETS:
        h = urlsplit(t["url"]).netloc.lower()
        hosts.setdefault(t["venue"], set()).add(h)
    return {k: sorted(v) for k, v in hosts.items()}


def main():
    session = requests.Session()
    session.headers.update(fp.HEADERS)
    venue_hosts = hosts_for_venue()
    tracked = {}
    for t in fp.TARGETS:
        tracked.setdefault(t["venue"], set()).add(t["url"])

    report = {
        "run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "wayback-coverage-probe",
        "question": "is each venue absent from the archive, or present under URLs we do not track?",
        "venues": [],
    }

    for venue in sorted(venue_hosts):
        meta = fp.VENUES[venue]
        entry = {"venue": venue, "name": meta["name"], "country": meta["country"],
                 "hosts": venue_hosts[venue], "domain_captures": 0, "earliest": None,
                 "latest": None, "product_urls": [], "tracked_urls_archived": 0,
                 "error": None}

        for host in venue_hosts[venue]:
            # 1. is the domain archived at all, and over what span
            span = cdx(session, url=host, matchType="domain", fl="timestamp",
                       filter="statuscode:200", collapse="timestamp:4", limit="200")
            time.sleep(PAUSE)
            if span is None:
                entry["error"] = "cdx unreachable"
                continue
            stamps = sorted(r[0] for r in span if r and r[0])
            if stamps:
                entry["domain_captures"] += len(stamps)
                lo, hi = stamps[0][:8], stamps[-1][:8]
                entry["earliest"] = min(entry["earliest"] or lo, lo)
                entry["latest"] = max(entry["latest"] or hi, hi)

            # 2. which archived URLs on that domain name one of the products
            for slug in SLUGS:
                rows = cdx(session, url=host, matchType="domain",
                           fl="original,timestamp", filter=["statuscode:200",
                           f"original:(?i).*{slug}.*"], collapse="urlkey", limit="60")
                time.sleep(PAUSE)
                if not rows:
                    continue
                for orig, ts in ((r[0], r[1]) for r in rows if len(r) >= 2):
                    entry["product_urls"].append({"url": orig, "seen": ts[:8], "slug": slug})

        # de-duplicate, and separate "already tracked" from "new to us"
        seen, uniq = set(), []
        for pu in entry["product_urls"]:
            if pu["url"] in seen:
                continue
            seen.add(pu["url"])
            pu["tracked"] = pu["url"] in tracked.get(venue, set())
            uniq.append(pu)
        uniq.sort(key=lambda x: x["url"])
        entry["product_urls"] = uniq
        entry["tracked_urls_archived"] = sum(1 for p in uniq if p["tracked"])
        entry["untracked_archived"] = sum(1 for p in uniq if not p["tracked"])

        verdict = ("cdx unreachable" if entry["error"]
                   else "absent from the archive" if not entry["domain_captures"]
                   else "archived, but no product page in it" if not uniq
                   else "archived with product pages we do not track" if entry["untracked_archived"]
                   else "archived, all product pages already tracked")
        entry["verdict"] = verdict
        report["venues"].append(entry)
        print(f"{venue:16s} {meta['country']} caps={entry['domain_captures']:4d} "
              f"prod={len(uniq):3d} new={entry.get('untracked_archived', 0):3d}  {verdict}")

    by_verdict = {}
    for e in report["venues"]:
        by_verdict[e["verdict"]] = by_verdict.get(e["verdict"], 0) + 1
    report["summary"] = by_verdict
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print("\n" + json.dumps(by_verdict, indent=1))


if __name__ == "__main__":
    main()
