# The Cost Series — LinkedIn captions

Two document posts, one week apart. Post 1 = notes/vet-linkedin-carousel.pdf
("The Input Ledger", 9 pages). Post 2 = notes/vet-post2-carousel.pdf (P&L anatomy).
Every figure reproducible from `data/*.json` in the repository.

---

## Post 1 — The Input Ledger

Your most important price is one you don't set.

Every medicine — human or animal — starts as an active pharmaceutical ingredient.
I pulled 44 years of its price from the US statistical agencies, and 16 years of
Türkiye's imported-input price, and looked only at the cost side. Deliberately:
selling prices are shaped by regulators, reference systems and rebates in every
market, so I measured the one side of the ledger nobody administers.

Three things the data says:

1. The ingredient market is volatile — it moves 1.37× more month-to-month than
   finished-medicine prices. The swings in this industry live on the cost side.

2. In Türkiye, 68% of a currency move lands in the imported input cost within the
   same calendar month — and ~100% by the next. There is no warning period. A hedge
   arranged after the move is a receipt, not a hedge.

3. Which means cost management in pharma is a discipline, not an afterthought:
   procurement timing, hedging horizon and price-review cadence are decisions the
   input data can actually inform.

But here's the thing: the powder is not the price.

An active ingredient is one line in a P&L that also carries R&D, manufacturing,
quality, pharmacovigilance and people. So the next post opens the other side of
the ledger: what does a medicine's price actually pay for — and how differently do
human and animal pharma companies answer that question? (Preview: one of them
spends ~a quarter of every revenue dollar on R&D. The other doesn't — and the
difference explains a 40-year price divergence.)

All sources on the slides. Built from BLS, TÜİK and OECD series, all public,
every figure a change between two named dates.

---

## Post 2 — What a medicine's price pays for  [FILL FROM data/pharma-pnl-derived.json]

Last week: the ingredient is the cheapest part of the medicine. So what's the
expensive part?

I took the annual reports of [N] pharmaceutical companies — [human list] on the
human side, [animal list] in animal health — and read the answer straight from
their SEC filings.

[HERO NUMBERS — verify before posting:]
- Human pharma spends ~[X]% of revenue on R&D. Animal health: ~[Y]%.
- Cost of goods: human ~[A]%, animal health ~[B]%.
- Same ingredient market feeds both — the anatomy above it is what differs.

The human medicine's price buys science. The animal medicine's price buys
manufacturing. Which is exactly why (last post) veterinary prices have tracked
ingredients for forty years while human pharma repriced far above inflation —
the cost anatomy predicted the price behaviour.

Method notes: 10-K FY figures via SEC EDGAR XBRL, [3-year averages], global
consolidated (not US-only), COGS ≠ ingredient (no filer splits it), no
editorial comment on any single company.

---

## Posting notes

- Post 1's riskiest misreading ("costs fell → prices should fall") is answered by
  post 2 — keep the gap between posts short (≤1 week).
- Do not quote employer-specific figures or single out any one company's margin.
- Expected pushback on post 2: "R&D% differs because human trials are costlier" —
  that's not pushback, that IS the point; agree in comments.
