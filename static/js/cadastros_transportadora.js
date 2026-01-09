// Auto-fill for Transportadora form (CNPJ and CEP)
(function () {
  const cfg = {
    buscar_cep_url: window.CADASTROS_BUSCAR_CEP_URL || '/cadastros/api/buscar-cep/',
    buscar_cnpj_url: window.CADASTROS_BUSCAR_CNPJ_URL || '/cadastros/api/buscar-cnpj/'
  };

  function getCsrf() {
    const el = document.querySelector('input[name=csrfmiddlewaretoken]');
    return el ? el.value : null;
  }

  async function buscarCnpj(cnpj) {
    try {
      const resp = await fetch(cfg.buscar_cnpj_url + '?cnpj=' + encodeURIComponent(cnpj), {headers: {'X-Requested-With':'XMLHttpRequest'}});
      if (!resp.ok) return null;
      const json = await resp.json();
      return json.dados || null;
    } catch(e){ console.error('buscarCnpj error', e); return null; }
  }

  async function buscarCep(cep) {
    try {
      const resp = await fetch(cfg.buscar_cep_url + '?cep=' + encodeURIComponent(cep), {headers: {'X-Requested-With':'XMLHttpRequest'}});
      if (!resp.ok) return null;
      const json = await resp.json();
      return json.dados || null;
    } catch(e){ console.error('buscarCep error', e); return null; }
  }

  function setFieldValue(selector, value){
    const el = document.getElementById(selector);
    if (!el) return;
    el.value = value || '';
  }

  document.addEventListener('DOMContentLoaded', function () {
    const cnpjEl = document.getElementById('id_cnpj');
    const cepEl = document.getElementById('id_cep');

    if (cnpjEl) {
      cnpjEl.addEventListener('blur', async function (e) {
        const val = (e.target.value || '').replace(/\D/g, '');
        if (!val || val.length !== 14) return;
        const dados = await buscarCnpj(val);
        if (!dados) return;
        setFieldValue('id_razao_social', dados.nome || '');
        setFieldValue('id_nome_fantasia', dados.nome_fantasia || '');
        setFieldValue('id_contato_principal_telefone', dados.telefone || '');
        setFieldValue('id_contato_principal_email', dados.email || '');
        if (dados.cep) {
          setFieldValue('id_cep', (dados.cep || '').replace(/\D/g, ''));
          // trigger CEP autofill
          cepEl && cepEl.dispatchEvent(new Event('blur'));
        }
      });
    }

    if (cepEl) {
      cepEl.addEventListener('blur', async function (e) {
        const val = (e.target.value || '').replace(/\D/g, '');
        if (!val || val.length !== 8) return;
        const dados = await buscarCep(val);
        if (!dados) return;
        setFieldValue('id_logradouro', dados.logradouro || '');
        setFieldValue('id_complemento', dados.complemento || '');
        setFieldValue('id_bairro', dados.bairro || '');
        setFieldValue('id_cidade', dados.cidade || '');
        setFieldValue('id_uf', dados.uf || '');
      });
    }

    // Inline edit frete on transportadora cards
    document.querySelectorAll('.btn-edit-frete').forEach(btn => {
      btn.addEventListener('click', async function (e) {
        const id = btn.getAttribute('data-id');
        const span = document.querySelector('.frete-display[data-id="' + id + '"]');
        if (!span) return;
        // create input
        const current = (span.textContent || '').replace(/[R$\s]/g, '').trim();
        const input = document.createElement('input');
        input.type = 'text';
        input.value = current === '-' ? '' : current;
        input.className = 'form-control form-control-sm d-inline-block';
        input.style.width = '120px';
        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn btn-sm btn-primary ms-2';
        saveBtn.textContent = 'Salvar';
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-sm btn-secondary ms-1';
        cancelBtn.textContent = 'Cancelar';

        // hide original
        span.style.display = 'none';
        btn.style.display = 'none';
        span.parentNode.appendChild(input);
        span.parentNode.appendChild(saveBtn);
        span.parentNode.appendChild(cancelBtn);

        cancelBtn.addEventListener('click', function () {
          input.remove(); saveBtn.remove(); cancelBtn.remove(); span.style.display = ''; btn.style.display = '';
        });

        saveBtn.addEventListener('click', async function () {
          const val = input.value.trim();
          const formData = new FormData();
          formData.append('frete', val);
          const csrf = getCsrf();

          // UI: show spinner, disable inputs
          const spinner = document.querySelector('.frete-spinner[data-id="' + id + '"]');
          const msg = document.querySelector('.frete-msg[data-id="' + id + '"]');
          const err = document.querySelector('.frete-error[data-id="' + id + '"]');
          const undoBtn = document.querySelector('.btn-undo[data-id="' + id + '"]');
          spinner && spinner.classList.remove('d-none');
          saveBtn.disabled = true; cancelBtn.disabled = true; input.disabled = true;

          try {
            // Optimistic update: show new value immediately
            const prevText = span.textContent;
            function formatCurrency(raw) {
              if (raw === '' || raw === null || raw === undefined) return '-';
              const n = Number(String(raw).replace(/\D/g, '').replace(/^0+(?!$)/, ''));
              if (isNaN(Number(raw))) {
                const parsed = Number(String(raw).replace(',', '.'));
                if (isNaN(parsed)) return '-';
                return parsed.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
              }
              return Number(String(raw).replace(',', '.')).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
            }
            span.textContent = val ? ('R$ ' + formatCurrency(val)) : '-';
            span.style.display = '';
            btn.style.display = '';

            const resp = await fetch(`/cadastros/transportadoras/${id}/frete/`, {
              method: 'POST',
              headers: {'X-Requested-With':'XMLHttpRequest', 'X-CSRFToken': csrf},
              body: formData
            });
            const json = await resp.json();
            if (resp.ok && json.sucesso) {
              // success: show confirmation and undo option
              spinner && spinner.classList.add('d-none');
              err && (err.textContent = ''); err && err.classList.add('d-none');
              msg && (msg.classList.remove('d-none')); setTimeout(()=>msg&&msg.classList.add('d-none'), 3000);

              // show undo button for 10s
              undoBtn && (undoBtn.classList.remove('d-none'));
              // store prev value on undoBtn.dataset
              if (undoBtn) {
                undoBtn.dataset.prev = prevText.replace(/[R$\s]/g,'').trim();
                // when clicked, send previous value back
                const timeoutId = setTimeout(()=>{ undoBtn.classList.add('d-none'); delete undoBtn.dataset.prev; }, 10000);
                undoBtn.onclick = async function () {
                  clearTimeout(timeoutId);
                  const prev = undoBtn.dataset.prev || '';
                  const fd = new FormData(); fd.append('frete', prev);
                  const r2 = await fetch(`/cadastros/transportadoras/${id}/frete/`, {method:'POST', headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken': csrf}, body: fd});
                  if (r2.ok) {
                    const j2 = await r2.json();
                    span.textContent = j2.frete_padrao ? ('R$ ' + j2.frete_padrao) : '-';
                    undoBtn.classList.add('d-none');
                  } else {
                    alert('Erro ao desfazer');
                  }
                };

              }

              input.remove(); saveBtn.remove(); cancelBtn.remove();
            } else {
              // revert optimistic update and show error
              spinner && spinner.classList.add('d-none');
              saveBtn.disabled = false; cancelBtn.disabled = false; input.disabled = false;
              span.textContent = prevText;
              err && (err.textContent = (json.erro || 'Não foi possível atualizar.')); err && err.classList.remove('d-none');
            }
          } catch (err) {
            console.error(err);
            spinner && spinner.classList.add('d-none');
            saveBtn.disabled = false; cancelBtn.disabled = false; input.disabled = false;
            alert('Erro ao atualizar frete');
          }
        });
      });
    });
  });
})();