#!/usr/bin/env python3
"""Can Eroom's Law be retested from primary open data? -> data/_pharma-probe.json

Eroom's Law (Scannell et al. 2012, Nat Rev Drug Discov) says new drugs approved
per billion USD of R&D has halved roughly every nine years since 1950. Retesting
it needs two series and a deflator:

  1. new drug approvals per year   — FDA CDER, novel drugs / new molecular entities
  2. pharma R&D spend per year     — PhRMA, NSF/NCSES, or BEA via FRED
  3. a deflator                    — GDP price index

This establishes only whether those are retrievable and long enough. It parses
nothing into a study and assumes no schema.

It carries two lessons paid for in earlier attempts:

  - A 200 is not access. The OECD endpoint returned 200 and a fixed truncated
    fragment for every query, and ignored the filter entirely; the evidence was
    identical byte counts sitting in the dump, unread. So every route records
    bytes and a content head, and paired routes are compared against each other.
  - Nothing is downloaded blind. A "narrow" OECD request turned out to be the
    whole 55MB database, 198 times over. Every response here is capped and the
    cap is reported, so a silent firehose is visible rather than fatal.

Run in GitHub Actions — this sandbox cannot reach any of these hosts.
"""
import json, os, ssl, sys, time, urllib.error, urllib.request

OUT = "data/_pharma-probe.json"
CAP = 8 * 1024 * 1024          # never pull more than this from one route
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; data availability probe)"}


def hit(name, url, note="", want=None):
    """Fetch one route, capped, and record what actually came back."""
    rec = {"name": name, "url": url, "note": note}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read(CAP + 1)
            rec["status"] = r.status
            rec["content_type"] = r.headers.get("Content-Type", "")
            rec["declared_length"] = r.headers.get("Content-Length")
            rec["capped"] = len(body) > CAP
            body = body[:CAP]
            rec["bytes"] = len(body)
            head = body[:1200].decode("utf-8", "replace")
            rec["head"] = head
            rec["looks_like"] = (
                "json" if head.lstrip()[:1] in "{[" else
                "html" if "<html" in head[:400].lower() else
                "xml" if head.lstrip().startswith("<?xml") else
                "zip" if body[:2] == b"PK" else
                "text/csv?")
            if want:
                rec["contains_expected"] = {w: (w in head) for w in want}
    except urllib.error.HTTPError as ex:
        rec["status"] = ex.code
        rec["error"] = f"HTTP {ex.code} {ex.reason}"
        try:
            rec["head"] = ex.read(600).decode("utf-8", "replace")
        except Exception:
            pass
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    rec["seconds"] = round(time.time() - t0, 1)
    print(f"  {rec.get('status', '---'):>4}  {rec.get('bytes', 0):>9,}b  "
          f"{rec.get('looks_like', ''):<10} {name}")
    return rec


def zip_probe(name, url, note=""):
    """Open the Drugs@FDA archive and report what is actually inside it.

    Eroom's Law counts NEW MOLECULAR ENTITIES, not approvals. openFDA's counts
    are every approval — generics, new formulations, new indications — so the
    whole study turns on whether the NME flag exists somewhere retrievable.
    Drugs@FDA is said to carry a submission classification; this checks.
    """
    import io, zipfile
    rec = {"name": name, "url": url, "note": note}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read(CAP + 1)
        rec["bytes"] = len(body)
        rec["capped"] = len(body) > CAP
        z = zipfile.ZipFile(io.BytesIO(body[:CAP]))
        rec["members"] = [{"name": i.filename, "size": i.file_size}
                          for i in z.infolist()]
        # the lookup table is small; read it whole and show every class
        for i in z.infolist():
            low = i.filename.lower()
            if "submissionclass" in low or "submission_class" in low:
                txt = z.read(i).decode("utf-8", "replace")
                rows = [l.split("\t") for l in txt.splitlines()]
                rec["submission_classes"] = rows[:60]
                rec["nme_rows"] = [r for r in rows
                                   if any("molecular" in c.lower() for c in r)]
            if low.endswith("submissions.txt"):
                txt = z.read(i).decode("utf-8", "replace")
                lines = txt.splitlines()
                rec["submissions_header"] = lines[0].split("\t")
                rec["submissions_rows"] = len(lines) - 1
                rec["submissions_sample"] = [l.split("\t") for l in lines[1:4]]
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    rec["seconds"] = round(time.time() - t0, 1)
    print(f"  zip {name}: {rec.get('bytes', 0):,}b, "
          f"{len(rec.get('members', []))} members"
          f"{'  ERR ' + rec['error'] if rec.get('error') else ''}")
    return rec


def fred_meta(sid):
    """FRED's own title and units for a series id. Never label a series by guess:
    Y694RC1A027NBEA was assumed to be pharma R&D and that assumption is exactly
    what this checks."""
    rec = {"name": f"fred-meta/{sid}", "series_id": sid}
    try:
        req = urllib.request.Request(
            f"https://fred.stlouisfed.org/data/{sid}.txt", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read(200_000).decode("utf-8", "replace")
        head, _, body = txt.partition("DATE")
        rec["metadata"] = [l.strip() for l in head.splitlines() if l.strip()][:12]
        rows = [l.split() for l in body.splitlines() if l and l[0].isdigit()]
        if rows:
            rec["first"], rec["last"] = rows[0], rows[-1]
            rec["n_obs"] = len(rows)
    except Exception as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    t = next((m for m in rec.get("metadata", []) if m.lower().startswith("title")), "?")
    print(f"  {sid}: {t[:70]}")
    print(f"      {rec.get('n_obs', 0)} obs, {rec.get('first', ['?'])[0]} "
          f"-> {rec.get('last', ['?'])[0]}")
    return rec


def main():
    routes = []

    # ---- 1. FDA approvals -------------------------------------------------
    # openFDA can count directly, which would give the approvals series without
    # any parsing at all. The count endpoint is the one that matters.
    routes.append(hit(
        "openfda/drugsfda/one-record",
        "https://api.fda.gov/drug/drugsfda.json?limit=1",
        "does the API answer at all, and what does a record look like",
        want=["application_number", "submissions"]))
    routes.append(hit(
        "openfda/drugsfda/count-by-approval-year",
        "https://api.fda.gov/drug/drugsfda.json"
        "?search=submissions.submission_status:%22AP%22"
        "&count=submissions.submission_status_date",
        "approvals per date — if this works the whole approvals series is one call"))
    routes.append(hit(
        "openfda/drugsfda/count-nda-only",
        "https://api.fda.gov/drug/drugsfda.json"
        "?search=submissions.submission_status:%22AP%22"
        "+AND+openfda.application_number:NDA*"
        "&count=submissions.submission_status_date",
        "PAIRED with the previous route: a different count means the filter bites"))
    routes.append(hit(
        "fda/drugsfda-data-files",
        "https://www.fda.gov/media/89850/download",
        "Drugs@FDA bulk TSVs (zip) — the fallback if openFDA cannot filter to NMEs"))

    # ---- 2. R&D spend -----------------------------------------------------
    # FRED is the one provider already proven from Actions. Several candidate
    # BEA ids; a wrong id fails alone rather than killing the probe.
    for sid, what in (
            ("Y694RC1A027NBEA", "private fixed investment in R&D, pharma and medicine mfg"),
            ("Y006RC1A027NBEA", "private fixed investment in R&D, total"),
            ("A191RD3A086NBEA", "GDP implicit price deflator, annual"),
            ("GDPDEF", "GDP deflator, quarterly"),
            ("PCU325412325412", "PPI pharmaceutical preparation manufacturing")):
        routes.append(hit(
            f"fred/{sid}",
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}",
            what, want=["DATE", sid]))

    # NSF is the authoritative US industry R&D source but has no proven route.
    routes.append(hit(
        "nsf/ncses-landing",
        "https://ncses.nsf.gov/surveys/business-enterprise-research-development",
        "is NCSES reachable at all — a landing page, not data"))

    # ---- 3. the paper's own figures --------------------------------------
    routes.append(hit(
        "nature/scannell-2012",
        "https://www.nature.com/articles/nrd3681",
        "the paper itself — is anything open, or is it all paywalled"))

    # ---- round 2: the two things a 200 does not answer -------------------
    print("\n  what is actually inside the Drugs@FDA archive:")
    routes.append(zip_probe(
        "fda/drugsfda-zip-contents",
        "https://www.fda.gov/media/89850/download",
        "does an NME / new-molecular-entity flag exist anywhere in here"))

    print("\n  what those FRED ids actually are:")
    meta = [fred_meta(s) for s in ("Y694RC1A027NBEA", "Y006RC1A027NBEA",
                                   "A191RD3A086NBEA", "PCU325412325412")]

    os.makedirs("data", exist_ok=True)
    doc = {"probe": "pharma / Eroom's Law data availability",
           "fred_metadata": meta,
           "generated_by": "scripts/probe_pharma.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "cap_bytes": CAP,
           "note": ("Discovery only. A 200 is not access: compare the paired "
                    "openFDA counts, and check bytes before believing a filter "
                    "worked."),
           "routes": routes}

    # the one comparison that decides whether openFDA can do the job
    a = next((r for r in routes if r["name"].endswith("count-by-approval-year")), {})
    b = next((r for r in routes if r["name"].endswith("count-nda-only")), {})
    if a.get("bytes") and b.get("bytes"):
        doc["openfda_filter_verdict"] = (
            "filter ignored — identical response" if a["bytes"] == b["bytes"]
            else f"filter bites: {a['bytes']:,}b unfiltered vs {b['bytes']:,}b filtered")
        print(f"\n  openFDA filter: {doc['openfda_filter_verdict']}")

    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"\nwrote {OUT} ({os.path.getsize(OUT):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
