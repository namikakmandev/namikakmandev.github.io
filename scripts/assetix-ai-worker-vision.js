/*
 * assetix-ai — shared Anthropic proxy with VISION support
 * =======================================================
 * Drop-in upgrade for the Cloudflare Worker at
 * https://assetix-ai.akmannamik83.workers.dev
 *
 * What it does
 *   POST {prompt, system}                → {text}               (unchanged — FiloDesk, dealer demo keep working)
 *   POST {prompt, system, image}         → {text, vision: true} (new — image is a JPEG/PNG data URL)
 *
 * The report-to-dashboard.html page detects `vision: true` in the reply; if the
 * flag is missing it automatically falls back to in-browser OCR, so deploying
 * this worker is safe to do at any time, in either order.
 *
 * How to deploy
 *   1. Cloudflare dashboard → Workers & Pages → assetix-ai → Edit code.
 *   2. BEFORE replacing anything, compare with your current code — if your
 *      worker uses a different MODEL or MAX_TOKENS, keep your values.
 *   3. Paste this file, keep your ANTHROPIC_API_KEY secret binding as-is
 *      (Settings → Variables → ANTHROPIC_API_KEY), then Deploy.
 *
 * Cost note: MODEL below is Claude's most capable tier. For a public demo
 * endpoint you may prefer "claude-haiku-4-5" (much cheaper, still strong at
 * reading report pages) — change the constant to switch.
 */

const MODEL = "claude-opus-4-8";
const MAX_TOKENS = 4096; // dashboard JSON needs room — short caps truncate it

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

function json(status, obj) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json", ...CORS },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (request.method !== "POST") return json(405, { error: "POST only" });

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return json(400, { error: "Body must be JSON" });
    }
    const prompt = typeof body.prompt === "string" ? body.prompt : "";
    const system = typeof body.system === "string" ? body.system : "";
    const image = typeof body.image === "string" ? body.image : "";
    if (!prompt) return json(400, { error: "Missing 'prompt'" });

    // Build the user content: optional image block first, then the text.
    const content = [];
    if (image) {
      // Accept a data URL: data:image/jpeg;base64,....
      const m = image.match(/^data:(image\/(?:jpeg|png|webp|gif));base64,(.+)$/s);
      if (!m) return json(400, { error: "image must be a base64 image data URL" });
      if (m[2].length > 8_000_000) return json(413, { error: "image too large" });
      content.push({
        type: "image",
        source: { type: "base64", media_type: m[1], data: m[2] },
      });
    }
    content.push({ type: "text", text: prompt.slice(0, 60_000) });

    const apiBody = {
      model: MODEL,
      max_tokens: MAX_TOKENS,
      messages: [{ role: "user", content }],
    };
    if (system) apiBody.system = system.slice(0, 20_000);

    let r;
    try {
      r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify(apiBody),
      });
    } catch (e) {
      return json(502, { error: "Upstream connection failed" });
    }

    let data;
    try {
      data = await r.json();
    } catch (e) {
      return json(502, { error: "Upstream returned non-JSON (" + r.status + ")" });
    }
    if (!r.ok) {
      return json(r.status, {
        error: "AI error (" + r.status + ")",
        detail: data && data.error ? data.error.message : undefined,
      });
    }
    if (data.stop_reason === "refusal") {
      return json(200, { text: "", vision: !!image, error: "The AI declined this request." });
    }

    const text = (data.content || [])
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("\n");

    return json(200, { text, vision: !!image });
  },
};
