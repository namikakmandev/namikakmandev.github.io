// End-to-end: real MCP client over Streamable HTTP against the compiled Worker,
// with data served from the repo's own data/ directory. Run: npm test
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { startStatic, startWorker, addr } from "./serve-node.mjs";

const { default: handler } = await import("../dist/index.js");

const stat = await startStatic();
const origin = addr(stat);
const worker = await startWorker(handler, { DATA_ORIGIN: origin });
const base = addr(worker);

let failures = 0;
async function check(name, fn) {
  try { await fn(); console.log("ok   ", name); }
  catch (e) { failures++; console.log("FAIL ", name, "\n     ", e.message.split("\n")[0]); }
}
const parse = (r) => JSON.parse(r.content[0].text);

// --- plain HTTP surface -----------------------------------------------------
await check("GET / describes the server", async () => {
  const r = await fetch(base + "/");
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.equal(j.transport, "streamable-http");
  assert.equal(j.auth, "none");
});

await check("bearer auth is enforced when MCP_API_KEYS is set", async () => {
  const w2 = await startWorker(handler, { DATA_ORIGIN: origin, MCP_API_KEYS: "k1, k2" });
  const u = addr(w2) + "/mcp";
  const init = { jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "0" } } };
  const hdr = { "content-type": "application/json", accept: "application/json, text/event-stream" };
  const no = await fetch(u, { method: "POST", headers: hdr, body: JSON.stringify(init) });
  assert.equal(no.status, 401);
  const yes = await fetch(u, { method: "POST", headers: { ...hdr, authorization: "Bearer k2" }, body: JSON.stringify(init) });
  assert.equal(yes.status, 200);
  w2.close();
});

// --- MCP client --------------------------------------------------------------
const client = new Client({ name: "e2e", version: "0.0.0" });
await client.connect(new StreamableHTTPClientTransport(new URL(base + "/mcp")));

await check("tools are listed", async () => {
  const { tools } = await client.listTools();
  const names = new Set(tools.map((t) => t.name));
  for (const n of ["compare_series", "describe_dataset", "get_caveats", "get_dataset", "get_series", "list_datasets", "search_datasets"]) assert.ok(names.has(n), n);
});

await check("list_datasets returns the catalog", async () => {
  const j = parse(await client.callTool({ name: "list_datasets", arguments: {} }));
  assert.ok(j.datasets.length >= 80, `only ${j.datasets.length} datasets`);
  assert.ok(j.datasets.some((d) => d.dataset === "us-prices"));
  const pipe = parse(await client.callTool({ name: "list_datasets", arguments: { provenance: "pipeline" } }));
  assert.ok(pipe.datasets.every((d) => d.provenance === "pipeline"));
});

await check("search_datasets finds cattle parity and HICP", async () => {
  const j = parse(await client.callTool({ name: "search_datasets", arguments: { query: "cattle parity" } }));
  assert.equal(j.matches[0].dataset, "cattle-parity");
  const h = parse(await client.callTool({ name: "search_datasets", arguments: { query: "hicp" } }));
  assert.ok(h.matches.some((m) => m.dataset === "eu-hicp"));
});

await check("describe_dataset: fetch.py series shape", async () => {
  const j = parse(await client.callTool({ name: "describe_dataset", arguments: { dataset: "us-prices" } }));
  const ids = j.series.map((s) => s.id).sort();
  assert.deepEqual(ids, ["cattle_ppi", "corn_ppi", "cpi"]);
  assert.ok(j.caveats.some((c) => c.includes("index numbers")));
});

await check("describe_dataset: table shape", async () => {
  const j = parse(await client.callTool({ name: "describe_dataset", arguments: { dataset: "cattle-us" } }));
  assert.deepEqual(j.series.map((s) => s.id).sort(), ["cattle_ppi", "corn_ppi", "parity_cattle_over_corn"]);
});

await check("describe_dataset: regions of tables", async () => {
  const j = parse(await client.callTool({ name: "describe_dataset", arguments: { dataset: "cattle-parity" } }));
  const ids = j.series.map((s) => s.id);
  assert.ok(ids.includes("US.parity_idx") && ids.includes("EU.meat_idx"), ids.join(","));
});

await check("describe_dataset: nested share records", async () => {
  const j = parse(await client.callTool({ name: "describe_dataset", arguments: { dataset: "pharma-share" } }));
  const ids = j.series.map((s) => s.id);
  assert.ok(ids.includes("DE.share_gdp"), ids.slice(0, 10).join(","));
});

await check("describe_dataset: grouped eurostat keys", async () => {
  const j = parse(await client.callTool({ name: "describe_dataset", arguments: { dataset: "fx-eur" } }));
  assert.ok(j.series.some((s) => s.id === "TRY"));
});

await check("get_series window and rebase", async () => {
  const j = parse(await client.callTool({ name: "get_series", arguments: { dataset: "eu-hicp", series: "hicp", start: "2020-01", end: "2020-12", transform: "rebase" } }));
  assert.equal(j.n, 12);
  assert.equal(j.points[0][0], "2020-01");
  assert.equal(j.points[0][1], 100);
});

await check("get_series yoy has a value at the window start", async () => {
  const j = parse(await client.callTool({ name: "get_series", arguments: { dataset: "us-prices", series: "cpi", start: "2022-01", end: "2022-03", transform: "yoy" } }));
  assert.equal(j.points[0][0], "2022-01");
  assert.ok(j.points[0][1] > 5 && j.points[0][1] < 10, `Jan 2022 US CPI yoy came out as ${j.points[0][1]}`);
  assert.equal(j.unit_hint, "percent");
});

await check("get_series annual resample and last_n", async () => {
  const j = parse(await client.callTool({ name: "get_series", arguments: { dataset: "us-prices", series: "cattle_ppi", frequency: "annual_mean", last_n: 3 } }));
  assert.equal(j.n, 3);
  assert.match(j.points[0][0], /^\d{4}$/);
});

await check("get_series unknown id lists alternatives", async () => {
  const r = await client.callTool({ name: "get_series", arguments: { dataset: "us-prices", series: "nope" } });
  assert.equal(r.isError, true);
  assert.match(r.content[0].text, /cattle_ppi/);
});

await check("get_series unknown dataset is a clean error", async () => {
  const r = await client.callTool({ name: "get_series", arguments: { dataset: "does-not-exist", series: "x" } });
  assert.equal(r.isError, true);
  assert.match(r.content[0].text, /No such dataset/);
});

await check("compare_series aligns monthly with annual", async () => {
  const j = parse(await client.callTool({ name: "compare_series", arguments: {
    a: { dataset: "us-prices", series: "cattle_ppi" },
    b: { dataset: "herd-cattle", series: "US" },
    start: "2000", end: "2024", frequency: "annual_mean",
  } }));
  assert.ok(j.n >= 20, `n=${j.n}`);
  assert.equal(j.columns.length, 4);
  assert.ok(j.correlation_levels && typeof j.correlation_levels.r === "number");
  assert.ok(j.a.caveats.length > 0);
});

await check("get_caveats carries provenance", async () => {
  const j = parse(await client.callTool({ name: "get_caveats", arguments: { dataset: "us-cowcalf-costs" } }));
  assert.ok(j.caveats.some((c) => /SURVEY BASIS CHANGED/.test(c)));
  assert.equal(j.provenance, "pipeline");
});

await check("get_dataset raw with path and size guard", async () => {
  const j = parse(await client.callTool({ name: "get_dataset", arguments: { dataset: "cattle-parity", path: "regions.US.columns" } }));
  assert.deepEqual(j, ["month", "meat_idx", "feed_idx", "parity_idx"]);
  const big = await client.callTool({ name: "get_dataset", arguments: { dataset: "ecb-spf" } });
  assert.equal(big.isError, true);
  assert.match(big.content[0].text, /Narrow it with a path/);
});

await check("resources: catalog and dataset template", async () => {
  const { resources } = await client.listResources();
  assert.ok(resources.some((r) => r.uri === "econ://catalog"));
  assert.ok(resources.some((r) => r.uri === "econ://dataset/us-prices"));
  const r = await client.readResource({ uri: "econ://dataset/eu-hicp" });
  const body = JSON.parse(r.contents[0].text);
  assert.ok(body.series.hicp);
});

await check("every catalogued dataset either yields series or reads raw", async () => {
  const cat = parse(await client.callTool({ name: "list_datasets", arguments: {} }));
  const empty = [];
  for (const d of cat.datasets) {
    const j = parse(await client.callTool({ name: "describe_dataset", arguments: { dataset: d.dataset } }));
    if (!j.series_count) empty.push(d.dataset);
  }
  console.log("      no series extracted (raw only):", empty.join(", ") || "none");
  assert.ok(empty.length < cat.datasets.length / 4, `${empty.length} of ${cat.datasets.length} datasets expose no series`);
});

await client.close();
worker.close();
stat.close();
console.log(failures ? `\n${failures} failing` : "\nall passing");
process.exit(failures ? 1 : 0);
