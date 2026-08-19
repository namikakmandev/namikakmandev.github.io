# European price levels (PPP) — study plan (draft, under construction)

Proposed output: **how expensive is each European country, really** — price
level indices (PLIs) for all 36 countries Eurostat covers (EU-27 + EFTA +
candidates, Türkiye included), for GDP, household consumption and a handful
of published product/service categories.

**Scope boundary: this study is PPP/price levels only.** The veterinary /
distributor markup question is a separate work item with its own note
(`notes/vet-markup-study.md`) and its own evidence base. The two are
assessed independently — no combined metric, no joint chart, because they
measure different objects (an economy-wide price level vs. a channel margin)
and joining them would imply a relationship the data cannot show.

## Why this scope

PPPs are the one dataset designed for cross-country *level* comparison —
unlike the HICP series already in the repo (vet-cpi, food-cpi, meat-cpi),
which compare *inflation paths* and say nothing about which country is
dearer. Eurostat publishes PPPs and PLIs for 36 countries, annually, and —
unusually for this repo's markets — **Türkiye is in the dataset** (candidate
country), so no separate TurkStat hunt is needed for this one.

Known limits, written down now:

- **No veterinary category.** Published PLI detail stops at aggregate groups
  (health, food, restaurants…). There is no "veterinary services" PLI;
  nobody publishes one. This study does not claim vet-price levels.
- **COICOP 2018 break.** PPP detail for 2022–2025 is on the new
  classification; earlier years were back-estimated only for GDP main
  aggregates. Category-level series must not be spliced across 2021/22.
- **PLI ≠ cost of living ranking for households.** PLIs compare price levels
  for a common basket at market exchange rates; say that, not more.

## Data plan (discover-first, all fetching in Actions)

| Step | What | Status |
|---|---|---|
| 1 | `eu-ppp` entry in data-sources.json (`prc_ppp_ind`, one-year filter) | DONE |
| 2 | `MODE=discover` via fetch-data.yml on this branch → real `na_item` + `ppp_cat` codes | RUNNING |
| 3 | Pin codes: PLI + PPP indicators; GDP, actual individual consumption, and the published category list worth keeping (health, food, services groups) | after discover |
| 4 | Widen `time` (full span per classification regime, respecting the 2021/22 break) and fetch for real | after 3 |
| 5 | Sanity: EU27 PLI ≈ 100 by construction; PLI = PPP ÷ exchange rate × 100 spot-check for 2–3 countries against `fx-eur` data | after 4 |

The one-year `time=2024` filter in the committed entry exists only to keep
the discovery request under the API size cap — the full dataset
(37 geo × ~50 categories × several indicators × 30 years) would blow it.

## Integrity checklist for this study

- [ ] Indicator named on every figure: PLI (EU27_2020 = 100), year stated
- [ ] Candidate-country data (TR, RS, …) flagged if Eurostat marks it
      provisional/estimated
- [ ] No category series crossing the 2021/22 COICOP break without a visible
      gap or annotation
- [ ] No "cheapest country for X" claim below the published category level
- [ ] Cross-check one country's PLI against the Eurostat Statistics
      Explained article before publishing anything

## Posting posture

Neutral economic data, no employer-sensitive market commentary expected —
but same discipline as prior posts: data only, source line on every image.
