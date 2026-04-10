document.addEventListener('DOMContentLoaded', function () {
  const cfg = (window._cadastros_funcionario_config || {});
  const modalNovaFuncaoElement = document.getElementById('modalNovaFuncao');
  const modalNovaFuncao = new bootstrap.Modal(modalNovaFuncaoElement);
  const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
  const selectFuncao = document.getElementById('id_funcao');
  const inputSalario = document.getElementById('id_salario');

  const quickFuncaoForm = document.getElementById('formNovaFuncao');
  const possuiInsalubridadeInput = document.getElementById('id_possui_insalubridade');
  const grauInsalubridadeWrapper = document.getElementById('modal_grau_insalubridade_wrapper');
  const grauInsalubridadeInput = document.getElementById('id_grau_insalubridade');
  const possuiPericulosidadeInput = document.getElementById('id_possui_periculosidade');
  const percentualPericulosidadeWrapper = document.getElementById('modal_percentual_periculosidade_wrapper');
  const percentualPericulosidadeInput = document.getElementById('id_percentual_periculosidade');
  const requerLaudoInput = document.getElementById('id_requer_laudo');
  const laudoWrapper = document.getElementById('modal_laudo_wrapper');
  const validadeLaudoInput = document.getElementById('id_validade_laudo');

  function toggleWrapper(wrapper, enabled, field) {
    if (!wrapper) return;
    wrapper.classList.toggle('d-none', !enabled);
    if (!enabled && field) {
      if (field.tagName === 'SELECT') {
        field.selectedIndex = 0;
      } else if (field.type === 'date' || field.type === 'text' || field.type === 'number' || field.tagName === 'TEXTAREA') {
        field.value = '';
      }
      field.classList.remove('is-invalid');
    }
  }

  function syncQuickFuncaoFields() {
    toggleWrapper(grauInsalubridadeWrapper, !!(possuiInsalubridadeInput && possuiInsalubridadeInput.checked), grauInsalubridadeInput);
    toggleWrapper(percentualPericulosidadeWrapper, !!(possuiPericulosidadeInput && possuiPericulosidadeInput.checked), percentualPericulosidadeInput);
    toggleWrapper(laudoWrapper, !!(requerLaudoInput && requerLaudoInput.checked), validadeLaudoInput);
  }

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

  if (possuiInsalubridadeInput) {
    possuiInsalubridadeInput.addEventListener('change', syncQuickFuncaoFields);
  }
  if (possuiPericulosidadeInput) {
    possuiPericulosidadeInput.addEventListener('change', syncQuickFuncaoFields);
  }
  if (requerLaudoInput) {
    requerLaudoInput.addEventListener('change', syncQuickFuncaoFields);
  }
  syncQuickFuncaoFields();

  if (modalNovaFuncaoElement) {
    modalNovaFuncaoElement.addEventListener('shown.bs.modal', function () {
      syncQuickFuncaoFields();
    });

    modalNovaFuncaoElement.addEventListener('hidden.bs.modal', function () {
      if (!quickFuncaoForm) return;
      quickFuncaoForm.reset();
      clearFuncaoModalErrors(quickFuncaoForm);
      syncQuickFuncaoFields();
    });
  }

  // Preenchimento automático de salário pela função
  if (selectFuncao && inputSalario) {
    selectFuncao.addEventListener('change', async function () {
      const funcaoId = selectFuncao.value;
      
      console.log('🔍 Função selecionada:', funcaoId);
      
      if (!funcaoId) {
        inputSalario.value = '';
        console.log('❌ Nenhuma função selecionada');
        return;
      }

      try {
        const url = `/cadastros/funcoes/get-salario/?funcao_id=${funcaoId}`;
        console.log('📡 Buscando salário em:', url);
        
        const response = await fetch(url, {
          method: 'GET',
          credentials: 'same-origin',
          headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        console.log('📊 Status da resposta:', response.status);

        if (response.ok) {
          const data = await response.json();
          console.log('✅ Dados recebidos:', data);
          
          if (data.sucesso && data.salario_base !== undefined) {
            const salarioFormatado = parseFloat(data.salario_base).toFixed(2);
            inputSalario.value = salarioFormatado;
            console.log(`💰 Salário preenchido: R$ ${salarioFormatado}`);
          } else if (data.erro) {
            console.warn('⚠️ Erro na resposta:', data.erro);
          }
        } else {
          const text = await response.text();
          console.error('❌ Erro HTTP:', response.status, text);
        }
      } catch (error) {
        console.error('❌ Erro ao buscar salário:', error);
      }
    });
  } else {
    console.warn('⚠️ Elementos não encontrados - selectFuncao:', !!selectFuncao, 'inputSalario:', !!inputSalario);
  }

  // Cadastrar nova função via AJAX
  const btnSalvarFuncao = document.getElementById('btnSalvarFuncao');
  if (btnSalvarFuncao) {
    btnSalvarFuncao.addEventListener('click', async function () {
      const form = quickFuncaoForm;
      if (!form) return;
      const btn = btnSalvarFuncao;
      btn.disabled = true;

      try {
        console.log('Submitting nova funcao via AJAX to', cfg.funcao_create_url);
        document.getElementById('loadingText').textContent = 'Salvando função...';
        modalNovaFuncao.hide();
        loadingModal.show();

        const csrfToken = (form.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value || '';
        const formData = new FormData(form);

        const response = await fetch(cfg.funcao_create_url || '/cadastros/funcoes/criar-ajax/', {
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
            
            // Trigger change event para preencher salário
            selectFuncao.dispatchEvent(new Event('change', { bubbles: true }));
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
        const form = quickFuncaoForm;
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
        const response = await fetch(cfg.buscar_cep_url || '/cadastros/buscar-cep/', {
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

  // PIX behavior moved to shared file: 'static/js/cadastros_banking.js'

});
