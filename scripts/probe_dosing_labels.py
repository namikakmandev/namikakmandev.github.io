#!/usr/bin/env python3
"""Fetch the three tablet brands' official dosing tables -> data/_dosing-*.txt

The cost-per-day grid prices one weight-matched dose per brand. Adding a second
reference weight needs each label's weight band for it, and the dev sandbox
cannot reach any regulator or manufacturer domain, so this runs where the
network works and saves the label TEXT. Nothing is parsed into the page from
here: a person reads the table and writes the recipe down, with the source.
"""
import gzip, io, json, os, re, sys, time, urllib.request

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0.0.0 Safari/537.36"),
      "Accept": "*/*", "Accept-Encoding": "gzip"}
CAP = 12 * 1024 * 1024

DOCS = [
    ("apoquel-ema-spc", "https://www.ema.europa.eu/en/documents/product-information/apoquel-epar-product-information_en.pdf"),
    ("apoquel-vmd-spc", "https://www.vmd.defra.gov.uk/productinformationdatabase/files/SPC_Documents/SPC_2222828.PDF"),
    ("apoquel-dailymed", "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=275a2c51-9679-4f42-b8cc-21b04369a056"),
    ("zenrelia-dailymed-pdf", "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid=adf9a1c8-31bd-4301-ac25-814d13f34cae&type=pdf"),
    ("zenrelia-dailymed", "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=adf9a1c8-31bd-4301-ac25-814d13f34cae"),
    ("zenrelia-elanco-guide", "https://assets.elanco.com/0cec44ed-3eaa-0009-2029-666567e7e4de/e64f1873-62ae-40b3-a861-bc909e05c74e/Zenrelia%20Launch%20Dosage%20Guide.pdf"),
    ("zenrelia-ema-spc", "https://www.ema.europa.eu/en/documents/product-information/zenrelia-epar-product-information_en.pdf"),
    ("numelvi-ec-annex", "https://ec.europa.eu/health/documents/community-register/2025/20250724166836/anx_166836_en.pdf"),
    ("numelvi-vmd-spc", "https://www.vmd.defra.gov.uk/productinformationdatabase/files/SPC_Documents/SPC_3179257.PDF"),
    ("numelvi-dailymed", "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=4926fcfa-20a0-46d8-aca2-53ae88332a31"),
]


def get(url, timeout=90, tries=3):
    last = None
    for i in range(tries):
        if i:
            time.sleep(5 * 2 ** (i - 1))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(CAP + 1)
                if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                    try:
                        body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
                    except OSError:
                        pass
                return r.status, r.headers.get("Content-Type", ""), body[:CAP]
        except Exception as ex:
            last = ex
    raise last


def to_text(ctype, body):
    if body[:5] == b"%PDF-":
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(body))
        return "\n\n".join((pg.extract_text() or "") for pg in rd.pages)
    html = body.decode("utf-8", "replace")
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)</(tr|p|div|li|h\d|table)>", "\n", html)
    html = re.sub(r"(?i)</t[dh]>", " | ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"[ \t]+", " ", html)
    return re.sub(r"\n\s*\n+", "\n", html)


def main():
    os.makedirs("data", exist_ok=True)
    log = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "docs": []}
    for name, url in DOCS:
        rec = {"name": name, "url": url}
        try:
            status, ctype, body = get(url)
            rec["status"], rec["type"], rec["bytes"] = status, ctype, len(body)
            text = to_text(ctype, body)
            path = f"data/_dosing-{name}.txt"
            open(path, "w").write(text)
            rec["file"], rec["chars"] = path, len(text)
            rec["kg_lines"] = sum(1 for ln in text.splitlines() if re.search(r"\bkg\b", ln))
            print(name, status, len(body), "bytes ->", path, rec["kg_lines"], "kg lines")
        except Exception as ex:
            rec["error"] = f"{type(ex).__name__}: {ex}"
            print(name, "ERROR", rec["error"])
        log["docs"].append(rec)
        time.sleep(2)
    json.dump(log, open("data/_dosing-labels-probe.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
