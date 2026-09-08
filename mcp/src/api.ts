/**
 * Plain HTTP surface next to /mcp, for things a browser page needs:
 *   GET  /v1/series?s=<json>   { series: [SeriesRef, ...] }  ->  points for each
 *   POST /v1/series            same, spec in the body
 * chart.html on the site calls this to draw what the `plot` tool links to.
 */
import { z } from "zod";
import { DataError } from "./data.js";
import type { ProviderEnv } from "./providers.js";
import { SeriesRefSchema, labelOf, resolve } from "./resolve.js";
import { analysisTools } from "./analysis.js";
import { round, toPoints } from "./transform.js";

/** A shaded band around one of the series: [x, low, high] points, inline (a band is a computed thing, not a reference). */
export const BandSchema = z.object({
  label: z.string().max(80).optional(),
  series: z.number().int().min(0).max(7).default(0).describe("Index of the series the band belongs to (colour and axis)"),
  points: z.array(z.tuple([z.string(), z.number(), z.number()])).min(1).max(400).describe("[date or horizon, low, high]"),
});
export type Band = z.infer<typeof BandSchema>;

export const PlotSpecSchema = z.object({
  series: z.array(SeriesRefSchema).min(1).max(8),
  title: z.string().max(200).optional(),
  scale: z.enum(["linear", "log"]).optional(),
  right: z.array(z.number().int().min(0).max(7)).optional(),
  dots: z.array(z.number().int().min(0).max(7)).optional().describe("Indexes of series to draw as points rather than a line (scatter)"),
  bands: z.array(BandSchema).max(4).optional(),
  xaxis: z.enum(["date", "number"]).optional().describe("number: x values are horizons or indexes, not dates"),
  xlabel: z.string().max(60).optional().describe("What a numeric x axis measures: horizon, lag, quantile, the name of the x series"),
  api: z.string().optional(),
});
export type PlotSpec = z.infer<typeof PlotSpecSchema>;

export interface SeriesPayload {
  label: string;
  source: string | null;
  caveats: string[];
  transform: string;
  n: number;
  first: string | null;
  last: string | null;
  points: [string, number][];
  error?: string;
}

/** Resolve every reference; a failing one comes back with `error` instead of killing the rest. */
export async function seriesPayload(spec: Pick<PlotSpec, "series">, origin: string, env: ProviderEnv): Promise<SeriesPayload[]> {
  const settled = await Promise.allSettled(spec.series.map((ref) => resolve(ref, origin, env)));
  return settled.map((r, i) => {
    if (r.status === "fulfilled") {
      const pts = toPoints(round(r.value.series));
      return { label: r.value.label, source: r.value.source, caveats: r.value.caveats, transform: r.value.transform,
        n: pts.length, first: pts[0]?.[0] ?? null, last: pts[pts.length - 1]?.[0] ?? null, points: pts };
    }
    const e = r.reason;
    return { label: labelOf(spec.series[i]), source: null, caveats: [], transform: spec.series[i].transform ?? "none",
      n: 0, first: null, last: null, points: [], error: e instanceof Error ? e.message : String(e) };
  });
}

/** The spec travels in the chart page's URL fragment as base64url JSON. */
export function encodeSpec(spec: PlotSpec): string {
  const bytes = new TextEncoder().encode(JSON.stringify(spec));
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function chartUrl(origin: string, spec: PlotSpec): string {
  return `${origin.replace(/\/$/, "")}/chart.html#${encodeSpec(spec)}`;
}

export async function handleSeriesRequest(request: Request, origin: string, env: ProviderEnv): Promise<{ status: number; body: unknown }> {
  let raw: unknown;
  try {
    if (request.method === "POST") raw = await request.json();
    else {
      const s = new URL(request.url).searchParams.get("s");
      if (!s) return { status: 400, body: { error: "Pass the spec as ?s=<json> or POST it as JSON: {\"series\":[{\"dataset\":\"us-prices\",\"series\":\"cattle_ppi\"}]}" } };
      raw = JSON.parse(s);
    }
  } catch (e) {
    return { status: 400, body: { error: `Spec is not valid JSON: ${e instanceof Error ? e.message : String(e)}` } };
  }
  const parsed = PlotSpecSchema.pick({ series: true }).safeParse(raw);
  if (!parsed.success) return { status: 400, body: { error: "Invalid spec", issues: parsed.error.issues.slice(0, 10) } };
  try {
    const series = await seriesPayload(parsed.data, origin, env);
    return { status: 200, body: { series } };
  } catch (e) {
    if (e instanceof DataError) return { status: 400, body: { error: e.message } };
    throw e;
  }
}

/**
 * POST /v1/analyze  {"tool":"forecast","args":{...}}
 * GET  /v1/analyze?tool=forecast&args=<json>
 *
 * The same handlers the MCP tools use, reachable from a plain web page: a
 * browser can run a forecast or find a structural break without an LLM in the
 * loop. GET /v1/analyze with no tool lists what is available.
 */
export async function handleAnalyzeRequest(request: Request, origin: string, env: ProviderEnv, self?: string): Promise<{ status: number; body: unknown }> {
  const tools = analysisTools(origin, env, self);
  const url = new URL(request.url);
  let tool = url.searchParams.get("tool") ?? "";
  let args: unknown = {};

  if (request.method === "POST") {
    let raw: unknown;
    try { raw = await request.json(); } catch (e) { return { status: 400, body: { error: `Body is not valid JSON: ${e instanceof Error ? e.message : String(e)}` } }; }
    if (!raw || typeof raw !== "object") return { status: 400, body: { error: 'Send {"tool": "forecast", "args": {...}}.' } };
    const o = raw as { tool?: unknown; args?: unknown };
    if (typeof o.tool === "string") tool = o.tool;
    if (o.args && typeof o.args === "object") args = o.args;
  } else {
    const a = url.searchParams.get("args");
    if (a) {
      try { args = JSON.parse(a); } catch (e) { return { status: 400, body: { error: `args is not valid JSON: ${e instanceof Error ? e.message : String(e)}` } }; }
    }
  }

  if (!tool) {
    return { status: 200, body: {
      how: 'POST {"tool":"<name>","args":{...}} or GET ?tool=<name>&args=<json>. Series references are the same as everywhere: {"dataset","series"} or {"provider","id"} or {"points"}.',
      example: { tool: "forecast", args: { series: { dataset: "us-prices", series: "cpi", start: "2015-01" }, horizon: 12 } },
      tools: [...tools.values()].map((t) => ({ name: t.name, title: t.title, description: t.description })),
    } };
  }

  const entry = tools.get(tool);
  if (!entry) return { status: 404, body: { error: `No analysis tool called '${tool}'.`, tools: [...tools.keys()] } };

  const parsed = z.object(entry.shape).safeParse(args);
  if (!parsed.success) {
    return { status: 400, body: { error: `Bad arguments for ${tool}`, issues: parsed.error.issues.slice(0, 10).map((i) => ({ path: i.path.join("."), message: i.message })) } };
  }
  try {
    const res = await entry.run(parsed.data as Record<string, unknown>);
    const text = res.content?.[0]?.text ?? "";
    if (res.isError) return { status: 400, body: { error: text, tool } };
    try { return { status: 200, body: { tool, result: JSON.parse(text) } }; }
    catch { return { status: 200, body: { tool, result: text } }; }
  } catch (e) {
    if (e instanceof DataError) return { status: 400, body: { error: e.message, tool } };
    return { status: 500, body: { error: e instanceof Error ? e.message : String(e), tool } };
  }
}
