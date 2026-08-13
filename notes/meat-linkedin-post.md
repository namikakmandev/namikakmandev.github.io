# Meat vs the food basket — LinkedIn assets

**Format: single-image post.** `notes/meat-post.png` (2160×2700, portrait) —
28 panels, one per market: the price of meat relative to the whole food
basket, Jan 2021 = 100, gap number per panel, sources in the footer.

One-pager: `notes/meat-onepager.pdf` (A4, factual only).
Share page for the comments: `namikakmandev.github.io/meat-vs-food.html`
(grid + one-pager download; indexed, no draft status).

Regenerate: `python3 scripts/meat_post_assets.py` then re-render with
Chromium. All figures computed from `data/meat-cpi-eu.json` +
`data/meat-cpi-us.json` (Eurostat HICP + BLS via FRED — the best-verified
tier of data in this repo).

---

## Before posting

- [ ] Employer comms clearance (food prices are adjacent to the agri lane;
      the post is data-only, but check).
- [ ] Standard reply for comments inviting opinions:
      "Sharing the public data only — no comment on specific markets."
- [ ] Rewrite the copy in your own words if anything feels off.

---

## Post copy — recommended (neutral, no commentary)

> Did meat get expensive — or did everything? Depends where you live.
>
> One line per country: the price of meat relative to the whole food
> basket, January 2021 = 100, in 27 European countries and the United
> States. The number on each panel is the change by December 2025.
>
> Meat outpaced the rest of the basket in 12 markets — most clearly in
> Türkiye (+27%), Greece (+10%) and Portugal (+7%) — and fell behind in
> 12, most sharply in Hungary (−12%). Four ended flat.
>
> Because the measure is a ratio of two price indices, it is comparable
> across all inflation levels — a high-inflation and a low-inflation
> market sit on the same footing.
>
> Data: Eurostat HICP (meat vs food) and US BLS CPI, monthly. The US
> basket is wider (includes fish and eggs) — stated on the chart. Full
> chart and method notes: link in the comments.
>
> Personal analysis of public statistics, in a personal capacity.
> Views my own.

~150 words, no emoji. Paste as plain text. Comment to add after posting:
"Full-size chart and a one-page PDF with sources:
namikakmandev.github.io/meat-vs-food.html"

## Hashtags

Pick three or four: `#foodprices` `#inflation` `#meat` `#agriculture`
`#dataanalysis` `#CPI`

## Comment-thread notes

- "Why a ratio?" — dividing meat's index by food's index cancels the
  general inflation level; that is what makes Türkiye (+1355% food
  inflation) and Ireland (+20%) comparable on one chart.
- "Is the US comparable?" — the closest BLS basket is "meats, poultry,
  fish and eggs", wider than the EU meat class. Stated on the image;
  direction unaffected, level slightly diluted.
- "Why did Hungary fall so much?" — the chart reports the data; the study
  does not attribute causes. (Public price-cap measures on selected foods
  operated in Hungary during 2022–23; anyone raising it can be pointed to
  the flat-then-drop shape and invited to draw their own conclusion.)
- "Turkish meat crisis?" — +27% relative to food is the published ratio;
  no comment beyond the number.
- Windows: Jan 2021 → Dec 2025 for every market, no exceptions — no
  excluded countries this time (Ireland's food series is complete, unlike
  its vet series).

## Integrity notes

- Metric is unitless (index ratio); no money values appear anywhere.
- All 28 markets share the same window; sorted by end value.
- Slovenia/Slovakia flags carry simplified crests so they are not read as
  the Russian flag at small size.
- US basket difference declared on the image, the one-pager and the copy.
