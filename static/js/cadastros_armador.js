// Formulário de Armador — CNPJ e CEP
(function () {
  const CNPJ_URL = '/cadastros/api/buscar-cnpj/';
  const CEP_URL  = '/cadastros/api/buscar-cep/';

  function csrf() {
    var el = document.querySelector('input[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  function showAlert(text, level) {
    var nav = document.querySelector('nav.breadcrumb')
           || document.querySelector('.container');
    if (!nav) return;
    var div = document.createElement('div');
    div.className = 'alert alert-' + (level || 'danger') + ' alert-dismissible fade show';
    div.setAttribute('role', 'alert');
    div.innerHTML = text + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    nav.parentNode.insertBefore(div, nav);
    setTimeout(function () {
      try { new bootstrap.Alert(div).close(); } catch (e) { div.remove(); }
    }, 6000);
  }

  function setBtn(btn, loading) {
    btn.disabled = loading;
    var icon = btn.querySelector('i');
    if (icon) icon.className = loading ? 'bi bi-hourglass-split' : 'bi bi-search';
    btn.querySelector('span') && (btn.querySelector('span').textContent = loading ? ' Buscando...' : ' Buscar');
  }

  function init() {

    /* ── CNPJ ─────────────────────────────────────────────── */
    var btnCNPJ = document.getElementById('buscarCNPJArmador');
    if (btnCNPJ) {
      btnCNPJ.addEventListener('click', function () {
        var form = btnCNPJ.closest('form');
        var inp  = form && form.querySelector('input[name="cnpj"]');
        if (!inp) { showAlert('Campo CNPJ não encontrado.', 'danger'); return; }

        var cnpj = inp.value.replace(/\D/g, '');
        if (cnpj.length !== 14) { showAlert('Digite um CNPJ válido com 14 dígitos.', 'warning'); return; }

        setBtn(btnCNPJ, true);

        fetch(CNPJ_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrf(),
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: 'cnpj=' + encodeURIComponent(cnpj)
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.sucesso) { showAlert(data.erro || 'CNPJ não encontrado.', 'warning'); return; }

          var d = data.dados || {};
          function set(name, val) {
            if (!val) return;
            var el = form.querySelector('[name="' + name + '"]');
            if (el) el.value = val;
          }
          set('nome',          d.nome);
          set('nome_fantasia', d.nome_fantasia);
          set('email',         d.email);
          set('telefone',      d.telefone);
          set('cep',           d.cep);
          set('endereco',      d.logradouro);
          set('numero',        d.numero);
          set('bairro',        d.bairro);
          set('cidade',        d.cidade || d.municipio);
          if (d.uf) {
            var ufEl = form.querySelector('[name="uf"]');
            if (ufEl) ufEl.value = d.uf.toUpperCase();
          }
          showAlert('Dados do CNPJ preenchidos com sucesso!', 'success');
        })
        .catch(function (err) {
          console.error('buscarCNPJ erro:', err);
          showAlert('Erro ao consultar CNPJ. Verifique a conexão.', 'danger');
        })
        .finally(function () { setBtn(btnCNPJ, false); });
      });
    }

    /* ── CEP ──────────────────────────────────────────────── */
    var btnCEP = document.getElementById('buscarCEP');
    if (btnCEP) {
      btnCEP.addEventListener('click', function () {
        var form = btnCEP.closest('form');
        var inp  = form && form.querySelector('input[name="cep"]');
        if (!inp) { showAlert('Campo CEP não encontrado.', 'danger'); return; }

        var cep = inp.value.replace(/\D/g, '');
        if (cep.length !== 8) { showAlert('Digite um CEP válido com 8 dígitos.', 'warning'); return; }

        setBtn(btnCEP, true);

        fetch(CEP_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrf(),
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: 'cep=' + encodeURIComponent(cep)
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var d = (data && data.dados) ? data.dados : data;
          if (!d || !d.logradouro) { showAlert(d.erro || 'CEP não encontrado.', 'warning'); return; }

          function set(name, val) {
            if (!val) return;
            var el = form.querySelector('[name="' + name + '"]');
            if (el) el.value = val;
          }
          set('endereco', d.logradouro);
          set('bairro',   d.bairro);
          set('cidade',   d.localidade || d.cidade);
          if (d.uf) {
            var ufEl = form.querySelector('[name="uf"]');
            if (ufEl) ufEl.value = d.uf.toUpperCase();
          }
          showAlert('Endereço preenchido com sucesso!', 'success');
        })
        .catch(function (err) {
          console.error('buscarCEP erro:', err);
          showAlert('Erro ao consultar CEP. Verifique a conexão.', 'danger');
        })
        .finally(function () { setBtn(btnCEP, false); });
      });
    }

  } // end init

  // Funciona independente do momento em que o script é carregado
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
