# Working in this repository

A GitHub Pages portfolio (static HTML at the root) plus two things that matter for data work:

- `data/` holds curated economics datasets as JSON, indexed by `data/_catalog.json`. Nothing here is edited by hand: `scripts/fetch.py` writes them from `data-sources.json`, and `scripts/build_catalog.py` rebuilds the index. The `.github/workflows/fetch-data.yml` workflow runs both monthly and on dispatch (inputs `only` = space-separated dataset names, `mode` = `discover` to dump a source's raw shape instead of parsing). It commits to `main` itself.
- `explore.html`, `chart.html` and `data.html` are the data pages. They share `css/data-look.css` (paper ground, Fraunces headings, Plex Mono numbers, the six line colours) on top of `css/style.css`; the rest of the site stays dark. `explore.html` draws six featured charts from `STARTS` before anything is clicked.
- `moves.html` is the monthly "what moved" note: `scripts/whats_moving.py` runs after the catalogue in the fetch workflow and writes `data/_moves.json` (the ten most unusual year-on-year moves, ranked by z-score against each series' own history). Its names come from the `INFO`/`SUBJECTS`/`NAMES`/`CODES` blocks in `explore.html`, which it parses, so keep those JSON-shaped.
- `mcp/` is the econ-data MCP server (TypeScript, Cloudflare Worker, zero runtime dependencies beyond the MCP SDK and zod). It serves the curated data, ten live providers, an econometrics toolkit, and the `plot` tool behind `chart.html`.

## Commands

```bash
cd mcp && npm test        # numeric checks + two end-to-end suites through a real MCP client (~30 s)
cd mcp && npm run typecheck
cd mcp && npm run bundle  # regenerates dist-bundle/econ-mcp.js; commit it
python3 scripts/build_catalog.py
```

Run the tests and the bundle before every commit that touches `mcp/`. The bundle is a fallback for manual paste deploys; the real deploy is git-driven.

## Deploy

Merging to `main` with changes under `mcp/` triggers Cloudflare Workers Builds (root `mcp`, `npx wrangler deploy`). Dashboard variables survive (`keep_vars`). Bump `SERVER_BUILD` in `mcp/src/version.ts` on every server change; `list_providers` echoes it, which is the only way to confirm a deploy from a client. Variables added in the dashboard create an undeployed version that must be promoted from the Deployments tab. The website's question box (`/v1/ask`, `js/ask.js`) spends the owner's `ANTHROPIC_API_KEY`; its daily counters are a Durable Object declared in `wrangler.jsonc`, so a change to the class needs a new migration tag.

The sandbox cannot reach the Worker, the site, or most data providers. Verify live behaviour through the Econ Data connector (tools `mcp__Econ_Data__*`) and data fetches through GitHub Actions runs. Reachable from the sandbox: npm, api.github.com (public endpoints), raw.githubusercontent.com, gitlab.com.

## Provider quirks (learned the hard way)

- **EVDS** (TCMB): host `evds3.tcmb.gov.tr/igmevdsms-dis/`, key in the `key` header, parameters follow the path with no `?` for every endpoint, including `categories/`, `datagroups/mode=0&code=&type=json`, `serieList/type=json&code=...`.
- **FAOSTAT**: needs a free developer account since 2025 (`FAOSTAT_USER`/`FAOSTAT_PASSWORD`, login at `api/v1/auth/login`, form-encoded, 60-minute JWT). The edge rejects requests without a User-Agent. The `element` filter returns nothing on some items even with the right code, so both the server and `fetch.py` filter elements client-side. Annual producer-price rows carry a `Months Code` (7021).
- **IMF** (SDMX 3.0): `api.imf.org/external/sdmx/3.0/data/dataflow/{agency}/{flow}/{version}/{key}` with `Accept: text/csv`; `+` or `~` for the latest version; `c[TIME_PERIOD]` filters return 400, so windows are cut client-side. CSV dimensions sit between the `ACTION` and `TIME_PERIOD` columns.
- **BIS**: SDMX CSV has no `KEY` column; key on the dimension columns.
- **FRED**: keyless CSV dates monthly data as `YYYY-MM-01`; `collapseDates` turns that into `YYYY-MM`.
- **World Bank Pink Sheet**: the workbook has no code row any more; columns are matched by commodity name.
- **GitHub Pages** runs Jekyll: files starting with `_` are not served unless `.nojekyll` exists (it does).

## Conventions

- Every tool result carries `source` and `caveats`; keep it that way when adding tools.
- Analysis tools take `SeriesRef` inputs (`{dataset, series}`, `{provider, id}`, `{points}`) so one implementation serves all data.
- New provider: add to `mcp/src/providers.ts`, the enum in `mcp/src/resolve.ts` and both enums in `mcp/src/analysis.ts`, the root listing in `mcp/src/index.ts`, a fixture in `mcp/test/fixtures.mjs`, and an end-to-end check.
- New stored dataset: an entry in `data-sources.json`, then dispatch the fetch workflow with `only` set to its name and read `data/_fetch-report.json`.
- Never paste keys or passwords into files or commits. Secrets live in the Cloudflare dashboard and GitHub Actions secrets.
