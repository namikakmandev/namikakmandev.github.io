/**
 * Tool registrations: live providers and the analysis layer.
 * Every analysis tool takes SeriesRef inputs (see resolve.ts), so a user can
 * point it at a local dataset, a live FRED or Eurostat pull, or their own
 * numbers, and gets the source and caveats echoed back with the result.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DataError, type Series } from "./data.js";
import { PROVIDERS, providerInfo, type ProviderEnv } from "./providers.js";
import { SeriesRefSchema, align, detectFrequency, futureDates, resolve, type Resolved, type SeriesRef } from "./resolve.js";
import { round, toPoints } from "./transform.js";
import * as S from "./stats.js";

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

function adfOut(a: S.AdfResult | null) {
  if (!a) return null;
  return { spec: a.spec, lags: a.lags, nobs: a.nobs, statistic: r3(a.statistic), critical: { "1%": r3(a.critical["1%"]), "5%": r3(a.critical["5%"]), "10%": r3(a.critical["10%"]) }, reject_unit_root_at: a.reject_unit_root_at };
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
      description: "External sources the server can pull from on demand (FRED, Eurostat, World Bank, ECB, OECD, Our World in Data, TCMB EVDS): coverage, id format, whether a key is configured, and starter ids.",
      inputSchema: {},
      annotations: { readOnlyHint: true },
    },
    wrap(async () => text({ providers: providerInfo(env), how: "search_external to find an id, fetch_external to pull it, or pass {provider, id} straight into any analysis tool." })),
  );

  server.registerTool(
    "search_external",
    {
      title: "Search a live provider",
      description: "Find series ids at a provider. FRED searches its full catalogue when FRED_API_KEY is set; World Bank searches all indicators; the others match against a curated starter list, so for those also try the provider's own website and pass the id to fetch_external.",
      inputSchema: {
        provider: z.enum(["fred", "eurostat", "worldbank", "ecb", "oecd", "owid", "evds"]),
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
      description: "Pull a series from FRED, Eurostat, World Bank, ECB, OECD, Our World in Data or TCMB EVDS as [date, value] points, with the same window and transform options as get_series. When the id returns several series (countries, dimensions), the reply lists their keys; pick one with 'series'.",
      inputSchema: {
        provider: z.enum(["fred", "eurostat", "worldbank", "ecb", "oecd", "owid", "evds"]),
        id: z.string(),
        params: z.record(z.string(), z.string()).optional().describe("Provider filters. Eurostat: dimension codes (geo, unit, ...). World Bank: country='TUR;USA' or 'all'. OWID: entities='Turkey;United States'. EVDS/ECB/OECD: start, end."),
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

export function registerAnalysis(server: McpServer, origin: string, env: ProviderEnv) {
  const get = (ref: SeriesRef) => resolve(ref, origin, env);
  const REF = SeriesRefSchema.describe("Series reference: {dataset, series} for local data, {provider, id[, series, params]} for live data, or {points} for inline data. Optional start, end, frequency, transform.");

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
      return text({
        ...meta(r), n: v.length, levels: adfOut(level), first_difference: adfOut(first), integration_order: order,
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
      description: "Regress y on one or more x series, aligned on shared dates. Newey-West robust standard errors, R², Durbin-Watson, AIC/BIC, residual tests, and a spurious-regression warning when levels are non-stationary. Set transform='log' on y and x for elasticities. Add lags of x for a distributed-lag model.",
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
      const allLog = [ry, ...rx].every((r) => r.transform === "log");
      return text({
        y: meta(ry), x: rx.map(meta),
        n: fit.n, k: fit.k, first: dates[x_lags], last: dates[dates.length - 1],
        coefficients: table,
        r2: r4(fit.r2), adj_r2: r4(fit.adj_r2), sigma: r4(fit.sigma), F: fit.F !== null ? r3(fit.F) : null, F_p: fit.F_p !== null ? r4(fit.F_p) : null,
        aic: r3(fit.aic), bic: r3(fit.bic), durbin_watson: r3(fit.dw), hac_lags: hac.lag,
        residuals: { ljung_box_p: r4(lb.p), jarque_bera_p: r4(S.jarqueBera(fit.resid).p) },
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
      return text({
        a: meta(ra), b: meta(rb), n: dates.length, first: dates[0], last: dates[dates.length - 1],
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
      return text({
        a: meta(ra), b: meta(rb), n: dates.length, first: dates[0], last: dates[dates.length - 1],
        significance_band: r3(band),
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
      return text({
        ...meta(r), n: v.length, frequency, lambda: lam,
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
      const offset = p === 12 ? Number(dates[0].slice(5, 7)) - 1 : p === 4 ? Number(dates[0].slice(6, 7)) - 1 : 0;
      return text({
        ...meta(r), n: v.length, period: p,
        seasonal_strength: r3(d.seasonal_strength), trend_strength: r3(d.trend_strength),
        seasonal_factors: d.seasonal_factors.map((x, i) => ({ season: labels[(i + offset) % p], effect: r4(x) })),
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
      description: "Project a series forward. auto picks Holt-Winters with seasonality for monthly/quarterly data and Holt's linear trend otherwise; ar fits an autoregression. Returns dated forecasts, an approximate 95% band from the residual spread, and in-sample fit.",
      inputSchema: {
        series: REF,
        horizon: z.number().int().min(1).max(60).default(12),
        method: z.enum(["auto", "holt_winters", "holt", "ar"]).default("auto"),
        ar_order: z.number().int().min(1).max(12).default(2),
      },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ series, horizon, method, ar_order }) => {
      const r = await get(series);
      const { dates, v } = values(r.series);
      const f = detectFrequency(dates);
      const future = futureDates(dates[dates.length - 1], horizon, f.frequency);
      const seasonalOk = f.period > 1 && v.length >= 3 * f.period;
      const m = method === "auto" ? (seasonalOk ? "holt_winters" : "holt") : method;
      let forecast: number[], fitted: number[], sdv: number, detail: Record<string, unknown>;
      if (m === "ar") {
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
      return text({
        ...meta(r), n: v.length, frequency: f.frequency, last_actual: [dates[dates.length - 1], r4(v[v.length - 1])],
        ...detail,
        in_sample: { mape_pct: r3(S.mean(ape) * 100), resid_sd: r4(sdv) },
        forecast: future.map((d, i) => ({ date: d, value: r4(forecast[i]), lo95: r4(forecast[i] - 1.96 * sdv * Math.sqrt(i + 1)), hi95: r4(forecast[i] + 1.96 * sdv * Math.sqrt(i + 1)) })),
        caveat: "The band grows with the square root of the horizon from the residual spread. It ignores parameter uncertainty and regime change, so treat it as a floor on the real uncertainty.",
      });
    }),
  );

  server.registerTool(
    "structural_break",
    {
      title: "Structural break",
      description: "Chow test at a given date, or a sup-F scan over the sample to locate the most likely break. Tests a shift in the mean of y, or in the relation y = a + b x when x is given.",
      inputSchema: { y: REF, x: REF.optional(), date: z.string().optional().describe("Candidate break date; omit to scan") },
      annotations: { readOnlyHint: true },
    },
    wrap(async ({ y, x, date }) => {
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
        return text({ y: meta(ry), x: rx ? meta(rx) : undefined, test: "Chow", break_date: dates[b], F: r3(c.F), p: r4(c.p), n_before: c.n1, n_after: c.n2,
          mean_before: r4(S.mean(before)), mean_after: r4(S.mean(after)), verdict: c.p < 0.05 ? "Break at this date (5%)" : "No evidence of a break at this date" });
      }
      const s = S.supF(yv, X);
      const top = [...s.scan].sort((p, q) => q.F - p.F).slice(0, 5).map((e) => ({ date: dates[e.index], F: r3(e.F) }));
      return text({ y: meta(ry), x: rx ? meta(rx) : undefined, test: "sup-F scan (Quandt-Andrews), 15% trimming", most_likely_break: dates[s.best.break_index], sup_F: r3(s.best.F),
        chow_p_at_that_date: r4(s.best.p), candidates: top,
        caveat: "The sup-F statistic has its own critical values (Andrews 1993), higher than the F-distribution's: the Chow p-value at a data-chosen date overstates significance. Use the scan to locate, then confirm with a Chow test at a date you can justify." });
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
      return text({ ...meta(r), other: ro ? meta(ro) : undefined, stat, window, n: out.length, points: out });
    }),
  );

  server.registerTool(
    "suggest_analysis",
    {
      title: "Suggest an analysis plan",
      description: "Inspect one or more series (frequency, length, integration order, trend, seasonality, overlap) and return an ordered plan of tool calls with the reason for each, plus the pitfalls the data carry. Use it before choosing a method.",
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
        seasonal_strength: p.decomposition ? r3(p.decomposition.seasonal_strength) : null,
        positive_only: p.v.every((x) => x > 0),
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
      const single = facts.length === 1;
      if (single) {
        const f = facts[0];
        if (f.trending || f.integration_order === "I(1)") plan.push({ step: step++, tool: "hp_filter", why: "Separate the trend from the cycle before reading turning points", args: { series: refOf(0) } });
        plan.push({ step: step++, tool: "structural_break", why: "Check whether one regime describes the whole sample before forecasting", args: { y: refOf(0) } });
        plan.push({ step: step++, tool: "forecast", why: f.seasonal_strength !== null && (f.seasonal_strength as number) > 0.3 ? "Holt-Winters handles the seasonality; compare with AR" : "Holt linear trend, then compare with AR", args: { series: refOf(0), method: "auto" } });
      } else {
        const orders = facts.map((f) => f.integration_order);
        const allI1 = orders.every((o) => o === "I(1)");
        const allI0 = orders.every((o) => o === "I(0)");
        const stationaryArgs = (i: number) => ({ ...refOf(i), transform: facts[i].positive_only ? "pct_change" : "diff" });
        if (allI1) {
          pitfalls.push("All series are I(1): a levels regression or a levels correlation between them will look strong whether or not they are related. Test cointegration first.");
          plan.push({ step: step++, tool: "cointegration", why: "Both I(1): find out if a long-run relation exists before regressing levels", args: { a: refOf(0), b: refOf(1) } });
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
        plan.push({ step: step++, tool: "rolling", why: "Check whether the relationship is stable over time before quoting one number", args: { series: stationaryArgs(0), other: stationaryArgs(1), stat: "corr", window: facts[0].frequency === "monthly" ? 36 : 10 } });
        plan.push({ step: step++, tool: "structural_break", why: "Locate a regime change in the relation, then re-estimate on the stable sample", args: { y: stationaryArgs(0), x: stationaryArgs(1) } });
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
