# econ-mcp

A remote [MCP](https://modelcontextprotocol.io) server for economics data and analysis. Any MCP client (Claude.ai, Claude Code, Claude Desktop, Cursor, ChatGPT) connects to it and can pull series, run the standard time-series tests on them, and get told which test fits.

Two kinds of data:

- **Curated datasets** from this repo's `data/` directory, served by GitHub Pages and refreshed by the workflows in `.github/workflows/`. The server reads them live, so a refresh needs no redeploy. The index is `data/_catalog.json`, rebuilt on the same schedule.
- **Live providers**: FRED, Eurostat, World Bank, ECB Data Portal, OECD, Our World in Data, and TCMB EVDS for Turkey. Pulled on demand, cached for ten minutes in the Worker, never stored.

Every answer carries the series' source and caveats. That is the point: a model asking for a number gets the survey break, the index-not-quantity warning, or the unknown provenance in the same reply.

## Tools

**Curated data**

| Tool | What it does |
|---|---|
| `list_datasets` | Every dataset with shape, coverage, source, note, provenance. |
| `search_datasets` | Keyword search over names, sources, notes and top-level series keys. |
| `describe_dataset` | Catalog entry plus every series id the file exposes, with date ranges. |
| `get_series` | One series as `[date, value]` points with window, `last_n`, annual resampling and transforms. |
| `compare_series` | Two series aligned on shared dates, with ratio and correlations of levels and of year-on-year changes. |
| `get_caveats` | Source, method notes, breaks, refresh status, provenance. |
| `get_dataset` | The raw file or a sub-tree by dot path, for anything that is not a plain series. |

**Live providers**

| Tool | What it does |
|---|---|
| `list_providers` | Coverage, id format, key status and starter ids per provider. |
| `search_external` | Find ids. FRED searches its full catalogue when `FRED_API_KEY` is set, World Bank searches all indicators, the rest match a starter list. |
| `fetch_external` | Pull a series by provider and id. Multi-series replies (countries, dimensions) list their keys; pick one with `series`. |

**Analysis**. Each takes series references, so the same call works on a local dataset, a live pull, or numbers you paste in:

```json
{ "dataset": "us-prices", "series": "cattle_ppi", "transform": "log", "start": "1990-01" }
{ "provider": "fred", "id": "CPIAUCSL", "transform": "yoy" }
{ "provider": "eurostat", "id": "prc_hicp_midx", "params": { "geo": "TR", "coicop": "CP00", "unit": "I15" } }
{ "points": [["2020", 101.2], ["2021", 104.9]], "label": "mine" }
```

| Tool | What it does |
|---|---|
| `suggest_analysis` | Inspects frequency, length, integration order, trend, seasonality and overlap, then returns an ordered plan of tool calls with reasons and the pitfalls the data carry. Call this first. |
| `describe_stats` | Moments, quantiles, autocorrelations, Ljung-Box, Jarque-Bera, ADF on levels and differences, trend and seasonal strength. |
| `test_stationarity` | Augmented Dickey-Fuller with MacKinnon critical values, lag length by AIC, integration order. |
| `regress` | OLS with Newey-West standard errors, R², Durbin-Watson, AIC/BIC, residual tests, optional distributed lags and trend. Warns when a levels regression looks spurious. Log both sides for elasticities. |
| `granger_causality` | F-tests in both directions, with a non-stationarity warning. |
| `cointegration` | Engle-Granger: long-run vector, residual unit-root test, equilibrium error. |
| `cross_correlation` | Correlation by lead and lag with a significance band. |
| `hp_filter` | Trend and cycle, lambda by frequency. |
| `decompose` | Classical seasonal decomposition, factors per month or quarter, strength measures. |
| `forecast` | Holt-Winters, Holt, or AR(p), with dated forecasts and an approximate band. |
| `structural_break` | Chow test at a date, or a sup-F scan to locate one. |
| `rolling` | Rolling mean, standard deviation, or correlation. |

The numerics are in `src/stats.ts`, dependency-free so they run on the Worker. Critical values are MacKinnon (1991); p-values come from the t, F and chi-square distributions. `test/stats.test.mjs` checks each estimator against known answers on seeded data.

Resources: `econ://catalog` and `econ://dataset/{name}`.

## Connect

The endpoint is `https://<worker-host>/mcp` over Streamable HTTP. After `npm run deploy` the host is `econ-mcp.<your-subdomain>.workers.dev`.

- **Claude.ai**: Settings, Connectors, Add custom connector, paste the `/mcp` URL.
- **Claude Code**: `claude mcp add --transport http econ https://<worker-host>/mcp`
- **Clients that only speak stdio**: `npx mcp-remote https://<worker-host>/mcp`

If `MCP_API_KEYS` is set, add `--header "Authorization: Bearer <key>"` in Claude Code, or enter the key where the client asks.

## Deploy

Pushes to `main` that touch `mcp/` deploy through `.github/workflows/deploy-mcp.yml` once `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` exist as repo secrets. By hand:

```bash
cd mcp
npm install
npx wrangler login
npm run deploy
```

### Without a token: paste into the dashboard

The same route the `assetix-ai` worker took. `dist-bundle/econ-mcp.js` is the whole server in one file (`npm run bundle` regenerates it).

1. Cloudflare dashboard, Workers & Pages, Create, Create Worker, name it `econ-mcp`, Deploy the placeholder.
2. Edit code, delete the placeholder, paste the contents of `dist-bundle/econ-mcp.js`, Deploy.
3. Settings, Variables and Secrets: add `DATA_ORIGIN` = `https://namikakmandev.github.io` (plain text). Add `EVDS_API_KEY` as a secret if you want Turkish data.
4. The endpoint is `https://econ-mcp.<your-subdomain>.workers.dev/mcp`. Open the root URL in a browser to see the server describe itself.

Optional secrets, kept out of git:

```bash
npx wrangler secret put FRED_API_KEY    # FRED catalogue search
npx wrangler secret put EVDS_API_KEY    # TCMB EVDS pulls
npx wrangler secret put MCP_API_KEYS    # bearer tokens, comma-separated
```

The free Workers tier is enough: no storage, no Durable Objects. The heaviest call, a Holt-Winters grid search on 900 monthly points, is well under the CPU limit.

## Develop and test

```bash
npm test          # numeric checks, then two end-to-end suites through the real MCP client
npm run dev:node  # local server on http://127.0.0.1:8787/mcp with data from the checkout
npm run dev       # wrangler dev, data from the live site
```

Provider parsers are tested against canned replies in `test/fixtures.mjs` in the shape each API returns. The live hosts are not reachable from the development sandbox, so the first real pull is a check to make after deploying.

## Layout rules the server relies on

- Date keys are `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-Qn` or `YYYY-Sn`. Anything else is raw only.
- A table is `{"columns": [...], "rows": [[date, ...], ...]}`; a list of rows needs `meta.columns`.
- Top-level `source`, `note`, `config.note`, `meta.construction` and `scope_note` are surfaced as caveats.
- Files starting with `_` are probes and are not catalogued.

## Later

- Per-user login (OAuth 2.1 through Cloudflare's `workers-oauth-provider`) and Stripe metering. The bearer check in `src/index.ts` is the seam.
- Johansen cointegration and VAR/VECM for more than two series, ARIMA with automatic order, KPSS as a complement to ADF.
- IMF and BIS providers once their SDMX 3 endpoints settle.
