#!/usr/bin/env python3
"""Livestock insurance study — data acquisition. Runs in GitHub Actions only
(the dev sandbox cannot reach these hosts).

MODE=discover  probe the three sources and dump their real structure:
               - TARSİM: which annual-report PDF URLs exist, and the text of
                 pages mentioning livestock/claims keywords
               - USDA RMA: links found on the livestock participation pages
               - Agroseguro: links found on the annual-report page
MODE=(empty)   extraction pass — only written AFTER discover output is known.

Output: data/livestock-ins-report.json (+ extracted series files later).
"""
import io
import json
import os
import re
import urllib.request

MODE = os.environ.get("MODE", "").strip()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (data pipeline; namikakmandev.github.io)"}

report = {}


def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def head_ok(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200, int(r.headers.get("Content-Length") or 0)
    except Exception as ex:
        return False, f"{type(ex).__name__}: {ex}"


KEYWORDS = ["cattle", "büyükbaş", "buyukbas", "livestock", "hayvan hayat",
            "claims paid", "hasar", "premium", "prim", "insured", "sigortalı",
            "poliçe", "policy", "loss ratio"]


def tarsim_discover():
    """Probe report URLs for both naming patterns, then dump keyword pages."""
    base = "https://www.tarsim.gov.tr/staticweb/krm-web/dergi/faaliyet-raporlari/"
    found = {}
    for year in range(2014, 2026):
        for pat in (f"ar-{year}.pdf", f"en-{year}.pdf", f"fr-{year}.pdf"):
            ok, size = head_ok(base + pat)
            if ok is True:
                found[f"{year}:{pat}"] = size
    out = {"urls_found": found}
    # read ONE recent report to learn the layout (discover only)
    recent = None
    for key in sorted(found, reverse=True):
        if key.startswith(("2024", "2023")):
            recent = base + key.split(":", 1)[1]
            break
    if recent:
        import pdfplumber
        raw = get(recent)
        pages = {}
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            out["n_pages"] = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "")
                low = text.lower()
                if any(k in low for k in KEYWORDS):
                    pages[i + 1] = text[:1200]
        # keep the 14 most keyword-dense pages to stay readable
        dense = sorted(pages.items(),
                       key=lambda kv: -sum(kv[1].lower().count(k) for k in KEYWORDS))
        out["report_read"] = recent
        out["keyword_pages"] = dict(dense[:14])
    return out


def links_on(url, exts=(".pdf", ".csv", ".xlsx", ".zip", ".xls")):
    html = get(url).decode("utf-8", "replace")
    links = re.findall(r'href="([^"]+)"', html)
    keep = [l for l in links if any(e in l.lower() for e in exts)
            or "participation" in l.lower() or "summary" in l.lower()
            or "informe" in l.lower() or "statistic" in l.lower()]
    return {"url": url, "n_links": len(links), "candidate_links": keep[:60]}


def rma_discover():
    out = {}
    for u in ("https://www.rma.usda.gov/tools-reports/summary-business/livestock-dairy-participation",
              "https://www.rma.usda.gov/tools-reports/summary-of-business",
              "https://pubfs-rma.fpac.usda.gov/pub/References/livestock_and_dairy_participation/"):
        try:
            out[u] = links_on(u)
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    return out


def agroseguro_discover():
    out = {}
    for u in ("https://agroseguro.es/conocenos/informe-anual/",
              "https://agroseguro.es/",
              "https://agroseguro.es/el-seguro-agrario/datos-relevantes/"):
        try:
            out[u] = links_on(u)
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    return out


# ------------------------------------------------------------- extraction
# Written against the discover dump of ar-2024.pdf: every report carries a
# "Key Figures" table (label + 4 year-columns) and per-line tables whose data
# rows read "YYYY n,nnn n,nnn n,nnn n,nnn n,nnn" (policies, sum insured,
# premium, subsidy, paid loss) under an ALL-CAPS "<LINE> INSURANCE" section.
TARSIM_BASE = "https://www.tarsim.gov.tr/staticweb/krm-web/dergi/faaliyet-raporlari/"
TARSIM_REPORTS = ["ar-2016.pdf", "ar-2020.pdf", "ar-2024.pdf", "ar-2025.pdf"]

KEY_LABELS = ["Sum Insured", "Total Premium", "Total Government Premium Subsidy",
              "Total Paid Loss", "Total Loss Occurred", "Number of Policies",
              "Number of Insured Cattle (Head)",
              "Number of Insured Sheep and Goats (Head)"]

NUM = r"([\d.,]{4,})"


def _n(tok):
    return int(tok.replace(",", "").replace(".", ""))


def tarsim_extract():
    import pdfplumber
    out = {"key_figures": {}, "lines": {}, "provenance": {}}
    for fname in TARSIM_REPORTS:
        url = TARSIM_BASE + fname
        try:
            raw = get(url)
        except Exception as ex:
            out["provenance"][fname] = f"FETCH FAIL {type(ex).__name__}: {ex}"
            continue
        rep_year = int(re.search(r"(\d{4})", fname).group(1))
        years = [rep_year - 3, rep_year - 2, rep_year - 1, rep_year]
        found_labels = {}
        section = None
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for pageno, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                # key-figures rows: label then 4 big numbers on one line
                if "Key Figures" in text or "Number of Insured Cattle" in text:
                    for lab in KEY_LABELS:
                        m = re.search(re.escape(lab) +
                                      r"\s+" + NUM + r"\s+" + NUM +
                                      r"\s+" + NUM + r"\s+" + NUM, text)
                        if m:
                            found_labels[lab] = (pageno,
                                                 [_n(m.group(i)) for i in range(1, 5)])
                # per-line tables: track the current section header
                for line in text.splitlines():
                    ls = line.strip()
                    m = re.match(r"^([A-Z][A-Z &]{2,40}) INSURANCE$", ls)
                    if m:
                        section = m.group(1).title()
                    m = re.match(r"^(20\d\d)\s+" + NUM + r"\s+" + NUM +
                                 r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM, ls)
                    if m and section:
                        yr = int(m.group(1))
                        row = {"policies": _n(m.group(2)),
                               "sum_insured": _n(m.group(3)),
                               "premium": _n(m.group(4)),
                               "subsidy": _n(m.group(5)),
                               "paid_loss": _n(m.group(6)),
                               "src": f"{fname} p.{pageno}"}
                        out["lines"].setdefault(section, {})[str(yr)] = row
        for lab, (pageno, vals) in found_labels.items():
            for yr, v in zip(years, vals):
                prev = out["key_figures"].setdefault(lab, {}).get(str(yr))
                if prev and prev["value"] != v:
                    out.setdefault("overlap_conflicts", []).append(
                        {"label": lab, "year": yr, "a": prev, "b": {"value": v, "src": fname}})
                out["key_figures"][lab][str(yr)] = {"value": v,
                                                    "src": f"{fname} p.{pageno}"}
        out["provenance"][fname] = {"years": years,
                                    "labels_found": sorted(found_labels)}
    return out


def rma_discover2():
    """Dump EVERY href on the participation page — the filtered pass missed
    the data files."""
    out = {}
    for u in ("https://www.rma.usda.gov/tools-reports/summary-business/livestock-dairy-participation",):
        try:
            html = get(u).decode("utf-8", "replace")
            out[u] = re.findall(r'href="([^"]+)"', html)
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    return out


def rma_discover3():
    """Round 3: the state/county page should carry the real ZIP links, and
    pubfs paths may allow direct HEAD probes."""
    out = {}
    for u in ("https://www.rma.usda.gov/tools-reports/summary-of-business/state-county-crop-summary-business",
              "https://www.rma.usda.gov/tools-reports/summary-of-business/national-summary-of-business-reports"):
        try:
            html = get(u).decode("utf-8", "replace")
            out[u] = [l for l in re.findall(r'href="([^"]+)"', html)
                      if any(e in l.lower() for e in (".zip", ".xls", ".csv", "pubfs", "sob"))][:40]
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    probes = {}
    for y in (2015, 2020, 2024, 2025):
        for pat in (f"https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/state_county_crop/sobcov_{y}.zip",
                    f"https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/national_summary_of_business/sobscc_{y}.zip"):
            ok, size = head_ok(pat)
            if ok is True:
                probes[pat] = size
    out["pubfs_probes"] = probes
    return out


def spain_discover2():
    """Round 3: the ENESA contracting-reports index found in round 2."""
    out = {}
    for u in ("https://www.mapa.gob.es/es/enesa/datos_sobre_el_seguro/informes_de_contratacion_del_seguro_agrario",
              "https://www.mapa.gob.es/es/enesa/datos_sobre_el_seguro/informes_de_contratacion_del_seguro_agrario/",
              "https://www.mapa.gob.es/es/enesa/becas_informes_contratacion"):
        try:
            html = get(u).decode("utf-8", "replace")
            out[u] = [l for l in re.findall(r'href="([^"]+)"', html)
                      if any(e in l.lower() for e in (".pdf", ".xls", ".csv", "informe", "contratacion"))][:40]
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    return out


def rma_sob_probe():
    """Inspect one sobcov ZIP: member names, delimiter, first rows, and the
    distinct plan/commodity pairs that look like livestock programs — so the
    final aggregation is written against the real layout."""
    import zipfile
    url = ("https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/"
           "Summary_of_Business/state_county_crop/sobcov_2024.zip")
    raw = get(url)
    zf = zipfile.ZipFile(io.BytesIO(raw))
    out = {"members": zf.namelist()}
    name = zf.namelist()[0]
    text = zf.read(name).decode("utf-8", "replace")
    lines = text.splitlines()
    out["n_rows"] = len(lines)
    out["first_rows"] = lines[:4]
    plans = {}
    for ln in lines:
        parts = [p.strip().strip('"') for p in ln.split("|")]
        joined = ln.upper()
        if any(k in joined for k in ("LRP", "DRP", "LGM", "CATTLE", "SWINE",
                                     "MILK", "DAIRY", "LAMB", "LIVESTOCK")):
            # keep a compact signature: up to first 12 fields
            plans.setdefault("|".join(parts[3:9]), 0)
            plans["|".join(parts[3:9])] += 1
    out["livestock_signatures"] = dict(sorted(plans.items(),
                                              key=lambda kv: -kv[1])[:25])
    return out


def spain_dump_all():
    """Unfiltered href dump — the filtered passes saw only language links."""
    u = ("https://www.mapa.gob.es/es/enesa/datos_sobre_el_seguro/"
         "informes_de_contratacion_del_seguro_agrario")
    html = get(u).decode("utf-8", "replace")
    links = re.findall(r'href="([^"]+)"', html)
    uniq = []
    for l in links:
        if l not in uniq:
            uniq.append(l)
    return {"n": len(links), "hrefs": uniq[:80],
            "tcm_assets": [l for l in uniq if "tcm" in l.lower()][:30]}


def rma_dir_listing():
    """pubfs answers direct probes — dump its directory listings to find the
    livestock data files (sobcov contains no livestock plans; the 'Lamb'
    matches were a Texas county)."""
    out = {}
    for u in ("https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/",
              "https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/",
              "https://pubfs-rma.fpac.usda.gov/pub/"):
        try:
            html = get(u).decode("utf-8", "replace")
            out[u] = re.findall(r'href="([^"]+)"', html)[:60]
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    # follow anything that smells of livestock
    base = "https://pubfs-rma.fpac.usda.gov"
    for u, links in list(out.items()):
        if isinstance(links, list):
            for l in links:
                if "livestock" in l.lower() or "lgm" in l.lower() or "lrp" in l.lower():
                    full = l if l.startswith("http") else base + l
                    try:
                        html = get(full).decode("utf-8", "replace")
                        out[full] = re.findall(r'href="([^"]+)"', html)[:80]
                    except Exception as ex:
                        out[full] = f"{type(ex).__name__}: {ex}"
    return out


LDP_DIR = ("https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/"
           "Summary_of_Business/livestock_and_dairy_participation/")


def _hdr_find(header, *cands):
    """Return index of the first header column whose name contains all words
    of one candidate (case-insensitive), else None."""
    low = [h.lower() for h in header]
    for cand in cands:
        words = cand.lower().split()
        for i, h in enumerate(low):
            if all(w in h for w in words):
                return i
    return None


def rma_livestock_extract():
    """List the livestock/dairy participation directory, then parse every
    per-year file whose first row is a header. Aggregates national totals by
    year x plan x commodity. Headerless files are dumped, not guessed."""
    import zipfile
    html = get(LDP_DIR).decode("utf-8", "replace")
    files = [l for l in re.findall(r'href="\./([^"]+)"', html)
             if not l.endswith("index.html")]
    out = {"dir_files": files, "series": {}, "layout": {}, "skipped": []}
    for fname in files:
        try:
            raw = get(LDP_DIR + fname)
        except Exception as ex:
            out["skipped"].append([fname, f"fetch {type(ex).__name__}: {ex}"])
            continue
        texts = []
        if fname.lower().endswith(".zip"):
            zf = zipfile.ZipFile(io.BytesIO(raw))
            for m in zf.namelist():
                texts.append((m, zf.read(m).decode("utf-8", "replace")))
        else:
            texts.append((fname, raw.decode("utf-8", "replace")))
        for member, text in texts:
            lines = text.splitlines()
            if not lines:
                continue
            delim = "|" if "|" in lines[0] else ","
            header = [h.strip().strip('"') for h in lines[0].split(delim)]
            if not any(c.isalpha() for c in header[0]):
                out["skipped"].append([f"{fname}:{member}", "no header row",
                                       lines[0][:200]])
                continue
            out["layout"][f"{fname}:{member}"] = header
            iy = _hdr_find(header, "commodity year", "reinsurance year", "year")
            iplan = _hdr_find(header, "insurance plan abbrev", "insurance plan name",
                              "insurance plan")
            icom = _hdr_find(header, "commodity name", "commodity")
            ipol = _hdr_find(header, "policies earning prem", "endorsements earning",
                             "policies sold")
            iqty = _hdr_find(header, "net number of head", "head count",
                             "net reported quantity", "quantity")
            iliab = _hdr_find(header, "liability")
            iprem = _hdr_find(header, "total premium", "premium")
            isub = _hdr_find(header, "subsidy")
            iind = _hdr_find(header, "indemnity")
            if None in (iy, iplan, icom, iprem, iind):
                out["skipped"].append([f"{fname}:{member}", "columns unmapped",
                                       header])
                continue
            for ln in lines[1:]:
                parts = [x.strip().strip('"') for x in ln.split(delim)]
                if len(parts) < len(header):
                    continue
                try:
                    yr = parts[iy][:4]
                    key = f"{parts[iplan]}|{parts[icom]}"
                    row = out["series"].setdefault(yr, {}).setdefault(
                        key, {"policies": 0, "quantity": 0.0, "liability": 0.0,
                              "premium": 0.0, "subsidy": 0.0, "indemnity": 0.0,
                              "src": f"{fname}:{member}"})
                    def num(i):
                        if i is None or not parts[i]:
                            return 0.0
                        return float(parts[i].replace(",", ""))
                    row["policies"] += int(num(ipol))
                    row["quantity"] += num(iqty)
                    row["liability"] += num(iliab)
                    row["premium"] += num(iprem)
                    row["subsidy"] += num(isub)
                    row["indemnity"] += num(iind)
                except (ValueError, IndexError):
                    continue
    return out


def _layout_fields(pdf_url):
    """Parse the ordered field list from an RMA record-layout PDF: rows are
    numbered 'N  Field Name  type...' lines."""
    import pdfplumber
    raw = get(pdf_url)
    fields = []
    dump = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            for ln in (page.extract_text() or "").splitlines():
                dump.append(ln)
                # rows read: "N  Element Name  Format  Description" where
                # Format is 9(..), X(..), S9(..) or DATE — single-spaced
                m = re.match(r"^\s*(\d{1,2})\s+([A-Za-z][A-Za-z0-9 /()&.'-]+?)\s+"
                             r"(?:S?9\(|X\(|DATE\b)", ln)
                if m:
                    idx = int(m.group(1))
                    if idx == len(fields) + 1:
                        fields.append(m.group(2).strip())
    return fields, dump[:120]


def rma_livestock_final():
    """Aggregate LRP/LGM/DRP using column maps parsed from RMA's own layout
    PDFs (files are headerless). Parsed layouts are recorded for audit."""
    import zipfile
    products = {
        "lrp": "LRP_Summary_of_Business_All_Years.pdf",
        "lgm": "LGM_Summary_of_Business_All_Years.pdf",
        "drp": "DRP_Summary_of_Business_2019_forward.pdf",
    }
    out = {"layouts": {}, "series": {}, "sanity": {}, "skipped": []}
    html = get(LDP_DIR).decode("utf-8", "replace")
    zips = sorted(l for l in re.findall(r'href="\./([^"]+)"', html)
                  if l.endswith(".zip"))
    for prod, layout_pdf in products.items():
        try:
            fields, dump = _layout_fields(LDP_DIR + layout_pdf)
        except Exception as ex:
            out["skipped"].append([prod, f"layout {type(ex).__name__}: {ex}"])
            continue
        out["layouts"][prod] = fields
        if len(fields) < 10:
            out["layouts"][prod + "_dump"] = dump
            out["skipped"].append([prod, "layout parse too short"])
            continue
        def find(*cands):
            return _hdr_find(fields, *cands)
        iy = find("commodity year")
        icom = find("commodity name")
        ipol = find("endorsements earning premium", "policies earning premium")
        iqty = find("net number of head", "net head count", "target marketings",
                    "declared milk production", "milk production",
                    "declared butterfat", "net quantity")
        iliab = find("liability", "total insured value")
        iprem = find("total premium")
        isub = find("subsidy", "premium subsidy")
        iind = find("indemnity")
        colmap = dict(year=iy, commodity=icom, policies=ipol, quantity=iqty,
                      liability=iliab, premium=iprem, subsidy=isub, indemnity=iind)
        out["layouts"][prod + "_colmap"] = {k: (fields[v] if v is not None else None)
                                            for k, v in colmap.items()}
        if None in (iy, icom, iprem, iind):
            out["skipped"].append([prod, "essential columns unmapped", colmap])
            continue
        for z in zips:
            if not z.startswith(prod + "_"):
                continue
            try:
                zf = zipfile.ZipFile(io.BytesIO(get(LDP_DIR + z)))
                text = zf.read(zf.namelist()[0]).decode("utf-8", "replace")
            except Exception as ex:
                out["skipped"].append([z, f"fetch {type(ex).__name__}: {ex}"])
                continue
            for ln in text.splitlines():
                parts = [x.strip() for x in ln.split("|")]
                if len(parts) < len(fields) - 2:
                    continue
                def num(i):
                    if i is None or i >= len(parts) or not parts[i]:
                        return 0.0
                    try:
                        return float(parts[i].replace(",", ""))
                    except ValueError:
                        return 0.0
                yr = parts[iy][:4] if iy < len(parts) else ""
                if not yr.startswith("20"):
                    continue
                key = f"{prod.upper()}|{parts[icom].title()}"
                row = out["series"].setdefault(yr, {}).setdefault(
                    key, {"policies": 0, "quantity": 0.0, "liability": 0.0,
                          "premium": 0.0, "subsidy": 0.0, "indemnity": 0.0,
                          "src": f"{z} (layout {layout_pdf})"})
                row["policies"] += int(num(ipol))
                row["quantity"] += num(iqty)
                row["liability"] += num(iliab)
                row["premium"] += num(iprem)
                row["subsidy"] += num(isub)
                row["indemnity"] += num(iind)
    # sanity: subsidy should not exceed premium; note violations, don't hide
    for yr, rows in out["series"].items():
        for key, r in rows.items():
            if r["premium"] and r["subsidy"] > r["premium"] * 1.001:
                out["sanity"].setdefault("subsidy_gt_premium", []).append([yr, key])
    return out


def spain_discover():
    """Agroseguro 403s; try the ministry (ENESA) pages instead."""
    out = {}
    for u in ("https://www.mapa.gob.es/es/enesa/publicaciones/",
              "https://www.mapa.gob.es/es/enesa/",
              "https://www.mapa.gob.es/es/enesa/estadisticas-del-seguro-agrario/"):
        try:
            out[u] = links_on(u)
        except Exception as ex:
            out[u] = f"{type(ex).__name__}: {ex}"
    return out


def main():
    if MODE == "discover":
        jobs = (("tarsim", tarsim_discover), ("rma", rma_discover),
                ("agroseguro", agroseguro_discover))
    elif MODE == "extract2":
        jobs = (("rma3", rma_discover3), ("spain2", spain_discover2))
    elif MODE == "extract3":
        jobs = (("rma_sob", rma_sob_probe), ("spain_all", spain_dump_all))
    elif MODE == "extract4":
        jobs = (("rma_dirs", rma_dir_listing),)
    elif MODE == "extract5":
        jobs = (("rma_livestock", rma_livestock_extract),)
    elif MODE == "extract6":
        jobs = (("rma_final", rma_livestock_final),)
    else:
        jobs = (("tarsim_series", tarsim_extract), ("rma2", rma_discover2),
                ("spain", spain_discover))
    for name, fn in jobs:
        try:
            report[name] = fn()
            print(f"[ok] {name}")
        except Exception as ex:  # one bad source must not stop the rest
            report[name] = {"error": f"{type(ex).__name__}: {ex}"}
            print(f"[FAIL] {name}: {type(ex).__name__}: {ex}")
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    suffix = {"discover": "report", "extract2": "round3",
              "extract3": "round4", "extract4": "round5",
              "extract5": "usa", "extract6": "usa"}.get(MODE, "tarsim")
    path = os.path.join(ROOT, "data", f"livestock-ins-{suffix}.json")
    json.dump(report, open(path, "w"), indent=1, ensure_ascii=False)
    print("wrote", path)


if __name__ == "__main__":
    main()
