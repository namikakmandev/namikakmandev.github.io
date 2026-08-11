# Vet bills vs inflation — LinkedIn assets

Deck: `notes/vet-cpi-carousel.pdf` — 6 slides, 2160×2700 (2× of 1080×1350
portrait), rendered from `notes/vet-cpi-carousel.html` by Chromium.
Single slides as PNG: `assets/vet-cpi-study/slide_01..06.png`.
Review page (private): the artifact link in the session — same content.

Regenerate: `python3 scripts/vetcpi_carousel_html.py` then re-render; every
figure is computed from `data/vet-cpi-eu.json` + `data/vet-cpi-us.json`, so
the deck cannot contradict the data.

Upload as a LinkedIn **document post**. Suggested title above the deck:
*Your vet bill beat inflation. Or did it?*

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy below in your own words if anything feels off.
- [ ] Consumer pet-care prices only — if a comment steers toward farm/livestock
      vet costs, that is a different dataset (spend, not prices); don't blend
      the two in replies.

---

## Post copy — recommended

> Your vet bill beat inflation. Or did it? Depends entirely on where you live.
>
> I compared the price of veterinary and pet services with overall inflation
> in 19 European countries and the US, 2017 → 2025. One small chart per
> country, all in the deck below.
>
> 📈 Far ahead: Bulgaria (+65 points over inflation), Poland +51, Slovakia
> +50, Sweden +35, Denmark +32.
>
> 📉 Behind: in Greece, Italy, Spain and Austria, vet prices rose *less* than
> inflation.
>
> The strangest chart is Germany's: perfectly flat for years — vet fees are
> fixed by a national fee schedule from 1999 — then +24% in a single month
> when the 2022 revision landed, then flat again. Regulated prices don't
> drift. They jump.
>
> Also: the US, home of the "vet costs are exploding" story, is mid-table.
> And Türkiye publishes no vet price index at all.
>
> 📄 Eurostat HICP and BLS CPI, monthly. Scope, exclusions and sources on the
> last slide.
>
> Personal analysis of public statistics. Views my own.

~160 words. The first two lines carry the hook before LinkedIn truncates.
Paste as plain text; the icons carry the structure.

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
