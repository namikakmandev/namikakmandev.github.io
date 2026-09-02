#!/usr/bin/env python3
"""Which shops publish a compare-at price?     -> data/_compare-at-probe.json

A campaign is only measurable as an episode when the shop states BOTH numbers
itself: what it is charging, and what it says the price normally is. One venue
in this tracker does that today (Cobasi, VTEX ListPrice), so every campaign the
study can show is Brazilian - which says nothing about Brazil and everything
about our extraction.

This asks the question for every venue page in the register, and it asks it the
way the rest of this pipeline asks questions: from the page, with the evidence
kept. For each page it records which compare-at shapes matched and the text
around each match, so a person can confirm the number is a struck-through
regular price and not a bundle, a unit rate, or the price of a related item.

It publishes no price and writes nothing into the study. A parser gets written
against the dump, per venue, once the dump proves the field exists.

Shapes tested (a shop can match several; the window says which is real):
  vtex-listprice     "listPrice": 23499        VTEX, in centavos or units
  shopify-compare    compare_at_price          Shopify variant JSON
  jsonld-listprice   priceSpecification        schema.org
  woo-del-ins        <del>..</del><ins>..      WooCommerce sale markup
  presta-regular     .regular-price            PrestaShop
  struck-generic     <del>, <s>, line-through  anything else that strikes a price

Run on a runner: the dev sandbox reaches no retail host.
"""
import gzip, io, json, os, re, sys, time, urllib.error, urllib.request

REG = "data/pricescraper-venues.json"
OUT = "data/_compare-at-probe.json"
CAP = 3 * 1024 * 1024
PAUSE = 1.5                     # between pages, so one shop is never hammered
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      "Accept-Encoding": "gzip"}

SHAPES = [
    ("vtex-listprice",   r'"[Ll]ist[Pp]rice"\s*:\s*([0-9]+(?:\.[0-9]+)?)'),
    ("shopify-compare",  r'"compare_at_price"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?'),
    ("jsonld-listprice", r'"(?:listPrice|highPrice|priceSpecification)"\s*:\s*[^,}]{0,80}'),
    ("woo-del-ins",      r'<del[^>]*>.{0,300}?</del>\s*<ins[^>]*>'),
    ("presta-regular",   r'class="[^"]*(?:regular-price|product-discount|old-price)[^"]*"'),
    ("struck-generic",   r'<(?:del|s)\b[^>]*>|text-decoration:\s*line-through'),
]
# A number that is struck through is only a compare-at if it is ABOVE the
# selling price; these windows let a person check that without refetching.
WINDOW = 220


def get(url, timeout=45, tries=2):
    last = None
    for i in range(tries):
        if i:
            time.sleep(4 * (2 ** (i - 1)))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(CAP + 1)
                if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                    try:
                        body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
                    except OSError:
                        pass
                return r.status, body[:CAP]
        except Exception as ex:
            last = ex
    raise last


def shapes_in(text):
    found = {}
    for name, pat in SHAPES:
        wins = []
        for m in re.finditer(pat, text, re.I | re.S):
            s = re.sub(r"\s+", " ", text[max(0, m.start() - WINDOW):m.end() + WINDOW])
            wins.append(s[:2 * WINDOW + 120])
            if len(wins) >= 3:
                break
        if wins:
            found[name] = wins
    return found


def main():
    reg = json.load(open(REG))["venues"]
    only = set(sys.argv[1:])
    doc = {"probe": "compare-at price availability",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "question": ("does this shop publish its own compare-at price, so a campaign "
                        "is measurable as an episode rather than guessed from a fall?"),
           "venues": {}}
    os.makedirs("data", exist_ok=True)

    for key, v in reg.items():
        if only and key not in only:
            continue
        rec = {"name": v["name"], "country": v["country"], "pages": []}
        # One page per product is enough to answer the question; a shop does not
        # change platform between its own product pages.
        seen_products = set()
        for pg in v["pages"]:
            if pg["product"] in seen_products:
                continue
            seen_products.add(pg["product"])
            if len(rec["pages"]) >= 2:
                break
            p = {"product": pg["product"], "url": pg["url"]}
            try:
                status, blob = get(pg["url"])
                text = blob.decode("utf-8", "replace")
                p["status"], p["bytes"] = status, len(blob)
                p["shapes"] = shapes_in(text)
                # Shopify hands the whole variant list over on a sibling route,
                # which is the cleanest compare-at there is; ask for it when the
                # page looks like Shopify at all.
                if "/products/" in pg["url"] and ("Shopify" in text or "shopify" in text):
                    try:
                        js = pg["url"].split("?")[0].rstrip("/") + ".js"
                        st2, b2 = get(js, tries=1)
                        d2 = json.loads(b2.decode("utf-8", "replace"))
                        p["shopify_js"] = {"status": st2, "variants": [
                            {"title": x.get("title"), "price": x.get("price"),
                             "compare_at_price": x.get("compare_at_price"),
                             "available": x.get("available")}
                            for x in (d2.get("variants") or [])[:12]]}
                    except Exception as ex2:
                        p["shopify_js_error"] = f"{type(ex2).__name__}: {ex2}"
            except Exception as ex:
                p["error"] = f"{type(ex).__name__}: {ex}"
            rec["pages"].append(p)
            print(f"{key:14}{p['product']:18}{p.get('status', p.get('error', ''))} "
                  f"{','.join((p.get('shapes') or {}).keys()) or '-'}", flush=True)
            time.sleep(PAUSE)
        # A venue counts as ANSWERING only if a shape carrying a number matched;
        # a bare <del> proves markup, not a price.
        numeric = {"vtex-listprice", "shopify-compare", "jsonld-listprice"}
        rec["has_numeric_compare_at"] = any(
            set((p.get("shapes") or {}).keys()) & numeric
            or any(x.get("compare_at_price") for x in (p.get("shopify_js") or {}).get("variants", []))
            for p in rec["pages"])
        doc["venues"][key] = rec

    doc["summary"] = {
        "venues_probed": len(doc["venues"]),
        "with_numeric_compare_at": sorted(k for k, r in doc["venues"].items()
                                          if r["has_numeric_compare_at"]),
        "unreachable": sorted(k for k, r in doc["venues"].items()
                              if all("error" in p for p in r["pages"]) and r["pages"]),
    }
    json.dump(doc, open(OUT, "w"), indent=1, ensure_ascii=False)
    print("\nwrote", OUT)
    print("compare-at found at:", ", ".join(doc["summary"]["with_numeric_compare_at"]) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
