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
const BRIEF_MAX_TOKENS = 9000;

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

/**
 * The advisor reads a dataset the way a careful colleague would before anyone quotes it:
 * what it measures, in what unit and on what base, where it comes from and how fresh it
 * is, where it breaks, what the latest numbers say, and what it must not be used for.
 */
const ADVISOR = `You are the data advisor on Namık Akman's economics data site (namikakmandev.github.io). A visitor is looking at one dataset and wants to understand it before using it. You have the econ tools: describe_dataset, get_caveats, get_series, describe_stats, search_datasets and the rest.

How to work:
- Call describe_dataset for the dataset, then get_caveats, then get_series with last_n (about 8 for annual data, 15 for monthly) for the series the visitor is looking at. At most six tool calls.
- Then write the reading, in this order, with short headings in bold:
  1. What it measures: the object being counted and the unit, in one or two sentences a non-economist can follow. Name the base period of an index.
  2. Where it comes from and how fresh it is: the source, the frequency, the last observation, and whether the tail is provisional or projected.
  3. How to read it: every caveat that changes the reading (a base change, a survey break, a currency, seasonality, a definitional quirk). Say which comparisons are safe and which are not.
  4. What the latest numbers say: the last value with its date, the change on a year earlier, and where that sits against the series' own history. Numbers only from the tool results, each with its date.
  5. Do not use it for: two or three things a reader might be tempted to conclude that this data cannot support.
  6. Worth asking next: two questions this dataset can answer well, phrased so the visitor can type them into the box.
- Never invent a number or a source. If the catalogue note is silent on something, say the note is silent.
- Answer in the visitor's language (Turkish or English). Keep it to about 250 words; plain text with short paragraphs; links as [text](url).`;

/**
 * The front page: a daily brief written from the morning's data. The caller (the fetch
 * workflow) sends the "what moved" note as context; the model reads it, verifies with the
 * tools, adds forecasts and correlations from the toolkit, and writes two to three pages.
 */
const BRIEF = `You write the daily brief for Namık Akman's economics data site (namikakmandev.github.io): a data newspaper's front page, written once each morning from the collection's own numbers. You have the econ tools: get_series, describe_dataset, get_caveats, plot, forecast, compare_series, cross_correlation, describe_stats, search_datasets and the rest.

You are given, as context, today's "what moved" note: the ten most unusual year-on-year moves across the collection, each with dataset, series, latest value, the change and how unusual it is. Start from it. Verify anything you quote beyond it with get_series (use last_n so results stay small). At most sixteen tool calls.

Write in this order, with these markdown headings:

# <a headline of at most twelve words, about the day's most important move>

## Today in the data
Four to six short paragraphs. Each takes one or two of the moves, gives the number with its date and its source, says what usually goes with such a move in the rest of the collection (check it with a second series where you can), and says plainly when a move is small in absolute terms or comes from a young series. Causes are hypotheses to check, never facts: write "worth checking against" not "because of".

## Charts
Call plot for three charts that carry the story (each up to four series, a sensible start date) and list them as markdown links "[title](chart_url)" with one line under each saying what to look at.

## Numbers desk
Two subsections.
### Forecasts
Call forecast (method auto, horizon 3 for monthly, 2 for annual) for two or three of the headline series. Report each as: the last observation with its date, the point forecast for the horizon end, the band, and the method the tool chose. Say what the band means in one clause. A forecast of a regulated or administered series is a projection of its past, say so.
### Correlations
Pick two pairs the moves suggest (the same measure in two countries, or a price and the thing it feeds into) and call cross_correlation or compare_series on year-on-year changes where the tool allows. Report r, the lag if any, and whether it clears the confidence band the tool returns; if it does not, say "not distinguishable from zero" and stop there. Never present a levels correlation between two trending series as a finding.

## What to watch
Three to five bullets on what the next releases in this collection will settle, each naming the dataset. The context lists which monthly series are due.

## Sources
One line per dataset used: publisher and code as the tool's source field gives them, and the last observation date.

Rules: every number carries its date and its dataset; nothing is invented; if a tool fails, say what could not be checked. About 1,300 to 1,700 words. Plain prose, no bullet lists outside What to watch, no tables. Write in English.`;

/** The question the page sends when the visitor presses "Explain this dataset". Exported for tests. */
export function advisorQuestion(dataset: string, series: string[], lang: "en" | "tr" = "en"): string {
  const shown = series.length ? (lang === "tr" ? ` Bakılan seriler: ${series.join(", ")}.` : ` The series on screen: ${series.join(", ")}.`) : "";
  return lang === "tr"
    ? `"${dataset}" veri setini açıkla: neyi ölçüyor, birimi ve kaynağı, kırılmalar ve uyarılar, son rakamlar ne söylüyor, ne için kullanılmamalı.${shown}`
    : `Explain the dataset "${dataset}": what it measures, its unit and source, the breaks and caveats, what the latest numbers say, and what it should not be used for.${shown}`;
}

interface AskBody {
  question?: string;
  history?: Array<{ role: "user" | "assistant"; content: string }>;
  /** "advisor" reads one dataset for the visitor; "brief" writes the daily front page from the context. */
  mode?: "ask" | "advisor" | "brief";
  /** brief only: today's what-moved note and the list of series due, as JSON text. */
  context?: string;
  dataset?: string;
  series?: string[];
  lang?: "en" | "tr";
}

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
  const advisor = body.mode === "advisor";
  const brief = body.mode === "brief";
  const context = brief ? String(body.context ?? "").slice(0, 40000) : "";
  if (brief && !context) return json({ error: "The brief needs its context: the what-moved note" }, 400);
  const dataset = String(body.dataset ?? "").trim().slice(0, 80);
  const shown = (Array.isArray(body.series) ? body.series : []).filter((x) => typeof x === "string").map((x) => x.slice(0, 80)).slice(0, 8);
  if (advisor && !/^[a-z0-9][a-z0-9-]*$/.test(dataset)) return json({ error: "The advisor needs a dataset name" }, 400);
  const question = advisor ? advisorQuestion(dataset, shown, body.lang === "tr" ? "tr" : "en")
    : brief ? `Write today's brief. Today is ${today()}. Context follows.\n\n${context}`
    : String(body.question ?? "").trim();
  if (!question) return json({ error: "Ask something" }, 400);
  if (question.length > MAX_QUESTION_CHARS) return json({ error: `Keep a question under ${MAX_QUESTION_CHARS} characters` }, 400);
  const history = (advisor || brief ? [] : Array.isArray(body.history) ? body.history : [])
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
    max_tokens: brief ? BRIEF_MAX_TOKENS : MAX_TOKENS,
    stream: true,
    system: brief ? BRIEF : advisor ? ADVISOR : SYSTEM,
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
