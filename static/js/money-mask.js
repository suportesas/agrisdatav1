/**
 * Máscara de valor decimal no padrão brasileiro (1.234,56) para inputs com a
 * classe "money-mask-input". Casas decimais configuráveis via atributo
 * data-decimals (default 2) — cobre tanto valores monetários (2 casas) quanto
 * quantidades/alíquotas/taxas de câmbio (3-4 casas).
 *
 * Cada input original vira um campo hidden (o que é de fato enviado ao
 * servidor, sempre em decimal simples "1234.56" — formato que o Django aceita
 * sem exigir localize=True) e ganha ao lado um campo de texto visível, onde o
 * usuário digita/vê o valor formatado em BR. Os dois ficam sincronizados a
 * cada tecla, sem depender da ordem de listeners no evento "submit".
 *
 * init(root) é idempotente e pode ser chamado de novo sobre conteúdo clonado
 * via cloneNode (ex: uma linha de formset duplicada) — nesse caso os pares
 * hidden+display já existem no clone (cloneNode copia atributos, mas não os
 * listeners/propriedades JS), então init() apenas re-liga os listeners no par
 * existente em vez de criar um novo par.
 */
(function () {
  'use strict';

  function decimalsOf(el) {
    var n = parseInt(el.dataset.decimals, 10);
    return isNaN(n) || n < 0 ? 2 : n;
  }

  function unitsFromRawDecimal(raw, decimals) {
    if (raw === null || raw === undefined || raw === '') return 0;
    var parsed = parseFloat(String(raw).replace(',', '.'));
    return isNaN(parsed) ? 0 : Math.round(parsed * Math.pow(10, decimals));
  }

  function formatBR(units, decimals) {
    var negative = units < 0;
    var digits = String(Math.abs(units)).padStart(decimals + 1, '0');
    var intPart = decimals > 0 ? digits.slice(0, -decimals) : digits;
    var fracPart = decimals > 0 ? digits.slice(-decimals) : '';
    intPart = intPart.replace(/^0+(?=\d)/, '');
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (negative ? '-' : '') + intPart + (decimals > 0 ? ',' + fracPart : '');
  }

  function plainDecimal(units, decimals) {
    var negative = units < 0;
    var digits = String(Math.abs(units)).padStart(decimals + 1, '0');
    var intPart = decimals > 0 ? digits.slice(0, -decimals) : digits;
    var fracPart = decimals > 0 ? digits.slice(-decimals) : '';
    return (negative ? '-' : '') + intPart + (decimals > 0 ? '.' + fracPart : '');
  }

  function wire(display, hidden) {
    var decimals = decimalsOf(hidden);
    var allowNegative = hidden.dataset.allowNegative === '1';

    display._moneyMaskHidden = hidden;
    hidden._moneyMaskDisplay = display;

    display.addEventListener('input', function () {
      var negative = allowNegative && display.value.trim().charAt(0) === '-';
      var digits = display.value.replace(/\D/g, '');
      var u = digits === '' ? 0 : parseInt(digits, 10);
      if (negative) u = -u;
      display.value = digits === '' ? '' : formatBR(u, decimals);
      hidden.value = digits === '' ? '' : plainDecimal(u, decimals);
      // Relay para código legado que ainda escuta "input" no elemento original
      // (que virou o hidden depois da máscara ser aplicada).
      hidden.dispatchEvent(new Event('input', { bubbles: true }));
    });

    display.addEventListener('focus', function () {
      display.select();
    });
  }

  function attach(input) {
    var decimals = decimalsOf(input);
    var units = unitsFromRawDecimal(input.value, decimals);
    var hasValue = input.value.trim() !== '';

    var display = document.createElement('input');
    display.type = 'text';
    display.className = input.className;
    if (input.id) display.id = input.id;
    display.dataset.moneyMaskDisplay = '1';
    display.setAttribute('inputmode', 'decimal');
    display.placeholder = input.getAttribute('placeholder') || (decimals > 0 ? '0,' + '0'.repeat(decimals) : '0');
    display.autocomplete = 'off';
    if (input.hasAttribute('required')) display.required = true;
    if (input.disabled) display.disabled = true;
    if (input.hasAttribute('readonly')) display.readOnly = true;
    display.value = hasValue ? formatBR(units, decimals) : '';

    input.type = 'hidden';
    input.removeAttribute('id');
    input.value = hasValue ? plainDecimal(units, decimals) : '';

    input.parentNode.insertBefore(display, input);
    wire(display, input);
  }

  function init(root) {
    (root || document).querySelectorAll('.money-mask-input').forEach(function (el) {
      if (el.type === 'hidden') {
        if (el._moneyMaskDisplay) return;
        var display = el.previousElementSibling;
        if (display && display.dataset && display.dataset.moneyMaskDisplay) wire(display, el);
        return;
      }
      if (el.dataset.moneyMaskDisplay) return;
      attach(el);
    });
  }

  function resolvePair(idOrElement) {
    var el = typeof idOrElement === 'string' ? document.getElementById(idOrElement) : idOrElement;
    if (!el) return null;
    if (el._moneyMaskDisplay) return { display: el._moneyMaskDisplay, hidden: el };
    if (el._moneyMaskHidden) return { display: el, hidden: el._moneyMaskHidden };
    return null;
  }

  function setValue(idOrElement, rawValue) {
    var pair = resolvePair(idOrElement);
    if (!pair) return;
    var decimals = decimalsOf(pair.hidden);
    var hasValue = rawValue !== null && rawValue !== undefined && String(rawValue).trim() !== '';
    var units = hasValue ? unitsFromRawDecimal(rawValue, decimals) : 0;
    pair.display.value = hasValue ? formatBR(units, decimals) : '';
    pair.hidden.value = hasValue ? plainDecimal(units, decimals) : '';
  }

  function getValue(idOrElement) {
    var pair = resolvePair(idOrElement);
    if (!pair) return 0;
    var parsed = parseFloat(pair.hidden.value);
    return isNaN(parsed) ? 0 : parsed;
  }

  document.addEventListener('DOMContentLoaded', function () {
    init(document);
  });

  window.MoneyMask = {
    init: init,
    setValue: setValue,
    getValue: getValue,
    parse: function (displayInput) {
      var raw = displayInput && displayInput.value ? displayInput.value : '';
      var normalized = raw.replace(/\./g, '').replace(',', '.');
      var parsed = parseFloat(normalized);
      return isNaN(parsed) ? 0 : parsed;
    }
  };
})();
