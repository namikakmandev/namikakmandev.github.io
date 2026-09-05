#!/usr/bin/env python3
"""Does 1% of price still buy 11.1% of operating profit?
-> data/price-leverage-results.json, assets/linkedin/price-leverage-*.{svg,png}

The claim: Marn & Rosiello, "Managing Price, Gaining Profit", Harvard Business
Review, September-October 1992. A 1% improvement in price, volume held, raises
operating profit by 11.1%; the same 1% in variable cost gives 7.8%, in volume
3.3%, in fixed cost 2.3%. The price figure is an identity:

    price leverage = revenue / operating profit = 1 / operating margin

so 11.1 is what an operating margin of 9.0% produces. It is a property of the
sample the authors averaged in 1992, and of nothing else. This script computes
the same identity on Damodaran's industry margin tables: eight regions today,
and every archived edition he still serves (the US back to 1998).

Only the price lever is retested. The other three need a fixed/variable cost
split that public accounts do not give.

Stdlib only. Inputs come from data/price-leverage.json, written in GitHub
Actions by scripts/fetch_price_leverage.py.
"""
import json, math, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import render_png                                   # noqa: E402

SRC = "data/price-leverage.json"
OUT = "data/price-leverage-results.json"
CLAIM = 11.1                          # % operating profit per 1% price, HBR 1992
CLAIM_MARGIN = 1 / CLAIM              # the operating margin that implies: 9.0%
MIN_FIRMS = 10                        # an "industry" of 3 firms is not an industry
# Editions whose operating-margin column is one of these, from 2011 on, are one
# regime. Earlier US editions use another layout and read "EBIT/Sales", and the
# level steps at the switch: a break, kept apart, never joined.
SAME_REGIME = {"Pre-tax Unadjusted Operating Margin", "Pre-tax Operating Margin"}
REGIME_FROM = 2011                    # first edition in the current layout; 1998 is the old one too
MIN_MARGIN = 0.01                     # below 1% the identity explodes; reported, not ranked
FINANCIAL = ("bank", "brokerage", "insurance", "financial svcs", "investments & asset",
             "reinsurance", "r.e.i.t")  # no revenue concept comparable to the rest

# industries a pricing reader will look for first; matched on the file's own names
WATCH = ["Drugs (Pharmaceutical)", "Drugs (Biotechnology)", "Healthcare Products",
         "Healthcare Support Services", "Food Processing", "Retail (Grocery and Food)",
         "Farming/Agriculture", "Chemical (Specialty)", "Auto & Truck",
         "Software (System & Application)", "Machinery", "Packaging & Container",
         "Retail (General)", "Transportation", "Utility (General)", "Beverage (Soft)"]


def hr(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def total_row(ed, without_financials=False):
    """The aggregate row, by the labels the files actually use."""
    tot = ed.get("totals") or {}
    if without_financials:
        for k, v in tot.items():
            if "without" in k.lower():
                return k, v
        return None, None
    for k, v in tot.items():
        kl = k.lower()
        if kl.startswith(("total market", "grand total", "market")) and "without" not in kl:
            return k, v
    return next(iter(tot.items()), (None, None))


def lev(m):
    return 1 / m if m and m > 0 else None


def is_financial(name):
    return any(f in name.lower() for f in FINANCIAL)


def industry_leverages(ed):
    """1/margin for every non-financial industry with a margin above the floor
    and enough firms. Financials have no comparable revenue line; a margin
    under 1% turns the identity into a number with no meaning."""
    xs = []
    for r in ed.get("industries", []):
        m, n = r.get("op_margin"), r.get("n_firms") or 0
        if m and m >= MIN_MARGIN and n >= MIN_FIRMS and not is_financial(r["name"]):
            xs.append((r["name"], 1 / m, m, n))
    return xs


def industry_excluded(ed):
    """What the spread leaves out, by reason, so the exclusion is visible."""
    out = {"financial": [], "near_zero_or_negative_margin": [], "too_few_firms": []}
    for r in ed.get("industries", []):
        m, n = r.get("op_margin"), r.get("n_firms") or 0
        if is_financial(r["name"]):
            out["financial"].append(r["name"])
        elif m is None or m < MIN_MARGIN:
            out["near_zero_or_negative_margin"].append(r["name"])
        elif n < MIN_FIRMS:
            out["too_few_firms"].append(r["name"])
    return out


def edition_year(yy, ed):
    """Editions are named by two-digit year; date_updated confirms it."""
    y = int(yy)
    y += 1900 if y >= 90 else 2000
    d = ed.get("date_updated") or ""
    if d[:4].isdigit() and abs(int(d[:4]) - y) > 1:
        print(f"  note: edition {yy} carries date {d}; labelled {y} by file name")
    return y


def summarise(ed, label):
    """Everything the story needs from one edition."""
    k, tot = total_row(ed)
    kx, totx = total_row(ed, without_financials=True)
    inds = industry_leverages(ed)
    ls = sorted(x[1] for x in inds)
    rec = {"label": label, "date_updated": ed.get("date_updated"),
           "op_margin_column": (ed.get("columns_used") or {}).get("op_margin"),
           "total_label": k, "n_firms": tot.get("n_firms") if tot else None,
           "op_margin": tot.get("op_margin") if tot else None,
           "leverage": lev(tot.get("op_margin")) if tot else None,
           "net_margin": tot.get("net_margin") if tot else None,
           "n_industries": len(inds),
           "industry_median_leverage": statistics.median(ls) if ls else None,
           "industry_q25_q75": [ls[len(ls) // 4], ls[(3 * len(ls)) // 4]] if len(ls) >= 4 else None,
           "industry_min": min(inds, key=lambda x: x[1])[:2] if inds else None,
           "industry_max": max(inds, key=lambda x: x[1])[:2] if inds else None}
    if totx:
        rec["without_financials"] = {"label": kx, "n_firms": totx.get("n_firms"),
                                     "op_margin": totx.get("op_margin"),
                                     "leverage": lev(totx.get("op_margin"))}
    if tot and tot.get("op_margin_pre_sbc"):
        rec["leverage_pre_stock_comp"] = lev(tot["op_margin_pre_sbc"])
    return rec


def mad_breaks(series, k=3.5):
    """Rule 3: year-on-year steps far outside the series' own typical step."""
    yrs = sorted(series)
    d = {yrs[i]: series[yrs[i]] - series[yrs[i - 1]] for i in range(1, len(yrs))}
    if len(d) < 5:
        return []
    med = statistics.median(d.values())
    mad = statistics.median(abs(v - med) for v in d.values()) or 1e-9
    return [{"year": y, "step": round(v, 2), "z": round((v - med) / (1.4826 * mad), 1)}
            for y, v in d.items() if abs(v - med) / (1.4826 * mad) > k]


def main():
    src = json.load(open(SRC))
    regions = src["regions"]
    res = {"generated_by": "scripts/price_leverage.py", "source_file": SRC,
           "fetched_at": src["fetched_at"],
           "claim": {"paper": "Marn & Rosiello, Managing Price, Gaining Profit, HBR Sep-Oct 1992",
                     "price_leverage_pct": CLAIM, "implied_operating_margin": round(CLAIM_MARGIN, 4),
                     "other_levers_pct": {"variable_cost": 7.8, "volume": 3.3, "fixed_cost": 2.3},
                     "identity": "price leverage = revenue / operating profit = 1 / operating margin"},
           "min_firms_per_industry": MIN_FIRMS}

    # ---------------------------------------------------- 1. the number today
    hr("1. What 1% of price buys today, by region (current edition)")
    today = {}
    for label, reg in regions.items():
        cur = reg["current"]
        if cur.get("status") != 200 or "parse_error" in cur:
            print(f"  {label:26} UNAVAILABLE {cur.get('status')} {cur.get('parse_error', '')}")
            continue
        s = summarise(cur, label)
        today[label] = s
        wf = s.get("without_financials", {}).get("leverage")
        print(f"  {label:26} {s['n_firms']:>7.0f} firms  margin {s['op_margin']:6.1%}  "
              f"1% price -> {s['leverage']:5.1f}%   median industry {s['industry_median_leverage']:5.1f}%"
              f"{'   ex-financials ' + format(wf, '.1f') + '%' if wf else ''}")
    res["today"] = today
    print(f"\n  1992 claim: {CLAIM}% (margin {CLAIM_MARGIN:.1%}).")
    above = [k for k, v in today.items() if v["leverage"] >= CLAIM]
    below = [k for k, v in today.items() if v["leverage"] < CLAIM]
    print(f"  at or above 11.1 today: {', '.join(above) or 'none'}")
    print(f"  below:                  {', '.join(below) or 'none'}")

    # -------------------------------------------------- 2. the drift, by year
    hr("2. The same number, every edition (aggregate and median industry)")
    series, other_regime = {}, {}
    for label, reg in regions.items():
        pts = {}
        for yy, ed in sorted(reg["archives"].items(), key=lambda kv: edition_year(kv[0], kv[1])):
            if ed.get("status") != 200 or "parse_error" in ed:
                continue
            y = edition_year(yy, ed)
            s = summarise(ed, f"{label} {y}")
            if not s["leverage"]:
                continue
            if s["op_margin_column"] not in SAME_REGIME or y < REGIME_FROM:
                other_regime.setdefault(label, {})[y] = s
                continue
            pts[y] = s
        cur = today.get(label)
        if cur and cur["leverage"]:
            d = cur.get("date_updated") or ""
            y = int(d[:4]) if d[:4].isdigit() else max(pts, default=2025) + 1
            pts[y] = cur
        if len(pts) >= 3:
            series[label] = pts
            yrs = sorted(pts)
            print(f"\n  {label}: {len(yrs)} editions, {yrs[0]}-{yrs[-1]}")
            cols = {pts[y]["op_margin_column"] for y in yrs}
            if len(cols) > 1:
                print(f"    operating-margin header varies across editions: {sorted(map(str, cols))}")
            for y in yrs:
                p = pts[y]
                print(f"    {y}: margin {p['op_margin']:6.1%}  leverage {p['leverage']:5.1f}%  "
                      f"median industry {p['industry_median_leverage']:5.1f}%  "
                      f"({p['n_firms']:.0f} firms, {p['n_industries']} industries)"
                      f"{'' if p['leverage'] < CLAIM else '   >= 11.1'}")
    res["series"] = {k: {str(y): {kk: vv for kk, vv in v[y].items() if kk not in ('industry_min', 'industry_max')}
                         for y in v} for k, v in series.items()}
    # the other regime, reported beside the series but never joined to it
    res["other_regime"] = {}
    for label, pts in other_regime.items():
        yrs = sorted(pts)
        main = series.get(label, {})
        first_main = min(main) if main else None
        step = (round(main[first_main]["leverage"] - pts[yrs[-1]]["leverage"], 1)
                if first_main and yrs else None)
        res["other_regime"][label] = {
            "editions": {str(y): {"op_margin": pts[y]["op_margin"], "leverage": round(pts[y]["leverage"], 1),
                                  "column": pts[y]["op_margin_column"], "n_firms": pts[y]["n_firms"]} for y in yrs},
            "columns": sorted({str(pts[y]["op_margin_column"]) for y in yrs}),
            "span": [yrs[0], yrs[-1]],
            "last_edition_leverage": round(pts[yrs[-1]]["leverage"], 1),
            "first_same_regime_edition": first_main,
            "first_same_regime_leverage": round(main[first_main]["leverage"], 1) if first_main else None,
            "step_at_switch": step,
            "note": ("an earlier layout and a different column; the level moves at the "
                     "switch by more than any year-on-year change inside either regime, so the "
                     "two are never drawn on one line or compared end to end")}
        print(f"\n  {label}: {len(yrs)} earlier editions ({yrs[0]}-{yrs[-1]}) on {res['other_regime'][label]['columns']} "
              f"kept apart: last of them {pts[yrs[-1]]['leverage']:.1f}%, first same-regime edition "
              f"{first_main}: {main[first_main]['leverage']:.1f}% (step {step:+.1f})")
        for y in yrs:
            print(f"    {y}: margin {pts[y]['op_margin']:6.1%}  leverage {pts[y]['leverage']:5.1f}%  ({pts[y]['op_margin_column']})")

    # when did the US last sit at 11.1?
    us = series.get("US", {})
    if us:
        yrs = sorted(us)
        at_or_above = [y for y in yrs if us[y]["leverage"] >= CLAIM]
        res["us_last_year_at_or_above_claim"] = max(at_or_above) if at_or_above else None
        res["us_first_year"] = yrs[0]
        res["us_range"] = [round(min(us[y]["leverage"] for y in yrs), 1),
                           round(max(us[y]["leverage"] for y in yrs), 1)]
        print(f"\n  US: last edition at or above {CLAIM}: {res['us_last_year_at_or_above_claim']}; "
              f"range {res['us_range'][0]}-{res['us_range'][1]} over {yrs[0]}-{yrs[-1]}")

    # -------------------------------------------- 3. the spread, by industry
    hr("3. The spread across industries (current US edition)")
    cur = regions["US"]["current"]
    inds = sorted(industry_leverages(cur), key=lambda x: x[1])
    print(f"  {len(inds)} US industries with >= {MIN_FIRMS} firms, a margin >= {MIN_MARGIN:.0%}, financials excluded")
    print(f"  lowest leverage : {inds[0][0]} margin {inds[0][2]:.1%} -> {inds[0][1]:.1f}%")
    print(f"  highest leverage: {inds[-1][0]} margin {inds[-1][2]:.1%} -> {inds[-1][1]:.1f}%")
    ls = [x[1] for x in inds]
    share_above = sum(1 for l in ls if l >= CLAIM) / len(ls)
    print(f"  median industry {statistics.median(ls):.1f}%; {share_above:.0%} of industries at or above {CLAIM}")
    watch = []
    for w in WATCH:
        hit = next((x for x in inds if x[0] == w), None)
        if hit:
            watch.append({"industry": hit[0], "leverage": round(hit[1], 1), "op_margin": round(hit[2], 4),
                          "n_firms": int(hit[3])})
    print("  named industries:")
    for w in watch:
        print(f"    {w['industry']:34} margin {w['op_margin']:6.1%} -> {w['leverage']:5.1f}%  ({w['n_firms']} firms)")
    excl = industry_excluded(cur)
    print(f"  excluded from the spread: {sum(len(v) for v in excl.values())} "
          f"({len(excl['financial'])} financial, {len(excl['near_zero_or_negative_margin'])} margin under "
          f"{MIN_MARGIN:.0%} or negative: {excl['near_zero_or_negative_margin']}, {len(excl['too_few_firms'])} too few firms)")
    res["industries_us"] = {"n": len(inds), "share_at_or_above_claim": round(share_above, 3),
                            "excluded": excl, "min_margin": MIN_MARGIN,
                            "median": round(statistics.median(ls), 1),
                            "lowest": {"industry": inds[0][0], "leverage": round(inds[0][1], 1), "op_margin": round(inds[0][2], 4)},
                            "highest": {"industry": inds[-1][0], "leverage": round(inds[-1][1], 1), "op_margin": round(inds[-1][2], 4)},
                            "watch": watch,
                            "all": [{"industry": n, "leverage": round(l, 1), "op_margin": round(m, 4), "n_firms": int(f)}
                                    for n, l, m, f in inds]}

    # ------------------------------------------------------------ 4. checks
    hr("4. Checks")
    checks = {}
    # (a) the claim is an identity: recompute it from its own margin
    checks["identity_recovers_claim"] = round(1 / CLAIM_MARGIN, 1) == CLAIM
    print(f"  1 / {CLAIM_MARGIN:.4f} = {1 / CLAIM_MARGIN:.1f}: the identity recovers the published 11.1")
    # (b) definition sensitivity, US current: unadjusted vs pre-SBC vs ex-financials
    s = today["US"]
    sens = {"pre-tax unadjusted (headline)": s["leverage"],
            "pre-stock-compensation": s.get("leverage_pre_stock_comp"),
            "without financials": s.get("without_financials", {}).get("leverage"),
            "median industry": s["industry_median_leverage"]}
    checks["us_definition_sensitivity"] = {k: round(v, 1) for k, v in sens.items() if v}
    print("  US today under each definition: " + ", ".join(f"{k} {v:.1f}%" for k, v in sens.items() if v))
    vals = [v for v in sens.values() if v]
    checks["all_us_definitions_below_claim"] = max(vals) < CLAIM
    print(f"  every US definition below {CLAIM}: {checks['all_us_definitions_below_claim']}")
    # (c) rule 3: steps in the US series that look like a method change, not economics
    if us:
        br = mad_breaks({y: us[y]["leverage"] for y in us})
        checks["us_series_large_steps"] = br
        print(f"  US series steps beyond 3.5 MAD: {br or 'none'}")
        cols = {}
        for y in sorted(us):
            cols.setdefault(us[y]["op_margin_column"], []).append(y)
        checks["us_op_margin_headers_by_edition"] = {str(k): [min(v), max(v)] for k, v in cols.items()}
        print(f"  header used, by edition span: {checks['us_op_margin_headers_by_edition']}")
    # (d) the aggregate is revenue-weighted: how far is it from the median industry?
    gaps = {k: round(v["leverage"] - v["industry_median_leverage"], 1) for k, v in today.items()}
    checks["aggregate_minus_median_industry"] = gaps
    print(f"  aggregate minus median-industry leverage, by region: {gaps}")
    res["checks"] = checks

    # ---------------------------------------------------------- 5. verdict
    hr("5. Verdict")
    us_now = today["US"]["leverage"]
    em = today.get("Emerging markets", {}).get("leverage")
    verdict = {"us_today": round(us_now, 1), "claim": CLAIM,
               "us_gap_pct_points": round(us_now - CLAIM, 1),
               "regions_at_or_above": above, "regions_below": below,
               "closest_region": min(today, key=lambda k: abs(today[k]["leverage"] - CLAIM)),
               "emerging_today": round(em, 1) if em else None}
    res["verdict"] = verdict
    print(f"  The 1992 rule says {CLAIM}. The US aggregate today gives {us_now:.1f}. "
          f"The region closest to the rule is {verdict['closest_region']} "
          f"({today[verdict['closest_region']]['leverage']:.1f}).")

    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"\nwrote {OUT}")
    chart_regions(res)
    chart_series(res)
    return 0


# ------------------------------------------------------------------ charts
INK, DIM, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"     # validated, slots 1-3
F = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"


def chart_regions(res):
    """One hue, sorted bars, the 1992 rule as a reference line. The job is
    magnitude against a threshold, so no categorical colour."""
    t = res["today"]
    rows = sorted(t.values(), key=lambda s: -s["leverage"])
    W, H, L, R, T, B = 1600, 1000, 330, 400, 250, 150
    pw, ph = W - L - R, H - T - B
    hi = max(CLAIM, max(s["leverage"] for s in rows)) * 1.12
    slot = ph / len(rows)
    bh = min(slot * 0.62, 44)

    def px(v):
        return L + v / hi * pw

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="56" font-size="37" font-weight="700" fill="{INK}">'
         f'The 11% rule, recomputed for every region, January 2026</text>',
         f'<text x="{L}" y="100" font-size="24" fill="{DIM}">Operating profit gained from a 1% price '
         f'improvement, volume unchanged. It is one over the operating margin,</text>',
         f'<text x="{L}" y="132" font-size="24" fill="{DIM}">so it is a fact about margins: revenue-weighted '
         f'across every listed company Damodaran covers in each region.</text>',
         f'<text x="{L}" y="180" font-size="25" font-weight="700" fill="{INK}">'
         f'Built on US companies in 1992. The US today: '
         f'<tspan fill="{BLUE}">{t["US"]["leverage"]:.1f}%</tspan>. '
         f'Nearest to 11.1 now: <tspan fill="{BLUE}">{res["verdict"]["closest_region"].lower()}</tspan>.</text>']
    for i in range(0, int(hi) + 1, 2):
        o.append(f'<line x1="{px(i):.1f}" y1="{T}" x2="{px(i):.1f}" y2="{T + ph}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{px(i):.1f}" y="{T + ph + 34}" font-size="19" fill="{MUTED}" text-anchor="middle">{i}%</text>')
    for j, s in enumerate(rows):
        y = T + j * slot + (slot - bh) / 2
        o.append(f'<text x="{L - 18}" y="{y + bh / 2 + 8:.1f}" font-size="23" fill="{INK}" text-anchor="end">{s["label"]}</text>')
        o.append(f'<rect x="{L}" y="{y:.1f}" width="{px(s["leverage"]) - L:.1f}" height="{bh:.1f}" fill="{BLUE}" rx="4"/>')
        o.append(f'<text x="{px(s["leverage"]) + 12:.1f}" y="{y + bh / 2 + 8:.1f}" font-size="22" fill="{INK}" font-weight="700">'
                 f'{s["leverage"]:.1f}%</text>')
        o.append(f'<text x="{px(s["leverage"]) + 92:.1f}" y="{y + bh / 2 + 8:.1f}" font-size="18" fill="{MUTED}">'
                 f'margin {s["op_margin"]:.1%} &#183; {s["n_firms"]:,.0f} firms</text>')
    o += [f'<line x1="{px(CLAIM):.1f}" y1="{T - 14}" x2="{px(CLAIM):.1f}" y2="{T + ph}" stroke="{INK}" '
          f'stroke-width="2.5" stroke-dasharray="10 7"/>',
          f'<text x="{px(CLAIM) + 10:.1f}" y="{T - 22}" font-size="21" font-weight="700" fill="{INK}">'
          f'HBR 1992: 11.1%</text>',
          f'<text x="{L}" y="{H - 66}" font-size="22" fill="{INK}">Above the line: thinner margins than the 1992 '
          f'sample, so a price point is worth more of the profit. Below: less.</text>',
          f'<text x="{L}" y="{H - 36}" font-size="22" fill="{INK}">Aggregates include loss-makers. The median US '
          f'industry gives {t["US"]["industry_median_leverage"]:.1f}%; the spread by industry is on the page.</text>',
          f'<text x="{L}" y="{H - 10}" font-size="17" fill="{MUTED}">Data: Damodaran, NYU Stern, margin tables by '
          f'region, Total Market row, pre-tax unadjusted operating margin, Jan 2026 &#183; '
          f'namikakmandev.github.io/price-leverage.html</text>', '</svg>']
    svg = "\n".join(o)
    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/price-leverage-regions.svg"
    open(path, "w").write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/price-leverage-regions.png", W, H)


def chart_series(res):
    """Three lines against the 1992 line: the US since 1998, Europe and
    emerging markets since their archives begin. Legend plus end labels."""
    ser = res["series"]
    keys = [k for k in ("US", "Emerging markets", "Europe") if k in ser]
    col = {"US": BLUE, "Emerging markets": AQUA, "Europe": ORANGE}
    pts = {k: {int(y): v["leverage"] for y, v in ser[k].items()} for k in keys}
    y0 = min(min(p) for p in pts.values())
    y1 = max(max(p) for p in pts.values())
    lo, hi = 4, max(CLAIM, max(max(p.values()) for p in pts.values())) * 1.12
    W, H, L, R, T, B = 1600, 1000, 118, 260, 250, 150
    pw, ph = W - L - R, H - T - B

    def px(y):
        return L + (y - y0) / (y1 - y0) * pw

    def py(v):
        return T + (1 - (v - lo) / (hi - lo)) * ph

    us_last = res.get("us_last_year_at_or_above_claim")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{F}">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="56" font-size="37" font-weight="700" fill="{INK}">'
         f'The US left the 11% rule behind. Emerging markets still live on it.</text>',
         f'<text x="{L}" y="100" font-size="24" fill="{DIM}">Operating profit gained from a 1% price '
         f'improvement, one over the aggregate operating margin, one point per edition of</text>',
         f'<text x="{L}" y="132" font-size="24" fill="{DIM}">Damodaran&#8217;s industry tables. Each January '
         f'edition reflects the previous fiscal year. Dashed: the 1992 figure.</text>',
         f'<text x="{L}" y="180" font-size="25" font-weight="700" fill="{INK}">'
         + (f'US: last at or above 11.1 in <tspan fill="{BLUE}">{us_last}</tspan>; ' if us_last
            else f'US: below 11.1 in every edition since <tspan fill="{BLUE}">{min(pts["US"])}</tspan>; ')
         + f'{y1}: <tspan fill="{BLUE}">{pts["US"][max(pts["US"])]:.1f}%</tspan>.'
         + (f'   Emerging markets {max(pts["Emerging markets"])}: <tspan fill="{AQUA}">{pts["Emerging markets"][max(pts["Emerging markets"])]:.1f}%</tspan>.'
            if "Emerging markets" in pts else "") + '</text>']
    for v in range(int(lo), int(hi) + 1, 2):
        o.append(f'<line x1="{L}" y1="{py(v):.1f}" x2="{L + pw}" y2="{py(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{L - 14}" y="{py(v) + 7:.1f}" font-size="20" fill="{MUTED}" text-anchor="end">{v}%</text>')
    for y in range(y0, y1 + 1):
        if y % 2 == 0:
            o.append(f'<text x="{px(y):.1f}" y="{T + ph + 34}" font-size="19" fill="{MUTED}" text-anchor="middle">{y}</text>')
    o.append(f'<line x1="{L}" y1="{py(CLAIM):.1f}" x2="{L + pw}" y2="{py(CLAIM):.1f}" stroke="{INK}" '
             f'stroke-width="2.5" stroke-dasharray="10 7"/>')
    # the label sits where no line passes: the first year at which every series is > 1.2 points from 11.1
    free = next((y for y in range(y0, y1 + 1) if all(abs(p.get(y, 99) - CLAIM) > 1.2 for p in pts.values())), y0)
    o.append(f'<text x="{px(free):.1f}" y="{py(CLAIM) - 12:.1f}" font-size="21" font-weight="700" fill="{INK}">HBR 1992: 11.1%</text>')
    # legend, top right of the plot
    lx = L + pw - 300
    for i, k in enumerate(keys):
        ly = T + 18 + i * 32
        o.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 34}" y2="{ly}" stroke="{col[k]}" stroke-width="4"/>')
        o.append(f'<text x="{lx + 46}" y="{ly + 7}" font-size="21" fill="{INK}">{k}</text>')
    for k in keys:
        p = pts[k]
        ys = sorted(p)
        d = " ".join(f"{'M' if i == 0 else 'L'}{px(y):.1f},{py(p[y]):.1f}" for i, y in enumerate(ys))
        o.append(f'<path d="{d}" fill="none" stroke="{col[k]}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
        for y in ys:
            o.append(f'<circle cx="{px(y):.1f}" cy="{py(p[y]):.1f}" r="5" fill="{col[k]}" stroke="#fff" stroke-width="2"/>')
        yl = ys[-1]
        o.append(f'<text x="{px(yl) + 14:.1f}" y="{py(p[yl]) + 8:.1f}" font-size="22" font-weight="700" fill="{INK}">'
                 f'{p[yl]:.1f}%</text>')
    o += [f'<text x="{L}" y="{H - 66}" font-size="22" fill="{INK}">Same identity, same source, every year: the '
          f'line moves only because operating margins do. US margins widened; emerging-market margins did not.</text>',
          f'<text x="{L}" y="{H - 36}" font-size="22" fill="{INK}">Editions are labelled by publication year. '
          f'No 2025 edition is served. Pre-2013 US editions: see the note on the page.</text>',
          f'<text x="{L}" y="{H - 10}" font-size="17" fill="{MUTED}">Data: Damodaran, NYU Stern, archived industry '
          f'margin tables margin&lt;yy&gt;.xls, Total Market row, pre-tax operating margin as labelled in each edition '
          f'&#183; namikakmandev.github.io/price-leverage.html</text>', '</svg>']
    svg = "\n".join(o)
    path = "assets/linkedin/price-leverage-series.svg"
    open(path, "w").write(svg)
    print(f"  wrote {path}")
    render_png(svg, "assets/linkedin/price-leverage-series.png", W, H)


if __name__ == "__main__":
    sys.exit(main())
