# Broiler feed/meat parity — extending the Türkiye monitor to Poland

Decision note, 2026-08. Answers "what is the most appropriate metric, and is the
data there?" before the build — per the data-availability checklist.

## The metric

Parity = **kg of feed one kg of chicken buys** (chicken-meat price ÷ feed price).
Unit-free, so it compares across currencies and inflation regimes without any
deflating — which is the whole point of a PL–TR comparison.

Constructions considered, best first:

1. **Absolute farm-gate parity** (live broiler PLN-or-TL/kg ÷ compound broiler
   feed price). The true grower economics; needs no anchor. Blocked for now:
   TÜİK collects no live-broiler farm-gate price (integration — the birds never
   trade on an open market; see broiler-margin.html method note), and Poland's
   MRiRW feed bulletins are PDFs. **Target, not the build.**
2. **Factory-gate PPI ratio, anchored** — the existing TR construction
   (PPI processed poultry meat ÷ PPI prepared feeds, level pinned to an official
   absolute parity). Poland has the exact NACE analogue in Eurostat
   `sts_inppd_m` (C1012 ÷ C1091), a proven provider in this repo's Actions
   pipeline. **This is the build**: same object, same construction, both
   countries — directly overlayable.
3. Chicken ÷ feed-grain basket — comparable but proxies actual feed away.
   Rejected as headline; the corn cross-check already exists for cattle.

Margin over feed cost (price − FCR × feed price) is more decision-useful but
imports an FCR assumption (~1.6 PL vs ~1.7–1.8 TR); kept as a possible derived
view, never the headline.

## Feasibility

```
PARTIAL until the Actions probe confirms Poland's NACE detail

Variable:      chicken-meat PPI ÷ prepared-feeds PPI, monthly, anchored to kg/kg
TR:            TÜİK Yİ-ÜFE C10.12 ÷ C10.91 · 2010-01→ · monthly · TEPGE 2023
               anchor (3.48) · lives in js/broiler-data.js — DONE
PL:            Eurostat sts_inppd_m C1012 ÷ C1091 · span TBD by probe · monthly.
               4-digit NACE is voluntary in STS — Poland's coverage is the open
               question the probe answers. Fallback: apri_pi20_outq poultry ÷
               apri_pi20_inq feedingstuffs (farm-gate, QUARTERLY — different
               object, would need its own page section, not the same chart).
Anchor (PL):   Eurostat annual absolute prices — apri_ap_anouta (chickens,
               live, per 100 kg) ÷ apri_ap_ina (complete broiler feed). Product
               codes TBD by probe. Until it lands, PL ships UNANCHORED: the
               index ratio supports the indexed-comparison chart only, and the
               kg/kg chart stays TR-only.
Comparability: identical construction both sides (option 2 above). Both are
               factory-gate, one step from the farm; stated on the page.
Breaks:        Eurostat STS rebased 2021=100 (I21, backcast); apri_pi rebases
               each 5 years; TR series has no known break 2010–2026.
Honest scope:  dynamics comparison (indexed) from day one; level (kg/kg)
               comparison only after the PL anchor is validated.
```

## Pipeline

- `data-sources.json`: `pl-*` probe entries (loose filters, tiny windows — safe
  if the monthly full fetch sweeps them) + `pl-broiler-ppi` fetch entry.
- `.github/workflows/broiler-parity-pl.yml`: discover → fetch → build → commit.
  Probe dump lands in `data/_pl-parity-probe.json`.
- `scripts/build_broiler_parity_pl.py`: ratio + optional anchor scaling +
  integrity metadata → `data/broiler-parity-pl.json`.
- `broiler-parity-pl-tr.html`: TR (from `js/broiler-data.js`) vs PL; renders
  honestly in all three states (PL missing / unanchored / anchored).

## Probe results (run 2026-08-25, data/_pl-parity-probe.json)

- `sts_inppd_m` PL: **C1012 and C1091 both reported.** indic_bt is
  `PRC_PRR_DOM` (not `PRIN` — the blind guess was wrong, the probe caught it).
  Units I21/I15/I10 all served; NSA only. → fetch entry fixed, FEASIBLE.
- Anchor: `apri_ap_anouta` prod_ani **11510000** = chickens live 1st choice,
  PLN/100 kg **live weight**; `apri_ap_ina` prod_inp **20624502** = complete
  feed for broiler production (bulk), PLN/100 kg. Both annual, 25 years,
  NAC+EUR. → anchor entries added.
- Comparability catch: the PL anchor is per kg LIVE weight, the TR anchor
  (TEPGE) per kg meat. The builder converts live → carcass-equivalent with a
  disclosed 0.76 yield; both the converted and raw live-based parities land in
  the output meta and the page states the assumption.
- Quarterly farm-gate fallback: `apri_pi20_outq` / `apri_pi20_inq` **404** —
  those dataset ids don't exist. Fallback dropped; primary path confirmed, so
  no hunt needed.

Remaining open item: cross-check the anchored PL level against any published
Polish relation (KIPDiP/IERiGŻ) if one turns up.
