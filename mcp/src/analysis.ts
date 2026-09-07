/**
 * Tool registrations: live providers and the analysis layer.
 * Every analysis tool takes SeriesRef inputs (see resolve.ts), so a user can
 * point it at a local dataset, a live FRED or Eurostat pull, or their own
 * numbers, and gets the source and caveats echoed back with the result.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DataError, type Series, caveatsFor, datasetName, extractSeries, loadCatalog, loadDataset, sourceFor } from "./data.js";
import { PROVIDERS, providerInfo, type ProviderEnv } from "./providers.js";
import { SeriesRefSchema, align, detectFrequency, futureDates, resolve, type Resolved, type SeriesRef } from "./resolve.js";
import { apply, clip, round, toPoints, type Transform } from "./transform.js";
import * as S from "./stats.js";
import { SERVER_BUILD } from "./version.js";
import { BandSchema, chartUrl, type Band, type PlotSpec } from "./api.js";

const r4 = (x: number) => (Number.isFinite(x) ? Math.round(x * 10000) / 10000 : null);
const r3 = (x: number) => (Number.isFinite(x) ? Math.round(x * 1000) / 1000 : null);

function text(obj: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(obj, null, 1) }] };
}
function fail(msg: string) {
  return { isError: true, content: [{ type: "text" as const, text: msg }] };
}
const wrap = <A extends unknown[], R>(fn: (...a: A) => Promise<R>) => async (...a: A) => {
  try { return await fn(...a); }
  catch (e) {
    if (e instanceof DataError || e instanceof Error) return fail(e.message);
    throw e;
  }
};

function meta(r: Resolved) {
  return { label: r.label, source: r.source, transform: r.transform, caveats: r.caveats };
}

function values(s: Series): { dates: string[]; v: number[] } {
  const dates = Object.keys(s).sort();
  return { dates, v: dates.map((d) => s[d]) };
}

function defaultLambda(period: number, freq: string): number {
  if (freq === "annual") return 100;
  if (freq === "quarterly") return 1600;
  if (freq === "monthly") return 129600;
  if (freq === "daily" || freq === "weekly") return 1e7;
  return period === 4 ? 1600 : 100;
}

/**
 * An inline chart series built from numbers this server computed (a fitted line, a
 * residual, an impulse response). Non-finite points drop out; a long series is thinned
 * so the link stays a link, keeping the first and last observation.
 */
const CHART_PTS = 400;
function inline(label: string, xs: Array<string | number>, vals: Array<number | null | undefined>): SeriesRef {
  const all: [string, number][] = [];
  xs.forEach((d, i) => { const x = vals[i]; if (typeof x === "number" && Number.isFinite(x)) all.push([String(d), x]); });
  if (all.length <= CHART_PTS) return { points: all, label };
  const step = (all.length - 1) / (CHART_PTS - 1), thin: [string, number][] = [];
  for (let i = 0; i < CHART_PTS; i++) thin.push(all[Math.round(i * step)]);
  thin[thin.length - 1] = all[all.length - 1];
  return { points: thin, label };
}
/** A shaded band on one of those series, from the same x values. */
function inlineBand(series: number, label: string, xs: Array<string | number>, lo: Array<number | null | undefined>, hi: Array<number | null | undefined>): Band {
  const all: [string, number, number][] = [];
  xs.forEach((d, i) => { const a = lo[i], b = hi[i]; if (typeof a === "number" && typeof b === "number" && Number.isFinite(a) && Number.isFinite(b)) all.push([String(d), a, b]); });
  if (all.length <= CHART_PTS) return { series, label, points: all };
  const step = (all.length - 1) / (CHART_PTS - 1), thin: [string, number, number][] = [];
  for (let i = 0; i < CHART_PTS; i++) thin.push(all[Math.round(i * step)]);
  thin[thin.length - 1] = all[all.length - 1];
  return { series, label, points: thin };
}
/** A flat reference line (a critical value, an unconditional level) across the same x range. */
function refLine(label: string, xs: Array<string | number>, level: number): SeriesRef {
  const ends = xs.length ? [xs[0], xs[xs.length - 1]] : [];
  return inline(label, ends, ends.map(() => level));
}
/** Horizons as fixed-width strings so a numeric x axis sorts them in order. */
const hx = (h: number) => String(h).padStart(2, "0");

function pointsOut(dates: string[], v: Array<number | null>): Array<[string, number | null]> {
  return dates.map((d, i) => [d, v[i] === null || v[i] === undefined ? null : (r4(v[i] as number) as number)]);
}

/** Quick profile used by describe_stats and suggest_analysis. */
function profile(r: Resolved) {
  const { dates, v } = values(r.series);
  const n = v.length;
  const { frequency, period } = detectFrequency(dates);
  const out: Record<string, unknown> = {
    n, first: dates[0], last: dates[n - 1], frequency,
    mean: r4(S.mean(v)), sd: n > 1 ? r4(S.sd(v)) : null, min: r4(Math.min(...v)), max: r4(Math.max(...v)),
    median: r4(S.quantile(v, 0.5)), q25: r4(S.quantile(v, 0.25)), q75: r4(S.quantile(v, 0.75)),
    skewness: n > 3 ? r3(S.skewness(v)) : null, kurtosis: n > 3 ? r3(S.kurtosis(v)) : null,
    positive_only: v.every((x) => x > 0),
  };
  if (n >= 20) {
    const lags = Math.min(period > 1 ? period : 10, Math.floor(n / 4));
    out.acf = Array.from({ length: lags }, (_, i) => r3(S.autocorr(v, i + 1)));
    out.ljung_box = (() => { const lb = S.ljungBox(v, lags); return { Q: r3(lb.Q), p: r4(lb.p), lags }; })();
    out.jarque_bera = (() => { const jb = S.jarqueBera(v); return { JB: r3(jb.JB), p: r4(jb.p) }; })();
  }
  let adfLevel: S.AdfResult | null = null, adfDiff: S.AdfResult | null = null;
  if (n >= 20) {
    try { adfLevel = S.adf(v, "c"); } catch { /* too short */ }
    try { adfDiff = S.adf(S.diff(v), "c"); } catch { /* too short */ }
  }
  let decomposition: S.Decomposition | null = null;
  if (period > 1 && n >= 3 * period) {
    try { decomposition = S.decompose(v, period); } catch { /* skip */ }
  }
  const trendFit = n >= 8 ? S.ols(v, v.map((_, i) => [1, i])) : null;
  return { dates, v, n, frequency, period, summary: out, adfLevel, adfDiff, decomposition, trendFit };
}

/** ARCH-LM on the series' own returns (log differences when positive, plain differences otherwise). */
function archProbe(v: number[]): { statistic: number; p: number; lags: number } | null {
  if (v.length < 60) return null;
  const pos = v.every((x) => x > 0);
  const r: number[] = [];
  for (let i = 1; i < v.length; i++) {
    const x = pos ? Math.log(v[i] / v[i - 1]) * 100 : v[i] - v[i - 1];
    if (Number.isFinite(x)) r.push(x);
  }
  if (r.length < 60) return null;
  try { return S.archLM(r, Math.min(5, Math.floor(r.length / 10))); } catch { return null; }
}

/**
 * Which season the first observation falls in, for labelling seasonal factors.
 * Handles 'YYYY-Qn', 'YYYY-MM', 'YYYY-MM-DD' and 'YYYY'; anything else starts at 0.
 */
function seasonOffset(first: string, period: number): number {
  let m: RegExpMatchArray | null;
  if ((m = /^\d{4}-Q([1-4])$/.exec(first))) return period === 4 ? Number(m[1]) - 1 : 0;
  if ((m = /^\d{4}-(\d{2})(?:-\d{2})?$/.exec(first))) {
    const month = Number(m[1]);
    if (period === 12) return month - 1;
    if (period === 4) return Math.floor((month - 1) / 3);
    if (period === 2) return Math.floor((month - 1) / 6);
  }
  return 0;
}

function adfOut(a: S.AdfResult | null) {
  if (!a) return null;
  return { spec: a.spec, lags: a.lags, nobs: a.nobs, statistic: r3(a.statistic), critical: { "1%": r3(a.critical["1%"]), "5%": r3(a.critical["5%"]), "10%": r3(a.critical["10%"]) }, reject_unit_root_at: a.reject_unit_root_at };
}

/** Which Johansen deterministic case the data support: series that drift need the unrestricted constant. */
function driftCheck(labels: string[], columns: number[][], chosen: "constant" | "restricted_constant" | "restricted_trend") {
  const rows = labels.map((l, i) => { const t = S.driftT(columns[i]); return { series: l, drift_t: r3(t), drifts: Math.abs(t) > 2 }; });
  const drifting = rows.filter((r) => r.drifts).map((r) => r.series);
  const suggested = drifting.length ? "constant" : "restricted_constant";
  const note = chosen === "restricted_trend"
    ? (drifting.length ? "Drift check: the series drift, so a trend inside the relation is admissible; keep it only if its coefficient in vecm is clearly non-zero, otherwise deterministic='constant' has more power." : "Drift check: none of the series drifts, so there is no trend for the relation to absorb; deterministic='restricted_constant' is the better-specified test.")
    : suggested === chosen ? "" : chosen === "constant"
    ? "Drift check: none of the series has a significant drift, so deterministic='restricted_constant' is the better-specified test here (the unrestricted constant over-rejects on drift-free series)."
    : `Drift check: ${drifting.join(", ")} drift${drifting.length === 1 ? "s" : ""} significantly, so deterministic='constant' fits the data better than the restricted constant.`;
  return { per_series: rows, suggested, note };
}

function integrationOrder(level: S.AdfResult | null, first: S.AdfResult | null): "I(0)" | "I(1)" | "I(2) or worse" | "unknown" {
  if (!level) return "unknown";
  if (level.reject_unit_root_at) return "I(0)";
  if (first?.reject_unit_root_at) return "I(1)";
  if (first) return "I(2) or worse";
  return "unknown";
}

export function registerProviders(server: McpServer, env: ProviderEnv) {
  server.registerTool(
    "list_providers",
    {
      title: "List live data providers",
      description: "External sources the server can pull from on demand (FRED, Eurostat, World Bank, ECB, OECD, Our World in Data, TCMB EVDS, BIS, FAOSTAT, IMF): coverage, id format, whether a key is configured, and starter ids.",
      inputSchema: {},
      annotations: { readOnlyHint: true },
    },
    wrap(async () => text({ server_build: SERVER_BUILD, providers: providerInfo(env), how: "search_external to find an id, fetch_external to pull it, or pass {provider, id} straight into any analysis tool." })),
  );

  server.registerTool(
    "search_external",
    {
      title: "Search a live provider",
      description: "Find series ids at a provider. FRED searches its full catalogue when FRED_API_KEY is set; World Bank searches all indicators; EVDS walks the TCMB catalogue when EVDS_API_KEY is set; FAOSTAT searches its item, area and element lists; the others match against a curated starter list, so for those also try the provider's own website and pass the id to fetch_external.",
      inputSchema: {
        provider: z.enum(["fred", "eurostat", "worldbank", "ecb", "oecd", "owid", "evds", "bis", "fao", "imf", "weather", "sec"]),
        query: z.string().min(1),
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    wrap(async ({ provider, query }) => {
      const p = PROVIDERS[provider];
      const hits = p.search ? await p.search(query, env) : [];
      return text({ provider, query, id_format: p.id_format, matches: hits.slice(0, 25), hint: hits.length ? undefined : `No match in the starter list. Any valid ${p.title} id still works with fetch_external.` });
    }),
  );

  server.registerTool(
    "fetch_external",
    {
      title: "Fetch from a live provider",
      description: "Pull a series from FRED, Eurostat, World Bank, ECB, OECD, Our World in Data, TCMB EVDS, BIS, FAOSTAT or IMF as [date, value] points, with the same window and transform options as get_series. When the id returns several series (countries, dimensions), the reply lists their keys; pick one with 'series'.",
      inputSchema: {
        provider: z.enum(["fred", "eurostat", "worldbank", "ecb", "oecd", "owid", "evds", "bis", "fao", "imf", "weather", "sec"]),
        id: z.string(),
        params: z.record(z.string(), z.string()).optional().describe("Provider filters. Eurostat: dimension codes (geo, unit, ...). World Bank: country='TUR;USA' or 'all'. OWID: entities='Turkey;United States'. EVDS/ECB/OECD: start, end. FAOSTAT: area, item, element, year (codes; several separated by commas). IMF: start, end, version."),
        series: z.string().optional().describe("Which series key to return when the id yields several"),
        start: z.string().optional(),
        end: z.string().optional(),
        last_n: z.number().int().min(1).max(5000).optional(),
        frequency: z.enum(["native", "annual_mean", "annual_last"]).default("native"),
        transform: z.enum(["none", "pct_change", "yoy", "diff", "rebase", "log"]).default("none"),
        base: z.string().optional(),
      },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    wrap(async ({ provider, id, params, series, start, end, last_n, frequency, transform, base }) => {
      const p = PROVIDERS[provider];
      const res = await p.fetch(id, params ?? {}, env);
      const keys = Object.keys(res.series);
      if (!series && keys.length !== 1) {
        return text({
          provider, id, source: res.source, notes: res.notes,
          series_count: keys.length,
          series: keys.slice(0, 200).map((k) => { const d = Object.keys(res.series[k]).sort(); return { key: k, n: d.length, first: d[0], last: d[d.length - 1] }; }),
          hint: "Call again with 'series' set to one of these keys, or narrow with params.",
        });
      }
      const r = await resolve({ provider, id, params, series, start, end, frequency, transform, base }, "", env);
      let pts = toPoints(round(r.series));
      if (last_n) pts = pts.slice(-last_n);
      return text({ ...meta(r), provider, id, series: series ?? keys[0], url: res.url, frequency, n: pts.length, first: pts[0]?.[0], last: pts[pts.length - 1]?.[0], points: pts });
    }),
  );
}

/**
 * Every analysis tool, captured as it is registered, so the same handler serves
 * both MCP and the plain HTTP endpoint at /v1/analyze. The zod shape validates
 * the arguments in both directions.
 */
export interface AnalysisTool {
  name: string;
  title: string;
  description: string;
  shape: z.ZodRawShape;
  run: (args: Record<string, unknown>) => Promise<{ isError?: boolean; content: Array<{ type: "text"; text: string }> }>;
}

/** Build the toolkit against one origin and environment, without an MCP server. */
export function analysisTools(origin: string, env: ProviderEnv, self?: string): Map<string, AnalysisTool> {
  const out = new Map<string, AnalysisTool>();
  const sink = {
    registerTool(name: string, def: { title?: string; description?: string; inputSchema?: z.ZodRawShape }, handler: (args: never) => unknown) {
      out.set(name, {
        name, title: def.title ?? name, description: def.description ?? "",
        shape: def.inputSchema ?? {},
        run: handler as AnalysisTool["run"],
      });
    },
  } as unknown as McpServer;
  registerAnalysis(sink, origin, env, self);
  return out;
}

export function registerAnalysis(server: McpServer, origin: string, env: ProviderEnv, self?: string) {
  const get = (ref: SeriesRef) => resolve(ref, origin, env);
  const REF = SeriesRefSchema.describe("Series reference: {dataset, series} for local data, {provider, id[, series, params]} for live data, or {points} for inline data. Optional start, end, frequency, transform.");

  server.registerTool(
    "plot",
    {
      title: "Plot series",
      description: "Draw up to 8 series on one interactive chart and return its link. The page shows hover values, log and rebase-to-100 toggles, a right-hand axis for series on another scale, shaded bands (forecast intervals, confidence bands), the sources and caveats, a data table and CSV download. forecast and local_projections return a ready chart_url of their own. Every series is resolved first, so a bad reference fails here rather than on the page. Give the user the chart_url.",
      inputSchema: {
        series: z.array(REF).min(1).max(8),
        title: z.string().max(200).optional().describe("Chart title; default is built from the series labels"),
        scale: z.enum(["linear", "log"]).default("linear"),
        right_axis: z.array(z.number().int().min(0).max(7)).optional().describe("0-based indexes of series to draw on a right-hand axis, for series whose units differ"),
        bands: z.array(BandSchema).max(4).optional().describe("Shaded bands, e.g. a forecast interval: [[date, low, high], ...] attached to a series by index"),
        xaxis: z.enum(["date", "number"]).default("date").describe("number when the x values are horizons or indexes (zero-padded strings such as '00', '01')"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, title, scale, right_axis, bands, xaxis }) => {
      const rs = await Promise.all(series.map(get));
      const badBand = (bands ?? []).find((b) => b.series >= series.length);
      if (badBand) return fail(`Band '${badBand.label ?? ""}' refers to series ${badBand.series}, but only ${series.length} series were given.`);
      const spec: PlotSpec = { series, title, scale, right: right_axis?.length ? right_axis : undefined, bands: bands?.length ? bands : undefined, xaxis: xaxis === "number" ? "number" : undefined, api: self };
      const url = chartUrl(origin, spec);
      return text({
        chart_url: url,
        how: "Open chart_url in a browser. The link carries the series references, not the numbers, so it stays current when the data refreshes. Share it as is.",
        series: rs.map((r) => {
          const pts = toPoints(r.series);
          return { label: r.label, transform: r.transform, n: pts.length, first: pts[0]?.[0], last: pts[pts.length - 1]?.[0], last_value: r4(pts[pts.length - 1]?.[1] ?? NaN), source: r.source, caveats: r.caveats };
        }),
        note: scale === "log" ? "Log scale: a straight line means constant growth; needs every value positive." : undefined,
      });
    }),
  );

  server.registerTool(
    "describe_stats",
    {
      title: "Descriptive statistics",
      description: "Summary statistics, autocorrelations, Ljung-Box and Jarque-Bera tests, a unit-root check on levels and first differences, and seasonal/trend strength where the frequency allows. A good first call before any modelling.",
      inputSchema: { series: REF },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series }) => {
      const r = await get(series);
      const p = profile(r);
      return text({
        ...meta(r), ...p.summary,
        chart_url: chartUrl(origin, { series: [series], title: r.label, api: self }),
        unit_root: { levels: adfOut(p.adfLevel), first_difference: adfOut(p.adfDiff), integration_order: integrationOrder(p.adfLevel, p.adfDiff) },
        linear_trend: p.trendFit ? { slope_per_period: r4(p.trendFit.beta[1]), t: r3(p.trendFit.t[1]), r2: r3(p.trendFit.r2) } : null,
        seasonality: p.decomposition ? { period: p.period, seasonal_strength: r3(p.decomposition.seasonal_strength), trend_strength: r3(p.decomposition.trend_strength), factors: p.decomposition.seasonal_factors.map(r3) } : null,
      });
    }),
  );

  server.registerTool(
    "test_stationarity",
    {
      title: "Unit root test (ADF)",
      description: "Augmented Dickey-Fuller test on levels and first differences with MacKinnon critical values, returning the integration order. Lag length by AIC unless given. spec: c = constant, ct = constant and trend, n = neither.",
      inputSchema: {
        series: REF,
        spec: z.enum(["c", "ct", "n"]).default("c"),
        lags: z.number().int().min(0).max(24).optional(),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, spec, lags }) => {
      const r = await get(series);
      const { v } = values(r.series);
      const level = S.adf(v, spec, lags ?? "auto");
      let first: S.AdfResult | null = null;
      try { first = S.adf(S.diff(v), spec === "ct" ? "c" : spec, lags ?? "auto"); } catch { /* short */ }
      const order = integrationOrder(level, first);
      const kp = S.kpss(v, spec === "ct" ? "ct" : "c");
      const kpssOut = { trend: kp.trend, lags: kp.lags, statistic: r3(kp.statistic), critical: kp.critical, reject_stationarity_at: kp.reject_stationarity_at,
        null_hypothesis: "The series is stationary. Rejecting means a unit root." };
      const adfSaysStationary = !!level.reject_unit_root_at, kpssSaysStationary = !kp.reject_stationarity_at;
      const joint = adfSaysStationary && kpssSaysStationary ? "Both tests agree: stationary."
        : !adfSaysStationary && !kpssSaysStationary ? "Both tests agree: unit root."
        : adfSaysStationary ? "ADF rejects a unit root but KPSS rejects stationarity: borderline, often a near-unit-root or a structural break. Check structural_break."
        : "Neither test rejects: the sample is too short or the series is too noisy to tell.";
      return text({
        ...meta(r), n: v.length, levels: adfOut(level), first_difference: adfOut(first), kpss: kpssOut, joint_reading: joint, integration_order: order,
        reading: order === "I(0)" ? "Stationary in levels: regress and correlate on levels."
          : order === "I(1)" ? "Unit root in levels, stationary after differencing. Use differences or growth rates for regression and correlation, or test for cointegration before regressing levels on levels."
          : order === "I(2) or worse" ? "Still non-stationary after one difference. Check for a trend break or take logs before differencing." : "Too short to say.",
        null_hypothesis: "The series has a unit root. Rejecting means stationary.",
      });
    }),
  );

  server.registerTool(
    "regress",
    {
      title: "OLS regression",
      description: "Regress y on one or more x series, aligned on shared dates. Newey-West robust standard errors, R², Durbin-Watson, AIC/BIC, residual tests, Breusch-Pagan for heteroskedasticity, VIF for collinearity, RESET for functional form, and a spurious-regression warning when levels are non-stationary. Set transform='log' on y and x for elasticities. Add lags of x for a distributed-lag model.",
      inputSchema: {
        y: REF,
        x: z.array(REF).min(1).max(8),
        x_lags: z.number().int().min(0).max(12).default(0).describe("Include lags 1..k of every x"),
        trend: z.boolean().default(false).describe("Add a linear time trend"),
        hac_lags: z.number().int().min(0).max(24).optional().describe("Newey-West bandwidth; default 4(n/100)^(2/9)"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ y, x, x_lags, trend, hac_lags }) => {
      const ry = await get(y);
      const rx = await Promise.all(x.map(get));
      const { dates, columns } = align([ry.series, ...rx.map((r) => r.series)]);
      if (dates.length < 8) return fail(`Only ${dates.length} shared dates between the series. Check frequencies (use frequency='annual_mean' to align monthly with annual) and windows.`);
      const names = ["const"];
      const rows: number[][] = [];
      const yv: number[] = [];
      for (let t = x_lags; t < dates.length; t++) {
        const row = [1];
        rx.forEach((r, j) => {
          row.push(columns[j + 1][t]);
          for (let l = 1; l <= x_lags; l++) row.push(columns[j + 1][t - l]);
        });
        if (trend) row.push(t);
        rows.push(row); yv.push(columns[0][t]);
      }
      rx.forEach((r) => { names.push(r.label); for (let l = 1; l <= x_lags; l++) names.push(`${r.label} (lag ${l})`); });
      if (trend) names.push("trend");
      const fit = S.ols(yv, rows);
      const hac = S.neweyWest(rows, fit.resid, fit.XtXinv, hac_lags);
      const table = names.map((name, j) => ({
        term: name, coef: r4(fit.beta[j]), se: r4(fit.se[j]), t: r3(fit.t[j]), p: r4(fit.p[j]),
        hac_se: r4(hac.se[j]), hac_t: r3(fit.beta[j] / hac.se[j]), hac_p: r4(S.tTwoSidedP(fit.beta[j] / hac.se[j], fit.n - fit.k)),
      }));
      const warnings: string[] = [];
      const levelsY = ry.transform === "none" || ry.transform === "log" || ry.transform === "rebase";
      if (levelsY && yv.length >= 20) {
        try {
          const ay = S.adf(yv, "c");
          const ax = rx.map((_, j) => { try { return S.adf(columns[j + 1].slice(x_lags), "c"); } catch { return null; } });
          if (!ay.reject_unit_root_at && ax.some((a) => a && !a.reject_unit_root_at)) {
            warnings.push("y and at least one x look non-stationary in levels (ADF does not reject). A high R² here can be spurious. Run cointegration on the pair, or re-run with transform='pct_change' or 'diff'.");
          }
        } catch { /* skip */ }
      }
      if (fit.dw < 1.2) warnings.push(`Durbin-Watson ${r3(fit.dw)}: strong positive residual autocorrelation. Use the HAC columns, not the plain se.`);
      const lb = S.ljungBox(fit.resid, Math.min(12, Math.floor(fit.n / 5)));
      const bp = S.breuschPagan(rows, fit.resid);
      const vifs = S.vif(rows);
      const vifTable = names.slice(1).map((nm, j) => ({ term: nm, vif: Number.isFinite(vifs[j]) ? r3(vifs[j]) : null }));
      let rs: { F: number; p: number; df: [number, number] } | null = null;
      try { if (fit.n > fit.k + 6) rs = S.reset(yv, rows, fit); } catch { /* collinear with the powers */ }
      if (bp.p < 0.05) warnings.push(`Breusch-Pagan p ${r4(bp.p)}: residual variance changes with the regressors (heteroskedasticity). The HAC columns are robust to it; the plain se are not.`);
      const highVif = vifTable.filter((v) => v.vif !== null && (v.vif as number) > 10).map((v) => v.term);
      if (highVif.length) warnings.push(`VIF above 10 for ${highVif.join(", ")}: these regressors move together, so their separate coefficients are poorly determined even if the fit is good. Drop one or combine them.`);
      if (rs && rs.p < 0.05) warnings.push(`RESET p ${r4(rs.p)}: powers of the fitted values add explanatory power, so the linear form is misspecified (a curvature, a missing variable, or logs needed).`);
      const allLog = [ry, ...rx].every((r) => r.transform === "log");
      // What the regression looks like: the fit against the data, the residuals, and for a
      // single regressor the scatter with the line through it.
      const fitDates = dates.slice(x_lags);
      const fitted = yv.map((val, i) => val - fit.resid[i]);
      const resSd = S.sd(fit.resid);
      const fitChart: PlotSpec = {
        series: [inline(ry.label, fitDates, yv), inline("fitted", fitDates, fitted)],
        title: `${ry.label}: actual against the fit on ${rx.map((r) => r.label).join(", ")}`, api: self,
      };
      const residChart: PlotSpec = {
        series: [inline("residual", fitDates, fit.resid)],
        bands: [inlineBand(0, "±2 residual sd", fitDates, fit.resid.map(() => -2 * resSd), fit.resid.map(() => 2 * resSd))],
        title: `${ry.label}: residuals`, api: self,
      };
      let scatterUrl: string | null = null;
      if (rx.length === 1 && x_lags === 0 && !trend) {
        const xs = rows.map((row) => row[1]);
        const lo = Math.min(...xs), hi = Math.max(...xs);
        const lineX = [lo, hi], lineY = lineX.map((xx) => fit.beta[0] + fit.beta[1] * xx);
        scatterUrl = chartUrl(origin, {
          series: [inline(`${ry.label} against ${rx[0].label}`, xs, yv), inline("fitted line", lineX, lineY)],
          dots: [0], xaxis: "number", xlabel: rx[0].label,
          title: `${ry.label} against ${rx[0].label}`, api: self,
        });
      }
      return text({
        y: meta(ry), x: rx.map(meta),
        n: fit.n, k: fit.k, first: dates[x_lags], last: dates[dates.length - 1],
        chart_url: chartUrl(origin, fitChart),
        residual_chart_url: chartUrl(origin, residChart),
        scatter_chart_url: scatterUrl ?? undefined,
        chart_note: "chart_url draws the actual series against the fitted values, residual_chart_url the errors against a two-sd band" + (scatterUrl ? ", scatter_chart_url the cloud of points with the regression line through it" : "") + ". Give the user the links.",
        coefficients: table,
        r2: r4(fit.r2), adj_r2: r4(fit.adj_r2), sigma: r4(fit.sigma), F: fit.F !== null ? r3(fit.F) : null, F_p: fit.F_p !== null ? r4(fit.F_p) : null,
        aic: r3(fit.aic), bic: r3(fit.bic), durbin_watson: r3(fit.dw), hac_lags: hac.lag,
        residuals: { ljung_box_p: r4(lb.p), jarque_bera_p: r4(S.jarqueBera(fit.resid).p) },
        diagnostics: {
          breusch_pagan: { statistic: r3(bp.statistic), p: r4(bp.p), df: bp.df, heteroskedastic_at_5pct: bp.p < 0.05 },
          vif: vifTable,
          reset: rs ? { F: r3(rs.F), p: r4(rs.p), df: rs.df, misspecified_at_5pct: rs.p < 0.05 } : null,
        },
        elasticities: allLog ? "Both sides are in logs, so each coefficient is an elasticity." : undefined,
        warnings,
      });
    }),
  );

  server.registerTool(
    "granger_causality",
    {
      title: "Granger causality",
      description: "Does a help predict b, and does b help predict a? F-tests on lag-augmented regressions in both directions. Use on stationary series (differences or growth rates); the tool checks and warns.",
      inputSchema: { a: REF, b: REF, lags: z.number().int().min(1).max(12).default(2) },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ a, b, lags }) => {
      const ra = await get(a), rb = await get(b);
      const { dates, columns } = align([ra.series, rb.series]);
      if (dates.length < 3 * lags + 8) return fail(`Only ${dates.length} shared dates; need at least ${3 * lags + 8} for ${lags} lags.`);
      const [va, vb] = columns;
      const ab = S.granger(vb, va, lags), ba = S.granger(va, vb, lags);
      const warnings: string[] = [];
      try {
        if (!S.adf(va, "c").reject_unit_root_at || !S.adf(vb, "c").reject_unit_root_at) warnings.push("At least one series looks non-stationary. Granger tests on levels of integrated series are unreliable; re-run with transform='diff' or 'pct_change'.");
      } catch { /* skip */ }
      return text({
        a: meta(ra), b: meta(rb), lags, n: ab.nobs, first: dates[0], last: dates[dates.length - 1],
        a_causes_b: { F: r3(ab.F), p: r4(ab.p), verdict: ab.p < 0.05 ? "a helps predict b (5%)" : "no evidence" },
        b_causes_a: { F: r3(ba.F), p: r4(ba.p), verdict: ba.p < 0.05 ? "b helps predict a (5%)" : "no evidence" },
        reading: "Granger causality is predictive precedence, not economic causation. A common driver can produce it in both directions.",
        warnings,
      });
    }),
  );

  server.registerTool(
    "cointegration",
    {
      title: "Cointegration (Engle-Granger)",
      description: "Do two I(1) series share a long-run relation? Regress a on b, test the residual for a unit root against Engle-Granger critical values. Returns the cointegrating vector and the equilibrium error series.",
      inputSchema: { a: REF, b: REF, include_residuals: z.boolean().default(false) },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ a, b, include_residuals }) => {
      const ra = await get(a), rb = await get(b);
      const { dates, columns } = align([ra.series, rb.series]);
      if (dates.length < 30) return fail(`Only ${dates.length} shared dates; cointegration tests need 30 or more.`);
      const [va, vb] = columns;
      const eg = S.engleGranger(va, vb);
      const orderA = integrationOrder(S.adf(va, "c"), S.adf(S.diff(va), "c"));
      const orderB = integrationOrder(S.adf(vb, "c"), S.adf(S.diff(vb), "c"));
      const notes: string[] = [];
      if (orderA !== "I(1)" || orderB !== "I(1)") notes.push(`Both series should be I(1) for this test to mean anything. Found a: ${orderA}, b: ${orderB}.`);
      const fit = S.ols(va, vb.map((x) => [1, x]));
      // The picture of the test: how far the pair sits from its long-run line, through time.
      const eqChart: PlotSpec = { series: [inline(`${ra.label} minus its long-run level given ${rb.label}`, dates, fit.resid)],
        title: `Equilibrium error: ${ra.label} against ${rb.label}`, api: self };
      const loB = Math.min(...vb), hiB = Math.max(...vb);
      const lineX = [loB, hiB];
      const scatterChart: PlotSpec = {
        series: [inline(`${ra.label} against ${rb.label}`, vb, va), inline("long-run line", lineX, lineX.map((x) => eg.beta[0] + eg.beta[1] * x))],
        dots: [0], xaxis: "number", xlabel: rb.label, title: `${ra.label} against ${rb.label}, with the long-run line`, api: self,
      };
      return text({
        a: meta(ra), b: meta(rb), n: dates.length, first: dates[0], last: dates[dates.length - 1],
        chart_url: chartUrl(origin, eqChart),
        scatter_chart_url: chartUrl(origin, scatterChart),
        chart_note: "chart_url is the equilibrium error through time: cointegration means it returns to zero rather than wandering. scatter_chart_url is the pair with the long-run line through it.",
        integration_order: { a: orderA, b: orderB },
        long_run: { equation: `a = ${r4(eg.beta[0])} + ${r4(eg.beta[1])} * b`, intercept: r4(eg.beta[0]), slope: r4(eg.beta[1]), slope_se: r4(eg.se[1]), r2: r4(eg.r2) },
        residual_test: { statistic: r3(eg.residual_adf.statistic), lags: eg.residual_adf.lags, critical: { "1%": r3(eg.critical["1%"]), "5%": r3(eg.critical["5%"]), "10%": r3(eg.critical["10%"]) }, cointegrated_at: eg.cointegrated_at },
        verdict: eg.cointegrated_at ? `Cointegrated at ${eg.cointegrated_at}: deviations from the long-run line are mean-reverting, so levels regression is meaningful and an error-correction model is the next step.` : "No cointegration found: a levels regression between these two is likely spurious. Work with differences or growth rates.",
        equilibrium_error: include_residuals ? pointsOut(dates, fit.resid) : undefined,
        notes,
      });
    }),
  );

  server.registerTool(
    "cross_correlation",
    {
      title: "Cross-correlation by lag",
      description: "Correlation between a(t) and b(t+k) for k in [-max_lag, max_lag]. Positive k means a leads b. Reports the strongest lag. Use on stationary transforms.",
      inputSchema: { a: REF, b: REF, max_lag: z.number().int().min(1).max(36).default(12) },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ a, b, max_lag }) => {
      const ra = await get(a), rb = await get(b);
      const { dates, columns } = align([ra.series, rb.series]);
      if (dates.length < max_lag * 2 + 10) return fail(`Only ${dates.length} shared dates for max_lag ${max_lag}.`);
      const cc = S.crossCorrelation(columns[0], columns[1], max_lag);
      const best = cc.reduce((p, q) => (Math.abs(q.r) > Math.abs(p.r) ? q : p));
      const band = 1.96 / Math.sqrt(dates.length);
      const lagX = cc.map((c) => c.lag);
      const ccChart: PlotSpec = {
        series: [inline(`corr(${ra.label} at t, ${rb.label} at t+k)`, lagX, cc.map((c) => c.r))],
        bands: [inlineBand(0, "not distinguishable from zero", lagX, cc.map(() => -band), cc.map(() => band))],
        xaxis: "number", xlabel: "lag, in periods", title: `${ra.label} against ${rb.label} by lag (positive k: ${ra.label} leads)`, api: self,
      };
      return text({
        a: meta(ra), b: meta(rb), n: dates.length, first: dates[0], last: dates[dates.length - 1],
        significance_band: r3(band),
        chart_url: chartUrl(origin, ccChart),
        chart_note: "The chart is the correlation against lag; bars outside the shaded band are the lags that carry information. Give the user the link.",
        strongest: { lag: best.lag, r: r3(best.r), reading: best.lag > 0 ? `a leads b by ${best.lag} periods` : best.lag < 0 ? `b leads a by ${-best.lag} periods` : "contemporaneous" },
        correlations: cc.map((c) => ({ lag: c.lag, r: r3(c.r), n: c.n, significant: Math.abs(c.r) > band })),
      });
    }),
  );

  server.registerTool(
    "hp_filter",
    {
      title: "Hodrick-Prescott filter",
      description: "Split a series into trend and cycle. Lambda defaults by frequency (100 annual, 1600 quarterly, 129600 monthly). Returns both components as points and the cycle's standard deviation.",
      inputSchema: { series: REF, lambda: z.number().positive().optional(), include_points: z.boolean().default(true) },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, lambda, include_points }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      const { frequency, period } = detectFrequency(dates);
      const lam = lambda ?? defaultLambda(period, frequency);
      const { trend, cycle } = S.hpFilter(v, lam);
      const trendChart: PlotSpec = { series: [inline(r.label, dates, v), inline("trend", dates, trend)], title: `${r.label} and its trend (HP, lambda ${lam})`, api: self };
      const cycleChart: PlotSpec = { series: [inline("cycle", dates, cycle)], title: `${r.label}: cycle around the trend`, api: self };
      return text({
        ...meta(r), n: v.length, frequency, lambda: lam,
        chart_url: chartUrl(origin, trendChart),
        cycle_chart_url: chartUrl(origin, cycleChart),
        chart_note: "chart_url draws the series with the trend through it; cycle_chart_url the gap between them, which is the object of interest.",
        cycle_sd: r4(S.sd(cycle)), cycle_last: r4(cycle[cycle.length - 1]), trend_last: r4(trend[trend.length - 1]),
        trend: include_points ? pointsOut(dates, trend) : undefined,
        cycle: include_points ? pointsOut(dates, cycle) : undefined,
        caveat: "The HP filter is two-sided and its end points are revised as data arrive. Do not read the last few cycle values as a turning point.",
      });
    }),
  );

  server.registerTool(
    "decompose",
    {
      title: "Seasonal decomposition",
      description: "Classical additive decomposition into trend, seasonal and residual, with seasonal factors per period and strength measures. Period defaults from the date format (12 monthly, 4 quarterly).",
      inputSchema: { series: REF, period: z.number().int().min(2).max(52).optional(), include_points: z.boolean().default(false) },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, period, include_points }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      const f = detectFrequency(dates);
      const p = period ?? f.period;
      if (p < 2) return fail(`No seasonal period for ${f.frequency} data. Pass period explicitly.`);
      const d = S.decompose(v, p);
      const labels = p === 12 ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] : p === 4 ? ["Q1", "Q2", "Q3", "Q4"] : Array.from({ length: p }, (_, i) => `s${i + 1}`);
      const offset = seasonOffset(dates[0], p);
      const trendChart: PlotSpec = { series: [inline(r.label, dates, v), inline("trend", dates, d.trend)], title: `${r.label} and its trend`, api: self };
      const partsChart: PlotSpec = { series: [inline("seasonal", dates, d.seasonal), inline("remainder", dates, d.residual)], title: `${r.label}: seasonal pattern and what is left`, api: self };
      const factorChart: PlotSpec = { series: [inline("seasonal effect", d.seasonal_factors.map((_, i) => i + 1), d.seasonal_factors)], xaxis: "number", xlabel: p === 12 ? "month of the year" : p === 4 ? "quarter" : "season", title: `${r.label}: average effect of each ${p === 12 ? "month" : p === 4 ? "quarter" : "season"}`, api: self };
      return text({
        ...meta(r), n: v.length, period: p,
        chart_url: chartUrl(origin, trendChart),
        components_chart_url: chartUrl(origin, partsChart),
        seasonal_shape_chart_url: chartUrl(origin, factorChart),
        chart_note: `chart_url is the series with its trend, components_chart_url the seasonal swing and the remainder, seasonal_shape_chart_url the average effect of each of the ${p} seasons in order (season 1 is ${(p === 12 ? ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] : p === 4 ? ["Q1","Q2","Q3","Q4"] : ["s1"])[((0 + offset) % p + p) % p]}).`,
        seasonal_strength: r3(d.seasonal_strength), trend_strength: r3(d.trend_strength),
        seasonal_factors: d.seasonal_factors.map((x, i) => ({ season: labels[(((i + offset) % p) + p) % p], effect: r4(x) })),
        reading: d.seasonal_strength > 0.6 ? "Strong seasonality: compare year-on-year or seasonally adjust before month-on-month reading." : d.seasonal_strength > 0.3 ? "Moderate seasonality." : "Weak seasonality: month-on-month changes are usable.",
        trend: include_points ? pointsOut(dates, d.trend) : undefined,
        seasonal: include_points ? pointsOut(dates, d.seasonal) : undefined,
        residual: include_points ? pointsOut(dates, d.residual) : undefined,
      });
    }),
  );

  server.registerTool(
    "forecast",
    {
      title: "Forecast",
      description: "Project a series forward. auto picks Holt-Winters with seasonality for monthly/quarterly data and Holt's linear trend otherwise; ar fits an autoregression. Returns dated forecasts, an approximate 95% band from the residual spread, and in-sample fit. Run forecast_evaluate first to pick the method by out-of-sample error.",
      inputSchema: {
        series: REF,
        horizon: z.number().int().min(1).max(60).default(12),
        method: z.enum(["auto", "holt_winters", "holt", "ar", "arima"]).default("auto"),
        ar_order: z.number().int().min(1).max(12).default(2),
        arima_order: z.tuple([z.number().int().min(0).max(5), z.number().int().min(0).max(2), z.number().int().min(0).max(3)]).optional().describe("[p, d, q] for method=arima; omitted = chosen by AIC with d from the ADF test"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, horizon, method, ar_order, arima_order }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      const f = detectFrequency(dates);
      const future = futureDates(dates[dates.length - 1], horizon, f.frequency);
      const seasonalOk = f.period > 1 && v.length >= 3 * f.period;
      const m = method === "auto" ? (seasonalOk ? "holt_winters" : "holt") : method;
      let forecast: number[], fitted: number[], sdv: number, detail: Record<string, unknown>;
      if (m === "arima") {
        const am = arima_order ? S.arima(v, arima_order[0], arima_order[1], arima_order[2], horizon) : S.autoArima(v, horizon);
        forecast = am.forecast; sdv = am.resid_sd;
        detail = { method: `ARIMA(${am.p},${am.d},${am.q})${arima_order ? "" : ", order by AIC"}`, const: r4(am.const), ar: am.ar.map(r4), ma: am.ma.map(r4), aic: r3(am.aic),
          note: "Conditional sum of squares estimate; the MA polynomial is not constrained to be invertible. Compare with Holt-Winters before trusting a long horizon." };
        // fitted on the differenced scale is not comparable to levels; report in-sample fit on differences only
        fitted = v.map(() => NaN);
      } else if (m === "ar") {
        const ar = S.arForecast(v, ar_order, horizon);
        forecast = ar.forecast; fitted = ar.fitted; sdv = ar.resid_sd;
        detail = { method: `AR(${ar_order})`, coefficients: ar.coef.map(r4), aic: r3(ar.aic) };
        fitted = [...new Array(ar_order).fill(NaN), ...fitted];
      } else {
        const per = m === "holt_winters" ? (seasonalOk ? f.period : 1) : 1;
        const hw = S.holtWinters(v, horizon, per);
        forecast = hw.forecast; fitted = hw.fitted; sdv = hw.resid_sd;
        detail = { method: per > 1 ? `Holt-Winters additive, period ${per}` : "Holt linear trend", alpha: hw.alpha, beta: hw.beta, gamma: hw.gamma, level: r4(hw.level), trend_per_period: r4(hw.trend) };
      }
      const ape = v.map((x, i) => (Number.isFinite(fitted[i]) && x !== 0 ? Math.abs((x - fitted[i]) / x) : NaN)).filter(Number.isFinite);
      const fc = future.map((d, i) => ({ date: d, value: r4(forecast[i]), lo95: r4(forecast[i] - 1.96 * sdv * Math.sqrt(i + 1)), hi95: r4(forecast[i] + 1.96 * sdv * Math.sqrt(i + 1)) }));
      const lastD = dates[dates.length - 1], lastV = r4(v[v.length - 1]) as number;
      // The chart joins the forecast to the last actual; the band starts at zero width there. Only finite rows go into the link.
      const finite = fc.filter((p) => p.value !== null && p.lo95 !== null && p.hi95 !== null);
      const chartSpec: PlotSpec = {
        series: [series, { points: [[lastD, lastV], ...finite.map((p) => [p.date, p.value as number] as [string, number])], label: `${r.label}, forecast` }],
        bands: [{ series: 1, label: "95% band", points: [[lastD, lastV, lastV], ...finite.map((p) => [p.date, p.lo95 as number, p.hi95 as number] as [string, number, number])] }],
        title: `${r.label}: ${String(detail.method)} forecast, ${horizon} ahead`, api: self,
      };
      return text({
        ...meta(r), n: v.length, frequency: f.frequency, last_actual: [lastD, lastV],
        ...detail,
        in_sample: { mape_pct: ape.length ? r3(S.mean(ape) * 100) : null, resid_sd: r4(sdv) },
        forecast: fc,
        chart_url: chartUrl(origin, chartSpec),
        chart_note: "The chart redraws the actual series from live data; the forecast and band are the numbers above, fixed in the link.",
        caveat: "The band grows with the square root of the horizon from the residual spread. It ignores parameter uncertainty and regime change, so treat it as a floor on the real uncertainty.",
      });
    }),
  );

  server.registerTool(
    "structural_break",
    {
      title: "Structural break",
      description: "Chow test at a given date, or a sup-F scan (Quandt-Andrews) over the sample to locate the most likely break, judged against Andrews' sup-F critical values so a data-chosen date gets an honest verdict. Set max_breaks above 1 for a sequential Bai-Perron style search that returns every significant break and the mean or relation inside each segment. Tests a shift in the mean of y, or in the relation y = a + b x when x is given.",
      inputSchema: { y: REF, x: REF.optional(), date: z.string().optional().describe("Candidate break date; omit to scan"), max_breaks: z.number().int().min(1).max(5).default(1).describe("Above 1: sequential search for several breaks") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ y, x, date, max_breaks }) => {
      const ry = await get(y);
      const rx = x ? await get(x) : null;
      const { dates, columns } = align(rx ? [ry.series, rx.series] : [ry.series]);
      if (dates.length < 20) return fail(`Only ${dates.length} observations; need 20 or more.`);
      const yv = columns[0];
      const X = rx ? columns[1].map((v) => [1, v]) : yv.map(() => [1]);
      if (date) {
        const b = dates.findIndex((d) => d >= date);
        if (b < 0) return fail(`Date ${date} is after the sample end ${dates[dates.length - 1]}`);
        const c = S.chow(yv, X, b);
        const before = yv.slice(0, b), after = yv.slice(b);
        const stepChart: PlotSpec = {
          series: [inline(ry.label, dates, yv), inline("mean each side of the break", dates, dates.map((_, t) => (t < b ? S.mean(before) : S.mean(after))))],
          title: `${ry.label}: level before and after ${dates[b]}`, api: self,
        };
        return text({ y: meta(ry), x: rx ? meta(rx) : undefined, test: "Chow", break_date: dates[b], F: r3(c.F), p: r4(c.p), n_before: c.n1, n_after: c.n2,
          chart_url: chartUrl(origin, stepChart),
          chart_note: "The chart draws the series with the average on each side of the tested date. Give the user the link.",
          mean_before: r4(S.mean(before)), mean_after: r4(S.mean(after)), verdict: c.p < 0.05 ? "Break at this date (5%)" : "No evidence of a break at this date" });
      }
      const k = X[0].length;
      const s = S.supF(yv, X);
      const top = [...s.scan].sort((p, q) => q.F - p.F).slice(0, 5).map((e) => ({ date: dates[e.index], F: r3(e.F) }));
      const crit = S.supFCritical(k), rej = S.supFReject(s.best.F, k);
      const segOut = (seg: S.BreakSegment) => ({ from: dates[seg.start], to: dates[seg.end], n: seg.n, mean_y: r4(seg.mean_y), ...(rx ? { intercept: r4(seg.beta[0]), slope: r4(seg.beta[1]) } : {}) });
      let multiple: Record<string, unknown> | undefined;
      const seq = max_breaks > 1 ? S.sequentialBreaks(yv, X, max_breaks) : null;
      if (seq) {
        multiple = { breaks: seq.breaks.map((b) => ({ date: dates[b.index], sup_F: r3(b.F), reject_at: b.reject_at })), segments: seq.segments.map(segOut), stopped: seq.stopped };
      }
      const segAt = (lo: number, hi: number): S.BreakSegment => {
        const ys = yv.slice(lo, hi), Xs = X.slice(lo, hi);
        let beta: number[]; try { beta = S.ols(ys, Xs).beta; } catch { beta = new Array<number>(k).fill(NaN); }
        return { start: lo, end: hi - 1, n: ys.length, beta, mean_y: S.mean(ys) };
      };
      const single = { segments: [segAt(0, s.best.break_index), segAt(s.best.break_index, yv.length)] };
      // The scan itself: F against every candidate date, with the line it has to clear.
      const scanDates = s.scan.map((e) => dates[e.index]);
      // The statistic runs to hundreds while the critical value sits near ten, so a flat
      // line would vanish at the foot of the chart. Shading everything below it instead
      // means the eye reads "out of the shade" as "a break", at any scale.
      const scanChart: PlotSpec = {
        series: [inline("sup-F at each candidate date", scanDates, s.scan.map((e) => e.F))],
        bands: [inlineBand(0, `below this, no break at 5% (${r3(crit["5%"])})`, scanDates, s.scan.map(() => 0), s.scan.map(() => crit["5%"]))],
        title: `${ry.label}: where a break is most likely`, api: self,
      };
      // The series with the level (or the fitted relation) inside each segment it found.
      const segs = seq ? seq.segments : single.segments;
      const stepAt = (t: number) => {
        const seg = segs.find((g) => t >= g.start && t <= g.end) ?? segs[segs.length - 1];
        return rx ? seg.beta[0] + seg.beta[1] * X[t][1] : seg.mean_y;
      };
      const segChart: PlotSpec = {
        series: [inline(ry.label, dates, yv), inline(rx ? "fit inside each segment" : "level inside each segment", dates, dates.map((_, t) => stepAt(t)))],
        title: `${ry.label}: ${segs.length} segment${segs.length > 1 ? "s" : ""}`, api: self,
      };
      return text({ y: meta(ry), x: rx ? meta(rx) : undefined, test: "sup-F scan (Quandt-Andrews), 15% trimming", most_likely_break: dates[s.best.break_index], sup_F: r3(s.best.F),
        chart_url: chartUrl(origin, scanChart),
        segments_chart_url: chartUrl(origin, segChart),
        chart_note: "chart_url is the F statistic at every candidate date against its 5% line, so the reader sees how sharp the break is. segments_chart_url draws the series with the level or the fit inside each segment.",
        sup_F_critical: { "10%": r3(crit["10%"]), "5%": r3(crit["5%"]), "1%": r3(crit["1%"]) }, reject_no_break_at: rej,
        chow_p_at_that_date: r4(s.best.p), candidates: top,
        segments: rej && rej !== "10%" ? single.segments.map(segOut) : undefined,
        multiple_breaks: multiple,
        verdict: rej === null ? "No break: the largest F in the scan is below Andrews' 10% critical value, so the sample can be treated as one regime."
          : rej === "10%" ? "Weak evidence of a break (10% only); do not split the sample on this alone."
          : `Break at ${dates[s.best.break_index]} (sup-F ${r3(s.best.F)} beats the ${rej} critical value ${r3(crit[rej])}).${multiple ? ` Sequential search: ${(multiple.breaks as unknown[]).length} break(s), ${multiple.stopped}.` : " Set max_breaks above 1 to look for more."}`,
        caveat: "Sup-F critical values are Andrews (1993) asymptotics with 15% trimming, simulated for this k; the plain Chow p-value at a data-chosen date overstates significance and is shown only for reference. The sequential search tests each segment on its own, so a break found late in the sequence has a weaker basis than the first. Breaks in the mean of a trending or non-stationary series are found everywhere; difference or detrend first." });
    }),
  );

  server.registerTool(
    "rolling",
    {
      title: "Rolling statistics",
      description: "Rolling mean, standard deviation, or correlation with a second series over a moving window. Shows how a relationship or volatility changes through time.",
      inputSchema: { series: REF, window: z.number().int().min(3).max(240).default(12), stat: z.enum(["mean", "sd", "corr"]).default("mean"), other: REF.optional().describe("Second series for stat=corr") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, window, stat, other }) => {
      const r = await get(series);
      const ro = other ? await get(other) : null;
      if (stat === "corr" && !ro) return fail("stat=corr needs 'other'");
      const { dates, columns } = align(ro ? [r.series, ro.series] : [r.series]);
      if (dates.length < window + 2) return fail(`Only ${dates.length} observations for window ${window}`);
      const out: Array<[string, number | null]> = [];
      for (let t = window - 1; t < dates.length; t++) {
        const a = columns[0].slice(t - window + 1, t + 1);
        let val: number;
        if (stat === "mean") val = S.mean(a);
        else if (stat === "sd") val = S.sd(a);
        else val = S.pearson(a, columns[1].slice(t - window + 1, t + 1));
        out.push([dates[t], r4(val)]);
      }
      const rollChart: PlotSpec = {
        series: [inline(`${window}-period rolling ${stat}${ro ? ` with ${ro.label}` : ""}`, out.map((x) => x[0]), out.map((x) => x[1]))],
        title: `${r.label}: rolling ${stat} over ${window} periods`, api: self,
      };
      return text({ ...meta(r), other: ro ? meta(ro) : undefined, stat, window, n: out.length,
        chart_url: chartUrl(origin, rollChart),
        chart_note: "The chart is the rolling statistic through time, which is the point of the tool. Give the user the link.",
        points: out });
    }),
  );

  server.registerTool(
    "volatility",
    {
      title: "GARCH(1,1) volatility",
      description: "Engle's ARCH-LM test for volatility clustering, then a GARCH(1,1) fit by maximum likelihood on the demeaned series (pass returns or growth rates, not levels). Returns omega, alpha, beta, persistence, the unconditional volatility, the conditional volatility path (last observations) and a one-step-ahead forecast. Typical for exchange rates, equity indices, commodity returns and inflation surprises.",
      inputSchema: {
        series: REF,
        last_n: z.number().int().min(1).max(600).default(60).describe("How many conditional-volatility points to return"),
        annualise: z.boolean().default(true).describe("Also report volatility scaled to annual terms by the series frequency"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, last_n, annualise }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      let g: S.GarchResult;
      try { g = S.garch11(v); } catch (e) { return fail(e instanceof Error ? e.message : String(e)); }
      const { frequency, period } = detectFrequency(dates);
      const perYear = frequency === "daily" ? 252 : frequency === "weekly" ? 52 : period;
      const condSd = g.cond_variance.map(Math.sqrt);
      const last = v[v.length - 1] - g.mean;
      const hNext = g.omega + g.alpha * last * last + g.beta * g.cond_variance[g.cond_variance.length - 1];
      const nonStationary = g.persistence >= 0.99;
      const uncSd = Math.sqrt(g.unconditional_variance);
      const volDates = dates.slice(-last_n), volPath = condSd.slice(-last_n);
      const volChart: PlotSpec = {
        series: [inline("conditional volatility", volDates, volPath), refLine(`unconditional (${r4(uncSd)})`, volDates, uncSd)],
        title: `${r.label}: GARCH(1,1) volatility`, api: self,
      };
      return text({
        ...meta(r), n: g.nobs, first: dates[0], last: dates[dates.length - 1], frequency,
        chart_url: chartUrl(origin, volChart),
        chart_note: "The chart is the conditional volatility path against its unconditional level: the clustering the model is about is visible there, not in the parameters.",
        arch_lm: { statistic: r3(g.arch_lm.statistic), p: r4(g.arch_lm.p), lags: g.arch_lm.lags, clustering: g.arch_lm.p < 0.05 },
        garch: { omega: r4(g.omega), alpha: r4(g.alpha), beta: r4(g.beta), persistence: r4(g.persistence), loglik: r3(g.loglik), aic: r3(g.aic), bic: r3(g.bic) },
        unconditional_sd: r4(uncSd),
        unconditional_sd_annualised: annualise && Number.isFinite(g.unconditional_variance) ? r4(Math.sqrt(g.unconditional_variance * perYear)) : null,
        forecast_next_sd: r4(Math.sqrt(hNext)),
        conditional_sd: pointsOut(dates.slice(-last_n), condSd.slice(-last_n)),
        reading: [
          g.arch_lm.p < 0.05 ? "Volatility clusters: calm and turbulent periods persist, so a constant-variance model understates risk in the turbulent ones." : "No significant ARCH effect: a constant variance is an adequate description; the GARCH parameters below carry little information.",
          `Shock half-life: about ${r3(Math.log(0.5) / Math.log(Math.max(Math.min(g.persistence, 0.9999), 1e-6)))} periods (persistence ${r4(g.persistence)}).`,
          nonStationary ? "Persistence at or above 0.99: variance is close to integrated (IGARCH); the unconditional level is not meaningful." : "",
          `Current conditional volatility ${r4(condSd[condSd.length - 1])} vs unconditional ${r4(uncSd)}: ${condSd[condSd.length - 1] > uncSd ? "above" : "below"} normal.`,
        ].filter(Boolean).join(" "),
        caveat: "Gaussian likelihood; with fat tails the point estimates are consistent but the bands are too narrow. Demeaned series, no mean equation: put an AR term in first if returns are autocorrelated.",
      });
    }),
  );

  server.registerTool(
    "quantile_regress",
    {
      title: "Quantile regression",
      description: "Regression of y on x at several quantiles (default 0.1, 0.25, 0.5, 0.75, 0.9), next to OLS. Shows whether the relation differs in the tails: e.g. does feed cost matter more when cattle prices are already high. Median regression is also a robust alternative to OLS with outliers.",
      inputSchema: {
        y: REF, x: z.array(REF).min(1).max(4),
        quantiles: z.array(z.number().min(0.02).max(0.98)).min(1).max(9).default([0.1, 0.25, 0.5, 0.75, 0.9]),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ y, x, quantiles }) => {
      const ry = await get(y); const rx = await Promise.all(x.map(get));
      const { dates, columns } = align([ry.series, ...rx.map((r) => r.series)]);
      if (dates.length < 30) return fail(`Only ${dates.length} shared dates; need 30 or more.`);
      const Y = columns[0], X = dates.map((_, t) => [1, ...rx.map((__, j) => columns[j + 1][t])]);
      const names = ["const", ...rx.map((r) => r.label)];
      const olsFit = S.ols(Y, X);
      const qs = [...new Set(quantiles)].sort((a, b) => a - b);   // low tail first, whatever order was passed
      const rows = qs.map((q) => { const f = S.quantileRegress(Y, X, q); return { quantile: q, coefficients: Object.fromEntries(names.map((nm, j) => [nm, r4(f.beta[j])])), iterations: f.iterations }; });
      const slopeSpread = rx.map((r, j) => { const b = rows.map((row) => row.coefficients[r.label] as number); return { x: r.label, low_quantile: b[0], high_quantile: b[b.length - 1], ols: r4(olsFit.beta[j + 1]), tail_asymmetry: r4((b[b.length - 1] ?? 0) - (b[0] ?? 0)) }; });
      // The slope of each x across the distribution of y, against its single OLS number.
      const qSeries: SeriesRef[] = [];
      rx.forEach((r, j) => {
        qSeries.push(inline(`${r.label} by quantile`, qs, rows.map((row) => row.coefficients[r.label] as number)));
        if (qSeries.length < 8) qSeries.push(refLine(`${r.label}, OLS`, qs, olsFit.beta[j + 1]));
      });
      const qChart: PlotSpec = { series: qSeries.slice(0, 8), xaxis: "number", xlabel: `quantile of ${ry.label}`, title: `${ry.label}: slope at each quantile`, api: self };
      return text({
        y: meta(ry), x: rx.map(meta), n: dates.length, first: dates[0], last: dates[dates.length - 1],
        chart_url: chartUrl(origin, qChart),
        chart_note: "The chart puts each slope against the quantile of " + ry.label + ", with its OLS value as a flat line: where the two diverge, one average number is hiding the story.",
        ols: Object.fromEntries(names.map((nm, j) => [nm, r4(olsFit.beta[j])])),
        quantiles: qs,
        by_quantile: rows,
        slope_across_quantiles: slopeSpread,
        reading: slopeSpread.map((sp) => Math.abs(sp.tail_asymmetry ?? 0) > Math.abs((sp.ols ?? 0) * 0.5) ? `${sp.x}: the slope changes materially across the distribution of ${ry.label} (${sp.low_quantile} at the low tail vs ${sp.high_quantile} at the high tail), so one OLS number hides where the effect lives.` : `${sp.x}: slope roughly the same across quantiles; OLS is a fair summary.`).join(" "),
        caveat: "Coefficients by iteratively reweighted least squares (no standard errors); quantile paths that cross each other signal too few observations in the tails. Same stationarity cautions as regress.",
      });
    }),
  );

  server.registerTool(
    "principal_components",
    {
      title: "Principal components (common factor)",
      description: "Principal components of 2 to 8 standardised series: how much of their joint movement one common factor explains, each series' loading on it, and the factor score as a dated series. Use for a common inflation or activity factor across countries, or a commodity index from several prices. Pass stationary transforms (yoy, pct_change) unless the levels themselves are the object.",
      inputSchema: { series: z.array(REF).min(2).max(8), components: z.number().int().min(1).max(4).default(2), last_n: z.number().int().min(1).max(600).default(60) },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, components, last_n }) => {
      const rs = await Promise.all(series.map(get));
      const { dates, columns } = align(rs.map((r) => r.series));
      if (dates.length < rs.length + 10) return fail(`Only ${dates.length} shared dates for ${rs.length} series.`);
      const Y = dates.map((_, t) => columns.map((c) => c[t]));
      const p = S.pca(Y);
      const m = Math.min(components, p.k);
      const labels = rs.map((r) => r.label);
      const scoreDates = dates.slice(-last_n);
      const scoreChart: PlotSpec = {
        series: Array.from({ length: m }, (_, c) => inline(`component ${c + 1}`, scoreDates, p.scores.slice(-last_n).map((row) => row[c]))),
        title: `Common factor${m > 1 ? "s" : ""} across ${labels.join(", ")}`, api: self,
      };
      const comps = p.explained.slice(0, p.k).map((_, i) => i + 1);
      const screeChart: PlotSpec = {
        series: [inline("share of joint variance", comps, p.explained.slice(0, p.k)),
          inline("cumulative", comps, comps.map((_, i) => p.explained.slice(0, i + 1).reduce((a, b) => a + b, 0)))],
        xaxis: "number", xlabel: "component", title: "How much each component explains", api: self,
      };
      return text({
        series: rs.map(meta), n: p.nobs, first: dates[0], last: dates[dates.length - 1],
        chart_url: chartUrl(origin, scoreChart),
        scree_chart_url: chartUrl(origin, screeChart),
        chart_note: "chart_url is the common factor through time, the series to quote as the shared movement; scree_chart_url shows how much of the joint variation each component carries.",
        explained_variance: p.explained.slice(0, p.k).map((e, i) => ({ component: i + 1, share: r4(e), cumulative: r4(p.explained.slice(0, i + 1).reduce((a, b) => a + b, 0)) })),
        loadings: Array.from({ length: m }, (_, c) => ({ component: c + 1, loadings: Object.fromEntries(labels.map((l, j) => [l, r4(p.loadings[c][j])])) })),
        correlation_matrix: Object.fromEntries(labels.map((l, i) => [l, Object.fromEntries(labels.map((l2, j) => [l2, r3(p.correlation[i][j])]))])),
        scores: Array.from({ length: m }, (_, c) => ({ component: c + 1, points: pointsOut(dates.slice(-last_n), p.scores.slice(-last_n).map((row) => row[c])) })),
        reading: `The first component explains ${r3(p.explained[0] * 100)}% of the joint variance${p.explained[0] > 0.6 ? ": these series largely move together as one factor." : p.explained[0] > 0.4 ? ": a common factor exists but idiosyncratic moves matter." : ": no dominant common factor; the series mostly move on their own."} Loadings with the same sign mean the series rise together with the factor; a negative loading moves against it.`,
        caveat: "Series are standardised (unit variance), so each gets equal weight regardless of scale. Components are descriptive, not causal; sign is fixed so the largest loading is positive.",
      });
    }),
  );

  server.registerTool(
    "panel_regress",
    {
      title: "Panel regression across countries (fixed effects)",
      description: "Regression across many units and years at once, for datasets whose series keys are 'UNIT|INDICATOR' (asia-wdi, imf-weo). Reports the within (fixed-effects) estimate that uses only variation inside each country, the pooled estimate that also uses differences between countries, and the between estimate on country means, with standard errors clustered by country and an F test for whether country effects exist at all. Use it to ask whether a relation holds across economies rather than in one.",
      inputSchema: {
        dataset: z.string().describe("Dataset with 'UNIT|INDICATOR' keys, e.g. 'asia-wdi' or 'imf-weo'"),
        y: z.string().describe("Indicator to explain, e.g. 'gdp_growth' or 'NGDP_RPCH'"),
        x: z.array(z.string()).min(1).max(4).describe("Explanatory indicators, same naming"),
        units: z.array(z.string()).max(60).optional().describe("Restrict to these units (country codes as used in the keys); default every unit that has all the indicators"),
        effects: z.enum(["pooled", "unit", "unit_time"]).default("unit").describe("unit = country fixed effects; unit_time = country and year effects (removes global shocks); pooled = no effects"),
        transform: z.enum(["none", "log", "diff", "yoy"]).default("none").describe("Applied to every series; log both sides gives elasticities"),
        start: z.string().optional(), end: z.string().optional(),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ dataset, y, x, units, effects, transform, start, end }) => {
      const [cat, body] = await Promise.all([loadCatalog(origin), loadDataset(origin, dataset)]);
      const all = extractSeries(body);
      const wanted = [y, ...x];
      const indicators = new Set<string>();
      const byUnit = new Map<string, Map<string, Series>>();
      for (const [key, s] of all) {
        const i = key.indexOf("|");
        if (i < 0) continue;
        const u = key.slice(0, i), ind = key.slice(i + 1);
        indicators.add(ind);
        if (!wanted.includes(ind)) continue;
        if (units && !units.includes(u)) continue;
        let m = byUnit.get(u);
        if (!m) { m = new Map(); byUnit.set(u, m); }
        m.set(ind, s);
      }
      if (!indicators.size) return fail(`${datasetName(dataset)} has no 'UNIT|INDICATOR' series keys, so it is not a panel. Use regress for a single-series dataset.`);
      const missing = wanted.filter((w) => !indicators.has(w));
      if (missing.length) return fail(`Not in ${datasetName(dataset)}: ${missing.join(", ")}. Indicators available: ${[...indicators].sort().join(", ")}`);

      const yy: number[] = [], XX: number[][] = [], uIdx: number[] = [], tIdx: number[] = [];
      const timeIndex = new Map<string, number>();
      const usedUnits: string[] = [], skipped: string[] = [];
      for (const [u, m] of [...byUnit.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
        if (wanted.some((w) => !m.has(w))) { skipped.push(u); continue; }
        const cols = wanted.map((w) => apply(clip(m.get(w)!, start, end), transform as Transform));
        const dates = Object.keys(cols[0]).filter((d) => cols.every((c) => d in c && Number.isFinite(c[d]))).sort();
        if (dates.length < 3) { skipped.push(u); continue; }
        const ui = usedUnits.length;
        usedUnits.push(u);
        for (const d of dates) {
          if (!timeIndex.has(d)) timeIndex.set(d, timeIndex.size);
          yy.push(cols[0][d]);
          XX.push(cols.slice(1).map((c) => c[d]));
          uIdx.push(ui); tIdx.push(timeIndex.get(d)!);
        }
      }
      if (usedUnits.length < 2) return fail(`Only ${usedUnits.length} unit(s) have all of ${wanted.join(", ")} with 3 or more shared periods${skipped.length ? ` (skipped ${skipped.join(", ")})` : ""}.`);

      let res: S.PanelResult;
      try { res = S.panelRegress(yy, XX, uIdx, tIdx, effects); }
      catch (e) { return fail(e instanceof Error ? e.message : String(e)); }

      const coefRow = (fit: S.PanelFit, hasConst: boolean) => {
        const names = hasConst ? ["const", ...x] : x;
        return names.map((nm, j) => ({ term: nm, coefficient: r4(fit.beta[j]), se: r4(fit.se[j]), t: r3(fit.t[j]), p: r4(fit.p[j]), significant_5pct: fit.p[j] < 0.05 }));
      };
      const withinRow = coefRow(res.estimate, effects === "pooled");
      const pooledRow = coefRow(res.pooled, true);
      const betweenRow = res.between ? coefRow(res.between, true) : null;
      const comparison = x.map((nm, j) => {
        const w = withinRow.find((r) => r.term === nm)?.coefficient ?? null;
        const p0 = pooledRow.find((r) => r.term === nm)?.coefficient ?? null;
        const b = betweenRow?.find((r) => r.term === nm)?.coefficient ?? null;
        // Compare the unrounded estimates: a coefficient that rounds to 0 is not a sign change.
        const wRaw = effects === "pooled" ? res.pooled.beta[j + 1] : res.estimate.beta[j];
        const flips = wRaw * res.pooled.beta[j + 1] < 0;
        return { x: nm, within: w, pooled: p0, between: b, sign_flips_between_within_and_pooled: flips };
      });
      const flipped = comparison.filter((c) => c.sign_flips_between_within_and_pooled).map((c) => c.x);
      return text({
        dataset: datasetName(dataset),
        source: sourceFor(cat.datasets.find((d) => d.file === `data/${datasetName(dataset)}.json`), body),
        caveats: caveatsFor(cat.datasets.find((d) => d.file === `data/${datasetName(dataset)}.json`), body),
        y, x, transform, effects,
        sample: { observations: res.nobs, units: res.units, unit_codes: usedUnits, periods: res.periods, balanced: res.balanced, skipped_units: skipped.length ? skipped : undefined },
        estimate: { specification: effects === "pooled" ? "pooled OLS" : effects === "unit" ? "within (country fixed effects)" : "two-way within (country and year effects)", coefficients: withinRow, r2: r4(res.estimate.r2), df_residual: res.estimate.df },
        pooled: { coefficients: pooledRow, r2: r4(res.pooled.r2) },
        between: res.between ? { coefficients: betweenRow, r2: r4(res.between.r2), note: "One observation per country (its mean): pure cross-section, so it answers a different question." } : null,
        comparison_of_slopes: comparison,
        f_test_unit_effects: res.f_unit_effects ? { tests: effects === "unit_time" ? "country and year effects jointly, against pooled OLS" : "country effects, against pooled OLS", F: r3(res.f_unit_effects.F), p: r4(res.f_unit_effects.p), df: [res.f_unit_effects.df1, res.f_unit_effects.df2], effects_matter: res.f_unit_effects.p < 0.05 } : null,
        reading: [
          res.f_unit_effects && res.f_unit_effects.p < 0.05
            ? `${effects === "unit_time" ? "Country and year effects are" : "Country effects are"} significant: pooled OLS confounds differences between countries with the relation inside them, so read the within estimate.`
            : "No significant effects of that kind: the pooled and within estimates answer nearly the same question here.",
          flipped.length ? `Sign flips between pooled and within for ${flipped.join(", ")}: the cross-country pattern runs opposite to the within-country one, a Simpson's paradox in this panel. Say which one you mean.` : "",
          effects === "unit" ? "Year effects are not removed, so a global shock hitting every country in the same year still loads on the regressors; try effects=unit_time to net it out." : "",
          transform === "log" ? "Both sides in logs: coefficients read as elasticities." : "",
        ].filter(Boolean).join(" "),
        caveat: "Standard errors are clustered by country, which handles serial correlation within a country but needs a decent number of countries (roughly 20 or more) to be reliable; with few units treat the p-values as indicative. Fixed effects remove anything constant per country, so a slow-moving regressor loses most of its variation; two-way effects are removed by sequential demeaning, which is exact on a balanced panel and approximate otherwise. Nothing here identifies causality: reverse causality and omitted time-varying variables survive fixed effects.",
      });
    }),
  );

  server.registerTool(
    "johansen",
    {
      title: "Johansen cointegration (2 to 5 series)",
      description: "Trace test for the number of cointegrating relations among several I(1) series. deterministic='constant' (default) puts an unrestricted constant in the VAR, right for series that drift (price levels, logs of output); 'restricted_constant' puts the constant inside the cointegrating relation only, right for series without drift (interest rates, ratios, real exchange rates) and then reports the constant as part of the vector. Returns the eigenvalues, trace statistics against MacKinnon-Haug-Michelis critical values for the chosen case, the rank at 5%, the first cointegrating vector normalised on the first series, and a drift check that says which case fits the data. Use cointegration (Engle-Granger) for exactly two series when you want the residual series.",
      inputSchema: { series: z.array(REF).min(2).max(5), lags: z.number().int().min(1).max(8).default(1).describe("Lagged differences in the VECM"), deterministic: z.enum(["constant", "restricted_constant", "restricted_trend"]).default("constant").describe("constant: unrestricted, for drifting series; restricted_constant: inside the relation only, for drift-free series; restricted_trend: unrestricted constant plus a linear trend inside the relation, when the series drift at different rates so the equilibrium itself trends") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, lags, deterministic }) => {
      const rs = await Promise.all(series.map(get));
      const { dates, columns } = align(rs.map((r) => r.series));
      if (dates.length < 30) return fail(`Only ${dates.length} shared dates; need 30 or more.`);
      const Y = dates.map((_, t) => columns.map((c) => c[t]));
      const j = S.johansen(Y, lags, deterministic);
      const drift = driftCheck(rs.map((r) => r.label), columns, deterministic);
      const labels = [...rs.map((r) => r.label), ...(deterministic === "restricted_constant" ? ["constant"] : deterministic === "restricted_trend" ? ["trend"] : [])];
      // The relation itself: beta'y through time. Cointegration means this comes back.
      // Drawn even at rank 0, where the point is that the line wanders instead of returning.
      let relUrl: string | null = null;
      const bv = j.cointegrating_vector ?? (j.vectors?.length ? j.vectors[0] : null);
      if (bv) {
        const rel = Y.map((row, t) => {
          let z = 0;
          row.forEach((x, i) => { z += bv[i] * x; });
          if (deterministic === "restricted_constant") z += bv[rs.length];
          if (deterministic === "restricted_trend") z += bv[rs.length] * t;
          return z;
        });
        relUrl = chartUrl(origin, { series: [inline(j.rank_at_5pct > 0 ? "cointegrating relation" : "leading combination (no relation at 5%)", dates, rel)], title: `Long-run relation between ${rs.map((r) => r.label).join(", ")}`, api: self });
      }
      return text({
        series: rs.map(meta), n: j.nobs, first: dates[0], last: dates[dates.length - 1], lags, deterministic,
        chart_url: relUrl ?? undefined,
        chart_note: relUrl ? (j.rank_at_5pct > 0
          ? "The chart is the first cointegrating relation through time: a line that returns to its mean is what the trace test is claiming."
          : "The chart is the combination with the strongest mean reversion in the data. The trace test does not call it cointegrated at 5%, and the wandering line is why.") : undefined,
        eigenvalues: j.eigenvalues.map(r4),
        trace_tests: j.trace.map((t) => ({ null_rank_at_most: t.r, statistic: r3(t.statistic), critical: t.critical, reject: t.reject })),
        rank_at_5pct: j.rank_at_5pct,
        cointegrating_vector: j.cointegrating_vector ? Object.fromEntries(labels.map((l, i) => [l, r4(j.cointegrating_vector![i])])) : null,
        drift_check: drift,
        reading: [j.rank_at_5pct === 0 ? "No cointegrating relation at 5%: model these in differences (VAR on growth rates)."
          : `${j.rank_at_5pct} cointegrating relation${j.rank_at_5pct > 1 ? "s" : ""} at 5%: a levels relation exists; an error-correction model is appropriate. The vector shows the long-run weights, normalised so the first series has weight 1${deterministic === "restricted_constant" ? ", with the constant of the relation as its last element" : deterministic === "restricted_trend" ? ", with the trend coefficient of the relation (per period) as its last element" : ""}.`, drift.note].filter(Boolean).join(" "),
        caveat: "Critical values assume no breaks and the chosen deterministic case. Results are sensitive to the lag choice; try lags 1 to 4. The wrong case biases the rank: an unrestricted constant on drift-free series over-rejects, a restricted constant on drifting series mis-specifies the trend, and a restricted trend costs power when the relation does not trend (test its coefficient in vecm).",
      });
    }),
  );

  server.registerTool(
    "vecm",
    {
      title: "Vector error-correction model",
      description: "For 2 to 5 cointegrated I(1) series: the long-run vectors (Johansen), the adjustment coefficients alpha with t-tests (which series does the correcting, and how fast), short-run lag coefficients, and the current error-correction term (how far the system is from its long-run relation right now). Rank defaults to the Johansen 5% result.",
      inputSchema: {
        series: z.array(REF).min(2).max(5),
        lags: z.number().int().min(1).max(8).default(1).describe("Lagged differences in the model"),
        rank: z.number().int().min(1).max(4).optional().describe("Number of cointegrating relations; default from the Johansen trace test at 5%"),
        deterministic: z.enum(["constant", "restricted_constant", "restricted_trend"]).default("constant").describe("constant: unrestricted, for drifting series; restricted_constant: inside the relation only, for drift-free series such as rates and ratios; restricted_trend: a linear trend inside the relation as well, when the equilibrium itself trends"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, lags, rank, deterministic }) => {
      const rs = await Promise.all(series.map(get));
      const { dates, columns } = align(rs.map((r) => r.series));
      if (dates.length < 30) return fail(`Only ${dates.length} shared dates; need 30 or more.`);
      const Y = dates.map((_, t) => columns.map((c) => c[t]));
      let m: S.VecmResult;
      try { m = S.vecm(Y, lags, rank, deterministic); } catch (e) { return fail(e instanceof Error ? e.message : String(e)); }
      const labels = rs.map((r) => r.label);
      const rc = deterministic === "restricted_constant", rt = deterministic === "restricted_trend";
      const drift = driftCheck(labels, columns, deterministic);
      const relations = m.beta[0].map((_, c) => ({
        relation: c + 1,
        long_run_vector: Object.fromEntries([...labels.map((l, i) => [l, r4(m.beta[i][c])]), ...(rc ? [["constant", r4(m.beta_constant[c])]] : []), ...(rt ? [["trend", r4(m.beta_trend[c])]] : [])]),
        equation: `${labels[0]} = ${labels.slice(1).map((l, i) => `${r4(-m.beta[i + 1][c])} × ${l}`).join(" + ")} ${rc ? `+ ${r4(-m.beta_constant[c])}` : rt ? `+ ${r4(-m.beta_trend[c])} × t + constant` : "+ constant"} (normalised on ${labels[0]})`,
        adjustment: labels.map((l, i) => ({ series: l, alpha: r4(m.alpha[i][c]), t: r3(m.alpha_t[i][c]), p: r4(m.alpha_p[i][c]), adjusts: m.alpha_p[i][c] < 0.05, share_corrected_per_period: r3(Math.abs(m.alpha[i][c])) })),
        ect_last: r4(m.ect[m.ect.length - 1][c]),
        ect_mean: r4(m.ect.reduce((a, row) => a + row[c], 0) / m.ect.length),
      }));
      const adjusters = relations[0].adjustment.filter((a) => a.adjusts).map((a) => a.series);
      const half = labels.map((l, i) => ({ l, a: m.alpha[i][0], p: m.alpha_p[i][0] })).filter((x) => x.p < 0.05 && x.a < 0).map((x) => `${x.l}: ${r3(Math.log(0.5) / Math.log(1 - Math.min(Math.abs(x.a), 0.99)))} periods`);
      const ectDates = dates.slice(dates.length - m.ect.length);
      const ectChart: PlotSpec = {
        series: Array.from({ length: Math.min(m.rank, 4) }, (_, c) => inline(`deviation, relation ${c + 1}`, ectDates, m.ect.map((row) => row[c]))),
        title: `${labels.join(", ")}: distance from the long-run relation`, api: self,
      };
      return text({
        series: rs.map(meta), n: m.nobs, first: dates[0], last: dates[dates.length - 1], lags, rank: m.rank, deterministic,
        chart_url: chartUrl(origin, ectChart),
        chart_note: "The chart is the error-correction term: how far the system sits from its long-run relation at each date, and how quickly it is pulled back. Give the user the link.",
        drift_check: drift,
        johansen: { rank_at_5pct: m.johansen.rank_at_5pct, trace: m.johansen.trace.map((t) => ({ null_rank_at_most: t.r, statistic: r3(t.statistic), critical_5pct: t.critical["5%"], reject: t.reject })) },
        relations,
        short_run: m.gamma.map((G, l) => ({ lag: l + 1, coefficients: Object.fromEntries(labels.map((eq, i) => [eq, Object.fromEntries(labels.map((v, j) => [v, r4(G[i][j])]))])) })),
        r2_by_equation: Object.fromEntries(labels.map((l, i) => [l, r4(m.r2[i])])),
        reading: [
          adjusters.length ? `${adjusters.join(" and ")} respond${adjusters.length === 1 ? "s" : ""} to deviations from the long-run relation; the others are weakly exogenous (they drive, they do not adjust).` : "No series adjusts significantly: the relation is not being corrected in this sample, which weakens the cointegration case.",
          half.length ? `Half-life of a deviation: ${half.join(", ")}.` : "",
          `Deviation now (relation 1): ${relations[0].ect_last} against a sample mean of ${relations[0].ect_mean}; a value above the mean means ${labels[0]} sits above its long-run level given the others.`,
          drift.note,
        ].filter(Boolean).join(" "),
        caveat: `Alpha t-tests use OLS standard errors equation by equation. ${rc ? "The constant is restricted to the cointegrating relation, so the error-correction term is already centred and the differences carry no separate intercept." : rt ? "A linear trend sits inside the cointegrating relation (its coefficient is per period, from the first shared date) and the differences keep an unrestricted constant; if the trend coefficient is tiny, re-run with deterministic='constant' for a sharper test." : "The constant is unrestricted (enters the differences), so the error-correction term has a non-zero mean; read the current deviation against the sample mean."} Sensitive to the lag choice and to breaks in the relation; check structural_break on the error-correction term if the sample spans a regime change.`,
      });
    }),
  );

  server.registerTool(
    "var_model",
    {
      title: "Vector autoregression with structural impulse responses",
      description: "Estimate a VAR(p) on 2 to 5 stationary series, lag order by AIC unless given. Returns coefficients, block Granger tests, impulse responses with bootstrap bands, cumulative responses and the forecast error variance decomposition. Identification: cholesky (recursive, in the order the series are given), long_run (Blanchard-Quah: shock j has no permanent effect on series i for i < j, so put the variable whose permanent shock you want first and pass it in differences), or sign (draw rotations and keep those whose responses carry the requested signs; bands then reflect identification uncertainty). Pass growth rates or differences; the tool warns on non-stationary input. local_projections gives the same response without the lag structure.",
      inputSchema: {
        series: z.array(REF).min(2).max(5),
        lags: z.number().int().min(1).max(12).optional().describe("Lag order; default chosen by AIC up to max_lags"),
        max_lags: z.number().int().min(1).max(12).default(6),
        horizon: z.number().int().min(1).max(40).default(12),
        identification: z.enum(["cholesky", "long_run", "sign"]).default("cholesky"),
        sign_restrictions: z.array(z.object({
          shock: z.number().int().min(0).max(4).describe("0-based index of the shock"),
          variable: z.number().int().min(0).max(4).describe("0-based index of the series that must respond"),
          sign: z.enum(["+", "-"]),
          horizons: z.array(z.number().int().min(0).max(40)).min(1).default([0]),
        })).max(20).optional().describe("For identification=sign: e.g. a demand shock raises output and prices on impact"),
        shock_names: z.array(z.string().max(40)).max(5).optional().describe("Labels for the structural shocks, in shock order"),
        bootstrap: z.number().int().min(0).max(500).default(200).describe("Residual-bootstrap replications for the response bands (cholesky and long_run); 0 to skip"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, lags, max_lags, horizon, identification, sign_restrictions, shock_names, bootstrap }) => {
      const rs = await Promise.all(series.map(get));
      const { dates, columns } = align(rs.map((r) => r.series));
      if (dates.length < 40) return fail(`Only ${dates.length} shared dates; need 40 or more.`);
      const Y = dates.map((_, t) => columns.map((c) => c[t]));
      const p = lags ?? S.varSelectLag(Y, max_lags);
      const m = S.varModel(Y, p, horizon);
      const names = rs.map((r) => r.label);
      const shocks = names.map((nm, j) => shock_names?.[j] ?? (identification === "cholesky" ? `${nm} shock` : identification === "long_run" ? (j === 0 ? `permanent shock (${nm})` : `shock ${j + 1} (no long-run effect on ${names.slice(0, j).join(", ")})`) : `shock ${j + 1}`));
      const warnings: string[] = [];
      columns.forEach((c, i) => { try { if (!S.adf(c, "c").reject_unit_root_at) warnings.push(`${names[i]} looks non-stationary; a VAR in levels can be spurious${identification === "long_run" ? " and long-run effects are not defined" : ""}. Use transform='pct_change' or 'diff'.`); } catch { /* skip */ } });
      const coefTable = m.coef.map((row, e) => {
        const terms: Record<string, number | null> = { const: r4(row[0]) };
        for (let l = 1; l <= p; l++) names.forEach((nm, j) => { terms[`${nm} (lag ${l})`] = r4(row[1 + (l - 1) * m.k + j]); });
        return { equation: names[e], terms };
      });
      const grid = (M: number[][][], f = r4) => M.map((h, i) => ({ h: i, response: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, f(h[ri][si])]))])) }));
      let irf: number[][][], cumulative: number[][][], fevd: number[][][], bands: Record<string, unknown> | null = null, longRun: Record<string, unknown> | null = null, signInfo: Record<string, unknown> | null = null, B: number[][];
      if (identification === "sign") {
        if (!sign_restrictions?.length) return fail("identification='sign' needs sign_restrictions, e.g. [{shock: 0, variable: 0, sign: '+'}, {shock: 0, variable: 1, sign: '+'}].");
        const bad = sign_restrictions.find((r) => r.shock >= m.k || r.variable >= m.k);
        if (bad) return fail(`A restriction refers to shock ${bad.shock} or variable ${bad.variable}, but there are only ${m.k} series (indexes 0..${m.k - 1}).`);
        let sr: S.SignResult;
        try { sr = S.signIdentify(m, sign_restrictions.map((r) => ({ shock: r.shock, variable: r.variable, sign: r.sign === "+" ? 1 : -1, horizons: r.horizons })), 200, 20000); }
        catch (e) { return fail(e instanceof Error ? e.message : String(e)); }
        irf = sr.irf_median; cumulative = sr.cumulative_median; fevd = sr.fevd_median; B = sr.B_median_target;
        bands = { kind: "16th and 84th percentiles over the accepted draws (identification uncertainty, not sampling uncertainty)", horizons: sr.irf_lo.map((lo, h) => ({ h, lo: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(lo[ri][si])]))])), hi: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(sr.irf_hi[h][ri][si])]))])) })) };
        signInfo = { accepted_draws: sr.accepted, total_draws: sr.draws, acceptance_rate: r4(sr.accepted / sr.draws), restrictions: sign_restrictions.map((r) => `${shocks[r.shock]} ${r.sign === "+" ? "raises" : "lowers"} ${names[r.variable]} at h=${r.horizons.join(",")}`),
          note: "Responses shown are pointwise medians across accepted draws; impact_matrix is the single accepted draw closest to them (Fry-Pagan median target). Restrictions identify sets, not points: a narrow band means the data pin the response down, a wide one means the restrictions do not." };
      } else {
        let id: { B: number[][]; long_run: number[][] | null };
        try { id = S.identify(m, identification); } catch (e) { return fail(e instanceof Error ? e.message : String(e)); }
        B = id.B;
        const sresp = S.structuralResponses(m.psi, B);
        irf = sresp.irf; cumulative = sresp.cumulative; fevd = sresp.fevd;
        if (id.long_run) longRun = { note: "Permanent effect of each shock on each series' level (for series passed in differences); lower triangular by construction", matrix: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(id.long_run![ri][si])]))])) };
        if (bootstrap > 0) {
          try {
            const bb = S.varBootstrap(Y, p, horizon, identification, bootstrap);
            bands = { kind: `residual bootstrap, ${bb.reps} replications, 16th/84th and 5th/95th percentiles`, horizons: bb.lo16.map((lo, h) => ({ h,
              lo16: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(lo[ri][si])]))])),
              hi84: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(bb.hi84[h][ri][si])]))])),
              lo05: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(bb.lo05[h][ri][si])]))])),
              hi95: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(bb.hi95[h][ri][si])]))])) })) };
          } catch (e) { warnings.push(`Bootstrap bands unavailable: ${e instanceof Error ? e.message : String(e)}`); }
        }
      }
      // Which responses are distinguishable from zero at the 68% level, by shock and series
      const significant: string[] = [];
      if (bands) {
        const hs = bands.horizons as Array<Record<string, Record<string, Record<string, number | null>>>>;
        const loKey = identification === "sign" ? "lo" : "lo16", hiKey = identification === "sign" ? "hi" : "hi84";
        names.forEach((rn) => shocks.forEach((sn) => {
          const hh = hs.map((row, h) => ({ h, lo: row[loKey][rn][sn], hi: row[hiKey][rn][sn] })).filter((x) => x.lo !== null && x.hi !== null && ((x.lo as number) > 0 || (x.hi as number) < 0)).map((x) => x.h);
          if (hh.length) significant.push(`${rn} to ${sn}: h=${hh.length > 6 ? `${hh[0]}..${hh[hh.length - 1]} (${hh.length})` : hh.join(",")}`);
        }));
      }
      // One chart per shock: every series' response, with the 68% band where there is one.
      const hs2 = bands ? (bands.horizons as Array<Record<string, unknown>>) : null;
      const loKey2 = identification === "sign" ? "lo" : "lo16", hiKey2 = identification === "sign" ? "hi" : "hi84";
      const hAxis = irf.map((_, h) => hx(h));
      const f0 = detectFrequency(dates).frequency;
      const irfCharts = shocks.map((sn, si) => {
        const shown = names.slice(0, 8);
        const spec: PlotSpec = {
          series: shown.map((rn, ri) => inline(rn, hAxis, irf.map((h) => h[ri][si]))),
          bands: hs2 ? shown.slice(0, 4).map((rn, ri) => inlineBand(ri, "68% band", hAxis,
            hs2.map((row) => ((row[loKey2] as Record<string, Record<string, number | null>>)[rn][sn])),
            hs2.map((row) => ((row[hiKey2] as Record<string, Record<string, number | null>>)[rn][sn])))) : undefined,
          xaxis: "number", xlabel: `periods after the shock (${f0})`, title: `Response to a ${sn}`, api: self,
        };
        return { shock: sn, chart_url: chartUrl(origin, spec) };
      });
      return text({
        series: rs.map(meta), n: m.nobs, first: dates[0], last: dates[dates.length - 1], lags: p, lag_selection: lags ? "given" : `AIC over 1..${max_lags}`,
        aic: r3(m.aic), bic: r3(m.bic),
        equations: coefTable,
        granger_block_tests: m.granger.map((g) => ({ cause: names[g.cause], effect: names[g.effect], F: r3(g.F), p: r4(g.p), significant_5pct: g.p < 0.05 })),
        identification, shocks,
        impact_matrix: { note: "Row = series, column = structural shock: the response on impact to a one-standard-deviation shock", matrix: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(B[ri][si])]))])) },
        long_run_effects: longRun,
        sign_identification: signInfo,
        impulse_response_charts: irfCharts,
        chart_note: "One chart per shock, each drawing how every series responds over the horizon with its 68% band. These are the figures to show; the tables below are the same numbers.",
        impulse_responses: { note: identification === "cholesky" ? "Response of row series to a one-standard-deviation orthogonalised shock in column; ordering matters for contemporaneous effects." : "Response of row series to a one-standard-deviation structural shock in column.", horizons: grid(irf) },
        cumulative_responses_at_horizon: Object.fromEntries(names.map((rn, ri) => [rn, Object.fromEntries(shocks.map((sn, si) => [sn, r4(cumulative[horizon][ri][si])]))])),
        response_bands: bands,
        significant_at_68pct: significant.length ? significant : bands ? ["none: no response is distinguishable from zero even at the 68% level"] : undefined,
        variance_decomposition_at_horizon: Object.fromEntries(names.map((vn, vi) => [vn, Object.fromEntries(shocks.map((sn, si) => [sn, r3(fevd[horizon][vi][si])]))])),
        warnings,
        caveat: identification === "long_run" ? "Long-run restrictions are only as good as the assumption that shocks after the first have no permanent effect on the earlier series; they are fragile when the VAR's lag polynomial is close to a unit root (very persistent series), where Psi(1) is poorly estimated. Series must be stationary; for level effects pass differences and read cumulative_responses_at_horizon."
          : identification === "sign" ? "Sign restrictions do not point-identify: the band shows the set of models consistent with the restrictions and the data, and the median response need not come from any single model. Add restrictions at more horizons or on more variables to narrow it."
          : "Recursive identification assumes the ordering: an earlier series does not respond within the period to shocks in later ones. Reorder to test how much the conclusion depends on it, or use long_run or sign identification.",
      });
    }),
  );

  server.registerTool(
    "deflate",
    {
      title: "Real terms",
      description: "Divide a nominal series by a price index to express it in constant prices of a base date (index rebased to 100 there). Aligns on shared dates; use frequency='annual_mean' on the monthly side when mixing frequencies.",
      inputSchema: { nominal: REF, deflator: REF, base: z.string().optional().describe("Date whose prices to use; default = last shared date") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ nominal, deflator, base }) => {
      const rn = await get(nominal), rd = await get(deflator);
      const { dates, columns } = align([rn.series, rd.series]);
      if (!dates.length) return fail("No shared dates between the nominal series and the deflator.");
      const b = base ?? dates[dates.length - 1];
      const bi = dates.indexOf(b);
      if (bi < 0) return fail(`Base ${b} is not a shared date (range ${dates[0]}..${dates[dates.length - 1]}).`);
      const pb = columns[1][bi];
      const real = columns[0].map((v, i) => (columns[1][i] ? (v * pb) / columns[1][i] : NaN));
      const defChart: PlotSpec = {
        series: [inline(`${rn.label}, nominal`, dates, columns[0]), inline(`at ${b} prices`, dates, real)],
        title: `${rn.label}: nominal and real`, api: self,
      };
      return text({ nominal: meta(rn), deflator: meta(rd), base_date: b, n: dates.length, unit_hint: `${rn.label} at ${b} prices`,
        chart_url: chartUrl(origin, defChart),
        chart_note: "The chart puts the nominal series against the same series in constant prices; the gap between them is the inflation. Give the user the link.",
        points: pointsOut(dates, real) });
    }),
  );

  server.registerTool(
    "predict",
    {
      title: "Recommend a method and predict",
      description: "One call for 'where is this going?'. It tests every forecasting method that suits the series on its own past (re-fitting at a run of earlier dates and scoring what actually happened), says which methods are worth using and why, picks the winner, and forecasts with it. Returns the ranked methods with their out-of-sample error, whether the winner genuinely beats assuming no change, the dated forecast with a 95% band, and a chart link. Pass method to override the recommendation.",
      inputSchema: {
        series: REF,
        horizon: z.number().int().min(1).max(36).default(12),
        origins: z.number().int().min(4).max(40).default(12).describe("How many past dates to test each method at"),
        method: z.enum(["auto", "naive", "drift", "seasonal_naive", "holt", "holt_winters", "ar", "arima"]).default("auto").describe("auto = use the method that wins the test"),
        ar_order: z.number().int().min(1).max(12).default(2),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, horizon, origins, method, ar_order }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      const f = detectFrequency(dates);
      const H = horizon, seasonal = f.period > 1;
      const minTrain = Math.max(24, 3 * (seasonal ? f.period : 1), 3 * ar_order + 6);
      if (v.length < minTrain + H + 4) return fail(`Only ${v.length} observations of ${r.label}; a ${H}-step test needs at least ${minTrain + H + 4}. Ask for a shorter horizon, or forecast without the test.`);
      const last = v[v.length - 1], lastD = dates[dates.length - 1];
      const MAX_TRAIN = 600;
      const mk = (name: string) => (train0: number[]) => {
        const t = train0.length > MAX_TRAIN ? train0.slice(-MAX_TRAIN) : train0;
        const lastV = t[t.length - 1];
        if (name === "naive") return new Array<number>(H).fill(lastV);
        if (name === "drift") return Array.from({ length: H }, (_, h) => lastV + ((h + 1) * (lastV - t[0])) / (t.length - 1));
        if (name === "seasonal_naive") return Array.from({ length: H }, (_, h) => t[t.length - f.period + (h % f.period)]);
        if (name === "holt") return S.holtWinters(t, H, 1).forecast;
        if (name === "holt_winters") return S.holtWinters(t, H, f.period).forecast;
        if (name === "ar") return S.arForecast(t, ar_order, H).forecast;
        return S.autoArima(t, H).forecast;
      };
      const candidates = ["naive", "drift", ...(seasonal ? ["seasonal_naive", "holt_winters"] : []), "holt", "ar", "arima"];
      const scored: Array<{ method: string; rmse: number; mape: number | null; bias: number; errs: number[] }> = [];
      const skipped: string[] = [];
      let origIdx: number[] = [];
      for (const name of candidates) {
        try {
          const bt = S.rollingOrigin(v, mk(name), H, origins, minTrain, 1);
          if (bt.failures === bt.origins.length) { skipped.push(name); continue; }
          origIdx = bt.origins;
          const flatE = bt.errors.flat();
          const flatA = bt.origins.flatMap((o) => Array.from({ length: H }, (_, h) => v[o + 1 + h]));
          const m = S.errorMetrics(flatE, flatA);
          scored.push({ method: name, rmse: m.rmse, mape: m.mape, bias: m.bias, errs: bt.errors.map((row) => row[H - 1]) });
        } catch { skipped.push(name); }
      }
      if (!scored.length) return fail(`No forecasting method could be tested on ${r.label}: ${skipped.join(", ")} all failed. The series may be too short or too irregular.`);
      scored.sort((a, b) => a.rmse - b.rmse);
      const best = scored[0], naive = scored.find((x) => x.method === "naive");
      let beatsNaive: boolean | null = null, dmP: number | null = null;
      if (naive && naive !== best) {
        try { const d = S.dieboldMariano(best.errs, naive.errs, H); beatsNaive = d.better === 1; dmP = d.p; }
        catch { beatsNaive = null; }
      }
      const chosen = method === "auto" ? best.method : method;
      const label: Record<string, string> = { naive: "assume no change", drift: "straight-line trend", seasonal_naive: "repeat last year's pattern", holt: "trend smoothing", holt_winters: "seasonal smoothing", ar: "autoregression", arima: "ARIMA" };
      // The forecast itself, fitted on everything
      let fc: number[], sd: number, detail: string;
      if (chosen === "naive") { fc = new Array<number>(H).fill(last); sd = S.sd(S.diff(v)); detail = "assume no change"; }
      else if (chosen === "drift") { const slope = (last - v[0]) / (v.length - 1); fc = Array.from({ length: H }, (_, h) => last + (h + 1) * slope); sd = S.sd(S.diff(v)); detail = "straight-line trend"; }
      else if (chosen === "seasonal_naive") { fc = Array.from({ length: H }, (_, h) => v[v.length - f.period + (h % f.period)]); sd = S.sd(S.diff(v, f.period)); detail = "repeat last year's pattern"; }
      else if (chosen === "ar") { const a = S.arForecast(v, ar_order, H); fc = a.forecast; sd = a.resid_sd; detail = `autoregression of order ${ar_order}`; }
      else if (chosen === "arima") { const a = S.autoArima(v, H); fc = a.forecast; sd = a.resid_sd; detail = `ARIMA(${a.p},${a.d},${a.q})`; }
      else { const hw = S.holtWinters(v, H, chosen === "holt_winters" && seasonal ? f.period : 1); fc = hw.forecast; sd = hw.resid_sd; detail = chosen === "holt_winters" ? `seasonal smoothing, period ${f.period}` : "trend smoothing"; }
      const future = futureDates(lastD, H, f.frequency);
      const rows = future.map((d, i) => ({ date: d, value: r4(fc[i]), lo95: r4(fc[i] - 1.96 * sd * Math.sqrt(i + 1)), hi95: r4(fc[i] + 1.96 * sd * Math.sqrt(i + 1)) }));
      const finite = rows.filter((x) => x.value !== null && x.lo95 !== null && x.hi95 !== null);
      const chartSpec: PlotSpec = {
        series: [series, { points: [[lastD, r4(last) as number], ...finite.map((x) => [x.date, x.value as number] as [string, number])], label: `${r.label}, ${detail}` }],
        bands: [{ series: 1, label: "95% band", points: [[lastD, r4(last) as number, r4(last) as number], ...finite.map((x) => [x.date, x.lo95 as number, x.hi95 as number] as [string, number, number])] }],
        title: `${r.label}: ${detail}, ${H} ahead`, api: self,
      };
      const skillOf = (x: typeof best) => (naive && naive.rmse ? r3(1 - x.rmse / naive.rmse) : null);
      return text({
        ...meta(r), n: v.length, frequency: f.frequency, last_actual: [lastD, r4(last)],
        tested: { methods: scored.length, horizon: H, origins: origIdx.length, from: dates[origIdx[0]], to: dates[origIdx[origIdx.length - 1]],
          note: "Every method was re-fitted at each of those dates and asked to forecast forward, then scored against what actually happened." },
        methods: scored.map((x, i) => ({ rank: i + 1, method: x.method, what_it_does: label[x.method], typical_error: r4(x.rmse),
          error_pct: x.mape === null ? null : r3(x.mape), bias: r4(x.bias), better_than_no_change: x.method === "naive" ? 0 : skillOf(x), recommended: x.method === best.method })),
        skipped: skipped.length ? skipped.map((m) => ({ method: m, why: m === "seasonal_naive" || m === "holt_winters" ? "the data has no seasonal cycle" : "not enough history to fit it" })) : undefined,
        recommendation: { method: best.method, what_it_does: label[best.method],
          beats_no_change: beatsNaive, significance_p: dmP,
          why: best.method === "naive"
            ? "Nothing beat assuming no change, so the honest forecast is the last value with a band around it."
            : beatsNaive === true ? `It had the lowest error over the test, and the margin over assuming no change is statistically real.`
            : beatsNaive === false ? `It had the lowest error over the test, but the margin over assuming no change is inside the noise, so treat the path as indicative and the band as the real answer.`
            : `It had the lowest error over the test.` },
        used: { method: chosen, what_it_does: label[chosen], overridden: method !== "auto" },
        forecast: rows,
        chart_url: chartUrl(origin, chartSpec),
        reading: `Over ${origIdx.length} test dates, ${label[best.method]} forecast ${H} ${f.frequency === "annual" ? "years" : f.frequency === "quarterly" ? "quarters" : "periods"} ahead with a typical error of ${r4(best.rmse)}${naive && naive !== best ? `, against ${r4(naive.rmse)} for assuming no change` : ""}. ${method !== "auto" ? `You asked for ${label[chosen]}, so that is what the forecast below uses.` : ""} ${r.label} was ${r4(last)} in ${lastD}; the forecast for ${rows[rows.length - 1].date} is ${rows[rows.length - 1].value}, and nineteen times in twenty it should land between ${rows[rows.length - 1].lo95} and ${rows[rows.length - 1].hi95}.`.replace(/\s+/g, " ").trim(),
        caveat: "The band comes from how wrong the method was in the past and grows with the horizon. It assumes the future behaves like the sample: a policy change, a drought or a war is outside it. Test dates overlap, so the comparison between methods is sharper than the significance test.",
      });
    }),
  );

  server.registerTool(
    "forecast_evaluate",
    {
      title: "Forecast backtest (rolling origin)",
      description: "Which forecasting method actually works on this series? Re-fits every method at a series of past origins, forecasts the next `horizon` periods each time, and scores the errors against what happened: RMSE, MAE and MAPE by horizon and overall, a skill score against the naive no-change forecast, and Diebold-Mariano tests of whether the best method beats naive and the runner-up. Methods: naive, drift, seasonal_naive, holt, holt_winters, ar, arima. Run it before quoting a forecast; then call forecast with the winning method.",
      inputSchema: {
        series: REF,
        horizon: z.number().int().min(1).max(24).default(6).describe("Steps ahead scored at every origin"),
        origins: z.number().int().min(4).max(60).default(12).describe("How many past origins to re-fit at; the last one leaves room for a full horizon"),
        step: z.number().int().min(1).max(12).default(1).describe("Periods between origins"),
        methods: z.array(z.enum(["naive", "drift", "seasonal_naive", "holt", "holt_winters", "ar", "arima"])).min(1).optional().describe("Default: every method the series supports"),
        ar_order: z.number().int().min(1).max(12).default(2),
        max_train: z.number().int().min(48).max(3000).default(600).describe("At each origin, fit on at most this many of the latest observations (a rolling window once the sample is longer)"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, horizon, origins, step, methods, ar_order, max_train }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      const f = detectFrequency(dates);
      const H = horizon;
      const seasonalOk = f.period > 1;
      const wanted = methods ?? ["naive", "drift", ...(seasonalOk ? ["seasonal_naive", "holt_winters"] : []), "holt", "ar", "arima"];
      const minTrain = Math.max(24, 3 * (seasonalOk ? f.period : 1), 3 * ar_order + 6);
      const need = minTrain + H + (origins - 1) * step;
      if (v.length < minTrain + H + 4) return fail(`Only ${v.length} observations; need at least ${minTrain + H + 4} for a ${H}-step backtest (${minTrain} to train on, ${H} to score, a few origins).`);
      const skipped: Array<{ method: string; why: string }> = [];
      const lastVal = (a: number[]) => a[a.length - 1];
      let arimaOrder: [number, number, number] | null = null;
      const forecasters: Record<string, (train: number[]) => number[]> = {
        naive: (t) => new Array<number>(H).fill(lastVal(t)),
        drift: (t) => Array.from({ length: H }, (_, h) => lastVal(t) + ((h + 1) * (lastVal(t) - t[0])) / (t.length - 1)),
        seasonal_naive: (t) => Array.from({ length: H }, (_, h) => t[t.length - f.period + (h % f.period)]),
        holt: (t) => S.holtWinters(t, H, 1).forecast,
        holt_winters: (t) => S.holtWinters(t, H, f.period).forecast,
        ar: (t) => S.arForecast(t, ar_order, H).forecast,
        arima: (t) => {
          if (!arimaOrder) { const a = S.autoArima(t, H); arimaOrder = [a.p, a.d, a.q]; return a.forecast; }
          return S.arima(t, arimaOrder[0], arimaOrder[1], arimaOrder[2], H).forecast;
        },
      };
      const runs: Array<{ method: string; bt: S.BacktestErrors }> = [];
      for (const m of wanted) {
        if ((m === "seasonal_naive" || m === "holt_winters") && !seasonalOk) { skipped.push({ method: m, why: `${f.frequency} data has no seasonal period` }); continue; }
        try {
          const bt = S.rollingOrigin(v, (train) => forecasters[m](train.length > max_train ? train.slice(-max_train) : train), H, origins, minTrain, step);
          if (bt.failures === bt.origins.length) { skipped.push({ method: m, why: "failed at every origin" }); continue; }
          runs.push({ method: m, bt });
        } catch (e) { skipped.push({ method: m, why: e instanceof Error ? e.message : String(e) }); }
      }
      if (!runs.length) return fail(`No method could be evaluated: ${skipped.map((s) => `${s.method} (${s.why})`).join("; ")}`);
      const orig = runs[0].bt.origins;
      const actualsAt = (h: number) => orig.map((o) => v[o + 1 + h]);
      const scored = runs.map(({ method, bt }) => {
        const byH = Array.from({ length: H }, (_, h) => S.errorMetrics(bt.errors.map((row) => row[h]), actualsAt(h)));
        const allE = bt.errors.flat(), allA = orig.flatMap((o) => Array.from({ length: H }, (_, h) => v[o + 1 + h]));
        const overall = S.errorMetrics(allE, allA);
        return { method, bt, byH, overall };
      }).sort((a, b) => a.overall.rmse - b.overall.rmse);
      const naive = scored.find((s) => s.method === "naive");
      const best = scored[0], second = scored[1];
      const dm = (a: typeof best, b: typeof best, h: number) => {
        try {
          const d = S.dieboldMariano(a.bt.errors.map((row) => row[h]), b.bt.errors.map((row) => row[h]), h + 1);
          const verdict = d.degenerate ? (d.better === 1 ? `${a.method} is better at every origin (constant gap, no sampling variance)` : d.better === 2 ? `${b.method} is better at every origin (constant gap, no sampling variance)` : "identical losses") : d.better === 1 ? `${a.method} is better` : d.better === 2 ? `${b.method} is better` : "no significant difference";
          return { horizon: h + 1, statistic: Number.isFinite(d.statistic) ? r3(d.statistic) : null, p: r4(d.p), n: d.n, verdict, degenerate: d.degenerate || undefined };
        } catch (e) { return { horizon: h + 1, statistic: null, p: null, n: 0, verdict: `not tested: ${e instanceof Error ? e.message : String(e)}`, degenerate: undefined }; }
      };
      const tests: Record<string, unknown> = {};
      if (naive && naive !== best) tests[`${best.method}_vs_naive`] = [dm(best, naive, 0), H > 1 ? dm(best, naive, H - 1) : null].filter(Boolean);
      if (second && second !== naive) tests[`${best.method}_vs_${second.method}`] = [dm(best, second, 0), H > 1 ? dm(best, second, H - 1) : null].filter(Boolean);
      const skill = (s: typeof best) => (naive && Number.isFinite(naive.overall.rmse) && naive.overall.rmse > 0 ? r3(1 - s.overall.rmse / naive.overall.rmse) : null);
      const bestVsNaive = tests[`${best.method}_vs_naive`] as Array<{ verdict: string; degenerate?: boolean }> | undefined;
      const beatsNaive = bestVsNaive?.some((t) => t.verdict.startsWith(best.method) && !t.degenerate);
      const degenerateWin = !beatsNaive && bestVsNaive?.some((t) => t.verdict.startsWith(best.method) && t.degenerate);
      const naiveTested = bestVsNaive?.some((t) => !t.verdict.startsWith("not tested") && !t.degenerate);
      const methodArg = best.method === "naive" || best.method === "drift" || best.method === "seasonal_naive" ? null : best.method;
      const hAxisF = Array.from({ length: H }, (_, i) => hx(i + 1));
      const scoreChart: PlotSpec = {
        series: scored.slice(0, 8).map((x) => inline(x.method, hAxisF, x.byH.map((mm) => mm.rmse))),
        xaxis: "number", xlabel: `periods ahead (${f.frequency})`, title: `${r.label}: forecast error by how far ahead`, api: self,
      };
      return text({
        ...meta(r), n: v.length, frequency: f.frequency, horizon: H,
        chart_url: chartUrl(origin, scoreChart),
        chart_note: "The chart is each method's out-of-sample error against the horizon: the lines cross when one method is better close in and another further out. Give the user the link.",
        origins: { count: orig.length, step, first: dates[orig[0]], last: dates[orig[orig.length - 1]], scored_through: dates[orig[orig.length - 1] + H], min_training_points: minTrain, training_window: v.length > max_train ? `rolling, last ${max_train} observations` : "expanding, all history" },
        arima_order: arimaOrder ? { order: arimaOrder, note: "Chosen by AIC on the first training window and held fixed after that" } : undefined,
        ranking: scored.map((s, i) => ({
          rank: i + 1, method: s.method,
          rmse: r4(s.overall.rmse), mae: r4(s.overall.mae), mape_pct: s.overall.mape === null ? null : r3(s.overall.mape), bias: r4(s.overall.bias),
          skill_vs_naive: s.method === "naive" ? 0 : skill(s),
          by_horizon: s.byH.map((m, h) => ({ h: h + 1, rmse: r4(m.rmse), mae: r4(m.mae), mape_pct: m.mape === null ? null : r3(m.mape) })),
          failed_origins: s.bt.failures || undefined,
        })),
        diebold_mariano: tests,
        skipped: skipped.length ? skipped : undefined,
        reading: [
          `Over ${orig.length} origins from ${dates[orig[0]]} to ${dates[orig[orig.length - 1]]}, ${best.method} had the lowest ${H}-step RMSE (${r4(best.overall.rmse)})${naive && naive !== best ? ` against ${r4(naive.overall.rmse)} for naive, a skill of ${r3((skill(best) ?? 0) * 100)}%` : ""}.`,
          naive && naive !== best ? (beatsNaive ? "The Diebold-Mariano test says that improvement is real at 5%." : degenerateWin ? `${best.method} beats naive by the same margin at every origin, so there is no sampling variation to test: the series is close to deterministic over this window.` : naiveTested ? "The Diebold-Mariano test cannot distinguish it from naive: the series is close to unpredictable at this horizon and a no-change forecast is as honest a statement." : "Too few origins for a Diebold-Mariano test (it needs 6 paired errors), so whether that gap is real is untested; raise origins.") : best.method === "naive" ? "Naive wins: nothing here forecasts better than the last value. Quote the last value with the error band, not a model." : "",
          Math.abs(best.overall.bias) > 0.5 * best.overall.mae ? `${best.method} is biased (mean error ${r4(best.overall.bias)}): it systematically ${best.overall.bias > 0 ? "under" : "over"}-forecasts, a sign of a trend or level shift the method does not track.` : "",
          methodArg ? `Next: forecast with method='${methodArg}'.` : "",
        ].filter(Boolean).join(" "),
        recommended_call: methodArg ? { tool: "forecast", args: { series, method: methodArg, horizon: H, ...(methodArg === "ar" ? { ar_order } : {}), ...(methodArg === "arima" && arimaOrder ? { arima_order: arimaOrder } : {}) } } : null,
        caveat: `Each origin re-estimates the model on data up to that point, so the scores are genuinely out of sample, but ${orig.length} origins is a small sample for the Diebold-Mariano test and adjacent origins overlap; treat a p-value near 0.05 as a coin toss. Errors are in the units of the series (${r.transform === "none" ? "levels" : r.transform}); MAPE is undefined when an actual is zero. ${need > v.length ? `Fewer origins than requested fit the sample.` : ""}`.trim(),
      });
    }),
  );

  server.registerTool(
    "local_projections",
    {
      title: "Local projections (Jordà impulse response)",
      description: "Impulse response of y to a shock in x by local projections: for each horizon h, regress y(t+h) on x(t) with lags of both (and of any controls) and report the coefficient with Newey-West bands. Unlike var_model it imposes no lag structure across horizons and gives a confidence band per horizon, at the cost of noisier long-horizon estimates. Pass stationary series (growth rates, differences). Responses are per unit of x and per one-standard-deviation shock, plus the cumulative response.",
      inputSchema: {
        y: REF, x: REF,
        controls: z.array(REF).max(3).optional().describe("Extra series whose lags enter as controls"),
        horizon: z.number().int().min(1).max(40).default(12),
        lags: z.number().int().min(1).max(8).optional().describe("Lags of y, x and controls as controls; default 4 (2 for annual data)"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ y, x, controls, horizon, lags }) => {
      const ry = await get(y), rx = await get(x);
      const rc = await Promise.all((controls ?? []).map(get));
      const { dates, columns } = align([ry.series, rx.series, ...rc.map((c) => c.series)]);
      if (dates.length < 40) return fail(`Only ${dates.length} shared dates; need 40 or more.`);
      const f = detectFrequency(dates);
      const p = lags ?? (f.frequency === "annual" ? 2 : 4);
      let lp: S.LpResult;
      try { lp = S.localProjections(columns[0], columns[1], horizon, p, columns.slice(2)); } catch (e) { return fail(e instanceof Error ? e.message : String(e)); }
      const warnings: string[] = [];
      [ry, rx, ...rc].forEach((r, i) => { try { if (!S.adf(columns[i], "c").reject_unit_root_at) warnings.push(`${r.label} looks non-stationary; local projections on levels can be spurious. Use transform='pct_change' or 'diff'.`); } catch { /* skip */ } });
      let cum = 0;
      const rows = lp.horizons.map((h) => {
        cum += h.beta;
        return { h: h.h, response: r4(h.beta), se: r4(h.se), lo90: r4(h.beta - 1.645 * h.se), hi90: r4(h.beta + 1.645 * h.se), lo95: r4(h.beta - 1.96 * h.se), hi95: r4(h.beta + 1.96 * h.se), t: r3(h.t), p: r4(h.p), significant_5pct: h.p < 0.05, response_to_1sd_shock: r4(h.beta * lp.shock_sd), cumulative: r4(cum), n: h.n };
      });
      const sig = rows.filter((r) => r.significant_5pct).map((r) => r.h);
      const peak = rows.reduce((a, b) => (Math.abs(b.response ?? 0) > Math.abs(a.response ?? 0) ? b : a), rows[0]);
      const impact = rows[0];
      const hx = (h: number) => String(h).padStart(2, "0");
      const finiteRows = rows.filter((r) => r.response !== null && r.lo95 !== null && r.hi95 !== null && r.cumulative !== null);
      const chartSpec: PlotSpec = {
        series: [
          { points: finiteRows.map((r) => [hx(r.h), r.response as number]), label: `response of ${ry.label} to a unit shock in ${rx.label}` },
          { points: finiteRows.map((r) => [hx(r.h), r.cumulative as number]), label: "cumulative response" },
        ],
        bands: [{ series: 0, label: "95% band", points: finiteRows.map((r) => [hx(r.h), r.lo95 as number, r.hi95 as number]) }],
        xaxis: "number", xlabel: `periods after the shock (${f.frequency})`, title: `Local projections: ${ry.label} after a shock to ${rx.label}`, api: self,
      };
      return text({
        y: meta(ry), x: meta(rx), controls: rc.map(meta), n: dates.length, first: dates[0], last: dates[dates.length - 1], frequency: f.frequency, lags: p, horizon,
        shock_sd: r4(lp.shock_sd),
        responses: rows,
        chart_url: chartUrl(origin, chartSpec),
        peak: { h: peak.h, response: peak.response, response_to_1sd_shock: peak.response_to_1sd_shock },
        cumulative_at_horizon: rows[rows.length - 1].cumulative,
        reading: [
          `A one-unit move in ${rx.label} shifts ${ry.label} by ${impact.response} on impact${impact.significant_5pct ? "" : " (not significant)"}, with the largest response at h=${peak.h} (${peak.response}, or ${peak.response_to_1sd_shock} for a typical one-sd shock).`,
          sig.length ? `Significant at 5% at horizons ${sig.length > 6 ? `${sig[0]}..${sig[sig.length - 1]} (${sig.length} of ${rows.length})` : sig.join(", ")}.` : "No horizon is significant at 5%: no measurable response once the lags are controlled for.",
          `Cumulative response after ${horizon} periods: ${rows[rows.length - 1].cumulative}.`,
          "Compare with var_model: if both agree on sign and timing the finding is robust to the lag structure; if they differ, the VAR is imposing shape the data do not support.",
        ].join(" "),
        warnings,
        caveat: `Newey-West bandwidth equals the horizon, which handles the overlap the h-step target creates. The response is to x(t) after controlling for ${p} lags of everything, so it is a reduced-form timing relation, not an identified structural shock; contemporaneous feedback from y to x within a period is not ruled out. Bands widen and the sample shrinks by one observation per horizon.`,
      });
    }),
  );

  server.registerTool(
    "iv_regress",
    {
      title: "Instrumental variables (2SLS)",
      description: "Two-stage least squares for when x is endogenous: it is set jointly with y, or a confounder moves both, so OLS is biased. Needs at least one instrument per endogenous regressor: a series that moves x but affects y only through x. Returns the 2SLS coefficients with plain and Newey-West errors next to OLS, the first-stage F of the excluded instruments (below 10 means weak instruments and unreliable estimates), the Wu-Hausman test of whether x is endogenous at all (if not, OLS is fine and more precise), and the Sargan over-identification test when there are more instruments than endogenous regressors. Typical: a supply shifter (weather, input cost) as the instrument for quantity in a demand equation, or a policy rate abroad for the domestic one.",
      inputSchema: {
        y: REF,
        x: z.array(REF).min(1).max(2).describe("Endogenous regressors"),
        instruments: z.array(REF).min(1).max(4).describe("Excluded instruments: move x, affect y only through x"),
        exog: z.array(REF).max(4).optional().describe("Exogenous controls, in both stages"),
        hac_lags: z.number().int().min(0).max(24).optional().describe("Newey-West bandwidth; default 4(n/100)^(2/9)"),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ y, x, instruments, exog, hac_lags }) => {
      const ry = await get(y);
      const rx = await Promise.all(x.map(get)), rz = await Promise.all(instruments.map(get)), rw = await Promise.all((exog ?? []).map(get));
      const { dates, columns } = align([ry.series, ...rx.map((r) => r.series), ...rz.map((r) => r.series), ...rw.map((r) => r.series)]);
      if (dates.length < 20) return fail(`Only ${dates.length} shared dates across y, x, instruments and controls; need 20 or more.`);
      const T = dates.length;
      const col = (i: number) => columns[i];
      const endog = Array.from({ length: T }, (_, t) => rx.map((_, j) => col(1 + j)[t]));
      const inst = Array.from({ length: T }, (_, t) => rz.map((_, j) => col(1 + rx.length + j)[t]));
      const ex = rw.length ? Array.from({ length: T }, (_, t) => rw.map((_, j) => col(1 + rx.length + rz.length + j)[t])) : [];
      let iv: S.IvResult;
      try { iv = S.twoSLS(col(0), endog, inst, ex, hac_lags); } catch (e) { return fail(e instanceof Error ? e.message : String(e)); }
      const names = ["const", ...rx.map((r) => r.label), ...rw.map((r) => r.label)];
      const table = names.map((term, j) => ({
        term, coef_2sls: r4(iv.beta[j]), se: r4(iv.se[j]), t: r3(iv.t[j]), p: r4(iv.p[j]),
        hac_se: r4(iv.hac_se[j]), hac_t: r3(iv.beta[j] / iv.hac_se[j]), hac_p: r4(S.tTwoSidedP(iv.beta[j] / iv.hac_se[j], iv.n - iv.k)),
        coef_ols: r4(iv.ols.beta[j]), ols_se: r4(iv.ols.se[j]),
      }));
      const weak = iv.first_stage.map((f, j) => ({ endogenous: rx[j].label, F_excluded_instruments: r3(f.F_excluded), p: r4(f.F_p), df: f.df, r2: r4(f.r2), partial_r2: r4(f.partial_r2), weak: f.F_excluded < 10 }));
      const anyWeak = weak.some((w) => w.weak);
      const endogenous = iv.wu_hausman.p < 0.05;
      const warnings: string[] = [];
      const levels = ry.transform === "none" || ry.transform === "log" || ry.transform === "rebase";
      if (levels && T >= 20) {
        try {
          const ay = S.adf(col(0), "c");
          if (!ay.reject_unit_root_at && rx.some((_, j) => { try { return !S.adf(col(1 + j), "c").reject_unit_root_at; } catch { return false; } })) warnings.push("y and at least one x look non-stationary in levels; 2SLS on levels can be spurious like OLS. Use transform='pct_change' or 'diff', or establish cointegration first.");
        } catch { /* skip */ }
      }
      const allLog = [ry, ...rx, ...rw].every((r) => r.transform === "log");
      // The two fits side by side: where 2SLS and OLS part company is where endogeneity bites.
      const Xrow = (t: number) => [1, ...endog[t], ...(ex.length ? ex[t] : [])];
      const fit2 = dates.map((_, t) => Xrow(t).reduce((a, xv, j) => a + xv * iv.beta[j], 0));
      const fitO = dates.map((_, t) => Xrow(t).reduce((a, xv, j) => a + xv * iv.ols.beta[j], 0));
      const ivChart: PlotSpec = {
        series: [inline(ry.label, dates, col(0)), inline("2SLS fit", dates, fit2), inline("OLS fit", dates, fitO)],
        title: `${ry.label}: 2SLS against OLS`, api: self,
      };
      return text({
        y: meta(ry), x: rx.map(meta), instruments: rz.map(meta), exog: rw.map(meta),
        chart_url: chartUrl(origin, ivChart),
        chart_note: "The chart draws the series with both fits: a visible gap between the 2SLS and OLS lines is the bias the instruments are correcting.",
        n: iv.n, first: dates[0], last: dates[T - 1], identification: iv.L === iv.m ? "just identified" : `over-identified (${iv.L} instruments for ${iv.m} endogenous regressor${iv.m > 1 ? "s" : ""})`,
        coefficients: table,
        r2: r4(iv.r2), sigma: r4(iv.sigma), hac_lags: iv.hac_lag,
        first_stage: weak,
        wu_hausman: { F: r3(iv.wu_hausman.F), p: r4(iv.wu_hausman.p), df: iv.wu_hausman.df, endogenous_at_5pct: endogenous, null_hypothesis: "x is exogenous: OLS and 2SLS estimate the same thing" },
        sargan: iv.sargan ? { statistic: r3(iv.sargan.statistic), p: r4(iv.sargan.p), df: iv.sargan.df, instruments_valid_at_5pct: iv.sargan.p >= 0.05, null_hypothesis: "The over-identifying instruments are uncorrelated with the error" } : null,
        elasticities: allLog ? "Both sides are in logs, so each coefficient is an elasticity." : undefined,
        reading: [
          anyWeak ? `Weak instruments: first-stage F ${weak.filter((w) => w.weak).map((w) => `${w.F_excluded_instruments} for ${w.endogenous}`).join(", ")} is below 10, so the 2SLS estimate is biased towards OLS and its standard errors understate the uncertainty. Find a stronger instrument before quoting the number.` : `Instruments are strong (first-stage F ${weak.map((w) => w.F_excluded_instruments).join(", ")}).`,
          endogenous ? `Wu-Hausman rejects exogeneity (p ${r4(iv.wu_hausman.p)}): OLS is biased here, so the 2SLS coefficient on ${rx.map((r) => r.label).join(", ")} (${table.slice(1, 1 + rx.length).map((r) => r.coef_2sls).join(", ")}) is the one to quote, against ${table.slice(1, 1 + rx.length).map((r) => r.coef_ols).join(", ")} by OLS.` : `Wu-Hausman does not reject exogeneity (p ${r4(iv.wu_hausman.p)}): OLS and 2SLS agree within noise, and OLS is the more precise estimate.`,
          iv.sargan ? (iv.sargan.p < 0.05 ? `Sargan rejects (p ${r4(iv.sargan.p)}): at least one instrument affects y directly, so the exclusion restriction fails and the estimate is not identified.` : `Sargan does not reject (p ${r4(iv.sargan.p)}): the over-identifying instruments are consistent with each other.`) : "Just identified: the exclusion restriction cannot be tested, it has to be argued.",
        ].join(" "),
        warnings,
        caveat: "2SLS is consistent, not unbiased: in small samples it leans towards OLS, more so with weak instruments. The instrument must be relevant (testable, first-stage F) and excludable (only arguable: Sargan tests consistency among instruments, not validity). HAC errors use the structural residuals and the fitted regressors.",
      });
    }),
  );

  server.registerTool(
    "suggest_analysis",
    {
      title: "Suggest an analysis plan",
      description: "Inspect one or more series (frequency, length, integration order, trend, seasonality, volatility clustering, overlap) and return an ordered plan of tool calls with the reason for each, plus the pitfalls the data carry. Routes to the right member of the toolkit, including forecast_evaluate before forecast, local_projections next to var_model, iv_regress when the question is causal and an instrument exists, volatility for ARCH effects, principal_components for three or more series, quantile_regress for tail behaviour and panel_regress when the series come from a country panel. Use it before choosing a method.",
      inputSchema: { series: z.array(REF).min(1).max(4), question: z.string().optional().describe("What you want to know, e.g. 'does feed price drive cattle price?'") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, question }) => {
      const rs = await Promise.all(series.map(get));
      const ps = rs.map(profile);
      const facts = ps.map((p, i) => ({
        label: rs[i].label, n: p.n, frequency: p.frequency, first: p.dates[0], last: p.dates[p.n - 1],
        integration_order: integrationOrder(p.adfLevel, p.adfDiff),
        trending: p.trendFit ? Math.abs(p.trendFit.t[1]) > 4 : false,
        drifts: Math.abs(S.driftT(p.v)) > 2,
        seasonal_strength: p.decomposition ? r3(p.decomposition.seasonal_strength) : null,
        positive_only: p.v.every((x) => x > 0),
        volatility_clustering_p: (() => { const a = archProbe(p.v); return a ? r4(a.p) : null; })(),
        caveats: rs[i].caveats,
      }));
      const plan: Array<{ step: number; tool: string; why: string; args?: Record<string, unknown> }> = [];
      const pitfalls: string[] = [];
      let step = 1;
      const refOf = (i: number) => ({ ...series[i] });

      for (const f of facts) for (const c of f.caveats) pitfalls.push(`${f.label}: ${c}`);
      const freqs = new Set(facts.map((f) => f.frequency));
      const mixed = freqs.size > 1;
      if (mixed) {
        pitfalls.push(`Mixed frequencies (${[...freqs].join(", ")}). Align to the coarsest with frequency='annual_mean' (or annual_last for stocks and index levels) on the finer series before any joint test.`);
      }
      for (const [i, f] of facts.entries()) {
        if (f.seasonal_strength !== null && (f.seasonal_strength as number) > 0.5) {
          pitfalls.push(`${f.label} is strongly seasonal (strength ${f.seasonal_strength}). Compare year-on-year (transform='yoy') or decompose first.`);
          plan.push({ step: step++, tool: "decompose", why: `Quantify and remove the seasonal pattern in ${f.label}`, args: { series: refOf(i) } });
        }
      }
      for (const [i, f] of facts.entries()) {
        plan.push({ step: step++, tool: "describe_stats", why: `Baseline for ${f.label}: distribution, autocorrelation, unit root`, args: { series: refOf(i) } });
      }
      for (const [i, f] of facts.entries()) {
        if (f.volatility_clustering_p !== null && (f.volatility_clustering_p as number) < 0.05) {
          pitfalls.push(`${f.label}: volatility clusters (ARCH-LM p ${f.volatility_clustering_p}), so a constant-variance model understates risk in turbulent stretches and forecast bands are too narrow there.`);
          plan.push({ step: step++, tool: "volatility", why: `Model the changing variance of ${f.label}: persistence, current versus normal volatility, one-step forecast`, args: { series: { ...refOf(i), transform: f.positive_only ? "pct_change" : "diff" } } });
        }
      }
      const single = facts.length === 1;
      if (single) {
        const f = facts[0];
        if (f.trending || f.integration_order === "I(1)") plan.push({ step: step++, tool: "hp_filter", why: "Separate the trend from the cycle before reading turning points", args: { series: refOf(0) } });
        plan.push({ step: step++, tool: "structural_break", why: "Check whether one regime describes the whole sample before forecasting", args: { y: refOf(0) } });
        if (f.n >= 60) plan.push({ step: step++, tool: "forecast_evaluate", why: "Let a rolling backtest pick the method: out-of-sample error against naive, not in-sample fit", args: { series: refOf(0) } });
        plan.push({ step: step++, tool: "forecast", why: f.seasonal_strength !== null && (f.seasonal_strength as number) > 0.3 ? "Holt-Winters handles the seasonality; compare with AR" : "Holt linear trend, then compare with AR", args: { series: refOf(0), method: "auto" } });
      } else {
        const orders = facts.map((f) => f.integration_order);
        const allI1 = orders.every((o) => o === "I(1)");
        const allI0 = orders.every((o) => o === "I(0)");
        const stationaryArgs = (i: number) => ({ ...refOf(i), transform: facts[i].positive_only ? "pct_change" : "diff" });
        if (allI1) {
          pitfalls.push("All series are I(1): a levels regression or a levels correlation between them will look strong whether or not they are related. Test cointegration first.");
          // Drift, not a levels trend fit: a trend regression on a random walk is spurious and reads "trending" most of the time.
          const det = facts.some((f) => f.drifts) ? "constant" : "restricted_constant";
          if (det === "restricted_constant") pitfalls.push("None of the series drifts (mean first difference not significant), so the Johansen constant belongs inside the cointegrating relation (deterministic='restricted_constant'); the default unrestricted constant over-rejects on drift-free series.");
          if (facts.length > 2) plan.push({ step: step++, tool: "johansen", why: `${facts.length} I(1) series: count the cointegrating relations before choosing levels or differences`, args: { series: facts.map((_, i) => refOf(i)), deterministic: det } });
          plan.push({ step: step++, tool: "cointegration", why: "Both I(1): find out if a long-run relation exists before regressing levels", args: { a: refOf(0), b: refOf(1) } });
          plan.push({ step: step++, tool: "vecm", why: "If cointegrated: which series does the adjusting, how fast, and how far the system is from equilibrium now", args: { series: facts.map((_, i) => refOf(i)), deterministic: det } });
          plan.push({ step: step++, tool: "cross_correlation", why: "On growth rates, find which one moves first and by how many periods", args: { a: stationaryArgs(0), b: stationaryArgs(1) } });
          plan.push({ step: step++, tool: "granger_causality", why: "On growth rates, test predictive precedence in both directions", args: { a: stationaryArgs(0), b: stationaryArgs(1), lags: facts[0].frequency === "monthly" ? 3 : 2 } });
          plan.push({ step: step++, tool: "regress", why: "If cointegrated: levels regression (in logs for elasticities) is meaningful with HAC errors. If not: regress growth on growth.", args: { y: { ...refOf(0), transform: "log" }, x: [{ ...refOf(1), transform: "log" }] } });
        } else if (allI0) {
          plan.push({ step: step++, tool: "cross_correlation", why: "Stationary series: lead-lag structure on levels is valid", args: { a: refOf(0), b: refOf(1) } });
          plan.push({ step: step++, tool: "granger_causality", why: "Test predictive precedence in both directions", args: { a: refOf(0), b: refOf(1) } });
          plan.push({ step: step++, tool: "regress", why: "Levels regression with HAC errors; add x_lags for a distributed lag", args: { y: refOf(0), x: facts.slice(1).map((_, j) => refOf(j + 1)) } });
        } else {
          pitfalls.push(`Mixed integration orders (${orders.join(", ")}): put every series on a stationary footing (growth rates or differences) before regression or correlation.`);
          plan.push({ step: step++, tool: "cross_correlation", why: "On stationary transforms, find the lead-lag", args: { a: stationaryArgs(0), b: stationaryArgs(1) } });
          plan.push({ step: step++, tool: "granger_causality", why: "On stationary transforms, test precedence", args: { a: stationaryArgs(0), b: stationaryArgs(1) } });
          plan.push({ step: step++, tool: "regress", why: "Growth-on-growth regression with HAC errors", args: { y: stationaryArgs(0), x: facts.slice(1).map((_, j) => stationaryArgs(j + 1)) } });
        }
        if (facts.length >= 3) {
          plan.push({ step: step++, tool: "principal_components", why: `${facts.length} series: see whether one common factor drives most of their joint movement before modelling them one by one`, args: { series: facts.map((_, i) => stationaryArgs(i)) } });
        }
        if (facts[0].n >= 60) {
          plan.push({ step: step++, tool: "quantile_regress", why: "Check whether the relation is the same in calm and extreme periods, not only on average", args: { y: stationaryArgs(0), x: [stationaryArgs(1)] } });
        }
        plan.push({ step: step++, tool: "var_model", why: "On stationary transforms, trace how a shock to one series propagates to the others and how much of each series' variance the others explain", args: { series: facts.map((_, i) => stationaryArgs(i)) } });
        plan.push({ step: step++, tool: "local_projections", why: "The same impulse response without the VAR's lag structure, with a confidence band per horizon; agreement with var_model makes the timing robust", args: { y: stationaryArgs(0), x: stationaryArgs(1) } });
        plan.push({ step: step++, tool: "rolling", why: "Check whether the relationship is stable over time before quoting one number", args: { series: stationaryArgs(0), other: stationaryArgs(1), stat: "corr", window: facts[0].frequency === "monthly" ? 36 : 10 } });
        plan.push({ step: step++, tool: "structural_break", why: "Locate a regime change in the relation, then re-estimate on the stable sample", args: { y: stationaryArgs(0), x: stationaryArgs(1) } });
      }
      // Series drawn from a country panel (keys 'UNIT|INDICATOR'): the same question can be
      // asked of every country at once, which is a different and usually stronger test.
      const panel = (() => {
        const sets = series.map((r) => (r.dataset && r.series && r.series.includes("|") ? { ds: r.dataset, ind: r.series.slice(r.series.indexOf("|") + 1) } : null));
        if (sets.some((x) => x === null)) return null;
        const ds = new Set(sets.map((x) => x!.ds));
        if (ds.size !== 1) return null;
        const inds = [...new Set(sets.map((x) => x!.ind))];
        return { dataset: [...ds][0], indicators: inds };
      })();
      if (panel) {
        if (panel.indicators.length >= 2) {
          plan.push({ step: step++, tool: "panel_regress", why: `These come from the ${panel.dataset} country panel: estimate the same relation across every country at once, with country fixed effects and errors clustered by country, instead of one country at a time`, args: { dataset: panel.dataset, y: panel.indicators[0], x: panel.indicators.slice(1), effects: "unit" } });
        } else {
          pitfalls.push(`All ${facts.length} series are '${panel.indicators[0]}' for different countries in ${panel.dataset}. Comparing two countries answers a narrower question than panel_regress across all of them.`);
        }
      }
      if (!single && question && /\b(caus|effect of|impact of|drives?|driven|elasticit)/i.test(question)) {
        pitfalls.push("The question is causal. regress, granger_causality and local_projections measure timing and association, not causation: a common driver (energy, exchange rate, demand) can produce all of them. If a series exists that moves the explanatory variable but reaches the outcome only through it (a supply shifter, a foreign policy rate, weather), iv_regress with it as the instrument is the test that separates the two.");
      }
      return text({
        question: question ?? null,
        series: facts,
        pitfalls,
        plan,
        reporting: "Whatever survives: quote the sample window, the transform, the test statistic with its critical value or p-value, and the caveats above next to the number.",
      });
    }),
  );
}
