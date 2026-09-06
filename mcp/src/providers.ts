/**
 * Live data providers. Each one turns a public statistical API into the same
 * shape the local datasets use: a map of series id -> {date: value}.
 *
 * Nothing is stored. Responses are cached in the isolate for a few minutes.
 * Keys: FRED fetch is keyless (the CSV endpoint); FRED search needs
 * FRED_API_KEY. TCMB EVDS needs EVDS_API_KEY. Everything else is open.
 */
import { DataError, type Series } from "./data.js";

export interface ProviderEnv {
  FRED_API_KEY?: string;
  EVDS_API_KEY?: string;
}

export interface FetchResult {
  provider: string;
  id: string;
  source: string;
  url: string;
  series: Record<string, Series>;
  notes: string[];
}

export interface CuratedEntry { id: string; title: string; hint?: string }

export interface Provider {
  name: string;
  title: string;
  coverage: string;
  id_format: string;
  needs_key: string | null;
  curated: CuratedEntry[];
  fetch(id: string, params: Record<string, string>, env: ProviderEnv): Promise<FetchResult>;
  search?(query: string, env: ProviderEnv): Promise<CuratedEntry[]>;
}

const TTL_MS = 10 * 60 * 1000;
const textCache = new Map<string, { at: number; body: string }>();

async function getText(url: string, headers: Record<string, string> = {}): Promise<string> {
  const hit = textCache.get(url);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.body;
  const res = await fetch(url, { headers: { "user-agent": "econ-mcp/0.2 (+https://namikakmandev.github.io)", ...headers } });
  if (!res.ok) throw new DataError(`Upstream ${res.status} from ${new URL(url).host}: ${(await res.text()).slice(0, 200)}`);
  const body = await res.text();
  const head = body.trimStart().slice(0, 15).toLowerCase();
  if (head.startsWith("<!doctype") || head.startsWith("<html")) {
    throw new DataError(`${new URL(url).host} answered with a web page instead of data. For EVDS this usually means the key was rejected; check it at evds2.tcmb.gov.tr.`);
  }
  textCache.set(url, { at: Date.now(), body });
  return body;
}

async function getJson(url: string, headers: Record<string, string> = {}): Promise<unknown> {
  const t = await getText(url, headers);
  try { return JSON.parse(t); } catch { throw new DataError(`Non-JSON reply from ${new URL(url).host}: ${t.slice(0, 200)}`); }
}

/** Minimal CSV reader: handles quoted fields and CRLF. Returns rows of strings. */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], field = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; }
      else field += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.length > 1 || (r.length === 1 && r[0] !== ""));
}

function num(s: string | undefined | null): number | null {
  if (s === undefined || s === null) return null;
  const t = String(s).trim();
  if (t === "" || t === "." || t === "NaN" || t === ":" || t === "n/a") return null;
  const x = Number(t.replace(/,/g, "."));
  return Number.isFinite(x) ? x : null;
}

/** Normalise the date formats these APIs use to YYYY, YYYY-MM, YYYY-MM-DD, YYYY-Qn, YYYY-Sn. */
export function normDate(raw: string): string | null {
  const s = raw.trim();
  let m: RegExpMatchArray | null;
  if ((m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s))) return `${m[1]}-${m[2]}-${m[3]}`;
  if ((m = /^(\d{4})-(\d{2})$/.exec(s))) return `${m[1]}-${m[2]}`;
  if ((m = /^(\d{4})M(\d{2})$/.exec(s))) return `${m[1]}-${m[2]}`;
  if ((m = /^(\d{4})-?Q([1-4])$/i.exec(s))) return `${m[1]}-Q${m[2]}`;
  if ((m = /^(\d{4})-?S([12])$/i.exec(s))) return `${m[1]}-S${m[2]}`;
  if ((m = /^(\d{4})$/.exec(s))) return m[1];
  if ((m = /^(\d{4})-(\d{1,2})$/.exec(s))) return `${m[1]}-${m[2].padStart(2, "0")}`;           // EVDS monthly "2020-1"
  if ((m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(s))) return `${m[3]}-${m[2]}-${m[1]}`;               // EVDS daily dd-mm-yyyy
  if ((m = /^(\d{4})-(\d{2})-(\d{2})T/.exec(s))) return `${m[1]}-${m[2]}-${m[3]}`;
  return null;
}

/**
 * FRED and the World Bank date monthly, quarterly and annual observations as full
 * days (2020-01-01). Collapse those to YYYY-MM, YYYY-Qn or YYYY so they align with
 * Eurostat and the curated files, and so frequency detection sees the real cadence.
 */
export function collapseDates(s: Series): Series {
  const keys = Object.keys(s).sort();
  if (keys.length < 2 || !keys.every((k) => /^\d{4}-\d{2}-\d{2}$/.test(k))) return s;
  const days = keys.map((k) => Date.parse(k) / 86400000);
  const steps = days.slice(1).map((d, i) => d - days[i]);
  const median = [...steps].sort((a, b) => a - b)[Math.floor(steps.length / 2)];
  const firstOfMonth = keys.every((k) => k.endsWith("-01"));
  let fmt: ((k: string) => string) | null = null;
  if (firstOfMonth && median >= 28 && median <= 31) fmt = (k) => k.slice(0, 7);
  else if (firstOfMonth && median >= 89 && median <= 92 && keys.every((k) => ["01", "04", "07", "10"].includes(k.slice(5, 7)))) fmt = (k) => `${k.slice(0, 4)}-Q${Math.floor(Number(k.slice(5, 7)) / 3) + 1}`;
  else if (median >= 365 && median <= 366 && keys.every((k) => k.slice(5) === keys[0].slice(5))) fmt = (k) => k.slice(0, 4);
  if (!fmt) return s;
  const out: Series = {};
  for (const k of keys) out[fmt(k)] = s[k];
  return Object.keys(out).length === keys.length ? out : s;
}

function qs(params: Record<string, string>): string {
  return Object.entries(params).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
}

// ---------------------------------------------------------------------------
// FRED

const fred: Provider = {
  name: "fred",
  title: "FRED (Federal Reserve Bank of St. Louis)",
  coverage: "US and international macro: prices, rates, output, labour, money. 800k+ series.",
  id_format: "FRED series id, e.g. CPIAUCSL, GDPC1, UNRATE, DEXUSEU, WPU0131",
  needs_key: "search only: FRED_API_KEY (free at fred.stlouisfed.org)",
  curated: [
    { id: "CPIAUCSL", title: "US CPI, all items, SA, 1982-84=100, monthly" },
    { id: "CPILFESL", title: "US core CPI (ex food and energy), monthly" },
    { id: "PCEPI", title: "US PCE price index, monthly" },
    { id: "GDPC1", title: "US real GDP, chained 2017 dollars, quarterly SAAR" },
    { id: "GDP", title: "US nominal GDP, quarterly SAAR" },
    { id: "UNRATE", title: "US unemployment rate, monthly" },
    { id: "PAYEMS", title: "US nonfarm payrolls, thousands, monthly" },
    { id: "FEDFUNDS", title: "Effective federal funds rate, monthly" },
    { id: "DGS10", title: "10-year Treasury yield, daily" },
    { id: "DGS2", title: "2-year Treasury yield, daily" },
    { id: "T10Y2Y", title: "10y minus 2y Treasury spread, daily" },
    { id: "M2SL", title: "US M2 money stock, monthly" },
    { id: "INDPRO", title: "US industrial production index, monthly" },
    { id: "PPIACO", title: "US PPI all commodities, monthly" },
    { id: "DEXUSEU", title: "USD per EUR, daily" },
    { id: "DEXTUUS", title: "TRY per USD, daily" },
    { id: "DCOILBRENTEU", title: "Brent crude, USD/bbl, daily" },
    { id: "DCOILWTICO", title: "WTI crude, USD/bbl, daily" },
    { id: "HOUST", title: "US housing starts, thousands, monthly" },
    { id: "UMCSENT", title: "University of Michigan consumer sentiment, monthly" },
    { id: "CP0000EZ19M086NEST", title: "Euro area HICP, all items, monthly" },
    { id: "LRHUTTTTEZM156S", title: "Euro area unemployment rate, monthly" },
    { id: "IRSTCB01TRM156N", title: "Turkey central bank policy rate, monthly" },
    { id: "TURCPIALLMINMEI", title: "Turkey CPI, all items, monthly" },
    { id: "WPU0131", title: "US PPI slaughter cattle, monthly" },
    { id: "WPU012202", title: "US PPI corn, monthly" },
  ],
  async fetch(id, params) {
    const url = `https://fred.stlouisfed.org/graph/fredgraph.csv?id=${encodeURIComponent(id)}`;
    const rows = parseCsv(await getText(url));
    if (!rows.length || rows[0].length < 2) throw new DataError(`FRED returned nothing for ${id}. Check the id at fred.stlouisfed.org.`);
    const header = rows[0];
    const s: Series = {};
    for (const r of rows.slice(1)) {
      const d = normDate(r[0]);
      const v = num(r[1]);
      if (d && v !== null) s[d] = v;
    }
    const notes = ["Units and seasonal adjustment are as published by FRED; check the series page for the exact definition.",
      "Monthly, quarterly and annual series are keyed YYYY-MM, YYYY-Qn and YYYY so they align with other sources; daily series keep full dates."];
    return { provider: "fred", id, source: `FRED series ${header[1] ?? id}`, url, series: { [id]: collapseDates(s) }, notes: params.note ? [...notes, params.note] : notes };
  },
  async search(query, env) {
    if (!env.FRED_API_KEY) return curatedSearch(fred.curated, query);
    const url = `https://api.stlouisfed.org/fred/series/search?${qs({ search_text: query, api_key: env.FRED_API_KEY, file_type: "json", limit: "25", order_by: "popularity", sort_order: "desc" })}`;
    const j = (await getJson(url)) as { seriess?: Array<{ id: string; title: string; frequency_short?: string; units_short?: string; seasonal_adjustment_short?: string; observation_start?: string; observation_end?: string }> };
    return (j.seriess ?? []).map((x) => ({
      id: x.id,
      title: x.title,
      hint: [x.frequency_short, x.units_short, x.seasonal_adjustment_short, `${x.observation_start}..${x.observation_end}`].filter(Boolean).join(", "),
    }));
  },
};

// ---------------------------------------------------------------------------
// Eurostat (JSON-stat 2.0)

interface JsonStat {
  id: string[];
  size: number[];
  dimension: Record<string, { category: { index: Record<string, number> | string[]; label?: Record<string, string> } }>;
  value: Record<string, number | null> | Array<number | null>;
  label?: string;
}

/** JSON-stat 2.0 -> rows of (dimension codes, value). Ported from scripts/fetch.py. */
export function jsonStatRows(j: JsonStat): Array<{ key: Record<string, string>; value: number }> {
  const codes = j.id.map((d) => {
    const idx = j.dimension[d].category.index;
    if (Array.isArray(idx)) return idx;
    const inv: string[] = [];
    for (const [code, pos] of Object.entries(idx)) inv[pos] = code;
    return inv;
  });
  const strides = new Array<number>(j.size.length).fill(1);
  for (let i = j.size.length - 2; i >= 0; i--) strides[i] = strides[i + 1] * j.size[i + 1];
  const out: Array<{ key: Record<string, string>; value: number }> = [];
  const entries: Array<[number, number | null]> = Array.isArray(j.value)
    ? j.value.map((v, i) => [i, v] as [number, number | null])
    : Object.entries(j.value).map(([p, v]) => [Number(p), v] as [number, number | null]);
  for (const [p, v] of entries) {
    if (v === null || v === undefined || !Number.isFinite(v)) continue;
    const key: Record<string, string> = {};
    j.id.forEach((d, i) => { key[d] = codes[i][Math.floor(p / strides[i]) % j.size[i]]; });
    out.push({ key, value: v });
  }
  return out;
}

const eurostat: Provider = {
  name: "eurostat",
  title: "Eurostat",
  coverage: "EU and candidate countries (Turkey included in many tables): national accounts, prices, labour, agriculture, energy, trade.",
  id_format: "Dataset code plus dimension filters as params, e.g. id=prc_hicp_midx params={geo:'TR', coicop:'CP00', unit:'I15'}. Unfiltered dimensions are returned as separate series keyed 'dim1|dim2'.",
  needs_key: null,
  curated: [
    { id: "prc_hicp_midx", title: "HICP monthly index", hint: "params: geo, coicop (CP00 = all items), unit (I15)" },
    { id: "prc_hicp_manr", title: "HICP annual rate of change, monthly", hint: "params: geo, coicop" },
    { id: "nama_10_gdp", title: "GDP and main aggregates, annual", hint: "params: geo, na_item (B1GQ = GDP), unit (CP_MEUR)" },
    { id: "namq_10_gdp", title: "GDP quarterly", hint: "params: geo, na_item, unit, s_adj (SCA)" },
    { id: "une_rt_m", title: "Unemployment rate, monthly", hint: "params: geo, age (TOTAL), sex (T), unit (PC_ACT), s_adj (SA)" },
    { id: "sts_inppd_m", title: "Producer prices in industry, domestic market, monthly", hint: "params: geo, nace_r2, unit (I21), s_adj (NSA)" },
    { id: "sts_inpr_m", title: "Industrial production index, monthly", hint: "params: geo, nace_r2 (B-D), unit (I21), s_adj (SCA)" },
    { id: "ert_bil_eur_m", title: "Exchange rates vs euro, monthly", hint: "params: currency (USD, TRY), statinfo (AVG), unit (NAC)" },
    { id: "apri_ap_ina", title: "Agricultural prices, absolute, annual", hint: "params: geo, prod_veg or prod_ani, unit" },
    { id: "nrg_pc_204", title: "Electricity prices for households, semi-annual", hint: "params: geo, consom, unit, tax, currency" },
    { id: "lc_lci_r2_q", title: "Labour cost index, quarterly", hint: "params: geo, nace_r2, unit, s_adj" },
    { id: "ext_lt_intratrd", title: "Intra and extra EU trade, annual", hint: "params: geo, partner, indic_et" },
    { id: "demo_pjan", title: "Population on 1 January, annual", hint: "params: geo, age (TOTAL), sex (T)" },
    { id: "gov_10dd_edpt1", title: "Government deficit and debt, annual", hint: "params: geo, na_item, sector (S13), unit" },
  ],
  async fetch(id, params) {
    const base = params.api === "comext"
      ? "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/"
      : "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/";
    const filters = Object.entries(params).filter(([k]) => k !== "api" && k !== "group_dims");
    const url = `${base}${encodeURIComponent(id)}?format=JSON&lang=EN` + filters.map(([k, v]) => v.split(",").map((vi) => `&${encodeURIComponent(k)}=${encodeURIComponent(vi.trim())}`).join("")).join("");
    const j = (await getJson(url)) as JsonStat & { error?: unknown };
    if (!j.id || !j.dimension) throw new DataError(`Eurostat returned no data for ${id} with ${JSON.stringify(params)}. ${JSON.stringify(j).slice(0, 300)}`);
    const rows = jsonStatRows(j);
    const free = j.id.filter((d) => d !== "time" && j.size[j.id.indexOf(d)] > 1);
    const groupDims = params.group_dims ? params.group_dims.split(",").map((s) => s.trim()) : free;
    const series: Record<string, Series> = {};
    for (const { key, value } of rows) {
      const t = normDate(key.time ?? "");
      if (!t) continue;
      const g = groupDims.length ? groupDims.map((d) => key[d]).join("|") : "ALL";
      (series[g] ??= {})[t] = value;
    }
    const labels: string[] = [];
    for (const d of free) {
      const lab = j.dimension[d].category.label ?? {};
      labels.push(`${d}: ${Object.entries(lab).slice(0, 12).map(([c, l]) => `${c}=${l}`).join(", ")}${Object.keys(lab).length > 12 ? ", ..." : ""}`);
    }
    const notes = [
      "Series keys are the codes of the dimensions you did not filter, joined with '|'. Add params to narrow.",
      ...labels,
      "Eurostat flags (provisional, break in series) are dropped in this view. Check the dataset's metadata page for breaks.",
    ];
    return { provider: "eurostat", id, source: `Eurostat ${id}: ${j.label ?? ""}`.trim(), url, series, notes };
  },
  async search(query) { return curatedSearch(eurostat.curated, query); },
};

// ---------------------------------------------------------------------------
// World Bank

const worldbank: Provider = {
  name: "worldbank",
  title: "World Bank (World Development Indicators and more)",
  coverage: "Every country, annual: GDP, growth, inflation, population, trade, investment, poverty, energy.",
  id_format: "Indicator code, e.g. NY.GDP.MKTP.CD; params.country = ISO2/ISO3 codes separated by ';' (default TR;US;DEU), 'all' for every country.",
  needs_key: null,
  curated: [
    { id: "NY.GDP.MKTP.CD", title: "GDP, current US$" },
    { id: "NY.GDP.MKTP.KD.ZG", title: "GDP growth, annual %" },
    { id: "NY.GDP.PCAP.PP.KD", title: "GDP per capita, PPP, constant 2021 intl $" },
    { id: "FP.CPI.TOTL.ZG", title: "Inflation, consumer prices, annual %" },
    { id: "SL.UEM.TOTL.ZS", title: "Unemployment, % of labour force (ILO)" },
    { id: "SP.POP.TOTL", title: "Population, total" },
    { id: "NE.EXP.GNFS.ZS", title: "Exports of goods and services, % of GDP" },
    { id: "NE.IMP.GNFS.ZS", title: "Imports of goods and services, % of GDP" },
    { id: "BX.KLT.DINV.WD.GD.ZS", title: "FDI net inflows, % of GDP" },
    { id: "GC.DOD.TOTL.GD.ZS", title: "Central government debt, % of GDP" },
    { id: "NE.GDI.TOTL.ZS", title: "Gross capital formation, % of GDP" },
    { id: "NV.AGR.TOTL.ZS", title: "Agriculture value added, % of GDP" },
    { id: "NV.IND.MANF.ZS", title: "Manufacturing value added, % of GDP" },
    { id: "PA.NUS.FCRF", title: "Official exchange rate, LCU per US$, period average" },
    { id: "FR.INR.LEND", title: "Lending interest rate, %" },
    { id: "EG.USE.PCAP.KG.OE", title: "Energy use, kg oil equivalent per capita" },
    { id: "SI.POV.GINI", title: "Gini index" },
    { id: "SH.XPD.CHEX.GD.ZS", title: "Current health expenditure, % of GDP" },
    { id: "AG.PRD.LVSK.XD", title: "Livestock production index" },
    { id: "AG.PRD.FOOD.XD", title: "Food production index" },
  ],
  async fetch(id, params) {
    const country = (params.country ?? "TR;US;DEU").trim();
    const url = `https://api.worldbank.org/v2/country/${encodeURIComponent(country)}/indicator/${encodeURIComponent(id)}?format=json&per_page=20000`;
    const j = (await getJson(url)) as unknown;
    if (!Array.isArray(j) || !Array.isArray(j[1])) {
      const msg = Array.isArray(j) && j[0] && typeof j[0] === "object" && "message" in (j[0] as object) ? JSON.stringify((j[0] as { message: unknown }).message) : JSON.stringify(j).slice(0, 200);
      throw new DataError(`World Bank returned no data for ${id} / ${country}: ${msg}`);
    }
    const series: Record<string, Series> = {};
    let name = id;
    for (const r of j[1] as Array<{ date: string; value: number | null; countryiso3code?: string; country?: { id: string; value: string }; indicator?: { value: string } }>) {
      if (r.value === null || r.value === undefined) continue;
      const d = normDate(r.date);
      if (!d) continue;
      const c = r.countryiso3code || r.country?.id || "?";
      (series[c] ??= {})[d] = r.value;
      if (r.indicator?.value) name = r.indicator.value;
    }
    return { provider: "worldbank", id, source: `World Bank ${id}: ${name}`, url, series,
      notes: ["Series keys are ISO3 country codes.", "Annual data. Values are as published; some indicators are revised for several years."] };
  },
  async search(query) {
    const url = `https://api.worldbank.org/v2/indicator?format=json&per_page=25000`;
    try {
      const j = (await getJson(url)) as unknown;
      if (Array.isArray(j) && Array.isArray(j[1])) {
        const all = (j[1] as Array<{ id: string; name: string; sourceNote?: string }>).map((x) => ({ id: x.id, title: x.name, hint: (x.sourceNote ?? "").slice(0, 120) }));
        const hits = curatedSearch(all, query);
        if (hits.length) return hits.slice(0, 25);
      }
    } catch { /* fall back to the curated list below */ }
    return curatedSearch(worldbank.curated, query);
  },
};

// ---------------------------------------------------------------------------
// ECB Data Portal (SDMX CSV)

function sdmxCsvSeries(csv: string, keyCols?: string[]): { series: Record<string, Series>; columns: string[] } {
  const rows = parseCsv(csv);
  if (rows.length < 2) return { series: {}, columns: rows[0] ?? [] };
  const header = rows[0];
  const ti = header.indexOf("TIME_PERIOD"), vi = header.indexOf("OBS_VALUE");
  if (ti < 0 || vi < 0) throw new DataError(`Unexpected SDMX CSV columns: ${header.slice(0, 12).join(", ")}`);
  const dimCols = keyCols ?? header.filter((h, i) => i !== ti && i !== vi && !/^(OBS_|TIME_|KEY$|FREQ$|DATAFLOW$|STRUCTURE|ACTION$|UNIT_MULT|DECIMALS|TITLE|COLLECTION|COMPILING|SOURCE_AGENCY|Observation|Time|Measure)/.test(h) && !h.toLowerCase().endsWith("_label") && !/[a-z]/.test(h));
  const idx = dimCols.map((c) => header.indexOf(c)).filter((i) => i >= 0);
  const series: Record<string, Series> = {};
  for (const r of rows.slice(1)) {
    const d = normDate(r[ti] ?? "");
    const v = num(r[vi]);
    if (!d || v === null) continue;
    const key = idx.length ? idx.map((i) => r[i]).filter((x) => x !== "").join(".") : "ALL";
    (series[key] ??= {})[d] = v;
  }
  // Collapse to one key if every dimension column is identical across rows.
  const keys = Object.keys(series);
  if (keys.length === 1) return { series: { [keys[0]]: series[keys[0]] }, columns: header };
  return { series, columns: header };
}

const ecb: Provider = {
  name: "ecb",
  title: "ECB Data Portal",
  coverage: "Euro area money, rates, exchange rates, balance of payments, bank lending, HICP. Daily to annual.",
  id_format: "'FLOW/KEY' as in the ECB portal URL, e.g. EXR/D.USD.EUR.SP00.A, FM/B.U2.EUR.4F.KR.MRR_FR.LEV, ICP/M.U2.N.000000.4.ANR. Wildcards allowed in the key.",
  needs_key: null,
  curated: [
    { id: "EXR/D.USD.EUR.SP00.A", title: "USD per EUR reference rate, daily" },
    { id: "EXR/M.TRY.EUR.SP00.A", title: "TRY per EUR, monthly average" },
    { id: "EXR/M.USD.EUR.SP00.A", title: "USD per EUR, monthly average" },
    { id: "FM/B.U2.EUR.4F.KR.MRR_FR.LEV", title: "ECB main refinancing rate, business daily" },
    { id: "FM/B.U2.EUR.4F.KR.DFR.LEV", title: "ECB deposit facility rate" },
    { id: "ICP/M.U2.N.000000.4.ANR", title: "Euro area HICP annual rate, monthly" },
    { id: "ICP/M.U2.N.000000.4.INX", title: "Euro area HICP index, monthly" },
    { id: "BSI/M.U2.N.A.M30.X.1.U2.2300.Z01.E", title: "Euro area M3, monthly" },
    { id: "MIR/M.U2.B.A2A.A.R.A.2240.EUR.N", title: "Bank lending rate to firms, new business, monthly" },
    { id: "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", title: "Euro area 10y AAA government bond yield, daily" },
    { id: "IRS/M.TR.L.L40.CI.0000.TRY.N.Z", title: "Turkey long-term interest rate, monthly" },
  ],
  async fetch(id, params) {
    const [flow, key] = id.includes("/") ? id.split("/", 2) : [id, ""];
    if (!key) throw new DataError("ECB ids look like FLOW/KEY, e.g. EXR/D.USD.EUR.SP00.A");
    const extra: Record<string, string> = { format: "csvdata" };
    if (params.start) extra.startPeriod = params.start;
    if (params.end) extra.endPeriod = params.end;
    const url = `https://data-api.ecb.europa.eu/service/data/${encodeURIComponent(flow)}/${key}?${qs(extra)}`;
    const { series } = sdmxCsvSeries(await getText(url, { accept: "text/csv" }), ["KEY"]);
    const keys = Object.keys(series);
    if (!keys.length) throw new DataError(`ECB returned no observations for ${id}`);
    return { provider: "ecb", id, source: `ECB Data Portal ${flow} ${key}`, url, series,
      notes: ["Series keys are the full SDMX keys. Rates are in percent per annum, exchange rates in units of currency per euro."] };
  },
  async search(query) { return curatedSearch(ecb.curated, query); },
};

// ---------------------------------------------------------------------------
// OECD (SDMX CSV)

const oecd: Provider = {
  name: "oecd",
  title: "OECD Data Explorer",
  coverage: "OECD and partner countries (Turkey is a member): leading indicators, prices, labour, productivity, agriculture, health.",
  id_format: "'AGENCY,DATAFLOW,VERSION/KEY' as shown under 'API' in data-explorer.oecd.org, e.g. OECD.SDD.STES,DSD_STES@DF_CLI,4.1/TUR.M.LI...AA...H. Leave dimensions blank for wildcards.",
  needs_key: null,
  curated: [
    { id: "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,1.1/Q..TUR+USA+DEU.S1..B1GQ......", title: "Quarterly GDP, main aggregates", hint: "filter further in the explorer, copy the key" },
    { id: "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/TUR+USA+DEU.M.N.CPI.PA._T.N.GY", title: "CPI, all items, % change y/y, monthly" },
    { id: "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,1.0/TUR+USA+DEU..._Z.Y._T.Y_GE15..M", title: "Unemployment rate, monthly" },
    { id: "OECD.SDD.STES,DSD_STES@DF_CLI,4.1/TUR+USA+DEU.M.LI...AA...H", title: "Composite leading indicator, monthly" },
  ],
  async fetch(id, params) {
    const [flow, key] = id.includes("/") ? [id.slice(0, id.indexOf("/")), id.slice(id.indexOf("/") + 1)] : [id, "all"];
    const extra: Record<string, string> = { format: "csvfilewithlabels", dimensionAtObservation: "AllDimensions" };
    if (params.start) extra.startPeriod = params.start;
    if (params.end) extra.endPeriod = params.end;
    const url = `https://sdmx.oecd.org/public/rest/data/${flow}/${key}?${qs(extra)}`;
    const csv = await getText(url, { accept: "text/csv" });
    const { series, columns } = sdmxCsvSeries(csv);
    if (!Object.keys(series).length) throw new DataError(`OECD returned no observations for ${id}. Columns: ${columns.slice(0, 10).join(", ")}`);
    return { provider: "oecd", id, source: `OECD ${flow} ${key}`, url, series,
      notes: ["Series keys join the coded dimension columns with '.'; labels are in the CSV but dropped here. Narrow the key in the OECD explorer for a single series."] };
  },
  async search(query) { return curatedSearch(oecd.curated, query); },
};

// ---------------------------------------------------------------------------
// Our World in Data

const owid: Provider = {
  name: "owid",
  title: "Our World in Data",
  coverage: "Long-run global series: energy, agriculture, health, population, CO2, livestock. Mostly annual.",
  id_format: "Grapher slug from the chart URL, e.g. cattle-livestock-count-heads; params.entities = names separated by ';' (default all).",
  needs_key: null,
  curated: [
    { id: "cattle-livestock-count-heads", title: "Cattle stocks, head (FAO)" },
    { id: "meat-production-tonnes", title: "Meat production, tonnes (FAO)" },
    { id: "per-capita-meat-consumption-by-type-kilograms-per-year", title: "Meat supply per capita by type" },
    { id: "co2-emissions-per-capita", title: "CO2 emissions per capita" },
    { id: "primary-energy-cons", title: "Primary energy consumption" },
    { id: "population", title: "Population" },
    { id: "life-expectancy", title: "Life expectancy at birth" },
    { id: "gdp-per-capita-worldbank", title: "GDP per capita, PPP (World Bank)" },
    { id: "share-of-population-in-extreme-poverty", title: "Extreme poverty share" },
    { id: "cereal-yield", title: "Cereal yield, t/ha" },
  ],
  async fetch(id, params) {
    const url = `https://ourworldindata.org/grapher/${encodeURIComponent(id)}.csv?v=1&csvType=full&useColumnShortNames=true`;
    const rows = parseCsv(await getText(url));
    if (rows.length < 2) throw new DataError(`OWID returned nothing for ${id}`);
    const header = rows[0].map((h) => h.trim());
    const lower = header.map((h) => h.toLowerCase());
    const ei = lower.indexOf("entity"), yi = lower.indexOf("year"), ci = lower.indexOf("code");
    const vi = header.findIndex((_, i) => i !== ei && i !== yi && i !== ci);
    if (ei < 0 || yi < 0 || vi < 0) throw new DataError(`Unexpected OWID columns: ${header.join(", ")}`);
    const want = params.entities ? new Set(params.entities.split(";").map((s) => s.trim().toLowerCase())) : null;
    const series: Record<string, Series> = {};
    for (const r of rows.slice(1)) {
      const name = r[ei]?.trim();
      if (!name || (want && !want.has(name.toLowerCase()))) continue;
      const d = normDate(r[yi] ?? "");
      const v = num(r[vi]);
      if (d && v !== null) (series[name] ??= {})[d] = v;
    }
    if (!Object.keys(series).length) throw new DataError(`No rows matched entities '${params.entities}' in ${id}`);
    return { provider: "owid", id, source: `Our World in Data: ${header[vi]} (${id})`, url, series,
      notes: ["Series keys are entity names as OWID spells them ('United States', 'European Union (27)', 'Turkey'). OWID re-publishes upstream sources; cite the original named on the chart page."] };
  },
  async search(query) { return curatedSearch(owid.curated, query); },
};

// ---------------------------------------------------------------------------
// TCMB EVDS (Turkey)

const evds: Provider = {
  name: "evds",
  title: "TCMB EVDS (Central Bank of Turkey)",
  coverage: "Turkey: exchange rates, policy and market rates, CPI/PPI detail, money, balance of payments, surveys, sector prices.",
  id_format: "EVDS series codes separated by '-', e.g. TP.DK.USD.A, TP.TUKFIY2025.GENEL (CPI 2025=100), TP.TUFE1YI.T1 (PPI). params.start/end as dd-mm-yyyy. search_external walks the full EVDS catalogue.",
  needs_key: "EVDS_API_KEY (free at evds2.tcmb.gov.tr)",
  curated: [
    { id: "TP.DK.USD.A", title: "USD/TRY buying rate, daily" },
    { id: "TP.DK.EUR.A", title: "EUR/TRY buying rate, daily" },
    { id: "TP.TUKFIY2025.GENEL", title: "CPI, general index (2025=100, from 2005), monthly" },
    { id: "TP.FE25.OKTG03", title: "CPI core B (ex unprocessed food, energy, alcohol, tobacco, gold), 2025=100" },
    { id: "TP.FG.J0", title: "CPI, general index (2003=100, ends 2026-01), monthly" },
    { id: "TP.TUFE1YI.T1", title: "Domestic PPI, general (2003=100), monthly" },
    { id: "TP.BISPOLFAIZ.TUR", title: "One-week repo policy rate" },
    { id: "TP.TRY.MT02", title: "Weighted average deposit rate, up to 3 months, weekly" },
    { id: "TP.PY.P01.T", title: "Money supply M1" },
    { id: "TP.TUFE1YI.T17", title: "PPI meat products" },
    { id: "TP.TUFE1YI.T25", title: "PPI prepared animal feeds" },
  ],
  async fetch(id, params, env) {
    if (!env.EVDS_API_KEY) throw new DataError("EVDS needs EVDS_API_KEY on the server. Set it with: npx wrangler secret put EVDS_API_KEY");
    const start = params.start ?? "01-01-2000";
    const end = params.end ?? new Date().toLocaleDateString("en-GB").replace(/\//g, "-");
    // Same endpoint the evds Python package (0.4) uses; the older evds2 service path now serves the web app.
    const url = `https://evds3.tcmb.gov.tr/igmevdsms-dis/series=${encodeURIComponent(id)}&startDate=${start}&endDate=${end}&type=json`;
    const j = (await getJson(url, { key: env.EVDS_API_KEY, accept: "application/json" })) as { items?: Array<Record<string, unknown>> };
    const items = j.items ?? [];
    const series: Record<string, Series> = {};
    for (const it of items) {
      const d = normDate(String(it.Tarih ?? ""));
      if (!d) continue;
      for (const [k, v] of Object.entries(it)) {
        if (k === "Tarih" || k === "UNIXTIME") continue;
        const x = num(v as string);
        if (x !== null) (series[k.replace(/_/g, ".")] ??= {})[d] = x;
      }
    }
    if (!Object.keys(series).length) throw new DataError(`EVDS returned no rows for ${id} between ${start} and ${end}`);
    return { provider: "evds", id, source: `TCMB EVDS ${id}`, url: url.replace(/key=[^&]+/, ""), series,
      notes: ["EVDS dates are as published: monthly 'YYYY-MM', daily 'YYYY-MM-DD'. Index bases and units are on the series page in EVDS."] };
  },
  async search(query, env) {
    if (!env.EVDS_API_KEY) return curatedSearch(evds.curated, query);
    // Walk the EVDS catalogue: all datagroups, then the series of the best-matching groups.
    const base = "https://evds3.tcmb.gov.tr/igmevdsms-dis/";
    const hdr = { key: env.EVDS_API_KEY, accept: "application/json" };
    type Group = { DATAGROUP_CODE: string; DATAGROUP_NAME_ENG?: string; DATAGROUP_NAME?: string; FREQUENCY_STR?: string };
    type Serie = { SERIE_CODE: string; SERIE_NAME_ENG?: string; SERIE_NAME?: string; FREQUENCY_STR?: string; START_DATE?: string; END_DATE?: string };
    // EVDS routes on the path: parameters follow the endpoint with no '?', as the data endpoint does.
    const groups = (await getJson(`${base}datagroups/mode=0&code=&type=json`, hdr)) as Group[];
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    const score = (s: string) => terms.reduce((n, t) => n + (s.toLowerCase().includes(t) ? 1 : 0), 0);
    const ranked = (Array.isArray(groups) ? groups : [])
      .map((g) => ({ g, s: score(`${g.DATAGROUP_NAME_ENG ?? ""} ${g.DATAGROUP_NAME ?? ""} ${g.DATAGROUP_CODE}`) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 4);
    const out: CuratedEntry[] = [];
    for (const { g } of ranked) {
      try {
        const series = (await getJson(`${base}serieList/type=json&code=${encodeURIComponent(g.DATAGROUP_CODE)}`, hdr)) as Serie[];
        for (const s of Array.isArray(series) ? series : []) {
          const name = s.SERIE_NAME_ENG || s.SERIE_NAME || "";
          out.push({ id: s.SERIE_CODE, title: `${name} [${g.DATAGROUP_NAME_ENG ?? g.DATAGROUP_CODE}]`, hint: [s.FREQUENCY_STR, s.START_DATE ? `${s.START_DATE}..${s.END_DATE ?? ""}` : ""].filter(Boolean).join(", ") });
        }
      } catch { /* one group failing should not hide the others */ }
    }
    const direct = out.filter((e) => score(`${e.id} ${e.title}`) > 0);
    return (direct.length ? direct : out).slice(0, 60);
  },
};

// ---------------------------------------------------------------------------
// BIS Data Portal (SDMX CSV)

const bis: Provider = {
  name: "bis",
  title: "BIS Data Portal",
  coverage: "Bank for International Settlements: residential property prices, credit to households and firms, debt service ratios, effective exchange rates, policy rates. Most countries, quarterly or monthly.",
  id_format: "'FLOW/KEY' as in the BIS portal, e.g. WS_SPP/Q.TR.N.628 (selected property prices, Türkiye, nominal, index 2010=100), WS_TC/Q.TR.H.A.M.770.A (credit to households, % of GDP), WS_CBPOL/M.TR (policy rate).",
  needs_key: null,
  curated: [
    { id: "WS_SPP/Q.TR.N.628", title: "Türkiye residential property prices, nominal index 2010=100, quarterly" },
    { id: "WS_SPP/Q.TR.R.628", title: "Türkiye residential property prices, real index, quarterly" },
    { id: "WS_SPP/Q.DE.N.628", title: "Germany residential property prices, nominal, quarterly" },
    { id: "WS_SPP/Q.US.N.628", title: "United States residential property prices, nominal, quarterly" },
    { id: "WS_TC/Q.TR.H.A.M.770.A", title: "Türkiye credit to households, % of GDP, quarterly" },
    { id: "WS_TC/Q.TR.N.A.M.770.A", title: "Türkiye credit to non-financial corporations, % of GDP, quarterly" },
    { id: "WS_CBPOL/M.TR", title: "Türkiye central bank policy rate, monthly" },
    { id: "WS_CBPOL/M.US", title: "US policy rate, monthly" },
    { id: "WS_EER/M.N.B.TR", title: "Türkiye nominal effective exchange rate, broad basket, monthly" },
    { id: "WS_EER/M.R.B.TR", title: "Türkiye real effective exchange rate, broad basket, monthly" },
  ],
  async fetch(id, params) {
    const [flow, key] = id.includes("/") ? id.split("/", 2) : [id, ""];
    if (!key) throw new DataError("BIS ids look like FLOW/KEY, e.g. WS_SPP/Q.TR.N.628");
    const extra: Record<string, string> = { format: "csv" };
    if (params.start) extra.startPeriod = params.start;
    if (params.end) extra.endPeriod = params.end;
    const url = `https://stats.bis.org/api/v2/data/dataflow/BIS/${encodeURIComponent(flow)}/1.0/${key}?${qs(extra)}`;
    // BIS CSV carries no KEY column; key on the coded dimension columns instead.
    const { series, columns } = sdmxCsvSeries(await getText(url, { accept: "text/csv" }));
    if (!Object.keys(series).length) throw new DataError(`BIS returned no observations for ${id}. Columns: ${columns.slice(0, 10).join(", ")}`);
    return { provider: "bis", id, source: `BIS Data Portal ${flow} ${key}`, url, series,
      notes: ["Series keys are the full SDMX keys. Property price indices are 2010=100; credit series are as labelled in the key (percent of GDP or currency)."] };
  },
  async search(query) { return curatedSearch(bis.curated, query); },
};

// ---------------------------------------------------------------------------
// FAOSTAT (FAO). Keyless JSON API; a domain plus area/item/element codes.

const FAO_HOSTS = ["https://faostatservices.fao.org/api/v1/en/", "https://fenixservices.fao.org/faostat/api/v1/en/"];

const FAO_DOMAINS: Record<string, string> = {
  QCL: "Crops and livestock products: production, area harvested, yield, stocks (elements 5510 production t, 5312 area ha, 5419 yield, 5111 stocks head, 5320 producing animals slaughtered)",
  PP: "Producer prices (elements 5530 LCU/t, 5532 USD/t, 5539 index 2014-16=100)",
  TCL: "Crops and livestock trade (elements 5610 import quantity t, 5622 import value 1000 USD, 5910 export quantity t, 5922 export value 1000 USD)",
  FBS: "Food balances 2010 onward (elements 664 food supply kcal/cap/day, 5142 food t, 5301 domestic supply t, 511 population)",
  RFN: "Fertilizers by nutrient (items 3102 N, 3103 P2O5, 3104 K2O; elements 5510 production, 5610 import qty, 5910 export qty, 5157 agricultural use t)",
  RL: "Land use (items 6601 agricultural land, 6621 cropland, 6655 permanent meadows; element 5110 area 1000 ha)",
  CP: "Consumer price indices, monthly (items 23013 food CPI, 23014 general CPI; element 6120 index 2015=100, 6122 food price inflation %)",
  QV: "Value of agricultural production (elements 152 gross production value current USD 1000, 154 constant 2014-16 USD)",
  EI: "Emissions intensities (element 723 kg CO2eq per kg product)",
  OA: "Population and employment in agriculture (item 3010 population; elements 511 total, 561 rural)",
};

async function faoGet(path: string): Promise<unknown> {
  const errors: string[] = [];
  for (const h of FAO_HOSTS) {
    try { return await getJson(h + path, { accept: "application/json" }); }
    catch (e) { errors.push(`${new URL(h).host}: ${e instanceof Error ? e.message : String(e)}`); }
  }
  throw new DataError(`FAOSTAT did not answer. ${errors.join(" | ")}`);
}

function faoList(v: string | undefined): string | undefined {
  if (!v) return undefined;
  // "2010:2024" -> "2010,2011,...,2024"; otherwise pass the comma list through.
  const m = /^(\d{4}):(\d{4})$/.exec(v.trim());
  if (!m) return v.replace(/\s+/g, "");
  const out: string[] = [];
  for (let y = Number(m[1]); y <= Number(m[2]); y++) out.push(String(y));
  return out.join(",");
}

const FAO_MONTHS: Record<string, string> = { "7001": "01", "7002": "02", "7003": "03", "7004": "04", "7005": "05", "7006": "06", "7007": "07", "7008": "08", "7009": "09", "7010": "10", "7011": "11", "7012": "12" };

const fao: Provider = {
  name: "fao",
  title: "FAOSTAT (FAO)",
  coverage: "Agriculture and food for every country and region, annual from 1961 (monthly for food price indices): production, livestock stocks, producer prices, trade, food balances, fertilizers, land use, emissions.",
  id_format: "A FAOSTAT domain code (QCL production and stocks, PP producer prices, TCL trade, FBS food balances, RFN fertilizers, RL land, CP consumer prices, QV production value) with params area, item, element as FAOSTAT codes, several separated by commas, and optional year '2010:2024'. Areas: 223 Türkiye, 231 USA, 79 Germany, 150 Netherlands, 21 Brazil, 351 China, 100 India, 5000 World, 5707 EU27. Items: 866 cattle, 1057 chickens, 976 sheep, 867 cattle meat, 1058 chicken meat, 882 raw cow milk, 1062 hen eggs, 15 wheat, 56 maize, 44 barley, 236 soybeans, 267 sunflower seed, 225 hazelnuts, 388 tomatoes, 157 sugar beet. search_external finds the rest.",
  needs_key: null,
  curated: [
    { id: "QCL", title: "Türkiye cattle stocks, head", hint: "params {area:'223', item:'866', element:'5111'}" },
    { id: "QCL", title: "Türkiye chicken meat production, tonnes", hint: "params {area:'223', item:'1058', element:'5510'}" },
    { id: "QCL", title: "Türkiye wheat production, tonnes", hint: "params {area:'223', item:'15', element:'5510'}" },
    { id: "QCL", title: "Türkiye raw cow milk production, tonnes", hint: "params {area:'223', item:'882', element:'5510'}" },
    { id: "PP", title: "Türkiye cattle meat producer price, USD/t", hint: "params {area:'223', item:'867', element:'5532'}" },
    { id: "PP", title: "Türkiye wheat producer price, USD/t", hint: "params {area:'223', item:'15', element:'5532'}" },
    { id: "PP", title: "Türkiye raw milk producer price, LCU/t", hint: "params {area:'223', item:'882', element:'5530'}" },
    { id: "TCL", title: "Türkiye soybean imports, tonnes", hint: "params {area:'223', item:'236', element:'5610'}" },
    { id: "TCL", title: "Türkiye hazelnut exports, 1000 USD", hint: "params {area:'223', item:'225', element:'5922'}" },
    { id: "RFN", title: "Türkiye nitrogen fertilizer agricultural use, tonnes N", hint: "params {area:'223', item:'3102', element:'5157'}" },
    { id: "CP", title: "Türkiye food CPI, monthly, 2015=100", hint: "params {area:'223', item:'23013', element:'6120'}" },
    { id: "FBS", title: "Türkiye food supply, kcal per capita per day", hint: "params {area:'223', item:'2901', element:'664'}" },
    { id: "QCL", title: "World cattle stocks, head", hint: "params {area:'5000', item:'866', element:'5111'}" },
  ],
  async fetch(id, params) {
    const domain = id.trim().toUpperCase();
    if (!/^[A-Z]{2,4}$/.test(domain)) throw new DataError(`FAOSTAT ids are domain codes such as QCL, PP, TCL. Known: ${Object.keys(FAO_DOMAINS).join(", ")}`);
    if (!params.item && !params.element) throw new DataError("FAOSTAT needs at least item or element in params, e.g. {area:'223', item:'866', element:'5111'}. Use search_external to find codes.");
    const q: Record<string, string> = { area: faoList(params.area) ?? "223", show_codes: "true", show_unit: "true", show_flags: "false", null_values: "false", output_type: "objects" };
    if (params.item) q.item = faoList(params.item)!;
    if (params.element) q.element = faoList(params.element)!;
    if (params.year) q.year = faoList(params.year)!;
    const path = `data/${domain}?${qs(q)}`;
    const j = (await faoGet(path)) as { data?: Record<string, string | number>[] };
    const rows = Array.isArray(j?.data) ? j.data : [];
    if (!rows.length) throw new DataError(`FAOSTAT returned no rows for ${domain} with ${JSON.stringify(params)}. Check the codes with search_external.`);
    const dimNames = ["Area", "Item", "Element"];
    const distinct = dimNames.map((d) => new Set(rows.map((r) => String(r[d] ?? ""))));
    const keyDims = dimNames.filter((_, i) => distinct[i].size > 1);
    const series: Record<string, Series> = {};
    const units = new Set<string>();
    for (const r of rows) {
      const v = num(r.Value as string);
      if (v === null) continue;
      const y = String(r.Year ?? r["Year Code"] ?? "").trim();
      if (!/^\d{4}$/.test(y)) continue;
      const mc = String(r["Months Code"] ?? "");
      const date = FAO_MONTHS[mc] ? `${y}-${FAO_MONTHS[mc]}` : mc && !FAO_MONTHS[mc] ? "" : y;   // annual rows in a monthly domain are skipped
      if (!date) continue;
      const key = keyDims.length ? keyDims.map((d) => String(r[d])).join("|") : `${r.Area}|${r.Item}|${r.Element}`;
      (series[key] ??= {})[date] = v;
      if (r.Unit) units.add(String(r.Unit));
    }
    if (!Object.keys(series).length) throw new DataError(`FAOSTAT rows for ${domain} carried no numeric values`);
    const src = `FAOSTAT ${domain} (${FAO_DOMAINS[domain]?.split(":")[0] ?? domain})`;
    return { provider: "fao", id: domain, source: src, url: FAO_HOSTS[0] + path, series,
      notes: [`Units: ${[...units].join(", ") || "as published"}. FAOSTAT figures are official, semi-official, estimated or imputed by country and year; the flags are on the FAOSTAT site.`,
        keyDims.length ? `Series keys are ${keyDims.join("|")} labels.` : "Single series: area, item and element were all fixed."] };
  },
  async search(query) {
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    const score = (s: string) => terms.reduce((n, t) => n + (s.toLowerCase().includes(t) ? 1 : 0), 0);
    const out: CuratedEntry[] = [];
    for (const [code, desc] of Object.entries(FAO_DOMAINS)) if (score(`${code} ${desc}`) > 0) out.push({ id: code, title: `domain ${code}: ${desc}` });
    type Def = { code: string; label: string };
    const lists: [string, string, string][] = [["QCL", "item", "item"], ["PP", "item", "item"], ["QCL", "area", "area"], ["QCL", "element", "element"], ["TCL", "element", "element"]];
    const seen = new Set<string>();
    await Promise.all(lists.map(async ([domain, dim, param]) => {
      try {
        const j = (await faoGet(`definitions/domain/${domain}/${dim}`)) as { data?: Def[] };
        for (const d of j?.data ?? []) {
          const k = `${param}:${d.code}`;
          if (seen.has(k) || score(`${d.code} ${d.label}`) === 0) continue;
          seen.add(k);
          out.push({ id: domain, title: `${param} ${d.code}: ${d.label}`, hint: `params {${param}:'${d.code}'} in ${domain}${dim === "item" ? " (also PP, TCL)" : ""}` });
        }
      } catch { /* a definitions list failing should not hide the rest */ }
    }));
    return out.sort((a, b) => score(b.title) - score(a.title)).slice(0, 60);
  },
};

// ---------------------------------------------------------------------------

export function curatedSearch(list: CuratedEntry[], query: string): CuratedEntry[] {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  return list
    .map((e) => {
      const hay = `${e.id} ${e.title} ${e.hint ?? ""}`.toLowerCase();
      const score = terms.reduce((s, t) => s + (e.id.toLowerCase() === t ? 3 : 0) + (hay.includes(t) ? 1 : 0), 0);
      return { e, score };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((x) => x.e);
}

export const PROVIDERS: Record<string, Provider> = { fred, eurostat, worldbank, ecb, oecd, owid, evds, bis, fao };

export function providerInfo(env: ProviderEnv) {
  return Object.values(PROVIDERS).map((p) => ({
    provider: p.name,
    title: p.title,
    coverage: p.coverage,
    id_format: p.id_format,
    needs_key: p.needs_key,
    key_present: p.name === "evds" ? (env.EVDS_API_KEY ? "yes (fetch and catalogue search enabled)" : "no") : p.name === "fred" ? (env.FRED_API_KEY ? "yes (search enabled)" : "no (fetch works, search uses the starter list)") : "not needed",
    starter_ids: p.curated.slice(0, 8).map((c) => `${c.id}: ${c.title}`),
  }));
}
