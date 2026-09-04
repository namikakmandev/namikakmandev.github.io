#!/usr/bin/env python3
"""Availability probe for the second-label study -> data/_repurpose-probe.json

The question: when one molecule carries two FDA labels (Cialis and Adcirca are
the same 20 mg tadalafil tablet), how far apart are the prices, and does the
gap survive generic entry? Three things have to exist before that is a study:

  1. A per-product price series. CMS NADAC (National Average Drug Acquisition
     Cost) is the open candidate: pharmacy acquisition cost per NDC, weekly,
     published on data.medicaid.gov. Never touched from here before.
  2. A way to get from an NDC to the FDA application that approved it. The
     FDA NDC directory carries an APPLICATIONNUMBER column, if memory serves
     — which is exactly the kind of claim this probe exists to check.
  3. The second-label pairs themselves, built from Drugs@FDA rather than
     recalled: molecules with two or more approved original NDAs under
     different trade names, plus the Type 9/10 "new indication as a distinct
     NDA" classes and efficacy-supplement counts for the count study.

Discovery only. Every response is recorded with status, bytes and a capped
head; a 200 is not access, so filtered requests are paired with an unfiltered
one and the byte counts compared. Parsers are written after this runs, against
the column names it dumps, not before.

Run in GitHub Actions — this sandbox reaches none of these hosts.
"""
import collections, io, json, re, sys, time, urllib.error, urllib.parse, urllib.request, zipfile

OUT = "data/_repurpose-probe.json"
CAP = 24 * 1024 * 1024
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; availability probe)"}
HEAD = 1500

NME_CLASSES = {"7", "8"}
EFFICACY_CLASS = "2"
NEW_INDICATION_NDA_CLASSES = {"22", "24", "25"}   # Type 10, Type 9, Type 9-BLA
WATCH = ["TADALAFIL", "SILDENAFIL", "FINASTERIDE", "SEMAGLUTIDE", "LIRAGLUTIDE",
         "TIRZEPATIDE", "BUPROPION", "MINOXIDIL", "NALTREXONE", "DULOXETINE"]


def fetch(url, cap=CAP, timeout=240):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(cap + 1)
        ctype = r.headers.get("Content-Type", "")
        clen = r.headers.get("Content-Length")
    return body[:cap], len(body) > cap, ctype, clen


def route(name, url, note, keep_body=False):
    """One request, recorded whatever happens."""
    rec = {"name": name, "url": url, "note": note}
    t0 = time.time()
    body = b""
    try:
        body, capped, ctype, clen = fetch(url)
        rec.update(status=200, content_type=ctype, declared_length=clen,
                   capped=capped, bytes=len(body),
                   head=body[:HEAD].decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error=str(e),
                   head=(e.read(HEAD) or b"").decode("utf-8", "replace"))
    except Exception as e:                       # noqa: BLE001 — record, don't die
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    rec["seconds"] = round(time.time() - t0, 1)
    print(f"  {name}: {rec.get('status')} {rec.get('bytes', 0):,}b "
          f"{rec['seconds']}s", flush=True)
    return (rec, body) if keep_body else rec


# ---------------------------------------------------------------- 1. NADAC
def nadac():
    """data.medicaid.gov is a DKAN site. Its metastore lists every dataset with
    its distributions; search by title for NADAC, then pull the head of one
    CSV and try the datastore query API with and without a filter."""
    out = {"routes": []}
    rec, body = route("medicaid/metastore-datasets",
                      "https://data.medicaid.gov/api/1/metastore/schemas/dataset/items?show-reference-ids",
                      "every dataset on the site; look for NADAC by title", keep_body=True)
    out["routes"].append(rec)
    found = []
    if rec.get("status") == 200:
        try:
            items = json.loads(body.decode("utf-8", "replace"))
            out["n_datasets"] = len(items)
            for it in items:
                title = it.get("title", "")
                if "NADAC" not in title.upper():
                    continue
                dists = []
                for d in it.get("distribution", []) or []:
                    dd = d.get("data", d) if isinstance(d, dict) else {}
                    dists.append({"identifier": d.get("identifier") if isinstance(d, dict) else None,
                                  "downloadURL": dd.get("downloadURL"),
                                  "format": dd.get("format") or dd.get("mediaType")})
                found.append({"identifier": it.get("identifier"), "title": title,
                              "modified": it.get("modified"), "distributions": dists})
        except Exception as e:                   # noqa: BLE001
            out["parse_error"] = f"{type(e).__name__}: {e}"
    found.sort(key=lambda x: x["title"])
    out["nadac_datasets"] = found
    out["n_nadac_datasets"] = len(found)

    # the site's own search endpoint, as a second opinion on the list above
    out["routes"].append(route("medicaid/search-nadac",
                               "https://data.medicaid.gov/api/1/search?fulltext=NADAC&page-size=50",
                               "search API; should agree with the metastore listing"))

    # head of one CSV: the newest 'NADAC (National Average Drug Acquisition Cost)'
    # dataset with a downloadURL. Capped hard — these files are big.
    target = None
    for it in found:
        for d in it["distributions"]:
            if d.get("downloadURL"):
                if target is None or (it.get("modified") or "") > (target[0].get("modified") or ""):
                    target = (it, d)
    if target:
        it, d = target
        out["csv_target"] = {"title": it["title"], "identifier": it["identifier"],
                             "distribution": d["identifier"], "url": d["downloadURL"]}
        rec, body = route("medicaid/nadac-csv-head", d["downloadURL"],
                          "columns and a few rows of the newest NADAC file", keep_body=True)
        out["routes"].append(rec)
        if rec.get("status") == 200 and body:
            lines = body.decode("utf-8", "replace").splitlines()
            out["csv_header"] = lines[0].split(",") if lines else None
            out["csv_rows_in_cap"] = len(lines) - 1
            out["csv_sample"] = lines[1:4]
            hits = [l for l in lines[1:] if any(w in l.upper() for w in ("TADALAFIL", "SILDENAFIL", "ADCIRCA", "CIALIS", "REVATIO", "VIAGRA"))]
            out["csv_watch_hits"] = hits[:25]
            out["csv_watch_hit_count"] = len(hits)
            dates = collections.Counter()
            for l in lines[1:]:
                m = re.search(r"(\d{2}/\d{2}/\d{4})", l)
                if m:
                    dates[m.group(1)] += 1
            out["csv_dates_seen"] = dict(dates.most_common(8))

        # datastore query API, PAIRED: unfiltered count vs filtered by description
        dist = d["identifier"]
        if dist:
            base = f"https://data.medicaid.gov/api/1/datastore/query/{dist}"
            out["routes"].append(route("medicaid/datastore-unfiltered", base + "?limit=5&results=true&count=true",
                                       "does the datastore answer, and how many rows does it hold"))
            q = urllib.parse.urlencode({
                "limit": 50, "results": "true", "count": "true",
                "conditions[0][property]": "ndc_description",
                "conditions[0][value]": "TADALAFIL%",
                "conditions[0][operator]": "LIKE"})
            out["routes"].append(route("medicaid/datastore-filtered", base + "?" + q,
                                       "PAIRED with the previous route: a different count means the filter bites"))
            sql = f'[SELECT * FROM {dist}][WHERE ndc_description LIKE "TADALAFIL%"][LIMIT 20]'
            out["routes"].append(route("medicaid/datastore-sql",
                                       "https://data.medicaid.gov/api/1/datastore/sql?query=" + urllib.parse.quote(sql),
                                       "the SQL flavour of the same query"))
    else:
        out["csv_target"] = None
    return out


# ---------------------------------------------------------- 2. NDC directory
def ndc_directory():
    """FDA NDC directory zip: product.txt should carry APPLICATIONNUMBER, which
    is the join from a priced NDC to the NDA that approved it."""
    out = {"routes": []}
    rec, body = route("fda/ndc-directory-zip", "https://www.accessdata.fda.gov/cder/ndctext.zip",
                      "the whole directory; product.txt + package.txt", keep_body=True)
    out["routes"].append(rec)
    if rec.get("status") == 200 and body[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(body))
        out["members"] = [{"name": i.filename, "size": i.file_size} for i in z.infolist()]
        for member in ("product.txt", "package.txt"):
            if member not in z.namelist():
                out[member] = "MISSING"
                continue
            txt = z.read(member).decode("utf-8", "replace")
            lines = txt.splitlines()
            head = lines[0].split("\t")
            out[member] = {"header": head, "rows": len(lines) - 1, "sample": lines[1:3]}
            if member == "product.txt":
                ix = {c.strip().upper(): i for i, c in enumerate(head)}
                col_sub = ix.get("SUBSTANCENAME")
                col_app = ix.get("APPLICATIONNUMBER")
                col_cat = ix.get("MARKETINGCATEGORYNAME")
                watch = collections.defaultdict(list)
                cats = collections.Counter()
                for l in lines[1:]:
                    f = l.split("\t")
                    if len(f) < len(head):
                        continue
                    if col_cat is not None:
                        cats[f[col_cat].strip()] += 1
                    sub = f[col_sub].strip().upper() if col_sub is not None else ""
                    for w in WATCH:
                        if sub == w or sub.startswith(w + " "):
                            watch[w].append({
                                "proprietary": f[ix["PROPRIETARYNAME"]].strip() if "PROPRIETARYNAME" in ix else None,
                                "ndc": f[ix["PRODUCTNDC"]].strip() if "PRODUCTNDC" in ix else None,
                                "application": f[col_app].strip() if col_app is not None else None,
                                "category": f[col_cat].strip() if col_cat is not None else None,
                                "strength": (f[ix["ACTIVE_NUMERATOR_STRENGTH"]].strip() + " " + f[ix["ACTIVE_INGRED_UNIT"]].strip()) if "ACTIVE_NUMERATOR_STRENGTH" in ix else None,
                                "form": f[ix["DOSAGEFORMNAME"]].strip() if "DOSAGEFORMNAME" in ix else None,
                                "labeler": f[ix["LABELERNAME"]].strip() if "LABELERNAME" in ix else None,
                            })
                out["has_application_column"] = col_app is not None
                out["marketing_categories"] = dict(cats.most_common(12))
                out["watch"] = {w: {"n": len(v), "brands": sorted({r["proprietary"] for r in v if r["proprietary"]})[:20],
                                    "applications": sorted({r["application"] for r in v if r["application"]})[:30],
                                    "sample": v[:6]}
                                for w, v in watch.items()}
    # openFDA's NDC endpoint as a second route, paired
    out["routes"].append(route("openfda/ndc-tadalafil",
                               "https://api.fda.gov/drug/ndc.json?search=generic_name:tadalafil&limit=100",
                               "does openFDA carry application_number on NDC records"))
    out["routes"].append(route("openfda/ndc-sildenafil",
                               "https://api.fda.gov/drug/ndc.json?search=generic_name:sildenafil&limit=100",
                               "PAIRED: different molecule, different byte count expected"))
    return out


# ------------------------------------------------------ 3. Medicare Part D
def part_d():
    """data.cms.gov publishes a DCAT catalogue at /data.json; find the Part D
    spending-by-drug dataset and its API URL from the catalogue, not memory."""
    out = {"routes": []}
    rec, body = route("cms/data.json", "https://data.cms.gov/data.json",
                      "DCAT catalogue; find 'Part D Spending by Drug' by title", keep_body=True)
    out["routes"].append(rec)
    hits = []
    if rec.get("status") == 200:
        try:
            cat = json.loads(body.decode("utf-8", "replace"))
            ds = cat.get("dataset", [])
            out["n_datasets"] = len(ds)
            for d in ds:
                t = d.get("title", "")
                if "PART D" in t.upper() and "SPENDING" in t.upper():
                    hits.append({"title": t, "modified": d.get("modified"),
                                 "identifier": d.get("identifier"),
                                 "distributions": [{"format": x.get("format"), "mediaType": x.get("mediaType"),
                                                    "accessURL": x.get("accessURL"), "downloadURL": x.get("downloadURL")}
                                                   for x in d.get("distribution", [])][:6]})
        except Exception as e:                   # noqa: BLE001
            out["parse_error"] = f"{type(e).__name__}: {e}"
    out["part_d_datasets"] = hits[:10]
    # try the first API-looking URL, filtered to one brand
    for h in hits:
        for x in h["distributions"]:
            u = x.get("accessURL") or x.get("downloadURL") or ""
            if "data-api" in u:
                sep = "&" if "?" in u else "?"
                out["routes"].append(route("cms/part-d-api-adcirca",
                                           u + sep + "filter[Brnd_Name]=Adcirca&size=10",
                                           "does the API filter by brand; column name is a guess to be corrected from the head"))
                out["routes"].append(route("cms/part-d-api-unfiltered", u + sep + "size=3",
                                           "PAIRED: what the columns are really called"))
                return out
    return out


# ------------------------------------------- 4. second labels from Drugs@FDA
def second_labels():
    """Build the candidate pairs for real: molecules with >=2 approved original
    NDAs under different trade names, from Products.txt + Submissions.txt.
    Also the counts the count-study needs: efficacy supplements per NME, and
    the Type 9/10 new-indication NDAs."""
    out = {}
    rec, body = route("fda/drugsfda-zip", "https://www.fda.gov/media/89850/download",
                      "the archive the Eroom study already uses", keep_body=True)
    out["route"] = rec
    if rec.get("status") != 200 or body[:2] != b"PK":
        return out
    z = zipfile.ZipFile(io.BytesIO(body))

    def table(name):
        lines = z.read(name).decode("utf-8", "replace").splitlines()
        head = [c.strip() for c in lines[0].split("\t")]
        rows = []
        for l in lines[1:]:
            f = l.split("\t")
            if len(f) >= len(head):
                rows.append(dict(zip(head, [x.strip() for x in f])))
        return head, rows

    _, subs = table("Submissions.txt")
    _, prods = table("Products.txt")
    apps_head, apps = table("Applications.txt")
    out["applications_header"] = apps_head
    appl_type = {a["ApplNo"]: a.get("ApplType", "") for a in apps}

    # first approval date + class of each application's ORIG submission
    orig = {}
    eff = collections.Counter()
    for s in subs:
        if s["SubmissionStatus"].upper() != "AP":
            continue
        if s["SubmissionType"].upper() == "ORIG":
            d = s["SubmissionStatusDate"][:10]
            if s["ApplNo"] not in orig or d < orig[s["ApplNo"]]["date"]:
                orig[s["ApplNo"]] = {"date": d, "class": s["SubmissionClassCodeID"]}
        elif s["SubmissionType"].upper() == "SUPPL" and s["SubmissionClassCodeID"] == EFFICACY_CLASS:
            eff[s["ApplNo"]] += 1

    # molecule -> approved NDAs with trade names
    by_mol = collections.defaultdict(dict)
    for p in prods:
        a = p["ApplNo"]
        if a not in orig or appl_type.get(a, "") not in ("NDA", "BLA"):
            continue
        mol = p["ActiveIngredient"].upper()
        by_mol[mol].setdefault(a, {"name": p["DrugName"], "date": orig[a]["date"],
                                   "class": orig[a]["class"], "forms": set(), "strengths": set(),
                                   "efficacy_supplements": eff[a]})
        by_mol[mol][a]["forms"].add(p["Form"])
        by_mol[mol][a]["strengths"].add(p["Strength"])

    pairs = []
    for mol, apps_ in by_mol.items():
        names = {v["name"] for v in apps_.values()}
        if len(names) < 2:
            continue
        rows = sorted(apps_.items(), key=lambda kv: kv[1]["date"])
        pairs.append({"molecule": mol, "n_applications": len(rows), "n_names": len(names),
                      "first": rows[0][1]["date"],
                      "applications": [{"appl": a, "name": v["name"], "approved": v["date"],
                                        "class": v["class"], "forms": sorted(v["forms"])[:4],
                                        "strengths": sorted(v["strengths"])[:6],
                                        "efficacy_supplements": v["efficacy_supplements"]}
                                       for a, v in rows][:8]})
    pairs.sort(key=lambda x: (-x["n_names"], x["molecule"]))
    out["n_molecules_with_two_names"] = len(pairs)
    out["n_molecules_total"] = len(by_mol)
    out["watch"] = [p for p in pairs if any(p["molecule"].startswith(w) for w in WATCH)]
    out["top_by_names"] = [{"molecule": p["molecule"], "n_names": p["n_names"],
                            "names": sorted({a["name"] for a in p["applications"]})[:6]} for p in pairs[:25]]

    # count-study inputs: per NME, efficacy supplements and years to first one
    nme = [a for a, o in orig.items() if o["class"] in NME_CLASSES]
    n_eff = sum(1 for a in nme if eff[a] > 0)
    out["count_study"] = {
        "n_nme_applications": len(nme),
        "n_nme_with_efficacy_supplement": n_eff,
        "share": round(n_eff / len(nme), 3) if nme else None,
        "efficacy_supplements_distribution": dict(collections.Counter(min(eff[a], 10) for a in nme)),
        "n_new_indication_distinct_nda": sum(1 for o in orig.values() if o["class"] in NEW_INDICATION_NDA_CLASSES),
        "new_indication_nda_by_year": dict(collections.Counter(
            o["date"][:4] for o in orig.values() if o["class"] in NEW_INDICATION_NDA_CLASSES)),
        "note": ("efficacy supplements are counted from Submissions.txt class 2 SUPPL AP; the "
                 "year of the FIRST efficacy supplement per NME is the next thing to compute"),
    }
    return out


def main():
    doc = {"probe": "second-label / repurposing data availability",
           "generated_by": "scripts/probe_repurpose.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "cap_bytes": CAP,
           "note": ("Discovery only. A 200 is not access: compare paired byte counts, "
                    "and read column names from the heads before writing a parser.")}
    for key, fn in (("nadac", nadac), ("ndc_directory", ndc_directory),
                    ("part_d", part_d), ("second_labels", second_labels)):
        print(f"== {key}", flush=True)
        try:
            doc[key] = fn()
        except Exception as e:                   # noqa: BLE001
            doc[key] = {"fatal": f"{type(e).__name__}: {e}"}
            print(f"  FATAL {e}", flush=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
