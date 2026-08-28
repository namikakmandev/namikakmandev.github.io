#!/usr/bin/env python3
"""Daily price scraper for 5 canine dermatology (animal pharma) products.

Tracks list prices from US online pet pharmacies:

  cytopoint          PetVM (fallback Bandana Rx)
  apoquel            PetVM (fallback California Pet Pharmacy, per-tablet)
  apoquel-chewable   California Pet Pharmacy (fallbacks Heartland, EntirelyPets Rx)
  numelvi            Heartland Vet Supply (fallback PetRx / Shopify JSON)
  zenrelia           PetVM (fallback EntirelyPets Rx)

Extraction is layered because store platforms differ (PrestaShop,
AspDotNetStorefront, Magento, Shopify): JSON-LD Product offers first, then
price meta tags, then a Shopify /products/*.js endpoint, then a visible-price
regex as last resort. Whatever method wins is recorded in the report so a
silent selector rot shows up in data/_pharma-prices-report.json instead of as
quietly wrong numbers.

Appends one point per product per day to data/pharma-prices.json (re-running
the same day overwrites that day's point). A failed product keeps its history
untouched; the failure lands in the report file.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "pharma-prices.json"
REPORT = ROOT / "data" / "_pharma-prices-report.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

PRODUCTS = [
    {
        "id": "cytopoint",
        "name": "Cytopoint",
        "maker": "Zoetis",
        "unit": "per vial (10-40 mg)",
        "sources": [
            {"store": "PetVM", "url": "https://petvm.com/skin-coat/458-cytopoint-for-dogs.html"},
            {"store": "Bandana Rx", "url": "https://bandanarx.com/skin-coat/458-cytopoint-for-dogs.html"},
        ],
    },
    {
        "id": "apoquel",
        "name": "Apoquel",
        "maker": "Zoetis",
        "unit": "per tablet",
        "sources": [
            {"store": "PetVM", "url": "https://petvm.com/skin-coat/318-apoquel.html"},
            {"store": "California Pet Pharmacy", "url": "https://www.californiapetpharmacy.com/apoquel-16mg-per-tablet.html"},
        ],
    },
    {
        "id": "apoquel-chewable",
        "name": "Apoquel Chewable",
        "maker": "Zoetis",
        "unit": "per chewable (16 mg)",
        "sources": [
            {"store": "California Pet Pharmacy", "url": "https://www.californiapetpharmacy.com/apoquel-chewable-16mg-per-chewable.html"},
            {"store": "Heartland Vet Supply", "url": "https://www.heartlandvetsupply.com/p-6816-apoquel-oclacitinib-chewable-tablets-for-dogs.aspx"},
            {"store": "EntirelyPets Rx", "url": "https://entirelypetspharmacy.com/apoquel-chewable-tablets-16mg-30-tablet.html"},
        ],
    },
    {
        "id": "numelvi",
        "name": "Numelvi",
        "maker": "Merck",
        "unit": "page variants (per tablet to 30-ct bottle)",
        "sources": [
            {"store": "Heartland Vet Supply", "url": "https://www.heartlandvetsupply.com/p-7274-numelvi-atinvicitinib-tablets-for-dogs.aspx"},
            {"store": "PetRx", "url": "https://petrx.com/products/numelvi-atinvicitinib-tablets"},
        ],
    },
    {
        "id": "zenrelia",
        "name": "Zenrelia",
        "maker": "Elanco",
        "unit": "per tablet (4.8-15 mg strengths)",
        "sources": [
            {"store": "PetVM", "url": "https://petvm.com/skin-coat/511-zenrelia-ilunocitnib-tablets.html"},
            {"store": "EntirelyPets Rx", "url": "https://entirelypetspharmacy.com/zenrelia-tablets-for-dogs.html"},
        ],
    },
]

# Sanity bounds: anything outside is treated as a mis-parse, not a price.
PRICE_MIN, PRICE_MAX = 1.0, 3000.0


def plausible(values):
    return sorted({round(float(v), 2) for v in values
                   if PRICE_MIN <= float(v) <= PRICE_MAX})


def walk_ldjson(node, out):
    """Collect offer prices from any schema.org Product/Offer structure."""
    if isinstance(node, list):
        for item in node:
            walk_ldjson(item, out)
        return
    if not isinstance(node, dict):
        return
    for key in ("price", "lowPrice", "highPrice"):
        val = node.get(key)
        if val not in (None, ""):
            try:
                out.append(float(str(val).replace(",", "").replace("$", "")))
            except ValueError:
                pass
    for key in ("@graph", "offers", "itemListElement", "item", "hasVariant", "model"):
        if key in node:
            walk_ldjson(node[key], out)


def extract_ldjson(html):
    prices = []
    for match in re.finditer(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.S | re.I):
        raw = match.group(1).strip()
        try:
            walk_ldjson(json.loads(raw), prices)
        except json.JSONDecodeError:
            # Some stores emit sloppy JSON-LD; grab price fields textually.
            prices += [p for p in re.findall(
                r'"(?:price|lowPrice|highPrice)"\s*:\s*"?([0-9][0-9,]*\.?[0-9]{0,2})',
                raw)]
    return plausible(prices)


def extract_meta(html):
    prices = re.findall(
        r'<meta[^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|og:price:amount|price)["\'][^>]+content=["\']\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})',
        html, re.I)
    prices += re.findall(
        r'<meta[^>]+content=["\']\$?\s*([0-9][0-9,]*\.[0-9]{2})["\'][^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|og:price:amount|price)["\']',
        html, re.I)
    return plausible(p.replace(",", "") for p in prices)


def extract_shopify(session, url):
    if "/products/" not in url:
        return []
    try:
        resp = session.get(url.split("?")[0] + ".js", headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return []
        product = resp.json()
        cents = [v.get("price") for v in product.get("variants", [])
                 if v.get("available", True) and v.get("price") is not None]
        return plausible(c / 100.0 for c in cents)
    except (requests.RequestException, ValueError):
        return []


def extract_inline_js(html):
    """Price fields inside inline scripts (PrestaShop, Magento configs)."""
    prices = re.findall(
        r'"(?:price|price_amount|productPrice|special_price|finalPrice)"\s*:\s*"?\$?([0-9][0-9,]*\.[0-9]{2})"?',
        html)
    return plausible(p.replace(",", "") for p in prices)


def extract_visible(html):
    """Last resort: $-amounts in the top chunk of the page body."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    prices = re.findall(r"\$\s*([0-9][0-9,]*\.[0-9]{2})", body[:40000])
    return plausible(p.replace(",", "") for p in prices)


def scrape_source(session, source):
    """Returns (result_dict_or_None, note). result has lo/hi/method."""
    shopify = extract_shopify(session, source["url"])
    if shopify:
        return {"lo": shopify[0], "hi": shopify[-1], "method": "shopify-json"}, "ok"

    try:
        resp = session.get(source["url"], headers=HEADERS, timeout=30)
    except requests.RequestException as exc:
        return None, f"request failed: {exc.__class__.__name__}: {exc}"
    if resp.status_code != 200:
        return None, f"http {resp.status_code}"
    html = resp.text

    for method, fn in (("ld+json", extract_ldjson),
                       ("meta", extract_meta),
                       ("inline-js", extract_inline_js),
                       ("visible-$", extract_visible)):
        prices = fn(html)
        if prices:
            return {"lo": prices[0], "hi": prices[-1], "method": method}, "ok"
    return None, "no price found in page"


def main():
    session = requests.Session()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if DATA.exists():
        store = json.loads(DATA.read_text())
    else:
        store = {"meta": {}, "history": {}}

    store["meta"] = {
        "title": "Animal pharma price tracker",
        "currency": "USD",
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "products": [{k: p[k] for k in ("id", "name", "maker", "unit")} |
                     {"sources": p["sources"]} for p in PRODUCTS],
    }

    report = {"run": store["meta"]["updated"], "date": today, "products": {}}
    failures = 0

    for product in PRODUCTS:
        entry = None
        attempts = []
        for source in product["sources"]:
            result, note = scrape_source(session, source)
            attempts.append({"store": source["store"], "url": source["url"], "note": note,
                             **({"method": result["method"],
                                 "lo": result["lo"], "hi": result["hi"]} if result else {})})
            if result:
                entry = {"d": today, "lo": result["lo"], "hi": result["hi"],
                         "store": source["store"], "method": result["method"]}
                break
            time.sleep(2)

        report["products"][product["id"]] = attempts
        history = store["history"].setdefault(product["id"], [])
        if entry:
            if history and history[-1]["d"] == today:
                history[-1] = entry
            else:
                history.append(entry)
            print(f"{product['id']:18s} ${entry['lo']:>8.2f} - ${entry['hi']:>8.2f}"
                  f"  [{entry['store']} / {entry['method']}]")
        else:
            failures += 1
            print(f"{product['id']:18s} FAILED ({attempts[-1]['note']})", file=sys.stderr)
        time.sleep(2)

    DATA.write_text(json.dumps(store, indent=1) + "\n")
    REPORT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"\nwrote {DATA.name} and {REPORT.name}"
          f" ({failures} of {len(PRODUCTS)} products failed)")
    # Fail the job only when nothing at all could be scraped.
    sys.exit(1 if failures == len(PRODUCTS) else 0)


if __name__ == "__main__":
    main()
