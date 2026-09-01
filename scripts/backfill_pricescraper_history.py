#!/usr/bin/env python3
"""One-year history backfill for the promoted pricescraper venues, from the
Wayback Machine.                     -> data/pricescraper-history.json

The tracker's pre-2026 history for other markets was reconstructed the same
way (its observations carry 'wayback' method tags): list archived captures of
the exact product URL, fetch the original bytes of each, and run the same
parser the daily read uses. An archived capture that cannot prove price,
currency and pack size yields a recorded refusal, never a guess.

Captures are collapsed to one per day per URL, and every fetch retries with
backoff: the first run lost two of three Cobasi SKUs to the archive's
connection throttling, not to missing data.

Run in GitHub Actions — the dev sandbox blocks web.archive.org too.
"""
import gzip, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

OUT = "data/pricescraper-history.json"
CAP = 2 * 1024 * 1024
CDX = ("https://web.archive.org/cdx/search/cdx?url={url}&output=json"
       "&from={frm}&to={to}&filter=statuscode:200&collapse=timestamp:8&limit=60")
SNAP = "https://web.archive.org/web/{ts}id_/{url}"
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; price history backfill)",
      "Accept-Encoding": "gzip"}

TARGETS = [
    {"venue": "cobasi", "country": "BR", "cur": "BRL", "adapter": "vtex-jsonld",
     "sku": "apoquel-tab-3.6", "mg": 3.6, "n": 20, "pack_proof": r"20\s*comprimidos",
     "url": "https://www.cobasi.com.br/apoquel-dermatologico-zoetis-para-cachorro-3-6-mg-3816434/p"},
    {"venue": "cobasi", "country": "BR", "cur": "BRL", "adapter": "vtex-jsonld",
     "sku": "apoquel-tab-5.4", "mg": 5.4, "n": 20, "pack_proof": r"20\s*comprimidos",
     "url": "https://www.cobasi.com.br/apoquel-dermatologico-zoetis-para-cachorro-54mg-3816442/p"},
    {"venue": "cobasi", "country": "BR", "cur": "BRL", "adapter": "vtex-jsonld",
     "sku": "apoquel-tab-16", "mg": 16, "n": 20, "pack_proof": r"20\s*comprimidos",
     "url": "https://www.cobasi.com.br/-apoquel-dermatologico-zoetis-para-cachorro-3816450/p"},
    # Shopify's variant table is the authority for the live read; whether the
    # archive holds it, or only the product page's single JSON-LD offer, is a
    # question this run answers rather than assumes. The page prices all
    # strengths identically today; a HISTORICAL capture only proves the price
    # it shows, so page-level captures are recorded per capture and published
    # only if the capture itself names the per-tablet model.
    {"venue": "petsdrugmart", "country": "CA", "cur": "CAD", "adapter": "shopify-variants-js",
     "sku": None, "mg": None, "n": 1, "pack_proof": None,
     "url": "https://petsdrugmart.ca/products/apoquel-tablet.js"},
    {"venue": "petsdrugmart", "country": "CA", "cur": "CAD", "adapter": "shopify-page-jsonld",
     "sku": None, "mg": None, "n": 1, "pack_proof": r"per\s+dose/tablet|per\s+tablet",
     "url": "https://petsdrugmart.ca/products/apoquel-tablet"},
    {"venue": "petsdrugmart", "country": "CA", "cur": "CAD", "adapter": "unknown-legacy",
     "sku": None, "mg": None, "n": None, "pack_proof": None,
     "url": "https://www.petsdrugmart.ca/en/Product/Apoquel-119005/4086"},
]

PDM_MG = {"3.6 mg": ("apoquel-tab-3.6", 3.6),
          "5.4 mg": ("apoquel-tab-5.4", 5.4),
          "16 mg": ("apoquel-tab-16", 16)}


def get(url, timeout=90, tries=3):
    """web.archive.org refuses connections when hit in bursts; a refusal is
    throttling, not absence, so back off and try again before recording it."""
    last = None
    for i in range(tries):
        if i:
            time.sleep(8 * (2 ** (i - 1)))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(CAP + 1)
                if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                    try:
                        body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
                    except OSError:
                        pass
                return r.status, body[:CAP].decode("utf-8", "replace")
        except Exception as ex:
            last = ex
    raise last


def product_jsonld(text):
    for m in re.finditer(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            text, re.S | re.I):
        try:
            block = json.loads(m.group(1).strip())
        except Exception:
            continue
        types = block.get("@type")
        if types == "Product" or (isinstance(types, list) and "Product" in types):
            return block
    return None


def captures(url, frm, to):
    try:
        status, text = get(CDX.format(url=urllib.parse.quote(url, safe=""), frm=frm, to=to))
        rows = json.loads(text)
        if not rows:
            return []
        head = rows[0]
        ts_i = head.index("timestamp")
        return [r[ts_i] for r in rows[1:]]
    except Exception as ex:
        print(f"  CDX failed for {url[:60]}: {ex}")
        return None


def parse_capture(t, ts, text):
    """One archived capture -> (observations, refusal-or-None)."""
    day = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
    if t["adapter"] == "vtex-jsonld":
        prod = product_jsonld(text)
        offer = (prod or {}).get("offers") or {}
        price, cur = offer.get("price"), offer.get("priceCurrency")
        if not prod:
            return [], "no Product JSON-LD in capture"
        if not price:
            return [], "no offers.price in capture"
        if cur != t["cur"]:
            return [], f"currency {cur!r} in capture"
        if not re.search(t["pack_proof"], text, re.I):
            return [], "pack proof missing in capture"
        p = round(float(price), 2)
        o = {"d": day, "sku": t["sku"], "product": "apoquel", "form": "tab",
             "mg": t["mg"], "n": t["n"], "venue": t["venue"],
             "country": t["country"], "cur": t["cur"], "price": p,
             "unit": round(p / t["n"], 4), "method": "vtex-jsonld+wayback",
             "hist": True, "label": "20 comprimidos"}
        # The capture's own compare-at price, where it carries one, with the
        # same centavos normalisation the daily read uses. list > price on a
        # given day is what makes a campaign a measurable episode rather than
        # a guess about why the price moved.
        lists = {round(float(x), 2)
                 for x in re.findall(r'"[Ll]ist[Pp]rice"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text)}
        lists = {round(x / 100, 2) if x > 20 * p else x for x in lists}
        lists = {x for x in lists if p < x < 5 * p}
        if len(lists) == 1:
            o["list"] = lists.pop()
        return [o], None
    if t["adapter"] == "shopify-variants-js":
        try:
            j = json.loads(text)
        except Exception:
            return [], "capture is not JSON"
        out = []
        for v in j.get("variants", []):
            hit = PDM_MG.get(str(v.get("title", "")).strip())
            if hit and isinstance(v.get("price"), int) and v["price"] > 0:
                p = round(v["price"] / 100, 2)
                out.append({"d": day, "sku": hit[0], "product": "apoquel",
                            "form": "tab", "mg": hit[1], "n": 1,
                            "venue": t["venue"], "country": t["country"],
                            "cur": t["cur"], "price": p, "unit": p,
                            "method": "shopify-variants+wayback", "hist": True,
                            "label": "per tablet"})
        return (out, None) if out else ([], "no known variants in capture")
    if t["adapter"] == "shopify-page-jsonld":
        prod = product_jsonld(text)
        offer = (prod or {}).get("offers") or {}
        price, cur = offer.get("price"), offer.get("priceCurrency")
        if not prod:
            return [], "no Product JSON-LD in capture"
        if not price:
            return [], "no offers.price in capture"
        if cur != t["cur"]:
            return [], f"currency {cur!r} in capture"
        if not re.search(t["pack_proof"], text, re.I):
            return [], "per-tablet pricing statement missing in capture"
        # the capture proves ONE per-tablet price, not the three-way variant
        # split, so it is recorded strength-unstated (mg null) — the schema's
        # own convention for exactly this case
        p = round(float(price), 2)
        return [{"d": day, "sku": "apoquel-tab", "product": "apoquel",
                 "form": "tab", "mg": None, "n": 1, "venue": t["venue"],
                 "country": t["country"], "cur": t["cur"], "price": p,
                 "unit": p, "method": "shopify-jsonld+wayback", "hist": True,
                 "label": "per tablet, strength not stated in capture"}], None
    # unknown-legacy: discover only, publish nothing
    head = re.sub(r"\s+", " ", text[:400])
    return [], f"legacy platform, parser not written; head: {head[:200]}"


def main():
    to = time.strftime("%Y%m%d", time.gmtime())
    frm = str(int(to[:4]) - 1) + to[4:]
    doc = {"note": ("Wayback backfill for the promoted pricescraper venues, "
                    "one capture per month per URL, parsed with the daily "
                    "read's own parsers. Refusals are recorded per capture."),
           "generated_by": "scripts/backfill_pricescraper_history.py",
           "window": {"from": frm, "to": to},
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "observations": [], "log": []}

    for t in TARGETS:
        name = f"{t['venue']}/{t['sku'] or t['adapter']}"
        ts_list = captures(t["url"], frm, to)
        if ts_list is None:
            doc["log"].append({"target": name, "cdx": "failed"})
            continue
        print(f"{name}: {len(ts_list)} archived captures")
        doc["log"].append({"target": name, "cdx_captures": len(ts_list),
                           "url": t["url"], "parsed": 0, "refused": []})
        entry = doc["log"][-1]
        for ts in ts_list:
            time.sleep(4)   # be gentle with the archive
            try:
                status, text = get(SNAP.format(ts=ts, url=t["url"]))
            except Exception as ex:
                entry["refused"].append({"ts": ts, "why": f"{type(ex).__name__}: {ex}"})
                continue
            obs, why = parse_capture(t, ts, text)
            if why:
                entry["refused"].append({"ts": ts, "why": why})
            else:
                doc["observations"].extend(obs)
                entry["parsed"] += 1
                print(f"  {ts[:8]}: {', '.join(str(o['price']) for o in obs)}")

    # one point per (day, venue, sku)
    seen = {}
    for o in doc["observations"]:
        seen[(o["d"], o["venue"], o["sku"])] = o
    doc["observations"] = sorted(seen.values(),
                                 key=lambda o: (o["venue"], o["sku"] or "", o["d"]))

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(doc['observations'])} historical observations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
