// JS para o formulário de Cliente
// - Define UF='EX' quando país != Brasil
// - Mostra/oculta campos (IE, EORI, Porto) conforme regras
// - Busca CEP via endpoint configurável (default: /cadastros/api/buscar-cep/)

(function () {
  const cfg = {
    buscar_cep_url: window.CADASTROS_BUSCAR_CEP_URL || '/cadastros/api/buscar-cep/',
    buscar_cnpj_url: window.CADASTROS_BUSCAR_CNPJ_URL || '/cadastros/api/buscar-cnpj/'
  };

  function getCsrfToken() {
    const el = document.querySelector('input[name=csrfmiddlewaretoken]');
    return el ? el.value : null;
  }

  function showClientAlert(text, level='danger'){
    try{
      const main = document.querySelector('main');
      if (!main) return;
      const div = document.createElement('div');
      div.className = `alert alert-${level} alert-dismissible fade show`;
      div.setAttribute('role','alert');
      div.innerHTML = `${text} <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>`;
      main.insertBefore(div, main.firstChild);
      setTimeout(()=>{ try { var bs = bootstrap.Alert.getInstance(div) || new bootstrap.Alert(div); bs.close(); } catch(e){} }, 5000);
    }catch(e){console.error('showClientAlert failed', e);}  }

  function hideElement(el) {
    if (!el) return;
    let grp = el.closest('.form-group') || el.parentElement;
    // fallback: find nearest ancestor with a bootstrap grid column (e.g. col-md-4)
    let ancestor = el;
    while (ancestor && ancestor !== document.body) {
      if (ancestor.className && /(^|\s)col-md-\d+($|\s)/.test(ancestor.className)) { grp = ancestor; break; }
      ancestor = ancestor.parentElement;
    }
    if (grp) grp.style.display = 'none'; else el.style.display = 'none';
  }
  function showElement(el) {
    if (!el) return;
    let grp = el.closest('.form-group') || el.parentElement;
    let ancestor = el;
    while (ancestor && ancestor !== document.body) {
      if (ancestor.className && /(^|\s)col-md-\d+($|\s)/.test(ancestor.className)) { grp = ancestor; break; }
      ancestor = ancestor.parentElement;
    }
    if (grp) grp.style.display = ''; else el.style.display = '';
  }

  document.addEventListener('DOMContentLoaded', function () {

    // Elements
    const pais = document.getElementById('id_pais');
    const uf = document.getElementById('id_uf');
    const inscricao = document.getElementById('id_inscricao_estadual');
    const tipoCliente = document.getElementById('id_tipo_cliente');
    const eori = document.getElementById('id_eori');
    const vat = document.getElementById('id_vat');
    const porto = document.getElementById('id_porto_destino');
    const moeda = document.getElementById('id_moeda_padrao');

    function updateByCountry(value) {
      const country = (value || '').trim().toLowerCase();
      if (!uf) return;
      if (country && country !== 'brasil') {
        // set UF to EX
        uf.value = 'EX';
        // hide IE field (not relevant for exterior)
        if (inscricao) hideElement(inscricao);
      } else {
        // Show IE and let user pick UF
        if (inscricao) showElement(inscricao);
      }
    }

    async function updateVendedoresByTipo(tipo) {
      try {
        const sel = document.getElementById('id_vendedor_responsavel');
        if (!sel) return;
        const url = `${cfg.buscar_cnpj_url.replace('/buscar-cnpj/','/buscar-cnpj/').replace('/buscar-cnpj/','/buscar-cnpj/')}`; // noop placeholder to keep code style
        const resp = await fetch(`/cadastros/api/vendedores-por-tipo/?tipo=${encodeURIComponent(tipo)}`, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
        if (!resp.ok) return;
        const json = await resp.json().catch(() => ({}));
        const vendedores = json.vendedores || [];
        const current = sel.value;
        sel.innerHTML = '';
        const empty = document.createElement('option'); empty.value = ''; empty.textContent = '-- Nenhum --'; sel.appendChild(empty);
        vendedores.forEach(v => {
          const opt = document.createElement('option'); opt.value = v.id; opt.textContent = v.nome; sel.appendChild(opt);
        });
        // try to restore previous selection if still present
        if (current && Array.from(sel.options).some(o => o.value === current)) sel.value = current;
      } catch (err) {
        // ignore errors silently
        console.error('Erro ao atualizar vendedores:', err);
      }
    }

    function updateByTipoCliente() {
      const val = tipoCliente ? tipoCliente.value : '';
      if (val === 'IMPORTADOR') {
        // mostrar EORI, VAT, Porto e Moeda
        if (eori) showElement(eori);
        if (vat) showElement(vat);
        if (porto) showElement(porto);
        if (moeda) showElement(moeda);
        // Importadores use UF='EX' for address fields
        document.querySelectorAll('select[name="uf"], input[name="uf"]').forEach(el => {
          try { el.value = 'EX'; } catch(e){}
        });
      } else {
        if (eori) hideElement(eori);
        if (vat) hideElement(vat);
        if (porto) hideElement(porto);
        if (moeda) hideElement(moeda);
      }
      // Update vendedor list dynamically
      updateVendedoresByTipo(val === 'IMPORTADOR' ? 'IMPORTADOR' : 'NACIONAL');
    }

    if (pais) {
      pais.addEventListener('change', function (e) { updateByCountry(e.target.value); });
      // initialize
      updateByCountry(pais.value);
    }

    if (tipoCliente) {
      tipoCliente.addEventListener('change', updateByTipoCliente);
      updateByTipoCliente();
    }

    // Buscar CNPJ (aplica-se a formulários de fornecedor/cliente)
    const buscarCNPJBtn = document.getElementById('buscarCNPJ');

    // Adicionar Moeda via modal
    const addMoedaBtn = document.getElementById('addMoedaBtn');
    const moedaModalElem = document.getElementById('moedaModal');
    const moedaSaveBtn = document.getElementById('moedaSaveBtn');
    const moedaCodigo = document.getElementById('moeda_codigo');
    const moedaNome = document.getElementById('moeda_nome');
    const moedaFeedback = document.getElementById('moedaFeedback');

    function showMoedaModal() {
      if (!moedaModalElem) return;
      const modal = new bootstrap.Modal(moedaModalElem);
      moedaFeedback.textContent = '';
      moedaCodigo.value = '';
      moedaNome.value = '';
      modal.show();
    }

    async function saveMoeda() {
      moedaFeedback.textContent = '';
      const codigo = (moedaCodigo.value || '').trim().toUpperCase();
      const nome = (moedaNome.value || '').trim();
      if (!codigo || !nome) {
        moedaFeedback.textContent = 'Código e nome são obrigatórios.';
        return;
      }
      const csrf = getCsrfToken();
      try {

        moedaSaveBtn.disabled = true;
        const resp = await fetch('/cadastros/moedas/novo-ajax/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrf,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json'
          },
          body: `codigo=${encodeURIComponent(codigo)}&nome=${encodeURIComponent(nome)}`
        });

        let json = null;
        try { json = await resp.json(); } catch(e){ console.error('invalid json', e); }
        if (!resp.ok) {
          moedaFeedback.textContent = (json && (json.error || json.erro)) || 'Erro ao criar moeda';
          console.error('saveMoeda error response', resp.status, json);
          return;
        }
        // adicionar opção ao select
        const sel = document.getElementById('id_moeda_padrao');
        if (sel) {
          const opt = document.createElement('option');
          opt.value = json.moeda.codigo;
          opt.textContent = `${json.moeda.nome} (${json.moeda.codigo})`;
          opt.selected = true;
          sel.appendChild(opt);
          // ensure select reflects change and notify any listeners/plugins
          sel.value = json.moeda.codigo;
          try { sel.dispatchEvent(new Event('change', {bubbles: true})); } catch(e){}
          try { sel.focus(); } catch(e){}
          // Diagnostic: log select state and emit custom event

          try { sel.dispatchEvent(new CustomEvent('moeda:added', {detail: {codigo: json.moeda.codigo, nome: json.moeda.nome}, bubbles: true})); } catch(e){}
        }
        // fechar modal (blur to avoid focus trapped inside hidden modal)
        try { moedaSaveBtn.blur(); } catch(e){}
        const modal = bootstrap.Modal.getInstance(moedaModalElem);
        // move focus back to the select or opener after the modal is fully hidden to avoid aria-hidden+focus warnings
        if (modal) {
          moedaModalElem.addEventListener('hidden.bs.modal', function _focusBack(){
            try {
              const sel = document.getElementById('id_moeda_padrao');
              if (sel) {
                sel.focus();
                sel.dispatchEvent(new Event('change', {bubbles: true}));
              } else if (addMoedaBtn) {
                addMoedaBtn.focus();
              }
            } catch(e){ console.error('focus restore after moeda modal hide failed', e); }
            moedaModalElem.removeEventListener('hidden.bs.modal', _focusBack);
          }, {once:true});
          try { modal.hide(); } catch(e){ console.error('modal.hide failed', e); }
        } else {
          try { moedaSaveBtn.blur(); } catch(e){}
        }
      } catch(err) {
        moedaFeedback.textContent = 'Erro ao salvar moeda';
        console.error('saveMoeda threw', err);
      }
    }

    if (addMoedaBtn) addMoedaBtn.addEventListener('click', showMoedaModal);
    if (moedaSaveBtn) moedaSaveBtn.addEventListener('click', saveMoeda);
    if (buscarCNPJBtn) {
      // Defensive logging to help diagnose why CNPJ search may not run in some environments
      try { buscarCNPJBtn.addEventListener('click', async () => {
        console.debug('buscarCNPJ clicked');
        const form = buscarCNPJBtn.closest('form');
        if (!form) { console.error('buscarCNPJ: enclosing form not found'); showClientAlert('Erro interno: formulário não encontrado', 'danger'); return; }
        const cnpjInput = form.querySelector('input[name="cnpj_cpf"]');
        if (!cnpjInput) { console.error('buscarCNPJ: cnpj_cpf input not found in form'); showClientAlert('Campo CNPJ/CPF não encontrado', 'danger'); return; }
        const cnpj = (cnpjInput.value || '').replace(/\D/g, '');
        if (cnpj.length !== 14) { showClientAlert('Digite um CNPJ válido (14 dígitos)', 'danger'); return; }

        const csrf = getCsrfToken();
        // prefer the generic loading modal if present, else the cnpj-specific one
        const loadingModalElem = document.getElementById('loadingModal') || document.getElementById('cnpjLoadingModal');
        const loadingModal = loadingModalElem ? new bootstrap.Modal(loadingModalElem) : null;

        try {
          buscarCNPJBtn.disabled = true;
          if (loadingModal) loadingModal.show();

          const resp = await fetch(cfg.buscar_cnpj_url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
              'X-CSRFToken': csrf,
              'Accept': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: `cnpj=${cnpj}`
          });

          if (!resp.ok) {
            if (loadingModal) loadingModal.hide();
            const json = await resp.json().catch(() => ({}));
            showClientAlert(json.erro || 'Erro ao buscar CNPJ', 'danger');
            return;
          }

          // Parse JSON defensively: handle cases where server returns HTML or malformed JSON
          let data = null;
          try {
            const text = await resp.text();
            try { data = text ? JSON.parse(text) : {}; } catch (jsonErr) {
              console.error('buscarCNPJ: response not JSON', text);
              if (loadingModal) loadingModal.hide();
              showClientAlert('Resposta inválida do servidor ao buscar CNPJ', 'danger');
              return;
            }
          } catch (readErr) {
            console.error('buscarCNPJ: failed to read response text', readErr);
            if (loadingModal) loadingModal.hide();
            showClientAlert('Erro ao ler resposta do servidor', 'danger');
            return;
          }

          if (data && data.sucesso && data.dados) {
            if (loadingModal) loadingModal.hide();
            const d = data.dados;

            // Keep previous values to allow revert on cancel
            const changed = [];
            const previous = {};
            const map = [
              {sel:'input[name="razao_social"]', label: 'Razão Social', val: d.nome},
              {sel:'input[name="nome_comercial"]', label: 'Nome Comercial', val: d.nome_fantasia},
              {sel:'input[name="cnpj_cpf"]', label: 'CNPJ', val: d.cnpj},
              {sel:'input[name="contato_principal_telefone"]', label: 'Telefone', val: d.telefone},
              {sel:'input[name="contato_principal_email"]', label: 'E-mail', val: d.email}
            ];

            map.forEach(item => {
              const el = form.querySelector(item.sel);
              if (!el) return;
              previous[item.sel] = el.value || '';
              if ((item.val || '') !== (el.value || '')) {
                changed.push({sel:item.sel, label:item.label, old: previous[item.sel], new: item.val || ''});
                el.value = item.val || '';
                el.setAttribute('data-autofilled','1');
                el.classList.add('border-warning');
              }
            });

            // Auto-toggle international fields when UF is not a known Brazilian state
            try {
              const ufVal = (d.uf || '').toString().trim().toUpperCase();
              const brazilUF = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];
              if (ufVal && brazilUF.indexOf(ufVal) === -1) {
                // Consider foreign -> set tipo_cliente to IMPORTADOR
                if (typeof tipoCliente !== 'undefined' && tipoCliente) { tipoCliente.value = 'IMPORTADOR'; updateByTipoCliente(); }
              }
              // If returned UF is present and there is a UF field, set it
              try {
                const ufField = form.querySelector('select[name="uf"]') || form.querySelector('input[name="uf"]');
                if (ufField && ufVal) ufField.value = ufVal;
              } catch(e){}
              // If returned city/cep, fill address fields if present
              if (form.querySelector('input[name="logradouro"]') && d.logradouro) form.querySelector('input[name="logradouro"]').value = d.logradouro;
              if (form.querySelector('input[name="numero"]') && d.numero) form.querySelector('input[name="numero"]').value = d.numero;
              if (form.querySelector('input[name="bairro"]') && d.bairro) form.querySelector('input[name="bairro"]').value = d.bairro;
              if (form.querySelector('input[name="cidade"]') && d.cidade) form.querySelector('input[name="cidade"]').value = d.cidade || d.municipio;
              if (form.querySelector('input[name="cep"]') && d.cep) form.querySelector('input[name="cep"]').value = (d.cep || '').replace(/\D/g,'');
            } catch(e) { /* ignore gracefully */ }

            // If nothing changed, hide loader, quick message and return
            if (changed.length === 0) {
              if (loadingModal) loadingModal.hide();
              showClientAlert('Nenhuma alteração detectada', 'info');
              return;
            }

            // Populate confirm modal list
            const list = document.getElementById('cnpjConfirmList');
            list.innerHTML = '';
            changed.forEach(it => {
              const li = document.createElement('li');
              li.className = 'list-group-item';
              li.innerHTML = `<strong>${it.label}:</strong> <div class="small text-muted">Antigo: ${it.old || '(vazio)'}</div><div>${it.new || '(vazio)'}</div>`;
              list.appendChild(li);
            });

            // Show modal and wire handlers
            const confirmModalElem = document.getElementById('cnpjConfirmModal');
            const confirmModal = confirmModalElem ? new bootstrap.Modal(confirmModalElem) : null;
            const acceptBtn = document.getElementById('cnpjConfirmAccept');
            const cancelBtn = document.getElementById('cnpjConfirmCancel');

            const cleanup = ()=>{
              // remove temporary highlight
              map.forEach(item => { const el = form.querySelector(item.sel); if (el) el.classList.remove('border-warning'); });
            };

            let accepted = false;
            let hiddenHandler = null;

            const onAccept = ()=>{
              accepted = true;
              // mark fields as confirmed
              map.forEach(item => { const el = form.querySelector(item.sel); if (el && el.getAttribute('data-autofilled') === '1') { el.setAttribute('data-confirmed','1'); el.classList.remove('border-warning'); el.classList.add('border-success'); } });
              if (confirmModal) confirmModal.hide();
              showClientAlert('✅ Dados preenchidos com sucesso!', 'success');
              cleanup();
              // remove handlers
              acceptBtn.removeEventListener('click', onAccept);
              cancelBtn.removeEventListener('click', onCancel);
              if (hiddenHandler && confirmModalElem) confirmModalElem.removeEventListener('hidden.bs.modal', hiddenHandler);
            };

            const onCancel = (fromHidden=false)=>{
              // revert values
              changed.forEach(it=>{
                const el = form.querySelector(it.sel);
                if (el) { el.value = it.old; el.removeAttribute('data-autofilled'); el.classList.remove('border-warning'); }
              });
              if (!fromHidden && confirmModal) confirmModal.hide();
              showClientAlert('Alterações revertidas', 'warning');
              cleanup();
              acceptBtn.removeEventListener('click', onAccept);
              cancelBtn.removeEventListener('click', onCancel);
              if (hiddenHandler && confirmModalElem) confirmModalElem.removeEventListener('hidden.bs.modal', hiddenHandler);
            };

            if (acceptBtn && cancelBtn) {
              acceptBtn.addEventListener('click', onAccept);
              cancelBtn.addEventListener('click', onCancel);
            }

            if (confirmModal) {
              hiddenHandler = function(){ if (!accepted) onCancel(true); };
              confirmModalElem.addEventListener('hidden.bs.modal', hiddenHandler);
              confirmModal.show();
            }
          } else {
            if (loadingModal) loadingModal.hide();
            showClientAlert(data.erro || 'CNPJ não encontrado', 'danger');
          }
        } catch (err) {
          console.error(err);
          if (loadingModal) loadingModal.hide();
          showClientAlert('Erro ao buscar CNPJ', 'danger');
        } finally {
          if (loadingModal) loadingModal.hide();
          buscarCNPJBtn.disabled = false;
        }
      });
    }
    // Accessibility: ensure modals return focus and focus first interactive element on open
    document.querySelectorAll('.modal[data-a11y], .modal[data-a11y="true"]').forEach(modalEl => {
      modalEl.addEventListener('show.bs.modal', (e) => {
        // Save last focused element
        modalEl._lastActive = document.activeElement;
        // Move focus to first focusable element inside modal
        setTimeout(()=>{
          const focusable = modalEl.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
          if (focusable) focusable.focus();
        }, 10);
      });
      modalEl.addEventListener('hidden.bs.modal', (e) => {
        // Restore focus to last active element
        try {
          if (modalEl._lastActive && typeof modalEl._lastActive.focus === 'function') modalEl._lastActive.focus();
        } catch(err){/* ignore */}
      });
    });

          } else {
            if (loadingModal) loadingModal.hide();
            const fb = document.getElementById('cnpjFeedback');
            if (fb) { fb.classList.remove('text-success'); fb.classList.add('text-danger'); fb.textContent = data.erro || 'CNPJ não encontrado'; }
            else alert(data.erro || 'CNPJ não encontrado');
          }
        } catch (err) {
          console.error(err);
          if (loadingModal) loadingModal.hide();
          alert('Erro ao buscar CNPJ');
        } finally {
          if (loadingModal) loadingModal.hide();
          buscarCNPJBtn.disabled = false;
        }
      });

      // Add input mask for CNPJ/CPF similar to Fornecedor form
      try {
        const cnpjInputs = document.querySelectorAll('input[name="cnpj_cpf"]');
        cnpjInputs.forEach(input => {
          input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');

            if (value.length <= 11) {
              // CPF mask
              value = value.replace(/(\d{3})(\d)/, '$1.$2');
              value = value.replace(/(\d{3})(\d)/, '$1.$2');
              value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
            } else {
              // CNPJ mask
              value = value.replace(/^(\d{2})(\d)/, '$1.$2');
              value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
              value = value.replace(/\.(\d{3})(\d)/, '.$1/$2');
              value = value.replace(/(\d{4})(\d)/, '$1-$2');
            }

            e.target.value = value;
          });
        });
      } catch (maskErr) { /* ignore */ }
    }

    // Presets de Prazo Pagamento: popula lista de termos e atualiza `prazo_pagamento`
    const prazoPresetSelect = document.getElementById('id_prazo_pagamento_padrao_select');
    const prazoTermsSelect = document.getElementById('id_prazo_pagamento_padrao_terms');
    const prazoInput = document.getElementById('id_prazo_pagamento');

    if (prazoPresetSelect && prazoTermsSelect && prazoInput) {
      prazoPresetSelect.addEventListener('change', function(e){
        const opt = prazoPresetSelect.selectedOptions[0];
        const terms = opt ? (opt.getAttribute('data-terms') || '') : '';
        if (!terms) {
          prazoTermsSelect.style.display = 'none';
          prazoTermsSelect.innerHTML = '';
          return;
        }
        const parts = terms.split(',').map(s=>s.trim()).filter(s=>s);
        prazoTermsSelect.innerHTML = '';
        parts.forEach(p=>{
          const o = document.createElement('option'); o.value = p; o.textContent = p + ' dias'; prazoTermsSelect.appendChild(o);
        });
        prazoTermsSelect.style.display = '';
        // set default prazo to first term
        if (parts.length) prazoInput.value = parts[0];
      });

      prazoTermsSelect.addEventListener('change', function(e){
        prazoInput.value = prazoTermsSelect.value;
      });
    }

    // Buscar CEP buttons (generic): elements with class 'btn-buscar-cep' must be present in the template
    document.querySelectorAll('.btn-buscar-cep').forEach(btn => {
      btn.addEventListener('click', async () => {
        const form = btn.closest('form');
        if (!form) return;
        const cepInput = form.querySelector('input[name="cep"]');
        if (!cepInput) { alert('Campo CEP não encontrado'); return; }
        const cep = (cepInput.value || '').replace(/\D/g, '');
        if (cep.length !== 8) { alert('Digite um CEP válido'); return; }

        // Show loader if present
        const csrf = getCsrfToken();
        try {
          btn.disabled = true;
          const resp = await fetch(cfg.buscar_cep_url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
              'X-CSRFToken': csrf,
              'Accept': 'application/json'
            },
            body: `cep=${cep}`
          });

          if (!resp.ok) {
            const json = await resp.json().catch(() => ({}));
            alert(json.erro || 'Erro ao buscar CEP');
            return;
          }

          const data = await resp.json();
          // Some endpoints return {sucesso: true, dados: {...}} while others return flat object
          const d = (data && data.dados) ? data.dados : data;

          // Optional loading modal handling: find nearest or global modal
          const loadingModalEl = document.getElementById('loadingModal') || document.querySelector('.loadingModal');
          const loadingModal = loadingModalEl ? new bootstrap.Modal(loadingModalEl) : null;

          // Fill fields if present
          if (form.querySelector('input[name="logradouro"]')) form.querySelector('input[name="logradouro"]').value = d.logradouro || '';
          if (form.querySelector('input[name="bairro"]')) form.querySelector('input[name="bairro"]').value = d.bairro || '';
          if (form.querySelector('input[name="cidade"]')) form.querySelector('input[name="cidade"]').value = d.cidade || d.localidade || '';
          if (form.querySelector('select[name="uf"]') || form.querySelector('input[name="uf"]')) {
            const ufField = form.querySelector('select[name="uf"]') || form.querySelector('input[name="uf"]');
            if (ufField) ufField.value = (d.uf || ufField.value).toUpperCase();
          }
          if (form.querySelector('input[name="cep"]')) form.querySelector('input[name="cep"]').value = d.cep || cepInput.value;

        } catch (err) {
          console.error(err);
          alert('Erro ao buscar CEP');
        } finally {
          btn.disabled = false;
          const loadingModalEl2 = document.getElementById('loadingModal') || document.querySelector('.loadingModal');
          if (loadingModalEl2) {
            try { const lm2 = new bootstrap.Modal(loadingModalEl2); lm2.hide(); } catch(e){}
          }
        }
      });
    });

    // Quick-add modals for Contato / Conta / Documento
    document.querySelectorAll('.btn-quick-add').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const url = btn.getAttribute('data-url');
        const target = btn.getAttribute('data-target-list');
        if (!url) return;
        try {
          const resp = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
          const json = await resp.json();
          const modalEl = document.getElementById('quickAddModal');
          const modalBody = document.getElementById('quickAddModalBody');
          modalBody.innerHTML = json.form_html || '<div class="alert alert-danger">Erro ao carregar formulário.</div>';
          const modal = new bootstrap.Modal(modalEl);
          modal.show();

          // attach submit handler
          const form = modalBody.querySelector('form');
          if (form) attachModalFormHandler(form, url, target, modal);
        } catch (err) {
          console.error(err);
          alert('Erro ao abrir formulário');
        }
      });
    });

    // Delegate edit/delete for account cards (AJAX)
    const contasRow = document.getElementById('clienteContasRow');
    if (contasRow) {
      contasRow.addEventListener('click', async function (ev) {
        const editBtn = ev.target.closest('.btn-conta-edit');
        const deleteBtn = ev.target.closest('.btn-conta-delete');
        const modalEl = document.getElementById('quickAddModal');
        const modalBody = document.getElementById('quickAddModalBody');
        const modal = modalEl ? new bootstrap.Modal(modalEl) : null;

        if (editBtn) {
          ev.preventDefault();
          const url = editBtn.getAttribute('data-edit-url');
          if (!url) return;
          try {
            const resp = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
            const json = await resp.json();
            modalBody.innerHTML = json.form_html || '<div class="alert alert-danger">Erro ao carregar formulário.</div>';
            if (modal) modal.show();
            const form = modalBody.querySelector('form');
            if (form) attachModalFormHandler(form, url, '#clienteContasRow', modal);
          } catch (err) {
            console.error(err);
            alert('Erro ao abrir formulário de edição');
          }
        }

        if (deleteBtn) {
          ev.preventDefault();
          const url = deleteBtn.getAttribute('data-delete-url');
          if (!url) return;
          try {
            const resp = await fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
            const json = await resp.json();
            modalBody.innerHTML = json.form_html || '<div class="alert alert-danger">Erro ao carregar confirmação.</div>';
            if (modal) modal.show();
            const form = modalBody.querySelector('form');
            if (form) {
              form.addEventListener('submit', async function (ev2) {
                ev2.preventDefault();
                const fd = new FormData(form);
                try {
                  const resp2 = await fetch(url, {method: 'POST', body: fd, headers: {'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCsrfToken()}});
                  const json2 = await resp2.json();
                  if (json2.success) {
                    // remove element and decrement counters
                    const id = json2.conta_id;
                    const el = document.getElementById('conta-' + id);
                    if (el) el.remove();
                    ['count_contas','tab_count_contas'].forEach(cid => { const ce = document.getElementById(cid); if (ce) { let v = parseInt((ce.textContent||'0').trim(),10)||0; ce.textContent = String(Math.max(0, v - 1)); }});
                    if (modal) modal.hide();
                  } else {
                    modalBody.innerHTML = json2.form_html || '<div class="alert alert-danger">Erro ao excluir.</div>';
                  }
                } catch (err) { console.error(err); alert('Erro ao submeter exclusão'); }
              });
            }
          } catch (err) {
            console.error(err);
            alert('Erro ao carregar confirmação de exclusão');
          }
        }
      });
    }

    function attachModalFormHandler(form, url, target, modal) {
      const onSubmit = async (ev) => {
        ev.preventDefault();
        const fd = new FormData(form);
        try {
          const resp = await fetch(url, {method: 'POST', body: fd, headers: {'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCsrfToken()}});
          const json = await resp.json();
          if (json.success) {
            // If an updated item was returned (update flow), replace existing element
            if (json.conta_id) {
              const el = document.getElementById('conta-' + json.conta_id);
              if (el) {
                el.outerHTML = json.item_html || '';
              } else if (target) {
                const container = document.querySelector(target);
                if (container) container.insertAdjacentHTML('afterbegin', json.item_html || '');
                else { window.location.reload(); return; }
              }
            } else {
              // append item HTML to target; if target doesn't exist (first item), reload page to render full layout
              if (target) {
                const container = document.querySelector(target);
                if (container) {
                  // if this is the documentos table, insert into its tbody if present
                  const tbody = container.querySelector('tbody');
                  if (tbody) {
                    tbody.insertAdjacentHTML('afterbegin', json.item_html || '');
                  } else {
                    container.insertAdjacentHTML('afterbegin', json.item_html || '');
                  }
                } else {
                  // fallback: reload to render tables/containers
                  window.location.reload();
                  return;
                }
              }
            }

            // increment counter if present
            const mapping = {
              '#clienteContatosTbody': 'count_contatos',
              '#clienteContasRow': 'count_contas',
              '#clienteDocumentosRow': 'count_documentos',
              '#clienteEnderecosRow': 'count_enderecos'
            };
            try {
              const countId = mapping[target];
              if (countId) {
                const el = document.getElementById(countId);
                if (el) {
                  const val = parseInt((el.textContent || '').trim() || '0', 10);
                  el.textContent = String(val + 1);
                }
              }
            } catch (e) { /* ignore */ }

            modal.hide();
          } else {
            // show form with errors
            const modalBody = document.getElementById('quickAddModalBody');
            modalBody.innerHTML = json.form_html || '<div class="alert alert-danger">Erro de validação</div>';
            const newForm = modalBody.querySelector('form');
            if (newForm) attachModalFormHandler(newForm, url, target, modal);
          }
        } catch (err) {
          console.error(err);
          alert('Erro ao submeter formulário');
        }
      };
      form.addEventListener('submit', onSubmit);
    }
    // Setup cliente form handlers (derived from fornecedor pattern)
    function setupClienteFormHandlers() {
      const clienteForm = document.getElementById('clienteForm');
      if (!clienteForm) return;

      // mark when submit event happens to avoid duplicate submissions
      clienteForm.addEventListener('submit', function (ev) {
        clienteForm._submitTriggered = true;
      }, true);

      // Synchronize enhanced selects (Choices/Select2) before validation
      function syncFormBeforeSubmit() {
        try {
          const prazoSelect = document.getElementById('id_prazo_pagamento_padrao_select');
          if (prazoSelect) {
            try { prazoSelect.dispatchEvent(new Event('change', {bubbles:true})); } catch(e){}
            if (prazoSelect.options.length <= 1) {
              const possible = document.querySelector('.choices') || document.querySelector('.select2');
              if (possible) {
                const text = possible.querySelector('.choices__item--selectable, .select2-selection__rendered');
                if (text) {
                  const term = (text.textContent || '').trim();
                  for (const opt of prazoSelect.options) {
                    if ((opt.textContent||'').trim().indexOf(term) !== -1) { opt.selected = true; prazoSelect.value = opt.value; break; }
                  }
                  try { prazoSelect.dispatchEvent(new Event('change', {bubbles:true})); } catch(e){}
                }
              }
            }
          }

          const moedaSelect = document.getElementById('id_moeda_padrao');
          if (moedaSelect) {
            try { moedaSelect.dispatchEvent(new Event('change', {bubbles:true})); } catch(e){}
          }
        } catch (e) { console.error('syncFormBeforeSubmit error', e); }
      }

      // Strong client-side validation: show clear alert if form invalid and focus first invalid field
      clienteForm.addEventListener('submit', function(ev){
        try {
          syncFormBeforeSubmit();
          if (!clienteForm.checkValidity()) {
            ev.preventDefault();
            ev.stopPropagation();
            const invalids = Array.from(clienteForm.querySelectorAll(':invalid'));
            const msgs = invalids.map(i => {
              try {
                const id = i.id || i.name || '(campo)';
                let label = null;
                try { label = clienteForm.querySelector("label[for='"+id+"']").textContent; } catch(e){}
                label = label || i.getAttribute('aria-label') || i.name || i.id || '(campo)';
                return `${label}`;
              } catch(e){ return '(campo inválido)'; }
            });
            showClientAlert('Campos obrigatórios faltando: ' + msgs.join(', '), 'danger');
            if (invalids.length) {
              try { invalids[0].focus(); } catch(e){}
            }
            try { const btn = document.getElementById('clienteSaveBtn'); if (btn) btn.disabled = false; } catch(e){}
            return false;
          }
          try { const btn = document.getElementById('clienteSaveBtn'); if (btn) { btn.disabled = true; showClientAlert('Enviando formulário...', 'info'); } } catch(e){}
        } catch(err) { console.error('submit-validation error', err); }
      }, false);

      clienteForm.addEventListener('invalid', function (ev) {
        try { console.warn('invalid field on submit', ev.target.name || ev.target.id, ev.target); } catch(e){}
      }, true);

      const saveBtn = clienteForm.querySelector('button[type="submit"]');
      if (saveBtn) {
        saveBtn.addEventListener('click', function (ev) {
          try {
            if (clienteForm._submitting) return; // already submitting
            clienteForm._submitting = true;
            try { saveBtn.disabled = true; } catch(e){}
            try {
              if (typeof clienteForm.requestSubmit === 'function') clienteForm.requestSubmit();
              else clienteForm.submit();
            } catch (err) {
              console.error('programmatic submit failed', err);
              clienteForm._submitting = false;
              try { saveBtn.disabled = false; } catch(e){}
            }
          } catch (err) { console.error('Save button handler error', err); }
        });

        const topBtn = document.getElementById('clienteSaveBtn');
        if (topBtn && topBtn !== saveBtn) {
          topBtn.addEventListener('click', function(ev){
            try { if (clienteForm && typeof clienteForm.requestSubmit === 'function') clienteForm.requestSubmit(); else if (clienteForm) clienteForm.submit(); } catch(e){ console.error('fallback submit failed', e); }

            setTimeout(async function(){
              try {
                if (clienteForm && !clienteForm._submitTriggered) {
                  console.warn('submit not triggered, performing AJAX fallback');
                  const fd = new FormData(clienteForm);
                  const url = clienteForm.action || window.location.href;
                  const resp = await fetch(url, {method: 'POST', body: fd, headers: {'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest'}});
                  const text = await resp.text();
                  if (resp.redirected) { window.location = resp.url; return; }
                  if (text && text.indexOf('<form') !== -1 && text.indexOf('name="razao_social"') !== -1) { document.open(); document.write(text); document.close(); return; }
                  window.location.reload();
                }
              } catch(err) { console.error('ajax fallback submit failed', err); }
            }, 250);
          });
        }
      }

      // Ensure moeda added events are handled
      const moedaSelect = document.getElementById('id_moeda_padrao');
      if (moedaSelect) {
        moedaSelect.addEventListener('moeda:added', function (e) {
          try { console.log('moeda:added event received', e.detail); } catch(e){}
          try {
            if (window.Choices && moedaSelect._choicesInstance) {
              moedaSelect._choicesInstance.setChoices(Array.from(moedaSelect.options).map(o=>({value:o.value,label:o.text})), 'value','label', false);
            }
            try { moedaSelect.dispatchEvent(new Event('change', {bubbles: true})); } catch(e){}
          } catch(e){ console.error('failed to update enhanced select', e); }

          try {
            const nativeCount = moedaSelect.options.length;
            if (nativeCount <= 1) {
              const container = moedaSelect.parentElement;
              const newSel = document.createElement('select');
              newSel.className = moedaSelect.className || 'form-select';
              newSel.id = moedaSelect.id || 'id_moeda_padrao';
              newSel.name = moedaSelect.name || 'moeda_padrao';
              const globalMoedas = window.__cadastros_moedas || Array.from(moedaSelect.options).map(o=>({value:o.value,label:o.text}));
              (globalMoedas || []).forEach(m => { const o = document.createElement('option'); o.value = m.value || m.codigo || m.codigo; o.textContent = m.label || m.nome || m.nome; if (m.value === e.detail.codigo || m.codigo === e.detail.codigo) o.selected = true; newSel.appendChild(o); });
              if (container) container.insertBefore(newSel, moedaSelect);
              moedaSelect.remove();
            }
          } catch(err){ console.error('fallback select rebuild error', err); }

          try {
            const prazoSelect = document.getElementById('id_prazo_pagamento_padrao_select');
            if (prazoSelect) {
              prazoSelect.addEventListener('change', function(ev){ try { /* Prazo preset changed: no-op */ } catch(e){} });
            }
          } catch(e){ console.error('prazo select bind failed', e); }
        });
      }
    }

    // initialize handlers
    setupClienteFormHandlers();
  });
})();