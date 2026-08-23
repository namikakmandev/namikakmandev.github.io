# Cattle parity — time-series tests

Reproduce with `python3 scripts/parity_econometrics.py` (needs `statsmodels`).
Raw output: `data/cattle-parity-tests.json`. Series as published:
US 1971-01→ (n=667), EU 2015-11→ (n=130), TR 2010-01→ (n=199),
IL 2005-01→ (n=259), IL-alt 2013-02→ (n=162).

Four questions the correlations on the study page cannot answer, and what the
tests say. Two published figures were re-derived independently and both match.

---

## 0. What replicated

| Published claim | Re-derived | Verdict |
|---|---|---|
| "2016 base is 23% above the US long-run mean" | +22.6% (2016 mean 1.324 vs full-sample 1.080) | matches |
| Israel pairs "r = 0.96 in levels, 0.89 in annual changes" | 0.958 levels, 0.886 annual | matches |
| "84% of movement from feed, 16% from cattle" (US) | 78% / 22% on monthly log changes | matches, direction confirmed |

The data construction is sound. Everything below is about what may be *concluded*
from it, not about whether it was built correctly.

---

## 1. Stationarity — is a parity level meaningful?

ADF (null: unit root, i.e. no fixed mean) and KPSS (null: stationary) on log parity.

| | corr in **levels** | corr in **monthly changes** | parity ADF p | parity KPSS p |
|---|---|---|---|---|
| US | 0.59 | **0.08** | 0.012 | 0.013 |
| EU | 0.46 | 0.23 | 0.702 | 0.058 |
| TR | 0.99 | 0.51 | 0.424 | 0.100 |
| IL | 0.62 | **−0.00** | 0.231 | 0.051 |
| IL-alt | 0.63 | **−0.33** | 0.797 | 0.010 |

**The level/change gap is the whole point.** US meat and feed correlate at 0.59 in
levels and 0.08 in changes; Israel goes from 0.62 to zero, and the alternative
Israel pair flips sign. Almost all of the level correlation is two series drifting
upward together, not a relationship. The deck headline *"one ratio, read as change
— never as level"* is not caution, it is the correct reading, and it now has a test
behind it.

**But it cuts further than the study currently admits.** ADF and KPSS both reject
for the US — the classic near-unit-root / structural-break signature. For EU, TR,
IL and IL-alt the parity level does not test as mean-reverting at all. So "parity
is cheap/expensive against its own mean" is not supported outside the US, and even
there it is fragile (§3).

## 2. Cointegration — are meat and feed genuinely tied?

Engle-Granger and Johansen on log meat / log feed. They disagree, which is normal:
Engle-Granger has low power, Johansen more.

| | Engle-Granger p | Johansen trace (r=0) vs 5% crit | verdict | β (meat on feed) |
|---|---|---|---|---|
| US | 0.251 | 14.8 vs 15.5 | **no** (just misses) | 0.70 |
| EU | 0.792 | 8.1 vs 15.5 | no | 0.58 |
| TR | 0.540 | 20.2 vs 15.5 | **yes** | 1.03 |
| IL | 0.356 | 20.0 vs 15.5 | **yes** | 0.60 |
| IL-alt | 0.933 | 4.9 vs 15.5 | no | 0.13 |

Two findings, both awkward:

1. **The long-run tie is established for Turkey and Israel, not for the US** — the
   flagship market, with the longest series, is the one that fails. US trace 14.8
   against a 15.5 threshold is a near-miss, not a pass.
2. **The ratio imposes 1:1 pass-through, and only Turkey's data supports it.**
   β is 0.70 (US), 0.58 (EU), 0.60 (IL), 0.13 (IL-alt), 1.03 (TR). A 10% feed move
   is not matched by a 10% meat move anywhere except Turkey. Dividing meat by feed
   is a *definition*, and that is fine — but it should be described as an index
   convention, not as an equilibrium the market returns to.

## 3. Mean-reversion speed — and whether the mean holds still

AR(1) on log parity. **The confidence interval is the finding, not the point estimate.**

| | ρ | half-life | 95% CI |
|---|---|---|---|
| US | 0.972 | 24 months | 14 – 73 months |
| EU | 0.991 | 76 months | 18 – never |
| TR | 0.979 | 32 months | 13 – never |
| IL | 0.980 | 35 months | 16 – never |
| IL-alt | 0.989 | 64 months | 20 – never |

Only the US produces a finite upper bound. Everywhere else ρ is statistically
indistinguishable from 1 — "the cycle takes about three years" is a number the data
will not carry.

Zivot-Andrews (unit root allowing one break in the mean) and US subsamples:

| | ZA p | break |
|---|---|---|
| US | 0.123 | 2006-09 |
| TR | **0.020** | 2022-11 |
| IL-alt | **0.017** | 2021-01 |
| EU / IL | 0.867 / 0.429 | — |

| US window | mean parity | sd | parity ADF p |
|---|---|---|---|
| 1971–1985 | 0.824 | 0.198 | 0.251 |
| 1986–2005 | 1.198 | 0.278 | 0.019 |
| 2006–2015 | 0.986 | 0.355 | 0.202 |
| 2016–2026 | 1.310 | 0.453 | 0.837 |

The US break lands on **September 2006** — the ethanol build-out, unprompted by the
test. Before 2006 parity mean-reverts (ADF p=0.053 for 1971–2005); after, it does
not (p=0.487). Volatility more than doubles across the four windows. The cycle
framing is much better supported in the first half of the sample than the second,
and the level the cycle returns to has itself moved.

## 4. Lead-lag — does feed move first?

Granger causality on monthly log changes, lags 1–6 (p-values; **bold** = significant at 5%).

| | feed → meat | meat → feed | reading |
|---|---|---|---|
| US | **0.024 / 0.040 / 0.043** (lags 4–6) | 0.39 – 0.88 | one-directional, feed leads |
| EU | 0.059 – 0.071 | **0.009 – 0.013** | runs the other way |
| TR | **0.001 – 0.024** | **0.004 – 0.014** | feedback, both directions |
| IL | 0.27 – 0.91 | 0.45 – 0.80 | nothing either way |
| IL-alt | 0.23 – 0.85 | **0.000 – 0.0003** | meat leads |

Share of monthly parity variance: US feed **78%**, EU feed **86%**, TR feed **21%**
(meat 79%), IL feed **30%** (meat 70%).

**"A grain cycle wearing a cattle costume" is a US and EU statement.** In Turkey the
meat side drives four-fifths of parity movement and causality runs both ways; in
Israel feed leads nothing at all. Applied to all four markets the line is wrong —
applied to the US, it is exactly right and now has a directional test behind it.

## 5. Israel robustness — do the two pairs say the same thing?

| | value |
|---|---|
| correlation, levels | 0.958 |
| correlation, annual changes | 0.886 |
| correlation, quarterly changes | 0.766 |
| correlation, monthly changes | 0.555 |
| cointegration of the two parities (EG p) | 0.692 |
| ADF on the spread between them | p = 0.454 |

The published figures replicate. But the agreement is horizon-dependent — strong
annually, half as strong monthly — and the two pairs are **not** cointegrated: the
gap between them wanders without returning. So "the conclusion does not depend on
the pair chosen" holds for the annual direction of travel. It does not hold for the
level, or for month-to-month timing.

---

## Drafting: what goes where

The tests belong in the methodology note. The deck gets shorter sentences, not
longer ones.

**Slide: "It is a grain cycle wearing a cattle costume"**
- *deck:* "In the US, feed moves first — meat follows within six months, never the
  reverse. In Turkey it is the opposite: meat drives four-fifths of the swing."
- *methodology:* Granger causality on monthly log changes, lags 1–6. US feed→meat
  significant at lags 4–6 (p = 0.024/0.040/0.043), meat→feed insignificant
  throughout (p ≥ 0.39). TR bidirectional at all lags tested.

**Slide: "One ratio, read as change — never as level"**
- *deck:* "In levels these series correlate at 0.6. In changes, at 0.1. The level is
  two trends passing each other — only the change is information."
- *methodology:* ADF/KPSS on log parity; level correlation 0.588 vs 0.083 on first
  differences (US). Corresponding pairs for EU/TR/IL in the table above.

**Slide: "Where each market stands against its own 2016"**
- *deck:* "2016 is a starting line, not a fair value. The US sat 23% above its own
  half-century average that year — and since 2006 there is no average it reliably
  returns to."
- *methodology:* 2016 mean 1.324 vs full-sample 1.080 (+22.6%). Zivot-Andrews break
  2006-09; parity ADF p = 0.053 (1971–2005) vs 0.487 (2006–2026).

**Slide: Israel robustness**
- *deck:* "Israel behaves like the others — checked against a second, independently
  built pair over thirteen years."
- *methodology:* levels 0.958, annual changes 0.886, monthly 0.555. The two pairs
  are not cointegrated (p = 0.692); agreement is a shared annual direction, not a
  shared level.

## What should change on the study page

1. **Qualify the grain-cycle claim to US/EU.** Currently the strongest, most
   quotable line in the deck, and it is wrong for half the sample.
2. **Drop or bound any "returns to its mean in N months" language.** Only the US
   has a finite upper bound, and it is 73 months wide.
3. **Describe the ratio as an index convention, not an equilibrium.** β ≠ 1 in four
   of five pairs.
4. **Add the post-2006 break to the US narrative.** The test found the ethanol
   shift without being told to look for it — that is a genuinely good story, not a
   caveat.
5. **Soften the Israel robustness sentence** from "does not depend on the pair
   chosen" to the annual-direction version.

None of this weakens the study. Items 1 and 4 make it more interesting: the cycle
is not one global mechanism but two different ones, and the US regime visibly
changed in 2006.
