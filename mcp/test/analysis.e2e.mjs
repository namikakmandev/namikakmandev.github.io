// End-to-end for providers (against fixtures) and the analysis tools (against the
// repo's own data), through the real MCP client. Run: npm test
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { startStatic, startWorker, addr } from "./serve-node.mjs";
import { installFetchMock } from "./fixtures.mjs";

const { default: handler } = await import("../dist/index.js");
installFetchMock();

const stat = await startStatic();
const origin = addr(stat);
const worker = await startWorker(handler, { DATA_ORIGIN: origin, EVDS_API_KEY: "test-key", FRED_API_KEY: "fred-key" });
const base = addr(worker);

let failures = 0;
async function check(name, fn) {
  try { await fn(); console.log("ok   ", name); }
  catch (e) { failures++; console.log("FAIL ", name, "\n     ", e.message.split("\n")[0]); }
}
const client = new Client({ name: "e2e-analysis", version: "0.0.0" });
await client.connect(new StreamableHTTPClientTransport(new URL(base + "/mcp")));
const call = async (name, args) => {
  const r = await client.callTool({ name, arguments: args });
  if (r.isError) throw new Error(`${name}: ${r.content[0].text}`);
  return JSON.parse(r.content[0].text);
};
const callRaw = (name, args) => client.callTool({ name, arguments: args });

// --- providers -----------------------------------------------------------------
await check("tool list includes providers and analysis", async () => {
  const { tools } = await client.listTools();
  const names = new Set(tools.map((t) => t.name));
  for (const n of ["list_providers", "search_external", "fetch_external", "describe_stats", "test_stationarity", "regress", "granger_causality", "cointegration", "cross_correlation", "hp_filter", "decompose", "forecast", "structural_break", "rolling", "suggest_analysis"]) assert.ok(names.has(n), n);
});

await check("list_providers reports key state", async () => {
  const j = await call("list_providers", {});
  const evds = j.providers.find((p) => p.provider === "evds");
  assert.equal(evds.key_present, true);
  assert.equal(j.providers.length, 7);
});

await check("FRED: keyless CSV parses, missing '.' dropped, search via API", async () => {
  const j = await call("fetch_external", { provider: "fred", id: "CPIAUCSL" });
  assert.equal(j.first, "2019-11", "monthly FRED dates collapse to YYYY-MM");
  assert.equal(j.last, "2021-12");
  assert.equal(j.n, 26);
  const s = await call("search_external", { provider: "fred", query: "consumer price index" });
  assert.equal(s.matches[0].id, "CPIAUCSL");
  const yoy = await call("fetch_external", { provider: "fred", id: "CPIAUCSL", transform: "yoy", start: "2020-12" });
  assert.equal(yoy.points[0][0], "2020-12");
  assert.ok(Math.abs(yoy.points[0][1] - 1.39) < 0.05, `Dec 2020 yoy ${yoy.points[0][1]}`);
});

await check("Eurostat: JSON-stat with two geos lists keys, then narrows", async () => {
  const j = await call("fetch_external", { provider: "eurostat", id: "prc_hicp_midx", params: { coicop: "CP00", unit: "I15" } });
  assert.equal(j.series_count, 2);
  assert.deepEqual(j.series.map((s) => s.key).sort(), ["DE", "TR"]);
  const tr = await call("fetch_external", { provider: "eurostat", id: "prc_hicp_midx", params: { coicop: "CP00", unit: "I15" }, series: "TR" });
  assert.deepEqual(tr.points, [["2024-01", 1690.4], ["2024-02", 1767.2], ["2024-03", 1823.9]]);
  const bad = await callRaw("fetch_external", { provider: "eurostat", id: "nope_dataset" });
  assert.equal(bad.isError, true);
});

await check("World Bank: ISO3 keys, nulls dropped, indicator search", async () => {
  const j = await call("fetch_external", { provider: "worldbank", id: "NY.GDP.MKTP.CD", params: { country: "TR;US" } });
  assert.deepEqual(j.series.map((s) => s.key).sort(), ["TUR", "USA"]);
  const us = j.series.find((s) => s.key === "USA");
  assert.equal(us.n, 1);
  const s = await call("search_external", { provider: "worldbank", query: "gdp current" });
  assert.equal(s.matches[0].id, "NY.GDP.MKTP.CD");
});

await check("ECB: SDMX CSV keyed by KEY", async () => {
  const j = await call("fetch_external", { provider: "ecb", id: "EXR/M.USD.EUR.SP00.A" });
  assert.equal(j.series, "EXR.M.USD.EUR.SP00.A");
  assert.deepEqual(j.points[0], ["2024-01", 1.0905]);
});

await check("OECD: labelled CSV keyed by coded dimensions", async () => {
  const j = await call("fetch_external", { provider: "oecd", id: "OECD.SDD.STES,DSD_STES@DF_CLI,4.1/.M.LI...AA...H" });
  assert.equal(j.series_count, 2);
  const keys = j.series.map((s) => s.key);
  assert.ok(keys.some((k) => k.startsWith("TUR.")) && keys.some((k) => k.startsWith("USA.")), keys.join(","));
});

await check("OWID: entity filter", async () => {
  const j = await call("fetch_external", { provider: "owid", id: "cattle-livestock-count-heads", params: { entities: "Turkey" } });
  assert.deepEqual(j.points, [["2021", 18036117], ["2022", 17024129]]);
  const all = await call("fetch_external", { provider: "owid", id: "cattle-livestock-count-heads" });
  assert.equal(all.series_count, 3);
});

await check("EVDS: key header sent, monthly dates normalised", async () => {
  const j = await call("fetch_external", { provider: "evds", id: "TP.DK.USD.A" });
  assert.equal(j.series, "TP.DK.USD.A");
  assert.deepEqual(j.points[0], ["2024-01", 30.1153]);
});

// --- analysis on local data -----------------------------------------------------
const CPI = { dataset: "us-prices", series: "cpi" };
const CATTLE = { dataset: "us-prices", series: "cattle_ppi" };
const CORN = { dataset: "us-prices", series: "corn_ppi" };

await check("describe_stats: CPI is I(1), trending, carries caveats", async () => {
  const j = await call("describe_stats", { series: { ...CPI, start: "1990-01" } });
  assert.equal(j.frequency, "monthly");
  assert.equal(j.unit_root.integration_order, "I(1)", JSON.stringify(j.unit_root));
  assert.ok(j.linear_trend.t > 10);
  assert.ok(j.caveats.some((c) => c.includes("index numbers")));
  assert.ok(Array.isArray(j.acf) && j.acf[0] > 0.9);
});

await check("test_stationarity: CPI yoy inflation vs CPI level", async () => {
  const lvl = await call("test_stationarity", { series: { ...CPI, start: "1990-01" } });
  assert.equal(lvl.levels.reject_unit_root_at, null);
  assert.ok(lvl.levels.critical["5%"] < -2.8);
  const infl = await call("test_stationarity", { series: { ...CPI, start: "1990-01", transform: "yoy" } });
  assert.ok(["I(0)", "I(1)"].includes(infl.integration_order));
});

await check("regress: log cattle on log corn warns about spurious levels; growth regression does not", async () => {
  const lv = await call("regress", { y: { ...CATTLE, transform: "log", start: "1990-01" }, x: [{ ...CORN, transform: "log", start: "1990-01" }] });
  assert.equal(lv.coefficients.length, 2);
  assert.ok(lv.elasticities);
  assert.ok(lv.warnings.some((w) => /spurious/.test(w)), JSON.stringify(lv.warnings));
  const gr = await call("regress", { y: { ...CATTLE, transform: "pct_change", start: "1990-01" }, x: [{ ...CORN, transform: "pct_change", start: "1990-01" }], x_lags: 2 });
  assert.equal(gr.coefficients.length, 4);
  assert.ok(!gr.warnings.some((w) => /spurious/.test(w)));
  assert.ok(gr.coefficients.every((c) => typeof c.hac_se === "number"));
});

await check("granger_causality on growth rates returns both directions", async () => {
  const j = await call("granger_causality", { a: { ...CORN, transform: "pct_change", start: "1990-01" }, b: { ...CATTLE, transform: "pct_change", start: "1990-01" }, lags: 3 });
  assert.ok(typeof j.a_causes_b.p === "number" && typeof j.b_causes_a.p === "number");
  assert.equal(j.warnings.length, 0, JSON.stringify(j.warnings));
});

await check("cointegration reports orders, vector and verdict", async () => {
  const j = await call("cointegration", { a: { ...CATTLE, transform: "log", start: "1990-01" }, b: { ...CORN, transform: "log", start: "1990-01" }, include_residuals: true });
  assert.equal(j.integration_order.a, "I(1)");
  assert.ok(typeof j.long_run.slope === "number");
  assert.ok(j.residual_test.critical["5%"] < -3);
  assert.ok(Array.isArray(j.equilibrium_error) && j.equilibrium_error.length > 300);
});

await check("cross_correlation finds a lag and a band", async () => {
  const j = await call("cross_correlation", { a: { ...CORN, transform: "pct_change", start: "2000-01" }, b: { ...CATTLE, transform: "pct_change", start: "2000-01" }, max_lag: 6 });
  assert.equal(j.correlations.length, 13);
  assert.ok(j.significance_band > 0 && j.significance_band < 0.2);
});

await check("hp_filter picks the monthly lambda and returns components", async () => {
  const j = await call("hp_filter", { series: { ...CPI, start: "2010-01", transform: "log" } });
  assert.equal(j.lambda, 129600);
  assert.equal(j.trend.length, j.cycle.length);
  assert.ok(Math.abs(j.trend[0][1] + j.cycle[0][1] - Math.log(217.488)) < 0.01);
});

await check("decompose on meat CPI gives 12 factors and a reading", async () => {
  const j = await call("decompose", { series: { dataset: "meat-cpi-us", series: (await call("describe_dataset", { dataset: "meat-cpi-us" })).series[0].id, start: "2010-01" } });
  assert.equal(j.seasonal_factors.length, 12);
  assert.equal(j.seasonal_factors[0].season, "Jan");
  assert.ok(typeof j.seasonal_strength === "number");
});

await check("forecast: auto picks Holt-Winters for monthly, dates continue, band widens", async () => {
  const j = await call("forecast", { series: { ...CPI, start: "2015-01" }, horizon: 6 });
  assert.match(j.method, /Holt-Winters/);
  assert.equal(j.forecast.length, 6);
  const last = j.last_actual[0];
  assert.ok(j.forecast[0].date > last, `${j.forecast[0].date} after ${last}`);
  assert.ok(j.forecast[5].hi95 - j.forecast[5].lo95 > j.forecast[0].hi95 - j.forecast[0].lo95);
  const ar = await call("forecast", { series: { ...CPI, start: "2015-01", transform: "pct_change" }, horizon: 3, method: "ar", ar_order: 3 });
  assert.equal(ar.method, "AR(3)");
});

await check("structural_break scans and tests a date", async () => {
  const scan = await call("structural_break", { y: { ...CPI, start: "2015-01", transform: "yoy" } });
  assert.match(scan.most_likely_break, /^\d{4}-\d{2}$/);
  const at = await call("structural_break", { y: { ...CPI, start: "2015-01", transform: "yoy" }, date: "2021-03" });
  assert.equal(at.test, "Chow");
  assert.ok(at.p < 0.05);
});

await check("rolling correlation over 36 months", async () => {
  const j = await call("rolling", { series: { ...CATTLE, transform: "pct_change", start: "2005-01" }, other: { ...CORN, transform: "pct_change", start: "2005-01" }, stat: "corr", window: 36 });
  assert.ok(j.n > 100);
  assert.ok(j.points.every((p) => p[1] === null || Math.abs(p[1]) <= 1));
});

await check("inline points work as a series reference", async () => {
  const pts = Array.from({ length: 40 }, (_, i) => [String(1980 + i), 100 + 3 * i + (i % 2 ? 1 : -1)]);
  const j = await call("describe_stats", { series: { points: pts, label: "mine" } });
  assert.equal(j.label, "mine");
  assert.equal(j.frequency, "annual");
  assert.equal(j.n, 40);
});

await check("suggest_analysis: two I(1) series get cointegration first; one series gets a forecast path", async () => {
  const two = await call("suggest_analysis", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], question: "does corn drive cattle?" });
  assert.equal(two.series.length, 2);
  const tools = two.plan.map((p) => p.tool);
  assert.ok(tools.includes("cointegration") && tools.includes("granger_causality") && tools.includes("rolling"), tools.join(","));
  assert.ok(tools.indexOf("cointegration") < tools.indexOf("regress"));
  assert.ok(two.pitfalls.some((p) => /I\(1\)/.test(p)));
  const one = await call("suggest_analysis", { series: [{ ...CPI, start: "2010-01" }] });
  assert.ok(one.plan.some((p) => p.tool === "forecast"));
  const mixed = await call("suggest_analysis", { series: [CPI, { dataset: "herd-cattle", series: "US" }] });
  assert.ok(mixed.pitfalls.some((p) => /Mixed frequencies/.test(p)));
});

await check("provider ref inside an analysis tool", async () => {
  const j = await call("describe_stats", { series: { provider: "fred", id: "CPIAUCSL" } });
  assert.equal(j.n, 26);
  assert.equal(j.frequency, "monthly");
  // FRED monthly keys now align with the curated monthly files
  const cmp = await call("regress", { y: { provider: "fred", id: "CPIAUCSL", transform: "pct_change" }, x: [{ dataset: "us-prices", series: "cpi", transform: "pct_change" }] });
  assert.ok(cmp.n >= 20, `aligned n=${cmp.n}`);
  // The fixture holds hand-typed CPI values that differ slightly from the revised vintage in data/, so the slope is near 1, not exactly 1.
  assert.ok(Math.abs(cmp.coefficients[1].coef - 1) < 0.2, `same series should regress with slope near 1, got ${cmp.coefficients[1].coef}`);
});

await client.close();
worker.close();
stat.close();
console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
