/**
 * One way to name a series wherever it lives, so every analysis tool takes
 * the same input:
 *   { dataset, series }                     a local dataset from data/
 *   { provider, id, series?, params? }      a live provider (fred, eurostat, ...)
 *   { points: [[date, value], ...] }        the user's own numbers
 * plus the same window and transform options as get_series.
 */
import { z } from "zod";
import { DataError, type Series, caveatsFor, extractSeries, loadCatalog, loadDataset, datasetName, sourceFor } from "./data.js";
import { PROVIDERS, type ProviderEnv } from "./providers.js";
import { apply, clip, resample, type Frequency, type Transform } from "./transform.js";

export const SeriesRefSchema = z.object({
  dataset: z.string().optional().describe("Local dataset name, e.g. 'us-prices'"),
  series: z.string().optional().describe("Series id within the dataset or provider result; required for local datasets, optional when a provider returns one series"),
  provider: z.enum(["fred", "eurostat", "worldbank", "ecb", "oecd", "owid", "evds"]).optional(),
  id: z.string().optional().describe("Provider series or dataset id"),
  params: z.record(z.string(), z.string()).optional().describe("Provider filters, e.g. {geo:'TR'} for Eurostat, {country:'TUR'} for World Bank"),
  points: z.array(z.tuple([z.string(), z.number()])).optional().describe("Inline data as [date, value] pairs"),
  label: z.string().optional().describe("Name to use in the output"),
  start: z.string().optional(),
  end: z.string().optional(),
  frequency: z.enum(["native", "annual_mean", "annual_last"]).optional(),
  transform: z.enum(["none", "pct_change", "yoy", "diff", "rebase", "log"]).optional(),
  base: z.string().optional(),
});
export type SeriesRef = z.infer<typeof SeriesRefSchema>;

export interface Resolved {
  label: string;
  series: Series;
  source: string | null;
  caveats: string[];
  transform: string;
}

export function labelOf(ref: SeriesRef): string {
  if (ref.label) return ref.label;
  if (ref.dataset) return `${datasetName(ref.dataset)}:${ref.series ?? ""}`;
  if (ref.provider) return `${ref.provider}:${ref.id}${ref.series ? ":" + ref.series : ""}`;
  return "inline";
}

export async function resolve(ref: SeriesRef, origin: string, env: ProviderEnv): Promise<Resolved> {
  let raw: Series | undefined;
  let source: string | null = null;
  let caveats: string[] = [];
  const label = labelOf(ref);

  if (ref.points) {
    raw = {};
    for (const [d, v] of ref.points) if (Number.isFinite(v)) raw[d] = v;
    source = "user-supplied";
  } else if (ref.dataset) {
    if (!ref.series) throw new DataError(`Series id is required for local dataset ${ref.dataset}. Use describe_dataset to list them.`);
    const [cat, body] = await Promise.all([loadCatalog(origin), loadDataset(origin, ref.dataset)]);
    const all = extractSeries(body);
    raw = all.get(ref.series);
    if (!raw) throw new DataError(`No series '${ref.series}' in ${ref.dataset}. Available: ${[...all.keys()].slice(0, 30).join(", ")}`);
    const entry = cat.datasets.find((d) => d.file === `data/${datasetName(ref.dataset!)}.json`);
    source = sourceFor(entry, body);
    caveats = caveatsFor(entry, body);
  } else if (ref.provider) {
    if (!ref.id) throw new DataError(`Provider ${ref.provider} needs an id`);
    const p = PROVIDERS[ref.provider];
    const res = await p.fetch(ref.id, ref.params ?? {}, env);
    const keys = Object.keys(res.series);
    const pick = ref.series ?? (keys.length === 1 ? keys[0] : undefined);
    if (!pick) throw new DataError(`${ref.provider}:${ref.id} returned ${keys.length} series. Choose one with 'series': ${keys.slice(0, 30).join(", ")}`);
    raw = res.series[pick];
    if (!raw) throw new DataError(`No series '${pick}' in ${ref.provider}:${ref.id}. Available: ${keys.slice(0, 30).join(", ")}`);
    source = res.source;
    caveats = res.notes;
  } else {
    throw new DataError("A series reference needs dataset+series, provider+id, or points");
  }

  const transform = (ref.transform ?? "none") as Transform;
  let s = clip(raw, ref.start ? yearEarlier(ref.start, transform) : undefined, ref.end);
  s = resample(s, (ref.frequency ?? "native") as Frequency);
  s = apply(s, transform, ref.base);
  s = clip(s, ref.start, ref.end);
  if (!Object.keys(s).length) throw new DataError(`${label}: no observations after windowing ${ref.start ?? ""}..${ref.end ?? ""}`);
  return { label, series: s, source, caveats, transform };
}

function yearEarlier(start: string, transform: string): string {
  if (transform !== "yoy") return start;
  return String(Number(start.slice(0, 4)) - 1).padStart(4, "0") + start.slice(4);
}

/** Inner join on dates. Returns aligned arrays in date order. */
export function align(list: Series[]): { dates: string[]; columns: number[][] } {
  if (!list.length) return { dates: [], columns: [] };
  const dates = Object.keys(list[0]).filter((d) => list.every((s) => d in s)).sort();
  return { dates, columns: list.map((s) => dates.map((d) => s[d])) };
}

export type Freq = "daily" | "weekly" | "monthly" | "quarterly" | "semiannual" | "annual" | "unknown";

export function detectFrequency(dates: string[]): { frequency: Freq; period: number } {
  const k = dates[0] ?? "";
  if (/^\d{4}$/.test(k)) return { frequency: "annual", period: 1 };
  if (/^\d{4}-Q\d$/.test(k)) return { frequency: "quarterly", period: 4 };
  if (/^\d{4}-S\d$/.test(k)) return { frequency: "semiannual", period: 2 };
  if (/^\d{4}-\d{2}$/.test(k)) return { frequency: "monthly", period: 12 };
  if (/^\d{4}-\d{2}-\d{2}$/.test(k)) {
    if (dates.length > 2) {
      const days = dates.slice(0, 40).map((d) => Date.parse(d) / 86400000);
      const steps = days.slice(1).map((d, i) => d - days[i]).sort((a, b) => a - b);
      const step = steps[Math.floor(steps.length / 2)];
      if (step > 5 && step < 9) return { frequency: "weekly", period: 52 };
      if (step >= 28 && step <= 31) return { frequency: "monthly", period: 12 };
      if (step >= 89 && step <= 92) return { frequency: "quarterly", period: 4 };
      if (step >= 365) return { frequency: "annual", period: 1 };
    }
    return { frequency: "daily", period: 1 };
  }
  return { frequency: "unknown", period: 1 };
}

/** Dates following `last`, in the same format, h steps ahead. */
export function futureDates(last: string, h: number, freq: Freq): string[] {
  const out: string[] = [];
  if (freq === "annual") { const y = Number(last); for (let i = 1; i <= h; i++) out.push(String(y + i)); }
  else if (freq === "monthly") {
    let y = Number(last.slice(0, 4)), m = Number(last.slice(5, 7));
    for (let i = 0; i < h; i++) { m++; if (m > 12) { m = 1; y++; } out.push(`${y}-${String(m).padStart(2, "0")}`); }
  } else if (freq === "quarterly") {
    let y = Number(last.slice(0, 4)), q = Number(last.slice(6, 7));
    for (let i = 0; i < h; i++) { q++; if (q > 4) { q = 1; y++; } out.push(`${y}-Q${q}`); }
  } else if (freq === "semiannual") {
    let y = Number(last.slice(0, 4)), s = Number(last.slice(6, 7));
    for (let i = 0; i < h; i++) { s++; if (s > 2) { s = 1; y++; } out.push(`${y}-S${s}`); }
  } else {
    const step = freq === "weekly" ? 7 : 1;
    const t = Date.parse(last);
    if (!Number.isFinite(t)) throw new DataError(`Cannot extend dates from '${last}'`);
    for (let i = 1; i <= h; i++) out.push(new Date(t + i * step * 86400000).toISOString().slice(0, 10));
  }
  return out;
}
