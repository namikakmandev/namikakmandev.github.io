// End-to-end for providers (against fixtures) and the analysis tools (against the
// repo's own data), through the real MCP client. Run: npm test
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { startStatic, startWorker, addr } from "./serve-node.mjs";
import { installFetchMock, setSecBlocked } from "./fixtures.mjs";

const { default: handler } = await import("../dist/index.js");
installFetchMock();

const stat = await startStatic();
const origin = addr(stat);
const worker = await startWorker(handler, { DATA_ORIGIN: origin, EVDS_API_KEY: "test-key", FRED_API_KEY: "fred-key", FAOSTAT_USER: "fao@example.com", FAOSTAT_PASSWORD: "pw", SEC_USER_AGENT: "Test Caller test@example.com" });
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
  for (const n of ["list_providers", "search_external", "fetch_external", "describe_stats", "test_stationarity", "regress", "granger_causality", "cointegration", "cross_correlation", "hp_filter", "decompose", "forecast", "structural_break", "rolling", "suggest_analysis", "forecast_evaluate", "local_projections", "iv_regress", "predict"]) assert.ok(names.has(n), n);
});

await check("list_providers reports key state", async () => {
  const j = await call("list_providers", {});
  const evds = j.providers.find((p) => p.provider === "evds");
  assert.match(String(evds.key_present), /yes/);
  assert.equal(j.providers.length, 12);
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

await check("decompose labels seasons from the first date, whatever format it comes in", async () => {
  // Quarterly data written as ISO month-ends, starting in Q2, with the peak on the first observation.
  const season = [0, 5, 0, -5];                     // Q1, Q2, Q3, Q4
  const iso = Array.from({ length: 40 }, (_, i) => {
    const month = ((i + 1) % 4) * 3 + 1;            // i=0 -> April (Q2)
    const year = 2015 + Math.floor((i + 1) / 4);
    return [`${year}-${String(month).padStart(2, "0")}-01`, 100 + 0.5 * i + season[(i + 1) % 4]];
  });
  const j = await call("decompose", { series: { points: iso, label: "iso quarters" }, period: 4 });
  assert.equal(j.seasonal_factors.length, 4);
  assert.ok(j.seasonal_factors.every((f) => /^Q[1-4]$/.test(f.season)), JSON.stringify(j.seasonal_factors));
  const peak = j.seasonal_factors.reduce((a, b) => (b.effect > a.effect ? b : a));
  assert.equal(peak.season, "Q2", `peak labelled ${peak.season}`);
  const trough = j.seasonal_factors.reduce((a, b) => (b.effect < a.effect ? b : a));
  assert.equal(trough.season, "Q4", `trough labelled ${trough.season}`);
  // 'YYYY-Qn' is the other quarterly spelling and must land on the same labels.
  const qn = iso.map(([d, v], i) => [`${2015 + Math.floor((i + 1) / 4)}-Q${((i + 1) % 4) + 1}`, v]);
  const q = await call("decompose", { series: { points: qn }, period: 4 });
  assert.deepEqual(q.seasonal_factors.map((f) => f.season), j.seasonal_factors.map((f) => f.season));
  // An annual date carries no season; labels must still be real, starting at the first one.
  const ann = Array.from({ length: 40 }, (_, i) => [String(1980 + i), 100 + 0.5 * i + season[i % 4]]);
  const a = await call("decompose", { series: { points: ann }, period: 4 });
  assert.ok(a.seasonal_factors.every((f) => typeof f.season === "string"), JSON.stringify(a.seasonal_factors));
  assert.equal(a.seasonal_factors[0].season, "Q1");
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
  // Bands ride in the spec; one that points past the series list is refused.
  const banded = await call("plot", { series: [{ ...CATTLE, start: "2024-01" }], bands: [{ series: 0, label: "range", points: [["2024-01", 100, 120], ["2024-02", 101, 122]] }] });
  const bs = JSON.parse(Buffer.from(banded.chart_url.split("#")[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString());
  assert.equal(bs.bands.length, 1); assert.equal(bs.bands[0].points.length, 2); assert.equal(bs.xaxis, undefined);
  const off = await callRaw("plot", { series: [CATTLE], bands: [{ series: 3, points: [["2024-01", 1, 2]] }] });
  assert.ok(off.isError && /refers to series 3/.test(off.content[0].text));
});

const decodeSpec = (url) => JSON.parse(Buffer.from(url.split("#")[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString());

await check("forecast and local_projections return chart links with their bands", async () => {
  const f = await call("forecast", { series: { ...CPI, start: "2015-01" }, horizon: 6, method: "holt" });
  const spec = decodeSpec(f.chart_url);
  assert.equal(spec.series.length, 2);
  assert.deepEqual(spec.series[0], { ...CPI, start: "2015-01" }, "the actual series stays a live reference");
  assert.equal(spec.series[1].points.length, 7, "last actual plus six forecasts");
  assert.deepEqual(spec.series[1].points[0], f.last_actual, "the forecast line starts at the last actual");
  assert.equal(spec.bands[0].series, 1);
  assert.equal(spec.bands[0].points.length, 7);
  const [, lo, hi] = spec.bands[0].points[0]; assert.equal(lo, hi, "band starts at zero width");
  assert.equal(spec.bands[0].points[6][1], f.forecast[5].lo95); assert.equal(spec.bands[0].points[6][2], f.forecast[5].hi95);
  assert.equal(spec.api, base);
  const lp = await call("local_projections", { y: { ...CATTLE, transform: "pct_change", start: "1995-01" }, x: { ...CORN, transform: "pct_change", start: "1995-01" }, horizon: 12 });
  const ls = decodeSpec(lp.chart_url);
  assert.equal(ls.xaxis, "number");
  assert.equal(ls.series[0].points.length, 13);
  assert.deepEqual(ls.series[0].points.map((p) => p[0]), Array.from({ length: 13 }, (_, h) => String(h).padStart(2, "0")), "zero-padded horizons sort as strings");
  assert.equal(ls.bands[0].points[3][1], lp.responses[3].lo95);
  // The /v1/series endpoint the page calls resolves the inline points in order
  const r = await fetch(base + "/v1/series?s=" + encodeURIComponent(JSON.stringify({ series: ls.series })));
  const j = await r.json();
  assert.equal(j.series[0].points.length, 13);
  assert.equal(j.series[0].points[10][0], "10");
});

await check("every method that has a picture returns a chart link, and each one decodes to a drawable spec", async () => {
  const window = { start: "2000-01" };
  const cattle = { ...CATTLE, ...window }, corn = { ...CORN, ...window }, cpi = { ...CPI, ...window };
  const g = { ...CATTLE, ...window, transform: "pct_change" }, g2 = { ...CORN, ...window, transform: "pct_change" };

  const cases = [
    ["describe_stats", { series: cattle }, ["chart_url"]],
    ["regress", { y: cattle, x: [corn] }, ["chart_url", "residual_chart_url", "scatter_chart_url"]],
    ["cointegration", { a: { ...cattle, transform: "log" }, b: { ...corn, transform: "log" } }, ["chart_url", "scatter_chart_url"]],
    ["cross_correlation", { a: g, b: g2, max_lag: 6 }, ["chart_url"]],
    ["hp_filter", { series: cattle, include_points: false }, ["chart_url", "cycle_chart_url"]],
    ["decompose", { series: cattle }, ["chart_url", "components_chart_url", "seasonal_shape_chart_url"]],
    ["structural_break", { y: cattle }, ["chart_url", "segments_chart_url"]],
    ["structural_break", { y: cattle, date: "2020-01" }, ["chart_url"]],
    ["rolling", { series: g, window: 24, stat: "sd" }, ["chart_url"]],
    ["volatility", { series: g }, ["chart_url"]],
    ["quantile_regress", { y: cattle, x: [corn] }, ["chart_url"]],
    ["principal_components", { series: [g, g2] }, ["chart_url", "scree_chart_url"]],
    ["deflate", { nominal: cattle, deflator: cpi }, ["chart_url"]],
    ["iv_regress", { y: g, x: [g2], instruments: [{ ...CPI, ...window, transform: "pct_change" }] }, ["chart_url"]],
    ["forecast_evaluate", { series: cpi, horizon: 3, origins: 8, methods: ["naive", "drift"] }, ["chart_url"]],
    ["vecm", { series: [{ ...cattle, transform: "log" }, { ...corn, transform: "log" }], rank: 1 }, ["chart_url"]],
    ["johansen", { series: [{ ...cattle, transform: "log" }, { ...corn, transform: "log" }] }, ["chart_url"]],
  ];
  for (const [tool, args, keys] of cases) {
    const out = await call(tool, args);
    for (const k of keys) {
      assert.ok(typeof out[k] === "string" && out[k].includes("/chart.html#"), `${tool}: ${k} missing`);
      const spec = decodeSpec(out[k]);
      assert.ok(spec.series.length >= 1 && spec.series.length <= 8, `${tool}: ${k} has ${spec.series.length} series`);
      for (const ser of spec.series) {
        if (!ser.points) continue;
        assert.ok(ser.points.length >= 2 && ser.points.length <= 400, `${tool}: ${k} has ${ser.points.length} points`);
        for (const [x, v] of ser.points) assert.ok(typeof x === "string" && Number.isFinite(v), `${tool}: ${k} has a non-finite point`);
      }
      for (const b of spec.bands ?? []) {
        assert.ok(spec.series[b.series], `${tool}: ${k} band points past the series list`);
        for (const [, lo, hi] of b.points) assert.ok(Number.isFinite(lo) && Number.isFinite(hi) && hi >= lo, `${tool}: ${k} band is not an interval`);
      }
      assert.equal(spec.api, base);
    }
  }
  // A scatter marks which series is drawn as points, and the fitted line spans the data
  const reg = await call("regress", { y: cattle, x: [corn] });
  const sc = decodeSpec(reg.scatter_chart_url);
  assert.deepEqual(sc.dots, [0]);
  assert.equal(sc.xaxis, "number");
  assert.equal(sc.series[1].points.length, 2, "the fitted line is two ends");
  // Impulse responses come back one chart per shock, each with a band per response
  const v = await call("var_model", { series: [g, g2], horizon: 8, bootstrap: 50 });
  assert.equal(v.impulse_response_charts.length, v.shocks.length);
  const irf = decodeSpec(v.impulse_response_charts[0].chart_url);
  assert.equal(irf.xaxis, "number");
  assert.equal(irf.series.length, 2);
  assert.equal(irf.series[0].points.length, 9, "h = 0..8");
  assert.equal(irf.bands.length, 2);
  // A long series is thinned to a link a browser can carry, first and last kept
  const long = await call("hp_filter", { series: { ...CATTLE, start: "1960-01" }, include_points: false });
  const hp = decodeSpec(long.chart_url);
  const pts = hp.series[1].points;
  assert.ok(pts.length <= 400);
  assert.equal(pts[0][0].slice(0, 4), "1960");
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

await check("volatility, quantile_regress and principal_components run on the price data", async () => {
  const v = await call("volatility", { series: { ...CATTLE, transform: "pct_change", start: "1990-01" }, last_n: 12 });
  assert.ok(typeof v.garch.persistence === "number" && v.conditional_sd.length === 12, JSON.stringify(v).slice(0, 200));
  const q = await call("quantile_regress", { y: { ...CATTLE, transform: "yoy", start: "1990-01" }, x: [{ ...CORN, transform: "yoy", start: "1990-01" }] });
  assert.equal(q.by_quantile.length, 5);
  // Quantiles passed high-to-low must still report the low tail as the low tail.
  const desc = await call("quantile_regress", { y: { ...CATTLE, transform: "yoy", start: "1990-01" }, x: [{ ...CORN, transform: "yoy", start: "1990-01" }], quantiles: [0.9, 0.5, 0.1, 0.9] });
  assert.deepEqual(desc.quantiles, [0.1, 0.5, 0.9], "sorted and de-duplicated");
  assert.deepEqual(desc.by_quantile.map((r) => r.quantile), [0.1, 0.5, 0.9]);
  const sp = desc.slope_across_quantiles[0];
  assert.equal(sp.low_quantile, desc.by_quantile[0].coefficients[sp.x], "low tail is q=0.1");
  assert.equal(sp.high_quantile, desc.by_quantile[2].coefficients[sp.x], "high tail is q=0.9");
  assert.ok(Math.abs(sp.tail_asymmetry - (sp.high_quantile - sp.low_quantile)) < 1e-6, "asymmetry signed high minus low");
  const p = await call("principal_components", { series: [{ ...CATTLE, transform: "yoy", start: "1990-01" }, { ...CORN, transform: "yoy", start: "1990-01" }, { ...CPI, transform: "yoy", start: "1990-01" }], last_n: 6 });
  assert.equal(p.explained_variance.length, 3);
  assert.ok(p.scores[0].points.length === 6);
});

await check("panel_regress on asia-wdi: fixed effects across countries, and a helpful error for a bad indicator", async () => {
  const j = await call("panel_regress", { dataset: "asia-wdi", y: "gdp_growth", x: ["gross_capital_formation_pct_gdp"], effects: "unit" });
  assert.ok(j.sample.units >= 8, `only ${j.sample.units} units`);
  assert.equal(j.estimate.coefficients.length, 1);
  assert.ok(typeof j.estimate.coefficients[0].se === "number");
  assert.ok(j.pooled.coefficients.length === 2, "pooled carries a constant");
  assert.ok(j.reading.length > 20);
  assert.match(j.f_test_unit_effects.tests, /country effects/, "one-way names what it tests");
  assert.equal(j.f_test_unit_effects.df[0], j.sample.units - 1);
  assert.equal(typeof j.f_test_unit_effects.effects_matter, "boolean");
  const bad = await callRaw("panel_regress", { dataset: "asia-wdi", y: "not_an_indicator", x: ["gdp_growth"] });
  assert.ok(bad.isError && /Indicators available/.test(bad.content[0].text));

  // GDP in billions gives a pooled slope of -3e-5: it rounds to 0.0000 for display, but it is
  // the same sign as the within slope, so this is not a Simpson's paradox and must not be sold as one.
  const tiny = await call("panel_regress", { dataset: "asia-wdi", y: "gdp_growth", x: ["gdp_usd_bn"], effects: "unit" });
  const cmp = tiny.comparison_of_slopes[0];
  assert.equal(cmp.pooled, 0, "pooled slope rounds to zero for display");
  assert.ok(cmp.within < 0, `within ${cmp.within}`);
  assert.equal(cmp.sign_flips_between_within_and_pooled, false, "rounded zero is not a sign change");
  assert.ok(!/Simpson/.test(tiny.reading), tiny.reading);

  // Two-way effects: the F test and the reading both have to say year effects are in there.
  const two = await call("panel_regress", { dataset: "asia-wdi", y: "gdp_growth", x: ["gross_capital_formation_pct_gdp"], effects: "unit_time" });
  assert.match(two.f_test_unit_effects.tests, /year/, "two-way names the year effects");
  assert.equal(two.f_test_unit_effects.df[0], (two.sample.units - 1) + (two.sample.periods - 1));
  if (two.f_test_unit_effects.effects_matter) assert.match(two.reading, /Country and year effects/);
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
  const j = await call("var_model", { series: [{ ...CORN, transform: "pct_change", start: "1995-01" }, { ...CATTLE, transform: "pct_change", start: "1995-01" }], horizon: 6, bootstrap: 60 });
  assert.ok(j.lags >= 1);
  assert.equal(j.identification, "cholesky");
  assert.equal(j.impulse_responses.horizons.length, 7);
  assert.equal(j.granger_block_tests.length, 2);
  assert.equal(j.warnings.length, 0, JSON.stringify(j.warnings));
  const fevd = j.variance_decomposition_at_horizon;
  const row = Object.values(fevd)[0];
  assert.ok(Math.abs(Object.values(row).reduce((a, b) => a + b, 0) - 1) < 0.01);
  assert.equal(j.response_bands.horizons.length, 7);
  const sh = j.shocks; assert.equal(sh.length, 2);
  const h0 = j.response_bands.horizons[0];
  assert.ok(h0.lo16[j.series[0].label][sh[0]] <= h0.hi84[j.series[0].label][sh[0]], "band ordered");
  assert.ok(Array.isArray(j.significant_at_68pct));
  assert.equal(j.impact_matrix.matrix[j.series[0].label][sh[1]], 0, "Cholesky: first series does not respond to the second shock on impact");
  assert.equal(j.long_run_effects, null);
});

await check("var_model with long-run and sign identification", async () => {
  const S2 = [{ ...CATTLE, transform: "pct_change", start: "1995-01" }, { ...CORN, transform: "pct_change", start: "1995-01" }];
  const lr = await call("var_model", { series: S2, horizon: 8, identification: "long_run", bootstrap: 40, shock_names: ["permanent", "transitory"] });
  assert.deepEqual(lr.shocks, ["permanent", "transitory"]);
  assert.equal(lr.long_run_effects.matrix[lr.series[0].label].transitory, 0, "shock 2 has no long-run effect on series 1");
  assert.ok(typeof lr.impact_matrix.matrix[lr.series[0].label].permanent === "number");
  assert.equal(lr.response_bands.horizons.length, 9);
  assert.ok("cumulative_responses_at_horizon" in lr);
  assert.match(lr.caveat, /Long-run restrictions/);
  const sg = await call("var_model", { series: S2, horizon: 6, identification: "sign", sign_restrictions: [{ shock: 0, variable: 0, sign: "+" }, { shock: 0, variable: 1, sign: "+", horizons: [0, 1] }, { shock: 1, variable: 1, sign: "-" }] });
  assert.ok(sg.sign_identification.accepted_draws > 0, JSON.stringify(sg.sign_identification));
  assert.equal(sg.sign_identification.restrictions.length, 3);
  const r0 = sg.impulse_responses.horizons[0].response;
  assert.ok(r0[sg.series[0].label][sg.shocks[0]] > 0 && r0[sg.series[1].label][sg.shocks[0]] > 0 && r0[sg.series[1].label][sg.shocks[1]] < 0, "median responses obey the restrictions");
  assert.ok(sg.response_bands.horizons[0].lo[sg.series[0].label][sg.shocks[0]] <= r0[sg.series[0].label][sg.shocks[0]]);
  const none = await callRaw("var_model", { series: S2, identification: "sign" });
  assert.ok(none.isError && /needs sign_restrictions/.test(none.content[0].text));
  const impossible = await callRaw("var_model", { series: S2, identification: "sign", sign_restrictions: [{ shock: 0, variable: 0, sign: "+" }, { shock: 0, variable: 0, sign: "-" }] });
  assert.ok(impossible.isError && /No draw/.test(impossible.content[0].text));
  const bad = await callRaw("var_model", { series: S2, identification: "sign", sign_restrictions: [{ shock: 3, variable: 0, sign: "+" }] });
  assert.ok(bad.isError && /only 2 series/.test(bad.content[0].text));
});

await check("johansen and vecm with a restricted trend report the trend coefficient", async () => {
  const j = await call("johansen", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], lags: 2, deterministic: "restricted_trend" });
  assert.equal(j.trace_tests[0].critical["5%"], 25.8721);
  assert.match(j.drift_check.note, /Drift check/);
  if (j.cointegrating_vector) assert.ok("trend" in j.cointegrating_vector);
  const v = await call("vecm", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], lags: 2, rank: 1, deterministic: "restricted_trend" });
  assert.ok("trend" in v.relations[0].long_run_vector);
  assert.match(v.relations[0].equation, /× t \+ constant/);
  assert.match(v.caveat, /linear trend sits inside/);
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

await check("forecast_evaluate ranks methods out of sample, tests the winner against naive, and points at forecast", async () => {
  const j = await call("forecast_evaluate", { series: { ...CPI, start: "2005-01" }, horizon: 3, origins: 8 });
  assert.equal(j.origins.count, 8);
  assert.match(j.origins.training_window, /expanding/);
  const long = await call("forecast_evaluate", { series: CPI, horizon: 2, origins: 6, methods: ["naive", "holt"], max_train: 120 });
  assert.match(long.origins.training_window, /rolling, last 120/);
  // A deterministic series: drift is exact, naive is not, and the reading must not claim a 5% test result.
  const line = Array.from({ length: 80 }, (_, i) => [`${2000 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}`, 10 + i]);
  const det = await call("forecast_evaluate", { series: { points: line, label: "line" }, horizon: 2, origins: 6, methods: ["naive", "drift"] });
  assert.equal(det.ranking[0].method, "drift");
  assert.match(det.reading, /same margin at every origin/);
  assert.doesNotMatch(det.reading, /real at 5%/);
  assert.ok(j.ranking.length >= 6, JSON.stringify(j.ranking.map((r) => r.method)));
  for (let i = 1; i < j.ranking.length; i++) assert.ok(j.ranking[i].rmse >= j.ranking[i - 1].rmse, "sorted by RMSE");
  assert.equal(j.ranking[0].rank, 1);
  assert.equal(j.ranking[0].by_horizon.length, 3);
  const naive = j.ranking.find((r) => r.method === "naive");
  assert.equal(naive.skill_vs_naive, 0);
  assert.ok(j.arima_order && j.arima_order.order.length === 3, "ARIMA order chosen once");
  if (j.ranking[0].method !== "naive") {
    const t = j.diebold_mariano[`${j.ranking[0].method}_vs_naive`];
    assert.ok(Array.isArray(t) && t.length === 2 && t[0].horizon === 1 && t[1].horizon === 3, JSON.stringify(t));
  }
  assert.match(j.reading, /lowest 3-step RMSE/);
  // A subset of methods, and a series too short for the horizon
  const sub = await call("forecast_evaluate", { series: { ...CPI, start: "2015-01" }, horizon: 1, origins: 6, methods: ["naive", "drift"] });
  assert.deepEqual(sub.ranking.map((r) => r.method).sort(), ["drift", "naive"]);
  assert.equal(Object.keys(sub.diebold_mariano).length, 1, "runner-up naive is not tested twice");
  assert.equal(sub.diebold_mariano[Object.keys(sub.diebold_mariano)[0]].length, 1, "one horizon, one test");
  // Too few origins for the test: say so, do not call it a tie.
  const few = await call("forecast_evaluate", { series: { ...CPI, start: "2015-01" }, horizon: 1, origins: 4, methods: ["naive", "ar"], ar_order: 3 });
  if (few.ranking[0].method === "ar") {
    assert.match(few.reading, /Too few origins/);
    assert.equal(few.recommended_call.args.ar_order, 3, "the scored order is the recommended one");
  }
  assert.match(few.diebold_mariano[Object.keys(few.diebold_mariano)[0]][0].verdict, /^not tested/);
  const short = await callRaw("forecast_evaluate", { series: { ...CPI, start: "2023-01" }, horizon: 12 });
  assert.ok(short.isError && /need at least/.test(short.content[0].text), short.content[0].text);
});

await check("local_projections on corn and cattle growth returns a band per horizon and a cumulative response", async () => {
  const j = await call("local_projections", { y: { ...CATTLE, transform: "pct_change", start: "1995-01" }, x: { ...CORN, transform: "pct_change", start: "1995-01" }, horizon: 6 });
  assert.equal(j.responses.length, 7);
  assert.equal(j.lags, 4);
  assert.equal(j.responses[0].h, 0);
  for (const r of j.responses) { assert.ok(r.lo95 <= r.response && r.response <= r.hi95, `band at h=${r.h}`); assert.ok(r.lo90 >= r.lo95); }
  assert.ok(Math.abs(j.responses[6].cumulative - j.responses.reduce((a, r) => a + r.response, 0)) < 1e-3, "cumulative is the running sum");
  assert.ok(j.shock_sd > 0);
  assert.equal(j.cumulative_at_horizon, j.responses[6].cumulative);
  assert.equal(j.warnings.length, 0, JSON.stringify(j.warnings));
  const lev = await call("local_projections", { y: { ...CATTLE, start: "1995-01" }, x: { ...CORN, start: "1995-01" }, horizon: 2, lags: 2 });
  assert.ok(lev.warnings.length >= 1, "levels get a non-stationarity warning");
  const ctl = await call("local_projections", { y: { ...CATTLE, transform: "pct_change", start: "1995-01" }, x: { ...CORN, transform: "pct_change", start: "1995-01" }, controls: [{ ...CPI, transform: "pct_change", start: "1995-01" }], horizon: 3 });
  assert.equal(ctl.controls.length, 1);
});

await check("suggest_analysis routes to forecast_evaluate before forecast, and to local_projections next to var_model", async () => {
  const one = await call("suggest_analysis", { series: [{ ...CPI, start: "2000-01" }] });
  const tools = one.plan.map((p) => p.tool);
  assert.ok(tools.indexOf("forecast_evaluate") >= 0 && tools.indexOf("forecast_evaluate") < tools.indexOf("forecast"), tools.join(","));
  const two = await call("suggest_analysis", { series: [CATTLE, CORN] });
  const t2 = two.plan.map((p) => p.tool);
  assert.ok(t2.indexOf("local_projections") > t2.indexOf("var_model"), t2.join(","));
});

await check("iv_regress: 2SLS next to OLS with first-stage, Wu-Hausman and Sargan, and clean errors", async () => {
  // Cattle growth on corn growth, corn's own lag as the instrument: a timing instrument, fine for the plumbing.
  const g = (ref) => ({ ...ref, transform: "pct_change", start: "1995-01" });
  const corn = await call("get_series", { ...CORN, transform: "pct_change", start: "1994-12" });
  const lagged = corn.points.slice(0, -1).map((p, i) => [corn.points[i + 1][0], p[1]]);
  const j = await call("iv_regress", { y: g(CATTLE), x: [g(CORN)], instruments: [{ points: lagged, label: "corn lag" }] });
  assert.equal(j.identification, "just identified");
  assert.equal(j.coefficients.length, 2);
  assert.ok(typeof j.coefficients[1].coef_2sls === "number" && typeof j.coefficients[1].coef_ols === "number");
  assert.equal(j.first_stage.length, 1); assert.ok(typeof j.first_stage[0].F_excluded_instruments === "number");
  assert.ok(typeof j.wu_hausman.p === "number"); assert.equal(j.sargan, null);
  assert.equal(j.warnings.length, 0, JSON.stringify(j.warnings));
  const over = await call("iv_regress", { y: g(CATTLE), x: [g(CORN)], instruments: [{ points: lagged, label: "corn lag" }, g(CPI)], exog: [{ ...CPI, transform: "yoy", start: "1995-01" }] });
  assert.match(over.identification, /over-identified/);
  assert.ok(over.sargan && over.sargan.df === 1);
  assert.equal(over.coefficients.length, 3);
  const under = await callRaw("iv_regress", { y: g(CATTLE), x: [g(CORN), g(CPI)], instruments: [{ points: lagged, label: "corn lag" }] });
  assert.ok(under.isError && /Under-identified/.test(under.content[0].text), under.content[0].text);
  const lev = await call("iv_regress", { y: { ...CATTLE, start: "1995-01" }, x: [{ ...CORN, start: "1995-01" }], instruments: [{ ...CPI, start: "1995-01" }] });
  assert.ok(lev.warnings.length >= 1, "levels get the spurious warning");
  const self = await callRaw("iv_regress", { y: g(CATTLE), x: [g(CORN)], instruments: [g(CORN)] });
  assert.ok(self.isError && /reproduce/.test(self.content[0].text), "x as its own instrument is refused");
  const plan = await call("suggest_analysis", { series: [CATTLE, CORN], question: "does corn drive cattle prices?" });
  assert.ok(plan.pitfalls.some((p) => /iv_regress/.test(p)), "causal question points at iv_regress");
});

await check("structural_break judges the scan against sup-F critical values and finds several breaks on request", async () => {
  const j = await call("structural_break", { y: { ...CATTLE, transform: "yoy", start: "1990-01" } });
  assert.ok(j.sup_F_critical["5%"] > j.sup_F_critical["10%"] && j.sup_F_critical["1%"] > j.sup_F_critical["5%"]);
  assert.ok(["1%", "5%", "10%", null].includes(j.reject_no_break_at));
  assert.match(j.verdict, /break/i);
  // A series with two obvious level shifts
  const pts = Array.from({ length: 150 }, (_, i) => [`${1990 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}`, Math.sin(i) * 0.3 + (i >= 50 ? 3 : 0) + (i >= 100 ? -4 : 0)]);
  const m = await call("structural_break", { y: { points: pts, label: "steps" }, max_breaks: 4 });
  assert.equal(m.multiple_breaks.breaks.length, 2, JSON.stringify(m.multiple_breaks));
  assert.deepEqual(m.multiple_breaks.breaks.map((b) => b.date), ["1994-03", "1998-05"]);
  assert.equal(m.multiple_breaks.segments.length, 3);
  assert.ok(Math.abs(m.multiple_breaks.segments[1].mean_y - m.multiple_breaks.segments[0].mean_y - 3) < 0.3);
  assert.match(m.verdict, /Sequential search: 2 break/);
  const rel = await call("structural_break", { y: { ...CATTLE, transform: "pct_change", start: "1990-01" }, x: { ...CORN, transform: "pct_change", start: "1990-01" }, max_breaks: 2 });
  assert.ok(rel.multiple_breaks.segments.every((sg) => "slope" in sg), "relation breaks report slopes per segment");
});

await check("regress reports Breusch-Pagan, VIF and RESET diagnostics", async () => {
  const j = await call("regress", { y: { ...CATTLE, transform: "yoy", start: "1990-01" }, x: [{ ...CORN, transform: "yoy", start: "1990-01" }, { ...CPI, transform: "yoy", start: "1990-01" }] });
  assert.ok(typeof j.diagnostics.breusch_pagan.p === "number" && j.diagnostics.breusch_pagan.df === 2);
  assert.equal(j.diagnostics.vif.length, 2);
  assert.ok(j.diagnostics.vif.every((v) => v.vif >= 1));
  assert.ok(j.diagnostics.reset && typeof j.diagnostics.reset.p === "number");
  // A regressor entered twice via lags of a smooth series should push VIF up and be warned about
  const lagged = await call("regress", { y: { ...CATTLE, transform: "yoy", start: "1990-01" }, x: [{ ...CPI, start: "1990-01" }], x_lags: 2 });
  assert.ok(lagged.diagnostics.vif.some((v) => v.vif > 10), JSON.stringify(lagged.diagnostics.vif));
  assert.ok(lagged.warnings.some((w) => /VIF above 10/.test(w)), lagged.warnings.join(" | "));
});

await check("johansen and vecm with a restricted constant report the constant in the vector and a drift check", async () => {
  const j = await call("johansen", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], lags: 2, deterministic: "restricted_constant" });
  assert.equal(j.deterministic, "restricted_constant");
  assert.equal(j.trace_tests[0].critical["5%"], 20.2618);
  assert.equal(j.drift_check.per_series.length, 2);
  assert.ok(["constant", "restricted_constant"].includes(j.drift_check.suggested));
  if (j.cointegrating_vector) assert.ok("constant" in j.cointegrating_vector);
  const v = await call("vecm", { series: [{ ...CATTLE, transform: "log", start: "1990-01" }, { ...CORN, transform: "log", start: "1990-01" }], lags: 2, rank: 1, deterministic: "restricted_constant" });
  assert.ok("constant" in v.relations[0].long_run_vector);
  assert.match(v.caveat, /restricted to the cointegrating relation/);
  // Two drift-free inline series: suggest_analysis picks the restricted constant
  const n = 200, a = [0], b = [];
  let seed = 9; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 - 0.5; };
  for (let i = 1; i < n; i++) a.push(a[i - 1] + rnd());
  for (let i = 0; i < n; i++) b.push(3 + a[i] + rnd() * 0.3);
  const dt = (i) => `${1990 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}`;
  const plan = await call("suggest_analysis", { series: [{ points: a.map((v, i) => [dt(i), v]), label: "a" }, { points: b.map((v, i) => [dt(i), v]), label: "b" }] });
  assert.ok(plan.series.every((f) => f.integration_order === "I(1)"), JSON.stringify(plan.series.map((f) => f.integration_order)));
  const jo = plan.plan.find((p) => p.tool === "vecm");
  assert.equal(jo.args.deterministic, "restricted_constant", "drift-free walks get the restricted constant");
  assert.ok(plan.pitfalls.some((p) => /restricted_constant/.test(p)));
  // The same walks with a drift added: the unrestricted constant
  const plan2 = await call("suggest_analysis", { series: [{ points: a.map((v, i) => [dt(i), v + 0.5 * i]), label: "a" }, { points: b.map((v, i) => [dt(i), v + 0.5 * i]), label: "b" }] });
  const jo2 = plan2.plan.find((p) => p.tool === "vecm");
  if (jo2) assert.equal(jo2.args.deterministic, "constant", "drifting walks get the unrestricted constant");
});

await check("sec: a company balance sheet by quarter, restatements resolved, tickers and CIKs both work", async () => {
  // First, before anything caches the directory: when the SEC refuses the caller, say so.
  // Reporting it as an unknown company would send the reader hunting for a valid ticker.
  setSecBlocked(true);
  const blocked = await callRaw("fetch_external", { provider: "sec", id: "AAPL:Assets" });
  assert.ok(blocked.isError, blocked.content[0].text);
  const said = blocked.content[0].text;
  assert.match(said, /refused its ticker directory/, said);
  assert.match(said, /403/, "the status the SEC gave");
  assert.match(said, /Undeclared Automated Tool/, "the words off the SEC's own page, not the markup around them");
  assert.match(said, /SEC_USER_AGENT/, "and what to do about it");
  setSecBlocked(false);
  const bs = await call("fetch_external", { provider: "sec", id: "AAPL:balance_sheet" });
  // Only the tags this filer actually reports come back; the rest of the statement is absent, not empty.
  assert.deepEqual(bs.series.map((x) => x.key), ["Assets", "StockholdersEquity"], JSON.stringify(bs.series));
  assert.equal(bs.series[0].first, "2023-Q1");
  assert.match(bs.source, /Apple Inc\./);
  assert.match(bs.source, /CIK 0000320193/);
  const assets = await call("fetch_external", { provider: "sec", id: "AAPL:Assets" });
  // The SEC's own calendar frame labels the quarter, so odd fiscal years stay comparable.
  assert.deepEqual(assets.points, [["2023-Q1", 332160000000], ["2023-Q2", 335038000000], ["2023-Q3", 352583000000], ["2023-Q4", 353514000000]]);
  assert.equal(assets.points[2][1], 352583000000, "the later filing wins over the first print of the same period");
  // Flows keep the quarterly duration by default, and the fiscal year on request
  const ni = await call("fetch_external", { provider: "sec", id: "AAPL:NetIncomeLoss" });
  assert.deepEqual(ni.points, [["2023-Q1", 24160000000], ["2023-Q2", 19881000000], ["2023-Q3", 22956000000]], "the twelve-month row is not a quarter");
  const niY = await call("fetch_external", { provider: "sec", id: "AAPL:NetIncomeLoss", params: { annual: "true" } });
  assert.deepEqual(niY.points, [["2023", 96995000000]]);
  // A CIK works as well as a ticker
  const byCik = await call("fetch_external", { provider: "sec", id: "CIK0000320193:Assets" });
  assert.equal(byCik.points.length, 4);
  assert.ok(byCik.caveats.some((c) => /restated/.test(c)), JSON.stringify(byCik.caveats));
  // Clear errors for a bad ticker, a bad tag and a malformed id
  for (const [args, re] of [
    [{ provider: "sec", id: "NOPE:Assets" }, /No SEC filer with ticker/],
    [{ provider: "sec", id: "AAPL:NotATag" }, /no us-gaap tag/],

    [{ provider: "sec", id: "AAPL" }, /TICKER:TAG/],
  ]) {
    const r = await callRaw("fetch_external", args);
    assert.ok(r.isError && re.test(r.content[0].text), JSON.stringify(args) + " -> " + r.content[0].text);
  }
  // list_providers must report the contact state, and it can only do that if the variable
  // reaches the provider at all: a plumbing gap here makes the documented remedy useless.
  const provs = await call("list_providers", {});
  const secp = provs.providers.find((p) => p.provider === "sec");
  assert.match(String(secp.needs_key), /SEC_USER_AGENT/);
  assert.match(String(secp.key_present), /yes/, "the worker passes SEC_USER_AGENT through to the provider");
  const found = await call("search_external", { provider: "sec", query: "balance sheet" });
  assert.ok(found.matches.length, JSON.stringify(found));
  // A bare ticker with no curated match still offers that filer's three statements
  const byName = await call("search_external", { provider: "sec", query: "IBM" });
  assert.deepEqual(byName.matches.map((m) => m.id), ["IBM:balance_sheet", "IBM:income_statement", "IBM:cash_flow"], JSON.stringify(byName.matches));
});

await check("weather: named regions and lat,lon, monthly aggregation, sums for rain and means for temperature", async () => {
  const j = await call("fetch_external", { provider: "weather", id: "us-corn-belt+tr-konya", params: { start: "2024-06", end: "2024-07" } });
  assert.equal(j.series_count, 4, JSON.stringify(Object.keys(j.series || {})));
  const corn = await call("fetch_external", { provider: "weather", id: "us-corn-belt+tr-konya", params: { start: "2024-06", end: "2024-07" }, series: "us-corn-belt.precipitation_sum" });
  // June has two days in the fixture (4 + 6 mm), July one (1.5 mm): rainfall is summed.
  assert.deepEqual(corn.points, [["2024-06", 10], ["2024-07", 1.5]]);
  const temp = await call("fetch_external", { provider: "weather", id: "us-corn-belt+tr-konya", params: { start: "2024-06", end: "2024-07" }, series: "us-corn-belt.temperature_2m_mean" });
  // Temperature is averaged, not summed.
  assert.deepEqual(temp.points, [["2024-06", 23], ["2024-07", 25]]);
  // A null day is skipped rather than counted as zero.
  const konya = await call("fetch_external", { provider: "weather", id: "us-corn-belt+tr-konya", params: { start: "2024-06", end: "2024-07" }, series: "tr-konya.precipitation_sum" });
  assert.deepEqual(konya.points, [["2024-06", 0], ["2024-07", 2.5]]);
  assert.match(j.source, /ERA5/);
  assert.ok(j.notes.some((c) => /reanalysis/.test(c)), JSON.stringify(j.notes));
  assert.ok(corn.caveats.some((c) => /reanalysis/.test(c)), JSON.stringify(corn.caveats));
  // Annual and daily aggregation, and a bare coordinate pair
  const annual = await call("fetch_external", { provider: "weather", id: "41.6,-93.6", params: { start: "2024", end: "2024", aggregate: "annual" }, series: "41.6,-93.6.precipitation_sum" });
  assert.deepEqual(annual.points, [["2024", 11.5]]);
  const daily = await call("fetch_external", { provider: "weather", id: "us-corn-belt", params: { aggregate: "daily" }, series: "us-corn-belt.temperature_2m_mean" });
  assert.equal(daily.points.length, 3);
  // Clear errors for a bad place, a bad aggregate and too many locations
  for (const [args, re] of [
    [{ provider: "weather", id: "narnia" }, /Unknown weather location/],
    [{ provider: "weather", id: "us-corn-belt", params: { aggregate: "hourly" } }, /aggregate must be/],
    [{ provider: "weather", id: "999,999" }, /Latitude must be/],
  ]) {
    const r = await callRaw("fetch_external", args);
    assert.ok(r.isError && re.test(r.content[0].text), JSON.stringify(args) + " -> " + r.content[0].text);
  }
  const s = await call("search_external", { provider: "weather", query: "konya" });
  assert.ok(s.matches.some((m) => m.id === "tr-konya"), JSON.stringify(s.matches));
  // It plugs into the analysis layer like any other series
  const st = await call("describe_stats", { series: { provider: "weather", id: "us-corn-belt", params: { aggregate: "daily" }, series: "us-corn-belt.temperature_2m_mean" } });
  assert.equal(st.n, 3);
});

await check("/v1/analyze runs the same tools over plain HTTP, no MCP client", async () => {
  // The catalogue of what is callable
  const list = await (await fetch(base + "/v1/analyze")).json();
  assert.ok(list.tools.length > 20, list.tools.length + " tools");
  assert.ok(list.tools.some((t) => t.name === "forecast" && t.description), JSON.stringify(list.tools.slice(0, 2)));

  // A forecast, by POST
  const r = await fetch(base + "/v1/analyze", { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ tool: "forecast", args: { series: { dataset: "us-prices", series: "cpi", start: "2015-01" }, horizon: 4, method: "holt" } }) });
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.equal(j.tool, "forecast");
  assert.equal(j.result.forecast.length, 4);
  assert.ok(j.result.chart_url && j.result.source, "carries the chart link and the source");

  // A structural break, by GET
  const g = await fetch(base + "/v1/analyze?tool=structural_break&args=" + encodeURIComponent(JSON.stringify({ y: { dataset: "us-prices", series: "cattle_ppi", transform: "yoy", start: "1990-01" }, max_breaks: 2 })));
  const gj = await g.json();
  assert.equal(g.status, 200);
  assert.ok(gj.result.verdict && gj.result.sup_F_critical, JSON.stringify(gj).slice(0, 200));

  // Errors are reported, not thrown
  const bad = await fetch(base + "/v1/analyze?tool=nope");
  assert.equal(bad.status, 404);
  assert.ok((await bad.json()).tools.length > 0);
  const badArgs = await fetch(base + "/v1/analyze?tool=forecast&args=" + encodeURIComponent(JSON.stringify({ horizon: 4 })));
  assert.equal(badArgs.status, 400);
  assert.ok((await badArgs.json()).issues.length, "says which argument is wrong");
  const badSeries = await fetch(base + "/v1/analyze", { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ tool: "forecast", args: { series: { dataset: "us-prices", series: "nope" } } }) });
  assert.equal(badSeries.status, 400);
  assert.match((await badSeries.json()).error, /No series/);
  // CORS, so a browser page on the site can call it
  assert.equal(r.headers.get("access-control-allow-origin"), "*");
});

await check("predict recommends a method, says whether it beats no-change, and forecasts with it", async () => {
  const j = await call("predict", { series: { ...CPI, start: "2005-01" }, horizon: 6, origins: 10 });
  assert.ok(j.methods.length >= 6, JSON.stringify(j.methods.map((m) => m.method)));
  for (let i = 1; i < j.methods.length; i++) assert.ok(j.methods[i].typical_error >= j.methods[i - 1].typical_error, "ranked by error");
  assert.equal(j.methods[0].rank, 1);
  assert.ok(j.methods.filter((m) => m.recommended).length === 1, "exactly one recommendation");
  assert.equal(j.methods[0].method, j.recommendation.method);
  assert.ok(j.methods.every((m) => m.what_it_does), "every method explained in words");
  assert.equal(j.used.method, j.recommendation.method);
  assert.equal(j.used.overridden, false);
  assert.equal(j.forecast.length, 6);
  assert.ok(j.forecast[5].lo95 < j.forecast[5].value && j.forecast[5].value < j.forecast[5].hi95, "band brackets the path");
  assert.ok(j.forecast[5].hi95 - j.forecast[5].lo95 > j.forecast[0].hi95 - j.forecast[0].lo95, "band widens with the horizon");
  assert.ok(j.chart_url.includes("chart.html#"), j.chart_url);
  assert.ok(j.tested.origins === 10 && j.tested.from < j.tested.to);
  assert.match(j.reading, /typical error/);
  assert.ok(typeof j.recommendation.why === "string" && j.recommendation.why.length > 20);
  // Overriding the recommendation is honoured and flagged
  const forced = await call("predict", { series: { ...CPI, start: "2005-01" }, horizon: 6, origins: 10, method: "naive" });
  assert.equal(forced.used.method, "naive");
  assert.equal(forced.used.overridden, true);
  assert.ok(forced.forecast.every((p) => p.value === forced.last_actual[1]), "naive holds the last value flat");
  assert.match(forced.reading, /You asked for assume no change/);
  // A series too short to test says so instead of guessing
  const short = await callRaw("predict", { series: { ...CPI, start: "2025-01" }, horizon: 12 });
  assert.ok(short.isError && /needs at least/.test(short.content[0].text), short.content[0].text);
  // And it is reachable over plain HTTP too
  const http = await fetch(base + "/v1/analyze", { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ tool: "predict", args: { series: { ...CATTLE, transform: "yoy", start: "1995-01" }, horizon: 3, origins: 8 } }) });
  const hj = await http.json();
  assert.equal(http.status, 200);
  assert.equal(hj.result.forecast.length, 3);
  assert.ok(hj.result.recommendation.method);
});

await client.close();
worker.close();
stat.close();
console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
