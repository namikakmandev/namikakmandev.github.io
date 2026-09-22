#!/usr/bin/env python3
"""Assemble the shared claude.ai page from the site page.

    python3 build_artifact.py --out <dir>        # writes <dir>/index.html and <dir>/data/vault.json
        [--budget <xlsx> --budget-year 2025 --budget-line 'ebru kk']

harcama-sifreli.html is the source of truth for the parser, the report and the
rendering; this takes those blocks and wraps them in the artifact's shell (no
lock screen, data in data/vault.json, edits saved by republishing that file).
"""
import argparse, io, json, re, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import expense_control as ec  # noqa: E402

SHELL_CSS = (HERE / "artifact" / "shell.css").read_text(encoding="utf-8")
SHELL_BODY = (HERE / "artifact" / "shell.html").read_text(encoding="utf-8")
SHELL_JS = (HERE / "artifact" / "shell.js").read_text(encoding="utf-8")


def cut(src, start, end):
    return src[src.index(start):src.index(end)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--transactions", default=str(HERE / "out" / "transactions.json"))
    ap.add_argument("--budget"); ap.add_argument("--budget-sheet"); ap.add_argument("--budget-year")
    ap.add_argument("--budget-line"); ap.add_argument("--no-data", action="store_true")
    ap.add_argument("--owner", action="append", default=[],
                    help="NAME:transactions.json:budget-row — one per person; may repeat")
    a = ap.parse_args()
    out = Path(a.out); (out / "data").mkdir(parents=True, exist_ok=True)

    src = io.open(ROOT / "harcama-sifreli.html", encoding="utf-8").read()
    rules_stmt = re.search(r'<script id="rules-statement" type="application/json">(.*?)</script>', src, re.S).group(1)
    rules_cats = re.search(r'<script id="rules-categories" type="application/json">(.*?)</script>', src, re.S).group(1)
    rules_teb = re.search(r'<script id="rules-statement-teb" type="application/json">(.*?)</script>', src, re.S).group(1)
    viz_css = cut(src, "/* @viz-start", "/* @viz-end */") + "/* @viz-end */"
    js = cut(src, "/* ------------------------------------------------------------------- rules */",
                  "/* ------------------------------------------------------------------- vault */")
    owners = cut(src, "/* Whose card a statement belongs to", "async function save()")
    render = cut(src, "/* ------------------------------------------------------------------ render */",
                      "/* ------------------------------------------------------------------ events */")
    events = cut(src, "/* ------------------------------------------------------------------ events */",
                      "$('exportCsv').addEventListener")
    render = render.replace("'son kayıt '", "'son güncelleme '")

    page = (SHELL_CSS.replace("/* @viz */", viz_css) + SHELL_BODY
            + '\n<script id="rules-statement" type="application/json">' + rules_stmt + '</script>'
            + '\n<script id="rules-statement-teb" type="application/json">' + rules_teb + '</script>'
            + '\n<script id="rules-categories" type="application/json">' + rules_cats + '</script>'
            + '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>'
            + '\n<script>\n"use strict";\n' + js + owners + SHELL_JS.split("/* @render */")[0] + render + events
            + SHELL_JS.split("/* @render */")[1])
    page = page.replace("pdfjsLib.GlobalWorkerOptions.workerSrc = 'assets/vendor/pdfjs/pdf.worker.min.js';",
                        "pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';")
    page = re.sub(r"document\.querySelectorAll\('\.tabs button'\)\.forEach\(btn => btn\.addEventListener\('click', \(\) => \{.*?\}\)\);\n", "", page, flags=re.S)
    page = page.replace("document.querySelector('.tabs button[data-tab=ekle]').click();", "location.hash = '#tab-ekle';")
    page = page.replace("document.querySelector('.tabs button[data-tab=ozet]').click();", "location.hash = '#tab-ozet';")
    page = page.replace("html += '<h2>Gelecek aylara şimdiden yazılmış taksitler</h2>'",
                        "html += '<h2 id=\"taahhut\">Gelecek aylara şimdiden yazılmış taksitler</h2>'")
    (out / "index.html").write_text(page, encoding="utf-8")

    if not a.no_data:
        budget = ec.read_budget(Path(a.budget), a.budget_sheet, a.budget_year) if a.budget else None
        specs = a.owner or [f"Ebru:{a.transactions}:{a.budget_line or ''}"]
        tx, cards, budgets = [], {}, {}
        for spec in specs:
            name, path, row = (spec.split(":") + [""])[:3]
            part = json.loads(Path(path).read_text(encoding="utf-8"))
            for t in part:
                for k in ("raw", "page", "line", "post_date"): t.pop(k, None)
                if t.get("card"): cards[t["card"]] = name
            tx.extend(part)
            if budget and row:
                label = next(k for k in budget["monthly"] if ec.fold(k) == ec.fold(row))
                budgets[name] = {m: abs(v) for m, v in budget["monthly"][label].items()}
        tx.sort(key=lambda t: (t["date"], t["description"]))
        for i, t in enumerate(tx):
            t["id"] = f"{t['date']}|{t['description']}|{t['amount']:.2f}|{t.get('card','')}|{t['statement']}|{i}"
        vault = {"version": 2, "transactions": tx, "budget": {}, "cards": cards, "budgets": budgets,
                 "updated": datetime.now().isoformat(timespec="seconds")}
        (out / "data" / "vault.json").write_text(json.dumps(vault, ensure_ascii=False), encoding="utf-8")
        print(f"  vault: {len(tx)} transactions, cards {cards}, budgets for {sorted(budgets)}")
    print(f"  {out/'index.html'}  ({(out/'index.html').stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
