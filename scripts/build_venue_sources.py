"""Publish the scraper's own target list so the report can cite its sources.

The observation store records WHICH venue a price came from, but not the page
it was read off. That page is the citation: without it "Pet Drugs Online,
GBP 2.05" is an assertion the reader has to take on trust, and cannot check.

The list is generated from fetch_pharma_prices.TARGETS rather than written by
hand, so a link can never drift from the URL the scraper actually fetched. If
a target is retired from the roster, its link disappears with it.

Optional targets (probes that may 404) are marked, and so is whether the venue
still appears in the current data - a citation to a shop we no longer read
should not look like a live source.

Output: data/venue-sources.json
"""
import json
import pathlib
import sys
from collections import defaultdict
from urllib.parse import urlsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_pharma_prices as fp

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "venue-sources.json"
STORE = ROOT / "data" / "pharma-prices.json"


def main():
    live = set()
    if STORE.exists():
        obs = json.loads(STORE.read_text()).get("observations", [])
        if obs:
            latest = max(o["d"] for o in obs)
            live = {o["venue"] for o in obs if o["d"] == latest}

    pages = defaultdict(list)
    for t in fp.TARGETS:
        v = t.get("venue")
        if not v or not t.get("url"):
            continue
        pages[v].append({
            "product": t.get("product"),
            "url": t["url"],
            "optional": bool(t.get("optional")),
        })

    out = {}
    for vid, meta in fp.VENUES.items():
        rows = sorted(pages.get(vid, []), key=lambda r: (r["product"] or "", r["url"]))
        if not rows:
            continue
        # The shop's own root, derived from the first target rather than stored
        # separately, so it cannot disagree with the pages beneath it.
        parts = urlsplit(rows[0]["url"])
        out[vid] = {
            "name": meta.get("name", vid),
            "country": meta.get("country"),
            "site": f"{parts.scheme}://{parts.netloc}",
            "host": parts.netloc,
            "live": vid in live,
            "pages": rows,
        }

    OUT.write_text(json.dumps({
        "note": "Generated from scripts/fetch_pharma_prices.py TARGETS. Every URL here "
                "is a page the scraper actually requests, so the citation and the "
                "measurement cannot drift apart.",
        "venues": dict(sorted(out.items())),
    }, indent=1, ensure_ascii=False) + "\n")
    n = sum(len(v["pages"]) for v in out.values())
    print(f"wrote {OUT.name}: {len(out)} venues, {n} source pages, "
          f"{sum(1 for v in out.values() if v['live'])} live in the latest scrape")


if __name__ == "__main__":
    main()
