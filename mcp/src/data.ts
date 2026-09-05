/**
 * Data access for the MCP server.
 *
 * The Worker owns no data. Every dataset is a JSON file published by the
 * GitHub Pages site (DATA_ORIGIN/data/<name>.json), refreshed by the repo's
 * own GitHub Actions. This module fetches those files, caches them for the
 * lifetime of the isolate, and turns the handful of layouts found in data/
 * into one uniform view: a set of named series, each a map of date -> value.
 */

export type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
export type Series = Record<string, number>;

export interface SeriesInfo {
  id: string;
  n: number;
  first: string;
  last: string;
}

export interface CatalogEntry {
  file: string;
  bytes: number;
  shape: string;
  series: number | null;
  observations: number | null;
  coverage: { first: string; last: string } | null;
  last_commit: string | null;
  provenance: string;
  producer: string | null;
  provider?: string;
  auto_refresh: boolean;
  source: string | Record<string, unknown> | null;
  note: string | null;
  as_of?: string;
  refresh?: string;
  series_keys?: string[];
  error?: string;
}

export interface Catalog {
  generated_by: string;
  totals: { datasets: number; observations: number; by_provenance: Record<string, number> };
  datasets: CatalogEntry[];
}

// YYYY, YYYY-MM, YYYY-MM-DD, and Eurostat's YYYY-Qn / YYYY-Sn. All sort lexically.
const DATE = /^\d{4}(-(\d{2}|Q\d|S\d))?(-\d{2})?$/;
const TTL_MS = 10 * 60 * 1000;

// Keys that describe a dataset rather than contain one.
const META_KEYS = new Set([
  "source", "source_url", "source_file", "fetched_by", "fetched_at", "config", "note",
  "generated_by", "base", "meta", "unit", "hicp_source", "cpi_source", "_readme",
  "as_of", "question", "definition", "scope_note", "encoding", "excludes", "basis",
  "dimension_order", "window", "log", "runs", "errors", "updated", "asof",
]);
// Container keys that hold the body of the dataset. They are dropped from series ids
// so that us-prices.json exposes "cattle_ppi", not "series.cattle_ppi".
const CONTAINER_KEYS = new Set(["series", "shares", "regions", "countries", "groups"]);

interface CacheEntry { at: number; body: Json }
const cache = new Map<string, CacheEntry>();

export class DataError extends Error {}

export function datasetName(fileOrName: string): string {
  return fileOrName.replace(/^data\//, "").replace(/\.json$/, "");
}

export async function fetchJson(origin: string, path: string): Promise<Json> {
  const url = `${origin.replace(/\/$/, "")}/${path}`;
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.body;
  const res = await fetch(url, { headers: { accept: "application/json" } });
  if (res.status === 404) throw new DataError(`No such dataset: ${path}`);
  if (!res.ok) throw new DataError(`Upstream ${res.status} for ${path}`);
  const body = (await res.json()) as Json;
  cache.set(url, { at: Date.now(), body });
  return body;
}

export async function loadCatalog(origin: string): Promise<Catalog> {
  return (await fetchJson(origin, "data/_catalog.json")) as unknown as Catalog;
}

export async function loadDataset(origin: string, name: string): Promise<Json> {
  const clean = datasetName(name);
  if (!/^[a-z0-9][a-z0-9-]*$/i.test(clean)) throw new DataError(`Bad dataset name: ${name}`);
  return fetchJson(origin, `data/${clean}.json`);
}

// ---------------------------------------------------------------------------
// Series extraction

function isObj(v: Json): v is { [k: string]: Json } {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function numeric(v: Json): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** A dict whose keys are dates and whose values are numbers (nulls tolerated). */
function isSeriesDict(v: Json): boolean {
  if (!isObj(v)) return false;
  const keys = Object.keys(v);
  if (keys.length < 1) return false;
  let dated = 0;
  for (const k of keys) if (DATE.test(k)) dated++;
  if (dated < keys.length * 0.8) return false;
  return keys.some((k) => numeric(v[k]) || v[k] === null);
}

/** A dict of date -> {field: number}, e.g. pharma-share.json country blocks. */
function isDatedRecordDict(v: Json): boolean {
  if (!isObj(v)) return false;
  const keys = Object.keys(v);
  if (keys.length < 2) return false;
  return keys.every((k) => DATE.test(k) && isObj(v[k]));
}

function cleanSeries(v: { [k: string]: Json }): Series {
  const out: Series = {};
  for (const k of Object.keys(v).sort()) {
    const x = v[k];
    if (DATE.test(k) && numeric(x)) out[k] = x;
  }
  return out;
}

function tableSeries(columns: Json[], rows: Json[], prefix: string, out: Map<string, Series>) {
  columns.forEach((col, i) => {
    if (i === 0 || typeof col !== "string") return;
    const s: Series = {};
    for (const r of rows) {
      if (!Array.isArray(r) || r.length <= i) continue;
      const d = String(r[0]);
      const x = r[i];
      if (DATE.test(d) && numeric(x)) s[d] = x;
    }
    if (Object.keys(s).length) out.set(prefix ? `${prefix}.${col}` : col, s);
  });
}

function walk(node: Json, path: string, depth: number, out: Map<string, Series>) {
  if (depth > 5 || !isObj(node)) return;

  if (Array.isArray(node.columns) && Array.isArray(node.rows)) {
    tableSeries(node.columns, node.rows, path, out);
    return;
  }
  if (isSeriesDict(node)) {
    const s = cleanSeries(node);
    if (Object.keys(s).length) out.set(path, s);
    return;
  }
  if (isDatedRecordDict(node)) {
    const fields = new Set<string>();
    const recs: Record<string, { [k: string]: Json }> = {};
    for (const d of Object.keys(node)) {
      const r = node[d];
      if (isObj(r)) { recs[d] = r; for (const f of Object.keys(r)) fields.add(f); }
    }
    for (const f of fields) {
      const s: Series = {};
      for (const d of Object.keys(recs).sort()) {
        const x = recs[d][f];
        if (numeric(x)) s[d] = x;
      }
      if (Object.keys(s).length) out.set(path ? `${path}.${f}` : f, s);
    }
    return;
  }
  for (const [k, v] of Object.entries(node)) {
    if (depth === 0 && META_KEYS.has(k)) continue;
    if (typeof v !== "object" || v === null) continue;
    const next = depth === 0 && CONTAINER_KEYS.has(k) ? path : path ? `${path}.${k}` : k;
    if (Array.isArray(v)) {
      // A list of rows with column names kept in meta (broiler-parity-pl.json).
      const meta = isObj(node.meta) ? node.meta : null;
      if (meta && Array.isArray(meta.columns)) tableSeries(meta.columns, v, next, out);
      continue;
    }
    walk(v, next, depth + 1, out);
  }
}

export function extractSeries(dataset: Json): Map<string, Series> {
  const out = new Map<string, Series>();
  walk(dataset, "", 0, out);
  return out;
}

export function describeSeries(all: Map<string, Series>): SeriesInfo[] {
  const infos: SeriesInfo[] = [];
  for (const [id, s] of all) {
    const keys = Object.keys(s);
    infos.push({ id, n: keys.length, first: keys[0], last: keys[keys.length - 1] });
  }
  return infos;
}

/** Caveats travel with the data: from the catalog, from the file itself, from provenance. */
export function caveatsFor(entry: CatalogEntry | undefined, dataset: Json): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const add = (s: unknown) => {
    if (typeof s === "string" && s.trim() && !seen.has(s)) { seen.add(s); out.push(s); }
  };
  if (entry) {
    add(entry.note);
    if (entry.provenance === "manual") add(`Pulled by hand, as of ${entry.as_of ?? "unknown"}. ${entry.refresh ?? ""}`.trim());
    if (entry.provenance === "unattributed") add("No script produces this file. Provenance unknown. Verify before use.");
    if (!entry.auto_refresh && entry.provenance !== "manual") add("Not on the refresh schedule. Check last_commit before treating it as current.");
  }
  if (isObj(dataset)) {
    add(dataset.note);
    add(dataset.scope_note);
    if (isObj(dataset.config)) add(dataset.config.note);
    if (isObj(dataset.meta)) { add(dataset.meta.note); add(dataset.meta.construction); }
  }
  return out;
}

/** A source may be a string or, in a few generated files, a small object of sources. */
export function asText(v: unknown, max = 400): string | null {
  if (typeof v === "string") return v;
  if (v && typeof v === "object") return JSON.stringify(v).slice(0, max);
  return null;
}

export function sourceFor(entry: CatalogEntry | undefined, dataset: Json): string | null {
  const fromEntry = asText(entry?.source);
  if (fromEntry) return fromEntry;
  if (isObj(dataset)) {
    const own = asText(dataset.source);
    if (own) return own;
    if (isObj(dataset.meta) && typeof dataset.meta.construction === "string") return dataset.meta.construction;
  }
  return null;
}

/** Follow a dot path into a JSON value: "regions.US.rows". */
export function dig(node: Json, path: string): Json {
  let cur: Json = node;
  for (const part of path.split(".").filter(Boolean)) {
    if (Array.isArray(cur) && /^\d+$/.test(part)) cur = cur[Number(part)] ?? null;
    else if (isObj(cur) && part in cur) cur = cur[part];
    else throw new DataError(`Path not found: ${path} (stopped at "${part}")`);
  }
  return cur;
}
