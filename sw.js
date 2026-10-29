// オフライン用のキャッシュ設定
// data.js や index.html を更新したら、CACHE_VERSION の数字を1つ上げてください。
// （上げないと、利用者の端末に古いデータが残ります）
const CACHE_VERSION = 3;
const CACHE = "kendaku-v" + CACHE_VERSION;
const FILES = [
  "./",
  "./index.html",
  "./data.js",
  "./manifest.webmanifest",
  "./icon.svg",
  "./icon-32.png",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-maskable-512.png",
  "./apple-touch-icon.png"
];

self.addEventListener("install", e => {
  // 1ファイルが見つからなくても、ほかのファイルはキャッシュする
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.all(FILES.map(f => c.add(f).catch(() => console.warn("キャッシュできません:", f)))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith("kendaku-") && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// アプリ本体とデータ：ネット優先（つながらなければキャッシュ）
// フォントなどその他：キャッシュ優先
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const isApp = url.origin === location.origin &&
    (req.mode === "navigate" || url.pathname.endsWith("/data.js") || url.pathname.endsWith(".html"));

  if (isApp) {
    e.respondWith(
      fetch(req)
        .then(res => { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res; })
        .catch(() => caches.match(req).then(r => r || caches.match("./index.html")))
    );
    return;
  }
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }))
  );
});
