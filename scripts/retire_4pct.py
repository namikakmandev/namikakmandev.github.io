#!/usr/bin/env python3
"""Replication of the 4% rule, then a retest with the data the authors lacked.

Two papers, one rule:

  Bengen (1994), "Determining Withdrawal Rates Using Historical Data" — a
    retiree drawing 4% of the starting portfolio, raised each year with
    inflation, from a stock/bond mix, never ran out inside 30 years in any
    starting year on record.
  Cooley, Hubbard & Walz (1998), the "Trinity Study" — the same exercise
    reported as success rates. At 4% over 30 years, inflation-adjusted, they
    published 95% for a 50/50 portfolio and 98% for 75/25, over 1926-1995.

Their sample is 41 overlapping 30-year windows, so those figures are 2 failures
and 1 failure respectively. That is the target this replication has to hit.

It lands one failure short of each, and the reason is the bond series. They held
long-term high-grade CORPORATE bonds; the only public series is government. Add
the credit spread back and the published figures reproduce exactly — which is
itself the finding, because the rule is never quoted with "and you must hold
corporate credit risk" attached.

Stage 1 replicates their window. Stage 2 asks the question they could not: the
rule has since been quoted for twenty-seven more years of history, including
2000-02, 2008 and 2022. Does it still hold?

Stdlib only, deterministic.

  python3 scripts/retire_4pct.py
"""
import json, sys
from collections import defaultdict

PANEL = "data/retire-us.json"
TRINITY_FIRST, TRINITY_LAST = 1926, 1995      # the 1998 paper's sample
PUBLISHED = {0.50: 0.95, 0.75: 0.98}          # their 4%/30y figures


# ---------------------------------------------------------------- simulation

def simulate(rows, i0, rate, horizon, alloc, fee=0.0, bond="bond10",
             timing="start", spread=0.0):
    """One retirement. -> (survived, ending balance in start-year money).

    The withdrawal is a fixed share of the STARTING portfolio, raised by
    inflation every year — not a share of the current balance. That is what
    makes the rule able to fail at all, and it is what both papers modelled.
    """
    bal, draw, infl = 1.0, rate, 1.0
    for k in range(horizon):
        r = rows[i0 + k]
        if timing == "start":
            bal -= draw
            if bal <= 0:
                return False, 0.0
        bal *= (1 + alloc * r["stock"]
                + (1 - alloc) * (r[bond] + spread) - fee)
        if timing == "end":
            bal -= draw
        if bal <= 0:
            return False, 0.0
        infl *= 1 + r["cpi"]
        draw *= 1 + r["cpi"]
    return True, bal / infl


def windows(rows, horizon, first=None, last=None):
    """Every starting year whose full horizon fits inside [first, last]."""
    out = []
    for i, r in enumerate(rows):
        if first is not None and r["year"] < first:
            continue
        if i + horizon > len(rows):
            break
        if last is not None and rows[i + horizon - 1]["year"] > last:
            break
        out.append(i)
    return out


def run(rows, rate, horizon, alloc, first=None, last=None, **kw):
    idx = windows(rows, horizon, first, last)
    res = [(rows[i]["year"],) + simulate(rows, i, rate, horizon, alloc, **kw)
           for i in idx]
    ok = [r for r in res if r[1]]
    return {"n": len(res), "fail": len(res) - len(ok),
            "rate": len(ok) / len(res) if res else float("nan"),
            "ends": sorted(r[2] for r in ok),
            "failures": [r[0] for r in res if not r[1]], "all": res}


def pct(xs, p):
    if not xs:
        return float("nan")
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def safemax(rows, horizon, alloc, first=None, last=None, **kw):
    """Highest withdrawal rate (to 0.01pp) at which no window failed."""
    lo, hi = 0.0, 0.15
    for _ in range(40):
        mid = (lo + hi) / 2
        if run(rows, mid, horizon, alloc, first, last, **kw)["fail"] == 0:
            lo = mid
        else:
            hi = mid
    return lo


# ---------------------------------------------------------------- report

def hr(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def grid(rows, rates, allocs, horizon, first=None, last=None, **kw):
    print(f"    {'withdrawal':<12}" + "".join(f"{int(a * 100):>7}/{int(100 - a * 100):<7}"
                                              for a in allocs))
    for w in rates:
        cells = []
        for a in allocs:
            r = run(rows, w, horizon, a, first, last, **kw)
            cells.append(f"{r['rate'] * 100:>6.0f}%{'':7}")
        print(f"    {w * 100:>9.1f}%  " + "".join(cells))


def main():
    doc = json.load(open(PANEL))
    rows = doc["years"]
    cov = doc["coverage"]

    hr("0. The data")
    print(f"  source      {doc['source']}")
    print(f"  mirror      {doc['source_url']}")
    print(f"  coverage    {cov['first_year']}–{cov['last_year']}  "
          f"({cov['n_years']} complete return years)")
    print(f"  caveat      {doc['caveat']}")

    hr("1. Replication — the Trinity Study's own window, 1926–1995")
    print("  Published: 4% over 30 years, inflation-adjusted, succeeded in 95% of")
    print("  periods at 50/50 and 98% at 75/25. Their sample is 41 overlapping")
    print("  windows, so that is 2 failures and 1 failure.\n")
    for alloc, target in sorted(PUBLISHED.items()):
        r = run(rows, 0.04, 30, alloc, TRINITY_FIRST, TRINITY_LAST)
        mark = "MATCH" if r["fail"] == round((1 - target) * r["n"]) else "differs"
        print(f"    {int(alloc * 100)}/{int(100 - alloc * 100)} stocks/bonds:  "
              f"{r['rate'] * 100:.0f}% success  ({r['fail']} failures of "
              f"{r['n']} windows)   published {target * 100:.0f}%  -> {mark}")
        if r["failures"]:
            print(f"        failing retirement years: {r['failures']}")

    print("\n  the full published-style table, 30 years, inflation-adjusted, "
          "1926–1995:")
    grid(rows, (0.03, 0.04, 0.05, 0.06, 0.07),
         (1.0, 0.75, 0.5, 0.25, 0.0), 30, TRINITY_FIRST, TRINITY_LAST)

    hr("1b. Reconciling the gap — what the missing bond series is worth")
    print("  Both published figures come out one failure higher than this")
    print("  replication. The candidate explanation is the asset: they held")
    print("  long-term high-grade corporate bonds, and the public series is")
    print("  government. Adding a credit spread back to the bond leg:\n")
    print(f"      {'spread over govt':<20}{'50/50':>14}{'75/25':>14}")
    for sp in (0.0, 0.005, 0.010, 0.015, 0.020):
        a = run(rows, 0.04, 30, 0.50, TRINITY_FIRST, TRINITY_LAST, spread=sp)
        b = run(rows, 0.04, 30, 0.75, TRINITY_FIRST, TRINITY_LAST, spread=sp)
        star = ""
        if round(a["rate"], 2) == 0.95 and round(b["rate"], 2) == 0.98:
            star = "   <- reproduces both"
        print(f"      {sp * 100:>15.1f}%     {a['rate'] * 100:>8.0f}%"
              f"{b['rate'] * 100:>13.0f}%{star}")
    print("\n      published:                    95%           98%")
    print("      A spread of half a point already reproduces the 50/50 figure,")
    print("      and one and a half points reproduces both. Historically that is")
    print("      an ordinary high-grade spread, so the replication succeeds — on")
    print("      the condition that the retiree holds corporate bonds. Everything")
    print("      below stays on government bonds, which is the conservative read.")

    hr("2. Bengen's claim — the highest rate that never failed")
    for label, first, last in (("1926–1995 (their data)", TRINITY_FIRST, TRINITY_LAST),
                               ("1926–2022 (with what came after)", TRINITY_FIRST, None),
                               ("1871–2022 (everything on record)", None, None)):
        for alloc in (0.75, 0.5):
            s = safemax(rows, 30, alloc, first, last)
            n = run(rows, 0.04, 30, alloc, first, last)
            print(f"    {label:<34} {int(alloc * 100)}/{int(100 - alloc * 100)}:  "
                  f"SAFEMAX {s * 100:.2f}%   "
                  f"4% success {n['rate'] * 100:.0f}% ({n['n']} windows)")

    hr("3. What 'success' actually means")
    r = run(rows, 0.04, 30, 0.5, TRINITY_FIRST, None)
    ends = r["ends"]
    broke = sum(1 for e in ends if e < 1.0)
    print("  A 'success' is a portfolio that did not hit zero. It is not a")
    print("  portfolio that kept its value. 4%, 30 years, 50/50, 1926–2022:\n")
    print(f"    success rate                      {r['rate'] * 100:.0f}% "
          f"({r['n']} windows)")
    print(f"    median ending wealth              {pct(ends, 0.5):.2f}x the "
          f"starting capital, in real terms")
    print(f"    worst 10% of outcomes ended at    {pct(ends, 0.10):.2f}x")
    print(f"    best  10% ended at                {pct(ends, 0.90):.2f}x")
    print(f"    ended poorer than they started    {broke} of {len(ends)} "
          f"({broke / len(ends) * 100:.0f}%)")
    print("    The rule's promise is 'you will not run out'. The spread of what")
    print("    you actually end with is enormous, and it is not in the promise.")

    print("\n  4% is a 30-year answer. It is quoted as if it were permanent:")
    for h in (30, 40, 50):
        rr = run(rows, 0.04, h, 0.5, TRINITY_FIRST, None)
        print(f"    {h}-year retirement, 50/50:        "
              f"{rr['rate'] * 100:>3.0f}% success  ({rr['n']} windows)")

    print("\n  And it is a before-costs answer. The same test with a fee drag:")
    for fee in (0.0, 0.005, 0.01, 0.02):
        rr = run(rows, 0.04, 30, 0.5, TRINITY_FIRST, None, fee=fee)
        s = safemax(rows, 30, 0.5, TRINITY_FIRST, None, fee=fee)
        print(f"    fee {fee * 100:>4.1f}%/yr:                     "
              f"{rr['rate'] * 100:>3.0f}% success   SAFEMAX {s * 100:.2f}%")

    hr("4. The retest — 27 years the authors never saw")
    print("  The 1998 paper stops in 1995. Every retirement beginning 1966 or")
    print("  later was still running when they published. Those windows have")
    print("  since completed, and they include 2000-02, 2008 and 2022.\n")
    for alloc in (0.75, 0.5):
        old = run(rows, 0.04, 30, alloc, TRINITY_FIRST, TRINITY_LAST)
        new = run(rows, 0.04, 30, alloc, TRINITY_FIRST, None)
        added = new["n"] - old["n"]
        print(f"    {int(alloc * 100)}/{int(100 - alloc * 100)}:  published window "
              f"{old['rate'] * 100:.0f}% ({old['n']} windows)  ->  "
              f"through 2022 {new['rate'] * 100:.0f}% ({new['n']} windows, "
              f"{added} added)")
        if new["failures"]:
            print(f"        failing retirement years now: {new['failures']}")

    hr("5. Robustness")
    print("  5a. how many independent tests is '41 windows' really?")
    idx = windows(rows, 30, TRINITY_FIRST, None)
    non = [i for k, i in enumerate(idx) if k % 30 == 0]
    print(f"      overlapping 30-year windows, 1926–2022      {len(idx)}")
    print(f"      non-overlapping ones                        {len(non)}")
    print("      Consecutive windows share 29 of their 30 years. '95% of all")
    print("      historical periods' is three independent retirements and a bit.")

    print("\n  5b. the bond series, which is the weakest joint")
    for bond in ("bond10", "bond5"):
        rr = run(rows, 0.04, 30, 0.5, TRINITY_FIRST, None, bond=bond)
        s = safemax(rows, 30, 0.5, TRINITY_FIRST, None, bond=bond)
        print(f"      {bond:<8} 4% success {rr['rate'] * 100:>3.0f}%   "
              f"SAFEMAX {s * 100:.2f}%")

    print("\n  5c. withdrawing at the start of the year vs the end")
    for timing in ("start", "end"):
        rr = run(rows, 0.04, 30, 0.5, TRINITY_FIRST, None, timing=timing)
        s = safemax(rows, 30, 0.5, TRINITY_FIRST, None, timing=timing)
        print(f"      {timing:<8} 4% success {rr['rate'] * 100:>3.0f}%   "
              f"SAFEMAX {s * 100:.2f}%")

    print("\n  5d. the whole record, not just the post-1926 one")
    for first, label in ((None, "1871–2022"), (TRINITY_FIRST, "1926–2022")):
        rr = run(rows, 0.04, 30, 0.5, first, None)
        s = safemax(rows, 30, 0.5, first, None)
        print(f"      {label}  4% success {rr['rate'] * 100:>3.0f}%   "
              f"SAFEMAX {s * 100:.2f}%   ({rr['n']} windows)")

    print("\n  5e. the retirements that actually failed, and when they began")
    rr = run(rows, 0.04, 30, 0.5, None, None)
    print(f"      1871–2022, 4%, 50/50: {rr['fail']} failures of {rr['n']} — "
          f"years {rr['failures']}")

    # ------------------------------------------------------------------ export
    def pack(r):
        return {"success": round(r["rate"], 4), "n": r["n"], "fail": r["fail"],
                "failures": r["failures"]}

    out = {
        "generated_by": "scripts/retire_4pct.py",
        "source_url": doc["source_url"], "fetched_at": doc["fetched_at"],
        "coverage": cov,
        "published_targets": {"trinity_50_50": 0.95, "trinity_75_25": 0.98,
                              "window": f"{TRINITY_FIRST}-{TRINITY_LAST}"},
        "replication": {f"{int(a * 100)}_{int(100 - a * 100)}":
                        pack(run(rows, 0.04, 30, a, TRINITY_FIRST, TRINITY_LAST))
                        for a in PUBLISHED},
        "retest": {f"{int(a * 100)}_{int(100 - a * 100)}":
                   pack(run(rows, 0.04, 30, a, TRINITY_FIRST, None))
                   for a in PUBLISHED},
        "spread_reconciliation": {
            f"{sp:.3f}": {"50_50": round(run(rows, 0.04, 30, 0.50, TRINITY_FIRST,
                                             TRINITY_LAST, spread=sp)["rate"], 4),
                          "75_25": round(run(rows, 0.04, 30, 0.75, TRINITY_FIRST,
                                             TRINITY_LAST, spread=sp)["rate"], 4)}
            for sp in (0.0, 0.005, 0.010, 0.015, 0.020)},
        "timing": {t: {"success": round(run(rows, 0.04, 30, 0.5, TRINITY_FIRST,
                                            None, timing=t)["rate"], 4),
                       "safemax": round(safemax(rows, 30, 0.5, TRINITY_FIRST,
                                                None, timing=t) * 100, 2)}
                   for t in ("start", "end")},
        "windows": {"overlapping": len(windows(rows, 30, TRINITY_FIRST, None)),
                    "non_overlapping": len(
                        [i for k, i in enumerate(windows(rows, 30, TRINITY_FIRST,
                                                         None)) if k % 30 == 0])},
        "all_failures_1871": run(rows, 0.04, 30, 0.5)["failures"],
        "by_start_year": [{"year": y, "survived": ok, "ending": round(end, 4)}
                          for y, ok, end in run(rows, 0.04, 30, 0.5)["all"]],
        "safemax": {"trinity_window": round(safemax(rows, 30, 0.5, TRINITY_FIRST,
                                                    TRINITY_LAST) * 100, 2),
                    "through_2022": round(safemax(rows, 30, 0.5, TRINITY_FIRST,
                                                  None) * 100, 2),
                    "full_record": round(safemax(rows, 30, 0.5) * 100, 2)},
        "horizons": {str(h): pack(run(rows, 0.04, h, 0.5, TRINITY_FIRST, None))
                     for h in (30, 40, 50)},
        "fees": {str(f): {**pack(run(rows, 0.04, 30, 0.5, TRINITY_FIRST, None,
                                     fee=f)),
                          "safemax": round(safemax(rows, 30, 0.5, TRINITY_FIRST,
                                                   None, fee=f) * 100, 2)}
                 for f in (0.0, 0.005, 0.01, 0.02)},
        "ending_wealth": {"p10": round(pct(ends, 0.10), 3),
                          "median": round(pct(ends, 0.50), 3),
                          "p90": round(pct(ends, 0.90), 3),
                          "share_below_start": round(broke / len(ends), 4),
                          "n": len(ends)},
        "grid": {f"{w:.3f}": {f"{int(a * 100)}": round(
            run(rows, w, 30, a, TRINITY_FIRST, None)["rate"], 4)
            for a in (1.0, 0.75, 0.5, 0.25, 0.0)}
            for w in (0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07)},
        "grid_fee1": {f"{w:.3f}": round(
            run(rows, w, 30, 0.5, TRINITY_FIRST, None, fee=0.01)["rate"], 4)
            for w in (0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07)},
        "grid_50y": {f"{w:.3f}": round(
            run(rows, w, 50, 0.5, TRINITY_FIRST, None)["rate"], 4)
            for w in (0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07)},
    }
    with open("data/retire-results.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print("\n  wrote data/retire-results.json\n")


if __name__ == "__main__":
    sys.exit(main())
