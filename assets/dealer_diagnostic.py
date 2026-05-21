"""Divisional & Monthly P&L (command-line version).

Same logic as js/dealer-diagnostic-v2.js: turn a trial balance into a
consolidated P&L, a 12-month seasonal view that exposes loss-making months,
and a per-division breakdown. Multi-industry presets.

Run:
    python dealer_diagnostic.py
"""


INDUSTRIES = {
    "auto": {
        "label": "Auto dealer",
        "note": "Full-service car dealer — thin metal margin, profit really in service & parts.",
        "divisions": ["New cars", "Used cars", "Service", "Parts", "F&I", "Rental"],
        "seasonality": [80, 80, 95, 100, 105, 100, 85, 80, 95, 105, 100, 75],
        "tb": [
            {"code": "600.01", "name": "New car sales",            "div": "New cars",  "kind": "rev",  "amount": 18_000_000},
            {"code": "600.02", "name": "Used car sales",           "div": "Used cars", "kind": "rev",  "amount": 9_000_000},
            {"code": "600.03", "name": "Service & repair revenue", "div": "Service",   "kind": "rev",  "amount": 2_400_000},
            {"code": "600.04", "name": "Parts sales",              "div": "Parts",     "kind": "rev",  "amount": 1_800_000},
            {"code": "600.05", "name": "F&I / commission income",  "div": "F&I",       "kind": "rev",  "amount": 600_000},
            {"code": "600.06", "name": "Rental income",            "div": "Rental",    "kind": "rev",  "amount": 700_000},
            {"code": "620.01", "name": "New car cost of sales",    "div": "New cars",  "kind": "cogs", "amount": 17_100_000},
            {"code": "620.02", "name": "Used car cost of sales",   "div": "Used cars", "kind": "cogs", "amount": 8_100_000},
            {"code": "620.03", "name": "Service direct cost",      "div": "Service",   "kind": "cogs", "amount": 840_000},
            {"code": "620.04", "name": "Parts cost of sales",      "div": "Parts",     "kind": "cogs", "amount": 1_350_000},
            {"code": "620.05", "name": "F&I direct cost",          "div": "F&I",       "kind": "cogs", "amount": 60_000},
            {"code": "620.06", "name": "Rental direct cost",       "div": "Rental",    "kind": "cogs", "amount": 490_000},
            {"code": "760.00", "name": "Marketing & selling exp.", "div": "Overhead",  "kind": "opex", "amount": 1_500_000},
            {"code": "770.00", "name": "General admin expense",    "div": "Overhead",  "kind": "opex", "amount": 2_400_000},
        ],
    },
    "manufacturing": {
        "label": "Manufacturing",
        "note": "Machine builder — the aftermarket (spare parts & service) carries the margin.",
        "divisions": ["Machines", "Spare parts", "Service & install", "Engineering"],
        "seasonality": [85, 90, 100, 100, 105, 100, 80, 70, 100, 110, 105, 55],
        "tb": [
            {"code": "600.01", "name": "Machine sales",           "div": "Machines",          "kind": "rev",  "amount": 24_000_000},
            {"code": "600.02", "name": "Spare parts sales",       "div": "Spare parts",       "kind": "rev",  "amount": 6_000_000},
            {"code": "600.03", "name": "Service & installation",  "div": "Service & install", "kind": "rev",  "amount": 4_000_000},
            {"code": "600.04", "name": "Engineering projects",    "div": "Engineering",       "kind": "rev",  "amount": 3_000_000},
            {"code": "620.01", "name": "Machine COGS",            "div": "Machines",          "kind": "cogs", "amount": 18_000_000},
            {"code": "620.02", "name": "Spare parts COGS",        "div": "Spare parts",       "kind": "cogs", "amount": 3_600_000},
            {"code": "620.03", "name": "Service & install cost",  "div": "Service & install", "kind": "cogs", "amount": 2_000_000},
            {"code": "620.04", "name": "Engineering cost",        "div": "Engineering",       "kind": "cogs", "amount": 2_100_000},
            {"code": "760.00", "name": "Selling expense",         "div": "Overhead",          "kind": "opex", "amount": 2_500_000},
            {"code": "770.00", "name": "Administrative expense",  "div": "Overhead",          "kind": "opex", "amount": 4_000_000},
        ],
    },
    "distribution": {
        "label": "Distribution",
        "note": "Wholesale distribution — very thin margins; small leakage moves the result.",
        "divisions": ["Branded wholesale", "Generic wholesale", "Logistics", "Value-added"],
        "seasonality": [90, 90, 95, 95, 100, 100, 95, 90, 100, 105, 105, 95],
        "tb": [
            {"code": "600.01", "name": "Branded wholesale",      "div": "Branded wholesale", "kind": "rev",  "amount": 40_000_000},
            {"code": "600.02", "name": "Generic wholesale",      "div": "Generic wholesale", "kind": "rev",  "amount": 18_000_000},
            {"code": "600.03", "name": "Logistics services",     "div": "Logistics",         "kind": "rev",  "amount": 5_000_000},
            {"code": "600.04", "name": "Value-added services",   "div": "Value-added",       "kind": "rev",  "amount": 2_000_000},
            {"code": "620.01", "name": "Branded COGS",           "div": "Branded wholesale", "kind": "cogs", "amount": 35_200_000},
            {"code": "620.02", "name": "Generic COGS",           "div": "Generic wholesale", "kind": "cogs", "amount": 16_560_000},
            {"code": "620.03", "name": "Logistics cost",         "div": "Logistics",         "kind": "cogs", "amount": 3_500_000},
            {"code": "620.04", "name": "Value-added cost",       "div": "Value-added",       "kind": "cogs", "amount": 1_200_000},
            {"code": "760.00", "name": "Selling expense",        "div": "Overhead",          "kind": "opex", "amount": 1_800_000},
            {"code": "770.00", "name": "Administrative expense", "div": "Overhead",          "kind": "opex", "amount": 2_400_000},
        ],
    },
    "services": {
        "label": "Services",
        "note": "Professional services — labour-driven; utilisation and rate set the margin.",
        "divisions": ["Consulting", "Managed services", "Training"],
        "seasonality": [85, 90, 100, 95, 100, 90, 75, 70, 95, 105, 110, 85],
        "tb": [
            {"code": "600.01", "name": "Consulting fees",          "div": "Consulting",       "kind": "rev",  "amount": 12_000_000},
            {"code": "600.02", "name": "Managed services revenue", "div": "Managed services", "kind": "rev",  "amount": 8_000_000},
            {"code": "600.03", "name": "Training revenue",         "div": "Training",         "kind": "rev",  "amount": 2_500_000},
            {"code": "620.01", "name": "Consulting delivery cost", "div": "Consulting",       "kind": "cogs", "amount": 6_000_000},
            {"code": "620.02", "name": "Managed services cost",    "div": "Managed services", "kind": "cogs", "amount": 4_000_000},
            {"code": "620.03", "name": "Training delivery cost",   "div": "Training",         "kind": "cogs", "amount": 1_000_000},
            {"code": "760.00", "name": "Selling expense",          "div": "Overhead",         "kind": "opex", "amount": 1_500_000},
            {"code": "770.00", "name": "Administrative expense",   "div": "Overhead",         "kind": "opex", "amount": 3_000_000},
        ],
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def diagnose(industry):
    """Turn a trial balance dict into consolidated / divisional / monthly P&L.

    `industry` mirrors the shape used by the web tool: divisions, seasonality,
    and a tb list of {div, kind in {rev, cogs, opex}, amount}.
    """
    divs = industry["divisions"]
    per = {d: {"rev": 0.0, "cogs": 0.0} for d in divs}
    overhead = 0.0
    for a in industry["tb"]:
        amt = a["amount"]
        if a["kind"] == "opex":
            overhead += amt
            continue
        per.setdefault(a["div"], {"rev": 0.0, "cogs": 0.0})
        per[a["div"]][a["kind"]] += amt

    tot_rev = 0.0
    tot_gross = 0.0
    for d in divs:
        per[d]["gross"] = per[d]["rev"] - per[d]["cogs"]
        per[d]["margin_pct"] = (per[d]["gross"] / per[d]["rev"] * 100) if per[d]["rev"] else 0.0
        tot_rev += per[d]["rev"]
        tot_gross += per[d]["gross"]
    tot_cogs = tot_rev - tot_gross
    net = tot_gross - overhead

    sum_w = sum(industry["seasonality"]) or 1
    monthly = []
    loss_months = []
    for i, m in enumerate(MONTHS):
        f = industry["seasonality"][i] / sum_w
        m_rev = tot_rev * f
        m_gross = tot_gross * f
        m_cogs = m_rev - m_gross
        m_oh = overhead / 12
        m_net = m_gross - m_oh
        if m_net < 0:
            loss_months.append(m)
        monthly.append({
            "m": m, "rev": m_rev, "cogs": m_cogs,
            "gross": m_gross, "oh": m_oh, "net": m_net,
        })

    return {
        "per": per, "divisions": divs, "overhead": overhead,
        "tot_rev": tot_rev, "tot_cogs": tot_cogs, "tot_gross": tot_gross,
        "gross_margin_pct": (tot_gross / tot_rev * 100) if tot_rev else 0.0,
        "net": net,
        "net_margin_pct": (net / tot_rev * 100) if tot_rev else 0.0,
        "monthly": monthly,
        "loss_months": loss_months,
    }


def _lira(v):
    r = round(v)
    return ("-TL " if r < 0 else "TL ") + f"{abs(r):,}"


def _paren(v):
    return "(" + _lira(abs(v)) + ")"


def _print_report(key):
    ind = INDUSTRIES[key]
    R = diagnose(ind)

    print(f"\n=== {ind['label']} ===")
    print(ind["note"])

    print("\n-- Consolidated P&L --")
    print(f"  Revenue            {_lira(R['tot_rev'])}")
    print(f"  Cost of sales      {_paren(R['tot_cogs'])}")
    print(f"  Gross profit       {_lira(R['tot_gross'])}  ({R['gross_margin_pct']:.1f}%)")
    print(f"  Operating overhead {_paren(R['overhead'])}")
    print(f"  Net profit         {_lira(R['net'])}  ({R['net_margin_pct']:.1f}%)")

    print("\n-- Per division --")
    name_w = max(len(d) for d in R["divisions"])
    print(f"  {'Division':<{name_w}}  {'Revenue':>14}  {'Gross':>14}  Margin")
    for d in R["divisions"]:
        p = R["per"][d]
        print(f"  {d:<{name_w}}  {_lira(p['rev']):>14}  {_lira(p['gross']):>14}  {p['margin_pct']:.1f}%")

    ranked = sorted(R["divisions"], key=lambda d: R["per"][d]["gross"], reverse=True)
    best, worst = ranked[0], ranked[-1]
    share = (R["per"][best]["gross"] / R["tot_gross"] * 100) if R["tot_gross"] else 0
    print(f"\n  Biggest profit engine: {best} ({_lira(R['per'][best]['gross'])}, "
          f"{share:.0f}% of all gross).")
    print(f"  Weakest: {worst} ({R['per'][worst]['margin_pct']:.1f}% margin).")
    losers = [d for d in R["divisions"] if R["per"][d]["gross"] < 0]
    if losers:
        print(f"  Loss-making at gross level: {', '.join(losers)}.")

    print("\n-- 12-month P&L (seasonal revenue/cost, fixed overhead) --")
    print(f"  {'Month':<5} {'Revenue':>14} {'Gross':>14} {'Net':>14}")
    for row in R["monthly"]:
        print(f"  {row['m']:<5} {_lira(row['rev']):>14} {_lira(row['gross']):>14} {_lira(row['net']):>14}")
    if R["loss_months"]:
        print(f"\n  {len(R['loss_months'])} month(s) run at a loss: "
              f"{', '.join(R['loss_months'])} — even though the year nets {_lira(R['net'])}. "
              f"That is exactly when a low-margin business runs short of cash.")
    else:
        print("\n  No month runs at a loss on this seasonality — but a sharper "
              "seasonal swing or a weaker year quickly changes that.")


if __name__ == "__main__":
    for key in INDUSTRIES:
        _print_report(key)
