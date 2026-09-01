#!/usr/bin/env python3
"""Collect the two series behind Eroom's Law -> data/pharma-eroom.json

Eroom's Law (Scannell et al. 2012) says new drugs approved per billion USD of
R&D halves about every nine years. The paper's window ends around 2010. Since
then approvals have risen sharply while everyone kept citing the decline, so
whether the law still holds is an open question rather than a settled one.

It cannot be retested on the paper's own 1950 baseline: three probe rounds
established that no pharma R&D spending series reaches back that far through
any retrievable route (data/_pharma-probe.json, data/_pharma-spend-probe.json).
The numerator goes back to 1939; the denominator starts in 2005. So the honest
study is the modern window, and the page has to say so.

  numerator    FDA new molecular entities per year, built from the Drugs@FDA
               bulk archive: original applications, approved, submission class
               7 (Type 1 - New Molecular Entity) or 8 (Type 1/4). Validated
               against the FDA's own published novel-approval counts.
  denominator  business R&D in pharmaceuticals. Eurostat BERD, NACE C21.
  deflator     captured alongside, so the ratio can be put in constant prices.

This run also reports the full geo and unit lists rather than assuming them,
and dumps the structure of one NSF table, because a US R&D series would make
the denominator cover both regions that actually do the research.

Stdlib only. Runs in GitHub Actions; this sandbox reaches none of these hosts.
"""
import collections, io, json, os, re, sys, time, urllib.request, zipfile

OUT = "data/pharma-eroom.json"
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions)"}
CAP = 16 * 1024 * 1024
NME_CLASSES = {"7", "8"}
DRUGSFDA = "https://www.fda.gov/media/89850/download"
EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
            "rd_e_berdindr2?format=JSON&lang=EN&nace_r2=C21")
# Money must be deflated before it is correlated with anything. Round 2 read
# this id's title off FRED rather than trusting my label for it: "Gross domestic
# product (implicit price deflator)", annual.
DEFLATOR = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=A191RD3A086NBEA"


def get(url, cap=CAP, timeout=240):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(cap + 1)
    if len(body) > cap:
        raise RuntimeError(f"response exceeded {cap:,}b cap: {url}")
    return body


def nme_by_year():
    """FDA new molecular entities per year, from the primary submission records."""
    z = zipfile.ZipFile(io.BytesIO(get(DRUGSFDA)))
    lines = z.read("Submissions.txt").decode("utf-8", "replace").splitlines()
    ix = {c: i for i, c in enumerate(lines[0].split("\t"))}
    per, dropped = collections.Counter(), 0
    for line in lines[1:]:
        f = line.split("\t")
        if len(f) < len(ix):
            dropped += 1
            continue
        if (f[ix["SubmissionType"]].strip().upper() != "ORIG"
                or f[ix["SubmissionStatus"]].strip().upper() != "AP"
                or f[ix["SubmissionClassCodeID"]].strip() not in NME_CLASSES):
            continue
        y = f[ix["SubmissionStatusDate"]].strip()[:4]
        if y.isdigit():
            per[int(y)] += 1
    return {"by_year": {str(y): per[y] for y in sorted(per)},
            "n": sum(per.values()), "malformed_rows_dropped": dropped,
            "source": DRUGSFDA,
            "definition": ("original applications, status AP, submission class "
                           "7 (Type 1 - New Molecular Entity) or 8 (Type 1/4), "
                           "counted by the year of SubmissionStatusDate")}


def _jsonstat(j):
    """JSON-stat 2.0 -> [(dim tuple, value)]. Eurostat's own layout, read from
    the response rather than assumed: dimension order comes from j['id']."""
    dims = j["id"]
    sizes = j["size"]
    cats = [list(j["dimension"][d]["category"]["index"]) for d in dims]
    labels = {d: j["dimension"][d]["category"].get("label", {}) for d in dims}
    out = []
    for flat, v in j["value"].items():
        i = int(flat)
        key = []
        for axis in range(len(sizes) - 1, -1, -1):
            key.append(cats[axis][i % sizes[axis]])
            i //= sizes[axis]
        out.append((tuple(reversed(key)), v))
    return dims, cats, labels, out


def berd_pharma():
    """Business R&D in pharmaceuticals (NACE C21), every geo and unit offered."""
    j = json.loads(get(EUROSTAT, cap=8 * 1024 * 1024).decode("utf-8", "replace"))
    dims, cats, labels, rows = _jsonstat(j)
    di = {d: k for k, d in enumerate(dims)}
    series = collections.defaultdict(dict)
    for key, v in rows:
        if v is None:
            continue
        series[(key[di["geo"]], key[di["unit"]])][key[di["time"]]] = v
    packed = {f"{g}|{u}": dict(sorted(t.items())) for (g, u), t in series.items()}
    return {"dimensions": dims,
            "geo_available": cats[di["geo"]],
            "unit_available": cats[di["unit"]],
            "unit_labels": labels["unit"],
            "time_available": cats[di["time"]],
            "series": packed, "n_series": len(packed),
            "source": EUROSTAT,
            "definition": ("Eurostat rd_e_berdindr2, business enterprise R&D "
                           "expenditure, NACE C21 manufacture of basic "
                           "pharmaceutical products and preparations")}


def us_deflator():
    """US GDP implicit price deflator, annual, so the ratio can be put in
    constant prices. Deflating pushes the ratio UP in later years, so the
    current-price result is the conservative one — but the rule is deflate
    first, and both versions belong on the page."""
    rows = get(DEFLATOR, cap=1024 * 1024, timeout=90).decode().splitlines()
    out = {}
    for line in rows[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        y, v = parts[0][:4], parts[1].strip()
        try:
            out[y] = float(v)
        except ValueError:
            continue
    return {"by_year": out, "n": len(out), "source": DEFLATOR,
            "series_id": "A191RD3A086NBEA",
            "title": "Gross domestic product (implicit price deflator), annual",
            "base": "index, 2017 = 100 as published by FRED"}


def nsf_table_shape():
    """Is a US pharma R&D series extractable from NSF's tables with stdlib?

    An xlsx is a zip of XML, so this needs no third-party reader. Reports the
    sheet names and the first rows of the first sheet so a parser can be
    written against what is there, not against what the page implies.
    """
    url = ("https://ncses.nsf.gov/pubs/nsf25354/assets/technical-tables/tables/"
           "nsf25354-taba-001.xlsx")
    rec = {"url": url}
    try:
        z = zipfile.ZipFile(io.BytesIO(get(url, cap=8 * 1024 * 1024, timeout=120)))
        rec["members"] = [i.filename for i in z.infolist()][:24]
        wb = z.read("xl/workbook.xml").decode("utf-8", "replace")
        rec["sheets"] = re.findall(r'<sheet name="([^"]+)"', wb)
        shared = []
        if "xl/sharedStrings.xml" in [i.filename for i in z.infolist()]:
            ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
            shared = re.findall(r"<t[^>]*>([^<]*)</t>", ss)
        rec["n_shared_strings"] = len(shared)
        rec["first_strings"] = shared[:40]
        rec["mentions_pharma"] = any("pharmac" in s.lower() for s in shared)
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    return rec


def main():
    doc = {"generated_by": "scripts/fetch_pharma.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "question": ("Eroom's Law says approvals per R&D dollar halve every "
                        "nine years. The paper stops around 2010. Did it "
                        "continue?"),
           "scope_note": ("The paper's 1950 baseline is not retestable: no "
                          "pharma R&D series reaches back that far through any "
                          "retrievable route. Numerator from 1939, denominator "
                          "from 2005.")}

    print("FDA new molecular entities")
    doc["nme"] = nme_by_year()
    print(f"  {doc['nme']['n']:,} approvals, "
          f"{len(doc['nme']['by_year'])} years")

    print("Eurostat BERD, NACE C21")
    doc["berd"] = berd_pharma()
    b = doc["berd"]
    print(f"  {b['n_series']} geo x unit series, time {b['time_available'][0]}"
          f"-{b['time_available'][-1]}")
    print(f"  units: {b['unit_available']}")
    print(f"  geos ({len(b['geo_available'])}): {b['geo_available']}")

    print("US GDP deflator")
    doc["deflator"] = us_deflator()
    dfl = doc["deflator"]["by_year"]
    print(f"  {len(dfl)} years, {min(dfl)}-{max(dfl)}")

    print("NSF table shape")
    doc["nsf_probe"] = nsf_table_shape()
    print(f"  sheets: {doc['nsf_probe'].get('sheets')}  "
          f"pharma mentioned: {doc['nsf_probe'].get('mentions_pharma')}"
          f"{'  ERR ' + doc['nsf_probe']['error'] if doc['nsf_probe'].get('error') else ''}")

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"\nwrote {OUT} ({os.path.getsize(OUT):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
