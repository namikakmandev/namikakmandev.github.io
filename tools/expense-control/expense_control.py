#!/usr/bin/env python3
"""Credit-card expenditure control.

Turns credit-card statement PDFs into a normalised transaction list, tags every
line with a category, and checks the result against a budget spreadsheet.

Nothing here is meant to be committed. Statements go in `inbox/`, results in
`out/`; both are git-ignored, and this repository is public. Never commit a
statement, an export, or a rendered report.

Subcommands
  discover  dump what a PDF or XLSX actually contains, so the rules can be tuned
  parse     statements -> out/transactions.{json,csv}
  report    transactions (+ budget) -> variance report on stdout, CSV and HTML
  run       parse + report in one go

Typical first run:

    python3 expense_control.py discover inbox/*.pdf --password 'XXXX'
    # adjust rules/garanti-bbva.json against out/discover/*.txt, then
    python3 expense_control.py run inbox/*.pdf --password 'XXXX' \
        --budget inbox/budget.xlsx --html
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_STATEMENT_RULES = HERE / "rules" / "garanti-bbva.json"
DEFAULT_CATEGORY_RULES = HERE / "rules" / "categories.json"
DEFAULT_OUT = HERE / "out"

DATE_FORMATS = ("%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d")
AMOUNT_LIKE = re.compile(r"\d[.,]\d{2}\b")

TR_MONTHS = {
    "ocak": 1, "oca": 1, "subat": 2, "sub": 2, "mart": 3, "mar": 3,
    "nisan": 4, "nis": 4, "mayis": 5, "may": 5, "haziran": 6, "haz": 6,
    "temmuz": 7, "tem": 7, "agustos": 8, "agu": 8, "eylul": 9, "eyl": 9,
    "ekim": 10, "eki": 10, "kasim": 11, "kas": 11, "aralik": 12, "ara": 12,
}
EN_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
TOTAL_ROW = re.compile(r"^(genel\s*)?(ara\s*)?(toplam|total|sum|net)\b", re.I)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def fold(text: str) -> str:
    """Lowercase and strip Turkish diacritics, for tolerant key matching."""
    table = str.maketrans("ÇĞİIÖŞÜçğıiöşü", "cgiiosucgiiosu")
    return text.translate(table).lower().strip()


def squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" ", " ")).strip()


def parse_amount(raw, style: str = "tr"):
    """'1.234,56' -> 1234.56. Trailing '-' and (parentheses) mean negative."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace(" ", "").replace(" ", "")
    if not s:
        return None
    negative = s.startswith("-") or s.endswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.strip("()+-")
    s = re.sub(r"(TL|TRY|USD|EUR|GBP|₺|\$|€|£)", "", s, flags=re.I)
    if style == "tr":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def parse_date(raw: str, fallback_year=None):
    s = squeeze(raw).replace(".", "/").replace("-", "/")
    for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    if fallback_year and re.fullmatch(r"\d{2}/\d{2}", s):
        try:
            return datetime.strptime(f"{s}/{fallback_year}", "%d/%m/%Y").date()
        except ValueError:
            return None
    return None


def normalise_month(value, year_hint=None):
    """Anything month-shaped -> 'YYYY-MM'. Returns (month_key, had_explicit_year)."""
    if value is None:
        return None, False
    if isinstance(value, datetime):
        return f"{value.year:04d}-{value.month:02d}", True
    if hasattr(value, "year") and hasattr(value, "month"):
        return f"{value.year:04d}-{value.month:02d}", True

    text = squeeze(str(value))
    if not text:
        return None, False

    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}", True
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{4})", text)
    if m:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}", True

    m = re.fullmatch(r"([A-Za-zÇĞİÖŞÜçğıöşü]{3,12})\s*[-/. ]?\s*(\d{2}|\d{4})?", text)
    if not m:
        return None, False
    name = fold(m.group(1))
    month = TR_MONTHS.get(name) or EN_MONTHS.get(name)
    if not month:
        return None, False
    raw_year = m.group(2)
    if raw_year:
        year = int(raw_year)
        if year < 100:
            year += 2000
        return f"{year:04d}-{month:02d}", True
    if year_hint:
        return f"{int(year_hint):04d}-{month:02d}", False
    return f"0000-{month:02d}", False


def compile_all(patterns, flags=re.I):
    return [re.compile(p, flags) for p in patterns or []]


def expand_paths(entries):
    """argparse already globs on most shells, but be robust when it does not."""
    out = []
    for entry in entries:
        matches = sorted(glob.glob(entry))
        out.extend(matches or [entry])
    seen, unique = set(), []
    for path in out:
        resolved = str(Path(path).resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


# --------------------------------------------------------------------------
# text extraction
# --------------------------------------------------------------------------

def extract_pages(path: Path, password=None):
    """Return a list of page texts. Accepts .pdf, or .txt for testing/pasting."""
    if path.suffix.lower() in {".txt", ".text"}:
        return path.read_text(encoding="utf-8", errors="replace").split("\f")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"{path.name}: expected a .pdf or .txt file")

    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - environment problem
        raise SystemExit(
            "pdfplumber is required to read PDFs.  pip install pdfplumber"
        ) from exc

    try:
        with pdfplumber.open(str(path), password=password or "") as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        hint = ""
        if "password" in str(exc).lower() or "encrypt" in str(exc).lower():
            hint = ("  This statement looks password-protected — pass the bank's "
                    "PDF password with --password.")
        raise SystemExit(f"{path.name}: could not read the PDF ({exc}).{hint}")


# --------------------------------------------------------------------------
# statement parsing
# --------------------------------------------------------------------------

def load_rules(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_header(text, rules):
    header = {}
    style = rules.get("decimal_style", "tr")
    money_fields = {"period_total", "minimum_payment", "credit_limit", "available_limit"}
    for field, patterns in (rules.get("header") or {}).items():
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if not match:
                continue
            raw = squeeze(match.group(1))
            if field in money_fields:
                header[field] = parse_amount(raw, style)
            elif field.endswith("_date"):
                parsed = parse_date(raw)
                header[field] = parsed.isoformat() if parsed else raw
            else:
                header[field] = raw
            break
    return header


def _peel_installment(text, inst_re):
    """Strip a trailing '3/12' style marker. Returns (paid, total, rest)."""
    match = inst_re.search(text)
    if not match:
        return None, None, text
    paid, total = int(match.group("paid")), int(match.group("total"))
    if not (total > 1 and total >= paid >= 1):
        return None, None, text
    return paid, total, squeeze(text[: match.start()])


def parse_statement(path: Path, rules, password=None):
    pages = extract_pages(path, password)
    text = "\n".join(pages)
    header = extract_header(text, rules)

    style = rules.get("decimal_style", "tr")
    default_currency = rules.get("default_currency", "TRY")
    txn_res = compile_all(rules.get("transaction"))
    skip_res = compile_all(rules.get("skip_lines"))
    credit_res = compile_all(rules.get("credit_markers"))
    inst_re = re.compile(rules["installment"], re.I) if rules.get("installment") else None

    statement_year = None
    if header.get("statement_date"):
        statement_year = str(header["statement_date"])[:4]

    transactions, missed = [], []
    for page_no, page in enumerate(pages, 1):
        for line_no, raw_line in enumerate(page.splitlines(), 1):
            line = squeeze(raw_line)
            if not line or any(r.search(line) for r in skip_res):
                continue

            # The instalment marker sits after the amount on some layouts and at
            # the end of the description on others; peel it off the line first.
            paid = total = None
            if inst_re:
                paid, total, line = _peel_installment(line, inst_re)

            match = next((m for m in (r.match(line) for r in txn_res) if m), None)
            if not match:
                if AMOUNT_LIKE.search(line):
                    missed.append({"page": page_no, "line": line_no, "text": line})
                continue

            groups = match.groupdict()
            when = parse_date(groups.get("date", ""), statement_year)
            amount = parse_amount(groups.get("amount"), style)
            if when is None or amount is None:
                missed.append({"page": page_no, "line": line_no, "text": line})
                continue

            description = squeeze(groups.get("description") or "")
            trailing = (groups.get("trailing") or "").strip()

            if paid is None and inst_re:
                paid, total, description = _peel_installment(description, inst_re)

            if amount > 0:
                is_credit = "-" in trailing or any(r.search(description) for r in credit_res)
                if is_credit:
                    amount = -amount

            currency = (groups.get("currency") or groups.get("currency_after")
                        or default_currency).upper()
            currency = {"TL": "TRY"}.get(currency, currency)

            transactions.append({
                "date": when.isoformat(),
                "post_date": (parse_date(groups.get("post_date") or "", statement_year) or when).isoformat(),
                "description": description,
                "amount": round(amount, 2),
                "currency": currency,
                "installment_no": paid,
                "installment_total": total,
                "card": header.get("card_number", ""),
                "statement": path.name,
                "page": page_no,
                "line": line_no,
                "raw": line,
            })

    return {
        "source": str(path),
        "header": header,
        "transactions": transactions,
        "unparsed_amount_lines": missed,
        "pages": len(pages),
        "empty_text": not text.strip(),
    }


def dedupe(transactions):
    """The same charge often appears in several overlapping statements."""
    seen, unique, dropped = set(), [], 0
    for txn in transactions:
        key = (txn["card"], txn["date"], fold(txn["description"]), round(txn["amount"], 2))
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        unique.append(txn)
    return unique, dropped


# --------------------------------------------------------------------------
# categorisation
# --------------------------------------------------------------------------

class Categoriser:
    def __init__(self, rules):
        self.fallback = rules.get("fallback", "Diger")
        self.rules = [
            (rule["category"], compile_all(rule["patterns"]))
            for rule in rules.get("rules", [])
        ]

    def __call__(self, description):
        for category, patterns in self.rules:
            if any(p.search(description) for p in patterns):
                return category
        return self.fallback


def merchant_of(description):
    """Collapse a description to something stable enough to group on."""
    text = squeeze(description).upper()
    text = re.sub(r"\b\d{2}[./]\d{2}([./]\d{2,4})?\b", " ", text)
    text = re.sub(r"\b(TR|TUR|IST|ISTANBUL|ANKARA|IZMIR)\b\s*$", " ", text)
    text = re.sub(r"[^\w\s&.'-]", " ", text, flags=re.UNICODE)
    text = squeeze(text)
    return " ".join(text.split()[:4]) or "?"


# --------------------------------------------------------------------------
# budget
# --------------------------------------------------------------------------

def _sheet_grid(sheet):
    return [list(row) for row in sheet.iter_rows(values_only=True)]


def _month_header(row, year_hint):
    """Score a row as a month header. Returns {col_index: 'YYYY-MM'} or {}."""
    found, months, year, previous = {}, [], year_hint, None
    for idx, cell in enumerate(row):
        key, explicit = normalise_month(cell, year)
        if not key:
            continue
        month = int(key[5:7])
        if not explicit:
            if previous is not None and month <= previous and year:
                year = int(year) + 1
            key = f"{int(year):04d}-{month:02d}" if year else key
        else:
            year = int(key[:4])
        previous = month
        found[idx] = key
        months.append(key)
    return found if len(months) >= 2 else {}


AMOUNT_HEADER = re.compile(r"b[uü]t[çc]e|budget|plan|tutar|amount|hedef|target|yillik|annual", re.I)


def read_budget(path: Path, sheet_name=None, year_hint=None):
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("openpyxl is required to read the budget.  pip install openpyxl") from exc

    workbook = openpyxl.load_workbook(str(path), data_only=True)
    sheets = [workbook[sheet_name]] if sheet_name else list(workbook.worksheets)

    best = None
    for sheet in sheets:
        grid = _sheet_grid(sheet)
        for row_idx, row in enumerate(grid[:30]):
            columns = _month_header(row, year_hint)
            layout = "monthly"
            if not columns:
                columns = {
                    idx: "total"
                    for idx, cell in enumerate(row)
                    if isinstance(cell, str) and AMOUNT_HEADER.search(cell)
                }
                layout = "total"
            if not columns:
                continue
            entries = _read_rows(grid, row_idx, columns)
            if entries and (best is None or len(entries) > len(best["entries"])):
                best = {
                    "sheet": sheet.title,
                    "header_row": row_idx + 1,
                    "layout": layout,
                    "columns": columns,
                    "entries": entries,
                }
        if best and best["sheet"] == sheet.title and len(best["entries"]) >= 3:
            break

    if not best:
        raise SystemExit(
            f"{path.name}: could not find a budget table.  Run "
            f"`expense_control.py discover {path}` to see the sheets, then pass "
            f"--budget-sheet."
        )

    monthly, totals = defaultdict(dict), {}
    for category, values in best["entries"].items():
        for key, amount in values.items():
            if key == "total":
                totals[category] = totals.get(category, 0.0) + amount
            else:
                monthly[category][key] = monthly[category].get(key, 0.0) + amount
        if category not in totals:
            totals[category] = round(sum(monthly[category].values()), 2)

    return {
        "source": str(path),
        "sheet": best["sheet"],
        "header_row": best["header_row"],
        "layout": best["layout"],
        "months": sorted({k for k in best["columns"].values() if k != "total"}),
        "monthly": {k: dict(v) for k, v in monthly.items()},
        "total": totals,
    }


def _read_rows(grid, header_row, columns):
    amount_cols = set(columns)
    label_col = None
    for idx in range(min(amount_cols)):
        if any(isinstance(row[idx], str) and row[idx].strip()
               for row in grid[header_row + 1:] if idx < len(row)):
            label_col = idx
            break
    if label_col is None:
        label_col = 0

    entries = {}
    for row in grid[header_row + 1:]:
        if label_col >= len(row):
            continue
        label = row[label_col]
        if not isinstance(label, str) or not label.strip():
            continue
        label = squeeze(label)
        if TOTAL_ROW.match(label):
            continue
        values = {}
        for idx, key in columns.items():
            if idx >= len(row):
                continue
            amount = parse_amount(row[idx])
            if amount:
                values[key] = round(values.get(key, 0.0) + amount, 2)
        if values:
            entries.setdefault(label, {})
            for key, amount in values.items():
                entries[label][key] = round(entries[label].get(key, 0.0) + amount, 2)
    return entries


def match_budget_categories(budget_categories, spend_categories):
    """Loose name matching between the spreadsheet's labels and our categories."""
    mapping = {}
    folded = {fold(c): c for c in spend_categories}
    for label in budget_categories:
        key = fold(label)
        if key in folded:
            mapping[label] = folded[key]
            continue
        hit = next((v for k, v in folded.items() if k in key or key in k), None)
        mapping[label] = hit
    return mapping


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def build_report(transactions, budget=None, fallback="Diger"):
    spend = [t for t in transactions if t["amount"] > 0]
    credits = [t for t in transactions if t["amount"] < 0]

    by_category = defaultdict(float)
    by_month = defaultdict(float)
    by_cat_month = defaultdict(lambda: defaultdict(float))
    by_merchant = defaultdict(lambda: {"amount": 0.0, "count": 0, "category": ""})

    for txn in spend:
        month = txn["date"][:7]
        by_category[txn["category"]] += txn["amount"]
        by_month[month] += txn["amount"]
        by_cat_month[txn["category"]][month] += txn["amount"]
        entry = by_merchant[txn["merchant"]]
        entry["amount"] += txn["amount"]
        entry["count"] += 1
        entry["category"] = txn["category"]

    months = sorted(by_month)
    outstanding = 0.0
    for txn in spend:
        total, paid = txn.get("installment_total"), txn.get("installment_no")
        if total and paid and total > paid:
            outstanding += txn["amount"] * (total - paid)

    variance, scope = [], None
    if budget:
        # Only compare the months we actually have statements for: a 12-month
        # budget against one month of spending would show false headroom.
        monthly = budget.get("monthly") or {}
        budget_months = sorted({m for values in monthly.values() for m in values})
        overlap = sorted(set(months) & set(budget_months))
        scope = {
            "mode": "months" if overlap else "full",
            "months": overlap,
            "budget_months": budget_months,
            "spend_months": months,
        }

        def planned_for(label, full_total):
            if overlap:
                return round(sum(monthly.get(label, {}).get(m, 0.0) for m in overlap), 2)
            return full_total

        mapping = match_budget_categories(budget["total"], by_category)
        used = set()
        for label, full_total in sorted(budget["total"].items(), key=lambda kv: -kv[1]):
            category = mapping.get(label)
            actual = by_category.get(category, 0.0) if category else 0.0
            if category:
                used.add(category)
            variance.append(_variance_row(label, category, planned_for(label, full_total), actual))
        for category, actual in sorted(by_category.items(), key=lambda kv: -kv[1]):
            if category not in used:
                variance.append(_variance_row(category, category, 0.0, actual))

    unmatched = sorted(
        ({"merchant": m, **v} for m, v in by_merchant.items() if v["category"] == fallback),
        key=lambda r: -r["amount"],
    )

    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "transactions": len(transactions),
        "months": months,
        "total_spend": round(sum(by_category.values()), 2),
        "total_credits": round(sum(t["amount"] for t in credits), 2),
        "installment_outstanding": round(outstanding, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])},
        "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
        "by_category_month": {c: {m: round(a, 2) for m, a in sorted(ms.items())}
                              for c, ms in by_cat_month.items()},
        "top_merchants": sorted(
            ({"merchant": m, "amount": round(v["amount"], 2), "count": v["count"],
              "category": v["category"]} for m, v in by_merchant.items()),
            key=lambda r: -r["amount"],
        )[:25],
        "variance": variance,
        "budget_scope": scope,
        "unmatched": unmatched,
        "budget": {k: v for k, v in (budget or {}).items() if k != "monthly"} or None,
    }


def _variance_row(label, category, planned, actual):
    planned, actual = round(planned, 2), round(actual, 2)
    diff = round(actual - planned, 2)
    ratio = (actual / planned) if planned else None
    if planned == 0:
        status = "UNBUDGETED" if actual else "-"
    elif ratio > 1.0:
        status = "OVER"
    elif ratio > 0.85:
        status = "WATCH"
    else:
        status = "OK"
    return {
        "label": label,
        "category": category,
        "budget": planned,
        "actual": actual,
        "diff": diff,
        "used_pct": round(ratio * 100, 1) if ratio is not None else None,
        "status": status,
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def money(value):
    return f"{value:,.2f}".replace(",", " ")


def table(rows, headers, aligns=None):
    if not rows:
        return "  (nothing)\n"
    grid = [headers] + [[str(c) for c in row] for row in rows]
    widths = [max(len(r[i]) for r in grid) for i in range(len(headers))]
    aligns = aligns or ["<"] * len(headers)
    out = ["  " + "  ".join(f"{h:{a}{w}}" for h, a, w in zip(headers, aligns, widths)),
           "  " + "  ".join("-" * w for w in widths)]
    for row in grid[1:]:
        out.append("  " + "  ".join(f"{c:{a}{w}}" for c, a, w in zip(row, aligns, widths)))
    return "\n".join(out) + "\n"


def render_console(report):
    lines = [
        "",
        "=" * 72,
        f"  EXPENDITURE CONTROL   {report['generated']}",
        "=" * 72,
        f"  transactions        {report['transactions']}",
        f"  period              {report['months'][0] if report['months'] else '-'}"
        f" .. {report['months'][-1] if report['months'] else '-'}",
        f"  total spend         {money(report['total_spend'])}",
        f"  credits / refunds   {money(report['total_credits'])}",
        f"  instalments due     {money(report['installment_outstanding'])}  (future periods)",
        "",
        "  SPEND BY CATEGORY",
    ]
    total = report["total_spend"] or 1
    lines.append(table(
        [[c, money(a), f"{a / total * 100:5.1f}%"] for c, a in report["by_category"].items()],
        ["category", "amount", "share"], ["<", ">", ">"]))

    lines.append("  SPEND BY MONTH")
    lines.append(table([[m, money(a)] for m, a in report["by_month"].items()],
                       ["month", "amount"], ["<", ">"]))

    if report["variance"]:
        scope = report.get("budget_scope") or {}
        if scope.get("mode") == "months":
            lines.append(f"  BUDGET vs ACTUAL   over {len(scope['months'])} of "
                         f"{len(scope['budget_months'])} budgeted month(s): "
                         f"{', '.join(scope['months'])}")
        else:
            lines.append("  BUDGET vs ACTUAL   ! no month overlap between the budget and the "
                         "statements — comparing against the FULL budget period")
            lines.append(f"  {' ' * 20}budget covers {scope.get('budget_months') or 'no months'}; "
                         f"statements cover {scope.get('spend_months')}")
        lines.append(table(
            [[v["label"], money(v["budget"]), money(v["actual"]), money(v["diff"]),
              f"{v['used_pct']:.0f}%" if v["used_pct"] is not None else "-", v["status"]]
             for v in report["variance"]],
            ["line", "budget", "actual", "diff", "used", "status"],
            ["<", ">", ">", ">", ">", "<"]))

    lines.append("  TOP MERCHANTS")
    lines.append(table([[m["merchant"], m["category"], str(m["count"]), money(m["amount"])]
                        for m in report["top_merchants"][:15]],
                       ["merchant", "category", "n", "amount"], ["<", "<", ">", ">"]))

    if report["unmatched"]:
        missing = sum(u["amount"] for u in report["unmatched"])
        lines.append(f"  UNCATEGORISED  ({money(missing)} across "
                     f"{len(report['unmatched'])} merchants) — add these to rules/categories.json")
        lines.append(table([[u["merchant"], str(u["count"]), money(u["amount"])]
                            for u in report["unmatched"][:15]],
                           ["merchant", "n", "amount"], ["<", ">", ">"]))
    return "\n".join(lines)


def render_html(report, path: Path):
    def esc(value):
        return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    status_rows = ""
    for v in report["variance"]:
        pct = v["used_pct"] or 0
        status_rows += (
            f"<tr class='s-{v['status'].lower()}'><td>{esc(v['label'])}</td>"
            f"<td class='n'>{money(v['budget'])}</td><td class='n'>{money(v['actual'])}</td>"
            f"<td class='n'>{money(v['diff'])}</td>"
            f"<td class='meter'><span style='width:{min(pct, 100):.0f}%'></span>"
            f"<em>{pct:.0f}%</em></td><td>{v['status']}</td></tr>")

    scope = report.get("budget_scope") or {}
    if scope.get("mode") == "months":
        scope_note = (f" <small style='font-weight:400;text-transform:none'>"
                      f"({esc(', '.join(scope['months']))})</small>")
    elif scope:
        scope_note = (" <small style='font-weight:400;text-transform:none'>"
                      "(ay ortusmesi yok — tam butce donemi ile karsilastirildi)</small>")
    else:
        scope_note = ""

    cat_rows = "".join(
        f"<tr><td>{esc(c)}</td><td class='n'>{money(a)}</td>"
        f"<td class='n'>{a / (report['total_spend'] or 1) * 100:.1f}%</td></tr>"
        for c, a in report["by_category"].items())
    month_rows = "".join(f"<tr><td>{esc(m)}</td><td class='n'>{money(a)}</td></tr>"
                         for m, a in report["by_month"].items())
    merch_rows = "".join(
        f"<tr><td>{esc(m['merchant'])}</td><td>{esc(m['category'])}</td>"
        f"<td class='n'>{m['count']}</td><td class='n'>{money(m['amount'])}</td></tr>"
        for m in report["top_merchants"])
    unmatched_rows = "".join(
        f"<tr><td>{esc(u['merchant'])}</td><td class='n'>{u['count']}</td>"
        f"<td class='n'>{money(u['amount'])}</td></tr>" for u in report["unmatched"][:40])

    html = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Harcama Kontrolu</title>
<style>
:root {{ --bg:#fbfaf8; --fg:#1c1b19; --mut:#6b6862; --line:#e2ded7; --card:#fff;
         --ok:#2f7d4f; --watch:#b07510; --over:#b3402f; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141413; --fg:#eeece7; --mut:#9a968e;
  --line:#2c2b28; --card:#1c1b19; --ok:#63b184; --watch:#d9a441; --over:#e0705c; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; padding:32px 20px; background:var(--bg); color:var(--fg);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif }}
main {{ max-width:940px; margin:0 auto }}
h1 {{ font-size:22px; margin:0 0 4px }}
p.sub {{ color:var(--mut); margin:0 0 28px; font-size:13px }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:32px }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px }}
.kpi b {{ display:block; font-size:20px; font-variant-numeric:tabular-nums }}
.kpi span {{ color:var(--mut); font-size:12px; text-transform:uppercase; letter-spacing:.04em }}
h2 {{ font-size:14px; text-transform:uppercase; letter-spacing:.06em; color:var(--mut);
  margin:32px 0 10px; font-weight:600 }}
.wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--card) }}
table {{ border-collapse:collapse; width:100%; font-size:14px }}
th,td {{ padding:8px 12px; text-align:left; border-bottom:1px solid var(--line) }}
th {{ font-size:12px; color:var(--mut); font-weight:600; text-transform:uppercase; letter-spacing:.04em }}
tr:last-child td {{ border-bottom:0 }}
td.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap }}
td.meter {{ position:relative; min-width:130px }}
td.meter span {{ display:block; height:7px; border-radius:4px; background:var(--ok) }}
td.meter em {{ font-style:normal; font-size:11px; color:var(--mut) }}
tr.s-watch td.meter span {{ background:var(--watch) }}
tr.s-over td.meter span {{ background:var(--over) }}
tr.s-over td:first-child {{ font-weight:600 }}
footer {{ color:var(--mut); font-size:12px; margin-top:36px }}
</style></head><body><main>
<h1>Harcama Kontrolu</h1>
<p class="sub">{esc(report['generated'])} &middot; {report['transactions']} islem &middot;
{esc(report['months'][0] if report['months'] else '-')} –
{esc(report['months'][-1] if report['months'] else '-')}</p>
<div class="kpis">
  <div class="kpi"><span>Toplam harcama</span><b>{money(report['total_spend'])}</b></div>
  <div class="kpi"><span>Iade / odeme</span><b>{money(report['total_credits'])}</b></div>
  <div class="kpi"><span>Kalan taksit</span><b>{money(report['installment_outstanding'])}</b></div>
  <div class="kpi"><span>Kategori</span><b>{len(report['by_category'])}</b></div>
</div>
{"<h2>Butce vs gerceklesen" + scope_note + "</h2><div class='wrap'><table><thead><tr><th>Kalem</th><th>Butce</th><th>Gerceklesen</th><th>Fark</th><th>Kullanim</th><th>Durum</th></tr></thead><tbody>" + status_rows + "</tbody></table></div>" if status_rows else ""}
<h2>Kategori bazinda</h2>
<div class="wrap"><table><thead><tr><th>Kategori</th><th>Tutar</th><th>Pay</th></tr></thead><tbody>{cat_rows}</tbody></table></div>
<h2>Ay bazinda</h2>
<div class="wrap"><table><thead><tr><th>Ay</th><th>Tutar</th></tr></thead><tbody>{month_rows}</tbody></table></div>
<h2>En cok harcanan isyerleri</h2>
<div class="wrap"><table><thead><tr><th>Isyeri</th><th>Kategori</th><th>Adet</th><th>Tutar</th></tr></thead><tbody>{merch_rows}</tbody></table></div>
{"<h2>Kategorisiz</h2><div class='wrap'><table><thead><tr><th>Isyeri</th><th>Adet</th><th>Tutar</th></tr></thead><tbody>" + unmatched_rows + "</tbody></table></div>" if unmatched_rows else ""}
<footer>Kaynak: kredi karti ekstreleri{(" &middot; butce: " + esc(Path(report['budget']['source']).name)) if report.get('budget') else ""}.
Bu dosya kisisel finansal veri icerir — repoya commit etmeyin.</footer>
</main></body></html>"""
    path.write_text(html, encoding="utf-8")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def write_transactions(transactions, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "transactions.json").write_text(
        json.dumps(transactions, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["date", "post_date", "description", "merchant", "category", "amount",
              "currency", "installment_no", "installment_total", "card", "statement"]
    with (out_dir / "transactions.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(transactions)
    return out_dir / "transactions.json", out_dir / "transactions.csv"


def cmd_discover(args):
    out_dir = Path(args.out) / "discover"
    out_dir.mkdir(parents=True, exist_ok=True)
    rules = load_rules(args.rules)
    txn_res = compile_all(rules.get("transaction"))
    inst_re = re.compile(rules["installment"], re.I) if rules.get("installment") else None

    for name in expand_paths(args.files):
        path = Path(name)
        print(f"\n=== {path.name} ===")
        if path.suffix.lower() in {".xlsx", ".xlsm"}:
            _discover_workbook(path, out_dir)
            continue
        pages = extract_pages(path, args.password)
        dump, hits, amount_lines = [], 0, 0
        for page_no, page in enumerate(pages, 1):
            dump.append(f"----- page {page_no} -----")
            for line_no, raw in enumerate(page.splitlines(), 1):
                line = squeeze(raw)
                if inst_re:
                    _, _, line = _peel_installment(line, inst_re)
                matched = next((i for i, r in enumerate(txn_res) if r.match(line)), None)
                if matched is not None:
                    hits += 1
                if AMOUNT_LIKE.search(line):
                    amount_lines += 1
                flag = f"[txn:{matched}]" if matched is not None else (
                    "[?money?]" if AMOUNT_LIKE.search(line) else "")
                dump.append(f"{page_no:>3}:{line_no:<4} {flag:<9} {line}")
        target = out_dir / (path.stem + ".txt")
        target.write_text("\n".join(dump), encoding="utf-8")
        print(f"  pages {len(pages)}, lines with money {amount_lines}, "
              f"matched as transactions {hits}")
        if amount_lines and hits < amount_lines * 0.4:
            print("  ^ most money lines did not match — adjust 'transaction' in "
                  f"{Path(args.rules).name}")
        print(f"  dump: {target}")
        header = extract_header("\n".join(pages), rules)
        for key, value in header.items():
            print(f"    {key:<18} {value}")
        if not header:
            print("    (no header fields matched)")


def _discover_workbook(path: Path, out_dir: Path):
    import openpyxl
    workbook = openpyxl.load_workbook(str(path), data_only=True)
    dump = []
    for sheet in workbook.worksheets:
        print(f"  sheet '{sheet.title}'  {sheet.max_row} rows x {sheet.max_column} cols")
        dump.append(f"----- sheet: {sheet.title} -----")
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
            cells = [("" if c is None else str(c)) for c in row]
            if not any(c.strip() for c in cells):
                continue
            dump.append(f"{row_idx:>4} | " + " | ".join(cells))
            if row_idx <= 12:
                print(f"    {row_idx:>3} | " + " | ".join(c[:18] for c in cells[:10]))
    target = out_dir / (path.stem + ".txt")
    target.write_text("\n".join(dump), encoding="utf-8")
    print(f"  dump: {target}")


def _collect(args):
    rules = load_rules(args.rules)
    categorise = Categoriser(load_rules(args.categories))
    transactions, problems = [], []

    for name in expand_paths(args.files):
        path = Path(name)
        parsed = parse_statement(path, rules, args.password)
        found = len(parsed["transactions"])
        missed = len(parsed["unparsed_amount_lines"])
        print(f"  {path.name:<44} {found:>4} txn   {missed:>4} unparsed money lines")
        if parsed["empty_text"]:
            problems.append(f"{path.name}: no extractable text — the PDF is probably a scan; "
                            "OCR it first.")
        elif found == 0:
            problems.append(f"{path.name}: no transactions matched — run `discover` on it "
                            "and adjust the 'transaction' patterns.")
        transactions.extend(parsed["transactions"])

    transactions, dropped = dedupe(transactions)
    for txn in transactions:
        txn["merchant"] = merchant_of(txn["description"])
        txn["category"] = categorise(txn["description"])
    transactions.sort(key=lambda t: (t["date"], t["description"]))

    if getattr(args, "since", None):
        transactions = [t for t in transactions if t["date"] >= args.since]
    if getattr(args, "until", None):
        transactions = [t for t in transactions if t["date"] <= args.until]

    if dropped:
        print(f"  deduplicated {dropped} repeated line(s) across statements")
    for problem in problems:
        print(f"  ! {problem}")
    return transactions


def cmd_parse(args):
    transactions = _collect(args)
    if not transactions:
        raise SystemExit("no transactions parsed — nothing written")
    json_path, csv_path = write_transactions(transactions, Path(args.out))
    print(f"\n  {len(transactions)} transactions -> {json_path}\n"
          f"  {' ' * len(str(len(transactions)))} {' ' * 12} {csv_path}")
    return transactions


def _report(transactions, args):
    budget = None
    if args.budget:
        year_hint = args.budget_year or (transactions[0]["date"][:4] if transactions else None)
        budget = read_budget(Path(args.budget), args.budget_sheet, year_hint)
        print(f"  budget: sheet '{budget['sheet']}' row {budget['header_row']}, "
              f"{budget['layout']} layout, {len(budget['total'])} lines")

    fallback = load_rules(args.categories).get("fallback", "Diger")
    report = build_report(transactions, budget, fallback)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "summary-by-category.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["category", "amount"])
        writer.writerows(report["by_category"].items())
    if report["variance"]:
        with (out_dir / "budget-variance.csv").open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(report["variance"][0]))
            writer.writeheader()
            writer.writerows(report["variance"])

    print(render_console(report))
    print(f"  written: {out_dir / 'report.json'}")
    if args.html:
        html_path = out_dir / "report.html"
        render_html(report, html_path)
        print(f"           {html_path}")
    return report


def cmd_report(args):
    source = Path(args.transactions or Path(args.out) / "transactions.json")
    if not source.exists():
        raise SystemExit(f"{source} not found — run `parse` first")
    transactions = json.loads(source.read_text(encoding="utf-8"))
    if args.since:
        transactions = [t for t in transactions if t["date"] >= args.since]
    if args.until:
        transactions = [t for t in transactions if t["date"] <= args.until]
    _report(transactions, args)


def cmd_run(args):
    _report(cmd_parse(args), args)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="expense_control.py",
        description="Control expenditure against a budget, from credit-card statement PDFs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Typical first run:")[-1])
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--rules", default=str(DEFAULT_STATEMENT_RULES),
                        help="statement parsing rules (default: rules/garanti-bbva.json)")
    common.add_argument("--categories", default=str(DEFAULT_CATEGORY_RULES),
                        help="category keyword rules (default: rules/categories.json)")
    common.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output directory (default: tools/expense-control/out, git-ignored)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_inputs(sub):
        sub.add_argument("files", nargs="+", help="statement PDFs (or .txt dumps)")
        sub.add_argument("--password", help="PDF password, if the statement is protected")

    def add_filters(sub):
        sub.add_argument("--since", help="drop transactions before this ISO date")
        sub.add_argument("--until", help="drop transactions after this ISO date")

    def add_budget(sub):
        sub.add_argument("--budget", help="budget .xlsx to compare against")
        sub.add_argument("--budget-sheet", help="sheet name, if auto-detection picks the wrong one")
        sub.add_argument("--budget-year", help="year for bare month headers like 'Eylul'")
        sub.add_argument("--html", action="store_true", help="also write out/report.html")

    discover = subparsers.add_parser("discover", parents=[common], help="dump what a PDF/XLSX contains")
    add_inputs(discover)
    discover.set_defaults(func=cmd_discover)

    parse = subparsers.add_parser("parse", parents=[common], help="statements -> transactions")
    add_inputs(parse)
    add_filters(parse)
    parse.set_defaults(func=cmd_parse)

    report = subparsers.add_parser("report", parents=[common], help="transactions (+budget) -> variance report")
    report.add_argument("--transactions", help="transactions.json (default: <out>/transactions.json)")
    add_filters(report)
    add_budget(report)
    report.set_defaults(func=cmd_report)

    run = subparsers.add_parser("run", parents=[common], help="parse + report")
    add_inputs(run)
    add_filters(run)
    add_budget(run)
    run.set_defaults(func=cmd_run)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
