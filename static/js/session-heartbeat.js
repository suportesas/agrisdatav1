/*
 * Mantém a sessão viva enquanto o usuário interage de verdade com a página
 * (mouse, teclado, scroll, toque) e a aba está visível. Sem interação real,
 * o heartbeat para de ser enviado e o timeout de inatividade do servidor
 * (InactivityLogoutMiddleware) passa a valer normalmente.
 */
(function () {
  var HEARTBEAT_URL = document.currentScript.dataset.url;
  var HEARTBEAT_INTERVAL_MS = 60 * 1000; // bem menor que o timeout do servidor (5 min)
  var ACTIVITY_WINDOW_MS = HEARTBEAT_INTERVAL_MS + 10 * 1000; // margem para o intervalo do timer

  var lastInteractionAt = Date.now();
  var sessionExpired = false;

  function markInteraction() {
    lastInteractionAt = Date.now();
  }

  ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'wheel'].forEach(function (evt) {
    window.addEventListener(evt, markInteraction, { passive: true });
  });

  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function handleExpiredSession() {
    if (sessionExpired) return;
    sessionExpired = true;
    var loginUrl = '/login/?next=' + encodeURIComponent(window.location.pathname + window.location.search);
    var msg = 'Sua sessão expirou por inatividade. Você será redirecionado para o login.';
    if (typeof window.showToast === 'function') {
      window.showToast(msg, 'warning');
      setTimeout(function () { window.location.href = loginUrl; }, 2500);
    } else {
      window.location.href = loginUrl;
    }
  }

  function sendHeartbeat() {
    if (sessionExpired) return;
    if (document.visibilityState !== 'visible') return;
    if (Date.now() - lastInteractionAt > ACTIVITY_WINDOW_MS) return; // usuário realmente parado

    fetch(HEARTBEAT_URL, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
      }
    }).then(function (response) {
      // Sessão expirou entre um heartbeat e outro: o middleware redireciona para /login/
      if (response.redirected || response.url.indexOf('/login') !== -1 || response.status === 403) {
        handleExpiredSession();
      }
    }).catch(function () {
      // Falha de rede pontual não deve derrubar a sessão no client-side.
    });
  }

  setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
})();
