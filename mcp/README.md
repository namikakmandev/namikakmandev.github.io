# econ-mcp

A remote [MCP](https://modelcontextprotocol.io) server over the economics datasets published in this repo's `data/` directory. Any MCP client (Claude.ai, Claude Code, Claude Desktop, Cursor, ChatGPT) can connect and pull the series, with the caveats attached.

The server holds no data. It reads the JSON files that GitHub Pages already serves from `https://namikakmandev.github.io/data/`, so every scheduled refresh in `.github/workflows/` reaches MCP clients with no redeploy. The catalog it indexes is `data/_catalog.json`, rebuilt by `scripts/build_catalog.py` on the same schedule.

## Tools

| Tool | What it does |
|---|---|
| `list_datasets` | Every dataset with shape, coverage, source, note, provenance. Filter by provenance. |
| `search_datasets` | Keyword search over names, sources, notes and top-level series keys. |
| `describe_dataset` | Catalog entry plus every series id the file exposes, with date ranges. |
| `get_series` | One series as `[date, value]` points. Window, `last_n`, annual resampling, and transforms: `pct_change`, `yoy`, `diff`, `rebase`, `log`. |
| `compare_series` | Two series aligned on shared dates, with ratio and correlation of levels and of year-on-year changes. |
| `get_caveats` | Source, method notes, survey breaks, refresh status and provenance for a dataset. |
| `get_dataset` | The raw file, or a sub-tree by dot path, for anything that is not a plain series. |

Resources: `econ://catalog` and `econ://dataset/{name}`.

Series ids follow the file layout. A `fetch.py` file exposes its series keys (`cattle_ppi`), a table exposes its columns (`parity_cattle_over_corn`), a regions file exposes `region.column` (`US.parity_idx`), and a country-by-year record file exposes `country.field` (`DE.share_gdp`). Ask `describe_dataset` when unsure.

Every answer from `get_series` and `compare_series` carries the dataset's caveats. That is the point of the server: a model that asks for numbers gets the warnings in the same reply.

## Connect

The endpoint is `https://<worker-host>/mcp` over Streamable HTTP. After `npm run deploy` the host is `econ-mcp.<your-subdomain>.workers.dev`.

- **Claude.ai**: Settings, Connectors, Add custom connector, paste the `/mcp` URL.
- **Claude Code**: `claude mcp add --transport http econ https://<worker-host>/mcp`
- **Claude Desktop / clients that only speak stdio**: `npx mcp-remote https://<worker-host>/mcp`

If `MCP_API_KEYS` is set, add `--header "Authorization: Bearer <key>"` in Claude Code, or enter the key where the client asks for one.

## Deploy

```bash
cd mcp
npm install
npx wrangler login          # once
npm run deploy
```

Free Cloudflare Workers tier is enough: no storage, no Durable Objects, one stateless request per tool call.

Optional bearer auth, kept out of git:

```bash
npx wrangler secret put MCP_API_KEYS    # comma-separated tokens
```

## Develop and test

```bash
npm test          # builds, then runs a real MCP client against the Worker with data/ served locally
npm run dev:node  # same server on http://127.0.0.1:8787/mcp, data from the local checkout
npm run dev       # wrangler dev, data from the live site
```

`test/e2e.mjs` covers each layout in `data/`, the transforms, the size guard on raw reads, auth, and resources. It also lists which files expose no series, which is expected for maps, forecast archives and probe reports.

## Layout rules the server relies on

- Date keys are `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-Qn` or `YYYY-Sn`. Anything else is raw only.
- A table is `{"columns": [...], "rows": [[date, ...], ...]}`; a list of rows needs `meta.columns`.
- Top-level `source`, `note`, `config.note`, `meta.construction` and `scope_note` are surfaced as caveats.
- Files starting with `_` are probes and are not catalogued.

## Next steps toward a paid tier

1. Replace the bearer check in `src/index.ts` with OAuth 2.1 (Cloudflare's `workers-oauth-provider`), which is what Claude.ai connectors expect for per-user accounts.
2. Meter or gate tools with Stripe's agent toolkit for Cloudflare MCP servers.
3. Move heavy files to R2 and keep GitHub Pages as the free tier.
