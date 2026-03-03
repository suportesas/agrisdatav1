#!/usr/bin/env python
"""
Script para testar a view e template de criação de parcelas
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_agricola.settings')
sys.path.insert(0, r'c:\erp_agricola')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from cadastros.models import Empresa
from financeiro.models import ContaPagar, FormaPagemento
from datetime import datetime, timedelta

User = get_user_model()

def test_parcela_criar_page():
    """Testar carregamento da página de criação de parcelas"""
    print("🧪 Testando página de criação de parcelas...\n")
    
    # Criar cliente e usuário
    client = Client()
    
    # Buscar ou criar usuário
    user = User.objects.filter(username='admin').first()
    if not user:
        print("❌ Admin não encontrado. Execute criar_admin_simples.py primeiro.")
        return
    
    # Login
    login_success = client.login(username='admin', password='admin')
    print(f"✅ Login: {'Sucesso' if login_success else 'Falha'}")
    
    # Buscar uma empresa e conta a pagar
    empresa = Empresa.objects.filter(user=user).first()
    if not empresa:
        print("❌ Empresa não encontrada para o usuário.")
        return
    
    conta = ContaPagar.objects.filter(empresa=empresa, parcelas__isnull=True).first()
    if not conta:
        print("❌ Conta a pagar sem parcelas não encontrada.")
        print("   Criando conta de teste...")
        fornecedor = empresa.fornecedores.first()
        if fornecedor:
            conta = ContaPagar.objects.create(
                empresa=empresa,
                numero='TEST-001',
                fornecedor=fornecedor,
                valor_total=3000.00,
                data_emissao=datetime.now().date(),
            )
            print(f"   ✅ Conta criada: {conta.numero}")
        else:
            print("   ❌ Nenhum fornecedor encontrado.")
            return
    
    # Testar acesso à página
    response = client.get(f'/financeiro/contas/{conta.pk}/parcelas/criar/')
    
    print(f"\n📝 Testando GET /financeiro/contas/{conta.pk}/parcelas/criar/")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Página carregada com sucesso!")
        
        # Verificar contexto
        context = response.context or {}
        print(f"\n📊 Contexto da página:")
        print(f"  - conta: {context.get('conta')}")
        print(f"  - condicoes: {len(context.get('condicoes', []))} condição(ões)")
        print(f"  - formas_pagamento: {len(context.get('formas_pagamento', []))} forma(s)")
        
        # Verificar Template
        templates = [t.name for t in response.templates]
        print(f"\n📄 Templates usados:")
        for template in templates:
            print(f"  - {template}")
        
        # Verificar conteúdo
        content = response.content.decode('utf-8')
        checks = {
            'Criar Parcelas': 'Criar Parcelas Automaticamente' in content,
            'Condições': 'À Vista' in content and '30 Dias' in content,
            'Formas de Pagamento': 'Forma de Pagamento' in content,
            'Preview': 'Parcelas que Serão Criadas' in content,
            'JavaScript': 'atualizarParcelas' in content,
        }
        
        print(f"\n✨ Verificação de conteúdo:")
        for chave, resultado in checks.items():
            status = "✅" if resultado else "❌"
            print(f"  {status} {chave}")
    
    elif response.status_code == 302:
        print(f"⚠️  Redirecionamento para: {response.url}")
    else:
        print(f"❌ Erro: {response.status_code}")
    
    # Testar POST
    print(f"\n\n📡 Testando POST with condicao_pagamento='30'")
    
    post_data = {
        'condicao_pagamento': '30',
        'forma_pagamento_padrao': '',
    }
    
    response = client.post(
        f'/financeiro/contas/{conta.pk}/parcelas/criar/',
        post_data,
        follow=True
    )
    
    print(f"Status: {response.status_code}")
    
    # Verificar se parcelas foram criadas
    parcelas = conta.parcelas.all()
    print(f"\n📊 Parcelas criadas: {parcelas.count()}")
    
    if parcelas.exists():
        print("✅ Parcelas criadas com sucesso!")
        for p in parcelas:
            print(f"  - Parcela #{p.numero_parcela}: R$ {p.valor_parcela} (venc. {p.data_vencimento})")
    else:
        print("❌ Nenhuma parcela foi criada.")
    
    print("\n" + "="*60)
    print("✅ TESTE COMPLETO!")

if __name__ == '__main__':
    test_parcela_criar_page()
