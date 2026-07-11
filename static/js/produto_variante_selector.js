/**
 * ProdutoVarianteSelector
 *
 * Widget reutilizável para seleção de produto com suporte a variantes.
 * Quando o produto base selecionado possui variantes, abre dropdowns para
 * cada dimensão (Variedade, Marca, Calibre...) e resolve automaticamente
 * o SKU exato, gerando a descrição concatenada.
 *
 * Uso:
 *   new ProdutoVarianteSelector(containerElement, options)
 *
 * Options:
 *   urls.buscar         – URL do endpoint ajax_buscar_produtos
 *   urls.dimensoes      – URL do endpoint ajax_variante_dimensoes
 *   urls.resolver       – URL do endpoint ajax_variante_resolver
 *   csrfToken           – CSRF token para POST
 *   onResolve(produto)  – callback quando o produto final é resolvido
 *                         produto: {produto_id, nome_completo, codigo, preco_venda, unidade_sigla}
 *   initialProdutoId    – ID do produto já selecionado (edição)
 *   initialProdutoText  – Texto do produto já selecionado (edição)
 *   somenteBases        – Se true, busca apenas produtos base (padrão: false)
 */
class ProdutoVarianteSelector {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.opts = Object.assign({
      urls: {},
      csrfToken: '',
      onResolve: null,
      initialProdutoId: null,
      initialProdutoText: '',
      somenteBases: false,
    }, options);

    this._produtoBaseId = null;
    this._produtoFinalId = null;
    this._dimensoes = [];
    this._debounceTimer = null;

    this._render();
    if (this.opts.initialProdutoId) {
      this._carregarInicial();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // DOM
  // ──────────────────────────────────────────────────────────────────
  _render() {
    this.container.innerHTML = `
      <div class="pvs-base-wrapper">
        <label class="form-label fw-semibold">Produto <span class="text-danger">*</span></label>
        <div class="position-relative">
          <input type="text" class="form-control pvs-search"
                 placeholder="Digite para buscar produto…" autocomplete="off">
          <div class="pvs-dropdown position-absolute w-100 bg-white border rounded shadow-sm"
               style="z-index:1050;max-height:250px;overflow-y:auto;display:none;top:100%;left:0;"></div>
        </div>
        <input type="hidden" class="pvs-produto-id">
      </div>
      <div class="pvs-atributos mt-2" style="display:none;"></div>
      <div class="pvs-resultado mt-2" style="display:none;"></div>
    `;

    this.searchInput = this.container.querySelector('.pvs-search');
    this.dropdown = this.container.querySelector('.pvs-dropdown');
    this.produtoIdInput = this.container.querySelector('.pvs-produto-id');
    this.atributosArea = this.container.querySelector('.pvs-atributos');
    this.resultadoArea = this.container.querySelector('.pvs-resultado');

    this.searchInput.addEventListener('input', () => this._onSearchInput());
    this.searchInput.addEventListener('blur', () => setTimeout(() => this.dropdown.style.display = 'none', 200));
    this.searchInput.addEventListener('focus', () => {
      if (this.searchInput.value.length >= 2) this._buscar(this.searchInput.value);
    });
  }

  // ──────────────────────────────────────────────────────────────────
  // BUSCA
  // ──────────────────────────────────────────────────────────────────
  _onSearchInput() {
    clearTimeout(this._debounceTimer);
    const q = this.searchInput.value.trim();
    if (q.length < 2) { this.dropdown.style.display = 'none'; return; }
    this._debounceTimer = setTimeout(() => this._buscar(q), 280);
  }

  async _buscar(q) {
    const params = new URLSearchParams({ q });
    if (this.opts.somenteBases) params.set('apenas_base', '1');
    try {
      const res = await fetch(`${this.opts.urls.buscar}?${params}`);
      const data = await res.json();
      this._renderDropdown(data.results || []);
    } catch (e) { /* silencioso */ }
  }

  _renderDropdown(results) {
    if (!results.length) {
      this.dropdown.innerHTML = '<div class="p-2 text-muted small">Nenhum resultado encontrado.</div>';
    } else {
      this.dropdown.innerHTML = results.map(r => `
        <div class="pvs-option p-2 border-bottom" style="cursor:pointer;" data-id="${r.id}" data-text="${this._esc(r.text)}" data-tem-variantes="${r.tem_variantes ? '1' : '0'}">
          ${this._esc(r.text)}
          ${r.tem_variantes ? '<span class="badge ms-1" style="background:#d1fae5;color:#047857;font-size:.65rem;"><i class="bi bi-layers"></i> variantes</span>' : ''}
        </div>
      `).join('');
      this.dropdown.querySelectorAll('.pvs-option').forEach(el => {
        el.addEventListener('mousedown', () => this._selecionarBase(el));
        el.addEventListener('mouseover', () => el.style.background = '#eaf5ec');
        el.addEventListener('mouseout', () => el.style.background = '');
      });
    }
    this.dropdown.style.display = 'block';
  }

  // ──────────────────────────────────────────────────────────────────
  // SELEÇÃO DO PRODUTO BASE
  // ──────────────────────────────────────────────────────────────────
  async _selecionarBase(el) {
    const id = el.dataset.id;
    const text = el.dataset.text;
    const temVariantes = el.dataset.temVariantes === '1';

    this.searchInput.value = text;
    this.dropdown.style.display = 'none';
    this._produtoBaseId = id;
    this._resetAtributos();

    if (temVariantes) {
      await this._carregarDimensoes(id);
    } else {
      // Produto simples sem variantes → resolve diretamente
      this._produtoFinalId = id;
      this.produtoIdInput.value = id;
      this._mostrarResultado({ nome_completo: text, codigo: '' });
      this._chamarCallback({ produto_id: id, nome_completo: text });
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // CARREGAR DIMENSÕES
  // ──────────────────────────────────────────────────────────────────
  async _carregarDimensoes(produtoBaseId) {
    try {
      const res = await fetch(`${this.opts.urls.dimensoes}?produto_base_id=${produtoBaseId}`);
      const data = await res.json();
      if (data.error) { console.error(data.error); return; }
      this._dimensoes = data.dimensoes || [];
      this._renderAtributos();
    } catch (e) { console.error('Erro ao carregar dimensões:', e); }
  }

  _renderAtributos() {
    if (!this._dimensoes.length) {
      this.atributosArea.style.display = 'none';
      return;
    }
    this.atributosArea.style.display = 'block';
    this.atributosArea.innerHTML = `
      <div class="row g-2">
        ${this._dimensoes.map(d => `
          <div class="col">
            <label class="form-label fw-semibold mb-1" style="font-size:.82rem;">
              <i class="bi bi-tag me-1 text-violet"></i>${this._esc(d.nome)}
            </label>
            <select class="form-select form-select-sm pvs-dim-select" data-dim-id="${d.id}" data-dim-nome="${this._esc(d.nome)}">
              <option value="">-- selecione --</option>
              ${d.valores.map(v => `<option value="${this._esc(v)}">${this._esc(v)}</option>`).join('')}
            </select>
          </div>
        `).join('')}
      </div>
    `;
    this.atributosArea.querySelectorAll('.pvs-dim-select').forEach(sel => {
      sel.addEventListener('change', () => this._tentarResolver());
    });
  }

  // ──────────────────────────────────────────────────────────────────
  // RESOLVER VARIANTE
  // ──────────────────────────────────────────────────────────────────
  async _tentarResolver() {
    const selects = [...this.atributosArea.querySelectorAll('.pvs-dim-select')];
    const atributos = {};
    let completo = true;
    for (const sel of selects) {
      if (!sel.value) { completo = false; break; }
      atributos[sel.dataset.dimId] = sel.value;
    }

    this.resultadoArea.style.display = 'none';

    if (!completo) return;

    try {
      const res = await fetch(this.opts.urls.resolver, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.opts.csrfToken },
        body: JSON.stringify({ produto_base_id: this._produtoBaseId, atributos }),
      });
      const data = await res.json();
      if (data.erro) {
        this._mostrarErro(data.erro);
        this.produtoIdInput.value = '';
        this._produtoFinalId = null;
      } else {
        this._produtoFinalId = data.produto_id;
        this.produtoIdInput.value = data.produto_id;
        this._mostrarResultado(data);
        this._chamarCallback(data);
      }
    } catch (e) {
      this._mostrarErro('Erro de comunicação ao resolver variante.');
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // UI AUXILIAR
  // ──────────────────────────────────────────────────────────────────
  _mostrarResultado(produto) {
    this.resultadoArea.style.display = 'block';
    this.resultadoArea.innerHTML = `
      <div class="alert alert-success p-2 d-flex align-items-center gap-2 mb-0" style="border-radius:8px;">
        <i class="bi bi-check-circle-fill text-success"></i>
        <div>
          <strong>${this._esc(produto.nome_completo)}</strong>
          ${produto.codigo ? `<small class="text-muted ms-2">${this._esc(produto.codigo)}</small>` : ''}
          ${produto.preco_venda ? `<small class="text-muted ms-2">R$ ${produto.preco_venda}</small>` : ''}
        </div>
      </div>`;
  }

  _mostrarErro(msg) {
    this.resultadoArea.style.display = 'block';
    this.resultadoArea.innerHTML = `
      <div class="alert alert-warning p-2 d-flex align-items-center gap-2 mb-0" style="border-radius:8px;">
        <i class="bi bi-exclamation-triangle-fill text-warning"></i>
        <small>${this._esc(msg)}</small>
      </div>`;
  }

  _resetAtributos() {
    this._dimensoes = [];
    this._produtoFinalId = null;
    this.produtoIdInput.value = '';
    this.atributosArea.style.display = 'none';
    this.atributosArea.innerHTML = '';
    this.resultadoArea.style.display = 'none';
    this.resultadoArea.innerHTML = '';
  }

  // ──────────────────────────────────────────────────────────────────
  // CARREGAMENTO INICIAL (modo edição)
  // ──────────────────────────────────────────────────────────────────
  async _carregarInicial() {
    const id = this.opts.initialProdutoId;
    this._produtoFinalId = id;
    this.produtoIdInput.value = id;
    this.searchInput.value = this.opts.initialProdutoText || `#${id}`;
    this._mostrarResultado({ nome_completo: this.opts.initialProdutoText || `Produto #${id}`, codigo: '' });
  }

  _chamarCallback(produto) {
    if (typeof this.opts.onResolve === 'function') {
      this.opts.onResolve(produto);
    }
  }

  _esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ──────────────────────────────────────────────────────────────────
  // API PÚBLICA
  // ──────────────────────────────────────────────────────────────────
  getValue() { return this._produtoFinalId; }
  reset() { this.searchInput.value = ''; this._resetAtributos(); this._produtoBaseId = null; }
}
