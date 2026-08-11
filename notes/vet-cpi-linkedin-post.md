# Vet bills vs inflation — LinkedIn assets

Deck: `notes/vet-cpi-carousel.pdf` (6 slides, 1080×1350 portrait).
Single slides as PNG: `assets/vet-cpi-study/`.
Regenerate: `python3 scripts/vetcpi_carousel.py` — every figure recomputed from
`data/vet-cpi-eu.json` + `data/vet-cpi-us.json`, so the deck cannot contradict
the data.

Upload as a LinkedIn **document post**. Suggested title above the deck:
*Your vet bill beat inflation. Or did it?*

---

## Before posting

- [ ] Check your employer's external communications policy.
- [ ] Rewrite the copy below in your own words if anything feels off.
- [ ] Consumer pet-care prices only — if a comment steers toward farm/livestock
      vet costs, that is a different dataset (`aact_eaa01`, spend not prices);
      don't blend the two in replies.

---

## Post copy — recommended

> Your vet bill beat inflation. Or did it? Depends entirely on where you live.
>
> I compared the price of veterinary and other pet services with all-items
> inflation across 15 European countries and the US, Jan 2021 → Dec 2025.
>
> 📈 North and East: far ahead. Poland +71% vet vs +40% headline. Sweden +54%
> vs +23%. Denmark, Germany, Hungary and Czechia all 14–23 points ahead.
>
> 📉 South: behind. In Italy, Spain, Portugal and Austria vet prices rose
> *less* than inflation.
>
> 🇺🇸 And the US — home of the "vet costs are exploding" story — is mid-table:
> +28% vs +24%.
>
> The most striking chart is Germany's: a flat line for two years (vet fees are
> set by a national schedule last revised in 1999), then +24% in a single month
> when the new schedule landed in late 2022. Regulated prices don't drift —
> they jump.
>
> 📄 Eurostat HICP (CP0935 vs CP00) and BLS CPI, monthly. Scope, exclusions
> and known steps on the last slide.
>
> Personal analysis of public statistics. Views my own.

~150 words. First two lines carry the hook before truncation.
Paste as plain text; the icons carry the structure.

## Hashtags

Pick three or four: `#inflation` `#pets` `#veterinary` `#dataanalysis` `#CPI` `#petcare`

## Integrity notes carried on the deck

- Common window Jan 2021 → Dec 2025 for every market; the US decade slide is
  labelled with its own window.
- Ireland excluded (series ends Dec 2023); Türkiye excluded (no vet class in
  Eurostat HICP) — both declared on slide 6, not silently dropped.
- Germany's +24% (Dec 2022) and Sweden's +18% (Oct 2022) are real repricings,
  annotated on slide 3; no methodology break spans the window.
- US series is "pet services including veterinary" (SS62031) — the
  like-for-like match to HICP CP0935, which also covers vet *and other* pet
  services. Veterinarian-services-only (SS62032) is not on FRED; if quoted in
  comments, numbers will differ — that's the basket, not an error.
