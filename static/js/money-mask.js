/**
 * Máscara de valor monetário no padrão brasileiro (1.234,56) para inputs com a
 * classe "money-mask-input".
 *
 * Cada input original vira um campo hidden (o que é de fato enviado ao
 * servidor, sempre em decimal simples "1234.56" — formato que o Django aceita
 * sem exigir localize=True) e ganha ao lado um campo de texto visível, onde o
 * usuário digita/vê o valor formatado em BR. Os dois ficam sincronizados a
 * cada tecla, sem depender da ordem de listeners no evento "submit".
 */
(function () {
  'use strict';

  function centsFromRawDecimal(raw) {
    if (raw === null || raw === undefined || raw === '') return 0;
    var parsed = parseFloat(String(raw).replace(',', '.'));
    return isNaN(parsed) ? 0 : Math.round(parsed * 100);
  }

  function formatBR(cents) {
    var negative = cents < 0;
    var digits = String(Math.abs(cents)).padStart(3, '0');
    var intPart = digits.slice(0, -2).replace(/^0+(?=\d)/, '');
    var centPart = digits.slice(-2);
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (negative ? '-' : '') + intPart + ',' + centPart;
  }

  function plainDecimal(cents) {
    var negative = cents < 0;
    var digits = String(Math.abs(cents)).padStart(3, '0');
    return (negative ? '-' : '') + digits.slice(0, -2) + '.' + digits.slice(-2);
  }

  function attach(input) {
    if (input.dataset.moneyMaskBound) return;
    input.dataset.moneyMaskBound = '1';

    var allowNegative = input.dataset.allowNegative === '1';
    var cents = centsFromRawDecimal(input.value);
    var hasValue = input.value.trim() !== '';

    var display = document.createElement('input');
    display.type = 'text';
    display.className = input.className;
    if (input.id) display.id = input.id;
    display.setAttribute('inputmode', 'decimal');
    display.placeholder = input.getAttribute('placeholder') || '0,00';
    display.autocomplete = 'off';
    if (input.hasAttribute('required')) display.required = true;
    if (input.disabled) display.disabled = true;
    display.value = hasValue ? formatBR(cents) : '';

    input.type = 'hidden';
    input.removeAttribute('id');
    input.value = hasValue ? plainDecimal(cents) : '';

    input.parentNode.insertBefore(display, input);

    display.addEventListener('input', function () {
      var negative = allowNegative && display.value.trim().charAt(0) === '-';
      var digits = display.value.replace(/\D/g, '');
      var c = digits === '' ? 0 : parseInt(digits, 10);
      if (negative) c = -c;
      display.value = digits === '' ? '' : formatBR(c);
      input.value = digits === '' ? '' : plainDecimal(c);
    });

    display.addEventListener('focus', function () {
      display.select();
    });
  }

  function init(root) {
    (root || document).querySelectorAll('.money-mask-input').forEach(attach);
  }

  document.addEventListener('DOMContentLoaded', function () {
    init(document);
  });

  window.MoneyMask = {
    init: init,
    parse: function (displayInput) {
      var raw = displayInput && displayInput.value ? displayInput.value : '';
      var normalized = raw.replace(/\./g, '').replace(',', '.');
      var parsed = parseFloat(normalized);
      return isNaN(parsed) ? 0 : parsed;
    }
  };
})();
