/**
 * Cloudflare Worker entry. Streamable HTTP MCP at /mcp, stateless: a fresh
 * server and transport per request, nothing kept between calls except the
 * in-isolate data cache. Works unchanged on any Web-standard runtime.
 */
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { buildServer, SERVER_NAME, SERVER_VERSION } from "./server.js";

export interface Env {
  DATA_ORIGIN: string;
  /** Optional comma-separated bearer tokens. Unset = open server. */
  MCP_API_KEYS?: string;
}

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
  "access-control-allow-headers": "content-type, authorization, mcp-session-id, mcp-protocol-version, last-event-id",
  "access-control-expose-headers": "mcp-session-id, mcp-protocol-version",
};

function withCors(res: Response): Response {
  const headers = new Headers(res.headers);
  for (const [k, v] of Object.entries(CORS)) headers.set(k, v);
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}

function json(obj: unknown, status = 200): Response {
  return withCors(new Response(JSON.stringify(obj, null, 1), { status, headers: { "content-type": "application/json" } }));
}

function authorized(request: Request, env: Env): boolean {
  const keys = (env.MCP_API_KEYS ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  if (!keys.length) return true;
  const auth = request.headers.get("authorization") ?? "";
  const m = /^Bearer\s+(.+)$/i.exec(auth);
  return !!m && keys.includes(m[1].trim());
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return withCors(new Response(null, { status: 204 }));

    if (url.pathname === "/" || url.pathname === "") {
      return json({
        name: SERVER_NAME,
        version: SERVER_VERSION,
        transport: "streamable-http",
        endpoint: new URL("/mcp", url).href,
        data_origin: env.DATA_ORIGIN,
        auth: env.MCP_API_KEYS ? "bearer" : "none",
        docs: "https://github.com/namikakmandev/namikakmandev.github.io/tree/main/mcp",
      });
    }

    if (url.pathname === "/health") return json({ ok: true });

    if (url.pathname === "/mcp") {
      if (!authorized(request, env)) {
        return withCors(new Response("Unauthorized", { status: 401, headers: { "www-authenticate": "Bearer" } }));
      }
      const server = buildServer(env.DATA_ORIGIN);
      const transport = new WebStandardStreamableHTTPServerTransport({
        sessionIdGenerator: undefined,   // stateless
        enableJsonResponse: true,
      });
      await server.connect(transport);
      const res = await transport.handleRequest(request);
      return withCors(res);
    }

    return json({ error: "not found", try: ["/", "/mcp", "/health"] }, 404);
  },
} satisfies ExportedHandler<Env>;
