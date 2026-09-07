#!/usr/bin/env python3
"""Browser checks for harcama-sifreli.html.

    pip install playwright && python3 tests/test_page.py

Serves the repository over http (localStorage needs a real origin), drives the
page with Chromium, and cross-checks its statement parser against the Python
CLI on the same fixture, so the two can never drift apart silently.

The pdf.js import path is not covered here: it loads from cdnjs, which this
sandbox cannot reach. Everything downstream of text extraction is covered by
feeding the fixture text straight into the page's parser.
"""

import functools
import http.server
import json
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tools/expense-control/tests/fixtures/garanti-sample.txt"
PORT = 8731
XCHECK = Path(tempfile.mkdtemp()) / "xcheck"
PASSED = FAILED = 0

def check(label, got, want):
    global PASSED, FAILED
    if got == want: PASSED += 1; print(f"  ok    {label}")
    else: FAILED += 1; print(f"  FAIL  {label}\n          got  {got!r}\n          want {want!r}")

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
class Quiet(socketserver.TCPServer):
    allow_reuse_address = True
srv = Quiet(("127.0.0.1", PORT), handler)
srv.RequestHandlerClass.log_message = lambda *a, **k: None
threading.Thread(target=srv.serve_forever, daemon=True).start()

URL = f"http://127.0.0.1:{PORT}/harcama-sifreli.html"
pages_text = FIXTURE.read_text(encoding="utf-8")

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    page.wait_for_selector("#lockBtn")

    print("\nfirst run — create the vault")
    check("fresh-vault prompt", page.inner_text("#lockTitle"), "Yeni kasa oluştur")
    check("confirm field shown", page.is_visible("#pw2"), True)
    page.fill("#pw", "1234"); page.fill("#pw2", "9999")
    page.click("#lockBtn")
    check("mismatch rejected", page.inner_text("#lockErr"), "Şifreler eşleşmiyor.")
    page.fill("#pw2", "1234"); page.click("#lockBtn")
    page.wait_for_selector("#app:not([hidden])", timeout=15000)
    check("app unlocked", page.is_visible("#app"), True)
    check("lock screen hidden after unlock", page.is_visible("#lock"), False)
    check("empty state", "Henüz veri yok" in page.inner_text("#tab-ozet"), True)

    print("\nthe page's own parser, on the CLI's fixture")
    parsed = page.evaluate("txt => parseStatementText(txt.split('\\f'), 'ekstre.pdf')", pages_text)
    check("transaction count", len(parsed["transactions"]), 14)
    check("no unparsed money lines", parsed["missed"], [])
    check("statement date", parsed["header"]["statement_date"], "05/08/2026")
    check("card masked", parsed["header"]["card_number"], "5549 **** **** 1234")
    by_desc = {}
    for t in parsed["transactions"]: by_desc.setdefault(t["description"], t)
    check("bonus col not taken as amount", by_desc["MIGROS TICARET AS ISTANBUL TR"]["amount"], 1284.90)
    check("category assigned", by_desc["SHELL PETROL KADIKOY TR"]["category"], "Yakit")
    mm = by_desc["MEDIAMARKT ISTANBUL TR"]
    check("instalment paid", mm["installment_no"], 2)
    check("instalment total", mm["installment_total"], 6)
    check("instalment stripped", mm["description"], "MEDIAMARKT ISTANBUL TR")
    check("payment is credit", by_desc["KREDI KARTI ODEME"]["amount"], -5000.0)
    check("refund is credit", by_desc["IADE TRENDYOL ISTANBUL TR"]["amount"], -349.90)

    # cross-check against the Python CLI on the same fixture
    cli = subprocess.run([sys.executable, "expense_control.py", "parse", str(FIXTURE),
                          "--out", str(XCHECK)],
                         cwd=str(ROOT / "tools/expense-control"), capture_output=True, text=True)
    py = json.loads((XCHECK / "transactions.json").read_text(encoding="utf-8"))
    key = lambda t: (t["date"], t["description"], round(t["amount"], 2), t["category"],
                     t["installment_no"], t["installment_total"])
    check("page parser == CLI parser",
          sorted(map(key, parsed["transactions"])), sorted(map(key, py)))

    print("\ningest, budget and report")
    page.evaluate("async ts => { addTransactions(ts); await save(); renderAll(); }",
                  parsed["transactions"])
    page.wait_for_timeout(300)
    check("summary rendered", "TOPLAM HARCAMA" in page.inner_text("#tab-ozet"), True)
    check("spend total shown", "17.496,09" in page.inner_text("#tab-ozet"), True)
    check("instalments shown", "19.996,00" in page.inner_text("#tab-ozet"), True)

    page.click("button[data-tab=islemler]")
    check("txn rows listed", page.locator("#txnTable tbody tr").count(), 14)
    page.fill("#filterText", "migros")
    check("filter works", page.locator("#txnTable tbody tr").count(), 2)
    page.fill("#filterText", "")

    page.click("button[data-tab=butce]")
    page.fill("#budgetTable input.bCell[data-cat='Market'][data-month='2026-07']", "2000")
    page.locator("#budgetTable input.bCell[data-cat='Market'][data-month='2026-07']").blur()
    page.wait_for_timeout(400)
    page.click("button[data-tab=ozet]")
    summary = page.inner_text("#tab-ozet")
    check("budget table appears", "BÜTÇE VS GERÇEKLEŞEN" in summary, True)
    check("scoped to overlapping month", "2026-07" in summary, True)
    check("market flagged over",
          re.search(r"Market\s+2\.000,00\s+2\.925,80\s+925,80\s+146,3%\s+OVER", summary) is not None, True)
    check("percentages use turkish decimal comma", "146.3%" in summary, False)

    print("\nuncategorised and re-categorising")
    check("uncategorised listed", "KARDELEN KUYUMCULUK" in summary, True)
    page.click("button[data-tab=islemler]")
    page.fill("#filterText", "kardelen")
    page.select_option("#txnTable tbody tr:first-child select.catSel", "Diger")
    sel = page.locator("#txnTable tbody tr:first-child select.catSel")
    sel.select_option("Kisisel Bakim")
    page.wait_for_timeout(300)
    page.click("button[data-tab=ozet]")
    check("category persisted", page.evaluate(
        "VAULT.transactions.find(t => t.merchant.startsWith('KARDELEN')).category"), "Kisisel Bakim")
    check("dropped out of uncategorised list",
          page.evaluate("buildReport(VAULT.transactions, VAULT.budget).unmatched.length"), 0)
    check("no longer counted as Diger",
          page.evaluate("buildReport(VAULT.transactions, VAULT.budget).byCategory.some(r => r[0] === 'Diger')"), False)

    print("\nmanual entry")
    page.click("button[data-tab=ekle]")
    page.fill("#mDate", "2026-07-31"); page.fill("#mDesc", "TEST KAYIT"); page.fill("#mAmount", "123.45")
    page.click("#addManual")
    page.wait_for_timeout(300)
    check("manual entry added", "1 işlem eklendi." in page.inner_text("#log"), True)
    check("count is 15", page.evaluate("VAULT.transactions.length"), 15)

    print("\nlock, wrong password, persistence")
    page.reload()
    page.wait_for_selector("#lockBtn")
    check("existing-vault prompt", page.inner_text("#lockTitle"), "Harcama Kontrolü")
    check("no confirm field", page.is_visible("#pw2"), False)
    page.fill("#pw", "yanlis"); page.click("#lockBtn")
    page.wait_for_timeout(2500)
    check("wrong password rejected", page.inner_text("#lockErr"), "Şifre yanlış — tekrar deneyin.")
    check("still locked", page.is_visible("#app"), False)
    page.fill("#pw", "1234"); page.click("#lockBtn")
    page.wait_for_selector("#app:not([hidden])", timeout=15000)
    check("data survived reload", page.evaluate("VAULT.transactions.length"), 15)
    check("budget survived reload", page.evaluate("VAULT.budget['Market']['2026-07']"), 2000)

    print("\nstorage is ciphertext only")
    raw = page.evaluate("localStorage.getItem('harcama-vault-v1')")
    for secret in ("MIGROS", "MEDIAMARKT", "5549", "TEST KAYIT"):
        check(f"'{secret}' not readable in storage", secret in raw, False)
    check("stored blob is AES-GCM envelope", sorted(json.loads(raw).keys()), ["ct", "isv", "iter", "iv", "salt"][:1] + ["iter", "iv", "salt", "v"])

    print("\nexport")
    with page.expect_download() as dl:
        page.click("button[data-tab=islemler]"); page.click("#exportCsv")
    csv_text = Path(dl.value.path()).read_text(encoding="utf-8")
    check("csv exported", csv_text.splitlines()[0].startswith("﻿date,description"), True)
    check("csv rows", len(csv_text.strip().splitlines()) - 1, 15)

    print("\npassword change")
    page.click("button[data-tab=ayarlar]")
    page.fill("#npw", "abc"); page.fill("#npw2", "abc"); page.click("#changePw")
    page.wait_for_timeout(2000)
    check("password changed", page.inner_text("#pwErr"), "Şifre değiştirildi.")
    page.reload(); page.wait_for_selector("#lockBtn")
    page.fill("#pw", "1234"); page.click("#lockBtn"); page.wait_for_timeout(2500)
    check("old password no longer works", page.is_visible("#app"), False)
    page.fill("#pw", "abc"); page.click("#lockBtn")
    page.wait_for_selector("#app:not([hidden])", timeout=15000)
    check("new password works", page.evaluate("VAULT.transactions.length"), 15)

    check("no uncaught js errors", [e for e in errors if "pdf" not in e.lower()], [])
    browser.close()
srv.shutdown()
shutil.rmtree(XCHECK.parent, ignore_errors=True)
print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
