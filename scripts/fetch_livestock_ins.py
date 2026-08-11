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
    suffix = "report" if MODE == "discover" else "tarsim"
    path = os.path.join(ROOT, "data", f"livestock-ins-{suffix}.json")
    json.dump(report, open(path, "w"), indent=1, ensure_ascii=False)
    print("wrote", path)


if __name__ == "__main__":
    main()
