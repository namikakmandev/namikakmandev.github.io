/* Fridge Tracker service worker.
   Scope is /fridge/ only — it never touches the rest of the site.
   Strategy: stale-while-revalidate. The kitchen copy opens instantly and
   works with no signal; a newer version is fetched in the background and
   picked up on the next launch. */

const CACHE = "fridge-v1";
const SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon.svg",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-maskable-512.png",
  "./icon-180.png"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())   // a missing optional asset must not block install
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if(req.method !== "GET") return;
  if(new URL(req.url).origin !== self.location.origin) return;

  e.respondWith(
    caches.open(CACHE).then(async cache => {
      const cached = await cache.match(req, { ignoreSearch:true });
      const network = fetch(req).then(res => {
        if(res && res.ok) cache.put(req, res.clone());
        return res;
      }).catch(() => null);

      if(cached) return cached;
      const res = await network;
      if(res) return res;
      // offline and never cached: fall back to the app shell for navigations
      return (req.mode === "navigate" ? cache.match("./index.html") : undefined)
        || new Response("", { status:504, statusText:"Offline" });
    })
  );
});
