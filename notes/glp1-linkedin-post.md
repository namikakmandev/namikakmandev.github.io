# GLP-1 — LinkedIn assets

Two decks exist. **Only A is intended for LinkedIn.**

| | File | Content | Status |
|---|---|---|---|
| **A** | `notes/glp1-molecules-carousel.pdf` | Molecule landscape — receptor targets, stage, indication. No share prices, no company names, no trade names. | **publish** |
| **B** | `notes/glp1-carousel.pdf` | Markets study — returns, valuation multiples, the one-stock finding. Molecule-led, companies as data attribution. | in repo, **not** for posting |

Regenerate: `python3 scripts/glp1_molecules_carousel.py` · `python3 scripts/glp1_carousel.py`
Single slides as PNG: `assets/glp1-study/molecules/` and `assets/glp1-study/carousel/`

---

## Before posting

- [ ] **Check your employer's external communications policy.** The decisive step, and the one nobody else can do for you.
- [ ] Confirm you are content with the personal-capacity wording below, in your own words rather than mine.
- [ ] A links only to `namikakmandev.github.io` (the site root), not to the markets study. Note the site itself does host that study, which names companies and shows share prices — reachable in two clicks if someone goes looking.

---

## How to upload

LinkedIn carousels are **document posts**. Create post → the document icon → upload the PDF → give it a title.

- The **title you type on upload appears above the deck.** Make it the hook, not "carousel". Suggested: *Eight molecules are chasing obesity. Two have arrived.*
- Slide 1 is the feed thumbnail. It has to earn the tap on its own.
- Keep the PDF as-is at 1080×1350 — portrait takes the most vertical space in the feed.

---

## Post copy — recommended

> Eight molecules are chasing the obesity market. Two have arrived.
>
> GLP-1 medicines copy the gut hormones that tell the body it has eaten. Semaglutide and tirzepatide are approved. Six more are still in trials.
>
> I mapped the landscape by molecule rather than by company — what each one targets, how far it has got, and which disease it is aimed at.
>
> Three things stood out.
>
> **The field started with one receptor and now targets four.** The first medicines hit GLP-1 alone. Newer ones pair it with GIP, amylin or glucagon — adding effects rather than simply dosing harder.
>
> **The next contest is oral.** One approved peptide now comes as a tablet. A small molecule is in Phase 3 behind it, and small molecules are far simpler to manufacture at the scale this demand implies.
>
> **The biology is spreading past weight.** One molecule is already approved in liver disease. Another entered Phase 3 there this month, and is in trials for alcohol use disorder — the same receptor family reaching into addiction.
>
> Receptor targets, stages and approvals are on the slides, with sources: company filings, company releases and regulatory announcements, as at August 2026. No trade names, and cross-trial figures are not head-to-head.
>
> Personal analysis using public information. Views my own. Not medical advice.

**Why this shape:** the first two lines carry the hook before LinkedIn truncates. The three bolded points map to slides 2, 4 and 5, so someone who reads only the post still gets the substance, and someone who swipes gets the evidence.

## Post copy — shorter alternative

> GLP-1 medicines copy the gut hormones that tell the body it has eaten.
>
> Eight molecules are in play. Two are approved. Six are in trials.
>
> What surprised me mapping them out: the field began by targeting one receptor and now targets four — GLP-1, GIP, amylin and glucagon — and the newest programmes are aimed at the liver and at addiction rather than at weight.
>
> Landscape by molecule, with sources, as at August 2026. No trade names.
>
> Personal analysis using public information. Views my own. Not medical advice.

## Post copy — question opener

> Which is harder: finding a molecule that works, or making it into a tablet?
>
> Eight GLP-1 molecules are in play for obesity. Two are approved. The interesting contest now is formulation, not efficacy — one approved peptide has reached tablet form, and a small molecule is in Phase 3 behind it, far simpler to manufacture at scale.
>
> I mapped all eight by receptor target, stage and indication. Sources on the slides, as at August 2026.
>
> Personal analysis using public information. Views my own. Not medical advice.

---

## Hashtags

Pick three or four, not ten: `#GLP1` `#obesity` `#drugdevelopment` `#pharma` `#MASH` `#clinicaltrials`

---

## Slide map — deck A

| # | Slide | Point |
|---|-------|-------|
| 1 | Eight molecules. Two have arrived. | Plain-language opener, unit bar by stage, 587% prescription growth |
| 2 | One target became four. | Receptor matrix: molecule × GLP-1 / GIP / amylin / glucagon |
| 3 | Two on the market. Six behind them. | Pipeline positioned Phase 1 → Approved |
| 4 | The next contest is oral. | Weight-loss bars for the two oral candidates, with cross-trial caveat |
| 5 | The same biology is moving into the liver. | Indication map: obesity / liver disease / alcohol use disorder |
| 6 | What this covers. | Scope, sources, limitations |

## Integrity notes carried on the deck

- Slide 4's bars are **not head-to-head** — different trials, populations and durations. Stated on the slide.
- All counts derive from the molecule table in the script, so a headline cannot contradict the data.
- Molecule names appear only where a filing or company release confirms them.
- Stages are as at August 2026 and change; several readouts are due.

## If someone asks about the markets angle in the comments

Deck B exists and is in the repo. It is not posted, and the two questions are separate: A is about the science, B is about share prices. Answering market questions under a science post pulls you into exactly the territory A was built to avoid.
