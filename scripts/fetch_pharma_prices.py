#!/usr/bin/env python3
"""Daily multi-country price tracker for 5 canine dermatology products.

v2: observations are per (product x form/strength x venue x country), not
per page. Three countries, 2-3 venues each:

  US  PetVM, California Pet Pharmacy, Heartland Vet Supply (+PetRx, EntirelyPets Rx)
  GB  VetUK, Pet Drugs Online, VetDispense (+Hyperdrug, the only UK Numelvi listing)
  TR  Sandia, Petilac, Vepetzamani (Apoquel only — Cytopoint is clinic-only in TR,
      Zenrelia/Numelvi not in TR retail as of Aug 2026)
  AU  Discount Pet Meds, YourPetPA, Pet Chemist (no Numelvi launch yet)
  DE  Trettin Apotheken, medizinfuchs comparator, A3 Apotheke (Numelvi has PZNs
      but no pharmacy stocks it yet)
  NL  Diermedicatie.nl probes — Dutch UDA rules bar web sales of these Rx
      products, so pages may carry no price; kept optional to report honestly

Each target URL is either a SKUPAGE (the page sells exactly one form/strength,
declared in config) or a MULTI page (several variants; an adapter extracts
(label, price) pairs and a label parser maps them to strength/count).

MODE=discover dumps each page's price-bearing structures (JSON-LD, meta,
variant/option blocks, price-ish script snippets) to the report file instead
of parsing — the repo convention for writing parsers against a source's real
shape rather than what its platform docs imply.

Failures never destroy history: a product-venue that fails simply gets no
observation that day, and the reason lands in data/_pharma-prices-report.json.
Prices stay in venue currency (USD/GBP/TRY); cross-currency comparison is the
chart page's job, not the scraper's.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "pharma-prices.json"
REPORT = ROOT / "data" / "_pharma-prices-report.json"
MODE = os.environ.get("MODE", "")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8,tr;q=0.6",
}

PRODUCTS = {
    "cytopoint":        {"name": "Cytopoint",        "maker": "Zoetis", "forms": ["inj"]},
    "apoquel":          {"name": "Apoquel",          "maker": "Zoetis", "forms": ["tab"]},
    "apoquel-chewable": {"name": "Apoquel Chewable", "maker": "Zoetis", "forms": ["chew"]},
    "numelvi":          {"name": "Numelvi",          "maker": "Merck",  "forms": ["tab"]},
    "zenrelia":         {"name": "Zenrelia",         "maker": "Elanco", "forms": ["tab"]},
}

VENUES = {
    "petvm":     {"name": "PetVM",                   "country": "US", "currency": "USD"},
    "cpp":       {"name": "California Pet Pharmacy", "country": "US", "currency": "USD"},
    "heartland": {"name": "Heartland Vet Supply",    "country": "US", "currency": "USD"},
    "petrx":     {"name": "PetRx",                   "country": "US", "currency": "USD"},
    "entirely":  {"name": "EntirelyPets Rx",         "country": "US", "currency": "USD"},
    "vetuk":     {"name": "VetUK",                   "country": "GB", "currency": "GBP"},
    "pdo":       {"name": "Pet Drugs Online",        "country": "GB", "currency": "GBP"},
    "vetdisp":   {"name": "VetDispense",             "country": "GB", "currency": "GBP"},
    "hyperdrug": {"name": "Hyperdrug",               "country": "GB", "currency": "GBP"},
    "sandia":    {"name": "Sandia Vet",              "country": "TR", "currency": "TRY"},
    "petilac":   {"name": "Petilac",                 "country": "TR", "currency": "TRY"},
    "vepet":     {"name": "Vepetzamani",             "country": "TR", "currency": "TRY"},
    "dpm":       {"name": "Discount Pet Meds",       "country": "AU", "currency": "AUD"},
    "ypa":       {"name": "YourPetPA",               "country": "AU", "currency": "AUD"},
    "petchem":   {"name": "Pet Chemist",             "country": "AU", "currency": "AUD"},
    "trettin":   {"name": "Trettin Apotheken",       "country": "DE", "currency": "EUR"},
    "diermed":   {"name": "Diermedicatie.nl",        "country": "NL", "currency": "EUR"},
    "gosvet":    {"name": "GosVet (PL storefront)",  "country": "PL", "currency": "EUR"},
    "vetshopcz": {"name": "VeterinaShop.cz",         "country": "CZ", "currency": "CZK"},
    "metrovet":  {"name": "MetropoleVet",            "country": "CZ", "currency": "CZK"},
    "dogmo":     {"name": "DogmoPharm",              "country": "HU", "currency": "HUF"},
    "vetker":    {"name": "Vetker",                  "country": "HU", "currency": "HUF"},
    "hazipatika": {"name": "Hazikedvenc Patika",     "country": "HU", "currency": "HUF"},
}

# kind: "sku" = page sells exactly the declared form/strength/count
#       "multi" = page carries variants; adapter + label parser split them
# sku fields: form (tab|chew|inj), mg (strength), n (units per listed price;
#             None = parse from variant label / page, fall back to 1)
TARGETS = [
    # ---------------- US ----------------
    {"product": "cytopoint", "venue": "petvm", "kind": "multi",
     "url": "https://petvm.com/skin-coat/458-cytopoint-for-dogs.html",
     "form": "inj"},
    {"product": "apoquel", "venue": "petvm", "kind": "multi",
     "url": "https://petvm.com/skin-coat/318-apoquel.html",
     "form": "tab"},
    {"product": "zenrelia", "venue": "petvm", "kind": "multi",
     "url": "https://petvm.com/skin-coat/511-zenrelia-ilunocitnib-tablets.html",
     "form": "tab"},
    {"product": "apoquel", "venue": "cpp", "kind": "sku",
     "url": "https://www.californiapetpharmacy.com/apoquel-16mg-per-tablet.html",
     "form": "tab", "mg": 16, "n": 1},
    {"product": "apoquel-chewable", "venue": "cpp", "kind": "sku",
     "url": "https://www.californiapetpharmacy.com/apoquel-chewable-16mg-per-chewable.html",
     "form": "chew", "mg": 16, "n": 1},
    {"product": "numelvi", "venue": "heartland", "kind": "sku",
     "url": "https://www.heartlandvetsupply.com/p-7274-numelvi-atinvicitinib-tablets-for-dogs.aspx",
     "form": "tab", "mg": 4.8, "n": 1},
    {"product": "apoquel-chewable", "venue": "heartland", "kind": "sku",
     "url": "https://www.heartlandvetsupply.com/p-6816-apoquel-oclacitinib-chewable-tablets-for-dogs.aspx",
     "form": "chew", "n": 1},
    {"product": "numelvi", "venue": "petrx", "kind": "multi",
     "url": "https://petrx.com/products/numelvi-atinvicitinib-tablets",
     "form": "tab"},
    {"product": "zenrelia", "venue": "entirely", "kind": "sku",
     "url": "https://entirelypetspharmacy.com/zenrelia-tablets-for-dogs.html",
     "form": "tab", "n": 1},
    # ---------------- GB ----------------
    {"product": "apoquel", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/apoquel-16mg",
     "form": "tab", "mg": 16, "n": 1},
    {"product": "apoquel-chewable", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/apoquel-chewable-tablets-16mg",
     "form": "chew", "mg": 16, "n": 1},
    {"product": "zenrelia", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/zenrelia-film-coated-tablets-for-dogs-15mg",
     "form": "tab", "mg": 15, "n": 1},
    {"product": "apoquel", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/apoquel/2431-16mg-apoquel-tablet-single-tablet.html",
     "form": "tab", "mg": 16, "n": 1},
    {"product": "cytopoint", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/cytopoint/2518-cytopoint-20mg-pack-of-2-vials.html",
     "form": "inj", "mg": 20, "n": 2},
    {"product": "cytopoint", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/cytopoint/2520-cytopoint-40mg-pack-of-2-vials.html",
     "form": "inj", "mg": 40, "n": 2},
    {"product": "zenrelia", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/zenrelia-for-dogs/2844-15mg-zenrelia-for-dogs-per-tablet.html",
     "form": "tab", "mg": 15, "n": 1},
    {"product": "numelvi", "venue": "hyperdrug", "kind": "multi",
     "url": "https://hyperdrug.co.uk/numelvi-tablets-for-dogs/",
     "form": "tab", "optional": True},
    # ---------------- TR ----------------
    {"product": "apoquel", "venue": "sandia", "kind": "sku",
     "url": "https://shop.sandiavet.com/kopek-urunleri/apoquel-16-mg-20-tablet/",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "petilac", "kind": "sku",
     "url": "https://www.petilac.com/urun/apoquel-16-mg-kasinti-tableti",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "vepet", "kind": "sku",
     "url": "https://www.vepetzamani.com/urun/apoquel-16-mg-kasinti-tableti",
     "form": "tab", "mg": 16, "n": 20},
    # ---------------- AU ----------------
    {"product": "apoquel", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/apoquel-16mg-single-tablet-oclacitinib-maleate/",
     "form": "tab", "mg": 16, "n": 1},
    {"product": "zenrelia", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/zenrelia-15mg-tablets-90/",
     "form": "tab", "mg": 15, "n": 90},
    {"product": "zenrelia", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/zenrelia-6-4mg-single-tablets/",
     "form": "tab", "mg": 6.4, "n": 1},
    {"product": "cytopoint", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/cytopoint-20mg-injection-2-vials-lokivetmab/",
     "form": "inj", "mg": 20, "n": 2},
    {"product": "cytopoint", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/cytopoint-30mg-injection-2-vials-lokivetmab/",
     "form": "inj", "mg": 30, "n": 2},
    {"product": "apoquel", "venue": "ypa", "kind": "multi",
     "url": "https://yourpetpa.com.au/products/apoquel-16mg-per-tablet",
     "form": "tab", "mg": 16},
    {"product": "cytopoint", "venue": "ypa", "kind": "multi",
     "url": "https://yourpetpa.com.au/products/cytopoint-injection-40mg-2-vials",
     "form": "inj", "mg": 40, "n": 2},
    {"product": "cytopoint", "venue": "petchem", "kind": "sku",
     "url": "https://petchemist.com.au/products/cytopoint-injection-40mg-2-vials.html",
     "form": "inj", "mg": 40, "n": 2, "optional": True},
    # ---------------- DE ----------------
    {"product": "apoquel", "venue": "trettin", "kind": "sku",
     "url": "https://www.shop.trettin-apotheken.de/product/apoquel-16-mg-filmtabletten-f-hunde.949759.html",
     "form": "tab", "mg": 16, "n": 100},
    {"product": "apoquel-chewable", "venue": "trettin", "kind": "sku",
     "url": "https://www.shop.trettin-apotheken.de/product/apoquel-16-mg-kautabletten-f-hunde.936112.html",
     "form": "chew", "mg": 16, "n": 20},
    {"product": "zenrelia", "venue": "trettin", "kind": "sku",
     "url": "https://www.shop.trettin-apotheken.de/product/zenrelia-15-mg-filmtabletten-fuer-hunde.1057632.html",
     "form": "tab", "mg": 15, "n": 30},
    {"product": "cytopoint", "venue": "trettin", "kind": "sku",
     "url": "https://www.shop.trettin-apotheken.de/product/cytopoint-40-mg-ml-injektionsloesung-f-hunde.806409.html",
     "form": "inj", "mg": 40, "n": 1},
    # ---------------- NL (UDA rules may hide prices — probes) ----------------
    {"product": "apoquel", "venue": "diermed", "kind": "multi",
     "url": "https://www.diermedicatie.nl/nl/apoquel.html",
     "form": "tab"},
    {"product": "apoquel-chewable", "venue": "diermed", "kind": "multi",
     "url": "https://www.diermedicatie.nl/nl/apoquel-kauwtabletten-hond.html",
     "form": "chew", "optional": True},
    {"product": "zenrelia", "venue": "diermed", "kind": "multi",
     "url": "https://www.diermedicatie.nl/nl/zenrelia-hond.html",
     "form": "tab"},
    {"product": "cytopoint", "venue": "diermed", "kind": "multi",
     "url": "https://www.diermedicatie.nl/nl/cytopoint.html",
     "form": "inj"},
    {"product": "numelvi", "venue": "diermed", "kind": "multi",
     "url": "https://www.diermedicatie.nl/nl/numelvi-hond.html",
     "form": "tab", "optional": True},
    # ---------------- PL (GosVet: EU storefront serving Poland, EUR) ----------------
    {"product": "apoquel", "venue": "gosvet", "kind": "sku",
     "url": "https://gosvet.com/pl/producto/apoquel-16mg-100-comprimidos/",
     "form": "tab", "mg": 16, "n": 100},
    {"product": "apoquel-chewable", "venue": "gosvet", "kind": "sku",
     "url": "https://gosvet.com/pl/producto/apoquel-16-mg-20-comprimidos-masticables/",
     "form": "chew", "mg": 16, "n": 20, "optional": True},
    {"product": "cytopoint", "venue": "gosvet", "kind": "sku",
     "url": "https://gosvet.com/pl/cytopoint-20mg-ml-2vialesx1ml/",
     "form": "inj", "mg": 20, "n": 2, "optional": True},
    {"product": "cytopoint", "venue": "gosvet", "kind": "sku",
     "url": "https://gosvet.com/pl/cytopoint-30mg-ml-2vialesx1ml/",
     "form": "inj", "mg": 30, "n": 2, "optional": True},
    # ---------------- CZ ----------------
    {"product": "apoquel", "venue": "vetshopcz", "kind": "sku",
     "url": "https://www.veterinashop.cz/apoquel-16mg-100tbl",
     "form": "tab", "mg": 16, "n": 100, "optional": True},
    {"product": "apoquel", "venue": "vetshopcz", "kind": "sku",
     "url": "https://www.veterinashop.cz/apoquel-16mg-20tbl",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "metrovet", "kind": "multi",
     "url": "https://www.metropolevet.cz/produkt/tablety-a-leciva/apoquel/",
     "form": "tab", "mg": 16, "optional": True},
    # ---------------- HU ----------------
    {"product": "apoquel", "venue": "dogmo", "kind": "sku",
     "url": "https://webshop.dogmopharm.hu/apoquel-16-mg-filmtabletta-100x",
     "form": "tab", "mg": 16, "n": 100},
    {"product": "apoquel", "venue": "dogmo", "kind": "sku",
     "url": "https://webshop.dogmopharm.hu/apoquel-16-mg-filmtabletta-20x",
     "form": "tab", "mg": 16, "n": 20},
    {"product": "apoquel-chewable", "venue": "dogmo", "kind": "sku",
     "url": "https://webshop.dogmopharm.hu/apoquel-16-mg-ragotabletta-kutyak-reszere-20x",
     "form": "chew", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "vetker", "kind": "sku",
     "url": "https://vetker.hu/apoquel-16-mg-filmtabletta-kutyak-reszere-20x-2.html",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "hazipatika", "kind": "multi",
     "url": "https://hazikedvencpatika.hu/apoquel-16mg-2755",
     "form": "tab", "mg": 16, "optional": True},
]

PRICE_MIN, PRICE_MAX = 0.5, 1000000.0  # HUF/TRY pack prices run to six digits


# ---------------------------------------------------------------- helpers --

def to_float(s):
    """Parse '1,049.99', '1.049,99', '3.695,00 TL', '£1.93' -> float."""
    s = re.sub(r"[^\d.,]", "", str(s))
    if not s: return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):    # 1.049,99
            s = s.replace(".", "").replace(",", ".")
        else:                              # 1,049.99
            s = s.replace(",", "")
    elif "," in s:
        # lone comma: decimal if 2 digits follow, thousands otherwise
        if re.search(r",\d{2}$", s): s = s.replace(".", "").replace(",", ".")
        else: s = s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if PRICE_MIN <= v <= PRICE_MAX else None


def parse_label(label, default_mg=None):
    """'16 mg, 30 tablets' / '40mg pack of 2' -> (mg, count)."""
    label = str(label)
    mg = None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*-?\s*mg", label, re.I)
    if m: mg = float(m.group(1).replace(",", "."))
    n = None
    m = (re.search(r"(\d+)\s*[x×]\s*\d+\s*ml\b", label, re.I)
         or re.search(r"(\d+)\s*(?:count|tabl\.?|tablet(?:s|ten)?|kautablet(?:s|ten)?|filmtablet(?:s|ten)?|chewables?|tabs?|comprimidos|vials?|adet|st(?:ück|k)?|'?li)(?![a-z])", label, re.I)
         or re.search(r"pack of\s*(\d+)", label, re.I)
         or re.search(r"[x×]\s*(\d+)\b", label, re.I))
    if m: n = int(m.group(1))
    if re.search(r"per\s+(tablet|chewable|vial)|single|sold per", label, re.I): n = 1
    return (mg if mg is not None else default_mg), n


def walk_ldjson(node, out):
    if isinstance(node, list):
        for item in node: walk_ldjson(item, out)
        return
    if not isinstance(node, dict): return
    name = node.get("name") or node.get("sku") or ""
    for key in ("price", "lowPrice", "highPrice"):
        if node.get(key) not in (None, ""):
            v = to_float(node[key])
            if v is not None: out.append((str(name), v))
    for key in ("@graph", "offers", "itemListElement", "item", "hasVariant", "model",
                "priceSpecification"):
        if key in node: walk_ldjson(node[key], out)


def ldjson_blocks(html):
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html, re.S | re.I):
        yield m.group(1).strip()


def extract_ldjson(html):
    """-> [(label, price)] from schema.org blocks."""
    out = []
    for raw in ldjson_blocks(html):
        try:
            walk_ldjson(json.loads(raw), out)
        except json.JSONDecodeError:
            for p in re.findall(r'"(?:price|lowPrice|highPrice)"\s*:\s*"?([0-9][0-9.,]*)', raw):
                v = to_float(p)
                if v is not None: out.append(("", v))
    return out


def extract_meta(html):
    # standard_amount (list price before placeholder tricks) wins when present
    std = [v for p in re.findall(
        r'<meta[^>]+og:price:standard_amount["\'][^>]+content=["\']([^"\']+)', html, re.I)
        + re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+og:price:standard_amount', html, re.I)
        if (v := to_float(p)) is not None]
    if std:
        return [("", v) for v in std]
    out = []
    for pat in (r'<meta[^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|og:price:amount|price)["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|og:price:amount|price)["\']'):
        for p in re.findall(pat, html, re.I):
            v = to_float(p)
            if v is not None: out.append(("", v))
    return out


def extract_inline_js(html):
    out = []
    for p in re.findall(
            r'"(?:price|price_amount|productPrice|special_price|finalPrice|salesprice|current_price)"\s*:\s*"?\$?£?([0-9][0-9.,]*)"?',
            html, re.I):
        v = to_float(p)
        if v is not None: out.append(("", v))
    return out


def extract_visible(html, currency):
    sym = {"USD": r"\$", "AUD": r"\$", "GBP": "£", "TRY": r"(?:₺|TL)", "EUR": "€",
           "CZK": r"(?:Kč|CZK)", "HUF": r"(?:Ft|HUF)", "PLN": r"(?:zł|PLN)"}[currency]
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    out = []
    pats = ([rf"{sym}\s*([0-9][0-9.,]*)", rf"([0-9][0-9 \u00a0.,]*[0-9])\s*{sym}"]
            if currency in ("TRY", "EUR", "CZK", "HUF", "PLN") else [rf"{sym}\s*([0-9][0-9.,]*)"])
    for pat in pats:
        for p in re.findall(pat, body[:60000]):
            v = to_float(p)
            if v is not None: out.append(("", v))
        if out: break
    return out


# --------------------------------------------------------- multi adapters --

def variants_prestashop(html):
    """PetVM (PrestaShop): valid-JSON combinations blob; per-combination price
    sits in specific_price.price, combos without one use the base productPrice."""
    out = []
    m = re.search(r"var\s+combinations\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        return out
    try:
        combos = json.loads(m.group(1))
    except json.JSONDecodeError:
        return out
    bm = re.search(r"var\s+productPrice\s*=\s*'?([0-9.]+)", html)
    base = float(bm.group(1)) if bm else None
    for c in combos.values():
        label = c.get("attributes_values")
        if isinstance(label, dict): label = " ".join(str(x) for x in label.values())
        sp = c.get("specific_price")
        price = None
        if isinstance(sp, dict): price = to_float(sp.get("price"))
        if price is None: price = to_float(c.get("price"))
        if price is None: price = base
        if price is not None and PRICE_MIN <= price <= PRICE_MAX:
            out.append((str(label or ""), price))
    return out


def variants_shopify(session, url):
    if "/products/" not in url: return []
    try:
        r = session.get(url.split("?")[0] + ".js", headers=HEADERS, timeout=30)
        if r.status_code != 200: return []
        p = r.json()
        return [(v.get("title") or v.get("public_title") or "", c / 100.0)
                for v in p.get("variants", [])
                if (c := v.get("price")) is not None]
    except (requests.RequestException, ValueError):
        return []


def variants_select_options(html):
    """<option>16 mg, 30 ct - $84.00</option> patterns (Heartland etc.)."""
    out = []
    for m in re.finditer(r"<option[^>]*>([^<]{4,120})</option>", html, re.I):
        text = m.group(1)
        pm = re.search(r"[\$£€]\s*([0-9][0-9.,]*)|([0-9][0-9.,]*)\s*(?:TL|₺|€)", text)
        if pm:
            v = to_float(pm.group(1) or pm.group(2))
            if v is not None:
                out.append((re.sub(r"[\$£₺€].*", "", text).strip(" \t-–:"), v))
    return out


def variants_ldjson(html):
    return [(l, v) for l, v in extract_ldjson(html) if l]


# --------------------------------------------------------------- scraping --

def fetch(session, url):
    try:
        r = session.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as exc:
        return None, f"request failed: {exc.__class__.__name__}"
    if r.status_code != 200:
        return None, f"http {r.status_code}"
    return r.text, "ok"


def scrape_sku(html, t, currency):
    """Single-SKU page -> one observation dict or None."""
    for method, cands in (("ld+json", extract_ldjson(html)),
                          ("meta", extract_meta(html)),
                          ("inline-js", extract_inline_js(html)),
                          ("visible", extract_visible(html, currency))):
        vals = sorted({v for _, v in cands})
        if vals:
            price = vals[0]     # sale price sits below list price
            return {"mg": t.get("mg"), "n": t.get("n") or 1,
                    "price": price, "method": method}
    return None


def scrape_multi(session, html, t, currency, allow_shopify=True):
    """Multi-variant page -> [observation], best adapter wins."""
    for method, pairs in (("shopify", variants_shopify(session, t["url"]) if allow_shopify else []),
                          ("prestashop", variants_prestashop(html)),
                          ("ld+json", variants_ldjson(html)),
                          ("options", variants_select_options(html))):
        best = {}
        for label, price in pairs:
            mg, n = parse_label(label, t.get("mg"))
            if n is None: n = t.get("n")
            key = (mg, n)
            if key not in best or price < best[key]["price"]:
                best[key] = {"mg": mg, "n": n or 1, "price": price,
                             "method": method, "label": label[:60]}
        if best:
            return list(best.values())
    # fall back to page-level single observation, count unknown
    one = scrape_sku(html, t, currency)
    if one:
        one["method"] += "/page-level"
        return [one]
    return []


def discover_dump(session, html, t):
    """What does this page actually contain? Snippets for parser-writing."""
    d = {"url": t["url"], "ldjson": [], "meta": [], "options": [],
         "shopify": [], "js_hits": []}
    for raw in ldjson_blocks(html):
        d["ldjson"].append(raw[:1500])
    d["meta"] = [m[:200] for m in re.findall(
        r'<meta[^>]+(?:price|Price)[^>]*>', html)][:10]
    d["options"] = [m[:150] for m in re.findall(
        r"<option[^>]*>[^<]*(?:\$|£|TL|₺|mg)[^<]*</option>", html, re.I)][:25]
    if "/products/" in t["url"]:
        d["shopify"] = [f"{l} -> {v}" for l, v in variants_shopify(session, t["url"])][:20]
    m = re.search(r"var\s+combinations\s*=\s*(\{.*?\});", html, re.S)
    if m: d["combinations"] = m.group(1)[:15000]
    d["data_price"] = [x[:200] for x in re.findall(
        r"<[^>]+data-(?:price|baseprice|varprice)[^>]*>", html, re.I)][:30]
    for m in re.finditer(
            r".{0,80}(?:price_amount|productPrice|salesprice|VariantPrice).{0,120}",
            html):
        if len(d["js_hits"]) >= 12: break
        d["js_hits"].append(m.group(0).replace("\n", " ")[:200])
    d["size"] = len(html)
    return d


def sku_id(product, form, mg):
    frag = f"{mg:g}" if mg is not None else "x"
    return f"{product}-{form}-{frag}"


def main():
    session = requests.Session()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    store = json.loads(DATA.read_text()) if DATA.exists() else {}
    if store.get("schema") != 2:
        store = {"schema": 2, "meta": {}, "observations": []}
    store["meta"] = {
        "title": "Animal pharma price tracker",
        "updated": now,
        "products": PRODUCTS,
        "venues": VENUES,
        "note": "price is in venue currency for n units of the SKU; "
                "unit price = price / n. mg null = strength not stated on page.",
    }

    report = {"run": now, "mode": MODE or "fetch", "targets": []}
    discoveries = []
    n_obs, n_fail = 0, 0

    # replace any same-day rows so a rerun is idempotent
    store["observations"] = [o for o in store["observations"] if o["d"] != today]

    for t in TARGETS:
        venue = VENUES[t["venue"]]
        html, note = fetch(session, t["url"])
        entry = {"product": t["product"], "venue": t["venue"], "url": t["url"],
                 "kind": t["kind"], "note": note}
        if html is None:
            if not t.get("optional"): n_fail += 1
            report["targets"].append(entry)
            time.sleep(2)
            continue

        if MODE == "discover":
            discoveries.append(discover_dump(session, html, t))
            report["targets"].append(entry)
            time.sleep(2)
            continue

        if t["kind"] == "sku":
            one = scrape_sku(html, t, venue["currency"])
            rows = [one] if one else []
        else:
            rows = scrape_multi(session, html, t, venue["currency"])

        if not rows:
            entry["note"] = "no price found"
            if not t.get("optional"): n_fail += 1
        else:
            entry["rows"] = len(rows)
            entry["methods"] = sorted({r["method"] for r in rows})
            for r in rows:
                n_obs += 1
                store["observations"].append({
                    "d": today, "sku": sku_id(t["product"], t["form"], r.get("mg")),
                    "product": t["product"], "form": t["form"],
                    "mg": r.get("mg"), "n": r.get("n") or 1,
                    "venue": t["venue"], "country": venue["country"],
                    "cur": venue["currency"], "price": round(r["price"], 2),
                    "unit": round(r["price"] / (r.get("n") or 1), 4),
                    "method": r["method"],
                    **({"label": r["label"]} if r.get("label") else {}),
                })
        report["targets"].append(entry)
        time.sleep(2)

    if MODE == "discover":
        report["discoveries"] = discoveries
        REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
        print(f"discovery dump for {len(discoveries)} targets -> {REPORT.name}")
        return

    DATA.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    by_cc = {}
    for o in store["observations"]:
        if o["d"] == today:
            by_cc.setdefault(o["country"], 0)
            by_cc[o["country"]] += 1
    print(f"{n_obs} observations today ({by_cc}), {n_fail} required targets failed")
    sys.exit(1 if n_obs == 0 else 0)


if __name__ == "__main__":
    main()
