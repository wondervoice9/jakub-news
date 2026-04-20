// Service worker for offline app shell. Does NOT cache data.json or
// cot_gold.json (always fresh).
const VERSION = "v16-sell-buy-verdict";
const CACHE = `jakub-news-${VERSION}`;
const SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./storage.js",
  "./weather.js",
  "./weather-bg.js",
  "./cot.js",
  "./manifest.webmanifest",
  "./icons/icon.svg",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  // Never cache data.json or cot_gold.json — always fetch fresh
  if (url.pathname.endsWith("/data.json") || url.pathname.endsWith("/cot_gold.json")) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }
  // App shell: cache-first
  if (url.origin === location.origin) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
