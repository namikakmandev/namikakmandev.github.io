// Run the Worker on plain Node, with the repo's own data/ directory as the origin.
// Used by the e2e test and by `npm run dev:node` when wrangler is not an option.
//
//   node test/serve-node.mjs            # MCP at http://127.0.0.1:8787/mcp
//   DATA_ORIGIN=https://namikakmandev.github.io node test/serve-node.mjs
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..");

/** Static file server over the repo root, so /data/x.json resolves like on GitHub Pages. */
export function startStatic(port = 0) {
  const srv = http.createServer((req, res) => {
    const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    const file = path.join(repoRoot, p);
    if (!file.startsWith(repoRoot) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404); res.end("not found"); return;
    }
    res.writeHead(200, { "content-type": file.endsWith(".json") ? "application/json" : "text/plain" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => srv.listen(port, "127.0.0.1", () => resolve(srv)));
}

/** Bridge Node's http to the Worker's fetch(Request, env) handler. */
export function startWorker(handler, env, port = 0) {
  const srv = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = chunks.length ? Buffer.concat(chunks) : undefined;
    const url = `http://${req.headers.host}${req.url}`;
    const request = new Request(url, {
      method: req.method,
      headers: req.headers,
      body: body && req.method !== "GET" && req.method !== "HEAD" ? body : undefined,
    });
    try {
      const out = await handler.fetch(request, env);
      const headers = {};
      out.headers.forEach((v, k) => { headers[k] = v; });
      res.writeHead(out.status, headers);
      if (out.body) {
        for await (const chunk of out.body) res.write(chunk);
      }
      res.end();
    } catch (e) {
      res.writeHead(500, { "content-type": "text/plain" });
      res.end(String(e?.stack ?? e));
    }
  });
  return new Promise((resolve) => srv.listen(port, "127.0.0.1", () => resolve(srv)));
}

export function addr(srv) {
  const a = srv.address();
  return `http://127.0.0.1:${a.port}`;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { default: handler } = await import("../dist/index.js");
  let origin = process.env.DATA_ORIGIN;
  if (!origin) origin = addr(await startStatic());
  const w = await startWorker(handler, { DATA_ORIGIN: origin, MCP_API_KEYS: process.env.MCP_API_KEYS }, Number(process.env.PORT ?? 8787));
  console.log(`econ-mcp on ${addr(w)}/mcp  (data from ${origin})`);
}
