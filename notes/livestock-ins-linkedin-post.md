# Livestock insurance — LinkedIn assets

**Format: single-image post.** `notes/livestock-ins-post.png` (2160×2700,
portrait) — two charts: Türkiye's penetration curve (TARSİM) and the US LRP
head-insured curve, product definitions on the image, sources in the footer.

One-pager: `notes/livestock-ins-onepager.pdf` (A4, factual only — KPIs,
three charts, scheme table, sources).
Full study page: `namikakmandev.github.io/livestock-insurance.html`
(currently `noindex`; remove the meta tag when cleared to publicise).

Regenerate everything: `python3 scripts/livestock_post_assets.py` then
re-render with Chromium. All figures flow from
`data/livestock-ins-tarsim.json` (page-pinned TARSİM extractions) and
`data/livestock-ins-usa.json` (RMA files, column maps from RMA's own
layout PDFs), plus `data/herd-cattle.json` denominators.

---

## Before posting — IMPORTANT

- [ ] **Employer comms clearance first.** This topic (livestock risk) is
      closer to the author's professional territory than the vet-CPI post.
      Do not post before explicit clearance.
- [ ] Standard reply for comments inviting market opinions:
      "Sharing the public data only — no comment on specific markets."
- [ ] Rewrite the copy in your own words if anything feels off.

---

## Post copy — recommended (neutral, no commentary)

> Who insures the herd? Two schemes, two continents, one pattern.
>
> Türkiye (TARSİM): the share of the national cattle herd covered by
> mortality-and-disease insurance rose from 3% in 2013 to 41% in 2024;
> 10.0 million head were insured in 2025.
>
> United States (USDA Livestock Risk Protection): cattle head covered by
> price insurance rose from 0.2 million in 2015 to 6.2 million in 2024 —
> roughly 7% of the January-1 inventory.
>
> The two products are different — one insures against death and disease,
> the other against price declines — so the series are shown side by side,
> never summed. In both countries, the take-off follows an expansion of the
> government premium subsidy, visible in the same public files.
>
> Data: TARSİM annual reports; USDA RMA livestock participation files;
> TÜİK/FAOSTAT herd figures. Method notes and the full study are linked on
> the image.
>
> Personal analysis of public statistics, in a personal capacity.
> Views my own.

~150 words, no emoji, data-only. Paste as plain text.

## Hashtags

Pick three or four: `#livestock` `#agriculture` `#insurance`
`#riskmanagement` `#dataanalysis` `#cattle`

## Comment-thread notes

- "Are these comparable?" — no, and the post says so: mortality cover vs
  price cover. Each series is compared with itself over time.
- "Why did both take off?" — the subsidy expansion timing is in the data
  (TR: ~50% premium subsidy throughout, scheme scaled with enrolment
  campaigns; US: LRP subsidy 13% of premium in 2015 → 35% in 2024).
  State the numbers, decline to editorialise beyond them.
- "What about the EU?" — Spain's scheme publishes no machine-readable
  series (insurer site blocks automation; ministry pages script-rendered);
  Germany uses compulsory public epidemic funds, which are not insurance.
  Both stated on the study page.
- "TARSİM 2025 loss ratio jumped to 77%?" — the source reports the jump;
  the study does not attribute a cause. Paid loss excludes outstanding
  claims; premiums are written, not earned.
- "US 2025 indemnities look tiny" — endorsements still settling;
  the study shows no 2025 loss ratio for that reason.

## Publication switches (when cleared)

1. Remove `<meta name="robots" content="noindex, nofollow">` from
   `livestock-insurance.html` (regenerate via scripts/livestock_ins_page.py
   after deleting the tag from the template, or edit in place).
2. Optionally add a project card to projects.html.
