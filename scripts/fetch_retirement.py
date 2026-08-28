#!/usr/bin/env python3
"""Build the annual return series behind the 4% rule, from Robert Shiller's data.

Source: the open mirror of Robert Shiller's monthly series (github.com/datasets/
s-and-p-500) — S&P 500 price, dividend, CPI and the long government bond yield,
January 1871 onward. This is the public stand-in for the inputs Bengen (1994)
and Cooley, Hubbard & Walz (1998, "the Trinity Study") used; neither paper's
exact bond series is public, which is the main caveat this study carries.

Produces one row per calendar year, January to January:

  stock   S&P 500 total return: price change plus the dividends paid that year
  bond    total return on a constant-maturity government bond, constructed by
          buying it at par and selling it a year later one year shorter, at the
          new yield. Built at 10 and at 5 years so the analysis can show what
          the bond assumption is worth.
  cpi     inflation, which is what the withdrawal is indexed to

Usage:  python3 scripts/fetch_retirement.py
"""
import argparse, csv, io, json, os, sys, urllib.request
from datetime import date

SRC = ("https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/"
       "data.csv")
MATURITIES = (10, 5)


def bond_price(coupon, years, yld):
    """Price of an annual-coupon bond, face 1."""
    if yld == 0:
        return coupon * years + 1.0
    disc = (1 + yld) ** -years
    return coupon * (1 - disc) / yld + disc


def bond_total_return(y0, y1, maturity):
    """Buy at par, hold one year, sell one year shorter at the new yield.

    This is the standard constant-maturity construction. It is a proxy: Bengen
    used intermediate Treasuries and the Trinity Study used long-term corporate
    bonds, and neither series is public. Running it at two maturities is how
    this study shows what the choice costs.
    """
    return bond_price(y0, maturity - 1, y1) + y0 - 1.0


def load_rows(url):
    print(f"  downloading {url} ...")
    with urllib.request.urlopen(url, timeout=300) as r:
        text = r.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def num(row, key):
    """Shiller's mirror writes 0 for 'not filled in yet'; treat that as missing."""
    v = row.get(key, "")
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f == 0 else f


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/retire-us.json")
    args = ap.parse_args(argv)

    print("Shiller monthly series")
    rows = load_rows(SRC)
    print(f"  read {len(rows):,} months, "
          f"{rows[0]['Date']} to {rows[-1]['Date']}")

    by_month = {}
    for r in rows:
        y, m, _ = r["Date"].split("-")
        by_month[(int(y), int(m))] = r

    years = sorted({y for y, _ in by_month})
    out = []
    for y in years:
        jan0, jan1 = by_month.get((y, 1)), by_month.get((y + 1, 1))
        if not jan0 or not jan1:
            continue
        p0, p1 = num(jan0, "SP500"), num(jan1, "SP500")
        c0, c1 = (num(jan0, "Consumer Price Index"),
                  num(jan1, "Consumer Price Index"))
        y0, y1 = (num(jan0, "Long Interest Rate"),
                  num(jan1, "Long Interest Rate"))
        # Shiller's Dividend column is the annualised rate in force each month;
        # averaging the twelve months gives the dividend actually paid that year.
        divs = [num(by_month[(y, m)], "Dividend") for m in range(1, 13)
                if (y, m) in by_month]
        divs = [d for d in divs if d is not None]
        if not all((p0, p1, c0, c1, y0, y1)) or len(divs) < 12:
            continue
        d = sum(divs) / len(divs)

        row = {"year": y,
               "stock": round((p1 + d) / p0 - 1, 6),
               "cpi": round(c1 / c0 - 1, 6)}
        for mat in MATURITIES:
            row[f"bond{mat}"] = round(
                bond_total_return(y0 / 100.0, y1 / 100.0, mat), 6)
        out.append(row)

    doc = {
        "source": "Robert Shiller, monthly US stock market and CPI data",
        "source_url": "https://github.com/datasets/s-and-p-500",
        "note": ("Public mirror of Shiller's series. Prices run to the present, "
                 "but the dividend, CPI and yield columns lag, so complete "
                 "return years end earlier — see coverage below."),
        "fetched_by": "scripts/fetch_retirement.py",
        "fetched_at": date.today().isoformat(),
        "definitions": {
            "stock": "S&P 500 total return, January to January, dividends included",
            "bond10": "constant-maturity 10-year government bond total return",
            "bond5": "same construction at 5 years, to price the assumption",
            "cpi": "January-to-January inflation, what the withdrawal is indexed to",
        },
        "caveat": ("Bengen (1994) used intermediate-term Treasuries; Cooley, "
                   "Hubbard & Walz (1998) used long-term high-grade corporate "
                   "bonds. Neither series is public. These are government-bond "
                   "proxies and the replication is only as good as that."),
        "coverage": {"first_year": out[0]["year"], "last_year": out[-1]["year"],
                     "n_years": len(out)},
        "years": out,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(doc, fh, indent=1)

    print(f"  built {len(out)} complete return years: "
          f"{out[0]['year']}–{out[-1]['year']}")
    print(f"  wrote {args.out} ({os.path.getsize(args.out):,} bytes)")
    for r in out[:2] + out[-2:]:
        print(f"    {r['year']}  stock={r['stock']:+.4f}  "
              f"bond10={r['bond10']:+.4f}  cpi={r['cpi']:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
