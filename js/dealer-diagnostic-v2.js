// Divisional & Monthly P&L — multi-industry, from a trial balance.

var INDUSTRIES = {
  auto: {
    label: "Auto dealer",
    note: "Full-service car dealer — thin metal margin, profit really in service & parts.",
    divisions: ["New cars", "Used cars", "Service", "Parts", "F&I", "Rental"],
    seasonality: [80, 80, 95, 100, 105, 100, 85, 80, 95, 105, 100, 75],
    tb: [
      { code: "600.01", name: "New car sales",            div: "New cars",  kind: "rev",  amount: 18000000 },
      { code: "600.02", name: "Used car sales",           div: "Used cars", kind: "rev",  amount: 9000000 },
      { code: "600.03", name: "Service & repair revenue", div: "Service",   kind: "rev",  amount: 2400000 },
      { code: "600.04", name: "Parts sales",              div: "Parts",     kind: "rev",  amount: 1800000 },
      { code: "600.05", name: "F&I / commission income",  div: "F&I",       kind: "rev",  amount: 600000 },
      { code: "600.06", name: "Rental income",            div: "Rental",    kind: "rev",  amount: 700000 },
      { code: "620.01", name: "New car cost of sales",    div: "New cars",  kind: "cogs", amount: 17100000 },
      { code: "620.02", name: "Used car cost of sales",   div: "Used cars", kind: "cogs", amount: 8100000 },
      { code: "620.03", name: "Service direct cost",      div: "Service",   kind: "cogs", amount: 840000 },
      { code: "620.04", name: "Parts cost of sales",      div: "Parts",     kind: "cogs", amount: 1350000 },
      { code: "620.05", name: "F&I direct cost",          div: "F&I",       kind: "cogs", amount: 60000 },
      { code: "620.06", name: "Rental direct cost",       div: "Rental",    kind: "cogs", amount: 490000 },
      { code: "760.00", name: "Marketing & selling exp.", div: "Overhead",  kind: "opex", amount: 1500000 },
      { code: "770.00", name: "General admin expense",    div: "Overhead",  kind: "opex", amount: 2400000 },
    ],
  },
  manufacturing: {
    label: "Manufacturing",
    note: "Machine builder — the aftermarket (spare parts & service) carries the margin.",
    divisions: ["Machines", "Spare parts", "Service & install", "Engineering"],
    seasonality: [85, 90, 100, 100, 105, 100, 80, 70, 100, 110, 105, 55],
    tb: [
      { code: "600.01", name: "Machine sales",            div: "Machines",          kind: "rev",  amount: 24000000 },
      { code: "600.02", name: "Spare parts sales",        div: "Spare parts",       kind: "rev",  amount: 6000000 },
      { code: "600.03", name: "Service & installation",   div: "Service & install", kind: "rev",  amount: 4000000 },
      { code: "600.04", name: "Engineering projects",     div: "Engineering",       kind: "rev",  amount: 3000000 },
      { code: "620.01", name: "Machine COGS",             div: "Machines",          kind: "cogs", amount: 18000000 },
      { code: "620.02", name: "Spare parts COGS",         div: "Spare parts",       kind: "cogs", amount: 3600000 },
      { code: "620.03", name: "Service & install cost",   div: "Service & install", kind: "cogs", amount: 2000000 },
      { code: "620.04", name: "Engineering cost",         div: "Engineering",       kind: "cogs", amount: 2100000 },
      { code: "760.00", name: "Selling expense",          div: "Overhead",          kind: "opex", amount: 2500000 },
      { code: "770.00", name: "Administrative expense",   div: "Overhead",          kind: "opex", amount: 4000000 },
    ],
  },
  distribution: {
    label: "Distribution",
    note: "Wholesale distribution — very thin margins; small leakage moves the result.",
    divisions: ["Branded wholesale", "Generic wholesale", "Logistics", "Value-added"],
    seasonality: [90, 90, 95, 95, 100, 100, 95, 90, 100, 105, 105, 95],
    tb: [
      { code: "600.01", name: "Branded wholesale",        div: "Branded wholesale", kind: "rev",  amount: 40000000 },
      { code: "600.02", name: "Generic wholesale",        div: "Generic wholesale", kind: "rev",  amount: 18000000 },
      { code: "600.03", name: "Logistics services",       div: "Logistics",         kind: "rev",  amount: 5000000 },
      { code: "600.04", name: "Value-added services",     div: "Value-added",       kind: "rev",  amount: 2000000 },
      { code: "620.01", name: "Branded COGS",             div: "Branded wholesale", kind: "cogs", amount: 35200000 },
      { code: "620.02", name: "Generic COGS",             div: "Generic wholesale", kind: "cogs", amount: 16560000 },
      { code: "620.03", name: "Logistics cost",           div: "Logistics",         kind: "cogs", amount: 3500000 },
      { code: "620.04", name: "Value-added cost",         div: "Value-added",       kind: "cogs", amount: 1200000 },
      { code: "760.00", name: "Selling expense",          div: "Overhead",          kind: "opex", amount: 1800000 },
      { code: "770.00", name: "Administrative expense",   div: "Overhead",          kind: "opex", amount: 2400000 },
    ],
  },
  services: {
    label: "Services",
    note: "Professional services — labour-driven; utilisation and rate set the margin.",
    divisions: ["Consulting", "Managed services", "Training"],
    seasonality: [85, 90, 100, 95, 100, 90, 75, 70, 95, 105, 110, 85],
    tb: [
      { code: "600.01", name: "Consulting fees",          div: "Consulting",        kind: "rev",  amount: 12000000 },
      { code: "600.02", name: "Managed services revenue", div: "Managed services",  kind: "rev",  amount: 8000000 },
      { code: "600.03", name: "Training revenue",         div: "Training",          kind: "rev",  amount: 2500000 },
      { code: "620.01", name: "Consulting delivery cost", div: "Consulting",        kind: "cogs", amount: 6000000 },
      { code: "620.02", name: "Managed services cost",    div: "Managed services",  kind: "cogs", amount: 4000000 },
      { code: "620.03", name: "Training delivery cost",   div: "Training",          kind: "cogs", amount: 1000000 },
      { code: "760.00", name: "Selling expense",          div: "Overhead",          kind: "opex", amount: 1500000 },
      { code: "770.00", name: "Administrative expense",   div: "Overhead",          kind: "opex", amount: 3000000 },
    ],
  },
};

var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
var CUR = "auto";

function n(v) { var x = parseFloat(v); return isNaN(x) ? 0 : x; }
function getN(id) { var el = document.getElementById(id); return el ? n(el.value) : 0; }
function setTxt(id, t) { var el = document.getElementById(id); if (el) el.textContent = t; }
function lira(v) {
  var r = Math.round(v);
  return (r < 0 ? "-₺" : "₺") + Math.abs(r).toLocaleString("en-US");
}
function paren(v) { return "(" + lira(Math.abs(v)) + ")"; }
function pc(part, whole) { return whole ? (part / whole) * 100 : 0; }

function buildInputs() {
  var tbDef = INDUSTRIES[CUR].tb;
  var html = "";
  tbDef.forEach(function (a, i) {
    html +=
      '<div class="dd2-tbrow">' +
      '<label for="tb-' + i + '"><b>' + a.code + "</b> " + a.name +
      ' <span class="dd2-tag">' + a.div + "</span></label>" +
      '<input type="number" id="tb-' + i + '" step="10000" value="' + a.amount + '" />' +
      "</div>";
  });
  document.getElementById("tb-grid").innerHTML = html;
  document.querySelectorAll("#tb-grid input").forEach(function (el) {
    el.addEventListener("input", recompute);
  });
  setTxt("ind-note", INDUSTRIES[CUR].note);
}

function setIndustry(key) {
  if (!INDUSTRIES[key]) return;
  CUR = key;
  document.querySelectorAll("#ind-presets button").forEach(function (b) {
    b.classList.toggle("on", b.dataset.ind === key);
  });
  buildInputs();
  recompute();
}

function recompute() {
  var ind = INDUSTRIES[CUR];
  var DIVS = ind.divisions;
  var per = {};
  DIVS.forEach(function (d) { per[d] = { rev: 0, cogs: 0 }; });
  var overhead = 0;
  ind.tb.forEach(function (a, i) {
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
  var totCost = totRev - totGross;
  var net = totGross - overhead;
  var nls = net < 0 ? ' style="color:var(--loss)"' : "";

  // ---- Consolidated P&L ----
  document.getElementById("cons-tbody").innerHTML =
    '<tr><td>Revenue</td><td class="num">' + lira(totRev) + "</td></tr>" +
    '<tr><td>Cost of sales</td><td class="num">' + paren(totCost) + "</td></tr>" +
    '<tr style="font-weight:700"><td>Gross profit</td><td class="num">' + lira(totGross) + "</td></tr>" +
    '<tr><td>Gross margin %</td><td class="num">' + pc(totGross, totRev).toFixed(1) + "%</td></tr>" +
    '<tr><td>Operating overhead</td><td class="num">' + paren(overhead) + "</td></tr>" +
    '<tr style="font-weight:700"><td>Net profit</td><td class="num"' + nls + ">" + lira(net) + "</td></tr>" +
    '<tr><td>Net margin %</td><td class="num"' + nls + ">" + pc(net, totRev).toFixed(1) + "%</td></tr>";

  setTxt("k-rev", lira(totRev));
  setTxt("k-gross", lira(totGross));
  setTxt("k-oh", lira(overhead));
  setTxt("k-net", lira(net));
  setTxt("k-net-pct", pc(net, totRev).toFixed(1) + "% of rev");
  var ne = document.getElementById("k-net");
  if (ne) ne.style.color = net < 0 ? "var(--loss)" : "";

  // ---- 12-month P&L (seasonal revenue/cost, fixed overhead) ----
  var sumW = ind.seasonality.reduce(function (s, w) { return s + w; }, 0) || 1;
  var mh = '<tr><th>Monthly</th>';
  MONTHS.forEach(function (m) { mh += '<th class="num">' + m + "</th>"; });
  mh += '<th class="num">Total</th></tr>';
  document.getElementById("m-thead").innerHTML = mh;

  var rRev = "<tr><td>Revenue</td>", rCost = "<tr><td>Cost of sales</td>";
  var rGross = '<tr style="font-weight:700"><td>Gross profit</td>';
  var rOH = "<tr><td>Operating overhead</td>", rNet = '<tr style="font-weight:700"><td>Net profit</td>';
  var lossMonths = [];
  MONTHS.forEach(function (m, i) {
    var f = ind.seasonality[i] / sumW;
    var mRev = totRev * f, mGross = totGross * f, mCost = mRev - mGross;
    var mOH = overhead / 12, mNet = mGross - mOH;
    if (mNet < 0) lossMonths.push(m);
    var ls = mNet < 0 ? ' style="color:var(--loss)"' : "";
    rRev += '<td class="num">' + lira(mRev) + "</td>";
    rCost += '<td class="num">' + paren(mCost) + "</td>";
    rGross += '<td class="num">' + lira(mGross) + "</td>";
    rOH += '<td class="num">' + paren(mOH) + "</td>";
    rNet += '<td class="num"' + ls + ">" + lira(mNet) + "</td>";
  });
  rRev += '<td class="num">' + lira(totRev) + "</td></tr>";
  rCost += '<td class="num">' + paren(totCost) + "</td></tr>";
  rGross += '<td class="num">' + lira(totGross) + "</td></tr>";
  rOH += '<td class="num">' + paren(overhead) + "</td></tr>";
  rNet += '<td class="num"' + nls + ">" + lira(net) + "</td></tr>";
  document.getElementById("m-tbody").innerHTML = rRev + rCost + rGross + rOH + rNet;

  if (lossMonths.length) {
    setTxt(
      "m-insight",
      lossMonths.length + " month" + (lossMonths.length > 1 ? "s" : "") +
        " run at a loss (" + lossMonths.join(", ") +
        ") even though the year nets " + lira(net) +
        " — that is exactly when a low-margin business runs short of cash."
    );
  } else {
    setTxt("m-insight", "No month runs at a loss on this seasonality — but a sharper seasonal swing or a weaker year quickly changes that.");
  }

  // ---- Divisional P&L (vertical: lines down, divisions across) ----
  var th = '<tr><th>P&amp;L</th>';
  DIVS.forEach(function (d) { th += '<th class="num">' + d + "</th>"; });
  th += '<th class="num">Total</th></tr>';
  document.getElementById("pl-thead").innerHTML = th;

  var b = "<tr><td>Revenue</td>";
  DIVS.forEach(function (d) { b += '<td class="num">' + lira(per[d].rev) + "</td>"; });
  b += '<td class="num">' + lira(totRev) + "</td></tr>";
  b += "<tr><td>Cost of sales</td>";
  DIVS.forEach(function (d) { b += '<td class="num">' + paren(per[d].cogs) + "</td>"; });
  b += '<td class="num">' + paren(totCost) + "</td></tr>";
  b += '<tr style="font-weight:700"><td>Gross profit</td>';
  DIVS.forEach(function (d) {
    var ls = per[d].gross < 0 ? ' style="color:var(--loss)"' : "";
    b += '<td class="num"' + ls + ">" + lira(per[d].gross) + "</td>";
  });
  b += '<td class="num">' + lira(totGross) + "</td></tr>";
  b += "<tr><td>Gross margin %</td>";
  DIVS.forEach(function (d) { b += '<td class="num">' + pc(per[d].gross, per[d].rev).toFixed(1) + "%</td>"; });
  b += '<td class="num">' + pc(totGross, totRev).toFixed(1) + "%</td></tr>";
  b += '<tr><td colspan="' + (DIVS.length + 2) + '" style="border:0;padding:6px 0"></td></tr>';
  b += "<tr><td>Operating overhead <em>(shared)</em></td>";
  DIVS.forEach(function () { b += '<td class="num">—</td>'; });
  b += '<td class="num">' + paren(overhead) + "</td></tr>";
  b += '<tr style="font-weight:700"><td>Net profit</td>';
  DIVS.forEach(function () { b += '<td class="num">—</td>'; });
  b += '<td class="num"' + nls + ">" + lira(net) + "</td></tr>";
  document.getElementById("pl-tbody").innerHTML = b;

  // ranking read-out
  var ranked = DIVS.slice().sort(function (a, c) { return per[c].gross - per[a].gross; });
  var best = ranked[0], worst = ranked[ranked.length - 1];
  var losers = DIVS.filter(function (d) { return per[d].gross < 0; });
  var msg =
    "Biggest profit engine: " + best + " (" + lira(per[best].gross) + ", " +
    pc(per[best].gross, totGross).toFixed(0) + "% of all gross). Weakest: " +
    worst + " (" + pc(per[worst].gross, per[worst].rev).toFixed(1) + "% margin).";
  if (losers.length) msg += " Loss-making at gross level: " + losers.join(", ") + ".";
  setTxt("pl-insight", msg);
}

document.querySelectorAll("#ind-presets button").forEach(function (b) {
  b.addEventListener("click", function () { setIndustry(b.dataset.ind); });
});

buildInputs();
recompute();
