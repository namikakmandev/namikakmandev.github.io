---
name: data-integrity
description: Checks whether a data finding is actually real before it gets published. Use when correlating two series, comparing values across years or countries, deriving a headline number from public statistics, or when asked "is this right?" about an analysis. Also use before putting any figure into a slide, report, film or post.
---

# Data integrity checks

Every rule below comes from a real error that shipped and had to be corrected.
Run them before a number leaves the workspace.

## 1. Is the level meaningful, or only the change?

An **index** is not a quantity. `WPU0131 / WPU012202` is the ratio of two BLS price
indexes, both based on 1982 = 100. A value of 2.44 does **not** mean "one kilo buys
2.44 kilos". It means "the relative price is 2.44× what it was in the base year".

- Test: **change the base year.** If the number moves, it was never a physical quantity.
- What survives: ratios between two dates, percent change vs a base, peak-to-trough
  coefficients. The base-year constant cancels in all of these.
- What does not: absolute levels, cross-country level comparisons, any unit like kg or $.
- If a physical figure is genuinely needed, find a source that publishes one
  (e.g. USDA NASS steer-corn price ratio: bushels of corn per 100 lb of cattle).

## 2. Deflate before correlating anything measured in money

Nominal money series trend upward because money loses value. Correlating one against
anything else that trends produces a large coefficient that means nothing.

Real example: EU vet spend per head vs herd size gave **r = −0.94 nominal**. Deflated
by HICP it was **−0.12**. The first number was two trends passing each other.

- Deflate with a stated deflator (CPI, HICP) and say which one.
- After deflating, re-run the correlation. Report the real one.
- If two series both trend, assume the correlation is spurious until detrended.

## 3. Look for methodology breaks before comparing endpoints

USDA ERS changed its cow-calf survey basis in 2008: a **−29% step** in one year that is
not economic. A 1996→2025 comparison across it is meaningless.

- Plot or print year-over-year change and look for a single implausible step.
- Check the source's own base/vintage column if it has one.
- Split the series at the break and analyse within each regime.

## 4. Publish the definition of every derived measure

If a table cannot be reproduced from the published data file, it is not a finding.

State, on the artefact itself: what counts as a peak (e.g. local maximum over a
±18-month window on the 12-month average), what a plateau is (months within 10% of that
peak), what a "fall" is measured from and to. Different reasonable definitions give
different answers — that is fine, as long as yours is written down.

## 5. Check "neutral" claims for every series, not just the convenient ones

A methodology page claimed 2016 was "a neutral base year, close to each series' own
long-run mean (EU 101, TR 104)" — and silently omitted the US, which sat at **123**.
On a full-sample base the US figure was 226, not 184.

- If you assert neutrality, compute it for **all** series and publish all of them.
- Publish the sensitivity range, including the least flattering case.

## 6. Correlation is not a lead

A peak correlation at a non-zero lag is only a lead if it is **clearly** higher than at
lag zero. TR→US was r = 0.60 at −4 months versus 0.58 at 0. That is noise, and calling
it a four-month lead was wrong.

Also ask what is driving a high correlation. US–EU parity correlated at 0.87, but US
corn vs EU feed grain alone correlated at 0.81 — most of it was the shared denominator,
not a synchronised cattle cycle.

## 7. Decompose before naming the cause

Before calling something "the cattle cycle", check which side actually moves.
Variance decomposition of the year-on-year change: **84% came from corn, 16% from
cattle.** It was a grain cycle wearing a cattle costume.

```python
var_num, var_den = pvariance(dlog(numerator)), pvariance(dlog(denominator))
cov = covariance(dlog(numerator), dlog(denominator))
share_den = (var_den - cov) / (var_num + var_den - 2*cov)
```

## 8. Small samples

Five cycles is five observations. "Every one" out of five is a pattern, not a law. Say
the sample size out loud, and say what would falsify the claim.

## 9. Name the data in the heading, not only in the footnote

A reader should never have to infer which market or which period a number covers. If a
chart is US-only, the *headline* says so — not the source line in grey capitals at the
bottom.

Real failures this rule comes from:

- A slide headed "Our customers are at their most profitable point in 55 years" sat above
  a US-only figure. Only the US has 55 years; the EU record starts in 2015. The claim was
  true for one market and unsupported for the other two.
- Two chart slides were built entirely on US data with no "US" anywhere in the title.
- "0.50 kg" and "2.44 kg" appeared with no country and no date, in a deck whose whole
  argument was about three different countries.

Apply it mechanically:

- Every headline names the market when the slide is not all markets: "**The US:** a
  record…", "Five **US** peaks…"
- Every number carries market **and** date: "US, Jun 2026", not "today"
- When the scope changes between slides, say so on the slide where it changes
  ("**Now all three** — each on its own base")
- Mark the switch from measured to modelled in the heading or the line under it

## 10. Write the sources on the artefact itself

Not in a separate file, not "available on request". Every deck, page, report or post
carries its own sources where a sceptic will look for them.

Include, for each series: **publisher, exact series or dataset code, unit, span.**
"BLS producer price indexes WPU0131 (slaughter cattle) ÷ WPU012202 (corn), via FRED,
1971→" — a reader can verify that. "Source: BLS" is not verifiable.

Alongside the sources, in the same block, list:

- **Deflators used**, named — a money figure without a stated deflator invites the question
- **Known breaks** — "ERS changed survey basis in 2008, no comparison spans it"
- **What the series does not measure** — "EU veterinary line covers all livestock, not
  cattle alone"
- **What is missing** — "no per-head cost accounts published for Türkiye". An absent
  market must be declared, never quietly dropped while the title still claims three.

Close with reproducibility: which committed data files every figure comes from, and the
data cut-off date. If a number in the artefact cannot be recomputed from a file in the
repository, it should not be in the artefact.

## 11. Land an outcome, or the work is wasted

A study that ends in findings has not finished. The reader cannot act on "parity is at a
peak" or "spend correlates at 0.70" — those are inputs. **The last thing they see must be
what to do, per market, per decision.** If nobody can act on it differently on Monday,
the analysis was an expensive way of being interesting.

The test: could the reader repeat one instruction to their own boss? If the only thing
they can repeat is a number, the ending failed.

**Findings → outcome, worked example:**

| Finding | Outcome |
|---|---|
| US spend tracks margin at r = 0.70; margin at a record | **Time the price move** — phase the increase before the plateau breaks |
| EU spend per head is flat; herd &minus;1.4%/yr | **Defend the volume** — no cycle upside or downside, the erosion is structural |
| T&uuml;rkiye herd growing, spend unmeasurable | **Grow, and get visibility** — the only market where head count adds |

Rules for the closing slide or section:

- **One instruction per market or segment**, in the imperative. Not "consider", not
  "may warrant attention".
- **Say what is different between them.** "The US is a timing problem, the EU is a volume
  problem, T&uuml;rkiye is a visibility problem" tells a reader more than three paragraphs.
- **Attach the decision to a period.** "2027 points up" beats "in the medium term".
- **Show it, do not write it.** Arrows, gauges, coloured verdict badges. If the closing
  page is prose, it will be skimmed and forgotten.
- **An honest null is still an outcome.** "Do not act on this yet, and here is the one
  thing that would change that" is a decision. Silence is not.
- **Name what would change the instruction.** An outcome with no falsifier is an opinion.

Do this even when the analysis is inconclusive. Especially then — an inconclusive study
that names the missing piece and the cost of getting it has produced a decision. One that
just stops has produced nothing.

## Before publishing, confirm

- [ ] Every number has a unit, a market and a date attached
- [ ] Money figures are deflated, and the deflator is named
- [ ] No comparison spans a known methodology break
- [ ] Derived measures have published definitions
- [ ] Base-year / normalisation choices are stated for every series
- [ ] Correlations were checked for common trend and for what drives them
- [ ] Sample sizes are stated where they are small
- [ ] Every claim is reproducible from the committed data files
- [ ] Every heading names the market and period it covers
- [ ] Sources are printed on the artefact, with publisher, series code, unit and span
- [ ] Deflators, breaks, exclusions and missing markets are listed alongside the sources
- [ ] The work ends in an instruction per market or segment, not a summary of findings
- [ ] Each instruction is tied to a period, and states what would change it
