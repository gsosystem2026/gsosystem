{% load static %}
const APP_VERSION = "{{ app_version|default:'1.0' }}";
const SHELL_CACHE = `gso-shell-${APP_VERSION}`;
const RUNTIME_CACHE = `gso-runtime-${APP_VERSION}`;
const OFFLINE_URL = "/offline/";

const SHELL_URLS = [
  OFFLINE_URL,
  "/accounts/staff/task-management/",
  "/accounts/staff/task-history/",
  "{% static 'css/tailwind.css' %}",
  "{% static 'js/personnel_offline_sync.js' %}",
  "{% static 'img/logo/gso_logo.png' %}"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== SHELL_CACHE && key !== RUNTIME_CACHE)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

function isNavigationRequest(request) {
  return request.mode === "navigate";
}

function isStaticAsset(requestUrl) {
  return requestUrl.pathname.startsWith("/static/");
}

function isPersonnelPage(requestUrl) {
  return requestUrl.pathname.startsWith("/accounts/staff/task-management/")
    || requestUrl.pathname.startsWith("/accounts/staff/task-history/")
    || /\/accounts\/staff\/request-management\/\d+\/$/.test(requestUrl.pathname);
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          const cloned = response.clone();
          caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, cloned));
          return response;
        });
      })
    );
    return;
  }

  if (isNavigationRequest(request) || isPersonnelPage(url)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const cloned = response.clone();
          caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, cloned));
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => {
            if (cached) return cached;
            return caches.match(OFFLINE_URL);
          })
        )
    );
  }
});
