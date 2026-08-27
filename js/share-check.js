/* Shared plumbing for the checker tools: reproducible analysis links and
   Python code export.

   A share link packs the pasted data and every setting into the URL FRAGMENT
   (the part after #). Fragments are never sent to any server — not that these
   pages have one — so the privacy promise survives sharing: the data travels
   inside the link itself, from one browser to another, and nowhere else.
   Anyone opening the link sees the same analysis recomputed live, which makes
   every shared result one click to reproduce or to challenge. */

"use strict";

/* ------------------------------ encoding ----------------------------------- */

const SC_B64 = {
  enc(bytes) {
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000)
      s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  },
  dec(str) {
    const s = atob(str.replace(/-/g, "+").replace(/_/g, "/"));
    const out = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
    return out;
  },
};

async function scPipe(bytes, stream) {
  const s = new Blob([bytes]).stream().pipeThrough(stream);
  return new Uint8Array(await new Response(s).arrayBuffer());
}

// state object -> "z<base64url of deflated JSON>", falling back to raw JSON
// ("r" prefix) where CompressionStream is missing.
async function scEncodeState(obj) {
  const json = new TextEncoder().encode(JSON.stringify(obj));
  if (typeof CompressionStream !== "undefined") {
    const packed = await scPipe(json, new CompressionStream("deflate-raw"));
    return "z" + SC_B64.enc(packed);
  }
  return "r" + SC_B64.enc(json);
}

async function scDecodeState(str) {
  const kind = str[0], body = SC_B64.dec(str.slice(1));
  const json = kind === "z"
    ? await scPipe(body, new DecompressionStream("deflate-raw"))
    : body;
  return JSON.parse(new TextDecoder().decode(json));
}

/* ------------------------------ share button -------------------------------- */

// Wire a share button: getState() supplies the current state; on click the
// link is built, put on the clipboard, and the button confirms briefly.
function scInitShare(buttonId, getState) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  const label = btn.textContent;
  btn.addEventListener("click", async () => {
    const state = getState();
    if (!state) { btn.textContent = "Run a check first"; setTimeout(() => (btn.textContent = label), 1800); return; }
    const hash = await scEncodeState(state);
    const url = location.origin + location.pathname + "#s=" + hash;
    let note = "Link copied";
    if (url.length > 30000) note = "Link copied (very long — email may truncate it; prefer chat)";
    else if (url.length > 8000) note = "Link copied (long — some apps truncate URLs)";
    try { await navigator.clipboard.writeText(url); }
    catch (e) { prompt("Copy this link:", url); note = "Link ready"; }
    btn.textContent = note + " ✓";
    setTimeout(() => (btn.textContent = label), 2600);
  });
}

// On load: if the URL carries a state fragment, hand it to the page.
async function scLoadShared(apply) {
  const m = /[#&]s=([A-Za-z0-9_-]+)/.exec(location.hash);
  if (!m) return false;
  try {
    const state = await scDecodeState(m[1]);
    apply(state);
    return true;
  } catch (e) {
    console.warn("share link unreadable:", e);
    return false;
  }
}

/* ------------------------------ code export --------------------------------- */

// Show generated code in a panel with a copy button. One panel per page.
function scShowCode(containerId, code) {
  const box = document.getElementById(containerId);
  if (!box) return;
  box.hidden = false;
  box.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px">' +
    "<strong>The same analysis as Python</strong>" +
    '<button class="cc-btn ghost" id="' + containerId + '-copy">Copy code</button></div>' +
    '<p class="cc-note">Standard pandas / SciPy / statsmodels. Your data is embedded, so the ' +
    "script is self-contained — run it and the numbers on this page should reproduce.</p>" +
    '<pre style="overflow:auto;max-height:420px;background:var(--surface-2);border-radius:8px;' +
    'padding:12px;font-size:.8rem;line-height:1.45"><code></code></pre>';
  box.querySelector("code").textContent = code;
  document.getElementById(containerId + "-copy").addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(code); } catch (_) {}
    e.target.textContent = "Copied ✓";
    setTimeout(() => (e.target.textContent = "Copy code"), 2000);
  });
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Embed raw pasted data as a Python triple-quoted string, safely.
function scPyData(text) {
  return 'DATA = """\\\n' + text.replace(/\\/g, "\\\\").replace(/"""/g, '\\"\\"\\"') + '\n"""';
}

const SC_API = { scEncodeState, scDecodeState, scInitShare, scLoadShared, scShowCode, scPyData };
if (typeof module !== "undefined" && module.exports) module.exports = SC_API;
if (typeof window !== "undefined") Object.assign(window, SC_API);
