/* PWA bootstrap — registro do SW, prompt de instalação, push subscription, sync offline */
(function () {
  'use strict';

  let _db = null;

  /* 1. Registrar Service Worker */
  if ('serviceWorker' in navigator) {
    // SW servido como view Django em /portal/campo/sw.js com header Service-Worker-Allowed: /
    navigator.serviceWorker.register('/portal/campo/sw.js', { scope: '/portal/campo/' })
      .then(reg => {
        console.log('[PWA] SW registrado:', reg.scope);
        document.addEventListener('click', askNotificationOnce, { once: true });
      })
      .catch(err => console.warn('[PWA] Falha no SW:', err));
  }

  /* 2. Inicializar SQLite WASM offline */
  async function initOfflineDB() {
    try {
      const { default: CampoDB } = await import('/static/campo_pwa/offline-db.js');
      _db = await CampoDB.init();
      return _db;
    } catch (e) {
      console.warn('[PWA] SQLite WASM não disponível:', e.message);
      return null;
    }
  }

  /* 3. Enfileirar mutação offline quando SW notifica */
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', async event => {
      if (event.data && event.data.type === 'OFFLINE_ENQUEUE') {
        const db = _db || await initOfflineDB();
        if (db) {
          db.enqueueSync(event.data.endpoint, event.data.method, event.data.payload);
          console.log('[PWA] Enfileirado offline:', event.data.endpoint);
        }
      }
      if (event.data && event.data.type === 'SYNC_RESULT') {
        if (event.data.results && _db) {
          event.data.results.forEach(r => {
            if (r.ok) _db.removeSyncItem(r.id);
            else _db.incrementTentativas(r.id);
          });
        }
      }
    });
  }

  /* 4. Sincronizar fila quando volta online */
  window.addEventListener('online', () => processSyncQueue());

  async function processSyncQueue() {
    const db = _db || await initOfflineDB();
    if (!db) return;
    const queue = db.getSyncQueue();
    if (!queue.length) return;

    const csrfToken = getCookie('csrftoken');

    // Tenta via fetch direto primeiro (mais simples)
    const toRemove = [];
    for (const item of queue) {
      try {
        const resp = await fetch('/portal/campo/sync/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({ queue: [item] }),
        });
        const data = await resp.json();
        if (data.ok && data.results && data.results[0] && data.results[0].ok) {
          toRemove.push(item.id);
        } else {
          db.incrementTentativas(item.id);
        }
      } catch (_) {
        // Ainda offline, tenta depois
      }
    }
    toRemove.forEach(id => db.removeSyncItem(id));
    if (toRemove.length) console.log(`[PWA] Sincronizadas ${toRemove.length} mutações offline`);
  }

  // Tentar sync logo no carregamento (caso tenha voltado online)
  if (navigator.onLine) {
    setTimeout(processSyncQueue, 2000);
  }

  // Inicializar DB ao carregar
  initOfflineDB();

  /* 2. Prompt de instalação */
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', e => {
    e.preventDefault();
    deferredPrompt = e;
    const btn = document.getElementById('pwa-install-btn');
    if (btn) {
      btn.classList.remove('d-none');
      btn.addEventListener('click', () => {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
          deferredPrompt = null;
          btn.classList.add('d-none');
        });
      });
    }
  });
  window.addEventListener('appinstalled', () => {
    const btn = document.getElementById('pwa-install-btn');
    if (btn) btn.classList.add('d-none');
  });

  /* 3. Solicitar permissão push e enviar subscription ao servidor */
  const VAPID_PUBLIC_KEY = window.VAPID_PUBLIC_KEY || '';

  function askNotificationOnce() {
    if (!VAPID_PUBLIC_KEY) return;
    if (!('PushManager' in window)) return;
    if (Notification.permission === 'granted') {
      subscribePush();
    } else if (Notification.permission === 'default') {
      Notification.requestPermission().then(p => { if (p === 'granted') subscribePush(); });
    }
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
  }

  function subscribePush() {
    navigator.serviceWorker.ready.then(reg => {
      reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      }).then(sub => {
        const data = sub.toJSON();
        fetch('/portal/campo/push/subscribe/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: JSON.stringify({
            endpoint: data.endpoint,
            p256dh: data.keys.p256dh,
            auth: data.keys.auth,
          }),
        });
      }).catch(err => console.warn('[PWA] Push subscribe falhou:', err));
    });
  }

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
})();
