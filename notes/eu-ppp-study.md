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
| 2 | `MODE=discover` via fetch-data.yml on this branch → real `na_item` + `ppp_cat` codes | DONE 2026-08-19 (dump in data/_fetch-report.json) |
| 3 | Pin codes: `PLI_EU27_2020` + `PPP_EU27_2020`; ppp_cat GDP, A01, E011, A0101, A01010102 (meat), A0106 (health), A010603 (hospital), A0107, A0111, A0112, P0201 | DONE |
| 4 | Full fetch → `data/eu-ppp.json` (404 KB) | DONE 2026-08-19 |
| 5 | Sanity: EU27 PLI = 100 every year/category ✓; PLI = PPP ÷ fx × 100 exact for TR/PL/CZ 2024 vs `fx-eur.json` ✓ | DONE |

What the fetched data actually contains (verified, not assumed):

- **50 geos with a 2024 GDP PLI** — EU-27, EFTA, UK, candidates incl. TR,
  Western Balkans, plus US and JP and the EU/EA aggregates.
- **Spans:** GDP / A01 / E011 run 1995–2024; category detail (food, meat,
  health, transport, restaurants, misc, consumer services) runs 2003–2024;
  hospital services 2006–2024. Series are continuous — no visible gap at
  the 2021/22 COICOP change in this dataset, but treat pre-2022 category
  values as back-estimates until the metadata says otherwise.
- **No veterinary or pharmaceutical category exists** (61 ppp_cat codes
  checked in the discover dump) — lowest health detail is A0106 Health /
  A010603 Hospital services. Confirms the scope boundary above.
- 2024 GDP PLI range for orientation: North Macedonia 50.7 / Türkiye 50.9
  at the bottom; Iceland 152.9 / Switzerland 160.0 at the top (EU27 = 100).

## Built output

`ppp-europe.html` — interactive explorer, listed on projects.html
(card image `assets/ppp-europe.png`). Three views from `data/eu-ppp.json`:
map + ranked bars (any category, any year), one-country category profile,
and small-multiples PLI paths per country. Diverging blue↔orange around
EU-27 = 100 (poles #4696ee / #e26b36, validated against the dark surface
with the dataviz palette checker); Kosovo dropped from the country list —
present in the dataset's geo dimension but publishes no PLI values, so the
page honestly says 37 countries.

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
