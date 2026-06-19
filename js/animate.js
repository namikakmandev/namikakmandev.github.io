// GSAP motion for the homepage — "quiet & premium" direction.
// Safe by design: if GSAP fails to load, or the visitor prefers reduced
// motion, NOTHING is hidden — the page (and the real stat numbers) show normally.
(function () {
  if (typeof window.gsap === "undefined") return;

  var reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;
  if (reduceMotion) return;

  gsap.registerPlugin(ScrollTrigger);

  // 1) Hero entrance — headline, paragraph, buttons, stat strip rise in calmly
  var heroBits = gsap.utils.toArray(
    ".hero h1, .hero p, .hero .btn, .hero-stats"
  );
  if (heroBits.length) {
    gsap.from(heroBits, {
      y: 22,
      opacity: 0,
      duration: 1.0,
      ease: "power3.out",
      stagger: 0.1,
    });
  }

  // 2) Count-up on the real credibility numbers (15+, 11).
  //    The final value is already in the HTML, so it's correct even without JS;
  //    here we briefly reset to 0 and count up when it scrolls into view.
  gsap.utils.toArray("[data-count]").forEach(function (el) {
    var end = parseInt(el.dataset.count, 10);
    var suffix = el.dataset.suffix || "";
    var obj = { v: 0 };
    ScrollTrigger.create({
      trigger: el,
      start: "top 92%",
      once: true,
      onEnter: function () {
        el.textContent = "0" + suffix;
        gsap.to(obj, {
          v: end,
          duration: 1.3,
          ease: "power2.out",
          onUpdate: function () {
            el.textContent = Math.round(obj.v) + suffix;
          },
        });
      },
    });
  });

  // 3) Section heading + intro reveal
  gsap.utils.toArray(".section-title, .section-sub").forEach(function (el) {
    gsap.from(el, {
      y: 20,
      opacity: 0,
      duration: 0.7,
      ease: "power2.out",
      scrollTrigger: { trigger: el, start: "top 88%" },
    });
  });

  // 4) Featured-work cards fade up as you reach them
  gsap.utils.toArray(".card").forEach(function (card) {
    gsap.from(card, {
      scrollTrigger: { trigger: card, start: "top 86%" },
      y: 30,
      opacity: 0,
      duration: 0.7,
      ease: "power2.out",
    });
  });
})();
