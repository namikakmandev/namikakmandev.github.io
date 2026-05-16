// Dealership Divisional P&L — essential first layer
// Input: trial balance. Output: a clean P&L per division.

var SAMPLE_TB = [
  { code: "600.01", name: "New car sales",               div: "New cars",  kind: "rev",  amount: 18000000 },
  { code: "600.02", name: "Used car sales",              div: "Used cars", kind: "rev",  amount: 9000000 },
  { code: "600.03", name: "Service & repair revenue",    div: "Service",   kind: "rev",  amount: 2400000 },
  { code: "600.04", name: "Parts sales",                 div: "Parts",     kind: "rev",  amount: 1800000 },
  { code: "600.05", name: "F&I / commission income",     div: "F&I",       kind: "rev",  amount: 600000 },
  { code: "600.06", name: "Rental income",               div: "Rental",    kind: "rev",  amount: 700000 },
  { code: "620.01", name: "New car cost of sales",       div: "New cars",  kind: "cogs", amount: 17100000 },
  { code: "620.02", name: "Used car cost of sales",      div: "Used cars", kind: "cogs", amount: 8100000 },
  { code: "620.03", name: "Service direct cost",         div: "Service",   kind: "cogs", amount: 840000 },
  { code: "620.04", name: "Parts cost of sales",         div: "Parts",     kind: "cogs", amount: 1350000 },
  { code: "620.05", name: "F&I direct cost",             div: "F&I",       kind: "cogs", amount: 60000 },
  { code: "620.06", name: "Rental direct cost",          div: "Rental",    kind: "cogs", amount: 490000 },
  { code: "760.00", name: "Marketing & selling expense", div: "Overhead",  kind: "opex", amount: 1500000 },
  { code: "770.00", name: "General administrative exp.",  div: "Overhead",  kind: "opex", amount: 2400000 },
];

var DIVS = ["New cars", "Used cars", "Service", "Parts", "F&I", "Rental"];

function n(v) { var x = parseFloat(v); return isNaN(x) ? 0 : x; }
function getN(id) { var el = document.getElementById(id); return el ? n(el.value) : 0; }
function setTxt(id, t) { var el = document.getElementById(id); if (el) el.textContent = t; }
function lira(v) {
  var r = Math.round(v);
  return (r < 0 ? "-₺" : "₺") + Math.abs(r).toLocaleString("en-US");
}
function pc(part, whole) { return whole ? (part / whole) * 100 : 0; }

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
  document.querySelectorAll("#tb-grid input").forEach(function (el) {
    el.addEventListener("input", recompute);
  });
}

function recompute() {
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

  var totRev = 0, totGross = 0;
  DIVS.forEach(function (d) {
    per[d].gross = per[d].rev - per[d].cogs;
    totRev += per[d].rev;
    totGross += per[d].gross;
  });
  var net = totGross - overhead;

  // Vertical P&L: line items down the rows, divisions (+ Total) across the columns
  var paren = function (v) { return "(" + lira(Math.abs(v)) + ")"; };
  var ncols = DIVS.length + 2;

  // Consolidated P&L — the whole dealership as one statement
  var nls0 = net < 0 ? ' style="color:var(--loss)"' : "";
  var cons =
    '<tr><td>Revenue</td><td class="num">' + lira(totRev) + "</td></tr>" +
    '<tr><td>Cost of sales</td><td class="num">' + paren(totRev - totGross) + "</td></tr>" +
    '<tr style="font-weight:700"><td>Gross profit</td><td class="num">' + lira(totGross) + "</td></tr>" +
    '<tr><td>Gross margin %</td><td class="num">' + pc(totGross, totRev).toFixed(1) + "%</td></tr>" +
    '<tr><td>Operating overhead</td><td class="num">' + paren(overhead) + "</td></tr>" +
    '<tr style="font-weight:700"><td>Net profit</td><td class="num"' + nls0 + ">" + lira(net) + "</td></tr>" +
    '<tr><td>Net margin %</td><td class="num"' + nls0 + ">" + pc(net, totRev).toFixed(1) + "%</td></tr>";
  document.getElementById("cons-tbody").innerHTML = cons;

  var thead = '<tr><th>P&amp;L</th>';
  DIVS.forEach(function (d) { thead += '<th class="num">' + d + "</th>"; });
  thead += '<th class="num">Total</th></tr>';
  document.getElementById("pl-thead").innerHTML = thead;

  var body = "";
  // Revenue
  body += "<tr><td>Revenue</td>";
  DIVS.forEach(function (d) { body += '<td class="num">' + lira(per[d].rev) + "</td>"; });
  body += '<td class="num">' + lira(totRev) + "</td></tr>";
  // Cost of sales
  body += "<tr><td>Cost of sales</td>";
  DIVS.forEach(function (d) { body += '<td class="num">' + paren(per[d].cogs) + "</td>"; });
  body += '<td class="num">' + paren(totRev - totGross) + "</td></tr>";
  // Gross profit (bold, red where negative)
  body += '<tr style="font-weight:700"><td>Gross profit</td>';
  DIVS.forEach(function (d) {
    var ls = per[d].gross < 0 ? ' style="color:var(--loss)"' : "";
    body += '<td class="num"' + ls + ">" + lira(per[d].gross) + "</td>";
  });
  body += '<td class="num">' + lira(totGross) + "</td></tr>";
  // Gross margin %
  body += "<tr><td>Gross margin %</td>";
  DIVS.forEach(function (d) {
    body += '<td class="num">' + pc(per[d].gross, per[d].rev).toFixed(1) + "%</td>";
  });
  body += '<td class="num">' + pc(totGross, totRev).toFixed(1) + "%</td></tr>";
  // spacer
  body += '<tr><td colspan="' + ncols + '" style="border:0;padding:6px 0"></td></tr>';
  // Operating overhead (shared pool, total only)
  body += "<tr><td>Operating overhead <em>(shared)</em></td>";
  DIVS.forEach(function () { body += '<td class="num">—</td>'; });
  body += '<td class="num">' + paren(overhead) + "</td></tr>";
  // Net profit (bold, total only)
  body += '<tr style="font-weight:700"><td>Net profit</td>';
  DIVS.forEach(function () { body += '<td class="num">—</td>'; });
  var nls = net < 0 ? ' style="color:var(--loss)"' : "";
  body += '<td class="num"' + nls + ">" + lira(net) + "</td></tr>";

  document.getElementById("pl-tbody").innerHTML = body;

  setTxt("k-rev", lira(totRev));
  setTxt("k-gross", lira(totGross));
  setTxt("k-oh", lira(overhead));
  setTxt("k-net", lira(net));
  setTxt("k-net-pct", pc(net, totRev).toFixed(1) + "% of rev");
  var ne = document.getElementById("k-net");
  if (ne) ne.style.color = net < 0 ? "var(--loss)" : "";

  // "what's profitable / what's not" read
  var ranked = DIVS.slice().sort(function (a, b) { return per[b].gross - per[a].gross; });
  var best = ranked[0], worst = ranked[ranked.length - 1];
  var losers = DIVS.filter(function (d) { return per[d].gross < 0; });
  var showR = per["New cars"].rev + per["Used cars"].rev;
  var showG = per["New cars"].gross + per["Used cars"].gross;
  var aftR = per["Service"].rev + per["Parts"].rev;
  var aftG = per["Service"].gross + per["Parts"].gross;

  var msg =
    "Biggest profit engine: " + best + " (" + lira(per[best].gross) + ", " +
    pc(per[best].gross, totGross).toFixed(0) + "% of all gross). Weakest: " +
    worst + " (" + pc(per[worst].gross, per[worst].rev).toFixed(1) + "% margin). ";
  if (losers.length) {
    msg += "Loss-making at gross level: " + losers.join(", ") + ". ";
  }
  msg +=
    "Showroom (new + used) is " + pc(showR, totRev).toFixed(0) +
    "% of revenue but only " + pc(showG, totGross).toFixed(0) +
    "% of gross; aftersales (service + parts) is " + pc(aftR, totRev).toFixed(0) +
    "% of revenue but " + pc(aftG, totGross).toFixed(0) +
    "% of gross — a service business with a showroom attached.";
  setTxt("pl-insight", msg);
}

buildInputs();
recompute();
