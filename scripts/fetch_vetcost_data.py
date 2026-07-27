#!/usr/bin/env python3
"""Test the hypothesis: does veterinary + medicine spend PER HEAD rise as herds shrink?

USDA ERS publishes commodity costs and returns, including a
"veterinary and medicine" line for cow-calf operations, per bred cow.

Two modes:
  MODE=discover  -> crawl the ERS product pages and report every data-file link
  (default)      -> download the file named in ERS_URL and parse the vet line

Writes data/vetcost-report.json either way, so a failure is visible rather than silent.
"""
import io, json, os, re, sys, urllib.request

UA = {"User-Agent": "namikakmandev-cattle-story/1.0 (github actions)"}
report = {}


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


PAGES = [
    "https://www.ers.usda.gov/data-products/commodity-costs-and-returns",
    "https://www.ers.usda.gov/data-products/commodity-costs-and-returns/commodity-costs-and-returns",
]


def discover():
    found = {}
    for page in PAGES:
        try:
            html = get(page).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            found[page] = f"ERROR {type(e).__name__}: {e}"
            continue
        links = re.findall(r'href="([^"]+)"', html)
        data = [l for l in links
                if re.search(r"\.(xlsx?|csv)(\?|$)", l, re.I)
                or "webdocs/DataFiles" in l]
        # keep the cattle-relevant ones first
        cattle = [l for l in data if re.search(r"cow|calf|cattle|beef", l, re.I)]
        found[page] = {"total_data_links": len(data),
                       "cattle_links": cattle[:25],
                       "sample_other": data[:15]}
    report["discover"] = found
    print(json.dumps(found, indent=1)[:6000])


def parse_file(url):
    raw = get(url)
    report["file"] = {"url": url, "bytes": len(raw)}
    name = url.lower()
    if name.endswith(".csv") or ".csv?" in name:
        text = raw.decode("utf-8", "replace")
        lines = text.splitlines()
        report["head"] = lines[:8]
        rows = [r for r in lines if re.search(r"veterinar", r, re.I)]
        report["vet_rows"] = rows[:40]
        print("HEAD:"); print("\n".join(lines[:8]))
        print("VET ROWS:", len(rows)); print("\n".join(rows[:40]))
        return
    # xls/xlsx
    try:
        import openpyxl  # noqa: PLC0415
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
        out = {}
        for ws in wb.worksheets:
            hits = []
            for row in ws.iter_rows(values_only=True):
                cells = [c for c in row if c is not None]
                if cells and any(isinstance(c, str) and re.search(r"veterinar", c, re.I) for c in cells):
                    hits.append([str(c)[:40] for c in cells][:30])
            if hits:
                out[ws.title] = hits[:5]
        report["sheets_with_vet"] = out
        print(json.dumps(out, indent=1)[:6000])
    except Exception as e:  # noqa: BLE001
        report["parse_error"] = f"{type(e).__name__}: {e}"
        print("parse error:", e)


def main():
    os.makedirs("data", exist_ok=True)
    mode = os.environ.get("MODE", "").strip()
    url = os.environ.get("ERS_URL", "").strip()
    if mode == "discover" or not url:
        discover()
    else:
        parse_file(url)
    json.dump(report, open("data/vetcost-report.json", "w"), indent=1)


if __name__ == "__main__":
    main()
