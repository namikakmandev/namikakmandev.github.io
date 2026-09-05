#!/usr/bin/env python3
"""Collect Damodaran's industry margin tables -> data/price-leverage.json

The claim under test is Marn & Rosiello (Harvard Business Review, 1992): a
1% improvement in price raises operating profit by 11.1%. That number is an
identity — revenue over operating profit, so one over the operating margin of
whatever sample you average. This fetch collects the margins the identity
needs today: Damodaran's industry averages for the US, Europe, emerging
markets, Japan, China, India, Australia/NZ/Canada and the world, plus every
archived edition he still serves (the US goes back to 1998).

What the probe established (data/_margin-archive-probe.json):
  - each file is BIFF .xls with a 'Variables & FAQ' sheet and an 'Industry
    Averages' sheet, header on the row that starts 'Industry Name';
  - the column wanted is 'Pre-tax Unadjusted Operating Margin' — operating
    income before tax, after all operating costs, no lease or R&D
    capitalisation — which is the closest match to the article's operating
    profit. Older editions may name it differently, so the column is located
    by header text per file and the header used is recorded per edition;
  - the aggregate row is 'Total Market' (Europe: 'Grand Total'), a
    revenue-weighted sum, which is the same construction as the article's
    'average income statement';
  - 'Date updated:' in the first rows carries an Excel serial date.

xlrd is needed to read BIFF and is installed by the workflow; the site's
analysis script stays stdlib-only. The dev sandbox cannot reach NYU Stern,
so this runs in GitHub Actions and commits the result.
"""
import datetime, json, re, sys, time, urllib.error, urllib.request

try:
    import xlrd
except ImportError:                              # pragma: no cover
    sys.exit("xlrd is required: pip install xlrd==2.0.1")

OUT = "data/price-leverage.json"
BASE = "https://pages.stern.nyu.edu/~adamodar/"
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; +https://namikakmandev.github.io)"}
CAP = 8 * 1024 * 1024

REGIONS = {                                       # label -> file stem
    "US": "margin", "Europe": "marginEurope", "Emerging markets": "marginemerg",
    "Global": "marginGlobal", "Japan": "marginJapan", "Australia, NZ & Canada": "marginRest",
    "China": "marginChina", "India": "marginIndia",
}
ARCHIVE_YY = ["98", "99"] + [f"{y:02d}" for y in range(0, 26)]


def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(CAP + 1)
    if len(body) > CAP:
        raise RuntimeError(f"response exceeded {CAP:,}b cap: {url}")
    return body


def excel_date(v):
    """Excel serial -> ISO date; anything else is returned as text."""
    try:
        f = float(v)
        if 20000 < f < 80000:
            return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(f))).isoformat()
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s or None


def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s or s.upper() in ("NA", "N/A", "#DIV/0!", "#N/A", "-"):
        return None
    if s.endswith("%"):
        try:
            return float(s[:-1]) / 100.0
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def pick(headers, *rules):
    """First header matching a rule; a rule is (must_contain, must_not_contain)."""
    low = [str(h).strip().lower().replace("\n", " ") for h in headers]
    low = [re.sub(r"\s+", " ", h) for h in low]
    for must, must_not in rules:
        for i, h in enumerate(low):
            if all(m in h for m in must) and not any(n in h for n in must_not):
                return i, headers[i]
    return None, None


def find_header(wb):
    """The 'Industry Name' row, in whichever sheet and column it sits. Old
    editions put the table on 'Sheet3' or start it in column B."""
    order = sorted(wb.sheet_names(), key=lambda n: (n != "Industry Averages", n))
    for name in order:
        sh = wb.sheet_by_name(name)
        for r in range(min(sh.nrows, 80)):
            for c in range(min(sh.ncols, 3)):
                v = str(sh.cell_value(r, c)).strip().lower()
                if v.startswith("industry") or v in ("sector", "industry group"):
                    return sh, r, c
    return None, None, None


def parse_workbook(body, full=True):
    wb = xlrd.open_workbook(file_contents=body)
    sh, hdr, c0 = find_header(wb)
    if sh is None:
        first = wb.sheet_by_index(0)
        peek = [[str(first.cell_value(r, c))[:40] for c in range(min(first.ncols, 6))]
                for r in range(min(first.nrows, 14))]
        raise ValueError(f"no 'Industry Name' header in sheets {wb.sheet_names()}; first rows {peek}")
    name = sh.name
    rows = [[sh.cell_value(r, c) for c in range(c0, sh.ncols)] for r in range(sh.nrows)]

    date_updated = None
    for r in [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(min(sh.nrows, 12))]:
        for i, v in enumerate(r[:3]):
            if str(v).strip().lower().startswith("date"):
                date_updated = excel_date(r[i + 1]) if len(r) > i + 1 else None
                break
        if date_updated:
            break
    headers = [str(h).strip() for h in rows[hdr]]

    i_n, h_n = pick(headers, (("number of firms",), ()), (("numebr of firms",), ()), (("firms",), ()))
    i_op, h_op = pick(headers,
                      (("pre-tax", "unadjusted", "operating margin"), ()),
                      (("pre-tax", "operating margin"), ("pre-stock", "lease", "r&d", "after-tax")),
                      (("operating margin",), ("after-tax", "pre-stock", "lease", "r&d", "(1-t)")),
                      (("operating margin",), ("(1-t)", "after-tax")))
    op_kind = "pre-tax" if i_op is not None else None
    i_tax, h_tax = pick(headers, (("tax rate",), ()), (("effective tax",), ()))
    if i_op is None:
        # only an after-tax operating margin: keep it, flagged, and back out
        # pre-tax where the same row carries a tax rate
        i_op, h_op = pick(headers, (("operating margin",), ()), (("ebit", "sales"), ("ebitda",)))
        op_kind = "after-tax" if i_op is not None else None
    i_net, h_net = pick(headers, (("net margin",), ()))
    i_gross, h_gross = pick(headers, (("gross margin",), ()))
    i_ebitda, h_ebitda = pick(headers, (("ebitda/sales",), ()), (("ebitda",), ("sg&a", "r&d")))
    i_sbc, h_sbc = pick(headers, (("pre-stock",), ()))
    if i_op is None:
        raise ValueError(f"no operating margin column among {headers}")

    industries, totals = [], {}
    for r in rows[hdr + 1:]:
        label = str(r[0]).strip()
        if not label:
            continue
        op = num(r[i_op]) if i_op < len(r) else None
        rec = {"n_firms": num(r[i_n]) if i_n is not None and i_n < len(r) else None,
               "op_margin": op,
               "net_margin": num(r[i_net]) if i_net is not None and i_net < len(r) else None}
        if op_kind == "after-tax":
            rec["op_margin_after_tax"] = op
            t = num(r[i_tax]) if i_tax is not None and i_tax < len(r) else None
            rec["tax_rate"] = t
            rec["op_margin"] = op / (1 - t) if (op is not None and t is not None and t < 1) else None
        if full:
            rec.update(gross_margin=num(r[i_gross]) if i_gross is not None and i_gross < len(r) else None,
                       ebitda_sales=num(r[i_ebitda]) if i_ebitda is not None and i_ebitda < len(r) else None,
                       op_margin_pre_sbc=num(r[i_sbc]) if i_sbc is not None and i_sbc < len(r) else None)
        low = label.lower()
        if low.startswith(("total", "grand total", "market", "all ")):
            totals[label] = rec
        else:
            rec["name"] = label
            industries.append(rec)
    return {"sheet": name, "header_row": hdr + 1, "header_col": c0 + 1, "date_updated": date_updated,
            "header": headers,
            "columns_used": {"n_firms": h_n, "op_margin": h_op, "op_margin_kind": op_kind,
                             "tax_rate": h_tax if op_kind == "after-tax" else None,
                             "net_margin": h_net, "gross_margin": h_gross, "ebitda_sales": h_ebitda,
                             "op_margin_pre_sbc": h_sbc},
            "n_industries": len(industries), "totals": totals, "industries": industries}


def edition(url, full):
    try:
        body = get(url)
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code}
    rec = {"url": url, "status": 200, "bytes": len(body)}
    try:
        rec.update(parse_workbook(body, full=full))
    except Exception as e:                       # noqa: BLE001 — record, keep going
        rec["parse_error"] = f"{type(e).__name__}: {e}"
    return rec


def main():
    doc = {"generated_by": "scripts/fetch_price_leverage.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "question": ("Does a 1% price improvement still raise operating profit by 11.1% "
                        "(Marn & Rosiello, HBR 1992)? Price leverage = 1 / operating margin."),
           "source": {"publisher": "Aswath Damodaran, NYU Stern, damodaran.com",
                      "current": BASE + "pc/datasets/<stem>.xls",
                      "archives": BASE + "pc/archives/<stem><yy>.xls",
                      "index": BASE + "New_Home_Page/datacurrent.html",
                      "archive_index": BASE + "New_Home_Page/dataarchived.html",
                      "note": ("Damodaran computes industry averages from listed-company "
                               "financials (Capital IQ), revenue-weighted within each industry; "
                               "'Total Market' is the revenue-weighted aggregate of every firm.")},
           "definition": ("op_margin is the column recorded in columns_used.op_margin for each "
                          "edition — 'Pre-tax Unadjusted Operating Margin' where the edition "
                          "has it. Editions are labelled by the year in the file name; "
                          "date_updated is read from the sheet."),
           "regions": {}}
    for label, stem in REGIONS.items():
        print(f"== {label}", flush=True)
        reg = {"stem": stem, "current": edition(BASE + f"pc/datasets/{stem}.xls", full=True), "archives": {}}
        cur = reg["current"]
        print(f"  current: {cur.get('status')} {cur.get('date_updated')} "
              f"{cur.get('n_industries')} industries, op col = {cur.get('columns_used', {}).get('op_margin')!r}",
              flush=True)
        for yy in ARCHIVE_YY:
            e = edition(BASE + f"pc/archives/{stem}{yy}.xls", full=False)
            if e.get("status") == 200:
                reg["archives"][yy] = e
                if "parse_error" in e:
                    print(f"  {yy}: PARSE ERROR {e['parse_error'][:300]}", flush=True)
                    continue
                tot = next(iter(e.get("totals", {}).items()), (None, {}))
                print(f"  {yy}: {e.get('date_updated')} {e.get('n_industries')} ind, "
                      f"op col = {e.get('columns_used', {}).get('op_margin')!r}, "
                      f"{tot[0]} op_margin={tot[1].get('op_margin')}", flush=True)
            time.sleep(0.2)
        doc["regions"][label] = reg
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=0, ensure_ascii=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
