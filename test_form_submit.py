#!/usr/bin/env python
"""
Script para testar o envio do formulário
"""
import os
import sys
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

try:
    from django.test import Client
    from usuarios.models import Usuario
    from compras.models import SolicitacaoCompra
    from produtos.models import Produto

    # Buscar usuário com empresa
    user = Usuario.objects.filter(empresa__isnull=False).first()
    if not user:
        print("✗ Usuário não encontrado")
        sys.exit(1)

    print(f"✓ Testando com: {user}")
    print(f"  Empresa: {user.empresa}")

    # Buscar um produto
    produto = Produto.objects.filter(categoria__empresa=user.empresa).first()
    if not produto:
        print("✗ Nenhum produto encontrado")
        sys.exit(1)

    print(f"  Produto: {produto}")
    print(f"  Unidade padrão: {produto.unidade_medida}")

    # Preparar dados completos para o formulário
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    data = {
        'data_necessidade': tomorrow,
        'departamento': 'Operações',
        'justificativa': 'Teste de solicitação de compra',
        'emergencial': False,
        'itens-TOTAL_FORMS': '1',
        'itens-INITIAL_FORMS': '0',
        'itens-MIN_NUM_FORMS': '1',
        'itens-MAX_NUM_FORMS': '1000',
        # Item 1
        'itens-0-produto': str(produto.id),
        'itens-0-quantidade': '10',
        'itens-0-unidade_medida': str(produto.unidade_medida.id),
        'itens-0-especificacao': 'Teste',
        'itens-0-DELETE': '',
        'itens-0-id': '',
    }

    print("\n=== Enviando formulário ===")
    print(f"Dados: {data}")

    client = Client()
    client.force_login(user)

    response = client.post('/compras/solicitacoes/nova/', data)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 302:
        print("✓ Redirecionado (sucesso esperado)")
        # Buscar a solicitação criada
        sol = SolicitacaoCompra.objects.filter(empresa=user.empresa).last()
        if sol:
            print(f"✓ Solicitação criada: #{sol.id}")
            print(f"  Data necessidade: {sol.data_necessidade}")
            print(f"  Itens: {sol.itens.count()}")
        else:
            print("? Nenhuma solicitação encontrada")
    elif response.status_code == 200:
        # Verificar se há erros no formulário
        html = response.content.decode('utf-8')
        
        if 'errorlist' in html:
            print("✗ Erros no formulário encontrados")
            # Extrair erros
            import re
            errors = re.findall(r'<li>(.*?)</li>', html)
            for error in errors[:5]:
                print(f"  - {error}")
        else:
            print("? Formulário retornou 200 sem erros óbvios")
            # Verificar se há problemas com management form
            if 'itens-TOTAL_FORMS' in html:
                print("✓ Management form presente")
            else:
                print("✗ Management form não encontrado")
    else:
        print(f"✗ Erro: {response.status_code}")

except Exception as e:
    import traceback
    print(f"✗ Erro: {e}")
    traceback.print_exc()
