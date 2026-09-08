# econ-mcp

A remote [MCP](https://modelcontextprotocol.io) server for economics data and analysis. Any MCP client (Claude.ai, Claude Code, Claude Desktop, Cursor, ChatGPT) connects to it and can pull series, run the standard time-series tests on them, and get told which test fits.

Two kinds of data:

- **Curated datasets** from this repo's `data/` directory, served by GitHub Pages and refreshed by the workflows in `.github/workflows/`. The server reads them live, so a refresh needs no redeploy. The index is `data/_catalog.json`, rebuilt on the same schedule.
- **Live providers**: FRED, Eurostat, World Bank, ECB Data Portal, OECD, Our World in Data, BIS, IMF Data (WEO projections, CPI, IFS), FAOSTAT (with a free account), and TCMB EVDS for Turkey (with catalogue search), and Open-Meteo historical weather (ERA5 reanalysis, keyless). Pulled on demand, cached for ten minutes in the Worker, never stored.

And one way to look at any of it: the `plot` tool returns a link to `chart.html` on the site, an interactive chart of up to eight series with hover values, log and rebase toggles, a right-hand axis, the sources and caveats, a table and CSV download. The link carries the series references, so it redraws from fresh data every time.

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
| `weather` (provider) | Daily temperature, rainfall and evapotranspiration anywhere on land from 1940, aggregated to months or years. Named grain and livestock regions (`us-corn-belt`, `tr-konya`, `ua-steppe`, `br-mato-grosso`, …) or any `lat,lon`. The natural instrument for `iv_regress`: weather moves feed cost but reaches meat prices only through it. |
| `search_external` | Find ids. FRED searches its full catalogue when `FRED_API_KEY` is set, World Bank searches all indicators, EVDS walks the TCMB catalogue, FAOSTAT searches its item, area and element lists; the rest match a starter list. |
| `fetch_external` | Pull a series by provider and id. Multi-series replies (countries, dimensions) list their keys; pick one with `series`. |

**Drawing**

| Tool | What it does |
|---|---|
| `plot` | Resolves up to 8 series references and returns a `chart_url` on the site. Options: title, log scale, which series go on a right-hand axis, shaded bands, a numeric x axis for horizons. `forecast` and `local_projections` return a ready `chart_url` with their band. |

The page reads `GET /v1/series?s=<json>` on the Worker (also `POST /v1/series`), a plain HTTP endpoint that resolves the same series references and returns points, sources and caveats. Anything that speaks HTTP can use it directly.

`/v1/analyze` runs the analysis tools over the same plain HTTP: `POST {"tool":"predict","args":{...}}`, or `GET ?tool=...&args=<json>`, and `GET /v1/analyze` with no tool lists what is callable. A web page can therefore forecast a series or locate a structural break with no MCP client and no model in the loop; `explore.html` on the site does exactly that.

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
| `test_stationarity` | Augmented Dickey-Fuller with MacKinnon critical values plus KPSS, lag length by AIC, integration order and a joint reading. |
| `regress` | OLS with Newey-West standard errors, R², Durbin-Watson, AIC/BIC, residual tests, Breusch-Pagan, VIF and RESET diagnostics, optional distributed lags and trend. Warns when a levels regression looks spurious. Log both sides for elasticities. |
| `granger_causality` | F-tests in both directions, with a non-stationarity warning. |
| `cointegration` | Engle-Granger: long-run vector, residual unit-root test, equilibrium error. |
| `johansen` | Trace test for 2 to 5 series with MacKinnon-Haug-Michelis critical values for an unrestricted constant, a restricted constant or a restricted trend, rank, first cointegrating vector, and a drift check that says which case the data support. |
| `vecm` | Vector error-correction model on cointegrated series: long-run vectors (with the constant or trend inside the relation when restricted), adjustment coefficients with t-tests (who corrects, how fast, half-life), short-run lags, and the current deviation from equilibrium. |
| `var_model` | VAR(p) with lag order by AIC, block Granger tests, structural impulse responses (recursive, long-run Blanchard-Quah, or sign restrictions) with bootstrap bands, cumulative responses, long-run effects and variance decomposition. |
| `local_projections` | Jordà impulse response of y to a shock in x: one regression per horizon with Newey-West bands, responses per unit and per one-sd shock, cumulative response. The check on `var_model`. |
| `cross_correlation` | Correlation by lead and lag with a significance band. |
| `hp_filter` | Trend and cycle, lambda by frequency. |
| `decompose` | Classical seasonal decomposition, factors per month or quarter, strength measures. |
| `forecast` | Holt-Winters, Holt, AR(p), or ARIMA(p,d,q) with order by AIC, with dated forecasts and an approximate band. |
| `predict` | One call for "where is this going?": tests every method that suits the series, ranks them by out-of-sample error, says whether the winner really beats assuming no change, and forecasts with it. Explains each method in plain words. |
| `forecast_evaluate` | Rolling-origin backtest of naive, drift, seasonal naive, Holt, Holt-Winters, AR and ARIMA: RMSE, MAE, MAPE by horizon, skill against naive, Diebold-Mariano tests of the winner. Run it before `forecast`. |
| `deflate` | A nominal series in constant prices of a base date, using any price index as deflator. |
| `structural_break` | Chow test at a date, or a sup-F scan judged against Andrews critical values; `max_breaks` runs a sequential search for several breaks with the mean or relation per segment. |
| `volatility` | ARCH-LM test and a GARCH(1,1) fit: persistence, unconditional and conditional volatility, one-step forecast. |
| `iv_regress` | Two-stage least squares when x is endogenous: 2SLS next to OLS with HAC errors, first-stage F for weak instruments, Wu-Hausman for endogeneity, Sargan for over-identification. |
| `quantile_regress` | Regression at several quantiles next to OLS, to see whether the relation differs in the tails. |
| `principal_components` | Common factor across 2 to 8 series: explained variance, loadings, factor scores. |
| `panel_regress` | Fixed-effects, pooled and between regressions across countries on `UNIT|INDICATOR` datasets, clustered standard errors, F test for country effects. |
| `rolling` | Rolling mean, standard deviation, or correlation. |

The numerics are in `src/stats.ts`, dependency-free so they run on the Worker. Critical values are MacKinnon (1991) for the unit-root tests, MacKinnon-Haug-Michelis (1999) for the Johansen cases, and Andrews (1993) asymptotics for the sup-F test; the 10% and 1% Johansen columns for the restricted cases and the sup-F table are simulated from the limiting Brownian functionals (see the comments in `stats.ts`); p-values come from the t, F and chi-square distributions. `test/stats.test.mjs` checks each estimator against known answers on seeded data.

Resources: `econ://catalog` and `econ://dataset/{name}`.

## Connect

The endpoint is `https://<worker-host>/mcp` over Streamable HTTP. After `npm run deploy` the host is `econ-mcp.<your-subdomain>.workers.dev`.

- **Claude.ai**: Settings, Connectors, Add custom connector, paste the `/mcp` URL.
- **Claude Code**: `claude mcp add --transport http econ https://<worker-host>/mcp`
- **Clients that only speak stdio**: `npx mcp-remote https://<worker-host>/mcp`

If `MCP_API_KEYS` is set, add `--header "Authorization: Bearer <key>"` in Claude Code, or enter the key where the client asks.

### The question box on the website

`POST /v1/ask` with `{question, history?}` asks Claude Opus 5 with this server's tools attached (Anthropic's MCP connector calls `/mcp` server-side) and streams Anthropic's server-sent events straight back; `GET /v1/ask/quota` returns what the caller has left. `js/ask.js` on `explore.html` and `econ-mcp.html` is the page side. The owner pays per question, so a Durable Object (`AskQuota`, declared in `wrangler.jsonc`, nothing to create by hand) counts questions: 10 per visitor per day by hashed IP, 300 per day for the site, both in `src/ask.ts`. Past the limit the page points at the free route above. A question is capped at 4,000 output tokens and Anthropic's server-side tool loop stops at `pause_turn`, which the page reports rather than resuming. The box is off, and says so, until `ANTHROPIC_API_KEY` is set.

## Deploy

The Worker is connected to this repository through Cloudflare Workers Builds: every push to `main` that touches `mcp/` builds and deploys it (root directory `mcp`, deploy command `npx wrangler deploy`). Nothing to run by hand.

Variables and secrets live in the Worker's settings in the Cloudflare dashboard and survive deploys (`keep_vars` in `wrangler.jsonc`):

- `DATA_ORIGIN` (optional, defaults to the portfolio site)
- `EVDS_API_KEY` for TCMB EVDS pulls
- `FAOSTAT_USER` and `FAOSTAT_PASSWORD` for FAOSTAT (a free developer account at www.fao.org/faostat/en/#developer-portal; the API has required a login since 2025). The same two names as repository secrets let the fetch workflow refresh the `fao-*` datasets.
- `FRED_API_KEY` for FRED catalogue search
- `MCP_API_KEYS` comma-separated bearer tokens, when the server should not be open
- `ANTHROPIC_API_KEY` (Secret) switches on `/v1/ask`; set a monthly spend limit on the key in the Anthropic console as the wall the code cannot cross

Manual alternatives, should the git connection ever be off: `npm run deploy` after `npx wrangler login`, or paste `dist-bundle/econ-mcp.js` (regenerate with `npm run bundle`) into the Worker in the dashboard.

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
- Bayesian VAR with a Minnesota prior; cointegration with a break in the relation (Gregory-Hansen); Markov-switching regimes.
- IMF provider once its SDMX 3 endpoint settles; EIA and UN Comtrade with keys.
