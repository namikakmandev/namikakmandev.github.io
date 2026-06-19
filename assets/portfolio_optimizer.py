"""Product Portfolio Optimizer (command-line version).

Same logic as js/portfolio-optimizer.js: allocate a limited resource across
products to maximise total contribution margin, subject to per-product demand
ceilings and strategic minimums. The optimal allocation is the LP / divisible-
knapsack solution — fund the strategic floors first, then greedily buy units
in descending order of contribution earned per unit of the scarce resource.

Run:
    python portfolio_optimizer.py
"""

import math


INDUSTRIES = {
    "generic": {
        "res": "Capacity units", "budget": 9000,
        "rows": [
            {"name": "Product A — premium", "p": 180, "c": 70, "r": 6, "d": 1400, "m": 200, "u": 300},
            {"name": "Product B — core",    "p": 95,  "c": 48, "r": 3, "d": 2600, "m": 400, "u": 500},
            {"name": "Product C — value",   "p": 42,  "c": 31, "r": 2, "d": 3000, "m": 0,   "u": 1500},
            {"name": "Product D — new",     "p": 130, "c": 60, "r": 5, "d": 900,  "m": 0,   "u": 150},
            {"name": "Product E — legacy",  "p": 55,  "c": 52, "r": 4, "d": 1200, "m": 0,   "u": 480},
        ],
    },
    "pharma": {
        "res": "Field-force days", "budget": 2200,
        "rows": [
            {"name": "Brand Alfa (in-patent)", "p": 240, "c": 70,  "r": 1.2, "d": 6000, "m": 300, "u": 600},
            {"name": "Brand Beta (growth)",    "p": 160, "c": 55,  "r": 1.0, "d": 4500, "m": 150, "u": 300},
            {"name": "Brand Gama (mature)",    "p": 90,  "c": 40,  "r": 0.7, "d": 5000, "m": 0,   "u": 800},
            {"name": "Brand Delta (launch)",   "p": 320, "c": 110, "r": 1.8, "d": 1800, "m": 0,   "u": 100},
            {"name": "Generic line (tender)",  "p": 28,  "c": 24,  "r": 0.4, "d": 8000, "m": 0,   "u": 1000},
        ],
    },
    "manufacturing": {
        "res": "Machine hours", "budget": 7000,
        "rows": [
            {"name": "Assembly — Line 1", "p": 420, "c": 210, "r": 2.5, "d": 1600, "m": 200, "u": 500},
            {"name": "Assembly — Line 2", "p": 260, "c": 150, "r": 1.8, "d": 2400, "m": 200, "u": 900},
            {"name": "Spare parts kit",   "p": 85,  "c": 38,  "r": 0.5, "d": 5000, "m": 0,   "u": 1500},
            {"name": "Custom / project",  "p": 950, "c": 520, "r": 6.0, "d": 400,  "m": 0,   "u": 90},
            {"name": "Refurb / service",  "p": 140, "c": 120, "r": 1.2, "d": 1800, "m": 0,   "u": 1500},
        ],
    },
}


def optimize(rows, budget):
    """Allocate `budget` of the scarce resource across `rows`.

    Each row: name, p (price), c (cost), r (resource/unit),
              d (max demand), m (strategic minimum), u (current units).
    Returns a dict with the optimized plan and uplift vs current.
    """
    # normalize and enrich
    items = []
    for i, row in enumerate(rows):
        p, c = row["p"], row["c"]
        res = max(0.0, row.get("r", 0))
        d = max(0.0, row.get("d", 0))
        m = min(d, max(0.0, row.get("m", 0)))
        cur = min(d, max(0.0, row.get("u", 0)))
        cm = p - c
        eff = (cm / res) if res > 0 else math.inf
        items.append({
            "idx": i, "name": row["name"], "p": p, "c": c,
            "res": res, "d": d, "m": m, "cur": cur,
            "cm": cm, "eff": eff, "opt": m,
        })

    # 1) lock in mandatory strategic minimums
    used = sum(x["res"] * x["opt"] for x in items)
    mins_infeasible = used > budget + 1e-9
    free = max(0.0, budget - used)

    # 2) greedy: best contribution-per-resource first, only if cm > 0
    queue = sorted([x for x in items if x["cm"] > 0],
                   key=lambda x: x["eff"], reverse=True)
    for x in queue:
        headroom = x["d"] - x["opt"]
        if headroom <= 0:
            continue
        if x["res"] <= 0:
            take = headroom  # no resource cost — fill to demand
        else:
            by_budget = math.floor((free + 1e-9) / x["res"])
            take = min(headroom, by_budget)
        if take <= 0:
            continue
        x["opt"] += take
        free -= take * x["res"]

    # 3) decorate
    for x in items:
        x["optC"] = x["cm"] * x["opt"]
        x["curC"] = x["cm"] * x["cur"]
        x["optR"] = x["res"] * x["opt"]
        if x["cm"] <= 0:
            x["status"] = "Loss/unit — hold at floor" if x["cm"] < 0 else "Zero margin — floor"
        elif x["opt"] > x["cur"] + 0.5:
            x["status"] = "Scale up"
        elif x["opt"] < x["cur"] - 0.5:
            x["status"] = "Scale down"
        else:
            x["status"] = "Hold"

    opt_c = sum(x["optC"] for x in items)
    cur_c = sum(x["curC"] for x in items)
    opt_r = sum(x["optR"] for x in items)
    cur_r = sum(x["res"] * x["cur"] for x in items)
    return {
        "rows": items, "budget": budget,
        "optC": opt_c, "curC": cur_c,
        "optR": opt_r, "curR": cur_r,
        "uplift": opt_c - cur_c,
        "upliftPct": ((opt_c - cur_c) / cur_c * 100) if cur_c > 0 else 0.0,
        "funded": sum(1 for x in items if x["opt"] > 0),
        "minsInfeasible": mins_infeasible,
        "leftover": free,
    }


def _money(n):
    sign = "-" if n < 0 else ""
    return f"{sign}EUR {abs(round(n)):,}"


def _u(n):
    return f"{round(n):,}"


def _print_report(industry_key):
    ind = INDUSTRIES[industry_key]
    R = optimize(ind["rows"], ind["budget"])
    reslab = ind["res"]
    label_w = max(len(x["name"]) for x in R["rows"])

    print(f"\n=== Product Portfolio Optimizer — {industry_key} ===")
    print(f"Resource: {reslab}   Budget: {_u(R['budget'])}")
    if R["minsInfeasible"]:
        print("!! Strategic minimums alone exceed the budget — cut a floor or raise budget.")

    header = f"{'Product':<{label_w}}  {'CM/u':>8}  {'Res/u':>6}  {'CM/res':>9}  " \
             f"{'Cur':>6}  {'Opt':>6}  {'Opt C':>12}  Action"
    print(header)
    print("-" * len(header))
    for x in R["rows"]:
        eff = "inf" if x["eff"] == math.inf else _money(x["eff"])
        print(f"{x['name']:<{label_w}}  {_money(x['cm']):>8}  "
              f"{x['res']:>6.2f}  {eff:>9}  "
              f"{_u(x['cur']):>6}  {_u(x['opt']):>6}  {_money(x['optC']):>12}  {x['status']}")

    print("-" * len(header))
    print(f"{'Current plan contribution':<{label_w + 32}} {_money(R['curC']):>12}")
    print(f"{'Optimized contribution':<{label_w + 32}} {_money(R['optC']):>12}")
    sign = "+" if R["uplift"] >= 0 else ""
    pct = f"  ({sign}{R['upliftPct']:.1f}%)" if R["curC"] > 0 else ""
    print(f"{'Uplift':<{label_w + 32}} {sign + _money(R['uplift']):>12}{pct}")
    util = (R["optR"] / R["budget"] * 100) if R["budget"] > 0 else 0
    print(f"{reslab + ' used':<{label_w + 32}} {_u(R['optR']) + ' / ' + _u(R['budget']):>12}  ({util:.0f}%)")
    print(f"{'Products funded':<{label_w + 32}} {R['funded']} / {len(R['rows'])}")


if __name__ == "__main__":
    for key in INDUSTRIES:
        _print_report(key)
