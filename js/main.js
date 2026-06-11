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
