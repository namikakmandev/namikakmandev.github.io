# LinkedIn post — Vet Spend Index, Europe 2015→2025

Companion graphic: `vet-spend-index.html` (open the page, screenshot the dark card —
it is sized for LinkedIn's 4:5 portrait format).

Format modeled on the "iPhone Price Index 2026" post (Visual Capitalist repost):
question hook → ranked flag list → one twist the chart doesn't show at first glance →
discussion prompt → source line → hashtags.

---

## Post copy (EN)

📉 Europe spends €7.3B a year on farm animal health. In real terms, that is *less* than a decade ago.

Same industry, same decade — opposite directions.

🔵 Fastest real growth in veterinary spending, 2015→2025 (inflation-adjusted):

🇨🇿 Czechia: +66%
🇵🇹 Portugal: +63%
🇭🇺 Hungary: +47%
🇵🇱 Poland: +39%

🔴 In real decline:

🇩🇪 Germany: −4%
🇪🇸 Spain: −5%
🇫🇷 France: −24%
🇷🇴 Romania: −33%

🇪🇺 EU-27 total: +22% nominal — but −5% after inflation.

The headline number hides the real story. Cumulative euro-area inflation (+29%) ate the entire nominal increase in the EU's largest Western markets, while Central & Eastern Europe outran it by 40–65 points.

For animal-health strategy that split matters: in Western Europe the game is price and mix. The volume growth story has moved East.

What's behind it? Herd consolidation in the West, intensification and price catch-up in CEE are the usual suspects — but I'd genuinely like to hear how colleagues in these markets read it.

Source: Eurostat, Economic Accounts for Agriculture (aact_eaa01, "Veterinary expenses", € million at current prices, all livestock), deflated by euro-area HICP. UK excluded (series ends 2020).

#AnimalHealth #VetMed #Livestock #Pricing #Europe #CEE #AgEconomics #Inflation #Data #Strategy

---

## Why this concept (vs alternatives considered)

1. **Vet Spend Index (chosen)** — squarely in the author's professional realm
   (animal-health pricing, CEEME); single Eurostat dataset already in this repo,
   so every figure is reproducible; East–West divergence gives it the same
   "same thing, wildly different by country" hook as the iPhone post.
2. **Cattle parity (kg feed per kg cattle, TR/EU/US)** — signature study
   (`parite-sigir`), strong material, but index-based: absolute cross-country
   levels are not comparable (base-year trap), so it fits a thread/series better
   than a single ranked-bar graphic. Good candidate for post #2.
3. **Beef price index by country (literal iPhone clone)** — needs retail beef
   prices per country from a new source; data not in repo, availability and
   comparability unverified. Skipped.

## Integrity notes (checked before publishing)

- Real change computed as EUR current-price series ÷ euro-area HICP annual mean
  (FRED CP0000EZ19M086NEST); 2015 HICP 77.71 → 2025 100.00 (+28.7%).
- Percent changes are ratios between two dates — base-year invariant. No
  cross-country *level* comparison is made (levels shown only as each country's
  own € million, not per animal).
- No per-animal normalization: the expense series covers ALL livestock while the
  repo's herd series is cattle-only — dividing them would fabricate a number.
- UK series ends 2020 → excluded and declared on the artifact.
- FX caveat declared: values are EUR-converted, so non-euro countries' figures
  include exchange-rate effects.
- Sources, deflator, exclusions and repro files are printed on the graphic itself.

## Numbers (from data/eu-vet-countries.json + data/eu-hicp.json, cut-off Aug 2026)

| Country | 2015 €M | 2025 €M | Nominal | Real (HICP-defl.) |
|---|---|---|---|---|
| CZ | 111 | 237 | +113.0% | +65.6% |
| PT | 35 | 73 | +110.3% | +63.4% |
| HU | 68 | 129 | +89.0% | +46.9% |
| PL | 108 | 194 | +79.0% | +39.1% |
| IE | 269 | 412 | +53.2% | +19.0% |
| AT | 121 | 185 | +52.5% | +18.5% |
| NL | 381 | 544 | +42.8% | +11.0% |
| BE | 228 | 323 | +41.5% | +10.0% |
| IT | 737 | 968 | +31.3% | +2.0% |
| DE | 925 | 1,139 | +23.1% | −4.3% |
| ES | 571 | 699 | +22.3% | −4.9% |
| FR | 1,455 | 1,434 | −1.5% | −23.5% |
| RO | 329 | 285 | −13.3% | −32.6% |
| EU-27 | 5,960 | 7,277 | +22.1% | −5.1% |
