#!/usr/bin/env python3
"""Checks for the expenditure-control tool.

    python3 tests/test_expense_control.py

Everything is generated: a synthetic statement PDF (reportlab), a synthetic
budget workbook (openpyxl), and the text fixture in tests/fixtures. No real
statement is ever needed to run these, and none should ever be added here.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import expense_control as ec  # noqa: E402

FIXTURE = HERE / "fixtures" / "garanti-sample.txt"
RULES = ec.load_rules(ec.DEFAULT_STATEMENT_RULES)
CATEGORIES = ec.load_rules(ec.DEFAULT_CATEGORY_RULES)

PASSED = FAILED = 0


def check(label, got, want):
    global PASSED, FAILED
    if got == want:
        PASSED += 1
        print(f"  ok    {label}")
    else:
        FAILED += 1
        print(f"  FAIL  {label}\n          got  {got!r}\n          want {want!r}")


def close(label, got, want, tol=0.01):
    check(label, abs(got - want) <= tol, True) if abs(got - want) > tol else check(label, True, True)


# --------------------------------------------------------------------------

def test_numbers():
    print("\nnumber and date parsing")
    check("tr thousands", ec.parse_amount("1.284,90"), 1284.90)
    check("tr trailing minus", ec.parse_amount("5.000,00-"), -5000.0)
    check("tr parentheses", ec.parse_amount("(349,90)"), -349.90)
    check("currency suffix", ec.parse_amount("1.875,00 TL"), 1875.0)
    check("passthrough float", ec.parse_amount(12000), 12000.0)
    check("junk", ec.parse_amount("abc"), None)
    check("iso date", ec.parse_date("06/07/2026").isoformat(), "2026-07-06")
    check("dotted date", ec.parse_date("06.07.2026").isoformat(), "2026-07-06")
    check("short date + year", ec.parse_date("06/07", "2026").isoformat(), "2026-07-06")
    check("month tr long", ec.normalise_month("Eylul", 2026)[0], "2026-09")
    check("month tr short+yy", ec.normalise_month("Eyl-26")[0], "2026-09")
    check("month en", ec.normalise_month("September 2026")[0], "2026-09")
    check("month iso", ec.normalise_month("2026-09")[0], "2026-09")
    check("month junk", ec.normalise_month("Kategori")[0], None)


def test_parse_text():
    print("\nstatement parsing (text fixture)")
    parsed = ec.parse_statement(FIXTURE, RULES)
    txns = parsed["transactions"]
    check("transaction count", len(txns), 14)
    check("no unparsed money lines", len(parsed["unparsed_amount_lines"]), 0)
    check("statement date", parsed["header"]["statement_date"], "2026-08-05")
    check("period total", parsed["header"]["period_total"], 18452.30)
    check("card masked", parsed["header"]["card_number"], "5549 **** **** 1234")

    by_desc = {}
    for txn in txns:                      # keep the first of any repeated description
        by_desc.setdefault(txn["description"], txn)
    migros = by_desc["MIGROS TICARET AS ISTANBUL TR"]
    check("bonus column not taken as amount", migros["amount"], 1284.90)
    check("currency normalised", migros["currency"], "TRY")
    mm = by_desc["MEDIAMARKT ISTANBUL TR"]
    check("instalment paid", mm["installment_no"], 2)
    check("instalment total", mm["installment_total"], 6)
    check("instalment stripped from text", mm["description"], "MEDIAMARKT ISTANBUL TR")
    check("payment is a credit", by_desc["KREDI KARTI ODEME"]["amount"], -5000.0)
    check("refund is a credit", by_desc["IADE TRENDYOL ISTANBUL TR"]["amount"], -349.90)
    check("skip line ignored", "Devreden Bakiye" in by_desc, False)
    check("total line ignored", any("Toplam" in d for d in by_desc), False)


def test_parse_pdf():
    print("\nstatement parsing (generated PDF)")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        print("  skip  reportlab not installed (pip install reportlab)")
        return
    tmp = Path(tempfile.mkdtemp())
    try:
        pdf_path = tmp / "statement.pdf"
        pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
        pdf.setFont("Courier", 9)
        y = 800
        for line in FIXTURE.read_text(encoding="utf-8").splitlines():
            pdf.drawString(30, y, line)
            y -= 12
        pdf.save()

        parsed = ec.parse_statement(pdf_path, RULES)
        check("pdf transaction count", len(parsed["transactions"]), 14)
        check("pdf header parsed", parsed["header"]["period_total"], 18452.30)
        total = round(sum(t["amount"] for t in parsed["transactions"]), 2)
        check("pdf net matches text net", total,
              round(sum(t["amount"] for t in ec.parse_statement(FIXTURE, RULES)["transactions"]), 2))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_categories_and_dedupe():
    print("\ncategorisation and de-duplication")
    categorise = ec.Categoriser(CATEGORIES)
    for description, want in [
        ("MIGROS TICARET AS ISTANBUL TR", "Market"),
        ("SHELL PETROL KADIKOY TR", "Yakit"),
        ("NETFLIX COM AMSTERDAM NL", "Abonelik & Dijital"),
        ("TURKCELL ILETISIM TR", "Telekom"),
        ("ECZANE SAGLIK ISTANBUL TR", "Saglik"),
        ("UBER BV AMSTERDAM NL", "Ulasim"),
        ("KARDELEN KUYUMCULUK TR", "Diger"),
    ]:
        check(f"category {description[:22]}", categorise(description), want)

    check("merchant strips city", ec.merchant_of("MIGROS TICARET AS ISTANBUL TR"),
          "MIGROS TICARET AS ISTANBUL")

    txns = ec.parse_statement(FIXTURE, RULES)["transactions"]

    # the same charge arriving on a second, overlapping statement is a duplicate
    from copy import deepcopy
    other = deepcopy(txns)
    for txn in other:
        txn["statement"] = "overlapping-statement.pdf"
    merged, dropped = ec.dedupe(txns + other)
    check("cross-statement duplicates removed", len(merged), len(txns))
    check("duplicate count reported", dropped, len(txns))

    # but the same charge twice on ONE statement is two real charges
    kept, dropped_same = ec.dedupe(txns + deepcopy(txns))
    check("same-statement repeats kept", len(kept), len(txns) * 2)
    check("no false duplicates", dropped_same, 0)


def _make_budget(path, monthly=True):
    import openpyxl
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Butce"
    sheet["A1"] = "2026-2027 Kisisel Butce"
    if monthly:
        sheet.append([])
        sheet.append(["Kategori", "Tem", "Agu", "Eyl"])
        for row in [["Market", 2000, 2000, 2000],
                    ["Yakit", 1000, 1000, 1000],
                    ["Abonelik & Dijital", 250, 250, 250],
                    ["Telekom", 800, 800, 800],
                    ["Saglik", 1000, 1000, 1000],
                    ["Toplam", 5050, 5050, 5050]]:
            sheet.append(row)
    else:
        sheet.append([])
        sheet.append(["Kategori", "Yillik Butce"])
        for row in [["Market", 24000], ["Yakit", 36000], ["Toplam", 60000]]:
            sheet.append(row)
    workbook.save(path)


def test_budget():
    print("\nbudget reading")
    tmp = Path(tempfile.mkdtemp())
    try:
        monthly_path = tmp / "budget-monthly.xlsx"
        _make_budget(monthly_path, monthly=True)
        budget = ec.read_budget(monthly_path, year_hint=2026)
        check("monthly layout detected", budget["layout"], "monthly")
        check("months read", budget["months"], ["2026-07", "2026-08", "2026-09"])
        check("total row excluded", "Toplam" in budget["total"], False)
        check("category rolled up", budget["total"]["Market"], 6000.0)
        check("monthly cell kept", budget["monthly"]["Yakit"]["2026-08"], 1000.0)

        total_path = tmp / "budget-total.xlsx"
        _make_budget(total_path, monthly=False)
        annual = ec.read_budget(total_path)
        check("total layout detected", annual["layout"], "total")
        check("annual figure", annual["total"]["Yakit"], 36000.0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_report():
    print("\nreport")
    tmp = Path(tempfile.mkdtemp())
    try:
        budget_path = tmp / "budget.xlsx"
        _make_budget(budget_path, monthly=True)
        budget = ec.read_budget(budget_path, year_hint=2026)

        txns = ec.parse_statement(FIXTURE, RULES)["transactions"]
        categorise = ec.Categoriser(CATEGORIES)
        for txn in txns:
            txn["merchant"] = ec.merchant_of(txn["description"])
            txn["category"] = categorise(txn["description"])
        report = ec.build_report(txns, budget, CATEGORIES["fallback"])

        spend = round(sum(t["amount"] for t in txns if t["amount"] > 0), 2)
        check("total spend", report["total_spend"], spend)
        check("credits netted separately", report["total_credits"], -5349.90)
        check("market total", report["by_category"]["Market"], 2925.80)
        check("single month", report["months"], ["2026-07"])
        check("instalment commitment", report["installment_outstanding"], 4999.0 * 4)

        # The budget covers Jul-Sep but the statement only covers Jul, so the
        # comparison must be scoped to July alone rather than the whole quarter.
        check("budget scoped to overlap", report["budget_scope"]["mode"], "months")
        check("overlapping months", report["budget_scope"]["months"], ["2026-07"])

        variance = {v["label"]: v for v in report["variance"]}
        check("july market budget only", variance["Market"]["budget"], 2000.0)
        check("market over july budget", variance["Market"]["status"], "OVER")
        check("yakit over budget", variance["Yakit"]["status"], "OVER")
        check("yakit overspend", variance["Yakit"]["diff"], 3025.0)   # 4025.00 spent vs 1000.00
        check("telekom near budget", variance["Telekom"]["status"], "WATCH")  # 749/800 = 94%
        check("abonelik near budget", variance["Abonelik & Dijital"]["status"], "WATCH")  # 229.99/250 = 92%
        check("saglik within budget", variance["Saglik"]["status"], "OK")  # 512.60/1000 = 51%
        check("unbudgeted surfaces", variance["Elektronik"]["status"], "UNBUDGETED")
        check("uncategorised surfaces",
              [u["merchant"] for u in report["unmatched"]], ["KARDELEN KUYUMCULUK"])

        ec.render_html(report, tmp / "report.html")
        html = (tmp / "report.html").read_text(encoding="utf-8")
        check("html renders", html.startswith("<!doctype html>") and "Harcama Kontrolu" in html, True)
        check("html has variance table", "Butce vs gerceklesen" in html, True)
        check("console renders", "SPEND BY CATEGORY" in ec.render_console(report), True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_instalment_plans():
    print("\ninstalment plans are counted once, not once per statement")
    base = {"description": "TRENDYOL.COM", "merchant": "TRENDYOL.COM", "category": "Online Alisveris",
            "currency": "TRY", "card": "", "installment_gross": 6000.0}
    # the same 6-instalment plan as it appears on three consecutive statements
    rows = [dict(base, date="2026-01-20", amount=1000.0, installment_no=1, installment_total=6, statement="a"),
            dict(base, date="2026-02-20", amount=1000.0, installment_no=2, installment_total=6, statement="b"),
            dict(base, date="2026-03-20", amount=1000.0, installment_no=3, installment_total=6, statement="c"),
            # a different purchase of the same thing, started a month later: its own plan
            dict(base, date="2026-03-20", amount=1000.0, installment_no=2, installment_total=6, statement="c"),
            # a reversal being credited back in instalments
            dict(base, date="2026-03-20", amount=-500.0, installment_no=1, installment_total=2, statement="c",
                 installment_gross=1000.0),
            # an ordinary, non-instalment charge
            dict(base, date="2026-03-21", amount=250.0, installment_no=None, installment_total=None, statement="c")]
    plans = ec.instalment_plans(rows)
    check("three appearances collapse to one plan, plus the other two", len(plans), 3)
    latest = next(p for p in plans if p["amount"] > 0 and p["installment_no"] == 3)
    check("latest appearance kept", latest["statement"], "c")
    schedule = ec.instalment_schedule(plans)
    check("first plan: 3 of 6 paid, 3 to come", sum(r["committed"] for r in schedule.values()),
          1000.0 * 3 + 1000.0 * 4)
    check("months run forward from the latest billing", sorted(schedule)[:2], ["2026-04", "2026-05"])
    check("reversal counted as a pending credit",
          schedule["2026-04"]["pending_credits"], -500.0)
    report = ec.build_report(rows)
    check("report uses the per-plan figure", report["installment_outstanding"], 7000.0)
    check("open plan count", report["installment_open_plans"], 2)
    check("naive row-sum would have been wrong",
          sum(r["amount"] * (r["installment_total"] - r["installment_no"])
              for r in rows if r["amount"] > 0 and r["installment_total"]) != 7000.0, True)


def test_cli():
    print("\ncli end to end")
    tmp = Path(tempfile.mkdtemp())
    try:
        budget_path = tmp / "budget.xlsx"
        _make_budget(budget_path, monthly=True)
        code = ec.main(["run", str(FIXTURE), "--out", str(tmp), "--budget", str(budget_path),
                        "--budget-year", "2026", "--html"])
        check("exit code", code, 0)
        for name in ("transactions.json", "transactions.csv", "report.json",
                     "summary-by-category.csv", "budget-variance.csv", "report.html"):
            check(f"wrote {name}", (tmp / name).exists(), True)
        written = json.loads((tmp / "transactions.json").read_text(encoding="utf-8"))
        check("cli transaction count", len(written), 14)

        code = ec.main(["report", "--out", str(tmp), "--since", "2026-07-20"])
        check("date filter runs", code, 0)
        filtered = json.loads((tmp / "report.json").read_text(encoding="utf-8"))
        check("date filter applied", filtered["transactions"], 6)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for test in (test_numbers, test_parse_text, test_parse_pdf, test_categories_and_dedupe,
                 test_budget, test_report, test_instalment_plans, test_cli):
        test()
    print(f"\n{PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)
