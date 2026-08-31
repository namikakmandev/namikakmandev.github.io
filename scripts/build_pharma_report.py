#!/usr/bin/env python3
"""Bake pharma-prices.html into a single self-contained file.

This repo is private, so there is no GitHub Pages host serving it. Opened
straight off disk, the page's relative fetch() calls are blocked by the
browser's file:// origin rules and every chart comes up empty. So the data
is inlined into the HTML and the fetches are replaced with resolved
promises. The result opens by double-click, works offline, and can be
mailed or archived as one file.

The live FX call to frankfurter.app is deliberately left alone: it already
degrades to null on failure, and leaving it live means an offline copy is
merely a little stale on AUD/PLN/CZK/HUF/RON rather than wrong.

Output: pharma-report.html
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "pharma-prices.html"
OUT = ROOT / "pharma-report.html"

# (fetch expression as it appears in the source, key under EMBED, file)
SOURCES = [
    ("fetch('data/pharma-prices.json').then(r=>{ if(!r.ok) throw new Error('no data'); return r.json(); })",
     "data", "data/pharma-prices.json", True),
    ("fetch('rates.json').then(r=>r.ok?r.json():null).catch(()=>null)",
     "rates", "rates.json", False),
    ("fetch('data/fx-usd.json').then(r=>r.ok?r.json():null).catch(()=>null)",
     "fx", "data/fx-usd.json", False),
    ("fetch('data/vat-vet-medicines.json').then(r=>r.ok?r.json():null).catch(()=>null)",
     "vat", "data/vat-vet-medicines.json", False),
    ("fetch('data/vet-cpi-us.json').then(r=>r.ok?r.json():null).catch(()=>null)",
     "uscpi", "data/vet-cpi-us.json", False),
    ("fetch('data/cpi-eu.json').then(r=>r.ok?r.json():null).catch(()=>null)",
     "eucpi", "data/cpi-eu.json", False),
]


def load(rel, required):
    p = ROOT / rel
    if not p.exists():
        if required:
            sys.exit(f"build_pharma_report: {rel} is missing and is required")
        print(f"  ! {rel} missing - embedding null")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    html = SRC.read_text(encoding="utf-8")
    embed = {}
    for expr, key, rel, required in SOURCES:
        if expr not in html:
            sys.exit(f"build_pharma_report: fetch for {key} not found in "
                     f"pharma-prices.html - the page changed, update SOURCES")
        embed[key] = load(rel, required)
        html = html.replace(expr, f"Promise.resolve(EMBED.{key})")

    # "</" inside a <script> would close the block early, whatever the JSON says
    blob = json.dumps(embed, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    inject = ('<script type="application/json" id="embedded-data">' + blob + "</script>\n"
              "<script>const EMBED = JSON.parse("
              "document.getElementById('embedded-data').textContent);</script>\n")

    m = re.search(r"<body[^>]*>", html)
    if not m:
        sys.exit("build_pharma_report: no <body> tag found")
    html = html[:m.end()] + "\n" + inject + html[m.end():]

    OUT.write_text(html, encoding="utf-8")
    n = len(embed["data"].get("observations", []))
    print(f"wrote {OUT.name}: {OUT.stat().st_size/1024:.0f} KB, {n} observations")


if __name__ == "__main__":
    main()
