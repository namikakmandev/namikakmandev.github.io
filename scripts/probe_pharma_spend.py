#!/usr/bin/env python3
"""Round 3: can the DENOMINATOR be found? -> data/_pharma-spend-probe.json

Rounds 1 and 2 settled the numerator. The NME flag exists in Drugs@FDA
(SubmissionClassCodeID 7 and 8) and the archive downloads clean. What is still
missing is pharma R&D spending per year, without which Eroom's Law cannot be
retested as stated — the denominator is the whole claim.

Round 2 also showed why nothing here is taken on trust: FRED's Y694RC1A027NBEA,
which I had labelled pharma R&D from memory, is economy-wide "Gross Domestic
Product: Research and Development". Every series below is therefore reported
with the source's own title, never mine.

Three things this does:

  1. Actually builds the NME series from the archive, rather than assuming the
     join works. If the numerator cannot be computed there is no study and the
     denominator does not matter.
  2. Discovers NSF/NCSES download links instead of guessing URLs — the OECD
     attempt died on invented endpoints.
  3. Checks Eurostat BERD by industry, where NACE C21 is pharmaceuticals.
     Eurostat is already a proven provider here, but it is EU-only and starts
     far too late for a 1950 baseline; the point is to know that for certain.

Run in GitHub Actions — this sandbox reaches none of these hosts.
"""
import collections, io, json, os, re, sys, time, urllib.error, urllib.request, zipfile

OUT = "data/_pharma-spend-probe.json"
CAP = 12 * 1024 * 1024
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; availability probe)"}
NME_CLASSES = {"7", "8"}          # Type 1 NME, and Type 1/4 NME + new combination


def fetch(url, cap=CAP, timeout=180):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(cap + 1)
    return body[:cap], len(body) > cap


def build_nme_series():
    """The numerator, computed for real. Original applications, approved, class
    7 or 8, counted by the year of the approval date."""
    rec = {"what": "FDA new molecular entity approvals per year",
           "source": "Drugs@FDA bulk archive, Submissions.txt"}
    try:
        body, capped = fetch("https://www.fda.gov/media/89850/download")
        rec["capped"] = capped
        z = zipfile.ZipFile(io.BytesIO(body))
        txt = z.read("Submissions.txt").decode("utf-8", "replace")
        lines = txt.splitlines()
        head = lines[0].split("\t")
        ix = {c: i for i, c in enumerate(head)}
        per = collections.Counter()
        kept = skipped_nodate = 0
        for line in lines[1:]:
            f = line.split("\t")
            if len(f) < len(head):
                continue
            if f[ix["SubmissionType"]].strip().upper() != "ORIG":
                continue
            if f[ix["SubmissionStatus"]].strip().upper() != "AP":
                continue
            if f[ix["SubmissionClassCodeID"]].strip() not in NME_CLASSES:
                continue
            d = f[ix["SubmissionStatusDate"]].strip()[:4]
            if not d.isdigit():
                skipped_nodate += 1
                continue
            per[int(d)] += 1
            kept += 1
        rec["n_nme_approvals"] = kept
        rec["skipped_missing_date"] = skipped_nodate
        rec["by_year"] = {str(y): per[y] for y in sorted(per)}
        yrs = sorted(per)
        rec["span"] = [yrs[0], yrs[-1]] if yrs else None
        # the sanity check that matters: does the recent decade look like the
        # 40-60 novel approvals a year the FDA itself reports?
        rec["recent"] = {str(y): per[y] for y in range(2015, 2025) if y in per}
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    print(f"  NME series: {rec.get('n_nme_approvals', 0):,} approvals, "
          f"span {rec.get('span')}{'  ERR ' + rec['error'] if rec.get('error') else ''}")
    return rec


def discover_links(name, url, pattern=r'href="([^"]+\.(?:xlsx|xls|csv|zip))"'):
    """Report what a landing page actually offers. The OECD attempt invented
    endpoints; this reads them off the page instead."""
    rec = {"name": name, "url": url}
    try:
        body, _ = fetch(url, cap=4 * 1024 * 1024, timeout=90)
        html = body.decode("utf-8", "replace")
        links = re.findall(pattern, html, re.I)
        seen, out = set(), []
        for h in links:
            if h not in seen:
                seen.add(h)
                out.append(h)
        rec["n_links"] = len(out)
        rec["links"] = out[:40]
        rec["mentions_pharma"] = bool(re.search(r"pharmac", html, re.I))
        rec["mentions_naics_3254"] = "3254" in html
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    print(f"  {name}: {rec.get('n_links', 0)} data links, "
          f"pharma mentioned={rec.get('mentions_pharma')}"
          f"{'  ERR ' + rec['error'] if rec.get('error') else ''}")
    return rec


def eurostat_berd():
    """BERD by industry. NACE C21 is pharmaceuticals. Proven provider, but the
    span is the question: a 1950 baseline is not on offer here."""
    rec = {"name": "eurostat/rd_e_berdindr2", "what": "BERD by NACE industry"}
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
           "rd_e_berdindr2?format=JSON&lang=EN")
    rec["url"] = url
    try:
        body, capped = fetch(url, cap=6 * 1024 * 1024, timeout=120)
        rec["bytes"] = len(body)
        rec["capped"] = capped
        j = json.loads(body.decode("utf-8", "replace"))
        dims = j.get("dimension", {})
        rec["dimensions"] = list(dims)
        for d in dims:
            cat = dims[d].get("category", {}).get("index", {})
            keys = list(cat) if isinstance(cat, dict) else cat
            rec[f"dim_{d}"] = keys[:24] if keys else None
        t = rec.get("dim_time") or []
        rec["time_span"] = [t[0], t[-1]] if t else None
        rec["has_C21"] = any("C21" == k for k in (rec.get("dim_nace_r2") or []))
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    print(f"  eurostat BERD: dims={rec.get('dimensions')}, "
          f"time={rec.get('time_span')}, C21={rec.get('has_C21')}"
          f"{'  ERR ' + rec['error'] if rec.get('error') else ''}")
    return rec


def main():
    print("1. the numerator, computed rather than assumed")
    nme = build_nme_series()

    print("\n2. NSF/NCSES — what does the page actually offer")
    nsf = [discover_links(
        "ncses/berd-survey",
        "https://ncses.nsf.gov/surveys/business-enterprise-research-development"),
        discover_links(
        "ncses/data-tables",
        "https://ncses.nsf.gov/data-collections/business-enterprise-research-development")]

    print("\n3. Eurostat BERD by industry")
    euro = eurostat_berd()

    os.makedirs("data", exist_ok=True)
    doc = {"probe": "pharma R&D spend — the Eroom denominator",
           "generated_by": "scripts/probe_pharma_spend.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "note": ("Round 2 showed a FRED id labelled from memory was the wrong "
                    "series entirely, so nothing here is named by me: every "
                    "source reports its own titles, dimensions and spans."),
           "nme_series": nme, "nsf": nsf, "eurostat": euro}
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"\nwrote {OUT} ({os.path.getsize(OUT):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
