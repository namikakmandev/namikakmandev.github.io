/* "Ask the data": a question box that talks to the Worker's /v1/ask, which asks Claude with the
   site's own tools attached and streams the answer back as server-sent events. Five questions a
   day per visitor; past that the box points at the free route, connecting the server to your
   own Claude. Drop <div id="ask"></div> on a page and include this script. */
(function () {
  "use strict";
  var host = document.getElementById("ask");
  if (!host) return;
  var API = (host.getAttribute("data-api") || "https://econ-mcp.akmannamik83.workers.dev").replace(/\/$/, "");
  var CONNECT = host.getAttribute("data-connect") || "econ-mcp.html#connect";
  var history = [];      // [{role, content}] sent back so a follow-up can say "and for Germany?"
  var busy = false;

  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  /* Enough markdown for an answer: links, bold, bullets, paragraphs. Everything is escaped first. */
  function md(text) {
    var h = esc(text);
    h = h.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_, t, u) { return "<a href='" + u + "' target='_blank' rel='noopener'>" + t + "</a>"; });
    h = h.replace(/(^|[\s(])((https?:\/\/)[^\s<)]+)/g, function (_, pre, u) { return pre + "<a href='" + u + "' target='_blank' rel='noopener'>" + u + "</a>"; });
    h = h.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
    h = h.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    var lines = h.split("\n"), out = "", inList = false;
    lines.forEach(function (ln) {
      var m = /^\s*[-*•]\s+(.*)$/.exec(ln);
      if (m) { if (!inList) { out += "<ul>"; inList = true; } out += "<li>" + m[1] + "</li>"; return; }
      if (inList) { out += "</ul>"; inList = false; }
      if (!ln.trim()) { out += "<br>"; return; }
      out += "<p>" + ln + "</p>";
    });
    if (inList) out += "</ul>";
    return out;
  }
  function toolLabel(name) {
    var words = { get_series: "reading a series", search_datasets: "searching the catalogue", list_datasets: "listing the datasets", describe_dataset: "reading a dataset's description",
      fetch_external: "pulling live data", search_external: "searching a provider", plot: "drawing a chart", regress: "running a regression", forecast: "forecasting", test_stationarity: "testing for a unit root",
      describe_stats: "summarising", compare_series: "comparing series", cointegration: "testing cointegration", granger_causality: "testing Granger causality", structural_break: "looking for a break",
      suggest_analysis: "choosing a method", var_model: "fitting a VAR", volatility: "fitting GARCH", deflate: "deflating", rolling: "rolling statistics", decompose: "decomposing", hp_filter: "filtering", panel_regress: "panel regression" };
    return words[name] || ("calling " + name);
  }

  host.innerHTML =
    "<div class='ask'>" +
      "<div class='ask-head'><h2 class='sec'>Ask the data</h2>" +
        "<span class='ask-quota' id='ask-quota'>checking…</span></div>" +
      "<p class='sec-note'>Type a question in English or Turkish. The assistant looks the answer up in the datasets and live providers on this site, quotes the source, and draws a chart when one helps. It is Claude Opus 5 with this site's tools; five questions a day per visitor.</p>" +
      "<div class='ask-thread' id='ask-thread' hidden></div>" +
      "<form class='ask-form' id='ask-form'>" +
        "<textarea id='ask-q' rows='2' maxlength='1000' placeholder='e.g. How has Turkish inflation compared with the euro area since 2020?'></textarea>" +
        "<button type='submit' class='ask-go' id='ask-go'>Ask</button>" +
      "</form>" +
      "<div class='ask-examples' id='ask-ex'>" +
        ["Cattle prices against corn in the US since 2015: what happened to the ratio?", "Türkiye'de politika faizi ve enflasyon son beş yılda nasıl seyretti?", "Is the Brent price series stationary? Plot it and test it.", "Which countries in the WEO data have government debt above 100% of GDP?"]
          .map(function (q) { return "<button type='button' class='ask-eg'>" + esc(q) + "</button>"; }).join("") +
      "</div>" +
    "</div>";

  var thread = document.getElementById("ask-thread"), form = document.getElementById("ask-form"), qEl = document.getElementById("ask-q"), go = document.getElementById("ask-go"), quotaEl = document.getElementById("ask-quota");

  function showQuota(remaining, perDay, enabled) {
    if (enabled === false) { quotaEl.textContent = "assistant off"; quotaEl.title = "The server has no API key set, so the box is idle."; return; }
    if (remaining == null) { quotaEl.textContent = ""; return; }
    quotaEl.textContent = remaining + " of " + (perDay || 5) + " questions left today";
    if (remaining <= 0) limitReached();
  }
  function limitReached() {
    go.disabled = true; qEl.disabled = true;
    var note = document.createElement("p");
    note.className = "ask-limit";
    note.innerHTML = "That is today's allowance for this box. It resets at midnight UTC. For unlimited use, <a href='" + esc(CONNECT) + "'>connect the server to your own Claude</a>: it takes a minute and costs this site nothing.";
    form.parentNode.insertBefore(note, form.nextSibling);
  }
  fetch(API + "/v1/ask/quota").then(function (r) { return r.json(); }).then(function (j) { showQuota(j.remaining, j.per_day, j.enabled); }).catch(function () { quotaEl.textContent = ""; });

  function bubble(cls, html) {
    var d = document.createElement("div"); d.className = "ask-msg " + cls; d.innerHTML = html; thread.appendChild(d); thread.hidden = false; return d;
  }

  /* Parse Anthropic's server-sent events as they arrive. Text deltas go on the page; a
     tool-use block becomes a short status line; the stop reason ends the turn. */
  function ask(question) {
    if (busy || !question) return;
    busy = true; go.disabled = true;
    bubble("me", esc(question));
    var ans = bubble("bot", "<div class='ask-status'>thinking…</div><div class='ask-text'></div>");
    var statusEl = ans.querySelector(".ask-status"), textEl = ans.querySelector(".ask-text");
    var text = "", stop = null, tools = 0;
    function render() { textEl.innerHTML = md(text); }
    function finish(errMsg) {
      busy = false; if (!qEl.disabled) go.disabled = false;
      if (errMsg) { statusEl.innerHTML = "<span class='ask-err'>" + esc(errMsg) + "</span>"; return; }
      statusEl.textContent = stop === "pause_turn" ? "stopped at the tool-call limit for one question; ask a narrower follow-up" : stop === "max_tokens" ? "the answer hit its length limit" : stop === "refusal" ? "the model declined this one" : (tools ? tools + " tool call" + (tools > 1 ? "s" : "") : "");
      if (text.trim()) { history.push({ role: "user", content: question }, { role: "assistant", content: text }); if (history.length > 6) history = history.slice(-6); }
    }
    fetch(API + "/v1/ask", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ question: question, history: history }) })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (j) { if (r.status === 429) { showQuota(0, j.per_day); } throw new Error(j.error || ("HTTP " + r.status)); });
        var rem = r.headers.get("x-ask-remaining"); if (rem !== null && rem !== "") showQuota(+rem);
        var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";
        function handle(evt) {
          var d; try { d = JSON.parse(evt); } catch (e) { return; }
          if (d.type === "content_block_start" && d.content_block) {
            var b = d.content_block;
            if (b.type === "mcp_tool_use" || b.type === "server_tool_use" || b.type === "tool_use") { tools++; statusEl.textContent = toolLabel(b.name) + "…"; }
            else if (b.type === "text") { statusEl.textContent = "writing…"; if (text && !/\n$/.test(text)) { text += "\n\n"; render(); } }
          } else if (d.type === "content_block_delta" && d.delta) {
            if (d.delta.type === "text_delta") { text += d.delta.text; render(); }
          } else if (d.type === "message_delta" && d.delta && d.delta.stop_reason) stop = d.delta.stop_reason;
          else if (d.type === "error") throw new Error((d.error && d.error.message) || "stream error");
        }
        function pump() {
          return reader.read().then(function (res) {
            if (res.done) { finish(); return; }
            buf += dec.decode(res.value, { stream: true });
            var parts = buf.split("\n\n"); buf = parts.pop();
            parts.forEach(function (chunk) {
              chunk.split("\n").forEach(function (line) { if (line.indexOf("data:") === 0) handle(line.slice(5).trim()); });
            });
            return pump();
          });
        }
        return pump();
      })
      .catch(function (e) { finish(e.message || String(e)); });
  }

  form.addEventListener("submit", function (ev) { ev.preventDefault(); var q = qEl.value.trim(); if (!q) return; qEl.value = ""; ask(q); });
  qEl.addEventListener("keydown", function (ev) { if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true })); } });
  document.getElementById("ask-ex").addEventListener("click", function (ev) { var b = ev.target.closest(".ask-eg"); if (!b) return; qEl.value = b.textContent; qEl.focus(); });
})();
