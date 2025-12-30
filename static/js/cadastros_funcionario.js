document.addEventListener('DOMContentLoaded', function () {
  const cfg = (window._cadastros_funcionario_config || {});
  const modalNovaFuncao = new bootstrap.Modal(document.getElementById('modalNovaFuncao'));
  const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
  const selectFuncao = document.getElementById('id_funcao');

  function clearFuncaoModalErrors(form) {
    if (!form) return;
    const invalids = form.querySelectorAll('.is-invalid');
    invalids.forEach(el => el.classList.remove('is-invalid'));
    const previousFeedbacks = form.querySelectorAll('.invalid-feedback');
    previousFeedbacks.forEach(f => f.remove());
    const errorsDiv = document.getElementById('funcao-errors');
    if (errorsDiv) errorsDiv.innerHTML = '';
  }

  function showFieldErrors(form, errors) {
    if (!form) return;
    clearFuncaoModalErrors(form);

    let first = null;
    const errorsDiv = document.getElementById('funcao-errors');

    for (const [field, msgs] of Object.entries(errors || {})) {
      const input = form.querySelector(`[name="${field}"]`);
      if (input) {
        input.classList.add('is-invalid');
        const fb = document.createElement('div');
        fb.className = 'invalid-feedback';
        fb.textContent = msgs.join(' ');
        if (input.parentNode) {
          if (input.parentNode.classList && input.parentNode.classList.contains('input-group')) {
            input.parentNode.parentNode.insertBefore(fb, input.parentNode.nextSibling);
          } else {
            input.parentNode.insertBefore(fb, input.nextSibling);
          }
        } else {
          input.insertAdjacentElement('afterend', fb);
        }
        if (!first) first = input;
      } else if (errorsDiv) {
        const p = document.createElement('p');
        p.className = 'text-danger small mb-1';
        p.textContent = `${field}: ${msgs.join(' ')}`;
        errorsDiv.appendChild(p);
      }
    }
    if (first) first.focus();
  }

  // Cadastrar nova função via AJAX
  const btnSalvarFuncao = document.getElementById('btnSalvarFuncao');
  if (btnSalvarFuncao) {
    btnSalvarFuncao.addEventListener('click', async function () {
      const form = document.getElementById('formNovaFuncao');
      if (!form) return;
      const btn = btnSalvarFuncao;
      btn.disabled = true;

      try {
        document.getElementById('loadingText').textContent = 'Salvando função...';
        modalNovaFuncao.hide();
        loadingModal.show();

        const csrfToken = (form.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value || '';
        const formData = new FormData(form);

        const response = await fetch(cfg.funcao_create_url || '{% url "cadastros:funcao_create_ajax" %}', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': csrfToken, 'Accept': 'application/json' },
          body: formData
        });

        if (response.status === 401 || response.status === 403) {
          const err = new Error('Não autorizado');
          err.status = response.status;
          throw err;
        }

        const text = await response.text();
        let data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { const err = new Error('Resposta não JSON'); err.text = text; err.status = response.status; throw err; }
        if (!response.ok) { const err = new Error('HTTP ' + response.status); err.data = data; throw err; }

        if (data && data.sucesso) {
          if (selectFuncao) {
            const option = new Option(data.nome, data.id, true, true);
            try { selectFuncao.add(option); } catch (e) { selectFuncao.append(option); }
            selectFuncao.value = data.id;
          }

          form.reset();
          clearFuncaoModalErrors(form);
          modalNovaFuncao.hide();
          alert('✅ ' + data.mensagem);
        } else {
          showFieldErrors(form, (data && data.erros) || {});
          modalNovaFuncao.show();
        }
      } catch (error) {
        console.error('Erro ao criar função via AJAX', error);
        const form = document.getElementById('formNovaFuncao');
        if (error && error.data && error.data.erros) {
          showFieldErrors(form, error.data.erros);
          modalNovaFuncao.show();
        } else if (error && error.text) {
          alert('❌ Erro ao salvar função: resposta inesperada do servidor. Verifique se está logado.');
          modalNovaFuncao.show();
        } else if (error && (error.status === 401 || error.status === 403)) {
          alert('❌ Não autorizado. Faça login novamente.');
          modalNovaFuncao.show();
        } else {
          alert('❌ Erro ao salvar função');
          modalNovaFuncao.show();
        }
      } finally {
        loadingModal.hide();
        btn.disabled = false;
      }
    });
  }

  // Buscar CEP
  const btnBuscarCEP = document.getElementById('buscarCEPFunc');
  if (btnBuscarCEP) {
    btnBuscarCEP.addEventListener('click', async function () {
      const cepInput = document.querySelector(cfg.cep_selector || '[name="cep"]');
      if (!cepInput) { alert('Campo CEP não encontrado'); return; }
      const cep = (cepInput.value || '').replace(/\D/g, '');

      console.log('Iniciando busca CEP', cep);

      if (cep.length !== 8) { alert('Digite um CEP válido'); return; }

      document.getElementById('loadingText').textContent = 'Buscando CEP...';
      loadingModal.show();

      try {
        const response = await fetch(cfg.buscar_cep_url || '{% url "cadastros:buscar_cep" %}', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': (document.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value || ''
          },
          body: `cep=${cep}`
        });

        const data = await response.json();
        loadingModal.hide();

        if (data.sucesso) {
          const d = data.dados || {};
          const endereco = document.querySelector(cfg.endereco_selector || '[name="endereco"]');
          const bairro = document.querySelector(cfg.bairro_selector || '[name="bairro"]');
          const cidade = document.querySelector(cfg.cidade_selector || '[name="cidade"]');
          const uf = document.querySelector(cfg.uf_selector || '[name="uf"]');
          if (endereco) endereco.value = d.logradouro || '';
          if (bairro) bairro.value = d.bairro || '';
          if (cidade) cidade.value = d.localidade || d.cidade || '';
          if (uf) uf.value = d.uf || '';
          alert('✅ Endereço preenchido!');
        } else {
          alert('❌ CEP não encontrado');
        }
      } catch (e) {
        loadingModal.hide();
        alert('❌ Erro ao buscar CEP');
      }
    });
  }

});
