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


def main():
    if MODE != "discover":
        raise SystemExit("extraction pass not written yet — run MODE=discover "
                         "first and write the parser against its output")
    for name, fn in (("tarsim", tarsim_discover), ("rma", rma_discover),
                     ("agroseguro", agroseguro_discover)):
        try:
            report[name] = fn()
            print(f"[ok] {name}")
        except Exception as ex:  # one bad source must not stop the rest
            report[name] = {"error": f"{type(ex).__name__}: {ex}"}
            print(f"[FAIL] {name}: {type(ex).__name__}: {ex}")
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    path = os.path.join(ROOT, "data", "livestock-ins-report.json")
    json.dump(report, open(path, "w"), indent=1, ensure_ascii=False)
    print("wrote", path)


if __name__ == "__main__":
    main()
