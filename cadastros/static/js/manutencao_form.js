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
  fetch(`/cadastros/api/lote-produto-data/?vehicle_id=${vehicleSelect.value}`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(r => r.json())
    .then(data => { placaField.value = data.placa || ''; })
    .catch(() => { placaField.value = ''; });
}

// ── Busca de produto com autocomplete ────────────────────────────────────────

let _debounceTimer = null;

function buscarProduto(input) {
  clearTimeout(_debounceTimer);
  const q = input.value.trim();
  fecharDropdown(input);

  if (q.length < 2) return;

  _debounceTimer = setTimeout(() => {
    fetch(`/cadastros/api/produto-busca/?q=${encodeURIComponent(q)}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(r => r.json())
      .then(data => renderizarDropdown(input, data.results || []))
      .catch(() => {});
  }, 300);
}

function renderizarDropdown(input, results) {
  fecharDropdown(input);
  if (!results.length) return;

  const dropdown = document.createElement('ul');
  dropdown.className = 'list-group position-absolute w-100 shadow z-3 produto-dropdown';
  dropdown.style.top = '100%';
  dropdown.style.maxHeight = '220px';
  dropdown.style.overflowY = 'auto';

  results.forEach(item => {
    const li = document.createElement('li');
    li.className = 'list-group-item list-group-item-action py-1 px-2 small';
    li.style.cursor = 'pointer';
    li.innerHTML = `<strong>${item.nome}</strong> <span class="text-muted">${item.unidade_medida} &mdash; Estoque: ${parseFloat(item.quantidade_disponivel).toFixed(3)}</span>`;
    li.addEventListener('mousedown', e => {
      e.preventDefault();
      const row = input.closest('tr.formset-row');
      selecionarProduto(row, item);
    });
    dropdown.appendChild(li);
  });

  const wrapper = input.closest('td');
  wrapper.appendChild(dropdown);
}

function fecharDropdown(input) {
  const td = input.closest('td');
  if (!td) return;
  const existing = td.querySelector('.produto-dropdown');
  if (existing) existing.remove();
}

function selecionarProduto(row, item) {
  row.querySelector('input[name$="-lote"]').value = item.lote_id;
  row.querySelector('input[name$="-nome_produto"]').value = item.nome;
  row.querySelector('input[name$="-descricao"]').value = item.nome;
  row.querySelector('input[name$="-unidade_medida"]').value = item.unidade_medida;
  row.querySelector('input[name$="-valor_custo"]').value = parseFloat(item.valor_custo).toFixed(4);
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
    if (e.target.classList.contains('produto-search-input')) {
      buscarProduto(e.target);
    }
    if (e.target.classList.contains('quantidade-input') || e.target.classList.contains('desconto-input')) {
      const row = e.target.closest('tr.formset-row');
      if (row) recalcularTotal(row);
    }
  });

  document.addEventListener('focusout', function (e) {
    if (e.target.classList.contains('produto-search-input')) {
      setTimeout(() => fecharDropdown(e.target), 200);
    }
  });

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-remover-peca');
    if (btn) removerLinha(btn);
  });

  recalcularTodosTotais();
});
