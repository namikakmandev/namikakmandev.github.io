#!/usr/bin/env python3
"""Round 2 for the 11.1% retest -> data/_margin-archive-probe.json

Round 1: the SEC returns 403 to the Actions runner on every route, so the
US filer panel is off the table for now. Damodaran's industry margin tables
answer in five regions, but as BIFF .xls, which the stdlib cannot read.

This round settles three things:
  1. Whether the HTML edition of the US table (datafile/margin.html) carries
     the same columns — a stdlib-parseable route.
  2. Whether the archived yearly editions exist, and under what names, so
     the study can show the number drifting since the late 1990s rather
     than a single snapshot. The archive index is read for its real links.
  3. What the .xls files actually contain: sheet names, header row and the
     first data rows, read with xlrd here in Actions. The site's analysis
     scripts stay stdlib-only; only the fetch would depend on xlrd, and that
     dependency is recorded as such.
"""
import json, re, subprocess, sys, time, urllib.error, urllib.request

OUT = "data/_margin-archive-probe.json"
CAP = 8 * 1024 * 1024
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions; availability probe; +https://namikakmandev.github.io)"}
BASE = "https://pages.stern.nyu.edu/~adamodar/"


def fetch(url, cap=CAP, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(cap + 1)
    return body[:cap], len(body) > cap


def route(name, url, note, keep_body=False):
    rec = {"name": name, "url": url, "note": note}
    body = b""
    try:
        body, capped = fetch(url)
        rec.update(status=200, bytes=len(body), capped=capped, magic=body[:4].hex())
    except urllib.error.HTTPError as e:
        rec.update(status=e.code)
    except Exception as e:                       # noqa: BLE001
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    print(f"  {name}: {rec.get('status')} {rec.get('bytes', 0):,}b", flush=True)
    time.sleep(0.2)
    return (rec, body) if keep_body else rec


def html_table():
    out = {}
    rec, body = route("damodaran/margin.html", BASE + "New_Home_Page/datafile/margin.html",
                      "HTML edition of the US margin table", keep_body=True)
    out["route"] = rec
    if rec.get("status") == 200:
        html = body.decode("utf-8", "replace")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I)
        cells = [[re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S | re.I)]
                 for r in rows]
        cells = [c for c in cells if c]
        out["n_rows"] = len(cells)
        out["header"] = cells[0] if cells else None
        out["sample"] = cells[1:5]
        out["last"] = cells[-2:]
        m = re.search(r"(?:updated|as of|Date of last update)[^<]{0,80}", html, flags=re.I)
        out["date_hint"] = m.group(0) if m else None
    return out


def archives():
    """Read the archive index for its real links, then try the naming
    patterns those links suggest for margin files."""
    out = {"routes": []}
    rec, body = route("damodaran/archive-index", BASE + "New_Home_Page/dataarchived.html",
                      "index of archived yearly data; discover margin links", keep_body=True)
    out["routes"].append(rec)
    links = []
    if rec.get("status") == 200:
        html = body.decode("utf-8", "replace")
        links = sorted(set(re.findall(r'href="([^"]*margin[^"]*)"', html, flags=re.I)))
    out["archive_margin_links"] = links[:80]
    out["n_archive_margin_links"] = len(links)
    # the archive index may link to per-year pages; follow the first two
    pages = [l for l in links if l.endswith(".html")][:2]
    for p in pages:
        u = p if p.startswith("http") else BASE + "New_Home_Page/" + p.lstrip("/")
        r2, b2 = route("damodaran/archive-page", u, "per-year archive page", keep_body=True)
        out["routes"].append(r2)
        if r2.get("status") == 200:
            out.setdefault("archive_page_links", []).extend(
                sorted(set(re.findall(r'href="([^"]*margin[^"]*\.xlsx?)"', b2.decode("utf-8", "replace"), flags=re.I)))[:60])
    # direct guesses, recorded as guesses: pc/archives/margin<yy>.xls
    hits = {}
    for yy in ["98", "99"] + [f"{y:02d}" for y in range(0, 26)]:
        for pat in (f"pc/archives/margin{yy}.xls", f"pc/archives/margin{yy}.xlsx"):
            r = route(f"guess/{pat}", BASE + pat, "naming-pattern guess")
            if r.get("status") == 200:
                hits[yy] = {"url": BASE + pat, "bytes": r["bytes"], "magic": r["magic"]}
                break
    out["archive_hits_by_year"] = hits
    return out


def xls_contents():
    """Read the live .xls files with xlrd, installed here, and dump what is
    inside — sheet names, header, first rows, row count."""
    out = {"install": None, "files": {}}
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xlrd==2.0.1"], check=True,
                       capture_output=True, text=True, timeout=240)
        import xlrd                               # noqa: PLC0415
        out["install"] = "xlrd 2.0.1 ok"
    except Exception as e:                       # noqa: BLE001
        out["install"] = f"pip/xlrd failed: {type(e).__name__}: {e}"
        return out
    for name in ("margin", "marginEurope", "marginemerg", "marginGlobal", "marginJapan", "marginRest",
                 "marginChina", "marginIndia"):
        rec, body = route(f"damodaran/{name}.xls", BASE + f"pc/datasets/{name}.xls", "read with xlrd", keep_body=True)
        if rec.get("status") != 200:
            out["files"][name] = {"status": rec.get("status")}
            continue
        try:
            wb = xlrd.open_workbook(file_contents=body)
            f = {"sheets": wb.sheet_names(), "n_sheets": wb.nsheets}
            sh = wb.sheet_by_index(wb.nsheets - 1) if "Industry Averages" not in wb.sheet_names() else wb.sheet_by_name("Industry Averages")
            f["sheet_read"] = sh.name
            f["nrows"] = sh.nrows
            f["ncols"] = sh.ncols
            rows = [[sh.cell_value(r, c) for c in range(min(sh.ncols, 14))] for r in range(min(sh.nrows, 12))]
            f["first_rows"] = rows
            # locate the header row: the first row whose first cell is 'Industry Name'
            hdr = next((r for r in range(min(sh.nrows, 40)) if str(sh.cell_value(r, 0)).strip().lower().startswith("industry")), None)
            f["header_row_index"] = hdr
            if hdr is not None:
                f["header"] = [sh.cell_value(hdr, c) for c in range(sh.ncols)]
                f["n_industry_rows"] = sh.nrows - hdr - 1
                f["last_rows"] = [[sh.cell_value(r, c) for c in range(min(sh.ncols, 14))] for r in range(max(hdr + 1, sh.nrows - 3), sh.nrows)]
            # a date, if the sheet says
            for r in range(min(sh.nrows, 8)):
                v = str(sh.cell_value(r, 0))
                if re.search(r"20\d\d", v):
                    f["date_hint"] = v[:160]
                    break
            out["files"][name] = f
        except Exception as e:                   # noqa: BLE001
            out["files"][name] = {"xlrd_error": f"{type(e).__name__}: {e}"}
    return out


def main():
    doc = {"probe": "Damodaran margins: HTML edition, yearly archives, .xls contents",
           "generated_by": "scripts/probe_margin_archive.py",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for key, fn in (("html_table", html_table), ("archives", archives), ("xls_contents", xls_contents)):
        print(f"== {key}", flush=True)
        try:
            doc[key] = fn()
        except Exception as e:                   # noqa: BLE001
            doc[key] = {"fatal": f"{type(e).__name__}: {e}"}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, default=str)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
