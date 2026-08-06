# GLP-1 study — LinkedIn carousel & post

**Asset:** `notes/glp1-carousel.pdf` — 10 slides, 1080×1350 (4:5 portrait).
Single slides as PNG in `assets/glp1-study/carousel/` for image posts or Twitter/X.

**Regenerate:** `python3 scripts/glp1_carousel.py`
Numbers come from `data/glp1-stocks.json` and `data/glp1-valuation.json`, so the deck
cannot drift from the study page. Basis is the **last complete month** — the newest bar
in the price file is a partial month captured mid-session.

---

## How to post it

LinkedIn carousels are **document posts**: upload the PDF directly (Create post →
document icon → upload → give it a title). LinkedIn converts it to the swipeable
card deck. HTML cannot be uploaded; PPT/DOCX would just be converted to PDF anyway.

- The **title you type on upload appears above the deck** — make it the hook, not "carousel".
- Slide 1 is the thumbnail in the feed. It has to earn the swipe on its own.
- Put the study link in the **first comment** if you want maximum reach, or in the post
  body if you care more about clicks than impressions.
- 4:5 portrait takes the most vertical space in the feed. Don't switch to square.

---

## Post copy (option A — the counterintuitive finding)

> GLP-1 drugs were the biggest thing in medicine this decade.
>
> Held equally since 2015, the six profitable GLP-1 names returned +450%, against
> +275% for the S&P 500. A clear win for the theme.
>
> Now remove Eli Lilly.
>
> The same basket returns +170% — it loses to a plain index fund.
>
> One stock carried the entire theme. And the company that *invented* the category,
> Novo Nordisk, returned +175% against the index's +275%, and sits 65% below its
> 2024 peak.
>
> Being right about the trend was not the same as making money from it.
>
> Full study, charts and open data pipeline in the comments. Not investment advice.

## Post copy (option B — the valuation angle)

> Novo Nordisk trades at 14x earnings. Eli Lilly trades at 40x.
>
> So Novo is the cheap one, right?
>
> Adjust for growth and it isn't. Consensus has Novo's earnings *falling* next year
> and compounding at 7% a year; Lilly's compound at 17%. On a PEG basis Novo is the
> **more** expensive of the two — 2.26 versus 1.92.
>
> A 14x multiple on shrinking earnings is not a discount. It's a forecast.
>
> I pulled 21 years of monthly total returns for 12 GLP-1 names, then added the
> valuation layer. What the price already assumes turned out to be the whole story.

## Post copy (option C — teaching angle, widest audience)

> A quick way to sanity-check any share price: flip the multiple upside down.
>
> Novo Nordisk at 14x earnings → 7.1% earnings yield
> Eli Lilly at 40x earnings → 2.5% earnings yield
>
> Suddenly it's comparable to a bond, or a flat you'd rent out. And the real question
> appears on its own: why accept 2.5% from Lilly?
>
> Because Lilly's earnings grow at 17% a year and Novo's are flat until 2028. That
> trade-off is what valuation actually is.
>
> I worked through it on 12 GLP-1 stocks — including why the "cheap" one is the
> expensive one.

---

## Slide map

| # | Slide | Point |
|---|-------|-------|
| 1 | One drug class, two opposite outcomes | Hook + scope |
| 2 | Same science, different decade | LLY vs NVO vs index, total return since 2015 |
| 3 | They rose together — then split | Indexed divergence chart from 2021 |
| 4 | −73% | Novo's drawdown + why losses are asymmetric |
| 5 | Same tailwind, opposite results | 1-yr dispersion inside the theme |
| 6 | One stock carried the entire theme | The finding: basket vs ex-Lilly vs index |
| 7 | The inventor lagged the market | Novo vs S&P since 2015 |
| 8 | So Novo is cheap now? | PE / growth / PEG side by side |
| 9 | Flip it upside down | Earnings yield — the teaching slide |
| 10 | What it cannot tell you | Honest limits + link |

## Notes

- Valuation figures are a manual snapshot (fundamentals via Bigdata.com), not the
  monthly cron. Re-pull before reposting if it's been a while.
- Trailing PE is GAAP; consensus forward EPS is adjusted. Stated on the study page.
- Keep "Not investment advice" in the post, not only on slide 10.
