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
