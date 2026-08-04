/**
 * Formulário de manutenção: placa automática, busca de produto, linhas dinâmicas, total geral.
 */

// ── Utilitários ───────────────────────────────────────────────────────────────

function getPrefix() {
  return 'itens';
}

function getTotalForms() {
  return parseInt(document.getElementById(`id_${getPrefix()}-TOTAL_FORMS`).value, 10);
}

function setTotalForms(n) {
  document.getElementById(`id_${getPrefix()}-TOTAL_FORMS`).value = n;
}

// ── Placa automática ──────────────────────────────────────────────────────────

function preencherPlaca() {
  const vehicleSelect = document.getElementById('id_vehicle');
  const placaField = document.querySelector('input[name="placa"]');
  if (!vehicleSelect || !placaField) return;

  if (!vehicleSelect.value) {
    placaField.value = '';
    return;
  }

  placaField.value = '...';
  fetch(`/frota/api/lote-produto-data/?vehicle_id=${vehicleSelect.value}`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(r => r.json())
    .then(data => { placaField.value = data.placa || ''; })
    .catch(() => { placaField.value = ''; });
}

// ── Busca de produto (combobox Select2 padrão do sistema) ───────────────────

function inicializarSelect2Produto(scope) {
  if (window.jQuery && window.AgrisSelect2) {
    window.AgrisSelect2.initFromDataAttrs(scope);
  }
}

function selecionarProduto(row, data) {
  row.querySelector('input[name$="-lote"]').value = data.lote_id || '';
  row.querySelector('input[name$="-nome_produto"]').value = data.nome_produto || '';
  row.querySelector('input[name$="-descricao"]').value = data.nome_produto || '';
  row.querySelector('input[name$="-unidade_medida"]').value = data.unidade_medida || '';
  row.querySelector('input[name$="-valor_custo"]').value = parseFloat(data.valor_custo || 0).toFixed(4);
  recalcularTotal(row);
}

function limparProduto(row) {
  row.querySelector('input[name$="-lote"]').value = '';
  row.querySelector('input[name$="-nome_produto"]').value = '';
  row.querySelector('input[name$="-descricao"]').value = '';
  row.querySelector('input[name$="-unidade_medida"]').value = '';
  row.querySelector('input[name$="-valor_custo"]').value = '0.0000';
  recalcularTotal(row);
}

// ── Cálculo de totais ─────────────────────────────────────────────────────────

function recalcularTotal(row) {
  const qty = parseFloat(row.querySelector('.quantidade-input')?.value) || 0;
  const custo = parseFloat(row.querySelector('.custo-input')?.value) || 0;
  const desc = parseFloat(row.querySelector('.desconto-input')?.value) || 0;
  const total = Math.max(0, qty * custo - desc);
  const totalField = row.querySelector('.valor-total');
  if (totalField) totalField.value = total.toFixed(2);
  atualizarTotalGeral();
}

function atualizarTotalGeral() {
  let soma = 0;
  document.querySelectorAll('#pecas-tbody tr.formset-row').forEach(row => {
    if (row.style.display === 'none') return;
    soma += parseFloat(row.querySelector('.valor-total')?.value) || 0;
  });
  const el = document.getElementById('total-geral');
  if (el) el.textContent = `R$ ${soma.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function recalcularTodosTotais() {
  document.querySelectorAll('#pecas-tbody tr.formset-row').forEach(row => recalcularTotal(row));
}

// ── Linhas dinâmicas ──────────────────────────────────────────────────────────

function adicionarLinha() {
  const template = document.getElementById('empty-form-template');
  if (!template) return;

  const idx = getTotalForms();
  const clone = template.content.cloneNode(true);
  const tr = clone.querySelector('tr');

  tr.innerHTML = tr.innerHTML.replaceAll('__prefix__', idx);
  tr.setAttribute('data-form-index', idx);

  document.getElementById('pecas-tbody').appendChild(tr);
  setTotalForms(idx + 1);
  inicializarSelect2Produto(tr);
  atualizarTotalGeral();
}

function removerLinha(btn) {
  const row = btn.closest('tr.formset-row');
  if (!row) return;

  const idInput = row.querySelector('input[name$="-id"]');
  const deleteInput = row.querySelector('input[name$="-DELETE"]');

  if (idInput && idInput.value) {
    // Registro existente — marcar para deleção pelo Django
    if (deleteInput) deleteInput.value = 'on';
    row.style.display = 'none';
  } else {
    row.remove();
  }
  atualizarTotalGeral();
}

// ── Inicialização e event delegation ─────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
  const vehicleSelect = document.getElementById('id_vehicle');
  if (vehicleSelect) {
    vehicleSelect.addEventListener('change', preencherPlaca);
  }

  const btnAdicionar = document.getElementById('btn-adicionar-peca');
  if (btnAdicionar) {
    btnAdicionar.addEventListener('click', adicionarLinha);
  }

  document.addEventListener('input', function (e) {
    if (e.target.classList.contains('quantidade-input') || e.target.classList.contains('desconto-input') || e.target.classList.contains('custo-input')) {
      const row = e.target.closest('tr.formset-row');
      if (row) recalcularTotal(row);
    }
  });

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-remover-peca');
    if (btn) removerLinha(btn);
  });

  if (window.jQuery) {
    // Select2 (usado no campo #id_vehicle) só dispara 'change' nativo de forma
    // confiável em alguns navegadores/versões — 'select2:select'/'select2:clear'
    // são os eventos próprios do plugin, sempre disparados na seleção via AJAX.
    $(document).on('select2:select select2:clear', '#id_vehicle', preencherPlaca);

    $(document).on('select2:select', '.produto-select', function (e) {
      const row = this.closest('tr.formset-row');
      const produtoId = e.params.data.id;
      if (!row || !produtoId) return;
      fetch(`/frota/api/lote-produto-data/?produto_id=${produtoId}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(r => r.json())
        .then(data => { if (!data.error) selecionarProduto(row, data); })
        .catch(() => {});
    });

    $(document).on('select2:clear', '.produto-select', function () {
      const row = this.closest('tr.formset-row');
      if (row) limparProduto(row);
    });
  }

  recalcularTodosTotais();
});
