(function () {
  'use strict';

  const checkboxes = document.querySelectorAll('.chk-nota');
  const chkTodos   = document.getElementById('chk-todos');
  const barraSelecao   = document.getElementById('barra-selecao');
  const qtdEl      = document.getElementById('qtd-selecionadas');
  const totalEl    = document.getElementById('total-selecionado');
  const nomeClienteEl = document.getElementById('nome-cliente-sel');
  const btnFechar  = document.getElementById('btn-fechar-lote');

  let clienteIdLock = null; // ID do cliente da 1ª nota selecionada

  function formatBRL(value) {
    return value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function atualizar() {
    const selecionadas = [...checkboxes].filter(c => c.checked);
    const total = selecionadas.reduce((acc, c) => acc + parseFloat(c.dataset.valor || 0), 0);

    qtdEl.textContent  = selecionadas.length;
    totalEl.textContent = formatBRL(total);
    btnFechar.disabled = selecionadas.length === 0;

    if (selecionadas.length > 0) {
      barraSelecao.classList.remove('d-none');
      nomeClienteEl.textContent = selecionadas[0].dataset.clienteNome || '';
    } else {
      barraSelecao.classList.add('d-none');
      nomeClienteEl.textContent = '';
    }
  }

  function aplicarLock(clienteId) {
    clienteIdLock = clienteId;
    checkboxes.forEach(c => {
      if (c.dataset.clienteId !== String(clienteId)) {
        c.disabled = true;
        c.closest('tr').classList.add('table-secondary', 'opacity-50');
      }
    });
  }

  function liberarLock() {
    clienteIdLock = null;
    checkboxes.forEach(c => {
      c.disabled = false;
      c.closest('tr').classList.remove('table-secondary', 'opacity-50');
    });
  }

  checkboxes.forEach(chk => {
    chk.addEventListener('change', function () {
      const selecionadas = [...checkboxes].filter(c => c.checked);

      if (selecionadas.length === 0) {
        // Nenhuma selecionada — libera tudo
        liberarLock();
      } else if (this.checked && clienteIdLock === null) {
        // Primeira seleção — impõe lock de cliente
        aplicarLock(this.dataset.clienteId);
      }

      atualizar();
    });
  });

  // Selecionar/desmarcar todas (visíveis e habilitadas)
  if (chkTodos) {
    chkTodos.addEventListener('change', function () {
      const habilitadas = [...checkboxes].filter(c => !c.disabled);

      if (this.checked && habilitadas.length > 0) {
        // Impõe lock do cliente da primeira habilitada se não houver lock
        if (clienteIdLock === null) {
          aplicarLock(habilitadas[0].dataset.clienteId);
        }
        [...checkboxes].filter(c => !c.disabled).forEach(c => { c.checked = true; });
      } else {
        checkboxes.forEach(c => { c.checked = false; });
        liberarLock();
      }

      atualizar();
    });
  }

  atualizar();
})();
