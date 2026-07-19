import json
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Role, Programa, RoleAudit

User = get_user_model()


@pytest.fixture
def e2e_templates_data(db):
    empresa = Empresa.objects.create(nome='E2E Empresa Tpl')
    user = User.objects.create_user(username='tpladmin', password='pass', tipo='ADMIN')
    user.empresa = empresa
    user.save()

    role = Role.objects.create(empresa=empresa, name='TemplateRole')

    client = Client()
    assert client.login(username='tpladmin', password='pass')

    return {'empresa': empresa, 'role': role, 'client': client}


def test_save_and_apply_permission_template_via_api(e2e_templates_data):
    """Salva e aplica um template de permissões batendo direto na API.

    A UI de "salvar/aplicar template" que esse teste cobria via Playwright
    (input[name="add"], botão "Salvar como template", #template-select) não
    existe em nenhum template atual — só o backend (empresas/views.py:
    save_permission_template/apply_template_to_role/permission_templates_list)
    ainda tem essa funcionalidade. Até a UI ser reconstruída (ou removida de
    vez), este teste cobre o contrato da API que ela consumiria.
    """
    role = e2e_templates_data['role']
    client = e2e_templates_data['client']

    programa = Programa.objects.filter(ativo=True).first()
    assert programa is not None, 'Nenhum Programa ativo encontrado — rode a sincronização de programas antes dos testes'

    # Salva as permissões atuais como template
    resp = client.post(
        f'/empresas/roles/{role.id}/permissions/save-template/',
        data=json.dumps({'nome': 'E2E Template', 'dados': {'programa_ids': [programa.id]}}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    template_id = resp.json()['template_id']

    # Template aparece na listagem da empresa
    resp = client.get('/empresas/roles/templates/')
    assert resp.status_code == 200
    assert any(t['nome'] == 'E2E Template' for t in resp.json()['templates'])

    # Aplica o template na role
    resp = client.post(
        f'/empresas/roles/{role.id}/permissions/apply-template/',
        data=json.dumps({'template_id': template_id}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.json() == {'ok': True, 'applied': 1}

    role.refresh_from_db()
    assert programa in role.programas.all()
    assert RoleAudit.objects.filter(role=role, action='permissions_updated').exists()
