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
import { round, toPoints } from "./transform.js";

export const PlotSpecSchema = z.object({
  series: z.array(SeriesRefSchema).min(1).max(8),
  title: z.string().max(200).optional(),
  scale: z.enum(["linear", "log"]).optional(),
  right: z.array(z.number().int().min(0).max(7)).optional(),
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
