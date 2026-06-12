/**
 * Service Worker — Portal Campo PWA
 * Offline: SQLite WASM via OPFS (quando online, network-first; quando offline, serve do SQLite local)
 * Sync: drena sync_queue ao reconectar
 */
const CACHE_NAME = 'campo-v2';
const STATIC_CACHE = [
  '/static/campo_pwa/pwa.js',
  '/static/campo_pwa/offline-db.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
];

// ─── Instalação ────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_CACHE).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ─── Estratégia de fetch ───────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Estáticos CDN/static: cache-first
  if (!url.pathname.startsWith('/portal/campo/')) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Portal campo: network-first com fallback para cache HTML
  if (request.method === 'GET') {
    event.respondWith(networkFirstPortal(request));
    return;
  }

  // POSTs (iniciar/executar/concluir OS): quando offline enfileira no SQLite
  if (request.method === 'POST') {
    event.respondWith(postWithOfflineQueue(request));
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const resp = await fetch(request);
    if (resp.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, resp.clone());
    }
    return resp;
  } catch (_) {
    return cached || new Response('Offline', { status: 503 });
  }
}

async function networkFirstPortal(request) {
  try {
    const resp = await fetch(request);
    if (resp.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, resp.clone());
    }
    return resp;
  } catch (_) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return offlineFallbackPage();
  }
}

async function postWithOfflineQueue(request) {
  try {
    return await fetch(request);
  } catch (_) {
    // Offline: salva na sync_queue do SQLite WASM
    const cloned = request.clone();
    const url = request.url;
    let payload = {};
    try {
      const text = await cloned.text();
      payload = Object.fromEntries(new URLSearchParams(text).entries());
    } catch (_) {}

    await enqueueOffline(url, 'POST', payload);

    // Retorna resposta fake de sucesso para o service worker não quebrar a UI
    return new Response(JSON.stringify({ ok: true, offline: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

function offlineFallbackPage() {
  const html = `<!DOCTYPE html><html lang="pt-br"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Campo — Sem conexão</title>
    <style>
      body{font-family:system-ui;background:#f0f4f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
      .box{text-align:center;padding:2rem;background:#fff;border-radius:1rem;box-shadow:0 4px 24px rgba(0,0,0,.1)}
      h2{color:#1a6e3c}p{color:#666}
    </style>
  </head><body><div class="box">
    <h2>📶 Sem conexão</h2>
    <p>Você está offline. Os dados salvos localmente continuam disponíveis.<br>
    Quando a conexão voltar, tudo será sincronizado automaticamente.</p>
    <button onclick="location.reload()" style="background:#1a6e3c;color:#fff;border:none;padding:.75rem 2rem;border-radius:2rem;cursor:pointer;font-size:1rem">Tentar novamente</button>
  </div></body></html>`;
  return new Response(html, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

// ─── SQLite WASM helpers (chamados pelo SW) ─────────────────────────────────
// O SW não pode importar módulos ES diretamente em todos os navegadores,
// então usamos um canal de mensagens com o cliente para operar no banco.
// A operação real acontece em offline-db.js carregado na página.

async function enqueueOffline(endpoint, method, payload) {
  const clients = await self.clients.matchAll();
  for (const client of clients) {
    client.postMessage({
      type: 'OFFLINE_ENQUEUE',
      endpoint,
      method,
      payload,
    });
  }
}

// ─── Sincronização quando volta online ────────────────────────────────────
self.addEventListener('message', async event => {
  if (event.data && event.data.type === 'SYNC_QUEUE') {
    // Cliente envia a fila; SW processa e notifica resultado
    const { queue, csrfToken } = event.data;
    const results = [];

    for (const item of queue) {
      try {
        const resp = await fetch(item.endpoint, {
          method: item.method,
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
          },
          body: new URLSearchParams(item.payload).toString(),
        });
        results.push({ id: item.id, ok: resp.ok, status: resp.status });
      } catch (_) {
        results.push({ id: item.id, ok: false, error: 'network' });
      }
    }

    event.source.postMessage({ type: 'SYNC_RESULT', results });
  }
});

// ─── Push notifications ───────────────────────────────────────────────────
self.addEventListener('push', event => {
  let data = { title: 'Nova OS no Campo', body: 'Você tem uma nova Ordem de Serviço.', url: '/portal/campo/' };
  try { data = Object.assign(data, event.data.json()); } catch (_) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/img/logo.png',
      badge: '/static/img/logo.png',
      tag: 'campo-os',
      data: { url: data.url },
      vibrate: [200, 100, 200],
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/portal/campo/';
  event.waitUntil(clients.openWindow(url));
});
