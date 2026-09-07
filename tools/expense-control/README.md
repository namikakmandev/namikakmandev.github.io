# Expenditure control

Turns credit-card statement PDFs into a categorised transaction list and checks
it against a budget spreadsheet. Built for the Garanti BBVA *Geçmiş Dönem Kredi
Kartı Ekstresi* layout, but the parsing is entirely regex-driven, so any issuer
is a matter of editing one JSON file.

> **This repository is public.** Statements go in `inbox/`, results in `out/`.
> Both are git-ignored — keep them that way. Never commit a statement, an
> export, or a rendered report.

## Install

```bash
pip install pdfplumber openpyxl      # reportlab too, if you want to run the tests
```

## Use

```bash
cd tools/expense-control
mkdir -p inbox && cp ~/Downloads/*.pdf inbox/     # statements + the budget .xlsx

# 1. see what the PDFs actually contain, and whether the rules match them
python3 expense_control.py discover inbox/*.pdf --password 'XXXX'

# 2. once discover reports a sensible transaction count, run the whole thing
python3 expense_control.py run inbox/*.pdf --password 'XXXX' \
    --budget inbox/'2026-2027 budget personally.xlsx' --html
```

`--password` is only needed if the bank protects the PDF; Turkish banks usually
do. If a statement is a scan rather than real text, `discover` will say so —
OCR it first (`ocrmypdf in.pdf out.pdf`).

### Subcommands

| command | what it does |
| --- | --- |
| `discover FILES...` | Dumps every line of a PDF (or every cell of an `.xlsx`) to `out/discover/`, flagging which lines matched a transaction pattern (`[txn:0]`) and which look like money but did not (`[?money?]`). This is how you tune the rules. |
| `parse FILES...` | Statements → `out/transactions.json` and `out/transactions.csv`. |
| `report` | `out/transactions.json` (+ `--budget`) → console summary, `out/report.json`, `out/summary-by-category.csv`, `out/budget-variance.csv`, and with `--html` a self-contained `out/report.html`. |
| `run FILES...` | `parse` then `report`. |

Useful flags: `--since` / `--until` (ISO dates), `--budget-sheet`,
`--budget-year` (for bare month headers like `Eylül`), `--out`.

## What the report tells you

- spend by category and by month, with each category's share
- **budget vs actual** per line: planned, actual, difference, % used, and a
  status — `OK`, `WATCH` (>85% used), `OVER`, or `UNBUDGETED` (you spent on
  something with no budget line at all)
- top merchants by spend
- **instalments due** — the remaining commitment from every `n/m` charge, i.e.
  what is already locked into future statements before you spend anything
- **uncategorised** — merchants that fell through to `Diğer`, with amounts, so
  you know exactly what to add to `rules/categories.json` next

Payments and refunds are detected and carried as negative amounts; they are
netted out of "spend" and reported separately, so a card payment never looks
like expenditure.

## Tuning

**`rules/garanti-bbva.json`** — statement layout.

- `header` — one or more regexes per field; the first that matches wins.
- `transaction` — the line patterns. Pattern 1 treats the **first** money
  column as the amount and an optional **second** as the bonus/points column.
  If your statement prints a running balance first and the amount last, copy
  `transaction_amount_last` over `transaction`.
- `installment` — an `n/m` marker, stripped from the description whether it
  sits at the end of the line or the end of the description.
- `skip_lines` — subtotals, page furniture, carried-forward balances.
- `credit_markers` — descriptions that mean money coming back (payments,
  refunds, cancellations), flipped to negative.

The workflow is always: run `discover`, open `out/discover/<name>.txt`, find a
transaction line that is flagged `[?money?]` instead of `[txn:0]`, and widen the
pattern until it matches.

**`rules/categories.json`** — merchant keywords. First match wins, so specific
merchants go above generic keywords. Patterns are case-insensitive regexes
matched against the description. The `UNCATEGORISED` block at the end of every
report is your to-do list for this file.

## Adding another issuer

Copy `rules/garanti-bbva.json`, edit the patterns against that bank's
`discover` dump, and pass `--rules rules/<bank>.json`. Statements from different
banks can be parsed separately into the same `out/` and reported together;
`parse` de-duplicates identical charges that appear in overlapping statements.

## Tests

```bash
python3 tests/test_expense_control.py     # 71 checks, ~2 s
```

Everything is synthetic: a text fixture, a statement PDF generated with
reportlab, and a budget workbook generated with openpyxl. The tests never need
— and must never be given — a real statement.
