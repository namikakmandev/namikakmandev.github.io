# Parite: Sığır — can the Middle East be added?

Feasibility check, not an analysis. Written before any design work, following
`.claude/skills/data-availability`. Nothing here was verified by direct fetch —
**this sandbox has no egress** (every candidate host returns 403 at the proxy),
so the open questions are wired into `scripts/probe_me_parity.py`, which runs in
Actions and dumps what each source actually returns.

## What the existing study measures

`data/cattle-parity.json` holds three regions, each a **meat price ÷ feed price**
ratio, rebased to its own 2016 mean = 100:

| Region | Numerator | Denominator | Frequency · span |
|---|---|---|---|
| US | Slaughter cattle PPI `WPU0131` | Corn PPI `WPU012202` | monthly · 1971-01 → 2026-06 |
| EU | Young bull R3 carcass, EUR/100 kg | Feed grain (maize), EUR/t | monthly · 2015-11 → 2026-07 |
| TR | Meat & meat products Yİ-ÜFE `TP.TUFE1YI.T17` | Compound feed Yİ-ÜFE `TP.TUFE1YI.T25` | monthly · 2010-01 → 2026-06 |

Two properties of that design constrain any addition. It needs **monthly**
data — the headline findings are lag correlations measured in months, and annual
data cannot carry them. And it needs a feed series that is a **domestic feed
cost**, because the claim being made is "the grain cycle drives feeder economics".

## Verdict per market

**PARTIAL — one strong candidate (Israel), one workable (Saudi Arabia), the rest
either annual-only or not machine-readable.**

### Israel — FEASIBLE, best candidate

CBS publishes an **agricultural output price index** and an **agricultural input
price index**, and the input index carries a dedicated **Fodder** sub-index
(2000 = 100, monthly; visible in third-party mirrors back to at least 2018, CBS
itself carries it much further). Output side has a livestock breakdown. That is
the same object the TR series is: an output PPI over an input PPI, both national,
both monthly.

There is a keyless JSON/XML API — `https://api.cbs.gov.il/index/data/price?id=<code>&format=json`
with a catalog endpoint `.../index/data/price_all?lang=en&chapter=<x>`. What is
**not** known is the numeric `id` of the two indices. That is the single blocker
and it is a discovery question, not a data-existence question.

Bonus: Israel is the only Middle East market where the ratio means the same thing
as in the US/EU/TR series — domestic feeding, domestic feed pricing, a real
statistical office publishing both sides on the same base.

### Saudi Arabia — PARTIAL, with a caveat that changes the story

GASTAT's **Wholesale Price Index** (2014 = 100, monthly, published to the current
month) has a *live animals and animal products* division and an *agriculture and
fishery products* division that carries cereals. Both sides exist at monthly
frequency, which already beats Egypt and Iran.

The caveat is economic, not statistical: **Saudi feed is almost entirely
imported**, and barley imports sat under a subsidy regime that was restructured in
the mid-2010s. A Saudi "parity" therefore measures *domestic meat price vs
imported feed landed cost under a changing subsidy* — a genuinely different object
from the US corn-belt ratio. Includable, but only with that spelled out, and the
subsidy reform is a break that has to be marked on the chart.

Machine-readability is unconfirmed: GASTAT publishes bulletins and an open-data
portal, but no API is documented. Probe first.

### Egypt — PARTIAL, blocked on format

CAPMAS has run a monthly PPI since September 2007 (base 2004/05), ISIC-structured,
so crop and animal production divisions exist. Coverage and frequency are fine.
The problem is delivery: the series ship as **PDF bulletins** through the CAPMAS
metadata catalog, with no open API found. Getting a 200-month series out of that
is a scraping project, not a `data-sources.json` entry.

Worth noting the FX question is *not* a blocker: both sides of the ratio are in
EGP, so the 2016/2022–24 devaluations do not mechanically move it. They move it
economically — imported feed repriced against domestic meat — which is a real
result, not an artefact.

### Iran — NOT FEASIBLE for this design

SCI publishes an agricultural PPI, but quarterly rather than monthly, and access
is unreliable. More importantly, feed has been sold at preferential/subsidised FX
rates for much of the window, so the denominator is an administered price, not a
market one. The ratio would not be comparable to the other four and the chart
would imply a comparison it cannot support.

### Jordan — PARTIAL, thin

DOS publishes a monthly **agricultural producer price index** (2016 = 100), which
is the numerator side. The denominator is the problem: Jordanian feed is imported
barley and does not appear as a domestic feed price index. Also PDF-delivered.

### UAE, Qatar, Kuwait, Oman, Bahrain — NOT FEASIBLE

Negligible domestic cattle feeding and no published feed/livestock price indices.
Nothing to add.

## The cross-country alternative worth considering

**FAOSTAT Producer Prices (PP domain)** reports farm-gate prices for primary
crops and live animals: annual 1991→ for ~160 countries, and **monthly from
January 2010 for 60+ countries** across ~200 products. Every Middle East market
above is an FAO member reporting into it.

This is attractive for two reasons beyond coverage. First, one source for all
countries means one methodology instead of five national ones — the "levels are
not comparable, read only changes" warning in the methodology note gets weaker.
Second, FAOSTAT prices are in **currency per tonne**, so meat ÷ feed is a
physically interpretable number — literally how many tonnes of maize a tonne of
cattle buys — which the current US figure of 2.44 explicitly is *not*.

The cost: monthly country coverage in PP is uneven and needs checking country by
country, and FAOSTAT lags roughly two years, so it cannot carry the "where are we
now" part of the story. Realistic use is a **second panel** — a slower,
better-comparable cross-country view sitting behind the fast US/EU/TR one — not a
replacement.

## Honest scope, if this ships

- Add **Israel** to the main four-region chart. It is the only market where the
  series measures the same object.
- Add **Saudi Arabia** as a labelled exception ("imported feed"), or leave it out.
  Do not put it on the same axis unlabelled.
- Everything else is annual-only or PDF-only. Say that; do not proxy it.
- A "Middle East parity" title would be dishonest for a two-country addition. The
  claim the data supports is **Israel joins the panel; the Gulf is a different
  economy; the rest is not published at usable frequency.**

## Status: implemented, not yet fetched

`scripts/fetch_cattle_data.py` now builds both regions and `build_merged()` folds
them into `data/cattle-parity.json` as `IL` and `SA`, rebased on exactly the same
terms as the other three.

- `build_il()` resolves the two CBS index ids **from the catalog by name at run
  time**, because they are not documented. Pin them with `IL_OUTPUT_ID` /
  `IL_FODDER_ID` once a run has printed them.
- `build_sa()` probes the candidate GASTAT/open-data endpoints and accepts a
  human-extracted CSV via `SA_WPI_CSV` (`month,series,value`). It **raises rather
  than writing an empty region** — a silent zero would read on the chart as "Saudi
  has no parity", which is a different claim from "we could not fetch it".
- The Saudi imported-feed caveat is carried as a `caveat` field on the region
  itself, so it travels with the data into whatever renders it.

Both were validated end-to-end against mock payloads (resolver, series parser,
CSV parser, merge, caveat propagation). **Neither has fetched a real number** —
this sandbox has no egress. Run `.github/workflows/cattle-data.yml`.

`parite-sigir.html`, the methodology page and the deck are deliberately untouched.
They hardcode three regions plus derived constants — long-run means, historical
dips, post-dip peaks — which can only be computed from real series. Wiring them
before the fetch would mean inventing those numbers.

## Open questions the probe answers

Run `.github/workflows/me-parity-probe.yml` (manual dispatch). It writes
`data/_me-parity-probe.json` and prints raw structure. It fetches nothing into the
analysis — discovery only.

1. Israel CBS: what are the index ids for agricultural output and fodder input,
   what is the monthly span, and does the API return them keylessly?
2. FAOSTAT PP: which Middle East countries actually have **monthly** cattle and
   maize/barley rows, and from when?
3. GASTAT: is there any machine-readable WPI endpoint at all, or is it bulletins?
