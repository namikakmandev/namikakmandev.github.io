---
name: data-availability
description: Checks whether the public data needed for a proposed study actually exists, and at what quality, BEFORE any analysis or design work starts. Use when someone proposes a new study, asks "can we analyse X?", "is there data on Y?", "what should we look at next?", or wants to extend an existing analysis to a new country, sector or variable.
---

# Is the data there? Check before building.

The expensive failure is not a wrong answer. It is two days of design work on a study
whose key variable does not exist for one of the markets. Answer feasibility first, in
writing, before anything is built.

## The environment

**This sandbox cannot reach FRED, Eurostat, USDA, BLS, NASS or FAO — the egress proxy
returns 403.** Do not conclude a source is unavailable because a local `curl` failed.
All fetching runs in GitHub Actions via `scripts/fetch.py` and `data-sources.json`.

Discovery pass first, always:

```
MODE=discover python scripts/fetch.py NAME
```

It dumps the source's real column names, dimension ids and category codes. Write the
parser against that output, never against what the API docs imply. Three parsers were
written blind and all three silently returned zero rows: OWID uses lowercase `entity`,
Eurostat's item dimension is `am_item` not `itm_newa`, and a `month=M12` filter
returned an empty dimension rather than an error.

## Providers already proven to work from Actions

| Provider | Covers | Notes |
|---|---|---|
| **FRED** | any US economic series, plus euro-area HICP | keyless CSV, most reliable |
| **Eurostat** | any dataset, EU members + EU aggregates | JSON-stat; run discovery for dimension names |
| **FAOSTAT via OWID** | any country, any agricultural commodity, 1961→ | annual only; best cross-country coverage |
| **USDA ERS** | commodity costs and returns, incl. per-head cost lines | file URLs change; scrape the product page for links |

**Türkiye is the usual gap — but check which Eurostat dataset before saying so.**
Probed July 2026, and the blanket version of this rule was wrong:

| Eurostat dataset | Türkiye? |
|---|---|
| `apro_mt_lscatl` livestock survey | **YES** — dairy cows 2012–2025, and 2025 lands before FAOSTAT's 2024 |
| `apro_mt_pann` slaughter/trade | filter accepted, **zero values** |
| `aact_eaa01` economic accounts | **no** — confirms the original rule, for this dataset only |

So Türkiye has *head counts* in Eurostat and no *money* accounts. TurkStat and
CBRT/EVDS have their own series; EVDS needs an API key (already a repo secret).
The EVDS agriculture catalogue holds an input price index — `TP.TARIMGFE.GK378650496`
veterinary expenses, `…499` concentrated feed — but those are **price indexes, not
spend**, and no foreign-trade series appears anywhere in that catalogue.

**A dimension catalogue is not data.** `MODE=discover` on a Eurostat dataset lists
every category the *dataset* has, including geos with nothing in them. Two probes
looked like TR coverage in discovery and returned zero rows on a real fetch. Confirm
availability with a real fetch and a row count, never with the catalogue alone.

**HTTP 413 from Eurostat is a query-size limit, not an absence.** An unfiltered
`aact_eaa01` probe returned 413; the same query with one `am_item` succeeded.

## What to report back

Before agreeing to a study, produce this. It takes minutes and prevents days.

1. **The variable, per market.** Name the exact series or dataset for each market. If
   one is missing, say so plainly — do not assume a proxy will turn up.
2. **Coverage.** First year, last year, number of observations, per market.
3. **Frequency.** Monthly, quarterly or annual — and whether that is enough for the
   claim. Annual data cannot support a lag measured in months.
4. **Comparability.** Are the series measuring the same object? A farm-gate price, an
   abattoir quotation and a factory-gate processed-meat index are three different
   things, even if all three are called "meat prices".
5. **Known breaks.** Survey redesigns, base-year changes, definitional changes.
6. **The honest scope.** If the data supports two of three markets, say the study is a
   two-market study. Do not quietly drop the third and keep the original title.

## Judging whether it is worth doing

- **Is the answer already known?** A study that can only confirm the obvious is a
  confirmation exercise, not research. Prefer questions whose answer you cannot
  predict — those are the ones worth the effort.
- **Is the key variable measured, or only proxied?** A proxy is fine if the limitation
  travels with every number derived from it. Write that limitation down now, not later.
- **Does the conclusion need a link the data cannot show?** If the commercial argument
  requires "X causes Y" and the data only shows X and Y separately, that gap is the
  study — state it as the open question rather than papering over it.

## Output shape

```
FEASIBLE / PARTIAL / NOT FEASIBLE

Variable:      <what is actually being measured>
US:            <source> · <span> · <frequency>
EU:            <source> · <span> · <frequency>
TR:            <source or NOT AVAILABLE>
Comparability: <are these the same object? what differs?>
Breaks:        <known discontinuities>
Honest scope:  <what the study can truthfully claim>
Missing:       <what would have to be assumed or dropped>
```
