// AI advisor for the Divisional & Monthly P&L tool.
// Reuses the shared Anthropic proxy (same Cloudflare Worker as ASSETIX).
// Reads the live tool globals (INDUSTRIES, CUR, getN, MONTHS, eur, pc) from
// dealer-diagnostic-v2.js, so the model always sees the current numbers.

(function () {
  var AI_PROXY_URL = "https://assetix-ai.akmannamik83.workers.dev";
  var AI_SYSTEM =
    "You are an experienced, level-headed management accountant and commercial-finance advisor. " +
    "You are reading a profit & loss statement that was built from a company's trial balance, broken down by division and across 12 months. " +
    "Explain clearly where the profit really comes from, which divisions are strong or weak, and why some months can run at a loss even in a profitable year. " +
    "Be balanced and cautious: do NOT give definitive orders ('shut this division', 'you must cut costs') — weigh options and use measured language ('worth reviewing', 'you may want to look at'). " +
    "Remind the user, where relevant, that figures NOT in this view (cash timing, why a division is loss-making, one-off items, transfer pricing, the strategic role of a low-margin division) can change the right call. " +
    "If the user asks HOW a number is computed or what a term means, use the 'METHOD & NOTES' block to answer accurately. " +
    "Do NOT invent figures you were not given; if unsure, say 'I don't have that here'. " +
    "Keep answers short, clear, and in English. This is analysis from an illustrative model, not formal financial advice.";

  function askAI(prompt, system) {
    return fetch(AI_PROXY_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: prompt, system: system })
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) return { error: (j.error || ("AI error (" + r.status + ")")) + (j.detail ? " — " + j.detail : "") };
          return { text: j.text || "" };
        });
      })
      .catch(function () { return { error: "Connection error — could not reach the AI service." }; });
  }

  // Recompute the current numbers exactly as the tool does, for context.
  function dd2Context() {
    var ind = INDUSTRIES[CUR];
    if (!ind) return "No data loaded.";
    var DIVS = ind.divisions;
    var per = {};
    DIVS.forEach(function (d) { per[d] = { rev: 0, cogs: 0 }; });
    var overhead = 0;
    ind.tb.forEach(function (a, i) {
      var amt = getN("tb-" + i);
      if (a.kind === "opex") { overhead += amt; return; }
      if (!per[a.div]) per[a.div] = { rev: 0, cogs: 0 };
      if (a.kind === "rev") per[a.div].rev += amt; else per[a.div].cogs += amt;
    });
    var totRev = 0, totGross = 0;
    DIVS.forEach(function (d) {
      per[d].gross = per[d].rev - per[d].cogs;
      totRev += per[d].rev; totGross += per[d].gross;
    });
    var net = totGross - overhead;

    var divLines = DIVS.map(function (d) {
      return "- " + d + ": revenue " + eur(per[d].rev) + ", gross profit " + eur(per[d].gross) +
        " (" + pc(per[d].gross, per[d].rev).toFixed(1) + "% margin, " +
        pc(per[d].gross, totGross).toFixed(0) + "% of total gross)";
    }).join("\n");

    // 12-month seasonal view → which months run at a loss
    var sumW = ind.seasonality.reduce(function (s, w) { return s + w; }, 0) || 1;
    var lossMonths = [];
    MONTHS.forEach(function (m, i) {
      var f = ind.seasonality[i] / sumW;
      var mNet = totGross * f - overhead / 12;
      if (mNet < 0) lossMonths.push(m);
    });

    var ranked = DIVS.slice().sort(function (a, c) { return per[c].gross - per[a].gross; });
    var best = ranked[0], worst = ranked[ranked.length - 1];
    var losers = DIVS.filter(function (d) { return per[d].gross < 0; });

    return "OPEN TOOL: Divisional & Monthly P&L (built from a trial balance). Industry profile: " + ind.label + ".\n" +
      "CONSOLIDATED: revenue " + eur(totRev) + " · gross profit " + eur(totGross) +
      " (" + pc(totGross, totRev).toFixed(1) + "% gross margin) · operating overhead " + eur(overhead) +
      " (one shared pool) · net profit " + eur(net) + " (" + pc(net, totRev).toFixed(1) + "% net margin).\n" +
      "DIVISIONAL gross profit:\n" + divLines + "\n" +
      "READ-OUT: biggest profit engine = " + best + " (" + eur(per[best].gross) + ", " +
      pc(per[best].gross, totGross).toFixed(0) + "% of all gross); weakest = " + worst +
      " (" + pc(per[worst].gross, per[worst].rev).toFixed(1) + "% margin)" +
      (losers.length ? "; loss-making at gross level: " + losers.join(", ") : "") + ".\n" +
      "12-MONTH VIEW: " + (lossMonths.length
        ? lossMonths.length + " month(s) run at a loss (" + lossMonths.join(", ") + ") even though the full year nets " + eur(net) + " — that is when a low-margin business runs short of cash."
        : "no month runs at a loss on this seasonality.") + "\n" +
      "\nMETHOD & NOTES (use if the user asks how a number is computed):\n" +
      "- Source: a single trial balance. Each account is tagged revenue / cost of sales / operating expense and mapped to a division.\n" +
      "- Gross profit (per division and total) = revenue − cost of sales. Gross margin % = gross ÷ revenue.\n" +
      "- Operating overhead is ONE shared pool, subtracted at the total only — it is NOT split arbitrarily across divisions (so divisions show gross, not net).\n" +
      "- Net profit = total gross profit − overhead. Net margin % = net ÷ revenue.\n" +
      "- 12-month view: revenue and cost flex with an industry seasonality pattern; overhead is fixed (1/12 each month). A month runs at a loss when its seasonal gross falls below the fixed monthly overhead. This monthly split is ILLUSTRATIVE — the full version uses 12 real monthly trial balances.\n" +
      "- Everything runs locally in the browser; figures here are an indicative model, not audited accounts. Currency symbols are illustrative.";
  }

  var fab = document.getElementById("aiFab"),
      panel = document.getElementById("aiChat"),
      msgs = document.getElementById("aiChatMsgs"),
      input = document.getElementById("aiChatInput"),
      sendBtn = document.getElementById("aiChatSend"),
      closeBtn = document.getElementById("aiChatClose");
  if (!fab || !panel) return;

  var history = [], greeted = false;
  function bubble(role, text) {
    var me = role === "user", w = document.createElement("div");
    w.style.cssText = "max-width:86%;padding:9px 12px;border-radius:12px;white-space:pre-wrap;" +
      (me ? "align-self:flex-end;background:var(--accent);color:#fff;border-bottom-right-radius:4px"
          : "align-self:flex-start;background:var(--surface);border:1px solid var(--border);color:var(--text);border-bottom-left-radius:4px");
    w.textContent = text; msgs.appendChild(w); msgs.scrollTop = msgs.scrollHeight; return w;
  }
  function openPanel() {
    panel.style.display = "flex";
    if (!greeted) {
      greeted = true;
      bubble("ai", "Hi — ask me about this P&L. e.g. “Which division makes the real profit?”, “Why do some months lose money?”, or “How is net profit calculated?”");
    }
    setTimeout(function () { input.focus(); }, 50);
  }
  function closePanel() { panel.style.display = "none"; }
  fab.addEventListener("click", function () { panel.style.display === "flex" ? closePanel() : openPanel(); });
  closeBtn.addEventListener("click", closePanel);

  function send() {
    var q = (input.value || "").trim(); if (!q) return;
    input.value = ""; bubble("user", q); history.push("User: " + q);
    var typing = bubble("ai", "…"); sendBtn.disabled = true;
    var convo = history.slice(-6).join("\n");
    var prompt = dd2Context() + "\n\nCONVERSATION:\n" + convo +
      "\n\nAnswer the last question in the context of this P&L — short, clear, English.";
    askAI(prompt, AI_SYSTEM).then(function (res) {
      typing.textContent = res.error ? "⚠ " + res.error : res.text;
      if (!res.error) history.push("Advisor: " + res.text);
      sendBtn.disabled = false; setTimeout(function () { input.focus(); }, 50);
    });
  }
  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); send(); } });
})();
