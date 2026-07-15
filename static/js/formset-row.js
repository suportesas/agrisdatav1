// Generic "clone last row" Django formset row add/remove helper for complex form pages.
// Extracted/generalized from the pagamentos/duplicatas/referencias formset handlers in
// templates/faturamento/nota_fiscal/form.html (that file is left untouched — this is new
// shared infrastructure for future complex-form migrations).
//
// Usage:
//   var fs = FormsetRow.init({
//     prefix: 'itens',                       // Django formset prefix
//     container: document.getElementById('items-body'),
//     rowSelector: '.item-row',
//     addButton: document.getElementById('add-item'),
//     onClone: function (newRow, idx) { ... },   // optional: set per-field defaults on the new row
//     onRemove: function (row) { ... },          // optional: called after a row is removed/hidden
//   });
//   // fs.renumber({ numberField: '-numero_item', displaySelector: '.item-seq', countBadgeId: 'items-count-badge', countLabel: 'itens' });
//
// Notes:
// - Assumes the standard "-N-" Django formset name/id pattern (e.g. name="itens-0-produto").
// - Requires at least one existing row in `container` to clone from. If a formset can render
//   zero rows (extra=0, min_num=0), the caller must handle the empty-state case separately —
//   this helper does not fabricate row markup from scratch.
// - Soft-deletes existing rows (hides + checks the "-DELETE" checkbox) and hard-removes
//   unsaved/new rows (no "-DELETE" field), matching Django formset can_delete semantics.
(function (global) {
  function renameIndex(el, idx) {
    el.name = el.name.replace(/-\d+-/, '-' + idx + '-');
    if (el.id) el.id = el.id.replace(/-\d+-/, '-' + idx + '-');
  }

  function resetField(el) {
    if (el.type === 'checkbox' || el.type === 'radio') {
      el.checked = false;
    } else {
      el.value = '';
    }
  }

  function totalFormsInput(prefix) {
    return document.getElementById('id_' + prefix + '-TOTAL_FORMS');
  }

  function attachRemove(row, opts) {
    var btn = row.querySelector(opts.removeButtonSelector || '.row-action.danger, .btn-remove-row');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var chk = row.querySelector('input[type=checkbox][name$="-DELETE"]');
      if (chk) {
        chk.checked = true;
        row.style.display = 'none';
      } else {
        row.remove();
      }
      if (typeof opts.onRemove === 'function') opts.onRemove(row);
    });
  }

  function init(opts) {
    var container = opts.container;
    var rowSelector = opts.rowSelector;
    var total = totalFormsInput(opts.prefix);

    function addRow() {
      var rows = Array.prototype.slice.call(container.querySelectorAll(rowSelector));
      var lastRow = rows[rows.length - 1];
      if (!lastRow || !total) return null;

      var idx = parseInt(total.value, 10);
      var newRow = lastRow.cloneNode(true);
      newRow.querySelectorAll('input,select,textarea').forEach(function (el) {
        renameIndex(el, idx);
        resetField(el);
      });
      newRow.style.display = '';

      if (typeof opts.onClone === 'function') opts.onClone(newRow, idx);

      container.appendChild(newRow);
      total.value = idx + 1;
      attachRemove(newRow, opts);

      return newRow;
    }

    container.querySelectorAll(rowSelector).forEach(function (row) {
      attachRemove(row, opts);
    });

    if (opts.addButton) {
      opts.addButton.addEventListener('click', addRow);
    }

    return {
      addRow: addRow,
      renumber: function (cfg) {
        var n = 1;
        container.querySelectorAll(rowSelector).forEach(function (row) {
          if (row.style.display === 'none') return;
          if (cfg.numberField) {
            var el = row.querySelector('input[name$="' + cfg.numberField + '"]');
            if (el) el.value = n;
          }
          if (cfg.displaySelector) {
            var seq = row.querySelector(cfg.displaySelector);
            if (seq) seq.textContent = n;
          }
          n++;
        });
        if (cfg.countBadgeId) {
          var badge = document.getElementById(cfg.countBadgeId);
          if (badge) badge.textContent = (n - 1) + ' ' + (cfg.countLabel || 'itens');
        }
      },
    };
  }

  global.FormsetRow = { init: init };
})(window);
