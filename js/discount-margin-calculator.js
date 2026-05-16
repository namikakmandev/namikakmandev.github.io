// ---- Discount & Margin Calculator ----
// Universal: works in any currency, runs entirely in the browser.

const $ = (id) => document.getElementById(id);
const IDS = ["dm-price", "dm-cost", "dm-disc", "dm-units"];

function num(id) {
  const v = parseFloat($(id).value);
  return isNaN(v) ? 0 : v;
}

function money(n, sym) {
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  const s = abs.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return sign + (sym ? sym + " " : "") + s;
}

function pctTxt(n) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 }) + "%";
}

function compute() {
  const price = num("dm-price");
  const cost = num("dm-cost");
  const disc = Math.min(100, Math.max(0, num("dm-disc")));
  const units = num("dm-units");

  const net = price * (1 - disc / 100);
  const mBefore = price - cost;
  const mAfter = net - cost;
  const mBeforePct = price > 0 ? (mBefore / price) * 100 : 0;
  const mAfterPct = net > 0 ? (mAfter / net) * 100 : 0;

  // Extra unit volume needed to keep the SAME total profit after the discount.
  let extraPct = null; // null = cannot break even (selling at/below cost)
  if (mAfter > 0 && mBefore > 0) {
    extraPct = (mBefore / mAfter - 1) * 100;
  }

  return {
    price, cost, disc, units, net,
    mBefore, mAfter, mBeforePct, mAfterPct, extraPct,
  };
}

function drawChart(r, sym, factor) {
  const W = 720, H = 360, mT = 38, mB = 54, mL = 56, mR = 24;
  const pw = W - mL - mR, ph = H - mT - mB;

  const cost = r.cost * factor;
  const priceB = r.price * factor;     // selling price before discount
  const priceA = r.net * factor;       // selling price after discount
  const profB = r.mBefore * factor;
  const profA = r.mAfter * factor;

  const maxV = Math.max(priceB, priceA, cost, 1);
  const Y = (v) => mT + ph - (v / maxV) * ph;   // 0 at the bottom
  const y0 = Y(0);

  const bw = 150;
  const x1 = mL + pw * 0.24 - bw / 2;
  const x2 = mL + pw * 0.72 - bw / 2;
  const cx1 = x1 + bw / 2, cx2 = x2 + bw / 2;

  const seg = (x, vTop, vBot, color) =>
    `<rect x="${x.toFixed(1)}" y="${Y(vTop).toFixed(1)}" width="${bw}" ` +
    `height="${Math.max(1, Y(vBot) - Y(vTop)).toFixed(1)}" style="fill:${color}"/>`;

  const stack = (x, price, profit, profColor, label) => {
    let g = "";
    // grey block = the price you BUY it for (cost)
    g += seg(x, Math.min(cost, Math.max(price, 0)), 0, "var(--text-dim)");
    if (price >= cost) {
      g += seg(x, price, cost, profColor);                 // profit on top
    } else {
      g += seg(x, cost, Math.max(price, 0), "var(--accent-3)"); // red = loss zone
    }
    const topV = Math.max(price, cost);
    g += `<text x="${(x + bw / 2).toFixed(1)}" y="${(Y(topV) - 12).toFixed(1)}" ` +
      `text-anchor="middle" class="cp-ax" style="font-weight:700;font-size:17px">` +
      `sell ${money(price, sym)}</text>`;
    const mid = (Math.max(price, cost) + Math.min(price, cost)) / 2;
    g += `<text x="${(x + bw / 2).toFixed(1)}" y="${(Y(mid) + 5).toFixed(1)}" ` +
      `text-anchor="middle" class="cp-ax" style="font-size:13px;fill:#fff;font-weight:600">` +
      `${profit >= 0 ? "profit " : "loss "}${money(profit, sym)}</text>`;
    g += `<text x="${(x + bw / 2).toFixed(1)}" y="${(H - 24).toFixed(1)}" ` +
      `text-anchor="middle" class="cp-ax" style="font-size:15px">${label}</text>`;
    return g;
  };

  let s = "";
  s += `<line x1="${mL}" y1="${y0.toFixed(1)}" x2="${(W - mR).toFixed(1)}" y2="${y0.toFixed(1)}" stroke="var(--border)"/>`;
  s += stack(x1, priceB, profB, "var(--accent)", "Before discount");
  s += stack(x2, priceA, profA, profA < 0 ? "var(--accent-3)" : "var(--accent-2)", "After discount");

  // dotted horizontal line = the price you buy it for
  const yc = Y(cost);
  s += `<line x1="${mL}" y1="${yc.toFixed(1)}" x2="${(W - mR).toFixed(1)}" y2="${yc.toFixed(1)}" ` +
    `stroke="var(--text)" stroke-width="1.5" stroke-dasharray="5 4" opacity="0.7"/>`;
  s += `<text x="${(W - mR).toFixed(1)}" y="${(yc - 8).toFixed(1)}" text-anchor="end" ` +
    `class="cp-ax" style="font-size:13px">You buy it for ${money(cost, sym)}</text>`;

  // dotted connector between the two bar tops = the price drop
  s += `<line x1="${cx1.toFixed(1)}" y1="${Y(priceB).toFixed(1)}" ` +
    `x2="${cx2.toFixed(1)}" y2="${Y(priceA).toFixed(1)}" stroke="var(--accent-3)" ` +
    `stroke-width="2" stroke-dasharray="6 4"/>`;
  s += `<circle cx="${cx1.toFixed(1)}" cy="${Y(priceB).toFixed(1)}" r="4" fill="var(--accent-3)"/>`;
  s += `<circle cx="${cx2.toFixed(1)}" cy="${Y(priceA).toFixed(1)}" r="4" fill="var(--accent-3)"/>`;

  $("dm-svg").innerHTML = s;
}

function render() {
  const sym = $("dm-cur").value;
  const r = compute();

  $("dm-net").textContent = money(r.net, sym);
  $("dm-gmb").textContent = money(r.mBefore, sym);
  $("dm-gmb-pct").textContent = r.price > 0 ? "(" + pctTxt(r.mBeforePct) + ")" : "";
  $("dm-gma").textContent = money(r.mAfter, sym);
  $("dm-gma-pct").textContent = r.net > 0 ? "(" + pctTxt(r.mAfterPct) + ")" : "";

  const extraEl = $("dm-extra");
  const row = $("dm-extra-row");
  const msg = $("dm-msg");

  if (r.mAfter <= 0) {
    extraEl.textContent = "Impossible";
    extraEl.style.color = "var(--loss)";
    msg.textContent =
      "At this discount the price is at or below your cost — you lose money on every unit, so no amount of extra volume breaks even.";
    msg.style.color = "var(--loss)";
  } else if (r.extraPct === null || r.disc === 0) {
    extraEl.textContent = "+0%";
    extraEl.style.color = "var(--text)";
    msg.textContent = r.mBefore <= 0
      ? "Your price is already at or below cost before any discount."
      : "No discount applied — your margin is unchanged.";
    msg.style.color = "var(--text-dim)";
  } else {
    const profitCut = r.mBefore > 0 ? (1 - r.mAfter / r.mBefore) * 100 : 0;
    extraEl.textContent = "+" + pctTxt(r.extraPct);
    extraEl.style.color = "var(--accent-3)";
    let line =
      "A " + pctTxt(r.disc) + " discount cuts your per-unit profit by " +
      pctTxt(profitCut) + ". You must sell " + pctTxt(r.extraPct) +
      " more units just to make the same total profit.";
    if (r.units > 0) {
      const extraUnits = Math.ceil(r.units * (r.extraPct / 100));
      line += " On " + r.units.toLocaleString() + " units that is about " +
        extraUnits.toLocaleString() + " extra units.";
    }
    msg.textContent = line;
    msg.style.color = "var(--text-dim)";
  }
  row.style.borderColor = "";

  // Units → show TOTAL profit (margin × units) so the input visibly matters.
  const hasUnits = r.units > 0;
  const factor = hasUnits ? r.units : 1;

  $("dm-chart-title").textContent = hasUnits
    ? "Total profit on " + r.units.toLocaleString() +
      " units — before vs. after the discount"
    : "Profit per unit — before vs. after the discount";

  const totRow = $("dm-tot-row");
  if (hasUnits && r.mBefore > r.mAfter) {
    const totalBefore = r.mBefore * r.units;
    const totalAfter = r.mAfter * r.units;
    const lost = totalBefore - totalAfter;
    totRow.hidden = false;
    $("dm-tot").textContent = money(lost, sym);
    $("dm-tot").style.color = "var(--accent-3)";
    $("dm-tot-note").textContent =
      "(" + money(totalBefore, sym) + " → " + money(totalAfter, sym) + ")";
  } else {
    totRow.hidden = true;
  }

  drawChart(r, sym, factor);
}

IDS.forEach((id) => {
  const el = $(id);
  if (el) el.addEventListener("input", render);
});
$("dm-cur").addEventListener("change", render);

render();
