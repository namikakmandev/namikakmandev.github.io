# LinkedIn post — The Discount Breakeven Table

Companion graphic: `discount-breakeven.html` (open the page, screenshot the dark
card — sized for LinkedIn's 4:5 portrait format).

Chosen as the interim post while the vet-spend / livestock-economics lane is
paused pending the internal discussion: pure arithmetic, no market data, no
employer overlap — showcases pricing craft, not company material. Links back to
the interactive calculator already live on the site.

---

## Post copy (EN)

💸 A 5% discount feels small. The volume it demands is not.

Here is the math nobody runs before hitting "approve" — extra volume needed just to earn the SAME profit as before the discount (at a 30% gross margin):

▪️ 2% off → +7% volume
▪️ 5% off → +20% volume
▪️ 10% off → +50% volume
▪️ 15% off → +100% volume. Double. Just to stand still.

And it gets steeper the thinner your margin:

At a 20% margin, a 10% discount needs +100% volume. A 15% discount needs +300%. And the moment the discount reaches your margin, no volume on earth breaks even — you lose money on every extra unit you "win."

The formula is one line: required volume = discount ÷ (margin − discount). The consequences are rarely one line.

So before approving the next discount, ask a single question: where, exactly, is the extra volume coming from? If nobody can answer with a number, it's not a growth lever — it's a margin donation.

I built a small calculator to run your own numbers — link in the comments. 👇

What's the biggest discount you've seen approved without a volume answer behind it?

#Pricing #PricingStrategy #RevenueManagement #Discounting #CommercialExcellence #Margin #Sales #B2B #Strategy #Finance

**First comment (post immediately after publishing):**
🧮 The calculator: https://namikakmandev.github.io/discount-margin-calculator.html
Enter price, cost and discount — it shows your net price, remaining margin, and the exact break-even volume.

---

## Why this topic now

- The vet-spend index (`vet-spend-index.html`) is parked: it became input to an
  internal discussion, so the whole livestock-economics lane waits for the
  meeting outcome. This post is deliberately in the no-overlap zone.
- Evergreen, universally relevant to commercial audiences, and the CTA drives
  traffic to an existing tool on the author's own site.

## Integrity notes

- Formula: uplift = d/(m−d). Identical to the live calculator's
  `extraPct = (mBefore/mAfter − 1)` in `js/discount-margin-calculator.js`
  (both reduce to the same expression) — poster, post and tool agree.
- Stated assumptions on the artifact: variable-cost gross margin, break-even
  defined as same total gross profit, no fixed-cost absorption or elasticity
  effects; noted that real break-evens are usually worse (terms/rebates).
- No market data, no external sources needed; every figure reproducible from
  the printed formula.

## Numbers on the graphic (uplift = d/(m−d))

At 30% margin: 2%→+7.1% · 4%→+15.4% · 5%→+20% · 6%→+25% · 8%→+36.4% ·
10%→+50% · 12%→+66.7% · 15%→+100%

Matrix — 5% off needs: +33.3% (20% m), +20% (30% m), +14.3% (40% m), +11.1% (50% m)
10% off needs: +100%, +50%, +33.3%, +25%
15% off needs: +300%, +100%, +60%, +42.9%
