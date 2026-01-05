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
    if (buscarCNPJBtn) {
      buscarCNPJBtn.addEventListener('click', async () => {
        const form = buscarCNPJBtn.closest('form');
        if (!form) return;
        const cnpjInput = form.querySelector('input[name="cnpj_cpf"]');
        if (!cnpjInput) { alert('Campo CNPJ/CPF não encontrado'); return; }
        const cnpj = (cnpjInput.value || '').replace(/\D/g, '');
        if (cnpj.length !== 14) { alert('Digite um CNPJ válido (14 dígitos)'); return; }

        const csrf = getCsrfToken();
        const loadingModalElem = document.getElementById('cnpjLoadingModal');
        const loadingModal = loadingModalElem ? new bootstrap.Modal(loadingModalElem) : null;
        try {
          buscarCNPJBtn.disabled = true;
          if (loadingModal) loadingModal.show();

          const resp = await fetch(cfg.buscar_cnpj_url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
              'X-CSRFToken': csrf,
              'Accept': 'application/json'
            },
            body: `cnpj=${cnpj}`
          });

          if (!resp.ok) {
            if (loadingModal) loadingModal.hide();
            const json = await resp.json().catch(() => ({}));
            alert(json.erro || 'Erro ao buscar CNPJ');
            return;
          }

          const data = await resp.json();

        if (data.sucesso && data.dados) {
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

            // If nothing changed, hide loader, show quick message and return
            if (changed.length === 0) {
              if (loadingModal) loadingModal.hide();
              const fb = document.getElementById('cnpjFeedback');
              if (fb) { fb.classList.remove('text-danger'); fb.classList.add('text-success'); fb.textContent = 'Nenhuma alteração detectada'; setTimeout(()=>{ fb.textContent='\u00A0'; fb.classList.remove('text-success'); }, 3000); }
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
              const fb = document.getElementById('cnpjFeedback');
              if (fb) { fb.classList.remove('text-danger'); fb.classList.add('text-success'); fb.textContent = 'Alterações confirmadas'; setTimeout(()=>{ fb.textContent='\u00A0'; fb.classList.remove('text-success'); }, 3500); }
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
              const fb = document.getElementById('cnpjFeedback');
              if (fb) { fb.classList.remove('text-success'); fb.classList.add('text-danger'); fb.textContent = 'Alterações revertidas'; setTimeout(()=>{ fb.textContent='\u00A0'; fb.classList.remove('text-danger'); }, 3500); }
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
  });
})();