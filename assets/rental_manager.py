"""Rental Portfolio Manager (command-line version).

Same logic as js/rental-manager.js: a tiny CRM for a short-term / summer rental
business. Per-booking nights / rent / net, portfolio-wide revenue, occupancy,
cleaning turnovers still owed, and a top-N net-by-property leaderboard.

Run:
    python rental_manager.py
"""

from datetime import date, datetime, timedelta


PRESETS = {
    "coast":    {"n": 20, "label": "Coast Villa", "base": 140, "span": 7, "clean": 70},
    "city":     {"n": 12, "label": "City Flat",   "base": 95,  "span": 4, "clean": 45},
    "mountain": {"n": 8,  "label": "Chalet",      "base": 175, "span": 6, "clean": 85},
}

NAMES = ["Aydin", "Maria", "John", "Lena", "Carlos", "Sofia", "Ahmet",
         "Emma", "Luca", "Nora", "Pavel", "Yuki", "Omar", "Clara", "Ivan", "Mei"]


def _iso(d):
    return d.isoformat()


def _parse(s):
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def make_portfolio(kind, today=None):
    """Generate a deterministic sample portfolio for the given preset key."""
    cfg = PRESETS[kind]
    today = today or date.today()
    season_start = date(today.year, 6, 1)
    out = []
    for i in range(cfg["n"]):
        prop = f"{cfg['label']} {i + 1:02d}"
        rate = cfg["base"] + ((i * 17) % 90)
        # main summer booking
        ci = season_start + timedelta(days=(i * 11) % 90)
        co = ci + timedelta(days=cfg["span"] + (i % 3))
        guest = f"{NAMES[i % len(NAMES)]} {NAMES[(i + 5) % len(NAMES)][0]}."
        out.append({"prop": prop, "guest": guest, "ci": _iso(ci), "co": _iso(co),
                    "rate": rate, "clean": cfg["clean"],
                    "status": "Confirmed", "cleaned": False})
        # every 3rd property: a past stay still needing its turnover (cleaning due)
        if i % 3 == 0:
            pco = today - timedelta(days=3 + (i % 9))
            pci = pco - timedelta(days=cfg["span"])
            g = f"{NAMES[(i + 2) % len(NAMES)]} {NAMES[(i + 9) % len(NAMES)][0]}."
            out.append({"prop": prop, "guest": g, "ci": _iso(pci), "co": _iso(pco),
                        "rate": rate, "clean": cfg["clean"],
                        "status": "Checked-out", "cleaned": False})
        # every 7th (offset 3): a cancelled booking (excluded from totals)
        if i % 7 == 3:
            cci = season_start + timedelta(days=40 + i)
            g = f"{NAMES[(i + 4) % len(NAMES)]} C."
            out.append({"prop": prop, "guest": g, "ci": _iso(cci),
                        "co": _iso(cci + timedelta(days=cfg["span"])),
                        "rate": rate, "clean": cfg["clean"],
                        "status": "Cancelled", "cleaned": False})
    return out


def calc(b, today=None):
    """Per-booking computation: nights, rent, net, flags."""
    today = today or date.today()
    ci = _parse(b.get("ci"))
    co = _parse(b.get("co"))
    nights = max(0, (co - ci).days) if (ci and co) else 0
    active = b.get("status") != "Cancelled"
    rate = float(b.get("rate") or 0)
    clean_fee = float(b.get("clean") or 0)
    rent = nights * rate
    net = rent - clean_fee
    cleaning_due = (
        active and not b.get("cleaned")
        and (b.get("status") == "Checked-out" or (co and co < today))
    )
    soon = (
        active and b.get("status") == "Confirmed"
        and ci and today <= ci <= today + timedelta(days=14)
    )
    return {"nights": nights, "active": active,
            "rent": rent, "clean_fee": clean_fee, "net": net,
            "cleaning_due": cleaning_due, "soon": soon}


def portfolio_kpis(bookings, today=None):
    """Aggregate revenue, occupancy, turnovers, and net-by-property."""
    today = today or date.today()
    rev = clean = 0.0
    booked_nights = 0
    active_count = due = soon = 0
    props = set()
    net_by_prop = {}
    min_ci = max_co = None

    for b in bookings:
        props.add(b.get("prop") or "—")
        c = calc(b, today)
        if not c["active"]:
            continue
        active_count += 1
        rev += c["rent"]
        clean += c["clean_fee"]
        booked_nights += c["nights"]
        if c["cleaning_due"]:
            due += 1
        if c["soon"]:
            soon += 1
        key = b.get("prop") or "—"
        net_by_prop[key] = net_by_prop.get(key, 0.0) + c["net"]
        ci = _parse(b.get("ci"))
        co = _parse(b.get("co"))
        if ci and (min_ci is None or ci < min_ci):
            min_ci = ci
        if co and (max_co is None or co > max_co):
            max_co = co

    n_props = max(1, len(props))
    span_days = max(1, (max_co - min_ci).days) if (min_ci and max_co) else 1
    capacity = n_props * span_days
    occ = (booked_nights / capacity * 100) if capacity > 0 else 0

    return {
        "rev": rev, "clean": clean, "net": rev - clean,
        "occ_pct": occ, "props": len(props), "active": active_count,
        "due": due, "soon": soon,
        "net_by_prop": net_by_prop,
    }


def _money(n, sym="EUR "):
    sign = "-" if n < 0 else ""
    return f"{sign}{sym}{abs(round(n)):,}"


def _print_report(kind, today=None):
    bookings = make_portfolio(kind, today)
    K = portfolio_kpis(bookings, today)

    print(f"\n=== Rental Portfolio — {PRESETS[kind]['label']} preset ({len(bookings)} bookings) ===")
    print(f"  Revenue         {_money(K['rev'])}")
    print(f"  Cleaning fees   {_money(K['clean'])}")
    print(f"  Net             {_money(K['net'])}")
    print(f"  Occupancy       {K['occ_pct']:.0f}%")
    print(f"  Properties      {K['props']}")
    print(f"  Active bookings {K['active']}")
    print(f"  Cleaning due    {K['due']}")
    print(f"  Check-in <=14d  {K['soon']}")

    leaderboard = sorted(K["net_by_prop"].items(), key=lambda kv: kv[1], reverse=True)[:8]
    if leaderboard:
        print("\n  Top by net:")
        for name, val in leaderboard:
            print(f"    {name:<18} {_money(val)}")


if __name__ == "__main__":
    for kind in PRESETS:
        _print_report(kind)
