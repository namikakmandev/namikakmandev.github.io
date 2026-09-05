/**
 * The MCP server: tools and resources over the published datasets.
 * Built fresh per request (stateless), so keep construction cheap.
 */
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  type Catalog, type CatalogEntry, type Json, DataError,
  asText, caveatsFor, datasetName, describeSeries, dig, extractSeries, loadCatalog, loadDataset, sourceFor,
} from "./data.js";
import { apply, clip, correlation, resample, round, toPoints, type Frequency, type Transform } from "./transform.js";
import { registerAnalysis, registerProviders } from "./analysis.js";
import type { ProviderEnv } from "./providers.js";

export const SERVER_NAME = "econ-data";
export const SERVER_VERSION = "0.2.0";

const RAW_LIMIT_BYTES = 200_000;

const TRANSFORM = z.enum(["none", "pct_change", "yoy", "diff", "rebase", "log"]).default("none")
  .describe("none = levels; pct_change = % vs previous observation; yoy = % vs same period a year earlier; diff = first difference; rebase = index, base date = 100; log = natural log");
const FREQUENCY = z.enum(["native", "annual_mean", "annual_last"]).default("native")
  .describe("native keeps the source frequency; annual_mean / annual_last collapse monthly data to years");

function text(obj: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(obj, null, 1) }] };
}

function fail(msg: string) {
  return { isError: true, content: [{ type: "text" as const, text: msg }] };
}

function entryFor(cat: Catalog, name: string): CatalogEntry | undefined {
  const file = `data/${datasetName(name)}.json`;
  return cat.datasets.find((d) => d.file === file);
}

function summary(e: CatalogEntry) {
  return {
    dataset: datasetName(e.file),
    shape: e.shape,
    series: e.series,
    observations: e.observations,
    coverage: e.coverage,
    source: asText(e.source),
    note: e.note,
    provenance: e.provenance,
    auto_refresh: e.auto_refresh,
    last_commit: e.last_commit,
    series_keys: e.series_keys?.slice(0, 20),
  };
}

export function buildServer(origin: string, env: ProviderEnv = {}): McpServer {
  const server = new McpServer(
    { name: SERVER_NAME, version: SERVER_VERSION },
    {
      instructions:
        "Economics data and analysis. Two kinds of data: curated datasets at namikakmandev.github.io " +
        "(list_datasets, search_datasets, describe_dataset, get_series) and live pulls from FRED, Eurostat, " +
        "World Bank, ECB, OECD, Our World in Data and TCMB EVDS (list_providers, search_external, fetch_external). " +
        "Analysis tools (describe_stats, test_stationarity, regress, granger_causality, cointegration, " +
        "cross_correlation, hp_filter, decompose, forecast, structural_break, rolling) all take series references: " +
        "{dataset, series}, {provider, id}, or {points}. Call suggest_analysis first when unsure which method fits; " +
        "it checks integration order, seasonality and overlap and returns an ordered plan. Every result carries " +
        "source and caveats: quote them next to the number.",
    },
  );

  const wrap = <A extends unknown[], R>(fn: (...a: A) => Promise<R>) => async (...a: A) => {
    try {
      return await fn(...a);
    } catch (e) {
      if (e instanceof DataError) return fail(e.message);
      throw e;
    }
  };

  server.registerTool(
    "list_datasets",
    {
      title: "List datasets",
      description: "Every dataset in the catalog with shape, coverage, source, caveat note and provenance. Filter by provenance to see only the ones that refresh on a schedule.",
      inputSchema: {
        provenance: z.enum(["all", "pipeline", "script", "manual", "unattributed"]).default("all")
          .describe("pipeline = fetched on a schedule; script = built by a repo script, run by hand; manual = pulled by hand; unattributed = nothing claims it"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ provenance }) => {
      const cat = await loadCatalog(origin);
      const rows = cat.datasets
        .filter((d) => !d.error && (provenance === "all" || d.provenance === provenance))
        .map(summary);
      return text({ generated_by: cat.generated_by, totals: cat.totals, datasets: rows });
    }),
  );

  server.registerTool(
    "search_datasets",
    {
      title: "Search datasets",
      description: "Keyword search over dataset names, sources, notes and top-level series keys (country codes, series names). Returns the best matches.",
      inputSchema: {
        query: z.string().min(1).describe("Words to look for, e.g. 'cattle parity', 'HICP', 'TR pharma'"),
        limit: z.number().int().min(1).max(50).default(10),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ query, limit }) => {
      const cat = await loadCatalog(origin);
      const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
      const scored = cat.datasets
        .filter((d) => !d.error)
        .map((d) => {
          const name = datasetName(d.file).toLowerCase();
          const hay = [name, asText(d.source), d.note, d.producer, d.provider, ...(d.series_keys ?? [])]
            .filter(Boolean).join(" ").toLowerCase();
          let score = 0;
          for (const t of terms) {
            if (name.includes(t)) score += 3;
            if (d.series_keys?.some((k) => k.toLowerCase() === t)) score += 2;
            if (hay.includes(t)) score += 1;
          }
          return { d, score };
        })
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score || (b.d.observations ?? 0) - (a.d.observations ?? 0))
        .slice(0, limit);
      if (!scored.length) return text({ query, matches: [], hint: "Nothing matched. Try list_datasets for the full catalog." });
      return text({ query, matches: scored.map((x) => ({ score: x.score, ...summary(x.d) })) });
    }),
  );

  server.registerTool(
    "describe_dataset",
    {
      title: "Describe dataset",
      description: "Catalog entry plus every series id the dataset exposes, with its date range. Use the ids with get_series and compare_series.",
      inputSchema: { dataset: z.string().describe("Dataset name, e.g. 'us-prices' or 'cattle-parity'") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ dataset }) => {
      const [cat, body] = await Promise.all([loadCatalog(origin), loadDataset(origin, dataset)]);
      const entry = entryFor(cat, dataset);
      const series = describeSeries(extractSeries(body));
      return text({
        dataset: datasetName(dataset),
        catalog: entry ? summary(entry) : null,
        source: sourceFor(entry, body),
        caveats: caveatsFor(entry, body),
        series_count: series.length,
        series,
        hint: series.length ? undefined : "No date-keyed series found. Use get_dataset to read the raw structure.",
      });
    }),
  );

  server.registerTool(
    "get_series",
    {
      title: "Get series",
      description: "One series as [date, value] points, optionally windowed, resampled and transformed. Series ids come from describe_dataset (e.g. 'cattle_ppi', 'US.parity_idx', 'DE.share_gdp').",
      inputSchema: {
        dataset: z.string(),
        series: z.string().describe("Series id from describe_dataset"),
        start: z.string().optional().describe("Inclusive, same format as the series dates: '2015' or '2015-01'"),
        end: z.string().optional().describe("Inclusive"),
        last_n: z.number().int().min(1).max(5000).optional().describe("Keep only the last N observations"),
        frequency: FREQUENCY,
        transform: TRANSFORM,
        base: z.string().optional().describe("Base date for transform=rebase; default is the first date in the window"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ dataset, series, start, end, last_n, frequency, transform, base }) => {
      const [cat, body] = await Promise.all([loadCatalog(origin), loadDataset(origin, dataset)]);
      const all = extractSeries(body);
      const s = all.get(series);
      if (!s) return fail(`No series '${series}' in ${dataset}. Available: ${[...all.keys()].slice(0, 40).join(", ")}${all.size > 40 ? ", ..." : ""}`);
      const entry = entryFor(cat, dataset);
      // Window first so transforms see the full history they need (yoy needs the prior year).
      let out = clip(s, start ? yearEarlier(start, transform) : undefined, end);
      out = resample(out, frequency as Frequency);
      out = apply(out, transform as Transform, base);
      out = clip(out, start, end, last_n);
      const pts = toPoints(round(out));
      return text({
        dataset: datasetName(dataset),
        series,
        source: sourceFor(entry, body),
        caveats: caveatsFor(entry, body),
        frequency, transform,
        unit_hint: transform === "pct_change" || transform === "yoy" ? "percent" : transform === "rebase" ? `index, ${base ?? pts[0]?.[0]} = 100` : "as published",
        n: pts.length,
        first: pts[0]?.[0] ?? null,
        last: pts[pts.length - 1]?.[0] ?? null,
        points: pts,
      });
    }),
  );

  server.registerTool(
    "compare_series",
    {
      title: "Compare two series",
      description: "Align two series on the dates they share and return them side by side with a ratio. Reports correlation of levels and of year-on-year changes; the second is the one that means something for trending series.",
      inputSchema: {
        a: z.object({ dataset: z.string(), series: z.string() }),
        b: z.object({ dataset: z.string(), series: z.string() }),
        start: z.string().optional(),
        end: z.string().optional(),
        frequency: FREQUENCY,
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ a, b, start, end, frequency }) => {
      const cat = await loadCatalog(origin);
      const [ba, bb] = await Promise.all([loadDataset(origin, a.dataset), loadDataset(origin, b.dataset)]);
      const sa = extractSeries(ba).get(a.series);
      const sb = extractSeries(bb).get(b.series);
      if (!sa) return fail(`No series '${a.series}' in ${a.dataset}`);
      if (!sb) return fail(`No series '${b.series}' in ${b.dataset}`);
      const f = frequency as Frequency;
      const xa = resample(clip(sa, start, end), f);
      const xb = resample(clip(sb, start, end), f);
      const dates = Object.keys(xa).filter((k) => k in xb).sort();
      if (!dates.length) return fail("The two series share no dates. Check their frequencies (use frequency=annual_mean to align monthly with annual) and windows.");
      const rows = dates.map((d) => [d, xa[d], xb[d], xb[d] !== 0 ? Math.round((xa[d] / xb[d]) * 10000) / 10000 : null]);
      const ya = apply(xa, "yoy"), yb = apply(xb, "yoy");
      return text({
        a: { ...a, source: sourceFor(entryFor(cat, a.dataset), ba), caveats: caveatsFor(entryFor(cat, a.dataset), ba) },
        b: { ...b, source: sourceFor(entryFor(cat, b.dataset), bb), caveats: caveatsFor(entryFor(cat, b.dataset), bb) },
        frequency,
        n: rows.length,
        first: dates[0], last: dates[dates.length - 1],
        correlation_levels: correlation(xa, xb),
        correlation_yoy: correlation(ya, yb),
        reading: "Two series that both trend will correlate in levels whatever the relation between them. Judge co-movement on correlation_yoy, and only after reading the caveats.",
        columns: ["date", "a", "b", "a_over_b"],
        rows,
      });
    }),
  );

  server.registerTool(
    "get_caveats",
    {
      title: "Get caveats",
      description: "Everything that travels with a dataset that an honest chart would mention: source, method notes, survey breaks, refresh status, provenance.",
      inputSchema: { dataset: z.string() },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ dataset }) => {
      const [cat, body] = await Promise.all([loadCatalog(origin), loadDataset(origin, dataset)]);
      const entry = entryFor(cat, dataset);
      return text({
        dataset: datasetName(dataset),
        source: sourceFor(entry, body),
        caveats: caveatsFor(entry, body),
        provenance: entry?.provenance ?? "unknown",
        producer: entry?.producer ?? null,
        auto_refresh: entry?.auto_refresh ?? false,
        last_commit: entry?.last_commit ?? null,
        fetched_at: (body && typeof body === "object" && !Array.isArray(body) && typeof body.fetched_at === "string") ? body.fetched_at : null,
      });
    }),
  );

  server.registerTool(
    "get_dataset",
    {
      title: "Get raw dataset",
      description: "The dataset file as published, or a sub-tree of it via a dot path (e.g. 'regions.US' or 'meta'). For anything that is not a plain series. Large files must be narrowed with a path.",
      inputSchema: {
        dataset: z.string(),
        path: z.string().optional().describe("Dot path into the JSON, e.g. 'config', 'regions.US.columns', 'observations.0'"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ dataset, path }) => {
      const body = await loadDataset(origin, dataset);
      const sub: Json = path ? dig(body, path) : body;
      const s = JSON.stringify(sub);
      if (s.length > RAW_LIMIT_BYTES) {
        const keys = sub && typeof sub === "object" && !Array.isArray(sub) ? Object.keys(sub) : [];
        return fail(`That is ${Math.round(s.length / 1024)} KB, over the ${RAW_LIMIT_BYTES / 1000} KB limit. Narrow it with a path. Keys here: ${keys.slice(0, 40).join(", ")}${Array.isArray(sub) ? ` (array of ${sub.length})` : ""}. Or use describe_dataset and get_series.`);
      }
      return { content: [{ type: "text" as const, text: s }] };
    }),
  );

  server.registerResource(
    "catalog",
    "econ://catalog",
    { title: "Dataset catalog", description: "Index of every dataset, as JSON", mimeType: "application/json" },
    async (uri) => ({ contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(await loadCatalog(origin)) }] }),
  );

  server.registerResource(
    "dataset",
    new ResourceTemplate("econ://dataset/{name}", {
      list: async () => {
        const cat = await loadCatalog(origin);
        return {
          resources: cat.datasets.filter((d) => !d.error).map((d) => ({
            uri: `econ://dataset/${datasetName(d.file)}`,
            name: datasetName(d.file),
            description: asText(d.source) ?? undefined,
            mimeType: "application/json",
          })),
        };
      },
    }),
    { title: "Dataset file", description: "One dataset as published", mimeType: "application/json" },
    async (uri, { name }) => {
      const body = await loadDataset(origin, String(name));
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(body) }] };
    },
  );

  registerProviders(server, env);
  registerAnalysis(server, origin, env);

  return server;
}

/** For yoy the window must start a year earlier so the first point has a comparator. */
function yearEarlier(start: string, transform: string): string {
  if (transform !== "yoy") return start;
  return String(Number(start.slice(0, 4)) - 1).padStart(4, "0") + start.slice(4);
}
