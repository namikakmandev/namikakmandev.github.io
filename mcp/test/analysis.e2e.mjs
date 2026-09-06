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
const worker = await startWorker(handler, { DATA_ORIGIN: origin, EVDS_API_KEY: "test-key", FRED_API_KEY: "fred-key", FAOSTAT_USER: "fao@example.com", FAOSTAT_PASSWORD: "pw" });
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
  assert.match(String(evds.key_present), /yes/);
  assert.equal(j.providers.length, 10);
});

await check("IMF: SDMX-CSV keyed by the dimension columns, dataflow search", async () => {
  const j = await call("fetch_external", { provider: "imf", id: "IMF.RES/WEO/TUR+USA.NGDP_RPCH.A" });
  assert.equal(j.series_count, 2);
  const tr = await call("fetch_external", { provider: "imf", id: "IMF.RES/WEO/TUR+USA.NGDP_RPCH.A", series: "TUR.NGDP_RPCH.A" });
  assert.deepEqual(tr.points, [["2023", 5.1], ["2024", 3.2], ["2025", 2.7]]);
  const s = await call("search_external", { provider: "imf", query: "consumer price" });
  assert.ok(s.matches.some((m) => /IMF.STA\/CPI/.test(m.id)), JSON.stringify(s.matches).slice(0, 300));
});

await check("FAOSTAT: rows keyed by the varying dimension, search over definitions", async () => {
  const j = await call("fetch_external", { provider: "fao", id: "QCL", params: { area: "223,231", item: "866", element: "5111" } });
  assert.equal(j.series_count, 2);
  const tr = await call("fetch_external", { provider: "fao", id: "QCL", params: { area: "223,231", item: "866", element: "5111" }, series: "Türkiye" });
  assert.deepEqual(tr.points, [["2021", 18036117], ["2022", 17024129]]);
  const s = await call("search_external", { provider: "fao", query: "cattle" });
  assert.ok(s.matches.some((m) => m.id === "QCL" && /866/.test(m.title)), JSON.stringify(s.matches).slice(0, 300));
  // Without an account the fetch fails with the registration pointer and search falls back to the starter list.
  const w2 = await startWorker(handler, { DATA_ORIGIN: origin });
  const c2 = new Client({ name: "e2e-noacct", version: "0.0.0" });
  await c2.connect(new StreamableHTTPClientTransport(new URL(addr(w2) + "/mcp")));
  const bad = await c2.callTool({ name: "fetch_external", arguments: { provider: "fao", id: "QCL", params: { item: "866", element: "5111" } } });
  assert.ok(bad.isError && /developer-portal/.test(bad.content[0].text), bad.content[0].text);
  const s2 = JSON.parse((await c2.callTool({ name: "search_external", arguments: { provider: "fao", query: "cattle" } })).content[0].text);
  assert.ok(s2.matches.length > 0 && s2.matches.every((m) => !/866:/.test(m.title)));
  const info = JSON.parse((await c2.callTool({ name: "list_providers", arguments: {} })).content[0].text);
  assert.match(info.providers.find((p) => p.provider === "fao").key_present, /^no/);
  await c2.close(); w2.close();
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


await check("BIS: SDMX CSV keyed by KEY, quarterly dates", async () => {
  const j = await call("fetch_external", { provider: "bis", id: "WS_SPP/Q.TR.N.628" });
  assert.deepEqual(j.points[0], ["2024-Q1", 1315.4]);
});

await check("EVDS catalogue search walks datagroups and series", async () => {
  const s = await call("search_external", { provider: "evds", query: "consumer price index" });
  assert.ok(s.matches.some((m) => m.id === "TP.FG.J0X"), JSON.stringify(s.matches).slice(0, 200));
});

await check("plot resolves every series and links to chart.html with the spec in the fragment", async () => {
  const j = await call("plot", { series: [{ ...CATTLE, start: "2015-01" }, { ...CORN, start: "2015-01" }], title: "Cattle vs corn", right_axis: [1] });
  assert.ok(j.chart_url.startsWith(origin + "/chart.html#"), j.chart_url);
  const spec = JSON.parse(Buffer.from(j.chart_url.split("#")[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString());
  assert.equal(spec.series.length, 2);
  assert.deepEqual(spec.right, [1]);
  assert.equal(spec.api, base);
  assert.equal(j.series[0].first, "2015-01");
  const bad = await client.callTool({ name: "plot", arguments: { series: [{ dataset: "us-prices", series: "nope" }] } });
  assert.ok(bad.isError);
});

await check("GET /v1/series returns points for a spec, and errors per series", async () => {
  const spec = { series: [{ ...CATTLE, start: "2020-01", end: "2020-03" }, { dataset: "us-prices", series: "nope" }] };
  const r = await fetch(base + "/v1/series?s=" + encodeURIComponent(JSON.stringify(spec)));
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.equal(j.series.length, 2);
  assert.equal(j.series[0].n, 3);
  assert.match(j.series[1].error, /No series 'nope'/);
  const p = await fetch(base + "/v1/series", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(spec) });
  assert.equal((await p.json()).series[0].points[0][0], "2020-01");
  const badr = await fetch(base + "/v1/series?s=" + encodeURIComponent("{}"));
  assert.equal(badr.status, 400);
});

await check("test_stationarity reports KPSS and a joint reading", async () => {
  const j = await call("test_stationarity", { series: { ...CPI, start: "1990-01" } });
  assert.ok(j.kpss && typeof j.kpss.statistic === "number");
  assert.match(j.joint_reading, /unit root|stationary|borderline|short/);
});

await check("johansen on cattle, corn and CPI logs returns trace tests and a rank", async () => {
  const j = await call("johansen", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }, { ...CPI, transform: "log", start: "1990-01" }], lags: 2 });
  assert.equal(j.trace_tests.length, 3);
  assert.ok(j.rank_at_5pct >= 0 && j.rank_at_5pct <= 3);
});

await check("vecm on cattle and corn logs reports adjustment and the current deviation, or a clear rank-0 message", async () => {
  const r = await callRaw("vecm", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], lags: 2 });
  const t = r.content[0].text;
  if (r.isError) assert.match(t, /rank 0|No cointegrating/);
  else { const j = JSON.parse(t); assert.ok(j.relations.length >= 1 && typeof j.relations[0].ect_last === "number"); assert.ok(j.reading.length > 20); }
  const forced = await call("vecm", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], lags: 2, rank: 1 });
  assert.equal(forced.rank, 1);
  assert.equal(forced.relations[0].adjustment.length, 2);
});

await check("var_model on growth rates gives IRFs, FEVD and block Granger tests", async () => {
  const j = await call("var_model", { series: [{ ...CORN, transform: "pct_change", start: "1995-01" }, { ...CATTLE, transform: "pct_change", start: "1995-01" }], horizon: 6 });
  assert.ok(j.lags >= 1);
  assert.equal(j.impulse_responses.horizons.length, 7);
  assert.equal(j.granger_block_tests.length, 2);
  assert.equal(j.warnings.length, 0, JSON.stringify(j.warnings));
  const fevd = j.variance_decomposition_at_horizon;
  const row = Object.values(fevd)[0];
  assert.ok(Math.abs(Object.values(row).reduce((a, b) => a + b, 0) - 1) < 0.01);
});

await check("forecast method arima picks an order and returns dated points", async () => {
  const j = await call("forecast", { series: { ...CPI, start: "2015-01" }, horizon: 4, method: "arima" });
  assert.match(j.method, /^ARIMA\(\d,\d,\d\)/);
  assert.equal(j.forecast.length, 4);
});

await check("deflate expresses cattle PPI in CPI terms of a base month", async () => {
  const j = await call("deflate", { nominal: CATTLE, deflator: CPI, base: "2020-01" });
  const b = j.points.find((p) => p[0] === "2020-01");
  const raw = await call("get_series", { dataset: "us-prices", series: "cattle_ppi", start: "2020-01", end: "2020-01" });
  assert.ok(Math.abs(b[1] - raw.points[0][1]) < 1e-3, "at the base date real equals nominal");
});

await client.close();
worker.close();
stat.close();
console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
