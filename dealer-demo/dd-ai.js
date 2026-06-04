// AI advisor for the Dealership Profit & Variance Diagnostic.
// Reuses the shared Anthropic proxy. Runs on the SAMPLE dataset only —
// an uploaded real trial balance is never sent anywhere, preserving the
// tool's "nothing is uploaded" promise.

(function () {
  var AI_PROXY_URL = "https://assetix-ai.akmannamik83.workers.dev";
  var AI_SYSTEM =
    "You are an experienced automotive-retail financial advisor talking to a car-dealer principal or GM. " +
    "You are reading a diagnostic built from the dealership's own trial balance (Turkish ₺, Tek Düzen accounts), plus units, list prices, budget and the OEM bonus programme. " +
    "Explain in plain language where the profit REALLY comes from (usually fixed operations — parts & service — and OEM bonus money, not the metal margin on new cars), where price is leaking below list, why plan was missed (volume vs rate), and how close the dealer is to the next OEM stair-step tier. " +
    "Be balanced and cautious: do NOT give hard orders ('cut this', 'fire that') — weigh options with measured language ('worth reviewing', 'you may want to look at'). " +
    "Remind the user, where relevant, of things NOT in these numbers (campaign support and trade-in over-allowances sitting inside 'leakage', cash timing, why a division looks weak, one-offs). Do not over-claim leakage as lost discipline. " +
    "You are told which TAB the user is currently viewing — if their question relates to it, focus your answer there. " +
    "Industry benchmark ranges are general orientation only, NOT brand-specific truth: present a flag as a question worth asking, never as a verdict. " +
    "If asked HOW a number is computed, use the 'METHOD & NOTES' block. Do NOT invent figures you were not given; if unsure say 'I don't have that here'. " +
    "Keep answers short, clear, English. This is analysis from an illustrative Phase-1 model, not formal financial or tax advice.";

  function askAI(prompt, system) {
    return fetch(AI_PROXY_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: prompt, system: system })
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) return { error: (j.error || ("AI error (" + r.status + ")")) + (j.detail ? " — " + j.detail : "") };
        return { text: j.text || "" };
      });
    }).catch(function () { return { error: "Connection error — could not reach the AI service." }; });
  }

  // ₺ formatter (mirror of the page's L()); fall back to the global if present.
  function L(v) {
    if (typeof window.L === "function") return window.L(v);
    var r = Math.round(v); return (r < 0 ? "-₺" : "₺") + Math.abs(r).toLocaleString("en-US");
  }
  function p1(v) { return (v == null ? "—" : v.toFixed(1) + "%"); }

  function ddContext() {
    var d = window.__DD;
    if (!d) return "No data computed yet.";
    var divLines = d.divisions.map(function (x) {
      var pr = d.per[x];
      return "- " + x + ": revenue " + L(pr.rev) + ", gross " + L(pr.gross) +
        " (" + (pr.rev ? (pr.gross / pr.rev * 100).toFixed(1) : "0.0") + "% margin)";
    }).join("\n");

    var allocLine = "";
    if (d.ohBasis && d.ohBasis !== "none") {
      var basisName = { rev: "revenue share", gross: "gross-profit share", equal: "equal per division" }[d.ohBasis] || d.ohBasis;
      allocLine = "OVERHEAD ALLOCATION is ON (basis: " + basisName + ") — net profit per division after its allocated overhead:\n" +
        d.divisions.map(function (x) { return "- " + x + ": net " + L(d.netBy[x]) + " (overhead " + L(d.alloc[x]) + ")"; }).join("\n") +
        "\n(Allocation is a modelling choice, not a hard cost — a division can look loss-making purely from carrying shared overhead it doesn't truly cause; flag this when relevant.)\n";
    }

    var activeTabEl = document.querySelector("#tabs .tab.on");
    var activeTab = activeTabEl ? activeTabEl.textContent.trim() : "Overview";

    var m = window.MACRO;
    var macroLine = "";
    if (m) {
      macroLine = "LIVE TÜRKİYE MACRO BACKDROP (TCMB EVDS, monthly): inflation (TÜFE yıllık) " +
        (m.market && m.market.tufe && m.market.tufe.yoy != null ? m.market.tufe.yoy + "%" : "—") + ", policy rate " +
        (m.rate && m.rate.value != null ? m.rate.value + "%" : "—") + ", commercial loan rate " +
        (m.market && m.market.loan_comm ? m.market.loan_comm.value + "%" : "—") + ", USD/TRY " +
        (m.fx ? m.fx.USDTRY : "—") + ", EUR/TRY " + (m.fx ? m.fx.EURTRY : "—") +
        ". Use this for two dealer-specific angles: (a) FLOORPLAN financing cost — at these loan rates, unsold stock is expensive to hold; (b) REPLACEMENT-COST margin — at this inflation, cost-based COGS understates the true cost of what was sold, so reported margin overstates real margin.\n";
    }

    var ltvLine = "";
    if (d.ltv) {
      ltvLine = "DEAL & LIFETIME VALUE (a typical new-car deal): front-end (car only, after discount) " + L(d.ltv.front) +
        ", F&I " + L(d.ltv.fi) + ", service annuity " + L(d.ltv.annuity) + " (" + d.ltv.years + " yrs @ " + d.ltv.ret + "% retention) → true customer lifetime value " + L(d.ltv.ltv) +
        ". Point: the metal front-end is thin/negative; the multi-year service annuity is the real prize, so a discount that secures a retained service customer can pay off.\n";
    }

    var ol = window.OUTLOOK;
    var outlookLine = "";
    if (ol && ol.rows) {
      outlookLine = "YEAR-END 2026 OUTLOOK (official sources, shown as published — not this tool's forecast): " +
        ol.rows.map(function (r) { return r.src.split(" — ")[0] + " (" + r.date + ") inflation " + r.inf + ", USD/TRY " + r.fx + ", GDP " + r.gdp; }).join("; ") +
        ". Note the divergence: the government target (~16%) is far below the market/IMF expectation (~29%); for planning, lean to the higher end.\n";
    }

    var rmLine = "";
    if (d.realMargin) {
      rmLine = "REAL (INFLATION-ADJUSTED) MARGIN: at ~" + d.realMargin.infl + "% inflation and ~" + d.realMargin.holdM +
        " months' average stock-holding, ~" + L(d.realMargin.drag) + " of reported gross is just the rising replacement cost of inventory, not real profit — so replacement-cost margin is " +
        d.realMargin.real.toFixed(1) + "% vs reported " + d.realMargin.reported.toFixed(1) + "%. Under high inflation, reported profit overstates real profit; this is diagnosis, not a tax position.\n";
    }

    var bmLine = "";
    if (d.benchmarks && d.benchmarks.length) {
      bmLine = "INDUSTRY BENCHMARK CONTEXT (general automotive-retail reference ranges — orientation only, confirm per brand):\n" +
        d.benchmarks.map(function (b) {
          return "- " + b.lab + ": this dealer " + b.val.toFixed(1) + "% vs reference " + b.lo + "–" + b.hi + "% → " + b.status;
        }).join("\n") + "\n";
    }

    return "OPEN TOOL: Dealership Profit & Variance Diagnostic (Phase 1 — built from one trial balance). SAMPLE auto dealer, Turkish ₺ / Tek Düzen accounts.\n" +
      "USER IS CURRENTLY VIEWING THE '" + activeTab + "' TAB — focus there if the question relates to it.\n" +
      "CONSOLIDATED: revenue " + L(d.rev) + " · gross profit " + L(d.gross) + " (" + p1(d.grossPct) + ") · operating overhead " + L(d.overhead) + (d.ohBasis && d.ohBasis !== "none" ? " (allocated to divisions)" : " (one shared pool)") + " · net profit " + L(d.net) + " (" + p1(d.netPct) + " of revenue).\n" +
      "DIVISIONS (gross profit):\n" + divLines + "\n" +
      allocLine +
      ltvLine +
      macroLine +
      rmLine +
      outlookLine +
      "PROFIT ENGINE: biggest = " + d.best + " (" + L(d.bestGross) + ", " + d.bestSharePct.toFixed(0) + "% of all gross). Thinnest margin = " + d.thin + " (" + p1(d.thinPct) + "). Service absorption = " + d.absorption.toFixed(0) + "% (fixed-ops gross ÷ total overhead; 100% = parts & service alone cover all overhead).\n" +
      "ADDRESSABLE LEAKAGE (vs the dealer's own targets, OEM support stripped out): total " + L(d.totLeak) + (d.worstLeak && d.worstLeak !== "—" ? "; biggest = " + d.worstLeak + " (" + L(d.worstLeakAmt) + ")" : "") + (d.leaks && d.leaks.length ? ". Ranked sources: " + d.leaks.map(function(x){return x.name+" "+L(x.amt);}).join("; ") : "") + ". Most leakage is usually in fixed-ops (service labour-rate realization), not vehicle discounts.\n" +
      "VARIANCE vs PLAN: gross " + (d.tVar < 0 ? "missed plan by " : "beat plan by ") + L(Math.abs(d.tVar)) + ", driven mainly by " + d.driver + ". Volume effect " + L(d.tVol) + " + Rate effect " + L(d.tRate) + " reconcile exactly to the " + L(d.tVar) + " total. Worst vs plan: " + d.worstVar + " (" + L(d.worstVarAmt) + ").\n" +
      "OEM BONUS (" + d.ncDiv + "): registration achievement " + (d.ach * 100).toFixed(0) + "% of target (tier " + d.tierLbl + "). Holdback " + L(d.holdback) + " + volume stair-step " + L(d.volBonus) + " (" + L(d.perUnit) + "/unit, retroactive on all units) + CSI " + (d.csiOn ? L(d.csiAmt) : "withheld (target not met)") + " = total OEM income " + L(d.oem) + ". New-car margin from accounts " + p1(d.ncRev ? d.ncGross / d.ncRev * 100 : 0) + " → " + p1(d.ncRev ? d.ncGrossOEM / d.ncRev * 100 : 0) + " WITH OEM money. " + (d.nextB && d.unitsNeeded > 0 ? d.unitsNeeded + " more new car(s) reaches the next tier (the stair-step is retroactive, so a few units near a threshold can be worth far more than their own margin)." : "Top tier reached.") + "\n" +
      bmLine +
      "INDUSTRY EXTRAS (cite as orientation, not verdicts): Benchmark reference ranges include NADA Data 2025 (US franchised dealers; service & parts ≈ 13% of sales, ~$494 per repair order) — US data, directional only for Türkiye. USED-CAR MARKET (BETAM sahibindex): avg listing ≈ ₺1.17M, +23.3% YoY nominal but −6.8% in REAL terms after inflation — nominal up, real values eroding. EV WATCH: Türkiye EV sales roughly doubled in 2025; EVs need far less routine service, so the dealer's service-absorption profit engine faces structural pressure.\n" +
      "\nMETHOD & NOTES (use if asked how a number is computed):\n" +
      "- Everything starts from ONE trial balance. Accounts are tagged revenue / cost of sales / operating expense and mapped to a division.\n" +
      "- Gross profit = revenue − cost of sales (per division and total). Overhead is ONE shared pool, subtracted only at the total — divisions are NOT charged an arbitrary overhead split (so divisions show gross, not net).\n" +
      "- Service absorption % = (Service + Parts gross) ÷ total overhead. A dealer benchmark of ~100% means fixed ops alone pay all the bills.\n" +
      "- Price leakage = (list price − realized price) × units, per division; realized price = division revenue ÷ units.\n" +
      "- Variance: Volume effect = (actual revenue − budget revenue) × budget gross%; Rate effect = actual revenue × (actual gross% − budget gross%). They sum exactly to total gross variance.\n" +
      "- OEM income = holdback (% of new-car revenue) + volume stair-step (₺/unit by tier of the annual registration target, retroactive on every unit) + CSI/margin support (released only if the survey target is met). Real new-car profit = accounts gross + OEM income.\n" +
      "- Phase 2 (not built yet): replacement-cost / inflation-adjusted margin — under high Turkish inflation, cost-based COGS understates the true cost of what was sold.\n" +
      "- Everything runs locally in the browser. This advisor is answering about the built-in SAMPLE dealership only.";
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
          : "align-self:flex-start;background:var(--surface);border:1px solid var(--line);color:var(--ink);border-bottom-left-radius:4px");
    w.textContent = text; msgs.appendChild(w); msgs.scrollTop = msgs.scrollHeight; return w;
  }
  function openPanel() {
    panel.style.display = "flex";
    if (!greeted) {
      greeted = true;
      bubble("ai", "Hi — ask me about this dealership. e.g. “Where does the profit really come from?”, “How much am I leaking below list?”, or “How close am I to the next OEM bonus tier?”");
    }
    setTimeout(function () { input.focus(); }, 50);
  }
  function closePanel() { panel.style.display = "none"; }
  fab.addEventListener("click", function () { panel.style.display === "flex" ? closePanel() : openPanel(); });
  closeBtn.addEventListener("click", closePanel);

  function send() {
    var q = (input.value || "").trim(); if (!q) return;
    input.value = ""; bubble("user", q); history.push("User: " + q);
    // Privacy guard: never send an uploaded real trial balance.
    if (!window.__DD || !window.__DD.isSample) {
      bubble("ai", "To protect confidentiality, the assistant only works on the built-in sample dealership — your uploaded trial balance stays in your browser and is never sent anywhere. Reload the page to return to the sample and I'll answer in full.");
      return;
    }
    var typing = bubble("ai", "…"); sendBtn.disabled = true;
    var convo = history.slice(-6).join("\n");
    var prompt = ddContext() + "\n\nCONVERSATION:\n" + convo +
      "\n\nAnswer the last question in the context of this dealership — short, clear, English.";
    askAI(prompt, AI_SYSTEM).then(function (res) {
      typing.textContent = res.error ? "⚠ " + res.error : res.text;
      if (!res.error) history.push("Advisor: " + res.text);
      sendBtn.disabled = false; setTimeout(function () { input.focus(); }, 50);
    });
  }
  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); send(); } });
})();
