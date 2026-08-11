# Vet bills vs inflation — LinkedIn assets

**Chosen format: single-image post.** `notes/vet-cpi-grid.png` (2160×2700,
portrait) — the 20-country small-multiples grid, self-contained with legend
and source line. Upload as an ordinary image post with the copy below.

Alternative kept in repo: the 6-slide document deck
`notes/vet-cpi-carousel.pdf` (same numbers, rendered from the same HTML).

Regenerate: `python3 scripts/vetcpi_carousel_html.py` then re-render with
Chromium; every figure is computed from `data/vet-cpi-eu.json` +
`data/vet-cpi-us.json`, so the image cannot contradict the data.

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy below in your own words if anything feels off.
- [ ] Consumer pet-care prices only — if a comment steers toward farm/livestock
      vet costs, that is a different dataset (spend, not prices); don't blend
      the two in replies.

---

## Post copy — recommended (neutral, no commentary)

Chosen because some covered markets fall under the author's professional
responsibility: the post presents data only and explicitly declines
commentary. Standard reply for comments inviting opinion on a specific
market: "Sharing the public data only — no comment on specific markets."

> Veterinary and pet-service prices vs. overall inflation, 2017–2025.
> One chart per country, 20 markets.
>
> Data: Eurostat HICP (veterinary and other services for pets vs. all
> items) and US BLS CPI, monthly, both indexed to January 2017 = 100.
> The number on each panel is the difference in percentage points over
> the window.
>
> Sources and method notes are on the image; every figure is reproducible
> from the public series.
>
> Shared as data, without commentary — the charts speak for themselves.
>
> Personal analysis of public statistics, in a personal capacity.
> Views my own.

Note: the one-pager PDF contains a "What the data shows" commentary
section — keep it internal or strip that section before sharing it
anywhere public.

## Post copy — alternative (simple, corporate, with observations)

> Veterinary service prices vs. overall inflation, 2017–2025.
>
> I compared consumer prices for veterinary and pet services with headline
> inflation across 19 European countries and the United States, using
> Eurostat HICP and BLS CPI data. One chart per country; the figure is the
> gap in percentage points.
>
> Three observations:
>
> 1. The gap is widest in Central, Northern and Eastern Europe: Bulgaria
> +65 points above inflation, Poland +51, Slovakia +50, Sweden +35,
> Denmark +32.
>
> 2. In Southern Europe and Austria, veterinary prices rose more slowly
> than inflation — Greece −16, Austria −7, Spain, Italy and Portugal all
> below headline.
>
> 3. Where fees are regulated, prices move in steps, not trends. Germany's
> index was flat for years, rose 24% in one month when the revised fee
> schedule took effect in late 2022, and has been flat since.
>
> The United States sits mid-table at +4 points. Türkiye publishes no
> veterinary price index.
>
> Sources and methodology on the chart. Personal analysis of public
> statistics; views my own.

~140 words, no emoji, numbered structure. The first line states the topic
plainly. Paste as plain text.

## Hashtags

Pick three or four: `#inflation` `#pets` `#veterinary` `#dataanalysis` `#CPI` `#petcare`

## Comment-thread notes

- "Why is Germany a staircase?" — administered prices: the GOT fee ordinance
  fixes vet fees; the index only moves when the ordinance is revised
  (verified in the raw data: 112.0 flat → 154.8, then 155.3 over three years).
- "Where's Türkiye?" — TÜİK reports only all-items HICP to Eurostat; no
  vet-services class is published. Declared on the last slide.
- "US vet inflation is way higher than that" — quotes of BLS *veterinarian
  services* (SS62032) will differ; the deck uses *pet services including
  veterinary* (SS62031) because it matches Eurostat's basket (veterinary AND
  other pet services). Basket difference, not an error.
- Windows differ per slide and each slide states its own; the cross-country
  grid is Jan 2017 → Dec 2025, the longest span all 20 markets share.

## Integrity notes carried on the deck

- Ireland excluded (series ends Dec 2023); Türkiye excluded (no vet class) —
  both declared on slide 6.
- Germany +24% (Dec 2022) and Sweden +18% (Oct 2022) annotated as real
  repricings, not data breaks; no methodology break spans the window.
- Sources with dataset codes, units and spans printed on slide 6.
