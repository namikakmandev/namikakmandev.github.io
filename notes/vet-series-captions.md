# The Cost Series — LinkedIn captions

Two document posts, one week apart. Post 1 = notes/vet-linkedin-carousel.pdf
("The Input Ledger", 9 pages). Post 2 = notes/vet-post2-carousel.pdf (P&L anatomy).
Every figure reproducible from `data/*.json` in the repository.

---

## Post 1 — The Input Ledger (US)

**Use this one.** The hook is the first three lines — LinkedIn cuts the post at
"…see more" around there, so the paradox has to land before the fold.

---

The active ingredient in a US medicine costs 89% more than it did in 1982.

It is also 45% cheaper.

Both numbers are correct. The gap between them is inflation — and it is the
reason almost nobody in this industry can tell you what their most important
input actually costs.

Every medicine, human or animal, starts as an active pharmaceutical ingredient.
I pulled 44 years of its US price from the statistical agencies, deflated it,
and looked only at the cost side. Deliberately: selling prices are list-basis
and rebate-shaped, so I measured the one side of the ledger nobody administers.

Three things the data says:

1. The ingredient is a basket — bulk antibiotics, vitamins, hormones, alkaloids —
   and its market is volatile: it moves 1.37× more month-to-month than
   finished-medicine prices. The swings in this industry live on the cost side.

2. Shocks arrive inside a single month — the largest jump was +12.4% in June
   2008, and nothing in the series gives advance warning. Procurement timing is
   a margin lever, not admin.

3. Which is why cost management in pharma is a discipline: anchor price reviews
   and purchasing to the input curve, because it moves first and hardest.

**But the powder is not the price.**

An active ingredient is one line in a P&L that also carries research, plants,
quality and people — and the two halves of this industry fill that line in
opposite directions. One of them spends about a fifth of every revenue dollar on
R&D. The other spends nearly half of it on making the thing.

Part 2 reads that split straight from eight companies' own SEC filings, human
pharma and animal health side by side, same method as this one. It is also the
honest answer to the obvious objection to this post — *if the input got cheaper,
why didn't the medicine?*

Before then: which of the two is the R&D-heavy one, and by how much? The
multiple surprised me. I'll put it on slide 4.

All sources on the slides — BLS series codes, public, every figure a change
between two named dates.

---

### Alternate hooks (swap the first three lines only)

**A — the paradox** *(recommended, used above)*
> The active ingredient in a US medicine costs 89% more than it did in 1982.
> It is also 45% cheaper.
> Both numbers are correct. The gap between them is inflation.

Why it works: two "facts" that can't both be true, resolved in the third line.
It also frames the post as a method post rather than a pricing post, which is
the safer read.

**B — the positional hook**
> Your most important price is one you don't set.
> Every medicine — human or animal — begins as a powder bought on a world
> market, and that market moves 1.37× harder than the medicine it becomes.

Why it works: speaks directly to anyone in procurement, finance or commercial.
Weaker on curiosity, stronger on "this is for me."

**C — the shock hook**
> In one month — June 2008 — the price of pharmaceutical active ingredients
> jumped 12.4%.
> Forty-four years of monthly data contain no warning that it was coming.
> I went looking for one anyway. Here is what the series will and won't tell you.

Why it works: concrete date, concrete number, honest negative result. Best if
you want the comments to be about forecasting and procurement timing.

**D — the definitional hook**
> There is no such thing as "the price of the active ingredient."
> There is a basket — antibiotics, vitamins, hormones, alkaloids — and the
> basket has moved in the opposite direction to the medicines made from it for
> four decades.

Why it works: corrects an assumption most readers hold. Slightly slower burn.

---

### Alternate harbingers (swap the closing block only)

**1 — the objection-killer** *(recommended, used above)*
Names the misreading out loud ("if the input got cheaper, why didn't the
medicine?") and promises the answer next week. This is the version that protects
you: it tells the reader the post is incomplete on purpose, so nobody finishes
post 1 with "costs fell, prices didn't" as the takeaway.

**2 — the question**
> Part 2, in a few days: what does a medicine's price actually pay for?
> I read it off eight companies' 10-Ks. Human pharma puts roughly a fifth of
> every revenue dollar into R&D. Animal health puts a third of that.
> The 2.7× gap is not a footnote — it is the reason the two sides have priced
> in opposite directions for twenty years.
> If you benchmark an animal-health company against human-pharma norms, you are
> comparing different animals. I'll show the arithmetic.

**3 — the one-liner** *(if the caption is running long)*
> Next: the powder is not the price. Eight 10-Ks, human pharma vs animal health,
> and what $100 of revenue actually buys. One side spends a fifth of it on
> science. The other doesn't — and that is the whole divergence.

Rule for all three: tease the *ratio*, never a single company's margin.

---

## Post 2 — What a medicine's price pays for

Last week: the ingredient is the cheapest part of the medicine. So what's the
expensive part?

I read the answer straight from eight companies' SEC filings — Pfizer, Lilly,
AbbVie and Bristol Myers Squibb on the human side; Zoetis, Elanco and Phibro in
animal health (Merck shown separately: ~9% of it is animal health, so it pools
with neither group). FY2023–25 averages, medians per group.

The anatomy of $100 of revenue:

- R&D: human pharma 19.4 — animal health 7.3. A 2.7× gap.
- Cost of goods: human 29.6 — animal health 44.6. Inverted.
- What remains after COGS+R&D+SG&A: ~30 vs ~23. Similar discipline,
  opposite routes to it.

The human medicine's price buys science. The animal medicine's price buys
manufacturing. And that explains last week's chart: an R&D-built P&L must
reprice to fund the next molecule (human prices +75% real over the clean
20-year window) — a manufacturing-built P&L tracks its inputs (veterinary
prices −4% real, same window, BLS's own veterinary index).

If you benchmark an animal-health company against human-pharma norms, you're
comparing different animals.

Method: SEC EDGAR XBRL, 10-K FY values, global consolidated (not US-only),
COGS ≠ ingredient (no filer splits it), concept tags recorded per company,
every figure recomputed from committed data. Small samples — 4 and 3 filers —
medians, and stated.

## Posting notes

- Post 1's riskiest misreading ("costs fell → prices should fall") is answered by
  post 2 — keep the gap between posts short (≤1 week).
- Do not quote employer-specific figures or single out any one company's margin.
- Expected pushback on post 2: "R&D% differs because human trials are costlier" —
  that's not pushback, that IS the point; agree in comments.
