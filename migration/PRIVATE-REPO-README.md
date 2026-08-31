# Pharma price tracker

Daily retail prices for the five canine atopic-dermatitis brands — Cytopoint
and Apoquel (Zoetis), Numelvi (Merck), Zenrelia (Elanco) — tracked per form,
per strength, per venue, per country across 15 markets, with history
reconstructed from web archives back to 2016.

**This repo is private on purpose.** It holds a working price study, not a
published one. Nothing here is served on the open web.

## Reading the report

Open **`pharma-report.html`** — double-click it. All data is baked in, so it
works offline and needs no server.

`pharma-prices.html` is the *source* of that file. It fetches its data at
runtime and therefore only works behind a web server; opened off disk it
comes up blank. Edit this one, then run the builder:

```
python scripts/build_pharma_report.py
```

The report has two tabs. **Findings** carries the conclusions and the three
comparison charts. **Appendix & method** carries everything that qualifies
them — how much weight each market's data can bear, the markets that are
absent and why, the limitations, and the method.

## What runs on its own

`.github/workflows/pharma-prices.yml` scrapes daily at 13:37 UTC, checks the
new rows for parse artifacts, rebuilds `pharma-report.html`, and commits.
Nothing needs a secret: FX rates are pulled from the already-published copy
at `namikakmandev.github.io/rates.json`.

Run it by hand from the Actions tab (`workflow_dispatch`) at any time.

## Scripts

| script | what it does |
|---|---|
| `fetch_pharma_prices.py` | the daily scraper — venue roster, per-platform extractors. `MODE=discover` dumps a page's real structure instead of parsing it, which is how new venues get added |
| `build_pharma_report.py` | inlines the data into `pharma-report.html` |
| `pharma_outlier_check.py` | flags prices that break from their neighbours or their own series by 2.5×; `--purge` removes them |
| `probe_wayback_coverage.py` | asks the Wayback CDX API which venues are archived at all |
| `harvest_wayback_targets.py` | reads SKU identity out of archived URLs |
| `backfill_from_candidates.py` | fetches the archived pages as declared SKUs |

## Data

`data/pharma-prices.json` is the observation store. One row per
`(date, sku, venue, pack size)` — pack size is part of the identity, without
it a 20-pack and a 100-pack from the same shop collapse into one row and the
price is nonsense.

Every row is a **published asking price**, not a transaction. No row here is
evidence that a dog was treated at that price. The appendix grades each
market on how much its prices can bear.
