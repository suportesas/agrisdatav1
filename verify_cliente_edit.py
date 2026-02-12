"""
Verificar por que o cliente não consegue ser editado após inserção
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '.')
django.setup()

from django.test import Client
from cadastros.models import Cliente
from empresas.models import Empresa
from usuarios.models import Usuario

empresa = Empresa.objects.filter(nome__icontains='Terra Brasilis').first()
cliente = Cliente.objects.filter(pk=3, empresa=empresa).first()
usuario = Usuario.objects.filter(empresa=empresa, is_active=True).first()

print("="*80)
print("VERIFICACAO: Estado do Cliente e Capacidade de Edicao")
print("="*80)
print(f"Usuario: {usuario.username}")
print(f"Cliente: {cliente.razao_social} (ID: {cliente.id})")
print(f"Empresa cliente: {cliente.empresa.nome}")
print(f"Empresa usuario: {usuario.empresa.nome if usuario.empresa else 'NENHUMA'}")

print("\n" + "="*80)
print("Dados Atuais do Cliente:")
print("="*80)
print(f"  razao_social: {cliente.razao_social}")
print(f"  tipo_cliente: {cliente.tipo_cliente}")
print(f"  tipo_pessoa: {cliente.tipo_pessoa}")
print(f"  limite_credito: {cliente.limite_credito}")
print(f"  forma_pagamento_padrao: {cliente.forma_pagamento_padrao}")
print(f"  prazo_pagamento: {cliente.prazo_pagamento}")
print(f"  regime_tributario: {cliente.regime_tributario}")
print(f"  usuario_vinculado: {cliente.usuario_vinculado}")
print(f"  status: {cliente.status}")

print("\n" + "="*80)
print("Tentando fazer GET (carregar formulario)...")
print("="*80)

client = Client()
client.force_login(usuario)
response = client.get(f'/cadastros/clientes/{cliente.id}/editar/')

print(f"Status code: {response.status_code}")

if response.status_code == 200:
    print("✅ FORMULARIO CARREGOU COM SUCESSO")
    
    # Tentar verificar erros
    if 'form' in response.context:
        form = response.context['form']
        print(f"\nFormulario validado: {form.is_valid()}")
        if not form.is_valid():
            print("Erros na forma:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
else:
    print(f"❌ ERRO AO CARREGAR FORMULARIO")
    print(f"Body: {response.content[:500]}")

print("\n" + "="*80)
print("Tentando fazer POST (salvar cliente)...")
print("="*80)

# Preparar dados minimos
post_data = {
    'empresa': str(empresa.id),
    'tipo_cliente': cliente.tipo_cliente or 'NACIONAL',
    'tipo_pessoa': cliente.tipo_pessoa or 'PJ',
    'razao_social': cliente.razao_social,
    'cnpj_cpf': cliente.cnpj_cpf or '',
    'inscricao_estadual': cliente.inscricao_estadual or '',
    'inscricao_municipal': '',
    'inscricao_suframa': '',
    'eori': '',
    'vat': '',
    'regime_tributario': cliente.regime_tributario or 'Lucro Presumido',
    'contribuinte_icms': 'on' if cliente.contribuinte_icms else '',
    'pais': cliente.pais or 'Brasil',
    'moeda_padrao': cliente.moeda_padrao or 'BRL',
    'porto_destino': cliente.porto_destino.id if cliente.porto_destino else '',
    'contato_principal_nome': '',
    'contato_principal_telefone': '',
    'contato_principal_email': '',
    'limite_credito': str(cliente.limite_credito or '0'),
    'forma_pagamento_padrao': cliente.forma_pagamento_padrao or 'BOLETO',
    'desconto_padrao': str(cliente.desconto_padrao or '0'),
    'vendedor_responsavel': cliente.vendedor_responsavel.id if cliente.vendedor_responsavel else '',
    'observacoes_comerciais': cliente.observacoes_comerciais or '',
    'acesso_portal': 'on' if cliente.acesso_portal else '',
    'usuario_vinculado': str(cliente.usuario_vinculado_id or usuario.id),
    'prazo_pagamento': str(cliente.prazo_pagamento or ''),
    'prazo_pagamento_padrao': str(cliente.prazo_pagamento_padrao_id or ''),
}

response = client.post(f'/cadastros/clientes/{cliente.id}/editar/', post_data, follow=True)
print(f"Status code: {response.status_code}")

if response.status_code == 200:
    if response.redirect_chain:
        print(f"✅ REDIRECCIONOU PARA: {response.redirect_chain[-1][0]}")
        print("✅ CLIENTE EDITADO COM SUCESSO")
    else:
        # Verificar se tem erros
        print("Verifique se ha erros na pagina...")
        if 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                print("\n❌ ERROS NO FORMULARIO:")
                for field, errors in form.errors.items():
                    print(f"  {field}: {errors}")
else:
    print(f"❌ ERRO AO SALVAR: {response.status_code}")

print("\n" + "="*80)
print("RESUMO:")
print("="*80)
print(f"""
Se voce nao consegue editar no navegador, pode ser:

1. ❌ FORMULARIO NAO CARREGA (GET retorna erro)
   - Solucao: Recarregue a página e limpe cache

2. ❌ FORMULARIO CARREGA MAS TEM VALIDACAO ERRO (POST retorna erro)
   - Solucao: Preencha corretamente todos os campos obrigatorios

3. ❌ VALIDACAO DE EMPRESA (usuario em empresa diferente)
   - Verifique se está logado na empresa correta
   - Empresa do usuario: {usuario.empresa.nome if usuario.empresa else 'NENHUMA'}
   - Empresa do cliente: {cliente.empresa.nome}

4. ❌ PROBLEMA DE PERMISSAO (usuario nao pode editar este cliente)
   - Verifique se o usuario tem permissao para cadastros.change_cliente

TESTE: Tente abrir a URL direto no navegador:
http://127.0.0.1:8000/cadastros/clientes/{cliente.id}/editar/

Se der erro 404 ou 403, o problema é anterior ao formulario.
Se carregar o formulario mas nao conseguir preencher, é problema de JS.
""")
