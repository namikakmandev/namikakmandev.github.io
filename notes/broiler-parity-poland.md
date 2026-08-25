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

Open items after the first probe run: confirm C1012/C1091 for PL, pick the
longest unit base (I21 vs I15 chain), fill real product codes for the anchor
entries, validate the anchor against KIPDiP/IERiGŻ published relations if
findable.
