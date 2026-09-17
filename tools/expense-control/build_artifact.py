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
    a = ap.parse_args()
    out = Path(a.out); (out / "data").mkdir(parents=True, exist_ok=True)

    src = io.open(ROOT / "harcama-sifreli.html", encoding="utf-8").read()
    rules_stmt = re.search(r'<script id="rules-statement" type="application/json">(.*?)</script>', src, re.S).group(1)
    rules_cats = re.search(r'<script id="rules-categories" type="application/json">(.*?)</script>', src, re.S).group(1)
    viz_css = cut(src, "/* @viz-start", "/* @viz-end */") + "/* @viz-end */"
    js = cut(src, "/* ------------------------------------------------------------------- rules */",
                  "/* ------------------------------------------------------------------- vault */")
    render = cut(src, "/* ------------------------------------------------------------------ render */",
                      "/* ------------------------------------------------------------------ events */")
    events = cut(src, "/* ------------------------------------------------------------------ events */",
                      "$('exportCsv').addEventListener")
    render = render.replace("'son kayıt '", "'son güncelleme '")

    page = (SHELL_CSS.replace("/* @viz */", viz_css) + SHELL_BODY
            + '\n<script id="rules-statement" type="application/json">' + rules_stmt + '</script>'
            + '\n<script id="rules-categories" type="application/json">' + rules_cats + '</script>'
            + '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>'
            + '\n<script>\n"use strict";\n' + js + SHELL_JS.split("/* @render */")[0] + render + events
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
        tx = json.loads(Path(a.transactions).read_text(encoding="utf-8"))
        for i, t in enumerate(tx):
            t.setdefault("id", f"{t['date']}|{t['description']}|{t['amount']:.2f}|{t.get('card','')}|{t['statement']}|{i}")
            for k in ("raw", "page", "line", "post_date"): t.pop(k, None)
        vault = {"version": 1, "transactions": tx, "budget": {}, "updated": datetime.now().isoformat(timespec="seconds")}
        if a.budget and a.budget_line:
            b = ec.read_budget(Path(a.budget), a.budget_sheet, a.budget_year)
            label = next(k for k in b["monthly"] if ec.fold(k) == ec.fold(a.budget_line))
            vault["totalBudget"] = {m: abs(v) for m, v in b["monthly"][label].items()}
            vault["totalBudgetLabel"] = label
        (out / "data" / "vault.json").write_text(json.dumps(vault, ensure_ascii=False), encoding="utf-8")
    print(f"  {out/'index.html'}  ({(out/'index.html').stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
