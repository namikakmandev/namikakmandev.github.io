# Expenditure control

Turns credit-card statement PDFs into a categorised transaction list and checks
it against a budget spreadsheet. Built for the Garanti BBVA / Bonus *Geçmiş
Dönem Kredi Kartı Ekstresi*, with a second, regex-driven layout for simpler
statements — either way an issuer is one JSON file.

**Every statement is checked against the bank's own "Dönem Borcunuz".** Carried
forward + charges − credits has to land on the printed period total. That is
what establishes the parse is complete: not that it looked plausible, but that
it adds up to the figure the bank itself prints.

> **This repository is public.** Statements go in `inbox/`, results in `out/`.
> Both are git-ignored — keep them that way. Never commit a statement, an
> export, or a rendered report.

## Install

```bash
pip install pdfplumber openpyxl      # reportlab and playwright too, for the tests
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

### Two layouts

`rules/garanti-bonus.json` (`"layout": "columns"`, the default) reads the table
by **where the numbers sit**, because on this statement a regex over flattened
text cannot be correct:

- Two right-aligned money columns, Bonus (TL) and Tutar (TL). Only Tutar is
  expenditure — a bonus-campaign line carries its figure in the Bonus column,
  so "the last number on the line" books loyalty points as money spent.
- A third column holds the original amount and currency of a foreign charge;
  these are kept as `original_amount` / `original_currency`.
- Dates are Turkish long form, "24 Aralık 2025".
- Instalments read "1.760,00x3=5.280,00 1.Taksit".
- A trailing `+` on the amount marks a credit — a payment, refund or reversal.
- Fee lines (DÖNEM FAİZİ, GEÇ ÖDEME FAİZİ, KKDF + BSMV) carry no date at all.
- The template paints invisible ~2pt "bosluk" spacer glyphs that glue
  themselves onto the amount, so anything under `min_font_size` is dropped
  before words are built.

The amount column is found from the data (the rightmost cluster of right-edges
across dated rows), not hard-coded, so it survives a change of page geometry.

`rules/garanti-bbva.json` (`"layout": "lines"`) is the regex-per-line form, for
statements whose columns do survive being flattened to text.

**`rules/garanti-bbva.json`** — line layout.

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

## Şifreli sayfa (tarayıcıda)

If you would rather not touch the command line, `harcama-sifreli.html` at the
repository root is the same tool as a password-locked web page — the same
`*-sifreli` pattern as the other protected reports here, but read/write.

Open it at `https://namikakmandev.github.io/harcama-sifreli.html`. On first
visit you set a password (anything you like — short is fine); after that the
page asks for it before showing anything.

- **Your data never leaves the browser.** Transactions and budget are encrypted
  with AES-256-GCM (PBKDF2-SHA256, 250 000 iterations) under your password and
  kept in that browser's `localStorage`. Nothing is uploaded, and nothing is
  written to this repository.
- **Import** statement PDFs by drag-and-drop — parsed in the page, with the
  same column logic and the same reconciliation check as the CLI, which the
  import log reports per file. Also a `transactions.csv` from the CLI, or one
  transaction at a time by hand.
- **Import a budget `.xlsx`** — the page finds the month-header row and the
  items under it, shows what it found, and asks before applying. Either every
  row becomes a category budget, or one row (a household cash-flow sheet
  usually has a single line per card) becomes the monthly total to measure
  against. The workbook is read natively: an `.xlsx` is a ZIP of XML and the
  browser can inflate and parse both, so there is no spreadsheet library.
- **Budget** can also be typed into a category × month grid; the "Aylık" box
  fills every month at once.
- **Özet** shows the same figures as the CLI report: budget vs actual scoped to
  the overlapping months, spend by category and month, top merchants,
  outstanding instalments, and the uncategorised list. Categories can be
  reassigned inline from the İşlemler tab.
- **Backups** export as an encrypted file that only opens with the same
  password, so you can move the vault to another browser or machine.

Caveats worth knowing:

- The password protects the **vault**, not the page. The page itself is public
  — anyone can open it, but they see a lock screen and ciphertext.
- **Lose the password and the data is gone.** There is no recovery. Take an
  encrypted backup.
- `localStorage` is per-browser and per-device. Clearing site data wipes the
  vault; use a backup.
- pdf.js is vendored in `assets/vendor/pdfjs/` and served from this repository,
  so PDF reading works offline and depends on no CDN.
- The page is deliberately **not linked from the site navigation**. It is
  reachable only if you know the URL.

The page and the CLI share one set of rules. After editing anything in
`rules/`, run:

```bash
python3 scripts/build_expense_page.py
```

which injects the current rules into the page. `tests/test_page.py` asserts
that the page's parser and the CLI's parser return identical results on the
same fixture, so the two cannot drift apart unnoticed.

## Tests

```bash
python3 tests/test_expense_control.py     # 79 checks on the CLI, ~3 s
python3 tests/test_page.py                # 43 checks driving the page in Chromium
```

The browser test needs `pip install playwright`. It serves the repository over
http, drives `harcama-sifreli.html`, and verifies the crypto round-trip, that
a wrong password is rejected, and that nothing readable is left in
`localStorage`.

Everything is synthetic. `tests/make_fixture_pdf.py` generates a statement in
the column layout with all of its awkwardness — the two money columns, a
bonus-only row, a foreign charge, instalments, a `+` credit, undated fee rows
and the invisible spacer glyphs — and the fixture computes its own period total
so the reconciliation check is exercised for real. Budgets are generated with
openpyxl. The tests never need — and must never be given — a real statement.

`test_page.py` also asserts that the page and the CLI return identical
transactions from the same PDF, so the two parsers cannot drift apart.
