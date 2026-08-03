# Handoff: broiler meat/feed parity pipeline

For any agent or developer picking this up (written for OpenAI Codex; nothing here
is agent-specific). State as of 2026-08-03, branch `claude/broiler-meat-feed-parity-gibzxa`.

## What this is

Broiler (chicken) meat-price ÷ feed-price parity across Egypt, Iraq, Jordan, Kuwait,
Türkiye, Poland, Saudi Arabia, Lebanon, Oman, Qatar, UAE — built the same way as the
earlier cattle parity study (`parite-sigir*.html`, `data/cattle-parity.json`).

The deliverable dataset is **`data/broiler-parity.json`**, built by
**`scripts/build_broiler_parity.py`** from the fetched series below. Regions in it:

| key | what | frequency | span | basis |
|---|---|---|---|---|
| PL-weekly | EC agri-food portal, broiler ÷ feed wheat & maize, EUR | weekly | 2015-11 → now (auto) | carcass selling price |
| TR-monthly | TÜİK Yİ-ÜFE T17 ÷ T25 via EVDS | monthly | 2005-01 → now (auto) | ALL-meat PPI, not broiler-specific |
| WORLD | IMF poultry index ÷ corn (2016=100) via FRED | monthly | 2003-01 → now (auto) | world benchmark, index only |
| EG, QA, LB | FAOSTAT chicken ÷ maize, USD/t | annual | ends 2019–2023 | carcass producer price |
| PL, IQ, JO | FAOSTAT chicken ÷ maize, USD/t | annual | ends 2011–2024 | live-weight ("biological") producer price |
| TR-carcass / TR-bio | FAOSTAT, two segments | annual | 1999–2012 / 2011–2024 | basis change — never splice |

Kuwait, Oman, UAE: **no poultry prices exist in any public API** (verified by dumping
every item those countries report to FAOSTAT — see `data/pp-items-*.json`).
Saudi Arabia: chicken exists (1999–2023) but no usable domestic feed series.

## Architecture

Everything is config-driven:

1. **`data-sources.json`** — one entry per series. Providers: `fred`, `eurostat`,
   `owid`, `csv` (plain or zipped), `json` (generic JSON-record APIs), `evds` (CBRT).
2. **`scripts/fetch.py`** — the only fetcher. `MODE=discover python scripts/fetch.py NAME`
   dumps the source's real structure instead of parsing; ALWAYS discover before writing
   a parser config. Every run writes `data/_fetch-report.json` (counts, spans, errors)
   so a silent zero is visible.
3. **`.github/workflows/fetch-data.yml`** — runs it. Manual dispatch takes `only`
   (space-separated source names) and `mode` (`discover` or empty), plus a monthly
   cron. It commits `data/` back to the branch it ran on.
4. `scripts/build_broiler_parity.py` — pure local step, reads `data/*.json`, writes
   `data/broiler-parity.json`. Run it after any refetch.
5. `scripts/check_world_me_correlation.py` — integrity check (see "Findings" below).

**The dev sandbox cannot reach any statistics host** (FAO, FRED, Eurostat, TCMB,
ec.europa.eu, even DBnomics) — the egress proxy 403s. Never conclude a source is dead
from a local curl; run it through the Actions workflow. GitHub API is reachable, so
the loop is: edit config → push → dispatch workflow → pull → read
`data/_fetch-report.json`.

**Do not push to the branch while a fetch workflow is running** — the workflow's own
commit will be rejected as non-fast-forward and the run fails at the Commit step
(fetch results are still in the run logs if that happens).

## Endpoints and their traps (each cost a debugging cycle)

- **FAOSTAT**: the query API (`faostatservices.fao.org`) returns **401** now. Use the
  public bulk zip instead:
  `https://bulks-faostat.fao.org/production/Prices_E_All_Data_(Normalized).zip`
  (~43 MB, csv provider handles zips). Filters that work:
  `Item Code` 1058 = chicken carcass, `Item` = "Meat of chickens, fresh or chilled (biological)"
  for the live-weight item, 56 = maize, 15 = wheat; `Element Code` 5532 = USD/tonne
  (5530 = LCU); `Months Code` 7021 = annual value (monthly rows exist for some countries).
  Publication lag ~18–30 months, one new year each December.
- **EVDS (CBRT)**: moved from `evds2.tcmb.gov.tr/service/evds/...` to
  **`https://evds3.tcmb.gov.tr/igmevdsms-dis/`** — the old host serves an HTML SPA
  shell for every path (looks like success, isn't JSON). Auth: repo Actions secret
  **`EVDS_KEY`** passed as env, sent as `key:` header. Data:
  `{base}series=CODE&startDate=dd-mm-yyyy&endDate=dd-mm-yyyy&type=json` (params in
  path style, no `?`; multiple codes joined with `-`; response items keyed
  `TP_TUFE1YI_T17` i.e. dots→underscores, dates as `2005-1`). Catalogue:
  `{base}datagroups/mode=0&code=&type=json` and `{base}serieList/type=json&code=DATAGROUP`.
  Useful codes: `TP.TUFE1YI.T17` (meat products PPI), `TP.TUFE1YI.T25` (prepared
  animal feeds PPI), `TP.TARIMGFE.GK378650499` (concentrated feeds input index,
  2020-01→). EVDS has **no broiler-specific price**: the current agricultural PPI
  datagroup (`bie_tarimufe`) stops at 4 aggregates and there is no retail item-price
  group. A truly broiler-only TR series means integrating TurkStat's own portal (open item).
- **EC agri-food portal** (current EU weekly prices, from 1991):
  `https://www.ec.europa.eu/agrifood/api/poultry/prices?memberStateCodes=PL&beginDate=01/01/2015&endDate=31/12/2026`
  and `.../api/cereal/prices?...`. JSON lists. Traps: poultry prices use dot decimals
  ("€235.96") but cereal prices use **decimal commas** ("€165,88") — the json provider
  normalises both; dates are dd/mm/yyyy (`key_fmt: "dmy"`); poultry unit is EUR/100 kg
  (×10 for EUR/t), cereals EUR/t. Product names: "Whole broiler (65%)", "Feed wheat",
  "Feed maize".
- **Eurostat**: `apri_pi20_*` / `apri_pi15_*` agricultural price index datasets 404 on
  the dissemination API even though they exist on DBnomics — abandoned; the EC
  agri-food portal is better for prices anyway. Other Eurostat datasets (e.g.
  `aact_eaa01`) work fine via the existing provider.
- **FRED**: keyless CSV, most reliable. IMF world prices: `PPOULTUSDM` (poultry —
  an **index** 2016=100, not USD/t!), `PMAIZMTUSDM` (corn USD/t), `PSMEAUSDM`
  (soybean meal), `PWHEAMTUSDM` (wheat). Because poultry is an index, the world
  parity is only valid as an index (corn rebased to 2016=100 in the build script).

## Integrity findings — keep these attached to any use of the data

1. **Bases differ by country** (carcass vs live weight vs PPI index). Ratios are
   comparable over time within a region; levels are NOT comparable across regions.
2. **Türkiye's FAOSTAT levels are wrong-looking**: 2023 shows ~5,282 USD/t for "live
   weight" vs ~2,300 USD/t TurkStat farm gate. Use ratio movement only; never quote
   the level. (Caveat is embedded in the JSON.)
3. **The world benchmark does not proxy domestic ME parity.**
   `scripts/check_world_me_correlation.py`: in log changes, world parity vs domestic
   parity r = 0.05 (EG, n=16), −0.26 (QA, n=7), 0.17 (IQ, n=13), −0.63 (JO, n=8);
   level correlations of 0.3–0.8 are shared trend. Only Türkiye co-moves (r_yoy = 0.50,
   n=246). Frame WORLD as the *import-cost benchmark*, not an estimate of farm-gate
   parity. Pass-through is weak because of FX wedges (Egypt devaluations distort the
   official-rate USD series) and administered/subsidised feed markets.
4. Dead series stay dead: Jordan stopped reporting 2011, Iraq 2018, Lebanon 2019.
5. Small samples: annual overlaps are 5–18 observations — say so wherever quoted.

## How to extend

- New series = new entry in `data-sources.json` (no code unless a new provider is
  needed). Then: push → dispatch `fetch-data.yml` with `only=<name> mode=discover` →
  read report → fix config → dispatch again without mode → pull →
  `python3 scripts/build_broiler_parity.py` → commit.
- One-off probes: set `"enabled": false` after use — but note fetch.py skips disabled
  entries even when named explicitly in `only`, so flip the flag while probing.
- The monthly cron refreshes everything enabled on the default branch once merged.

## Open items

- Report page (`broiler-parity.html` in the style of `parite-sigir.html`) not built yet.
- Broiler-specific TR monthly series would need TurkStat's data portal (separate API).
- Gulf current data exists only in manual monthly bulletins (Saudi GASTAT, Oman NCSI,
  Egypt CAPMAS) — retail basis, no API; decide whether manual collection is worth it.
- FAOSTAT adds one year each December — refetch then extends the annual layer.
