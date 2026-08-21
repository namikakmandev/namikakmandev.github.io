# Broiler parity, four markets: Türkiye · Poland · Egypt · Saudi Arabia

Feasibility + design note, following `.claude/skills/data-availability`.
The ask: one profitability KPI per market, ~10 years. Annual frequency was
accepted by the owner, which changes the verdict from the monthly case.

## Route

- FAOSTAT Producer Prices (PP), **bulk zip** — the API returns 401 from
  Actions (`data/_me-parity-probe.json`), the bulk service returns 200.
- `scripts/fetch_broiler_annual.py` + `.github/workflows/broiler-annual.yml`.
  Writes `data/broiler-annual.json` (series + KPI) and
  `data/_broiler-annual-report.json` (everything found, chosen, rejected).
- National monthly routes remain what the cattle probe established: TÜİK is
  live (see `broiler-margin.html`), Poland could go monthly via the EC
  agrifood API, CAPMAS is PDF-only, GASTAT machine endpoints are dead.

## The KPI, and whether it is objective

Parity = chicken-meat producer price ÷ feed-grain producer price, both
farm-gate, both LCU/tonne, one FAO methodology for all four countries.

**Within a country over time it is objective** — same object, same source,
both sides in the same currency, so devaluations don't move it mechanically.
It tracks the margin squeeze/repair cycle, which is what a profitability KPI
is for.

**Across countries in levels it would be misleading**, for reasons that are
economic, not statistical:

1. The denominator is one grain, not compound feed. Broiler rations are
   grain + soymeal + premix; the grain share differs by country.
2. Egypt and Saudi Arabia import most feed. A domestic grain producer price
   understates their true feed-cost swings; Saudi feed also sat under a
   changing subsidy regime (same caveat as the cattle study, carried on the
   data as a `caveat` field).
3. Integration structure, VAT treatment and farm-gate definitions differ.

So the published KPI is **`parity_idx`: parity as % of the country's own
2015–2024 mean**. 100 = that market's own normal margin; 80 = a squeeze;
120 = a fat year. That is comparable across the four in *direction and
stress*, which is the honest claim. Raw parity levels stay in the JSON for
the per-country read but must not share an unlabelled axis.

## Honest scope

- Annual data cannot carry monthly stories (the Türkiye monitor's Dec-2025
  trough, cycle timing in months). It shows decade trends and bad *years*.
- FAOSTAT lags ~2 years; this is a backdrop KPI, not a now-cast. For "where
  are we now" in Türkiye, `broiler-margin.html` remains the instrument.
- Whatever countries the fetch report excludes stay excluded — the script
  raises the exclusion into `decisions` rather than silently dropping.

## Status

Fetch wired and mock-validated (long+wide formats, feed-grain fallback
order maize→wheat→barley→sorghum, exclusion guards, caveat propagation).
First real run: see `data/_broiler-annual-report.json` on this branch.
