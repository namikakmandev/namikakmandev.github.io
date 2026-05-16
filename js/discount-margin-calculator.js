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
  const W = 720, H = 360, mT = 30, mB = 54, mL = 60, mR = 20;
  const pw = W - mL - mR, ph = H - mT - mB;
  const before = r.mBefore * factor, after = r.mAfter * factor;
  const vals = [before, after];
  const maxV = Math.max(...vals, 1);
  const minV = Math.min(...vals, 0);
  const span = maxV - minV || 1;
  const Y = (v) => mT + ph - ((v - minV) / span) * ph;
  const y0 = Y(0);

  const bw = 150;
  const x1 = mL + pw * 0.22 - bw / 2;
  const x2 = mL + pw * 0.7 - bw / 2;

  const bar = (x, v, color, label) => {
    const top = Math.min(Y(v), y0);
    const h = Math.abs(Y(v) - y0);
    return (
      `<rect x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${bw}" ` +
      `height="${Math.max(1, h).toFixed(1)}" rx="6" style="fill:${color}"/>` +
      `<text x="${(x + bw / 2).toFixed(1)}" y="${(v >= 0 ? top - 10 : top + h + 22).toFixed(1)}" ` +
      `text-anchor="middle" class="cp-ax" style="font-weight:700;font-size:18px">` +
      `${money(v, sym)}</text>` +
      `<text x="${(x + bw / 2).toFixed(1)}" y="${(H - 24).toFixed(1)}" ` +
      `text-anchor="middle" class="cp-ax" style="font-size:15px">${label}</text>`
    );
  };

  let s = "";
  s += `<line x1="${mL}" y1="${y0.toFixed(1)}" x2="${(W - mR).toFixed(1)}" y2="${y0.toFixed(1)}" stroke="var(--border)"/>`;
  s += bar(x1, before, "var(--accent)", "Before discount");
  s += bar(x2, after, after < 0 ? "var(--accent-3)" : "var(--accent-2)", "After discount");
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
