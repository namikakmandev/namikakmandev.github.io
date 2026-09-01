#!/usr/bin/env python3
"""Discover-mode probe of the pricescraper candidate queue.
                                    -> data/_pricescraper-queue-probe.json

The animal-pharma price tracker holds a queue of candidate venues for Brazil,
Canada, Japan and China. Its own rule: no venue is promoted until the scraper
has fetched the real page, the dump has been read, and a parser is written
against what the page actually returns. The dev sandbox blocks every retail
domain at the egress proxy, so this runs where the network works.

This parses nothing into the tracker. It records, for each candidate URL:

  - status, final URL after redirects, content type, capped byte count
  - the page <title>
  - every JSON-LD block, parsed if it parses, verbatim head if it does not
  - og:price / itemprop price signals outside JSON-LD
  - gate signals: does the page smell like a captcha, login wall or bot check

Lessons inherited from scripts/probe_pharma.py: a 200 is not access, so heads
and byte counts are recorded rather than trusted; every read is capped and the
cap is reported.
"""
import gzip, io, json, os, re, sys, time, urllib.error, urllib.request

OUT = "data/_pricescraper-queue-probe.json"
CAP = 2 * 1024 * 1024
# A browser-shaped UA: several of these shops answer python-urllib's default
# with a 403 that says nothing about what a real visitor sees.
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en;q=0.8,pt-BR;q=0.6,ja;q=0.4,zh-CN;q=0.4",
    "Accept-Encoding": "gzip",
}

# The queue, copied verbatim from the tracker's embedded data (queue.queue),
# minus the recorded exclusions, which are decisions not to fetch at all.
QUEUE = [
    {"country": "BR", "currency": "BRL", "venue_id": "cobasi",
     "name": "Cobasi", "platform_guess": "VTEX",
     "urls": [
        {"product": "apoquel", "mg": 3.6, "n": 20,
         "url": "https://www.cobasi.com.br/apoquel-dermatologico-zoetis-para-cachorro-3-6-mg-3816434/p"},
        {"product": "apoquel", "mg": 5.4, "n": None,
         "url": "https://www.cobasi.com.br/apoquel-dermatologico-zoetis-para-cachorro-54mg-3816442/p"},
        {"product": "apoquel", "mg": 16, "n": None,
         "url": "https://www.cobasi.com.br/-apoquel-dermatologico-zoetis-para-cachorro-3816450/p"},
     ]},
    {"country": "BR", "currency": "BRL", "venue_id": "petlove",
     "name": "Petlove", "platform_guess": "unknown",
     "urls": [
        {"product": "apoquel", "mg": None, "n": None,
         "url": "https://www.petlove.com.br/apoquel-dermatologico-zoetis-para-caes/p"},
     ]},
    {"country": "CA", "currency": "CAD", "venue_id": "petsdrugmart",
     "name": "PetsDrugMart", "platform_guess": "unknown",
     "urls": [
        {"product": "apoquel", "mg": None, "n": None,
         "url": "https://www.petsdrugmart.ca/en/Product/Apoquel-119005/4086"},
     ]},
    {"country": "JP", "currency": "JPY", "venue_id": "civet",
     "name": "Ci Vet (Ci Medical)", "platform_guess": "trade gate?",
     "urls": [
        {"product": "apoquel", "mg": 3.6, "n": None,
         "url": "https://www.ci-medical.com/vet/catalog_item/804Y2509"},
        {"product": "apoquel", "mg": 5.4, "n": None,
         "url": "https://www.ci-medical.com/vet/catalog_item/804Y2510"},
        {"product": "apoquel", "mg": 16, "n": None,
         "url": "https://www.ci-medical.com/vet/catalog_item/804Y2511"},
     ]},
    # China has no stable product URL on record. The queue predicts a bot
    # challenge rather than a price; this fetch exists to turn that prediction
    # into an observation, not to find a price.
    {"country": "CN", "currency": "CNY", "venue_id": "jd",
     "name": "JD.com pet health", "platform_guess": "bot-protected",
     "urls": [
        {"product": "apoquel", "mg": None, "n": None,
         "url": "https://search.jd.com/Search?keyword=%E7%88%B1%E6%B3%A2%E5%85%8B"},
     ]},
]

GATE_SIGNALS = [
    # generic
    "captcha", "cf-challenge", "are you a robot", "access denied",
    "please verify", "unusual traffic",
    # login walls, in the queue's languages
    "log in to see", "login to view", "sign in to see",
    "faça login", "entre para ver",            # pt-BR
    "ログイン",                                  # ja: login
    "会員", "医療関係者",                        # ja: members / medical personnel
    "登录", "验证",                              # zh: login / verify
]


def fetch(url):
    rec = {"url": url}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read(CAP + 1)
            rec["status"] = r.status
            rec["final_url"] = r.url
            rec["content_type"] = r.headers.get("Content-Type", "")
            if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                try:
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
                except OSError:
                    pass
            rec["capped"] = len(body) > CAP
            body = body[:CAP]
            rec["bytes"] = len(body)
    except urllib.error.HTTPError as ex:
        rec["status"] = ex.code
        rec["error"] = f"HTTP {ex.code} {ex.reason}"
        try:
            body = ex.read(200_000)
        except Exception:
            body = b""
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
        body = b""
    rec["seconds"] = round(time.time() - t0, 1)

    text = body.decode("utf-8", "replace")
    low = text.lower()

    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    if m:
        rec["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:300]

    # JSON-LD, verbatim: the parser gets written against THIS, later, by a
    # person reading the dump — not against a guess.
    blocks = []
    for jm in re.finditer(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            text, re.S | re.I):
        raw = jm.group(1).strip()
        try:
            blocks.append({"parsed": json.loads(raw)})
        except Exception:
            blocks.append({"unparseable_head": raw[:2000]})
    if blocks:
        rec["jsonld"] = blocks[:8]

    # price signals outside JSON-LD
    metas = re.findall(
        r'<meta[^>]+(?:property|itemprop|name)=["\'][^"\']*price[^"\']*["\'][^>]*>',
        text, re.I)
    if metas:
        rec["price_metas"] = metas[:12]
    inline = re.findall(
        r'(?:R\$|CAD?\s?\$|¥|￥)\s?[\d.,]{2,12}', text)
    if inline:
        rec["inline_currency_hits"] = inline[:20]

    rec["gate_signals"] = sorted({s for s in GATE_SIGNALS if s in low or s in text})
    rec["head"] = text[:1500]
    print(f"  {rec.get('status', '---'):>4} {rec.get('bytes', 0):>9,}b "
          f"jsonld={len(blocks)} gates={rec['gate_signals'] or '-'} {url[:80]}")
    return rec


# Round 2: PetsDrugMart's page carries ONE JSON-LD offer (CAD 2.62 per
# tablet) for a product sold in three strengths, so the strength that price
# belongs to is not stated. The shop is Shopify (assets under /cdn/shop/),
# and Shopify serves the variant table — id, title, price per variant — at
# <product-url>.js. That table is the difference between "a Canadian price
# exists" and "this price is the 5.4 mg tablet".
JSON_EXTRAS = [
    {"venue_id": "petsdrugmart", "what": "shopify variants",
     "url": "https://petsdrugmart.ca/products/apoquel-tablet.js"},
]


def fetch_json(url):
    rec = {"url": url}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read(CAP + 1)
            rec["status"] = r.status
            rec["content_type"] = r.headers.get("Content-Type", "")
            if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                try:
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
                except OSError:
                    pass
            body = body[:CAP]
            rec["bytes"] = len(body)
        try:
            rec["json"] = json.loads(body)
        except Exception:
            rec["head"] = body[:1500].decode("utf-8", "replace")
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    rec["seconds"] = round(time.time() - t0, 1)
    print(f"  {rec.get('status', '---'):>4} {rec.get('bytes', 0):>9,}b "
          f"json={'yes' if 'json' in rec else 'no'} {url[:80]}")
    return rec


def main():
    venues = []
    for v in QUEUE:
        print(f"{v['country']} {v['name']}:")
        out = dict(v)
        out["fetches"] = [dict(u, **{"fetch": fetch(u["url"])}) for u in v["urls"]]
        for f in out["fetches"]:
            f["fetch"].pop("url", None)
        venues.append(out)
        time.sleep(2)   # one shop at a time, politely

    extras = []
    for x in JSON_EXTRAS:
        print(f"extra: {x['venue_id']} {x['what']}:")
        extras.append(dict(x, fetch=fetch_json(x["url"])))

    os.makedirs("data", exist_ok=True)
    doc = {
        "probe": "pricescraper candidate queue — discover mode",
        "generated_by": "scripts/probe_pricescraper_queue.py",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cap_bytes": CAP,
        "note": ("Discovery only. Nothing here is a published price. Promotion "
                 "requires a person to read the JSON-LD blocks in this dump "
                 "and write a parser against what actually came back — pack "
                 "size (n) included, which snippets routinely omit."),
        "venues": venues,
        "extras": extras,
    }
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(f"\nwrote {OUT} ({os.path.getsize(OUT):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
