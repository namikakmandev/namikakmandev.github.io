# The Cost Series — LinkedIn captions

Two document posts, one week apart. Post 1 = notes/vet-linkedin-carousel.pdf
("The Input Ledger", 9 pages). Post 2 = notes/vet-post2-carousel.pdf (P&L anatomy).
Every figure reproducible from `data/*.json` in the repository.

---

## Post 1 — The Input Ledger (US)

Your most important price is one you don't set.

Every medicine — human or animal — starts as an active pharmaceutical
ingredient. I pulled 44 years of its US price from the statistical agencies and
looked only at the cost side. Deliberately: selling prices are list-basis and
rebate-shaped, so I measured the one side of the ledger nobody administers.

Three things the data says:

1. The ingredient is a basket — bulk antibiotics, vitamins, hormones, alkaloids —
   and its market is volatile: it moves 1.37× more month-to-month than
   finished-medicine prices. The swings in this industry live on the cost side.

2. Shocks arrive inside a single month — the largest jump was +12.4% in June
   2008, and nothing in the series gives advance warning. Procurement timing is
   a margin lever, not admin.

3. Which is why cost management in pharma is a discipline: anchor price reviews
   and purchasing to the input curve, because it moves first and hardest.

But here's the thing: the powder is not the price.

An active ingredient is one line in a P&L that also carries R&D, manufacturing,
quality and people. Next post opens the other side of the ledger: what does a
medicine's price actually pay for — and how differently do human and animal
pharma companies answer it? (Preview: one spends ~a fifth of every revenue
dollar on R&D. The other doesn't — and the difference explains a forty-year
price divergence.)

All sources on the slides — BLS series, public, every figure a change between
two named dates.

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
