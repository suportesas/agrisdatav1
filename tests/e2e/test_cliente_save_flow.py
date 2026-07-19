try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import Cliente, PrazoPagamentoPadrao

User = get_user_model()


@pytest.fixture
def e2e_cliente_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa Cliente')
        user = User.objects.create_user(username='e2ecliente', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        # create a cliente to edit
        cliente = Cliente.objects.create(empresa=empresa, razao_social='E2E Cliente', cnpj_cpf='12345678901234')
        preset = PrazoPagamentoPadrao.objects.create(empresa=empresa, nome='30 dias', termos='30', ativo=True)

        client = Client()
        assert client.login(username='e2ecliente', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'cliente': cliente, 'preset': preset, 'sessionid': sessionid}


def test_cliente_edit_flow(page, live_server, e2e_cliente_data):
    """Edita um cliente: adiciona uma moeda nova via modal (aba "Exportação /
    Importação") e aplica um preset de prazo de pagamento (aba "Dados
    Comerciais"), depois salva.

    cliente_form.html organiza os campos em abas (nav .section-nav +
    .form-section[data-tab-panel], ver static/js/section-nav.js) — "Moeda
    Padrão" fica na aba "sec-exportacao" e "Preset Prazo" na aba
    "sec-comercial". Nenhum dos dois campos depende do valor de
    tipo_cliente; a visibilidade é só a aba ativa.
    """
    cliente = e2e_cliente_data['cliente']
    preset = e2e_cliente_data['preset']
    sessionid = e2e_cliente_data['sessionid']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    page.goto(f"{live_server.url}/cadastros/clientes/{cliente.pk}/editar/")

    # --- Aba "Exportação / Importação": adicionar uma moeda via modal ---
    page.click('a[data-tab="sec-exportacao"]')
    page.click('#addMoedaBtn')
    page.wait_for_selector('#moedaModal', state='visible', timeout=5000)

    page.fill('#moeda_codigo', 'JPY')
    page.fill('#moeda_nome', 'Iene')

    resp_list = []
    page.on('response', lambda r: resp_list.append(r) if '/cadastros/moedas/novo-ajax/' in r.url else None)
    page.click('#moedaSaveBtn')

    page.wait_for_timeout(500)
    assert resp_list, 'Requisição AJAX de criação de moeda não foi enviada'
    resp = resp_list[0]
    j = resp.json()
    assert j.get('success'), f'Criação de moeda falhou: status={resp.status} body={resp.text()}'

    # cadastros_cliente.js já seleciona a moeda recém-criada no <select> e
    # fecha o modal (bootstrap.Modal.hide()) — não precisa reabrir/re-selecionar.
    page.wait_for_selector('#moedaModal', state='hidden', timeout=5000)
    assert page.eval_on_selector('#id_moeda_padrao', 'el => el.value') == 'JPY'

    # --- Aba "Dados Comerciais": aplicar preset de prazo de pagamento ---
    page.click('a[data-tab="sec-comercial"]')
    page.select_option('#id_prazo_pagamento_padrao_select', str(preset.pk))

    # prazo_pagamento é HiddenInput (sincronizado via JS ao trocar o preset) —
    # nunca fica "visible", só "attached". atualizarTermos() já preenche o
    # valor com o primeiro termo do preset assim que ele é selecionado.
    page.wait_for_function(
        "() => document.getElementById('id_prazo_pagamento').value === '30'",
        timeout=3000,
    )

    # --- Salvar ---
    page.click('button#clienteSaveBtn')

    # cliente_update redireciona para o detail do cliente em caso de sucesso
    page.wait_for_url(f"{live_server.url}/cadastros/clientes/{cliente.pk}/", timeout=10000)
    assert page.locator('text=atualizado').count() >= 1
