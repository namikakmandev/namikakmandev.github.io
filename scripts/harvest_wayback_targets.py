#!/usr/bin/env python3
"""Turn archived product URLs into backfill targets we can trust.

The coverage probe found 27 venues whose product pages ARE in the archive
under URLs the tracker does not follow - shops that re-slugged, moved
platform, or simply have more SKUs archived than we track. Those pages are
the only route to European price history: Farmapets IT goes back to Feb
2023, Centauro ES to Aug 2020, MetropoleVet CZ to 2022, PetMart RO to Jan
2022 under an old URL scheme the live site no longer uses.

A URL is only usable if we can name the SKU it sells WITHOUT trusting the
page, because the integrity rule is that a price we cannot attribute to a
specific strength never gets recorded. So this reads the SKU out of the URL
slug and drops everything it cannot classify. Two traps it has to survive:

  * Continental shops write 5.4 mg as "54" and 3.6 mg as "36" (farmapets:
    apoquel-54-mg-100-compresse). A naive parse invents a 54 mg Apoquel.
    Every strength is therefore snapped to the product's real strength list
    and dropped if it does not land on one.
  * The slug filter matches image derivatives and search pages as readily as
    product pages (.../apoquel-54-mg-100-compresse.jpg, /ricerca?s=Apoquel).

Output is data/_wayback-candidates.json - candidates for review, not data.
Nothing here fetches anything or writes an observation.
"""

import json
import re
import sys
from collections import Counter
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import fetch_pharma_prices as fp

COVERAGE = fp.ROOT / "data" / "_wayback-coverage.json"
OUT = fp.ROOT / "data" / "_wayback-candidates.json"

# Strengths this dataset has actually observed live. Deliberately NOT a claim
# about every strength each product is licensed in - a strength we have never
# seen is dropped rather than guessed at, which loses a few real SKUs (CPP
# lists an 84 mg Zenrelia we have no live row for) but never invents one.
STRENGTHS = {
    "apoquel":          [3.6, 5.4, 16.0],
    "apoquel-chewable": [3.6, 5.4, 16.0],
    "cytopoint":        [10.0, 20.0, 30.0, 40.0],
    "zenrelia":         [4.8, 6.4, 8.5, 15.0],
    "numelvi":          [4.8, 7.2, 21.6, 31.6],
}

ASSET = re.compile(r"\.(jpe?g|png|gif|webp|svg|css|js|pdf|xml|ico|woff2?)$", re.I)
LISTING = re.compile(r"(\?|/ricerca|/search|/cerca|/szukaj|/hledani|/recherche|/buscar"
                     r"|/category|/kategoria|/collections?/|/tag/|/c/[A-Z])", re.I)

# chewable in the languages the panel actually uses
CHEW = re.compile(r"(chewable|chew-|mastica|masticabil|ragotab|zuvacie|zvykaci"
                  r"|kautab|kauwtab|zuvaci|comprimidos-masticables|compresse-masticabili"
                  r"|tablete-masticabile|rago-)", re.I)
FILMCOAT = re.compile(r"(film|filmom|filmtab|obalene|powlekan|rivestit|pellicul)", re.I)
INJ = re.compile(r"(iniett|inject|injek|iniectabil|vial|viales|ampul|solucion|soluzione)", re.I)


def product_of(slug):
    if "cytopoint" in slug or "lokivetmab" in slug:
        return "cytopoint"
    if "zenrelia" in slug or "ilunocitinib" in slug:
        return "zenrelia"
    if "numelvi" in slug:
        return "numelvi"
    if "apoquel" in slug or "oclacitinib" in slug or "oclacitina" in slug:
        return "apoquel"                       # form decided separately below
    return None


def form_of(pid, slug):
    if pid == "cytopoint":
        return "inj"                           # Cytopoint is only ever injectable
    if CHEW.search(slug):
        return "chew"
    if FILMCOAT.search(slug) or re.search(r"(tablet|tablete|tabletta|compresse|comprimid"
                                          r"|comprim|tbl|cps|cds|cp\b)", slug, re.I):
        return "tab"
    return None


def strength_of(pid, slug):
    """Read a strength and snap it to one we have observed for this product.

    Continental slugs drop the decimal point: 5,4 mg becomes '54', 3,6 mg
    becomes '36', and 21,6 mg becomes '216'. Anything that does not land on a
    real label strength is dropped rather than guessed.
    """
    cands = []
    for m in re.finditer(r"(\d+(?:[.,-]\d+)?)\s*-?\s*mg", slug, re.I):
        raw = m.group(1).replace(",", ".").replace("-", ".")
        try:
            cands.append(float(raw))
        except ValueError:
            continue
    if not cands:
        return None, None
    real = STRENGTHS[pid]
    for v in cands:
        for r in real:
            if abs(v - r) < 0.05:
                return r, "exact"
        for r in real:                          # 54 -> 5.4, 36 -> 3.6, 216 -> 21.6
            if abs(v / 10.0 - r) < 0.05:
                return r, "decimal-dropped"
    return None, f"no label strength matches {cands}"


def pack_of(slug):
    """Pack count, in the unit the shop sells: tablets, or vials."""
    m = re.search(r"(\d+)\s*(?:vial|viales|fiale|flacon)", slug, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*-?\s*(compresse|comprimid\w*|comprim\w*|tablet\w*|tabletta"
                  r"|tablete|tbl\b|cps\b|cds\b|cp\b|db\b|szt\b|stk\b|x\b)", slug, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:^|[-/])(\d+)x(?:[-/]|$)", slug, re.I)
    if m:
        return int(m.group(1))
    return None


def main():
    cov = json.loads(COVERAGE.read_text())
    tracked = {(t["venue"], t["url"]) for t in fp.TARGETS}

    # GosVet serves Spanish-language base URLs from a .com domain and is filed
    # here as a Polish storefront; harvesting its non-/pl/ pages would attach
    # Spanish shelf prices to Poland. Left out deliberately.
    SKIP_VENUES = {"gosvet", "perfectpet"}

    out = {"run": cov["run"], "mode": "wayback-candidate-harvest",
           "rule": "SKU must be readable from the URL slug; strength must snap to a "
                   "real label strength; nothing is fetched here",
           "candidates": [], "rejected": []}
    reasons = Counter()

    for e in cov["venues"]:
        venue = e["venue"]
        if venue in SKIP_VENUES:
            reasons[f"venue skipped: {venue}"] += len(e["product_urls"])
            continue
        for pu in e["product_urls"]:
            url = pu["url"]
            slug = unquote(urlsplit(url).path).lower()
            if ASSET.search(url) or LISTING.search(url):
                reasons["asset or listing URL"] += 1
                continue
            pid = product_of(slug)
            if not pid:
                reasons["no product in slug"] += 1
                continue
            form = form_of(pid, slug)
            if not form:
                reasons["form not stated in slug"] += 1
                continue
            if pid == "apoquel" and form == "chew":
                pid = "apoquel-chewable"
            mg, how = strength_of(pid, slug)
            if mg is None:
                reasons["strength unreadable or not a real one"] += 1
                out["rejected"].append({"url": url, "why": how})
                continue
            n = pack_of(slug)
            if n is None:
                reasons["pack count not in slug"] += 1
                continue
            out["candidates"].append({
                "venue": venue, "country": e["country"], "product": pid, "form": form,
                "mg": mg, "n": n, "url": url, "seen": pu["seen"],
                "strength_read": how, "already_tracked": (venue, url) in tracked,
            })

    out["candidates"].sort(key=lambda c: (c["country"], c["venue"], c["product"], c["mg"], c["n"]))
    out["rejected"] = out["rejected"][:40]
    out["reasons"] = dict(reasons)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")

    new = [c for c in out["candidates"] if not c["already_tracked"]]
    print(f"{len(out['candidates'])} candidates, {len(new)} not already tracked")
    print(json.dumps(dict(reasons), indent=1))
    by = Counter((c["country"], c["venue"]) for c in new)
    for (cc, v), k in sorted(by.items()):
        print(f"  {cc} {v:16s} {k:3d} new SKU URLs")


if __name__ == "__main__":
    main()
