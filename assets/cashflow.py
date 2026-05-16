"""Cash Flow & Runway simulator (command-line version).

Same projection logic as js/cashflow.js. Run:
    python cashflow.py
"""

HORIZON = 12

SCENARIOS = {
    "best": {"sales": 1.10, "cost": 0.95, "label": "Best"},
    "base": {"sales": 1.00, "cost": 1.00, "label": "Base"},
    "worst": {"sales": 0.85, "cost": 1.10, "label": "Worst"},
}


def project(inflows, outflows, start_cash, scenario,
            sales_slider=0.0, cost_slider=0.0, collection_delay_days=0):
    """Build the 12-month projection for one scenario.

    inflows  : list of {"amt": monthly €, "g": monthly growth % }
    outflows : list of {"type": "fixed"|"pct", "val": € or % of inflow }
    """
    s = SCENARIOS[scenario]
    sales_mult = s["sales"] * (1 + sales_slider / 100)
    cost_mult = s["cost"] * (1 + cost_slider / 100)
    k = min(1.0, collection_delay_days / 30)  # fraction of inflow that slips a month

    fixed_sum = sum(o["val"] for o in outflows if o["type"] == "fixed")
    pct_sum = sum(o["val"] for o in outflows if o["type"] == "pct") / 100

    rows = []
    prev_close = start_cash
    prev_gross = 0.0
    for m in range(HORIZON):
        gross = sum(ln["amt"] * (1 + ln["g"] / 100) ** m for ln in inflows) * sales_mult
        received = (1 - k) * gross + k * prev_gross
        outflow = (fixed_sum + pct_sum * gross) * cost_mult
        opening = start_cash if m == 0 else prev_close
        net = received - outflow
        closing = opening + net
        rows.append({
            "m": m + 1, "opening": opening, "inflow": received,
            "outflow": outflow, "net": net, "closing": closing,
        })
        prev_close = closing
        prev_gross = gross

    runway = HORIZON
    for i, r in enumerate(rows):
        if r["closing"] < 0:
            runway = i
            break

    low = min(rows, key=lambda r: r["closing"])
    return {
        "rows": rows,
        "runway": runway,
        "low": low["closing"],
        "low_month": low["m"],
        "end": rows[HORIZON - 1]["closing"],
        "cum_net": sum(r["net"] for r in rows),
    }


def _money(n):
    return ("-" if n < 0 else "") + "EUR " + f"{abs(round(n)):,}"


if __name__ == "__main__":
    # A simple generic business, same defaults as the web tool's "generic" preset.
    inflows = [
        {"amt": 50000, "g": 3},   # product sales
        {"amt": 12000, "g": 2},   # services
    ]
    outflows = [
        {"type": "fixed", "val": 35000},  # salaries
        {"type": "fixed", "val": 12000},  # rent & office
        {"type": "fixed", "val": 8000},   # marketing
        {"type": "pct", "val": 35},       # COGS as % of inflow
    ]
    start_cash = 80000

    print("Cash Flow & Runway Simulator\n")
    for key in ("best", "base", "worst"):
        p = project(inflows, outflows, start_cash, key)
        label = SCENARIOS[key]["label"]
        runway = "12+ months" if p["runway"] >= HORIZON else f"{p['runway']} months"
        print(f"--- {label} scenario ---")
        print(f"  Runway        {runway}")
        print(f"  Lowest cash   {_money(p['low'])}  (month {p['low_month']})")
        print(f"  Ending cash   {_money(p['end'])}")
        print(f"  Cumulative net {_money(p['cum_net'])}\n")

    print("Month-by-month (Base):")
    base = project(inflows, outflows, start_cash, "base")
    print(f"  {'M':>3} {'Opening':>12} {'Inflow':>12} {'Outflow':>12} {'Closing':>12}")
    for r in base["rows"]:
        print(f"  {('M' + str(r['m'])):>3} {_money(r['opening']):>12} "
              f"{_money(r['inflow']):>12} {_money(r['outflow']):>12} "
              f"{_money(r['closing']):>12}")
