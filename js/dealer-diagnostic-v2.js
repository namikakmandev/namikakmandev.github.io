// Dealership Profit & Variance Diagnostic — Phase 1 skeleton
// One dataset (trial balance + units + list + budget) -> P&L, realization, variance.

var SAMPLE_TB = [
  { code: "600.01", name: "New car sales",              div: "New cars",  kind: "rev",  amount: 18000000 },
  { code: "600.02", name: "Used car sales",             div: "Used cars", kind: "rev",  amount: 9000000 },
  { code: "600.03", name: "Service & repair revenue",   div: "Service",   kind: "rev",  amount: 2400000 },
  { code: "600.04", name: "Parts sales",                div: "Parts",     kind: "rev",  amount: 1800000 },
  { code: "600.05", name: "F&I / commission income",    div: "F&I",       kind: "rev",  amount: 600000 },
  { code: "600.06", name: "Rental income",              div: "Rental",    kind: "rev",  amount: 700000 },
  { code: "620.01", name: "New car cost of sales",      div: "New cars",  kind: "cogs", amount: 17100000 },
  { code: "620.02", name: "Used car cost of sales",     div: "Used cars", kind: "cogs", amount: 8100000 },
  { code: "620.03", name: "Service direct cost",        div: "Service",   kind: "cogs", amount: 840000 },
  { code: "620.04", name: "Parts cost of sales",        div: "Parts",     kind: "cogs", amount: 1350000 },
  { code: "620.05", name: "F&I direct cost",            div: "F&I",       kind: "cogs", amount: 60000 },
  { code: "620.06", name: "Rental direct cost",         div: "Rental",    kind: "cogs", amount: 490000 },
  { code: "760.00", name: "Marketing & selling expense",div: "Overhead",  kind: "opex", amount: 1500000 },
  { code: "770.00", name: "General administrative exp.",div: "Overhead",  kind: "opex", amount: 2400000 },
];

var DIVS = ["New cars", "Used cars", "Service", "Parts", "F&I", "Rental"];
var BUDGET = {
  "New cars":  { rev: 18500000, gm: 6 },
  "Used cars": { rev: 8500000,  gm: 10 },
  "Service":   { rev: 2600000,  gm: 66 },
  "Parts":     { rev: 1900000,  gm: 26 },
  "F&I":       { rev: 700000,   gm: 90 },
  "Rental":    { rev: 700000,   gm: 32 },
};

function n(v) {
  var x = parseFloat(v);
  return isNaN(x) ? 0 : x;
}
function getN(id) {
  var el = document.getElementById(id);
  return el ? n(el.value) : 0;
}
function setTxt(id, t) {
  var el = document.getElementById(id);
  if (el) el.textContent = t;
}
function lira(v) {
  var r = Math.round(v);
  return (r < 0 ? "-₺" : "₺") + Math.abs(r).toLocaleString("en-US");
}
function pc(part, whole) {
  return whole ? (part / whole) * 100 : 0;
}

// ---- build editable inputs once (so typing never loses focus) ----
function buildInputs() {
  var tb = document.getElementById("tb-grid");
  var html = "";
  SAMPLE_TB.forEach(function (a, i) {
    html +=
      '<div class="dd2-tbrow">' +
      '<label for="tb-' + i + '"><b>' + a.code + "</b> " + a.name +
      ' <span class="dd2-tag">' + a.div + "</span></label>" +
      '<input type="number" id="tb-' + i + '" step="10000" value="' + a.amount + '" />' +
      "</div>";
  });
  tb.innerHTML = html;

  var bud = document.getElementById("bud-grid");
  var bh = "";
  DIVS.forEach(function (d, i) {
    bh +=
      '<div class="form-row"><label for="br-' + i + '">' + d + " — budget revenue</label>" +
      '<input type="number" id="br-' + i + '" step="50000" value="' + BUDGET[d].rev + '" /></div>' +
      '<div class="form-row"><label for="bg-' + i + '">' + d + " — budget gross %</label>" +
      '<input type="number" id="bg-' + i + '" step="0.5" value="' + BUDGET[d].gm + '" /></div>';
  });
  bud.innerHTML = bh;

  document.querySelectorAll("input").forEach(function (el) {
    el.addEventListener("input", recompute);
  });
}

function recompute() {
  // --- Part 1: division P&L from the trial balance ---
  var per = {};
  DIVS.forEach(function (d) { per[d] = { rev: 0, cogs: 0 }; });
  var overhead = 0;
  SAMPLE_TB.forEach(function (a, i) {
    var amt = getN("tb-" + i);
    if (a.kind === "opex") { overhead += amt; return; }
    if (!per[a.div]) per[a.div] = { rev: 0, cogs: 0 };
    if (a.kind === "rev") per[a.div].rev += amt;
    else per[a.div].cogs += amt;
  });

  var totRev = 0, totGross = 0, plRows = "";
  DIVS.forEach(function (d) {
    per[d].gross = per[d].rev - per[d].cogs;
    totRev += per[d].rev;
    totGross += per[d].gross;
  });
  var net = totGross - overhead;
  DIVS.forEach(function (d) {
    var p = per[d];
    plRows +=
      "<tr><td>" + d + '</td><td class="num">' + lira(p.rev) +
      '</td><td class="num">' + lira(p.cogs) + '</td><td class="num">' + lira(p.gross) +
      '</td><td class="num">' + pc(p.gross, p.rev).toFixed(1) + '%</td><td class="num">' +
      pc(p.gross, totGross).toFixed(0) + "%</td></tr>";
  });
  plRows +=
    '<tr style="font-weight:700"><td>Total</td><td class="num">' + lira(totRev) +
    '</td><td class="num">' + lira(totRev - totGross) + '</td><td class="num">' +
    lira(totGross) + '</td><td class="num">' + pc(totGross, totRev).toFixed(1) +
    '%</td><td class="num">100%</td></tr>';
  document.getElementById("pl-tbody").innerHTML = plRows;

  setTxt("k-rev", lira(totRev));
  setTxt("k-gross", lira(totGross));
  setTxt("k-oh", lira(overhead));
  setTxt("k-net", lira(net));
  setTxt("k-net-pct", pc(net, totRev).toFixed(1) + "% of rev");
  var ne = document.getElementById("k-net");
  if (ne) ne.style.color = net < 0 ? "var(--loss)" : "";

  var showR = per["New cars"].rev + per["Used cars"].rev;
  var showG = per["New cars"].gross + per["Used cars"].gross;
  var aftR = per["Service"].rev + per["Parts"].rev;
  var aftG = per["Service"].gross + per["Parts"].gross;
  setTxt(
    "pl-insight",
    "Showroom (new + used) is " + pc(showR, totRev).toFixed(0) +
      "% of revenue but only " + pc(showG, totGross).toFixed(0) +
      "% of gross. Aftersales (service + parts) is just " + pc(aftR, totRev).toFixed(0) +
      "% of revenue but " + pc(aftG, totGross).toFixed(0) +
      "% of gross — a service business with a showroom attached."
  );
  setTxt("bridge-net", lira(net));

  // --- Part 2: price realization vs list ---
  var uN = Math.max(1, getN("u-new")), lN = getN("l-new");
  var uU = Math.max(1, getN("u-used")), lU = getN("l-used");
  var realN = per["New cars"].rev / uN, realU = per["Used cars"].rev / uU;
  var leakN = (lN - realN) * uN, leakU = (lU - realU) * uU;
  var leak = leakN + leakU;
  setTxt("r-new", pc(realN, lN).toFixed(1) + "%");
  setTxt("r-used", pc(realU, lU).toFixed(1) + "%");
  setTxt("r-leak", lira(leak));
  var rl = document.getElementById("r-leak");
  if (rl) rl.style.color = leak > 0 ? "var(--loss)" : "";
  setTxt(
    "r-insight",
    "New cars realize " + lira(realN) + " of a " + lira(lN) +
      " list (" + pc(realN, lN).toFixed(1) + "%); used " + lira(realU) +
      " of " + lira(lU) + " (" + pc(realU, lU).toFixed(1) + "%). Closing the gap to list is " +
      lira(leak) + " a year — and not one deal record was needed to see it."
  );

  // --- Part 3: variance vs budget (volume + margin-rate) ---
  var actG = 0, budG = 0, vRows = "", worst = null;
  DIVS.forEach(function (d, i) {
    var revA = per[d].rev, gA = per[d].rev ? per[d].gross / per[d].rev : 0;
    var revB = getN("br-" + i), gB = getN("bg-" + i) / 100;
    var grA = per[d].gross, grB = revB * gB;
    var vol = (revA - revB) * gB;
    var rate = revA * (gA - gB);
    actG += grA;
    budG += grB;
    if (!worst || vol + rate < worst.v) worst = { d: d, v: vol + rate };
    vRows +=
      "<tr><td>" + d + '</td><td class="num">' + lira(vol) +
      '</td><td class="num">' + lira(rate) + '</td><td class="num">' +
      lira(vol + rate) + "</td></tr>";
  });
  var varc = actG - budG;
  vRows +=
    '<tr style="font-weight:700"><td>Total</td><td class="num">—</td><td class="num">—</td><td class="num">' +
    lira(varc) + "</td></tr>";
  document.getElementById("v-tbody").innerHTML = vRows;
  setTxt("v-act", lira(actG));
  setTxt("v-bud", lira(budG));
  setTxt("v-var", lira(varc));
  var vv = document.getElementById("v-var");
  if (vv) vv.style.color = varc < 0 ? "var(--loss)" : "";
  setTxt(
    "v-insight",
    (varc < 0 ? "Missed plan by " + lira(-varc) : "Beat plan by " + lira(varc)) +
      ". Biggest single driver: " + worst.d + " (" + lira(worst.v) +
      "). The board can now see whether the gap is volume or margin — not just that it exists."
  );

  // --- closing synthesis ---
  setTxt(
    "dd-close",
    "One dataset, one story: net profit is " + lira(net) +
      "; price realization is leaving " + lira(leak) +
      " on the table vs list; and the result " +
      (varc < 0 ? "missed plan by " + lira(-varc) : "beat plan by " + lira(varc)) +
      ". None of this is new data — it was sitting in their own trial balance the whole time. That, ranked and explained, is the engagement."
  );
}

buildInputs();
recompute();
