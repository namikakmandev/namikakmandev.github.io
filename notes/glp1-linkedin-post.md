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
> GLP-1 medicines copy the gut hormones that tell the body it has eaten. Semaglutide and tirzepatide are approved. Six more are in trials.
>
> I mapped all eight by molecule rather than by company. Three things stood out 👇
>
> 🧬 One receptor became four. The first medicines hit GLP-1 alone. Newer ones add GIP, amylin or glucagon — more effect, not just more dose.
>
> 💊 The next contest is oral. One approved peptide is now a tablet. A small molecule sits in Phase 3 behind it, far simpler to make at scale.
>
> 🩺 It is moving past weight. One molecule is approved in liver disease; another entered Phase 3 there this month, and is in trials for alcohol use disorder.
>
> 📄 Sources on the slides: filings, company releases and regulatory announcements, as at August 2026. No trade names; cross-trial figures are not head-to-head.
>
> Personal analysis using public information. Views my own. Not medical advice.

About 150 words. The first two lines carry the hook before LinkedIn truncates;
the three icons map to slides 2, 4 and 5, so the post stands alone and the deck
supplies the evidence.

**Paste as plain text — LinkedIn has no bold in posts.** Markdown asterisks show
up literally, and the Unicode-bold trick breaks screen readers. The icons already
carry the structure, so no emphasis markup is needed.

## Post copy — short version

> 🧬 GLP-1 medicines copy the gut hormones that tell the body it has eaten.
>
> Eight molecules are in play for obesity. Two are approved. Six are in trials.
>
> Mapping them out, two things surprised me: the field began with one receptor and now targets four — GLP-1, GIP, amylin and glucagon — and the newest programmes aim at the liver and at addiction rather than at weight.
>
> 📄 Landscape by molecule, with sources, as at August 2026. No trade names.
>
> Personal analysis using public information. Views my own. Not medical advice.

**Icons:** keep to three or four. More reads as clutter, and pharma audiences
tend to be conservative. Swap 🩺 for 🫁 or drop it entirely if it feels much.

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
