"""Account & Portfolio Prioritization — whitespace engine (command-line version).

Same scoring logic as js/prioritization.js. Run:
    python prioritization.py sample_prioritization.csv

Finds "whitespace": products a customer's peers buy but they don't,
and ranks the estimated opportunity per account manager.
"""

import csv
import re
import sys
from statistics import median

REQUIRED = ["AccountManager", "Customer", "Product", "Sales"]
ADOPT_MIN = 0.4  # a product counts as "peers buy it" at >= 40% adoption

COL_ALIASES = {
    "AccountManager": ["accountmanager", "accountmgr", "am", "salesrep", "rep",
                       "salesperson", "owner", "kam"],
    "Customer": ["customer", "account", "client", "customername",
                 "accountname", "buyer"],
    "Product": ["product", "sku", "item", "productname", "article"],
    "Sales": ["sales", "revenue", "amount", "netsales", "netrevenue",
              "turnover", "value", "salesvalue"],
    "Segment": ["segment", "customersegment", "tier", "class"],
    "Region": ["region", "area", "territory", "geo", "country"],
    "ProductGroup": ["productgroup", "group", "category", "productcategory",
                     "family", "productline"],
    "Margin%": ["margin", "marginpct", "gm", "gmpct", "grossmargin",
                "grossmarginpct"],
}


def _norm(h):
    return re.sub(r"[\s_%.\-/()]+", "", str(h).lstrip("﻿").strip().lower())


def resolve_cols(raw_head):
    """Map each column index to a canonical name using flexible header aliases."""
    mapping = {}
    for i, h in enumerate(raw_head):
        n = _norm(h)
        for canon, aliases in COL_ALIASES.items():
            if n in aliases:
                mapping[i] = canon
                break
    return mapping


def parse_num(s):
    """Parse a number tolerating thousands separators and European decimals."""
    if isinstance(s, (int, float)):
        return float(s)
    s = re.sub(r"[^\d.,\-]", "", str(s).strip())
    if not s:
        return None
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = parts[0] + "." + parts[1]
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def to_objects(rows):
    cmap = resolve_cols(rows[0])
    head = list(dict.fromkeys(cmap.values()))
    data = []
    for r in rows[1:]:
        o = {}
        for i, canon in cmap.items():
            o[canon] = (r[i] if i < len(r) else "").strip()
        data.append(o)
    return head, data


def whitespace(rows):
    head, data = to_objects(rows)
    missing = [c for c in REQUIRED if c not in head]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))

    has_seg = "Segment" in head
    has_margin = "Margin%" in head
    has_group = "ProductGroup" in head

    # Build customers
    cust = {}
    for r in data:
        sales = parse_num(r.get("Sales"))
        if not r.get("Customer") or not r.get("Product") or sales is None:
            continue
        c = cust.setdefault(r["Customer"], {
            "name": r["Customer"],
            "segment": r.get("Segment") or "-" if has_seg else "-",
            "products": {}, "am_totals": {}, "total": 0.0,
        })
        c["products"][r["Product"]] = c["products"].get(r["Product"], 0) + sales
        c["total"] += sales
        if r.get("AccountManager"):
            c["am_totals"][r["AccountManager"]] = \
                c["am_totals"].get(r["AccountManager"], 0) + sales

    customers = list(cust.values())
    if len(customers) < 4:
        raise ValueError(f"Need at least a few customers to compare. "
                         f"Only {len(customers)} found.")

    for c in customers:
        c["am"] = max(c["am_totals"], key=c["am_totals"].get) \
            if c["am_totals"] else "-"

    # Product meta (group + margin)
    p_meta = {}
    for r in data:
        if not r.get("Product"):
            continue
        m = p_meta.setdefault(r["Product"], {"group": "-", "margins": []})
        if has_group and r.get("ProductGroup"):
            m["group"] = r["ProductGroup"]
        if has_margin:
            mg = parse_num(r.get("Margin%"))
            if mg is not None:
                m["margins"].append(mg)
    product_list = list(p_meta.keys())
    for p in product_list:
        ms = p_meta[p]["margins"]
        p_meta[p]["margin"] = sum(ms) / len(ms) if ms else None

    # Size bands (terciles) within segment (or global)
    def band_map(group):
        s = sorted(group, key=lambda c: c["total"])
        n = len(s)
        for i, c in enumerate(s):
            c["band"] = "S" if i < n / 3 else ("M" if i < 2 * n / 3 else "L")

    if has_seg:
        by_seg = {}
        for c in customers:
            by_seg.setdefault(c["segment"], []).append(c)
        for grp in by_seg.values():
            band_map(grp)
    else:
        band_map(customers)

    def peer_key(c):
        return (c["segment"] + "|" if has_seg else "") + c["band"]

    key_groups = {}
    for c in customers:
        key_groups.setdefault(peer_key(c), []).append(c)

    def peers_of(c):
        p = [x for x in key_groups[peer_key(c)] if x is not c]
        if len(p) < 5 and has_seg:
            p = [x for x in customers
                 if x is not c and x["segment"] == c["segment"]]
        if len(p) < 5:
            p = [x for x in customers if x is not c]
        return p

    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    # Whitespace scoring
    opps = []
    for c in customers:
        peers = peers_of(c)
        for p in product_list:
            actual = c["products"].get(p, 0)
            buyers = [x for x in peers if x["products"].get(p, 0) > 0]
            adoption = len(buyers) / len(peers) if peers else 0
            if adoption < ADOPT_MIN:
                continue
            spends = [b["products"][p] for b in buyers]
            med_spend = median(spends) if spends else 0
            med_peer_total = median([b["total"] for b in buyers]) \
                if buyers else (c["total"] or 1)
            scale = clamp(c["total"] / (med_peer_total or 1), 0.5, 2.5)
            benchmark = med_spend * scale
            opp = benchmark - actual
            floor = max(500, 0.02 * c["total"])
            if opp <= floor:
                continue
            mg = p_meta[p]["margin"]
            score = opp * (mg / 100 if mg is not None else 1)
            opps.append({
                "am": c["am"], "customer": c["name"], "segment": c["segment"],
                "product": p, "group": p_meta[p]["group"], "actual": actual,
                "adoption": adoption, "opp": opp, "margin": mg, "score": score,
            })

    opps.sort(key=lambda o: o["score"], reverse=True)
    return opps, len(customers), len(product_list)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_prioritization.csv"
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.reader(f) if any(cell.strip() for cell in r)]
    except OSError as e:
        sys.exit(f"Could not read {path}: {e}")

    opps, n_cust, n_prod = whitespace(rows)
    total = sum(o["opp"] for o in opps)
    print("Account & Portfolio Prioritization")
    print(f"  {n_cust} customers, {n_prod} products")
    print(f"  {len(opps)} opportunities, "
          f"EUR {round(total):,} total whitespace\n")
    print(f"  {'#':>3}  {'Account Mgr':<16} {'Customer':<16} "
          f"{'Product':<16} {'Opportunity':>12}")
    for i, o in enumerate(opps[:15], 1):
        print(f"  {i:>3}  {o['am'][:16]:<16} {o['customer'][:16]:<16} "
              f"{o['product'][:16]:<16} EUR {round(o['opp']):>9,}")
