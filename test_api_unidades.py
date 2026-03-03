#!/usr/bin/env python
"""
Script para testar a API de unidades de medida
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from produtos.models import Produto, UnidadeMedida
from empresas.models import Empresa

User = get_user_model()

# Buscar uma empresa
empresas = Empresa.objects.all()
print(f"Total de empresas: {empresas.count()}")

if empresas.exists():
    empresa = empresas.first()
    print(f"\nEmpresa selecionada: {empresa.nome}")
    
    # Verificar unidades desta empresa
    unidades = UnidadeMedida.objects.filter(empresa=empresa)
    print(f"Unidades da empresa: {unidades.count()}")
    for u in unidades:
        print(f"  - {u.id}: {u.nome} ({u.sigla})")
    
    # Buscar produtos da empresa
    produtos = Produto.objects.filter(categoria__empresa=empresa)
    print(f"\nProdutos da empresa: {produtos.count()}")
    
    if produtos.exists():
        produto = produtos.first()
        print(f"\nProduto selecionado: {produto.nome} (ID: {produto.id})")
        print(f"Unidade padrão: {produto.unidade_medida}")
        
        # Simular a API
        print("\n--- Simulando resposta da API ---")
        unidades_empresa = UnidadeMedida.objects.filter(empresa=empresa).values('id', 'nome', 'sigla').order_by('nome')
        
        response_data = {
            'success': True,
            'unidades': list(unidades_empresa),
            'unidade_padrao_id': produto.unidade_medida.id,
            'unidade_padrao_nome': produto.unidade_medida.nome,
        }
        
        print(f"Resposta JSON: {response_data}")
        print(f"Quantidade de unidades: {len(response_data['unidades'])}")
    else:
        print("Nenhum produto encontrado!")
else:
    print("Nenhuma empresa encontrada!")
