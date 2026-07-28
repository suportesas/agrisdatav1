/**
 * Combobox unificado: dropdown + busca + rolagem infinita, sobre o Select2.
 *
 * Contrato do backend: GET <url>?q=<termo>&page=<n> (+ extraParams), retorna
 * {results: [{id, text, ...}], pagination: {more: bool}}. Um `q` vazio deve
 * retornar a primeira página sem filtro (não uma lista vazia) — é isso que
 * faz o campo já mostrar registros ao abrir, sem precisar digitar nada.
 */

/**
 * Select2 core (mesmo na versão usada aqui, 4.1.0-rc.0) nunca ganhou uma opção
 * oficial pra travar a direção do dropdown — ele decide sozinho "acima"/"abaixo"
 * conforme o espaço na viewport, e some da tela do usuário quando decide "acima"
 * perto do rodapé. Isso adiciona a opção `dropdownPosition: 'below'|'above'|'auto'`
 * reescrevendo o método interno de posicionamento (mesma técnica do plugin
 * select2-dropdownPosition — https://github.com/andreivictor/select2-dropdownPosition).
 * Roda uma única vez, no carregamento deste arquivo.
 */
(function ($) {
  if (!$ || !$.fn || !$.fn.select2 || !$.fn.select2.amd) return;
  var Defaults = $.fn.select2.amd.require('select2/defaults');
  if (Defaults.defaults.__agrisDropdownPositionPatched) return;
  Defaults.defaults.__agrisDropdownPositionPatched = true;
  $.extend(Defaults.defaults, { dropdownPosition: 'auto' });

  var AttachBody = $.fn.select2.amd.require('select2/dropdown/attachBody');

  AttachBody.prototype._positionDropdown = function () {
    var $window = $(window);

    var isCurrentlyAbove = this.$dropdown.hasClass('select2-dropdown--above');
    var isCurrentlyBelow = this.$dropdown.hasClass('select2-dropdown--below');

    var newDirection = null;

    var offset = this.$container.offset();
    offset.bottom = offset.top + this.$container.outerHeight(false);

    var container = { height: this.$container.outerHeight(false) };
    container.top = offset.top;
    container.bottom = offset.top + container.height;

    var dropdown = { height: this.$dropdown.outerHeight(false) };

    // Barras fixas tipo .app-footer-bar (Salvar/Cancelar, sticky no rodapé) ficam
    // por cima do conteúdo mas não reduzem $window.height() — sem descontar a
    // altura dela aqui, o cálculo de "cabe embaixo?" dá certo mesmo quando o
    // dropdown vai ficar coberto por ela.
    var $footerBar = $('.app-footer-bar:visible').last();
    var reservedBottom = $footerBar.length ? $footerBar.outerHeight(true) : 0;

    var viewport = {
      top: $window.scrollTop(),
      bottom: $window.scrollTop() + $window.height() - reservedBottom,
    };

    var enoughRoomAbove = viewport.top < (offset.top - dropdown.height);
    var enoughRoomBelow = viewport.bottom > (offset.bottom + dropdown.height);

    var css = { left: offset.left, top: container.bottom };

    var $offsetParent = this.$dropdownParent;
    if ($offsetParent.css('position') === 'static') {
      $offsetParent = $offsetParent.offsetParent();
    }
    var parentOffset = $offsetParent.offset();
    css.top -= parentOffset.top;
    css.left -= parentOffset.left;

    var dropdownPositionOption = this.options.get('dropdownPosition');

    if (dropdownPositionOption === 'above' || dropdownPositionOption === 'below') {
      newDirection = dropdownPositionOption;
    } else {
      if (!isCurrentlyAbove && !isCurrentlyBelow) newDirection = 'below';
      if (!enoughRoomBelow && enoughRoomAbove && !isCurrentlyAbove) newDirection = 'above';
      else if (!enoughRoomAbove && enoughRoomBelow && isCurrentlyAbove) newDirection = 'below';
    }

    if (newDirection === 'above' || (isCurrentlyAbove && newDirection !== 'below')) {
      css.top = container.top - parentOffset.top - dropdown.height;
    }

    if (newDirection != null) {
      this.$dropdown
        .removeClass('select2-dropdown--below select2-dropdown--above')
        .addClass('select2-dropdown--' + newDirection);
      this.$container
        .removeClass('select2-container--below select2-container--above')
        .addClass('select2-container--' + newDirection);
    }

    this.$dropdownContainer.css(css);
  };
})(window.jQuery);

(function (global) {
  var DEFAULT_LANGUAGE = {
    inputTooShort: function () { return 'Digite para buscar...'; },
    noResults: function () { return 'Nenhum resultado encontrado'; },
    searching: function () { return 'Buscando...'; },
    loadingMore: function () { return 'Carregando mais resultados…'; },
    errorLoading: function () { return 'Não foi possível carregar os resultados'; },
  };

  function initSelect2Ajax(selector, options) {
    options = options || {};
    // $() wraps a CSS-selector string, a raw DOM element, or an already-jQuery
    // object correctly in all three cases — do NOT special-case strings only,
    // callers pass raw elements too (e.g. `this` inside a jQuery .each()).
    var $el = $(selector);
    var config = $.extend(true, {
      theme: 'bootstrap-5',
      width: '100%',
      allowClear: true,
      placeholder: options.placeholder || 'Selecione...',
      minimumInputLength: 0,
      dropdownPosition: 'auto',
      language: DEFAULT_LANGUAGE,
      dropdownParent: options.dropdownParent || undefined,
      ajax: {
        url: options.url,
        dataType: 'json',
        delay: 300,
        cache: true,
        data: function (params) {
          var extra = typeof options.extraParams === 'function' ? options.extraParams() : (options.extraParams || {});
          return $.extend({ q: params.term || '', page: params.page || 1 }, extra);
        },
        processResults: function (data, params) {
          params.page = params.page || 1;
          return {
            results: data.results || [],
            pagination: { more: !!(data.pagination && data.pagination.more) },
          };
        },
      },
    }, options.select2Options || {});
    return $el.select2(config);
  }

  // Auto-inicializa qualquer <select class="select2-ajax" data-ajax-url="..."> —
  // é o que core.widgets.Select2AjaxWidget gera. Basta chamar isso uma vez
  // após o DOM (e o Select2) estarem carregados; seguro de chamar de novo
  // depois de clonar linhas de formset (pula selects já inicializados).
  function initFromDataAttrs(root) {
    var scope = root ? $(root) : $(document);
    scope.find('select.select2-ajax[data-ajax-url]').each(function () {
      var $el = $(this);
      if ($el.data('select2')) return;
      // #empty-form-container holds the hidden formset row template that
      // "Adicionar Item" clones via cloneNode(true). If it gets select2-ified
      // here, that markup (the extra <span class="select2-container">) rides
      // along in every clone, then gets select2-ified *again* on the clone —
      // two stacked "Buscar produto" boxes per row instead of one.
      if ($el.closest('#empty-form-container').length) return;
      var extra = {};
      try { extra = JSON.parse($el.attr('data-extra-params') || '{}'); } catch (e) {}
      // Select2 por padrão anexa o dropdown no <body>; dentro de um modal
      // Bootstrap isso costuma ficar atrás do backdrop ou cortado. Ancorando
      // no próprio modal resolve sem precisar de init explícito por campo.
      var $modal = $el.closest('.modal');
      initSelect2Ajax($el, {
        url: $el.data('ajax-url'),
        placeholder: $el.data('placeholder'),
        extraParams: extra,
        dropdownParent: $modal.length ? $modal : undefined,
      });
    });
  }

  global.AgrisSelect2 = { init: initSelect2Ajax, initFromDataAttrs: initFromDataAttrs };
})(window);
