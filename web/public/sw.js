const CACHE = "sma-shell-0.16.0";
self.addEventListener("install", (event) =>
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await cache.addAll([
        "/",
        "/app-icon.png",
        "/manifest.webmanifest",
        "/icon-192.png",
        "/icon-512.png",
        "/fonts/Manrope-Regular.ttf",
        "/fonts/Manrope-Bold.ttf",
      ]);
      const html = await (await cache.match("/")).text();
      const assets = [
        ...html.matchAll(/(?:src|href)=["'](\/_next\/static\/[^"']+)["']/g),
      ].map((match) => match[1].replaceAll("&amp;", "&"));
      await cache.addAll([...new Set(assets)]);
      await self.skipWaiting();
    })(),
  ),
);
self.addEventListener("activate", (event) =>
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("sma-shell-") && key !== CACHE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  ),
);
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/")
  )
    return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/")));
    return;
  }
  if (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/fonts/") ||
    url.pathname.startsWith("/python/") ||
    url.pathname.startsWith("/python-runtime/") ||
    url.pathname === "/calculation-worker.js" ||
    url.pathname.startsWith("/logos/") ||
    url.pathname === "/app-icon.png"
  ) {
    event.respondWith(
      caches.match(event.request).then(
        (cached) =>
          cached ||
          fetch(event.request).then(async (response) => {
            if (response.ok) {
              const copy = response.clone();
              try {
                await (await caches.open(CACHE)).put(event.request, copy);
              } catch {}
            }
            return response;
          }),
      ),
    );
  }
});
self.addEventListener("push", (event) => {
  event.waitUntil(
    (async () => {
      let payload = {};
      try {
        payload = event.data?.json() || {};
      } catch {}
      const title =
        typeof payload.title === "string"
          ? payload.title.slice(0, 200)
          : "SMA Stock Analyzer";
      const body =
        typeof payload.body === "string"
          ? payload.body.slice(0, 1000)
          : "Open the app to review your saved lines.";
      await self.registration.showNotification(title, {
        body,
        icon: "/icon-192.png",
        badge: "/icon-192.png",
        tag: typeof payload.tag === "string" ? payload.tag : undefined,
        data: { url: "/#alerts" },
      });
    })(),
  );
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      for (const client of windows) {
        if (new URL(client.url).origin === self.location.origin) {
          await client.focus();
          client.postMessage({ type: "open-alerts" });
          return;
        }
      }
      await self.clients.openWindow("/#alerts");
    })(),
  );
});
