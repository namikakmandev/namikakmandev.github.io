#!/usr/bin/env python3
"""Availability probe for the "1% price = 11.1% operating profit" retest
-> data/_price-leverage-probe.json

Marn & Rosiello (HBR, 1992) built the 11.1% from the average income statement
of a large company sample: price leverage is revenue over operating profit, so
an operating margin of about 9% gives 11.1. The retest needs, for as many
listed companies as possible, revenue and operating income for the same fiscal
year, plus an industry code and ideally a region.

Three candidate sources, none touched from here before:

  1. SEC XBRL "frames" API: one call returns one concept for every filer in a
     calendar year. If Revenues and OperatingIncomeLoss both come back with
     thousands of entities, the whole US panel is a handful of requests.
  2. SEC Financial Statement Data Sets: quarterly bulk zips with sub.txt
     (which carries the SIC code) and num.txt. Heavier, but the industry key.
  3. Damodaran's industry margin tables (US, Europe, emerging, global). The
     region split comes only from here, and the files are .xls, which the
     stdlib cannot read — that limitation is recorded, not solved, here.

Discovery only. A 200 is not access: paired requests, byte counts, capped
heads, and column names read from the responses before any parser exists.

Run in GitHub Actions — this sandbox reaches none of these hosts.
"""
import collections, io, json, re, statistics, sys, time, urllib.error, urllib.request, zipfile

OUT = "data/_price-leverage-probe.json"
CAP = 24 * 1024 * 1024
BIG = 260 * 1024 * 1024
# SEC asks for an identifying User-Agent on every request and throttles at 10/s.
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; availability probe; +https://namikakmandev.github.io)",
      "Accept-Encoding": "gzip, deflate"}
HEAD = 1200

REV_TAGS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]
OPINC_TAG = "OperatingIncomeLoss"


def fetch(url, cap=CAP, timeout=300):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(cap + 1)
        enc = r.headers.get("Content-Encoding", "")
        ctype = r.headers.get("Content-Type", "")
        clen = r.headers.get("Content-Length")
    if enc == "gzip":
        import gzip
        body = gzip.decompress(body)
    return body[:cap], len(body) > cap, ctype, clen


def route(name, url, note, keep_body=False, cap=CAP):
    rec = {"name": name, "url": url, "note": note}
    t0 = time.time()
    body = b""
    try:
        body, capped, ctype, clen = fetch(url, cap=cap)
        rec.update(status=200, content_type=ctype, declared_length=clen,
                   capped=capped, bytes=len(body), magic=body[:4].hex(),
                   head=body[:HEAD].decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error=str(e),
                   head=(e.read(HEAD) or b"").decode("utf-8", "replace"))
    except Exception as e:                       # noqa: BLE001
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    rec["seconds"] = round(time.time() - t0, 1)
    print(f"  {name}: {rec.get('status')} {rec.get('bytes', 0):,}b {rec['seconds']}s", flush=True)
    time.sleep(0.15)                              # stay well under SEC's 10/s
    return (rec, body) if keep_body else rec


# ------------------------------------------------------------ 1. SEC frames
def frames(tag, period):
    return f"https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/{period}.json"


def parse_frame(body):
    j = json.loads(body.decode("utf-8", "replace"))
    data = j.get("data", [])
    return {"label": j.get("label"), "description": (j.get("description") or "")[:200],
            "n": len(data), "sample": data[:2],
            "by_cik": {d["cik"]: d["val"] for d in data if "cik" in d and "val" in d}}


def sec_frames():
    out = {"routes": [], "frames": {}}
    got = {}
    for tag in [OPINC_TAG] + REV_TAGS:
        rec, body = route(f"sec/frames/{tag}/CY2024", frames(tag, "CY2024"),
                          "every filer's value for this concept in calendar 2024", keep_body=True)
        out["routes"].append(rec)
        if rec.get("status") == 200:
            try:
                p = parse_frame(body)
                got[tag] = p["by_cik"]
                out["frames"][tag + "/CY2024"] = {k: v for k, v in p.items() if k != "by_cik"}
            except Exception as e:               # noqa: BLE001
                out["frames"][tag + "/CY2024"] = {"parse_error": f"{type(e).__name__}: {e}"}
    # PAIRED: another year of the same concept, and the earliest XBRL year, for span
    for period in ("CY2023", "CY2012", "CY2009"):
        rec, body = route(f"sec/frames/{OPINC_TAG}/{period}", frames(OPINC_TAG, period),
                          "paired with CY2024: a different entity count means the period filter bites; "
                          "CY2009 is the first XBRL year", keep_body=True)
        out["routes"].append(rec)
        if rec.get("status") == 200:
            try:
                p = parse_frame(body)
                out["frames"][f"{OPINC_TAG}/{period}"] = {k: v for k, v in p.items() if k != "by_cik"}
            except Exception as e:               # noqa: BLE001
                out["frames"][f"{OPINC_TAG}/{period}"] = {"parse_error": str(e)}

    # the headline, previewed for real: revenue (first tag that has it) / operating income, CY2024
    if OPINC_TAG in got:
        op = got[OPINC_TAG]
        rev = {}
        src = collections.Counter()
        for tag in REV_TAGS:
            for cik, v in got.get(tag, {}).items():
                if cik not in rev and v and v > 0:
                    rev[cik] = v
                    src[tag] += 1
        both = [(rev[c], op[c]) for c in rev if c in op]
        pos = [(r, o) for r, o in both if o > 0]
        margins = sorted(o / r for r, o in pos)
        lev = sorted(r / o for r, o in pos)
        def q(xs, p):
            return xs[int(p * (len(xs) - 1))] if xs else None
        out["preview_CY2024"] = {
            "n_with_revenue": len(rev), "revenue_tag_used": dict(src),
            "n_with_both": len(both), "n_positive_operating_income": len(pos),
            "share_loss_making": round(1 - len(pos) / len(both), 3) if both else None,
            "operating_margin_median": round(q(margins, .5), 4) if margins else None,
            "operating_margin_q25_q75": [round(q(margins, .25), 4), round(q(margins, .75), 4)] if margins else None,
            "price_leverage_median_pct": round(q(lev, .5), 2) if lev else None,
            "price_leverage_q25_q75_pct": [round(q(lev, .25), 2), round(q(lev, .75), 2)] if lev else None,
            "revenue_weighted_margin": round(sum(o for _, o in pos) / sum(r for r, _ in pos), 4) if pos else None,
            "note": ("profit-making filers only; loss-makers have no defined price leverage and "
                     "are reported as a share. Duplicate-CIK handling and fiscal-year alignment "
                     "are the fetch's job, not this preview's."),
        }
    return out


# ------------------------------------------------- 2. SEC bulk data sets
def sec_bulk():
    """The quarterly zips carry sub.txt with the SIC code, which the frames API
    does not. Read the newest Q1 file (10-K season) far enough to know the
    columns, the form mix, and how many 10-Ks carry a SIC."""
    out = {"routes": []}
    rec, body = route("sec/fsds-landing", "https://www.sec.gov/dera/data/financial-statement-data-sets",
                      "landing page; discover the zip links instead of guessing names", keep_body=True)
    out["routes"].append(rec)
    links = []
    if rec.get("status") == 200:
        links = sorted(set(re.findall(r'href="([^"]*financial-statement-data-sets/(\d{4}q[1-4])\.zip)"',
                                      body.decode("utf-8", "replace"))))
    out["zip_links"] = [l[1] for l in links][-12:]
    out["n_zip_links"] = len(links)
    q1 = [l for l in links if l[1].endswith("q1")]
    if not q1:
        # fall back to the documented path pattern for the most recent Q1
        out["fallback"] = "no links discovered; trying the documented path for 2026q1"
        q1 = [("/files/dera/data/financial-statement-data-sets/2026q1.zip", "2026q1")]
    path, label = q1[-1]
    url = path if path.startswith("http") else "https://www.sec.gov" + path
    rec, body = route(f"sec/fsds-{label}", url, "one quarter's bulk zip; sub.txt columns and SIC coverage",
                      keep_body=True, cap=BIG)
    out["routes"].append(rec)
    if rec.get("status") == 200 and body[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(body))
        out["members"] = [{"name": i.filename, "size": i.file_size} for i in z.infolist()]
        if "sub.txt" in z.namelist():
            lines = z.read("sub.txt").decode("utf-8", "replace").splitlines()
            head = lines[0].split("\t")
            ix = {c: i for i, c in enumerate(head)}
            forms = collections.Counter()
            sic_present = 0
            tenk = 0
            for l in lines[1:]:
                f = l.split("\t")
                if len(f) < len(head):
                    continue
                forms[f[ix["form"]]] += 1
                if f[ix["form"]] == "10-K":
                    tenk += 1
                    if f[ix["sic"]].strip():
                        sic_present += 1
            out["sub"] = {"header": head, "rows": len(lines) - 1, "forms": dict(forms.most_common(10)),
                          "n_10k": tenk, "n_10k_with_sic": sic_present, "sample": lines[1][:400]}
        if "num.txt" in z.namelist():
            lines = z.read("num.txt").decode("utf-8", "replace").splitlines()
            head = lines[0].split("\t")
            ix = {c: i for i, c in enumerate(head)}
            tags = collections.Counter()
            for l in lines[1:]:
                f = l.split("\t")
                if len(f) < len(head):
                    continue
                t = f[ix["tag"]]
                if t in REV_TAGS or t == OPINC_TAG:
                    tags[t] += 1
            out["num"] = {"header": head, "rows": len(lines) - 1, "tags_of_interest": dict(tags),
                          "sample": lines[1][:300]}
    return out


# ------------------------------------------------------------ 3. Damodaran
def damodaran():
    out = {"routes": []}
    rec, body = route("damodaran/datacurrent", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html",
                      "the current-data index; discover the margin files by link text", keep_body=True)
    out["routes"].append(rec)
    found = []
    if rec.get("status") == 200:
        html = body.decode("utf-8", "replace")
        for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{0,120})', html):
            href, text = m.group(1), m.group(2)
            if "margin" in href.lower() or "margin" in text.lower():
                found.append({"href": href, "text": text.strip()})
    out["margin_links"] = found[:30]
    # the known US file, and its regional siblings, whatever the index said
    for name in ("margin", "marginEurope", "marginemerg", "marginGlobal", "marginJapan"):
        for ext in ("xls", "xlsx"):
            url = f"https://pages.stern.nyu.edu/~adamodar/pc/datasets/{name}.{ext}"
            rec = route(f"damodaran/{name}.{ext}", url, "does the file exist, and is it BIFF (.xls) or OOXML (.xlsx)")
            if rec.get("status") == 200:
                m = rec.get("magic", "")
                rec["looks_like"] = ("xlsx/zip" if m.startswith("504b") else
                                     "xls/BIFF" if m == "d0cf11e0" else "unknown")
            out["routes"].append(rec)
            if rec.get("status") == 200:
                break
    # the historical margin file, if it exists, would give a 1992-adjacent baseline
    out["routes"].append(route("damodaran/histmargin", "https://pages.stern.nyu.edu/~adamodar/pc/datasets/histmargin.xls",
                               "historical margins by year, if published"))
    return out


def main():
    doc = {"probe": "1% price = 11.1% operating profit (Marn & Rosiello 1992) — data availability",
           "generated_by": "scripts/probe_price_leverage.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "note": ("Discovery only. A 200 is not access: compare paired entity counts, and read "
                    "column names from the heads before writing a parser.")}
    for key, fn in (("sec_frames", sec_frames), ("sec_bulk", sec_bulk), ("damodaran", damodaran)):
        print(f"== {key}", flush=True)
        try:
            doc[key] = fn()
        except Exception as e:                   # noqa: BLE001
            doc[key] = {"fatal": f"{type(e).__name__}: {e}"}
            print(f"  FATAL {e}", flush=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, default=str)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
