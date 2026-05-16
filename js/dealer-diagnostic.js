// Dealership Profit & Leakage Diagnostic — Stage 1: cross-division profit waterfall

function num(id) {
  const el = document.getElementById(id);
  if (!el) return 0;
  const v = parseFloat(el.value);
  return isNaN(v) || v < 0 ? 0 : v;
}

// €1,234,567  (no decimals — these are annual P&L figures)
function eur(n) {
  return "€" + Math.round(n).toLocaleString("en-US");
}
// Compact label for chart bars: €4.56M / €560k / €900
function eurShort(n) {
  const a = Math.abs(n);
  if (a >= 1e6) return "€" + (n / 1e6).toFixed(2) + "M";
  if (a >= 1e3) return "€" + Math.round(n / 1e3) + "k";
  return "€" + Math.round(n);
}
function pct(part, whole) {
  return whole > 0 ? (part / whole) * 100 : 0;
}
function setTxt(id, t) {
  const el = document.getElementById(id);
  if (el) el.textContent = t;
}

function model() {
  const div = [
    { key: "new",   label: "New cars",   rev: num("rev-new"),   gmPct: num("gm-new") },
    { key: "used",  label: "Used cars",  rev: num("rev-used"),  gmPct: num("gm-used") },
    { key: "svc",   label: "Service",    rev: num("rev-svc"),   gmPct: num("gm-svc") },
    { key: "parts", label: "Parts",      rev: num("rev-parts"), gmPct: num("gm-parts") },
    { key: "fi",    label: "F&I",        rev: num("rev-fi"),    gmPct: num("gm-fi") },
    { key: "rent",  label: "Rent-a-car", rev: num("rev-rent"),  gmPct: num("gm-rent") },
  ];
  div.forEach((d) => (d.gross = (d.rev * d.gmPct) / 100));
  const totalRev = div.reduce((s, d) => s + d.rev, 0);
  const totalGross = div.reduce((s, d) => s + d.gross, 0);
  const overhead = num("overhead");
  const net = totalGross - overhead;
  return { div, totalRev, totalGross, overhead, net };
}

function buildChart(m) {
  const svg = document.getElementById("dd-svg");
  const W = 960, H = 480, mL = 18, mR = 18, mT = 40, mB = 96;
  const plotW = W - mL - mR, plotH = H - mT - mB;

  const steps = [];
  m.div.forEach((d) => steps.push({ label: d.label, kind: "inc", delta: d.gross }));
  steps.push({ label: "Total gross", kind: "sub", value: m.totalGross, accent: "blue" });
  steps.push({ label: "Overhead", kind: "dec", delta: m.overhead });
  steps.push({
    label: "Net profit",
    kind: "total",
    value: m.net,
    accent: m.net < 0 ? "loss" : "green",
  });

  let run = 0;
  const bars = steps.map((s) => {
    let lo, hi;
    if (s.kind === "total" || s.kind === "sub") {
      lo = Math.min(0, s.value);
      hi = Math.max(0, s.value);
      run = s.value;
    } else if (s.kind === "dec") {
      const start = run;
      run = run - s.delta;
      lo = Math.min(start, run);
      hi = Math.max(start, run);
    } else {
      const start = run;
      run = run + s.delta;
      lo = Math.min(start, run);
      hi = Math.max(start, run);
    }
    return Object.assign({}, s, { lo: lo, hi: hi, top: run });
  });

  const maxV = Math.max(0, ...bars.map((b) => b.hi));
  const minV = Math.min(0, ...bars.map((b) => b.lo));
  const span = maxV - minV || 1;
  const y = (v) => mT + ((maxV - v) / span) * plotH;

  const n = steps.length;
  const slot = plotW / n;
  const bw = Math.min(70, slot * 0.62);
  const yz = y(0);
  let out =
    `<line x1="${mL}" y1="${yz.toFixed(1)}" x2="${W - mR}" y2="${yz.toFixed(
      1
    )}" stroke="var(--border)" stroke-width="1"/>`;

  bars.forEach((b, i) => {
    const cx = mL + slot * i + slot / 2;
    const x = cx - bw / 2;
    const yTop = y(b.hi);
    const yBot = y(b.lo);
    const h = Math.max(1, yBot - yTop);
    let fill;
    if (b.accent === "blue") fill = "var(--accent)";
    else if (b.accent === "green") fill = "var(--accent-2)";
    else if (b.accent === "loss") fill = "var(--loss)";
    else if (b.kind === "inc") fill = "var(--accent-2)";
    else if (b.kind === "sub" || b.kind === "total") fill = "var(--accent)";
    else fill = "var(--text-dim)";
    const op = b.kind === "dec" ? "0.55" : "1";
    out +=
      `<rect x="${x.toFixed(1)}" y="${yTop.toFixed(1)}" width="${bw.toFixed(
        1
      )}" height="${h.toFixed(1)}" rx="3" style="fill:${fill};opacity:${op}"/>`;

    const sign = b.kind === "dec" ? "−" : b.kind === "inc" ? "+" : "";
    const amount = b.kind === "dec" || b.kind === "inc" ? b.delta : b.value;
    out +=
      `<text x="${cx.toFixed(1)}" y="${(yTop - 8).toFixed(
        1
      )}" text-anchor="middle" class="wf-vlabel">${sign}${eurShort(
        amount
      )}</text>`;

    const ly = H - mB + 18;
    out +=
      `<text x="${cx.toFixed(1)}" y="${ly.toFixed(
        1
      )}" text-anchor="end" class="wf-clabel" transform="rotate(-35 ${cx.toFixed(
        1
      )} ${ly.toFixed(1)})">${b.label}</text>`;

    if (i < bars.length - 1) {
      const yr = y(b.top);
      const nx = mL + slot * (i + 1) + slot / 2 - bw / 2;
      out +=
        `<line x1="${(x + bw).toFixed(1)}" y1="${yr.toFixed(1)}" x2="${nx.toFixed(
          1
        )}" y2="${yr.toFixed(
          1
        )}" stroke="var(--text-dim)" stroke-width="1" stroke-dasharray="3 3" opacity="0.45"/>`;
    }
  });

  svg.innerHTML = out;
}

function render() {
  const m = model();
  setTxt("k-rev", eur(m.totalRev));
  setTxt("k-gross", eur(m.totalGross));
  setTxt("k-oh", eur(m.overhead));
  setTxt("k-net", eur(m.net));
  setTxt("k-net-pct", pct(m.net, m.totalRev).toFixed(1) + "% of rev");

  const netRow = document.getElementById("k-net");
  if (netRow) netRow.style.color = m.net < 0 ? "var(--loss)" : "";

  // The myth-buster line: showroom vs aftersales, revenue share vs gross share
  const salesRev = m.div[0].rev + m.div[1].rev;
  const salesGross = m.div[0].gross + m.div[1].gross;
  const aftRev = m.div[2].rev + m.div[3].rev;
  const aftGross = m.div[2].gross + m.div[3].gross;
  setTxt(
    "dd-insight",
    "Showroom (new + used) is " +
      pct(salesRev, m.totalRev).toFixed(0) +
      "% of revenue but only " +
      pct(salesGross, m.totalGross).toFixed(0) +
      "% of gross profit. Aftersales (service + parts) is just " +
      pct(aftRev, m.totalRev).toFixed(0) +
      "% of revenue but " +
      pct(aftGross, m.totalGross).toFixed(0) +
      "% of gross — this is a service business with a showroom attached."
  );

  buildChart(m);
}

const INPUTS = [
  "rev-new", "gm-new", "rev-used", "gm-used", "rev-svc", "gm-svc",
  "rev-parts", "gm-parts", "rev-fi", "gm-fi", "rev-rent", "gm-rent",
  "overhead",
];
INPUTS.forEach((id) => {
  const el = document.getElementById(id);
  if (el) el.addEventListener("input", render);
});

render();

// ---- Stage 2: true deal economics + discount slider ----
const discSlider = document.querySelector("#deal-disc-slider input[type=range]");
const discLabel = document.querySelector("#deal-disc-slider label b");

function renderDeal() {
  const sticker = num("deal-sticker");
  const cost = num("deal-cost");
  const prep = num("deal-prep");
  const fi = num("deal-fi");
  const svcYr = num("deal-svc");
  const years = num("deal-years");
  const ret = Math.min(100, num("deal-ret"));
  const disc = discSlider ? parseFloat(discSlider.value) : 0;

  const frontProfit = sticker - disc - cost - prep;
  const annuity = svcYr * years * (ret / 100);
  const ltv = frontProfit + fi + annuity;
  const frontBE = sticker - cost - prep; // discount where the car alone breaks even
  const ltvBE = frontBE + fi + annuity; // discount where the whole customer breaks even

  if (discLabel) discLabel.textContent = eur(disc);
  setTxt("d-front", eur(frontProfit));
  setTxt("d-fi", eur(fi));
  setTxt("d-svc", eur(annuity));
  setTxt("d-ltv", eur(ltv));

  const fEl = document.getElementById("d-front");
  if (fEl) fEl.style.color = frontProfit < 0 ? "var(--loss)" : "";
  const lEl = document.getElementById("d-ltv");
  if (lEl) lEl.style.color = ltv < 0 ? "var(--loss)" : "";

  let msg =
    "The car alone makes " +
    eur(frontProfit) +
    ". Add " +
    eur(fi) +
    " F&I and " +
    eur(annuity) +
    " of retained service, and the customer is really worth " +
    eur(ltv) +
    ". ";
  if (frontProfit < 0) {
    msg +=
      "At this discount the car itself loses " +
      eur(-frontProfit) +
      " — the deal only survives on F&I and service. ";
  } else {
    msg +=
      "Push the discount past " +
      eur(frontBE) +
      " and the car itself starts losing money — you would be betting the whole deal on F&I and service. ";
  }
  msg +=
    "The customer only turns unprofitable once the discount passes " +
    eur(ltvBE) +
    " — which is why discount policy must be tied to service retention, not set on the showroom floor alone.";
  setTxt("d-insight", msg);
}

["deal-sticker", "deal-cost", "deal-prep", "deal-fi", "deal-svc", "deal-years", "deal-ret"].forEach(
  (id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", renderDeal);
  }
);
if (discSlider) discSlider.addEventListener("input", renderDeal);

renderDeal();
