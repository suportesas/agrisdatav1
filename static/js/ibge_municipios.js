/**
 * ibge_municipios.js
 * Autocomplete de municípios via API pública do IBGE.
 * Uso: setupIBGEAutocomplete('id_uf', 'id_municipio', 'id_codigo_municipio', 'dl-mun-id')
 */
(function (global) {
  'use strict';

  var _cache = {};

  function normalize(str) {
    return (str || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  function fetchMunicipios(uf, cb) {
    uf = (uf || '').trim().toUpperCase();
    if (uf.length !== 2) { cb([]); return; }
    if (_cache[uf]) { cb(_cache[uf]); return; }
    fetch('https://servicodados.ibge.gov.br/api/v1/localidades/estados/' + uf + '/municipios')
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (data) {
        _cache[uf] = (data || []).map(function (m) {
          return { id: String(m.id), nome: m.nome };
        });
        cb(_cache[uf]);
      })
      .catch(function () { cb([]); });
  }

  function fillDatalist(dlId, municipios) {
    var dl = document.getElementById(dlId);
    if (!dl) return;
    dl.innerHTML = municipios.map(function (m) {
      return '<option value="' + m.nome + '" data-codigo="' + m.id + '">';
    }).join('');
  }

  function autofill(munInput, codInput, municipios) {
    var nome = normalize(munInput.value);
    if (!nome) return;
    var found = municipios.find(function (m) { return normalize(m.nome) === nome; });
    if (found) {
      codInput.value = found.id;
      codInput.dispatchEvent(new Event('change'));
    }
  }

  /**
   * Configura autocomplete IBGE para um par de campos (UF + Município + Código).
   * @param {string} ufId       - id do input de UF
   * @param {string} munId      - id do input de município
   * @param {string} codId      - id do input de código IBGE
   * @param {string} datalistId - id do <datalist> (deve existir no HTML)
   */
  function setupIBGEAutocomplete(ufId, munId, codId, datalistId) {
    var ufEl  = document.getElementById(ufId);
    var munEl = document.getElementById(munId);
    var codEl = document.getElementById(codId);
    if (!ufEl || !munEl || !codEl) return;

    munEl.setAttribute('list', datalistId);
    munEl.setAttribute('autocomplete', 'off');

    function getCache() {
      return _cache[(ufEl.value || '').trim().toUpperCase()] || [];
    }

    function load() {
      var uf = (ufEl.value || '').trim().toUpperCase();
      if (uf.length !== 2) return;
      fetchMunicipios(uf, function (muns) {
        fillDatalist(datalistId, muns);
        autofill(munEl, codEl, muns);
      });
    }

    ufEl.addEventListener('change', load);
    ufEl.addEventListener('blur', load);

    // 'input' dispara ao selecionar do datalist imediatamente (sem precisar sair do campo)
    munEl.addEventListener('input', function () { autofill(munEl, codEl, getCache()); });
    munEl.addEventListener('change', function () { autofill(munEl, codEl, getCache()); });

    // Pré-carregar se UF já preenchida (edição de registro existente)
    if ((ufEl.value || '').trim().length === 2) load();
  }

  global.setupIBGEAutocomplete = setupIBGEAutocomplete;
  global._ibgeMunCache = _cache;

}(window));
