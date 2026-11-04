// My LibriVox Box service worker: keeps the app's own files so it opens offline.
// Bump VERSION whenever you upload a new index.html so phones pick up the update.
const VERSION = 'my-librivox-box-v12';
const FILES = ['./', './index.html', './app.webmanifest',
               './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', e => {
  // cache: 'reload' skips the browser's HTTP cache, so a fresh upload is what gets stored
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES.map(f => new Request(f, {cache: 'reload'})))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// only the app's own files are handled here; LibriVox, Internet Archive and audio requests go straight to the network
self.addEventListener('fetch', e => {
  if(e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.open(VERSION).then(async cache => {
    const hit = await cache.match(e.request, {ignoreSearch: true});
    const path = new URL(e.request.url).pathname;
    if(e.request.mode === 'navigate' || path.endsWith('.webmanifest') || path.endsWith('/sw.js')){
      try{ const r = await fetch(e.request, {cache: 'no-cache'}); if(r.ok) cache.put(e.request, r.clone()); return r; }
      catch(err){ return hit || cache.match('./index.html'); }
    }
    const fresh = fetch(e.request).then(r => { if(r.ok) cache.put(e.request, r.clone()); return r; }).catch(() => null);
    return hit || (await fresh) || (e.request.mode === 'navigate' ? cache.match('./index.html') : Response.error());
  }));
});
