#!/usr/bin/env python3
"""Daily price read for the promoted pricescraper venues.
                                        -> data/pricescraper-daily.json

Reads the two venues promoted from the candidate queue on 2026-09-01 and
appends one observation per SKU per day, in the tracker's own observation
schema, so the history can be folded straight into the Animal Pharma Price
Tracker's embedded data.

Both parsers are written against what the discover probe actually returned
(data/_pricescraper-queue-probe.json), not against a guess:

  cobasi        VTEX product pages carry a schema.org Product JSON-LD block
                whose offers.price is the cash price (163.90 under a crossed
                out 234.99 on probe day). Pack size is NOT in the JSON-LD, so
                each SKU declares the text its page proved ("20 comprimidos" /
                "Embalagem com 20 comprimidos") and the observation is
                REFUSED, not guessed, if that text disappears.

  petsdrugmart  Shopify serves the variant table at /products/<handle>.js:
                variant title is the strength, price is integer cents. The
                shop prices per single tablet (n=1); currency is CAD per the
                page's JSON-LD offer.

A run that cannot prove a number records the failure and publishes nothing
for that SKU. Re-running on the same day replaces that day's observations
rather than duplicating them.

Run in GitHub Actions — the dev sandbox blocks both retail domains.
"""
import gzip, io, json, os, re, sys, time, urllib.error, urllib.request

OUT = "data/pricescraper-daily.json"
CAP = 2 * 1024 * 1024
KEEP_RUNS = 30
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en;q=0.8,pt-BR;q=0.6",
    "Accept-Encoding": "gzip",
}

COBASI_SKUS = [
    {"sku": "apoquel-tab-3.6", "mg": 3.6, "n": 20, "pack_proof": r"20\s*comprimidos",
     "url": "https://www.cobasi.com.br/apoquel-dermatologico-zoetis-para-cachorro-3-6-mg-3816434/p"},
    {"sku": "apoquel-tab-5.4", "mg": 5.4, "n": 20, "pack_proof": r"20\s*comprimidos",
     "url": "https://www.cobasi.com.br/apoquel-dermatologico-zoetis-para-cachorro-54mg-3816442/p"},
    {"sku": "apoquel-tab-16", "mg": 16, "n": 20, "pack_proof": r"20\s*comprimidos",
     "url": "https://www.cobasi.com.br/-apoquel-dermatologico-zoetis-para-cachorro-3816450/p"},
]

PDM_URL = "https://petsdrugmart.ca/products/apoquel-tablet.js"
PDM_MG = {"3.6 mg": ("apoquel-tab-3.6", 3.6),
          "5.4 mg": ("apoquel-tab-5.4", 5.4),
          "16 mg": ("apoquel-tab-16", 16)}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read(CAP + 1)
        if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
            try:
                body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
            except OSError:
                pass
        return r.status, body[:CAP].decode("utf-8", "replace")


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


def read_cobasi(today, basis):
    obs, fails = [], []
    for s in COBASI_SKUS:
        why = None
        try:
            status, text = get(s["url"])
            if status != 200:
                why = f"HTTP {status}"
            else:
                prod = product_jsonld(text)
                offer = (prod or {}).get("offers") or {}
                price = offer.get("price")
                cur = offer.get("priceCurrency")
                if not prod:
                    why = "no Product JSON-LD on page"
                elif not price:
                    why = "Product JSON-LD carries no offers.price"
                elif cur != "BRL":
                    why = f"currency changed: {cur!r} (refusing to publish)"
                elif not re.search(s["pack_proof"], text, re.I):
                    why = (f"pack proof /{s['pack_proof']}/ no longer on page — "
                           "pack size may have changed, refusing to publish")
                else:
                    p = round(float(price), 2)
                    o = {
                        "d": today, "sku": s["sku"], "product": "apoquel",
                        "form": "tab", "mg": s["mg"], "n": s["n"],
                        "venue": "cobasi", "country": "BR", "cur": "BRL",
                        "price": p, "unit": round(p / s["n"], 4),
                        "method": "vtex-jsonld", "label": "20 comprimidos"}
                    # The JSON-LD price sits ~30% under a crossed-out list
                    # price, so the list is captured too: a fall in the shelf
                    # price and the start of a campaign look identical unless
                    # both series exist. VTEX embeds it as ListPrice.
                    lists = {round(float(x), 2)
                             for x in re.findall(r'"[Ll]ist[Pp]rice"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text)}
                    lists = {x for x in lists if x > p}
                    if len(lists) == 1:
                        o["list"] = lists.pop()
                    elif lists:
                        basis.append({"venue": "cobasi", "sku": s["sku"],
                                      "ambiguous_list_prices": sorted(lists)})
                    # Is the discounted price gated behind a subscription?
                    # Record the page's own words around every mention.
                    for kw in ("assinante", "assinatura"):
                        for mm in list(re.finditer(kw, text, re.I))[:4]:
                            basis.append({"venue": "cobasi", "sku": s["sku"], "kw": kw,
                                          "context": re.sub(r"\s+", " ",
                                              text[max(0, mm.start()-120):mm.end()+160])})
                    obs.append(o)
        except Exception as ex:
            why = f"{type(ex).__name__}: {ex}"
        if why:
            fails.append({"venue": "cobasi", "sku": s["sku"], "why": why})
        print(f"  cobasi {s['sku']}: {'FAIL ' + why if why else 'ok ' + str(obs[-1]['price'])}")
        time.sleep(2)
    return obs, fails


def read_petsdrugmart(today, basis):
    obs, fails = [], []
    try:
        status, text = get(PDM_URL)
        if status != 200:
            raise RuntimeError(f"HTTP {status}")
        j = json.loads(text)
        variants = j.get("variants", [])
        seen = {}
        for v in variants:
            hit = PDM_MG.get(str(v.get("title", "")).strip())
            if hit:
                seen[hit] = v
        for (sku, mg), v in sorted(seen.items()):
            price = v.get("price")
            if not isinstance(price, int) or price <= 0:
                fails.append({"venue": "petsdrugmart", "sku": sku,
                              "why": f"variant price not positive cents: {price!r}"})
                continue
            if not v.get("available", True):
                fails.append({"venue": "petsdrugmart", "sku": sku,
                              "why": "variant marked unavailable"})
                continue
            p = round(price / 100, 2)
            obs.append({
                "d": today, "sku": sku, "product": "apoquel",
                "form": "tab", "mg": mg, "n": 1,
                "venue": "petsdrugmart", "country": "CA", "cur": "CAD",
                "price": p, "unit": p,
                "method": "shopify-variants", "label": "per tablet"})
            print(f"  petsdrugmart {sku}: ok {p}")
        for title in PDM_MG:
            if not any(t == title for t in
                       (str(v.get("title", "")).strip() for v in variants)):
                fails.append({"venue": "petsdrugmart", "sku": PDM_MG[title][0],
                              "why": f"variant {title!r} missing from table"})
        # A Canadian pharmacy price can hide a dispensing fee added at
        # checkout, and tax is added by provincial convention. The variant
        # table cannot say either; the product page's own words can.
        try:
            _, ptext = get("https://petsdrugmart.ca/products/apoquel-tablet")
            for kw in ("dispensing", "fee", "GST", "HST", " tax", "per dose", "markup"):
                for mm in list(re.finditer(re.escape(kw), ptext, re.I))[:3]:
                    basis.append({"venue": "petsdrugmart", "kw": kw.strip(),
                                  "context": re.sub(r"\s+", " ",
                                      ptext[max(0, mm.start()-140):mm.end()+180])})
        except Exception as ex:
            basis.append({"venue": "petsdrugmart",
                          "basis_probe_error": f"{type(ex).__name__}: {ex}"})
    except Exception as ex:
        fails.append({"venue": "petsdrugmart", "sku": "*",
                      "why": f"{type(ex).__name__}: {ex}"})
        print(f"  petsdrugmart: FAIL {ex}")
    return obs, fails


def main():
    today = time.strftime("%Y-%m-%d", time.gmtime())
    doc = {"note": ("Daily reads of the venues promoted from the pricescraper "
                    "candidate queue, in the tracker's observation schema. A "
                    "read that cannot prove price, currency and pack size "
                    "publishes nothing and records why in runs[]."),
           "generated_by": "scripts/fetch_pricescraper_daily.py",
           "observations": [], "runs": []}
    if os.path.exists(OUT):
        with open(OUT) as fh:
            doc = json.load(fh)

    basis = []
    obs_br, fail_br = read_cobasi(today, basis)
    obs_ca, fail_ca = read_petsdrugmart(today, basis)
    doc["basis"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "note": ("Price-basis evidence from the pages themselves: list "
                             "prices behind the campaign price, subscription wording, "
                             "dispensing-fee and tax wording. Replaced every run."),
                    "evidence": basis}
    new = obs_br + obs_ca
    fails = fail_br + fail_ca

    # same-day rerun replaces, never duplicates
    replaced = {(o["d"], o["venue"], o["sku"]) for o in new}
    doc["observations"] = [o for o in doc["observations"]
                           if (o["d"], o["venue"], o["sku"]) not in replaced] + new
    doc["observations"].sort(key=lambda o: (o["d"], o["venue"], o["sku"]))
    doc["runs"] = (doc.get("runs", [])
                   + [{"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "published": len(new), "refused": fails}])[-KEEP_RUNS:]
    doc["updated"] = doc["runs"][-1]["at"]

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(new)} published, {len(fails)} refused, "
          f"{len(doc['observations'])} total observations")
    # a day where nothing could be proven should fail loudly in the Actions UI
    return 0 if new else 1


if __name__ == "__main__":
    sys.exit(main())
