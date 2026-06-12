// Mobile navigation toggle
const toggle = document.querySelector(".nav-toggle");
const links = document.querySelector(".nav-links");
if (toggle && links) {
  toggle.addEventListener("click", () => {
    links.classList.toggle("open");
    const expanded = links.classList.contains("open");
    toggle.setAttribute("aria-expanded", String(expanded));
  });
}

// Sticky header: add depth (shadow) once the page is scrolled
const header = document.querySelector(".site-header");
if (header) {
  const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}

// Filter tabs on the tools grid (Zoom-style category switcher)
const ftabs = document.querySelectorAll(".ftab");
if (ftabs.length) {
  const cards = document.querySelectorAll("#tools-grid .card");
  ftabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      ftabs.forEach((t) => {
        t.classList.toggle("on", t === tab);
        t.setAttribute("aria-selected", String(t === tab));
      });
      const filter = tab.dataset.filter;
      cards.forEach((card) => {
        card.classList.toggle("f-hide", filter !== "all" && card.dataset.cat !== filter);
      });
      // Layout changed — let GSAP recalculate scroll-reveal positions
      if (window.ScrollTrigger) window.ScrollTrigger.refresh();
    });
  });
}

// Cursor spotlight on cards: track the mouse position per card (CSS does the rest)
document.querySelectorAll(".card").forEach((card) => {
  card.addEventListener("pointermove", (e) => {
    const r = card.getBoundingClientRect();
    card.style.setProperty("--mx", e.clientX - r.left + "px");
    card.style.setProperty("--my", e.clientY - r.top + "px");
  });
});

// Stories carousel: arrows, dots, auto-advance (pauses on hover/focus)
const stories = document.querySelector(".stories");
if (stories) {
  const track = stories.querySelector(".stories-track");
  const slides = stories.querySelectorAll(".story");
  const dotsBox = stories.querySelector(".story-dots");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let current = 0;
  let timer = null;

  slides.forEach((_, i) => {
    const dot = document.createElement("button");
    dot.className = "story-dot" + (i === 0 ? " on" : "");
    dot.setAttribute("aria-label", "Story " + (i + 1));
    dot.addEventListener("click", () => go(i));
    dotsBox.appendChild(dot);
  });
  const dots = dotsBox.querySelectorAll(".story-dot");

  function go(i) {
    current = (i + slides.length) % slides.length;
    track.style.transform = "translateX(-" + current * 100 + "%)";
    dots.forEach((d, j) => d.classList.toggle("on", j === current));
    // Play only the visible demo video; pause the rest to save battery/data
    slides.forEach((s, j) => {
      const v = s.querySelector("video");
      if (!v) return;
      if (j === current) { v.play().catch(() => {}); } else { v.pause(); }
    });
  }
  go(0);

  stories.querySelectorAll(".story-arrow").forEach((btn) => {
    btn.addEventListener("click", () => go(current + Number(btn.dataset.dir)));
  });

  // Auto-advance every 14s (long enough to watch a demo clip);
  // pauses while the visitor is reading or tabbing through
  if (!reduceMotion) {
    const start = () => { timer = setInterval(() => go(current + 1), 14000); };
    const stop = () => { clearInterval(timer); };
    start();
    stories.addEventListener("mouseenter", stop);
    stories.addEventListener("mouseleave", start);
    stories.addEventListener("focusin", stop);
    stories.addEventListener("focusout", start);
  }
}

// Video lightbox: click any demo preview to watch it large
let vlb = null;
function openLightbox(src) {
  if (!vlb) {
    vlb = document.createElement("div");
    vlb.className = "vlb";
    vlb.innerHTML =
      '<button class="vlb-close" aria-label="Close video">&times;</button>' +
      '<video controls playsinline></video>';
    document.body.appendChild(vlb);
    const close = () => {
      const v = vlb.querySelector("video");
      v.pause();
      v.removeAttribute("src");
      v.load();
      vlb.classList.remove("open");
      document.body.style.overflow = "";
    };
    vlb.addEventListener("click", (e) => {
      if (e.target === vlb || e.target.classList.contains("vlb-close")) close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && vlb.classList.contains("open")) close();
    });
  }
  const v = vlb.querySelector("video");
  v.src = src;
  vlb.classList.add("open");
  document.body.style.overflow = "hidden";
  v.play().catch(() => {});
}

// Card previews: float (auto-play) while visible on screen, click opens the lightbox.
// Visitors who prefer reduced motion get hover-to-play instead.
const previewReduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const cardMedias = document.querySelectorAll(".card-media");
cardMedias.forEach((media) => {
  const v = media.querySelector("video");
  if (!v) return;
  media.addEventListener("click", () => openLightbox(media.dataset.demo || v.src));
  v.addEventListener("play", () => media.classList.add("playing"));
  v.addEventListener("pause", () => media.classList.remove("playing"));
  if (previewReduceMotion) {
    media.addEventListener("mouseenter", () => { v.play().catch(() => {}); });
    media.addEventListener("mouseleave", () => { v.pause(); });
  }
});
// Floating hero data cards: click glides down to the flagship tools
document.querySelectorAll(".hero-float").forEach((f) => {
  f.addEventListener("click", () => {
    const target = document.querySelector("#flagships");
    if (target) target.scrollIntoView({ behavior: "smooth" });
  });
});

if (!previewReduceMotion && cardMedias.length && "IntersectionObserver" in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const v = entry.target.querySelector("video");
      if (!v) return;
      if (entry.isIntersecting) { v.play().catch(() => {}); } else { v.pause(); }
    });
  }, { threshold: 0.35 });
  cardMedias.forEach((m) => io.observe(m));
}

// Carousel videos open the lightbox too
document.querySelectorAll(".story-video").forEach((v) => {
  v.addEventListener("click", () => openLightbox(v.getAttribute("src")));
});

// Live market pulse: real numbers from the site's own data pipelines.
// rates.json = TCMB/TÜİK/ECB (refreshed daily by a GitHub Action);
// us.json on the finance-tools site = FRED producer prices (monthly).
(async function buildPulse() {
  const el = document.getElementById("pulse");
  if (!el) return;
  const hide = () => { const s = el.closest("section"); if (s) s.style.display = "none"; };
  try {
    const r = await (await fetch("rates.json", { cache: "no-store" })).json();
    const chips = [];
    const fx = r.fx || {};
    const m = r.market || {};
    if (fx.USDTRY) chips.push({ v: fx.USDTRY.toFixed(2), l: "USD / TRY", s: "ECB · " + (r.fxAsof || ""), h: "assetix.html" });
    if (fx.EURTRY) chips.push({ v: fx.EURTRY.toFixed(2), l: "EUR / TRY", s: "ECB · " + (r.fxAsof || ""), h: "assetix.html" });
    if (r.rate && r.rate.value != null) chips.push({ v: r.rate.value.toFixed(1) + "%", l: "TCMB policy rate", s: "TCMB · " + (r.rate.asof || ""), h: "assetix.html" });
    if (m.deposit) chips.push({ v: m.deposit.value.toFixed(1) + "%", l: "TL deposit rate", s: "TCMB · " + m.deposit.asof, h: "assetix.html" });
    if (m.tufe) chips.push({ v: "+" + m.tufe.yoy.toFixed(1) + "%", l: "TR inflation · CPI YoY", s: "TÜİK · " + m.tufe.asof, h: "assetix.html" });
    if (m.kfe_tr) chips.push({ v: "+" + m.kfe_tr.yoy.toFixed(1) + "%", l: "TR house prices · YoY", s: "TCMB KFE · " + m.kfe_tr.asof, h: "assetix.html" });
    try {
      const us = await (await fetch("https://namikakmandev.github.io/commercial-finance-tools/data/us.json", { cache: "no-store" })).json();
      const steel = (us.buckets || []).find((b) => b.id === "us_steel");
      if (steel && steel.series && steel.series.length >= 13) {
        const n = steel.series.length;
        const yoy = (steel.series[n - 1] / steel.series[n - 13] - 1) * 100;
        chips.push({ v: (yoy >= 0 ? "+" : "") + yoy.toFixed(1) + "%", l: "US steel PPI · YoY", s: "FRED · " + (us.last_updated || ""), h: "https://namikakmandev.github.io/commercial-finance-tools/" });
      }
    } catch (e) { /* FRED chip is optional */ }
    if (!chips.length) return hide();
    el.innerHTML = chips.map((c) =>
      '<a class="pulse-chip" href="' + c.h + '"><strong>' + c.v + "</strong><span>" + c.l + "</span><em>" + c.s + "</em></a>"
    ).join("");
  } catch (e) { hide(); }
})();

// Auto-update footer year
const yearEl = document.querySelector("[data-year]");
if (yearEl) yearEl.textContent = new Date().getFullYear();

// Contact form: no backend yet, so guide the user
const form = document.querySelector("#contact-form");
if (form) {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const status = document.querySelector("#form-status");
    if (status) {
      status.textContent =
        "Thanks! This form isn't connected yet — please reach me via LinkedIn for now.";
      status.style.color = "var(--accent)";
    }
    form.reset();
  });
}
