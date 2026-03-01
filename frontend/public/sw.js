const CACHE_NAME = "agent-ops-v1";
const OFFLINE_URL = "/offline.html";

const PRECACHE_URLS = ["/", "/offline.html"];

// Install — precache critical assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)),
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)),
        ),
      ),
  );
  self.clients.claim();
});

// Fetch — network-first with offline fallback
self.addEventListener("fetch", (event) => {
  // Skip non-GET, WebSocket, and API requests
  if (
    event.request.method !== "GET" ||
    event.request.url.includes("/api/") ||
    event.request.url.includes("/ws/") ||
    event.request.url.startsWith("chrome-extension://")
  ) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses for static assets
        if (
          response.ok &&
          event.request.url.match(/\.(js|css|png|svg|ico|woff2?)$/)
        ) {
          const clone = response.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(async () => {
        // Try cache first
        const cached = await caches.match(event.request);
        if (cached) return cached;

        // Navigation requests get offline page
        if (event.request.mode === "navigate") {
          const offlinePage = await caches.match(OFFLINE_URL);
          if (offlinePage) return offlinePage;
        }

        return new Response("Offline", { status: 503, statusText: "Offline" });
      }),
  );
});
