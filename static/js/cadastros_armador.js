// JS para o formulário de Armador
console.log('cadastros_armador.js loaded');

(function () {
  const cfg = {
    buscar_cep_url: window.CADASTROS_BUSCAR_CEP_URL || '/cadastros/api/buscar-cep/',
    buscar_cnpj_url: window.CADASTROS_BUSCAR_CNPJ_URL || '/cadastros/api/buscar-cnpj/'
  };

  function getCsrfToken() {
    const el = document.querySelector('input[name=csrfmiddlewaretoken]');
    return el ? el.value : null;
  }

  function showAlert(text, level = 'danger') {
    try {
      const main = document.querySelector('main') || document.querySelector('.container-fluid');
      if (!main) return;
      const div = document.createElement('div');
      div.className = `alert alert-${level} alert-dismissible fade show`;
      div.setAttribute('role', 'alert');
      div.innerHTML = `${text} <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>`;
      main.insertBefore(div, main.firstChild);
      setTimeout(() => {
        try {
          const bs = bootstrap.Alert.getInstance(div) || new bootstrap.Alert(div);
          bs.close();
        } catch (e) { }
      }, 5000);
    } catch (e) {
      console.error('showAlert failed', e);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Buscar CNPJ - Click no ícone de lupa
    const cnpjLabel = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('CNPJ'));
    if (cnpjLabel) {
      const icon = cnpjLabel.querySelector('i.bi-search');
      if (icon) {
        icon.addEventListener('click', async (e) => {
          e.preventDefault();
          const cnpjInput = document.querySelector('input[name="cnpj"]');
          if (!cnpjInput) {
            showAlert('Campo CNPJ não encontrado', 'danger');
            return;
          }

          const cnpj = (cnpjInput.value || '').replace(/\D/g, '');
          if (cnpj.length !== 14) {
            showAlert('Digite um CNPJ válido (14 dígitos)', 'danger');
            return;
          }

          const csrf = getCsrfToken();
          try {
            icon.style.opacity = '0.5';
            icon.style.pointerEvents = 'none';

            const resp = await fetch(cfg.buscar_cnpj_url, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRFToken': csrf,
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
              },
              body: `cnpj=${cnpj}`
            });

            if (!resp.ok) {
              const json = await resp.json().catch(() => ({}));
              showAlert(json.erro || 'Erro ao buscar CNPJ', 'danger');
              return;
            }

            const data = await resp.json();
            if (data && data.sucesso && data.dados) {
              const d = data.dados;

              // Preencher campos principais
              if (d.nome) document.querySelector('input[name="nome"]').value = d.nome;
              if (d.nome_fantasia) {
                const nf = document.querySelector('input[name="nome_fantasia"]');
                if (nf) nf.value = d.nome_fantasia;
              }

              // Preencher endereço
              if (d.logradouro) document.querySelector('input[name="endereco"]').value = d.logradouro;
              if (d.numero) document.querySelector('input[name="numero"]').value = d.numero;
              if (d.bairro) document.querySelector('input[name="bairro"]').value = d.bairro;
              if (d.cidade) document.querySelector('input[name="cidade"]').value = d.cidade;
              if (d.uf) {
                const ufField = document.querySelector('select[name="uf"]') || document.querySelector('input[name="uf"]');
                if (ufField) ufField.value = d.uf.toUpperCase();
              }
              if (d.cep) document.querySelector('input[name="cep"]').value = d.cep;

              showAlert('CNPJ carregado com sucesso!', 'success');
            } else {
              showAlert(data.erro || 'CNPJ não encontrado', 'warning');
            }
          } catch (err) {
            console.error('Erro ao buscar CNPJ:', err);
            showAlert('Erro ao buscar CNPJ. Verifique a conexão.', 'danger');
          } finally {
            icon.style.opacity = '1';
            icon.style.pointerEvents = 'auto';
          }
        });
      }
    }

    // Buscar CEP - Click no ícone de lupa
    const cepLabel = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('CEP'));
    if (cepLabel) {
      const icon = cepLabel.querySelector('i.bi-search');
      if (icon) {
        icon.addEventListener('click', async (e) => {
          e.preventDefault();
          const cepInput = document.querySelector('input[name="cep"]');
          if (!cepInput) {
            showAlert('Campo CEP não encontrado', 'danger');
            return;
          }

          const cep = (cepInput.value || '').replace(/\D/g, '');
          if (cep.length !== 8) {
            showAlert('Digite um CEP válido (8 dígitos)', 'danger');
            return;
          }

          const csrf = getCsrfToken();
          try {
            icon.style.opacity = '0.5';
            icon.style.pointerEvents = 'none';

            const resp = await fetch(cfg.buscar_cep_url, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRFToken': csrf,
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
              },
              body: `cep=${cep}`
            });

            if (!resp.ok) {
              const json = await resp.json().catch(() => ({}));
              showAlert(json.erro || 'Erro ao buscar CEP', 'danger');
              return;
            }

            const data = await resp.json();
            const d = (data && data.dados) ? data.dados : data;

            if (d && d.logradouro) {
              // Preencher campos
              if (d.logradouro) document.querySelector('input[name="endereco"]').value = d.logradouro;
              if (d.bairro) document.querySelector('input[name="bairro"]').value = d.bairro;
              if (d.cidade) document.querySelector('input[name="cidade"]').value = d.cidade;
              if (d.uf) {
                const ufField = document.querySelector('select[name="uf"]') || document.querySelector('input[name="uf"]');
                if (ufField) ufField.value = d.uf.toUpperCase();
              }
              if (d.cep) document.querySelector('input[name="cep"]').value = d.cep;

              showAlert('CEP carregado com sucesso!', 'success');
            } else {
              showAlert(d.erro || 'CEP não encontrado', 'warning');
            }
          } catch (err) {
            console.error('Erro ao buscar CEP:', err);
            showAlert('Erro ao buscar CEP. Verifique a conexão.', 'danger');
          } finally {
            icon.style.opacity = '1';
            icon.style.pointerEvents = 'auto';
          }
        });
      }
    }

    // Melhorar UX do ícone de busca - mostrar cursor de pointer
    document.querySelectorAll('label i.bi-search').forEach(icon => {
      icon.style.cursor = 'pointer';
      icon.style.transition = 'opacity 0.2s';
      icon.addEventListener('mouseenter', () => {
        icon.style.opacity = '0.7';
      });
      icon.addEventListener('mouseleave', () => {
        icon.style.opacity = '1';
      });
    });
  });
})();
