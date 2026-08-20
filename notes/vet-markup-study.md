# Veterinary / distributor markups in Europe — study plan (draft, under construction)

Proposed output: **what is publicly known about markups in the veterinary
medicines channel, country by country** — who is allowed to dispense, where
margins have actually been measured, and where nothing is published.

**Scope boundary: this is a separate work item from the PPP study**
(`notes/eu-ppp-study.md`). The two are assessed independently — no combined
metric. A country's general price level and its vet-channel markup are
different objects; nothing here gets divided or multiplied by a PLI.

## The honest starting point

There is **no public dataset of veterinarian or distributor markups by
country**. Vet-medicine prices and margins are unregulated in most of
Europe (Regulation (EU) 2019/6 harmonises authorisation and distribution,
not prices), so no PPRI-style database exists for them. Any "markup per
country" table would be fabricated. What CAN be built honestly:

1. **A dispensing-rights map (all 36 countries).** Who may sell veterinary
   medicines — vet, pharmacy, both, differs per country and per category
   (POM vs OTC, food-producing vs companion animals). This is documentable
   from legislation and FVE overviews, and it is the single biggest reason
   "vet markup" is not one comparable object across countries.
2. **Measured-margin case studies (few countries, non-comparable).**
   Presented as boxes, never as a league table.
3. **The gap itself as the finding**: no European body measures veterinary
   distribution margins; the UK needed a two-year market investigation to
   produce one country's numbers.

## What exists publicly (evidence inventory)

| Source | Covers | What it actually contains | Status |
|---|---|---|---|
| UK CMA vet services market investigation, final report Mar 2026 + remedies (by Sep 2026) | UK | the only deep public margin evidence: practice medicine margins, margin squeeze on independents, £21 prescription-fee cap | TO EXTRACT — pin every figure to a report paragraph |
| FVE VETsurvey 2015 / 2018 / 2023 | ~24 FVE member countries | profession income and financial indicators — NOT medicine markups; useful context only | TO EXTRACT |
| WHO PPRI / GÖG Pharma Price Information | ~30 countries | regulated wholesale + pharmacy markups for HUMAN medicines only | PROXY ONLY — usable solely where pharmacies dispense vet meds, limitation must travel with every number |
| France: wholesale market sizing (~€1.57bn, 2022); purchasing-group discounts reported at 30–50% off list | FR | distributor-layer fragments, not a measured markup | TO VERIFY against primary source before use |
| National legislation / FVE dispensing-rights overviews | all 36 | who may dispense, per country | TO COMPILE — this is the map in deliverable 1 |

Rows marked TO VERIFY/TO EXTRACT carry **no numbers into any chart** until
pinned to a primary source with page/paragraph reference.

## Structural context datasets (fetched and verified 2026-08-20)

Committed via the standard pipeline — industry structure, not markups; they
size the channel, they do not measure a margin:

- **`data/eu-vet-sbs.json`** — Eurostat SBS, veterinary activities (NACE
  M75): enterprises, turnover, value added, persons employed, turnover per
  person, 39 geos, **2005–2020**. Legacy SBS series ends 2020; 2021+ needs
  the successor EBS dataset (open hunt). Sanity: DE 2020 = 10,652
  enterprises, €4.66bn turnover, 55,349 employed; EU-27 = 80,000
  enterprises.
- **`data/eu-vet-weight.json`** — HICP item weights CP0934 (pets and
  related products) + CP0935 (veterinary and other services for pets),
  per-mille of the consumption basket, 43 geos, **1996–2025**. 2025 vet+pet
  services weight: FR 5.49‰ (highest), EU-27 2.88‰, DE 2.61‰. **Türkiye
  transmits no CP0934/CP0935 weight at all** — a real gap, not an
  oversight. No 2026 in the dataset yet (ECOICOP2 rebase; successor to
  watch).

## Dispensing-rights map — fill rules

- One row per country; columns: may vets dispense? may pharmacies? online
  sale allowed? source (law or FVE doc + year).
- Every cell sourced or left blank — a blank cell is a finding ("not
  documented"), a guessed cell is a fabrication.
- No row is prefilled here: as of this draft the table has zero entries,
  by design.

## Integrity checklist for this study

- [ ] No cross-country markup comparison chart, ever — case-study boxes only
- [ ] Every margin figure pinned to report + paragraph/page
- [ ] PPRI numbers labelled "human medicines" wherever they appear
- [ ] Dispensing map: each cell carries its own source and year
- [ ] The word "markup" defined once (on what base price, which channel
      stage) and used consistently
- [ ] No blending with the PPP study or the vet-CPI series

## Posting posture

**Higher sensitivity than vet-CPI.** A markup study points at named market
participants (distributors, corporate vet groups) far more directly than a
price-index post. Decide with employer comms whether the case-study boxes
are postable at all before drafting any public asset; the dispensing-rights
map alone is the low-risk publishable core.
