/**
 * Cloudflare Worker entry. Streamable HTTP MCP at /mcp, stateless: a fresh
 * server and transport per request, nothing kept between calls except the
 * in-isolate data cache. Works unchanged on any Web-standard runtime.
 */
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { buildServer, SERVER_NAME, SERVER_VERSION } from "./server.js";
import { handleAnalyzeRequest, handleSeriesRequest } from "./api.js";
import { AskQuota, handleAskRequest, ASK_MODEL, PER_VISITOR_PER_DAY } from "./ask.js";

export { AskQuota };

export interface Env {
  /** Where the curated datasets live. Defaults to the portfolio site when unset. */
  DATA_ORIGIN?: string;
  /** Optional comma-separated bearer tokens. Unset = open server. */
  MCP_API_KEYS?: string;
  /** Optional. Enables FRED catalogue search; fetch works without it. */
  FRED_API_KEY?: string;
  /** Optional. Required for TCMB EVDS pulls. */
  EVDS_API_KEY?: string;
  /** Optional but effectively required for SEC pulls: the SEC refuses callers whose
   *  user agent does not name them, in the form 'Company Name admin@example.com'. */
  SEC_USER_AGENT?: string;
  /** Optional. FAOSTAT developer account (free); or a ready token. */
  FAOSTAT_USER?: string;
  FAOSTAT_PASSWORD?: string;
  FAOSTAT_API_TOKEN?: string;
  /** Optional. Switches on /v1/ask, the website's question box; the owner pays per question. */
  ANTHROPIC_API_KEY?: string;
  /** The daily question counters behind /v1/ask. Declared in wrangler.jsonc. */
  ASK_QUOTA?: DurableObjectNamespace;
}

function providerEnv(env: Env) {
  return { FRED_API_KEY: env.FRED_API_KEY, EVDS_API_KEY: env.EVDS_API_KEY, FAOSTAT_USER: env.FAOSTAT_USER, FAOSTAT_PASSWORD: env.FAOSTAT_PASSWORD, FAOSTAT_API_TOKEN: env.FAOSTAT_API_TOKEN, SEC_USER_AGENT: env.SEC_USER_AGENT };
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

const DEFAULT_ORIGIN = "https://namikakmandev.github.io";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const origin = env.DATA_ORIGIN || DEFAULT_ORIGIN;

    if (request.method === "OPTIONS") return withCors(new Response(null, { status: 204 }));

    if (url.pathname === "/" || url.pathname === "") {
      return json({
        name: SERVER_NAME,
        version: SERVER_VERSION,
        transport: "streamable-http",
        endpoint: new URL("/mcp", url).href,
        data_origin: origin,
        auth: env.MCP_API_KEYS ? "bearer" : "none",
        providers: { fred: "fetch keyless, search " + (env.FRED_API_KEY ? "enabled" : "starter list"), eurostat: "open", worldbank: "open", ecb: "open", oecd: "open", owid: "open", evds: env.EVDS_API_KEY ? "enabled" : "needs EVDS_API_KEY", bis: "open", fao: env.FAOSTAT_API_TOKEN || (env.FAOSTAT_USER && env.FAOSTAT_PASSWORD) ? "enabled" : "needs FAOSTAT_USER and FAOSTAT_PASSWORD", imf: "open", weather: "open", sec: "open" },
        http: { series: new URL("/v1/series?s=" + encodeURIComponent('{"series":[{"dataset":"us-prices","series":"cattle_ppi","start":"2020"}]}'), url).href, analyze: new URL("/v1/analyze", url).href, chart: origin + "/chart.html",
          ask: env.ANTHROPIC_API_KEY ? `${new URL("/v1/ask", url).href} (${ASK_MODEL}, ${PER_VISITOR_PER_DAY} questions per visitor per day)` : "off: no ANTHROPIC_API_KEY" },
        docs: "https://github.com/namikakmandev/namikakmandev.github.io/tree/main/mcp",
      });
    }

    if (url.pathname === "/health") return json({ ok: true });

    if (url.pathname === "/v1/series") {
      if (!authorized(request, env)) return withCors(new Response("Unauthorized", { status: 401, headers: { "www-authenticate": "Bearer" } }));
      const { status, body } = await handleSeriesRequest(request, origin, providerEnv(env));
      return json(body, status);
    }

    if (url.pathname === "/v1/analyze") {
      if (!authorized(request, env)) return withCors(new Response("Unauthorized", { status: 401, headers: { "www-authenticate": "Bearer" } }));
      const { status, body } = await handleAnalyzeRequest(request, origin, providerEnv(env), url.origin);
      return json(body, status);
    }

    if (url.pathname === "/v1/ask" || url.pathname === "/v1/ask/quota") {
      return handleAskRequest(request, env, new URL("/mcp", url).href);
    }

    if (url.pathname === "/mcp") {
      if (!authorized(request, env)) {
        return withCors(new Response("Unauthorized", { status: 401, headers: { "www-authenticate": "Bearer" } }));
      }
      const server = buildServer(origin, providerEnv(env), url.origin);
      const transport = new WebStandardStreamableHTTPServerTransport({
        sessionIdGenerator: undefined,   // stateless
        enableJsonResponse: true,
      });
      await server.connect(transport);
      const res = await transport.handleRequest(request);
      return withCors(res);
    }

    return json({ error: "not found", try: ["/", "/mcp", "/health", "/v1/series?s=...", "/v1/analyze", "/v1/ask"] }, 404);
  },
} satisfies ExportedHandler<Env>;
