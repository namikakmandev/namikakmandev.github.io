/**
 * Series arithmetic. Pure functions over date -> value maps.
 * Dates are "YYYY", "YYYY-MM" or "YYYY-MM-DD" strings and sort lexically.
 */
import type { Series } from "./data.js";
import { DataError } from "./data.js";

export type Transform = "none" | "pct_change" | "yoy" | "diff" | "rebase" | "log";
export type Frequency = "native" | "annual_mean" | "annual_last";

export function clip(s: Series, start?: string, end?: string, lastN?: number): Series {
  let keys = Object.keys(s).sort();
  if (start) keys = keys.filter((k) => k >= start);
  if (end) keys = keys.filter((k) => k <= end || k.startsWith(end));
  if (lastN && lastN > 0) keys = keys.slice(-lastN);
  const out: Series = {};
  for (const k of keys) out[k] = s[k];
  return out;
}

/** The same date one year earlier, in the series' own key format. */
function yearBefore(d: string): string {
  const y = Number(d.slice(0, 4)) - 1;
  return String(y).padStart(4, "0") + d.slice(4);
}

export function apply(s: Series, t: Transform, base?: string): Series {
  const keys = Object.keys(s).sort();
  const out: Series = {};
  switch (t) {
    case "none":
      return s;
    case "log":
      for (const k of keys) if (s[k] > 0) out[k] = Math.log(s[k]);
      return out;
    case "diff":
      for (let i = 1; i < keys.length; i++) out[keys[i]] = s[keys[i]] - s[keys[i - 1]];
      return out;
    case "pct_change":
      for (let i = 1; i < keys.length; i++) {
        const prev = s[keys[i - 1]];
        if (prev !== 0) out[keys[i]] = (s[keys[i]] / prev - 1) * 100;
      }
      return out;
    case "yoy":
      for (const k of keys) {
        const prev = s[yearBefore(k)];
        if (prev !== undefined && prev !== 0) out[k] = (s[k] / prev - 1) * 100;
      }
      return out;
    case "rebase": {
      const b = base ?? keys[0];
      const bv = s[b];
      if (bv === undefined) throw new DataError(`Rebase date ${b} is not in the series (range ${keys[0]}..${keys[keys.length - 1]})`);
      if (bv === 0) throw new DataError(`Cannot rebase on a zero value at ${b}`);
      for (const k of keys) out[k] = (s[k] / bv) * 100;
      return out;
    }
  }
}

export function resample(s: Series, f: Frequency): Series {
  if (f === "native") return s;
  const groups = new Map<string, number[]>();
  for (const k of Object.keys(s).sort()) {
    const y = k.slice(0, 4);
    if (!groups.has(y)) groups.set(y, []);
    groups.get(y)!.push(s[k]);
  }
  const out: Series = {};
  for (const [y, vals] of groups) {
    out[y] = f === "annual_last" ? vals[vals.length - 1] : vals.reduce((a, b) => a + b, 0) / vals.length;
  }
  return out;
}

export function round(s: Series, digits = 4): Series {
  const m = 10 ** digits;
  const out: Series = {};
  for (const k of Object.keys(s)) out[k] = Math.round(s[k] * m) / m;
  return out;
}

export function toPoints(s: Series): [string, number][] {
  return Object.keys(s).sort().map((k) => [k, s[k]]);
}

/** Pearson correlation over the dates two series share. */
export function correlation(a: Series, b: Series): { r: number; n: number } | null {
  const keys = Object.keys(a).filter((k) => k in b);
  const n = keys.length;
  if (n < 3) return null;
  const xs = keys.map((k) => a[k]);
  const ys = keys.map((k) => b[k]);
  const mx = xs.reduce((p, q) => p + q, 0) / n;
  const my = ys.reduce((p, q) => p + q, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx, dy = ys[i] - my;
    sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
  }
  if (sxx === 0 || syy === 0) return null;
  return { r: Math.round((sxy / Math.sqrt(sxx * syy)) * 1000) / 1000, n };
}
