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
    "alphaportal": {"name": "Alphaportal",          "country": "HU", "currency": "HUF",
                    "note": "upper end of HU retail band (independent median ~34k Ft/20)"},
    "tuttofarma": {"name": "TuttoFarma",             "country": "IT", "currency": "EUR"},
    "mypharmaclick": {"name": "MyPharmaClick",       "country": "IT", "currency": "EUR"},
    "farmapets":  {"name": "FarmaPets",              "country": "IT", "currency": "EUR"},
    "boticasur": {"name": "Boticasur",               "country": "ES", "currency": "EUR"},
    "todomascota": {"name": "Todoparatumascota",     "country": "ES", "currency": "EUR"},
    "farmamascota": {"name": "La Farmacia de tu Mascota", "country": "ES", "currency": "EUR"},
    "dogteur":   {"name": "Dogteur",                 "country": "FR", "currency": "EUR"},
    "mapharma":  {"name": "Ma Pharma Naturelle",     "country": "FR", "currency": "EUR"},
    "sorgue":    {"name": "Pharmacie de la Sorgue",  "country": "FR", "currency": "EUR"},
    "pharmavie": {"name": "Pharmavie St-Priest",     "country": "FR", "currency": "EUR"},
    "citovet":   {"name": "Citovet (Warsaw)",        "country": "PL", "currency": "PLN"},
    "vetsupply-au": {"name": "Vet Supply Pharmacy",   "country": "AU", "currency": "AUD"},
    "vetslovepets": {"name": "Vets Love Pets",        "country": "AU", "currency": "AUD"},
    "viovet":    {"name": "VioVet",                   "country": "GB", "currency": "GBP"},
    "blumberger": {"name": "Blumberger Apotheke",     "country": "DE", "currency": "EUR"},
    "pharmaservices": {"name": "PharmaServices",      "country": "FR", "currency": "EUR"},
    "centauro":  {"name": "Centauro",                 "country": "ES", "currency": "EUR"},
    "ceneo":     {"name": "Ceneo.pl (comparator)",    "country": "PL", "currency": "PLN"},
    "compari":   {"name": "Compari.ro (comparator)",  "country": "RO", "currency": "RON"},
    "pricero":   {"name": "price.ro (comparator)",    "country": "RO", "currency": "RON"},
    "lekyjasne": {"name": "LekyJasne.cz (aggregate)", "country": "CZ", "currency": "CZK"},
    "arukereso": {"name": "Arukereso.hu (comparator)", "country": "HU", "currency": "HUF"},
    "petmart":   {"name": "PetMart",                  "country": "RO", "currency": "RON"},
}

# kind: "sku" = page sells exactly the declared form/strength/count
#       "multi" = page carries variants; adapter + label parser split them
#       "agg"  = price-comparison portal page for ONE declared SKU; we record
#                the cheapest offer plus how many plausible offers the page
#                carries (sample size), method "aggregate"
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
    {"product": "cytopoint", "venue": "hyperdrug", "kind": "multi",
     "url": "https://hyperdrug.co.uk/cytopoint-injection/",
     "form": "inj", "optional": True},
    {"product": "cytopoint", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/cytopoint-solution-for-injection-for-dogs-30mg",
     "form": "inj", "mg": 30, "n": 1, "optional": True},
    {"product": "cytopoint", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/cytopoint-solution-for-injection-for-dogs-40mg",
     "form": "inj", "mg": 40, "n": 1, "optional": True},
    {"product": "zenrelia", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/zenrelia-film-coated-tablets-for-dogs-8-5mg",
     "form": "tab", "mg": 8.5, "n": 1, "optional": True},
    {"product": "numelvi", "venue": "pdo", "kind": "sku",
     "url": "https://www.petdrugsonline.co.uk/numelvi-tablets-for-dogs-21-6mg",
     "form": "tab", "mg": 21.6, "n": 1, "optional": True},
    {"product": "cytopoint", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/cytopoint/2519-cytopoint-30mg-pack-of-2-vials.html",
     "form": "inj", "mg": 30, "n": 2, "optional": True},
    {"product": "numelvi", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/numelvi-tablets-for-dogs/2890-216mg-numelvi-tablets-for-dogs-per-tablet.html",
     "form": "tab", "mg": 21.6, "n": 1, "optional": True},
    {"product": "numelvi", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/numelvi-tablets-for-dogs/2891-72mg-numelvi-tablets-for-dogs-per-tablet.html",
     "form": "tab", "mg": 7.2, "n": 1, "optional": True},
    {"product": "zenrelia", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/zenrelia-for-dogs/2843-85mg-zenrelia-for-dogs-per-tablet.html",
     "form": "tab", "mg": 8.5, "n": 1, "optional": True},
    {"product": "zenrelia", "venue": "vetdisp", "kind": "sku",
     "url": "https://www.vetdispense.co.uk/zenrelia-for-dogs/2841-48mg-zenrelia-for-dogs-per-tablet.html",
     "form": "tab", "mg": 4.8, "n": 1, "optional": True},
    {"product": "cytopoint", "venue": "viovet", "kind": "multi",
     "url": "https://www.viovet.co.uk/Cytopoint/c40548/",
     "form": "inj", "optional": True},
    {"product": "numelvi", "venue": "viovet", "kind": "multi",
     "url": "https://www.viovet.co.uk/Numelvi-Tablets-for-Dogs/c180052/",
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
    {"product": "apoquel-chewable", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/apoquel-chewable-16mg-100-tablets/",
     "form": "chew", "mg": 16, "n": 100, "optional": True},
    {"product": "apoquel-chewable", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/copy-of-apoquel-16mg-single-tablet/",
     "form": "chew", "mg": 16, "n": 1, "optional": True},
    {"product": "zenrelia", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/zenrelia-4-8mg-single-tablets/",
     "form": "tab", "mg": 4.8, "n": 1, "optional": True},
    {"product": "zenrelia", "venue": "dpm", "kind": "sku",
     "url": "https://discountpetmeds.com.au/zenrelia-8-5-mg-single-tablets/",
     "form": "tab", "mg": 8.5, "n": 1, "optional": True},
    {"product": "apoquel-chewable", "venue": "ypa", "kind": "multi",
     "url": "https://yourpetpa.com.au/products/apoquel-16mg-per-chewable-tablet",
     "form": "chew", "mg": 16, "n": 1, "optional": True},
    {"product": "apoquel-chewable", "venue": "ypa", "kind": "multi",
     "url": "https://yourpetpa.com.au/products/copy-of-apoquel-16mg-100-tablets",
     "form": "chew", "mg": 16, "n": 100, "optional": True},
    {"product": "zenrelia", "venue": "ypa", "kind": "multi",
     "url": "https://yourpetpa.com.au/products/zenrelia-15mg-90-tablets",
     "form": "tab", "mg": 8.5, "n": 90, "optional": True},
    {"product": "apoquel", "venue": "vetsupply-au", "kind": "sku",
     "url": "https://www.vetsupplypharmacy.com.au/apoquel-tablets-16mg-pack.aspx",
     "form": "tab", "mg": 16, "n": 1, "optional": True},
    {"product": "apoquel-chewable", "venue": "vetslovepets", "kind": "multi",
     "url": "https://vetslovepets.com.au/products/apoquel-chewable-tablet",
     "form": "chew", "optional": True},
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
    {"product": "apoquel", "venue": "alphaportal", "kind": "sku",
     "url": "https://www.alphaportal2.hu/allatfaj/kutya/apoquel-16-mg-filmtabletta-100x-10009859/",
     "form": "tab", "mg": 16, "n": 100, "optional": True},
    {"product": "apoquel", "venue": "alphaportal", "kind": "sku",
     "url": "https://www.alphaportal2.hu/termek-kategoria/allatgyogyaszati-keszitmenyek/apoquel-16-mg-filmtabletta-20x-10010186/",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    # ---------------- IT ----------------
    {"product": "apoquel", "venue": "tuttofarma", "kind": "sku",
     "url": "https://www.tuttofarma.it/farmaci-veterinari-con-ricetta/114815-apoquel-100-compresse-rivestite-16mg-farmaco-veterinario.html",
     "form": "tab", "mg": 16, "n": 100, "optional": True},
    {"product": "apoquel-chewable", "venue": "tuttofarma", "kind": "sku",
     "url": "https://www.tuttofarma.it/detraibili/114818-apoquel-20-compresse-masticabili-16mg-farmaco-veterinario.html",
     "form": "chew", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "mypharmaclick", "kind": "sku",
     "url": "https://www.mypharmaclick.com/veterinaria/204546-apoquel-16-mg-20-compresse-rivestite",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "farmapets", "kind": "sku",
     "url": "https://www.farmapets.it/farmaci-per-cani-con-ricetta/706-apoquel-16-mg-20-compresse.html",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel-chewable", "venue": "farmapets", "kind": "sku",
     "url": "https://www.farmapets.it/farmaci-per-cani-con-ricetta/1631-apoquel-masticabile-16-mg-20-compresse.html",
     "form": "chew", "mg": 16, "n": 20, "optional": True},
    # ---------------- ES ----------------
    {"product": "apoquel", "venue": "boticasur", "kind": "sku",
     "url": "https://boticasur.es/apoquel-16-mg-20-comprimidos.html",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "boticasur", "kind": "sku",
     "url": "https://boticasur.es/apoquel-54-mg-100-comprimidos-zoetis.html",
     "form": "tab", "mg": 5.4, "n": 100, "optional": True},
    {"product": "apoquel", "venue": "todomascota", "kind": "sku",
     "url": "https://www.todoparatumascota.eu/tienda/APOQUEL-PARA-PERROS-16-MG-100-COMPRIMIDOS-p348312328",
     "form": "tab", "mg": 16, "n": 100, "optional": True},
    {"product": "zenrelia", "venue": "farmamascota", "kind": "multi",
     "url": "https://www.lafarmaciadetumascota.com/producto/zenrelia-15-mg/",
     "form": "tab", "mg": 15, "n": 30, "optional": True},
    {"product": "apoquel-chewable", "venue": "farmamascota", "kind": "multi",
     "url": "https://www.lafarmaciadetumascota.com/producto/apoquel-16mg-masticable/",
     "form": "chew", "mg": 16, "n": 20, "optional": True},
    # ---------------- FR (reservation/click-and-collect prices) ----------------
    {"product": "apoquel", "venue": "dogteur", "kind": "sku",
     "url": "https://www.dogteur.com/apoquel-16-mg-20-cps.html",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "apoquel", "venue": "dogteur", "kind": "sku",
     "url": "https://www.dogteur.com/apoquel-16-mg-100-cps.html",
     "form": "tab", "mg": 16, "n": 100, "optional": True},
    {"product": "apoquel", "venue": "mapharma", "kind": "sku",
     "url": "https://mapharmanaturelle.com/autres/131899-apoquel-16mg-100-comprimes-pellicules-5414736057484.html",
     "form": "tab", "mg": 16, "n": 100, "optional": True},
    {"product": "apoquel", "venue": "sorgue", "kind": "sku",
     "url": "https://pharmaciedelasorgue.apothical.fr/medicament-produit-parapharmacie/406113-apoquel-16-mg-comprimes-chien-chat-b-20",
     "form": "tab", "mg": 16, "n": 20, "optional": True},
    {"product": "cytopoint", "venue": "pharmavie", "kind": "sku",
     "url": "https://pharmaciedumarche-saintpriest.pharmavie.fr/medicament-produit-parapharmacie/361459-cytopoint-40-mg-solution-injectable-pour-chiens-solution-injectable",
     "form": "inj", "mg": 40, "n": 1, "optional": True},
    # ---------------- PL (Zenrelia only — Apoquel/Cytopoint are vet-channel-only) ----------------
    {"product": "zenrelia", "venue": "citovet", "kind": "multi",
     "url": "https://sklep.citovet.pl/produkt/zenrelia/",
     "form": "tab", "optional": True},
]

# Agent-verified expansion (2026-08-28): full product lineups at proven venues
# plus new venues with snippet price evidence. All optional; slugs are known to
# be unreliable at several venues, so every row is keyed by DECLARED mg/n.
_TRET = "https://www.shop.trettin-apotheken.de/product/"
_TUTTO = "https://www.tuttofarma.it/farmaci-veterinari-con-ricetta/"
_FPETS = "https://www.farmapets.it/"
_MPN = "https://mapharmanaturelle.com/autres/"
_ALPHA = "https://www.alphaportal2.hu/"
# CEE reinforcement (comparator pages carry many shops' offers -> kind "agg")
EXTRA_AGGS = [
    # product, venue, url, form, mg, n
    ("apoquel", "ceneo", "https://www.ceneo.pl/107695335", "tab", 16, 20),
    ("apoquel", "ceneo", "https://www.ceneo.pl/107695333", "tab", 16, 10),
    ("apoquel", "ceneo", "https://www.ceneo.pl/107695329", "tab", 5.4, 20),
    ("apoquel", "compari", "https://suplimente-nutritive-caini.compari.ro/zoetis/apoquel-16-mg-20-tablete-p1118270956/", "tab", 16, 20),
    ("apoquel", "compari", "https://suplimente-nutritive-caini.compari.ro/zoetis/apoquel-5-4-mg-20-tablete-p1118270899/", "tab", 5.4, 20),
    ("apoquel", "pricero", "https://www.price.ro/preturi-zoetis-apoquel-16-mg-20-tablete-3061462", "tab", 16, 20),
    ("apoquel", "lekyjasne", "https://lekyjasne.cz/veterina/0910f7c78024e66f/", "tab", 16, 1),
    ("apoquel", "lekyjasne", "https://lekyjasne.cz/veterina/0910f7c7819808fb/", "tab", 3.6, 1),
    ("apoquel", "arukereso", "https://vitamin-taplalekkiegeszito-kutyaknak.arukereso.hu/apoquel-16mg-100-tabletta-p463108458/", "tab", 16, 100),
]
for _pr, _ve, _u, _f, _mg, _n in EXTRA_AGGS:
    TARGETS.append({"product": _pr, "venue": _ve, "kind": "agg", "url": _u,
                    "form": _f, "mg": _mg, "n": _n, "optional": True})

EXTRA_SKUS = [
    ("apoquel", "petmart", "https://www.petmart.ro/apoquel-16-mg-20-tablete.html", "tab", 16, 20),
    # product, venue, url, form, mg, n
    # -------- DE / Trettin: full lineups --------
    ("cytopoint", "trettin", _TRET + "cytopoint-30-mg-ml-injektionsloesung-f-hunde.806408.html", "inj", 30, 1),
    ("zenrelia", "trettin", _TRET + "zenrelia-15-mg-filmtabletten-fuer-hunde.1057633.html", "tab", 15, 90),
    ("zenrelia", "trettin", _TRET + "zenrelia-8-5-mg-filmtabletten-fuer-hunde.1057636.html", "tab", 8.5, 90),
    ("zenrelia", "trettin", _TRET + "zenrelia-6-4-mg-filmtabletten-fuer-hunde.1057638.html", "tab", 6.4, 30),
    ("numelvi", "trettin", _TRET + "numelvi-21-6-mg-tabletten-fuer-hunde.1057072.html", "tab", 21.6, 30),
    ("numelvi", "trettin", _TRET + "numelvi-7-2-mg-tabletten-fuer-hunde.1057070.html", "tab", 7.2, 30),
    ("numelvi", "trettin", _TRET + "numelvi-31-6-mg-tabletten-fuer-hunde.1057075.html", "tab", 31.6, 90),
    ("apoquel", "trettin", _TRET + "apoquel-16-mg-filmtabletten-f-hunde.949756.html", "tab", 16, 20),
    ("apoquel-chewable", "trettin", _TRET + "apoquel-16-mg-kautabletten-f-hunde.936111.html", "chew", 16, 100),
    # -------- DE / Blumberger (venue 2; counts per agent PZN attribution) --------
    # Blumberger pages surface the per-tablet price -> track as per-unit
    ("apoquel-chewable", "blumberger", "https://www.blumbergerapotheke.de/produkt/18228471/apoquel-16-mg-kautabletten-f-hunde", "chew", 16, 1),
    # -------- FR / Ma Pharma Naturelle: Zenrelia set + extras --------
    ("zenrelia", "mapharma", _MPN + "135478-zenrelia-15-mg-chiens-30-comprimes.html", "tab", 15, 30),
    ("zenrelia", "mapharma", _MPN + "135479-zenrelia-15-mg-chiens-90-comprimes.html", "tab", 15, 90),
    ("zenrelia", "mapharma", _MPN + "135481-zenrelia-85-mg-chiens-30-comprimes.html", "tab", 8.5, 30),
    ("zenrelia", "mapharma", _MPN + "135476-zenrelia-48-mg-chiens-30-comprimes.html", "tab", 4.8, 30),
    ("apoquel", "mapharma", _MPN + "131929-apoquel-16mg-20-comprimes-pellicules-5414736057477.html", "tab", 16, 20),
    ("apoquel-chewable", "mapharma", _MPN + "131900-apoquel-16-mg-20-comprimes-5414736053011.html", "chew", 16, 20),
    ("apoquel", "pharmaservices", "https://www.pharmaservices.fr/medicaments-sur-ordonnance/8061-apoquel-chien-16-mg-100-comprimes.html", "tab", 16, 100),
    # -------- IT / TuttoFarma: Cytopoint + Zenrelia + Numelvi --------
    ("cytopoint", "tuttofarma", _TUTTO + "115412-cytopoint-iniettabile-2-fiale-1ml-10mg-ml-farmaco-veterinario.html", "inj", 10, 2),
    ("cytopoint", "tuttofarma", _TUTTO + "115413-cytopoint-iniettabile-2-fiale-1ml-20mg-ml-farmaco-veterinario.html", "inj", 20, 2),
    ("cytopoint", "tuttofarma", _TUTTO + "115414-cytopoint-iniettabile-2-fiale-1ml-30mg-ml-farmaco-veterinario.html", "inj", 30, 2),
    ("cytopoint", "tuttofarma", _TUTTO + "115415-cytopoint-iniettabile-2-fiale-1ml-40mg-ml-farmaco-veterinario.html", "inj", 40, 2),
    ("zenrelia", "tuttofarma", _TUTTO + "226765-zenrelia-30cpr-riv-15mg.html", "tab", 15, 30),
    ("zenrelia", "tuttofarma", _TUTTO + "226766-zenrelia-90cpr-riv-15mg.html", "tab", 15, 90),
    ("zenrelia", "tuttofarma", _TUTTO + "226764-zenrelia-30cpr-riv-85mg.html", "tab", 8.5, 30),
    ("zenrelia", "tuttofarma", _TUTTO + "226762-zenrelia-30cpr-riv-64mg.html", "tab", 6.4, 30),
    ("numelvi", "tuttofarma", _TUTTO + "226759-numelvi-90cpr-riv-216mg-cani.html", "tab", 21.6, 90),
    ("numelvi", "tuttofarma", _TUTTO + "226755-numelvi-90cpr-riv-48mg-cani.html", "tab", 4.8, 90),
    # -------- IT / FarmaPets --------
    ("cytopoint", "farmapets", _FPETS + "farmaci-per-cani-con-ricetta-refrigerati/778-cytopoint-soluzione-iniettabile-10-mg-2-flaconi.html", "inj", 10, 2),
    ("cytopoint", "farmapets", _FPETS + "farmaci-per-cani-con-ricetta-refrigerati/781-cytopoint-soluzione-iniettabile-40-mg-2-flaconi.html", "inj", 40, 2),
    ("zenrelia", "farmapets", _FPETS + "farmaci-per-cani-con-ricetta/2281-zenrelia-15-mg-90-compresse-per-cani.html", "tab", 15, 90),
    ("zenrelia", "farmapets", _FPETS + "farmaci-per-cani-con-ricetta/2276-zenrelia-85-mg-30-compresse-per-cani.html", "tab", 8.5, 30),
    ("numelvi", "farmapets", _FPETS + "farmaci-per-cani-con-ricetta/2291-numelvi-316-mg-90-compresse.html", "tab", 31.6, 90),
    ("numelvi", "farmapets", _FPETS + "farmaci-per-cani-con-ricetta/2288-numelvi-48-mg-90-compresse.html", "tab", 4.8, 90),
    # -------- IT / MyPharmaClick --------
    ("zenrelia", "mypharmaclick", "https://www.mypharmaclick.com/veterinaria/207300-zenrelia-15-mg-30-compresse-per-cani-con-dermatite-atopica", "tab", 15, 30),
    ("apoquel-chewable", "mypharmaclick", "https://www.mypharmaclick.com/antiparassitari/204743-apoquel-16-mg-20-compresse-masticabili-8436025896120", "chew", 16, 20),
    # -------- ES --------
    ("apoquel", "boticasur", "https://boticasur.es/apoquel-5-4-mg-100-comprimidos-zoetis.html", "tab", 5.4, 100),
    ("apoquel", "boticasur", "https://boticasur.es/apoquel-3-6-mg-20-comprimidos-zoetis.html", "tab", 3.6, 20),
    ("cytopoint", "centauro", "https://shop.centauro.es/es/Salud-animal/Dermatolog%C3%ADa/Inmunomoduladores---Supresores/CYTOPOINT-10MG-ML-2X1ML-/p/1027202", "inj", 10, 2),
    # -------- CZ / VeterinaShop --------
    ("apoquel", "vetshopcz", "https://www.veterinashop.cz/apoquel-5-4mg-20tbl", "tab", 5.4, 20),
    ("apoquel", "vetshopcz", "https://www.veterinashop.cz/apoquel-5-4mg-100tbl", "tab", 5.4, 100),
    # -------- HU / Alphaportal (vial count unstated on HU cytopoint pages -> n=1 flagged) --------
    ("apoquel-chewable", "alphaportal", _ALPHA + "termek-kategoria/allatgyogyaszati-keszitmenyek/apoquel-3-6-mg-ragotabletta-kutyak-reszere-20x-g22000209/", "chew", 3.6, 20),
    ("apoquel-chewable", "alphaportal", _ALPHA + "allatfaj/kutya/apoquel-16-mg-ragotabletta-kutyak-reszere-100x-g22000214/", "chew", 16, 100),
    ("cytopoint", "alphaportal", _ALPHA + "termek-kategoria/allatgyogyaszati-keszitmenyek/cytopoint-10-mg-injekcio-1-ml-10022539/", "inj", 10, 1),
    ("cytopoint", "alphaportal", _ALPHA + "termek-kategoria/allatgyogyaszati-keszitmenyek/cytopoint-40-mg-injekcio-1-ml-10022552/", "inj", 40, 1),
    ("numelvi", "alphaportal", _ALPHA + "allatfaj/kutya/numelvi-21-6-mg-tabletta-kutyak-szamara-3x30-g260009/", "tab", 21.6, 90),
    ("numelvi", "alphaportal", _ALPHA + "allatfaj/kutya/numelvi-31-6-mg-tabletta-kutyak-szamara-1x30-g25000180/", "tab", 31.6, 30),
    # -------- HU / Kincsem (bare host — www caused the earlier 404) --------
]
for _pr, _ve, _u, _f, _mg, _n in EXTRA_SKUS:
    TARGETS.append({"product": _pr, "venue": _ve, "kind": "sku", "url": _u,
                    "form": _f, "mg": _mg, "n": _n, "optional": True})

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
         or re.search(r"(\d+)\s*(?:count|tbl\.?|tabl\.?|tablet(?:s|ten|ta)?|kautablet(?:s|ten)?|filmtablet(?:s|ten|ta)?|r[aá]g[oó]tabletta|chewables?|tabs?|comprimidos|vials?|adet|st(?:ück|k)?|db|x|'?li)(?![a-z])", label, re.I)
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
           "CZK": r"(?:Kč|CZK)", "HUF": r"(?:Ft|HUF)", "PLN": r"(?:zł|PLN)",
           "RON": r"(?:lei|RON)"}[currency]
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    out = []
    pats = ([rf"{sym}\s*([0-9][0-9.,]*)", rf"([0-9][0-9 \u00a0.,]*[0-9])(?:,-)?\s*{sym}"]
            if currency in ("TRY", "EUR", "CZK", "HUF", "PLN", "RON") else [rf"{sym}\s*([0-9][0-9.,]*)"])
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
        elif t["kind"] == "agg":
            cands = sorted({v for fn in (extract_ldjson, extract_meta, extract_inline_js)
                            for _, v in fn(html)}
                           | {v for _, v in extract_visible(html, venue["currency"])})
            # offers cluster around the SKU price; drop sub-10% stragglers
            # (shipping fees, per-unit teasers) relative to the page median
            if cands:
                med = cands[len(cands) // 2]
                offers = [v for v in cands if v >= med * 0.1]
                rows = [{"mg": t.get("mg"), "n": t.get("n") or 1,
                         "price": min(offers), "method": "aggregate",
                         "offers": len(offers)}] if offers else []
            else:
                rows = []
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
                    **({"offers": r["offers"]} if r.get("offers") else {}),
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
