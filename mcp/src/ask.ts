/**
 * "Ask the data": a visitor types a question on the website, this Worker asks Claude with
 * the site's own MCP tools attached, and streams the answer back. Anthropic's MCP connector
 * makes the tool calls server-side against /mcp, so nothing here runs an agent loop.
 *
 * The cost is the site owner's, so two counters bound it: questions per visitor per day
 * (by hashed IP) and questions per day for the whole site. They live in one Durable Object
 * so every isolate sees the same numbers. Past the limit the page points at the free route:
 * connect the server to your own Claude.
 */

export const ASK_MODEL = "claude-opus-5";
export const PER_VISITOR_PER_DAY = 5;
export const SITE_PER_DAY = 300;
const MAX_QUESTION_CHARS = 1000;
const MAX_HISTORY_TURNS = 6;
const MAX_TOKENS = 4000;

export interface AskEnv {
  ANTHROPIC_API_KEY?: string;
  MCP_API_KEYS?: string;
  ASK_QUOTA?: DurableObjectNamespace;
}

// ---------------------------------------------------------------------------
// Quota arithmetic, pure so it can be tested without a runtime.

export interface QuotaState { day: string; site: number; visitors: Record<string, number> }

export function emptyQuota(day: string): QuotaState { return { day, site: 0, visitors: {} }; }

/** UTC calendar day, the unit of "per day". */
export function today(now = Date.now()): string { return new Date(now).toISOString().slice(0, 10); }

export function quotaView(s: QuotaState, visitor: string) {
  const used = s.visitors[visitor] ?? 0;
  return { remaining: Math.max(0, PER_VISITOR_PER_DAY - used), site_remaining: Math.max(0, SITE_PER_DAY - s.site), per_day: PER_VISITOR_PER_DAY };
}

/** Take one question for `visitor`, or say why not. Mutates and returns the state. */
export function takeQuota(s: QuotaState, visitor: string, day: string): { ok: boolean; reason?: "visitor" | "site"; state: QuotaState } {
  if (s.day !== day) s = emptyQuota(day);
  const used = s.visitors[visitor] ?? 0;
  if (used >= PER_VISITOR_PER_DAY) return { ok: false, reason: "visitor", state: s };
  if (s.site >= SITE_PER_DAY) return { ok: false, reason: "site", state: s };
  s.visitors[visitor] = used + 1;
  s.site += 1;
  return { ok: true, state: s };
}

/** Give a question back when the upstream call never produced an answer. */
export function refundQuota(s: QuotaState, visitor: string, day: string): QuotaState {
  if (s.day !== day) return s;
  if (s.visitors[visitor]) s.visitors[visitor] -= 1;
  if (s.site) s.site -= 1;
  return s;
}

// ---------------------------------------------------------------------------
// The Durable Object: one instance for the whole site, state under a single key.

const STATE_KEY = "quota";

export class AskQuota {
  constructor(private ctx: DurableObjectState) {}

  private async load(): Promise<QuotaState> {
    return (await this.ctx.storage.get<QuotaState>(STATE_KEY)) ?? emptyQuota(today());
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const visitor = url.searchParams.get("v") ?? "anon";
    const day = today();
    let s = await this.load();
    if (s.day !== day) s = emptyQuota(day);
    if (url.pathname === "/take") {
      const r = takeQuota(s, visitor, day);
      await this.ctx.storage.put(STATE_KEY, r.state);
      return Response.json({ ok: r.ok, reason: r.reason ?? null, ...quotaView(r.state, visitor) });
    }
    if (url.pathname === "/refund") {
      s = refundQuota(s, visitor, day);
      await this.ctx.storage.put(STATE_KEY, s);
      return Response.json({ ok: true, ...quotaView(s, visitor) });
    }
    return Response.json(quotaView(s, visitor));
  }
}

// ---------------------------------------------------------------------------
// The HTTP handler.

/** A visitor is an IP, hashed so the counter never holds an address. */
async function visitorId(request: Request): Promise<string> {
  const ip = request.headers.get("cf-connecting-ip") ?? request.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("ask:" + ip));
  return [...new Uint8Array(digest)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function quotaStub(env: AskEnv): DurableObjectStub | null {
  if (!env.ASK_QUOTA) return null;
  return env.ASK_QUOTA.get(env.ASK_QUOTA.idFromName("site"));
}

async function quotaCall(env: AskEnv, path: string, visitor: string): Promise<Record<string, unknown>> {
  const stub = quotaStub(env);
  if (!stub) return { ok: true, remaining: PER_VISITOR_PER_DAY, site_remaining: SITE_PER_DAY, per_day: PER_VISITOR_PER_DAY, unmetered: true };
  const res = await stub.fetch(`https://quota${path}?v=${encodeURIComponent(visitor)}`);
  return (await res.json()) as Record<string, unknown>;
}

const SYSTEM = `You answer questions on Namık Akman's economics data site (namikakmandev.github.io) using the econ tools connected to you: curated datasets, live pulls from FRED, Eurostat, World Bank, ECB, OECD, BIS, IMF, FAOSTAT, TCMB EVDS, SEC EDGAR and Our World in Data, and an econometrics toolkit.

How to work:
- Start with search_datasets or list_datasets when you do not know the series id; never guess ids.
- Pull only what the answer needs: use start, last_n or frequency so a tool result is not thousands of points. At most six tool calls per question.
- Every tool result carries "source" and "caveats". Quote the source next to the number, and repeat a caveat when it changes how the number should be read (a base change, a survey break, projections mixed with actuals).
- For any comparison or trend, call plot and give the visitor the chart link; it opens an interactive chart.
- Never invent a number. If the data is not there, say so and say where it might be found.
- Answer in the visitor's language (Turkish or English). Be brief: a few sentences and the key figures, not an essay. Use plain text with short paragraphs; links as [text](url).`;

interface AskBody { question?: string; history?: Array<{ role: "user" | "assistant"; content: string }> }

export async function handleAskRequest(request: Request, env: AskEnv, mcpUrl: string): Promise<Response> {
  const cors = { "access-control-allow-origin": "*", "access-control-allow-headers": "content-type" };
  const json = (obj: unknown, status = 200) => new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...cors } });
  const url = new URL(request.url);
  const visitor = await visitorId(request);

  if (request.method === "GET" || url.pathname.endsWith("/quota")) {
    const q = await quotaCall(env, "/", visitor);
    return json({ ...q, model: ASK_MODEL, enabled: !!env.ANTHROPIC_API_KEY });
  }
  if (request.method !== "POST") return json({ error: "POST a JSON body: {question, history?}" }, 405);
  if (!env.ANTHROPIC_API_KEY) return json({ error: "The assistant is not switched on: the server has no ANTHROPIC_API_KEY. Connect the MCP endpoint to your own Claude instead." }, 503);

  let body: AskBody;
  try { body = (await request.json()) as AskBody; } catch { return json({ error: "The body is not JSON" }, 400); }
  const question = String(body.question ?? "").trim();
  if (!question) return json({ error: "Ask something" }, 400);
  if (question.length > MAX_QUESTION_CHARS) return json({ error: `Keep a question under ${MAX_QUESTION_CHARS} characters` }, 400);
  const history = (Array.isArray(body.history) ? body.history : [])
    .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content.trim())
    .slice(-MAX_HISTORY_TURNS)
    .map((m) => ({ role: m.role, content: m.content.slice(0, 4000) }));
  // The transcript must alternate and end on the question; drop a leading assistant turn.
  while (history.length && history[0].role === "assistant") history.shift();

  const q = await quotaCall(env, "/take", visitor);
  if (!q.ok) {
    return json({
      error: q.reason === "site"
        ? "The assistant has answered its share of questions for today across the whole site. It resets at midnight UTC; or connect the server to your own Claude, which has no limit."
        : `That is ${PER_VISITOR_PER_DAY} questions today, the daily allowance per visitor. It resets at midnight UTC; or connect the server to your own Claude, which has no limit.`,
      reason: q.reason, remaining: 0, per_day: PER_VISITOR_PER_DAY,
    }, 429);
  }

  const mcpServer: Record<string, unknown> = { type: "url", url: mcpUrl, name: "econ" };
  const bearer = (env.MCP_API_KEYS ?? "").split(",").map((s) => s.trim()).filter(Boolean)[0];
  if (bearer) mcpServer.authorization_token = bearer;

  const payload = {
    model: ASK_MODEL,
    max_tokens: MAX_TOKENS,
    stream: true,
    system: SYSTEM,
    messages: [...history, { role: "user", content: question }],
    mcp_servers: [mcpServer],
    tools: [{ type: "mcp_toolset", mcp_server_name: "econ" }],
    output_config: { effort: "medium" },
    // If a safety classifier declines, the request is re-routed server-side by refusal category.
    fallbacks: "default",
  };

  let upstream: Response;
  try {
    upstream = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "mcp-client-2025-11-20,server-side-fallback-2026-07-01",
      },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    await quotaCall(env, "/refund", visitor);
    return json({ error: `Could not reach the model: ${e instanceof Error ? e.message : String(e)}` }, 502);
  }
  if (!upstream.ok || !upstream.body) {
    await quotaCall(env, "/refund", visitor);
    const text = await upstream.text().catch(() => "");
    let msg = text.slice(0, 300);
    try { msg = String((JSON.parse(text) as { error?: { message?: string } }).error?.message ?? msg); } catch { /* keep raw */ }
    return json({ error: `The model returned ${upstream.status}: ${msg}` }, 502);
  }
  // Anthropic's own server-sent events go straight through; the page reads text deltas,
  // tool-use blocks and the stop reason from them.
  return new Response(upstream.body, {
    status: 200,
    headers: { "content-type": "text/event-stream", "cache-control": "no-cache", "x-ask-remaining": String(q.remaining ?? ""), ...cors, "access-control-expose-headers": "x-ask-remaining" },
  });
}
