# Livestock insurance — study plan (draft, under construction)

Proposed post: **who insures livestock, against what, and what the schemes
pay out** — penetration, premiums and claims for the countries that publish
real numbers.

## Why this scope

A single cross-country "penetration league table" would be dishonest:
"livestock insurance" is not one product. TARSİM's core cover is
mortality/disease; the main US programs (LRP, DRP) insure price and margin
risk; Germany routes epidemic risk through compulsory public funds
(Tierseuchenkassen), so a low insurance rate there does not mean unmanaged
risk. The study therefore leads with a typology — insured / public fund /
uncovered — and shows penetration and claims only per scheme, product named.

## Data plan (discover-first, all fetching in Actions)

| Market | Source | What it publishes | Status |
|---|---|---|---|
| TR | TARSİM annual reports (PDF, EN) | insured head by species, premiums, claims paid, policy counts | DONE — zero overlap conflicts |
| US | USDA RMA livestock/dairy participation files | head insured, premiums, subsidies, indemnities per program/year | DONE — LRP+DRP (LGM omitted, unmapped) |
| ES | Agroseguro / ENESA | insured animals, premiums, claims by line | PARKED — site blocks bots; ministry pages script-rendered |
| Denominators | TÜİK/FAOSTAT herd series | already committed: data/cattle-*.json, data/herd-cattle.json | done |

Comparable metric across schemes: **loss ratio (claims ÷ premiums)** —
unitless, immune to FX and inflation. Absolute values shown per scheme only.

Pipeline: `scripts/fetch_livestock_ins.py` via `.github/workflows/livestock-ins.yml`
(MODE=discover first; extraction pass written only against discover output —
house rule, three parsers written blind all failed silently before).

## Integrity checklist for this study

- [ ] Every penetration figure: numerator source (report + page), denominator
      source and year, species definition (cattle vs all livestock)
- [ ] Product named on every chart (mortality vs price/margin cover)
- [ ] Germany-style public funds shown as a separate category, not zero
- [ ] Loss ratios per scheme over time; no cross-scheme "winner" claims
- [ ] TARSİM figures pinned to report page numbers (PDF source, no API)
- [ ] Drought/disease years annotated only where the source itself names them

## Posting posture

Same as the vet-CPI post: data only, no market commentary (author's
professional territory — clear with employer comms before posting).
